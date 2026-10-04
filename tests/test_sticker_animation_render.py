"""L3-09: sticker/effect entrance + exit must look the same in render as in preview.

Renders a real VideoEditor job in tmp_path (synthetic gray 1080x1920 footage,
a synthetic opaque-white RGBA sticker and a synthetic black effect clip), then
reads every frame and measures, per frame:

* sticker alpha (centre luma blended against the known background) and scale
  (width of the painted box vs. its resting width);
* effect alpha (multiply of black over gray at globalAlpha a = bg * (1 - a)).

Both are compared with overlay_anim_state, which the Canvas helper
frontend/src/lib/stickerAnimation.js reproduces exactly
(test_preview_render_parity.py::test_overlay_anim_state_js_matches_python).
"""

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

import scripts.video_editor as video_editor_module
from scripts.config import FPS
from scripts.video_editor import VideoEditor, overlay_anim_state

W, H = 1080, 1920
CROP_X, CROP_W = 300, 480          # covers both overlays (centred at x=540)
STK_START, STK_END = 1.0, 2.0      # visible 1.0 s -> 7-frame in, 6-frame out
FX_START, FX_END = 0.5, 1.5
STK_CY, FX_CY = int(H * 0.25), int(H * 0.7)
REST_W = 320                       # sticker_geometry(scale=1) at 1080 wide

# Alpha: x264 + limited-range rounding on a ~110-level span -> ~0.02; the
# fade filter itself is exact to 1/65535. Scale: the render rounds the
# transient width to even pixels and the box edge is thresholded -> <= 3 px
# of 320 (0.01).
ALPHA_TOL = 0.03
SCALE_TOL = 0.012


def _run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")


@pytest.mark.render_regression
def test_sticker_and_effect_entrance_exit_match_preview_math(tmp_path, monkeypatch):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and FFprobe are required for the render regression fixture")
    from PIL import Image

    effects_dir = tmp_path / "Effects"
    effects_dir.mkdir()
    effect_file = effects_dir / "fx_anim_probe.mov"
    sticker = tmp_path / "stk_probe.png"
    source = tmp_path / "gray.mp4"
    audio = tmp_path / "mix.wav"
    subtitles = tmp_path / "captions.ass"
    output = tmp_path / "render.mp4"
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    monkeypatch.setattr(video_editor_module, "EFFECTS_DIR", effects_dir)

    Image.new("RGBA", (240, 160), (255, 255, 255, 255)).save(sticker)
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
          "color=c=black:s=360x360:r=30:d=3.0", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
          str(effect_file)])
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
          f"color=c=0x808080:s={W}x{H}:r=30:d=3.0", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
          str(source)])
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
          "sine=frequency=440:sample_rate=48000:duration=3.0", "-c:a", "pcm_s16le", str(audio)])
    subtitles.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8",
    )

    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source)],
        total_duration=3.0,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subtitles),
        output_mp4_path=str(output),
        clip_list=[{"source_path": str(source), "trim_start": 0.0, "trim_end": 3.0, "duration": 3.0}],
        stickers=[{"id": "s", "path": str(sticker), "start": STK_START, "end": STK_END,
                   "normX": 0.5, "normY": 0.25, "scale": 1.0}],
        effects=[{"id": "fx", "effectId": "fx_anim_probe", "start": FX_START, "end": FX_END,
                  "normX": 0.5, "normY": 0.7, "scale": 1.0}],
        export_preset="post",
    )

    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(output), "-vf", f"crop={CROP_W}:{H}:{CROP_X}:0",
         "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
        check=True, capture_output=True,
    ).stdout
    # Raw (limited-range) Y plane: a full-range gray decode clips the
    # multiplied-black effect below 16 and bends the measured alpha.
    planes = np.frombuffer(raw, np.uint8).reshape(-1, H * CROP_W * 3 // 2)
    frames = planes[:, : H * CROP_W].reshape(-1, H, CROP_W).astype(float)
    assert frames.shape[0] >= 85, frames.shape

    cx = 540 - CROP_X
    bg = float(np.median(frames[0][STK_CY - 10:STK_CY + 10, cx - 10:cx + 10]))
    rest = int(round((STK_START + 0.5) * FPS))
    white = float(np.median(frames[rest][STK_CY - 10:STK_CY + 10, cx - 10:cx + 10]))
    fx_bg = float(np.median(frames[0][FX_CY - 10:FX_CY + 10, cx - 10:cx + 10]))
    assert white - bg > 80, (bg, white)

    def sticker_measure(n):
        f = frames[n]
        a = (float(np.median(f[STK_CY - 4:STK_CY + 4, cx - 4:cx + 4])) - bg) / (white - bg)
        row = f[STK_CY, :]
        amp = row.max() - bg
        if amp < 15:
            return a, None
        cols = np.nonzero(row - bg > amp * 0.5)[0]
        return a, (cols.max() - cols.min() + 1) / REST_W

    def effect_alpha(n):
        luma = float(np.median(frames[n][FX_CY - 4:FX_CY + 4, cx - 4:cx + 4]))
        black = float(np.median(frames[int(round((FX_START + 0.5) * FPS))][FX_CY - 4:FX_CY + 4, cx - 4:cx + 4]))
        return (fx_bg - luma) / (fx_bg - black)

    s0 = int(STK_START * FPS)
    e0 = int(STK_END * FPS)
    rows = []
    for n in [s0 - 1, s0, s0 + 1, s0 + 2, s0 + 3, s0 + 4, s0 + 5, s0 + 7, rest,
              e0 - 6, e0 - 4, e0 - 3, e0 - 1, e0, e0 + 1]:
        t = n / FPS
        exp_a, exp_s = overlay_anim_state(t, STK_START, STK_END)
        if t < STK_START - 1e-9 or t > STK_END + 1e-9:
            exp_a = 0.0
        got_a, got_s = sticker_measure(n)
        rows.append((n, round(t, 4), round(exp_a, 4), round(got_a, 4), round(exp_s, 4),
                     None if got_s is None else round(got_s, 4)))
        assert got_a == pytest.approx(exp_a, abs=ALPHA_TOL), rows[-1]
        if got_s is not None and exp_a > 0.3:
            assert got_s == pytest.approx(exp_s, abs=SCALE_TOL), rows[-1]
    print("sticker n,t,alpha_exp,alpha_render,scale_exp,scale_render:", rows)

    f0, f1 = int(FX_START * FPS), int(FX_END * FPS)
    fx_rows = []
    for n in [f0, f0 + 2, f0 + 4, f0 + 7, f1 - 6, f1 - 3, f1]:
        t = n / FPS
        exp_a, _ = overlay_anim_state(t, FX_START, FX_END, scale_in=False)
        got = effect_alpha(n)
        fx_rows.append((n, round(t, 4), round(exp_a, 4), round(got, 4)))
        assert got == pytest.approx(exp_a, abs=ALPHA_TOL), fx_rows[-1]
    print("effect n,t,alpha_exp,alpha_render:", fx_rows)
