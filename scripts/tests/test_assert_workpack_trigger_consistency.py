from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_workpack_trigger_consistency.py"


def write_contract(path: Path, patterns: list[str]) -> None:
    payload = {
        "high_risk_patterns": patterns,
        "workpack_root": "docs/workpacks",
        "required_workpack_files": ["01_plan.md", "02_context.md", "03_checklist.md"],
        "manual_hook_reference_tokens": ["manual_hook_output.json"],
        "agent_report_root": "docs/review/agent_reports",
        "required_agent_reports": ["DDD_report.md", "SEC_report.md", "QA_report.md"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_agents(path: Path, patterns: list[str]) -> None:
    lines = [
        "# AGENTS",
        "#### 12.3-A Working Memory 3문서 트리거(변경 파일 패턴 기반, 강제)",
        "다음 패턴 중 하나라도 변경되면 workpack 3문서를 반드시 생성/갱신한다.",
    ]
    lines.extend([f"- `{item}`" for item in patterns])
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manual(path: Path, patterns: list[str]) -> None:
    lines = [
        "# Agent Manual",
        "## Trigger Patterns (Fail-Closed)",
    ]
    lines.extend([f"- `{item}`" for item in patterns])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class WorkpackTriggerConsistencyTest(unittest.TestCase):
    def run_script(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--root",
                str(root),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_pass_when_all_sources_match(self) -> None:
        patterns = ["backend/**", "frontend/**", "scripts/**"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_agents(root / "AGENTS.md", patterns)
            write_manual(root / "docs/agent_manual/02_working_memory_contract.md", patterns)
            write_contract(root / "scripts/contracts/workpack_agent_report_contract.json", patterns)

            proc = self.run_script(root)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_fail_when_manual_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_agents(root / "AGENTS.md", ["backend/**", "scripts/**"])
            write_manual(
                root / "docs/agent_manual/02_working_memory_contract.md",
                ["backend/**", "frontend/**"],
            )
            write_contract(
                root / "scripts/contracts/workpack_agent_report_contract.json",
                ["backend/**", "scripts/**"],
            )

            proc = self.run_script(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("MANUAL_CONTRACT_MISMATCH", proc.stdout)

    def test_fail_when_agents_trigger_heading_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# AGENTS\n## no heading\n- `backend/**`\n", encoding="utf-8")
            write_manual(root / "docs/agent_manual/02_working_memory_contract.md", ["backend/**"])
            write_contract(root / "scripts/contracts/workpack_agent_report_contract.json", ["backend/**"])

            proc = self.run_script(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("AGENTS_TRIGGER_SECTION_MISSING", proc.stdout)


if __name__ == "__main__":
    unittest.main()
