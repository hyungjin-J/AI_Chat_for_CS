from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "agent" / "manual_hook.py"


class ManualHookTest(unittest.TestCase):
    def test_fail_closed_when_manual_chapter_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manual_root = Path(tmp) / "docs" / "agent_manual"
            manual_root.mkdir(parents=True, exist_ok=True)
            # Intentionally create only one file.
            (manual_root / "01_preflight_and_baseline.md").write_text(
                "# Chapter 01\nMust read first.\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--task",
                    "test fail closed",
                    "--changed-files",
                    "AGENTS.md,scripts/agent/manual_hook.py",
                    "--manual-root",
                    str(manual_root),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "FAIL")
            self.assertGreaterEqual(len(payload["blockers"]), 1)

    def test_pass_with_required_chapters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manual_root = Path(tmp) / "docs" / "agent_manual"
            manual_root.mkdir(parents=True, exist_ok=True)
            chapters = (
                "01_preflight_and_baseline.md",
                "02_working_memory_contract.md",
                "03_pr_decomposition_and_agent_roles.md",
                "04_gates_notion_and_evidence.md",
            )
            for chapter in chapters:
                (manual_root / chapter).write_text(
                    f"# {chapter}\nline one\nline two\nline three\n",
                    encoding="utf-8",
                )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--task",
                    "test pass",
                    "--changed-files",
                    "AGENTS.md\nscripts/agent/manual_hook.py",
                    "--manual-root",
                    str(manual_root),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(len(payload["manual_chapters"]), 4)
            self.assertEqual(len(payload["chapter_summaries"]), 4)
            self.assertGreaterEqual(payload["changed_files_count"], 2)


if __name__ == "__main__":
    unittest.main()
