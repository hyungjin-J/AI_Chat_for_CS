from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_fixed_artifact_paths.py"


class FixedArtifactContractTest(unittest.TestCase):
    def test_missing_contract_path_fails_with_missing_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "docs/review/mvp_verification_pack/artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)

            existing = artifacts / "exists.txt"
            existing.write_text("ok\n", encoding="utf-8")
            missing_rel = "docs/review/mvp_verification_pack/artifacts/missing.txt"

            contract = {
                "artifact_root": "docs/review/mvp_verification_pack/artifacts/",
                "allowed_non_artifact_paths": ["spec_sync_report.md"],
                "fixed_paths": [
                    "docs/review/mvp_verification_pack/artifacts/exists.txt",
                    missing_rel,
                    "spec_sync_report.md",
                ],
            }
            (root / "spec_sync_report.md").write_text("sync\n", encoding="utf-8")
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--contract",
                    str(contract_path),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("PATH_MISSING", proc.stdout)
            self.assertIn(missing_rel, proc.stdout)

    def test_contract_passes_when_all_paths_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "docs/review/mvp_verification_pack/artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "exists.txt").write_text("ok\n", encoding="utf-8")
            (root / "spec_sync_report.md").write_text("sync\n", encoding="utf-8")

            contract = {
                "artifact_root": "docs/review/mvp_verification_pack/artifacts/",
                "allowed_non_artifact_paths": ["spec_sync_report.md"],
                "fixed_paths": [
                    "docs/review/mvp_verification_pack/artifacts/exists.txt",
                    "spec_sync_report.md",
                ],
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--contract",
                    str(contract_path),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_contract_safety_rejects_path_traversal_absolute_and_backslash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "docs/review/mvp_verification_pack/artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "ok.txt").write_text("ok\n", encoding="utf-8")
            (root / "spec_sync_report.md").write_text("sync\n", encoding="utf-8")

            contract = {
                "artifact_root": "docs/review/mvp_verification_pack/artifacts/",
                "allowed_non_artifact_paths": ["spec_sync_report.md"],
                "fixed_paths": [
                    "docs/review/mvp_verification_pack/artifacts/ok.txt",
                    "../secrets.txt",
                    "/etc/passwd",
                    "C:\\temp\\x",
                    "docs/../x",
                    "spec_sync_report.md",
                ],
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--contract",
                    str(contract_path),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("PATH_TRAVERSAL_FORBIDDEN", proc.stdout)
            self.assertIn("PATH_ABSOLUTE_FORBIDDEN", proc.stdout)
            self.assertIn("PATH_BACKSLASH_FORBIDDEN", proc.stdout)
            self.assertIn("../secrets.txt", proc.stdout)
            self.assertIn("/etc/passwd", proc.stdout)
            self.assertIn("C:\\temp\\x", proc.stdout)
            self.assertIn("docs/../x", proc.stdout)


if __name__ == "__main__":
    unittest.main()
