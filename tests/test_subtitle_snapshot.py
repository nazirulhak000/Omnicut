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
