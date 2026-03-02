
param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$TenantKey = "demo-tenant",
    [string]$Role = "AGENT",
    [string]$CrossTenantKey = "tenant-a",
    [string]$ComposeFile = "infra/compose/production/docker-compose.prod.yml",
    [string]$ArtifactDir = "docs/review/mvp_verification_pack/artifacts",
    [switch]$SkipDbCheck,
    [switch]$SkipLogCheck,
    [switch]$NoIsolationPass
)

$ErrorActionPreference = "Stop"


function Set-EnvDefault {
    param(
        [string]$Name,
        [string]$Value
    )
    if ([string]::IsNullOrWhiteSpace((Get-Item -Path ("Env:" + $Name) -ErrorAction SilentlyContinue).Value)) {
        Set-Item -Path ("Env:" + $Name) -Value $Value
    }
}

function Stop-BackendOn8080 {
    param($Proc)
    if ($Proc -and -not $Proc.HasExited) {
        Stop-Process -Id $Proc.Id -Force -ErrorAction SilentlyContinue
    }
    $existing = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    if ($existing) {
        foreach ($procId in $existing) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Wait-BackendReady {
    param(
        [string]$Url,
        [string]$Tenant
    )
    for ($i = 0; $i -lt 120; $i++) {
        try {
            Invoke-RestMethod -Uri ($Url.TrimEnd("/") + "/health") -Method GET `
                -Headers @{"X-Tenant-Key" = $Tenant; "X-Trace-Id" = [guid]::NewGuid().ToString()} `
                -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    throw "backend_not_ready"
}

function Assert-DockerReady {
    cmd /c "docker info >nul 2>nul" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "docker_engine_not_running"
    }
}

New-Item -ItemType Directory -Force -Path $ArtifactDir | Out-Null
New-Item -ItemType Directory -Force -Path "tmp" | Out-Null

$dateTag = Get-Date -Format "yyyyMMdd"
$reportPath = Join-Path $ArtifactDir ("e2e_smoke_report_" + $dateTag + ".json")
$tracePath = Join-Path $ArtifactDir ("e2e_smoke_trace_samples_" + $dateTag + ".txt")
$runtimeLog = Join-Path $ArtifactDir "backend_runtime_e2e_output.txt"
$isolationReportPath = Join-Path $ArtifactDir ("e2e_smoke_report_isolation_" + $dateTag + ".json")
$isolationTracePath = Join-Path $ArtifactDir ("e2e_smoke_trace_samples_isolation_" + $dateTag + ".txt")

Set-EnvDefault -Name "POSTGRES_DB" -Value "aichatbot"
Set-EnvDefault -Name "POSTGRES_USER" -Value "aichatbot"
Set-EnvDefault -Name "POSTGRES_PASSWORD" -Value "local-dev-only-password"
Set-EnvDefault -Name "DB_URL" -Value ("jdbc:postgresql://localhost:5432/" + $env:POSTGRES_DB)
Set-EnvDefault -Name "DB_USERNAME" -Value $env:POSTGRES_USER
Set-EnvDefault -Name "DB_PASSWORD" -Value $env:POSTGRES_PASSWORD
Set-EnvDefault -Name "APP_JWT_SECRET" -Value "change-me-in-prod-change-me-in-prod-change-me-in-prod"
Set-EnvDefault -Name "APP_JWT_SECRET_REF" -Value "secret_ref://jwt/demo"
Set-EnvDefault -Name "LLM_PROVIDER_KEY_REF" -Value "secret_ref://llm/demo"

Write-Host "[e2e] starting infra services from $ComposeFile"
Assert-DockerReady
docker compose -f $ComposeFile up -d postgres redis | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "compose_up_failed"
}

Stop-BackendOn8080

$env:SPRING_PROFILES_ACTIVE = "postgres,e2e"
$env:APP_LLM_PROVIDER = "mock"
$env:DB_URL = "jdbc:postgresql://localhost:5432/$($env:POSTGRES_DB)"
$env:DB_USERNAME = $env:POSTGRES_USER
$env:DB_PASSWORD = $env:POSTGRES_PASSWORD
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"
$env:APP_IDEMPOTENCY_STORE = "redis"
$env:APP_E2E_FORCE_FAIL_CLOSED_ENABLED = "true"
$env:APP_E2E_FORCE_FAIL_CLOSED_TRIGGER = "__E2E_FORCE_FAIL_CLOSED__"
$env:APP_E2E_FORCE_FAIL_CLOSED_ERROR_CODE = "AI-009-409-EVIDENCE"

if (Test-Path $runtimeLog) {
    Remove-Item -Path $runtimeLog -Force
}

$backendProc = Start-Process cmd.exe `
    -ArgumentList "/c cd /d backend && gradlew.bat bootRun --no-daemon > ..\$runtimeLog 2>&1" `
    -PassThru

try {
    Write-Host "[e2e] waiting backend readiness"
    Wait-BackendReady -Url $BaseUrl -Tenant $TenantKey

    $argsMain = @(
        "e2e/api_smoke/run_e2e_smoke.py",
        "--base-url", $BaseUrl,
        "--tenant-key", $TenantKey,
        "--role", $Role,
        "--cross-tenant-key", $CrossTenantKey,
        "--compose-file", $ComposeFile,
        "--compose-service", "postgres",
        "--db-method", "docker-exec",
        "--db-name", $env:POSTGRES_DB,
        "--db-user", $env:POSTGRES_USER,
        "--db-password", $env:POSTGRES_PASSWORD,
        "--backend-log-file", $runtimeLog,
        "--output-report-json", $reportPath,
        "--output-trace-txt", $tracePath
    )
    if ($SkipDbCheck) {
        $argsMain += "--skip-db-check"
    }
    if ($SkipLogCheck) {
        $argsMain += "--skip-log-check"
    }

    Write-Host "[e2e] running primary smoke"
    python @argsMain
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if (-not $NoIsolationPass) {
        $argsIsolation = @(
            "e2e/api_smoke/run_e2e_smoke.py",
            "--base-url", $BaseUrl,
            "--tenant-key", $CrossTenantKey,
            "--auth-tenant-key", $TenantKey,
            "--role", $Role,
            "--cross-tenant-key", $CrossTenantKey,
            "--compose-file", $ComposeFile,
            "--compose-service", "postgres",
            "--db-method", "docker-exec",
            "--db-name", $env:POSTGRES_DB,
            "--db-user", $env:POSTGRES_USER,
            "--db-password", $env:POSTGRES_PASSWORD,
            "--backend-log-file", $runtimeLog,
            "--output-report-json", $isolationReportPath,
            "--output-trace-txt", $isolationTracePath
        )
        if ($SkipDbCheck) {
            $argsIsolation += "--skip-db-check"
        }
        if ($SkipLogCheck) {
            $argsIsolation += "--skip-log-check"
        }

        Write-Host "[e2e] running isolation-focused pass"
        python @argsIsolation
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    Write-Host "[e2e] done"
    Write-Host "report: $reportPath"
    Write-Host "trace:  $tracePath"
} finally {
    Stop-BackendOn8080 -Proc $backendProc
}
