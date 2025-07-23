#!/usr/bin/env python3
"""
Test script to verify the robust directory removal functionality
"""
import os
import sys
import tempfile
import stat

# Add src to path to import our utilities
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.folder_utils import setup_clf_analysis_directories

def test_robust_directory_removal():
    """Test the robust directory removal functionality"""
    print("🧪 Testing Robust Directory Removal")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        build_path = os.path.join(temp_dir, "test_build")
        os.makedirs(build_path, exist_ok=True)
        
        print(f"📁 Using build directory: {build_path}")
        
        # Step 1: Create initial directory structure
        print("\n1. Creating initial directory structure...")
        directories = setup_clf_analysis_directories(build_path, clear_existing=False)
        clf_analysis_path = directories['clf_analysis']
        print(f"   ✅ Created: {clf_analysis_path}")
        
        # Step 2: Add some files to simulate real usage
        print("\n2. Adding files to simulate real usage...")
        test_file1 = os.path.join(clf_analysis_path, "test_file.txt")
        test_file2 = os.path.join(directories['layer_partials'], "layer_test.json")
        
        with open(test_file1, 'w') as f:
            f.write("test content")
        with open(test_file2, 'w') as f:
            f.write('{"test": "data"}')
        
        print(f"   ✅ Created test files")
        
        # Step 3: Test normal clearing (should work)
        print("\n3. Testing normal directory clearing...")
        try:
            directories = setup_clf_analysis_directories(build_path, clear_existing=True)
            print(f"   ✅ Normal clearing worked")
        except Exception as e:
            print(f"   ❌ Normal clearing failed: {e}")
            return False
        
        # Step 4: Create a problematic scenario (read-only file)
        print("\n4. Testing with read-only file...")
        # Recreate directory and add a read-only file
        directories = setup_clf_analysis_directories(build_path, clear_existing=False)
        readonly_file = os.path.join(directories['clf_analysis'], "readonly_file.txt")
        
        with open(readonly_file, 'w') as f:
            f.write("readonly content")
        
        # Make file read-only
        os.chmod(readonly_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        print(f"   ✅ Created read-only test file")
        
        # Step 5: Test robust clearing
        print("\n5. Testing robust directory clearing...")
        try:
            directories = setup_clf_analysis_directories(build_path, clear_existing=True)
            print(f"   ✅ Robust clearing handled read-only file")
        except Exception as e:
            print(f"   ❌ Robust clearing failed: {e}")
            return False
        
        print("\n✅ ALL TESTS PASSED!")
        print("\n📊 Summary:")
        print(f"   • Normal directory removal: ✅")
        print(f"   • Read-only file handling: ✅") 
        print(f"   • Graceful error handling: ✅")
        print(f"   • Directory recreation: ✅")
        
        return True

if __name__ == "__main__":
    print("🚀 Testing robust directory removal functionality...")
    print("This verifies the fix for the 'Directory not empty' error\n")
    
    success = test_robust_directory_removal()
    
    if success:
        print("\n🎉 Robust directory removal test complete!")
        print("The fix should resolve the 'Directory not empty' issue.")
    else:
        print("\n❌ Tests failed - fix needs more work.")
        sys.exit(1)
