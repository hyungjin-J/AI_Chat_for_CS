#!/usr/bin/env python3
"""Backup/restore rehearsal for deterministic DB recoverability checks."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_COMPOSE_FILE = "infra/docker-compose.yml"
DEFAULT_ARTIFACT_DIR = "docs/review/mvp_verification_pack/artifacts"
DEFAULT_DUMP_DIR = "tmp/db_backup_restore"
DEFAULT_DB = "aichatbot"
DEFAULT_DB_USER = "aichatbot"
DEFAULT_DB_PASSWORD = "local-dev-only-password"
DEFAULT_POSTGRES_SERVICE = "postgres"
DEFAULT_REDIS_SERVICE = "redis"

DUMP_CONTAINER_PATH = "/tmp/db_backup_restore_source.dump"
RESTORE_CONTAINER_PATH = "/tmp/db_backup_restore_target.dump"

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"


@dataclass
class Violation:
    code: str
    message: str
    details: str


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class RehearsalFailure(RuntimeError):
    def __init__(self, violation: Violation):
        super().__init__(violation.message)
        self.violation = violation


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def default_artifact_date() -> str:
    return utc_now().strftime("%Y%m%d")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DB backup/restore rehearsal (clean volume path)")
    parser.add_argument("--compose-file", default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--postgres-service", default=DEFAULT_POSTGRES_SERVICE)
    parser.add_argument("--redis-service", default=DEFAULT_REDIS_SERVICE)
    parser.add_argument("--database", default=DEFAULT_DB)
    parser.add_argument("--db-user", default=DEFAULT_DB_USER)
    parser.add_argument("--db-password", default=DEFAULT_DB_PASSWORD)
    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--artifact-date", default=default_artifact_date())
    parser.add_argument("--output-txt")
    parser.add_argument("--output-json")
    parser.add_argument("--dump-dir", default=DEFAULT_DUMP_DIR)
    parser.add_argument("--keep-dump", action="store_true")
    parser.add_argument("--skip-flyway-validate", action="store_true")
    parser.add_argument("--skip-cleanup", action="store_true")
    parser.add_argument("--ci", action="store_true")
    return parser.parse_args(argv)


def run_command(command: list[str], cwd: Path | None = None) -> CommandResult:
    proc = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return CommandResult(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def summarize_output(result: CommandResult, limit: int = 1600) -> str:
    merged = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
    if not merged:
        return "(no output)"
    if len(merged) <= limit:
        return merged
    return merged[: limit - 3] + "..."


def command_str(command: list[str]) -> str:
    return " ".join(command)


def compose_base(compose_file: str) -> list[str]:
    return ["docker", "compose", "-f", compose_file]


def build_flyway_command(args: argparse.Namespace, action: str) -> list[str]:
    return [
        *compose_base(args.compose_file),
        "--profile",
        "db-tools",
        "run",
        "--rm",
        "flyway",
        f"-url=jdbc:postgresql://{args.postgres_service}:5432/{args.database}",
        f"-user={args.db_user}",
        f"-password={args.db_password}",
        "-connectRetries=30",
        "-locations=filesystem:/flyway/sql,filesystem:/flyway/sql-postgresql",
        action,
    ]


def execute_checked(
    check_name: str,
    command: list[str],
    checks: dict[str, dict[str, str]],
    fail_code: str,
    fail_message: str,
) -> CommandResult:
    result = run_command(command)
    if result.returncode != 0:
        details = f"command={command_str(command)}\n{summarize_output(result)}"
        checks[check_name] = {"status": "FAIL", "details": details}
        raise RehearsalFailure(Violation(code=fail_code, message=fail_message, details=details))
    details = f"command={command_str(command)}"
    checks[check_name] = {"status": "PASS", "details": details}
    return result


def run_psql_scalar(
    args: argparse.Namespace,
    sql: str,
) -> tuple[bool, str, str]:
    command = [
        *compose_base(args.compose_file),
        "exec",
        "-T",
        "-e",
        f"PGPASSWORD={args.db_password}",
        args.postgres_service,
        "psql",
        "-U",
        args.db_user,
        "-d",
        args.database,
        "-v",
        "ON_ERROR_STOP=1",
        "-At",
        "-c",
        sql,
    ]
    result = run_command(command)
    if result.returncode != 0:
        return False, "", f"command={command_str(command)}\n{summarize_output(result)}"
    return True, result.stdout.strip(), ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def render_text(payload: dict) -> str:
    lines = [
        "db_backup_restore_rehearsal",
        f"status={payload['status']}",
        f"artifact_date={payload['artifact_date']}",
        f"started_at_utc={payload['started_at_utc']}",
        f"finished_at_utc={payload['finished_at_utc']}",
        f"duration_ms={payload['duration_ms']}",
        f"compose_file={payload['compose_file']}",
        f"database={payload['database']}",
        f"dump_path={payload['dump_path']}",
        f"dump_sha256={payload['dump_sha256']}",
        f"violation_count={payload['violation_count']}",
    ]
    for name, result in payload["checks"].items():
        lines.append(f"check.{name}={result['status']} :: {result['details']}")
    for item in payload["violations"]:
        lines.append(f"- [{item['code']}] {item['message']} :: {item['details']}")
    return "\n".join(lines) + "\n"


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def execute_rehearsal(args: argparse.Namespace) -> dict:
    started_at = utc_now()
    started_mono = time.monotonic()

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    dump_dir = Path(args.dump_dir)
    dump_dir.mkdir(parents=True, exist_ok=True)

    dump_path = dump_dir / f"db_backup_restore_{args.artifact_date}.dump"
    smoke_txt = dump_dir / f"db_smoke_after_restore_{args.artifact_date}.txt"
    smoke_json = dump_dir / f"db_smoke_after_restore_{args.artifact_date}.json"

    checks: dict[str, dict[str, str]] = {}
    violations: list[Violation] = []
    dump_sha256 = ""

    try:
        execute_checked(
            "compose_down_source",
            [*compose_base(args.compose_file), "down", "-v"],
            checks,
            "COMPOSE_DOWN_SOURCE_FAILED",
            "failed to reset source volume before rehearsal",
        )

        up_services = [args.postgres_service]
        if args.redis_service and args.redis_service not in up_services:
            up_services.append(args.redis_service)
        execute_checked(
            "compose_up_source",
            [*compose_base(args.compose_file), "up", "-d", *up_services],
            checks,
            "COMPOSE_UP_SOURCE_FAILED",
            "failed to start source postgres/redis",
        )

        execute_checked(
            "flyway_migrate_source",
            build_flyway_command(args, "migrate"),
            checks,
            "FLYWAY_MIGRATE_FAILED",
            "flyway migrate failed on source instance",
        )

        execute_checked(
            "pg_dump_source",
            [
                *compose_base(args.compose_file),
                "exec",
                "-T",
                "-e",
                f"PGPASSWORD={args.db_password}",
                args.postgres_service,
                "pg_dump",
                "-U",
                args.db_user,
                "-d",
                args.database,
                "-F",
                "c",
                "-f",
                DUMP_CONTAINER_PATH,
            ],
            checks,
            "PG_DUMP_FAILED",
            "pg_dump failed on source instance",
        )

        execute_checked(
            "pg_dump_copy_to_host",
            [
                *compose_base(args.compose_file),
                "cp",
                f"{args.postgres_service}:{DUMP_CONTAINER_PATH}",
                str(dump_path),
            ],
            checks,
            "PG_DUMP_COPY_FAILED",
            "failed to copy pg_dump file to host",
        )

        if not dump_path.exists():
            raise RehearsalFailure(
                Violation(
                    code="DUMP_FILE_MISSING",
                    message="dump file missing after docker cp",
                    details=dump_path.as_posix(),
                )
            )
        dump_sha256 = sha256_file(dump_path)
        checks["dump_sha256"] = {"status": "PASS", "details": dump_sha256}

        execute_checked(
            "compose_down_after_dump",
            [*compose_base(args.compose_file), "down", "-v"],
            checks,
            "COMPOSE_DOWN_AFTER_DUMP_FAILED",
            "failed to destroy source volume after dump",
        )

        execute_checked(
            "compose_up_restore_target",
            [*compose_base(args.compose_file), "up", "-d", *up_services],
            checks,
            "COMPOSE_UP_TARGET_FAILED",
            "failed to start restore target postgres/redis",
        )

        execute_checked(
            "restore_copy_to_container",
            [
                *compose_base(args.compose_file),
                "cp",
                str(dump_path),
                f"{args.postgres_service}:{RESTORE_CONTAINER_PATH}",
            ],
            checks,
            "RESTORE_COPY_FAILED",
            "failed to copy dump file into target postgres container",
        )

        execute_checked(
            "pg_restore_target",
            [
                *compose_base(args.compose_file),
                "exec",
                "-T",
                "-e",
                f"PGPASSWORD={args.db_password}",
                args.postgres_service,
                "pg_restore",
                "-U",
                args.db_user,
                "-d",
                args.database,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                RESTORE_CONTAINER_PATH,
            ],
            checks,
            "PG_RESTORE_FAILED",
            "pg_restore failed on restore target",
        )

        if args.skip_flyway_validate:
            checks["flyway_validate_target"] = {"status": "SKIPPED", "details": "skip flag enabled"}
        else:
            execute_checked(
                "flyway_validate_target",
                build_flyway_command(args, "validate"),
                checks,
                "FLYWAY_VALIDATE_FAILED",
                "flyway validate failed after restore",
            )

        smoke_command = [
            sys.executable,
            "scripts/db_smoke_test.py",
            "--method",
            "docker-exec",
            "--compose-file",
            args.compose_file,
            "--compose-service",
            args.postgres_service,
            "--database",
            args.database,
            "--user",
            args.db_user,
            "--password",
            args.db_password,
            "--output-txt",
            str(smoke_txt),
            "--output-json",
            str(smoke_json),
        ]
        smoke_result = execute_checked(
            "db_smoke_after_restore_exec",
            smoke_command,
            checks,
            "DB_SMOKE_EXEC_FAILED",
            "db_smoke_test.py execution failed after restore",
        )
        del smoke_result

        try:
            smoke_payload = json.loads(smoke_json.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RehearsalFailure(
                Violation(
                    code="DB_SMOKE_JSON_INVALID",
                    message="db_smoke_test output json is missing or invalid",
                    details=str(exc),
                )
            ) from exc
        smoke_status = str(smoke_payload.get("status", "")).upper()
        if smoke_status != "PASS":
            raise RehearsalFailure(
                Violation(
                    code="DB_SMOKE_FAILED",
                    message="db_smoke_test reported non-pass status",
                    details=f"status={smoke_payload.get('status')}",
                )
            )
        checks["db_smoke_after_restore"] = {"status": "PASS", "details": "status=PASS"}

        core_queries = [
            (
                "seed_demo_tenant_exists",
                "SELECT COUNT(*) FROM tb_tenant WHERE tenant_key = 'demo-tenant';",
                1,
                "==",
            ),
            (
                "role_taxonomy_exists",
                (
                    "SELECT COUNT(DISTINCT role_code) FROM tb_role "
                    f"WHERE tenant_id = '{DEMO_TENANT_ID}' "
                    "AND role_code IN ('AGENT','CUSTOMER','ADMIN','OPS','SYSTEM');"
                ),
                5,
                "==",
            ),
            (
                "seed_users_minimum",
                (
                    "SELECT COUNT(*) FROM tb_user "
                    f"WHERE tenant_id = '{DEMO_TENANT_ID}' "
                    "AND login_id IN ('agent1','admin1','ops1');"
                ),
                3,
                ">=",
            ),
            (
                "kb_seed_minimum",
                (
                    "SELECT COUNT(*) FROM tb_kb_chunk_embedding "
                    f"WHERE tenant_id = '{DEMO_TENANT_ID}';"
                ),
                2,
                ">=",
            ),
            (
                "flyway_no_failures",
                "SELECT COUNT(*) FROM flyway_schema_history WHERE success = false;",
                0,
                "==",
            ),
            (
                "foundation_index_exists",
                (
                    "SELECT COUNT(*) FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND indexname = 'idx_tb_message_tenant_conversation_created_at';"
                ),
                1,
                "==",
            ),
        ]

        for check_name, sql, expected, op in core_queries:
            ok, raw_value, error_detail = run_psql_scalar(args, sql)
            if not ok:
                checks[check_name] = {"status": "FAIL", "details": error_detail}
                violations.append(
                    Violation(
                        code="CORE_QUERY_EXEC_FAILED",
                        message=f"core query execution failed: {check_name}",
                        details=error_detail,
                    )
                )
                continue
            try:
                observed = int(raw_value.strip())
            except ValueError:
                details = f"raw_value={raw_value!r}"
                checks[check_name] = {"status": "FAIL", "details": details}
                violations.append(
                    Violation(
                        code="CORE_QUERY_PARSE_FAILED",
                        message=f"core query returned non-integer: {check_name}",
                        details=details,
                    )
                )
                continue

            passed = observed == expected if op == "==" else observed >= expected
            detail = f"observed={observed} expected={op}{expected}"
            checks[check_name] = {"status": "PASS" if passed else "FAIL", "details": detail}
            if not passed:
                violations.append(
                    Violation(
                        code="CORE_QUERY_FAILED",
                        message=f"core query expectation failed: {check_name}",
                        details=detail,
                    )
                )

    except RehearsalFailure as failure:
        violations.append(failure.violation)
    except Exception as exc:  # pragma: no cover - defensive guard
        violations.append(
            Violation(
                code="UNHANDLED_EXCEPTION",
                message="unexpected exception during backup/restore rehearsal",
                details=str(exc),
            )
        )
    finally:
        if args.skip_cleanup:
            checks["compose_down_final"] = {"status": "SKIPPED", "details": "skip flag enabled"}
        else:
            cleanup_command = [*compose_base(args.compose_file), "down", "-v"]
            cleanup_result = run_command(cleanup_command)
            if cleanup_result.returncode == 0:
                checks["compose_down_final"] = {"status": "PASS", "details": command_str(cleanup_command)}
            else:
                detail = f"command={command_str(cleanup_command)}\n{summarize_output(cleanup_result)}"
                checks["compose_down_final"] = {"status": "FAIL", "details": detail}
                violations.append(
                    Violation(
                        code="COMPOSE_DOWN_FINAL_FAILED",
                        message="final compose down -v failed",
                        details=detail,
                    )
                )

        if args.keep_dump:
            checks["dump_retention"] = {"status": "KEPT", "details": dump_path.as_posix()}
        else:
            if dump_path.exists():
                try:
                    dump_path.unlink()
                    checks["dump_retention"] = {"status": "REMOVED", "details": dump_path.as_posix()}
                except OSError as exc:
                    checks["dump_retention"] = {"status": "FAIL", "details": str(exc)}
                    violations.append(
                        Violation(
                            code="DUMP_DELETE_FAILED",
                            message="failed to delete dump file",
                            details=str(exc),
                        )
                    )
            else:
                checks["dump_retention"] = {"status": "REMOVED", "details": "already absent"}

            if dump_dir.exists():
                for temp_path in (Path(RESTORE_CONTAINER_PATH).name, Path(DUMP_CONTAINER_PATH).name):
                    maybe_local = dump_dir / temp_path
                    if maybe_local.exists():
                        maybe_local.unlink()
                if not any(dump_dir.iterdir()):
                    try:
                        shutil.rmtree(dump_dir)
                    except OSError:
                        pass

    finished_at = utc_now()
    duration_ms = int((time.monotonic() - started_mono) * 1000)

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "artifact_date": args.artifact_date,
        "started_at_utc": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at_utc": finished_at.isoformat().replace("+00:00", "Z"),
        "duration_ms": duration_ms,
        "compose_file": args.compose_file,
        "database": args.database,
        "postgres_service": args.postgres_service,
        "redis_service": args.redis_service,
        "dump_path": dump_path.as_posix(),
        "dump_sha256": dump_sha256,
        "checks": checks,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    artifact_dir = Path(args.artifact_dir)
    output_txt = Path(args.output_txt) if args.output_txt else artifact_dir / f"db_backup_restore_rehearsal_{args.artifact_date}.txt"
    output_json = Path(args.output_json) if args.output_json else artifact_dir / f"db_backup_restore_rehearsal_{args.artifact_date}.json"

    payload = execute_rehearsal(args)
    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    write_output(output_txt, text_report)
    write_output(output_json, json_report)

    sys.stdout.write(text_report)
    if args.ci:
        return 0 if payload["status"] == "PASS" else 1
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

