param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$TenantKey = "demo-tenant",
    [string]$LoginId = "agent1",
    [string]$Password = "agent1-pass",
    [string]$K6Bin = "k6",
    [string]$SseVus = "2",
    [string]$SseDuration = "45s",
    [string]$RateLimitStartTime = "45s",
    [string]$RateLimitIterations = "6",
    [switch]$RequireDocker,
    [switch]$BootstrapCompose,
    [string]$ComposeFile = "infra/docker-compose.yml",
    [switch]$SkipFlyway,
    [string]$BackendSseConcurrencyMaxPerUser = "2",
    [string]$BackendSseHoldMs = "2500"
)

$ErrorActionPreference = "Stop"

$resultDir = "perf/out"
$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Path $resultDir -Force | Out-Null
New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null

$dateTag = Get-Date -Format "yyyyMMdd"
$resultJson = Join-Path $resultDir "result.json"
$gateJson = Join-Path $artifactDir "perf_sse_gate_$dateTag.json"
$gateTxt = Join-Path $artifactDir "perf_sse_gate_$dateTag.txt"

$args = @(
    "scripts/run_perf_sse_gate.py",
    "--base-url", $BaseUrl,
    "--tenant-key", $TenantKey,
    "--login-id", $LoginId,
    "--password", $Password,
    "--k6-bin", $K6Bin,
    "--sse-vus", $SseVus,
    "--sse-duration", $SseDuration,
    "--rate-limit-start-time", $RateLimitStartTime,
    "--rate-limit-iterations", $RateLimitIterations,
    "--backend-sse-concurrency-max-per-user", $BackendSseConcurrencyMaxPerUser,
    "--backend-sse-hold-ms", $BackendSseHoldMs,
    "--result-json", $resultJson,
    "--thresholds", "perf/thresholds.yaml",
    "--gate-json", $gateJson,
    "--gate-txt", $gateTxt
)
if ($RequireDocker) {
    $args += "--require-docker"
}
if ($BootstrapCompose) {
    $args += "--bootstrap-compose"
    $args += "--compose-file"
    $args += $ComposeFile
}
if ($SkipFlyway) {
    $args += "--skip-flyway"
}

python @args
$exitCode = $LASTEXITCODE

Write-Host "perf_sse_gate_exit_code=$exitCode"
Write-Host "result_json=$resultJson"
Write-Host "gate_txt=$gateTxt"
Write-Host "gate_json=$gateJson"
exit $exitCode
