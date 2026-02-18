# MVP Verification Pack 변경 이력

- Last synced at: 2026-02-18 20:10 (KST)
- Version(commit): `3e057a3+working-tree`
- SSOT status source: `04_TEST_RESULTS.md`

## 2026-02-18 (Phase2 final gate hardening)
1. 검증팩 정본 식별 문서 `CURRENT.md`를 추가했다.
2. `00/06/PHASE2` 요약 문서를 `04_TEST_RESULTS`와 동일 상태 매트릭스로 정렬했다.
3. `_DEPRECATED/README.md`를 UTF-8 한글 기준으로 정리했다.
4. `scripts/assert_verification_pack_consistency.ps1`를 신규 추가했다.
5. consistency 스크립트에 PASS-아티팩트 존재 검증을 구현했다.
6. consistency 스크립트에 요약 문서 PASS 주장-결과표 충돌 검증을 구현했다.
7. consistency 스크립트에 정본 문서명 중복 탐지 검증을 구현했다.
8. `scripts/verify_all.ps1` 마지막 단계에 consistency 게이트를 추가했다.
9. `scripts/verify_all.ps1`에 Node 버전 정책(CI fail / local warn)을 추가했다.
10. Node 버전 로그 아티팩트(`node_version_check.txt`)를 생성하도록 추가했다.
11. `.github/workflows/mvp-demo-verify.yml`에 consistency 체크 단계를 추가했다.
12. nightly workflow에 `infra/docker-compose.ollama.yml` 기동 단계를 추가했다.
13. nightly workflow에서 provider 결과가 SKIPPED면 실패 처리하도록 변경했다.
14. `infra/docker-compose.ollama.yml`를 신규 추가했다.
15. `scripts/run_provider_regression.ps1`를 재작성했다.
16. provider 스크립트에 조용한 SKIPPED 금지 및 실행 가이드를 추가했다.
17. provider 스크립트에 ollama compose 자동 기동 시도를 추가했다.
18. idempotency 설정에 `redis-fail-strategy`를 추가했다.
19. production 프로파일 기본값을 `fail_closed`로 고정했다.
20. router에 Redis 장애 시 fail_closed/fallback_memory 분기 로직을 추가했다.
21. Redis fallback 발생 메트릭 `idempotency_redis_fallback_total`을 추가했다.
22. `sse_first_token` 메트릭명을 seconds 단위 관례로 정렬했다.
23. `scripts/generate_metrics_report.ps1`를 표본수(n)/해석 경고 포함 형태로 개선했다.
24. `docs/ops/BRANCH_PROTECTION_SETUP.md`를 신규 추가했다.

## 2026-02-18 (Phase2.1 gate lock)
1. Node 버전을 `.nvmrc`에서 `22.12.0`으로 고정했다.
2. `verify_all.ps1`를 로컬/CI 모두 기본 strict fail 정책으로 조정했다.
3. 로컬 임시 우회용 `APP_VERIFY_ALLOW_NON_22_NODE=true` 옵션을 추가했다.
4. SSE 동시성 실제 한도 검증 스크립트 `run_sse_concurrency_real_limit_test.ps1`를 추가했다.
5. 실한도 증빙 파일 `artifacts/sse_concurrency_real_limit_proof.txt` 생성 경로를 표준화했다.
6. 아티팩트 비밀/PII 스캔 스크립트 `scan_artifacts_for_secrets_and_pii.ps1`를 추가했다.
7. 브랜치 보호 점검 스크립트 `check_branch_protection.ps1`를 추가했다.
8. metrics 샘플링 래퍼 `run_metrics_sampling.ps1`를 추가했다.
9. `generate_metrics_report.ps1`에 샘플 실패 감지 및 예산 상향 설정을 보강했다.
10. SSOT consistency 스크립트에 `03_TEST_PLAN` ↔ `04_TEST_RESULTS` ID 집합 일치 검증을 추가했다.
11. SSOT consistency 스크립트에 `CHANGELOG.md` 존재/SSOT 소스 명시 검증을 추가했다.
12. `mvp-demo-verify.yml`에 실한도 동시성/브랜치 점검/아티팩트 스캔 단계를 추가했다.
13. 테스트 문서에 `SSE-CONC-REAL-001`, `SEC-ARTIFACT-SCAN-001` 항목을 추가했다.
14. 결과 문서 `OBS-METRICS-001`에 표본수 `n` 표시를 추가했다.
