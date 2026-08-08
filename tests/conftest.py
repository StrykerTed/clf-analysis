"""Shared test setup for clf-analysis.

Imports here are awkward for a reason worth stating: the production entrypoints
(`clf_analysis_api.py`, the analysis scripts) run with `src/` as the working
directory, so modules inside `src/` import each other as top-level names -
`from config import ...`, `from utils.myfuncs...`. Tests run from the repo root,
so `src/` has to go on sys.path before anything under it can be imported. Doing
that once here keeps every test file free of path juggling.
"""

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


def square(cx, cy, half, clockwise=False):
    """An axis-aligned square as a closed point list.

    Winding matters to the code under test: an exterior contour is conventionally
    counter-clockwise and a hole clockwise, and the classifier cross-checks
    winding against nesting. Being able to ask for either lets a test exercise
    the disagreement path deliberately rather than by accident.
    """
    pts = [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
        (cx - half, cy - half),
    ]
    return pts[::-1] if clockwise else pts
