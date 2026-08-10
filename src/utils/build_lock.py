"""A cross-process reader/writer lock over one build's derived artifacts.

The three admission guards added on 9 Aug stop a service starting a second job that
would collide with its own first one. They cannot help here, because the collision
that remains is between *different services*: clf-analysis rmtrees
``<build>/clf_analysis`` at the start of every run, while layer-alignments and
defect-detect read ``platform_layer_pathdata_*.json`` out of it. Nothing in a
process-local dict is visible to another process, so the only place the two can
agree is the filesystem.

Why flock rather than a PID or timestamp file
---------------------------------------------
The hard part of a lock is not taking it, it is releasing it when the holder dies.
A PID file left behind by a crashed run blocks every later run until somebody
notices and deletes it, and "somebody notices" is not a mechanism. ``flock`` is held
by an open file descriptor, so the kernel drops it when the process exits for any
reason - crash, kill -9, power loss. There is no stale state to clean up and no
liveness heuristic to get wrong.

It also gives us reader/writer directly: many readers may hold LOCK_SH at once, a
writer takes LOCK_EX and waits for them all to leave. That is exactly the shape of
the problem - several analyses may read one build's CLF output simultaneously, but
the run that rebuilds it must be alone.

Where the lock file lives, and why it is NOT inside clf_analysis
---------------------------------------------------------------
``<build>/.clf_analysis.lock``, a sibling of the directory it guards, never inside
it. This looks like a detail and is not. On POSIX a file descriptor survives
unlinking, so if the lock file lived inside ``clf_analysis`` the rmtree would delete
it while the writer still held it - the writer keeps its lock on a now-nameless
inode, and the next process to arrive creates a *fresh* file at the same path and
locks that instead. Both would believe they hold the lock, which is worse than
having no lock at all because it looks like it works.

Readers fail fast rather than blocking
--------------------------------------
A CLF run takes hours. A reader that blocks on LOCK_EX would simply hang, and an
HTTP worker that hangs for hours is indistinguishable from one that has died. So
readers take the lock non-blocking and raise ``BuildLocked``, which the API layers
turn into the same 409 the admission guards return. Refusing in a second with a
sentence saying why beats succeeding on half-deleted input, and beats hanging.

The writer, by contrast, holds LOCK_EX across the whole rebuild and not merely the
rmtree: a half-rewritten directory is exactly as dangerous to read as one that is
mid-deletion, and the window between the two is where a naive implementation would
quietly let a reader in.

Cost is a single ``open`` plus a single ``flock`` per job - microseconds, taken once
when a job starts and never inside a per-layer loop. The standing constraint that we
cannot slow the main process down is not in tension with this.

⚠ This file is duplicated byte-for-byte into clf-analysis, python-defect-detect and
python-layer-alignments because the three repos share no package. If you change it,
change all three - ``tools/check_resolver_consistency.py`` exists in
python-defect-detect precisely because that kind of drift has already happened once
with ``build_artifact_resolver.py``.
"""

import errno
import fcntl
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

LOCK_FILENAME = ".clf_analysis.lock"


class BuildLocked(Exception):
    """Raised when the build's artifacts are held by another process.

    ``holder_hint`` is whatever the holder wrote into the lock file - free text, best
    effort, and never trusted for control flow. It exists so the refusal can say
    "clf-analysis, started 14:48" instead of "resource busy", because the second
    message sends someone hunting through logs.
    """

    def __init__(self, build_path, holder_hint=None):
        self.build_path = build_path
        self.holder_hint = holder_hint
        detail = f" ({holder_hint})" if holder_hint else ""
        super().__init__(
            f"The derived artifacts for {os.path.basename(build_path)} are being "
            f"rebuilt by another process{detail}. Wait for it to finish and retry."
        )


def lock_path_for(build_path):
    """The lock file guarding <build_path>/clf_analysis - a sibling, never inside it."""
    return os.path.join(build_path, LOCK_FILENAME)


def _read_hint(fd):
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        return os.read(fd, 512).decode("utf-8", "replace").strip() or None
    except OSError:
        return None


def _write_hint(fd, hint):
    """Record who holds the lock. Best effort - never fail a job over a diagnostic."""
    try:
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, hint.encode("utf-8")[:512])
        os.fsync(fd)
    except OSError:
        pass


@contextmanager
def _flock(build_path, operation, hint):
    if not os.path.isdir(build_path):
        raise FileNotFoundError(f"build folder does not exist: {build_path}")

    path = lock_path_for(build_path)
    # 0o666 so a lock taken by one service is writable by another running as a
    # different user; the file carries no data worth protecting.
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        try:
            fcntl.flock(fd, operation | fcntl.LOCK_NB)
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EACCES, errno.EWOULDBLOCK):
                raise BuildLocked(build_path, _read_hint(fd))
            raise
        if hint:
            _write_hint(fd, hint)
        yield path
    finally:
        # Closing the fd releases the lock; do it even if the body raised. The kernel
        # would do this at process exit anyway, which is the whole point of flock.
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


@contextmanager
def build_write_lock(build_path, hint=None):
    """Exclusive. Hold across the destructive rebuild, not just the delete."""
    with _flock(build_path, fcntl.LOCK_EX, hint or f"writer pid {os.getpid()}") as p:
        logger.info("Took exclusive lock on %s", p)
        yield p
        logger.info("Released exclusive lock on %s", p)


@contextmanager
def build_read_lock(build_path, hint=None):
    """Shared. Several readers may hold it at once; a writer waits for all of them."""
    with _flock(build_path, fcntl.LOCK_SH, hint or f"reader pid {os.getpid()}") as p:
        logger.debug("Took shared lock on %s", p)
        yield p
