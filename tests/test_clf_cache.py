"""The cache is a speed change that must not become a correctness change.

Two risks, and they are not equally obvious. The dull one is that it fails to
cache and the stage stays slow. The sharp one is that it serves a *stale* handle:
re-running a build deletes and re-extracts the ABP to the same path, so a
long-lived worker keyed on the path alone would hand the new run the previous
extraction's geometry - and geometry is what the cut is made from.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from utils.platform_analysis import clf_cache  # noqa: E402


class _FakeCLF:
    """Stands in for CLFFile - we are testing the caching, not the parser."""
    opens = 0

    def __init__(self, path):
        _FakeCLF.opens += 1
        with open(path, "rb") as fh:
            self.content = fh.read()
        self.path = path


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    clf_cache.clear_clf_cache()
    _FakeCLF.opens = 0
    monkeypatch.setattr(clf_cache, "CLFFile", _FakeCLF)
    yield
    clf_cache.clear_clf_cache()


def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_bytes(body)
    return str(p)


def test_repeated_requests_open_the_file_once(tmp_path):
    path = _write(tmp_path, "Part.clf", b"geometry-v1")

    parts = [clf_cache.open_clf(path) for _ in range(500)]

    assert _FakeCLF.opens == 1
    assert all(p is parts[0] for p in parts)


def test_distinct_files_are_cached_separately(tmp_path):
    a = _write(tmp_path, "Part.clf", b"a")
    b = _write(tmp_path, "Net.clf", b"b")

    assert clf_cache.open_clf(a) is not clf_cache.open_clf(b)
    assert _FakeCLF.opens == 2
    assert clf_cache.cache_size() == 2


def test_a_re_extracted_build_is_not_served_the_old_geometry(tmp_path):
    """Re-running a build rewrites the SAME path with new content. Keying on the
    path alone would silently return the previous extraction."""
    path = _write(tmp_path, "Part.clf", b"geometry-v1")
    first = clf_cache.open_clf(path)
    assert first.content == b"geometry-v1"

    os.utime(path, (0, 0))                     # make the change unmistakable
    with open(path, "wb") as fh:
        fh.write(b"geometry-v2-which-is-longer")

    second = clf_cache.open_clf(path)

    assert second is not first
    assert second.content == b"geometry-v2-which-is-longer"


def test_same_size_but_newer_is_still_a_miss(tmp_path):
    """Size alone is not enough - an edit can preserve length."""
    path = _write(tmp_path, "Part.clf", b"AAAA")
    first = clf_cache.open_clf(path)

    with open(path, "wb") as fh:
        fh.write(b"BBBB")
    os.utime(path, (1_000_000, 1_000_000))

    second = clf_cache.open_clf(path)
    assert second is not first
    assert second.content == b"BBBB"


def test_the_cache_is_bounded_so_it_cannot_exhaust_file_descriptors(tmp_path, monkeypatch):
    monkeypatch.setattr(clf_cache, "MAX_OPEN", 4)

    for i in range(20):
        clf_cache.open_clf(_write(tmp_path, "f%d.clf" % i, b"x%d" % i))

    assert clf_cache.cache_size() == 4


def test_eviction_is_least_recently_used(tmp_path, monkeypatch):
    monkeypatch.setattr(clf_cache, "MAX_OPEN", 2)
    a = _write(tmp_path, "a.clf", b"a")
    b = _write(tmp_path, "b.clf", b"b")
    c = _write(tmp_path, "c.clf", b"c")

    first_a = clf_cache.open_clf(a)
    clf_cache.open_clf(b)
    clf_cache.open_clf(a)          # a is now the most recently used, b the least
    clf_cache.open_clf(c)          # evicts b, not a

    assert clf_cache.open_clf(a) is first_a
    assert _FakeCLF.opens == 3     # a, b, c - and a was never re-opened


def test_clear_drops_everything(tmp_path):
    path = _write(tmp_path, "Part.clf", b"x")
    first = clf_cache.open_clf(path)

    clf_cache.clear_clf_cache()

    assert clf_cache.cache_size() == 0
    assert clf_cache.open_clf(path) is not first


def test_a_missing_file_behaves_as_it_did_before_the_cache_existed(tmp_path):
    """The caller has its own try/except around this; the cache must not swallow
    or reshape the failure."""
    missing = str(tmp_path / "nope.clf")

    with pytest.raises(OSError):
        clf_cache.open_clf(missing)

    assert clf_cache.cache_size() == 0
