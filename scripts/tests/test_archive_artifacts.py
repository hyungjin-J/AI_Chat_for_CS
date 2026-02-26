from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_SCRIPT_PATH = REPO_ROOT / "scripts" / "archive_artifacts.py"


def write_text(path: Path, content: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_index_payload(
    artifact_root: Path,
    archive_root: Path,
    candidates: list[str],
    family_map: dict[str, str],
) -> Path:
    families: dict[str, list[str]] = {}
    for rel, family in family_map.items():
        families.setdefault(family, []).append(rel)

    group_families = []
    for family, files in sorted(families.items()):
        sorted_files = sorted(files)
        latest_by_extension: dict[str, str] = {}
        for rel in sorted_files:
            ext = Path(rel).suffix.lower()
            latest_by_extension[ext] = rel
        group_families.append(
            {
                "family": family,
                "file_count": len(sorted_files),
                "files": sorted_files,
                "latest_by_extension": latest_by_extension,
                "archive_candidates": [rel for rel in sorted_files if rel in candidates],
            }
        )

    payload = {
        "artifact_root": str(artifact_root),
        "indexed_file_count": len(family_map),
        "archive_keep_latest_per_extension": 1,
        "archive_manifest_path": str(archive_root / "_ARCHIVE_MANIFEST.json"),
        "pinned_paths_count": 0,
        "archive_summary": {
            "bundle_count": 0,
            "archived_file_count": 0,
            "recent_bundles": [],
        },
        "groups": [
            {
                "group": "report",
                "family_count": len(group_families),
                "families": group_families,
            }
        ],
        "latest_files": [],
        "archive_candidates": candidates,
    }

    index_json_path = artifact_root / "_INDEX.json"
    write_text(index_json_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return index_json_path


def run_archive_script(
    artifact_root: Path,
    archive_root: Path,
    index_json_path: Path,
    refresh_index: bool = False,
) -> subprocess.CompletedProcess[str]:
    args = [
        "python",
        str(ARCHIVE_SCRIPT_PATH),
        "--artifact-root",
        str(artifact_root),
        "--index-json",
        str(index_json_path),
        "--archive-root",
        str(archive_root),
        "--manifest-json",
        str(archive_root / "_ARCHIVE_MANIFEST.json"),
        "--output-txt",
        str(artifact_root / "artifact_archive_report.txt"),
        "--output-json",
        str(artifact_root / "artifact_archive_report.json"),
    ]
    if refresh_index:
        args.append("--refresh-index")
    else:
        args.append("--no-refresh-index")

    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def load_report_json(artifact_root: Path) -> dict:
    return json.loads((artifact_root / "artifact_archive_report.json").read_text(encoding="utf-8"))


class ArchiveArtifactsTest(unittest.TestCase):
    def test_archives_family_bundle_and_removes_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            archive_root = Path(tmp) / "docs/review/mvp_verification_pack/archive"

            wave_json = "utf8_normalization_wave2_report.json"
            wave_md = "utf8_normalization_wave2_report.md"
            write_text(artifacts / wave_json, "{}\n")
            write_text(artifacts / wave_md, "# wave2\n")

            family_map = {
                wave_json: "utf8_normalization_waveN_report",
                wave_md: "utf8_normalization_waveN_report",
            }
            index_path = write_index_payload(
                artifact_root=artifacts,
                archive_root=archive_root,
                candidates=[wave_json, wave_md],
                family_map=family_map,
            )

            proc = run_archive_script(artifacts, archive_root, index_path, refresh_index=False)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

            report = load_report_json(artifacts)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["created_bundle_count"], 1)
            self.assertEqual(report["archived_file_count"], 2)
            self.assertFalse((artifacts / wave_json).exists())
            self.assertFalse((artifacts / wave_md).exists())

            bundles = list((archive_root / "bundles").rglob("*.zip"))
            self.assertEqual(len(bundles), 1)
            with zipfile.ZipFile(bundles[0], "r") as zf:
                members = sorted(zf.namelist())
            self.assertEqual(members, [wave_json, wave_md])

    def test_skips_pinned_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            archive_root = Path(tmp) / "docs/review/mvp_verification_pack/archive"

            pinned_rel = "phase2_1_2_frontend_build_output.txt"
            candidate_rel = "utf8_normalization_wave2_report.json"
            write_text(artifacts / pinned_rel, "keep\n")
            write_text(artifacts / candidate_rel, "archive\n")

            family_map = {
                pinned_rel: "phase2_1_2_frontend_build_output",
                candidate_rel: "utf8_normalization_waveN_report",
            }
            index_path = write_index_payload(
                artifact_root=artifacts,
                archive_root=archive_root,
                candidates=[pinned_rel, candidate_rel],
                family_map=family_map,
            )

            proc = run_archive_script(artifacts, archive_root, index_path, refresh_index=False)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

            report = load_report_json(artifacts)
            self.assertEqual(report["status"], "PASS")
            self.assertGreaterEqual(report["skipped_pinned_count"], 1)
            self.assertIn(pinned_rel, report["skipped_pinned"])
            self.assertTrue((artifacts / pinned_rel).exists())
            self.assertFalse((artifacts / candidate_rel).exists())

    def test_idempotent_second_run_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            archive_root = Path(tmp) / "docs/review/mvp_verification_pack/archive"

            candidate_rel = "utf8_normalization_wave2_report.json"
            write_text(artifacts / candidate_rel, "archive\n")

            family_map = {candidate_rel: "utf8_normalization_waveN_report"}
            index_path = write_index_payload(
                artifact_root=artifacts,
                archive_root=archive_root,
                candidates=[candidate_rel],
                family_map=family_map,
            )

            first = run_archive_script(artifacts, archive_root, index_path, refresh_index=False)
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            first_report = load_report_json(artifacts)
            self.assertEqual(first_report["created_bundle_count"], 1)

            first_bundle_count = len(list((archive_root / "bundles").rglob("*.zip")))
            second = run_archive_script(artifacts, archive_root, index_path, refresh_index=False)
            self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
            second_report = load_report_json(artifacts)
            self.assertEqual(second_report["created_bundle_count"], 0)
            self.assertGreaterEqual(second_report["skipped_already_archived_count"], 1)
            second_bundle_count = len(list((archive_root / "bundles").rglob("*.zip")))
            self.assertEqual(first_bundle_count, second_bundle_count)


if __name__ == "__main__":
    unittest.main()
