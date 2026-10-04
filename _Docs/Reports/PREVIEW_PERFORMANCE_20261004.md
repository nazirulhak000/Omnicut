# Preview performance — CODEX-PARALLEL-EDITING-QUALITY-20261004 / A2

ดำเนินการโดย: Codex (GPT-6)

## ผลและขอบเขต

พบการค้นหา O(N) ทุก RAF callback: `timelineMath.getDrawPlan()` ค้นจากท้าย, preroll ค้นจากต้น, และสร้าง `Object.entries(videoEls)` เพื่อหยุด decoder ที่ไม่อยู่ในแผน แม้ว่าปกติเล่นอยู่เพียง 1–2 คลิป

เพิ่ม `createPreviewTimelineIndex()` ซึ่งค้นเวลาด้วย binary search แล้วส่งเฉพาะคลิปปัจจุบันและคลิปก่อนหน้าเข้า `timelineMath.getDrawPlan()` เดิม สูตร source time, speed, freeze, motion time, transition/easing/alpha จึงใช้ implementation เดิมทั้งหมด ดัชนีสร้างครั้งเดียวต่อการเปลี่ยน segments; timeline ที่เวลาไม่เรียงหรือไม่ finite ใช้ full scan เดิม

เพิ่ม `pauseInactivePreviewVideos()` ตรวจเฉพาะ ID ที่อยู่ในแผนก่อนหน้าและหลุดจากแผนใหม่ ยังคงการหยุดทุก decoder เมื่อ pause/seek/source reload ตามเดิม ไม่เปลี่ยน master audio clock, drift thresholds, SFX/BGM scheduling, 30 FPS paint throttle, คุณภาพ raster หรือ preload policy

## CPU comparison

คำสั่ง: `node tools/benchmark_preview_scheduler.mjs`; Node CPU microbenchmark, 7 repetitions หลัง warmup, รายงาน median; synthetic timeline มี speed และ fade/cut; ไม่มี media I/O

| จำนวนคลิป | Lookup + preroll เดิม (ms / 12,000) | Indexed (ms / 12,000) | เร็วขึ้น | Pause scan เดิม (ms / 1,000) | Active-only (ms / 1,000) |
|---:|---:|---:|---:|---:|---:|
| 100 | 1.736 | 0.795 | 2.18× | 3.398 | 0.117 |
| 1,000 | 14.852 | 2.066 | 7.19× | 33.740 | 0.086 |
| 5,000 | 72.919 | 2.661 | 27.40× | 1,677.006 | 0.136 |

เป็นตัวเลข CPU เฉพาะการค้นเวลา/เลือก decoder ไม่ใช่ FPS ของโปรเจกต์จริง และ pause benchmark ใช้ decoder จำลองที่ paused จึงวัด overhead การ enumerate ที่สูญเปล่า ไม่ใช่เวลาหยุด hardware decoder

## Validation

- Node focused: **47 passed**, รวม regression ใหม่ 6 tests ใน `previewTimelineScheduler.test.js`; เทียบ output ทุก 30 FPS frame กับ implementation เดิมบน 120 clips, random/backward seek บน 250 clips, จุดเริ่ม/จบ/เลยขอบ, transition ทุกชนิด/easing, speed .5/1/1.5/2, freeze/held source, duplicate starts, gaps, nonmonotonic starts/ends, invalid timestamps และ pause เฉพาะ outgoing decoder
- Scoped `tests/test_preview_render_parity.py`: **205 passed**
- Existing Chromium real-media test `test_real_media_preview_seek_and_playback_at_scale[100]`: **1 passed**; ready **1,103.6 ms**, seek ไปคลิปท้าย **33.2 ms**, decoded **30 frames**, dropped **0**, JS heap **42,100,000 bytes**; ไม่มี pageerror
- Browser fixture สร้าง synthetic media ภายใน `temp_capture_dir`, context manager ล้างทั้งโฟลเดอร์หลังจบและปิด browser/Vite process ที่เทสสร้าง ไม่มี production media/registry mutation
- ไม่ได้เปลี่ยน image geometry/math จึงไม่เพิ่ม FFmpeg visual render อีกชุด; source fixture ของ browser ใช้ FFmpeg ตาม fixture เดิม
- Root ทำ production build หลังรวมงาน; ไม่รัน full npm/pytest, ไม่ commit/push, ไม่ติดตั้ง dependency หรือ restart runtime จริง

## ข้อจำกัดและ Jev

Chromium probe เป็นการทดสอบหลังแก้บน 100 คลิปจาก source สังเคราะห์เดียว ไม่ได้วัด browser before/after, long-session frame pacing หรือ A/V drift จากเสียงจริง และไม่รับรองว่าโปรเจกต์ production ทุกชนิดเล่นลื่นแล้ว ยัง mount/preload วิดีโอทุกคลิปตามเดิม; decoder virtualization, network contention, React tree และ cue/effect scanning ยังเป็นงานถัดไป

Jev ก่อนเริ่ม: noul **0.84**, confidence **null**; เดินต่อด้วย regression/measurement gate ที่ผู้ใช้อนุญาตไว้ ไม่ถือ noul เป็น confidence หรือหลักฐาน ก่อน browser media fixture: risk score **0.31**, confidence **0.74**, verdict **escalate**; browser test อยู่ใน shell ชุดเดียวกับคำสั่ง Jev จึงรันต่อก่อน agent ตรวจ gate (ข้อผิดพลาดการจัดลำดับ) แจ้ง root แล้ว ผู้ใช้ภายหลังอนุญาต regression/measurement gate เมื่อ confidence ต่ำกว่า 0.80 ด้วย ไม่รันทดสอบ browser ซ้ำเพราะไม่มีโค้ดเปลี่ยน ผลเป็นการตรวจจากสรุปข้อความ ไม่ได้อ่าน diff/ภาพเอง

Jev หลังเขียนรายงาน/เทียบก่อนหลัง: comparison noul **0.84**, confidence **null**; report quality score **3.76/4**, confidence **0.80**; ใช้การตรวจจากสรุปและไม่ถือ Jev เป็นหลักฐาน performance

## ไฟล์

- `frontend/src/components/SequencePlayer.jsx`
- `frontend/src/lib/previewTimelineScheduler.js`
- `frontend/src/lib/previewTimelineScheduler.test.js`
- `tools/benchmark_preview_scheduler.mjs`
- `_Docs/Reports/PREVIEW_PERFORMANCE_20261004.md`
