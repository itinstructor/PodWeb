# Server-Side Stream Recording

Server-side MJPEG stream recording to MP4 format using FFmpeg.

**Supported Platforms**: Windows Server 2025, Windows 10/11, Linux, macOS

## Quick Start (Windows Server 2025)

```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; .\setup_recording.ps1
```

This automated script will:
- ✅ Create recordings directory
- ✅ Check for FFmpeg installation
- ✅ Verify Python dependencies
- ✅ Configure Windows firewall rules
- ✅ Create automatic cleanup task (optional)

## Installation

### Windows Server 2025

#### Option 1: Chocolatey (Recommended)
```powershell
# Install Chocolatey first if not already installed
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install FFmpeg
choco install ffmpeg -y
```

#### Option 2: Windows Package Manager (winget)
```powershell
winget install ffmpeg
```

#### Option 3: Manual Installation
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to `C:\Program Files\ffmpeg`
3. Add to PATH:
   - Right-click "This PC" → Properties → Advanced system settings
   - Click "Environment Variables"
   - Add `C:\Program Files\ffmpeg\bin` to Path

#### Option 4: Using the Setup Script
The automated setup script will guide you through FFmpeg installation.

#### Verify Installation
```powershell
ffmpeg -version
```

### Linux

```bash
sudo apt-get install ffmpeg
```

### macOS

```bash
brew install ffmpeg
```

### 2. Verify Installation

```bash
ffmpeg -version
```

## Features

- **Server-side recording**: Captures MJPEG streams directly on the server
- **MP4 output**: Native H.264 video codec
- **Authentication**: Only logged-in users can start/stop recordings
- **Status monitoring**: Real-time recording status and file size tracking
- **Secure downloads**: Path traversal protection, user authentication

## Configuration

Edit `stream_recorder.py` constants:

```python
RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'recordings')
FFMPEG_CMD = 'ffmpeg'  # or full path if not in PATH
```

### FFmpeg Encoding Options

In `stream_recorder.py`, adjust these parameters:

```python
'-c:v', 'libx264',      # Video codec: libx264 (H.264), libvpx (VP8), hevc_nvenc (NVIDIA)
'-preset', 'medium',    # Speed: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
'-crf', '23',          # Quality: 0-51 (lower=better, 23=default)
'-b:v', '2000k',       # Video bitrate (optional, overrides CRF)
```

## API Endpoints

All endpoints require authentication (`user_id` in session).

### Start Recording
```
POST /podsinspace/recording/start

Request:
{
  "stream_url": "http://localhost:8080/stream.mjpg",
  "recording_id": "optional_id"  // auto-generated if omitted
}

Response:
{
  "success": true,
  "message": "Recording started: 20251212_153000",
  "recording_id": "20251212_153000"
}
```

### Stop Recording
```
POST /podsinspace/recording/stop/{recording_id}

Response:
{
  "success": true,
  "message": "Recording stopped (size: 15728640 bytes)",
  "download_url": "/podsinspace/static/recordings/stream_recording_2025-12-12_15-30-00.mp4"
}
```

### Get Status
```
GET /podsinspace/recording/status/{recording_id}

Response:
{
  "status": "recording",
  "filename": "stream_recording_2025-12-12_15-30-00.mp4",
  "file_size": 15728640,
  "download_url": "/podsinspace/static/recordings/stream_recording_2025-12-12_15-30-00.mp4"
}
```

### Download Recording
```
GET /podsinspace/recording/download/{filename}

Returns: Binary MP4 file
```

## Usage

### From Web UI

1. Log in to the blog
2. Click **Record** button on home page
3. Recording starts (button turns red)
4. Click **Stop Recording** when done
5. Click **Download** to save MP4 file

### From Python

```python
from stream_recorder import recording_manager

# Start recording
success, msg, recording_id = recording_manager.start_recording(
    'http://localhost:8080/stream.mjpg'
)

# Check status
status = recording_manager.get_recording_status(recording_id)
print(f"Status: {status['status']}, Size: {status['file_size']} bytes")

# Stop and download
success, msg, url = recording_manager.stop_recording(recording_id)
print(f"Download: {url}")
```

### From JavaScript

```javascript
// Start recording
const response = await fetch('/podsinspace/recording/start', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    stream_url: 'http://localhost:8080/stream.mjpg'
  })
});

const data = await response.json();
const recordingId = data.recording_id;

// Stop recording
const stopResponse = await fetch(
  `/podsinspace/recording/stop/${recordingId}`,
  {method: 'POST'}
);
```

## File Storage

Recorded files are stored in:
```
static/recordings/
  stream_recording_2025-12-12_15-30-00.mp4
  stream_recording_2025-12-12_15-45-30.mp4
  ...
```

Clean up old files manually or with a scheduled task:
```bash
# Delete files older than 7 days
find static/recordings -name "*.mp4" -mtime +7 -delete
```

## Troubleshooting

### Windows Server 2025 Specific

#### FFmpeg not found
```
Error: [Errno 2] No such file or directory: 'ffmpeg'
```

**Solutions**:
1. **Verify FFmpeg is installed**:
   ```powershell
   ffmpeg -version
   ```

2. **Add to PATH manually**:
   ```powershell
   # Temporary (current session only)
   $env:Path += ";C:\Program Files\ffmpeg\bin"
   
   # Permanent (all sessions)
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\ffmpeg\bin", "Machine")
   ```

3. **Update Python code with explicit path**:
   Edit `stream_recorder.py` line ~24:
   ```python
   FFMPEG_CMD = r'C:\Program Files\ffmpeg\bin\ffmpeg.exe'
   ```

4. **Use the automated setup script**:
   ```powershell
   .\setup_recording.ps1
   ```

#### Windows Firewall Blocking

```
Error: Connection refused
```

**Solution**: The setup script configures firewall rules automatically. Or manually add:
```powershell
New-NetFirewallRule -DisplayName "Flask App Recording" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 5000, 8000
```

#### IIS Integration Issues

If running through IIS:
1. Verify Application Pool identity has write access to `static\recordings`
2. Right-click folder → Properties → Security → Add "IIS AppPool\DefaultAppPool"
3. Grant Modify permissions

```powershell
# PowerShell script to set permissions
$path = "C:\inetpub\podsinspace\static\recordings"
$acl = Get-Acl -Path $path
$permission = "BUILTIN\IIS_IUSRS", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($permission)
$acl.SetAccessRule($rule)
Set-Acl -Path $path -AclObject $acl
```

#### Long Filename Issues

Windows Server may truncate long filenames. If you see:
```
Error: Filename is too long
```

**Solution**: Disable 8.3 naming:
```powershell
fsutil 8dot3name set C: 0
```

#### Running as Windows Service

To run Flask app as Windows Service, use NSSM:

```powershell
# Install NSSM if not already installed
choco install nssm -y

# Create service
nssm install PodsinspaceRecorder `
    "C:\inetpub\podsinspace\.venv\Scripts\python.exe" `
    "C:\inetpub\podsinspace\main_app.py"

# Set working directory
nssm set PodsinspaceRecorder AppDirectory "C:\inetpub\podsinspace"

# Start service
nssm start PodsinspaceRecorder

# Check status
Get-Service PodsinspaceRecorder
```

### General Troubleshooting

### MJPEG stream not accessible
```
Error: Cannot open input stream
```

**Solution**: Verify stream URL is reachable:
```bash
curl -I http://localhost:8080/stream.mjpg
```

### Insufficient disk space
```
Error: No space left on device
```

**Solution**: Delete old recordings or increase disk space:
```bash
du -sh static/recordings/
```

### Poor video quality
Adjust encoding quality in `stream_recorder.py`:
- Increase `-crf` value (23 → 28) for lower quality, smaller file
- Decrease `-crf` value (23 → 18) for higher quality, larger file
- Set video bitrate: `-b:v 5000k`

### Slow encoding
Use faster preset:
```python
'-preset', 'fast',  # or ultrafast, superfast, veryfast, faster
```

## Performance Considerations

- **CPU**: H.264 encoding is CPU-intensive; use `-preset fast` for lower CPU
- **Storage**: 1-2 MB per second at medium quality (640x480)
- **Bandwidth**: Stream source must be accessible during recording
- **Concurrency**: Each recording uses ~20-40% CPU per stream

## Security

- ✅ Only authenticated users can start/stop recordings
- ✅ Path traversal protection in download endpoint
- ✅ Filename validation
- ✅ All API endpoints require `user_id` in session
- ⚠️ Recordings stored in static directory (accessible via web)
  - Consider moving to protected directory
  - Implement access control per-recording

## License

Same as main application
