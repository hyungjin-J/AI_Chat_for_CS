from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_workpack_agent_report_contract.py"


def write_contract(path: Path) -> None:
    contract = {
        "high_risk_patterns": ["backend/**", "scripts/**", "AGENTS.md"],
        "workpack_root": "docs/workpacks",
        "required_workpack_files": ["01_plan.md", "02_context.md", "03_checklist.md"],
        "manual_hook_reference_tokens": ["orchestrator_control_manual_hook_output.json", "manual_hook_output.json"],
        "agent_report_root": "docs/review/agent_reports",
        "required_agent_reports": ["DDD_report.md", "SEC_report.md", "QA_report.md"],
    }
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class WorkpackAgentReportContractTest(unittest.TestCase):
    def test_not_required_when_no_high_risk_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "contract.json"
            write_contract(contract_path)

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--contract",
                    str(contract_path),
                    "--changed-files",
                    "README.md",
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("high_risk_triggered=False", proc.stdout)
            self.assertIn("status=PASS", proc.stdout)

    def test_fails_when_agent_report_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "contract.json"
            write_contract(contract_path)

            workpack_dir = root / "docs/workpacks/20260222_topic_a"
            workpack_dir.mkdir(parents=True, exist_ok=True)
            (workpack_dir / "01_plan.md").write_text("# plan\n", encoding="utf-8")
            (workpack_dir / "02_context.md").write_text(
                "manual hook: docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json\n",
                encoding="utf-8",
            )
            (workpack_dir / "03_checklist.md").write_text("# checklist\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--contract",
                    str(contract_path),
                    "--changed-files",
                    "backend/src/main/java/com/aichatbot/Foo.java",
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("AGENT_REPORT_ROOT_MISSING", proc.stdout)

    def test_passes_when_workpack_and_reports_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "contract.json"
            write_contract(contract_path)

            topic = "20260222_topic_ok"
            workpack_dir = root / "docs/workpacks" / topic
            workpack_dir.mkdir(parents=True, exist_ok=True)
            (workpack_dir / "01_plan.md").write_text("# plan\n", encoding="utf-8")
            (workpack_dir / "02_context.md").write_text(
                "hook path: docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json\n",
                encoding="utf-8",
            )
            (workpack_dir / "03_checklist.md").write_text("# checklist\n", encoding="utf-8")

            report_dir = root / "docs/review/agent_reports" / topic
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "DDD_report.md").write_text("# ddd\n", encoding="utf-8")
            (report_dir / "SEC_report.md").write_text("# sec\n", encoding="utf-8")
            (report_dir / "QA_report.md").write_text("# qa\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--contract",
                    str(contract_path),
                    "--changed-files",
                    "scripts/assert_workpack_agent_report_contract.py",
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
            self.assertIn("high_risk_triggered=True", proc.stdout)


if __name__ == "__main__":
    unittest.main()
