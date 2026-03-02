from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "e2e" / "api_smoke" / "run_e2e_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_e2e_smoke_module", SCRIPT_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("failed to load run_e2e_smoke module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class E2eApiSmokeRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def test_probe_base_url_reachable_unreachable(self) -> None:
        with mock.patch.object(
            self.mod.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            reachable, detail = self.mod.probe_base_url_reachable("http://localhost:8080", timeout_sec=1)
        self.assertFalse(reachable)
        self.assertIsNone(detail["http_status"])
        self.assertIn("connection refused", detail["error"])

    def test_build_output_paths_supports_out_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(
                artifact_dir=tmp,
                output_report_json="",
                output_trace_txt="",
                out=str(Path(tmp) / "custom_report.json"),
                trace_out=str(Path(tmp) / "custom_trace.txt"),
            )
            report_path, trace_path = self.mod.build_output_paths(args)
            self.assertEqual(report_path.name, "custom_report.json")
            self.assertEqual(trace_path.name, "custom_trace.txt")

    def test_s1_required_events_match_contract(self) -> None:
        self.assertEqual(set(self.mod.S1_REQUIRED_EVENTS), {"token", "citation", "done"})


if __name__ == "__main__":
    unittest.main()
