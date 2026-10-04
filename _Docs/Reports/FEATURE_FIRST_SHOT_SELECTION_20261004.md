# เลือกภาพตรงฟีเจอร์ก่อนความหลากหลาย
ดำเนินการโดย: Codex (GPT-6)
วันที่: 2026-10-04

## สาเหตุและการแก้
Catalog scorer เดิมรวม relevance และ anti-repeat ไว้ใน score เดียว จึงเกิดกรณีบทพูดฟีเจอร์เดิมต่อเนื่อง แต่คะแนนความหลากหลายดันภาพคนละฟีเจอร์ขึ้นมาแทนภาพที่ตรงบท

- เก็บ evidence จาก non-generic scene keywords ที่ตรง cue และคำใน domain patterns ที่ตรงทั้ง cue/scene description
- เมื่อมี evidence เลือก candidate ภายในกลุ่มนี้ก่อน แล้วใช้ scoring/angle diversity/anti-repeat เดิมเลือกมุม ไม่ปล่อยให้ novelty ผลักไปฉากไม่มี evidence
- ถ้าไม่มี evidence ใช้ narrative/hero/spin/variety fallback เดิม ไม่อ้างว่ารู้ภาพตรงบท
- เก็บ `selection_evidence` เป็นข้อความ metadata สำหรับสืบย้อน ไม่ใช่ confidence หรือผลตรวจพิกเซล
- เมื่อ cache มีทั้ง catalog และ matches ที่อ้าง scene IDs ให้ประเมินใหม่ในเครื่องตาม cue ปัจจุบัน ไม่ตรึงผล diversity-first เก่าหรือ grouping จาก duration เก่าไว้ใน text-keyed cache
- Direct Vision matches ที่ไม่มี scene IDs ยัง reuse cache เดิม ไม่มี network call/cache write ในเส้นทาง rematch ที่ตรวจรับ

## ผลก่อนและหลัง
Baseline ใหม่ **3 failed / 1 passed**:
- พูด USB-C สี่ช่วง: เดิมเลือก `[USB-C, screen, logo, box]`; ใหม่เลือก USB-C **4/4**
- มี USB-C สองมุม: เดิมเลือกสี่ฉากปนคนละเรื่อง; ใหม่สลับ `[0,1,0,1]` เฉพาะสองมุมที่เกี่ยวข้อง
- ไม่มี scene keywords แต่ description ตรง feature: เดิมหลุดไปฉากอื่น; ใหม่รักษาฉากที่เกี่ยวข้อง
- ไม่มี feature evidence: ยังใช้ variety fallback เดิม

## ตรวจรับ
- Focused catalog/cache/shot/source-window/style/transition units **146 เคสไม่ซ้ำผ่าน**: ชุดสุดท้าย111 passed (1.00s), smart matcher+Gemini matcher35 passed ในชุดก่อนหน้า (ชุด47รวม tests ที่ซ้ำ)
- Scoped preview/render parity **5 passed**, 0.55s
- Real catalog → shot planner → FFmpeg → production JS preview **1 passed**, 2.58s: **8s/240frames** ไม่มี raw frames จาก screen/box; preview/render source timing ต่างไม่เกิน **1 frame**
- Real shortage policy 30/60 FPS และ long hold **3 passed**, 6.42s; กติกาค้างภาพพร้อมแจ้งเมื่อ footage ไม่พอไม่เปลี่ยน
- รวม gate รอบนี้ **155 passed**, ไม่มี pytest skips/warnings จากชุด offline ที่ผ่าน; compileall/API225/scoped diff check ผ่าน (Git มี LF/CRLF notice)
- มีการลอง collect `tests/test_gemini_vision_match.py` แล้วพบ `ModuleNotFoundError: dotenv`; ตรวจพบว่าเป็น legacy manual diagnostic ที่สร้าง Gemini client ตอน import จึงไม่ใช้เป็น offline gate ไม่ติดตั้ง dependency หรือเรียก API ของไฟล์นั้น ข้อผิดพลาด collection นี้แยกจากชุด155ที่ผ่าน
- Media ทุกชิ้นอยู่ใน TemporaryDirectory และ regression basetemp ชั่วคราวที่ล้างแล้ว ไม่แตะข้อมูลจริง/registry หรือใช้ Vision quota
- ไม่รัน full pytest/npm/build ตามคำสั่งผู้ใช้ ไม่มี frontend code changes

## ขอบเขตและข้อจำกัด
- เป็นการแก้การจัดอันดับจาก catalog metadata ไม่ใช่การตรวจความหมายของพิกเซลจริง หาก catalog อธิบายภาพผิด กติกานี้ยังเลือกผิดได้
- ความหลากหลายถูกจำกัดภายในภาพที่มีหลักฐานตรงบท ไม่ได้เพิ่มวัตถุดิบหรือค้นหามุมใหม่
- ไม่รับรองว่า raw frames จะไม่ซ้ำทั้งหมดเมื่อมีเพียงมุมเดียว การจัดสรรช่วงที่ reuse scene ยาวเป็นงานแยก; source-window/freeze policy เดิมยังใช้
- Existing saved timeline ไม่ถูกเปลี่ยนย้อนหลัง ต้องสร้าง shot plan ใหม่เพื่อใช้ selection policy นี้; cached catalog rematch ไม่ต้อง index/upload ใหม่
- Jev scores: ก่อนเริ่ม0.54/ก่อนrender0.51/ก่อนหลัง0.62/doc0.59, confidence=null ทั้งหมด ใช้ measurement gate ตามอนุญาตเดิม ไม่ใช้ score แทน confidence
- Backend reload หลังตรวจ0 active tasks และตรวจ HTTP200 หลัง reload
