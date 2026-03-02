#!/usr/bin/env python3
"""PostgreSQL local readiness smoke test with explicit docker preflight reason codes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_EXPECTED_TABLES = (
    "flyway_schema_history",
    "tb_tenant",
    "tb_user",
    "tb_conversation",
    "tb_message",
    "tb_kb_chunk_embedding",
)

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIPPED = "SKIPPED"

REASON_NONE = "NONE"
REASON_DOCKER_ENGINE_DOWN = "DOCKER_ENGINE_DOWN"
REASON_DOCKER_PERMISSION = "DOCKER_PERMISSION"
REASON_COMPOSE_FILE_MISSING = "COMPOSE_FILE_MISSING"
REASON_DRIVER_NOT_AVAILABLE = "DRIVER_NOT_AVAILABLE"
REASON_DRIVER_CONNECTION_FAILED = "DRIVER_CONNECTION_FAILED"
REASON_DOCKER_COMPOSE_UP_FAILED = "DOCKER_COMPOSE_UP_FAILED"
REASON_DOCKER_EXEC_FAILED = "DOCKER_EXEC_FAILED"
REASON_CHECK_FAILED = "CHECK_FAILED"
REASON_METHOD_INVALID = "METHOD_INVALID"
REASON_UNKNOWN = "UNKNOWN"
REASON_UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

DOCKER_ENGINE_TOKENS = (
    "failed to connect to the docker api",
    "cannot connect to the docker daemon",
    "is the docker daemon running",
    "dockerdesktoplinuxengine",
    "open //./pipe/dockerdesktoplinuxengine",
    "error during connect",
)
DOCKER_PERMISSION_TOKENS = (
    "permission denied",
    "access is denied",
    "got permission denied while trying to connect",
)

REMEDIATION_HINTS = {
    REASON_NONE: "-",
    REASON_DOCKER_ENGINE_DOWN: "Start Docker Desktop/Engine and verify `docker info` succeeds.",
    REASON_DOCKER_PERMISSION: "Grant Docker daemon access to this terminal/session and rerun.",
    REASON_COMPOSE_FILE_MISSING: "Verify compose path exists and pass the correct `--compose-file` value.",
    REASON_DRIVER_NOT_AVAILABLE: "Install psycopg/psycopg2 or run docker-exec mode.",
    REASON_DRIVER_CONNECTION_FAILED: "Check DB host/port/user/password and PostgreSQL readiness.",
    REASON_DOCKER_COMPOSE_UP_FAILED: "Inspect `docker compose up` stderr and fix container startup issues.",
    REASON_DOCKER_EXEC_FAILED: "Inspect docker exec/psql logs and ensure postgres container is healthy.",
    REASON_CHECK_FAILED: "Inspect violation details and restore expected DB schema/extension/table state.",
    REASON_METHOD_INVALID: "Use --method auto|driver|docker-exec.",
    REASON_UNKNOWN: "Inspect stderr/stdout tail in this artifact and triage manually.",
    REASON_UNEXPECTED_ERROR: "Inspect exception details in this artifact and rerun after fix.",
}


@dataclass
class Violation:
    code: str
    message: str
    details: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PostgreSQL + pgvector smoke checks")
    parser.add_argument("--db-url", default=os.environ.get("DB_URL", ""))
    parser.add_argument("--host", default=os.environ.get("DB_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DB_PORT", "5432")))
    parser.add_argument("--database", default=os.environ.get("POSTGRES_DB", "aichatbot"))
    parser.add_argument(
        "--user",
        default=os.environ.get("DB_USERNAME", os.environ.get("POSTGRES_USER", "aichatbot")),
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("DB_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "local-dev-only-password")),
    )
    parser.add_argument("--method", choices=("auto", "driver", "docker-exec"), default="auto")
    parser.add_argument(
        "--docker-unavailable-policy",
        choices=("fail", "skipped"),
        default="fail",
        help="When docker preflight fails in docker-exec mode.",
    )
    parser.add_argument("--auto-up", action="store_true", help="Run `docker compose up -d <service>` before checks")
    parser.add_argument("--compose-file", default="infra/docker-compose.yml")
    parser.add_argument("--compose-service", default="postgres")
    parser.add_argument("--expected-table", dest="expected_tables", action="append")
    parser.add_argument("--output-txt")
    parser.add_argument("--output-json")
    return parser.parse_args()


def normalize_text(text: str, max_chars: int = 2000) -> str:
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    value = "".join(ch for ch in value if ch == "\n" or ch >= " ")
    value = value.strip()
    if len(value) > max_chars:
        return value[-max_chars:]
    return value


def parse_db_url(raw: str) -> tuple[str, int, str]:
    value = raw.strip()
    if not value:
        raise ValueError("empty db url")

    if value.startswith("jdbc:postgresql://"):
        value = value[len("jdbc:") :]

    parsed = urlparse(value)
    if parsed.scheme != "postgresql":
        raise ValueError(f"unsupported db url scheme: {parsed.scheme}")

    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") or "aichatbot"
    return host, port, database


def resolve_connection(args: argparse.Namespace) -> tuple[str, int, str]:
    if args.db_url:
        try:
            return parse_db_url(args.db_url)
        except ValueError:
            return args.host, args.port, args.database
    return args.host, args.port, args.database


def detect_driver_module() -> str | None:
    try:
        import psycopg  # type: ignore  # noqa: F401

        return "psycopg"
    except ImportError:
        pass

    try:
        import psycopg2  # type: ignore  # noqa: F401

        return "psycopg2"
    except ImportError:
        return None


def run_subprocess(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def classify_docker_failure(raw_output: str) -> str:
    value = raw_output.lower()
    if any(token in value for token in DOCKER_PERMISSION_TOKENS):
        return REASON_DOCKER_PERMISSION
    if any(token in value for token in DOCKER_ENGINE_TOKENS):
        return REASON_DOCKER_ENGINE_DOWN
    return REASON_UNKNOWN


def run_docker_preflight() -> tuple[bool, str]:
    proc = run_subprocess(["docker", "info", "--format", "{{json .ServerErrors}}"])
    output = normalize_text((proc.stdout or "") + "\n" + (proc.stderr or ""))
    return (proc.returncode == 0, output)


def run_psql_via_docker_exec(
    compose_file: Path,
    compose_service: str,
    user: str,
    database: str,
    password: str,
    sql: str,
) -> tuple[bool, str]:
    command = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "exec",
        "-T",
        "-e",
        f"PGPASSWORD={password}",
        compose_service,
        "psql",
        "-U",
        user,
        "-d",
        database,
        "-v",
        "ON_ERROR_STOP=1",
        "-At",
        "-c",
        sql,
    ]
    proc = run_subprocess(command)
    success = proc.returncode == 0
    text = normalize_text((proc.stdout or "").strip())
    if not success and proc.stderr:
        text = normalize_text(f"{text}\n{proc.stderr.strip()}")
    return success, text


def run_checks_with_driver(
    driver: str,
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    expected_tables: list[str],
) -> tuple[list[Violation], dict[str, str]]:
    violations: list[Violation] = []
    checks: dict[str, str] = {}

    if driver == "psycopg":
        import psycopg  # type: ignore

        conn = psycopg.connect(host=host, port=port, dbname=database, user=user, password=password)
    elif driver == "psycopg2":
        import psycopg2  # type: ignore

        conn = psycopg2.connect(host=host, port=port, dbname=database, user=user, password=password)
    else:
        raise ValueError(f"unsupported driver: {driver}")

    try:
        conn.autocommit = False
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["select_1"] = "PASS" if cursor.fetchone()[0] == 1 else "FAIL"

            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            vector_exists = bool(cursor.fetchone()[0])
            checks["vector_extension"] = "PASS" if vector_exists else "FAIL"
            if not vector_exists:
                violations.append(
                    Violation(
                        code="VECTOR_EXTENSION_MISSING",
                        message="pgvector extension is not enabled",
                        details="expected extname=vector in pg_extension",
                    )
                )

            placeholders = ", ".join(["%s"] * len(expected_tables))
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ({placeholders})
                """,
                expected_tables,
            )
            found = int(cursor.fetchone()[0])
            expected = len(expected_tables)
            checks["expected_tables"] = f"{found}/{expected}"
            if found != expected:
                violations.append(
                    Violation(
                        code="TABLE_MISSING",
                        message="required tables are missing",
                        details=f"found={found} expected={expected}",
                    )
                )

            cursor.execute("CREATE TEMP TABLE codex_db_smoke_tmp(id INTEGER PRIMARY KEY, note TEXT)")
            cursor.execute("INSERT INTO codex_db_smoke_tmp(id, note) VALUES (1, 'smoke-ok')")
            cursor.execute("SELECT note FROM codex_db_smoke_tmp WHERE id = 1")
            note = str(cursor.fetchone()[0])
            checks["temp_write_read"] = "PASS" if note == "smoke-ok" else "FAIL"
            if note != "smoke-ok":
                violations.append(
                    Violation(
                        code="TEMP_WRITE_READ_FAILED",
                        message="temp table insert/read check failed",
                        details=f"note={note}",
                    )
                )

            conn.rollback()
    finally:
        conn.close()

    return violations, checks


def run_checks_with_docker_exec(
    compose_file: Path,
    compose_service: str,
    user: str,
    database: str,
    password: str,
    expected_tables: list[str],
) -> tuple[list[Violation], dict[str, str]]:
    violations: list[Violation] = []
    checks: dict[str, str] = {}

    ok, out = run_psql_via_docker_exec(
        compose_file=compose_file,
        compose_service=compose_service,
        user=user,
        database=database,
        password=password,
        sql="SELECT 1",
    )
    checks["select_1"] = "PASS" if ok and out.strip() == "1" else "FAIL"
    if checks["select_1"] != "PASS":
        violations.append(Violation(code="SELECT_1_FAILED", message="SELECT 1 failed", details=out))

    ok, out = run_psql_via_docker_exec(
        compose_file=compose_file,
        compose_service=compose_service,
        user=user,
        database=database,
        password=password,
        sql="SELECT CASE WHEN EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN '1' ELSE '0' END",
    )
    checks["vector_extension"] = "PASS" if ok and out.strip() == "1" else "FAIL"
    if checks["vector_extension"] != "PASS":
        violations.append(
            Violation(
                code="VECTOR_EXTENSION_MISSING",
                message="pgvector extension is not enabled",
                details=out,
            )
        )

    escaped_tables = ", ".join("'" + name.replace("'", "''") + "'" for name in expected_tables)
    ok, out = run_psql_via_docker_exec(
        compose_file=compose_file,
        compose_service=compose_service,
        user=user,
        database=database,
        password=password,
        sql=(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            f"AND table_name IN ({escaped_tables})"
        ),
    )
    found = int(out.strip()) if ok and out.strip().isdigit() else -1
    expected = len(expected_tables)
    checks["expected_tables"] = f"{found}/{expected}"
    if found != expected:
        violations.append(
            Violation(
                code="TABLE_MISSING",
                message="required tables are missing",
                details=f"found={found} expected={expected} raw={out}",
            )
        )

    ok, out = run_psql_via_docker_exec(
        compose_file=compose_file,
        compose_service=compose_service,
        user=user,
        database=database,
        password=password,
        sql=(
            "BEGIN; "
            "CREATE TEMP TABLE codex_db_smoke_tmp(id INTEGER PRIMARY KEY, note TEXT); "
            "INSERT INTO codex_db_smoke_tmp(id, note) VALUES (1, 'smoke-ok'); "
            "SELECT note FROM codex_db_smoke_tmp WHERE id = 1; "
            "ROLLBACK;"
        ),
    )
    checks["temp_write_read"] = "PASS" if ok and "smoke-ok" in out else "FAIL"
    if checks["temp_write_read"] != "PASS":
        violations.append(
            Violation(
                code="TEMP_WRITE_READ_FAILED",
                message="temp table insert/read check failed",
                details=out,
            )
        )

    return violations, checks


def render_text(payload: dict) -> str:
    lines = [
        "db_smoke_test",
        f"status={payload['status']}",
        f"reason_code={payload['reason_code']}",
        f"remediation_hint={payload['remediation_hint']}",
        f"method={payload['method']}",
        f"host={payload['host']}",
        f"port={payload['port']}",
        f"database={payload['database']}",
        f"docker_preflight_status={payload['docker_preflight_status']}",
        f"select_1={payload['checks'].get('select_1', 'UNKNOWN')}",
        f"vector_extension={payload['checks'].get('vector_extension', 'UNKNOWN')}",
        f"expected_tables={payload['checks'].get('expected_tables', 'UNKNOWN')}",
        f"temp_write_read={payload['checks'].get('temp_write_read', 'UNKNOWN')}",
        f"violation_count={payload['violation_count']}",
    ]
    for violation in payload["violations"]:
        lines.append(f"- [{violation['code']}] {violation['message']} :: {violation['details']}")
    return "\n".join(lines) + "\n"


def write_output(path: str | None, content: str) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def make_payload(
    *,
    status: str,
    reason_code: str,
    method: str,
    host: str,
    port: int,
    database: str,
    expected_tables: list[str],
    docker_preflight_status: str,
    checks: dict[str, str],
    violations: list[Violation],
) -> dict:
    return {
        "status": status,
        "reason_code": reason_code,
        "remediation_hint": REMEDIATION_HINTS.get(reason_code, REMEDIATION_HINTS[REASON_UNKNOWN]),
        "method": method,
        "host": host,
        "port": port,
        "database": database,
        "expected_tables": expected_tables,
        "docker_preflight_status": docker_preflight_status,
        "checks": checks,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }


def execute(args: argparse.Namespace) -> dict:
    host, port, database = resolve_connection(args)
    expected_tables = sorted(set(args.expected_tables or list(DEFAULT_EXPECTED_TABLES)))
    driver = detect_driver_module()
    method = args.method
    if method == "auto":
        method = "driver" if driver else "docker-exec"

    violations: list[Violation] = []
    checks: dict[str, str] = {}
    reason_code = REASON_NONE
    status = STATUS_PASS
    docker_preflight_status = "NOT_REQUIRED"

    if method == "driver":
        if not driver:
            reason_code = REASON_DRIVER_NOT_AVAILABLE
            violations.append(
                Violation(
                    code=REASON_DRIVER_NOT_AVAILABLE,
                    message="python postgres driver is not installed",
                    details="install psycopg or run with --method docker-exec",
                )
            )
            status = STATUS_FAIL
        else:
            try:
                violations, checks = run_checks_with_driver(
                    driver=driver,
                    host=host,
                    port=port,
                    database=database,
                    user=args.user,
                    password=args.password,
                    expected_tables=expected_tables,
                )
                if violations:
                    reason_code = REASON_CHECK_FAILED
                    status = STATUS_FAIL
            except Exception as exc:  # pragma: no cover - defensive path
                reason_code = REASON_DRIVER_CONNECTION_FAILED
                violations = [
                    Violation(
                        code=REASON_DRIVER_CONNECTION_FAILED,
                        message="driver-based DB smoke test failed",
                        details=normalize_text(str(exc)),
                    )
                ]
                status = STATUS_FAIL

    elif method == "docker-exec":
        compose_file = Path(args.compose_file)
        docker_ok, docker_preflight_output = run_docker_preflight()
        if docker_ok:
            docker_preflight_status = "PASS"
        else:
            docker_preflight_status = "FAIL"
            reason_code = classify_docker_failure(docker_preflight_output)
            violations.append(
                Violation(
                    code=reason_code,
                    message="docker preflight failed",
                    details=docker_preflight_output,
                )
            )
            if args.docker_unavailable_policy == "skipped":
                status = STATUS_SKIPPED
            else:
                status = STATUS_FAIL
            return make_payload(
                status=status,
                reason_code=reason_code,
                method=method,
                host=host,
                port=port,
                database=database,
                expected_tables=expected_tables,
                docker_preflight_status=docker_preflight_status,
                checks=checks,
                violations=violations,
            )

        if not compose_file.exists():
            reason_code = REASON_COMPOSE_FILE_MISSING
            violations.append(
                Violation(
                    code=REASON_COMPOSE_FILE_MISSING,
                    message="compose file does not exist",
                    details=compose_file.as_posix(),
                )
            )
            status = STATUS_FAIL
        else:
            if args.auto_up:
                up_proc = run_subprocess(
                    [
                        "docker",
                        "compose",
                        "-f",
                        str(compose_file),
                        "up",
                        "-d",
                        args.compose_service,
                    ]
                )
                if up_proc.returncode != 0:
                    compose_output = normalize_text((up_proc.stdout or "") + "\n" + (up_proc.stderr or ""))
                    reason_code = REASON_DOCKER_COMPOSE_UP_FAILED
                    violations.append(
                        Violation(
                            code=REASON_DOCKER_COMPOSE_UP_FAILED,
                            message="failed to start postgres service",
                            details=compose_output,
                        )
                    )
            if not violations:
                try:
                    violations, checks = run_checks_with_docker_exec(
                        compose_file=compose_file,
                        compose_service=args.compose_service,
                        user=args.user,
                        database=database,
                        password=args.password,
                        expected_tables=expected_tables,
                    )
                    if violations:
                        reason_code = REASON_CHECK_FAILED
                        status = STATUS_FAIL
                except Exception as exc:  # pragma: no cover - defensive path
                    reason_code = REASON_DOCKER_EXEC_FAILED
                    violations = [
                        Violation(
                            code=REASON_DOCKER_EXEC_FAILED,
                            message="docker-exec DB smoke test failed",
                            details=normalize_text(str(exc)),
                        )
                    ]
                    status = STATUS_FAIL

    else:
        reason_code = REASON_METHOD_INVALID
        violations.append(
            Violation(
                code=REASON_METHOD_INVALID,
                message="unsupported method",
                details=method,
            )
        )
        status = STATUS_FAIL

    if status == STATUS_PASS and violations:
        status = STATUS_FAIL

    if reason_code == REASON_NONE and status != STATUS_PASS:
        reason_code = REASON_CHECK_FAILED

    return make_payload(
        status=status,
        reason_code=reason_code,
        method=method,
        host=host,
        port=port,
        database=database,
        expected_tables=expected_tables,
        docker_preflight_status=docker_preflight_status,
        checks=checks,
        violations=violations,
    )


def main() -> int:
    args = parse_args()
    try:
        payload = execute(args)
    except Exception as exc:  # pragma: no cover - always-write safety net
        host, port, database = resolve_connection(args)
        payload = make_payload(
            status=STATUS_FAIL,
            reason_code=REASON_UNEXPECTED_ERROR,
            method=args.method,
            host=host,
            port=port,
            database=database,
            expected_tables=sorted(set(args.expected_tables or list(DEFAULT_EXPECTED_TABLES))),
            docker_preflight_status="UNKNOWN",
            checks={},
            violations=[
                Violation(
                    code=REASON_UNEXPECTED_ERROR,
                    message="unexpected exception in db_smoke_test",
                    details=normalize_text(str(exc)),
                )
            ],
        )

    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_output(args.output_txt, text_report)
    write_output(args.output_json, json_report)
    sys.stdout.write(text_report)
    if payload["status"] in {STATUS_PASS, STATUS_SKIPPED}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
