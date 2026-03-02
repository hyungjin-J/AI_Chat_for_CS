from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "spec_impl_coverage_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("spec_impl_coverage_report", SCRIPT_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("failed to load spec_impl_coverage_report module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_report(work_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(SCRIPT_PATH), *args],
        cwd=work_dir,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def build_minimal_fixture(root: Path, *, include_backend_endpoint: bool) -> dict[str, Path]:
    docs_references = root / "docs" / "references"
    backend_main = root / "backend" / "src" / "main" / "java" / "com" / "acme" / "api"
    backend_test = root / "backend" / "src" / "test" / "java" / "com" / "acme" / "api"
    frontend_src = root / "frontend" / "src" / "shared" / "api"
    artifacts = root / "docs" / "review" / "mvp_verification_pack" / "artifacts"

    docs_references.mkdir(parents=True, exist_ok=True)
    backend_main.mkdir(parents=True, exist_ok=True)
    backend_test.mkdir(parents=True, exist_ok=True)
    frontend_src.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    requirements_path = docs_references / "CS AI Chatbot_Requirements Statement.csv"
    requirements_path.write_text(
        "ReqID,\uc911\uc694\ub3c4\n"
        "SEC-001,Must\n"
        "OPS-001,Should\n",
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
    worksheet.append(
        [
            2,
            "OPS",
            "API-OPS-ECHO",
            "echo",
            "GET",
            "/v1/ops/echo",
            "-",
            "-",
            "-",
            "OPS",
            "ReqID: OPS-001",
        ]
    )
    workbook.save(workbook_path)
    workbook.close()

    if include_backend_endpoint:
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

    (frontend_src / "authApi.ts").write_text(
        "export const loginUrl = \"/v1/auth/login\";\n",
        encoding="utf-8",
    )
    (backend_test / "AuthControllerTest.java").write_text(
        "class AuthControllerTest { String p = \"/v1/auth/login\"; }\n",
        encoding="utf-8",
    )

    report_json = artifacts / "spec_impl_coverage_report.json"
    report_txt = artifacts / "spec_impl_coverage_report.txt"
    report_md = artifacts / "spec_impl_coverage_report.md"
    return {
        "requirements": requirements_path,
        "workbook": workbook_path,
        "backend_main": root / "backend" / "src" / "main" / "java",
        "backend_test": root / "backend" / "src" / "test",
        "frontend_src": root / "frontend" / "src",
        "report_json": report_json,
        "report_txt": report_txt,
        "report_md": report_md,
    }


class SpecImplCoverageReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_parse_reqids_supports_reqid_plus(self) -> None:
        note = "ReqID: SEC-001, API-007\\nReqID+: UI-004, UI-005"
        tokens = self.module.parse_reqids_from_note(note)
        self.assertEqual(tokens, ["API-007", "SEC-001", "UI-004", "UI-005"])

    def test_path_normalization_and_equivalence(self) -> None:
        left = self.module.normalize_endpoint_template("/v1/sessions/{session_id}/messages/{message_id}/")
        right = self.module.normalize_endpoint_template("/v1/sessions/{sid}/messages/{mid}")
        self.assertEqual(left, "/v1/sessions/{}/messages/{}")
        self.assertTrue(self.module.paths_equivalent(left, right))

        regex = self.module.compile_endpoint_regex("/v1/sessions/{session_id}/messages/{message_id}")
        matched = regex.search("const u = `/v1/sessions/${sessionId}/messages/${messageId}`;")
        self.assertIsNotNone(matched)

    def test_report_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            fixture = build_minimal_fixture(work_dir, include_backend_endpoint=True)

            args = [
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
            ]

            first = run_report(work_dir, *args)
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            first_json = fixture["report_json"].read_text(encoding="utf-8")
            first_txt = fixture["report_txt"].read_text(encoding="utf-8")

            second = run_report(work_dir, *args)
            self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
            second_json = fixture["report_json"].read_text(encoding="utf-8")
            second_txt = fixture["report_txt"].read_text(encoding="utf-8")

            self.assertEqual(first_json, second_json)
            self.assertEqual(first_txt, second_txt)

            payload = json.loads(first_json)
            self.assertEqual(
                list(payload.keys()),
                [
                    "status",
                    "generated_at_utc",
                    "metadata",
                    "summary",
                    "must_green_program_ids",
                    "must_red_program_ids",
                    "missing_must_apis",
                    "rows",
                ],
            )
            self.assertEqual(payload["rows"][0]["program_id"], "API-AUTH-LOGIN")
            self.assertEqual(payload["rows"][1]["program_id"], "API-OPS-ECHO")


if __name__ == "__main__":
    unittest.main()
