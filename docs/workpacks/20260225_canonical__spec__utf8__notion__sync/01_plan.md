# Workpack Plan - 20260225_canonical__spec__utf8__notion__sync

## Scope

- Remove UTF-8 BOM from 3 canonical spec CSV files only.
- Regenerate UTF-8 full-scan/current/baseline/ratchet/strict artifacts.
- Update `spec_sync_report.md` with Notion sync metadata and evidence links.
- Sync three mapped Notion pages in the same execution session.
- Refresh artifact index outputs and close merge-block gates.

## Constraints

- Preserve CSV schema/header/column semantics (encoding-only change).
- Preserve ROLE taxonomy and error payload shape.
- Preserve fail-closed answer contract and tenant/RBAC authority.
- Do not introduce REST/SSE public contract drift.

## Acceptance

- UTF-8 full-scan baseline reaches `0`.
- `continuation_utf8_strict_gate` stays `PASS` with `violation_count=0`.
- `spec_sync_report_gate` and `artifact_index_gate` are `PASS`.
- Notion sync evidence for Summary/Requirements/Development is recorded.
