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

function Test-AsciiOnly {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    foreach ($char in $Value.ToCharArray()) {
        if ([int][char]$char -gt 127) {
            return $false
        }
    }
    return $true
}

function Resolve-AsciiMirrorRoot {
    param(
        [string]$RequestedRoot = ""
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedRoot)) {
        $resolvedRequested = [System.IO.Path]::GetFullPath($RequestedRoot)
        if (Test-AsciiOnly -Value $resolvedRequested) {
            return $resolvedRequested
        }
        throw "MirrorRoot must be ASCII-only: $resolvedRequested"
    }

    $tempValue = $env:TEMP
    if (-not $tempValue) {
        $tempValue = "C:\Temp"
    }

    $candidate = [System.IO.Path]::Combine($tempValue, "AI_Chatbot_ascii_workspace")
    if (Test-AsciiOnly -Value $candidate) {
        return [System.IO.Path]::GetFullPath($candidate)
    }

    $fallback = "C:\Temp\AI_Chatbot_ascii_workspace"
    return [System.IO.Path]::GetFullPath($fallback)
}

function Get-WorkspaceAsciiStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspacePath,
        [Parameter(Mandatory = $true)]
        [string]$ScriptRoot
    )

    $checkScript = Join-Path $ScriptRoot "check_workspace_path_ascii.py"
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand -or -not (Test-Path -Path $checkScript)) {
        return @{
            status = "UNKNOWN"
            output = @(
                "check_workspace_path_ascii",
                "status=UNKNOWN",
                "details=python or check script not available; fallback to local ASCII detector"
            )
        }
    }

    $output = @(& python $checkScript --path $WorkspacePath 2>&1)
    $statusLine = ($output | Where-Object { $_ -like "status=*" } | Select-Object -First 1)
    if (-not $statusLine) {
        return @{
            status = "UNKNOWN"
            output = @(
                $output
            )
        }
    }

    $status = $statusLine.Split("=", 2)[1].Trim().ToUpperInvariant()
    return @{
        status = $status
        output = $output
    }
}

function Invoke-RobocopyMirror {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath
    )

    $excludeDirs = @(
        ".git",
        "node_modules",
        ".gradle",
        "dist",
        "build",
        "target",
        "out",
        ".idea",
        ".vscode"
    )

    $robocopyArgs = @(
        $SourcePath,
        $DestinationPath,
        "/MIR",
        "/R:2",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP",
        "/XD"
    ) + $excludeDirs

    & robocopy @robocopyArgs
    $robocopyExitCode = $LASTEXITCODE
    if ($robocopyExitCode -gt 7) {
        throw "robocopy failed with exit code $robocopyExitCode"
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [ScriptBlock]$Action,
        [switch]$DryRunStep
    )

    if ($DryRunStep) {
        Write-Host "[DRY-RUN] $Name"
        return
    }

    Write-Host "[RUN] $Name"
    & $Action
}

try {
    $resolvedSourceRoot = (Resolve-Path -Path $SourceRoot).Path
    $sourceRootAscii = Test-AsciiOnly -Value $resolvedSourceRoot
    $asciiStatus = Get-WorkspaceAsciiStatus -WorkspacePath $resolvedSourceRoot -ScriptRoot $PSScriptRoot

    foreach ($line in $asciiStatus.output) {
        if ($line) {
            Write-Host $line
        }
    }

    $statusIsWarning = $asciiStatus.status -eq "WARNING"
    $shouldMirror = $ForceMirror -or $statusIsWarning -or (-not $sourceRootAscii)
    $resolvedMirrorRoot = Resolve-AsciiMirrorRoot -RequestedRoot $MirrorRoot

    if (-not (Test-AsciiOnly -Value $resolvedMirrorRoot)) {
        throw "Resolved mirror root is not ASCII-only: $resolvedMirrorRoot"
    }

    $runRoot = $resolvedSourceRoot
    $pathMode = "native"
    $mirrorPerformed = $false

    if ($shouldMirror) {
        if (([System.IO.Path]::GetFullPath($resolvedSourceRoot)).TrimEnd("\") -eq ([System.IO.Path]::GetFullPath($resolvedMirrorRoot)).TrimEnd("\")) {
            throw "Mirror root must be different from source root."
        }

        Invoke-Step -Name "mirror workspace to ASCII path" -DryRunStep:$DryRun -Action {
            if ((Test-Path -Path $resolvedMirrorRoot) -and -not $KeepMirror) {
                Remove-Item -Path $resolvedMirrorRoot -Recurse -Force
            }
            New-Item -Path $resolvedMirrorRoot -ItemType Directory -Force | Out-Null
            Invoke-RobocopyMirror -SourcePath $resolvedSourceRoot -DestinationPath $resolvedMirrorRoot
        }

        $runRoot = $resolvedMirrorRoot
        $pathMode = "mirrored"
        $mirrorPerformed = -not $DryRun
    } else {
        Write-Host "[INFO] Workspace path is ASCII-safe. Running in-place."
    }

    $runBootstrap = -not $SkipNodeBootstrap
    $runInstall = -not $SkipInstall
    $runTests = -not $SkipTests
    $runBuild = -not $SkipBuild

    if ($runBootstrap) {
        Invoke-Step -Name "bootstrap node from .nvmrc" -DryRunStep:$DryRun -Action {
            $bootstrapScript = Join-Path $runRoot "scripts/bootstrap_node_from_nvmrc.ps1"
            if (-not (Test-Path -Path $bootstrapScript)) {
                throw "bootstrap script not found in run root: $bootstrapScript"
            }
            & powershell -ExecutionPolicy Bypass -File $bootstrapScript -NvmrcPath (Join-Path $runRoot ".nvmrc")
            if ($LASTEXITCODE -ne 0) {
                throw "bootstrap_node_from_nvmrc.ps1 failed with exit code $LASTEXITCODE"
            }
        }
    } else {
        Write-Host "[SKIP] node bootstrap"
    }

    $frontendPath = Join-Path $runRoot "frontend"
    if (-not $DryRun -and -not (Test-Path -Path $frontendPath)) {
        throw "frontend directory not found: $frontendPath"
    }

    $frontendCommands = @()
    if ($runInstall) { $frontendCommands += "npm ci --prefer-offline --no-audit --fund=false" }
    if ($runTests) { $frontendCommands += "npm run test:run" }
    if ($runBuild) { $frontendCommands += "npm run build" }

    foreach ($cmd in $frontendCommands) {
        Invoke-Step -Name "frontend: $cmd" -DryRunStep:$DryRun -Action {
            Push-Location $frontendPath
            try {
                cmd /c $cmd
                if ($LASTEXITCODE -ne 0) {
                    throw "frontend command failed: $cmd (exit=$LASTEXITCODE)"
                }
            } finally {
                Pop-Location
            }
        }
    }

    if (-not $frontendCommands) {
        Write-Host "[SKIP] frontend commands (install/tests/build 모두 skip)"
    }

    $summaryLines = @(
        "mirror_and_run_frontend",
        "status=PASS",
        "source_root=$resolvedSourceRoot",
        "run_root=$runRoot",
        "path_mode=$pathMode",
        "mirror_requested=$shouldMirror",
        "mirror_performed=$mirrorPerformed",
        "dry_run=$DryRun",
        "node_bootstrap_ran=$runBootstrap",
        "npm_ci_ran=$runInstall",
        "npm_test_ran=$runTests",
        "npm_build_ran=$runBuild"
    )
    $summary = ($summaryLines -join "`n") + "`n"
    Write-Host $summary

    if ($SmokeArtifactPath) {
        $artifactPath = [System.IO.Path]::GetFullPath($SmokeArtifactPath)
        $artifactDir = Split-Path -Path $artifactPath -Parent
        if ($artifactDir) {
            New-Item -Path $artifactDir -ItemType Directory -Force | Out-Null
        }
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($artifactPath, $summary, $utf8NoBom)
        Write-Host "[OK] smoke artifact written: $artifactPath"
    }

    exit 0
} catch {
    Write-Error $_
    exit 1
}
