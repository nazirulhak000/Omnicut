# GADGET Native Source Verify — 2026-09-19

ดำเนินการโดย: Codex (GPT-5)

## สถานะ

- Position: ย่อยข่าวและรีวิว Gadget ใหม่ให้เข้าใจง่ายใน 30–60 วินาที พร้อมมุมใช้จริง
- ผ่าน quality gate: 5 จาก 6 source
- ทุกไฟล์ที่ผ่านเป็น native `1920×1080` พร้อมเสียง และไม่ใช่ไฟล์ upscale
- Xiaomi ยังไม่ผ่าน: YouTube แสดง native 1080p format แต่ตอบ `HTTP 403` ก่อนเริ่มดาวน์โหลด
- ไม่มีการใช้ Xiaomi ไฟล์เก่า `640×360` แทน
- ยังไม่เริ่มแตกคลิป เพราะกำหนดให้ source ต้องครบก่อน

## Source ที่ผ่าน

| Brand | File | Video | Audio | Duration |
|---|---|---:|---|---:|
| Samsung | `samsung_webembedded_cdC0sSWM3Bo.mp4` | 1920×1080 AV1 | AAC | 116.38s |
| Google Event | `google_event_native_c84y9gAY90c.mp4` | 1920×1080 AV1 | AAC | 5050.27s |
| Google Pixel | `google_pixel_GNuXueQ1BYc.mp4` | 1920×1080 H.264 | AAC | 15.07s |
| Motorola | `motorola_Pi2eSkBP9dM.mp4` | 1920×1080 H.264 | AAC | 19.88s |
| Anker | `anker_native_WBsbzFxRy9I.mp4` | 1920×1080 AV1 | AAC | 130.17s |

## การคุ้มครองงานเก่า

- ย้าย output ตัดต่อ/upscale เดิมออกจากโฟลเดอร์ใช้งานไปที่ `.tmp/gadget_reset_discard_20260919/`
- เก็บ source ดิบเก่าไว้ชั่วคราว เนื่องจาก Xiaomi native ยังดาวน์โหลดไม่ได้
- ยังไม่มีไฟล์ใหม่ใน `04_Exports/`
- Source และ official footage ยังอยู่ภายใต้ `HOLD_FOR_RIGHTS_REVIEW` ห้ามเผยแพร่จนกว่าจะตรวจสิทธิ์และเพิ่ม commentary/remix ตามแผน
