# Delete recordings older than 30 days
param([int]$DaysOld = 30)

$recordingsDir = "C:\inetpub\podsinspace\static\recordings"
$cutoffDate = (Get-Date).AddDays(-$DaysOld)

if (-not (Test-Path $recordingsDir)) {
    Write-Host "Recordings directory not found: $recordingsDir"
    exit 1
}

$deletedCount = 0
Get-ChildItem -Path $recordingsDir -Filter "*.mp4" | Where-Object { $_.LastWriteTime -lt $cutoffDate } | ForEach-Object {
    Remove-Item -Path $_.FullName -Force
    $deletedCount++
}

Write-Host "Cleanup complete: Deleted $deletedCount recordings older than $DaysOld days"
