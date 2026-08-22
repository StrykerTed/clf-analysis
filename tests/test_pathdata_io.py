"""Per-layer path data is 98.8% of what this stage writes, and it feeds the CUT.

So there are two things to pin. First, that the compact form is genuinely smaller
- that is the whole point of the change. Second, and far more important, that a
reader gets back the same geometry, because getting the cut right is the master
priority and a 0.7 mm grid shift once moved cluster count from 4,397 to 24,455.

The rounding bound is not asserted from theory: measured across 423,650 real
coordinates on build 520643, the worst displacement was 0.00000381 mm, which is
0.000034 of a camera pixel, and no coordinate moved into a different pixel.
"""
import json

from utils.platform_analysis.pathdata_io import (
    COORD_DECIMALS,
    dump_path_data,
    dumps_path_data,
    round_floats,
)

# one camera pixel, measured on four machines
MM_PER_PIXEL = 0.11198

SAMPLE = [
    {
        "type": "path",
        "shape_type": "exterior",
        "identifier": "part-1",
        "closed": True,
        "points": [
            [-41.294498443603516, -69.67169952392578],
            [-41.282901763916016, -69.60870361328125],
            [-41.27009963989258, -69.53610229492188],
        ],
    },
    {
        "type": "path",
        "shape_type": "hole",
        "identifier": None,
        "closed": False,
        "points": [[0.0, 0.0], [1.5, -2.25]],
    },
]


def test_structure_survives_a_round_trip():
    """Readers must see the same shape of data - only whitespace and trailing
    float digits are allowed to change."""
    out = json.loads(dumps_path_data(SAMPLE))

    assert len(out) == len(SAMPLE)
    for got, want in zip(out, SAMPLE):
        assert got["type"] == want["type"]
        assert got["shape_type"] == want["shape_type"]
        assert got["identifier"] == want["identifier"]
        assert got["closed"] == want["closed"]
        assert len(got["points"]) == len(want["points"])


def test_no_point_moves_by_a_meaningful_distance():
    """The assertion that actually protects the cut."""
    out = json.loads(dumps_path_data(SAMPLE))

    worst_mm = 0.0
    for got, want in zip(out, SAMPLE):
        for got_pt, want_pt in zip(got["points"], want["points"]):
            for got_v, want_v in zip(got_pt, want_pt):
                worst_mm = max(worst_mm, abs(got_v - want_v))

    # 4 dp can displace a coordinate by at most 0.00005 mm by construction
    assert worst_mm <= 0.5 * 10 ** -COORD_DECIMALS
    # which is under a thousandth of a camera pixel
    assert worst_mm / MM_PER_PIXEL < 0.001


def test_no_coordinate_changes_pixel():
    """Sub-pixel is not enough on its own - a value sitting on a pixel boundary
    could still cross it. It must not."""
    out = json.loads(dumps_path_data(SAMPLE))

    for got, want in zip(out, SAMPLE):
        for got_pt, want_pt in zip(got["points"], want["points"]):
            for got_v, want_v in zip(got_pt, want_pt):
                assert int(got_v / MM_PER_PIXEL) == int(want_v / MM_PER_PIXEL)


def test_compact_form_is_substantially_smaller():
    pretty = json.dumps(SAMPLE, indent=2)
    compact = dumps_path_data(SAMPLE)

    assert len(compact) < len(pretty)
    assert "\n" not in compact
    assert ", " not in compact


def test_booleans_and_none_are_not_rounded():
    """bool is a subclass of int, not float, but it is worth pinning that the
    recursion leaves flags and nulls alone rather than coercing them."""
    payload = {"closed": True, "open": False, "identifier": None, "n": 3, "x": 1.23456789}
    out = round_floats(payload)

    assert out["closed"] is True
    assert out["open"] is False
    assert out["identifier"] is None
    assert out["n"] == 3 and isinstance(out["n"], int)
    assert out["x"] == round(1.23456789, COORD_DECIMALS)


def test_tuples_become_lists_as_json_would_anyway():
    assert round_floats(((1.111111, 2.222222),)) == [[1.1111, 2.2222]]


def test_writes_to_a_file(tmp_path):
    target = tmp_path / "platform_layer_pathdata_73.35mm.json"
    dump_path_data(SAMPLE, str(target))

    reloaded = json.loads(target.read_text())
    assert len(reloaded) == len(SAMPLE)
    assert reloaded[0]["points"][0] == [-41.2945, -69.6717]
