"""The cross-process lock guarding <build>/clf_analysis.

The point of this lock is that it works between *separate processes* - an in-process
guard was never the problem. So these tests spawn real subprocesses rather than
asserting against threads in this one; a threading-only test would pass just as
happily against a lock that does nothing across process boundaries, which is the only
boundary that matters here.
"""
import os
import subprocess
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.build_lock import (  # noqa: E402
    BuildLocked,
    LOCK_FILENAME,
    build_read_lock,
    build_write_lock,
    lock_path_for,
)

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))


def _spawn_holder(build_path, mode, seconds=10):
    """Start a real process holding the lock, and wait until it actually has it."""
    code = textwrap.dedent(f"""
        import sys, time
        sys.path.insert(0, {SRC!r})
        from utils.build_lock import build_read_lock, build_write_lock
        fn = build_write_lock if {mode!r} == "write" else build_read_lock
        with fn({str(build_path)!r}, hint="test holder"):
            print("HELD", flush=True)
            time.sleep({seconds})
    """)
    p = subprocess.Popen([sys.executable, "-c", code],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    line = p.stdout.readline().strip()
    assert line == "HELD", f"holder failed to start: {line} {p.stderr.read()}"
    return p


@pytest.fixture
def build(tmp_path):
    d = tmp_path / "515357"
    (d / "clf_analysis").mkdir(parents=True)
    return d


def test_a_writer_in_another_process_blocks_a_reader(build):
    """The actual bug: clf-analysis rebuilding while detection tries to read."""
    holder = _spawn_holder(build, "write")
    try:
        with pytest.raises(BuildLocked):
            with build_read_lock(build):
                pass
    finally:
        holder.kill(); holder.wait()


def test_a_reader_in_another_process_blocks_a_writer(build):
    """The same collision from the other side - the rebuild must wait for readers."""
    holder = _spawn_holder(build, "read")
    try:
        with pytest.raises(BuildLocked):
            with build_write_lock(build):
                pass
    finally:
        holder.kill(); holder.wait()


def test_two_readers_can_hold_it_at_once(build):
    """Shared, not exclusive: concurrent analyses of one build are harmless."""
    holder = _spawn_holder(build, "read")
    try:
        with build_read_lock(build):
            pass  # must not raise
    finally:
        holder.kill(); holder.wait()


def test_the_lock_is_released_when_the_holder_is_killed(build):
    """Why flock and not a PID file: kill -9 must not wedge the build forever."""
    holder = _spawn_holder(build, "write")
    holder.kill()
    holder.wait()
    with build_write_lock(build):
        pass  # the kernel dropped the dead process's lock


def test_the_refusal_names_the_holder(build):
    holder = _spawn_holder(build, "write")
    try:
        with pytest.raises(BuildLocked) as excinfo:
            with build_read_lock(build):
                pass
        assert "test holder" in str(excinfo.value)
        assert "515357" in str(excinfo.value)
    finally:
        holder.kill(); holder.wait()


def test_the_lock_file_is_a_sibling_of_clf_analysis_not_inside_it(build):
    """If it lived inside, the rmtree would delete it out from under a held lock and
    the next arrival would create a fresh file and lock that instead - two writers,
    both convinced they are alone."""
    p = lock_path_for(build)
    assert os.path.basename(p) == LOCK_FILENAME
    assert os.path.dirname(p) == str(build)
    # The file is *named* .clf_analysis.lock, so a substring check would pass
    # trivially. What matters is that no directory component is clf_analysis - i.e.
    # the file is not inside the tree that gets rmtree'd.
    assert "clf_analysis" not in p.split(os.sep)[:-1]


def test_wiping_clf_analysis_does_not_disturb_the_lock(build):
    """The rmtree clf-analysis performs must leave the lock file standing."""
    import shutil
    with build_write_lock(build):
        shutil.rmtree(build / "clf_analysis")
        assert os.path.exists(lock_path_for(build))
    holder = _spawn_holder(build, "write")   # still usable afterwards
    holder.kill(); holder.wait()


def test_releasing_happens_even_if_the_body_raises(build):
    with pytest.raises(ValueError):
        with build_write_lock(build):
            raise ValueError("boom")
    with build_write_lock(build):
        pass  # not wedged


def test_a_missing_build_folder_is_an_error_not_a_silent_lock(build):
    with pytest.raises(FileNotFoundError):
        with build_write_lock(str(build) + "-nonexistent"):
            pass


def test_the_same_process_can_reacquire_after_releasing(build):
    with build_read_lock(build):
        pass
    with build_write_lock(build):
        pass
