# AI Producer Hub — Audit & Improvement Plan

วันที่: 2026-09-13  
สั่งโดย: user  
ดำเนินการโดย: Codex (GPT-5)  
สถานะ: แผนรออนุมัติ ยังไม่แก้โค้ด

## 1. เป้าหมายของงาน

ยกระดับ `AI Producer Hub` จากหน้า Dashboard ที่รวมตัวเลขและปุ่มลัด ให้เป็นศูนย์บัญชาการที่ตอบคำถามได้ทันทีว่า:

1. ตอนนี้ควรทำอะไรเป็นอันดับแรก
2. ทำไมรายการนี้ถึงสำคัญ และจะจบงานอย่างไร
3. ข้อมูลที่ใช้ตัดสินใจเชื่อถือได้แค่ไหน
4. ถ้าข้อมูลผิดพลาดหรือซิงก์ไม่สำเร็จ ผู้ใช้กู้สถานการณ์ได้อย่างไร

หลักการ: ทำให้ flow จาก `เห็นงาน → เข้าใจเหตุผล → กดทำงาน → สถานะเปลี่ยนจริง → เรียนรู้จากผลลัพธ์` สั้นและตรวจสอบได้

## 2. ขอบเขตที่ตรวจแล้ว

| ส่วน | ไฟล์หลัก | สิ่งที่พบ |
| :--- | :--- | :--- |
| หน้า Hub | `frontend/src/components/producer/ProducerHub.jsx:81-1814` | รวม Greeting, KPI, Next Mission, Ref Vault, Action Queue, Retrospective, Rules และ Modal ไว้หน้าเดียว |
| Insight engine | `frontend/src/lib/producerInsights.js:104-699` | คำนวณ quota, queue, pacing, greeting, retrospective และ local persistence |
| API | `scripts/api_producer.py:50-312` | Notes, upload media และ endpoint แปลง idea เป็น angle |
| Quick capture | `frontend/src/components/producer/QuickRefPage.jsx` | มี mobile capture, search/filter และ sync ทุก 20 วินาที แต่ logic ซ้ำกับ Hub บางส่วน |
| Route/entry | `frontend/src/App.jsx:447-455`, `frontend/src/api.js:404-422` | Hub เข้าผ่านเมนูหลัก และใช้ API แบบกระจายหลาย endpoint |
| Tests | `frontend/src/lib/producerInsights.test.js` | มี unit test ของ pure functions แต่ยังไม่มี component-flow test ของ Hub โดยตรง |

ข้อมูลจาก browser ที่เปิดใช้งานจริง ณ เวลาตรวจ: weekly `5/35`, daily cut `1/5`, daily post `0/3`, queue `19` รายการ แบ่งเป็น ready-to-post `2`, ready-to-cut `17`, needs-footage `0`, notes `1` รายการ ค่านี้เป็น snapshot ไม่ใช่ baseline ถาวร

## 3. สรุปการประเมิน UX เบื้องต้น

เป็นคะแนนจาก code review + browser snapshot ไม่ใช่ผลทดสอบกับผู้ใช้จริง

| Heuristic | คะแนน / 4 | เหตุผลย่อ |
| :--- | :---: | :--- |
| Visibility of system status | 2 | เห็นตัวเลขและ queue แต่ไม่เห็น last sync, source, หรือสถานะ action หลังออกไปหน้าอื่น |
| Match with real workflow | 2 | ปุ่ม `ส่ง TikTok ตอนนี้เลย` พาไป Gallery; คำว่า AI/retrospective สื่อเกินสิ่งที่ engine ทำจริง |
| User control | 2 | มี filter และ modal แต่ไม่มี dismiss/complete/snooze ของงานใน Hub และ modal ยังไม่รองรับ flow มืออาชีพครบ |
| Consistency | 3 | สี, card, CTA และคำเรียกโดยรวมเป็นระบบเดียวกัน |
| Error prevention | 1 | partial API failure เงียบ, upload หลายไฟล์มีความเสี่ยงจับ preview ผิดไฟล์, save notes เป็น full overwrite |
| Recognition | 3 | มี Next Mission และ preview บทช่วยลดการสลับหน้า |
| Flexibility | 2 | มี round-robin, filter และ Quick Ref แต่ไม่มี search/sort/bulk/keyboard path ใน queue |
| Minimalism | 2 | ลำดับข้อมูลชัดช่วงบน แต่หน้าแนวยาวและมีข้อมูลรองที่แย่งความสนใจจากภารกิจหลัก |
| Error recovery | 1 | ใช้ `alert`/`console.warn`, ไม่รักษา failed state หรือ retry ที่อธิบายได้ |
| Help & documentation | 2 | มี Studio Rules แต่ยังเป็นกฎคงที่ ไม่ใช่ help ตาม context ของงานที่กำลังทำ |
| **รวม** | **20 / 40** | **Acceptable: มีฐานดี แต่ควรแก้ความน่าเชื่อถือและ action loop ก่อนเพิ่มฟีเจอร์ใหม่** |

## 4. Findings ที่ควรจัดลำดับ

### P1 — ต้องทำก่อนเพิ่มฟีเจอร์ใหม่

#### P1.1 Next Mission ยังเลือกจากลำดับ array ไม่ใช่ความเร่งด่วนทางธุรกิจ

- Location: `ProducerHub.jsx:147-181`, `producerInsights.js:359-486`
- ผลกระทบ: ผู้ใช้เห็นว่างานนี้คืออันดับ 1 แต่ระบบไม่ได้อธิบายคะแนนจาก deadline, อายุคลิป, product priority, status หรือ readiness
- แผน: สร้าง `nextAction` ที่มี `priorityScore`, `reason`, `blockingReason`, `deepLink` และ `expectedOutcome`; แสดงเหตุผลสั้นๆ เช่น “rendered แล้ว 6 ชั่วโมง, ยังไม่โพสต์”
- Acceptance: รายการที่แสดงเป็นอันดับ 1 ต้อง trace กลับได้ว่าคะแนนมาจาก field ใด และปุ่มต้องเปิด object เดิม ไม่ใช่แค่เปิดหน้า Gallery/Editor ทั่วไป

#### P1.2 ปุ่ม action หลายจุดไม่ปิดวงจรงาน

- Location: `ProducerHub.jsx:745-805`, `1290-1360`
- ผลกระทบ: `ส่ง TikTok`, `เริ่มตัดต่อ`, `แนบคลิป / ดูแผน` เป็นการนำทาง แต่ Hub ไม่รู้ว่าผู้ใช้ทำสำเร็จหรือยัง จึงยังแสดงงานเดิมและทำให้เกิดความไม่แน่ใจ
- แผน: ส่ง stable identity (`productId`, `angleId`, `exportId`, `projectName`) ไปทุก route, ให้ destination รายงานกลับเมื่อ action สำเร็จ และ refresh เฉพาะ entity ที่เกี่ยวข้อง
- ข้อจำกัด: ห้ามเปลี่ยน status ใน Hub แบบหลอกๆ ต้องอัปเดตหลัง backend/editor ทำงานจริงเท่านั้น

#### P1.3 สถิติมีความเสี่ยงนับซ้ำและข้ามวันจาก timezone

- Location: `producerInsights.js:253-356`
- ผลกระทบ: export กับ angle เดียวกันอาจใช้ key คนละแบบ (`export_id/path/name` กับ `angle_id`) และการเลือกวันใช้ local `Date` ขณะที่ข้อมูล API เป็น ISO อาจทำให้ quota แสดงคลาดเคลื่อน
- แผน: กำหนด canonical clip identity, normalization ของ timestamp และ timezone ของ workspace เป็น contract กลาง; ให้ stats engine คืน `sourceIds` ที่ถูกนับไว้เพื่อ debug
- Acceptance: fixture เดียวกันที่มี export + angle + posted record ต้องนับเป็น 1 คลิป; test boundary ก่อน/หลังเที่ยงคืนและวันอาทิตย์/วันจันทร์

#### P1.4 AI และ Retrospective สื่อความสามารถเกิน implementation จริง

- Location: `api_producer.py:234-312`, `producerInsights.js:585-632`
- ผลกระทบ: endpoint ชื่อ AI แต่ปัจจุบันใช้ keyword heuristic และไม่ได้อ่าน `ref_image/ref_images` หรือดึงเนื้อหาจาก URL; retrospective อ้างเหตุผลเชิง causal จากยอดวิวเพียงอย่างเดียว
- แผน 2 ทางเลือก:
  - ทางปลอดภัย: เปลี่ยน copy เป็น “วิเคราะห์อัตโนมัติ” / “ข้อเสนอจากกฎเบื้องต้น” และใส่ source + confidence
  - ทางเต็ม: เชื่อม AI multimodal จริง, ส่ง ref เป็น input, เก็บ prompt/model/time และบังคับ output schema พร้อม fallback ที่ติดป้ายชัดเจน
- Recommendation: ทำทางปลอดภัยก่อน แล้วค่อยเปิด AI จริงเมื่อ data contract พร้อม

#### P1.5 การซิงก์ Notes เป็น full overwrite มี lost update

- Location: `ProducerHub.jsx:358-412`, `QuickRefPage.jsx`, `api_producer.py:169-229`
- ผลกระทบ: PC และมือถือแก้พร้อมกันแล้วการบันทึกชุดหลังสามารถทับรายการชุดแรกโดยไม่แจ้งผู้ใช้
- แผน: เปลี่ยนเป็น revision/updatedAt + optimistic concurrency หรือใช้ add/update/delete รายการเดียวเป็นหลัก; ถ้าชนกันให้ merge ตาม note id และแสดง conflict ที่ผู้ใช้เลือกได้
- Acceptance: concurrent save 2 clients ห้ามทำ note หายและต้องมีผลลัพธ์ที่ตรวจสอบได้

#### P1.6 Upload หลายไฟล์ยังผูก server URL ด้วยการแทนที่ทุก `data:` preview

- Location: `ProducerHub.jsx:204-239`
- ผลกระทบ: ถ้า FileReader และ upload response จังหวะเหลื่อมกัน รูป preview อาจถูกแทนด้วย URL ของไฟล์อื่น; หาก upload fail จะส่ง base64 เข้า notes ซึ่งทำให้ payload ใหญ่และเปิดจากมือถือไม่ได้
- แผน: ใช้ temporary item id ต่อไฟล์, state `uploading/ready/failed`, map URL ตาม id, ห้าม save note ที่มี upload failed โดยไม่เตือน และกำหนด limit/type/size

### P2 — ควรทำในรอบถัดไป

#### P2.1 Queue ยาวและค้นหารายการเฉพาะเจาะจงยาก

- Location: `ProducerHub.jsx:1142-1360`
- แผน: เพิ่ม search, sort (`urgent`, `oldest`, `product`, `status`), collapsed grouping, count ที่ไม่ซ้ำ, empty state และ pagination/windowing; แก้ product identity ให้ใช้ `productId` เดียว ไม่สร้างปุ่มซ้ำจาก code/name

#### P2.2 เป้าหมายโควตายังเป็นตัวเลขเดี่ยว ไม่ผูก capacity จริง

- Location: `ProducerHub.jsx:1487-1565`, `producerInsights.js:633-672`
- แผน: เพิ่ม working days, planned posts, production capacity, deadline และ “recommended pace”; แยก “เป้าหมายส่วนตัว” กับ “งานค้างจริง” ไม่ให้ progress bar ทำให้เข้าใจว่า queue = ผลิตสำเร็จ

#### P2.3 Idea/Ref Vault ยังเป็น form + card list ไม่ใช่ knowledge workflow

- Location: `ProducerHub.jsx:804-1140`, `QuickRefPage.jsx`
- แผน: เพิ่ม search/filter ใน Hub, note detail/edit, favorite/archive, source preview, duplicate detection, product/angle provenance และปุ่ม “นำไปสร้าง angle” ที่เก็บ link กลับหา note เดิม

#### P2.4 Copy/Share ระบุว่าแนบรูป แต่จริงๆ คัดลอกเป็น text URL

- Location: `producerInsights.js:139-198`, `ProducerHub.jsx:402-413`
- แผน: เปลี่ยนข้อความให้ตรงจริงเป็น “คัดลอกสรุป + ลิงก์ภาพ” หรือทำ clipboard rich payload เมื่อ browser รองรับ พร้อม fallback ที่แจ้งชัด

#### P2.5 Retrospective ยังไม่มี sample size, baseline และ metric ที่ใช้ตัดสิน

- Location: `producerInsights.js:585-632`, `ProducerHub.jsx:1362-1445`
- แผน: แสดงจำนวนคลิป, ช่วงเวลา, median/average, views per post, like/share/comment rate และเปรียบเทียบกับ baseline; ห้ามเขียน “เพราะ” ถ้าไม่มีหลักฐานเชิงเปรียบเทียบ

### P2/P3 — Accessibility, resilience และ polish

- ผูก `label` กับ input ด้วย `htmlFor`/`id` ให้ครบ
- Modal ต้องมี `role="dialog"`, `aria-modal`, `aria-labelledby`, focus management, Esc และคืน focus ไปปุ่มเดิม
- เปลี่ยน thumbnail ที่ `onClick` บน `div` เป็น keyboard-accessible button
- เพิ่ม `aria-live` สำหรับ loading, sync, save, upload และ error
- แยก error state ต่อ section แทนการปล่อย `Promise.allSettled` แล้วเงียบ
- เพิ่ม reduced-motion path ให้ `animate-pulse`, `animate-bounce`, `animate-fadeIn`
- ตรวจ viewport 390x844, 768 และ desktop; จุดหลักต้องไม่เกิด horizontal overflow และ touch target อย่างน้อย 44px
- พิจารณาลด blur/shadow หนักบนหน้า queue ยาวและ lazy-load รูปที่อยู่นอก viewport

## 5. ทิศทาง UX ที่แนะนำ

ใช้โครงสร้าง 4 ชั้น โดยให้ผู้ใช้เห็นงานสำคัญก่อน:

```text
Now       → Next Best Action: งานเดียว เหตุผล ผลลัพธ์ ปุ่มไปยัง object จริง
Produce   → Queue: งานทั้งหมด ค้นหา/กรอง/เรียง และสถานะที่ยืนยันจากระบบ
Capture   → Idea & Ref Vault: เก็บเรฟเร็ว พร้อม provenance และ sync ที่ไม่ทำข้อมูลหาย
Learn     → Performance & Playbook: บทเรียนจากข้อมูลจริง พร้อม sample size และ confidence
```

ข้อเสนอเชิง layout:

1. Header เหลือ `last synced`, health ของ data source และ primary action ที่สัมพันธ์กับ Next Action
2. KPI แสดง 3 ค่าเท่าที่ช่วยตัดสินใจ: `งานต้องโพสต์`, `งานพร้อมตัด`, `pace ถึงเป้า`; quota setting ย้ายเป็น secondary disclosure
3. Next Action เพิ่ม “เหตุผล” และ “สถานะล่าสุด” ไม่ใช้ข้อความเร่งเร้าอย่างเดียว
4. Queue แบ่งเป็น active work กับ blocked work; แต่ละ row มี owner/status/reason/last update/deep link
5. Ref Vault มี capture form กระชับด้านบน และ list ที่ค้นหาได้ด้านล่าง; บน mobile ใช้ capture-first ตาม QuickRef
6. Retrospective อยู่หลังงานที่ต้องทำ และติดป้ายว่า `จากข้อมูลจริง` หรือ `ข้อเสนอจาก heuristic`

## 6. Roadmap แนะนำ

### Phase 0 — Contract & baseline

- ตกลง timezone, definition ของ `cut`, `post`, `ready`, `blocked`, `completed`
- เก็บ baseline จาก fixture และ browser snapshot
- แยก user data ที่ค้างอยู่ใน working tree: ห้ามแตะ `02_Assets/Refs/*`

Gate: มี glossary/fixture และรายการ identity ที่ใช้ trace ครบ

### Phase 1 — Trust layer

- เพิ่ม canonical identity และ stats source tracing
- แก้ duplicate queue/product filter และ standalone export matching
- เพิ่ม API response metadata: `generatedAt`, `source`, `partialFailures`, `lastUpdated`
- เปลี่ยน AI copy ให้ตรงกับความสามารถจริง

Gate: targeted Vitest + pytest ครบ edge cases, no duplicate IDs, timestamp boundary ผ่าน

### Phase 2 — Action loop

- เพิ่ม ranked `nextAction` + reason + deep link
- ส่ง stable IDs ไป Editor/Gallery/Flow
- refresh หลัง destination ทำงานจริง และแสดง success/failure ที่ Hub
- เพิ่ม search/sort/empty/loading/error state ใน queue

Gate: component-flow test ยืนยันปุ่มแต่ละประเภทไป object ถูกตัวและไม่เปลี่ยน status เอง

### Phase 3 — Capture & sync reliability

- upload item state ต่อไฟล์และ validation
- note mutation แบบ single-item + revision/conflict handling
- note provenance, edit/detail, duplicate detection และ copy/share semantics ที่ตรงจริง
- ลดการเก็บ base64 ใน notes ถาวร

Gate: concurrent sync test, upload failure test, mobile-to-PC browser verification

### Phase 4 — Evidence-first Retrospective

- metrics model, baseline, sample size, period, confidence
- แยก heuristic recommendation กับ AI-generated recommendation
- จดบทเรียนพร้อม source clip/metric และย้อนกลับไปหา angle/note ได้

Gate: fixture หลายชุดที่ผลต่างกันต้องให้ insight ต่างกัน ไม่ใช่ข้อความ template เดิมทุกครั้ง

### Phase 5 — Accessibility, responsive และ polish

- dialog/focus/keyboard/aria-live/contrast/reduced-motion
- mobile 390x844 และ tablet layout
- performance pass สำหรับ image/list/blur

Gate: keyboard walkthrough, browser screenshots desktop/mobile, detector และ build

## 7. สิ่งที่ยังไม่ควรทำตอนนี้

- ยังไม่ควรเพิ่ม AI agent ใหญ่หรือ dashboard metric ใหม่ ก่อนแก้ canonical identity และ trust label
- ยังไม่ควรเพิ่มปุ่ม “ทำเสร็จ” ใน Hub ถ้าไม่มี backend operation รองรับ
- ยังไม่ควรย้ายหรือลบไฟล์ใน `01_Raw/` หรือ `02_Assets/`
- ยังไม่ควรรวม ProducerHub กับ QuickRefPage เป็นไฟล์เดียว เพราะจะทำให้ seam ของ desktop/mobile ตื้นลง; ควรดึง shared capture/sync module แทน

## 8. ตัวชี้วัดความสำเร็จ

| Metric | เป้าหมายหลังปรับปรุง |
| :--- | :--- |
| Time to first meaningful action | ไม่เกิน 10 วินาทีหลังหน้าโหลดสำเร็จ |
| Next Action correctness | 100% มี stable ID และ deep link ไป object เดิม |
| Duplicate queue identity | 0 รายการซ้ำใน fixture และ browser snapshot |
| Silent data loss | 0 กรณีจาก concurrent note save test |
| Partial failure visibility | ทุก API failure ต้องมี source + retry หรือ fallback ที่เห็นได้ |
| AI transparency | ผู้ใช้แยกได้ว่าเป็น heuristic, fallback หรือ AI จริง 100% |
| Mobile usability | viewport 390x844 ไม่มี horizontal overflow ใน core flow |
| Core keyboard path | เปิด/ปิด modal, ค้นหา, filter, preview และ primary action ได้ครบ |

## 9. Test/Gate เมื่อเริ่ม implementation

```text
cd frontend
npm test
npm run build

cd ..
python -m compileall -q scripts
python -m pytest tests/test_producer_notes_api.py -q -p no:cacheprovider --tb=short
python -m pytest tests/ -q -p no:cacheprovider --tb=short

node C:\Users\Winon\.agents\skills\impeccable\scripts\detect.mjs --json <changed-targets>
```

นอกจากคำสั่ง ต้องตรวจจริงด้วย browser ที่ desktop และ mobile viewport, keyboard-only flow, modal focus, partial API failure และรายการ queue ที่มีข้อมูลหลักร้อย

## 10. ลำดับที่ผมแนะนำให้เริ่ม

เริ่มจาก Phase 1 → Phase 2 → Phase 3 เพราะสามเฟสนี้แก้ความเสี่ยงที่ผู้ใช้จะตัดสินใจผิดหรือทำข้อมูลหายโดยตรง จากนั้นจึงทำ Phase 4 เพื่อให้ Retrospective มีหลักฐานจริง และปิดท้ายด้วย Phase 5 สำหรับคุณภาพการใช้งาน

รอบนี้ยังไม่มีการแก้โค้ดและยังไม่ควรปิดใน `HISTORY.md` จนกว่าจะเลือก scope และผ่าน Gate ของ implementation รอบถัดไป
