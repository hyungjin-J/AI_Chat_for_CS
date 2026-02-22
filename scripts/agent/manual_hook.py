#!/usr/bin/env python3
"""Pre-code control manual hook (fail-closed)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_CHAPTERS = (
    "01_preflight_and_baseline.md",
    "02_working_memory_contract.md",
    "03_pr_decomposition_and_agent_roles.md",
    "04_gates_notion_and_evidence.md",
)


@dataclass
class ChapterSummary:
    chapter: str
    summary: list[str]


def parse_changed_files(raw: str) -> list[str]:
    # Accept comma or newline separated values.
    chunks = re.split(r"[\r\n,]+", raw)
    normalized: list[str] = []
    for chunk in chunks:
        cleaned = chunk.lstrip("\ufeff").strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def summarize_chapter(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig", errors="strict")
    lines = [line.strip() for line in text.splitlines()]
    summary: list[str] = []
    for line in lines:
        if not line:
            continue
        if line.startswith("#"):
            continue
        summary.append(line)
        if len(summary) == 3:
            break
    if not summary:
        summary.append("No actionable summary line found; review the chapter body.")
    return summary


def build_next_actions(status: str, missing: list[str], selected: list[str]) -> list[str]:
    if status == "FAIL":
        actions = [
            "Fail-closed: create missing manual chapters before coding.",
            "Re-run manual_hook.py with the same --task and --changed-files inputs.",
        ]
        for chapter in missing:
            actions.append(f"Create: docs/agent_manual/{chapter}")
        return actions

    actions = [
        "Open and read all returned manual chapters before implementation.",
        "Create/update workpack files before touching runtime code:",
        "docs/workpacks/YYYYMMDD_<topic>/01_plan.md",
        "docs/workpacks/YYYYMMDD_<topic>/02_context.md",
        "docs/workpacks/YYYYMMDD_<topic>/03_checklist.md",
        "Declare 'no code changes before approval' in workpack plan/checklist.",
    ]
    for chapter in selected:
        actions.append(f"Load chapter: docs/agent_manual/{chapter}")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual hook for orchestrator pre-code control")
    parser.add_argument("--task", required=True, help="User request / task statement")
    parser.add_argument(
        "--changed-files",
        help="Changed files list (comma or newline separated)",
    )
    parser.add_argument(
        "--changed-files-file",
        help="Optional file path containing changed files (one per line)",
    )
    parser.add_argument(
        "--manual-root",
        default="docs/agent_manual",
        help="Manual chapters root directory",
    )
    parser.add_argument("--output-json", help="Optional path to write JSON output")
    args = parser.parse_args()

    manual_root = Path(args.manual_root)
    changed_raw = args.changed_files or ""
    if args.changed_files_file:
        changed_file = Path(args.changed_files_file)
        if not changed_file.exists():
            blockers = [f"changed-files-file not found: {changed_file.as_posix()}"]
            payload = {
                "status": "FAIL",
                "task": args.task,
                "manual_chapters": [],
                "chapter_summaries": [],
                "blockers": blockers,
                "next_actions": [
                    "Fail-closed: provide a valid changed files input.",
                    "Use --changed-files or --changed-files-file.",
                ],
                "changed_files_count": 0,
                "changed_files_sample": [],
            }
            output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            if args.output_json:
                output_path = Path(args.output_json)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(output, encoding="utf-8")
            sys.stdout.write(output)
            return 1
        changed_raw = changed_file.read_text(encoding="utf-8-sig", errors="strict")

    changed_files = parse_changed_files(changed_raw)
    blockers: list[str] = []

    if not changed_files:
        blockers.append("changed-files is empty after parsing")

    selected_chapters = list(REQUIRED_CHAPTERS)
    missing_chapters = [name for name in REQUIRED_CHAPTERS if not (manual_root / name).exists()]
    for chapter in missing_chapters:
        blockers.append(f"missing manual chapter: {manual_root.as_posix()}/{chapter}")

    chapter_summaries: list[ChapterSummary] = []
    if not missing_chapters:
        for chapter in selected_chapters:
            chapter_path = manual_root / chapter
            chapter_summaries.append(
                ChapterSummary(chapter=chapter, summary=summarize_chapter(chapter_path))
            )

    status = "PASS" if not blockers else "FAIL"
    payload = {
        "status": status,
        "task": args.task,
        "manual_chapters": [f"{manual_root.as_posix()}/{name}" for name in selected_chapters],
        "chapter_summaries": [
            {"chapter": item.chapter, "summary": item.summary} for item in chapter_summaries
        ],
        "blockers": blockers,
        "next_actions": build_next_actions(
            status=status,
            missing=missing_chapters,
            selected=selected_chapters,
        ),
        "changed_files_count": len(changed_files),
        "changed_files_sample": changed_files[:20],
    }

    output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")

    sys.stdout.write(output)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
