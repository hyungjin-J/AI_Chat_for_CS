#!/usr/bin/env python3
"""Read-only verifier for tenant-scoped audit hash chain integrity."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_COMPOSE_FILE = "infra/docker-compose.yml"
DEFAULT_COMPOSE_SERVICE = "postgres"
DEFAULT_DB_NAME = "aichatbot"
DEFAULT_DB_USER = "aichatbot"
DEFAULT_DB_PASSWORD = "local-dev-only-password"
DEFAULT_DB_HOST = "127.0.0.1"
DEFAULT_DB_PORT = 5432
DEFAULT_LIMIT = 5000
DEFAULT_FAILURE_SAMPLE_LIMIT = 20
DEFAULT_ARTIFACT_DIR = "docs/review/mvp_verification_pack/artifacts"

MASK_PATTERNS = (
    (re.compile(r"(?i)(PGPASSWORD=)([^\s]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(--db-password\s+)([^\s]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(--password\s+)([^\s]+)"), r"\1***REDACTED***"),
    (
        re.compile(
            r"(?i)(\b(?:api[_-]?key|secret|token|access[_-]?token|refresh[_-]?token|cookie)\b\s*[:=]\s*)([^\s\"']+)"
        ),
        r"\1***REDACTED***",
    ),
)


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    details: str


@dataclass(frozen=True)
class ChainRow:
    audit_id: str
    chain_seq: int | None
    hash_prev: str | None
    hash_curr: str | None
    trace_id: str | None
    action_type: str | None
    target_type: str | None
    target_id: str | None
    before_json: str | None
    after_json: str | None
    created_at_epoch_ms: int


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify tenant-scoped audit chain (read-only)")
    parser.add_argument("--tenant-key", required=True)
    parser.add_argument("--from-utc", required=True)
    parser.add_argument("--to-utc", required=True)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--failure-sample-limit", type=int, default=DEFAULT_FAILURE_SAMPLE_LIMIT)

    parser.add_argument("--method", choices=("docker-exec", "local-psql"), default="docker-exec")
    parser.add_argument("--compose-file", default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--compose-service", default=DEFAULT_COMPOSE_SERVICE)
    parser.add_argument("--db-host", default=os.environ.get("DB_HOST", DEFAULT_DB_HOST))
    parser.add_argument("--db-port", type=int, default=int(os.environ.get("DB_PORT", str(DEFAULT_DB_PORT))))
    parser.add_argument("--database", default=os.environ.get("POSTGRES_DB", DEFAULT_DB_NAME))
    parser.add_argument("--db-user", default=os.environ.get("DB_USERNAME", os.environ.get("POSTGRES_USER", DEFAULT_DB_USER)))
    parser.add_argument(
        "--db-password",
        default=os.environ.get("DB_PASSWORD", os.environ.get("POSTGRES_PASSWORD", DEFAULT_DB_PASSWORD)),
    )

    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--output-txt")
    parser.add_argument("--output-json")
    return parser.parse_args()


def parse_utc(value: str, field_name: str) -> dt.datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO8601 UTC timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone offset (UTC recommended): {value}")
    return parsed.astimezone(dt.timezone.utc)


def format_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sanitize_text(value: str) -> str:
    sanitized = value
    for pattern, replacement in MASK_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def mask_command(parts: list[str]) -> list[str]:
    masked: list[str] = []
    redact_next = False
    for token in parts:
        lowered = token.lower()
        if redact_next:
            masked.append("***REDACTED***")
            redact_next = False
            continue
        if lowered in {"--db-password", "--password"}:
            masked.append(token)
            redact_next = True
            continue
        if token.startswith("PGPASSWORD="):
            masked.append("PGPASSWORD=***REDACTED***")
            continue
        masked.append(sanitize_text(token))
    return masked


def command_text(parts: list[str]) -> str:
    return " ".join(mask_command(parts))


def run_command(parts: list[str], env: dict[str, str] | None = None) -> CommandResult:
    proc = subprocess.run(
        parts,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return CommandResult(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def run_psql(args: argparse.Namespace, sql: str) -> tuple[bool, str, str]:
    if args.method == "docker-exec":
        command = [
            "docker",
            "compose",
            "-f",
            args.compose_file,
            "exec",
            "-T",
            "-e",
            f"PGPASSWORD={args.db_password}",
            args.compose_service,
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
    else:
        command = [
            "psql",
            "-h",
            args.db_host,
            "-p",
            str(args.db_port),
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
        env = dict(os.environ)
        env["PGPASSWORD"] = args.db_password
        result = run_command(command, env=env)

    if result.returncode != 0:
        details = (
            f"command={command_text(command)}\n"
            f"stdout={sanitize_text(result.stdout.strip())}\n"
            f"stderr={sanitize_text(result.stderr.strip())}"
        )
        return False, "", details
    return True, result.stdout.strip(), f"command={command_text(command)}"


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def safe_str(value: str | None) -> str:
    return "" if value is None else value


def compute_expected_hash(tenant_id: str, row: ChainRow) -> str:
    if row.chain_seq is None:
        return ""
    payload = "|".join(
        [
            tenant_id,
            safe_str(row.trace_id),
            safe_str(row.action_type),
            safe_str(row.target_type),
            safe_str(row.target_id),
            safe_str(row.before_json),
            safe_str(row.after_json),
            str(row.chain_seq),
            safe_str(row.hash_prev),
            str(row.created_at_epoch_ms),
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def decode_chain_rows(raw_json: str) -> list[ChainRow]:
    if raw_json.strip() == "":
        return []
    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("audit query payload must be a JSON list")

    rows: list[ChainRow] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        row = ChainRow(
            audit_id=str(item.get("audit_id", "")),
            chain_seq=item.get("chain_seq"),
            hash_prev=item.get("hash_prev"),
            hash_curr=item.get("hash_curr"),
            trace_id=item.get("trace_id"),
            action_type=item.get("action_type"),
            target_type=item.get("target_type"),
            target_id=item.get("target_id"),
            before_json=item.get("before_json"),
            after_json=item.get("after_json"),
            created_at_epoch_ms=int(item.get("created_at_epoch_ms", 0)),
        )
        rows.append(row)
    return rows


def verify_chain(tenant_id: str, rows: list[ChainRow], sample_limit: int) -> tuple[int, list[str]]:
    failures: list[str] = []
    previous: ChainRow | None = None

    for row in rows:
        if row.chain_seq is None or row.hash_prev is None or row.hash_curr is None:
            failures.append(f"missing_chain_fields:audit_id={row.audit_id},trace_id={safe_str(row.trace_id)}")
            previous = row
            continue

        if previous is not None and previous.chain_seq is not None:
            expected_seq = previous.chain_seq + 1
            if row.chain_seq != expected_seq:
                failures.append(
                    f"chain_seq_gap:audit_id={row.audit_id},trace_id={safe_str(row.trace_id)},"
                    f"expected={expected_seq},actual={row.chain_seq}"
                )
            if row.hash_prev != previous.hash_curr:
                failures.append(f"hash_link_mismatch:audit_id={row.audit_id},trace_id={safe_str(row.trace_id)}")

        expected_hash = compute_expected_hash(tenant_id=tenant_id, row=row)
        if expected_hash != row.hash_curr:
            failures.append(f"hash_curr_mismatch:audit_id={row.audit_id},trace_id={safe_str(row.trace_id)}")

        previous = row

    if len(failures) <= sample_limit:
        return len(failures), failures
    return len(failures), failures[:sample_limit]


def render_text(payload: dict) -> str:
    lines = [
        "verify_audit_chain_integrity",
        f"status={payload['status']}",
        f"tenant_key={payload['tenant_key']}",
        f"tenant_id={payload['tenant_id']}",
        f"from_utc={payload['from_utc']}",
        f"to_utc={payload['to_utc']}",
        f"method={payload['method']}",
        f"database={payload['database']}",
        f"checked_rows={payload['checked_rows']}",
        f"failure_count={payload['failure_count']}",
        f"violation_count={payload['violation_count']}",
        f"verified_at_utc={payload['verified_at_utc']}",
    ]
    if payload["status"] != "PASS":
        lines.append(
            "remediation_playbook=docs/ops/runbook/playbooks/audit_chain_integrity_incident.md"
        )
    for check_name, check_value in payload["checks"].items():
        lines.append(f"check.{check_name}={check_value}")
    for sample in payload["failure_samples"]:
        lines.append(f"sample={sample}")
    for violation in payload["violations"]:
        lines.append(f"- [{violation['code']}] {violation['message']} :: {violation['details']}")
    return "\n".join(lines) + "\n"


def write_output(path: Path | None, content: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    violations: list[Violation] = []
    checks: dict[str, str] = {}
    tenant_id = ""
    rows: list[ChainRow] = []
    failure_count = 0
    failure_samples: list[str] = []

    try:
        from_utc = parse_utc(args.from_utc, "from_utc")
        to_utc = parse_utc(args.to_utc, "to_utc")
        if from_utc > to_utc:
            raise ValueError("from_utc must be less than or equal to to_utc")
    except ValueError as exc:
        violations.append(
            Violation(
                code="INPUT_VALIDATION_FAILED",
                message="invalid verifier input",
                details=sanitize_text(str(exc)),
            )
        )
        from_utc = dt.datetime.now(dt.timezone.utc)
        to_utc = from_utc

    if not violations:
        tenant_sql = (
            "SELECT id::text "
            "FROM tb_tenant "
            f"WHERE tenant_key = {sql_literal(args.tenant_key)} "
            "LIMIT 1;"
        )
        ok, tenant_out, tenant_detail = run_psql(args=args, sql=tenant_sql)
        checks["tenant_lookup"] = "PASS" if ok else "FAIL"
        if not ok:
            violations.append(
                Violation(
                    code="TENANT_LOOKUP_FAILED",
                    message="failed to resolve tenant_id from tenant_key",
                    details=tenant_detail,
                )
            )
        else:
            tenant_id = tenant_out.strip()
            if tenant_id == "":
                violations.append(
                    Violation(
                        code="TENANT_NOT_FOUND",
                        message="tenant_key not found",
                        details=f"tenant_key={sanitize_text(args.tenant_key)}",
                    )
                )

    if not violations:
        bounded_limit = max(1, min(10000, int(args.limit)))
        chain_sql = f"""
SELECT COALESCE(
    json_agg(row_to_json(t) ORDER BY t.chain_seq_null_last, t.chain_seq, t.created_at_epoch_ms, t.audit_id)::text,
    '[]'
)
FROM (
    SELECT
        id::text AS audit_id,
        chain_seq,
        hash_prev,
        hash_curr,
        trace_id::text AS trace_id,
        action_type,
        target_type,
        target_id,
        CAST(before_json AS VARCHAR) AS before_json,
        CAST(after_json AS VARCHAR) AS after_json,
        FLOOR(EXTRACT(EPOCH FROM created_at) * 1000)::bigint AS created_at_epoch_ms,
        CASE WHEN chain_seq IS NULL THEN 1 ELSE 0 END AS chain_seq_null_last
    FROM tb_audit_log
    WHERE tenant_id = {sql_literal(tenant_id)}::uuid
      AND created_at >= {sql_literal(format_utc(from_utc))}::timestamptz
      AND created_at <= {sql_literal(format_utc(to_utc))}::timestamptz
    ORDER BY chain_seq_null_last ASC, chain_seq ASC, created_at_epoch_ms ASC, id ASC
    LIMIT {bounded_limit}
) AS t;
""".strip()
        ok, chain_out, chain_detail = run_psql(args=args, sql=chain_sql)
        checks["audit_query"] = "PASS" if ok else "FAIL"
        if not ok:
            violations.append(
                Violation(
                    code="AUDIT_QUERY_FAILED",
                    message="failed to query audit rows for chain verification",
                    details=chain_detail,
                )
            )
        else:
            try:
                rows = decode_chain_rows(chain_out)
            except Exception as exc:  # noqa: BLE001
                violations.append(
                    Violation(
                        code="AUDIT_QUERY_PARSE_FAILED",
                        message="failed to parse audit query payload",
                        details=sanitize_text(str(exc)),
                    )
                )

    if not violations:
        failure_count, failure_samples = verify_chain(
            tenant_id=tenant_id,
            rows=rows,
            sample_limit=max(1, int(args.failure_sample_limit)),
        )
        checks["chain_verify"] = "PASS" if failure_count == 0 else "FAIL"

    status = "PASS"
    if violations:
        status = "FAIL"
    elif failure_count > 0:
        status = "FAIL"

    payload = {
        "status": status,
        "tenant_key": sanitize_text(args.tenant_key),
        "tenant_id": tenant_id,
        "from_utc": format_utc(from_utc),
        "to_utc": format_utc(to_utc),
        "method": args.method,
        "database": args.database,
        "checked_rows": len(rows),
        "failure_count": failure_count,
        "failure_samples": [sanitize_text(item) for item in failure_samples],
        "checks": checks,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
        "verified_at_utc": utc_now(),
    }

    default_prefix = f"audit_chain_verify_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')}"
    output_txt = Path(args.output_txt) if args.output_txt else artifact_dir / f"{default_prefix}.txt"
    output_json = Path(args.output_json) if args.output_json else artifact_dir / f"{default_prefix}.json"

    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_output(output_txt, text_report)
    write_output(output_json, json_report)

    sys.stdout.write(text_report)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
