#!/usr/bin/env python3
"""Archive optional artifact candidates into family zip bundles."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from build_artifact_index import (
    DEFAULT_ARCHIVE_MANIFEST,
    DEFAULT_ARCHIVE_ROOT,
    DEFAULT_ARTIFACT_ROOT,
    SIDECAR_MANIFEST_SUFFIX,
    build_archive_manifest_payload,
    extract_date_score,
    extract_wave,
    hash_file_sha256,
    load_pinned_paths,
    normalize,
    path_key,
    scan_sidecar_archive_payload,
    to_repo_relative,
)

KST = timezone(timedelta(hours=9))
HEAD_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RETENTION_GROUPS = {"gate", "summary", "report"}


@dataclass(frozen=True)
class Violation:
    code: str
    path: str
    details: str


def resolve_path(raw: str | None, fallback: Path, base: Path) -> Path:
    if raw:
        value = Path(raw)
        if value.is_absolute():
            return value.resolve()
        return (base / value).resolve()
    return (base / fallback).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive artifact candidates into zip bundles")
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--index-json")
    parser.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE_ROOT))
    parser.add_argument("--manifest-json", default=str(DEFAULT_ARCHIVE_MANIFEST))
    parser.add_argument("--output-txt")
    parser.add_argument("--output-json")
    parser.add_argument("--refresh-index", dest="refresh_index", action="store_true", default=True)
    parser.add_argument("--no-refresh-index", dest="refresh_index", action="store_false")
    return parser.parse_args()


def load_index_payload(index_json_path: Path) -> dict:
    return json.loads(index_json_path.read_text(encoding="utf-8", errors="strict"))


def build_file_metadata(index_payload: dict) -> tuple[dict[str, str], dict[str, str]]:
    family_map: dict[str, str] = {}
    group_map: dict[str, str] = {}
    for group in index_payload.get("groups", []):
        group_name = normalize(str(group.get("group", ""))).lower()
        for family in group.get("families", []):
            family_name = str(family.get("family", "misc"))
            for item in family.get("files", []):
                file_path = normalize(str(item))
                if not file_path:
                    continue
                family_map[file_path] = family_name
                group_map[file_path] = group_name
    return family_map, group_map


def sanitize_family_for_filename(family: str) -> str:
    return family.replace("\\", "__").replace("/", "__")


def candidate_rank(path: str) -> tuple[int, tuple[int, int, int], str, str, str]:
    stem = Path(path).stem.lower()
    suffix = Path(path).suffix.lower()
    return (
        extract_wave(stem),
        extract_date_score(stem),
        stem,
        suffix,
        path_key(path),
    )


def apply_retention_exceptions(
    candidates: list[str],
    family_map: dict[str, str],
    group_map: dict[str, str],
) -> tuple[list[str], dict[str, list[str]]]:
    candidate_set = set(candidates)
    grouped_all_files: dict[tuple[str, str], list[str]] = {}
    for rel, family in family_map.items():
        group = group_map.get(rel, "misc")
        if group not in RETENTION_GROUPS:
            continue
        grouped_all_files.setdefault((family, group), []).append(rel)

    excluded: set[str] = set()
    excluded_by_family: dict[str, list[str]] = {}
    for (family, _group), files in grouped_all_files.items():
        latest = max(files, key=candidate_rank)
        if latest in candidate_set:
            excluded.add(latest)
            excluded_by_family.setdefault(family, []).append(latest)

    eligible = sorted({item for item in candidates if item not in excluded}, key=path_key)
    for family in list(excluded_by_family.keys()):
        excluded_by_family[family] = sorted(set(excluded_by_family[family]), key=path_key)
    return eligible, excluded_by_family


def resolve_head_commit(repo_root: Path) -> tuple[str, Violation | None]:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    commit = proc.stdout.strip().lower()
    if proc.returncode != 0 or not HEAD_SHA_RE.match(commit):
        details = proc.stderr.strip() if proc.stderr.strip() else "unable to resolve HEAD commit hash"
        return "", Violation(
            code="ARCHIVE_SOURCE_COMMIT_RESOLVE_FAILED",
            path=normalize(repo_root.as_posix()),
            details=details,
        )
    return commit, None


def allocate_bundle_paths(
    archive_root: Path,
    family_name: str,
    date_token: str,
) -> tuple[Path, Path]:
    safe_family = sanitize_family_for_filename(family_name)
    family_dir = archive_root / safe_family
    family_dir.mkdir(parents=True, exist_ok=True)

    base = f"{date_token}_{safe_family}"
    suffix = 1
    while True:
        suffix_token = "" if suffix == 1 else f"_v{suffix:02d}"
        zip_path = family_dir / f"{base}{suffix_token}.zip"
        manifest_path = family_dir / f"{base}{suffix_token}{SIDECAR_MANIFEST_SUFFIX}"
        if not zip_path.exists() and not manifest_path.exists():
            return zip_path, manifest_path
        suffix += 1


def create_sidecar_bundle(
    repo_root: Path,
    artifact_root: Path,
    archive_root: Path,
    family_name: str,
    files: list[str],
    excluded_files: list[str],
    source_commit: str,
    created_at_kst: str,
    date_token: str,
) -> tuple[dict | None, list[str], Violation | None]:
    missing: list[str] = []
    source_files: list[Path] = []
    rel_files: list[str] = []
    for rel in files:
        source_path = (artifact_root / rel).resolve()
        if not source_path.exists():
            missing.append(rel)
            continue
        source_files.append(source_path)
        rel_files.append(rel)

    if not rel_files:
        return None, sorted(set(missing), key=path_key), None

    zip_path, manifest_path = allocate_bundle_paths(
        archive_root=archive_root,
        family_name=family_name,
        date_token=date_token,
    )
    temp_zip_path = zip_path.with_suffix(f"{zip_path.suffix}.tmp")
    try:
        with zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for source_path, rel in zip(source_files, rel_files):
                zf.write(source_path, arcname=rel)
        temp_zip_path.replace(zip_path)
    except OSError as exc:
        if temp_zip_path.exists():
            temp_zip_path.unlink(missing_ok=True)
        return None, sorted(set(missing), key=path_key), Violation(
            code="ARCHIVE_BUNDLE_CREATE_FAILED",
            path=normalize(zip_path.as_posix()),
            details=f"failed to create sidecar zip: {exc}",
        )

    included_files = sorted(
        [{"path": rel, "sha256": hash_file_sha256(source_path)} for source_path, rel in zip(source_files, rel_files)],
        key=lambda item: path_key(str(item["path"])),
    )
    zip_sha256 = hash_file_sha256(zip_path)
    zip_rel = to_repo_relative(repo_root, zip_path)
    manifest_rel = to_repo_relative(repo_root, manifest_path)

    manifest_payload = {
        "schema_version": 1,
        "family_name": family_name,
        "created_at_kst": created_at_kst,
        "source_commit": source_commit,
        "zip_path": zip_rel,
        "manifest_path": manifest_rel,
        "zip_sha256": zip_sha256,
        "included_files": included_files,
        "excluded_files": sorted(set(excluded_files), key=path_key),
    }

    try:
        manifest_path.write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return None, sorted(set(missing), key=path_key), Violation(
            code="ARCHIVE_MANIFEST_WRITE_FAILED",
            path=normalize(manifest_path.as_posix()),
            details=f"failed to write sidecar manifest: {exc}",
        )

    bundle_entry = {
        "bundle_path": normalize(zip_path.as_posix()),
        "manifest_path": normalize(manifest_path.as_posix()),
        "family": family_name,
        "file_count": len(included_files),
        "members": [item["path"] for item in included_files],
        "excluded_files": sorted(set(excluded_files), key=path_key),
    }
    return bundle_entry, sorted(set(missing), key=path_key), None


def refresh_index(
    repo_root: Path,
    artifact_root: Path,
    archive_root: Path,
    manifest_path: Path,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str((repo_root / "scripts" / "build_artifact_index.py").resolve()),
        "--artifact-root",
        str(artifact_root),
        "--archive-root",
        str(archive_root),
        "--archive-manifest",
        str(manifest_path),
        "--index-md",
        str((artifact_root / "_INDEX.md").resolve()),
        "--index-json",
        str((artifact_root / "_INDEX.json").resolve()),
        "--gate-output-txt",
        str((artifact_root / "artifact_index_gate.txt").resolve()),
        "--gate-output-json",
        str((artifact_root / "artifact_index_gate.json").resolve()),
    ]
    return subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def render_report_text(payload: dict) -> str:
    lines = [
        "artifact_archive_report",
        f"status={payload['status']}",
        f"artifact_root={payload['artifact_root']}",
        f"archive_root={payload['archive_root']}",
        f"manifest_path={payload['manifest_path']}",
        f"manifest_bundle_count={payload['manifest_bundle_count']}",
        f"manifest_archived_file_count={payload['manifest_archived_file_count']}",
        f"sidecar_manifest_count={payload['sidecar_manifest_count']}",
        f"sidecar_archive_count={payload['sidecar_archive_count']}",
        f"sidecar_archived_file_count={payload['sidecar_archived_file_count']}",
        f"candidate_count={payload['candidate_count']}",
        f"eligible_count={payload['eligible_count']}",
        f"retention_excluded_count={payload['retention_excluded_count']}",
        f"archived_file_count={payload['archived_file_count']}",
        f"created_bundle_count={payload['created_bundle_count']}",
        f"skipped_pinned_count={payload['skipped_pinned_count']}",
        f"skipped_already_archived_count={payload['skipped_already_archived_count']}",
        f"skipped_missing_count={payload['skipped_missing_count']}",
        f"refresh_index={payload['refresh_index']}",
        f"refresh_index_exit_code={payload['refresh_index_exit_code']}",
        f"violation_count={payload['violation_count']}",
    ]

    if payload["created_bundles"]:
        lines.append("created_bundles:")
        for item in payload["created_bundles"]:
            lines.append(
                f"- {item['bundle_path']} family={item['family']} file_count={item['file_count']} "
                f"manifest={item['manifest_path']}"
            )

    if payload["retention_excluded"]:
        lines.append("retention_excluded:")
        for item in payload["retention_excluded"]:
            lines.append(f"- {item}")

    if payload["violations"]:
        lines.append("violations:")
        for item in payload["violations"]:
            lines.append(f"- [{item['code']}] {item['path']} :: {item['details']}")

    if payload["refresh_index_stdout"]:
        lines.append("refresh_index_stdout:")
        lines.extend(payload["refresh_index_stdout"].strip().splitlines())

    if payload["refresh_index_stderr"]:
        lines.append("refresh_index_stderr:")
        lines.extend(payload["refresh_index_stderr"].strip().splitlines())

    return "\n".join(lines) + "\n"


def write_text(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_stdout_safe(text: str) -> None:
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(text.encode(encoding, errors="replace"))


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()

    artifact_root = resolve_path(args.artifact_root, DEFAULT_ARTIFACT_ROOT, repo_root)
    index_json_path = (
        resolve_path(args.index_json, Path("_INDEX.json"), repo_root)
        if args.index_json
        else (artifact_root / "_INDEX.json").resolve()
    )
    archive_root = resolve_path(args.archive_root, DEFAULT_ARCHIVE_ROOT, repo_root)
    manifest_path = resolve_path(args.manifest_json, DEFAULT_ARCHIVE_MANIFEST, repo_root)
    output_txt_path = (
        resolve_path(args.output_txt, Path("artifact_archive_report.txt"), repo_root)
        if args.output_txt
        else (artifact_root / "artifact_archive_report.txt").resolve()
    )
    output_json_path = (
        resolve_path(args.output_json, Path("artifact_archive_report.json"), repo_root)
        if args.output_json
        else (artifact_root / "artifact_archive_report.json").resolve()
    )

    violations: list[Violation] = []

    if not artifact_root.exists() or not artifact_root.is_dir():
        violations.append(
            Violation(
                code="ARTIFACT_ROOT_MISSING",
                path=normalize(artifact_root.as_posix()),
                details="artifact root directory not found",
            )
        )

    if not index_json_path.exists():
        violations.append(
            Violation(
                code="INDEX_JSON_MISSING",
                path=normalize(index_json_path.as_posix()),
                details="_INDEX.json not found; run scripts/build_artifact_index.py first",
            )
        )

    index_payload: dict = {}
    family_map: dict[str, str] = {}
    group_map: dict[str, str] = {}
    candidates: list[str] = []
    if not violations:
        index_payload = load_index_payload(index_json_path)
        family_map, group_map = build_file_metadata(index_payload)
        candidates = sorted(
            {
                normalize(str(path))
                for path in index_payload.get("archive_candidates", [])
                if normalize(str(path))
            },
            key=path_key,
        )

    pinned_paths = load_pinned_paths(repo_root, artifact_root)
    legacy_manifest_payload = build_archive_manifest_payload(archive_root, repo_root)
    sidecar_payload = scan_sidecar_archive_payload(archive_root, repo_root)
    already_archived = {
        normalize(str(item.get("original_path", "")))
        for item in legacy_manifest_payload.get("archived_files", [])
        if normalize(str(item.get("original_path", "")))
    }
    already_archived.update(
        {
            normalize(path)
            for path in sidecar_payload.get("archived_paths", [])
            if normalize(path)
        }
    )

    skipped_pinned: list[str] = []
    skipped_already_archived: list[str] = []
    eligible_before_retention: list[str] = []
    for candidate in candidates:
        if candidate in pinned_paths:
            skipped_pinned.append(candidate)
            continue
        if candidate in already_archived:
            skipped_already_archived.append(candidate)
            continue
        eligible_before_retention.append(candidate)

    eligible, retention_excluded_by_family = apply_retention_exceptions(
        candidates=eligible_before_retention,
        family_map=family_map,
        group_map=group_map,
    )
    retention_excluded = sorted(
        {item for values in retention_excluded_by_family.values() for item in values},
        key=path_key,
    )

    source_commit, commit_violation = resolve_head_commit(repo_root)
    if commit_violation is not None:
        violations.append(commit_violation)

    now_kst = datetime.now(tz=KST)
    date_token = now_kst.strftime("%Y%m%d")
    created_at_kst = now_kst.strftime("%Y-%m-%d %H:%M:%S +09:00")
    started_at_utc = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    family_to_files: dict[str, list[str]] = {}
    for rel in eligible:
        family = family_map.get(rel, "misc")
        family_to_files.setdefault(family, []).append(rel)

    created_bundles: list[dict] = []
    archived_files_this_run: list[str] = []
    skipped_missing: list[str] = []

    for family in sorted(family_to_files.keys(), key=path_key):
        files = sorted(set(family_to_files[family]), key=path_key)
        bundle_entry, missing, bundle_violation = create_sidecar_bundle(
            repo_root=repo_root,
            artifact_root=artifact_root,
            archive_root=archive_root,
            family_name=family,
            files=files,
            excluded_files=retention_excluded_by_family.get(family, []),
            source_commit=source_commit,
            created_at_kst=created_at_kst,
            date_token=date_token,
        )
        skipped_missing.extend(missing)
        if bundle_violation is not None:
            violations.append(bundle_violation)
            continue
        if bundle_entry is not None:
            created_bundles.append(bundle_entry)
            archived_files_this_run.extend(bundle_entry["members"])

    refreshed_legacy_manifest = build_archive_manifest_payload(archive_root, repo_root)
    manifest_text = json.dumps(refreshed_legacy_manifest, ensure_ascii=False, indent=2) + "\n"
    write_text(manifest_path, manifest_text)
    refreshed_sidecar_payload = scan_sidecar_archive_payload(archive_root, repo_root)

    refresh_proc: subprocess.CompletedProcess[str] | None = None
    if args.refresh_index:
        refresh_proc = refresh_index(
            repo_root=repo_root,
            artifact_root=artifact_root,
            archive_root=archive_root,
            manifest_path=manifest_path,
        )
        if refresh_proc.returncode != 0:
            violations.append(
                Violation(
                    code="INDEX_REFRESH_FAILED",
                    path=normalize((artifact_root / "artifact_index_gate.txt").as_posix()),
                    details="build_artifact_index.py returned non-zero during refresh",
                )
            )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "artifact_root": normalize(artifact_root.as_posix()),
        "archive_root": normalize(archive_root.as_posix()),
        "manifest_path": normalize(manifest_path.as_posix()),
        "manifest_bundle_count": refreshed_legacy_manifest.get("bundle_count", 0),
        "manifest_archived_file_count": refreshed_legacy_manifest.get("archived_file_count", 0),
        "sidecar_manifest_count": refreshed_sidecar_payload.get("manifest_count", 0),
        "sidecar_archive_count": refreshed_sidecar_payload.get("archive_count", 0),
        "sidecar_archived_file_count": refreshed_sidecar_payload.get("archived_file_count", 0),
        "started_at_utc": started_at_utc,
        "candidate_count": len(candidates),
        "eligible_count": len(eligible),
        "retention_excluded_count": len(retention_excluded),
        "retention_excluded": retention_excluded,
        "archived_file_count": len(sorted(set(archived_files_this_run), key=path_key)),
        "created_bundle_count": len(created_bundles),
        "created_bundles": created_bundles,
        "skipped_pinned_count": len(skipped_pinned),
        "skipped_pinned": sorted(set(skipped_pinned), key=path_key),
        "skipped_already_archived_count": len(skipped_already_archived),
        "skipped_already_archived": sorted(set(skipped_already_archived), key=path_key),
        "skipped_missing_count": len(skipped_missing),
        "skipped_missing": sorted(set(skipped_missing), key=path_key),
        "refresh_index": bool(args.refresh_index),
        "refresh_index_exit_code": None if refresh_proc is None else refresh_proc.returncode,
        "refresh_index_stdout": "" if refresh_proc is None else refresh_proc.stdout,
        "refresh_index_stderr": "" if refresh_proc is None else refresh_proc.stderr,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }

    report_text = render_report_text(payload)
    report_json = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_text(output_txt_path, report_text)
    write_text(output_json_path, report_json)

    write_stdout_safe(report_text)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
