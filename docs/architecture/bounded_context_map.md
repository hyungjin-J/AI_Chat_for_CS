# Bounded Context Map

## Purpose
This document fixes the bounded-context ownership model used by backend/frontend refactors and scaffold automation.

## Context Catalog

| Context | Source Packages | Owns | Depends On |
|---|---|---|---|
| Identity | `auth`, RBAC subset from `admin` | login, MFA, role matrix, session auth state | Platform security, SharedKernel role/tenant |
| Conversation | `session`, `message`, `answer`, `llm`, `tool` | message/session lifecycle, response generation, streaming state | Identity, Knowledge, Billing |
| Knowledge | `rag` | retrieval, citation, evidence scoring | Platform mybatis, Conversation |
| Billing | `billing` | plan, quota, usage, rate card | Conversation, Backoffice |
| Operations | `ops`, parts of `global.audit` and `global.scheduler` | ops dashboards, audit/export, ops events | Cross-context events |
| Backoffice channel | `/v1/admin/*` controllers in multiple packages | operator workflows, cross-context orchestration | Identity, Operations, Billing |

## Shared Layers

| Layer | Owns | Must Not Own |
|---|---|---|
| `platform` | config, security, error, observability, privacy, mybatis wiring | business policy and domain decisions |
| `sharedkernel` | stable primitives and shared value types (`TenantKey`, `TraceId`, `Role`, `UtcClock`) | context-specific use cases |

## Interaction Rules

1. Context-to-context integration is done through application service interfaces or ACL adapters.
2. `platform` must not import `contexts.*` packages.
3. `sharedkernel` contains only stable abstractions reused by multiple contexts.
4. Backoffice orchestration composes domain use cases; it does not become a policy owner.

## Admin Classification

`admin` is classified as a **channel** (`channels/backoffice`) rather than a single business domain.  
Reason: current `/v1/admin/*` API surface crosses Identity/Operations/Billing boundaries.

## Migration Note

Current package names remain valid during transition.  
Target package shape is introduced incrementally by PR:
1. contract and template lock,
2. backend package migration,
3. frontend feature migration.
