from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "block_legacy_packages.py"


def write_contract(path: Path) -> None:
    contract = {
        "java_roots": ["backend/src/main/java", "backend/src/test/java"],
        "legacy_packages": ["auth", "billing", "message", "rag", "session", "admin", "ops", "answer", "llm", "tool", "global"],
    }
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class BlockLegacyPackagesTest(unittest.TestCase):
    def test_pass_when_no_legacy_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "contract.json"
            write_contract(contract_path)
            target = root / "backend/src/main/java/com/aichatbot/contexts/identity/presentation/AuthController.java"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "package com.aichatbot.contexts.identity.presentation;\n\n"
                "import java.util.UUID;\n"
                "public class AuthController {}\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--contract",
                    str(contract_path),
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

    def test_fail_when_legacy_path_or_import_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "contract.json"
            write_contract(contract_path)

            legacy_file = root / "backend/src/main/java/com/aichatbot/auth/presentation/AuthController.java"
            legacy_file.parent.mkdir(parents=True, exist_ok=True)
            legacy_file.write_text(
                "package com.aichatbot.auth.presentation;\n\n"
                "public class AuthController {}\n",
                encoding="utf-8",
            )

            modern_file = root / "backend/src/main/java/com/aichatbot/contexts/identity/presentation/AnotherController.java"
            modern_file.parent.mkdir(parents=True, exist_ok=True)
            modern_file.write_text(
                "package com.aichatbot.contexts.identity.presentation;\n\n"
                "import com.aichatbot.auth.application.AuthService;\n"
                "public class AnotherController {}\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--contract",
                    str(contract_path),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("LEGACY_PACKAGE_PATH_DETECTED", proc.stdout)
            self.assertIn("LEGACY_PACKAGE_IMPORT_DETECTED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
