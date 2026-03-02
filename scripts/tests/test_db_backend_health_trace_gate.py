from __future__ import annotations

import types
import unittest
from unittest import mock

from scripts import db_backend_health_trace_gate


def make_args(**overrides):
    defaults = {
        "endpoint": "http://localhost:8080/actuator/health",
        "trace_header": "X-Trace-Id",
        "trace_id": "11111111-1111-1111-1111-111111111111",
        "without_trace_expected": 409,
        "with_trace_expected": 200,
        "readiness_timeout_sec": 0,
        "poll_interval_sec": 0.2,
        "http_timeout_sec": 1.0,
        "docker_preflight": False,
        "docker_unavailable_policy": "fail",
        "output_txt": None,
        "output_json": None,
        "without_trace_raw": None,
        "with_trace_raw": None,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


class DbBackendHealthTraceGateScriptTest(unittest.TestCase):
    def test_classify_docker_engine_down(self) -> None:
        raw = "failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine"
        self.assertEqual(
            db_backend_health_trace_gate.classify_docker_failure(raw),
            db_backend_health_trace_gate.REASON_DOCKER_ENGINE_DOWN,
        )

    def test_classify_docker_permission(self) -> None:
        raw = "permission denied while trying to connect to the docker daemon socket"
        self.assertEqual(
            db_backend_health_trace_gate.classify_docker_failure(raw),
            db_backend_health_trace_gate.REASON_DOCKER_PERMISSION,
        )

    def test_execute_returns_skipped_on_docker_preflight_failure(self) -> None:
        args = make_args(docker_preflight=True, docker_unavailable_policy="skipped")
        with mock.patch.object(
            db_backend_health_trace_gate,
            "run_docker_preflight",
            return_value=(False, "failed to connect to the docker API"),
        ):
            payload, _, _ = db_backend_health_trace_gate.execute(args)

        self.assertEqual(payload["status"], db_backend_health_trace_gate.STATUS_SKIPPED)
        self.assertEqual(payload["reason_code"], db_backend_health_trace_gate.REASON_DOCKER_ENGINE_DOWN)
        self.assertEqual(payload["docker_preflight_status"], "FAIL")
        self.assertEqual(payload["violation_count"], 1)

    def test_execute_contract_fail_when_endpoint_unreachable(self) -> None:
        args = make_args()
        with mock.patch.object(
            db_backend_health_trace_gate,
            "wait_with_trace_status",
            return_value=(
                db_backend_health_trace_gate.ProbeResult(
                    status_code=None,
                    error="connection refused",
                    raw_response="connection refused",
                ),
                2,
            ),
        ):
            with mock.patch.object(
                db_backend_health_trace_gate,
                "probe_endpoint",
                return_value=db_backend_health_trace_gate.ProbeResult(
                    status_code=None,
                    error="connection refused",
                    raw_response="connection refused",
                ),
            ):
                payload, _, _ = db_backend_health_trace_gate.execute(args)

        self.assertEqual(payload["status"], db_backend_health_trace_gate.STATUS_FAIL)
        self.assertEqual(payload["reason_code"], db_backend_health_trace_gate.REASON_TARGET_UNREACHABLE)
        self.assertGreaterEqual(payload["violation_count"], 1)


if __name__ == "__main__":
    unittest.main()
