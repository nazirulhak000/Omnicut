# Professional Editing Style System

แผนยกระดับคุณภาพคลิปแบบ one-click สำหรับ OmniCut Pro Studio โดยแยก “ความสามารถของ Editing Engine” ออกจาก “รสนิยมของแต่ละ Style Preset”

สถานะ: Phase 1 เสร็จ — Style Contract + Golden Master; Phase 2A และ 2B เสร็จ — pacing core ถูกเชื่อมกับ subtitle pipeline และ manifest แบบไม่เปลี่ยน FFmpeg cut behavior
วันที่เริ่ม: 2026-09-09

## เป้าหมาย

เปลี่ยนระบบจากการวาง Hook, Caption, Sticker, Effect และ Transition แบบองค์ประกอบแยกกัน ให้เป็นระบบที่เข้าใจจังหวะและภาษาการตัดต่อของทั้งคลิป โดยยังรักษา project เดิมและ Preview = Render parity

เป้าหมายคุณภาพเริ่มต้นคือคลิปรีวิวสินค้าแนวตั้งที่ดูจบในตัวและไม่ต้องแต่งต่อหนัก ไม่ใช่การรับประกันว่าเนื้อหาทุกชิ้นจะ viral

## สิ่งที่มีอยู่แล้วกับสิ่งที่ยังขาด

ระบบปัจจุบันมี primitive หลายชิ้นอยู่แล้ว:

- Hook templates ใน `frontend/src/lib/hookStyles.js` และ `scripts/hook_styles.py`
- Hook motion catalog ใน `scripts/hook_motion_presets.py`
- Shared overlay model ใน `frontend/src/lib/overlayModel.js` และ `scripts/overlay_model.py`
- Text template gallery ใน `frontend/src/components/editor/AssetPanel.jsx`
- Clip transition normalization และ effect rendering ใน `scripts/video_editor.py`
- Timeline document และ overlay track model ใน `frontend/src/lib/timelineSchema.js`
- Audio stem contract: Voice `1.0`, SFX `0.28`, BGM `0.12`

สิ่งที่ยังขาดคือสัญญาระดับ “ทั้งคลิป” ที่บอกว่า primitive เหล่านี้ควรทำงานร่วมกันอย่างไร เช่น:

- เมื่อไหร่ควรตัดภาพและเมื่อไหร่ควรคงช็อตไว้
- ช่วงใดควรใช้ Hook, Keyword Pop, Product Callout หรือ CTA
- ในหนึ่งช่วงเวลามี Motion เด่นได้กี่ชิ้น
- Transition แบบใดเป็นค่าเริ่มต้น และแบบใดต้องมีเหตุผลจากการเคลื่อนภาพ/เนื้อหา
- สีและ Typography ต้องรักษาลำดับความสำคัญอย่างไร
- SFX และ BGM ควรตอบสนองต่อจังหวะตัดอย่างไร

## สถาปัตยกรรมเป้าหมาย

```text
Raw footage + transcript + product context
                 │
                 ▼
       Editorial analysis / beat map
                 │
                 ▼
      Style Preset + deterministic rules
                 │
                 ▼
       Timeline Document per project
                 │
          ┌──────┴──────┐
          ▼             ▼
     Canvas Preview   ASS/FFmpeg Render
```

Style Preset เป็นข้อมูลที่เลือกต่อโปรเจกต์ ไม่ใช่ค่าที่ฝังบังคับกับทุกโปรเจกต์ ส่วน Prompt มีหน้าที่ช่วยจัดประเภทเนื้อหา เช่น Hook, Problem, Proof และ CTA; การคำนวณเวลา, clamp, z-order, audio mix และการ Render ต้องเป็น deterministic rule ของระบบ

## Golden Master: `clean_tech_review`

สไตล์แรกสำหรับคลิปรีวิวสินค้า/อุปกรณ์ไอที:

- บุคลิก: สะอาด คม ทันสมัย มีพลังแบบพอดี
- โครงเรื่อง: Hook → Problem → Demo/Proof → Verdict → CTA
- สีหลัก: พื้นเข้ม/ภาพจริง + ขาวสำหรับข้อมูลหลัก + Accent สีเดียวสำหรับคำสำคัญ
- Typography: หัวข้อเด่นหนึ่งระดับ, รายละเอียดหนึ่งระดับ, CTA หนึ่งระดับ
- Motion: ใช้ punch-in, slide, scale และ keyword emphasis แบบสั้นและมีเหตุผล
- Transition: Hard cut เป็นค่าเริ่มต้น; ใช้ movement transition เฉพาะจุดที่ภาพหรือเนื้อหา motivate
- Audio: Voice อยู่หน้าสุด, BGM duck ตาม Voice, SFX ใช้เฉพาะ event สำคัญ

## Style Contract v1

ค่าด้านล่างเป็น acceptance target สำหรับ preset แรก ไม่ใช่ค่าตายตัวของทุก preset

### Editorial structure

| ช่วง | เป้าหมาย | Acceptance target |
|---|---|---|
| Hook | ดึงความสนใจ | เริ่มภายใน 0–2 วินาที, ข้อความ 3–6 คำ, มี visual focus เดียว |
| Problem | ระบุ pain point | มีข้อความ/ภาพช่วยยืนยัน ไม่ใส่ effect แย่งเสียงพูด |
| Demo/Proof | แสดงหลักฐาน | เปลี่ยนภาพตามใจความหรือ action ที่เห็นจริง |
| Verdict | สรุปความคุ้มค่า | ลดความหนาแน่นของ overlay ให้คนอ่านทัน |
| CTA | ปิดการดู | มีข้อความเดียวที่ชัด อยู่ใน safe zone และไม่ชน subtitle |

### Pacing

- ตัด Dead Air และคำซ้ำก่อนจัด Motion
- Pattern interrupt target ทุกประมาณ 1.5–3 วินาทีตามพลังของช่วงเนื้อหา ไม่ใช่บังคับทุกจุด
- ไม่ตัดประโยคกลางความหมายเพียงเพื่อให้เร็ว
- J-Cut/L-Cut ใช้เชื่อมช่วงที่เสียงช่วยพาผู้ชมไปฉากถัดไป

### Motion budget

- Micro motion: 120–180ms
- Standard entrance/exit: 240–360ms
- Hero Hook motion: 400–600ms
- กล้อง punch-in เริ่มต้นที่ 3–6%
- หนึ่ง beat มี visual emphasis หลักไม่เกินหนึ่งชิ้น และ supporting accent ไม่เกินหนึ่งชิ้น
- Motion ที่ไม่มี semantic หรือ audio trigger ต้องถูกปิดโดย default

### Transition policy

- Hard cut: ค่าเริ่มต้นประมาณ 70–80%
- Movement-based transition: ประมาณ 10–20%
- Stylized zoom/blur/flash/whip: รวมไม่เกิน 5–10%
- Transition ต้องไม่กินความยาวจนทำให้ช็อตสั้นผิดธรรมชาติ
- Transition ที่เลือกต้องมีเหตุผลจาก movement, beat หรือ semantic section change

### Typography and color

- มี hierarchy เดียวกันทั้งคลิป: Hook > Keyword/Proof > Supporting detail > CTA
- Accent color ไม่เกิน 1 สีหลักและ 1 สีสถานะ
- ไม่ให้ Hook, Caption, Sticker และ Effect แข่งขันกันเป็นจุดเด่นพร้อมกัน
- ใช้ safe-zone เดิมของโปรเจกต์ โดยเฉพาะขอบล่าง 420px และพื้นที่ด้านขวาที่แพลตฟอร์มบดบัง
- ทุกค่าที่ส่งผลต่อภาพต้องมีค่าที่ Canvas และ ASS/FFmpeg เปรียบเทียบกันได้

### Audio

- Voice: `1.0`
- SFX: `0.28`
- BGM: `0.12`
- BGM ต้อง duck เมื่อมี Voice
- SFX ต้องผูกกับ event ที่มองเห็นหรือจังหวะเปลี่ยน ไม่ใช่ใส่ทุก cut
- รักษา J-Cut lead-in ประมาณ 150–250ms เมื่อมีเหตุผลด้าน pacing

## Acceptance rubric

ให้ประเมินคลิปตัวอย่างด้วยคะแนน 0–5 ในแต่ละหัวข้อ โดยใช้ footage, script และ output resolution เดียวกัน:

| หัวข้อ | น้ำหนัก |
|---|---:|
| โครงเรื่องและจังหวะ | 30% |
| ความต่อเนื่องของการตัด | 20% |
| Audio mix และ sound design | 15% |
| Typography / layout / readability | 15% |
| Color consistency | 10% |
| Motion / transition restraint | 10% |

ต้องบันทึกเหตุผลของคะแนนและ timestamp ที่พบปัญหา ห้ามติ๊กผ่านจากการดูโค้ดอย่างเดียว

## แผนเฟสถัดไป

### Phase 2 — Editorial beat map และ pacing

สถานะ: Phase 2A เสร็จ — core ถูกแยกเป็น `scripts/editorial_pacing.py` พร้อม deterministic contract/test; Phase 2B รอ ownership เพื่อ integrate เข้า render/timeline

Phase 2A ทำหน้าที่ normalize word timestamps, classify silence gaps และสร้าง scene/interval beat candidates โดย snap ได้เฉพาะ word-free boundaries

Phase 2B จะเชื่อมผลลัพธ์เข้ากับ Editorial analysis, Timeline Document และ render orchestration โดยต้องมี decision เรื่อง source transcript schema, existing project migration และ Preview = Render parity ก่อนแก้ไฟล์หลัก

### Phase 3 — Style-driven motion composition

ให้ Style Preset เลือก motion family และ intensity ผ่าน shared overlay/timeline model โดยจำกัด motion budget และรักษา preview/render parity

### Phase 4 — Color and audio finishing

เพิ่ม look normalization, accent palette, voice ducking, SFX event policy และ loudness checks โดยไม่ทำให้ต้นฉบับเสียหาย

### Phase 5 — Template gallery and one-click orchestration

ให้ผู้ใช้เลือก Style Preset ต่อโปรเจกต์, preview ก่อน render, duplicate preset ได้ และ re-render ได้โดยไม่เปลี่ยน project เก่าโดยไม่ตั้งใจ

### Phase 6 — Golden-master validation

ใช้คลิปตัวอย่างหลายประเภท ตรวจ output จริงหลายเฟรม (เข้า/ค้าง/ออก), audio artifact, Preview = Render และเก็บคะแนนก่อน/หลัง

## ข้อจำกัดและความเสี่ยง

- คุณภาพสุดท้ายขึ้นกับคุณภาพ footage, script, voice และ B-roll; Style Preset ไม่สามารถรับประกัน viral ได้
- การทำ Motion มากขึ้นโดยไม่มี hierarchy จะลด readability และทำให้คลิปดูรก
- การเปลี่ยน visual contract ต้องแก้ Canvas และ ASS/FFmpeg คู่กัน พร้อม behavioral render test
- Existing project ต้องเก็บ style/version ที่ใช้ไว้ เพื่อไม่ให้ re-render เก่าเปลี่ยนโดยเงียบ ๆ
- งาน implementation เฟสถัดไปต้องตรวจ working-tree ownership ก่อนแตะ `Timeline.jsx`, `SequencePlayer.jsx`, `scripts/video_editor.py`, `scripts/subtitle/*` หรือไฟล์ที่ Claude กำลังแก้
## Current implementation status

Phase 2A, Phase 2B, and Phase 2C are complete. The pacing core now adapts real optional `cues[*].word_timings`, persists `editorial_pacing` through `SubtitleStage` and `PipelineContext`, participates in the subtitle incremental-render fingerprint, and safely drives generated clip boundaries. Manual clip lists and legacy manifests without a pacing plan retain their existing path.

Phase 3A is complete. `style_preset` now travels through the render request, pipeline context, manifest, and incremental-render fingerprint. The `clean_tech_review` policy applies a deterministic transition budget at the auto-generated clip seam: hard cuts remain the default, restrained movement is periodic, and stylized transitions are rarer and duration-capped. Since both Preview and FFmpeg consume the same generated clip list, this slice preserves their shared timing contract. Manual transitions remain user-owned.

Phase 3B is complete. Live clip camera motion now evaluates `zoom`, `pan_x`, and `pan_y` keyframes on the played local timeline in both Canvas Preview and FFmpeg. Auto-generated clips receive subtle push/pan keyframes only on alternating sufficiently long shots; manual clips retain authored keyframes. Clips without camera keyframes keep the existing static fast path, while speed, freeze-tail, rotation, mirror, blur, and audio handling remain unchanged. The contract clamps the evaluated result to zoom `1.0–3.0` and pan `-1.0–1.0`, and was verified with unit, source-parity, and multi-frame FFmpeg tests.
