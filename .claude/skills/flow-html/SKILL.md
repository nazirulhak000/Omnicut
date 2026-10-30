---
name: flow-html
description: >-
  ออกแบบและสร้างแผนผังสถาปัตยกรรม ลูปกระบวนการทำงาน (Pipeline/Workflow/SOP) ในรูปแบบ Interactive HTML Dashboard ระดับ Pro Studio
  (Dark Cyberpunk/Obsidian, Connected Visual Node Chain, Interactive Mermaid.js พร้อม Zoom/Pan, 5-Stage Phase Deep-Dive, Data Contracts Schema & Live ID Simulator, 1-Click Master Prompt Library)
---

# 🌊 flow-html — Interactive Architecture & Pipeline Flow Dashboard Skill

สกิลมาตรฐานสำหรับออกแบบ สร้าง และส่งมอบแผนผังกระบวนการทำงาน (Pipeline Workflow), สถาปัตยกรรมระบบ (System Architecture), และคู่มือปฏิบัติงาน (Interactive SOP) ในรูปแบบ **Interactive HTML Dashboard ระดับ Pro Studio** หน้าเดียวจบ (Single-File Self-Contained) ที่สวยงาม อลังการ ครบถ้วน และใช้งานได้จริงทั้งสำหรับมนุษย์และ AI

---

## 🎯 1. วัตถุประสงค์และการใช้งาน (When to use /flow-html)

เรียกใช้สกิล `/flow-html` เมื่อต้องการ:
1. **สร้าง Flowchart สถาปัตยกรรมระบบหรือกระบวนการทำงาน (Pipeline)** ที่มีหลายขั้นตอน ให้สวยงามระดับ Master Dashboard
2. **สร้าง Interactive SOP Dashboard** ที่เปิดดูในเบราว์เซอร์แล้วเห็นภาพรวมได้ทันที มีทั้ง Visual Node Chain, Interactive Mermaid.js Graph, เจาะลึกรายขั้นตอน (Step-by-Step), พจนานุกรมรหัส (Data Matrix & Simulator), และชุดคำสั่งสำเร็จรูป (Prompt Library)
3. **ผสาน Mermaid.js ในรูปแบบ Interactive** มีปุ่ม Zoom In, Zoom Out, Reset, Fit Width และระบบ Pan ด้วยการลากเมาส์
4. **ทำกล่องก๊อปปี้คำสั่ง 1-คลิก (1-Click Copy with Toast)** ให้ผู้ใช้หรือผู้ควบคุมงานคัดลอกพรอมต์/สคริปต์ไปสั่งงาน AI ได้ทันทีโดยไม่ตกหล่น

---

## 🎨 2. Visual & Architectural Standard (Pro Studio Aesthetic)

เอกสาร HTML ที่สร้างจากสกิลนี้ต้องยึดถือมาตรฐานความสวยงามระดับพรีเมียม (เทียบเท่า `OMNICUT_STUDIO_WORKFLOW.html`):

| องค์ประกอบ | สเปกมาตรฐาน |
| :--- | :--- |
| **Theme & Atmosphere** | Dark Mode ระดับลึก (`#040711` ถึง `#070c18`), พื้นหลัง `radial-gradient` เรืองแสงหลากสี (Cyan, Indigo, Emerald), การ์ดกึ่งโปร่งแสง Glassmorphism (`rgba(14, 23, 42, 0.78)` พร้อม `backdrop-filter: blur(18px)`) |
| **Typography** | ภาษาไทย: `IBM Plex Sans Thai` หรือ `Prompt`<br>ภาษาอังกฤษ: `Plus Jakarta Sans`<br>โค้ดและรหัส: `JetBrains Mono` |
| **Color Accents** | Cyan (`#22d3ee`), Indigo (`#6366f1`), Purple (`#a855f7`), Amber (`#f59e0b`), Emerald (`#10b981`), Rose (`#f43f5e`) |
| **Top Navigation** | Sticky Top Bar พร้อม Logo Orb เรืองแสง, ชื่อระบบ, ป้ายสถานะ, และ Quick Jump Links เชื่อมไปยังแต่ละ Section |
| **Hero Section** | Header กลางใหญ่พร้อม Glowing Badge, Gradient Text, สรุปใจความสำคัญ, และ Stat Pills สำหรับสเปกหลัก |
| **Visual Node Chain** | แถวการ์ดสเตจแนวนอนเชื่อมโยงกัน (Horizontal Connected Chain) พร้อมตัวเลขเรืองแสงสีประจำสเตจ |
| **Interactive Canvas** | Mermaid V10 Canvas ในกรอบโค้ด พร้อมแถบเครื่องมือซูม/เลื่อนมุมมอง (Zoom In, Zoom Out, Reset, Fit) |
| **Phase Cards Deep-Dive** | การ์ดเจาะลึกแต่ละสเตจ มีแถบสีซ้ายมือ (`::before`), ป้ายสถานะ, กล่อง Input/Action และ กล่อง Output/Artifacts |
| **Data Contracts & Simulator** | ตารางสคีมาครบทุกฟิลด์ + เครื่องจำลองการสร้างรหัสสด (Live ID Generator Simulator) พร้อมปุ่มคัดลอก 1-คลิก |
| **Master Prompt Library** | การ์ดคำสั่งสั่งงาน AI พร้อมปุ่ม 1-คลิก ก๊อปปี้ และกล่องแจ้งเตือน Toast ไม่รบกวนสายตา |

---

## 📐 3. โครงสร้างหลัก 6 ส่วนใน Flow Dashboard

```
1. [ Top Sticky Nav ]          ➔ Logo Orb + Quick Navigation Links
2. [ Hero Header ]             ➔ Glowing Badge + Title + Subtitle + Stat Pills
3. [ Visual Node Chain ]       ➔ Connected Horizontal Stage Cards (01 Ingest -> 02 Draft -> 03 Render -> 04 Pack -> 05 Post)
4. [ Interactive Mermaid SVG ] ➔ Pan & Zoom Canvas with Subgraphs and Decision Diamonds
5. [ 5-Stage Phase Deep-Dive ] ➔ Color-coded Phase Cards (Actions, Artifacts, Rules)
6. [ Data Contracts & Matrix ] ➔ UUID & Identity Table + Live ID Generator Simulator
7. [ 1-Click Prompt Library ]  ➔ Copy-ready AI Prompts with Toast Feedback
8. [ Strict Safety Guards ]    ➔ Visual Guardrails & Constraints Cards
```

---

## 🔑 4. กฎเหล็กพจนานุกรมรหัส OmniCut (OmniCut Identity Schema)

เมื่อนำสกิลนี้ไปใช้ในโปรเจกต์ OmniCut ให้ยึดถือโครงสร้างรหัสระบุตัวตนนี้เป็นกฎเหล็ก:

1. **`product_id`**: 32 ตัวอักษร Hex ไม่มียัติภังค์ เจนด้วย `uuid.uuid4().hex`
2. **`product_code`**: ตัวพิมพ์ใหญ่ 3-5 ตัว + เลข 2 หลัก (เช่น `ORS01`, `ESS02`, `GOC01`)
3. **`angle_id`**: `ang_` + 8 ตัวอักษร Hex (เช่น `ang_e8f2a1b0`)
4. **`export_id`**: `exp_` + 32 ตัวอักษร Hex (เช่น `exp_a1b2c3d4e5f678901234567890abcdef`)
5. **`job_id`**: `job_` + 16 ตัวอักษร Hex (เช่น `job_582ab38e104f129a`)
6. **`channel_id`**: สตริงระบุชื่อช่อง (เช่น `main`)
7. **`Export MP4`**: `YYYYMMDD_{PRODUCT}_{HOOK}_vN.mp4`
8. **`Cover WebP`**: `YYYYMMDD_{PRODUCT}_{HOOK}_cover.webp`

---

## 🚀 5. มาตรฐานผลลัพธ์ไฟล์ (File Delivery)

- จัดเก็บไฟล์ HTML ที่สร้างไว้ใน `_Docs/` เสมอ (เช่น `_Docs/UNIFIED_AI_PRODUCTION_PIPELINE_FLOW.html`)
- บันทึกการอ้างอิงกลับไปยังไฟล์ Master SOP (`_Docs/UNIFIED_AI_PRODUCTION_PIPELINE_SOP.md`)
- ส่งมอบผลงานพร้อมลิงก์ไฟล์ `file:///...` ที่ผู้ใช้สามารถคลิกเปิดดูในเบราว์เซอร์ได้ทันที
