#!/usr/bin/env python3
"""Cross-spec consistency checks for AI_Chatbot reference artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
REF_DIR = ROOT / "docs" / "references"
UIUX_PATH = sorted((ROOT / "docs" / "uiux").glob("CS_RAG_UI_UX_*.xlsx"))[0]

REQ_PATH = REF_DIR / "CS AI Chatbot_Requirements Statement.csv"
SUM_PATH = REF_DIR / "Summary of key features.csv"
DEV_PATH = REF_DIR / "Development environment.csv"
API_XLSX = REF_DIR / "google_ready_api_spec_v0.3_20260216.xlsx"
DB_XLSX = REF_DIR / "CS_AI_CHATBOT_DB.xlsx"

REQ_ID_RE = re.compile(r"\b[A-Z]{2,5}-\d{3}\b")


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    samples: list[str]


def read_req_master() -> set[str]:
    df = pd.read_csv(REQ_PATH, encoding="utf-8-sig")
    return set(df.iloc[:, 0].astype(str).str.strip())


def check_summary_ids(req_master: set[str]) -> CheckResult:
    df = pd.read_csv(SUM_PATH, encoding="utf-8-sig")
    ids = set(df.iloc[:, 5].astype(str).str.strip())
    missing = sorted(ids - req_master)
    return CheckResult(
        name="summary_reqid_subset",
        passed=len(missing) == 0,
        detail=f"summary={len(ids)} missing_in_requirements={len(missing)}",
        samples=missing[:20],
    )


def check_dev_ids(req_master: set[str]) -> CheckResult:
    df = pd.read_csv(DEV_PATH, encoding="utf-8-sig")
    refs: set[str] = set()
    for v in df.iloc[:, 6].astype(str):
        refs.update(REQ_ID_RE.findall(v))
    missing = sorted(refs - req_master)
    return CheckResult(
        name="dev_reqid_subset",
        passed=len(missing) == 0,
        detail=f"dev_refs={len(refs)} missing_in_requirements={len(missing)}",
        samples=missing[:20],
    )


def check_api_note_ids(req_master: set[str]) -> CheckResult:
    wb = load_workbook(API_XLSX, data_only=False, read_only=True)
    ws = wb.worksheets[1]  # 전체API목록
    refs: set[str] = set()
    for r in range(2, 600):
        note = ws.cell(r, 11).value
        if isinstance(note, str) and "ReqID" in note:
            refs.update(REQ_ID_RE.findall(note))
    missing = sorted(refs - req_master)
    return CheckResult(
        name="api_note_reqid_subset",
        passed=len(missing) == 0,
        detail=f"api_note_refs={len(refs)} missing_in_requirements={len(missing)}",
        samples=missing[:20],
    )


def check_uiux_91_ids(req_master: set[str]) -> CheckResult:
    wb = load_workbook(UIUX_PATH, data_only=False, read_only=True)
    ws = next(ws for ws in wb.worksheets if ws.title.startswith("91_"))
    ids: set[str] = set()
    for r in range(4, min(ws.max_row, 4000) + 1):
        v = ws.cell(r, 1).value
        if isinstance(v, str):
            t = v.strip()
            if re.match(r"^[A-Z]{2,5}-\d{3}$", t):
                ids.add(t)
    missing = sorted(ids - req_master)
    return CheckResult(
        name="uiux91_reqid_subset",
        passed=len(missing) == 0,
        detail=f"uiux91_refs={len(ids)} missing_in_requirements={len(missing)}",
        samples=missing[:20],
    )


def _collect_texts() -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []

    for path in [REQ_PATH, SUM_PATH, DEV_PATH]:
        df = pd.read_csv(path, encoding="utf-8-sig")
        for i, row in df.astype(str).iterrows():
            texts.append((f"{path.name}:row{i+2}", " | ".join(row.tolist())))

    api_wb = load_workbook(API_XLSX, data_only=False, read_only=True)
    api_ws = api_wb.worksheets[1]
    for r in range(2, 600):
        for c in [8, 11]:
            v = api_ws.cell(r, c).value
            if isinstance(v, str) and v.strip():
                texts.append((f"{API_XLSX.name}:r{r}c{c}", v))

    db_wb = load_workbook(DB_XLSX, data_only=False, read_only=True)
    for ws in db_wb.worksheets[:20]:
        for r in range(1, min(ws.max_row, 80) + 1):
            for c in range(1, 8):
                v = ws.cell(r, c).value
                if isinstance(v, str) and v.strip():
                    texts.append((f"{DB_XLSX.name}:{ws.title}!{r},{c}", v))
    return texts


def check_secret_terms() -> CheckResult:
    # Allow alias wording only in this exact phrase.
    allow_phrase = "alias: key_ref/api_key_ref"
    forbidden_hits: list[str] = []
    for loc, text in _collect_texts():
        t = text.lower()
        if "key_ref" in t or "api_key_ref" in t:
            if allow_phrase in t:
                continue
            forbidden_hits.append(loc)
    return CheckResult(
        name="secret_ref_standard",
        passed=len(forbidden_hits) == 0,
        detail=f"forbidden_key_ref_hits={len(forbidden_hits)}",
        samples=forbidden_hits[:20],
    )


def check_role_standard() -> CheckResult:
    wb = load_workbook(API_XLSX, data_only=False, read_only=True)
    ws = wb.worksheets[1]
    roles = set()
    for r in range(2, 600):
        role = ws.cell(r, 10).value
        if isinstance(role, str) and role.strip():
            roles.add(role.strip())
    allowed = {"AGENT", "CUSTOMER", "ADMIN", "OPS", "SYSTEM"}
    extra = sorted(roles - allowed)
    return CheckResult(
        name="role_standard",
        passed=len(extra) == 0,
        detail=f"roles={sorted(roles)}",
        samples=extra,
    )


def check_access_level_standard() -> CheckResult:
    wb = load_workbook(API_XLSX, data_only=False, read_only=True)
    ws = wb.worksheets[1]
    allowed = {"PUBLIC", "AUTHENTICATED"}
    expected = {
        ("POST", "/v1/auth/login"): "PUBLIC",
        ("POST", "/v1/auth/refresh"): "PUBLIC",
        ("POST", "/v1/auth/logout"): "AUTHENTICATED",
    }
    found: set[str] = set()
    issues: list[str] = []
    pattern = re.compile(r"access_level\s*=\s*([A-Z_]+)")
    for r in range(2, 600):
        method = ws.cell(r, 5).value
        endpoint = ws.cell(r, 6).value
        role = ws.cell(r, 10).value
        note = ws.cell(r, 11).value
        role_text = role.strip() if isinstance(role, str) else ""
        if role_text in allowed:
            issues.append(f"role_column_misuse:r{r}:{role_text}")
        note_text = note if isinstance(note, str) else ""
        tokens = pattern.findall(note_text)
        for token in tokens:
            found.add(token)
            if token not in allowed:
                issues.append(f"invalid_access_level:r{r}:{token}")
        key = (str(method).strip() if method else "", str(endpoint).strip() if endpoint else "")
        if key in expected and expected[key] not in tokens:
            issues.append(f"missing_access_level:r{r}:{key[0]} {key[1]} expected={expected[key]}")
    return CheckResult(
        name="access_level_standard",
        passed=len(issues) == 0,
        detail=f"access_levels={sorted(found)}",
        samples=issues[:20],
    )


def check_sse_standard_terms() -> CheckResult:
    bad_hits: list[str] = []
    for loc, text in _collect_texts():
        low = text.lower()
        if "token/chunk" in low:
            bad_hits.append(loc)
    return CheckResult(
        name="sse_event_term_standard",
        passed=len(bad_hits) == 0,
        detail=f"token_chunk_occurrences={len(bad_hits)}",
        samples=bad_hits[:20],
    )


def check_uiux_94_placeholder() -> CheckResult:
    wb = load_workbook(UIUX_PATH, data_only=False, read_only=True)
    ws = next(ws for ws in wb.worksheets if ws.title.startswith("94_"))
    bad_rows: list[str] = []
    for r in range(4, min(ws.max_row, 3000) + 1):
        item_type = str(ws.cell(r, 1).value).strip()
        item_key = str(ws.cell(r, 2).value).strip()
        if item_type in {"ReqID", "API", "DB"} and item_key in {"", "-"}:
            bad_rows.append(f"row={r} type={item_type} key={item_key!r}")
    return CheckResult(
        name="uiux94_no_placeholder_keys",
        passed=len(bad_rows) == 0,
        detail=f"placeholder_rows={len(bad_rows)}",
        samples=bad_rows[:20],
    )


def main() -> None:
    req_master = read_req_master()
    checks = [
        check_summary_ids(req_master),
        check_dev_ids(req_master),
        check_api_note_ids(req_master),
        check_uiux_91_ids(req_master),
        check_secret_terms(),
        check_role_standard(),
        check_access_level_standard(),
        check_sse_standard_terms(),
        check_uiux_94_placeholder(),
    ]

    pass_count = sum(1 for c in checks if c.passed)
    fail_count = len(checks) - pass_count
    output = {
        "pass_count": pass_count,
        "fail_count": fail_count,
        "checks": [asdict(c) for c in checks],
    }

    out_path = ROOT / "docs" / "uiux" / "reports" / "spec_consistency_check_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PASS={pass_count} FAIL={fail_count}")
    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"[{status}] {c.name}: {c.detail}")
        if c.samples:
            print(f"  samples: {c.samples[:5]}")
    print(f"report: {out_path}")


if __name__ == "__main__":
    main()
