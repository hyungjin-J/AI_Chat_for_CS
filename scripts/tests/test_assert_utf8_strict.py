from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_utf8_strict.py"


class Utf8StrictGateTest(unittest.TestCase):
    def run_script(
        self,
        root: Path,
        changed_files: list[str] | None = None,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = [
            "python",
            str(SCRIPT_PATH),
            "--root",
            str(root),
        ]
        if changed_files is not None:
            args.extend(["--changed-files", "\n".join(changed_files)])
        if extra_args:
            args.extend(extra_args)
        return subprocess.run(
            args,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_pass_on_utf8_without_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs/review/mvp_verification_pack/artifacts/pass.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok\n", encoding="utf-8")

            proc = self.run_script(root, ["docs/review/mvp_verification_pack/artifacts/pass.txt"])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_fail_on_utf16_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs/review/mvp_verification_pack/artifacts/fail_utf16.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes("utf16-content".encode("utf-16"))

            proc = self.run_script(root, ["docs/review/mvp_verification_pack/artifacts/fail_utf16.txt"])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("UTF16_BOM_FORBIDDEN", proc.stdout)

    def test_fail_on_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs/review/mvp_verification_pack/artifacts/fail_utf8_bom.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\xef\xbb\xbf" + "hello".encode("utf-8"))

            proc = self.run_script(root, ["docs/review/mvp_verification_pack/artifacts/fail_utf8_bom.txt"])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("UTF8_BOM_FORBIDDEN", proc.stdout)

    def test_fail_on_non_utf8_binary_text_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs/review/mvp_verification_pack/artifacts/fail_non_utf8.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\x80\x81\x82")

            proc = self.run_script(root, ["docs/review/mvp_verification_pack/artifacts/fail_non_utf8.txt"])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("NON_UTF8_TEXT", proc.stdout)

    def test_full_scan_skips_node_modules_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "docs/review/mvp_verification_pack/artifacts/good.txt"
            bad_ignored = root / "frontend/node_modules/ignored_bad.txt"
            good.parent.mkdir(parents=True, exist_ok=True)
            bad_ignored.parent.mkdir(parents=True, exist_ok=True)
            good.write_text("ok\n", encoding="utf-8")
            bad_ignored.write_bytes(b"\xef\xbb\xbfbad")

            proc = self.run_script(root, changed_files=None, extra_args=["--full-scan"])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_baseline_ratchet_fails_on_new_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs/review/mvp_verification_pack/artifacts/new_bad.txt"
            baseline = root / "docs/review/mvp_verification_pack/artifacts/utf8_full_scan_baseline_violations.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\xef\xbb\xbfbad")
            baseline.write_text("{\"violations\": []}\n", encoding="utf-8")

            proc = self.run_script(
                root,
                changed_files=["docs/review/mvp_verification_pack/artifacts/new_bad.txt"],
                extra_args=["--baseline-file", "docs/review/mvp_verification_pack/artifacts/utf8_full_scan_baseline_violations.json"],
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("new_violation_count=1", proc.stdout)

    def test_fail_when_baseline_grows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = root / "docs/review/mvp_verification_pack/artifacts/head_baseline.json"
            base = root / "docs/review/mvp_verification_pack/artifacts/base_baseline.json"
            head.parent.mkdir(parents=True, exist_ok=True)
            head.write_text(
                json.dumps(
                    {
                        "violations": [
                            {
                                "code": "UTF8_BOM_FORBIDDEN",
                                "path": "docs/review/mvp_verification_pack/artifacts/old.txt",
                                "details": "old",
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            base.write_text('{"violations":[]}\n', encoding="utf-8")

            proc = self.run_script(
                root,
                changed_files=[],
                extra_args=[
                    "--baseline-file",
                    "docs/review/mvp_verification_pack/artifacts/head_baseline.json",
                    "--baseline-base-file",
                    "docs/review/mvp_verification_pack/artifacts/base_baseline.json",
                ],
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("baseline_growth_count=1", proc.stdout)

    def test_pass_when_baseline_size_is_same(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = root / "docs/review/mvp_verification_pack/artifacts/head_baseline.json"
            base = root / "docs/review/mvp_verification_pack/artifacts/base_baseline.json"
            sample = {
                "violations": [
                    {
                        "code": "UTF8_BOM_FORBIDDEN",
                        "path": "docs/review/mvp_verification_pack/artifacts/same.txt",
                        "details": "same",
                    }
                ]
            }
            head.parent.mkdir(parents=True, exist_ok=True)
            head.write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")
            base.write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")

            proc = self.run_script(
                root,
                changed_files=[],
                extra_args=[
                    "--baseline-file",
                    "docs/review/mvp_verification_pack/artifacts/head_baseline.json",
                    "--baseline-base-file",
                    "docs/review/mvp_verification_pack/artifacts/base_baseline.json",
                ],
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("baseline_growth_count=0", proc.stdout)

    def test_pass_when_baseline_size_decreases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = root / "docs/review/mvp_verification_pack/artifacts/head_baseline.json"
            base = root / "docs/review/mvp_verification_pack/artifacts/base_baseline.json"
            head.parent.mkdir(parents=True, exist_ok=True)
            head.write_text('{"violations":[]}\n', encoding="utf-8")
            base.write_text(
                json.dumps(
                    {
                        "violations": [
                            {
                                "code": "UTF8_BOM_FORBIDDEN",
                                "path": "docs/review/mvp_verification_pack/artifacts/old.txt",
                                "details": "old",
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            proc = self.run_script(
                root,
                changed_files=[],
                extra_args=[
                    "--baseline-file",
                    "docs/review/mvp_verification_pack/artifacts/head_baseline.json",
                    "--baseline-base-file",
                    "docs/review/mvp_verification_pack/artifacts/base_baseline.json",
                ],
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("baseline_growth_count=0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
