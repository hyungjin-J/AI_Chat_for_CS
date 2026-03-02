$ErrorActionPreference = "Stop"

# Why: check_all은 AGENTS.md 표준 one-command 검증 진입점이다.
$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

Write-Host "[1/23] node version policy check"
$nodeVersion = (node -v).Trim()
@"
node_version=$nodeVersion
"@ | Out-File -FilePath "$artifactDir\node_version_check.txt" -Encoding utf8
$npmVersion = (npm -v).Trim()
@"
npm_version=$npmVersion
"@ | Out-File -FilePath "$artifactDir\node_runtime_discipline_check.txt" -Encoding utf8
$nodeGateOutput = "$artifactDir\phase2_1_2_node_ssot_check.txt"
python scripts/assert_node_ssot.py `
    --nvmrc .nvmrc `
    --package-json frontend/package.json `
    --check-runtime `
    --output $nodeGateOutput
if ($LASTEXITCODE -ne 0) {
    throw @"
node SSOT assertion failed (fail-fast).
Run bootstrap recovery:
  - Windows: powershell -ExecutionPolicy Bypass -File scripts/bootstrap_node_from_nvmrc.ps1
  - macOS/Linux: bash scripts/bootstrap_node_from_nvmrc.sh
Gate report: $nodeGateOutput
"@
}

Write-Host "[2/25] env contract gate"
python scripts/validate_env_contract.py `
    --env-example .env.example `
    --output-txt "$artifactDir\env_contract_check.txt" `
    --output-json "$artifactDir\env_contract_check.json"
if ($LASTEXITCODE -ne 0) {
    throw "env contract gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[3/25] workpack + specialized agent report contract"
python scripts/assert_workpack_agent_report_contract.py `
    --use-git-diff `
    --output-txt "$artifactDir\workpack_agent_contract_v2.txt" `
    --output-json "$artifactDir\workpack_agent_contract_v2.json"
if ($LASTEXITCODE -ne 0) {
    throw "workpack/agent report contract failed: exit_code=$LASTEXITCODE"
}

Write-Host "[3/23] workpack trigger consistency gate"
python scripts/assert_workpack_trigger_consistency.py `
    --output-txt "$artifactDir\continuation_trigger_consistency_gate.txt" `
    --output-json "$artifactDir\continuation_trigger_consistency_gate.json"
if ($LASTEXITCODE -ne 0) {
    throw "workpack trigger consistency gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[4/24] domain layer purity ratchet gate"
python scripts/assert_domain_layer_boundaries.py `
    --output-txt "$artifactDir\domain_layer_boundary_gate.txt" `
    --output-json "$artifactDir\domain_layer_boundary_gate.json"
if ($LASTEXITCODE -ne 0) {
    throw "domain layer purity gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[5/24] application port boundary ratchet gate"
python scripts/assert_application_port_boundaries.py `
    --output-txt "$artifactDir\application_port_boundary_gate.txt" `
    --output-json "$artifactDir\application_port_boundary_gate.json"
if ($LASTEXITCODE -ne 0) {
    throw "application port boundary gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[6/24] mapper namespace drift gate"
python scripts/verify_mapper_namespaces.py `
    --output-txt "$artifactDir\mapper_namespace_gate.txt" `
    --output-json "$artifactDir\mapper_namespace_gate.json"
if ($LASTEXITCODE -ne 0) {
    throw "mapper namespace gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[7/24] legacy package reintroduction blocker"
python scripts/block_legacy_packages.py `
    --output-txt "$artifactDir\legacy_package_blocker.txt" `
    --output-json "$artifactDir\legacy_package_blocker.json"
if ($LASTEXITCODE -ne 0) {
    throw "legacy package blocker failed: exit_code=$LASTEXITCODE"
}

Write-Host "[8/24] backoffice ACL boundary ratchet gate"
python scripts/assert_backoffice_acl_boundary.py `
    --output-txt "$artifactDir\backoffice_acl_boundary_gate.txt" `
    --output-json "$artifactDir\backoffice_acl_boundary_gate.json"
if ($LASTEXITCODE -ne 0) {
    throw "backoffice ACL boundary gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[9/24] frontend import boundary gate"
python scripts/assert_frontend_import_boundaries.py `
    --output-txt "$artifactDir\frontend_import_boundary_gate.txt" `
    --output-json "$artifactDir\frontend_import_boundary_gate.json"
if ($LASTEXITCODE -ne 0) {
    throw "frontend import boundary gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[10/24] UTF-8 strict decode gate"
python scripts/assert_utf8_strict.py `
    --use-git-diff `
    --output-txt "$artifactDir\continuation_utf8_strict_gate.txt" `
    --output-json "$artifactDir\continuation_utf8_strict_gate.json"
if ($LASTEXITCODE -ne 0) {
    throw "utf-8 strict decode gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[11/24] scaffold contract smoke gate"
python scripts/assert_scaffold_contract_smoke.py `
    --output-txt "$artifactDir\scaffold_contract_smoke.txt" `
    --output-json "$artifactDir\scaffold_contract_smoke.json"
if ($LASTEXITCODE -ne 0) {
    throw "scaffold contract smoke gate failed: exit_code=$LASTEXITCODE"
}

Write-Host "[12/24] docker compose up -d"
docker compose -f infra/docker-compose.yml up -d

Write-Host "[13/24] backend test"
cmd /c "cd /d backend && gradlew.bat test --no-daemon > ..\$artifactDir\backend_gradle_test_output.txt 2>&1"
if ($LASTEXITCODE -ne 0) {
    throw "backend tests failed: exit_code=$LASTEXITCODE"
}
Get-Content "$artifactDir\backend_gradle_test_output.txt"

Write-Host "[14/24] frontend build"
cmd /c "cd /d frontend && npm ci --prefer-offline --no-audit --fund=false > ..\$artifactDir\frontend_npm_ci_output.txt 2>&1"
if ($LASTEXITCODE -ne 0) {
    throw "frontend npm ci failed: exit_code=$LASTEXITCODE"
}
Get-Content "$artifactDir\frontend_npm_ci_output.txt"

cmd /c "cd /d frontend && npm run build > ..\$artifactDir\frontend_build_output.txt 2>&1"
if ($LASTEXITCODE -ne 0) {
    throw "frontend build failed: exit_code=$LASTEXITCODE"
}
Get-Content "$artifactDir\frontend_build_output.txt"

Write-Host "[15/24] e2e evidence"
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_e2e_evidence.ps1
if ($LASTEXITCODE -ne 0) {
    throw "e2e evidence generation failed: exit_code=$LASTEXITCODE"
}

Write-Host "[16/24] negative tests"
powershell -ExecutionPolicy Bypass -File scripts/run_mvp_negative_tests.ps1
if ($LASTEXITCODE -ne 0) {
    throw "negative tests failed: exit_code=$LASTEXITCODE"
}

Write-Host "[17/24] idempotency redis e2e"
powershell -ExecutionPolicy Bypass -File scripts/run_idempotency_redis_e2e.ps1
if ($LASTEXITCODE -ne 0) {
    throw "idempotency redis e2e failed: exit_code=$LASTEXITCODE"
}

Write-Host "[18/24] sse resume fault injection"
python tests/sse_resume_fault_injection_test.py
if ($LASTEXITCODE -ne 0) {
    throw "sse resume fault injection failed: exit_code=$LASTEXITCODE"
}

Write-Host "[19/24] metrics report"
powershell -ExecutionPolicy Bypass -File scripts/run_metrics_sampling.ps1 -SampleCount 20
if ($LASTEXITCODE -ne 0) {
    throw "metrics report generation failed: exit_code=$LASTEXITCODE"
}

Write-Host "[20/24] sse real concurrency limit proof"
powershell -ExecutionPolicy Bypass -File scripts/run_sse_concurrency_real_limit_test.ps1
if ($LASTEXITCODE -ne 0) {
    throw "sse real concurrency limit proof failed: exit_code=$LASTEXITCODE"
}

Write-Host "[21/24] branch protection check (manual/pass)"
powershell -ExecutionPolicy Bypass -File scripts/check_branch_protection.ps1
if ($LASTEXITCODE -ne 0) {
    throw "branch protection check failed: exit_code=$LASTEXITCODE"
}

Write-Host "[22/24] artifact sanitization scan"
powershell -ExecutionPolicy Bypass -File scripts/scan_artifacts_for_secrets_and_pii.ps1
if ($LASTEXITCODE -ne 0) {
    throw "artifact sanitization scan failed: exit_code=$LASTEXITCODE"
}

Write-Host "[23/24] verification pack consistency"
powershell -ExecutionPolicy Bypass -File scripts/assert_verification_pack_consistency.ps1
if ($LASTEXITCODE -ne 0) {
    throw "verification pack consistency failed: exit_code=$LASTEXITCODE"
}

Write-Host "[24/24] provider evidence consistency"
powershell -ExecutionPolicy Bypass -File scripts/assert_provider_regression_evidence.ps1
if ($LASTEXITCODE -ne 0) {
    throw "provider evidence consistency failed: exit_code=$LASTEXITCODE"
}

Write-Host "check_all completed"
