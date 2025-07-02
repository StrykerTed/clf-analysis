#!/usr/bin/env python3
"""
Test script to debug hole detection at 136.55mm height
This will run just the process_layer_data function with debug output for 136.55mm
"""

import os
import sys

# Add parent directory to path to find setup_paths
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import setup_paths

from utils.myfuncs.file_utils import find_clf_files
from utils.platform_analysis.file_handlers import setup_abp_folders
from utils.platform_analysis.visualization_utils import process_layer_data

def test_hole_detection_136_55():
    """Test hole detection specifically at 136.55mm height"""
    
    print("=== Testing Hole Detection at 136.55mm ===\n")
    
    # Setup paths
    abp_file = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_sourcefiles/preprocess build-424292.abp"
    build_dir = setup_abp_folders(abp_file)
    
    print(f"Build directory: {build_dir}")
    
    # Find CLF files
    clf_files = find_clf_files(build_dir)
    print(f"Found {len(clf_files)} CLF files")
    
    # Define colors for different CLF files
    colors = {
        'Part.clf': 'blue',
        'WaferSupport.clf': 'red',
        'Net.clf': 'green'
    }
    
    # Test height
    test_height = 136.55
    
    print(f"\nTesting hole detection at {test_height}mm...\n")
    
    # Process each CLF file
    total_shapes = 0
    total_holes = 0
    
    for clf_info in clf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {clf_info['name']} in {clf_info['folder']}")
        print(f"{'='*60}")
        
        shape_data_list = process_layer_data(clf_info, test_height, colors)
        
        file_shapes = len(shape_data_list)
        file_holes = sum(1 for shape in shape_data_list if shape.get('is_hole', False))
        
        total_shapes += file_shapes
        total_holes += file_holes
        
        print(f"\nFile summary:")
        print(f"  Total shapes: {file_shapes}")
        print(f"  Holes found: {file_holes}")
        print(f"  Exterior shapes: {file_shapes - file_holes}")
        
        if file_holes > 0:
            print(f"  Hole details:")
            for i, shape in enumerate(shape_data_list):
                if shape.get('is_hole', False):
                    print(f"    Hole {i}: ID={shape.get('identifier')}, parent_id={shape.get('parent_shape_id')}")
    
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total shapes across all files: {total_shapes}")
    print(f"Total holes found: {total_holes}")
    print(f"Total exterior shapes: {total_shapes - total_holes}")
    
    if total_holes == 0:
        print("\n*** WARNING: No holes detected! ***")
        print("This explains why the platform_layer_pathdata_136.55mm.json file")
        print("contains only 'exterior' shapes and no 'interior' (hole) shapes.")
    else:
        print(f"\n*** SUCCESS: {total_holes} holes detected! ***")

if __name__ == "__main__":
    test_hole_detection_136_55()
