import os
import sys

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Add src directory to Python path
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add utils directory to Python path
utils_path = os.path.join(src_path, 'utils')
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)