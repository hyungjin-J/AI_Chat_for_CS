$ErrorActionPreference = "Stop"

$artifactDir = "docs/review/mvp_verification_pack/artifacts"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$outputPath = Join-Path $artifactDir "branch_protection_check.txt"

function Parse-Repo {
    $origin = (git config --get remote.origin.url)
    if ([string]::IsNullOrWhiteSpace($origin)) {
        return $null
    }
    if ($origin -match 'github.com[:/](?<owner>[^/]+)/(?<repo>[^/.]+)(\.git)?$') {
        return @{ owner = $matches.owner; repo = $matches.repo }
    }
    return $null
}

$requiredCheck = "mvp-demo-verify / verify"
$repoInfo = Parse-Repo

if (-not $repoInfo) {
@"
status=MANUAL
reason=remote_origin_not_github_or_missing
required_check=$requiredCheck
action=GitHub Settings > Branches > main protection에서 required check 설정 필요
"@ | Out-File -FilePath $outputPath -Encoding utf8
    Write-Host "branch_protection_check=MANUAL"
    exit 0
}

$ghCmd = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghCmd) {
@"
status=MANUAL
reason=gh_cli_not_installed
required_check=$requiredCheck
repo=$($repoInfo.owner)/$($repoInfo.repo)
action=gh 설치 또는 웹 UI에서 수동 확인
"@ | Out-File -FilePath $outputPath -Encoding utf8
    Write-Host "branch_protection_check=MANUAL"
    exit 0
}

try {
    $apiPath = "repos/$($repoInfo.owner)/$($repoInfo.repo)/branches/main/protection"
    $json = gh api $apiPath 2>$null
    if ([string]::IsNullOrWhiteSpace($json)) {
        throw "gh_api_empty"
    }
    $obj = $json | ConvertFrom-Json
    $contexts = @()
    if ($obj.required_status_checks -and $obj.required_status_checks.contexts) {
        $contexts = @($obj.required_status_checks.contexts)
    }
    $found = $false
    foreach ($ctx in $contexts) {
        if ($ctx -eq $requiredCheck) {
            $found = $true
            break
        }
    }

    $status = if ($found) { "PASS" } else { "FAIL" }
    @"
status=$status
repo=$($repoInfo.owner)/$($repoInfo.repo)
required_check=$requiredCheck
registered_checks=$($contexts -join ",")
"@ | Out-File -FilePath $outputPath -Encoding utf8

    if (-not $found) {
        throw "required_check_missing"
    }

    Write-Host "branch_protection_check=PASS"
} catch {
@"
status=MANUAL
reason=gh_api_unavailable_or_not_authorized
repo=$($repoInfo.owner)/$($repoInfo.repo)
required_check=$requiredCheck
action=gh auth login 후 재실행 또는 웹 UI 수동 확인
"@ | Out-File -FilePath $outputPath -Encoding utf8
    Write-Host "branch_protection_check=MANUAL"
    exit 0
}
