#!/usr/bin/env python3
"""
Simple test program for holes detection.
First step: Draw all shapes at height 134.00mm without any hole detection.
This establishes a baseline before we add hole detection logic.
"""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt   
import numpy as np   
from matplotlib.patches import Polygon

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
    should_skip_folder
)


def test_simple_shapes_at_height(height=134.0):
    """
    Simple test to draw all shapes at a specific height without hole detection.
    Uses the same exclusion logic as the main program.
    """
    print(f"Testing simple shapes drawing at height {height}mm...")
    
    # Set up paths like the main program
    build_dir = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/preprocess build-424292"
    config_dir = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/config"
    output_dir = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/my_outputs/simple_holes_test"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Build directory: {build_dir}")
    print(f"Output directory: {output_dir}")
    
    # Use hardcoded exclusion patterns (same as seen in logs)
    exclusion_patterns = [
        "_Support",
        "supports", 
        "SUPPORTS",
        "Supports",
        "ebm-ti64",
        "Porous",
        "Cylinder", 
        "Support",
        "Coupon",
        "s_Skin"
    ]
    print(f"Exclusion patterns: {exclusion_patterns}")
    
    # Find CLF files
    all_clf_files = find_clf_files(build_dir)
    print(f"Found {len(all_clf_files)} total CLF files")
    
    # Filter CLF files based on exclusion patterns (same as main program)
    clf_files = []
    for clf_info in all_clf_files:
        should_skip = should_skip_folder(clf_info['folder'], exclusion_patterns)
        if should_skip:
            print(f"  Skipping: {clf_info['name']} in {clf_info['folder']}")
        else:
            clf_files.append(clf_info)
            print(f"  Keeping: {clf_info['name']} in {clf_info['folder']}")
    
    excluded_count = len(all_clf_files) - len(clf_files)
    print(f"Excluded {excluded_count} files, processing {len(clf_files)} files")
    
    # Define colors for different CLF files
    colors = {
        'Part.clf': '#2E86AB',
        'WaferSupport.clf': '#A23B72', 
        'Net.clf': '#F18F01'
    }
    
    # Create figure
    setup_platform_figure(figsize=(15, 15))
    
    # Add standard platform elements
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    # Track statistics
    total_shapes = 0
    files_with_shapes = 0
    file_details = []
    
    # Process each CLF file
    for clf_info in clf_files:
        try:
            part = CLFFile(clf_info['path'])
            layer = part.find(height)
            
            if layer is None or not hasattr(layer, 'shapes'):
                print(f"  - {clf_info['name']}: No layer found at {height}mm")
                continue
            
            shapes = list(layer.shapes)
            color = colors.get(clf_info['name'], '#666666')
            shapes_in_file = 0
            
            print(f"  - {clf_info['name']}: Found {len(shapes)} shapes")
            
            # Process each shape (only first path for now - no hole detection)
            for i, shape in enumerate(shapes):
                if not hasattr(shape, 'points') or not shape.points:
                    continue
                
                # Get identifier for shape
                identifier = "unknown"
                if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                    identifier = str(shape.model.id)
                
                # Only process first path (exterior) - no hole detection yet
                points = shape.points[0]
                
                # Draw the shape
                if should_close_path(points):
                    # Draw as filled polygon with transparency
                    polygon = Polygon(points, facecolor=color, alpha=0.3, 
                                    edgecolor=color, linewidth=1)
                    plt.gca().add_patch(polygon)
                else:
                    # Draw as line
                    draw_shape(plt, points, color)
                
                shapes_in_file += 1
                total_shapes += 1
            
            if shapes_in_file > 0:
                files_with_shapes += 1
            
            file_details.append({
                'filename': clf_info['name'],
                'folder': clf_info['folder'],
                'shapes': shapes_in_file
            })
            
            print(f"    Processed {shapes_in_file} shapes from {clf_info['name']}")
            
        except Exception as e:
            print(f"Error processing {clf_info['name']}: {e}")
            continue
    
    # Create legend
    legend_elements = []
    for clf_name, color in colors.items():
        if any(detail['filename'] == clf_name and detail['shapes'] > 0 for detail in file_details):
            legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, alpha=0.3, 
                                               edgecolor=color, label=f'{clf_name}'))
    
    if legend_elements:
        plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.)
    
    plt.title(f'Simple Shapes Test at {height}mm\n'
             f'Total Files: {len(clf_files)} | Files with Shapes: {files_with_shapes}\n'
             f'Total Shapes: {total_shapes} (First Path Only - No Holes)')
    
    add_platform_labels(plt)
    set_platform_limits(plt)
    
    # Save the view
    filename = f'simple_shapes_test_{height}mm.png'
    output_path = os.path.join(output_dir, filename)
    save_platform_figure(plt, output_path)
    
    print(f"\nSimple shapes test completed!")
    print(f"Results:")
    print(f"  - Total files processed: {len(clf_files)}")
    print(f"  - Files with shapes: {files_with_shapes}")
    print(f"  - Total shapes drawn: {total_shapes}")
    print(f"  - Output saved to: {output_path}")
    
    # Print file details
    print("\nFile details:")
    for detail in file_details:
        if detail['shapes'] > 0:
            print(f"  - {detail['filename']}: {detail['shapes']} shapes")
    
    return output_path, total_shapes, file_details


def main():
    """Main function to run the simple shapes test."""
    print("=" * 60)
    print("SIMPLE SHAPES TEST - NO HOLE DETECTION")
    print("=" * 60)
    
    # Test at height 134.0mm (same as the holes analysis)
    output_path, total_shapes, file_details = test_simple_shapes_at_height(134.0)
    
    print("\nTest completed successfully!")
    print(f"Check the output at: {output_path}")
    print("\nNext step: Add hole detection logic to this baseline.")


if __name__ == "__main__":
    main()
