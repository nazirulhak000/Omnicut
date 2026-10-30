# -*- coding: utf-8 -*-
"""Audio splitting, dead-air trimming, glitch sanitization, and clip assembly for Couple Paper Chat (#5)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import wave

import numpy as np


def _read_wav_mono(path: Path | str) -> Tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if sampwidth == 2:
        pcm = np.frombuffer(raw, dtype=np.int16)
    else:
        pcm = np.frombuffer(raw, dtype=np.int16)
    if ch > 1 and len(pcm) >= ch:
        pcm = pcm.reshape(-1, ch)[:, 0]
    return pcm.copy(), sr


def _write_wav_mono(path: Path | str, samples: np.ndarray, sr: int = 24000) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if np.issubdtype(samples.dtype, np.floating):
        clipped = np.clip(samples, -1.0, 1.0)
        pcm16 = (clipped * 32767.0).astype(np.int16)
    else:
        pcm16 = samples.astype(np.int16)
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(pcm16.tobytes())
    return out


def _silence_threshold_for_array(arr: np.ndarray) -> float:
    """Return amplitude threshold distinguishing speech from silence/noise floor."""
    if len(arr) == 0:
        return 0.0
    max_abs = float(np.max(np.abs(arr)))
    if np.issubdtype(arr.dtype, np.floating) and max_abs <= 2.0:
        return max(0.008, max_abs * 0.04)
    return max(280.0, max_abs * 0.04)


def split_by_longest_gaps(
    audio_samples: Union[np.ndarray, Sequence[float], Path, str],
    sr: int = 24000,
    expected_count: int = 1,
    min_silence_sec: float = 0.18,
) -> List[np.ndarray]:
    """Split a single-take audio pass into `expected_count` turn segments by longest silence gaps."""
    if isinstance(audio_samples, (Path, str)):
        arr, file_sr = _read_wav_mono(audio_samples)
        sr = sr or file_sr
    else:
        arr = np.asarray(audio_samples)

    if expected_count <= 1 or len(arr) == 0:
        return [arr.copy()]

    win_samples = max(1, int(0.025 * sr))
    hop_samples = max(1, int(0.010 * sr))
    if len(arr) <= win_samples * expected_count:
        return [seg.copy() for seg in np.array_split(arr, expected_count)]

    n_frames = max(1, (len(arr) - win_samples) // hop_samples + 1)
    rms = np.zeros(n_frames, dtype=np.float64)
    arr_f = arr.astype(np.float64)
    for i in range(n_frames):
        chunk = arr_f[i * hop_samples : i * hop_samples + win_samples]
        rms[i] = np.sqrt(np.mean(chunk * chunk)) if len(chunk) else 0.0

    peak_rms = float(np.max(rms)) if len(rms) else 0.0
    thresh = peak_rms * 0.05 if peak_rms > 0 else 0.0
    silent_mask = rms <= thresh

    # Find contiguous silent runs (excluding leading and trailing silence at the very edges)
    runs: List[Tuple[int, int, float]] = []
    in_run = False
    run_start = 0
    for idx, is_silent in enumerate(silent_mask):
        if is_silent and not in_run:
            in_run = True
            run_start = idx
        elif not is_silent and in_run:
            in_run = False
            dur = (idx - run_start) * hop_samples / float(sr)
            if run_start > 0:
                runs.append((run_start, idx, dur))
    # Notice: trailing silence at the end of the file is not an inter-turn gap

    qualifying = [r for r in runs if r[2] >= min_silence_sec]
    if len(qualifying) < expected_count - 1:
        qualifying = runs

    qualifying.sort(key=lambda r: r[2], reverse=True)
    if len(qualifying) >= expected_count - 1:
        selected = sorted(qualifying[: expected_count - 1], key=lambda r: r[0])
        split_indices = [
            int(((r[0] + r[1]) * 0.5) * hop_samples) for r in selected
        ]
        segments: List[np.ndarray] = []
        prev = 0
        for sp in split_indices:
            sp_clamped = max(prev + 1, min(len(arr) - 1, sp))
            segments.append(arr[prev:sp_clamped].copy())
            prev = sp_clamped
        segments.append(arr[prev:].copy())
        return segments

    return [seg.copy() for seg in np.array_split(arr, expected_count)]


def trim_dead_air(
    audio_samples: Union[np.ndarray, Sequence[float]],
    sr: int = 24000,
    pad_lead_sec: float = 0.18,
    pad_tail_sec: float = 0.22,
) -> np.ndarray:
    """Trim leading and trailing dead air while preserving natural lead/tail padding."""
    arr = np.asarray(audio_samples).copy()
    if len(arr) == 0:
        return arr

    thresh = _silence_threshold_for_array(arr)
    active = np.where(np.abs(arr) > thresh)[0]
    if len(active) == 0:
        max_keep = min(len(arr), max(1, int((pad_lead_sec + pad_tail_sec) * sr)))
        return np.zeros(max_keep, dtype=arr.dtype)

    lead_pad = max(0, int(pad_lead_sec * sr))
    tail_pad = max(0, int(pad_tail_sec * sr))
    start_idx = max(0, int(active[0]) - lead_pad)
    end_idx = min(len(arr), int(active[-1]) + 1 + tail_pad)

    trimmed = arr[start_idx:end_idx].copy()
    # Zero out the padding zones outside active speech so lead/tail have zero hiss
    inner_lead = int(active[0]) - start_idx
    inner_tail = end_idx - (int(active[-1]) + 1)
    if inner_lead > 0:
        trimmed[:inner_lead] = 0
    if inner_tail > 0:
        trimmed[len(trimmed) - inner_tail :] = 0
    return trimmed


def _sanitize_single_array(arr: np.ndarray, sr: int = 24000) -> np.ndarray:
    """Zero out single-sample spikes and low-amplitude hiss in silent intervals."""
    out = np.asarray(arr).copy()
    if len(out) == 0:
        return out

    thresh = _silence_threshold_for_array(out)
    # 1. Remove isolated 1-3 sample click spikes surrounded by silence
    if len(out) > 6:
        abs_v = np.abs(out.astype(np.float64))
        for i in range(2, len(out) - 2):
            if abs_v[i] > thresh * 2.0 and abs_v[i - 2] <= thresh and abs_v[i + 2] <= thresh:
                out[i - 1 : i + 2] = 0

    # 2. Zero out frames whose energy is below the silence floor
    win = max(1, int(0.015 * sr))
    n_wins = len(out) // win
    for w in range(n_wins):
        s = w * win
        e = s + win
        segment = out[s:e]
        if float(np.max(np.abs(segment))) <= thresh:
            out[s:e] = 0
    rem = n_wins * win
    if rem < len(out) and float(np.max(np.abs(out[rem:]))) <= thresh:
        out[rem:] = 0
    return out


def sanitize_inter_turn_glitches(
    turn_wavs: Union[Sequence[Union[Path, str, np.ndarray]], np.ndarray, Path, str],
    sr: int = 24000,
) -> Union[List[Union[Path, np.ndarray]], np.ndarray, Path]:
    """Ensure silence gaps and turn edges have exact 0.0 amplitude (zero inter-turn noise/hiss)."""
    if isinstance(turn_wavs, np.ndarray):
        return _sanitize_single_array(turn_wavs, sr=sr)

    if isinstance(turn_wavs, (Path, str)):
        p = Path(turn_wavs)
        pcm, file_sr = _read_wav_mono(p)
        cleaned = _sanitize_single_array(pcm, sr=file_sr)
        _write_wav_mono(p, cleaned, sr=file_sr)
        return p

    results: List[Union[Path, np.ndarray]] = []
    for item in turn_wavs:
        if isinstance(item, (Path, str)):
            p = Path(item)
            pcm, file_sr = _read_wav_mono(p)
            cleaned = _sanitize_single_array(pcm, sr=file_sr)
            _write_wav_mono(p, cleaned, sr=file_sr)
            results.append(p)
        else:
            arr = np.asarray(item)
            results.append(_sanitize_single_array(arr, sr=sr))
    return results


def _extract_phrases_and_speaker(turn: Any) -> Tuple[str, List[Tuple[str, str]]]:
    """Normalize a turn entry into (speaker, [(display_text, spoken_text), ...])."""
    if isinstance(turn, (list, tuple)):
        raw_spk = str(turn[0]).strip().upper()
        phrases_raw = turn[1] if len(turn) > 1 else []
        if isinstance(phrases_raw, str):
            phrases = [(phrases_raw, phrases_raw)]
        else:
            phrases = []
            for p in phrases_raw:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    phrases.append((str(p[0]), str(p[1])))
                elif isinstance(p, dict):
                    d = str(p.get("display_text") or p.get("display") or p.get("text") or "")
                    s = str(p.get("spoken_text") or p.get("spoken") or d)
                    phrases.append((d, s))
                else:
                    phrases.append((str(p), str(p)))
    elif isinstance(turn, dict):
        raw_spk = str(turn.get("speaker", "F")).strip().upper()
        if "phrases" in turn and isinstance(turn["phrases"], list):
            phrases = []
            for p in turn["phrases"]:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    phrases.append((str(p[0]), str(p[1])))
                elif isinstance(p, dict):
                    d = str(p.get("display_text") or p.get("display") or p.get("text") or "")
                    s = str(p.get("spoken_text") or p.get("spoken") or d)
                    phrases.append((d, s))
                else:
                    phrases.append((str(p), str(p)))
        else:
            d = str(turn.get("display_text") or turn.get("text") or "")
            s = str(turn.get("spoken_text") or d)
            phrases = [(d, s)]
    else:
        raw_spk = "F"
        phrases = [(str(turn), str(turn))]

    spk = "F" if (raw_spk.startswith("F") or "นุ้ย" in raw_spk or "NUI" in raw_spk) else "M"
    if not phrases:
        phrases = [("", "")]
    return spk, phrases


def assemble_clip_audio(
    turns: Sequence[Any],
    turn_audio_paths: Sequence[Union[Path, str, np.ndarray]],
    output_vo_path: Path | str,
    output_timings_path: Path | str,
    cross_speaker_gap_sec: float = 0.20,
    same_speaker_gap_sec: float = 0.12,
) -> Dict[str, Any]:
    """Assemble turn audio files/arrays into `vo.wav` and write `timings.json` with `cta_t`."""
    if len(turns) != len(turn_audio_paths):
        raise ValueError(
            f"Mismatch between turns count ({len(turns)}) and turn_audio_paths ({len(turn_audio_paths)})"
        )

    vo_path = Path(output_vo_path)
    timings_path = Path(output_timings_path)
    vo_path.parent.mkdir(parents=True, exist_ok=True)
    timings_path.parent.mkdir(parents=True, exist_ok=True)

    out_sr = 24000
    pieces: List[np.ndarray] = []
    turns_timings: List[List[Tuple[float, float]]] = []
    turn_spans: List[Dict[str, Any]] = []
    gap_spans: List[Tuple[int, int]] = []
    cursor_samples = 0

    parsed_turns = [_extract_phrases_and_speaker(t) for t in turns]

    for i, (spk, phrases) in enumerate(parsed_turns):
        audio_item = turn_audio_paths[i]
        if isinstance(audio_item, (Path, str)):
            pcm, file_sr = _read_wav_mono(audio_item)
            if i == 0 and file_sr > 0:
                out_sr = file_sr
        else:
            arr = np.asarray(audio_item)
            if np.issubdtype(arr.dtype, np.floating):
                pcm = (np.clip(arr, -1.0, 1.0) * 32767.0).astype(np.int16)
            else:
                pcm = arr.astype(np.int16)

        pcm_clean = _sanitize_single_array(pcm, sr=out_sr)
        if len(pcm_clean) == 0:
            pcm_clean = np.zeros(int(0.25 * out_sr), dtype=np.int16)

        turn_start_sec = round(cursor_samples / float(out_sr), 3)
        turn_dur_sec = len(pcm_clean) / float(out_sr)
        turn_end_sec = round((cursor_samples + len(pcm_clean)) / float(out_sr), 3)

        # Proportional phrase alignment within the turn
        weights = [max(1, len(s.strip()) or len(d.strip()) or 1) for d, s in phrases]
        total_w = float(sum(weights))
        phrase_pairs: List[Tuple[float, float]] = []
        p_cursor = turn_start_sec
        for pi, w in enumerate(weights):
            p_dur = turn_dur_sec * (w / total_w)
            p_start = round(p_cursor, 3)
            p_end = round(turn_end_sec if pi + 1 == len(weights) else p_cursor + p_dur, 3)
            if p_end <= p_start:
                p_end = round(p_start + 0.05, 3)
            phrase_pairs.append((p_start, p_end))
            p_cursor += p_dur

        turns_timings.append(phrase_pairs)
        turn_spans.append(
            {
                "turn_index": i,
                "speaker": spk,
                "start": turn_start_sec,
                "end": turn_end_sec,
            }
        )

        pieces.append(pcm_clean)
        cursor_samples += len(pcm_clean)

        if i + 1 < len(parsed_turns):
            next_spk = parsed_turns[i + 1][0]
            gap_sec = cross_speaker_gap_sec if next_spk != spk else same_speaker_gap_sec
        else:
            gap_sec = 0.12
        gap_samples = max(1, int(gap_sec * out_sr))
        gap_start = cursor_samples
        pieces.append(np.zeros(gap_samples, dtype=np.int16))
        cursor_samples += gap_samples
        gap_spans.append((gap_start, cursor_samples))

    full_pcm = np.concatenate(pieces) if pieces else np.zeros(int(0.5 * out_sr), dtype=np.int16)
    # Guarantee exact 0.0 in every inter-turn silence gap
    for gs, ge in gap_spans:
        full_pcm[gs:ge] = 0

    _write_wav_mono(vo_path, full_pcm, sr=out_sr)

    vo_dur = round(len(full_pcm) / float(out_sr), 3)
    if turns_timings and turns_timings[-1]:
        cta_t = round(turns_timings[-1][-1][0], 3)
    else:
        cta_t = round(max(0.0, vo_dur - 1.5), 3)

    timings_payload = {
        "vo": vo_dur,
        "cta_t": cta_t,
        "turns": turns_timings,
        "turn_spans": turn_spans,
        "gap_spans_samples": gap_spans,
        "sample_rate": out_sr,
    }
    timings_path.write_text(
        json.dumps(timings_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return timings_payload
