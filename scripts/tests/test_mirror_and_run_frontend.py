from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "mirror_and_run_frontend.py"


def write_text(path: Path, content: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_frontend_workspace(root: Path, lockfiles: list[str]) -> Path:
    frontend_dir = root / "frontend"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        frontend_dir / "package.json",
        """{
  "name": "frontend",
  "private": true,
  "scripts": {
    "test:run": "echo test",
    "build": "echo build"
  }
}
""",
    )
    for lockfile in lockfiles:
        write_text(frontend_dir / lockfile, "lock\n")
    return frontend_dir


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def summary_value(text: str, key: str) -> str:
    prefix = f"{key}="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    raise AssertionError(f"missing key: {key}\n{text}")


class MirrorAndRunFrontendTest(unittest.TestCase):
    def test_ascii_path_dry_run_stays_native(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_ascii_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script(
                "--source-root",
                str(workspace),
                "--dry-run",
                "--skip-node-bootstrap",
                "--skip-install",
                "--skip-tests",
                "--skip-build",
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "path_mode"), "native")
            self.assertEqual(summary_value(proc.stdout, "package_manager"), "npm")

    def test_non_ascii_path_dry_run_switches_to_mirror(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_root_") as tmp:
            root = Path(tmp)
            workspace = root / "한글_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script(
                "--source-root",
                str(workspace),
                "--dry-run",
                "--skip-node-bootstrap",
                "--skip-install",
                "--skip-tests",
                "--skip-build",
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "path_mode"), "mirrored")
            self.assertEqual(summary_value(proc.stdout, "mirror_requested"), "True")

    def test_package_lock_only_selects_npm(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_npm_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script(
                "--source-root",
                str(workspace),
                "--dry-run",
                "--skip-node-bootstrap",
                "--skip-install",
                "--skip-tests",
                "--skip-build",
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "package_manager"), "npm")
            self.assertIn("npm ci --prefer-offline --no-audit --fund=false", proc.stdout)

    def test_lockfile_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_conflict_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json", "pnpm-lock.yaml"])

            proc = run_script(
                "--source-root",
                str(workspace),
                "--dry-run",
                "--skip-node-bootstrap",
                "--skip-install",
                "--skip-tests",
                "--skip-build",
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("multiple lock files detected", proc.stderr)

    def test_smoke_artifact_is_created(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_artifact_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])
            artifact_path = workspace / "artifacts" / "smoke.txt"

            proc = run_script(
                "--source-root",
                str(workspace),
                "--dry-run",
                "--skip-node-bootstrap",
                "--skip-install",
                "--skip-tests",
                "--skip-build",
                "--smoke-artifact-path",
                str(artifact_path),
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertTrue(artifact_path.exists())
            content = artifact_path.read_text(encoding="utf-8")
            self.assertIn("mirror_and_run_frontend", content)
            self.assertIn("status=PASS", content)

    def test_skip_flags_disable_command_execution_flags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_skip_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script(
                "--source-root",
                str(workspace),
                "--dry-run",
                "--skip-node-bootstrap",
                "--skip-install",
                "--skip-tests",
                "--skip-build",
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "node_bootstrap_ran"), "False")
            self.assertEqual(summary_value(proc.stdout, "npm_ci_ran"), "False")
            self.assertEqual(summary_value(proc.stdout, "npm_test_ran"), "False")
            self.assertEqual(summary_value(proc.stdout, "npm_build_ran"), "False")


if __name__ == "__main__":
    unittest.main()
