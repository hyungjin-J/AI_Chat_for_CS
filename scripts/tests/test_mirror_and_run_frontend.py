from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "mirror_and_run_frontend.py"
ARTIFACT_DIR = "docs/review/mvp_verification_pack/artifacts"


def write_text(path: Path, content: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_frontend_workspace(
    root: Path,
    lockfiles: list[str],
    nvmrc: str = "22.12.0",
    package_manager: str | None = None,
) -> Path:
    write_text(root / ".nvmrc", nvmrc + "\n")
    frontend_dir = root / "frontend"
    frontend_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "name": "frontend",
        "private": True,
        "scripts": {
            "test:run": "echo test",
            "build": "echo build",
            "dev": "echo dev",
        },
    }
    if package_manager:
        payload["packageManager"] = package_manager

    write_text(frontend_dir / "package.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
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
    def test_default_task_is_smoke_and_native_on_ascii_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_ascii_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script("--source-root", str(workspace), "--dry-run")

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "task"), "smoke")
            self.assertEqual(summary_value(proc.stdout, "smoke_mode"), "True")
            self.assertEqual(summary_value(proc.stdout, "path_mode"), "native")
            self.assertEqual(summary_value(proc.stdout, "package_manager"), "npm")

    def test_non_ascii_path_dry_run_switches_to_mirror(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_root_") as tmp:
            root = Path(tmp)
            workspace = root / "유니코드_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script("--source-root", str(workspace), "--dry-run", "--task", "smoke")

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "path_mode"), "mirrored")
            self.assertEqual(summary_value(proc.stdout, "mirror_requested"), "True")
            self.assertIn("Non-ASCII workspace path detected", proc.stdout)
            self.assertIn("ASCII mirror target", proc.stdout)

    def test_no_mirror_is_allowed_with_loud_warning(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_nomirror_") as tmp:
            root = Path(tmp)
            workspace = root / "유니코드_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script(
                "--source-root",
                str(workspace),
                "--dry-run",
                "--task",
                "smoke",
                "--no-mirror",
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "path_mode"), "native")
            self.assertEqual(summary_value(proc.stdout, "mirror_requested"), "False")
            self.assertIn("--no-mirror enabled", proc.stdout)

    def test_package_lock_only_selects_npm(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_npm_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script("--source-root", str(workspace), "--dry-run", "--task", "smoke")

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "package_manager"), "npm")
            self.assertEqual(summary_value(proc.stdout, "package_manager_source"), "lockfile:package-lock.json")

    def test_yarn_lock_selects_yarn(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_yarn_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["yarn.lock"])

            proc = run_script("--source-root", str(workspace), "--dry-run", "--task", "smoke")

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "package_manager"), "yarn")
            self.assertEqual(summary_value(proc.stdout, "package_manager_source"), "lockfile:yarn.lock")

    def test_package_manager_field_fallback_without_lockfile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_pkgmgr_field_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, [], package_manager="pnpm@9.12.1")

            proc = run_script("--source-root", str(workspace), "--dry-run", "--task", "smoke")

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "package_manager"), "pnpm")
            self.assertEqual(summary_value(proc.stdout, "package_manager_source"), "package.json:packageManager")

    def test_lockfile_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_conflict_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json", "pnpm-lock.yaml"])

            proc = run_script("--source-root", str(workspace), "--dry-run", "--task", "smoke")

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("multiple lock files detected", proc.stderr)

    def test_smoke_default_artifact_is_created(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_artifact_smoke_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])
            expected = workspace / ARTIFACT_DIR / "node22_unicode_mirror_helper_smoke.txt"

            proc = run_script("--source-root", str(workspace), "--dry-run", "--task", "smoke")

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertTrue(expected.exists())
            content = expected.read_text(encoding="utf-8")
            self.assertIn("mirror_and_run_frontend", content)
            self.assertIn("status=PASS", content)
            self.assertIn("task=smoke", content)

    def test_test_task_emits_deterministic_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_artifact_test_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])
            expected = workspace / ARTIFACT_DIR / "node22_unicode_mirror_helper_test.txt"

            proc = run_script("--source-root", str(workspace), "--dry-run", "--task", "test")

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertTrue(expected.exists())
            content = expected.read_text(encoding="utf-8")
            self.assertIn("task=test", content)
            self.assertIn("npm_test_ran=True", content)

    def test_cli_rejects_smoke_with_non_smoke_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_cli_conflict_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])

            proc = run_script("--source-root", str(workspace), "--smoke", "--task", "test")

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("--smoke cannot be combined", proc.stderr)

    def test_artifact_path_override_is_respected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_artifact_override_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"])
            custom = workspace / "custom_artifacts" / "mirror_helper.txt"

            proc = run_script(
                "--source-root",
                str(workspace),
                "--dry-run",
                "--task",
                "smoke",
                "--artifact-path",
                str(custom),
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertTrue(custom.exists())
            self.assertIn(f"artifact_path={custom}", custom.read_text(encoding="utf-8"))

    def test_nvmrc_mismatch_shows_expected_and_current_versions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror_node_warn_") as tmp:
            workspace = Path(tmp)
            make_frontend_workspace(workspace, ["package-lock.json"], nvmrc="0.0.1")

            proc = run_script("--source-root", str(workspace), "--dry-run", "--task", "smoke")

            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertEqual(summary_value(proc.stdout, "node_required_version"), "0.0.1")
            self.assertEqual(summary_value(proc.stdout, "node_check_status"), "WARNING")
            self.assertIn("expected from .nvmrc=0.0.1", proc.stdout)


if __name__ == "__main__":
    unittest.main()
