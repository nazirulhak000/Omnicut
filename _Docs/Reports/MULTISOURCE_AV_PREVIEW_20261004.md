# Multisource master-audio preview validation — 2026-10-04

ดำเนินการโดย: Codex (GPT-6)
รอบ: CODEX-EDITING-VALIDATION-20261004 / A2

## ผล

Production `SequencePlayer` ผ่านการเล่นจริงใน headless Chromium ด้วยวิดีโอสังเคราะห์ **3 source ต่างกัน** และเสียง master WAV แบบไม่เงียบ: speed **1 / 1.5 / 0.75**, fade **0.5s**, cut, pause/resume, seek ย้อนหลัง **0.7s** และ seek ไปข้างหน้า **6.0s** การสังเกตการเล่นรวมประมาณ 7 วินาที; เทสทั้งหมด **1 passed in 9.73s** (final run)

ไม่พบ defect ที่ทำซ้ำได้ในขอบเขตนี้ จึงไม่ได้แก้ `SequencePlayer` หรือ scheduler เพิ่ม รอบนี้เพิ่มเฉพาะ browser fixture/test/report

## วัดอะไร

Fixture ใช้ production player ทั้งหมดและ intercept `CanvasRenderingContext2D.drawImage(video)` ทั้ง canvas หลักและ offscreen โดยบันทึกครั้งแรกของแต่ละ source/timeline timestamp เพื่อลดการนับ repeated draw จาก pipeline ภาพ บันทึก `requestVideoFrameCallback` metadata.mediaTime ล่าสุด ซึ่งเป็น timestamp ที่ browser รายงานว่าเสนอแก่ compositor เปรียบเทียบกับ `getDrawPlan()` source time; ไม่ใช้ `video.currentTime` แทน timestamp ของเฟรม

แปลง source PTS กลับเป็น timeline ด้วย `(PTS - trim_start) / speed + segStart` แล้วเทียบกับ `audio.currentTime` ของ master media element ที่กำลังเล่น ค่านี้วัดความสอดคล้องระหว่าง compositor-reported source timestamp กับ master media clock ไม่ใช่เสียงที่ออกจากลำโพงหรือเวลาที่ display แสดง canvas จริง RVFC timestamp ล่าสุดอาจต่างจาก frame ที่ GPU วาดในช่วง callback scheduling; ไม่ถอดรหัส frame ID จากพิกเซลและไม่วัด physical lip sync

ใช้ stable samples ที่ player/audio กำลังเล่น, video ไม่ seeking และ RVFC callback อายุ <100ms: **418 / 426 samples** ไม่นับ source/time ซ้ำจาก offscreen draws ภายใน timestamp เดียว; เป็น samples ของ draw calls ไม่ใช่จำนวน encoded frames หรือ FPS benchmark

## Final run measurements

| Absolute error | Median ms | P95 ms | Max ms |
|---|---:|---:|---:|
| Source compositor PTS vs expected source time | 17.31 | 73.87 | 96.00 |
| PTS mapped to timeline vs master audio media clock | 16.97 | 56.57 | 81.10 |
| Canvas timeline readout vs master audio media clock | 0.00 | 9.57 | 21.33 |
| Video currentTime readout vs expected source time | 11.83 | 23.72 | 25.92 |

ตัวเลข readout ที่ต่ำกว่าตัวเลข PTS แสดงว่า `currentTime` เพียงอย่างเดียวไม่พอใช้สรุปภาพ/เสียงตรงกัน

| ช่วง | Samples | Source PTS error P95 / max ms | PTS mapped vs audio P95 / max ms |
|---|---:|---:|---:|
| Transition (in/out) | 100 | 68.00 / 96.00 | 49.20 / 64.00 |
| Steady (solo) | 318 | 75.83 / 96.00 | 56.89 / 81.10 |

Ready **249.01ms**, backward seek **19.70ms**, forward seek **27.80ms**; pause check 180ms ผ่าน audio movement <20ms และ video movement <40ms; ครบ source av-0/av-1/av-2 และ roles in/out/solo; ไม่มี pageerror

Regression gates: timeline/media-clock P95 <50ms; source PTS error และ PTS-mapped/audio error P95 <200ms เพื่อครอบคลุมค่าชดเชย drift/decoder callback scheduling บน headless browser ตัวเลข gate ไม่ใช่คำรับรอง physical AV synchronization

## ทำซ้ำและ cleanup

`& .venv/Scripts/python.exe -m pytest tests/motion_capture/test_multisource_av_preview_browser.py -q -s`

ใช้ `motion_fixture_url` จาก existing test-owned Vite infrastructure และ `temp_capture_dir("multisource-av-")` สำหรับ MP4/WAV ทั้งหมด FFmpeg ทุกครั้งมี timeout; browser ปิดใน finally; context manager ล้าง media folder และ fixture server ล้างโฟลเดอร์ log/ปิด exact test process เมื่อ session จบ ไม่มี production Raw/Assets/Projects/Exports/registry mutation และไม่มี runtime restart จริง

มี passing exploratory runs ก่อน final run; รันใหม่เพราะเพิ่มการผ่าน cut จริง/phase metrics และ dedup repeated offscreen draws ไม่ได้รัน full suite/build/commit/push

## Jev และข้อจำกัด

Jev ก่อนเริ่ม: noul **0.81**, confidence **null**. ก่อน media tests: risk score **0.26**, confidence **0.78**; rerun score **0.66**, confidence **0.55**; final rerun score **0.39**, confidence **0.68**. หลังเขียนรายงาน quality score **3.62/4**, confidence **0.68**. ทุก call ตรวจผลก่อนรันเทสแยกคำสั่ง ใช้ regression/measurement gate ที่ผู้ใช้อนุญาตเมื่อ confidence null/<0.80; Jev อ่านเพียงสรุปข้อความ ไม่ได้ตรวจเฟรม/diff และผลไม่ใช่หลักฐาน AV sync

ไม่ได้วัด physical speaker latency/display presentation, voice-cut/WebAudio clock path, audio waveform capture, mobile/GPU/device อื่น, long session, production project หรือก่อน/หลัง CPU/FPS gain. ทดสอบ smooth540; ไม่อ้างว่าผลนี้รับรอง Master1080/ทุก quality mode

ไฟล์ใหม่: `frontend/multisource_av_preview.html`, `frontend/src/multisourceAvPreviewFixture.jsx`, `tests/motion_capture/test_multisource_av_preview_browser.py`, รายงานนี้
