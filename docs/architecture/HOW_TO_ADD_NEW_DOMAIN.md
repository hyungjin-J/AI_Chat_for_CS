# 새 도메인 추가 방법 (DDD Template)

## 목적
새 도메인/피처를 추가할 때 구조 일관성을 유지하고, Codex 스캐폴딩으로 시작 시간을 줄인다.

## 1) Backend 컨텍스트 생성

```bash
python scripts/scaffold_backend_context.py --context <context_name> --dry-run
python scripts/scaffold_backend_context.py --context <context_name>
```

생성 위치:
- `backend/src/main/java/com/aichatbot/contexts/<context_name>/...`
- `backend/src/main/resources/mappers/<context_name>/...`
- `backend/src/test/java/com/aichatbot/contexts/<context_name>/...`

필수 확인:
1. `domain/application/infrastructure/presentation` 디렉토리 생성 확인
2. Mapper XML namespace와 Mapper 인터페이스 FQCN 일치 확인
3. SQL 바인딩에서 `${}` 금지, `#{}`만 사용
4. 테넌트 데이터 접근은 `tenant_key` 조건 포함

## 2) Frontend 피처 생성

```bash
python scripts/scaffold_frontend_feature.py --context <context_name> --feature <feature_name> --dry-run
python scripts/scaffold_frontend_feature.py --context <context_name> --feature <feature_name>
```

생성 위치:
- `frontend/src/features/<context_name>/<feature_name>/api|model|hooks|ui`

필수 확인:
1. `pages/*`는 route composition only 유지
2. 비즈니스 로직/API wiring은 `features/*` 내부 유지
3. 공통 유틸은 `frontend/src/shared`로 이동

## 3) 경계/게이트 확인

```bash
python scripts/assert_workpack_agent_report_contract.py --use-git-diff --git-base-ref origin/main
python scripts/assert_platform_boundary.py
python -m unittest discover -s scripts/tests -p "test_*.py"
```

필수 확인:
1. `platform/sharedkernel`에서 `contexts.*` import 금지
2. 신규 스캐폴딩 테스트 통과
3. workpack(01/02/03) + agent report(DDD/SEC/QA) 계약 통과
4. 기존 게이트(`spec_consistency`, doc lint 등) 통과

## 4) 마무리 체크리스트
1. 기능/보안 정책/하드닝 동작 변화 없음
2. public API 계약 변화 없음
3. chatGPT handoff 문서 2종(AGENTS 16.8) 업데이트
4. 증적 아티팩트 경로 업데이트 및 lint PASS
