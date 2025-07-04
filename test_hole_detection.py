#!/usr/bin/env python3
"""
Test program to investigate hole detection at different heights.
This program will analyze shapes and look for multi-path patterns that could indicate holes.
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
from utils.platform_analysis.visualization_utils import create_clean_platform_skin_only_enhanced
from utils.pyarcam.clfutil import CLFFile

# Configuration
BUILD_DIR = "abp_contents/preprocess build-424292"
OUTPUT_DIR = "my_outputs/hole_detection_test"
TEST_HEIGHTS = [8.2, 50.0, 100.0, 134.0, 150.0, 200.0]  # Different heights to test

def analyze_shapes_for_holes(clf_files, height):
    """Analyze shapes at a specific height to look for multi-path patterns (holes)."""
    print(f"\n=== Analyzing shapes at height {height}mm ===")
    
    hole_candidates = []
    multi_path_shapes = []
    
    for clf_info in clf_files:
        try:
            # Only check skin files for holes
            if 'skin' not in clf_info['folder'].lower():
                continue
                
            part = CLFFile(clf_info['path'])
            if not hasattr(part, 'box'):
                continue
                
            layer = part.find(height)
            if layer is None:
                continue
                
            if hasattr(layer, 'shapes'):
                shapes = list(layer.shapes)
                
                for i, shape in enumerate(shapes):
                    if hasattr(shape, 'points') and shape.points:
                        num_paths = len(shape.points)
                        
                        # Look for shapes with multiple paths
                        if num_paths > 1:
                            shape_identifier = "unknown"
                            if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                                shape_identifier = str(shape.model.id)
                            
                            shape_info = {
                                'file': clf_info['name'],
                                'folder': clf_info['folder'],
                                'shape_index': i,
                                'shape_id': shape_identifier,
                                'num_paths': num_paths,
                                'path_lengths': [len(points) for points in shape.points],
                                'height': height
                            }
                            
                            multi_path_shapes.append(shape_info)
                            
                            # Check if paths could be holes (inner paths)
                            for path_idx, points in enumerate(shape.points):
                                if path_idx > 0:  # Not the first (outer) path
                                    hole_info = shape_info.copy()
                                    hole_info['hole_path_index'] = path_idx
                                    hole_info['hole_path_length'] = len(points)
                                    hole_candidates.append(hole_info)
                                    
                                    print(f"  POTENTIAL HOLE: {clf_info['name']} - Shape {i} (ID:{shape_identifier}), Path {path_idx}/{num_paths}")
                                    print(f"    Path lengths: {[len(p) for p in shape.points]}")
                        
        except Exception as e:
            print(f"Error analyzing {clf_info['name']}: {e}")
    
    print(f"Found {len(multi_path_shapes)} shapes with multiple paths")
    print(f"Found {len(hole_candidates)} potential holes")
    
    return multi_path_shapes, hole_candidates

def main():
    print("Testing hole detection at different heights...")
    print(f"Build directory: {BUILD_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Get CLF files
    build_path = os.path.join(os.getcwd(), BUILD_DIR)
    if not os.path.exists(build_path):
        print(f"Build directory not found: {build_path}")
        return
    
    # Gather all CLF files
    clf_files = find_clf_files(build_path)
    
    # Apply exclusion logic (same as main program)
    try:
        config_path = os.path.join("src", "config", "folder_exclusions.json")
        import json
        with open(config_path, 'r') as f:
            exclusion_config = json.load(f)
        exclusion_patterns = exclusion_config.get('folder_exclusions', [])
        print(f"Loaded exclusion patterns: {exclusion_patterns}")
    except Exception as e:
        print(f"Could not load exclusion config: {e}")
        exclusion_patterns = ['_Support', 'supports', 'SUPPORTS', 'Supports', 'ebm-ti64', 'Porous', 'Cylinder', 'Support', 'Coupon', 's_Skin']
    
    # Filter files using exclusion logic
    excluded_files = []
    for clf_info in clf_files:
        folder_name = clf_info['folder']
        filename = clf_info['name']
        
        # Check folder exclusions
        if should_skip_folder(folder_name, exclusion_patterns):
            excluded_files.append(clf_info)
            continue
            
        # Check if filename should be skipped (like WaferSupport.clf)
        if filename == 'WaferSupport.clf':
            excluded_files.append(clf_info)
            continue
    
    excluded_paths = {info['path'] for info in excluded_files}
    filtered_files = [clf_info for clf_info in clf_files if clf_info['path'] not in excluded_paths]
    
    print(f"Found {len(clf_files)} CLF files total")
    print(f"Excluded {len(excluded_files)} files based on folder patterns")
    print(f"Processing {len(filtered_files)} CLF files")
    
    # Filter for skin files only
    skin_files = [f for f in filtered_files if 'skin' in f['folder'].lower()]
    print(f"Found {len(skin_files)} skin files for hole analysis")
    
    if len(skin_files) == 0:
        print("No skin files found!")
        return
    
    # Analyze holes at different heights
    all_multi_path_shapes = []
    all_hole_candidates = []
    
    for height in TEST_HEIGHTS:
        multi_path_shapes, hole_candidates = analyze_shapes_for_holes(filtered_files, height)
        all_multi_path_shapes.extend(multi_path_shapes)
        all_hole_candidates.extend(hole_candidates)
        
        # Create visualization for heights with interesting results
        if len(hole_candidates) > 0 or len(multi_path_shapes) > 0:
            print(f"  Creating enhanced visualization for height {height}mm...")
            output_path_height = os.path.join(OUTPUT_DIR, f"height_{height}mm")
            os.makedirs(output_path_height, exist_ok=True)
            
            try:
                create_clean_platform_skin_only_enhanced(
                    clf_files=filtered_files,
                    output_dir=output_path_height,
                    height=height,
                    fill_closed=False,
                    alignment_style_only=False,
                    save_clean_png=True,
                    only_skin_files=True
                )
                print(f"    ✓ Visualization saved for height {height}mm")
            except Exception as e:
                print(f"    ✗ Error creating visualization for height {height}mm: {e}")
    
    # Summary
    print(f"\n=== HOLE DETECTION SUMMARY ===")
    print(f"Total multi-path shapes found: {len(all_multi_path_shapes)}")
    print(f"Total potential holes found: {len(all_hole_candidates)}")
    
    if len(all_hole_candidates) > 0:
        print(f"\nHole details:")
        for hole in all_hole_candidates:
            print(f"  - {hole['file']} in {hole['folder']}: Shape {hole['shape_index']} (ID:{hole['shape_id']}), "
                  f"Path {hole['hole_path_index']}/{hole['num_paths']} at height {hole['height']}mm")
    else:
        print("No holes were detected at any height.")
        print("This could mean:")
        print("  1. No holes exist in the skin files at the tested heights")
        print("  2. The hole detection logic needs refinement")
        print("  3. Holes might exist at other heights not tested")
    
    print(f"\nTest complete! Check outputs in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
