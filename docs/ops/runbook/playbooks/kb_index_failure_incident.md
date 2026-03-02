# kb_index_failure_incident

## Symptoms / Detection Signals
- `tb_kb_reindex_job.status`가 `RETRY_WAIT` 또는 `DEAD_LETTER`로 증가.
- `tb_kb_document_version.pipeline_status`가 `FAILED` 또는 장시간 `RUNNING`에 고착.
- 운영 지표 이상:
  - `kb_index_latency_ms` 급증
  - `kb_index_fail_rate` 상승
  - `parser_error_rate` 상승
- 로그 키워드:
  - `KB_INDEX_JOB_FAILED`
  - `KB_INDEX_JOB_RETRY_SCHEDULED`
  - `KB_INDEX_JOB_DEAD_LETTER`

## Immediate Mitigation (First Response)
1. 릴리즈/대량 업로드를 잠시 동결한다.
2. 실패 `job_id`, `tenant_key`, `trace_id`를 먼저 확보한다.
3. 실패 단계(parser/embed/search)를 `error_code`로 분류한다.
4. 승인 전환(`approve`)은 `pipeline_status=INDEXED`인 버전만 허용되는지 확인한다.

## Verification Commands (Normal vs Abnormal)
정상 기준:
- 신규 잡이 `PENDING -> RUNNING -> DONE`으로 수렴.
- `pipeline_status=INDEXED`이며 `pipeline_error_code`가 비어 있음.
- 동일 `Idempotency-Key` 요청 시 동일 `job_id` 재사용.

비정상 기준:
- 동일 잡이 `RETRY_WAIT`를 반복하고 `attempt_count`가 증가.
- `attempt_count >= max_attempts` 후 `DEAD_LETTER` 전환.
- `pipeline_error_excerpt`에 민감정보 패턴이 노출됨(허용 불가).

읽기 전용 확인 SQL:
```sql
SELECT id,
       tenant_id,
       job_type,
       status,
       attempt_count,
       max_attempts,
       next_retry_at,
       error_code,
       error_excerpt,
       last_trace_id,
       requested_at,
       completed_at
FROM tb_kb_reindex_job
ORDER BY requested_at DESC
LIMIT 100;
```

```sql
SELECT id,
       document_id,
       version_no,
       status,
       pipeline_status,
       pipeline_error_code,
       pipeline_error_excerpt,
       pipeline_updated_at,
       updated_at
FROM tb_kb_document_version
ORDER BY updated_at DESC
LIMIT 100;
```

## Recovery Procedure (lease_until / fencing_token / janitor job focus)
1. 먼저 스케줄러 락 상태를 확인한다(`kb_index_pipeline_worker`).
2. 락 이상 시 `scheduler_lock_incident` 절차대로 `lease_until_utc`, `fencing_token`, janitor 복구 상태를 확인한다.
3. 락 정상인데 KB 잡만 실패하면, 실패 원인별로 조치한다:
   - parser 계열(`KB-INDEX-PARSER-*`): 원문 형식/파서 규칙 점검
   - embed 계열(`KB-INDEX-EMBED-*`): 임베딩 생성기/입력 길이 점검
   - search 계열(`KB-INDEX-SEARCH-*`): 인덱스 쓰기 가능 상태 점검
4. 원인 해소 후 `DEAD_LETTER` 잡은 신규 요청으로 재큐잉한다(기존 job 재강제 실행 금지).
5. 재처리 완료 후 `approve` 전환 및 검색 경로가 승인 버전만 조회하는지 검증한다.

## Post-Incident Actions
- `incident_id`, `root_trace_id`, `tenant_key`, 장애 구간(`from_utc/to_utc`)을 기록한다.
- 증적은 마스킹된 형태로만 저장한다(PII/토큰/쿠키/키 금지).
- 재발 방지 체크:
  - Idempotency-Key 정책 준수 여부
  - retry/backoff 파라미터 적정성
  - `DEAD_LETTER` 모니터링 알람 임계값
  - 파서/임베딩/검색 실패 통합테스트 최신 PASS 여부

