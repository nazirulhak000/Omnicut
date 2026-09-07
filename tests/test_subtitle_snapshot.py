"""
Snapshot fixture test for SubtitleEngine to ensure byte/semantic parity across refactoring.
"""

from pathlib import Path
from scripts.subtitle_engine import SubtitleEngine


def test_subtitle_engine_ass_snapshot(tmp_path):
    """Generates ASS from a comprehensive fixture and asserts key structural blocks."""
    cues = [
        {"id": 1, "start": 0.0, "end": 1.5, "text": "ใครกำลังมองหาสายชาร์จ", "sfx": "whoosh"},
        {"id": 2, "start": 1.5, "end": 3.2, "text": "ชาร์จเร็ว 66W แม่เหล็กแน่น", "sfx": "pop"},
        {"id": 3, "start": 3.2, "end": 4.8, "text": "ราคาพิเศษวันนี้ 149 บาท", "sfx": "cash"}
    ]
    overlays = [
        {
            "id": "hook_1",
            "type": "hook_header",
            "start": 0.0,
            "end": 3.0,
            "brand": "Esseger",
            "model": "Magnetic Pro 3-in-1",
            "label": "ตัวจบทุกปัญหา",
            "style": {"preset": "capsule_pill", "theme": "black_gold"},
            "motion": {"in": "bounce", "loop": "pulse", "out": "fade", "accent": "underline"},
            "scrim": True
        },
        {
            "id": "txt_1",
            "type": "text",
            "start": 1.0,
            "end": 3.5,
            "text": "⚡ FAST CHARGE",
            "position": "center",
            "animation": "pop",
            "pill": {"preset": "cyberpunk_neon", "pad_x_em": 0.35, "pad_y_em": 0.15}
        }
    ]

    out_file = tmp_path / "snapshot.ass"
    ass_path, micro_cues = SubtitleEngine.generate_ass(
        cues=cues,
        output_ass_path=str(out_file),
        font_name="IBMPlex",
        overlays=overlays,
        bilingual=True,
        caption_position="bottom",
        caption_scale=1.0
    )

    assert Path(ass_path).exists()
    content = Path(ass_path).read_text(encoding="utf-8")

    # Semantic & Structural validations
    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "[V4+ Styles]" in content
    assert "Style: TikTokWhite" in content
    assert "Style: HookHeader" in content
    assert "Style: TextOverlayMain" in content
    assert "[Events]" in content
    assert "Dialogue:" in content
    assert len(micro_cues) >= 3


# ----------------------------------------------------------------------
# Security: user/scraper-controlled text must never inject its own ASS
# override tags. Product names come straight from scraped Shopee/TikTok
# listings, and captions/on_screen text come from the AI script generator
# working off that same scraped data -- an unescaped `{`, `}` or `\` in any
# of it would let a listing forge \c/\pos/\r override tags into the
# rendered subtitle. ASS's own escape (`\{`, `\}`, doubled backslash) must
# survive the whole pipeline: wrapping, kinetic-highlighting, and hook/
# overlay banner rendering.
# ----------------------------------------------------------------------

_INJECTION_ATTEMPT = r"Cool Mic {\c&HFF0000&\pos(9999,9999)}INJECTED{\r} end"


def _assert_no_raw_override_survived(content: str):
    """
    The literal attacker payload (unescaped brace-and-backslash run) must not
    appear anywhere in the output -- if it does, libass will read it as a
    real override tag rather than literal punctuation. Matched case-
    insensitively since some render paths (e.g. the hook banner tiers)
    legitimately uppercase their text as a style choice unrelated to escaping.
    """
    lowered = content.lower()
    assert r"{\c&hff0000&\pos(9999,9999)}" not in lowered
    assert r"{\r}" not in lowered
    # The escaped form (ASS's own backslash-escape for braces, and a doubled
    # backslash for the literal backslash) must be present instead -- proof
    # the text made it through as literal characters, not silently dropped.
    assert r"\{\\c&hff0000&\\pos(9999,9999)\}" in lowered
    assert r"injected\{\\r\}" in lowered or r"injected\{ \}" in lowered


def test_caption_text_with_override_syntax_renders_as_literal_text(tmp_path):
    """A caption line containing raw ASS override syntax must render literally."""
    cues = [
        {"id": 1, "start": 0.0, "end": 2.0, "text": _INJECTION_ATTEMPT},
    ]
    out_file = tmp_path / "injection_caption.ass"
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=cues,
        output_ass_path=str(out_file),
        font_name="IBMPlex",
        overlays=[],
        bilingual=False,
        caption_position="bottom",
    )
    content = Path(ass_path).read_text(encoding="utf-8")
    _assert_no_raw_override_survived(content)


def test_bilingual_translation_with_override_syntax_renders_as_literal_text(tmp_path, monkeypatch):
    """The English line (from the translator) must be escaped the same way as Thai."""
    from scripts.translator import SubtitleTranslator

    monkeypatch.setattr(
        SubtitleTranslator, "translate_batch",
        classmethod(lambda cls, texts: [_INJECTION_ATTEMPT for _ in texts]),
    )

    cues = [
        {"id": 1, "start": 0.0, "end": 2.0, "text": "สวัสดีครับ"},
    ]
    out_file = tmp_path / "injection_bilingual.ass"
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=cues,
        output_ass_path=str(out_file),
        font_name="IBMPlex",
        overlays=[],
        bilingual=True,
        caption_position="bottom",
    )
    content = Path(ass_path).read_text(encoding="utf-8")
    _assert_no_raw_override_survived(content)


def test_hook_banner_text_with_override_syntax_renders_as_literal_text(tmp_path):
    """A scraped product/brand/model/label name must not inject its own override tags."""
    cues = [{"id": 1, "start": 0.0, "end": 2.0, "text": "ทดสอบ"}]
    out_file = tmp_path / "injection_hook.ass"
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=cues,
        output_ass_path=str(out_file),
        font_name="IBMPlex",
        hook_brand=_INJECTION_ATTEMPT,
        hook_model="",
        hook_label="",
        hook_duration=2.0,
        bilingual=False,
        caption_position="bottom",
    )
    content = Path(ass_path).read_text(encoding="utf-8")
    _assert_no_raw_override_survived(content)


def test_text_overlay_with_override_syntax_renders_as_literal_text(tmp_path):
    """A freeform text overlay must not inject its own override tags."""
    cues = [{"id": 1, "start": 0.0, "end": 2.0, "text": "ทดสอบ"}]
    out_file = tmp_path / "injection_overlay.ass"
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=cues,
        output_ass_path=str(out_file),
        font_name="IBMPlex",
        text_overlays=[{"text": _INJECTION_ATTEMPT, "position": "middle"}],
        bilingual=False,
        caption_position="bottom",
    )
    content = Path(ass_path).read_text(encoding="utf-8")
    _assert_no_raw_override_survived(content)


def test_spec_bar_on_screen_text_with_override_syntax_renders_as_literal_text(tmp_path):
    """The on-screen spec bar (AI-script text derived from scraped data) must be escaped too."""
    cues = [
        {"id": 1, "start": 0.0, "end": 2.0, "text": "ทดสอบ", "on_screen": _INJECTION_ATTEMPT},
    ]
    out_file = tmp_path / "injection_specbar.ass"
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=cues,
        output_ass_path=str(out_file),
        font_name="IBMPlex",
        overlays=[],
        bilingual=False,
        caption_position="bottom",
    )
    content = Path(ass_path).read_text(encoding="utf-8")
    _assert_no_raw_override_survived(content)
