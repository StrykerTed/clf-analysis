"""Hole classification: the geometric rule introduced in 0f79927.

This is the highest-value thing in the repo to pin. Everything downstream -
the cutout mask, and therefore every defect count - depends on which contours
are called holes, and until this file existed the rule had no test at all.

The bug the rule replaced was not an arithmetic slip. The old test asked "is
this the second shape's first path, in a folder named Skin?", which is a
question about how the CLF happens to pack contours rather than about the
geometry. On build 520643 the same 18 parts one millimetre apart are packed as
two shapes at 147.80 mm and one shape at 148.80 mm, so the identical physical
slot was a hole at one height and solid metal at the next. That is why
`test_classification_is_independent_of_path_order` matters more than any single
worked example here: it encodes the property that actually broke.
"""

import numpy as np
import pytest

from utils.platform_analysis.visualization_utils import (
    _classify_paths_by_nesting,
    _polygon_contains,
    _signed_area,
)

from conftest import square


# --- the primitives the rule is built on -----------------------------------

def test_signed_area_sign_follows_winding():
    ccw = _signed_area(square(0, 0, 10))
    cw = _signed_area(square(0, 0, 10, clockwise=True))
    assert ccw > 0
    assert cw < 0
    assert ccw == pytest.approx(-cw)


def test_signed_area_magnitude_is_the_area():
    # A 20x20 square, whatever its winding.
    assert abs(_signed_area(square(3, -7, 10))) == pytest.approx(400.0)


def test_polygon_contains_rejects_a_partial_overlap():
    # Bounding-box rejection: shifted far enough that it straddles the edge.
    assert not _polygon_contains(square(0, 0, 10), square(15, 0, 10))


def test_polygon_contains_accepts_true_nesting():
    assert _polygon_contains(square(0, 0, 10), square(0, 0, 4))


def test_polygon_contains_needs_three_points():
    assert not _polygon_contains([(0, 0), (1, 1)], square(0, 0, 1))


# --- the rule itself --------------------------------------------------------

def test_a_lone_contour_is_never_a_hole():
    """With nothing to be nested inside, "hole" is not a question that arises."""
    assert _classify_paths_by_nesting([square(0, 0, 10)]) == [(False, None)]


def test_no_paths_is_handled():
    assert _classify_paths_by_nesting([]) == []


def test_inner_contour_of_a_ring_is_a_hole():
    outer = square(0, 0, 10)
    inner = square(0, 0, 4, clockwise=True)
    result = _classify_paths_by_nesting([outer, inner])
    assert result[0] == (False, None)      # exterior, no container
    assert result[1] == (True, 0)          # hole, contained by path 0


def test_disjoint_contours_are_both_exterior():
    """The case the old rule got wrong.

    Two parts side by side, packed as two paths. Neither contains the other, so
    neither is a hole - but the old index-based rule flagged the second one
    regardless, cutting real metal out of a part that had no hole in it.
    """
    result = _classify_paths_by_nesting([square(-20, 0, 8), square(20, 0, 8)])
    assert result == [(False, None), (False, None)]


def test_even_odd_makes_an_island_solid_again():
    """Depth 2 is metal, not void.

    A boss in the middle of a pocket is printed material. Counting "is nested at
    all" instead of "is nested an odd number of times" would erase it.
    """
    result = _classify_paths_by_nesting([
        square(0, 0, 30),                    # depth 0 -> exterior
        square(0, 0, 20, clockwise=True),    # depth 1 -> hole
        square(0, 0, 10),                    # depth 2 -> exterior again
    ])
    assert [is_hole for is_hole, _ in result] == [False, True, False]


def test_parent_is_the_immediate_container_not_the_outermost():
    """parent must be the smallest enclosing contour.

    The compositing pass in python-layer-alignments cuts each hole against its
    parent shape; pointing at the outermost contour instead of the immediate one
    is how a Skin inner wall came to erase the Core nested inside it.
    """
    result = _classify_paths_by_nesting([
        square(0, 0, 30),
        square(0, 0, 20, clockwise=True),
        square(0, 0, 10),
    ])
    assert result[1][1] == 0   # middle's parent is the outer square
    assert result[2][1] == 1   # innermost's parent is the middle, not the outer


def test_classification_is_independent_of_path_order():
    """The property the 520643 defect was really about.

    The same geometry must classify the same way no matter what order the CLF
    packs the contours in. This is what makes the rule geometric rather than a
    statement about file layout, so it is checked over every permutation rather
    than one hand-picked reordering.
    """
    from itertools import permutations

    paths = {
        "outer": square(0, 0, 30),
        "hole": square(0, 0, 20, clockwise=True),
        "island": square(0, 0, 10),
        "neighbour": square(80, 0, 5),
    }
    expected = {"outer": False, "hole": True, "island": False, "neighbour": False}

    for order in permutations(paths):
        result = _classify_paths_by_nesting([paths[name] for name in order])
        got = {name: result[i][0] for i, name in enumerate(order)}
        assert got == expected, f"order {order} classified as {got}"


def test_nesting_wins_when_winding_disagrees_and_says_so(capsys):
    """A wrongly-wound hole is still a hole.

    Winding is a cross-check, not the decision: CLF contours in the wild are not
    reliably wound, so trusting winding silently is how a hole gets missed. The
    code must prefer nesting and report the disagreement, because a silent
    disagreement is the thing that makes this class of bug invisible.
    """
    outer = square(0, 0, 10)
    inner_wrongly_wound = square(0, 0, 4)  # CCW, i.e. looks like an exterior
    result = _classify_paths_by_nesting([outer, inner_wrongly_wound], context=' [t]')

    assert result[1][0] is True, "nesting must win over winding"
    assert "winding/nesting disagree" in capsys.readouterr().out


def test_accepts_numpy_arrays_as_well_as_lists():
    """The production caller passes numpy arrays out of the CLF reader."""
    paths = [np.asarray(square(0, 0, 10)), np.asarray(square(0, 0, 4))]
    result = _classify_paths_by_nesting(paths)
    assert [is_hole for is_hole, _ in result] == [False, True]
