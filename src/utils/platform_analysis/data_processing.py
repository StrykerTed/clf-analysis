import os
import numpy as np
import matplotlib.pyplot as plt

from utils.myfuncs.shape_things import should_close_path
from utils.myfuncs.plotTools import (
    setup_platform_figure,
    draw_platform_boundary,
    add_reference_lines,
    draw_shape,
    set_platform_limits,
    save_platform_figure
)


def analyze_layer(clf_file, height, output_dir, clf_info, path_counts, shape_types, 
               file_identifier_counts, shapes_by_identifier, draw_points=True, 
               draw_lines=True, save_layer_partials=True):
    """Analyze a specific layer and generate visualization with path closure"""
    try:
        layer = clf_file.find(height)
        if layer is None:
            return f"No layer found at height {height}"
        
        # Initialize all the tracking variables
        x_min, x_max = float('inf'), float('-inf')
        y_min, y_max = float('inf'), float('-inf')
        shapes = layer.shapes if hasattr(layer, 'shapes') else []
        
        if save_layer_partials:
            plt.figure(figsize=(12, 12))
        
        # Initialize file-specific counter if not exists
        file_key = f"{clf_info['folder']}/{clf_info['name']}"
        if file_key not in file_identifier_counts:
            file_identifier_counts[file_key] = {}
            
                
        for shape in shapes:
            has_identifier = hasattr(shape, 'model') and hasattr(shape.model, 'id')
            
            if not has_identifier:
                print(f"Found shape without identifier at height {height}mm in {clf_info['name']}")
                
            # Initialize shape position tracking for all shapes
            if hasattr(shape, 'points'):
                points = shape.points[0]
                if isinstance(points, np.ndarray) and points.shape[1] >= 2:
                    x_min = min(x_min, np.min(points[:, 0]))
                    x_max = max(x_max, np.max(points[:, 0]))
                    y_min = min(y_min, np.min(points[:, 1]))
                    y_max = max(y_max, np.max(points[:, 1]))

            # Store shape information regardless of identifier
            shape_info = {
                'points': None,
                'type': 'unknown',
                'height': height,
                'file': clf_info['name'],
                'folder': clf_info['folder'],
                'is_closed': False
            }
            
            # Extract shape data and determine type
            if hasattr(shape, 'points'):
                points = shape.points[0]
                if isinstance(points, np.ndarray) and points.shape[1] >= 2:
                    shape_info['points'] = points.copy()
                    if len(points) == 1:
                        shape_info['type'] = 'point'
                        if draw_points:
                            plt.plot(points[0, 0], points[0, 1], 'ro', markersize=2, alpha=0.5)
                    elif len(points) == 2:
                        shape_info['type'] = 'line'
                        if draw_lines:
                            plt.plot(points[:, 0], points[:, 1], 'g-', linewidth=0.5, alpha=0.5)
                    else:
                        shape_info['type'] = 'path'
                        # Use draw_shape function for paths
                        draw_shape(plt, points, 'b', linewidth=0.5, alpha=0.5)
                        
                        # Check if path should be closed
                        if should_close_path(points):
                            shape_info['is_closed'] = True
            
            elif hasattr(shape, 'radius') and hasattr(shape, 'center'):
                shape_info['type'] = 'circle'
                shape_info['radius'] = shape.radius
                shape_info['center'] = shape.center
                shape_info['is_closed'] = True  # Circles are always closed

            # Update shape type counts
            if shape_info['type'] not in shape_types:
                shape_types[shape_info['type']] = 0
            shape_types[shape_info['type']] += 1

            # Process shapes based on whether they have an identifier
            if has_identifier:
                identifier = shape.model.id
                
                # Initialize identifier in path_counts if not exists
                if identifier not in path_counts:
                    path_counts[identifier] = {
                        "total": 0,
                        "by_type": {
                            "point": 0,
                            "line": 0,
                            "path": 0,
                            "circle": 0,
                            "unknown": 0
                        },
                        "closed_paths": 0,
                        "open_paths": 0
                    }

                # Initialize storage for this identifier if needed
                if identifier not in shapes_by_identifier:
                    shapes_by_identifier[identifier] = {
                        'shapes': [],
                        'height_range': [float('inf'), float('-inf')],
                        'count': 0,
                        'closed_paths': 0,
                        'total_paths': 0
                    }

                # Update identifier statistics
                shapes_by_identifier[identifier]['count'] += 1
                shapes_by_identifier[identifier]['shapes'].append(shape_info)
                
                # Update height range for identifier
                shapes_by_identifier[identifier]['height_range'][0] = min(
                    shapes_by_identifier[identifier]['height_range'][0], 
                    height
                )
                shapes_by_identifier[identifier]['height_range'][1] = max(
                    shapes_by_identifier[identifier]['height_range'][1], 
                    height
                )

                # Update path counts
                path_counts[identifier]["total"] += 1
                path_counts[identifier]["by_type"][shape_info['type']] += 1

                # Update closed/open path counts
                if shape_info['type'] == "path":
                    shapes_by_identifier[identifier]['total_paths'] += 1
                    if shape_info['is_closed']:
                        path_counts[identifier]["closed_paths"] += 1
                        shapes_by_identifier[identifier]['closed_paths'] += 1
                    else:
                        path_counts[identifier]["open_paths"] += 1

                # Update file-specific identifier counts
                file_key = f"{clf_info['folder']}/{clf_info['name']}"
                if file_key not in file_identifier_counts:
                    file_identifier_counts[file_key] = {}
                if identifier not in file_identifier_counts[file_key]:
                    file_identifier_counts[file_key][identifier] = 0
                file_identifier_counts[file_key][identifier] += 1

            else:
                # Process shapes without identifiers
                if 'no_identifier' not in shapes_by_identifier:
                    shapes_by_identifier['no_identifier'] = {
                        'shapes': [],
                        'height_range': [float('inf'), float('-inf')],
                        'count': 0,
                        'closed_paths': 0,
                        'total_paths': 0
                    }
                
                # Update non-identifier statistics
                shapes_by_identifier['no_identifier']['count'] += 1
                shapes_by_identifier['no_identifier']['shapes'].append(shape_info)
                
                # Update height range for non-identifier shapes
                shapes_by_identifier['no_identifier']['height_range'][0] = min(
                    shapes_by_identifier['no_identifier']['height_range'][0], 
                    height
                )
                shapes_by_identifier['no_identifier']['height_range'][1] = max(
                    shapes_by_identifier['no_identifier']['height_range'][1], 
                    height
                )

                # Update path counts for non-identifier shapes
                if shape_info['type'] == "path":
                    shapes_by_identifier['no_identifier']['total_paths'] += 1
                    if shape_info['is_closed']:
                        shapes_by_identifier['no_identifier']['closed_paths'] += 1
                        
        image_path = None          
        if save_layer_partials:
            # Create figure
            setup_platform_figure(figsize=(12, 12))
            
            # Draw platform boundary and axes with custom styling
            draw_platform_boundary(plt, color='r', alpha=0.3, 
                                label='Platform boundary (-125 to +125mm)')
            add_reference_lines(plt, alpha=0.5)
            
            plt.title(f'Layer at Height: {height:.3f}mm\nSource: {clf_info["name"]} in {clf_info["folder"]}')
            plt.xlabel('X (mm)')
            plt.ylabel('Y (mm)')

            plt.grid(True)
            plt.legend()
            
            set_platform_limits(plt)
            
            sanitized_folder = clf_info["folder"].replace('/', '_').replace('\\', '_')
            filename = f'layer_{height:.3f}mm_{clf_info["name"]}_{sanitized_folder}.png'
            
            output_path = os.path.join(output_dir, "layer_partials", filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            save_platform_figure(plt, output_path)
            
            image_path = os.path.join("layer_partials", filename)
        
        # Count closed paths correctly
        closed_paths_count = sum(1 for s in shapes 
                               if (hasattr(s, 'points') and 
                                   len(s.points) > 0 and 
                                   should_close_path(s.points[0])))
        return {
            "height": height,
            "num_shapes": len(shapes),
            "image": image_path,  # Use image_path here instead of direct filename reference
            "file": clf_info["name"],
            "folder": clf_info["folder"],
            "position": {
                "x_min": float(x_min) if x_min != float('inf') else None,
                "x_max": float(x_max) if x_max != float('-inf') else None,
                "y_min": float(y_min) if y_min != float('inf') else None,
                "y_max": float(y_max) if y_max != float('-inf') else None
            },
            "closed_paths": closed_paths_count,
            "total_paths": sum(1 for s in shapes if hasattr(s, 'points'))
        }
        
    except Exception as e:
        print(f"Error in layer analysis: {str(e)}")
        return f"Error analyzing layer: {str(e)}"


def generate_full_layer_heights(max_height):
    """Generate a list of all layer heights from 0.05mm to max_height in 0.05mm increments"""
    heights = []
    current_height = 0.05  # Start at 0.0500mm
    while current_height <= max_height:
        heights.append(round(current_height, 4))  # Round to 4 decimal places
        current_height = round(current_height + 0.05, 4)
    return heights


def get_max_layer_height(clf_files):
    """Find the maximum layer height across all CLF files"""
    max_height = 0
    for clf_info in clf_files:
        try:
            from utils.pyarcam.clfutil import CLFFile
            part = CLFFile(clf_info['path'])
            if hasattr(part, 'box'):
                max_height = max(max_height, float(part.box.max[2]))
        except Exception as e:
            print(f"Error getting max height for {clf_info['name']}: {str(e)}")
    return max_height