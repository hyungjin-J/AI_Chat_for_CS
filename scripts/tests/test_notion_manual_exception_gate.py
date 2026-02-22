from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_notion_manual_exception_gate.py"


class NotionManualExceptionGateTest(unittest.TestCase):
    def test_missing_artifact_file_fails_with_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "notion_blocked_status.json"
            spec_sync = root / "spec_sync_report.md"

            status_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "status": "BLOCKED_AUTOMATION",
                      "reason": "NOTION_AUTH_PRECHECK_FAILED",
                      "detected_at_kst": "2026-02-22 00:00:00 +09:00",
                      "preflight_ref": "tmp/preflight.json"
                    }
                    """
                ),
                encoding="utf-8",
            )
            spec_sync.write_text("BLOCKED_AUTOMATION\n", encoding="utf-8")

            missing_patch = root / "notion_manual_patch.md"
            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--status-json",
                    str(status_path),
                    "--manual-patch",
                    str(missing_patch),
                    "--spec-sync",
                    str(spec_sync),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("notion_manual_patch.md", proc.stdout)
            self.assertIn("not found", proc.stdout)

    def test_empty_required_field_reports_file_and_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "notion_blocked_status.json"
            patch_path = root / "notion_manual_patch.md"
            spec_sync = root / "spec_sync_report.md"
            preflight_ref = root / "preflight.json"
            preflight_ref.write_text("{}", encoding="utf-8")

            status_path.write_text(
                textwrap.dedent(
                    f"""\
                    {{
                      "status": "BLOCKED_AUTOMATION",
                      "reason": "",
                      "detected_at_kst": "2026-02-22 00:00:00 +09:00",
                      "preflight_ref": "{preflight_ref.as_posix()}"
                    }}
                    """
                ),
                encoding="utf-8",
            )
            patch_path.write_text(
                textwrap.dedent(
                    """\
                    - Last synced at: 2026-02-22 00:00:00 +09:00
                    - Source file: docs/references/Development environment.csv
                    - Version: abc1234
                    - Change summary:
                      1. sample
                    https://www.notion.so/sample
                    """
                ),
                encoding="utf-8",
            )
            spec_sync.write_text(
                textwrap.dedent(
                    """\
                    notion_blocked_status.json
                    notion_manual_patch.md
                    BLOCKED_AUTOMATION
                    Phase2.1
                    """
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--status-json",
                    str(status_path),
                    "--manual-patch",
                    str(patch_path),
                    "--spec-sync",
                    str(spec_sync),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("notion_blocked_status.json", proc.stdout)
            self.assertIn("field 'reason' is empty", proc.stdout)


if __name__ == "__main__":
    unittest.main()
