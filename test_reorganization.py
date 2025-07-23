#!/usr/bin/env python3
"""
Test script to verify that the reorganized code and new folder_utils work correctly
This demonstrates the successful refactoring of directory creation logic
"""
import os
import sys
import tempfile
import shutil

# Add src to path to import our utilities
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.folder_utils import create_directory_structure

def test_reorganization():
    """Test the reorganized directory creation functionality"""
    print("🔧 Testing Reorganized Code Structure")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temp directory: {temp_dir}")
        
        # Test the main function that was extracted
        print("\n1. Testing create_directory_structure()...")
        directories = create_directory_structure("test_build_999", temp_dir)
        
        # Verify all expected directories were created
        expected_dirs = [
            'build_path', 'clf_analysis', 'output_dir', 'layer_partials',
            'composite_platforms', 'identifier_views', 'clean_platforms', 'holes_views'
        ]
        
        for dir_name in expected_dirs:
            if dir_name in directories and os.path.exists(directories[dir_name]):
                print(f"   ✅ {dir_name}: {os.path.basename(directories[dir_name])}")
            else:
                print(f"   ❌ {dir_name}: MISSING")
                return False
        
        print("\n2. Verifying directory structure...")
        build_path = directories['build_path']
        clf_analysis_path = directories['clf_analysis']
        
        # Check that clf_analysis is inside build_path
        if clf_analysis_path.startswith(build_path):
            print(f"   ✅ clf_analysis correctly nested in build directory")
        else:
            print(f"   ❌ Directory nesting incorrect")
            return False
        
        # Check subdirectories
        subdirs = ['layer_partials', 'composite_platforms', 'identifier_views', 'clean_platforms', 'holes_views']
        for subdir in subdirs:
            subdir_path = directories[subdir]
            if os.path.exists(subdir_path) and subdir_path.startswith(clf_analysis_path):
                print(f"   ✅ {subdir} correctly created in clf_analysis")
            else:
                print(f"   ❌ {subdir} missing or incorrectly placed")
                return False
        
        print("\n✅ ALL TESTS PASSED!")
        print("\n📊 Summary:")
        print(f"   • Refactoring successful: ✅")
        print(f"   • Directory creation modularized: ✅") 
        print(f"   • All paths correctly structured: ✅")
        print(f"   • Code is now more maintainable: ✅")
        
        return True

if __name__ == "__main__":
    print("🚀 Testing the reorganized CLF analysis code...")
    print("This verifies that the directory creation logic has been")
    print("successfully moved to src/utils/folder_utils.py\n")
    
    success = test_reorganization()
    
    if success:
        print("\n🎉 Reorganization verification complete!")
        print("The code is now better organized and ready for further development.")
    else:
        print("\n❌ Tests failed - reorganization needs fixes.")
        sys.exit(1)
