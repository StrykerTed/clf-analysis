"""One CLF analysis per build at a time.

Why this needs pinning
----------------------
Both analyse routes accepted unconditionally and started a daemon thread, and
`run_analysis` opens by wiping the build's output directory:
`create_directory_structure(..., clear_existing=True)` rmtrees
<build>/clf_analysis wholesale, and `setup_abp_folders` rmtrees and re-extracts
the ABP contents directory. So a second analysis of the same build deletes the
first one's outputs while it is still writing them, and re-extracts the ABP the
first one is still reading. Nothing in any of the four services held a lock of
any kind; "run analyses sequentially" was an operating rule people had to
remember.

The deliberate difference from the layer-alignment service
----------------------------------------------------------
That service is guarded one-at-a-time, because its pipeline is driven through
process-global environment variables and *any* two jobs corrupt each other.
This one is guarded per build, because its pipeline holds no module-level
mutable state and writes only under its own build - two different builds are
genuinely independent, so refusing them would cost capability for nothing.

`test_a_different_build_is_still_allowed` exists to keep that difference
honest: if someone later copies the alignment service's single-flight guard
over here for symmetry, this test should stop them.
"""

import os
import sys
import threading

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _path in (_ROOT, os.path.join(_ROOT, "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import clf_analysis_api as api  # noqa: E402


@pytest.fixture
def client():
    api.app.config["TESTING"] = True
    with api.app.test_client() as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_module_state():
    """running_jobs and the admission table are module-level globals."""
    original_jobs = dict(api.running_jobs)
    yield
    api.running_jobs.clear()
    api.running_jobs.update(original_jobs)
    api._active_builds.clear()


@pytest.fixture
def blocking_worker(monkeypatch):
    """A worker that parks until released, so a job is genuinely in flight.

    It releases in a `finally` because that is the contract the real worker
    honours; a fake that forgot would make these tests pass for the wrong
    reason.
    """
    started = threading.Event()
    release = threading.Event()

    def fake_worker(job_id, build_id, holes_interval, create_composite_views):
        try:
            api.running_jobs[job_id]["status"] = "running"
            started.set()
            release.wait(timeout=10)
        finally:
            api._release_build_slot(build_id, job_id)

    monkeypatch.setattr(api, "run_analysis_background", fake_worker)
    yield started, release
    release.set()


def _analyze(client, build_id="515357"):
    return client.post("/api/analyze", json={"build_id": build_id})


def _analyze_by_build(client, build_id="515357"):
    return client.post(f"/api/builds/{build_id}/analyze", json={})


# --------------------------------------------------------------------------
# Admission
# --------------------------------------------------------------------------


def test_the_first_analysis_is_accepted(client, blocking_worker):
    started, _ = blocking_worker

    response = _analyze(client)

    assert response.status_code == 202, response.get_data(as_text=True)
    assert started.wait(timeout=5), "worker never started"


def test_a_second_analysis_of_the_same_build_is_refused(client, blocking_worker):
    started, _ = blocking_worker
    first = _analyze(client)
    assert started.wait(timeout=5)

    second = _analyze(client)

    assert second.status_code == 409, second.get_data(as_text=True)
    body = second.get_json()
    assert body["active_job_id"] == first.get_json()["job_id"]
    assert body["active_build_id"] == "515357"
    assert body["check_status_url"] == f"/api/jobs/{first.get_json()['job_id']}"


def test_a_different_build_is_still_allowed(client, blocking_worker):
    """The guard is per build on purpose - see the module docstring."""
    started, _ = blocking_worker
    _analyze(client, build_id="515357")
    assert started.wait(timeout=5)

    second = _analyze(client, build_id="515415")

    assert second.status_code == 202, second.get_data(as_text=True)
    assert set(api._active_builds) == {"515357", "515415"}


def test_a_refused_request_starts_nothing(client, blocking_worker):
    """A 409 must not leave a phantom queued job behind - the frontend polls
    running_jobs, and a job that never runs would sit at 'queued' forever."""
    started, _ = blocking_worker
    _analyze(client)
    assert started.wait(timeout=5)

    _analyze(client)

    assert len(api.running_jobs) == 1


def test_both_routes_share_one_slot_per_build(client, blocking_worker):
    """Admission lives in the shared helper precisely so it cannot be enforced
    on one route and forgotten on the other."""
    started, _ = blocking_worker
    _analyze(client, build_id="515357")
    assert started.wait(timeout=5)

    second = _analyze_by_build(client, build_id="515357")

    assert second.status_code == 409, second.get_data(as_text=True)


def test_the_slot_is_reusable_once_the_job_finishes(client, blocking_worker):
    started, release = blocking_worker
    _analyze(client)
    assert started.wait(timeout=5)
    assert _analyze(client).status_code == 409

    release.set()
    for _ in range(500):  # the worker releases in its finally, just after waking
        if not api._active_builds:
            break
        threading.Event().wait(0.01)

    started.clear()
    assert _analyze(client).status_code == 202


# --------------------------------------------------------------------------
# Releasing the slot - a leak blocks that build until the service restarts
# --------------------------------------------------------------------------


def test_the_worker_releases_when_the_analysis_reports_failure(monkeypatch):
    """`run_analysis` reports failure by returning success=False rather than
    raising, so the release cannot live on the happy path."""
    monkeypatch.setattr(
        api, "run_analysis",
        lambda **kwargs: {"success": False, "error": "no abp file found"},
    )
    job_id = "job-reports-failure"
    api.running_jobs[job_id] = {"job_id": job_id, "build_id": "515357", "status": "queued"}
    assert api._claim_build_slot("515357", job_id) is None

    api.run_analysis_background(job_id, "515357", 10, False)

    assert api.running_jobs[job_id]["status"] == "failed"
    assert "515357" not in api._active_builds, "a failed analysis blocked the build"


def test_the_worker_releases_when_the_analysis_raises(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("analysis exploded")

    monkeypatch.setattr(api, "run_analysis", boom)
    job_id = "job-raises"
    api.running_jobs[job_id] = {"job_id": job_id, "build_id": "515357", "status": "queued"}
    assert api._claim_build_slot("515357", job_id) is None

    api.run_analysis_background(job_id, "515357", 10, False)

    assert api.running_jobs[job_id]["status"] == "failed"
    assert "515357" not in api._active_builds, "a raising analysis blocked the build"


def test_the_route_releases_if_the_thread_cannot_start(client, monkeypatch):
    """Claiming the slot then failing to start the worker would hold it with
    nothing running behind it - the one way this guard could be worse than no
    guard at all."""
    def unstartable(*args, **kwargs):
        raise RuntimeError("cannot spawn thread")

    monkeypatch.setattr(api.threading, "Thread", unstartable)

    response = _analyze(client)

    assert response.status_code == 500
    assert not api._active_builds, "the slot leaked on a start failure"


def test_a_dead_worker_thread_does_not_hold_the_build_forever():
    """Belt and braces for the case the `finally` never runs - the thread was
    killed from outside."""
    dead = threading.Thread(target=lambda: None)
    dead.start()
    dead.join()
    api._active_builds["515357"] = {"job_id": "job-dead", "thread": dead}

    assert api._claim_build_slot("515357", "job-new") is None
    assert api._active_builds["515357"]["job_id"] == "job-new"


def test_a_live_worker_thread_keeps_the_build():
    release = threading.Event()
    alive = threading.Thread(target=lambda: release.wait(timeout=10))
    alive.start()
    api._active_builds["515357"] = {"job_id": "job-alive", "thread": alive}
    try:
        assert api._claim_build_slot("515357", "job-new") == "job-alive"
    finally:
        release.set()
        alive.join(timeout=5)


def test_releasing_is_keyed_to_the_holder():
    """A late release from a previous job must not free the build out from
    under whoever holds it now."""
    assert api._claim_build_slot("515357", "job-current") is None

    api._release_build_slot("515357", "job-previous")

    assert api._active_builds["515357"]["job_id"] == "job-current"
