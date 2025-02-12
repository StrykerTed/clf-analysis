import os
import shutil
import zipfile

def setup_abp_processing(abp_filename):
    """
    Sets up the processing environment for an ABP file.
    1. Creates abp_files_unzipped directory if it doesn't exist
    2. Creates a specific folder for this ABP file
    3. Extracts ABP contents to that folder
    
    Args:
        abp_filename (str): Name of the ABP file (e.g., "preprocess build-271360.abp")
        
    Returns:
        str: Path to the extracted folder
    """
    # Get base directory
    base_dir = os.getcwd()
    
    # Setup main unzip directory
    unzip_base = os.path.join(base_dir, "abp_files_unzipped")
    os.makedirs(unzip_base, exist_ok=True)
    
    # Create folder name from ABP filename (remove .abp extension)
    folder_name = os.path.splitext(abp_filename)[0]
    extract_path = os.path.join(unzip_base, folder_name)
    
    # If folder exists, remove it to ensure clean state
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    
    # Create fresh folder
    os.makedirs(extract_path)
    
    # Full path to ABP file
    abp_path = os.path.join(base_dir, abp_filename)
    
    # Extract ABP contents
    if not os.path.exists(abp_path):
        raise FileNotFoundError(f"ABP file not found: {abp_path}")
        
    try:
        with zipfile.ZipFile(abp_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print(f"Successfully extracted {abp_filename} to {extract_path}")
    except zipfile.BadZipFile:
        raise ValueError(f"The file {abp_filename} is not a valid zip/ABP file")
    except Exception as e:
        raise Exception(f"Error extracting {abp_filename}: {str(e)}")
        
    return extract_path

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