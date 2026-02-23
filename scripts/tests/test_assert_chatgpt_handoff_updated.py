from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_chatgpt_handoff_updated.py"


def run_script(changed_files: str, mode: str = "core-only") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(SCRIPT_PATH), "--changed-files", changed_files, "--mode", mode],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class AssertChatgptHandoffUpdatedTest(unittest.TestCase):
    def test_pass_when_only_handoff_docs_changed(self) -> None:
        changed = "\n".join(
            [
                "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md",
                "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md",
            ]
        )
        proc = run_script(changed)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("status=PASS", proc.stdout)
        self.assertIn("trigger_changed_count=0", proc.stdout)

    def test_fail_when_core_changed_without_handoff_docs(self) -> None:
        proc = run_script("scripts/spec_consistency_check.py", mode="core-only")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("status=FAIL", proc.stdout)
        self.assertIn("CHATGPT_HANDOFF_NOT_UPDATED", proc.stdout)
        self.assertIn("core_changed_count=1", proc.stdout)

    def test_fail_when_core_changed_with_partial_handoff_docs(self) -> None:
        changed = "\n".join(
            [
                "scripts/spec_consistency_check.py",
                "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md",
            ]
        )
        proc = run_script(changed, mode="core-only")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("status=FAIL", proc.stdout)
        self.assertIn("missing_handoff_docs=chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md", proc.stdout)

    def test_pass_when_core_changed_with_both_handoff_docs(self) -> None:
        changed = "\n".join(
            [
                "scripts/spec_consistency_check.py",
                "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md",
                "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md",
            ]
        )
        proc = run_script(changed, mode="core-only")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("status=PASS", proc.stdout)
        self.assertIn("required_handoff_docs_changed=True", proc.stdout)

    def test_pass_when_non_core_changed_without_handoff_docs_in_core_only_mode(self) -> None:
        proc = run_script("README.md", mode="core-only")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("status=PASS", proc.stdout)
        self.assertIn("core_changed_count=0", proc.stdout)
        self.assertIn("warning_count=1", proc.stdout)
        self.assertIn("CHATGPT_HANDOFF_RECOMMENDED", proc.stdout)

    def test_pass_when_non_blocking_docs_changed_without_handoff_docs(self) -> None:
        proc = run_script(
            "docs/review/mvp_verification_pack/artifacts/some_artifact.txt",
            mode="core-only",
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("status=PASS", proc.stdout)
        self.assertIn("non_blocking_changed_count=1", proc.stdout)
        self.assertIn("warning_count=0", proc.stdout)

    def test_fail_when_non_core_changed_without_handoff_docs_in_strict_all_mode(self) -> None:
        proc = run_script("README.md", mode="strict-all")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("status=FAIL", proc.stdout)
        self.assertIn("CHATGPT_HANDOFF_NOT_UPDATED", proc.stdout)
        self.assertIn("mode=strict-all", proc.stdout)


if __name__ == "__main__":
    unittest.main()
