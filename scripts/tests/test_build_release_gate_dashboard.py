from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_release_gate_dashboard.py"
FIXTURE_ROOT = REPO_ROOT / "scripts" / "tests" / "fixtures" / "release_dashboard" / "base" / "artifacts"


def run_script(artifacts_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python",
            str(SCRIPT_PATH),
            "--artifacts-dir",
            str(artifacts_dir),
            "--index-json",
            str(artifacts_dir / "_INDEX.json"),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def load_dashboard_json(artifacts_dir: Path) -> dict:
    return json.loads((artifacts_dir / "release_gate_dashboard.json").read_text(encoding="utf-8"))


class BuildReleaseGateDashboardTest(unittest.TestCase):
    def test_output_is_deterministic_and_contains_table_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "artifacts"
            shutil.copytree(FIXTURE_ROOT, artifacts_dir)

            first = run_script(artifacts_dir)
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            first_md = (artifacts_dir / "release_gate_dashboard.md").read_text(encoding="utf-8")
            first_json = (artifacts_dir / "release_gate_dashboard.json").read_text(encoding="utf-8")
            payload = json.loads(first_json)

            second = run_script(artifacts_dir)
            self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
            second_md = (artifacts_dir / "release_gate_dashboard.md").read_text(encoding="utf-8")
            second_json = (artifacts_dir / "release_gate_dashboard.json").read_text(encoding="utf-8")

            self.assertEqual(first_md, second_md)
            self.assertEqual(first_json, second_json)

            self.assertEqual(
                list(payload.keys()),
                ["metadata", "summary", "gates", "baseline_snapshot", "triage"],
            )
            self.assertTrue(payload["gates"])
            self.assertEqual(
                list(payload["gates"][0].keys()),
                [
                    "key",
                    "name",
                    "status",
                    "reason",
                    "evidence",
                    "primary_evidence",
                    "key_metric",
                    "parsed_fields",
                ],
            )

            self.assertIn("| Gate name | Status | Evidence path(s) | Key metric |", first_md)
            self.assertIn("[domain_layer_boundary_gate.json](domain_layer_boundary_gate.json)", first_md)

    def test_missing_gate_is_marked_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "artifacts"
            shutil.copytree(FIXTURE_ROOT, artifacts_dir)

            proc = run_script(artifacts_dir)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

            payload = load_dashboard_json(artifacts_dir)
            target = next(item for item in payload["gates"] if item["key"] == "db_backend_health_trace_gate")
            self.assertEqual(target["status"], "MISSING")
            self.assertEqual(target["reason"], "no evidence file found")


if __name__ == "__main__":
    unittest.main()
