#!/usr/bin/env python3
"""
Test script for identifier filtering functionality
Tests the complete identifier filtering workflow
"""

import os
import sys

# Add src directory to path
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Add current directory to path
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add web_app directory to path
web_app_dir = os.path.join(current_dir, 'web_app')
if web_app_dir not in sys.path:
    sys.path.insert(0, web_app_dir)

from web_app.clf_analysis_wrapper import analyze_build_for_web

def test_identifier_filtering():
    """Test the identifier filtering functionality"""
    
    # Test build path
    test_build_path = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_contents/build-431627"
    test_height = 135.8
    
    print("=" * 60)
    print("TESTING IDENTIFIER FILTERING FUNCTIONALITY")
    print("=" * 60)
    
    if not os.path.exists(test_build_path):
        print(f"❌ Test build not found: {test_build_path}")
        return False
    
    print(f"✅ Test build found: {test_build_path}")
    print(f"📏 Test height: {test_height}mm")
    
    # Test 1: No identifier filter (all shapes)
    print("\n🔍 Test 1: No identifier filter (all shapes)")
    print("-" * 40)
    
    try:
        results_all = analyze_build_for_web(
            build_folder_path=test_build_path,
            height_mm=test_height,
            exclude_folders=True,
            identifiers=None
        )
        
        if "error" in results_all:
            print(f"❌ Analysis failed: {results_all['error']}")
            return False
        
        print(f"✅ Analysis successful!")
        print(f"📊 Files processed: {results_all.get('files_processed', 0)}")
        print(f"📊 Files excluded: {results_all.get('files_excluded', 0)}")
        
        if "clean_platform" in results_all.get('visualizations', {}):
            print("🎨 Visualization generated successfully")
        else:
            print("⚠️  No visualization generated")
        
        # Cleanup
        try:
            from web_app.clf_analysis_wrapper import CLFWebAnalyzer
            analyzer = CLFWebAnalyzer()
            analyzer.cleanup_temp_files(results_all.get("temp_directory", ""))
            print("🧹 Cleaned up temporary files")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
            
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False
    
    # Test 2: With identifier filter
    print("\n🔍 Test 2: With identifier filter ['1', '2']")
    print("-" * 40)
    
    try:
        results_filtered = analyze_build_for_web(
            build_folder_path=test_build_path,
            height_mm=test_height,
            exclude_folders=True,
            identifiers=['1', '2']
        )
        
        if "error" in results_filtered:
            print(f"❌ Analysis failed: {results_filtered['error']}")
            return False
        
        print(f"✅ Filtered analysis successful!")
        print(f"📊 Files processed: {results_filtered.get('files_processed', 0)}")
        print(f"📊 Files excluded: {results_filtered.get('files_excluded', 0)}")
        
        if "clean_platform" in results_filtered.get('visualizations', {}):
            print("🎨 Filtered visualization generated successfully")
            # Check if filename includes identifier info
            viz_info = results_filtered['visualizations']['clean_platform']
            filename = viz_info.get('filename', '')
            if 'filtered' in filename:
                print(f"✅ Filename includes filter info: {filename}")
            else:
                print(f"⚠️  Filename doesn't show filter: {filename}")
        else:
            print("⚠️  No filtered visualization generated")
        
        # Cleanup
        try:
            from web_app.clf_analysis_wrapper import CLFWebAnalyzer
            analyzer = CLFWebAnalyzer()
            analyzer.cleanup_temp_files(results_filtered.get("temp_directory", ""))
            print("🧹 Cleaned up temporary files")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
            
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 IDENTIFIER FILTERING TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_identifier_filtering()
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
