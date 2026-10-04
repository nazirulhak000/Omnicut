"""Browser test of "pick product points on the preview" in the real EditorShell.

Drives the production EditorShell (same isolated in-memory API as
``test_editor_shell_browser.py``) with a tiny synthetic clip and checks the
Cutout point-picking contract end to end:

* pick mode is off by default, and with it off a click on the preview never adds
  a point;
* with pick mode on, clicking a known place on the preview stores the same
  normalized point at two different preview sizes, and draws a marker there;
* markers stay glued to the picked normalized position when the preview resizes;
* points and source/time reference survive save + reload; markers appear only
  while paused in pick mode and "ล้างจุด" clears both points and reference.

Everything runs against temp storage under ``.tmp`` and is removed afterwards.
The test skips, with the reason, when Node/Vite, Chromium or FFmpeg is missing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import pytest

from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.vite_fixture import ViteFixtureUnavailable

PROJECT = "editor-audit"
SAVE_TITLE = "บันทึกการแก้ไขลงโปรเจกต์ (Ctrl+S)"
STYLE_TAB_TITLE = "สไตล์"
CUTOUT_CHECKBOX = "เปิดใช้งานการตัดพื้นหลังสินค้า"
PICK_BUTTON = "เลือกจุดสินค้า"  # label flips to "เสร็จสิ้นการเลือกจุด" while pick mode is on
PICK_BUTTON_ANY = r"^(เลือกจุดสินค้า|เสร็จสิ้นการเลือกจุด)$"
CLEAR_BUTTON = "ล้างจุด"
MARKERS = '[data-testid="subject-point-markers"] > span'
PLAY_TOGGLE = 'button[aria-label="เล่นพรีวิว"], button[aria-label="หยุดพรีวิวชั่วคราว"]'
FRAME_CANVAS = 'canvas[data-preview-quality]'

# The place on the preview we click, as a fraction of the 9:16 frame.
TARGET = (0.3, 0.6)
TOLERANCE = 0.02  # frame is >= 280px wide, so 0.02 is a few pixels, not a loose bound

SIZES = ({"width": 1600, "height": 1100}, {"width": 1280, "height": 820})


@pytest.fixture()
def app_url(request):
    try:
        return request.getfixturevalue("motion_fixture_url")
    except ViteFixtureUnavailable as exc:
        pytest.skip(f"Vite fixture unavailable: {exc}")


def _frame_box(page) -> dict:
    """Bounding box of the visible preview frame (the canvas' 9:16 container)."""
    canvas = page.locator(f"{FRAME_CANVAS}:visible").first
    canvas.wait_for(timeout=10000)
    box = canvas.locator("xpath=..").bounding_box()
    assert box and box["width"] > 100 and box["height"] > 100, box
    return box


def _click_fraction(page, fx: float, fy: float) -> None:
    box = _frame_box(page)
    page.mouse.click(box["x"] + box["width"] * fx, box["y"] + box["height"] * fy)


def _marker_fractions(page) -> list[tuple[float, float]]:
    """Marker centres as fractions of the frame, measured from real layout."""
    box = _frame_box(page)
    centres = []
    markers = page.locator(MARKERS)
    for index in range(markers.count()):
        marker = markers.nth(index).bounding_box()
        centres.append((
            (marker["x"] + marker["width"] / 2 - box["x"]) / box["width"],
            (marker["y"] + marker["height"] / 2 - box["y"]) / box["height"],
        ))
    return centres


def _save(page, manifest: dict) -> dict:
    with page.expect_response(lambda response: (
        f"/api/projects/{PROJECT}/state" in response.url and response.request.method == "PATCH"
    )):
        page.get_by_title(SAVE_TITLE).click()
    return manifest.get("background_isolation") or {}


def _open_cutout_panel(page) -> None:
    page.get_by_title(STYLE_TAB_TITLE, exact=True).first.click()
    checkbox = page.get_by_label(CUTOUT_CHECKBOX)
    checkbox.wait_for(timeout=10000)
    if not checkbox.is_checked():
        checkbox.check()
    assert checkbox.is_checked()


def _close_to(actual: tuple[float, float], expected: tuple[float, float], label: str) -> None:
    assert abs(actual[0] - expected[0]) <= TOLERANCE and abs(actual[1] - expected[1]) <= TOLERANCE, (
        f"{label}: {actual} is not within {TOLERANCE} of {expected}"
    )


@pytest.mark.parametrize('preview_quality', ['master1080', 'smooth540'])
@pytest.mark.parametrize('camera,expected_prompt', [({}, TARGET),
    # The render flips before it crops, so pan_x=1 shows the right half of the
    # flipped frame: screen x 0.3 is raw x 540 - 540*0.3 = 378 -> 0.35 (L2-10;
    # this used to expect 0.85, the opposite side of the shot).
    ({'zoom': 2, 'pan_x': 1, 'mirror': True}, (0.35, 0.55))], ids=['identity', 'zoom-pan-mirror'])
def test_subject_points_pick_resize_save_reload_clear(app_url, monkeypatch, preview_quality, camera, expected_prompt):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.motion_capture.clip_pair import create_clip_source
    from tests.motion_capture.overlay_pair import vite_fs_url

    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    parsed = urlsplit(app_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    with temp_capture_dir("subject-points-browser-") as temp_root:
        try:
            source = create_clip_source(Path(temp_root))
        except RuntimeError as exc:
            pytest.skip(f"FFmpeg unavailable for the synthetic clip: {exc}")
        clip_url = vite_fs_url(base_url, source)
        manifest = {
            "project_name": PROJECT,
            "clip_list": [{"source_path": clip_url, "trim_start": 0, "trim_end": 2, "duration": 2, **camera}],
            "transitions": [],
            "total_duration": 2,
            "cues": [],
            "artifacts": {},
            "show_watermark": False,
        }

        with sync_api.sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:  # environment dependent
                pytest.skip(f"Chromium could not launch: {exc}")
            try:
                page = browser.new_page(viewport=SIZES[0], ignore_https_errors=True)
                page.add_init_script(f"localStorage.setItem('omnicut.previewQuality', '{preview_quality}')")
                page_errors: list[str] = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def mock_api(route):
                    request = route.request
                    path = urlsplit(request.url).path
                    if path == f"/api/projects/{PROJECT}" and request.method == "GET":
                        response = manifest
                    elif path == f"/api/projects/{PROJECT}/state" and request.method == "PATCH":
                        manifest.update(request.post_data_json or {})
                        response = manifest
                    elif path == "/api/projects":
                        response = {"projects": [PROJECT]}
                    elif path == "/api/assets/all":
                        response = {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []}
                    elif path == "/api/hook-motion-presets":
                        response = {"catalog": {}, "default": None}
                    else:
                        response = {"tasks": [], "milestones": [], "custom": []}
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(response))

                page.route("**/api/**", mock_api)
                page.goto(f"{base_url}/editor_shell_audit.html?clip={clip_url}", wait_until="domcontentloaded")
                page.locator('[data-timeline-item="clip"]:visible').first.wait_for(timeout=15000)
                _frame_box(page)

                _open_cutout_panel(page)
                pick = page.get_by_role("button", name=re.compile(PICK_BUTTON_ANY))
                pick.wait_for(timeout=10000)

                # 1. Pick mode off by default: a click on the preview adds nothing.
                assert pick.get_attribute("aria-pressed") in (None, "false")
                _click_fraction(page, *TARGET)
                page.wait_for_timeout(250)
                assert page.locator(MARKERS).count() == 0, "a click with pick mode off added a marker"
                assert not (_save(page, manifest).get("subject_points")), "pick-off click leaked a point into the project"

                # 2. Pick mode on: the same fractional click stores the same normalized point at two sizes.
                pick.click()
                assert pick.get_attribute("aria-pressed") == "true"
                page.wait_for_function("""() => {
                    const canvas = document.querySelector('canvas[data-preview-quality]');
                    return canvas?.dataset.subjectPromptSourceTime === '0';
                }""", timeout=10000)
                assert float(page.locator(FRAME_CANVAS).first.get_attribute('data-preview-time')) <= 0.01
                frame_widths = []
                stored_points = []
                for size in SIZES:
                    page.set_viewport_size(size)
                    page.wait_for_timeout(300)
                    frame_widths.append(_frame_box(page)["width"])
                    assert not page_errors, page_errors
                    if page.get_by_label("จุดสินค้า", exact=True).get_by_role("button", name=CLEAR_BUTTON).is_enabled():
                        page.get_by_label("จุดสินค้า", exact=True).get_by_role("button", name=CLEAR_BUTTON).click()
                        assert page.locator(MARKERS).count() == 0
                    play_toggle = page.locator(PLAY_TOGGLE).first
                    label_before = play_toggle.get_attribute("aria-label") if play_toggle.count() else None
                    _click_fraction(page, *TARGET)
                    try:
                        page.locator(MARKERS).first.wait_for(timeout=5000)
                    except sync_api.TimeoutError:
                        label_after = play_toggle.get_attribute("aria-label") if play_toggle.count() else None
                        pytest.fail(
                            f"pick-mode click at {TARGET} of the preview added no point at {size}; "
                            f"play/pause label {label_before!r} -> {label_after!r} "
                            "(a changed label means the full-frame play button took the click instead of the picker)"
                        )
                    assert page.locator(MARKERS).count() == 1
                    _close_to(_marker_fractions(page)[0], TARGET, f"marker at {size}")
                    config = _save(page, manifest)
                    assert config["prompt_reference_source"] == clip_url
                    assert config["prompt_reference_start"] == 0
                    points = config.get("subject_points") or []
                    assert len(points) == 1, config
                    assert points[0]["label"] == 1
                    stored_points.append((points[0]["x"], points[0]["y"]))
                    _close_to(stored_points[-1], expected_prompt, f"stored worker point at {size}")
                assert abs(frame_widths[0] - frame_widths[1]) > 20, f"preview did not change size: {frame_widths}"
                _close_to(stored_points[0], stored_points[1], "stored point across preview sizes")

                # 3. A marker stays on the same normalized spot when the preview resizes.
                page.set_viewport_size(SIZES[0])
                page.wait_for_timeout(300)
                _close_to(_marker_fractions(page)[0], TARGET, "marker after resizing back")

                # 4. Reload keeps the points (pick mode is transient and resets).
                page.reload(wait_until="domcontentloaded")
                page.locator('[data-timeline-item="clip"]:visible').first.wait_for(timeout=15000)
                assert page.locator(MARKERS).count() == 0, "markers leaked outside transient pick mode after reload"
                _open_cutout_panel(page)
                assert page.get_by_role("button", name=re.compile(PICK_BUTTON_ANY)).get_attribute("aria-pressed") in (None, "false")
                persisted = _save(page, manifest)
                assert len(persisted["subject_points"]) == 1
                _close_to((persisted["subject_points"][0]["x"], persisted["subject_points"][0]["y"]),
                          expected_prompt, "saved point after reload")
                assert persisted["prompt_reference_source"] == clip_url
                assert persisted["prompt_reference_start"] == 0

                # 5. After reload with pick mode off a click still adds nothing.
                _click_fraction(page, 0.7, 0.2)
                page.wait_for_timeout(250)
                assert page.locator(MARKERS).count() == 0, "markers leaked into ordinary playback"
                assert page.locator(PLAY_TOGGLE).first.get_attribute("aria-label") == "หยุดพรีวิวชั่วคราว"
                assert _save(page, manifest)["subject_points"] == persisted["subject_points"]
                # Re-entering the picker pauses playback and restores the saved
                # marker at its source coordinates, without inventing another point.
                pick = page.get_by_role("button", name=re.compile(PICK_BUTTON_ANY))
                pick.click()
                page.locator(MARKERS).first.wait_for(timeout=10000)
                assert page.locator(MARKERS).count() == 1
                _close_to(_marker_fractions(page)[0], TARGET, "marker after picker re-entry")
                # T5 hides the central play overlay while picking, so it cannot
                # cover the product. Visible markers above prove playback paused.
                assert page.locator(PLAY_TOGGLE).count() == 0
                assert page.locator('[data-subject-pick-mode="on"]').count() == 1
                pick.click()
                assert page.locator(MARKERS).count() == 0, "markers leaked after leaving picker"

                # 6. "ล้างจุด" clears markers and the saved project.
                page.get_by_label("จุดสินค้า", exact=True).get_by_role("button", name=CLEAR_BUTTON).click()
                assert page.locator(MARKERS).count() == 0
                assert not _save(page, manifest).get("subject_points")
                assert "prompt_reference_source" not in _save(page, manifest)
                page.reload(wait_until="domcontentloaded")
                page.locator('[data-timeline-item="clip"]:visible').first.wait_for(timeout=15000)
                page.wait_for_timeout(300)
                assert page.locator(MARKERS).count() == 0

                assert not page_errors, page_errors
            finally:
                browser.close()


def test_ready_cutout_allows_multiple_points_after_first_point_invalidates_artifact(app_url, monkeypatch):
    """Pick from the original while editing a ready/stale Cutout prompt."""
    from playwright.sync_api import sync_playwright
    from tests.motion_capture.clip_pair import create_clip_source
    from tests.motion_capture.overlay_pair import vite_fs_url

    monkeypatch.setenv('OMNICUT_ENCODER', 'cpu')
    parsed = urlsplit(app_url)
    base_url = f'{parsed.scheme}://{parsed.netloc}'
    with temp_capture_dir('subject-points-stale-browser-') as temporary:
        source = create_clip_source(Path(temporary))
        clip_url = vite_fs_url(base_url, source)
        config = {'schema_version': 1, 'enabled': True, 'engine': 'sam2',
                  'model': 'sam2.1_hiera_tiny', 'quality': 'balanced',
                  'artifact': {'schema_version': 1, 'status': 'ready', 'id': 'bgseq1-0123456789abcdef'}}
        manifest = {'project_name': PROJECT, 'background_isolation': config,
                    'clip_list': [{'id': 'picked-source', 'source_path': clip_url, 'trim_start': 0,
                                   'trim_end': 2, 'duration': 2, 'background_isolation': config}],
                    'transitions': [], 'total_duration': 2, 'cues': [], 'artifacts': {}, 'show_watermark': False}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport=SIZES[0], ignore_https_errors=True)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))

                def mock_api(route):
                    path = urlsplit(route.request.url).path
                    if path == f'/api/projects/{PROJECT}/state':
                        manifest.update(route.request.post_data_json or {})
                        response = manifest
                    elif path == f'/api/projects/{PROJECT}':
                        response = manifest
                    elif path.startswith('/api/background-isolation/sequences/'):
                        # A ready marker whose media is unavailable must not
                        # stop the user from correcting its prompt on the original.
                        route.fulfill(status=404, body='artifact unavailable')
                        return
                    elif path == '/api/assets/all':
                        response = {'sfx': [], 'music': [], 'fonts': [], 'stickers': [], 'luts': [], 'effects': []}
                    elif path == '/api/hook-motion-presets':
                        response = {'catalog': {}, 'default': None}
                    else:
                        response = {'projects': [PROJECT], 'tasks': [], 'custom': [], 'milestones': []}
                    route.fulfill(status=200, content_type='application/json', body=json.dumps(response))

                page.route('**/api/**', mock_api)
                page.goto(f'{base_url}/editor_shell_audit.html?clip={clip_url}', wait_until='domcontentloaded')
                page.locator('[data-timeline-item="clip"]:visible').first.wait_for(timeout=15000)
                page.wait_for_function("[...document.querySelectorAll('video')].some(v=>v.videoWidth>0 && v.readyState>=2)")
                _open_cutout_panel(page)
                page.get_by_role('button', name=re.compile(PICK_BUTTON_ANY)).click()
                _click_fraction(page, 0.3, 0.6)
                page.locator(MARKERS).first.wait_for(timeout=5000)
                saved = _save(page, manifest)
                assert saved['artifact']['status'] == 'stale', saved
                assert len(saved['subject_points']) == 1
                page.keyboard.down('Shift')
                try:
                    _click_fraction(page, 0.7, 0.4)
                finally:
                    page.keyboard.up('Shift')
                saved = _save(page, manifest)
                assert [p['label'] for p in saved['subject_points']] == [1, 0], saved
                assert page.locator(MARKERS).count() == 2
                _close_to(_marker_fractions(page)[0], (0.3, 0.6), 'positive marker')
                _close_to(_marker_fractions(page)[1], (0.7, 0.4), 'negative marker after stale')
                assert not errors, errors
            finally:
                browser.close()


def test_smooth_picker_uses_native_master_then_restores_padded_proxy(app_url):
    """A real 16:9 Master and padded 9:16 proxy must not share pick geometry."""
    import subprocess
    from tests.motion_capture.clip_pair import create_clip_source
    from tests.motion_capture.test_high_resolution_playback_browser import _serve_video
    from playwright.sync_api import sync_playwright

    parsed = urlsplit(app_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("subject-points-proxy-") as temporary:
        source = create_clip_source(Path(temporary), landscape=True)
        proxy = Path(temporary) / "proxy.mp4"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
                        "-vf", "scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2,setsar=1",
                        "-c:v", "libx264", "-preset", "ultrafast", str(proxy)], check=True, capture_output=True)
        master_url = "/api/media/picker-master.mp4"
        manifest = {"project_name": PROJECT, "clip_list": [{"source_path": master_url,
                    "trim_start": 0, "trim_end": 2, "duration": 2}], "transitions": [],
                    "total_duration": 2, "cues": [], "artifacts": {}, "show_watermark": False}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport=SIZES[0], ignore_https_errors=True)
                page.add_init_script("localStorage.setItem('omnicut.previewQuality', 'smooth540')")
                def mock_api(route):
                    path = urlsplit(route.request.url).path
                    if path == master_url:
                        return _serve_video(route, source)
                    if path == "/api/media/picker-proxy.mp4":
                        return _serve_video(route, proxy)
                    if path == "/api/proxy/for-clip":
                        response = {"url": "/api/media/picker-proxy.mp4", "is_proxy": True, "status": "ready"}
                    elif path == f"/api/projects/{PROJECT}" and route.request.method == "GET":
                        response = manifest
                    elif path == f"/api/projects/{PROJECT}/state" and route.request.method == "PATCH":
                        manifest.update(route.request.post_data_json)
                        response = {"ok": True, "project": PROJECT}
                    elif path == "/api/projects":
                        response = {"projects": [PROJECT]}
                    elif path == "/api/assets/all":
                        response = {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []}
                    elif path == "/api/hook-motion-presets":
                        response = {"catalog": {}, "default": None}
                    else:
                        response = {"tasks": [], "milestones": [], "custom": []}
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(response))
                page.route("**/api/**", mock_api)
                page.goto(f"{base_url}/editor_shell_audit.html?{urlencode({'clip': master_url})}", wait_until="domcontentloaded")
                try:
                    page.wait_for_function("Array.from(document.querySelectorAll('video')).some(v => v.currentSrc.includes('picker-proxy.mp4') && v.readyState >= 2)", timeout=10000)
                except Exception:
                    print(page.evaluate("""() => ({videos:Array.from(document.querySelectorAll('video')).map(v =>
                        ({src:v.currentSrc, ready:v.readyState,error:v.error?.message})),
                        canvas:document.querySelector('canvas[data-preview-quality]')?.dataset,
                        requests:performance.getEntriesByType('resource').filter(r => r.name.includes('/api/')).map(r=>r.name)})"""))
                    raise
                _open_cutout_panel(page)
                pick = page.get_by_role("button", name=re.compile(PICK_BUTTON_ANY))
                pick.click()
                page.wait_for_function("""() => {
                    const v = Array.from(document.querySelectorAll('video')).find(v => v.currentSrc.includes('picker-master.mp4'));
                    return v?.readyState >= 2 && !v.seeking && v.videoWidth > v.videoHeight && v.currentTime <= .04;
                }""")
                assert page.locator(FRAME_CANVAS).first.get_attribute("data-preview-quality") == "smooth540"
                _click_fraction(page, *TARGET)
                page.locator(MARKERS).first.wait_for(timeout=10000)
                assert page.locator(MARKERS).count() == 1
                pick.click()
                page.wait_for_function("Array.from(document.querySelectorAll('video')).some(v => v.currentSrc.includes('picker-proxy.mp4') && v.readyState >= 2)")
                assert page.locator(FRAME_CANVAS).first.get_attribute("data-preview-quality") == "smooth540"
                assert page.locator(MARKERS).count() == 0, "markers leaked into normal proxy preview"
                saved = _save(page, manifest)
                assert len(saved["subject_points"]) == 1
                assert saved["prompt_reference_source"] == master_url
                assert saved["prompt_reference_start"] == 0
                pick.click()
                page.locator(MARKERS).first.wait_for(timeout=10000)
                _close_to(_marker_fractions(page)[0], TARGET, "native Master marker after picker re-entry")
                pick.click()
                assert page.locator(MARKERS).count() == 0, "markers leaked after picker re-entry ended"
            finally:
                browser.close()
