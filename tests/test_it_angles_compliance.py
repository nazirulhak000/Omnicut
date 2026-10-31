"""
Every text field of the IT angle catalog goes into an LLM prompt (or straight
onto the screen as a fallback hook), so none of it may steer toward price talk
or exaggerated claims. Pure/offline.
"""

import pytest

import scripts.compliance_lint as cl
from scripts.it_angles import IT_ANGLE_CATALOG, catalog_for_prompt, fallback_angles

TEXT_FIELDS = ("name", "description", "proof_needed", "fallback_hook")


def _angle_ids():
    return [a["key"] for a in IT_ANGLE_CATALOG]


@pytest.mark.parametrize("angle", IT_ANGLE_CATALOG, ids=_angle_ids())
def test_every_angle_text_field_passes_compliance_lint(angle):
    for field in TEXT_FIELDS:
        assert cl.lint_text(angle[field], field=field) == [], (angle["key"], field, angle[field])
        assert not cl.ELLIPSIS_RE.search(angle[field]), (angle["key"], field)
    for i, pattern in enumerate(angle["hook_patterns"]):
        assert cl.lint_text(pattern, field="hook_patterns", index=i) == [], (angle["key"], pattern)
        # A hook pattern becomes the first spoken line of the clip.
        assert cl.lint_opening_line(pattern) == [], (angle["key"], pattern)
        assert not cl.ELLIPSIS_RE.search(pattern), (angle["key"], pattern)
    assert cl.lint_opening_line(angle["fallback_hook"]) == [], angle["key"]


def test_spec_compare_is_a_spec_comparison_not_a_price_comparison():
    angle = next(a for a in IT_ANGLE_CATALOG if a["key"] == "spec_compare")
    assert "สเปก" in angle["name"]
    assert "ราคา" not in angle["name"]


def test_angle_keys_are_unchanged():
    assert _angle_ids() == [
        "spec_compare", "fake_vs_real", "real_test", "spec_explained",
        "pain_point", "dont_cheap_out", "how_to_setup", "worth_upgrade",
    ]


def test_prompt_catalog_and_fallbacks_carry_no_price_terms():
    for entry in catalog_for_prompt() + catalog_for_prompt(seller_assets_only=True):
        for text in [entry["name"], entry["description"], *entry["hook_patterns"]]:
            assert cl.find_price_term(text) is None, text
    for angle in fallback_angles("หูฟัง Bluetooth"):
        assert cl.lint_text(angle["hook"]) == []
        assert cl.lint_text(angle["title"]) == []
        assert cl.lint_text(angle["why_it_works"]) == []
