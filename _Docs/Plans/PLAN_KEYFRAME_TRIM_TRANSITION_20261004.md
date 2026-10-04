# แผนงานยกระดับฟีเจอร์การตัดต่อ (CapCut Gap: Keyframe UI, Trim to Playhead, Transition)
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)
วันที่: 2026-10-04
สถานะ: วางแผนแล้ว พร้อมเริ่มลงมือหลังได้รับการยืนยัน

---

## 🎯 1. วัตถุประสงค์
ยกระดับประสบการณ์การตัดต่อของ OmniCut Pro Studio ให้เทียบเท่าและเหนือกว่า CapCut Desktop PC ตามผลการสำรวจ Gap Analysis (`_Docs/Reports/CAPCUT_EDITOR_GAP_20261003/00_SUMMARY.md`) โดยโฟกัส 3 ฟีเจอร์ตัดต่อที่มีผลต่อความเร็วและคุณภาพงานสูงสุด:
1. **ระบบ Keyframe UI บนไทม์ไลน์และ Inspector (T9):** เติมเต็มการใช้งานคีย์เฟรมด้วยปุ่มรูปเพชร (Diamond ◆/◇) และแสดง Marker บนไทม์ไลน์
2. **ปุ่มลัดและปุ่ม UI Trim to Playhead (Q / W) (L1-02):** ตัดหัวคลิปและท้ายคลิปให้วิ่งมาชนหัวอ่านได้ในคลิกเดียวจาก Toolbar และคีย์บอร์ด
3. **Transition & Subtitle Sync Guard (L5-05):** ตรวจสอบและดูแลความสอดคล้องของข้อความ/ซับไตเติลเมื่อใส่ Transition บนรอยต่อคลิป

---

## 🔍 2. รายละเอียดสถาปัตยกรรมและการเปลี่ยนแปลง

### 2.1 ปุ่มลัดและปุ่ม UI Trim to Playhead (Q / W)
- **ปัญหา:** ปัจจุบันระบบมี logic `resolveTrimHead`/`resolveTrimTail` ใน `timelineTrimOps.js` และรองรับคีย์บอร์ด Q/W ใน `editorShortcutKeys.js` แล้ว แต่ **ยังไม่มีปุ่มบนแถบเครื่องมือ Toolbar** ทำให้ผู้ใช้ที่ไม่ได้จำคีย์ลัดคลิกตัดหัว/ท้ายไม่ได้
- **การเปลี่ยนแปลง:**
  1. `frontend/src/components/editor/Toolbar.jsx`:
     - เพิ่มปุ่ม `ตัดหัวถึงหัวอ่าน (Q)` (ไอคอนตัดหัวคลิป) ถัดจากปุ่มแยก (Scissors)
     - เพิ่มปุ่ม `ตัดท้ายถึงหัวอ่าน (W)` (ไอคอนตัดท้ายคลิป)
     - ผูกเข้ากับ `onTrimHead` และ `onTrimTail` พร้อมแสดง tooltip และ shortcut ชัดเจน
  2. `frontend/src/components/editor/EditorShell.jsx`:
     - ส่ง `trimHeadAtPlayhead` และ `trimTailAtPlayhead` ลงมาที่ `Toolbar`

### 2.2 ระบบ Keyframe UI บนไทม์ไลน์และ Inspector (T9)
- **ปัญหา:** Backend (`video_editor.py:884-1039`) และพรีวิว (`timelineMath.js:120-144`) รองรับการเรนเดอร์คีย์เฟรมแบบ dynamic camera (zoom, pan_x, pan_y) ครบแล้ว แต่หน้าเว็บขาด UI สำหรับวางคีย์เฟรมอิสระ ทำให้งาน T9 (ซูมเข้า/ออกตามช่วงเวลา) ทำไม่ได้จาก UI
- **การเปลี่ยนแปลง:**
  1. `frontend/src/components/editor/Inspector.jsx`:
     - ส่ง `playhead` เข้า `ClipInspector` เพื่อให้รู้ตำแหน่งเวลาปัจจุบันของหัวอ่านบนคลิป
  2. `frontend/src/components/editor/inspector/ClipInspector.jsx`:
     - คำนวณ `motionTime = motionTimeAt(selectedSeg, playhead)`
     - ตรวจสอบว่าที่ `motionTime` มี keyframe หรือไม่ (`hasKeyframeAtPlayhead`)
     - เพิ่ม **ปุ่มรูปเพชร (Diamond Icon ◆ / ◇)** ข้างหัวข้อ "กรอบภาพ / ซูม / เลื่อน":
       - **Active (◆ สีส้ม/ฟ้าเรืองแสง):** เมื่อหัวอ่านอยู่ตรงจุดคีย์เฟรมเดิม -> คลิกเพื่อลบคีย์เฟรม ณ จุดนั้น
       - **Inactive (◇ เส้นขอบโปร่ง):** เมื่อหัวอ่านยังไม่มีคีย์เฟรม -> คลิกเพื่อเพิ่มคีย์เฟรมใหม่ ณ จุดนั้นด้วยค่าปัจจุบัน
     - เพิ่มปุ่มกระโดด **ก่อนหน้า ◀** และ **ถัดไป ▶** เพื่อเลื่อนหัวอ่านไปยังจุดคีย์เฟรมของคลิปนั้นอย่างแม่นยำ
     - เมื่อลาก Slider ซูม/เลื่อนในขณะที่คลิปมี keyframe และหัวอ่านตรงจุด -> อัปเดต keyframe ณ จุดนั้น
  3. `frontend/src/components/editor/TimelineClip.jsx`:
     - แสดง **Diamond Marker (◆)** สีทอง/ส้ม บนแถบไทม์ไลน์ของคลิปตามเวลา `kf.time * pxPerSec`
     - แสดง tooltip บอกเวลาเมื่อ hover
  4. `frontend/src/lib/timelineMath.js` (L1-14 Split Keyframe Guard):
     - ในฟังก์ชัน split clip ปรับปรุงให้ตัดแบ่งและ offset เวลาของ `keyframes` ให้คลิปท่อนขวาอย่างแม่นยำ ป้องกันคีย์เฟรมเพี้ยนหลังการ split

### 2.3 Transition Sync & Verification
- ตรวจสอบ `transitionControls.js` และการวาง Transition บน Timeline
- ตรวจสอบว่าเมื่อใส่ Transition ที่มีความยาว overlap ไม่ทำให้ข้อความซับไตเติลที่ผูกกับเสียงพากย์คลาดเคลื่อน
- เพิ่มชุดทดสอบ unit tests และ parity tests ครอบคลุมการทำงานทั้งหมด

---

## 📋 3. แผนการดำเนินงาน (Todo Checklist)

- [ ] **Phase 1: Trim to Playhead Toolbar Integration (Q / W)**
  - [ ] 1.1 ปรับ `Toolbar.jsx` เพิ่มปุ่ม `ตัดหัวถึงหัวอ่าน` (Trim Head, Q) และ `ตัดท้ายถึงหัวอ่าน` (Trim Tail, W)
  - [ ] 1.2 ปรับ `EditorShell.jsx` ส่งคำสั่ง `trimHeadAtPlayhead` และ `trimTailAtPlayhead` เข้า `Toolbar`
  - [ ] 1.3 ทดสอบการตัดคลิปผ่านปุ่ม Toolbar และคีย์ลัด Q/W (ตรวจสอบการ ripple และ playhead seek)
- [ ] **Phase 2: Keyframe UI (Diamond Icon & Timeline Markers)**
  - [ ] 2.1 ปรับ `Inspector.jsx` ส่ง `playhead` ให้ `ClipInspector`
  - [ ] 2.2 ปรับ `ClipInspector.jsx` เพิ่มปุ่มรูปเพชร (Diamond ◆/◇) สำหรับ Add/Remove Keyframe และปุ่มกระโดด ◀ ▶
  - [ ] 2.3 ปรับ `TimelineClip.jsx` วาดมาร์กเกอร์รูปเพชร ◆ บนแทร็กวิดีโอตามตำแหน่งเวลาคีย์เฟรมจริง
  - [ ] 2.4 ปรับปรุง `splitClipAt` ใน `timelineMath.js` ให้แบ่ง keyframe ไปยังคลิปท่อนขวาได้อย่างถูกต้อง (แก้ L1-14)
- [ ] **Phase 3: Transition Sync & Safety Checks**
  - [ ] 3.1 ตรวจสอบความเข้ากันได้ของการเปลี่ยน Transition กับการเล่นพรีวิวและตำแหน่งซับไตเติล
  - [ ] 3.2 ตรวจสอบข้อความเตือนเมื่อ Transition ซ้อนทับเกินความยาวคลิป
- [ ] **Phase 4: Automated Tests, Parity Verification & Build**
  - [ ] 4.1 เขียน unit tests สำหรับ Keyframe Diamond Operations และ Split Keyframe
  - [ ] 4.2 รันชุดทดสอบ frontend (`npm test`) และ backend (`pytest`)
  - [ ] 4.3 รัน `npm run build` ตรวจสอบความถูกต้อง 100%
