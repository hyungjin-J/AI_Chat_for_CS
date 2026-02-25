#!/usr/bin/env python3
"""Build deterministic artifact index and optionally fail when stale."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_ARTIFACT_ROOT = Path("docs/review/mvp_verification_pack/artifacts")
DEFAULT_ARCHIVE_KEEP = 1
GROUP_ORDER = {
    "gate": 0,
    "report": 1,
    "summary": 2,
    "evidence": 3,
    "misc": 4,
}
DATE_TOKEN_RE = re.compile(r"20\d{2}(?:\d{2}|[xX]{2})(?:\d{2}|[xX]{2})?")
WAVE_TOKEN_RE = re.compile(r"wave(\d+)")


@dataclass(frozen=True)
class ArtifactEntry:
    path: str
    stem: str
    suffix: str
    family: str
    group: str
    wave: int
    date_score: tuple[int, int, int]
    version_rank: tuple[int, tuple[int, int, int], str, str]


@dataclass(frozen=True)
class Violation:
    code: str
    path: str
    details: str


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
    parsed = [parse_date_token(token) for token in tokens]
    return max(parsed)


def extract_wave(stem: str) -> int:
    waves = [int(raw) for raw in WAVE_TOKEN_RE.findall(stem)]
    if not waves:
        return -1
    return max(waves)


def classify_group(stem_lower: str) -> str:
    if "_gate" in stem_lower:
        return "gate"
    if "_report" in stem_lower:
        return "report"
    if "_summary" in stem_lower:
        return "summary"
    evidence_tokens = ("check", "lint", "validate", "smoke", "status", "scan", "output")
    if any(token in stem_lower for token in evidence_tokens):
        return "evidence"
    return "misc"


def normalize_family(stem_lower: str) -> str:
    normalized = WAVE_TOKEN_RE.sub("waveN", stem_lower)
    normalized = DATE_TOKEN_RE.sub("DATE", normalized)
    normalized = re.sub(r"_DATE$", "", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def should_skip(path: Path) -> bool:
    name = path.name.lower()
    return name in {"_index.md", "_index.json", "artifact_index_gate.txt", "artifact_index_gate.json"}


def scan_artifacts(artifact_root: Path) -> list[ArtifactEntry]:
    entries: list[ArtifactEntry] = []
    for path in sorted(artifact_root.rglob("*"), key=lambda item: normalize(item.as_posix()).lower()):
        if not path.is_file():
            continue
        if should_skip(path):
            continue
        rel = normalize(path.relative_to(artifact_root).as_posix())
        stem = path.stem
        stem_lower = stem.lower()
        suffix = path.suffix.lower()
        group = classify_group(stem_lower)
        family = normalize_family(stem_lower)
        wave = extract_wave(stem_lower)
        date_score = extract_date_score(stem_lower)
        version_rank = (wave, date_score, stem_lower, suffix)
        entries.append(
            ArtifactEntry(
                path=rel,
                stem=stem,
                suffix=suffix,
                family=family,
                group=group,
                wave=wave,
                date_score=date_score,
                version_rank=version_rank,
            )
        )
    return entries


def build_group_payload(entries: list[ArtifactEntry], archive_keep_latest_per_extension: int) -> list[dict]:
    grouped: dict[tuple[str, str], list[ArtifactEntry]] = {}
    for entry in entries:
        key = (entry.group, entry.family)
        grouped.setdefault(key, []).append(entry)

    groups: dict[str, list[dict]] = {}
    for (group, family), values in grouped.items():
        values_sorted = sorted(values, key=lambda item: item.path.lower())
        latest_by_ext: dict[str, ArtifactEntry] = {}
        for item in values_sorted:
            current = latest_by_ext.get(item.suffix)
            if current is None:
                latest_by_ext[item.suffix] = item
                continue
            if item.version_rank > current.version_rank:
                latest_by_ext[item.suffix] = item
            elif item.version_rank == current.version_rank and item.path.lower() > current.path.lower():
                latest_by_ext[item.suffix] = item

        sorted_by_version = sorted(
            values_sorted,
            key=lambda item: (item.suffix, item.version_rank, item.path.lower()),
            reverse=True,
        )
        keep_budget: dict[str, int] = {}
        kept_paths: set[str] = set()
        for item in sorted_by_version:
            current = keep_budget.get(item.suffix, 0)
            if current >= archive_keep_latest_per_extension:
                continue
            kept_paths.add(item.path)
            keep_budget[item.suffix] = current + 1
        archive_candidates = sorted(
            [item.path for item in values_sorted if item.path not in kept_paths],
            key=lambda item: item.lower(),
        )

        family_payload = {
            "family": family,
            "file_count": len(values_sorted),
            "files": [item.path for item in values_sorted],
            "latest_by_extension": {
                ext: latest_by_ext[ext].path for ext in sorted(latest_by_ext.keys())
            },
            "archive_candidates": archive_candidates,
        }
        groups.setdefault(group, []).append(family_payload)

    result: list[dict] = []
    for group_name in sorted(groups.keys(), key=lambda name: (GROUP_ORDER.get(name, 99), name)):
        families = sorted(groups[group_name], key=lambda item: item["family"])
        result.append(
            {
                "group": group_name,
                "family_count": len(families),
                "families": families,
            }
        )
    return result


def build_index_payload(
    artifact_root: Path,
    entries: list[ArtifactEntry],
    archive_keep_latest_per_extension: int,
) -> dict:
    groups = build_group_payload(entries, archive_keep_latest_per_extension=archive_keep_latest_per_extension)
    latest_files: list[str] = []
    archive_candidates: list[str] = []
    for group in groups:
        for family in group["families"]:
            for ext in sorted(family["latest_by_extension"].keys()):
                latest_files.append(family["latest_by_extension"][ext])
            for rel in family["archive_candidates"]:
                archive_candidates.append(rel)
    latest_files = sorted(set(latest_files), key=lambda item: item.lower())
    archive_candidates = sorted(set(archive_candidates), key=lambda item: item.lower())

    return {
        "artifact_root": normalize(artifact_root.as_posix()),
        "indexed_file_count": len(entries),
        "archive_keep_latest_per_extension": archive_keep_latest_per_extension,
        "groups": groups,
        "latest_files": latest_files,
        "archive_candidates": archive_candidates,
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Artifact Index",
        "",
        f"- artifact_root: `{payload['artifact_root']}`",
        f"- indexed_file_count: {payload['indexed_file_count']}",
        f"- archive_keep_latest_per_extension: {payload['archive_keep_latest_per_extension']}",
        f"- latest_files_count: {len(payload['latest_files'])}",
        f"- archive_candidates_count: {len(payload['archive_candidates'])}",
        "",
        "## Latest Files",
    ]
    if payload["latest_files"]:
        for rel in payload["latest_files"]:
            lines.append(f"- `{rel}`")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Archive Candidates (Optional)")
    if payload["archive_candidates"]:
        for rel in payload["archive_candidates"]:
            lines.append(f"- `{rel}`")
    else:
        lines.append("- (none)")

    for group in payload["groups"]:
        lines.append("")
        lines.append(f"## Group: {group['group']}")
        lines.append(f"- family_count: {group['family_count']}")
        for family in group["families"]:
            lines.append("")
            lines.append(f"### {family['family']}")
            lines.append(f"- file_count: {family['file_count']}")
            lines.append("- latest_by_extension:")
            for ext, rel in family["latest_by_extension"].items():
                lines.append(f"  - `{ext}`: `{rel}`")
            lines.append("- archive_candidates:")
            for rel in family["archive_candidates"]:
                lines.append(f"  - `{rel}`")
            lines.append("- files:")
            for rel in family["files"]:
                lines.append(f"  - `{rel}`")
    lines.append("")
    return "\n".join(lines)


def build_gate_payload(
    check_mode: bool,
    payload: dict,
    md_path: Path,
    json_path: Path,
    expected_md: str,
    expected_json: str,
) -> dict:
    violations: list[Violation] = []

    if check_mode:
        for target in (md_path, json_path):
            if not target.exists():
                violations.append(
                    Violation(
                        code="INDEX_MISSING",
                        path=normalize(target.as_posix()),
                        details="index file not found; run scripts/build_artifact_index.py",
                    )
                )
        if md_path.exists():
            current = md_path.read_text(encoding="utf-8", errors="strict")
            if current != expected_md:
                violations.append(
                    Violation(
                        code="INDEX_STALE",
                        path=normalize(md_path.as_posix()),
                        details="markdown index is stale; rebuild artifact index",
                    )
                )
        if json_path.exists():
            current = json_path.read_text(encoding="utf-8", errors="strict")
            if current != expected_json:
                violations.append(
                    Violation(
                        code="INDEX_STALE",
                        path=normalize(json_path.as_posix()),
                        details="json index is stale; rebuild artifact index",
                    )
                )

    return {
        "status": "PASS" if not violations else "FAIL",
        "check_mode": check_mode,
        "artifact_root": payload["artifact_root"],
        "indexed_file_count": payload["indexed_file_count"],
        "index_md_path": normalize(md_path.as_posix()),
        "index_json_path": normalize(json_path.as_posix()),
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }


def render_gate_text(payload: dict) -> str:
    lines = [
        "artifact_index_gate",
        f"status={payload['status']}",
        f"check_mode={payload['check_mode']}",
        f"indexed_file_count={payload['indexed_file_count']}",
        f"index_md_path={payload['index_md_path']}",
        f"index_json_path={payload['index_json_path']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(f"- [{item['code']}] {item['path']} :: {item['details']}")
    return "\n".join(lines) + "\n"


def write_text(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic artifact index")
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--index-md")
    parser.add_argument("--index-json")
    parser.add_argument("--check", action="store_true", help="Fail when existing index files are stale/missing")
    parser.add_argument(
        "--archive-keep-latest-per-extension",
        type=int,
        default=DEFAULT_ARCHIVE_KEEP,
        help="How many latest files to keep per extension before marking older files as optional archive candidates",
    )
    parser.add_argument("--gate-output-txt")
    parser.add_argument("--gate-output-json")
    return parser.parse_args()


def resolve_path(base: Path, raw: str | None, fallback_name: str) -> Path:
    if raw:
        value = Path(raw)
        if value.is_absolute():
            return value
        return (Path.cwd() / value).resolve()
    return (base / fallback_name).resolve()


def main() -> int:
    args = parse_args()
    artifact_root_raw = Path(args.artifact_root)
    artifact_root = artifact_root_raw if artifact_root_raw.is_absolute() else (Path.cwd() / artifact_root_raw)
    artifact_root = artifact_root.resolve()

    if not artifact_root.exists() or not artifact_root.is_dir():
        sys.stderr.write(f"artifact root not found: {artifact_root.as_posix()}\n")
        return 1

    if args.archive_keep_latest_per_extension < 1:
        sys.stderr.write("--archive-keep-latest-per-extension must be >= 1\n")
        return 1

    index_md_path = resolve_path(artifact_root, args.index_md, "_INDEX.md")
    index_json_path = resolve_path(artifact_root, args.index_json, "_INDEX.json")
    gate_txt_path = resolve_path(artifact_root, args.gate_output_txt, "artifact_index_gate.txt")
    gate_json_path = resolve_path(artifact_root, args.gate_output_json, "artifact_index_gate.json")

    entries = scan_artifacts(artifact_root)
    index_payload = build_index_payload(
        artifact_root,
        entries,
        archive_keep_latest_per_extension=args.archive_keep_latest_per_extension,
    )
    index_md = render_markdown(index_payload)
    index_json = json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n"

    if not args.check:
        write_text(index_md_path, index_md)
        write_text(index_json_path, index_json)

    gate_payload = build_gate_payload(
        check_mode=bool(args.check),
        payload=index_payload,
        md_path=index_md_path,
        json_path=index_json_path,
        expected_md=index_md,
        expected_json=index_json,
    )
    gate_text = render_gate_text(gate_payload)
    gate_json = json.dumps(gate_payload, ensure_ascii=False, indent=2) + "\n"
    write_text(gate_txt_path, gate_text)
    write_text(gate_json_path, gate_json)

    sys.stdout.write(gate_text)
    return 0 if gate_payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
