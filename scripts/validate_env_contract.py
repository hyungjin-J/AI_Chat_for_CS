#!/usr/bin/env python3
"""Validate production env contract for reproducible deployments."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_KEYS = (
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DB_URL",
    "DB_USERNAME",
    "DB_PASSWORD",
    "REDIS_HOST",
    "REDIS_PORT",
    "SPRING_PROFILES_ACTIVE",
    "APP_LLM_PROVIDER",
    "APP_IDEMPOTENCY_STORE",
    "APP_IDEMPOTENCY_REDIS_FAIL_STRATEGY",
    "APP_TRACE_REQUIRE_HEADER",
    "APP_OLLAMA_BASE_URL",
    "APP_OLLAMA_MODEL",
    "LLM_PROVIDER_KEY_REF",
    "VITE_API_BASE_URL",
    "APP_JWT_SECRET",
    "APP_JWT_SECRET_REF",
)

REDACTED_ONLY_KEYS = {
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DB_URL",
    "DB_USERNAME",
    "DB_PASSWORD",
    "APP_JWT_SECRET",
}

SECRET_REF_PATTERN = re.compile(r"^(secret|vault|aws-sm|gcp-sm|azure-kv)://.+$")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?:\+\d{1,3}[- ]?)?(?:\d{2,4}[- ]?){2}\d{4}\b")
SECRET_LIKE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9._-]{8,}\.[A-Za-z0-9._-]{8,}\b"),
)


@dataclass
class Violation:
    code: str
    key: str
    message: str
    remediation: str
    line: int | None = None


def parse_env_file(env_path: Path) -> tuple[dict[str, str], list[Violation]]:
    if not env_path.exists():
        return {}, [
            Violation(
                code="ENV_FILE_MISSING",
                key="",
                message=f"{env_path.as_posix()} not found",
                remediation="Create the env example file before running this gate.",
            )
        ]

    parsed: dict[str, str] = {}
    violations: list[Violation] = []
    raw_content = env_path.read_text(encoding="utf-8", errors="strict")
    if raw_content.startswith("\ufeff"):
        raw_content = raw_content.lstrip("\ufeff")
    for line_no, raw_line in enumerate(raw_content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if "=" not in raw_line:
            violations.append(
                Violation(
                    code="INVALID_LINE",
                    key="",
                    line=line_no,
                    message="line must be KEY=VALUE format",
                    remediation="Fix malformed line in env example.",
                )
            )
            continue

        key_raw, value_raw = raw_line.split("=", 1)
        key = key_raw.strip()
        value = value_raw.strip()
        if not key:
            violations.append(
                Violation(
                    code="EMPTY_KEY",
                    key="",
                    line=line_no,
                    message="empty environment variable name",
                    remediation="Provide a non-empty key before '='.",
                )
            )
            continue

        parsed[key] = value

    return parsed, violations


def contains_pii_or_secret(value: str) -> bool:
    if value == "<REDACTED>":
        return False
    if EMAIL_PATTERN.search(value):
        return True
    if PHONE_PATTERN.search(value):
        return True
    for pattern in SECRET_LIKE_PATTERNS:
        if pattern.search(value):
            return True
    return False


def validate_env(parsed: dict[str, str]) -> list[Violation]:
    violations: list[Violation] = []

    for required in REQUIRED_KEYS:
        if required not in parsed:
            violations.append(
                Violation(
                    code="MISSING_REQUIRED_KEY",
                    key=required,
                    message=f"required key '{required}' is missing",
                    remediation="Add the missing key to .env.example.",
                )
            )

    tenant_value = parsed.get("X_TENANT_KEY")
    if tenant_value is not None and tenant_value.strip():
        violations.append(
            Violation(
                code="TENANT_DEFAULT_FORBIDDEN",
                key="X_TENANT_KEY",
                message="X_TENANT_KEY default value is forbidden",
                remediation="Remove the value and keep tenant key runtime-injected per request.",
            )
        )

    for key in REDACTED_ONLY_KEYS:
        if key in parsed and parsed[key] != "<REDACTED>":
            violations.append(
                Violation(
                    code="REDACTED_ONLY_KEY",
                    key=key,
                    message=f"{key} must be '<REDACTED>' in .env.example",
                    remediation="Replace the committed sample value with <REDACTED>.",
                )
            )

    for key, value in parsed.items():
        if key.endswith("_REF"):
            if not SECRET_REF_PATTERN.match(value):
                violations.append(
                    Violation(
                        code="INVALID_SECRET_REF_FORMAT",
                        key=key,
                        message=f"{key} must use scheme://... format",
                        remediation="Use one of secret://, vault://, aws-sm://, gcp-sm://, azure-kv://",
                    )
                )
            elif "<REDACTED>" not in value:
                violations.append(
                    Violation(
                        code="SECRET_REF_REDACTION_REQUIRED",
                        key=key,
                        message=f"{key} must keep redacted placeholder in committed .env.example",
                        remediation="Replace live secret reference path with <REDACTED> placeholder.",
                    )
                )

        if contains_pii_or_secret(value):
            violations.append(
                Violation(
                    code="SENSITIVE_PATTERN_DETECTED",
                    key=key,
                    message=f"sensitive pattern detected in key '{key}'",
                    remediation="Replace the value with <REDACTED> or secret_ref placeholder.",
                )
            )

    return violations


def render_text(status: str, env_example: Path, violations: list[Violation]) -> str:
    lines = [
        "env_contract_validation",
        f"status={status}",
        f"env_example={env_example.as_posix()}",
        f"required_keys={len(REQUIRED_KEYS)}",
        f"violation_count={len(violations)}",
    ]
    for violation in violations:
        line_meta = f" line={violation.line}" if violation.line is not None else ""
        lines.append(
            f"- [{violation.code}] key={violation.key}{line_meta} "
            f"message={violation.message} remediation={violation.remediation}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate .env.example contract")
    parser.add_argument("--env-example", required=True, help="Path to .env.example")
    parser.add_argument("--output-json", help="Optional JSON report path")
    parser.add_argument("--output-txt", help="Optional text report path")
    args = parser.parse_args()

    env_example = Path(args.env_example)
    parsed, parse_violations = parse_env_file(env_example)
    violations = parse_violations + validate_env(parsed)
    status = "PASS" if not violations else "FAIL"

    payload = {
        "status": status,
        "env_example": env_example.as_posix(),
        "required_keys": list(REQUIRED_KEYS),
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }
    report_text = render_text(status=status, env_example=env_example, violations=violations)

    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_txt:
        output_txt = Path(args.output_txt)
        output_txt.parent.mkdir(parents=True, exist_ok=True)
        output_txt.write_text(report_text, encoding="utf-8")

    sys.stdout.write(report_text)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
