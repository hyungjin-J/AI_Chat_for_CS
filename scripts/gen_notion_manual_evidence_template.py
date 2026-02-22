#!/usr/bin/env python3
"""Generate fixed-name Notion manual exception evidence templates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_STATUS_PATH = Path("docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json")
DEFAULT_PATCH_PATH = Path("docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md")
DEFAULT_PREFLIGHT_REF = "tmp/ci_notion_auth_preflight.json"
DEFAULT_REASON = "NOTION_AUTH_PRECHECK_FAILED"

DEFAULT_TARGETS = [
    "https://www.notion.so/<TARGET_PAGE_ID_1>",
    "https://www.notion.so/<TARGET_PAGE_ID_2>",
]


def now_kst() -> str:
    kst = timezone(timedelta(hours=9))
    return datetime.now(tz=kst).strftime("%Y-%m-%d %H:%M:%S +09:00")


def refuse_overwrite(path: Path, force: bool, label: str) -> None:
    if path.exists() and not force:
        raise FileExistsError(
            f"{label} already exists: {path.as_posix()} "
            "(rerun with --force to overwrite)"
        )


def render_manual_patch_template(timestamp_kst: str, targets: list[str]) -> str:
    targets_block = "\n".join(f"{index + 1}. {target}" for index, target in enumerate(targets))
    return f"""# Notion Manual Sync Patch Template

- Last synced at: {timestamp_kst}
- Source file: <SPEC_FILE_PATHS>
- Version: <COMMIT_OR_TAG>
- Change summary:
  1. <SUMMARY_LINE_1>
  2. <SUMMARY_LINE_2>
  3. <SUMMARY_LINE_3>
- Owner: <OWNER>
- Recorded at: {timestamp_kst}

## Notion targets
{targets_block}

## Execution checklist
- [ ] Manual patch applied to all Notion targets
- [ ] Page metadata updated (Last synced at / Source file / Version / Change summary)
- [ ] `spec_sync_report.md` updated with BLOCKED reason, evidence paths, and close result
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Notion manual exception evidence templates")
    parser.add_argument("--status-json", default=str(DEFAULT_STATUS_PATH))
    parser.add_argument("--manual-patch", default=str(DEFAULT_PATCH_PATH))
    parser.add_argument("--reason", default=DEFAULT_REASON)
    parser.add_argument("--preflight-ref", default=DEFAULT_PREFLIGHT_REF)
    parser.add_argument("--target", action="append", dest="targets")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    status_path = Path(args.status_json)
    patch_path = Path(args.manual_patch)
    targets = args.targets if args.targets else list(DEFAULT_TARGETS)
    timestamp_kst = now_kst()

    try:
        refuse_overwrite(status_path, args.force, "status evidence")
        refuse_overwrite(patch_path, args.force, "manual patch evidence")
    except FileExistsError as exc:
        print(f"[WARN] {exc}")
        return 1

    status_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.parent.mkdir(parents=True, exist_ok=True)

    status_payload = {
        "status": "BLOCKED_AUTOMATION",
        "reason": args.reason,
        "detected_at_kst": timestamp_kst,
        "preflight_ref": args.preflight_ref,
        "manual_patch": patch_path.as_posix(),
        "targets": targets,
    }
    status_path.write_text(
        json.dumps(status_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    patch_path.write_text(
        render_manual_patch_template(timestamp_kst=timestamp_kst, targets=targets),
        encoding="utf-8",
    )

    print("Generated Notion manual exception evidence templates:")
    print(f"- {status_path.as_posix()}")
    print(f"- {patch_path.as_posix()}")
    print("")
    print("Next actions:")
    print("1) Replace template placeholders and apply manual patch in Notion.")
    print("2) Update page metadata fields (Last synced at / Source file / Version / Change summary).")
    print("3) Record BLOCKED reason and close evidence in spec_sync_report.md.")
    print("4) Run scripts/check_notion_manual_exception_gate.py to validate close readiness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
