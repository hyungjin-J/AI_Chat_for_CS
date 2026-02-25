from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_spec_sync_report_updated.py"
SUMMARY_PATH = "docs/references/Summary of key features.csv"
REQUIREMENTS_PATH = "docs/references/CS AI Chatbot_Requirements Statement.csv"
DEVELOPMENT_PATH = "docs/references/Development environment.csv"
SUMMARY_URL = "https://www.notion.so/2ed405a3a72081d594b2c3738b3c8149"
REQUIREMENTS_URL = "https://www.notion.so/2ed405a3a720816594e4dc34972174ec"
DEVELOPMENT_URL = "https://www.notion.so/2ed405a3a72081d198e6f648e508b6e7"


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


class AssertSpecSyncReportUpdatedTest(unittest.TestCase):
    def init_repo(self, root: Path) -> str:
        run_git(root, "init")
        run_git(root, "config", "user.name", "test")
        run_git(root, "config", "user.email", "test@example.com")

        write_text(
            root / SUMMARY_PATH,
            "Feature,ReqID\nA,AI-001\n",
        )
        write_text(
            root / REQUIREMENTS_PATH,
            "Requirement,ReqID\nA,AI-001\n",
        )
        write_text(
            root / DEVELOPMENT_PATH,
            "Feature,ReqID\nA,AI-001\n",
        )
        write_text(
            root / "spec_sync_report.md",
            "Last synced at\nSource file\nVersion\nChange summary\n",
        )
        write_text(root / "README.md", "baseline\n")

        run_git(root, "add", ".")
        run_git(root, "commit", "-m", "initial")
        return run_git(root, "rev-parse", "HEAD")

    def run_script(
        self,
        root: Path,
        base_ref: str,
        head_ref: str,
        require_metadata: bool = False,
        require_notion_evidence_format: bool = False,
        changed_files: str | None = None,
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
        if require_metadata:
            args.append("--require-metadata")
        if require_notion_evidence_format:
            args.append("--require-notion-evidence-format")
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

            proc = self.run_script(root, base, head)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("spec_changed_count=0", proc.stdout)

    def test_fail_when_spec_changed_without_spec_sync_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self.init_repo(root)
            write_text(
                root / SUMMARY_PATH,
                "Feature,ReqID\nA,AI-002\n",
            )
            run_git(root, "add", SUMMARY_PATH)
            run_git(root, "commit", "-m", "spec change")
            head = run_git(root, "rev-parse", "HEAD")

            proc = self.run_script(root, base, head)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_REPORT_NOT_UPDATED", proc.stdout)

    def test_pass_when_spec_and_report_are_updated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self.init_repo(root)
            write_text(
                root / SUMMARY_PATH,
                "Feature,ReqID\nA,AI-003\n",
            )
            write_text(
                root / "spec_sync_report.md",
                "Last synced at: 2026-02-23\nSource file: docs/references/Summary of key features.csv\nVersion: abc123\nChange summary: spec refresh\n",
            )
            run_git(root, "add", SUMMARY_PATH, "spec_sync_report.md")
            run_git(root, "commit", "-m", "spec and report")
            head = run_git(root, "rev-parse", "HEAD")

            proc = self.run_script(root, base, head, require_metadata=True)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("spec_sync_report_changed=True", proc.stdout)

    def test_fail_when_metadata_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = self.init_repo(root)
            write_text(
                root / SUMMARY_PATH,
                "Feature,ReqID\nA,AI-004\n",
            )
            write_text(root / "spec_sync_report.md", "updated only\n")
            run_git(root, "add", SUMMARY_PATH, "spec_sync_report.md")
            run_git(root, "commit", "-m", "missing metadata")
            head = run_git(root, "rev-parse", "HEAD")

            proc = self.run_script(root, base, head, require_metadata=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_REPORT_METADATA_MISSING", proc.stdout)

    def test_strict_pass_with_single_source_evidence(self) -> None:
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
                require_metadata=True,
                require_notion_evidence_format=True,
                changed_files=changed_files,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("source_evidence=docs/references/Summary of key features.csv status=PASS", proc.stdout)

    def test_strict_pass_with_multiple_sources_in_single_section(self) -> None:
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

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                require_metadata=True,
                require_notion_evidence_format=True,
                changed_files=changed_files,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_strict_fail_when_source_file_block_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[DEVELOPMENT_PATH],
                notion_urls=[DEVELOPMENT_URL],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                require_metadata=True,
                require_notion_evidence_format=True,
                changed_files=changed_files,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_EVIDENCE_BLOCK_MISSING", proc.stdout)

    def test_strict_fail_when_last_synced_at_kst_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value=head,
                last_synced_at="2026-02-25 23:39:05",
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                require_metadata=True,
                require_notion_evidence_format=True,
                changed_files=changed_files,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_LAST_SYNCED_AT_INVALID_KST", proc.stdout)

    def test_strict_fail_when_version_commit_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value="working tree",
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                require_metadata=True,
                require_notion_evidence_format=True,
                changed_files=changed_files,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_VERSION_COMMIT_MISSING", proc.stdout)

    def test_strict_fail_when_version_commit_does_not_match_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value="deadbee",
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                require_metadata=True,
                require_notion_evidence_format=True,
                changed_files=changed_files,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_VERSION_HEAD_MISMATCH", proc.stdout)

    def test_strict_fail_when_notion_url_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[REQUIREMENTS_URL],
                version_value=head,
                summary_lines=3,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                require_metadata=True,
                require_notion_evidence_format=True,
                changed_files=changed_files,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_NOTION_URL_MISMATCH", proc.stdout)

    def test_strict_fail_when_change_summary_line_count_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            report = build_spec_sync_report(
                source_files=[SUMMARY_PATH],
                notion_urls=[SUMMARY_URL],
                version_value=head,
                summary_lines=2,
            )
            write_text(root / "spec_sync_report.md", report)
            changed_files = f"{SUMMARY_PATH}\nspec_sync_report.md"

            proc = self.run_script(
                root,
                base_ref=head,
                head_ref=head,
                require_metadata=True,
                require_notion_evidence_format=True,
                changed_files=changed_files,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_CHANGE_SUMMARY_COUNT_INVALID", proc.stdout)


if __name__ == "__main__":
    unittest.main()
