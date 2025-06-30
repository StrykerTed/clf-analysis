#!/usr/bin/env python3
"""
E-beam Path Analysis Script
Investigates what the different path types (solid vs dotted) could represent
in electron beam additive manufacturing context.
"""

import os
import sys
import json
import numpy as np

# Add paths
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

def analyze_ebeam_patterns():
    """Analyze the path patterns in context of e-beam manufacturing"""
    
    print("🔬 E-BEAM PATH PATTERN ANALYSIS")
    print("=" * 60)
    
    # Load the shape data
    json_file = "shape_analysis_data_134.0mm.json"
    if not os.path.exists(json_file):
        print("❌ Analysis data not found!")
        return
    
    with open(json_file, 'r') as f:
        shapes_data = json.load(f)
    
    print("🎯 POSSIBLE E-BEAM INTERPRETATIONS:")
    print("-" * 40)
    
    for shape_idx, shape in enumerate(shapes_data):
        shape_name = "Banana" if shape_idx == 0 else "Ellipse"
        print(f"\n🔸 {shape_name} Shape (ID: {shape['identifier']}):")
        
        for path_idx, path in enumerate(shape['paths']):
            winding = path['winding']
            area = path['area']
            
            # Determine likely e-beam function based on winding
            if 'CCW' in winding:
                beam_function = "🔥 MELTING/FUSION PATH"
                description = "Primary e-beam path for material fusion"
                line_style = "Solid line"
            else:  # CW
                beam_function = "❄️  SUPPORT/AUXILIARY PATH"
                description = "Secondary operation (cooling, supports, or hatching)"
                line_style = "Dotted line"
            
            print(f"   Path {path_idx + 1}: {beam_function}")
            print(f"      📊 Winding: {winding}")
            print(f"      📐 Area: {area:.1f} mm²")
            print(f"      🎨 Visual: {line_style}")
            print(f"      💡 Likely function: {description}")
            
            # Additional analysis based on area relationships
            if len(shape['paths']) == 2:
                other_path = shape['paths'][1 - path_idx]
                area_ratio = area / other_path['area']
                
                if area_ratio > 1.1:  # Significantly larger
                    print(f"      🔍 Analysis: DOMINANT path (area ratio: {area_ratio:.2f})")
                elif area_ratio < 0.9:  # Significantly smaller
                    print(f"      🔍 Analysis: SECONDARY path (area ratio: {area_ratio:.2f})")
                else:
                    print(f"      🔍 Analysis: SIMILAR SIZE path (area ratio: {area_ratio:.2f})")
    
    print("\n🏭 E-BEAM MANUFACTURING CONTEXT:")
    print("-" * 40)
    
    interpretations = [
        "🔥 CCW (Solid) Paths - MELTING OPERATION:",
        "   • Primary e-beam path for material fusion",
        "   • Counter-clockwise movement for consistent heat distribution",
        "   • Main structural geometry creation",
        "",
        "❄️ CW (Dotted) Paths - SECONDARY OPERATION:",
        "   • Could be support structure paths",
        "   • Possible cooling or consolidation passes",
        "   • Hatching patterns for internal structure",
        "   • Tool path for surface finishing",
        "   • Powder bed preparation routes",
        "",
        "🤔 ALTERNATIVE INTERPRETATIONS:",
        "   • Different power levels (high vs low beam intensity)",
        "   • Multiple scan strategies (outline vs infill)",
        "   • Process sequence (first pass vs second pass)",
        "   • Material deposition vs machining operations"
    ]
    
    for line in interpretations:
        print(line)
    
    print("\n🔬 TECHNICAL ANALYSIS:")
    print("-" * 40)
    
    # Analyze the specific patterns we found
    if len(shapes_data) >= 2:
        banana = shapes_data[0]
        ellipse = shapes_data[1]
        
        print("🍌 Banana Shape Pattern:")
        if len(banana['paths']) == 2:
            ccw_area = next(p['area'] for p in banana['paths'] if 'CCW' in p['winding'])
            cw_area = next(p['area'] for p in banana['paths'] if 'CW' in p['winding'])
            
            print(f"   • CCW (fusion): {ccw_area:.1f} mm² - Primary structure")
            print(f"   • CW (support): {cw_area:.1f} mm² - Secondary operation")
            print(f"   • Both paths are large → Likely different scan strategies")
            print(f"   • Similar sizes → Could be outline + infill pattern")
        
        print("\n⭕ Ellipse Shape Pattern:")
        if len(ellipse['paths']) == 2:
            ccw_area = next(p['area'] for p in ellipse['paths'] if 'CCW' in p['winding'])
            cw_area = next(p['area'] for p in ellipse['paths'] if 'CW' in p['winding'])
            
            print(f"   • CCW (fusion): {ccw_area:.1f} mm² - Ring structure")
            print(f"   • CW (support): {cw_area:.1f} mm² - Internal processing")
            print(f"   • Classic hole-in-ring → Likely outline + internal hatching")
    
    print("\n💡 MOST LIKELY EXPLANATION:")
    print("-" * 40)
    print("Based on the patterns observed:")
    print("🎯 CCW (Solid) = OUTLINE/PERIMETER scanning")
    print("🎯 CW (Dotted) = INFILL/HATCHING scanning")
    print("")
    print("This is a common dual-strategy approach in e-beam melting:")
    print("• Outline paths create precise boundaries")
    print("• Infill paths provide internal structure and density")
    print("• Different windings help optimize scan efficiency")
    print("• Reduces thermal stress and improves part quality")

def analyze_manufacturing_sequence():
    """Analyze the likely manufacturing sequence"""
    
    print("\n⏱️  MANUFACTURING SEQUENCE ANALYSIS:")
    print("-" * 40)
    
    sequence_steps = [
        "1️⃣ POWDER LAYER DEPOSITION",
        "   • Fresh powder spread across build platform",
        "   • Layer thickness: ~50μm (based on model.thickness)",
        "",
        "2️⃣ OUTLINE SCANNING (CCW - Solid paths)",
        "   • E-beam traces perimeter boundaries",
        "   • Higher power for complete fusion",
        "   • Creates strong outer shell",
        "",
        "3️⃣ INFILL SCANNING (CW - Dotted paths)", 
        "   • E-beam fills interior regions",
        "   • May use lower power or different speed",
        "   • Provides internal structure and density",
        "",
        "4️⃣ LAYER COMPLETION",
        "   • Both scan strategies complete the layer",
        "   • Move to next Z-height (+0.05mm)",
        "   • Repeat for next layer"
    ]
    
    for step in sequence_steps:
        print(step)

if __name__ == "__main__":
    analyze_ebeam_patterns()
    analyze_manufacturing_sequence()
