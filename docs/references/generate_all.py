#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CS AI Chatbot DB 설계 산출물 생성 스크립트

왜 필요한가:
- CSV/ERD/DDL/운영문서가 서로 어긋나면 유지보수 비용이 급증한다.
- 단일 메타데이터에서 산출물을 함께 생성해 일관성을 높인다.
"""

from __future__ import annotations

import csv
import os
import re
import traceback
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple


BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"
CSV_DIR = GENERATED_DIR / "csv_package"
ZIP_PATH = GENERATED_DIR / "CS_AI_CHATBOT_DB_CSV_Package.zip"


@dataclass
class Column:
    name: str
    typ: str
    nullable: bool = True
    key: str = ""
    default: str = ""
    desc: str = ""
    note: str = ""


@dataclass
class ForeignKey:
    cols: Tuple[str, ...]
    ref_schema: str
    ref_table: str
    ref_cols: Tuple[str, ...]


@dataclass
class Table:
    schema: str
    name: str
    desc: str
    cols: List[Column]
    pk: Tuple[str, ...]
    uks: List[Tuple[str, ...]] = field(default_factory=list)
    fks: List[ForeignKey] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    partitioned: bool = False
    comment: str = ""

    @property
    def sql_name(self) -> str:
        return self.name.lower()

    @property
    def fq(self) -> str:
        return f"{self.schema}.{self.sql_name}"


def C(
    name: str,
    typ: str,
    nullable: bool = True,
    key: str = "",
    default: str = "",
    desc: str = "",
    note: str = "",
) -> Column:
    return Column(name, typ, nullable, key, default, desc, note)


def FK(cols: Iterable[str], ref_schema: str, ref_table: str, ref_cols: Iterable[str]) -> ForeignKey:
    return ForeignKey(tuple(cols), ref_schema, ref_table, tuple(ref_cols))


def ensure_dirs() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)


def add_table(
    out: List[Table],
    schema: str,
    name: str,
    desc: str,
    extras: List[Column],
    include_tenant: bool = True,
    partitioned: bool = False,
    uks: List[Tuple[str, ...]] | None = None,
    fks: List[ForeignKey] | None = None,
    indexes: List[str] | None = None,
    comment: str = "",
) -> None:
    cols = [C("id", "uuid", False, "PK", "gen_random_uuid()", "ID")]
    if include_tenant:
        cols.append(C("tenant_id", "uuid", False, "FK", "", "테넌트 ID"))
    cols.extend(extras)
    if partitioned:
        cols.append(C("created_at", "timestamptz", False, "PK", "CURRENT_TIMESTAMP", "생성 시각"))
    else:
        cols.append(C("created_at", "timestamptz", False, "", "CURRENT_TIMESTAMP", "생성 시각"))
    cols.append(C("updated_at", "timestamptz", False, "", "CURRENT_TIMESTAMP", "수정 시각"))

    pk = ("id", "created_at") if partitioned else ("id",)
    out.append(
        Table(
            schema=schema,
            name=name,
            desc=desc,
            cols=cols,
            pk=pk,
            uks=uks or [],
            fks=fks or [],
            indexes=indexes or [],
            partitioned=partitioned,
            comment=comment,
        )
    )


def build_tables() -> List[Table]:
    t: List[Table] = []

    # Tenancy & RBAC
    add_table(
        t,
        "core",
        "TB_TENANT",
        "테넌트 마스터",
        [
            C("tenant_key", "varchar(100)", False, "UK", "", "테넌트 키"),
            C("tenant_name", "varchar(200)", False, "", "", "테넌트명"),
            C("status", "varchar(20)", False, "", "'active'", "상태"),
            C("plan_tier", "varchar(20)", False, "", "'standard'", "요금제"),
        ],
        include_tenant=False,
        uks=[("tenant_key",)],
    )
    add_table(
        t,
        "core",
        "TB_TENANT_DOMAIN",
        "테넌트 도메인",
        [
            C("host", "varchar(255)", False, "UK", "", "도메인"),
            C("locale", "varchar(10)", False, "", "'ko-KR'", "로케일"),
            C("is_default", "boolean", False, "", "false", "기본 도메인"),
        ],
        uks=[("host",)],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_USER",
        "사용자",
        [
            C("login_id", "varchar(120)", False, "UK", "", "로그인 ID"),
            C("display_name", "varchar(120)", False, "", "", "표시 이름"),
            C("status", "varchar(20)", False, "", "'active'", "상태"),
        ],
        uks=[("tenant_id", "login_id")],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_ROLE",
        "역할",
        [C("role_code", "varchar(60)", False, "UK", "", "역할 코드"), C("role_name", "varchar(120)", False, "", "", "역할명")],
        uks=[("tenant_id", "role_code")],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_PERMISSION",
        "권한",
        [C("perm_code", "varchar(120)", False, "UK", "", "권한 코드"), C("perm_name", "varchar(150)", False, "", "", "권한명")],
        include_tenant=False,
        uks=[("perm_code",)],
    )
    add_table(
        t,
        "core",
        "TB_USER_ROLE",
        "사용자-역할 매핑",
        [C("user_id", "uuid", False, "FK", "", "사용자 ID"), C("role_id", "uuid", False, "FK", "", "역할 ID")],
        uks=[("tenant_id", "user_id", "role_id")],
        fks=[
            FK(("tenant_id",), "core", "tb_tenant", ("id",)),
            FK(("user_id",), "core", "tb_user", ("id",)),
            FK(("role_id",), "core", "tb_role", ("id",)),
        ],
    )
    add_table(
        t,
        "core",
        "TB_ROLE_PERMISSION",
        "역할-권한 매핑",
        [C("role_id", "uuid", False, "FK", "", "역할 ID"), C("permission_id", "uuid", False, "FK", "", "권한 ID")],
        uks=[("tenant_id", "role_id", "permission_id")],
        fks=[
            FK(("tenant_id",), "core", "tb_tenant", ("id",)),
            FK(("role_id",), "core", "tb_role", ("id",)),
            FK(("permission_id",), "core", "tb_permission", ("id",)),
        ],
    )
    add_table(
        t,
        "core",
        "TB_AUTH_SESSION",
        "인증 세션",
        [
            C("user_id", "uuid", False, "FK", "", "사용자 ID"),
            C("session_token_hash", "varchar(128)", False, "UK", "", "세션 토큰 해시"),
            C("expires_at", "timestamptz", False, "", "", "만료 시각"),
        ],
        uks=[("session_token_hash",)],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("user_id",), "core", "tb_user", ("id",))],
    )

    # 채널/고객/세션
    add_table(
        t,
        "core",
        "TB_CHANNEL",
        "채널",
        [C("channel_code", "varchar(60)", False, "UK", "", "채널 코드"), C("channel_name", "varchar(120)", False, "", "", "채널명")],
        uks=[("tenant_id", "channel_code")],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_WIDGET_INSTANCE",
        "위젯 인스턴스",
        [
            C("channel_id", "uuid", False, "FK", "", "채널 ID"),
            C("widget_key", "varchar(120)", False, "UK", "", "위젯 키"),
            C("theme_json", "jsonb", True, "", "'{}'::jsonb", "테마"),
        ],
        uks=[("tenant_id", "widget_key")],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("channel_id",), "core", "tb_channel", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_CUSTOMER",
        "고객(PII 최소)",
        [C("channel_id", "uuid", False, "FK", "", "채널 ID"), C("display_name_masked", "varchar(120)", True, "", "", "마스킹 이름")],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("channel_id",), "core", "tb_channel", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_CUSTOMER_IDENTITY",
        "고객 식별자 해시",
        [
            C("customer_id", "uuid", False, "FK", "", "고객 ID"),
            C("identity_type", "varchar(30)", False, "", "", "식별자 타입"),
            C("customer_token_hash", "varchar(128)", False, "UK", "", "토큰 해시"),
        ],
        uks=[("tenant_id", "identity_type", "customer_token_hash")],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("customer_id",), "core", "tb_customer", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_CONVERSATION",
        "대화 세션",
        [
            C("channel_id", "uuid", False, "FK", "", "채널 ID"),
            C("customer_id", "uuid", False, "FK", "", "고객 ID"),
            C("status", "varchar(20)", False, "", "'active'", "상태"),
            C("trace_id", "uuid", True, "", "", "추적 ID"),
        ],
        fks=[
            FK(("tenant_id",), "core", "tb_tenant", ("id",)),
            FK(("channel_id",), "core", "tb_channel", ("id",)),
            FK(("customer_id",), "core", "tb_customer", ("id",)),
        ],
    )

    # 메시징
    add_table(
        t,
        "core",
        "TB_MESSAGE",
        "메시지(월 파티션)",
        [
            C("conversation_id", "uuid", False, "FK", "", "대화 ID"),
            C("role", "varchar(20)", False, "", "", "발화 주체"),
            C("message_text", "text", True, "", "", "메시지 본문"),
            C("trace_id", "uuid", True, "", "", "추적 ID"),
            C("policy_version_id", "uuid", True, "", "", "정책 버전"),
            C("template_version_id", "uuid", True, "", "", "템플릿 버전"),
            C("prompt_version_id", "uuid", True, "", "", "프롬프트 버전"),
            C("index_version_id", "uuid", True, "", "", "인덱스 버전"),
        ],
        partitioned=True,
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("conversation_id",), "core", "tb_conversation", ("id",))],
        comment="권장 인덱스: (tenant_id, conversation_id, created_at), (tenant_id, created_at), BRIN(created_at)",
    )
    add_table(
        t,
        "core",
        "TB_ATTACHMENT",
        "첨부파일",
        [
            C("storage_key", "varchar(255)", False, "UK", "", "스토리지 키"),
            C("file_name", "varchar(255)", False, "", "", "파일명"),
            C("mime_type", "varchar(120)", False, "", "", "MIME"),
            C("size_bytes", "bigint", False, "", "", "크기"),
        ],
        uks=[("tenant_id", "storage_key")],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_MESSAGE_ATTACHMENT",
        "메시지-첨부 연결",
        [
            C("message_id", "uuid", False, "FK", "", "메시지 ID"),
            C("message_created_at", "timestamptz", False, "FK", "", "메시지 생성 시각"),
            C("attachment_id", "uuid", False, "FK", "", "첨부 ID"),
        ],
        uks=[("tenant_id", "message_id", "message_created_at", "attachment_id")],
        fks=[
            FK(("tenant_id",), "core", "tb_tenant", ("id",)),
            FK(("message_id", "message_created_at"), "core", "tb_message", ("id", "created_at")),
            FK(("attachment_id",), "core", "tb_attachment", ("id",)),
        ],
    )
    add_table(
        t,
        "core",
        "TB_MESSAGE_FEEDBACK",
        "메시지 피드백",
        [
            C("message_id", "uuid", False, "FK", "", "메시지 ID"),
            C("message_created_at", "timestamptz", False, "FK", "", "메시지 생성 시각"),
            C("feedback_type", "varchar(30)", False, "", "", "thumb/csat"),
            C("score", "smallint", True, "", "", "점수"),
        ],
        fks=[
            FK(("tenant_id",), "core", "tb_tenant", ("id",)),
            FK(("message_id", "message_created_at"), "core", "tb_message", ("id", "created_at")),
        ],
    )
    add_table(
        t,
        "core",
        "TB_STREAM_EVENT",
        "SSE 이벤트 로그",
        [
            C("message_id", "uuid", False, "FK", "", "메시지 ID"),
            C("message_created_at", "timestamptz", False, "FK", "", "메시지 생성 시각"),
            C("event_type", "varchar(30)", False, "", "", "token/tool/citation/done/error/safe_response"),
            C("event_seq", "integer", False, "", "", "순번"),
            C("payload_json", "jsonb", True, "", "'{}'::jsonb", "payload"),
        ],
        fks=[
            FK(("tenant_id",), "core", "tb_tenant", ("id",)),
            FK(("message_id", "message_created_at"), "core", "tb_message", ("id", "created_at")),
        ],
        uks=[("tenant_id", "message_id", "message_created_at", "event_seq")],
    )

    # Tool
    add_table(
        t,
        "core",
        "TB_TOOL_DEFINITION",
        "툴 정의",
        [
            C("tool_name", "varchar(120)", False, "UK", "", "툴명"),
            C("tool_version", "varchar(40)", False, "UK", "'v1'", "버전"),
            C("schema_json", "jsonb", False, "", "'{}'::jsonb", "입력 스키마"),
            C("timeout_ms", "integer", False, "", "8000", "타임아웃"),
        ],
        uks=[("tenant_id", "tool_name", "tool_version")],
        fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))],
    )
    add_table(
        t,
        "core",
        "TB_TOOL_CALL_LOG",
        "툴 호출 로그(월 파티션)",
        [
            C("conversation_id", "uuid", False, "", "", "대화 ID"),
            C("tool_name", "varchar(120)", False, "", "", "툴명"),
            C("http_status", "integer", True, "", "", "HTTP 상태"),
            C("latency_ms", "integer", True, "", "", "지연(ms)"),
            C("trace_id", "uuid", True, "", "", "추적 ID"),
        ],
        partitioned=True,
        comment="권장 인덱스: (tenant_id, conversation_id, created_at), BRIN(created_at)",
    )

    # KB/인덱싱
    add_table(t, "core", "TB_KB", "지식베이스", [C("kb_key", "varchar(100)", False, "UK", "", "KB 키"), C("kb_name", "varchar(200)", False, "", "", "KB명")], uks=[("tenant_id", "kb_key")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])
    add_table(t, "core", "TB_KB_SOURCE", "지식 원천", [C("kb_id", "uuid", False, "FK", "", "KB ID"), C("source_type", "varchar(30)", False, "", "", "원천 유형"), C("source_uri", "text", False, "", "", "원천 URI")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("kb_id",), "core", "tb_kb", ("id",))])
    add_table(t, "core", "TB_KB_DOCUMENT", "KB 문서", [C("kb_id", "uuid", False, "FK", "", "KB ID"), C("source_id", "uuid", True, "FK", "", "원천 ID"), C("title", "varchar(255)", False, "", "", "문서 제목"), C("status", "varchar(20)", False, "", "'ingested'", "상태")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("kb_id",), "core", "tb_kb", ("id",)), FK(("source_id",), "core", "tb_kb_source", ("id",))])
    add_table(t, "core", "TB_KB_DOCUMENT_VERSION", "문서 버전", [C("document_id", "uuid", False, "FK", "", "문서 ID"), C("version_no", "integer", False, "UK", "", "버전 번호"), C("status", "varchar(20)", False, "", "'draft'", "상태")], uks=[("document_id", "version_no")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("document_id",), "core", "tb_kb_document", ("id",))])
    add_table(t, "core", "TB_KB_CHUNK", "문서 청크", [C("kb_id", "uuid", False, "FK", "", "KB ID"), C("document_version_id", "uuid", False, "FK", "", "문서 버전"), C("chunk_no", "integer", False, "UK", "", "청크 순번"), C("chunk_text", "text", False, "", "", "청크 텍스트"), C("opensearch_doc_id", "varchar(120)", True, "", "", "OpenSearch 문서 ID")], uks=[("document_version_id", "chunk_no")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("kb_id",), "core", "tb_kb", ("id",)), FK(("document_version_id",), "core", "tb_kb_document_version", ("id",))])
    add_table(t, "core", "TB_KB_INGEST_JOB", "인제스트 작업", [C("kb_id", "uuid", False, "FK", "", "KB ID"), C("status", "varchar(20)", False, "", "'queued'", "상태"), C("total_docs", "integer", False, "", "0", "전체 문서 수"), C("processed_docs", "integer", False, "", "0", "처리 수"), C("failed_docs", "integer", False, "", "0", "실패 수")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("kb_id",), "core", "tb_kb", ("id",))])
    add_table(t, "core", "TB_KB_INDEX_VERSION", "인덱스 버전", [C("kb_id", "uuid", False, "FK", "", "KB ID"), C("index_version", "integer", False, "UK", "", "인덱스 버전"), C("status", "varchar(20)", False, "", "'building'", "상태"), C("opensearch_index_name", "varchar(200)", True, "", "", "OpenSearch 인덱스명")], uks=[("kb_id", "index_version")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("kb_id",), "core", "tb_kb", ("id",))])

    # vec
    add_table(t, "vec", "TB_KB_CHUNK_EMBEDDING", "청크 임베딩", [C("kb_chunk_id", "uuid", False, "FK", "", "청크 ID"), C("index_version_id", "uuid", False, "FK", "", "인덱스 버전"), C("embedding", "vector(1536)", False, "", "", "임베딩"), C("embedding_dim", "integer", False, "", "1536", "차원"), C("model_name", "varchar(120)", False, "", "", "모델명")], uks=[("kb_chunk_id", "index_version_id")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("kb_chunk_id",), "core", "tb_kb_chunk", ("id",)), FK(("index_version_id",), "core", "tb_kb_index_version", ("id",))], indexes=["CREATE INDEX IF NOT EXISTS ivf_tb_kb_chunk_embedding__embedding ON vec.tb_kb_chunk_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"])
    add_table(t, "vec", "TB_ANSWER_BANK", "승인 답변 저장소", [C("question_fingerprint", "varchar(128)", False, "UK", "", "질문 지문"), C("answer_json", "jsonb", False, "", "", "답변 JSON"), C("citation_json", "jsonb", False, "", "", "인용 JSON"), C("policy_version_id", "uuid", True, "", "", "정책 버전"), C("index_version_id", "uuid", True, "", "", "인덱스 버전")], uks=[("tenant_id", "question_fingerprint", "policy_version_id", "index_version_id")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])
    add_table(t, "vec", "TB_SEMANTIC_CACHE", "시맨틱 캐시", [C("cache_key", "varchar(128)", False, "UK", "", "캐시 키"), C("query_embedding", "vector(1536)", True, "", "", "질의 벡터"), C("answer_json", "jsonb", False, "", "", "답변 JSON"), C("session_summary", "text", True, "", "", "PII 제외 요약"), C("expires_at", "timestamptz", False, "", "", "만료 시각")], uks=[("tenant_id", "cache_key")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))], indexes=["CREATE INDEX IF NOT EXISTS hnsw_tb_semantic_cache__query_embedding ON vec.tb_semantic_cache USING hnsw (query_embedding vector_cosine_ops);"])

    # RAG/생성
    add_table(t, "core", "TB_RAG_SEARCH_LOG", "RAG 검색 로그(월 파티션)", [C("conversation_id", "uuid", False, "", "", "대화 ID"), C("query_text_masked", "text", False, "", "", "마스킹 질의"), C("top_k", "integer", False, "", "5", "TopK"), C("trace_id", "uuid", True, "", "", "추적 ID")], partitioned=True, comment="권장 인덱스: (tenant_id, conversation_id, created_at), BRIN(created_at)")
    add_table(t, "core", "TB_RAG_CITATION", "RAG 인용", [C("message_id", "uuid", False, "FK", "", "메시지 ID"), C("message_created_at", "timestamptz", False, "FK", "", "메시지 생성"), C("chunk_id", "uuid", True, "FK", "", "청크 ID"), C("rank_no", "integer", False, "", "", "순번"), C("excerpt_masked", "text", False, "", "", "인용문")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("message_id", "message_created_at"), "core", "tb_message", ("id", "created_at")), FK(("chunk_id",), "core", "tb_kb_chunk", ("id",))])
    add_table(t, "core", "TB_GENERATION_LOG", "생성 로그", [C("message_id", "uuid", False, "FK", "", "메시지 ID"), C("message_created_at", "timestamptz", False, "FK", "", "메시지 생성"), C("provider_id", "uuid", True, "", "", "Provider ID"), C("model_id", "uuid", True, "", "", "Model ID"), C("input_tokens", "integer", True, "", "", "입력 토큰"), C("output_tokens", "integer", True, "", "", "출력 토큰"), C("trace_id", "uuid", True, "", "", "추적 ID")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("message_id", "message_created_at"), "core", "tb_message", ("id", "created_at"))])
    add_table(t, "core", "TB_GUARDRAIL_EVENT", "가드레일 이벤트", [C("conversation_id", "uuid", True, "", "", "대화 ID"), C("message_id", "uuid", True, "", "", "메시지 ID"), C("message_created_at", "timestamptz", True, "", "", "메시지 생성"), C("rule_code", "varchar(80)", False, "", "", "룰 코드"), C("action", "varchar(40)", False, "", "", "조치"), C("trace_id", "uuid", True, "", "", "추적 ID")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])

    # 템플릿/정책/프롬프트
    add_table(t, "core", "TB_TEMPLATE", "템플릿", [C("template_key", "varchar(100)", False, "UK", "", "템플릿 키"), C("category", "varchar(60)", False, "", "", "카테고리"), C("status", "varchar(20)", False, "", "'active'", "상태")], uks=[("tenant_id", "template_key")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])
    add_table(t, "core", "TB_TEMPLATE_VERSION", "템플릿 버전", [C("template_id", "uuid", False, "FK", "", "템플릿 ID"), C("version_no", "integer", False, "UK", "", "버전"), C("body_text", "text", False, "", "", "본문"), C("approval_status", "varchar(20)", False, "", "'draft'", "승인 상태")], uks=[("template_id", "version_no")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("template_id",), "core", "tb_template", ("id",))])
    add_table(t, "core", "TB_TEMPLATE_PLACEHOLDER", "템플릿 변수", [C("template_version_id", "uuid", False, "FK", "", "템플릿 버전 ID"), C("placeholder_key", "varchar(80)", False, "UK", "", "변수 키"), C("data_type", "varchar(30)", False, "", "'string'", "데이터 타입"), C("required", "boolean", False, "", "false", "필수")], uks=[("template_version_id", "placeholder_key")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("template_version_id",), "core", "tb_template_version", ("id",))])
    add_table(t, "core", "TB_POLICY", "정책", [C("policy_key", "varchar(100)", False, "UK", "", "정책 키"), C("category", "varchar(60)", False, "", "", "카테고리"), C("status", "varchar(20)", False, "", "'active'", "상태")], uks=[("tenant_id", "policy_key")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])
    add_table(t, "core", "TB_POLICY_VERSION", "정책 버전", [C("policy_id", "uuid", False, "FK", "", "정책 ID"), C("version_no", "integer", False, "UK", "", "버전"), C("rule_json", "jsonb", False, "", "'{}'::jsonb", "룰"), C("answer_contract_json", "jsonb", True, "", "'{}'::jsonb", "Answer Contract"), C("approval_status", "varchar(20)", False, "", "'draft'", "승인 상태")], uks=[("policy_id", "version_no")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("policy_id",), "core", "tb_policy", ("id",))])
    add_table(t, "core", "TB_PROMPT", "프롬프트", [C("prompt_key", "varchar(100)", False, "UK", "", "프롬프트 키"), C("prompt_type", "varchar(30)", False, "", "", "프롬프트 타입"), C("status", "varchar(20)", False, "", "'active'", "상태")], uks=[("tenant_id", "prompt_key")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])
    add_table(t, "core", "TB_PROMPT_VERSION", "프롬프트 버전", [C("prompt_id", "uuid", False, "FK", "", "프롬프트 ID"), C("version_no", "integer", False, "UK", "", "버전"), C("system_prompt_text", "text", False, "", "", "시스템 프롬프트"), C("schema_json", "jsonb", True, "", "'{}'::jsonb", "스키마"), C("approval_status", "varchar(20)", False, "", "'draft'", "승인 상태")], uks=[("prompt_id", "version_no")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("prompt_id",), "core", "tb_prompt", ("id",))])
    add_table(t, "core", "TB_TEMPLATE_POLICY_MAP", "템플릿-정책 매핑", [C("category", "varchar(60)", False, "", "", "카테고리"), C("template_id", "uuid", False, "FK", "", "템플릿 ID"), C("template_version_id", "uuid", True, "FK", "", "템플릿 버전"), C("policy_id", "uuid", False, "FK", "", "정책 ID"), C("policy_version_id", "uuid", True, "FK", "", "정책 버전"), C("effective_from", "timestamptz", False, "", "CURRENT_TIMESTAMP", "적용 시작"), C("effective_to", "timestamptz", True, "", "", "적용 종료")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("template_id",), "core", "tb_template", ("id",)), FK(("template_version_id",), "core", "tb_template_version", ("id",)), FK(("policy_id",), "core", "tb_policy", ("id",)), FK(("policy_version_id",), "core", "tb_policy_version", ("id",))])

    # LLM
    add_table(t, "core", "TB_LLM_PROVIDER", "LLM Provider", [C("provider_code", "varchar(60)", False, "UK", "", "Provider 코드"), C("provider_name", "varchar(120)", False, "", "", "Provider명"), C("endpoint_url", "text", True, "", "", "엔드포인트")], uks=[("tenant_id", "provider_code")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])
    add_table(t, "core", "TB_LLM_MODEL", "LLM 모델", [C("provider_id", "uuid", False, "FK", "", "Provider ID"), C("model_code", "varchar(100)", False, "UK", "", "모델 코드"), C("context_window", "integer", True, "", "", "컨텍스트 윈도우"), C("max_output_tokens", "integer", True, "", "", "최대 출력 토큰")], uks=[("provider_id", "model_code")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("provider_id",), "core", "tb_llm_provider", ("id",))])
    add_table(t, "core", "TB_PROVIDER_KEY", "Provider 키", [C("provider_id", "uuid", False, "FK", "", "Provider ID"), C("key_name", "varchar(120)", False, "UK", "", "키 이름"), C("secret_ref", "varchar(255)", False, "", "", "KMS/Vault 참조"), C("rotation_cycle_days", "integer", False, "", "90", "회전 주기")], uks=[("provider_id", "key_name")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("provider_id",), "core", "tb_llm_provider", ("id",))])
    add_table(t, "core", "TB_LLM_ROUTE", "모델 라우팅", [C("route_name", "varchar(120)", False, "UK", "", "라우트명"), C("provider_id", "uuid", False, "FK", "", "Provider ID"), C("model_id", "uuid", False, "FK", "", "Model ID"), C("timeout_ms", "integer", False, "", "15000", "타임아웃"), C("fallback_route_id", "uuid", True, "", "", "폴백 라우트"), C("enabled", "boolean", False, "", "true", "활성")], uks=[("tenant_id", "route_name")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",)), FK(("provider_id",), "core", "tb_llm_provider", ("id",)), FK(("model_id",), "core", "tb_llm_model", ("id",))])

    # 운영/감사
    add_table(t, "ops", "TB_AUDIT_LOG", "감사 로그(월 파티션)", [C("actor_user_id", "uuid", True, "", "", "행위자"), C("action_type", "varchar(80)", False, "", "", "행위"), C("target_type", "varchar(80)", True, "", "", "대상 유형"), C("target_id", "varchar(120)", True, "", "", "대상 ID"), C("trace_id", "uuid", True, "", "", "추적 ID")], partitioned=True, comment="권장 인덱스: (tenant_id, created_at), (tenant_id, actor_user_id, created_at), BRIN(created_at)")
    add_table(t, "ops", "TB_OPS_EVENT", "운영 이벤트(월 파티션)", [C("event_type", "varchar(80)", False, "", "", "이벤트 유형"), C("severity", "varchar(20)", False, "", "", "심각도"), C("component", "varchar(80)", False, "", "", "컴포넌트"), C("message", "text", False, "", "", "메시지"), C("trace_id", "uuid", True, "", "", "추적 ID")], partitioned=True, comment="권장 인덱스: (tenant_id, created_at), (tenant_id, severity, created_at), BRIN(created_at)")
    add_table(t, "ops", "TB_ERROR_CATALOG", "에러 카탈로그", [C("error_code", "varchar(80)", False, "UK", "", "에러 코드"), C("http_status", "integer", False, "", "", "HTTP 상태"), C("user_message_ko", "varchar(255)", False, "", "", "한글 메시지"), C("retryable", "boolean", False, "", "false", "재시도 가능")], include_tenant=False, uks=[("error_code",)])
    add_table(t, "ops", "TB_NOTIFICATION_RULE", "알림 룰", [C("rule_name", "varchar(120)", False, "", "", "룰 이름"), C("event_type", "varchar(80)", False, "", "", "이벤트 유형"), C("severity_threshold", "varchar(20)", False, "", "'warning'", "임계 심각도"), C("channel_type", "varchar(30)", False, "", "", "알림 채널"), C("enabled", "boolean", False, "", "true", "활성")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])
    add_table(t, "ops", "TB_WEBHOOK_ENDPOINT", "웹훅 엔드포인트", [C("integration_type", "varchar(60)", False, "", "", "연동 유형"), C("endpoint_url", "text", False, "", "", "URL"), C("secret_ref", "varchar(255)", False, "", "", "비밀키 참조"), C("status", "varchar(20)", False, "", "'active'", "상태")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])
    add_table(t, "ops", "TB_INTEGRATION_LOG", "연동 로그(월 파티션)", [C("integration_type", "varchar(60)", False, "", "", "연동 유형"), C("endpoint_id", "uuid", True, "", "", "엔드포인트 ID"), C("http_status", "integer", True, "", "", "HTTP 상태"), C("latency_ms", "integer", True, "", "", "지연(ms)"), C("trace_id", "uuid", True, "", "", "추적 ID")], partitioned=True, comment="권장 인덱스: (tenant_id, integration_type, created_at), BRIN(created_at)")
    add_table(t, "ops", "TB_EXPORT_JOB", "내보내기 작업", [C("job_type", "varchar(40)", False, "", "", "작업 유형"), C("status", "varchar(20)", False, "", "'queued'", "상태"), C("output_uri", "varchar(255)", True, "", "", "결과 URI"), C("row_count", "bigint", True, "", "", "행 수")], fks=[FK(("tenant_id",), "core", "tb_tenant", ("id",))])

    return t


def create_csv_package(tables: List[Table]) -> List[Path]:
    files: List[Path] = []
    for tb in tables:
        rows = [
            [f"{tb.name} - {tb.desc}", "", "", "", "", "", ""],
            ["", "", "", "", "", "", ""],
            ["컬럼명", "데이터타입", "NULLABLE", "KEY", "기본값", "설명", "비고"],
        ]
        for col in tb.cols:
            rows.append([col.name, col.typ, "" if col.nullable else "NOT NULL", col.key, col.default, col.desc, col.note])
        p = CSV_DIR / f"{tb.name}.csv"
        with p.open("w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)
        files.append(p)

    guide = CSV_DIR / "README_구글스프레드시트_업로드_가이드.txt"
    write_text(
        guide,
        """Google 스프레드시트 업로드 가이드
1) docs/references/generated/CS_AI_CHATBOT_DB_CSV_Package.zip 압축 해제
2) Drive에 CSV 업로드
3) Google Sheets > 파일 > 가져오기 > 업로드
4) 가져오기 옵션: "새 시트 삽입" 권장
5) 본 패키지는 UTF-8-SIG(BOM)으로 저장되어 한글 깨짐을 방지합니다.
""",
    )
    files.append(guide)
    return files


def create_zip() -> Path:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(CSV_DIR.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(CSV_DIR.parent))
    return ZIP_PATH


def ddl_table(tb: Table) -> str:
    lines = [f"-- {tb.name}: {tb.desc}", f"CREATE TABLE IF NOT EXISTS {tb.fq} ("]
    defs: List[str] = []
    for col in tb.cols:
        row = f"    {col.name} {col.typ}"
        if not col.nullable:
            row += " NOT NULL"
        if col.default:
            row += f" DEFAULT {col.default}"
        defs.append(row)
    defs.append(f"    PRIMARY KEY ({', '.join(tb.pk)})")
    for uk in tb.uks:
        defs.append(f"    UNIQUE ({', '.join(uk)})")
    for f in tb.fks:
        defs.append(f"    FOREIGN KEY ({', '.join(f.cols)}) REFERENCES {f.ref_schema}.{f.ref_table} ({', '.join(f.ref_cols)})")
    lines.append(",\n".join(defs))
    lines.append(") PARTITION BY RANGE (created_at);" if tb.partitioned else ");")
    if tb.comment:
        escaped = tb.comment.replace("'", "''")
        lines.append(f"COMMENT ON TABLE {tb.fq} IS '{escaped}';")
    for idx in tb.indexes:
        lines.append(idx)
    lines.append("")
    return "\n".join(lines)


PARTITION_SQL = """
-- 파티션 인덱스 방식: Partition-per-index
-- 이유: 파티션 생성 시 child 인덱스를 즉시 생성해 누락 위험을 최소화한다.
CREATE OR REPLACE FUNCTION ops.ensure_partition_indexes(p_parent text, p_schema text, p_part text, p_suffix text)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_fq text := format('%I.%I', p_schema, p_part);
BEGIN
  IF p_parent = 'core.tb_message' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, conversation_id, created_at DESC)', format('ix_tb_message__tenant_conversation_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, created_at DESC)', format('ix_tb_message__tenant_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_message__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'core.tb_tool_call_log' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, conversation_id, created_at DESC)', format('ix_tb_tool_call_log__tenant_conversation_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_tool_call_log__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'core.tb_rag_search_log' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, conversation_id, created_at DESC)', format('ix_tb_rag_search_log__tenant_conversation_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_rag_search_log__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'ops.tb_audit_log' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, created_at DESC)', format('ix_tb_audit_log__tenant_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, actor_user_id, created_at DESC)', format('ix_tb_audit_log__tenant_actor_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_audit_log__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'ops.tb_ops_event' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, created_at DESC)', format('ix_tb_ops_event__tenant_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, severity, created_at DESC)', format('ix_tb_ops_event__tenant_severity_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_ops_event__created_at_%s', p_suffix), v_fq);
  ELSIF p_parent = 'ops.tb_integration_log' THEN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s (tenant_id, integration_type, created_at DESC)', format('ix_tb_integration_log__tenant_type_created_%s', p_suffix), v_fq);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s USING brin (created_at)', format('brin_tb_integration_log__created_at_%s', p_suffix), v_fq);
  END IF;
END $$;

CREATE OR REPLACE FUNCTION ops.create_month_partition(p_parent text, p_month date)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE s text := split_part(p_parent, '.', 1);
DECLARE r text := split_part(p_parent, '.', 2);
DECLARE ms date := date_trunc('month', p_month)::date;
DECLARE me date := (ms + interval '1 month')::date;
DECLARE y text := to_char(ms, 'YYYYMM');
DECLARE p text := format('%s_%s', r, y);
BEGIN
  EXECUTE format('CREATE TABLE IF NOT EXISTS %I.%I PARTITION OF %s FOR VALUES FROM (%L) TO (%L)', s, p, p_parent, ms, me);
  PERFORM ops.ensure_partition_indexes(p_parent, s, p, y);
  RETURN format('%I.%I', s, p);
END $$;

CREATE OR REPLACE FUNCTION ops.ensure_future_partitions(months_ahead integer DEFAULT 2)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE i integer; m date;
BEGIN
  IF months_ahead < 0 THEN RAISE EXCEPTION 'months_ahead must be >= 0'; END IF;
  FOR i IN 0..months_ahead LOOP
    m := date_trunc('month', now())::date + make_interval(months => i);
    PERFORM ops.create_month_partition('core.tb_message', m);
    PERFORM ops.create_month_partition('core.tb_tool_call_log', m);
    PERFORM ops.create_month_partition('core.tb_rag_search_log', m);
    PERFORM ops.create_month_partition('ops.tb_audit_log', m);
    PERFORM ops.create_month_partition('ops.tb_ops_event', m);
    PERFORM ops.create_month_partition('ops.tb_integration_log', m);
  END LOOP;
END $$;
"""


GAP_VIEW_SQL = """
CREATE OR REPLACE VIEW ops.v_partition_index_gaps AS
WITH pm AS (
  SELECT 'core.tb_message'::text p UNION ALL SELECT 'core.tb_tool_call_log'
  UNION ALL SELECT 'core.tb_rag_search_log' UNION ALL SELECT 'ops.tb_audit_log'
  UNION ALL SELECT 'ops.tb_ops_event' UNION ALL SELECT 'ops.tb_integration_log'
),
pt AS (
  SELECT pm.p parent_table, n.nspname sch, c.relname rel, regexp_replace(c.relname, '^.*_(\\d{6})$', '\\1') y
  FROM pg_inherits i
  JOIN pg_class c ON c.oid=i.inhrelid
  JOIN pg_namespace n ON n.oid=c.relnamespace
  JOIN pg_class p ON p.oid=i.inhparent
  JOIN pg_namespace pn ON pn.oid=p.relnamespace
  JOIN pm ON pm.p = pn.nspname || '.' || p.relname
),
exp AS (
  SELECT parent_table, sch, rel,
    CASE parent_table
      WHEN 'core.tb_message' THEN ARRAY[format('ix_tb_message__tenant_conversation_created_%s', y), format('ix_tb_message__tenant_created_%s', y), format('brin_tb_message__created_at_%s', y)]
      WHEN 'core.tb_tool_call_log' THEN ARRAY[format('ix_tb_tool_call_log__tenant_conversation_created_%s', y), format('brin_tb_tool_call_log__created_at_%s', y)]
      WHEN 'core.tb_rag_search_log' THEN ARRAY[format('ix_tb_rag_search_log__tenant_conversation_created_%s', y), format('brin_tb_rag_search_log__created_at_%s', y)]
      WHEN 'ops.tb_audit_log' THEN ARRAY[format('ix_tb_audit_log__tenant_created_%s', y), format('ix_tb_audit_log__tenant_actor_created_%s', y), format('brin_tb_audit_log__created_at_%s', y)]
      WHEN 'ops.tb_ops_event' THEN ARRAY[format('ix_tb_ops_event__tenant_created_%s', y), format('ix_tb_ops_event__tenant_severity_created_%s', y), format('brin_tb_ops_event__created_at_%s', y)]
      WHEN 'ops.tb_integration_log' THEN ARRAY[format('ix_tb_integration_log__tenant_type_created_%s', y), format('brin_tb_integration_log__created_at_%s', y)]
      ELSE ARRAY[]::text[] END expected
  FROM pt
),
act AS (
  SELECT schemaname, tablename, array_agg(indexname) idx FROM pg_indexes GROUP BY schemaname, tablename
)
SELECT e.parent_table, e.sch || '.' || e.rel AS partition_table,
       ARRAY(SELECT unnest(e.expected) EXCEPT SELECT unnest(COALESCE(a.idx, ARRAY[]::text[]))) AS missing_index_names,
       now() AS checked_at
FROM exp e LEFT JOIN act a ON a.schemaname=e.sch AND a.tablename=e.rel;

-- 운영 runbook
-- (a) SELECT ops.ensure_future_partitions(3);
-- (b) SELECT * FROM ops.v_partition_index_gaps WHERE cardinality(missing_index_names) > 0;
-- (c) SELECT ops.ensure_partition_indexes('core.tb_message', 'core', 'tb_message_202601', '202601');
-- 주의: 대형 인덱스는 CREATE INDEX CONCURRENTLY 분리 실행(Flyway/Liquibase 트랜잭션 분리 필요)
"""


def create_ddl(tables: List[Table]) -> Path:
    ddl: List[str] = []
    ddl.append(
        f"""-- CS AI Chatbot PostgreSQL DDL (PostgreSQL 15+)
-- generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS vec;
CREATE SCHEMA IF NOT EXISTS ops;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
DO $$ BEGIN CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION WHEN undefined_file THEN RAISE NOTICE 'pgvector not installed'; END $$;
SET search_path = core, vec, ops, public;
"""
    )
    for tb in tables:
        ddl.append(ddl_table(tb))
    ddl.append(PARTITION_SQL)
    ddl.append(GAP_VIEW_SQL)
    ddl.append("SELECT ops.ensure_future_partitions(2);")
    p = GENERATED_DIR / "postgresql_ddl.sql"
    write_text(p, "\n".join(ddl))
    return p


def sql_to_mermaid_type(typ: str) -> str:
    t = typ.lower()
    if "uuid" in t:
        return "UUID"
    if "timestamp" in t:
        return "TIMESTAMP"
    if "json" in t:
        return "JSONB"
    if "vector" in t:
        return "VECTOR"
    if "int" in t:
        return "INT"
    if "bool" in t:
        return "BOOLEAN"
    if "text" in t:
        return "TEXT"
    return "VARCHAR"


def create_erd_mmd(tables: List[Table]) -> Path:
    lines = ["erDiagram"]
    for tb in tables:
        lines.append(f"    {tb.name} {{")
        for c in tb.cols:
            mark = " PK" if c.name in tb.pk else (" FK" if c.key.startswith("FK") else "")
            lines.append(f"        {sql_to_mermaid_type(c.typ)} {c.name}{mark}")
        lines.append("    }")
    for tb in tables:
        for f in tb.fks:
            lines.append(f"    {f.ref_table.upper()} ||--o{{ {tb.name} : references")
    p = GENERATED_DIR / "ERD.mmd"
    write_text(p, "\n".join(lines) + "\n")
    return p


def create_erd_dbml(tables: List[Table]) -> Path:
    lines = ["// CS AI Chatbot DBML"]
    for tb in tables:
        lines.append(f"Table {tb.schema}.{tb.name} {{")
        for c in tb.cols:
            opts = []
            if len(tb.pk) == 1 and c.name in tb.pk:
                opts.append("pk")
            if not c.nullable:
                opts.append("not null")
            if c.default:
                opts.append(f"default: `{c.default}`")
            suffix = f" [{', '.join(opts)}]" if opts else ""
            lines.append(f"  {c.name} {c.typ}{suffix}")
        if len(tb.pk) > 1 or tb.uks:
            lines.append("")
            lines.append("  Indexes {")
            if len(tb.pk) > 1:
                lines.append(f"    ({', '.join(tb.pk)}) [pk]")
            for uk in tb.uks:
                lines.append(f"    ({', '.join(uk)}) [unique]")
            lines.append("  }")
        lines.append("}\n")
    for tb in tables:
        for f in tb.fks:
            lines.append(
                f"Ref: {f.ref_schema}.{f.ref_table}.({', '.join(f.ref_cols)}) < {tb.schema}.{tb.name}.({', '.join(f.cols)})"
            )
    p = GENERATED_DIR / "ERD.dbml"
    write_text(p, "\n".join(lines) + "\n")
    return p


def create_docs() -> List[Path]:
    docs = {
        "VECTOR_TUNING.md": """# VECTOR_TUNING
- HNSW vs IVFFlat 선택:
  - HNSW: 재현율/저지연 우선, 메모리 사용량 큼
  - IVFFlat: 대용량/비용 효율 우선, probes 튜닝 필수
- HNSW 파라미터:
  - M, ef_construction, ef_search를 Recall@K + p95 latency로 동시 검증
- IVFFlat 튜닝:
  - lists/probes를 데이터 규모별 조정, 도메인 변화 시 재학습/리빌드
- 운영:
  - 벡터 테이블 ANALYZE 주기 유지
  - 대량 변경 후 REINDEX 검토
  - index_version_id 기반 blue/green 재색인
- 필터링 결합:
  - tenant_id/kb_id/language 사전 필터 우선
  - 과도한 필터로 recall 하락 가능성 점검
""",
        "MULTITENANCY_SAAS.md": """# MULTITENANCY_SAAS
- 모델 비교:
  - Shared DB + tenant_id(+RLS)
  - DB per tenant
  - Schema per tenant
- 권장안:
  - Shared + 선택적 RLS + 대형 테넌트 셀 분리
- 분리 수준:
  - 논리 분리(tenant_id), 물리 분리(셀), 키 분리(KMS alias)
- 온보딩/오프보딩:
  - tenant 생성 -> seed 주입 -> 도메인/키 설정
  - 오프보딩은 export -> freeze -> 보존기간 후 파기
- 테넌트 쿼터/비용:
  - 토큰/툴콜/검색 예산 + 세션 누적 예산
- noisy neighbor 방지:
  - rate-limit, queue 분리, read replica, vec 워크로드 분리
""",
        "OPENSEARCH_HYBRID.md": """# OPENSEARCH_HYBRID
- 매핑:
  - keyword/BM25 필드 + vector 필드 동시 운영
- 검색 플로우:
  - keyword topK + vector topK -> RRF 병합
- 필터/부스팅:
  - tenant_id/kb_id 필수 필터
  - freshness boosting, 정책/필수문구 가중치
- 운영:
  - reindex -> alias swap -> blue/green -> 롤백
- 버전 연동:
  - TB_KB_INDEX_VERSION.opensearch_index_name으로 동기화 관리
""",
        "MIGRATION_DEV_STG_PROD.md": """# MIGRATION_DEV_STG_PROD
- Flyway/Liquibase 권장:
  - SQL 중심이면 Flyway, 복잡 롤백/다중 DB면 Liquibase
- 파티션/인덱스:
  - 부모 테이블 배포 후 ensure_future_partitions()로 선생성
- CONCURRENTLY 분리:
  - CREATE INDEX CONCURRENTLY는 트랜잭션 분리(post-deploy)로 실행
  - Flyway/Liquibase 기본 트랜잭션과 분리 필요
- 시드 데이터:
  - 권한/에러코드/기본 정책 버전 관리
- 롤백:
  - expand/contract 패턴
  - 스키마 호환성 + 성능 게이트 + index gap 점검
""",
        "COST_OPTIMIZATION.md": """# COST_OPTIMIZATION
- 보관 정책:
  - 핫/웜/콜드 티어링, 콜드는 객체 스토리지 오프로딩
- 삭제 비용 최적화:
  - 로그는 파티션 DROP 기반 보존정책
- 읽기 복제본/풀링:
  - 리포팅 분리, 커넥션 풀로 burst 완화
- vector 분리 기준:
  - ANN 쿼리 SLA 저하 시 vec 전용 인스턴스 분리
- 캐시 계층:
  - semantic cache(Redis/Postgres 기준 분리)
  - 응답/프롬프트/검색결과 캐시 분리
""",
        "SECURITY_AUDIT_DBA.md": """# SECURITY_AUDIT_DBA
- 암호화:
  - at-rest(KMS), in-transit(TLS)
- 시크릿 저장:
  - secret_ref만 저장, 평문 금지
- 권한 분리:
  - 운영/개발/감사 역할 최소권한
- RLS 주의:
  - 성능/인덱스/정책 테스트 동반
- 변경 감사:
  - 정책/템플릿/프롬프트/키/권한 변경 이벤트 기록
- trace_id 상관관계:
  - 메시지-툴-검색-생성 로그 연결
- 운영 점검:
  - 파티션 생성 누락
  - ops.v_partition_index_gaps 인덱스 누락
  - vacuum/analyze 상태
""",
    }
    paths: List[Path] = []
    for filename, content in docs.items():
        p = GENERATED_DIR / filename
        write_text(p, content)
        paths.append(p)
    return paths


def sheet_title(raw: str, used: set[str]) -> str:
    t = re.sub(r"[\[\]\*\?/\\:]", "_", raw).strip()[:95] or "Sheet"
    x = t
    n = 2
    while x in used:
        s = f"_{n}"
        x = f"{t[:95-len(s)]}{s}"
        n += 1
    used.add(x)
    return x


def try_google_upload(csv_files: List[Path]) -> str:
    cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred and not Path(cred).exists():
        cred = ""
    if not cred:
        alt = Path("credentials/service_account.json")
        if alt.exists():
            cred = str(alt.resolve())
    if not cred:
        return "실패: 자격증명이 없어 자동 업로드를 건너뜁니다. CSV ZIP을 수동 업로드하세요."
    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
        creds = service_account.Credentials.from_service_account_file(
            cred,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
        )
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        created = sheets.spreadsheets().create(body={"properties": {"title": f"CS_AI_CHATBOT_DB_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}}).execute()
        sid = created["spreadsheetId"]
        used: set[str] = set()
        reqs = [{"updateSheetProperties": {"properties": {"sheetId": 0, "title": sheet_title(csv_files[0].stem, used)}, "fields": "title"}}]
        titles = [next(iter(used))]
        for f in csv_files[1:]:
            title = sheet_title(f.stem, used)
            reqs.append({"addSheet": {"properties": {"title": title}}})
            titles.append(title)
        sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": reqs}).execute()
        for file, title in zip(csv_files, titles):
            with file.open("r", encoding="utf-8-sig", newline="") as fh:
                values = list(csv.reader(fh))
            sheets.spreadsheets().values().update(spreadsheetId=sid, range=f"'{title}'!A1", valueInputOption="RAW", body={"values": values}).execute()
        return f"성공: https://docs.google.com/spreadsheets/d/{sid}"
    except Exception as e:  # pylint: disable=broad-except
        return f"실패: Google Sheets 업로드 오류: {e}\n{traceback.format_exc()}"


def create_google_result(csv_files: List[Path]) -> Path:
    p = GENERATED_DIR / "google_sheets_result.txt"
    write_text(p, try_google_upload(csv_files) + "\n")
    return p


def main() -> None:
    ensure_dirs()
    tables = build_tables()
    generated: List[Path] = []
    csv_files = create_csv_package(tables)
    generated.extend(csv_files)
    generated.append(create_zip())
    generated.append(create_erd_mmd(tables))
    generated.append(create_erd_dbml(tables))
    generated.append(create_ddl(tables))
    generated.extend(create_docs())
    generated.append(create_google_result([x for x in csv_files if x.suffix.lower() == ".csv"]))
    generated.append(BASE_DIR / "generate_all.py")

    print("=== 생성된 파일 목록 ===")
    for p in sorted(generated):
        print(p)


if __name__ == "__main__":
    main()
