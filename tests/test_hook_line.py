"""
M1: the hook line -- one line of text on screen from the first frame, with the
brand / model / label nameplate following it at 1.8 s.

Pure-data tests for choosing the line and placing it, plus the ASS writer's side
of preview = render parity (the canvas preview draws the very same overlay
fields; see tests/test_preview_render_parity.py for the JS mirror of the
defaults used here).
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.hook_line import (  # noqa: E402
    HOOK_LINE_END_SEC,
    HOOK_LINE_MAX_CHARS,
    HOOK_LINE_MAX_WIDTH_PX,
    HOOK_LINE_ROLE,
    apply_hook_line,
    build_hook_line_overlay,
    choose_hook_line,
    merge_adjacent_spans,
)
from scripts.hook_styles import HOOK_TEMPLATES  # noqa: E402
from scripts.overlay_model import (  # noqa: E402
    HOOK_NAMEPLATE_DEFAULT_SEC,
    hook_overlay_from_legacy,
    migrate_to_overlays,
)
from scripts.subtitle.font_metrics import _measure_text_width_px  # noqa: E402
from scripts.subtitle_engine import SubtitleEngine  # noqa: E402

# Thai combining marks: a clause that starts with one was cut mid-syllable.
_THAI_COMBINING = re.compile("^[ัิ-ฺ็-๎]")


def _manifest(**extra):
    base = {"hook_brand": "Logitech", "hook_model": "Wave Keys", "hook_label": "Keyboard"}
    base.update(extra)
    return base


def _nameplate(overlays):
    return next(o for o in overlays if o["kind"] == "hook")


def _hook_line(overlays):
    return next((o for o in overlays if o.get("role") == HOOK_LINE_ROLE), None)


# ---------------------------------------------------------------- the text
def test_short_hook_title_is_used_whole():
    assert choose_hook_line({"hook_title": "ปวดข้อมือใช่ไหม"}) == "ปวดข้อมือใช่ไหม"


def test_source_priority_is_hook_title_then_hook_then_first_line():
    lines = [{"text": "บรรทัดแรกของสคริปต์"}]
    assert choose_hook_line({"hook_title": "ฮุกจากไตเติล", "hook": "ฮุกจากฟิลด์", "lines": lines}) == "ฮุกจากไตเติล"
    assert choose_hook_line({"hook_title": "", "hook": "ฮุกจากฟิลด์", "lines": lines}) == "ฮุกจากฟิลด์"
    assert choose_hook_line({"hook": "  ", "lines": lines}) == "บรรทัดแรกของสคริปต์"


def test_nothing_to_show_skips_the_layer():
    assert choose_hook_line(None) is None
    assert choose_hook_line({}) is None
    assert choose_hook_line({"hook_title": "   ", "lines": []}) is None


@pytest.mark.parametrize("title", [
    "ปวดข้อมือตอนพิมพ์งานทั้งวัน ต้องดูตัวนี้",
    "ใครเคยเจอปัญหาแบตหมดไวบ้างวันนี้เราจะมาดูกัน",
    "สายชาร์จแม่เหล็กแรงดูดสูงงานดีมากจริงๆ นะ",
])
def test_long_hook_is_cut_to_a_thai_safe_phrase_that_fits_one_line(title):
    line = choose_hook_line({"hook_title": title})
    assert line, "a long Thai hook should still yield a first phrase"
    assert len(line) <= HOOK_LINE_MAX_CHARS
    assert "\n" not in line and "..." not in line and "…" not in line
    # Cut at a word boundary: it is a prefix of the source and no syllable /
    # tone mark was left dangling at either end.
    assert title.replace(" ", "").startswith(line.replace(" ", ""))
    assert not _THAI_COMBINING.match(line)
    remainder = title[len(line):].lstrip()
    assert not _THAI_COMBINING.match(remainder)


def test_dangling_connective_is_trimmed_back():
    assert choose_hook_line({"hook_title": "ถ้าคุณใช้เมาส์ที่"}) == "ถ้าคุณใช้เมาส์"


def test_ellipsis_and_emoji_never_reach_the_screen():
    line = choose_hook_line({"hook_title": "ปวดข้อมือ... ใช่ไหม \U0001F525"})
    assert line == "ปวดข้อมือ ใช่ไหม"


@pytest.mark.parametrize("title", [
    "ลดเหลือ 199 บาท",          # price
    "ราคาพิเศษวันนี้เท่านั้น",     # price talk
    "ดีที่สุดในโลกการันตี 100%",  # exaggerated claim
])
def test_compliance_hits_skip_the_layer(title):
    assert choose_hook_line({"hook_title": title}) is None


# ---------------------------------------------------------- the look + fit
@pytest.mark.parametrize("template", sorted(HOOK_TEMPLATES))
def test_hook_line_wears_the_templates_largest_tier(template):
    nameplate = hook_overlay_from_legacy("Logi", "Wave", "Key", style={"template": template})
    line = build_hook_line_overlay("ปวดข้อมือใช่ไหม", nameplate)
    assert line is not None
    tiers = {k: v for k, v in HOOK_TEMPLATES[template]["tiers"].items()}
    largest = max(tiers.values(), key=lambda t: t["size_pct"])
    look = line["look"]
    # Same face, outline and colour as the template's biggest tier: no new
    # family and no new colour.
    assert look["font"] == (largest.get("font") or HOOK_TEMPLATES[template]["font"])
    assert look["outline_color"] == largest["outline_color"]
    assert look["outline_px"] == float(largest["outline_px"])
    assert look["color"] == ("accent" if largest["color"] is None else largest["color"])
    assert look["upper"] is False


def test_size_is_the_tier_size_or_scaled_down_but_never_below_70_percent():
    nameplate = hook_overlay_from_legacy("Logi", "Wave", "Key", style={"template": "bold_pop"})
    short = build_hook_line_overlay("ปวดข้อมือ", nameplate)
    long = build_hook_line_overlay("ปวดข้อมือตอนพิมพ์งาน", nameplate)
    assert short["look"]["size_pct"] >= long["look"]["size_pct"]
    # bold_pop's brand tier is 122% of a 70 px banner base = 85 px; the text
    # overlay's own base is 50 px, so the unscaled size_pct is 171.
    full = round(round(1080 * 0.065) * 122 / 100 / round(1080 * 0.0463) * 100)
    assert short["look"]["size_pct"] <= full
    assert long["look"]["size_pct"] >= int(full * 0.70) - 1


def test_line_fits_the_safe_width_including_its_outline():
    for template in sorted(HOOK_TEMPLATES):
        nameplate = hook_overlay_from_legacy("Logi", "Wave", "Key", style={"template": template})
        line = build_hook_line_overlay("ปวดข้อมือตอนพิมพ์งาน", nameplate)
        if line is None:
            continue  # allowed: cannot fit at >= 70% -> skipped, never shrunk further
        look = line["look"]
        px = round(round(1080 * 0.0463) * look["size_pct"] / 100)
        width = _measure_text_width_px("ปวดข้อมือตอนพิมพ์งาน", look["font"], px)
        if width is not None:
            assert width + 2 * look["outline_px"] <= HOOK_LINE_MAX_WIDTH_PX + 2, template


def test_position_is_top_centred_and_clear_of_the_edges_and_tiktok_ui():
    nameplate = hook_overlay_from_legacy("Logi", "Wave", "Key")
    line = build_hook_line_overlay("ปวดข้อมือใช่ไหม", nameplate)
    assert line["x"] == 0.5
    assert 180 / 1920 <= line["y"] <= 300 / 1920, "inside the top band, below the status bar"
    assert (1080 - HOOK_LINE_MAX_WIDTH_PX) / 2 >= 60, "left/right margin"


# ----------------------------------------------------------- timing / apply
def test_nameplate_follows_the_hook_line_for_three_seconds():
    overlays = migrate_to_overlays(_manifest())
    assert _nameplate(overlays)["end"] - _nameplate(overlays)["start"] == HOOK_NAMEPLATE_DEFAULT_SEC == 3.0

    out = apply_hook_line(overlays, {"hook_title": "ปวดข้อมือใช่ไหม"}, total_duration=30.0)
    line, plate = _hook_line(out), _nameplate(out)
    assert (line["start"], line["end"]) == (0.0, HOOK_LINE_END_SEC) == (0.0, 1.8)
    assert plate["start"] == 1.8
    assert plate["end"] == pytest.approx(4.8)


def test_explicit_hook_duration_wins_and_is_measured_from_the_nameplate_start():
    overlays = migrate_to_overlays(_manifest(hook_duration=4.5))
    out = apply_hook_line(overlays, {"hook_title": "ปวดข้อมือใช่ไหม"}, total_duration=30.0)
    plate = _nameplate(out)
    assert plate["start"] == 1.8
    assert plate["end"] == pytest.approx(1.8 + 4.5)


def test_nameplate_is_clipped_to_the_clip_length():
    overlays = migrate_to_overlays(_manifest())
    out = apply_hook_line(overlays, {"hook_title": "ปวดข้อมือใช่ไหม"}, total_duration=3.5)
    assert _nameplate(out)["end"] == 3.5


def test_no_hook_line_leaves_the_nameplate_at_zero():
    overlays = migrate_to_overlays(_manifest())
    for script in (None, {}, {"hook_title": "ลดเหลือ 199 บาท"}):
        out = apply_hook_line(overlays, script, total_duration=30.0)
        assert _hook_line(out) is None
        assert _nameplate(out)["start"] == 0.0
        assert _nameplate(out)["end"] == 3.0


def test_apply_is_idempotent_and_does_not_mutate_its_input():
    overlays = migrate_to_overlays(_manifest())
    before = json.dumps(overlays, sort_keys=True)
    once = apply_hook_line(overlays, {"hook_title": "ปวดข้อมือใช่ไหม"}, total_duration=30.0)
    assert json.dumps(overlays, sort_keys=True) == before
    twice = apply_hook_line(once, {"hook_title": "ปวดข้อมือใช่ไหม"}, total_duration=30.0)
    assert twice == once
    assert sum(1 for o in twice if o.get("role") == HOOK_LINE_ROLE) == 1


def test_clip_too_short_for_both_layers_is_left_alone():
    overlays = migrate_to_overlays(_manifest())
    out = apply_hook_line(overlays, {"hook_title": "ปวดข้อมือใช่ไหม"}, total_duration=2.0)
    assert _hook_line(out) is None and _nameplate(out)["start"] == 0.0


def test_hook_line_alone_when_the_project_has_no_nameplate():
    out = apply_hook_line(
        [], {"hook_title": "ปวดข้อมือใช่ไหม"}, total_duration=30.0,
        style={"style": {"template": "clean"}},
    )
    assert len(out) == 1 and out[0]["role"] == HOOK_LINE_ROLE
    assert out[0]["look"]["font"] == HOOK_TEMPLATES["clean"]["font"]


def test_merge_adjacent_spans_joins_the_hand_off_but_not_distant_spans():
    assert merge_adjacent_spans([(1.8, 4.8), (0.0, 1.8)]) == [(0.0, 4.8)]
    assert merge_adjacent_spans([(0.0, 1.8), (10.0, 12.0)]) == [(0.0, 1.8), (10.0, 12.0)]
    assert merge_adjacent_spans([(0.0, 0.0)]) == []


# ------------------------------------------------------------ the ASS side
def _dialogues(tmp_path, overlays, name="hook_line"):
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=[{"id": 1, "start": 0.0, "end": 3.0, "text": "ทดสอบ", "sfx": None}],
        output_ass_path=str(tmp_path / f"{name}.ass"),
        overlays=overlays,
        bilingual=False,
    )
    text = Path(ass_path).read_text(encoding="utf-8")
    return [l for l in text.splitlines() if l.startswith("Dialogue:")]


def _start_of(line):
    h, m, s = line.split(",", 2)[1].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def test_ass_has_the_line_at_frame_zero_and_the_nameplate_at_1_8s(tmp_path, monkeypatch):
    # generate_ass translates every micro-cue; keep the test offline.
    import scripts.translator as translator
    monkeypatch.setattr(
        translator.SubtitleTranslator, "translate_batch",
        classmethod(lambda cls, phrases, custom_dict=None: ["x"] * len(phrases)),
    )
    overlays = apply_hook_line(
        migrate_to_overlays(_manifest()), {"hook_title": "ปวดข้อมือใช่ไหม"}, total_duration=30.0,
    )
    events = _dialogues(tmp_path, overlays)
    line_events = [e for e in events if "ปวดข้อมือใช่ไหม" in e.replace("\\N", "")]
    assert line_events, "hook line text missing from the ASS"
    assert min(_start_of(e) for e in line_events) == 0.0
    assert max(_start_of(e) for e in line_events) < 0.01
    plate_events = [e for e in events if "HookHeader" in e]
    assert plate_events, "nameplate missing from the ASS"
    assert min(_start_of(e) for e in plate_events) >= 1.79
    # The hook line is gone by the time the nameplate shows.
    ends = [e.split(",", 3)[2] for e in line_events]
    assert all(end.startswith("0:00:01.8") or end.startswith("0:00:01.79") for end in ends), ends
    # One line only: no \N break inside the hook text.
    assert all("\\N" not in e.split(",,", 1)[-1] for e in line_events)


# ------------------------------------------------------------ the stage
def _run_stage(**ctx_kwargs):
    from unittest.mock import patch

    from scripts.pipeline_context import PipelineContext
    from scripts.stages.subtitle_stage import SubtitleStage

    values = {
        "product_name": "Logitech Wave Keys",
        "raw_video_path": "unused.mp4",
        "total_duration": 12.0,
        "cues": [{"start": 0.0, "end": 2.0, "text": "ทดสอบ"}],
        "script_data": {"hook_title": "ปวดข้อมือใช่ไหม", "lines": [{"text": "ปวดข้อมือใช่ไหม"}]},
    }
    values.update(ctx_kwargs)
    ctx = PipelineContext(**values)
    with patch.object(SubtitleEngine, "generate_ass", return_value=(None, [])) as gen:
        SubtitleStage.run(ctx)
    return ctx, gen.call_args.kwargs["overlays"]


def test_stage_adds_the_line_when_overlays_come_from_the_banner_scalars(tmp_path):
    ctx, passed = _run_stage(
        project_dir=tmp_path, hook_brand="Logitech", hook_model="Wave Keys", hook_label="Keyboard",
    )
    assert _hook_line(passed)["end"] == 1.8
    assert (_nameplate(passed)["start"], _nameplate(passed)["end"]) == (1.8, pytest.approx(4.8))
    assert ctx.effective_overlays == passed
    # One merged wash across both layers, not two stacked ones.
    assert ctx.scrim_spans == [(0.0, pytest.approx(4.8))]


def test_stage_adds_the_line_when_the_new_clip_form_sent_its_own_overlays(tmp_path):
    sent = migrate_to_overlays(_manifest())  # what NewClipPanel posts: nameplate at 0, default length
    _, passed = _run_stage(project_dir=tmp_path, overlays=sent)
    assert _hook_line(passed) is not None
    assert _nameplate(passed)["start"] == 1.8
    assert sent[0]["start"] == 0.0, "the request's own list is not mutated"


def test_stage_explicit_hook_duration_wins(tmp_path):
    _, passed = _run_stage(
        project_dir=tmp_path, hook_brand="Logitech", hook_model="Wave Keys", hook_label="Keyboard",
        hook_duration=4.5,
    )
    assert _nameplate(passed)["end"] - _nameplate(passed)["start"] == pytest.approx(4.5)


def test_stage_default_nameplate_length_is_three_seconds(tmp_path):
    _, passed = _run_stage(
        project_dir=tmp_path, hook_brand="Logitech", hook_model="Wave Keys", hook_label="Keyboard",
        script_data={"hook_title": "ลดเหลือ 199 บาท"},  # compliance hit -> no hook line
    )
    assert _hook_line(passed) is None
    assert (_nameplate(passed)["start"], _nameplate(passed)["end"]) == (0.0, 3.0)


def test_stage_leaves_a_later_pass_alone(tmp_path):
    sent = migrate_to_overlays(_manifest())
    _, passed = _run_stage(
        project_dir=tmp_path, overlays=sent,
        manifest={"micro_cues": [{"id": 1, "start": 0.0, "end": 1.0, "text": "x"}]},
    )
    assert _hook_line(passed) is None
    assert _nameplate(passed)["start"] == 0.0


# --------------------------------------------------------- JS-side defaults
def test_js_nameplate_default_matches_python():
    if not shutil.which("node"):
        pytest.skip("needs node")
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "default.mjs"
        mod = (ROOT / "frontend" / "src" / "lib" / "overlayModel.js").resolve().as_uri()
        runner.write_text(
            f"import {{ HOOK_NAMEPLATE_DEFAULT_SEC, migrateToOverlays }} from '{mod}';\n"
            "const o = migrateToOverlays({hook_brand: 'L', hook_model: 'W', hook_label: 'K'});\n"
            "console.log(JSON.stringify({d: HOOK_NAMEPLATE_DEFAULT_SEC, s: o[0].start, e: o[0].end}));\n",
            encoding="utf-8",
        )
        out = subprocess.run(["node", str(runner)], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    assert out.returncode == 0, out.stderr
    got = json.loads(out.stdout)
    assert got == {"d": HOOK_NAMEPLATE_DEFAULT_SEC, "s": 0, "e": HOOK_NAMEPLATE_DEFAULT_SEC}


def test_js_reads_the_hook_line_look_exactly_as_python_does():
    """
    The canvas preview and the ASS writer both flatten an overlay's look with
    resolveLook / resolve_look. The hook line is plain data in the manifest, so
    preview = render holds only if both flatteners agree on it, for every look.
    """
    if not shutil.which("node"):
        pytest.skip("needs node")
    from scripts.overlay_model import resolve_look

    overlays = []
    for template in sorted(HOOK_TEMPLATES):
        nameplate = hook_overlay_from_legacy("Logi", "Wave", "Key", style={"template": template})
        line = build_hook_line_overlay("ปวดข้อมือใช่ไหม", nameplate)
        if line is not None:
            overlays.append(line)
    assert overlays
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "look.mjs"
        mod = (ROOT / "frontend" / "src" / "lib" / "overlayModel.js").resolve().as_uri()
        runner.write_text(
            f"import {{ resolveLook }} from '{mod}';\n"
            "const overlays = JSON.parse(process.argv[2]);\n"
            "console.log(JSON.stringify(overlays.map(o => resolveLook(o.look, o.tiers[0].look))));\n",
            encoding="utf-8",
        )
        out = subprocess.run(
            ["node", str(runner), json.dumps(overlays)],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
    assert out.returncode == 0, out.stderr
    for overlay, js_look in zip(overlays, json.loads(out.stdout)):
        py_look = json.loads(json.dumps(resolve_look(overlay["look"], overlay["tiers"][0]["look"])))
        assert py_look == js_look, overlay["look"]["font"]
