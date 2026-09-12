# 📋 OmniCut Pro Studio — Todo กลาง

สมุดบันทึกรอบงานที่ **ยังไม่เสร็จ** ของโปรเจกต์นี้ — ทุกงานต้องผ่านไฟล์นี้ก่อนแตะโค้ด

| ไฟล์ | ใช้ทำอะไร |
| :--- | :--- |
| **TODO.md** (ไฟล์นี้) | งานที่ยังไม่เสร็จ + Backlog — เขียนแผนลงที่นี่ก่อนลงมือ |
| [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md) | รอบที่ปิดแล้ว ย้ายบล็อกเต็มไปเก็บไว้ที่นั่น ห้ามแก้ย้อนหลัง |
| [TEMPLATE_MOTION_PLAN.md](file:///d:/Winona/Programmer/Capcut/TEMPLATE_MOTION_PLAN.md) | แผนยาวของงาน motion ข้อความ (Round 3–7) — เหตุผลและตัวเลขที่วัดมา |
| [SYSTEM_AUDIT_2026-09-09.md](file:///d:/Winona/Programmer/Capcut/SYSTEM_AUDIT_2026-09-09.md) | รายงาน DB/Infra/System audit เต็ม (4-agent, read-only) |
| [SYSTEM_AUDIT_FIX_PLAN.md](file:///d:/Winona/Programmer/Capcut/SYSTEM_AUDIT_FIX_PLAN.md) | แผนแก้ตาม audit ข้างบน แบ่ง 10 stream ขนาน + phase สำหรับยิง agent พร้อมกัน |
| [PRO_EDITOR_STYLE_PLAN.md](file:///d:/Winona/Programmer/Capcut/PRO_EDITOR_STYLE_PLAN.md) | แผนยกระดับคุณภาพการตัดต่ออัตโนมัติด้วย Editorial Style Preset กลาง |
| [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md) | กติกาว่าหนึ่งรอบทำยังไง ติ๊กยังไง ปิดรอบยังไง |

---

## สถานะรวม

---

- [x] Round HOOK-DEFAULT-5S-1 — ปรับค่าเริ่มต้น (default) ของป้ายฮุกพาดหัว (Hook Banner) เป็น 5.0 วินาทีตั้งแต่ตอนสร้างโปรเจกต์ (2026-09-11; frontend 151 passed, backend 157 passed, build pass)
- [x] Round ANALYTICS-HUB-1 — พัฒนาเมนูใหม่ "ศูนย์วิเคราะห์ข้อมูลและสถิติรวม" (Analytics & Operations Hub) รวมแดชบอร์ด 4 มิติ (Production, Tokens, Storage, Inventory) (2026-09-11; backend 4 passed, frontend 151 passed, build pass)
- [x] Round SETTINGS-TOKEN-REMOVAL-1 — ถอดแท็บและสถิติโทเคนออกจากหน้าตั้งค่าระบบ (System Settings) ปรับ Eyebrow และเมนูเป็น 'ตั้งค่าระบบ' เต็มรูปแบบ (2026-09-11; frontend 151 passed, build pass)
- [x] Round ANALYTICS-HEADER-DATA-FIX-1 — ตัด Header ซ้ำซ้อนใน AnalyticsHub + ปลดล็อกพอร์ต 8000 จาก process ค้าง ทำให้โหลดข้อมูลสถิติได้สมบูรณ์ 100% (2026-09-11; backend 4 passed, frontend 151 passed, build pass)
- [x] Round POSTED-ARCHIVE-STORAGE-1 — วิดเจ็ตสรุปจำนวนคลิปที่โพสต์แล้วและพื้นที่ประหยัดได้หากย้ายสำรอง (Archive & Storage Reclamation) บน Analytics Hub (2026-09-12; backend 4 passed, frontend 151 passed, build pass)
- [x] Round USER-GUIDE-1 — เมนูใหม่ "คู่มือใช้งาน" แนบในโปรแกรม + อธิบายโฟลว์หลักครบ 7 เมนู (2026-09-12; frontend 151 passed, build 3.47s)
- [x] Round ANALYTICS-CHARTS-1 — พัฒนาระบบกราฟเส้น กราฟโดนัท Funnel Chart และเกจวัดแบบ Pure SVG สไตล์ Dark Modern Glassmorphism สำหรับแดชบอร์ดทั้ง 4 แท็บ (2026-09-12; frontend 151 passed, backend 4 passed, build 3.44s, browser verified)
- [x] Round ANALYTICS-CHARTS-POLISH-1 — ปรับขนาดและจัดระเบียบเลย์เอาท์กราฟใน Analytics Hub ให้กระชับ สวยงาม พอดีสายตา ไม่ใหญ่เกินจำเป็น (2026-09-12; frontend 151 passed, build 3.25s, browser verified)
- [x] Round USER-GUIDE-2 — ปรับการ์ดเมนู 1-7 เป็น grid หลายคอลัมน์บนจอกว้าง กล่องกระชับตามข้อความ (2026-09-12; frontend 151 passed, build 3.87s)
- [x] Round USER-GUIDE-3 — กระชับทุกกล่องในคู่มือ (โฟลว์ 7 ขั้น, คลิปแรก, 4 เฟส, โฟลเดอร์, เช็กลิสต์, ปัญหา, FAQ) (2026-09-12; frontend 151 passed, build 3.69s)
- [x] Round USER-GUIDE-4 — ยกระดับคู่มือเป็น interactive (sticky TOC + scrollspy, เช็กลิสต์ติ๊กได้, การ์ดเมนู accordion, โฟลว์กดไปเมนูได้, ปัญหามีปุ่มลัด, FAQ ค้นหาได้) (2026-09-12; frontend 151 passed, build 4.22s)

---

## รอบงานถัดไป (Next Sprint: P0 Safety & UX Boosters)

### Round SAFE-1 — Disk Guard ก่อน Render & Auto-Snapshot CapCut Manifest 3 Versions

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: รอดำเนินการ

**เป้าหมาย:**
1. **Disk Guard ก่อน Render:** ตรวจสอบพื้นที่ว่างบนดิสก์ (`shutil.disk_usage`) ก่อนเริ่ม Render งานวิดีโอ 1080x1920 หากพื้นที่เหลือน้อยกว่า 3GB ให้แจ้งเตือนและระงับการเรนเดอร์ทันที ป้องกัน FFmpeg ค้างและไฟล์เสียหาย
2. **Auto-Snapshot CapCut Manifest:** ทำระบบ Rolling Backup สำรองไฟล์ `project.json` อัตโนมัติ 3 เวอร์ชั่น (`.bak1`, `.bak2`, `.bak3`) ทุกครั้งก่อนเซฟ ป้องกันไฟล์ Draft เสียหายจนกู้คืนไม่ได้

### Todo
- [ ] เขียน Disk Space Checker ใน `scripts/api_render.py` (ขั้นต่ำ 3GB)
- [ ] ทำ rolling 3-version snapshot ใน `ProjectManifest.save()`
- [ ] รัน Gate และทดสอบ unit test

---
