# แผนพรีวิวเฟรมคมชัด 1080p เมื่อหยุดภาพ

วันที่: 2026-09-29  
ดำเนินการโดย: Codex (GPT-6)  
สถานะ: ปิดรอบแล้ว 2026-10-03 · ดำเนินการโดย: Codex (GPT-6)

## เป้าหมาย

เมื่อหยุดเล่นหรือ seek เพื่อเช็กรายละเอียด ให้พรีวิวเฟรมระดับ 1080×1920 จากไฟล์ Master จริง ไม่ใช่ขยาย Proxy 540p ส่วนระหว่าง Playback ให้ใช้เส้นทางพรีวิวเดิมเพื่อคงความลื่นไหล

## สิ่งที่ตรวจพบ

- `SequencePlayer.jsx` ใช้ Canvas logical size 540×960 และเลือก Proxy 540p เมื่อมีไฟล์
- `scripts/video_editor.py` เรนเดอร์ไฟล์โพสต์ที่ 1080×1920; Draft ปัจจุบัน 720×1280
- `SequencePlayer` มีเส้นทาง `captureCoverFrame()` ที่โหลด Master แล้ววาดเฟรมที่ 1080×1920 ด้วย renderer เดียวกับ Timeline ซึ่งเป็นฐานสำหรับภาพตรวจความคมชัด
- `preview_render_parity.md` และ `font_text_visual_contract.md` กำหนดสัดส่วน typography/ตำแหน่งไว้ ต้องรักษาเดิม ห้ามขยายขนาดตัวอักษรเมื่อเพิ่มความละเอียด

## แนวทาง

1. ทำภาพ high-quality still preview จาก Master ที่ playhead ปัจจุบัน เมื่อหยุดหรือหลัง seek/แก้ไขแล้วนิ่งตามช่วง debounce
2. ใช้ภาพดังกล่าวเป็น overlay แบบ `pointer-events: none` เหนือ canvas เดิม เพื่อรักษา geometry สำหรับ selection, drag, snap และ hit testing
3. ซ่อนภาพคมชัดระหว่าง Playback และใช้ Canvas/proxy 540p ตามเดิม
4. ผูกทุก capture กับ revision key; เมื่อ playhead, source หรือ state ภาพเปลี่ยน ให้ทิ้งคำตอบเก่าที่มาช้าและไม่แสดงเฟรม stale
5. มีทางเลือกปิด still preview คุณภาพสูง และ fallback ไปภาพเดิมเมื่อ capture ไม่สำเร็จ
6. ใช้ค่า position/font scale เดิม; ปรับเฉพาะความละเอียดการวาดเฟรมและแหล่งวิดีโอที่ใช้สร้าง still

## เกณฑ์ผ่าน

- หลังหยุด/seek แสดงเฟรมจาก Master ที่ 1080×1920 และไม่ใช้ proxy 540 เป็น input
- ระหว่างเล่นไม่ค้างรอ full-resolution capture และไม่มี still frame เก่าทับภาพปัจจุบัน
- การลาก/เลือก Caption, Overlay, Sticker และ Safe Zone ใช้พิกัดเดิม
- ภาพที่ตำแหน่งและเวลาตรงกันมี typography, framing, cutout, LUT, sticker และ overlay สอดคล้องกับ FFmpeg render ภายใน tolerance ที่เทสต์กำหนด
- มี browser evidence ของจริงและวัดเวลารอเฟรม/หน่วยความจำบนเครื่องนี้
- การทดสอบเขียนเฉพาะ `.tmp/`; cleanup ไฟล์ทดสอบทั้งหมดก่อนปิดรอบ

## ผลวัดระหว่าง implementation

- Browser test เทียบภาพหยุด 1080×1920 จาก Master กับ FFmpeg Post Render 1080×1920 ผ่าน **4/4** กรณี (trim, transition, compact layout, split)
- เวลาสร้างเฟรมใน browser harness **27–34 ms** สำหรับ synthetic fixture; PNG **47.4 KiB** ต่อเฟรมตัวอย่าง
- Raw RGBA ต่อ Canvas 1080×1920 เท่ากับ `1080 × 1920 × 4 = 8,294,400 bytes` หรือประมาณ **7.91 MiB**; high-res render ใช้ Canvas หลักกับ offscreen จึงมี raw pixel surfaces ราว **15.82 MiB** ระหว่างวาด ก่อนนับ video decoder, browser/GPU copies และภาพแสดงผล
- ตัวเลขหน่วยความจำเป็นการคำนวณขนาด raw surface ไม่ใช่ peak process RAM measurement; PNG size/latency มาจาก synthetic fixture ไม่ใช่คลิปทุก codec
- Automated gates: `npm test` **420 passed**, `npm run build` ผ่าน, Preview/Render parity **188 passed**, FFmpeg render behavior **24 passed**, Cutout parity **1 passed**, Editor performance **12 passed**
- Full backend suite: **2176 passed, 2 failed, 8 skipped, 32 warnings** ใน 555.68s; ทั้งสอง failure อยู่ที่ `_quality_setting()` ใน `tests/test_phase1_smoke.py` ซึ่งไม่รู้จัก hardware encoder `h264_nvenc` flag `-cq` ที่โค้ดปัจจุบันเลือก
- `git diff --check` พบ trailing whitespace ที่มีอยู่ก่อนรอบนี้ใน `HISTORY.md` และบล็อก QA เดิมใน `TODO.md`; ไม่แก้ทับประวัติ/ขอบเขตอื่น
- งานทดสอบใช้ temp directories และลบอัตโนมัติ; ไม่มี output ทดสอบค้างในโฟลเดอร์ผลงาน

## ขอบเขตที่ไม่เปลี่ยน

- Output ยังคง 1080×1920 ที่ 30 FPS
- ไม่เปลี่ยน Draft 720p, editing proxy, analysis proxy, AI model หรือ TTS
- ไม่เปลี่ยนฟอนต์, บท/คำซับ, ขนาด/ตำแหน่งข้อความ, safe zone หรือ motion contract
- รักษา diff เดิมใน working tree; ไม่ reset, stash หรือเขียนทับไฟล์ที่แก้ไว้

## ปิด gate และต่อยอด 2026-10-03

- ผลรวมสุดท้าย 2286 passed, 11 skipped ไม่มี failure; frontend491/build/compile/API216/diff check ผ่าน
- โหมดเริ่มต้นพัฒนาเพิ่มเติมเป็น Master playback 1080×1920 จริงพร้อมตัวเลือก540p; still preview เดิมยังใช้ใน540p
- Cutout clock, subject picking และ SAM2 GPU ผ่านการทดสอบ; ผลละเอียดและข้อจำกัดอยู่ที่ [รายงาน integration](../Reports/PC_MAX_PREVIEW_CUTOUT_INTEGRATION_20261003.md)
- ย้ายบล็อกรอบเต็มเข้า HISTORY.md แล้ว รักษาตัวเลข snapshot เดิมข้างต้นไว้ตามวันที่
