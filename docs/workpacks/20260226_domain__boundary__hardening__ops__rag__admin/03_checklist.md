# Workpack Checklist - 20260226_domain__boundary__hardening__ops__rag__admin

- [x] Added `assert_application_port_boundaries.py` with ratchet and baseline-growth guard
- [x] Added `application_port_boundary_contract.json` and baseline `violations=[]`
- [x] Refactored `operations` application services to depend on domain ports
- [x] Refactored `knowledge/rag` application services to depend on domain ports
- [x] Removed `knowledge/rag/presentation` direct infrastructure dependency via `CitationQueryService`
- [x] Moved `CitationView` to `knowledge/rag/domain/readmodel`
- [x] Tightened backoffice ACL contract to forbid `.domain.` imports
- [x] Updated `AdminOpsDashboardController` to consume application-level views only
- [x] Added/updated gate tests (application-port + backoffice-domain import)
- [x] Regenerated boundary gate artifacts and confirmed PASS
