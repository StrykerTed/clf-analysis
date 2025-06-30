#!/usr/bin/env python3
"""
Enhanced Hole Detection Analysis - Scans multiple heights to find shapes with holes
"""

import os
import sys
import numpy as np

# Add paths
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import setup_paths
from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import find_clf_files

def find_shapes_with_holes_at_multiple_heights(clf_file_path, heights=[1.0, 2.0, 5.0, 10.0]):
    """Search for shapes with holes across multiple heights"""
    
    try:
        part = CLFFile(clf_file_path)
        found_holes = []
        
        for height in heights:
            layer = part.find(height)
            if layer is None or not hasattr(layer, 'shapes'):
                continue
                
            for i, shape in enumerate(layer.shapes):
                if hasattr(shape, 'points') and len(shape.points) > 1:
                    # Found a shape with holes!
                    identifier = "unknown"
                    if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                        identifier = shape.model.id
                    
                    found_holes.append({
                        'file': os.path.basename(clf_file_path),
                        'height': height,
                        'shape_index': i,
                        'identifier': identifier,
                        'num_paths': len(shape.points),
                        'num_holes': len(shape.points) - 1,
                        'shape': shape
                    })
        
        return found_holes
        
    except Exception as e:
        print(f"❌ Error analyzing {clf_file_path}: {e}")
        return []

def demonstrate_hole_characteristics(shape):
    """Analyze and demonstrate hole characteristics"""
    
    exterior = shape.points[0]
    holes = shape.points[1:]
    
    print(f"\n🔍 DETAILED HOLE ANALYSIS:")
    print(f"   🔷 Exterior boundary: {len(exterior)} points")
    
    # Calculate areas and winding
    def signed_area(points):
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return area / 2.0
    
    ext_area = signed_area(exterior)
    ext_winding = "CCW" if ext_area > 0 else "CW"
    
    print(f"   🔷 Exterior area: {abs(ext_area):.2f}")
    print(f"   🔷 Exterior winding: {ext_winding}")
    
    for i, hole in enumerate(holes):
        hole_area = signed_area(hole)
        hole_winding = "CCW" if hole_area > 0 else "CW"
        
        print(f"   🕳️  Hole {i+1}: {len(hole)} points")
        print(f"   🕳️  Hole {i+1} area: {abs(hole_area):.2f}")
        print(f"   🕳️  Hole {i+1} winding: {hole_winding}")
        
        # Check if hole winding is opposite to exterior (standard for holes)
        if hole_winding != ext_winding:
            print(f"   ✅ Hole {i+1} has opposite winding - CONFIRMED HOLE")
        else:
            print(f"   ⚠️  Hole {i+1} has same winding - May be separate shape")

def comprehensive_hole_scan(build_path):
    """Comprehensive scan for holes across all files and heights"""
    
    print(f"🔍 COMPREHENSIVE HOLE SCAN")
    print(f"Build: {os.path.basename(build_path)}")
    print("=" * 60)
    
    clf_files = find_clf_files(build_path)
    print(f"📁 Scanning {len(clf_files)} CLF files...")
    
    all_holes_found = []
    
    for clf_info in clf_files:
        holes_in_file = find_shapes_with_holes_at_multiple_heights(clf_info['path'])
        all_holes_found.extend(holes_in_file)
    
    if not all_holes_found:
        print("❌ No shapes with holes found in any files at any height!")
        return
    
    print(f"\n🎉 FOUND {len(all_holes_found)} SHAPES WITH HOLES!")
    print("=" * 60)
    
    for i, hole_data in enumerate(all_holes_found):
        print(f"\n🕳️  SHAPE WITH HOLES #{i+1}:")
        print(f"   📄 File: {hole_data['file']}")
        print(f"   📏 Height: {hole_data['height']}mm")
        print(f"   🆔 Identifier: {hole_data['identifier']}")
        print(f"   📦 Total paths: {hole_data['num_paths']}")
        print(f"   🕳️  Number of holes: {hole_data['num_holes']}")
        
        # Demonstrate detailed analysis on first few
        if i < 3:  # Only analyze first 3 in detail
            demonstrate_hole_characteristics(hole_data['shape'])
    
    return all_holes_found

if __name__ == "__main__":
    build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/build-431627"
    
    if os.path.exists(build_path):
        results = comprehensive_hole_scan(build_path)
    else:
        print(f"❌ Build path not found: {build_path}")
