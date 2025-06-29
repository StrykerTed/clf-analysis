from flask import Flask, render_template, jsonify, request
import os
import re
import time
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

@app.route('/api/builds/<build_number>/analyze', methods=['POST'])
def analyze_build(build_number):
    """Analyze a specific build with height parameter"""
    try:
        # Get JSON data from request
        data = request.get_json() if request.is_json else {}
        height_mm = data.get('height_mm', 0)
        build_folder = data.get('build_folder', '')
        identifiers = data.get('identifiers', None)  # New: identifier filter
        
        # Validate height
        if not isinstance(height_mm, (int, float)) or height_mm < 0 or height_mm > 9999.99:
            return jsonify({
                'status': 'error',
                'message': 'Invalid height value. Must be between 0 and 9999.99 mm'
            }), 400
        
        # Find the build folder
        actual_build_folder = None
        if os.path.exists(ABP_CONTENTS_PATH):
            for folder in os.listdir(ABP_CONTENTS_PATH):
                if f'build' in folder.lower() and build_number in folder:
                    actual_build_folder = folder
                    break
        
        if not actual_build_folder:
            return jsonify({
                'status': 'error',
                'message': f'Build {build_number} not found'
            }), 404
        
        # Get the full path to the build folder
        build_folder_path = os.path.join(ABP_CONTENTS_PATH, actual_build_folder)
        
        # Import and use the CLF analysis wrapper
        from clf_analysis_wrapper import analyze_build_for_web
        
        print(f"Starting CLF analysis for build {build_number} at height {height_mm}mm")
        if identifiers:
            print(f"Filtering to identifiers: {identifiers}")
        
        # Perform the actual CLF analysis
        analysis_results = analyze_build_for_web(
            build_folder_path=build_folder_path,
            height_mm=height_mm,
            exclude_folders=True,  # Always exclude folders for web analysis
            identifiers=identifiers  # New: pass identifier filter
        )
        
        # Check if analysis was successful
        if "error" in analysis_results:
            return jsonify({
                'status': 'error',
                'message': f'Analysis failed: {analysis_results["error"]}',
                'build_number': build_number,
                'height_mm': height_mm
            }), 500
        
        # Cleanup temporary files (optional - could be done async)
        try:
            from clf_analysis_wrapper import CLFWebAnalyzer
            analyzer = CLFWebAnalyzer()
            analyzer.cleanup_temp_files(analysis_results.get("temp_directory", ""))
        except Exception as cleanup_error:
            print(f"Warning: Cleanup failed: {cleanup_error}")
        
        # Prepare response with visualization data
        response_data = {
            'status': 'success',
            'message': f'Analysis completed for Build {build_number}',
            'build_folder': actual_build_folder,
            'build_number': build_number,
            'height_mm': height_mm,
            'analysis_id': f"{build_number}_{height_mm}_{int(time.time())}",
            'timestamp': analysis_results.get('timestamp'),
            'files_processed': analysis_results.get('files_processed', 0),
            'files_excluded': analysis_results.get('files_excluded', 0),
            'total_files_found': analysis_results.get('total_files_found', 0),
            'visualizations': analysis_results.get('visualizations', {})
        }
        
        print(f"Analysis completed successfully. Processed {response_data['files_processed']} files.")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in analyze_build endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Analysis error: {str(e)}',
            'build_number': build_number if 'build_number' in locals() else 'unknown',
            'height_mm': height_mm if 'height_mm' in locals() else 0
        }), 500
        return jsonify({
            'status': 'success',
            'message': f'Analysis started for Build {build_number}',
            'build_folder': actual_build_folder,
            'build_number': build_number,
            'height_mm': height_mm,
            'analysis_id': f"{build_number}_{height_mm}_{int(time.time())}"
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
