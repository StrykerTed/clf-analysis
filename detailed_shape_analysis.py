#!/usr/bin/env python3
"""
Detailed Shape Analysis Script
Focuses on analyzing shapes at height 134.00mm to extract all possible information
about paths, especially the banana shape with ellipse inside.
"""

import os
import sys
import numpy as np
import json
from pprint import pprint

# Add paths
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import setup_paths
from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import find_clf_files

def extract_all_shape_attributes(shape, shape_index):
    """Extract all possible attributes from a shape object"""
    print(f"\n{'='*80}")
    print(f"🔍 DETAILED ANALYSIS OF SHAPE {shape_index + 1}")
    print(f"{'='*80}")
    
    # Basic shape information
    print(f"📊 Shape Object Type: {type(shape)}")
    print(f"📊 Shape Object: {shape}")
    
    # Get all attributes of the shape
    print(f"\n🔧 ALL SHAPE ATTRIBUTES:")
    all_attrs = dir(shape)
    for attr in sorted(all_attrs):
        if not attr.startswith('_'):  # Skip private attributes
            try:
                value = getattr(shape, attr)
                if callable(value):
                    print(f"   🔗 {attr}(): {type(value)} (method)")
                else:
                    print(f"   📋 {attr}: {value} ({type(value)})")
            except Exception as e:
                print(f"   ❌ {attr}: Error accessing - {e}")
    
    # Focus on specific important attributes
    print(f"\n🎯 KEY ATTRIBUTES ANALYSIS:")
    
    # Points analysis
    if hasattr(shape, 'points'):
        points = shape.points
        print(f"   📍 points: {len(points)} path(s)")
        
        for path_idx, path in enumerate(points):
            print(f"\n   🛤️  PATH {path_idx + 1}:")
            print(f"      📏 Number of points: {len(path)}")
            print(f"      📊 Point type: {type(path)}")
            
            if len(path) > 0:
                print(f"      🏁 First point: {path[0]}")
                print(f"      🏁 Last point: {path[-1]}")
                print(f"      📐 Min X,Y: ({min(p[0] for p in path):.3f}, {min(p[1] for p in path):.3f})")
                print(f"      📐 Max X,Y: ({max(p[0] for p in path):.3f}, {max(p[1] for p in path):.3f})")
                
                # Calculate center
                center_x = sum(p[0] for p in path) / len(path)
                center_y = sum(p[1] for p in path) / len(path)
                print(f"      🎯 Center: ({center_x:.3f}, {center_y:.3f})")
                
                # Check if path is closed
                is_closed = np.allclose(path[0], path[-1], atol=1e-6)
                print(f"      🔄 Is closed: {is_closed}")
                
                # Calculate area using shoelace formula
                area = calculate_polygon_area(path)
                print(f"      📐 Area: {area:.6f}")
                
                # Determine winding direction
                winding = get_winding_direction(path)
                print(f"      🌀 Winding: {winding}")
    
    # Model information
    if hasattr(shape, 'model'):
        model = shape.model
        print(f"\n   🏗️  MODEL INFORMATION:")
        print(f"      📊 Model type: {type(model)}")
        print(f"      📊 Model: {model}")
        
        # Get all model attributes
        model_attrs = dir(model)
        for attr in sorted(model_attrs):
            if not attr.startswith('_'):
                try:
                    value = getattr(model, attr)
                    if callable(value):
                        print(f"      🔗 model.{attr}(): {type(value)} (method)")
                    else:
                        print(f"      📋 model.{attr}: {value} ({type(value)})")
                except Exception as e:
                    print(f"      ❌ model.{attr}: Error accessing - {e}")
    
    # Additional attributes to check
    interesting_attrs = [
        'id', 'identifier', 'name', 'type', 'closed', 'area', 'bounds',
        'color', 'material', 'thickness', 'properties', 'metadata',
        'contour', 'contours', 'boundary', 'holes', 'exterior', 'interior'
    ]
    
    print(f"\n   🔍 CHECKING FOR SPECIFIC ATTRIBUTES:")
    for attr in interesting_attrs:
        if hasattr(shape, attr):
            try:
                value = getattr(shape, attr)
                print(f"      ✅ {attr}: {value} ({type(value)})")
            except Exception as e:
                print(f"      ❌ {attr}: Error accessing - {e}")
        else:
            print(f"      ⚪ {attr}: Not found")

def calculate_polygon_area(points):
    """Calculate the area of a polygon using the shoelace formula"""
    if len(points) < 3:
        return 0.0
    
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0

def get_winding_direction(points):
    """Get winding direction of a polygon"""
    if len(points) < 3:
        return "Unknown"
    
    n = len(points)
    signed_area = 0.0
    for i in range(n):
        j = (i + 1) % n
        signed_area += points[i][0] * points[j][1]
        signed_area -= points[j][0] * points[i][1]
    
    if signed_area > 0:
        return "CCW (Counter-Clockwise)"
    elif signed_area < 0:
        return "CW (Clockwise)"
    else:
        return "Degenerate"

def analyze_path_relationships(shape, shape_index):
    """Analyze relationships between paths in a multi-path shape"""
    if not hasattr(shape, 'points') or len(shape.points) < 2:
        return
    
    print(f"\n🔗 PATH RELATIONSHIP ANALYSIS FOR SHAPE {shape_index + 1}:")
    print(f"{'='*60}")
    
    paths = shape.points
    
    for i, path_a in enumerate(paths):
        for j, path_b in enumerate(paths):
            if i >= j:  # Only analyze unique pairs
                continue
                
            print(f"\n   🔄 Comparing Path {i+1} vs Path {j+1}:")
            
            # Area comparison
            area_a = calculate_polygon_area(path_a)
            area_b = calculate_polygon_area(path_b)
            print(f"      📐 Areas: {area_a:.6f} vs {area_b:.6f}")
            
            if area_a > area_b:
                print(f"      🔷 Path {i+1} is LARGER (likely exterior)")
                print(f"      🕳️  Path {j+1} is SMALLER (likely hole)")
            else:
                print(f"      🔷 Path {j+1} is LARGER (likely exterior)")
                print(f"      🕳️  Path {i+1} is SMALLER (likely hole)")
            
            # Winding direction comparison
            wind_a = get_winding_direction(path_a)
            wind_b = get_winding_direction(path_b)
            print(f"      🌀 Windings: '{wind_a}' vs '{wind_b}'")
            
            if wind_a != wind_b:
                print(f"      ✅ Different windings → One is likely a hole")
            else:
                print(f"      ⚠️  Same windings → Both might be exteriors")
            
            # Containment test (simple center point test)
            center_a = (sum(p[0] for p in path_a) / len(path_a), 
                       sum(p[1] for p in path_a) / len(path_a))
            center_b = (sum(p[0] for p in path_b) / len(path_b), 
                       sum(p[1] for p in path_b) / len(path_b))
            
            print(f"      🎯 Centers: ({center_a[0]:.3f}, {center_a[1]:.3f}) vs ({center_b[0]:.3f}, {center_b[1]:.3f})")
            
            # Point-in-polygon test
            is_a_in_b = is_point_in_polygon(center_a, path_b)
            is_b_in_a = is_point_in_polygon(center_b, path_a)
            
            print(f"      📍 Path {i+1} center in Path {j+1}: {is_a_in_b}")
            print(f"      📍 Path {j+1} center in Path {i+1}: {is_b_in_a}")
            
            if is_a_in_b and not is_b_in_a:
                print(f"      🎯 CONCLUSION: Path {i+1} is a HOLE inside Path {j+1}")
            elif is_b_in_a and not is_a_in_b:
                print(f"      🎯 CONCLUSION: Path {j+1} is a HOLE inside Path {i+1}")
            elif is_a_in_b and is_b_in_a:
                print(f"      🤔 STRANGE: Both centers are inside each other")
            else:
                print(f"      🔄 CONCLUSION: Paths are separate/adjacent")

def is_point_in_polygon(point, polygon):
    """Test if a point is inside a polygon using ray casting"""
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def save_path_data_to_json(shapes_data, output_file):
    """Save extracted path data to JSON for further analysis"""
    print(f"\n💾 Saving path data to: {output_file}")
    
    serializable_data = []
    
    for shape_data in shapes_data:
        shape_info = {
            'shape_index': shape_data['shape_index'],
            'identifier': shape_data.get('identifier', 'unknown'),
            'num_paths': len(shape_data['paths']),
            'paths': []
        }
        
        for path_idx, path_data in enumerate(shape_data['paths']):
            path_info = {
                'path_index': path_idx,
                'num_points': len(path_data['points']),
                'points': path_data['points'].tolist() if hasattr(path_data['points'], 'tolist') else path_data['points'],
                'area': path_data['area'],
                'winding': path_data['winding'],
                'center': path_data['center'],
                'bounds': path_data['bounds'],
                'is_closed': path_data['is_closed']
            }
            shape_info['paths'].append(path_info)
        
        serializable_data.append(shape_info)
    
    with open(output_file, 'w') as f:
        json.dump(serializable_data, f, indent=2)
    
    print(f"✅ Path data saved successfully")

def analyze_clf_at_height(clf_file_path, height=134.0):
    """Main analysis function for a specific CLF file at given height"""
    print(f"\n🎯 ANALYZING CLF FILE AT HEIGHT {height}mm")
    print(f"📁 File: {os.path.basename(clf_file_path)}")
    print(f"{'='*100}")
    
    try:
        part = CLFFile(clf_file_path)
        layer = part.find(height)
        
        if layer is None:
            print(f"❌ No layer found at height {height}mm")
            return
            
        if not hasattr(layer, 'shapes'):
            print("❌ Layer has no shapes")
            return
            
        total_shapes = len(layer.shapes)
        print(f"📊 Found {total_shapes} shapes in layer")
        
        shapes_data = []
        
        for i, shape in enumerate(layer.shapes):
            if hasattr(shape, 'points'):
                num_paths = len(shape.points)
                
                # Get identifier if available
                identifier = "unknown"
                if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                    identifier = shape.model.id
                
                print(f"\n🔸 Found shape with {num_paths} path(s) (ID: {identifier})")
                
                # Extract all attributes
                extract_all_shape_attributes(shape, i)
                
                # Analyze path relationships if multiple paths
                if num_paths > 1:
                    analyze_path_relationships(shape, i)
                
                # Store data for JSON export
                shape_data = {
                    'shape_index': i,
                    'identifier': identifier,
                    'paths': []
                }
                
                for path_idx, path in enumerate(shape.points):
                    path_data = {
                        'points': path,
                        'area': calculate_polygon_area(path),
                        'winding': get_winding_direction(path),
                        'center': (sum(p[0] for p in path) / len(path), sum(p[1] for p in path) / len(path)),
                        'bounds': {
                            'min_x': min(p[0] for p in path),
                            'max_x': max(p[0] for p in path),
                            'min_y': min(p[1] for p in path),
                            'max_y': max(p[1] for p in path)
                        },
                        'is_closed': np.allclose(path[0], path[-1], atol=1e-6)
                    }
                    shape_data['paths'].append(path_data)
                
                shapes_data.append(shape_data)
        
        # Save data to JSON
        output_file = f"shape_analysis_data_{height}mm.json"
        save_path_data_to_json(shapes_data, output_file)
        
        print(f"\n✅ Analysis complete! Found {len(shapes_data)} shapes with path data")
        
    except Exception as e:
        print(f"❌ Error analyzing {clf_file_path}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Focus specifically on the file: 5518-F-101_10_AN5518-F-101_Skin
    # Located in preprocess build-424292 folder
    target_file_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/preprocess build-424292/Models/5518-F-101_10_AN5518-F-101_Skin/Part.clf"
    
    if os.path.exists(target_file_path):
        print(f"✅ Found target file: {target_file_path}")
        analyze_clf_at_height(target_file_path, height=134.0)
    else:
        print(f"❌ Target file not found: {target_file_path}")
        
        # Fallback: search in preprocess build-424292
        build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/preprocess build-424292"
        if os.path.exists(build_path):
            print(f"\n🔍 Searching in: {build_path}")
            clf_files = find_clf_files(build_path)
            
            target_folder = "5518-F-101_10_AN5518-F-101_Skin"
            for clf_info in clf_files:
                if target_folder in clf_info['folder']:
                    print(f"✅ Found: {clf_info['path']}")
                    analyze_clf_at_height(clf_info['path'], height=134.0)
                    break
            else:
                print(f"❌ Could not find folder containing: {target_folder}")
                print("\n📋 Available folders:")
                for clf_info in clf_files[:10]:  # Show first 10
                    print(f"   - {clf_info['folder']}")
        else:
            print(f"❌ Build path not found: {build_path}")
