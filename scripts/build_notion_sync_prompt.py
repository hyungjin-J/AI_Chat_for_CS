#!/usr/bin/env python3
"""Build a deterministic prompt for Codex Notion sync execution in CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_context(path: Path) -> Dict[str, Any]:
    # Accept both UTF-8 and UTF-8 BOM files for CI/local shell compatibility.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _render_mapping(changed_targets: List[str], mapping: Dict[str, str]) -> str:
    lines = []
    for path in changed_targets:
        lines.append(f"- `{path}` -> {mapping[path]}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render CI prompt for Codex Notion auto-sync.")
    parser.add_argument("--context-json", required=True)
    parser.add_argument("--sync-key", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--pr-number", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    context = _load_context(Path(args.context_json))
    changed_targets = context.get("changed_targets", [])
    mapping = context.get("mapping", {})

    if not changed_targets:
        raise ValueError("No changed targets in context; prompt rendering should not run.")

    targets_block = _render_mapping(changed_targets, mapping)
    commit_short = args.commit_sha[:7]

    prompt = f"""You are Codex running in CI for AI_Chatbot.

Mission:
1) Update mapped Notion pages for changed sync-target files via Notion MCP.
2) Update local `spec_sync_report.md` with a deterministic auto-sync record.

Context:
- PR number: {args.pr_number}
- Source commit: `{args.commit_sha}`
- Source commit short: `{commit_short}`
- Sync key: `{args.sync_key}`
- Sync marker for report: `[[AUTO_SYNC:SPEC_SYNC_REPORT:{args.sync_key}]]`

Changed sync-target files and Notion mappings:
{targets_block}

Hard constraints (Fail-Closed):
- Use Notion MCP. If Notion access fails for any target, stop and fail.
- Do not edit any local file except `spec_sync_report.md`.
- Do not modify CSV/XLSX structures.
- Never include secrets/tokens in any output.
- Keep all text UTF-8.

Notion update requirements (idempotent):
- For each mapped Notion page, upsert a block anchored by:
  - `[[AUTO_SYNC:SPEC_SYNC_META]]`
  - `[[AUTO_SYNC:SOURCE_FILE:<repo-path>]]`
- Upsert metadata fields (replace-in-place if marker exists):
  - Last synced at (KST)
  - Source file
  - Version / Commit
  - Change summary (3~10 lines)
  - Sync key (`{args.sync_key}`)
- Never duplicate pages/sections when rerun with same source content.

`spec_sync_report.md` update requirements:
- Append (or update) a section anchored by:
  - `[[AUTO_SYNC:SPEC_SYNC_REPORT:{args.sync_key}]]`
- Include:
  - synced time (KST)
  - source commit
  - changed files list
  - mapped Notion URLs
  - execution result summary
- If the same marker already exists, keep file unchanged (idempotent).

Output expectations:
- Perform the Notion sync actions first.
- Then edit `spec_sync_report.md` accordingly.
- Final response should summarize what was synced and whether it was idempotent.
"""

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(prompt, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
