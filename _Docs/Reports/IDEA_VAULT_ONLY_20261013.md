# Producer เหลือเฉพาะคลังไอเดีย — 2026-10-13

ดำเนินการโดย: Codex (GPT-6)

ผู้ใช้ให้เก็บเฉพาะ Idea & Ref Vault ถอด greeting/quota/targets/mission/action queue/retrospective/quick-preview และ state/modal ที่เกี่ยวข้องออกจาก ProducerHub ลด component จาก2525เหลือ1195บรรทัด เก็บ form/list/รูป/ลิงก์/edit/pin/copy/AI action ที่เป็นส่วนของVaultตามเดิม ไม่สร้างหน้าใหม่

เมนู desktop/mobile/Topbar ใช้ชื่อคลังไอเดียและLightbulb ภายในยังใช้producerroute/producer_manual_draftและNotes APIเดิม เพื่อให้ไอเดีย/เรฟที่เก็บไว้กลับมาได้ oldretainedtargetsไม่เปิดmodalอีก ส่วนนี้fetchเฉพาะproducts+notesแทน6แหล่ง ส่วนglobalappอื่นยังทำงานตามเดิม

ไม่ลบnotes/ref files/สินค้า/คลิป/targetsstorageหรือข้อมูลbackend ไม่runpaidAI/render/post/restart/commit งานAntigravityUnified/Essager/TikToksharpไม่ถูกทับ

## Verification

- ExistingProducerdraft/upload/pendingSave/noteedit/proposal/channel+navigation browser11passed20.94s
- NewrealAppVault capture/link+in-memoryPNG upload/save/reload/oldnotes/channelisolation desktop-mobile2passed6.51s รวมunique13cases (offlineHTTPfixtures)
- Frontend1021passed; build945msผ่าน มีsharedtreechunk-sizewarningไม่ใช่error
- Scopedgitdiffcheck0; desktop/mobile inspectedหนึ่งรอบ ภาพ2ไฟล์cleanupแล้วไม่มีวิดีโอ/รูปทดสอบในproduction
- Detector4inheritedVault warnings (gray-on-color/bounce-easing/dynamic clipboardimg regex) ไม่เปลี่ยนstylingเดิมที่ผู้ใช้ขอเก็บ ตรวจภาพแล้ว UIอ่านได้/ไม่overflow
- InitialnewfixtureผิดPOSTendpoint แก้เป็น /producer/notes/addพร้อมsuccess/revisionแล้วผ่าน
- Jevจากสรุปquality3.72/4confidence0.78 บันทึกตามจริงและใช้explicituserinstruction/tests-reviewoverrideเดิม ไม่ใช่codeproof
