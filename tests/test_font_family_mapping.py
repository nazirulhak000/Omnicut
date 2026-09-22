"""
Regression tests for font_name -> font family resolution
(scripts/subtitle/font_metrics.py's _load_font_family_map).

Two bugs found while diagnosing "วรรณยุกต์ไทยชั้นสองยุบใน libass"
(TODO.md's tone-mark collapse entry, e.g. "เพิ่ง" rendering as "เพีง"):

1. Kanit/Prompt/Mitr/Itim have no GPOS mark-anchor for stacked Thai tone
   marks -- confirmed via a libass-vs-PIL differential render (both collapse
   the mark identically, so it's the font file, not libass). Fixed by
   removing Kanit/Prompt from the UI's font picker (NewClipPanel.jsx) --
   nothing to assert here at the Python layer since the font files
   themselves aren't changing, only which ones the UI offers.

2. The UI's "Noto Sans Thai" option sends font_name="NotoSansThai", which
   never matched any preset id/font_name/family key in the map -- it
   silently fell through to DEFAULT_FONT_FAMILY (IBM Plex Sans Thai), so
   picking Noto in the UI rendered in IBM Plex instead, with no error or
   indication. This is the bug these tests guard against.
"""
from scripts.subtitle.font_metrics import (
    DEFAULT_FONT_FAMILY,
    _load_font_family_map,
    ass_top_anchor_offset,
)


def test_notosansthai_ui_id_resolves_to_noto_family():
    font_map = _load_font_family_map()
    assert font_map.get("NotoSansThai", DEFAULT_FONT_FAMILY) == "Noto Sans Thai"


def test_ibmplex_ui_id_still_resolves_correctly():
    font_map = _load_font_family_map()
    assert font_map.get("IBMPlex", DEFAULT_FONT_FAMILY) == "IBM Plex Sans Thai"


def test_unknown_font_id_falls_back_to_default_not_silently_wrong():
    font_map = _load_font_family_map()
    assert font_map.get("something_never_registered", DEFAULT_FONT_FAMILY) == DEFAULT_FONT_FAMILY


def test_ass_top_anchor_offset_compensates_the_boosted_ibm_line_box():
    # 70 render px is the 1080-wide hook em. IBM Plex's 1650-unit Windows
    # line box needs about 31 px of added ascent when its 1000-unit em is
    # restored; keep this deterministic without optional fontTools.
    assert ass_top_anchor_offset("IBM Plex Sans Thai", 70) == 31
