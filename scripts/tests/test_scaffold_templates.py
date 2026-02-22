from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SCRIPT = REPO_ROOT / "scripts" / "scaffold_backend_context.py"
FRONTEND_SCRIPT = REPO_ROOT / "scripts" / "scaffold_frontend_feature.py"


class BackendScaffoldTemplateTest(unittest.TestCase):
    def test_backend_scaffold_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            java_root = root / "backend/src/main/java/com/aichatbot/contexts"
            mapper_root = root / "backend/src/main/resources/mappers"
            test_root = root / "backend/src/test/java/com/aichatbot/contexts"

            proc = subprocess.run(
                [
                    "python",
                    str(BACKEND_SCRIPT),
                    "--context",
                    "identity",
                    "--java-root",
                    str(java_root),
                    "--mapper-root",
                    str(mapper_root),
                    "--test-root",
                    str(test_root),
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
            self.assertTrue(
                (java_root / "identity/domain/mapper/IdentityMapper.java").exists()
            )
            self.assertTrue(
                (mapper_root / "identity/IdentityMapper.xml").exists()
            )

            second = subprocess.run(
                [
                    "python",
                    str(BACKEND_SCRIPT),
                    "--context",
                    "identity",
                    "--java-root",
                    str(java_root),
                    "--mapper-root",
                    str(mapper_root),
                    "--test-root",
                    str(test_root),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("status=FAIL", second.stdout)


class FrontendScaffoldTemplateTest(unittest.TestCase):
    def test_frontend_scaffold_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feature_root = root / "frontend/src/features"

            proc = subprocess.run(
                [
                    "python",
                    str(FRONTEND_SCRIPT),
                    "--context",
                    "conversation",
                    "--feature",
                    "chat_panel",
                    "--root",
                    str(feature_root),
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
            self.assertTrue(
                (
                    feature_root
                    / "conversation/chat_panel/ui/ChatPanel.tsx"
                ).exists()
            )
            self.assertTrue(
                (
                    feature_root
                    / "conversation/chat_panel/hooks/useChatPanel.ts"
                ).exists()
            )
            self.assertTrue(
                (
                    feature_root
                    / "conversation/chat_panel/api/chatPanelApi.ts"
                ).exists()
            )

            second = subprocess.run(
                [
                    "python",
                    str(FRONTEND_SCRIPT),
                    "--context",
                    "conversation",
                    "--feature",
                    "chat_panel",
                    "--root",
                    str(feature_root),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("status=FAIL", second.stdout)


if __name__ == "__main__":
    unittest.main()
