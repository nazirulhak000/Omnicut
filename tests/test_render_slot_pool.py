"""Render slot pool (AGENTS rule 24): up to N clips render at once, FIFO.

Offline and deterministic -- only threads and Events, no pipeline, no FFmpeg.
"""

import threading
import time

import pytest
from fastapi import HTTPException

from scripts import render_jobs
from scripts import tiktok_enhancer


@pytest.fixture(autouse=True)
def fresh_pool(monkeypatch):
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    previous = render_jobs.render_concurrency()
    render_jobs.set_render_concurrency(4)
    yield
    render_jobs.set_render_concurrency(previous)


def _hold_slots(count, job_prefix="hold"):
    """Start `count` threads that each take a slot and keep it until released."""
    release = threading.Event()
    entered = threading.Semaphore(0)
    errors = []

    def holder(i):
        try:
            with render_jobs.render_slot(f"{job_prefix}-{i}"):
                entered.release()
                release.wait(10)
        except Exception as exc:  # pragma: no cover - surfaced via errors
            errors.append(exc)
            entered.release()

    threads = [threading.Thread(target=holder, args=(i,), daemon=True) for i in range(count)]
    for t in threads:
        t.start()
    return threads, release, entered, errors


def _wait_until(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return False


@pytest.mark.parametrize("raw, expected", [
    (None, 4), ("", 4), ("   ", 4), ("abc", 4), ("2.5", 4),
    ("1", 1), ("2", 2), (" 3 ", 3), ("4", 4),
    ("0", 1), ("-7", 1), ("5", 4), ("64", 4),
])
def test_concurrency_env_is_parsed_and_clamped(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv(render_jobs.RENDER_CONCURRENCY_ENV, raising=False)
    else:
        monkeypatch.setenv(render_jobs.RENDER_CONCURRENCY_ENV, raw)
    assert render_jobs.resolve_render_concurrency() == expected


def test_default_pool_size_follows_rule_24(monkeypatch):
    monkeypatch.delenv(render_jobs.RENDER_CONCURRENCY_ENV, raising=False)
    assert render_jobs.RENDER_CONCURRENCY_DEFAULT == 4
    assert render_jobs.resolve_render_concurrency() == 4


@pytest.mark.parametrize("size", [1, 2, 4])
def test_pool_admits_exactly_n_concurrent_holders(size):
    render_jobs.set_render_concurrency(size)
    lock = threading.Lock()
    state = {"active": 0, "max": 0}

    def work(i):
        with render_jobs.render_slot(f"job-{i}"):
            with lock:
                state["active"] += 1
                state["max"] = max(state["max"], state["active"])
            time.sleep(0.15)
            with lock:
                state["active"] -= 1

    # size + 2 workers, but never more than size + MAX_QUEUED_RENDERS so none
    # of them is refused with 429.
    workers = min(size + 2, size + render_jobs.MAX_QUEUED_RENDERS)
    threads = [threading.Thread(target=work, args=(i,)) for i in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert state["max"] == size
    assert render_jobs.active_count() == 0
    assert render_jobs.queued_count() == 0


def test_is_busy_reports_any_held_slot_not_only_a_full_pool():
    assert render_jobs.is_busy() is False
    threads, release, entered, errors = _hold_slots(1)
    assert entered.acquire(timeout=5)
    try:
        # One of four slots taken: delete/archive must still be refused.
        assert render_jobs.is_busy() is True
        assert render_jobs.active_count() == 1
        # And a new render still starts immediately (pool not full).
        with render_jobs.render_slot("fresh"):
            assert render_jobs.active_count() == 2
    finally:
        release.set()
        for t in threads:
            t.join(5)
    assert not errors
    assert render_jobs.is_busy() is False


def test_429_once_pool_full_and_queue_full():
    render_jobs.set_render_concurrency(2)
    holders, release_holders, entered, errors = _hold_slots(2)
    for _ in range(2):
        assert entered.acquire(timeout=5)

    waiters_done = []

    def waiter(i):
        with render_jobs.render_slot(f"wait-{i}"):
            waiters_done.append(i)

    waiters = [threading.Thread(target=waiter, args=(i,)) for i in range(render_jobs.MAX_QUEUED_RENDERS)]
    try:
        for t in waiters:
            t.start()
        assert _wait_until(lambda: render_jobs.queued_count() == render_jobs.MAX_QUEUED_RENDERS)

        with pytest.raises(HTTPException) as exc:
            with render_jobs.render_slot("one-too-many"):
                pass
        assert exc.value.status_code == 429
        assert render_jobs.queued_count() == render_jobs.MAX_QUEUED_RENDERS
    finally:
        release_holders.set()
        for t in holders + waiters:
            t.join(5)
    assert sorted(waiters_done) == list(range(render_jobs.MAX_QUEUED_RENDERS))
    assert not errors
    assert render_jobs.active_count() == 0 and render_jobs.queued_count() == 0


def test_waiting_job_is_marked_queued():
    render_jobs.set_render_concurrency(1)
    render_jobs.create_job("waiting-job")
    holders, release, entered, _ = _hold_slots(1)
    assert entered.acquire(timeout=5)
    got = []

    def wait_then_run():
        with render_jobs.render_slot("waiting-job"):
            got.append(True)

    t = threading.Thread(target=wait_then_run)
    try:
        t.start()
        assert _wait_until(lambda: render_jobs.queued_count() == 1)
        job = render_jobs.get_job("waiting-job")
        assert job["status"] == "queued"
        assert "1" in job["message"]  # tells the user how many clips fit
    finally:
        release.set()
        for th in holders + [t]:
            th.join(5)
    assert got == [True]


def test_waiters_are_served_fifo_so_a_batch_cannot_starve_a_single_render():
    """A thread that releases and immediately re-acquires (a batch worker
    moving to its next item) must not jump ahead of a render already queued."""
    render_jobs.set_render_concurrency(1)
    order = []
    batch_has_slot = threading.Event()
    single_queued = threading.Event()

    def batch_worker():
        with render_jobs.render_slot("batch-item-1"):
            batch_has_slot.set()
            assert single_queued.wait(5)
            order.append("batch-1")
        # Straight back into the queue for the next item.
        with render_jobs.render_slot("batch-item-2"):
            order.append("batch-2")

    def single_render():
        assert batch_has_slot.wait(5)
        threading.Timer(0.05, single_queued.set).start()
        with render_jobs.render_slot("single"):
            order.append("single")

    threads = [threading.Thread(target=batch_worker), threading.Thread(target=single_render)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert order == ["batch-1", "single", "batch-2"]


def test_slot_released_when_body_raises():
    render_jobs.set_render_concurrency(1)
    with pytest.raises(ValueError):
        with render_jobs.render_slot("boom"):
            raise ValueError("render blew up")
    assert render_jobs.active_count() == 0
    with render_jobs.render_slot("after"):
        assert render_jobs.is_busy()


def test_pool_cannot_be_resized_while_a_render_holds_a_slot():
    holders, release, entered, _ = _hold_slots(1)
    assert entered.acquire(timeout=5)
    try:
        with pytest.raises(RuntimeError):
            render_jobs.set_render_concurrency(2)
    finally:
        release.set()
        for t in holders:
            t.join(5)
    assert render_jobs.set_render_concurrency(2) == 2
    assert render_jobs.set_render_concurrency(99) == 4


def test_concurrent_create_job_does_not_break_pruning():
    for i in range(60):
        render_jobs.create_job(f"old-{i}")
        render_jobs.ACTIVE_JOBS[f"old-{i}"]["status"] = "completed"
    errors = []

    def spam(prefix):
        try:
            for i in range(200):
                render_jobs.create_job(f"{prefix}-{i}")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=spam, args=(f"t{n}",)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert not errors


# --------------------------------------------------------- per-project lock
def test_same_project_renders_serialise_but_different_projects_overlap():
    lock = threading.Lock()
    active = {}
    peak = {"same": 0, "total": 0}

    def render(name):
        handle = render_jobs.acquire_project_render_lock(name, channel_id="main")
        try:
            with lock:
                active[name] = active.get(name, 0) + 1
                peak["same"] = max(peak["same"], max(active.values()))
                peak["total"] = max(peak["total"], sum(active.values()))
            time.sleep(0.1)
            with lock:
                active[name] -= 1
        finally:
            handle.release()

    names = ["PROJ-A", "PROJ-A", "PROJ-B", "PROJ-C"]
    threads = [threading.Thread(target=render, args=(n,)) for n in names]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert peak["same"] == 1  # PROJ-A never rendered twice at once
    assert peak["total"] >= 2  # different projects ran together
    assert render_jobs._PROJECT_LOCKS == {}  # refcounted entries are cleaned up


def test_project_lock_serialises_identical_names():
    first = render_jobs.acquire_project_render_lock("DUP01-test_1", channel_id="main")
    acquired = threading.Event()

    def second():
        handle = render_jobs.acquire_project_render_lock("DUP01-test_1", channel_id="main")
        acquired.set()
        handle.release()

    t = threading.Thread(target=second)
    t.start()
    time.sleep(0.15)
    assert not acquired.is_set(), "a second render of the same project must wait"
    first.release()
    t.join(5)
    assert acquired.is_set()
    assert render_jobs._PROJECT_LOCKS == {}


def test_project_lock_wait_honours_cancel(monkeypatch):
    monkeypatch.setattr(render_jobs, "PROJECT_LOCK_POLL_SECONDS", 0.02)
    first = render_jobs.acquire_project_render_lock("CANCEL01_1")
    cancel = threading.Event()
    cancel.set()
    outcome = []

    def second():  # another render thread, waiting on the same project
        try:
            render_jobs.acquire_project_render_lock("CANCEL01_1", cancel_event=cancel)
            outcome.append("acquired")
        except render_jobs.RenderCancelled:
            outcome.append("cancelled")

    t = threading.Thread(target=second)
    t.start()
    t.join(5)
    assert outcome == ["cancelled"]
    first.release()
    assert render_jobs._PROJECT_LOCKS == {}


def test_project_lock_keys_secondary_channel_names_into_their_namespace():
    first = render_jobs.acquire_project_render_lock("clip_1", channel_id="ch2")
    try:
        assert render_jobs._project_lock_key("ch2/clip_1", "ch2") in render_jobs._PROJECT_LOCKS
        # Same bare name on main is a different folder -> independent lock.
        other = render_jobs.acquire_project_render_lock("clip_1", channel_id="main")
        other.release()
    finally:
        first.release()


def test_unnamed_project_needs_no_lock():
    handle = render_jobs.acquire_project_render_lock(None)
    handle.release()
    handle.release()  # idempotent
    assert render_jobs._PROJECT_LOCKS == {}


# --------------------------------------------------------- NVENC sessions
@pytest.mark.parametrize("raw, expected", [(None, 4), ("", 4), ("x", 4), ("0", 1), ("3", 3), ("8", 8), ("20", 8)])
def test_nvenc_session_cap_env_is_clamped(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv(tiktok_enhancer.NVENC_SESSIONS_ENV, raising=False)
    else:
        monkeypatch.setenv(tiktok_enhancer.NVENC_SESSIONS_ENV, raw)
    assert tiktok_enhancer.resolve_nvenc_sessions() == expected


class _FakeRun:
    """Stands in for subprocess.run inside tiktok_enhancer; tracks NVENC overlap."""

    def __init__(self, nvenc_fails=False):
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.codecs = []
        self.nvenc_fails = nvenc_fails

    def __call__(self, cmd, **kwargs):
        import subprocess
        codec = cmd[cmd.index("-c:v") + 1] if "-c:v" in cmd else None
        if codec is None:  # ffprobe audio probe
            return subprocess.CompletedProcess(cmd, 0, stdout='{"streams": [{"codec_name": "aac"}]}', stderr="")
        with self.lock:
            self.codecs.append(codec)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.05)
        finally:
            with self.lock:
                self.active -= 1
        if codec == "h264_nvenc" and self.nvenc_fails:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="OpenEncodeSessionEx failed: out of memory (10)")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def test_enhancer_caps_concurrent_nvenc_sessions(tmp_path, monkeypatch):
    fake = _FakeRun()
    monkeypatch.setattr(tiktok_enhancer, "HAS_NVENC", True)
    monkeypatch.setattr(tiktok_enhancer, "_NVENC_SESSIONS", threading.BoundedSemaphore(2))
    monkeypatch.setattr(tiktok_enhancer.subprocess, "run", fake)
    sources = []
    for i in range(6):
        src = tmp_path / f"in_{i}.mp4"
        src.write_bytes(b"x")
        sources.append(src)
    threads = [threading.Thread(target=tiktok_enhancer.enhance_video_for_tiktok, args=(s,)) for s in sources]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert fake.codecs.count("h264_nvenc") == 6
    assert fake.max_active == 2


def test_enhancer_falls_back_to_libx264_when_nvenc_session_fails(tmp_path, monkeypatch):
    fake = _FakeRun(nvenc_fails=True)
    monkeypatch.setattr(tiktok_enhancer, "HAS_NVENC", True)
    monkeypatch.setattr(tiktok_enhancer.subprocess, "run", fake)
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    out = tiktok_enhancer.enhance_video_for_tiktok(src)
    assert out.name == "in_tiktok_sharp.mp4"
    assert fake.codecs == ["h264_nvenc", "libx264"]
