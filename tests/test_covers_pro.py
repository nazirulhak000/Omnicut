"""
Unit tests for Pro 9:16 Cover Studio (Round COV-1).
Tests badge catalog, hook generator, Thai text wrapping, and Pillow 9:16 template rendering.
"""
import pytest
from pathlib import Path
from PIL import Image

from scripts.config import BASE_DIR, COVERS_DIR, STICKERS_DIR
from scripts.api_covers import (
    get_badges_catalog,
    generate_hook_ideas,
    _wrap_thai_text,
    render_pro_cover,
    COVER_W,
    COVER_H,
)


def test_get_badges_catalog():
    badges = get_badges_catalog()
    assert isinstance(badges, list)
    if list(STICKERS_DIR.glob("*.png")):
        assert len(badges) > 0
        first = badges[0]
        assert "id" in first
        assert "title" in first
        assert "url" in first
        assert first["url"].startswith("/api/media/")


def test_generate_hook_ideas():
    hooks = generate_hook_ideas(
        product_name="Logitech Wave Keys",
        angle_title="แก้ปวดข้อมือพิมพ์งาน",
        script_content="ปวดข้อมือเวลาทำงานไหม ลองตัวนี้"
    )
    assert len(hooks) >= 4
    # Ensure English brand is preserved
    found_brand = any("Logitech Wave Keys" in h["text"] for h in hooks)
    assert found_brand, "Brand name 'Logitech Wave Keys' should be preserved in hook text"
    
    # Check categories
    categories = [h["category"] for h in hooks]
    assert any("เตือนภัย" in c or "อยากรู้" in c for c in categories)
    assert any("คุ้มค่า" in c for c in categories)
    # Covers never carry a price / promo (TikTok rule).
    for h in hooks:
        assert "ราคา" not in h["text"] and "โปร" not in h["category"]


def test_wrap_thai_text():
    # Short text
    res = _wrap_thai_text("ของดีบอกต่อ", max_chars_per_line=15)
    assert len(res) == 1
    assert res[0] == "ของดีบอกต่อ"

    # Manual newline
    res = _wrap_thai_text("บรรทัดที่หนึ่ง\nบรรทัดที่สอง")
    assert len(res) == 2
    assert res[0] == "บรรทัดที่หนึ่ง"
    assert res[1] == "บรรทัดที่สอง"

    # Long text wrapping
    long_text = "อย่าเพิ่งซื้อสิ่งนี้ถ้ายังไม่ได้ลองใช้จริงกับตัวเอง"
    res = _wrap_thai_text(long_text, max_chars_per_line=14)
    assert len(res) >= 2


from scripts.api_covers import (
    COVER_W,
    COVER_H,
    PROFILE_W,
    PROFILE_H,
    _clean_cover_text,
    _wrap_thai_text,
    generate_hook_ideas,
    get_badges_catalog,
    render_pro_cover,
    find_raw_sources_for_video,
)


def test_render_pro_cover_all_templates(tmp_path):
    # Test rendering all 4 templates with solid background
    test_stem = "test_pro_unit_cover"

    for tmpl in ["neon", "yellow_bar", "modern_box", "minimal_bold"]:
        primary, path_3x4 = render_pro_cover(
            video_path_str=None,
            custom_image_str=None,
            template=tmpl,
            hook_text="อย่าเพิ่งซื้อตัวนี้\nถ้ายังไม่รู้สิ่งนี้!",
            sub_text="พิกัดลด 50% ในตะกร้า",
            hook_position="top",
            badge="badge_best_seller_3d.png",
            badge_position="top_left",
            export_stem=f"{test_stem}_{tmpl}",
        )
        assert primary.exists()
        assert primary.name.endswith(".jpg")

        # Verify dimensions 1080x1920
        with Image.open(primary) as img:
            assert img.size == (COVER_W, COVER_H), f"Cover size must be (1080, 1920), got {img.size}"

        # Cleanup
        try:
            primary.unlink()
        except Exception:
            pass


def test_render_pro_cover_profile_3x4(tmp_path):
    # Test 3:4 profile grid output (1080x1440)
    test_stem = "test_pro_3x4_cover"
    primary, path_3x4 = render_pro_cover(
        video_path_str=None,
        custom_image_str=None,
        aspect_ratio="3:4",
        pan_y_pct=25.0,
        enable_hook_text=False,  # Clean frame
        enable_badge=False,
        export_stem=test_stem,
    )
    assert primary.exists()
    assert "_3x4" in primary.name
    with Image.open(primary) as img:
        assert img.size == (PROFILE_W, PROFILE_H), f"3:4 Cover size must be (1080, 1440), got {img.size}"
    
    try:
        primary.unlink()
    except Exception:
        pass


def test_render_pro_cover_dual_export(tmp_path):
    # Test exporting both 9:16 and 3:4
    test_stem = "test_pro_dual_cover"
    primary, path_3x4 = render_pro_cover(
        video_path_str=None,
        custom_image_str=None,
        aspect_ratio="both",
        pan_y_pct=50.0,
        enable_hook_text=True,
        enable_badge=True,
        hook_text="ตัวจบที่ตามหา",
        export_stem=test_stem,
    )
    assert primary.exists()
    assert path_3x4 is not None and path_3x4.exists()

    with Image.open(primary) as img9:
        assert img9.size == (COVER_W, COVER_H)
    with Image.open(path_3x4) as img3:
        assert img3.size == (PROFILE_W, PROFILE_H)

    try:
        primary.unlink()
        path_3x4.unlink()
    except Exception:
        pass


def test_find_raw_sources_for_video():
    from scripts.config import BASE_DIR
    sample_mp4 = BASE_DIR / "04_Exports" / "Ready_to_post" / "logitech_wave_keys_ปัญหาก่อนใช้_1_20260905_160015.mp4"
    if sample_mp4.exists():
        sources = find_raw_sources_for_video(sample_mp4)
        assert isinstance(sources, list)
        assert len(sources) > 0
        assert "path" in sources[0]


def test_render_pro_cover_zoom_and_pan(tmp_path):
    # Test rendering with zoom_scale and 2D pan
    test_stem = "test_pro_zoom_cover"
    primary, _ = render_pro_cover(
        video_path_str=None,
        custom_image_str=None,
        pan_x_pct=25.0,
        pan_y_pct=10.0,
        zoom_scale=1.5,
        aspect_ratio="9:16",
        enable_hook_text=False,
        enable_badge=False,
        export_stem=test_stem,
    )
    assert primary.exists()
    with Image.open(primary) as img:
        assert img.size == (COVER_W, COVER_H)
    
    try:
        primary.unlink()
    except Exception:
        pass
