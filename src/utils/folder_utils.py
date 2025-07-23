# folder_utils.py
"""
Utilities for creating and managing directory structures for CLF analysis
"""
import os
import shutil
import logging


def setup_clf_analysis_directories(build_path, clear_existing=True):
    """
    Set up the standard directory structure for CLF analysis.
    
    Args:
        build_path (str): The main build directory path
        clear_existing (bool): Whether to clear existing clf_analysis folder if it exists
    
    Returns:
        dict: Dictionary containing paths to all created directories
    """
    logger = logging.getLogger(__name__)
    
    # Create clf_analysis subfolder
    clf_analysis_path = os.path.join(build_path, "clf_analysis")
    
    # Clear existing clf_analysis folder if it exists and clear_existing is True
    if clear_existing and os.path.exists(clf_analysis_path):
        try:
            # First attempt: normal rmtree
            shutil.rmtree(clf_analysis_path)
            print(f"Cleared existing clf_analysis folder: {clf_analysis_path}")
            logger.info(f"Cleared existing clf_analysis folder: {clf_analysis_path}")
        except OSError as e:
            if e.errno == 66:  # Directory not empty
                print(f"Warning: Could not remove {clf_analysis_path} - trying forceful removal...")
                logger.warning(f"Could not remove {clf_analysis_path} - trying forceful removal: {e}")
                try:
                    # More aggressive removal - handle read-only files
                    def handle_remove_readonly(func, path, exc):
                        import stat
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    
                    shutil.rmtree(clf_analysis_path, onerror=handle_remove_readonly)
                    print(f"Successfully cleared clf_analysis folder using forceful removal")
                    logger.info(f"Successfully cleared clf_analysis folder using forceful removal")
                except Exception as e2:
                    print(f"Warning: Could not completely clear {clf_analysis_path}: {e2}")
                    print(f"The analysis will continue using the existing directory structure.")
                    print(f"Some old files may remain - results may include data from previous runs.")
                    logger.warning(f"Could not completely clear {clf_analysis_path}: {e2}")
            else:
                print(f"Warning: Could not remove {clf_analysis_path}: {e}")
                print(f"The analysis will continue using the existing directory structure.")
                logger.warning(f"Could not remove {clf_analysis_path}: {e}")
                print(f"Continuing with existing directory structure...")
    
    os.makedirs(clf_analysis_path, exist_ok=True)
    
    # Create subdirectories within clf_analysis
    subdirs = {
        'layer_partials': os.path.join(clf_analysis_path, "layer_partials"),
        'composite_platforms': os.path.join(clf_analysis_path, "composite_platforms"),
        'identifier_views': os.path.join(clf_analysis_path, "identifier_views"),
        'clean_platforms': os.path.join(clf_analysis_path, "clean_platforms"),
        'holes_views': os.path.join(clf_analysis_path, "holes_views")
    }
    
    # Create all subdirectories
    for subdir_name, subdir_path in subdirs.items():
        os.makedirs(subdir_path, exist_ok=True)
    
    # Add main paths to the return dictionary
    result = {
        'clf_analysis': clf_analysis_path,
        'output_dir': clf_analysis_path,  # For backward compatibility
        **subdirs
    }
    
    # Log the creation
    print(f"Created clf_analysis directory: {clf_analysis_path}")
    print(f"Created subdirectories: {', '.join(subdirs.keys())}")
    logger.info(f"Created clf_analysis directory structure at: {clf_analysis_path}")
    
    return result


def setup_build_directory(build_id, main_build_folder="/Users/ted.tedford/Documents/MIDAS"):
    """
    Set up the main build directory for a given build ID.
    
    Args:
        build_id (str): The build identifier
        main_build_folder (str): The base folder for all builds
    
    Returns:
        str: Path to the created build directory
    """
    logger = logging.getLogger(__name__)
    
    build_path = os.path.join(main_build_folder, build_id)
    os.makedirs(build_path, exist_ok=True)
    
    print(f"Created build directory: {build_path}")
    logger.info(f"Created build directory: {build_path}")
    
    return build_path


def create_directory_structure(build_id, main_build_folder="/Users/ted.tedford/Documents/MIDAS", clear_existing=True):
    """
    Create the complete directory structure for CLF analysis.
    This combines build directory setup and clf_analysis directory setup.
    
    Args:
        build_id (str): The build identifier
        main_build_folder (str): The base folder for all builds
        clear_existing (bool): Whether to clear existing clf_analysis folder if it exists
    
    Returns:
        dict: Dictionary containing all created directory paths
    """
    # Set up main build directory
    build_path = setup_build_directory(build_id, main_build_folder)
    
    # Set up clf_analysis subdirectory structure
    directories = setup_clf_analysis_directories(build_path, clear_existing)
    
    # Add build_path to the result
    directories['build_path'] = build_path
    
    return directories


def ensure_directory_exists(directory_path, description=None):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path (str): Path to the directory
        description (str): Optional description for logging
    
    Returns:
        str: The directory path (for chaining)
    """
    logger = logging.getLogger(__name__)
    
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        msg = f"Created directory: {directory_path}"
        if description:
            msg += f" ({description})"
        print(msg)
        logger.info(msg)
    
    return directory_path


def get_subdirectory_path(base_path, subdirectory_name):
    """
    Get the path to a subdirectory within a base path.
    Creates the subdirectory if it doesn't exist.
    
    Args:
        base_path (str): The base directory path
        subdirectory_name (str): Name of the subdirectory
    
    Returns:
        str: Full path to the subdirectory
    """
    subdir_path = os.path.join(base_path, subdirectory_name)
    return ensure_directory_exists(subdir_path, f"{subdirectory_name} subdirectory")
