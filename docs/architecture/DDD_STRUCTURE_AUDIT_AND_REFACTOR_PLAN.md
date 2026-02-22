# DDD Structure Audit And Refactor Plan

## 1) Summary
This document is the architecture SSOT for the current DDD layout.
The repository now uses context-first boundaries and channel separation.

## 2) Current Structure Snapshot (2026-02-22)

### 2.1 Backend Java
```text
backend/src/main/java/com/aichatbot
├─ channels
│  └─ backoffice
├─ contexts
│  ├─ identity
│  ├─ conversation
│  ├─ knowledge
│  ├─ billing
│  └─ operations
├─ platform
└─ sharedkernel
```

### 2.2 Backend Resources (MyBatis)
```text
backend/src/main/resources/mappers
├─ conversation
├─ identity
├─ knowledge
├─ operations
└─ platform
```

### 2.3 Frontend
```text
frontend/src
├─ app
├─ features
├─ pages
├─ shared
└─ widgets
```

## 3) Boundary Rules
1. `presentation -> application -> domain` direction only.
2. `domain` must not import `presentation/application/infrastructure` directly.
3. Cross-context calls must use application ACL/contracts only.
4. `platform/sharedkernel` must not import domain policy.
5. `channels/backoffice` orchestrates contexts and must not own domain policy.

## 4) MyBatis Mapper Contract
1. Mapper interface: `backend/src/main/java/**/domain/**/mapper/*Mapper.java`
2. XML path: `backend/src/main/resources/mappers/<context>/**/*Mapper.xml`
3. XML namespace must match mapper interface FQCN.
4. `${}` is forbidden; `#{}` only.
5. Tenant-scoped data queries must include `tenant_key` filter.

## 5) Migration Focus (Open)
1. Add mapper namespace drift CI gate for all XML files.
2. Block legacy root package reintroduction by static contract gate.
3. Move billing persistence from in-memory repositories to mapper-backed persistence.

## 6) DoD
1. Architecture docs and AGENTS rules are consistent with actual source layout.
2. CI gates enforce boundary, namespace, and legacy-package contracts.
3. Public API contracts stay unchanged during structural migration.
