#!/usr/bin/env python3
"""
Comprehensive hole analysis script that loops through every layer height and finds all holes.
Focuses on skin files only and detects anomalies in hole count and shape.
"""

import os
import sys
import numpy as np
import json
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import setup_paths

from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import (
    find_clf_files,
    should_skip_folder,
    load_exclusion_patterns
)


def is_skin_file(file_path, folder_name):
    """Check if a file is a skin file based on folder name."""
    skin_indicators = ['skin', 'Skin', 'SKIN']
    return any(indicator in folder_name for indicator in skin_indicators)


def calculate_bbox_from_points(points):
    """Calculate bounding box from a list of points."""
    if not points or len(points) == 0:
        return None
    
    try:
        points_array = np.array(points) if not isinstance(points, np.ndarray) else points
        if len(points_array.shape) == 2 and points_array.shape[1] >= 2:
            min_x, max_x = np.min(points_array[:, 0]), np.max(points_array[:, 0])
            min_y, max_y = np.min(points_array[:, 1]), np.max(points_array[:, 1])
            
            return {
                'min_x': float(min_x),
                'min_y': float(min_y), 
                'max_x': float(max_x),
                'max_y': float(max_y),
                'width': float(max_x - min_x),
                'height': float(max_y - min_y)
            }
    except Exception as e:
        print(f"Error calculating bbox: {e}")
        return None
    
    return None


def analyze_hole_shape(bbox):
    """
    Analyze if a hole bbox matches expected elongated oval pattern.
    Based on the sample image, holes should be reasonably elongated.
    """
    if not bbox:
        return False, "No bbox data"
    
    width = bbox['width']
    height = bbox['height']
    
    # Basic size check - holes shouldn't be too tiny or huge
    min_size = 0.1  # mm
    max_size = 50.0  # mm
    
    if width < min_size or height < min_size:
        return False, f"Too small: {width:.2f}x{height:.2f}mm"
    
    if width > max_size or height > max_size:
        return False, f"Too large: {width:.2f}x{height:.2f}mm"
    
    # Aspect ratio check - should be somewhat elongated (oval-like)
    # From the sample image, holes appear to have aspect ratios roughly between 1.5:1 and 4:1
    aspect_ratio = max(width, height) / min(width, height)
    min_aspect = 1.2  # Allow nearly square holes
    max_aspect = 6.0  # Allow quite elongated holes
    
    if aspect_ratio < min_aspect:
        return False, f"Too square: aspect ratio {aspect_ratio:.2f}"
    
    if aspect_ratio > max_aspect:
        return False, f"Too elongated: aspect ratio {aspect_ratio:.2f}"
    
    # Area check - reasonable hole size
    area = width * height
    min_area = 0.1  # mm²
    max_area = 100.0  # mm²
    
    if area < min_area:
        return False, f"Area too small: {area:.2f}mm²"
    
    if area > max_area:
        return False, f"Area too large: {area:.2f}mm²"
    
    return True, f"Valid hole: {width:.2f}x{height:.2f}mm, aspect {aspect_ratio:.2f}, area {area:.2f}mm²"


def main():
    """Main function to analyze holes across all layer heights."""
    
    # Configuration
    BUILD_DIR = "abp_contents/preprocess build-424292"
    MAX_HOLES_PER_LAYER = 18
    
    # Create output directory
    output_dir = "my_outputs/hole_analysis"
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("COMPREHENSIVE HOLE ANALYSIS - ALL LAYER HEIGHTS")
    print("=" * 80)
    print(f"Build directory: {BUILD_DIR}")
    print(f"Max holes per layer threshold: {MAX_HOLES_PER_LAYER}")
    print(f"Output directory: {output_dir}")
    print(f"Analysis started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load exclusion patterns
    try:
        script_dir = os.path.join(project_root, 'src', 'config')
        exclusion_patterns = load_exclusion_patterns(script_dir)
        print(f"Loaded exclusion patterns: {exclusion_patterns}")
    except Exception as e:
        print(f"Error loading exclusion patterns: {e}")
        exclusion_patterns = []
    
    # Build the full path to the build directory
    build_path = os.path.join(project_root, BUILD_DIR)
    if not os.path.exists(build_path):
        print(f"ERROR: Build directory not found at {build_path}")
        return
    
    # Find all CLF files and filter for skin files only
    all_clf_files = find_clf_files(build_path)
    print(f"Found {len(all_clf_files)} CLF files total")
    
    # Filter for skin files only
    skin_files = []
    for clf_info in all_clf_files:
        # Skip excluded folders
        if should_skip_folder(clf_info['folder'], exclusion_patterns):
            continue
        
        # Only keep skin files
        if is_skin_file(clf_info['path'], clf_info['folder']):
            skin_files.append(clf_info)
    
    print(f"Found {len(skin_files)} skin files to analyze")
    for skin_file in skin_files:
        print(f"  - {skin_file['name']} in {skin_file['folder']}")
    print()
    
    if not skin_files:
        print("ERROR: No skin files found!")
        return
    
    # Analysis results
    analysis_results = {
        'start_time': datetime.now().isoformat(),
        'build_directory': BUILD_DIR,
        'max_holes_threshold': MAX_HOLES_PER_LAYER,
        'skin_files_analyzed': len(skin_files),
        'layer_analysis': {},
        'errors': [],
        'warnings': [],
        'summary': {}
    }
    
    # Find the maximum height from all skin files
    max_height = 0
    print("Finding maximum layer height from skin files...")
    
    for clf_info in skin_files:
        try:
            part = CLFFile(clf_info['path'])
            if hasattr(part, 'layers'):
                for layer in part.layers:
                    if hasattr(layer, 'z'):
                        max_height = max(max_height, layer.z)
        except Exception as e:
            print(f"Error reading heights from {clf_info['name']}: {e}")
            continue
    
    # Generate ALL heights from 0 to max_height in 0.05mm increments
    layer_thickness = 0.05  # mm - typical layer thickness
    sorted_heights = []
    current_height = 0.0
    
    while current_height <= max_height:
        sorted_heights.append(round(current_height, 3))  # Round to avoid floating point issues
        current_height += layer_thickness
    
    print(f"Generated {len(sorted_heights)} layer heights from 0.0mm to {max_height:.3f}mm in {layer_thickness}mm increments")
    print(f"First 10 heights: {sorted_heights[:10]}")
    print(f"Last 10 heights: {sorted_heights[-10:]}")
    print()
    
    # Analyze each height
    print("Analyzing holes at each layer height...")
    print("-" * 80)
    
    for height_idx, height in enumerate(sorted_heights):
        print(f"Analyzing height {height}mm ({height_idx + 1}/{len(sorted_heights)})")
        
        layer_data = {
            'height_mm': height,
            'total_holes': 0,
            'files_with_holes': 0,
            'hole_details': [],
            'shape_errors': [],
            'bbox_errors': []
        }
        
        # Check each skin file at this height
        for clf_info in skin_files:
            try:
                part = CLFFile(clf_info['path'])
                layer = part.find(height)
                
                if layer is None:
                    continue
                
                # Look for holes in the shape data
                file_holes = []
                if hasattr(layer, 'shapes') and layer.shapes is not None:
                    try:
                        shapes_list = list(layer.shapes) if hasattr(layer.shapes, '__iter__') else []
                        
                        for shape_idx, shape in enumerate(shapes_list):
                            if hasattr(shape, 'points'):
                                try:
                                    # Safely check if shape.points exists and has content
                                    points_data = getattr(shape, 'points', None)
                                    if points_data is not None:
                                        # Convert to list to avoid numpy array truthiness issues
                                        points_list = list(points_data) if hasattr(points_data, '__iter__') else []
                                        
                                        # Look for multiple paths (holes are typically additional paths)
                                        if len(points_list) > 1:
                                            # Process paths after the first one as potential holes
                                            for path_idx in range(1, len(points_list)):
                                                try:
                                                    hole_points = points_list[path_idx]
                                                    hole_bbox = calculate_bbox_from_points(hole_points)
                                                    
                                                    if hole_bbox:
                                                        is_valid, validation_msg = analyze_hole_shape(hole_bbox)
                                                        
                                                        hole_info = {
                                                            'file_name': clf_info['name'],
                                                            'folder': clf_info['folder'],
                                                            'shape_index': shape_idx,
                                                            'path_index': path_idx,
                                                            'bbox': hole_bbox,
                                                            'is_valid': is_valid,
                                                            'validation_msg': validation_msg
                                                        }
                                                        
                                                        file_holes.append(hole_info)
                                                        layer_data['hole_details'].append(hole_info)
                                                        
                                                        if not is_valid:
                                                            layer_data['bbox_errors'].append({
                                                                'file': clf_info['name'],
                                                                'error': validation_msg,
                                                                'bbox': hole_bbox
                                                            })
                                                except Exception as path_e:
                                                    # Skip this path if it can't be processed
                                                    continue
                                except Exception as shape_e:
                                    # Skip this shape if it can't be processed
                                    continue
                    except Exception as layer_e:
                        print(f"  ERROR: Error processing layer shapes in {clf_info['name']}: {layer_e}")
                        continue
                
                if file_holes:
                    layer_data['files_with_holes'] += 1
                    layer_data['total_holes'] += len(file_holes)
                
            except Exception as e:
                error_msg = f"Error processing {clf_info['name']} at height {height}mm: {e}"
                print(f"  ERROR: {error_msg}")
                analysis_results['errors'].append(error_msg)
                continue
        
        # Check for too many holes
        if layer_data['total_holes'] > MAX_HOLES_PER_LAYER:
            error_msg = f"Height {height}mm: Found {layer_data['total_holes']} holes (exceeds limit of {MAX_HOLES_PER_LAYER})"
            print(f"  ERROR: {error_msg}")
            analysis_results['errors'].append(error_msg)
        
        # Report findings for this height
        if layer_data['total_holes'] > 0:
            print(f"  Height {height}mm: {layer_data['total_holes']} holes in {layer_data['files_with_holes']} files")
            if layer_data['bbox_errors']:
                print(f"    {len(layer_data['bbox_errors'])} bbox validation errors")
        
        analysis_results['layer_analysis'][str(height)] = layer_data
    
    print()
    print("-" * 80)
    
    # Generate summary
    total_holes = sum(layer['total_holes'] for layer in analysis_results['layer_analysis'].values())
    layers_with_holes = sum(1 for layer in analysis_results['layer_analysis'].values() if layer['total_holes'] > 0)
    total_bbox_errors = sum(len(layer['bbox_errors']) for layer in analysis_results['layer_analysis'].values())
    
    analysis_results['summary'] = {
        'total_layers_analyzed': len(sorted_heights),
        'layers_with_holes': layers_with_holes,
        'total_holes_found': total_holes,
        'total_bbox_errors': total_bbox_errors,
        'total_errors': len(analysis_results['errors']),
        'max_holes_in_layer': max((layer['total_holes'] for layer in analysis_results['layer_analysis'].values()), default=0)
    }
    
    # Print summary
    print("ANALYSIS SUMMARY:")
    print(f"  Total layers analyzed: {analysis_results['summary']['total_layers_analyzed']}")
    print(f"  Layers with holes: {analysis_results['summary']['layers_with_holes']}")
    print(f"  Total holes found: {analysis_results['summary']['total_holes_found']}")
    print(f"  Max holes in any layer: {analysis_results['summary']['max_holes_in_layer']}")
    print(f"  Bbox validation errors: {analysis_results['summary']['total_bbox_errors']}")
    print(f"  Processing errors: {analysis_results['summary']['total_errors']}")
    
    if analysis_results['errors']:
        print("\nERRORS FOUND:")
        for error in analysis_results['errors']:
            print(f"  - {error}")
    
    # Save detailed results
    analysis_results['end_time'] = datetime.now().isoformat()
    
    output_file = os.path.join(output_dir, f"comprehensive_hole_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"\nDetailed analysis saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
