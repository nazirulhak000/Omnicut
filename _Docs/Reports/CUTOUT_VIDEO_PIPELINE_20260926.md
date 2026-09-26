# ผลตรวจ Cutout แบบวิดีโอ — 2026-09-26

ดำเนินการโดย: Codex (GPT-6)  
สถานะ: Pipeline ใช้งานได้และย้าย BLU01 แล้ว; QA ภาพจริงทุกช่วงยังเปิดอยู่ใน `TODO.md`

## สิ่งที่เปลี่ยน

- งาน Cutout ใหม่สตรีมภาพต้นฉบับผ่าน rembg ไปเป็น `cutout.webm` (VP9 alpha) หนึ่งไฟล์ต่อช่วงต้นฉบับ พร้อม manifest/checksum และ atomic publish; ไม่มีการเก็บ PNG รายเฟรมใน namespace ใหม่
- API เสิร์ฟ manifest และวิดีโอแบบ Range; Preview ใช้ HTML video วาด Canvas เมื่อเฟรมพร้อมจริง; Render ถอด alpha ด้วย `libvpx-vp9` และวางสินค้าเหนือเลเยอร์ข้อความ
- ไฟล์ PNG เก่ายังอ่านได้เพื่อเปิดโปรเจกต์เดิม; BLU01 ถูกย้ายโดยสำรอง `project.json` ก่อนเขียนค่าใหม่ และไม่ลบ source หรือ cache เก่า
- หลังพบว่าหน้า editor ที่เปิดค้างบันทึกค่า PNG เก่าทับโปรเจกต์และ cache ถูกล้าง ระบบ Editor จึงตรวจ manifest ของ artifact ที่ระบุว่า `ready` ทุก 15 วินาที; หากไฟล์หาย สถานะเป็น `quality_failed`, Preview ไม่เผยพื้นหลังต้นฉบับ และ Render ไม่อ้างว่าพร้อมใช้งาน

## หลักฐานจาก BLU01

| ช่วงต้นฉบับ (วินาที) | คลิปที่ใช้ | เฟรม | WebM (MiB) |
| --- | --- | ---: | ---: |
| 5.460–16.642 | 2 clips | 335 | 2.62 |
| 22.000–26.720 | 1 clip | 142 | 2.12 |
| 45.000–51.660 | 1 clip | 200 | 1.33 |
| 65.000–70.700 | 1 clip | 171 | 1.83 |

รวม 4 วิดีโอ / 848 เฟรม / 8,284,446 bytes (7.90 MiB). ทั้ง 5 clip ใน `project.json` ชี้ artifact รุ่น 2 ที่มีสถานะ `ready`; ตรวจ SHA-256 ทั้ง 4 ไฟล์ตรงกับ manifest และมี backup ก่อนแก้ไข 2 รุ่นใน `06_Archive/cutout_project_backups/`. ตัวเลข 341.66 MB / 852 ไฟล์ในภาพหน้าจอเป็นสถานะเดิม จึงใช้เป็นข้อมูลอ้างอิงจากภาพ ไม่ใช่การวัด cache เดียวกันก่อนและหลังด้วยเครื่องมือ.

เรนเดอร์ส่วนตัวอย่างของคลิปจริง 0.5 วินาทีที่ source time 22.0 วินาทีเป็น MP4 สำเร็จ ตรวจภาพที่เวลา 0.2 และ 0.4 วินาทีแล้วเห็นสินค้าเคลื่อนไปตามวิดีโอโดยมี mood background แทนพื้นหลังเดิม. ไฟล์ทดลองอยู่ใน `.tmp/` ระหว่างตรวจและลบแล้วทั้งหมด. ทดสอบ FFmpeg กับ fixture ยังตรวจพิกเซล alpha/composite และ 30 FPS; Chromium fixture ตรวจ Canvas ที่ใช้ alpha video จริงและ HTTP Range 206.

เปิด Chromium Preview โดยเสิร์ฟ WebM จริงของ BLU01 และคลิปต้นฉบับช่วงเดียวกันครบทั้ง 4 source windows; เห็นพื้นหลัง mood `#0B1220` และวัตถุที่แยกออกในทุกช่วง. ช็อตที่ถือวงกลมระบายความร้อนแยกตัววงกลมออก แต่ไม่เก็บมือและโทรศัพท์ที่อยู่ฉากหลัง; จึงยังต้องให้ผู้ใช้ตรวจว่าการเลือกวัตถุตรงเจตนาของงาน และยังไม่กล่าวว่าคุณภาพ mask เทียบเท่า CapCut ทุกช็อต. ลบคลิป ภาพ และสคริปต์ probe ใน `.tmp/` ทั้งหมดหลังตรวจ.

## ผลทดสอบ

- Focused backend: `47 passed, 3 skipped`, warning เดิมของ Starlette 1 รายการ
- Frontend `npm test`: `316 passed`; Chromium ตรวจกรณี artifact หาย `2 passed`; `npm run build` ผ่าน (มี font URLs ที่ Vite รอ resolve ตอน runtime ตามเดิม)
- `compileall`, API import (`211 routes`) และ `git diff --check` ผ่าน
- Full backend gate ยังไม่ผ่าน: รอบแรกหยุดที่ `test_editor_controls_browser.py::test_inspector_panel_visible_controls_have_accessible_names[text_overlay]` เพราะ Text Overlay Inspector มี input ไม่มี accessible name; เป็นส่วนที่อยู่นอกการแก้ Cutout. เมื่อแยก module นี้ออก suite ที่เหลือ `1797 passed, 7 skipped, 34 warnings` ใน 9 นาที 50 วินาที.

## เหตุการณ์ระหว่างตรวจ

หลังการย้ายรอบแรก โปรเจกต์ BLU01 ถูกเขียนอีกครั้งเวลา 14:30 ด้วย artifact PNG รุ่นเก่า และ `03_Projects/.cache` ว่างตั้งแต่ 14:39. จึงหยุดการตรวจ Preview จริง ไม่ใช้ข้อมูล `ready` เดิมเป็นหลักฐานว่าระบบยังพร้อม. ผู้ใช้ยืนยันว่าปิดหน้าแก้ไขแล้ว จึงสร้าง artifact วิดีโอและสำรองโปรเจกต์จากสถานะล่าสุดอีกครั้ง. งานจบเวลา 15:01; ตรวจ artifact/project JSON/Checksum หลังจบผ่านทั้งหมด.

## งานที่ยังต้องตรวจ

- เปิด BLU01 ใน editor แล้วเล่น/scrub ที่ต้น กลาง ท้าย และรอยต่อของ Cutout ทั้ง 4 ช่วง; เทียบ Preview กับ Export ณ เวลาเดียวกัน รวมกรณีข้อความอยู่หลังสินค้า
- วัดความนิ่งของขอบในช็อตเคลื่อนไหวเร็ว; temporal smoothing ปัจจุบันลดการแกว่งเล็กน้อย แต่ยังไม่พิสูจน์ว่าให้คุณภาพเทียบเท่า CapCut ทุกฉาก และยังไม่ได้ทำ scene cut reset
- เก็บเวลาประมวลผล/Render ด้วยการวัดจริงก่อนกล่าวอ้างเรื่องความเร็ว และให้ full backend gate ผ่านก่อนปิดรอบใน `HISTORY.md`
