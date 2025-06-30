#!/usr/bin/env python3
"""
CLF Shape Analysis Summary
Provides a text summary of the analysis findings
"""

import json
import os

def print_summary():
    """Print a comprehensive summary of the analysis"""
    
    # Load the data
    json_file = "shape_analysis_data_134.0mm.json"
    if not os.path.exists(json_file):
        print("❌ Analysis data not found. Run detailed_shape_analysis.py first!")
        return
    
    with open(json_file, 'r') as f:
        shapes_data = json.load(f)
    
    print("🎯 CLF SHAPE ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"📁 File: 5518-F-101_10_AN5518-F-101_Skin")
    print(f"📏 Height: 134.0mm")
    print(f"🔢 Total Shapes: {len(shapes_data)}")
    print()
    
    for i, shape in enumerate(shapes_data):
        shape_name = "🍌 Banana Shape" if i == 0 else "⭕ Ellipse Shape"
        print(f"{shape_name} (Shape {i+1})")
        print("-" * 40)
        print(f"   📊 Shape ID: {shape['identifier']}")
        print(f"   🛤️  Number of Paths: {shape['num_paths']}")
        
        total_area = sum(path['area'] for path in shape['paths'])
        print(f"   📐 Total Area: {total_area:.2f} mm²")
        
        for j, path in enumerate(shape['paths']):
            path_type = "Exterior" if "CCW" in path['winding'] else "Interior/Hole"
            print(f"   Path {j+1}: {path_type}")
            print(f"      🔢 Points: {path['num_points']}")
            print(f"      📐 Area: {path['area']:.2f} mm²")
            print(f"      🌀 Winding: {path['winding']}")
            print(f"      🎯 Center: ({path['center'][0]:.1f}, {path['center'][1]:.1f})")
            print(f"      📦 Bounds: X[{path['bounds']['min_x']:.1f}, {path['bounds']['max_x']:.1f}] Y[{path['bounds']['min_y']:.1f}, {path['bounds']['max_y']:.1f}]")
            print(f"      🔄 Closed: {path['is_closed']}")
        print()
    
    print("🔍 KEY FINDINGS:")
    print("-" * 20)
    
    # Analyze the banana shape
    if len(shapes_data) > 0:
        banana = shapes_data[0]
        print(f"🍌 Banana Shape Analysis:")
        if len(banana['paths']) == 2:
            path1_area = banana['paths'][0]['area']
            path2_area = banana['paths'][1]['area']
            path1_wind = banana['paths'][0]['winding']
            path2_wind = banana['paths'][1]['winding']
            
            print(f"   • Two separate paths with different windings ({path1_wind[:3]} vs {path2_wind[:3]})")
            print(f"   • Path areas: {path1_area:.1f} vs {path2_area:.1f} mm²")
            print(f"   • Likely represents a complex shape with internal features")
    
    # Analyze the ellipse shape
    if len(shapes_data) > 1:
        ellipse = shapes_data[1]
        print(f"⭕ Ellipse Shape Analysis:")
        if len(ellipse['paths']) == 2:
            path1_area = ellipse['paths'][0]['area']
            path2_area = ellipse['paths'][1]['area']
            path1_wind = ellipse['paths'][0]['winding']
            path2_wind = ellipse['paths'][1]['winding']
            
            print(f"   • Classic hole-in-shape pattern ({path1_wind[:3]} exterior, {path2_wind[:3]} hole)")
            print(f"   • Hole area: {path2_area:.1f} mm² inside {path1_area:.1f} mm² exterior")
            print(f"   • True ellipse with internal void")
    
    print()
    print("📊 GENERATED FILES:")
    print("-" * 20)
    
    # List generated files
    files = [
        ("clf_shapes_overview_134.0mm.png", "Comprehensive 6-panel analysis view"),
        ("clf_shape_1_banana_134.0mm.png", "Detailed banana shape visualization"),
        ("clf_shape_2_ellipse_134.0mm.png", "Detailed ellipse shape visualization"),
        ("shape_analysis_data_134.0mm.json", "Raw path data for further analysis")
    ]
    
    for filename, description in files:
        if os.path.exists(filename):
            print(f"   ✅ {filename} - {description}")
        else:
            print(f"   ❌ {filename} - {description} (missing)")
    
    print()
    print("🎉 Analysis Complete! Check the PNG files for visual representations.")

if __name__ == "__main__":
    print_summary()
