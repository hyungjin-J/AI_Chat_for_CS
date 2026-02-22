from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_scaffold_contract_smoke.py"
DEFAULT_CONTRACT = REPO_ROOT / "scripts/contracts/domain_template_contract.json"


class ScaffoldContractSmokeTest(unittest.TestCase):
    def run_script(self, contract_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--root",
                str(REPO_ROOT),
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

    def test_pass_with_default_contract(self) -> None:
        proc = self.run_script(DEFAULT_CONTRACT)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("status=PASS", proc.stdout)

    def test_fail_when_contract_requires_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contract = json.loads(DEFAULT_CONTRACT.read_text(encoding="utf-8"))
            contract["backend_context_template"]["required_files"].append(
                "application/usecase/{Context}MissingUseCase.java"
            )
            temp_contract = Path(tmp) / "contract.json"
            temp_contract.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            proc = self.run_script(temp_contract)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("MissingUseCase", proc.stdout)


if __name__ == "__main__":
    unittest.main()
