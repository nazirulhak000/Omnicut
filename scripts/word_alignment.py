"""Word-level timing for voiceovers that ship none (Gemini Flash TTS).

Edge-TTS streams a word boundary for every word it speaks, and the voice
stage stores those on each cue as ``word_timings`` -- a list of
``{"text", "start", "end"}`` dicts in absolute seconds on the voiceover
timeline (``scripts/voice_engine.py``).  Gemini Flash TTS returns one wav and
no timing at all, so everything downstream that keys off spoken words
(editorial pacing, SpecBar onset, word reveal) stayed off for the default
engine.

This module recovers the same contract after the fact: it transcribes the
final voiceover with faster-whisper (``word_timestamps=True``) and maps the
recognized words back onto the *known* script text.  The script -- not the
recognizer -- is the source of truth for what was said; whisper only
contributes *when*.  Thai has no spaces and whisper's word pieces never break
where pythainlp's do, so the mapping is done per character
(``difflib.SequenceMatcher``) and then folded back to pythainlp ``newmm``
tokens, the same tokenizer ``scripts/subtitle/translation_service.py`` uses.

Everything here is best effort.  Callers treat ``None`` as "no timings" and
keep their legacy behaviour; nothing in this module may fail a render.

GPU rule (AGENTS.md rule 21): the model loads on ``cuda``/``float16``
whenever ``ctranslate2.get_cuda_device_count() > 0`` and only falls back to
``cpu``/``int8`` (with a Thai warning) when no CUDA device is usable.  One
model instance is shared process-wide behind a lock so concurrent renders
(``render_jobs`` runs several workers) never load a second copy into VRAM.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# Bump when the alignment output changes shape or meaning: cached results
# from an older version are then ignored instead of reused.
ALIGNMENT_VERSION = 1

# The model every faster-whisper call site in this repo already uses
# (cloud_runner, tools/batch_produce_*). Override with OMNICUT_WORD_ALIGN_MODEL.
DEFAULT_MODEL_SIZE = "large-v3-turbo"
MODEL_ENV = "OMNICUT_WORD_ALIGN_MODEL"
# "0"/"off"/"false"/"no" turns alignment off entirely.
ENABLE_ENV = "OMNICUT_WORD_ALIGN"
# The model is loaded with local_files_only=True by default so a render never
# stalls on a ~1.6 GB download; set this to "1" to allow fetching it.
ALLOW_DOWNLOAD_ENV = "OMNICUT_WORD_ALIGN_ALLOW_DOWNLOAD"

# Below this share of script words matched, the transcript is too far from
# the script to trust (wrong audio, heavy hallucination) and nothing is
# attached.
MIN_COVERAGE = 0.6
# A token counts as matched when at least this share of its characters
# aligned to recognized characters.
TOKEN_MATCH_RATIO = 0.5

_THAI_BLOCK = ("฀", "๿")

_MODEL_LOCK = threading.Lock()
_TRANSCRIBE_LOCK = threading.Lock()
_MODELS: Dict[Tuple[str, str, str], Any] = {}
_DEVICE: Optional[Tuple[str, str]] = None
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
_MEMORY_CACHE_LIMIT = 32


def _log(message: str) -> None:
    print(message)


# ---------------------------------------------------------------------------
# Model handling
# ---------------------------------------------------------------------------

def alignment_enabled() -> bool:
    value = os.environ.get(ENABLE_ENV, "").strip().casefold()
    return value not in {"0", "off", "false", "no"}


def configured_model_size(model_size: Optional[str] = None) -> str:
    return (model_size or os.environ.get(MODEL_ENV) or DEFAULT_MODEL_SIZE).strip()


def resolve_device() -> Tuple[str, str]:
    """``("cuda", "float16")`` when a CUDA device exists, else ``("cpu", "int8")``."""
    global _DEVICE
    if _DEVICE is not None:
        return _DEVICE
    try:
        import ctranslate2  # type: ignore

        if ctranslate2.get_cuda_device_count() > 0:
            _DEVICE = ("cuda", "float16")
            return _DEVICE
    except Exception:
        pass
    _log("⚠️ [WordAlign] ไม่พบการ์ดจอ CUDA — ใช้ CPU (int8) จัดเวลาคำแทน ซึ่งช้ากว่ามาก")
    _DEVICE = ("cpu", "int8")
    return _DEVICE


def get_shared_model(
    model_size: Optional[str] = None,
    *,
    factory: Optional[Callable[..., Any]] = None,
) -> Any:
    """Return the process-wide faster-whisper model, loading it once.

    Thread-safe: concurrent callers block on one lock and all receive the
    same instance, so N parallel renders hold one copy in VRAM. ``factory``
    replaces ``faster_whisper.WhisperModel`` (tests).
    """
    size = configured_model_size(model_size)
    with _MODEL_LOCK:
        device, compute_type = resolve_device()
        key = (size, device, compute_type)
        cached = _MODELS.get(key)
        if cached is not None:
            return cached
        if factory is None:
            from faster_whisper import WhisperModel  # type: ignore

            factory = WhisperModel
        local_only = os.environ.get(ALLOW_DOWNLOAD_ENV, "").strip().casefold() not in {"1", "true", "yes"}
        try:
            model = factory(size, device=device, compute_type=compute_type, local_files_only=local_only)
        except Exception as load_err:
            if device != "cuda":
                raise
            _log(
                f"⚠️ [WordAlign] โหลดโมเดล {size} บน GPU ไม่สำเร็จ ({load_err}) — "
                "ลองใช้ CPU (int8) แทน"
            )
            model = factory(size, device="cpu", compute_type="int8", local_files_only=local_only)
        _MODELS[key] = model
        return model


def reset_shared_models() -> None:
    """Forget the loaded model, the device probe and the memory cache (tests)."""
    global _DEVICE
    with _MODEL_LOCK:
        _MODELS.clear()
        _DEVICE = None
        _MEMORY_CACHE.clear()


# ---------------------------------------------------------------------------
# Text handling
# ---------------------------------------------------------------------------

def tokenize_script(text: str) -> List[str]:
    """pythainlp ``newmm`` tokens of ``text`` with whitespace tokens dropped."""
    if not text:
        return []
    try:
        from pythainlp.tokenize import word_tokenize

        raw = word_tokenize(text, engine="newmm")
    except Exception:
        raw = text.split()
    return [tok.strip() for tok in raw if tok and tok.strip()]


def _norm_chars(text: str) -> List[str]:
    """Comparable characters of ``text``: lower-cased letters/digits and every
    Thai-block code point (Thai vowels/tone marks are combining marks, not
    ``isalnum``). Spaces, punctuation and thousands separators drop out, so
    "5,000 mAh" and "5000mAh" compare equal."""
    out: List[str] = []
    for ch in unicodedata.normalize("NFC", str(text or "")):
        if _THAI_BLOCK[0] <= ch <= _THAI_BLOCK[1] or ch.isalnum():
            low = ch.lower()
            out.append(low if len(low) == 1 else ch)
    return out


def _is_content(token: str) -> bool:
    return bool(_norm_chars(token))


# ---------------------------------------------------------------------------
# Transcription + alignment
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecognizedWord:
    text: str
    start: float
    end: float


def transcribe_words(
    audio_path: Path,
    model: Any,
    *,
    initial_prompt: Optional[str] = None,
    language: str = "th",
) -> List[RecognizedWord]:
    """All words faster-whisper heard in ``audio_path``, with timestamps."""
    words: List[RecognizedWord] = []
    with _TRANSCRIBE_LOCK:
        segments, _info = model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
            initial_prompt=initial_prompt or None,
            condition_on_previous_text=False,
            beam_size=5,
        )
        # `segments` is a lazy generator: decode happens while iterating, so
        # it must be drained while the lock is still held.
        for seg in segments:
            for w in getattr(seg, "words", None) or []:
                text = str(getattr(w, "word", "") or "").strip()
                try:
                    start = float(getattr(w, "start"))
                    end = float(getattr(w, "end"))
                except (TypeError, ValueError):
                    continue
                if not text or end < start:
                    continue
                words.append(RecognizedWord(text=text, start=start, end=end))
    return words


@dataclass
class TokenAlignment:
    """Timing for each script token; ``timings[i]`` is ``None`` for tokens
    with no comparable characters (punctuation)."""

    timings: List[Optional[Dict[str, Any]]]
    matched: int
    total: int

    @property
    def coverage(self) -> float:
        return self.matched / self.total if self.total else 0.0


def align_tokens(
    tokens: Sequence[str],
    words: Sequence[RecognizedWord],
    duration: Optional[float] = None,
) -> TokenAlignment:
    """Map recognized ``words`` onto script ``tokens`` by character alignment.

    Each recognized word's span is spread evenly over its characters; a token
    takes the time of the first to the last of its characters that aligned.
    Tokens that did not align (or that would run backwards in time) are
    interpolated between their aligned neighbours by character count, so the
    returned stream covers every content token in order -- which is what the
    character-walking consumers (``SubtitleEngine._clause_boundaries_from_word_timings``,
    ``word_reveal._spans_from_real_timings``) need.
    """
    a_chars: List[str] = []
    a_token: List[int] = []
    token_chars: List[List[int]] = [[] for _ in tokens]
    for ti, tok in enumerate(tokens):
        for ch in _norm_chars(tok):
            token_chars[ti].append(len(a_chars))
            a_chars.append(ch)
            a_token.append(ti)

    b_chars: List[str] = []
    b_times: List[Tuple[float, float]] = []
    for w in words:
        chars = _norm_chars(w.text)
        if not chars:
            continue
        span = max(0.0, w.end - w.start)
        n = len(chars)
        for k, ch in enumerate(chars):
            b_chars.append(ch)
            b_times.append((w.start + span * k / n, w.start + span * (k + 1) / n))

    content = [ti for ti, idxs in enumerate(token_chars) if idxs]
    timings: List[Optional[Dict[str, Any]]] = [None] * len(tokens)
    if not content:
        return TokenAlignment(timings=timings, matched=0, total=0)

    matched_b: List[Optional[int]] = [None] * len(a_chars)
    if a_chars and b_chars:
        matcher = difflib.SequenceMatcher(None, "".join(a_chars), "".join(b_chars), autojunk=False)
        for block in matcher.get_matching_blocks():
            # A lone matching character is as likely chance as alignment in
            # Thai's small alphabet; real matches come in runs.
            if block.size < 2:
                continue
            for k in range(block.size):
                matched_b[block.a + k] = block.b + k

    anchors: Dict[int, Tuple[float, float]] = {}
    last_start = last_end = float("-inf")
    for ti in content:
        idxs = token_chars[ti]
        hits = [matched_b[i] for i in idxs if matched_b[i] is not None]
        if len(hits) / len(idxs) < TOKEN_MATCH_RATIO:
            continue
        lo, hi = min(hits), max(hits)
        if hi - lo > 3 * len(idxs) + 4:
            continue  # characters scattered across the transcript: not one word
        start, end = b_times[lo][0], b_times[hi][1]
        # Whisper's neighbouring words routinely overlap by tens of ms; a
        # start well before the previous token's start/end is an out-of-order
        # spurious match instead.
        if start < last_start - 0.05 or start < last_end - 0.25:
            continue
        # The token's own first/last characters may have been claimed by a
        # neighbour's matching run (greedy longest-match across a token
        # boundary); extend by the missing characters at the local rate.
        lead = next(k for k, i in enumerate(idxs) if matched_b[i] is not None)
        tail = next(k for k, i in enumerate(reversed(idxs)) if matched_b[i] is not None)
        if lead:
            start -= lead * (b_times[lo][1] - b_times[lo][0])
        if tail:
            end += tail * (b_times[hi][1] - b_times[hi][0])
        start = max(start, last_end, 0.0)
        end = max(end, start)
        anchors[ti] = (start, end)
        last_start = start
        last_end = max(last_end, end)

    # Seconds per character from the aligned tokens, used to size the
    # leading/trailing tokens that have only one neighbour.
    a_dur = sum(anchors[t][1] - anchors[t][0] for t in anchors)
    a_len = sum(len(token_chars[t]) for t in anchors)
    per_char = (a_dur / a_len) if a_len and a_dur > 0 else 0.08

    timeline_end = duration if duration is not None else (b_times[-1][1] if b_times else None)
    pos = 0
    while pos < len(content):
        ti = content[pos]
        if ti in anchors:
            start, end = anchors[ti]
            timings[ti] = {"text": tokens[ti], "start": start, "end": end, "_aligned": True}
            pos += 1
            continue
        run_end = pos
        while run_end < len(content) and content[run_end] not in anchors:
            run_end += 1
        run = content[pos:run_end]
        run_chars = sum(len(token_chars[t]) for t in run)
        prev_t = anchors[content[pos - 1]][1] if pos > 0 else None
        next_t = anchors[content[run_end]][0] if run_end < len(content) else None
        if prev_t is None and next_t is None:
            return TokenAlignment(timings=[None] * len(tokens), matched=0, total=len(content))
        if prev_t is None:
            prev_t = max(0.0, next_t - per_char * run_chars)
        if next_t is None:
            next_t = prev_t + per_char * run_chars
            if timeline_end is not None:
                next_t = max(prev_t, min(next_t, float(timeline_end)))
        span = max(0.0, next_t - prev_t)
        cursor = prev_t
        for t in run:
            share = span * len(token_chars[t]) / run_chars if run_chars else 0.0
            timings[t] = {"text": tokens[t], "start": cursor, "end": cursor + share, "_aligned": False}
            cursor += share
        pos = run_end

    return TokenAlignment(timings=timings, matched=len(anchors), total=len(content))


# ---------------------------------------------------------------------------
# Cue-level API
# ---------------------------------------------------------------------------

@dataclass
class CueAlignment:
    """Per-cue ``word_timings`` in the Edge-TTS schema plus match stats."""

    word_timings: List[List[Dict[str, Any]]]
    matched: int
    total: int
    model: str
    cached: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def coverage(self) -> float:
        return self.matched / self.total if self.total else 0.0


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_key(audio_hash: str, texts: Sequence[str], model_size: str) -> str:
    payload = json.dumps(
        {"v": ALIGNMENT_VERSION, "audio": audio_hash, "texts": list(texts), "model": model_size},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_cache(cache_path: Optional[Path], key: str) -> Optional[Dict[str, Any]]:
    hit = _MEMORY_CACHE.get(key)
    if hit is not None:
        return hit
    if cache_path is None:
        return None
    try:
        data = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and data.get("key") == key and isinstance(data.get("word_timings"), list):
        _remember(key, data)
        return data
    return None


def _remember(key: str, data: Dict[str, Any]) -> None:
    if len(_MEMORY_CACHE) >= _MEMORY_CACHE_LIMIT:
        _MEMORY_CACHE.pop(next(iter(_MEMORY_CACHE)))
    _MEMORY_CACHE[key] = data


def _write_cache(cache_path: Optional[Path], key: str, data: Dict[str, Any]) -> None:
    _remember(key, data)
    if cache_path is None:
        return
    try:
        path = Path(cache_path)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as cache_err:
        _log(f"⚠️ [WordAlign] บันทึกแคชเวลาคำไม่สำเร็จ ({cache_err}) — ทำงานต่อได้ตามปกติ")


def align_cues(
    audio_path: Path,
    cues: Sequence[Mapping[str, Any]],
    *,
    duration: Optional[float] = None,
    model_size: Optional[str] = None,
    model: Any = None,
    cache_path: Optional[Path] = None,
    min_coverage: float = MIN_COVERAGE,
) -> Optional[CueAlignment]:
    """Word timings for every cue's text, measured against ``audio_path``.

    ``cues`` must be the in-order cues of the whole voiceover (absolute
    times). Returns ``None`` -- with a Thai log line -- when alignment is
    disabled, faster-whisper/the model is unavailable, or too few script
    words could be matched. Never raises.
    """
    try:
        if not alignment_enabled():
            _log("[WordAlign] ปิดการจัดเวลาคำไว้ (OMNICUT_WORD_ALIGN) — ข้าม")
            return None
        audio_path = Path(audio_path)
        texts = [str(c.get("text") or "") for c in cues]
        cue_tokens = [tokenize_script(t) for t in texts]
        if not any(cue_tokens):
            return None

        size = configured_model_size(model_size)
        key = _cache_key(_file_sha256(audio_path), texts, size)
        cached = _read_cache(cache_path, key)
        if cached is not None:
            return CueAlignment(
                word_timings=cached["word_timings"],
                matched=int(cached.get("matched") or 0),
                total=int(cached.get("total") or 0),
                model=size,
                cached=True,
            )

        if model is None:
            model = get_shared_model(size)
        prompt = " ".join(t for t in texts if t.strip())
        words = transcribe_words(audio_path, model, initial_prompt=prompt)
        if not words:
            _log("⚠️ [WordAlign] faster-whisper ไม่ได้ยินคำใดเลยในเสียงพากย์ — ไม่ใส่เวลาคำ")
            return None

        flat: List[str] = []
        owner: List[int] = []
        for ci, toks in enumerate(cue_tokens):
            flat.extend(toks)
            owner.extend([ci] * len(toks))
        result = align_tokens(flat, words, duration=duration)
        if result.coverage < min_coverage:
            _log(
                f"⚠️ [WordAlign] จับคู่คำกับสคริปต์ได้แค่ {result.coverage:.0%} "
                f"(ต่ำกว่า {min_coverage:.0%}) — ไม่ใส่เวลาคำ ใช้จังหวะเดิม"
            )
            return None

        per_cue: List[List[Dict[str, Any]]] = [[] for _ in cues]
        for ti, timing in enumerate(result.timings):
            if timing is None:
                continue
            start = round(max(0.0, timing["start"]), 3)
            end = round(max(start, timing["end"]), 3)
            per_cue[owner[ti]].append({"text": timing["text"], "start": start, "end": end})

        alignment = CueAlignment(
            word_timings=per_cue, matched=result.matched, total=result.total, model=size
        )
        _write_cache(
            cache_path,
            key,
            {
                "key": key,
                "version": ALIGNMENT_VERSION,
                "model": size,
                "matched": result.matched,
                "total": result.total,
                "word_timings": per_cue,
            },
        )
        return alignment
    except ImportError as import_err:
        _log(f"⚠️ [WordAlign] ยังไม่ได้ติดตั้ง faster-whisper ({import_err}) — ข้ามการจัดเวลาคำ")
        return None
    except Exception as align_err:
        _log(f"⚠️ [WordAlign] จัดเวลาคำไม่สำเร็จ ({align_err}) — ทำงานต่อโดยไม่มีเวลาคำ")
        return None


def attach_word_timings(
    cues: Sequence[Mapping[str, Any]], alignment: CueAlignment
) -> List[Dict[str, Any]]:
    """Copies of ``cues`` with ``word_timings`` filled from ``alignment``.

    A cue that already carries non-empty ``word_timings`` keeps them.
    """
    out: List[Dict[str, Any]] = []
    for idx, cue in enumerate(cues):
        copied = dict(cue)
        if not copied.get("word_timings") and idx < len(alignment.word_timings):
            copied["word_timings"] = [dict(w) for w in alignment.word_timings[idx]]
        out.append(copied)
    return out


# ---------------------------------------------------------------------------
# Spec-number onset (SpecBar / spec callouts)
# ---------------------------------------------------------------------------

_DIGITS_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _digits_key(text: str) -> str:
    return re.sub(r"[^0-9.]", "", text.replace(",", ""))


def spec_onset_time(
    word_timings: Optional[Iterable[Mapping[str, Any]]],
    on_screen: str = "",
    *,
    start: Optional[float] = None,
    end: Optional[float] = None,
    min_visible: float = 0.4,
    max_early: float = 1.0,
) -> Optional[float]:
    """When the cue's spec number starts being spoken, or ``None``.

    Picks the spoken spec number (``SPEC_NUMBER_PATTERN`` -- the same regex
    caption highlighting uses) whose value matches the number in
    ``on_screen``; else the cue's first spec number; else the first token
    carrying ``on_screen``'s digits. ``None`` when there are no timings, no
    number, or the onset would leave the bar less than ``min_visible``
    seconds before ``end`` (or sits implausibly far before ``start``) -- the
    caller then keeps the sentence start.
    """
    timings = [
        w for w in (word_timings or [])
        if isinstance(w, Mapping) and isinstance(w.get("start"), (int, float))
    ]
    if not timings:
        return None
    from scripts.subtitle.translation_service import SPEC_NUMBER_PATTERN, find_spec_number

    target = ""
    shown = str(on_screen or "")
    spec_shown = find_spec_number(shown)
    first_digits = _DIGITS_RE.search(spec_shown or shown)
    if first_digits:
        target = _digits_key(first_digits.group(0))

    concat = ""
    owner: List[int] = []
    for i, w in enumerate(timings):
        text = str(w.get("text") or "")
        concat += text
        owner.extend([i] * len(text))

    chosen: Optional[int] = None
    first_match: Optional[int] = None
    for match in SPEC_NUMBER_PATTERN.finditer(concat):
        idx = owner[match.start()]
        if first_match is None:
            first_match = idx
        num = _DIGITS_RE.search(match.group(0))
        if target and num and _digits_key(num.group(0)) == target:
            chosen = idx
            break
    if chosen is None and target:
        chosen = next(
            (i for i, w in enumerate(timings) if target and target in _digits_key(str(w.get("text") or ""))),
            None,
        )
    if chosen is None:
        chosen = first_match
    if chosen is None:
        return None

    onset = float(timings[chosen]["start"])
    if onset < 0:
        return None
    if end is not None and onset > float(end) - min_visible:
        return None
    if start is not None and onset < float(start) - max_early:
        return None
    return round(onset, 3)


__all__ = [
    "ALIGNMENT_VERSION",
    "CueAlignment",
    "DEFAULT_MODEL_SIZE",
    "RecognizedWord",
    "TokenAlignment",
    "align_cues",
    "align_tokens",
    "alignment_enabled",
    "attach_word_timings",
    "configured_model_size",
    "get_shared_model",
    "reset_shared_models",
    "resolve_device",
    "spec_onset_time",
    "tokenize_script",
    "transcribe_words",
]
