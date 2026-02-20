$ErrorActionPreference = "Stop"

$packDir = "docs/review/mvp_verification_pack"
$artifactDir = Join-Path $packDir "artifacts"
$resultsPath = Join-Path $packDir "04_TEST_RESULTS.md"
$planPath = Join-Path $packDir "03_TEST_PLAN.md"
$summaryPath = Join-Path $packDir "00_EXEC_SUMMARY.md"
$artifactSummaryPath = Join-Path $packDir "06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md"
$changelogPath = Join-Path $packDir "CHANGELOG.md"

if (-not (Test-Path $resultsPath)) { throw "missing 04_TEST_RESULTS.md" }
if (-not (Test-Path $planPath)) { throw "missing 03_TEST_PLAN.md" }
if (-not (Test-Path $summaryPath)) { throw "missing 00_EXEC_SUMMARY.md" }
if (-not (Test-Path $artifactSummaryPath)) { throw "missing 06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md" }
if (-not (Test-Path $changelogPath)) { throw "missing CHANGELOG.md" }

function Parse-StatusMap([string]$content) {
    $map = @{}
    foreach ($line in ($content -split "`n")) {
        $trim = $line.Trim()
        if (-not $trim.StartsWith("|")) { continue }
        if ($trim -like "|---*") { continue }
        $cols = $trim.Trim("|").Split("|") | ForEach-Object { $_.Trim() }
        if ($cols.Count -lt 2) { continue }
        $testId = $cols[0]
        if ($testId -notmatch '^[A-Z0-9-]+$') { continue }
        $statusRaw = $cols[1].ToUpperInvariant()
        if ($statusRaw.Contains("PASS") -or $statusRaw.Contains("통과")) {
            $map[$testId] = "PASS"
        } elseif ($statusRaw.Contains("FAIL") -or $statusRaw.Contains("실패")) {
            $map[$testId] = "FAIL"
        } elseif ($statusRaw.Contains("SKIPPED") -or $statusRaw.Contains("건너")) {
            $map[$testId] = "SKIPPED"
        }
    }
    return $map
}

function Parse-ReferencedArtifacts([string]$content) {
    $refs = @()
    foreach ($m in [regex]::Matches($content, '`artifacts/([^`]+)`')) {
        $refs += $m.Groups[1].Value
    }
    return $refs
}

function Parse-TestIdsFromPlan([string]$content) {
    $ids = New-Object System.Collections.Generic.HashSet[string]
    foreach ($line in ($content -split "`n")) {
        $trim = $line.Trim()
        if (-not $trim.StartsWith("|")) { continue }
        if ($trim -like "|---*") { continue }
        $cols = $trim.Trim("|").Split("|") | ForEach-Object { $_.Trim() }
        if ($cols.Count -lt 1) { continue }
        $testId = $cols[0]
        if ($testId -match '^[A-Z0-9-]+$') {
            $null = $ids.Add($testId)
        }
    }
    return $ids
}

$resultsContent = Get-Content $resultsPath -Raw -Encoding utf8
$resultsStatus = Parse-StatusMap $resultsContent
if ($resultsStatus.Count -eq 0) {
    throw "cannot parse test status map from 04_TEST_RESULTS.md"
}

# 1) PASS in 04 must have all artifact files present
$resultLines = $resultsContent -split "`n"
foreach ($line in $resultLines) {
    $trim = $line.Trim()
    if (-not $trim.StartsWith("|")) { continue }
    if ($trim -like "|---*") { continue }
    $cols = $trim.Trim("|").Split("|") | ForEach-Object { $_.Trim() }
    if ($cols.Count -lt 4) { continue }
    $testId = $cols[0]
    if ($testId -notmatch '^[A-Z0-9-]+$') { continue }
    if ($resultsStatus[$testId] -ne "PASS") { continue }

    $artifactRefs = Parse-ReferencedArtifacts $cols[3]
    if ($artifactRefs.Count -eq 0) {
        throw "PASS test has no artifact refs: $testId"
    }
    foreach ($ref in $artifactRefs) {
        $full = Join-Path $artifactDir $ref
        if (-not (Test-Path $full)) {
            throw "PASS test artifact missing: $testId -> $full"
        }
    }
}

# 2) 00/06 docs must not claim PASS when 04 is FAIL/SKIPPED
# Why: 삭제된 과거 요약 문서를 필수 의존하지 않고, 현재 검증팩 정본만 기준으로 일관성을 확인한다.
$docsToCheck = @($summaryPath, $artifactSummaryPath)
foreach ($docPath in $docsToCheck) {
    $content = Get-Content $docPath -Raw -Encoding utf8
    $docMap = Parse-StatusMap $content
    foreach ($key in $docMap.Keys) {
        if ($docMap[$key] -eq "PASS") {
            if (-not $resultsStatus.ContainsKey($key)) {
                throw "$docPath claims PASS for unknown test id: $key"
            }
            if ($resultsStatus[$key] -ne "PASS") {
                throw "$docPath claims PASS for $key but 04 says $($resultsStatus[$key])"
            }
        }
    }
}

# 2-1) 03 and 04 test id sets must match exactly.
$planContent = Get-Content $planPath -Raw -Encoding utf8
$planIds = Parse-TestIdsFromPlan $planContent
$resultIds = New-Object System.Collections.Generic.HashSet[string]
foreach ($k in $resultsStatus.Keys) { $null = $resultIds.Add($k) }
foreach ($planId in $planIds) {
    if (-not $resultIds.Contains($planId)) {
        throw "03 contains test id not found in 04: $planId"
    }
}
foreach ($resultId in $resultIds) {
    if (-not $planIds.Contains($resultId)) {
        throw "04 contains test id not found in 03: $resultId"
    }
}

# 2-2) CHANGELOG must explicitly indicate SSOT source.
$changelogContent = Get-Content $changelogPath -Raw -Encoding utf8
if ($changelogContent -notmatch '(?i)04_TEST_RESULTS\.md') {
    throw "CHANGELOG must reference 04_TEST_RESULTS.md as SSOT source"
}

# 3) duplicate check for canonical doc names outside _DEPRECATED
$targetNames = @(
    "03_TEST_PLAN.md",
    "00_EXEC_SUMMARY.md",
    "04_TEST_RESULTS.md",
    "06_ARTIFACT_SUMMARY_FOR_CROSS_CHECK.md",
    "CHANGELOG.md"
)
foreach ($name in $targetNames) {
    $all = Get-ChildItem -Recurse -File -Filter $name | Where-Object {
        $_.FullName -notmatch '\\_DEPRECATED\\' -and
        $_.FullName -notmatch '\\node_modules\\' -and
        $_.FullName -notmatch '\\\.git\\'
    }
    if ($all.Count -gt 1) {
        $paths = ($all | Select-Object -ExpandProperty FullName) -join ", "
        throw "duplicate canonical docs found: $name -> $paths"
    }
}

Write-Host "verification_pack_consistency=PASS"
