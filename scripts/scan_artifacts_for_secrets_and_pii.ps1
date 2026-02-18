$ErrorActionPreference = "Stop"

$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$outputPath = Join-Path $artifactDir "artifact_sanitization_scan.txt"

$includeExt = @("*.txt", "*.log", "*.json", "*.md")
$files = @()
foreach ($ext in $includeExt) {
    $files += Get-ChildItem -Path $artifactDir -File -Filter $ext -ErrorAction SilentlyContinue
}
$files = $files | Sort-Object FullName -Unique

$rules = @(
    @{ Name = "AUTH_HEADER"; Pattern = '(?i)Authorization\s*:' },
    @{ Name = "BEARER_TOKEN"; Pattern = '(?i)Bearer\s+[A-Za-z0-9_\-\.]{20,}' },
    @{ Name = "JWT_LIKE"; Pattern = 'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}' },
    @{ Name = "EMAIL_RAW"; Pattern = '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' },
    @{ Name = "PHONE_RAW"; Pattern = '(?<!\*)\b\d{2,3}[- ]?\d{3,4}[- ]?\d{4}\b' }
)

$allowlist = @(
    '@***',
    'example.com',
    'support@example.com',
    'masked',
    '[EMAIL]',
    '[PHONE]',
    '[ORDER_ID]'
)

$hits = New-Object System.Collections.Generic.List[object]
foreach ($file in $files) {
    $lines = Get-Content -Path $file.FullName -Encoding utf8 -ErrorAction SilentlyContinue
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        foreach ($rule in $rules) {
            $match = [regex]::Match($line, $rule.Pattern)
            if (-not $match.Success) {
                continue
            }
            $isAllowed = $false
            foreach ($allow in $allowlist) {
                if ($line -like "*$allow*") {
                    $isAllowed = $true
                    break
                }
            }
            if (-not $isAllowed) {
                $hits.Add([pscustomobject]@{
                    file = $file.Name
                    line = ($i + 1)
                    rule = $rule.Name
                    sample = ($line.Substring(0, [Math]::Min($line.Length, 200)))
                })
            }
        }
    }
}

if ($hits.Count -gt 0) {
    $report = @("artifact_scan_status=FAIL", "hit_count=$($hits.Count)", "")
    foreach ($hit in $hits) {
        $report += "file=$($hit.file) line=$($hit.line) rule=$($hit.rule) sample=$($hit.sample)"
    }
    $report -join "`n" | Out-File -FilePath $outputPath -Encoding utf8
    throw "artifact sanitization scan failed. see $outputPath"
}

@"
artifact_scan_status=PASS
scanned_files=$($files.Count)
checked_patterns=$($rules.Count)
allowlist_entries=$($allowlist.Count)
"@ | Out-File -FilePath $outputPath -Encoding utf8

Write-Host "artifact_sanitization_scan=PASS"
