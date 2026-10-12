"""Slice the 21 acoustic speech segments from raw_gemini_vo.wav, apply snappy 1.34x tempo,
assemble assets/clips/goc01-pov-32s/vo.wav, and perform acoustic waveform alignment
for every word in each segment to write whisper_words.json.
"""
import json
import subprocess
import wave
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent.parent
RAW_WAV = HERE / "raw_gemini_vo.wav"
OUT_VO = STUDIO / "assets" / "clips" / "goc01-pov-32s" / "vo.wav"
OUT_VO.parent.mkdir(parents=True, exist_ok=True)

# Exact 21 acoustic segments detected from raw_gemini_vo.wav + sub-words in each segment
SEGMENTS = [
    (0.24, 5.22, ["พี่บ่าว", "มานั่งตรงนี้เดี๋ยวนี้", "เมื่อกี้เดินไปหลังบ้าน", "แหลงไหรไว้"]),
    (6.22, 10.06, ["ฮะ", "เปล่าครับที่รัก", "เค้าไปเปิดพัดลมเฉยๆ", "ไม่ได้พูดอะไรเลย"]),
    (10.62, 12.30, ["ไม่ได้แหลงบ้านมึงสิ"]),
    (12.66, 13.12, ["ฟังนะ"]),
    (13.36, 15.22, ["ชัดระดับล้านเค"]),
    (15.82, 20.58, ["เมียดุยังกะหมาพิตบูล", "ตัวก็เล็กนิดเดียว", "ด่าทีบ้านสะเทือน"]),
    (21.16, 23.06, ["หมาพิตบูลพร่องมึงสิ"]),
    (23.36, 25.92, ["เปิดพัดลมเบอร์สาม", "เสียงลมไม่เข้าสักแอะ"]),
    (26.20, 29.02, ["แต่เสียงนินทากูชัด", "ยังกะมานอนแหลงในรูหู"]),
    (29.28, 30.54, ["เบอะบะจริงนิ"]),
    (31.18, 32.20, ["โถ่ที่รัก"]),
    (32.44, 38.94, ["ก็ใครจะคิดว่าไมค์", "GoChek", "Ultra S24", "ตัวแค่นี้", "มันจะตัดเสียงลมเกลี้ยง"]),
    (39.72, 41.14, ["90% ล่ะ"]),
    (42.14, 42.72, ["ไหนเอามาแลดิ๊"]),
    (43.08, 44.80, ["โห", "เคสชาร์จโคตรเท่"]),
    (45.10, 46.78, ["แบตอึด 35 ชั่วโมง"]),
    (47.10, 48.56, ["แถมดูดเสียงทะลุกำแพงอีก", "ยึด"]),
    (50.52, 53.38, ["ทีหลังไปเดินห้าง", "กูจะติดเสื้อมึงไว้ตลอด"]),
    (53.76, 54.68, ["ได้แรงอก"]),
    (55.44, 56.56, ["จบกันชีวิตผม"]),
    (56.84, 60.00, ["ใครอยากได้ไมค์ชัดทะลุกำแพง", "กดตะกร้าเหลือง", "ซ้ายล่างเลยครับ"]),
]


def align_words_in_waveform(samples: np.ndarray, sr: int, words: list[str], seg_offset: float) -> list[dict]:
    """Distribute word boundaries along the real acoustic energy cumulative distribution of the segment."""
    dur = len(samples) / sr
    if len(words) == 1:
        return [{"w": words[0], "s": round(seg_offset, 3), "e": round(seg_offset + dur, 3)}]

    # Compute smooth energy envelope (10ms hop)
    hop = max(1, int(0.01 * sr))
    n_hops = max(1, len(samples) // hop)
    env = np.sqrt(np.mean(samples[:n_hops * hop].reshape(n_hops, hop) ** 2, axis=1)) + 1e-4
    cum_energy = np.cumsum(env)
    cum_energy = cum_energy / cum_energy[-1]

    # Weight each word by phonetic length
    weights = [max(2, len(w.replace(" ", ""))) for w in words]
    total_w = sum(weights)
    cum_w = 0
    out = []
    cur_s = 0.0
    for idx, (w, wt) in enumerate(zip(words, weights)):
        cum_w += wt
        if idx == len(words) - 1:
            nxt_t = dur
        else:
            target_frac = cum_w / total_w
            hop_idx = int(np.searchsorted(cum_energy, target_frac))
            nxt_t = round(min(dur - 0.03, max(cur_s + 0.06, (hop_idx / n_hops) * dur)), 3)
        out.append({
            "w": w,
            "s": round(seg_offset + cur_s, 3),
            "e": round(seg_offset + nxt_t, 3),
        })
        cur_s = nxt_t
    return out


def main():
    with wave.open(str(RAW_WAV), "rb") as wf:
        raw_sr = wf.getframerate()
        raw_frames = wf.readframes(wf.getnframes())
        raw_audio = np.frombuffer(raw_frames, dtype=np.int16)

    tmp_dir = HERE / "_tmp_segs"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    out_sr = 48000
    tempo = 1.34
    gap_sec = 0.05
    gap_samples = np.zeros(int(gap_sec * out_sr), dtype=np.int16)

    combined_mono = []
    all_words = []
    cur_time = 0.0

    for idx, (t0, t1, words) in enumerate(SEGMENTS):
        s0 = int(t0 * raw_sr)
        s1 = int(t1 * raw_sr)
        chunk = raw_audio[s0:s1]

        in_wav = tmp_dir / f"in_{idx:02d}.wav"
        out_wav = tmp_dir / f"out_{idx:02d}.wav"
        with wave.open(str(in_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(raw_sr)
            wf.writeframes(chunk.tobytes())

        # Female segments (ฮาดุหหห): lift pitch +3.1 semitones (1.20x) + sweet presence EQ while keeping exact 1.34x total speed
        female_segs = {0, 2, 3, 4, 6, 7, 8, 9, 13, 14, 15, 16, 17, 18}
        if idx in female_segs:
            pitch = 1.20
            adj_tempo = round(tempo / pitch, 5)
            af = f"asetrate={int(raw_sr * pitch)},aresample={out_sr},atempo={adj_tempo},highpass=f=145,equalizer=f=3600:t=q:w=1.2:g=4.0"
        else:
            af = f"atempo={tempo}"
            if idx == 5:
                af += ",highpass=f=220,lowpass=f=5800,volume=1.15"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(in_wav),
            "-af", af,
            "-ar", str(out_sr), "-ac", "1", str(out_wav)
        ], check=True, capture_output=True)

        with wave.open(str(out_wav), "rb") as wf:
            seg_pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

        seg_float = seg_pcm.astype(np.float32) / 32768.0
        seg_dur = len(seg_pcm) / out_sr

        aligned = align_words_in_waveform(seg_float, out_sr, words, cur_time)
        all_words.extend(aligned)

        combined_mono.append(seg_pcm)
        combined_mono.append(gap_samples)
        cur_time += seg_dur + gap_sec

    full_mono = np.concatenate(combined_mono)
    pre_norm_wav = tmp_dir / "pre_norm.wav"
    with wave.open(str(pre_norm_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(out_sr)
        wf.writeframes(full_mono.tobytes())

    # Final stereo -16 LUFS broadcast master
    subprocess.run([
        "ffmpeg", "-y", "-i", str(pre_norm_wav),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=9",
        "-ar", str(out_sr), "-ac", "2", str(OUT_VO)
    ], check=True, capture_output=True)

    total_dur = round(len(full_mono) / out_sr, 3)
    (HERE / "vo_meta.json").write_text(json.dumps({"duration": total_dur}, indent=2), encoding="utf-8")
    (HERE / "whisper_words.json").write_text(json.dumps(all_words, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Aligned {len(all_words)} words across {len(SEGMENTS)} segments -> {OUT_VO} ({total_dur}s)")


if __name__ == "__main__":
    main()
