from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "perf" / "assert_perf_gate.py"


def run_gate(result_file: Path, thresholds_file: Path, out_json: Path, out_txt: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python",
            str(SCRIPT),
            "--result",
            str(result_file),
            "--thresholds",
            str(thresholds_file),
            "--output-json",
            str(out_json),
            "--output-txt",
            str(out_txt),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def point(metric: str, value: float) -> str:
    return json.dumps(
        {
            "type": "Point",
            "data": {
                "metric": metric,
                "value": value,
            },
        },
        ensure_ascii=False,
    )


class AssertPerfGateTest(unittest.TestCase):
    def test_gate_passes_with_valid_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            result_file = tmp_dir / "result.json"
            thresholds_file = tmp_dir / "thresholds.yaml"
            out_json = tmp_dir / "gate.json"
            out_txt = tmp_dir / "gate.txt"

            result_file.write_text(
                "\n".join(
                    [
                        point("first_token_ms", 900),
                        point("first_token_ms", 1100),
                        point("first_token_ms", 1200),
                        point("first_token_ms", 1000),
                        point("first_token_ms", 1300),
                        point("sse_done_success_rate", 1),
                        point("sse_done_success_rate", 1),
                        point("sse_done_success_rate", 1),
                        point("sse_error_rate", 0),
                        point("sse_error_rate", 0),
                        point("sse_safe_response_rate", 0),
                        point("message_accepted_202_rate", 1),
                        point("rate_limit_429_rate", 1),
                        point("rate_limit_headers_ok_rate", 1),
                        point("rate_limit_contract_ok_rate", 1),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            thresholds_file.write_text(
                json.dumps(
                    {
                        "metrics": {
                            "first_token_ms": {"p95_max": 1500, "sample_count_min": 5},
                            "sse_done_success_rate": {"min": 0.95},
                            "sse_error_rate": {"max": 0.1},
                            "sse_safe_response_rate": {"max": 0.2},
                            "message_accepted_202_rate": {"min": 0.9},
                            "rate_limit_429_rate": {"min": 0.9},
                            "rate_limit_headers_ok_rate": {"min": 0.9},
                            "rate_limit_contract_ok_rate": {"min": 0.9},
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            completed = run_gate(result_file, thresholds_file, out_json, out_txt)
            self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["violation_count"], 0)

    def test_gate_fails_when_threshold_is_not_met(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            result_file = tmp_dir / "result.json"
            thresholds_file = tmp_dir / "thresholds.yaml"
            out_json = tmp_dir / "gate.json"
            out_txt = tmp_dir / "gate.txt"

            result_file.write_text(
                "\n".join(
                    [
                        point("first_token_ms", 2900),
                        point("first_token_ms", 3000),
                        point("first_token_ms", 3200),
                        point("first_token_ms", 3100),
                        point("first_token_ms", 3050),
                        point("sse_done_success_rate", 0),
                        point("sse_done_success_rate", 1),
                        point("sse_error_rate", 1),
                        point("sse_safe_response_rate", 1),
                        point("message_accepted_202_rate", 0),
                        point("rate_limit_429_rate", 0),
                        point("rate_limit_headers_ok_rate", 0),
                        point("rate_limit_contract_ok_rate", 0),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            thresholds_file.write_text(
                json.dumps(
                    {
                        "metrics": {
                            "first_token_ms": {"p95_max": 2000, "sample_count_min": 5},
                            "sse_done_success_rate": {"min": 0.95},
                            "sse_error_rate": {"max": 0.1},
                            "sse_safe_response_rate": {"max": 0.2},
                            "message_accepted_202_rate": {"min": 0.95},
                            "rate_limit_429_rate": {"min": 0.95},
                            "rate_limit_headers_ok_rate": {"min": 0.95},
                            "rate_limit_contract_ok_rate": {"min": 0.95},
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            completed = run_gate(result_file, thresholds_file, out_json, out_txt)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("status=FAIL", completed.stdout)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "FAIL")
            self.assertGreater(payload["violation_count"], 0)

    def test_gate_reads_perf_meta_reason_when_points_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            result_file = tmp_dir / "result.json"
            thresholds_file = tmp_dir / "thresholds.yaml"
            out_json = tmp_dir / "gate.json"
            out_txt = tmp_dir / "gate.txt"

            result_file.write_text(
                json.dumps(
                    {
                        "type": "PerfGateMeta",
                        "status": "FAIL",
                        "reason_code": "TARGET_UNREACHABLE",
                        "reason_detail": "health_status=503",
                        "remediation_hint": "start backend",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            thresholds_file.write_text(
                json.dumps({"metrics": {"first_token_ms": {"p95_max": 2000}}}, ensure_ascii=False),
                encoding="utf-8",
            )

            completed = run_gate(result_file, thresholds_file, out_json, out_txt)
            self.assertNotEqual(completed.returncode, 0)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(payload["reason_code"], "TARGET_UNREACHABLE")
            self.assertIn("health_status=503", payload["reason_detail"])

    def test_gate_sets_missing_file_reason_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            result_file = tmp_dir / "result.json"
            thresholds_file = tmp_dir / "thresholds.yaml"
            out_json = tmp_dir / "gate.json"
            out_txt = tmp_dir / "gate.txt"

            thresholds_file.write_text(
                json.dumps({"metrics": {"first_token_ms": {"p95_max": 2000}}}, ensure_ascii=False),
                encoding="utf-8",
            )
            completed = run_gate(result_file, thresholds_file, out_json, out_txt)
            self.assertNotEqual(completed.returncode, 0)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(payload["reason_code"], "RESULT_FILE_MISSING")


if __name__ == "__main__":
    unittest.main()
