"""Real Chromium checks for timeline UX #2: filmstrip, cursor-anchored zoom, multi-select.

Drives the production EditorShell (``editor_shell_audit.html``) with an isolated
in-memory API. Every file is generated under ``.tmp`` and removed afterwards;
nothing is written to 03_Projects / 04_Exports.
"""

from __future__ import annotations

from contextlib import contextmanager
import io
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image
from playwright.sync_api import sync_playwright

from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import vite_fs_url

CLIP_SECONDS = 2.0
PRESETS = (10, 25, 50, 100, 200, 400, 800)
TILE_COLORS = ((200, 60, 60), (60, 200, 60), (60, 60, 200), (200, 200, 60), (60, 200, 200), (200, 60, 200))


def _sprite_png(count: int) -> bytes:
    """Horizontal sprite of `count` solid, distinct 48x85 tiles (what the backend would return)."""
    sprite = Image.new("RGB", (48 * count, 85))
    for i in range(count):
        sprite.paste(Image.new("RGB", (48, 85), TILE_COLORS[i % len(TILE_COLORS)]), (48 * i, 0))
    buffer = io.BytesIO()
    sprite.save(buffer, format="PNG")
    return buffer.getvalue()


def _manifest(clip_url: str, starts: list[float], overrides: dict[int, dict] | None = None) -> dict:
    overrides = overrides or {}
    return {
        "project_name": "editor-audit",
        "clip_list": [
            {"source_path": clip_url, "trim_start": start, "trim_end": round(start + CLIP_SECONDS, 3),
             "duration": CLIP_SECONDS, **overrides.get(index, {})}
            for index, start in enumerate(starts)
        ],
        "transitions": [],
        "total_duration": CLIP_SECONDS * len(starts),
        "cues": [],
        "artifacts": {},
        "show_watermark": False,
    }


@contextmanager
def editor_page(motion_fixture_url, starts, *, filmstrip="ok", viewport=None, overrides=None):
    """Yield (page, manifest, filmstrip_requests, page_errors) for the real editor."""
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("timeline-ux2-") as temp_root:
        source = create_clip_source(Path(temp_root))
        clip_url = vite_fs_url(base_url, source)
        manifest = _manifest(clip_url, starts, overrides)
        filmstrip_requests: list[dict] = []
        page_errors: list[str] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport=viewport or {"width": 1600, "height": 1100}, ignore_https_errors=True)
                page.add_init_script("localStorage.setItem('omnicut.previewQuality', 'smooth540')")
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def mock_api(route):
                    request = route.request
                    path = urlsplit(request.url).path
                    if path == "/api/projects/editor-audit" and request.method == "GET":
                        response = manifest
                    elif path == "/api/projects/editor-audit/state" and request.method == "PATCH":
                        manifest.update(request.post_data_json or {})
                        response = manifest
                    elif path == "/api/projects":
                        response = {"projects": ["editor-audit"]}
                    elif path == "/api/assets/all":
                        response = {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []}
                    elif path == "/api/hook-motion-presets":
                        response = {"catalog": {}, "default": None}
                    else:
                        response = {"tasks": [], "milestones": [], "custom": []}
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(response))

                def mock_filmstrip(route):
                    query = parse_qs(urlsplit(route.request.url).query)
                    count = int(query["count"][0])
                    filmstrip_requests.append({
                        "count": count,
                        "start": query.get("start", [None])[0],
                        "end": query.get("end", [None])[0],
                        "url": route.request.url,
                    })
                    if filmstrip == "fail":
                        route.fulfill(status=500, content_type="application/json", body='{"detail":"boom"}')
                        return
                    route.fulfill(
                        status=200, content_type="image/png", body=_sprite_png(count),
                        headers={"Cache-Control": "public, max-age=86400"},
                    )

                page.route("**/api/**", mock_api)
                page.route("**/api/editor/filmstrip**", mock_filmstrip)
                page.goto(
                    f"{base_url}/editor_shell_audit.html?clip={clip_url}",
                    wait_until="domcontentloaded",
                )
                page.locator('[data-timeline-item="clip"]:visible').first.wait_for(timeout=15000)
                yield page, manifest, filmstrip_requests, page_errors
            finally:
                browser.close()


def _clips(page):
    return page.locator('[data-timeline-item="clip"]:visible')


def _px_per_sec(page) -> float:
    width = _clips(page).first.evaluate("node => parseFloat(node.style.width)")
    return float(width) / CLIP_SECONDS


def _ruler(page):
    return page.locator('[title="คลิกหรือลากเพื่อเลื่อนหัวอ่าน"]:visible').first


def _save(page, manifest):
    with page.expect_response(lambda r: "/api/projects/editor-audit/state" in r.url and r.request.method == "PATCH"):
        page.get_by_title("บันทึกการแก้ไขลงโปรเจกต์ (Ctrl+S)").click()
    return [(c["trim_start"], c["trim_end"]) for c in manifest["clip_list"]]


# ---------------------------------------------------------------- filmstrip

def test_clip_filmstrip_is_lazy_cached_and_changes_no_layout(motion_fixture_url):
    # 24 clips with distinct trim windows: far more than fit on screen.
    starts = [round(i * 0.1, 1) for i in range(16)] + [round(i * 0.1, 1) for i in range(8)]
    with editor_page(motion_fixture_url, starts) as (page, manifest, requests, page_errors):
        page.wait_for_function(
            "() => document.querySelectorAll('[data-timeline-item=\"clip\"] [data-filmstrip=\"loaded\"]').length > 0",
            timeout=15000,
        )
        page.wait_for_timeout(600)
        first = list(requests)
        windows = {(r["start"], r["end"]) for r in first}
        # Visible clips only: fewer distinct windows than the 16 distinct clips.
        assert 0 < len(windows) < 16, windows
        # Clips with the same window share one sprite. Playwright's routing turns the
        # browser cache off, so the preload and the CSS use of one sprite show up as
        # two hits here (a plain Chromium run, checked separately, makes exactly one);
        # more than two hits for a URL would mean a per-clip request.
        per_url: dict[str, int] = {}
        for r in first:
            per_url[r["url"]] = per_url.get(r["url"], 0) + 1
        assert max(per_url.values()) <= 2, per_url
        # Tile count is bucketed by clip width (100 px at 50 px/s -> 2 slots -> count 2).
        assert {r["count"] for r in first} <= {2, 4}, first

        clip = _clips(page).first
        loaded = clip.locator('[data-filmstrip="loaded"]')
        assert loaded.count() == 1
        assert int(loaded.get_attribute("data-filmstrip-count")) >= 2
        assert loaded.locator(":scope > div").count() == 2  # one slot per ~48 px of clip

        # The strip is a background layer: hiding it must not move or resize the clip.
        box_with = clip.bounding_box()
        loaded.evaluate("node => { node.style.display = 'none'; }")
        box_without = clip.bounding_box()
        loaded.evaluate("node => { node.style.display = ''; }")
        assert box_with == box_without

        # Selecting, seeking and a context-menu round trip re-render clips but
        # must not request anything new.
        clip.click(position={"x": 30, "y": 20})
        _ruler(page).click(position={"x": 120, "y": 10}, modifiers=["Shift"])
        page.wait_for_timeout(700)
        assert len(requests) == len(first), (len(first), len(requests))
        assert clip.get_attribute("aria-pressed") == "true"

        # Scrolling the timeline brings further clips on screen: only then are they fetched.
        before = len(requests)
        _ruler(page).evaluate("""ruler => {
            let node = ruler;
            while (node && !(node.scrollWidth > node.clientWidth + 5 && /auto|scroll/.test(getComputedStyle(node).overflowX))) node = node.parentElement;
            node.scrollLeft = node.scrollWidth;
        }""")
        page.wait_for_timeout(900)
        assert len(requests) > before, "off-screen clips were never loaded after scrolling"
        assert not page_errors, page_errors


def test_clip_filmstrip_failure_leaves_clips_unchanged_and_is_not_retried(motion_fixture_url):
    with editor_page(motion_fixture_url, [0, 0.5, 1.0], filmstrip="fail") as (page, manifest, requests, page_errors):
        page.wait_for_timeout(1500)
        assert requests, "the endpoint was never asked"
        assert page.locator('[data-timeline-item="clip"] [data-filmstrip="loaded"]').count() == 0
        count = len(requests)
        # Re-render a lot: a failed sprite URL is remembered and not asked for again.
        for index in range(3):
            _clips(page).nth(index).click(position={"x": 30, "y": 20})
        _ruler(page).click(position={"x": 200, "y": 10}, modifiers=["Shift"])
        page.wait_for_timeout(800)
        assert len(requests) == count, (count, len(requests))
        # Clips are fully usable.
        assert _clips(page).count() == 3
        assert abs(_px_per_sec(page) - 50) < 0.5
        assert not page_errors, page_errors


# --------------------------------------------------------------------- zoom

def _time_under(page, cursor_x: float) -> float:
    ruler_box = _ruler(page).bounding_box()
    return (cursor_x - ruler_box["x"]) / _px_per_sec(page)


def test_continuous_zoom_keeps_time_under_cursor_and_presets_still_work(motion_fixture_url):
    # 48 s of clips: wide enough that the track scrolls, so the anchor is reachable.
    with editor_page(motion_fixture_url, [0, 0.5, 1.0, 1.5] * 6) as (page, manifest, requests, page_errors):
        assert abs(_px_per_sec(page) - 50) < 0.5
        ruler_box = _ruler(page).bounding_box()
        cursor_x = ruler_box["x"] + 5.3 * 50
        cursor_y = ruler_box["y"] + 80
        t_before = _time_under(page, cursor_x)
        assert abs(t_before - 5.3) < 0.01

        page.mouse.move(cursor_x, cursor_y)
        page.keyboard.down("Control")
        page.mouse.wheel(0, -100)
        page.keyboard.up("Control")
        page.wait_for_function("() => parseFloat(document.querySelector('[data-timeline-item=\"clip\"]').style.width) > 101")
        px = _px_per_sec(page)
        assert 55 < px < 70, px  # one notch ~ x1.22, not a preset
        assert all(abs(px - p) > 1 for p in PRESETS)
        assert abs(_time_under(page, cursor_x) - t_before) < 1 / 30, (_time_under(page, cursor_x), t_before)

        # Several quick notches: still anchored, and well past a preset step.
        for _ in range(7):
            page.keyboard.down("Control")
            page.mouse.wheel(0, -100)
            page.keyboard.up("Control")
        page.wait_for_function("() => parseFloat(document.querySelector('[data-timeline-item=\"clip\"]').style.width) > 380")
        page.wait_for_timeout(200)
        px_in = _px_per_sec(page)
        assert px_in > 190, px_in
        assert abs(_time_under(page, cursor_x) - t_before) < 1 / 30
        # Frame ticks appear once a frame is wide enough to tell apart.
        assert page.locator('[data-frame-ticks="frame"]:visible').count() >= 1

        # Zoom out around the same cursor.
        for _ in range(3):
            page.keyboard.down("Control")
            page.mouse.wheel(0, 100)
            page.keyboard.up("Control")
        page.wait_for_timeout(300)
        assert _px_per_sec(page) < px_in
        assert abs(_time_under(page, cursor_x) - t_before) < 1 / 30

        # Toolbar +/- and the + key still hop between presets from an in-between value.
        zoom_in = page.get_by_title(re.compile("^ซูมเข้า")).locator("visible=true").first
        zoom_out = page.get_by_title(re.compile("^ซูมออก")).locator("visible=true").first
        current = _px_per_sec(page)
        zoom_in.click()
        page.wait_for_timeout(200)
        expected_up = next(p for p in PRESETS if p > current * 1.01)
        assert abs(_px_per_sec(page) - expected_up) < 0.5, (current, _px_per_sec(page), expected_up)
        zoom_out.click()
        page.wait_for_timeout(200)
        expected_down = max(p for p in PRESETS if p < expected_up * 0.99)
        assert abs(_px_per_sec(page) - expected_down) < 0.5
        _clips(page).first.click(position={"x": 30, "y": 20})
        page.keyboard.press("+")
        page.wait_for_timeout(200)
        assert abs(_px_per_sec(page) - expected_up) < 0.5

        # "Fit" lands on the exact px/s that fills the track (any value, not a preset).
        page.get_by_title("ซูมให้เห็นทั้งคลิปพอดีจอ").locator("visible=true").first.click()
        page.wait_for_timeout(300)
        fitted = _px_per_sec(page)
        assert 10 <= fitted <= 800 and fitted != expected_up
        assert not page_errors, page_errors


# ------------------------------------------------------------- multi-select

def _pressed(page):
    return [bool(c.get_attribute("aria-pressed") == "true") for c in _clips(page).all()]


def _extras(page):
    return [c.locator("[data-multi-selected]").count() == 1 for c in _clips(page).all()]


def _banner(page):
    return page.locator('[data-testid="inspector-multi-select"]:visible')


def test_multi_select_toggle_range_escape_delete_one_undo(motion_fixture_url):
    with editor_page(motion_fixture_url, [0, 0.5, 1.0, 1.5]) as (page, manifest, requests, page_errors):
        clips = _clips(page)
        assert clips.count() == 4
        # Plain click: one clip, no banner.
        clips.nth(0).click(position={"x": 30, "y": 20})
        assert _pressed(page) == [True, False, False, False]
        assert _banner(page).count() == 0

        # Ctrl+click adds, the clicked clip becomes the primary (no tint), others are tinted.
        clips.nth(2).click(position={"x": 30, "y": 20}, modifiers=["Control"])
        assert _pressed(page) == [True, False, True, False]
        assert _extras(page) == [True, False, False, False]
        assert "เลือก 2 คลิป" in _banner(page).inner_text()
        # Ctrl+click on a member removes it again.
        clips.nth(0).click(position={"x": 30, "y": 20}, modifiers=["Control"])
        assert _pressed(page) == [False, False, True, False]
        assert _banner(page).count() == 0
        clips.nth(0).click(position={"x": 30, "y": 20}, modifiers=["Control"])

        # A plain click collapses the set.
        clips.nth(3).click(position={"x": 30, "y": 20})
        assert _pressed(page) == [False, False, False, True]

        # Shift+click selects a range from the last plain click.
        clips.nth(1).click(position={"x": 30, "y": 20})
        clips.nth(3).click(position={"x": 30, "y": 20}, modifiers=["Shift"])
        assert _pressed(page) == [False, True, True, True]
        assert "เลือก 3 คลิป" in _banner(page).inner_text()

        # Escape clears everything.
        page.keyboard.press("Escape")
        assert _pressed(page) == [False, False, False, False]
        assert _banner(page).count() == 0

        # Delete removes every selected clip as ONE undo step.
        clips.nth(0).click(position={"x": 30, "y": 20})
        clips.nth(1).click(position={"x": 30, "y": 20}, modifiers=["Control"])
        clips.nth(3).click(position={"x": 30, "y": 20}, modifiers=["Control"])
        assert "เลือก 3 คลิป" in _banner(page).inner_text()
        page.keyboard.press("Delete")
        assert clips.count() == 1
        assert _save(page, manifest) == [(1.0, 3.0)]
        page.keyboard.press("Control+z")
        assert clips.count() == 4, "one Ctrl+Z must bring all three clips back"
        page.keyboard.press("Control+Shift+z")
        assert clips.count() == 1
        assert not page_errors, page_errors


def test_multi_select_context_menu_keeps_set_and_trim_acts_on_primary_only(motion_fixture_url):
    with editor_page(motion_fixture_url, [0, 0.5, 1.0, 1.5]) as (page, manifest, requests, page_errors):
        clips = _clips(page)
        clips.nth(0).click(position={"x": 30, "y": 20})
        clips.nth(1).click(position={"x": 30, "y": 20}, modifiers=["Control"])
        assert _pressed(page) == [True, True, False, False]

        # Q/W act on the primary (clip 2, last clicked) only; the set survives.
        px = _px_per_sec(page)
        _ruler(page).click(position={"x": 3.0 * px, "y": 10}, modifiers=["Shift"])
        page.keyboard.press("w")
        page.wait_for_timeout(200)
        assert _pressed(page) == [True, True, False, False]
        assert "เลือก 2 คลิป" in _banner(page).inner_text()
        assert _save(page, manifest) == [(0, 2.0), (0.5, 1.5), (1.0, 3.0), (1.5, 3.5)]

        # Right-click on a member keeps the whole set and the menu says so.
        clips.nth(0).click(button="right", position={"x": 30, "y": 20})
        assert _pressed(page) == [True, True, False, False]
        menu_delete = page.get_by_role("button", name="ลบ 2 คลิป")
        assert menu_delete.is_visible()
        # Right-click on a clip outside the set replaces the selection.
        page.keyboard.press("Escape")
        clips.nth(3).click(button="right", position={"x": 30, "y": 20})
        assert _pressed(page) == [False, False, False, True]
        assert page.get_by_role("button", name="ลบคลิป").is_visible()
        page.keyboard.press("Escape")
        # Escape with a menu open closes only the menu.
        clips.nth(1).click(position={"x": 30, "y": 20})
        clips.nth(2).click(position={"x": 30, "y": 20}, modifiers=["Control"])
        clips.nth(1).click(button="right", position={"x": 30, "y": 20})
        page.keyboard.press("Escape")
        assert page.locator("[data-context-menu]").count() == 0
        assert _pressed(page) == [False, True, True, False]
        # The menu's delete removes the whole set.
        clips.nth(1).click(button="right", position={"x": 30, "y": 20})
        page.get_by_role("button", name="ลบ 2 คลิป").click()
        assert clips.count() == 2
        assert not page_errors, page_errors


# ------------------------------------------------- copy / paste clip settings

SETTINGS_SOURCE = {
    "trim_end": 4, "duration": 4, "speed": 2, "zoom": 1.2, "pan_x": 0.1,
    "brightness": 0.05, "contrast": 1.1, "saturation": 1.3,
    "transition_in": "fade", "transition_duration": 0.4,
    "keyframes": [{"time": 0, "zoom": 1.0}, {"time": 2, "zoom": 1.3, "easing": "ease_in_out"}],
}


def _clip_fields(manifest, index):
    clip = manifest["clip_list"][index]
    return {k: clip.get(k) for k in ("trim_start", "trim_end", "speed", "zoom", "pan_x", "brightness",
                                     "contrast", "saturation", "keyframes")}


def test_copy_paste_clip_settings_reaches_every_selected_clip_in_one_undo_step(motion_fixture_url):
    with editor_page(motion_fixture_url, [0, 0.5, 1.0, 1.5], overrides={0: SETTINGS_SOURCE}) as (
        page, manifest, requests, page_errors,
    ):
        clips = _clips(page)
        assert clips.count() == 4

        # Nothing copied yet: the context menu shows Paste disabled and says why.
        clips.nth(1).click(button="right", position={"x": 30, "y": 20})
        paste = page.get_by_role("button", name=re.compile(r"^วางการตั้งค่า\s+Ctrl\+Alt\+V$"))
        assert paste.is_visible() and paste.is_disabled()
        page.keyboard.press("Escape")
        page.keyboard.press("Control+Alt+v")
        assert page.get_by_text("ยังไม่ได้คัดลอกการตั้งค่าคลิป").first.is_visible()

        # Copy from clip 1 (the primary), then paste onto clips 2 and 3 selected together.
        clips.nth(0).click(position={"x": 30, "y": 20})
        page.keyboard.press("Control+Alt+c")
        assert page.get_by_text("คัดลอกการตั้งค่าคลิปแล้ว").first.is_visible()
        clips.nth(1).click(position={"x": 30, "y": 20})
        clips.nth(2).click(position={"x": 30, "y": 20}, modifiers=["Control"])
        assert "เลือก 2 คลิป" in _banner(page).inner_text()
        _save(page, manifest)  # baseline in the editor's own normalized form
        before = {i: _clip_fields(manifest, i) for i in range(4)}
        page.keyboard.press("Control+Alt+v")
        assert page.get_by_text("วางการตั้งค่าลง 2 คลิปแล้ว").first.is_visible()

        _save(page, manifest)
        for index in (1, 2):
            fields = _clip_fields(manifest, index)
            assert fields["speed"] == 2 and fields["zoom"] == 1.2 and fields["pan_x"] == 0.1
            assert (fields["brightness"], fields["contrast"], fields["saturation"]) == (0.05, 1.1, 1.3)
            # Trim is the clip's own, untouched.
            assert (fields["trim_start"], fields["trim_end"]) == (before[index]["trim_start"], before[index]["trim_end"])
            # Camera keyframes came across with their easing, scaled from the source clip's
            # 2 s played length to this clip's (2 s of source at the pasted 2x = 1 s).
            kf = fields["keyframes"]
            assert [round(p["time"], 3) for p in kf] == [0, 1.0], kf
            assert kf[1]["easing"] == "ease_in_out" and kf[1]["zoom"] == 1.3
        # The other clips are untouched.
        assert _clip_fields(manifest, 0) == before[0]
        assert _clip_fields(manifest, 3) == before[3]
        # The incoming transition came along: boundaries 1->2 and 2->3 are now fades.
        assert [t.get("type") for t in manifest["transitions"][:2]] == ["fade", "fade"], manifest["transitions"]

        # Pasting again changes nothing (and so must not add an undo step).
        page.keyboard.press("Control+Alt+v")
        assert page.get_by_text("ตรงกับที่คัดลอกไว้อยู่แล้ว").first.is_visible()

        # ONE Ctrl+Z puts both clips back.
        page.keyboard.press("Control+z")
        _save(page, manifest)
        for index in (1, 2):
            assert _clip_fields(manifest, index) == before[index], index
        page.keyboard.press("Control+Shift+z")
        _save(page, manifest)
        assert _clip_fields(manifest, 1)["speed"] == 2 and _clip_fields(manifest, 2)["speed"] == 2

        # The context menu does the same for a single clip outside the selection.
        clips.nth(3).click(button="right", position={"x": 30, "y": 20})
        page.get_by_role("button", name=re.compile(r"^วางการตั้งค่า\s")).click()
        _save(page, manifest)
        assert _clip_fields(manifest, 3)["speed"] == 2 and _clip_fields(manifest, 3)["zoom"] == 1.2
        # ...and copies from the clip it was opened on. (Pasted 2x speed and fades
        # shrank and overlapped the clips, so aim at the middle of the 50 px clip.)
        clips.nth(1).click(button="right", position={"x": 25, "y": 20})
        page.get_by_role("button", name=re.compile(r"^คัดลอกการตั้งค่า\s+Ctrl\+Alt\+C$")).click()
        assert page.get_by_text("คัดลอกการตั้งค่าคลิปแล้ว").first.is_visible()
        assert not page_errors, page_errors
