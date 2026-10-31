"""Viral Lint (roadmap M4): retention + compliance checks on a project manifest.

Pure and deterministic -- no I/O, no AI, no clock. ``lint_manifest()`` reads a
manifest dict (the stored ``project.json`` or the editor's save payload merged
over it) and returns a list of :class:`Issue`, each with a severity and the
timeline span it is about, so the editor can list it before render and paint
it on the Timeline ruler.

Severities:
- ``block``  -- the render must not start (compliance hard rules only:
  price / discount / price guess and exaggerated claims).
- ``warn``   -- shown, never blocks (retention problems).
- ``info``   -- context only (e.g. a clip that is allowed to hold a frame).

Rules and thresholds (style values come from ``StyleMotionPolicy`` of the
manifest's ``style_preset``, read-only):

=============  ========  ===================================================
code           severity  fires when
=============  ========  ===================================================
HOOK_SLOW      warn      first on-screen text (captions, overlays) later than
                         0.5 s, or first spoken word later than 0.3 s
LONG_SHOT      warn      clip longer than ``max_shot`` x 1.25 and no
                         ``hold_reason``
HOLD           info      clip carries ``hold_reason`` (allowed hold)
HOOK_PACING    warn      clip starting inside ``hook_window_sec`` is longer
                         than ``hook_max_shot`` (hold clips exempt)
STATIC_SPAN    warn      a span inside one clip longer than ``max_static_sec``
                         with no cut, transition or moving camera keyframe
DEAD_AIR       warn      gap between voice cues longer than 0.4 s
SFX_DENSE      warn      two SFX that will be heard (after
                         ``sfx_manager.plan_sfx_events``) closer than 2.0 s
LENGTH         warn      timeline longer than ``target_duration`` x 1.15
STRUCTURE      warn      ``compliance_lint.check_script_structure`` warning
                         (open loop / payoff / comment question)
COMPLIANCE     block     price or exaggerated claim in a cue, script line,
                         on-screen text, hook field or overlay text
COMPLIANCE     warn      filler opener / CTA in the first spoken line
=============  ========  ===================================================

Score (0-100): ``100 - 30*block - 6*warn - 1*info`` where each rule code
(per severity) contributes at most ``SCORE_MAX_PER_CODE`` (3) issues, clamped to [0, 100].
Ten long shots therefore cost the same as three: the score tracks how many
kinds of problem a clip has, not how long the list is.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts import compliance_lint
from scripts.style_motion_policy import (
    StyleMotionPolicy,
    resolve_style_motion_policy,
    style_motion_policy_from_dict,
)

try:  # Reuse the mix planner so the lint judges the SFX that are really heard.
    from scripts.sfx_manager import SFX_MIN_GAP_S as _SFX_MIN_GAP_S
    from scripts.sfx_manager import plan_sfx_events as _plan_sfx_events
except Exception:  # pragma: no cover - optional dependency chain
    _SFX_MIN_GAP_S = 2.0
    _plan_sfx_events = None

SEVERITY_BLOCK = "block"
SEVERITY_WARN = "warn"
SEVERITY_INFO = "info"
SEVERITIES = (SEVERITY_BLOCK, SEVERITY_WARN, SEVERITY_INFO)

HOOK_TEXT_MAX_SEC = 0.5
HOOK_VOICE_MAX_SEC = 0.3
LONG_SHOT_FACTOR = 1.25
DEAD_AIR_SEC = 0.4
SFX_MIN_GAP_SEC = float(_SFX_MIN_GAP_S)
LENGTH_TOLERANCE = 0.15
# One frame at 30 fps: layout here is not frame-rounded, so a clip planned at
# exactly the cap must not trip the rule on a rounding hair.
TIME_TOLERANCE = 1 / 30
DEFAULT_TRANSITION_SEC = 0.4   # == timelineMath.js FADE_DURATION
MAX_TRANSITION_SEC = 2.0       # == timelineMath.js MAX_TRANSITION_DURATION
MAX_FREEZE_TAIL_SEC = 10.0
MIN_CLIP_SEC = 0.2

SCORE_PENALTY = {SEVERITY_BLOCK: 30, SEVERITY_WARN: 6, SEVERITY_INFO: 1}
SCORE_MAX_PER_CODE = 3

HOLD_REASON_TH = {
    "source_window_exhausted": "ภาพตรงบทหมดและไม่มีฟุตเทจอื่นให้ใช้",
}

_OVERLAY_TEXT_KEYS = ("text", "title", "subtitle", "label", "value", "headline", "caption", "spec", "line")
_OVERLAY_NEST_KEYS = ("tiers", "items", "lines", "specs", "rows")
_HOOK_FIELDS = ("hook", "hook_title", "hook_brand", "hook_model", "hook_label")


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    start: Optional[float]
    end: Optional[float]
    message_th: str
    clip_index: Optional[int] = None
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# small readers
# ---------------------------------------------------------------------------
def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _r(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value, 3)


def _fmt(seconds: float) -> str:
    return f"{seconds:.2f}"


def _records(value: Any) -> List[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _resolve_policy(manifest: Mapping[str, Any], policy: Any) -> StyleMotionPolicy:
    if isinstance(policy, StyleMotionPolicy):
        return policy
    if isinstance(policy, Mapping):
        return style_motion_policy_from_dict(policy)
    params = manifest.get("render_params") if isinstance(manifest.get("render_params"), Mapping) else {}
    return resolve_style_motion_policy(manifest.get("style_preset") or params.get("style_preset"))


def _target_duration(manifest: Mapping[str, Any]) -> Optional[float]:
    params = manifest.get("render_params") if isinstance(manifest.get("render_params"), Mapping) else {}
    for raw in (manifest.get("target_duration"), params.get("target_duration")):
        value = _num(raw)
        if value is not None and value > 0:
            return value
    return None


# ---------------------------------------------------------------------------
# timeline layout (same bookkeeping as timelineMath.planSequenceFrames, without
# the frame grid)
# ---------------------------------------------------------------------------
def _played_duration(clip: Mapping[str, Any]) -> float:
    trim_start = _num(clip.get("trim_start")) or 0.0
    trim_end = _num(clip.get("trim_end"))
    speed = _num(clip.get("speed")) or 1.0
    speed = speed if speed > 0 else 1.0
    freeze = min(MAX_FREEZE_TAIL_SEC, max(0.0, _num(clip.get("freeze_tail")) or 0.0))
    if trim_end is not None and trim_end > trim_start:
        return max(MIN_CLIP_SEC, (trim_end - trim_start) / speed + freeze)
    duration = _num(clip.get("duration"))
    if duration is not None and duration > 0:
        return max(MIN_CLIP_SEC, duration)
    return MIN_CLIP_SEC


def _boundary(manifest: Mapping[str, Any], clips: Sequence[Mapping[str, Any]], index: int) -> Tuple[str, float]:
    """(type, duration) of the edge in front of clip ``index`` (> 0)."""
    transitions = manifest.get("transitions") if isinstance(manifest.get("transitions"), list) else None
    kind, duration = "cut", None
    if transitions is not None and index - 1 < len(transitions) and isinstance(transitions[index - 1], Mapping):
        edge = transitions[index - 1]
        kind = str(edge.get("type") or "cut")
        duration = _num(edge.get("duration"))
    else:
        clip = clips[index]
        kind = str(clip.get("transition_in") or "cut")
        duration = _num(clip.get("transition_duration"))
    if kind == "cut":
        return "cut", 0.0
    raw = DEFAULT_TRANSITION_SEC if duration is None else duration
    return kind, min(MAX_TRANSITION_SEC, max(0.1, raw))


def layout_clips(manifest: Mapping[str, Any]) -> List[Dict[str, Any]]:
    clips = _records(manifest.get("clip_list") or manifest.get("clips"))
    segments: List[Dict[str, Any]] = []
    acc = 0.0
    for index, clip in enumerate(clips):
        dur = _played_duration(clip)
        overlap = 0.0
        if index > 0:
            kind, fade = _boundary(manifest, clips, index)
            if kind != "cut":
                overlap = min(fade, max(0.05, min(acc, dur) - 0.05))
        start = max(0.0, acc - overlap) if index > 0 else 0.0
        end = start + dur
        acc = end
        segments.append({"index": index, "clip": clip, "start": start, "end": end, "dur": dur, "overlap": overlap})
    return segments


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------
def _overlay_strings(node: Any, depth: int = 0) -> Iterable[str]:
    if depth > 3:
        return
    if isinstance(node, str):
        if node.strip():
            yield node
        return
    if isinstance(node, list):
        for item in node:
            yield from _overlay_strings(item, depth + 1)
        return
    if not isinstance(node, Mapping):
        return
    for key in _OVERLAY_TEXT_KEYS:
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            yield value
    for key in _OVERLAY_NEST_KEYS:
        if key in node:
            yield from _overlay_strings(node.get(key), depth + 1)


def _overlay_records(manifest: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return _records(manifest.get("overlays")) + _records(manifest.get("text_overlays"))


def _cues(manifest: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    for key in ("cues", "micro_cues", "beat_cues"):
        cues = [c for c in _records(manifest.get(key)) if _num(c.get("start")) is not None]
        if cues:
            return sorted(cues, key=lambda c: _num(c.get("start")))
    return []


def _hook_slow(manifest, cues, segments) -> List[Issue]:
    issues: List[Issue] = []
    text_starts = [_num(c.get("start")) for c in cues if str(c.get("text") or "").strip()]
    for overlay in _overlay_records(manifest):
        start = _num(overlay.get("start"))
        if start is None:
            start = 0.0 if overlay.get("start") is None else None
        if start is not None and any(True for _ in _overlay_strings(overlay)):
            text_starts.append(start)
    text_starts = [t for t in text_starts if t is not None]
    if text_starts:
        first_text = min(text_starts)
        if first_text > HOOK_TEXT_MAX_SEC + 1e-6:
            issues.append(Issue("HOOK_SLOW", SEVERITY_WARN, 0.0, _r(first_text),
                                f"ข้อความแรกขึ้นจอที่ {_fmt(first_text)} วินาที ช้ากว่า {HOOK_TEXT_MAX_SEC} วินาที "
                                "ใส่ข้อความ hook ตั้งแต่เฟรมแรก", detail="text"))
    elif segments:
        issues.append(Issue("HOOK_SLOW", SEVERITY_WARN, 0.0, None,
                            "ไม่มีข้อความบนจอเลย ใส่ข้อความ hook ตั้งแต่เฟรมแรก", detail="text"))

    word_starts = [_num(w.get("start")) for w in _records(manifest.get("word_timings"))]
    word_starts = [t for t in word_starts if t is not None]
    voice_starts = word_starts or [_num(c.get("start")) for c in cues]
    if voice_starts:
        first_voice = min(voice_starts)
        if first_voice > HOOK_VOICE_MAX_SEC + 1e-6:
            issues.append(Issue("HOOK_SLOW", SEVERITY_WARN, 0.0, _r(first_voice),
                                f"เสียงพากย์คำแรกเริ่มที่ {_fmt(first_voice)} วินาที ช้ากว่า {HOOK_VOICE_MAX_SEC} วินาที "
                                "ตัดช่วงเงียบหัวคลิปออก", detail="voice"))
    return issues


def _shot_rules(segments, policy: StyleMotionPolicy) -> List[Issue]:
    issues: List[Issue] = []
    shot_cap = policy.max_shot * LONG_SHOT_FACTOR
    for seg in segments:
        clip, index, dur = seg["clip"], seg["index"], seg["dur"]
        start, end = _r(seg["start"]), _r(seg["end"])
        hold_reason = clip.get("hold_reason")
        if hold_reason:
            reason = HOLD_REASON_TH.get(str(hold_reason), str(hold_reason))
            issues.append(Issue("HOLD", SEVERITY_INFO, start, end,
                                f"ช็อตนี้ค้างภาพยาว {_fmt(dur)} วินาทีตามที่อนุญาต ({reason})",
                                clip_index=index, detail=str(hold_reason)))
            continue
        if dur > shot_cap + TIME_TOLERANCE:
            issues.append(Issue("LONG_SHOT", SEVERITY_WARN, start, end,
                                f"ช็อตยาว {_fmt(dur)} วินาที เกินเพดาน {_fmt(shot_cap)} วินาทีของสไตล์นี้ "
                                "แบ่งช็อตหรือแทรกภาพมุมอื่น", clip_index=index))
        if seg["start"] < policy.hook_window_sec - 1e-6 and dur > policy.hook_max_shot + TIME_TOLERANCE:
            issues.append(Issue("HOOK_PACING", SEVERITY_WARN, start, end,
                                f"ช็อตช่วง hook ({_fmt(policy.hook_window_sec)} วินาทีแรก) ยาว {_fmt(dur)} วินาที "
                                f"ควรไม่เกิน {_fmt(policy.hook_max_shot)} วินาที", clip_index=index))
    return issues


def _moving_intervals(keyframes: Any) -> List[Tuple[float, float]]:
    points = []
    for point in keyframes if isinstance(keyframes, list) else []:
        if isinstance(point, Mapping):
            t = _num(point.get("time", 0.0))
            if t is not None:
                points.append((t, point))
    points.sort(key=lambda item: item[0])
    previous: Dict[str, Tuple[float, float]] = {}
    out: List[Tuple[float, float]] = []
    for t, point in points:
        for prop in ("zoom", "pan_x", "pan_y"):
            raw = point.get(prop) if prop in point else (point.get("value") if point.get("property") == prop else None)
            value = _num(raw)
            if value is None:
                continue
            if prop in previous and abs(previous[prop][1] - value) > 1e-6 and t > previous[prop][0]:
                out.append((previous[prop][0], t))
            previous[prop] = (t, value)
    return out


def _static_spans(segments, policy: StyleMotionPolicy) -> List[Issue]:
    limit = policy.max_static_sec
    if not limit or limit <= 0:
        return []
    issues: List[Issue] = []
    for pos, seg in enumerate(segments):
        dur = seg["dur"]
        moving = list(_moving_intervals(seg["clip"].get("keyframes")))
        if seg["overlap"] > 0:
            moving.append((0.0, seg["overlap"]))
        if pos + 1 < len(segments) and segments[pos + 1]["overlap"] > 0:
            moving.append((dur - segments[pos + 1]["overlap"], dur))
        cursor = 0.0
        gaps: List[Tuple[float, float]] = []
        for a, b in sorted((max(0.0, a), min(dur, b)) for a, b in moving):
            if b <= a:
                continue
            if a > cursor:
                gaps.append((cursor, a))
            cursor = max(cursor, b)
        if dur > cursor:
            gaps.append((cursor, dur))
        for a, b in gaps:
            if b - a > limit + TIME_TOLERANCE:
                issues.append(Issue("STATIC_SPAN", SEVERITY_WARN, _r(seg["start"] + a), _r(seg["start"] + b),
                                    f"ภาพนิ่ง {_fmt(b - a)} วินาที ไม่มีตัด รอยต่อ หรือกล้องขยับ "
                                    f"(สไตล์นี้ไม่ควรเกิน {_fmt(limit)} วินาที) เพิ่ม camera punch หรือแทรกช็อต",
                                    clip_index=seg["index"]))
    return issues


def _dead_air(cues) -> List[Issue]:
    issues: List[Issue] = []
    voice_end = None
    for cue in cues:
        start, end = _num(cue.get("start")), _num(cue.get("end"))
        if voice_end is not None and start - voice_end > DEAD_AIR_SEC + 1e-6:
            issues.append(Issue("DEAD_AIR", SEVERITY_WARN, _r(voice_end), _r(start),
                                f"เสียงพากย์เงียบ {_fmt(start - voice_end)} วินาที เกิน {DEAD_AIR_SEC} วินาที "
                                "ขยับประโยคให้ชิดกันหรือตัดช่วงเงียบ"))
        if end is not None:
            voice_end = end if voice_end is None else max(voice_end, end)
    return issues


def _sfx_fire_times(manifest, cues, segments, duration: Optional[float]) -> List[float]:
    overlays = _records(manifest.get("overlays"))
    cut_times = [seg["start"] for seg in segments[1:]]
    if _plan_sfx_events is not None:
        try:
            events = _plan_sfx_events(list(cues), overlays, total_duration=duration, cut_times=cut_times)
            return sorted(float(e["fire"]) for e in events)
        except Exception:  # pragma: no cover - planner contract drift
            pass
    raw = [_num(item.get("start")) for item in list(cues) + overlays if item.get("sfx")]
    return sorted(t for t in raw if t is not None)


def _sfx_dense(manifest, cues, segments, duration) -> List[Issue]:
    issues: List[Issue] = []
    fires = _sfx_fire_times(manifest, cues, segments, duration)
    for a, b in zip(fires, fires[1:]):
        if b - a < SFX_MIN_GAP_SEC - 1e-6:
            issues.append(Issue("SFX_DENSE", SEVERITY_WARN, _r(a), _r(b),
                                f"เสียงเอฟเฟกต์ 2 เสียงห่างกันแค่ {_fmt(b - a)} วินาที "
                                f"ควรห่างอย่างน้อย {_fmt(SFX_MIN_GAP_SEC)} วินาที"))
    return issues


def _length(duration: Optional[float], target: Optional[float]) -> List[Issue]:
    if duration is None or target is None:
        return []
    limit = target * (1 + LENGTH_TOLERANCE)
    if duration <= limit + 1e-6:
        return []
    return [Issue("LENGTH", SEVERITY_WARN, _r(target), _r(duration),
                  f"คลิปยาว {_fmt(duration)} วินาที เกินเป้า {_fmt(target)} วินาทีเกิน 15% "
                  f"(ไม่ควรเกิน {_fmt(limit)} วินาที) ตัดประโยคหรือช็อตที่ไม่จำเป็น")]


def _line_spans(manifest: Mapping[str, Any], count: int) -> List[Tuple[Optional[float], Optional[float]]]:
    """Timeline span of each script line, from line-folded beat cues when they line up."""
    beats = _records(manifest.get("beat_cues"))
    if len(beats) == count:
        return [(_r(_num(b.get("start"))), _r(_num(b.get("end")))) for b in beats]
    return [(None, None)] * count


def _script_lines(manifest: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    script = manifest.get("script_data") if isinstance(manifest.get("script_data"), Mapping) else {}
    lines = _records(script.get("lines"))
    if lines:
        return lines
    return _records(manifest.get("beat_cues")) or _records(manifest.get("cues"))


def _structure(manifest, target, timeline_known: bool) -> List[Issue]:
    lines = _script_lines(manifest)
    if not lines:
        return []
    spans = _line_spans(manifest, len(lines))
    if spans[0][0] is None:
        timed = [(_r(_num(c.get("start"))), _r(_num(c.get("end")))) for c in lines]
        if all(s is not None for s, _ in timed):
            spans = timed
    result = compliance_lint.check_script_structure(lines, target_duration=target)
    issues: List[Issue] = []
    for warning in result.get("warnings", []):
        code = warning.get("code")
        if code == compliance_lint.STRUCT_LENGTH_OFF_TARGET and timeline_known:
            continue  # LENGTH judges the real timeline; the char estimate would repeat it
        start = end = None
        if code == compliance_lint.STRUCT_NO_OPEN_LOOP:
            head = spans[: min(2, len(spans))]
            start, end = head[0][0], head[-1][1]
        elif code == compliance_lint.STRUCT_FILLER_ENDING:
            start, end = spans[-1]
        issues.append(Issue("STRUCTURE", SEVERITY_WARN, start, end, str(warning.get("message") or ""), detail=code))
    return issues


def _compliance(manifest, cues, policy: StyleMotionPolicy, duration: Optional[float]) -> List[Issue]:
    texts: List[Tuple[Any, Optional[float], Optional[float]]] = []
    for cue in cues:
        texts.append((cue.get("text"), _r(_num(cue.get("start"))), _r(_num(cue.get("end")))))
    for beat in _records(manifest.get("beat_cues")):
        span = (_r(_num(beat.get("start"))), _r(_num(beat.get("end"))))
        texts.append((beat.get("text"), *span))
        texts.append((beat.get("on_screen"), *span))
    script = manifest.get("script_data") if isinstance(manifest.get("script_data"), Mapping) else {}
    lines = _records(script.get("lines"))
    for line, span in zip(lines, _line_spans(manifest, len(lines))):
        texts.append((line.get("text"), *span))
        texts.append((line.get("on_screen"), *span))
    hook_end = _r(min(policy.hook_window_sec, duration) if duration else policy.hook_window_sec)
    for source in (script, manifest):
        for key in _HOOK_FIELDS:
            if isinstance(source.get(key), str):
                texts.append((source.get(key), 0.0, hook_end))
    for overlay in _overlay_records(manifest):
        span = (_r(_num(overlay.get("start"))), _r(_num(overlay.get("end"))))
        for text in _overlay_strings(overlay):
            texts.append((text, *span))

    issues: List[Issue] = []
    seen: Dict[Tuple[Any, Any], List[Tuple[Optional[float], Optional[float]]]] = {}

    def _overlaps(a, b) -> bool:
        if a[0] is None or b[0] is None:
            return a[0] is None and b[0] is None
        a_end = a[1] if a[1] is not None else a[0]
        b_end = b[1] if b[1] is not None else b[0]
        return a[0] <= b_end + 1e-6 and b[0] <= a_end + 1e-6

    def _add(severity: str, violation: Mapping[str, Any], start, end) -> None:
        # The same phrase reaches a cue, its folded beat cue and the script
        # line; report it once, on the first (narrowest: cues go first) span.
        spans = seen.setdefault((violation.get("code"), violation.get("message")), [])
        if any(_overlaps((start, end), span) for span in spans):
            return
        spans.append((start, end))
        issues.append(Issue("COMPLIANCE", severity, start, end, str(violation.get("message") or ""),
                            detail=violation.get("code")))

    for text, start, end in texts:
        if not isinstance(text, str) or not text.strip():
            continue
        for violation in compliance_lint.lint_text(text):
            _add(SEVERITY_BLOCK, violation, start, end)

    first_line = None
    if lines:
        first_line = (lines[0].get("text"), *_line_spans(manifest, len(lines))[0])
    elif cues:
        first_line = (cues[0].get("text"), _r(_num(cues[0].get("start"))), _r(_num(cues[0].get("end"))))
    if first_line and isinstance(first_line[0], str):
        for violation in compliance_lint.lint_opening_line(first_line[0]):
            _add(SEVERITY_WARN, violation, first_line[1], first_line[2])
    return issues


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def timeline_duration(manifest: Mapping[str, Any], segments: Optional[List[Dict[str, Any]]] = None) -> Optional[float]:
    segments = layout_clips(manifest) if segments is None else segments
    if segments:
        return max(seg["end"] for seg in segments)
    total = _num(manifest.get("total_duration"))
    if total is not None and total > 0:
        return total
    ends = [_num(c.get("end")) for c in _cues(manifest)]
    ends = [e for e in ends if e is not None]
    return max(ends) if ends else None


def lint_manifest(manifest: Any, policy: Any = None) -> List[Issue]:
    """Every retention/compliance issue of ``manifest``, sorted by time."""
    if not isinstance(manifest, Mapping):
        return []
    style = _resolve_policy(manifest, policy)
    segments = layout_clips(manifest)
    cues = _cues(manifest)
    duration = timeline_duration(manifest, segments)
    target = _target_duration(manifest)

    issues: List[Issue] = []
    issues += _hook_slow(manifest, cues, segments)
    issues += _shot_rules(segments, style)
    issues += _static_spans(segments, style)
    issues += _dead_air(cues)
    issues += _sfx_dense(manifest, cues, segments, duration)
    issues += _length(duration if segments else None, target)
    issues += _structure(manifest, target, timeline_known=bool(segments))
    issues += _compliance(manifest, cues, style, duration)

    rank = {SEVERITY_BLOCK: 0, SEVERITY_WARN: 1, SEVERITY_INFO: 2}
    issues.sort(key=lambda i: (i.start is None, i.start if i.start is not None else 0.0, rank[i.severity], i.code))
    return issues


def summarize(issues: Sequence[Issue]) -> Dict[str, int]:
    summary = {severity: 0 for severity in SEVERITIES}
    for issue in issues:
        summary[issue.severity] += 1
    return summary


def score(issues: Sequence[Issue]) -> int:
    """100 - 30/block - 6/warn - 1/info, at most SCORE_MAX_PER_CODE issues per (code, severity)."""
    counted: Dict[Tuple[str, str], int] = {}
    penalty = 0
    for issue in issues:
        key = (issue.code, issue.severity)
        if counted.get(key, 0) >= SCORE_MAX_PER_CODE:
            continue
        counted[key] = counted.get(key, 0) + 1
        penalty += SCORE_PENALTY[issue.severity]
    return max(0, min(100, 100 - penalty))


def lint_report(manifest: Any, policy: Any = None) -> Dict[str, Any]:
    """API shape: ``{issues, summary: {block, warn, info}, score}``."""
    issues = lint_manifest(manifest, policy)
    return {"issues": [issue.to_dict() for issue in issues], "summary": summarize(issues), "score": score(issues)}


__all__ = [
    "Issue",
    "SEVERITY_BLOCK",
    "SEVERITY_WARN",
    "SEVERITY_INFO",
    "layout_clips",
    "lint_manifest",
    "lint_report",
    "score",
    "summarize",
    "timeline_duration",
]
