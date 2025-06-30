#!/usr/bin/env python3
"""
Visualize the banana shape with ellipse to understand its structure
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json

# Add paths
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import setup_paths
from utils.pyarcam.clfutil import CLFFile

def visualize_banana_ellipse_shape():
    """Create detailed visualization of the banana + ellipse shape"""
    
    # Load the JSON data
    json_file = "shape_analysis_data_134.0mm.json"
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        print("Run detailed_shape_analysis.py first!")
        return
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    if not data:
        print("❌ No shape data found in JSON file")
        return
    
    shape_data = data[0]  # Get the first (and likely only) shape
    paths = shape_data['paths']
    
    print(f"🎨 Creating visualization for Shape ID: {shape_data['identifier']}")
    print(f"📊 Number of paths: {len(paths)}")
    
    # Create figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'Banana + Ellipse Shape Analysis (ID: {shape_data["identifier"]})\nHeight: 134.0mm', 
                 fontsize=16, fontweight='bold')
    
    # Plot 1: Combined view
    ax1 = axes[0, 0]
    ax1.set_title('Combined View: Exterior + Interior', fontweight='bold')
    
    for i, path_data in enumerate(paths):
        points = np.array(path_data['points'])
        label = f"Path {i+1} ({'Exterior' if i == 0 else 'Interior'})"
        color = 'blue' if i == 0 else 'red'
        
        # Plot the path
        ax1.plot(points[:, 0], points[:, 1], color=color, linewidth=2, label=label)
        
        # Mark start/end points
        ax1.plot(points[0, 0], points[0, 1], 'o', color=color, markersize=8, label=f'{label} Start')
        ax1.plot(points[-1, 0], points[-1, 1], 's', color=color, markersize=8, label=f'{label} End')
        
        # Mark center
        center = path_data['center']
        ax1.plot(center[0], center[1], 'x', color=color, markersize=10, markeredgewidth=3)
    
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Plot 2: Path directions with arrows
    ax2 = axes[0, 1]
    ax2.set_title('Path Directions (with arrows)', fontweight='bold')
    
    for i, path_data in enumerate(paths):
        points = np.array(path_data['points'])
        color = 'blue' if i == 0 else 'red'
        
        # Plot the path
        ax2.plot(points[:, 0], points[:, 1], color=color, linewidth=2, alpha=0.7)
        
        # Add direction arrows
        for j in range(0, len(points) - 1, 5):  # Every 5th point
            start = points[j]
            end = points[j + 1]
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            ax2.arrow(start[0], start[1], dx, dy, head_width=0.3, head_length=0.2, 
                     fc=color, ec=color, alpha=0.7)
    
    ax2.set_aspect('equal')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Filled shapes
    ax3 = axes[1, 0]
    ax3.set_title('Filled Shapes (Solid Fill)', fontweight='bold')
    
    # Plot exterior as filled polygon
    exterior_points = np.array(paths[0]['points'])
    exterior_poly = patches.Polygon(exterior_points, facecolor='lightblue', 
                                   edgecolor='blue', alpha=0.7, label='Exterior')
    ax3.add_patch(exterior_poly)
    
    # Plot interior as filled polygon
    interior_points = np.array(paths[1]['points'])
    interior_poly = patches.Polygon(interior_points, facecolor='lightcoral', 
                                   edgecolor='red', alpha=0.7, label='Interior')
    ax3.add_patch(interior_poly)
    
    ax3.set_aspect('equal')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Plot 4: Proper hole visualization (exterior with interior cutout)
    ax4 = axes[1, 1]
    ax4.set_title('Proper Hole Visualization\n(Interior subtracted from exterior)', fontweight='bold')
    
    # Create a path that represents exterior with hole
    exterior_points = np.array(paths[0]['points'])
    interior_points = np.array(paths[1]['points'])
    
    # Plot exterior filled
    exterior_poly = patches.Polygon(exterior_points, facecolor='lightgreen', 
                                   edgecolor='darkgreen', alpha=0.8, label='Final Shape')
    ax4.add_patch(exterior_poly)
    
    # Plot interior as white cutout
    interior_poly = patches.Polygon(interior_points, facecolor='white', 
                                   edgecolor='black', alpha=1.0, label='Hole')
    ax4.add_patch(interior_poly)
    
    ax4.set_aspect('equal')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    # Adjust layout to prevent overlap
    plt.tight_layout()
    
    # Save the plot
    output_file = "banana_ellipse_visualization.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Visualization saved: {output_file}")
    
    plt.show()
    
    # Print detailed analysis
    print(f"\n📊 DETAILED PATH ANALYSIS:")
    print(f"{'='*60}")
    
    for i, path_data in enumerate(paths):
        path_type = "EXTERIOR" if i == 0 else "INTERIOR/HOLE"
        print(f"\n🛤️  PATH {i+1} ({path_type}):")
        print(f"   📏 Points: {path_data['num_points']}")
        print(f"   📐 Area: {path_data['area']:.6f}")
        print(f"   🌀 Winding: {path_data['winding']}")
        print(f"   🎯 Center: ({path_data['center'][0]:.3f}, {path_data['center'][1]:.3f})")
        print(f"   📦 Bounds: X[{path_data['bounds']['min_x']:.3f}, {path_data['bounds']['max_x']:.3f}], Y[{path_data['bounds']['min_y']:.3f}, {path_data['bounds']['max_y']:.3f}]")
        print(f"   🔄 Closed: {path_data['is_closed']}")
        
        # Check if paths should be closed
        points = np.array(path_data['points'])
        first_point = points[0]
        last_point = points[-1]
        distance = np.sqrt((last_point[0] - first_point[0])**2 + (last_point[1] - first_point[1])**2)
        print(f"   📏 Start-End Distance: {distance:.6f}")
        
        if distance < 1.0:  # Close enough to be considered closed
            print(f"   ✅ Paths are effectively closed (distance < 1.0)")
        else:
            print(f"   ⚠️  Paths may be open (distance > 1.0)")

def analyze_winding_order():
    """Analyze the winding order in detail"""
    
    print(f"\n🌀 WINDING ORDER ANALYSIS:")
    print(f"{'='*50}")
    
    json_file = "shape_analysis_data_134.0mm.json"
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    shape_data = data[0]
    paths = shape_data['paths']
    
    def calculate_signed_area(points):
        """Calculate signed area to determine winding direction"""
        points = np.array(points)
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return area / 2.0
    
    for i, path_data in enumerate(paths):
        points = path_data['points']
        signed_area = calculate_signed_area(points)
        
        print(f"\n🛤️  PATH {i+1}:")
        print(f"   📐 Signed Area: {signed_area:.6f}")
        print(f"   🌀 Winding: {'CCW' if signed_area > 0 else 'CW'} ({'Positive' if signed_area > 0 else 'Negative'})")
        
        if i == 0:
            print(f"   🔷 This is the EXTERIOR boundary")
        else:
            if signed_area * calculate_signed_area(paths[0]['points']) < 0:
                print(f"   ✅ Opposite winding to exterior → CONFIRMED HOLE")
            else:
                print(f"   ⚠️  Same winding as exterior → NOT a proper hole")

def check_point_in_polygon():
    """Check point-in-polygon relationships"""
    
    print(f"\n📍 POINT-IN-POLYGON ANALYSIS:")
    print(f"{'='*50}")
    
    json_file = "shape_analysis_data_134.0mm.json"
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    shape_data = data[0]
    paths = shape_data['paths']
    
    def point_in_polygon(point, polygon):
        """Ray casting algorithm for point in polygon test"""
        x, y = point
        polygon = np.array(polygon)
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
    
    exterior_points = paths[0]['points']
    interior_points = paths[1]['points']
    
    # Test interior center in exterior
    interior_center = paths[1]['center']
    is_interior_in_exterior = point_in_polygon(interior_center, exterior_points)
    
    print(f"🎯 Interior center: ({interior_center[0]:.3f}, {interior_center[1]:.3f})")
    print(f"📍 Interior center in exterior polygon: {is_interior_in_exterior}")
    
    # Test exterior center in interior
    exterior_center = paths[0]['center']
    is_exterior_in_interior = point_in_polygon(exterior_center, interior_points)
    
    print(f"🎯 Exterior center: ({exterior_center[0]:.3f}, {exterior_center[1]:.3f})")
    print(f"📍 Exterior center in interior polygon: {is_exterior_in_interior}")
    
    # Test a few sample points from interior boundary in exterior
    print(f"\n🔍 Testing interior boundary points in exterior:")
    sample_indices = [0, len(interior_points)//4, len(interior_points)//2, 3*len(interior_points)//4]
    
    for idx in sample_indices:
        point = interior_points[idx]
        is_inside = point_in_polygon(point, exterior_points)
        print(f"   Point {idx}: ({point[0]:.3f}, {point[1]:.3f}) → Inside exterior: {is_inside}")

if __name__ == "__main__":
    visualize_banana_ellipse_shape()
    analyze_winding_order()
    check_point_in_polygon()
