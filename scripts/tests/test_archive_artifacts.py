from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_SCRIPT_PATH = REPO_ROOT / "scripts" / "archive_artifacts.py"
REQUIRED_MANIFEST_FIELDS = {
    "zip_sha256",
    "created_at_kst",
    "source_commit",
    "family_name",
    "included_files",
    "excluded_files",
}


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
        "archive_layout_version": 2,
        "archive_keep_latest_per_extension": 1,
        "archive_manifest_path": str(archive_root / "_ARCHIVE_MANIFEST.json"),
        "pinned_paths_count": 0,
        "archive_summary": {
            "bundle_count": 0,
            "archived_file_count": 0,
            "sidecar_manifest_count": 0,
            "sidecar_archive_count": 0,
            "sidecar_archived_file_count": 0,
            "recent_bundles": [],
            "recent_sidecar_archives": [],
        },
        "archive_families": [],
        "latest_archives": [],
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


def list_sidecar_manifests(archive_root: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in archive_root.rglob("*.manifest.json")
            if path.is_file() and path.name != "_ARCHIVE_MANIFEST.json"
        ]
    )


def list_sidecar_zips(archive_root: Path) -> list[Path]:
    bundles_dir = (archive_root / "bundles").resolve()
    result: list[Path] = []
    for path in archive_root.rglob("*.zip"):
        if not path.is_file():
            continue
        try:
            path.resolve().relative_to(bundles_dir)
            continue
        except ValueError:
            result.append(path)
    return sorted(result)


class ArchiveArtifactsTest(unittest.TestCase):
    def test_archives_family_bundle_copy_only_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            archive_root = Path(tmp) / "docs/review/mvp_verification_pack/archive"

            older = "utf8_normalization_wave2_report.json"
            latest = "utf8_normalization_wave3_report.json"
            write_text(artifacts / older, '{"v":2}\n')
            write_text(artifacts / latest, '{"v":3}\n')

            family_map = {
                older: "utf8_normalization_waveN_report",
                latest: "utf8_normalization_waveN_report",
            }
            index_path = write_index_payload(
                artifact_root=artifacts,
                archive_root=archive_root,
                candidates=[older, latest],
                family_map=family_map,
            )

            proc = run_archive_script(artifacts, archive_root, index_path, refresh_index=False)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

            report = load_report_json(artifacts)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["created_bundle_count"], 1)
            self.assertEqual(report["archived_file_count"], 1)
            self.assertTrue((artifacts / older).exists())
            self.assertTrue((artifacts / latest).exists())
            self.assertIn(latest, report["retention_excluded"])

            sidecar_zips = list_sidecar_zips(archive_root)
            sidecar_manifests = list_sidecar_manifests(archive_root)
            self.assertEqual(len(sidecar_zips), 1)
            self.assertEqual(len(sidecar_manifests), 1)

            with zipfile.ZipFile(sidecar_zips[0], "r") as zf:
                members = sorted(zf.namelist())
            self.assertEqual(members, [older])

            manifest_payload = json.loads(sidecar_manifests[0].read_text(encoding="utf-8"))
            self.assertTrue(REQUIRED_MANIFEST_FIELDS.issubset(set(manifest_payload.keys())))
            self.assertRegex(
                str(manifest_payload["created_at_kst"]),
                r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+09:00$",
            )
            self.assertRegex(str(manifest_payload["source_commit"]), r"^[0-9a-f]{40}$")
            self.assertEqual([item["path"] for item in manifest_payload["included_files"]], [older])
            self.assertIn(latest, manifest_payload["excluded_files"])

    def test_skips_pinned_candidates_and_keeps_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            archive_root = Path(tmp) / "docs/review/mvp_verification_pack/archive"

            pinned_rel = "phase2_1_2_frontend_build_output.txt"
            older = "utf8_normalization_wave2_report.json"
            latest = "utf8_normalization_wave3_report.json"
            write_text(artifacts / pinned_rel, "keep\n")
            write_text(artifacts / older, '{"v":2}\n')
            write_text(artifacts / latest, '{"v":3}\n')

            family_map = {
                pinned_rel: "phase2_1_2_frontend_build_output",
                older: "utf8_normalization_waveN_report",
                latest: "utf8_normalization_waveN_report",
            }
            index_path = write_index_payload(
                artifact_root=artifacts,
                archive_root=archive_root,
                candidates=[pinned_rel, older, latest],
                family_map=family_map,
            )

            proc = run_archive_script(artifacts, archive_root, index_path, refresh_index=False)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

            report = load_report_json(artifacts)
            self.assertEqual(report["status"], "PASS")
            self.assertGreaterEqual(report["skipped_pinned_count"], 1)
            self.assertIn(pinned_rel, report["skipped_pinned"])
            self.assertTrue((artifacts / pinned_rel).exists())
            self.assertTrue((artifacts / older).exists())

    def test_idempotent_second_run_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp) / "docs/review/mvp_verification_pack/artifacts"
            archive_root = Path(tmp) / "docs/review/mvp_verification_pack/archive"

            older = "utf8_normalization_wave2_report.json"
            latest = "utf8_normalization_wave3_report.json"
            write_text(artifacts / older, '{"v":2}\n')
            write_text(artifacts / latest, '{"v":3}\n')

            family_map = {
                older: "utf8_normalization_waveN_report",
                latest: "utf8_normalization_waveN_report",
            }
            index_path = write_index_payload(
                artifact_root=artifacts,
                archive_root=archive_root,
                candidates=[older, latest],
                family_map=family_map,
            )

            first = run_archive_script(artifacts, archive_root, index_path, refresh_index=False)
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            first_report = load_report_json(artifacts)
            self.assertEqual(first_report["created_bundle_count"], 1)

            first_zip_count = len(list_sidecar_zips(archive_root))
            second = run_archive_script(artifacts, archive_root, index_path, refresh_index=False)
            self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
            second_report = load_report_json(artifacts)
            self.assertEqual(second_report["created_bundle_count"], 0)
            self.assertGreaterEqual(second_report["skipped_already_archived_count"], 1)
            second_zip_count = len(list_sidecar_zips(archive_root))
            self.assertEqual(first_zip_count, second_zip_count)


if __name__ == "__main__":
    unittest.main()
