import os
from pyarcam.clfutil import CLFFile
import numpy as np

def summarize_points(points):
    """Create a concise summary of points data"""
    if not isinstance(points, list) or not points:
        return "No points"
        
    point_arrays = []
    for point_array in points:
        if isinstance(point_array, np.ndarray):
            summary = {
                'shape': point_array.shape,
                'first': point_array[0] if len(point_array) > 0 else None,
                'last': point_array[-1] if len(point_array) > 0 else None,
                'is_closed': np.allclose(point_array[0], point_array[-1], rtol=1e-5, atol=1e-8) if len(point_array) > 2 else False
            }
            point_arrays.append(summary)
    
    return point_arrays

def inspect_shape_concise(shape, prefix=""):
    """Concise shape inspection"""
    shape_info = {
        'type': type(shape).__name__,
        'attributes': {}
    }
    
    # Get interesting attributes (excluding methods and private attributes)
    attributes = [attr for attr in dir(shape) 
                 if not attr.startswith('__') and 
                 not callable(getattr(shape, attr))]
    
    for attr in attributes:
        try:
            value = getattr(shape, attr)
            
            # Special handling for points
            if attr == 'points':
                shape_info['points_summary'] = summarize_points(value)
                continue
                
            # Special handling for model
            if attr == 'model' and value is not None:
                model_info = {
                    'id': getattr(value, 'id', None),
                    'name': getattr(value, 'name', None),
                    'thickness': getattr(value, 'thickness', None)
                }
                if hasattr(value, 'box'):
                    model_info['bounds'] = {
                        'x': [float(value.box.min[0]), float(value.box.max[0])],
                        'y': [float(value.box.min[1]), float(value.box.max[1])],
                        'z': [float(value.box.min[2]), float(value.box.max[2])]
                    }
                shape_info['model'] = model_info
                continue
                
            # Store other attributes directly
            shape_info['attributes'][attr] = value
            
        except Exception as e:
            shape_info['attributes'][attr] = f"Error: {str(e)}"
    
    return shape_info

def analyze_layer_summary(clf_file, height):
    """Analyze a layer and provide a concise summary"""
    layer = clf_file.find(height)
    if layer is None:
        return None
        
    layer_summary = {
        'height': height,
        'num_shapes': len(layer.shapes) if hasattr(layer, 'shapes') else 0,
        'shapes': []
    }
    
    if hasattr(layer, 'shapes'):
        for shape in layer.shapes:
            shape_info = inspect_shape_concise(shape)
            layer_summary['shapes'].append(shape_info)
    
    return layer_summary

def print_layer_summary(layer_summary):
    """Print layer summary in a readable format"""
    if not layer_summary:
        print("No layer data")
        return
        
    print(f"\nLayer at height {layer_summary['height']}mm")
    print(f"Number of shapes: {layer_summary['num_shapes']}")
    
    for i, shape in enumerate(layer_summary['shapes']):
        print(f"\nShape {i}:")
        print(f"  Type: {shape['type']}")
        
        if 'model' in shape:
            model = shape['model']
            print(f"  Model:")
            print(f"    ID: {model['id']}")
            print(f"    Name: {model['name']}")
            if 'bounds' in model:
                b = model['bounds']
                print(f"    Bounds: X[{b['x'][0]:.2f}, {b['x'][1]:.2f}] "
                      f"Y[{b['y'][0]:.2f}, {b['y'][1]:.2f}] "
                      f"Z[{b['z'][0]:.2f}, {b['z'][1]:.2f}]")
        
        if 'points_summary' in shape:
            for j, points in enumerate(shape['points_summary']):
                print(f"  Points array {j}:")
                print(f"    Shape: {points['shape']}")
                print(f"    Closed: {points['is_closed']}")

def main():
    try:
        # Specific subfolder we want to analyze
        subfolder = "Cylinder"
        
        # Find the build directory
        base_dir = os.getcwd()
        build_dir = os.path.join(base_dir, "preprocess build-270851.abp")
        models_dir = os.path.join(build_dir, "Models", subfolder)
        
        print(f"Looking in: {models_dir}")
        if not os.path.exists(models_dir):
            print("Directory not found!")
            return
            
        # Find CLF files
        clf_files = [f for f in os.listdir(models_dir) if f.endswith('.clf')]
        print(f"Found {len(clf_files)} CLF files")
        
        # Process each file
        for filename in clf_files:
            filepath = os.path.join(models_dir, filename)
            print(f"\nAnalyzing: {filename}")
            
            part = CLFFile(filepath)
            if hasattr(part, 'box'):
                min_height = part.box.min[2]
                max_height = part.box.max[2]
                
                print(f"File bounds: Z range {min_height:.3f}mm to {max_height:.3f}mm")
                print(f"Number of layers: {part.nlayers}")
                
                # Analyze at different heights
                heights = [min_height, (min_height + max_height) / 2, max_height]
                for height in heights:
                    summary = analyze_layer_summary(part, height)
                    print_layer_summary(summary)
            else:
                print("No box attribute found in CLF file")
                
    except Exception as e:
        print(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    main()