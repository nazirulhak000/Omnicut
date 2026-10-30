# -*- coding: utf-8 -*-
"""Transcript verification gate for Couple Paper Chat (#5) voiceovers."""

from __future__ import annotations

from difflib import SequenceMatcher
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

_CLEAN_RE = re.compile(r"[^\u0E00-\u0E7Fa-zA-Z0-9]+")
_FORBIDDEN_FILLERS = ("เอ่อ", "อืม", "สวัสดีครับ", "สวัสดีค่ะ", "โฮโฮ")


def _normalize_text(text: str) -> str:
    return _CLEAN_RE.sub("", (text or "").lower())


def _extract_expected_turn_texts(expected_turns: Sequence[Any]) -> List[str]:
    texts: List[str] = []
    for t in expected_turns:
        if isinstance(t, str):
            texts.append(t.strip())
        elif isinstance(t, (list, tuple)):
            body = t[1] if len(t) > 1 else ""
            if isinstance(body, str):
                texts.append(body.strip())
            elif isinstance(body, (list, tuple)):
                parts = []
                for p in body:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        parts.append(str(p[1]))
                    elif isinstance(p, dict):
                        parts.append(
                            str(
                                p.get("spoken_text")
                                or p.get("spoken")
                                or p.get("display_text")
                                or p.get("text")
                                or ""
                            )
                        )
                    else:
                        parts.append(str(p))
                texts.append(" ".join(x.strip() for x in parts if x and str(x).strip()))
            else:
                texts.append(str(body).strip())
        elif isinstance(t, dict):
            if "spoken_text" in t or "text" in t:
                texts.append(str(t.get("spoken_text") or t.get("text") or "").strip())
            else:
                phrases = t.get("phrases", [])
                parts = []
                for p in phrases:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        parts.append(str(p[1]))
                    elif isinstance(p, dict):
                        parts.append(
                            str(
                                p.get("spoken_text")
                                or p.get("spoken")
                                or p.get("display_text")
                                or p.get("display")
                                or p.get("text")
                                or ""
                            )
                        )
                    else:
                        parts.append(str(p))
                texts.append(" ".join(x.strip() for x in parts if x and str(x).strip()))
        else:
            texts.append(str(t).strip())
    return texts


def verify_clip_transcript(
    vo_path: Union[Path, str],
    expected_turns: Sequence[Any],
    output_verify_path: Union[Path, str],
    transcriber_fn: Optional[Callable[[Path], Any]] = None,
    min_similarity: float = 0.80,
) -> Dict[str, Any]:
    """Verify voiceover transcript against expected dialogue turns and write `verify.json`.

    Strictly fails (`passed=False`) when:
    - `vo_path` is missing or empty
    - `similarity < min_similarity`
    - Transcribed turn count mismatches `len(expected_turns)` (when per-turn segments are returned)
    - Unscripted filler hallucinations occur
    """
    vo_file = Path(vo_path)
    out_file = Path(output_verify_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    expected_list = _extract_expected_turn_texts(expected_turns)
    expected_full_raw = " ".join(expected_list)
    expected_norm = _normalize_text(expected_full_raw)

    issues: List[str] = []

    if not vo_file.exists() or vo_file.stat().st_size == 0:
        issues.append(f"missing_or_empty_audio:{vo_file}")
        result = {
            "passed": False,
            "similarity": 0.0,
            "turns_checked": 0,
            "expected_turns_count": len(expected_list),
            "issues": issues,
        }
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    if transcriber_fn is not None:
        raw_transcript = transcriber_fn(vo_file)
    else:
        raise RuntimeError(
            "No transcriber_fn provided and offline mode prevents implicit model download."
        )

    heard_turns: Optional[List[str]] = None
    if isinstance(raw_transcript, str):
        heard_full_raw = raw_transcript
    elif isinstance(raw_transcript, dict):
        if "turns" in raw_transcript and isinstance(raw_transcript["turns"], list):
            heard_turns = [
                str(x.get("text", x) if isinstance(x, dict) else x)
                for x in raw_transcript["turns"]
            ]
            heard_full_raw = " ".join(heard_turns)
        else:
            heard_full_raw = str(raw_transcript.get("text", ""))
    elif isinstance(raw_transcript, (list, tuple)):
        heard_turns = [
            str(
                getattr(x, "text", None)
                or (x.get("text") if isinstance(x, dict) else x)
            )
            for x in raw_transcript
        ]
        heard_full_raw = " ".join(heard_turns)
    else:
        heard_full_raw = str(raw_transcript)

    if heard_turns is not None and len(heard_turns) != len(expected_list):
        issues.append(
            f"turn_count_mismatch: expected {len(expected_list)} turns, got {len(heard_turns)}"
        )

    heard_norm = _normalize_text(heard_full_raw)
    if not expected_norm and not heard_norm:
        similarity = 1.0
    elif not expected_norm or not heard_norm:
        similarity = 0.0
    else:
        similarity = round(SequenceMatcher(None, expected_norm, heard_norm).ratio(), 4)

    if similarity < min_similarity:
        issues.append(
            f"low_similarity: {similarity:.3f} < min_similarity {min_similarity:.3f}"
        )

    # Check per-turn similarity if turn-aligned list matches length
    turn_details: List[Dict[str, Any]] = []
    if heard_turns is not None and len(heard_turns) == len(expected_list):
        for idx, (exp_t, hrd_t) in enumerate(zip(expected_list, heard_turns)):
            e_n = _normalize_text(exp_t)
            h_n = _normalize_text(hrd_t)
            t_sim = round(SequenceMatcher(None, e_n, h_n).ratio(), 4) if (e_n or h_n) else 1.0
            t_ok = t_sim >= min_similarity
            if not t_ok:
                issues.append(
                    f"turn_{idx:02d}_low_similarity: {t_sim:.3f} < {min_similarity:.3f}"
                )
            turn_details.append(
                {
                    "turn": idx,
                    "expected": exp_t,
                    "heard": hrd_t,
                    "similarity": t_sim,
                    "passed": t_ok,
                }
            )

    for filler in _FORBIDDEN_FILLERS:
        if filler in heard_full_raw and filler not in expected_full_raw:
            issues.append(f"forbidden_filler_detected:{filler}")

    turns_checked = len(heard_turns) if heard_turns is not None else len(expected_list)
    passed = len(issues) == 0 and similarity >= min_similarity

    result = {
        "passed": bool(passed),
        "similarity": float(similarity),
        "turns_checked": int(turns_checked),
        "expected_turns_count": len(expected_list),
        "issues": issues,
        "turns": turn_details,
    }
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
