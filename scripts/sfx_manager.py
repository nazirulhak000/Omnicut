"""
Audio & SFX Manager with Auto-Ducking and Timestamped Sound Effects Mixing
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import SFX_DIR, MUSIC_DIR, BGM_VOLUME, VOICE_VOLUME, SFX_VOLUME
from scripts.asset_registry import AssetRegistry
from scripts.it_angles import DEFAULT_BGM

class SFXManager:
    """Handles sound effects placement and background music mixing with auto-ducking."""

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
        text_overlays: Optional[List[Dict]] = None
    ) -> str:
        """
        Mixes voiceover, SFX triggers at cue start times, and looped background music.
        """
        out_path = Path(output_audio_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        voice_path = Path(voice_audio_path).resolve()
        bgm_path = cls.resolve_bgm_path(bgm_name)

        inputs = ["-i", str(voice_path)]
        filter_complex = []
        input_count = 1

        # 1. Voice filter (clear voice). With ducking on, the voice is split:
        # one copy goes into the mix, the other is only a sidechain key for the
        # music -- it is never heard twice.
        bgm_vol = min(1.0, max(0.0, float(bgm_vol)))
        if bgm_ducking:
            filter_complex.append(
                f"[0:a]volume={voice_vol},apad=pad_dur=1.0,asplit=2[voice_padded][voice_key];"
            )
        else:
            filter_complex.append(f"[0:a]volume={voice_vol},apad=pad_dur=1.0[voice_padded];")

        # 2. Add Boom on 0.0s Hook
        boom_file = cls.resolve("boom")
        if boom_file and boom_file.exists():
            inputs.extend(["-i", str(boom_file)])
            filter_complex.append(f"[{input_count}:a]volume={sfx_vol}[sfx_boom];")
            sfx_nodes = ["[sfx_boom]"]
            input_count += 1
        else:
            sfx_nodes = []

        # 3. Add SFX inputs per cue
        for idx, cue in enumerate(cues):
            sfx_type = cue.get("sfx")
            sfx_file = cls.resolve(sfx_type) if sfx_type else None
            if sfx_file and sfx_file.exists():
                inputs.extend(["-i", str(sfx_file)])
                # J-Cut Transition SFX: เสียง Whoosh เริ่มก่อนรอยต่อภาพ 120ms เพื่อให้จุดพีคตรงกับรอยต่อพอดี
                sfx_name_low = str(sfx_file.name).lower()
                is_transition_sfx = any(w in sfx_name_low for w in ["whoosh", "swish", "swoosh", "transition"])
                pre_roll = 0.12 if is_transition_sfx else 0.0
                delay_ms = int(max(0.02, float(cue["start"]) - pre_roll) * 1000)
                node_name = f"sfx_{idx}"
                filter_complex.append(
                    f"[{input_count}:a]volume={sfx_vol},adelay={delay_ms}|{delay_ms}[{node_name}];"
                )
                sfx_nodes.append(f"[{node_name}]")
                input_count += 1

        # 3.5 Add SFX inputs per text overlay
        if text_overlays:
            for idx, item in enumerate(text_overlays):
                sfx_type = item.get("sfx")
                if not sfx_type:
                    continue
                sfx_file = cls.resolve(sfx_type)
                if sfx_file and sfx_file.exists():
                    inputs.extend(["-i", str(sfx_file)])
                    sfx_name_low = str(sfx_file.name).lower()
                    is_transition_sfx = any(w in sfx_name_low for w in ["whoosh", "swish", "swoosh", "transition"])
                    pre_roll = 0.12 if is_transition_sfx else 0.0
                    delay_ms = int(max(0.02, float(item.get("start", 0.0)) - pre_roll) * 1000)
                    node_name = f"sfx_txt_{idx}"
                    filter_complex.append(
                        f"[{input_count}:a]volume={sfx_vol},adelay={delay_ms}|{delay_ms}[{node_name}];"
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
            BASELINE_CHARS_PER_SEC = 10.0
            total_chars = sum(len(str(c.get("text", ""))) for c in cues)
            cue_span = sum(
                max(0.01, float(c.get("end", 0.0)) - float(c.get("start", 0.0))) for c in cues
            )
            chars_per_sec = (total_chars / cue_span) if cue_span > 0 else BASELINE_CHARS_PER_SEC
            tempo_ratio = min(1.08, max(0.92, chars_per_sec / BASELINE_CHARS_PER_SEC))

            # Without ducking this is simply a constant, quiet music bed --
            # which is all it ever was, despite the old comment here claiming
            # auto-ducking. With ducking on, sidechaincompress pulls the music
            # down while the voice is actually speaking and lets it back up in
            # the gaps. Both legs need a matching format or the filter errors.
            fade_start = max(0.0, total_duration - 0.35)
            filter_complex.append(
                f"[{bgm_idx}:a]atempo={tempo_ratio:.3f},volume={bgm_vol},atrim=0:{total_duration + 0.5},"
                f"afade=t=out:st={fade_start:.3f}:d=0.35[bgm_bed];"
            )
            if bgm_ducking:
                filter_complex.append(
                    "[bgm_bed]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[bgm_fmt];"
                    "[voice_key]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[key_fmt];"
                    "[bgm_fmt][key_fmt]sidechaincompress="
                    # threshold/ratio picked by measurement, not by feel: on a test
                    # mix these pull the music down 13.7 dB while the voice is
                    # speaking (0.05/8 gave only 6.6 dB, 0.01/20 overdid it at
                    # 18.6 dB and left the bed inaudible).
                    "threshold=0.02:ratio=12:attack=20:release=300:makeup=1[bgm];"
                )
            else:
                filter_complex.append("[bgm_bed]anull[bgm];")
            bgm_node = "[bgm]"

        # 5. Combine all tracks with amix (normalize=0 to prevent volume reduction) + Loudness Normalization
        if bgm_ducking and not bgm_node:
            # No music to duck: the split key would dangle and ffmpeg refuses a
            # filter graph with an unused output.
            filter_complex.append("[voice_key]anullsink;")
        mix_inputs = ["[voice_padded]"] + sfx_nodes
        if bgm_node:
            mix_inputs.append(bgm_node)

        filter_complex.append(
            f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:normalize=0:duration=first,"
            f"loudnorm=I=-14:TP=-1.0:LRA=8[aout]"
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

        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0:
            print(f"Warning: Advanced mix had warning, falling back to simple voice copy. Stderr: {res.stderr[:200]}")
            cmd_fb = ["ffmpeg", "-y", "-i", str(voice_path), "-ac", "2", "-ar", "44100", str(out_path)]
            subprocess.run(cmd_fb, capture_output=True, encoding="utf-8", errors="ignore")

        return str(out_path)

if __name__ == "__main__":
    print("SFXManager ready.")
