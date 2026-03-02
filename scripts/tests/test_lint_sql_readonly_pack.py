from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "lint_sql_readonly_pack.py"


def run_script(sql_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(SCRIPT_PATH), "--sql-file", str(sql_file)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class LintSqlReadonlyPackTest(unittest.TestCase):
    def test_pass_for_safe_select_only_sql(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sql_file = Path(tmp) / "safe.sql"
            sql_file.write_text(
                "-- DROP in comment should be ignored\n"
                "SELECT current_database();\n"
                "SELECT 'DELETE in string literal should be ignored';\n",
                encoding="utf-8",
            )

            proc = run_script(sql_file)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("violation_count=0", proc.stdout)

    def test_fail_for_destructive_keyword(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sql_file = Path(tmp) / "unsafe.sql"
            sql_file.write_text(
                "SELECT 1;\n"
                "DROP TABLE tb_message;\n",
                encoding="utf-8",
            )

            proc = run_script(sql_file)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("READONLY_SQL_FORBIDDEN_KEYWORD", proc.stdout)
            self.assertIn("keyword=DROP", proc.stdout)

    def test_pass_for_canonical_ops_pack(self) -> None:
        sql_file = REPO_ROOT / "docs/ops/sql/DB_OPERATIONS_QUERIES.sql"
        proc = run_script(sql_file)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("status=PASS", proc.stdout)


if __name__ == "__main__":
    unittest.main()
