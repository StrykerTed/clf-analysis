from flask import Flask, render_template, jsonify
import os
import re
from pathlib import Path

app = Flask(__name__)

# Configuration
ABP_CONTENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'abp_contents')

@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/health')
def health():
    return {'status': 'ok', 'message': 'Flask app is running'}

@app.route('/api/builds')
def get_available_builds():
    """Get list of available ABP build folders"""
    builds = []
    
    try:
        if os.path.exists(ABP_CONTENTS_PATH):
            for folder in os.listdir(ABP_CONTENTS_PATH):
                folder_path = os.path.join(ABP_CONTENTS_PATH, folder)
                if os.path.isdir(folder_path):
                    # Look for folders containing 'build-' or 'build '
                    if 'build' in folder.lower():
                        # Extract build number
                        build_match = re.search(r'build[-\s]*(\d+)', folder, re.IGNORECASE)
                        if build_match:
                            build_number = build_match.group(1)
                            
                            # Check if Complete folder exists (indicates processed build)
                            complete_path = os.path.join(folder_path, 'Complete')
                            models_path = os.path.join(folder_path, 'Models')
                            
                            build_info = {
                                'folder_name': folder,
                                'build_number': build_number,
                                'display_name': f"Build {build_number}",
                                'path': folder_path,
                                'has_complete': os.path.exists(complete_path),
                                'has_models': os.path.exists(models_path),
                                'status': 'Complete' if os.path.exists(complete_path) else 'Processing'
                            }
                            builds.append(build_info)
        
        # Sort by build number
        builds.sort(key=lambda x: int(x['build_number']), reverse=True)
        
        return jsonify({
            'status': 'success',
            'builds': builds,
            'count': len(builds)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'builds': [],
            'count': 0
        }), 500

@app.route('/api/builds/<build_number>/analyze')
def analyze_build(build_number):
    """Analyze a specific build (placeholder for future implementation)"""
    try:
        # Find the build folder
        build_folder = None
        if os.path.exists(ABP_CONTENTS_PATH):
            for folder in os.listdir(ABP_CONTENTS_PATH):
                if f'build' in folder.lower() and build_number in folder:
                    build_folder = folder
                    break
        
        if not build_folder:
            return jsonify({
                'status': 'error',
                'message': f'Build {build_number} not found'
            }), 404
        
        # Placeholder response
        return jsonify({
            'status': 'success',
            'message': f'Analysis started for Build {build_number}',
            'build_folder': build_folder,
            'build_number': build_number
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
