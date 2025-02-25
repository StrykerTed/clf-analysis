import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

def setup_platform_figure(figsize=(15, 15)):
    """Creates and returns a new figure with standard size for platform plots"""
    return plt.figure(figsize=figsize)

def draw_platform_boundary(plt, alpha=0.5, label='Platform boundary', linestyle='--', color='k'):
    """Draws the standard 250mm x 250mm platform boundary"""
    return plt.plot([-125, 125, 125, -125, -125], 
                    [-125, -125, 125, 125, -125], 
                    f'{color}{linestyle}', alpha=alpha, label=label)

def add_reference_lines(plt, alpha=0.3, grid_alpha=0.2):
    """Adds horizontal and vertical reference lines through the origin"""
    plt.axhline(y=0, color='gray', linestyle='-', alpha=alpha)
    plt.axvline(x=0, color='gray', linestyle='-', alpha=alpha)
    plt.grid(True, alpha=grid_alpha)

def set_platform_limits(plt, margin=5):
    """Sets the standard axis limits for platform plots with optional margin"""
    plt.xlim(-125-margin, 125+margin)
    plt.ylim(-125-margin, 125+margin)
    plt.axis('equal')

def setup_clean_platform_figure(figsize=(15, 15)):
    """Creates a figure specifically for clean platform views with no chart elements"""
    fig = plt.figure(figsize=figsize)
    
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
    
    return fig

def draw_shape(plt, points, color, alpha=0.7, linewidth=0.5):
    """Draw a shape, closing the path if appropriate"""
    from utils.myfuncs.shape_things import should_close_path
    
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
            # Store midpoint
            if midpoints is not None:
                midpoints.append((xm, ym))
        else:
            # Diagonal segment, do not draw
            continue
            
def save_platform_figure(plt, output_path, dpi=300, bbox_inches='tight', pad_inches=0.1):
    """Saves the figure to the specified path with standard settings"""
    plt.savefig(output_path, dpi=dpi, bbox_inches=bbox_inches, pad_inches=pad_inches)
    plt.close()

def setup_standard_platform_view(title=None, figsize=(15, 15)):
    """Creates a standard platform view with boundary, grid, and reference lines"""
    from utils.myfuncs.print_utils import add_platform_labels
    
    fig = setup_platform_figure(figsize)
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    
    if title:
        plt.title(title)
    
    set_platform_limits(plt)
    add_platform_labels(plt)
    
    return fig