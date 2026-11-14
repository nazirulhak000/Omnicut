# 📋 แผนงานถอดระบบภายนอกและการเชื่อมต่อ CapCut ออกจาก OmniCut Studio 100%
(Plan: Decouple & Remove CapCut External Workflow & Builder from OmniCut Pro Studio)

**วันที่:** 2026-11-14  
**ดำเนินการโดย:** Antigravity (Gemini 3.8 Flash High)  
**เป้าหมาย:** ทำการ Clean Sweep ถอดเวิร์กโฟลว์, เครื่องมือสร้างดราฟต์ภายนอก (CapCut Builder), คำสั่งเอเจนต์ส่งออก/นำเข้าดราฟต์, และการมอนิเตอร์โฟลเดอร์ CapCut Desktop ออกจากโปรแกรมทั้งหมดตามคำขอผู้ใช้ ("ไม่ทำงานกับ capcut แล้วครับ เอาออกได้เลยครับ") โดยรักษาความสามารถในการเรนเดอร์และพรีวิวแบบ Native In-App Studio ของ OmniCut ไว้อย่างสมบูรณ์ 100% (Zero-Regression)

---

## 1. ขอบเขตการตัดออกและปรับปรุง (Scope of Removal)

### ส่วนที่ 1: สคริปต์และเครื่องมือภายนอก (Backend Tools & Builders)
1. **ลบ `scripts/capcut_builder.py`**:
   - เครื่องมือภายนอกสำหรับสร้างดราฟต์ CapCut (`draft_content.json`, `root_meta_info.json`) ผ่าน `pyJianYingDraft` / `VectCutAPI` ที่ไม่ได้ใช้งานแล้ว
2. **ลบ `tests/test_capcut_builder_7_1.py`**:
   - ชุดทดสอบเฉพาะของ `capcut_builder.py`
3. **ลบ `tools/slice_capcut_stickers.py`**:
   - สคริปต์ one-off เก่าที่ใช้หั่นสติกเกอร์ชีต CapCut
4. **ตัด Action ใน In-App AI Agent**:
   - ใน `scripts/agent/omnicut_agent_tools.py`: ถอด `export_or_import_capcut_draft`, ถอดการ import `CapCutBuilder`, และทำความสะอาด `apply_action`
   - ใน `scripts/agent/agy_bridge.py`: ถอด action `export_or_import_capcut_draft`, regex matcher, และคำสั่ง fallback `"ส่งออกดราฟต์ capcut"`, `"นำเข้าดราฟต์ capcut"`
5. **ปรับปรุงชุดทดสอบ Parity**:
   - ใน `tests/test_capcut_7_1_wave3_parity.py`: ตัดการทดสอบ round-trip draft importer ที่ผูกกับ `capcut_builder.py` ออก โดยคงการทดสอบ Math / Shader Parity ของตัว Editor ไว้อย่างสมบูรณ์

### ส่วนที่ 2: หน้าจอผู้ใช้งาน (Frontend UI & Text Copy)
1. **`frontend/src/components/SystemSettings.jsx`**:
   - ลบการ์ดโฟลเดอร์ `CapCut Drafts (โฟลเดอร์ CapCut PC)`
   - ลบกล่องสถานะ `CapCut PC Draft Sync`
   - ปรับข้อความหัวข้อจาก `สถานะการเรนเดอร์และ CapCut PC Integration` เป็น `สถานะเอนจินการเรนเดอร์ (FFmpeg Hardware Engine)`
   - ปรับสถานะ System Status Pill จาก `CapCut Synced / ไม่พบ CapCut` เป็น `System Ready / FFmpeg Ready`
   - คลีนข้อความคำอธิบายในหมวด Storage & Engine
2. **`frontend/src/components/SystemAssets.jsx`**:
   - ลบแถวไดเรกทอรี `CapCut PC Projects Draft`
   - ลบการ์ดแสดงสถานะ `CapCut PC Draft Sync`
   - ปรับคำอธิบาย Hub ให้ไม่มีคำว่า "และการเชื่อมต่อ CapCut"
   - ปรับข้อความพรีวิวฟอนต์เป็น "ฟอนต์ทั้งหมดถูกแพ็กรวมในระบบและ FFmpeg อัตโนมัติ"
3. **`frontend/src/components/MediaAssetsHub.jsx`**:
   - ลบการ์ดไดเรกทอรี `capcut` (CapCut Drafts) ออกจากรายการหมวดระบบ
   - ปรับ sublabel จาก `โฟลเดอร์ & CapCut Drafts` เป็น `โฟลเดอร์ & ไดเรกทอรีระบบ`
   - ปรับคำอธิบายหมวดและป้ายความเข้ากันได้จาก `FFmpeg / CapCut PC` เป็น `FFmpeg Native Engine`
4. **`frontend/src/components/SubSrtTool.jsx`**:
   - ปรับหัวข้อจาก `AI Auto-SRT Generator (ถอดซับแม่นยำ 100% สไตล์ CapCut)` เป็น `AI Auto-SRT Generator (ถอดซับแม่นยำ 100% สำหรับคลิปวิดีโอ)`
   - ปรับข้อความแนะนำจาก `ลากไฟล์เข้า CapCut ได้ทันที` เป็น `ลากไฟล์เข้าห้องตัดต่อได้ทันที`
5. **`frontend/src/components/ProductToClip.jsx`**:
   - ปรับ tooltip จาก `โปรเจกต์ CapCut: ...` เป็น `โปรเจกต์: ...`

### ส่วนที่ 3: Backend APIs & Server Metadata
1. **`scripts/api_server.py`**:
   - ปรับ OpenAPI / Swagger title & description ให้คลีน ไร้คำว่า `CapCut`
2. **`scripts/api_render.py`**:
   - ปรับสถานะ `get_system_status` คืนค่าโฟลเดอร์ระบบและสถานะ engine อย่างถูกต้อง
3. **`scripts/config.py` & `scripts/path_utils.py`**:
   - คง `CAPCUT_DRAFT_DIR` ไว้เป็น legacy constant สำหรับ path containment backward-compatibility (ป้องกันข้อผิดพลาดกรณีมี path เก่าค้างในระบบ) โดยมาร์กเป็น `# Legacy backward-compatibility only`

---

## 2. ขั้นตอนการดำเนินการ (Execution Steps)

1. [x] บันทึกแผนงานลง `_Docs/Plans/PLAN_DECOUPLE_AND_REMOVE_CAPCUT_WORKFLOW_20261114.md`
2. [ ] เพิ่มรอบงานลง `TODO.md` ในหัวข้อ `## รอบปัจจุบัน`
3. [ ] ดำเนินการลบไฟล์ `scripts/capcut_builder.py`, `tests/test_capcut_builder_7_1.py`, `tools/slice_capcut_stickers.py`
4. [ ] ดำเนินการปรับปรุง `scripts/agent/omnicut_agent_tools.py` และ `scripts/agent/agy_bridge.py`
5. [ ] ดำเนินการปรับปรุง `tests/test_capcut_7_1_wave3_parity.py`
6. [ ] ดำเนินการปรับปรุง Frontend UI: `SystemSettings.jsx`, `SystemAssets.jsx`, `MediaAssetsHub.jsx`, `SubSrtTool.jsx`, `ProductToClip.jsx`
7. [ ] ดำเนินการปรับปรุง `scripts/api_server.py` และ `scripts/api_render.py`
8. [ ] รันการทดสอบ Vitest และ Pytest ครบวงจร ยืนยัน Zero-Regression
9. [ ] รันการบิลด์ Frontend (`npm run build`) ตรวจสอบความถูกต้อง
10. [ ] ย้ายรอบงานเข้าสู่ `HISTORY.md` และสรุปผลให้ผู้ใช้
