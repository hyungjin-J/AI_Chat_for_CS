#!/usr/bin/env python3
"""Cross-platform mirror-and-run helper for frontend reproducibility."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".gradle",
    "dist",
    "build",
    "target",
    "out",
    ".idea",
    ".vscode",
}


def write_stdout_safe(text: str) -> None:
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(text.encode(encoding, errors="replace"))


def write_stderr_safe(text: str) -> None:
    try:
        sys.stderr.write(text)
    except UnicodeEncodeError:
        encoding = sys.stderr.encoding or "utf-8"
        sys.stderr.buffer.write(text.encode(encoding, errors="replace"))


def print_safe(text: str) -> None:
    write_stdout_safe(text + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mirror workspace and run frontend chain")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--mirror-root", default="")
    parser.add_argument("--force-mirror", action="store_true")
    parser.add_argument("--keep-mirror", action="store_true")
    parser.add_argument("--skip-node-bootstrap", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke-artifact-path", default="")
    return parser.parse_args()


def is_ascii_only(value: str) -> bool:
    return all(ord(char) <= 127 for char in value)


def normalize_path(value: str) -> str:
    return value.replace("\\", "/")


def run_step(name: str, cmd: list[str], cwd: Path | None, dry_run: bool) -> None:
    if dry_run:
        print_safe(f"[DRY-RUN] {name}")
        return

    print_safe(f"[RUN] {name}")
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    if proc.returncode != 0:
        rendered = " ".join(cmd)
        raise RuntimeError(f"command failed (exit={proc.returncode}): {rendered}")


def resolve_ascii_mirror_root(requested_root: str) -> Path:
    if requested_root.strip():
        resolved = Path(requested_root).expanduser().resolve()
        if not is_ascii_only(str(resolved)):
            raise RuntimeError(f"mirror root must be ASCII-only: {resolved}")
        return resolved

    if os.name == "nt":
        temp_value = os.environ.get("TEMP") or "C:/Temp"
        candidate = Path(temp_value) / "AI_Chatbot_ascii_workspace"
        if is_ascii_only(str(candidate)):
            return candidate.resolve()
        return Path("C:/Temp/AI_Chatbot_ascii_workspace").resolve()

    return Path("/tmp/AI_Chatbot_ascii_workspace").resolve()


def get_workspace_ascii_status(source_root: Path, script_root: Path) -> tuple[str, list[str]]:
    check_script = script_root / "check_workspace_path_ascii.py"
    if not check_script.exists():
        return (
            "UNKNOWN",
            [
                "check_workspace_path_ascii",
                "status=UNKNOWN",
                "details=check script not available; fallback to local ASCII detector",
            ],
        )

    proc = subprocess.run(
        [sys.executable, str(check_script), "--path", str(source_root)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    lines: list[str] = []
    if proc.stdout:
        lines.extend([line for line in proc.stdout.splitlines() if line.strip()])
    if proc.stderr:
        lines.extend([line for line in proc.stderr.splitlines() if line.strip()])

    status = "UNKNOWN"
    for line in lines:
        if line.startswith("status="):
            status = line.split("=", 1)[1].strip().upper()
            break

    if not lines:
        lines = [
            "check_workspace_path_ascii",
            "status=UNKNOWN",
            "details=no output from ASCII checker",
        ]

    return status, lines


def path_is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def mirror_workspace(source_root: Path, mirror_root: Path, keep_mirror: bool, dry_run: bool) -> bool:
    if dry_run:
        print_safe("[DRY-RUN] mirror workspace to ASCII path")
        return False

    print_safe("[RUN] mirror workspace to ASCII path")
    if mirror_root.exists() and not keep_mirror:
        shutil.rmtree(mirror_root)

    mirror_root.mkdir(parents=True, exist_ok=True)

    ignore_fn = shutil.ignore_patterns(*sorted(EXCLUDE_DIRS))
    shutil.copytree(source_root, mirror_root, dirs_exist_ok=True, ignore=ignore_fn)
    return True


def detect_package_manager(frontend_dir: Path) -> str:
    lock_files = []
    if (frontend_dir / "pnpm-lock.yaml").exists():
        lock_files.append("pnpm")
    if (frontend_dir / "yarn.lock").exists():
        lock_files.append("yarn")
    if (frontend_dir / "package-lock.json").exists():
        lock_files.append("npm")

    if len(lock_files) > 1:
        raise RuntimeError(
            "multiple lock files detected in frontend/: "
            + ", ".join(sorted(lock_files))
            + " (fail-closed)"
        )

    if len(lock_files) == 1:
        return lock_files[0]

    package_json_path = frontend_dir / "package.json"
    if package_json_path.exists():
        payload = json.loads(package_json_path.read_text(encoding="utf-8"))
        package_manager = str(payload.get("packageManager", "")).strip().lower()
        if package_manager.startswith("pnpm"):
            return "pnpm"
        if package_manager.startswith("yarn"):
            return "yarn"
        if package_manager.startswith("npm"):
            return "npm"

    raise RuntimeError(
        "no lock file detected (pnpm-lock.yaml/yarn.lock/package-lock.json) "
        "and packageManager field is unavailable (fail-closed)"
    )


def install_command_for(manager: str) -> list[str]:
    if manager == "npm":
        return ["npm", "ci", "--prefer-offline", "--no-audit", "--fund=false"]
    if manager == "pnpm":
        return ["pnpm", "install", "--frozen-lockfile"]
    if manager == "yarn":
        return ["yarn", "install", "--frozen-lockfile"]
    raise RuntimeError(f"unsupported package manager: {manager}")


def run_command_for(manager: str, script_name: str) -> list[str]:
    return [manager, "run", script_name]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_summary(
    source_root: Path,
    run_root: Path,
    path_mode: str,
    mirror_requested: bool,
    mirror_performed: bool,
    dry_run: bool,
    node_bootstrap_ran: bool,
    install_ran: bool,
    tests_ran: bool,
    build_ran: bool,
    package_manager: str,
    install_command: str,
) -> str:
    lines = [
        "mirror_and_run_frontend",
        "status=PASS",
        f"source_root={source_root}",
        f"run_root={run_root}",
        f"path_mode={path_mode}",
        f"mirror_requested={mirror_requested}",
        f"mirror_performed={mirror_performed}",
        f"dry_run={dry_run}",
        f"node_bootstrap_ran={node_bootstrap_ran}",
        f"npm_ci_ran={install_ran}",
        f"npm_test_ran={tests_ran}",
        f"npm_build_ran={build_ran}",
        f"package_manager={package_manager}",
        f"install_command={install_command}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    script_root = Path(__file__).resolve().parent

    source_root = Path(args.source_root).expanduser().resolve()
    source_root_ascii = is_ascii_only(str(source_root))

    status, ascii_output = get_workspace_ascii_status(source_root=source_root, script_root=script_root)
    for line in ascii_output:
        print_safe(line)

    should_mirror = bool(args.force_mirror or status == "WARNING" or not source_root_ascii)
    mirror_root = resolve_ascii_mirror_root(args.mirror_root)
    if not is_ascii_only(str(mirror_root)):
        raise RuntimeError(f"resolved mirror root is not ASCII-only: {mirror_root}")

    if source_root == mirror_root:
        raise RuntimeError("mirror root must be different from source root")

    if path_is_under(mirror_root, source_root):
        raise RuntimeError("mirror root must be outside source root")

    run_root = source_root
    path_mode = "native"
    mirror_performed = False

    if should_mirror:
        mirror_performed = mirror_workspace(
            source_root=source_root,
            mirror_root=mirror_root,
            keep_mirror=bool(args.keep_mirror),
            dry_run=bool(args.dry_run),
        )
        run_root = mirror_root
        path_mode = "mirrored"
    else:
        print_safe("[INFO] Workspace path is ASCII-safe. Running in-place.")

    # When dry-run + mirror requested, run root may not exist yet.
    effective_root = run_root
    if args.dry_run and should_mirror and not mirror_performed:
        effective_root = source_root

    frontend_dir = effective_root / "frontend"
    if not frontend_dir.exists():
        raise RuntimeError(f"frontend directory not found: {frontend_dir}")

    package_manager = detect_package_manager(frontend_dir)
    install_command = install_command_for(package_manager)

    run_bootstrap = not args.skip_node_bootstrap
    run_install = not args.skip_install
    run_tests = not args.skip_tests
    run_build = not args.skip_build

    if run_bootstrap:
        if os.name == "nt":
            bootstrap_script = effective_root / "scripts" / "bootstrap_node_from_nvmrc.ps1"
            if not bootstrap_script.exists():
                raise RuntimeError(f"bootstrap script not found: {bootstrap_script}")
            run_step(
                "bootstrap node from .nvmrc",
                [
                    "powershell",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(bootstrap_script),
                    "-NvmrcPath",
                    str(effective_root / ".nvmrc"),
                ],
                cwd=effective_root,
                dry_run=bool(args.dry_run),
            )
        else:
            bootstrap_script = effective_root / "scripts" / "bootstrap_node_from_nvmrc.sh"
            if not bootstrap_script.exists():
                raise RuntimeError(f"bootstrap script not found: {bootstrap_script}")
            run_step(
                "bootstrap node from .nvmrc",
                ["bash", str(bootstrap_script), str(effective_root / ".nvmrc")],
                cwd=effective_root,
                dry_run=bool(args.dry_run),
            )
    else:
        print_safe("[SKIP] node bootstrap")

    if run_install:
        run_step(
            f"frontend: {' '.join(install_command)}",
            install_command,
            cwd=frontend_dir,
            dry_run=bool(args.dry_run),
        )
    if run_tests:
        test_cmd = run_command_for(package_manager, "test:run")
        run_step(
            f"frontend: {' '.join(test_cmd)}",
            test_cmd,
            cwd=frontend_dir,
            dry_run=bool(args.dry_run),
        )
    if run_build:
        build_cmd = run_command_for(package_manager, "build")
        run_step(
            f"frontend: {' '.join(build_cmd)}",
            build_cmd,
            cwd=frontend_dir,
            dry_run=bool(args.dry_run),
        )

    if not any((run_install, run_tests, run_build)):
        print_safe("[SKIP] frontend commands (install/tests/build all skipped)")

    summary = build_summary(
        source_root=source_root,
        run_root=run_root,
        path_mode=path_mode,
        mirror_requested=should_mirror,
        mirror_performed=mirror_performed,
        dry_run=bool(args.dry_run),
        node_bootstrap_ran=run_bootstrap,
        install_ran=run_install,
        tests_ran=run_tests,
        build_ran=run_build,
        package_manager=package_manager,
        install_command=" ".join(install_command),
    )
    write_stdout_safe(summary)

    if args.smoke_artifact_path:
        artifact_path = Path(args.smoke_artifact_path).expanduser().resolve()
        write_text(artifact_path, summary)
        print_safe(f"[OK] smoke artifact written: {artifact_path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        error_summary = f"mirror_and_run_frontend\nstatus=FAIL\nerror={exc}\n"
        write_stderr_safe(f"[FAIL] {exc}\n")
        # Best-effort artifact write on failures.
        try:
            args = parse_args()
            if args.smoke_artifact_path:
                write_text(Path(args.smoke_artifact_path).expanduser().resolve(), error_summary)
        except Exception:
            pass
        raise SystemExit(1)
