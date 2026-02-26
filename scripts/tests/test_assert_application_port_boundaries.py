from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_application_port_boundaries.py"


def write_contract(path: Path, baseline_file: str, include_missing_target: bool = False) -> None:
    targets: list[dict] = [
        {
            "name": "operations_application",
            "scan_root": "backend/src/main/java/com/aichatbot/contexts/operations/application",
            "file_glob": "**/*.java",
            "required_prefix": "com.aichatbot.contexts.",
            "forbidden_import_tokens": [".infrastructure."],
        },
        {
            "name": "rag_application",
            "scan_root": "backend/src/main/java/com/aichatbot/contexts/knowledge/rag/application",
            "file_glob": "**/*.java",
            "required_prefix": "com.aichatbot.contexts.",
            "forbidden_import_tokens": [".infrastructure."],
        },
    ]
    if include_missing_target:
        targets.append(
            {
                "name": "missing_scan_root",
                "scan_root": "backend/src/main/java/com/aichatbot/contexts/missing/application",
                "file_glob": "**/*.java",
                "required_prefix": "com.aichatbot.contexts.",
                "forbidden_import_tokens": [".infrastructure."],
            }
        )
    payload = {
        "targets": targets,
        "baseline_file": baseline_file,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_baseline(path: Path, violations: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"violations": violations}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_java(path: Path, imports: list[str]) -> None:
    body = ["package com.aichatbot.contexts.sample.application;"]
    body.extend([f"import {item};" for item in imports])
    body.append("public final class SampleService {}")
    body.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body), encoding="utf-8")


class ApplicationPortBoundaryRatchetTest(unittest.TestCase):
    def run_script(
        self,
        root: Path,
        contract_path: Path,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = [
            "python",
            str(SCRIPT_PATH),
            "--root",
            str(root),
            "--contract",
            str(contract_path),
        ]
        if extra_args:
            args.extend(extra_args)
        return subprocess.run(
            args,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_pass_with_zero_baseline_and_no_forbidden_imports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            write_baseline(root / baseline_rel, [])
            contract_path = root / "scripts/contracts/application_port_boundary_contract.json"
            write_contract(contract_path, baseline_rel)

            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/operations/application/SampleService.java",
                ["com.aichatbot.contexts.operations.domain.OpsMetricRow"],
            )
            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/knowledge/rag/application/SampleService.java",
                ["com.aichatbot.contexts.knowledge.rag.domain.model.ChunkSearchRow"],
            )

            proc = self.run_script(root, contract_path)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("new_violation_count=0", proc.stdout)

    def test_fail_when_new_forbidden_import_is_added(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            write_baseline(root / baseline_rel, [])
            contract_path = root / "scripts/contracts/application_port_boundary_contract.json"
            write_contract(contract_path, baseline_rel)

            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/operations/application/SampleService.java",
                ["com.aichatbot.contexts.operations.infrastructure.OpsRepository"],
            )
            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/knowledge/rag/application/SampleService.java",
                [],
            )

            proc = self.run_script(root, contract_path)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("new_violation_count=1", proc.stdout)
            self.assertIn("APP_PORT_FORBIDDEN_IMPORT", proc.stdout)

    def test_fail_when_baseline_grows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head_baseline_rel = "docs/review/mvp_verification_pack/artifacts/head_baseline.json"
            base_baseline_rel = "docs/review/mvp_verification_pack/artifacts/base_baseline.json"
            sample_violation = [
                {
                    "target": "operations_application",
                    "file": "backend/src/main/java/com/aichatbot/contexts/operations/application/SampleService.java",
                    "line": 2,
                    "import_target": "com.aichatbot.contexts.operations.infrastructure.OpsRepository",
                    "code": "APP_PORT_FORBIDDEN_IMPORT",
                    "details": "",
                }
            ]
            write_baseline(root / head_baseline_rel, sample_violation)
            write_baseline(root / base_baseline_rel, [])
            contract_path = root / "scripts/contracts/application_port_boundary_contract.json"
            write_contract(contract_path, head_baseline_rel)

            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/operations/application/SampleService.java",
                [],
            )
            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/knowledge/rag/application/SampleService.java",
                [],
            )

            proc = self.run_script(
                root,
                contract_path,
                ["--baseline-base-file", base_baseline_rel],
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("baseline_growth_count=1", proc.stdout)

    def test_pass_when_baseline_violation_is_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            write_baseline(
                root / baseline_rel,
                [
                    {
                        "target": "operations_application",
                        "file": "backend/src/main/java/com/aichatbot/contexts/operations/application/SampleService.java",
                        "line": 2,
                        "import_target": "com.aichatbot.contexts.operations.infrastructure.OpsRepository",
                        "code": "APP_PORT_FORBIDDEN_IMPORT",
                        "details": "",
                    }
                ],
            )
            contract_path = root / "scripts/contracts/application_port_boundary_contract.json"
            write_contract(contract_path, baseline_rel)

            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/operations/application/SampleService.java",
                [],
            )
            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/knowledge/rag/application/SampleService.java",
                [],
            )

            proc = self.run_script(root, contract_path)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("resolved_baseline_count=1", proc.stdout)

    def test_fail_when_scan_root_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            write_baseline(root / baseline_rel, [])
            contract_path = root / "scripts/contracts/application_port_boundary_contract.json"
            write_contract(contract_path, baseline_rel, include_missing_target=True)

            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/operations/application/SampleService.java",
                [],
            )
            write_java(
                root / "backend/src/main/java/com/aichatbot/contexts/knowledge/rag/application/SampleService.java",
                [],
            )

            proc = self.run_script(root, contract_path)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("APP_PORT_SCAN_ROOT_MISSING", proc.stdout)


if __name__ == "__main__":
    unittest.main()
