#!/usr/bin/env python3
"""
Hole Detection Analysis Script
Analyzes CLF shapes to identify exterior boundaries vs holes (interior boundaries)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Add paths
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import setup_paths
from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import find_clf_files

def analyze_shape_structure(clf_file_path, height=1.0):
    """Analyze the structure of shapes in a CLF file to identify holes"""
    print(f"\n🔍 Analyzing shape structure in: {os.path.basename(clf_file_path)} at height: {height}mm")
    
    try:
        part = CLFFile(clf_file_path)
        layer = part.find(height)
        
        if layer is None:
            print(f"❌ No layer found at height {height}mm")
            return
            
        if not hasattr(layer, 'shapes'):
            print("❌ Layer has no shapes")
            return
            
        shapes_with_holes = []
        total_shapes = len(layer.shapes)
        
        for i, shape in enumerate(layer.shapes):
            if hasattr(shape, 'points'):
                num_paths = len(shape.points)
                
                # Get identifier if available
                identifier = "unknown"
                if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                    identifier = shape.model.id
                
                print(f"\n🔸 Shape {i+1} (ID: {identifier}):")
                print(f"   📦 Number of paths: {num_paths}")
                
                if num_paths > 1:
                    print(f"   🕳️  HAS HOLES! {num_paths-1} hole(s) detected")
                    
                    # Analyze each path
                    exterior = shape.points[0]
                    holes = shape.points[1:]
                    
                    print(f"   🔷 Exterior boundary: {len(exterior)} points")
                    for j, hole in enumerate(holes):
                        print(f"   🕳️  Hole {j+1}: {len(hole)} points")
                    
                    # Store for visualization
                    shapes_with_holes.append({
                        'index': i,
                        'identifier': identifier,
                        'exterior': exterior,
                        'holes': holes,
                        'shape_obj': shape
                    })
                else:
                    print(f"   ✅ Simple shape (no holes)")
                    
        return shapes_with_holes
        
    except Exception as e:
        print(f"❌ Error analyzing {clf_file_path}: {e}")
        return []

def visualize_shapes_with_holes(shapes_with_holes, output_path):
    """Create visualization showing exterior boundaries and holes"""
    if not shapes_with_holes:
        print("📊 No shapes with holes found to visualize")
        return None
        
    print(f"\n🎨 Creating visualization of {len(shapes_with_holes)} shapes with holes...")
    
    fig, ax = plt.subplots(figsize=(12, 12))
    
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    for i, shape_data in enumerate(shapes_with_holes):
        color = colors[i % len(colors)]
        identifier = shape_data['identifier']
        exterior = shape_data['exterior']
        holes = shape_data['holes']
        
        # Draw exterior boundary (filled)
        ext_polygon = Polygon(exterior, facecolor=color, alpha=0.3, edgecolor=color, linewidth=2)
        ax.add_patch(ext_polygon)
        
        # Draw holes (as white cutouts)
        for j, hole in enumerate(holes):
            hole_polygon = Polygon(hole, facecolor='white', alpha=1.0, edgecolor='black', linewidth=1)
            ax.add_patch(hole_polygon)
            
            # Add hole label
            hole_center = np.mean(hole, axis=0)
            ax.text(hole_center[0], hole_center[1], f'HOLE\n{j+1}', 
                   ha='center', va='center', fontsize=8, 
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        # Add shape label
        ext_center = np.mean(exterior, axis=0)
        ax.text(ext_center[0], ext_center[1], f'Shape {shape_data["index"]+1}\nID: {identifier}', 
               ha='center', va='center', fontsize=10, weight='bold',
               bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.7))
    
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_title('CLF Shapes: Exterior Boundaries vs Holes\n(Holes shown as white cutouts)', 
                fontsize=14, weight='bold')
    
    # Auto-scale to fit all shapes
    ax.autoscale()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Visualization saved: {output_path}")
    
    return output_path

def demonstrate_hole_detection_algorithm(shape_points):
    """Demonstrate different algorithms for detecting if a path is a hole vs exterior"""
    
    print("\n🧮 HOLE DETECTION ALGORITHMS:")
    print("=" * 50)
    
    exterior = shape_points[0]
    holes = shape_points[1:] if len(shape_points) > 1 else []
    
    def calculate_signed_area(points):
        """Calculate signed area of a polygon (positive = counterclockwise, negative = clockwise)"""
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return area / 2.0
    
    def get_winding_direction(points):
        """Get winding direction: CCW (counterclockwise) or CW (clockwise)"""
        signed_area = calculate_signed_area(points)
        return "CCW" if signed_area > 0 else "CW"
    
    def is_point_inside_polygon(point, polygon):
        """Check if a point is inside a polygon using ray casting"""
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
    
    # Algorithm 1: Winding Direction
    print("🔍 Algorithm 1: Winding Direction Analysis")
    ext_direction = get_winding_direction(exterior)
    print(f"   Exterior boundary: {ext_direction}")
    
    for i, hole in enumerate(holes):
        hole_direction = get_winding_direction(hole)
        print(f"   Path {i+2}: {hole_direction}")
        if hole_direction != ext_direction:
            print(f"      ✅ Different winding → HOLE detected!")
        else:
            print(f"      ⚠️  Same winding → May not be a hole")
    
    # Algorithm 2: Containment Test
    print("\n🔍 Algorithm 2: Containment Analysis")
    for i, hole in enumerate(holes):
        hole_center = np.mean(hole, axis=0)
        is_inside = is_point_inside_polygon(hole_center, exterior)
        print(f"   Path {i+2} center: {hole_center}")
        print(f"   Inside exterior? {is_inside}")
        if is_inside:
            print(f"      ✅ Center inside exterior → HOLE detected!")
        else:
            print(f"      ⚠️  Center outside → Separate shape")
    
    # Algorithm 3: Area Comparison
    print("\n🔍 Algorithm 3: Area Analysis")
    ext_area = abs(calculate_signed_area(exterior))
    print(f"   Exterior area: {ext_area:.2f}")
    
    for i, hole in enumerate(holes):
        hole_area = abs(calculate_signed_area(hole))
        print(f"   Path {i+2} area: {hole_area:.2f}")
        if hole_area < ext_area:
            print(f"      ✅ Smaller area → Likely a HOLE")
        else:
            print(f"      ⚠️  Larger/equal area → May be separate shape")

def scan_build_for_holes(build_path, max_files=10):
    """Scan a build directory for shapes with holes"""
    print(f"\n🔍 Scanning build for shapes with holes: {os.path.basename(build_path)}")
    print("=" * 60)
    
    clf_files = find_clf_files(build_path)
    print(f"📁 Found {len(clf_files)} CLF files")
    
    total_holes_found = 0
    files_with_holes = 0
    
    for i, clf_info in enumerate(clf_files[:max_files]):
        print(f"\n📄 File {i+1}/{min(max_files, len(clf_files))}: {clf_info['name']}")
        
        shapes_with_holes = analyze_shape_structure(clf_info['path'], height=1.0)
        
        if shapes_with_holes:
            files_with_holes += 1
            total_holes_found += sum(len(s['holes']) for s in shapes_with_holes)
            
            # Demonstrate detection algorithms on first shape with holes
            if len(shapes_with_holes) > 0:
                first_shape = shapes_with_holes[0]
                all_paths = [first_shape['exterior']] + first_shape['holes']
                demonstrate_hole_detection_algorithm(all_paths)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Files scanned: {min(max_files, len(clf_files))}")
    print(f"   Files with holes: {files_with_holes}")
    print(f"   Total holes found: {total_holes_found}")

if __name__ == "__main__":
    # Test with a known build
    build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/build-431627"
    
    if os.path.exists(build_path):
        scan_build_for_holes(build_path, max_files=5)
    else:
        print(f"❌ Build path not found: {build_path}")
