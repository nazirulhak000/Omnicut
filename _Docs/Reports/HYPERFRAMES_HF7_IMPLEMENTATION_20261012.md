# HyperFrames HF7 implementation / integration

ดำเนินการโดย: Codex (GPT-6) + delegated agents (Codex GPT-6) · 2026-10-12

สถานะ: ปิด implementation/integration HF7-A–F พร้อม tests/review/cleanup · ยังไม่เปิด production หรือยืนยัน live AI/TikTok

## ผลลัพธ์และโฟลว์จริง

Creative → HyperFrames รองรับ Product/Angle, Standalone และ Gadget project จริงของช่องที่เลือก ใช้ external AI session หรือ explicit Gemini action ในแอปผ่าน durable authoring เดิม ทั้งสองเส้นทางต้อง submit immutable revision → ผู้ใช้รับ revision → guarded renderer → QC → ผู้ใช้ยืนยันส่งออก → Registry/Gallery → Schedule/PostingJob เดิม → ผู้ใช้กด extension → receipt → actual publication observation

Gadget finalize สร้าง render candidate ใน repository จริง ไม่อนุมัติตัวเอง หน้า Gallery/queue/prepare บังคับ approved master ตัวเดียวกับ export และตรวจ SHA ของ bytes จริง หาก slot ผูกผ่าน API ต้องยังเป็นคู่ campaign/slot/project เดิมและเนื้อหาเดิมที่ผ่าน readiness ข้อมูล source และ caption/title ของ export ถูกแช่แข็ง ไม่เปลี่ยนตาม brief รุ่นใหม่

Approved-master overlays ต้อง inspect และยืนยัน digest ก่อนสร้างงาน สำรอง master immutable และสร้างภาพ PNG/JPG/WebP ไม่เกิน 24 ชั้นตาม safe region/เวลาเดิม Worker ตรวจ closed composition/master hash และ required audio; ไม่แก้ภาพ เสียง ความยาว ฟอนต์หรือข้อความต้นฉบับ Output ใหม่ยังผ่าน revision acceptance/QC/Gadget Review ก่อนเป็น master

## จุดที่ตรวจและแก้ระหว่าง integration

- Provider instance ใช้ cache ตาม canonical root เพื่อ cancel task จริงได้ แม้ Workflow factory สร้าง object ใหม่แต่ละ request มี owner/channel/fence/source CAS และ startup interruption ที่ไม่ retry paid request เอง
- API route policy เพิ่ม 5 routes; recovery ของ provider แยกจาก renderer เพื่อไม่ลบผล recovery ที่สำเร็จเมื่อ provider error
- Gallery ใช้ canonical HF project และ frozen metadata แทนการเดา ProductStore parent จากชื่อไฟล์ Standalone/Gadget ไม่สร้าง parent ปลอม
- Queue/prepare ตรวจ source readiness ก่อน transaction/job และ pin export/source/artifact/slot fingerprints ไม่รับ parent หรือ project identity ปลอมจาก caller
- Existing durable publication effect phase บันทึก URL/เวลา/observation ลง exact Gadget artifact เฉพาะ current approved master เท่านั้นที่เปลี่ยน project เป็น published หากมี master ใหม่แล้วจะคงผลเป็นประวัติของคลิปเก่า Slot ที่ถูกย้าย/แก้เนื้อหาไม่รับผลโพสต์ของ snapshot เดิม
- หลัง published อนุมัติ candidate รุ่นใหม่ได้ การอนุมัติ master เดิมซ้ำเป็น no-write read; writer ของ timeline/quality/artifact ครอบ read-modify-write ด้วย shared RLock เพื่อรักษาประวัติโพสต์เมื่อทำงานพร้อมกัน
- UI เลือก source, เริ่ม/ยกเลิก AI, missing key/SDK, inspect/approval/layers, เปิด Gadget Review และ Gallery จริง มี unsaved/channel fencing และ desktop/mobile verification โดยคง font contract เดิม
- Backup relocation test พบ submitted metadata ที่เก็บ absolute path ของต้นทางเดิม แก้ CreativeJobStore get/list/submit ให้ใช้ canonical relative revision identity และ rehydrate เฉพาะ workspace ปัจจุบัน ตรวจ owner/project/base revision/entrypoint/aliases รองรับ snapshot_path รูปแบบเก่าโดยไม่ rewrite archived hashes หรืออ่านจากต้นทาง New persisted submissions ไม่เก็บ absolute pointers; legacy pointers เหลือเป็นข้อมูลประกอบที่ตรวจความสอดคล้องก่อนใช้ canonical identity เท่านั้น

## หลักฐานการทดสอบ

| ชุด | ผล | ขอบเขตหลักฐาน |
|---|---|---|
| Backend full ก่อน publication supplement | 3903 passed / 29 skipped / 62 warnings; 1402.97s | `.tmp/hf7-backend-full.log`; ไม่รวม tests ที่เพิ่มภายหลัง |
| Browser full | 185 passed; 665.83s | `.tmp/hf7-browser-full.log`; offline HTTP fixtures |
| Final HF7/shared regression | 237 passed / 1 skipped; 129.73s | `.tmp/hf7-final-regression.log`; provider/API/source/readiness/publication/recovery/effects/observation/route/startup |
| Final UI targeted | 10 passed; 19.72s | `.tmp/hf7-ui-confirm.log`; 7 HF7 + 3 workflow, desktop/mobile viewed |
| Frontend / extension / build | 1021 passed / 64 passed / build passed | `.tmp/hf7-node-confirm.log`, `.tmp/hf7-extension-final.log`, `.tmp/hf7-build-confirm.log` |
| Provider service/authoring/API | 65 passed | Fake transport, no paid Gemini request |
| Publication-domain supplement | 94 passed; 107.19s | Actual repositories/approve/prepare/receipts/effects; added after initial full collection |
| Publication/concurrency final | 97 passed; 95.70s | รวม 3 concurrent timeline/quality/artifact writers ที่รักษาประวัติ publication |
| Overlay offline/API | 47 passed / 2 skipped | Windows symlink permission skips; actual SDK audio/pixel test additionally runs opt-in |
| Actual guarded SDK/render workflow | 74 passed; 74.56s | `.tmp/hf7-render-confirm.log`; original pixels, timed raster layer, audio frequency/RMS, master SHA unchanged |
| Actual Gadget summary UI | 7 passed; 15.73s | `.tmp/hf7-ui-real-summary.log`; fixture ใช้ product_identity ตาม API จริงและแสดง brand/model/variant |
| Backup full with HF7 relocation | 31 passed; 17.63s | Source unavailable, target get/list/actual CLI router, legacy pointer formats, wrong-scope/path rejection, immutable master/checkpoint preserved |
| Final authoring consumers | 52 passed; 15.08s | `.tmp/hf7-authoring-consumers.log`; Workflow/CLI/recovery/finalize หลัง canonical rehydration fix |
| Canonical backup/AI/source integration | 135 passed / 1 skipped; 51.31s | รวม backup/authoring/provider/AI API/overlay/source; sealed hash guard supplement 2 passed |
| Final backup + actual overlay after cleanup fixtures | 61 passed; 37.66s | Backup31 + overlay30 รวม actual SDK; owned temporary media/project/archive cleanup 100% |

Compileall scripts, Node worker/guard syntax และ git diff --check ผ่าน ข้ามเฉพาะ tests ตาม platform/opt-in; full backend warnings บันทึกตามจริง ไม่สรุปว่าไม่มี warning

## Jev และข้อจำกัด

ใช้ `tools/jev_advisor.py` เดิม Provider quality 1.96/3 confidence 0.84, safety 2.93/3 confidence 0.93; source quality 3.05/4 confidence 0.73; overlay quality 3.22/4 confidence 0.77; publication quality 3.36/4 confidence 0.56 และ improvement 3.97/4 confidence 0.98 ผล confidence ต่ำเก็บตามจริงและใช้ authorization เดิมของผู้ใช้ให้ tests/review ตัดสินต่อในขอบเขตนี้ Jev ตรวจข้อความ ไม่ใช่หลักฐานว่าโค้ด/media ผ่าน

Root final text review ก่อนปิด backup defect: quality 3.28/4 confidence 0.57, improvement 3.82/4 confidence 0.83 (`.tmp/hf7-final-jev.log`) ไม่ใช้แทนผล restore/render/repository tests

หลังแก้ canonical restore: quality 3.48/4 confidence 0.58, improvement 3.96/4 confidence 0.98 (`.tmp/hf7-final-jev-closed.log`) ดำเนินต่อด้วย tests/review ตาม authorization เดิมของผู้ใช้

ไม่มี paid live AI request, ไม่ restart production API, ไม่โพสต์จริง ไม่แก้ approved master/data ของจริง และไม่กลับไปทำ TikTok/queue/Temp งานเก่าที่ผู้ใช้ยกเลิกไว้ Runtime ใหม่ต้องโหลดผ่านการเปิดแอปใหม่ตามเวลาที่เจ้าของงานสะดวก

Gemini configured แปลว่ามี configuration ไม่ใช่ live key/model verified หน้า UI เลือก Gadget project; optional campaign/slot binding มีที่ API และไม่มี slot selector ในหน้า UI Overlay เป็นภาพนิ่งตามเวลา ไม่ใช่ NLE แบบอิสระหรือ AI ที่แก้ approved master ได้เอง การโพสต์ยังเริ่มด้วย extension ตามคำยืนยันของผู้ใช้

Agent provider แจ้ง out-of-credits ตอน browser handoff แต่บันทึกไฟล์แล้ว parent รับช่วงจนผ่าน Cannot inspect account balance; checkpoints บันทึกใน TODO ก่อนปิดรอบ ขยะภาพ/video ของเทสใช้ temporary storage และลบหลังตรวจ คงเฉพาะ text evidence logs

ดู [คู่มือ](../HYPERFRAMES_WORKFLOW_GUIDE.md) และ [แผน/โฟลว์ HF7](../Plans/PLAN_HYPERFRAMES_HF7_20261012.md)
