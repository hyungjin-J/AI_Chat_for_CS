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

function Start-Backend {
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
    $env:DB_URL = "jdbc:postgresql://localhost:5432/aichatbot"
    $env:DB_USERNAME = "aichatbot"
    $env:DB_PASSWORD = "local-dev-only-password"
    $env:APP_BUDGET_SESSION_BUDGET_MAX = "10000"
    $env:APP_BUDGET_INPUT_TOKEN_MAX = "50"
    $env:APP_BUDGET_SSE_CONCURRENCY_MAX_PER_USER = "0"

    $runtimeLog = Join-Path $artifactDir "backend_runtime_negative_output.txt"
    return Start-Process cmd.exe -ArgumentList "/c cd /d backend && gradlew.bat bootRun --no-daemon > ..\$runtimeLog 2>&1" -PassThru
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

function Mask-TokenJson {
    param([string]$rawJson)
    if ([string]::IsNullOrWhiteSpace($rawJson)) {
        return $rawJson
    }
    try {
        $obj = $rawJson | ConvertFrom-Json
        if ($obj.PSObject.Properties.Name -contains "access_token") {
            $obj.access_token = "***"
        }
        if ($obj.PSObject.Properties.Name -contains "refresh_token") {
            $obj.refresh_token = "***"
        }
        return ($obj | ConvertTo-Json -Compress -Depth 20)
    } catch {
        return $rawJson
    }
}

function Status-FromRawResponse {
    param([string]$raw)
    $match = [regex]::Match($raw, "HTTP/[0-9.]+\s+([0-9]{3})")
    if ($match.Success) {
        return $match.Groups[1].Value
    }
    return "unknown"
}

function ErrorCode-FromRawResponse {
    param([string]$raw)
    $match = [regex]::Match($raw, '"error_code"\s*:\s*"([^"]+)"')
    if ($match.Success) {
        return $match.Groups[1].Value
    }
    return ""
}

docker compose -f infra/docker-compose.yml up -d | Out-Null

$backendProc = Start-Backend
try {
    Wait-BackendReady

    $tenant = "demo-tenant"

    $loginAgentPath = "tmp/neg_login_agent.json"
    Write-JsonFile $loginAgentPath '{"login_id":"agent1","password":"agent1-pass","channel_id":"test","client_nonce":"neg-agent"}'
    $agentLoginRaw = cmd /c "curl -sS http://localhost:8080/v1/auth/login -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$loginAgentPath 2>nul"
    $agentLogin = $agentLoginRaw | ConvertFrom-Json
    $agentToken = $agentLogin.access_token
    if ([string]::IsNullOrWhiteSpace($agentToken)) {
        throw "agent_login_failed"
    }

    $loginAdminPath = "tmp/neg_login_admin.json"
    Write-JsonFile $loginAdminPath '{"login_id":"admin1","password":"admin1-pass","channel_id":"test","client_nonce":"neg-admin"}'
    $adminLoginRaw = cmd /c "curl -sS http://localhost:8080/v1/auth/login -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$loginAdminPath 2>nul"
    $adminLogin = $adminLoginRaw | ConvertFrom-Json
    $adminToken = $adminLogin.access_token
    if ([string]::IsNullOrWhiteSpace($adminToken)) {
        throw "admin_login_failed"
    }

    # E2E-AUTH-401
    $auth401Raw = cmd /c "curl -sS -i http://localhost:8080/v1/chat/bootstrap -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" 2>nul"

    # E2E-AUTH-403 (AGENT role requesting ADMIN endpoint)
    $auth403Raw = cmd /c "curl -sS -i http://localhost:8080/v1/admin/tenants/00000000-0000-0000-0000-000000000001/usage-report -H ""Authorization: Bearer $agentToken"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" 2>nul"

    # NEG-422-IDEM (missing Idempotency-Key)
    $sessionBodyPath = "tmp/neg_session_body.json"
    Write-JsonFile $sessionBodyPath "{}"
    $idem422Raw = cmd /c "curl -sS -i http://localhost:8080/v1/sessions -H ""Authorization: Bearer $agentToken"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$sessionBodyPath 2>nul"

    # Idempotency duplicate 409 proof
    $dupKey = "idem-dup-" + (New-Uuid)
    $idemFirstRaw = cmd /c "curl -sS -i http://localhost:8080/v1/sessions -H ""Authorization: Bearer $agentToken"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $dupKey"" -H ""Content-Type: application/json"" --data-binary @$sessionBodyPath 2>nul"
    $idemSecondRaw = cmd /c "curl -sS -i http://localhost:8080/v1/sessions -H ""Authorization: Bearer $agentToken"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $dupKey"" -H ""Content-Type: application/json"" --data-binary @$sessionBodyPath 2>nul"

    # Session for budget / sse checks
    $workSessionRaw = cmd /c "curl -sS http://localhost:8080/v1/sessions -H ""Authorization: Bearer $agentToken"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$sessionBodyPath 2>nul"
    $workSession = $workSessionRaw | ConvertFrom-Json
    $workSessionId = $workSession.session_id
    if ([string]::IsNullOrWhiteSpace($workSessionId)) {
        throw "work_session_failed"
    }

    # NEG-BUDGET-001
    $budgetBodyPath = "tmp/neg_budget_body.json"
    $longText = "refund policy " + ("A" * 1600)
    Write-JsonFile $budgetBodyPath (ConvertTo-Json @{text=$longText; top_k=3; client_nonce="neg-budget"} -Compress)
    $budget429Raw = cmd /c "curl -sS -i http://localhost:8080/v1/sessions/$workSessionId/messages -H ""Authorization: Bearer $agentToken"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$budgetBodyPath 2>nul"

    # Prepare one message for SSE concurrency check
    $sseBodyPath = "tmp/neg_sse_body.json"
    Write-JsonFile $sseBodyPath '{"text":"refund policy","top_k":3,"client_nonce":"neg-sse"}'
    $sseMsgRaw = cmd /c "curl -sS http://localhost:8080/v1/sessions/$workSessionId/messages -H ""Authorization: Bearer $agentToken"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$sseBodyPath 2>nul"
    $sseMsg = $sseMsgRaw | ConvertFrom-Json
    $sseMessageId = $sseMsg.id
    if ([string]::IsNullOrWhiteSpace($sseMessageId)) {
        throw "sse_message_failed"
    }

    # SSE-CONC-429 (deterministic by forcing max=0)
    $sse429Raw = cmd /c "curl -sS -i http://localhost:8080/v1/sessions/$workSessionId/messages/$sseMessageId/stream -H ""Authorization: Bearer $agentToken"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" 2>nul"

    @"
401_status=$(Status-FromRawResponse $auth401Raw)
401_error_code=$(ErrorCode-FromRawResponse $auth401Raw)
401_raw=$auth401Raw

403_status=$(Status-FromRawResponse $auth403Raw)
403_error_code=$(ErrorCode-FromRawResponse $auth403Raw)
403_raw=$auth403Raw

agent_login_masked=$(Mask-TokenJson $agentLoginRaw)
admin_login_masked=$(Mask-TokenJson $adminLoginRaw)
"@ | Out-File -FilePath (Join-Path $artifactDir "rbac_401_403_checks.txt") -Encoding utf8

    @"
status=$(Status-FromRawResponse $budget429Raw)
error_code=$(ErrorCode-FromRawResponse $budget429Raw)
raw=$budget429Raw
"@ | Out-File -FilePath (Join-Path $artifactDir "budget_429_checks.txt") -Encoding utf8

    @"
status=$(Status-FromRawResponse $sse429Raw)
error_code=$(ErrorCode-FromRawResponse $sse429Raw)
policy_note=forced APP_BUDGET_SSE_CONCURRENCY_MAX_PER_USER=0 for deterministic 429 proof
raw=$sse429Raw
"@ | Out-File -FilePath (Join-Path $artifactDir "sse_concurrency_attempts.txt") -Encoding utf8

    @"
status=$(Status-FromRawResponse $idem422Raw)
error_code=$(ErrorCode-FromRawResponse $idem422Raw)
raw=$idem422Raw
"@ | Out-File -FilePath (Join-Path $artifactDir "idempotency_negative_422.txt") -Encoding utf8

    @"
first_status=$(Status-FromRawResponse $idemFirstRaw)
first_error_code=$(ErrorCode-FromRawResponse $idemFirstRaw)
second_status=$(Status-FromRawResponse $idemSecondRaw)
second_error_code=$(ErrorCode-FromRawResponse $idemSecondRaw)
first_raw=$idemFirstRaw
second_raw=$idemSecondRaw
"@ | Out-File -FilePath (Join-Path $artifactDir "idempotency_409_proof.txt") -Encoding utf8

    Write-Output "negative tests completed"
} finally {
    Stop-Backend -proc $backendProc
}
