$ErrorActionPreference = "Stop"

$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
New-Item -ItemType Directory -Force -Path "tmp" | Out-Null

$logPath = Join-Path $artifactDir "provider_regression_ollama.log"
$backendLog = Join-Path $artifactDir "provider_regression_backend.log"
$composeFile = "infra/docker-compose.ollama.yml"
$ollamaService = "ollama"
$ollamaContainer = "aichatbot-ollama"
$defaultModel = if ([string]::IsNullOrWhiteSpace($env:APP_OLLAMA_MODEL)) { "qwen2.5:7b-instruct" } else { $env:APP_OLLAMA_MODEL }
$autoPullModel = if ($env:APP_PROVIDER_AUTO_PULL_MODEL -eq "false") { $false } else { $true }
$script:ProviderExitCode = 0

function New-Uuid {
    [guid]::NewGuid().ToString()
}

function Write-Result($status, $reason, $nextStep = "") {
@"
provider=ollama
status=$status
reason=$reason
next_step=$nextStep
generated_at=$(Get-Date -Format "yyyy-MM-dd HH:mm:ssK")
"@ | Out-File -FilePath $logPath -Encoding utf8
}

function Ensure-DockerCompose {
    try {
        $null = docker compose version
        return $true
    } catch {
        Write-Result "SKIPPED" "docker_compose_not_available" "Install Docker Desktop and verify docker compose version"
        $script:ProviderExitCode = 2
        Write-Host "SKIPPED: docker compose not available."
        Write-Host "How to run:"
        Write-Host "1) Install Docker Desktop"
        Write-Host "2) Start Docker Desktop"
        Write-Host "3) Confirm: docker compose version"
        return $false
    }
}

function Ensure-OllamaContainerHealthy {
    try {
        $running = docker inspect -f "{{.State.Running}}" $ollamaContainer 2>$null
        if ($running -ne "true") {
            return $false
        }
        $health = docker inspect -f "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ollamaContainer 2>$null
        if ($health -eq "healthy" -or $health -eq "none") {
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

function Ensure-OllamaReachableAndModel {
    if (-not (Ensure-DockerCompose)) {
        return $false
    }

    if (-not $env:APP_OLLAMA_BASE_URL) {
        $env:APP_OLLAMA_BASE_URL = "http://localhost:11434"
        Write-Host "[provider] APP_OLLAMA_BASE_URL not set. default=http://localhost:11434"
    }

    $ollamaBase = $env:APP_OLLAMA_BASE_URL.TrimEnd("/")

    if (-not (Ensure-OllamaContainerHealthy)) {
        Write-Host "[provider] ollama service not healthy. starting via docker compose..."
        try {
            docker compose -f $composeFile up -d $ollamaService | Out-Null
        } catch {
            Write-Result "SKIPPED" "ollama_compose_start_failed" "docker compose -f $composeFile up -d $ollamaService"
            $script:ProviderExitCode = 2
            Write-Host "SKIPPED: ollama compose start failed"
            Write-Host "How to run:"
            Write-Host "1) docker compose -f $composeFile up -d $ollamaService"
            Write-Host "2) set APP_OLLAMA_BASE_URL=http://localhost:11434"
            Write-Host "3) rerun scripts/run_provider_regression.ps1"
            return $false
        }
    }

    for ($i = 0; $i -lt 60; $i++) {
        try {
            $null = Invoke-RestMethod -Uri "$ollamaBase/api/tags" -Method GET -TimeoutSec 3
            break
        } catch {
            Start-Sleep -Seconds 2
            if ($i -eq 59) {
                Write-Result "SKIPPED" "ollama_not_ready_after_compose" "docker compose -f $composeFile logs $ollamaService"
                $script:ProviderExitCode = 2
                Write-Host "SKIPPED: ollama is not ready."
                Write-Host "How to run:"
                Write-Host "1) docker compose -f $composeFile up -d $ollamaService"
                Write-Host "2) docker compose -f $composeFile logs $ollamaService"
                Write-Host "3) set APP_OLLAMA_BASE_URL=http://localhost:11434"
                Write-Host "4) rerun scripts/run_provider_regression.ps1"
                return $false
            }
        }
    }

    try {
        $tags = Invoke-RestMethod -Uri "$ollamaBase/api/tags" -Method GET -TimeoutSec 5
        $found = $false
        if ($tags.models) {
            foreach ($m in $tags.models) {
                if ($m.name -eq $defaultModel) {
                    $found = $true
                    break
                }
            }
        }
        if (-not $found) {
            if (-not $autoPullModel) {
                Write-Result "SKIPPED" "ollama_model_missing" "docker compose -f $composeFile exec $ollamaService ollama pull $defaultModel"
                $script:ProviderExitCode = 2
                Write-Host "SKIPPED: model missing -> $defaultModel"
                Write-Host "How to run:"
                Write-Host "1) docker compose -f $composeFile exec $ollamaService ollama pull $defaultModel"
                Write-Host "2) set APP_OLLAMA_MODEL=$defaultModel"
                Write-Host "3) rerun scripts/run_provider_regression.ps1"
                return $false
            }
            Write-Host "[provider] model not found. pulling $defaultModel ..."
            docker compose -f $composeFile exec $ollamaService ollama pull $defaultModel | Out-Null
        }
    } catch {
        Write-Result "SKIPPED" "ollama_model_check_failed" "docker compose -f $composeFile exec $ollamaService ollama list"
        $script:ProviderExitCode = 2
        Write-Host "SKIPPED: unable to verify model state."
        Write-Host "How to run:"
        Write-Host "1) docker compose -f $composeFile exec $ollamaService ollama list"
        Write-Host "2) docker compose -f $composeFile exec $ollamaService ollama pull $defaultModel"
        Write-Host "3) rerun scripts/run_provider_regression.ps1"
        return $false
    }

    $env:APP_OLLAMA_MODEL = $defaultModel
    return $true
}

if (-not (Ensure-OllamaReachableAndModel)) {
    exit $script:ProviderExitCode
}

$existing = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if ($existing) {
    foreach ($procId in $existing) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

$env:SPRING_PROFILES_ACTIVE = "postgres"
$env:APP_LLM_PROVIDER = "ollama"
$env:DB_URL = "jdbc:postgresql://localhost:5432/aichatbot"
$env:DB_USERNAME = "aichatbot"
$env:DB_PASSWORD = "local-dev-only-password"
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"

$backendProc = Start-Process cmd.exe -ArgumentList "/c cd /d backend && gradlew.bat bootRun --no-daemon > ..\$backendLog 2>&1" -PassThru

try {
    $ready = $false
    for ($i = 0; $i -lt 120; $i++) {
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

    $tenant = "demo-tenant"
    $loginBodyPath = "tmp/provider_login.json"
    '{"login_id":"agent1","password":"agent1-pass","channel_id":"test","client_nonce":"provider-login"}' |
        Out-File -FilePath $loginBodyPath -Encoding utf8
    $loginResp = cmd /c "curl -sS http://localhost:8080/v1/auth/login -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$loginBodyPath 2>nul"
    $login = $loginResp | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($login.access_token)) { throw "login_failed" }
    $token = $login.access_token

    $sessionBodyPath = "tmp/provider_session.json"
    "{}" | Out-File -FilePath $sessionBodyPath -Encoding utf8
    $sessionResp = cmd /c "curl -sS http://localhost:8080/v1/sessions -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$sessionBodyPath 2>nul"
    $session = $sessionResp | ConvertFrom-Json
    $sessionId = $session.session_id

    $normalBodyPath = "tmp/provider_normal.json"
    '{"text":"refund policy","top_k":3,"client_nonce":"provider-normal"}' |
        Out-File -FilePath $normalBodyPath -Encoding utf8
    $normalResp = cmd /c "curl -sS http://localhost:8080/v1/sessions/$sessionId/messages -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$normalBodyPath 2>nul"
    $normal = $normalResp | ConvertFrom-Json
    $normalId = $normal.id

    $normalSse = cmd /c "curl -sS -N http://localhost:8080/v1/sessions/$sessionId/messages/$normalId/stream -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" 2>nul"
    $normalHasCitation = $normalSse -like "*event:citation*"
    $normalHasDone = $normalSse -like "*event:done*"

    $failBodyPath = "tmp/provider_fail.json"
    '{"text":"zzzzzz qqqqq","top_k":1,"client_nonce":"provider-fail"}' |
        Out-File -FilePath $failBodyPath -Encoding utf8
    $failResp = cmd /c "curl -sS http://localhost:8080/v1/sessions/$sessionId/messages -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" -H ""Idempotency-Key: $(New-Uuid)"" -H ""Content-Type: application/json"" --data-binary @$failBodyPath 2>nul"
    $fail = $failResp | ConvertFrom-Json
    $failId = $fail.id
    $failSse = cmd /c "curl -sS -N http://localhost:8080/v1/sessions/$sessionId/messages/$failId/stream -H ""Authorization: Bearer $token"" -H ""X-Tenant-Key: $tenant"" -H ""X-Trace-Id: $(New-Uuid)"" 2>nul"
    $failHasSafeResponse = $failSse -like "*event:safe_response*"
    $failLeaksToken = ($failSse -like "*event:token*")
    $failHasDone = $failSse -like "*event:done*"

    $status = "FAIL"
    $reason = "provider_regression_failed"
    $nextStep = ""
    if ($failHasSafeResponse -and $failHasDone -and -not $failLeaksToken) {
        if ($normalHasCitation -and $normalHasDone) {
            $status = "PASS"
            $reason = "provider_regression_run"
        } else {
            $status = "SKIPPED"
            $reason = "provider_not_warmed_or_model_output_not_grounded"
            $nextStep = "ollama pull <model>; set APP_OLLAMA_MODEL; rerun"
        }
    }
@"
provider=ollama
status=$status
reason=$reason
next_step=$nextStep
generated_at=$(Get-Date -Format "yyyy-MM-dd HH:mm:ssK")
normal_has_citation=$normalHasCitation
normal_has_done=$normalHasDone
fail_has_safe_response=$failHasSafeResponse
fail_has_done=$failHasDone
fail_leaks_token=$failLeaksToken

[normal_stream]
$normalSse

[fail_stream]
$failSse
"@ | Out-File -FilePath $logPath -Encoding utf8

    if ($status -eq "FAIL") {
        $script:ProviderExitCode = 1
    } elseif ($status -eq "SKIPPED") {
        $script:ProviderExitCode = 2
    } else {
        $script:ProviderExitCode = 0
    }
} catch {
    if (-not (Test-Path $logPath)) {
        Write-Result "FAIL" $_.Exception.Message
    }
    $script:ProviderExitCode = 1
} finally {
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
}

if ($script:ProviderExitCode -eq 0) {
    Write-Host "provider_regression=PASS exit_code=0"
    exit 0
}
if ($script:ProviderExitCode -eq 2) {
    Write-Host "provider_regression=SKIPPED exit_code=2"
    exit 2
}
Write-Host "provider_regression=FAIL exit_code=1"
exit 1
