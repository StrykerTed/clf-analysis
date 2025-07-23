# test_folder_utils.py
"""
Simple test to verify the folder_utils functions work correctly
"""
import os
import sys
import tempfile
import shutil

# Add the src directory to the path to find our utils
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(script_dir), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from utils.folder_utils import (
    setup_clf_analysis_directories,
    setup_build_directory,
    create_directory_structure,
    ensure_directory_exists,
    get_subdirectory_path
)

def test_folder_utils():
    """Test the folder utility functions"""
    print("Testing folder_utils.py functions...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Test setup_build_directory
        build_path = setup_build_directory("test_build_123", temp_dir)
        assert os.path.exists(build_path), "Build directory should exist"
        print("✓ setup_build_directory works")
        
        # Test setup_clf_analysis_directories
        directories = setup_clf_analysis_directories(build_path)
        expected_dirs = ['clf_analysis', 'layer_partials', 'composite_platforms', 
                        'identifier_views', 'clean_platforms', 'holes_views']
        
        for dir_name in expected_dirs:
            assert dir_name in directories, f"Directory {dir_name} should be in result"
            assert os.path.exists(directories[dir_name]), f"Directory {dir_name} should exist"
        print("✓ setup_clf_analysis_directories works")
        
        # Test create_directory_structure
        full_dirs = create_directory_structure("test_build_456", temp_dir)
        assert 'build_path' in full_dirs, "build_path should be in result"
        assert 'clf_analysis' in full_dirs, "clf_analysis should be in result"
        print("✓ create_directory_structure works")
        
        # Test ensure_directory_exists
        test_dir = os.path.join(temp_dir, "test_ensure")
        ensure_directory_exists(test_dir)
        assert os.path.exists(test_dir), "Ensured directory should exist"
        print("✓ ensure_directory_exists works")
        
        # Test get_subdirectory_path
        sub_path = get_subdirectory_path(temp_dir, "test_subdir")
        assert os.path.exists(sub_path), "Subdirectory should be created"
        print("✓ get_subdirectory_path works")
        
        print("\n✅ All folder_utils tests passed!")

if __name__ == "__main__":
    test_folder_utils()
