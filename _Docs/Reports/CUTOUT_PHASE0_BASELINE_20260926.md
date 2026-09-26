# Phase 0 Baseline — Cutout Video Pipeline (วัดจริง 2026-09-26)

**ดำเนินการโดย:** Claude Code (Claude Opus 5 1M)
**รอบ:** CUTOUT-VIDEO-PIPELINE-REPLAN-20260926 — Phase 0
**เครื่องที่วัด:** Windows 11, ffmpeg จาก PATH, `.venv` ของโปรเจกต์

> เอกสารนี้บันทึก **ตัวเลขที่วัดได้จริง** จากฟุตเทจจริง ไม่ใช่ค่าประมาณ
> รายงานรอบก่อน (`CUTOUT_VIDEO_PIPELINE_20260926.md`) ระบุเองว่าตัวเลข 341.66 MB
> เป็นค่าที่อ่านจากภาพหน้าจอ ไม่ใช่การวัด และยังไม่มีการจับเวลาใดๆ

---

## 1. สิ่งที่เพิ่มเข้าไปเพื่อให้วัดได้

ก่อนหน้านี้ `scripts/background_isolation_video_worker.py` **ไม่มีการจับเวลาเลย**
(`grep perf_counter|elapsed|time.monotonic` ได้ 0 บรรทัด) จึงพิสูจน์เรื่องความเร็วไม่ได้

เพิ่ม `manifest["performance"]` ที่เขียนตอน encode เสร็จ เก็บค่าที่วัดจากนาฬิกาจริง:

| ฟิลด์ | ความหมาย |
| :--- | :--- |
| `encode_seconds` | เวลาลูป decode → rembg → encode ทั้งหมด |
| `frame_count` | จำนวนเฟรมที่ผลิตได้จริง |
| `source_seconds` | ช่วงเวลาต้นฉบับที่เฟรมครอบคลุมจริง (ไม่ใช่ค่าที่ขอมา) |
| `seconds_per_frame` | ต้นทุนต่อเฟรม |
| `realtime_factor` | `encode_seconds / source_seconds` |
| `output_bytes` / `bytes_per_frame` | ขนาดผลลัพธ์ ใช้จับ regression ของ codec |

ล็อกด้วยเทส `test_manifest_records_measured_encode_performance`

---

## 2. ผลวัดจริง — BLU01 window 22.000–26.720s

ต้นฉบับ: `01_Raw/.../bluwow cx07.mov` · 1920x1080 · 30fps · 78.47s · 141.5 MB

| ตัวชี้วัด | ค่าที่วัดได้ |
| :--- | ---: |
| เฟรม | 142 |
| ช่วงต้นฉบับ | 4.733 s |
| **เวลา encode** | **89.403 s** |
| ต่อเฟรม | 0.6296 s |
| **realtime factor** | **18.89x** (ช้ากว่าเวลาจริง ~19 เท่า) |
| ขนาดผลลัพธ์ | 1,307,288 bytes (1.25 MiB) |
| ต่อเฟรม | 9,206 bytes |

**อ่านค่านี้ยังไง:** คลิป 1 นาทีที่ 1080p30 จะใช้เวลาแยกพื้นหลังราว **19 นาที** บนเครื่องนี้
เป็นงานที่ต้องรันแบบ background เท่านั้น ห้ามให้ผู้ใช้รอหน้าจอ

ประมาณการทั้ง 4 windows ของ BLU01 (848 เฟรม): ~**534 วินาที (~9 นาที)**
ตัวเลขนี้เป็นการประมาณจากต้นทุนต่อเฟรมที่วัดได้ ไม่ได้รันครบทั้ง 4 windows

---

## 3. พิสูจน์ alpha — และกับดักที่เจอระหว่างวัด

**ผลลัพธ์: artifact ถูกต้อง** decode แล้วได้ alpha `min=0 max=255` (มีทั้งโปร่งและทึบจริง)

**แต่เจอกับดักสำคัญ:** ตอนแรกผม probe โดยไม่ระบุ decoder ได้ `min=255 max=255`
ซึ่งดูเหมือน alpha หาย ทั้งที่ไฟล์ปกติดี

| คำสั่ง | ผล alpha |
| :--- | :--- |
| `ffmpeg -ss 4.0 -i cutout.webm ...` | `min=255 max=255` ❌ **alpha หาย** |
| `ffmpeg -c:v libvpx-vp9 -ss 4.0 -i cutout.webm ...` | `min=0 max=255` ✅ ถูกต้อง |

ffmpeg เลือก VP9 decoder ตัวปกติที่**ทิ้ง alpha plane เงียบๆ** ต้องบังคับ `-c:v libvpx-vp9` เสมอ

ตรงนี้ยืนยันว่าที่ `_verify_video()` (`background_isolation_video_worker.py:45-68`)
บังคับ decoder ไว้นั้น **เป็นสิ่งจำเป็น ไม่ใช่ของเกิน** — ถ้าใครถอดออกจะได้ false negative ทันที
และตรงกับที่แผน `CUTOUT_VIDEO_PIPELINE_REPLAN_20260926.md:64` เตือนไว้

---

## 4. Seek latency — วัดแล้ว แต่เทียบกับ gate ไม่ได้

วัด 30 seeks สลับหน้า/หลังบน artifact จริง (บังคับ `-c:v libvpx-vp9`):

| | ms |
| :--- | ---: |
| p50 | 309 |
| p95 | 344 |
| min / max | 273 / 347 |

**ดูเผินๆ เหมือนไม่ผ่าน gate `warm seek p95 <= 200ms`
(`CUTOUT_TEMPORAL_QUALITY_PLAN_20260926.md:121`) แต่สรุปแบบนั้นไม่ได้**

แยกต้นทุนออกมาแล้วพบว่าเกือบทั้งหมดคือการ start process ไม่ใช่การ seek:

| | p50 (ms) |
| :--- | ---: |
| start ffmpeg เปล่าๆ (`-version`) | 242 |
| decode เฟรมแรก ไม่ seek | 287 |
| decode หลัง seek | 309 |
| **ต้นทุน seek จริง** | **~22** |

gate 200ms หมายถึง **การ seek ในเบราว์เซอร์** ซึ่งเปิดไฟล์ค้างไว้แล้ว ไม่ได้ start process ใหม่ทุกครั้ง
การวัดผ่าน subprocess จึงเทียบกันไม่ได้ **ไม่ถือว่า gate นี้ fail**

ฝั่งเบราว์เซอร์มีเทสคุมอยู่แล้วที่ `tests/motion_capture/test_cutout_video_preview.py`
(ยืนยัน `seeks <= 2` และเฟรมที่มองเห็น) — แต่เป็น **correctness ไม่ใช่ latency**
การวัด p50/p95 ในเบราว์เซอร์จริงยังเป็นงานค้าง

---

## 5. สรุปสถานะ Phase 0

| หัวข้อ | สถานะ |
| :--- | :--- |
| VP9 alpha ถูกต้อง | ✅ วัดแล้ว `min=0 max=255` |
| ต้องบังคับ `-c:v libvpx-vp9` | ✅ พิสูจน์แล้วว่าจำเป็น (ไม่ใส่ = alpha หายเงียบ) |
| Seek ทำงานได้ | ✅ decode ได้ทุกตำแหน่งที่ทดสอบ |
| เวลา encode | ✅ วัดแล้ว 18.89x realtime |
| ขนาดผลลัพธ์ | ✅ วัดแล้ว 9,206 bytes/frame |
| บันทึกลง manifest อัตโนมัติ | ✅ ทุก artifact ต่อจากนี้มีตัวเลขติดมาเอง |
| Seek p50/p95 ในเบราว์เซอร์จริง | ⬜ ยังไม่วัด |
| VFR source | ⬜ ไม่มีเทสครอบคลุม |
| `rotation != 0` | ⬜ ทุก call site ส่ง `rotation=0` |

---

## Notes

- ไฟล์ที่ใช้วัดทั้งหมดอยู่ใน `.tmp/phase0_baseline/` (gitignored) และลบแล้วหลังวัดเสร็จ
- ไม่แตะ `01_Raw/`, `02_Assets/`, `03_Projects/`, `04_Exports/`
- วัด window เดียว (สั้นสุดใน 4 windows) เพราะต้นทุน ~90 วินาทีต่อ window
  ตัวเลขต่อเฟรมใช้ประมาณ window อื่นได้ แต่ **ยังไม่ได้วัดครบทั้ง 4**
- `temporal mode` ที่ใช้วัดคือ `legacy` (ค่า default) ไม่ใช่ `motion`
