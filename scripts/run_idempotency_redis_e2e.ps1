$ErrorActionPreference = "Stop"

$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
New-Item -ItemType Directory -Force -Path "tmp" | Out-Null

function New-Uuid {
    [guid]::NewGuid().ToString()
}

function Start-Backend {
    param([string]$logPath)

    $existing = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    if ($existing) {
        foreach ($procId in $existing) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }

    $env:SPRING_PROFILES_ACTIVE = "postgres"
    $env:APP_LLM_PROVIDER = "mock"
    $env:APP_IDEMPOTENCY_STORE = "redis"
    $env:DB_URL = "jdbc:postgresql://localhost:5432/aichatbot"
    $env:DB_USERNAME = "aichatbot"
    $env:DB_PASSWORD = "local-dev-only-password"
    $env:REDIS_HOST = "localhost"
    $env:REDIS_PORT = "6379"

    return Start-Process cmd.exe -ArgumentList "/c cd /d backend && gradlew.bat bootRun --no-daemon > ..\$logPath 2>&1" -PassThru
}

function Wait-BackendReady {
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
    if (-not $ready) {
        throw "backend_not_ready"
    }
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

function Login-Agent {
    $tenant = "demo-tenant"
    $trace = New-Uuid
    $idem = New-Uuid
    $bodyPath = "tmp/login_body_idem_redis.json"
    '{"login_id":"agent1","password":"agent1-pass","channel_id":"test","client_nonce":"nonce-idem-redis"}' |
        Out-File -FilePath $bodyPath -Encoding utf8

    $resp = cmd /c "curl -sS http://localhost:8080/v1/auth/login -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $trace"" -H ""Idempotency-Key: $idem"" -H ""Content-Type: application/json"" --data-binary @$bodyPath 2>nul"
    $json = $resp | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($json.access_token)) {
        throw "login_failed: $resp"
    }
    return $json.access_token
}

function Create-Session {
    param(
        [string]$token,
        [string]$idempotencyKey
    )
    $tenant = "demo-tenant"
    $trace = New-Uuid
    $bodyPath = "tmp/create_session_idem_redis.json"
    "{}" | Out-File -FilePath $bodyPath -Encoding utf8

    $raw = cmd /c "curl -sS -i http://localhost:8080/v1/sessions -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $trace"" -H ""Idempotency-Key: $idempotencyKey"" -H ""Content-Type: application/json"" --data-binary @$bodyPath 2>nul"
    return $raw
}

docker compose -f infra/docker-compose.yml up -d | Out-Null

$artifactPath = Join-Path $artifactDir "idempotency_redis_e2e.txt"
$backendLog1 = Join-Path $artifactDir "idempotency_redis_backend_run1.txt"
$backendLog2 = Join-Path $artifactDir "idempotency_redis_backend_run2.txt"
$fixedIdempotencyKey = "idem-redis-session-" + (New-Uuid)

$run1 = Start-Backend -logPath $backendLog1
try {
    Wait-BackendReady
    $token1 = Login-Agent
    $first = Create-Session -token $token1 -idempotencyKey $fixedIdempotencyKey
} finally {
    Stop-Backend -proc $run1
}

Start-Sleep -Seconds 2

$run2 = Start-Backend -logPath $backendLog2
try {
    Wait-BackendReady
    $token2 = Login-Agent
    $second = Create-Session -token $token2 -idempotencyKey $fixedIdempotencyKey
} finally {
    Stop-Backend -proc $run2
}

$status1 = "unknown"
if ($first) {
    $m1 = [regex]::Match($first, "HTTP/[0-9.]+\s+([0-9]{3})")
    if ($m1.Success) {
        $status1 = $m1.Groups[1].Value
    }
}

$status2 = "unknown"
if ($second) {
    $m2 = [regex]::Match($second, "HTTP/[0-9.]+\s+([0-9]{3})")
    if ($m2.Success) {
        $status2 = $m2.Groups[1].Value
    }
}
$errorCode2 = ""
if ($second) {
    $m3 = [regex]::Match($second, '"error_code"\s*:\s*"([^"]+)"')
    if ($m3.Success) {
        $errorCode2 = $m3.Groups[1].Value
    }
}

@"
idempotency_store=redis
fixed_idempotency_key=$fixedIdempotencyKey
first_request_status=$status1
second_request_status_after_restart=$status2
second_request_error_code=$errorCode2
expected_second_status=409
expected_second_error_code=API-003-409

--- first_response ---
$first

--- second_response ---
$second
"@ | Out-File -FilePath $artifactPath -Encoding utf8

Write-Output "idempotency redis e2e completed: $artifactPath"
