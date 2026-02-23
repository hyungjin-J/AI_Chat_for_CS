param(
    [string]$NvmrcPath = ".nvmrc"
)

$ErrorActionPreference = "Stop"

function Read-RequiredNodeVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -Path $Path)) {
        throw ".nvmrc not found: $Path"
    }

    $lines = Get-Content -Path $Path -Encoding utf8
    foreach ($line in $lines) {
        $value = $line.Trim()
        if ($value -and -not $value.StartsWith("#")) {
            return $value.TrimStart("v")
        }
    }

    throw ".nvmrc is empty: $Path"
}

function Read-CurrentNodeVersion {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodeCommand) {
        return ""
    }

    $runtime = (node -v).Trim()
    if (-not $runtime) {
        return ""
    }
    return $runtime.TrimStart("v")
}

function Invoke-WorkspaceAsciiWarning {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        return
    }

    $asciiCheckScript = Join-Path $PSScriptRoot "check_workspace_path_ascii.py"
    if (-not (Test-Path -Path $asciiCheckScript)) {
        return
    }

    & python $asciiCheckScript --path (Get-Location).Path
}

try {
    $required = Read-RequiredNodeVersion -Path $NvmrcPath
    $current = Read-CurrentNodeVersion

    if ($current -eq $required) {
        Write-Host "[OK] Node runtime already matches .nvmrc ($required)."
        Invoke-WorkspaceAsciiWarning
        Write-Host "[NEXT] Continue with: npm ci --prefer-offline --no-audit --fund=false"
        exit 0
    }

    if ($current) {
        Write-Warning "[ACTION] Node mismatch detected (current=$current required=$required)."
    } else {
        Write-Warning "[ACTION] Node runtime is not available in PATH (required=$required)."
    }

    $nvmCommand = Get-Command nvm -ErrorAction SilentlyContinue
    if ($nvmCommand) {
        Write-Host "[ACTION] Trying automatic recovery with nvm install/use..."
        & nvm install $required
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[FAIL] nvm install failed for $required"
            exit 1
        }

        & nvm use $required
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[FAIL] nvm use failed for $required"
            exit 1
        }

        $after = Read-CurrentNodeVersion
        if ($after -eq $required) {
            Write-Host "[OK] Node runtime switched to $after."
            Invoke-WorkspaceAsciiWarning
            Write-Host "[NEXT] Re-run gate: python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime"
            exit 0
        }

        Write-Error "[FAIL] Node is still mismatched after nvm use (current=$after required=$required)"
        exit 1
    }

    Write-Warning "[ACTION] nvm was not found."
    Write-Host "1) Install nvm-windows: https://github.com/coreybutler/nvm-windows/releases"
    Write-Host "2) Re-open terminal so PATH is refreshed."
    Write-Host "3) Run: nvm install $required"
    Write-Host "4) Run: nvm use $required"
    Write-Host "5) Re-run gate: python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime"
    Write-Host "[ALT] Direct installer fallback: https://nodejs.org/en/download (select v$required)"
    exit 1
} catch {
    Write-Error $_
    exit 1
}
