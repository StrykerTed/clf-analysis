"""
CLF Analysis Wrapper for Web Application
This module provides web-specific CLF analysis functionality without modifying the existing codebase.
It duplicates necessary functionality from get_platform_paths_shapes_shapely.py and related modules.
"""

import os
import sys
import json
import tempfile
import shutil
from datetime import datetime
import base64
import io

# Configure matplotlib to use non-interactive backend for web application
import matplotlib
matplotlib.use('Agg')  # Use Anti-Grain Geometry backend (non-interactive)

# Add the src directory to path for imports
src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Add root directory to path
root_dir = os.path.dirname(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import setup_paths
from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import find_clf_files, load_exclusion_patterns, should_skip_folder
from utils.platform_analysis.visualization_utils import create_clean_platform
from config import PROJECT_ROOT

class CLFWebAnalyzer:
    """Web-specific CLF analyzer that generates SVG/PNG for web display"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.config_dir = os.path.join(self.project_root, "config")
        
    def analyze_build(self, build_folder_path, height_mm, exclude_folders=True, identifiers=None):
        """
        Analyze a build at specified height and return visualization data
        
        Args:
            build_folder_path: Path to the build folder
            height_mm: Height in millimeters to analyze
            exclude_folders: Whether to exclude folders based on patterns
            identifiers: List of specific identifier numbers to analyze, or None for all
            
        Returns:
            dict with analysis results and visualization paths
        """
        try:
            print(f"Starting CLF analysis for build: {build_folder_path}")
            print(f"Analysis height: {height_mm}mm")
            if identifiers:
                print(f"Filtering to identifiers: {identifiers}")
            
            # Validate inputs
            if not os.path.exists(build_folder_path):
                raise ValueError(f"Build folder not found: {build_folder_path}")
                
            if not (0 <= height_mm <= 9999.99):
                raise ValueError(f"Invalid height: {height_mm}mm. Must be between 0 and 9999.99")
            
            # Create temporary output directory for this analysis
            temp_dir = tempfile.mkdtemp(prefix="clf_web_analysis_")
            print(f"Created temporary directory: {temp_dir}")
            
            # Load exclusion patterns
            exclusion_patterns = []
            if exclude_folders:
                try:
                    exclusion_patterns = load_exclusion_patterns(self.config_dir)
                    print(f"Loaded {len(exclusion_patterns)} exclusion patterns")
                except Exception as e:
                    print(f"Warning: Could not load exclusion patterns: {e}")
            
            # Find CLF files
            print("Finding CLF files...")
            all_clf_files = find_clf_files(build_folder_path)
            print(f"Found {len(all_clf_files)} total CLF files")
            
            # Filter CLF files based on exclusion patterns
            if exclude_folders and exclusion_patterns:
                clf_files = []
                excluded_files = []
                
                for clf_info in all_clf_files:
                    should_skip = should_skip_folder(clf_info['folder'], exclusion_patterns)
                    if should_skip:
                        excluded_files.append(clf_info)
                    else:
                        clf_files.append(clf_info)
                
                print(f"Excluded {len(excluded_files)} files based on folder patterns")
                print(f"Processing {len(clf_files)} CLF files")
            else:
                clf_files = all_clf_files
                excluded_files = []
                print(f"Processing all {len(clf_files)} CLF files (no exclusions)")
            
            # Create analysis results
            analysis_results = {
                "timestamp": datetime.now().isoformat(),
                "build_folder": build_folder_path,
                "height_mm": height_mm,
                "exclude_folders": exclude_folders,
                "exclusion_patterns": exclusion_patterns,
                "total_files_found": len(all_clf_files),
                "files_processed": len(clf_files),
                "files_excluded": len(excluded_files),
                "temp_directory": temp_dir,
                "visualizations": {}
            }
            
            # Generate clean platform visualization
            print(f"Generating clean platform visualization at {height_mm}mm...")
            try:
                # Create the visualization using existing utilities
                if identifiers is not None:
                    # Use custom visualization with identifier filtering
                    clean_file = self.create_filtered_clean_platform(
                        clf_files, 
                        temp_dir,
                        height=height_mm,
                        identifiers=identifiers,
                        fill_closed=True,
                        save_clean_png=True
                    )
                else:
                    # Use standard visualization for all identifiers
                    clean_file = create_clean_platform(
                        clf_files, 
                        temp_dir,
                        height=height_mm,
                        fill_closed=True,  # Fill closed shapes for better visualization
                        alignment_style_only=False,
                        save_clean_png=True
                    )
                
                if clean_file:
                    # Convert relative path to absolute
                    if not os.path.isabs(clean_file):
                        clean_file_abs = os.path.join(temp_dir, clean_file)
                    else:
                        clean_file_abs = clean_file
                    
                    print(f"Created clean platform file: {clean_file_abs}")
                    
                    # Check if file exists and convert to base64 for web display
                    if os.path.exists(clean_file_abs):
                        with open(clean_file_abs, 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            
                        analysis_results["visualizations"]["clean_platform"] = {
                            "filename": os.path.basename(clean_file_abs),
                            "path": clean_file_abs,
                            "base64_data": img_data,
                            "type": "image/png"
                        }
                        print("Successfully converted visualization to base64")
                    else:
                        print(f"Warning: Generated file not found at {clean_file_abs}")
                        
                else:
                    print("No clean platform file was generated")
                    
            except Exception as viz_error:
                print(f"Error generating visualization: {viz_error}")
                analysis_results["visualizations"]["error"] = str(viz_error)
            
            # Add file details to results
            analysis_results["processed_files"] = []
            for clf_info in clf_files:
                try:
                    part = CLFFile(clf_info['path'])
                    file_detail = {
                        "name": clf_info['name'],
                        "folder": clf_info['folder'],
                        "path": clf_info['path'],
                        "num_layers": part.nlayers if hasattr(part, 'nlayers') else 0,
                        "bounds": None
                    }
                    
                    if hasattr(part, 'box'):
                        file_detail["bounds"] = {
                            "x_range": [float(part.box.min[0]), float(part.box.max[0])],
                            "y_range": [float(part.box.min[1]), float(part.box.max[1])],
                            "z_range": [float(part.box.min[2]), float(part.box.max[2])]
                        }
                    
                    analysis_results["processed_files"].append(file_detail)
                    
                except Exception as e:
                    print(f"Error reading CLF file {clf_info['name']}: {e}")
            
            # Add excluded file details
            analysis_results["excluded_files"] = []
            for clf_info in excluded_files:
                excluded_detail = {
                    "name": clf_info['name'],
                    "folder": clf_info['folder'],
                    "path": clf_info['path'],
                    "matching_patterns": [pattern for pattern in exclusion_patterns if pattern in clf_info['folder']]
                }
                analysis_results["excluded_files"].append(excluded_detail)
            
            print("CLF analysis completed successfully")
            return analysis_results
            
        except Exception as e:
            print(f"Error in CLF analysis: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "build_folder": build_folder_path,
                "height_mm": height_mm
            }
    
    def cleanup_temp_files(self, temp_directory):
        """Clean up temporary files created during analysis"""
        try:
            if os.path.exists(temp_directory):
                shutil.rmtree(temp_directory)
                print(f"Cleaned up temporary directory: {temp_directory}")
        except Exception as e:
            print(f"Warning: Could not clean up temp directory {temp_directory}: {e}")
    
    def create_filtered_clean_platform(self, clf_files, output_dir, height=1.0, identifiers=None, 
                                     fill_closed=False, save_clean_png=True):
        """
        Create a clean platform view filtered by specific identifiers
        
        Args:
            clf_files: List of CLF file info dictionaries
            output_dir: Output directory for visualization
            height: Height in mm to analyze
            identifiers: List of identifier numbers to include (strings or ints)
            fill_closed: Whether to fill closed shapes
            save_clean_png: Whether to save PNG output
            
        Returns:
            Path to generated PNG file or None
        """
        import json
        import numpy as np
        from utils.myfuncs.shape_things import should_close_path
        
        print(f"Creating filtered platform view for identifiers: {identifiers}")
        
        # Convert identifiers to strings for consistent comparison
        if identifiers is not None:
            identifier_strings = [str(id_val).strip() for id_val in identifiers if str(id_val).strip()]
            print(f"Normalized identifiers for filtering: {identifier_strings}")
        else:
            identifier_strings = None
        
        # Define colors dictionary
        colors = {
            'Part.clf': 'blue',
            'WaferSupport.clf': 'red',
            'Net.clf': 'green'
        }
        
        # Process all CLF files and collect shape data
        all_shape_data = []
        filtered_shape_data = []
        
        for clf_info in clf_files:
            try:
                part = CLFFile(clf_info['path'])
                if not hasattr(part, 'box'):
                    continue
                    
                layer = part.find(height)
                if layer is None:
                    continue
                    
                if hasattr(layer, 'shapes'):
                    for shape in layer.shapes:
                        color = colors.get(clf_info['name'], 'gray')
                        
                        # Extract shape identifier if it exists
                        shape_identifier = None
                        if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                            shape_identifier = str(shape.model.id).strip()
                        
                        # Process shape points
                        if hasattr(shape, 'points') and shape.points:
                            points = shape.points[0]
                            if isinstance(points, np.ndarray) and points.shape[0] >= 1 and points.shape[1] >= 2:
                                should_close = False
                                try:
                                    should_close = should_close_path(points)
                                    if hasattr(should_close, 'item'):
                                        should_close = should_close.item()
                                except Exception as e:
                                    print(f"Error in should_close_path for {clf_info['name']}: {str(e)}")
                                    should_close = False
                                
                                shape_data = {
                                    'type': 'path',
                                    'points': points.tolist(),
                                    'color': color,
                                    'clf_name': clf_info['name'],
                                    'clf_folder': clf_info['folder'],
                                    'fill_closed': fill_closed,
                                    'should_close': should_close,
                                    'identifier': shape_identifier
                                }
                                all_shape_data.append(shape_data)
                                
                                # Filter by identifier if specified
                                if identifier_strings is None:
                                    # No filter, include all shapes
                                    filtered_shape_data.append(shape_data)
                                else:
                                    # Include only shapes with matching identifiers
                                    if shape_identifier and shape_identifier in identifier_strings:
                                        filtered_shape_data.append(shape_data)
                                        print(f"Including shape with identifier: {shape_identifier}")
                                    elif shape_identifier:
                                        print(f"Excluding shape with identifier: {shape_identifier}")
                                    else:
                                        print("Excluding shape without identifier")
                        
                        # Process circle shapes
                        elif hasattr(shape, 'radius') and hasattr(shape, 'center'):
                            shape_identifier = None
                            if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                                shape_identifier = str(shape.model.id).strip()
                            
                            shape_data = {
                                'type': 'circle',
                                'center': shape.center.tolist(),
                                'radius': shape.radius,
                                'color': color,
                                'clf_name': clf_info['name'],
                                'clf_folder': clf_info['folder'],
                                'identifier': shape_identifier
                            }
                            all_shape_data.append(shape_data)
                            
                            # Filter by identifier
                            if identifier_strings is None:
                                filtered_shape_data.append(shape_data)
                            else:
                                if shape_identifier and shape_identifier in identifier_strings:
                                    filtered_shape_data.append(shape_data)
                                    print(f"Including circle with identifier: {shape_identifier}")
            
            except Exception as e:
                print(f"Error processing {clf_info['name']} at height {height}mm: {str(e)}")
        
        print(f"Total shapes found: {len(all_shape_data)}")
        print(f"Shapes after filtering: {len(filtered_shape_data)}")
        
        # Create the visualization if requested
        if save_clean_png and filtered_shape_data:
            import matplotlib.pyplot as plt
            from matplotlib.patches import Polygon
            from utils.myfuncs.plotTools import setup_platform_figure, save_platform_figure, draw_shape
            
            # Create figure with equal aspect ratio
            fig = setup_platform_figure(figsize=(15, 15))
            
            # Remove all margins and spacing
            ax = plt.gca()
            ax.set_position([0, 0, 1, 1])
            
            # Set exact limits for platform size
            plt.xlim(-125, 125)
            plt.ylim(-125, 125)
            
            # Turn off all chart elements
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            plt.axis('off')
            
            # Draw filtered shapes
            for shape_data in filtered_shape_data:
                if shape_data['type'] == 'path' and 'points' in shape_data:
                    points = np.array(shape_data['points'])
                    color = shape_data['color']
                    
                    if fill_closed and shape_data.get('should_close', False):
                        polygon = Polygon(points, facecolor='black', edgecolor=color, alpha=0.5)
                        plt.gca().add_patch(polygon)
                    else:
                        draw_shape(plt, points, color)
                        
                elif shape_data['type'] == 'circle':
                    circle = plt.Circle(shape_data['center'], shape_data['radius'], 
                                       color=shape_data['color'], fill=False, alpha=0.7)
                    plt.gca().add_artist(circle)
            
            plt.axis('equal')  # Ensure perfect square
            
            # Create filename with identifier info
            if identifier_strings:
                id_suffix = "_".join(identifier_strings[:3])  # Limit to first 3 IDs for filename
                if len(identifier_strings) > 3:
                    id_suffix += f"_plus{len(identifier_strings)-3}more"
                filename = f'clean_platform_{height}mm_filtered_{id_suffix}.png'
            else:
                filename = f'clean_platform_{height}mm_all.png'
                
            output_path = os.path.join(output_dir, "clean_platforms", filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            save_platform_figure(plt, output_path, pad_inches=0)
            png_path = os.path.join("clean_platforms", filename)
            
            print(f"Saved filtered visualization to: {output_path}")
            
            return png_path
        
        elif save_clean_png and not filtered_shape_data:
            print("No shapes found after filtering - no visualization generated")
            return None
        
        else:
            return None


def analyze_build_for_web(build_folder_path, height_mm, exclude_folders=True, identifiers=None):
    """
    Convenience function for web app to analyze a build
    
    Args:
        build_folder_path: Path to the build folder
        height_mm: Height in millimeters to analyze
        exclude_folders: Whether to exclude folders based on patterns
        identifiers: List of specific identifier numbers to analyze, or None for all
        
    Returns:
        dict with analysis results
    """
    analyzer = CLFWebAnalyzer()
    return analyzer.analyze_build(build_folder_path, height_mm, exclude_folders, identifiers)


if __name__ == "__main__":
    # Test the analyzer
    test_build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/build-431627"
    test_height = 1.0
    
    print("Testing CLF Web Analyzer...")
    results = analyze_build_for_web(test_build_path, test_height, exclude_folders=True)
    
    if "error" in results:
        print(f"Analysis failed: {results['error']}")
    else:
        print("Analysis successful!")
        print(f"Processed {results['files_processed']} files")
        print(f"Excluded {results['files_excluded']} files")
        if "clean_platform" in results["visualizations"]:
            print("Generated clean platform visualization")
        
        # Cleanup
        analyzer = CLFWebAnalyzer()
        analyzer.cleanup_temp_files(results["temp_directory"])
