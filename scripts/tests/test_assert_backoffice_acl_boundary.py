from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_backoffice_acl_boundary.py"


def write_contract(path: Path, baseline_file: str, baseline_markdown: str) -> None:
    payload = {
        "scan_root": "backend/src/main/java/com/aichatbot/channels/backoffice",
        "file_glob": "**/*.java",
        "forbidden_import_tokens": [".infrastructure.", ".presentation.", ".domain."],
        "required_prefix": "com.aichatbot.contexts.",
        "baseline_file": baseline_file,
        "baseline_markdown": baseline_markdown,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_baseline_json(path: Path, violations: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"violations": violations}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_baseline_markdown(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Baseline",
                "",
                "| file | line | import | classification |",
                "|---|---:|---|---|",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_java(path: Path, imports: list[str]) -> None:
    body = ["package com.aichatbot.channels.backoffice.presentation;"]
    body.extend([f"import {item};" for item in imports])
    body.append("public final class SampleController {}")
    body.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body), encoding="utf-8")


class BackofficeAclBoundaryRatchetTest(unittest.TestCase):
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
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_pass_when_only_baseline_violation_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_json_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            baseline_md_rel = "docs/review/mvp_verification_pack/artifacts/baseline.md"
            file_path = "backend/src/main/java/com/aichatbot/channels/backoffice/presentation/SampleController.java"
            import_target = "com.aichatbot.contexts.operations.infrastructure.OpsRepository"
            write_baseline_json(
                root / baseline_json_rel,
                [
                    {
                        "file": file_path,
                        "line": 2,
                        "import_target": import_target,
                        "classification": "FORBIDDEN_INFRA_IMPORT",
                    }
                ],
            )
            write_baseline_markdown(root / baseline_md_rel)

            contract_path = root / "scripts/contracts/backoffice_acl_boundary_contract.json"
            write_contract(contract_path, baseline_json_rel, baseline_md_rel)
            write_java(root / file_path, [import_target])

            proc = self.run_script(root, contract_path)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("new_violation_count=0", proc.stdout)

    def test_fail_on_new_forbidden_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_json_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            baseline_md_rel = "docs/review/mvp_verification_pack/artifacts/baseline.md"
            write_baseline_json(root / baseline_json_rel, [])
            write_baseline_markdown(root / baseline_md_rel)
            contract_path = root / "scripts/contracts/backoffice_acl_boundary_contract.json"
            write_contract(contract_path, baseline_json_rel, baseline_md_rel)

            write_java(
                root / "backend/src/main/java/com/aichatbot/channels/backoffice/presentation/SampleController.java",
                ["com.aichatbot.contexts.identity.rbac.infrastructure.RbacApprovalService"],
            )
            proc = self.run_script(root, contract_path)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("new_violation_count=1", proc.stdout)

    def test_fail_on_new_domain_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_json_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            baseline_md_rel = "docs/review/mvp_verification_pack/artifacts/baseline.md"
            write_baseline_json(root / baseline_json_rel, [])
            write_baseline_markdown(root / baseline_md_rel)
            contract_path = root / "scripts/contracts/backoffice_acl_boundary_contract.json"
            write_contract(contract_path, baseline_json_rel, baseline_md_rel)

            write_java(
                root / "backend/src/main/java/com/aichatbot/channels/backoffice/presentation/SampleController.java",
                ["com.aichatbot.contexts.operations.domain.OpsMetricTotal"],
            )
            proc = self.run_script(root, contract_path)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("new_violation_count=1", proc.stdout)
            self.assertIn("FORBIDDEN_DOMAIN_IMPORT", proc.stdout)

    def test_pass_for_application_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_json_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            baseline_md_rel = "docs/review/mvp_verification_pack/artifacts/baseline.md"
            write_baseline_json(root / baseline_json_rel, [])
            write_baseline_markdown(root / baseline_md_rel)
            contract_path = root / "scripts/contracts/backoffice_acl_boundary_contract.json"
            write_contract(contract_path, baseline_json_rel, baseline_md_rel)

            write_java(
                root / "backend/src/main/java/com/aichatbot/channels/backoffice/presentation/SampleController.java",
                ["com.aichatbot.contexts.identity.rbac.application.RbacApprovalFacade"],
            )
            proc = self.run_script(root, contract_path)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("new_violation_count=0", proc.stdout)

    def test_fail_when_baseline_grows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head_baseline_rel = "docs/review/mvp_verification_pack/artifacts/head_baseline.json"
            base_baseline_rel = "docs/review/mvp_verification_pack/artifacts/base_baseline.json"
            baseline_md_rel = "docs/review/mvp_verification_pack/artifacts/baseline.md"
            write_baseline_json(
                root / head_baseline_rel,
                [
                    {
                        "file": "backend/src/main/java/com/aichatbot/channels/backoffice/presentation/NewDebt.java",
                        "line": 2,
                        "import_target": "com.aichatbot.contexts.operations.infrastructure.OpsRepository",
                        "classification": "FORBIDDEN_INFRA_IMPORT",
                    }
                ],
            )
            write_baseline_json(root / base_baseline_rel, [])
            write_baseline_markdown(root / baseline_md_rel)
            contract_path = root / "scripts/contracts/backoffice_acl_boundary_contract.json"
            write_contract(contract_path, head_baseline_rel, baseline_md_rel)

            proc = self.run_script(
                root,
                contract_path,
                ["--baseline-base-file", base_baseline_rel],
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("baseline_growth_count=1", proc.stdout)

    def test_pass_when_baseline_size_is_same(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head_baseline_rel = "docs/review/mvp_verification_pack/artifacts/head_baseline.json"
            base_baseline_rel = "docs/review/mvp_verification_pack/artifacts/base_baseline.json"
            baseline_md_rel = "docs/review/mvp_verification_pack/artifacts/baseline.md"
            sample = [
                {
                    "file": "backend/src/main/java/com/aichatbot/channels/backoffice/presentation/SameDebt.java",
                    "line": 2,
                    "import_target": "com.aichatbot.contexts.operations.infrastructure.OpsRepository",
                    "classification": "FORBIDDEN_INFRA_IMPORT",
                }
            ]
            write_baseline_json(root / head_baseline_rel, sample)
            write_baseline_json(root / base_baseline_rel, sample)
            write_baseline_markdown(root / baseline_md_rel)
            contract_path = root / "scripts/contracts/backoffice_acl_boundary_contract.json"
            write_contract(contract_path, head_baseline_rel, baseline_md_rel)

            proc = self.run_script(
                root,
                contract_path,
                ["--baseline-base-file", base_baseline_rel],
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("baseline_growth_count=0", proc.stdout)

    def test_pass_when_baseline_size_decreases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head_baseline_rel = "docs/review/mvp_verification_pack/artifacts/head_baseline.json"
            base_baseline_rel = "docs/review/mvp_verification_pack/artifacts/base_baseline.json"
            baseline_md_rel = "docs/review/mvp_verification_pack/artifacts/baseline.md"
            write_baseline_json(root / head_baseline_rel, [])
            write_baseline_json(
                root / base_baseline_rel,
                [
                    {
                        "file": "backend/src/main/java/com/aichatbot/channels/backoffice/presentation/OldDebt.java",
                        "line": 2,
                        "import_target": "com.aichatbot.contexts.operations.infrastructure.OpsRepository",
                        "classification": "FORBIDDEN_INFRA_IMPORT",
                    }
                ],
            )
            write_baseline_markdown(root / baseline_md_rel)
            contract_path = root / "scripts/contracts/backoffice_acl_boundary_contract.json"
            write_contract(contract_path, head_baseline_rel, baseline_md_rel)

            proc = self.run_script(
                root,
                contract_path,
                ["--baseline-base-file", base_baseline_rel],
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("baseline_growth_count=0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
