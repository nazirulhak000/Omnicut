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


def test_3x4_crop_guard_respects_pan_y_on_textured_image(isolated_storage):
    """B4: textured background must not force crop_y=0 when no text overlay is rendered."""
    import numpy as np

    # Build a 1080x1920 textured image whose every row has high std (> 20)
    # Top band (0..239): distinct red/cyan checkerboard
    # Middle band (240..1679): distinct green/blue checkerboard
    # Bottom band (1680..1919): distinct yellow/magenta checkerboard
    arr = np.zeros((COVER_H, COVER_W, 3), dtype=np.uint8)
    xs = (np.arange(COVER_W) // 8) % 2
    # Top 0..239
    arr[:240, xs == 0] = [220, 20, 20]
    arr[:240, xs == 1] = [20, 220, 220]
    # Middle 240..1679
    arr[240:1680, xs == 0] = [20, 200, 40]
    arr[240:1680, xs == 1] = [20, 40, 200]
    # Bottom 1680..1919
    arr[1680:, xs == 0] = [230, 220, 20]
    arr[1680:, xs == 1] = [220, 20, 220]

    src_path = isolated_storage / "01_Raw" / "textured.png"
    src_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, mode="RGB").save(src_path)
    out_dir = isolated_storage / "05_Covers_Thumbnails"

    out_0, _ = render_pro_cover(
        custom_image_str=str(src_path),
        aspect_ratio="3:4",
        pan_y_pct=0.0,
        enable_hook_text=False,
        enable_badge=False,
        export_stem="pan0",
        output_dir=out_dir,
    )
    out_50, _ = render_pro_cover(
        custom_image_str=str(src_path),
        aspect_ratio="3:4",
        pan_y_pct=50.0,
        enable_hook_text=False,
        enable_badge=False,
        export_stem="pan50",
        output_dir=out_dir,
    )
    out_100, _ = render_pro_cover(
        custom_image_str=str(src_path),
        aspect_ratio="3:4",
        pan_y_pct=100.0,
        enable_hook_text=False,
        enable_badge=False,
        export_stem="pan100",
        output_dir=out_dir,
    )

    with Image.open(out_0) as im0, Image.open(out_50) as im50, Image.open(out_100) as im100:
        a0 = np.array(im0)
        a50 = np.array(im50)
        a100 = np.array(im100)
        assert im50.size == (PROFILE_W, PROFILE_H)
        # pan_y_pct=0 starts in the red/cyan top band (R > 180 on col 0)
        assert a0[10, 2, 0] > 170 and a0[10, 2, 1] < 60
        # pan_y_pct=50 starts at crop_y=240 (green/blue middle band, G > 160 on col 0, NOT red top!)
        assert a50[10, 2, 1] > 160 and a50[10, 2, 0] < 60
        # pan_y_pct=100 ends in the yellow/magenta bottom band (R > 170 on last row)
        assert a100[-10, 2, 0] > 170 and a100[-10, 2, 1] > 160


def test_3x4_crop_guard_protects_top_hook_overlay(isolated_storage):
    """B4: when top hook text IS rendered, pan_y_pct=100 still shifts crop_y up to protect it."""
    import numpy as np

    out_dir = isolated_storage / "05_Covers_Thumbnails"
    primary, path_3x4 = render_pro_cover(
        video_path_str=None,
        custom_image_str=None,
        aspect_ratio="both",
        pan_y_pct=100.0,
        enable_hook_text=True,
        enable_badge=False,
        hook_text="บรรทัดที่หนึ่ง\nบรรทัดที่สอง\nบรรทัดที่สาม",
        hook_position="top",
        template="neon",
        export_stem="hook_guard",
        output_dir=out_dir,
    )
    assert primary.exists() and path_3x4 is not None and path_3x4.exists()
    with Image.open(path_3x4) as img:
        assert img.size == (PROFILE_W, PROFILE_H)
        # Top 40px of 3:4 crop must remain clean background breathing margin (dark ~18,18,22), not clipped yellow text
        top_strip = img.crop((0, 0, PROFILE_W, 40)).convert("RGB")
        max_channel = int(np.array(top_strip).max())
        assert max_channel < 80, f"Top breathing margin clipped hook text (max RGB={max_channel})"
