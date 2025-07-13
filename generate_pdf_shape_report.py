#!/usr/bin/env python3
"""
PDF Shape Report Generator

This program runs after get_platform_paths_shapes_shapely.py to generate a comprehensive
PDF report showing all shapes from CLF files organized by folder.

Author: Generated for CLF Analysis Clean
Date: 2025-07-07
"""

import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon
import argparse
from datetime import datetime

# Add the src directory to the path to import our utilities
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from utils.pyarcam.clfutil import CLFFile
    from utils.myfuncs.plotTools import (
        setup_platform_figure,
        draw_platform_boundary,
        add_reference_lines,
        set_platform_limits,
        draw_shape
    )
    from utils.myfuncs.print_utils import add_platform_labels
    from utils.myfuncs.shape_things import should_close_path
except ImportError as e:
    print(f"Error importing utilities: {e}")
    print("Make sure you're running this from the root directory of the CLF analysis project")
    sys.exit(1)


def get_user_input():
    """Get build ID and height from user input"""
    print("=== PDF Shape Report Generator ===")
    print("This program generates a PDF report of shapes from processed CLF files.\n")
    
    # Get build ID
    while True:
        build_id = input("Enter the build ID (e.g., 430848): ").strip()
        if build_id:
            # Check if the folder exists
            folder_name = f"preprocess build-{build_id}"
            abp_contents_path = os.path.join("abp_contents", folder_name)
            
            if os.path.exists(abp_contents_path):
                print(f"✓ Found folder: {abp_contents_path}")
                break
            else:
                print(f"✗ Folder not found: {abp_contents_path}")
                print("Available folders in abp_contents:")
                if os.path.exists("abp_contents"):
                    for item in os.listdir("abp_contents"):
                        if os.path.isdir(os.path.join("abp_contents", item)):
                            print(f"  - {item}")
                else:
                    print("  abp_contents directory not found!")
                print()
        else:
            print("Build ID cannot be empty. Please try again.")
    
    # Get height
    while True:
        height_str = input("Enter the height in mm (e.g., 136.55): ").strip()
        try:
            height = float(height_str)
            if height > 0:
                print(f"✓ Using height: {height} mm")
                break
            else:
                print("Height must be positive. Please try again.")
        except ValueError:
            print("Invalid height format. Please enter a number (e.g., 136.55)")
    
    return build_id, height


def find_clf_files(build_path):
    """Find all CLF files in the build directory and organize by folder"""
    clf_files_by_folder = {}
    
    print(f"Scanning for CLF files in: {build_path}")
    
    for root, dirs, files in os.walk(build_path):
        for file in files:
            if file.endswith('.clf'):
                file_path = os.path.join(root, file)
                folder_name = os.path.relpath(root, build_path)
                
                if folder_name not in clf_files_by_folder:
                    clf_files_by_folder[folder_name] = []
                
                clf_files_by_folder[folder_name].append({
                    'name': file,
                    'path': file_path,
                    'folder': folder_name
                })
    
    total_files = sum(len(files) for files in clf_files_by_folder.values())
    print(f"Found {total_files} CLF files in {len(clf_files_by_folder)} folders")
    
    return clf_files_by_folder


def extract_shapes_from_clf(clf_info, height):
    """Extract shape data from a CLF file at specified height"""
    try:
        part = CLFFile(clf_info['path'])
        if not hasattr(part, 'box'):
            return []
            
        layer = part.find(height)
        if layer is None:
            return []
            
        shapes_data = []
        
        if hasattr(layer, 'shapes'):
            for i, shape in enumerate(layer.shapes):
                # Get identifier if available
                identifier = None
                if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                    identifier = shape.model.id
                
                # Process shape points
                if hasattr(shape, 'points') and shape.points:
                    for path_idx, points in enumerate(shape.points):
                        if isinstance(points, np.ndarray) and points.shape[0] >= 2 and points.shape[1] >= 2:
                            should_close = should_close_path(points)
                            if hasattr(should_close, 'item'):
                                should_close = should_close.item()
                            
                            shape_data = {
                                'type': 'path',
                                'points': points.copy(),
                                'should_close': should_close,
                                'identifier': identifier,
                                'shape_index': i,
                                'path_index': path_idx
                            }
                            shapes_data.append(shape_data)
                
                # Process circles
                elif hasattr(shape, 'radius') and hasattr(shape, 'center'):
                    shape_data = {
                        'type': 'circle',
                        'center': shape.center,
                        'radius': shape.radius,
                        'identifier': identifier,
                        'shape_index': i
                    }
                    shapes_data.append(shape_data)
        
        return shapes_data
        
    except Exception as e:
        print(f"Error processing {clf_info['name']}: {e}")
        return []


def create_folder_page(pdf, folder_name, clf_files, height, page_num):
    """Create a PDF page for a specific folder showing all its shapes"""
    print(f"  Creating page {page_num} for folder: {folder_name}")
    
    # Create figure
    fig = plt.figure(figsize=(11, 8.5))  # Letter size
    
    # Title section
    fig.suptitle(f'Folder: {folder_name}\nHeight: {height} mm\nPage {page_num}', 
                 fontsize=14, fontweight='bold')
    
    # Create main plot area
    ax = plt.subplot(111)
    
    # Set up platform view
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    set_platform_limits(plt)
    add_platform_labels(plt)
    
    # Colors for different files
    colors = plt.cm.tab10(np.linspace(0, 1, len(clf_files)))
    
    total_shapes = 0
    files_with_shapes = 0
    legend_handles = []
    legend_labels = []
    
    # Process each CLF file in the folder
    for file_idx, (clf_info, color) in enumerate(zip(clf_files, colors)):
        shapes_data = extract_shapes_from_clf(clf_info, height)
        
        if shapes_data:
            files_with_shapes += 1
            total_shapes += len(shapes_data)
            
            # Add to legend
            legend_handles.append(plt.Line2D([0], [0], color=color, lw=2))
            legend_labels.append(f"{clf_info['name']} ({len(shapes_data)} shapes)")
            
            # Draw shapes
            for shape_data in shapes_data:
                if shape_data['type'] == 'path':
                    points = shape_data['points']
                    draw_shape(plt, points, color, alpha=0.7, linewidth=1)
                elif shape_data['type'] == 'circle':
                    circle = plt.Circle(
                        shape_data['center'],
                        shape_data['radius'],
                        color=color,
                        fill=False,
                        alpha=0.7,
                        linewidth=1
                    )
                    ax.add_artist(circle)
    
    # Add legend if there are shapes
    if legend_handles:
        plt.legend(legend_handles, legend_labels, 
                  bbox_to_anchor=(1.05, 1), loc='upper left', 
                  borderaxespad=0., fontsize=8)
    
    # Add summary text
    summary_text = f"Files in folder: {len(clf_files)}\n"
    summary_text += f"Files with shapes: {files_with_shapes}\n"
    summary_text += f"Total shapes: {total_shapes}"
    
    plt.figtext(0.02, 0.02, summary_text, fontsize=10, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
    
    plt.tight_layout()
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    
    return total_shapes, files_with_shapes


def generate_summary_page(pdf, build_id, height, total_folders, total_files, 
                         total_shapes, folders_with_shapes):
    """Generate a summary page for the PDF report"""
    fig = plt.figure(figsize=(11, 8.5))
    
    # Title
    fig.suptitle(f'CLF Shape Report Summary\nBuild: {build_id} | Height: {height} mm', 
                 fontsize=16, fontweight='bold')
    
    # Remove axes
    ax = plt.subplot(111)
    ax.axis('off')
    
    # Summary statistics
    summary_stats = f"""
ANALYSIS SUMMARY
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

BUILD INFORMATION:
• Build ID: {build_id}
• Analysis Height: {height} mm
• Build Path: abp_contents/preprocess build-{build_id}

PROCESSING RESULTS:
• Total Folders Scanned: {total_folders}
• Total CLF Files Found: {total_files}
• Folders with Shapes: {folders_with_shapes}
• Total Shapes Extracted: {total_shapes}

NOTES:
• Each page shows shapes from one folder
• Different colors represent different CLF files
• Shapes are drawn at the specified height layer
• Platform boundaries and reference lines are shown for context
"""
    
    plt.text(0.05, 0.95, summary_stats, transform=ax.transAxes, 
             fontsize=12, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
    
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


def main():
    """Main function to generate PDF report"""
    try:
        # Get user input
        build_id, height = get_user_input()
        
        # Set up paths
        folder_name = f"preprocess build-{build_id}"
        build_path = os.path.join("abp_contents", folder_name)
        
        # Create output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"shape_report_build_{build_id}_{height}mm_{timestamp}.pdf"
        
        print(f"\nGenerating PDF report: {output_filename}")
        print(f"Source: {build_path}")
        print(f"Height: {height} mm\n")
        
        # Find all CLF files organized by folder
        clf_files_by_folder = find_clf_files(build_path)
        
        if not clf_files_by_folder:
            print("No CLF files found!")
            return
        
        # Generate PDF
        with PdfPages(output_filename) as pdf:
            # Track statistics
            total_folders = len(clf_files_by_folder)
            total_files = sum(len(files) for files in clf_files_by_folder.values())
            grand_total_shapes = 0
            folders_with_shapes = 0
            page_num = 1
            
            print("Generating PDF pages...")
            
            # Generate summary page first
            generate_summary_page(pdf, build_id, height, total_folders, 
                                 total_files, "TBD", "TBD")
            
            # Process each folder
            for folder_name, clf_files in sorted(clf_files_by_folder.items()):
                page_num += 1
                total_shapes, files_with_shapes = create_folder_page(
                    pdf, folder_name, clf_files, height, page_num
                )
                
                grand_total_shapes += total_shapes
                if total_shapes > 0:
                    folders_with_shapes += 1
            
            # Update summary page with final statistics
            print(f"\nRegenerating summary page with final statistics...")
            generate_summary_page(pdf, build_id, height, total_folders, 
                                 total_files, grand_total_shapes, folders_with_shapes)
        
        print(f"\n✓ PDF report generated successfully!")
        print(f"📄 Output file: {output_filename}")
        print(f"📊 Summary:")
        print(f"   • {total_folders} folders processed")
        print(f"   • {total_files} CLF files scanned")
        print(f"   • {folders_with_shapes} folders with shapes")
        print(f"   • {grand_total_shapes} total shapes found")
        print(f"   • {page_num} pages generated")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError generating PDF report: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
