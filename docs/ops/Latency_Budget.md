# Latency Budget

## 입력값
| Metric | Value |
|---|---|
| p50 total latency | 2200.0 ms |
| p95 total latency | 8500.0 ms |
| p99 total latency | 14000.0 ms |
| first-token | 1200.0 ms |
| token rate | 25.0 token/s |
| reconnect count | 1 |

## 권장값
| Parameter | Recommended |
|---|---|
| request timeout | 15000.0 ms |
| connect timeout | 3000.0 ms |
| retry backoff base | 480.0 ms |
| retry backoff max | 480.0 ms |

## 해석
- 체감 UX 상태: **양호**
- first-token 목표: 1~2초(P95)
- done 이전 종료 시 재연결은 최대 3회 이내로 유지
- 429 수신 시 Retry-After 우선 적용, 클라이언트 임의 재시도 금지
- fail-closed 트리거(citation 누락/계약실패) 시 즉시 safe_response로 전환
