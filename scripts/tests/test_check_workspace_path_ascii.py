from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_workspace_path_ascii.py"


class CheckWorkspacePathAsciiTest(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python", str(SCRIPT_PATH), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_pass_for_ascii_path(self) -> None:
        proc = self.run_script("--path", "C:/temp/ascii_workspace")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("status=PASS", proc.stdout)

    def test_warning_for_non_ascii_path(self) -> None:
        proc = self.run_script("--path", "C:/temp/\ud55c\uae00_workspace")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("status=WARNING", proc.stdout)
        self.assertIn("non_ascii_count=", proc.stdout)

    def test_strict_mode_returns_nonzero_for_non_ascii_path(self) -> None:
        proc = self.run_script("--path", "C:/temp/\ud55c\uae00_workspace", "--strict")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("status=WARNING", proc.stdout)


if __name__ == "__main__":
    unittest.main()
