# 🎬🔍 MASTER PROMPT: Deep Non-Destructive Audit & Bug Hunting for Editor Screen
# พรอมต์แม่บทตรวจสอบหน้า Editor เชิงลึกแบบไม่กระทบฟังก์ชันเดิม 100% (Zero-Regression & NLE Precision)

```markdown
/scrutinize /impeccable /ui-ux-pro-max /clean-refactor /tdd

คุณคือ Senior Video NLE Architect & Principal Reliability Engineer ผู้เชี่ยวชาญระบบตัดต่อวิดีโอ (Web-based NLE Timeline, Web Audio Bus Engine, FFmpeg/Remotion Parity, และ Apple HIG Touch Ergonomics)

---

## 🎯 ภารกิจหลัก (Objective)
ทำการ **"ตรวจสอบเชิงลึก ตรวจจับบั๊ก และค้นหาจุดบกพร่องของหน้า Editor (`frontend/src/components/editor/` และ `SequencePlayer.jsx`)"** อย่างละเอียดทุกซอกทุกมุม เพื่อยกระดับประสบการณ์การตัดต่อให้แม่นยำ ลื่นไหล ไร้ข้อผิดพลาด โดยมี **"กฎเหล็กห้ามกระทบของเดิมเด็ดขาด (Strict Zero-Regression & Non-Destructive Contract)"**

---

## ⛔ กฎเหล็ก: สิ่งที่ "ห้ามกระทบของเดิมเด็ดขาด" (STRICT DON'Ts)
1. ❌ **ห้ามทำให้ Preview != Render:** การแสดงผลตัวหนังสือ, ตำแหน่งซับ, สีไฮไลต์ `#66FF00`, ขนาดฟอนต์ `Mali-Bold 88px` ใน `SequencePlayer.jsx` ต้องตรงกับ `subtitle_engine.py` และ `test_preview_render_parity.py` 100%
2. ❌ **ห้ามเปลี่ยนโครงสร้าง Manifest (`draft_content.json`):** การ Save/Load สถานะโปรเจกต์ต้อง Round-trip ได้สมบูรณ์ ห้ามทำคีย์ข้อมูลเสียง (voiceEdit, microCuesList, tracks) สูญหายหรือเพี้ยน
3. ❌ **ห้ามทำลายคีย์ลัดเดิม (Keyboard Shortcuts):** Space (Play/Pause), Q (Trim Head), W (Trim Tail), C (Split), J/K/L (Shuttle), Z/Y (Undo/Redo) ต้องทำงานได้ตามปกติ 100%
4. ❌ **ห้ามกระทบระดับเสียงของ Audio Mix Bus:** Voice (1.0), SFX (0.28), BGM (0.12/0.14) และการตัดเสียงเชื่อมรอยต่อ (15ms crossfade ramps) ต้องคงเดิมตาม `scripts/config.py`
5. ❌ **ห้ามลบ/เขียนทับวัตถุดิบจริงใน `01_Raw/` และ `02_Assets/`**

---

## 🔍 แผนผังตรวจสอบ 9 สถานีของหน้า Editor (Editor Audit Traversal Matrix)

ให้เข้าตรวจและรายงานผลทีละสถานีตามลำดับนี้:

### 📍 สถานีที่ 1: เครื่องเล่นวิดีโอแนวตั้ง 9:16 (`SequencePlayer.jsx`)
- [ ] **1.1 Video Aspect Ratio & Stage:** สัดส่วน 9:16 (1080x1920) ตรงเป๊ะ ไม่ถูกบีบหรือยืดในทุกขนาดหน้าจอ (Desktop จอแบน / iPhone 15 Pro Max จอแคบ)
- [ ] **1.2 Frame-Accurate Playhead Sync:** วิดีโอเล่นตรงกับหัวอ่านไทม์ไลน์ ไม่มีอาการภาพดีเลย์หรือกระตุก
- [ ] **1.3 Double-Tap & Touch Controls:** แตะ 2 ครั้งบนวิดีโอเพื่อ Play/Pause และมีแอนิเมชัน Ripple นุ่มนวล
- [ ] **1.4 TikTok Safe Zone Overlay:** มีเส้นไกด์แสดงขอบเขตปลอดภัยของ TikTok (ขอบล่าง 420px, แถบปุ่มขวา 120px) แตะเปิด-ปิดได้ชัดเจน
- [ ] **1.5 Supersub Rendering Parity:** ซับไตเติลภาษาไทย `Mali-Bold 88px` มีขอบดำ 5.2px, คำไฮไลต์เขียวนีออน `#66FF00`, การตัดพยางค์ไม่ขาดวิ่น (Syllable Clustering), และ Progressive Ghost Reveal ทำงานสมบูรณ์

### 📍 สถานีที่ 2: ไทม์ไลน์มัลติแทร็ก & หัวอ่าน (`Timeline.jsx` + `TimelinePlayhead.jsx` + `TimelineRuler.jsx`)
- [ ] **2.1 Scrubbing Smoothness:** ลากหัวอ่าน (Playhead) ลื่นไหล ไม่หน่วง และมี `touch-action: none` ป้องกันไม่ให้เบราว์เซอร์แย่งเลื่อนหน้าจอ
- [ ] **2.2 Playhead Visibility:** ก้านหัวอ่านสีขาวหนา 3.5px มีหมุดจับด้านบนชัดเจน มองเห็นง่ายแม้นิ้วบัง
- [ ] **2.3 Multi-Level Zooming:** การซูมไทม์ไลน์ (10px/s ถึง 500px/s) แบบ Logarithmic Scale รูดลื่น และมีปุ่มลัด Zoom to Fit
- [ ] **2.4 Timecode & Ruler Markers:** แถบสเกลเวลาแบ่งเป็นวินาทีและเฟรมอย่างแม่นยำ ไม่เพี้ยนตามอัตราเฟรมเรต 30 FPS

### 📍 สถานีที่ 3: การจัดการคลิป & ฟิล์มสตริป (`TimelineClip.jsx` + `ClipFilmstrip.jsx` + `TrimAdjustModal.jsx`)
- [ ] **3.1 Trimming Edge Ergonomics:** การจับขอบคลิปเพื่อยืด-หด (Trim) ไม่หลุดง่าย มี Threshold ป้องกันการลากหดจนคลิปหาย (MIN_REMAINING_SECONDS)
- [ ] **3.2 Filmstrip Thumbnail Caching:** รูปพรีวิวเฟรมในคลิปโหลดเร็วและไม่เกิด Memory Leak เมื่อมีจำนวนคลิปเยอะ
- [ ] **3.3 J-Cut Transition Preview:** รอยต่อของภาพและเสียงเหลื่อมกัน 150-250ms แสดงผลบนไทม์ไลน์ถูกต้อง
- [ ] **3.4 Clip Selection & Ripple Edit:** การเลือกคลิปมีขอบสว่างนีออนชัดเจน และการลบคลิปมีตัวเลือกว่าจะดึงคลิปข้างหลังมาชิด (Ripple) หรือไม่

### 📍 สถานีที่ 4: ระบบผสมเสียงมัลติบัส (`editorAudioBus.js` + `VoiceEditNotice.jsx` + `MixDegradedNotice.jsx`)
- [ ] **4.1 4-Bus Audio Architecture:** ตรวจสอบ Bus Voice, SFX, BGM, Clip Audio ว่าแยกกันเป็นอิสระ
- [ ] **4.2 Non-Destructive Voice Cut Ramps:** เมื่อตัดต่อเสียงพูด รอยตัดต้องมี Crossfade Linear Ramp 15ms ป้องกันเสียง "แป๊ก/คลิก" ที่รอยต่อ
- [ ] **4.3 Audio Context Lifecycle:** เมื่อกด Pause เสียงต้องเงียบสนิททันที และเมื่อ Unmount ต้องสั่ง `audioContext.close()` ป้องกัน Memory Leak
- [ ] **4.4 Solo / Mute State Integrity:** การกด Solo หรือ Mute แทร็กใดแทร็กหนึ่ง ต้องไม่ทำให้สถานะระดับเสียงที่เซฟไว้เพี้ยน

### 📍 สถานีที่ 5: แผงตรวจคำและซับไตเติล (`CaptionInspector.jsx` + `CuesTranscriptInspector.jsx`)
- [ ] **5.1 In-Place Text Editing:** แตะแก้คำผิดในบทพูดได้ทันทีโดยไม่ต้องส่งไปเรนเดอร์ใหม่ทั้งคลิป
- [ ] **5.2 Thai Rule Linter:** ตรวจจับคำต้องห้ามอัตโนมัติ (ห้ามมีจุดไข่ปลา `...` หรือ `…`, ห้ามคำทับศัพท์อังกฤษที่สะกดเพี้ยน)
- [ ] **5.3 Syllable Timestamp Bounds:** การขยับเวลาของคำ ต้องไม่ทำให้คำข้างหน้าและข้างหลังทับซ้อนกัน

### 📍 สถานีที่ 6: ตัวควบคุมโอเวอร์เลย์และสติกเกอร์ (`OverlayInspector.jsx` + `StickerInspector.jsx` + `CutoutInspector.jsx`)
- [ ] **6.1 Background Cutout Preview:** สลับดูเลเยอร์ภาพคนไดคัท (SAM2 / Rembg) กับเลเยอร์พื้นหลังได้ถูกต้อง
- [ ] **6.2 Universal Badges Compliance:** สติกเกอร์ที่ใส่ต้องเป็นไปตาม Universal Badges 6 แบบ ไม่มีการพิมพ์ข้อความเฉพาะสินค้าลงบนสติกเกอร์ (Rule 3.6)
- [ ] **6.3 Z-Index Layer Ordering:** ลำดับเลเยอร์ถูกต้อง (Video ➜ Subject Cutout ➜ Overlays ➜ Subtitles Foregrounded เสมอ)

### 📍 สถานีที่ 7: แถบเครื่องมือและพรีเซ็ต (`Toolbar.jsx` + `StylePresetPicker.jsx` + `RenderButton.jsx`)
- [ ] **7.1 Button Verbal Cleanliness:** ปุ่มทุกปุ่มต้องขึ้นต้นด้วยคำกริยาและไม่มีไอคอนสัญลักษณ์นำหน้า (Rule 3.8 / 4.8)
- [ ] **7.2 Mobile Touch Sizing:** ปุ่มคำสั่งใน Toolbar ต้องมีขนาดสัมผัสไม่ต่ำกว่า 44x44px
- [ ] **7.3 Style Preset Consistency:** การสลับพรีเซ็ตสไตล์คลิป (#5 Couple Paper Chat หรือ Gadget Pro) ต้องไม่ลบล้างการตัดต่อที่ทำค้างไว้

### 📍 สถานีที่ 8: การเซฟสถานะและการกู้คืน (`EditorShell.jsx` + `workspaceCoordinator.js`)
- [ ] **8.1 Debounced Auto-Save:** ระบบ Autosave ต้องไม่ยิง Request ถี่เกินไป และต้องไม่บล็อกการตัดต่อของผู้ใช้
- [ ] **8.2 Project Conflict Guard (`ProjectRevisionNotice.jsx`):** มีการเตือนเมื่อโปรเจกต์มีการเปลี่ยนแปลงจากที่อื่น ป้องกันการเซฟทับงานโดยไม่รู้ตัว
- [ ] **8.3 Screen Wake Lock:** หน้าจอไม่ดับระหว่างกำลังพรีวิวหรือเรนเดอร์ (`useWakeLock`)

### 📍 สถานีที่ 9: การตรวจสอบความสมบูรณ์ 100% ผ่านชุดทดสอบอัตโนมัติ
- [ ] **9.1 Frontend Vitest Suite:** รัน `cd frontend; npm test -- --run` ทุกเทส (1,055/1,055) ต้องผ่าน 100%
- [ ] **9.2 Backend Pytest Suite:** รัน `pytest` ทุกเทส (80/80) ต้องผ่าน 100%
- [ ] **9.3 Preview-Render Parity Test:** รัน `pytest tests/test_preview_render_parity.py` ต้องผ่านฉลุย ไร้ข้อแตกต่าง

---

## 📑 รูปแบบรายงานผลการตรวจ (Audit Output Format)
เมื่อทำการตรวจเสร็จสิ้น ให้สรุปรายงานตามโครงสร้าง 4 ส่วนนี้:
1. 🟢 **จุดแข็งและส่วนที่สมบูรณ์แล้ว (Verified Strengths & Parity):** ฟังก์ชันที่ทำงานได้ถูกต้องแม่นยำตามสเปก
2. 🔴 **บั๊กหรือความเสี่ยงที่พบ (Latent Bugs & Edge-Case Flaws):** ระบุชื่อไฟล์ บรรทัด และผลกระทบต่อผู้ใช้
3. 🟡 **ข้อเสนอแนะในการปรับปรุง UX/UI (Refinement Opportunities):** จุดที่ปรับแล้วจะช่วยให้ลื่นไหลขึ้น โดยแบ่งตามระดับความสำคัญ (P1 เร่งด่วน, P2 ปานกลาง, P3 เล็กน้อย)
4. 🛡️ **แผนผังการปรับปรุงแบบ Non-Destructive (Surgical Patching Plan):** อธิบายขั้นตอนการแก้โดยยืนยันว่าจะไม่กระทบฟังก์ชันเดิม 100%

เริ่มการตรวจสอบสถานีที่ 1 ได้ทันทีครับ!
```
