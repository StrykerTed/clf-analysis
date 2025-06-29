#!/usr/bin/env python3
"""
Quick utility to extract all unique identifiers from a build
"""
import os
import sys

# Add src directory to path
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import setup_paths
from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import find_clf_files, load_exclusion_patterns, should_skip_folder
from config import PROJECT_ROOT

def extract_identifiers_from_build(build_path, exclude_folders=True):
    """Extract all unique identifiers from a build"""
    print(f"Extracting identifiers from: {build_path}")
    
    # Load exclusion patterns
    config_dir = os.path.join(PROJECT_ROOT, "config")
    exclusion_patterns = load_exclusion_patterns(config_dir) if exclude_folders else []
    
    # Find CLF files
    all_clf_files = find_clf_files(build_path)
    print(f"Found {len(all_clf_files)} total CLF files")
    
    # Filter CLF files based on exclusion patterns
    if exclude_folders and exclusion_patterns:
        clf_files = []
        for clf_info in all_clf_files:
            should_skip = should_skip_folder(clf_info['folder'], exclusion_patterns)
            if not should_skip:
                clf_files.append(clf_info)
        print(f"Processing {len(clf_files)} CLF files after exclusions")
    else:
        clf_files = all_clf_files
    
    identifiers = set()
    identifier_details = {}
    
    for clf_info in clf_files:
        try:
            print(f"Processing: {clf_info['name']}")
            part = CLFFile(clf_info['path'])
            
            # Sample a few layers to get identifiers
            if hasattr(part, 'box'):
                heights = [part.box.min[2], (part.box.min[2] + part.box.max[2]) / 2, part.box.max[2]]
                
                for height in heights:
                    try:
                        layer = part.find(height)
                        if layer is not None:
                            shapes = layer.shapes if hasattr(layer, 'shapes') else []
                            
                            for shape in shapes:
                                if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                                    identifier = shape.model.id
                                    identifiers.add(identifier)
                                    
                                    if identifier not in identifier_details:
                                        identifier_details[identifier] = {
                                            'files': set(),
                                            'shape_count': 0
                                        }
                                    
                                    identifier_details[identifier]['files'].add(clf_info['name'])
                                    identifier_details[identifier]['shape_count'] += 1
                    except Exception as e:
                        print(f"  Error processing height {height}: {e}")
                        
        except Exception as e:
            print(f"Error processing {clf_info['name']}: {e}")
    
    return identifiers, identifier_details

if __name__ == "__main__":
    # Test with build 424292
    build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/preprocess build-424292"
    
    if os.path.exists(build_path):
        identifiers, details = extract_identifiers_from_build(build_path)
        
        print(f"\n=== IDENTIFIER ANALYSIS ===")
        print(f"Found {len(identifiers)} unique identifiers:")
        
        for identifier in sorted(identifiers):
            files = details[identifier]['files']
            count = details[identifier]['shape_count']
            print(f"  ID {identifier}: {count} shapes across {len(files)} files")
            for file in sorted(files):
                print(f"    - {file}")
        
        print(f"\nAll identifiers: {sorted(identifiers)}")
    else:
        print(f"Build path not found: {build_path}")
