from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_spec_sync_report_updated.py"


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


class AssertSpecSyncReportUpdatedTest(unittest.TestCase):
    def init_repo(self, root: Path) -> str:
        run_git(root, "init")
        run_git(root, "config", "user.name", "test")
        run_git(root, "config", "user.email", "test@example.com")

        write_text(
            root / "docs/references/Summary of key features.csv",
            "Feature,요구사항ID\nA,AI-001\n",
        )
        write_text(
            root / "spec_sync_report.md",
            "Last synced at\nSource file\nVersion\nChange summary\n",
        )
        write_text(root / "README.md", "baseline\n")

        run_git(root, "add", ".")
        run_git(root, "commit", "-m", "initial")
        return run_git(root, "rev-parse", "HEAD")

    def run_script(self, root: Path, base_ref: str, head_ref: str, require_metadata: bool = False) -> subprocess.CompletedProcess[str]:
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
        if require_metadata:
            args.append("--require-metadata")
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
                root / "docs/references/Summary of key features.csv",
                "Feature,요구사항ID\nA,AI-002\n",
            )
            run_git(root, "add", "docs/references/Summary of key features.csv")
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
                root / "docs/references/Summary of key features.csv",
                "Feature,요구사항ID\nA,AI-003\n",
            )
            write_text(
                root / "spec_sync_report.md",
                "Last synced at: 2026-02-23\nSource file: docs/references/Summary of key features.csv\nVersion: abc123\nChange summary: spec refresh\n",
            )
            run_git(root, "add", "docs/references/Summary of key features.csv", "spec_sync_report.md")
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
                root / "docs/references/Summary of key features.csv",
                "Feature,요구사항ID\nA,AI-004\n",
            )
            write_text(root / "spec_sync_report.md", "updated only\n")
            run_git(root, "add", "docs/references/Summary of key features.csv", "spec_sync_report.md")
            run_git(root, "commit", "-m", "missing metadata")
            head = run_git(root, "rev-parse", "HEAD")

            proc = self.run_script(root, base, head, require_metadata=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SPEC_SYNC_REPORT_METADATA_MISSING", proc.stdout)


if __name__ == "__main__":
    unittest.main()
