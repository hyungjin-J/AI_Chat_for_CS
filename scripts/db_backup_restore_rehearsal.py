#!/usr/bin/env python3
"""Backup/restore rehearsal for deterministic DB recoverability checks."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
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

RTO_MINUTES = 60
RPO_HOURS = 24

SAFE_SEED_TABLE_EXCLUDE_TOKENS = (
    "audit",
    "billing",
    "citation",
    "conversation",
    "event",
    "export",
    "log",
    "message",
    "mfa",
    "ops",
    "rag",
    "role",
    "session",
    "stream",
    "user",
)

TEXT_TYPE_NAMES = {"character", "character varying", "text"}
INTEGER_TYPE_NAMES = {"smallint", "integer", "bigint"}
FLOAT_TYPE_NAMES = {"numeric", "real", "double precision", "decimal"}
BOOL_TYPE_NAMES = {"boolean"}
DATE_TYPE_NAMES = {"date"}
UUID_TYPE_NAMES = {"uuid"}

CORE_REQUIRED_TABLES = (
    "tb_tenant",
    "tb_user",
    "tb_message",
    "tb_kb_chunk_embedding",
    "flyway_schema_history",
)

SENSITIVE_REGEX_REPLACEMENTS = (
    (re.compile(r"(?i)(PGPASSWORD=)([^\s]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(--password\s+)([^\s]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(--db-password\s+)([^\s]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(-password=)([^\s]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(--password=)([^\s]+)"), r"\1***REDACTED***"),
    (
        re.compile(
            r"(?i)(\b(?:api[_-]?key|secret|token|access[_-]?token|refresh[_-]?token)\b\s*[:=]\s*)([^\s\"']+)"
        ),
        r"\1***REDACTED***",
    ),
)


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


@dataclass
class SeedPlan:
    table_name: str
    marker_column: str
    marker_value: str
    insert_sql: str
    verify_sql: str


@dataclass
class SeedExecution:
    strategy: str
    table_name: str | None
    inserted_row_count: int
    fallback_reason: str
    verify_sql: str | None


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


def mask_sensitive_text(text: str) -> str:
    sanitized = text
    for pattern, replacement in SENSITIVE_REGEX_REPLACEMENTS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def mask_command(command: list[str]) -> list[str]:
    masked: list[str] = []
    redact_next = False
    for token in command:
        if redact_next:
            masked.append("***REDACTED***")
            redact_next = False
            continue

        lowered = token.lower()
        if lowered in {"--password", "--db-password"}:
            masked.append(token)
            redact_next = True
            continue

        if token.startswith("PGPASSWORD="):
            masked.append("PGPASSWORD=***REDACTED***")
            continue
        if lowered.startswith("-password="):
            masked.append("-password=***REDACTED***")
            continue
        if lowered.startswith("--password="):
            masked.append("--password=***REDACTED***")
            continue

        masked.append(mask_sensitive_text(token))

    return masked


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
    merged = mask_sensitive_text(merged)
    if not merged:
        return "(no output)"
    if len(merged) <= limit:
        return merged
    return merged[: limit - 3] + "..."


def command_str(command: list[str]) -> str:
    return " ".join(mask_command(command))


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


def wait_for_postgres_ready(
    args: argparse.Namespace,
    checks: dict[str, dict[str, str]],
    check_name: str,
    fail_code: str,
    fail_message: str,
    attempts: int = 30,
    sleep_seconds: float = 1.0,
) -> None:
    probe_command = [
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
        "SELECT 1;",
    ]
    last_details = f"command={command_str(probe_command)}"
    for attempt in range(1, attempts + 1):
        result = run_command(probe_command)
        if result.returncode == 0 and "1" in result.stdout.strip().split():
            checks[check_name] = {
                "status": "PASS",
                "details": f"attempt={attempt} command={command_str(probe_command)}",
            }
            return
        last_details = (
            f"attempt={attempt} command={command_str(probe_command)}\n{summarize_output(result)}"
        )
        time.sleep(sleep_seconds)

    checks[check_name] = {"status": "FAIL", "details": last_details}
    raise RehearsalFailure(Violation(code=fail_code, message=fail_message, details=last_details))


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


def run_psql_json(args: argparse.Namespace, sql: str) -> tuple[bool, list[dict[str, object]], str]:
    ok, raw, error_detail = run_psql_scalar(args, sql)
    if not ok:
        return False, [], error_detail
    payload = raw.strip()
    if payload == "":
        return True, [], ""

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        details = f"json decode failed: {exc} raw={mask_sensitive_text(payload)!r}"
        return False, [], details

    if not isinstance(parsed, list):
        return False, [], f"expected JSON list, got type={type(parsed).__name__}"

    normalized: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            normalized.append(item)
    return True, normalized, ""


def sql_quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def is_table_excluded(table_name: str) -> bool:
    lowered = table_name.lower()
    if lowered == "flyway_schema_history":
        return True
    if lowered.startswith("pg_"):
        return True
    return any(token in lowered for token in SAFE_SEED_TABLE_EXCLUDE_TOKENS)


def choose_marker_column(columns: list[dict[str, object]]) -> str | None:
    preferred_order = ["table_name", "name", "code", "status", "note", "description"]
    for preferred in preferred_order:
        for column in columns:
            if str(column.get("column_name")) == preferred:
                data_type = str(column.get("data_type", "")).lower()
                if data_type in TEXT_TYPE_NAMES:
                    return preferred

    for column in columns:
        data_type = str(column.get("data_type", "")).lower()
        if data_type in TEXT_TYPE_NAMES:
            return str(column.get("column_name"))
    return None


def default_value_sql(data_type: str, marker_value: str) -> str | None:
    lowered = data_type.lower()
    now = utc_now()

    if lowered in TEXT_TYPE_NAMES:
        return sql_quote_literal(marker_value)
    if lowered in INTEGER_TYPE_NAMES:
        return "1"
    if lowered in FLOAT_TYPE_NAMES:
        return "1"
    if lowered in BOOL_TYPE_NAMES:
        return "TRUE"
    if lowered in DATE_TYPE_NAMES:
        return sql_quote_literal(now.date().isoformat()) + "::date"
    if lowered == "timestamp without time zone":
        timestamp_value = now.replace(tzinfo=None).isoformat(timespec="seconds")
        return sql_quote_literal(timestamp_value) + "::timestamp"
    if lowered == "timestamp with time zone":
        return sql_quote_literal(now.isoformat(timespec="seconds")) + "::timestamptz"
    if lowered in UUID_TYPE_NAMES:
        generated = str(uuid.uuid5(uuid.NAMESPACE_DNS, marker_value + "-uuid"))
        return sql_quote_literal(generated) + "::uuid"
    return None


def build_safe_seed_plan(
    table_columns: dict[str, list[dict[str, object]]],
    fk_tables: set[str],
    marker_value: str,
) -> tuple[SeedPlan | None, str]:
    def table_rank(table_name: str) -> tuple[int, str]:
        if table_name in {"tb_data_retention_policy", "tb_partition_plan"}:
            return 0, table_name
        return 1, table_name

    for table_name in sorted(table_columns.keys(), key=table_rank):
        if is_table_excluded(table_name):
            continue
        if table_name in fk_tables:
            continue

        columns = table_columns.get(table_name, [])
        if not columns:
            continue

        marker_column = choose_marker_column(columns)
        if not marker_column:
            continue

        required_columns: list[dict[str, object]] = []
        for column in columns:
            nullable = str(column.get("is_nullable", "")).upper() == "YES"
            has_default = bool(column.get("column_default"))
            if not nullable and not has_default:
                required_columns.append(column)

        insert_columns: list[str] = []
        insert_values: list[str] = []
        marker_applied = False
        unsupported = False

        for column in required_columns:
            column_name = str(column.get("column_name"))
            data_type = str(column.get("data_type", "")).lower()
            if column_name == marker_column:
                value_sql = sql_quote_literal(marker_value)
                marker_applied = True
            else:
                value_sql = default_value_sql(data_type, marker_value)
            if value_sql is None:
                unsupported = True
                break
            insert_columns.append(sql_quote_identifier(column_name))
            insert_values.append(value_sql)

        if unsupported:
            continue

        if not marker_applied:
            marker_column_meta = next((col for col in columns if str(col.get("column_name")) == marker_column), None)
            marker_data_type = str((marker_column_meta or {}).get("data_type", "")).lower()
            marker_sql = default_value_sql(marker_data_type, marker_value)
            if marker_sql is None:
                continue
            insert_columns.append(sql_quote_identifier(marker_column))
            insert_values.append(marker_sql)

        if not insert_columns:
            continue

        table_sql = sql_quote_identifier(table_name)
        insert_sql = (
            f"INSERT INTO {table_sql} ({', '.join(insert_columns)}) "
            f"VALUES ({', '.join(insert_values)});"
        )
        verify_sql = (
            "SELECT COUNT(*) FROM "
            f"{table_sql} WHERE {sql_quote_identifier(marker_column)} = {sql_quote_literal(marker_value)};"
        )
        return (
            SeedPlan(
                table_name=table_name,
                marker_column=marker_column,
                marker_value=marker_value,
                insert_sql=insert_sql,
                verify_sql=verify_sql,
            ),
            "",
        )

    return None, "no safe insert target found from information_schema"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def discover_safe_seed_plan(args: argparse.Namespace, checks: dict[str, dict[str, str]]) -> tuple[SeedPlan | None, str]:
    column_sql = """
SELECT COALESCE(
    json_agg(row_to_json(meta) ORDER BY meta.table_name, meta.ordinal_position)::text,
    '[]'
)
FROM (
    SELECT
        c.table_name,
        c.column_name,
        c.data_type,
        c.is_nullable,
        c.column_default,
        c.ordinal_position
    FROM information_schema.columns AS c
    JOIN information_schema.tables AS t
      ON t.table_schema = c.table_schema
     AND t.table_name = c.table_name
    WHERE c.table_schema = 'public'
      AND t.table_type = 'BASE TABLE'
) AS meta;
""".strip()

    fk_sql = """
SELECT COALESCE(
    json_agg(row_to_json(meta) ORDER BY meta.table_name)::text,
    '[]'
)
FROM (
    SELECT DISTINCT tc.table_name
    FROM information_schema.table_constraints AS tc
    WHERE tc.table_schema = 'public'
      AND tc.constraint_type = 'FOREIGN KEY'
) AS meta;
""".strip()

    ok_columns, column_rows, column_error = run_psql_json(args, column_sql)
    if not ok_columns:
        checks["safe_seed_discovery"] = {"status": "FAIL", "details": column_error}
        return None, f"metadata query failed: {column_error}"

    ok_fk, fk_rows, fk_error = run_psql_json(args, fk_sql)
    if not ok_fk:
        checks["safe_seed_discovery"] = {"status": "FAIL", "details": fk_error}
        return None, f"foreign key query failed: {fk_error}"

    table_columns: dict[str, list[dict[str, object]]] = {}
    for row in column_rows:
        table_name = str(row.get("table_name", ""))
        if not table_name:
            continue
        table_columns.setdefault(table_name, []).append(row)

    fk_tables = {str(item.get("table_name", "")) for item in fk_rows if str(item.get("table_name", ""))}
    marker_value = f"rehearsal_{args.artifact_date}_{uuid.uuid4().hex[:8]}"
    plan, reason = build_safe_seed_plan(table_columns, fk_tables, marker_value)

    discovery_details = (
        f"table_count={len(table_columns)} fk_table_count={len(fk_tables)} "
        f"selected_table={(plan.table_name if plan else '-')} "
        f"reason={(reason if not plan else '-')}"
    )
    checks["safe_seed_discovery"] = {"status": "PASS", "details": discovery_details}
    return plan, reason


def run_fallback_seed_checks(
    args: argparse.Namespace,
    checks: dict[str, dict[str, str]],
    reason: str,
) -> tuple[bool, str]:
    fallback_queries = [
        ("seed_fallback_flyway_history_rows", "SELECT COUNT(*) FROM flyway_schema_history;", 1, ">="),
        (
            "seed_fallback_vector_extension",
            "SELECT CASE WHEN EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN 1 ELSE 0 END;",
            1,
            "==",
        ),
        (
            "seed_fallback_core_tables",
            (
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                f"AND table_name IN ({', '.join(sql_quote_literal(name) for name in CORE_REQUIRED_TABLES)});"
            ),
            len(CORE_REQUIRED_TABLES),
            "==",
        ),
    ]

    failed_checks: list[str] = []
    for check_name, sql, expected, op in fallback_queries:
        ok, raw_value, error_detail = run_psql_scalar(args, sql)
        if not ok:
            checks[check_name] = {"status": "FAIL", "details": error_detail}
            failed_checks.append(check_name)
            continue
        try:
            observed = int(raw_value.strip())
        except ValueError:
            details = f"raw_value={mask_sensitive_text(raw_value)!r}"
            checks[check_name] = {"status": "FAIL", "details": details}
            failed_checks.append(check_name)
            continue

        passed = observed >= expected if op == ">=" else observed == expected
        details = f"observed={observed} expected={op}{expected}"
        checks[check_name] = {"status": "PASS" if passed else "FAIL", "details": details}
        if not passed:
            failed_checks.append(check_name)

    if failed_checks:
        detail = f"reason={reason} failed_checks={','.join(failed_checks)}"
        checks["safe_seed_fallback"] = {"status": "FAIL", "details": detail}
        return False, detail

    checks["safe_seed_fallback"] = {"status": "PASS", "details": f"reason={reason}"}
    return True, reason


def execute_seed_step(args: argparse.Namespace, checks: dict[str, dict[str, str]]) -> SeedExecution:
    plan, reason = discover_safe_seed_plan(args, checks)
    if not plan:
        fallback_ok, fallback_detail = run_fallback_seed_checks(args, checks, reason)
        if not fallback_ok:
            raise RehearsalFailure(
                Violation(
                    code="SAFE_SEED_FALLBACK_FAILED",
                    message="fallback validation failed when safe seed insertion was unavailable",
                    details=fallback_detail,
                )
            )
        return SeedExecution(
            strategy="fallback",
            table_name=None,
            inserted_row_count=0,
            fallback_reason=fallback_detail,
            verify_sql=None,
        )

    ok_insert, _, insert_error = run_psql_scalar(args, plan.insert_sql)
    if not ok_insert:
        fallback_reason = f"safe insert failed: {insert_error}"
        checks["safe_seed_insert_source"] = {"status": "FAIL", "details": fallback_reason}
        fallback_ok, fallback_detail = run_fallback_seed_checks(args, checks, fallback_reason)
        if not fallback_ok:
            raise RehearsalFailure(
                Violation(
                    code="SAFE_SEED_INSERT_AND_FALLBACK_FAILED",
                    message="safe seed insert failed and fallback validation also failed",
                    details=fallback_detail,
                )
            )
        return SeedExecution(
            strategy="fallback",
            table_name=None,
            inserted_row_count=0,
            fallback_reason=fallback_detail,
            verify_sql=None,
        )

    ok_verify, raw_value, verify_error = run_psql_scalar(args, plan.verify_sql)
    if not ok_verify:
        raise RehearsalFailure(
            Violation(
                code="SAFE_SEED_VERIFY_SOURCE_FAILED",
                message="failed to verify inserted safe seed row on source instance",
                details=verify_error,
            )
        )
    try:
        inserted_count = int(raw_value.strip())
    except ValueError as exc:
        raise RehearsalFailure(
            Violation(
                code="SAFE_SEED_VERIFY_PARSE_FAILED",
                message="safe seed source verification returned non-integer",
                details=f"raw_value={mask_sensitive_text(raw_value)!r}",
            )
        ) from exc

    if inserted_count < 1:
        raise RehearsalFailure(
            Violation(
                code="SAFE_SEED_VERIFY_SOURCE_EMPTY",
                message="safe seed row is missing immediately after source insert",
                details=f"table={plan.table_name} marker_column={plan.marker_column}",
            )
        )

    checks["safe_seed_insert_source"] = {
        "status": "PASS",
        "details": (
            f"table={plan.table_name} marker_column={plan.marker_column} "
            f"marker_value={plan.marker_value} inserted_rows={inserted_count}"
        ),
    }
    return SeedExecution(
        strategy="inserted",
        table_name=plan.table_name,
        inserted_row_count=inserted_count,
        fallback_reason="",
        verify_sql=plan.verify_sql,
    )


def verify_seed_after_restore(
    args: argparse.Namespace,
    checks: dict[str, dict[str, str]],
    seed_execution: SeedExecution,
) -> None:
    if seed_execution.strategy != "inserted" or not seed_execution.verify_sql:
        checks["safe_seed_restore_verify"] = {
            "status": "SKIPPED",
            "details": f"strategy={seed_execution.strategy}",
        }
        return

    ok, raw_value, error_detail = run_psql_scalar(args, seed_execution.verify_sql)
    if not ok:
        checks["safe_seed_restore_verify"] = {"status": "FAIL", "details": error_detail}
        raise RehearsalFailure(
            Violation(
                code="SAFE_SEED_RESTORE_VERIFY_EXEC_FAILED",
                message="failed to verify safe seed row after restore",
                details=error_detail,
            )
        )
    try:
        observed = int(raw_value.strip())
    except ValueError as exc:
        details = f"raw_value={mask_sensitive_text(raw_value)!r}"
        checks["safe_seed_restore_verify"] = {"status": "FAIL", "details": details}
        raise RehearsalFailure(
            Violation(
                code="SAFE_SEED_RESTORE_VERIFY_PARSE_FAILED",
                message="safe seed restore verification returned non-integer",
                details=details,
            )
        ) from exc

    details = f"observed={observed} expected=>=1"
    checks["safe_seed_restore_verify"] = {
        "status": "PASS" if observed >= 1 else "FAIL",
        "details": details,
    }
    if observed < 1:
        raise RehearsalFailure(
            Violation(
                code="SAFE_SEED_RESTORE_VERIFY_FAILED",
                message="safe seed row did not survive restore",
                details=details,
            )
        )


def render_text(payload: dict) -> str:
    lines = [
        "db_backup_restore_rehearsal",
        f"status={payload['status']}",
        f"artifact_date={payload['artifact_date']}",
        f"started_at_utc={payload['started_at_utc']}",
        f"finished_at_utc={payload['finished_at_utc']}",
        f"duration_ms={payload['duration_ms']}",
        f"rto_minutes={payload['rto_minutes']}",
        f"rpo_hours={payload['rpo_hours']}",
        f"compose_file={payload['compose_file']}",
        f"database={payload['database']}",
        f"dump_path={payload['dump_path']}",
        f"dump_sha256={payload['dump_sha256']}",
        f"dump_size_bytes={payload['dump_size_bytes']}",
        f"dump_created_at_utc={payload['dump_created_at_utc']}",
        f"seed_strategy={payload['seed_strategy']}",
        f"seed_table={payload['seed_table']}",
        f"seed_inserted_row_count={payload['seed_inserted_row_count']}",
        f"fallback_reason={payload['fallback_reason']}",
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
    dump_size_bytes = 0
    dump_created_at_utc = ""

    seed_execution = SeedExecution(
        strategy="fallback",
        table_name=None,
        inserted_row_count=0,
        fallback_reason="",
        verify_sql=None,
    )

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
        wait_for_postgres_ready(
            args=args,
            checks=checks,
            check_name="postgres_ready_source",
            fail_code="POSTGRES_READY_SOURCE_FAILED",
            fail_message="postgres did not become ready on source instance",
        )

        execute_checked(
            "flyway_migrate_source",
            build_flyway_command(args, "migrate"),
            checks,
            "FLYWAY_MIGRATE_FAILED",
            "flyway migrate failed on source instance",
        )

        seed_execution = execute_seed_step(args, checks)

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
        dump_size_bytes = dump_path.stat().st_size
        dump_created_at_utc = dt.datetime.fromtimestamp(
            dump_path.stat().st_mtime,
            tz=dt.timezone.utc,
        ).isoformat().replace("+00:00", "Z")
        checks["dump_sha256"] = {"status": "PASS", "details": dump_sha256}
        checks["dump_meta"] = {
            "status": "PASS",
            "details": f"size_bytes={dump_size_bytes} created_at_utc={dump_created_at_utc}",
        }

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
        wait_for_postgres_ready(
            args=args,
            checks=checks,
            check_name="postgres_ready_restore_target",
            fail_code="POSTGRES_READY_TARGET_FAILED",
            fail_message="postgres did not become ready on restore target",
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

        verify_seed_after_restore(args, checks, seed_execution)

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
                details = f"raw_value={mask_sensitive_text(raw_value)!r}"
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
                details=mask_sensitive_text(str(exc)),
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
                            details=mask_sensitive_text(str(exc)),
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
        "rto_minutes": RTO_MINUTES,
        "rpo_hours": RPO_HOURS,
        "compose_file": args.compose_file,
        "database": args.database,
        "postgres_service": args.postgres_service,
        "redis_service": args.redis_service,
        "dump_path": dump_path.as_posix(),
        "dump_sha256": dump_sha256,
        "dump_size_bytes": dump_size_bytes,
        "dump_created_at_utc": dump_created_at_utc,
        "seed_strategy": seed_execution.strategy,
        "seed_table": seed_execution.table_name,
        "seed_inserted_row_count": seed_execution.inserted_row_count,
        "fallback_reason": seed_execution.fallback_reason,
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
