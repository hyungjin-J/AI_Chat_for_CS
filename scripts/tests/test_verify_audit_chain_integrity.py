from __future__ import annotations

import base64
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_audit_chain_integrity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_audit_chain_integrity", SCRIPT_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("failed to load verify_audit_chain_integrity module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VerifyAuditChainIntegrityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_parse_utc_accepts_z_suffix(self) -> None:
        parsed = self.module.parse_utc("2026-03-01T00:00:00Z", "from_utc")
        self.assertEqual(parsed.year, 2026)
        self.assertEqual(parsed.month, 3)
        self.assertEqual(parsed.day, 1)
        self.assertEqual(self.module.format_utc(parsed), "2026-03-01T00:00:00Z")

    def test_compute_expected_hash_matches_java_payload_rule(self) -> None:
        row = self.module.ChainRow(
            audit_id="40000000-0000-4000-8000-000000000001",
            chain_seq=1,
            hash_prev="GENESIS",
            hash_curr="",
            trace_id="20000000-0000-4000-8000-000000000001",
            action_type="AUTH_LOGIN_SUCCESS",
            target_type="AUTH_SESSION",
            target_id="session-1",
            before_json=None,
            after_json='{"result":"ok"}',
            created_at_epoch_ms=1709287200000,
        )
        tenant_id = "10000000-0000-4000-8000-000000000001"
        payload = "|".join(
            [
                tenant_id,
                row.trace_id or "",
                row.action_type or "",
                row.target_type or "",
                row.target_id or "",
                "",
                row.after_json or "",
                "1",
                "GENESIS",
                "1709287200000",
            ]
        )
        expected = base64.b64encode(hashlib.sha256(payload.encode("utf-8")).digest()).decode("ascii")
        actual = self.module.compute_expected_hash(tenant_id=tenant_id, row=row)
        self.assertEqual(actual, expected)

    def test_verify_chain_detects_hash_curr_mismatch(self) -> None:
        tenant_id = "10000000-0000-4000-8000-000000000001"
        first = self.module.ChainRow(
            audit_id="a1",
            chain_seq=1,
            hash_prev="GENESIS",
            hash_curr="bogus-hash",
            trace_id="t1",
            action_type="A",
            target_type="B",
            target_id="C",
            before_json=None,
            after_json='{"ok":true}',
            created_at_epoch_ms=1709287200000,
        )
        failure_count, failures = self.module.verify_chain(tenant_id=tenant_id, rows=[first], sample_limit=20)
        self.assertGreater(failure_count, 0)
        self.assertTrue(any(item.startswith("hash_curr_mismatch:") for item in failures))

    def test_verify_chain_detects_seq_gap(self) -> None:
        tenant_id = "10000000-0000-4000-8000-000000000001"
        first = self.module.ChainRow(
            audit_id="a1",
            chain_seq=1,
            hash_prev="GENESIS",
            hash_curr="h1",
            trace_id="t1",
            action_type="A",
            target_type="B",
            target_id="C",
            before_json=None,
            after_json="{}",
            created_at_epoch_ms=1709287200000,
        )
        second = self.module.ChainRow(
            audit_id="a2",
            chain_seq=3,
            hash_prev="h1",
            hash_curr="h2",
            trace_id="t2",
            action_type="A",
            target_type="B",
            target_id="C",
            before_json=None,
            after_json="{}",
            created_at_epoch_ms=1709287201000,
        )
        failure_count, failures = self.module.verify_chain(tenant_id=tenant_id, rows=[first, second], sample_limit=20)
        self.assertGreater(failure_count, 0)
        self.assertTrue(any(item.startswith("chain_seq_gap:") for item in failures))

    def test_mask_command_redacts_passwords(self) -> None:
        masked = self.module.command_text(
            [
                "docker",
                "compose",
                "exec",
                "-e",
                "PGPASSWORD=secret",
                "postgres",
                "psql",
                "--db-password",
                "another-secret",
            ]
        )
        self.assertNotIn("secret", masked)
        self.assertIn("***REDACTED***", masked)


if __name__ == "__main__":
    unittest.main()
