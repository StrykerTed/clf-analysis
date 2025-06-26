# CLF Analysis Tool

A Python toolkit for analyzing and visualizing CLF (Custom Layer Format) files from Arcam EBM additive manufacturing machines.

## 🚀 Features

- **CLF File Processing**: Complete parsing and analysis of Arcam EBM layer data
- **PyArcam Integration**: Built-in utilities for working with Arcam machine data
- **Shapely Analysis**: Advanced geometric analysis of platform paths and shapes
- **Multiprocessing Support**: Optimized for large-scale data processing
- **Layerqam Calibration**: Camera calibration and coordinate transformation
- **Visualization Tools**: Rich plotting and analysis visualization

## 📦 Installation

1. **Clone or navigate to the project directory**

   ```bash
   cd clf_analysis_clean
   ```

2. **Create a virtual environment**

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install the package**
   ```bash
   python setup.py install
   ```

## 🏃 Quick Start

### Run Platform Analysis Tool

```bash
python src/tools/get_platform_paths_shapes_shapely.py
```

### Run Example Script

```bash
python examples/example_clf.py
```

### Run Tests

```bash
python -m unittest discover src/tools/tests
```

## 🔌 Usage Examples

### Working with CLF Files

```python
from pyarcam.clfutil import CLFFile

# Open and read a CLF file
file = CLFFile("filename.clf")

# Print header content
print(file)

# Load and display first layer as bitmap
file.layer[0].load().show()
```

### Layerqam Calibration Analysis

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

# Calculate RMSE metrics
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

## 🏗️ Project Structure

```
clf_analysis_clean/
├── src/
│   ├── tools/               # Standalone analysis tools
│   │   ├── get_platform_paths_shapes_shapely.py
│   │   └── tests/          # Unit tests
│   └── utils/              # Core utilities
│       ├── myfuncs/        # General utility functions
│       ├── platform_analysis/  # Platform analysis modules
│       └── pyarcam/        # CLF and Arcam EBM data handling
├── examples/               # Sample usage scripts
├── requirements.txt        # Python dependencies
├── setup.py               # Package installation
├── CLAUDE.md              # Development guidelines
└── README.md              # This file
```

## ⚡ Performance Features

- **Multiprocessing**: CPU-bound tasks utilize all available cores
- **Shapely Integration**: Efficient geometric operations
- **Optimized Data Structures**: Memory-efficient processing of large CLF files
- **Batch Processing**: Handle multiple files simultaneously

## 🔧 Configuration

### Environment Variables

- **Python Version**: Requires Python 3.11 for compatibility
- **Virtual Environment**: Always activate venv before development
- **Port Management**: Default development port is 8080

### Code Style Guidelines

- Standard library imports first, then third-party, then local modules
- Module-level logging with `logger = logging.getLogger(__name__)`
- Snake_case for functions/variables, CamelCase for classes
- Type hints encouraged for better code documentation

## 🚧 Development Status

- ✅ **CLF file parsing and analysis**
- ✅ **PyArcam integration with full utilities**
- ✅ **Shapely-based geometric analysis**
- ✅ **Multiprocessing optimization**
- ✅ **Comprehensive logging and error handling**
- ✅ **Unit testing framework**
- 🚧 **Advanced visualization features**
- 🚧 **Web interface for analysis results**

## 🔮 Future Enhancements

1. **Advanced Analytics**

   - Machine learning integration for pattern recognition
   - Predictive analysis for build quality
   - Statistical analysis of manufacturing parameters

2. **Visualization Improvements**

   - Interactive 3D visualization
   - Real-time analysis dashboards
   - Export capabilities for reports

3. **Integration Features**
   - CAD software integration
   - Cloud-based processing
   - API endpoints for external tools

## 🛠️ Development

### Adding New Analysis Tools

1. Create new tool in `src/tools/` directory
2. Follow existing code patterns and logging practices
3. Add corresponding tests in `src/tools/tests/`
4. Update documentation

### Performance Optimization

The toolkit uses multiprocessing for CPU-intensive tasks:

```python
from multiprocessing import Pool

num_processes = min(os.cpu_count(), len(tasks))

with Pool(processes=num_processes) as pool:
    results = pool.map(process_item, items)
```

## 📝 Logging

- Console output for development
- Module-level loggers with `logging.getLogger(__name__)`
- Error handling with specific exceptions
- JSON serialization compatibility for numpy data types

## 🔒 Data Handling

- Secure processing of proprietary CLF files
- Memory-efficient handling of large datasets
- Proper cleanup of temporary files
- Type conversion for JSON serialization compatibility

## 🤝 Contributing

Key areas for contribution:

1. Advanced geometric analysis algorithms
2. Performance optimization
3. Visualization enhancements
4. Additional file format support
5. Machine learning integration

---

## Notes

- Always activate venv if not active
- Use python3
- Check if server is running on port 8080 before running. Never use another port
