#!/usr/bin/env python3
"""
Comprehensive Shapes with Holes Visualization
Creates a single combined view of all shapes with holes found at 8.2mm height.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import to_rgba
import math

def load_comprehensive_data(json_file):
    """Load the comprehensive analysis data"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ JSON file not found: {json_file}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error reading JSON file: {e}")
        return None

def extract_shapes_with_holes(data):
    """Extract only shapes that have holes"""
    shapes_with_holes = []
    
    for file_data in data['files']:
        for shape in file_data['shapes']:
            if shape['has_holes']:
                # Add file context to shape data
                shape_with_context = shape.copy()
                shape_with_context['source_file'] = file_data['file_name']
                shapes_with_holes.append(shape_with_context)
    
    return shapes_with_holes

def create_comprehensive_holes_visualization(shapes_with_holes, height=8.2):
    """Create a comprehensive visualization showing all shapes with holes"""
    
    # Calculate grid dimensions for subplots
    total_shapes = len(shapes_with_holes)
    if total_shapes == 0:
        print("❌ No shapes with holes found!")
        return None
    
    # Create a reasonable grid layout
    if total_shapes <= 6:
        cols = min(3, total_shapes)
        rows = math.ceil(total_shapes / cols)
    elif total_shapes <= 20:
        cols = 4
        rows = math.ceil(total_shapes / cols)
    else:
        # For many shapes, create a larger grid
        cols = 6
        rows = math.ceil(total_shapes / cols)
    
    # Create figure with calculated dimensions
    fig_width = min(20, cols * 3.5)
    fig_height = min(24, rows * 3)
    fig, axes = plt.subplots(rows, cols, figsize=(fig_width, fig_height))
    
    # Ensure axes is always a 2D array
    if rows == 1 and cols == 1:
        axes = np.array([[axes]])
    elif rows == 1:
        axes = axes.reshape(1, -1)
    elif cols == 1:
        axes = axes.reshape(-1, 1)
    
    # Color schemes for different types of shapes
    exterior_color = '#2E86AB'
    hole_color = '#A23B72'
    
    for idx, shape in enumerate(shapes_with_holes):
        row = idx // cols
        col = idx % cols
        
        if row >= rows:
            break
            
        ax = axes[row, col]
        
        # Plot exterior paths and holes
        exterior_paths = []
        hole_paths = []
        
        for path in shape['paths']:
            if path.get('is_likely_hole', False):
                hole_paths.append(path)
            else:
                exterior_paths.append(path)
        
        # Plot exterior boundaries
        for i, path in enumerate(exterior_paths):
            points = np.array(path['points'])
            ax.plot(points[:, 0], points[:, 1], 
                   color=exterior_color, linewidth=2, 
                   label=f'Exterior {i+1}' if i == 0 else "")
            
            # Fill exterior area lightly
            ax.fill(points[:, 0], points[:, 1], 
                   color=exterior_color, alpha=0.2)
        
        # Plot holes
        for i, path in enumerate(hole_paths):
            points = np.array(path['points'])
            ax.plot(points[:, 0], points[:, 1], 
                   color=hole_color, linewidth=2, linestyle='--',
                   label=f'Hole {i+1}' if i == 0 else "")
            
            # Fill hole area
            ax.fill(points[:, 0], points[:, 1], 
                   color=hole_color, alpha=0.4)
            
            # Mark hole center
            center = path['center']
            ax.plot(center[0], center[1], 'o', 
                   color=hole_color, markersize=6)
            
            # Add hole area annotation
            ax.annotate(f'H: {path["area"]:.1f}mm²', 
                       xy=center, xytext=(5, 5), 
                       textcoords='offset points',
                       fontsize=8, color=hole_color,
                       bbox=dict(boxstyle='round,pad=0.2', 
                               facecolor='white', alpha=0.8))
        
        # Customize subplot
        ax.set_title(f'ID: {shape["identifier"]} ({shape["source_file"]})\n'
                    f'Paths: {shape["num_paths"]}, Area: {shape["total_area"]:.1f}mm²', 
                    fontsize=10, fontweight='bold')
        ax.set_xlabel('X (mm)', fontsize=8)
        ax.set_ylabel('Y (mm)', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal', adjustable='box')
        
        # Add legend only to first subplot
        if idx == 0:
            ax.legend(fontsize=8)
    
    # Hide empty subplots
    total_subplots = rows * cols
    for idx in range(total_shapes, total_subplots):
        row = idx // cols
        col = idx % cols
        if row < rows and col < cols:
            axes[row, col].set_visible(False)
    
    plt.tight_layout()
    plt.suptitle(f'🕳️  All Shapes with Holes at {height}mm\n'
                f'Found {len(shapes_with_holes)} shapes with holes across {height}mm layer', 
                fontsize=16, fontweight='bold', y=0.98)
    
    return fig

def create_holes_summary_plot(shapes_with_holes, height=8.2):
    """Create summary statistics plots for holes"""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. Hole areas distribution
    hole_areas = []
    exterior_areas = []
    
    for shape in shapes_with_holes:
        for path in shape['paths']:
            if path.get('is_likely_hole', False):
                hole_areas.append(path['area'])
            else:
                exterior_areas.append(path['area'])
    
    ax1.hist(hole_areas, bins=20, alpha=0.7, color='#A23B72', label=f'Holes ({len(hole_areas)})')
    ax1.set_xlabel('Area (mm²)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Distribution of Hole Areas')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Number of holes per shape
    holes_per_shape = []
    for shape in shapes_with_holes:
        hole_count = len([p for p in shape['paths'] if p.get('is_likely_hole', False)])
        holes_per_shape.append(hole_count)
    
    ax2.hist(holes_per_shape, bins=range(1, max(holes_per_shape)+2), 
             alpha=0.7, color='#2E86AB', align='left')
    ax2.set_xlabel('Number of Holes per Shape')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Distribution of Holes per Shape')
    ax2.grid(True, alpha=0.3)
    
    # 3. Total area vs hole area
    total_areas = []
    total_hole_areas = []
    
    for shape in shapes_with_holes:
        total_area = shape['total_area']
        hole_area = sum(p['area'] for p in shape['paths'] if p.get('is_likely_hole', False))
        total_areas.append(total_area)
        total_hole_areas.append(hole_area)
    
    ax3.scatter(total_areas, total_hole_areas, alpha=0.6, color='#F18F01')
    ax3.set_xlabel('Total Shape Area (mm²)')
    ax3.set_ylabel('Total Hole Area (mm²)')
    ax3.set_title('Total Area vs Hole Area')
    ax3.grid(True, alpha=0.3)
    
    # Add diagonal reference line
    max_area = max(max(total_areas), max(total_hole_areas))
    ax3.plot([0, max_area], [0, max_area], 'k--', alpha=0.3, label='Equal areas')
    ax3.legend()
    
    # 4. Hole area percentage
    hole_percentages = []
    for total_area, hole_area in zip(total_areas, total_hole_areas):
        if total_area > 0:
            percentage = (hole_area / total_area) * 100
            hole_percentages.append(percentage)
    
    ax4.hist(hole_percentages, bins=20, alpha=0.7, color='#C73E1D')
    ax4.set_xlabel('Hole Area Percentage (%)')
    ax4.set_ylabel('Frequency')
    ax4.set_title('Distribution of Hole Area as % of Total')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.suptitle(f'📊 Hole Analysis Statistics at {height}mm', 
                fontsize=16, fontweight='bold', y=0.98)
    
    return fig

def main():
    """Main function to create comprehensive holes visualization"""
    
    # Load comprehensive analysis data
    json_file = "all_shapes_analysis_136.55mm.json"
    data = load_comprehensive_data(json_file)
    
    if data is None:
        print("❌ Could not load comprehensive analysis data!")
        print("   Make sure to run analyze_all_shapes_at_height.py first!")
        return
    
    print(f"✅ Loaded comprehensive analysis for {data['total_shapes']} shapes")
    
    # Extract shapes with holes
    shapes_with_holes = extract_shapes_with_holes(data)
    print(f"🕳️  Found {len(shapes_with_holes)} shapes with holes")
    
    if not shapes_with_holes:
        print("❌ No shapes with holes found!")
        return
    
    # Create comprehensive visualization
    print("🎨 Creating comprehensive holes visualization...")
    fig1 = create_comprehensive_holes_visualization(shapes_with_holes, height=data['analysis_height'])
    
    if fig1:
        # Save comprehensive visualization
        filename1 = f"all_shapes_with_holes_{data['analysis_height']}mm.png"
        fig1.savefig(filename1, dpi=300, bbox_inches='tight')
        print(f"💾 Saved: {filename1}")
    
    # Create summary statistics
    print("📊 Creating holes summary statistics...")
    fig2 = create_holes_summary_plot(shapes_with_holes, height=data['analysis_height'])
    
    # Save summary statistics
    filename2 = f"holes_statistics_{data['analysis_height']}mm.png"
    fig2.savefig(filename2, dpi=300, bbox_inches='tight')
    print(f"💾 Saved: {filename2}")
    
    # Show plots
    print("🖼️  Displaying visualizations...")
    plt.show()
    
    # Print summary
    print(f"\n✅ Visualization complete!")
    print(f"📊 Summary:")
    print(f"   - Analysis height: {data['analysis_height']}mm")
    print(f"   - Total files analyzed: {data['total_files_analyzed']}")
    print(f"   - Total shapes: {data['total_shapes']}")
    print(f"   - Shapes with holes: {len(shapes_with_holes)}")
    
    # Calculate hole statistics
    total_holes = sum(len([p for p in shape['paths'] if p.get('is_likely_hole', False)]) 
                     for shape in shapes_with_holes)
    total_hole_area = sum(sum(p['area'] for p in shape['paths'] if p.get('is_likely_hole', False)) 
                         for shape in shapes_with_holes)
    
    print(f"   - Total holes: {total_holes}")
    print(f"   - Total hole area: {total_hole_area:.2f} mm²")
    
    if total_holes > 0:
        avg_hole_area = total_hole_area / total_holes
        print(f"   - Average hole area: {avg_hole_area:.2f} mm²")

if __name__ == "__main__":
    main()
