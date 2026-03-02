param(
    [string]$SourceRoot = ".",
    [string]$MirrorRoot = "",
    [switch]$ForceMirror,
    [switch]$NoMirror,
    [switch]$KeepMirror,
    [ValidateSet("smoke", "test", "build", "dev")]
    [string]$Task = "smoke",
    [switch]$Smoke,
    [switch]$SkipNodeBootstrap,
    [switch]$SkipInstall,
    [switch]$SkipTests,
    [switch]$SkipBuild,
    [switch]$DryRun,
    [string]$ArtifactPath = "",
    [string]$SmokeArtifactPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$runner = Join-Path $PSScriptRoot "mirror_and_run_frontend.py"
if (-not (Test-Path -Path $runner)) {
    throw "mirror runner not found: $runner"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "python command not found in PATH"
}

if ($Smoke -and $Task -ne "smoke") {
    throw "-Smoke cannot be combined with -Task other than smoke"
}

if (-not [string]::IsNullOrWhiteSpace($ArtifactPath) -and -not [string]::IsNullOrWhiteSpace($SmokeArtifactPath)) {
    throw "Use either -ArtifactPath or -SmokeArtifactPath, not both"
}

$argsList = @(
    $runner,
    "--source-root", $SourceRoot,
    "--task", $Task
)

if (-not [string]::IsNullOrWhiteSpace($MirrorRoot)) {
    $argsList += @("--mirror-root", $MirrorRoot)
}
if ($ForceMirror) { $argsList += "--force-mirror" }
if ($NoMirror) { $argsList += "--no-mirror" }
if ($KeepMirror) { $argsList += "--keep-mirror" }
if ($Smoke) { $argsList += "--smoke" }
if ($SkipNodeBootstrap) { $argsList += "--skip-node-bootstrap" }
if ($SkipInstall) { $argsList += "--skip-install" }
if ($SkipTests) { $argsList += "--skip-tests" }
if ($SkipBuild) { $argsList += "--skip-build" }
if ($DryRun) { $argsList += "--dry-run" }
if (-not [string]::IsNullOrWhiteSpace($ArtifactPath)) {
    $argsList += @("--artifact-path", $ArtifactPath)
}
if (-not [string]::IsNullOrWhiteSpace($SmokeArtifactPath)) {
    $argsList += @("--smoke-artifact-path", $SmokeArtifactPath)
}

& python @argsList
exit $LASTEXITCODE
