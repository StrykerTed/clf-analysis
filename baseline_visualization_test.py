#!/usr/bin/env python3
"""
Simple test program that visualizes all shapes at a given height (134.0mm) without any hole detection.
This program uses the exact same exclusion logic as the main program to ensure consistency.
"""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt   
import numpy as np   
from matplotlib.patches import Polygon
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import setup_paths

from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.plotTools import (
    setup_platform_figure,
    draw_platform_boundary,
    add_reference_lines,
    set_platform_limits,
    draw_shape,
    save_platform_figure
)
from utils.myfuncs.print_utils import add_platform_labels
from utils.myfuncs.shape_things import should_close_path
from utils.myfuncs.file_utils import (
    find_clf_files,
    should_skip_folder,
    load_exclusion_patterns
)


def main():
    """Main function to visualize all shapes at height 134.0mm with no hole detection."""
    
    # Configuration
    HEIGHT = 134.0  # mm
    BUILD_DIR = "abp_contents/preprocess build-424292"
    
    # Create output directory
    output_dir = "my_outputs/baseline_visualization"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Starting baseline visualization at height {HEIGHT}mm")
    print(f"Build directory: {BUILD_DIR}")
    print(f"Output directory: {output_dir}")
    
    # Load exclusion patterns from the config file (same as main program)
    try:
        script_dir = os.path.join(project_root, 'src', 'config')
        exclusion_patterns = load_exclusion_patterns(script_dir)
        print(f"Loaded exclusion patterns: {exclusion_patterns}")
    except Exception as e:
        print(f"Error loading exclusion patterns: {e}")
        print("Using empty exclusion patterns")
        exclusion_patterns = []
    
    # Build the full path to the build directory
    build_path = os.path.join(project_root, BUILD_DIR)
    if not os.path.exists(build_path):
        print(f"Error: Build directory not found at {build_path}")
        return
    
    # Find all CLF files (same as main program)
    all_clf_files = find_clf_files(build_path)
    print(f"Found {len(all_clf_files)} CLF files total")
    
    # Filter based on exclusion patterns (same logic as main program)
    clf_files = []
    for clf_info in all_clf_files:
        should_skip = should_skip_folder(clf_info['folder'], exclusion_patterns)
        if should_skip:
            print(f"Skipping file: {clf_info['name']} in {clf_info['folder']}")
        else:
            clf_files.append(clf_info)
            print(f"Keeping file: {clf_info['name']} in {clf_info['folder']}")
    
    excluded_count = len(all_clf_files) - len(clf_files)
    print(f"Excluded {excluded_count} files based on folder patterns")
    print(f"Processing {len(clf_files)} CLF files")
    
    # Set up the figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    # Draw platform boundary and reference lines
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    # Statistics
    total_shapes = 0
    total_paths = 0
    files_processed = 0
    
    # Bbox data collection
    bbox_data = []
    
    # Process each CLF file
    for clf_info in clf_files:
        try:
            part = CLFFile(clf_info['path'])
            if not hasattr(part, 'box'):
                print(f"No box attribute in {clf_info['name']}")
                continue
                
            layer = part.find(HEIGHT)
            if layer is None:
                print(f"No layer at height {HEIGHT}mm in {clf_info['name']}")
                continue
                
            # Process each shape in the layer
            if hasattr(layer, 'shapes'):
                for shape_idx, shape in enumerate(layer.shapes):
                    total_shapes += 1
                    
                    # Get bbox data for this shape
                    shape_bbox = None
                    try:
                        # Try different ways to access bbox data
                        if hasattr(shape, 'box'):
                            bbox_obj = shape.box
                            # Check if it's a function that needs to be called
                            if callable(bbox_obj):
                                bbox_obj = bbox_obj()
                            
                            # Now try to access the bbox attributes
                            if hasattr(bbox_obj, 'min_x'):
                                shape_bbox = {
                                    'min_x': bbox_obj.min_x,
                                    'min_y': bbox_obj.min_y,
                                    'max_x': bbox_obj.max_x,
                                    'max_y': bbox_obj.max_y,
                                    'width': bbox_obj.max_x - bbox_obj.min_x,
                                    'height': bbox_obj.max_y - bbox_obj.min_y
                                }
                        
                        # Alternative: try to compute bbox from shape points
                        if shape_bbox is None and hasattr(shape, 'points') and shape.points:
                            all_x = []
                            all_y = []
                            for path in shape.points:
                                if isinstance(path, np.ndarray) or isinstance(path, list):
                                    points_array = np.array(path) if not isinstance(path, np.ndarray) else path
                                    if len(points_array.shape) == 2 and points_array.shape[1] >= 2:
                                        all_x.extend(points_array[:, 0])
                                        all_y.extend(points_array[:, 1])
                            
                            if all_x and all_y:
                                min_x, max_x = min(all_x), max(all_x)
                                min_y, max_y = min(all_y), max(all_y)
                                shape_bbox = {
                                    'min_x': min_x,
                                    'min_y': min_y,
                                    'max_x': max_x,
                                    'max_y': max_y,
                                    'width': max_x - min_x,
                                    'height': max_y - min_y
                                }
                    except Exception as bbox_error:
                        print(f"Error getting bbox for shape {shape_idx} in {clf_info['name']}: {bbox_error}")
                        shape_bbox = None
                    
                    # Store bbox data (with shape and path information)
                    bbox_info = {
                        'file_name': clf_info['name'],
                        'folder': clf_info['folder'],
                        'shape_index': shape_idx,
                        'height_mm': HEIGHT,
                        'bbox': shape_bbox,
                        'num_paths': len(shape.points) if hasattr(shape, 'points') and shape.points else 0
                    }
                    bbox_data.append(bbox_info)
                    
                    # Process paths in the shape
                    if hasattr(shape, 'points') and shape.points:
                        # Process all paths in the shape, not just the first one
                        for path_idx, points in enumerate(shape.points):
                            total_paths += 1
                            
                            # Convert to numpy array if needed
                            if not isinstance(points, np.ndarray):
                                points = np.array(points)
                            
                            # Skip if not enough points
                            if len(points) < 3:
                                continue
                            
                            # Check if path should be closed
                            close_path = should_close_path(points)
                            
                            # Color coding based on shape index and path index
                            if shape_idx == 0:
                                # First shape in each file - use blues
                                if path_idx == 0:
                                    color = 'darkblue'  # First path of first shape
                                elif path_idx == 1:
                                    color = 'blue'      # Second path of first shape
                                else:
                                    color = 'lightblue'  # Third+ path of first shape
                            elif shape_idx == 1:
                                # Second shape in each file - use greens
                                if path_idx == 0:
                                    color = 'darkgreen'  # First path of second shape
                                elif path_idx == 1:
                                    color = 'green'      # Second path of second shape
                                else:
                                    color = 'lightgreen' # Third+ path of second shape
                            else:
                                # Third+ shape in each file - use reds/oranges
                                if path_idx == 0:
                                    color = 'darkred'    # First path of third+ shape
                                elif path_idx == 1:
                                    color = 'red'        # Second path of third+ shape
                                else:
                                    color = 'orange'     # Third+ path of third+ shape
                            
                            # Adjust alpha based on whether path is closed
                            alpha = 0.7 if close_path else 0.9
                            
                            # Different line width for different path indices
                            linewidth = 2 if path_idx == 0 else 1
                            
                            draw_shape(plt, points, 
                                     color=color, 
                                     alpha=alpha,
                                     linewidth=linewidth)
            
            files_processed += 1
            print(f"Processed {clf_info['name']}: found shapes in layer at {HEIGHT}mm")
            
        except Exception as e:
            print(f"Error processing {clf_info['name']}: {e}")
            continue
    
    # Add title and labels
    ax.set_title(f'Baseline Visualization - All Shapes at {HEIGHT}mm\\n'
                f'Files: {files_processed}, Shapes: {total_shapes}, Paths: {total_paths}', 
                fontsize=14, fontweight='bold')
    
    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], color='darkblue', lw=2, alpha=0.7, label='Shape[0] Path[0] (first path of first shape)'),
        plt.Line2D([0], [0], color='blue', lw=1, alpha=0.7, label='Shape[0] Path[1+] (additional paths of first shape)'),
        plt.Line2D([0], [0], color='darkgreen', lw=2, alpha=0.7, label='Shape[1] Path[0] (first path of second shape)'),
        plt.Line2D([0], [0], color='green', lw=1, alpha=0.7, label='Shape[1] Path[1+] (additional paths of second shape)'),
        plt.Line2D([0], [0], color='darkred', lw=2, alpha=0.7, label='Shape[2+] Path[0] (first path of third+ shape)'),
        plt.Line2D([0], [0], color='red', lw=1, alpha=0.7, label='Shape[2+] Path[1+] (additional paths of third+ shape)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
    
    # Add platform labels
    add_platform_labels(plt)
    
    # Set platform limits
    set_platform_limits(plt)
    
    # Save the figure
    output_filename = f'baseline_visualization_{HEIGHT}mm.png'
    output_path = os.path.join(output_dir, output_filename)
    save_platform_figure(plt, output_path)
    
    print(f"\\nBaseline visualization complete!")
    print(f"Output saved to: {output_path}")
    print(f"Total files processed: {files_processed}")
    print(f"Total shapes: {total_shapes}")
    print(f"Total paths: {total_paths}")
    
    # Save summary to JSON
    summary = {
        "height_mm": HEIGHT,
        "build_directory": BUILD_DIR,
        "exclusion_patterns": exclusion_patterns,
        "total_clf_files_found": len(all_clf_files),
        "files_excluded": excluded_count,
        "files_processed": files_processed,
        "total_shapes": total_shapes,
        "total_paths": total_paths,
        "output_file": output_filename
    }
    
    summary_path = os.path.join(output_dir, f'baseline_summary_{HEIGHT}mm.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Save bbox data to JSON
    bbox_path = os.path.join(output_dir, f'bbox_data_{HEIGHT}mm.json')
    with open(bbox_path, 'w') as f:
        json.dump(bbox_data, f, indent=2)
    
    print(f"Summary saved to: {summary_path}")
    print(f"Bbox data saved to: {bbox_path}")
    print(f"Total bbox records: {len(bbox_data)}")


if __name__ == "__main__":
    main()
