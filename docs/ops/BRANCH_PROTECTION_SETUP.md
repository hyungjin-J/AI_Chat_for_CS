# BRANCH_PROTECTION_SETUP

## 목적
`mvp-demo-verify`가 실패하면 머지되지 않도록 GitHub 브랜치 보호 규칙을 5분 내 설정한다.

## 대상 브랜치
- `main` (또는 운영 기본 브랜치)

## 설정 절차
1. GitHub 저장소 > `Settings` > `Branches`
2. `Add branch protection rule`
3. Branch name pattern: `main`
4. `Require a pull request before merging` 체크
5. `Require status checks to pass before merging` 체크
6. Required checks에 아래 정확한 이름 추가:
   - `mvp-demo-verify / verify`
7. (권장) `Require branches to be up to date before merging` 체크
8. 저장

## 스크린샷 자리
- [ ] Branch rule 화면 스크린샷 첨부
- [ ] Required checks 목록 스크린샷 첨부

## 설정 완료 확인 방법
1. PR에서 `mvp-demo-verify` 실패 상태면 Merge 버튼이 비활성화되어야 한다.
2. `mvp-demo-verify` 성공 + 리뷰 승인 시에만 Merge 가능해야 한다.
3. 로컬 확인 스크립트:
   - `powershell -ExecutionPolicy Bypass -File scripts/check_branch_protection.ps1`
   - 결과 파일: `docs/review/mvp_verification_pack/artifacts/branch_protection_check.txt`

## 운영 체크리스트
- [ ] Required check 이름 오탈자 없음 (`mvp-demo-verify / verify`)
- [ ] fork PR 정책과 충돌 없음
- [ ] 관리자 예외 머지 비활성화 여부 확인
