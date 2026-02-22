param(
    [string]$NvmrcPath = ".nvmrc"
)

$ErrorActionPreference = "Stop"

Write-Host "[compat] bootstrap_node_22.ps1 is deprecated. Use scripts/bootstrap_node_from_nvmrc.ps1."
& powershell -ExecutionPolicy Bypass -File "$PSScriptRoot/bootstrap_node_from_nvmrc.ps1" -NvmrcPath $NvmrcPath
exit $LASTEXITCODE
