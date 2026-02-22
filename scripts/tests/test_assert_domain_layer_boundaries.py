from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_domain_layer_boundaries.py"


def write_contract(path: Path, baseline_path: str) -> None:
    payload = {
        "scan_root": "backend/src/main/java/com/aichatbot/contexts",
        "domain_glob": "**/domain/**/*.java",
        "forbidden_import_tokens": [
            ".infrastructure.",
            ".application.",
            ".presentation.",
        ],
        "baseline_file": baseline_path,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_baseline(path: Path, violations: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"violations": violations}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_java_with_import(path: Path, import_target: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "package com.aichatbot.contexts.billing.domain.service;",
                f"import {import_target};",
                "public final class SampleDomainService {}",
                "",
            ]
        ),
        encoding="utf-8",
    )


class DomainLayerBoundaryRatchetTest(unittest.TestCase):
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

    def test_pass_when_only_baseline_violation_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            baseline_path = root / baseline_rel
            write_baseline(
                baseline_path,
                [
                    {
                        "file": "backend/src/main/java/com/aichatbot/contexts/billing/domain/service/SampleDomainService.java",
                        "line": 2,
                        "import_target": "com.aichatbot.contexts.billing.infrastructure.RateCardRepository",
                        "code": "DOMAIN_LAYER_FORBIDDEN_IMPORT",
                    }
                ],
            )

            contract_path = root / "scripts/contracts/domain_layer_boundary_contract.json"
            write_contract(contract_path, baseline_rel)

            java_path = root / "backend/src/main/java/com/aichatbot/contexts/billing/domain/service/SampleDomainService.java"
            write_java_with_import(java_path, "com.aichatbot.contexts.billing.infrastructure.RateCardRepository")

            proc = self.run_script(root, contract_path)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)
            self.assertIn("new_violation_count=0", proc.stdout)

    def test_fail_when_new_violation_is_added(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            write_baseline(root / baseline_rel, [])

            contract_path = root / "scripts/contracts/domain_layer_boundary_contract.json"
            write_contract(contract_path, baseline_rel)

            java_path = root / "backend/src/main/java/com/aichatbot/contexts/knowledge/domain/service/SampleDomainService.java"
            write_java_with_import(java_path, "com.aichatbot.contexts.knowledge.application.KnowledgeUseCase")

            proc = self.run_script(root, contract_path)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("status=FAIL", proc.stdout)
            self.assertIn("new_violation_count=1", proc.stdout)

    def test_pass_when_baseline_violation_is_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_rel = "docs/review/mvp_verification_pack/artifacts/baseline.json"
            write_baseline(
                root / baseline_rel,
                [
                    {
                        "file": "backend/src/main/java/com/aichatbot/contexts/identity/domain/service/OldViolation.java",
                        "line": 2,
                        "import_target": "com.aichatbot.contexts.identity.infrastructure.AuthRepository",
                        "code": "DOMAIN_LAYER_FORBIDDEN_IMPORT",
                    }
                ],
            )

            contract_path = root / "scripts/contracts/domain_layer_boundary_contract.json"
            write_contract(contract_path, baseline_rel)

            proc = self.run_script(root, contract_path)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("resolved_baseline_count=1", proc.stdout)
            self.assertIn("status=PASS", proc.stdout)

    def test_fail_when_baseline_grows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head_baseline_rel = "docs/review/mvp_verification_pack/artifacts/head_baseline.json"
            base_baseline_rel = "docs/review/mvp_verification_pack/artifacts/base_baseline.json"
            write_baseline(
                root / head_baseline_rel,
                [
                    {
                        "file": "backend/src/main/java/com/aichatbot/contexts/billing/domain/service/AddedDebt.java",
                        "line": 2,
                        "import_target": "com.aichatbot.contexts.billing.infrastructure.RateCardRepository",
                        "code": "DOMAIN_LAYER_FORBIDDEN_IMPORT",
                    }
                ],
            )
            write_baseline(root / base_baseline_rel, [])
            contract_path = root / "scripts/contracts/domain_layer_boundary_contract.json"
            write_contract(contract_path, head_baseline_rel)

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
            sample = [
                {
                    "file": "backend/src/main/java/com/aichatbot/contexts/billing/domain/service/SameDebt.java",
                    "line": 2,
                    "import_target": "com.aichatbot.contexts.billing.infrastructure.RateCardRepository",
                    "code": "DOMAIN_LAYER_FORBIDDEN_IMPORT",
                }
            ]
            write_baseline(root / head_baseline_rel, sample)
            write_baseline(root / base_baseline_rel, sample)
            contract_path = root / "scripts/contracts/domain_layer_boundary_contract.json"
            write_contract(contract_path, head_baseline_rel)

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
            write_baseline(root / head_baseline_rel, [])
            write_baseline(
                root / base_baseline_rel,
                [
                    {
                        "file": "backend/src/main/java/com/aichatbot/contexts/billing/domain/service/OldDebt.java",
                        "line": 2,
                        "import_target": "com.aichatbot.contexts.billing.infrastructure.RateCardRepository",
                        "code": "DOMAIN_LAYER_FORBIDDEN_IMPORT",
                    }
                ],
            )
            contract_path = root / "scripts/contracts/domain_layer_boundary_contract.json"
            write_contract(contract_path, head_baseline_rel)

            proc = self.run_script(
                root,
                contract_path,
                ["--baseline-base-file", base_baseline_rel],
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("baseline_growth_count=0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
