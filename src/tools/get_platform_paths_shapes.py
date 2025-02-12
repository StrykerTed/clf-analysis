import os
import json
import logging
from datetime import datetime
from pyarcam.clfutil import CLFFile
import matplotlib.pyplot as plt
import numpy as np

from myfuncs.file_utils import (
    create_output_folder
)

def find_clf_files(build_dir):
    """Find all CLF files in the build directory structure"""
    clf_files = []
    models_dir = os.path.join(build_dir, "Models")
    
    if not os.path.exists(models_dir):
        print(f"Models directory not found at: {models_dir}")
        return clf_files
        
    print(f"Scanning directory: {models_dir}")
    
    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file.endswith('.clf'):
                full_path = os.path.join(root, file)
                rel_folder = os.path.relpath(root, models_dir)
                clf_files.append({
                    'path': full_path,
                    'folder': rel_folder,
                    'name': file
                })
                print(f"Found CLF file: {file} in {rel_folder}")
    
    return clf_files

def create_identifier_platform_view(identifier, shapes_data, output_dir):
    """Create a platform view showing all shapes for a specific identifier"""
    try:
        plt.figure(figsize=(15, 15))
        
        # Draw platform boundaries
        plt.plot([-125, 125, 125, -125, -125], 
                [-125, -125, 125, 125, -125], 
                'k--', alpha=0.5, label='Platform boundary')
        
        # Reference lines
        plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        plt.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
        plt.grid(True, alpha=0.2)
        
        # Draw all shapes for this identifier
        height_range = shapes_data['height_range']
        total_shapes = shapes_data['count']
        
        shape_colors = plt.cm.viridis(np.linspace(0, 1, len(shapes_data['shapes'])))
        
        for shape_info, color in zip(shapes_data['shapes'], shape_colors):
            if shape_info['points'] is not None:
                points = shape_info['points']
                if shape_info['type'] == 'point':
                    plt.plot(points[0, 0], points[0, 1], 'o', color=color, markersize=2, alpha=0.7)
                else:
                    plt.plot(points[:, 0], points[:, 1], '-', color=color, linewidth=0.5, alpha=0.7)
            elif shape_info['type'] == 'circle':
                circle = plt.Circle(
                    shape_info['center'], 
                    shape_info['radius'], 
                    color=color, 
                    fill=False, 
                    alpha=0.7
                )
                plt.gca().add_artist(circle)
        
        plt.title(f'Identifier {identifier} Platform View\n'
                 f'Total Shapes: {total_shapes}\n'
                 f'Height Range: {height_range[0]:.2f}mm to {height_range[1]:.2f}mm')
        plt.xlabel('X Position (mm)')
        plt.ylabel('Y Position (mm)')
        plt.axis('equal')
        
        # Set axis limits to match platform
        plt.xlim(-130, 130)
        plt.ylim(-130, 130)
        
        # Save the figure
        identifier_dir = os.path.join(output_dir, "identifier_views")
        os.makedirs(identifier_dir, exist_ok=True)
        filename = f'identifier_{identifier}_platform_view.png'
        output_path = os.path.join(identifier_dir, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return os.path.join("identifier_views", filename)
        
    except Exception as e:
        print(f"Error creating identifier platform view for ID {identifier}: {str(e)}")
        return None

def create_platform_composite(clf_files, output_dir, height=1.0):
    """Create a composite view of all shapes at specified height"""
    plt.figure(figsize=(15, 15))
    
    # Draw platform boundaries based on -125 to +125mm system
    plt.plot([-125, 125, 125, -125, -125], 
            [-125, -125, 125, 125, -125], 
            'k--', alpha=0.5, label='Platform boundary')
    
    # Reference lines
    plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    plt.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
    
    # Draw grid
    plt.grid(True, alpha=0.2)
    
    # Different colors for different file types
    colors = {
        'Part.clf': 'blue',
        'WaferSupport.clf': 'red',
        'Net.clf': 'green'
    }
    
    shapes_found = False
    for clf_info in clf_files:
        try:
            part = CLFFile(clf_info['path'])
            if not hasattr(part, 'box'):
                continue
                
            layer = part.find(height)
            if layer is None:
                continue
                
            if hasattr(layer, 'shapes'):
                for shape in layer.shapes:
                    if hasattr(shape, 'points'):
                        points = shape.points[0]
                        if isinstance(points, np.ndarray) and points.shape[1] >= 2:
                            color = colors.get(clf_info['name'], 'gray')
                            plt.plot(points[:, 0], points[:, 1], 
                                   color=color, linewidth=0.5, 
                                   label=clf_info['name'] if not shapes_found else "")
                            shapes_found = True
            
        except Exception as e:
            print(f"Error processing {clf_info['name']} for platform view: {str(e)}")
    
    plt.title(f'Platform Composite View at Height {height}mm')
    plt.xlabel('X Position (mm)')
    plt.ylabel('Y Position (mm)')
    plt.axis('equal')
    
    plt.xlim(-130, 130)
    plt.ylim(-130, 130)
    
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())
    
    filename = f'platform_composite_{height}mm.png'
    output_path = os.path.join(output_dir, "composite_platforms", filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return os.path.join("composite_platforms", filename)

def analyze_layer(clf_file, height, output_dir, clf_info, path_counts, shape_types, file_identifier_counts, shapes_by_identifier, draw_points=True, draw_lines=True):
    """Analyze a specific layer and generate visualization"""
    try:
        layer = clf_file.find(height)
        if layer is None:
            return f"No layer found at height {height}"
        
        plt.figure(figsize=(12, 12))
        shapes = layer.shapes if hasattr(layer, 'shapes') else []
        
        # Track shape positions
        x_min, x_max = float('inf'), float('-inf')
        y_min, y_max = float('inf'), float('-inf')
        
        # Initialize file-specific counter if not exists
        file_key = f"{clf_info['folder']}/{clf_info['name']}"
        if file_key not in file_identifier_counts:
            file_identifier_counts[file_key] = {}
        
        for shape in shapes:
            if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                identifier = shape.model.id
                
                # Initialize storage for this identifier if needed
                if identifier not in shapes_by_identifier:
                    shapes_by_identifier[identifier] = {
                        'shapes': [],
                        'height_range': [float('inf'), float('-inf')],
                        'count': 0
                    }
                
                # Store shape information
                shape_info = {
                    'points': None,
                    'type': 'unknown',
                    'height': height,
                    'file': clf_info['name'],
                    'folder': clf_info['folder']
                }
                
                # Update height range
                shapes_by_identifier[identifier]['height_range'][0] = min(
                    shapes_by_identifier[identifier]['height_range'][0], 
                    height
                )
                shapes_by_identifier[identifier]['height_range'][1] = max(
                    shapes_by_identifier[identifier]['height_range'][1], 
                    height
                )
                
                shapes_by_identifier[identifier]['count'] += 1
                
                # Extract shape data
                if hasattr(shape, 'points'):
                    points = shape.points[0]
                    if isinstance(points, np.ndarray) and points.shape[1] >= 2:
                        shape_info['points'] = points.copy()
                        if len(points) == 1:
                            shape_info['type'] = 'point'
                        elif len(points) == 2:
                            shape_info['type'] = 'line'
                        else:
                            shape_info['type'] = 'path'
                elif hasattr(shape, 'radius') and hasattr(shape, 'center'):
                    shape_info['type'] = 'circle'
                    shape_info['radius'] = shape.radius
                    shape_info['center'] = shape.center
                
                shapes_by_identifier[identifier]['shapes'].append(shape_info)
                
                # Update file-specific identifier counts
                if identifier not in file_identifier_counts[file_key]:
                    file_identifier_counts[file_key][identifier] = 0
                file_identifier_counts[file_key][identifier] += 1
                
                # Initialize counts for this identifier if it doesn't exist
                if identifier not in path_counts:
                    path_counts[identifier] = {
                        "total": 0,
                        "by_type": {
                            "point": 0,
                            "line": 0,
                            "path": 0,
                            "circle": 0,
                            "unknown": 0
                        }
                    }
                shape_type = "unknown"
            
            # Process shape visualization
            if hasattr(shape, 'points'):
                points = shape.points[0]
                if isinstance(points, np.ndarray):
                    if points.shape[1] >= 2:
                        if len(points) == 1:
                            shape_type = "point"
                            if draw_points:
                                plt.plot(points[0, 0], points[0, 1], 'ro', markersize=2, alpha=0.5)
                        elif len(points) == 2:
                            shape_type = "line"
                            if draw_lines:
                                plt.plot(points[:, 0], points[:, 1], 'g-', linewidth=0.5, alpha=0.5)
                        else:
                            shape_type = "path"
                            plt.plot(points[:, 0], points[:, 1], 'b-', linewidth=0.5)
                        
                        x_min = min(x_min, np.min(points[:, 0]))
                        x_max = max(x_max, np.max(points[:, 0]))
                        y_min = min(y_min, np.min(points[:, 1]))
                        y_max = max(y_max, np.max(points[:, 1]))
            
            elif hasattr(shape, 'radius') or hasattr(shape, 'center'):
                shape_type = "circle"
            
            if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                identifier = shape.model.id
                path_counts[identifier]["total"] += 1
                path_counts[identifier]["by_type"][shape_type] += 1
            
            if shape_type not in shape_types:
                shape_types[shape_type] = 0
            shape_types[shape_type] += 1
        
        plt.plot([-125, 125, 125, -125, -125], 
                [-125, -125, 125, 125, -125], 
                'r--', alpha=0.3, label='Platform boundary (-125 to +125mm)')
        
        plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        
        plt.title(f'Layer at Height: {height:.3f}mm\nSource: {clf_info["name"]} in {clf_info["folder"]}')
        plt.xlabel('X (mm)')
        plt.ylabel('Y (mm)')
        plt.axis('equal')
        plt.grid(True)
        plt.legend()
        
        plt.xlim(-130, 130)
        plt.ylim(-130, 130)
        
        sanitized_folder = clf_info["folder"].replace('/', '_').replace('\\', '_')
        filename = f'layer_{height:.3f}mm_{clf_info["name"]}_{sanitized_folder}.png'
        
        output_path = os.path.join(output_dir, "layer_partials", filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            "height": height,
            "num_shapes": len(shapes),
            "image": os.path.join("layer_partials", filename),
            "file": clf_info["name"],
            "folder": clf_info["folder"],
            "position": {
                "x_min": float(x_min) if x_min != float('inf') else None,
                "x_max": float(x_max) if x_max != float('-inf') else None,
                "y_min": float(y_min) if y_min != float('inf') else None,
                "y_max": float(y_max) if y_max != float('-inf') else None
            }
        }
        
    except Exception as e:
        print(f"Error in layer analysis: {str(e)}")
        return f"Error analyzing layer: {str(e)}"
    
def main():
    try:
        draw_points = input("Draw points as small circles? (y/n): ").lower().startswith('y')
        draw_lines = input("Draw lines? (y/n): ").lower().startswith('y')
        
        base_dir = os.getcwd()
        build_dir = os.path.join(base_dir, "preprocess build-270851.abp")
        output_dir = create_output_folder(base_dir)
        
        print(f"Looking for build directory at: {build_dir}")
        if not os.path.exists(build_dir):
            print("Build directory not found!")
            return
            
        print("\nFinding CLF files...")
        clf_files = find_clf_files(build_dir)
        print(f"Found {len(clf_files)} CLF files")
        
        # Dictionaries to track statistics
        path_counts = {}
        shape_types = {}
        file_identifier_counts = {}
        shapes_by_identifier = {}
        
        platform_info = {
            "files_analyzed": [],
            "layers": [],
            "platform_composites": [],
            "file_identifier_summary": [],
            "identifier_platform_views": []
        }
        
        # Process each CLF file
        for clf_info in clf_files:
            try:
                print(f"\nProcessing: {clf_info['name']} in {clf_info['folder']}")
                part = CLFFile(clf_info['path'])
                
                file_info = {
                    "filename": clf_info['name'],
                    "folder": clf_info['folder'],
                    "num_layers": part.nlayers,
                    "z_range": [part.box.min[2], part.box.max[2]] if hasattr(part, 'box') else None,
                    "bounds": {
                        "x_range": [float(part.box.min[0]), float(part.box.max[0])] if hasattr(part, 'box') else None,
                        "y_range": [float(part.box.min[1]), float(part.box.max[1])] if hasattr(part, 'box') else None,
                        "z_range": [float(part.box.min[2]), float(part.box.max[2])] if hasattr(part, 'box') else None
                    }
                }
                platform_info["files_analyzed"].append(file_info)
                
                if hasattr(part, 'box'):
                    heights = np.linspace(part.box.min[2], part.box.max[2], 7)
                    for height in heights:
                        print(f"  Analyzing layer at height {height:.3f}mm")
                        layer_info = analyze_layer(part, height, output_dir, clf_info, 
                                                path_counts, shape_types, file_identifier_counts,
                                                shapes_by_identifier,
                                                draw_points=draw_points, 
                                                draw_lines=draw_lines)
                        if isinstance(layer_info, dict):
                            platform_info["layers"].append(layer_info)
                
            except Exception as e:
                print(f"Error processing {clf_info['name']}: {str(e)}")
        
        # Create file identifier summary
        for file_path, identifiers in file_identifier_counts.items():
            summary_entry = {
                "file_path": file_path,
                "identifier_counts": {
                    str(identifier): count 
                    for identifier, count in identifiers.items()
                },
                "total_shapes": sum(identifiers.values()),
                "unique_identifiers": len(identifiers)
            }
            platform_info["file_identifier_summary"].append(summary_entry)
        
        # Create identifier-specific platform views
        print("\nGenerating identifier-specific platform views...")
        for identifier, shapes_data in shapes_by_identifier.items():
            try:
                print(f"Creating platform view for identifier {identifier}...")
                view_file = create_identifier_platform_view(identifier, shapes_data, output_dir)
                if view_file:
                    platform_info["identifier_platform_views"].append({
                        "identifier": identifier,
                        "filename": view_file,
                        "total_shapes": shapes_data['count'],
                        "height_range": shapes_data['height_range']
                    })
                    print(f"Created identifier view for ID {identifier}")
            except Exception as e:
                print(f"Error creating identifier view for ID {identifier}: {str(e)}")
        
        # Print summary information
        print("\nIdentifier Summary by File:")
        for summary in platform_info["file_identifier_summary"]:
            print(f"\nFile: {summary['file_path']}")
            print(f"Total Shapes: {summary['total_shapes']}")
            print(f"Unique Identifiers: {summary['unique_identifiers']}")
            print("Identifier Counts:")
            for identifier, count in summary['identifier_counts'].items():
                print(f"  ID {identifier}: {count} shapes")
        
        # Create composite platform views at multiple heights
        wanted_layer_heights = [1, 25, 50, 100,120,140,160,170,180, 200]
        print("\nGenerating platform composite views at multiple heights...")
        for height in wanted_layer_heights:
            try:
                print(f"Creating composite view at height {height}mm...")
                composite_file = create_platform_composite(clf_files, output_dir, height=height)
                platform_info["platform_composites"].append({
                    "height": height,
                    "filename": composite_file
                })
                print(f"Created platform composite at {height}mm: {composite_file}")
            except Exception as e:
                print(f"Error creating composite at height {height}mm: {str(e)}")
        
        # Save all information to JSON
        summary_filename = "platform_info.json"
        summary_path = os.path.join(output_dir, summary_filename)
        
        # Prepare final JSON data
        json_identifier_info = {
            "path_counts": path_counts,
            "shape_types": shape_types,
            "visualization_settings": {
                "draw_points": draw_points,
                "draw_lines": draw_lines
            }
        }
        
        platform_info['analysis_summary'] = json_identifier_info
        
        # Save to JSON file
        with open(summary_path, 'w') as f:
            json.dump(platform_info, f, indent=2)
            
        print(f"\nAnalysis complete. Results saved to: {output_dir}")
        print(f"Summary file: {summary_path}")
        print("\nIdentifier-specific platform views created:")
        for view_info in platform_info["identifier_platform_views"]:
            print(f"ID {view_info['identifier']}: {view_info['filename']}")
        
        # Print shape type statistics
        print("\nShape Types Summary:")
        for shape_type, count in shape_types.items():
            print(f"{shape_type}: {count} instances")
            
    except Exception as e:
        print(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    main()
