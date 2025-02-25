import os
import shutil
import zipfile


def cleanup_abp_folder(folder_path):
    """
    Cleans up the extracted ABP folder when processing is complete.
    
    Args:
        folder_path (str): Path to the extracted folder
    """
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            print(f"Cleaned up folder: {folder_path}")
    except Exception as e:
        print(f"Warning: Could not clean up folder {folder_path}: {str(e)}")