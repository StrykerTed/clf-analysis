#!/usr/bin/env python3
"""
Complete shape visualization program that shows ALL shapes at a given height.
Shows both holes (Shape[1] Path[0]) in green and all other shapes in blue.
This version (v4) analyzes preprocess build-430848 at height 152.00mm.
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
    """Main function to visualize ALL shapes from ALL folders at height 152.00mm."""
    
    # Configuration
    HEIGHT = 153.45  # mm
    BUILD_DIR = "abp_contents/preprocess build-430848"
    
    # Create output directory
    output_dir = "my_outputs/holes_only_visualization"
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
    total_holes = 0
    files_with_shapes = set()
    files_with_holes = set()
    total_files_with_holes = 0
    total_files_with_shapes = 0
    files_processed = 0
    
    # Bbox data collection
    bbox_data = []
    
    # Process each CLF file
    for clf_info in clf_files:
        # Initialize file-level flags for each file
        file_has_holes = False
        file_has_shapes = False
        
        try:
            part = CLFFile(clf_info['path'])
            if not hasattr(part, 'box'):
                print(f"No box attribute in {clf_info['name']}")
                continue
                
            layer = part.find(HEIGHT)
            if layer is None:
                print(f"No layer at height {HEIGHT}mm in {clf_info['name']}")
                continue
                
            # Process each shape in the layer - show ALL shapes and identify holes
            for shape_idx, shape in enumerate(layer.shapes):
                if hasattr(shape, 'points') and shape.points:
                    for path_idx, path in enumerate(shape.points):
                        if len(path) >= 3:  # Valid path with at least 3 points
                            total_shapes += 1
                            file_has_shapes = True
                            
                            # Convert to numpy array
                            points = np.array(path)
                            
                            # Check if this is a hole (Shape[1] Path[0])
                            is_hole = (shape_idx == 1 and path_idx == 0 and len(layer.shapes) >= 2)
                            
                            # Determine color based on number of points or hole status
                            if len(path) == 66:  # Highlight paths with 66 points in red or orange if hole
                                color = 'orange' if is_hole else 'red'
                                linewidth = 0.5
                                print(f"  Found potential hole (66 points): Shape[{shape_idx}] Path[{path_idx}] with {len(path)} points in {clf_info['folder']}")
                            elif is_hole:
                                total_holes += 1
                                file_has_holes = True
                                color = 'darkgreen'
                                linewidth = 1
                                print(f"  Found hole: Shape[{shape_idx}] Path[{path_idx}] with {len(path)} points in {clf_info['folder']}")
                            else:
                                color = 'blue'
                                linewidth = 0.5
                                print(f"  Found shape: Shape[{shape_idx}] Path[{path_idx}] with {len(path)} points in {clf_info['folder']}")
                            
                            # Draw the shape with the determined color
                            draw_shape(plt, points, 
                                    color=color, 
                                    alpha=0.8 if color == 'darkgreen' else 0.6,
                                    linewidth=linewidth)
                
                elif hasattr(shape, 'radius') and hasattr(shape, 'center'):
                    # Handle circles
                    total_shapes += 1
                    file_has_shapes = True
                    
                    circle = plt.Circle(
                        shape.center, 
                        shape.radius, 
                        color='blue', 
                        fill=False, 
                        alpha=0.6,
                        linewidth=2
                    )
                    plt.gca().add_artist(circle)
                    
                    print(f"  Found circle: Shape[{shape_idx}] radius={shape.radius} in {clf_info['folder']}")
            
            # Update file-level counters after processing all shapes in the file
            if file_has_holes:
                total_files_with_holes += 1
                files_with_holes.add(clf_info['name'])
            if file_has_shapes:
                total_files_with_shapes += 1
                files_with_shapes.add(clf_info['name'])
            
            files_processed += 1
            print(f"Processed {clf_info['name']}: found holes in layer at {HEIGHT}mm")
            
        except Exception as e:
            print(f"Error processing {clf_info['name']}: {str(e)}")
            continue
    
    # Add title and labels
    ax.set_title(f'Complete Shape Visualization (ALL Folders) at {HEIGHT}mm\\n'
                f'Files: {files_processed}, Files with shapes: {total_files_with_shapes}, Total shapes: {total_shapes}, Holes: {total_holes}', 
                fontsize=14, fontweight='bold')
    
    # Add legend  
    legend_elements = [
        plt.Line2D([0], [0], color='blue', lw=2, alpha=0.6, label='Regular Shapes'),
        plt.Line2D([0], [0], color='darkgreen', lw=3, alpha=0.8, label='Holes (Shape[1] Path[0])'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    # Add platform labels
    add_platform_labels(plt)
    
    # Set platform limits
    set_platform_limits(plt)
    
    # Save the figure
    output_filename = f'complete_shapes_visualization_{HEIGHT}mm.png'
    output_path = os.path.join(output_dir, output_filename)
    save_platform_figure(plt, output_path)
    
    print(f"\\nComplete shapes visualization complete!")
    print(f"Output saved to: {output_path}")
    print(f"Total files processed: {files_processed}")
    print(f"Files with shapes: {total_files_with_shapes}")
    print(f"Total shapes found: {total_shapes}")
    print(f"Files with holes: {total_files_with_holes}")
    print(f"Total holes found: {total_holes}")
    
    # Save summary to JSON
    summary = {
        "analysis_type": "complete_shapes_all_folders",
        "height_mm": HEIGHT,
        "build_directory": BUILD_DIR,
        "files_processed": files_processed,
        "files_with_shapes": total_files_with_shapes,
        "total_shapes": total_shapes,
        "files_with_holes": total_files_with_holes,
        "total_holes": total_holes,
        "output_file": output_filename
    }
    
    summary_path = os.path.join(output_dir, f'complete_shapes_summary_{HEIGHT}mm.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()