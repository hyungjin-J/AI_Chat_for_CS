# Backend Domain Template

## Goal
Use this template when creating a new backend bounded context so structure and boundary rules stay consistent.

## Directory Template

```text
backend/src/main/java/com/aichatbot/contexts/<context>
├─ domain
│  ├─ model
│  ├─ service
│  └─ mapper
├─ application
│  ├─ usecase
│  └─ dto
├─ infrastructure
│  ├─ persistence
│  │  └─ mybatis
│  └─ external
└─ presentation
   ├─ controller
   ├─ request
   └─ response
```

Mapper XML location:

```text
backend/src/main/resources/mappers/<context>/**/**/*Mapper.xml
```

## File Checklist

1. Domain model root class/record in `domain/model`.
2. Domain service interface in `domain/service`.
3. MyBatis mapper interface in `domain/mapper`.
4. Application use case interface and command/query DTOs.
5. Infrastructure persistence adapter backed by mapper interfaces.
6. Controller/request/response files with thin controller policy.
7. Unit and integration test skeleton.

## Boundary Rules

1. `domain` must not import `presentation` or framework concerns.
2. `application` orchestrates use cases and transactions.
3. `infrastructure` implements ports (mapper/external integrations).
4. Mapper XML namespace must match mapper interface FQCN.
5. SQL uses `#{}` only; `${}` is forbidden.
6. Tenant-scoped data must include `tenant_key` filter.

## Naming Rules

1. Context folder name: lowercase snake_case.
2. Java package: `com.aichatbot.contexts.<context>...`.
3. Class prefix: PascalCase form of `<context>`.
4. Mapper interface suffix: `Mapper`.

## Scaffold Command

```bash
python scripts/scaffold_backend_context.py --context <context>
```

Use `--dry-run` before generation in CI-sensitive branches.
