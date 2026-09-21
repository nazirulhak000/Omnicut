# Phase 6 — Golden-master validation report format

สถานะเอกสารนี้เป็น **เครื่องมือและรูปแบบรายงาน** เท่านั้น ยังไม่มีการอ้างว่า
ฟุตเทจจริงของโปรเจกต์ผ่านการตรวจแล้ว การรันกับไฟล์จริงต้องทำแยกต่างหากด้วย
`tools/golden_master_probe.py` และเก็บ JSON ที่ได้จากการรันนั้นไว้เป็นหลักฐาน

## ขอบเขต

`golden_master_probe.py` ตรวจ artifact ที่ render เสร็จแล้วแบบอ่านอย่างเดียว:

- `ffprobe` อ่าน stream/container metadata: duration, resolution, FPS, frame count,
  audio sample rate/channels และ duration ของแต่ละ stream
- `ffmpeg` ดึงภาพ grayscale ขนาดเล็กจากสามจุด: `entry`, `hold`, `exit`
- ทุก sample มี SHA-256 fingerprint และค่า `mean_luma`, `min_luma`, `max_luma`
  เพื่อจับภาพดำ ภาพค้าง และการเปลี่ยนแปลงที่ควรตรวจต่อ
- `volumedetect` เก็บ `mean_volume_db` และ `max_volume_db` พร้อมสัญญาณ
  near-silence, peak ใกล้ clipping และ audio/video duration mismatch
- `compare_reports(reference, candidate)` คืนค่า delta เชิงตัวเลขโดยไม่เทียบ path
  ของเครื่อง ซึ่งเหมาะกับการเก็บคะแนนก่อน/หลังเปลี่ยน style

การตรวจนี้เป็น smoke/triage gate ไม่ใช่การพิสูจน์ว่า motion สวย, subtitle อ่านง่าย,
สีถูกต้องเชิงศิลป์ หรือ Preview = Render ตรงกันทุก pixel

## วิธีรัน

ต้องมี `ffmpeg` และ `ffprobe` อยู่ใน PATH:

```powershell
python tools/golden_master_probe.py path\to\render.mp4 `
  --expected-width 1080 --expected-height 1920 --expected-fps 30 `
  --require-audio --output path\to\render.golden.json
```

ถ้าต้องการเทียบกับ baseline:

```powershell
python tools/golden_master_probe.py path\to\after.mp4 `
  --baseline path\to\before.golden.json `
  --output path\to\after.golden.json
```

exit code เป็น `0` เมื่อไม่มี `fail` signal และเป็น `1` เมื่อ artifact อ่านไม่ได้,
ไม่มี video, metadata ไม่ตรง expectation หรือไม่พบ audio ทั้งที่ใช้ `--require-audio`.
`warn` ยังไม่ทำให้ process fail เพราะภาพดำ/ภาพค้าง/peak อาจเป็นความตั้งใจของงาน
และต้องมีคน review บริบทของคลิป

## Numeric JSON contract (`golden-master.v1`)

ตัวอย่างด้านล่างเป็น **ตัวอย่างโครงสร้าง ไม่ใช่ผลจากฟุตเทจจริง**:

```json
{
  "schema_version": "golden-master.v1",
  "artifact": {"path": "render.mp4", "exists": true, "size_bytes": 123456},
  "thresholds": {
    "black_luma_max": 2.0,
    "clipping_peak_db": -0.1,
    "silence_peak_db": -60.0,
    "max_av_duration_delta_s": 0.25,
    "frame_width": 32,
    "frame_height": 32
  },
  "media": {
    "duration_s": 12.5,
    "video": {"width": 1080, "height": 1920, "fps": 30.0, "frame_count": 375, "duration_s": 12.5},
    "audio": {"sample_rate": 48000, "channels": 2, "duration_s": 12.5}
  },
  "samples": [
    {"label": "entry", "time_s": 0.0, "sha256": "...", "mean_luma": 88.0,
     "min_luma": 0, "max_luma": 255, "is_black": false},
    {"label": "hold", "time_s": 6.25, "sha256": "...", "mean_luma": 91.0,
     "min_luma": 1, "max_luma": 255, "is_black": false},
    {"label": "exit", "time_s": 12.466667, "sha256": "...", "mean_luma": 85.0,
     "min_luma": 0, "max_luma": 254, "is_black": false}
  ],
  "audio": {"present": true, "mean_volume_db": -18.0, "max_volume_db": -3.0,
            "video_audio_duration_delta_s": 0.0},
  "signals": [],
  "score": {"passed_checks": 1, "warning_signals": 0, "failed_signals": 0, "pass_rate_pct": 100.0},
  "status": "pass"
}
```

### Signal semantics

| Code | Severity | Meaning |
|---|---|---|
| `artifact_missing`, `probe_failed`, `video_stream_missing`, `duration_invalid`, `dimensions_invalid`, `*_mismatch`, `frame_sample_failed` | `fail` | Output cannot be trusted for this gate |
| `black_frame_sample` | `warn` | Sample is at/below `black_luma_max`; may be intentional fade/transition |
| `identical_sample_frames` | `warn` | All sampled fingerprints match; possible frozen render |
| `audio_stream_missing` | `warn`/`fail` | Missing audio; becomes fail with `--require-audio` |
| `audio_video_duration_mismatch` | `warn` | Absolute stream-duration delta exceeds `0.25s` by default |
| `audio_peak_near_clip`, `audio_near_silence`, `audio_probe_failed` | `warn` | Basic mix signal requiring contextual review |

## Required Phase 6 evidence

For each representative fixture, store:

1. the exact input/fixture identity and render command or pipeline revision;
2. the probe JSON before the style change;
3. the probe JSON after the style change and its `comparison` object;
4. a human review of entry/hold/exit frames and the actual exported audio;
5. separate Preview = Render parity and multi-frame FFmpeg behavioral test results.

The probe does **not** generate a golden baseline, does not decide whether a black
frame is intentional, and does not replace visual inspection. Real-footage runs may
also vary with codec, source VFR behavior, hardware encoder, and intentional fades.
Therefore a passing synthetic fixture must never be reported as a passing production
clip without the corresponding real artifact evidence.
