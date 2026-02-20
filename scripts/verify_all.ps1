$ErrorActionPreference = "Stop"

# Why: 기존 진입점(verify_all)을 유지해 기존 CI/개발 스크립트와의 호환성을 보장한다.
Write-Host "[compat] verify_all.ps1 delegates to scripts/check_all.ps1"
powershell -ExecutionPolicy Bypass -File "$PSScriptRoot/check_all.ps1"
exit $LASTEXITCODE
