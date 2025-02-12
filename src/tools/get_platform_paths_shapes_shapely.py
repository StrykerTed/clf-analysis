import os
import sys
import matplotlib.pyplot as plt   
import numpy as np      
import json  # For JSON handling
from matplotlib.patches import Polygon  # For polygon plotting

# Add parent directory to path to find setup_paths
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import setup_paths

from utils.pyarcam.clfutil import CLFFile

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

def create_non_identifier_platform_view(non_id_shapes, output_dir):
    """Create a platform view showing all shapes that don't have identifiers"""
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
        
        plt.title(f'Non-Identifier Shapes Platform View\n'
                 f'Total Shapes: {len(non_id_shapes)}')
        add_platform_labels(plt)
        plt.axis('equal')
        
        plt.xlim(-130, 130)
        plt.ylim(-130, 130)
        
        non_id_dir = os.path.join(output_dir, "non_identifier_views")
        os.makedirs(non_id_dir, exist_ok=True)
        filename = f'non_identifier_platform_view.png'
        output_path = os.path.join(non_id_dir, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return os.path.join("non_identifier_views", filename)
        
    except Exception as e:
        print(f"Error creating non-identifier platform view: {str(e)}")
        return None
    
def draw_aligned_shape(plt, points, color, midpoints=None, alpha=0.7, linewidth=0.5, tol=1e-6):
    """Draw only horizontal or vertical segments between points in a path."""
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dx = x1 - x0
        dy = y1 - y0
        if abs(dx) < tol and abs(dy) < tol:
            # Zero-length segment, skip
            continue
        elif abs(dx) < tol or abs(dy) < tol:
            # Vertical or horizontal segment
            plt.plot([x0, x1], [y0, y1], '-', color=color, linewidth=linewidth, alpha=1)
            # Compute midpoint
            xm = (x0 + x1) / 2
            ym = (y0 + y1) / 2
            # Mark midpoint with black dot
            # plt.plot(xm, ym, 'ko', markersize=1, alpha=1)
            # Store midpoint
            if midpoints is not None:
                midpoints.append((xm, ym))
        else:
            # Diagonal segment, do not draw
            continue


def remove_colinear_and_small_segments(points, colinear_tolerance=1e-7, min_segment_length=0.1):
    cleaned = []
    cleaned.append(points[0])
    for i in range(1, len(points) - 1):
        p_prev = points[i - 1]
        p_curr = points[i]
        p_next = points[i + 1]
        v1 = p_curr - p_prev
        v2 = p_next - p_curr
        cross = v1[0]*v2[1] - v1[1]*v2[0]
        length_v1 = np.linalg.norm(v1)
        # Remove point if nearly colinear or if the segment is too short
        if abs(cross) < colinear_tolerance or length_v1 < min_segment_length:
            continue
        cleaned.append(p_curr)
    cleaned.append(points[-1])
    return np.array(cleaned)

def has_mostly_right_angles(points, angle_tolerance=15, right_angle_threshold=0.75):
    if len(points) < 3:
        return False

    # Remove colinear points and very short segments before checking angles
    points = remove_colinear_and_small_segments(points)
    if len(points) < 4:
        return False

    angles = []
    n_points = len(points)
    for i in range(n_points):
        p1 = points[i]
        p2 = points[(i + 1) % n_points]
        p3 = points[(i + 2) % n_points]
        v1 = p2 - p1
        v2 = p3 - p2
        if np.all(v1 == 0) or np.all(v2 == 0):
            continue
        dot_product = np.dot(v1, v2)
        norms = np.linalg.norm(v1) * np.linalg.norm(v2)
        if norms == 0:
            continue
        cos_angle = dot_product / norms
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.degrees(np.arccos(cos_angle))
        angles.append(angle)

    if not angles:
        return False

    right_angles = sum(1 for angle in angles if abs(angle - 90) < angle_tolerance)
    right_angle_percentage = right_angles / len(angles)
    return right_angle_percentage >= right_angle_threshold

def create_clean_platform(clf_files, output_dir, height=1.0, fill_closed=False, alignment_style_only=False, save_clean_png=False):
    """Create a clean platform view without any chart elements, just shapes, and save raw path data."""
    # Initialize list to store shape data
    shape_data_list = []
    
    # If alignment_style_only, declare midpoints list
    if alignment_style_only:
        midpoints = []
    
    # Only create plot if save_clean_png is True
    if save_clean_png:
        # Create figure with equal aspect ratio
        fig = plt.figure(figsize=(15, 15))
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
        plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0)
        plt.close()
        png_path = os.path.join("clean_platforms", filename)
    else:
        png_path = None
    
    # Save the shape data to a file
    try:
        # Create 'imagePathRawData' directory if it doesn't exist
        raw_data_dir = os.path.join(output_dir, "imagePathRawData")
        os.makedirs(raw_data_dir, exist_ok=True)
    
        # Construct filename
        data_filename = f'platform_layer_pathdata_{height}mm.json'
        data_output_path = os.path.join(raw_data_dir, data_filename)
        
        # Write the data to file
        with open(data_output_path, 'w') as f:
            json.dump(shape_data_list, f, indent=2)
        
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
            # Draw platform boundary and axes
            plt.plot([-125, 125, 125, -125, -125], 
                    [-125, -125, 125, 125, -125], 
                    'r--', alpha=0.3, label='Platform boundary (-125 to +125mm)')
            
            plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
            
            plt.title(f'Layer at Height: {height:.3f}mm\nSource: {clf_info["name"]} in {clf_info["folder"]}')
            plt.xlabel('X (mm)')
            plt.ylabel('Y (mm)')
        
            plt.grid(True)
            plt.legend()
            
            plt.xlim(-130, 130)
            plt.ylim(-130, 130)
            plt.axis('equal')
            
            sanitized_folder = clf_info["folder"].replace('/', '_').replace('\\', '_')
            filename = f'layer_{height:.3f}mm_{clf_info["name"]}_{sanitized_folder}.png'
            
            output_path = os.path.join(output_dir, "layer_partials", filename)
            plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
            plt.close()
            
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
    
def draw_shape(plt, points, color, alpha=0.7, linewidth=0.5):
    """Draw a shape, closing the path if appropriate"""
    if len(points) < 2:
        plt.plot(points[0, 0], points[0, 1], 'o', 
                color=color, markersize=2, alpha=alpha)
        return
        
    # Draw the original points
    plt.plot(points[:, 0], points[:, 1], '-', 
            color=color, linewidth=linewidth, alpha=alpha)
    
    # If should be closed, add closure line
    if should_close_path(points):
        # Draw closing line
        closure_points = np.vstack([points[-1], points[0]])
        plt.plot(closure_points[:, 0], closure_points[:, 1], '-', 
                color=color, linewidth=linewidth, alpha=alpha)

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
        plt.axis('equal')
        
        plt.xlim(-130, 130)
        plt.ylim(-130, 130)
        
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

def create_platform_composite_with_folders(clf_files, output_dir, height=1.0, fill_closed=False):
    """Create a composite view with unique colors per folder and a legend"""
    plt.figure(figsize=(15, 15))
    
    # Get unique folders and assign colors using a colormap
    folders = sorted(list(set(clf_info['folder'] for clf_info in clf_files)))
    colors = plt.cm.tab20(np.linspace(0, 1, len(folders)))  # Use tab20 for distinct colors
    folder_colors = dict(zip(folders, colors))
    
    # Platform boundary
    plt.plot([-125, 125, 125, -125, -125], 
            [-125, -125, 125, 125, -125], 
            'k--', alpha=0.5, label='Platform boundary')
    
    plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    plt.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
    plt.grid(True, alpha=0.2)
    
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
   
    plt.xlim(-130, 130)
    plt.ylim(-130, 130)
    plt.axis('equal')
    
    # Create legend with folder names
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    
    filename = f'platform_composite_folders_{height}mm.png'
    output_path = os.path.join(output_dir, "composite_platforms", filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    
    return os.path.join("composite_platforms", filename)

def create_platform_composite(clf_files, output_dir, height=1.0, fill_closed=False):
    """Create a composite view of all shapes at specified height"""
    plt.figure(figsize=(15, 15))
    
    plt.plot([-125, 125, 125, -125, -125], 
            [-125, -125, 125, 125, -125], 
            'k--', alpha=0.5, label='Platform boundary')
    
    plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    plt.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
    plt.grid(True, alpha=0.2)
    
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
                                # Draw unfilled shape as before
                                draw_shape(plt, points, color)
                                
                            if not shapes_found:
                                plt.plot([], [], color=color, label=clf_info['name'])
                                shapes_found = True
            
        except Exception as e:
            print(f"Error processing {clf_info['name']} for platform view: {str(e)}")
    
    plt.title(f'Platform Composite View at Height {height}mm')
    add_platform_labels(plt)
   
    plt.xlim(-130, 130)
    plt.ylim(-130, 130)
    plt.axis('equal')
    
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())
    
    filename = f'platform_composite_{height}mm.png'
    output_path = os.path.join(output_dir, "composite_platforms", filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    
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
    wanted_layer_heights = list(range(1, 201))
    
    try:
        draw_points = 'y'
        draw_lines = 'y'
        fill_closed = input("Fill in closed shapes? (y/n): ").lower().startswith('y')
        exclude_folders = 'y'
        save_layer_partials = input("Save Layer Partials? (y/n): ").lower().startswith('y') 
        save_clean = input("Save Clean Platforms? (y/n): ").lower().startswith('y')
        save_clean_png = input("Save Clean Platforms PNG? (y/n): ").lower().startswith('y')
                # Ask for alignment style images only
        alignment_style_only = input("Alignment style images only? (y/n): ").lower().startswith('y')
        
        # Only ask for height mode if saving clean platforms
        clean_heights = None
        if save_clean:
            height_choice = input("Want full range of clean platform images or a sample? (full/sample): ").lower()
            if height_choice == 'full':
                print("Will process full range of heights at 0.05mm intervals")
            else:
                print("Will process sample heights only")
        
        exclusion_patterns = load_exclusion_patterns(os.path.dirname(os.path.abspath(__file__))) if exclude_folders else []
        
        if exclude_folders:
            print("\nExcluding folders containing these patterns:")
            for pattern in exclusion_patterns:
                print(f"- {pattern}")
        
        base_dir = os.getcwd()
        abpfoldername = "preprocess build-271152.abp"
        build_dir = os.path.join(base_dir, abpfoldername)
        output_dir = create_output_folder(abpfoldername, base_dir, save_layer_partials, alignment_style_only)
        
        # Create clean_platforms directory if needed
        if save_clean:
            clean_platforms_dir = os.path.join(output_dir, "clean_platforms")
            os.makedirs(clean_platforms_dir, exist_ok=True)
            print(f"Created clean platforms directory: {clean_platforms_dir}")
        
        print(f"\nLooking for build directory at: {build_dir}")
        if not os.path.exists(build_dir):
            print("Build directory not found!")
            return
            
        print("\nFinding CLF files...")
        all_clf_files = find_clf_files(build_dir)
        
        # Filter CLF files based on exclusion patterns
        if exclude_folders:
            clf_files = []
            for clf_info in all_clf_files:
                should_skip = should_skip_folder(clf_info['folder'], exclusion_patterns)
                if should_skip:
                    print(f"Skipping file: {clf_info['name']} in {clf_info['folder']}")
                else:
                    clf_files.append(clf_info)
                    print(f"Keeping file: {clf_info['name']} in {clf_info['folder']}")
                    
            excluded_count = len(all_clf_files) - len(clf_files)
            print(f"Found {len(all_clf_files)} total CLF files")
            print(f"Excluded {excluded_count} files based on folder patterns")
            print(f"Processing {len(clf_files)} CLF files")
        else:
            clf_files = all_clf_files
            print(f"Found {len(clf_files)} CLF files")
        
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
                    print(f"Creating clean platform view at height {height}mm...")
                    clean_file = create_clean_platform(
                        clf_files, 
                        output_dir,
                        height=height,
                        fill_closed=fill_closed,
                        alignment_style_only=alignment_style_only,
                        save_clean_png=save_clean_png
                    )

                    if save_clean_png and clean_file:
                        platform_info["clean_platforms"].append({
                            "height": height,
                            "filename": clean_file
                        })
                        print(f"Created clean platform at {height}mm: {clean_file}")
                    elif not save_clean_png:
                        print(f"Skipped clean platform PNG creation at {height}mm")
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
            
        print_analysis_summary(platform_info, closed_paths_found, shape_types, output_dir, summary_path)
            
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
             
if __name__ == "__main__":
    main()
