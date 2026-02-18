# AI_Chatbot 폴더 안내와 전체 진행 상황

작성일: 2026-02-18  
기준 문서: `docs/review/mvp_verification_pack/04_TEST_RESULTS.md`

## 1) 폴더별 안내 (무엇이 있고, 왜 있는지)

| 위치 | 안에 들어 있는 것(대표) | 왜 필요한지 |
|---|---|---|
| `.agents/` | 작업 규칙, 보조 기능 설명 파일 | 자동 작업 도구가 같은 기준으로 일하게 하기 위해 |
| `.github/workflows/` | `mvp-demo-verify.yml`, `provider-regression-nightly.yml` 등 | 코드가 바뀔 때 자동 점검을 돌려 실수를 줄이기 위해 |
| `backend/` | 서버 프로그램 코드, 실행 설정, 테스트 코드 | 로그인/질문/답변 생성/권한 체크 같은 핵심 기능을 처리하기 위해 |
| `frontend/` | 화면 코드(`src/`), 빌드 결과(`dist/`), 설치 패키지(`node_modules/`) | 상담원이 실제로 보는 화면을 제공하기 위해 |
| `infra/` | `docker-compose.yml`, `docker-compose.ollama.yml` | 개발 PC에서 서버/저장소/보조 도구를 한 번에 실행하기 위해 |
| `scripts/` | 전체 점검 스크립트(`verify_all.ps1`), 문서 일치 확인, 보안 점검 스크립트 | 반복 작업을 자동화하고, 사람 실수를 줄이기 위해 |
| `tests/` | 스트리밍 재연결/기본 흐름 확인 스크립트 | 중요한 동작이 실제로 잘 되는지 확인하기 위해 |
| `docs/` | 설계서, 점검 결과, 운영 가이드, 참고 스펙 | “왜 이렇게 만들었는지”와 “어떻게 확인했는지”를 남기기 위해 |
| `docs/review/mvp_verification_pack/` | 요약, 테스트 계획, 결과표, 증빙 파일 목록 | 현재 상태를 한곳에서 확인하고, 외부 검토를 받기 위해 |
| `docs/review/mvp_verification_pack/artifacts/` | 실제 실행 결과 파일(로그/응답/검사 결과) | 문서의 PASS/FAIL이 사실인지 증거로 보여주기 위해 |
| `docs/references/` | 요구사항/DB/API/개발환경 기준 파일(CSV, XLSX) | 프로젝트의 공식 기준(원천 문서)으로 사용하기 위해 |
| `docs/uiux/` | 화면 설계서, 화면 관련 정리 문서 | 화면 동작/문구/오류 표시 기준을 맞추기 위해 |
| `docs/ops/` | 운영 체크 문서, 배포 전 점검 문서 | 운영 단계에서 필요한 설정과 확인 절차를 표준화하기 위해 |
| `evaluation/` | 품질 측정용 데이터/리포트 형식/실행 코드 | 답변 품질을 수치로 점검하기 위해 |
| `tools/` | 다이어그램 제작 등 보조 도구 파일 | 반복 생성 작업(그림, 자료 생성)을 빠르게 하기 위해 |
| `tmp/` | 임시 파일 보관용 | 작업 중 잠깐 생성되는 파일을 분리하기 위해 |
| `_backup/` | 과거 백업 자료 | 이전 상태를 참고하거나 복구할 때 사용하기 위해 |

## 2) 전체 진행 상황과 남은 작업

| 항목 | 현재 상태 | 근거(증빙) | 남은 작업 |
|---|---|---|---|
| 서버 자동 테스트 | 완료 | `docs/review/mvp_verification_pack/artifacts/backend_gradle_test_output.txt` | 없음 |
| 화면 빌드 확인 | 완료 | `docs/review/mvp_verification_pack/artifacts/frontend_build_output.txt` | 없음 |
| 기본 흐름(로그인→세션→질문) | 완료 | `docs/review/mvp_verification_pack/artifacts/e2e_curl_transcripts.txt` | 없음 |
| 스트리밍 정상 흐름(근거 포함) | 완료 | `docs/review/mvp_verification_pack/artifacts/sse_stream_normal.log` | 없음 |
| 안전 차단 흐름(근거 부족 시 안전 응답) | 완료 | `docs/review/mvp_verification_pack/artifacts/sse_stream_fail_closed.log` | 없음 |
| 다른 회사 데이터 접근 차단 | 완료 | `docs/review/mvp_verification_pack/artifacts/tenant_isolation_403_checks.txt` | 없음 |
| 개인정보 가림 처리 | 완료 | `docs/review/mvp_verification_pack/artifacts/pii_masking_checks.txt` | 없음 |
| 요청 추적 번호 일치 확인 | 완료 | `docs/review/mvp_verification_pack/artifacts/trace_id_checks.txt` | 없음 |
| 사용량 제한/동시 연결 제한 | 완료 | `docs/review/mvp_verification_pack/artifacts/budget_429_checks.txt`, `docs/review/mvp_verification_pack/artifacts/sse_concurrency_real_limit_proof.txt` | 없음 |
| 문서끼리 결과 충돌 방지 점검 | 완료 | `docs/review/mvp_verification_pack/artifacts/e2e_runner_stdout.txt` | 없음 |
| 실제 외부 답변 도구(ollama) 회귀 점검 | 일부 보류(SKIPPED) | `docs/review/mvp_verification_pack/artifacts/provider_regression_ollama.log` | 실행 환경(ollama) 준비 후 1회 PASS 증빙 필요 |

## 3) 지금 기준 한 줄 정리

- 지금 프로젝트는 **데모 시연 가능한 상태**입니다.
- 다만 “실제 외부 답변 도구 점검”은 환경 준비 후 다시 실행해 PASS 증빙을 남기면 더 안정적인 마감이 됩니다.

## 4) 문서 읽는 순서(처음 보는 분용)

1. `docs/review/mvp_verification_pack/00_EXEC_SUMMARY.md` (전체 요약)
2. `docs/review/mvp_verification_pack/04_TEST_RESULTS.md` (최신 결과표)
3. `docs/review/mvp_verification_pack/06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md` (증빙 연결표)
4. `docs/review/mvp_verification_pack/artifacts/` (실행 증거 원본)
