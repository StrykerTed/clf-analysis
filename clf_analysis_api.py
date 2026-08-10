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

# Cross-process lock over the build's derived artifacts - the collision the in-process
# admission guard cannot see, because it is with a different service entirely.
from utils.build_lock import build_write_lock, BuildLocked

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


# ---------------------------------------------------------------------------
# Single-flight admission
# ---------------------------------------------------------------------------
# Both analyse routes accepted unconditionally and started a daemon thread, and
# `run_analysis` opens by wiping the build's output directory:
# `create_directory_structure(..., clear_existing=True)` rmtrees
# <build>/clf_analysis wholesale, and `setup_abp_folders` rmtrees and
# re-extracts the ABP contents directory. A second analysis of the same build
# therefore deletes the first one's outputs while it is still writing them,
# and re-extracts the ABP the first one is still reading.
#
# This was originally guarded *per build*, on the reasoning that "this pipeline
# holds no module-level mutable state and writes only under its own build, so
# two different builds are genuinely independent". That reasoning was wrong.
# Running it disproved it: matplotlib's pyplot IS module-level mutable state,
# and every job in this process shares it.
#
# `utils/platform_analysis/visualization_utils.py` drives pyplot through its
# module-level API in 86 places, and `save_platform_figure(plt, path)` is handed
# the *module*, so it saves whichever figure is globally current rather than one
# it owns. On 10 Aug 2026 three builds were analysed concurrently for the first
# time and two of the six plate-registered PNGs came back holding a different
# render entirely: 515415's identifier view contained a Combined Holes view at
# 4426x3831, and 515357's WITH_NO_ID view was 3727x3829, where both are required
# to be exactly 2100x2100. The 3D floor textures a 210mm plane with that file at
# its word, so the corruption reached the UI as a misregistered floor.
#
# So the slot is now global - one analysis at a time, whatever the build. The
# rule this service teaches is the one the alignment service already taught with
# its process-global environment variables: ask what two jobs *share*, not what
# folder they write to. A per-build lock cannot see a shared figure registry,
# and neither can the cross-service flock on <build>/.clf_analysis.lock, which
# guards the filesystem.
#
# The narrower fix - give every view its own Figure and never touch global
# pyplot state - is the better long-term answer and would allow concurrent
# builds again. It is 86 call sites, so it is deliberately not bundled here.
# Until it lands, serialising is what makes the output trustworthy.
#
# This also removes a performance problem that was previously tolerated:
# `run_analysis` sizes its multiprocessing Pool to
# min(cpu_count(), len(valid_files)), so concurrent builds each claimed every
# core and all of them crawled.
_admission_lock = threading.Lock()
_active_builds = {}  # build_id -> {'job_id': str, 'thread': Thread | None}


def _claim_build_slot(build_id, job_id):
    """Claim the one analysis slot for `job_id`.

    Returns None when claimed, or `(holder_build_id, holder_job_id)` when any
    analysis is already running - including one on a different build, because
    concurrent builds share this process's pyplot state. See the note above.

    A slot whose worker thread has died is reclaimed rather than blocking the
    service forever; a slot held by a slow but living thread is kept, which is
    the entire point of the guard.
    """
    with _admission_lock:
        for held_build, holder in list(_active_builds.items()):
            thread = holder['thread']
            if thread is not None and not thread.is_alive():
                logger.warning(
                    "Reclaiming slot for build %s from job %s - its worker "
                    "thread is no longer alive", held_build, holder['job_id']
                )
                del _active_builds[held_build]
                continue
            # thread is None only in the moment between claiming the slot
            # and starting the worker, which is a real in-flight job.
            return held_build, holder['job_id']
        _active_builds[build_id] = {'job_id': job_id, 'thread': None}
        return None


def _attach_build_thread(build_id, job_id, thread):
    """Record the worker thread so a dead one can be detected later."""
    with _admission_lock:
        holder = _active_builds.get(build_id)
        if holder is not None and holder['job_id'] == job_id:
            holder['thread'] = thread


def _release_build_slot(build_id, job_id):
    """Release the slot if `job_id` still holds it."""
    with _admission_lock:
        holder = _active_builds.get(build_id)
        if holder is not None and holder['job_id'] == job_id:
            del _active_builds[build_id]


def _build_in_progress_response(build_id, holder_build_id, holder_job_id):
    """Refuse a second analysis, naming the job that holds the slot.

    The holder may be a *different* build, so say which one - "already being
    analysed" about a build the caller did not ask for reads as a bug unless
    the message explains itself.
    """
    holder = running_jobs.get(holder_job_id, {})
    logger.warning(
        "Refusing analysis of build %s - job %s is already analysing build %s",
        build_id, holder_job_id, holder_build_id
    )
    if str(holder_build_id) == str(build_id):
        message = (
            f"Build {build_id} is already being analysed (job {holder_job_id}). "
            f"Starting a second one would delete this one's output directory "
            f"while it is still writing to it. Wait for it to finish, then retry."
        )
    else:
        message = (
            f"Build {holder_build_id} is being analysed (job {holder_job_id}), and "
            f"this service runs one analysis at a time. Concurrent builds share "
            f"this process's matplotlib state and corrupt each other's "
            f"plate-registered images. Wait for it to finish, then retry "
            f"build {build_id}."
        )
    return jsonify({
        'status': 'error',
        'message': message,
        'active_job_id': holder_job_id,
        'active_build_id': holder_build_id,
        'requested_build_id': build_id,
        'active_started_at': holder.get('started_at'),
        'check_status_url': f'/api/jobs/{holder_job_id}'
    }), 409


def _start_analysis_job(build_id, holes_interval, create_composite_views):
    """Admit and start one analysis job for `build_id`.

    Returns (job_id, None) when started, or (None, response) when refused -
    both routes share this so admission cannot be enforced in one and
    forgotten in the other.
    """
    job_id = str(uuid.uuid4())

    holder = _claim_build_slot(build_id, job_id)
    if holder is not None:
        holder_build_id, holder_job_id = holder
        return None, _build_in_progress_response(build_id, holder_build_id, holder_job_id)

    try:
        running_jobs[job_id] = {
            'job_id': job_id,
            'build_id': build_id,
            'status': 'queued',
            'started_at': datetime.now().isoformat(),
            'holes_interval': holes_interval,
            'create_composite_views': create_composite_views
        }

        logger.info(f"Created job {job_id} for build_id: {build_id}")

        thread = threading.Thread(
            target=run_analysis_background,
            args=(job_id, build_id, holes_interval, create_composite_views)
        )
        thread.daemon = True
        thread.start()
        _attach_build_thread(build_id, job_id, thread)
    except BaseException:
        # Nothing is running, so holding the slot would block this build for
        # the lifetime of the process.
        _release_build_slot(build_id, job_id)
        raise

    return job_id, None


def run_analysis_background(job_id, build_id, holes_interval, create_composite_views):
    """Run analysis in background thread and update job status"""
    try:
        logger.info(f"Starting background analysis for job {job_id}, build {build_id}")
        running_jobs[job_id]['status'] = 'running'

        # Hold the build's cross-process write lock for the WHOLE analysis, not just
        # the rmtree at the start. _claim_build_slot above stops *this* service running
        # two analyses of one build; it cannot stop layer-alignments or defect-detect
        # reading platform_layer_pathdata_*.json out of a directory this run is midway
        # through deleting and rewriting, because a dict in this process is invisible
        # to theirs. See utils/build_lock.py for why the lock file is a sibling of
        # clf_analysis rather than inside it.
        build_path = os.path.join(
            os.getenv("MIDAS_BASE_PATH", "/midas_data"), str(build_id)
        )
        hint = f"clf-analysis job {job_id} started {datetime.now().isoformat(timespec='seconds')}"
        with build_write_lock(build_path, hint=hint):
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
            
    except BuildLocked as e:
        # Another process holds this build - almost certainly an analysis reading the
        # artifacts we are about to delete. Fail with the holder named rather than
        # deleting under it, and say so in terms someone can act on.
        logger.warning(f"Job {job_id} refused: {e}")
        running_jobs[job_id]['status'] = 'failed'
        running_jobs[job_id]['error'] = str(e)

    except Exception as e:
        logger.exception(f"Job {job_id} error: {str(e)}")
        running_jobs[job_id]['status'] = 'failed'
        running_jobs[job_id]['error'] = str(e)

    finally:
        # Must be `finally`: a raise lands in the handler above, and a failed
        # analysis still has to hand the build back or nothing can re-run it
        # until the service is restarted.
        _release_build_slot(build_id, job_id)


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
        
        # One analysis per build at a time - see _claim_build_slot.
        job_id, refusal = _start_analysis_job(
            build_id, holes_interval, create_composite_views
        )
        if refusal is not None:
            return refusal
        
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
        
        # One analysis per build at a time - see _claim_build_slot.
        job_id, refusal = _start_analysis_job(
            build_id, holes_interval, create_composite_views
        )
        if refusal is not None:
            return refusal
        
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
