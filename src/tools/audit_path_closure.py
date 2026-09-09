#!/usr/bin/env python3
"""Are the extracted footprints actually closed loops?

WHY THIS EXISTS
---------------
Ted, 9 Sep 2026, on build 512002 after the `ebm-ti64` exclusion was removed:
*"the new coupons or ti64 parts we see appear to have some unclosed footprints.
pls make a new program to interrogate those paths to see if we are correctly
closing the path on all the items we should."*

He was right, and the defect is not visible from any existing tool.

⭐ THE THING THAT MAKES THIS SUBTLE
-----------------------------------
`closed_path_finder.py` already asks this question, but of the **CLF source**,
and it asks it as `np.allclose(points[0], points[-1])` - do the endpoints
coincide. In the EXTRACTED path data they never do. Not once. At 20.00 mm on
plate 201 the smallest first-to-last distance across 72 shapes is **0.133 mm**
and the median is 0.212 mm. Run that test here and every shape on every plate
reports "open", which is useless.

Closure in the extracted JSON is carried by a **flag**, `should_close`, and the
renderer fills the shape regardless (`fill_closed: 'y'`). So the real question is
not "do the ends meet" but:

    ⚠ Is there a shape we FILL, across a gap large enough that the fill is
      inventing geometry?

Because that is what reaches the cut. Filling an open outline joins its ends with
a straight chord, and every pixel between the chord and the true boundary is
either powder counted as part, or part surface thrown away. Both corrupt the
defect numbers, and neither raises an error anywhere.

WHAT IT FOUND FIRST TIME (plate 201, 20.00 mm)
----------------------------------------------
`alp-ebm-ti64-01_*_Solid_SKIN` - two shapes carrying **should_close: False** with
a **12.803 mm** end gap, which is **27% of the shape's own bounding diagonal**,
and `fill_closed: 'y'`. They are filled across a 12.8 mm chord.

For contrast the tensile bars (`ten-ebm-ti64-ms3-01_*`) are healthy: gaps of
0.646-0.691 mm, about 4% of their diagonal, and `should_close: True`.

So the gap alone is not the signal - **the gap relative to the shape's own size,
together with the should_close flag, is.** A 0.6 mm gap on a 17 mm part is a
tessellation artifact; a 12.8 mm gap on a 47 mm part is a broken outline.

USAGE
-----
    python3 src/tools/audit_path_closure.py --part 201
    python3 src/tools/audit_path_closure.py --part 201 --every 1     # all layers
    python3 src/tools/audit_path_closure.py --source <clf_analysis dir> --json out.json

Reads MIDAS_BASE_PATH (default ~/Documents/MIDAS) for --part.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict

HEIGHT_RE = re.compile(r"^platform_layer_pathdata_([0-9.]+)mm\.json$")

# A gap wider than this FRACTION of the shape's own bounding diagonal means the
# fill is inventing a meaningful amount of geometry. 0.02 (2%) sits an order of
# magnitude above the tessellation noise measured on healthy parts (~0.04 is the
# tensile bars' worst) - deliberately loose, so a hit is worth investigating
# rather than a number to tune. Report the ratio and let the reader judge.
SUSPICIOUS_RATIO = 0.02

# ⚠ THE GAP RATIO ALONE IS A FALSE-ALARM GENERATOR, measured 9 Sep 2026.
# Ranking plate 201 by gap/diagonal put `AN5518_*_Skin` at the top with 99.3%,
# which looks alarming and is not: those are 6-POINT slivers, 1.1 x 9.1 mm,
# enclosing 2.7-6.4 mm2 beside real Skin outlines of 315-378 points and
# 123-168 mm2. A near-straight open arc has a huge gap-to-diagonal ratio and
# encloses almost nothing, so filling it invents almost nothing.
#
# What actually matters is the AREA the fill invents. So rank by the enclosed
# area of shapes we fill without a close flag, and treat anything below this as
# noise. 50 mm2 is ~1/3 of one knee cross-section - small enough to catch a real
# broken outline, large enough to drop every sliver on plate 201.
MIN_INVENTED_AREA_MM2 = 50.0


def polygon_area(points):
    """Shoelace area of the path once the fill has closed it."""
    if not points or len(points) < 3:
        return 0.0
    n = len(points)
    return 0.5 * abs(sum(points[i][0] * points[(i + 1) % n][1]
                         - points[(i + 1) % n][0] * points[i][1]
                         for i in range(n)))


def endpoint_gap(points):
    """Distance from a path's first point to its last, and its bbox diagonal."""
    if not points or len(points) < 3:
        return None, None
    x0, y0 = points[0][0], points[0][1]
    x1, y1 = points[-1][0], points[-1][1]
    gap = math.hypot(x1 - x0, y1 - y0)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    return gap, diag


def classify(shape):
    """What is wrong with this shape, if anything.

    Four verdicts, and the ORDER matters - `filled_open` outranks `wide_gap`
    because a shape we fill across a large chord is actively corrupting the
    mask, whereas a wide gap on something we do not fill is merely untidy.
    """
    gap, diag = endpoint_gap(shape.get("points"))
    if gap is None:
        return "degenerate", 0.0, 0.0
    ratio = gap / diag if diag else 0.0
    should = bool(shape.get("should_close"))
    fills = str(shape.get("fill_closed", "")).lower() in ("y", "yes", "true", "1")

    area = polygon_area(shape.get("points"))
    if fills and not should and ratio > SUSPICIOUS_RATIO:
        # Only a shape enclosing REAL area is corrupting the mask; a sliver is
        # untidy and harmless. Both are reported, under different verdicts.
        if area >= MIN_INVENTED_AREA_MM2:
            return "filled_open", gap, ratio
        return "open_sliver", gap, ratio
    if ratio > SUSPICIOUS_RATIO:
        return "wide_gap", gap, ratio
    if not should and fills:
        return "filled_not_marked_closed", gap, ratio
    return "ok", gap, ratio


def audit(folder, every=25, verbose=False):
    raw = os.path.join(folder, "imagePathRawData-")
    if not os.path.isdir(raw):
        raise SystemExit(f"No imagePathRawData- under {folder}")

    layers = []
    for entry in sorted(os.listdir(raw)):
        match = HEIGHT_RE.match(entry)
        if match:
            layers.append((float(match.group(1)), entry))
    layers.sort()
    chosen = layers[::max(1, every)]

    per_folder = defaultdict(lambda: {
        "shapes": 0, "ok": 0, "wide_gap": 0, "filled_open": 0,
        "open_sliver": 0, "filled_not_marked_closed": 0, "degenerate": 0,
        "worst_ratio": 0.0, "worst_gap": 0.0, "worst_at": None,
    })
    worst = []

    for height, entry in chosen:
        with open(os.path.join(raw, entry)) as handle:
            shapes = json.load(handle)
        for shape in shapes:
            key = shape.get("clf_folder") or "(no clf_folder)"
            verdict, gap, ratio = classify(shape)
            row = per_folder[key]
            row["shapes"] += 1
            row[verdict] += 1
            if ratio > row["worst_ratio"]:
                row.update(worst_ratio=ratio, worst_gap=gap, worst_at=height)
            if verdict == "filled_open":
                worst.append((polygon_area(shape.get("points")), gap, height, key,
                              shape.get("shape_type"), shape.get("should_close")))

    worst.sort(reverse=True)
    return {"layersScanned": len(chosen), "layersTotal": len(layers),
            "perFolder": dict(per_folder), "worst": worst[:40]}


def family(name):
    for prefix, label in (("ten-ebm", "TENSILE ti64"), ("alp-ebm", "alp ti64"),
                          ("AN5518", "AN5518 part"), ("TBS", "TBS coupon"),
                          ("Gravimetric", "Gravimetric")):
        if name.startswith(prefix):
            return label
    return "other"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--part")
    parser.add_argument("--source")
    parser.add_argument("--every", type=int, default=25,
                        help="scan every Nth layer (default 25; 1 = all)")
    parser.add_argument("--json")
    args = parser.parse_args()

    if args.source:
        folder = os.path.expanduser(args.source)
    elif args.part:
        base = os.environ.get("MIDAS_BASE_PATH", os.path.expanduser("~/Documents/MIDAS"))
        folder = os.path.join(base, f"seed{args.part}", "clf_analysis")
    else:
        parser.error("give --part or --source")

    result = audit(folder, every=args.every)
    print(f"{folder}")
    print(f"scanned {result['layersScanned']} of {result['layersTotal']} layers "
          f"(every {args.every})\n")

    rows = sorted(result["perFolder"].items(),
                  key=lambda kv: -kv[1]["worst_ratio"])
    print(f"{'clf_folder':52} {'shapes':>7} {'filled':>7} {'wide':>6} "
          f"{'worst gap':>10} {'/diag':>7}")
    print(f"{'':52} {'':>7} {'open':>7} {'gap':>6}")
    bad_total = 0
    for name, row in rows:
        bad = row["filled_open"]
        bad_total += bad
        flag = "  <-- FILLED ACROSS AN OPEN OUTLINE" if bad else ""
        print(f"{name[:52]:52} {row['shapes']:7d} {bad:7d} {row['wide_gap']:6d} "
              f"{row['worst_gap']:9.3f} {row['worst_ratio']:6.1%}{flag}")

    print(f"\nby family:")
    fam = defaultdict(lambda: [0, 0, 0.0])
    for name, row in result["perFolder"].items():
        f = fam[family(name)]
        f[0] += row["shapes"]; f[1] += row["filled_open"]
        f[2] = max(f[2], row["worst_ratio"])
    for name, (shapes, bad, ratio) in sorted(fam.items(), key=lambda kv: -kv[1][1]):
        print(f"  {name:16} shapes {shapes:6d}   filled-open {bad:5d}   worst gap {ratio:5.1%}")

    if result["worst"]:
        print(f"\nworst offenders:")
        print(f"  {'area mm2':>9} {'gap mm':>8} {'height':>8}  folder")
        for area, gap, height, name, stype, should in result["worst"][:12]:
            print(f"  {area:9.1f} {gap:8.3f} {height:8.2f}  {name[:44]} "
                  f"({stype}, should_close={should})")

    slivers = sum(r["open_sliver"] for r in result["perFolder"].values())
    print(f"\nVERDICT: {bad_total} shape instance(s) enclose real area "
          f"(>={MIN_INVENTED_AREA_MM2:.0f} mm2) while being filled across an outline "
          f"that is NOT marked closed.")
    print(f"         {slivers} open sliver(s) ignored as harmless - see the note "
          f"on gap ratio in this file.")
    if args.json:
        with open(args.json, "w") as handle:
            json.dump(result, handle, indent=2, default=str)
        print(f"written: {args.json}")
    return 1 if bad_total else 0


if __name__ == "__main__":
    sys.exit(main())
