from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "gen_notion_manual_evidence_templates.py"


class NotionTemplateGeneratorTest(unittest.TestCase):
    def test_refuses_overwrite_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "notion_blocked_status.json"
            patch_path = root / "notion_manual_patch.md"
            status_path.write_text('{"status":"BLOCKED_AUTOMATION"}\n', encoding="utf-8")
            patch_path.write_text("# existing\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--status-path",
                    str(status_path),
                    "--patch-path",
                    str(patch_path),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("already exists", proc.stdout + proc.stderr)

    def test_generates_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "notion_blocked_status.json"
            patch_path = root / "notion_manual_patch.md"

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--status-path",
                    str(status_path),
                    "--patch-path",
                    str(patch_path),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertTrue(status_path.exists())
            self.assertTrue(patch_path.exists())

            status_text = status_path.read_text(encoding="utf-8")
            patch_text = patch_path.read_text(encoding="utf-8")
            self.assertIn('"status": "BLOCKED_AUTOMATION"', status_text)
            self.assertIn("detected_at_kst", status_text)
            self.assertIn("preflight_ref", status_text)

            self.assertIn("- Last synced at:", patch_text)
            self.assertIn("- Source file:", patch_text)
            self.assertIn("- Version:", patch_text)
            self.assertIn("- Change summary:", patch_text)
            self.assertIn("## Notion targets", patch_text)


if __name__ == "__main__":
    unittest.main()
