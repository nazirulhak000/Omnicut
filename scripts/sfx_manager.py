"""
Audio & SFX Manager with Auto-Ducking and Timestamped Sound Effects Mixing
"""

import os
import sys
import math
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

logger = logging.getLogger("OmniCut.SFXManager")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import SFX_DIR, MUSIC_DIR, BGM_VOLUME, VOICE_VOLUME, SFX_VOLUME
from scripts.asset_registry import AssetRegistry
from scripts.it_angles import DEFAULT_BGM
from scripts.ffmpeg_graph import cleanup_graph_file, externalize_filter_graph


DEFAULT_DUCKING_THRESHOLD = 0.02
DEFAULT_DUCKING_RATIO = 12
DEFAULT_DUCKING_ATTACK_MS = 20
DEFAULT_DUCKING_RELEASE_MS = 300
# Preview/render source contract: the default FFmpeg envelope is
# attack=20:release=300; the graph below still resolves both values from the
# policy so an explicitly constructed policy remains authoritative.
DEFAULT_LOUDNESS_I = -14.0
DEFAULT_TRUE_PEAK = -1.0
DEFAULT_LOUDNESS_LRA = 8.0


@dataclass(frozen=True)
class AudioFinishingPolicy:
    """Validated, deterministic settings for the final audio mix.

    The public render request still exposes the existing gain and
    ``bgm_ducking`` arguments.  This value object keeps the filter graph's
    safety limits and loudness contract in one place without changing those
    request fields or the preview's AUDIO_MIX values.
    """

    voice_volume: float
    bgm_volume: float
    sfx_volume: float
    bgm_ducking: bool
    ducking_threshold: float = DEFAULT_DUCKING_THRESHOLD
    ducking_ratio: int = DEFAULT_DUCKING_RATIO
    ducking_attack_ms: int = DEFAULT_DUCKING_ATTACK_MS
    ducking_release_ms: int = DEFAULT_DUCKING_RELEASE_MS
    loudness_i: float = DEFAULT_LOUDNESS_I
    true_peak: float = DEFAULT_TRUE_PEAK
    loudness_lra: float = DEFAULT_LOUDNESS_LRA


def _clamp_gain(value: Any, default: float) -> float:
    """Return a finite FFmpeg volume gain in the safe [0, 1] range."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(numeric):
        return default
    return min(1.0, max(0.0, numeric))


def _valid_loudness_targets(loudness_i: Any, true_peak: Any, loudness_lra: Any) -> bool:
    """Validate the supported social-video loudness target envelope."""
    try:
        integrated = float(loudness_i)
        peak = float(true_peak)
        lra = float(loudness_lra)
    except (TypeError, ValueError):
        return False
    return (
        all(math.isfinite(v) for v in (integrated, peak, lra))
        and -30.0 <= integrated <= -5.0
        and -6.0 <= peak <= 0.0
        and 1.0 <= lra <= 20.0
    )


def build_audio_finishing_policy(
    *,
    bgm_vol: Any = BGM_VOLUME,
    voice_vol: Any = VOICE_VOLUME,
    sfx_vol: Any = SFX_VOLUME,
    bgm_ducking: Any = False,
    loudness_i: Any = DEFAULT_LOUDNESS_I,
    true_peak: Any = DEFAULT_TRUE_PEAK,
    loudness_lra: Any = DEFAULT_LOUDNESS_LRA,
) -> AudioFinishingPolicy:
    """Build a backward-compatible policy from render-facing values.

    Invalid loudness overrides fall back to the established render target.
    That is intentionally fail-safe for old manifests and keeps a malformed
    optional setting from preventing a render.
    """
    if not _valid_loudness_targets(loudness_i, true_peak, loudness_lra):
        loudness_i = DEFAULT_LOUDNESS_I
        true_peak = DEFAULT_TRUE_PEAK
        loudness_lra = DEFAULT_LOUDNESS_LRA

    return AudioFinishingPolicy(
        voice_volume=_clamp_gain(voice_vol, VOICE_VOLUME),
        bgm_volume=_clamp_gain(bgm_vol, BGM_VOLUME),
        sfx_volume=_clamp_gain(sfx_vol, SFX_VOLUME),
        bgm_ducking=bool(bgm_ducking),
        loudness_i=float(loudness_i),
        true_peak=float(true_peak),
        loudness_lra=float(loudness_lra),
    )


def loudness_filter(policy: AudioFinishingPolicy) -> str:
    """Return the single-pass FFmpeg loudness normalizer for ``policy``."""
    if not _valid_loudness_targets(policy.loudness_i, policy.true_peak, policy.loudness_lra):
        raise ValueError("Invalid audio loudness policy")
    # Keep the established default spelling (`-1.0`) in the generated graph;
    # this is semantically identical to `-1` but makes the compatibility
    # contract obvious in logs and source-level parity checks.
    peak_text = "-1.0" if policy.true_peak == DEFAULT_TRUE_PEAK else f"{policy.true_peak:g}"
    return (
        f"loudnorm=I={policy.loudness_i:g}:TP={peak_text}:"
        f"LRA={policy.loudness_lra:g}"
    )


def _event_start(event: Mapping[str, Any], default: Optional[float]) -> Optional[float]:
    value = event.get("start", default)
    try:
        start = float(value)
    except (TypeError, ValueError):
        return None
    return start if math.isfinite(start) else None


def is_sfx_event_eligible(
    event: Any,
    *,
    total_duration: Optional[float] = None,
    default_start: Optional[float] = None,
) -> bool:
    """Decide whether a cue/overlay may create an SFX input node.

    Existing cue shape remains supported: a truthy ``sfx`` plus a numeric
    ``start`` is enough.  Newer callers can explicitly suppress an event with
    ``sfx_enabled``/``sfx_event``/``enabled``.  Invalid or out-of-range timing
    is ignored instead of producing a broken ``adelay`` expression.
    """
    if not isinstance(event, Mapping):
        return False
    sfx_name = event.get("sfx")
    if not isinstance(sfx_name, str) or not sfx_name.strip():
        return False
    if any(event.get(flag) is False for flag in ("sfx_enabled", "sfx_event", "enabled")):
        return False

    start = _event_start(event, default_start)
    if start is None or start < 0.0:
        return False
    if total_duration is not None:
        try:
            duration = float(total_duration)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(duration) or duration < 0.0 or start > duration:
            return False

    if "end" in event and event.get("end") is not None:
        try:
            end = float(event["end"])
        except (TypeError, ValueError):
            return False
        if not math.isfinite(end) or end < start:
            return False
    return True


def sfx_event_start(event: Mapping[str, Any], default: float = 0.0) -> float:
    """Read a validated event start, retaining the legacy overlay default."""
    start = _event_start(event, default)
    return default if start is None else start


def bgm_tempo_ratio(cues: Optional[List[Mapping[str, Any]]]) -> float:
    """atempo ratio the mixer applies to the BGM bed (chars/sec of the cues
    vs. a 10 chars/sec baseline, clamped to +-8%). Shared so beat-sync can
    rescale beat times by exactly the ratio that is rendered; rounded to the
    3 decimals the ffmpeg filter string carries."""
    BASELINE_CHARS_PER_SEC = 10.0
    cues = cues or []
    total_chars = sum(len(str(c.get("text", ""))) for c in cues)
    cue_span = sum(
        max(0.01, float(c.get("end", 0.0)) - float(c.get("start", 0.0))) for c in cues
    )
    chars_per_sec = (total_chars / cue_span) if cue_span > 0 else BASELINE_CHARS_PER_SEC
    tempo_ratio = min(1.08, max(0.92, chars_per_sec / BASELINE_CHARS_PER_SEC))
    return round(tempo_ratio, 3)


# Each cut leaves a hard edge in the voice; an 8 ms ramp on both sides of every
# join removes the click without moving a single sample (afade keeps the length,
# unlike acrossfade which would shorten the track by the fade time).
VOICE_CUT_FADE_S = 0.008


def build_voice_cut_graph(
    keep: List[Dict[str, float]],
    source_duration: float,
    out_label: str = "voice_cut",
) -> str:
    """Filter-graph head that plays only the kept ranges of input 0, in order.

    `keep` comes from voice_cut_map.keep_ranges (source seconds). Every range is
    atrim'd + asetpts-rebased, ramped 8 ms at the edges a cut created (not at
    the file's own head/tail), then concat'ed. atrim+concat is sample exact;
    aselect lost audio frames and acrossfade shortens, so neither is used.
    The result ends with ';' and leaves the joined voice on `[out_label]`.
    """
    fade = VOICE_CUT_FADE_S
    parts: List[str] = []
    labels = [f"vk{i}" for i in range(len(keep))]
    if len(keep) > 1:
        sources = "".join(f"[vs{i}]" for i in range(len(keep)))
        parts.append(f"[0:a]asplit={len(keep)}{sources};")
    for i, rng in enumerate(keep):
        src = f"[vs{i}]" if len(keep) > 1 else "[0:a]"
        start, end = rng["src_start"], rng["src_end"]
        is_tail = end >= source_duration - 1e-9
        trim = f"start={start:.6f}" if is_tail else f"start={start:.6f}:end={end:.6f}"
        chain = f"atrim={trim},asetpts=PTS-STARTPTS"
        if start > 1e-9:
            chain += f",afade=t=in:st=0:d={fade}"
        if not is_tail:
            chain += f",afade=t=out:st={max(0.0, end - start - fade):.6f}:d={fade}"
        target = f"[{out_label}]" if len(keep) == 1 else f"[{labels[i]}]"
        parts.append(f"{src}{chain}{target};")
    if len(keep) > 1:
        joined = "".join(f"[{label}]" for label in labels)
        parts.append(f"{joined}concat=n={len(keep)}:v=0:a=1[{out_label}];")
    return "".join(parts)


class SFXManager:
    """Handles sound effects placement and background music mixing with auto-ducking."""

    last_mix_status: Dict[str, Any] = {"success": True, "fallback": False, "error": None}

    # Resolution went through AssetRegistry.resolve_sfx_path() instead of a
    # fixed 5-entry dict -- that dict only ever reached whoosh/pop/ding/cash/
    # boom even though 02_Assets/SFX/ has 28 files. resolve_sfx_path() accepts
    # both those legacy short names and the full sfx_* registry ids, so an
    # old project.json manifest that still says "sfx": "boom" keeps working.
    @classmethod
    def resolve(cls, name: str):
        return AssetRegistry.resolve_sfx_path(name)

    @classmethod
    def resolve_bgm_path(cls, bgm_name: Optional[str] = None) -> Optional[Path]:
        """
        Same fallback `mix_audio_track` uses internally (named file in
        MUSIC_DIR, else the first track found there) -- exposed so a caller
        that needs to know which BGM file will actually play (e.g. beat-sync
        in pipeline.py) doesn't have to duplicate the lookup or run a full
        mix just to find out.
        """
        name = bgm_name or DEFAULT_BGM
        path = MUSIC_DIR / name
        if path.exists():
            return path
        # A registry id ("bgm_brass_funk") carries no extension, and the BGM
        # picker sends the id, not the filename -- so every choice used to miss
        # the path check above and land on the alphabetically-first file
        # instead. Resolve ids the same way resolve_sfx_path() does before
        # falling back, or the track the user picked is never the track that
        # renders.
        for entry in AssetRegistry.bgm():
            if entry.get("id") == name:
                by_id = Path(entry["path"])
                if by_id.exists():
                    return by_id
        bgm_files = list(MUSIC_DIR.glob("*.wav")) + list(MUSIC_DIR.glob("*.mp3"))
        return bgm_files[0] if bgm_files else None

    @staticmethod
    def _probe_voice_duration(voice_path: Path) -> Optional[float]:
        """Real length of the voice file in seconds (None when ffprobe cannot tell)."""
        try:
            res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(voice_path)],
                capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=30,
            )
            value = float((res.stdout or "").strip())
        except Exception as probe_err:  # noqa: BLE001 - a failed probe only disables the cut
            logger.warning("Cannot probe voice duration for ripple cuts: %s", probe_err)
            return None
        return value if math.isfinite(value) and value > 0 else None

    @classmethod
    def _voice_cut_graph(
        cls,
        voice_path: Path,
        voice_cuts: Optional[List[Dict]],
        voice_source_duration: Optional[float],
    ) -> str:
        """Graph head that drops `voice_cuts` from the voice, or '' for "no cuts".

        '' also covers cuts that normalise away entirely, so the untouched
        path never depends on this helper's output.
        """
        if not voice_cuts:
            return ""
        from scripts.voice_cut_map import EPS, keep_ranges

        duration = voice_source_duration
        if not duration or duration <= 0:
            duration = cls._probe_voice_duration(voice_path)
        if not duration:
            logger.warning("Ripple cuts ignored: voice file duration is unknown (%s)", voice_path)
            return ""
        keep = keep_ranges(voice_cuts, duration)
        if not keep:
            logger.warning("Ripple cuts ignored: they would remove the whole voice track")
            return ""
        if len(keep) == 1 and keep[0]["src_start"] <= EPS and keep[0]["src_end"] >= duration - EPS:
            return ""  # nothing effectively cut
        return build_voice_cut_graph(keep, duration)

    @classmethod
    def mix_audio_track(
        cls,
        voice_audio_path: str,
        cues: List[Dict],
        total_duration: float,
        output_audio_path: str,
        # Channel's signature sound: highest-confidence CC0 pick from a
        # Freesound genre sweep for the IT/tech-review vertical (4.95/5 over
        # 20 ratings, 349 downloads, description literally says "designed
        # for hype flow" -- picked on that objective signal since nothing
        # here can actually play the audio to judge it by ear). Overridable
        # per-render via RenderRequest.bgm_name; this is only what a render
        # falls back to when nothing is specified.
        bgm_name: str = DEFAULT_BGM,
        bgm_vol: float = BGM_VOLUME,
        voice_vol: float = VOICE_VOLUME,
        sfx_vol: float = SFX_VOLUME,
        bgm_ducking: bool = False,
        overlays: Optional[List[Dict]] = None,
        # Ripple-cut ranges of the voice file in SOURCE seconds
        # ([{start, end}, ...], see scripts/voice_cut_map.py). The file itself is
        # never rewritten: the ranges are dropped here, at mix time. None/empty
        # keeps the graph exactly as it was. `voice_source_duration` is the real
        # length of the voice file (probed when omitted).
        voice_cuts: Optional[List[Dict]] = None,
        voice_source_duration: Optional[float] = None,
    ) -> str:
        """
        Mixes voiceover, SFX triggers at cue start times, and looped background music.

        The result of the ffmpeg run is left in ``last_mix_status`` (the return
        value stays the output path): ``fallback`` is True when the full mix
        failed and only the voice was kept, so the caller can tell the user the
        clip has no music/SFX instead of letting that pass silently.
        """
        # A previous call's failure must not read as this call's.
        cls.last_mix_status = {"success": True, "fallback": False, "error": None}
        out_path = Path(output_audio_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        voice_path = Path(voice_audio_path).resolve()
        bgm_path = cls.resolve_bgm_path(bgm_name)
        policy = build_audio_finishing_policy(
            bgm_vol=bgm_vol,
            voice_vol=voice_vol,
            sfx_vol=sfx_vol,
            bgm_ducking=bgm_ducking,
        )

        inputs = ["-i", str(voice_path)]
        filter_complex = []
        input_count = 1

        # 1. Voice filter (clear voice). With ducking on, the voice is split:
        # one copy goes into the mix, the other is only a sidechain key for the
        # music -- it is never heard twice.
        # With ripple cuts the head `[0:a]` becomes the trimmed+joined voice
        # (`cut_graph` + `[voice_cut]`); everything after it is unchanged, and
        # with no cuts both stay the empty string / `[0:a]` (graph byte-identical).
        cut_graph = cls._voice_cut_graph(voice_path, voice_cuts, voice_source_duration)
        voice_head = "[voice_cut]" if cut_graph else "[0:a]"
        if policy.bgm_ducking:
            filter_complex.append(
                f"{cut_graph}{voice_head}volume={policy.voice_volume},apad=pad_dur=1.0,asplit=2[voice_padded][voice_key];"
            )
        else:
            filter_complex.append(f"{cut_graph}{voice_head}volume={policy.voice_volume},apad=pad_dur=1.0[voice_padded];")

        # 2. Add Boom on 0.0s Hook
        boom_file = cls.resolve("boom")
        if boom_file and boom_file.exists():
            inputs.extend(["-i", str(boom_file)])
            filter_complex.append(f"[{input_count}:a]volume={policy.sfx_volume}[sfx_boom];")
            sfx_nodes = ["[sfx_boom]"]
            input_count += 1
        else:
            sfx_nodes = []

        # 3. Add SFX inputs per cue
        for idx, cue in enumerate(cues):
            if not is_sfx_event_eligible(cue, total_duration=total_duration):
                continue
            sfx_type = cue.get("sfx")
            sfx_file = cls.resolve(sfx_type) if sfx_type else None
            if sfx_file and sfx_file.exists():
                inputs.extend(["-i", str(sfx_file)])
                # J-Cut Transition SFX: เสียง Whoosh เริ่มก่อนรอยต่อภาพ 120ms เพื่อให้จุดพีคตรงกับรอยต่อพอดี
                sfx_name_low = str(sfx_file.name).lower()
                is_transition_sfx = any(w in sfx_name_low for w in ["whoosh", "swish", "swoosh", "transition"])
                pre_roll = 0.12 if is_transition_sfx else 0.0
                delay_ms = int(max(0.02, sfx_event_start(cue) - pre_roll) * 1000)
                node_name = f"sfx_{idx}"
                filter_complex.append(
                    f"[{input_count}:a]volume={policy.sfx_volume},adelay={delay_ms}|{delay_ms}[{node_name}];"
                )
                sfx_nodes.append(f"[{node_name}]")
                input_count += 1

        # 3.5 One SFX input per overlay that carries one. The banner is an
        # overlay too now, so a banner with a whoosh mixes like any other.
        if overlays:
            for idx, item in enumerate(overlays):
                if not is_sfx_event_eligible(item, total_duration=total_duration, default_start=0.0):
                    continue
                sfx_type = item.get("sfx")
                if not sfx_type:
                    continue
                sfx_file = cls.resolve(sfx_type)
                if sfx_file and sfx_file.exists():
                    inputs.extend(["-i", str(sfx_file)])
                    sfx_name_low = str(sfx_file.name).lower()
                    is_transition_sfx = any(w in sfx_name_low for w in ["whoosh", "swish", "swoosh", "transition"])
                    pre_roll = 0.12 if is_transition_sfx else 0.0
                    delay_ms = int(max(0.02, sfx_event_start(item) - pre_roll) * 1000)
                    node_name = f"sfx_txt_{idx}"
                    filter_complex.append(
                        f"[{input_count}:a]volume={policy.sfx_volume},adelay={delay_ms}|{delay_ms}[{node_name}];"
                    )
                    sfx_nodes.append(f"[{node_name}]")
                    input_count += 1

        # 4. Add BGM input if exists
        bgm_node = None
        if bgm_path and bgm_path.exists():
            inputs.extend(["-stream_loop", "-1", "-i", str(bgm_path)])
            bgm_idx = input_count
            input_count += 1

            # Light tempo-match: nudge the BGM's speed toward how fast this
            # script is actually being read (chars/sec of the cues vs. a
            # normal-pace baseline), clamped to +-8% so it never audibly
            # pitches/warps -- a script read faster than usual gets a
            # slightly quicker bed instead of the two visibly drifting apart.
            tempo_ratio = bgm_tempo_ratio(cues)

            # Without ducking this is simply a constant, quiet music bed --
            # which is all it ever was, despite the old comment here claiming
            # auto-ducking. With ducking on, sidechaincompress pulls the music
            # down while the voice is actually speaking and lets it back up in
            # the gaps. Both legs need a matching format or the filter errors.
            fade_start = max(0.0, total_duration - 0.35)
            filter_complex.append(
                f"[{bgm_idx}:a]atempo={tempo_ratio:.3f},volume={policy.bgm_volume},atrim=0:{total_duration + 0.5},"
                f"afade=t=out:st={fade_start:.3f}:d=0.35[bgm_bed];"
            )
            if policy.bgm_ducking:
                filter_complex.append(
                    "[bgm_bed]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[bgm_fmt];"
                    "[voice_key]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[key_fmt];"
                    "[bgm_fmt][key_fmt]sidechaincompress="
                    # threshold/ratio picked by measurement, not by feel: on a test
                    # mix these pull the music down 13.7 dB while the voice is
                    # speaking (0.05/8 gave only 6.6 dB, 0.01/20 overdid it at
                    # 18.6 dB and left the bed inaudible).
                    f"threshold={policy.ducking_threshold}:ratio={policy.ducking_ratio}:"
                    f"attack={policy.ducking_attack_ms}:release={policy.ducking_release_ms}:makeup=1[bgm];"
                )
            else:
                filter_complex.append("[bgm_bed]anull[bgm];")
            bgm_node = "[bgm]"

        # 5. Combine all tracks with amix (normalize=0 to prevent volume reduction) + Loudness Normalization
        if policy.bgm_ducking and not bgm_node:
            # No music to duck: the split key would dangle and ffmpeg refuses a
            # filter graph with an unused output.
            filter_complex.append("[voice_key]anullsink;")
        mix_inputs = ["[voice_padded]"] + sfx_nodes
        if bgm_node:
            mix_inputs.append(bgm_node)

        filter_complex.append(
            f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:normalize=0:duration=first,"
            f"{loudness_filter(policy)}[aout]"
        )

        full_filter = "".join(filter_complex)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", full_filter,
            "-map", "[aout]",
            "-ac", "2",
            "-ar", "44100",
            "-t", str(total_duration + 0.2),
            str(out_path)
        ]

        # Many SFX cues make this graph (and the command line) long; above the
        # threshold it travels through a temp file, otherwise cmd is untouched.
        cmd, graph_script_file = externalize_filter_graph(cmd, full_filter)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        finally:
            cleanup_graph_file(graph_script_file)
        if res.returncode != 0:
            err_msg = res.stderr[:500] if res.stderr else "Unknown error"
            logger.warning(
                "Advanced audio mix failed (exit %s). Falling back to voice-only track. Error: %s",
                res.returncode,
                err_msg,
            )
            print(f"Warning: Advanced mix had warning, falling back to simple voice copy. Stderr: {err_msg[:200]}")
            cls.last_mix_status = {
                "success": False,
                "fallback": True,
                "error": err_msg,
            }
            # Losing the music/SFX must not undo an intentional voice mute
            # or its saved gain. Keep the same padded timeline bound as the
            # full mix, without the advanced filter graph that just failed.
            cmd_fb = [
                "ffmpeg", "-y", "-i", str(voice_path),
                "-af", f"volume={policy.voice_volume},apad=pad_dur=1.0",
                "-ac", "2", "-ar", "44100",
                "-t", str(total_duration + 0.2), str(out_path),
            ]
            if cut_graph:
                # The cuts still apply: a voice-only track must stay on the
                # same (post-cut) timeline as the picture, subtitles and SFX.
                cmd_fb = [
                    "ffmpeg", "-y", "-i", str(voice_path),
                    "-filter_complex",
                    f"{cut_graph}[voice_cut]volume={policy.voice_volume},apad=pad_dur=1.0[voice_fb]",
                    "-map", "[voice_fb]",
                    "-ac", "2", "-ar", "44100",
                    "-t", str(total_duration + 0.2), str(out_path),
                ]
            fb_res = subprocess.run(cmd_fb, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if fb_res.returncode != 0:
                fb_err = fb_res.stderr[:500] if fb_res.stderr else "Unknown error"
                logger.error("Audio mix fallback (voice-only copy) also failed: %s", fb_err)
                cls.last_mix_status["fallback_error"] = fb_err
        else:
            cls.last_mix_status = {
                "success": True,
                "fallback": False,
                "error": None,
            }

        return str(out_path)

if __name__ == "__main__":
    print("SFXManager ready.")
