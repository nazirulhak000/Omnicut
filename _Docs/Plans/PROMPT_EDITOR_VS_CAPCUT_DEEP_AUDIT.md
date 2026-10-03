# Prompt + แผน: ตรวจ Editor (ส่วนหน้า) เทียบ CapCut แบบละเอียด แยกเอเจนต์ตามเลน

ไฟล์นี้ใช้สั่ง AI coding agent ให้ชี้มาที่ไฟล์นี้แล้วสั่ง "ทำตามไฟล์นี้"
**รอบนี้เป็นงานตรวจอย่างเดียว (read-only) ห้ามแก้ซอร์สโค้ด** ผลลัพธ์คือรายงานเทียบ + ลำดับงานที่ควรทำ

ไฟล์ที่เกี่ยวข้อง (อ่านแล้วต่อยอด อย่าทำซ้ำ):
- `_Docs/Plans/APP_AUDIT_CAPCUT_REFERENCE_20261003.md` ตาราง 2 (เทียบ CapCut ระดับระบบ) รอบนี้ลงลึกเฉพาะ editor
- `_Docs/Plans/PRO_EDITOR_STYLE_PLAN.md`, `_Docs/Plans/CAPCUT_PREMIERE_TECH_INTEGRATION_PLAN.md`
- `_Docs/PROMPT_เทียบ_CapCut.md` รายการเมนูของ CapCut เป็นโครงเริ่มต้นได้ แต่ **ส่วน "สิ่งที่รู้อยู่แล้วว่ายังไม่มี" ล้าสมัยแล้ว**
  (audit 2026-10-03 พบว่ามี keyframe backend, LUT, silence detect, beat sync, speed คงที่แล้ว) ห้ามเชื่อ ต้องตรวจใหม่ทุกข้อ

---

## 1. เป้าหมาย

หาว่า editor ของ OmniCut (เมนูตัดต่อมือ) **ด้อยกว่า CapCut ตรงไหนบ้าง** ในมุมของคนที่ตัดคลิปรีวิวสินค้า TikTok แนวตั้ง 9:16 ยาว 30–90 วินาที
ครอบคลุม 6 แบบของความด้อยกว่า ไม่ใช่แค่ "ฟีเจอร์ไม่มี":

| รหัส | ชนิดช่องว่าง | ตัวอย่าง |
|---|---|---|
| G1 | ไม่มีฟีเจอร์ | ไม่มี mask ต่อคลิป |
| G2 | มีครึ่งเดียว | มี keyframe ใน backend แต่ไม่มี UI |
| G3 | ทำได้แต่ช้า/หลายขั้นกว่า | ต้องกด 5 ครั้งแทนที่จะเป็น 1 |
| G4 | ทำได้แต่ไม่แม่น/ไม่ละเอียด | snap ไม่จับ marker, trim ละเอียดระดับเฟรมไม่ได้ |
| G5 | ไม่ลื่น/ช้า | preview กระตุก, ไทม์ไลน์หน่วงเมื่อคลิปเยอะ |
| G6 | หาไม่เจอ/ไม่เข้าใจ | ฟีเจอร์มีแต่ซ่อนลึก, ไม่มี tooltip, ไม่มีคีย์ลัด |

## 2. บริบทที่ต้องรู้

- งานจริง: คลิปรีวิวแกดเจ็ต TikTok Shop affiliate 9:16 (1080x1920, 30 FPS) ทำเป็นชุดทุกวัน ความเร็วในการทำงานสำคัญพอๆ กับฟีเจอร์
- เครื่อง: AMD Ryzen 7 7735HS / Radeon (ไม่มี CUDA) RAM ~13.7 GiB ฟีเจอร์ที่หนัก GPU ให้ประเมินว่า "คุ้มกับเครื่องนี้ไหม"
- ผู้ใช้เขียนโค้ดไม่เป็น ทุกฟีเจอร์ต้องกดได้จาก UI
- ซอร์สหลัก: `frontend/src/components/editor/` (EditorShell.jsx ~3.4k บรรทัด, Timeline*.jsx, Toolbar.jsx, Inspector.jsx, `inspector/*`, `timeline/*`),
  `frontend/src/components/SequencePlayer.jsx` (~5.6k บรรทัด), `frontend/src/hooks/useEditor*.js`, `useTimelineDrag.js`, `frontend/src/lib/` (timelineMath/keyframeModel/beatGrid/silenceRipple/lut3d/motion/*)
- **ไฟล์ใหญ่ห้ามเปิดทั้งไฟล์** ใช้ grep หาตำแหน่งแล้วอ่านทีละช่วงไม่เกิน 100 บรรทัด (กฎประหยัดโทเคน AGENTS.md ข้อ 13)

## 3. หลักฐานฝั่ง CapCut (ห้ามเดา)

เครื่องนี้ **ติดตั้ง CapCut แล้ว** (`%LOCALAPPDATA%\CapCut\Apps\7.1.0.2890\CapCut.exe`) ให้ติดป้ายระดับหลักฐานทุกแถวฝั่ง CapCut:

| ระดับ | ความหมาย |
|---|---|
| **A** | เห็นจากหน้าจอ CapCut จริงในเครื่อง (ภาพหน้าจอที่ผู้ใช้ส่งให้ หรือผู้ใช้เปิดให้ดูแล้วเอเจนต์ถามกลับ) |
| **B** | มาจากเอกสาร/หน้าช่วยเหลืออย่างเป็นทางการ ต้องแนบ URL |
| **C** | ความรู้ทั่วไป/ความจำ ยังไม่ยืนยัน **ห้ามเขียนเป็นข้อเท็จจริง** ใช้คำว่า "น่าจะ" |

ข้อกำหนด:
- เอเจนต์ควบคุมหน้าต่าง CapCut เองไม่ได้ ถ้าต้องการระดับ A ให้ **ทำรายการ "ขอภาพหน้าจอจากผู้ใช้"** ท้ายรายงาน (ระบุว่าอยากเห็นเมนู/แผงไหน) ไม่ต้องรอ ให้ใช้ระดับ B/C ไปก่อนแล้วเขียนว่าต้องยืนยัน
- **ห้ามเปิดอ่าน/แก้/คัดลอกไฟล์ภายใน CapCut** (`Apps\...`, `User Data\`, `draft_content.json`, `.cloud_cache_*`) เพื่อ reverse engineer ให้เทียบจากพฤติกรรมที่ผู้ใช้เห็นเท่านั้น
- ห้ามคัดลอกโค้ด effect asset ฟอนต์ หรือ template ของ CapCut

## 4. หลักฐานฝั่ง OmniCut (ต้องเข้มกว่าฝั่ง CapCut)

ทุกแถวที่ตอบว่า "มี" ต้องมีครบ 3 อย่าง ไม่ครบให้ลดเป็น "มีครึ่งเดียว" หรือ "ยังไม่ยืนยัน":
1. **file:line** ที่โค้ดทำงานจริง (ไม่ใช่แค่ชื่อฟังก์ชัน/ตัวแปรที่ประกาศไว้)
2. **UI ที่กดได้** ชี้ได้ว่าปุ่ม/เมนู/คีย์ลัดอยู่ตรงไหน
3. **ผลลัพธ์ตอน render** ตรวจว่า backend (`scripts/video_editor.py` ฯลฯ) ใช้ค่านั้นจริง ไม่ใช่เห็นแค่ใน preview (Preview = Render ตาม `.agents/rules/preview_render_parity.md`)

วิธีลองกดจริง (ทำเท่าที่ปลอดภัย):
- ใช้ harness ที่มีอยู่: `frontend/editor_shell_audit.html` + `frontend/src/editorShellAuditFixture.jsx`, `frontend/editor_controls.html`, `tests/motion_capture/app_capture.py` (Playwright) ผลทุกอย่างลง `.tmp/` เท่านั้น
- ถ้ารัน dev server ได้ (`npm run dev` ใน `frontend/`) ให้ใช้ข้อมูลทดสอบใน `tmp_path`/`.tmp/` ห้ามแตะโปรเจกต์จริง
- ถ้าลองกดไม่ได้ ให้ระบุ "ยังไม่ได้ลองกด" ห้ามสรุปจากชื่อปุ่ม

## 5. งานเทียบแบบวัดจำนวนขั้นตอน (Task Benchmark)

นอกจากเทียบรายฟีเจอร์ ให้เทียบ **งานจริง** ว่าใช้กี่ขั้นตอน/กี่คลิก/กี่วินาที ในแต่ละเลนเลือกเฉพาะงานที่เกี่ยว แล้วนับ: OmniCut กี่ขั้น vs CapCut กี่ขั้น (ฝั่ง CapCut ติดป้ายระดับหลักฐาน)

| งาน | ชื่อ |
|---|---|
| T1 | ตัดกลางคลิป (split 2 จุด) แล้วลบท่อนกลางให้ช่องว่างปิดเอง (ripple delete) |
| T2 | เปลี่ยนความเร็วคลิป 1.5x แล้วดูความยาวใหม่ที่ไทม์ไลน์ |
| T3 | ปรับตำแหน่ง+ขนาดคลิปบนจอ (ซูมเข้า 120% เลื่อนขึ้น) ให้พอดี 9:16 |
| T4 | ใส่ข้อความอิสระ ลากวางตำแหน่ง ตั้งฟอนต์/สี/ขอบ ใส่แอนิเมชันเข้า-ออก |
| T5 | แก้คำผิดในซับ 1 คำ แล้วปรับเวลาขึ้น-ลงของท่อนนั้น |
| T6 | ใส่เพลงพื้นหลัง ตัดให้พอดีความยาวคลิป ปรับเสียงเบาลงช่วงที่มีเสียงพูด |
| T7 | ใส่ transition ระหว่างสองคลิป ปรับความยาว transition |
| T8 | ใส่สติกเกอร์/โลโก้ซ้อนบนวิดีโอ กำหนดช่วงเวลาที่แสดง |
| T9 | ทำ keyframe ซูมช้าๆ 3 วินาที (เริ่ม 100% จบ 115%) |
| T10 | ลบพื้นหลังวัตถุ (cutout) แล้วใส่พื้นหลังใหม่ |
| T11 | คัดลอกการตั้งค่า (สี/ความเร็ว/ซูม) จากคลิป A ไปวางที่คลิป B, C, D |
| T12 | ทำ undo 5 ครั้งหลังแก้หลายอย่าง แล้ว redo กลับ |
| T13 | บันทึกโปรเจกต์ ปิด เปิดใหม่ งานกลับมาครบ |
| T14 | ส่งออก ระบุความละเอียด/fps/ช่วงที่ส่งออก |

## 6. แบ่งเลน (1 เอเจนต์ต่อ 1 เลน รันขนานได้ เพราะแต่ละเลน read-only และเขียนไฟล์ของตัวเองเท่านั้น)

ทุกเลนเขียนรายงานที่ `_Docs/Reports/CAPCUT_EDITOR_GAP_20261003/<รหัสเลน>.md` (สร้างโฟลเดอร์เอง) **ห้ามเขียนไฟล์อื่น**

| เลน | ขอบเขต | ไฟล์หลักที่ต้องอ่าน | งานเทียบที่รับผิดชอบ | หัวข้อ CapCut ที่ต้องไล่ |
|---|---|---|---|---|
| **L1 Timeline** | ไทม์ไลน์และการแก้ไขคลิป | `Timeline.jsx`, `TimelineClip.jsx`, `timeline/*`, `useTimelineDrag.js`, `useTimelineKeyboard.js`, `lib/timelineMath.js`, `lib/collectionOperations.js`, `selectionResolver.js`, `pointerDragLifecycle.js` | T1, T11, T12 | หลายแทร็ก, ล็อก/ซ่อน/mute แทร็ก, snap (คลิป/playhead/marker/beat), magnetic/ripple, split, trim (ละเอียดระดับเฟรม), ลากข้ามแทร็ก, เลือกหลายคลิป, ลากกรอบเลือก, group/ungroup, marker, zoom ไทม์ไลน์ (fit/แถบเลื่อน), ไอคอนคลิป/thumbnail/filmstrip, เมนูคลิกขวา, ripple delete, ล็อกเสียงลิงก์กับภาพ |
| **L2 Clip & Inspector** | คุณสมบัติรายคลิป | `Inspector.jsx`, `inspector/ClipInspector.jsx`, `ProjectInspector.jsx`, `SliderControl.jsx`, `lib/keyframeModel.js`, `inspectorModel.js`, `lut3d.js`, `scripts/keyframe_engine.py`, `video_editor.py` ส่วน speed/crop/color | T2, T3, T9, T11 | ตำแหน่ง/ขนาด/หมุน/flip บนจอ (ลากบน canvas มี handle ไหม), crop, ความเร็วคงที่/curve, reverse, freeze, keyframe (UI+easing+ทุกค่า), ปรับสี (basic/curves/HSL/LUT/temperature), opacity/blend mode, mask, stabilize, chroma key, auto-reframe, ลบ/ขัด noise ภาพ, "คัดลอก-วางคุณสมบัติ" |
| **L3 Text & Overlay** | ข้อความ ซับ สติกเกอร์ | `inspector/CaptionInspector.jsx`, `OverlayInspector*.jsx`, `StickerInspector.jsx`, `CuesTranscriptInspector.jsx`, `lib/overlay*.js`, `FindReplaceModal.jsx`, `TextLookPreview.jsx`, `StylePresetPicker.jsx` | T4, T5, T8 | กล่องข้อความอิสระ, ลากวาง/หมุน/ย่อขยาย บน canvas, ฟอนต์/สี/ขอบ/เงา/พื้นหลัง/ตัวอักษรโค้ง, แอนิเมชันเข้า-ค้าง-ออก, ซับอัตโนมัติ, แก้ซับทีละท่อน, แปลซับ, ค้นหา-แทนที่, เทมเพลตข้อความ, สติกเกอร์/ภาพซ้อน, PiP, แท็บเลเยอร์ซ้อนกัน, จัดตำแหน่ง/align/guide, safe zone TikTok |
| **L4 Audio** | เสียงทั้งหมดใน editor | `lib/audioPeaks.js`, `beatGrid.js`, `silenceRipple.js`, `AssetPanel.jsx` (ส่วนเสียง), `useEditorCommands.js`, `SequencePlayer.jsx` (ส่วน audio), `scripts/sfx_manager.py`, `voice_*` | T6 | waveform บนไทม์ไลน์, volume ต่อคลิป/แทร็ก, fade, keyframe เสียง, ducking อัตโนมัติ, ตัดเสียงเงียบ, beat marker/beat sync, ลด noise, แยกเสียงจากวิดีโอ, voice changer, pitch/speed, เมตเตอร์ระดับเสียง, normalize, ห้องสมุดเพลง/SFX + ค้นหา/ฟังตัวอย่าง, ซิงก์ TTS |
| **L5 Effects, Transition, Cutout** | เอฟเฟกต์ รอยต่อ ฟิลเตอร์ ลบพื้นหลัง | `timeline/EffectTrack.jsx`, `inspector/EffectInspector.jsx`, `lib/effectPlayback.js`, `lib/motion/*`, `cutoutEngineModel.js`, `cutoutSubjectPointState.js`, `backgroundIsolation*.js`, `scripts/video_editor.py` ส่วน xfade/effect | T7, T10 | จำนวนและความหลากหลาย transition, ปรับความยาว/ทิศทาง, ฟิลเตอร์สำเร็จรูป+ความเข้ม, effect ภาพ (glitch/blur/shake/zoom), body effect, overlay ซ้อน, cutout (คลิกเลือกวัตถุ, ขอบ, preview ตอนเลือก, ใช้เวลาเท่าไร), พื้นหลังใหม่/blur, library effect + ค้นหา + ฟังตัวอย่างก่อนใส่ |
| **L6 Preview & Performance** | พรีวิว การเล่น ความลื่น | `SequencePlayer.jsx` (ใช้ grep), `lib/previewQuality.js`, `clipProxy.js`, `highResolutionStillPreview.js`, `cutoutVideoPlayback.js`, `lib/motion/performanceGuard.js`, `useEditorSelection.js`, `tests/test_preview_render_parity.py` | T3 (ส่วน preview), T12, T13 | เล่น/หยุด/seek ลื่นไหม, scrub, เฟรมต่อเฟรม, loop, เต็มจอ, ความละเอียด preview (proxy/quality), ซูม preview, safe zone/guide บน canvas, ความเร็วเมื่อคลิปเยอะ/ไทม์ไลน์ยาว, หน่วยความจำ, เวลาเปิดโปรเจกต์, Preview vs Render ตรงกันไหม (ตามกฎ parity), ตัวเลขวัดจริงถ้ารัน harness ได้ |
| **L7 Workflow & Shell** | ภาพรวมการทำงาน | `EditorShell.jsx`, `EditorHeader.jsx`, `HeaderMenu.jsx`, `Toolbar.jsx`, `AssetPanel.jsx`, `NewClipPanel.jsx`, `ProjectSelector.jsx`, `RenderButton.jsx`, `ShortcutsModal.jsx`, `usePanelLayout.js`, `useProjectAutosave.js`, `useProjectLoader.js`, `useRenderJob.js`, `useEditorShortcuts.js`, `lib/projectSaveQueue.js`, `renderJobModel.js` | T11, T12, T13, T14 | ไลบรารีสื่อ (ค้นหา/กรอง/ลากเข้า/preview ก่อนใช้), undo/redo (ข้ามช่วงเปิดปิด? history panel?), autosave/เวอร์ชัน/กู้คืน, คีย์ลัดครบแค่ไหน+ปรับแต่งได้ไหม, เลย์เอาต์แผง (ลาก/ย่อ/โหมดเต็ม), เทมเพลตโปรเจกต์ (บันทึก/แชร์), ส่งออก (ความละเอียด/fps/bitrate/ช่วงที่เลือก/ลายน้ำ/คิว), แสดงสถานะ render, ภาษาและ tooltip, ปุ่มช่วยเหลือ, หน้าจอเล็ก/UI scale |

เอเจนต์ที่ **8 (สังเคราะห์)** เริ่มหลังทุกเลนส่งรายงาน (ดูข้อ 9)

### กติกาเลน
- ห้ามแก้ซอร์ส ห้ามติดตั้งอะไร ห้าม `git add/commit/stash/checkout/reset`
- `SequencePlayer.jsx` และ `EditorShell.jsx` มี diff ค้างของเอเจนต์อื่น (ดู `git status` และตารางเจ้าของไฟล์ใน TODO.md) **อ่านได้ แต่ระบุในรายงานว่าบรรทัดอ้างอิงอาจขยับ**
- ถ้าเลนอื่นมีขอบเขตทับ (เช่น L2 กับ L6 ในเรื่อง preview ของ transform) ให้ L2 ตรวจฝั่ง inspector/ค่า L6 ตรวจฝั่งการเล่น ห้ามตรวจซ้ำ ใส่ "ดูเลน L6" แทน
- ห้ามสร้างไฟล์ทดสอบ/ภาพ/วิดีโอค้างนอก `.tmp/` และต้องลบหลังจบ (Cleanup 100%) ห้ามเขียนลง `01_Raw/`, `02_Assets/`, `04_Exports/`, `03_Projects/` จริง
- ห้ามเปลี่ยนฟอนต์/ซับ/safe zone หรือเสนอให้เปลี่ยน golden master (`font_text_visual_contract.md`) ถ้าเจอว่า CapCut ทำได้มากกว่า ให้บันทึกเป็น "ข้อเสนอ ต้องให้ผู้ใช้อนุมัติ"

## 7. รูปแบบรายงานต่อเลน

ทุกรายงานเลนต้องมี 5 ส่วนนี้ตามลำดับ:

**ส่วน 1: ตารางเทียบรายฟีเจอร์**

| # | ฟีเจอร์ | CapCut ทำอย่างไร | หลักฐาน CapCut (A/B/C + URL) | OmniCut | ชนิดช่องว่าง (G1–G6 หรือ "เท่า/ดีกว่า") | หลักฐาน OmniCut (file:line · UI · render) | ลองกดจริง (ใช่/ไม่) |
|---|---|---|---|---|---|---|---|

**ส่วน 2: Task Benchmark** (เฉพาะงาน T ที่เลนรับผิดชอบ)

| งาน | ขั้นตอน OmniCut (นับจากที่ลองจริง/อ่านโค้ด) | ขั้นตอน CapCut (ระดับหลักฐาน) | ต่างกัน | สาเหตุ |
|---|---|---|---|---|

**ส่วน 3: ช่องว่างที่เจอ** จัดเป็นรายการ แต่ละรายการมี
- รหัส `<เลน>-<เลขลำดับ>` เช่น `L1-04`
- ชนิดช่องว่าง G1–G6
- **ผลกระทบกับงานจริง** (สูง/กลาง/ต่ำ) พร้อมเหตุผลว่า "งานรีวิวสินค้า 30–90 วิ ใช้บ่อยแค่ไหน"
- ทางแก้ที่เสนอ (ใช้โมดูลไหน, backend ต้องแก้ด้วยไหม, ต้องแก้ parity คู่ไหม)
- แรง: S (<2 ชม.) / M (ครึ่งวัน) / L (1–2 วัน) / XL
- ความเสี่ยง และไฟล์ที่ชนกับงานของเอเจนต์อื่น

**ส่วน 4: ที่ OmniCut ดีกว่าหรือเท่า CapCut แล้ว** (ต้องมี เพื่อกันการสรุปเอียง เช่น ซับ Ghost Reveal, auto-pipeline) พร้อมหลักฐาน

**ส่วน 5: ที่ตรวจไม่ได้/ต้องให้ผู้ใช้ช่วย** (ภาพหน้าจอ CapCut ที่ต้องขอ, ข้อมูลที่ต้องรันจริง, สิ่งที่ถูกบล็อกเพราะไฟล์เป็นของเอเจนต์อื่น)

### ข้อห้ามในรายงาน
- ห้ามใช้คำว่า "ครบ" "ไม่มีปัญหา" ถ้าไม่ได้ลองกดและไม่ได้ตรวจ render
- ห้ามนับปุ่มที่ backend ยังไม่ทำงานว่า "มี"
- ห้ามเสนอฟีเจอร์ที่ขัดกฎโปรเจกต์: ซับ/ฟอนต์ที่ล็อก, เพลงลิขสิทธิ์จาก TikTok, scrape เกิน metadata สาธารณะ, ลดสเปก 1080x1920/30fps
- ห้ามเสนอ "ไล่ตาม CapCut ทุกอย่าง" ถ้าฟีเจอร์นั้นงานรีวิวสินค้าไม่ใช้ ให้เขียนว่า "ไม่ควรทำ" พร้อมเหตุผล

## 8. ขั้นเตรียมของเอเจนต์ทุกตัว (บังคับ AGENTS.md)

1. อ่าน TODO.md ส่วนหัว (ไม่เกิน 100 บรรทัด) และ `git status`
2. **เอเจนต์หลัก (root) เปิดรอบใน TODO.md ก่อนปล่อยเลน** ชื่อ `Round EDITOR-CAPCUT-DEEP-AUDIT-<YYYYMMDD>` มี `ดำเนินการโดย: <เอเจนต์> (<โมเดล>)` และตารางเจ้าของไฟล์รายงานต่อเลน (แต่ละเลนเขียนได้แค่ไฟล์ของตัวเอง)
3. เลนที่ใช้ Jev (`tools/jev_advisor.py`) ให้ใช้ตอนเจอทางเลือก 3–7 ทางและจัดลำดับความสำคัญ ถ้า confidence < 0.80 หรือ null ให้ใส่ในส่วน 5 ว่า "ต้องผู้ใช้ตัดสิน" Jev ล่ม = ทำต่อ
4. เปิดไฟล์ทีละช่วง ห้ามเปิดทั้งไฟล์ใหญ่ ห้ามเปิด HISTORY.md ทั้งไฟล์

## 9. เอเจนต์สังเคราะห์ (หลังทุกเลนส่งเสร็จ)

อ่านรายงาน L1–L7 แล้วเขียน `_Docs/Reports/CAPCUT_EDITOR_GAP_20261003/00_SUMMARY.md` ประกอบด้วย:

1. **คะแนนต่อเลน** ระดับเท่า CapCut เป็น % *สำหรับงานรีวิวสินค้า* (ไม่ใช่ % ของฟีเจอร์ทั้งหมดของ CapCut) พร้อมวิธีคิดคะแนน (ถ่วงน้ำหนักตามความถี่ของงานจริง)
2. **ตารางช่องว่างรวม** จัดเรียงตาม (ผลกระทบ ÷ แรง) รวมรหัสจากทุกเลน กรองรายการซ้ำ/ทับกัน
3. **กอง 4 กอง:** ทำเลย (S/M ผลสูง) · ต้องแก้ backend/parity ด้วย (วางแผนก่อน) · ไม่คุ้มกับเครื่อง CPU-only (ระบุเวลาที่เพิ่ม) · ไม่ควรทำ (เหตุผล)
4. **Top 10** ที่ควรทำต่อ เรียงลำดับและขึ้นต่อกันอย่างไร ระบุไฟล์ที่ต้องแตะและเจ้าของไฟล์ที่ชนกัน (SequencePlayer/EditorShell)
5. **ผล Task Benchmark รวม** ตาราง T1–T14 OmniCut vs CapCut
6. **ข้อที่ขัดแย้งกับรายงาน audit รอบก่อน** (`APP_AUDIT_CAPCUT_REFERENCE_20261003.md` ตาราง 2) ถ้าพบว่าข้อไหนตอนนั้นสรุปผิด ให้ระบุ
7. **รายการขอภาพหน้าจอ CapCut จากผู้ใช้** รวมทุกเลน จัดกลุ่มตามเมนู เพื่อให้ผู้ใช้ส่งทีเดียว
8. **ข้อที่ต้องให้ผู้ใช้ตัดสินใจ** (รวมของที่ชนกฎโปรเจกต์)

ท้ายสุดสรุปในแชตไม่เกิน 15 บรรทัด + ลิงก์ `00_SUMMARY.md` แล้วถามผู้ใช้ว่าจะให้เริ่มทำ Top 10 ข้อไหนก่อน **ห้ามเริ่มแก้โค้ดเอง**

## 10. ปิดรอบ

- ตรวจว่าไม่มีไฟล์ทดสอบค้างนอก `.tmp/` และ `git status` ไม่มีซอร์สถูกแก้โดยรอบนี้ (เห็นแค่โฟลเดอร์รายงานใหม่ + TODO.md)
- อัปเดตบล็อกรอบใน TODO.md ให้ตรงของจริง ระบุเลนที่ตรวจไม่ครบและเหตุผล
- รอบนี้ยังไม่ย้ายเข้า HISTORY.md จนกว่าผู้ใช้อ่านสรุปและเลือกงานต่อ

---

## ภาคผนวก A: ข้อความสั่งเอเจนต์ (คัดลอกวางได้)

**สั่งเอเจนต์หลัก (ถ้าให้เขาแตกเลนเอง):**
```
ทำตามไฟล์ _Docs/Plans/PROMPT_EDITOR_VS_CAPCUT_DEEP_AUDIT.md
เปิดรอบใน TODO.md ก่อน แล้วแตก 7 เลน (L1–L7) ให้เอเจนต์ย่อยรันขนาน แต่ละเลนอ่านอย่างเดียวและเขียนเฉพาะรายงานของตัวเอง
เมื่อครบแล้วรวมเป็น 00_SUMMARY.md ห้ามแก้ซอร์สโค้ด
```

**สั่งทีละเลน (ถ้าเปิดหลายหน้าต่างเอง):**
```
ทำตามไฟล์ _Docs/Plans/PROMPT_EDITOR_VS_CAPCUT_DEEP_AUDIT.md เฉพาะเลน L<เลข> เขียนผลที่ _Docs/Reports/CAPCUT_EDITOR_GAP_20261003/L<เลข>.md ห้ามแก้ซอร์ส
```

## ภาคผนวก B: ตัวอย่างแถวรายงานที่ "ผ่านเกณฑ์"

| # | ฟีเจอร์ | CapCut | หลักฐาน CapCut | OmniCut | ช่องว่าง | หลักฐาน OmniCut | ลองกดจริง |
|---|---|---|---|---|---|---|---|
| 1 | Keyframe ค่า scale | มีปุ่ม diamond ในแผง Video > Basic; ลากเลื่อนจุดได้ | C (ยังไม่ยืนยัน ขอภาพหน้าจอ) | มีครึ่งเดียว | G2 | backend `keyframe_engine.py:30-123` ใช้งานได้; frontend `keyframeModel.js:105` มีโมเดลแต่ **ไม่มี UI** ใน `ClipInspector.jsx` (grep `keyframe` ไม่เจอปุ่ม); render ใช้ zoom/pan linear เท่านั้น `video_editor.py:884-966` | ใช่ (ไม่พบปุ่มใน inspector) |

ตัวอย่างที่ **ไม่ผ่าน**: "OmniCut มี keyframe แล้ว (keyframeModel.js)" ← ไม่มี UI ไม่ตรวจ render ไม่ได้ลองกด
