from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "vector_recall_latency_bench.py"


def load_module():
    spec = importlib.util.spec_from_file_location("vector_recall_latency_bench", SCRIPT_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("failed to load vector_recall_latency_bench module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def extract_probe(sql: str) -> int:
    match = re.search(r"SET LOCAL ivfflat\.probes = (\d+)", sql)
    if not match:
        raise AssertionError(f"probe not found in sql: {sql}")
    return int(match.group(1))


def extract_query_id(sql: str) -> str:
    match = re.search(r"AND id = '([^']+)'", sql)
    if not match:
        raise AssertionError(f"query id not found in sql: {sql}")
    return match.group(1)


def make_runner(
    module,
    *,
    row_count: int = 20,
    sample_ids: tuple[str, ...] = ("q1", "q2"),
    exact: dict[str, str] | None = None,
    approx: dict[tuple[int, str], tuple[str, float]] | None = None,
):
    exact_map = exact or {"q1": "a,b", "q2": "c,d"}
    approx_map = approx or {
        (1, "q1"): ("a,b", 10.0),
        (1, "q2"): ("c,d", 12.0),
        (2, "q1"): ("a,b", 11.0),
        (2, "q2"): ("c,x", 13.0),
    }

    def _run(command: list[str], env: dict[str, str] | None = None):
        del env
        sql = command[-1]
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT COUNT(*) FROM tb_kb_chunk_embedding e JOIN tb_kb_chunk c"):
            return module.CommandResult(returncode=0, stdout=f"{row_count}\n", stderr="")

        if "ORDER BY md5(e.id::text ||" in sql:
            return module.CommandResult(returncode=0, stdout="\n".join(sample_ids) + "\n", stderr="")

        if "SET LOCAL enable_indexscan = off" in sql:
            query_id = extract_query_id(sql)
            value = exact_map.get(query_id, "")
            return module.CommandResult(returncode=0, stdout=f"{value}\n", stderr="")

        if "SET LOCAL ivfflat.probes =" in sql:
            probe = extract_probe(sql)
            query_id = extract_query_id(sql)
            value, latency = approx_map[(probe, query_id)]
            return module.CommandResult(returncode=0, stdout=f"{value}\t{latency}\n", stderr="")

        return module.CommandResult(returncode=0, stdout="", stderr="")

    return _run


class VectorRecallLatencyBenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def run_main_with_runner(
        self,
        runner,
        *,
        extra_args: list[str] | None = None,
        baseline_payload: dict | None = None,
    ) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "artifacts"
            compose_file = root / "compose.yml"
            compose_file.write_text("services:\n  postgres: {}\n", encoding="utf-8")
            args = [
                "--compose-file",
                str(compose_file),
                "--artifact-dir",
                str(artifacts),
                "--artifact-date",
                "20260226",
                "--query-count",
                "2",
                "--top-k",
                "2",
                "--probe-values",
                "1,2",
            ]
            if baseline_payload is not None:
                baseline_path = root / "baseline.json"
                baseline_path.write_text(json.dumps(baseline_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                args.extend(["--baseline-json", str(baseline_path)])
            if extra_args:
                args.extend(extra_args)

            with mock.patch.object(self.module, "run_command", side_effect=runner):
                exit_code = self.module.main(args)

            txt_path = artifacts / "vector_recall_latency_bench_20260226.txt"
            json_path = artifacts / "vector_recall_latency_bench_20260226.json"
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            return {
                "exit_code": exit_code,
                "txt_path": txt_path,
                "json_path": json_path,
                "txt_content": txt_path.read_text(encoding="utf-8"),
                "payload": payload,
            }

    def test_pass_path_with_baseline_delta(self) -> None:
        baseline = {
            "probe_results": [
                {"probe": 1, "recall_at_k": 1.0, "p95_ms": 14.0},
                {"probe": 2, "recall_at_k": 0.75, "p95_ms": 16.0},
            ],
            "best_probe": {"probe": 1, "recall_at_k": 1.0, "p95_ms": 14.0},
        }
        result = self.run_main_with_runner(make_runner(self.module), baseline_payload=baseline)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("status=PASS", result["txt_content"])
        payload = result["payload"]
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["violation_count"], 0)
        self.assertEqual(payload["best_probe"]["probe"], 1)

    def test_fail_when_recall_drop_exceeds_threshold(self) -> None:
        baseline = {
            "probe_results": [{"probe": 1, "recall_at_k": 1.0, "p95_ms": 12.0}],
            "best_probe": {"probe": 1, "recall_at_k": 1.0, "p95_ms": 12.0},
        }
        approx = {
            (1, "q1"): ("x,y", 9.0),
            (1, "q2"): ("z,w", 11.0),
            (2, "q1"): ("x,y", 10.0),
            (2, "q2"): ("z,w", 12.0),
        }
        result = self.run_main_with_runner(
            make_runner(self.module, approx=approx),
            baseline_payload=baseline,
        )
        self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(result["payload"]["status"], "FAIL")
        self.assertTrue(any(v["code"] == "BENCH_RECALL_REGRESSION" for v in result["payload"]["violations"]))

    def test_fail_when_p95_regression_exceeds_threshold(self) -> None:
        baseline = {
            "probe_results": [{"probe": 1, "recall_at_k": 1.0, "p95_ms": 10.0}],
            "best_probe": {"probe": 1, "recall_at_k": 1.0, "p95_ms": 10.0},
        }
        approx = {
            (1, "q1"): ("a,b", 21.0),
            (1, "q2"): ("c,d", 24.0),
            (2, "q1"): ("a,b", 22.0),
            (2, "q2"): ("c,x", 23.0),
        }
        result = self.run_main_with_runner(
            make_runner(self.module, approx=approx),
            baseline_payload=baseline,
        )
        self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(result["payload"]["status"], "FAIL")
        self.assertTrue(any(v["code"] == "BENCH_LATENCY_REGRESSION" for v in result["payload"]["violations"]))

    def test_fail_when_data_is_insufficient(self) -> None:
        result = self.run_main_with_runner(make_runner(self.module, row_count=1))
        self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(result["payload"]["status"], "FAIL")
        self.assertTrue(any(v["code"] == "BENCH_DATA_INSUFFICIENT" for v in result["payload"]["violations"]))

    def test_default_output_filename_rule(self) -> None:
        result = self.run_main_with_runner(make_runner(self.module))
        self.assertEqual(result["txt_path"].name, "vector_recall_latency_bench_20260226.txt")
        self.assertEqual(result["json_path"].name, "vector_recall_latency_bench_20260226.json")

    def test_invalid_probe_value_raises_system_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            compose_file = Path(tmp) / "compose.yml"
            compose_file.write_text("services:\n  postgres: {}\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                self.module.main(
                    [
                        "--compose-file",
                        str(compose_file),
                        "--probe-values",
                        "1,abc",
                    ]
                )

    def test_ci_mode_applies_bounded_defaults(self) -> None:
        args = self.module.parse_args(["--ci"])
        self.assertTrue(args.ci)
        self.assertEqual(args.top_k, self.module.DEFAULT_CI_TOP_K)
        self.assertEqual(args.query_count, self.module.DEFAULT_CI_QUERY_COUNT)
        self.assertEqual(args.probe_values, list(self.module.DEFAULT_CI_PROBES))
        self.assertEqual(args.seed, self.module.DEFAULT_CI_SEED)

    def test_ci_mode_respects_explicit_overrides(self) -> None:
        args = self.module.parse_args(
            [
                "--ci",
                "--top-k",
                "5",
                "--query-count",
                "7",
                "--probe-values",
                "2,4",
                "--seed",
                "99",
            ]
        )
        self.assertEqual(args.top_k, 5)
        self.assertEqual(args.query_count, 7)
        self.assertEqual(args.probe_values, [2, 4])
        self.assertEqual(args.seed, 99)

    def test_main_writes_fail_artifacts_on_unhandled_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "artifacts"
            compose_file = root / "compose.yml"
            compose_file.write_text("services:\n  postgres: {}\n", encoding="utf-8")

            with mock.patch.object(
                self.module,
                "run_benchmark",
                side_effect=RuntimeError("boom local-dev-only-password"),
            ):
                exit_code = self.module.main(
                    [
                        "--compose-file",
                        str(compose_file),
                        "--artifact-dir",
                        str(artifacts),
                        "--artifact-date",
                        "20260226",
                    ]
                )

            self.assertNotEqual(exit_code, 0)
            txt_path = artifacts / "vector_recall_latency_bench_20260226.txt"
            json_path = artifacts / "vector_recall_latency_bench_20260226.json"
            self.assertTrue(txt_path.exists())
            self.assertTrue(json_path.exists())

            txt_content = txt_path.read_text(encoding="utf-8")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("status=FAIL", txt_content)
            self.assertNotIn("local-dev-only-password", txt_content)
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(payload["violation_count"], 1)
            self.assertEqual(payload["violations"][0]["code"], "BENCH_UNHANDLED_EXCEPTION")
            self.assertNotIn("local-dev-only-password", payload["violations"][0]["details"])


if __name__ == "__main__":
    unittest.main()
