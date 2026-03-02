#!/usr/bin/env python3
"""Build deterministic artifact index and optionally fail when stale."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


DEFAULT_ARTIFACT_ROOT = Path("docs/review/mvp_verification_pack/artifacts")
DEFAULT_ARCHIVE_ROOT = Path("docs/review/mvp_verification_pack/archive")
DEFAULT_ARCHIVE_MANIFEST = DEFAULT_ARCHIVE_ROOT / "_ARCHIVE_MANIFEST.json"
DEFAULT_ARCHIVE_KEEP = 1
ARCHIVE_LAYOUT_VERSION = 2
SIDECAR_MANIFEST_SUFFIX = ".manifest.json"
PINNED_CONTRACT_PATH = Path("scripts/contracts/fixed_artifact_paths.json")
PINNED_DOC_PATHS = [
    Path("docs/review/mvp_verification_pack/00_EXEC_SUMMARY.md"),
    Path("docs/review/mvp_verification_pack/03_TEST_PLAN.md"),
    Path("docs/review/mvp_verification_pack/04_TEST_RESULTS.md"),
    Path("docs/review/mvp_verification_pack/06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md"),
    Path("docs/review/verification_pack/README.md"),
    Path("docs/MVP_IMPLEMENTATION_REVIEW_PACK.md"),
]
START_HERE_ITEMS = (
    ("release_gate_dashboard_md", "release_gate_dashboard.md"),
    ("release_gate_dashboard_json", "release_gate_dashboard.json"),
    ("spec_impl_coverage_report_md", "spec_impl_coverage_report.md"),
    ("spec_impl_coverage_gate_json", "spec_impl_coverage_gate.json"),
    ("index_md", "_INDEX.md"),
    ("index_json", "_INDEX.json"),
)

GROUP_ORDER = {
    "gate": 0,
    "report": 1,
    "summary": 2,
    "evidence": 3,
    "misc": 4,
}
DATE_TOKEN_RE = re.compile(r"20\d{2}(?:\d{2}|[xX]{2})(?:\d{2}|[xX]{2})?")
WAVE_TOKEN_RE = re.compile(r"wave(\d+)")
BACKTICK_PATH_RE = re.compile(r"`([^`\r\n]+)`")
BUNDLE_NAME_RE = re.compile(r"^(.+?)__(\d{8}T\d{6}Z)$")
SIDECAR_REQUIRED_FIELDS = (
    "zip_sha256",
    "created_at_kst",
    "source_commit",
    "family_name",
    "included_files",
    "excluded_files",
)


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


def path_key(path: str) -> str:
    return normalize(path).lower()


def is_posix_relative(path: str) -> bool:
    pure = PurePosixPath(path)
    return not pure.is_absolute() and ".." not in pure.parts


def to_repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return normalize(path.resolve().relative_to(repo_root.resolve()).as_posix())
    except ValueError:
        return normalize(path.resolve().as_posix())


def hash_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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
    for path in sorted(artifact_root.rglob("*"), key=lambda item: path_key(item.as_posix())):
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


def artifact_root_relative(repo_root: Path, artifact_root: Path) -> str | None:
    try:
        rel = artifact_root.resolve().relative_to(repo_root.resolve())
        return normalize(rel.as_posix())
    except ValueError:
        return None


def extract_artifact_path_tokens(text: str, artifact_root_rel: str | None) -> set[str]:
    tokens: set[str] = set()
    marker = f"{artifact_root_rel}/" if artifact_root_rel else None
    marker_lower = marker.lower() if marker else None

    for raw in BACKTICK_PATH_RE.findall(text):
        candidate = normalize(raw)
        candidate_lower = candidate.lower()
        rel: str | None = None

        if candidate_lower.startswith("artifacts/"):
            rel = candidate[len("artifacts/") :]
        elif marker and candidate_lower.startswith(marker_lower):
            rel = candidate[len(marker) :]
        elif marker:
            pattern = f"/{marker_lower}"
            idx = candidate_lower.find(pattern)
            if idx >= 0:
                rel = candidate[idx + len(pattern) :]

        if rel is None:
            continue
        rel = normalize(rel)
        if rel and is_posix_relative(rel):
            tokens.add(rel)

    return tokens


def load_contract_pinned_paths(repo_root: Path, artifact_root_rel: str | None) -> set[str]:
    contract_path = repo_root / PINNED_CONTRACT_PATH
    if not contract_path.exists():
        return set()

    payload = json.loads(contract_path.read_text(encoding="utf-8", errors="strict"))
    contract_root = normalize(str(payload.get("artifact_root", "")).strip()).rstrip("/")
    contract_root_lower = contract_root.lower()
    artifact_root_marker = f"{artifact_root_rel}/" if artifact_root_rel else None
    artifact_root_marker_lower = artifact_root_marker.lower() if artifact_root_marker else None

    pinned: set[str] = set()
    for raw in payload.get("fixed_paths", []):
        path = normalize(str(raw))
        path_lower = path.lower()
        rel: str | None = None

        if artifact_root_marker and path_lower.startswith(artifact_root_marker_lower):
            rel = path[len(artifact_root_marker) :]
        elif contract_root and path_lower.startswith(f"{contract_root_lower}/"):
            rel = path[len(contract_root) + 1 :]

        if rel is None:
            continue
        rel = normalize(rel)
        if rel and is_posix_relative(rel):
            pinned.add(rel)

    return pinned


def load_document_pinned_paths(repo_root: Path, artifact_root_rel: str | None) -> set[str]:
    pinned: set[str] = set()
    for rel_doc in PINNED_DOC_PATHS:
        doc_path = repo_root / rel_doc
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8", errors="replace")
        pinned.update(extract_artifact_path_tokens(text, artifact_root_rel))
    return pinned


def load_pinned_paths(repo_root: Path, artifact_root: Path) -> set[str]:
    artifact_root_rel = artifact_root_relative(repo_root, artifact_root)
    pinned = set()
    pinned.update(load_contract_pinned_paths(repo_root, artifact_root_rel))
    pinned.update(load_document_pinned_paths(repo_root, artifact_root_rel))
    return set(sorted(pinned, key=path_key))


def parse_bundle_created_at(bundle_path: Path) -> str:
    match = BUNDLE_NAME_RE.match(bundle_path.stem)
    if match:
        token = match.group(2)
        return (
            f"{token[0:4]}-{token[4:6]}-{token[6:8]}"
            f"T{token[9:11]}:{token[11:13]}:{token[13:15]}Z"
        )
    return datetime.fromtimestamp(bundle_path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_bundle_family(bundle_path: Path) -> str:
    match = BUNDLE_NAME_RE.match(bundle_path.stem)
    if match:
        return match.group(1)
    return bundle_path.stem


def is_legacy_bundle_path(path: Path, archive_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to((archive_root / "bundles").resolve())
    except ValueError:
        return False
    return len(rel.parts) >= 2


def is_sidecar_manifest_path(path: Path, archive_root: Path) -> bool:
    if path.name == "_ARCHIVE_MANIFEST.json":
        return False
    if not path.name.endswith(SIDECAR_MANIFEST_SUFFIX):
        return False
    try:
        rel = path.resolve().relative_to(archive_root.resolve())
    except ValueError:
        return False
    if not rel.parts:
        return False
    return rel.parts[0] != "bundles"


def is_sidecar_zip_path(path: Path, archive_root: Path) -> bool:
    if path.suffix.lower() != ".zip":
        return False
    if is_legacy_bundle_path(path, archive_root):
        return False
    try:
        rel = path.resolve().relative_to(archive_root.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] != "bundles"


def sidecar_manifest_to_zip_path(manifest_path: Path) -> Path:
    if not manifest_path.name.endswith(SIDECAR_MANIFEST_SUFFIX):
        return manifest_path.with_suffix(".zip")
    stem = manifest_path.name[: -len(SIDECAR_MANIFEST_SUFFIX)]
    return manifest_path.with_name(f"{stem}.zip")


def scan_sidecar_archive_payload(archive_root: Path, repo_root: Path) -> dict:
    manifests: list[Path] = []
    if archive_root.exists():
        manifests = sorted(
            [
                path
                for path in archive_root.rglob(f"*{SIDECAR_MANIFEST_SUFFIX}")
                if path.is_file() and is_sidecar_manifest_path(path, archive_root)
            ],
            key=lambda item: path_key(item.as_posix()),
        )

    archive_entries: list[dict] = []
    archived_paths: list[str] = []

    for manifest_path in manifests:
        manifest_rel = to_repo_relative(repo_root, manifest_path)
        zip_path = sidecar_manifest_to_zip_path(manifest_path)
        zip_rel = to_repo_relative(repo_root, zip_path)

        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
        except (OSError, json.JSONDecodeError):
            payload = {}

        included_raw = payload.get("included_files", [])
        included_paths: list[str] = []
        if isinstance(included_raw, list):
            for item in included_raw:
                if not isinstance(item, dict):
                    continue
                rel = normalize(str(item.get("path", "")))
                if rel and is_posix_relative(rel):
                    included_paths.append(rel)

        archived_paths.extend(included_paths)
        family_name = str(payload.get("family_name", "")) or manifest_path.parent.name
        archive_entries.append(
            {
                "family_name": family_name,
                "zip_path": zip_rel,
                "manifest_path": manifest_rel,
                "created_at_kst": str(payload.get("created_at_kst", "")),
                "source_commit": str(payload.get("source_commit", "")),
                "zip_sha256": str(payload.get("zip_sha256", "")),
                "included_file_count": len(included_paths),
                "included_paths": sorted(set(included_paths), key=path_key),
            }
        )

    archive_entries = sorted(
        archive_entries,
        key=lambda item: (
            path_key(str(item.get("family_name", ""))),
            path_key(str(item.get("manifest_path", ""))),
        ),
    )
    archived_paths = sorted(set(archived_paths), key=path_key)

    family_map: dict[str, list[dict]] = {}
    for entry in archive_entries:
        family = str(entry.get("family_name", "misc"))
        family_map.setdefault(family, []).append(entry)

    archive_families: list[dict] = []
    latest_archives: list[dict] = []
    for family in sorted(family_map.keys(), key=path_key):
        entries = sorted(
            family_map[family],
            key=lambda item: path_key(str(item.get("manifest_path", ""))),
        )
        latest = entries[-1]
        archive_families.append(
            {
                "family_name": family,
                "archive_count": len(entries),
                "latest_zip_path": latest.get("zip_path", ""),
                "latest_manifest_path": latest.get("manifest_path", ""),
                "latest_created_at_kst": latest.get("created_at_kst", ""),
                "latest_source_commit": latest.get("source_commit", ""),
                "archives": [
                    {
                        "zip_path": item.get("zip_path", ""),
                        "manifest_path": item.get("manifest_path", ""),
                        "created_at_kst": item.get("created_at_kst", ""),
                        "source_commit": item.get("source_commit", ""),
                        "included_file_count": item.get("included_file_count", 0),
                    }
                    for item in entries
                ],
            }
        )
        latest_archives.append(
            {
                "family_name": family,
                "zip_path": latest.get("zip_path", ""),
                "manifest_path": latest.get("manifest_path", ""),
                "created_at_kst": latest.get("created_at_kst", ""),
                "source_commit": latest.get("source_commit", ""),
                "included_file_count": latest.get("included_file_count", 0),
            }
        )

    recent_sidecar_archives = sorted(
        archive_entries,
        key=lambda item: (
            str(item.get("created_at_kst", "")),
            path_key(str(item.get("manifest_path", ""))),
        ),
        reverse=True,
    )[:10]

    return {
        "manifest_count": len(manifests),
        "archive_count": len(archive_entries),
        "archived_file_count": len(archived_paths),
        "archives": archive_entries,
        "archive_families": archive_families,
        "latest_archives": latest_archives,
        "recent_sidecar_archives": [
            {
                "family_name": item.get("family_name", ""),
                "zip_path": item.get("zip_path", ""),
                "manifest_path": item.get("manifest_path", ""),
                "created_at_kst": item.get("created_at_kst", ""),
                "included_file_count": item.get("included_file_count", 0),
            }
            for item in recent_sidecar_archives
        ],
        "archived_paths": archived_paths,
    }


def build_archive_manifest_payload(archive_root: Path, repo_root: Path) -> dict:
    bundles: list[dict] = []
    archived_files: list[dict] = []

    bundle_files: list[Path] = []
    bundle_dir = archive_root / "bundles"
    if bundle_dir.exists():
        bundle_files = sorted(
            [path for path in bundle_dir.rglob("*.zip") if path.is_file()],
            key=lambda item: path_key(item.as_posix()),
        )

    for bundle_path in bundle_files:
        family = parse_bundle_family(bundle_path)
        created_at_utc = parse_bundle_created_at(bundle_path)
        members: list[str] = []
        try:
            with zipfile.ZipFile(bundle_path, "r") as zf:
                for name in sorted(zf.namelist(), key=path_key):
                    normalized = normalize(name)
                    if normalized.endswith("/"):
                        continue
                    if normalized and is_posix_relative(normalized):
                        members.append(normalized)
        except zipfile.BadZipFile:
            members = []

        bundle_rel = to_repo_relative(repo_root, bundle_path)
        bundles.append(
            {
                "bundle_path": bundle_rel,
                "family": family,
                "created_at_utc": created_at_utc,
                "file_count": len(members),
                "members": members,
            }
        )

        for member in members:
            archived_files.append(
                {
                    "original_path": member,
                    "family": family,
                    "bundle_path": bundle_rel,
                }
            )

    bundles = sorted(bundles, key=lambda item: path_key(item["bundle_path"]))
    archived_files = sorted(
        archived_files,
        key=lambda item: (path_key(item["original_path"]), path_key(item["bundle_path"])),
    )

    return {
        "schema_version": 1,
        "archive_root": to_repo_relative(repo_root, archive_root),
        "bundle_count": len(bundles),
        "archived_file_count": len(archived_files),
        "bundles": bundles,
        "archived_files": archived_files,
    }


def build_group_payload(
    entries: list[ArtifactEntry],
    archive_keep_latest_per_extension: int,
    archive_exclusions: set[str],
) -> list[dict]:
    grouped: dict[tuple[str, str], list[ArtifactEntry]] = {}
    for entry in entries:
        key = (entry.group, entry.family)
        grouped.setdefault(key, []).append(entry)

    groups: dict[str, list[dict]] = {}
    for (group, family), values in grouped.items():
        values_sorted = sorted(values, key=lambda item: path_key(item.path))
        latest_by_ext: dict[str, ArtifactEntry] = {}
        for item in values_sorted:
            current = latest_by_ext.get(item.suffix)
            if current is None:
                latest_by_ext[item.suffix] = item
                continue
            if item.version_rank > current.version_rank:
                latest_by_ext[item.suffix] = item
            elif item.version_rank == current.version_rank and path_key(item.path) > path_key(current.path):
                latest_by_ext[item.suffix] = item

        sorted_by_version = sorted(
            values_sorted,
            key=lambda item: (item.suffix, item.version_rank, path_key(item.path)),
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
            [
                item.path
                for item in values_sorted
                if item.path not in kept_paths and item.path not in archive_exclusions
            ],
            key=path_key,
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
    archive_manifest_path: Path,
    archive_manifest_payload: dict,
    sidecar_payload: dict,
    pinned_paths: set[str],
) -> dict:
    archived_paths = {
        normalize(str(item.get("original_path", "")))
        for item in archive_manifest_payload.get("archived_files", [])
        if normalize(str(item.get("original_path", "")))
    }
    archived_paths.update(
        {
            normalize(path)
            for path in sidecar_payload.get("archived_paths", [])
            if normalize(path)
        }
    )
    archive_exclusions = set(pinned_paths) | archived_paths

    groups = build_group_payload(
        entries,
        archive_keep_latest_per_extension=archive_keep_latest_per_extension,
        archive_exclusions=archive_exclusions,
    )
    indexed_paths = {entry.path for entry in entries}
    start_here = []
    for key, rel_path in START_HERE_ITEMS:
        if key in {"index_md", "index_json"}:
            present = True
        else:
            present = rel_path in indexed_paths
        start_here.append({"key": key, "path": rel_path, "present": present})
    release_gate_dashboard = {
        "markdown_path": "release_gate_dashboard.md",
        "json_path": "release_gate_dashboard.json",
        "markdown_present": "release_gate_dashboard.md" in indexed_paths,
        "json_present": "release_gate_dashboard.json" in indexed_paths,
    }
    spec_impl_coverage = {
        "report_markdown_path": "spec_impl_coverage_report.md",
        "report_json_path": "spec_impl_coverage_report.json",
        "report_text_path": "spec_impl_coverage_report.txt",
        "gate_json_path": "spec_impl_coverage_gate.json",
        "gate_text_path": "spec_impl_coverage_gate.txt",
        "report_markdown_present": "spec_impl_coverage_report.md" in indexed_paths,
        "report_json_present": "spec_impl_coverage_report.json" in indexed_paths,
        "report_text_present": "spec_impl_coverage_report.txt" in indexed_paths,
        "gate_json_present": "spec_impl_coverage_gate.json" in indexed_paths,
        "gate_text_present": "spec_impl_coverage_gate.txt" in indexed_paths,
    }

    latest_files: list[str] = []
    archive_candidates: list[str] = []
    for group in groups:
        for family in group["families"]:
            for ext in sorted(family["latest_by_extension"].keys()):
                latest_files.append(family["latest_by_extension"][ext])
            for rel in family["archive_candidates"]:
                archive_candidates.append(rel)

    latest_files = sorted(set(latest_files), key=path_key)
    archive_candidates = sorted(set(archive_candidates), key=path_key)

    recent_bundles = sorted(
        archive_manifest_payload.get("bundles", []),
        key=lambda item: (
            item.get("created_at_utc", ""),
            path_key(str(item.get("bundle_path", ""))),
        ),
        reverse=True,
    )[:10]

    return {
        "artifact_root": normalize(artifact_root.as_posix()),
        "archive_layout_version": ARCHIVE_LAYOUT_VERSION,
        "indexed_file_count": len(entries),
        "archive_keep_latest_per_extension": archive_keep_latest_per_extension,
        "archive_manifest_path": normalize(archive_manifest_path.as_posix()),
        "pinned_paths_count": len(pinned_paths),
        "archive_summary": {
            "bundle_count": archive_manifest_payload.get("bundle_count", 0),
            "archived_file_count": archive_manifest_payload.get("archived_file_count", 0),
            "sidecar_manifest_count": sidecar_payload.get("manifest_count", 0),
            "sidecar_archive_count": sidecar_payload.get("archive_count", 0),
            "sidecar_archived_file_count": sidecar_payload.get("archived_file_count", 0),
            "recent_bundles": [
                {
                    "bundle_path": item.get("bundle_path", ""),
                    "family": item.get("family", ""),
                    "file_count": item.get("file_count", 0),
                }
                for item in recent_bundles
            ],
            "recent_sidecar_archives": sidecar_payload.get("recent_sidecar_archives", []),
        },
        "archive_families": sidecar_payload.get("archive_families", []),
        "latest_archives": sidecar_payload.get("latest_archives", []),
        "start_here": start_here,
        "release_gate_dashboard": release_gate_dashboard,
        "spec_impl_coverage": spec_impl_coverage,
        "groups": groups,
        "latest_files": latest_files,
        "archive_candidates": archive_candidates,
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Artifact Index",
        "",
        f"- artifact_root: `{payload['artifact_root']}`",
        f"- archive_layout_version: {payload['archive_layout_version']}",
        f"- indexed_file_count: {payload['indexed_file_count']}",
        f"- archive_keep_latest_per_extension: {payload['archive_keep_latest_per_extension']}",
        f"- latest_files_count: {len(payload['latest_files'])}",
        f"- archive_candidates_count: {len(payload['archive_candidates'])}",
        f"- pinned_paths_count: {payload['pinned_paths_count']}",
        f"- archive_manifest_path: `{payload['archive_manifest_path']}`",
        "",
        "## Start Here",
    ]
    for item in payload.get("start_here", []):
        marker = "present" if item.get("present") else "missing"
        lines.append(f"- {item['key']}: `{item['path']}` ({marker})")

    lines.extend(
        [
            "",
        "## Archive Summary",
        f"- bundle_count: {payload['archive_summary']['bundle_count']}",
        f"- archived_file_count: {payload['archive_summary']['archived_file_count']}",
        f"- sidecar_manifest_count: {payload['archive_summary']['sidecar_manifest_count']}",
        f"- sidecar_archive_count: {payload['archive_summary']['sidecar_archive_count']}",
        f"- sidecar_archived_file_count: {payload['archive_summary']['sidecar_archived_file_count']}",
        ]
    )

    lines.append("- recent_bundles:")
    recent_bundles = payload["archive_summary"].get("recent_bundles", [])
    if recent_bundles:
        for bundle in recent_bundles:
            lines.append(
                "  - "
                f"`{bundle['bundle_path']}` "
                f"(family={bundle['family']}, file_count={bundle['file_count']})"
            )
    else:
        lines.append("  - (none)")

    lines.append("- recent_sidecar_archives:")
    recent_sidecars = payload["archive_summary"].get("recent_sidecar_archives", [])
    if recent_sidecars:
        for item in recent_sidecars:
            lines.append(
                "  - "
                f"`{item['zip_path']}` "
                f"(family={item['family_name']}, manifest=`{item['manifest_path']}`, "
                f"file_count={item['included_file_count']})"
            )
    else:
        lines.append("  - (none)")

    lines.append("")
    lines.append("## Latest Archives By Family")
    latest_archives = payload.get("latest_archives", [])
    if latest_archives:
        for item in latest_archives:
            lines.append(
                "- "
                f"{item['family_name']}: zip=`{item['zip_path']}`, "
                f"manifest=`{item['manifest_path']}`, "
                f"created_at_kst={item['created_at_kst']}, "
                f"file_count={item['included_file_count']}"
            )
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Latest Files")
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
            if family["archive_candidates"]:
                for rel in family["archive_candidates"]:
                    lines.append(f"  - `{rel}`")
            else:
                lines.append("  - (none)")
            lines.append("- files:")
            for rel in family["files"]:
                lines.append(f"  - `{rel}`")

    lines.append("")
    return "\n".join(lines)


def resolve_repo_path(repo_root: Path, raw: str) -> Path:
    value = Path(raw)
    if value.is_absolute():
        return value
    return (repo_root / value).resolve()


def build_gate_payload(
    check_mode: bool,
    payload: dict,
    md_path: Path,
    json_path: Path,
    expected_md: str,
    expected_json: str,
    archive_manifest_path: Path,
    expected_archive_manifest: str,
    archive_root: Path,
    repo_root: Path,
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

        if not archive_manifest_path.exists():
            violations.append(
                Violation(
                    code="ARCHIVE_MANIFEST_MISSING",
                    path=normalize(archive_manifest_path.as_posix()),
                    details="archive manifest missing; run scripts/build_artifact_index.py",
                )
            )
        else:
            current_manifest = archive_manifest_path.read_text(encoding="utf-8", errors="strict")
            if current_manifest != expected_archive_manifest:
                violations.append(
                    Violation(
                        code="ARCHIVE_MANIFEST_STALE",
                        path=normalize(archive_manifest_path.as_posix()),
                        details="archive manifest is stale; rebuild artifact index",
                    )
                )

            try:
                manifest_payload = json.loads(current_manifest)
            except json.JSONDecodeError:
                manifest_payload = {"bundles": []}

            for bundle in manifest_payload.get("bundles", []):
                bundle_path = normalize(str(bundle.get("bundle_path", "")))
                if not bundle_path:
                    continue
                bundle_fs_path = resolve_repo_path(repo_root, bundle_path)
                if not bundle_fs_path.exists():
                    violations.append(
                        Violation(
                            code="ARCHIVE_BUNDLE_MISSING",
                            path=bundle_path,
                            details="bundle declared in manifest but file is missing",
                        )
                    )

        sidecar_manifests = sorted(
            [
                path
                for path in archive_root.rglob(f"*{SIDECAR_MANIFEST_SUFFIX}")
                if path.is_file() and is_sidecar_manifest_path(path, archive_root)
            ],
            key=lambda item: path_key(item.as_posix()),
        )
        sidecar_zips = sorted(
            [
                path
                for path in archive_root.rglob("*.zip")
                if path.is_file() and is_sidecar_zip_path(path, archive_root)
            ],
            key=lambda item: path_key(item.as_posix()),
        )

        if sidecar_manifests or sidecar_zips:
            for zip_path in sidecar_zips:
                expected_manifest = zip_path.with_name(
                    f"{zip_path.stem}{SIDECAR_MANIFEST_SUFFIX}"
                )
                if not expected_manifest.exists():
                    violations.append(
                        Violation(
                            code="ARCHIVE_SIDECAR_MANIFEST_MISSING",
                            path=to_repo_relative(repo_root, expected_manifest),
                            details="sidecar zip exists without sibling manifest",
                        )
                    )

            for manifest_path in sidecar_manifests:
                manifest_rel = to_repo_relative(repo_root, manifest_path)
                zip_path = sidecar_manifest_to_zip_path(manifest_path)
                zip_rel = to_repo_relative(repo_root, zip_path)

                try:
                    sidecar_payload = json.loads(
                        manifest_path.read_text(encoding="utf-8", errors="strict")
                    )
                except json.JSONDecodeError:
                    violations.append(
                        Violation(
                            code="ARCHIVE_MANIFEST_INVALID_JSON",
                            path=manifest_rel,
                            details="sidecar manifest is not valid JSON",
                        )
                    )
                    continue

                missing_fields = [
                    field
                    for field in SIDECAR_REQUIRED_FIELDS
                    if field not in sidecar_payload
                ]
                if missing_fields:
                    violations.append(
                        Violation(
                            code="ARCHIVE_MANIFEST_REQUIRED_FIELD_MISSING",
                            path=manifest_rel,
                            details=f"missing required fields: {','.join(missing_fields)}",
                        )
                    )
                    continue

                if not zip_path.exists():
                    violations.append(
                        Violation(
                            code="ARCHIVE_ZIP_MISSING",
                            path=zip_rel,
                            details="sidecar manifest exists but zip file is missing",
                        )
                    )
                    continue

                actual_sha = hash_file_sha256(zip_path)
                expected_sha = normalize(str(sidecar_payload.get("zip_sha256", "")))
                if actual_sha != expected_sha:
                    violations.append(
                        Violation(
                            code="ARCHIVE_ZIP_SHA256_MISMATCH",
                            path=zip_rel,
                            details="manifest zip_sha256 does not match actual zip hash",
                        )
                    )

                included_payload = sidecar_payload.get("included_files", [])
                included_paths: set[str] = set()
                if isinstance(included_payload, list):
                    for item in included_payload:
                        if not isinstance(item, dict):
                            continue
                        rel = normalize(str(item.get("path", "")))
                        if rel and is_posix_relative(rel):
                            included_paths.add(rel)

                zip_members: set[str] = set()
                try:
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        for member in zf.namelist():
                            rel = normalize(member)
                            if rel.endswith("/"):
                                continue
                            if rel and is_posix_relative(rel):
                                zip_members.add(rel)
                except zipfile.BadZipFile:
                    violations.append(
                        Violation(
                            code="ARCHIVE_INCLUDED_LIST_MISMATCH",
                            path=zip_rel,
                            details="zip cannot be read for included_files verification",
                        )
                    )
                    continue

                if included_paths != zip_members:
                    missing_in_manifest = sorted(zip_members - included_paths, key=path_key)
                    extra_in_manifest = sorted(included_paths - zip_members, key=path_key)
                    violations.append(
                        Violation(
                            code="ARCHIVE_INCLUDED_LIST_MISMATCH",
                            path=manifest_rel,
                            details=(
                                "included_files path list differs from zip members "
                                f"(missing_in_manifest={missing_in_manifest}, "
                                f"extra_in_manifest={extra_in_manifest})"
                            ),
                        )
                    )

    return {
        "status": "PASS" if not violations else "FAIL",
        "check_mode": check_mode,
        "artifact_root": payload["artifact_root"],
        "indexed_file_count": payload["indexed_file_count"],
        "archive_manifest_path": normalize(archive_manifest_path.as_posix()),
        "archive_bundle_count": payload["archive_summary"]["bundle_count"],
        "archived_file_count": payload["archive_summary"]["archived_file_count"],
        "archive_sidecar_manifest_count": payload["archive_summary"]["sidecar_manifest_count"],
        "archive_sidecar_count": payload["archive_summary"]["sidecar_archive_count"],
        "archive_sidecar_archived_file_count": payload["archive_summary"]["sidecar_archived_file_count"],
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
        f"archive_manifest_path={payload['archive_manifest_path']}",
        f"archive_bundle_count={payload['archive_bundle_count']}",
        f"archived_file_count={payload['archived_file_count']}",
        f"archive_sidecar_manifest_count={payload['archive_sidecar_manifest_count']}",
        f"archive_sidecar_count={payload['archive_sidecar_count']}",
        f"archive_sidecar_archived_file_count={payload['archive_sidecar_archived_file_count']}",
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
    parser.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE_ROOT))
    parser.add_argument("--archive-manifest", default=str(DEFAULT_ARCHIVE_MANIFEST))
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


def resolve_path(raw: str | None, fallback: Path, base: Path) -> Path:
    if raw:
        value = Path(raw)
        if value.is_absolute():
            return value.resolve()
        return (base / value).resolve()
    return (base / fallback).resolve()


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()

    artifact_root = resolve_path(args.artifact_root, DEFAULT_ARTIFACT_ROOT, repo_root)
    if not artifact_root.exists() or not artifact_root.is_dir():
        sys.stderr.write(f"artifact root not found: {artifact_root.as_posix()}\n")
        return 1

    if args.archive_keep_latest_per_extension < 1:
        sys.stderr.write("--archive-keep-latest-per-extension must be >= 1\n")
        return 1

    archive_root = resolve_path(args.archive_root, DEFAULT_ARCHIVE_ROOT, repo_root)
    archive_manifest_path = resolve_path(args.archive_manifest, DEFAULT_ARCHIVE_MANIFEST, repo_root)
    index_md_path = (
        resolve_path(args.index_md, Path("_INDEX.md"), repo_root)
        if args.index_md
        else (artifact_root / "_INDEX.md").resolve()
    )
    index_json_path = (
        resolve_path(args.index_json, Path("_INDEX.json"), repo_root)
        if args.index_json
        else (artifact_root / "_INDEX.json").resolve()
    )
    gate_txt_path = (
        resolve_path(args.gate_output_txt, Path("artifact_index_gate.txt"), repo_root)
        if args.gate_output_txt
        else (artifact_root / "artifact_index_gate.txt").resolve()
    )
    gate_json_path = (
        resolve_path(args.gate_output_json, Path("artifact_index_gate.json"), repo_root)
        if args.gate_output_json
        else (artifact_root / "artifact_index_gate.json").resolve()
    )

    entries = scan_artifacts(artifact_root)
    pinned_paths = load_pinned_paths(repo_root, artifact_root)
    archive_manifest_payload = build_archive_manifest_payload(archive_root, repo_root)
    sidecar_payload = scan_sidecar_archive_payload(archive_root, repo_root)

    index_payload = build_index_payload(
        artifact_root,
        entries,
        archive_keep_latest_per_extension=args.archive_keep_latest_per_extension,
        archive_manifest_path=archive_manifest_path,
        archive_manifest_payload=archive_manifest_payload,
        sidecar_payload=sidecar_payload,
        pinned_paths=pinned_paths,
    )

    index_md = render_markdown(index_payload)
    index_json = json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n"
    archive_manifest_json = json.dumps(archive_manifest_payload, ensure_ascii=False, indent=2) + "\n"

    if not args.check:
        write_text(index_md_path, index_md)
        write_text(index_json_path, index_json)
        write_text(archive_manifest_path, archive_manifest_json)

    gate_payload = build_gate_payload(
        check_mode=bool(args.check),
        payload=index_payload,
        md_path=index_md_path,
        json_path=index_json_path,
        expected_md=index_md,
        expected_json=index_json,
        archive_manifest_path=archive_manifest_path,
        expected_archive_manifest=archive_manifest_json,
        archive_root=archive_root,
        repo_root=repo_root,
    )

    gate_text = render_gate_text(gate_payload)
    gate_json = json.dumps(gate_payload, ensure_ascii=False, indent=2) + "\n"
    write_text(gate_txt_path, gate_text)
    write_text(gate_json_path, gate_json)

    sys.stdout.write(gate_text)
    return 0 if gate_payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
