from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "assert_frontend_import_boundaries.py"


def write_contract(path: Path) -> None:
    payload = {
        "frontend_root": "frontend/src",
        "source_globs": ["**/*.ts", "**/*.tsx"],
        "path_aliases": {"@/": "frontend/src/"},
        "shared_dirs": ["shared", "widgets"],
        "features_dir": "features",
        "allowed_cross_feature_entry_files": ["index.ts", "index.tsx"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class FrontendImportBoundaryTest(unittest.TestCase):
    def run_script(self, root: Path, contract_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--root",
                str(root),
                "--contract",
                str(contract_path),
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_pass_when_feature_imports_shared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/frontend_import_boundary_contract.json"
            write_contract(contract_path)

            write_file(root / "frontend/src/shared/api/http.ts", "export const x = 1;\n")
            write_file(
                root / "frontend/src/features/a/ui/A.tsx",
                'import { x } from "../../../shared/api/http";\nexport const A = () => x;\n',
            )

            proc = self.run_script(root, contract_path)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_fail_when_shared_imports_feature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/frontend_import_boundary_contract.json"
            write_contract(contract_path)

            write_file(root / "frontend/src/features/a/index.ts", "export const a = 1;\n")
            write_file(
                root / "frontend/src/shared/bad.ts",
                'import { a } from "../features/a";\nexport const bad = a;\n',
            )

            proc = self.run_script(root, contract_path)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SHARED_WIDGETS_IMPORT_FEATURE_FORBIDDEN", proc.stdout)

    def test_fail_when_feature_imports_other_feature_internal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/frontend_import_boundary_contract.json"
            write_contract(contract_path)

            write_file(root / "frontend/src/features/b/index.ts", "export const b = 1;\n")
            write_file(root / "frontend/src/features/b/internal/secret.ts", "export const secret = 42;\n")
            write_file(
                root / "frontend/src/features/a/ui/A.tsx",
                'import { secret } from "../../b/internal/secret";\nexport const A = () => secret;\n',
            )

            proc = self.run_script(root, contract_path)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("FEATURE_CROSS_IMPORT_INTERNAL_FORBIDDEN", proc.stdout)

    def test_fail_when_cycle_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "scripts/contracts/frontend_import_boundary_contract.json"
            write_contract(contract_path)

            write_file(root / "frontend/src/shared/a.ts", 'import { b } from "../widgets/b"; export const a = b;\n')
            write_file(root / "frontend/src/widgets/b.ts", 'import { a } from "../shared/a"; export const b = a;\n')

            proc = self.run_script(root, contract_path)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("FRONTEND_MODULE_CYCLE_DETECTED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
