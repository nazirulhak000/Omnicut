# แผนงาน: ผนวกระบบ TikTok Pro Sharpness เข้าสู่ OmniCut Pro Studio (2026-10-12)

ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

## 🎯 1. วัตถุประสงค์ (Objective)
สร้างระบบ Video Enhancement ปรับปรุงความคมชัดของวิดีโอสำหรับลง TikTok (Unsharp Mask, BT.709 Color Primaries, H.264 High Profile, FastStart) ให้ใช้งานได้โดยตรงและครบวงจรในโปรแกรม OmniCut Pro Studio ทั้งผ่าน API, UI (Export Gallery 1-Click), และ HyperFrames Finalize Pipeline

## 🧱 2. สถาปัตยกรรมและการแบ่งเฟส (Phased Implementation)

### เฟส 1: Core Service Engine & Unit Tests
- สร้างโมดูล `scripts/tiktok_enhancer.py` (Production Core Service)
  - `enhance_video_for_tiktok(input_path, output_path=None, custom_opts=None)`
  - ปรับความคมชัด: `unsharp=5:5:0.8:5:5:0.3`
  - ปรับคอนทราสต์/สี: `eq=contrast=1.04:saturation=1.04`
  - ตรึงมาตรฐานสากล: `yuv420p`, `bt709`, `crf 18`, `preset medium`, `g 60`, `bf 2`
  - คอนเทนเนอร์: `+faststart` (moov atom at beginning)
  - รองรับ non-destructive (คงไฟล์เดิม สร้าง `_tiktok_sharp.mp4`)
- เขียนชุดทดสอบ unit test ใน `tests/test_tiktok_enhancer.py` (รันบน tmp_path และ clean up 100%)

### เฟส 2: FastAPI Router Endpoint
- เพิ่ม endpoint ใน `scripts/api_exports.py`:
  - `POST /api/exports/enhance-tiktok`
  - รับ payload: `{ "export_id": "...", "file_path": "..." }`
  - ตรวจสอบความปลอดภัย path ให้อยู่ใน workspace
  - เรียกใช้ `scripts/tiktok_enhancer.py`
  - ลงทะเบียนไฟล์ที่ enhance แล้วเข้า `_Docs/export_registry.json`
  - คืนค่าผลลัพธ์: `{ "success": True, "enhanced_path": "...", "specs": {...} }`
- เขียน API unit test

### เฟส 3: Export Gallery UI (Post Studio 1-Click Integration)
- อัปเดต `frontend/src/components/ExportGallery.jsx`:
  - เพิ่มปุ่ม `⚡ ปรับความคมชัด TikTok` ใน Post Studio การ์ดและโมดอลรายละเอียด
  - มีสถานะ Loading / Spinner ขณะกำลังแปลงไฟล์
  - แสดง Toast แจ้งเตือนเมื่อสำเร็จ และรีเฟรช Gallery ทันที
  - เพิ่ม Badge `[TikTok Sharp ✓]` สำหรับคลิปที่ผ่านการ enhance แล้ว
  - อัปเดต QR Code และลิงก์ดาวน์โหลดให้ชี้ไปยังคลิปที่ปรับปรุงแล้ว

### เฟส 4: HyperFrames Finalize Pipeline Hook
- อัปเดต `scripts/hyperframes_finalize.py` ให้มีตัวเลือก `auto_enhance_tiktok`
- ปรับให้คลิปที่ finalize เข้า `04_Exports/Ready_to_post/` สามารถ trigger TikTok sharp pass ได้ทันที

### เฟส 5: Verification & Quality Assurance
- ทดสอบการทำงาน End-to-End
- ตรวจสอบ Parity, Bitrate, Resolution (1080x1920 30fps), และ Cleanup ขยะทดสอบ 100%

---
