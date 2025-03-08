"""
Configuration settings for the project.
Contains paths, parameters, and other constants.
"""
import os

# Path configurations
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MY_OUTPUTS = os.path.join(os.path.dirname(PROJECT_ROOT), "my_outputs")

# Light spot detection parameters
LIGHT_SPOT_PARAMETERS = {
    'window_size': 11,
    'threshold_factor': 1.8,
    'min_spot_area': 15,
    'max_spot_area': 120,
    'clip_limit': 3.0,
    'tile_grid_size': (8, 8)
}