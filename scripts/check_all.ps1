$ErrorActionPreference = "Stop"

# Why: check_all은 AGENTS.md 표준 one-command 검증 진입점이다.
$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

Write-Host "[1/14] node version policy check"
$nodeVersion = (node -v).Trim()
@"
node_version=$nodeVersion
"@ | Out-File -FilePath "$artifactDir\node_version_check.txt" -Encoding utf8
python scripts/check_node_version.py `
    --nvmrc .nvmrc `
    --package-json frontend/package.json `
    --check-runtime `
    --output "$artifactDir\phase2_1_1_prA_node_ssot_check.txt"
if ($LASTEXITCODE -ne 0) {
    throw "node SSOT assertion failed. See $artifactDir\phase2_1_1_prA_node_ssot_check.txt"
}

Write-Host "[2/14] docker compose up -d"
docker compose -f infra/docker-compose.yml up -d

Write-Host "[3/14] backend test"
cmd /c "cd /d backend && gradlew.bat test --no-daemon > ..\$artifactDir\backend_gradle_test_output.txt 2>&1"
if ($LASTEXITCODE -ne 0) {
    throw "backend tests failed: exit_code=$LASTEXITCODE"
}
Get-Content "$artifactDir\backend_gradle_test_output.txt"

Write-Host "[4/14] frontend build"
cmd /c "cd /d frontend && npm ci > ..\$artifactDir\frontend_npm_ci_output.txt 2>&1"
if ($LASTEXITCODE -ne 0) {
    throw "frontend npm ci failed: exit_code=$LASTEXITCODE"
}
Get-Content "$artifactDir\frontend_npm_ci_output.txt"

cmd /c "cd /d frontend && npm run build > ..\$artifactDir\frontend_build_output.txt 2>&1"
if ($LASTEXITCODE -ne 0) {
    throw "frontend build failed: exit_code=$LASTEXITCODE"
}
Get-Content "$artifactDir\frontend_build_output.txt"

Write-Host "[5/14] e2e evidence"
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_e2e_evidence.ps1
if ($LASTEXITCODE -ne 0) {
    throw "e2e evidence generation failed: exit_code=$LASTEXITCODE"
}

Write-Host "[6/14] negative tests"
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_negative_tests.ps1
if ($LASTEXITCODE -ne 0) {
    throw "negative tests failed: exit_code=$LASTEXITCODE"
}

Write-Host "[7/14] idempotency redis e2e"
powershell -ExecutionPolicy Bypass -File scripts/run_idempotency_redis_e2e.ps1
if ($LASTEXITCODE -ne 0) {
    throw "idempotency redis e2e failed: exit_code=$LASTEXITCODE"
}

Write-Host "[8/14] sse resume fault injection"
python tests/sse_resume_fault_injection_test.py
if ($LASTEXITCODE -ne 0) {
    throw "sse resume fault injection failed: exit_code=$LASTEXITCODE"
}

Write-Host "[9/14] metrics report"
powershell -ExecutionPolicy Bypass -File scripts/run_metrics_sampling.ps1 -SampleCount 20
if ($LASTEXITCODE -ne 0) {
    throw "metrics report generation failed: exit_code=$LASTEXITCODE"
}

Write-Host "[10/14] sse real concurrency limit proof"
powershell -ExecutionPolicy Bypass -File scripts/run_sse_concurrency_real_limit_test.ps1
if ($LASTEXITCODE -ne 0) {
    throw "sse real concurrency limit proof failed: exit_code=$LASTEXITCODE"
}

Write-Host "[11/14] branch protection check (manual/pass)"
powershell -ExecutionPolicy Bypass -File scripts/check_branch_protection.ps1
if ($LASTEXITCODE -ne 0) {
    throw "branch protection check failed: exit_code=$LASTEXITCODE"
}

Write-Host "[12/14] artifact sanitization scan"
powershell -ExecutionPolicy Bypass -File scripts/scan_artifacts_for_secrets_and_pii.ps1
if ($LASTEXITCODE -ne 0) {
    throw "artifact sanitization scan failed: exit_code=$LASTEXITCODE"
}

Write-Host "[13/14] verification pack consistency"
powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1
if ($LASTEXITCODE -ne 0) {
    throw "verification pack consistency failed: exit_code=$LASTEXITCODE"
}

Write-Host "[14/14] provider evidence consistency"
powershell -ExecutionPolicy Bypass -File scripts/assert_provider_regression_evidence.ps1
if ($LASTEXITCODE -ne 0) {
    throw "provider evidence consistency failed: exit_code=$LASTEXITCODE"
}

Write-Host "check_all completed"
