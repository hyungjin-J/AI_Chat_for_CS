# Agent Manual 03 - PR Decomposition and Agent Roles

## Purpose
Split work into rollback-safe and ownership-clear units.

## Minimum PR Rule
- At least 2 PRs are required.
- Preferred: 3 PRs (control plane, documentation, QA gate wiring).

## Role Assignment Model
1. Control-Plane Agent
   - Hook script and control bootstrap
2. Documentation Architect Agent
   - Workpack and hardening pre-report artifacts
3. QA/Gate Agent
   - Gate execution contract and evidence checks
4. Release/Handoff Agent
   - Handoff docs and validation gate traceability

## Specialized Agent Reports (Mandatory for high-risk changes)
- Report root:
  - `docs/review/agent_reports/YYYYMMDD_<topic>/`
- Required files:
  - `DDD_report.md`
  - `SEC_report.md`
  - `QA_report.md`
- Template source:
  - `docs/review/templates/agent_reports/DDD_report_template.md`
  - `docs/review/templates/agent_reports/SEC_report_template.md`
  - `docs/review/templates/agent_reports/QA_report_template.md`

## PR Boundary Rules
- No mixed concern PRs that combine unrelated goals.
- Every PR must define:
  - scope
  - out-of-scope
  - rollback unit
  - evidence outputs

## DoD Gate Set (Mandatory in each PR)
- backend test
- frontend build and test
- spec consistency check
- utf8 strict check
- document and Notion gate checks
