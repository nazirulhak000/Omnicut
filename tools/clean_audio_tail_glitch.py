"""Clean audio tail glitch across all 20 Essager clips.
Removes the 150ms digital noise corruption caused by Gemini Flash TTS API chunking
without affecting spoken dialogue.
"""
import json
import wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
CLIPS_DIR = STUDIO / "clips"
ASSETS_DIR = STUDIO / "assets" / "clips"

def clean_vo_wav(vo_path: Path):
    """Detect and eliminate the tail noise burst in vo.wav."""
    if not vo_path.exists():
        return False, "file_not_found"

    with wave.open(str(vo_path), "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        data = wf.readframes(nframes)

    pcm = np.frombuffer(data, dtype=np.int16).copy()
    
    # We inspect the last 1.2 seconds in 10ms windows
    step_samples = int(0.01 * framerate) * nchannels
    n_steps = int(1.2 / 0.01)
    
    if len(pcm) < n_steps * step_samples:
        return False, "too_short"

    tail_pcm = pcm[-n_steps * step_samples:]
    frames = tail_pcm.reshape(n_steps, -1)
    max_amp = np.max(np.abs(frames), axis=1)
    rms = np.sqrt(np.mean(frames.astype(np.float32)**2, axis=1))

    # Scan for a spike (> 1000) in the last 450ms
    spike_window_start = n_steps - int(0.45 / 0.01)
    glitch_idx = None
    for idx in range(n_steps - 1, spike_window_start, -1):
        if max_amp[idx] > 1000:
            glitch_idx = idx
            break

    if glitch_idx is not None:
        # Check if preceded by a silence gap (rms < 50) within 350ms before glitch
        silence_idx = None
        for s_idx in range(glitch_idx - 1, max(0, glitch_idx - int(0.35 / 0.01)), -1):
            if rms[s_idx] < 50:
                silence_idx = s_idx
                break
        
        if silence_idx is not None:
            # We found silence right before the glitch!
            # silence_idx is the index in tail_pcm
            sample_offset_from_end = (n_steps - silence_idx) * step_samples
            cut_point = len(pcm) - sample_offset_from_end
            
            # Apply a 20ms gentle cosine fade-out at cut_point
            fade_len = int(0.02 * framerate) * nchannels
            if cut_point > fade_len:
                fade_steps = fade_len // nchannels
                mono_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_steps)))
                curve = np.repeat(mono_curve, nchannels) if nchannels == 2 else mono_curve
                pcm[cut_point - fade_len : cut_point] = (
                    pcm[cut_point - fade_len : cut_point] * curve
                ).astype(np.int16)
            
            # Zero out everything from cut_point to the end
            pcm[cut_point:] = 0
            
            with wave.open(str(vo_path), "wb") as wf:
                wf.setnchannels(nchannels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(framerate)
                wf.writeframes(pcm.tobytes())
            
            ms_cut = sample_offset_from_end / (framerate * nchannels) * 1000
            return True, f"cleaned_tail_glitch_{ms_cut:.0f}ms"

    # Even if no glitch was detected, ensure the very end (last 80ms) fades cleanly to zero
    fade_len = int(0.08 * framerate) * nchannels
    if len(pcm) > fade_len:
        fade_steps = fade_len // nchannels
        mono_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_steps)))
        curve = np.repeat(mono_curve, nchannels) if nchannels == 2 else mono_curve
        pcm[-fade_len:] = (pcm[-fade_len:] * curve).astype(np.int16)
        with wave.open(str(vo_path), "wb") as wf:
            wf.setnchannels(nchannels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(framerate)
            wf.writeframes(pcm.tobytes())
        return True, "smooth_tail_fade"

    return False, "no_action"

def clean_take_or_turn_wav(wav_path: Path):
    """Remove trailing noise from take_*.wav or turn_*.wav."""
    if not wav_path.exists():
        return False, "not_found"

    with wave.open(str(wav_path), "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        data = wf.readframes(wf.getnframes())

    pcm = np.frombuffer(data, dtype=np.int16).copy()
    win = int(0.01 * framerate) * nchannels
    n_win = int(0.35 * framerate * nchannels / win) # check last 350ms
    if len(pcm) < n_win * win:
        return False, "too_short"

    frames = pcm[:len(pcm)//win*win].reshape(-1, win)
    rms = np.sqrt(np.mean(frames.astype(np.float32)**2, axis=1))

    glitch_start_idx = None
    for i in range(1, min(n_win, len(rms)) + 1):
        idx = len(rms) - i
        if rms[idx] > 500:
            glitch_start_idx = idx

    if glitch_start_idx is not None:
        silence_idx = None
        for j in range(glitch_start_idx - 1, max(0, glitch_start_idx - 25), -1):
            if rms[j] < 100:
                silence_idx = j
                break
        if silence_idx is not None:
            cutoff_sample = silence_idx * win
            pcm = pcm[:cutoff_sample]
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(nchannels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(framerate)
                wf.writeframes(pcm.tobytes())
            return True, f"trimmed_{(len(data)//2 - cutoff_sample)/(framerate*nchannels)*1000:.1f}ms"
    return False, "clean"

def main():
    print("=== Cleaning Audio Tail Glitches across All 20 Clips ===")
    vo_cleaned = 0
    take_cleaned = 0
    
    for i in range(1, 21):
        cid = f"ess02-pov-s{i:02d}"
        vo_path = ASSETS_DIR / cid / "vo.wav"
        ok, reason = clean_vo_wav(vo_path)
        if ok:
            vo_cleaned += 1
            print(f"[{cid}] vo.wav: {reason}")
            
        clip_dir = CLIPS_DIR / cid
        tts_dir = clip_dir / "tts"
        if tts_dir.exists():
            for p in sorted(tts_dir.glob("*.wav")):
                tok, treason = clean_take_or_turn_wav(p)
                if tok and "trimmed" in treason:
                    take_cleaned += 1
                    print(f"  [{cid}/tts] {p.name}: {treason}")

    print(f"\nDone! Cleaned {vo_cleaned} vo.wav files and {take_cleaned} raw tts files.")

if __name__ == "__main__":
    main()
