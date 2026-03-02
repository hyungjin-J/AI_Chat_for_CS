#!/usr/bin/env python3
"""Run fixed-schema RAG regression cases against API endpoints."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = [
    "case_id",
    "tenant_key",
    "user_role",
    "query",
    "expected_policy_bundle",
    "requires_citation",
    "notes",
]

DEFAULT_DATASET = "eval/datasets/rag_regression_cases.csv"
DEFAULT_OUT_DIR = "eval/out/latest"
DEFAULT_TIMEOUT_SEC = 60

REASON_OK = "OK"
REASON_DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
REASON_INDEXING_INCOMPLETE = "INDEXING_INCOMPLETE"
REASON_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
REASON_THRESHOLD_UNDERSHOOT = "THRESHOLD_UNDERSHOOT"
REASON_METRIC_COMPUTATION_BUG = "METRIC_COMPUTATION_BUG"
REASON_CASE_FAILURE = "CASE_FAILURE"
REASON_NETWORK_UNAVAILABLE = "NETWORK_UNAVAILABLE"
REASON_AUTH_FAILED = "AUTH_FAILED"
REASON_TARGET_UNREACHABLE = "TARGET_UNREACHABLE"

INDEXING_PENDING_STATUSES = {"PENDING", "RUNNING", "RETRY_WAIT"}

PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE),
    re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4})\b"),
    re.compile(r"\b(?:ORDER|ORD|CASE|TICKET)[-_]?\d{4,}\b", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
]

FORBIDDEN_BY_BUNDLE = {
    "CS_STANDARD": [],
    "CS_FAIL_CLOSED_STRICT": ["internal-only", "hidden system prompt", "ignore policy"],
    "CS_POLICY_GUARD": ["developer override approved", "root admin token"],
}


@dataclass
class EvalCase:
    case_id: str
    tenant_key: str
    user_role: str
    query: str
    expected_policy_bundle: str
    requires_citation: int
    notes: str


@dataclass
class CaseResult:
    case_id: str
    tenant_key: str
    user_role: str
    trace_id: str
    status: str
    expected_outcome: str
    reason_code: str
    fail_closed: bool
    answer_contract_pass: bool
    citation_count: int
    requires_citation: int
    citation_covered: bool
    policy_violation: bool
    policy_violation_reasons: list[str]
    latency_ms: float | None
    post_status: int
    stream_status: int
    event_types: list[str]
    error_codes: list[str]
    notes: str
    error_message: str


@dataclass
class LoginResult:
    ok: bool
    token: str
    status: int
    error_code: str
    error_message: str
    trace_id: str


@dataclass
class PreflightResult:
    status: str
    reason_code: str
    reason_detail: str
    tenant_checks: list[dict[str, Any]]
    provider_checks: list[dict[str, Any]]
    admin_tokens: dict[str, str]


class HttpClient:
    def __init__(self, base_url: str, timeout_sec: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def request_json(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> tuple[int, str, Any]:
        url = f"{self.base_url}{path}"
        data: bytes | None = None
        req_headers = dict(headers)
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url=url, method=method.upper(), data=data, headers=req_headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                text = response.read().decode("utf-8", errors="replace")
                return response.getcode(), text, _try_json(text)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return exc.code, text, _try_json(text)

    def read_sse(self, path: str, headers: dict[str, str]) -> tuple[int, list[dict[str, Any]], str, float | None]:
        url = f"{self.base_url}{path}"
        req_headers = dict(headers)
        req_headers.setdefault("Accept", "text/event-stream")
        request = urllib.request.Request(url=url, method="GET", headers=req_headers)

        events: list[dict[str, Any]] = []
        raw_lines: list[str] = []
        current_id = ""
        current_event = ""
        current_data: list[str] = []
        first_payload_ms: float | None = None
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            status = response.getcode()
            for raw in response:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                raw_lines.append(line)
                if line.startswith("id:"):
                    current_id = line[3:].strip()
                    continue
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    continue
                if line.startswith("data:"):
                    current_data.append(line[5:].strip())
                    continue
                if line == "":
                    if current_event:
                        data_text = "\n".join(current_data)
                        if first_payload_ms is None:
                            first_payload_ms = (time.perf_counter() - started) * 1000.0
                        payload = _try_json(data_text)
                        if isinstance(payload, str):
                            nested = _try_json(payload)
                            if nested is not None:
                                payload = nested
                        events.append(
                            {
                                "id": current_id,
                                "event": current_event,
                                "data": data_text,
                                "payload": payload if payload is not None else data_text,
                            }
                        )
                    current_id = ""
                    current_event = ""
                    current_data = []
        return status, events, "\n".join(raw_lines), first_payload_ms


def _try_json(text: str) -> Any:
    candidate = (text or "").strip()
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _mask(s: str) -> str:
    value = s
    value = re.sub(r"(?i)access_token\s*[:=]\s*[^,\s]+", "access_token=<REDACTED>", value)
    value = re.sub(r"(?i)refresh_token\s*[:=]\s*[^,\s]+", "refresh_token=<REDACTED>", value)
    return value


def _parse_notes(notes: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for token in (notes or "").split(";"):
        part = token.strip()
        if not part or "=" not in part:
            continue
        key, raw = part.split("=", 1)
        parsed[key.strip().lower()] = raw.strip()
    return parsed


VISIBLE_TEXT_KEYS = {
    "text",
    "delta",
    "content",
    "answer",
    "message",
    "safe_response",
    "excerpt",
    "excerpt_masked",
    "summary",
    "reason",
    "detail",
}


def _collect_visible_text(payload: Any) -> list[str]:
    values: list[str] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_lower = str(key).strip().lower()
                if isinstance(value, str):
                    if key_lower in VISIBLE_TEXT_KEYS:
                        values.append(value)
                elif isinstance(value, (dict, list)):
                    _walk(value)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    return values


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return float(round(ordered[index], 3))


def _role_credentials(args: argparse.Namespace, role: str) -> tuple[str, str]:
    role_code = (role or "").strip().upper()
    if role_code == "AGENT":
        return args.agent_login_id, args.agent_password
    if role_code == "ADMIN":
        return args.admin_login_id, args.admin_password
    if role_code == "OPS":
        return args.ops_login_id, args.ops_password
    raise ValueError(f"unsupported user_role for eval: {role_code}")


def _extract_error_code(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("error_code")
        if value is not None:
            return str(value)
    return ""


def _headers(trace_id: str, tenant_key: str, token: str | None = None, with_idempotency: bool = False) -> dict[str, str]:
    headers = {
        "X-Trace-Id": trace_id,
        "X-Tenant-Key": tenant_key,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if with_idempotency:
        headers["Idempotency-Key"] = str(uuid.uuid4())
    return headers


def _tenant_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _is_provider_code(error_code: str) -> bool:
    code = (error_code or "").strip().upper()
    return code in {"SYS-003-503"}


def load_dataset(dataset_path: Path) -> list[EvalCase]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset not found: {dataset_path.as_posix()}")
    with dataset_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError("dataset header missing")
        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"dataset missing required columns: {missing}")
        rows: list[EvalCase] = []
        for row in reader:
            item = EvalCase(
                case_id=(row.get("case_id") or "").strip(),
                tenant_key=(row.get("tenant_key") or "").strip(),
                user_role=(row.get("user_role") or "").strip().upper(),
                query=(row.get("query") or "").strip(),
                expected_policy_bundle=(row.get("expected_policy_bundle") or "").strip(),
                requires_citation=int((row.get("requires_citation") or "0").strip()),
                notes=(row.get("notes") or "").strip(),
            )
            if not item.case_id or not item.tenant_key or not item.user_role or not item.query:
                raise ValueError(f"invalid dataset row (mandatory value missing): {row}")
            rows.append(item)
        return rows


def login_with_credentials(
    client: HttpClient,
    tenant_key: str,
    login_id: str,
    password: str,
    channel_id: str,
    nonce: str,
) -> LoginResult:
    trace_id = str(uuid.uuid4())
    try:
        status, text, payload = client.request_json(
            "POST",
            "/v1/auth/login",
            _headers(trace_id, tenant_key, with_idempotency=True),
            body={
                "login_id": login_id,
                "password": password,
                "channel_id": channel_id,
                "client_nonce": nonce,
            },
        )
    except urllib.error.URLError as exc:
        return LoginResult(
            ok=False,
            token="",
            status=0,
            error_code="",
            error_message=f"network_error={_mask(str(exc.reason))}",
            trace_id=trace_id,
        )

    if status == 201 and isinstance(payload, dict):
        access_token = payload.get("access_token")
        if isinstance(access_token, str) and access_token.strip():
            return LoginResult(
                ok=True,
                token=access_token.strip(),
                status=status,
                error_code="",
                error_message="",
                trace_id=trace_id,
            )
    return LoginResult(
        ok=False,
        token="",
        status=status,
        error_code=_extract_error_code(payload),
        error_message=f"login_failed status={status} body={_mask(text)[:240]}",
        trace_id=trace_id,
    )


def probe_base_url(client: HttpClient, tenant_key: str) -> tuple[bool, str]:
    trace_id = str(uuid.uuid4())
    try:
        status, text, _payload = client.request_json(
            "GET",
            "/health",
            _headers(trace_id, tenant_key),
            body=None,
        )
    except urllib.error.URLError as exc:
        return False, _mask(str(exc.reason))
    if status == 0:
        return False, _mask(text)
    return True, f"health_status={status}"


def run_seed_preflight(args: argparse.Namespace, tenant_key: str) -> dict[str, Any]:
    try:
        import seed_kb_minimal  # type: ignore
    except Exception as exc:  # pragma: no cover - defensive import failure
        return {
            "status": "FAIL",
            "reason_code": REASON_METRIC_COMPUTATION_BUG,
            "reason_detail": f"seed_module_import_failed error={exc.__class__.__name__}",
        }

    try:
        report = seed_kb_minimal.seed_minimal_kb(
            base_url=args.base_url,
            tenant_key=tenant_key,
            min_docs=args.min_approved_docs,
            timeout_sec=args.timeout_sec,
            index_timeout_sec=args.seed_index_timeout_sec,
            poll_interval_sec=args.seed_poll_interval_sec,
            admin_login_id=args.admin_login_id,
            admin_password=args.admin_password,
        )
    except Exception as exc:  # pragma: no cover - defensive always-write path
        return {
            "status": "FAIL",
            "reason_code": REASON_METRIC_COMPUTATION_BUG,
            "reason_detail": f"seed_execution_failed error={exc.__class__.__name__}",
        }

    return {
        "status": str(report.get("status", "FAIL")).strip().upper(),
        "reason_code": str(report.get("reason_code", REASON_DATA_UNAVAILABLE)).strip().upper(),
        "reason_detail": _mask(str(report.get("reason_detail", ""))),
        "ready_count": int(report.get("ready_count", 0) or 0),
        "documents": report.get("documents", []),
    }


def run_preflight(client: HttpClient, args: argparse.Namespace, cases: list[EvalCase]) -> PreflightResult:
    unique_tenants = sorted({case.tenant_key for case in cases})
    tenant_checks: list[dict[str, Any]] = []
    provider_checks: list[dict[str, Any]] = []
    admin_tokens: dict[str, str] = {}

    if not unique_tenants:
        return PreflightResult(
            status="FAIL",
            reason_code=REASON_DATA_UNAVAILABLE,
            reason_detail="dataset_contains_no_tenants",
            tenant_checks=[],
            provider_checks=[],
            admin_tokens={},
        )

    reachable, reachability_detail = probe_base_url(client, unique_tenants[0])
    if not reachable:
        return PreflightResult(
            status="FAIL",
            reason_code=REASON_TARGET_UNREACHABLE,
            reason_detail=f"base_url_unreachable reason={reachability_detail}",
            tenant_checks=[],
            provider_checks=[],
            admin_tokens={},
        )

    for tenant_key in unique_tenants:
        admin_login = login_with_credentials(
            client=client,
            tenant_key=tenant_key,
            login_id=args.admin_login_id,
            password=args.admin_password,
            channel_id="eval-preflight",
            nonce=f"eval-preflight-admin-{tenant_key}",
        )
        if not admin_login.ok:
            detail = (
                f"admin_login_failed tenant={tenant_key} status={admin_login.status} "
                f"error_code={admin_login.error_code} message={admin_login.error_message}"
            )
            reason_code = REASON_DATA_UNAVAILABLE
            if admin_login.status == 0:
                reason_code = REASON_TARGET_UNREACHABLE
            elif admin_login.status in (401, 403):
                reason_code = REASON_AUTH_FAILED
            return PreflightResult(
                status="FAIL",
                reason_code=reason_code,
                reason_detail=detail,
                tenant_checks=tenant_checks,
                provider_checks=provider_checks,
                admin_tokens=admin_tokens,
            )
        admin_tokens[tenant_key] = admin_login.token

        docs_trace = str(uuid.uuid4())
        docs_path = (
            f"/v1/admin/kb/documents?{urllib.parse.urlencode({'status': 'approved', 'limit': 200, 'offset': 0})}"
        )
        try:
            docs_status, docs_text, docs_payload = client.request_json(
                "GET",
                docs_path,
                _headers(docs_trace, tenant_key, token=admin_login.token),
                body=None,
            )
        except urllib.error.URLError as exc:
            detail = f"kb_documents_network_error tenant={tenant_key} reason={_mask(str(exc.reason))}"
            return PreflightResult(
                status="FAIL",
                reason_code=REASON_TARGET_UNREACHABLE,
                reason_detail=detail,
                tenant_checks=tenant_checks,
                provider_checks=provider_checks,
                admin_tokens=admin_tokens,
            )

        if docs_status != 200:
            detail = f"kb_documents_status tenant={tenant_key} status={docs_status} body={_mask(docs_text)[:240]}"
            return PreflightResult(
                status="FAIL",
                reason_code=REASON_DATA_UNAVAILABLE,
                reason_detail=detail,
                tenant_checks=tenant_checks,
                provider_checks=provider_checks,
                admin_tokens=admin_tokens,
            )

        approved_items = _tenant_items(docs_payload)
        indexed_approved = [
            item for item in approved_items if str(item.get("pipeline_status", "")).strip().upper() == "INDEXED"
        ]
        tenant_check: dict[str, Any] = {
            "tenant_key": tenant_key,
            "approved_count": len(approved_items),
            "approved_indexed_count": len(indexed_approved),
        }

        if len(indexed_approved) < args.min_approved_docs:
            tenant_check["auto_seed_attempted"] = not args.no_auto_seed
            if not args.no_auto_seed:
                seed_report = run_seed_preflight(args, tenant_key)
                tenant_check["auto_seed"] = {
                    "status": seed_report.get("status"),
                    "reason_code": seed_report.get("reason_code"),
                    "reason_detail": seed_report.get("reason_detail"),
                    "ready_count": seed_report.get("ready_count", 0),
                }
                if str(seed_report.get("status", "FAIL")).upper() != "PASS":
                    seed_reason_code = str(seed_report.get("reason_code", REASON_DATA_UNAVAILABLE)).upper()
                    seed_reason_detail = str(seed_report.get("reason_detail", "seed_failed"))
                    return PreflightResult(
                        status="FAIL",
                        reason_code=seed_reason_code,
                        reason_detail=f"auto_seed_failed tenant={tenant_key} detail={seed_reason_detail}",
                        tenant_checks=tenant_checks + [tenant_check],
                        provider_checks=provider_checks,
                        admin_tokens=admin_tokens,
                    )

                docs_trace = str(uuid.uuid4())
                try:
                    docs_status, docs_text, docs_payload = client.request_json(
                        "GET",
                        docs_path,
                        _headers(docs_trace, tenant_key, token=admin_login.token),
                        body=None,
                    )
                except urllib.error.URLError as exc:
                    detail = (
                        f"kb_documents_post_seed_network_error tenant={tenant_key} reason={_mask(str(exc.reason))}"
                    )
                    return PreflightResult(
                        status="FAIL",
                        reason_code=REASON_TARGET_UNREACHABLE,
                        reason_detail=detail,
                        tenant_checks=tenant_checks + [tenant_check],
                        provider_checks=provider_checks,
                        admin_tokens=admin_tokens,
                    )
                if docs_status != 200:
                    detail = (
                        f"kb_documents_post_seed_status tenant={tenant_key} status={docs_status} "
                        f"body={_mask(docs_text)[:240]}"
                    )
                    return PreflightResult(
                        status="FAIL",
                        reason_code=REASON_DATA_UNAVAILABLE,
                        reason_detail=detail,
                        tenant_checks=tenant_checks + [tenant_check],
                        provider_checks=provider_checks,
                        admin_tokens=admin_tokens,
                    )
                approved_items = _tenant_items(docs_payload)
                indexed_approved = [
                    item for item in approved_items if str(item.get("pipeline_status", "")).strip().upper() == "INDEXED"
                ]
                tenant_check["approved_count"] = len(approved_items)
                tenant_check["approved_indexed_count"] = len(indexed_approved)

        if len(indexed_approved) < args.min_approved_docs:
            detail = (
                f"tenant={tenant_key} approved_indexed_count={len(indexed_approved)} "
                f"required={args.min_approved_docs}"
            )
            return PreflightResult(
                status="FAIL",
                reason_code=REASON_INDEXING_INCOMPLETE,
                reason_detail=detail,
                tenant_checks=tenant_checks + [tenant_check],
                provider_checks=provider_checks,
                admin_tokens=admin_tokens,
            )

        tenant_checks.append(tenant_check)

    if args.skip_provider_preflight:
        return PreflightResult(
            status="PASS",
            reason_code=REASON_OK,
            reason_detail="provider_preflight_skipped",
            tenant_checks=tenant_checks,
            provider_checks=[],
            admin_tokens=admin_tokens,
        )

    for tenant_key in unique_tenants:
        ops_login = login_with_credentials(
            client=client,
            tenant_key=tenant_key,
            login_id=args.ops_login_id,
            password=args.ops_password,
            channel_id="eval-provider-preflight",
            nonce=f"eval-preflight-ops-{tenant_key}",
        )
        provider_check: dict[str, Any] = {"tenant_key": tenant_key}
        if not ops_login.ok:
            provider_check["status"] = "LOGIN_FAILED"
            provider_check["http_status"] = ops_login.status
            provider_check["error_code"] = ops_login.error_code
            provider_checks.append(provider_check)
            detail = (
                f"ops_login_failed tenant={tenant_key} status={ops_login.status} "
                f"error_code={ops_login.error_code} message={ops_login.error_message}"
            )
            reason_code = REASON_PROVIDER_UNAVAILABLE
            if ops_login.status == 0:
                reason_code = REASON_TARGET_UNREACHABLE
            return PreflightResult(
                status="FAIL",
                reason_code=reason_code,
                reason_detail=detail,
                tenant_checks=tenant_checks,
                provider_checks=provider_checks,
                admin_tokens=admin_tokens,
            )

        health_trace = str(uuid.uuid4())
        try:
            health_status, health_text, health_payload = client.request_json(
                "GET",
                "/v1/ops/llm/providers/health",
                _headers(health_trace, tenant_key, token=ops_login.token),
                body=None,
            )
        except urllib.error.URLError as exc:
            provider_check["status"] = "NETWORK_ERROR"
            provider_check["reason"] = _mask(str(exc.reason))
            provider_checks.append(provider_check)
            return PreflightResult(
                status="FAIL",
                reason_code=REASON_TARGET_UNREACHABLE,
                reason_detail=f"provider_health_network_error tenant={tenant_key}",
                tenant_checks=tenant_checks,
                provider_checks=provider_checks,
                admin_tokens=admin_tokens,
            )

        provider_check["http_status"] = health_status
        if health_status != 200:
            provider_check["status"] = "HTTP_NOT_OK"
            provider_check["body_excerpt"] = _mask(health_text)[:200]
            provider_checks.append(provider_check)
            return PreflightResult(
                status="FAIL",
                reason_code=REASON_PROVIDER_UNAVAILABLE,
                reason_detail=f"provider_health_status tenant={tenant_key} status={health_status}",
                tenant_checks=tenant_checks,
                provider_checks=provider_checks,
                admin_tokens=admin_tokens,
            )

        items = _tenant_items(health_payload)
        provider_check["provider_count"] = len(items)
        if not items:
            provider_check["status"] = "NO_PROVIDER_METADATA"
            provider_checks.append(provider_check)
            continue
        healthy_items = []
        for item in items:
            health_status_value = str(item.get("health_status", "")).strip().lower()
            kill_switch = bool(item.get("kill_switch", False))
            if health_status_value == "healthy" and not kill_switch:
                healthy_items.append(item)
        provider_check["healthy_count"] = len(healthy_items)
        provider_check["status"] = "PASS" if healthy_items else "NO_HEALTHY_PROVIDER"
        provider_checks.append(provider_check)
        if not healthy_items:
            return PreflightResult(
                status="FAIL",
                reason_code=REASON_PROVIDER_UNAVAILABLE,
                reason_detail=f"no_healthy_provider tenant={tenant_key}",
                tenant_checks=tenant_checks,
                provider_checks=provider_checks,
                admin_tokens=admin_tokens,
            )

    return PreflightResult(
        status="PASS",
        reason_code=REASON_OK,
        reason_detail="ok",
        tenant_checks=tenant_checks,
        provider_checks=provider_checks,
        admin_tokens=admin_tokens,
    )


def run_case(client: HttpClient, args: argparse.Namespace, case: EvalCase, token: str) -> CaseResult:
    trace_id = str(uuid.uuid4())
    headers = _headers(trace_id, case.tenant_key, token=token)
    notes = _parse_notes(case.notes)
    expected_outcome = notes.get("expect", "answer").lower()
    top_k = int(notes.get("top_k", "3"))

    session_status, session_text, session_json = client.request_json(
        "POST",
        "/v1/sessions",
        _headers(trace_id, case.tenant_key, token=token, with_idempotency=True),
        body={},
    )
    if session_status != 201 or not isinstance(session_json, dict):
        return CaseResult(
            case_id=case.case_id,
            tenant_key=case.tenant_key,
            user_role=case.user_role,
            trace_id=trace_id,
            status="FAIL",
            expected_outcome=expected_outcome,
            reason_code=REASON_CASE_FAILURE,
            fail_closed=session_status >= 400,
            answer_contract_pass=False,
            citation_count=0,
            requires_citation=case.requires_citation,
            citation_covered=case.requires_citation == 0,
            policy_violation=False,
            policy_violation_reasons=[],
            latency_ms=None,
            post_status=session_status,
            stream_status=0,
            event_types=[],
            error_codes=[_extract_error_code(session_json)],
            notes=case.notes,
            error_message=f"create_session_failed status={session_status} body={_mask(session_text)[:240]}",
        )
    session_id = str(session_json.get("session_id", ""))
    if not session_id:
        return CaseResult(
            case_id=case.case_id,
            tenant_key=case.tenant_key,
            user_role=case.user_role,
            trace_id=trace_id,
            status="FAIL",
            expected_outcome=expected_outcome,
            reason_code=REASON_CASE_FAILURE,
            fail_closed=False,
            answer_contract_pass=False,
            citation_count=0,
            requires_citation=case.requires_citation,
            citation_covered=case.requires_citation == 0,
            policy_violation=False,
            policy_violation_reasons=[],
            latency_ms=None,
            post_status=201,
            stream_status=0,
            event_types=[],
            error_codes=[],
            notes=case.notes,
            error_message="session_id_missing",
        )

    post_status, post_text, post_json = client.request_json(
        "POST",
        f"/v1/sessions/{session_id}/messages",
        _headers(trace_id, case.tenant_key, token=token, with_idempotency=True),
        body={"text": case.query, "top_k": top_k, "client_nonce": f"rag-reg-{case.case_id}"},
    )
    message_id = str(post_json.get("id", "")) if isinstance(post_json, dict) else ""
    event_types: list[str] = []
    error_codes: list[str] = []
    citations_count = 0
    stream_status = 0
    latency_ms: float | None = None
    fail_closed = post_status >= 400
    policy_violation_reasons: list[str] = []
    combined_text = ""

    if post_status == 202 and message_id:
        stream_status, events, _stream_raw, latency_ms = client.read_sse(
            f"/v1/sessions/{session_id}/messages/{message_id}/stream",
            headers,
        )
        event_types = [str(item.get("event", "")) for item in events if item.get("event")]
        visible_text_parts: list[str] = []
        for item in events:
            event_name = str(item.get("event", "")).strip().lower()
            payload = item.get("payload")
            if isinstance(payload, dict):
                code = payload.get("error_code")
                if code:
                    error_codes.append(str(code))
            if event_name == "token":
                if isinstance(payload, str) and payload.strip():
                    visible_text_parts.append(payload)
                else:
                    visible_text_parts.extend(_collect_visible_text(payload))
            elif event_name == "safe_response":
                visible_text_parts.extend(_collect_visible_text(payload))
            elif event_name == "citation":
                visible_text_parts.extend(_collect_visible_text(payload))
        if "safe_response" in event_types:
            fail_closed = True
        if "error" in event_types and "token" not in event_types:
            fail_closed = True
        citation_status, _, citation_json = client.request_json(
            "GET",
            f"/v1/rag/answers/{message_id}/citations",
            headers,
            body=None,
        )
        if citation_status == 200 and isinstance(citation_json, dict):
            data = citation_json.get("data")
            if isinstance(data, list):
                citations_count = len(data)
                for citation in data:
                    if isinstance(citation, dict):
                        excerpt = citation.get("excerpt_masked")
                        if excerpt:
                            visible_text_parts.append(str(excerpt))
        combined_text = "\n".join(visible_text_parts)
    elif isinstance(post_json, dict):
        code = post_json.get("error_code")
        if code:
            error_codes.append(str(code))
        visible_text_parts = _collect_visible_text(post_json)
        if visible_text_parts:
            combined_text = "\n".join(visible_text_parts)
        else:
            combined_text = post_text
    else:
        combined_text = post_text

    forbidden = list(FORBIDDEN_BY_BUNDLE.get(case.expected_policy_bundle, []))
    if "forbidden" in notes:
        forbidden.extend([item.strip() for item in notes["forbidden"].split("|") if item.strip()])

    for pattern in PII_PATTERNS:
        if pattern.search(combined_text):
            policy_violation_reasons.append(f"PII_PATTERN:{pattern.pattern}")
            break
    lower_blob = combined_text.casefold()
    for phrase in forbidden:
        if phrase.casefold() in lower_blob:
            policy_violation_reasons.append(f"FORBIDDEN_PHRASE:{phrase}")
            break

    citation_covered = case.requires_citation == 0 or citations_count >= 1
    has_done = "done" in event_types
    has_error = "error" in event_types
    has_safe = "safe_response" in event_types
    answer_contract_pass = bool(has_done and not has_error and not has_safe and citation_covered)
    if policy_violation_reasons:
        answer_contract_pass = False

    if expected_outcome == "fail_closed" and not fail_closed:
        status = "FAIL"
        error_message = "expected fail_closed but not observed"
    elif expected_outcome == "answer" and fail_closed:
        status = "FAIL"
        error_message = "expected answer path but fail_closed observed"
    elif policy_violation_reasons:
        status = "FAIL"
        error_message = "policy_violation_detected"
    elif expected_outcome == "answer" and not answer_contract_pass:
        status = "FAIL"
        error_message = "answer_contract_not_passed"
    else:
        status = "PASS"
        error_message = ""

    reason_code = REASON_OK
    if status == "FAIL":
        if post_status == 503 or stream_status == 503 or any(_is_provider_code(code) for code in error_codes):
            reason_code = REASON_PROVIDER_UNAVAILABLE
        else:
            reason_code = REASON_CASE_FAILURE

    return CaseResult(
        case_id=case.case_id,
        tenant_key=case.tenant_key,
        user_role=case.user_role,
        trace_id=trace_id,
        status=status,
        expected_outcome=expected_outcome,
        reason_code=reason_code,
        fail_closed=fail_closed,
        answer_contract_pass=answer_contract_pass,
        citation_count=citations_count,
        requires_citation=case.requires_citation,
        citation_covered=citation_covered,
        policy_violation=bool(policy_violation_reasons),
        policy_violation_reasons=policy_violation_reasons,
        latency_ms=latency_ms,
        post_status=post_status,
        stream_status=stream_status,
        event_types=event_types,
        error_codes=[code for code in error_codes if code],
        notes=case.notes,
        error_message=error_message,
    )


def aggregate(results: list[CaseResult]) -> dict[str, Any]:
    executed = [r for r in results if r.status in {"PASS", "FAIL"}]
    requires_cases = [r for r in executed if r.requires_citation == 1]
    citation_numerator = sum(1 for r in requires_cases if r.citation_count >= 1)
    fail_closed_numerator = sum(1 for r in executed if r.fail_closed)
    policy_violation_numerator = sum(1 for r in executed if r.policy_violation)
    answer_contract_numerator = sum(1 for r in executed if r.answer_contract_pass)
    case_pass_numerator = sum(1 for r in executed if r.status == "PASS")
    latencies = [r.latency_ms for r in executed if r.latency_ms is not None]
    latency_p95_ms = _p95([float(v) for v in latencies if v is not None])

    def _rate(numerator: int, denominator: int) -> float | None:
        if denominator <= 0:
            return None
        return round(float(numerator) / float(denominator), 6)

    return {
        "citation_coverage_rate": {
            "numerator": citation_numerator,
            "denominator": len(requires_cases),
            "value": _rate(citation_numerator, len(requires_cases)),
        },
        "fail_closed_rate": {
            "numerator": fail_closed_numerator,
            "denominator": len(executed),
            "value": _rate(fail_closed_numerator, len(executed)),
        },
        "policy_violation_rate": {
            "numerator": policy_violation_numerator,
            "denominator": len(executed),
            "value": _rate(policy_violation_numerator, len(executed)),
        },
        "answer_contract_pass_rate": {
            "numerator": answer_contract_numerator,
            "denominator": len(executed),
            "value": _rate(answer_contract_numerator, len(executed)),
        },
        "latency_p95_ms": {
            "value": latency_p95_ms,
            "samples": len(latencies),
        },
        "case_pass_rate": {
            "numerator": case_pass_numerator,
            "denominator": len(executed),
            "value": _rate(case_pass_numerator, len(executed)),
        },
    }


def build_skipped_results(cases: list[EvalCase], reason_code: str, reason_detail: str) -> list[CaseResult]:
    skipped: list[CaseResult] = []
    for case in cases:
        skipped.append(
            CaseResult(
                case_id=case.case_id,
                tenant_key=case.tenant_key,
                user_role=case.user_role,
                trace_id="",
                status="SKIP",
                expected_outcome=_parse_notes(case.notes).get("expect", "answer").lower(),
                reason_code=reason_code,
                fail_closed=False,
                answer_contract_pass=False,
                citation_count=0,
                requires_citation=case.requires_citation,
                citation_covered=case.requires_citation == 0,
                policy_violation=False,
                policy_violation_reasons=[],
                latency_ms=None,
                post_status=0,
                stream_status=0,
                event_types=[],
                error_codes=[],
                notes=case.notes,
                error_message=_mask(reason_detail),
            )
        )
    return skipped


def derive_failure_reason(results: list[CaseResult]) -> tuple[str, str]:
    failed = [item for item in results if item.status == "FAIL"]
    if not failed:
        return REASON_OK, ""
    reason_counts: dict[str, int] = {}
    for item in failed:
        reason = item.reason_code or REASON_CASE_FAILURE
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    if len(reason_counts) == 1:
        sole_reason = next(iter(reason_counts))
        return sole_reason, f"failed_cases={len(failed)}"

    if REASON_PROVIDER_UNAVAILABLE in reason_counts:
        return REASON_PROVIDER_UNAVAILABLE, (
            f"failed_cases={len(failed)} provider_related={reason_counts.get(REASON_PROVIDER_UNAVAILABLE, 0)}"
        )
    return REASON_CASE_FAILURE, f"failed_cases={len(failed)}"


def write_outputs(out_dir: Path, report: dict[str, Any], results: list[CaseResult]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.json"
    summary_path = out_dir / "summary.csv"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with summary_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "case_id",
                "tenant_key",
                "user_role",
                "trace_id",
                "status",
                "expected_outcome",
                "reason_code",
                "fail_closed",
                "answer_contract_pass",
                "citation_count",
                "requires_citation",
                "citation_covered",
                "policy_violation",
                "latency_ms",
                "post_status",
                "stream_status",
                "event_types",
                "error_codes",
                "error_message",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "case_id": result.case_id,
                    "tenant_key": result.tenant_key,
                    "user_role": result.user_role,
                    "trace_id": result.trace_id,
                    "status": result.status,
                    "expected_outcome": result.expected_outcome,
                    "reason_code": result.reason_code,
                    "fail_closed": int(result.fail_closed),
                    "answer_contract_pass": int(result.answer_contract_pass),
                    "citation_count": result.citation_count,
                    "requires_citation": result.requires_citation,
                    "citation_covered": int(result.citation_covered),
                    "policy_violation": int(result.policy_violation),
                    "latency_ms": "" if result.latency_ms is None else f"{result.latency_ms:.3f}",
                    "post_status": result.post_status,
                    "stream_status": result.stream_status,
                    "event_types": "|".join(result.event_types),
                    "error_codes": "|".join(result.error_codes),
                    "error_message": _mask(result.error_message),
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fixed-schema RAG regression harness")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--out", default=DEFAULT_OUT_DIR)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--agent-login-id", default="agent1")
    parser.add_argument("--agent-password", default="agent1-pass")
    parser.add_argument("--admin-login-id", default="admin1")
    parser.add_argument("--admin-password", default="admin1-pass")
    parser.add_argument("--ops-login-id", default="ops1")
    parser.add_argument("--ops-password", default="ops1-pass")
    parser.add_argument("--min-approved-docs", type=int, default=3)
    parser.add_argument("--no-auto-seed", action="store_true")
    parser.add_argument("--seed-index-timeout-sec", type=int, default=180)
    parser.add_argument("--seed-poll-interval-sec", type=float, default=2.0)
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--skip-provider-preflight", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset)
    out_dir = Path(args.out)
    client = HttpClient(base_url=args.base_url, timeout_sec=args.timeout_sec)

    status = "FAIL"
    reason_code = REASON_METRIC_COMPUTATION_BUG
    reason_detail = "not_started"
    preflight_payload: dict[str, Any] = {
        "status": "NOT_RUN",
        "reason_code": "",
        "reason_detail": "",
        "tenant_checks": [],
        "provider_checks": [],
    }
    cases: list[EvalCase] = []
    results: list[CaseResult] = []
    fatal_error = ""

    try:
        cases = load_dataset(dataset_path)
        if not cases:
            status = "SKIPPED"
            reason_code = REASON_DATA_UNAVAILABLE
            reason_detail = "dataset_empty"
            results = []
        else:
            if args.skip_preflight:
                preflight_payload = {
                    "status": "PASS",
                    "reason_code": REASON_OK,
                    "reason_detail": "preflight_skipped",
                    "tenant_checks": [],
                    "provider_checks": [],
                }
            else:
                preflight = run_preflight(client, args, cases)
                preflight_payload = {
                    "status": preflight.status,
                    "reason_code": preflight.reason_code,
                    "reason_detail": preflight.reason_detail,
                    "tenant_checks": preflight.tenant_checks,
                    "provider_checks": preflight.provider_checks,
                }
                if preflight.status != "PASS":
                    status = "SKIPPED"
                    reason_code = preflight.reason_code
                    reason_detail = preflight.reason_detail
                    results = build_skipped_results(cases, reason_code, reason_detail)

            if not results:
                token_cache: dict[tuple[str, str], str] = {}
                for case in cases:
                    cache_key = (case.tenant_key, case.user_role)
                    token = token_cache.get(cache_key, "")
                    if not token:
                        login_id, password = _role_credentials(args, case.user_role)
                        login = login_with_credentials(
                            client=client,
                            tenant_key=case.tenant_key,
                            login_id=login_id,
                            password=password,
                            channel_id="eval",
                            nonce=f"eval-login-{case.case_id}",
                        )
                        if not login.ok:
                            login_reason = REASON_AUTH_FAILED
                            if login.status == 0:
                                login_reason = REASON_TARGET_UNREACHABLE
                            elif login.status == 503 or _is_provider_code(login.error_code):
                                login_reason = REASON_PROVIDER_UNAVAILABLE
                            results.append(
                                CaseResult(
                                    case_id=case.case_id,
                                    tenant_key=case.tenant_key,
                                    user_role=case.user_role,
                                    trace_id=login.trace_id,
                                    status="FAIL",
                                    expected_outcome=_parse_notes(case.notes).get("expect", "answer").lower(),
                                    reason_code=login_reason,
                                    fail_closed=False,
                                    answer_contract_pass=False,
                                    citation_count=0,
                                    requires_citation=case.requires_citation,
                                    citation_covered=case.requires_citation == 0,
                                    policy_violation=False,
                                    policy_violation_reasons=[],
                                    latency_ms=None,
                                    post_status=login.status,
                                    stream_status=0,
                                    event_types=[],
                                    error_codes=[login.error_code] if login.error_code else [],
                                    notes=case.notes,
                                    error_message=login.error_message,
                                )
                            )
                            continue
                        token = login.token
                        token_cache[cache_key] = token

                    try:
                        results.append(run_case(client, args, case, token))
                    except urllib.error.URLError as exc:
                        results.append(
                            CaseResult(
                                case_id=case.case_id,
                                tenant_key=case.tenant_key,
                                user_role=case.user_role,
                                trace_id=str(uuid.uuid4()),
                                status="FAIL",
                                expected_outcome=_parse_notes(case.notes).get("expect", "answer").lower(),
                                reason_code=REASON_TARGET_UNREACHABLE,
                                fail_closed=False,
                                answer_contract_pass=False,
                                citation_count=0,
                                requires_citation=case.requires_citation,
                                citation_covered=case.requires_citation == 0,
                                policy_violation=False,
                                policy_violation_reasons=[],
                                latency_ms=None,
                                post_status=0,
                                stream_status=0,
                                event_types=[],
                                error_codes=[],
                                notes=case.notes,
                                error_message=f"network_error={_mask(str(exc.reason))}",
                            )
                        )

                fail_count = sum(1 for item in results if item.status == "FAIL")
                if fail_count == 0:
                    status = "PASS"
                    reason_code = REASON_OK
                    reason_detail = ""
                else:
                    status = "FAIL"
                    reason_code, reason_detail = derive_failure_reason(results)

    except Exception as exc:  # pragma: no cover - defensive always-write path
        status = "FAIL"
        reason_code = REASON_METRIC_COMPUTATION_BUG
        reason_detail = f"unhandled_exception={exc.__class__.__name__}"
        fatal_error = _mask(str(exc))
        if cases and not results:
            results = build_skipped_results(cases, reason_code, reason_detail)

    metrics = aggregate(results)
    report = {
        "generated_at_utc": _now_utc(),
        "base_url": args.base_url,
        "dataset_path": dataset_path.as_posix(),
        "case_count": len(cases),
        "status": status,
        "reason_code": reason_code,
        "reason_detail": _mask(reason_detail),
        "fatal_error": fatal_error,
        "preflight": preflight_payload,
        "execution_summary": {
            "executed": sum(1 for item in results if item.status in {"PASS", "FAIL"}),
            "passed": sum(1 for item in results if item.status == "PASS"),
            "failed": sum(1 for item in results if item.status == "FAIL"),
            "skipped": sum(1 for item in results if item.status == "SKIP"),
        },
        "metrics": metrics,
        "cases": [asdict(item) for item in results],
    }
    write_outputs(out_dir=out_dir, report=report, results=results)

    print("rag_regression_harness")
    print(f"status={status}")
    print(f"reason_code={reason_code}")
    print(f"report_path={(out_dir / 'report.json').as_posix()}")
    print(f"summary_path={(out_dir / 'summary.csv').as_posix()}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
