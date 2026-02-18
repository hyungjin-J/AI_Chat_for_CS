param(
    [int]$SampleCount = 10
)

$ErrorActionPreference = "Stop"

$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
New-Item -ItemType Directory -Force -Path "tmp" | Out-Null

$metricsRawPath = Join-Path $artifactDir "metrics_raw.txt"
$metricsReportPath = Join-Path $artifactDir "metrics_report.md"
$backendLogPath = Join-Path $artifactDir "metrics_backend_output.txt"

function New-Uuid {
    [guid]::NewGuid().ToString()
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
    $env:APP_BUDGET_SESSION_BUDGET_MAX = "999999"
    $env:APP_BUDGET_INPUT_TOKEN_MAX = "5000"
    $env:APP_BUDGET_OUTPUT_TOKEN_MAX = "5000"

    return Start-Process cmd.exe -ArgumentList "/c cd /d backend && gradlew.bat bootRun --no-daemon > ..\$backendLogPath 2>&1" -PassThru
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

function Write-JsonFile($path, $jsonText) {
    $jsonText | Out-File -FilePath $path -Encoding utf8
}

docker compose -f infra/docker-compose.yml up -d | Out-Null

$backendProc = Start-Backend
try {
    Wait-BackendReady

    $tenant = "demo-tenant"
    $loginBody = "tmp/metrics_login.json"
    Write-JsonFile $loginBody '{"login_id":"agent1","password":"agent1-pass","channel_id":"test","client_nonce":"metrics-login"}'
    $loginResp = cmd /c "curl -sS http://localhost:8080/v1/auth/login -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$loginBody 2>nul"
    $login = $loginResp | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($login.access_token)) {
        throw "login_failed"
    }
    $token = $login.access_token

    $sessionBody = "tmp/metrics_session.json"
    Write-JsonFile $sessionBody "{}"
    $sessionResp = cmd /c "curl -sS http://localhost:8080/v1/sessions -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$sessionBody 2>nul"
    $session = $sessionResp | ConvertFrom-Json
    $sessionId = $session.session_id

    for ($i = 1; $i -le $SampleCount; $i++) {
        $normalBody = "tmp/metrics_message_normal_$i.json"
        Write-JsonFile $normalBody (ConvertTo-Json @{text = "refund policy"; top_k = 3; client_nonce = "metrics-normal-$i"} -Compress)
        $normalResp = cmd /c "curl -sS http://localhost:8080/v1/sessions/$sessionId/messages -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$normalBody 2>nul"
        $normal = $normalResp | ConvertFrom-Json
        $normalMessageId = $normal.id
        if ([string]::IsNullOrWhiteSpace($normalMessageId)) {
            throw "metrics_sampling_message_create_failed_${i}: $normalResp"
        }
        $null = cmd /c "curl -sS -N http://localhost:8080/v1/sessions/$sessionId/messages/$normalMessageId/stream -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" 2>nul"
    }

    $failBody = "tmp/metrics_message_fail.json"
    Write-JsonFile $failBody '{"text":"zzzzzz qqqqq","top_k":1,"client_nonce":"metrics-fail"}'
    $failResp = cmd /c "curl -sS http://localhost:8080/v1/sessions/$sessionId/messages -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$failBody 2>nul"
    $fail = $failResp | ConvertFrom-Json
    $failMessageId = $fail.id
    $null = cmd /c "curl -sS -N http://localhost:8080/v1/sessions/$sessionId/messages/$failMessageId/stream -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" 2>nul"

    Start-Sleep -Seconds 1
    $raw = cmd /c "curl -sS http://localhost:8080/actuator/prometheus 2>nul"
    $raw | Out-File -FilePath $metricsRawPath -Encoding utf8

    $p50Ms = "N/A"
    $p95Ms = "N/A"
    $sampleN = 0
    $failClosedRate = "N/A"
    $citationCoverage = "N/A"
    $redisFallbackTotal = "N/A"

    foreach ($line in ($raw -split "`n")) {
        if ($line -match '^sse_first_token_seconds\{.*quantile="0.5".*\}\s+([0-9\.Ee+-]+)$') {
            $p50Ms = ([double]$matches[1] * 1000.0).ToString("F3")
        }
        if ($line -match '^sse_first_token_seconds\{.*quantile="0.95".*\}\s+([0-9\.Ee+-]+)$') {
            $p95Ms = ([double]$matches[1] * 1000.0).ToString("F3")
        }
        if ($line -match '^sse_first_token_seconds_count\s+([0-9\.Ee+-]+)$') {
            $sampleN = [int][double]$matches[1]
        }
        if ($line -match '^fail_closed_rate\s+([0-9\.Ee+-]+)$') {
            $failClosedRate = $matches[1]
        }
        if ($line -match '^citation_coverage\s+([0-9\.Ee+-]+)$') {
            $citationCoverage = $matches[1]
        }
        if ($line -match '^idempotency_redis_fallback_total\s+([0-9\.Ee+-]+)$') {
            $redisFallbackTotal = $matches[1]
        }
    }

    $sampleWarning = ""
    if ($sampleN -lt 30) {
        $sampleWarning = "WARNING: sample size is below 30, interpret p95 carefully."
    } else {
        $sampleWarning = "Sample size is sufficient for basic p95 interpretation."
    }

    $generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ssK"
    $reportLines = @(
        "# Metrics Report",
        "",
        "- generated_at: $generatedAt",
        "- source: /actuator/prometheus",
        "- metric_unit_policy: sse_first_token_seconds exposed in seconds, reported below in ms",
        "",
        "| metric | value |",
        "|---|---|",
        "| sse_first_token_ms_p50 | $p50Ms |",
        "| sse_first_token_ms_p95 | $p95Ms |",
        "| sse_first_token_sample_n | $sampleN |",
        "| fail_closed_rate | $failClosedRate |",
        "| citation_coverage | $citationCoverage |",
        "| idempotency_redis_fallback_total | $redisFallbackTotal |",
        "",
        "## Interpretation",
        "- $sampleWarning",
        "- idempotency_redis_fallback_total > 0 means Redis fallback occurred and distributed idempotency strength may degrade.",
        "",
        "## Notes",
        "- See metrics_raw.txt for raw values.",
        "- Option: powershell -ExecutionPolicy Bypass -File scripts/generate_metrics_report.ps1 -SampleCount 30"
    )

    $reportLines -join "`n" | Out-File -FilePath $metricsReportPath -Encoding utf8
    Write-Output "metrics report generated: $metricsReportPath"
} finally {
    Stop-Backend -proc $backendProc
}
