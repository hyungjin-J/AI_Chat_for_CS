# MVP Verification Pack 변경 이력

- Last synced at: 2026-02-21 03:25 (KST)
- Version(commit): `working-tree`
- SSOT status source: `04_TEST_RESULTS.md`

## 2026-02-21 (gap closure evidence hardening)
1. P0 백엔드 계약 테스트를 추가했다.
   - `MessageAnswerContractNegativeFlowTest`
   - `PiiEndToEndContractTest`
   - `TraceIdContractTest`
   - `RbacTenantMatrixTest`
   - `SseResumeContractTest`
2. SSE 스트림 서비스에서 연결 가드 해제를 `finally + 중복방지`로 보강해 테스트 간 429 회귀를 차단했다.
3. safe_response/error SSE payload에 `trace_id`를 보장하도록 보강했다.
4. 프론트 자동 테스트 체계를 도입했다.
   - `uuid.test.ts`, `sseParser.test.ts`, `errorMapping.test.ts`, `App.invalid-id-guard.test.tsx`
5. CI 게이트를 확장했다.
   - frontend test 실행
   - UUID lint 명시 실행
   - gitleaks 시크릿 스캔 추가
   - provider regression 조건부 실행(변수 기반)
6. `04_TEST_RESULTS.md`에 신규 테스트 ID와 최신 상태(PASS/SKIPPED)를 반영했다.
7. `00/03/06` 문서를 `04_TEST_RESULTS.md` 기준으로 재정렬했다.
8. 신규 아티팩트를 추가했다.
   - `frontend_test_output.txt`
   - `gap_closure_consistency_output.txt`
   - `provider_regression_gap_closure_output.txt`
   - `provider_regression_exit_code.txt`
   - `uuid_cast_scan_output.txt`
   - `mybatis_dollar_scan_output.txt`

## 2026-02-21 (project completion hardening)
1. `scripts/assert_verification_pack_consistency.ps1`에서 삭제된 `PHASE2_PROGRESS_SUMMARY_FOR_CHATGPT.md` 강제 의존을 제거했다.
2. 테스트/결과/CURRENT 문서의 실행 진입점을 `scripts/check_all.ps1`로 정렬했다.
3. `scripts/check_all.ps1`, `scripts/check_all.sh`를 추가하고 `verify_all`은 호환 래퍼로 유지했다.
4. 레거시 `/api/v1/**` 경로 차단 정책과 연동된 테스트를 보강했다.

## 2026-02-21 (post gap closure hardening)
1. provider 증빙 단일 진실원천 문서를 추가했다.
   - `docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md`
2. provider 증빙 정합성 스크립트를 추가하고 CI/one-command에 연결했다.
   - `scripts/assert_provider_regression_evidence.ps1`
   - `.github/workflows/mvp-demo-verify.yml`
   - `scripts/check_all.ps1`
3. provider 최신 PASS 근거를 커밋 가능한 아티팩트로 고정했다.
   - `artifacts/provider_regression_ollama_PASS_20260219_003600Z.txt`
4. SSE 동시성 계약 테스트를 추가해 한도 유지를 증명했다.
   - `SseConcurrencyLimitContractTest`
5. PII/trace 테스트를 강화했다.
   - PII: SSE payload raw PII 무유출 검증 추가
   - trace: safe_response + rag/stream_event 저장 trace 일치 검증 추가
