from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_ops_trend_report.py"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_script(artifacts_dir: Path, limit: int = 5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python",
            str(SCRIPT_PATH),
            "--artifacts-dir",
            str(artifacts_dir),
            "--limit",
            str(limit),
            "--output-txt",
            str(artifacts_dir / "ops_trend_report.txt"),
            "--output-json",
            str(artifacts_dir / "ops_trend_report.json"),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def load_report(artifacts_dir: Path) -> dict:
    return json.loads((artifacts_dir / "ops_trend_report.json").read_text(encoding="utf-8"))


class BuildOpsTrendReportTest(unittest.TestCase):
    def test_report_is_deterministic_and_ignores_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "artifacts"
            write_json(
                artifacts_dir / "db_backup_restore_rehearsal_20260201.json",
                {
                    "status": "FAIL",
                    "violations": [{"code": "COMPOSE_DOWN_SOURCE_FAILED"}],
                    "rto_minutes": 15,
                    "rpo_hours": 24,
                },
            )
            write_json(
                artifacts_dir / "db_backup_restore_rehearsal_20260101.json",
                {
                    "status": "PASS",
                    "rto_minutes": 12,
                    "rpo_hours": 24,
                },
            )
            write_json(
                artifacts_dir / "db_local_readiness_smoke_20260202.json",
                {
                    "status": "PASS",
                    "violation_count": 0,
                },
            )
            write_json(
                artifacts_dir / "vector_recall_latency_bench_20260203.json",
                {
                    "status": "PASS",
                    "p95_latency_ms": 180.5,
                },
            )

            first = run_script(artifacts_dir)
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            first_txt = (artifacts_dir / "ops_trend_report.txt").read_text(encoding="utf-8")
            first_json = (artifacts_dir / "ops_trend_report.json").read_text(encoding="utf-8")

            now = time.time()
            for offset, file_path in enumerate(sorted(artifacts_dir.glob("*.json"))):
                os.utime(file_path, (now + offset, now + offset))

            second = run_script(artifacts_dir)
            self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
            second_txt = (artifacts_dir / "ops_trend_report.txt").read_text(encoding="utf-8")
            second_json = (artifacts_dir / "ops_trend_report.json").read_text(encoding="utf-8")

            self.assertEqual(first_txt, second_txt)
            self.assertEqual(first_json, second_json)

    def test_missing_family_does_not_crash_and_is_marked_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "artifacts"
            write_json(
                artifacts_dir / "db_backup_restore_rehearsal_20260201.json",
                {"status": "PASS", "violation_count": 0},
            )
            write_json(
                artifacts_dir / "db_local_readiness_smoke_20260202.json",
                {"status": "PASS", "violation_count": 0},
            )

            proc = run_script(artifacts_dir)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            payload = load_report(artifacts_dir)

            vector_family = next(item for item in payload["families"] if item["key"] == "vector_bench_monitoring")
            self.assertEqual(vector_family["status"], "MISSING")
            self.assertEqual(vector_family["selected_count"], 0)

    def test_histogram_and_slo_fields_are_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "artifacts"
            write_json(
                artifacts_dir / "db_backup_restore_rehearsal_20260210.json",
                {
                    "status": "FAIL",
                    "violations": [
                        {"code": "COMPOSE_DOWN_SOURCE_FAILED"},
                        {"code": "COMPOSE_DOWN_SOURCE_FAILED"},
                        {"code": "COMPOSE_DOWN_FINAL_FAILED"},
                    ],
                    "rto_minutes": 11,
                    "rpo_hours": 24,
                },
            )
            write_json(
                artifacts_dir / "db_local_readiness_smoke_20260211.json",
                {"status": "PASS", "violation_count": 0},
            )
            write_json(
                artifacts_dir / "db_backend_health_trace_gate_20260212.json",
                {
                    "status": "FAIL",
                    "violations": [{"code": "HEALTH_TRACE_CONTRACT"}],
                },
            )
            write_json(
                artifacts_dir / "vector_recall_latency_bench_20260213.json",
                {"status": "PASS", "p95_latency_ms": 199.4},
            )
            write_json(
                artifacts_dir / "vector_bench_monitoring_20260214.json",
                {"status": "PASS", "latency_p95_ms": 201.1},
            )

            proc = run_script(artifacts_dir, limit=5)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            payload = load_report(artifacts_dir)

            backup = next(item for item in payload["families"] if item["key"] == "db_backup_restore_rehearsal")
            self.assertEqual(backup["failure_code_histogram"]["COMPOSE_DOWN_SOURCE_FAILED"], 2)
            self.assertEqual(backup["failure_code_histogram"]["COMPOSE_DOWN_FINAL_FAILED"], 1)
            self.assertEqual(backup["slo"]["rto_minutes"]["latest"], 11.0)
            self.assertEqual(backup["slo"]["rpo_hours"]["latest"], 24.0)

            vector = next(item for item in payload["families"] if item["key"] == "vector_bench_monitoring")
            self.assertEqual(vector["selected_count"], 2)
            self.assertEqual(vector["slo"]["p95_latency_ms"]["count"], 2)
            self.assertEqual(vector["slo"]["p95_latency_ms"]["max"], 201.1)


if __name__ == "__main__":
    unittest.main()
