#!/usr/bin/env python3
"""
Test program to visualize only skin files at a specific height.
This uses the new only_skin_files flag in create_clean_platform.
"""

import os
import sys
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from utils.myfuncs.file_utils import find_clf_files, should_skip_folder
from utils.platform_analysis.visualization_utils import create_clean_platform, create_clean_platform_skin_only_enhanced
sys.path.insert(0, str(src_path))

from utils.platform_analysis.visualization_utils import create_clean_platform, create_clean_platform_skin_only
from utils.myfuncs.file_utils import should_skip_folder


def get_clf_files_from_directory(build_dir):
    """Get all CLF files from the build directory with folder information"""
    clf_files = []
    
    models_dir = os.path.join(build_dir, "Models")
    if not os.path.exists(models_dir):
        print(f"Models directory not found: {models_dir}")
        return clf_files
    
    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file.endswith('.clf'):
                full_path = os.path.join(root, file)
                folder_name = os.path.basename(root)
                
                clf_info = {
                    'name': file,
                    'path': full_path,
                    'folder': folder_name
                }
                clf_files.append(clf_info)
    
    return clf_files


def apply_exclusions(clf_files, exclusion_patterns):
    """Apply exclusion patterns to filter out unwanted files"""
    excluded_files = []
    
    for clf_info in clf_files:
        folder_name = clf_info['folder']
        filename = clf_info['name']
        
        # Check if folder should be skipped
        if should_skip_folder(folder_name, exclusion_patterns):
            excluded_files.append(clf_info)
            continue
            
        # Check if filename should be skipped (like WaferSupport.clf)
        if filename == 'WaferSupport.clf':
            excluded_files.append(clf_info)
            continue
    
    excluded_paths = {info['path'] for info in excluded_files}
    
    # Filter out excluded files
    filtered_files = [clf_info for clf_info in clf_files if clf_info['path'] not in excluded_paths]
    
    print(f"Found {len(clf_files)} CLF files total")
    print(f"Excluded {len(excluded_files)} files based on folder patterns")
    print(f"Processing {len(filtered_files)} CLF files")
    
    return filtered_files


def main():
    HEIGHT = 134.0  # Test height
    
    print(f"Testing skin files only at height {HEIGHT}mm")
    
    # Set up paths
    BUILD_DIR = "abp_contents/preprocess build-424292"
    OUTPUT_DIR = "my_outputs/skin_files_test"
    
    print(f"Build directory: {BUILD_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Hardcoded exclusion patterns (same as main program)
    exclusion_patterns = [
        '_Support', 'supports', 'SUPPORTS', 'Supports', 
        'ebm-ti64', 'Porous', 'Cylinder', 'Support', 
        'Coupon', 's_Skin'
    ]
    
    print(f"Loaded exclusion patterns: {exclusion_patterns}")
    
    # Get project root and build path
    project_root = os.getcwd()
    build_path = os.path.join(project_root, BUILD_DIR)
    
    if not os.path.exists(build_path):
        print(f"Error: Build directory does not exist: {build_path}")
        return
    
    print(f"Scanning directory: {build_path}/Models")
    
    # Get all CLF files
    clf_files = get_clf_files_from_directory(build_path)
    
    if not clf_files:
        print("No CLF files found!")
        return
    
    # Apply exclusions
    filtered_files = apply_exclusions(clf_files, exclusion_patterns)
    
    if not filtered_files:
        print("No CLF files remaining after exclusions!")
        return
    
    # Show what skin files we have before filtering
    skin_files = [f for f in filtered_files if 'skin' in f['folder'].lower()]
    print(f"\nSkin files found: {len(skin_files)} out of {len(filtered_files)} total files")
    for skin_file in skin_files[:5]:  # Show first 5 examples
        print(f"  - {skin_file['name']} in {skin_file['folder']}")
    if len(skin_files) > 5:
        print(f"  ... and {len(skin_files) - 5} more")
    
    if len(skin_files) == 0:
        print("  No skin files found - checking all folder names for debug:")
        for i, f in enumerate(filtered_files[:10]):
            print(f"  {i+1}: {f['name']} in {f['folder']}")
        return
    
    # Test 1: All files (existing behavior)
    print(f"\n=== Test 1: All files ===")
    try:
        output_path_all = os.path.join(OUTPUT_DIR, f"all_files_{HEIGHT}mm")
        os.makedirs(output_path_all, exist_ok=True)
        
        result = create_clean_platform(
            clf_files=filtered_files,
            output_dir=output_path_all,
            height=HEIGHT,
            fill_closed=False,
            alignment_style_only=False,
            save_clean_png=True
        )
        
        if result:
            print(f"✓ All files visualization saved")
        else:
            print("✗ All files visualization failed")
            
    except Exception as e:
        print(f"✗ Error in all files test: {e}")
    
    # Test 2: Skin files only (enhanced with colorization)
    print(f"\n=== Test 2: Skin files only (Enhanced with colorization) ===")
    try:
        output_path_skin = os.path.join(OUTPUT_DIR, f"skin_files_only_{HEIGHT}mm")
        os.makedirs(output_path_skin, exist_ok=True)
        
        result = create_clean_platform_skin_only_enhanced(
            clf_files=filtered_files,
            output_dir=output_path_skin,
            height=HEIGHT,
            fill_closed=False,
            alignment_style_only=False,
            save_clean_png=True,
            only_skin_files=True  # Use only skin files
        )
        
        if result:
            print(f"✓ Enhanced skin files only visualization saved")
        else:
            print("✗ Skin files only visualization failed")
            
    except Exception as e:
        print(f"✗ Error in skin files only test: {e}")
    
    print(f"\nTest complete! Check outputs in: {OUTPUT_DIR}")
    print(f"Compare the two visualizations to see the difference between all files vs skin files only.")


if __name__ == "__main__":
    main()
