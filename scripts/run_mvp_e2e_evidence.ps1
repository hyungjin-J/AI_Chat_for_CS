$ErrorActionPreference = "Stop"

$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
New-Item -ItemType Directory -Force -Path "tmp" | Out-Null

function New-Uuid {
    [guid]::NewGuid().ToString()
}

function Write-JsonFile($path, $jsonText) {
    $jsonText | Out-File -FilePath $path -Encoding utf8
}

# Ensure clean backend process on 8080.
$existing = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if ($existing) {
    foreach ($procId in $existing) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

$backendLog = Join-Path $artifactDir "backend_runtime_e2e_output.txt"
if (Test-Path $backendLog) {
    Remove-Item $backendLog -Force
}

$env:SPRING_PROFILES_ACTIVE = "postgres"
$env:APP_LLM_PROVIDER = "mock"
$env:DB_URL = "jdbc:postgresql://localhost:5432/aichatbot"
$env:DB_USERNAME = "aichatbot"
$env:DB_PASSWORD = "local-dev-only-password"

$bootProc = Start-Process cmd.exe -ArgumentList "/c cd /d backend && gradlew.bat bootRun --no-daemon > ..\$backendLog 2>&1" -PassThru

try {
    $ready = $false
    for ($i = 0; $i -lt 90; $i++) {
        try {
            Invoke-RestMethod -Uri "http://localhost:8080/health" -Method GET `
                -Headers @{"X-Tenant-Key" = "demo-tenant"; "X-Trace-Id" = "11111111-1111-4111-8111-111111111111"} `
                -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) {
        throw "backend_not_ready"
    }

    $tenant = "demo-tenant"

    $traceLogin = New-Uuid
    $idemLogin = New-Uuid
    $loginBodyPath = "tmp/login_body.json"
    Write-JsonFile $loginBodyPath '{"login_id":"agent1","password":"agent1-pass","channel_id":"test","client_nonce":"nonce-login"}'
    $loginRespRaw = cmd /c "curl -sS http://localhost:8080/v1/auth/login -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $traceLogin"" -H ""Idempotency-Key: $idemLogin"" -H ""Content-Type: application/json"" --data-binary @$loginBodyPath 2>nul"
    $login = $loginRespRaw | ConvertFrom-Json
    $token = $login.access_token
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "login_failed: $loginRespRaw"
    }

    $traceSession = New-Uuid
    $idemSession = New-Uuid
    $sessionBodyPath = "tmp/session_body.json"
    Write-JsonFile $sessionBodyPath "{}"
    $sessionRespRaw = cmd /c "curl -sS http://localhost:8080/v1/sessions -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $traceSession"" -H ""Idempotency-Key: $idemSession"" -H ""Content-Type: application/json"" --data-binary @$sessionBodyPath 2>nul"
    $session = $sessionRespRaw | ConvertFrom-Json
    $sessionId = $session.session_id
    if ([string]::IsNullOrWhiteSpace($sessionId)) {
        throw "create_session_failed: $sessionRespRaw"
    }

    $traceMsg = New-Uuid
    $idemMsg = New-Uuid
    $messageBodyPath = "tmp/message_body.json"
    Write-JsonFile $messageBodyPath '{"text":"refund policy","top_k":3,"client_nonce":"nonce-refund"}'
    $msgRespRaw = cmd /c "curl -sS http://localhost:8080/v1/sessions/$sessionId/messages -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $traceMsg"" -H ""Idempotency-Key: $idemMsg"" -H ""Content-Type: application/json"" --data-binary @$messageBodyPath 2>nul"
    $msg = $msgRespRaw | ConvertFrom-Json
    $messageId = $msg.id
    if ([string]::IsNullOrWhiteSpace($messageId)) {
        throw "post_message_failed: $msgRespRaw"
    }

    $traceStream = New-Uuid
    $normalSse = cmd /c "curl -sS -N http://localhost:8080/v1/sessions/$sessionId/messages/$messageId/stream -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $traceStream"" 2>nul"
    $normalSsePath = Join-Path $artifactDir "sse_stream_normal.log"
    $normalSse | Out-File -FilePath $normalSsePath -Encoding utf8

    $traceCitation = New-Uuid
    $citResp = cmd /c "curl -sS http://localhost:8080/v1/rag/answers/$messageId/citations -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $traceCitation"" 2>nul"
    $citPath = Join-Path $artifactDir "citations_api_response.json"
    $citResp | Out-File -FilePath $citPath -Encoding utf8
    $citJson = $citResp | ConvertFrom-Json
    if ($null -eq $citJson.data -or $citJson.data.Count -lt 1) {
        throw "citation_missing: $citResp"
    }

    # Additional PII input request to prove request/log masking without affecting normal-answer proof.
    $tracePiiMsg = New-Uuid
    $idemPiiMsg = New-Uuid
    $piiMessageBodyPath = "tmp/message_body_pii.json"
    Write-JsonFile $piiMessageBodyPath '{"text":"refund policy. contact refund-team@example.com or +82 10-1234-5678 order AB-123456","top_k":3,"client_nonce":"nonce-refund-pii"}'
    $null = cmd /c "curl -sS http://localhost:8080/v1/sessions/$sessionId/messages -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $tracePiiMsg"" -H ""Idempotency-Key: $idemPiiMsg"" -H ""Content-Type: application/json"" --data-binary @$piiMessageBodyPath 2>nul"

    $traceTenant = New-Uuid
    $tenantResp = cmd /c "curl -sS -i http://localhost:8080/v1/sessions/$sessionId -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: tenant-a"" -H ""X-Trace-Id: $traceTenant"" 2>nul"
    $tenantPath = Join-Path $artifactDir "tenant_isolation_403_checks.txt"
    $tenantResp | Out-File -FilePath $tenantPath -Encoding utf8

    $dbTrace = docker exec aichatbot-postgres psql -U aichatbot -d aichatbot -t -A -c "SELECT trace_id::text FROM tb_message WHERE id = '$messageId' LIMIT 1;"
    $tracePath = Join-Path $artifactDir "trace_id_checks.txt"
    @"
http_post_message_trace_id=$traceMsg
message_response_trace_id=$($msg.trace_id)
db_message_trace_id=$dbTrace
message_id=$messageId
session_id=$sessionId
sse_events_with_trace:
$($normalSse -split "`n" | Where-Object { $_ -like "*trace_id*" -or $_ -like "event:done*" } | Out-String)
"@ | Out-File -FilePath $tracePath -Encoding utf8

    $excerpt = $citJson.data[0].excerpt_masked
    $dbMasked = docker exec aichatbot-postgres psql -U aichatbot -d aichatbot -t -A -c "SELECT query_text_masked FROM tb_rag_search_log ORDER BY created_at DESC LIMIT 1;"
    $piiPath = Join-Path $artifactDir "pii_masking_checks.txt"
    @"
input_raw=refund policy. contact refund-team@example.com or +82 10-1234-5678 order AB-123456
masked_in_rag_search_log=$dbMasked
citation_excerpt_masked=$excerpt
contains_raw_email=$($excerpt -like "*@example.com*")
contains_masked_email=$($excerpt -like "*@***")
"@ | Out-File -FilePath $piiPath -Encoding utf8

    $traceResume = New-Uuid
    $resumeSse = cmd /c "curl -sS -N http://localhost:8080/v1/sessions/$sessionId/messages/$messageId/stream/resume?last_event_id=2 -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $traceResume"" 2>nul"
    $resumePath = Join-Path $artifactDir "sse_resume_proof.log"
    @"
# baseline_first_stream
$normalSse
# resume_from_last_event_id_2
$resumeSse
"@ | Out-File -FilePath $resumePath -Encoding utf8

    $e2ePath = Join-Path $artifactDir "e2e_curl_transcripts.txt"
    @"
LOGIN_TRACE=$traceLogin
$loginRespRaw

CREATE_SESSION_TRACE=$traceSession
$sessionRespRaw

POST_MESSAGE_TRACE=$traceMsg
$msgRespRaw
"@ | Out-File -FilePath $e2ePath -Encoding utf8

    # Keep a dedicated bootRun+Postgres artifact for review checklist.
    $bootrunPath = Join-Path $artifactDir "backend_bootrun_postgres_output.txt"
    if (Test-Path $backendLog) {
        Copy-Item $backendLog $bootrunPath -Force
    }

    Write-Output "OK session_id=$sessionId message_id=$messageId"
} finally {
    if ($bootProc -and -not $bootProc.HasExited) {
        Stop-Process -Id $bootProc.Id -Force -ErrorAction SilentlyContinue
    }
    $remain = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    if ($remain) {
        foreach ($procId in $remain) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}
