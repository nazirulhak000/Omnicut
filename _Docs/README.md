# Workflow ตัดคลิป TikTok (รีวิว/ขายสินค้า) — CapCut

> เอกสารนี้เป็น workflow ฝั่ง production/CapCut ที่เก็บไว้ใช้อ้างอิง สำหรับ Web Editor และโครงสร้างโค้ดปัจจุบันให้อ่าน [../README.md](../README.md), [../ARCHITECTURE.md](../ARCHITECTURE.md) และ [../TODO.md](../TODO.md) การตั้งค่า export มาตรฐานของระบบปัจจุบันคือ 1080x1920, H.264/AAC, 30 FPS

## Pipeline ต้นน้ำ → ปลายน้ำ

**ต้นน้ำ**
1. หาไอเดีย/เทรนด์ + สรุปจุดขายสินค้า (hook/CTA) → `03_Projects/<ชื่อ>/script_brief.md`
2. ถ่ายวัตถุดิบ (product b-roll, talking-head, unboxing) ส่วนใหญ่จากมือถือ
3. ไฟล์จากมือถือ sync เข้าเครื่อง → พักที่ `00_Inbox`
4. จัดเข้า `01_Raw/YYYYMMDD_ชื่อสินค้า-ประเด็น/` (Video / Photo / VoiceMemo)

**กลางน้ำ (ใน CapCut)**
5. Rough cut ตาม script
6. Fine cut: ตัด silence/dead air, hook 3 วิแรกต้องปัง
7. เสียง: เพลง/SFX จาก CapCut library ก่อน ถ้าไม่มีค่อยหยิบจาก `02_Assets/Music` หรือ `02_Assets/SFX`
8. ภาพ: text overlay ราคา/สเปค/CTA, sticker/meme, transition, color
9. Caption/subtitle (auto-caption CapCut แล้ว sync ทวน)
10. Branding: โลโก้/watermark จาก `02_Assets/Branding`, end-card CTA
11. Review รอบสุดท้าย (จังหวะ + compliance โฆษณาสินค้า)

**ปลายน้ำ**
12. Export 9:16 → `04_Exports/Ready_to_post`
13. ทำ/เลือก cover → `05_Covers_Thumbnails`
14. เตรียม caption+hashtag (`03_Projects/<ชื่อ>/caption_draft.txt`)
15. โพสต์ TikTok → ย้ายไฟล์ export ไป `04_Exports/Posted`
16. หลังโพสต์ 30 วัน: ย้าย raw ที่ใช้แล้วเข้า `06_Archive`, จด performance ใน `performance_log.md`

## กฎ: ใช้ของ CapCut เอง vs ต้องมีโฟลเดอร์ asset

**ใช้ CapCut built-in ได้เลย** — เพลง/SFX ทั่วไป, filter/effect, sticker พื้นฐาน, font มาตรฐาน, auto-caption, template สำเร็จรูป (sync ข้าม PC/มือถืออัตโนมัติ)

**ต้องมี `02_Assets/` เอง เฉพาะ:**
- เพลง/เสียง trending ที่โหลดมาเอง (ไม่มีใน CapCut lib หรือต้องเช็คสิทธิ์เพลงเพื่อขายสินค้า)
- โลโก้/watermark/แบรนด์ (CapCut ไม่มีให้)
- ฟอนต์แบรนด์เฉพาะ
- Template ที่ทำเอง reuse ข้าม draft (intro/outro/lower-third ขายสินค้า)
- **Raw footage ต้อง backup เอง** ห้ามพึ่ง CapCut cache อย่างเดียว (clear cache/ล้างเครื่องมีสิทธิ์หายหมด)

## Naming convention

- Raw folder: `YYYYMMDD_ชื่อสินค้า-ประเด็นสั้นๆ` เช่น `20260812_ลิปสติกABC-รีวิว`
- Export file: `YYYYMMDD_ชื่อสินค้า_hook-สั้นๆ_vN` เช่น `20260812_ลิปสติกABC_ทาแล้วลื่นมาก_v1.mp4`
- **ชื่อ draft ใน CapCut ต้องตรงกับชื่อโฟลเดอร์ project เป๊ะ** — ตามรอยง่ายตอนสลับแก้ PC/มือถือ

## Checklist ก่อนโพสต์ (ขายสินค้า)

- [ ] hook ติดใน 3 วินาทีแรก
- [ ] ราคา/โปรโมชั่น/CTA ขึ้นชัดบนจอ (ไม่ใช่แค่พูด)
- [ ] caption มี disclaimer ถ้าเป็นโฆษณา/#ad ตามที่ต้องใช้
- [ ] เสียง/เพลงไม่ติดปัญหาลิขสิทธิ์
- [ ] ลิงก์ในไบโอ/ตะกร้าอัพเดทตรงกับสินค้าที่พูดถึง
- [ ] cover thumbnail อ่านง่าย มีข้อความ/ราคาโดดเด่น

## Risk ที่ต้องเช็คก่อนทำ automation (script แก้ draft_content.json)

CapCut บนเครื่องนี้เก็บ draft เป็น cloud-synced cache (`.cloud_cache_xxxxxxxxxx`) ไม่ใช่ folder ตั้งชื่อตาม draft แบบเก่า → ต้องเช็ค CapCut Settings (local draft path) ก่อนเริ่มเขียน script ส่วนนั้น
