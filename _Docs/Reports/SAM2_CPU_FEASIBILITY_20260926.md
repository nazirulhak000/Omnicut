# SAM 2.1 CPU Feasibility Spike — ผลวัดจริง 2026-09-26

ดำเนินการโดย: Cline (Claude) · รอบ: `SAM2-CPU-FEASIBILITY-SPIKE-20260926` · ปิดคำถาม Q3 ของรอบ `CUTOUT-TEMPORAL-QUALITY-PLAN-20260926`

## คำตอบสั้น

> **คุณภาพ = ผ่าน · ความเร็ว = ไม่ผ่านสำหรับงานสด · RAM = ไม่ใช่ข้อจำกัด**
> → ใช้ได้ **เฉพาะเป็น offline batch pre-process** ห้ามคิดว่าจะรันแบบ interactive/preview ได้

## เครื่องมือและอินพุต

| รายการ | ค่า |
| :--- | :--- |
| Engine | `sam2.1_hiera_tiny` (โมเดลเล็กสุดของ SAM 2.1) |
| Device / threads | CPU / 4 threads |
| Code commit | `2b90b9f5ceec907a1c18123530e92e794ad901a4` |
| Checkpoint SHA-256 | `7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69` |
| Harness | `tools/benchmark_cutout_tracker.py` (ใช้ตัวเดิม ไม่ได้เขียนซ้ำ) |
| เฟรม | 60 เฟรมจริงจากคลิปสินค้าแนวตั้ง 9:16 @ 30 fps = **2.0 วินาทีของวิดีโอ** |
| Prompts | 2 objects · สินค้าทรงกลม `(0.43, 0.49)` · ปากกาสีดำ `(0.75, 0.39)` |
| เครื่อง | AMD Ryzen 7 7735HS · RAM รวม 13.69 GiB · **RAM ว่างตอนเริ่ม 2.36 GiB** |

## ตัวเลขที่วัดได้

| ตัวเลข | ค่า |
| :--- | :-- |
| เวลาเริ่มโมเดล (startup) | **6.11 s** |
| เวลารวม 60 เฟรม | **715.61 s** (11m56s) |
| เวลาต่อเฟรม p50 | **11.47 s** |
| เวลาต่อเฟรม p95 | **15.59 s** |
| Peak RSS | **929.47 MiB** |
| ความครอบคลุมของ mask ต่ำสุด | 4.91% ของเฟรม |
| ความครอบคลุมของ mask สูงสุด | 12.49% ของเฟรม |

**ช้ากว่าเวลาจริง: 715.61 ÷ 2.0 = 358 เท่า**

## คำฉายเป็นเวลาจริง (30 fps, 4 threads, เครื่องนี้)

| ความยาวคลิป | เฟรม | เวลาที่ต้องใช้ (p50) |
| :--- | :--: | :-- |
| 2 วิ (ที่วัดจริง) | 60 | 11.9 นาที ✅ ตรงกับที่วัด |
| 5 วิ | 150 | **28.7 นาที** |
| 10 วิ | 300 | **57.4 นาที** |
| 15 วิ (ยาวที่สุดของรีวิว) | 450 | **86.0 นาที** |
| 60 วิ | 1800 | **5.7 ชั่วโมง** |

## คุณภาพการติดตาม — ผ่าน

ดูจาก contact sheet ที่เก็บไว้: `SAM2_CPU_FEASIBILITY_20260926_contact_sheet.png` (เฟรม 0 / 11 / 23 / 35 / 47 / 59)

| เกณฑ์ | ผล |
| :--- | :-- |
| ติดตามสินค้าทรงกลมตลอด 60 เฟรม | ✅ ขอบคม ไม่หลุด ไม่ขยายมือ |
| แยกมือออกจากพื้นหลังได้ | ✅ มือถูกตัดทิ้งตลอด |
| ติดตามปากกาสีดำได้ | ✅ ติดตามทั้งที่เคลื่อนที่ข้ามสินค้า |
| mask ไม่ระเบิด/ไม่หาย | ✅ coverage อยู่ระหว่าง 4.91%–12.49% แคบ ไม่มีอาการขยายหรือยุบ |
| รอยต่อระหว่างเฟรม | ✅ ต่อเนื่อง ไม่มีการกระพริบของ mask |

> ข้อจำกัดที่ probe ระบุไว้เอง: *"binary segmentation is not alpha matting"* — ได้ mask หยาบ ไม่ใ���่ขอบ alpha แบบ matting ต้องมีขั้นตอน refine ต่อ (เช่น `scripts/cutout_temporal.py`)

## ข้อสรุปสำหรับ Q3

1. **SAM 2.1 เล็ก (tiny) รันบน CPU ของเครื่องนี้ได้จริง** — ไม่ OOM แม้ RAM ว่างเหลือแค่ 2.36 GiB (ใช้จริงไม่ถึง 0.93 GiB)
2. **RAM ไม่ใช่ข้อจำกัด** — peak 929 MiB เหลือเฟื้อมาก ข้อจำกัดคือ **CPU เวลา**
3. **คุณภาพติดตามผ่าน** ใช้เป็นตัวช่วยหาขอบ/ติดตามวัตถุได้จริง
4. **ใช้งานได้เฉพาะแบบ offline batch** — ต้องรันเป็น worker แยกแบบ progress ได้ เหมือน `background_isolation_video_worker.py` ที่มีอยู่แล้ว
5. **ห้ามคิดว่า interactive ได้** — 86 นาทีต่อคลิป 15 วินาที ใช้ใน Preview หรือแก้ขอบแบบทันทีไม่ได้
6. **ทางออกที่ควรพิจารณา** ถ้าต้องเร็วขึ้น: ลด `image_size`, ลดจำนวนเฟรมที่ยิง (เช่น ทุก 3 เฟรมแล้ว interpolate), หรือเพิ่ม threads จาก 4 เป็น 8

## ไฟล์หลักฐาน

| ไฟล์ | ที่อยู่ |
| :--- | :--- |
| รายงานนี้ | `_Docs/Reports/SAM2_CPU_FEASIBILITY_20260926.md` |
| Contact sheet (หลักฐานภาพ) | `_Docs/Reports/SAM2_CPU_FEASIBILITY_20260926_contact_sheet.png` |
| ผลดิบจาก harness | `.tmp/cutout_tracker_probe/report.json` (ลบได้ เพราะ regenerate ได้) |
| เฟรมอินพุต | `.tmp/cutout_tracker_probe/` (ชั่วคราว) |

## วิธีทำซ้ำ

```powershell
# ต้องใช้ venv แยกเสมอ ห้ามติดตั้ง torch ลง .venv หลัก
tools\cutout_runtime\.venv\Scripts\python.exe tools\benchmark_cutout_tracker.py `
  --frames .tmp\cutout_tracker_probe `
  --checkpoint 03_Projects\.cache\cutout-models\sam2.1_hiera_tiny.pt `
  --prompts .tmp\cutout_tracker_probe\prompts.json `
  --report .tmp\cutout_tracker_probe\report.json `
  --contact .tmp\cutout_tracker_probe\contact_sheet.png
```
