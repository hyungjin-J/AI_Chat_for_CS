#!/usr/bin/env python3
"""Cross-spec consistency checks anchored on Requirements ReqID SSOT."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


REQ_ID_STRICT_RE = re.compile(r"\b[A-Z]{2,5}-\d{3}\b")
REQ_ID_LAX_RE = re.compile(r"\b[A-Z]{2,5}-[A-Za-z0-9]{3}\b")
REQID_TAG_RE = re.compile(r"ReqID\+?\s*:\s*([^\n\r;]+)", re.IGNORECASE)
SSE_EVENT_RE = re.compile(r"\b(token|tool|citation|done|error|heartbeat|safe_response)\b", re.IGNORECASE)

ROLE_TAXONOMY = {"AGENT", "CUSTOMER", "ADMIN", "OPS", "SYSTEM"}
SSE_EVENT_SET = {"token", "tool", "citation", "done", "error", "heartbeat", "safe_response"}
PLACEHOLDER_VALUES = {"", "-", "N/A", "NA", "NONE", "NULL"}

# Keep Korean labels as escapes to avoid shell/codepage drift on Windows.
KOR_REQ_ID = "\uc694\uad6c\uc0ac\ud56dID"      # 요구사항ID
KOR_API_LIST = "\uc804\uccb4API\ubaa9\ub85d"   # 전체API목록
KOR_NOTE = "\ube44\uace0"                      # 비고
KOR_ROLE = "\uad8c\ud55c"                      # 권한


@dataclass
class Violation:
    code: str
    file: str
    location: str
    token: str
    message: str


def normalize(path: str) -> str:
    return path.replace("\\", "/").strip()


def to_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return normalize(path.as_posix())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-spec consistency checks (ReqID SSOT + terminology)")
    parser.add_argument("--root", default=".")
    parser.add_argument("--requirements", default="docs/references/CS AI Chatbot_Requirements Statement.csv")
    parser.add_argument("--summary", default="docs/references/Summary of key features.csv")
    parser.add_argument("--development", default="docs/references/Development environment.csv")
    parser.add_argument("--api-workbook", default="docs/references/google_ready_api_spec_v0.3_20260216.xlsx")
    parser.add_argument("--api-sheet", default=KOR_API_LIST)
    parser.add_argument("--db-workbook", default="docs/references/CS_AI_CHATBOT_DB.xlsx")
    parser.add_argument(
        "--uiux-workbook",
        help="Optional explicit UI/UX workbook path. If omitted, the first docs/uiux/CS_RAG_UI_UX_*.xlsx is used.",
    )
    parser.add_argument("--uiux-glob", default="docs/uiux/CS_RAG_UI_UX_*.xlsx")
    parser.add_argument("--report-json", default="docs/uiux/reports/spec_consistency_check_report.json")
    parser.add_argument("--report-txt")
    parser.add_argument("--pass-artifact", help="Optional path for concise PASS summary text artifact.")
    return parser.parse_args()


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / value


def read_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file_pointer:
        rows = list(csv.reader(file_pointer))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def find_column(headers: list[str], candidates: list[str]) -> int | None:
    normalized = [header.strip().lower() for header in headers]
    normalized_candidates = [candidate.strip().lower() for candidate in candidates]

    for candidate in normalized_candidates:
        if candidate in normalized:
            return normalized.index(candidate)

    for candidate in normalized_candidates:
        for index, header in enumerate(normalized):
            if candidate in header:
                return index
    return None


def extract_reqid_tokens(value: str) -> tuple[list[str], list[str]]:
    strict_tokens = sorted(set(REQ_ID_STRICT_RE.findall(value)))
    lax_tokens = sorted(set(REQ_ID_LAX_RE.findall(value)))
    malformed_tokens = sorted(token for token in lax_tokens if token not in strict_tokens)
    return strict_tokens, malformed_tokens


def extract_prefix(token: str) -> str:
    return token.split("-", 1)[0] if "-" in token else ""


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return "UNKNOWN"
    return result.stdout.strip() or "UNKNOWN"


def add_violation(
    collection: list[Violation],
    code: str,
    file_path: Path,
    root: Path,
    location: str,
    token: str,
    message: str,
) -> None:
    collection.append(
        Violation(
            code=code,
            file=to_rel(file_path, root),
            location=location,
            token=token,
            message=message,
        )
    )


def load_requirements(root: Path, requirements_path: Path, violations: list[Violation]) -> set[str]:
    headers, rows = read_csv_rows(requirements_path)
    if not headers:
        add_violation(
            violations,
            "REQID_REQUIREMENTS_EMPTY",
            requirements_path,
            root,
            "file",
            "",
            "requirements CSV is empty",
        )
        return set()

    reqid_col = find_column(headers, ["ReqID", KOR_REQ_ID])
    if reqid_col is None:
        reqid_col = 0

    reqids: set[str] = set()
    seen: dict[str, int] = {}
    for row_number, row in enumerate(rows, start=2):
        value = row[reqid_col].strip() if reqid_col < len(row) else ""
        if not value:
            continue
        if not REQ_ID_STRICT_RE.fullmatch(value):
            add_violation(
                violations,
                "REQID_REQUIREMENTS_MALFORMED",
                requirements_path,
                root,
                f"row={row_number}",
                value,
                "requirements ReqID must match [A-Z]{2,5}-\\d{3}",
            )
            continue
        reqids.add(value)
        seen[value] = seen.get(value, 0) + 1

    for token, count in sorted(seen.items()):
        if count > 1:
            add_violation(
                violations,
                "REQID_REQUIREMENTS_DUPLICATE",
                requirements_path,
                root,
                "ReqID",
                token,
                f"duplicate ReqID detected: {count}",
            )
    return reqids


def validate_summary(root: Path, summary_path: Path, req_master: set[str], violations: list[Violation]) -> int:
    headers, rows = read_csv_rows(summary_path)
    if not headers:
        add_violation(
            violations,
            "REQID_SUMMARY_EMPTY",
            summary_path,
            root,
            "file",
            "",
            "summary CSV is empty",
        )
        return 0

    reqid_col = find_column(headers, [KOR_REQ_ID, "ReqID"])
    if reqid_col is None:
        add_violation(
            violations,
            "REQID_SUMMARY_COLUMN_MISSING",
            summary_path,
            root,
            "header",
            KOR_REQ_ID,
            "summary CSV missing 요구사항ID/ReqID column",
        )
        return 0

    token_count = 0
    for row_number, row in enumerate(rows, start=2):
        raw_value = row[reqid_col].strip() if reqid_col < len(row) else ""
        if not raw_value:
            continue

        strict_tokens, malformed_tokens = extract_reqid_tokens(raw_value)
        token_count += len(strict_tokens)
        for token in strict_tokens:
            if token not in req_master:
                add_violation(
                    violations,
                    "REQID_SUMMARY_UNKNOWN",
                    summary_path,
                    root,
                    f"row={row_number}",
                    token,
                    "summary 요구사항ID must exist in Requirements SSOT",
                )
        for token in malformed_tokens:
            add_violation(
                violations,
                "REQID_SUMMARY_MALFORMED",
                summary_path,
                root,
                f"row={row_number}",
                token,
                "summary 요구사항ID contains malformed ReqID token",
            )

        if not strict_tokens and not malformed_tokens and raw_value.upper() not in PLACEHOLDER_VALUES:
            add_violation(
                violations,
                "REQID_SUMMARY_MALFORMED",
                summary_path,
                root,
                f"row={row_number}",
                raw_value,
                "summary 요구사항ID cell has no valid ReqID token",
            )
    return token_count


def select_api_sheet(workbook_path: Path, preferred_sheet_name: str):
    workbook = load_workbook(workbook_path, data_only=False, read_only=True)
    preferred_normalized = preferred_sheet_name.strip().lower()

    for worksheet in workbook.worksheets:
        if worksheet.title.strip().lower() == preferred_normalized:
            return workbook, worksheet

    # Fallback for localization/codepage edge cases.
    for worksheet in workbook.worksheets:
        title = worksheet.title.strip().lower()
        if "api" in title and ("list" in title or "\ubaa9\ub85d" in worksheet.title):  # 목록
            return workbook, worksheet

    workbook.close()
    raise ValueError(f"sheet '{preferred_sheet_name}' not found in {workbook_path.as_posix()}")


def validate_api_notes_and_roles(
    root: Path,
    api_workbook: Path,
    api_sheet: str,
    req_master: set[str],
    violations: list[Violation],
) -> tuple[int, set[str], list[tuple[str, str, str]]]:
    workbook, worksheet = select_api_sheet(api_workbook, api_sheet)
    header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), None) or ()
    headers = [str(value).strip() if value is not None else "" for value in header_row]
    note_col = find_column(headers, [KOR_NOTE, "remark", "note"])
    role_col = find_column(headers, ["role", KOR_ROLE])
    if note_col is None:
        add_violation(
            violations,
            "REQID_API_COLUMN_MISSING",
            api_workbook,
            root,
            "header",
            KOR_NOTE,
            "API sheet missing 비고/remark/note column",
        )
        workbook.close()
        return 0, set(), []

    scan_max_col = max(note_col, role_col if role_col is not None else 0) + 1
    token_count = 0
    role_tokens: set[str] = set()
    corpus: list[tuple[str, str, str]] = []

    for row_number, row_values in enumerate(
        worksheet.iter_rows(
            min_row=2,
            max_row=worksheet.max_row,
            min_col=1,
            max_col=scan_max_col,
            values_only=True,
        ),
        start=2,
    ):
        if role_col is not None and role_col < len(row_values):
            raw_role = row_values[role_col]
            if isinstance(raw_role, str) and raw_role.strip():
                normalized_roles = re.split(r"[,/| ]+", raw_role.strip().upper())
                for token in normalized_roles:
                    if token:
                        role_tokens.add(token)

        note_cell = row_values[note_col] if note_col < len(row_values) else None
        if isinstance(note_cell, str) and note_cell.strip():
            cell_ref = f"{get_column_letter(note_col + 1)}{row_number}"
            corpus.append((to_rel(api_workbook, root), f"{worksheet.title}!{cell_ref}", note_cell))
        if not isinstance(note_cell, str):
            continue

        note_value = note_cell.strip()
        if not note_value or "reqid" not in note_value.lower():
            continue

        cell_ref = f"{get_column_letter(note_col + 1)}{row_number}"
        segments = REQID_TAG_RE.findall(note_value)
        segments_to_scan = segments if segments else [note_value]
        found_in_cell = 0
        malformed_in_cell: set[str] = set()

        for segment in segments_to_scan:
            strict_tokens, malformed_tokens = extract_reqid_tokens(segment)
            token_count += len(strict_tokens)
            found_in_cell += len(strict_tokens)
            for token in strict_tokens:
                if token not in req_master:
                    add_violation(
                        violations,
                        "REQID_API_UNKNOWN",
                        api_workbook,
                        root,
                        f"sheet={worksheet.title} cell={cell_ref}",
                        token,
                        "API 비고 ReqID reference is missing in Requirements SSOT",
                    )
            for token in malformed_tokens:
                malformed_in_cell.add(token)

        for token in sorted(malformed_in_cell):
            add_violation(
                violations,
                "REQID_API_MALFORMED",
                api_workbook,
                root,
                f"sheet={worksheet.title} cell={cell_ref}",
                token,
                "API 비고 contains malformed ReqID token",
            )

        if found_in_cell == 0 and not malformed_in_cell:
            add_violation(
                violations,
                "REQID_API_TAG_WITHOUT_TOKEN",
                api_workbook,
                root,
                f"sheet={worksheet.title} cell={cell_ref}",
                note_value,
                "API 비고 contains ReqID marker but no ReqID token",
            )

    workbook.close()
    return token_count, role_tokens, corpus


def iter_workbook_corpus_rows(
    worksheet,
    max_row: int,
    max_col: int,
):
    for row_number, row_values in enumerate(
        worksheet.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_col, values_only=True),
        start=1,
    ):
        yield row_number, row_values


def scan_workbook_for_reqids(
    root: Path,
    workbook_path: Path,
    req_master: set[str],
    violations: list[Violation],
    code_prefix: str,
) -> tuple[int, list[tuple[str, str, str]]]:
    workbook = load_workbook(workbook_path, data_only=False, read_only=True)
    token_count = 0
    corpus: list[tuple[str, str, str]] = []
    req_prefixes = {extract_prefix(token) for token in req_master}

    for worksheet in workbook.worksheets:
        if code_prefix == "UIUX" and not worksheet.title.startswith(("91_", "92_", "93_", "94_")):
            continue

        if code_prefix == "UIUX":
            max_row = min(worksheet.max_row, 1500)
            max_col = min(worksheet.max_column, 16)
        elif code_prefix == "DB":
            max_row = min(worksheet.max_row, 800)
            max_col = min(worksheet.max_column, 20)
        else:
            max_row = min(worksheet.max_row, 5000)
            max_col = min(worksheet.max_column, 40)

        reqid_columns: set[int] = set()
        for row_number, row_values in iter_workbook_corpus_rows(
            worksheet=worksheet,
            max_row=min(5, max_row),
            max_col=max_col,
        ):
            _ = row_number
            for col_index, value in enumerate(row_values, start=1):
                if not isinstance(value, str):
                    continue
                header_text = value.strip().lower()
                if "reqid" in header_text or KOR_REQ_ID.lower() in header_text:
                    reqid_columns.add(col_index)

        for row_number, row_values in iter_workbook_corpus_rows(
            worksheet=worksheet,
            max_row=max_row,
            max_col=max_col,
        ):
            for col_index, value in enumerate(row_values, start=1):
                if not isinstance(value, str):
                    continue
                text = value.strip()
                if not text:
                    continue

                location = f"{worksheet.title}!{get_column_letter(col_index)}{row_number}"
                corpus.append((to_rel(workbook_path, root), location, text))

                strict_tokens, malformed_tokens = extract_reqid_tokens(text)
                if not strict_tokens and not malformed_tokens:
                    continue

                has_explicit_reqid_marker = "reqid" in text.lower()
                has_reqid_marker = has_explicit_reqid_marker or col_index in reqid_columns
                filtered_strict = [token for token in strict_tokens if extract_prefix(token) in req_prefixes]
                filtered_malformed = [token for token in malformed_tokens if extract_prefix(token) in req_prefixes]

                if has_reqid_marker:
                    strict_to_validate = strict_tokens
                    malformed_to_validate = malformed_tokens if has_explicit_reqid_marker else filtered_malformed
                else:
                    strict_to_validate = filtered_strict
                    malformed_to_validate = []

                if not strict_to_validate and not malformed_to_validate:
                    continue

                for token in strict_to_validate:
                    token_count += 1
                    if token not in req_master:
                        add_violation(
                            violations,
                            f"REQID_{code_prefix}_UNKNOWN",
                            workbook_path,
                            root,
                            f"sheet={location}",
                            token,
                            "ReqID token was found but is missing in Requirements SSOT",
                        )
                for token in malformed_to_validate:
                    add_violation(
                        violations,
                        f"REQID_{code_prefix}_MALFORMED",
                        workbook_path,
                        root,
                        f"sheet={location}",
                        token,
                        "Malformed ReqID-like token detected",
                    )

    workbook.close()
    return token_count, corpus


def scan_csv_for_reqids(
    root: Path,
    csv_path: Path,
    req_master: set[str],
    violations: list[Violation],
    code_prefix: str,
) -> tuple[int, list[tuple[str, str, str]]]:
    headers, rows = read_csv_rows(csv_path)
    token_count = 0
    corpus: list[tuple[str, str, str]] = []
    if not headers:
        return token_count, corpus

    for row_number, row in enumerate(rows, start=2):
        joined = " | ".join(item for item in row if item)
        if not joined.strip():
            continue
        location = f"row={row_number}"
        corpus.append((to_rel(csv_path, root), location, joined))
        if "reqid" not in joined.lower():
            continue

        strict_tokens, malformed_tokens = extract_reqid_tokens(joined)

        for token in strict_tokens:
            token_count += 1
            if token not in req_master:
                add_violation(
                    violations,
                    f"REQID_{code_prefix}_UNKNOWN",
                    csv_path,
                    root,
                    location,
                    token,
                    "ReqID token was found but is missing in Requirements SSOT",
                )
        for token in malformed_tokens:
            add_violation(
                violations,
                f"REQID_{code_prefix}_MALFORMED",
                csv_path,
                root,
                location,
                token,
                "Malformed ReqID-like token detected",
            )
    return token_count, corpus


def collect_csv_corpus(root: Path, csv_path: Path) -> list[tuple[str, str, str]]:
    headers, rows = read_csv_rows(csv_path)
    if not headers:
        return []
    corpus: list[tuple[str, str, str]] = []
    for row_number, row in enumerate(rows, start=2):
        joined = " | ".join(item for item in row if item)
        if not joined.strip():
            continue
        corpus.append((to_rel(csv_path, root), f"row={row_number}", joined))
    return corpus


def validate_terminology(
    root: Path,
    corpus: list[tuple[str, str, str]],
    role_tokens: set[str],
    violations: list[Violation],
) -> dict[str, object]:
    secret_ref_hits = 0
    secret_alias_hits = 0
    sse_found: set[str] = set()

    for _, _, text in corpus:
        lowered = text.lower()
        if "secret_ref" in lowered:
            secret_ref_hits += 1
        if "key_ref" in lowered or "api_key_ref" in lowered:
            secret_alias_hits += 1

        for token in SSE_EVENT_RE.findall(text):
            sse_found.add(token.lower())

    if secret_ref_hits == 0:
        add_violation(
            violations,
            "TERMINOLOGY_SECRET_REF_MISSING",
            root / "docs/references",
            root,
            "corpus",
            "secret_ref",
            "secret_ref terminology was not found in scanned specs",
        )

    unknown_roles = sorted(token for token in role_tokens if token not in ROLE_TAXONOMY)
    for token in unknown_roles:
        add_violation(
            violations,
            "TERMINOLOGY_ROLE_UNKNOWN",
            root / "docs/references",
            root,
            "API role column",
            token,
            "role token is outside ROLE taxonomy AGENT/CUSTOMER/ADMIN/OPS/SYSTEM",
        )

    missing_roles = sorted(ROLE_TAXONOMY - {token for token in role_tokens if token in ROLE_TAXONOMY})
    if missing_roles:
        add_violation(
            violations,
            "TERMINOLOGY_ROLE_MISSING",
            root / "docs/references",
            root,
            "API role column",
            ",".join(missing_roles),
            "one or more ROLE taxonomy strings were not found",
        )

    missing_sse = sorted(SSE_EVENT_SET - sse_found)
    if missing_sse:
        add_violation(
            violations,
            "TERMINOLOGY_SSE_MISSING",
            root / "docs/references",
            root,
            "corpus",
            ",".join(missing_sse),
            "one or more required SSE event terms were not found",
        )

    return {
        "secret_ref_hits": secret_ref_hits,
        "secret_alias_hits": secret_alias_hits,
        "role_tokens_found": sorted(role_tokens),
        "sse_events_found": sorted(sse_found),
    }


def build_pass_artifact(root: Path, output_path: Path, payload: dict[str, object]) -> None:
    lines = [
        f"timestamp_utc={datetime.now(timezone.utc).isoformat()}",
        f"commit={git_head(root)}",
        f"status={payload['status']}",
        f"total_reqids_in_requirements={payload['summary']['total_reqids_in_requirements']}",
        (
            "total_reqid_tokens_found_in_each_spec="
            + json.dumps(payload["summary"]["reqid_token_counts"], ensure_ascii=False, sort_keys=True)
        ),
        f"invalid_tokens_count={payload['summary']['invalid_tokens_count']}",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(path: Path | None, content: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    requirements_path = resolve_path(root, args.requirements)
    summary_path = resolve_path(root, args.summary)
    development_path = resolve_path(root, args.development)
    api_workbook = resolve_path(root, args.api_workbook)
    db_workbook = resolve_path(root, args.db_workbook)

    if args.uiux_workbook:
        uiux_workbook = resolve_path(root, args.uiux_workbook)
    else:
        matches = sorted(root.glob(args.uiux_glob))
        if not matches:
            raise FileNotFoundError(f"UI/UX workbook not found by glob: {args.uiux_glob}")
        uiux_workbook = matches[0]

    report_json_path = resolve_path(root, args.report_json) if args.report_json else None
    report_txt_path = resolve_path(root, args.report_txt) if args.report_txt else None
    pass_artifact_path = resolve_path(root, args.pass_artifact) if args.pass_artifact else None

    violations: list[Violation] = []
    req_master = load_requirements(root, requirements_path, violations)

    summary_count = validate_summary(root, summary_path, req_master, violations)
    development_count, development_corpus = scan_csv_for_reqids(
        root=root,
        csv_path=development_path,
        req_master=req_master,
        violations=violations,
        code_prefix="DEVELOPMENT",
    )
    api_count, api_role_tokens, api_corpus = validate_api_notes_and_roles(
        root=root,
        api_workbook=api_workbook,
        api_sheet=args.api_sheet,
        req_master=req_master,
        violations=violations,
    )
    uiux_count, uiux_corpus = scan_workbook_for_reqids(
        root=root,
        workbook_path=uiux_workbook,
        req_master=req_master,
        violations=violations,
        code_prefix="UIUX",
    )
    db_count, db_corpus = scan_workbook_for_reqids(
        root=root,
        workbook_path=db_workbook,
        req_master=req_master,
        violations=violations,
        code_prefix="DB",
    )

    req_count = len(req_master)
    req_corpus = collect_csv_corpus(root, requirements_path)
    summary_corpus = collect_csv_corpus(root, summary_path)

    corpus = req_corpus + summary_corpus + development_corpus + api_corpus + uiux_corpus + db_corpus
    terminology_summary = validate_terminology(
        root=root,
        corpus=corpus,
        role_tokens=api_role_tokens,
        violations=violations,
    )

    reqid_token_counts = {
        "requirements": req_count,
        "summary": summary_count,
        "development": development_count,
        "api_note": api_count,
        "uiux": uiux_count,
        "db": db_count,
    }
    invalid_tokens_count = sum(1 for violation in violations if violation.code.startswith("REQID_"))

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "commit": git_head(root),
        "summary": {
            "total_reqids_in_requirements": len(req_master),
            "total_reqid_tokens_found_in_each_spec": reqid_token_counts,
            "reqid_token_counts": reqid_token_counts,
            "invalid_tokens_count": invalid_tokens_count,
        },
        "terminology": terminology_summary,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }

    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_report(report_json_path, json_report)

    lines = [
        f"{payload['status']} spec_consistency_check",
        f"total_reqids_in_requirements={payload['summary']['total_reqids_in_requirements']}",
        "total_reqid_tokens_found_in_each_spec="
        + json.dumps(reqid_token_counts, ensure_ascii=False, sort_keys=True),
        f"invalid_tokens_count={invalid_tokens_count}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in violations:
        lines.append(f"[{item.code}] {item.file} {item.location} token={item.token} :: {item.message}")
    text_report = "\n".join(lines) + "\n"

    write_report(report_txt_path, text_report)
    if pass_artifact_path is not None and payload["status"] == "PASS":
        build_pass_artifact(root, pass_artifact_path, payload)

    sys.stdout.write(text_report)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
