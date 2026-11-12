"""Burn subtitles in a second pass, so a caption edit does not redo the rest.

A render spends most of its time on everything *under* the subtitles: clip
scaling, zoom keyframes, transitions, the hook scrim. When only the .ass file
changes (a caption fix, a hook text edit) all of that work is identical to the
previous render. This module splits the final encode in two:

  pass 1  everything except the last ``subtitles`` filter -> an intermediate
          file, stored under a key derived from the exact pass-1 command and
          the identity of every file it reads
  pass 2  intermediate + subtitles -> the finished clip

A later render whose pass-1 key matches an existing intermediate skips pass 1.

Measured on a 42.5 s / 18 clip timeline (RTX 4060, h264_nvenc cq 20):
single pass 17.4 s; pass 1 13.6 s; pass 2 5.1 s. The second encode costs
0.0018 SSIM (Y) against the single-pass result and a first render is about
1.9 s slower, so the renderer uses it only for re-renders of an existing
project (owner decision 2026-11-12); ``OMNICUT_SUBTITLE_SECOND_PASS=0`` turns
it off everywhere.

Nothing here runs ffmpeg; ``VideoEditor`` owns the encode.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

KEY_VERSION = 1

# The renderer always ends the video chain with one of these two shapes:
#   ...[x]subtitles='<ass>':fontsdir='<fonts>'[v_final]
#   ...[x]subtitles='<ass>':fontsdir='<fonts>'[v_subbed];[v_subbed]scale=...[v_final]
_LAST_SUBTITLES = re.compile(
    r"\[(?P<src>[A-Za-z0-9_]+)\](?P<filter>subtitles='(?P<ass>(?:[^'\\]|\\.)*)'(?::[^\[;]*)?)\[(?P<out>v_final|v_subbed)\]"
)


class SecondPassUnavailable(ValueError):
    """The graph does not have the shape this split understands."""


@dataclass(frozen=True)
class SplitGraph:
    pre_graph: str          # pass 1: ends in [v_pre_subs]
    burn_chain: str         # pass 2: [0:v]subtitles=...[v_final] (plus the draft downscale, if any)
    ass_path: str           # the .ass file pass 2 reads (ffmpeg-escaped, as written in the graph)


def split_graph(graph: str) -> SplitGraph:
    """Cut ``graph`` at its last ``subtitles`` filter.

    Audio chains can follow the video chain in the same graph, so the cut is
    made around the filter rather than at the end of the string.
    """
    matches = list(_LAST_SUBTITLES.finditer(graph))
    if not matches:
        raise SecondPassUnavailable("no final subtitles filter in the graph")
    m = matches[-1]
    tail = graph[m.end():]
    downscale = ""
    if m.group("out") == "v_subbed":
        scale = re.match(r";\[v_subbed\](scale=[^\[;]*)\[v_final\]", tail)
        if not scale:
            raise SecondPassUnavailable("draft downscale after the subtitles filter not recognised")
        downscale = f",{scale.group(1)}"
        tail = tail[scale.end():]
    if "[v_final]" in tail or "[v_subbed]" in tail:
        raise SecondPassUnavailable("the video chain continues after the subtitles filter")
    pre = f"{graph[:m.start()]}[{m.group('src')}]null[v_pre_subs]{tail}"
    burn = f"[0:v]{m.group('filter')}{downscale}[v_final]"
    return SplitGraph(pre_graph=pre, burn_chain=burn, ass_path=m.group("ass"))


def _file_identity(path: Path) -> dict:
    try:
        stat = path.stat()
    except OSError:
        return {"path": str(path), "missing": True}
    return {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _content_identity(path: Path) -> dict:
    try:
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    except OSError:
        return {"path": str(path), "missing": True}


def intermediate_key(
    pass1_args: Sequence[str],
    media_inputs: Iterable[Path],
    small_dependencies: Iterable[Path] = (),
) -> str:
    """Key of the pass-1 result.

    ``pass1_args``          every ffmpeg argument of pass 1 except the output path
    ``media_inputs``        files given with ``-i`` (size + mtime; they can be gigabytes)
    ``small_dependencies``  files the graph itself names -- LUTs, the hook .ass burned
                            under an isolated subject -- hashed by content, because
                            they are rewritten in place under the same name
    """
    payload = {
        "version": KEY_VERSION,
        "args": list(pass1_args),
        "media": [_file_identity(Path(p)) for p in media_inputs],
        "small": [_content_identity(Path(p)) for p in small_dependencies],
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def intermediate_path(cache_dir: Path, key: str) -> Path:
    return Path(cache_dir) / f"pre_subtitles_{key}.mp4"


def find_reusable(cache_dir: Path, key: str, min_bytes: int = 1024) -> Optional[Path]:
    """The intermediate for ``key`` if it is on disk and not obviously truncated.

    Pass 1 writes to ``<name>.partial.mp4`` and renames on success, so a file at
    the final name is a completed encode.
    """
    path = intermediate_path(cache_dir, key)
    try:
        return path if path.is_file() and path.stat().st_size >= min_bytes else None
    except OSError:
        return None


def build_pass1_cmd(head: Sequence[str], inputs: Sequence[str], pre_graph: str, audio_map: Optional[str],
                    video_codec: Sequence[str], audio_codec: Sequence[str], fps: str, duration: str,
                    out_file: Path) -> List[str]:
    cmd = list(head) + list(inputs) + ["-filter_complex", pre_graph, "-map", "[v_pre_subs]"]
    if audio_map:
        cmd += ["-map", audio_map]
    cmd += list(video_codec) + ["-r", fps] + list(audio_codec) + ["-pix_fmt", "yuv420p", "-t", duration, str(out_file)]
    return cmd


def build_pass2_cmd(head: Sequence[str], intermediate: Path, burn_chain: str, has_audio: bool,
                    video_codec: Sequence[str], fps: str, out_file: Path) -> List[str]:
    cmd = list(head) + ["-i", str(intermediate), "-filter_complex", burn_chain, "-map", "[v_final]"]
    if has_audio:
        # The mix was encoded in pass 1; copying it keeps the audio bit-identical
        # across subtitle-only renders.
        cmd += ["-map", "0:a", "-c:a", "copy"]
    cmd += list(video_codec) + ["-r", fps, "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_file)]
    return cmd


def prune(cache_dir: Path, keep: int = 1) -> List[Path]:
    """Intermediates beyond the newest ``keep``, oldest first. The caller decides whether to delete."""
    # A ".partial.mp4" is a pass 1 another render is still writing.
    finished = [p for p in Path(cache_dir).glob("pre_subtitles_*.mp4") if not p.name.endswith(".partial.mp4")]
    files = sorted(finished, key=lambda p: p.stat().st_mtime, reverse=True)
    return list(reversed(files[keep:]))


# ---------------------------------------------------------------------------
# Renderer-facing helpers
# ---------------------------------------------------------------------------

ENV_SWITCH = "OMNICUT_SUBTITLE_SECOND_PASS"
# About 59 MB each for a 43 s clip; the newest few cover the projects someone
# is actively re-rendering.
KEEP_INTERMEDIATES = 6
# Inputs up to this size are identified by content. The mixed audio and sticker
# images are rewritten in place under the same name, so size + mtime would
# either miss a real change or (more often) invalidate on an identical rewrite.
CONTENT_HASH_MAX_BYTES = 64 * 1024 * 1024


def switched_off() -> bool:
    """True when the environment turns the second pass off for every render."""
    return os.environ.get(ENV_SWITCH, "").strip().lower() in ("0", "false", "off", "no")


def cache_dir() -> Path:
    from scripts.config import BASE_DIR

    return BASE_DIR / ".tmp" / "render_cache" / "second_pass"


def input_files(cmd_inputs: Sequence[str]) -> List[Path]:
    """Every path given with ``-i``. Raises when one is not a plain file.

    An image-sequence pattern or a lavfi source has no single file to
    fingerprint, so a render that uses one stays on the single pass.
    """
    files = []
    for i, arg in enumerate(cmd_inputs[:-1]):
        if arg != "-i":
            continue
        path = Path(cmd_inputs[i + 1])
        if not path.is_file():
            raise SecondPassUnavailable(f"input is not a plain file: {path.name}")
        files.append(path)
    return files


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _input_identity(path: Path, by_content: bool) -> dict:
    try:
        stat = path.stat()
        if by_content and stat.st_size <= CONTENT_HASH_MAX_BYTES:
            return {"path": str(path), "sha256": _stream_sha256(path)}
        return {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    except OSError:
        return {"path": str(path), "missing": True}


def render_key(pass1_args: Sequence[str], cmd_inputs: Sequence[str], footage_count: int,
               dependencies: Iterable[Path] = ()) -> str:
    """Key of the pass-1 result for a renderer command.

    ``footage_count``  how many of the leading ``-i`` files are source footage
                       (never rewritten, can be large: size + mtime); every
                       later input and each of ``dependencies`` (the LUT) is
                       identified by content.
    """
    files = input_files(cmd_inputs)
    payload = {
        "version": KEY_VERSION,
        "args": list(pass1_args),
        "inputs": [_input_identity(p, by_content=i >= footage_count) for i, p in enumerate(files)],
        "deps": [_input_identity(Path(p), by_content=True) for p in dependencies],
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def mark_used(path: Path) -> None:
    """Move a reused intermediate to the front of the keep-newest order."""
    try:
        os.utime(path, None)
    except OSError:
        pass


def drop_old_intermediates(directory: Path, keep: int = KEEP_INTERMEDIATES) -> List[Path]:
    """Delete this module's own intermediates beyond the newest ``keep``."""
    dropped = []
    try:
        stale = prune(directory, keep=keep)
    except OSError:
        return dropped
    for path in stale:
        try:
            path.unlink()
            dropped.append(path)
        except OSError:
            pass  # in use by another render; the next call retries
    return dropped
