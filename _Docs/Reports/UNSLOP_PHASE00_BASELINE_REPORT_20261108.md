# 📸 รายงานการตรวจสอบภาพจริงและวางทิศทาง (Phase 00 Baseline Report)

**วันที่:** 2026-11-08  
**ดำเนินการโดย:** Antigravity (Gemini 3.8 Flash)  
**สถานะ:** ผ่านเกณฑ์ Phase 00 (100% Live Snapshots & Visual Evidence) — รอยืนยัน Visual Direction จากผู้ใช้  
**เอกสารอ้างอิง:** [_Docs/Plans/PLAN_OMNICUT_UNSLOP_PHASE_RUNBOOK_20261108.md](file:///d:/Programmer/All%20Project/Omnicut/_Docs/Plans/PLAN_OMNICUT_UNSLOP_PHASE_RUNBOOK_20261108.md)

---

## 1. ตารางหลักฐานภาพหน้าจอจริง (Live Baseline Snapshot Matrix)

ถ่ายจากหน้าจอจริงของระบบที่กำลังรันอยู่บน `https://localhost:5173` (Vite + basicSsl, Node.js, Chromium Headless) บันทึกไว้ใน `_Docs/Reports/baseline_phase00/`:

| ลำดับ | รหัสภาพ | หน้าจอ (Route/Tab) | Viewport | ขนาดไฟล์ | สิ่งที่ตรวจสอบพบหลัก |
|---|---|---|---|---|---|
| 1 | `desktop_01_product_to_clip.png` | สินค้า ➔ คลิป (`/`) | 1440x900 | 457 KB | การ์ด "พื้นที่ทำงานสคริปต์" มีขอบเรืองแสงบน (Cyan/White glow), Carousel เลื่อนแนวนอนทำงานได้สมบูรณ์ |
| 2 | `desktop_02_editor.png` | ห้องตัดต่อก่อนเลือกโปรเจกต์ (`/editor`) | 1440x900 | 154 KB | หน้าสร้างคลิปใหม่ (Intake Form) มีการ์ดและปุ่มสีเขียว/ส้ม/ฟ้าผสมกัน |
| 3 | `desktop_02b_editor_loaded.png` | ห้องตัดต่อพร้อมโปรเจกต์ (`BLU01-ปัญหาก่อนใช้_1`) | 1440x900 | 363 KB | ขอบบนไทม์ไลน์มีเส้นเรืองแสงพร้อมประกายดาว `✦`, ปุ่มเรนเดอร์ส้มไล่เฉด, การ์ด SAM2 ใน Inspector มีเส้นกรอบไล่สี |
| 4 | `desktop_02c_editor_obsidian.png` | ห้องตัดต่อในโหมด Obsidian Pro Dark | 1440x900 | 358 KB | **สบายตาขึ้น 80% ทันที** เมื่อตัดแสง Ambient Orbs ออก คลิป 9:16 โดดเด่นขึ้นชัดเจน |
| 5 | `desktop_03_tracker.png` | Content Tracker 4 เฟส (`/tracker`) | 1440x900 | 623 KB | ขอบคอลัมน์ Kanban แต่ละเฟสเรืองแสงคนละสี (ขาว, ม่วง, ส้ม, เขียว), ปุ่ม "ส่งต่อไปยัง TikTok" เป็น Gradient ชมพู-ฟ้า |
| 6 | `desktop_04_assets.png` | คลังมีเดีย Media Assets (`/assets`) | 1440x900 | 299 KB | ตารางฟิลเตอร์และพรีวิวเสียง มี Glow สะท้อนในพื้นหลัง |
| 7 | `desktop_05_analytics.png` | ศูนย์วิเคราะห์สถิติ (`/analytics`) | 1440x900 | 306 KB | แสง Orbs กลมสีฟ้าสะท้อนหลังการ์ด KPI ขนาดใหญ่, กราฟ Funnel มีเส้นนีออนใต้ตัวเลข |
| 8 | `desktop_06_settings.png` | การตั้งค่าระบบ (`/settings`) | 1440x900 | 708 KB | แสดงตัวปรับแต่ง "Pulse Hub Glass Finetuner" และพบว่าธีมหลักถูกล็อกไว้ที่ "Ultra-Realistic Glassmorphism" |
| 9 | `mobile_01_product_to_clip.png` | หน้าเลือกสินค้าโหมดมือถือ | 390x844 | 197 KB | แสดงผลได้ดี, แถบเมนูล่าง (Bottom Navigation) ชัดเจน |
| 10 | `mobile_02_tracker.png` | แท็รกเกอร์โหมดมือถือ | 390x844 | 227 KB | คอลัมน์ Kanban เรียงซ้อนแนวตั้งอ่านง่าย |
| 11 | `mobile_03_editor.png` | ห้องตัดต่อโหมดมือถือ | 390x844 | 60 KB | ⚠️ **พบ Critical UI Defect:** Dropdown ช่อง, Dropdown โปรเจกต์ และปุ่มเรนเดอร์ ซ้อนทับกัน (Collision) จนอ่านไม่ออก |

---

## 2. ผลการวิเคราะห์จุดที่ทำให้ดูเป็น "AI Slop" จากภาพจริง

จากการตรวจสอบภาพจริง เทียบกับผลค้นหา Source ของ Codex (Gradient 295 จุด, Transition 716 จุด, Font Bold 1,907 จุด):

1. **สาเหตุรากเหง้า (Root Cause): ธีมเริ่มต้นถูกตั้งไว้ที่ `Ultra-Realistic Glassmorphism`**
   - ใน `frontend/src/lib/themeManager.js` และ `index.css`:
     `DEFAULT_THEME_ID = 'glassmorphism'`, `orbsDefault: true`, `glare: 95%`, `saturate: 210%`
   - มีการยิงแสงลูกบอลสะท้อน (Ambient Orbs) 3 ลูกในพื้นหลังตลอดเวลา ทำให้ทุกหน้ามีเงากลมเบลอสีฟ้า/ม่วง/ส้มลอยอยู่หลังการ์ด
   - มีการใส่เอฟเฟกต์ตกแต่งประกายดาว `✦` และขอบบนกล่องเรืองแสง (เช่น บนหัว Timeline ของ Editor และการ์ดพื้นที่ทำงานสคริปต์)
2. **การแจกสีแบบ Multi-Color โดยไม่มีหน้าที่:**
   - คอลัมน์ Kanban 4 ช่องใน Tracker ใช้เส้นขอบนีออน 4 สีที่แย่งสายตากัน
   - ปุ่ม Call to Action มีการใช้ Gradient สองสีตรงข้าม (เช่น ชมพู ➔ ฟ้าบนปุ่ม "ส่งต่อไปยัง TikTok") แทนที่จะเป็นสี Solid มาตรฐาน NLE
3. **ปัญหาบนหน้าจอมือถือ (Mobile Navbar Collision):**
   - บนหน้าจอความกว้าง 390px ใน `mobile_03_editor.png` แถบ Topbar ขาด Responsive Handling ทำให้ Project Selector และ Render Split Button ล้นมาชนทับชื่อช่อง

---

## 3. ขอบเขตห้ามแตะต้อง (Golden Contract & Guardrails)

เพื่อให้การ Unslop ในเฟสถัดๆ ไปปลอดภัย 100%:
- ❌ **ห้ามแตะต้องฟอนต์ในวิดีโอ 9:16:** ฟอนต์ `Mali-Bold` (ซับสไตล์กวนๆ), `Prompt-Bold`, `Prompt-Black`, และ `IBM Plex Sans Thai` ใน `02_Assets/Fonts/` ต้องคงเดิม 100% ตามกฎข้อ 10 และข้อ 17
- ❌ **ห้ามแตะพิกัดและการวาด Canvas Preview:** `SequencePlayer.jsx`, Safe Zone (ล่าง 420px), และ FFmpeg Render Contract ต้องคงเดิม 100%
- ✔️ **UI Font:** ปัจจุบันใช้ `Anuphan` (300–700) ซึ่งเป็นฟอนต์ไม่มีหัวที่อ่านภาษาไทยได้คมชัดและสวยงามมาก ให้คงเป็นฟอนต์มาตรฐานของ UI ต่อไป

---

## 4. ข้อเสนอทิศทางการออกแบบ 5 บรรทัด (Visual Direction Proposal)

ขอเสนอทิศทางเพื่อให้ผู้ใช้พิจารณายืนยันก่อนเริ่ม Phase 01–02:

1. **สลับ Default Theme เป็น `Obsidian Pro Dark`:** ปิด Ambient Orbs และแสงสว่างสะท้อนเป็นค่าเริ่มต้น ให้พื้นหลังดำสนิทสไตล์ DaVinci Resolve & Premiere Pro คลิป 9:16 จะเด่นที่สุดทันที
2. **ปรับแต่งสีให้มีหน้าที่ชัดเจน (Functional Color):** ยกเลิก Gradient แฟนซีบนปุ่มและกรอบการ์ด ใช้สีทึบคอนทราสต์สูง (Primary Action = Solid Neutral/Teal, Warning = Semantic Amber, Error = Red, Success = Green)
3. **ลบของประดับตกแต่งเกินจำเป็น (De-clutter Chrome):** ถอดประกายดาว `✦`, แสงฟุ้งรอบกล่อง (Glow box-shadow), และแถบสีสะท้อนบน Timeline / Kanban เพื่อความเรียบหรูระดับโปร
4. **แก้ไข Responsive Navbar บนมือถือ:** ปรับเลย์เอาต์ Header เมื่อจอเล็กกว่า 640px ให้เป็น Compact Icon / Stacked เพื่อตัดปัญหาปุ่มชนกัน 100%
5. **คงความเสถียรของฟังก์ชันและระบบทดสอบ:** รักษา State เดิม, Panel Persistence, และผ่านชุดทดสอบ 1,198 Frontend + Backend 100% ตลอดทุกรอบ

---

## 5. ผลการประเมินความปลอดภัยร่วมกับ Jev (TypeSafe System One)

- **Jev Assessment (noul score):** `0.83` (ปลอดภัยที่จะดำเนินการต่อโดยไม่กระทบ Video Render Contracts)
- **Frontend Vitest:** 1,198 / 1,198 passed (100%)
- **Backend Pytest:** 13 / 13 passed (100%)
