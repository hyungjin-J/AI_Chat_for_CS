from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "lint_chatgpt_handoff_docs.py"


def build_doc(updated_at: str, evidence_path: str, extra_line: str = "") -> str:
    bullets = "\n".join(f"- item {idx}" for idx in range(1, 11))
    extra_block = f"\n{extra_line}\n" if extra_line else "\n"
    return (
        "# Handoff Doc\n\n"
        f"- updated_at_kst: {updated_at}\n"
        "- base_commit_hash: abc1234\n"
        "- release_tag: 2026.03XX-phase2.1.3-gate-regression-drift-prevention\n"
        "- branch: main\n\n"
        "## 0) Change Summary (Added/Changed/Fixed/Removed, 10 lines)\n"
        f"{bullets}\n\n"
        "## 3) Validation Gate\n"
        "| Gate | Status | Evidence |\n"
        "|---|---|---|\n"
        f"| sample | PASS | {evidence_path} |\n"
        "| spec sync | PASS | spec_sync_report.md |\n"
        f"{extra_block}"
    )


class LintChatGptHandoffDocsTest(unittest.TestCase):
    def run_lint(self, workspace: Path) -> tuple[int, dict]:
        output_json = workspace / "lint.json"
        output_txt = workspace / "lint.txt"
        cmd = [
            "python",
            str(SCRIPT_PATH),
            "--files",
            "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md",
            "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md",
            "--output-json",
            str(output_json),
            "--output-txt",
            str(output_txt),
        ]
        proc = subprocess.run(
            cmd,
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        return proc.returncode, payload

    def prepare_workspace(self) -> Path:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        (root / "chatGPT").mkdir(parents=True, exist_ok=True)
        (root / "docs/review/mvp_verification_pack/artifacts").mkdir(parents=True, exist_ok=True)
        (root / "spec_sync_report.md").write_text("spec sync record\n", encoding="utf-8")
        return root

    def test_placeholder_updated_at_fails(self) -> None:
        root = self.prepare_workspace()
        evidence_path = "docs/review/mvp_verification_pack/artifacts/e1.txt"
        (root / evidence_path).write_text("ok\n", encoding="utf-8")

        doc = build_doc(updated_at="TBD", evidence_path=evidence_path)
        (root / "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md").write_text(doc, encoding="utf-8")
        (root / "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md").write_text(doc, encoding="utf-8")

        code, payload = self.run_lint(root)
        self.assertNotEqual(code, 0)
        self.assertGreater(payload["violation_count"], 0)

    def test_control_char_fails(self) -> None:
        root = self.prepare_workspace()
        evidence_path = "docs/review/mvp_verification_pack/artifacts/e2.txt"
        (root / evidence_path).write_text("ok\n", encoding="utf-8")

        control_char_line = "control-char=" + chr(0x07)
        doc = build_doc(
            updated_at="2026-02-22 00:00:00 +09:00",
            evidence_path=evidence_path,
            extra_line=control_char_line,
        )
        (root / "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md").write_text(doc, encoding="utf-8")
        (root / "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md").write_text(doc, encoding="utf-8")

        code, payload = self.run_lint(root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any(v["code"] == "DOC_CONTROL_CHAR" for v in payload["violations"]))

    def test_tab_character_fails(self) -> None:
        root = self.prepare_workspace()
        evidence_path = "docs/review/mvp_verification_pack/artifacts/e2_tab.txt"
        (root / evidence_path).write_text("ok\n", encoding="utf-8")

        doc = build_doc(
            updated_at="2026-02-22 00:00:00 +09:00",
            evidence_path=evidence_path,
            extra_line="tab\tcharacter",
        )
        (root / "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md").write_text(doc, encoding="utf-8")
        (root / "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md").write_text(doc, encoding="utf-8")

        code, payload = self.run_lint(root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any(v["code"] == "DOC_TAB_CHARACTER" for v in payload["violations"]))

    def test_trace_id_typo_fails(self) -> None:
        root = self.prepare_workspace()
        evidence_path = "docs/review/mvp_verification_pack/artifacts/e3.txt"
        (root / evidence_path).write_text("ok\n", encoding="utf-8")

        typo_key = "r" + "ace_id"
        doc = build_doc(
            updated_at="2026-02-22 00:00:00 +09:00",
            evidence_path=evidence_path,
            extra_line=f"{typo_key}: typo",
        )
        (root / "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md").write_text(doc, encoding="utf-8")
        (root / "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md").write_text(doc, encoding="utf-8")

        code, payload = self.run_lint(root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any(v["code"] == "DOC_TRACE_TYPO" for v in payload["violations"]))

    def test_trace_id_additional_typo_fails(self) -> None:
        root = self.prepare_workspace()
        evidence_path = "docs/review/mvp_verification_pack/artifacts/e3b.txt"
        (root / evidence_path).write_text("ok\n", encoding="utf-8")

        doc = build_doc(
            updated_at="2026-02-22 00:00:00 +09:00",
            evidence_path=evidence_path,
            extra_line="trcae_id: typo",
        )
        (root / "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md").write_text(doc, encoding="utf-8")
        (root / "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md").write_text(doc, encoding="utf-8")

        code, payload = self.run_lint(root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any(v["code"] == "DOC_TRACE_TYPO" for v in payload["violations"]))

    def test_missing_evidence_path_fails(self) -> None:
        root = self.prepare_workspace()
        missing_path = "docs/review/mvp_verification_pack/artifacts/not-found.txt"

        doc = build_doc(updated_at="2026-02-22 00:00:00 +09:00", evidence_path=missing_path)
        (root / "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md").write_text(doc, encoding="utf-8")
        (root / "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md").write_text(doc, encoding="utf-8")

        code, payload = self.run_lint(root)
        self.assertNotEqual(code, 0)
        self.assertGreater(payload["missing_paths_count"], 0)
        self.assertIn(missing_path, payload["missing_paths"])

    def test_forbidden_literal_generated_at_runtime_fails(self) -> None:
        root = self.prepare_workspace()
        evidence_path = "docs/review/mvp_verification_pack/artifacts/e4.txt"
        (root / evidence_path).write_text("ok\n", encoding="utf-8")

        token_literal = "OPENAI" + "_API_KEY"
        doc = build_doc(
            updated_at="2026-02-22 00:00:00 +09:00",
            evidence_path=evidence_path,
            extra_line=f"{token_literal} should be redacted",
        )
        (root / "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md").write_text(doc, encoding="utf-8")
        (root / "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md").write_text(doc, encoding="utf-8")

        code, payload = self.run_lint(root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any(v["code"] == "DOC_FORBIDDEN_LITERAL" for v in payload["violations"]))

    def test_normal_docs_pass(self) -> None:
        root = self.prepare_workspace()
        evidence_path = "docs/review/mvp_verification_pack/artifacts/e5.txt"
        (root / evidence_path).write_text("ok\n", encoding="utf-8")

        doc = build_doc(updated_at="2026-02-22 00:00:00 +09:00", evidence_path=evidence_path)
        (root / "chatGPT/CHATGPT_SELF_CONTAINED_BRIEFING_EN.md").write_text(doc, encoding="utf-8")
        (root / "chatGPT/IMPLEMENTATION_GUIDE_FOR_CHATGPT.md").write_text(doc, encoding="utf-8")

        code, payload = self.run_lint(root)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["missing_paths_count"], 0)
        self.assertGreaterEqual(payload["scanned_tables_count"], 2)


if __name__ == "__main__":
    unittest.main()
