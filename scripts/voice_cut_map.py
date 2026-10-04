"""แผนที่เวลาของ "ตัดช่วงเสียงพากย์" (voice_edit) — ฝั่ง Python

ไฟล์เสียงพากย์ไม่ถูกแตะเลย (ผู้ใช้เลือกแบบผสม D1=B ของ
`_Docs/Plans/PLAN_RIPPLE_ANCHOR_20261004.md`) manifest เก็บรายการช่วงที่ตัด
`voice_edit.cuts` เป็นเวลาของไฟล์เสียงต้นฉบับ (`u`, วินาที) แล้วตอนมิกซ์ค่อยตัด
ด้วย ffmpeg `atrim` (ดู `SFXManager.mix_audio_track(voice_cuts=...)`)

เวลา 2 แบบ:
    u = เวลาในไฟล์เสียงต้นฉบับ (source time)
    t = เวลาโปรแกรม = เวลาบนไทม์ไลน์หลังตัด (program time)

ฟังก์ชันหลัก 6 ตัวมีคู่ JS ชื่อเดียวกัน (camelCase) ใน
`frontend/src/lib/voiceCutMap.js` และต้องให้ผลเท่ากันทุกค่า (เทส parity เทียบ
สองฝั่ง) ดังนั้นลำดับการคำนวณทศนิยมในแต่ละฟังก์ชันถูกกำหนดตายตัวตามเอกสาร:

    normalize_cuts     <-> normalizeCuts(cuts, sourceDuration)
    keep_ranges        <-> keepRanges(cuts, sourceDuration)
    source_to_program  <-> sourceToProgram(u, cuts)
    program_to_source  <-> programToSource(t, cuts)
    effective_duration <-> effectiveDuration(cuts, sourceDuration)
    shift_time         <-> shiftTime(t, t0, t1)

กติกาการปัดเศษ: `floor(x * 30 + 0.5) / 30` (ปัดครึ่งขึ้น) เหมือน JS
`sequenceFrameIndex` (`Math.floor(s * 30 + 0.5)`) และ `snapToFrame`
(`Math.round(s * 30) / 30`) ใน `frontend/src/lib/timelineMath.js` และ
`sequence_frame_index` ใน `scripts/video_editor.py` ขอบ 1/30 s ตรงกับ sample เต็ม
ทุก rate ที่ใช้ (24k=800, 44.1k=1470, 48k=1600) จึงตัดได้ตรง sample

ส่วนท้ายไฟล์ (`validate_voice_edit`, `resolve_voice_cuts`, ...) เป็นเรื่อง
manifest ฝั่ง backend เท่านั้น ไม่มีคู่ JS
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.config import BASE_DIR, FPS

SCHEMA_VERSION = 1

# ค่าเผื่อทศนิยมเวลาเปรียบเทียบขอบ (วินาที) เล็กกว่า 1 sample ของทุก rate มาก
EPS = 1e-9

# ช่วงที่ยังเหลือหลังตัดต้องไม่สั้นกว่านี้ (ตรงกับกติกา UI "total < 1 s → ปฏิเสธ")
MIN_REMAINING_SECONDS = 1.0

# กันขนาด manifest บวม (ตัดช่วงเงียบหลายสิบจุดยังพอ)
MAX_CUTS = 1000

MAX_REASON_CHARS = 40


# ---------------------------------------------------------------------------
# Pure time maps (JS mirror)
# ---------------------------------------------------------------------------

def snap_to_frame(seconds: Any, fps: int = FPS) -> float:
    """ปัดเวลา (วินาที) เป็นเฟรมที่ใกล้ที่สุด ปัดครึ่งขึ้น: `floor(x*fps + 0.5)/fps`

    ค่าที่ไม่ใช่ตัวเลขจำกัด (NaN/inf/None) ได้ 0.0 · ผลไม่มี -0.0

        >>> snap_to_frame(2.01)
        2.0
        >>> snap_to_frame(2.49)
        2.5
        >>> snap_to_frame(1 / 60)   # ครึ่งเฟรมพอดี ปัดขึ้น
        0.03333333333333333
    """
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return math.floor(value * fps + 0.5) / fps + 0.0


def _finite(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalize_cuts(cuts: Optional[Iterable[Mapping[str, Any]]], source_duration: Any) -> List[Dict[str, Any]]:
    """ทำรายการ cut ให้เป็นรูปมาตรฐาน: snap กริด 1/30 → clamp [0, source_duration]
    → ทิ้งช่วงยาว 0 → เรียงตาม start → รวมช่วงที่ซ้อน/ติดกัน

    สัญญา (JS `normalizeCuts(cuts, sourceDuration)` ต้องเหมือนกัน):
      - อินพุต: รายการ `{start, end, ...}` หน่วยวินาทีของไฟล์ต้นฉบับ (`id`/`reason`
        และคีย์อื่นเก็บไว้ตามเดิม) รายการที่ไม่ใช่ dict หรือ start/end ไม่ใช่ตัวเลข
        จำกัดจะถูกข้ามเงียบ ๆ (ตัวตรวจแบบเข้มคือ `validate_voice_edit`)
      - ลำดับการคำนวณ: `s = snap(start)`, `e = snap(end)`, `s = max(s, 0)`,
        `e = min(e, source_duration)` แล้วทิ้งถ้า `e - s < 1e-9`
        (ปลายที่ clamp เข้า `source_duration` อาจไม่อยู่บนกริดถ้าไฟล์ยาวไม่ลงตัวเฟรม)
      - เรียงด้วย `(start, end)` แล้วรวมเมื่อ `next.start <= cur.end + 1e-9`
        ได้ `end = max(cur.end, next.end)` คง `id`/`reason` ของช่วงแรก
      - `source_duration` ไม่ใช่ตัวเลข > 0 → คืน `[]`
      - ผลคืน dict ใหม่ (ไม่แก้ของเดิม) · idempotent

    ตัวอย่าง (source_duration = 6.0):
        >>> normalize_cuts([{"id": "a", "start": 2.01, "end": 2.49}], 6.0)
        [{'id': 'a', 'start': 2.0, 'end': 2.5}]
        >>> normalize_cuts([{"id": "a", "start": 1.0, "end": 2.0},
        ...                 {"id": "b", "start": 1.5, "end": 3.0}], 6.0)   # ซ้อน → รวม
        [{'id': 'a', 'start': 1.0, 'end': 3.0}]
        >>> normalize_cuts([{"id": "a", "start": 5.5, "end": 9.0}], 6.0)   # clamp ท้ายไฟล์
        [{'id': 'a', 'start': 5.5, 'end': 6.0}]
        >>> normalize_cuts([{"id": "a", "start": 1.0, "end": 1.01}], 6.0)  # snap แล้วยาว 0 → ทิ้ง
        []
    """
    duration = _finite(source_duration)
    if duration is None or duration <= 0:
        return []
    items: List[Dict[str, Any]] = []
    for cut in cuts or []:
        if not isinstance(cut, Mapping):
            continue
        start = _finite(cut.get("start"))
        end = _finite(cut.get("end"))
        if start is None or end is None:
            continue
        start = max(snap_to_frame(start), 0.0)
        end = min(snap_to_frame(end), duration)
        if end - start < EPS:
            continue
        item = dict(cut)
        item["start"] = start
        item["end"] = end
        items.append(item)
    items.sort(key=lambda item: (item["start"], item["end"]))
    merged: List[Dict[str, Any]] = []
    for item in items:
        if merged and item["start"] <= merged[-1]["end"] + EPS:
            merged[-1]["end"] = max(merged[-1]["end"], item["end"])
        else:
            merged.append(item)
    return merged


def keep_ranges(cuts: Optional[Iterable[Mapping[str, Any]]], source_duration: Any) -> List[Dict[str, float]]:
    """ช่วงของไฟล์ต้นฉบับที่ "เหลือ" หลังตัด พร้อมตำแหน่งบนเวลาโปรแกรม

    สัญญา (JS `keepRanges(cuts, sourceDuration)` คืน `{srcStart, srcEnd, progStart}`;
    ฝั่ง Python ใช้คีย์ snake_case `src_start`/`src_end`/`prog_start`):
      - เรียก `normalize_cuts` ภายในก่อนเสมอ (idempotent)
      - เดินจาก `cursor = 0`: ทุก cut ที่ `cut.start - cursor >= 1e-9` ได้ range
        `{src_start: cursor, src_end: cut.start, prog_start: prog}` แล้ว
        `prog += src_end - src_start` และ `cursor = cut.end`
      - ท้ายสุดถ้า `source_duration - cursor >= 1e-9` ได้ range สุดท้ายจนถึง
        `source_duration` (ไม่มี cut → หนึ่ง range `0 → source_duration`)
      - `prog_start` ของ range ถัดไป = `prog_start` ก่อนหน้า + ความยาวของมัน
        (บวกสะสมตามลำดับนี้เท่านั้น เพื่อให้ JS ได้ทศนิยมตรงกัน)
      - ตัดหมดทั้งไฟล์ → `[]` · `source_duration` ไม่ถูกต้อง → `[]`

    ตัวอย่าง (source_duration = 6.0, cut [2.0, 2.5]):
        >>> keep_ranges([{"start": 2.0, "end": 2.5}], 6.0)
        [{'src_start': 0.0, 'src_end': 2.0, 'prog_start': 0.0}, {'src_start': 2.5, 'src_end': 6.0, 'prog_start': 2.0}]
        >>> keep_ranges([], 6.0)
        [{'src_start': 0.0, 'src_end': 6.0, 'prog_start': 0.0}]
        >>> keep_ranges([{"start": 0.0, "end": 1.0}], 6.0)   # ตัดหัวไฟล์
        [{'src_start': 1.0, 'src_end': 6.0, 'prog_start': 0.0}]
    """
    duration = _finite(source_duration)
    if duration is None or duration <= 0:
        return []
    ranges: List[Dict[str, float]] = []
    cursor = 0.0
    prog = 0.0
    for cut in normalize_cuts(cuts, duration):
        if cut["start"] - cursor >= EPS:
            ranges.append({"src_start": cursor, "src_end": cut["start"], "prog_start": prog})
            prog += cut["start"] - cursor
        cursor = cut["end"]
    if duration - cursor >= EPS:
        ranges.append({"src_start": cursor, "src_end": duration, "prog_start": prog})
    return ranges


def effective_duration(cuts: Optional[Iterable[Mapping[str, Any]]], source_duration: Any) -> float:
    """ความยาวหลังตัด = `source_duration - Σ(end - start)` ของ cut ที่ normalize แล้ว

    สัญญา (JS `effectiveDuration(cuts, sourceDuration)`): บวก `end - start` สะสมตาม
    ลำดับของ `normalize_cuts` เริ่มจาก 0.0 แล้วลบจาก `source_duration` · ผลต่ำสุด 0.0
    · `source_duration` ไม่ถูกต้อง → 0.0 · ไม่ปัดเศษ (ไฟล์ยาว 31.2 s ไม่ใช่ผลคูณเฟรม)

        >>> effective_duration([{"start": 2.0, "end": 2.5}], 6.0)
        5.5
        >>> effective_duration([], 6.0)
        6.0
        >>> round(effective_duration([{"start": 2.0, "end": 2.5}, {"start": 4.0, "end": 4.2}], 6.0), 6)
        5.3
    """
    duration = _finite(source_duration)
    if duration is None or duration <= 0:
        return 0.0
    removed = 0.0
    for cut in normalize_cuts(cuts, duration):
        removed += cut["end"] - cut["start"]
    return max(0.0, duration - removed)


def source_to_program(u: Any, cuts: Optional[Sequence[Mapping[str, Any]]]) -> float:
    """เวลาไฟล์ต้นฉบับ `u` → เวลาโปรแกรม `t` (เวลาที่ผู้ใช้เห็นหลังตัด)

    สัญญา (JS `sourceToProgram(u, cuts)`): `cuts` ต้อง normalize แล้ว (เรียง ไม่ซ้อน —
    ฟังก์ชันนี้ไม่ตรวจซ้ำ) เดินตามลำดับ cut โดยมี `removed = 0.0`:
      - `u <= cut.start` → หยุดวน
      - `u >= cut.end`   → `removed += cut.end - cut.start`
      - อยู่ข้างใน (start < u < end) → ยุบไปขอบ: คืน `cut.start - removed` ทันที
      คืน `u - removed` เมื่อวนจบ/หยุด · ต่อเนื่องที่ขอบ cut และไม่ลดลงเมื่อ u เพิ่ม

    ตัวอย่าง (cut [2.0, 2.5]):
        >>> cuts = [{"start": 2.0, "end": 2.5}]
        >>> source_to_program(1.0, cuts)    # ก่อน cut ไม่เปลี่ยน
        1.0
        >>> source_to_program(2.25, cuts)   # ใน cut → ยุบไปรอยต่อ
        2.0
        >>> source_to_program(3.0, cuts)    # หลัง cut เลื่อนเข้ามา 0.5
        2.5
    """
    value = _finite(u)
    if value is None:
        return 0.0
    removed = 0.0
    for cut in cuts or []:
        start, end = cut["start"], cut["end"]
        if value <= start:
            break
        if value >= end:
            removed += end - start
        else:
            return start - removed
    return value - removed


def program_to_source(t: Any, cuts: Optional[Sequence[Mapping[str, Any]]]) -> float:
    """เวลาโปรแกรม `t` → เวลาไฟล์ต้นฉบับ `u` ที่ต้องอ่านเสียงตรงนั้น

    สัญญา (JS `programToSource(t, cuts)`): `cuts` ต้อง normalize แล้ว เดินตามลำดับ cut
    โดยมี `removed = 0.0`; ตำแหน่งของ cut บนเวลาโปรแกรม `pos = cut.start - removed`:
      - `t >= pos` → `removed += cut.end - cut.start` (t ที่ขอบพอดีให้ไปฝั่ง
        "หลังตัด" คือ u = cut.end)
      - `t <  pos` → หยุดวน
      คืน `t + removed`
    จึง `source_to_program(program_to_source(t)) == t` เสมอ ส่วนทางกลับ u ที่
    อยู่ใน cut หรือที่ขอบซ้ายของ cut จะกลับมาที่ขอบขวา (u = cut.end)

    ตัวอย่าง (cut [2.0, 2.5]):
        >>> cuts = [{"start": 2.0, "end": 2.5}]
        >>> program_to_source(1.0, cuts)
        1.0
        >>> program_to_source(2.0, cuts)    # ที่รอยต่อพอดี → ฝั่งหลังตัด
        2.5
        >>> program_to_source(2.5, cuts)
        3.0
    """
    value = _finite(t)
    if value is None:
        return 0.0
    removed = 0.0
    for cut in cuts or []:
        if value >= cut["start"] - removed:
            removed += cut["end"] - cut["start"]
        else:
            break
    return value + removed


def shift_time(t: Any, t0: Any, t1: Any) -> float:
    """เลื่อนเวลา `t` ตามการลบช่วง `[t0, t1]` ออกจากเวลาโปรแกรม (ลบครั้งเดียว)

    สัญญา (JS `shiftTime(t, t0, t1)`), `d = t1 - t0`:
        t <= t0        → t
        t0 < t < t1    → t0          (ยุบเข้ารอยต่อ)
        t >= t1        → t - d
    ไม่ snap กริด (ผู้เรียกส่ง t0/t1 ที่ snap แล้ว)

        >>> shift_time(1.0, 2.0, 2.5)
        1.0
        >>> shift_time(2.25, 2.0, 2.5)
        2.0
        >>> shift_time(3.0, 2.0, 2.5)
        2.5
    """
    value = _finite(t)
    start = _finite(t0)
    end = _finite(t1)
    if value is None:
        return 0.0
    if start is None or end is None:
        return value
    if value <= start:
        return value
    if value < end:
        return start
    return value - (end - start)


# ---------------------------------------------------------------------------
# Backend only: manifest `voice_edit` validation + safe use
# ---------------------------------------------------------------------------

class VoiceEditError(ValueError):
    """voice_edit ไม่ถูกต้อง — ข้อความเป็นภาษาไทยพร้อมส่งให้ผู้ใช้ (HTTP 422)"""


def _resolve(value: Any) -> Optional[Path]:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = BASE_DIR / path
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def voice_file_identity(path: Any) -> Optional[Dict[str, Any]]:
    """`{path, size, mtime_ns}` ของไฟล์เสียงปัจจุบัน (None ถ้าไม่มี/ไม่ใช่ไฟล์)"""
    resolved = _resolve(path)
    if resolved is None:
        return None
    try:
        stat = resolved.stat()
    except OSError:
        return None
    if not resolved.is_file():
        return None
    return {"path": str(resolved), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def source_matches(source: Any, current: Any) -> bool:
    """`voice_edit.source` ยังตรงกับไฟล์เสียงปัจจุบันไหม (path + size + mtime_ns)

    `current` เป็น dict ที่มี `path` และ `size` (หรือ `size_bytes`) และ `mtime_ns`
    — รับได้ทั้งผล `voice_file_identity` และ fingerprint ของ pipeline_context
    ขาดคีย์ใดคีย์หนึ่ง = ตรวจไม่ได้ = ไม่ตรง (ห้ามใช้ cut)
    """
    if not isinstance(source, Mapping) or not isinstance(current, Mapping):
        return False
    src_path = _resolve(source.get("path"))
    cur_path = _resolve(current.get("path"))
    if src_path is None or cur_path is None or src_path != cur_path:
        return False
    cur_size = current.get("size", current.get("size_bytes"))
    src_size = source.get("size")
    src_mtime = source.get("mtime_ns")
    cur_mtime = current.get("mtime_ns")
    if None in (src_size, src_mtime, cur_size, cur_mtime):
        return False
    return src_size == cur_size and src_mtime == cur_mtime


def resolve_voice_cuts(
    voice_edit: Any,
    current_voice: Any,
) -> Tuple[List[Dict[str, Any]], Optional[str], float]:
    """ตัดสินว่า manifest `voice_edit` ใช้ได้กับไฟล์เสียงปัจจุบันหรือไม่

    คืน `(cuts, problem, source_duration)`:
      - ไม่มี voice_edit / ไม่มี cut → `([], None, 0.0)`
      - รูปแบบเสีย (ไม่ผ่าน `validate_voice_edit`) → `([], "invalid", 0.0)`
      - fingerprint ของ `source` ไม่ตรงไฟล์ปัจจุบัน (พากย์ใหม่/ไฟล์ถูกแทน) →
        `([], "stale", duration)` — **ห้ามใช้ cut เด็ดขาด**
      - ใช้ได้ → `(normalized_cuts, None, source.duration)`
    `current_voice` ดูที่ `source_matches`
    """
    if not voice_edit:
        return [], None, 0.0
    try:
        edit = validate_voice_edit(voice_edit, stamp=None)
    except VoiceEditError:
        return [], "invalid", 0.0
    if not edit or not edit["cuts"]:
        return [], None, 0.0
    duration = float(edit["source"]["duration"])
    if not source_matches(edit["source"], current_voice):
        return [], "stale", duration
    return edit["cuts"], None, duration


def validate_voice_edit(raw: Any, *, stamp: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """ตรวจ + ทำให้เป็นมาตรฐาน `voice_edit` ที่ client ส่งมา (ผิด → `VoiceEditError`)

    รูปแบบ (plan §3.1):
        {"schema_version": 1,
         "source": {"path": str, "size": int, "mtime_ns": int, "duration": float},
         "cuts": [{"id": str, "start": float, "end": float, "reason": str?}, ...]}
    กติกา:
      - `raw` เป็น None หรือไม่มี cut → คืน None (ล้าง voice_edit)
      - `source.duration` ต้องเป็นตัวเลข > 0; `path/size/mtime_ns` ที่ client ไม่ส่ง
        ให้ server เติมจาก `stamp` (ผล `voice_file_identity` ของไฟล์เสียงปัจจุบัน) —
        ที่ส่งมาแล้วไม่ถูกแก้ (ไม่ตรงไฟล์ = stale ตอนใช้)
      - `cuts` ≤ 1000 รายการ แต่ละอัน: `id` เป็น string ไม่ว่างและไม่ซ้ำ, `start`/`end`
        เป็นตัวเลข, `0 <= start < end <= source.duration` (เผื่อ 1e-6), ยาว ≥ 1 เฟรม
        (ยกเว้นช่วงท้ายไฟล์ที่ติดขอบ), **เรียงตาม start และไม่ซ้อนกัน** (ตามที่ client ส่ง)
      - จากนั้น snap กริด 1/30 และรวมช่วงที่ติดกันหลัง snap ด้วย `normalize_cuts`
      - ช่วงที่เหลือหลังตัดต้อง ≥ 1.0 s
      - คีย์อื่นในแต่ละ cut (เช่น `removed`) ส่งผ่านตามเดิม
    """
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise VoiceEditError("voice_edit ต้องเป็นอ็อบเจกต์ที่มี source และ cuts")
    version = raw.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise VoiceEditError(f"voice_edit.schema_version ต้องเป็น {SCHEMA_VERSION} (ได้ {version!r})")

    raw_cuts = raw.get("cuts")
    if raw_cuts is None:
        raw_cuts = []
    if not isinstance(raw_cuts, list):
        raise VoiceEditError("voice_edit.cuts ต้องเป็นรายการ")
    if not raw_cuts:
        return None
    if len(raw_cuts) > MAX_CUTS:
        raise VoiceEditError(f"voice_edit.cuts มากเกินไป (สูงสุด {MAX_CUTS} ช่วง)")

    source = raw.get("source")
    if not isinstance(source, Mapping):
        raise VoiceEditError("voice_edit.source ต้องเป็นอ็อบเจกต์ (path, size, mtime_ns, duration)")
    duration = _finite(source.get("duration"))
    if duration is None or duration <= 0:
        raise VoiceEditError("voice_edit.source.duration ต้องเป็นตัวเลขมากกว่า 0")
    out_source: Dict[str, Any] = {
        "path": source.get("path"),
        "size": source.get("size"),
        "mtime_ns": source.get("mtime_ns"),
        "duration": duration,
    }
    if stamp:
        # Fill only what the client left out, and never mix fields of two
        # different files: a client path that is not the current file keeps its
        # own (then mismatching) fingerprint and is judged stale at use time.
        if out_source["path"] in (None, ""):
            out_source["path"] = stamp.get("path")
            for key in ("size", "mtime_ns"):
                if out_source[key] is None:
                    out_source[key] = stamp.get(key)
        elif _resolve(out_source["path"]) == _resolve(stamp.get("path")):
            for key in ("size", "mtime_ns"):
                if out_source[key] is None:
                    out_source[key] = stamp.get(key)
    for key, kind in (("size", int), ("mtime_ns", int)):
        value = out_source[key]
        if value is not None and (isinstance(value, bool) or not isinstance(value, kind)):
            raise VoiceEditError(f"voice_edit.source.{key} ต้องเป็นจำนวนเต็ม")
    if out_source["path"] is not None and not isinstance(out_source["path"], str):
        raise VoiceEditError("voice_edit.source.path ต้องเป็นข้อความ")

    seen_ids = set()
    prev_end = 0.0
    prev_start = -1.0
    frame = 1.0 / FPS
    cleaned: List[Dict[str, Any]] = []
    for index, cut in enumerate(raw_cuts, start=1):
        label = f"ช่วงตัดที่ {index}"
        if not isinstance(cut, Mapping):
            raise VoiceEditError(f"{label}: ต้องเป็นอ็อบเจกต์ {{id, start, end}}")
        cut_id = cut.get("id")
        if not isinstance(cut_id, str) or not cut_id.strip():
            raise VoiceEditError(f"{label}: id ต้องเป็นข้อความที่ไม่ว่าง")
        if cut_id in seen_ids:
            raise VoiceEditError(f"{label}: id '{cut_id}' ซ้ำกับช่วงอื่น")
        seen_ids.add(cut_id)
        start = _finite(cut.get("start"))
        end = _finite(cut.get("end"))
        if start is None or end is None:
            raise VoiceEditError(f"{label}: start และ end ต้องเป็นตัวเลข")
        if start < -1e-6 or end > duration + 1e-6:
            raise VoiceEditError(
                f"{label}: ต้องอยู่ในความยาวไฟล์เสียง 0 ถึง {duration:.3f} วินาที (ได้ {start:.3f}–{end:.3f})"
            )
        if end <= start:
            raise VoiceEditError(f"{label}: end ต้องมากกว่า start")
        at_tail = end >= duration - 1e-6
        if end - start < frame - 1e-9 and not at_tail:
            raise VoiceEditError(f"{label}: สั้นกว่า 1 เฟรม ({end - start:.4f} วินาที)")
        if start < prev_start - 1e-9:
            raise VoiceEditError(f"{label}: ต้องเรียงตามเวลา start จากน้อยไปมาก")
        if start < prev_end - 1e-9:
            raise VoiceEditError(f"{label}: ซ้อนกับช่วงก่อนหน้า ต้องรวมเป็นช่วงเดียว")
        prev_start, prev_end = start, end
        reason = cut.get("reason", "manual")
        if reason is None:
            reason = "manual"
        if not isinstance(reason, str) or len(reason) > MAX_REASON_CHARS:
            raise VoiceEditError(f"{label}: reason ต้องเป็นข้อความไม่เกิน {MAX_REASON_CHARS} ตัวอักษร")
        item = dict(cut)
        item["id"] = cut_id
        item["reason"] = reason
        cleaned.append(item)

    cuts = normalize_cuts(cleaned, duration)
    if not cuts:
        raise VoiceEditError("ช่วงที่ตัดสั้นกว่า 1 เฟรมหลังปัดเข้ากริด จึงไม่มีช่วงใดถูกตัด")
    remaining = effective_duration(cuts, duration)
    if remaining < MIN_REMAINING_SECONDS - 1e-9:
        raise VoiceEditError(
            f"ตัดแล้วเหลือเสียงพากย์ {remaining:.2f} วินาที สั้นกว่าขั้นต่ำ {MIN_REMAINING_SECONDS:.0f} วินาที"
        )
    return {"schema_version": SCHEMA_VERSION, "source": out_source, "cuts": cuts}
