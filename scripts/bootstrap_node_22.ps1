param(
    [string]$NvmrcPath = ".nvmrc"
)

$ErrorActionPreference = "Stop"

function Get-RequiredNodeVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$NvmrcPath
    )

    if (-not (Test-Path -Path $NvmrcPath)) {
        throw ".nvmrc not found: $NvmrcPath"
    }

    $lines = Get-Content -Path $NvmrcPath -Encoding utf8
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ($trimmed -and -not $trimmed.StartsWith("#")) {
            return $trimmed.TrimStart("v")
        }
    }

    throw ".nvmrc is empty: $NvmrcPath"
}

function Get-CurrentNodeVersion {
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

try {
    $required = Get-RequiredNodeVersion -NvmrcPath $NvmrcPath
    $current = Get-CurrentNodeVersion

    if ($current -eq $required) {
        Write-Host "OK: Node runtime matches .nvmrc ($required)"
        exit 0
    }

    if ($current) {
        Write-Warning "Node mismatch: current=$current required=$required"
    } else {
        Write-Warning "Node runtime was not found in PATH. required=$required"
    }

    $nvmCommand = Get-Command nvm -ErrorAction SilentlyContinue
    if ($nvmCommand) {
        Write-Host "Attempting automatic recovery with nvm..."
        & nvm install $required
        if ($LASTEXITCODE -ne 0) {
            Write-Error "nvm install failed for $required"
            exit 1
        }

        & nvm use $required
        if ($LASTEXITCODE -ne 0) {
            Write-Error "nvm use failed for $required"
            exit 1
        }

        $after = Get-CurrentNodeVersion
        if ($after -eq $required) {
            Write-Host "OK: Node runtime switched to $after"
            exit 0
        }

        Write-Error "Node version is still mismatched after nvm use (current=$after required=$required)"
        exit 1
    }

    Write-Host "nvm is not installed or not available in this shell."
    Write-Host "Manual bootstrap steps:"
    Write-Host "1) Install nvm-windows: https://github.com/coreybutler/nvm-windows/releases"
    Write-Host "2) Re-open terminal."
    Write-Host "3) Run: nvm install $required"
    Write-Host "4) Run: nvm use $required"
    Write-Host "5) Re-run: python scripts/check_node_version.py --nvmrc .nvmrc --package-json frontend/package.json --check-runtime"
    Write-Host "Alternative installer: https://nodejs.org/en/download (select v$required)"
    exit 1
} catch {
    Write-Error $_
    exit 1
}
