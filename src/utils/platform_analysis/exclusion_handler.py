# exclusion_handler.py
"""
Handles exclusion-related functionality for platform analysis.
This module contains functions for processing excluded files, creating exclusion reports,
and managing excluded identifier views.
"""

import os
import csv
from utils.platform_analysis.visualization_utils import create_combined_excluded_identifier_platform_view


def create_exclusion_details_files(excluded_files_details, exclusion_patterns, output_dir):
    """
    Create CSV and TXT files documenting excluded files and their details.
    
    Args:
        excluded_files_details (list): List of dictionaries containing excluded file details
        exclusion_patterns (list): List of exclusion patterns used
        output_dir (str): Output directory for the files
        
    Returns:
        dict: Dictionary containing the created file information
    """
    print("\nCreating exclusion details file...")
    
    # Create CSV file
    csv_filename = "excluded_files_details.csv"
    csv_path = os.path.join(output_dir, csv_filename)
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'folder', 'full_path', 'num_layers', 'matching_patterns']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for detail in excluded_files_details:
            # Convert list to string for CSV
            detail_copy = detail.copy()
            detail_copy['matching_patterns'] = ', '.join(detail['matching_patterns'])
            writer.writerow(detail_copy)
    
    # Create TXT file
    txt_filename = "excluded_files_details.txt"
    txt_path = os.path.join(output_dir, txt_filename)
    
    with open(txt_path, 'w', encoding='utf-8') as txtfile:
        txtfile.write("EXCLUDED FILES DETAILS\n")
        txtfile.write("=" * 50 + "\n\n")
        txtfile.write(f"Total excluded files: {len(excluded_files_details)}\n")
        txtfile.write(f"Exclusion patterns used: {', '.join(exclusion_patterns)}\n\n")
        
        for i, detail in enumerate(excluded_files_details, 1):
            txtfile.write(f"{i}. {detail['filename']}\n")
            txtfile.write(f"   Folder: {detail['folder']}\n")
            txtfile.write(f"   Full Path: {detail['full_path']}\n")
            txtfile.write(f"   Number of Layers: {detail['num_layers']}\n")
            txtfile.write(f"   Matching Patterns: {', '.join(detail['matching_patterns'])}\n")
            txtfile.write("-" * 40 + "\n\n")
    
    exclusion_files_info = {
        "csv_file": csv_filename,
        "txt_file": txt_filename,
        "total_excluded": len(excluded_files_details)
    }
    
    print(f"Created exclusion details CSV: {csv_path}")
    print(f"Created exclusion details TXT: {txt_path}")
    print(f"Total excluded files documented: {len(excluded_files_details)}")
    
    return exclusion_files_info


def create_excluded_identifier_view(excluded_shapes_by_identifier, output_dir, platform_info):
    """
    Create combined view of excluded identifiers if requested.
    
    Args:
        excluded_shapes_by_identifier (dict): Dictionary of excluded shapes by identifier
        output_dir (str): Output directory for the view
        platform_info (dict): Platform information dictionary to update
        
    Returns:
        bool: True if view was created successfully, False otherwise
    """
    if not excluded_shapes_by_identifier:
        return False
        
    print("\nGenerating combined EXCLUDED identifier platform view...")
    excluded_combined_view_file = create_combined_excluded_identifier_platform_view(
        excluded_shapes_by_identifier, output_dir
    )
    
    if excluded_combined_view_file:
        platform_info["combined_excluded_identifier_view"] = {
            "filename": excluded_combined_view_file,
            "total_identifiers": len([id for id in excluded_shapes_by_identifier.keys() if id != 'no_identifier'])
        }
        print(f"Created combined EXCLUDED identifier view with "
              f"{platform_info['combined_excluded_identifier_view']['total_identifiers']} identifiers")
        return True
    
    return False


def process_excluded_files_details(draw_excluded, excluded_files_details, exclusion_patterns, 
                                 excluded_shapes_by_identifier, output_dir, platform_info):
    """
    Process all exclusion-related file creation and view generation.
    
    Args:
        draw_excluded (bool): Whether excluded files should be processed
        excluded_files_details (list): List of excluded file details
        exclusion_patterns (list): Exclusion patterns used
        excluded_shapes_by_identifier (dict): Excluded shapes by identifier
        output_dir (str): Output directory
        platform_info (dict): Platform information dictionary to update
    """
    if not draw_excluded:
        return
    
    # Create excluded identifier view
    if excluded_shapes_by_identifier:
        create_excluded_identifier_view(excluded_shapes_by_identifier, output_dir, platform_info)
    
    # Create exclusion details files
    if excluded_files_details:
        exclusion_files_info = create_exclusion_details_files(
            excluded_files_details, exclusion_patterns, output_dir
        )
        platform_info["exclusion_details_files"] = exclusion_files_info


def track_excluded_file_detail(clf_info, part, exclusion_patterns, heights_processed):
    """
    Create a detail record for an excluded file.
    
    Args:
        clf_info (dict): CLF file information
        part: CLF part object
        exclusion_patterns (list): List of exclusion patterns
        heights_processed (int): Number of heights processed for this file
        
    Returns:
        dict: Excluded file detail record
    """
    excluded_file_detail = {
        "filename": clf_info['name'],
        "folder": clf_info['folder'],
        "full_path": clf_info['path'],
        "num_layers": part.nlayers if hasattr(part, 'nlayers') else 0,
        "matching_patterns": [pattern for pattern in exclusion_patterns if pattern in clf_info['folder']],
        "heights_processed": heights_processed
    }
    return excluded_file_detail
