# T6 — 1-Click Whole-Product Assembly

ดำเนินการโดย: Codex (GPT-6) · วันที่: 2026-10-04
อ้างอิง: MASTER-UX-ELEVATION-SURPASSING-CAPCUT-20261003 / T6

## การแก้ไข

- เพิ่ม `scripts/interactive_sam2_assembly.py` และเรียกจาก interactive SAM2 daemon
- เลือก seed ที่ผ่านคะแนนและ positive/negative prompt; proposal ใหญ่คะแนนต่ำใช้เป็นแนวทางกรอบเท่านั้น
- ขยาย bounding box 20% ต่อด้าน แล้วเรียก box-only prediction อีกหนึ่งครั้ง เพื่อไม่ล็อกผลไว้ที่ชิ้นส่วนเล็ก
- หาก box เลือกตัวถังแต่เว้นกลาง ให้ประกอบเฉพาะพื้นที่ปิดที่มี seed อยู่ภายใน ไม่เติมพื้นหลังภายนอกหรือรูอื่น
- รับผลใหม่เมื่อคะแนน, seed coverage และขอบเขตผ่าน guard; มิฉะนั้นใช้ seed เดิม
- Multi-point/negative correction ใช้ joint prompts ตามเดิม; ไม่ทำ automatic assembly เมื่อมีหลายจุด
- ใช้ torch inference mode และรีโหลด interactive daemon ให้ใช้โค้ดใหม่

## ผลตรวจที่เสร็จแล้ว

- Cutout/API/prompt regression: **62 passed, 3 skipped**
- รวม preview/render source contracts: **256 passed, 3 skipped**
- Frontend ครั้งแรก **597 passed**; gate ล่าสุด **614 passed, 0 failed**, production build ผ่าน
- Python compileall ผ่าน; import API server ผ่าน **225 routes**
- RTX 4060 + SAM2 จริง บนภาพสินค้าจำลอง: IoU ก่อน **0.334084**, หลัง **0.999817**
- พื้นที่ mask ก่อน **12,759 px**, หลัง **38,184 px**; คะแนน proposal ตัวถัง **0.847129** (ไม่ใช่คะแนนความถูกต้องของ mask ที่ประกอบแล้ว)
- Warm inference **14.6 ms**; HTTP daemon prediction **49.2 ms** ครั้งแรก และ **13.5 ms** ครั้งถัดไป
- FFmpeg encode/extract เฟรมและดูภาพก่อน/หลังจริงแล้ว ตัวถังและกลางสินค้าครบใน fixture นี้
- วิดีโอ/ภาพ probe อยู่ใน TemporaryDirectory ใต้ `.tmp/` และลบทันทีหลังตรวจ **100%**; ไม่แตะ export registry หรือคลังผลงานจริง

## ขอบเขตและข้อจำกัด

- ผล GPU เป็น synthetic fixture ไม่ยืนยันความถูกต้อง 100% กับคลิปพัดลมต้นเหตุหรือสินค้าทุกชนิด
- รอบนี้แก้การเลือกวัตถุ/เส้นขอบใน interactive single-frame preview ตามไฟล์เป้าหมายของ handover; video propagation worker ยังใช้ prompt pipeline เดิม
- ถ้าไม่มี mask ที่น่าเชื่อถือ หรือกรอบใหม่ไม่ผ่าน guard อาจยังต้องเพิ่มจุดด้วยมือ
- `git diff --check` ทั้ง working tree พบ blank line at EOF ใน `tests/test_api_background_isolation.py` ซึ่งเป็นงานเดิมก่อนรอบนี้; ไม่แก้ไฟล์ดังกล่าว
- Full pytest ครั้งแรก: **2432 passed, 4 failed, 12 skipped, 54 warnings** (817.03s); 4 failures คือ browser test คาดปุ่ม Play ที่ T5 ซ่อนใน pick mode
- ปรับเฉพาะ assertion ให้ตรวจว่าปุ่มถูกซ่อนและ pick mode เปิด; browser gate ซ้ำ **6 passed** (46.75s)
- Full pytest gate สุดท้าย: **2465 passed, 0 failed, 12 skipped, 54 warnings** (682.92s); warnings จำนวนเท่าเดิมจาก Starlette/audioread/Pillow ในชุดรวม
- รอบกลางที่ใช้ basetemp ภายใน `.tmp` ถูกยกเลิก เพราะ test_app_capture_rejects_non_tmp_output สมมติ tmp_path อยู่นอกโปรเจกต์; gate สุดท้ายใช้ temp ภายนอกที่ตั้งชื่อเฉพาะ และผ่านแล้ว
- ล้างพื้นที่ pytest ของรอบกลางและรอบสุดท้ายแล้ว โดยตรวจเส้นทางและชื่อเฉพาะก่อนลบ; `git diff --check` เอกสารรอบนี้และ browser test ผ่าน

## Jev

- ก่อนเริ่ม noul **0.73**, confidence **null**; ผู้ใช้อนุญาตให้เริ่มต่อหลังแจ้ง gate
- Before/after + ก่อน FFmpeg noul **0.66**, confidence **null**
- หลังเขียนโค้ด noul **0.55**, confidence **null**
- หลังเขียนรายงาน noul **0.35**, confidence **null**
- ใช้ authorization ของผู้ใช้สำหรับรอบ T6; ผล Jev เป็นคำแนะนำข้อความ ไม่ใช่หลักฐานภาพ

## ทำซ้ำการตรวจ

ใช้ cutout-runtime Python รัน `tools/probe_interactive_sam2_assembly.py` ใน terminal ที่มี stdin;
utility สร้าง fixture ชั่วคราว ตรวจ GPU/HTTP/FFmpeg และรอ Enter หลังตรวจเฟรมเพื่อ cleanup
