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

TASK_CHOICES = ("smoke", "test", "build", "dev")
DEFAULT_ARTIFACT_DIR = Path("docs/review/mvp_verification_pack/artifacts")
DEFAULT_ARTIFACT_PATTERN = "node22_unicode_mirror_helper_{task}.txt"
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
    parser.add_argument("--no-mirror", action="store_true")
    parser.add_argument("--keep-mirror", action="store_true")
    parser.add_argument("--skip-node-bootstrap", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--task", choices=TASK_CHOICES, default="smoke")
    parser.add_argument("--smoke", action="store_true", help="Deprecated alias for --task smoke")
    parser.add_argument("--artifact-path", default="")
    parser.add_argument("--smoke-artifact-path", default="")
    return parser.parse_args()


def is_ascii_only(value: str) -> bool:
    return all(ord(char) <= 127 for char in value)


def resolve_task(args: argparse.Namespace) -> str:
    if args.smoke and args.task != "smoke":
        raise RuntimeError("--smoke cannot be combined with --task other than smoke")
    if args.smoke:
        return "smoke"
    return args.task


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
    manager, _ = detect_package_manager_with_source(frontend_dir)
    return manager


def detect_package_manager_with_source(frontend_dir: Path) -> tuple[str, str]:
    lock_files: list[tuple[str, str]] = []
    if (frontend_dir / "pnpm-lock.yaml").exists():
        lock_files.append(("pnpm", "pnpm-lock.yaml"))
    if (frontend_dir / "yarn.lock").exists():
        lock_files.append(("yarn", "yarn.lock"))
    if (frontend_dir / "package-lock.json").exists():
        lock_files.append(("npm", "package-lock.json"))

    if len(lock_files) > 1:
        raise RuntimeError(
            "multiple lock files detected in frontend/: "
            + ", ".join(sorted(manager for manager, _ in lock_files))
            + " (fail-closed)"
        )

    if len(lock_files) == 1:
        manager, lockfile = lock_files[0]
        return manager, f"lockfile:{lockfile}"

    package_json_path = frontend_dir / "package.json"
    if package_json_path.exists():
        payload = json.loads(package_json_path.read_text(encoding="utf-8"))
        package_manager = str(payload.get("packageManager", "")).strip().lower()
        if package_manager.startswith("pnpm"):
            return "pnpm", "package.json:packageManager"
        if package_manager.startswith("yarn"):
            return "yarn", "package.json:packageManager"
        if package_manager.startswith("npm"):
            return "npm", "package.json:packageManager"

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


def check_git_clean(source_root: Path) -> tuple[str, list[str]]:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=source_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return (
            "unknown",
            ["[WARNING] git command is unavailable; skipping clean-state check."],
        )

    if proc.returncode != 0:
        return (
            "unknown",
            ["[WARNING] git clean-state check unavailable (not a git repo or git error)."],
        )

    changed_lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if changed_lines:
        preview = ", ".join(changed_lines[:5])
        return (
            "false",
            [f"[WARNING] git working tree has uncommitted changes: {preview}"],
        )

    return ("true", ["[INFO] git working tree is clean."])


def parse_nvmrc_version(path: Path) -> str:
    if not path.exists():
        return ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        return line.lstrip("v").strip()
    return ""


def read_runtime_node_version() -> str:
    try:
        proc = subprocess.run(
            ["node", "-v"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""

    if proc.returncode != 0:
        return ""
    value = proc.stdout.strip().lstrip("v").strip()
    return value


def node_runtime_guidance(required: str) -> list[str]:
    if not required:
        return [
            "[GUIDE] .nvmrc version could not be read. Verify .nvmrc in repo root.",
            "[GUIDE] Then check runtime with: node -v",
        ]

    bootstrap_hint = f"nvm install {required} && nvm use {required}"
    return [
        f"[GUIDE] Expected Node version (.nvmrc): {required}",
        f"[GUIDE] Fix runtime version with: {bootstrap_hint}",
        "[GUIDE] Verify again with: python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime",
    ]


def check_node_runtime(source_root: Path) -> tuple[str, str, str, list[str]]:
    required = parse_nvmrc_version(source_root / ".nvmrc")
    runtime = read_runtime_node_version()

    if not required:
        return (
            "",
            runtime,
            "WARNING",
            ["[WARNING] .nvmrc is missing or empty."] + node_runtime_guidance(required),
        )
    if not runtime:
        return (
            required,
            "",
            "WARNING",
            [f"[WARNING] node runtime not found in PATH (expected from .nvmrc={required})."]
            + node_runtime_guidance(required),
        )
    if runtime != required:
        return (
            required,
            runtime,
            "WARNING",
            [
                f"[WARNING] node runtime mismatch (expected from .nvmrc={required}, current={runtime})."
            ]
            + node_runtime_guidance(required),
        )
    return (
        required,
        runtime,
        "PASS",
        [f"[INFO] node runtime matches .nvmrc (expected={required}, current={runtime})."],
    )


def resolve_artifact_path(source_root: Path, task: str, args: argparse.Namespace) -> Path:
    if args.artifact_path.strip():
        return Path(args.artifact_path).expanduser().resolve()
    if args.smoke_artifact_path.strip():
        return Path(args.smoke_artifact_path).expanduser().resolve()
    return (source_root / DEFAULT_ARTIFACT_DIR / DEFAULT_ARTIFACT_PATTERN.format(task=task)).resolve()


def build_summary(
    source_root: Path,
    run_root: Path,
    task: str,
    path_mode: str,
    mirror_requested: bool,
    mirror_performed: bool,
    dry_run: bool,
    git_clean: str,
    node_required_version: str,
    node_runtime_version: str,
    node_check_status: str,
    node_bootstrap_ran: bool,
    install_ran: bool,
    tests_ran: bool,
    build_ran: bool,
    dev_ran: bool,
    package_manager: str,
    package_manager_source: str,
    install_command: str,
    artifact_path: Path,
) -> str:
    lines = [
        "mirror_and_run_frontend",
        "status=PASS",
        f"task={task}",
        f"source_root={source_root}",
        f"run_root={run_root}",
        f"path_mode={path_mode}",
        f"mirror_requested={mirror_requested}",
        f"mirror_performed={mirror_performed}",
        f"smoke_mode={task == 'smoke'}",
        f"dry_run={dry_run}",
        f"git_clean={git_clean}",
        f"node_required_version={node_required_version}",
        f"node_runtime_version={node_runtime_version}",
        f"node_check_status={node_check_status}",
        f"node_bootstrap_ran={node_bootstrap_ran}",
        f"npm_ci_ran={install_ran}",
        f"npm_test_ran={tests_ran}",
        f"npm_build_ran={build_ran}",
        f"npm_dev_ran={dev_ran}",
        f"package_manager={package_manager}",
        f"package_manager_source={package_manager_source}",
        f"install_command={install_command}",
        f"artifact_path={artifact_path}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    task = resolve_task(args)
    script_root = Path(__file__).resolve().parent

    source_root = Path(args.source_root).expanduser().resolve()
    source_root_ascii = is_ascii_only(str(source_root))

    ascii_status, ascii_output = get_workspace_ascii_status(source_root=source_root, script_root=script_root)
    for line in ascii_output:
        print_safe(line)

    if args.force_mirror and args.no_mirror:
        raise RuntimeError("--force-mirror and --no-mirror cannot be used together")

    mirror_root = resolve_ascii_mirror_root(args.mirror_root)
    if not is_ascii_only(str(mirror_root)):
        raise RuntimeError(f"resolved mirror root is not ASCII-only: {mirror_root}")

    non_ascii_detected = bool(ascii_status == "WARNING" or not source_root_ascii)
    should_mirror = bool(args.force_mirror or non_ascii_detected)

    if non_ascii_detected:
        print_safe("[WARNING] Non-ASCII workspace path detected.")
        print_safe("[WARNING] Node package manager execution can fail on Unicode paths in some setups.")
        print_safe(f"[WARNING] source workspace: {source_root}")
        print_safe(f"[WARNING] ASCII mirror target: {mirror_root}")

    if args.no_mirror:
        print_safe("[WARNING] --no-mirror enabled. Running directly in source workspace.")
        if non_ascii_detected:
            print_safe("[WARNING] Expect possible frontend toolchain failures due to Unicode path handling.")
        should_mirror = False

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
        print_safe("[INFO] Running frontend commands in source workspace.")

    effective_root = run_root
    if args.dry_run and should_mirror and not mirror_performed:
        effective_root = source_root

    frontend_dir = effective_root / "frontend"
    if not frontend_dir.exists():
        raise RuntimeError(f"frontend directory not found: {frontend_dir}")

    package_manager, package_manager_source = detect_package_manager_with_source(frontend_dir)
    install_command = install_command_for(package_manager)

    git_clean, git_lines = check_git_clean(source_root)
    for line in git_lines:
        print_safe(line)

    node_required_version, node_runtime_version, node_check_status, node_lines = check_node_runtime(
        source_root
    )
    for line in node_lines:
        print_safe(line)

    smoke_mode = task == "smoke"
    run_bootstrap = False
    run_install = task in {"test", "build", "dev"} and not args.skip_install
    run_tests = task == "test" and not args.skip_tests
    run_build = task == "build" and not args.skip_build
    run_dev = task == "dev"

    if smoke_mode:
        print_safe("[INFO] task=smoke: fast preflight only (no install/test/build/dev).")
    if args.skip_node_bootstrap:
        print_safe("[SKIP] node bootstrap")
    else:
        print_safe("[INFO] node bootstrap automation is disabled; validation/guidance only.")

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

    if run_dev:
        dev_cmd = run_command_for(package_manager, "dev")
        run_step(
            f"frontend: {' '.join(dev_cmd)}",
            dev_cmd,
            cwd=frontend_dir,
            dry_run=bool(args.dry_run),
        )

    if not any((run_install, run_tests, run_build, run_dev)):
        print_safe("[SKIP] frontend commands (all disabled for selected task/options)")

    artifact_path = resolve_artifact_path(source_root=source_root, task=task, args=args)
    summary = build_summary(
        source_root=source_root,
        run_root=run_root,
        task=task,
        path_mode=path_mode,
        mirror_requested=should_mirror,
        mirror_performed=mirror_performed,
        dry_run=bool(args.dry_run),
        git_clean=git_clean,
        node_required_version=node_required_version,
        node_runtime_version=node_runtime_version,
        node_check_status=node_check_status,
        node_bootstrap_ran=run_bootstrap,
        install_ran=run_install,
        tests_ran=run_tests,
        build_ran=run_build,
        dev_ran=run_dev,
        package_manager=package_manager,
        package_manager_source=package_manager_source,
        install_command=" ".join(install_command),
        artifact_path=artifact_path,
    )
    write_stdout_safe(summary)

    write_text(artifact_path, summary)
    print_safe(f"[OK] artifact written: {artifact_path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        write_stderr_safe(f"[FAIL] {exc}\n")
        error_summary = f"mirror_and_run_frontend\nstatus=FAIL\nerror={exc}\n"
        try:
            parsed = parse_args()
            task = resolve_task(parsed)
            source_root = Path(parsed.source_root).expanduser().resolve()
            artifact_path = resolve_artifact_path(source_root=source_root, task=task, args=parsed)
            write_text(artifact_path, error_summary)
            write_stderr_safe(f"[FAIL] artifact written: {artifact_path}\n")
        except Exception:
            pass
        raise SystemExit(1)
