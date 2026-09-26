"""Behavioral tests for scripts/api_proxy.py.

The endpoint takes a caller-supplied clip path and turns it into a filesystem
read plus an ffmpeg encode, so the refusals get as much attention as the happy
path. Beyond that, two properties matter more than anything else here:

- asking for a proxy must never block the editor, so a clip with no proxy yet
  answers immediately with its master
- the response must never present a master as a proxy, or the render-side
  guard becomes the only thing between a 540p file and an export

PROJECTS_DIR and BASE_DIR are monkeypatched into tmp_path so no test touches
the real cache or media tree.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import scripts.api_proxy as api
import scripts.proxy_manager as pm

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not available on PATH"
)


def _make_clip(path: Path, seconds: float = 1.0) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"testsrc=size=320x240:rate=15:duration={seconds}",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(path)],
        capture_output=True, check=True, timeout=120,
    )
    return path


@pytest.fixture(autouse=True)
def _clear_in_flight():
    """The in-flight set is module state; a leak would make a later test think
    an encode was already running."""
    api._IN_FLIGHT.clear()
    yield
    api._IN_FLIGHT.clear()


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / "repo"
    raw = base / "01_Raw"
    projects = base / "03_Projects"
    raw.mkdir(parents=True)
    projects.mkdir(parents=True)

    monkeypatch.setattr(api, "BASE_DIR", base)
    monkeypatch.setattr(api, "CAPCUT_DRAFT_DIR", tmp_path / "drafts")
    monkeypatch.setattr(pm, "PROJECTS_DIR", projects)
    import scripts.api_videos as videos
    monkeypatch.setattr(videos, "BASE_DIR", base, raising=False)
    return raw


@pytest.fixture
def client(tree: Path) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _get(client: TestClient, source_path: str, **params):
    return client.get("/api/proxy/for-clip", params={"source_path": source_path, **params})


# ---------------------------------------------------------------------------
# Never block
# ---------------------------------------------------------------------------

def test_first_request_answers_with_the_master(client, tree):
    """The editor must be usable while the proxy encodes."""
    _make_clip(tree / "clip.mp4")
    body = _get(client, "01_Raw/clip.mp4").json()

    assert body["status"] in ("building", "master")
    assert body["is_proxy"] is False
    assert body["url"] == body["master_url"]
    assert "01_Raw/clip.mp4" in body["url"]


def test_ready_proxy_is_served_after_it_is_built(client, tree):
    master = _make_clip(tree / "clip.mp4")
    pm.ensure_proxy(master)

    body = _get(client, "01_Raw/clip.mp4").json()
    assert body["status"] == "ready"
    assert body["is_proxy"] is True
    assert body["url"] != body["master_url"]
    assert "editing-proxies" in body["url"]


def test_build_false_never_starts_an_encode(client, tree, monkeypatch):
    """A caller that only wants to know the current state must not trigger
    work as a side effect."""
    _make_clip(tree / "clip.mp4")
    monkeypatch.setattr(
        api, "_build_proxy_task",
        lambda *a, **k: pytest.fail("build=false must not encode"),
    )
    body = _get(client, "01_Raw/clip.mp4", build=False).json()
    assert body["status"] == "master"
    assert body["is_proxy"] is False


def test_repeat_requests_do_not_queue_a_second_encode(client, tree, monkeypatch):
    """A timeline asks about the same clip on every mount; each ask must not
    spawn another ffmpeg for work already in flight."""
    _make_clip(tree / "clip.mp4")
    started = []
    monkeypatch.setattr(api, "_build_proxy_task", lambda m, k: started.append(k))

    for _ in range(3):
        _get(client, "01_Raw/clip.mp4")

    assert len(started) == 1, f"expected one encode, got {len(started)}"


def test_background_task_releases_its_claim_on_failure(client, tree):
    """A failed encode must not leave the clip permanently marked as
    building, or it would never be retried."""
    junk = tree / "junk.mp4"
    junk.write_bytes(b"not a video")
    key = str(pm.proxy_path_for(junk))
    api._claim(key)

    api._build_proxy_task(str(junk), key)

    assert not api._is_building(key)


# ---------------------------------------------------------------------------
# Never present a master as a proxy
# ---------------------------------------------------------------------------

def test_master_response_is_not_flagged_as_a_proxy(client, tree):
    _make_clip(tree / "clip.mp4")
    body = _get(client, "01_Raw/clip.mp4", build=False).json()
    assert body["is_proxy"] is False
    assert body["url"] == body["master_url"]


def test_proxy_url_points_inside_the_proxy_cache(client, tree):
    master = _make_clip(tree / "clip.mp4")
    proxy = pm.ensure_proxy(master)
    body = _get(client, "01_Raw/clip.mp4").json()
    assert Path(body["url"]).name == proxy.name
    assert pm.is_proxy_path(proxy) is True


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hostile",
    ["../../../etc/passwd", "01_Raw/../../secret.mp4", r"..\..\config.py", "../config.py"],
)
def test_rejects_traversal(client, tree, hostile):
    assert _get(client, hostile).status_code in (400, 403, 404)


def test_rejects_a_path_outside_the_media_roots(client, tree, tmp_path):
    outside = tmp_path / "elsewhere.mp4"
    _make_clip(outside)
    assert _get(client, str(outside)).status_code == 403


def test_rejects_a_non_media_suffix(client, tree):
    (tree / "notes.txt").write_text("x", encoding="utf-8")
    assert _get(client, "01_Raw/notes.txt").status_code == 403


def test_missing_file_is_404(client, tree):
    assert _get(client, "01_Raw/nope.mp4").status_code == 404


def test_blank_path_is_400(client, tree):
    assert _get(client, "   ").status_code == 400


def test_error_text_does_not_leak_the_tree_layout(client, tree):
    res = _get(client, "01_Raw/nope.mp4")
    assert str(tree) not in res.text


# ---------------------------------------------------------------------------
# Cache status
# ---------------------------------------------------------------------------

def test_status_reports_an_empty_cache(client, tree):
    body = client.get("/api/proxy/status").json()
    assert body["status"] == "ok"
    assert body["count"] == 0 and body["bytes"] == 0


def test_status_counts_built_proxies(client, tree):
    pm.ensure_proxy(_make_clip(tree / "clip.mp4"))
    body = client.get("/api/proxy/status").json()
    assert body["count"] == 1 and body["bytes"] > 0
