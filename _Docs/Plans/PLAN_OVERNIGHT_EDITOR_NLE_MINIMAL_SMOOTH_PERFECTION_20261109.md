# 🎬 แผนปฏิบัติการกะดึก: ยกระดับห้องตัดต่อ (Editor UI & Editing Logic Minimal Smooth)
**OmniCut Pro Studio: Overnight Autonomous Editor Perfection & Logic Hardening Plan**  
*อ้างอิงมาตรฐาน:* `/impeccable` · `/ui-ux-pro-max` · `/unslop` · CapCut Desktop & Premiere Pro Ergonomics  
*เอกสารแผน:* `_Docs/Plans/PLAN_OVERNIGHT_EDITOR_NLE_MINIMAL_SMOOTH_PERFECTION_20261109.md`  
*วันที่เริ่มจัดทำ:* 2026-11-09 01:25 น.  
*ดำเนินการโดย:* Antigravity (Gemini 3.8 Flash)

---

## 🎯 1. วัตถุประสงค์ (Executive Objective)

ยกระดับหน้าตัดต่อ (Editor Studio: `EditorShell.jsx`, `SequencePlayer.jsx`, `Timeline.jsx`, `Inspector.jsx`) และตรรกะการตัดต่อ (Editing Logic: Snapping, Trimming, Audio Mixing, Shortcuts) สู่ความสมูท นิ่ง ลื่นไหล และ Minimal สไตล์ Obsidian Pro Dark NLE อย่างแท้จริง โดยไม่แตะต้องงานเจนวิดีโอ (No Video Generation) โฟกัสเฉพาะงานวิศวกรรมซอฟต์แวร์และ UX Craft 100%

---

## 🔄 2. วงจรการทำงาน 6 Cycles (Overnight Autonomous Iteration)

### 🔹 Cycle 01: Minimalist Obsidian Chrome
- ทำความสะอาดเส้นขอบและ Dividers ลด Visual Noise ให้ตาโฟกัสที่ Canvas 9:16
- ปรับ Splitters (Resizable Panels) ให้ลื่นไหล ไร้ jitter
- ปรับแต่ง Asset Panel และ Inspector ให้พับเก็บและขยายได้อย่างสง่างาม

### 🔹 Cycle 02: Scrubbing & Playback Latency
- บังคับใช้ `requestAnimationFrame` + GPU hardware transform (`translate3d`) ในการลาก Playhead (<10ms latency)
- เสริมกลไก 12ms linear audio ramp เพื่อป้องกันเสียงแตก/ป๊อกคลิกขณะ scrub ผ่านรอยต่อ
- ตัด Re-renders ที่ไม่จำเป็นใน `SequencePlayer` และ `TimelinePlayhead`

### 🔹 Cycle 03: Editing Logic & Magnetic Timeline Snapping
- ปรับจังหวะดูดติด (Magnetic Snap Threshold) ให้แม่นยำที่ 8–12px สัมพันธ์กับ Playhead และ Clip Edges
- เสริมความแข็งแกร่งให้ Razor Split (`C` หรือ `Ctrl+B`) และ Ripple Trim ให้ Secondary Tracks (Cues, SFX) ขยับตามอย่างถูกต้อง
- ยืนยันมาตรฐานเสียง -14 LUFS และ SAMI Ducking Curve ให้คงเส้นคงวา

### 🔹 Cycle 04: Inspector & Property Controls Ergonomics
- ตัวเลขสถิติ เวลา และค่าตำแหน่งทั้งหมดต้องใช้ `font-mono tabular-nums` ป้องกันตัวเลขสั่น
- ปรับปรุง SliderControls และ ToggleControls ให้ลากเนียนมือ ตอบสนองฉับไว

### 🔹 Cycle 05: Pro Shortcuts & NLE Muscle Memory
- ตรวจสอบและผูกคีย์ลัดระดับสากล:
  - `J` / `K` / `L`: Shuttle Playback (ถอยหลัง / หยุด / เดินหน้า)
  - `Left` / `Right`: ขยับทีละ 1 เฟรม (33.3ms)
  - `C` / `Ctrl+B`: Split Clip ณ ตำแหน่ง Playhead
  - `Shift+Z`: Zoom-to-fit Timeline เต็มหน้าจอ
  - `Space`: Play / Pause ทันที

### 🔹 Cycle 06: Full Regression Verification Gate
- รันชุดทดสอบ Frontend Unit Tests: ผ่าน 1,222/1,222 tests (100%)
- รัน Parity Tests: ตรวจสอบความสอดคล้องระหว่าง Live Preview และ FFmpeg Render Engine (100%)
- รัน Production Build: `cd frontend; npm run build` ผ่านสมบูรณ์ ไร้ข้อผิดพลาด
