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

def classify_paths(paths: List[PathMetrics]) -> List[PathMetrics]:
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


# --------------------------------------------------------------------------------------
# Core Analysis
# --------------------------------------------------------------------------------------

def analyze_file_at_height(clf_path: str, height: float) -> Optional[FileAnalysis]:
    file_name = os.path.basename(clf_path)
    try:
        part = CLFFile(clf_path)
        layer = part.find(height)
        if layer is None or not hasattr(layer, 'shapes'):
            return None

        shapes_metrics: List[ShapeMetrics] = []
        shapes_with_holes = 0
        total_paths = 0

        for s_idx, shape in enumerate(layer.shapes):
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
                    else:
                        area = polygon_area(pts_list)
                        winding = winding_direction(pts_list)
                        # Use first == last to determine closure similar to reference
                        is_closed = np.allclose(arr[0, :2], arr[-1, :2], atol=1e-6)
                        bbox = bbox_from_points(pts_list)

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
                        points=pts_list
                    )
                    path_metrics_list.append(pm)
                    total_paths += 1
                except Exception as e:
                    print(f"  Path {p_idx} in {file_name} could not be processed: {e}")
                    continue

            path_metrics_list = classify_paths(path_metrics_list)
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
        fa = analyze_file_at_height(info['path'], height)
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
