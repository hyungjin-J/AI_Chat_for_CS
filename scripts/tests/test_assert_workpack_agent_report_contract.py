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
        "high_risk_patterns": [
            "backend/**",
            "frontend/**",
            "scripts/**",
            "docs/references/**",
            "docs/uiux/**",
            "AGENTS.md",
        ],
        "topic_pattern": r"^20\d{6}_[a-z0-9]+(?:__[a-z0-9]+)*$",
        "forbidden_topic_tokens": ["misc", "etc", "tmp", "temp", "update", "fix"],
        "scope_stop_tokens": [
            "src",
            "main",
            "test",
            "java",
            "com",
            "aichatbot",
            "contexts",
            "channels",
            "backend",
            "frontend",
            "scripts",
            "docs",
            "review",
            "workpacks",
            "agent",
            "reports",
            "presentation",
            "application",
            "domain",
            "infrastructure",
            "github",
            "workflows",
            "chatgpt",
        ],
        "security_scope_patterns": [
            "backend/**/security/**",
            "backend/**/rbac/**",
            "backend/**/auth/**",
            "scripts/**security**",
        ],
        "workpack_root": "docs/workpacks",
        "required_workpack_files": ["01_plan.md", "02_context.md", "03_checklist.md"],
        "manual_hook_reference_tokens": [
            "orchestrator_control_manual_hook_output.json",
            "manual_hook_output.json",
        ],
        "agent_report_root": "docs/review/agent_reports",
        "required_agent_reports": ["DDD_report.md", "SEC_report.md", "QA_report.md"],
        "required_reports_by_scope": {
            "backend": ["DDD_report.md", "QA_report.md"],
            "frontend": ["QA_report.md"],
            "security": ["SEC_report.md"],
        },
        "spec_sync": {
            "patterns": [
                "docs/references/*.csv",
                "docs/references/*.xlsx",
                "docs/uiux/*.xlsx",
            ],
            "required_report": "spec_sync_report.md",
            "manual_exception_gate": {
                "script": "scripts/check_notion_manual_exception_gate.py",
                "status_file": "docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json",
                "manual_patch": "docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md",
                "spec_sync_report": "spec_sync_report.md",
            },
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_workpack(root: Path, topic: str) -> None:
    workpack_dir = root / "docs/workpacks" / topic
    workpack_dir.mkdir(parents=True, exist_ok=True)
    (workpack_dir / "01_plan.md").write_text("# plan\n", encoding="utf-8")
    (workpack_dir / "02_context.md").write_text(
        "manual hook: docs/review/mvp_verification_pack/artifacts/orchestrator_control_manual_hook_output.json\n",
        encoding="utf-8",
    )
    (workpack_dir / "03_checklist.md").write_text("# checklist\n", encoding="utf-8")


def write_reports(root: Path, topic: str, files: list[str]) -> None:
    report_dir = root / "docs/review/agent_reports" / topic
    report_dir.mkdir(parents=True, exist_ok=True)
    for file_name in files:
        (report_dir / file_name).write_text(f"# {file_name}\n", encoding="utf-8")


def write_fake_notion_gate(root: Path) -> None:
    script_path = root / "scripts/check_notion_manual_exception_gate.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        """#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--status-file", required=True)
parser.add_argument("--manual-patch", required=True)
parser.add_argument("--spec-sync", required=True)
parser.add_argument("--output-json")
parser.add_argument("--output-txt")
args = parser.parse_args()

status_text = Path(args.status_file).read_text(encoding="utf-8", errors="strict")
manual_text = Path(args.manual_patch).read_text(encoding="utf-8", errors="strict")
spec_text = Path(args.spec_sync).read_text(encoding="utf-8", errors="strict")

ok = ("PASS_GATE" in status_text) and ("manual patch" in manual_text) and ("spec_sync" in spec_text)
payload = {"status": "PASS" if ok else "FAIL", "checked": True}
if args.output_json:
    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False) + "\\n", encoding="utf-8")
if args.output_txt:
    Path(args.output_txt).write_text(f"status={payload['status']}\\n", encoding="utf-8")
print(f"status={payload['status']}")
sys.exit(0 if ok else 1)
""",
        encoding="utf-8",
    )


def write_manual_exception_files(root: Path, pass_gate: bool) -> None:
    status_path = root / "docs/review/mvp_verification_pack/artifacts/notion_blocked_status.json"
    patch_path = root / "docs/review/mvp_verification_pack/artifacts/notion_manual_patch.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    token = "PASS_GATE" if pass_gate else "FAIL_GATE"
    status_path.write_text(f'{{"status":"{token}"}}\n', encoding="utf-8")
    patch_path.write_text("manual patch\n", encoding="utf-8")


class WorkpackAgentReportContractV2Test(unittest.TestCase):
    def run_script(self, root: Path, contract_path: Path, changed_files: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--root",
                str(root),
                "--contract",
                str(contract_path),
                "--changed-files",
                "\n".join(changed_files),
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_backend_only_change_passes_with_backend_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/workpack_agent_report_contract.json"
            write_contract(contract_path)
            topic = "20260222_billing"
            write_workpack(root, topic)
            write_reports(root, topic, ["DDD_report.md", "QA_report.md"])

            changed = [
                "backend/src/main/java/com/aichatbot/contexts/billing/application/UsageRollupService.java",
                f"docs/workpacks/{topic}/01_plan.md",
                f"docs/workpacks/{topic}/02_context.md",
                f"docs/workpacks/{topic}/03_checklist.md",
                f"docs/review/agent_reports/{topic}/DDD_report.md",
                f"docs/review/agent_reports/{topic}/QA_report.md",
            ]
            proc = self.run_script(root, contract_path, changed)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_frontend_only_change_passes_with_qa_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/workpack_agent_report_contract.json"
            write_contract(contract_path)
            topic = "20260222_dashboard"
            write_workpack(root, topic)
            write_reports(root, topic, ["QA_report.md"])

            changed = [
                "frontend/src/features/backoffice/dashboard/ui/AdminDashboardView.tsx",
                f"docs/workpacks/{topic}/01_plan.md",
                f"docs/workpacks/{topic}/02_context.md",
                f"docs/workpacks/{topic}/03_checklist.md",
                f"docs/review/agent_reports/{topic}/QA_report.md",
            ]
            proc = self.run_script(root, contract_path, changed)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_security_change_passes_with_sec_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/workpack_agent_report_contract.json"
            write_contract(contract_path)
            topic = "20260222_security"
            write_workpack(root, topic)
            write_reports(root, topic, ["SEC_report.md"])

            changed = [
                "scripts/security_guard_rollup.py",
                f"docs/workpacks/{topic}/01_plan.md",
                f"docs/workpacks/{topic}/02_context.md",
                f"docs/workpacks/{topic}/03_checklist.md",
                f"docs/review/agent_reports/{topic}/SEC_report.md",
            ]
            proc = self.run_script(root, contract_path, changed)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("scope_security=True", proc.stdout)

    def test_spec_only_change_requires_spec_sync_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/workpack_agent_report_contract.json"
            write_contract(contract_path)
            topic = "20260222_requirements"
            write_workpack(root, topic)
            write_reports(root, topic, ["DDD_report.md", "SEC_report.md", "QA_report.md"])

            changed = [
                "docs/references/Summary of key features.csv",
                f"docs/workpacks/{topic}/01_plan.md",
                f"docs/workpacks/{topic}/02_context.md",
                f"docs/workpacks/{topic}/03_checklist.md",
                f"docs/review/agent_reports/{topic}/DDD_report.md",
                f"docs/review/agent_reports/{topic}/SEC_report.md",
                f"docs/review/agent_reports/{topic}/QA_report.md",
            ]
            proc = self.run_script(root, contract_path, changed)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_REPORT_NOT_UPDATED", proc.stdout)

    def test_mixed_change_requires_scope_bound_topic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/workpack_agent_report_contract.json"
            write_contract(contract_path)
            bad_topic = "20260222_unrelated"
            write_workpack(root, bad_topic)
            write_reports(root, bad_topic, ["DDD_report.md", "QA_report.md"])

            changed = [
                "backend/src/main/java/com/aichatbot/contexts/billing/application/UsageRollupService.java",
                "frontend/src/features/backoffice/dashboard/ui/AdminDashboardView.tsx",
                f"docs/workpacks/{bad_topic}/01_plan.md",
                f"docs/workpacks/{bad_topic}/02_context.md",
                f"docs/workpacks/{bad_topic}/03_checklist.md",
                f"docs/review/agent_reports/{bad_topic}/DDD_report.md",
                f"docs/review/agent_reports/{bad_topic}/QA_report.md",
            ]
            proc = self.run_script(root, contract_path, changed)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("TOPIC_SCOPE_BINDING_MISSING", proc.stdout)

    def test_spec_only_change_fails_when_manual_exception_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/workpack_agent_report_contract.json"
            write_contract(contract_path)
            write_fake_notion_gate(root)
            write_manual_exception_files(root, pass_gate=False)
            (root / "spec_sync_report.md").write_text("spec_sync\n", encoding="utf-8")
            topic = "20260222_spec__sync"
            write_workpack(root, topic)
            write_reports(root, topic, ["DDD_report.md", "SEC_report.md", "QA_report.md"])

            changed = [
                "docs/references/Summary of key features.csv",
                "spec_sync_report.md",
                f"docs/workpacks/{topic}/01_plan.md",
                f"docs/workpacks/{topic}/02_context.md",
                f"docs/workpacks/{topic}/03_checklist.md",
                f"docs/review/agent_reports/{topic}/DDD_report.md",
                f"docs/review/agent_reports/{topic}/SEC_report.md",
                f"docs/review/agent_reports/{topic}/QA_report.md",
            ]
            proc = self.run_script(root, contract_path, changed)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("NOTION_MANUAL_EXCEPTION_GATE_FAILED", proc.stdout)

    def test_spec_only_change_passes_when_manual_exception_gate_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/workpack_agent_report_contract.json"
            write_contract(contract_path)
            write_fake_notion_gate(root)
            write_manual_exception_files(root, pass_gate=True)
            (root / "spec_sync_report.md").write_text("spec_sync\n", encoding="utf-8")
            topic = "20260222_spec__sync"
            write_workpack(root, topic)
            write_reports(root, topic, ["DDD_report.md", "SEC_report.md", "QA_report.md"])

            changed = [
                "docs/references/Summary of key features.csv",
                "spec_sync_report.md",
                f"docs/workpacks/{topic}/01_plan.md",
                f"docs/workpacks/{topic}/02_context.md",
                f"docs/workpacks/{topic}/03_checklist.md",
                f"docs/review/agent_reports/{topic}/DDD_report.md",
                f"docs/review/agent_reports/{topic}/SEC_report.md",
                f"docs/review/agent_reports/{topic}/QA_report.md",
            ]
            proc = self.run_script(root, contract_path, changed)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("notion_manual_exception_gate_ran=True", proc.stdout)
            self.assertIn("status=PASS", proc.stdout)


if __name__ == "__main__":
    unittest.main()
