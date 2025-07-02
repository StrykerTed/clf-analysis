#!/usr/bin/env python3
"""
Analyze All Shapes at Height Script
Runs detailed shape analysis for ALL CLF files at a given height,
combining all shapes with holes into a single comprehensive view.
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

def extract_all_shape_attributes(shape, shape_index, file_name):
    """Extract all possible attributes from a shape object"""
    print(f"\n{'='*80}")
    print(f"🔍 DETAILED ANALYSIS OF SHAPE {shape_index + 1} FROM {file_name}")
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

def analyze_path_relationships(shape, shape_index, file_name):
    """Analyze relationships between paths in a multi-path shape"""
    if not hasattr(shape, 'points') or len(shape.points) < 2:
        return
    
    print(f"\n🔗 PATH RELATIONSHIP ANALYSIS FOR SHAPE {shape_index + 1} IN {file_name}:")
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

def save_combined_data_to_json(all_shapes_data, output_file, height):
    """Save all extracted shape data to JSON for comprehensive analysis"""
    print(f"\n💾 Saving combined shape data to: {output_file}")
    
    combined_data = {
        'analysis_height': height,
        'total_files_analyzed': len(all_shapes_data),
        'total_shapes': sum(len(file_data['shapes']) for file_data in all_shapes_data),
        'files': []
    }
    
    for file_data in all_shapes_data:
        file_info = {
            'file_path': file_data['file_path'],
            'file_name': file_data['file_name'],
            'num_shapes': len(file_data['shapes']),
            'shapes': []
        }
        
        for shape_data in file_data['shapes']:
            shape_info = {
                'shape_index': shape_data['shape_index'],
                'identifier': shape_data.get('identifier', 'unknown'),
                'file_source': file_data['file_name'],
                'num_paths': len(shape_data['paths']),
                'has_holes': len(shape_data['paths']) > 1,
                'total_area': sum(path['area'] for path in shape_data['paths']),
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
                    'is_closed': path_data['is_closed'],
                    'is_likely_hole': path_data.get('is_likely_hole', False)
                }
                shape_info['paths'].append(path_info)
            
            file_info['shapes'].append(shape_info)
        
        combined_data['files'].append(file_info)
    
    with open(output_file, 'w') as f:
        json.dump(combined_data, f, indent=2)
    
    print(f"✅ Combined shape data saved successfully")
    print(f"📊 Summary: {combined_data['total_shapes']} shapes from {combined_data['total_files_analyzed']} files")
    
    # Print summary of shapes with holes
    shapes_with_holes = []
    for file_data in combined_data['files']:
        for shape in file_data['shapes']:
            if shape['has_holes']:
                shapes_with_holes.append({
                    'file': shape['file_source'],
                    'shape_id': shape['identifier'],
                    'num_paths': shape['num_paths'],
                    'total_area': shape['total_area']
                })
    
    if shapes_with_holes:
        print(f"\n🕳️  Found {len(shapes_with_holes)} shapes with holes:")
        for shape in shapes_with_holes:
            print(f"   - File: {shape['file']}, ID: {shape['shape_id']}, Paths: {shape['num_paths']}, Area: {shape['total_area']:.2f}")
    else:
        print(f"\n⚪ No shapes with holes found at height {height}mm")

def classify_paths_as_holes(shape_data):
    """Classify paths as exterior boundaries or holes based on area and winding"""
    if len(shape_data['paths']) <= 1:
        return shape_data
    
    paths = shape_data['paths']
    
    # Sort paths by area (largest first)
    sorted_paths = sorted(enumerate(paths), key=lambda x: x[1]['area'], reverse=True)
    
    # The largest path is likely the exterior
    largest_idx, largest_path = sorted_paths[0]
    largest_path['is_likely_hole'] = False
    largest_path['classification'] = 'exterior'
    
    # Smaller paths are likely holes
    for i, (original_idx, path) in enumerate(sorted_paths[1:], 1):
        path['is_likely_hole'] = True
        path['classification'] = 'hole'
        
        # Additional check: if winding is opposite to largest, it's definitely a hole
        if path['winding'] != largest_path['winding']:
            path['confidence'] = 'high'
        else:
            path['confidence'] = 'medium'
    
    return shape_data

def analyze_clf_file_at_height(clf_file_path, height):
    """Analyze a single CLF file at given height"""
    file_name = os.path.basename(clf_file_path)
    print(f"\n🔍 Analyzing {file_name} at height {height}mm...")
    
    try:
        part = CLFFile(clf_file_path)
        layer = part.find(height)
        
        if layer is None:
            print(f"❌ No layer found at height {height}mm in {file_name}")
            return None
            
        if not hasattr(layer, 'shapes'):
            print(f"❌ Layer has no shapes in {file_name}")
            return None
            
        total_shapes = len(layer.shapes)
        print(f"📊 Found {total_shapes} shapes in {file_name}")
        
        file_shapes_data = []
        
        for i, shape in enumerate(layer.shapes):
            if hasattr(shape, 'points'):
                num_paths = len(shape.points)
                
                # Get identifier if available
                identifier = "unknown"
                if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                    identifier = shape.model.id
                
                print(f"   🔸 Shape {i+1}: {num_paths} path(s) (ID: {identifier})")
                
                # Extract detailed attributes (optional - comment out for less verbose output)
                # extract_all_shape_attributes(shape, i, file_name)
                
                # Analyze path relationships if multiple paths
                if num_paths > 1:
                    print(f"   🕳️  Shape has multiple paths - analyzing for holes...")
                    analyze_path_relationships(shape, i, file_name)
                
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
                
                # Classify paths as holes or exteriors
                shape_data = classify_paths_as_holes(shape_data)
                
                file_shapes_data.append(shape_data)
        
        return {
            'file_path': clf_file_path,
            'file_name': file_name,
            'shapes': file_shapes_data
        }
        
    except Exception as e:
        print(f"❌ Error analyzing {file_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_all_clf_files_at_height(build_path, height=8.2):
    """Main function to analyze all CLF files at a given height"""
    print(f"\n🎯 ANALYZING ALL CLF FILES AT HEIGHT {height}mm")
    print(f"📁 Build Path: {build_path}")
    print(f"{'='*100}")
    
    if not os.path.exists(build_path):
        print(f"❌ Build path not found: {build_path}")
        return
    
    # Find all CLF files
    print(f"🔍 Searching for CLF files...")
    clf_files = find_clf_files(build_path)
    print(f"📊 Found {len(clf_files)} CLF files")
    
    all_shapes_data = []
    files_with_shapes = 0
    total_shapes_found = 0
    
    for i, clf_info in enumerate(clf_files):
        print(f"\n{'='*60}")
        print(f"📄 Processing file {i+1}/{len(clf_files)}")
        
        file_data = analyze_clf_file_at_height(clf_info['path'], height)
        
        if file_data and file_data['shapes']:
            all_shapes_data.append(file_data)
            files_with_shapes += 1
            total_shapes_found += len(file_data['shapes'])
            
            # Quick summary for this file
            shapes_with_holes = [s for s in file_data['shapes'] if len(s['paths']) > 1]
            if shapes_with_holes:
                print(f"   🕳️  Found {len(shapes_with_holes)} shapes with holes in this file")
    
    print(f"\n{'='*100}")
    print(f"🎉 ANALYSIS COMPLETE!")
    print(f"📊 Summary:")
    print(f"   - Total CLF files: {len(clf_files)}")
    print(f"   - Files with shapes at {height}mm: {files_with_shapes}")
    print(f"   - Total shapes found: {total_shapes_found}")
    
    if all_shapes_data:
        # Save combined data to JSON
        output_file = f"all_shapes_analysis_{height}mm.json"
        save_combined_data_to_json(all_shapes_data, output_file, height)
        
        # Additional analysis: count holes across all files
        total_holes = 0
        files_with_holes = 0
        
        for file_data in all_shapes_data:
            file_has_holes = False
            for shape in file_data['shapes']:
                holes_in_shape = len([p for p in shape['paths'] if p.get('is_likely_hole', False)])
                total_holes += holes_in_shape
                if holes_in_shape > 0:
                    file_has_holes = True
            if file_has_holes:
                files_with_holes += 1
        
        print(f"\n🕳️  HOLE ANALYSIS:")
        print(f"   - Files containing holes: {files_with_holes}")
        print(f"   - Total holes found: {total_holes}")
        
        return all_shapes_data
    else:
        print(f"❌ No shapes found at height {height}mm in any file")
        return None

if __name__ == "__main__":
    # Analyze all files in the preprocess build-424292 folder
    build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/preprocess build-424292"
    
    # Set the height to analyze
    analysis_height = 136.55  # Change this to analyze different heights
    
    print(f"🚀 Starting comprehensive analysis at height {analysis_height}mm")
    
    all_data = analyze_all_clf_files_at_height(build_path, height=analysis_height)
    
    if all_data:
        print(f"\n✅ Analysis complete! Check the generated JSON file for detailed results.")
        print(f"💡 Next steps:")
        print(f"   1. Review 'all_shapes_analysis_{analysis_height}mm.json' for detailed data")
        print(f"   2. Run visualization scripts to see the shapes and holes")
        print(f"   3. Check web app for interactive exploration")
    else:
        print(f"\n❌ No data found. Try a different height or check the build path.")
