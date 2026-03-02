from __future__ import annotations

import types
import unittest
from unittest import mock

from scripts import db_smoke_test


def make_args(**overrides):
    defaults = {
        "db_url": "",
        "host": "localhost",
        "port": 5432,
        "database": "aichatbot",
        "user": "aichatbot",
        "password": "pw",
        "method": "docker-exec",
        "docker_unavailable_policy": "skipped",
        "auto_up": False,
        "compose_file": "infra/docker-compose.yml",
        "compose_service": "postgres",
        "expected_tables": None,
        "output_txt": None,
        "output_json": None,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


class DbSmokeTestScriptTest(unittest.TestCase):
    def test_classify_docker_engine_down(self) -> None:
        raw = "failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine"
        self.assertEqual(db_smoke_test.classify_docker_failure(raw), db_smoke_test.REASON_DOCKER_ENGINE_DOWN)

    def test_classify_docker_permission(self) -> None:
        raw = "permission denied while trying to connect to the docker daemon socket"
        self.assertEqual(db_smoke_test.classify_docker_failure(raw), db_smoke_test.REASON_DOCKER_PERMISSION)

    def test_execute_returns_skipped_on_docker_preflight_failure_with_skipped_policy(self) -> None:
        args = make_args(docker_unavailable_policy="skipped")
        with mock.patch.object(
            db_smoke_test,
            "run_docker_preflight",
            return_value=(False, "failed to connect to the docker API"),
        ):
            payload = db_smoke_test.execute(args)

        self.assertEqual(payload["status"], db_smoke_test.STATUS_SKIPPED)
        self.assertEqual(payload["reason_code"], db_smoke_test.REASON_DOCKER_ENGINE_DOWN)
        self.assertEqual(payload["docker_preflight_status"], "FAIL")
        self.assertEqual(payload["violation_count"], 1)

    def test_execute_returns_fail_on_docker_preflight_failure_with_fail_policy(self) -> None:
        args = make_args(docker_unavailable_policy="fail")
        with mock.patch.object(
            db_smoke_test,
            "run_docker_preflight",
            return_value=(False, "failed to connect to the docker API"),
        ):
            payload = db_smoke_test.execute(args)

        self.assertEqual(payload["status"], db_smoke_test.STATUS_FAIL)
        self.assertEqual(payload["reason_code"], db_smoke_test.REASON_DOCKER_ENGINE_DOWN)
        self.assertEqual(payload["violation_count"], 1)


if __name__ == "__main__":
    unittest.main()
