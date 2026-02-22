param(
    [int]$MaxAttempts = 3,
    [string]$FrontendDir = "frontend"
)

$ErrorActionPreference = "Stop"

if ($MaxAttempts -lt 1) {
    throw "MaxAttempts must be >= 1"
}

if (-not (Test-Path -Path $FrontendDir)) {
    throw "frontend directory not found: $FrontendDir"
}

$cmd = "npm ci --prefer-offline --no-audit --fund=false"

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    Write-Host "[attempt $attempt/$MaxAttempts] $cmd"
    cmd /c "cd /d $FrontendDir && $cmd"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] frontend install completed."
        exit 0
    }

    Write-Warning "[WARN] npm ci failed on attempt $attempt (exit_code=$LASTEXITCODE)."
    if ($attempt -lt $MaxAttempts) {
        Write-Host "[ACTION] Retrying after short delay..."
        Start-Sleep -Seconds 2
    }
}

Write-Error "[FAIL] npm ci failed after $MaxAttempts attempts."
Write-Host "Recommended next actions:"
Write-Host "1) powershell -ExecutionPolicy Bypass -File scripts/bootstrap_node_from_nvmrc.ps1"
Write-Host "2) Remove frontend\\node_modules and rerun install."
Write-Host "3) npm cache verify"
Write-Host "4) Follow docs/ops/runbook_windows_node_npm_lock.md"
exit 1
