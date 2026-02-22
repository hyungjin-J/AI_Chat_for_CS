param(
    [string]$ArtifactDir = "docs/review/mvp_verification_pack/artifacts",
    [string]$BundleName = "windows_npm_lock_diag_bundle.zip"
)

$ErrorActionPreference = "Stop"

function Safe-CommandOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    try {
        return (cmd /c $Command 2>&1 | Out-String).Trim()
    } catch {
        return "ERROR: $($_.Exception.Message)"
    }
}

New-Item -ItemType Directory -Force -Path $ArtifactDir | Out-Null

$bundleFolder = Join-Path $ArtifactDir "windows_npm_lock_diag_bundle"
if (Test-Path $bundleFolder) {
    Remove-Item -Recurse -Force $bundleFolder
}
New-Item -ItemType Directory -Force -Path $bundleFolder | Out-Null

$smokeMode = $env:DIAG_SMOKE -eq "1"
$kstZone = [System.TimeZoneInfo]::FindSystemTimeZoneById("Korea Standard Time")
$kstNow = [System.TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, $kstZone)
$timestamp = $kstNow.ToString("yyyy-MM-dd HH:mm:ss zzz")
$cwdLength = ((Get-Location).Path).Length
$osInfo = Get-CimInstance Win32_OperatingSystem

$summaryLines = @(
    "windows_npm_lock_diag_bundle",
    "captured_at_kst=$timestamp",
    "diag_smoke_mode=$smokeMode",
    "bundle_version=phase2_1_4"
)
($summaryLines -join "`n") + "`n" | Out-File -FilePath (Join-Path $bundleFolder "summary.txt") -Encoding utf8

("node_version=" + (Safe-CommandOutput -Command "node -v")) + "`n" |
    Out-File -FilePath (Join-Path $bundleFolder "node_version.txt") -Encoding utf8

("npm_version=" + (Safe-CommandOutput -Command "npm -v")) + "`n" |
    Out-File -FilePath (Join-Path $bundleFolder "npm_version.txt") -Encoding utf8

@(
    "os_caption=$($osInfo.Caption)"
    "os_version=$($osInfo.Version)"
    "os_build=$($osInfo.BuildNumber)"
) -join "`n" |
    Out-File -FilePath (Join-Path $bundleFolder "os_info.txt") -Encoding utf8

@(
    "cwd_length=$cwdLength"
    "cwd_path=<REDACTED_PATH>"
) -join "`n" |
    Out-File -FilePath (Join-Path $bundleFolder "path_length.txt") -Encoding utf8

$readmeLines = @(
    "This bundle is sanitized for npm lock diagnostics."
    "No raw user home path, tokens, keys, or private credentials are included."
    "When DIAG_SMOKE=1, collection remains minimal for CI safety."
)
($readmeLines -join "`n") + "`n" | Out-File -FilePath (Join-Path $bundleFolder "readme.txt") -Encoding utf8

$bundlePath = Join-Path $ArtifactDir $BundleName
if (Test-Path $bundlePath) {
    Remove-Item -Force $bundlePath
}
Compress-Archive -Path (Join-Path $bundleFolder "*") -DestinationPath $bundlePath -Force
Remove-Item -Recurse -Force $bundleFolder

Write-Host "windows_npm_lock_diag_bundle"
Write-Host "diag_smoke_mode=$smokeMode"
Write-Host "bundle_path=$bundlePath"
