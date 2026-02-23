from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "spec_consistency_check.py"

KOR_REQ_ID = "\uc694\uad6c\uc0ac\ud56dID"      # 요구사항ID
KOR_API_LIST = "\uc804\uccb4API\ubaa9\ub85d"   # 전체API목록
KOR_NOTE = "\ube44\uace0"                      # 비고


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file_pointer:
        writer = csv.writer(file_pointer)
        writer.writerow(headers)
        writer.writerows(rows)


def write_api_workbook(path: Path, note_rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = KOR_API_LIST
    headers = [
        "number",
        "category",
        "program_id",
        "api_name",
        "method",
        "endpoint",
        "auth",
        "request",
        "response",
        "ROLE",
        KOR_NOTE,
    ]
    worksheet.append(headers)

    roles = ["AGENT", "CUSTOMER", "ADMIN", "OPS", "SYSTEM"]
    for index, role in enumerate(roles, start=1):
        note = note_rows[index - 1] if index - 1 < len(note_rows) else ""
        worksheet.append(
            [
                str(index),
                "AUTH",
                f"API-{index:03d}",
                f"Test API {index}",
                "GET",
                f"/v1/test/{index}",
                "Bearer",
                "{}",
                "{}",
                role,
                note,
            ]
        )
    workbook.save(path)


def write_uiux_workbook(path: Path, token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "91_traceability"
    worksheet["A1"] = token
    workbook.save(path)


def write_db_workbook(path: Path, token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "TABLES"
    worksheet["A1"] = token
    workbook.save(path)


class SpecConsistencyCheckTest(unittest.TestCase):
    def run_script(
        self,
        root: Path,
        requirements: Path,
        summary: Path,
        development: Path,
        api_workbook: Path,
        db_workbook: Path,
        uiux_workbook: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--root",
                str(root),
                "--requirements",
                str(requirements),
                "--summary",
                str(summary),
                "--development",
                str(development),
                "--api-workbook",
                str(api_workbook),
                "--db-workbook",
                str(db_workbook),
                "--uiux-workbook",
                str(uiux_workbook),
                "--report-json",
                str(root / "report.json"),
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def create_base_fixture(self, root: Path) -> dict[str, Path]:
        requirements = root / "docs/references/CS AI Chatbot_Requirements Statement.csv"
        summary = root / "docs/references/Summary of key features.csv"
        development = root / "docs/references/Development environment.csv"
        api_workbook = root / "docs/references/google_ready_api_spec_v0.3_20260216.xlsx"
        db_workbook = root / "docs/references/CS_AI_CHATBOT_DB.xlsx"
        uiux_workbook = root / "docs/uiux/CS_RAG_UI_UX_\uc124\uacc4\uc11c.xlsx"

        write_csv(
            requirements,
            ["ReqID", "description"],
            [
                ["AI-001", "secret_ref token tool citation done error heartbeat safe_response"],
                ["SEC-001", "ROLE AGENT CUSTOMER ADMIN OPS SYSTEM"],
            ],
        )
        write_csv(
            summary,
            ["feature", KOR_REQ_ID],
            [
                ["A", "AI-001"],
                ["B", "SEC-001"],
            ],
        )
        write_csv(
            development,
            ["name", "description"],
            [["dev", "ReqID: AI-001, SEC-001"]],
        )
        write_api_workbook(
            api_workbook,
            [
                "ReqID: AI-001",
                "ReqID+: SEC-001",
                "secret_ref",
                "token tool citation done error heartbeat safe_response",
                "ReqID: AI-001",
            ],
        )
        write_uiux_workbook(uiux_workbook, "AI-001")
        write_db_workbook(db_workbook, "SEC-001")

        return {
            "requirements": requirements,
            "summary": summary,
            "development": development,
            "api_workbook": api_workbook,
            "db_workbook": db_workbook,
            "uiux_workbook": uiux_workbook,
        }

    def test_pass_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = self.create_base_fixture(root)
            proc = self.run_script(root=root, **fixture)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("PASS spec_consistency_check", proc.stdout)
            self.assertIn("invalid_tokens_count=0", proc.stdout)

    def test_fail_when_missing_reqid_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = self.create_base_fixture(root)
            write_csv(
                fixture["summary"],
                ["feature", KOR_REQ_ID],
                [["A", "AI-001"], ["B", "OPS-999"]],
            )
            proc = self.run_script(root=root, **fixture)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("REQID_SUMMARY_UNKNOWN", proc.stdout)
            self.assertIn("OPS-999", proc.stdout)

    def test_fail_when_typo_reqid_token_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = self.create_base_fixture(root)
            write_api_workbook(
                fixture["api_workbook"],
                [
                    "ReqID: AI-001",
                    "ReqID: SEC-01X",
                    "secret_ref",
                    "token tool citation done error heartbeat safe_response",
                    "ReqID: AI-001",
                ],
            )
            proc = self.run_script(root=root, **fixture)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("REQID_API_MALFORMED", proc.stdout)
            self.assertIn("SEC-01X", proc.stdout)


if __name__ == "__main__":
    unittest.main()
