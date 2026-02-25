#!/usr/bin/env python3
"""PostgreSQL local readiness smoke test (DB boot, schema, pgvector, basic query path)."""

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
    parser.add_argument("--user", default=os.environ.get("DB_USERNAME", os.environ.get("POSTGRES_USER", "aichatbot")))
    parser.add_argument("--password", default=os.environ.get("DB_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "local-dev-only-password")))
    parser.add_argument("--method", choices=("auto", "driver", "docker-exec"), default="auto")
    parser.add_argument("--auto-up", action="store_true", help="Run `docker compose up -d <service>` before checks in docker-exec mode")
    parser.add_argument("--compose-file", default="infra/docker-compose.yml")
    parser.add_argument("--compose-service", default="postgres")
    parser.add_argument("--expected-table", dest="expected_tables", action="append")
    parser.add_argument("--output-txt")
    parser.add_argument("--output-json")
    return parser.parse_args()


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
            # Keep explicit host/port/database fallback deterministic.
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
    text = (proc.stdout or "").strip()
    if not success and proc.stderr:
        text = f"{text}\n{proc.stderr.strip()}".strip()
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
        violations.append(
            Violation(
                code="SELECT_1_FAILED",
                message="SELECT 1 failed",
                details=out,
            )
        )

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
        f"method={payload['method']}",
        f"host={payload['host']}",
        f"port={payload['port']}",
        f"database={payload['database']}",
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


def main() -> int:
    args = parse_args()
    host, port, database = resolve_connection(args)
    expected_tables = sorted(set(args.expected_tables or list(DEFAULT_EXPECTED_TABLES)))

    driver = detect_driver_module()
    method = args.method
    if method == "auto":
        method = "driver" if driver else "docker-exec"

    violations: list[Violation] = []
    checks: dict[str, str] = {}

    if method == "driver":
        if not driver:
            violations.append(
                Violation(
                    code="DRIVER_NOT_AVAILABLE",
                    message="python postgres driver is not installed",
                    details="install psycopg or run with --method docker-exec",
                )
            )
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
            except Exception as exc:  # pragma: no cover - defensive path
                violations = [
                    Violation(
                        code="DRIVER_CONNECTION_FAILED",
                        message="driver-based DB smoke test failed",
                        details=str(exc),
                    )
                ]
    elif method == "docker-exec":
        compose_file = Path(args.compose_file)
        if not compose_file.exists():
            violations.append(
                Violation(
                    code="COMPOSE_FILE_MISSING",
                    message="compose file does not exist",
                    details=compose_file.as_posix(),
                )
            )
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
                    violations.append(
                        Violation(
                            code="DOCKER_COMPOSE_UP_FAILED",
                            message="failed to start postgres service",
                            details=(up_proc.stderr or up_proc.stdout or "").strip(),
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
                except Exception as exc:  # pragma: no cover - defensive path
                    violations = [
                        Violation(
                            code="DOCKER_EXEC_FAILED",
                            message="docker-exec DB smoke test failed",
                            details=str(exc),
                        )
                    ]
    else:
        violations.append(
            Violation(
                code="METHOD_INVALID",
                message="unsupported method",
                details=method,
            )
        )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "method": method,
        "host": host,
        "port": port,
        "database": database,
        "expected_tables": expected_tables,
        "checks": checks,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }
    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    write_output(args.output_txt, text_report)
    write_output(args.output_json, json_report)

    sys.stdout.write(text_report)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
