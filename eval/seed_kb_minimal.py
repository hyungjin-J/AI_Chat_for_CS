#!/usr/bin/env python3
"""Seed minimal KB documents for deterministic RAG regression runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


REASON_OK = "OK"
REASON_DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
REASON_INDEXING_INCOMPLETE = "INDEXING_INCOMPLETE"
REASON_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
REASON_NETWORK_UNAVAILABLE = "NETWORK_UNAVAILABLE"
REASON_TARGET_UNREACHABLE = "TARGET_UNREACHABLE"

DEFAULT_TIMEOUT_SEC = 60
DEFAULT_POLL_INTERVAL_SEC = 2.0
DEFAULT_INDEX_TIMEOUT_SEC = 180
DEFAULT_MIN_DOCS = 3
DEFAULT_OUT_JSON = "eval/out/latest/seed_kb_minimal_report.json"

SEED_DOCS = [
    (
        "eval_seed_refund_policy",
        "Refund policy for unopened products allows return within 7 days. "
        "Approved refunds are processed to the original payment method within 3 to 5 business days.",
    ),
    (
        "eval_seed_shipping_compensation",
        "Shipping delay compensation guide: if delivery is delayed beyond SLA, "
        "customer can request coupon credit and escalation review.",
    ),
    (
        "eval_seed_subscription_cancellation",
        "Subscription cancellation deadline policy: cancellation before billing renewal date "
        "prevents next-cycle charge; after renewal, refund follows refund policy rules.",
    ),
    (
        "eval_seed_handoff_criteria",
        "Handoff criteria to human agent policy: unresolved billing disputes, legal threats, "
        "or repeated policy conflicts must be escalated to human support.",
    ),
]


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


def _mask(value: str) -> str:
    text = value or ""
    text = text.replace("\r", " ").replace("\n", " ")
    return text[:240]


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


def _extract_error_code(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("error_code")
        if value is not None:
            return str(value)
    return ""


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


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


def login_admin(client: HttpClient, tenant_key: str, login_id: str, password: str) -> tuple[bool, str, dict[str, Any]]:
    trace_id = str(uuid.uuid4())
    try:
        status, text, payload = client.request_json(
            "POST",
            "/v1/auth/login",
            _headers(trace_id, tenant_key, with_idempotency=True),
            body={
                "login_id": login_id,
                "password": password,
                "channel_id": "eval-seed",
                "client_nonce": "eval-seed-login",
            },
        )
    except urllib.error.URLError as exc:
        return False, "", {
            "reason_code": REASON_TARGET_UNREACHABLE,
            "reason_detail": f"login_network_error={_mask(str(exc.reason))}",
            "http_status": 0,
            "trace_id": trace_id,
        }

    if status == 201 and isinstance(payload, dict):
        token = payload.get("access_token")
        if isinstance(token, str) and token.strip():
            return True, token.strip(), {
                "reason_code": REASON_OK,
                "reason_detail": "",
                "http_status": status,
                "trace_id": trace_id,
            }
    return False, "", {
        "reason_code": REASON_DATA_UNAVAILABLE,
        "reason_detail": f"login_failed status={status} body={_mask(text)}",
        "http_status": status,
        "error_code": _extract_error_code(payload),
        "trace_id": trace_id,
    }


def list_documents(client: HttpClient, tenant_key: str, token: str) -> tuple[int, list[dict[str, Any]], str]:
    trace_id = str(uuid.uuid4())
    path = f"/v1/admin/kb/documents?{urllib.parse.urlencode({'limit': 200, 'offset': 0})}"
    status, text, payload = client.request_json(
        "GET",
        path,
        _headers(trace_id, tenant_key, token=token),
        body=None,
    )
    return status, _items(payload), text


def upload_document(
    client: HttpClient,
    tenant_key: str,
    token: str,
    title: str,
    raw_content: str,
) -> tuple[int, dict[str, Any], str]:
    trace_id = str(uuid.uuid4())
    status, text, payload = client.request_json(
        "POST",
        "/v1/admin/kb/documents",
        _headers(trace_id, tenant_key, token=token, with_idempotency=True),
        body={
            "title": title,
            "source_type": "manual",
            "category": "cs",
            "effective_date": dt.date.today().isoformat(),
            "owner": "eval-seed",
            "raw_content": raw_content,
        },
    )
    return status, payload if isinstance(payload, dict) else {}, text


def approve_document(client: HttpClient, tenant_key: str, token: str, document_id: str) -> tuple[int, dict[str, Any], str]:
    trace_id = str(uuid.uuid4())
    status, text, payload = client.request_json(
        "POST",
        f"/v1/admin/kb/documents/{document_id}/approve",
        _headers(trace_id, tenant_key, token=token),
        body=None,
    )
    return status, payload if isinstance(payload, dict) else {}, text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed minimal KB docs for RAG regression")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--tenant-key", required=True)
    parser.add_argument("--min-docs", type=int, default=DEFAULT_MIN_DOCS)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--index-timeout-sec", type=int, default=DEFAULT_INDEX_TIMEOUT_SEC)
    parser.add_argument("--poll-interval-sec", type=float, default=DEFAULT_POLL_INTERVAL_SEC)
    parser.add_argument("--admin-login-id", default="admin1")
    parser.add_argument("--admin-password", default="admin1-pass")
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    return parser.parse_args()


def seed_minimal_kb(
    *,
    base_url: str,
    tenant_key: str,
    min_docs: int = DEFAULT_MIN_DOCS,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    index_timeout_sec: int = DEFAULT_INDEX_TIMEOUT_SEC,
    poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC,
    admin_login_id: str = "admin1",
    admin_password: str = "admin1-pass",
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at_utc": _now_utc(),
        "base_url": base_url,
        "tenant_key": tenant_key,
        "min_docs": min_docs,
        "status": "FAIL",
        "reason_code": REASON_DATA_UNAVAILABLE,
        "reason_detail": "not_started",
        "actions": [],
        "documents": [],
    }

    client = HttpClient(base_url=base_url, timeout_sec=timeout_sec)
    reachable, reachability_detail = probe_base_url(client, tenant_key)
    report["preflight"] = {
        "base_url_reachable": bool(reachable),
        "detail": reachability_detail,
    }
    if not reachable:
        report["status"] = "FAIL"
        report["reason_code"] = REASON_TARGET_UNREACHABLE
        report["reason_detail"] = f"base_url_unreachable reason={reachability_detail}"
        return report

    ok, token, login_meta = login_admin(client, tenant_key, admin_login_id, admin_password)
    report["login"] = login_meta
    if not ok:
        report["status"] = "FAIL"
        report["reason_code"] = str(login_meta.get("reason_code", REASON_DATA_UNAVAILABLE))
        report["reason_detail"] = str(login_meta.get("reason_detail", "admin_login_failed"))
        return report

    try:
        status, docs, docs_text = list_documents(client, tenant_key, token)
    except urllib.error.URLError as exc:
        report["status"] = "FAIL"
        report["reason_code"] = REASON_TARGET_UNREACHABLE
        report["reason_detail"] = f"list_documents_network_error reason={_mask(str(exc.reason))}"
        return report

    if status != 200:
        report["status"] = "FAIL"
        report["reason_code"] = REASON_DATA_UNAVAILABLE
        report["reason_detail"] = f"list_documents_failed status={status} body={_mask(docs_text)}"
        return report

    by_title: dict[str, dict[str, Any]] = {}
    for item in docs:
        title = str(item.get("title", "")).strip()
        if title and title not in by_title:
            by_title[title] = item

    target_docs = SEED_DOCS[: max(1, min(min_docs, len(SEED_DOCS)))]
    for title, content in target_docs:
        item = by_title.get(title)
        if item is None:
            try:
                upload_status, upload_payload, upload_text = upload_document(
                    client=client,
                    tenant_key=tenant_key,
                    token=token,
                    title=title,
                    raw_content=content,
                )
            except urllib.error.URLError as exc:
                report["status"] = "FAIL"
                report["reason_code"] = REASON_TARGET_UNREACHABLE
                report["reason_detail"] = (
                    f"upload_network_error title={title} reason={_mask(str(exc.reason))}"
                )
                return report
            report["actions"].append(
                {
                    "action": "upload",
                    "title": title,
                    "http_status": upload_status,
                    "error_code": _extract_error_code(upload_payload),
                }
            )
            if upload_status != 201:
                report["status"] = "FAIL"
                report["reason_code"] = REASON_DATA_UNAVAILABLE
                report["reason_detail"] = (
                    f"upload_failed title={title} status={upload_status} body={_mask(upload_text)}"
                )
                return report

    deadline = time.time() + max(5, int(index_timeout_sec))
    while True:
        try:
            status, docs, docs_text = list_documents(client, tenant_key, token)
        except urllib.error.URLError as exc:
            report["status"] = "FAIL"
            report["reason_code"] = REASON_TARGET_UNREACHABLE
            report["reason_detail"] = f"list_documents_poll_network_error reason={_mask(str(exc.reason))}"
            return report
        if status != 200:
            report["status"] = "FAIL"
            report["reason_code"] = REASON_DATA_UNAVAILABLE
            report["reason_detail"] = f"list_documents_poll_failed status={status} body={_mask(docs_text)}"
            return report

        by_title = {}
        for item in docs:
            title = str(item.get("title", "")).strip()
            if title and title not in by_title:
                by_title[title] = item

        indexed_titles: list[str] = []
        pending_titles: list[str] = []
        report_docs: list[dict[str, Any]] = []
        for title, _ in target_docs:
            item = by_title.get(title, {})
            doc_status = str(item.get("status", "")).strip().lower()
            pipeline_status = str(item.get("pipeline_status", "")).strip().upper()
            document_id = str(item.get("document_id", "")).strip()
            report_docs.append(
                {
                    "title": title,
                    "document_id": document_id,
                    "status": doc_status,
                    "pipeline_status": pipeline_status,
                }
            )
            if pipeline_status == "INDEXED":
                indexed_titles.append(title)
            else:
                pending_titles.append(title)

        report["documents"] = report_docs

        if len(indexed_titles) >= len(target_docs):
            break
        if time.time() > deadline:
            report["status"] = "FAIL"
            report["reason_code"] = REASON_INDEXING_INCOMPLETE
            report["reason_detail"] = (
                f"index_timeout indexed={len(indexed_titles)} required={len(target_docs)} "
                f"pending_titles={pending_titles}"
            )
            return report
        time.sleep(max(0.5, poll_interval_sec))

    # Approve all target docs.
    for doc in report.get("documents", []):
        document_id = str(doc.get("document_id", "")).strip()
        if not document_id:
            continue
        if str(doc.get("status", "")).strip().lower() == "approved":
            continue
        try:
            approve_status, approve_payload, approve_text = approve_document(client, tenant_key, token, document_id)
        except urllib.error.URLError as exc:
            report["status"] = "FAIL"
            report["reason_code"] = REASON_TARGET_UNREACHABLE
            report["reason_detail"] = (
                f"approve_network_error document_id={document_id} reason={_mask(str(exc.reason))}"
            )
            return report
        report["actions"].append(
            {
                "action": "approve",
                "document_id": document_id,
                "http_status": approve_status,
                "error_code": _extract_error_code(approve_payload),
            }
        )
        if approve_status not in (200, 409):
            report["status"] = "FAIL"
            report["reason_code"] = REASON_DATA_UNAVAILABLE
            report["reason_detail"] = (
                f"approve_failed document_id={document_id} status={approve_status} body={_mask(approve_text)}"
            )
            return report

    try:
        status, docs, docs_text = list_documents(client, tenant_key, token)
    except urllib.error.URLError as exc:
        report["status"] = "FAIL"
        report["reason_code"] = REASON_TARGET_UNREACHABLE
        report["reason_detail"] = f"final_list_documents_network_error reason={_mask(str(exc.reason))}"
        return report

    if status != 200:
        report["status"] = "FAIL"
        report["reason_code"] = REASON_DATA_UNAVAILABLE
        report["reason_detail"] = f"final_list_documents_failed status={status} body={_mask(docs_text)}"
        return report

    by_title = {}
    for item in docs:
        title = str(item.get("title", "")).strip()
        if title and title not in by_title:
            by_title[title] = item

    final_ready = 0
    final_docs: list[dict[str, Any]] = []
    for title, _ in target_docs:
        item = by_title.get(title, {})
        doc_status = str(item.get("status", "")).strip().lower()
        pipeline_status = str(item.get("pipeline_status", "")).strip().upper()
        if doc_status == "approved" and pipeline_status == "INDEXED":
            final_ready += 1
        final_docs.append(
            {
                "title": title,
                "document_id": str(item.get("document_id", "")).strip(),
                "status": doc_status,
                "pipeline_status": pipeline_status,
            }
        )

    report["documents"] = final_docs
    report["ready_count"] = final_ready

    if final_ready >= len(target_docs):
        report["status"] = "PASS"
        report["reason_code"] = REASON_OK
        report["reason_detail"] = ""
    else:
        report["status"] = "FAIL"
        report["reason_code"] = REASON_INDEXING_INCOMPLETE
        report["reason_detail"] = f"ready_count={final_ready} required={len(target_docs)}"

    return report


def main() -> int:
    args = parse_args()
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = seed_minimal_kb(
        base_url=args.base_url,
        tenant_key=args.tenant_key,
        min_docs=args.min_docs,
        timeout_sec=args.timeout_sec,
        index_timeout_sec=args.index_timeout_sec,
        poll_interval_sec=args.poll_interval_sec,
        admin_login_id=args.admin_login_id,
        admin_password=args.admin_password,
    )
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"status={report['status']}")
    print(f"reason_code={report['reason_code']}")
    print(f"report_path={out_path.as_posix()}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
