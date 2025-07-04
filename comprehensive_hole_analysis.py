#!/usr/bin/env python3
"""
Comprehensive Hole Analysis Script

This script loops through every layer height in all skin files,
finds every hole, and reports anomalies in count and shape characteristics.

Holes are expected to be:
- Shape[1] Path[0] in skin files
- Reasonably elongated oblong shapes
- Maximum of 18 holes per layer
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Any
import numpy as np

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import setup_paths

from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import find_clf_files, should_skip_folder, load_exclusion_patterns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_hole_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def calculate_bbox_properties(bbox: Tuple[float, float, float, float]) -> Dict[str, float]:
    """Calculate properties of a bounding box for shape analysis."""
    min_x, min_y, max_x, max_y = bbox
    width = max_x - min_x
    height = max_y - min_y
    area = width * height
    
    # Calculate aspect ratio (width/height or height/width, whichever is > 1)
    if width > height:
        aspect_ratio = width / height if height > 0 else float('inf')
    else:
        aspect_ratio = height / width if width > 0 else float('inf')
    
    return {
        'width': width,
        'height': height,
        'area': area,
        'aspect_ratio': aspect_ratio
    }

def is_reasonable_hole_shape(bbox: Tuple[float, float, float, float]) -> Tuple[bool, str]:
    """
    Check if a hole bbox represents a reasonable elongated oblong shape.
    
    Returns:
        Tuple of (is_valid, reason)
    """
    props = calculate_bbox_properties(bbox)
    
    # Check minimum area (too small might be noise)
    min_area = 0.1  # Adjust based on your data scale
    if props['area'] < min_area:
        return False, f"Area too small: {props['area']:.4f}"
    
    # Check maximum area (too large might be incorrect detection)
    max_area = 1000.0  # Adjust based on your data scale
    if props['area'] > max_area:
        return False, f"Area too large: {props['area']:.4f}"
    
    # Check aspect ratio (should be elongated but not extreme)
    min_aspect_ratio = 1.5  # At least somewhat elongated
    max_aspect_ratio = 10.0  # Not extremely thin
    
    if props['aspect_ratio'] < min_aspect_ratio:
        return False, f"Not elongated enough: aspect ratio {props['aspect_ratio']:.2f}"
    
    if props['aspect_ratio'] > max_aspect_ratio:
        return False, f"Too elongated: aspect ratio {props['aspect_ratio']:.2f}"
    
    return True, "Valid hole shape"

def analyze_holes_at_height(height: float, build_folder: str) -> Dict[str, Any]:
    """Analyze holes at a specific height in skin files."""
    logger.info(f"Analyzing holes at height {height}mm in {build_folder}")
    
    # Load exclusion patterns
    exclusion_patterns = load_exclusion_patterns()
    
    # Get all clf files using the correct pattern
    clf_files = find_clf_files(build_folder)
    
    # Filter for skin files only
    skin_files = []
    for clf_info in clf_files:
        if should_skip_folder(clf_info['folder'], exclusion_patterns):
            continue
        filename = os.path.basename(clf_info['file']).lower()
        if 'skin' in filename:
            skin_files.append(clf_info['file'])
    
    logger.info(f"Found {len(skin_files)} skin files")
    
    analysis_results = {
        'height': height,
        'build_folder': build_folder,
        'total_skin_files': len(skin_files),
        'files_with_holes': 0,
        'total_holes': 0,
        'hole_count_errors': [],
        'hole_shape_errors': [],
        'valid_holes': [],
        'file_analyses': []
    }
    
    for clf_file_path in skin_files:
        file_basename = os.path.basename(clf_file_path)
        logger.info(f"Processing {file_basename}")
        
        try:
            # Load CLF file and get platform data at this height
            clf_file = CLFFile(clf_file_path)
            platform_data = clf_file.get_platform_data(height)
            
            if not platform_data or 'shapes' not in platform_data:
                logger.warning(f"No platform data for {file_basename} at {height}mm")
                continue
            
            shapes = platform_data['shapes']
            holes_in_file = []
            
            # Look for holes (shape[1] path[0])
            for shape_idx, shape in enumerate(shapes):
                if len(shape) > 1:  # Has potential holes
                    hole_path = shape[1]  # Second shape is the hole
                    if len(hole_path) > 0:  # Has actual hole data
                        hole_points = hole_path[0]  # First path of the hole
                        
                        if len(hole_points) >= 3:  # Valid polygon
                            # Calculate bounding box
                            x_coords = [p[0] for p in hole_points]
                            y_coords = [p[1] for p in hole_points]
                            bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                            
                            # Check hole shape validity
                            is_valid, reason = is_reasonable_hole_shape(bbox)
                            
                            hole_info = {
                                'shape_idx': shape_idx,
                                'bbox': bbox,
                                'properties': calculate_bbox_properties(bbox),
                                'is_valid': is_valid,
                                'validation_reason': reason,
                                'point_count': len(hole_points)
                            }
                            
                            holes_in_file.append(hole_info)
                            
                            if is_valid:
                                analysis_results['valid_holes'].append(hole_info)
                            else:
                                analysis_results['hole_shape_errors'].append({
                                    'file': file_basename,
                                    'shape_idx': shape_idx,
                                    'reason': reason,
                                    'bbox': bbox,
                                    'properties': hole_info['properties']
                                })
            
            # Check hole count
            hole_count = len(holes_in_file)
            if hole_count > 18:
                error_msg = f"Too many holes: {hole_count} (max 18)"
                logger.error(f"{file_basename}: {error_msg}")
                analysis_results['hole_count_errors'].append({
                    'file': file_basename,
                    'count': hole_count,
                    'error': error_msg
                })
            
            if hole_count > 0:
                analysis_results['files_with_holes'] += 1
                analysis_results['total_holes'] += hole_count
            
            # Store file analysis
            file_analysis = {
                'file': file_basename,
                'hole_count': hole_count,
                'holes': holes_in_file,
                'shape_count': len(shapes)
            }
            analysis_results['file_analyses'].append(file_analysis)
            
            logger.info(f"{file_basename}: {hole_count} holes found")
            
        except Exception as e:
            logger.error(f"Error processing {file_basename}: {str(e)}")
            analysis_results['hole_shape_errors'].append({
                'file': file_basename,
                'error': f"Processing error: {str(e)}"
            })
    
    return analysis_results

def get_all_layer_heights(build_folder: str) -> List[float]:
    """Get all available layer heights from skin files."""
    logger.info("Discovering all layer heights...")
    
    # Load exclusion patterns
    exclusion_patterns = load_exclusion_patterns()
    
    clf_files = find_clf_files(build_folder)
    
    # Filter for skin files only
    skin_files = []
    for clf_info in clf_files:
        if should_skip_folder(clf_info['folder'], exclusion_patterns):
            continue
        filename = os.path.basename(clf_info['file']).lower()
        if 'skin' in filename:
            skin_files.append(clf_info['file'])
    
    all_heights = set()
    
    for clf_file_path in skin_files[:3]:  # Sample first few files to get height range
        try:
            clf_file = CLFFile(clf_file_path)
            heights = clf_file.get_available_heights()
            all_heights.update(heights)
        except Exception as e:
            logger.warning(f"Could not get heights from {os.path.basename(clf_file_path)}: {e}")
    
    sorted_heights = sorted(list(all_heights))
    logger.info(f"Found {len(sorted_heights)} unique layer heights")
    return sorted_heights

def main():
    """Main function to run comprehensive hole analysis."""
    logger.info("Starting Comprehensive Hole Analysis")
    
    # Setup paths
    current_dir = Path(__file__).parent
    build_folder = current_dir / "abp_contents" / "preprocess build-424292"
    
    if not build_folder.exists():
        logger.error(f"Build folder not found: {build_folder}")
        return
    
    # Create output directory
    output_dir = current_dir / "my_outputs" / "comprehensive_hole_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all layer heights
    try:
        layer_heights = get_all_layer_heights(str(build_folder))
        if not layer_heights:
            logger.error("No layer heights found")
            return
        
        logger.info(f"Will analyze {len(layer_heights)} layer heights")
        
    except Exception as e:
        logger.error(f"Failed to get layer heights: {e}")
        return
    
    # Analyze holes at each height
    all_results = []
    summary_stats = {
        'total_heights_analyzed': 0,
        'heights_with_holes': 0,
        'total_files_processed': 0,
        'total_files_with_holes': 0,
        'total_holes_found': 0,
        'total_hole_count_errors': 0,
        'total_hole_shape_errors': 0,
        'valid_holes_found': 0
    }
    
    for height in layer_heights:
        try:
            height_results = analyze_holes_at_height(height, str(build_folder))
            all_results.append(height_results)
            
            # Update summary stats
            summary_stats['total_heights_analyzed'] += 1
            if height_results['total_holes'] > 0:
                summary_stats['heights_with_holes'] += 1
            
            summary_stats['total_files_processed'] += height_results['total_skin_files']
            summary_stats['total_files_with_holes'] += height_results['files_with_holes']
            summary_stats['total_holes_found'] += height_results['total_holes']
            summary_stats['total_hole_count_errors'] += len(height_results['hole_count_errors'])
            summary_stats['total_hole_shape_errors'] += len(height_results['hole_shape_errors'])
            summary_stats['valid_holes_found'] += len(height_results['valid_holes'])
            
        except Exception as e:
            logger.error(f"Failed to analyze height {height}: {e}")
    
    # Save detailed results
    results_file = output_dir / "comprehensive_hole_analysis_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'summary': summary_stats,
            'detailed_results': all_results
        }, f, indent=2)
    
    # Generate summary report
    report_file = output_dir / "hole_analysis_summary_report.txt"
    with open(report_file, 'w') as f:
        f.write("COMPREHENSIVE HOLE ANALYSIS SUMMARY REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("OVERALL STATISTICS:\n")
        f.write(f"- Total layer heights analyzed: {summary_stats['total_heights_analyzed']}\n")
        f.write(f"- Heights with holes found: {summary_stats['heights_with_holes']}\n")
        f.write(f"- Total files processed: {summary_stats['total_files_processed']}\n")
        f.write(f"- Files with holes: {summary_stats['total_files_with_holes']}\n")
        f.write(f"- Total holes found: {summary_stats['total_holes_found']}\n")
        f.write(f"- Valid holes: {summary_stats['valid_holes_found']}\n")
        f.write(f"- Hole count errors: {summary_stats['total_hole_count_errors']}\n")
        f.write(f"- Hole shape errors: {summary_stats['total_hole_shape_errors']}\n\n")
        
        # Error details
        if summary_stats['total_hole_count_errors'] > 0:
            f.write("HOLE COUNT ERRORS (>18 holes):\n")
            for result in all_results:
                for error in result['hole_count_errors']:
                    f.write(f"- Height {result['height']}mm, {error['file']}: {error['count']} holes\n")
            f.write("\n")
        
        if summary_stats['total_hole_shape_errors'] > 0:
            f.write("HOLE SHAPE ERRORS:\n")
            for result in all_results:
                for error in result['hole_shape_errors']:
                    if 'reason' in error:
                        f.write(f"- Height {result['height']}mm, {error['file']}: {error['reason']}\n")
                    else:
                        f.write(f"- Height {result['height']}mm, {error['file']}: {error.get('error', 'Unknown error')}\n")
            f.write("\n")
        
        # Height-by-height summary
        f.write("HEIGHT-BY-HEIGHT SUMMARY:\n")
        for result in all_results:
            f.write(f"Height {result['height']}mm: {result['total_holes']} holes in {result['files_with_holes']} files\n")
    
    logger.info(f"Analysis complete. Results saved to {output_dir}")
    logger.info(f"Summary: {summary_stats['total_holes_found']} holes found across {summary_stats['total_heights_analyzed']} heights")
    logger.info(f"Errors: {summary_stats['total_hole_count_errors']} count errors, {summary_stats['total_hole_shape_errors']} shape errors")
    
    print("\n" + "="*60)
    print("COMPREHENSIVE HOLE ANALYSIS COMPLETE")
    print("="*60)
    print(f"Total holes found: {summary_stats['total_holes_found']}")
    print(f"Valid holes: {summary_stats['valid_holes_found']}")
    print(f"Heights analyzed: {summary_stats['total_heights_analyzed']}")
    print(f"Count errors (>18 holes): {summary_stats['total_hole_count_errors']}")
    print(f"Shape errors: {summary_stats['total_hole_shape_errors']}")
    print(f"\nDetailed results: {results_file}")
    print(f"Summary report: {report_file}")

if __name__ == "__main__":
    main()
