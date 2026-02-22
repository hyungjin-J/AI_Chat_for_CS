# Frontend Feature Template

## Goal
Use this template when adding a new frontend feature so routing stays thin and feature logic remains isolated.

## Directory Template

```text
frontend/src/features/<context>/<feature>
├─ api
├─ model
├─ hooks
└─ ui
```

## File Checklist

1. API functions in `api`.
2. Type definitions in `model`.
3. Feature hooks in `hooks`.
4. Presentational and container components in `ui`.
5. `index.ts` barrel export for route/page composition.

## Routing Rule

1. `frontend/src/pages` only composes route-level layouts and feature components.
2. Business logic, state orchestration, and API wiring belong to `features`.
3. Cross-feature reusable pieces move to `frontend/src/shared`.

## Naming Rules

1. Context and feature directories: lowercase snake_case.
2. Hook naming: `use<FeatureName>`.
3. Component naming: `<FeatureName>Panel` or explicit view names.
4. Public exports from `index.ts` only.

## Scaffold Command

```bash
python scripts/scaffold_frontend_feature.py --context <context> --feature <feature>
```

Use `--dry-run` to preview created files.
