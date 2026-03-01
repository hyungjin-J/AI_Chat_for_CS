from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "vector-bench-nightly.yml"


class VectorBenchWorkflowTest(unittest.TestCase):
    def test_workflow_contract(self) -> None:
        self.assertTrue(WORKFLOW.exists(), "vector benchmark workflow file is missing")
        content = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: vector-bench-nightly", content)
        self.assertIn("schedule:", content)
        self.assertIn("cron: \"0 18 * * *\"", content)
        self.assertIn("workflow_dispatch:", content)
        self.assertNotIn("pull_request:", content)
        self.assertNotIn("pull_request_target:", content)
        self.assertNotIn("\npush:", content)

        self.assertIn("docker compose -f \"${env:COMPOSE_FILE}\" down -v", content)
        self.assertIn("docker compose -f \"${env:COMPOSE_FILE}\" up -d postgres redis", content)
        self.assertIn("--profile db-tools run --rm flyway", content)
        self.assertIn("python scripts/db_smoke_test.py", content)

        self.assertIn("python scripts/vector_recall_latency_bench.py", content)
        self.assertIn("--ci-row-count\", \"3000\"", content)
        self.assertIn("--probe-values\", \"1,2,4,8\"", content)
        self.assertIn("VECTOR_BENCH_MAX_RECALL_DROP: \"0.03\"", content)
        self.assertIn("VECTOR_BENCH_MAX_P95_REGRESSION_RATIO: \"1.30\"", content)
        self.assertIn("BENCH_TXT_PATH", content)
        self.assertIn("BENCH_JSON_PATH", content)
        self.assertIn("BENCH_WORKFLOW_EXECUTION_FAILED", content)

        self.assertIn("Build vector bench monitoring gate artifact", content)
        self.assertIn("vector_bench_monitoring_gate.txt", content)
        self.assertIn("vector_bench_monitoring_gate.json", content)
        self.assertIn("benchmark_exit_code", content)
        self.assertIn("baseline_json_path", content)
        self.assertIn("max_recall_drop", content)
        self.assertIn("max_p95_regression_ratio", content)

        self.assertIn("Upload vector benchmark artifacts", content)
        self.assertIn("if: always()", content)
        self.assertIn("vector_recall_latency_bench_*.txt", content)
        self.assertIn("vector_recall_latency_bench_*.json", content)


if __name__ == "__main__":
    unittest.main()
