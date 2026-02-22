from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_platform_boundary.py"


class AssertPlatformBoundaryTest(unittest.TestCase):
    def test_forbidden_import_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "java"
            target = root / "com/aichatbot/platform/security/SecurityRule.java"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                (
                    "package com.aichatbot.platform.security;\n\n"
                    "import com.aichatbot.contexts.identity.application.LoginUseCase;\n\n"
                    "public final class SecurityRule {\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("PLATFORM_BOUNDARY_FORBIDDEN_IMPORT", proc.stdout)
            self.assertIn("com.aichatbot.contexts.identity.application.LoginUseCase", proc.stdout)

    def test_allowed_import_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "java"
            target = root / "com/aichatbot/platform/security/SecurityRule.java"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                (
                    "package com.aichatbot.platform.security;\n\n"
                    "import java.util.UUID;\n\n"
                    "public final class SecurityRule {\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_empty_scan_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "java"
            root.mkdir(parents=True, exist_ok=True)

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("scanned_files_count=0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
