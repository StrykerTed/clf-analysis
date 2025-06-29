#!/usr/bin/env python3
"""
Quick test to find actual identifiers and test filtering
"""

import os
import sys

# Add paths
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

web_app_dir = os.path.join(current_dir, 'web_app')
if web_app_dir not in sys.path:
    sys.path.insert(0, web_app_dir)

import setup_paths
from utils.pyarcam.clfutil import CLFFile
from utils.myfuncs.file_utils import find_clf_files, load_exclusion_patterns, should_skip_folder

def find_identifiers_in_build(build_path, max_files=5):
    """Find some actual identifiers in a build"""
    print(f"Looking for identifiers in: {build_path}")
    
    # Load exclusion patterns
    config_dir = os.path.join(os.path.dirname(__file__), "config")
    exclusion_patterns = []
    try:
        exclusion_patterns = load_exclusion_patterns(config_dir)
    except:
        pass
    
    # Find CLF files
    all_clf_files = find_clf_files(build_path)
    
    # Filter out excluded files
    clf_files = []
    for clf_info in all_clf_files:
        if not should_skip_folder(clf_info['folder'], exclusion_patterns):
            clf_files.append(clf_info)
        if len(clf_files) >= max_files:
            break
    
    print(f"Checking {len(clf_files)} files for identifiers...")
    
    identifiers_found = set()
    
    for clf_info in clf_files:
        try:
            part = CLFFile(clf_info['path'])
            if hasattr(part, 'box'):
                # Try a few different heights
                for height in [1.0, 2.0, 5.0, 10.0]:
                    layer = part.find(height)
                    if layer and hasattr(layer, 'shapes'):
                        for shape in layer.shapes:
                            if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                                identifier = str(shape.model.id).strip()
                                if identifier:
                                    identifiers_found.add(identifier)
                                    print(f"Found identifier '{identifier}' at height {height}mm in {clf_info['name']}")
                                    if len(identifiers_found) >= 5:
                                        break
                        if len(identifiers_found) >= 5:
                            break
                    if len(identifiers_found) >= 5:
                        break
                        
        except Exception as e:
            print(f"Error reading {clf_info['name']}: {e}")
        
        if len(identifiers_found) >= 5:
            break
    
    return list(identifiers_found)

def test_with_real_identifiers():
    """Test filtering with actual identifiers"""
    build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/build-431627"
    
    print("=" * 60)
    print("FINDING REAL IDENTIFIERS FOR TESTING")
    print("=" * 60)
    
    # Find some real identifiers
    identifiers = find_identifiers_in_build(build_path)
    
    if not identifiers:
        print("❌ No identifiers found in build!")
        return False
        
    print(f"\n🔍 Found identifiers: {identifiers}")
    
    # Test with a real identifier
    test_id = identifiers[0]
    print(f"\n🧪 Testing filtering with identifier: '{test_id}'")
    
    from web_app.clf_analysis_wrapper import analyze_build_for_web
    
    results = analyze_build_for_web(
        build_folder_path=build_path,
        height_mm=2.0,  # Try a higher layer
        exclude_folders=True,
        identifiers=[test_id]
    )
    
    if "error" in results:
        print(f"❌ Analysis failed: {results['error']}")
        return False
    
    print(f"✅ Analysis successful!")
    print(f"📊 Files processed: {results.get('files_processed', 0)}")
    
    if "clean_platform" in results.get('visualizations', {}):
        viz_info = results['visualizations']['clean_platform']
        filename = viz_info.get('filename', '')
        print(f"🎨 Generated filtered visualization: {filename}")
        
        if 'filtered' in filename:
            print("✅ Filename correctly shows filtering!")
        else:
            print("⚠️  Filename doesn't show filtering")
    else:
        print("⚠️  No visualization generated")
    
    # Cleanup
    try:
        from web_app.clf_analysis_wrapper import CLFWebAnalyzer
        analyzer = CLFWebAnalyzer()
        analyzer.cleanup_temp_files(results.get("temp_directory", ""))
    except Exception as e:
        pass
    
    return True

if __name__ == "__main__":
    test_with_real_identifiers()
