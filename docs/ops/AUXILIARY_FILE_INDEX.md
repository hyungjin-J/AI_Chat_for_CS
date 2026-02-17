# Auxiliary File Index

## Scope
- This index documents **non-implementation artifacts** in the repository.
- Excluded from this index:
  - `backend/src/main/java/**`
  - `frontend/src/**` (except static template assets if needed for operation context)

## Folder Roles
| Folder | Role |
|---|---|
| `.agents/` | Agent skill definitions and references |
| `.github/` | CI workflow definitions |
| `docs/` | Specs, operational docs, UI/UX artifacts |
| `infra/` | Local infra runtime definitions |
| `scripts/` | Validation, sync, gatekeeping automation |
| `tools/` | Scaffold/generator utilities and archived bootstrap scripts |
| `tests/` | Utility-level test scripts |
| `tmp/` | Local-only temp workspace (git tracks only `.gitkeep`) |
| `_backup/` | Backup policy folder (git tracks policy docs only) |

## Root Auxiliary Files
| File | Purpose |
|---|---|
| `AGENTS.md` | Global project rules and quality/security constraints |
| `README.md` | Project bootstrap and run guide |
| `.gitignore` | Ignore policy for cache/temp/artifacts |
| `spec_sync_report.md` | Spec↔Notion synchronization report log |

## CI / Agent
| File | Purpose |
|---|---|
| `.github/workflows/requirement-trace.yml` | Runs traceability + PII guard checks on PRs |
| `.agents/.skill-lock.json` | Skill lock metadata |
| `.agents/skills/**` | Skill instructions/references/scripts for coding agents |

## Docs

### `docs/ops/`
| File | Purpose |
|---|---|
| `docs/ops/CODEX_WORKLOG.md` | Work execution and validation log |
| `docs/ops/Latency_Budget.md` | Latency budget calculation output |
| `docs/ops/AUXILIARY_FILE_INDEX.md` | This index |
| `docs/ops/TMP_ARTIFACT_SUMMARY.md` | Summary of removed temp dumps |

### `docs/references/`
| File | Purpose |
|---|---|
| `docs/references/README.md` | Reference artifact guide |
| `docs/references/generate_all.py` | Generates reference outputs |
| `docs/references/CS AI Chatbot_Requirements Statement.csv` | Requirements source-of-truth |
| `docs/references/Summary of key features.csv` | Feature summary spec |
| `docs/references/Development environment.csv` | Dev environment spec |
| `docs/references/google_ready_api_spec_v0.3_20260216.xlsx` | API workbook |
| `docs/references/CS_AI_CHATBOT_DB.xlsx` | DB workbook |

### `docs/references/generated/`
| File | Purpose |
|---|---|
| `docs/references/generated/ERD.dbml` | DBML ERD output |
| `docs/references/generated/ERD.mmd` | Mermaid ERD output |
| `docs/references/generated/postgresql_ddl.sql` | PostgreSQL DDL output |
| `docs/references/generated/MULTITENANCY_SAAS.md` | Multitenancy design notes |
| `docs/references/generated/MIGRATION_DEV_STG_PROD.md` | Migration strategy notes |
| `docs/references/generated/OPENSEARCH_HYBRID.md` | Hybrid search notes |
| `docs/references/generated/VECTOR_TUNING.md` | Vector tuning notes |
| `docs/references/generated/SECURITY_AUDIT_DBA.md` | Security/DBA audit notes |
| `docs/references/generated/COST_OPTIMIZATION.md` | Cost optimization notes |

### `docs/uiux/`
| File | Purpose |
|---|---|
| `docs/uiux/UIUX_Spec.md` | UI/UX integrated spec |
| `docs/uiux/NOTION_READY_UIUX.md` | Notion-ready UI/UX summary |
| `docs/uiux/Figma_to_React_Checklist.md` | Figma-to-React implementation checklist |
| `docs/uiux/CS_RAG_UI_UX_설계서.xlsx` | UI/UX workbook |

### `docs/uiux/reports/`
| File | Purpose |
|---|---|
| `docs/uiux/reports/trace_report.json` | UI traceability validation output |
| `docs/uiux/reports/spec_consistency_check_report.json` | Cross-spec consistency check output |
| `docs/uiux/reports/spec_sync_changes.json` | Sync-repair change log output |
| `docs/uiux/reports/xlsx_gate_report.json` | UIUX xlsx gate report |

### `docs/uiux/assets/`
| Pattern | Purpose |
|---|---|
| `docs/uiux/assets/*.png` | Screen mock/reference images for design traceability |

## Automation Scripts

### `scripts/` (active automation)
| File | Purpose |
|---|---|
| `scripts/spec_consistency_check.py` | Cross-spec consistency validator |
| `scripts/spec_sync_repair.py` | Spec sync auto-repair script |
| `scripts/validate_ui_traceability.py` | Req/API/DB/UI traceability validator |
| `scripts/uiux_xlsx_gate_lib.py` | Shared logic for UIUX xlsx gate checks |
| `scripts/validate_uiux_xlsx_gate.py` | UIUX gate validator entry |
| `scripts/run_uiux_xlsx_gatekeeper.py` | UIUX gatekeeper patch/validate runner |
| `scripts/generate_uiux_workbook.py` | Generates UIUX workbook |
| `scripts/fix_uiux_workbook_layout.py` | Workbook styling/layout normalization |
| `scripts/refresh_uiux_design.py` | Refreshes workbook visuals/assets |
| `scripts/latency_budget_calculator.py` | Latency markdown generator |
| `scripts/pii_guard_scan.py` | PII/secret pattern scanner |

### `tools/bootstrap_archive/` (archived bootstrap)
| File | Purpose |
|---|---|
| `tools/bootstrap_archive/00_bootstrap.cmd` | Legacy bootstrap step 00 |
| `tools/bootstrap_archive/10_generate_backend.cmd` | Legacy bootstrap step 10 |
| `tools/bootstrap_archive/11_backend_skeleton.cmd` | Legacy bootstrap step 11 |
| `tools/bootstrap_archive/20_generate_frontend.cmd` | Legacy bootstrap step 20 |
| `tools/bootstrap_archive/21_frontend_skeleton.cmd` | Legacy bootstrap step 21 |
| `tools/bootstrap_archive/30_generate_infra.cmd` | Legacy bootstrap step 30 |
| `tools/bootstrap_archive/40_install_skills.cmd` | Legacy bootstrap step 40 |
| `tools/bootstrap_archive/50_generate_gitignore.cmd` | Legacy bootstrap step 50 |
| `tools/bootstrap_archive/60_generate_readme.cmd` | Legacy bootstrap step 60 |
| `tools/bootstrap_archive/90_verify.cmd` | Legacy bootstrap step 90 |
| `tools/bootstrap_archive/99_git_init_commit_push.cmd` | Legacy bootstrap step 99 |
| `tools/bootstrap_archive/README.md` | Archive policy + rerun warning |

## Infra / Tools / Tests
| File | Purpose |
|---|---|
| `infra/docker-compose.yml` | Local infra stack definition |
| `tools/scaffold_writer.py` | Utility that writes scaffold/config docs/files |
| `tests/sse_stream_basic_test.py` | Basic SSE stream behavior script |

## Temp / Backup Policy State
| Path | Current Policy |
|---|---|
| `tmp/` | Keep local temp only; git tracks `tmp/.gitkeep` only |
| `_backup/` | Do not commit backup payloads; git tracks policy docs only |

## Hygiene Rules Snapshot
- Cache artifacts are non-trackable: `**/__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- UIUX report outputs are consolidated under `docs/uiux/reports/`
- Archived bootstrap scripts are under `tools/bootstrap_archive/`
