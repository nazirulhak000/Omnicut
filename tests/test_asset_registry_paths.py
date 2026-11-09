"""Asset registry freshness + loud font failures (audit S5-01 / S5-02).

The real cache once kept absolute paths from the workspace's old root
(``...\\Capcut\\02_Assets``) after the project moved.  Freshness compared only
mtimes, so the stale cache won; every font path was missing, metrics fell back
to scale 1.0 silently and captions rendered ~40% smaller with the hook dropped.

Everything here runs in the conftest's temporary data root -- the real
``02_Assets/asset_registry.json`` is never read or written.
"""

import json
import os
import time
from pathlib import Path

import pytest

from scripts import asset_registry as registry_module
from scripts.asset_registry import AssetRegistry
from scripts.subtitle import font_metrics
from scripts.subtitle.font_metrics import FontAssetMissingError

FOREIGN_ROOT = "Z:\\Elsewhere\\OldWorkspace\\02_Assets"


@pytest.fixture(autouse=True)
def _fresh_memo(monkeypatch):
    monkeypatch.setattr(AssetRegistry, "_freshness_cache", None)
    monkeypatch.setattr(AssetRegistry, "_freshness_checked_at", 0.0)
    monkeypatch.setattr(font_metrics, "_FAMILY_FONT_PATH_CACHE", {})
    monkeypatch.setattr(font_metrics, "_ASS_GLYPH_SCALE_CACHE", {})
    monkeypatch.setattr(font_metrics, "_ASS_VERTICAL_METRICS_CACHE", {})
    monkeypatch.setattr(font_metrics, "_HAS_TRUE_BOLD_CACHE", {})


def _write_foreign_cache() -> dict:
    """A cache that is newer than every asset but points at another root."""
    registry = AssetRegistry.rebuild()
    for category in ("sfx", "bgm", "fonts", "stickers", "luts", "effects"):
        for entry in registry[category]:
            entry["path"] = f"{FOREIGN_ROOT}\\{Path(entry['path']).parent.name}\\{entry['name']}"
    path = registry_module.REGISTRY_PATH
    path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    future = time.time() + 3600
    os.utime(path, (future, future))
    AssetRegistry._freshness_cache = None
    return registry


def test_fresh_rebuild_is_fresh():
    AssetRegistry.rebuild()
    assert AssetRegistry._compute_cache_is_fresh() is True


def test_cache_with_foreign_root_paths_is_stale_even_when_newer():
    _write_foreign_cache()
    assert AssetRegistry._compute_cache_is_fresh() is False


def test_cache_with_missing_font_file_under_fonts_dir_is_stale():
    registry = AssetRegistry.rebuild()
    registry["fonts"][0]["path"] = str(registry_module.FONTS_DIR / "DoesNotExist-Bold.ttf")
    path = registry_module.REGISTRY_PATH
    path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    future = time.time() + 3600
    os.utime(path, (future, future))
    assert AssetRegistry._compute_cache_is_fresh() is False


def test_load_rebuilds_foreign_cache_and_restores_real_font_scale():
    _write_foreign_cache()
    fonts = AssetRegistry.fonts()
    fonts_dir = os.path.normcase(os.path.abspath(registry_module.FONTS_DIR))
    assert fonts
    for entry in fonts:
        assert os.path.normcase(os.path.abspath(entry["path"])).startswith(fonts_dir)
        assert Path(entry["path"]).is_file()
    # Golden master: IBM Plex line box 1000 / (1116 + 534).
    assert font_metrics.ass_glyph_scale("IBM Plex Sans Thai") == pytest.approx(1000 / 1650)


def test_ass_glyph_scale_raises_when_registry_font_file_is_missing(monkeypatch):
    fake = [{"name": "Ghost-Bold.ttf", "family": "Ghost Sans", "path": FOREIGN_ROOT + "\\Fonts\\Ghost-Bold.ttf"}]
    monkeypatch.setattr(AssetRegistry, "fonts", classmethod(lambda cls: fake))
    with pytest.raises(FontAssetMissingError) as excinfo:
        font_metrics.ass_glyph_scale("Ghost Sans")
    assert "ไม่พบไฟล์ฟอนต์" in str(excinfo.value)
    assert "Ghost Sans" not in font_metrics._ASS_GLYPH_SCALE_CACHE


def test_ass_glyph_scale_raises_for_family_without_any_face():
    with pytest.raises(FontAssetMissingError):
        font_metrics.ass_glyph_scale("No Such Family 123")


def test_text_measurement_raises_instead_of_estimating(monkeypatch):
    fake = [{"name": "Ghost-Bold.ttf", "family": "Ghost Sans", "path": FOREIGN_ROOT + "\\Fonts\\Ghost-Bold.ttf"}]
    monkeypatch.setattr(AssetRegistry, "fonts", classmethod(lambda cls: fake))
    with pytest.raises(FontAssetMissingError):
        font_metrics._measure_text_width_px("ทดสอบ", "Ghost Sans", 60)
    with pytest.raises(FontAssetMissingError):
        font_metrics.prefix_advances(["ทด", "สอบ"], "Ghost Sans", 60)


def test_word_layout_raises_instead_of_estimating(monkeypatch):
    from scripts.subtitle import word_layout

    monkeypatch.setattr(AssetRegistry, "fonts", classmethod(lambda cls: []))
    with pytest.raises(FontAssetMissingError):
        word_layout.layout_line("ทดสอบ ข้อความ", "IBM Plex Sans Thai", 50)


def test_hook_line_fit_raises_instead_of_dropping_hook(monkeypatch):
    from scripts import hook_line

    monkeypatch.setattr(font_metrics, "_measure_text_width_px", lambda *a, **k: None)
    with pytest.raises(FontAssetMissingError):
        hook_line._fit_size_pct("ปวดข้อมือตอนพิมพ์งาน", {"font": "IBM Plex Sans Thai"}, 120)


def test_hook_line_fits_with_real_fonts_after_rebuild():
    from scripts import hook_line

    _write_foreign_cache()
    pct = hook_line._fit_size_pct("ปวดข้อมือตอนพิมพ์งาน", {"font": "IBM Plex Sans Thai"}, 120)
    assert pct is not None
