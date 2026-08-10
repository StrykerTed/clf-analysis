import matplotlib
# Ensure we use non-interactive backend for web applications
if matplotlib.get_backend() != 'Agg':
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

# Import platform configuration
from config import PLATFORM_HALF_SIZE_MM

def setup_platform_figure(figsize=(15, 15)):
    """Creates and returns a new figure with standard size for platform plots"""
    return plt.figure(figsize=figsize)

def draw_platform_boundary(plt, alpha=0.5, label='Platform boundary', linestyle='--', color='k'):
    """Draws the platform boundary using configured platform size"""
    half_size = PLATFORM_HALF_SIZE_MM
    return plt.plot([-half_size, half_size, half_size, -half_size, -half_size], 
                    [-half_size, -half_size, half_size, half_size, -half_size], 
                    f'{color}{linestyle}', alpha=alpha, label=label)

def add_reference_lines(plt, alpha=0.3, grid_alpha=0.2):
    """Adds horizontal and vertical reference lines through the origin"""
    plt.axhline(y=0, color='gray', linestyle='-', alpha=alpha)
    plt.axvline(x=0, color='gray', linestyle='-', alpha=alpha)
    plt.grid(True, alpha=grid_alpha)

def set_platform_limits(plt, margin=5):
    """Sets the standard axis limits for platform plots with optional margin"""
    # Set the limit value with margin
    limit = PLATFORM_HALF_SIZE_MM + margin
    
    # Set equal aspect ratio first (this is more important for visualization correctness)
    plt.gca().set_aspect('equal', adjustable='box')
    
    # Then set the limits
    plt.xlim(-limit, limit)
    plt.ylim(-limit, limit)

def setup_clean_platform_figure(figsize=(15, 15)):
    """Creates a figure specifically for clean platform views with no chart elements"""
    fig = plt.figure(figsize=figsize)
    
    # Remove all margins and spacing
    ax = plt.gca()
    ax.set_position([0, 0, 1, 1])
    
    # Set exact limits for platform size
    half_size = PLATFORM_HALF_SIZE_MM
    plt.xlim(-half_size, half_size)
    plt.ylim(-half_size, half_size)
    
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


class PlateImageSizeError(RuntimeError):
    """A plate-registered image was not saved at the size its filename promises."""


def save_plate_registered_figure(plt, output_path, expected_px=2100, dpi=300):
    """Save a plate-registered image, and prove it kept the promise in its name.

    These filenames declare an exact geometry - ``..._210mmx210mm_2100px.png`` -
    and the 3D floor takes that at its word, texturing a 210mm plane with the
    file. So a wrong size is not cosmetic: every path drawn on the plate is
    misregistered by whatever the discrepancy is, and it looks like a
    calibration fault rather than a plotting one.

    Two ways the promise has actually been broken, both of which reached the UI:

    * ``plt.axis('equal')`` refits the limits to the data, and
      ``bbox_inches='tight'`` then crops to whatever the paths spanned - so the
      output size depended on where that build's parts sat on the plate.
    * pyplot's current figure is process-global. With concurrent builds, a save
      here captured another render entirely: on 10 Aug 2026 an identifier view
      came out 4426x3831 holding a Combined Holes figure.

    Neither announced itself. The file was written, the run reported success,
    and the defect surfaced hours later as a wrong-looking floor. A saved image
    can be measured in a millisecond, so measure it.

    A mismatched file is quarantined rather than deleted - renamed so that the
    resolver's ``^transparent_all_pathdata_\\d+mmx\\d+mm_\\d+px\\.png$`` pattern
    can no longer match it, which stops it being served while keeping the
    evidence for diagnosis.
    """
    import os

    from PIL import Image

    plt.savefig(output_path, dpi=dpi, bbox_inches=None, pad_inches=0)
    plt.close()

    with Image.open(output_path) as img:
        width, height = img.size

    if (width, height) == (expected_px, expected_px):
        return output_path

    quarantined = f"{output_path}.INVALID-{width}x{height}.png"
    try:
        os.replace(output_path, quarantined)
    except OSError:
        quarantined = None

    raise PlateImageSizeError(
        f"{os.path.basename(output_path)} promises {expected_px}x{expected_px} "
        f"but was saved {width}x{height}. The 3D floor textures a 210mm plane "
        f"with this file, so serving it would misregister every path on the "
        f"plate. Most likely causes: a stray axis('equal')/bbox_inches='tight', "
        f"or another figure was globally current when this was saved. "
        + (f"Quarantined as {os.path.basename(quarantined)}."
           if quarantined else "Could not quarantine the file.")
    )

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