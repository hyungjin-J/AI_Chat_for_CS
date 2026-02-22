param(
    [string]$ArtifactDir = "docs/review/mvp_verification_pack/artifacts",
    [string]$BundleName = "windows_npm_lock_diag_bundle.zip"
)

$ErrorActionPreference = "Stop"

function Mask-Text {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $masked = $Text
    $userHome = [Environment]::GetFolderPath("UserProfile")
    if ($userHome) {
        $masked = $masked -replace [regex]::Escape($userHome), "<REDACTED_USER_HOME>"
    }

    # Mask common token-like patterns if they appear in logs.
    $masked = $masked -replace "(?i)(api[_-]?key\s*[:=]\s*)(\S+)", '$1<REDACTED>'
    $masked = $masked -replace "(?i)(token\s*[:=]\s*)(\S+)", '$1<REDACTED>'
    $masked = $masked -replace "(?i)(authorization\s*[:=]\s*)(\S+)", '$1<REDACTED>'
    return $masked
}

function Safe-CaptureCommandOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    try {
        $raw = cmd /c $Command 2>&1 | Out-String
        return (Mask-Text -Text $raw.Trim())
    } catch {
        return "ERROR: $($_.Exception.Message)"
    }
}

New-Item -ItemType Directory -Force -Path $ArtifactDir | Out-Null

$workDir = Join-Path $ArtifactDir "windows_npm_lock_diag_bundle"
if (Test-Path $workDir) {
    Remove-Item -Recurse -Force $workDir
}
New-Item -ItemType Directory -Force -Path $workDir | Out-Null

$timestamp = [DateTimeOffset]::Now.ToString("yyyy-MM-dd HH:mm:ss zzz")
$cwd = (Get-Location).Path
$cwdMasked = Mask-Text -Text $cwd
$cwdLength = $cwd.Length
$osInfo = Get-CimInstance Win32_OperatingSystem

$summary = @()
$summary += "windows_npm_lock_diag_bundle"
$summary += "captured_at_kst=$timestamp"
$summary += "node_version=$(Safe-CaptureCommandOutput -Command 'node -v')"
$summary += "npm_version=$(Safe-CaptureCommandOutput -Command 'npm -v')"
$summary += "os_caption=$(Mask-Text -Text $osInfo.Caption)"
$summary += "os_version=$(Mask-Text -Text $osInfo.Version)"
$summary += "cwd=$cwdMasked"
$summary += "cwd_length=$cwdLength"
$summary += "notes=No secrets/tokens/PII should be included."
$summaryText = ($summary -join "`n") + "`n"
$summaryPath = Join-Path $workDir "diagnostics_summary.txt"
$summaryText | Out-File -FilePath $summaryPath -Encoding utf8

$npmLogRoot = Join-Path $env:APPDATA "npm-cache\_logs"
$logsOut = Join-Path $workDir "npm_log_excerpt.txt"
if (Test-Path $npmLogRoot) {
    $recentLogs = Get-ChildItem -Path $npmLogRoot -File | Sort-Object LastWriteTime -Descending | Select-Object -First 3
    if ($recentLogs.Count -gt 0) {
        $content = @()
        foreach ($log in $recentLogs) {
            $content += "=== log: $(Mask-Text -Text $log.Name) ==="
            $tail = Get-Content -Path $log.FullName -Tail 120 -ErrorAction SilentlyContinue | Out-String
            $content += (Mask-Text -Text $tail.Trim())
            $content += ""
        }
        ($content -join "`n") + "`n" | Out-File -FilePath $logsOut -Encoding utf8
    } else {
        "No npm logs found under $npmLogRoot" | Out-File -FilePath $logsOut -Encoding utf8
    }
} else {
    "npm log root not found: $(Mask-Text -Text $npmLogRoot)" | Out-File -FilePath $logsOut -Encoding utf8
}

$bundlePath = Join-Path $ArtifactDir $BundleName
if (Test-Path $bundlePath) {
    Remove-Item -Force $bundlePath
}
Compress-Archive -Path (Join-Path $workDir "*") -DestinationPath $bundlePath -Force

Write-Host "Windows npm lock diagnostic bundle generated:"
Write-Host $bundlePath
