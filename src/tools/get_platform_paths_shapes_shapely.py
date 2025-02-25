# get_platform_paths_shapes_shapely.py
import os
import sys
import matplotlib.pyplot as plt   
import numpy as np   
from logging.handlers import QueueHandler, QueueListener   
import logging
from multiprocessing import Manager 
from datetime import datetime 
import json  # For JSON handling
from matplotlib.patches import Polygon  # For polygon plotting

# Add parent directory to path to find setup_paths
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import setup_paths

from utils.pyarcam.clfutil import CLFFile

from utils.platform_analysis.file_handlers import (
    setup_abp_folders,
)

from utils.myfuncs.file_utils import (
    create_output_folder,
    find_clf_files,
    load_exclusion_patterns,
    should_skip_folder
)

from utils.myfuncs.shape_things import (
    should_close_path
)
from utils.myfuncs.print_utils import (
    add_platform_labels,
    print_analysis_summary,
    print_identifier_summary,
    create_unclosed_shapes_view
)

from utils.myfuncs.plotTools import (
    setup_standard_platform_view, 
    setup_platform_figure,
    draw_platform_boundary,
    add_reference_lines,
    set_platform_limits,
    draw_shape,
    draw_aligned_shape,
    save_platform_figure
)

def setup_logging(top_level_folder):
    """Configure logging for multiprocessing with timestamped filename in a logging subfolder."""
    # Create the logging subfolder in top_level_folder
    logging_dir = os.path.join(top_level_folder, "logging")
    os.makedirs(logging_dir, exist_ok=True)  # Create directory if it doesn't exist
    
    # Generate timestamp for the filename (e.g., 20250224_153022)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"shapely_abp_path_processing_{timestamp}.log"
    log_file = os.path.join(logging_dir, log_filename)
    
    # Set up manager for multiprocessing
    manager = Manager()
    log_queue = manager.Queue()
    
    # File handler: logs everything to the timestamped file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(processName)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler: only WARNING and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Set up the root logger for the main process
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
    
    # Start the queue listener
    listener = QueueListener(log_queue, file_handler, console_handler)
    listener.start()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger, log_queue, listener

def create_combined_identifier_platform_view(shapes_by_identifier, output_dir):
    """Create a single platform view showing all identifiers with different colors"""
    try:
        # Create a standard platform view
        setup_platform_figure()
        
        # Add standard platform elements
        draw_platform_boundary(plt)
        add_reference_lines(plt)
        
        # Skip the 'no_identifier' key if it exists
        identifiers = [id for id in shapes_by_identifier.keys() if id != 'no_identifier']
        
        if not identifiers:
            print("No identifiers found for combined view")
            return None
            
        # Generate a color for each identifier
        colors = plt.cm.tab10(np.linspace(0, 1, len(identifiers)))
        identifier_colors = dict(zip(identifiers, colors))
        
        # Track statistics
        total_shapes = 0
        min_height = float('inf')
        max_height = float('-inf')
        
        # Plot each identifier with its assigned color
        for identifier, color in identifier_colors.items():
            shapes_data = shapes_by_identifier[identifier]
            
            # Update statistics
            total_shapes += shapes_data['count']
            min_height = min(min_height, shapes_data['height_range'][0])
            max_height = max(max_height, shapes_data['height_range'][1])
            
            # Draw a sample shape for the legend
            plt.plot([], [], color=color, label=f"ID: {identifier}")
            
            # Draw all shapes for this identifier
            for shape_info in shapes_data['shapes']:
                if shape_info['points'] is not None:
                    points = shape_info['points']
                    if shape_info['type'] == 'point':
                        plt.plot(points[0, 0], points[0, 1], 'o', 
                                color=color, markersize=2, alpha=0.7)
                    else:
                        draw_shape(plt, points, color)
                elif shape_info['type'] == 'circle':
                    circle = plt.Circle(
                        shape_info['center'], 
                        shape_info['radius'], 
                        color=color, 
                        fill=False, 
                        alpha=0.7
                    )
                    plt.gca().add_artist(circle)
        
        plt.title(f'Combined Identifier Platform View\n'
                 f'Total Identifiers: {len(identifiers)}\n'
                 f'Total Shapes: {total_shapes}\n'
                 f'Height Range: {min_height:.2f}mm to {max_height:.2f}mm')
        add_platform_labels(plt)
        set_platform_limits(plt)
        
        # Add a legend for the identifiers
        plt.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.)
        
        # Save the plot
        identifier_dir = os.path.join(output_dir, "identifier_views")
        os.makedirs(identifier_dir, exist_ok=True)
        filename = f'combined_identifiers_platform_view.png'
        output_path = os.path.join(identifier_dir, filename)
        save_platform_figure(plt, output_path)
        
        return os.path.join("identifier_views", filename)
        
    except Exception as e:
        print(f"Error creating combined identifier platform view: {str(e)}")
        return None

def create_non_identifier_platform_view(non_id_shapes, output_dir):
    """Create a platform view showing all shapes that don't have identifiers"""
    try:        
        # Create a standard platform view with common elements
        title = f'Non-Identifier Shapes Platform View\nTotal Shapes: {len(non_id_shapes)}'
        setup_standard_platform_view(title)
        
        # Draw all shapes without identifiers
        shape_colors = plt.cm.viridis(np.linspace(0, 1, len(non_id_shapes)))
        
        for shape_info, color in zip(non_id_shapes, shape_colors):
            if shape_info['points'] is not None:
                points = shape_info['points']
                if shape_info['type'] == 'point':
                    plt.plot(points[0, 0], points[0, 1], 'o', 
                            color=color, markersize=2, alpha=0.7)
                else:
                    draw_shape(plt, points, color)
            elif shape_info['type'] == 'circle':
                circle = plt.Circle(
                    shape_info['center'], 
                    shape_info['radius'], 
                    color=color, 
                    fill=False, 
                    alpha=0.7
                )
                plt.gca().add_artist(circle)
        
        # Save the plot
        non_id_dir = os.path.join(output_dir, "non_identifier_views")
        os.makedirs(non_id_dir, exist_ok=True)
        filename = f'non_identifier_platform_view.png'
        output_path = os.path.join(non_id_dir, filename)
        save_platform_figure(plt, output_path)
        
        return os.path.join("non_identifier_views", filename)
        
    except Exception as e:
        print(f"Error creating non-identifier platform view: {str(e)}")
        return None

def create_clean_platform(clf_files, output_dir, height=1.0, fill_closed=False, alignment_style_only=False, save_clean_png=True):
    """Create a clean platform view without any chart elements, just shapes, and save raw path data."""
    # Initialize list to store shape data
    shape_data_list = []
    
    # If alignment_style_only, declare midpoints list
    if alignment_style_only:
        midpoints = []
    
    # Only create plot if save_clean_png is True
    if save_clean_png:
        # Create figure with equal aspect ratio
        fig = setup_platform_figure(figsize=(15, 15))
        
        # Remove all margins and spacing
        ax = plt.gca()
        ax.set_position([0, 0, 1, 1])
        
        # Set exact limits for platform size
        plt.xlim(-125, 125)
        plt.ylim(-125, 125)
        
        # Turn off all chart elements
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        plt.axis('off')
    
    colors = {
        'Part.clf': 'blue',
        'WaferSupport.clf': 'red',
        'Net.clf': 'green'
    }
    
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
                    color = colors.get(clf_info['name'], 'gray')
                    # --- Gather shape identifier if it exists ---
                    shape_identifier = None
                    if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                        shape_identifier = shape.model.id
                    if hasattr(shape, 'points') and shape.points:
                        points = shape.points[0]
                        if isinstance(points, np.ndarray) and points.shape[0] >= 1 and points.shape[1] >= 2:
                            should_close = False
                            # Safely call should_close_path
                            try:
                                should_close = should_close_path(points)
                            except Exception as e:
                                print(f"Error in should_close_path for {clf_info['name']}: {str(e)}")
                                should_close = False
                            
                            # Collect shape data
                            shape_data = {
                                'type': 'path',
                                'points': points.tolist(),
                                'color': color,
                                'clf_name': clf_info['name'],
                                'clf_folder': clf_info['folder'],
                                'fill_closed': fill_closed,
                                'identifier': shape_identifier
                            }
                            shape_data_list.append(shape_data)
                            
                            # Only plot if save_clean_png is True
                            if save_clean_png:
                                if alignment_style_only:
                                    draw_aligned_shape(plt, points, color, midpoints=midpoints)
                                else:
                                    if fill_closed and should_close:
                                        polygon = Polygon(points, facecolor='black', edgecolor=color, alpha=0.5)
                                        plt.gca().add_patch(polygon)
                                    else:
                                        draw_shape(plt, points, color)
                        else:
                            # Handle invalid points data
                            print(f"Invalid points in shape in {clf_info['name']}")
                            shape_data = {
                                'type': 'invalid',
                                'points': None,
                                'color': color,
                                'clf_name': clf_info['name'],
                                'clf_folder': clf_info['folder'],
                                'fill_closed': fill_closed,
                                'identifier': shape_identifier
                            }
                            shape_data_list.append(shape_data)
                    elif hasattr(shape, 'radius') and hasattr(shape, 'center'):
                        # Collect circle data
                        shape_data = {
                            'type': 'circle',
                            'center': shape.center.tolist(),
                            'radius': shape.radius,
                            'color': color,
                            'clf_name': clf_info['name'],
                            'clf_folder': clf_info['folder'],
                            'fill_closed': fill_closed,
                            'identifier': shape_identifier
                        }
                        shape_data_list.append(shape_data)
                        
                        # Only plot if save_clean_png is True
                        if save_clean_png:
                            circle = plt.Circle(shape.center, shape.radius, color=color, fill=False, alpha=0.7)
                            plt.gca().add_artist(circle)
                    else:
                        # Handle other shape types if necessary
                        print(f"Unrecognized shape type in {clf_info['name']}")
                        shape_data = {
                            'type': 'unknown',
                            'color': color,
                            'clf_name': clf_info['name'],
                            'clf_folder': clf_info['folder'],
                            'fill_closed': fill_closed,
                            'identifier': shape_identifier
                        }
                        shape_data_list.append(shape_data)
                     
        except Exception as e:
            print(f"Error processing {clf_info['name']} for clean platform: {str(e)}")
    
    # Only save PNG if save_clean_png is True
    if save_clean_png:        
        plt.axis('equal')  # Ensure perfect square
        filename = f'clean_platform_{height}mm.png'
        output_path = os.path.join(output_dir, "clean_platforms", filename)
        save_platform_figure(plt, output_path, pad_inches=0)
        png_path = os.path.join("clean_platforms", filename)
    else:
        png_path = None
    
    # Save the shape data to a file
    try:
        # Extract build number from ABP filename
        abp_name = os.path.basename(output_dir)
        build_number = abp_name.split('-')[1].split('.')[0] if '-' in abp_name else ''
        
        # Create directory with build number
        raw_data_dir = os.path.join(output_dir, f"imagePathRawData-{build_number}")
        os.makedirs(raw_data_dir, exist_ok=True)

        # Construct filename
        data_filename = f'platform_layer_pathdata_{height}mm.json'
        data_output_path = os.path.join(raw_data_dir, data_filename)
        
        # Write the data to file
        print(f"\nWriting shape data to: {data_output_path}")
        print(f"Number of shapes being written: {len(shape_data_list)}")
        
        with open(data_output_path, 'w') as f:
            json.dump(shape_data_list, f, indent=2)
        
        print(f"Successfully wrote shape data for height {height}mm")
        
    except Exception as e:
        print(f"Error saving shape data for clean platform at height {height}mm: {str(e)}")
        
    return png_path

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
 

def create_identifier_platform_view(identifier, shapes_data, output_dir):
    """Create a platform view showing all shapes for a specific identifier"""
    try:        
        # Create figure
        setup_platform_figure()
        
        # Add standard platform elements
        draw_platform_boundary(plt)
        add_reference_lines(plt)
        
        # Draw all shapes for this identifier
        height_range = shapes_data['height_range']
        total_shapes = shapes_data['count']
        
        shape_colors = plt.cm.viridis(np.linspace(0, 1, len(shapes_data['shapes'])))
        
        for shape_info, color in zip(shapes_data['shapes'], shape_colors):
            if shape_info['points'] is not None:
                points = shape_info['points']
                if shape_info['type'] == 'point':
                    plt.plot(points[0, 0], points[0, 1], 'o', 
                            color=color, markersize=2, alpha=0.7)
                else:
                    draw_shape(plt, points, color)
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
        add_platform_labels(plt)
        set_platform_limits(plt)
        
        identifier_dir = os.path.join(output_dir, "identifier_views")
        os.makedirs(identifier_dir, exist_ok=True)
        filename = f'identifier_{identifier}_platform_view.png'
        output_path = os.path.join(identifier_dir, filename)
        save_platform_figure(plt, output_path)
        
        return os.path.join("identifier_views", filename)
        
    except Exception as e:
        print(f"Error creating identifier platform view for ID {identifier}: {str(e)}")
        return None
    
def create_platform_composite_with_folders(clf_files, output_dir, height=1.0, fill_closed=False):
    """Create a composite view with unique colors per folder and a legend"""    
    # Create figure
    setup_platform_figure()
    
    # Get unique folders and assign colors using a colormap
    folders = sorted(list(set(clf_info['folder'] for clf_info in clf_files)))
    colors = plt.cm.tab20(np.linspace(0, 1, len(folders)))  # Use tab20 for distinct colors
    folder_colors = dict(zip(folders, colors))
    
    # Add standard platform elements
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    # Track which folders we've seen for legend
    folders_seen = set()
    
    for clf_info in clf_files:
        try:
            part = CLFFile(clf_info['path'])
            if not hasattr(part, 'box'):
                continue
                
            layer = part.find(height)
            if layer is None:
                continue
                
            folder = clf_info['folder']
            color = folder_colors[folder]
            
            if hasattr(layer, 'shapes'):
                for shape in layer.shapes:
                    if hasattr(shape, 'points'):
                        points = shape.points[0]
                        if isinstance(points, np.ndarray) and points.shape[1] >= 2:
                            # Draw shape with folder's color
                            if fill_closed and should_close_path(points):
                                polygon = Polygon(points, 
                                               facecolor=color, 
                                               edgecolor=color, 
                                               alpha=0.5)
                                plt.gca().add_patch(polygon)
                            else:
                                draw_shape(plt, points, color)
                                
                            # Add to legend (only once per folder)
                            if folder not in folders_seen:
                                plt.plot([], [], color=color, label=folder)
                                folders_seen.add(folder)
            
        except Exception as e:
            print(f"Error processing {clf_info['name']} for platform view: {str(e)}")
    
    plt.title(f'Platform Composite View at Height {height}mm')
    add_platform_labels(plt)
    set_platform_limits(plt)
    
    # Create legend with folder names
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    
    filename = f'platform_composite_folders_{height}mm.png'
    output_path = os.path.join(output_dir, "composite_platforms", filename)
    save_platform_figure(plt, output_path)
    
    return os.path.join("composite_platforms", filename)

def create_platform_composite(clf_files, output_dir, height=1.0, fill_closed=False):
    """Create a composite view of all shapes at specified height"""

    # Create a standard platform view with title
    title = f'Platform Composite View at Height {height}mm'
    setup_standard_platform_view(title)
    
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
                            
                            # Check if shape should be closed
                            if fill_closed and should_close_path(points):
                                # Create polygon for filled shape
                                polygon = Polygon(points, facecolor='black', edgecolor=color, alpha=0.5)
                                plt.gca().add_patch(polygon)
                            else:
                                # Draw unfilled shape
                                draw_shape(plt, points, color)
                                
                            if not shapes_found:
                                plt.plot([], [], color=color, label=clf_info['name'])
                                shapes_found = True
            
        except Exception as e:
            print(f"Error processing {clf_info['name']} for platform view: {str(e)}")
    
    # Add legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())
    
    # Save figure
    filename = f'platform_composite_{height}mm.png'
    output_path = os.path.join(output_dir, "composite_platforms", filename)
    save_platform_figure(plt, output_path)
    
    return os.path.join("composite_platforms", filename)

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
            part = CLFFile(clf_info['path'])
            if hasattr(part, 'box'):
                max_height = max(max_height, float(part.box.max[2]))
        except Exception as e:
            print(f"Error getting max height for {clf_info['name']}: {str(e)}")
    return max_height

def main():
    wanted_layer_heights = list(range(1, 201, 5))
    
    # Get the directory paths (do this once)
    script_dir = os.path.dirname(os.path.abspath(__file__))  # gets /tools directory
    src_dir = os.path.dirname(script_dir)                    # gets /src directory
    project_root = os.path.dirname(src_dir)                  # gets project root
    config_dir = os.path.join(src_dir, 'config')            # gets /src/config
    
    print(f"Script directory: {script_dir}")
    print(f"Project root: {project_root}")

    logger, log_queue, listener = setup_logging(project_root)
    abp_file = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_sourcefiles/preprocess build-271120.abp"
    logger.info(f"Processing ABP file: {abp_file}")
    
    build_dir = setup_abp_folders(abp_file)
    logger.info(f"Build directory set up at: {build_dir}")


    try:
        draw_points = 'y'
        draw_lines = 'y'
        fill_closed = 'y'
        exclude_folders = 'y'
        save_layer_partials = False 
        save_clean = 'y'
        save_clean_png = False
        alignment_style_only = False
        
        logger.info("Configuration parameters:")
        logger.info(f"  - Draw Points: {draw_points}")
        logger.info(f"  - Draw Lines: {draw_lines}")
        logger.info(f"  - Fill Closed Shapes: {fill_closed}")
        logger.info(f"  - Exclude Folders: {exclude_folders}")
        logger.info(f"  - Save Layer Partials: {save_layer_partials}")
        logger.info(f"  - Save Clean Platforms: {save_clean}")
        logger.info(f"  - Save Clean PNG: {save_clean_png}")
        logger.info(f"  - Alignment Style Only: {alignment_style_only}")

        # Only ask for height mode if saving clean platforms
        clean_heights = None
        if save_clean:
            height_choice = 'full'
            if height_choice == 'full':
                logger.info("Will process full range of heights at 0.05mm intervals")
            else:
                logger.info("Will process sample heights only")

        # Load exclusion patterns
        exclusion_patterns = load_exclusion_patterns(config_dir) if exclude_folders else []
        
        if exclude_folders:
            logger.info("Excluding folders containing these patterns:")
            for pattern in exclusion_patterns:
                logger.info(f"  - {pattern}")

        # Create output directory based on the ABP filename
        abp_name = os.path.basename(build_dir)
        output_dir = create_output_folder(abp_name, project_root, save_layer_partials, alignment_style_only)
        logger.info(f"Created output directory at: {output_dir}")
        logger.info(f"Project root directory at: {project_root}")
        
        # Create clean_platforms directory if needed
        if save_clean:
            clean_platforms_dir = os.path.join(output_dir, "clean_platforms")
            os.makedirs(clean_platforms_dir, exist_ok=True)
            logger.info(f"Created clean platforms directory: {clean_platforms_dir}")
        
        logger.info(f"Looking for build directory at: {build_dir}")
        if not os.path.exists(build_dir):
            logger.error("Build directory not found!")
            return
            
        logger.info("Finding CLF files...")
        all_clf_files = find_clf_files(build_dir)
        
        # Filter CLF files based on exclusion patterns
        if exclude_folders:
            clf_files = []
            for clf_info in all_clf_files:
                should_skip = should_skip_folder(clf_info['folder'], exclusion_patterns)
                if should_skip:
                    logger.debug(f"Skipping file: {clf_info['name']} in {clf_info['folder']}")
                else:
                    clf_files.append(clf_info)
                    logger.debug(f"Keeping file: {clf_info['name']} in {clf_info['folder']}")
                    
            excluded_count = len(all_clf_files) - len(clf_files)
            logger.info(f"Found {len(all_clf_files)} total CLF files")
            logger.info(f"Excluded {excluded_count} files based on folder patterns")
            logger.info(f"Processing {len(clf_files)} CLF files")
        else:
            clf_files = all_clf_files
            logger.info(f"Found {len(clf_files)} CLF files")
        
        # Dictionaries to track statistics
        path_counts = {}
        shape_types = {}
        file_identifier_counts = {}
        shapes_by_identifier = {}
        closed_paths_found = {}
        
        platform_info = {
            "files_analyzed": [],
            "layers": [],
            "platform_composites": [],
            "clean_platforms": [],
            "file_identifier_summary": [],
            "identifier_platform_views": [],
            "non_identifier_views": None,  # Add this line
            "closed_paths_summary": {},
            "exclusion_info": {
                "exclusions_enabled": exclude_folders,
                "patterns_used": exclusion_patterns if exclude_folders else [],
                "files_excluded": excluded_count if exclude_folders else 0
            }
        }
        
        # Process each CLF file
        for clf_info in clf_files:
            try:
                if should_skip_folder(clf_info['folder'], exclusion_patterns):
                    print(f"WARNING: Skipping incorrectly included file: {clf_info['name']} in {clf_info['folder']}")
                    continue
                    
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
                        # print(f"  Analyzing layer at height {height:.3f}mm")
                        layer_info = analyze_layer(part, height, output_dir, clf_info, 
                                                path_counts, shape_types, file_identifier_counts,
                                                shapes_by_identifier,
                                                draw_points=draw_points, 
                                                draw_lines=draw_lines,
                                                save_layer_partials=save_layer_partials)
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
        
        # In main function, replace the platform view generation section with:
        print("\nGenerating identifier and non-identifier platform views...")
        for identifier, shapes_data in shapes_by_identifier.items():
            try:
                if identifier == 'no_identifier':
                    print("Creating platform view for shapes without identifiers...")
                    view_file = create_non_identifier_platform_view(shapes_data['shapes'], output_dir)
                    if view_file:
                        platform_info["non_identifier_views"] = {
                            "filename": view_file,
                            "total_shapes": shapes_data['count'],
                            "closed_paths": shapes_data['closed_paths'],
                            "total_paths": shapes_data['total_paths'],
                            "height_range": shapes_data['height_range']
                        }
                        print(f"Created non-identifier view with {shapes_data['count']} shapes")
                else:
                    print(f"Creating platform view for identifier {identifier}...")
                    view_file = create_identifier_platform_view(identifier, shapes_data, output_dir)
                    if view_file:
                        closed_count = 0
                        total_count = 0
                        for shape_info in shapes_data['shapes']:
                            if shape_info['points'] is not None and len(shape_info['points']) > 2:
                                total_count += 1
                                if should_close_path(shape_info['points']):
                                    closed_count += 1
                        
                        platform_info["identifier_platform_views"].append({
                            "identifier": identifier,
                            "filename": view_file,
                            "total_shapes": shapes_data['count'],
                            "height_range": shapes_data['height_range'],
                            "closed_paths": closed_count,
                            "total_paths": total_count
                        })
                        
                        closed_paths_found[identifier] = {
                            "closed_count": closed_count,
                            "total_count": total_count,
                            "percentage_closed": (closed_count / total_count * 100) if total_count > 0 else 0
                        }
                        
                        print(f"Created identifier view for ID {identifier} "
                              f"({closed_count}/{total_count} paths closed)")
                    
            except Exception as e:
                print(f"Error creating view for {'non-identifier shapes' if identifier == 'no_identifier' else f'ID {identifier}'}: {str(e)}")
        
        # Create a combined view of all identifiers
        print("\nGenerating combined identifier platform view...")
        combined_view_file = create_combined_identifier_platform_view(shapes_by_identifier, output_dir)
        if combined_view_file:
            platform_info["combined_identifier_view"] = {
                "filename": combined_view_file,
                "total_identifiers": len([id for id in shapes_by_identifier.keys() if id != 'no_identifier'])
            }
            print(f"Created combined identifier view with {platform_info['combined_identifier_view']['total_identifiers']} identifiers")

        # Print summary information
        print_identifier_summary(platform_info["file_identifier_summary"], closed_paths_found)
        
        # Create composite platform views with original layer heights
   
        print("\nGenerating platform composite views...")
        for height in wanted_layer_heights:
            try:
                print(f"Creating composite view at height {height}mm...")
                composite_file = create_platform_composite_with_folders(clf_files, output_dir, 
                                                        height=height, 
                                                        fill_closed=fill_closed)
                platform_info["platform_composites"].append({
                    "height": height,
                    "filename": composite_file
                })
                print(f"Created platform composite at {height}mm: {composite_file}")
            except Exception as e:
                print(f"Error creating composite at height {height}mm: {str(e)}")

        # Create clean platform views with full or sample heights
        if save_clean:
            print("\nGenerating clean platform views...")
            if height_choice == 'full':
                max_height = get_max_layer_height(clf_files)
                clean_heights = generate_full_layer_heights(max_height)
                print(f"Processing all layers from 0.0500mm to {max_height}mm at 0.05mm intervals")
            else:
                clean_heights = wanted_layer_heights
                print(f"Processing sample layers: {clean_heights}")
                
            for height in clean_heights:
                try:
                    print(f"Processing height {height}mm...")
                    clean_file = create_clean_platform(
                        clf_files, 
                        output_dir,
                        height=height,
                        fill_closed=fill_closed,
                        alignment_style_only=alignment_style_only,
                        save_clean_png=True
                    )

                    if save_clean_png and clean_file:
                        platform_info["clean_platforms"].append({
                            "height": height,
                            "filename": clean_file
                        })
                        print(f"Created clean platform at {height}mm: {clean_file}")
                except Exception as e:
                    print(f"Error creating clean platform at height {height}mm: {str(e)}")
        
        # Add closed paths information to final JSON
        platform_info["closed_paths_summary"] = closed_paths_found
        
        unclosed_view, unclosed_count = create_unclosed_shapes_view(shapes_by_identifier, output_dir)
        if unclosed_view:
            platform_info["unclosed_shapes_view"] = {
                "filename": unclosed_view,
                "total_shapes": unclosed_count
            }
            print(f"\nCreated unclosed shapes view with {unclosed_count} shapes")
    
        # Prepare final JSON data
        json_identifier_info = {
            "path_counts": path_counts,
            "shape_types": shape_types,
            "visualization_settings": {
                "draw_points": draw_points,
                "draw_lines": draw_lines
            },
            "closed_paths": closed_paths_found
        }
        
        platform_info['analysis_summary'] = json_identifier_info
        
        # Save to JSON file
        summary_filename = "platform_info.json"
        summary_path = os.path.join(output_dir, summary_filename)
        with open(summary_path, 'w') as f:
            json.dump(platform_info, f, indent=2)
            
        logger.info(f"Saved platform info to: {summary_path}")
        print_analysis_summary(platform_info, closed_paths_found, shape_types, output_dir, summary_path)
            
        logger.info("Platform path analysis completed successfully")
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)
    finally:
        # Clean up the logging listener
        logger.info("Shutting down logging listener")
        listener.stop()
             
if __name__ == "__main__":
    main()
