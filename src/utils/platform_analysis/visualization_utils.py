import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from utils.myfuncs.plotTools import (
    setup_platform_figure,
    setup_standard_platform_view,
    draw_platform_boundary,
    add_reference_lines,
    set_platform_limits,
    draw_shape,
    draw_aligned_shape,
    save_platform_figure
)
from utils.myfuncs.print_utils import add_platform_labels
from utils.myfuncs.shape_things import should_close_path
from utils.pyarcam.clfutil import CLFFile


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
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
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
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_platform_figure(plt, output_path)
    
    return os.path.join("composite_platforms", filename)


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
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
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
            import json
            json.dump(shape_data_list, f, indent=2)
        
        print(f"Successfully wrote shape data for height {height}mm")
        
    except Exception as e:
        print(f"Error saving shape data for clean platform at height {height}mm: {str(e)}")
        
    return png_path