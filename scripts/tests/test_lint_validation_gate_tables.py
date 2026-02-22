from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "lint_validation_gate_tables.py"


class LintValidationGateTablesTest(unittest.TestCase):
    def prepare_workspace(self) -> Path:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        (root / "docs/reports").mkdir(parents=True, exist_ok=True)
        (root / "docs/review/mvp_verification_pack/artifacts").mkdir(parents=True, exist_ok=True)
        (root / "spec_sync_report.md").write_text("sync record\n", encoding="utf-8")
        return root

    def run_lint(self, root: Path, target_file: str) -> tuple[int, dict]:
        output_json = root / "lint_validation_gate_tables.json"
        output_txt = root / "lint_validation_gate_tables.txt"
        proc = subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--root",
                ".",
                "--files",
                target_file,
                "--output-json",
                str(output_json),
                "--output-txt",
                str(output_txt),
            ],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        return proc.returncode, payload

    def test_missing_local_evidence_fails(self) -> None:
        root = self.prepare_workspace()
        target = root / "docs/reports/report_missing.md"
        target.write_text(
            "\n".join(
                [
                    "# Report",
                    "## Validation Gate",
                    "| Gate | Status | Evidence |",
                    "|---|---|---|",
                    "| docs lint | FAIL | docs/review/mvp_verification_pack/artifacts/missing.txt |",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        code, payload = self.run_lint(root, "docs/reports/report_missing.md")
        self.assertNotEqual(code, 0)
        self.assertEqual(payload["status"], "FAIL")
        self.assertGreater(payload["missing_local_evidence_count"], 0)
        self.assertIn(
            "docs/review/mvp_verification_pack/artifacts/missing.txt",
            payload["missing_local_paths"],
        )

    def test_existing_local_evidence_passes(self) -> None:
        root = self.prepare_workspace()
        artifact_path = "docs/review/mvp_verification_pack/artifacts/existing.txt"
        (root / artifact_path).write_text("ok\n", encoding="utf-8")
        target = root / "docs/reports/report_ok.md"
        target.write_text(
            "\n".join(
                [
                    "# Report",
                    "## Validation Gate",
                    "| Gate | Status | Evidence |",
                    "|---|---|---|",
                    f"| docs lint | PASS | {artifact_path} |",
                    "| spec sync | PASS | spec_sync_report.md |",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        code, payload = self.run_lint(root, "docs/reports/report_ok.md")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["missing_local_evidence_count"], 0)
        self.assertEqual(payload["warning_count"], 0)

    def test_external_link_is_warning_only(self) -> None:
        root = self.prepare_workspace()
        artifact_path = "docs/review/mvp_verification_pack/artifacts/existing2.txt"
        (root / artifact_path).write_text("ok\n", encoding="utf-8")
        target = root / "docs/reports/report_warn.md"
        target.write_text(
            "\n".join(
                [
                    "# Report",
                    "## Validation Gate",
                    "| Gate | Status | Evidence |",
                    "|---|---|---|",
                    "| external | PASS | https://example.com/evidence |",
                    f"| local | PASS | `{artifact_path}` |",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        code, payload = self.run_lint(root, "docs/reports/report_warn.md")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertGreater(payload["warning_count"], 0)
        self.assertEqual(payload["missing_local_evidence_count"], 0)


if __name__ == "__main__":
    unittest.main()
