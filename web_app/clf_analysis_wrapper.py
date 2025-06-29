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
        
    def analyze_build(self, build_folder_path, height_mm, exclude_folders=True):
        """
        Analyze a build at specified height and return visualization data
        
        Args:
            build_folder_path: Path to the build folder
            height_mm: Height in millimeters to analyze
            exclude_folders: Whether to exclude folders based on patterns
            
        Returns:
            dict with analysis results and visualization paths
        """
        try:
            print(f"Starting CLF analysis for build: {build_folder_path}")
            print(f"Analysis height: {height_mm}mm")
            
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


def analyze_build_for_web(build_folder_path, height_mm, exclude_folders=True):
    """
    Convenience function for web app to analyze a build
    
    Args:
        build_folder_path: Path to the build folder
        height_mm: Height in millimeters to analyze
        exclude_folders: Whether to exclude folders based on patterns
        
    Returns:
        dict with analysis results
    """
    analyzer = CLFWebAnalyzer()
    return analyzer.analyze_build(build_folder_path, height_mm, exclude_folders)


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
