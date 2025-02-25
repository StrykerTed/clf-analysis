# file_handlers.py 
import os
import sys
import shutil
import zipfile
import json
from typing import List, Dict, Optional


def setup_abp_folders(abp_path: Optional[str] = None) -> str:
    """
    Set up the necessary folder structure and handle ABP file extraction.
    
    Args:
        abp_path (str, optional): Full path to the .abp file. If not provided, will prompt user.
    
    Returns:
        str: Path to the extracted contents directory
    
    Raises:
        FileNotFoundError: If the specified .abp file doesn't exist
        Exception: If there's an error during extraction
    """
    if not abp_path:
        # Prompt user for ABP file path
        abp_path = input("Please enter the full path to your .abp file: ").strip()
        
        # Handle quotes if user copied path from file explorer
        abp_path = abp_path.strip('"').strip("'")
    
    # Validate the provided path
    if not os.path.exists(abp_path):
        raise FileNotFoundError(f"ABP file not found at: {abp_path}")
    
    if not abp_path.lower().endswith('.abp'):
        raise ValueError("Provided file is not an .abp file")
    
    # Get the project root directory (2 levels up from the script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    
    # Define contents directory relative to project root
    contents_dir = os.path.join(project_root, 'abp_contents')
    
    # Create contents directory if it doesn't exist
    os.makedirs(contents_dir, exist_ok=True)
    
    print(f"Using ABP file: {abp_path}")
    
    # Create folder name from ABP file (without extension)
    folder_name = os.path.splitext(os.path.basename(abp_path))[0]
    extract_dir = os.path.join(contents_dir, folder_name)
    
    # Remove existing extracted directory if it exists
    if os.path.exists(extract_dir):
        print(f"Removing existing extracted directory: {extract_dir}")
        shutil.rmtree(extract_dir)
    
    os.makedirs(extract_dir, exist_ok=True)
    
    # Extract files, properly maintaining folder structure
    try:
        print(f"Extracting {os.path.basename(abp_path)} to {extract_dir}")
        with zipfile.ZipFile(abp_path, 'r') as zip_ref:
            for info in zip_ref.infolist():
                # Skip XML files
                if info.filename.lower().endswith('.xml'):
                    continue
                # Convert Windows-style backslashes to forward slashes
                fixed_name = info.filename.replace("\\", "/")
                # Build the target path using proper OS-specific separators
                target_path = os.path.join(extract_dir, *fixed_name.split("/"))
                target_dir = os.path.dirname(target_path)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                with zip_ref.open(info) as source, open(target_path, "wb") as target:
                    shutil.copyfileobj(source, target)
        print(f"Successfully extracted {os.path.basename(abp_path)} with proper folder structure")
    except Exception as e:
        raise Exception(f"Error extracting ABP file: {str(e)}")
    
    return extract_dir