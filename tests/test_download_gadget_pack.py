# -*- coding: utf-8 -*-
"""S1-10/S1-11: download_gadget_pack runs argv lists without a shell and
derives rule-12 / 1080p flags from media_intake_audit instead of hardcoding."""

from __future__ import annotations

import json

import pytest

from tools import download_gadget_pack as pack


def _setup(monkeypatch, tmp_path, signals, width=1920, height=1080):
    calls = []

    def fake_run(cmd, timeout=300):
        assert isinstance(cmd, list), "commands must be argv lists (no shell)"
        calls.append(cmd)
        if cmd[0] == "yt-dlp":
            out = cmd[cmd.index("-o") + 1]
            open(out, "wb").write(b"video")
        return True, "10.0", ""

    monkeypatch.setattr(pack, "OUTPUT_BASE", tmp_path)
    monkeypatch.setattr(pack, "run_cmd", fake_run)
    monkeypatch.setattr(pack, "audit_media", lambda path: {
        "status": "review_required", "media": {"width": width, "height": height},
        "signals": [{"code": c, "severity": "review"} for c in signals]})
    return calls


def _info(tmp_path):
    return json.loads(next(tmp_path.rglob("info.json")).read_text(encoding="utf-8"))


def test_url_with_quotes_is_passed_as_one_argument(monkeypatch, tmp_path):
    calls = _setup(monkeypatch, tmp_path, ["no_text_in_samples"])
    url = 'https://example.com/v?a=1&b="x"'
    assert pack.build_product_pack("p1", url, "Brand", "topic") is True
    assert url in calls[0]
    info = _info(tmp_path)
    assert info["status"] == "ready_for_editing"
    assert info["visual_review_required"] is True


@pytest.mark.parametrize("signals, size, status", [
    (["possible_foreign_subtitle"], (1920, 1080), "rejected_foreign_subtitles"),
    (["no_text_in_samples"], (640, 360), "rejected_low_resolution"),
])
def test_rule12_and_resolution_are_checked(monkeypatch, tmp_path, signals, size, status):
    _setup(monkeypatch, tmp_path, signals, *size)
    assert pack.build_product_pack("p2", "https://example.com/v", "Brand", "topic") is False
    info = _info(tmp_path)
    assert info["status"] == status
    assert info["no_foreign_subtitles"] is not True or status == "rejected_low_resolution"


def test_no_shell_true_left():
    src = open(pack.__file__, encoding="utf-8").read()
    assert "shell=True" not in src


def test_no_fake_channel_badge_in_gadget_tools():
    """S5-13 / rule 17: no hardcoded "TECH MX" badge in the sample/ASS tools."""
    from pathlib import Path
    root = Path(pack.__file__).resolve().parent
    for name in ("render_sample_gadget_clip.py", "generate_precision_ass.py"):
        text = (root / name).read_text(encoding="utf-8").lower()
        assert "tech mx" not in text and "techmx" not in text, name
