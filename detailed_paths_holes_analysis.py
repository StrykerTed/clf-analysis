#!/usr/bin/env python3
"""
Detailed Paths & Holes Analysis
--------------------------------
Extracts exhaustive information about every shape, its paths, and inferred holes
at a single specified layer height for a given build.

Features:
 - Robust build path resolution (internal repo abp_contents OR external MIDAS folder)
 - Detailed per-shape + per-path metrics (area, winding, bbox, closure, center)
 - Hole classification (exterior vs interior paths) with confidence flags
 - Additional hole metrics (area ratio to exterior, aspect ratio, bounding box stats)
 - Summary JSON + rich per-shape structure + quick text summary
 - PNG visualization (optional) reusing baseline color semantics (exterior vs holes)

Usage (CLI):
  python detailed_paths_holes_analysis.py --build-id 271726 --height 47.15 \
      --main-build-folder "/Users/ted.tedford/Documents/MIDAS" \
      --output-root my_outputs/detailed_paths_holes \
      --png

Defaults are set to the user's requested build/height so running without args is fine.
"""

from __future__ import annotations
import os
import sys
import json
import math
import argparse
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import setup_paths  # noqa: F401  (side effects: adjusts sys.path for utils)

from utils.pyarcam.clfutil import CLFFile  # type: ignore
from utils.myfuncs.file_utils import find_clf_files, should_skip_folder, load_exclusion_patterns  # type: ignore
from utils.myfuncs.shape_things import should_close_path  # type: ignore

try:
    # Optional plotting imports (only if --png)
    import matplotlib
    matplotlib.use('Agg')  # headless
    import matplotlib.pyplot as plt  # noqa: F401
    from utils.myfuncs.plotTools import (
        draw_platform_boundary,
        add_reference_lines,
        set_platform_limits,
        draw_shape,
        save_platform_figure
    )  # type: ignore
    from utils.myfuncs.print_utils import add_platform_labels  # type: ignore
    PLOTTING_AVAILABLE = True
except Exception:
    PLOTTING_AVAILABLE = False


# --------------------------------------------------------------------------------------
# Data Classes
# --------------------------------------------------------------------------------------

@dataclass
class PathMetrics:
    path_index: int
    num_points: int
    is_closed: bool
    area: float
    winding: str
    center: Tuple[float, float]
    bounds: Dict[str, float]
    bbox_aspect_ratio: Optional[float]
    bbox_area: Optional[float]
    is_likely_hole: bool = False
    classification: str = "exterior"  # exterior | hole | single
    confidence: str = "n/a"  # high | medium | low | n/a
    area_ratio_to_exterior: Optional[float] = None
    points: List[Tuple[float, float]] = field(default_factory=list)
    baseline_is_child: bool = False  # Rule-based (Shape[1] Path[0] & folder contains 'Skin')
    # Added geometric refinement metrics for circle detection
    perimeter: Optional[float] = None
    circularity: Optional[float] = None  # 4*pi*Area / Perimeter^2 (1.0 ideal circle)
    radial_deviation_ratio: Optional[float] = None  # std(radius)/mean(radius) (0 ideal circle)
    # Nesting / parity-based classification (new)
    nesting_depth: int = 0  # number of containing loops within same shape
    parity_classification: Optional[str] = None  # exterior/hole via even-odd parity
    classification_method: str = "area"  # 'area' or 'parity'


@dataclass
class ShapeMetrics:
    shape_index: int
    identifier: str
    num_paths: int
    has_holes: bool
    total_area: float
    exterior_area: Optional[float]
    hole_count: int
    paths: List[PathMetrics]


@dataclass
class FileAnalysis:
    file_path: str
    file_name: str
    shape_count: int
    shapes_with_holes: int
    total_paths: int
    shapes: List[ShapeMetrics]


# --------------------------------------------------------------------------------------
# Geometry Helpers
# --------------------------------------------------------------------------------------

def polygon_area(points: List[Tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i in range(len(points)):
        j = (i + 1) % len(points)
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0


def winding_direction(points: List[Tuple[float, float]]) -> str:
    if len(points) < 3:
        return "Unknown"
    signed_area = 0.0
    for i in range(len(points)):
        j = (i + 1) % len(points)
        signed_area += points[i][0] * points[j][1]
        signed_area -= points[j][0] * points[i][1]
    if signed_area > 0:
        return "CCW"
    if signed_area < 0:
        return "CW"
    return "Degenerate"


def bbox_from_points(points: List[Tuple[float, float]]) -> Optional[Dict[str, float]]:
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y
    return {
        'min_x': float(min_x),
        'max_x': float(max_x),
        'min_y': float(min_y),
        'max_y': float(max_y),
        'width': float(width),
        'height': float(height),
        'area': float(width * height),
        'aspect_ratio': float(max(width, height) / (min(width, height) if min(width, height) > 0 else 1e-9))
    }


# --------------------------------------------------------------------------------------
# Classification Logic
# --------------------------------------------------------------------------------------

def classify_paths_area(paths: List[PathMetrics]) -> List[PathMetrics]:
    if not paths:
        return paths
    if len(paths) == 1:
        paths[0].classification = 'single'
        return paths

    # Largest area path assumed exterior
    sorted_by_area = sorted(paths, key=lambda p: p.area, reverse=True)
    exterior = sorted_by_area[0]
    exterior.classification = 'exterior'
    exterior.is_likely_hole = False
    exterior.confidence = 'high'

    for p in sorted_by_area[1:]:
        p.classification = 'hole'
        p.is_likely_hole = True
        p.area_ratio_to_exterior = p.area / exterior.area if exterior.area > 0 else None
        # Winding difference increases confidence
        p.confidence = 'high' if p.winding != exterior.winding else 'medium'
    return paths


def classify_paths_parity(paths: List[PathMetrics]) -> None:
    """Assign parity-based classification using nesting depth (even=exterior, odd=hole).
    Updates nesting_depth and parity_classification in-place. Does not overwrite existing
    classification field so both methods can be compared. Intended to run AFTER metrics filled.
    """
    if len(paths) <= 1:
        for p in paths:
            p.nesting_depth = 0
            p.parity_classification = 'single'
        return
    # Precompute bounding boxes & representative points
    def bbox(pts):
        xs=[pt[0] for pt in pts]; ys=[pt[1] for pt in pts]
        return min(xs), max(xs), min(ys), max(ys)
    bboxes=[]
    for p in paths:
        if len(p.points) >=3:
            bboxes.append(bbox(p.points))
        else:
            bboxes.append((0,0,0,0))

    def point_in_poly(x: float, y: float, poly: List[Tuple[float,float]]):
        inside=False; n=len(poly)
        for i in range(n):
            j=(i-1)%n
            xi,yi=poly[i]; xj,yj=poly[j]
            if ((yi>y)!=(yj>y)) and (x < (xj - xi)*(y - yi)/(yj - yi + 1e-12) + xi):
                inside = not inside
        return inside

    # Use centroid as representative test point (fallback to first point)
    centroids=[]
    for p in paths:
        if len(p.points)>=3:
            cx=sum(pt[0] for pt in p.points)/len(p.points)
            cy=sum(pt[1] for pt in p.points)/len(p.points)
            centroids.append((cx,cy))
        else:
            centroids.append((0.0,0.0))

    # Compute nesting depths
    for i, p in enumerate(paths):
        depth=0
        if len(p.points) <3:
            p.nesting_depth=0; p.parity_classification='single'; continue
        px,py=centroids[i]
        bb_i=bboxes[i]
        for j, q in enumerate(paths):
            if i==j or len(q.points)<3:
                continue
            # bbox rejection
            minx,maxx,miny,maxy=bboxes[j]
            if not (minx <= px <= maxx and miny <= py <= maxy):
                continue
            if point_in_poly(px, py, q.points):
                depth +=1
        p.nesting_depth = depth
        p.parity_classification = 'exterior' if depth %2 ==0 else 'hole'

    # Harmonize single-case where multiple exteriors: keep existing classification if ambiguity
    # (No action needed; parity classification already set.)


# --------------------------------------------------------------------------------------
# Core Analysis
# --------------------------------------------------------------------------------------

def analyze_file_at_height(clf_path: str, height: float, folder_name: Optional[str] = None,
                           classification_mode: str = 'area') -> Optional[FileAnalysis]:
    file_name = os.path.basename(clf_path)
    try:
        part = CLFFile(clf_path)
        layer = part.find(height)
        if layer is None or not hasattr(layer, 'shapes'):
            return None

        shapes_metrics: List[ShapeMetrics] = []
        shapes_with_holes = 0
        total_paths = 0
        layer_shapes = list(layer.shapes)
        total_layer_shapes = len(layer_shapes)
        for s_idx, shape in enumerate(layer_shapes):
            if not hasattr(shape, 'points') or not shape.points:
                continue
            identifier = 'unknown'
            if hasattr(shape, 'model') and hasattr(shape.model, 'id'):
                try:
                    identifier = str(shape.model.id)
                except Exception:
                    pass

            path_metrics_list: List[PathMetrics] = []
            # Simplified direct extraction mirroring analyze_all_shapes_at_height.py
            for p_idx, path in enumerate(shape.points):
                try:
                    arr = np.asarray(path)
                    if arr.ndim != 2 or arr.shape[0] < 3 or arr.shape[1] < 2:
                        # Degenerate or unexpected shape
                        pts_list: List[Tuple[float, float]] = []
                    else:
                        pts_list = [(float(x), float(y)) for x, y in arr[:, :2]]

                    if len(pts_list) < 3:
                        area = 0.0
                        winding = "Unknown"
                        is_closed = False
                        bbox = None
                        perimeter = None
                        circularity = None
                        radial_dev_ratio = None
                    else:
                        area = polygon_area(pts_list)
                        winding = winding_direction(pts_list)
                        # Use first == last to determine closure similar to reference
                        is_closed = np.allclose(arr[0, :2], arr[-1, :2], atol=1e-6)
                        bbox = bbox_from_points(pts_list)
                        # Perimeter (include closing segment if closed)
                        perimeter = 0.0
                        for k in range(len(pts_list) - 1):
                            x1, y1 = pts_list[k]; x2, y2 = pts_list[k+1]
                            perimeter += math.hypot(x2 - x1, y2 - y1)
                        if is_closed:
                            x1, y1 = pts_list[-1]; x2, y2 = pts_list[0]
                            perimeter += math.hypot(x2 - x1, y2 - y1)
                        circularity = (4 * math.pi * area / (perimeter ** 2)) if perimeter and perimeter > 0 else None
                        # Radial deviation (coefficient of variation around centroid)
                        cx = sum(p[0] for p in pts_list) / len(pts_list)
                        cy = sum(p[1] for p in pts_list) / len(pts_list)
                        radii = [math.hypot(p[0]-cx, p[1]-cy) for p in pts_list]
                        if radii:
                            mean_r = sum(radii)/len(radii)
                            if mean_r > 0:
                                var_r = sum((r-mean_r)**2 for r in radii)/len(radii)
                                radial_dev_ratio = math.sqrt(var_r)/mean_r
                            else:
                                radial_dev_ratio = None
                        else:
                            radial_dev_ratio = None

                    # Baseline child rule (mimic process_layer_data logic):
                    # hole if this is the SECOND shape (index 1), FIRST path (index 0),
                    # there are at least 2 shapes in the layer, and folder contains 'Skin'.
                    baseline_is_child = (
                        s_idx == 1
                        and p_idx == 0
                        and total_layer_shapes >= 2
                        and (folder_name is not None and 'Skin' in folder_name)
                    )

                    pm = PathMetrics(
                        path_index=p_idx,
                        num_points=len(pts_list),
                        is_closed=is_closed,
                        area=area,
                        winding=winding,
                        center=(float(sum(p[0] for p in pts_list) / len(pts_list)) if pts_list else 0.0,
                                float(sum(p[1] for p in pts_list) / len(pts_list)) if pts_list else 0.0),
                        bounds={k: bbox[k] for k in ['min_x', 'max_x', 'min_y', 'max_y']} if bbox else {},
                        bbox_aspect_ratio=(bbox['aspect_ratio'] if bbox else None),
                        bbox_area=(bbox['area'] if bbox else None),
                        points=pts_list,
                        baseline_is_child=baseline_is_child,
                        perimeter=perimeter,
                        circularity=circularity,
                        radial_deviation_ratio=radial_dev_ratio
                    )
                    path_metrics_list.append(pm)
                    total_paths += 1
                except Exception as e:
                    print(f"  Path {p_idx} in {file_name} could not be processed: {e}")
                    continue

            # First perform area-based classification
            path_metrics_list = classify_paths_area(path_metrics_list)
            # Then parity classification
            classify_paths_parity(path_metrics_list)
            # Optionally override primary classification field with parity result
            if classification_mode in ('parity', 'both'):
                for p in path_metrics_list:
                    if p.parity_classification:
                        # Keep original in confidence label if switching method
                        if classification_mode == 'parity':
                            p.classification = p.parity_classification
                            p.classification_method = 'parity'
                        elif classification_mode == 'both':
                            # Keep area classification in classification, mark method
                            p.classification_method = 'area'
            else:
                for p in path_metrics_list:
                    p.classification_method = 'area'
            hole_count = sum(1 for p in path_metrics_list if p.classification == 'hole')
            if hole_count > 0:
                shapes_with_holes += 1
            exterior_area = next((p.area for p in path_metrics_list if p.classification == 'exterior'), None)
            shape_total_area = sum(p.area for p in path_metrics_list)
            sm = ShapeMetrics(
                shape_index=s_idx,
                identifier=identifier,
                num_paths=len(path_metrics_list),
                has_holes=hole_count > 0,
                total_area=shape_total_area,
                exterior_area=exterior_area,
                hole_count=hole_count,
                paths=path_metrics_list
            )
            shapes_metrics.append(sm)

        if not shapes_metrics:
            return None

        return FileAnalysis(
            file_path=clf_path,
            file_name=file_name,
            shape_count=len(shapes_metrics),
            shapes_with_holes=shapes_with_holes,
            total_paths=total_paths,
            shapes=shapes_metrics
        )
    except Exception as e:
        print(f"Error analyzing {file_name}: {e}")
        return None


def resolve_build_path(build_id: str, main_build_folder: str) -> Tuple[str, str]:
    """Return (build_path_used, preprocess_folder_path)."""
    # Candidate 1: repo-local abp_contents
    candidate1 = os.path.join(PROJECT_ROOT, 'abp_contents', f'preprocess build-{build_id}')
    # Candidate 2: external MIDAS style: <main_build_folder>/<build_id>/preprocess build-<build_id>
    candidate2 = os.path.join(main_build_folder, build_id, f'preprocess build-{build_id}')
    # Candidate 3: user-provided main build folder directly containing preprocess build-<id>
    candidate3 = os.path.join(main_build_folder, f'preprocess build-{build_id}')

    for c in [candidate1, candidate2, candidate3]:
        if os.path.exists(c):
            return os.path.dirname(c), c

    # Fallback: ensure candidate2 parent exists (create structure) even if preprocess missing
    os.makedirs(os.path.dirname(candidate2), exist_ok=True)
    return os.path.dirname(candidate2), candidate2


def load_clf_file_list(preprocess_folder: str, config_dir: Optional[str]) -> List[Dict[str, Any]]:
    exclusion_patterns = []
    try:
        exclusion_patterns = load_exclusion_patterns(config_dir) if config_dir else load_exclusion_patterns()
    except Exception:
        pass
    clf_files = find_clf_files(preprocess_folder)
    filtered = []
    for info in clf_files:
        if should_skip_folder(info['folder'], exclusion_patterns):
            continue
        filtered.append(info)
    return filtered


# --------------------------------------------------------------------------------------
# Visualization
# --------------------------------------------------------------------------------------

def visualize(files: List[FileAnalysis], height: float, out_path: str):
    if not PLOTTING_AVAILABLE:
        print("Plotting not available (matplotlib import failed). Skipping PNG generation.")
        return
    import matplotlib.pyplot as plt  # local import to respect backend
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    draw_platform_boundary(plt)
    add_reference_lines(plt)

    # Colors: exterior path = dark blue, holes = orange/red gradient, single = gray
    for fa in files:
        for shape in fa.shapes:
            for p in shape.paths:
                pts = p.points
                if len(pts) < 3:
                    continue
                if p.classification == 'exterior':
                    color = 'navy'
                    lw = 2
                    alpha = 0.75
                elif p.classification == 'hole':
                    color = 'orange' if p.confidence != 'high' else 'red'
                    lw = 1.25
                    alpha = 0.9
                else:
                    color = 'gray'
                    lw = 1
                    alpha = 0.6
                import numpy as _np
                arr = _np.asarray(pts)
                draw_shape(plt, arr, color=color, alpha=alpha, linewidth=lw)

    add_platform_labels(plt)
    set_platform_limits(plt)
    ax.set_title(f'Detailed Paths & Holes @ {height}mm\nFiles: {len(files)}', fontsize=14, fontweight='bold')
    save_platform_figure(plt, out_path)
    print(f"Saved visualization: {out_path}")


def visualize_baseline_children(files: List[FileAnalysis], height: float, out_path: str):
    """Second image: highlight baseline rule children vs parents.
    Colors:
      - Parent (not baseline child) exterior: black
      - Baseline child paths: magenta
      - Other hole classification (not baseline child): orange
    """
    if not PLOTTING_AVAILABLE:
        print("Plotting not available. Skipping baseline child visualization.")
        return
    import matplotlib.pyplot as plt  # noqa
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    for fa in files:
        for shape in fa.shapes:
            for p in shape.paths:
                pts = p.points
                if len(pts) < 3:
                    continue
                if p.baseline_is_child:
                    color = 'magenta'
                    lw = 2
                    alpha = 0.9
                elif p.classification == 'hole':
                    color = 'orange'
                    lw = 1.25
                    alpha = 0.7
                else:
                    color = 'black'
                    lw = 1.0
                    alpha = 0.6
                import numpy as _np
                arr = _np.asarray(pts)
                draw_shape(plt, arr, color=color, alpha=alpha, linewidth=lw)
    add_platform_labels(plt)
    set_platform_limits(plt)
    ax.set_title(f'Baseline Child Highlight @ {height}mm (magenta = Shape[1] Path[0])', fontsize=14, fontweight='bold')
    save_platform_figure(plt, out_path)
    print(f"Saved baseline child visualization: {out_path}")


def visualize_parents_inside_others(files: List[FileAnalysis], height: float, out_path: str):
    """Third image: show only parent (exterior/single) shapes whose exterior is fully contained
    inside another parent exterior in the same dataset (any file). Intended to isolate nested
    circles or similar fully enclosed parents that are NOT classified as holes by intra-shape logic.
    """
    if not PLOTTING_AVAILABLE:
        print("Plotting not available. Skipping parents-inside visualization.")
        return
    try:
        from shapely.geometry import Polygon as _ShapelyPolygon  # type: ignore
    except Exception:
        _ShapelyPolygon = None  # fallback to manual method

    def poly_contains(outer_pts: List[Tuple[float, float]], inner_pts: List[Tuple[float, float]]) -> bool:
        if len(outer_pts) < 3 or len(inner_pts) < 3:
            return False
        if _ShapelyPolygon:
            try:
                return _ShapelyPolygon(inner_pts).within(_ShapelyPolygon(outer_pts))
            except Exception:
                pass
        # Manual ray casting for each inner point
        def point_in_poly(x: float, y: float, poly: List[Tuple[float,float]]) -> bool:
            inside = False
            n = len(poly)
            for i in range(n):
                j = (i - 1) % n
                xi, yi = poly[i]
                xj, yj = poly[j]
                intersects = ((yi > y) != (yj > y)) and (x < (xj - xi)*(y - yi) / (yj - yi + 1e-12) + xi)
                if intersects:
                    inside = not inside
            return inside
        for (x,y) in inner_pts:
            if not point_in_poly(x,y, outer_pts):
                return False
        return True

    # Collect candidate parent exteriors (classification exterior or single)
    parents = []  # list of dicts with keys: pts, file_name, shape_index
    for fa in files:
        for shape in fa.shapes:
            exterior = next((p for p in shape.paths if p.classification in ('exterior','single')), None)
            if exterior and len(exterior.points) >= 3:
                parents.append({
                    'points': exterior.points,
                    'file': fa.file_name,
                    'shape_index': shape.shape_index,
                    'path_index': exterior.path_index,
                    'area': exterior.area
                })

    contained = []
    for i, inner in enumerate(parents):
        for j, outer in enumerate(parents):
            if i == j:
                continue
            # Quick bbox rejection
            in_pts = inner['points']; out_pts = outer['points']
            in_bbox = bbox_from_points(in_pts); out_bbox = bbox_from_points(out_pts)
            if not in_bbox or not out_bbox:
                continue
            if not (out_bbox['min_x'] <= in_bbox['min_x'] and out_bbox['max_x'] >= in_bbox['max_x'] and
                    out_bbox['min_y'] <= in_bbox['min_y'] and out_bbox['max_y'] >= in_bbox['max_y']):
                continue
            if poly_contains(outer['points'], inner['points']):
                contained.append(inner)
                break  # no need to check more outers

    import matplotlib.pyplot as plt  # noqa
    fig, ax = plt.subplots(1,1, figsize=(12,10))
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    if not contained:
        ax.set_title(f'No parent exteriors contained within another @ {height}mm', fontsize=14)
    else:
        for c in contained:
            import numpy as _np
            arr = _np.asarray(c['points'])
            draw_shape(plt, arr, color='purple', alpha=0.85, linewidth=2)
            # Annotate
            cx = sum(p[0] for p in c['points'])/len(c['points'])
            cy = sum(p[1] for p in c['points'])/len(c['points'])
            ax.text(cx, cy, 'P-IN', color='purple', fontsize=8, ha='center', va='center')
        ax.set_title(f'Parent Exteriors Fully Inside Other Parents @ {height}mm\nCount: {len(contained)}', fontsize=14, fontweight='bold')
    add_platform_labels(plt)
    set_platform_limits(plt)
    save_platform_figure(plt, out_path)
    print(f"Saved parents-inside visualization: {out_path}")


def visualize_shape_index(files: List[FileAnalysis], height: float, out_path: str, target_index: int):
    """Show only shapes with given shape_index (across all files)."""
    if not PLOTTING_AVAILABLE:
        return
    import matplotlib.pyplot as plt  # noqa
    fig, ax = plt.subplots(1,1, figsize=(10,8))
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    count_paths = 0
    for fa in files:
        for shape in fa.shapes:
            if shape.shape_index != target_index:
                continue
            for p in shape.paths:
                if len(p.points) < 3:
                    continue
                color = 'navy' if p.classification in ('exterior','single') else 'red'
                import numpy as _np
                arr = _np.asarray(p.points)
                draw_shape(plt, arr, color=color, alpha=0.85 if color=='navy' else 0.7, linewidth=2 if color=='navy' else 1.25)
                count_paths += 1
    add_platform_labels(plt)
    set_platform_limits(plt)
    ax.set_title(f'Shape Index {target_index} Only @ {height}mm (paths: {count_paths})', fontsize=13, fontweight='bold')
    save_platform_figure(plt, out_path)
    print(f"Saved shape index {target_index} visualization: {out_path}")


def visualize_baseline_mismatch(files: List[FileAnalysis], height: float, out_path: str):
    """Show only paths where baseline child rule and area-based classification disagree.
    Color coding:
      - baseline child & classification hole (agreement) -> magenta thin
      - baseline child & NOT classification hole -> yellow (missed by area method)
      - NOT baseline child & classification hole -> red (area method extra hole)
    """
    if not PLOTTING_AVAILABLE:
        return
    import matplotlib.pyplot as plt  # noqa
    fig, ax = plt.subplots(1,1, figsize=(12,10))
    draw_platform_boundary(plt)
    add_reference_lines(plt)
    mismatch_count = 0
    agree_count = 0
    for fa in files:
        for shape in fa.shapes:
            for p in shape.paths:
                if len(p.points) < 3:
                    continue
                baseline = p.baseline_is_child
                area_hole = (p.classification == 'hole')
                if baseline and area_hole:
                    color = 'magenta'; lw=1.5; alpha=0.9; agree_count +=1
                elif baseline and not area_hole:
                    color = 'yellow'; lw=2.2; alpha=0.95; mismatch_count +=1
                elif (not baseline) and area_hole:
                    color = 'red'; lw=1.8; alpha=0.85; mismatch_count +=1
                else:
                    continue  # neither baseline nor area hole
                import numpy as _np
                arr = _np.asarray(p.points)
                draw_shape(plt, arr, color=color, alpha=alpha, linewidth=lw)
    add_platform_labels(plt)
    set_platform_limits(plt)
    ax.set_title(f'Baseline vs Area Hole Mismatch @ {height}mm\nAgree (magenta): {agree_count} | Mismatches (yellow/red): {mismatch_count}', fontsize=13, fontweight='bold')
    save_platform_figure(plt, out_path)
    print(f"Saved baseline mismatch visualization: {out_path}")


def visualize_parity(files: List[FileAnalysis], height: float, out_path: str):
    """Visualization using parity-based classification (nesting depth even/odd)."""
    if not PLOTTING_AVAILABLE:
        return
    import matplotlib.pyplot as plt  # noqa
    fig, ax = plt.subplots(1,1, figsize=(12,10))
    draw_platform_boundary(plt); add_reference_lines(plt)
    placed=[]  # list of (x,y) for label collision avoidance
    for fa in files:
        for shape in fa.shapes:
            for p in shape.paths:
                if len(p.points) <3:
                    continue
                cls = p.parity_classification or p.classification
                color = 'navy' if cls in ('exterior','single') else 'red'
                import numpy as _np, random as _rand
                arr = _np.asarray(p.points)
                draw_shape(plt, arr, color=color, alpha=0.85 if color=='navy' else 0.9, linewidth=2 if color=='navy' else 1.25)
                cx,cy=p.center
                # jitter / offset to reduce overlaps
                jitter_attempts=5
                label=f"d{p.nesting_depth}"
                dx=0; dy=0
                for _ in range(jitter_attempts):
                    candidate=(cx+dx, cy+dy)
                    if all((candidate[0]-ox)**2 + (candidate[1]-oy)**2 > 4.0 for ox,oy in placed):
                        placed.append(candidate)
                        break
                    # try a new random small offset
                    dx = _rand.uniform(-3,3)
                    dy = _rand.uniform(-3,3)
                ax.text(candidate[0], candidate[1], label, fontsize=6, ha='center', va='center', color=color,
                        bbox=dict(facecolor='white', edgecolor='none', alpha=0.5, pad=0.5))
    add_platform_labels(plt); set_platform_limits(plt)
    ax.set_title(f'Parity (Nesting) Classification @ {height}mm', fontsize=14, fontweight='bold')
    save_platform_figure(plt, out_path)
    print(f"Saved parity classification visualization: {out_path}")


def visualize_area_vs_parity_mismatch(files: List[FileAnalysis], height: float, out_path: str):
    """Highlight differences between area-based and parity-based classification when both computed."""
    if not PLOTTING_AVAILABLE:
        return
    import matplotlib.pyplot as plt  # noqa
    fig, ax = plt.subplots(1,1, figsize=(12,10))
    draw_platform_boundary(plt); add_reference_lines(plt)
    mismatch=0; same=0
    for fa in files:
        for shape in fa.shapes:
            for p in shape.paths:
                if len(p.points)<3 or not p.parity_classification:
                    continue
                area_cls = p.classification if p.classification_method=='area' else p.classification  # current field holds area if mode both
                parity_cls = p.parity_classification
                differs = (area_cls != parity_cls) and not (area_cls=='single' and parity_cls=='exterior')
                if differs:
                    color='yellow'; lw=2.2; alpha=0.9; mismatch+=1
                else:
                    color='magenta'; lw=1.2; alpha=0.6; same+=1
                import numpy as _np
                arr=_np.asarray(p.points)
                draw_shape(plt, arr, color=color, alpha=alpha, linewidth=lw)
                cx,cy=p.center
                ax.text(cx, cy, f"A:{area_cls}\nP:{parity_cls}\nd{p.nesting_depth}", fontsize=6, ha='center', va='center', color=color)
    add_platform_labels(plt); set_platform_limits(plt)
    ax.set_title(f'Area vs Parity Classification @ {height}mm\nAgree(magenta):{same} | Diff(yellow):{mismatch}', fontsize=13, fontweight='bold')
    save_platform_figure(plt, out_path)
    print(f"Saved area vs parity mismatch visualization: {out_path}")


def visualize_single_file(fa: FileAnalysis, height: float, out_path: str):
    """Per-file visualization: show all paths for one CLF file with both area classification
    (primary classification field) and parity depth annotations. Colors mirror global view.
    """
    if not PLOTTING_AVAILABLE:
        return
    import matplotlib.pyplot as plt  # noqa
    fig, ax = plt.subplots(1,1, figsize=(10,8))
    draw_platform_boundary(plt); add_reference_lines(plt)
    # Derive parent & grandparent folder names
    parent_dir = os.path.basename(os.path.dirname(fa.file_path))
    grandparent_dir = os.path.basename(os.path.dirname(os.path.dirname(fa.file_path)))
    for shape in fa.shapes:
        for p in shape.paths:
            if len(p.points) < 3:
                continue
            cls = p.classification
            color = 'navy' if cls in ('exterior','single') else 'red'
            if p.baseline_is_child:
                color = 'magenta'
            import numpy as _np
            arr = _np.asarray(p.points)
            draw_shape(plt, arr, color=color, alpha=0.85 if color=='navy' else 0.9, linewidth=2 if color in ('navy','magenta') else 1.4)
            # annotate path indices and depth with slight offset
            cx, cy = p.center
            ax.text(cx+1.0, cy+1.0, f"s{shape.shape_index}p{p.path_index}\n{p.classification[0].upper()} d{p.nesting_depth}", fontsize=6,
                    ha='left', va='bottom', color='black', bbox=dict(facecolor='white', edgecolor='none', alpha=0.5, pad=0.5))
    add_platform_labels(plt); set_platform_limits(plt)
    ax.set_title((f'File: {fa.file_name} @ {height}mm\n'
                  f'Parent: {parent_dir} | Grandparent: {grandparent_dir}\n'
                  f'Shapes: {fa.shape_count} Paths: {fa.total_paths}'),
                 fontsize=10, fontweight='bold')
    save_platform_figure(plt, out_path)
    print(f"Saved per-file visualization: {out_path}")


def visualize_shape1_subdivided(files: List[FileAnalysis], height: float, out_path: str,
                                circularity_threshold: float = 0.92,
                                radial_dev_max: float = 0.06):
    """Additional Shape[1] visualization subdividing its paths by circle-likeness.

    Categories (colors):
      - Likely Circle (green): closed, circularity >= threshold, radial deviation <= radial_dev_max
      - Near Circle / Borderline (gold): closed, circularity within (threshold-0.05, threshold) OR radial_dev <= 1.25*radial_dev_max
      - Not Circle (blue if exterior/single, red if hole classification)

    Annotates each path with (c=.. rdev=..)
    """
    if not PLOTTING_AVAILABLE:
        return
    import matplotlib.pyplot as plt  # noqa
    fig, ax = plt.subplots(1,1, figsize=(11,9))
    draw_platform_boundary(plt); add_reference_lines(plt)
    total = 0; circles=0; borderline=0; not_circ=0
    for fa in files:
        for shape in fa.shapes:
            if shape.shape_index != 1:
                continue
            for p in shape.paths:
                if len(p.points) < 3:
                    continue
                total += 1
                c = p.circularity or 0.0
                rd = p.radial_deviation_ratio if p.radial_deviation_ratio is not None else 1e9
                closed = p.is_closed
                if closed and c >= circularity_threshold and rd <= radial_dev_max:
                    color = 'limegreen'; lw=2.2; alpha=0.95; circles +=1
                elif closed and (c >= circularity_threshold - 0.05 and c < circularity_threshold or rd <= radial_dev_max*1.25):
                    color = 'gold'; lw=1.8; alpha=0.9; borderline +=1
                else:
                    if p.classification == 'hole':
                        color = 'red'; lw=1.2
                    elif p.classification in ('exterior','single'):
                        color = 'navy'; lw=1.5
                    else:
                        color = 'gray'; lw=1.0
                    alpha=0.7; not_circ +=1
                import numpy as _np
                arr = _np.asarray(p.points)
                draw_shape(plt, arr, color=color, alpha=alpha, linewidth=lw)
                # Annotation at centroid
                cx = p.center[0]; cy = p.center[1]
                ax.text(cx, cy, f"c={c:.2f}\nrd={rd if rd!=1e9 else float('nan'):.2f}", fontsize=6,
                        ha='center', va='center', color=color)
    add_platform_labels(plt); set_platform_limits(plt)
    ax.set_title((f'Shape Index 1 Subdivided @ {height}mm\n'
                  f'Paths: {total} | Circles(green): {circles} | Borderline(gold): {borderline} | Not: {not_circ}\n'
                  f'Threshold c>={circularity_threshold}, rd<={radial_dev_max}'), fontsize=12, fontweight='bold')
    save_platform_figure(plt, out_path)
    print(f"Saved shape 1 subdivided visualization: {out_path}")


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Detailed paths & holes analysis at a single height")
    parser.add_argument('--build-id', default='271726')
    parser.add_argument('--height', type=float, default=47.15)
    parser.add_argument('--main-build-folder', default='/Users/ted.tedford/Documents/MIDAS')
    parser.add_argument('--output-root', default='my_outputs/detailed_paths_holes')
    parser.add_argument('--png', action='store_true', help='Generate PNG visualization')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of CLF files (0 = no limit)')
    parser.add_argument('--classification-mode', choices=['area','parity','both'], default='both',
                        help='Primary classification method for hole detection. "both" computes parity for comparison while keeping area labels.')
    parser.add_argument('--pdf', action='store_true', help='Assemble generated PNGs & summary into a single PDF report')
    args = parser.parse_args()

    build_id = str(args.build_id)
    height = float(args.height)
    main_build_folder = args.main_build_folder

    print(f"=== Detailed Paths & Holes Analysis ===")
    print(f"Build ID: {build_id}")
    print(f"Target Height: {height} mm")
    print(f"Main Build Folder: {main_build_folder}")

    build_path, preprocess_folder = resolve_build_path(build_id, main_build_folder)
    print(f"Resolved build path: {build_path}")
    print(f"Preprocess folder: {preprocess_folder}")

    if not os.path.exists(preprocess_folder):
        print(f"WARNING: Preprocess folder not found: {preprocess_folder}")
        print("No CLF files to analyze (create or sync build data). Exiting.")
        return

    config_dir = os.path.join(PROJECT_ROOT, 'src', 'config')
    clf_infos = load_clf_file_list(preprocess_folder, config_dir if os.path.isdir(config_dir) else None)
    if args.limit > 0:
        clf_infos = clf_infos[:args.limit]
    print(f"CLF files considered: {len(clf_infos)}")

    analyses: List[FileAnalysis] = []
    for info in clf_infos:
        fa = analyze_file_at_height(info['path'], height, folder_name=info.get('folder'),
                                    classification_mode=args.classification_mode)
        if fa:
            analyses.append(fa)

    if not analyses:
        print(f"No shapes found at height {height}mm across selected files.")
        return

    # Prepare output directory
    safe_height = ("%0.2f" % height).replace('.', '_')
    out_dir = os.path.join(PROJECT_ROOT, args.output_root, f"build-{build_id}_h-{safe_height}mm")
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory: {out_dir}")

    # Aggregate summary
    total_files = len(analyses)
    total_shapes = sum(a.shape_count for a in analyses)
    # Aggregate summary
    total_files = len(analyses)
    total_shapes = sum(a.shape_count for a in analyses)
    total_shapes_with_holes = sum(a.shapes_with_holes for a in analyses)
    total_paths = sum(a.total_paths for a in analyses)
    total_holes = sum(
        1
        for fa in analyses
        for shape in fa.shapes
        for p in shape.paths
        if p.classification == 'hole'
    )
    summary = {
        'build_id': build_id,
        'height_mm': height,
        'total_files': total_files,
        'total_shapes': total_shapes,
        'total_shapes_with_holes': total_shapes_with_holes,
        'total_paths': total_paths,
        'total_holes': total_holes,
    }

    detailed = {
        'build_id': build_id,
        'height_mm': height,
        'summary': summary,
        'files': [asdict(fa) for fa in analyses]
    }
    json_path = os.path.join(out_dir, f'detailed_paths_holes_{safe_height}mm.json')
    with open(json_path, 'w') as f:
        json.dump(detailed, f, indent=2)
    print(f"Saved JSON: {json_path}")

    # Optional PNG
    if args.png:
        png_path = os.path.join(out_dir, f'paths_holes_{safe_height}mm.png')
        visualize(analyses, height, png_path)
        # Second image (baseline child rule highlighting)
        png_child = os.path.join(out_dir, f'paths_baseline_children_{safe_height}mm.png')
        visualize_baseline_children(analyses, height, png_child)
        # Third image (parent exteriors contained within other parents)
        png_parents_inside = os.path.join(out_dir, f'parents_inside_parents_{safe_height}mm.png')
        visualize_parents_inside_others(analyses, height, png_parents_inside)
        # Shape index specific images
        for idx in (0,1,2):
            out_idx = os.path.join(out_dir, f'shape_index_{idx}_{safe_height}mm.png')
            visualize_shape_index(analyses, height, out_idx, idx)
        # Baseline vs classification mismatch diagnostic
        mismatch_png = os.path.join(out_dir, f'baseline_mismatch_{safe_height}mm.png')
        visualize_baseline_mismatch(analyses, height, mismatch_png)
        # Shape[1] subdivided by circle-likeness metrics
        shape1_sub_png = os.path.join(out_dir, f'shape_index_1_subdivided_{safe_height}mm.png')
        visualize_shape1_subdivided(analyses, height, shape1_sub_png)
        # Parity classification visualization (even-odd nesting)
        parity_png = os.path.join(out_dir, f'parity_classification_{safe_height}mm.png')
        visualize_parity(analyses, height, parity_png)
        # Area vs parity mismatch (only meaningful if both computed)
        if args.classification_mode == 'both':
            avp_png = os.path.join(out_dir, f'area_vs_parity_mismatch_{safe_height}mm.png')
            visualize_area_vs_parity_mismatch(analyses, height, avp_png)
        # Per-file images
        per_file_dir = os.path.join(out_dir, 'per_file')
        os.makedirs(per_file_dir, exist_ok=True)
        for fa in analyses:
            parent_dir = os.path.basename(os.path.dirname(fa.file_path))
            grandparent_dir = os.path.basename(os.path.dirname(os.path.dirname(fa.file_path)))
            base = os.path.splitext(fa.file_name)[0]
            def _sanitize(s: str) -> str:
                return ''.join(c if c.isalnum() or c in ('-','_') else '_' for c in s)
            file_png = os.path.join(per_file_dir, f"{_sanitize(grandparent_dir)}__{_sanitize(parent_dir)}__{_sanitize(base)}_{safe_height}mm.png")
            visualize_single_file(fa, height, file_png)
        # Build PDF if requested after generating images
        if args.pdf:
            try:
                from utils.pdf_things import build_pdf_report  # type: ignore
                build_pdf_report(out_dir, pdf_name=f'holes_analysis_{safe_height}mm.pdf')
            except Exception as e:
                print(f"PDF report generation failed: {e}")

    # Plain text summary
    txt_path = os.path.join(out_dir, f'summary_{safe_height}mm.txt')
    with open(txt_path, 'w') as f:
        f.write("DETAILED PATHS & HOLES ANALYSIS\n")
        f.write("="*40 + "\n")
        for k, v in summary.items():
            f.write(f"{k}: {v}\n")
        f.write("\nPer File:\n")
        for fa in analyses:
            f.write(f"- {fa.file_name}: shapes={fa.shape_count}, shapes_with_holes={fa.shapes_with_holes}, paths={fa.total_paths}\n")
    print(f"Saved text summary: {txt_path}")

    print("\nDone. Inspect JSON for full per-path detail.")


if __name__ == '__main__':
    main()
