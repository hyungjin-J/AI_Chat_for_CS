from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_SCRIPT = REPO_ROOT / "scripts" / "spec_impl_coverage_report.py"
GATE_SCRIPT = REPO_ROOT / "scripts" / "assert_spec_impl_coverage.py"


def run_python(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(script), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def build_fixture(root: Path, *, include_backend: bool) -> dict[str, Path]:
    docs_references = root / "docs" / "references"
    backend_main = root / "backend" / "src" / "main" / "java" / "com" / "acme" / "api"
    backend_test = root / "backend" / "src" / "test" / "java"
    frontend_src = root / "frontend" / "src"
    artifacts = root / "docs" / "review" / "mvp_verification_pack" / "artifacts"

    docs_references.mkdir(parents=True, exist_ok=True)
    backend_main.mkdir(parents=True, exist_ok=True)
    backend_test.mkdir(parents=True, exist_ok=True)
    frontend_src.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    (docs_references / "CS AI Chatbot_Requirements Statement.csv").write_text(
        "ReqID,\uc911\uc694\ub3c4\nSEC-001,Must\n",
        encoding="utf-8",
    )

    workbook_path = docs_references / "google_ready_api_spec_v0.3_20260216.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "\uc804\uccb4API\ubaa9\ub85d"
    worksheet.append(
        [
            "\ubc88\ud638",
            "\uce74\ud14c\uace0\ub9ac",
            "\ud504\ub85c\uadf8\ub7a8ID",
            "API\uba85",
            "Method",
            "Endpoint",
            "\uc124\uba85",
            "Request",
            "Response",
            "\uad8c\ud55c",
            "\ube44\uace0",
        ]
    )
    worksheet.append(
        [
            1,
            "AUTH",
            "API-AUTH-LOGIN",
            "login",
            "POST",
            "/v1/auth/login",
            "-",
            "-",
            "-",
            "PUBLIC",
            "ReqID: SEC-001",
        ]
    )
    workbook.save(workbook_path)
    workbook.close()

    if include_backend:
        (backend_main / "AuthController.java").write_text(
            "package com.acme.api;\n"
            "import org.springframework.web.bind.annotation.*;\n"
            "@RestController\n"
            "@RequestMapping(\"/v1/auth\")\n"
            "public class AuthController {\n"
            "    @PostMapping(\"/login\")\n"
            "    public String login() { return \"ok\"; }\n"
            "}\n",
            encoding="utf-8",
        )

    report_json = artifacts / "spec_impl_coverage_report.json"
    report_txt = artifacts / "spec_impl_coverage_report.txt"
    report_md = artifacts / "spec_impl_coverage_report.md"
    gate_json = artifacts / "spec_impl_coverage_gate.json"
    gate_txt = artifacts / "spec_impl_coverage_gate.txt"

    return {
        "requirements": docs_references / "CS AI Chatbot_Requirements Statement.csv",
        "workbook": workbook_path,
        "backend_main": root / "backend" / "src" / "main" / "java",
        "backend_test": root / "backend" / "src" / "test",
        "frontend_src": frontend_src,
        "report_json": report_json,
        "report_txt": report_txt,
        "report_md": report_md,
        "gate_json": gate_json,
        "gate_txt": gate_txt,
    }


class AssertSpecImplCoverageTest(unittest.TestCase):
    def test_gate_fails_when_must_backend_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            fixture = build_fixture(work_dir, include_backend=False)

            report = run_python(
                REPORT_SCRIPT,
                work_dir,
                "--root",
                str(work_dir),
                "--requirements",
                str(fixture["requirements"]),
                "--api-workbook",
                str(fixture["workbook"]),
                "--backend-root",
                str(fixture["backend_main"]),
                "--backend-test-root",
                str(fixture["backend_test"]),
                "--frontend-root",
                str(fixture["frontend_src"]),
                "--report-json",
                str(fixture["report_json"]),
                "--report-txt",
                str(fixture["report_txt"]),
                "--report-md",
                str(fixture["report_md"]),
            )
            self.assertEqual(report.returncode, 0, msg=report.stdout + report.stderr)

            gate = run_python(
                GATE_SCRIPT,
                work_dir,
                "--report-json",
                str(fixture["report_json"]),
                "--output-json",
                str(fixture["gate_json"]),
                "--output-txt",
                str(fixture["gate_txt"]),
            )
            self.assertNotEqual(gate.returncode, 0)
            self.assertIn("MUST_BACKEND_IMPLEMENTATION_MISSING", gate.stdout)

    def test_gate_can_optionally_require_tests_for_must(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            fixture = build_fixture(work_dir, include_backend=True)

            report = run_python(
                REPORT_SCRIPT,
                work_dir,
                "--root",
                str(work_dir),
                "--requirements",
                str(fixture["requirements"]),
                "--api-workbook",
                str(fixture["workbook"]),
                "--backend-root",
                str(fixture["backend_main"]),
                "--backend-test-root",
                str(fixture["backend_test"]),
                "--frontend-root",
                str(fixture["frontend_src"]),
                "--report-json",
                str(fixture["report_json"]),
                "--report-txt",
                str(fixture["report_txt"]),
                "--report-md",
                str(fixture["report_md"]),
            )
            self.assertEqual(report.returncode, 0, msg=report.stdout + report.stderr)

            payload = json.loads(fixture["report_json"].read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["must_only"]["must_backend_missing_count"], 0)
            self.assertEqual(payload["rows"][0]["tests_present"], False)

            gate_without_tests = run_python(
                GATE_SCRIPT,
                work_dir,
                "--report-json",
                str(fixture["report_json"]),
                "--output-json",
                str(fixture["gate_json"]),
                "--output-txt",
                str(fixture["gate_txt"]),
            )
            self.assertEqual(gate_without_tests.returncode, 0)

            gate_with_tests = run_python(
                GATE_SCRIPT,
                work_dir,
                "--report-json",
                str(fixture["report_json"]),
                "--output-json",
                str(fixture["gate_json"]),
                "--output-txt",
                str(fixture["gate_txt"]),
                "--require-tests-for-must",
            )
            self.assertNotEqual(gate_with_tests.returncode, 0)
            self.assertIn("MUST_TEST_COVERAGE_MISSING", gate_with_tests.stdout)


if __name__ == "__main__":
    unittest.main()
