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


if __name__ == "__main__":
    unittest.main()
