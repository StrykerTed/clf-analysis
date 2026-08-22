"""Open each CLF file once per run, instead of once per (file, height) pair.

`process_layer_data` is called once for every combination of CLF file and layer
height, and it built a fresh `CLFFile` on every call. On build 516484 that is
3,562 heights x 24 files = **85,488 opens of 24 distinct files**.

Measured on that build:

    CLFFile(path) open + parse   13.7 ms
    part.find(height)             0.6 ms      <- the work the open exists to serve
    ratio                        21 : 1

which is ~1,170 s of re-parsing inside a stage that takes ~1,399 s. Opening each
file once costs 24 x 13.7 ms = 0.33 s.

Reuse is safe. `CLFFile.find` seeks, so a reused handle does not depend on the
order it is asked for heights. That was checked over 480 (file, height)
comparisons against a freshly-opened file, in ascending, descending, shuffled,
repeated and interleaved order - zero mismatches. Holding all 24 open costs 3 MB.

Two properties this module has to keep:

* **Bounded.** A `CLFFile` wraps `io.FileIO`, so each cached entry holds an open
  file descriptor. A build has ~100 CLF files; the cap is well above that, so the
  working set never evicts, and a hypothetical larger build degrades to today's
  behaviour rather than to something worse.
* **Never stale.** A re-run of the same build deletes and re-extracts the ABP to
  the *same* path, so a path alone is not a safe key - a long-lived worker would
  serve the previous extraction's geometry. The key includes the file's size and
  mtime, which makes that impossible. Statting costs microseconds against the
  13.7 ms it guards.
"""
from collections import OrderedDict
import os

from utils.pyarcam.clfutil import CLFFile

# A build carries ~100 CLF files. Sized well above that so the working set of a
# single build never evicts, and far below any file-descriptor limit.
MAX_OPEN = 256

_cache = OrderedDict()


def _key(path):
    """Identity of the *file*, not of the name pointing at it.

    Size and mtime are what make a re-extracted ABP a cache miss rather than a
    silent wrong answer.
    """
    st = os.stat(path)
    return (os.path.abspath(path), st.st_size, st.st_mtime_ns)


def open_clf(path):
    """Return a CLFFile for `path`, reusing an already-open one when valid."""
    try:
        key = _key(path)
    except OSError:
        # Let the caller's own error handling see a missing/unreadable file
        # exactly as it did before this cache existed.
        return CLFFile(path)

    part = _cache.get(key)
    if part is not None:
        _cache.move_to_end(key)
        return part

    part = CLFFile(path)
    _cache[key] = part
    while len(_cache) > MAX_OPEN:
        _cache.popitem(last=False)
    return part


def clear_clf_cache():
    """Drop every cached handle. Call between builds in a long-lived worker."""
    _cache.clear()


def cache_size():
    """How many handles are currently held. For tests and diagnostics."""
    return len(_cache)
