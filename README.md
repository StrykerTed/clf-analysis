# CLF File Analysis Tool

This tool analyzes and visualizes CLF (Custom Layer Format) files from Arcam EBM machines. It processes manufacturing data layers and generates various visualizations.

## Setup Instructions

### 1. Python Environment Setup

First, ensure you have Python 3.11 installed. Then set up a virtual environment:

```bash
# Deactivate any existing virtual environment
deactivate

# Remove old virtual environment if it exists
rm -rf venv

# Create new virtual environment with Python 3.11
python3.11 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### 2. Install Dependencies

Install the required packages:

```bash
# Install core dependencies
pip install "numpy<2.0.0"
pip install "matplotlib>=3.5.0"
pip install opencv-python
pip install shapely

# Generate requirements.txt for future reference
pip freeze > requirements.txt
```

### 3. Install PyArcam

PyArcam is essential for working with Arcam EBM machine data.

```bash
# If installing from source
python setup.py install
```

## Using PyArcam

PyArcam provides utilities for working with Arcam EBM machines.

### Example 1: Working with CLF Files

```python
from pyarcam.clfutil import CLFFile

# Open and read a CLF file
file = CLFFile("filename.clf")

# Print header content
print(file)

# Load and display first layer as bitmap
file.layer[0].load().show()
```

### Example 2: Layerqam Calibration

```python
from pyarcam.layqam import LayqamFiles, CartesianPoints

# Open Layercam folder
files = LayqamFiles("path/to/layqam/folder")

# Extract calibration points
uvpoints = files.calibration[0].points()

# Set calibration pattern (58 points, 0.003 delta)
xypoints = CartesianPoints(num=58, delta=0.003)

# Calculate transformations
xy2uv = xypoints.polyfit(uvpoints)
uv2xy = uvpoints.polyfit(xypoints)

# Calculate and print RMSE
pixel_rmse = xypoints.transform(xy2uv).rmse(uvpoints)
meter_rmse = uvpoints.transform(uv2xy).rmse(xypoints)
print(f"RMSE in pixels: {pixel_rmse}")
print(f"RMSE in meters: {meter_rmse}")

# Visualize calibration
plt = files.calibration[0].plot()
points = xypoints.transform(xy2uv).round().tolist()
plt.circles(points=points, color=(0, 255, 0), size=5)
plt.show(scale=0.6)
```

## Development Notes

- When installing new packages, remember to update requirements.txt:
  ```bash
  pip freeze > requirements.txt
  ```
- Always activate the virtual environment before working on the project
- Use Python 3.11 for compatibility

## Troubleshooting

If you encounter issues:

1. Ensure you're using Python 3.11
2. Verify the virtual environment is activated
3. Confirm all dependencies are installed
4. Check PyArcam installation

----notes
always activate venv if not active
use python3
check if server is running on port 8080 before running. never use another port
