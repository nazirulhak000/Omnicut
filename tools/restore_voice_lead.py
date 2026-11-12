"""Put back the lead-in silence that an in-place cleanup removed from voiceover files.

On 2026-11-08 every existing voiceover.wav had a noise burst trimmed off its
tail in place. The same pass also removed leading silence, so the speech in
those files now starts 0.10-0.27 s earlier than in the mix and the subtitles
that were made from the original file. A normal re-render reuses the old mix
and stays in sync, but the first audio edit (BGM, SFX, levels) re-mixes from
the trimmed file and the voice then runs ahead of the captions.

For each project whose mix is older than its voice file this tool measures
where the voice sits inside that mix, prepends exactly that much silence to
the voice file, checks that the two now line up, and re-stamps the project's
fingerprints. The cleaned tail is kept. The file it replaces is first copied
to 06_Archive/voice_lead_backup/<project>/.

Usage (repository root, project .venv):
    python tools/restore_voice_lead.py            # measure and list only
    python tools/restore_voice_lead.py --apply
    python tools/restore_voice_lead.py --apply --project NAME
"""
from __future__ import annotations

import argparse
import shutil
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import pipeline_context, render_jobs  # noqa: E402
from scripts.config import ARCHIVE_DIR  # noqa: E402
from scripts.project_manifest import ProjectManifest  # noqa: E402

COMPARE_RATE = 8000           # Hz the comparison runs at
WINDOW_S = 8.0                # how much of the start is compared
MAX_SHIFT_S = 0.5             # a larger offset is not this cleanup's doing
ALIGNED_S = 0.004             # within this the files count as lined up
MIN_LEAD_S = 0.010            # below this there is nothing worth restoring
MIN_MATCH = 0.50              # waveform correlation below this is not the same recording
BACKUP_FOLDER = "voice_lead_backup"


def _waveform(path: Path) -> Optional[np.ndarray]:
    """The first WINDOW_S seconds (plus search room), mono, at COMPARE_RATE."""
    try:
        with wave.open(str(path), "rb") as source:
            if source.getsampwidth() != 2:
                return None
            rate, channels = source.getframerate(), source.getnchannels()
            frames = source.readframes(int(rate * (WINDOW_S + MAX_SHIFT_S + 1.0)))
    except (wave.Error, OSError, EOFError):
        return None
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32)
    if channels > 1:
        samples = samples[: len(samples) // channels * channels].reshape(-1, channels).mean(axis=1)
    if not len(samples):
        return None
    index = (np.arange(int(len(samples) * COMPARE_RATE / rate)) * rate / COMPARE_RATE).astype(np.int64)
    return samples[index]


def match_voice_in_mix(voice: Path, mix: Path) -> Optional[Tuple[float, float]]:
    """(offset seconds, match -1..1): where the voice sits in ``mix`` and how well it matches there.

    The signed waveforms are compared, not their loudness: the same recording
    lines up at exactly one offset, while music, effects or another take of
    the same script stay near zero.
    """
    a, b = _waveform(voice), _waveform(mix)
    if a is None or b is None:
        return None
    n = min(int(WINDOW_S * COMPARE_RATE), len(a), len(b))
    limit = int(MAX_SHIFT_S * COMPARE_RATE)
    if n <= limit * 4:
        return None
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    core = a[limit:n - limit]                      # the same voice samples for every shift
    core_norm = float(np.linalg.norm(core))
    if core_norm <= 0:
        return None
    best_shift, best_match = 0, -1.0
    for shift in range(-limit, limit + 1):
        other = b[limit + shift:n - limit + shift]
        norm = core_norm * float(np.linalg.norm(other))
        match = float(np.dot(core, other)) / norm if norm > 0 else -1.0
        if match > best_match:
            best_shift, best_match = shift, match
    return best_shift / COMPARE_RATE, best_match


def voice_offset_in_mix(voice: Path, mix: Path) -> Optional[float]:
    """Seconds by which the voice sits later in ``mix`` than in ``voice`` (negative: earlier).

    None when the mix does not clearly contain this voice inside the search
    range -- a different take, or an offset this tool was not written for.
    """
    found = match_voice_in_mix(voice, mix)
    if found is None:
        return None
    offset, match = found
    if match < MIN_MATCH or abs(offset) >= MAX_SHIFT_S - 0.002:
        return None
    return offset


def _paths(manifest: Dict[str, Any]) -> Tuple[Optional[Path], Optional[Path]]:
    voice = pipeline_context._manifest_artifact_path(manifest, "voice_audio")
    mix = pipeline_context._manifest_artifact_path(manifest, "mixed_audio")
    return voice, mix


def measure(manifest: Dict[str, Any]) -> Tuple[str, Optional[float]]:
    """('restore' | 'aligned' | 'not_affected' | 'unclear', offset seconds)."""
    voice, mix = _paths(manifest)
    try:
        if not (voice and mix and voice.is_file() and mix.is_file()):
            return "not_affected", None
        if mix.stat().st_mtime + 1.0 >= voice.stat().st_mtime:
            return "not_affected", None       # the mix was made from this voice file
    except OSError:
        return "not_affected", None
    if (manifest.get("voice_edit") or {}).get("cuts"):
        return "unclear", None                # a cut voice is not at the mix's timing by design
    offset = voice_offset_in_mix(voice, mix)
    if offset is None:
        return "unclear", None
    if abs(offset) <= ALIGNED_S:
        return "aligned", offset
    if offset < MIN_LEAD_S:
        return "unclear", offset              # voice later than the mix: not a trimmed lead
    return "restore", offset


def prepend_silence(voice: Path, seconds: float) -> None:
    with wave.open(str(voice), "rb") as source:
        params = source.getparams()
        audio = source.readframes(source.getnframes())
    lead = b"\x00" * (int(round(seconds * params.framerate)) * params.nchannels * params.sampwidth)
    tmp = voice.with_name(voice.name + ".lead.tmp")
    try:
        with wave.open(str(tmp), "wb") as target:
            target.setparams(params)
            target.writeframes(lead + audio)
        tmp.replace(voice)
    finally:
        if tmp.exists():
            tmp.unlink()


def restore(project_name: str) -> Tuple[bool, str]:
    manifest = ProjectManifest.load(project_name)
    if not manifest:
        return False, "ไม่พบ manifest"
    status, offset = measure(manifest)
    if status != "restore":
        return False, status
    voice, mix = _paths(manifest)
    backup = ARCHIVE_DIR / BACKUP_FOLDER / project_name / voice.name
    if backup.exists():
        return False, f"มีไฟล์สำรองอยู่แล้ว ({backup}) — ไม่เขียนทับ"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(voice, backup)
    prepend_silence(voice, offset)
    after = voice_offset_in_mix(voice, mix)
    if after is None or abs(after) > ALIGNED_S:
        shutil.copy2(backup, voice)           # put the file back exactly as it was
        return False, f"เติมแล้วยังไม่ตรง ({after}) — คืนไฟล์เดิม"
    strict = (manifest.get("incremental_render") or {}).get("schema_version") == \
        pipeline_context.INCREMENTAL_RENDER_SCHEMA_VERSION
    if strict:
        # The voice file changed, so the stored fingerprints must follow it or
        # the next render would synthesise a new take.
        render_jobs.finalize_incremental_render(project_name)
    return True, f"เติม {offset:.3f} วิ (วัดซ้ำ {after:+.3f})"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="change the voice files (default: measure only)")
    parser.add_argument("--project", help="one project name instead of all")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    names = [args.project] if args.project else sorted(p["project_name"] for p in ProjectManifest.list_projects())
    counts: Dict[str, int] = {}
    todo: List[str] = []
    for name in names:
        manifest = ProjectManifest.load(name)
        status, offset = measure(manifest) if manifest else ("not_affected", None)
        counts[status] = counts.get(status, 0) + 1
        if status == "restore":
            todo.append(name)
            print(f"  ต้องเติม {offset:.3f} วิ: {name}")
        elif status == "unclear":
            print(f"  วัดไม่ชัด ข้าม ({offset}): {name}")
    print("สรุป:", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if not args.apply:
        print("ยังไม่ได้แก้ไฟล์ — เพิ่ม --apply เพื่อเติมช่วงเงียบ")
        return 0

    failed = 0
    for name in todo:
        try:
            ok, note = restore(name)
        except Exception as exc:  # noqa: BLE001 - one bad project must not stop the rest
            ok, note = False, repr(exc)
        failed += 0 if ok else 1
        print(f"  {'✔' if ok else '❌'} {name}: {note}")
    print(f"เติมแล้ว {len(todo) - failed} โปรเจกต์, ไม่สำเร็จ {failed} · ไฟล์เดิมอยู่ที่ {ARCHIVE_DIR / BACKUP_FOLDER}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
