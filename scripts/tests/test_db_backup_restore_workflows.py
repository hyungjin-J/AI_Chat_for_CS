from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WEEKLY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "db-backup-restore-weekly.yml"
NIGHTLY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "db-backup-restore-nightly.yml"


class DbBackupRestoreWorkflowTest(unittest.TestCase):
    def test_weekly_workflow_contract(self) -> None:
        self.assertTrue(WEEKLY_WORKFLOW.exists(), "weekly workflow file is missing")
        content = WEEKLY_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: db-backup-restore-weekly", content)
        self.assertIn("cron: \"0 17 * * 0\"", content)
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("python scripts/db_backup_restore_rehearsal.py", content)
        self.assertIn("db_backup_restore_rehearsal_*.txt", content)
        self.assertIn("db_backup_restore_rehearsal_*.json", content)
        self.assertNotIn(".dump", content)

    def test_nightly_is_dispatch_only(self) -> None:
        self.assertTrue(NIGHTLY_WORKFLOW.exists(), "nightly workflow file is missing")
        content = NIGHTLY_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: db-backup-restore-nightly", content)
        self.assertIn("workflow_dispatch:", content)
        self.assertNotIn("schedule:", content)


if __name__ == "__main__":
    unittest.main()
