import os
import logging

logger = logging.getLogger(__name__)

def get_project_paths():
    """Get the directory paths for the project structure"""
    # Get the directory paths
    script_dir = os.path.dirname(os.path.abspath(__file__))     # gets current directory
    src_dir = os.path.dirname(os.path.dirname(script_dir))      # gets /src directory
    project_root = os.path.dirname(src_dir)                     # gets project root
    config_dir = os.path.join(src_dir, 'config')                # gets /src/config
    
    paths = {
        "script_dir": script_dir,
        "src_dir": src_dir,
        "project_root": project_root,
        "config_dir": config_dir
    }
    
    logger.info(f"Project paths: {paths}")
    return paths


def setup_directories(output_dir, save_layer_partials=False, save_clean=True):
    """Set up all required output directories"""
    # Create root output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create subdirectories based on configuration
    if save_layer_partials:
        os.makedirs(os.path.join(output_dir, "layer_partials"), exist_ok=True)
    
    if save_clean:
        os.makedirs(os.path.join(output_dir, "clean_platforms"), exist_ok=True)
    
    # Always create these directories
    os.makedirs(os.path.join(output_dir, "composite_platforms"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "identifier_views"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "non_identifier_views"), exist_ok=True)
    
    logger.info(f"Created output directories in {output_dir}")
    return output_dir