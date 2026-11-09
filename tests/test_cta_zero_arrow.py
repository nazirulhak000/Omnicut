# -*- coding: utf-8 -*-
"""AGENTS rule 23 (audit S6-06): the canonical Couple Paper Chat engines and
the couple_engine composer never draw a CTA arrow (no #cta-arrow SVG, no
#cta-shaft/#cta-head GSAP tweens)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINES = sorted((ROOT / "tools").glob("batch_produce_*.py")) + [
    ROOT / "scripts" / "couple_engine" / "compose.py",
]
ARROW = re.compile(r"cta-(?:arrow|shaft|head)\b")


@pytest.mark.parametrize("path", ENGINES, ids=lambda p: p.name)
def test_engine_template_has_no_cta_arrow(path):
    text = path.read_text(encoding="utf-8")
    hits = [f"{path.name}:{n}" for n, line in enumerate(text.splitlines(), 1) if ARROW.search(line)]
    assert hits == [], f"CTA arrow markup/tween found (rule 23 Zero-Arrow): {hits}"
