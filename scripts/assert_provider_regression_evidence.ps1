$ErrorActionPreference = "Stop"

$resultsPath = "docs/review/mvp_verification_pack/04_TEST_RESULTS.md"
$evidencePath = "docs/review/final/PROVIDER_REGRESSION_EVIDENCE.md"
$defaultMaxAgeDays = 30
$maxAgeDays = if ($env:APP_PROVIDER_PASS_MAX_AGE_DAYS) { [int]$env:APP_PROVIDER_PASS_MAX_AGE_DAYS } else { $defaultMaxAgeDays }

if (-not (Test-Path $resultsPath)) {
    throw "missing results file: $resultsPath"
}
if (-not (Test-Path $evidencePath)) {
    throw "missing provider evidence file: $evidencePath"
}

$resultsContent = Get-Content $resultsPath -Raw -Encoding utf8
$providerRow = ($resultsContent -split "`n" | Where-Object { $_ -match '^\|\s*LLM-PROVIDER-001\s*\|' } | Select-Object -First 1)
if (-not $providerRow) {
    throw "cannot find LLM-PROVIDER-001 row in $resultsPath"
}

$statusCell = ($providerRow.Trim('|').Split('|') | ForEach-Object { $_.Trim() })[1]
$status = $statusCell.ToUpperInvariant()

if ($status -notmatch "SKIPPED") {
    Write-Host "provider_regression_evidence=PASS (latest result is not SKIPPED)"
    exit 0
}

$evidenceContent = Get-Content $evidencePath -Raw -Encoding utf8

function Read-EvidenceValue([string]$key) {
    $pattern = "(?im)^\s*[-*]?\s*${key}\s*:\s*(.+?)\s*$"
    $match = [regex]::Match($evidenceContent, $pattern)
    if (-not $match.Success) {
        throw "missing key in provider evidence: $key"
    }
    return $match.Groups[1].Value.Trim()
}

$latestPassUtc = Read-EvidenceValue "latest_pass_utc"
$latestPassCommit = Read-EvidenceValue "latest_pass_commit"
$latestPassArtifact = Read-EvidenceValue "latest_pass_artifact"

$artifactPath = $latestPassArtifact.Trim('`')
if (-not (Test-Path $artifactPath)) {
    throw "latest pass artifact missing: $artifactPath"
}

$artifactContent = Get-Content $artifactPath -Raw -Encoding utf8
if ($artifactContent -notmatch "(?im)^status=PASS\s*$") {
    throw "latest pass artifact does not confirm PASS: $artifactPath"
}

if ($latestPassCommit -notmatch '^[0-9a-f]{7,40}$') {
    throw "invalid latest_pass_commit format: $latestPassCommit"
}

$passInstant = [DateTimeOffset]::Parse($latestPassUtc)
$ageDays = ([DateTimeOffset]::UtcNow - $passInstant).TotalDays
if ($ageDays -gt $maxAgeDays) {
    throw "latest PASS evidence is too old ($([math]::Round($ageDays, 1)) days > $maxAgeDays days)"
}

Write-Host "provider_regression_evidence=PASS"
Write-Host "latest_result_status=SKIPPED"
Write-Host "latest_pass_utc=$latestPassUtc"
Write-Host "latest_pass_commit=$latestPassCommit"
Write-Host "latest_pass_artifact=$artifactPath"
