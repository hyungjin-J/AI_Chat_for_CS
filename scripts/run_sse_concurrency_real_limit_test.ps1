$ErrorActionPreference = "Stop"

$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
New-Item -ItemType Directory -Force -Path "tmp" | Out-Null
$outPath = Join-Path $artifactDir "sse_concurrency_real_limit_proof.txt"
$backendLog = Join-Path $artifactDir "sse_concurrency_real_limit_backend.log"

function New-Uuid { [guid]::NewGuid().ToString() }

function Write-JsonFile($path, $jsonText) {
    $jsonText | Out-File -FilePath $path -Encoding utf8
}

function Status-FromRawResponse {
    param([string]$raw)
    $match = [regex]::Match($raw, "HTTP/[0-9.]+\s+([0-9]{3})")
    if ($match.Success) { return $match.Groups[1].Value }
    return "unknown"
}

function ErrorCode-FromRawResponse {
    param([string]$raw)
    $match = [regex]::Match($raw, '"error_code"\s*:\s*"([^"]+)"')
    if ($match.Success) { return $match.Groups[1].Value }
    return ""
}

function Stop-Backend {
    param($proc)
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    $remain = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    if ($remain) {
        foreach ($procId in $remain) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

$existing = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if ($existing) {
    foreach ($procId in $existing) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

docker compose -f infra/docker-compose.yml up -d | Out-Null

$env:SPRING_PROFILES_ACTIVE = "postgres"
$env:APP_LLM_PROVIDER = "mock"
$env:DB_URL = "jdbc:postgresql://localhost:5432/aichatbot"
$env:DB_USERNAME = "aichatbot"
$env:DB_PASSWORD = "local-dev-only-password"
$env:APP_BUDGET_SSE_CONCURRENCY_MAX_PER_USER = "2"
$env:APP_BUDGET_SSE_HOLD_MS = "3000"

$backendProc = Start-Process cmd.exe -ArgumentList "/c cd /d backend && gradlew.bat bootRun --no-daemon > ..\$backendLog 2>&1" -PassThru

try {
    $ready = $false
    for ($i = 0; $i -lt 90; $i++) {
        try {
            Invoke-RestMethod -Uri "http://localhost:8080/health" -Method GET `
                -Headers @{"X-Tenant-Key" = "demo-tenant"; "X-Trace-Id" = (New-Uuid)} `
                -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) { throw "backend_not_ready" }

    $tenant = "demo-tenant"
    $loginBodyPath = "tmp/sse_real_login.json"
    Write-JsonFile $loginBodyPath '{"login_id":"agent1","password":"agent1-pass","channel_id":"test","client_nonce":"sse-real-login"}'
    $loginResp = cmd /c "curl -sS http://localhost:8080/v1/auth/login -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$loginBodyPath 2>nul"
    $login = $loginResp | ConvertFrom-Json
    $token = $login.access_token
    if ([string]::IsNullOrWhiteSpace($token)) { throw "login_failed" }

    $sessionBodyPath = "tmp/sse_real_session.json"
    Write-JsonFile $sessionBodyPath "{}"
    $sessionResp = cmd /c "curl -sS http://localhost:8080/v1/sessions -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$sessionBodyPath 2>nul"
    $session = $sessionResp | ConvertFrom-Json
    $sessionId = $session.session_id

    $messageBodyPath = "tmp/sse_real_msg.json"
    Write-JsonFile $messageBodyPath '{"text":"refund policy","top_k":3,"client_nonce":"sse-real-msg"}'
    $msgResp = cmd /c "curl -sS http://localhost:8080/v1/sessions/$sessionId/messages -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$messageBodyPath 2>nul"
    $msg = $msgResp | ConvertFrom-Json
    $messageId = $msg.id

    $url = "http://localhost:8080/v1/sessions/$sessionId/messages/$messageId/stream"
    $h1 = "Authorization: Bearer $token"
    $h2 = "X-Tenant-Key: $tenant"

    $job1 = Start-Job -ScriptBlock {
        param($url, $h1, $h2)
        cmd /c "curl -sS -N --max-time 8 $url -H ""$h1"" -H ""$h2"" -H ""X-Trace-Id: $([guid]::NewGuid())"" 2>nul"
    } -ArgumentList $url, $h1, $h2

    $job2 = Start-Job -ScriptBlock {
        param($url, $h1, $h2)
        cmd /c "curl -sS -N --max-time 8 $url -H ""$h1"" -H ""$h2"" -H ""X-Trace-Id: $([guid]::NewGuid())"" 2>nul"
    } -ArgumentList $url, $h1, $h2

    Start-Sleep -Milliseconds 400

    $thirdRaw = cmd /c "curl -sS -i $url -H ""$h1"" -H ""$h2"" -H ""X-Trace-Id: $(New-Uuid)"" 2>nul"
    $thirdStatus = Status-FromRawResponse $thirdRaw
    $thirdCode = ErrorCode-FromRawResponse $thirdRaw

    $firstOut = Receive-Job -Job $job1 -Wait -AutoRemoveJob
    $secondOut = Receive-Job -Job $job2 -Wait -AutoRemoveJob

    @"
mode=real_limit
sse_concurrency_limit=2
sse_hold_ms=3000
third_status=$thirdStatus
third_error_code=$thirdCode
expected_status=429
expected_error_code=API-008-429-SSE
third_raw=$thirdRaw
first_stream_has_done=$($firstOut -like "*event:done*")
second_stream_has_done=$($secondOut -like "*event:done*")
"@ | Out-File -FilePath $outPath -Encoding utf8

    if ($thirdStatus -ne "429" -or $thirdCode -ne "API-008-429-SSE") {
        throw "sse_concurrency_real_limit_proof_failed"
    }

    Write-Host "sse_concurrency_real_limit=PASS"
} finally {
    Stop-Backend -proc $backendProc
}
