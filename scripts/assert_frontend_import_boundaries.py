#!/usr/bin/env python3
"""Fail-closed import boundary checks for frontend shared/widgets/features."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


IMPORT_PATTERN = re.compile(
    r"""^\s*(?:import|export)\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE,
)
DYNAMIC_IMPORT_PATTERN = re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)""")


@dataclass
class Violation:
    code: str
    file: str
    import_path: str
    details: str


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def normalize(path: Path) -> str:
    return path.as_posix()


def collect_source_files(root: Path, globs: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in globs:
        files.extend([path for path in root.glob(pattern) if path.is_file()])
    return sorted(set(files))


def parse_imports(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="strict")
    imports = IMPORT_PATTERN.findall(text)
    imports.extend(DYNAMIC_IMPORT_PATTERN.findall(text))
    return sorted(set(imports))


def resolve_import(
    importer: Path,
    import_path: str,
    repo_root: Path,
    frontend_root: Path,
    path_aliases: dict[str, str],
) -> Path | None:
    if import_path.startswith("."):
        candidate = (importer.parent / import_path).resolve()
        return resolve_with_extensions(candidate)

    for alias, mapped in path_aliases.items():
        if import_path.startswith(alias):
            suffix = import_path[len(alias):]
            mapped_base = (repo_root / mapped).resolve()
            candidate = mapped_base / suffix
            return resolve_with_extensions(candidate)

    if import_path.startswith("frontend/src/"):
        candidate = (repo_root / import_path).resolve()
        return resolve_with_extensions(candidate)
    if import_path.startswith("src/"):
        candidate = (repo_root / "frontend" / import_path).resolve()
        return resolve_with_extensions(candidate)
    if import_path.startswith("features/"):
        candidate = frontend_root / import_path
        return resolve_with_extensions(candidate.resolve())
    if import_path.startswith("shared/"):
        candidate = frontend_root / import_path
        return resolve_with_extensions(candidate.resolve())
    if import_path.startswith("widgets/"):
        candidate = frontend_root / import_path
        return resolve_with_extensions(candidate.resolve())
    return None


def resolve_with_extensions(candidate: Path) -> Path | None:
    checks = [
        candidate,
        Path(str(candidate) + ".ts"),
        Path(str(candidate) + ".tsx"),
        candidate / "index.ts",
        candidate / "index.tsx",
    ]
    for path in checks:
        if path.exists() and path.is_file():
            return path
    return None


def classify_group(path: Path, frontend_root: Path, features_dir: str, shared_dirs: list[str]) -> str:
    rel = normalize(path.relative_to(frontend_root))
    for shared_dir in shared_dirs:
        prefix = shared_dir.rstrip("/") + "/"
        if rel.startswith(prefix) or rel == shared_dir:
            return shared_dir
    feature_prefix = features_dir.rstrip("/") + "/"
    if rel.startswith(feature_prefix):
        parts = rel.split("/")
        if len(parts) >= 2:
            return f"feature:{parts[1]}"
    return "other"


def is_cross_feature_entry(path: Path, frontend_root: Path, features_dir: str, allowed_entry_files: set[str]) -> bool:
    rel = normalize(path.relative_to(frontend_root))
    prefix = features_dir.rstrip("/") + "/"
    if not rel.startswith(prefix):
        return False
    parts = rel.split("/")
    if len(parts) != 3:
        return False
    return parts[2] in allowed_entry_files


def detect_cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    stack: list[str] = []
    stack_set: set[str] = set()
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        visited.add(node)
        stack.append(node)
        stack_set.add(node)
        for nxt in sorted(edges.get(node, set())):
            if nxt not in visited:
                dfs(nxt)
            elif nxt in stack_set:
                cycle_start = stack.index(nxt)
                cycle = stack[cycle_start:] + [nxt]
                if len(cycle) > 2:
                    cycles.append(cycle)
        stack.pop()
        stack_set.remove(node)

    for node in sorted(edges):
        if node not in visited:
            dfs(node)
    return cycles


def render_text(payload: dict) -> str:
    lines = [
        "assert_frontend_import_boundaries",
        f"status={payload['status']}",
        f"scanned_file_count={payload['scanned_file_count']}",
        f"violation_count={payload['violation_count']}",
        f"cycle_count={payload['cycle_count']}",
    ]
    for item in payload["violations"]:
        lines.append(f"- [{item['code']}] {item['file']} -> {item['import_path']} :: {item['details']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert frontend import boundaries")
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--contract",
        default="scripts/contracts/frontend_import_boundary_contract.json",
    )
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    contract_path = (repo_root / args.contract) if not Path(args.contract).is_absolute() else Path(args.contract)
    contract = load_contract(contract_path)

    frontend_root = repo_root / contract["frontend_root"]
    source_globs = [str(item) for item in contract["source_globs"]]
    path_aliases = {str(key): str(value) for key, value in dict(contract.get("path_aliases", {})).items()}
    shared_dirs = [str(item) for item in contract["shared_dirs"]]
    features_dir = str(contract["features_dir"])
    allowed_entry_files = {str(item) for item in contract["allowed_cross_feature_entry_files"]}

    source_files = collect_source_files(frontend_root, source_globs)
    violations: list[Violation] = []
    graph: dict[str, set[str]] = {}

    for source_file in source_files:
        source_rel = normalize(source_file.relative_to(repo_root))
        source_group = classify_group(source_file, frontend_root, features_dir, shared_dirs)
        imports = parse_imports(source_file)
        for import_path in imports:
            target = resolve_import(
                importer=source_file,
                import_path=import_path,
                repo_root=repo_root,
                frontend_root=frontend_root,
                path_aliases=path_aliases,
            )
            if target is None or not target.exists():
                continue
            target_group = classify_group(target, frontend_root, features_dir, shared_dirs)
            graph.setdefault(source_group, set()).add(target_group)

            if source_group in {"shared", "widgets"} and target_group.startswith("feature:"):
                violations.append(
                    Violation(
                        code="SHARED_WIDGETS_IMPORT_FEATURE_FORBIDDEN",
                        file=source_rel,
                        import_path=import_path,
                        details=f"{source_group} cannot import {target_group}",
                    )
                )
                continue

            if source_group.startswith("feature:") and target_group.startswith("feature:"):
                source_feature = source_group.split(":", 1)[1]
                target_feature = target_group.split(":", 1)[1]
                if source_feature != target_feature and not is_cross_feature_entry(
                    path=target,
                    frontend_root=frontend_root,
                    features_dir=features_dir,
                    allowed_entry_files=allowed_entry_files,
                ):
                    violations.append(
                        Violation(
                            code="FEATURE_CROSS_IMPORT_INTERNAL_FORBIDDEN",
                            file=source_rel,
                            import_path=import_path,
                            details=(
                                "cross-feature imports must target public index.ts(x) only; "
                                f"source={source_feature} target={target_feature}"
                            ),
                        )
                    )

    cycles = detect_cycles(graph)
    for cycle in cycles:
        if any(node.startswith("feature:") or node in {"shared", "widgets"} for node in cycle):
            violations.append(
                Violation(
                    code="FRONTEND_MODULE_CYCLE_DETECTED",
                    file="(graph)",
                    import_path=" -> ".join(cycle),
                    details="lightweight cycle check failed",
                )
            )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "scanned_file_count": len(source_files),
        "violation_count": len(violations),
        "cycle_count": len(cycles),
        "violations": [asdict(item) for item in violations],
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
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
