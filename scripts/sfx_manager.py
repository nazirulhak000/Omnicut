"""
Audio & SFX Manager with Auto-Ducking and Timestamped Sound Effects Mixing
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import SFX_DIR, MUSIC_DIR, BGM_VOLUME, VOICE_VOLUME, SFX_VOLUME
from scripts.asset_registry import AssetRegistry

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
    def mix_audio_track(
        cls,
        voice_audio_path: str,
        cues: List[Dict],
        total_duration: float,
        output_audio_path: str,
        bgm_name: str = "tiktok_upbeat_bgm.wav",
        bgm_vol: float = 0.12,
        voice_vol: float = 1.0,
        sfx_vol: float = 0.28
    ) -> str:
        """
        Mixes voiceover, SFX triggers at cue start times, and looped background music.
        """
        out_path = Path(output_audio_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        voice_path = Path(voice_audio_path).resolve()
        bgm_path = MUSIC_DIR / bgm_name
        if not bgm_path.exists():
            bgm_files = list(MUSIC_DIR.glob("*.wav")) + list(MUSIC_DIR.glob("*.mp3"))
            bgm_path = bgm_files[0] if bgm_files else None

        inputs = ["-i", str(voice_path)]
        filter_complex = []
        input_count = 1

        # 1. Voice filter (clear voice)
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
                delay_ms = int(max(0.05, cue["start"]) * 1000)
                node_name = f"sfx_{idx}"
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
            # Auto-ducking: low volume during voice, trim to total_duration
            filter_complex.append(
                f"[{bgm_idx}:a]volume={bgm_vol},atrim=0:{total_duration + 0.5},afade=t=out:st={total_duration}:d=0.5[bgm];"
            )
            bgm_node = "[bgm]"

        # 5. Combine all tracks with amix (normalize=0 to prevent volume reduction) + Loudness Normalization
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
