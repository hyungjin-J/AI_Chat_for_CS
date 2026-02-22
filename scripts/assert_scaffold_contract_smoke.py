#!/usr/bin/env python3
"""Scaffold smoke gate: generate template outputs and validate contract structure."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def to_pascal_case(value: str) -> str:
    parts = [part for part in value.replace("-", "_").split("_") if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


def to_camel_case(value: str) -> str:
    pascal = to_pascal_case(value)
    if not pascal:
        return ""
    return pascal[:1].lower() + pascal[1:]


def run_command(command: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    text = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, text


def render_text(payload: dict) -> str:
    lines = [
        "assert_scaffold_contract_smoke",
        f"status={payload['status']}",
        f"backend_scaffold_exit={payload['backend_scaffold_exit']}",
        f"frontend_scaffold_exit={payload['frontend_scaffold_exit']}",
        f"missing_count={len(payload['missing_paths'])}",
    ]
    for path in payload["missing_paths"]:
        lines.append(f"- [MISSING] {path}")
    if payload["backend_scaffold_output"]:
        lines.append("backend_scaffold_output_snippet=" + payload["backend_scaffold_output"][:300].replace("\n", "\\n"))
    if payload["frontend_scaffold_output"]:
        lines.append("frontend_scaffold_output_snippet=" + payload["frontend_scaffold_output"][:300].replace("\n", "\\n"))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold smoke gate with template contract validation")
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract", default="scripts/contracts/domain_template_contract.json")
    parser.add_argument("--backend-context", default="continuation_acl")
    parser.add_argument("--frontend-context", default="backoffice")
    parser.add_argument("--frontend-feature", default="ops_console")
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    contract_path = (repo_root / args.contract) if not Path(args.contract).is_absolute() else Path(args.contract)
    contract = json.loads(contract_path.read_text(encoding="utf-8", errors="strict"))

    backend_context = args.backend_context.strip().lower()
    frontend_context = args.frontend_context.strip().lower()
    frontend_feature = args.frontend_feature.strip().lower()
    backend_context_class = to_pascal_case(backend_context)
    frontend_feature_class = to_pascal_case(frontend_feature)
    frontend_feature_camel = to_camel_case(frontend_feature)

    backend_script = repo_root / "scripts/scaffold_backend_context.py"
    frontend_script = repo_root / "scripts/scaffold_frontend_feature.py"

    missing_paths: list[str] = []
    backend_output = ""
    frontend_output = ""
    backend_exit = 1
    frontend_exit = 1

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        backend_java_root = workspace / "backend/src/main/java/com/aichatbot/contexts"
        backend_mapper_root = workspace / "backend/src/main/resources/mappers"
        backend_test_root = workspace / "backend/src/test/java/com/aichatbot/contexts"
        frontend_feature_root = workspace / "frontend/src/features"

        backend_cmd = [
            sys.executable,
            str(backend_script),
            "--context",
            backend_context,
            "--java-root",
            str(backend_java_root),
            "--mapper-root",
            str(backend_mapper_root),
            "--test-root",
            str(backend_test_root),
        ]
        frontend_cmd = [
            sys.executable,
            str(frontend_script),
            "--context",
            frontend_context,
            "--feature",
            frontend_feature,
            "--root",
            str(frontend_feature_root),
        ]

        backend_exit, backend_output = run_command(backend_cmd, cwd=repo_root)
        frontend_exit, frontend_output = run_command(frontend_cmd, cwd=repo_root)

        backend_contract = contract["backend_context_template"]
        backend_context_root = backend_java_root / backend_context
        for required_dir in backend_contract["required_dirs"]:
            expected = backend_context_root / required_dir
            if not expected.exists():
                missing_paths.append(expected.relative_to(workspace).as_posix())

        for required_file in backend_contract["required_files"]:
            rendered = (
                required_file.replace("{Context}", backend_context_class).replace("{context}", backend_context)
            )
            expected = backend_context_root / rendered
            if not expected.exists():
                missing_paths.append(expected.relative_to(workspace).as_posix())

        mapper_path = backend_contract["mapper_xml_path"]
        mapper_rendered = mapper_path.replace("{Context}", backend_context_class).replace("{context}", backend_context)
        mapper_expected = workspace / mapper_rendered
        if not mapper_expected.exists():
            missing_paths.append(mapper_expected.relative_to(workspace).as_posix())

        frontend_contract = contract["frontend_feature_template"]
        feature_root = frontend_feature_root / frontend_context / frontend_feature
        for required_dir in frontend_contract["required_dirs"]:
            expected = feature_root / required_dir
            if not expected.exists():
                missing_paths.append(expected.relative_to(workspace).as_posix())

        for required_file in frontend_contract["required_files"]:
            rendered_default = (
                required_file
                .replace("{feature}", frontend_feature)
                .replace("{Feature}", frontend_feature_class)
            )
            candidates = [feature_root / rendered_default]
            if "{feature}" in required_file:
                rendered_camel = (
                    required_file
                    .replace("{feature}", frontend_feature_camel)
                    .replace("{Feature}", frontend_feature_class)
                )
                candidates.append(feature_root / rendered_camel)
            if not any(candidate.exists() for candidate in candidates):
                missing_paths.append(candidates[0].relative_to(workspace).as_posix())

    status = "PASS" if backend_exit == 0 and frontend_exit == 0 and not missing_paths else "FAIL"
    payload = {
        "status": status,
        "backend_scaffold_exit": backend_exit,
        "frontend_scaffold_exit": frontend_exit,
        "missing_paths": sorted(set(missing_paths)),
        "backend_scaffold_output": backend_output,
        "frontend_scaffold_output": frontend_output,
    }

    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.output_txt:
        output_txt = Path(args.output_txt)
        output_txt.parent.mkdir(parents=True, exist_ok=True)
        output_txt.write_text(text_report, encoding="utf-8")
    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json_report, encoding="utf-8")

    sys.stdout.write(text_report)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
