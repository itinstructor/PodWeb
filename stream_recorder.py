"""
Server-side stream recording module using ffmpeg.
Handles MJPEG stream capture and MP4 encoding.
Compatible with Windows Server 2025, Linux, and macOS.
"""

import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Optional
import shutil
import sys

logger = logging.getLogger(__name__)

# Configuration
RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'recordings')
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Detect FFmpeg executable based on platform
def get_ffmpeg_command():
    """Get FFmpeg command, handling Windows vs Unix paths."""
    # Try common locations
    candidates = [
        'ffmpeg',  # In PATH
        'ffmpeg.exe',  # Windows in PATH
        r'C:\ffmpeg\ffmpeg.exe',  # Windows custom installation
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',  # Windows default
        r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',  # Windows 32-bit
        '/usr/bin/ffmpeg',  # Linux
        '/usr/local/bin/ffmpeg',  # macOS
        shutil.which('ffmpeg'),  # Portable way to find in PATH
    ]
    
    for cmd in candidates:
        if cmd and shutil.which(cmd):
            return cmd
    
    # If nothing found, default to 'ffmpeg' and let system try
    return 'ffmpeg'

FFMPEG_CMD = get_ffmpeg_command()


class StreamRecorder:
    """Handles MJPEG stream recording to MP4 format."""
    
    def __init__(self, stream_url: str, output_filename: Optional[str] = None):
        """
        Initialize stream recorder.
        
        Args:
            stream_url: URL of MJPEG stream (e.g., http://localhost:8080/stream.mjpg)
            output_filename: Optional custom filename (without path). 
                           If not provided, generates timestamp-based name.
        """
        self.stream_url = stream_url
        self.is_recording = False
        self.process = None
        
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            output_filename = f'stream_recording_{timestamp}.mp4'
        
        self.output_path = os.path.join(RECORDINGS_DIR, output_filename)
        self.output_filename = output_filename
    
    def start(self) -> bool:
        """
        Start recording the stream to MP4 file.
        
        Returns:
            bool: True if recording started successfully, False otherwise.
        """
        if self.is_recording:
            logger.warning('Recording already in progress')
            return False
        
        try:
            # FFmpeg command to capture MJPEG stream and encode to MP4
            cmd = [
                FFMPEG_CMD,
                '-i', self.stream_url,      # Input stream URL
                '-c:v', 'libx264',          # Video codec (H.264)
                '-preset', 'medium',        # Encoding speed (fast/medium/slow)
                '-crf', '23',              # Quality (0-51, lower = better, 23 = default)
                '-c:a', 'aac',             # Audio codec
                '-b:a', '128k',            # Audio bitrate
                '-movflags', '+faststart', # Enable streaming of MP4 file
                '-y',                      # Overwrite output file if exists
                self.output_path
            ]
            
            # Use Popen to start ffmpeg in background
            # Don't capture stdout/stderr - let them go to console/devnull
            # This prevents potential deadlocks when trying to interact with the process
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.is_recording = True
            logger.info(f'Started recording stream to: {self.output_path}')
            return True
            
        except Exception as e:
            logger.error(f'Failed to start recording: {str(e)}')
            self.is_recording = False
            return False
    
    def stop(self) -> bool:
        """
        Stop recording the stream.
        
        Returns:
            bool: True if stopped successfully, False if no recording in progress.
        """
        if not self.is_recording or self.process is None:
            logger.warning('No recording in progress')
            return False
        
        try:
            # FFmpeg monitors stdin for 'q' key to gracefully quit
            quit_sent = False
            try:
                if self.process.stdin and not self.process.stdin.closed:
                    logger.info('Sending quit command to FFmpeg...')
                    self.process.stdin.write(b'q\n')
                    self.process.stdin.flush()
                    quit_sent = True
            except (BrokenPipeError, OSError, ValueError) as e:
                logger.debug(f'Could not send quit to FFmpeg: {e}')
            
            # Wait for FFmpeg to finish
            try:
                logger.info('Waiting for FFmpeg to finish gracefully (max 20 seconds)...')
                self.process.wait(timeout=20)
                logger.info('FFmpeg finished gracefully')
            except subprocess.TimeoutExpired:
                # Graceful shutdown didn't work, terminate
                logger.warning('FFmpeg did not respond to quit command within timeout, terminating...')
                self.process.terminate()
                try:
                    logger.info('Waiting for termination (max 5 seconds)...')
                    self.process.wait(timeout=5)
                    logger.info('FFmpeg terminated')
                except subprocess.TimeoutExpired:
                    # Still didn't finish, kill it
                    logger.warning('FFmpeg did not terminate within timeout, killing process...')
                    self.process.kill()
                    self.process.wait()
                    logger.info('FFmpeg killed')
            
            self.is_recording = False
            logger.info(f'Stopped recording. File saved to: {self.output_path}')
            return True
            
        except Exception as e:
            logger.error(f'Error stopping recording: {str(e)}')
            self.is_recording = False
            # Try to kill the process as last resort
            try:
                if self.process:
                    self.process.kill()
            except:
                pass
            return False
    
    def get_file_size(self) -> int:
        """
        Get the size of the recorded file in bytes.
        
        Returns:
            int: File size in bytes, or 0 if file doesn't exist.
        """
        try:
            if os.path.exists(self.output_path):
                return os.path.getsize(self.output_path)
        except Exception as e:
            logger.error(f'Error getting file size: {str(e)}')
        
        return 0
    
    def get_file_url(self) -> str:
        """
        Get the URL to download the recorded file.
        
        Returns:
            str: Download URL path.
        """
        return f'/podsinspace/static/recordings/{self.output_filename}'
    
    def cleanup(self):
        """Clean up recording resources."""
        if self.is_recording:
            self.stop()
        if self.process:
            try:
                self.process.terminate()
            except:
                pass


class RecordingManager:
    """Manages active stream recordings."""
    
    def __init__(self):
        self.recordings = {}  # Dictionary to store active recordings by ID
    
    def start_recording(self, stream_url: str, recording_id: Optional[str] = None) -> tuple[bool, str, Optional[str]]:
        """
        Start a new recording.
        
        Args:
            stream_url: URL of the MJPEG stream
            recording_id: Optional ID for the recording (defaults to timestamp)
        
        Returns:
            Tuple of (success: bool, message: str, recording_id: str or None)
        """
        if recording_id is None:
            recording_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if recording_id in self.recordings:
            return False, 'Recording with this ID already exists', None
        
        recorder = StreamRecorder(stream_url)
        if recorder.start():
            self.recordings[recording_id] = recorder
            return True, f'Recording started: {recording_id}', recording_id
        else:
            return False, 'Failed to start recording', None
    
    def stop_recording(self, recording_id: str) -> tuple[bool, str, Optional[str], int]:
        """
        Stop a recording.
        
        Args:
            recording_id: ID of the recording to stop
        
        Returns:
            Tuple of (success: bool, message: str, download_url: str or None, file_size: int)
        """
        if recording_id not in self.recordings:
            return False, 'Recording not found', None, 0
        
        recorder = self.recordings[recording_id]
        if recorder.stop():
            download_url = recorder.get_file_url()
            file_size = recorder.get_file_size()
            # Safely remove from dictionary
            self.recordings.pop(recording_id, None)
            return True, f'Recording stopped (size: {file_size} bytes)', download_url, file_size
        else:
            return False, 'Failed to stop recording', None, 0
    
    def get_recording_status(self, recording_id: str) -> dict:
        """
        Get status of a recording.
        
        Args:
            recording_id: ID of the recording
        
        Returns:
            Dictionary with status information.
        """
        if recording_id not in self.recordings:
            return {
                'status': 'not_found',
                'filename': None,
                'file_size': 0,
                'download_url': None
            }
        
        recorder = self.recordings[recording_id]
        return {
            'status': 'recording' if recorder.is_recording else 'stopped',
            'filename': recorder.output_filename,
            'file_size': recorder.get_file_size(),
            'download_url': recorder.get_file_url()
        }
    
    def cleanup_all(self):
        """Stop all active recordings and cleanup resources."""
        for recording_id, recorder in list(self.recordings.items()):
            recorder.cleanup()
            del self.recordings[recording_id]


# Global instance
recording_manager = RecordingManager()
