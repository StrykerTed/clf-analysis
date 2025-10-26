"""
CLF Analysis API Service
Provides RESTful API endpoints for running platform paths shape analysis
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import logging
from datetime import datetime
import threading
import uuid

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import GPU detection utility (logs device info on import)
from utils.device_utils import get_device, log_device_info

# Import the run_analysis function
from tools.get_platform_paths_shapes_shapely import run_analysis

app = Flask(__name__)

# Configure CORS to allow calls from defect-detect-fe (port 6200) and other services
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5176",
            "http://127.0.0.1:5176",
            "http://localhost:6200",
            "http://127.0.0.1:6200",
            "http://defect-detect-fe:6200"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Store for tracking running jobs
running_jobs = {}


def run_analysis_background(job_id, build_id, holes_interval, create_composite_views):
    """Run analysis in background thread and update job status"""
    try:
        logger.info(f"Starting background analysis for job {job_id}, build {build_id}")
        running_jobs[job_id]['status'] = 'running'
        
        # Run the analysis
        result = run_analysis(
            build_id=build_id,
            holes_interval=holes_interval,
            create_composite_views=create_composite_views
        )
        
        # Update job status
        if result.get('success'):
            running_jobs[job_id]['status'] = 'completed'
            running_jobs[job_id]['result'] = result
            logger.info(f"Job {job_id} completed successfully")
        else:
            running_jobs[job_id]['status'] = 'failed'
            running_jobs[job_id]['error'] = result.get('error', 'Unknown error')
            logger.error(f"Job {job_id} failed: {result.get('error')}")
            
    except Exception as e:
        logger.exception(f"Job {job_id} error: {str(e)}")
        running_jobs[job_id]['status'] = 'failed'
        running_jobs[job_id]['error'] = str(e)


@app.route('/')
def home():
    """Root endpoint with API information"""
    return jsonify({
        'service': 'CLF Analysis API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'analyze': '/api/analyze',
            'analyze_by_build': '/api/builds/<build_id>/analyze'
        }
    })


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'clf-abp-path-analysis',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Trigger CLF analysis with provided parameters (async)
    
    Request Body (JSON):
    {
        "build_id": "271360",
        "holes_interval": 10,
        "create_composite_views": false
    }
    
    Response (immediate):
    {
        "status": "accepted",
        "job_id": "uuid",
        "message": "Analysis started"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body must be JSON'
            }), 400
        
        # Extract parameters with defaults
        build_id = data.get('build_id')
        holes_interval = data.get('holes_interval', 10)
        create_composite_views = data.get('create_composite_views', False)
        
        # Validate build_id
        if not build_id:
            return jsonify({
                'status': 'error',
                'message': 'build_id is required'
            }), 400
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job tracking
        running_jobs[job_id] = {
            'job_id': job_id,
            'build_id': build_id,
            'status': 'queued',
            'started_at': datetime.now().isoformat(),
            'holes_interval': holes_interval,
            'create_composite_views': create_composite_views
        }
        
        logger.info(f"Created job {job_id} for build_id: {build_id}")
        
        # Start analysis in background thread
        thread = threading.Thread(
            target=run_analysis_background,
            args=(job_id, build_id, holes_interval, create_composite_views)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediately with job ID
        return jsonify({
            'status': 'accepted',
            'job_id': job_id,
            'build_id': build_id,
            'message': f'Analysis started for build {build_id}',
            'check_status_url': f'/api/jobs/{job_id}'
        }), 202
            
    except Exception as e:
        logger.exception(f"Unexpected error in analyze endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500


@app.route('/api/builds/<build_id>/analyze', methods=['POST'])
def analyze_by_build(build_id):
    """
    Trigger CLF analysis for a specific build (async)
    
    URL Parameter:
        build_id: The build ID to analyze (e.g., "271360")
    
    Request Body (JSON, optional):
    {
        "holes_interval": 10,
        "create_composite_views": false
    }
    
    Response (immediate):
    {
        "status": "accepted",
        "job_id": "uuid",
        "message": "Analysis started"
    }
    """
    try:
        # Get optional parameters from request body
        data = request.get_json() or {}
        
        holes_interval = data.get('holes_interval', 10)
        create_composite_views = data.get('create_composite_views', False)
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job tracking
        running_jobs[job_id] = {
            'job_id': job_id,
            'build_id': build_id,
            'status': 'queued',
            'started_at': datetime.now().isoformat(),
            'holes_interval': holes_interval,
            'create_composite_views': create_composite_views
        }
        
        logger.info(f"Created job {job_id} for build_id: {build_id}")
        
        # Start analysis in background thread
        thread = threading.Thread(
            target=run_analysis_background,
            args=(job_id, build_id, holes_interval, create_composite_views)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediately with job ID
        return jsonify({
            'status': 'accepted',
            'job_id': job_id,
            'build_id': build_id,
            'message': f'Analysis started for build {build_id}',
            'check_status_url': f'/api/jobs/{job_id}'
        }), 202
            
    except Exception as e:
        logger.exception(f"Unexpected error in analyze_by_build endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """
    Get the status of a running or completed job
    
    Response:
    {
        "job_id": "uuid",
        "build_id": "271360",
        "status": "running|completed|failed",
        "started_at": "2025-10-08T...",
        "result": { ... } // only if completed
    }
    """
    if job_id not in running_jobs:
        return jsonify({
            'status': 'error',
            'message': 'Job not found'
        }), 404
    
    job_info = running_jobs[job_id].copy()
    
    return jsonify({
        'status': 'success',
        'job': job_info
    })


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """
    List all jobs (running and completed)
    
    Response:
    {
        "status": "success",
        "jobs": [ ... ]
    }
    """
    return jsonify({
        'status': 'success',
        'jobs': list(running_jobs.values()),
        'count': len(running_jobs)
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.exception("Internal server error")
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6300))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    
    logger.info(f"Starting CLF Analysis API on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
