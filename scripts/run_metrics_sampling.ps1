param(
    [int]$SampleCount = 20
)

$ErrorActionPreference = "Stop"

Write-Host "metrics_sampling_sample_count=$SampleCount"
powershell -ExecutionPolicy Bypass -File scripts/generate_metrics_report.ps1 -SampleCount $SampleCount
