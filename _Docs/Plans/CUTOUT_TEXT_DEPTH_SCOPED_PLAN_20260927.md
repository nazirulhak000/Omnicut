# แผนจัดชั้นข้อความและ Cutout เฉพาะช่วงที่ใช้

วันที่ 2026-09-27 · ดำเนินการโดย: Codex (GPT-6) · สถานะ: ออกแบบ รอตรวจทานก่อนแก้ production code

## 1. ผลลัพธ์ที่ผู้ใช้จะได้

- ข้อความบน Timeline แต่ละชิ้นเลือกว่า **หน้าสินค้า** หรือ **หลังสินค้า** ได้ โดยช่วงเวลาและตำแหน่งข้อความเดิมไม่เปลี่ยน
- เมื่อเลือกหลังสินค้า ระบบแสดงภาพ 3 ชั้น: คลิปเดิม → ข้อความ → สินค้า Cutout เฉพาะเวลาที่ข้อความนั้นแสดง
- ระบบเตรียม Cutout เฉพาะ source frames ที่จำเป็นต่อข้อความหลังสินค้า ไม่ใช้ทุกช่วงของคลิปโดยไม่จำเป็น แสดงจำนวนงาน/วินาที/เฟรมก่อนเริ่ม
- หลายข้อความที่ทับกันใช้ Cutout ช่วงเดียวกันได้ ช่วงที่แยกกันไม่ต้องประมวลผลช่องว่าง
- ถ้า Cutout ยังไม่พร้อม Preview และ Render แจ้งช่วงที่ขาดตามจริง ไม่แสดงผลที่ดูเหมือนพร้อม

## 2. พฤติกรรมเดิมที่ต้องรักษา

1. โปรเจกต์ที่ไม่มีฟิลด์ใหม่ต้องโหลด บันทึก และ Render เหมือนเดิม: Hook เดิมอยู่หลังสินค้าเมื่อเปิด Cutout; Text Overlay, caption, callout, sticker และ watermark อยู่หน้าสินค้า
2. Cutout แบบเดิมยังอ่าน artifact ที่ผูกกับคลิป, `cutout.webm` รุ่นใหม่ และ PNG sequence ของโปรเจกต์เก่าได้ ไม่ย้ายหรือล้าง cache เดิมอัตโนมัติ
3. ค่า `background_isolation.enabled`, model/quality/fallback, ปุ่มเตรียม Cutout, โหมดดู Mask, การยกเลิกงาน และ render bypass เดิมทำงานต่อ
4. ไม่เปลี่ยนข้อความ, font family/size/weight/outline, ตำแหน่ง, animation, safe zone, ระดับเสียง, หรือการตัดคลิปของโปรเจกต์เก่า
5. การบันทึกไม่เขียนทับไฟล์ดราฟต์ CapCut; การทดลองใช้ `.tmp/` และ fixture เท่านั้น

## 3. สิ่งที่โค้ดทำอยู่ตอนนี้

- `backgroundIsolationPreview.js` แยก Hook (`kind=hook`/`type=hook_header`) ไปชั้นหลังสินค้า ส่วน overlay อื่นไปชั้นหน้า
- `SequencePlayer.jsx` วาดคลิป → Hook → Cutout subject → caption/text หน้า ใน Canvas
- `background_isolation_compositor.py` แยก ASS ด้วย **ชื่อ Style ของ Hook**; `video_editor.py` ใส่ subject layer ของคลิปที่มี artifact หลัง Hook ทั้งช่วงคลิป
- `EditorShell.jsx` สร้างงาน Cutout จาก `trim_start..trim_end` ของคลิปทั้งหมดบน Timeline รวม source windows ที่ทับหรือติดกัน งานละ 30 fps / 1080×1920; artifact ปัจจุบันผูกกับคลิป จึงยังแทนหลายช่วงแยกภายในคลิปเดียวไม่ได้
- `editorProjectState.js` เก็บฟิลด์ overlay ที่ไม่รู้จักแบบ lossless จึงเพิ่มฟิลด์ใหม่แบบ additive ได้ แต่ต้องตรวจ API save/reload และ Timeline v2 ด้วย

## 4. สัญญาข้อมูลใหม่

### 4.1 ตำแหน่งข้อความ

- เพิ่ม `subject_layer` บน Hook/Text Overlay แต่ละชิ้น รับเฉพาะ `"front"` หรือ `"behind"`; ไม่เพิ่มค่าเริ่มต้นลง manifest เก่าระหว่างโหลด
- Resolver กลางที่ใช้ทั้ง JS/Python: ฟิลด์ที่ถูกต้องมีสิทธิ์สูงสุด; ถ้าขาด ฟีลด์ Hook เดิม = `behind`, Text Overlay เดิม = `front`; ค่าผิดรูปแบบ = แจ้ง validation และไม่เปลี่ยนความหมายเก่าเงียบ ๆ
- `hidden=true`, ข้อความว่าง, หรือช่วงเวลาไม่ถูกต้องไม่สร้างงาน Cutout; ข้อความที่เลือก `front` ไม่สร้างงาน
- รอบแรกครอบคลุม Hook และ Text Overlay ที่เป็นรายการบน Timeline เท่านั้น Subtitle cues และ Product Callout คงอยู่หน้า; ไม่เปลี่ยนความหมายของซับเดิม

### 4.2 โหมดขอบเขต Cutout

- เพิ่ม `background_isolation.scope_mode`: ไม่พบฟิลด์ = `legacy_clip` เพื่อคงโปรเจกต์เก่า 100%; โหมดใหม่ = `behind_text_windows` ให้ใช้เฉพาะช่วงของข้อความที่ resolve เป็น `behind`
- เปิดโหมดใหม่ด้วย UI ชัดเจนหลังผู้ใช้ตรวจ preflight; ไม่สลับโหมดให้โปรเจกต์ที่เปิดอยู่เอง
- เก็บ `scoped_artifacts` เป็นรายการแยกจาก `clip.background_isolation.artifact` เดิม แต่ละรายการมี source identity, rotation, source start/end, FPS, model/quality/temporal mode, artifact ID, status และ revision ของแผน
- ไม่เก็บผลลัพธ์ตาม ID ของข้อความ เพราะหลายข้อความอาจใช้เฟรม source เดียวกัน และการแก้คำโดยไม่เปลี่ยนเวลาต้อง reuse cache ได้

## 5. คำนวณช่วงอย่างไร

1. อ่านช่วงแสดงผลของ overlay แบบครึ่งเปิด `[start,end)` ตาม Timeline 30 fps; ปัดขอบเขตเป็น frame index เดียวกันทั้ง Preview/Render
2. หา intersection ระหว่างช่วงข้อความ `behind` กับช่วงที่แต่ละคลิปมีภาพจริง รวมคลิปที่ทับกันระหว่าง transition
3. แปลง Timeline time ไป source time ผ่าน `timelineMath.js` ตาม `trim_start`, `trim_end`, speed และตำแหน่งคลิป; ไม่มีการอ้างความยาว Raw เป็นค่าเริ่มต้นถ้า source window ยังแก้ไม่ได้ ให้ preflight แจ้ง `unresolved`
4. จัดกลุ่มตาม source fingerprint + rotation + settings + FPS; รวมช่วงที่ทับหรือติดกัน ไม่รวมช่องว่างที่ไม่จำเป็น; ปัดช่วงขยายสำหรับการ seek/temporal model เป็นจำนวนเฟรมเล็กน้อยที่ระบุแยกใน preflight
5. คิด `jobs`, source seconds, source frames และจำนวนเฟรม padding ให้เห็นก่อนกดเตรียม; preview/render ใช้ **ช่วงแสดงข้อความจริง** เป็น gate แม้ artifact จะมี padding

ตัวอย่าง: Hook 0–5 วินาที กับ Text Overlay 20–23 วินาทีบน source เดียวกัน → 2 windows รวม 8 วินาที ≈ 240 เฟรมที่ 30 fps ก่อน padding; source windows ที่ซ้อนกันถูกรวมก่อนนับ

## 6. หน้าจอและการแก้ไข

- ใน Inspector ของ Hook/Text Overlay เพิ่มตัวเลือก `ตำแหน่งเทียบกับสินค้า: หน้าสินค้า | หลังสินค้า`; ค่าเริ่มต้นแสดงตาม resolver แม้ฟิลด์ยังไม่ถูกบันทึก
- บล็อกข้อความบน Timeline แสดงป้าย `หน้า` หรือ `หลัง`; ส่วน Cutout lane แสดงเฉพาะช่วงที่ต้องใช้พร้อมสถานะ `พร้อม/ยังไม่พร้อม/กำลังทำ/ล้าสมัย`
- เมื่อเปลี่ยนหน้า/หลังหรือเลื่อนเวลา ให้คำนวณแผนใหม่ทันทีและแสดงความต่างของจำนวนเฟรม; ไม่เริ่ม rembg อัตโนมัติระหว่างลาก
- ปุ่ม `เตรียม Cutout จาก Timeline` ใช้แผนที่แสดงไว้; ถ้าไม่มีข้อความหลังสินค้าให้แสดง `ไม่มีช่วงที่ต้องเตรียม` และ Render ทำงานปกติ
- Preview แสดงข้อความหลังสินค้าตามชั้นจริง; เมื่อ artifact ที่จำเป็นขาด ให้แสดงสถานะชัด ไม่ใช้ภาพ proxy หรือ cache ของโปรเจกต์อื่นมาแทน
- มี Undo/Redo, Save/Reload, keyboard selection และ accessibility label สำหรับค่าที่เลือก; ใช้ UI กริยาและข้อความตามกฎเดิม

## 7. Preview, Render และ cache

### Preview

- เปลี่ยน `splitBackgroundIsolationOverlays` ให้ใช้ resolver ต่อรายการ แทน hardcode Hook; จับ `subject_layer` เดียวกันกับ Inspector/Timeline
- เลือก artifact ตาม source time ภายใน scoped window; หากเฟรมปัจจุบันอยู่นอกช่วงหลังสินค้า ไม่โหลดหรือวาด Cutout
- ใช้ master/proxy ที่มีอยู่โดยตรวจ artifact ID/frame mapping; โหมดดู Mask และการ seek ยังทำงาน

### Render

- สร้าง Behind/Front ASS passes จาก **overlay identity/subject_layer** ไม่อาศัยชื่อ Style เพียงอย่างเดียว; event ประกอบ เช่นเงา/พื้นหลังข้อความ/animation ต้องอยู่ชั้นเดียวกันทั้งหมด
- ประกอบ subject stream เฉพาะช่วง Timeline ที่ Behind overlay ใช้งาน รองรับหลาย scoped artifacts ในคลิปเดียว; ข้างนอกใช้คลิปเดิมโดยไม่มี subject overlay
- ตรวจว่าทุก Behind interval มี artifact ครอบคลุมครบด้วย fingerprint/settings/revision ก่อนเริ่ม FFmpeg; หากไม่ครบ แจ้งช่วงที่ขาดและหยุดอย่างปลอดภัย; ไม่ fallback เงียบ ๆ จน Preview ≠ Render
- รักษาลำดับ sticker, scrim, LUT, transition, caption และ watermark เดิม และทำ visual parity ที่ boundary frame

### Cache

- Cache key ใช้ source fingerprint + source window + rotation + FPS/resolution + engine/model/quality/temporal mode/worker version ไม่ผูกกับข้อความที่พิมพ์
- แก้ข้อความแต่เวลาเท่าเดิม: reuse; ย้ายเวลา: เตรียมเฉพาะช่วงใหม่; เปลี่ยนจาก `behind` เป็น `front`: ไม่ต้องประมวลผลเพิ่ม และไม่ลบ artifact เก่าทันที
- ใช้ project revision guard กับ task ที่จบทีหลัง เพื่อไม่ผูกผลลัพธ์ของแผนเก่ากับ Timeline ใหม่; cleaner ลบเฉพาะ namespace Cutout ตามกฎเดิม

## 8. ขั้นพัฒนาแบบแยกส่งได้

1. **ข้อมูลและ migration:** เพิ่ม resolver JS/Python, optional fields, Save/Reload, Undo/Redo; fixture ของโปรเจกต์เก่าต้องให้ผล bit-for-bit เดิม
2. **UI:** Inspector และป้าย Timeline; ยังไม่เปิด scoped processing จนมี gate ครบ
3. **Pure planner:** Timeline intervals → source windows → frame count; regression สำหรับ overlap, split, speed, transition, missing trim, hidden/front text และ source reuse
4. **Worker/cache binding:** สร้างและอ่านหลาย scoped artifacts ต่อ source/clip, cancellation, resume, stale revision, legacy compatibility
5. **Preview/Render พร้อมกัน:** ต่อ scoped windows เข้าทั้งสองฝั่งในรอบเดียว รวม ASS classification ตาม identity; ห้ามปล่อยให้ Preview ใช้ใหม่แต่ Render ยังใช้เก่า
6. **เปิดใช้งานผ่าน scope mode:** preflight จริง, error ที่เข้าใจง่าย, opt-in สำหรับโปรเจกต์เดิม; วัดเวลา/ขนาด cache ก่อน-หลัง

## 9. เกณฑ์รับงานและหลักฐาน

- โปรเจกต์เก่าอย่างน้อย 3 แบบ (Hook พร้อม Cutout, Text Overlay หน้า, PNG artifact เดิม) Save/Reload/Render เทียบก่อนหลังโดยไม่เปลี่ยนภาพหรือฟอนต์
- Fixture 60 วินาทีที่มี Behind 0–5 และ 20–23 วินาที ต้องคิดประมาณ 240 เฟรม + padding ที่รายงานชัด; ไม่ประมวลผลช่องว่าง 5–20 และ 23–60
- ข้อความหน้าและหลังที่ซ้อนกันบนเฟรมเดียวต้องเรียงภาพถูก; เฟรมก่อนเข้า/เฟรมแรก/เฟรมสุดท้าย/เฟรมหลังออกของทุก window ต้องตรง Preview กับ FFmpeg Render
- ทดสอบ transition, speed 0.5×/1×/2×, source ซ้ำ, trim แก้หลังเตรียม, cancel/retry, artifact หาย, cache เก่า, Save/Reload และเปลี่ยน depth ระหว่างงานกำลังรัน
- ตรวจขอบเหลืองเป็นงานคุณภาพ Mask แยก: เก็บภาพ Render จริงก่อน/หลัง เฟรมใกล้ข้อความ และตัดสินจากภาพ ไม่สรุปว่าการลดช่วงทำให้ขอบดีขึ้นเอง
- ชุดทดสอบ deterministic/offline ใช้ `.tmp/` เท่านั้น; รัน frontend tests/build, backend targeted/full ตาม testing standard, `test_preview_render_parity.py`, FFmpeg frame comparison และ `git diff --check`; cleanup 100%

## 10. ความเสี่ยงและขอบเขต

- ความเสี่ยงหลักอยู่ที่หลาย artifact ในคลิปเดียวและการ split ASS ตาม identity; ต้องทำ prototype กับ fixture ก่อนเปลี่ยน Render ของโปรเจกต์จริง
- ขอบคลิป/transition อาจทำให้ source time ของสองคลิปถูกใช้พร้อมกัน จึงต้องวางแผนต่อคลิป ไม่ดูเพียงข้อความรวมทั้ง Timeline
- `cutout.webm` ใช้ VP9 alpha; ขอบเหลืองอาจมาจาก mask/สีขอบหรือการเข้ารหัส ต้องวินิจฉัยด้วยเฟรมจริง ไม่เปลี่ยน model/สี/font ระหว่างงาน scope นี้
- งานนี้ไม่เพิ่ม AI ตัดสินใจเองว่าข้อความควรอยู่หน้า/หลัง ผู้ใช้เลือกเอง; ไม่เปลี่ยน Subtitle cues ให้เป็น Behind ในรอบแรก
- ยังไม่เริ่มแก้ production code ตามคำขอให้วางแผนก่อน
