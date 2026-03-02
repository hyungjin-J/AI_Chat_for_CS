from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "db_backup_restore_rehearsal.py"


def load_module():
    spec = importlib.util.spec_from_file_location("db_backup_restore_rehearsal", SCRIPT_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("failed to load db_backup_restore_rehearsal module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_success_runner(
    module,
    *,
    fail_migrate: bool = False,
    role_count: int = 5,
    seed_mode: str = "inserted",
    smoke_status: str = "PASS",
):
    seed_columns = [
        {
            "table_name": "tb_data_retention_policy",
            "column_name": "table_name",
            "data_type": "character varying",
            "is_nullable": "NO",
            "column_default": None,
            "ordinal_position": 1,
        },
        {
            "table_name": "tb_data_retention_policy",
            "column_name": "retention_days",
            "data_type": "integer",
            "is_nullable": "NO",
            "column_default": None,
            "ordinal_position": 2,
        },
        {
            "table_name": "tb_data_retention_policy",
            "column_name": "enabled",
            "data_type": "boolean",
            "is_nullable": "NO",
            "column_default": "true",
            "ordinal_position": 3,
        },
        {
            "table_name": "tb_data_retention_policy",
            "column_name": "updated_at",
            "data_type": "timestamp without time zone",
            "is_nullable": "NO",
            "column_default": "CURRENT_TIMESTAMP",
            "ordinal_position": 4,
        },
    ]

    def _run(command: list[str], cwd: Path | None = None):
        del cwd
        if "migrate" in command and "flyway" in command:
            if fail_migrate:
                return module.CommandResult(returncode=1, stdout="", stderr="flyway migrate failed")
            return module.CommandResult(returncode=0, stdout="migrate ok", stderr="")

        if "validate" in command and "flyway" in command:
            return module.CommandResult(returncode=0, stdout="validate ok", stderr="")

        if "cp" in command and any(
            value.endswith(f":{module.DUMP_CONTAINER_PATH}") for value in command
        ):
            local_path = Path(command[-1])
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(b"fake-dump-content")
            return module.CommandResult(returncode=0, stdout="", stderr="")

        if any(part.endswith("db_smoke_test.py") for part in command):
            json_path = Path(command[command.index("--output-json") + 1])
            txt_path = Path(command[command.index("--output-txt") + 1])
            json_path.parent.mkdir(parents=True, exist_ok=True)
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps({"status": smoke_status, "violation_count": 0, "violations": []}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            txt_path.write_text(f"db_smoke_test\nstatus={smoke_status}\n", encoding="utf-8")
            return module.CommandResult(returncode=0, stdout="db smoke pass", stderr="")

        if "psql" in command:
            sql = command[-1]
            if "information_schema.columns AS c" in sql:
                if seed_mode == "fallback":
                    return module.CommandResult(returncode=0, stdout="[]\n", stderr="")
                return module.CommandResult(returncode=0, stdout=json.dumps(seed_columns, ensure_ascii=False) + "\n", stderr="")
            if "constraint_type = 'FOREIGN KEY'" in sql:
                return module.CommandResult(returncode=0, stdout="[]\n", stderr="")
            if sql.startswith('INSERT INTO "tb_data_retention_policy"'):
                return module.CommandResult(returncode=0, stdout="", stderr="")
            if 'FROM "tb_data_retention_policy"' in sql and "rehearsal_" in sql:
                return module.CommandResult(returncode=0, stdout="1\n", stderr="")
            if "SELECT COUNT(*) FROM flyway_schema_history;" in sql:
                return module.CommandResult(returncode=0, stdout="11\n", stderr="")
            if "extname = 'vector'" in sql:
                return module.CommandResult(returncode=0, stdout="1\n", stderr="")
            if "FROM information_schema.tables" in sql and "table_name IN (" in sql:
                return module.CommandResult(returncode=0, stdout="5\n", stderr="")
            if "tenant_key = 'demo-tenant'" in sql:
                return module.CommandResult(returncode=0, stdout="1\n", stderr="")
            if "COUNT(DISTINCT role_code)" in sql:
                return module.CommandResult(returncode=0, stdout=f"{role_count}\n", stderr="")
            if "login_id IN ('agent1','admin1','ops1')" in sql:
                return module.CommandResult(returncode=0, stdout="3\n", stderr="")
            if "FROM tb_kb_chunk_embedding" in sql:
                return module.CommandResult(returncode=0, stdout="2\n", stderr="")
            if "flyway_schema_history WHERE success = false" in sql:
                return module.CommandResult(returncode=0, stdout="0\n", stderr="")
            if "pg_indexes" in sql:
                return module.CommandResult(returncode=0, stdout="1\n", stderr="")
            return module.CommandResult(returncode=0, stdout="1\n", stderr="")

        return module.CommandResult(returncode=0, stdout="", stderr="")

    return _run


class DbBackupRestoreRehearsalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def run_main_with_runner(self, runner, extra_args: list[str] | None = None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "artifacts"
            dump_dir = root / "dump"
            compose_file = root / "compose.yml"
            compose_file.write_text("services:\n  postgres: {}\n", encoding="utf-8")
            args = [
                "--compose-file",
                str(compose_file),
                "--artifact-dir",
                str(artifacts),
                "--artifact-date",
                "20260225",
                "--dump-dir",
                str(dump_dir),
            ]
            if extra_args:
                args.extend(extra_args)

            with mock.patch.object(self.module, "run_command", side_effect=runner):
                exit_code = self.module.main(args)

            json_path = artifacts / "db_backup_restore_rehearsal_20260225.json"
            txt_path = artifacts / "db_backup_restore_rehearsal_20260225.txt"
            txt_exists = txt_path.exists()
            json_exists = json_path.exists()
            txt_content = txt_path.read_text(encoding="utf-8") if txt_exists else ""
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            return {
                "exit_code": exit_code,
                "txt_path": txt_path,
                "json_path": json_path,
                "txt_exists": txt_exists,
                "json_exists": json_exists,
                "txt_content": txt_content,
                "payload": payload,
            }

    def test_pass_path_generates_artifacts(self) -> None:
        result = self.run_main_with_runner(make_success_runner(self.module))
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["txt_exists"])
        self.assertTrue(result["json_exists"])
        payload = result["payload"]
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["violation_count"], 0)
        self.assertEqual(payload["rto_minutes"], 60)
        self.assertEqual(payload["rpo_hours"], 24)
        self.assertEqual(payload["seed_strategy"], "inserted")
        self.assertEqual(payload["seed_table"], "tb_data_retention_policy")
        self.assertEqual(payload["seed_inserted_row_count"], 1)
        self.assertTrue(payload["dump_size_bytes"] > 0)
        self.assertTrue(payload["dump_created_at_utc"].endswith("Z"))
        self.assertIn("rto_minutes=60", result["txt_content"])
        self.assertIn("rpo_hours=24", result["txt_content"])

    def test_fallback_seed_strategy_when_no_safe_target(self) -> None:
        result = self.run_main_with_runner(make_success_runner(self.module, seed_mode="fallback"))
        self.assertEqual(result["exit_code"], 0)
        payload = result["payload"]
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["seed_strategy"], "fallback")
        self.assertIsNone(payload["seed_table"])
        self.assertEqual(payload["seed_inserted_row_count"], 0)
        self.assertIn("no safe insert target", payload["fallback_reason"])
        self.assertEqual(payload["checks"]["safe_seed_fallback"]["status"], "PASS")

    def test_fail_when_flyway_migrate_fails(self) -> None:
        result = self.run_main_with_runner(make_success_runner(self.module, fail_migrate=True))
        self.assertNotEqual(result["exit_code"], 0)
        self.assertTrue(result["txt_exists"])
        self.assertTrue(result["json_exists"])
        payload = result["payload"]
        self.assertEqual(payload["status"], "FAIL")
        self.assertTrue(any(v["code"] == "FLYWAY_MIGRATE_FAILED" for v in payload["violations"]))

    def test_fail_when_core_query_mismatch(self) -> None:
        result = self.run_main_with_runner(make_success_runner(self.module, role_count=4))
        self.assertNotEqual(result["exit_code"], 0)
        payload = result["payload"]
        self.assertEqual(payload["status"], "FAIL")
        self.assertTrue(any(v["code"] == "CORE_QUERY_FAILED" for v in payload["violations"]))
        self.assertEqual(payload["checks"]["role_taxonomy_exists"]["status"], "FAIL")

    def test_fail_when_smoke_reports_non_pass(self) -> None:
        result = self.run_main_with_runner(make_success_runner(self.module, smoke_status="FAIL"))
        self.assertNotEqual(result["exit_code"], 0)
        payload = result["payload"]
        self.assertEqual(payload["status"], "FAIL")
        self.assertTrue(any(v["code"] == "DB_SMOKE_FAILED" for v in payload["violations"]))
        self.assertEqual(payload["checks"]["db_smoke_after_restore_exec"]["status"], "PASS")

    def test_default_output_filename_rule(self) -> None:
        result = self.run_main_with_runner(make_success_runner(self.module))
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["txt_path"].name, "db_backup_restore_rehearsal_20260225.txt")
        self.assertEqual(result["json_path"].name, "db_backup_restore_rehearsal_20260225.json")

    def test_dump_removed_when_keep_dump_false(self) -> None:
        result = self.run_main_with_runner(make_success_runner(self.module))
        self.assertEqual(result["exit_code"], 0)
        payload = result["payload"]
        dump_path = Path(payload["dump_path"])
        self.assertFalse(dump_path.exists())

    def test_command_and_text_masking(self) -> None:
        masked_command = self.module.command_str(
            [
                "docker",
                "compose",
                "exec",
                "-e",
                "PGPASSWORD=super-secret",
                "postgres",
                "psql",
                "--password",
                "abcd",
                "--db-password",
                "efgh",
            ]
        )
        self.assertNotIn("super-secret", masked_command)
        self.assertNotIn("abcd", masked_command)
        self.assertNotIn("efgh", masked_command)
        self.assertIn("***REDACTED***", masked_command)

        masked_text = self.module.mask_sensitive_text(
            "PGPASSWORD=super-secret token=my-token --password abc"
        )
        self.assertNotIn("super-secret", masked_text)
        self.assertNotIn("my-token", masked_text)
        self.assertNotIn(" abc", masked_text)


if __name__ == "__main__":
    unittest.main()
