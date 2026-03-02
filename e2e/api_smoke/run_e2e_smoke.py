#!/usr/bin/env python3
"""Operational E2E smoke runner for counselor core flow."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACT_DIR = "docs/review/mvp_verification_pack/artifacts"
DEFAULT_REPORT_PREFIX = "e2e_smoke_report"
DEFAULT_TRACE_PREFIX = "e2e_smoke_trace_samples"
DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_COMPOSE_FILE = "infra/compose/production/docker-compose.prod.yml"
DEFAULT_COMPOSE_SERVICE = "postgres"
DEFAULT_DB_NAME = "aichatbot"
DEFAULT_DB_USER = "aichatbot"
DEFAULT_DB_PASSWORD = "local-dev-only-password"
DEFAULT_DB_HOST = "127.0.0.1"
DEFAULT_DB_PORT = 5432
DEFAULT_S1_QUERY = "refund policy processing timeline"
DEFAULT_S1_TOP_K = 3
DEFAULT_S6_FORCE_FAIL_CLOSED_TEXT = "__E2E_FORCE_FAIL_CLOSED__ synthetic contract failure probe"
DEFAULT_S6_FORCE_FAIL_CLOSED_ERROR_CODE = "AI-009-409-EVIDENCE"

PII_EMAIL = "smoke.pii.user@example.com"
PII_PHONE_REGEX = re.compile(r"(?:\\+82\\s*)?0?10[- ]?9876[- ]?5432", re.IGNORECASE)
PII_ORDER = "AB-123456"

RUNBOOK_SSE = "docs/ops/runbook/playbooks/sse_streaming_degradation.md"
RUNBOOK_PII = "docs/ops/runbook/playbooks/pii_leak_suspected.md"
RUNBOOK_RBAC = "docs/ops/runbook/playbooks/trace_id_missing.md"
RUNBOOK_FAIL_CLOSED = "docs/ops/runbook/playbooks/answer_contract_fail_spike.md"
RUNBOOK_INDEX = "docs/ops/runbook/README.md"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

REASON_NONE = "NONE"
REASON_TARGET_UNREACHABLE = "TARGET_UNREACHABLE"
REASON_BOOTSTRAP_FAILURE = "BOOTSTRAP_FAILURE"
REASON_SCENARIO_FAILURE = "SCENARIO_FAILURE"
REASON_UNEXPECTED_EXCEPTION = "UNEXPECTED_EXCEPTION"

S1_REQUIRED_EVENTS = ("token", "citation", "done")
S6_REQUIRED_EVENTS = ("safe_response", "error", "done")
S6_FORBIDDEN_EVENTS = ("token",)

REMEDIATION_HINTS = {
    REASON_NONE: "-",
    REASON_TARGET_UNREACHABLE: "Start backend and ensure base_url is reachable before running E2E smoke.",
    REASON_BOOTSTRAP_FAILURE: "Check login/bootstrap dependencies and rerun E2E smoke.",
    REASON_SCENARIO_FAILURE: "Inspect failed scenario stage/details and follow linked runbook.",
    REASON_UNEXPECTED_EXCEPTION: "Inspect traceback in report details and fix runner/runtime error.",
}


@dataclass
class ScenarioResult:
    scenario_id: str
    name: str
    status: str
    stage: str
    trace_id: str
    error_code: str
    message: str
    runbook: str
    details: dict[str, Any]


@dataclass
class HttpResponse:
    status: int
    body_text: str
    body_json: Any


@dataclass
class SseEvent:
    event_id: str
    event_type: str
    data_text: str
    payload: Any


@dataclass
class DbTraceEvidence:
    message_trace_id: str
    rag_trace_id: str
    stream_event_types: list[str]


class ScenarioFailure(RuntimeError):
    def __init__(
        self,
        stage: str,
        message: str,
        *,
        error_code: str = "",
        details: dict[str, Any] | None = None,
        runbook: str = RUNBOOK_INDEX,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.error_code = error_code
        self.details = details or {}
        self.runbook = runbook


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def date_tag_local() -> str:
    return dt.datetime.now().strftime("%Y%m%d")


def json_loads_safe(text: str) -> Any:
    candidate = (text or "").strip()
    if candidate == "":
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def create_trace_id() -> str:
    return str(uuid.uuid4())


def parse_payload(raw: str) -> Any:
    first = json_loads_safe(raw)
    if isinstance(first, str):
        second = json_loads_safe(first)
        if second is not None:
            return second
    return first if first is not None else raw


def normalize_base_url(raw: str) -> str:
    value = raw.strip().rstrip("/")
    if value == "":
        raise ValueError("base_url must not be empty")
    return value


def remediation_hint_for(reason_code: str) -> str:
    return REMEDIATION_HINTS.get(reason_code, REMEDIATION_HINTS[REASON_UNEXPECTED_EXCEPTION])


def classify_bootstrap_reason_code(stage: str) -> str:
    if stage == "preflight_base_url":
        return REASON_TARGET_UNREACHABLE
    return REASON_BOOTSTRAP_FAILURE


def probe_base_url_reachable(base_url: str, timeout_sec: int) -> tuple[bool, dict[str, Any]]:
    probe_url = normalize_base_url(base_url) + "/"
    request = urllib.request.Request(url=probe_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            return True, {"probe_url": probe_url, "http_status": int(response.getcode()), "error": ""}
    except urllib.error.HTTPError as exc:
        return True, {"probe_url": probe_url, "http_status": int(exc.code), "error": ""}
    except urllib.error.URLError as exc:
        return False, {
            "probe_url": probe_url,
            "http_status": None,
            "error": mask_secrets(str(exc.reason)),
        }


def contains_raw_pii(text: str) -> bool:
    blob = text or ""
    if PII_EMAIL.lower() in blob.lower():
        return True
    if PII_ORDER.lower() in blob.lower():
        return True
    if PII_PHONE_REGEX.search(blob):
        return True
    return False


def mask_secrets(text: str) -> str:
    value = text or ""
    value = re.sub(r"(?i)(access_token|refresh_token|authorization)\\s*[:=]\\s*[^,\\s]+", r"\\1=<REDACTED>", value)
    value = value.replace(PII_EMAIL, "<REDACTED>")
    value = value.replace(PII_ORDER, "<REDACTED>")
    value = PII_PHONE_REGEX.sub("<REDACTED>", value)
    return value


def shell_command(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.returncode, completed.stdout or "", completed.stderr or ""


def quote_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


class HttpClient:
    def __init__(self, base_url: str, timeout_sec: int) -> None:
        self.base_url = normalize_base_url(base_url)
        self.timeout_sec = timeout_sec

    def request_json(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> HttpResponse:
        url = self.base_url + path
        data_bytes: bytes | None = None
        req_headers = dict(headers)
        if body is not None:
            data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url=url, method=method.upper(), data=data_bytes, headers=req_headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                text = response.read().decode("utf-8", errors="replace")
                return HttpResponse(response.getcode(), text, json_loads_safe(text))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return HttpResponse(exc.code, text, json_loads_safe(text))
        except urllib.error.URLError as exc:
            raise ScenarioFailure(
                stage="http_connect",
                message="http request failed",
                details={
                    "url": url,
                    "method": method.upper(),
                    "reason": mask_secrets(str(exc.reason)),
                },
                runbook=RUNBOOK_INDEX,
            ) from exc

    def read_sse(
        self,
        path: str,
        headers: dict[str, str],
        max_events: int | None = None,
        stop_on_event_types: set[str] | None = None,
    ) -> tuple[int, list[SseEvent], str]:
        url = self.base_url + path
        req_headers = dict(headers)
        req_headers.setdefault("Accept", "text/event-stream")
        request = urllib.request.Request(url=url, method="GET", headers=req_headers)

        events: list[SseEvent] = []
        raw_lines: list[str] = []
        current_id = ""
        current_event = ""
        current_data: list[str] = []

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                status = response.getcode()
                for raw_bytes in response:
                    line = raw_bytes.decode("utf-8", errors="replace").rstrip("\r\n")
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
                            emitted = SseEvent(
                                event_id=current_id,
                                event_type=current_event,
                                data_text=data_text,
                                payload=parse_payload(data_text),
                            )
                            events.append(emitted)
                            if max_events is not None and len(events) >= max_events:
                                current_id = ""
                                current_event = ""
                                current_data = []
                                break
                            if stop_on_event_types and emitted.event_type in stop_on_event_types:
                                current_id = ""
                                current_event = ""
                                current_data = []
                                break
                        current_id = ""
                        current_event = ""
                        current_data = []
                if current_event:
                    # Why: some servers terminate SSE stream without a trailing blank line.
                    data_text = "\n".join(current_data)
                    emitted = SseEvent(
                        event_id=current_id,
                        event_type=current_event,
                        data_text=data_text,
                        payload=parse_payload(data_text),
                    )
                    events.append(emitted)
        except urllib.error.URLError as exc:
            raise ScenarioFailure(
                stage="sse_connect",
                message="sse request failed",
                details={
                    "url": url,
                    "reason": mask_secrets(str(exc.reason)),
                },
                runbook=RUNBOOK_SSE,
            ) from exc

        raw_text = "\n".join(raw_lines)
        return status, events, raw_text

class DbClient:
    def __init__(
        self,
        method: str,
        compose_file: str,
        compose_service: str,
        db_name: str,
        db_user: str,
        db_password: str,
        db_host: str,
        db_port: int,
    ) -> None:
        self.method = method
        self.compose_file = compose_file
        self.compose_service = compose_service
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_port = db_port

    def _run_psql(self, sql: str) -> tuple[list[str], int, str, str]:
        if self.method == "docker-exec":
            command = [
                "docker",
                "compose",
                "-f",
                self.compose_file,
                "exec",
                "-T",
                "-e",
                f"PGPASSWORD={self.db_password}",
                self.compose_service,
                "psql",
                "-U",
                self.db_user,
                "-d",
                self.db_name,
                "-At",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                sql,
            ]
            code, out, err = shell_command(command)
        else:
            command = [
                "psql",
                "-h",
                self.db_host,
                "-p",
                str(self.db_port),
                "-U",
                self.db_user,
                "-d",
                self.db_name,
                "-At",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                sql,
            ]
            env = dict(os.environ)
            env["PGPASSWORD"] = self.db_password
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                env=env,
            )
            code, out, err = completed.returncode, completed.stdout or "", completed.stderr or ""

        return command, code, out, err

    def execute_sql(self, sql: str, stage: str = "db_execute") -> str:
        command, code, out, err = self._run_psql(sql)
        if code != 0:
            raise ScenarioFailure(
                stage=stage,
                message="db execution failed",
                details={
                    "command": " ".join(command[:-1]) + " <SQL>",
                    "stderr": mask_secrets(err.strip()),
                    "stdout": mask_secrets(out.strip()),
                },
            )
        return out.strip()

    def query_json(self, sql: str) -> Any:
        command, code, out, err = self._run_psql(sql)

        if code != 0:
            raise ScenarioFailure(
                stage="db_query",
                message="db query failed",
                details={
                    "command": " ".join(command[:-1]) + " <SQL>",
                    "stderr": mask_secrets(err.strip()),
                    "stdout": mask_secrets(out.strip()),
                },
            )

        payload = json_loads_safe(out.strip())
        if payload is None:
            raise ScenarioFailure(
                stage="db_parse",
                message="db output was not valid JSON",
                details={"output": mask_secrets(out.strip())},
            )
        return payload


class E2ESmokeRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.http = HttpClient(args.base_url, args.timeout_sec)
        self.db = DbClient(
            method=args.db_method,
            compose_file=args.compose_file,
            compose_service=args.compose_service,
            db_name=args.db_name,
            db_user=args.db_user,
            db_password=args.db_password,
            db_host=args.db_host,
            db_port=args.db_port,
        )
        self.trace_lines: list[str] = []
        self.context: dict[str, Any] = {}

    def _set_last_trace_id(self, trace_id: str) -> None:
        self.context["last_trace_id"] = trace_id

    def _seed_uuid(self, tenant_key: str, purpose: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"e2e-smoke:{tenant_key}:{purpose}"))

    def _load_tenant_id(self, tenant_key: str) -> str:
        tenant_literal = quote_sql(tenant_key)
        payload = self.db.query_json(
            "SELECT json_build_object("
            "'tenant_id', COALESCE((SELECT id::text FROM tb_tenant WHERE tenant_key = " + tenant_literal + " LIMIT 1), '')"
            ")::text;"
        )
        tenant_id = ""
        if isinstance(payload, dict):
            tenant_id = str(payload.get("tenant_id", "")).strip()
        if tenant_id == "":
            raise ScenarioFailure(
                stage="kb_seed_tenant_lookup",
                message="tenant_key not found for KB seed",
                details={"tenant_key": tenant_key},
                runbook=RUNBOOK_SSE,
            )
        return tenant_id

    def ensure_kb_seed(self, tenant_key: str) -> None:
        if self.args.skip_kb_seed:
            self.trace_lines.append("s1.kb_seed=SKIPPED")
            return

        tenant_id = self._load_tenant_id(tenant_key)
        document_id = self._seed_uuid(tenant_key, "document")
        version_id = self._seed_uuid(tenant_key, "document_version")
        chunk_id = self._seed_uuid(tenant_key, "chunk")
        embedding_id = self._seed_uuid(tenant_key, "embedding")
        now_expr = "CURRENT_TIMESTAMP"
        chunk_text = (
            "refund policy states that approved refunds are processed to the original payment method "
            "within 3 to 5 business days."
        )
        normalized_chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()

        self.db.execute_sql(
            "INSERT INTO tb_kb_document (id, tenant_id, title, source_type, category, effective_date, owner, created_at, updated_at) "
            "VALUES ("
            + quote_sql(document_id)
            + "::uuid, "
            + quote_sql(tenant_id)
            + "::uuid, "
            + quote_sql("e2e_refund_policy")
            + ", "
            + quote_sql("policy")
            + ", "
            + quote_sql("CS")
            + ", CURRENT_DATE, "
            + quote_sql("e2e-smoke")
            + ", "
            + now_expr
            + ", "
            + now_expr
            + ") "
            "ON CONFLICT (id) DO UPDATE SET "
            "title = EXCLUDED.title, "
            "source_type = EXCLUDED.source_type, "
            "category = EXCLUDED.category, "
            "effective_date = EXCLUDED.effective_date, "
            "owner = EXCLUDED.owner, "
            "updated_at = CURRENT_TIMESTAMP;",
            stage="kb_seed_document",
        )

        self.db.execute_sql(
            "INSERT INTO tb_kb_document_version (id, tenant_id, document_id, version_no, status, approved_at, created_at, updated_at) "
            "VALUES ("
            + quote_sql(version_id)
            + "::uuid, "
            + quote_sql(tenant_id)
            + "::uuid, "
            + quote_sql(document_id)
            + "::uuid, 1, 'approved', CURRENT_TIMESTAMP, "
            + now_expr
            + ", "
            + now_expr
            + ") "
            "ON CONFLICT (id) DO UPDATE SET "
            "status = 'approved', "
            "approved_at = COALESCE(tb_kb_document_version.approved_at, CURRENT_TIMESTAMP), "
            "updated_at = CURRENT_TIMESTAMP;",
            stage="kb_seed_document_version",
        )

        self.db.execute_sql(
            "INSERT INTO tb_kb_chunk (id, tenant_id, document_version_id, chunk_no, chunk_hash, chunk_text, token_count, context_header, summary_text, created_at, updated_at) "
            "VALUES ("
            + quote_sql(chunk_id)
            + "::uuid, "
            + quote_sql(tenant_id)
            + "::uuid, "
            + quote_sql(version_id)
            + "::uuid, 1, "
            + quote_sql(normalized_chunk_hash)
            + ", "
            + quote_sql(chunk_text)
            + ", 32, "
            + quote_sql("[DOC] e2e_refund_policy | ver=1 | chunk=1/1 | source=policy | category=CS | owner=e2e-smoke")
            + ", "
            + quote_sql("approved refund takes 3 to 5 business days.")
            + ", "
            + now_expr
            + ", "
            + now_expr
            + ") "
            "ON CONFLICT (id) DO UPDATE SET "
            "chunk_hash = EXCLUDED.chunk_hash, "
            "chunk_text = EXCLUDED.chunk_text, "
            "token_count = EXCLUDED.token_count, "
            "context_header = EXCLUDED.context_header, "
            "summary_text = EXCLUDED.summary_text, "
            "updated_at = CURRENT_TIMESTAMP;",
            stage="kb_seed_chunk",
        )

        self.db.execute_sql(
            "INSERT INTO tb_kb_chunk_embedding (id, tenant_id, chunk_id, embedding_vector, embedding_dim, model, embedding_input_text, created_at, updated_at) "
            "VALUES ("
            + quote_sql(embedding_id)
            + "::uuid, "
            + quote_sql(tenant_id)
            + "::uuid, "
            + quote_sql(chunk_id)
            + "::uuid, "
            + quote_sql("[0.31,0.12,0.09]")
            + ", 1536, "
            + quote_sql("e2e-embedding-v1")
            + ", "
            + quote_sql(
                "[DOC] e2e_refund_policy | ver=1 | chunk=1/1\napproved refund takes 3 to 5 business days."
            )
            + ", "
            + now_expr
            + ", "
            + now_expr
            + ") "
            "ON CONFLICT (tenant_id, chunk_id) DO UPDATE SET "
            "embedding_vector = EXCLUDED.embedding_vector, "
            "embedding_dim = EXCLUDED.embedding_dim, "
            "model = EXCLUDED.model, "
            "embedding_input_text = EXCLUDED.embedding_input_text, "
            "updated_at = CURRENT_TIMESTAMP;",
            stage="kb_seed_embedding",
        )

        count_payload = self.db.query_json(
            "SELECT json_build_object("
            "'approved_chunk_count', ("
            "SELECT COUNT(*) FROM tb_kb_chunk c "
            "JOIN tb_kb_document_version dv ON dv.id = c.document_version_id AND dv.tenant_id = c.tenant_id "
            "WHERE c.tenant_id = "
            + quote_sql(tenant_id)
            + "::uuid AND dv.status = 'approved'"
            ")"
            ")::text;"
        )
        approved_count = 0
        if isinstance(count_payload, dict):
            value = count_payload.get("approved_chunk_count")
            approved_count = int(value) if isinstance(value, int) else int(str(value or "0"))
        if approved_count <= 0:
            raise ScenarioFailure(
                stage="kb_seed_verify",
                message="approved KB chunk count was zero after seed",
                details={"tenant_key": tenant_key},
                runbook=RUNBOOK_SSE,
            )

        self.trace_lines.append(
            "s1.kb_seed="
            + f"tenant={tenant_key},document_id={document_id},version_id={version_id},chunk_id={chunk_id},approved_chunks={approved_count}"
        )

    def _headers(self, trace_id: str, tenant_key: str, token: str | None = None, idem: bool = False) -> dict[str, str]:
        headers = {
            "X-Trace-Id": trace_id,
            "X-Tenant-Key": tenant_key,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if idem:
            headers["Idempotency-Key"] = str(uuid.uuid4())
        return headers

    def _auth_headers(self, trace_id: str, tenant_key: str, token: str, idem: bool = False) -> dict[str, str]:
        headers = self._headers(trace_id, tenant_key, token=token, idem=idem)
        missing: list[str] = []
        for key in ("X-Trace-Id", "X-Tenant-Key", "Authorization"):
            value = str(headers.get(key, "")).strip()
            if value == "":
                missing.append(key)
        if missing:
            raise ScenarioFailure(
                stage="request_header_contract",
                message=f"required headers missing: {missing}",
                details={"missing_headers": missing},
                runbook=RUNBOOK_RBAC,
            )
        return headers

    def login(self) -> tuple[str, str]:
        login_trace = create_trace_id()
        tenant_key = self.args.auth_tenant_key or self.args.tenant_key
        body = {
            "login_id": self.args.login_id,
            "password": self.args.password,
            "channel_id": self.args.channel_id,
            "client_nonce": "smoke-login",
        }
        response = self.http.request_json(
            "POST",
            "/v1/auth/login",
            self._headers(login_trace, tenant_key, idem=True),
            body=body,
        )

        if response.status != 201:
            if self.args.allow_demo_auth_fallback and tenant_key != "demo-tenant":
                fallback = self.http.request_json(
                    "POST",
                    "/v1/auth/login",
                    self._headers(create_trace_id(), "demo-tenant", idem=True),
                    body=body,
                )
                if fallback.status == 201 and isinstance(fallback.body_json, dict):
                    token = str(fallback.body_json.get("access_token", ""))
                    if token:
                        self.trace_lines.append("auth_fallback=demo-tenant")
                        return token, "demo-tenant"
            raise ScenarioFailure(
                stage="login",
                message=f"login failed status={response.status}",
                error_code=self._error_code(response.body_json),
                details={"tenant_key": tenant_key, "body": mask_secrets(response.body_text[:500])},
                runbook=RUNBOOK_RBAC,
            )

        if not isinstance(response.body_json, dict):
            raise ScenarioFailure(stage="login_parse", message="login response was not JSON")
        token = str(response.body_json.get("access_token", ""))
        if token == "":
            raise ScenarioFailure(stage="login_parse", message="access_token missing in login response")
        return token, tenant_key

    @staticmethod
    def _error_code(body_json: Any) -> str:
        if isinstance(body_json, dict):
            value = body_json.get("error_code")
            return "" if value is None else str(value)
        return ""

    def create_session(self, token: str, tenant_key: str, trace_id: str) -> str:
        response = self.http.request_json(
            "POST",
            "/v1/sessions",
            self._auth_headers(trace_id, tenant_key, token=token, idem=True),
            body={},
        )
        if response.status != 201:
            raise ScenarioFailure(
                stage="create_session",
                message=f"create session failed status={response.status}",
                error_code=self._error_code(response.body_json),
                details={"body": mask_secrets(response.body_text[:500])},
            )
        if not isinstance(response.body_json, dict):
            raise ScenarioFailure(stage="create_session_parse", message="create session response was not JSON")
        session_id = str(response.body_json.get("session_id", ""))
        if session_id == "":
            raise ScenarioFailure(stage="create_session_parse", message="session_id missing")
        return session_id

    def post_message(self, token: str, tenant_key: str, session_id: str, trace_id: str, text: str, top_k: int) -> str:
        response = self.http.request_json(
            "POST",
            f"/v1/sessions/{session_id}/messages",
            self._auth_headers(trace_id, tenant_key, token=token, idem=True),
            body={
                "text": text,
                "top_k": top_k,
                "client_nonce": "smoke-message",
            },
        )
        if response.status != 202:
            raise ScenarioFailure(
                stage="post_message",
                message=f"post message failed status={response.status}",
                error_code=self._error_code(response.body_json),
                details={"body": mask_secrets(response.body_text[:500])},
            )
        if not isinstance(response.body_json, dict):
            raise ScenarioFailure(stage="post_message_parse", message="post message response was not JSON")
        message_id = str(response.body_json.get("id", ""))
        if message_id == "":
            raise ScenarioFailure(stage="post_message_parse", message="message id missing")
        return message_id

    def load_trace_evidence(self, tenant_key: str, session_id: str, message_id: str) -> DbTraceEvidence:
        tenant_literal = quote_sql(tenant_key)
        session_literal = quote_sql(session_id)
        message_literal = quote_sql(message_id)
        sql = (
            "SELECT json_build_object("  # noqa: E131
            "'message_trace_id', ("
            "  SELECT COALESCE(trace_id::text, '') FROM tb_message "
            "  WHERE id = " + message_literal + "::uuid "
            "    AND tenant_id = (SELECT id FROM tb_tenant WHERE tenant_key = " + tenant_literal + ") "
            "  LIMIT 1"
            "),"
            "'rag_trace_id', ("
            "  SELECT COALESCE(trace_id::text, '') FROM tb_rag_search_log "
            "  WHERE conversation_id = " + session_literal + "::uuid "
            "    AND tenant_id = (SELECT id FROM tb_tenant WHERE tenant_key = " + tenant_literal + ") "
            "  ORDER BY created_at DESC LIMIT 1"
            "),"
            "'stream_event_types', COALESCE(("
            "  SELECT json_agg(event_type ORDER BY event_seq) FROM tb_stream_event "
            "  WHERE message_id = " + message_literal + "::uuid "
            "    AND tenant_id = (SELECT id FROM tb_tenant WHERE tenant_key = " + tenant_literal + ")"
            "), '[]'::json)"
            ")::text;"
        )
        payload = self.db.query_json(sql)
        if not isinstance(payload, dict):
            raise ScenarioFailure(stage="trace_db_parse", message="trace evidence payload malformed")
        stream_types = payload.get("stream_event_types", [])
        if not isinstance(stream_types, list):
            stream_types = []
        return DbTraceEvidence(
            message_trace_id=str(payload.get("message_trace_id", "")),
            rag_trace_id=str(payload.get("rag_trace_id", "")),
            stream_event_types=[str(item) for item in stream_types],
        )

    def fetch_citations(self, token: str, tenant_key: str, message_id: str, trace_id: str) -> list[dict[str, Any]]:
        response = self.http.request_json(
            "GET",
            f"/v1/rag/answers/{message_id}/citations",
            self._auth_headers(trace_id, tenant_key, token=token),
            body=None,
        )
        if response.status != 200:
            raise ScenarioFailure(
                stage="citations",
                message=f"citations query failed status={response.status}",
                error_code=self._error_code(response.body_json),
                details={"body": mask_secrets(response.body_text[:500])},
            )
        if not isinstance(response.body_json, dict):
            raise ScenarioFailure(stage="citations_parse", message="citations response was not JSON object")
        data = response.body_json.get("data")
        if not isinstance(data, list):
            raise ScenarioFailure(stage="citations_parse", message="citations data missing or invalid")
        return [item for item in data if isinstance(item, dict)]

    def close_session(self, token: str, tenant_key: str, session_id: str, trace_id: str) -> None:
        response = self.http.request_json(
            "POST",
            f"/v1/sessions/{session_id}/close",
            self._auth_headers(trace_id, tenant_key, token=token),
            body={"reason": "e2e smoke"},
        )
        if response.status != 200:
            raise ScenarioFailure(
                stage="close_session",
                message=f"close session failed status={response.status}",
                error_code=self._error_code(response.body_json),
                details={"body": mask_secrets(response.body_text[:500])},
            )

    def stream_all(self, token: str, tenant_key: str, session_id: str, message_id: str, trace_id: str) -> tuple[list[SseEvent], str]:
        status, events, raw = self.http.read_sse(
            f"/v1/sessions/{session_id}/messages/{message_id}/stream",
            self._auth_headers(trace_id, tenant_key, token=token),
            max_events=None,
            stop_on_event_types={"done"},
        )
        if status != 200:
            raise ScenarioFailure(stage="stream", message=f"stream failed status={status}")
        if not events:
            raise ScenarioFailure(stage="stream", message="stream returned no events")
        return events, raw

    def stream_resume(
        self,
        token: str,
        tenant_key: str,
        session_id: str,
        message_id: str,
        trace_id: str,
        last_event_id: str,
    ) -> tuple[list[SseEvent], str]:
        query = urllib.parse.urlencode({"last_event_id": last_event_id})
        status, events, raw = self.http.read_sse(
            f"/v1/sessions/{session_id}/messages/{message_id}/stream/resume?{query}",
            self._auth_headers(trace_id, tenant_key, token=token),
            max_events=None,
            stop_on_event_types={"done"},
        )
        if status != 200:
            raise ScenarioFailure(stage="stream_resume", message=f"stream resume failed status={status}")
        return events, raw

    def scenario_s1(self, token: str, tenant_key: str) -> ScenarioResult:
        trace_flow = create_trace_id()
        self._set_last_trace_id(trace_flow)
        self.ensure_kb_seed(tenant_key)
        session_id = self.create_session(token, tenant_key, trace_flow)
        message_id = self.post_message(
            token,
            tenant_key,
            session_id,
            trace_flow,
            self.args.s1_query_text,
            self.args.s1_top_k,
        )
        events, _ = self.stream_all(token, tenant_key, session_id, message_id, trace_flow)

        event_types = [event.event_type for event in events]
        required = set(S1_REQUIRED_EVENTS)
        missing = [name for name in required if name not in event_types]
        if missing:
            safe_payloads = []
            error_payloads = []
            for event in events:
                if event.event_type == "safe_response":
                    safe_payloads.append(mask_secrets(event.data_text))
                if event.event_type == "error":
                    error_payloads.append(mask_secrets(event.data_text))
            raise ScenarioFailure(
                stage="s1_stream_contract",
                message=f"S1 missing required SSE events: {missing}",
                details={
                    "event_types": event_types,
                    "safe_response_payloads": safe_payloads,
                    "error_payloads": error_payloads,
                    "request_header_contract": {
                        "x_trace_id": "present",
                        "x_tenant_key": "present",
                        "authorization": "present",
                    },
                },
                runbook=RUNBOOK_SSE,
            )

        if "safe_response" in event_types or "error" in event_types:
            raise ScenarioFailure(
                stage="s1_stream_contract",
                message="S1 received fail-closed events in normal flow",
                details={
                    "event_types": event_types,
                    "request_header_contract": {
                        "x_trace_id": "present",
                        "x_tenant_key": "present",
                        "authorization": "present",
                    },
                },
                runbook=RUNBOOK_SSE,
            )

        citations = self.fetch_citations(token, tenant_key, message_id, trace_flow)
        if not citations:
            raise ScenarioFailure(
                stage="s1_citations",
                message="citations list was empty",
                runbook=RUNBOOK_FAIL_CLOSED,
            )

        self.close_session(token, tenant_key, session_id, create_trace_id())

        trace_db = self.load_trace_evidence(tenant_key, session_id, message_id)
        if trace_db.message_trace_id == "":
            raise ScenarioFailure(
                stage="s1_trace_db",
                message="tb_message.trace_id missing",
                details={"expected": trace_flow, "actual": trace_db.message_trace_id},
                runbook=RUNBOOK_RBAC,
            )
        if trace_db.message_trace_id != trace_flow:
            raise ScenarioFailure(
                stage="s1_trace_db",
                message="tb_message.trace_id mismatch",
                details={"expected": trace_flow, "actual": trace_db.message_trace_id},
                runbook=RUNBOOK_RBAC,
            )
        if trace_db.rag_trace_id == "":
            raise ScenarioFailure(
                stage="s1_trace_db",
                message="tb_rag_search_log.trace_id missing",
                details={"expected": trace_flow, "actual": trace_db.rag_trace_id},
                runbook=RUNBOOK_RBAC,
            )
        if trace_db.rag_trace_id != trace_flow:
            raise ScenarioFailure(
                stage="s1_trace_db",
                message="tb_rag_search_log.trace_id mismatch",
                details={"expected": trace_flow, "actual": trace_db.rag_trace_id},
                runbook=RUNBOOK_RBAC,
            )

        payload_trace_ids: list[str] = []
        for event in events:
            if isinstance(event.payload, dict):
                trace_value = str(event.payload.get("trace_id", "")).strip()
                if trace_value:
                    payload_trace_ids.append(trace_value)
        if payload_trace_ids and any(trace != trace_flow for trace in payload_trace_ids):
            raise ScenarioFailure(
                stage="s1_trace_stream",
                message="SSE payload trace_id mismatch",
                details={"expected": trace_flow, "actual_values": payload_trace_ids},
                runbook=RUNBOOK_RBAC,
            )

        self.context["s1_session_id"] = session_id
        self.context["s1_message_id"] = message_id
        self.context["s1_trace_id"] = trace_flow
        self.context["s1_event_types"] = event_types
        self.context["s1_db_stream_event_types"] = trace_db.stream_event_types

        self.trace_lines.extend(
            [
                f"s1.trace_id={trace_flow}",
                f"s1.session_id={session_id}",
                f"s1.message_id={message_id}",
                f"s1.sse_event_types={','.join(event_types)}",
                f"s1.db_message_trace_id={trace_db.message_trace_id}",
                f"s1.db_rag_trace_id={trace_db.rag_trace_id}",
                f"s1.db_stream_events={','.join(trace_db.stream_event_types)}",
            ]
        )

        return ScenarioResult(
            scenario_id="S1",
            name="session-message-sse-citations-close",
            status="PASS",
            stage="complete",
            trace_id=trace_flow,
            error_code="",
            message="S1 passed",
            runbook=RUNBOOK_INDEX,
            details={
                "session_id": session_id,
                "message_id": message_id,
                "event_types": event_types,
                "db_stream_event_types": trace_db.stream_event_types,
                "citation_count": len(citations),
            },
        )

    def scenario_s2(self, token: str, tenant_key: str) -> ScenarioResult:
        trace_id = create_trace_id()
        self._set_last_trace_id(trace_id)
        session_id = self.create_session(token, tenant_key, trace_id)
        message_id = self.post_message(token, tenant_key, session_id, trace_id, "refund policy", 3)

        status, partial_events, _ = self.http.read_sse(
            f"/v1/sessions/{session_id}/messages/{message_id}/stream",
            self._headers(trace_id, tenant_key, token=token),
            max_events=3,
        )
        if status != 200:
            raise ScenarioFailure(stage="s2_stream_partial", message=f"partial stream failed status={status}")

        partial_ids = [event.event_id for event in partial_events if event.event_id != ""]
        if not partial_ids:
            raise ScenarioFailure(stage="s2_stream_partial", message="partial stream did not provide event id")

        last_event_id = partial_ids[-1]
        resume_trace = create_trace_id()
        resumed_events, _ = self.stream_resume(token, tenant_key, session_id, message_id, resume_trace, last_event_id)
        resumed_ids = [event.event_id for event in resumed_events if event.event_id != ""]

        for item in resumed_ids:
            if item.isdigit() and last_event_id.isdigit() and int(item) <= int(last_event_id):
                raise ScenarioFailure(
                    stage="s2_resume_order",
                    message="resume replayed old or equal event id",
                    details={"last_event_id": last_event_id, "resumed_ids": resumed_ids},
                    runbook=RUNBOOK_SSE,
                )

        resumed_types = [event.event_type for event in resumed_events]
        if "done" not in resumed_types:
            raise ScenarioFailure(
                stage="s2_resume_done",
                message="resume stream missing done event",
                details={"resumed_event_types": resumed_types},
                runbook=RUNBOOK_SSE,
            )

        self.trace_lines.extend(
            [
                f"s2.trace_id={trace_id}",
                f"s2.resume_trace_id={resume_trace}",
                f"s2.last_event_id={last_event_id}",
                f"s2.resumed_event_ids={','.join(resumed_ids)}",
            ]
        )

        return ScenarioResult(
            scenario_id="S2",
            name="network-drop-and-resume",
            status="PASS",
            stage="complete",
            trace_id=trace_id,
            error_code="",
            message="S2 passed",
            runbook=RUNBOOK_INDEX,
            details={
                "session_id": session_id,
                "message_id": message_id,
                "partial_event_ids": partial_ids,
                "resumed_event_ids": resumed_ids,
                "resumed_event_types": resumed_types,
            },
        )

    def _load_backend_log_text(self) -> str:
        if self.args.backend_log_file:
            path = Path(self.args.backend_log_file)
            if path.exists():
                return path.read_text(encoding="utf-8", errors="replace")

        command = [
            "docker",
            "compose",
            "-f",
            self.args.compose_file,
            "logs",
            "--no-color",
            "--tail",
            str(self.args.log_tail_lines),
            self.args.backend_log_service,
        ]
        code, out, _ = shell_command(command)
        if code == 0 and out.strip() != "":
            return out

        if self.args.skip_log_check:
            return ""

        raise ScenarioFailure(
            stage="s3_log_source",
            message="backend log source unavailable (provide --backend-log-file or running compose backend)",
            runbook=RUNBOOK_PII,
        )

    def scenario_s3(self, token: str, tenant_key: str) -> ScenarioResult:
        trace_id = create_trace_id()
        self._set_last_trace_id(trace_id)
        session_id = self.create_session(token, tenant_key, trace_id)
        pii_text = (
            "refund policy. contact "
            + PII_EMAIL
            + " or +82 10-9876-5432 order "
            + PII_ORDER
        )
        message_id = self.post_message(token, tenant_key, session_id, trace_id, pii_text, 3)
        events, raw_stream = self.stream_all(token, tenant_key, session_id, message_id, trace_id)

        if contains_raw_pii(raw_stream):
            raise ScenarioFailure(
                stage="s3_stream_masking",
                message="raw PII found in SSE stream output",
                runbook=RUNBOOK_PII,
            )

        citations = self.fetch_citations(token, tenant_key, message_id, create_trace_id())
        excerpt_blob = "\n".join(str(item.get("excerpt_masked", "")) for item in citations)
        if contains_raw_pii(excerpt_blob):
            raise ScenarioFailure(
                stage="s3_citation_masking",
                message="raw PII found in citation excerpt",
                runbook=RUNBOOK_PII,
            )

        if not self.args.skip_db_check:
            tenant_literal = quote_sql(tenant_key)
            session_literal = quote_sql(session_id)
            message_literal = quote_sql(message_id)
            pii_sql = (
                "SELECT json_build_object("
                "'query_text_masked', ("
                "  SELECT COALESCE(query_text_masked, '') FROM tb_rag_search_log "
                "  WHERE conversation_id = " + session_literal + "::uuid "
                "    AND tenant_id = (SELECT id FROM tb_tenant WHERE tenant_key = " + tenant_literal + ") "
                "  ORDER BY created_at DESC LIMIT 1"
                "),"
                "'citation_excerpt_masked', ("
                "  SELECT COALESCE(excerpt_masked, '') FROM tb_rag_citation "
                "  WHERE message_id = " + message_literal + "::uuid "
                "    AND tenant_id = (SELECT id FROM tb_tenant WHERE tenant_key = " + tenant_literal + ") "
                "  ORDER BY rank_no ASC LIMIT 1"
                ")"
                ")::text;"
            )
            pii_payload = self.db.query_json(pii_sql)
            if not isinstance(pii_payload, dict):
                raise ScenarioFailure(stage="s3_db_parse", message="S3 DB payload malformed", runbook=RUNBOOK_PII)

            masked_query = str(pii_payload.get("query_text_masked", ""))
            masked_excerpt = str(pii_payload.get("citation_excerpt_masked", ""))
            if contains_raw_pii(masked_query) or contains_raw_pii(masked_excerpt):
                raise ScenarioFailure(
                    stage="s3_db_masking",
                    message="raw PII found in DB masked fields",
                    details={
                        "query_preview": mask_secrets(masked_query[:120]),
                        "excerpt_preview": mask_secrets(masked_excerpt[:120]),
                    },
                    runbook=RUNBOOK_PII,
                )
        else:
            pii_payload = {"query_text_masked": "<SKIPPED>", "citation_excerpt_masked": "<SKIPPED>"}

        log_text = self._load_backend_log_text()
        if log_text and contains_raw_pii(log_text):
            raise ScenarioFailure(stage="s3_log_masking", message="raw PII found in backend logs", runbook=RUNBOOK_PII)

        self.trace_lines.extend(
            [
                f"s3.trace_id={trace_id}",
                f"s3.session_id={session_id}",
                f"s3.message_id={message_id}",
                "s3.pii_patterns=email/phone/order",
                f"s3.masked_query_preview={mask_secrets(str(pii_payload.get('query_text_masked', ''))[:160])}",
                f"s3.masked_excerpt_preview={mask_secrets(str(pii_payload.get('citation_excerpt_masked', ''))[:160])}",
            ]
        )

        return ScenarioResult(
            scenario_id="S3",
            name="pii-masking-in-storage-log-response",
            status="PASS",
            stage="complete",
            trace_id=trace_id,
            error_code="",
            message="S3 passed",
            runbook=RUNBOOK_INDEX,
            details={
                "session_id": session_id,
                "message_id": message_id,
                "stream_event_types": [event.event_type for event in events],
                "db_masked_query_present": str(pii_payload.get("query_text_masked", "")) != "",
                "db_masked_excerpt_present": str(pii_payload.get("citation_excerpt_masked", "")) != "",
                "log_check_skipped": self.args.skip_log_check,
                "db_check_skipped": self.args.skip_db_check,
            },
        )

    def scenario_s4(self, token: str, auth_tenant_key: str) -> ScenarioResult:
        trace_id = create_trace_id()
        self._set_last_trace_id(trace_id)
        session_id = str(self.context.get("s1_session_id", ""))
        if session_id == "":
            session_id = self.create_session(token, auth_tenant_key, trace_id)

        cross_tenant = self.args.cross_tenant_key
        if cross_tenant == auth_tenant_key:
            cross_tenant = "tenant-a" if auth_tenant_key != "tenant-a" else "tenant-budget"

        response = self.http.request_json(
            "GET",
            f"/v1/sessions/{session_id}",
            self._auth_headers(trace_id, cross_tenant, token=token),
            body=None,
        )

        if response.status not in (403, 404):
            raise ScenarioFailure(
                stage="s4_tenant_boundary",
                message=f"expected 403/404 for cross-tenant read, got {response.status}",
                error_code=self._error_code(response.body_json),
                details={"response_body": mask_secrets(response.body_text[:300]), "cross_tenant": cross_tenant},
                runbook=RUNBOOK_RBAC,
            )

        self.trace_lines.append(f"s4.trace_id={trace_id} cross_tenant={cross_tenant} status={response.status}")

        return ScenarioResult(
            scenario_id="S4",
            name="tenant-isolation-cross-tenant-session-read",
            status="PASS",
            stage="complete",
            trace_id=trace_id,
            error_code="",
            message="S4 passed",
            runbook=RUNBOOK_INDEX,
            details={
                "session_id": session_id,
                "auth_tenant_key": auth_tenant_key,
                "cross_tenant_key": cross_tenant,
                "status": response.status,
            },
        )

    def scenario_s5(self, token: str, tenant_key: str) -> ScenarioResult:
        trace_id = create_trace_id()
        self._set_last_trace_id(trace_id)
        response = self.http.request_json(
            "GET",
            self.args.admin_probe_path,
            self._auth_headers(trace_id, tenant_key, token=token),
            body=None,
        )
        if response.status != 403:
            raise ScenarioFailure(
                stage="s5_rbac",
                message=f"expected 403 for unauthorized admin endpoint, got {response.status}",
                error_code=self._error_code(response.body_json),
                details={"path": self.args.admin_probe_path, "body": mask_secrets(response.body_text[:300])},
                runbook=RUNBOOK_RBAC,
            )
        self.trace_lines.append(f"s5.trace_id={trace_id} path={self.args.admin_probe_path} status=403")
        return ScenarioResult(
            scenario_id="S5",
            name="rbac-403-for-admin-endpoint",
            status="PASS",
            stage="complete",
            trace_id=trace_id,
            error_code="",
            message="S5 passed",
            runbook=RUNBOOK_INDEX,
            details={"path": self.args.admin_probe_path, "status": 403},
        )

    def scenario_s6(self, token: str, tenant_key: str) -> ScenarioResult:
        trace_id = create_trace_id()
        self._set_last_trace_id(trace_id)
        session_id = self.create_session(token, tenant_key, trace_id)
        message_id = self.post_message(
            token,
            tenant_key,
            session_id,
            trace_id,
            self.args.s6_fail_closed_text,
            1,
        )
        events, _ = self.stream_all(token, tenant_key, session_id, message_id, trace_id)
        event_types = [event.event_type for event in events]

        missing_required = [name for name in S6_REQUIRED_EVENTS if name not in event_types]
        present_forbidden = [name for name in S6_FORBIDDEN_EVENTS if name in event_types]
        if missing_required or present_forbidden:
            raise ScenarioFailure(
                stage="s6_fail_closed",
                message="expected deterministic fail-closed SSE event contract",
                details={
                    "event_types": event_types,
                    "missing_required_events": missing_required,
                    "forbidden_events_present": present_forbidden,
                    "expected_required_events": list(S6_REQUIRED_EVENTS),
                    "expected_forbidden_events": list(S6_FORBIDDEN_EVENTS),
                },
                runbook=RUNBOOK_FAIL_CLOSED,
            )
        if self.args.s6_require_error_event and "error" not in event_types:
            raise ScenarioFailure(
                stage="s6_fail_closed",
                message="expected error event for deterministic fail-closed probe",
                details={
                    "event_types": event_types,
                    "expected_error_code": self.args.s6_expected_error_code,
                    "hint": "enable e2e force-fail-closed hook (APP_E2E_FORCE_FAIL_CLOSED_ENABLED=true)",
                },
                runbook=RUNBOOK_FAIL_CLOSED,
            )

        error_codes: list[str] = []
        for event in events:
            if event.event_type == "error" and isinstance(event.payload, dict):
                code = str(event.payload.get("error_code", "")).strip()
                if code:
                    error_codes.append(code)
        if self.args.s6_require_error_event:
            expected_code = self.args.s6_expected_error_code.strip()
            if expected_code and expected_code not in error_codes:
                raise ScenarioFailure(
                    stage="s6_fail_closed",
                    message="unexpected fail-closed error_code",
                    details={
                        "expected_error_code": expected_code,
                        "actual_error_codes": error_codes,
                        "event_types": event_types,
                    },
                    runbook=RUNBOOK_FAIL_CLOSED,
                )

        self.trace_lines.append(
            "s6.trace_id=" + trace_id + " event_types=" + ",".join(event_types) + " error_codes=" + ",".join(error_codes)
        )

        return ScenarioResult(
            scenario_id="S6",
            name="answer-contract-fail-closed",
            status="PASS",
            stage="complete",
            trace_id=trace_id,
            error_code=error_codes[0] if error_codes else "",
            message="S6 passed",
            runbook=RUNBOOK_INDEX,
            details={
                "session_id": session_id,
                "message_id": message_id,
                "event_types": event_types,
                "error_codes": error_codes,
            },
        )

    def execute(self) -> dict[str, Any]:
        token, effective_auth_tenant_key = self.login()
        scenario_functions = [
            ("S1", "session-message-sse-citations-close", lambda: self.scenario_s1(token, effective_auth_tenant_key)),
            ("S2", "network-drop-and-resume", lambda: self.scenario_s2(token, effective_auth_tenant_key)),
            ("S3", "pii-masking-in-storage-log-response", lambda: self.scenario_s3(token, effective_auth_tenant_key)),
            ("S4", "tenant-isolation-cross-tenant-session-read", lambda: self.scenario_s4(token, effective_auth_tenant_key)),
            ("S5", "rbac-403-for-admin-endpoint", lambda: self.scenario_s5(token, effective_auth_tenant_key)),
            ("S6", "answer-contract-fail-closed", lambda: self.scenario_s6(token, effective_auth_tenant_key)),
        ]

        results: list[ScenarioResult] = []
        for scenario_id, scenario_name, runner in scenario_functions:
            try:
                result = runner()
                results.append(result)
            except ScenarioFailure as exc:
                results.append(
                    ScenarioResult(
                        scenario_id=scenario_id,
                        name=scenario_name,
                        status="FAIL",
                        stage=exc.stage,
                        trace_id=str(self.context.get("last_trace_id", self.context.get("s1_trace_id", ""))),
                        error_code=exc.error_code,
                        message=str(exc),
                        runbook=exc.runbook,
                        details=exc.details,
                    )
                )
            except Exception as exc:  # pragma: no cover
                results.append(
                    ScenarioResult(
                        scenario_id=scenario_id,
                        name=scenario_name,
                        status="FAIL",
                        stage="unexpected_exception",
                        trace_id=str(self.context.get("last_trace_id", self.context.get("s1_trace_id", ""))),
                        error_code="",
                        message=str(exc),
                        runbook=RUNBOOK_INDEX,
                        details={"traceback": traceback.format_exc(limit=10)},
                    )
                )

        passed = sum(1 for item in results if item.status == "PASS")
        failed = sum(1 for item in results if item.status == "FAIL")
        first_failure = next((item for item in results if item.status == "FAIL"), None)
        reason_code = REASON_NONE if failed == 0 else REASON_SCENARIO_FAILURE

        payload = {
            "generated_at_utc": utc_now_iso(),
            "base_url": self.args.base_url,
            "target_tenant_key": self.args.tenant_key,
            "auth_tenant_key": self.args.auth_tenant_key,
            "effective_auth_tenant_key": effective_auth_tenant_key,
            "role": self.args.role,
            "status": STATUS_PASS if failed == 0 else STATUS_FAIL,
            "reason_code": reason_code,
            "remediation_hint": remediation_hint_for(reason_code),
            "summary": {
                "scenario_total": len(results),
                "scenario_pass": passed,
                "scenario_fail": failed,
            },
            "scenarios": [asdict(item) for item in results],
            "trace_context": {
                "flow_trace_id": self.context.get("s1_trace_id", ""),
                "flow_session_id": self.context.get("s1_session_id", ""),
                "flow_message_id": self.context.get("s1_message_id", ""),
                "flow_event_types": self.context.get("s1_event_types", []),
                "flow_db_stream_event_types": self.context.get("s1_db_stream_event_types", []),
            },
            "runbook_on_failure": first_failure.runbook if first_failure else RUNBOOK_INDEX,
        }
        return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run operational E2E smoke for counselor core flow")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--preflight-timeout-sec", type=int, default=3)
    parser.add_argument("--tenant-key", default="demo-tenant")
    parser.add_argument("--auth-tenant-key", default="")
    parser.add_argument("--cross-tenant-key", default="tenant-a")
    parser.add_argument("--role", default="AGENT")
    parser.add_argument("--login-id", default="agent1")
    parser.add_argument("--password", default="agent1-pass")
    parser.add_argument("--channel-id", default="test")
    parser.add_argument("--admin-probe-path", default="/v1/admin/templates")
    parser.add_argument("--s1-query-text", default=DEFAULT_S1_QUERY)
    parser.add_argument("--s1-top-k", type=int, default=DEFAULT_S1_TOP_K)
    parser.add_argument("--s6-fail-closed-text", default=DEFAULT_S6_FORCE_FAIL_CLOSED_TEXT)
    parser.add_argument(
        "--s6-expected-error-code",
        default=DEFAULT_S6_FORCE_FAIL_CLOSED_ERROR_CODE,
    )
    parser.add_argument("--s6-require-error-event", action="store_true", default=True)
    parser.add_argument("--s6-allow-no-error-event", action="store_true")
    parser.add_argument("--skip-kb-seed", action="store_true")

    parser.add_argument("--timeout-sec", type=int, default=90)
    parser.add_argument("--allow-demo-auth-fallback", action="store_true", default=True)
    parser.add_argument("--disable-demo-auth-fallback", action="store_true")

    parser.add_argument("--skip-db-check", action="store_true")
    parser.add_argument("--skip-log-check", action="store_true")
    parser.add_argument("--backend-log-file", default="")
    parser.add_argument("--backend-log-service", default="backend")
    parser.add_argument("--log-tail-lines", type=int, default=400)

    parser.add_argument("--db-method", choices=("docker-exec", "local-psql"), default="docker-exec")
    parser.add_argument("--compose-file", default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--compose-service", default=DEFAULT_COMPOSE_SERVICE)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument("--db-user", default=DEFAULT_DB_USER)
    parser.add_argument("--db-password", default=DEFAULT_DB_PASSWORD)
    parser.add_argument("--db-host", default=DEFAULT_DB_HOST)
    parser.add_argument("--db-port", type=int, default=DEFAULT_DB_PORT)

    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--output-report-json", default="")
    parser.add_argument("--output-trace-txt", default="")
    parser.add_argument("--out", default="", help="Alias for --output-report-json")
    parser.add_argument("--trace-out", default="", help="Alias for --output-trace-txt")
    return parser.parse_args()


def build_output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    artifact_dir = Path(args.artifact_dir)
    ensure_dir(artifact_dir)
    tag = date_tag_local()
    report_override = args.output_report_json or args.out
    trace_override = args.output_trace_txt or args.trace_out
    report_path = (
        Path(report_override)
        if report_override
        else artifact_dir / f"{DEFAULT_REPORT_PREFIX}_{tag}.json"
    )
    trace_path = (
        Path(trace_override)
        if trace_override
        else artifact_dir / f"{DEFAULT_TRACE_PREFIX}_{tag}.txt"
    )
    return report_path, trace_path


def write_outputs(report_payload: dict[str, Any], trace_lines: list[str], report_path: Path, trace_path: Path) -> None:
    ensure_dir(report_path.parent)
    ensure_dir(trace_path.parent)

    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    text_lines = [
        "e2e_smoke_trace_samples",
        f"status={report_payload.get('status', 'FAIL')}",
        f"reason_code={report_payload.get('reason_code', REASON_UNEXPECTED_EXCEPTION)}",
        f"remediation_hint={report_payload.get('remediation_hint', remediation_hint_for(REASON_UNEXPECTED_EXCEPTION))}",
        f"generated_at_utc={report_payload.get('generated_at_utc', '')}",
        f"base_url={report_payload.get('base_url', '')}",
        f"target_tenant_key={report_payload.get('target_tenant_key', '')}",
        f"effective_auth_tenant_key={report_payload.get('effective_auth_tenant_key', '')}",
    ]
    text_lines.extend(trace_lines)

    for scenario in report_payload.get("scenarios", []):
        if isinstance(scenario, dict) and scenario.get("status") == "FAIL":
            text_lines.append(
                "failure="
                + f"{scenario.get('scenario_id')} stage={scenario.get('stage')} "
                + f"error_code={scenario.get('error_code')} message={mask_secrets(str(scenario.get('message', '')))} "
                + f"runbook={scenario.get('runbook')}"
            )

    text_lines.append(f"runbook_on_failure={report_payload.get('runbook_on_failure', RUNBOOK_INDEX)}")
    trace_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")


def build_bootstrap_failure_payload(
    *,
    args: argparse.Namespace,
    stage: str,
    error_code: str,
    message: str,
    runbook: str,
    details: dict[str, Any],
    reason_code: str,
) -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now_iso(),
        "base_url": args.base_url,
        "target_tenant_key": args.tenant_key,
        "auth_tenant_key": args.auth_tenant_key,
        "effective_auth_tenant_key": args.auth_tenant_key,
        "role": args.role,
        "status": STATUS_FAIL,
        "reason_code": reason_code,
        "remediation_hint": remediation_hint_for(reason_code),
        "summary": {
            "scenario_total": 1,
            "scenario_pass": 0,
            "scenario_fail": 1,
        },
        "scenarios": [
            asdict(
                ScenarioResult(
                    scenario_id="BOOTSTRAP",
                    name="bootstrap-login-and-prechecks",
                    status=STATUS_FAIL,
                    stage=stage,
                    trace_id="",
                    error_code=error_code,
                    message=message,
                    runbook=runbook,
                    details=details,
                )
            )
        ],
        "trace_context": {},
        "runbook_on_failure": runbook,
    }


def main() -> int:
    args = parse_args()
    if args.disable_demo_auth_fallback:
        args.allow_demo_auth_fallback = False
    if args.s6_allow_no_error_event:
        args.s6_require_error_event = False
    if args.auth_tenant_key == "":
        args.auth_tenant_key = args.tenant_key

    report_path, trace_path = build_output_paths(args)

    trace_lines: list[str] = []
    reachable, preflight_detail = probe_base_url_reachable(args.base_url, args.preflight_timeout_sec)
    if not reachable:
        report_payload = build_bootstrap_failure_payload(
            args=args,
            stage="preflight_base_url",
            error_code=REASON_TARGET_UNREACHABLE,
            message="base_url was unreachable during preflight",
            runbook=RUNBOOK_INDEX,
            details=preflight_detail,
            reason_code=REASON_TARGET_UNREACHABLE,
        )
    else:
        trace_lines.append(
            "preflight.base_url="
            + f"reachable http_status={preflight_detail.get('http_status')} probe_url={preflight_detail.get('probe_url')}"
        )
        runner = E2ESmokeRunner(args)
        try:
            report_payload = runner.execute()
            trace_lines.extend(runner.trace_lines)
        except ScenarioFailure as exc:
            reason_code = classify_bootstrap_reason_code(exc.stage)
            report_payload = build_bootstrap_failure_payload(
                args=args,
                stage=exc.stage,
                error_code=exc.error_code,
                message=str(exc),
                runbook=exc.runbook,
                details=exc.details,
                reason_code=reason_code,
            )
            trace_lines.extend(runner.trace_lines)
        except Exception as exc:  # pragma: no cover
            report_payload = build_bootstrap_failure_payload(
                args=args,
                stage="unexpected_exception",
                error_code="",
                message=str(exc),
                runbook=RUNBOOK_INDEX,
                details={"traceback": traceback.format_exc(limit=10)},
                reason_code=REASON_UNEXPECTED_EXCEPTION,
            )
            trace_lines.extend(runner.trace_lines)

    write_outputs(report_payload, trace_lines, report_path, trace_path)

    print(f"e2e_smoke_status={report_payload['status']}")
    print(f"e2e_smoke_reason_code={report_payload.get('reason_code', REASON_NONE)}")
    print(f"report_json={report_path.as_posix()}")
    print(f"trace_txt={trace_path.as_posix()}")
    return 0 if report_payload["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
