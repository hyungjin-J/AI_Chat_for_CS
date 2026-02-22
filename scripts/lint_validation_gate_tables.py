#!/usr/bin/env python3
"""Lint Validation Gate evidence paths in non-chatGPT markdown docs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_GLOBS = [
    "docs/reports/**/*.md",
    "docs/ops/runbook_*.md",
    "docs/review/plans/**/*.md",
]
ARTIFACT_ROOT = "docs/review/mvp_verification_pack/artifacts/"
ALLOWED_SINGLE = "spec_sync_report.md"


@dataclass
class MissingPath:
    file: str
    line: int
    path: str
    reason: str


@dataclass
class WarningItem:
    file: str
    line: int
    code: str
    message: str


def normalize_path(path: str) -> str:
    return path.strip().strip("`").strip().replace("\\", "/")


def is_external_url(path: str) -> bool:
    p = path.lower()
    return p.startswith("http://") or p.startswith("https://")


def extract_paths(cell: str) -> set[str]:
    found: set[str] = set()

    for match in re.findall(r"`([^`]+)`", cell):
        normalized = normalize_path(match)
        if normalized:
            found.add(normalized)

    for match in re.findall(r"\[[^\]]+\]\(([^)]+)\)", cell):
        normalized = normalize_path(match)
        if normalized:
            found.add(normalized)

    for match in re.findall(r"(docs/review/mvp_verification_pack/artifacts/[A-Za-z0-9._/\-]+|spec_sync_report\.md)", cell):
        normalized = normalize_path(match)
        if normalized:
            found.add(normalized)

    return found


def find_validation_gate_blocks(lines: list[str]) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    start = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()
        if "validation gate" in lower and stripped.startswith("#"):
            if start is not None:
                blocks.append((start, idx))
            start = idx
            continue
        if start is not None and stripped.startswith("#"):
            blocks.append((start, idx))
            start = None
    if start is not None:
        blocks.append((start, len(lines)))
    return blocks


def parse_tables_in_block(
    file_path: Path,
    lines: list[str],
    block_start: int,
    block_end: int,
) -> tuple[int, int, list[MissingPath], list[WarningItem]]:
    scanned_tables = 0
    extracted_count = 0
    missing: list[MissingPath] = []
    warnings: list[WarningItem] = []

    i = block_start
    while i < block_end:
        line = lines[i].strip()
        if not line.startswith("|"):
            i += 1
            continue

        header_cells = [cell.strip().lower() for cell in line.split("|")[1:-1]]
        if "evidence" not in header_cells:
            i += 1
            continue

        evidence_idx = header_cells.index("evidence")
        if i + 1 >= block_end or not lines[i + 1].strip().startswith("|"):
            i += 1
            continue

        scanned_tables += 1
        i += 2  # skip header and separator
        while i < block_end and lines[i].strip().startswith("|"):
            raw_row = lines[i].strip()
            row_cells = [cell.strip() for cell in raw_row.split("|")[1:-1]]
            if evidence_idx >= len(row_cells):
                i += 1
                continue

            evidence_cell = row_cells[evidence_idx]
            extracted = extract_paths(evidence_cell)
            extracted_count += len(extracted)

            # Warn external links in evidence cell.
            if re.search(r"https?://", evidence_cell):
                warnings.append(
                    WarningItem(
                        file=file_path.as_posix(),
                        line=i + 1,
                        code="EXTERNAL_EVIDENCE_URL",
                        message="external URL in Evidence cell is skipped from local existence check",
                    )
                )

            for path in extracted:
                if is_external_url(path):
                    continue
                if path != ALLOWED_SINGLE and not path.startswith(ARTIFACT_ROOT):
                    warnings.append(
                        WarningItem(
                            file=file_path.as_posix(),
                            line=i + 1,
                            code="OUT_OF_SCOPE_LOCAL_PATH",
                            message=f"local evidence path out of allowed scope: {path}",
                        )
                    )
                    continue
                if not Path(path).exists():
                    missing.append(
                        MissingPath(
                            file=file_path.as_posix(),
                            line=i + 1,
                            path=path,
                            reason="local evidence path not found",
                        )
                    )
            i += 1
    return scanned_tables, extracted_count, missing, warnings


def collect_target_files(root: Path, files: list[str] | None, globs: list[str]) -> list[Path]:
    if files:
        resolved = [root / Path(item) if not Path(item).is_absolute() else Path(item) for item in files]
        return sorted({path.resolve() for path in resolved if path.exists()})

    found: set[Path] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if path.is_file():
                found.add(path.resolve())
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Validation Gate tables evidence paths")
    parser.add_argument("--root", default=".")
    parser.add_argument("--files", nargs="*")
    parser.add_argument("--glob", action="append", dest="globs")
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    globs = args.globs if args.globs else list(DEFAULT_GLOBS)
    targets = collect_target_files(root=root, files=args.files, globs=globs)

    scanned_tables_total = 0
    extracted_paths_total = 0
    missing: list[MissingPath] = []
    warnings: list[WarningItem] = []

    for target in targets:
        lines = target.read_text(encoding="utf-8", errors="strict").splitlines()
        blocks = find_validation_gate_blocks(lines=lines)
        for block_start, block_end in blocks:
            scanned, extracted, missing_items, warning_items = parse_tables_in_block(
                file_path=target.relative_to(root),
                lines=lines,
                block_start=block_start,
                block_end=block_end,
            )
            scanned_tables_total += scanned
            extracted_paths_total += extracted
            missing.extend(missing_items)
            warnings.extend(warning_items)

    missing_paths = sorted({item.path for item in missing})
    payload = {
        "status": "PASS" if not missing else "FAIL",
        "root": root.as_posix(),
        "target_globs": globs,
        "scanned_files_count": len(targets),
        "scanned_tables_count": scanned_tables_total,
        "extracted_evidence_paths_count": extracted_paths_total,
        "missing_local_evidence_count": len(missing),
        "missing_local_paths": missing_paths,
        "missing_local_evidence": [asdict(item) for item in missing],
        "warning_count": len(warnings),
        "warnings": [asdict(item) for item in warnings],
    }

    txt_lines = [
        "lint_validation_gate_tables",
        f"status={payload['status']}",
        f"scanned_files_count={payload['scanned_files_count']}",
        f"scanned_tables_count={payload['scanned_tables_count']}",
        f"extracted_evidence_paths_count={payload['extracted_evidence_paths_count']}",
        f"missing_local_evidence_count={payload['missing_local_evidence_count']}",
        f"warning_count={payload['warning_count']}",
    ]
    for item in payload["missing_local_evidence"]:
        txt_lines.append(
            f"- missing file={item['file']} line={item['line']} path={item['path']} reason={item['reason']}"
        )
    for item in payload["warnings"]:
        txt_lines.append(
            f"- warning file={item['file']} line={item['line']} code={item['code']} message={item['message']}"
        )
    txt_report = "\n".join(txt_lines) + "\n"
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.output_txt:
        out_txt = Path(args.output_txt)
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(txt_report, encoding="utf-8")
    if args.output_json:
        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json_report, encoding="utf-8")

    sys.stdout.write(txt_report)
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
