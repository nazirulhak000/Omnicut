"""The ghost reveal's active word follows the hook's accent colour."""
import json
from pathlib import Path

import pytest

from scripts.hook_styles import HOOK_TEMPLATES
from scripts.overlay_model import hook_overlay_from_legacy
from scripts.subtitle.badge_plate_renderer import ass_colour
from scripts.subtitle.ghost_reveal_ass import (
    ACTIVE_COLOUR,
    active_colour_for,
    build_ghost_reveal_events,
    build_multiline_reveal_events,
    build_reveal_line,
)
from scripts.subtitle.reveal_color import legible_reveal_hex, pick_reveal_hex


def _hook(template):
    return hook_overlay_from_legacy("BRAND", "Model X", "label", style={"template": template})


class TestPickRevealHex:
    @pytest.mark.parametrize("template,expected", [
        ("b1_viral_red", "#FE2C55"),
        ("b2_clean_yellow", "#FFE600"),
    ])
    def test_takes_the_brand_tier_accent_of_a_t1_template(self, template, expected):
        assert pick_reveal_hex([_hook(template)]) == expected

    def test_every_preset_template_resolves_to_a_hex(self):
        for key in HOOK_TEMPLATES:
            if key.startswith(("b1_", "b2_")):
                got = pick_reveal_hex([_hook(key)])
                assert got and got.startswith("#") and len(got) == 7, key

    def test_all_grey_hook_keeps_the_sop_green(self):
        overlay = _hook("plain")
        for tier in overlay["tiers"]:
            tier["look"]["color"] = "#D0D0D0"
        assert pick_reveal_hex([overlay]) is None

    def test_no_hook_overlay_keeps_the_sop_green(self):
        assert pick_reveal_hex([]) is None
        assert pick_reveal_hex(None) is None
        assert pick_reveal_hex([{"kind": "text", "tiers": []}]) is None

    def test_hidden_hook_is_ignored(self):
        overlay = _hook("b1_viral_red")
        overlay["hidden"] = True
        assert pick_reveal_hex([overlay]) is None

    def test_follows_a_hook_the_user_recoloured(self):
        overlay = _hook("b1_viral_red")
        overlay["tiers"][0]["look"]["color"] = "#00FF88"
        assert pick_reveal_hex([overlay]) == "#00FF88"

    def test_a_non_hex_tier_colour_is_skipped_not_crashed_on(self):
        overlay = _hook("b1_viral_red")
        overlay["tiers"][0]["look"]["color"] = None
        overlay["tiers"][1]["look"]["color"] = "red"
        assert pick_reveal_hex([overlay]) is None

    def test_a_very_dark_colour_is_lifted_toward_white(self):
        assert legible_reveal_hex("#1A0033") != "#1A0033"
        assert legible_reveal_hex("#FE2C55") == "#FE2C55"


class TestSharedParityFixture:
    """The same cases run through frontend/src/lib/revealColor.test.js."""

    @pytest.mark.parametrize("case", json.loads(
        (Path(__file__).parent / "fixtures" / "reveal_color_parity_cases.json").read_text(encoding="utf-8")
    )["cases"], ids=lambda c: c["name"])
    def test_case(self, case):
        assert pick_reveal_hex(case["overlays"]) == case["expected"]


class TestActiveColourOverride:
    def test_default_is_the_sop_green(self):
        assert active_colour_for(None) == ACTIVE_COLOUR

    def test_override_is_the_ass_spelling_of_the_hex(self):
        assert active_colour_for("#FE2C55") == f"{ass_colour('#FE2C55')}&"

    def test_reveal_line_uses_the_override_and_never_the_green(self):
        line = build_reveal_line(["ก", "ข", "ค"], 1, active_colour=active_colour_for("#FE2C55"))
        assert active_colour_for("#FE2C55") in line
        assert ACTIVE_COLOUR not in line

    def test_default_call_is_unchanged(self):
        assert build_reveal_line(["ก", "ข"], 0) == build_reveal_line(["ก", "ข"], 0, None, None)

    def test_single_and_multiline_builders_carry_it(self):
        colour = active_colour_for("#3B82F6")
        reveal = [{"text": "ก", "start": 0.0, "end": 0.5}, {"text": "ข", "start": 0.5, "end": 1.0}]
        for ev in build_ghost_reveal_events(reveal, 1.0, active_colour=colour):
            assert ACTIVE_COLOUR not in ev
        assert any(colour in ev for ev in build_ghost_reveal_events(reveal, 1.0, active_colour=colour))
        multi = build_multiline_reveal_events([reveal[:1], reveal[1:]], 1.0, ["{\\pos(0,0)}", "{\\pos(0,50)}"],
                                              active_colour=colour)
        assert any(colour in ev for ev in multi)
        assert not any(ACTIVE_COLOUR in ev for ev in multi)


class TestEngineEndToEnd:
    CUE = [{"id": 1, "start": 0.0, "end": 2.0, "text": "เครื่องนี้ช่วยลดอุณหภูมิ", "translation": ""}]

    def _ass(self, tmp_path, name, **kw):
        from scripts.subtitle_engine import SubtitleEngine

        out = tmp_path / name
        SubtitleEngine.generate_ass(self.CUE, str(out), font_name="IBMPlex", bilingual=False, **kw)
        return out.read_text(encoding="utf-8")

    def test_reveal_colour_replaces_the_green_in_the_file(self, tmp_path):
        text = self._ass(tmp_path, "a.ass", ghost_reveal=True, reveal_color="#FE2C55")
        assert active_colour_for("#FE2C55") in text
        assert ACTIVE_COLOUR not in text

    def test_omitting_it_still_renders_the_green(self, tmp_path):
        assert ACTIVE_COLOUR in self._ass(tmp_path, "b.ass", ghost_reveal=True)

    def test_sentence_mode_ignores_the_reveal_colour(self, tmp_path):
        text = self._ass(tmp_path, "c.ass", ghost_reveal=False, reveal_color="#FE2C55")
        assert active_colour_for("#FE2C55") not in text
        assert ACTIVE_COLOUR not in text

    def test_thai_tone_companions_follow_the_same_colour(self, tmp_path):
        """ที่ / นั่ง detach a tone into a companion event; it must not stay green."""
        from scripts.subtitle_engine import SubtitleEngine

        out = tmp_path / "d.ass"
        SubtitleEngine.generate_ass(
            [{"id": 1, "start": 0.0, "end": 2.0, "text": "นั่งสบายที่บ้าน", "translation": ""}],
            str(out), font_name="IBMPlex", bilingual=False, ghost_reveal=True, reveal_color="#FE2C55",
        )
        text = out.read_text(encoding="utf-8")
        assert ACTIVE_COLOUR not in text, "a detached tone stayed SOP green"
        assert active_colour_for("#FE2C55") in text


BS = chr(92)


def _tag(colour):
    """The ASS override that paints a run `colour`."""
    return BS + "c" + colour


class TestHighlightsFollowTheHook:
    """With the hook colour on, the keyword highlights of BOTH lines take it."""

    CUE = [{"id": 1, "start": 0.0, "end": 2.4, "text": "พัดลมระบายความร้อน",
            "translation": "Cooling fan keeps it cool"}]
    CYAN, YELLOW, RED = "&H00FFE600&", "&H0000E6FF&", "&H00303BFF&"

    def _ass(self, tmp_path, **kw):
        from scripts.subtitle_engine import SubtitleEngine

        # The hook's brand / model words become the project's custom keywords,
        # which is where the cyan "Cooling" in a real clip comes from.
        hook = hook_overlay_from_legacy("HOYAUP", "Cooling Fan", "", style={"template": "b1_viral_red"})
        out = tmp_path / "h.ass"
        SubtitleEngine.generate_ass(self.CUE, str(out), font_name="IBMPlex", bilingual=True,
                                    overlays=[hook], hook_brand="HOYAUP", hook_model="Cooling Fan", **kw)
        return out.read_text(encoding="utf-8")

    def _category_tags(self, text):
        return [c for c in (self.CYAN, self.YELLOW, self.RED) if "{" + _tag(c) + "}" in text]

    def test_premise_the_english_keyword_is_highlighted_by_default(self, tmp_path):
        assert self._category_tags(self._ass(tmp_path, ghost_reveal=True))

    def test_english_keywords_no_longer_keep_a_category_colour(self, tmp_path):
        text = self._ass(tmp_path, ghost_reveal=True, reveal_color="#FF2E93")
        assert active_colour_for("#FF2E93") in text
        assert self._category_tags(text) == [], "a category highlight survived the hook sync"

    def test_sentence_mode_keeps_category_colours_even_with_a_hook_colour(self, tmp_path):
        text = self._ass(tmp_path, ghost_reveal=False, reveal_color="#FF2E93")
        assert active_colour_for("#FF2E93") not in text
        assert self._category_tags(text)

    def test_recolour_leaves_the_base_colour_alone(self):
        from scripts.subtitle.reveal_color import recolour_highlights

        def run(*parts):
            return "".join("{" + _tag(c) + "}" + t for c, t in parts)

        src = run(("&H0000E6FF&", "ab"), ("&H00FFE600&", "cd"), ("&H00EAEAEA&", "ef"))
        out = recolour_highlights(src, "&H00AABBCC&")
        assert out == run(("&H00AABBCC&", "ab"), ("&H00AABBCC&", "cd"), ("&H00EAEAEA&", "ef"))
        # a yellow caption's own reset tag is yellow and must not be tinted
        kept = recolour_highlights(src, "&H00AABBCC&", keep="&H0000E6FF&")
        assert kept.startswith("{" + _tag("&H0000E6FF&") + "}ab")
