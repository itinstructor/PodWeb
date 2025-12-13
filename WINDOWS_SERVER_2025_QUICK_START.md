# Windows Server 2025 Stream Recording - Quick Reference

## One-Line Setup

```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; .\setup_recording.ps1
```

## Installation Steps

### 1. Install FFmpeg (Choose One)

**Chocolatey** (Recommended):
```powershell
choco install ffmpeg -y
ffmpeg -version  # Verify
```

**Winget**:
```powershell
winget install ffmpeg
ffmpeg -version
```

**Manual**:
1. Download from https://ffmpeg.org/download.html
2. Extract to `C:\Program Files\ffmpeg`
3. Add to PATH (see setup_recording.ps1 for GUI steps)

### 2. Create Recordings Directory

```powershell
New-Item -ItemType Directory -Path "C:\inetpub\podsinspace\static\recordings" -Force
```

### 3. Run Automated Setup

```powershell
# Open PowerShell as Administrator
cd C:\inetpub\podsinspace
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\setup_recording.ps1
```

This script:
- ✅ Creates recordings directory
- ✅ Checks FFmpeg installation
- ✅ Verifies Python dependencies
- ✅ Configures Windows Firewall
- ✅ Creates automatic cleanup task (optional)

### 4. Start Flask App

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run app
python main_app.py
# or if using gunicorn/waitress:
waitress-serve --port=5000 main_app:app
```

### 5. Test Recording

1. Navigate to: `http://localhost:5000/podsinspace`
2. Log in to blog
3. Click **Record** button
4. Click **Stop Recording**
5. Click **Download** to save MP4

## File Locations

```
C:\inetpub\podsinspace\
├── static\recordings\          # MP4 files stored here
│   ├── stream_recording_*.mp4
│   └── ...
├── stream_recorder.py          # Recording module
├── recording_routes.py         # API endpoints
├── setup_recording.ps1         # Setup script
└── STREAM_RECORDING_SETUP.md   # Full documentation
```

## API Commands

### Start Recording
```powershell
$params = @{
    Uri = "http://localhost:5000/podsinspace/recording/start"
    Method = "POST"
    ContentType = "application/json"
    Body = @{ stream_url = "http://pi-ip:8080/stream.mjpg" } | ConvertTo-Json
}
Invoke-RestMethod @params
```

### Check Recording Status
```powershell
Invoke-RestMethod `
    -Uri "http://localhost:5000/podsinspace/recording/status/20251212_150000" `
    -Method "GET" | ConvertTo-Json
```

### Stop Recording
```powershell
Invoke-RestMethod `
    -Uri "http://localhost:5000/podsinspace/recording/stop/20251212_150000" `
    -Method "POST"
```

## Firewall Configuration

If automatic setup fails:

```powershell
# Allow Flask app through firewall
New-NetFirewallRule -DisplayName "Flask Stream Recording" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 5000, 8000 `
    -Program "python.exe"

# Remove rule if needed
Remove-NetFirewallRule -DisplayName "Flask Stream Recording" -Confirm:$false
```

## Disk Space Management

### Check Recordings Directory Size
```powershell
(Get-ChildItem C:\inetpub\podsinspace\static\recordings -Recurse | 
    Measure-Object -Property Length -Sum).Sum / 1GB
```

### Manual Cleanup (Delete files older than 30 days)
```powershell
$recordingsDir = "C:\inetpub\podsinspace\static\recordings"
$ageInDays = 30
$cutoffDate = (Get-Date).AddDays(-$ageInDays)

Get-ChildItem -Path $recordingsDir -Filter "*.mp4" | 
    Where-Object { $_.LastWriteTime -lt $cutoffDate } | 
    Remove-Item -Force -Verbose
```

### Check Free Disk Space
```powershell
Get-Volume | Select-Object DriveLetter, FileSystemLabel, SizeRemaining, Size
```

## Troubleshooting Commands

### Check FFmpeg
```powershell
# Verify installation
ffmpeg -version

# Check supported formats
ffmpeg -formats | Select-String "mp4"

# Test stream (replace URL)
ffmpeg -i "http://localhost:8080/stream.mjpg" -t 5 -f null -
```

### Check Python & Flask
```powershell
# Verify Python
python --version

# Check Flask installation
python -c "import flask; print(flask.__version__)"

# Test Flask app import
python -c "from main_app import app; print('✓ Flask app loads successfully')"
```

### Check Running Processes
```powershell
# List Python processes
Get-Process python | Select-Object Id, ProcessName, CPU, Memory

# Kill specific FFmpeg process
Get-Process ffmpeg | Stop-Process -Force

# Check listening ports
netstat -ano | Select-String "5000"
```

### IIS AppPool Permissions
```powershell
# Check AppPool identity
Get-IISAppPool | Select-Object Name, ProcessModel.IdentityType

# Grant permissions to AppPool
icacls "C:\inetpub\podsinspace\static\recordings" /grant:r "IIS APPPOOL\DefaultAppPool:(OI)(CI)F" /T
```

## Performance Tips

- **Reduce Quality**: Lower bitrate in stream_recorder.py (saves disk space)
- **Faster Encoding**: Use `'-preset', 'fast'` instead of 'medium'
- **Multiple Recordings**: Monitor CPU usage, may need to limit concurrent recordings
- **Disk I/O**: Use SSD for recordings directory if possible

## Logs Location

```powershell
# Flask app logs
C:\inetpub\podsinspace\logs\main_app.log

# View recent errors
Get-Content C:\inetpub\podsinspace\logs\main_app.log -Tail 50

# Real-time monitoring
Get-Content C:\inetpub\podsinspace\logs\main_app.log -Wait -Tail 20
```

## Environment Variables

```powershell
# View all environment variables
Get-ChildItem env: | Sort-Object Name

# Set temporary variable
$env:FLASK_ENV = "production"

# Set permanent variable (requires restart)
[Environment]::SetEnvironmentVariable("FLASK_ENV", "production", "Machine")
```

## Security

### Run with Limited Privileges

```powershell
# Create separate Windows user for Flask app
New-LocalUser -Name "FlaskRecorder" -Password (ConvertTo-SecureString "SecurePassword123!" -AsPlainText -Force)

# Grant permissions to user
icacls "C:\inetpub\podsinspace\static\recordings" /grant "FlaskRecorder:(OI)(CI)M"
icacls "C:\inetpub\podsinspace\logs" /grant "FlaskRecorder:(OI)(CI)M"

# Run Flask app as user
runas /user:FlaskRecorder "python C:\inetpub\podsinspace\main_app.py"
```

### Restrict File Access

```powershell
# Only administrators can access recordings
$path = "C:\inetpub\podsinspace\static\recordings"
icacls $path /reset
icacls $path /grant:r "BUILTIN\Administrators:(OI)(CI)F"
icacls $path /grant:r "IIS APPPOOL\DefaultAppPool:(OI)(CI)R"
```

## More Help

See **STREAM_RECORDING_SETUP.md** for full documentation.

---

**Last Updated**: December 12, 2025  
**Windows Server Version**: 2025  
**Python Version**: 3.11+  
**FFmpeg**: 7.0+
