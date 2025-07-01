import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web applications
import matplotlib.pyplot as plt   
import numpy as np   
import json
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


def create_combined_excluded_identifier_platform_view(excluded_shapes_by_identifier, output_dir):
    """Create a combined platform view showing all excluded identifiers with unique colors"""
    try:
        # Skip the 'no_identifier' key if it exists
        identifiers = [id for id in excluded_shapes_by_identifier.keys() if id != 'no_identifier']
        
        if not identifiers:
            print("No excluded identifiers found for combined view")
            return None
            
        # Generate a color for each identifier
        colors = plt.cm.tab10(np.linspace(0, 1, len(identifiers)))
        identifier_colors = dict(zip(identifiers, colors))
        
        # Create figure
        setup_platform_figure()
        
        # Add standard platform elements
        draw_platform_boundary(plt)
        add_reference_lines(plt)
        
        total_shapes = 0
        height_ranges = []
        
        # Plot each identifier with its assigned color
        for identifier, color in identifier_colors.items():
            shapes_data = excluded_shapes_by_identifier[identifier]
            total_shapes += shapes_data['count']
            height_ranges.append(shapes_data['height_range'])
            
            # Draw all shapes for this identifier
            for shape_info in shapes_data['shapes']:
                if shape_info['points'] is not None:
                    points = shape_info['points']
                    if shape_info['type'] == 'point':
                        plt.plot(points[0, 0], points[0, 1], 'o', 
                                color=color, markersize=2, alpha=0.7, 
                                label=f'ID {identifier}' if identifier not in plt.gca().get_legend_handles_labels()[1] else "")
                    else:
                        draw_shape(plt, points, color)
                        # Add label only once per identifier
                        if identifier not in [t.get_text().split()[-1] for t in plt.gca().get_legend_handles_labels()[1]]:
                            plt.plot([], [], color=color, label=f'ID {identifier}')
                elif shape_info['type'] == 'circle':
                    circle = plt.Circle(
                        shape_info['center'], 
                        shape_info['radius'], 
                        color=color, 
                        fill=False, 
                        alpha=0.7
                    )
                    plt.gca().add_artist(circle)
                    # Add label only once per identifier
                    if identifier not in [t.get_text().split()[-1] for t in plt.gca().get_legend_handles_labels()[1]]:
                        plt.plot([], [], color=color, label=f'ID {identifier}')
        
        # Calculate overall height range
        if height_ranges:
            min_height = min(hr[0] for hr in height_ranges)
            max_height = max(hr[1] for hr in height_ranges)
        else:
            min_height = max_height = 0
        
        plt.title(f'Combined EXCLUDED Identifier Platform View\n'
                 f'Total Identifiers: {len(identifiers)} | Total Shapes: {total_shapes}\n'
                 f'Height Range: {min_height:.2f}mm to {max_height:.2f}mm')
        add_platform_labels(plt)
        set_platform_limits(plt)
        
        # Add legend
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
        
        # Save to identifier_views directory
        identifier_dir = os.path.join(output_dir, "identifier_views")
        os.makedirs(identifier_dir, exist_ok=True)
        filename = f'combined_excluded_identifier_platform_view.png'
        output_path = os.path.join(identifier_dir, filename)
        save_platform_figure(plt, output_path)
        
        print(f"Created combined excluded identifier view at: {output_path}")
        return os.path.join("identifier_views", filename)
        
    except Exception as e:
        print(f"Error creating combined excluded identifier platform view: {str(e)}")
        return None


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
        
        # Create transparent version with just the paths
        create_transparent_paths_view(shapes_by_identifier, output_dir)
        
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
    
    # Collect all shapes to reuse in transparent version
    all_shapes = []
    
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
                            # Store shape data for transparent version
                            all_shapes.append({
                                'points': points.copy(),
                                'color': color,
                                'folder': folder,
                                'should_close': should_close_path(points)
                            })
                            
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
    
    # Create transparent version
    create_transparent_composite_folders(all_shapes, output_dir, height, fill_closed)
    
    return os.path.join("composite_platforms", filename)


def create_transparent_composite_folders(shapes, output_dir, height, fill_closed=False):
    """Create a transparent composite view with paths from all folders without chart elements"""
    try:
        # Create figure with transparent background
        fig = plt.figure(figsize=(15, 15), facecolor="none")
        ax = plt.gca()
        ax.set_position([0, 0, 1, 1])  # Remove all margins
        ax.patch.set_alpha(0)  # Make axes background transparent
        
        # Set platform limits
        plt.xlim(-125, 125)
        plt.ylim(-125, 125)
        
        # Turn off all chart elements
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        plt.axis('off')
        
        # Draw all shapes
        for shape in shapes:
            points = shape['points']
            color = shape['color']
            
            if fill_closed and shape['should_close']:
                polygon = Polygon(points, 
                              facecolor=color, 
                              edgecolor=color, 
                              alpha=0.5)
                plt.gca().add_patch(polygon)
            else:
                draw_shape(plt, points, color)
        
        plt.axis('equal')  # Ensure perfect square
        
        # Save the transparent plot
        filename = f'transparent_composite_folders_{height}mm.png'
        output_path = os.path.join(output_dir, "composite_platforms", filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_platform_figure(plt, output_path, pad_inches=0, bbox_inches='tight')
        plt.close()
        
        print(f"Created transparent composite folders view at: {output_path}")
        return os.path.join("composite_platforms", filename)
        
    except Exception as e:
        print(f"Error creating transparent composite folders view: {str(e)}")
        return None


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


def process_layer_data(clf_info, height, colors):
    """Helper function to process a single layer and extract shape data.
    Used by create_clean_platform for parallel processing.
    Now includes hole detection using geometric containment."""
    shape_data_list = []
    
    try:
        part = CLFFile(clf_info['path'])
        if not hasattr(part, 'box'):
            return shape_data_list
            
        layer = part.find(height)
        if layer is None:
            return shape_data_list
            
        if hasattr(layer, 'shapes'):
            shapes = list(layer.shapes)
            
            # First pass: process all shapes as potential exteriors
            processed_shapes = []
            for i, shape in enumerate(shapes):
                color = colors.get(clf_info['name'], 'gray')
                shape_identifier = None
                if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                    shape_identifier = shape.model.id
                    
                if hasattr(shape, 'points') and shape.points:
                    points = shape.points[0]  # Only process the first path (exterior boundary)
                    if isinstance(points, np.ndarray) and points.shape[0] >= 1 and points.shape[1] >= 2:
                        should_close = False
                        try:
                            should_close = should_close_path(points)
                            if hasattr(should_close, 'item'):
                                should_close = should_close.item()
                        except Exception as e:
                            print(f"Error in should_close_path for {clf_info['name']}: {str(e)}")
                            should_close = False
                        
                        processed_shapes.append({
                            'index': i,
                            'points': points,
                            'identifier': shape_identifier,
                            'color': color,
                            'should_close': should_close
                        })
                        
                elif hasattr(shape, 'radius') and hasattr(shape, 'center'):
                    # Handle circles (add them directly as they don't have holes in this context)
                    shape_data = {
                        'type': 'circle',
                        'shape_type': 'exterior',  # Circles are always exterior
                        'center': shape.center.tolist(),
                        'radius': shape.radius,
                        'color': color,
                        'clf_name': clf_info['name'],
                        'clf_folder': clf_info['folder'],
                        'fill_closed': True,
                        'identifier': shape_identifier,
                        'parent_shape_id': None,
                        'is_hole': False
                    }
                    shape_data_list.append(shape_data)
            
            # Second pass: detect holes using geometric containment
            hole_relationships = []
            for i, shape1 in enumerate(processed_shapes):
                for j, shape2 in enumerate(processed_shapes):
                    if i == j:
                        continue
                    
                    # Check if shape2 is inside shape1 (shape2 is a hole in shape1)
                    if is_shape_inside_shape(shape2['points'], shape1['points']):
                        hole_relationships.append({
                            'hole_index': j,
                            'parent_index': i,
                            'hole_id': shape2['identifier'],
                            'parent_id': shape1['identifier']
                        })
                        print(f"  Found hole: Shape {j} (ID:{shape2['identifier']}) inside Shape {i} (ID:{shape1['identifier']})")
            
            # Third pass: create shape data with hole information
            hole_indices = set(rel['hole_index'] for rel in hole_relationships)
            
            for i, shape_info in enumerate(processed_shapes):
                is_hole = i in hole_indices
                parent_info = None
                
                if is_hole:
                    # Find parent information
                    for rel in hole_relationships:
                        if rel['hole_index'] == i:
                            parent_info = rel
                            break
                
                shape_data = {
                    'type': 'path',
                    'shape_type': 'hole' if is_hole else 'exterior',
                    'points': shape_info['points'].tolist(),
                    'color': shape_info['color'],
                    'clf_name': clf_info['name'],
                    'clf_folder': clf_info['folder'],
                    'fill_closed': True,  # Set default, will be updated by main function
                    'should_close': shape_info['should_close'],
                    'identifier': shape_info['identifier'],
                    'parent_shape_id': parent_info['parent_id'] if parent_info else None,
                    'parent_shape_index': parent_info['parent_index'] if parent_info else None,
                    'is_hole': is_hole
                }
                shape_data_list.append(shape_data)
                
            print(f"  Processed {len(processed_shapes)} shapes, found {len(hole_relationships)} holes in {clf_info['name']}")
                        
    except Exception as e:
        print(f"Error processing {clf_info['name']} at height {height}mm: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return shape_data_list


def is_shape_inside_shape(inner_points, outer_points):
    """
    Check if inner_points shape is geometrically contained within outer_points shape
    
    Args:
        inner_points: numpy array of points for the inner shape
        outer_points: numpy array of points for the outer shape
        
    Returns:
        bool: True if inner shape is inside outer shape
    """
    try:
        import numpy as np
        from matplotlib.path import Path
        
        # Create a path from the outer shape
        outer_path = Path(outer_points)
        
        # Check if all points of the inner shape are inside the outer path
        # We'll check a few sample points to be efficient
        sample_indices = np.linspace(0, len(inner_points)-1, min(10, len(inner_points)), dtype=int)
        sample_points = inner_points[sample_indices]
        
        # All sample points should be inside the outer shape
        inside_checks = outer_path.contains_points(sample_points)
        
        # Return True if most points are inside (allowing for edge cases)
        return np.sum(inside_checks) >= len(inside_checks) * 0.8
        
    except Exception as e:
        print(f"Error in geometric containment check: {e}")
        return False


def create_transparent_paths_view(shapes_by_identifier, output_dir):
    """Create a transparent PNG with just the path data from all identifiers, without any chart elements."""
    try:
        # Skip the 'no_identifier' key if it exists
        identifiers = [id for id in shapes_by_identifier.keys() if id != 'no_identifier']
        
        if not identifiers:
            print("No identifiers found for transparent paths view")
            return None
            
        # Generate a color for each identifier
        colors = plt.cm.tab10(np.linspace(0, 1, len(identifiers)))
        identifier_colors = dict(zip(identifiers, colors))
        
        # Create figure with transparent background
        fig = plt.figure(figsize=(15, 15), facecolor="none")
        ax = plt.gca()
        ax.set_position([0, 0, 1, 1])  # Remove all margins
        ax.patch.set_alpha(0)  # Make axes background transparent
        
        # Set platform limits
        plt.xlim(-125, 125)
        plt.ylim(-125, 125)
        
        # Turn off all chart elements
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        plt.axis('off')
        
        # Plot each identifier with its assigned color
        for identifier, color in identifier_colors.items():
            shapes_data = shapes_by_identifier[identifier]
            
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
        
        plt.axis('equal')  # Ensure perfect square
        
        # Save the transparent plot
        identifier_dir = os.path.join(output_dir, "identifier_views")
        os.makedirs(identifier_dir, exist_ok=True)
        filename = f'transparent_all_pathdata.png'
        output_path = os.path.join(identifier_dir, filename)
        save_platform_figure(plt, output_path, pad_inches=0, bbox_inches='tight')
        plt.close()
        
        # ALSO create a 2500x2500 version
        create_transparent_paths_view_2500px(shapes_by_identifier, output_dir)
        
        print(f"Created transparent paths view at: {output_path}")
        return os.path.join("identifier_views", filename)
        
    except Exception as e:
        print(f"Error creating transparent paths view: {str(e)}")
        return None
        

def create_transparent_paths_view_2500px(shapes_by_identifier, output_dir):
    """Create a 2500x2500 transparent PNG with just the path data from all identifiers, without chart elements."""
    try:
        # Skip the 'no_identifier' key if it exists
        identifiers = [id for id in shapes_by_identifier.keys() if id != 'no_identifier']
        
        if not identifiers:
            print("No identifiers found for 2500px transparent paths view")
            return None
            
        # Generate a color for each identifier
        colors = plt.cm.tab10(np.linspace(0, 1, len(identifiers)))
        identifier_colors = dict(zip(identifiers, colors))
        
        # Create figure with transparent background - size adjusted for 2500px output
        # 8.33 inches * 300 DPI = ~2500px
        fig = plt.figure(figsize=(8.33, 8.33), facecolor="none")
        ax = plt.gca()
        ax.set_position([0, 0, 1, 1])  # Remove all margins
        ax.patch.set_alpha(0)  # Make axes background transparent
        
        # Set platform limits - still representing the same 250mm x 250mm area
        plt.xlim(-125, 125)
        plt.ylim(-125, 125)
        
        # Turn off all chart elements
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        plt.axis('off')
        
        # Plot each identifier with its assigned color
        for identifier, color in identifier_colors.items():
            shapes_data = shapes_by_identifier[identifier]
            
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
        
        plt.axis('equal')  # Ensure perfect square
        
        # Save the transparent plot
        identifier_dir = os.path.join(output_dir, "identifier_views")
        os.makedirs(identifier_dir, exist_ok=True)
        filename = f'transparent_all_pathdata_250mmx250mm_2500px.png'
        output_path = os.path.join(identifier_dir, filename)
        save_platform_figure(plt, output_path, pad_inches=0, bbox_inches='tight')
        plt.close()
        
        print(f"Created 2500px transparent paths view at: {output_path}")
        return os.path.join("identifier_views", filename)
        
    except Exception as e:
        print(f"Error creating 2500px transparent paths view: {str(e)}")
        return None


def create_clean_platform(clf_files, output_dir, height=1.0, fill_closed=False, alignment_style_only=False, save_clean_png=True):
    """Create a clean platform view without any chart elements, just shapes, and save raw path data.
    Processes files sequentially to avoid nested multiprocessing conflicts."""
    import os
    import json
    
    # Define colors dictionary
    colors = {
        'Part.clf': 'blue',
        'WaferSupport.clf': 'red',
        'Net.clf': 'green'
    }
    
    # Process all CLF files sequentially (avoiding nested multiprocessing)
    shape_data_list = []
    for clf_info in clf_files:
        try:
            result = process_layer_data(clf_info, height, colors)
            shape_data_list.extend(result)
        except Exception as e:
            print(f"Error processing {clf_info['name']} at height {height}mm: {str(e)}")
    
    # Update fill_closed for all shapes
    for shape_data in shape_data_list:
        shape_data['fill_closed'] = fill_closed
    
    # Only create plot if save_clean_png is True
    if save_clean_png:
        # If alignment_style_only, declare midpoints list
        if alignment_style_only:
            midpoints = []
            
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
        
        # Draw all shapes
        for shape_data in shape_data_list:
            if shape_data['type'] == 'path' and 'points' in shape_data:
                points = np.array(shape_data['points'])
                color = shape_data['color']
                
                if alignment_style_only:
                    draw_aligned_shape(plt, points, color, midpoints=midpoints)
                else:
                    if fill_closed and shape_data.get('should_close', False):
                        polygon = Polygon(points, facecolor='black', edgecolor=color, alpha=0.5)
                        plt.gca().add_patch(polygon)
                    else:
                        draw_shape(plt, points, color)
            elif shape_data['type'] == 'circle':
                circle = plt.Circle(shape_data['center'], shape_data['radius'], 
                                   color=shape_data['color'], fill=False, alpha=0.7)
                plt.gca().add_artist(circle)
                
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
        
        # Add debugging information
        print(f"\nWriting shape data to: {data_output_path}")
        print(f"Number of shapes being written: {len(shape_data_list)}")
        
        with open(data_output_path, 'w') as f:
            json.dump(shape_data_list, f, indent=2)
        
        print(f"Successfully wrote shape data for height {height}mm")
        
    except Exception as e:
        print(f"Error saving shape data for clean platform at height {height}mm: {str(e)}")
        
    return png_path


def create_combined_holes_platform_view(clf_files, output_dir, height=134.0):
    """Create a platform view showing all detected holes across all CLF files at a specific height.
    Similar to combined_identifier_platform_view but focuses on holes detection."""
    try:
        print(f"Creating combined holes platform view at {height}mm...")
        
        # Define colors for different CLF files
        colors = {
            'Part.clf': '#2E86AB',
            'WaferSupport.clf': '#A23B72', 
            'Net.clf': '#F18F01'
        }
        
        all_exteriors = []
        all_holes = []
        holes_stats = {
            'total_files': len(clf_files),
            'files_with_holes': 0,
            'total_exteriors': 0,
            'total_holes': 0,
            'file_details': []
        }
        
        # Process each CLF file to find holes
        for clf_info in clf_files:
            try:
                part = CLFFile(clf_info['path'])
                layer = part.find(height)
                
                if layer is None or not hasattr(layer, 'shapes'):
                    continue
                
                shapes = list(layer.shapes)
                color = colors.get(clf_info['name'], '#666666')
                exteriors_in_file = 0
                holes_in_file = 0
                
                # Process each shape pair to find holes using geometric containment
                for i, shape1 in enumerate(shapes):
                    if not hasattr(shape1, 'points') or not shape1.points:
                        continue
                        
                    # Get identifier for shape1
                    identifier1 = "unknown"
                    if hasattr(shape1, 'model') and hasattr(shape1.model, 'id'):
                        identifier1 = str(shape1.model.id)
                    
                    # Shape1 first path is always an exterior
                    exterior_points = shape1.points[0]
                    exterior_info = {
                        'type': 'exterior',
                        'points': exterior_points,
                        'identifier': identifier1,
                        'clf_file': clf_info['name'],
                        'clf_folder': clf_info['folder'],
                        'color': color,
                        'shape_index': i
                    }
                    all_exteriors.append(exterior_info)
                    exteriors_in_file += 1
                    
                    # Look for other shapes that might be holes inside this shape
                    for j, shape2 in enumerate(shapes):
                        if i == j:  # Skip same shape
                            continue
                        
                        if not hasattr(shape2, 'points') or not shape2.points:
                            continue
                        
                        # Get identifier for shape2  
                        identifier2 = "unknown"
                        if hasattr(shape2, 'model') and hasattr(shape2.model, 'id'):
                            identifier2 = str(shape2.model.id)
                        
                        # Check if shape2 is inside shape1 using geometric containment
                        shape2_points = shape2.points[0]  # Use first path of shape2
                        
                        if is_shape_inside_shape(shape2_points, exterior_points):
                            print(f"    Found hole: Shape {j} (ID:{identifier2}) inside Shape {i} (ID:{identifier1}) in {clf_info['name']}")
                            
                            hole_info = {
                                'type': 'hole',
                                'points': shape2_points,
                                'identifier': identifier2,
                                'clf_file': clf_info['name'],
                                'clf_folder': clf_info['folder'],
                                'color': color,
                                'shape_index': j,
                                'parent_shape_index': i,
                                'parent_identifier': identifier1
                            }
                            all_holes.append(hole_info)
                            holes_in_file += 1
                
                # Add file statistics
                if holes_in_file > 0:
                    holes_stats['files_with_holes'] += 1
                
                holes_stats['file_details'].append({
                    'filename': clf_info['name'],
                    'folder': clf_info['folder'],
                    'exteriors': exteriors_in_file,
                    'holes': holes_in_file
                })
                
                print(f"  - {clf_info['name']}: {exteriors_in_file} exteriors, {holes_in_file} holes")
                
            except Exception as e:
                print(f"Error processing {clf_info['name']} for holes: {e}")
                continue
        
        # Update summary statistics
        holes_stats['total_exteriors'] = len(all_exteriors)
        holes_stats['total_holes'] = len(all_holes)
        
        print(f"Holes analysis summary:")
        print(f"  - Total files: {holes_stats['total_files']}")
        print(f"  - Files with holes: {holes_stats['files_with_holes']}")
        print(f"  - Total exterior shapes: {holes_stats['total_exteriors']}")
        print(f"  - Total holes found: {holes_stats['total_holes']}")
        
        # Create the visualization if we found any shapes
        if all_exteriors or all_holes:
            # Create figure
            setup_platform_figure(figsize=(15, 15))
            
            # Add standard platform elements
            draw_platform_boundary(plt)
            add_reference_lines(plt)
            
            # Draw exterior shapes (semi-transparent)
            for ext_shape in all_exteriors:
                points = ext_shape['points']
                color = ext_shape['color']
                
                # Draw as a filled polygon with low alpha
                polygon = Polygon(points, facecolor=color, alpha=0.3, 
                                edgecolor=color, linewidth=1)
                plt.gca().add_patch(polygon)
            
            # Draw holes (bright red for high visibility)
            for hole in all_holes:
                points = hole['points']
                
                # Draw holes as solid red polygons for visibility
                hole_polygon = Polygon(points, facecolor='red', alpha=0.8, 
                                     edgecolor='darkred', linewidth=2)
                plt.gca().add_patch(hole_polygon)
            
            # Create legend
            legend_elements = []
            for clf_name, color in colors.items():
                if any(ext['clf_file'] == clf_name for ext in all_exteriors):
                    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, alpha=0.3, 
                                                       edgecolor=color, label=f'{clf_name} (Exteriors)'))
            
            if all_holes:
                legend_elements.append(plt.Rectangle((0,0),1,1, facecolor='red', alpha=0.8, 
                                                   edgecolor='darkred', label='Holes'))
            
            if legend_elements:
                plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.)
            
            plt.title(f'Combined Holes Platform View at {height}mm\n'
                     f'Total Files: {holes_stats["total_files"]} | '
                     f'Files with Holes: {holes_stats["files_with_holes"]}\n'
                     f'Exterior Shapes: {holes_stats["total_exteriors"]} | '
                     f'Holes Found: {holes_stats["total_holes"]}')
            
            add_platform_labels(plt)
            set_platform_limits(plt)
            
            # Save the holes view
            holes_dir = os.path.join(output_dir, "holes_views")
            os.makedirs(holes_dir, exist_ok=True)
            filename = f'combined_holes_platform_view_{height}mm.png'
            output_path = os.path.join(holes_dir, filename)
            save_platform_figure(plt, output_path)
            
            print(f"Created combined holes view at: {output_path}")
            return os.path.join("holes_views", filename), holes_stats
        
        else:
            print("No shapes found for holes visualization")
            return None, holes_stats
            
    except Exception as e:
        print(f"Error creating combined holes platform view: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None