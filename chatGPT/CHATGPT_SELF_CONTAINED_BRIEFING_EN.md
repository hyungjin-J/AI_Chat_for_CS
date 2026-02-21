# CHATGPT SELF-CONTAINED BRIEFING (EN)

## 1) Purpose
This file is a path-independent handoff brief for ChatGPT (or any LLM assistant) that cannot access the repository directly.
Use this as the single context packet before asking for planning, review, or implementation guidance.

Latest sync note:
- This brief is maintained under `chatGPT/` as the primary handoff location (AGENTS.md section 16.8).

## 2) Project Snapshot
- Project: `AI_Chatbot`
- Domain: Customer-support AI assistant with grounded responses (RAG), strong security, and operational governance.
- Current stage: Go-Live Gap Closure completed (production-readiness hardening applied).
- Overall readiness: High (pre-production operational check level).

## 3) What Has Been Implemented
### Auth and Session
- JWT login/refresh/logout.
- Refresh rotation with reuse detection.
- Account lockout and rate-limit protections.
- Session listing and revoke controls.
- MFA (TOTP) flow for high-privilege roles (OPS/ADMIN).

### Authorization and RBAC
- Server-side RBAC as final authority.
- Permission staleness detection (`permission_version`) with forced re-auth behavior.
- Admin permission updates guarded by approval workflow.

### Ops/Admin Capabilities
- Ops dashboard (summary + series).
- Audit log query, diff, export controls.
- Audit chain integrity verification endpoint and operational handling.
- Immediate block actions for account/IP level controls.

### Operational Hardening
- Append-only ops event model.
- UTC-based hourly metrics with idempotent aggregation.
- Scheduler lock pattern for multi-instance safety.
- Incident runbooks for scheduler lock, audit chain integrity, and spec/notion sync gate.

## 4) Non-Negotiable Policy Locks
Do not violate these constraints in proposals or code suggestions:

1. ROLE taxonomy is fixed: `AGENT`, `CUSTOMER`, `ADMIN`, `OPS`, `SYSTEM`.
2. `Manager/System Admin` are not roles; they are `ADMIN` internal permission levels.
3. Standard error payload shape is fixed:
   - `error_code`, `message`, `trace_id`, `details`
4. Security code semantics are fixed:
   - stale permission -> `401 AUTH_STALE_PERMISSION`
   - lockout -> `429 AUTH_LOCKED`
   - rate-limit -> `429 AUTH_RATE_LIMITED`
   - refresh reuse -> `409 AUTH_REFRESH_REUSE_DETECTED`
5. Hardening gate policies (cookie/CSRF/rotation/lockout/UTC-bucket) must remain locked.
6. If specs change, Notion sync + metadata update + sync report entry are mandatory.

## 5) Current Validation Status (Latest Known)
- Backend tests: PASS
- Frontend tests: PASS
- Frontend build: PASS
- Spec consistency gate: PASS
- UTF-8 integrity checks: PASS
- Notion sync status for latest spec updates: DONE

## 6) Remaining Risks (Phase2.1 Candidates)
1. Notion MCP token/permission expiry handling in CI must be continuously monitored.
2. Large audit export should be improved with async queue-based processing.
3. WebAuthn is not yet introduced (TOTP-first phase currently).
4. Scheduler lock auto self-healing is not implemented (runbook-based recovery currently).

## 7) How to Use This Brief with ChatGPT
When requesting output, always provide:
1. The target task (exactly what to produce).
2. The fixed constraints from section 4.
3. Whether the request is plan-only or implementation-ready.
4. The expected output format (e.g., checklist, PR plan, API review, runbook draft).

## 8) Ready-to-Paste Prompt Block
```text
You are assisting with AI_Chatbot.
Assume the repository is not directly accessible.
Use only the context below as source of truth.

Context summary:
- Go-Live hardening is already applied.
- Auth/session/RBAC/Ops-admin/audit-chain/scheduler-lock are implemented.
- Validation gates are currently PASS.
- Remaining risks are: Notion CI token ops, async audit export, WebAuthn not yet added, scheduler self-healing pending.

Hard constraints:
- ROLEs fixed: AGENT/CUSTOMER/ADMIN/OPS/SYSTEM
- Manager/System Admin are ADMIN internal levels, not roles
- Error format fixed: error_code/message/trace_id/details
- Stale=401 AUTH_STALE_PERMISSION
- Lockout=429 AUTH_LOCKED
- Rate-limit=429 AUTH_RATE_LIMITED
- Refresh reuse=409 AUTH_REFRESH_REUSE_DETECTED
- Do not relax hardening gate policies.

Task:
[INSERT YOUR TASK HERE]

Output format:
[INSERT REQUIRED FORMAT HERE]
```
