import json
from pathlib import Path

import pytest

from scripts.content_guard import content_reason, normalize_text

CASES = json.loads((Path(__file__).parent / "fixtures" / "content_guard_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['reason'] or 'ok'}:{c['caption'][:18]!r}")
def test_content_reason_matches_shared_cases(case):
    assert content_reason(case["caption"], case["hashtags"]) == case["reason"]


def test_allow_price_flag_only_lifts_price_rule():
    assert content_reason("ราคา 199 บาท", "", allow_price=True) == ""
    assert content_reason("{name} ราคา 199", "", allow_price=True) == "placeholder_in_caption"


def test_normalize_text_strips_invisible_and_maps_digits():
    assert normalize_text("ร​าคา ๑๒") == "ราคา 12"


def test_python_twin_uses_the_same_limits_as_limits_js():
    import re
    from scripts import content_guard
    source = (Path(__file__).parent.parent / "tiktok_autopost_extension" / "limits.js").read_text(encoding="utf-8")
    assert int(re.search(r"MAX_TEXT_CHARS:\s*(\d+)", source).group(1)) == content_guard.MAX_TEXT_CHARS
    assert int(re.search(r"MAX_HASHTAGS:\s*(\d+)", source).group(1)) == content_guard.MAX_HASHTAGS
