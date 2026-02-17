#!/usr/bin/env python3
"""Detect Notion sync target changes and compute an idempotent sync key."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
SPEC_SYNC_REPORT = ROOT / "spec_sync_report.md"

# Canonical mapping from local source files to Notion pages.
SYNC_TARGETS: Dict[str, str] = {
    "docs/references/Summary of key features.csv": "https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149",
    "docs/references/CS AI Chatbot_Requirements Statement.csv": "https://www.notion.so/2ed405a3a720816594e4dc34972174ec",
    "docs/references/Development environment.csv": "https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7",
    "docs/references/google_ready_api_spec_v0.3_20260216.xlsx": "https://www.notion.so/2ed405a3a720816594e4dc34972174ec",
    "docs/references/CS_AI_CHATBOT_DB.xlsx": "https://www.notion.so/2ed405a3a720812180d9d508b77f31a4",
    "docs/uiux/CS_RAG_UI_UX_설계서.xlsx": "https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444",
    # Legacy aliases (support old locations if they still appear in diffs).
    "Summary of key features.csv": "https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149",
    "CS AI Chatbot_Requirements Statement.csv": "https://www.notion.so/2ed405a3a720816594e4dc34972174ec",
    "Development environment.csv": "https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7",
    "google_ready_api_spec_v0.3_20260216.xlsx": "https://www.notion.so/2ed405a3a720816594e4dc34972174ec",
    "CS_AI_CHATBOT_DB.xlsx": "https://www.notion.so/2ed405a3a720812180d9d508b77f31a4",
    "CS_RAG_UI_UX_설계서.xlsx": "https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444",
}


def _run_git(args: List[str], check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def _changed_files(base_ref: str, head_ref: str) -> List[str]:
    out = _run_git(["diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...{head_ref}"])
    changed = []
    for line in out.splitlines():
        normalized = _normalize_path(line)
        if normalized:
            changed.append(normalized)
    return changed


def _blob_oid(head_ref: str, path: str) -> str:
    # Return a stable token even if file resolution fails.
    proc = subprocess.run(
        ["git", "rev-parse", f"{head_ref}:{path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        return "MISSING"
    return proc.stdout.strip()


def _sync_key(head_ref: str, changed_targets: List[str]) -> str:
    sha = hashlib.sha256()
    for path in changed_targets:
        sha.update(path.encode("utf-8"))
        sha.update(b"\0")
        sha.update(_blob_oid(head_ref, path).encode("utf-8"))
        sha.update(b"\n")
    return sha.hexdigest()[:16]


def _contains_marker(sync_key: str) -> bool:
    if not sync_key or not SPEC_SYNC_REPORT.exists():
        return False
    marker = f"[[AUTO_SYNC:SPEC_SYNC_REPORT:{sync_key}]]"
    return marker in SPEC_SYNC_REPORT.read_text(encoding="utf-8")


def _append_github_output(path: Path, key: str, value: str) -> None:
    with path.open("a", encoding="utf-8") as fh:
        if "\n" in value:
            fh.write(f"{key}<<__EOF__\n{value}\n__EOF__\n")
        else:
            fh.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate for zero-touch Notion sync.")
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--output-json", required=False)
    parser.add_argument("--github-output", required=False)
    args = parser.parse_args()

    changed = _changed_files(args.base_ref, args.head_ref)
    changed_set = set(changed)
    changed_targets = [path for path in SYNC_TARGETS.keys() if path in changed_set]
    mapping = {path: SYNC_TARGETS[path] for path in changed_targets}

    sync_key = _sync_key(args.head_ref, changed_targets) if changed_targets else ""
    marker = f"[[AUTO_SYNC:SPEC_SYNC_REPORT:{sync_key}]]" if sync_key else ""
    already_synced = _contains_marker(sync_key)

    result = {
        "base_ref": args.base_ref,
        "head_ref": args.head_ref,
        "changed": bool(changed_targets),
        "changed_count": len(changed_targets),
        "changed_targets": changed_targets,
        "mapping": mapping,
        "sync_key": sync_key,
        "marker": marker,
        "already_synced": already_synced,
    }

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)

    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")

    if args.github_output:
        gh = Path(args.github_output)
        _append_github_output(gh, "notion_sync_changed", "true" if result["changed"] else "false")
        _append_github_output(
            gh,
            "notion_sync_already_synced",
            "true" if result["already_synced"] else "false",
        )
        _append_github_output(gh, "notion_sync_changed_count", str(result["changed_count"]))
        _append_github_output(gh, "notion_sync_key", result["sync_key"])
        _append_github_output(gh, "notion_sync_marker", result["marker"])
        _append_github_output(
            gh,
            "notion_sync_changed_targets",
            "\n".join(result["changed_targets"]),
        )
        _append_github_output(
            gh,
            "notion_sync_changed_targets_json",
            json.dumps(result["changed_targets"], ensure_ascii=False),
        )
        _append_github_output(
            gh,
            "notion_sync_mapping_json",
            json.dumps(result["mapping"], ensure_ascii=False),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

