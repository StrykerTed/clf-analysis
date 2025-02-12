import logging
import os
import json
from datetime import datetime 
import sys

logger = logging.getLogger(__name__)

def should_skip_folder(folder_name, patterns):
    """Check if folder should be skipped based on patterns"""
    # Print debug info
    print(f"Checking folder: '{folder_name}'")
    
    # Keep original case and just fix spaces
    normalized_folder = folder_name.replace(' ', '_')
    
    print(f"Looking for patterns: {patterns}")
    
    # Check each pattern exactly as it appears in the JSON
    for pattern in patterns:
        if pattern in normalized_folder:
            print(f"Found match with pattern: '{pattern}'")
            return True
            
    print("No patterns matched")
    return False

def load_exclusion_patterns(script_dir):
    """Load folder exclusion patterns from JSON file"""
    try:
        json_path = os.path.join(script_dir, 'folder_exclusions.json')
        
        with open(json_path, 'r') as f:
            data = json.load(f)
            return data['excluded_folder_patterns']
            
    except FileNotFoundError:
        print(f"ERROR: folder_exclusions.json not found at {json_path}")
        print("This file is required for program operation.")
        sys.exit(1)  # Exit with error code 1
    except Exception as e:
        print(f"ERROR: Failed to load folder_exclusions.json: {str(e)}")
        print("This file is required for program operation.")
        sys.exit(1)  # Exit with error code 1
        
def find_clf_files(build_dir):
    """Find all CLF files in the build directory structure"""
    clf_files = []
    models_dir = os.path.join(build_dir, "Models")
    
    if not os.path.exists(models_dir):
        print(f"Models directory not found at: {models_dir}")
        return clf_files
        
    print(f"Scanning directory: {models_dir}")
    
    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file.endswith('.clf'):
                full_path = os.path.join(root, file)
                rel_folder = os.path.relpath(root, models_dir)
                clf_files.append({
                    'path': full_path,
                    'folder': rel_folder,
                    'name': file
                })
                # print(f"Found CLF file: {file} in {rel_folder}")
    
    return clf_files


def create_output_folder(abpfoldername, base_dir, save_layer_partials, alignment_style_only):
    
    if save_layer_partials:
        layer_partials_dir = os.path.join(base_dir, "layer_partials")
        os.makedirs(layer_partials_dir, exist_ok=True)
        print(f"Created layer partials directory: {layer_partials_dir}")
        
    """Create output folder with datetime and visualization subfolders"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    my_outputs_dir = os.path.join(base_dir, "my_outputs", "get_platform_paths_shapes_shapely", timestamp, abpfoldername)
    if alignment_style_only:
        my_outputs_dir += "-crosscrossonly" 
    os.makedirs(my_outputs_dir, exist_ok=True)
    
    layer_partials_dir = os.path.join(my_outputs_dir, "layer_partials")
    composite_platforms_dir = os.path.join(my_outputs_dir, "composite_platforms")
    identifier_views_dir = os.path.join(my_outputs_dir, "identifier_views")
    
    clean_platforms_dir = os.path.join(my_outputs_dir, "clean_platforms")  # NEW
    os.makedirs(clean_platforms_dir, exist_ok=True)  # NEW
    print(f"Created clean platforms directory: {clean_platforms_dir}")  # NEW
    
    os.makedirs(layer_partials_dir, exist_ok=True)
    os.makedirs(composite_platforms_dir, exist_ok=True)
    os.makedirs(identifier_views_dir, exist_ok=True)
    
    print(f"Created output directory: {my_outputs_dir}")
    print(f"Created layer partials directory: {layer_partials_dir}")
    print(f"Created composite platforms directory: {composite_platforms_dir}")
    print(f"Created identifier views directory: {identifier_views_dir}")
    
    return my_outputs_dir