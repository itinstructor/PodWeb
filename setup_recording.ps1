# Windows Server 2025 Stream Recording Setup
# Run as Administrator in PowerShell

# Requires Administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

Write-Host "================================" -ForegroundColor Green
Write-Host "Stream Recording Setup for Windows Server 2025" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Set working directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# 1. Create recordings directory
Write-Host "`nStep 1: Creating recordings directory..." -ForegroundColor Yellow
$recordingsDir = Join-Path $scriptPath "static\recordings"
if (-not (Test-Path $recordingsDir)) {
    New-Item -ItemType Directory -Path $recordingsDir -Force | Out-Null
    Write-Host "Created: $recordingsDir" -ForegroundColor Green
} else {
    Write-Host "Already exists: $recordingsDir" -ForegroundColor Green
}

# 2. Check for FFmpeg
Write-Host "`nStep 2: Checking for FFmpeg..." -ForegroundColor Yellow
$ffmpegPath = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source

if ($ffmpegPath) {
    Write-Host "FFmpeg found at: $ffmpegPath" -ForegroundColor Green
    $ffmpegVersion = & ffmpeg -version 2>&1 | Select-Object -First 1
    Write-Host $ffmpegVersion -ForegroundColor Green
} else {
    Write-Host "FFmpeg not found in PATH" -ForegroundColor Red
    Write-Host "`nChoose installation method:" -ForegroundColor Yellow
    Write-Host "1. Chocolatey (recommended): choco install ffmpeg" -ForegroundColor Cyan
    Write-Host "2. Winget: winget install ffmpeg" -ForegroundColor Cyan
    Write-Host "3. Manual: Download from https://ffmpeg.org/download.html" -ForegroundColor Cyan
    Write-Host "`nAfter installation, restart PowerShell and run this script again." -ForegroundColor Yellow
}

# 3. Check Python virtual environment
Write-Host "`nStep 3: Checking Python environment..." -ForegroundColor Yellow
$venvPath = Join-Path $scriptPath ".venv"

if (Test-Path $venvPath) {
    Write-Host "Virtual environment found: $venvPath" -ForegroundColor Green
    
    # Activate venv
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    & $activateScript
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "Virtual environment not found at: $venvPath" -ForegroundColor Red
    Write-Host "Run: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# 4. Verify required Python modules
Write-Host "`nStep 4: Verifying Python dependencies..." -ForegroundColor Yellow
python -c "import flask; print('[OK] Flask installed')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Flask..." -ForegroundColor Yellow
    pip install flask
}

# 5. Test FFmpeg command
Write-Host "`nStep 5: Testing FFmpeg functionality..." -ForegroundColor Yellow
if ($ffmpegPath) {
    $ffmpegTest = & ffmpeg -formats 2>&1 | Select-String "mp4" -Quiet
    if ($ffmpegTest) {
        Write-Host "[OK] FFmpeg supports MP4 format" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] MP4 support may be missing" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARNING] Cannot test FFmpeg (not installed)" -ForegroundColor Yellow
}

# 6. Create firewall rule (if needed)
Write-Host "`nStep 6: Checking firewall rules..." -ForegroundColor Yellow
$firewallRule = Get-NetFirewallRule -DisplayName "Flask App Recording" -ErrorAction SilentlyContinue
if (-not $firewallRule) {
    Write-Host "Firewall rule not found. Creating rule for Flask app (port 5000/8000)..." -ForegroundColor Yellow
    try {
        New-NetFirewallRule -DisplayName "Flask App Recording" `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalPort 5000, 8000 `
            -Program "python.exe" `
            -ErrorAction Stop | Out-Null
        Write-Host "[OK] Firewall rule created" -ForegroundColor Green
    } catch {
        Write-Host "[WARNING] Could not create firewall rule: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Firewall rule already exists" -ForegroundColor Green
}

# 7. Create cleanup script
Write-Host "`nStep 7: Creating cleanup helper script..." -ForegroundColor Yellow
$cleanupScriptPath = Join-Path $scriptPath "cleanup_recordings.ps1"

$cleanupContent = @'
# Delete recordings older than 30 days
param([int]$DaysOld = 30)

$recordingsDir = "{RECORDINGS_DIR}"
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
'@

$cleanupContent = $cleanupContent -replace "{RECORDINGS_DIR}", $recordingsDir
Set-Content -Path $cleanupScriptPath -Value $cleanupContent -Force
Write-Host "[OK] Cleanup script created: $cleanupScriptPath" -ForegroundColor Green

# 8. Show next steps
Write-Host "`n================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Verify FFmpeg is installed: ffmpeg -version" -ForegroundColor Cyan
Write-Host "2. Start Flask app: python main_app.py" -ForegroundColor Cyan
Write-Host "3. Navigate to: http://localhost:5000/podsinspace" -ForegroundColor Cyan
Write-Host "4. Log in and test recording on home page" -ForegroundColor Cyan
Write-Host "`nRecordings stored in: $recordingsDir" -ForegroundColor Cyan
Write-Host "`nFor more information, see: STREAM_RECORDING_SETUP.md" -ForegroundColor Cyan

# Show disk space
Write-Host "`nDisk Space:" -ForegroundColor Yellow
$diskInfo = Get-Volume | Where-Object { $_.DriveLetter -eq (Split-Path $recordingsDir -Qualifier).TrimEnd(":") }
if ($diskInfo) {
    $freeGB = [math]::Round($diskInfo.SizeRemaining / 1GB, 2)
    $totalGB = [math]::Round($diskInfo.Size / 1GB, 2)
    Write-Host "$freeGB GB free of $totalGB GB total" -ForegroundColor Cyan
}

Write-Host ""
