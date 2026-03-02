from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_artifact_index.py"


def write_text(path: Path, content: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_script(artifact_root: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    archive_root = artifact_root.parent / "archive"
    archive_manifest = archive_root / "_ARCHIVE_MANIFEST.json"
    args = [
        "python",
        str(SCRIPT_PATH),
        "--artifact-root",
        str(artifact_root),
        "--archive-root",
        str(archive_root),
        "--archive-manifest",
        str(archive_manifest),
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def create_sidecar_archive(
    archive_root: Path,
    family_name: str,
    members: list[str],
    created_at_kst: str = "2026-02-27 09:00:00 +09:00",
) -> tuple[Path, Path]:
    safe_family = family_name.replace("/", "__")
    family_dir = archive_root / safe_family
    family_dir.mkdir(parents=True, exist_ok=True)
    zip_path = family_dir / f"20260227_{safe_family}.zip"
    manifest_path = family_dir / f"20260227_{safe_family}.manifest.json"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for member in members:
            zf.writestr(member, "sidecar\n")

    manifest_payload = {
        "schema_version": 1,
        "family_name": family_name,
        "created_at_kst": created_at_kst,
        "source_commit": "0123456789abcdef0123456789abcdef01234567",
        "zip_sha256": sha256_file(zip_path),
        "included_files": [{"path": member, "sha256": "dummy"} for member in members],
        "excluded_files": [],
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return zip_path, manifest_path


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
            archive_manifest = artifacts.parent / "archive" / "_ARCHIVE_MANIFEST.json"
            write_text(artifacts / "spec_consistency_check_report.json")

            missing = run_script(artifacts, check=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("INDEX_MISSING", missing.stdout)
            self.assertIn("ARCHIVE_MANIFEST_MISSING", missing.stdout)

            built = run_script(artifacts)
            self.assertEqual(built.returncode, 0, msg=built.stdout + built.stderr)
            self.assertTrue(archive_manifest.exists())

            index_md = artifacts / "_INDEX.md"
            index_md.write_text(index_md.read_text(encoding="utf-8") + "\n# stale\n", encoding="utf-8")

            stale = run_script(artifacts, check=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("INDEX_STALE", stale.stdout)

    def test_check_mode_detects_archive_manifest_stale_and_missing_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            archive_manifest = artifacts.parent / "archive" / "_ARCHIVE_MANIFEST.json"
            write_text(artifacts / "utf8_normalization_wave2_report.json")

            built = run_script(artifacts)
            self.assertEqual(built.returncode, 0, msg=built.stdout + built.stderr)

            archive_manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "archive_root": "docs/review/mvp_verification_pack/archive",
                        "bundle_count": 1,
                        "archived_file_count": 1,
                        "bundles": [
                            {
                                "bundle_path": "C:/nonexistent/archive/missing_bundle.zip",
                                "family": "utf8_normalization_waveN_report",
                                "created_at_utc": "2026-02-26T00:00:00Z",
                                "file_count": 1,
                                "members": ["utf8_normalization_wave2_report.json"],
                            }
                        ],
                        "archived_files": [
                            {
                                "original_path": "utf8_normalization_wave2_report.json",
                                "family": "utf8_normalization_waveN_report",
                                "bundle_path": "C:/nonexistent/archive/missing_bundle.zip",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            stale = run_script(artifacts, check=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("ARCHIVE_MANIFEST_STALE", stale.stdout)
            self.assertIn("ARCHIVE_BUNDLE_MISSING", stale.stdout)

    def test_check_mode_detects_sidecar_manifest_missing_for_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            archive_root = artifacts.parent / "archive"
            write_text(artifacts / "utf8_normalization_wave2_report.json")

            built = run_script(artifacts)
            self.assertEqual(built.returncode, 0, msg=built.stdout + built.stderr)

            family_dir = archive_root / "utf8_normalization_waveN_report"
            family_dir.mkdir(parents=True, exist_ok=True)
            zip_path = family_dir / "20260227_utf8_normalization_waveN_report.zip"
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("utf8_normalization_wave2_report.json", "x\n")

            checked = run_script(artifacts, check=True)
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("ARCHIVE_SIDECAR_MANIFEST_MISSING", checked.stdout)

    def test_check_mode_detects_sidecar_sha_and_membership_mismatch_and_missing_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            write_text(artifacts / "utf8_normalization_wave2_report.json")
            write_text(artifacts / "utf8_normalization_wave3_report.json")

            built = run_script(artifacts)
            self.assertEqual(built.returncode, 0, msg=built.stdout + built.stderr)

            archive_root = artifacts.parent / "archive"
            zip_path, manifest_path = create_sidecar_archive(
                archive_root=archive_root,
                family_name="utf8_normalization_waveN_report",
                members=["utf8_normalization_wave2_report.json"],
            )

            rebuilt = run_script(artifacts)
            self.assertEqual(rebuilt.returncode, 0, msg=rebuilt.stdout + rebuilt.stderr)

            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["zip_sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            sha_check = run_script(artifacts, check=True)
            self.assertNotEqual(sha_check.returncode, 0)
            self.assertIn("ARCHIVE_ZIP_SHA256_MISMATCH", sha_check.stdout)

            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["zip_sha256"] = sha256_file(zip_path)
            payload["included_files"] = [{"path": "utf8_normalization_wave3_report.json", "sha256": "dummy"}]
            manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            member_check = run_script(artifacts, check=True)
            self.assertNotEqual(member_check.returncode, 0)
            self.assertIn("ARCHIVE_INCLUDED_LIST_MISMATCH", member_check.stdout)

            zip_path.unlink()
            missing_zip_check = run_script(artifacts, check=True)
            self.assertNotEqual(missing_zip_check.returncode, 0)
            self.assertIn("ARCHIVE_ZIP_MISSING", missing_zip_check.stdout)

    def test_index_surfaces_release_dashboard_in_start_here(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            write_text(artifacts / "release_gate_dashboard.md", "# Release Gate Dashboard\n")
            write_text(artifacts / "release_gate_dashboard.json", "{}\n")
            write_text(artifacts / "spec_impl_coverage_report.md", "# Spec Coverage\n")
            write_text(artifacts / "spec_impl_coverage_report.json", "{}\n")
            write_text(artifacts / "spec_impl_coverage_report.txt", "spec_impl_coverage_report\n")
            write_text(artifacts / "spec_impl_coverage_gate.json", "{}\n")
            write_text(artifacts / "spec_impl_coverage_gate.txt", "assert_spec_impl_coverage\n")
            write_text(artifacts / "spec_consistency_check_report.json")

            proc = run_script(artifacts)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

            payload = load_index(artifacts)
            self.assertIn("start_here", payload)
            self.assertIn("release_gate_dashboard", payload)
            self.assertIn("spec_impl_coverage", payload)
            self.assertEqual(payload["release_gate_dashboard"]["markdown_path"], "release_gate_dashboard.md")
            self.assertEqual(payload["release_gate_dashboard"]["json_path"], "release_gate_dashboard.json")
            self.assertTrue(payload["release_gate_dashboard"]["markdown_present"])
            self.assertTrue(payload["release_gate_dashboard"]["json_present"])
            self.assertTrue(payload["spec_impl_coverage"]["report_markdown_present"])
            self.assertTrue(payload["spec_impl_coverage"]["gate_json_present"])

            start_here_keys = [item["key"] for item in payload["start_here"]]
            self.assertIn("release_gate_dashboard_md", start_here_keys)
            self.assertIn("release_gate_dashboard_json", start_here_keys)
            self.assertIn("spec_impl_coverage_report_md", start_here_keys)
            self.assertIn("spec_impl_coverage_gate_json", start_here_keys)

            index_md = (artifacts / "_INDEX.md").read_text(encoding="utf-8")
            self.assertIn("## Start Here", index_md)
            self.assertIn("release_gate_dashboard.md", index_md)


if __name__ == "__main__":
    unittest.main()
