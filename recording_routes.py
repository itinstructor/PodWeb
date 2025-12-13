"""
Stream recording API routes for blog blueprint.
Handles starting, stopping, and checking status of stream recordings.
"""

from flask import Blueprint, request, jsonify, send_file, session
from functools import wraps
import logging
import os

from stream_recorder import recording_manager

logger = logging.getLogger(__name__)

# Create blueprint for recording routes
recording_bp = Blueprint('recording', __name__)


# Health check endpoint (no auth required)
@recording_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check to verify the blueprint is loaded."""
    return jsonify({'status': 'ok', 'blueprint': 'recording'})


def login_required_json(f):
    """Decorator to require login for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            response = jsonify({'success': False, 'message': 'Unauthorized - please log in'})
            response.status_code = 401
            response.headers['Content-Type'] = 'application/json'
            return response
        return f(*args, **kwargs)
    return decorated_function


@recording_bp.route('/start', methods=['POST'])
@login_required_json
def start_recording():
    """
    Start recording a stream.
    
    Request JSON:
    {
        "stream_url": "http://localhost:8080/stream.mjpg",
        "recording_id": "optional_id"
    }
    
    Response:
    {
        "success": bool,
        "message": str,
        "recording_id": str or null
    }
    """
    try:
        data = request.get_json() or {}
        stream_url = data.get('stream_url')
        recording_id = data.get('recording_id')
        
        if not stream_url:
            response = jsonify({
                'success': False,
                'message': 'stream_url is required'
            })
            response.status_code = 400
            response.headers['Content-Type'] = 'application/json'
            return response
        
        success, message, rid = recording_manager.start_recording(stream_url, recording_id)
        
        response = jsonify({
            'success': success,
            'message': message,
            'recording_id': rid
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as e:
        logger.error(f'Error in start_recording: {str(e)}')
        response = jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        })
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        return response


@recording_bp.route('/stop/<recording_id>', methods=['POST'])
@login_required_json
def stop_recording(recording_id):
    """
    Stop recording.
    
    Response:
    {
        "success": bool,
        "message": str,
        "download_url": str or null,
        "file_size": int
    }
    """
    try:
        success, message, download_url, file_size = recording_manager.stop_recording(recording_id)
        
        response = jsonify({
            'success': success,
            'message': message,
            'download_url': download_url,
            'file_size': file_size
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as e:
        logger.error(f'Error in stop_recording: {str(e)}')
        response = jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        })
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        return response


@recording_bp.route('/status/<recording_id>', methods=['GET'])
@login_required_json
def get_status(recording_id):
    """
    Get status of a recording.
    
    Response:
    {
        "status": "recording|stopped|not_found",
        "filename": str,
        "file_size": int,
        "download_url": str
    }
    """
    try:
        status = recording_manager.get_recording_status(recording_id)
        response = jsonify(status)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as e:
        logger.error(f'Error in get_status: {str(e)}')
        response = jsonify({
            'status': 'error',
            'message': str(e)
        })
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        return response


@recording_bp.route('/download/<filename>', methods=['GET'])
@login_required_json
def download_recording(filename):
    """
    Download a recorded file.
    
    Args:
        filename: Name of the file to download
    """
    try:
        # Security: validate filename doesn't contain path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        recordings_dir = os.path.join(
            os.path.dirname(__file__), 
            'static', 
            'recordings'
        )
        file_path = os.path.join(recordings_dir, filename)
        
        # Verify file exists and is in recordings directory
        if not os.path.exists(file_path) or not os.path.abspath(file_path).startswith(
            os.path.abspath(recordings_dir)
        ):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
    
    except Exception as e:
        logger.error(f'Error in download_recording: {str(e)}')
        return jsonify({'error': str(e)}), 500


@recording_bp.route('/delete/<filename>', methods=['POST'])
@login_required_json
def delete_recording(filename):
    """
    Delete a recorded file.
    
    Args:
        filename: Name of the file to delete
    
    Response:
    {
        "success": bool,
        "message": str
    }
    """
    try:
        # Security: validate filename doesn't contain path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            response = jsonify({
                'success': False,
                'message': 'Invalid filename'
            })
            response.status_code = 400
            response.headers['Content-Type'] = 'application/json'
            return response
        
        recordings_dir = os.path.join(
            os.path.dirname(__file__), 
            'static', 
            'recordings'
        )
        file_path = os.path.join(recordings_dir, filename)
        
        # Verify file exists and is in recordings directory
        if not os.path.exists(file_path) or not os.path.abspath(file_path).startswith(
            os.path.abspath(recordings_dir)
        ):
            response = jsonify({
                'success': False,
                'message': 'File not found'
            })
            response.status_code = 404
            response.headers['Content-Type'] = 'application/json'
            return response
        
        # Delete the file
        os.remove(file_path)
        logger.info(f'Deleted recording file: {filename}')
        
        response = jsonify({
            'success': True,
            'message': f'File {filename} deleted successfully'
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as e:
        logger.error(f'Error in delete_recording: {str(e)}')
        response = jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        })
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        return response
