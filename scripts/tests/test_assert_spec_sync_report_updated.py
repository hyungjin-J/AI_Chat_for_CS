from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_spec_sync_report_updated.py"
NOTION_EVIDENCE_ROOT = "docs/review/mvp_verification_pack/artifacts"
SUMMARY_PATH = "docs/references/Summary of key features.csv"
REQUIREMENTS_PATH = "docs/references/CS AI Chatbot_Requirements Statement.csv"
DEVELOPMENT_PATH = "docs/references/Development environment.csv"
UIUX_PATH = "docs/uiux/CS_RAG_UI_UX_설계서.xlsx"
SUMMARY_URL = "https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149"
REQUIREMENTS_URL = "https://www.notion.so/2ed405a3a720816594e4dc34972174ec"
DEVELOPMENT_URL = "https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7"
UIUX_URL = "https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444"


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_spec_sync_report(
    source_files: list[str],
    notion_urls: list[str],
    version_value: str,
    *,
    last_synced_at: str = "2026-02-25 23:39:05 +09:00",
    summary_lines: int = 3,
) -> str:
    source_lines = "\n".join(f"  - {item}" for item in source_files)
    summary = "\n".join(f"  {index + 1}. summary line {index + 1}" for index in range(summary_lines))
    notion_lines = "\n".join(f"- Notion URL: {item}" for item in notion_urls)
    return textwrap.dedent(
        f"""\
        ## Session (Spec Sync)
        - Last synced at: {last_synced_at}
        - Source file:
        {source_lines}
        - Version(or commit): {version_value}
        - Change summary:
        {summary}
        {notion_lines}
        """
    )


def build_notion_sync_evidence(
    source_files: list[str],
    notion_pages: list[str],
    version_value: str,
    *,
    last_synced_at_kst: str = "2026-02-27 09:00:00 +09:00",
    summary_lines: int = 3,
) -> str:
    source_lines = "\n".join(f"  - {item}" for item in source_files)
    summary = "\n".join(f"  {index + 1}. summary line {index + 1}" for index in range(summary_lines))
    notion_lines = "\n".join(f"  - {item}" for item in notion_pages)
    return textwrap.dedent(
        f"""\
        ## Notion Sync Evidence
        - last_synced_at_kst: {last_synced_at_kst}
        - source_file(s):
        {source_lines}
        - version/commit: {version_value}
        - notion_page:
        {notion_lines}
        - change_summary:
        {summary}
        """
    )


class AssertSpecSyncReportUpdatedTest(unittest.TestCase):
    def init_repo(self, root: Path) -> str:
        run_git(root, "init")
        run_git(root, "config", "user.name", "test")
        run_git(root, "config", "user.email", "test@example.com")

        write_text(root / SUMMARY_PATH, "Feature,ReqID\nA,AI-001\n")
        write_text(root / REQUIREMENTS_PATH, "Requirement,ReqID\nA,AI-001\n")
        write_text(root / DEVELOPMENT_PATH, "Feature,ReqID\nA,AI-001\n")
        write_text(root / UIUX_PATH, "sheet,description\nmain,baseline\n")
        write_text(
            root / "spec_sync_report.md",
            "## baseline\n- Last synced at: 2026-02-25 23:39:05 +09:00\n",
        )
        write_text(root / "README.md", "baseline\n")

        run_git(root, "add", ".")
        run_git(root, "commit", "-m", "initial")
        return run_git(root, "rev-parse", "HEAD")

    def run_script(
        self,
        root: Path,
        *,
        base_ref: str,
        head_ref: str,
        changed_files: str | None = None,
        mode: str | None = None,
        notion_evidence_date: str | None = None,
        notion_evidence_root: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = [
            "python",
            str(SCRIPT_PATH),
            "--root",
            str(root),
            "--base-ref",
            base_ref,
            "--head-ref",
            head_ref,
        ]
        if changed_files is not None:
            args.extend(["--changed-files", changed_files])
        if mode is not None:
            args.extend(["--mode", mode])
        if notion_evidence_date is not None:
            args.extend(["--notion-evidence-date", notion_evidence_date])
        if notion_evidence_root is not None:
            args.extend(["--notion-evidence-root", notion_evidence_root])
        return subprocess.run(
            args,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_pass_when_no_spec_file_changed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self.init_repo(root)
            write_text(root / "README.md", "changed\n")
            run_git(root, "add", "README.md")
            run_git(root, "commit", "-m", "docs")
            head = run_git(root, "rev-parse", "HEAD")

            proc = self.run_script(root, base_ref=base, head_ref=head)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("spec_changed_count=0", proc.stdout)

    # a) canonical file changed + spec_sync_report unchanged -> FAIL
    def test_fail_when_spec_changed_without_report_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self.init_repo(root)
            write_text(root / SUMMARY_PATH, "Feature,ReqID\nA,AI-002\n")
            run_git(root, "add", SUMMARY_PATH)
            run_git(root, "commit", "-m", "spec change")
            head = run_git(root, "rev-parse", "HEAD")

            proc = self.run_script(root, base_ref=base, head_ref=head)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_REPORT_NOT_UPDATED", proc.stdout)

    # b) 2 canonical files changed + report has only one -> FAIL
    def test_fail_when_one_of_two_changed_files_missing_in_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = "\n".join([SUMMARY_PATH, REQUIREMENTS_PATH, "spec_sync_report.md"])

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                changed_files=changed_files,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_EVIDENCE_BLOCK_MISSING", proc.stdout)
            self.assertIn(REQUIREMENTS_PATH, proc.stdout)

    # c) notion domain matches but path differs -> FAIL
    def test_fail_when_notion_url_path_is_mismatched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=["https://www.notion.so/2ed405a3a72081d594b2c3738b3c8140"],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(root, base_ref=head, head_ref=head, changed_files=changed_files)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_NOTION_URL_MISMATCH", proc.stdout)

    # d) Last synced at missing +09:00 -> FAIL
    def test_fail_when_last_synced_at_has_no_plus_0900(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value=head,
                last_synced_at="2026-02-25 23:39:05 KST",
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(root, base_ref=head, head_ref=head, changed_files=changed_files)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_LAST_SYNCED_AT_INVALID_KST", proc.stdout)

    # e) version commit differs from HEAD -> FAIL
    def test_fail_when_commit_does_not_match_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(root, base_ref=head, head_ref=head, changed_files=changed_files)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_VERSION_HEAD_MISMATCH", proc.stdout)

    # f) all strict checks satisfied -> PASS
    def test_pass_when_all_strict_conditions_are_satisfied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH, REQUIREMENTS_PATH, DEVELOPMENT_PATH],
                notion_urls=[SUMMARY_URL, REQUIREMENTS_URL, DEVELOPMENT_URL],
                version_value=head,
                summary_lines=4,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = "\n".join(
                [SUMMARY_PATH, REQUIREMENTS_PATH, DEVELOPMENT_PATH, "spec_sync_report.md"]
            )

            proc = self.run_script(root, base_ref=head, head_ref=head, changed_files=changed_files)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    # regression: Source file filename exact match is enforced
    def test_fail_when_source_filename_case_or_name_is_not_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=["docs/references/summary of key features.csv"],
                notion_urls=[SUMMARY_URL],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(root, base_ref=head, head_ref=head, changed_files=changed_files)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_EVIDENCE_BLOCK_MISSING", proc.stdout)

    def test_pass_when_uiux_canonical_file_is_mapped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[UIUX_PATH],
                notion_urls=[UIUX_URL],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{UIUX_PATH}\nspec_sync_report.md"

            proc = self.run_script(root, base_ref=head, head_ref=head, changed_files=changed_files)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_warning_only_mode_warns_when_notion_evidence_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                changed_files=changed_files,
                notion_evidence_date="20260227",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("warning_count=1", proc.stdout)
            self.assertIn("NOTION_SYNC_EVIDENCE_SAME_DAY_MISSING", proc.stdout)

    def test_strict_all_mode_fails_when_notion_evidence_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                changed_files=changed_files,
                mode="strict-all",
                notion_evidence_date="20260227",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("NOTION_SYNC_EVIDENCE_SAME_DAY_MISSING", proc.stdout)

    def test_strict_all_mode_passes_with_valid_same_day_notion_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value=head,
                summary_lines=3,
            )
            evidence = build_notion_sync_evidence(
                source_files=[SUMMARY_PATH],
                notion_pages=[SUMMARY_URL],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            write_text(
                root / NOTION_EVIDENCE_ROOT / "notion_sync_evidence_20260227.md",
                evidence,
            )
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                changed_files=changed_files,
                mode="strict-all",
                notion_evidence_date="20260227",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("warning_count=0", proc.stdout)
            self.assertIn(
                "notion_evidence_file=docs/review/mvp_verification_pack/artifacts/notion_sync_evidence_20260227.md",
                proc.stdout,
            )


if __name__ == "__main__":
    unittest.main()
