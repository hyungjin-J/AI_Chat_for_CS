#!/usr/bin/env python3
"""Build deterministic weekly Ops trend summary from artifact JSON files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_ARTIFACTS_DIR = Path("docs/review/mvp_verification_pack/artifacts")
DEFAULT_REPORT_TXT = "ops_trend_report.txt"
DEFAULT_REPORT_JSON = "ops_trend_report.json"
DATE_TOKEN_RE = re.compile(r"20\d{6}")
STATUS_VALUES = {"PASS", "FAIL", "ERROR", "MISSING", "UNKNOWN"}

FAMILY_SPECS = (
    (
        "db_backup_restore_rehearsal",
        "DB backup/restore rehearsal",
        re.compile(r"^db_backup_restore_rehearsal(?:[_-].*)?\.json$", re.IGNORECASE),
    ),
    (
        "db_repro_nightly",
        "DB reproducibility nightly",
        re.compile(
            r"^db_(?:local_readiness_smoke|backend_health_trace_gate)(?:[_-].*)?\.json$",
            re.IGNORECASE,
        ),
    ),
    (
        "vector_bench_monitoring",
        "Vector bench monitoring",
        re.compile(
            r"^(?:vector_recall_latency_bench|vector_bench(?:_[a-z0-9_]+)?)(?:[_-].*)?\.json$",
            re.IGNORECASE,
        ),
    ),
)

RTO_KEYS = ("rto_minutes",)
RPO_KEYS = ("rpo_hours",)
P95_KEYS = ("p95_latency_ms", "latency_p95_ms", "p95_ms")


def normalize(path: str) -> str:
    return path.replace("\\", "/").strip()


def parse_date_score(name: str) -> tuple[int, int, int]:
    matches = DATE_TOKEN_RE.findall(name)
    if not matches:
        return (-1, -1, -1)
    best = max(matches)
    year = int(best[:4])
    month = int(best[4:6])
    day = int(best[6:8])
    return (year, month, day)


def infer_status(payload: object) -> str:
    if isinstance(payload, dict):
        status_raw = payload.get("status")
        if isinstance(status_raw, str):
            status = status_raw.strip().upper()
            if status in STATUS_VALUES:
                return status
        violation_count = payload.get("violation_count")
        if isinstance(violation_count, int):
            return "PASS" if violation_count == 0 else "FAIL"
    return "ERROR"


def extract_failure_codes(payload: object) -> list[str]:
    codes: list[str] = []
    if not isinstance(payload, dict):
        return codes

    value = payload.get("failure_code")
    if isinstance(value, str) and value.strip():
        codes.append(value.strip())

    value = payload.get("error_code")
    if isinstance(value, str) and value.strip():
        codes.append(value.strip())

    violations = payload.get("violations")
    if isinstance(violations, list):
        for item in violations:
            if isinstance(item, dict):
                code = item.get("code")
                if isinstance(code, str) and code.strip():
                    codes.append(code.strip())
            elif isinstance(item, str) and item.strip():
                codes.append(item.strip())

    checks = payload.get("checks")
    if isinstance(checks, dict):
        for key in sorted(checks.keys(), key=lambda item: str(item).lower()):
            check_value = checks[key]
            if isinstance(check_value, dict):
                check_status = str(check_value.get("status", "")).strip().upper()
                if check_status == "FAIL":
                    codes.append(f"CHECK_{key}")
            elif isinstance(check_value, str):
                check_status = check_value.strip().upper()
                if check_status == "FAIL":
                    codes.append(f"CHECK_{key}")
    return sorted(codes)


def collect_numeric_values(payload: object, keys: tuple[str, ...]) -> list[float]:
    values: list[float] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_lower = str(key).lower()
                if key_lower in keys and isinstance(value, (int, float)):
                    values.append(float(value))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return values


def summarize_numeric(values: list[float]) -> dict[str, float | int] | None:
    if not values:
        return None
    ordered = sorted(values)
    count = len(ordered)
    avg = sum(ordered) / count
    return {
        "count": count,
        "min": ordered[0],
        "max": ordered[-1],
        "avg": round(avg, 4),
        "latest": values[-1],
    }


def list_json_files(artifacts_dir: Path) -> list[Path]:
    if not artifacts_dir.exists():
        return []
    return sorted(artifacts_dir.glob("*.json"), key=lambda item: normalize(item.name).lower())


def select_family_files(paths: list[Path], pattern: re.Pattern[str], limit: int) -> list[Path]:
    candidates = [path for path in paths if pattern.match(path.name)]
    ranked = sorted(
        candidates,
        key=lambda path: (parse_date_score(path.stem), normalize(path.name).lower()),
        reverse=True,
    )
    return ranked[:limit]


def build_family_summary(artifacts_dir: Path, files: list[Path]) -> dict:
    if not files:
        return {
            "status": "MISSING",
            "selected_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "error_count": 0,
            "failure_code_histogram": {},
            "slo": {
                "rto_minutes": None,
                "rpo_hours": None,
                "p95_latency_ms": None,
            },
            "artifacts": [],
        }

    failure_histogram: dict[str, int] = {}
    artifact_rows: list[dict] = []
    pass_count = 0
    fail_count = 0
    error_count = 0
    rto_samples: list[float] = []
    rpo_samples: list[float] = []
    p95_samples: list[float] = []

    for path in files:
        rel = normalize(path.relative_to(artifacts_dir).as_posix())
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
        except (OSError, json.JSONDecodeError):
            status = "ERROR"
            codes = ["JSON_PARSE_ERROR"]
            payload = {}
        else:
            status = infer_status(payload)
            codes = extract_failure_codes(payload)

        if status == "PASS":
            pass_count += 1
        elif status == "FAIL":
            fail_count += 1
        else:
            error_count += 1

        for code in codes:
            failure_histogram[code] = failure_histogram.get(code, 0) + 1

        rto_values = collect_numeric_values(payload, RTO_KEYS)
        rpo_values = collect_numeric_values(payload, RPO_KEYS)
        p95_values = collect_numeric_values(payload, P95_KEYS)
        rto_samples.extend(rto_values)
        rpo_samples.extend(rpo_values)
        p95_samples.extend(p95_values)

        artifact_rows.append(
            {
                "path": rel,
                "date_score": list(parse_date_score(path.stem)),
                "status": status,
                "failure_codes": codes,
            }
        )

    summary_status = "PASS"
    if fail_count > 0:
        summary_status = "FAIL"
    elif error_count > 0:
        summary_status = "ERROR"

    return {
        "status": summary_status,
        "selected_count": len(files),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "error_count": error_count,
        "failure_code_histogram": {key: failure_histogram[key] for key in sorted(failure_histogram.keys())},
        "slo": {
            "rto_minutes": summarize_numeric(rto_samples),
            "rpo_hours": summarize_numeric(rpo_samples),
            "p95_latency_ms": summarize_numeric(p95_samples),
        },
        "artifacts": artifact_rows,
    }


def build_report(artifacts_dir: Path, limit: int, repo_root: Path) -> dict:
    all_json = list_json_files(artifacts_dir)
    families: list[dict] = []

    for key, label, pattern in FAMILY_SPECS:
        selected = select_family_files(all_json, pattern, limit)
        summary = build_family_summary(artifacts_dir, selected)
        families.append(
            {
                "key": key,
                "label": label,
                "pattern": pattern.pattern,
                "limit": limit,
                **summary,
            }
        )

    overall_pass = sum(item["pass_count"] for item in families)
    overall_fail = sum(item["fail_count"] for item in families)
    overall_error = sum(item["error_count"] for item in families)
    overall_selected = sum(item["selected_count"] for item in families)
    overall_status = "PASS"
    if overall_fail > 0:
        overall_status = "FAIL"
    elif overall_error > 0:
        overall_status = "ERROR"

    artifacts_dir_label = normalize(relative_or_name(artifacts_dir, repo_root))
    return {
        "schema_version": 1,
        "artifacts_dir": artifacts_dir_label,
        "limit_per_family": limit,
        "overall": {
            "status": overall_status,
            "selected_count": overall_selected,
            "pass_count": overall_pass,
            "fail_count": overall_fail,
            "error_count": overall_error,
        },
        "families": families,
        "generated_from_commit": git_head_short(repo_root),
    }


def git_head_short(repo_root: Path) -> str:
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return "UNKNOWN"
    if proc.returncode != 0:
        return "UNKNOWN"
    value = (proc.stdout or "").strip()
    return value if value else "UNKNOWN"


def relative_or_name(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.name


def render_txt(payload: dict) -> str:
    lines = [
        "ops_trend_report",
        f"status={payload['overall']['status']}",
        f"selected_count={payload['overall']['selected_count']}",
        f"pass_count={payload['overall']['pass_count']}",
        f"fail_count={payload['overall']['fail_count']}",
        f"error_count={payload['overall']['error_count']}",
        f"limit_per_family={payload['limit_per_family']}",
        f"generated_from_commit={payload['generated_from_commit']}",
    ]

    for family in payload["families"]:
        lines.append("")
        lines.append(f"[{family['key']}] {family['label']}")
        lines.append(f"status={family['status']}")
        lines.append(f"selected_count={family['selected_count']}")
        lines.append(f"pass_count={family['pass_count']}")
        lines.append(f"fail_count={family['fail_count']}")
        lines.append(f"error_count={family['error_count']}")

        histogram = family["failure_code_histogram"]
        if histogram:
            lines.append("failure_code_histogram:")
            for key in sorted(histogram.keys()):
                lines.append(f"- {key}: {histogram[key]}")
        else:
            lines.append("failure_code_histogram: (none)")

        slo = family["slo"]
        lines.append(f"rto_minutes={json.dumps(slo['rto_minutes'], ensure_ascii=False)}")
        lines.append(f"rpo_hours={json.dumps(slo['rpo_hours'], ensure_ascii=False)}")
        lines.append(f"p95_latency_ms={json.dumps(slo['p95_latency_ms'], ensure_ascii=False)}")

        if family["artifacts"]:
            lines.append("artifacts:")
            for item in family["artifacts"]:
                lines.append(
                    f"- {item['path']} status={item['status']} date_score={item['date_score']} "
                    f"failure_codes={item['failure_codes']}"
                )
        else:
            lines.append("artifacts: (missing)")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic Ops trend report")
    parser.add_argument("--artifacts-dir", default=str(DEFAULT_ARTIFACTS_DIR))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output-txt")
    parser.add_argument("--output-json")
    return parser.parse_args()


def resolve_path(base: Path, raw: str) -> Path:
    value = Path(raw)
    if value.is_absolute():
        return value
    return (base / value).resolve()


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()
    artifacts_dir = resolve_path(repo_root, args.artifacts_dir)
    output_txt = (
        resolve_path(repo_root, args.output_txt)
        if args.output_txt
        else artifacts_dir / DEFAULT_REPORT_TXT
    )
    output_json = (
        resolve_path(repo_root, args.output_json)
        if args.output_json
        else artifacts_dir / DEFAULT_REPORT_JSON
    )

    limit = args.limit if args.limit > 0 else 5
    payload = build_report(artifacts_dir=artifacts_dir, limit=limit, repo_root=repo_root)
    txt = render_txt(payload)
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_output(output_txt, txt)
    write_output(output_json, json_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
