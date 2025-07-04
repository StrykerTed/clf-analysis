#!/usr/bin/env python3
"""
Enhanced test program for holes detection with color-coded analysis.
This program will help identify elliptical holes by:
1. Drawing all shapes at height 134.00mm 
2. Color-coding shapes based on:
   - Filename (CLF source)
   - Shape type (path vs circle)
   - Path index (multiple paths within same shape)
   - Geometric properties (area, perimeter, eccentricity for ellipses)
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
    should_skip_folder
)


def calculate_shape_properties(points):
    """Calculate geometric properties of a shape to help identify ellipses."""
    try:
        if len(points) < 3:
            return None
        
        # Calculate area using shoelace formula
        x = points[:, 0]
        y = points[:, 1]
        area = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        
        # Calculate perimeter
        diffs = np.diff(points, axis=0, append=points[0:1])
        perimeter = np.sum(np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2))
        
        # Calculate centroid
        cx = np.mean(x)
        cy = np.mean(y)
        
        # Calculate compactness (4*pi*area/perimeter^2) - circles = 1, ellipses < 1
        compactness = 4 * np.pi * area / (perimeter**2) if perimeter > 0 else 0
        
        # Calculate bounding box dimensions
        min_x, max_x = np.min(x), np.max(x)
        min_y, max_y = np.min(y), np.max(y)
        width = max_x - min_x
        height = max_y - min_y
        
        # Calculate aspect ratio (width/height)
        aspect_ratio = width / height if height > 0 else 1.0
        
        return {
            'area': area,
            'perimeter': perimeter,
            'centroid': (cx, cy),
            'compactness': compactness,
            'width': width,
            'height': height,
            'aspect_ratio': aspect_ratio,
            'bounding_box': (min_x, min_y, max_x, max_y)
        }
    except Exception as e:
        print(f"Error calculating shape properties: {e}")
        return None


def is_likely_ellipse(points, properties=None):
    """Determine if a shape is likely an ellipse based on geometric properties."""
    if properties is None:
        properties = calculate_shape_properties(points)
    
    if properties is None:
        return False
    
    # Ellipses typically have:
    # - High compactness (close to circle)
    # - Reasonable aspect ratio (not too elongated)
    # - Smooth curves (approximated by point count)
    
    compactness = properties['compactness']
    aspect_ratio = properties['aspect_ratio']
    point_count = len(points)
    
    # Heuristics for ellipse detection
    is_compact = compactness > 0.5  # Reasonably circular
    is_reasonable_aspect = 0.3 < aspect_ratio < 3.0  # Not too elongated
    has_enough_points = point_count > 8  # Smooth curves need more points
    
    return is_compact and is_reasonable_aspect and has_enough_points


def enhanced_holes_test_at_height(height=134.0):
    """
    Enhanced test to analyze shapes at a specific height with detailed color coding.
    """
    print(f"Enhanced holes analysis at height {height}mm...")
    
    # Set up paths
    build_dir = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/preprocess build-424292"
    output_dir = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/my_outputs/enhanced_holes_test"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Hardcoded exclusion patterns (same as main program)
    exclusion_patterns = [
        "AuxiliarySupport",
        "BuildProcessor", 
        "Recoater",
        "support"
    ]
    
    # Hardcoded filename exclusions
    filename_exclusions = [
        "WaferSupport.clf"
    ]
    
    print(f"Using folder exclusion patterns: {exclusion_patterns}")
    print(f"Using filename exclusions: {filename_exclusions}")
    
    # Find all CLF files
    all_clf_files = find_clf_files(build_dir)
    print(f"Found {len(all_clf_files)} CLF files total")
    
    # Filter based on exclusion patterns
    clf_files = []
    for clf_info in all_clf_files:
        # Check folder exclusions
        should_skip_by_folder = should_skip_folder(clf_info['folder'], exclusion_patterns)
        # Check filename exclusions
        should_skip_by_filename = clf_info['name'] in filename_exclusions
        
        if not should_skip_by_folder and not should_skip_by_filename:
            clf_files.append(clf_info)
        else:
            reason = "folder" if should_skip_by_folder else "filename"
            print(f"Excluding ({reason}): {clf_info['folder']}/{clf_info['name']}")
    
    print(f"After exclusions: {len(clf_files)} CLF files to process")
    
    # Define colors for different criteria
    clf_colors = {
        'Part.clf': 'blue',
        'WaferSupport.clf': 'red', 
        'Net.clf': 'green',
        'unknown': 'gray'
    }
    
    # Colors for path analysis
    path_colors = ['darkblue', 'lightblue', 'cyan', 'teal', 'navy']
    
    # Colors for shape types
    shape_type_colors = {
        'likely_ellipse': 'orange',
        'small_shape': 'yellow',
        'large_shape': 'purple',
        'regular_shape': 'gray'
    }
    
    # Collect all shape data for analysis
    all_shapes = []
    shapes_by_clf = {}
    shapes_by_type = {}
    potential_holes = []
    
    # Process each CLF file
    for clf_info in clf_files:
        try:
            part = CLFFile(clf_info['path'])
            if not hasattr(part, 'box'):
                print(f"No box attribute in {clf_info['name']}")
                continue
                
            layer = part.find(height)
            if layer is None:
                print(f"No layer found at {height}mm in {clf_info['name']}")
                continue
                
            if not hasattr(layer, 'shapes'):
                print(f"No shapes in layer at {height}mm in {clf_info['name']}")
                continue
                
            shapes = list(layer.shapes)
            print(f"Found {len(shapes)} shapes in {clf_info['name']}")
            
            shapes_by_clf[clf_info['name']] = []
            
            # Process each shape
            for shape_idx, shape in enumerate(shapes):
                # Get shape identifier
                shape_identifier = None
                if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                    shape_identifier = shape.model.id
                
                # Handle path-based shapes
                if hasattr(shape, 'points') and shape.points:
                    num_paths = len(shape.points)
                    
                    for path_idx, points in enumerate(shape.points):
                        if isinstance(points, np.ndarray) and points.shape[0] >= 1 and points.shape[1] >= 2:
                            # Calculate shape properties
                            properties = calculate_shape_properties(points)
                            is_ellipse = is_likely_ellipse(points, properties)
                            
                            # Determine shape category
                            shape_category = 'regular_shape'
                            if is_ellipse:
                                shape_category = 'likely_ellipse'
                            elif properties and properties['area'] < 10:
                                shape_category = 'small_shape'
                            elif properties and properties['area'] > 1000:
                                shape_category = 'large_shape'
                            
                            # Create shape data
                            shape_data = {
                                'type': 'path',
                                'points': points,
                                'clf_name': clf_info['name'],
                                'clf_folder': clf_info['folder'],
                                'shape_index': shape_idx,
                                'path_index': path_idx,
                                'total_paths': num_paths,
                                'is_multi_path': num_paths > 1,
                                'identifier': shape_identifier,
                                'properties': properties,
                                'is_likely_ellipse': is_ellipse,
                                'shape_category': shape_category,
                                'should_close': should_close_path(points)
                            }
                            
                            all_shapes.append(shape_data)
                            shapes_by_clf[clf_info['name']].append(shape_data)
                            
                            # Track by shape type
                            if shape_category not in shapes_by_type:
                                shapes_by_type[shape_category] = []
                            shapes_by_type[shape_category].append(shape_data)
                            
                            # Track potential holes (additional paths in multi-path shapes)
                            if path_idx > 0 and 'skin' in clf_info['name'].lower():
                                potential_holes.append(shape_data)
                                print(f"  Potential hole: Path {path_idx} in Shape {shape_idx} in {clf_info['name']}")
                
                # Handle circle-based shapes
                elif hasattr(shape, 'radius') and hasattr(shape, 'center'):
                    shape_data = {
                        'type': 'circle',
                        'center': shape.center,
                        'radius': shape.radius,
                        'clf_name': clf_info['name'],
                        'clf_folder': clf_info['folder'],
                        'shape_index': shape_idx,
                        'path_index': 0,
                        'total_paths': 1,
                        'is_multi_path': False,
                        'identifier': shape_identifier,
                        'properties': {'area': np.pi * shape.radius**2},
                        'is_likely_ellipse': False,
                        'shape_category': 'circle',
                        'should_close': True
                    }
                    all_shapes.append(shape_data)
                    shapes_by_clf[clf_info['name']].append(shape_data)
                    
        except Exception as e:
            print(f"Error processing {clf_info['name']}: {str(e)}")
            continue
    
    print(f"\nTotal shapes collected: {len(all_shapes)}")
    print(f"Potential holes found: {len(potential_holes)}")
    
    # Create visualization by CLF source
    create_visualization_by_clf(all_shapes, clf_colors, output_dir, height)
    
    # Create visualization by shape type
    create_visualization_by_type(all_shapes, shape_type_colors, output_dir, height)
    
    # Create visualization highlighting potential holes
    create_holes_visualization(all_shapes, potential_holes, output_dir, height)
    
    # Save analysis data
    save_analysis_data(all_shapes, shapes_by_clf, shapes_by_type, potential_holes, output_dir, height)
    
    # Print summary
    print_analysis_summary(all_shapes, shapes_by_clf, shapes_by_type, potential_holes)


def create_visualization_by_clf(all_shapes, clf_colors, output_dir, height):
    """Create visualization colored by CLF source file."""
    print(f"Creating CLF-based visualization...")
    
    # Create figure
    setup_platform_figure()
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    # Draw shapes colored by CLF
    legend_added = set()
    
    for shape_data in all_shapes:
        color = clf_colors.get(shape_data['clf_name'], clf_colors['unknown'])
        
        if shape_data['type'] == 'path':
            points = shape_data['points']
            draw_shape(plt, points, color)
            
            # Add to legend
            if shape_data['clf_name'] not in legend_added:
                plt.plot([], [], color=color, label=shape_data['clf_name'])
                legend_added.add(shape_data['clf_name'])
                
        elif shape_data['type'] == 'circle':
            circle = plt.Circle(shape_data['center'], shape_data['radius'], 
                              color=color, fill=False, alpha=0.7)
            plt.gca().add_artist(circle)
            
            # Add to legend
            if shape_data['clf_name'] not in legend_added:
                plt.plot([], [], color=color, label=shape_data['clf_name'])
                legend_added.add(shape_data['clf_name'])
    
    plt.title(f'Shapes by CLF Source at Height {height}mm')
    add_platform_labels(plt)
    set_platform_limits(plt)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Save
    filename = f'shapes_by_clf_{height}mm.png'
    output_path = os.path.join(output_dir, filename)
    save_platform_figure(plt, output_path)
    print(f"Saved CLF visualization: {output_path}")


def create_visualization_by_type(all_shapes, shape_type_colors, output_dir, height):
    """Create visualization colored by shape type/category."""
    print(f"Creating shape type visualization...")
    
    # Create figure
    setup_platform_figure()
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    # Draw shapes colored by type
    legend_added = set()
    
    for shape_data in all_shapes:
        shape_category = shape_data.get('shape_category', 'regular_shape')
        color = shape_type_colors.get(shape_category, 'gray')
        
        if shape_data['type'] == 'path':
            points = shape_data['points']
            draw_shape(plt, points, color)
            
            # Add to legend
            if shape_category not in legend_added:
                plt.plot([], [], color=color, label=shape_category.replace('_', ' ').title())
                legend_added.add(shape_category)
                
        elif shape_data['type'] == 'circle':
            circle = plt.Circle(shape_data['center'], shape_data['radius'], 
                              color=color, fill=False, alpha=0.7)
            plt.gca().add_artist(circle)
            
            # Add to legend
            if 'circle' not in legend_added:
                plt.plot([], [], color=color, label='Circle')
                legend_added.add('circle')
    
    plt.title(f'Shapes by Type at Height {height}mm')
    add_platform_labels(plt)
    set_platform_limits(plt)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Save
    filename = f'shapes_by_type_{height}mm.png'
    output_path = os.path.join(output_dir, filename)
    save_platform_figure(plt, output_path)
    print(f"Saved type visualization: {output_path}")


def create_holes_visualization(all_shapes, potential_holes, output_dir, height):
    """Create visualization highlighting potential holes."""
    print(f"Creating holes visualization...")
    
    # Create figure
    setup_platform_figure()
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    # Draw all shapes in gray first
    for shape_data in all_shapes:
        if shape_data['type'] == 'path':
            points = shape_data['points']
            draw_shape(plt, points, 'lightgray')
        elif shape_data['type'] == 'circle':
            circle = plt.Circle(shape_data['center'], shape_data['radius'], 
                              color='lightgray', fill=False, alpha=0.3)
            plt.gca().add_artist(circle)
    
    # Highlight potential holes in red
    for hole_data in potential_holes:
        if hole_data['type'] == 'path':
            points = hole_data['points']
            draw_shape(plt, points, 'red', linewidth=2)
        elif hole_data['type'] == 'circle':
            circle = plt.Circle(hole_data['center'], hole_data['radius'], 
                              color='red', fill=False, alpha=0.8, linewidth=2)
            plt.gca().add_artist(circle)
    
    # Add legend
    plt.plot([], [], color='lightgray', label='Regular Shapes')
    plt.plot([], [], color='red', label=f'Potential Holes ({len(potential_holes)})')
    
    plt.title(f'Potential Holes at Height {height}mm')
    add_platform_labels(plt)
    set_platform_limits(plt)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Save
    filename = f'potential_holes_{height}mm.png'
    output_path = os.path.join(output_dir, filename)
    save_platform_figure(plt, output_path)
    print(f"Saved holes visualization: {output_path}")


def save_analysis_data(all_shapes, shapes_by_clf, shapes_by_type, potential_holes, output_dir, height):
    """Save detailed analysis data to JSON files."""
    print(f"Saving analysis data...")
    
    # Prepare data for JSON serialization
    def prepare_shape_for_json(shape_data):
        """Convert shape data to JSON-serializable format."""
        json_shape = {}
        for key, value in shape_data.items():
            if key == 'points':
                json_shape[key] = value.tolist() if hasattr(value, 'tolist') else value
            elif key == 'center':
                json_shape[key] = value.tolist() if hasattr(value, 'tolist') else value
            elif isinstance(value, np.ndarray):
                json_shape[key] = value.tolist()
            elif isinstance(value, (np.integer, np.floating, np.bool_)):
                json_shape[key] = value.item()
            elif isinstance(value, bool):
                json_shape[key] = bool(value)
            elif value is None:
                json_shape[key] = None
            elif isinstance(value, dict):
                # Recursively handle nested dictionaries
                json_shape[key] = {}
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, (np.integer, np.floating, np.bool_)):
                        json_shape[key][nested_key] = nested_value.item()
                    elif isinstance(nested_value, bool):
                        json_shape[key][nested_key] = bool(nested_value)
                    else:
                        json_shape[key][nested_key] = nested_value
            else:
                json_shape[key] = value
        return json_shape
    
    # Save all shapes
    all_shapes_json = [prepare_shape_for_json(shape) for shape in all_shapes]
    with open(os.path.join(output_dir, f'all_shapes_{height}mm.json'), 'w') as f:
        json.dump(all_shapes_json, f, indent=2)
    
    # Save potential holes
    potential_holes_json = [prepare_shape_for_json(hole) for hole in potential_holes]
    with open(os.path.join(output_dir, f'potential_holes_{height}mm.json'), 'w') as f:
        json.dump(potential_holes_json, f, indent=2)
    
    # Save summary statistics
    summary = {
        'height': height,
        'total_shapes': len(all_shapes),
        'potential_holes': len(potential_holes),
        'shapes_by_clf': {clf: len(shapes) for clf, shapes in shapes_by_clf.items()},
        'shapes_by_type': {type_name: len(shapes) for type_name, shapes in shapes_by_type.items()},
        'multi_path_shapes': len([s for s in all_shapes if s.get('is_multi_path', False)]),
        'likely_ellipses': len([s for s in all_shapes if s.get('is_likely_ellipse', False)])
    }
    
    with open(os.path.join(output_dir, f'analysis_summary_{height}mm.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Saved analysis data to {output_dir}")


def print_analysis_summary(all_shapes, shapes_by_clf, shapes_by_type, potential_holes):
    """Print summary of analysis results."""
    print(f"\n=== ANALYSIS SUMMARY ===")
    print(f"Total shapes: {len(all_shapes)}")
    print(f"Potential holes: {len(potential_holes)}")
    
    print(f"\nShapes by CLF:")
    for clf, shapes in shapes_by_clf.items():
        print(f"  {clf}: {len(shapes)} shapes")
    
    print(f"\nShapes by type:")
    for type_name, shapes in shapes_by_type.items():
        print(f"  {type_name}: {len(shapes)} shapes")
    
    print(f"\nMulti-path shapes: {len([s for s in all_shapes if s.get('is_multi_path', False)])}")
    print(f"Likely ellipses: {len([s for s in all_shapes if s.get('is_likely_ellipse', False)])}")
    
    if potential_holes:
        print(f"\nPotential holes details:")
        for hole in potential_holes:
            print(f"  - {hole['clf_name']}: Shape {hole['shape_index']}, Path {hole['path_index']}")
            if hole['properties']:
                print(f"    Area: {hole['properties']['area']:.2f}, Compactness: {hole['properties']['compactness']:.3f}")


if __name__ == "__main__":
    # Configure matplotlib
    plt.style.use('default')
    
    # Run the enhanced analysis
    enhanced_holes_test_at_height(134.0)
    
    print("\nEnhanced holes analysis complete!")
