# แผนปรับปรุง OmniCut TikTok Post Helper

วันที่: 2026-11-11 · รุ่นที่ตรวจ: 0.10.1 · ดำเนินการโดย: Codex (GPT-6)

## ขอบเขตและข้อเสนอหลัก

เป้าหมาย: ให้การอัปโหลด ตั้งเวลา และจัดการแบบร่างเชื่อถือได้ พร้อมบอกสถานะและกู้คืนได้ตรงความจริง
รอบนี้ตรวจและจัดทำแผนเท่านั้น ไม่แก้ implementation ไม่โพสต์จริง ไม่เรียก backend เพื่อเปลี่ยนข้อมูล
ตรวจ panel → orchestrator → worker/CDP → posting protocol → queue effects รวมทั้งการยืนยันผลและ recovery

แนวทางที่เล็กที่สุด: แก้ด่านตรวจและหลักฐานแบบร่างบนโครงเดิมก่อน ยังไม่ต้องเขียน extension ใหม่หรือย้าย runner ทั้งก้อนไป service worker
ของเดิมมี account guard, intent guard, attempt fence, durable pending receipt, reconcile และ run history อยู่แล้ว ต้องรักษาไว้
งานปรับ accessibility/dialog/thumbnail เพิ่งทำในรอบก่อน จึงให้ความสำคัญกับความถูกต้องของ workflow ก่อนการเปลี่ยนหน้าตาอีกครั้ง

## สิ่งที่ตรวจยืนยันแล้ว

- `node --test --test-reporter=tap tiktok_autopost_extension/*.test.cjs`: ผ่าน 211/211, fail 0, skip 0
- จำลองโค้ดจริงแบบออฟไลน์ใน Node/VM เพิ่ม 4 กรณี พบช่องว่างด้านล่าง แม้เทสเดิมผ่าน
- Backend: ตรวจ `scripts/api_tiktok_autopost.py:614–741` และ `scripts/posting_jobs.py` ในเส้นทาง claim/attempt/ack/reconcile/effects จาก source; ไม่ได้รัน backend suite ในรอบเอกสารนี้
- ไม่ได้ทดสอบกับบัญชี TikTok จริง จึงยังไม่รับรอง selectors/หน้าตาปัจจุบันหรือผลโพสต์จริง
- Jev ก่อนเริ่ม: เลือก audit-only, confidence 1.00 จากข้อความสรุปขอบเขต ไม่ได้อ่านไฟล์เอง และไม่ใช่หลักฐานยืนยันโค้ด
- Jev ตรวจเอกสารฉบับเต็มที่ส่งเป็นข้อความ: 3.94/4, confidence 0.96, verdict proceed; เป็นความเห็นต่อแผน ไม่ใช่การตรวจ implementation

## รายการแก้ตามความสำคัญ

### F1 · P0 · การตรวจแบบร่างล้มเหลว แต่ด่านเริ่มรันยังผ่านได้

ตำแหน่ง: `tiktok_autopost_extension/sidepanel.js:3178–3185`, `3801–3812`
เส้นทาง: `syncDraftsWithTikTok()` จับ error แล้วคืน `{ok:false, results:[], problems:[]}` แต่ caller ตรวจเฉพาะ `check.problems` จึงไม่หยุดเมื่อ `ok:false`
จำลอง worker ตอบ `debugger_disconnected`: ได้ `check.ok=false` และ `callerBlocks=false` จริง
ผลกระทบ: อาจเริ่มเตรียม/เปิดแบบร่างโดยที่การตรวจว่าถูกลบ โพสต์เอง หรือเสี่ยงซ้ำ ยังไม่สำเร็จ; guard ขั้นถัดไปยังมี จึงไม่สรุปว่าจะโพสต์ซ้ำแน่นอน
แก้: ต้องผ่าน `check.ok === true`, ผลต้องครบทุก id ที่ขอตรวจ และช่อง/epoch ต้องตรง; error/ผลหาย/unknown ให้หยุดก่อนยืนยันเริ่มรัน
ตรวจรับ: worker error, response ไม่ครบ, ไม่รู้ผล, และผลครบปกติ; สามกรณีแรกต้องไม่เรียก prepare/open draft/submit

### F2 · P0 · หลักฐานบันทึกแบบร่างยังสับสนกับรายการเก่าได้

ตำแหน่ง: `tiktok_autopost_extension/background.js:4787–4823`, `731–743`, `4896–4906`
เส้นทาง: ตัด caption เหลือ 14 ตัว → ค้นในข้อความทั้งหน้า → ยืนยันเมื่ออยู่ Drafts; ยังยอมรับ `rowVisible:null` ใน wait helper ด้วย
จำลองหน้า Drafts ที่มีเพียง `Same product review OLD EP1` แล้วขอยืนยัน `Same product review NEW EP2`: ได้ `sameKey:true`, `rowVisible:true`, `confirmed:true`
ผลกระทบ: บันทึก `draft_saved` ให้คลิปใหม่ได้จากหลักฐานของคลิปเก่า และ reconcile แบบ draft ใช้ helper เดียวกัน
แก้: ตรวจรายแถว ใช้ EP เมื่อปรากฏ/ตัวระบุ platform เมื่ออ่านได้; ถ้า EP ต่างต้องปฏิเสธ; fallback ต้องได้แถวเดียวและมีหลักฐานว่าเกิดจาก attempt นี้ ไม่ยืนยันด้วย URL/count/prefix อย่างเดียว
ตัวระบุที่อ่านจาก DOM ให้ถือเป็นหลักฐานที่ต้องตรวจความคงที่ก่อนใช้งาน ไม่สมมติว่ามี stable platform id อยู่แล้ว
ตรวจรับ: prefix ซ้ำ, EP ต่าง/ไม่แสดง, พบหลายแถว, caption สั้น, ข้อความอยู่ header, รายการเก่า; หลักฐานไม่พอต้อง `confirmation_unknown` และห้ามคลิกซ้ำ

### F3 · P1 · Smart ถูก preflight ปิดทาง fallback ไปแบบร่าง

ตำแหน่ง: `tiktok_autopost_extension/preflight.js:66–76`, `batch_orchestrator.js:321–327`, `README.md` หัวข้อ Modes
โหมด Smart ถูกนับเป็น `needsSchedule` จึง fail ทันทีเมื่อ schedule เหลือ 0 ทั้งที่มี draft ว่าง
จำลอง schedule=0, draft=10, mode=smart: ได้ `ok:false` และ blocker ว่าโควตาตั้งเวลาเต็ม
แก้: ใช้การคำนวณแผน quota ร่วมกับ runner ให้ Smart fallback เฉพาะคลิปอัปโหลดปกติ; publish-from-draft แบบตั้งเวลาต้องใช้ schedule quota ตามเดิม
ตรวจรับ: ตาราง Smart/Schedule-only/Draft-only/Publish-now × โควตา 0/ว่าง/อ่านไม่ได้ และคลิป normal/draft; หน้ายืนยันต้องบอกจำนวน schedule/draft ที่จะทำจริง

### F4 · P1 · Run lock ยังไม่เป็น atomic และผู้เสีย lock ไม่หยุด

ตำแหน่ง: `tiktok_autopost_extension/run_lock.js:17–44`, `sidepanel.js:3087–3092`, `3204–3209`
lock ใช้ read → write → sleep 150ms → read ไม่ใช่ compare-and-swap; heartbeat คืน false แต่ panel ไม่ใช้ผล
จำลอง B อ่าน snapshot ว่างช้า จากนั้น A acquire สำเร็จ แล้ว B เขียนต่อ: ได้ `A:true`, `B:true`, owner สุดท้าย B และ heartbeat ของ A=false
ผลกระทบ: สอง run loop อาจคิดว่าตนถือ lock และแทรกขั้นตอนกัน; backend attempt fence ยังต้องคงอยู่และไม่ได้ถูกพิสูจน์ว่าข้ามได้
แก้: ให้จุดเดียวเป็นผู้จัดสรร run owner แบบ serialized และมี durable run id/fencing generation; ทุก action ที่เปลี่ยนหน้า/งานต้องตรวจ owner; heartbeat หายให้หยุดเริ่มขั้นตอนใหม่
ถ้าจะใช้ Web Locks ต้องทดสอบใน extension origin/หลาย window จริงก่อนเลือก; อย่าอาศัย storage timer เป็น mutex
ตรวจรับ: delayed-read race, สอง panel, manual action ระหว่าง batch, worker restart, timer ช้า; หลังเสีย lock ห้ามเริ่มขั้นตอนใหม่ และห้ามตัดการบันทึกผลของ attempt ที่เกิดแล้ว

### F5 · P1 · สแกน Drafts ไม่ครบอาจถูกสรุปว่าถูกลบแล้ว

ตำแหน่ง: `tiktok_autopost_extension/background.js:5569–5601`, `5671–5676`, `draft_sync.js:25–30`
collector คืนเพียง rows โดยไม่บอกจบจริง/ชน cap/หน้าโหลดไม่ครบ; classifier ใช้ completeness ของ Content เพียงฝั่งเดียว
ผลกระทบ: ถ้า Drafts อ่านไม่ครบ แต่ Content จบและไม่พบ ก็อาจแสดง `deleted` และชวนผู้ใช้รีเซ็ตคิวทั้งที่แบบร่างยังอยู่
แก้: ทั้งสอง scanner คืน `{rows, complete, stoppedBy, expectedCount, account, scannedAt}`; จะสรุป deleted ต้องครบทั้ง Drafts และ Content และบัญชีตรง
ตรวจรับ: draft list โหลดช้า, selector ไม่ตรง, อ่านได้ 0 แถวแต่ยัง loading, ชน cap, scroll container ผิด, empty state จริง; ไม่ครบให้ unknown
สถานะข้อนี้มาจากการ trace source ยังไม่ได้จำลอง DOM scanner ครบเส้นทางในรอบนี้

### F6 · P1 · ค่า channel/mode ยังเปลี่ยนได้ระหว่าง preflight และยืนยัน

ตำแหน่ง: `tiktok_autopost_extension/sidepanel.js:259–271`, `3165–3218`
เลือก clips และตรวจ mode ก่อน await หลายจุด แต่ setBusy หลัง acquire; ตัวเลือกช่องตรวจเพียง busy/activeClip และไม่ได้ตรวจ batchStarting
ผลกระทบ: ในสถานะที่ไม่มี activeClip อาจได้รายการ/การตรวจความพร้อมจากบริบทเก่า แต่ prepare ด้วยบริบทใหม่; backend guards อาจปฏิเสธภายหลัง แต่ควรตัดปัญหาที่ต้นทาง
แก้: freeze run context `{channelId, channelEpoch, mode, selectedIds, scheduleSnapshot}` ตั้งแต่เริ่ม; ปิด controls ที่เปลี่ยนบริบท และตรวจ snapshot อีกครั้งก่อน prepare
ตรวจรับ: เปลี่ยนช่อง/โหมดระหว่าง preflight, draft scan, dialog; ต้องใช้ context ที่ยืนยันเดียวกันหรือยกเลิกรอบ
สถานะข้อนี้เป็นช่องว่างที่พบจาก source ยังไม่ได้จำลอง interaction จริง

### F7 · P1 · Recovery แจ้งว่าพักงานแล้ว แม้คำสั่งพักงานล้มเหลว

ตำแหน่ง: `tiktok_autopost_extension/sidepanel.js:3102–3112`, `run_lock.js:40–44`
`takeOrphan()` ลบ marker ก่อน recovery; error ของ release ถูก catch แล้วตามด้วยสถานะว่า “พักงานที่ค้างแล้ว” เสมอ
แก้: คง recovery marker จนทราบผลจริง; แสดงแยก “พบงานค้าง / พักสำเร็จ / ยังพักไม่สำเร็จ / รอตรวจผล” พร้อมปุ่มตรวจซ้ำที่ไม่คลิกเผยแพร่
ตรวจรับ: backend offline, worker busy, receipt ส่งไม่สำเร็จ, ปิด panel ระหว่าง recovery; ห้ามรายงานว่าพักสำเร็จเมื่อยังไม่สำเร็จ

### F8 · P2 · ทำให้ดูแล DOM automation และปัญหาหน้างานง่ายขึ้น

ตำแหน่ง: `background.js` กลุ่ม attachProductLink/setScheduleDateTime/confirmation, `sidepanel.js:33–83`, `run_history.js`, `auth_key.js`
แก้เป็นช่วงเล็ก: แยก Studio adapter (selectors/DOM readers), protocol client, result verifier และ panel controller โดยรักษา behavior เดิม
เพิ่ม deadline/cancel สำหรับ panel fetch ที่ยังไม่มี timeout; timeout หลัง attempt ต้องเป็น unknown/reconcile ไม่เริ่มคลิกใหม่
เพิ่ม error code/ขั้นตอน/เวลาที่ใช้/run id/job id/เวลาตรวจล่าสุด และปุ่มดำเนินการตามสาเหตุ เช่น เชื่อมใหม่ ตรวจผล ส่ง receipt เดิมซ้ำ
ประเมินโหลดรูปด้วย authenticated fetch + blob URL เพื่อลด API key ใน URL; revoke URL และทดสอบ redaction โดยไม่พิมพ์ key จริง
ยังไม่จำเป็นต้องย้าย runner ทั้งหมด; ประเมิน durable coordinator เมื่อความต้องการปิด panel แล้วทำต่อได้รับการยืนยันเป็นงานแยก

## ลำดับลงมือและเกณฑ์ส่งมอบ

| รอบ | งาน | ผลส่งมอบ / gate |
| --- | --- | --- |
| 1 | F1 + F2 | Regression tests ต้อง fail บนพฤติกรรมเดิม แล้วผ่านหลังแก้; ไม่มี prepare เมื่อ sync ล้มเหลว, ไม่มี false draft_saved |
| 2 | F3 + F5 | quota decision ตรงกันทั้ง preflight/runner; negative scan ต้องมี completeness สองฝั่ง |
| 3 | F4 + F6 + F7 | run owner เดียว, snapshot ไม่เปลี่ยน, recovery ตรงจริง; ทดสอบหลาย panel/restart แบบ isolated |
| 4 | F8 | แยกโมดูลทีละส่วน, diagnostic ชัด, deadline เหมาะกับแต่ละ stage; ไม่มี behavior drift |

ทุก implementation round ต้องมี TODO ของตนเอง, feature branch, regression test ตามสัญญาพฤติกรรม และบันทึกผลจริง
ใช้ fixture/temp storage เท่านั้น; ห้ามใช้คิว JSON หรือไฟล์ exports ของจริงเป็นชุดทดสอบ
คง upload/submit ทีละคลิปต่อบัญชี/แท็บ; งานส่วนนี้มี shared DOM และ quota จึงไม่ควรเพิ่ม 4 posting workers ตามกฎ batch render
หลัง offline gates: ทดสอบ extension ที่โหลดจริงใน Chromium profile แยก โดยใช้หน้า fixture ให้ครบ panel → runtime → worker → stub backend
ทดสอบบัญชี TikTok จริงและการเผยแพร่จริงเป็น gate แยกหลัง implementation พร้อมระบุคลิป/โหมดที่จะใช้; รอบตรวจแผนนี้ไม่ได้ดำเนินการ

## ข้อสรุป

เริ่มจาก F1/F2 ก่อน: ปิดทางผ่านเมื่อการตรวจล้มเหลว และทำให้หลักฐานแบบร่างระบุคลิปได้จริง จากนั้นจึงแก้ Smart/scan completeness และความเป็นเจ้าของรอบ
สถานะอัปเดต 2026-11-12: F1/F2 แก้แล้วใน 0.10.2; ผลตรวจและข้อจำกัดอยู่ใน [รายงาน P0](../Reports/AUTOPOST_P0_IMPLEMENTATION_20261112.md) · ดำเนินการโดย: Codex (GPT-6)
อัปเดตต่อ 2026-11-12: F3–F7 และปุ่มเตรียมคลิปแก้แล้วใน 0.10.3; F8 ทำ timeout/แยกโมดูลบางส่วน ดู [ผลเตรียมคลิปและ hardening](../Reports/AUTOPOST_PREPARE_HARDENING_20261112.md) · ดำเนินการโดย: Codex (GPT-6)
งานแยก DOM automation ทั้งก้อนและตรวจบัญชี TikTok จริงยังคงเป็นงานค้างตามข้อจำกัดในรายงาน
