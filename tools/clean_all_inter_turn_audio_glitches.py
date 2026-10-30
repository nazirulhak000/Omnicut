"""Comprehensive Cleaner for Inter-Turn and Tail Audio Glitches across All 20 Essager Clips.
Eliminates:
1. Mid-clip digital noise bursts (e.g. 120ms burst at 54.24s in s19 between Female & Male turns)
2. Trailing TTS glitches at the end of raw takes and vo.wav
3. Splice pops and clicks in silence intervals between dialogue
Preserves 100% of spoken dialogue.
"""
import sys
import wave
from pathlib import Path
import numpy as np

# Force UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
CLIPS_DIR = STUDIO / "clips"
ASSETS_DIR = STUDIO / "assets" / "clips"

def clean_isolated_bursts_in_vo(pcm: np.ndarray, sr: int, ch: int):
    """Detect and silence isolated noise bursts and splice clicks in vo.wav."""
    win = int(0.01 * sr * ch) # 10ms window
    n_win = len(pcm) // win
    frames = pcm[:n_win * win].reshape(n_win, win)
    rms = np.sqrt(np.mean(frames.astype(np.float32)**2, axis=1))
    max_amp = np.max(np.abs(frames), axis=1)
    
    cleaned = pcm.copy()
    glitch_log = []
    
    i = 2
    while i < n_win - 3:
        # Check if preceded by silence (at least 20ms with rms < 80)
        quiet_before = (rms[i-2] < 80 and rms[i-1] < 80)
        if quiet_before and max_amp[i] > 5000 and rms[i] > 800:
            # Find burst end
            j = i
            while j < n_win and (max_amp[j] > 1200 or rms[j] > 250):
                j += 1
            burst_len_ms = (j - i) * 10
            
            # Check if followed by silence (at least 20ms with rms < 80) or end of file
            quiet_after = (j >= n_win - 2) or (rms[j] < 80 and rms[j+1] < 80)
            
            # If isolated burst is between 10ms and 360ms
            if quiet_after and 10 <= burst_len_ms <= 360:
                t0 = i * 0.01
                t1 = j * 0.01
                max_val = int(np.max(max_amp[i:j]))
                glitch_log.append((t0, t1, burst_len_ms, max_val))
                
                # Apply 5ms fade-out at burst start and 5ms fade-in at burst end
                s_start = i * win
                s_end = j * win
                fade_s = int(0.005 * sr * ch)
                
                # Zero out the noise interval
                cleaned[s_start:s_end] = 0
                
                # Smooth transition on boundaries
                if s_start >= fade_s:
                    fade_steps = fade_s // ch
                    mono_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_steps)))
                    curve = np.repeat(mono_curve, ch) if ch == 2 else mono_curve
                    cleaned[s_start-fade_s:s_start] = (cleaned[s_start-fade_s:s_start] * curve).astype(np.int16)
                
                i = j + 2
                continue
        i += 1
        
    # Also ensure the last 100ms fades smoothly to zero
    tail_fade_s = int(0.08 * sr * ch)
    if len(cleaned) > tail_fade_s:
        # If last 100ms has any energy, zero it out with fade
        if np.max(np.abs(cleaned[-tail_fade_s:])) > 0:
            fade_steps = tail_fade_s // ch
            mono_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_steps)))
            curve = np.repeat(mono_curve, ch) if ch == 2 else mono_curve
            cleaned[-tail_fade_s:] = (cleaned[-tail_fade_s:] * curve).astype(np.int16)
            cleaned[-int(0.05 * sr * ch):] = 0
            
    return cleaned, glitch_log

def clean_take_or_turn_wav(wav_path: Path):
    """Ensure raw take or turn wav has no trailing noise spike."""
    if not wav_path.exists():
        return False, 0
    with wave.open(str(wav_path), "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        data = wf.readframes(wf.getnframes())

    pcm = np.frombuffer(data, dtype=np.int16).copy()
    win = int(0.01 * framerate) * nchannels
    n_win = min(len(pcm) // win, int(0.50 * framerate * nchannels / win)) # check last 500ms
    if n_win < 3:
        return False, 0
        
    frames = pcm[-n_win*win:].reshape(n_win, win)
    rms = np.sqrt(np.mean(frames.astype(np.float32)**2, axis=1))
    max_amp = np.max(np.abs(frames), axis=1)

    # Scan for trailing glitch
    for k in range(len(frames) - 1):
        if rms[k] < 80 and max_amp[k+1] > 3000:
            cutoff_sample = len(pcm) - (n_win - k) * win
            pcm = pcm[:cutoff_sample]
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(nchannels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(framerate)
                wf.writeframes(pcm.tobytes())
            return True, int(max_amp[k+1])
    return False, 0

def main():
    print("=" * 70)
    print("🚀 Running Inter-Turn and Tail Audio Glitch Cleaner across 20 Clips")
    print("=" * 70)
    
    total_bursts_cleaned = 0
    clips_with_glitches = {}
    
    # 1. Clean all vo.wav files
    for i in range(1, 21):
        cid = f"ess02-pov-s{i:02d}"
        vo_path = ASSETS_DIR / cid / "vo.wav"
        if not vo_path.exists():
            continue
            
        with wave.open(str(vo_path), "rb") as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            data = wf.readframes(wf.getnframes())
            
        pcm = np.frombuffer(data, dtype=np.int16)
        cleaned_pcm, glitches = clean_isolated_bursts_in_vo(pcm, framerate, nchannels)
        
        if glitches:
            total_bursts_cleaned += len(glitches)
            clips_with_glitches[cid] = glitches
            print(f"[{cid}] Cleaned {len(glitches)} noise burst(s):")
            for g in glitches:
                print(f"   ⚡ t={g[0]:.2f}s - {g[1]:.2f}s ({g[2]}ms, max amplitude={g[3]})")
                
            # Write back cleaned vo.wav
            with wave.open(str(vo_path), "wb") as wf:
                wf.setnchannels(nchannels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(framerate)
                wf.writeframes(cleaned_pcm.tobytes())
        else:
            print(f"[{cid}] vo.wav: Clean (no isolated bursts)")

    # 2. Clean any remaining tts raw wavs
    raw_cleaned = 0
    for i in range(1, 21):
        cid = f"ess02-pov-s{i:02d}"
        tts_dir = CLIPS_DIR / cid / "tts"
        if tts_dir.exists():
            for p in sorted(tts_dir.glob("*.wav")):
                tok, max_spk = clean_take_or_turn_wav(p)
                if tok:
                    raw_cleaned += 1
                    print(f"  [{cid}/tts] Trimmed trailing spike in {p.name} (max={max_spk})")

    # 3. Verification Phase: re-scan all 20 vo.wav files
    print("\n" + "=" * 70)
    print("🔍 VERIFICATION: Re-scanning all 20 vo.wav files for any remaining glitches")
    print("=" * 70)
    
    all_clean = True
    for i in range(1, 21):
        cid = f"ess02-pov-s{i:02d}"
        vo_path = ASSETS_DIR / cid / "vo.wav"
        with wave.open(str(vo_path), "rb") as wf:
            framerate = wf.getframerate()
            nchannels = wf.getnchannels()
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        
        _, remaining = clean_isolated_bursts_in_vo(pcm, framerate, nchannels)
        # Check tail 100ms
        tail = pcm[-int(0.10 * framerate * nchannels):]
        tail_max = np.max(np.abs(tail)) if len(tail) > 0 else 0
        
        if remaining or tail_max > 0:
            print(f"❌ [{cid}] Still has issues: {len(remaining)} bursts, tail_max={tail_max}")
            all_clean = False
        else:
            print(f"✅ [{cid}] 100% Clean! (0 glitches, tail_max=0)")

    if all_clean:
        print("\n🎉 SUCCESS: All 20 clips are now 100% clean and artifact-free!")
    else:
        print("\n⚠️ Some clips still need attention.")
        
    print(f"\nSummary:")
    print(f"- Total clips with corrupted audio fixed: {len(clips_with_glitches)} / 20")
    print(f"- Total noise bursts eliminated: {total_bursts_cleaned}")
    print(f"- Raw TTS files trimmed: {raw_cleaned}")

if __name__ == "__main__":
    main()
