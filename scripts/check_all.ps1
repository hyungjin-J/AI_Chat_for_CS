$ErrorActionPreference = "Stop"

# Why: check_all은 AGENTS.md 표준 one-command 검증 진입점이다.
Write-Host "[1/13] docker compose up -d"
docker compose -f infra/docker-compose.yml up -d

$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

Write-Host "[2/13] node version policy check"
$nodeVersion = (node -v).Trim()
$nodeMajor = 0
if ($nodeVersion -match "^v([0-9]+)") {
    $nodeMajor = [int]$matches[1]
}
$allowNon22 = $env:APP_VERIFY_ALLOW_NON_22_NODE -eq "true"
$nodePolicy = if ($allowNon22) { "override_allow" } elseif ($env:CI -eq "true") { "ci_fail" } else { "strict_fail" }
@"
node_version=$nodeVersion
node_major=$nodeMajor
expected_major=22
policy=$nodePolicy
override_allow_non22=$allowNon22
"@ | Out-File -FilePath "$artifactDir\node_version_check.txt" -Encoding utf8
if ($nodeMajor -ne 22) {
    if ($allowNon22) {
        Write-Warning "Node major version is not 22. current=$nodeVersion (override enabled)"
    } else {
        throw "node major version must be 22. current=$nodeVersion. use Node 22.12.0 or set APP_VERIFY_ALLOW_NON_22_NODE=true for temporary local override"
    }
}

Write-Host "[3/13] backend test"
cmd /c "cd /d backend && gradlew.bat test --no-daemon > ..\$artifactDir\backend_gradle_test_output.txt 2>&1"
if ($LASTEXITCODE -ne 0) {
    throw "backend tests failed: exit_code=$LASTEXITCODE"
}
Get-Content "$artifactDir\backend_gradle_test_output.txt"

Write-Host "[4/13] frontend build"
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

Write-Host "[5/13] e2e evidence"
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_e2e_evidence.ps1
if ($LASTEXITCODE -ne 0) {
    throw "e2e evidence generation failed: exit_code=$LASTEXITCODE"
}

Write-Host "[6/13] negative tests"
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_negative_tests.ps1
if ($LASTEXITCODE -ne 0) {
    throw "negative tests failed: exit_code=$LASTEXITCODE"
}

Write-Host "[7/13] idempotency redis e2e"
powershell -ExecutionPolicy Bypass -File scripts/run_idempotency_redis_e2e.ps1
if ($LASTEXITCODE -ne 0) {
    throw "idempotency redis e2e failed: exit_code=$LASTEXITCODE"
}

Write-Host "[8/13] sse resume fault injection"
python tests/sse_resume_fault_injection_test.py
if ($LASTEXITCODE -ne 0) {
    throw "sse resume fault injection failed: exit_code=$LASTEXITCODE"
}

Write-Host "[9/13] metrics report"
powershell -ExecutionPolicy Bypass -File scripts/run_metrics_sampling.ps1 -SampleCount 20
if ($LASTEXITCODE -ne 0) {
    throw "metrics report generation failed: exit_code=$LASTEXITCODE"
}

Write-Host "[10/13] sse real concurrency limit proof"
powershell -ExecutionPolicy Bypass -File scripts/run_sse_concurrency_real_limit_test.ps1
if ($LASTEXITCODE -ne 0) {
    throw "sse real concurrency limit proof failed: exit_code=$LASTEXITCODE"
}

Write-Host "[11/13] branch protection check (manual/pass)"
powershell -ExecutionPolicy Bypass -File scripts/check_branch_protection.ps1
if ($LASTEXITCODE -ne 0) {
    throw "branch protection check failed: exit_code=$LASTEXITCODE"
}

Write-Host "[12/13] artifact sanitization scan"
powershell -ExecutionPolicy Bypass -File scripts/scan_artifacts_for_secrets_and_pii.ps1
if ($LASTEXITCODE -ne 0) {
    throw "artifact sanitization scan failed: exit_code=$LASTEXITCODE"
}

Write-Host "[13/13] verification pack consistency"
powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1
if ($LASTEXITCODE -ne 0) {
    throw "verification pack consistency failed: exit_code=$LASTEXITCODE"
}

Write-Host "check_all completed"
