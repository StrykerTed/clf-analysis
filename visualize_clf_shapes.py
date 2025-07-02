#!/usr/bin/env python3
"""
Visualize CLF Shapes Script
Creates visualizations of the shapes extracted from the CLF analysis,
showing the banana shape and ellipse with their paths and relationships.
"""

import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import to_rgba

# Add paths
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

def load_shape_data(json_file):
    """Load shape data from JSON file"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ JSON file not found: {json_file}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error reading JSON file: {e}")
        return None

def create_comprehensive_visualization(shapes_data, height=134.0):
    """Create a comprehensive visualization of all shapes and paths"""
    
    # Set up the figure with multiple subplots
    fig = plt.figure(figsize=(20, 12))
    
    # Define colors for different paths
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#592E83', '#1B8A5A']
    
    # 1. Overview plot - all shapes together
    ax1 = plt.subplot(2, 3, 1)
    plot_all_shapes_overview(ax1, shapes_data, colors)
    ax1.set_title(f'📊 Overview: All Shapes at {height}mm', fontsize=14, fontweight='bold')
    
    # 2. Shape 1 detailed (Banana shape)
    ax2 = plt.subplot(2, 3, 2)
    if len(shapes_data) > 0:
        plot_shape_detailed(ax2, shapes_data[0], colors, "🍌 Shape 1: Banana")
    
    # 3. Shape 2 detailed (Ellipse shape)
    ax3 = plt.subplot(2, 3, 3)
    if len(shapes_data) > 1:
        plot_shape_detailed(ax3, shapes_data[1], colors, "⭕ Shape 2: Ellipse")
    
    # 4. Path comparison by area
    ax4 = plt.subplot(2, 3, 4)
    plot_path_areas(ax4, shapes_data)
    
    # 5. Winding direction analysis
    ax5 = plt.subplot(2, 3, 5)
    plot_winding_analysis(ax5, shapes_data)
    
    # 6. Shape centers and bounds
    ax6 = plt.subplot(2, 3, 6)
    plot_centers_and_bounds(ax6, shapes_data, colors)
    
    plt.tight_layout()
    plt.suptitle(f'🔍 CLF Shape Analysis: 5518-F-101_Skin at {height}mm', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    return fig

def plot_all_shapes_overview(ax, shapes_data, colors):
    """Plot all shapes in one overview"""
    
    all_x_coords = []
    all_y_coords = []
    
    for shape_idx, shape in enumerate(shapes_data):
        shape_color_base = colors[shape_idx % len(colors)]
        
        for path_idx, path_data in enumerate(shape['paths']):
            points = np.array(path_data['points'])
            
            # Determine line style based on winding
            linestyle = '-' if 'CCW' in path_data['winding'] else '--'
            linewidth = 2 if path_idx == 0 else 1.5  # Thicker for exterior paths
            
            # Add transparency for interior paths
            alpha = 0.8 if path_idx == 0 else 0.6
            
            ax.plot(points[:, 0], points[:, 1], 
                   color=shape_color_base, 
                   linestyle=linestyle,
                   linewidth=linewidth,
                   alpha=alpha,
                   label=f'Shape {shape_idx+1} Path {path_idx+1}')
            
            # Mark start point
            ax.plot(points[0, 0], points[0, 1], 'o', 
                   color=shape_color_base, markersize=6)
            
            # Add path center
            center = path_data['center']
            ax.plot(center[0], center[1], 's', 
                   color=shape_color_base, markersize=4, alpha=0.7)
            
            all_x_coords.extend(points[:, 0])
            all_y_coords.extend(points[:, 1])
    
    ax.set_xlabel('X Coordinate (mm)')
    ax.set_ylabel('Y Coordinate (mm)')
    ax.grid(True, alpha=0.3)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_aspect('equal', adjustable='box')

def plot_shape_detailed(ax, shape_data, colors, title):
    """Plot a single shape with detailed path information"""
    
    shape_color = colors[shape_data['shape_index'] % len(colors)]
    
    for path_idx, path_data in enumerate(shape_data['paths']):
        points = np.array(path_data['points'])
        
        # Color variation for different paths
        path_color = plt.cm.Set1(path_idx / max(1, len(shape_data['paths']) - 1))
        
        # Line style based on winding
        linestyle = '-' if 'CCW' in path_data['winding'] else '--'
        linewidth = 3 if path_idx == 0 else 2
        
        ax.plot(points[:, 0], points[:, 1], 
               color=path_color, 
               linestyle=linestyle,
               linewidth=linewidth,
               label=f'Path {path_idx+1} ({path_data["winding"][:3]})')
        
        # Mark start and end points
        ax.plot(points[0, 0], points[0, 1], 'o', 
               color=path_color, markersize=8, label=f'Start P{path_idx+1}')
        ax.plot(points[-1, 0], points[-1, 1], 's', 
               color=path_color, markersize=8, label=f'End P{path_idx+1}')
        
        # Add center point
        center = path_data['center']
        ax.plot(center[0], center[1], '^', 
               color=path_color, markersize=8, label=f'Center P{path_idx+1}')
        
        # Add area annotation
        area = path_data['area']
        ax.annotate(f'Area: {area:.1f}', 
                   xy=center, xytext=(10, 10), 
                   textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor=path_color, alpha=0.3),
                   fontsize=9)
    
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('X Coordinate (mm)')
    ax.set_ylabel('Y Coordinate (mm)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_aspect('equal', adjustable='box')

def plot_path_areas(ax, shapes_data):
    """Create a bar chart comparing path areas"""
    
    path_labels = []
    areas = []
    colors_list = []
    
    for shape_idx, shape in enumerate(shapes_data):
        for path_idx, path_data in enumerate(shape['paths']):
            path_labels.append(f'S{shape_idx+1}P{path_idx+1}')
            areas.append(path_data['area'])
            colors_list.append(plt.cm.Set1(shape_idx))
    
    bars = ax.bar(path_labels, areas, color=colors_list, alpha=0.7)
    
    # Add value labels on bars
    for bar, area in zip(bars, areas):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + max(areas)*0.01,
                f'{area:.1f}', ha='center', va='bottom', fontsize=10)
    
    ax.set_title('📐 Path Areas Comparison', fontsize=12, fontweight='bold')
    ax.set_xlabel('Path (Shape-Path)')
    ax.set_ylabel('Area (mm²)')
    ax.grid(True, alpha=0.3, axis='y')

def plot_winding_analysis(ax, shapes_data):
    """Visualize winding directions"""
    
    ccw_count = 0
    cw_count = 0
    
    shape_info = []
    
    for shape_idx, shape in enumerate(shapes_data):
        for path_idx, path_data in enumerate(shape['paths']):
            winding = path_data['winding']
            if 'CCW' in winding:
                ccw_count += 1
            elif 'CW' in winding:
                cw_count += 1
            
            shape_info.append({
                'label': f'S{shape_idx+1}P{path_idx+1}',
                'winding': 'CCW' if 'CCW' in winding else 'CW',
                'area': path_data['area']
            })
    
    # Create pie chart for winding distribution
    if ccw_count + cw_count > 0:
        wedges, texts, autotexts = ax.pie([ccw_count, cw_count], 
                                          labels=['CCW (Exterior)', 'CW (Hole)'],
                                          colors=['#2E86AB', '#A23B72'],
                                          autopct='%1.0f%%',
                                          startangle=90)
    
    ax.set_title('🌀 Winding Direction Distribution', fontsize=12, fontweight='bold')
    
    # Add text summary
    text_summary = []
    for info in shape_info:
        text_summary.append(f"{info['label']}: {info['winding']} (Area: {info['area']:.1f})")
    
    ax.text(1.3, 0.5, '\n'.join(text_summary), 
           transform=ax.transAxes, fontsize=9,
           verticalalignment='center',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.3))

def plot_centers_and_bounds(ax, shapes_data, colors):
    """Plot shape centers and bounding boxes"""
    
    for shape_idx, shape in enumerate(shapes_data):
        shape_color = colors[shape_idx % len(colors)]
        
        for path_idx, path_data in enumerate(shape['paths']):
            bounds = path_data['bounds']
            center = path_data['center']
            
            # Draw bounding rectangle
            width = bounds['max_x'] - bounds['min_x']
            height = bounds['max_y'] - bounds['min_y']
            
            rect = patches.Rectangle((bounds['min_x'], bounds['min_y']), 
                                   width, height,
                                   linewidth=1, 
                                   edgecolor=shape_color,
                                   facecolor=shape_color,
                                   alpha=0.1)
            ax.add_patch(rect)
            
            # Mark center
            ax.plot(center[0], center[1], 'o', 
                   color=shape_color, markersize=8,
                   label=f'S{shape_idx+1}P{path_idx+1} Center')
            
            # Add center coordinates as text
            ax.annotate(f'({center[0]:.1f}, {center[1]:.1f})', 
                       xy=center, xytext=(5, 5), 
                       textcoords='offset points',
                       fontsize=8,
                       bbox=dict(boxstyle='round,pad=0.2', 
                               facecolor=shape_color, alpha=0.3))
    
    ax.set_title('🎯 Centers & Bounds', fontsize=12, fontweight='bold')
    ax.set_xlabel('X Coordinate (mm)')
    ax.set_ylabel('Y Coordinate (mm)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_aspect('equal', adjustable='box')

def create_individual_shape_plots(shapes_data, height=134.0):
    """Create individual detailed plots for each shape"""
    
    figures = []
    
    for shape_idx, shape in enumerate(shapes_data):
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # Plot the shape with high detail
        colors = plt.cm.Set1(np.linspace(0, 1, len(shape['paths'])))
        
        for path_idx, path_data in enumerate(shape['paths']):
            points = np.array(path_data['points'])
            color = colors[path_idx]
            
            # Main path
            linestyle = '-' if 'CCW' in path_data['winding'] else '--'
            ax.plot(points[:, 0], points[:, 1], 
                   color=color, linewidth=3, linestyle=linestyle,
                   label=f'Path {path_idx+1}: {path_data["winding"]} (Area: {path_data["area"]:.1f})')
            
            # Points with numbering (show every 20th point to avoid clutter)
            step = max(1, len(points) // 20)
            for i in range(0, len(points), step):
                ax.plot(points[i, 0], points[i, 1], 'o', 
                       color=color, markersize=3, alpha=0.6)
                if i % (step * 2) == 0:  # Label every other marked point
                    ax.annotate(f'{i}', xy=(points[i, 0], points[i, 1]),
                               xytext=(3, 3), textcoords='offset points',
                               fontsize=6, alpha=0.7)
            
            # Start and end points
            ax.plot(points[0, 0], points[0, 1], 's', 
                   color=color, markersize=10, label=f'Start P{path_idx+1}')
            ax.plot(points[-1, 0], points[-1, 1], '^', 
                   color=color, markersize=10, label=f'End P{path_idx+1}')
            
            # Center
            center = path_data['center']
            ax.plot(center[0], center[1], 'D', 
                   color=color, markersize=8, label=f'Center P{path_idx+1}')
        
        shape_name = "Banana" if shape_idx == 0 else "Ellipse"
        ax.set_title(f'🔍 Detailed View: Shape {shape_idx+1} ({shape_name}) at {height}mm\n'
                    f'ID: {shape["identifier"]}, Paths: {shape["num_paths"]}', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('X Coordinate (mm)')
        ax.set_ylabel('Y Coordinate (mm)')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        figures.append(fig)
    
    return figures

def save_visualizations(fig, individual_figs, height=134.0):
    """Save all visualizations to files"""
    
    # Save comprehensive overview
    overview_filename = f"clf_shapes_overview_{height}mm.png"
    fig.savefig(overview_filename, dpi=300, bbox_inches='tight')
    print(f"💾 Saved overview: {overview_filename}")
    
    # Save individual shape plots
    for i, individual_fig in enumerate(individual_figs):
        shape_name = "banana" if i == 0 else "ellipse"
        individual_filename = f"clf_shape_{i+1}_{shape_name}_{height}mm.png"
        individual_fig.savefig(individual_filename, dpi=300, bbox_inches='tight')
        print(f"💾 Saved individual: {individual_filename}")

def main():
    """Main visualization function"""
    
    # Load the shape data
    json_file = "shape_analysis_data_8.2mm.json"
    shapes_data = load_shape_data(json_file)
    
    if shapes_data is None:
        print("❌ Could not load shape data. Make sure to run detailed_shape_analysis.py first!")
        return
    
    print(f"✅ Loaded data for {len(shapes_data)} shapes")
    
    # Create comprehensive visualization
    print("🎨 Creating comprehensive visualization...")
    fig = create_comprehensive_visualization(shapes_data)
    
    # Create individual detailed plots
    print("🎨 Creating individual shape plots...")
    individual_figs = create_individual_shape_plots(shapes_data)
    
    # Save all visualizations
    save_visualizations(fig, individual_figs, height=8.2)
    
    # Show the plots
    print("🖼️  Displaying visualizations...")
    plt.show()
    
    print("✅ Visualization complete!")

if __name__ == "__main__":
    main()
