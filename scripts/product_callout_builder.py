"""Build deterministic product callout overlays without touching the pipeline.

Product callouts are semantic text overlays, not subtitles and not a renderer
concern.  This module deliberately returns the repository's existing overlay
shape (``kind="text"``) with product-specific metadata attached so a later
pipeline seam can consume it without inventing another drawing model.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.color_theme import normalize_hex
from scripts.compliance_lint import format_violations_th, lint_text
from scripts.overlay_model import new_text_overlay


# No "price" type: clips must never show a price/discount (TikTok rule). A
# legacy "price" callout (auto metadata or a manual overlay) normalizes to
# None and is dropped, and any other callout whose text trips the compliance
# lint is dropped with a Thai log line (see _passes_compliance).
CALLOUT_TYPES = ("brand", "model", "feature", "spec", "proof", "cta")
_CALLOUT_TYPE_SET = set(CALLOUT_TYPES)
_TYPE_PRIORITY = {name: index for index, name in enumerate(CALLOUT_TYPES)}
CALLOUT_THEME_ROLES = {
    "brand": "primary",
    "model": "secondary",
    "feature": "primary",
    "spec": "secondary",
    "proof": "secondary",
    "cta": "primary",
}
_TEXT_FIELDS = ("text", "value", "label", "content")
_EMPTY_TEXT_RE = re.compile(r"\s+")


def build_product_callouts(
    beat_cues: Optional[Sequence[Mapping[str, Any]]] = None,
    product_metadata: Optional[Mapping[str, Any]] = None,
    manual_overlays: Optional[Sequence[Mapping[str, Any]]] = None,
    color_theme: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Return auto product callouts merged with manual callouts.

    ``beat_cues`` are the source of truth for automatic timing.  A product
    value may select a cue with ``beat_id``/``beat_index``; values without a
    selector use the first valid cue.  The metadata supports the common
    product fields (brand, model, features, specs, proof and cta) and an
    optional explicit ``callouts`` list. A ``price`` field is ignored and any
    callout text that trips ``scripts.compliance_lint`` (price/claim) is
    dropped with a Thai log line -- never rendered.

    Dedupe is semantic: normalized ``(callout_type, text)`` is one identity.
    A manual overlay with that identity replaces the generated overlay.  The
    function never mutates any input and intentionally does no text escaping;
    escaping belongs to the ASS/render boundary.
    """
    cues = _valid_cues(beat_cues or [])
    metadata = product_metadata if isinstance(product_metadata, Mapping) else {}

    generated: List[Dict[str, Any]] = []
    candidates = list(_metadata_candidates(metadata))
    candidates.extend(_cue_candidates(cues))
    for candidate in candidates:
        overlay = _candidate_to_overlay(candidate, cues, origin="auto", color_theme=color_theme)
        if overlay is not None:
            generated.append(overlay)

    manual = [_normalize_manual_overlay(item) for item in (manual_overlays or [])]
    manual = [item for item in manual if item is not None]
    return _merge_deduplicated(generated, manual)


def build_callouts(
    beat_cues: Optional[Sequence[Mapping[str, Any]]] = None,
    product_metadata: Optional[Mapping[str, Any]] = None,
    manual_overlays: Optional[Sequence[Mapping[str, Any]]] = None,
    color_theme: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Backward-friendly short alias for :func:`build_product_callouts`."""
    return build_product_callouts(beat_cues, product_metadata, manual_overlays, color_theme)


def _valid_cues(cues: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    valid: List[Dict[str, Any]] = []
    for index, cue in enumerate(cues):
        if not isinstance(cue, Mapping):
            continue
        start = _finite_number(cue.get("start"))
        end = _finite_number(cue.get("end"))
        if start is None or end is None or end <= start:
            continue
        copied = copy.deepcopy(dict(cue))
        copied["_index"] = index
        copied["_start"] = round(start, 3)
        copied["_end"] = round(end, 3)
        valid.append(copied)
    return valid


def _metadata_candidates(metadata: Mapping[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield candidates in stable semantic order, without changing metadata."""
    for field, callout_type in (("brand", "brand"), ("model", "model")):
        value = metadata.get(field)
        if value not in (None, ""):
            yield _candidate(value, callout_type, field)

    for field, callout_type in (
        ("features", "feature"),
        ("specs", "spec"),
        ("proof", "proof"),
        ("cta", "cta"),
    ):
        value = metadata.get(field)
        if value in (None, "", []):
            continue
        values = value if field in ("features", "specs") and _is_list_like(value) else [value]
        for item in values:
            yield _candidate(item, callout_type, field)

    explicit = metadata.get("callouts")
    if _is_list_like(explicit):
        for item in explicit:
            if isinstance(item, Mapping):
                yield _candidate(item, item.get("callout_type") or item.get("type"), "callouts")

    # ``on_screen`` is the existing script-side source for a visual spec.  It
    # is converted here only; the pipeline remains untouched in this phase.
    cue_candidates = metadata.get("beat_cues")
    if _is_list_like(cue_candidates):
        for cue in cue_candidates:
            if isinstance(cue, Mapping) and str(cue.get("on_screen") or "").strip():
                value = str(cue["on_screen"]).strip()
                kind = "spec" if _looks_like_spec(value) else "feature"
                yield {
                    "text": value,
                    "callout_type": kind,
                    "source_field": "beat_cues.on_screen",
                    "beat_id": cue.get("id"),
                    "beat_index": cue.get("index"),
                    "start": cue.get("start"),
                    "end": cue.get("end"),
                }


def _cue_candidates(cues: Sequence[Mapping[str, Any]]) -> Iterable[Dict[str, Any]]:
    """Convert non-empty cue ``on_screen`` values into auto callouts."""
    for cue in cues:
        value = str(cue.get("on_screen") or "").strip()
        if not value:
            continue
        yield {
            "text": value,
            "callout_type": "spec" if _looks_like_spec(value) else "feature",
            "source_field": "beat_cues.on_screen",
            "beat_id": cue.get("id"),
            "beat_index": cue.get("_index"),
            "start": cue.get("start"),
            "end": cue.get("end"),
        }


def _candidate(value: Any, callout_type: Any, source_field: str) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        candidate = copy.deepcopy(dict(value))
        candidate.setdefault("callout_type", callout_type)
        candidate.setdefault("source_field", source_field)
        return candidate
    return {"text": str(value), "callout_type": callout_type, "source_field": source_field}


def _candidate_to_overlay(
    candidate: Mapping[str, Any],
    cues: Sequence[Mapping[str, Any]],
    *,
    origin: str,
    color_theme: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    text = _candidate_text(candidate)
    callout_type = _normalize_callout_type(candidate.get("callout_type") or candidate.get("type"))
    if not text or callout_type is None:
        return None
    if not _passes_compliance(text, callout_type, origin):
        return None

    timing = _candidate_timing(candidate, cues)
    if timing is None:
        return None
    start, end, beat = timing
    source = _source_for(candidate, beat)
    identity = _identity(callout_type, text)
    overlay = new_text_overlay(
        overlay_id=f"callout-{callout_type}-{_digest(identity)}",
        text=text,
        start=start,
        end=end,
        look=_generated_look(callout_type, color_theme),
        template_id="product_callout",
    )
    overlay.update(
        {
            "role": "product_callout",
            "callout_type": callout_type,
            "theme_role": CALLOUT_THEME_ROLES.get(callout_type, "primary"),
            "origin": origin,
            "source": source,
        }
    )
    return overlay


def _generated_look(
    callout_type: str,
    color_theme: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Return only the auto colour overrides; manual looks stay untouched."""

    if not isinstance(color_theme, Mapping):
        return {}
    role = CALLOUT_THEME_ROLES.get(callout_type, "primary")
    color = normalize_hex(color_theme.get(role))
    if color is None:
        color = normalize_hex(color_theme.get("neutral")) or "#FFFFFF"
    outline = normalize_hex(color_theme.get("ink")) or "#000000"
    secondary = normalize_hex(color_theme.get("secondary")) or color
    return {
        "color": color,
        "outline_color": outline,
        "accent_color": secondary,
    }


def _normalize_manual_overlay(item: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(item, Mapping):
        return None
    if item.get("role") != "product_callout" and not (
        item.get("origin") == "manual" and item.get("callout_type")
    ):
        return None
    text = _candidate_text(item)
    callout_type = _normalize_callout_type(item.get("callout_type") or item.get("type"))
    if not text or callout_type is None:
        return None
    if not _passes_compliance(text, callout_type, "manual"):
        return None
    copied = copy.deepcopy(dict(item))
    copied["kind"] = "text"
    copied["role"] = "product_callout"
    copied["callout_type"] = callout_type
    copied["origin"] = "manual"
    copied.setdefault("source", {"kind": "manual"})
    copied.setdefault("tiers", [{"text": text, "look": {}}])
    if not copied.get("id"):
        copied["id"] = f"callout-{callout_type}-{_digest(_identity(callout_type, text))}"
    return copied


def _merge_deduplicated(
    generated: Sequence[Mapping[str, Any]],
    manual: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Dedupe by semantic identity; manual entries always replace auto ones."""
    by_identity: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in generated:
        key = _overlay_identity(item)
        if key not in by_identity:
            by_identity[key] = copy.deepcopy(dict(item))
    for item in manual:
        manual_id = item.get("id")
        if manual_id:
            for key, existing in list(by_identity.items()):
                if existing.get("id") == manual_id:
                    del by_identity[key]
        key = _overlay_identity(item)
        by_identity[key] = copy.deepcopy(dict(item))

    return sorted(
        by_identity.values(),
        key=lambda item: (
            _finite_number(item.get("start")) or 0.0,
            _finite_number(item.get("end")) or 0.0,
            _TYPE_PRIORITY.get(item.get("callout_type"), len(_TYPE_PRIORITY)),
            _candidate_text(item).casefold(),
            str(item.get("id") or ""),
        ),
    )


def _overlay_identity(item: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        _normalize_callout_type(item.get("callout_type")) or "feature",
        _normalize_text(_candidate_text(item)),
    )


def _identity(callout_type: str, text: str) -> Tuple[str, str]:
    return callout_type, _normalize_text(text)


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _candidate_text(candidate: Mapping[str, Any]) -> str:
    tiers = candidate.get("tiers")
    if isinstance(tiers, Sequence) and not isinstance(tiers, (str, bytes)) and tiers:
        first = tiers[0]
        if isinstance(first, Mapping) and first.get("text") is not None:
            return str(first["text"]).strip()
    for field in _TEXT_FIELDS:
        value = candidate.get(field)
        if value is not None:
            return str(value).strip()
    return ""


def _normalize_text(text: str) -> str:
    return _EMPTY_TEXT_RE.sub(" ", text).strip().casefold()


def _normalize_callout_type(value: Any) -> Optional[str]:
    normalized = str(value or "").strip().casefold()
    return normalized if normalized in _CALLOUT_TYPE_SET else None


def _candidate_timing(
    candidate: Mapping[str, Any], cues: Sequence[Mapping[str, Any]]
) -> Optional[Tuple[float, float, Optional[Mapping[str, Any]]]]:
    explicit_start = _finite_number(candidate.get("start"))
    explicit_end = _finite_number(candidate.get("end"))
    if explicit_start is not None and explicit_end is not None and explicit_end > explicit_start:
        beat = next(
            (cue for cue in cues if candidate.get("beat_id") is not None and cue.get("id") == candidate["beat_id"]),
            None,
        )
        return round(explicit_start, 3), round(explicit_end, 3), beat
    if not cues:
        return None

    selected = None
    if candidate.get("beat_id") is not None:
        selected = next((cue for cue in cues if cue.get("id") == candidate["beat_id"]), None)
    if selected is None and candidate.get("beat_index") is not None:
        try:
            selected = next(
                (cue for cue in cues if cue.get("_index") == int(candidate["beat_index"])),
                None,
            )
        except (TypeError, ValueError):
            selected = None
    if selected is None:
        selected = cues[0]
    return selected["_start"], selected["_end"], selected


def _source_for(candidate: Mapping[str, Any], beat: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    source = copy.deepcopy(candidate.get("source")) if isinstance(candidate.get("source"), Mapping) else {}
    source.setdefault("field", candidate.get("source_field") or "product_metadata")
    if beat is not None:
        source.setdefault("beat_id", beat.get("id"))
        source.setdefault("beat_index", beat.get("_index"))
    return source


def _passes_compliance(text: str, callout_type: str, origin: str) -> bool:
    """False (and a Thai log line) when a callout would show price/claim text."""
    hits = lint_text(text, field=f"callout:{callout_type}")
    if not hits:
        return True
    print(
        f"⚠️ [ProductCallout] ตัด callout ({origin}/{callout_type}) '{text[:40]}' "
        f"ออก เพราะผิดกฎ compliance:\n{format_violations_th(hits)}"
    )
    return False


def _looks_like_spec(text: str) -> bool:
    return bool(re.search(r"\d|%|mah|w\b|v\b|hz\b|ip\d", text, re.IGNORECASE))


def _finite_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _is_list_like(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


__all__ = ["CALLOUT_THEME_ROLES", "CALLOUT_TYPES", "build_callouts", "build_product_callouts"]
