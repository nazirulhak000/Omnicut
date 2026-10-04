# รักษาจุดตัดและรอยต่อที่เลือกไว้
ดำเนินการโดย: Codex (GPT-6)
วันที่: 2026-10-04

## ปัญหาและผลที่แก้
Assembly เดิมตีความ transition array ที่เป็น cut ทั้งหมด (รวม None/[]) ว่าไม่มีแผน จึงเติม effect ตามสไตล์ทับแผนใน editor และแผน automatic ที่ตัดสินใจใช้ cut แล้วได้ นอกจากนี้ explicit transition array ที่มี effect ไม่ได้ sync กลับ clip metadata ทำให้ preview ต่างจาก render ได้

ใช้ `_resolve_transition_plan` เป็นจุดรวมแผนก่อน render/manifest:
- Explicit array มีผลก่อน clip metadata รวม [] ซึ่งหมายถึง cut ทุก boundary; array สั้นเติม boundary ที่เหลือด้วย cut และตัดส่วนเกินตามจำนวนคลิป
- เมื่อไม่มี array บน existing/editor timeline อ่านรอยต่อจากคลิป รวม duration/easing; ไม่เลือก style effect ใหม่
- Automatic effect picker ทำงานเฉพาะ newly generated plan ที่ array=None และไม่มี editor clip_list; รักษา style budget และ source handle guards เดิม
- Shot matcher ใช้ None เป็น unspecified ไม่ใช้ truthiness จึงไม่สร้าง effects ทับ explicit []
- Normalize แผนด้วย renderer contract แล้ว sync clip metadata, ctx.transitions และ manifest ให้ตรงกัน; cut ล้าง duration/easing ที่ไม่ใช้งาน
- ไม่เปลี่ยน trim/speed/duration ของ editor timeline ไม่เพิ่ม overlap compensation ซ้ำ
- เปลี่ยน source-text test เก่าที่ตรวจ dead reference block เป็น behavioral parity ของ resolver + production JS

## การตรวจรับ
- Baseline ใหม่ **8 failed / 1 passed** ก่อนแก้: authored all-cut, generated all-cut, legacy clip metadata, explicit mixed plan และ explicit empty plan
- Focused unit/integration **125 passed**, 1.19s
- Scoped preview/render parity **8 passed**, 0.85s
- New real assembly/render/replay **1 passed**, 2.89s: source synthetic, stage run จริง, manifest/export registry writes mock, output เฉพาะ TemporaryDirectory
- Real regression ของ complete-thought holds, short source windows 30/60 FPS และ camera transition handles **7 passed**, 19.08s
- รวม **141 passed**, ไม่มี pytest skips/warnings; compileall ผ่าน; API import **225 routes**; scoped diff check ผ่าน (Git แจ้ง LF/CRLF ตาม working tree)
- Clip ทดสอบ 4s ได้ **120 frames**; hard cuts ที่ **30/60/90**; production preview แสดงทีละคลิปทุกเฟรม และ source frame ตรง render ภายใน **1 frame**
- โหลด clip/transition plan ที่ save แล้วเรนเดอร์รอบสอง: cut positions และ trim/duration ไม่เปลี่ยน
- Automatic unspecified plan ยังได้ effect ตาม budget; existing 0.6s slide/ease-out คงค่าเดิม ไม่ถูกลดเป็น style default 0.28s
- ไม่มี frontend code changes; ไม่รัน full pytest/npm/build ตามคำสั่งผู้ใช้
- ล้าง temporary media ของรอบนี้ทั้งหมด ไม่มี real asset/project/export/registry writes

## Jev / ขอบเขต
- ก่อนเริ่ม score **0.88**, ก่อน FFmpeg **0.73**, ก่อน/หลัง **0.68**, ตรวจเอกสาร **0.55**; confidence ทุกครั้ง=null
- ใช้ focused regression/measurement gate ตามที่ผู้ใช้อนุญาตแล้ว ไม่ใช้คะแนนเป็น confidence หรือหลักฐานตรวจภาพ
- ยืนยันการรักษาแผนและ timing ในกรณีทดสอบ ไม่รับรอง semantic matching หรือความชอบด้านสุนทรียะของคลิปจริง
- Backend ก่อน reload มี **0 active tasks**; โหลดโค้ดใหม่และตรวจ **HTTP 200** หลัง restart
