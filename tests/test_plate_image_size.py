"""A plate-registered image must be the size its filename promises.

Why this needs pinning
----------------------
`transparent_all_pathdata_210mmx210mm_2100px.png` is not a picture, it is a
measurement. The 3D floor textures a 210mm plane with it, so a file that is not
exactly 2100x2100 misregisters every path drawn on the plate - and it presents
as a calibration fault, which is the expensive thing to debug.

It has gone wrong twice, by two different mechanisms, and neither announced
itself:

* `plt.axis('equal')` refit the limits to the data and `bbox_inches='tight'`
  cropped the save to whatever the paths spanned, so the output size depended on
  where that build's parts happened to sit. Fixed in 8acd557.
* pyplot's current figure is process-global. Three builds analysed concurrently
  on 10 Aug 2026 produced an identifier view of 4426x3831 containing a Combined
  Holes render, and a WITH_NO_ID view of 3727x3829.

In both cases the file was written, the run reported success, and the defect
surfaced hours later in the UI. Measuring the file you just wrote costs a
millisecond, so the promise is now checked rather than assumed.
"""

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _path in (_ROOT, os.path.join(_ROOT, "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

from utils.myfuncs.plotTools import (  # noqa: E402
    PlateImageSizeError,
    save_plate_registered_figure,
)


def _figure(figsize=(7.0, 7.0), xlim=(-105, 105), ylim=(-105, 105)):
    """A figure that saves to 2100x2100 at 300dpi when left alone."""
    plt.close("all")
    plt.figure(figsize=figsize)
    plt.plot([-50, 50], [-50, 50])
    plt.xlim(*xlim)
    plt.ylim(*ylim)
    return plt


def test_a_correctly_sized_plate_image_is_saved(tmp_path):
    out = str(tmp_path / "transparent_all_pathdata_210mmx210mm_2100px.png")
    save_plate_registered_figure(_figure(), out, expected_px=2100)

    with Image.open(out) as img:
        assert img.size == (2100, 2100)


def test_a_wrong_sized_plate_image_raises(tmp_path):
    """The whole point: a wrong size must stop the run, not be written quietly."""
    out = str(tmp_path / "transparent_all_pathdata_210mmx210mm_2100px.png")

    # 5in x 300dpi = 1500px, not the 2100 the filename promises.
    with pytest.raises(PlateImageSizeError) as excinfo:
        save_plate_registered_figure(_figure(figsize=(5.0, 5.0)), out, expected_px=2100)

    assert "1500x1500" in str(excinfo.value)
    assert "2100x2100" in str(excinfo.value)


def test_a_wrong_sized_plate_image_is_not_left_where_it_can_be_served(tmp_path):
    """The resolver matches `^transparent_all_pathdata_\\d+mmx\\d+mm_\\d+px\\.png$`.

    Quarantining renames the file out of that pattern, so a bad image cannot be
    served even if the raise is swallowed further up - which is exactly what the
    surrounding `except Exception: return None` in the view functions would do.
    """
    out = str(tmp_path / "transparent_all_pathdata_210mmx210mm_2100px.png")

    with pytest.raises(PlateImageSizeError):
        save_plate_registered_figure(_figure(figsize=(5.0, 5.0)), out, expected_px=2100)

    assert not os.path.exists(out), "the wrong-sized file is still at the served path"


def test_the_evidence_is_kept_rather_than_deleted(tmp_path):
    """Deleting a corrupt artifact destroys the only copy of the symptom."""
    out = str(tmp_path / "transparent_all_pathdata_210mmx210mm_2100px.png")

    with pytest.raises(PlateImageSizeError):
        save_plate_registered_figure(_figure(figsize=(5.0, 5.0)), out, expected_px=2100)

    quarantined = [f for f in os.listdir(tmp_path) if "INVALID" in f]
    assert quarantined == [
        "transparent_all_pathdata_210mmx210mm_2100px.png.INVALID-1500x1500.png"
    ]


def test_a_non_square_save_is_caught(tmp_path):
    """The real 10 Aug failures were non-square, not merely the wrong scale."""
    out = str(tmp_path / "transparent_all_pathdata_210mmx210mm_2100px.png")

    with pytest.raises(PlateImageSizeError) as excinfo:
        save_plate_registered_figure(
            _figure(figsize=(7.0, 6.0)), out, expected_px=2100
        )

    assert "2100x1800" in str(excinfo.value)
