from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_artifact_index.py"


def write_text(path: Path, content: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_script(artifact_root: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    args = [
        "python",
        str(SCRIPT_PATH),
        "--artifact-root",
        str(artifact_root),
        "--index-md",
        str(artifact_root / "_INDEX.md"),
        "--index-json",
        str(artifact_root / "_INDEX.json"),
        "--gate-output-txt",
        str(artifact_root / "artifact_index_gate.txt"),
        "--gate-output-json",
        str(artifact_root / "artifact_index_gate.json"),
    ]
    if check:
        args.append("--check")
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def load_index(artifact_root: Path) -> dict:
    return json.loads((artifact_root / "_INDEX.json").read_text(encoding="utf-8"))


def find_family(payload: dict, family_name: str) -> dict:
    for group in payload["groups"]:
        for family in group["families"]:
            if family["family"] == family_name:
                return family
    raise AssertionError(f"family not found: {family_name}")


class BuildArtifactIndexTest(unittest.TestCase):
    def test_build_is_deterministic_regardless_of_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            write_text(artifacts / "utf8_normalization_wave2_report.json")
            write_text(artifacts / "utf8_normalization_wave10_report.json")
            write_text(artifacts / "utf8_normalization_wave10_report.md")
            write_text(artifacts / "phase2_1_pr1_ci_step_summary_20260221.txt")
            write_text(artifacts / "phase2_1_pr1_ci_step_summary_202603XX.txt")
            write_text(artifacts / "phase2_1_4_unittest_output.txt")

            first = run_script(artifacts)
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            first_json = (artifacts / "_INDEX.json").read_text(encoding="utf-8")
            first_md = (artifacts / "_INDEX.md").read_text(encoding="utf-8")

            # mtime shuffle should not affect deterministic output.
            now = time.time()
            for offset, file_path in enumerate(sorted(artifacts.rglob("*"))):
                if file_path.is_file():
                    os.utime(file_path, (now + offset, now + offset))

            second = run_script(artifacts)
            self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
            second_json = (artifacts / "_INDEX.json").read_text(encoding="utf-8")
            second_md = (artifacts / "_INDEX.md").read_text(encoding="utf-8")

            self.assertEqual(first_json, second_json)
            self.assertEqual(first_md, second_md)

    def test_latest_selection_uses_wave_and_date_heuristics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            write_text(artifacts / "utf8_normalization_wave2_report.json")
            write_text(artifacts / "utf8_normalization_wave9_report.json")
            write_text(artifacts / "utf8_normalization_wave10_report.json")
            write_text(artifacts / "phase2_1_pr1_ci_step_summary_20260221.txt")
            write_text(artifacts / "phase2_1_pr1_ci_step_summary_202603XX.txt")

            proc = run_script(artifacts)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            payload = load_index(artifacts)

            wave_family = find_family(payload, "utf8_normalization_waveN_report")
            self.assertEqual(
                wave_family["latest_by_extension"][".json"],
                "utf8_normalization_wave10_report.json",
            )

            summary_family = find_family(payload, "phase2_1_pr1_ci_step_summary")
            self.assertEqual(
                summary_family["latest_by_extension"][".txt"],
                "phase2_1_pr1_ci_step_summary_202603XX.txt",
            )

    def test_check_mode_fails_on_missing_and_stale_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            write_text(artifacts / "spec_consistency_check_report.json")

            missing = run_script(artifacts, check=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("INDEX_MISSING", missing.stdout)

            built = run_script(artifacts)
            self.assertEqual(built.returncode, 0, msg=built.stdout + built.stderr)

            index_md = artifacts / "_INDEX.md"
            index_md.write_text(index_md.read_text(encoding="utf-8") + "\n# stale\n", encoding="utf-8")

            stale = run_script(artifacts, check=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("INDEX_STALE", stale.stdout)


if __name__ == "__main__":
    unittest.main()
