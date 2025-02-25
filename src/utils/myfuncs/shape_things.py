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