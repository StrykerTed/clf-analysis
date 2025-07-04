#!/usr/bin/env python3
"""
Ellipse-focused visualization to identify the blue elliptical holes.
This will create a special view showing only the 12 likely ellipses we detected.
"""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt   
import numpy as np   
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import setup_paths

from utils.myfuncs.plotTools import (
    setup_platform_figure,
    draw_platform_boundary,
    add_reference_lines,
    set_platform_limits,
    draw_shape,
    save_platform_figure
)
from utils.myfuncs.print_utils import add_platform_labels


def visualize_ellipses_only():
    """Create a visualization showing only the likely ellipses."""
    
    # Load the analysis data
    json_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/my_outputs/enhanced_holes_test/all_shapes_134.0mm.json"
    
    with open(json_path, 'r') as f:
        all_shapes = json.load(f)
    
    # Filter for likely ellipses
    ellipses = [shape for shape in all_shapes if shape.get('is_likely_ellipse', False)]
    
    print(f"Found {len(ellipses)} likely ellipses")
    
    # Create figure
    setup_platform_figure()
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    # Colors for different CLF sources
    clf_colors = {
        'Part.clf': 'red',
        'Net.clf': 'blue', 
        'unknown': 'orange'
    }
    
    # Draw each ellipse with detailed information
    for i, ellipse in enumerate(ellipses):
        points = np.array(ellipse['points'])
        clf_name = ellipse['clf_name']
        clf_folder = ellipse['clf_folder']
        
        color = clf_colors.get(clf_name, clf_colors['unknown'])
        
        # Draw the ellipse
        draw_shape(plt, points, color, linewidth=3)
        
        # Add a number label
        centroid = ellipse['properties']['centroid']
        plt.text(centroid[0], centroid[1], str(i+1), 
                fontsize=12, fontweight='bold', color='white',
                ha='center', va='center',
                bbox=dict(boxstyle='circle', facecolor='black', alpha=0.7))
        
        # Print details
        props = ellipse['properties']
        print(f"Ellipse {i+1}:")
        print(f"  File: {clf_folder}/{clf_name}")
        print(f"  Centroid: ({centroid[0]:.1f}, {centroid[1]:.1f})")
        print(f"  Area: {props['area']:.2f}")
        print(f"  Compactness: {props['compactness']:.3f}")
        print(f"  Aspect ratio: {props['aspect_ratio']:.3f}")
        print(f"  Width x Height: {props['width']:.2f} x {props['height']:.2f}")
        print()
    
    # Add legend
    legend_elements = []
    for clf_name, color in clf_colors.items():
        if any(e['clf_name'] == clf_name for e in ellipses):
            count = sum(1 for e in ellipses if e['clf_name'] == clf_name)
            legend_elements.append(plt.Line2D([0], [0], color=color, lw=3, 
                                            label=f'{clf_name} ({count})'))
    
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.title(f'Likely Ellipses at Height 134.0mm (Total: {len(ellipses)})')
    add_platform_labels(plt)
    set_platform_limits(plt)
    
    # Save
    output_dir = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/my_outputs/enhanced_holes_test"
    filename = 'ellipses_only_134.0mm.png'
    output_path = os.path.join(output_dir, filename)
    save_platform_figure(plt, output_path)
    print(f"Saved ellipses visualization: {output_path}")


def visualize_ellipses_in_context():
    """Create a visualization showing ellipses highlighted against all other shapes."""
    
    # Load the analysis data
    json_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/my_outputs/enhanced_holes_test/all_shapes_134.0mm.json"
    
    with open(json_path, 'r') as f:
        all_shapes = json.load(f)
    
    # Separate ellipses from other shapes
    ellipses = [shape for shape in all_shapes if shape.get('is_likely_ellipse', False)]
    other_shapes = [shape for shape in all_shapes if not shape.get('is_likely_ellipse', False)]
    
    print(f"Drawing {len(other_shapes)} other shapes in gray and {len(ellipses)} ellipses in bright colors")
    
    # Create figure
    setup_platform_figure()
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    # Draw all other shapes in light gray first
    for shape in other_shapes:
        if shape['type'] == 'path':
            points = np.array(shape['points'])
            draw_shape(plt, points, 'lightgray', alpha=0.3)
        elif shape['type'] == 'circle':
            center = shape['center']
            radius = shape['radius']
            circle = plt.Circle(center, radius, color='lightgray', fill=False, alpha=0.3)
            plt.gca().add_artist(circle)
    
    # Draw ellipses in bright colors
    ellipse_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 
                     'pink', 'olive', 'cyan', 'magenta', 'yellow', 'black']
    
    for i, ellipse in enumerate(ellipses):
        points = np.array(ellipse['points'])
        color = ellipse_colors[i % len(ellipse_colors)]
        
        # Draw the ellipse with thick line
        draw_shape(plt, points, color, linewidth=4)
        
        # Add a number label
        centroid = ellipse['properties']['centroid']
        plt.text(centroid[0], centroid[1], str(i+1), 
                fontsize=14, fontweight='bold', color='white',
                ha='center', va='center',
                bbox=dict(boxstyle='circle', facecolor='black', alpha=0.8))
    
    # Add legend
    plt.plot([], [], color='lightgray', alpha=0.3, label=f'Other Shapes ({len(other_shapes)})')
    plt.plot([], [], color='red', linewidth=4, label=f'Likely Ellipses ({len(ellipses)})')
    
    plt.title(f'Ellipses in Context at Height 134.0mm')
    add_platform_labels(plt)
    set_platform_limits(plt)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Save
    output_dir = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/my_outputs/enhanced_holes_test"
    filename = 'ellipses_in_context_134.0mm.png'
    output_path = os.path.join(output_dir, filename)
    save_platform_figure(plt, output_path)
    print(f"Saved ellipses in context visualization: {output_path}")


if __name__ == "__main__":
    print("Creating ellipse-focused visualizations...")
    visualize_ellipses_only()
    print()
    visualize_ellipses_in_context()
    print("\nEllipse analysis complete!")
