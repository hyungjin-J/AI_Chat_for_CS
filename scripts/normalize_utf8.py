#!/usr/bin/env python3
"""Normalize selected text files to UTF-8 without BOM."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import fnmatch
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_CODE_FILTER = [
    "UTF8_BOM_FORBIDDEN",
    "UTF16_BOM_FORBIDDEN",
    "UTF32_BOM_FORBIDDEN",
]
DEFAULT_FALLBACK_ENCODINGS = ["cp949", "euc-kr", "latin-1"]
CANONICAL_SPEC_BASENAMES = {
    "cs ai chatbot_requirements statement.csv",
    "summary of key features.csv",
    "development environment.csv",
    "cs_ai_chatbot_db.xlsx",
    "cs_rag_ui_ux_\uc124\uacc4\uc11c.xlsx",
}
CANONICAL_SPEC_BASENAME_GLOBS = ("google_ready_api_spec*.xlsx",)
CANONICAL_SPEC_CONFIRMATION = "I understand Notion sync is required"


@dataclass
class ConversionResult:
    path: str
    old_encoding: str
    new_encoding: str
    action: str
    old_bytes_sha256: str
    new_bytes_sha256: str
    old_decoded_sha256: str
    new_decoded_sha256: str
    old_line_endings: str
    new_line_endings: str
    changed: bool
    status: str
    message: str


def parse_paths(raw_items: list[str]) -> list[str]:
    values: list[str] = []
    for raw in raw_items:
        for token in raw.replace(",", "\n").splitlines():
            token = token.strip().replace("\\", "/")
            if token:
                values.append(token)
    return sorted(set(values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize files to UTF-8 without BOM")
    parser.add_argument("--root", default=".")
    parser.add_argument("--paths", nargs="*", default=[])
    parser.add_argument("--baseline-file", help="Optional UTF-8 scan baseline/current JSON")
    parser.add_argument("--code-filter", nargs="*", default=DEFAULT_CODE_FILTER)
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Maximum number of files to process (0 means no limit)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-fallback-encodings", nargs="*", default=DEFAULT_FALLBACK_ENCODINGS)
    parser.add_argument(
        "--allow-canonical-spec",
        action="store_true",
        help="Allow canonical spec files to be normalized (dangerous; requires confirmation phrase)",
    )
    parser.add_argument(
        "--canonical-spec-confirm",
        default="",
        help="Typed confirmation phrase required with --allow-canonical-spec",
    )
    parser.add_argument("--report-md")
    parser.add_argument("--report-json")
    return parser.parse_args()


def load_paths_from_baseline(root: Path, baseline_file: Path, code_filter: set[str]) -> list[str]:
    payload = json.loads(baseline_file.read_text(encoding="utf-8", errors="strict"))
    violations = payload.get("violations", []) if isinstance(payload, dict) else []
    paths: list[str] = []
    for item in violations:
        code = str(item.get("code", "")).strip()
        rel = str(item.get("path", "")).strip().replace("\\", "/")
        if not rel:
            continue
        if code_filter and code not in code_filter:
            continue
        if (root / rel).is_file():
            paths.append(rel)
    return sorted(set(paths))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def line_ending_style(text: str) -> str:
    crlf_count = text.count("\r\n")
    normalized = text.replace("\r\n", "")
    cr_count = normalized.count("\r")
    lf_count = normalized.count("\n")
    if crlf_count and not lf_count and not cr_count:
        return "CRLF"
    if lf_count and not crlf_count and not cr_count:
        return "LF"
    if cr_count and not crlf_count and not lf_count:
        return "CR"
    if not crlf_count and not cr_count and not lf_count:
        return "NONE"
    return f"MIXED(CRLF={crlf_count},LF={lf_count},CR={cr_count})"


def is_probably_binary(raw: bytes) -> bool:
    if not raw:
        return False
    sample = raw[:4096]
    if b"\x00" in sample:
        return True
    text_like_controls = {9, 10, 13}
    non_printable = 0
    for byte in sample:
        if byte < 32 and byte not in text_like_controls:
            non_printable += 1
    return (non_printable / len(sample)) > 0.30


def detect_encoding(raw: bytes, fallback_encodings: list[str]) -> tuple[str | None, str | None]:
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", None
    if raw.startswith(b"\xff\xfe\x00\x00"):
        return "utf-32", None
    if raw.startswith(b"\x00\x00\xfe\xff"):
        return "utf-32", None
    if raw.startswith(b"\xff\xfe"):
        return "utf-16", None
    if raw.startswith(b"\xfe\xff"):
        return "utf-16", None

    if is_probably_binary(raw):
        return None, "binary file detected; skipped"

    try:
        raw.decode("utf-8", errors="strict")
        return "utf-8", None
    except UnicodeDecodeError:
        pass

    for encoding in fallback_encodings:
        try:
            raw.decode(encoding, errors="strict")
            return encoding, None
        except UnicodeDecodeError:
            continue
    return None, "unable to decode with utf-8 or fallback encodings"


def normalize_file(
    path: Path,
    root: Path,
    fallback_encodings: list[str],
    dry_run: bool,
) -> ConversionResult:
    raw = path.read_bytes()
    old_encoding, error = detect_encoding(raw, fallback_encodings)
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix().replace("\\", "/")

    if old_encoding is None:
        return ConversionResult(
            path=rel,
            old_encoding="unknown",
            new_encoding="utf-8",
            action="SKIP_BINARY_OR_UNDECODABLE",
            old_bytes_sha256=sha256_hex(raw),
            new_bytes_sha256=sha256_hex(raw),
            old_decoded_sha256="",
            new_decoded_sha256="",
            old_line_endings="UNKNOWN",
            new_line_endings="UNKNOWN",
            changed=False,
            status="SKIPPED",
            message=error or "decode failure",
        )

    decoded = raw.decode(old_encoding, errors="strict")
    normalized = decoded.encode("utf-8")
    old_line_endings = line_ending_style(decoded)
    new_line_endings = line_ending_style(normalized.decode("utf-8", errors="strict"))

    old_decoded_hash = sha256_hex(decoded.encode("utf-8"))
    new_decoded_hash = sha256_hex(normalized)
    changed = raw != normalized

    action = "NO_CHANGE"
    if changed:
        if old_encoding == "utf-8-sig":
            action = "BOM_REMOVED"
        elif old_encoding.startswith("utf-16"):
            action = "UTF16_TO_UTF8"
        elif old_encoding.startswith("utf-32"):
            action = "UTF32_TO_UTF8"
        elif old_encoding == "utf-8":
            action = "UTF8_REWRITE"
        else:
            action = f"{old_encoding.upper()}_TO_UTF8"

    if changed and not dry_run:
        original_mode = path.stat().st_mode
        path.write_bytes(normalized)
        # Preserve file mode where possible after write operation.
        try:
            os.chmod(path, original_mode)
        except OSError:
            pass

    return ConversionResult(
        path=rel,
        old_encoding=old_encoding,
        new_encoding="utf-8",
        action=action,
        old_bytes_sha256=sha256_hex(raw),
        new_bytes_sha256=sha256_hex(normalized if changed else raw),
        old_decoded_sha256=old_decoded_hash,
        new_decoded_sha256=new_decoded_hash,
        old_line_endings=old_line_endings,
        new_line_endings=new_line_endings,
        changed=changed,
        status="CHANGED" if changed else "NOOP",
        message="normalized" if changed else "already utf-8 without BOM",
    )


def render_markdown(results: list[ConversionResult], dry_run: bool) -> str:
    changed = [item for item in results if item.changed]
    skipped = [item for item in results if item.status == "SKIPPED"]
    lines = [
        "# UTF-8 Normalization Report",
        "",
        f"- generated_at_utc: {datetime.now(timezone.utc).isoformat()}",
        f"- dry_run: {'YES' if dry_run else 'NO'}",
        f"- candidate_count: {len(results)}",
        f"- changed_count: {len(changed)}",
        f"- skipped_count: {len(skipped)}",
        "- verification_method: decoded-text SHA-256 + byte SHA-256",
        "",
        "| file | old_encoding | action | old_bytes_sha256 | new_bytes_sha256 | old_decoded_sha256 | new_decoded_sha256 | line_endings(old->new) | status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in results:
        lines.append(
            f"| `{item.path}` | `{item.old_encoding}` | `{item.action}` | "
            f"`{item.old_bytes_sha256}` | `{item.new_bytes_sha256}` | "
            f"`{item.old_decoded_sha256}` | `{item.new_decoded_sha256}` | "
            f"`{item.old_line_endings}->{item.new_line_endings}` | `{item.status}` |"
        )
    if skipped:
        lines.extend(["", "## Skipped", ""])
        for item in skipped:
            lines.append(f"- `{item.path}`: {item.message}")
    lines.append("")
    return "\n".join(lines)


def write_output(path: Path | None, content: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def is_canonical_spec_path(path_value: str) -> bool:
    basename = Path(path_value).name.strip().casefold()
    if basename in CANONICAL_SPEC_BASENAMES:
        return True
    return any(fnmatch.fnmatch(basename, pattern) for pattern in CANONICAL_SPEC_BASENAME_GLOBS)


def validate_canonical_spec_guard(args: argparse.Namespace, input_paths: list[str]) -> tuple[bool, str]:
    canonical_paths = sorted(path for path in input_paths if is_canonical_spec_path(path))
    if not canonical_paths:
        return True, ""

    if not args.allow_canonical_spec:
        message = "\n".join(
            [
                "normalize_utf8.py fail-fast: canonical spec files are blocked by default.",
                "Use --allow-canonical-spec with explicit confirmation only when Notion/spec sync updates are planned.",
                "blocked_paths:",
                *[f"- {path}" for path in canonical_paths],
            ]
        )
        return False, message

    if args.canonical_spec_confirm.strip() != CANONICAL_SPEC_CONFIRMATION:
        message = "\n".join(
            [
                "normalize_utf8.py fail-fast: --allow-canonical-spec requires exact confirmation phrase.",
                f"required_confirmation: {CANONICAL_SPEC_CONFIRMATION}",
                "blocked_paths:",
                *[f"- {path}" for path in canonical_paths],
            ]
        )
        return False, message

    warning = "\n".join(
        [
            "WARNING: canonical spec normalization override is active.",
            "You are responsible for Notion/spec_sync_report workflow compliance.",
            "override_paths:",
            *[f"- {path}" for path in canonical_paths],
        ]
    )
    return True, warning


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    max_files = args.max_files if args.max_files and args.max_files > 0 else 0
    if max_files <= 0 and args.limit and args.limit > 0:
        max_files = args.limit

    input_paths = parse_paths(args.paths)
    if args.baseline_file:
        baseline_path = Path(args.baseline_file)
        if not baseline_path.is_absolute():
            baseline_path = root / baseline_path
        baseline_paths = load_paths_from_baseline(
            root=root,
            baseline_file=baseline_path,
            code_filter={item.strip() for item in args.code_filter if item.strip()},
        )
        input_paths = sorted(set(input_paths + baseline_paths))

    if max_files > 0:
        input_paths = input_paths[:max_files]

    guard_ok, guard_message = validate_canonical_spec_guard(args, input_paths)
    if not guard_ok:
        sys.stderr.write(guard_message + "\n")
        return 2
    if guard_message:
        sys.stderr.write(guard_message + "\n")

    results: list[ConversionResult] = []
    for rel in input_paths:
        absolute = root / rel
        if not absolute.is_file():
            results.append(
                ConversionResult(
                    path=rel,
                    old_encoding="missing",
                    new_encoding="utf-8",
                    action="MISSING_FILE",
                    old_bytes_sha256="",
                    new_bytes_sha256="",
                    old_decoded_sha256="",
                    new_decoded_sha256="",
                    old_line_endings="UNKNOWN",
                    new_line_endings="UNKNOWN",
                    changed=False,
                    status="SKIPPED",
                    message="file not found",
                )
            )
            continue
        results.append(
            normalize_file(
                absolute,
                root,
                args.allow_fallback_encodings,
                args.dry_run,
            )
        )

    markdown_report = render_markdown(results, args.dry_run)
    json_report = json.dumps(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "dry_run": bool(args.dry_run),
            "max_files": max_files,
            "candidate_count": len(results),
            "changed_count": sum(1 for item in results if item.changed),
            "skipped_count": sum(1 for item in results if item.status == "SKIPPED"),
            "results": [asdict(item) for item in results],
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    report_md = Path(args.report_md) if args.report_md else None
    report_json = Path(args.report_json) if args.report_json else None
    write_output(report_md, markdown_report)
    write_output(report_json, json_report)

    sys.stdout.write(markdown_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
