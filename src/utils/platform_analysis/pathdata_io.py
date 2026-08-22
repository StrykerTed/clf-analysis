"""Writing the per-layer path data.

This is 98.8% of everything clf_analysis produces - 3,021 files and 6.2 GB on
build 520643 - and it was written as pretty-printed JSON: one coordinate per
line, six spaces of indent, every float at full float64 repr.

Two changes, both measured before being made, on a representative layer file:

    as written (indent=2)                    2,108,768 B      6.20 GB total
    compact separators                       1,170,913 B      3.44 GB   1.8x
    compact + 4 dp                             572,530 B      1.68 GB   3.7x

Nearly half the bytes were indentation.

WHY 4 dp IS SAFE - and why it is barely a precision reduction at all.
Across 423,650 coordinates sampled through build 520643, the worst displacement
from rounding was 0.00000381 mm: 0.000034 of a camera pixel, where one pixel is
0.11198 mm. NO coordinate moved into a different pixel. That worst case is
2**-18, which is float32 epsilon at these magnitudes - so the discarded digits
are float32 representation noise printed through a float64 repr, not data.

This is worth stating carefully because the path data is what the CUT is made
from, and getting the cut right is the master priority. Shifting the calibration
grid by 0.7 mm once moved cluster count from 4,397 to 24,455, so this system is
extremely sensitive to sub-millimetre change and precision here gets measured
rather than assumed.

The JSON structure is unchanged. Only whitespace and trailing float digits
differ, so every existing reader keeps working.
"""
import json

# 0.1 micrometres. The layercam resolves ~0.11 mm per pixel, so this is roughly
# a thousand times finer than anything downstream can distinguish.
COORD_DECIMALS = 4


def round_floats(obj, ndigits=COORD_DECIMALS):
    """Recursively round every float, leaving structure and other types alone.

    Tuples become lists, which is what json.dump would have produced anyway.
    Booleans are not floats in Python, so they pass through untouched.
    """
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, (list, tuple)):
        return [round_floats(item, ndigits) for item in obj]
    if isinstance(obj, dict):
        return {key: round_floats(value, ndigits) for key, value in obj.items()}
    return obj


def dumps_path_data(shape_data_list, ndigits=COORD_DECIMALS):
    """Serialise path data compactly. Returns a str."""
    return json.dumps(round_floats(shape_data_list, ndigits), separators=(",", ":"))


def dump_path_data(shape_data_list, file_path, ndigits=COORD_DECIMALS):
    """Write path data to file_path compactly."""
    with open(file_path, "w") as handle:
        handle.write(dumps_path_data(shape_data_list, ndigits))
