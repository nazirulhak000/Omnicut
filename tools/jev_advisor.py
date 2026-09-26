"""
Jev Decision Layer CLI — the single entry point every AI agent uses to ask
TypeSafe System One (Jev) for a structured decision.

Rule: .agents/rules/jev_decision_layer.md
Skill: .agents/skills/typesafe-ai/SKILL.md

Design notes
------------
* Read-only. Never writes to the repo. State files are supplied by the caller
  (conventionally under .tmp/).
* One API call answers every question (System One fan-out), so a multi-question
  spec costs the same as a single question.
* Always prints a machine-readable JSON object on stdout, including a
  ``verdict`` so callers can gate on confidence instead of eyeballing values.
* Degrades gracefully: a missing key or SDK never raises, it reports ``ok:false``
  and exits with EXIT_UNAVAILABLE so agent work is never blocked by Jev.

Exit codes
----------
0  proceed    - every question met the confidence threshold
1  escalate   - at least one answer was missing or below the threshold
2  unavailable- no API key, SDK missing, or the call itself failed
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CONFIDENCE_THRESHOLD = 0.80

EXIT_OK = 0
EXIT_ESCALATE = 1
EXIT_UNAVAILABLE = 2

VALID_KINDS = ("choice", "score", "noul")


# ── helpers ────────────────────────────────────────────────────────────────

def _emit(payload: Dict[str, Any], code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


def _load_json_arg(raw: str) -> Dict[str, Any]:
    """Accept either an inline JSON document or a path to a .json file."""
    candidate = Path(raw).expanduser()
    if candidate.is_file():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(raw)


def _parse_options(pairs: List[str]) -> Dict[str, str]:
    """Turn ``--option "key=description"`` repeats into a criteria dict."""
    criteria: Dict[str, str] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"--option ต้องเป็น 'key=description' แต่ได้: {pair!r}")
        key, description = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"--option ต้องมี key แต่ได้: {pair!r}")
        criteria[key] = description.strip()
    if not criteria:
        raise ValueError("ต้องมี --option อย่างน้อย 1 ตัว")
    return criteria


def _parse_levels(raw: str) -> List[str]:
    levels = [item.strip() for item in raw.split(",") if item.strip()]
    if len(levels) < 2:
        raise ValueError("--levels ต้องมีอย่างน้อย 2 ระดับ คั่นด้วยลูกน้ำ")
    return levels


def _build_questions(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a fan-out spec into typesafe_sdk question objects."""
    from typesafe_sdk import Choice, Noul, Score

    builders = {"choice": Choice, "score": Score, "noul": Noul}
    questions: Dict[str, Any] = {}
    for name, raw in spec.items():
        kind = str(raw.get("type", "")).strip().lower()
        if kind not in VALID_KINDS:
            raise ValueError(f"question {name!r}: type ต้องเป็นหนึ่งใน {VALID_KINDS} แต่ได้ {raw.get('type')!r}")
        instructions = str(raw.get("instructions", "")).strip()
        if not instructions:
            raise ValueError(f"question {name!r}: ต้องมี instructions")
        if kind == "choice":
            criteria = raw.get("criteria") or {}
            if not isinstance(criteria, dict) or not criteria:
                raise ValueError(f"question {name!r}: choice ต้องมี criteria เป็น dict ที่ไม่ว่าง")
            questions[name] = builders[kind](instructions=instructions, criteria=criteria)
        elif kind == "score":
            levels = raw.get("levels") or raw.get("criteria") or []
            if not isinstance(levels, list) or len(levels) < 2:
                raise ValueError(f"question {name!r}: score ต้องมี levels เป็น list อย่างน้อย 2 ระดับ")
            questions[name] = builders[kind](instructions=instructions, criteria=levels)
        else:
            questions[name] = builders[kind](instructions=instructions)
    if not questions:
        raise ValueError("ต้องมีคำถามอย่างน้อย 1 ข้อ")
    return questions



# ── decision normalisation ────────────────────────────────────────────────

_ACTIVE_THRESHOLD = DEFAULT_CONFIDENCE_THRESHOLD


def _float_or_none(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_kind(question_obj: Any, kind: str) -> bool:
    return type(question_obj).__name__.lower() == kind


def _pick(response: Any, bucket: str, name: str) -> Any:
    holder = getattr(response, bucket, None) or {}
    return holder[name]


def _normalize(kind: str, obj: Any) -> Dict[str, Any]:
    """Flatten one SDK response object into a stable dict.

    The SDK does not always populate ``confidence`` and ships different field
    names across versions, so every lookup is defensive: a missing value
    surfaces as ``None`` and forces ``escalate`` rather than raising.
    """
    confidence = _float_or_none(getattr(obj, "confidence", None))
    out: Dict[str, Any] = {"kind": kind, "confidence": confidence}
    if kind == "choice":
        out["choice"] = getattr(obj, "choice", None)
        distribution = dict(getattr(obj, "distribution", None) or {})
        out["distribution"] = {str(k): _float_or_none(v) for k, v in distribution.items()} or None
    elif kind == "score":
        out["score"] = _float_or_none(getattr(obj, "score", None))
        levels = getattr(obj, "probabilities", None) or getattr(obj, "level_probabilities", None) or {}
        out["level_probabilities"] = {str(k): _float_or_none(v) for k, v in dict(levels).items()} or None
    else:
        out["noul"] = _float_or_none(getattr(obj, "noul", None))
    out["escalate"] = confidence is None or confidence < _ACTIVE_THRESHOLD
    return out


def ask(questions: Dict[str, Any], state: Dict[str, Any], threshold: float) -> Dict[str, Any]:
    """Run exactly one System One call and normalise every answer."""
    global _ACTIVE_THRESHOLD
    _ACTIVE_THRESHOLD = threshold

    from scripts.typesafe_bridge import get_typesafe_client, is_typesafe_available

    if not is_typesafe_available():
        return {
            "ok": False,
            "error": "TYPESAFE_API_KEY is not configured",
            "hint": "ตั้งค่า TYPESAFE_API_KEY ใน .env แล้วโหลด .venv ใหม่",
        }

    client = get_typesafe_client()
    if not client:
        return {
            "ok": False,
            "error": "TypeSafe client could not be initialised",
            "hint": "ตรวจว่า typesafe-sdk ติดตั้งใน .venv แล้ว",
        }

    started = time.perf_counter()
    try:
        response = client.system_one(state=state, questions=questions)
    except Exception as exc:  # network/auth/quota -> never crash the caller
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "hint": "Jev ใช้ไม่ได้ตอนนี้ ให้ทำงานต่อแบบ degrade และแจ้งผู้ใช้",
        }
    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    results: Dict[str, Any] = {}
    for name, question in questions.items():
        kind = _is_kind(question, "choice") and "choice" or _is_kind(question, "score") and "score" or "noul"
        bucket = {"choice": "choices", "score": "scores", "noul": "nouls"}[kind]
        results[name] = _normalize(kind, _pick(response, bucket, name))

    needs_escalation = [name for name, value in results.items() if value["escalate"]]
    return {
        "ok": True,
        "latency_ms": latency_ms,
        "confidence_threshold": threshold,
        "verdict": "escalate" if needs_escalation else "proceed",
        "escalate_on": needs_escalation,
        "results": results,
    }


# ── CLI ───────────────────────────────────────────────────────────────────

def _spec_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    """Wrap a single-question invocation into the same fan-out spec shape."""
    name = (getattr(args, "name", None) or args.cmd).strip()
    if args.cmd == "noul":
        return {name: {"type": "noul", "instructions": args.instructions}}
    if args.cmd == "choice":
        return {name: {"type": "choice", "instructions": args.instructions,
                       "criteria": _parse_options(args.option)}}
    return {name: {"type": "score", "instructions": args.instructions,
                   "levels": _parse_levels(args.levels)}}


def _check() -> int:
    payload: Dict[str, Any] = {"tool": "jev_advisor", "model": "Jev (TypeSafe System One)"}
    try:
        from scripts.typesafe_bridge import get_typesafe_api_key, is_typesafe_available
    except Exception as exc:
        payload.update({"ok": False, "sdk_importable": False, "error": f"{type(exc).__name__}: {exc}"})
        return _emit(payload, EXIT_UNAVAILABLE)

    payload["sdk_importable"] = True
    payload["key_present"] = bool(get_typesafe_api_key())
    payload["ok"] = is_typesafe_available()
    try:
        import typesafe_sdk  # noqa: F401
        payload["typesafe_sdk"] = "installed"
    except Exception as exc:
        payload["typesafe_sdk"] = f"missing: {type(exc).__name__}"
        payload["ok"] = False
    payload["text_input_only"] = True
    if payload["ok"]:
        payload["next"] = "tools/jev_advisor.py fanout --spec <file.json>"
    return _emit(payload, EXIT_OK if payload["ok"] else EXIT_UNAVAILABLE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jev_advisor",
        description="ถาม Jev (TypeSafe System One) เพื่อตัดสินใจร่วมกับ agent — ดู .agents/rules/jev_decision_layer.md",
    )
    parser.add_argument("--check", action="store_true", help="เช็คว่า Jev ใช้ได้ไหม (ไม่ยิงเครือข่าย)")
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE_THRESHOLD,
                        help="เกณฑ์ verdict (ค่าเริ่มต้น 0.80)")
    sub = parser.add_subparsers(dest="cmd")

    noul = sub.add_parser("noul", help="ถามว่าเงื่อนไขเป็นจริงไหม -> 0.0-1.0")
    noul.add_argument("--state", required=True, help="path ไฟล์ .json หรือ JSON inline")
    noul.add_argument("--instructions", required=True)
    noul.add_argument("--name", default="noul", help="ชื่อคำถามในผลลัพธ์ (ค่าเริ่มต้นตามชนิดคำถาม)")

    choice = sub.add_parser("choice", help="เลือก 1 จากหลายตัวเลือก")
    choice.add_argument("--state", required=True)
    choice.add_argument("--instructions", required=True)
    choice.add_argument("--option", action="append", default=[],
                        help="'key=คำอธิบาย' ใช้ซ้ำหลายครั้ง")
    choice.add_argument("--name", default="choice")

    score = sub.add_parser("score", help="ให้คะแนนบนแกนเชิงเรียง")
    score.add_argument("--state", required=True)
    score.add_argument("--instructions", required=True)
    score.add_argument("--levels", required=True, help="ระดับคั่นด้วยลูกน้ำ เช่น 'ต่ำ,กลาง,สูง'")
    score.add_argument("--name", default="score")

    fanout = sub.add_parser("fanout", help="หลายคำถามใน 1 call (แนะนำ)")
    fanout.add_argument("--spec", required=True, help="ไฟล์ .json: {state, questions:{name:{type,...}}}")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.check:
        return _check()
    if not args.cmd:
        parser.print_help()
        return EXIT_UNAVAILABLE

    try:
        if args.cmd == "fanout":
            spec = _load_json_arg(args.spec)
            state = spec.get("state", {})
            raw_questions = spec.get("questions", {})
        else:
            state = _load_json_arg(args.state)
            raw_questions = _spec_from_args(args)
        if not isinstance(state, dict):
            raise ValueError("state ต้องเป็น JSON object")
        questions = _build_questions(raw_questions)
    except Exception as exc:
        return _emit({"ok": False, "error": f"{type(exc).__name__}: {exc}",
                      "hint": "ดู .agents/rules/jev_decision_layer.md หัวข้อ 5"}, EXIT_UNAVAILABLE)

    result = ask(questions, state, args.confidence)
    if not result.get("ok"):
        return _emit(result, EXIT_UNAVAILABLE)
    return _emit(result, EXIT_ESCALATE if result["verdict"] == "escalate" else EXIT_OK)


if __name__ == "__main__":
    raise SystemExit(main())

