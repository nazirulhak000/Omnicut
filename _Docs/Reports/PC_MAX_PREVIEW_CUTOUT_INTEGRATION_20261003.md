# ผลพัฒนา Preview / Cutout / SAM2 สำหรับ PC

วันที่: 2026-10-03 · ดำเนินการโดย: Codex (GPT-6), preview / cutout_playback / sam2_integration และ root ผู้รวมงาน

## สิ่งที่เปลี่ยน

- พรีวิวค่าเริ่มต้น **ชัด 1080p** เล่นและหยุดด้วย Canvas backing 1080×1920 จาก Master; เลือก **ลื่น 540p** ได้ และจำคุณภาพในเครื่องนี้
- พิกัดแก้ไขยังเป็น 540×960 จึงรักษาฟอนต์ ตำแหน่ง ขนาด และ safe zone; offscreen, matte, Spotlight และ LUT ใช้ backing ตามโหมด
- โหมด 1080p เลือก Cutout alpha Master; ถ้ามีเพียงไฟล์พรีวิว ป้ายแสดงข้อเท็จจริง ภาพหยุดจาก Master แบบเดิมยังใช้ได้ในโหมด 540p
- แก้ Cutout กระพริบที่ความเร็วทศนิยมด้วยเวลาของเฟรมที่ decoder นำเสนอจริง ไม่ลดเกณฑ์ตรวจเฟรม
- เลือกจุดสินค้าแล้วพรีวิวหยุดและแสดงต้นฉบับที่เฟรมเริ่มต้นตรงกับ worker ของช่วงตัด (รวมการ reuse และโหมดเฉพาะช่วงข้อความ) รองรับจุดสินค้าและ Shift/Alt-click จุดที่ไม่ต้องการ รวมหลายจุดได้แม้ Cutout เดิมล้าสมัย; ระหว่างเลือกใช้ Master แม้เลือกคุณภาพ 540p แล้วกลับไป proxy หลังเลือกเสร็จ; พิกัดย้อน zoom/pan/mirror/rotation กลับสู่ worker letterbox และ marker แปลงกลับตามภาพ
- ไม่รับจุดที่กำกวมระหว่างรอยต่อสองคลิป; ภาพตรวจตอนหยุดใช้ข้อจำกัด blur/Cutout เดียวกับ playback
- รวม frontend normalization และปฏิเสธ engine/model คนละตระกูล โดยรักษาข้อมูล legacy rembg/u2net; แก้ toast ที่เข้าไม่ถึงของ ContentTracker
- SAM2 ใช้ runtime/checkpoint จาก workspace/environment, ตรวจ CUDA จริง และไม่ใช้ tiny แทนโมเดลอื่นที่ไม่มีไฟล์
- worker letterbox ตรงสัญญาจุดสินค้า, cache identity SAM2 เปลี่ยนตาม geometry/points; alpha นอก active intervals โปร่งใส แต่ยังติดตามทั้งช่วง จึงไม่ได้ลดจำนวน inference ตามจำนวนเฟรม active
- input frames SAM2 เก็บใน RAM ส่วน inference/state ยังอยู่บน CUDA; preflight และ worker ตรวจความจุจริง รวม duration ที่ API ต้อง probe เมื่อไม่ได้ระบุ

## ผลวัด Preview

Chromium headless, timeline สองคลิป 1080×1920 และ 1920×1080 พร้อมรอยต่อ circleopen ทั้งสองโหมดในตาราง **decode Master เหมือนกัน** เพื่อวัดภาระ Canvas; การใช้ proxy ทดสอบแยกด้วย API จำลองที่ส่งไฟล์ proxy จริง

| รายการ | 540p | 1080p |
|---|---:|---:|
| เฟรมที่วัด | 180 | 169 |
| เวลา paint p50 | 4.1 ms | 9.0 ms |
| เวลา paint p95 | 10.7 ms | 24.6 ms |
| ช่องว่าง callback p95 | 18.0 ms | 26.9 ms |
| ช่องว่างเกิน 50 ms | 0 | 0 |
| decoder dropped frames | 0 ทั้งสองคลิป | 0 ทั้งสองคลิป |
| เปิด fixture จนพร้อม | 255.5 ms | 227.6 ms |
| seek + capture | 72.6 ms | 121.9 ms |
| Canvas หลัก RGBA (คำนวณ) | 1.98 MiB | 7.91 MiB |
| JS heap ที่ browser รายงาน | 26,000,000 B | 26,000,000 B |

ไม่ได้วัด peak RAM รวม browser/decoder/GPU; RGBA เป็นขนาด surface เดียว ไม่ใช่หน่วยความจำทั้งหมด ตัวเลขเป็น fixture จำลอง ไม่รับประกันทุก codec/จำนวนคลิป/เอฟเฟกต์

### ภาพเทียบ FFmpeg

จับ Canvas 1080×1920 **ระหว่างเล่นจริง** ก่อน/ใน/หลังรอยต่อ cut, circleopen และ dissolve; มี trim, zoom, mirror และสองอัตราส่วน source

- Cut / circleopen เปรียบเทียบ RGB: normalized MAE 0.0426–0.0496 และ 0.0427–0.0493 ตามลำดับ (เกณฑ์เดิม <0.08)
- Dissolve หลังปรับทั้งภาพให้เป็น YUV420 แบบ export: MAE 0.0407–0.0599 (เกณฑ์ <0.08); RGB ของ Canvas กับสี export มี chroma subsampling ต่างกัน จึงไม่กล่าวอ้างว่าทุกพิกเซลสีเหมือนกัน
- แยกตรวจ mask dissolve ขาวดำที่ 1080p กับ FFmpeg จริง: MAE **0.0000072338** (เกณฑ์ <0.01); ใช้ float32 `frand()` ตาม [FFmpeg vf_xfade.c](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavfilter/vf_xfade.c)

## Cutout clock

ก่อนแก้ fractional speed 1.3155 เห็นสินค้า 44/60 และ 47/60 เฟรม ในรอบตรวจนี้ หลังแก้เกณฑ์ยังเป็น visible ≥54/60 และ seeks ≤2

| ความเร็ว | 540p visible | 1080p visible | seeks เพิ่มในช่วงวัด |
|---|---:|---:|---:|
| 0.5× | 60/60 | 60/60 | 0 |
| 1× | 60/60 | 60/60 | 0 |
| 1.3155× | 60/60 | 60/60 | 0 |
| 2× | 58/60 | 60/60 | 0 |

Node clock tests 11 ผ่าน และ browser Cutout 9 ผ่าน; การแก้ใช้ recovery เมื่อ decoder drift เกิน 1.5/fps, ชดเชย rate สูงสุด ±10% ตาม presented frame และรักษา paused tolerance เดิม

## SAM2 GPU ผ่าน API จริง

Runtime แยก Python 3.10.11 / torch 2.6.0+cu124 / RTX 4060; ใช้ checkpoint ที่มีอยู่ ไม่ติดตั้งหรือดาวน์โหลดในรอบนี้

| รายการ | 9:16 source เต็ม 12 เฟรม | Square source → letterbox, active 6/12 |
|---|---:|---:|
| Product IoU เฉลี่ย | 92.31% | 88.13% |
| Product IoU รายเฟรม | 87.18–98.61% | 87.84–88.35% |
| พื้นที่มือที่รั่วใน ROI ทดสอบ | 0% | 0% |
| dispatch รวม | 4.706 s | 4.426 s |
| worker | 3.137 s | 2.895 s |

- positive alpha ≥240, negative alpha ≤16; ตรวจ alpha Master และ proxy จากไฟล์จริงผ่าน HTTP media endpoint
- นอก active intervals Master alpha 0; proxy VP9 ปัดเป็น 1/255 ได้
- cache reuse ไม่เปลี่ยน mtime; เปลี่ยน positive/negative points แล้ว artifact ID เปลี่ยน
- CUDA peak allocated **661.34 MiB**, reserved **806 MiB**; input offload ลด allocation 120 MiB ใน fixture นี้
- RAM input ประมาณ **12 MiB/เฟรม + 1 GiB overhead** ของทั้ง source window; ตัวอย่าง 60 s @30 FPS ≈22.09 GiB แม้ active intervals สั้นกว่า ไม่ใช่ผลวัด peak RAM รวม
- ทดสอบ GPU ล่าสุด **2 passed / 12.27 s**; backend ที่เกี่ยวข้องรวม API/refactor **99 passed, 6 skipped** โดย GPU เป็น opt-in

ตัวเลขคุณภาพเป็นวัตถุจำลองเยื้องศูนย์กับมือสัมผัสสินค้า ไม่ครอบคลุมทุกสินค้าหรือทุกวัตถุดิบจริง คู่มือย้ายเครื่องและตั้ง runtime/checkpoint อยู่ที่ [tools/cutout_runtime/README.md](../../tools/cutout_runtime/README.md)

## Gate รวม

- Preview + point picking + parity snapshot ก่อนเสริม Master picker: **206 passed / 74.91 s** รวมการเลือกหลายจุดหลัง artifact ล้าสมัย, resize/save/reload และ zoom/pan/mirror ทั้ง 540p/1080p
- Frontend **491 passed**, build ผ่าน
- compileall scripts/tools และ API import **216 routes** ผ่าน
- Reference-frame regression: **3 Node tests + 6 browser cases passed**; จุดยังเป็น normalized points ระดับโปรเจกต์ ใช้ร่วมกับทุก source window ไม่ใช่จุดแยกรายคลิป/รายวัตถุ/รายเวลา
- Baseline รวมก่อนเก็บ Master picker: **2284 passed, 1 failed, 11 skipped /612.93s**; ไฟล์โค้ด 726 ไฟล์ไม่เปลี่ยนระหว่างรัน failure เป็น source assertion เงื่อนไขเสียงเดิม ปรับให้ตรวจ guard ใหม่แล้ว parity189 ผ่าน
- Final full pytest: **2286 passed, 11 skipped, 32 warnings /548.85s** ไม่มี failure; SHA-256 ของ source 726 ไฟล์ตรงก่อน/หลังรัน
- `git diff --check` ผ่าน; fixtures ใช้ TemporaryDirectory และ cleanup อัตโนมัติ ไม่สร้างผลงานทดสอบในโฟลเดอร์ export/project จริง
- GPU acceptance 2 เคสรันแยกด้วย opt-in และผ่านแล้ว ชุด pytest ปกติคง deterministic/offline; warnings ที่เหลือเป็น datetime/Pillow/librosa deprecation และ audio fallback เดิม
- ไม่มี commit/push ในรอบนี้ งาน audit อื่นของ Claude/Cline ที่ยังมีหัวข้อเปิดอยู่คงแยกไว้ใน TODO

Jev เป็นผู้ตรวจข้อความ ไม่ใช่หลักฐานภาพ: scope integration risk 2.25/4 confidence 0.59; FFmpeg temp probe risk 0.45/4 confidence 0.62; preview risk ก่อน FFmpeg 0.13 confidence 0.89; SAM2 final quality 2.83/4 confidence 0.78 ผู้ใช้ยืนยันขอบเขต implementation แล้ว ใช้ผลทดสอบจริงตัดสิน gate

ปิด 5 รอบ Codex ที่เกี่ยวข้องแล้วใน TODO/HISTORY พร้อมชื่อเอเจนต์และโมเดล; ลบ logs/spec ชั่วคราว 6 ไฟล์หลังบันทึกตัวเลขตรวจจริงไว้ในรายงานนี้ ไม่มีโฟลเดอร์ทดสอบ high-resolution/subject-points/cutout-video ของรอบค้าง
