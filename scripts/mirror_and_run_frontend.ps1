param(
    [string]$SourceRoot = ".",
    [string]$MirrorRoot = "",
    [switch]$ForceMirror,
    [switch]$KeepMirror,
    [switch]$SkipNodeBootstrap,
    [switch]$SkipInstall,
    [switch]$SkipTests,
    [switch]$SkipBuild,
    [switch]$DryRun,
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

$argsList = @(
    $runner,
    "--source-root", $SourceRoot
)

if (-not [string]::IsNullOrWhiteSpace($MirrorRoot)) {
    $argsList += @("--mirror-root", $MirrorRoot)
}
if ($ForceMirror) { $argsList += "--force-mirror" }
if ($KeepMirror) { $argsList += "--keep-mirror" }
if ($SkipNodeBootstrap) { $argsList += "--skip-node-bootstrap" }
if ($SkipInstall) { $argsList += "--skip-install" }
if ($SkipTests) { $argsList += "--skip-tests" }
if ($SkipBuild) { $argsList += "--skip-build" }
if ($DryRun) { $argsList += "--dry-run" }
if (-not [string]::IsNullOrWhiteSpace($SmokeArtifactPath)) {
    $argsList += @("--smoke-artifact-path", $SmokeArtifactPath)
}

& python @argsList
exit $LASTEXITCODE
