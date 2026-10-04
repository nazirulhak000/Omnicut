"""Real Chromium check: the preview plays a voice with ripple cuts like the render.

Mounts the production EditorShell (``editor_shell_audit.html``) on an isolated
in-memory API whose project carries a synthetic voice wav (1 kHz bursts at
known source times) and ``voice_edit`` cuts. WebAudio is instrumented from an
init script (createBufferSource / start / stop and AudioParam automation) so
the test reads exactly what SequencePlayer handed the audio clock:

* with cuts: one AudioBufferSourceNode per kept range, started back to back at
  the keepRanges program positions (within 1 ms), from the kept source offsets,
  with the 8 ms linear ramps only at the edges a cut created; the picture clock
  stays on the audio clock (drift < 1 frame over 30 s of playback); pause stops
  every node;
* without cuts: no AudioBufferSourceNode for the voice, the <audio> element plays.

Everything is generated under ``.tmp`` and removed afterwards. Whether it SOUNDS
right (no clicks, natural joins) still needs a human listening test.
"""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from scripts.voice_cut_map import keep_ranges
from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import vite_fs_url

RATE = 48000
VOICE_SECONDS = 34.0
BURSTS = (1.0, 3.0, 5.0, 12.0, 20.0, 30.0)
CUTS = [
    {"id": "cut-a", "start": 2.0, "end": 2.5, "reason": "manual"},
    {"id": "cut-b", "start": 10.0, "end": 11.0, "reason": "manual"},
]
FADE = 0.008
CLIP_SECONDS = 4.0
CLIP_COPIES = 9  # 36 s of picture: longer than the 32.5 s cut voice

PROBE = """
(() => {
  const probe = { sources: [], params: [], ctx: null };
  window.__voiceProbe = probe;
  const Base = window.BaseAudioContext || window.AudioContext;
  const create = Base.prototype.createBufferSource;
  Base.prototype.createBufferSource = function () {
    const node = create.call(this);
    probe.ctx = this;
    const rec = { started: false, stopped: false };
    probe.sources.push(rec);
    const start = node.start.bind(node);
    node.start = (when = 0, offset = 0, duration) => {
      Object.assign(rec, {
        started: true, when, offset, duration,
        bufferDuration: node.buffer ? node.buffer.duration : null,
        ctxAtStart: this.currentTime,
      });
      return duration === undefined ? start(when, offset) : start(when, offset, duration);
    };
    const stop = node.stop.bind(node);
    node.stop = (...args) => { rec.stopped = true; return stop(...args); };
    return node;
  };
  ['setValueAtTime', 'linearRampToValueAtTime'].forEach((name) => {
    const orig = AudioParam.prototype[name];
    AudioParam.prototype[name] = function (value, time) {
      probe.params.push({ name, value, time });
      return orig.call(this, value, time);
    };
  });
  window.__voiceState = () => {
    const ctx = probe.ctx;
    const input = [...document.querySelectorAll('input[aria-label="เลื่อนตำแหน่งเล่นวิดีโอ"]')]
      .find((el) => el.offsetParent !== null);
    const audio = document.querySelector('audio');
    return {
      ctxTime: ctx ? ctx.currentTime : null,
      ctxState: ctx ? ctx.state : null,
      playhead: input ? Number(input.value) : null,
      audioPaused: audio ? audio.paused : null,
      sources: probe.sources.filter((s) => s.started).map(({ when, offset, duration, bufferDuration, ctxAtStart, stopped }) => (
        { when, offset, duration, bufferDuration, ctxAtStart, stopped })),
      params: probe.params,
    };
  };
})();
"""


def _write_voice(path: Path) -> None:
    """Mono 16-bit wav: silence with 60 ms 1 kHz bursts at BURSTS (source seconds)."""
    frames = bytearray()
    total = int(VOICE_SECONDS * RATE)
    burst_len = int(0.06 * RATE)
    starts = {int(b * RATE) for b in BURSTS}
    active_until = -1
    for i in range(total):
        if i in starts:
            active_until = i + burst_len
        value = int(12000 * math.sin(2 * math.pi * 1000 * i / RATE)) if i < active_until else 0
        frames += struct.pack("<h", value)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(bytes(frames))


def _manifest(clip_url: str, voice_url: str, cuts) -> dict:
    manifest = {
        "project_name": "editor-audit",
        "clip_list": [
            {"source_path": clip_url, "trim_start": 0, "trim_end": CLIP_SECONDS, "duration": CLIP_SECONDS}
            for _ in range(CLIP_COPIES)
        ],
        "transitions": [],
        "total_duration": CLIP_SECONDS * CLIP_COPIES,
        "audio_duration": VOICE_SECONDS,
        "cues": [],
        "artifacts": {"voice_audio": {"path": voice_url}},
        "show_watermark": False,
    }
    if cuts:
        manifest["voice_edit"] = {"schema_version": 1, "source": {"duration": VOICE_SECONDS}, "cuts": cuts}
        manifest["voice_edit_stale"] = False
    return manifest


def _open_editor(playwright, base_url, manifest, page_errors):
    browser = playwright.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, ignore_https_errors=True)
    page.add_init_script("localStorage.setItem('omnicut.previewQuality', 'smooth540')")
    page.add_init_script(PROBE)
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    def mock_api(route):
        request = route.request
        path = urlsplit(request.url).path
        if path == "/api/projects/editor-audit" and request.method == "GET":
            response = manifest
        elif path == "/api/projects/editor-audit/state" and request.method == "PATCH":
            response = manifest  # never persisted anywhere: in-memory only
        elif path == "/api/projects":
            response = {"projects": ["editor-audit"]}
        elif path == "/api/assets/all":
            response = {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []}
        elif path == "/api/hook-motion-presets":
            response = {"catalog": {}, "default": None}
        else:
            response = {"tasks": [], "milestones": [], "custom": []}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(response))

    page.route("**/api/**", mock_api)
    page.goto(f"{base_url}/editor_shell_audit.html", wait_until="domcontentloaded")
    page.locator('[data-timeline-item="clip"]:visible').first.wait_for(timeout=20000)
    page.wait_for_function(
        "() => [...document.querySelectorAll('input[aria-label=\"เลื่อนตำแหน่งเล่นวิดีโอ\"]')]"
        ".some((el) => el.offsetParent !== null && Number(el.max) > 30)",
        timeout=30000,
    )
    return browser, page


def _play_button(page):
    return page.locator('button[aria-label="เล่น (Space)"]:visible').first


def _pause_button(page):
    return page.locator('button[aria-label="หยุดชั่วคราว (Space)"]:visible').first


def _state(page):
    return page.evaluate("window.__voiceState()")


def _voice_sources(state):
    return [s for s in state["sources"] if s["bufferDuration"] and abs(s["bufferDuration"] - VOICE_SECONDS) < 0.01]


def _sync_offset(page, samples: int = 24) -> float:
    """Smallest (audio-clock program time - shown playhead) over a burst of samples.

    The shown playhead is published at most every 33 ms, so a single sample can
    lag by up to a frame; the minimum over a burst is the true offset.
    """
    offsets = []
    for _ in range(samples):
        state = _state(page)
        first = _voice_sources(state)[0]
        t0 = first["offset"]  # first kept range starts at source 0 = program 0
        audio_program = t0 + (state["ctxTime"] - first["when"])
        offsets.append(audio_program - state["playhead"])
        page.wait_for_timeout(17)
    return min(offsets, key=abs)


def test_voice_cuts_schedule_kept_ranges_on_the_audio_clock(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("voice-cut-preview-") as temp_root:
        root = Path(temp_root)
        voice = root / "voice.wav"
        _write_voice(voice)
        clip_url = vite_fs_url(base_url, create_clip_source(root))
        manifest = _manifest(clip_url, vite_fs_url(base_url, voice), CUTS)
        keep = keep_ranges(CUTS, VOICE_SECONDS)
        assert [(r["src_start"], r["src_end"], r["prog_start"]) for r in keep] == [
            (0, 2.0, 0), (2.5, 10.0, 2.0), (11.0, VOICE_SECONDS, 9.5),
        ]
        page_errors: list[str] = []
        with sync_playwright() as playwright:
            browser, page = _open_editor(playwright, base_url, manifest, page_errors)
            try:
                _play_button(page).click()
                page.wait_for_function("() => window.__voiceState().sources.length >= 3", timeout=15000)
                state = _state(page)
                assert state["ctxState"] == "running"
                assert state["audioPaused"] is True, "the uncut <audio> element must stay silent"
                nodes = _voice_sources(state)
                assert len(nodes) == len(keep), nodes

                # Program time the first node starts at (decode can finish a moment after play).
                t0 = nodes[0]["offset"] - keep[0]["src_start"] + keep[0]["prog_start"]
                assert 0 <= t0 < keep[0]["src_end"], t0
                w0 = nodes[0]["when"]
                for node, rng in zip(nodes, keep):
                    expected_when = w0 + max(0.0, rng["prog_start"] - t0)
                    expected_offset = rng["src_start"] + max(0.0, t0 - rng["prog_start"])
                    assert abs(node["when"] - expected_when) < 0.001, (node, rng)
                    assert abs(node["offset"] - expected_offset) < 1e-9, (node, rng)
                    assert abs(node["duration"] - (rng["src_end"] - expected_offset)) < 1e-9, (node, rng)
                    assert node["when"] >= node["ctxAtStart"], "no node may be handed over already late"

                # Ramps: out at the end of every range before a cut, in at the
                # start of every range after one, none at the file's own head/tail.
                params = state["params"]

                def has(name, value, time):
                    return any(p["name"] == name and abs(p["value"] - value) < 1e-6 and abs(p["time"] - time) < 0.001
                               for p in params)

                for i, rng in enumerate(keep):
                    start_ctx = w0 + (rng["prog_start"] - t0)
                    end_ctx = start_ctx + (rng["src_end"] - rng["src_start"])
                    if i > 0:
                        assert has("setValueAtTime", 0, start_ctx), f"range {i}: ramp starts from 0"
                        assert has("linearRampToValueAtTime", 1, start_ctx + FADE), f"range {i}: fade in"
                    if i < len(keep) - 1:
                        assert has("setValueAtTime", 1, end_ctx - FADE), f"range {i}: fade-out start"
                        assert has("linearRampToValueAtTime", 0, end_ctx), f"range {i}: fade out"
                last_end = w0 + (keep[-1]["prog_start"] - t0) + (keep[-1]["src_end"] - keep[-1]["src_start"])
                assert not has("linearRampToValueAtTime", 0, last_end), "no fade at the file's own tail"

                # Master clock = audio clock: the shown playhead follows the
                # scheduled voice and does not drift over 30 s of playback.
                page.wait_for_timeout(1500)
                early = _sync_offset(page)
                page.wait_for_timeout(29000)
                late = _sync_offset(page)
                print(f"voice-cut clock offset early={early * 1000:.1f} ms late={late * 1000:.1f} ms "
                      f"drift={(late - early) * 1000:.1f} ms")
                assert abs(early) < 1 / 30, early
                assert abs(late) < 1 / 30, late
                assert abs(late - early) < 1 / 30, (early, late)
                assert _state(page)["playhead"] > 30

                # Pause stops every scheduled voice node.
                _pause_button(page).click()
                page.wait_for_timeout(200)
                assert all(n["stopped"] for n in _voice_sources(_state(page)))
                assert page_errors == []
            finally:
                browser.close()


def test_no_cuts_keeps_the_audio_element_path(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("voice-cut-preview-") as temp_root:
        root = Path(temp_root)
        voice = root / "voice.wav"
        _write_voice(voice)
        clip_url = vite_fs_url(base_url, create_clip_source(root))
        manifest = _manifest(clip_url, vite_fs_url(base_url, voice), None)
        page_errors: list[str] = []
        with sync_playwright() as playwright:
            browser, page = _open_editor(playwright, base_url, manifest, page_errors)
            try:
                _play_button(page).click()
                page.wait_for_function(
                    "() => { const a = document.querySelector('audio'); return a && !a.paused && a.currentTime > 0.3; }",
                    timeout=15000,
                )
                page.wait_for_timeout(700)
                state = _state(page)
                assert state["audioPaused"] is False
                assert _voice_sources(state) == [], "no AudioBufferSourceNode may carry the voice without cuts"
                assert not [p for p in state["params"] if p["name"] == "linearRampToValueAtTime"]
                _pause_button(page).click()
                assert page_errors == []
            finally:
                browser.close()
