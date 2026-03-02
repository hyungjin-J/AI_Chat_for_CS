#!/usr/bin/env python3
"""Build a deterministic release gate dashboard artifact (non-blocking)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


DEFAULT_ARTIFACTS_DIR = Path("docs/review/mvp_verification_pack/artifacts")
DEFAULT_DASHBOARD_MD = "release_gate_dashboard.md"
DEFAULT_DASHBOARD_JSON = "release_gate_dashboard.json"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIPPED = "SKIPPED"
STATUS_MISSING = "MISSING"
STATUS_ERROR = "ERROR"
ALLOWED_STATUSES = {STATUS_PASS, STATUS_FAIL, STATUS_SKIPPED, STATUS_MISSING, STATUS_ERROR}
DATE_TOKEN_RE = re.compile(r"20\d{2}(?:\d{2}|[xX]{2})(?:\d{2}|[xX]{2})?")
STATUS_TOKEN_RE = re.compile(r"^\s*status\s*[:=]\s*(PASS|FAIL|SKIPPED|MISSING|ERROR)\b", re.IGNORECASE)
PASS_FAIL_TOKEN_RE = re.compile(r"^\s*(PASS|FAIL|SKIPPED)\b", re.IGNORECASE)
KEY_VALUE_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*[:=]\s*(.*?)\s*$")

GATE_SPECS = (
    {
        "key": "domain_layer_boundary_gate",
        "name": "Domain layer boundary gate",
        "paths": ("domain_layer_boundary_gate.json", "domain_layer_boundary_gate.txt"),
        "metric_fields": (
            "baseline_violation_count",
            "new_violation_count",
            "current_violation_count",
        ),
    },
    {
        "key": "application_port_boundary_gate",
        "name": "Application port boundary gate",
        "paths": ("application_port_boundary_gate.json", "application_port_boundary_gate.txt"),
        "metric_fields": (
            "baseline_violation_count",
            "new_violation_count",
            "current_violation_count",
        ),
    },
    {
        "key": "continuation_utf8_strict_gate",
        "name": "UTF-8 strict decode gate",
        "paths": ("continuation_utf8_strict_gate.json", "continuation_utf8_strict_gate.txt"),
        "metric_fields": ("violation_count", "scanned_file_count"),
    },
    {
        "key": "utf8_full_scan_ratchet_gate",
        "name": "UTF-8 full-scan ratchet gate",
        "paths": ("utf8_full_scan_ratchet_gate.json", "utf8_full_scan_ratchet_gate.txt"),
        "metric_fields": (
            "baseline_violation_count",
            "new_violation_count",
            "violation_count",
            "scanned_file_count",
        ),
    },
    {
        "key": "spec_consistency_check_report",
        "name": "Spec consistency check",
        "paths": (
            "spec_consistency_check_report.json",
            "spec_consistency_check_pass.txt",
            "spec_consistency_check_report.txt",
        ),
        "metric_fields": ("violation_count", "invalid_tokens_count"),
    },
    {
        "key": "spec_sync_report_gate",
        "name": "Spec sync report gate",
        "paths": ("spec_sync_report_gate.json", "spec_sync_report_gate.txt"),
        "metric_fields": ("spec_changed_count", "evidence_section_count", "violations_count"),
    },
    {
        "key": "spec_impl_coverage_gate",
        "name": "Spec implementation coverage gate",
        "paths": ("spec_impl_coverage_gate.json", "spec_impl_coverage_gate.txt"),
        "metric_fields": ("must_api_rows", "must_backend_missing_count", "must_tests_missing_count"),
    },
    {
        "key": "artifact_index_gate",
        "name": "Artifact index gate",
        "paths": ("artifact_index_gate.json", "artifact_index_gate.txt"),
        "metric_fields": ("indexed_file_count", "violation_count"),
    },
    {
        "key": "artifact_archive_report",
        "name": "Artifact archive report",
        "paths": ("artifact_archive_report.json", "artifact_archive_report.txt"),
        "metric_fields": ("archived_file_count", "violation_count"),
    },
    {
        "key": "node22_unicode_mirror_helper_smoke",
        "name": "Node22 unicode mirror helper smoke",
        "paths": ("node22_unicode_mirror_helper_smoke.txt",),
        "metric_fields": ("path_mode", "node_check_status", "mirror_performed"),
    },
    {
        "key": "db_local_readiness_smoke",
        "name": "DB local readiness smoke",
        "paths": ("db_local_readiness_smoke.json", "db_local_readiness_smoke.txt"),
        "metric_fields": ("reason_code", "method", "violation_count"),
    },
    {
        "key": "db_backend_health_trace_gate",
        "name": "DB backend health trace gate",
        "paths": ("db_backend_health_trace_gate.json", "db_backend_health_trace_gate.txt"),
        "metric_fields": ("reason_code", "violation_count", "without_trace_status", "with_trace_status"),
    },
    {
        "key": "prod_deploy_smoke",
        "name": "Production deploy smoke",
        "paths": ("prod_deploy_smoke_*.json", "prod_deploy_smoke_*.txt"),
        "metric_fields": ("reason_code", "flyway_row_count", "without_trace_status", "with_trace_status"),
    },
    {
        "key": "e2e_smoke",
        "name": "Operational E2E smoke",
        "paths": (
            "e2e_smoke_report_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].json",
            "e2e_smoke_trace_samples_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].txt",
        ),
        "metric_fields": ("reason_code", "status", "scenario_total", "scenario_pass", "scenario_fail"),
    },
    {
        "key": "rag_regression_gate",
        "name": "RAG regression gate",
        "paths": (
            "rag_regression_gate_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].json",
            "rag_regression_gate_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].txt",
        ),
        "metric_fields": ("reason_code", "violation_count"),
    },
    {
        "key": "perf_sse_gate",
        "name": "SSE perf gate",
        "paths": (
            "perf_sse_gate_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_actual.json",
            "perf_sse_gate_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].txt",
        ),
        "metric_fields": ("reason_code", "violation_count"),
    },
    {
        "key": "audit_chain_verifier",
        "name": "Audit chain verifier",
        "paths": ("golive_audit_chain_verify_*.json", "golive_audit_chain_verify_*.txt"),
        "metric_fields": ("violation_count", "checked_rows", "failure_count"),
    },
)

TRIAGE_PATHS = (
    "artifact_index_gate.json",
    "artifact_index_gate.txt",
    "spec_sync_report_gate.json",
    "spec_sync_report_gate.txt",
    "spec_consistency_check_report.json",
    "spec_consistency_check_pass.txt",
    "release_gate_dashboard.json",
)


def normalize(path: str) -> str:
    return path.strip().replace("\\", "/")


def parse_date_token(token: str) -> tuple[int, int, int]:
    year = int(token[0:4])
    month_token = token[4:6] if len(token) >= 6 else "00"
    day_token = token[6:8] if len(token) >= 8 else "00"
    month = int(month_token) if month_token.isdigit() else -1
    day = int(day_token) if day_token.isdigit() else -1
    return (year, month, day)


def extract_date_score(stem: str) -> tuple[int, int, int]:
    tokens = DATE_TOKEN_RE.findall(stem)
    if not tokens:
        return (-1, -1, -1)
    return max(parse_date_token(token) for token in tokens)


def run_git(repo_root: Path, args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return "UNKNOWN"

    value = (proc.stdout or "").strip()
    if proc.returncode != 0 or not value:
        return "UNKNOWN"
    return value


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_text_key_values(head_lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in head_lines:
        match = KEY_VALUE_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key:
            result[key] = value
    return result


def parse_status_from_text_head(head_lines: list[str], key_values: dict[str, str]) -> str | None:
    for line in head_lines:
        status_match = STATUS_TOKEN_RE.match(line)
        if status_match:
            return status_match.group(1).upper()
    for line in head_lines:
        token_match = PASS_FAIL_TOKEN_RE.match(line)
        if token_match:
            return token_match.group(1).upper()

    violation_raw = key_values.get("violation_count")
    if violation_raw is not None:
        try:
            return STATUS_PASS if int(violation_raw) == 0 else STATUS_FAIL
        except ValueError:
            return STATUS_ERROR
    return None


def infer_status_from_json(payload: dict) -> str:
    raw_status = payload.get("status")
    if isinstance(raw_status, str):
        normalized = raw_status.strip().upper()
        if normalized in ALLOWED_STATUSES:
            return normalized
        if normalized in {"OK", "SUCCESS", "SUCCEEDED"}:
            return STATUS_PASS
        if normalized in {"WARN", "WARNING"}:
            return STATUS_FAIL

    violation_count = payload.get("violation_count")
    if isinstance(violation_count, int):
        return STATUS_PASS if violation_count == 0 else STATUS_FAIL

    return STATUS_ERROR


def select_primary_evidence(evidence: list[dict]) -> dict | None:
    existing = [item for item in evidence if item["exists"]]
    if not existing:
        return None
    json_candidates = [item for item in existing if item["path"].lower().endswith(".json")]
    if json_candidates:
        return json_candidates[0]
    return existing[0]


def contains_glob_pattern(path: str) -> bool:
    return any(char in path for char in ("*", "?", "["))


def select_latest_candidate(matches: list[Path], artifacts_dir: Path) -> Path:
    def sort_key(path: Path) -> tuple[tuple[int, int, int], int, str]:
        rel = normalize(path.relative_to(artifacts_dir).as_posix())
        suffix_rank = 1 if path.suffix.lower() == ".json" else 0
        return (extract_date_score(path.stem.lower()), suffix_rank, rel.lower())

    return sorted(matches, key=sort_key)[-1]


def resolve_evidence_paths(artifacts_dir: Path, declared_paths: tuple[str, ...]) -> list[dict]:
    evidence: list[dict] = []
    for declared in declared_paths:
        if contains_glob_pattern(declared):
            matches = [path for path in artifacts_dir.glob(declared) if path.is_file()]
            if matches:
                chosen = select_latest_candidate(matches, artifacts_dir)
                rel = normalize(chosen.relative_to(artifacts_dir).as_posix())
                evidence.append(
                    {
                        "path": rel,
                        "exists": True,
                        "declared_path": declared,
                    }
                )
            else:
                evidence.append(
                    {
                        "path": declared,
                        "exists": False,
                        "declared_path": declared,
                    }
                )
            continue

        abs_path = artifacts_dir / declared
        evidence.append(
            {
                "path": declared,
                "exists": abs_path.exists(),
                "declared_path": declared,
            }
        )
    return evidence


def collect_metric_string(metric_fields: tuple[str, ...], payload: dict[str, object]) -> str:
    metric_parts: list[str] = []
    for field in metric_fields:
        if field not in payload:
            continue
        value = payload[field]
        if isinstance(value, (str, int, float, bool)):
            metric_parts.append(f"{field}={value}")
    if not metric_parts:
        return "-"
    return ", ".join(metric_parts)


def select_parsed_fields(metric_fields: tuple[str, ...], payload: dict[str, object]) -> dict[str, object]:
    allowed = set(metric_fields)
    allowed.update(
        {
            "status",
            "violation_count",
            "baseline_violation_count",
            "new_violation_count",
            "current_violation_count",
        }
    )
    result: dict[str, object] = {}
    for key in sorted(allowed):
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, (str, int, float, bool)):
            result[key] = value
    return result


def parse_json_artifact(path: Path, metric_fields: tuple[str, ...]) -> tuple[str, str, str, dict[str, object]]:
    try:
        text = safe_read_text(path)
    except OSError as exc:
        return (STATUS_ERROR, "-", f"cannot read file: {exc}", {})

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return (STATUS_ERROR, "-", "invalid json artifact", {})

    if not isinstance(payload, dict):
        return (STATUS_ERROR, "-", "json artifact is not an object", {})

    status = infer_status_from_json(payload)
    metric = collect_metric_string(metric_fields, payload)
    parsed_fields = select_parsed_fields(metric_fields, payload)
    reason = "" if status != STATUS_ERROR else "unable to infer status from json"
    return (status, metric, reason, parsed_fields)


def parse_text_artifact(path: Path, metric_fields: tuple[str, ...]) -> tuple[str, str, str, dict[str, object]]:
    try:
        text = safe_read_text(path)
    except OSError as exc:
        return (STATUS_ERROR, "-", f"cannot read file: {exc}", {})

    head_lines = text.splitlines()[:20]
    key_values = parse_text_key_values(head_lines)
    status = parse_status_from_text_head(head_lines, key_values)
    if status is None:
        return (STATUS_ERROR, "-", "status token not found in first 20 lines", key_values)

    metric_payload: dict[str, object] = {key: value for key, value in key_values.items()}
    metric = collect_metric_string(metric_fields, metric_payload)
    metric_payload["status"] = status
    parsed_fields = select_parsed_fields(metric_fields, metric_payload)
    return (status, metric, "", parsed_fields)


def evaluate_gate(artifacts_dir: Path, spec: dict) -> dict:
    metric_fields = tuple(spec.get("metric_fields", ()))
    evidence = resolve_evidence_paths(artifacts_dir=artifacts_dir, declared_paths=tuple(spec["paths"]))

    primary = select_primary_evidence(evidence)
    if primary is None:
        return {
            "key": spec["key"],
            "name": spec["name"],
            "status": STATUS_MISSING,
            "reason": "no evidence file found",
            "evidence": evidence,
            "primary_evidence": None,
            "key_metric": "-",
            "parsed_fields": {},
        }

    path = artifacts_dir / primary["path"]
    if primary["path"].lower().endswith(".json"):
        status, metric, reason, parsed_fields = parse_json_artifact(path, metric_fields)
    else:
        status, metric, reason, parsed_fields = parse_text_artifact(path, metric_fields)

    return {
        "key": spec["key"],
        "name": spec["name"],
        "status": status,
        "reason": reason,
        "evidence": evidence,
        "primary_evidence": primary["path"],
        "key_metric": metric,
        "parsed_fields": parsed_fields,
    }


def render_evidence_markdown(evidence: list[dict]) -> str:
    items: list[str] = []
    for item in evidence:
        path = item["path"]
        if item["exists"]:
            items.append(f"[{path}]({path})")
        else:
            items.append(f"`{path}` (missing)")
    return "<br>".join(items)


def load_index_json(index_path: Path | None) -> dict | None:
    if index_path is None or not index_path.exists():
        return None
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def list_public_api_compare_candidates(artifacts_dir: Path, index_payload: dict | None) -> list[Path]:
    discovered: dict[str, Path] = {}

    if index_payload is not None:
        latest_files = index_payload.get("latest_files", [])
        if isinstance(latest_files, list):
            for item in latest_files:
                if not isinstance(item, str):
                    continue
                rel = normalize(item)
                if "public_api_compare" not in rel.lower():
                    continue
                path = artifacts_dir / rel
                if path.exists():
                    discovered[normalize(path.as_posix()).lower()] = path

    for path in artifacts_dir.glob("*public_api_compare*.json"):
        discovered[normalize(path.as_posix()).lower()] = path
    for path in artifacts_dir.glob("*public_api_compare*.txt"):
        discovered[normalize(path.as_posix()).lower()] = path

    def sort_key(path: Path) -> tuple[tuple[int, int, int], int, str]:
        suffix_rank = 1 if path.suffix.lower() == ".json" else 0
        return (extract_date_score(path.stem.lower()), suffix_rank, normalize(path.name).lower())

    return sorted(discovered.values(), key=sort_key)


def find_numeric_key(payload: object, targets: tuple[str, ...]) -> int | None:
    stack: list[object] = [payload]
    normalized_targets = {target.lower() for target in targets}
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                key_lower = str(key).lower()
                if key_lower in normalized_targets and isinstance(value, int):
                    return value
                stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)
    return None


def parse_api_compare_from_json(path: Path) -> tuple[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return ("UNKNOWN", normalize(path.name))

    added = find_numeric_key(payload, ("added", "added_count", "api_added_count"))
    removed = find_numeric_key(payload, ("removed", "removed_count", "api_removed_count"))
    if added is None or removed is None:
        return ("UNKNOWN", normalize(path.name))
    return (f"added={added}, removed={removed}", normalize(path.name))


def parse_api_compare_from_text(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    head = "\n".join(text.splitlines()[:40])
    added_match = re.search(r"\badded(?:_count)?\b[^0-9-]*(-?\d+)", head, re.IGNORECASE)
    removed_match = re.search(r"\bremoved(?:_count)?\b[^0-9-]*(-?\d+)", head, re.IGNORECASE)
    if not added_match or not removed_match:
        return ("UNKNOWN", normalize(path.name))
    return (f"added={int(added_match.group(1))}, removed={int(removed_match.group(1))}", normalize(path.name))


def resolve_api_compare_snapshot(
    artifacts_dir: Path,
    index_payload: dict | None,
) -> dict[str, object]:
    candidates = list_public_api_compare_candidates(artifacts_dir, index_payload)
    if not candidates:
        return {"value": "UNKNOWN", "source": None}

    chosen = candidates[-1]
    try:
        if chosen.suffix.lower() == ".json":
            value, source = parse_api_compare_from_json(chosen)
        else:
            value, source = parse_api_compare_from_text(chosen)
    except OSError:
        return {"value": "UNKNOWN", "source": normalize(chosen.name)}
    return {"value": value, "source": source}


def build_baseline_snapshot(gates: list[dict], api_compare: dict[str, object]) -> dict:
    domain_gate = next((item for item in gates if item["key"] == "domain_layer_boundary_gate"), None)
    utf8_gate = next((item for item in gates if item["key"] == "utf8_full_scan_ratchet_gate"), None)

    domain_value = "UNKNOWN"
    domain_source = None
    if domain_gate and isinstance(domain_gate.get("parsed_fields"), dict):
        value = domain_gate["parsed_fields"].get("baseline_violation_count")
        if isinstance(value, int):
            domain_value = value
            domain_source = domain_gate.get("primary_evidence")
        elif isinstance(value, str) and value.isdigit():
            domain_value = int(value)
            domain_source = domain_gate.get("primary_evidence")

    utf8_value = "UNKNOWN"
    utf8_source = None
    if utf8_gate and isinstance(utf8_gate.get("parsed_fields"), dict):
        value = utf8_gate["parsed_fields"].get("baseline_violation_count")
        if isinstance(value, int):
            utf8_value = value
            utf8_source = utf8_gate.get("primary_evidence")
        elif isinstance(value, str) and value.isdigit():
            utf8_value = int(value)
            utf8_source = utf8_gate.get("primary_evidence")

    return {
        "domain_purity_baseline": {
            "expected": 0,
            "value": domain_value,
            "source": domain_source,
        },
        "utf8_full_scan_baseline": {
            "expected": 0,
            "value": utf8_value,
            "source": utf8_source,
        },
        "public_api_compare": {
            "value": api_compare["value"],
            "source": api_compare["source"],
        },
    }


def build_summary(gates: list[dict]) -> dict:
    counts = {
        STATUS_PASS: 0,
        STATUS_FAIL: 0,
        STATUS_SKIPPED: 0,
        STATUS_MISSING: 0,
        STATUS_ERROR: 0,
    }
    for gate in gates:
        status = gate.get("status", STATUS_ERROR)
        if status not in counts:
            status = STATUS_ERROR
        counts[status] += 1

    overall = STATUS_PASS
    if counts[STATUS_FAIL] or counts[STATUS_MISSING] or counts[STATUS_ERROR]:
        overall = STATUS_FAIL

    return {
        "overall_status": overall,
        "status_counts": counts,
        "gate_count": len(gates),
    }


def build_triage(gates: list[dict]) -> dict:
    failing = [gate["name"] for gate in gates if gate["status"] in {STATUS_FAIL, STATUS_ERROR, STATUS_MISSING}]
    return {
        "failing_gates": failing,
        "priority_artifacts": list(TRIAGE_PATHS),
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Release Gate Dashboard",
        "",
        f"- git_head_short: `{payload['metadata']['git_head_short']}`",
        f"- git_branch: `{payload['metadata']['git_branch']}`",
        f"- artifacts_dir: `{payload['metadata']['artifacts_dir']}`",
        f"- index_json: `{payload['metadata']['index_json']}`",
        f"- overall_status: `{payload['summary']['overall_status']}`",
        "",
        "## Gate Status Table",
        "| Gate name | Status | Evidence path(s) | Key metric |",
        "| --- | --- | --- | --- |",
    ]

    for gate in payload["gates"]:
        lines.append(
            "| "
            + gate["name"]
            + " | "
            + gate["status"]
            + " | "
            + render_evidence_markdown(gate["evidence"])
            + " | "
            + gate["key_metric"]
            + " |"
        )

    baseline = payload["baseline_snapshot"]
    lines.extend(
        [
            "",
            "## Baseline Snapshot",
            "- Domain purity baseline (expected 0): "
            + f"`{baseline['domain_purity_baseline']['value']}`"
            + f" (source: `{baseline['domain_purity_baseline']['source'] or 'UNKNOWN'}`)",
            "- UTF-8 full-scan baseline (expected 0): "
            + f"`{baseline['utf8_full_scan_baseline']['value']}`"
            + f" (source: `{baseline['utf8_full_scan_baseline']['source'] or 'UNKNOWN'}`)",
            "- Public API compare added/removed: "
            + f"`{baseline['public_api_compare']['value']}`"
            + f" (source: `{baseline['public_api_compare']['source'] or 'UNKNOWN'}`)",
            "",
            "## If FAIL, where to look first",
        ]
    )

    failing_gates = payload["triage"]["failing_gates"]
    if failing_gates:
        lines.append("- failing_gates: " + ", ".join(failing_gates))
    else:
        lines.append("- failing_gates: (none)")
    lines.append("- priority_artifacts:")
    for rel in payload["triage"]["priority_artifacts"]:
        lines.append(f"  - [{rel}]({rel})")

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build non-blocking release gate dashboard artifacts")
    parser.add_argument("--artifacts-dir", default=str(DEFAULT_ARTIFACTS_DIR))
    parser.add_argument(
        "--index-json",
        default=None,
        help="Optional index json path (defaults to artifacts/_INDEX.json when present)",
    )
    return parser.parse_args()


def resolve_path(base: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (base / path).resolve()


def build_dashboard_payload(artifacts_dir: Path, index_json_path: Path | None) -> dict:
    repo_root = Path.cwd().resolve()
    git_head_short = run_git(repo_root, ["rev-parse", "--short", "HEAD"])
    git_branch = run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    index_payload = load_index_json(index_json_path)

    gates = [evaluate_gate(artifacts_dir, spec) for spec in GATE_SPECS]
    summary = build_summary(gates)
    api_compare = resolve_api_compare_snapshot(artifacts_dir, index_payload)
    baseline_snapshot = build_baseline_snapshot(gates, api_compare)
    triage = build_triage(gates)

    return {
        "metadata": {
            "git_head_short": git_head_short,
            "git_branch": git_branch,
            "artifacts_dir": normalize(artifacts_dir.as_posix()),
            "index_json": normalize(index_json_path.as_posix()) if index_json_path else "MISSING",
        },
        "summary": summary,
        "gates": gates,
        "baseline_snapshot": baseline_snapshot,
        "triage": triage,
    }


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()
    artifacts_dir = resolve_path(repo_root, args.artifacts_dir)
    dashboard_md_path = artifacts_dir / DEFAULT_DASHBOARD_MD
    dashboard_json_path = artifacts_dir / DEFAULT_DASHBOARD_JSON

    index_json_path: Path | None
    if args.index_json:
        index_json_path = resolve_path(repo_root, args.index_json)
    else:
        default_index = artifacts_dir / "_INDEX.json"
        index_json_path = default_index if default_index.exists() else None

    if not artifacts_dir.exists():
        fallback_payload = {
            "metadata": {
                "git_head_short": run_git(repo_root, ["rev-parse", "--short", "HEAD"]),
                "git_branch": run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]),
                "artifacts_dir": normalize(artifacts_dir.as_posix()),
                "index_json": normalize(index_json_path.as_posix()) if index_json_path else "MISSING",
            },
            "summary": {
                "overall_status": STATUS_FAIL,
                "status_counts": {
                    STATUS_PASS: 0,
                    STATUS_FAIL: 0,
                    STATUS_SKIPPED: 0,
                    STATUS_MISSING: len(GATE_SPECS),
                    STATUS_ERROR: 0,
                },
                "gate_count": len(GATE_SPECS),
            },
            "gates": [
                {
                    "key": spec["key"],
                    "name": spec["name"],
                    "status": STATUS_MISSING,
                    "reason": "artifact directory missing",
                    "evidence": [{"path": rel, "exists": False} for rel in spec["paths"]],
                    "primary_evidence": None,
                    "key_metric": "-",
                    "parsed_fields": {},
                }
                for spec in GATE_SPECS
            ],
            "baseline_snapshot": {
                "domain_purity_baseline": {"expected": 0, "value": "UNKNOWN", "source": None},
                "utf8_full_scan_baseline": {"expected": 0, "value": "UNKNOWN", "source": None},
                "public_api_compare": {"value": "UNKNOWN", "source": None},
            },
            "triage": {
                "failing_gates": [spec["name"] for spec in GATE_SPECS],
                "priority_artifacts": list(TRIAGE_PATHS),
            },
        }
        dashboard_md = render_markdown(fallback_payload)
        dashboard_json = json.dumps(fallback_payload, ensure_ascii=False, indent=2) + "\n"
        write_output(dashboard_md_path, dashboard_md)
        write_output(dashboard_json_path, dashboard_json)
        return 0

    try:
        payload = build_dashboard_payload(artifacts_dir, index_json_path)
    except Exception as exc:  # pragma: no cover - defensive fallback
        payload = {
            "metadata": {
                "git_head_short": run_git(repo_root, ["rev-parse", "--short", "HEAD"]),
                "git_branch": run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]),
                "artifacts_dir": normalize(artifacts_dir.as_posix()),
                "index_json": normalize(index_json_path.as_posix()) if index_json_path else "MISSING",
            },
            "summary": {
                "overall_status": STATUS_FAIL,
                "status_counts": {
                    STATUS_PASS: 0,
                    STATUS_FAIL: 0,
                    STATUS_SKIPPED: 0,
                    STATUS_MISSING: 0,
                    STATUS_ERROR: len(GATE_SPECS),
                },
                "gate_count": len(GATE_SPECS),
            },
            "gates": [
                {
                    "key": spec["key"],
                    "name": spec["name"],
                    "status": STATUS_ERROR,
                    "reason": f"dashboard generation error: {exc}",
                    "evidence": [{"path": rel, "exists": (artifacts_dir / rel).exists()} for rel in spec["paths"]],
                    "primary_evidence": None,
                    "key_metric": "-",
                    "parsed_fields": {},
                }
                for spec in GATE_SPECS
            ],
            "baseline_snapshot": {
                "domain_purity_baseline": {"expected": 0, "value": "UNKNOWN", "source": None},
                "utf8_full_scan_baseline": {"expected": 0, "value": "UNKNOWN", "source": None},
                "public_api_compare": {"value": "UNKNOWN", "source": None},
            },
            "triage": {
                "failing_gates": [spec["name"] for spec in GATE_SPECS],
                "priority_artifacts": list(TRIAGE_PATHS),
            },
        }

    dashboard_md = render_markdown(payload)
    dashboard_json = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_output(dashboard_md_path, dashboard_md)
    write_output(dashboard_json_path, dashboard_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
