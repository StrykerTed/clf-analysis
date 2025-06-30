#!/usr/bin/env python3
"""
Enhanced CLF Analysis with Hole Detection
Properly processes exterior boundaries and holes as separate entities
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib
matplotlib.use('Agg')

# Add paths
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import setup_paths
from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import find_clf_files
from utils.myfuncs.plotTools import setup_platform_figure, save_platform_figure

def analyze_layer_with_holes(clf_info, height):
    """Enhanced layer analysis that properly detects and categorizes holes"""
    
    shape_data = {
        'exterior_shapes': [],
        'holes': [],
        'total_shapes': 0,
        'shapes_with_holes': 0,
        'total_holes': 0
    }
    
    try:
        part = CLFFile(clf_info['path'])
        layer = part.find(height)
        
        if layer is None or not hasattr(layer, 'shapes'):
            return shape_data
        
        shape_data['total_shapes'] = len(layer.shapes)
        
        for shape_idx, shape in enumerate(layer.shapes):
            if not hasattr(shape, 'points'):
                continue
                
            # Get identifier
            identifier = "unknown"
            if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                identifier = str(shape.model.id)
            
            num_paths = len(shape.points)
            
            if num_paths == 1:
                # Simple shape with no holes
                exterior = shape.points[0]
                shape_info = {
                    'type': 'exterior',
                    'points': exterior,
                    'identifier': identifier,
                    'clf_file': clf_info['name'],
                    'clf_folder': clf_info['folder'],
                    'shape_index': shape_idx,
                    'has_holes': False,
                    'hole_count': 0
                }
                shape_data['exterior_shapes'].append(shape_info)
                
            elif num_paths > 1:
                # Shape with holes
                shape_data['shapes_with_holes'] += 1
                shape_data['total_holes'] += (num_paths - 1)
                
                exterior = shape.points[0]
                holes = shape.points[1:]
                
                # Add exterior boundary
                exterior_info = {
                    'type': 'exterior',
                    'points': exterior,
                    'identifier': identifier,
                    'clf_file': clf_info['name'],
                    'clf_folder': clf_info['folder'],
                    'shape_index': shape_idx,
                    'has_holes': True,
                    'hole_count': len(holes)
                }
                shape_data['exterior_shapes'].append(exterior_info)
                
                # Add each hole separately
                for hole_idx, hole in enumerate(holes):
                    hole_info = {
                        'type': 'hole',
                        'points': hole,
                        'identifier': identifier,
                        'clf_file': clf_info['name'],
                        'clf_folder': clf_info['folder'],
                        'shape_index': shape_idx,
                        'hole_index': hole_idx,
                        'parent_exterior': exterior
                    }
                    shape_data['holes'].append(hole_info)
        
        return shape_data
        
    except Exception as e:
        print(f"Error analyzing {clf_info['name']}: {e}")
        return shape_data

def create_hole_aware_visualization(clf_files, output_dir, height=1.0, 
                                  show_holes=True, fill_exteriors=True):
    """Create visualization that distinguishes between exterior shapes and holes"""
    
    print(f"Creating hole-aware visualization at {height}mm...")
    
    all_exteriors = []
    all_holes = []
    
    # Process all files
    for clf_info in clf_files:
        shape_data = analyze_layer_with_holes(clf_info, height)
        all_exteriors.extend(shape_data['exterior_shapes'])
        all_holes.extend(shape_data['holes'])
    
    print(f"Found {len(all_exteriors)} exterior shapes and {len(all_holes)} holes")
    
    if not all_exteriors and not all_holes:
        print("No shapes found to visualize")
        return None
    
    # Create visualization
    fig = setup_platform_figure(figsize=(15, 15))
    ax = plt.gca()
    
    # Remove margins and set limits
    ax.set_position([0, 0, 1, 1])
    plt.xlim(-125, 125)
    plt.ylim(-125, 125)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    plt.axis('off')
    
    # Define colors for different CLF files
    colors = {
        'Part.clf': 'blue',
        'WaferSupport.clf': 'red',
        'Net.clf': 'green'
    }
    
    # Draw exterior shapes
    for ext_shape in all_exteriors:
        color = colors.get(ext_shape['clf_file'], 'gray')
        points = ext_shape['points']
        
        if fill_exteriors:
            # Fill exterior shapes
            polygon = Polygon(points, facecolor=color, alpha=0.3, 
                            edgecolor=color, linewidth=1)
            ax.add_patch(polygon)
        else:
            # Just outline
            polygon = Polygon(points, facecolor='none', 
                            edgecolor=color, linewidth=1)
            ax.add_patch(polygon)
    
    # Draw holes (if enabled)
    if show_holes:
        for hole in all_holes:
            points = hole['points']
            # Holes are drawn as white cutouts with black borders
            hole_polygon = Polygon(points, facecolor='white', alpha=1.0, 
                                 edgecolor='black', linewidth=2)
            ax.add_patch(hole_polygon)
    
    plt.axis('equal')
    
    # Generate filename
    hole_suffix = "_with_holes" if show_holes else "_no_holes"
    fill_suffix = "_filled" if fill_exteriors else "_outline"
    filename = f'hole_aware_platform_{height}mm{hole_suffix}{fill_suffix}.png'
    output_path = os.path.join(output_dir, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    save_platform_figure(plt, output_path, pad_inches=0)
    print(f"Saved hole-aware visualization: {output_path}")
    
    return output_path

def generate_hole_statistics(clf_files, height=1.0):
    """Generate detailed statistics about holes in the build"""
    
    print(f"\n📊 HOLE STATISTICS AT {height}mm")
    print("=" * 50)
    
    total_exteriors = 0
    total_holes = 0
    total_shapes_with_holes = 0
    hole_counts_by_identifier = {}
    
    for clf_info in clf_files:
        shape_data = analyze_layer_with_holes(clf_info, height)
        
        total_exteriors += len(shape_data['exterior_shapes'])
        total_holes += shape_data['total_holes']
        total_shapes_with_holes += shape_data['shapes_with_holes']
        
        # Count holes by identifier
        for ext_shape in shape_data['exterior_shapes']:
            if ext_shape['has_holes']:
                identifier = ext_shape['identifier']
                hole_count = ext_shape['hole_count']
                
                if identifier not in hole_counts_by_identifier:
                    hole_counts_by_identifier[identifier] = {
                        'shapes': 0,
                        'total_holes': 0
                    }
                
                hole_counts_by_identifier[identifier]['shapes'] += 1
                hole_counts_by_identifier[identifier]['total_holes'] += hole_count
    
    print(f"📦 Total exterior shapes: {total_exteriors}")
    print(f"🕳️  Total holes: {total_holes}")
    print(f"🔗 Shapes with holes: {total_shapes_with_holes}")
    print(f"📋 Identifiers with holes: {len(hole_counts_by_identifier)}")
    
    if hole_counts_by_identifier:
        print(f"\n🆔 HOLES BY IDENTIFIER:")
        for identifier, stats in sorted(hole_counts_by_identifier.items()):
            print(f"   ID {identifier}: {stats['shapes']} shapes, {stats['total_holes']} holes")

def test_hole_detection():
    """Test the hole detection functionality"""
    
    build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/build-431627"
    test_height = 135.8  # Use the height where holes actually exist
    
    print("🔍 TESTING HOLE DETECTION FUNCTIONALITY")
    print("=" * 60)
    
    if not os.path.exists(build_path):
        print(f"❌ Build path not found: {build_path}")
        return
    
    clf_files = find_clf_files(build_path)
    # Filter to just non-excluded files for testing
    test_files = [f for f in clf_files if 'Part.clf' in f['name']][:5]
    
    print(f"📁 Testing with {len(test_files)} files")
    
    # Generate statistics
    generate_hole_statistics(test_files, test_height)
    
    # Create visualizations
    output_dir = "/tmp/hole_detection_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create different visualization types
    print(f"\n🎨 Creating visualizations...")
    
    # 1. With holes shown (filled exteriors)
    viz1 = create_hole_aware_visualization(test_files, output_dir, test_height, 
                                         show_holes=True, fill_exteriors=True)
    
    # 2. Without holes (just exteriors filled)
    viz2 = create_hole_aware_visualization(test_files, output_dir, test_height, 
                                         show_holes=False, fill_exteriors=True)
    
    # 3. With holes (outline only)
    viz3 = create_hole_aware_visualization(test_files, output_dir, test_height, 
                                         show_holes=True, fill_exteriors=False)
    
    print(f"\n✅ Test complete! Visualizations saved to: {output_dir}")
    
    return [viz1, viz2, viz3]

if __name__ == "__main__":
    test_hole_detection()
