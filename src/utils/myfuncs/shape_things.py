import numpy as np


def should_close_path(points):
    """Determine if a path should be closed based on endpoints and geometry"""
    if len(points) < 3:
        return False
        
    # Calculate distance between start and end points
    start_point = points[0]
    end_point = points[-1]
    gap = np.linalg.norm(end_point - start_point)
    
    # Calculate overall path length for comparison
    segments = points[1:] - points[:-1]
    total_length = np.sum(np.sqrt(np.sum(segments**2, axis=1)))
    
    # If gap is small relative to total path length, close it
    return gap < (total_length * 0.05)  # 5% threshold