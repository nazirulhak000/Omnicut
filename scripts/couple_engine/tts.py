# -*- coding: utf-8 -*-
"""Two-pass Single-Take TTS synthesizer for Couple Paper Chat (#5) clips.

Strictly enforces Rule 20:
- Only models in ALLOWED_TTS_MODELS ('gemini-3.8-flash-tts', 'gemini-3.1-flash-tts-preview') are allowed.
- Never falls back to 'gemini-2.5-flash-preview-tts'.
- When all configured API keys return 429 / quota exhausted, raises QuotaExhaustedError
  so the job orchestrator can transition to 'paused_quota'.
"""

from __future__ import annotations

import base64
import inspect
import json
from pathlib import Path
import urllib.error
import urllib.request
import wave
from typing import Any, Callable, Dict, List, Optional, Sequence

from scripts.config import get_gemini_api_keys
from scripts.couple_engine.config import (
    ALLOWED_TTS_MODELS,
    BAO_VOICE_CONFIG,
    DEFAULT_TTS_MODEL,
    NUI_VOICE_CONFIG,
    validate_tts_model,
)


class QuotaExhaustedError(RuntimeError):
    """Raised when all Gemini API keys return 429 / quota exhausted for allowed TTS models."""


def _extract_turn_speaker_and_text(turn: Any) -> tuple[str, str]:
    """Extract normalized speaker ('F' or 'M') and spoken text from a turn specification."""
    if isinstance(turn, (list, tuple)):
        raw_spk = str(turn[0]).strip().upper()
        body = turn[1] if len(turn) > 1 else ""
        if isinstance(body, str):
            text = body
        elif isinstance(body, (list, tuple)):
            parts = []
            for item in body:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    parts.append(str(item[1]))
                elif isinstance(item, dict):
                    parts.append(str(item.get("spoken_text") or item.get("spoken") or item.get("display_text") or item.get("text") or ""))
                else:
                    parts.append(str(item))
            text = " ".join(p.strip() for p in parts if p and str(p).strip())
        else:
            text = str(body)
    elif isinstance(turn, dict):
        raw_spk = str(turn.get("speaker", "F")).strip().upper()
        if "spoken_text" in turn or "text" in turn:
            text = str(turn.get("spoken_text") or turn.get("text") or "").strip()
        else:
            phrases = turn.get("phrases", [])
            parts = []
            for p in phrases:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    parts.append(str(p[1]))
                elif isinstance(p, dict):
                    parts.append(str(p.get("spoken_text") or p.get("spoken") or p.get("display_text") or p.get("display") or p.get("text") or ""))
                else:
                    parts.append(str(p))
            text = " ".join(x.strip() for x in parts if x and str(x).strip())
    else:
        raise TypeError(f"Unsupported turn format: {type(turn)!r}")

    if raw_spk.startswith("F") or "นุ้ย" in raw_spk or "NUI" in raw_spk:
        spk = "F"
    else:
        spk = "M"
    return spk, text


def build_single_take_prompt(lines: Sequence[str], voice_config: Dict[str, Any]) -> str:
    """Build the single-take prompt with Monolithic Acting Guard and 2s silence separator."""
    joined = "\n\n... ...\n\n".join(str(line).strip() for line in lines if str(line).strip())
    style = voice_config.get("style", "")
    guard = voice_config.get("guard", "")
    return (
        f"[Voice style: {style}\n"
        f"{guard}\n"
        f"Between each section where you see '... ...' leave a clear 2 second silence.]\n\n"
        f"{joined}\n"
    )


def _write_silence_wav(path: Path, duration_sec: float = 0.5, sr: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_samples = max(1, int(duration_sec * sr))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * n_samples)


def _default_gemini_tts_request(
    *,
    prompt: str,
    voice_name: str,
    model: str,
    api_key: str,
    out_wav: Path,
    timeout: int = 180,
) -> Path:
    """Perform a single HTTP call to Gemini TTS API for an allowed model."""
    validate_tts_model(model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice_name}
                }
            },
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res_data = json.loads(resp.read())
        pcm = base64.b64decode(
            res_data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        )
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm)
    return out_wav


def _invoke_custom_tts_fn(
    tts_fn: Callable[..., Any],
    *,
    speaker: str,
    lines: List[str],
    prompt: str,
    voice_config: Dict[str, Any],
    model: str,
    out_wav: Path,
    api_key: str,
) -> Path:
    """Invoke a caller/test-supplied tts_fn with flexible argument matching."""
    sig = inspect.signature(tts_fn)
    params = list(sig.parameters.values())
    accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
    param_names = {p.name for p in params}

    kwargs: Dict[str, Any] = {
        "speaker": speaker,
        "lines": lines,
        "prompt": prompt,
        "voice_config": voice_config,
        "voice_name": voice_config["voice_name"],
        "model": model,
        "out_wav": out_wav,
        "output_path": out_wav,
        "api_key": api_key,
    }

    if accepts_var_kw:
        result = tts_fn(**kwargs)
    elif param_names and param_names.issubset(kwargs.keys()):
        filtered = {k: v for k, v in kwargs.items() if k in param_names}
        result = tts_fn(**filtered)
    else:
        # Positional fallback based on parameter count
        pos_args_map = {
            1: (prompt,),
            2: (prompt, out_wav),
            3: (prompt, voice_config["voice_name"], out_wav),
            4: (lines, voice_config, model, out_wav),
            5: (lines, voice_config, model, out_wav, api_key),
        }
        pos_args = pos_args_map.get(len(params), (prompt, voice_config["voice_name"], model, out_wav))
        result = tts_fn(*pos_args)

    if isinstance(result, (bytes, bytearray)):
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(bytes(result))
    elif not out_wav.exists():
        _write_silence_wav(out_wav)
    return out_wav


def _is_quota_error(exc: BaseException) -> bool:
    if isinstance(exc, QuotaExhaustedError):
        return True
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg or "quota" in msg or "resource_exhausted" in msg or "rate limit" in msg


def synthesize_couple_clip_passes(
    turns: Sequence[Any],
    output_dir: Path | str,
    model: str = DEFAULT_TTS_MODEL,
    tts_fn: Optional[Callable[..., Any]] = None,
    api_keys: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Synthesize a Couple Paper Chat clip in 2 single-take passes (Pass 1: Nui, Pass 2: Bao).

    Args:
        turns: Sequence of turn dicts or tuples.
        output_dir: Directory where `pass_f.wav` and `pass_m.wav` are written.
        model: Primary TTS model (must be in ALLOWED_TTS_MODELS).
        tts_fn: Optional injectable TTS callable for offline tests or custom transport.
        api_keys: Optional list of Gemini API keys to rotate through on 429 errors.

    Returns:
        Dict with pass metadata, file paths, turn index mappings, and models used.
    """
    primary_model = validate_tts_model(model)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    f_lines: List[str] = []
    f_turn_indices: List[int] = []
    m_lines: List[str] = []
    m_turn_indices: List[int] = []

    for idx, turn in enumerate(turns):
        spk, text = _extract_turn_speaker_and_text(turn)
        if spk == "F":
            f_lines.append(text)
            f_turn_indices.append(idx)
        else:
            m_lines.append(text)
            m_turn_indices.append(idx)

    keys = list(api_keys) if api_keys is not None else get_gemini_api_keys()
    if not keys:
        keys = ["test_default_key"]

    # Candidate models strictly from ALLOWED_TTS_MODELS only (primary first)
    candidate_models = [primary_model] + [
        m for m in ALLOWED_TTS_MODELS if m != primary_model
    ]

    passes_spec = [
        ("F", f_lines, f_turn_indices, NUI_VOICE_CONFIG, out_dir / "pass_f.wav"),
        ("M", m_lines, m_turn_indices, BAO_VOICE_CONFIG, out_dir / "pass_m.wav"),
    ]

    pass_results: Dict[str, Any] = {}
    requests_made = 0

    for spk, lines, turn_indices, voice_cfg, wav_path in passes_spec:
        if not lines:
            pass_results[spk] = {
                "speaker": spk,
                "voice_name": voice_cfg["voice_name"],
                "wav_path": None,
                "turn_indices": [],
                "line_count": 0,
                "model_used": None,
            }
            continue

        prompt = build_single_take_prompt(lines, voice_cfg)
        succeeded = False
        used_model = None
        saw_quota_error = False
        last_error: Optional[BaseException] = None

        for cand_model in candidate_models:
            validate_tts_model(cand_model)
            for key in keys:
                try:
                    requests_made += 1
                    if tts_fn is not None:
                        _invoke_custom_tts_fn(
                            tts_fn,
                            speaker=spk,
                            lines=lines,
                            prompt=prompt,
                            voice_config=voice_cfg,
                            model=cand_model,
                            out_wav=wav_path,
                            api_key=key,
                        )
                    else:
                        _default_gemini_tts_request(
                            prompt=prompt,
                            voice_name=voice_cfg["voice_name"],
                            model=cand_model,
                            api_key=key,
                            out_wav=wav_path,
                        )
                    succeeded = True
                    used_model = cand_model
                    break
                except Exception as exc:
                    last_error = exc
                    if _is_quota_error(exc):
                        saw_quota_error = True
                        continue
                    raise
            if succeeded:
                break

        if not succeeded:
            if saw_quota_error:
                raise QuotaExhaustedError(
                    f"Quota exhausted (HTTP 429) across all {len(keys)} API key(s) "
                    f"and allowed models {candidate_models} for speaker '{spk}'."
                ) from last_error
            raise RuntimeError(f"TTS synthesis failed for speaker '{spk}': {last_error}") from last_error

        pass_results[spk] = {
            "speaker": spk,
            "voice_name": voice_cfg["voice_name"],
            "wav_path": wav_path,
            "turn_indices": turn_indices,
            "line_count": len(lines),
            "model_used": used_model,
            "prompt": prompt,
        }

    return {
        "passes": pass_results,
        "f_wav": pass_results["F"]["wav_path"],
        "m_wav": pass_results["M"]["wav_path"],
        "requests_made": requests_made,
        "model": primary_model,
    }
