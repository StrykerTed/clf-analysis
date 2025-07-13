#!/usr/bin/env python3
"""
Test script to verify the improved height sampling works correctly.
This script will show the height ranges and samples that would be used.
"""

import os
import sys
import numpy as np

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from utils.pyarcam.clfutil import CLFFile
except ImportError as e:
    print(f"Error importing CLFFile: {e}")
    print("Make sure you're running this from the root directory")
    sys.exit(1)

def test_height_sampling(build_id):
    """Test the height sampling logic without running the full analysis"""
    
    print(f"=== Testing Height Sampling for Build {build_id} ===\n")
    
    # Set up paths
    folder_name = f"preprocess build-{build_id}"
    build_path = os.path.join("abp_contents", folder_name)
    
    if not os.path.exists(build_path):
        print(f"Error: Build folder not found: {build_path}")
        return
    
    print(f"Scanning: {build_path}")
    
    # Find all CLF files
    clf_files = []
    for root, dirs, files in os.walk(build_path):
        for file in files:
            if file.endswith('.clf'):
                file_path = os.path.join(root, file)
                folder_name = os.path.relpath(root, build_path)
                clf_files.append({
                    'name': file,
                    'path': file_path,
                    'folder': folder_name
                })
    
    print(f"Found {len(clf_files)} CLF files\n")
    
    if not clf_files:
        print("No CLF files found!")
        return
    
    # Determine global height range
    global_min_height = float('inf')
    global_max_height = float('-inf')
    file_ranges = []
    
    print("File height ranges:")
    for clf_info in clf_files:
        try:
            part = CLFFile(clf_info['path'])
            if hasattr(part, 'box'):
                file_min = float(part.box.min[2])
                file_max = float(part.box.max[2])
                
                global_min_height = min(global_min_height, file_min)
                global_max_height = max(global_max_height, file_max)
                
                file_ranges.append({
                    'file': f"{clf_info['folder']}/{clf_info['name']}",
                    'min': file_min,
                    'max': file_max
                })
                
                print(f"  {clf_info['folder']}/{clf_info['name']:15s}: {file_min:7.2f} to {file_max:7.2f} mm")
        except Exception as e:
            print(f"  Error reading {clf_info['name']}: {e}")
    
    if global_min_height == float('inf'):
        print("No valid height data found!")
        return
    
    # Apply padding
    height_padding = (global_max_height - global_min_height) * 0.05
    padded_min = max(0, global_min_height - height_padding)
    padded_max = global_max_height + height_padding
    
    print(f"\nGlobal height analysis:")
    print(f"  Original range: {global_min_height:.2f} to {global_max_height:.2f} mm")
    print(f"  Padding added:  {height_padding:.2f} mm (5%)")
    print(f"  Final range:    {padded_min:.2f} to {padded_max:.2f} mm")
    
    # Generate height samples
    num_samples = 15
    heights = np.linspace(padded_min, padded_max, num_samples)
    
    print(f"\nHeight samples ({num_samples} points):")
    for i, h in enumerate(heights):
        print(f"  {i+1:2d}: {h:8.2f} mm")
    
    # Show which files will be processed at which heights
    print(f"\nFile processing analysis:")
    tolerance = 0.1
    
    for file_range in file_ranges:
        valid_heights = []
        for h in heights:
            if (h >= file_range['min'] - tolerance and 
                h <= file_range['max'] + tolerance):
                valid_heights.append(h)
        
        print(f"  {file_range['file']:40s}: {len(valid_heights):2d} heights")
        if len(valid_heights) < 5:  # Show heights for files with few samples
            height_str = ", ".join(f"{h:.1f}" for h in valid_heights)
            print(f"    Heights: {height_str}")
    
    print(f"\n=== Test Complete ===")

if __name__ == "__main__":
    # Test with a specific build ID
    test_build_id = input("Enter build ID to test (e.g., 271360): ").strip()
    if test_build_id:
        test_height_sampling(test_build_id)
    else:
        print("No build ID provided")
