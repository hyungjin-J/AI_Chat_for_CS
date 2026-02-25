from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "normalize_utf8.py"


class NormalizeUtf8Test(unittest.TestCase):
    def run_script(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--root",
                str(root),
                *args,
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_bom_removal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "sample_bom.txt"
            target.write_bytes(b"\xef\xbb\xbfhello\n")
            report_json = root / "report_bom.json"

            proc = self.run_script(
                root,
                "--paths",
                "sample_bom.txt",
                "--report-json",
                str(report_json),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            data = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertEqual(data["changed_count"], 1)
            item = data["results"][0]
            self.assertEqual(item["action"], "BOM_REMOVED")
            self.assertEqual(item["status"], "CHANGED")
            self.assertEqual(target.read_bytes(), b"hello\n")

    def test_utf16_to_utf8_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "sample_utf16.txt"
            target.write_bytes("가나다\n".encode("utf-16"))
            report_json = root / "report_utf16.json"

            proc = self.run_script(
                root,
                "--paths",
                "sample_utf16.txt",
                "--report-json",
                str(report_json),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            data = json.loads(report_json.read_text(encoding="utf-8"))
            item = data["results"][0]
            self.assertEqual(item["action"], "UTF16_TO_UTF8")
            self.assertEqual(item["status"], "CHANGED")
            raw = target.read_bytes()
            self.assertFalse(raw.startswith(b"\xff\xfe"))
            self.assertEqual(raw.decode("utf-8"), "가나다\n")

    def test_binary_skip_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "sample.bin"
            original = b"\x00\x01\x02\x03binary\x00payload"
            target.write_bytes(original)
            report_json = root / "report_bin.json"

            proc = self.run_script(
                root,
                "--paths",
                "sample.bin",
                "--report-json",
                str(report_json),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            data = json.loads(report_json.read_text(encoding="utf-8"))
            item = data["results"][0]
            self.assertEqual(item["status"], "SKIPPED")
            self.assertEqual(item["action"], "SKIP_BINARY_OR_UNDECODABLE")
            self.assertIn("binary file detected", item["message"])
            self.assertEqual(target.read_bytes(), original)

    def test_missing_file_is_reported_as_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_json = root / "report_missing.json"

            proc = self.run_script(
                root,
                "--paths",
                "missing.txt",
                "--report-json",
                str(report_json),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            data = json.loads(report_json.read_text(encoding="utf-8"))
            item = data["results"][0]
            self.assertEqual(item["status"], "SKIPPED")
            self.assertEqual(item["action"], "MISSING_FILE")
            self.assertEqual(item["old_line_endings"], "UNKNOWN")
            self.assertEqual(item["new_line_endings"], "UNKNOWN")
            self.assertEqual(item["message"], "file not found")

    def test_canonical_spec_guard_blocks_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs/references/Development environment.csv"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\xef\xbb\xbfname,desc\nx,y\n")

            proc = self.run_script(
                root,
                "--paths",
                "docs/references/Development environment.csv",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("canonical spec files are blocked by default", proc.stderr)
            self.assertTrue(target.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_canonical_spec_guard_requires_confirmation_with_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs/references/Summary of key features.csv"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\xef\xbb\xbfname,desc\nx,y\n")

            proc = self.run_script(
                root,
                "--paths",
                "docs/references/Summary of key features.csv",
                "--allow-canonical-spec",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("requires exact confirmation phrase", proc.stderr)
            self.assertTrue(target.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_canonical_spec_guard_allows_with_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs/references/google_ready_api_spec_v0.3_20260216.xlsx"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\xef\xbb\xbfplaceholder\n")
            report_json = root / "canonical_report.json"

            proc = self.run_script(
                root,
                "--paths",
                "docs/references/google_ready_api_spec_v0.3_20260216.xlsx",
                "--allow-canonical-spec",
                "--canonical-spec-confirm",
                "I understand Notion sync is required",
                "--report-json",
                str(report_json),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("override is active", proc.stderr)
            self.assertFalse(target.read_bytes().startswith(b"\xef\xbb\xbf"))
            data = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertEqual(data["changed_count"], 1)
            self.assertEqual(data["results"][0]["action"], "BOM_REMOVED")


if __name__ == "__main__":
    unittest.main()
