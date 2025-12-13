/**
 * Stream Recorder Module
 * Handles server-side MJPEG stream recording to MP4
 */

document.addEventListener('DOMContentLoaded', function() {
  const recordBtn = document.getElementById('recordBtn');
  const downloadBtn = document.getElementById('downloadBtn');
  const recordingTimer = document.getElementById('recordingTimer');
  
  let recordingId = null;
  let isRecording = false;
  let recordingStartTime = null;
  let timerInterval = null;

  /**
   * Update recording timer display
   */
  function updateTimer() {
    if (!recordingStartTime) return;
    
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    recordingTimer.textContent = timeStr;
  }

  /**
   * Start recording timer
   */
  function startTimer() {
    recordingStartTime = Date.now();
    recordingTimer.style.display = 'block';
    updateTimer();
    
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(updateTimer, 1000);
  }

  /**
   * Stop recording timer
   */
  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
    recordingStartTime = null;
    recordingTimer.style.display = 'none';
    recordingTimer.textContent = '00:00';
  }

  /**
   * Start server-side stream recording
   */
  async function startRecording() {
    // Get the upstream camera URL from the image's data attribute
    const imgElement = document.getElementById('live-stream-img');
    const streamUrl = imgElement.getAttribute('data-camera-url');
    
    if (!streamUrl) {
      alert('Error: Camera URL not configured');
      return;
    }
    
    try {
      const response = await fetch('/podsinspace/recording/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stream_url: streamUrl,
          recording_id: null  // Server generates ID
        })
      });
      
      // Check if response is OK and is JSON
      if (!response.ok) {
        let errorMsg = `HTTP ${response.status}: `;
        try {
          const errorData = await response.json();
          errorMsg += errorData.message || 'Unknown error';
        } catch {
          errorMsg += response.statusText || 'Unknown error';
        }
        alert('Failed to start recording: ' + errorMsg);
        return;
      }
      
      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        console.error('Failed to parse JSON response:', parseError);
        alert('Error starting recording: Invalid response from server (JSON parse error)');
        return;
      }
      
      if (data.success) {
        recordingId = data.recording_id;
        isRecording = true;
        
        // Start the recording timer
        startTimer();
        
        // Update button UI
        recordBtn.classList.remove('btn-light');
        recordBtn.classList.add('btn-danger');
        recordBtn.innerHTML = '<i class="bi bi-stop-circle-fill"></i> Stop Recording';
        recordBtn.disabled = false;
        
        // Start monitoring status
        monitorRecordingStatus();
        
        console.log('Recording started:', recordingId);
      } else {
        alert('Failed to start recording: ' + (data.message || 'Unknown error'));
      }
    } catch (error) {
      alert('Error starting recording: ' + error.message);
      console.error('Start recording error:', error);
    }
  }

  /**
   * Stop server-side stream recording
   */
  async function stopRecording() {
    if (!recordingId) {
      alert('No active recording');
      return;
    }
    
    // Disable the button to prevent multiple clicks
    recordBtn.disabled = true;
    
    try {
      const response = await fetch(`/podsinspace/recording/stop/${recordingId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      // Check if response is OK first
      if (!response.ok) {
        let errorMsg = `HTTP ${response.status}: `;
        try {
          const errorData = await response.json();
          errorMsg += errorData.message || 'Unknown error';
        } catch {
          errorMsg += response.statusText || 'Unknown error';
        }
        alert('Failed to stop recording: ' + errorMsg);
        recordBtn.disabled = false;
        return;
      }
      
      // Parse the JSON response
      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        console.error('Failed to parse JSON response:', parseError);
        alert('Error stopping recording: Invalid response from server (JSON parse error)');
        recordBtn.disabled = false;
        return;
      }
      
      // Handle the response
      if (data.success) {
        isRecording = false;
        recordingId = null;  // Clear the recording ID
        
        // Stop the recording timer
        stopTimer();
        
        // Update button UI
        recordBtn.classList.add('btn-light');
        recordBtn.classList.remove('btn-danger');
        recordBtn.innerHTML = '<i class="bi bi-circle-fill" style="color: red;"></i> Record';
        recordBtn.disabled = false;
        
        // Enable download button
        downloadBtn.disabled = false;
        downloadBtn.classList.add('btn-success');
        downloadBtn.dataset.downloadUrl = data.download_url;
        downloadBtn.dataset.filename = data.download_url.split('/').pop();
        
        // Get file size from response (in bytes), convert to MB
        const fileSizeMB = (data.file_size / 1024 / 1024).toFixed(2);
        alert(`Recording complete!\nFile size: ${fileSizeMB} MB`);
        console.log('Recording stopped:', data);
      } else {
        alert('Failed to stop recording: ' + (data.message || 'Unknown error'));
        recordBtn.disabled = false;
      }
    } catch (error) {
      alert('Error stopping recording: ' + error.message);
      console.error('Stop recording error:', error);
      recordBtn.disabled = false;
    }
  }

  /**
   * Monitor recording status periodically
   */
  function monitorRecordingStatus() {
    if (!isRecording || !recordingId) return;
    
    fetch(`/podsinspace/recording/status/${recordingId}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: Failed to get status`);
        }
        return response.json();
      })
      .then(data => {
        if (data.status === 'recording') {
          // Update download button with current file size
          const fileSizeMB = (data.file_size / 1024 / 1024).toFixed(2);
          downloadBtn.title = `File size: ${fileSizeMB} MB`;
          
          // Check again in 2 seconds
          setTimeout(monitorRecordingStatus, 2000);
        }
      })
      .catch(error => console.error('Status check error:', error));
  }



  /**
   * Download recorded file
   */
  async function downloadRecording() {
    const downloadUrl = downloadBtn.dataset.downloadUrl;
    const filename = downloadBtn.dataset.filename;
    
    if (!downloadUrl || !filename) {
      alert('No recording available to download');
      return;
    }
    
    try {
      const response = await fetch(downloadUrl);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      console.log('Download initiated:', filename);
      
      // Delete the file after successful download
      deleteRecording(filename);
    } catch (error) {
      alert('Error downloading file: ' + error.message);
      console.error('Download error:', error);
    }
  }

  /**
   * Delete a recorded file
   */
  async function deleteRecording(filename) {
    try {
      const response = await fetch(`/podsinspace/recording/delete/${filename}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('Failed to delete file:', errorData.message);
        return;
      }
      
      const data = await response.json();
      if (data.success) {
        console.log('Recording file deleted:', filename);
        
        // Reset download button
        downloadBtn.disabled = true;
        downloadBtn.classList.remove('btn-success');
        downloadBtn.dataset.downloadUrl = '';
        downloadBtn.dataset.filename = '';
        downloadBtn.title = '';
      } else {
        console.error('Failed to delete file:', data.message);
      }
    } catch (error) {
      console.error('Error deleting file:', error);
    }
  }

  /**
   * Handle record button click
   */
  recordBtn.addEventListener('click', function() {
    if (!isRecording) {
      startRecording();
    } else {
      stopRecording();
    }
  });

  /**
   * Handle download button click
   */
  downloadBtn.addEventListener('click', function() {
    downloadRecording();
  });
});
