# ⏱️🖥️ MASTER PROMPT: 1-Hour Autonomous Desktop NLE Refinement Loop for Editor Screen
# พรอมต์แม่บทกะ 1 ชั่วโมงเต็ม: ปรับแต่งหน้า Editor โหมดเดสก์ท็อปให้ทรงพลัง ลื่นไหล ระดับ Premiere Pro / CapCut Desktop

```markdown
/goal /impeccable /ui-ux-pro-max /clean-refactor /profiler-opt /tdd

## 🌟 คำสั่งปฏิบัติการกะ 1 ชั่วโมงเต็ม (1-Hour Autonomous Desktop NLE Sprint)
คุณได้รับมอบหมายให้สวมบทบาท **"Lead NLE Systems Architect & Desktop UI Specialist"** ดำเนินการตรวจสอบ ยกระดับ และขัดเกลาหน้า **Editor (`EditorShell.jsx` และคอมโพเนนต์ย่อยทั้งหมด)** ในมุมมอง **Desktop ขนาดใหญ่ (1920×1080 / 1440p / 4K Ultrawide)** อย่างต่อเนื่อง **"เต็มเวลา 1 ชั่วโมง (60 นาที)"** แบบอัตโนมัติ ห้ามหยุดกลางคัน และห้ามถามคำถามยิบย่อย

---

## ⛔ กฎเหล็กความปลอดภัย: ห้ามกระทบของเดิมเด็ดขาด (Strict Non-Destructive Contract)
1. ❌ **Preview = Render 100%:** ซับไตเติล `Mali-Bold 88px`, สีไฮไลต์ `#66FF00`, การแสดงผลพยางค์ และ Progressive Reveal ใน `SequencePlayer.jsx` ต้องตรงกับ `subtitle_engine.py` และผ่าน `test_preview_render_parity.py` เสมอ
2. ❌ **Manifest Round-Trip Integrity:** ห้ามดัดแปลงโครงสร้างคีย์ของ `draft_content.json` (`voiceEdit`, `microCuesList`, `tracks`) ที่จะทำให้ข้อมูลโปรเจกต์เดิมพัง
3. ❌ **Shortcuts Preserved:** คีย์ลัดหลักทั้งหมด (Space, Q, W, C, J, K, L, Z, Y) ต้องคงเดิมและแม่นยำยิ่งขึ้น
4. ❌ **Audio Mix Stability:** ระดับเสียง Voice 1.0, SFX 0.28, BGM 0.12/0.14 และ Crossfade Ramp 15ms ต้องคงตามสเปก
5. ❌ **ชุดทดสอบ 1,055/1,055 tests:** ต้องผ่าน 100% ทุกครั้งก่อนจบแต่ละรอบ

---

## 🖥️ 6 เสาหลักยกระดับหน้า Editor ขนาด Desktop (Desktop NLE Mastery Matrix)

ทุกรอบการวนลูป ต้องเข้าตรวจและยกระดับ 6 เสาหลักนี้ให้สมบูรณ์แบบ:

### 📍 เสาหลักที่ 1: Pro 3-Column Split & Resizable Panes (การจัดเลย์เอาต์หน้าจอคอม)
- [ ] **1.1 Balanced 3-Column Layout:**
  * **ซ้าย (Asset Library):** คลังวัตถุดิบ ฟุตเทจ B-Roll ซาวด์ดนตรี แถบเลือกสไตล์
  * **กลาง (9:16 Stage):** หน้าจอพรีวิววิดีโอ 9:16 ขนาดใหญ่ คมชัด 60fps มีตัวบอกเวลา Timecode และปุ่ม Fullscreen
  * **ขวา (Deep Inspector):** แผงปรับแต่งคลิป, แก้บทพูด, ปรับซับ, ไดคัท SAM2, ตัวเลือกลุคโอเวอร์เลย์
  * **ล่าง (Multi-Track Timeline):** ไทม์ไลน์กว้างเต็มหน้าจอ จัดสรรพื้นที่ความสูงอย่างลงตัว
- [ ] **1.2 Smooth Drag Resizing & Persistence:**
  * ขอบกั้นระหว่างแผง (Splitters) สามารถใช้เมาส์คลิกลากปรับขนาดความกว้าง/สูงได้อย่างลื่นไหล
  * จดจำขนาดแผงที่ผู้ใช้ปรับไว้ลงใน `localStorage` เมื่อรีเฟรชหน้าจอไม่ต้องปรับใหม่
- [ ] **1.3 Quick Collapse / Expand Toggles:** ปุ่มพับ-ขยายแผงซ้ายและขวา (`PanelLeftClose`, `PanelRightClose`) ทำงานนุ่มนวลด้วย CSS transitions

### 📍 เสาหลักที่ 2: ไทม์ไลน์เดสก์ท็อปและเมาส์ขั้นสูง (Timeline & Mouse Ergonomics)
- [ ] **2.1 Precision Wheel Navigation:**
  * เลื่อนล้อเมาส์ธรรมดา (Wheel) = เลื่อนไทม์ไลน์ซ้าย-ขวา (Horizontal Scroll)
  * กด `Ctrl + Wheel` = ซูมเข้า-ออกไทม์ไลน์โดยยึดตำแหน่งเคอร์เซอร์เมาส์เป็นศูนย์กลาง (Anchored Zoom)
- [ ] **2.2 Frame-Accurate Playhead Scrubbing:** ลากหัวอ่านได้ละเอียดระดับเสี้ยวเฟรม พร้อม Snapping ติดขอบคลิปและมาร์กเกอร์จังหวะดนตรี (Beat Snap Points)
- [ ] **2.3 Distinct Color-Coded Tracks:** แยกสีแทร็กชัดเจนตามมาตรฐาน Pro NLE:
  * แทร็กภาพวิดีโอ (Video): สีนีออนฟ้า Cyan
  * แทร็กเสียงพากย์ (Voice): สีนีออนส้ม Amber พร้อมรูปคลื่นเสียง (Waveform)
  * แทร็กเอฟเฟกต์เสียง (SFX): สีนีออนม่วง Violet
  * แทร็กดนตรีเบื้องหลัง (BGM): สีนีออนเขียวมรกต Emerald
- [ ] **2.4 Multi-Selection & Range Marking:** รองรับการลากเมาส์ครอบเพื่อเลือกหลายคลิป (Marquee Selection) และการกด I / O เพื่อมาร์กจุด In / Out

### 📍 เสาหลักที่ 3: ระบบคีย์ลัดมืออาชีพ (Pro NLE Keyboard Shortcuts)
- [ ] **3.1 Shuttle Playback (J / K / L):**
  * `L` = เล่นไปข้างหน้า (กดซ้ำเพื่อเร่งสปีด 2x / 4x)
  * `K` = หยุดเล่น (Pause)
  * `J` = เล่นถอยหลัง (กดซ้ำเพื่อเร่งสปีดถอยหลัง 2x / 4x)
- [ ] **3.2 Precision Step Navigation:**
  * ลูกศร ซ้าย / ขวา = เลื่อนทีละ 1 เฟรม (1/30 วินาที)
  * `Shift + ลูกศร ซ้าย / ขวา` = เลื่อนทีละ 1 วินาที (30 เฟรม)
- [ ] **3.3 Trimming & Splitting:**
  * `Q` = Ripple Trim Head (ตัดหัวคลิปทิ้งจนถึงหัวอ่าน)
  * `W` = Ripple Trim Tail (ตัดท้ายคลิปทิ้งตั้งแต่หัวอ่าน)
  * `C` = Razor Split (ตัดแบ่งคลิป ณ ตำแหน่งหัวอ่าน)
  * `Shift + Z` = Zoom to Fit (ซูมไทม์ไลน์พอดีหน้าจอ)

### 📍 เสาหลักที่ 4: สุนทรียภาพ Dark Glassmorphism Studio (Pulse Hub Aesthetic)
- [ ] **4.1 Studio Dark OLED Palette:** พื้นหลังแคนวาส `#030509` คอนทราสต์ตัดกับแผงคอนโทรล `#0b1120` สบายตาสำหรับการตัดต่อเป็นเวลานาน
- [ ] **4.2 Subtle Glass Surfaces:** แผงควบคุมใช้ `.glass-panel` ขอบบนมีเส้นแสง 1px Specular Rim Light, แสงสะท้อน 38% Curvature Sheen เบาบาง ไม่แย่งความสนใจจากวิดีโอ
- [ ] **4.3 Typography & Readability:** ใช้ฟอนต์ `Anuphan` ตัวเลขอ่านง่าย คมชัดทุกขนาด ไม่มีอาการเบลอหรือฟอนต์ล้นกรอบ

### 📍 เสาหลักที่ 5: แผงควบคุมเสียงและมิกเซอร์เดสก์ท็อป (Audio Mixer & VU Meters)
- [ ] **5.1 4-Bus Desktop Channel Strips:** แผงปรับระดับเสียง Voice, SFX, BGM, Clip Audio มี Fader แนวนอน/แนวตั้งที่จับลากง่าย
- [ ] **5.2 Quick Mute / Solo States:** ปุ่ม M (Mute) และ S (Solo) มีไฟสีสว่างชัดเจนเมื่อเปิดใช้งาน
- [ ] **5.3 Voice Cut Integrity Notice:** มีแถบเตือนสถานะการตัดต่อเสียง (VoiceEditNotice) แสดงชัดเจน ไม่เกะกะสายตา

### 📍 เสาหลักที่ 6: การเซฟงานและการป้องกันข้อมูลสูญหาย (Autosave & State Integrity)
- [ ] **6.1 Debounced Auto-Save Indicator:** สัญลักษณ์ไฟสถานะเซฟงาน (Saving ➜ Saved) แสดงมุมขวาบนอย่างนุ่มนวล
- [ ] **6.2 Conflict Protection:** ระบบเตือนเมื่อมีการแก้ไขจากภายนอก ป้องกันการเขียนทับงานโดยไม่ตั้งใจ
- [ ] **6.3 Zero Memory Leak:** ตรวจสอบและเคลียร์ Web Audio Context, Event Listeners เมื่อปิดหรือรีโหลดหน้า Editor

---

## 🔁 ระเบียบลูป 1 ชั่วโมงเต็ม (1-Hour 4-Cycle Iterative Protocol)

ให้แบ่งการทำงานออกเป็น **4 รอบย่อย (Cycles)** รอบละประมาณ 12–15 นาที เพื่อเก็บรายละเอียดจนครบ 60 นาที:

```
[นาทีที่ 00 - 15] ── รอบ Cycle 1: เลย์เอาต์เดสก์ท็อป 3 แผง & Resizable Splitters + Persistence
[นาทีที่ 15 - 30] ── รอบ Cycle 2: ไทม์ไลน์เมาส์ขั้นสูง, Ctrl+Wheel Zoom, สีแทร็ก และ Snapping
[นาทีที่ 30 - 45] ── รอบ Cycle 3: คีย์ลัดมืออาชีพ J/K/L Shuttle, 1-Frame Step, Q/W Trimming
[นาทีที่ 45 - 60] ── รอบ Cycle 4: ธีมสตูดิโอกระจกเข้ม Dark Glass, แผงมิกเซอร์เสียง & สรุปผล
```

### ในแต่ละรอบย่อยให้ปฏิบัติดังนี้:
1. **Audit:** ส่องโค้ดหาจุดที่ต้องยกระดับในเสาหลักประจำรอบ
2. **Execute:** ลงมือเขียนโค้ดและปรับปรุงไฟล์อย่างประณีต
3. **Verify Tests:** รัน `cd frontend; npm test -- --run` ทุกเทส (1,055/1,055) ต้องผ่าน 100%
4. **Build Check:** รัน `cd frontend; npm run build` เพื่อให้แน่ใจว่า Production Bundle สมบูรณ์
5. **Git Commit:** ทำ Git Commit แยกในแต่ละรอบ พร้อมบันทึกลง `TODO.md`
6. **Next Cycle:** เข้าสู่รอบถัดไปทันทีจนกว่าจะครบ 1 ชั่วโมง!

---

## 🏁 สิ่งที่ต้องส่งมอบเมื่อครบ 1 ชั่วโมง (End-of-Hour Deliverable)
เมื่อครบเวลา 60 นาที ให้จัดทำเอกสารสรุปผลไว้ที่:
`_Docs/Reports/EDITOR_DESKTOP_1HOUR_SPRINT_<YYYYMMDD>.md`
ระบุ:
- รายละเอียดสิ่งที่ได้รับการอัปเกรดทั้ง 4 รอบ
- รายการคีย์ลัดและฟังก์ชันเมาส์ที่พร้อมใช้งานบนเดสก์ท็อป
- ผลการทดสอบ (Vitest 100% Pass)
- ยืนยัน Zero-Regression ว่าของเดิมยังทำงานได้สมบูรณ์ 100%

**เริ่มนับเวลาและเริ่มรอบ Cycle 1 ได้ทันทีครับ!**
```
