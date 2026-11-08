# OmniCut UI — แผนปฏิบัติการรายเฟสและการเลือกโมเดล

วันที่: 2026-11-08 · ดำเนินการโดย: Codex (GPT-6.1-sol)

สถานะ: **แผนเอกสารเท่านั้น ยังไม่เริ่ม implementation**

แผนหลัก: [ผลตรวจและทิศทางจาก 10 รอบ](PLAN_OMNICUT_UNSLOP_10_ROUNDS_20261108.md)

เอกสารนี้แตก 7 phase กว้างในแผนเดิมเป็น **10 เฟสทำงาน 00–09** เพื่อให้แต่ละรอบมีขอบเขตและหลักฐานตรวจรับชัดเจน สิบรอบตรวจในแผนเดิมยังเป็นบันทึก audit ไม่ใช่หมายเลขเฟสลงมือ

## 1. คำแนะนำเรื่องโมเดล

**ใช้ GPT-6.1 Terra ได้เป็นตัวหลัก และใช้ Gemini 3.8 Flash ได้เช่นกัน** การเลือกด้านล่างเป็นข้อเสนอสำหรับความเสี่ยงของ OmniCut ไม่ใช่ผล benchmark เปรียบเทียบสองรุ่นบน repository นี้

### 1.1 ข้อเท็จจริงจากเอกสารทางการ

| โมเดล | สิ่งที่เอกสารรองรับ | ผลต่อการเลือกงานนี้ |
|---|---|---|
| GPT-6.1 Terra | เน้น visual reasoning, computer use และงานเขียน; รับภาพเป็น input; รองรับ reasoning `high` และระดับอื่น | เป็น candidate สำหรับอ่านภาพ UI, ปรับ presentation และตรวจงานจากภาพพร้อม source |
| Gemini 3.8 Flash | ระบุการใช้กับ software engineering ระยะยาว, agents และ enterprise workflows; รับ text/image/video/audio/PDF และให้ text output; thinking `low/medium/high` | เป็น candidate สำหรับ implementation ที่แบ่งขอบเขตชัด และ review ภาพประกอบโค้ด |
| GPT-6.1 Sol | เอกสารระบุ complex coding, computer use และ professional work | เป็นตัวเลือกเมื่อมี bug ที่ต้อง trace หลายระบบหรือให้ reviewer ช่วยกับจุดเสี่ยง |

แหล่งอ้างอิงที่เปิดอ่านวันที่ 2026-11-08: [Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra), [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)

เอกสาร Terra ไม่ได้ระบุว่าชนะ Gemini ใน React refactor และเอกสาร Gemini ไม่ได้ยืนยันว่าชนะ Terra ใน visual design จึงไม่จัดอันดับจากชื่อโมเดลหรือคำว่า Flash เพียงอย่างเดียว

### 1.2 วิธีเลือกให้ใช้งานง่าย

- **ต้องการใช้รุ่นเดียว:** เริ่มด้วย **GPT-6.1 Terra, High** ตามตัวเลือกที่ผู้ใช้สนใจ ให้ผ่าน baseline และ pilot ก่อนขยายทั้งแอป คำแนะนำนี้เป็นการเลือกเชิงปฏิบัติ ไม่รับประกันผลจากชื่อรุ่น
- **ทำอยู่ใน Antigravity และสะดวก Gemini:** ใช้ **Gemini 3.8 Flash, High** ได้ โดยส่งเฟสเดียวและไฟล์ที่เกี่ยวข้องในแต่ละครั้ง โหลดสกิลและกฎที่ agent อ่านได้จริง
- **ต้องการใช้สองรุ่น:** ให้รุ่นหนึ่งเป็นผู้แก้และอีกรุ่น review diff/ภาพ/ผลทดสอบเมื่อจบเฟส ไม่ให้ทั้งคู่แก้ source ชุดเดียวพร้อมกัน การแบ่งบทบาทเป็นทางเลือก ไม่จำเป็นต้องใช้สองรุ่นทุกครั้ง
- **งานซับซ้อนติดขัด:** ถ้า trace readiness/save/channel แล้วหาสาเหตุไม่ได้ หรือแก้แล้วเกิด regression ให้ขอ review ด้วย Sol High จากหลักฐานที่ค้าง โดยไม่กวาดแก้หลายระบบเพิ่มเอง
- **งานเบา:** หลัง direction และ components ผ่านแล้ว งานปรับข้อความ UI หรือย้าย token เฉพาะหน้าอาจใช้ Medium ได้ตามตัวเลือกของเครื่องมือ; จุดข้าม state และ contract ใช้ High เป็นจุดเริ่มต้น

ชื่อ effort/thinking ใน UI ของแต่ละเครื่องมืออาจแสดงต่างกัน การตั้ง High เป็นคำแนะนำของรอบ implementation ยังไม่มีการเปลี่ยนโมเดลหรือ settings ใน session นี้

### 1.3 วิธีพิสูจน์ว่ารุ่นที่เลือกเพียงพอ

ให้ทำ Phase 02 และ pilot แรกใน Phase 03/04 ด้วย candidate ที่เลือกก่อน โดยตรวจว่ารุ่นนั้นทำได้ครบดังนี้

1. ทำตามไฟล์และขอบเขตที่ระบุ ไม่เปลี่ยน font/render contract เพื่อแก้ UI
2. ส่งภาพจริงและอธิบายสิ่งที่เปลี่ยนได้ ไม่ตัดสินจาก source หรือ exit code อย่างเดียว
3. ผ่าน tests/build ที่เกี่ยวข้องและรองรับ state ที่กำหนด
4. ไม่สร้าง generic glass/glow/gradient กลับมาเมื่อย้ายไปหน้าใหม่
5. ไม่รายงานว่างานผ่านเมื่อยังไม่มีเครื่องมือหรือหลักฐานตรวจรับ

ถ้ายังขาด ให้จำแนกว่าเป็นปัญหา context, tool access, brief หรือ reasoning ก่อนเปลี่ยนรุ่น โมเดลที่อ่านภาพได้ก็ยังต้องมีเครื่องมือเปิดแอปและเก็บภาพจริงได้

## 2. ภาพรวมสิบเฟส

| เฟส | ผลลัพธ์หลัก | ตัวเลือกเริ่มต้น | ใช้ Gemini 3.8 Flash ได้หรือไม่ | พึ่งพา |
|---|---|---|---|---|
| 00 | ภาพ baseline และทิศทางที่ผู้ใช้เลือก | Terra High | ได้ | ไม่มี |
| 01 | state semantics ที่ตรวจสอบแล้ว | Terra High; Sol review ถ้าซับซ้อน | ได้ พร้อม review จุดเสี่ยง | 00 |
| 02 | tokens และ shared components | Terra High | ได้ | 00 + state contract จาก 01 |
| 03 | shell/navigation ใช้ระบบภาพใหม่ | Terra High | ได้ | 02 |
| 04 | Editor pilot ที่ตรวจภาพและ behavior แล้ว | Terra High | ได้ พร้อม gates ของ Editor | 01–03 |
| 05 | สินค้า/มุมสคริปต์อ่านง่ายและทำงานต่อเนื่อง | Terra High | ได้ | 02–04 และ naming ล่าสุด |
| 06 | Tracker/Gallery/ส่งงานใช้ความหมายเดียวกัน | Terra High | ได้ | 01, 02, 04, 05 |
| 07 | Assets/Analytics ใช้ระบบเดียวกัน | Terra High หรือ Gemini High | ได้ | 02, 03 และ pilot ผ่าน |
| 08 | Settings/Guide/utility/specialized studios ครบ | Terra High หรือ Gemini High | ได้ | 02–07 ตาม surface |
| 09 | mobile, regression และส่งมอบ | Terra High | ได้; ใช้อีกรุ่น review ได้ | 00–08 |

ทุกเฟสมี checkpoint รีวิวก่อนขยายขอบเขต การเริ่ม implementation จะต้องมีคำสั่งใหม่จากผู้ใช้ รอบนี้ยังไม่เริ่มเฟส 00

## 3. ขอบเขตรายเฟส

### Phase 00 — เก็บภาพปัจจุบันและเลือกทิศทาง

**เป้าหมาย:** ให้การตัดสินใจตั้งอยู่บน build ปัจจุบัน เพราะรอบ audit ก่อนยังดู live UI ไม่ได้

**ทำ:** ตรวจ TODO/status/diff ล่าสุด; เก็บ desktop/mobile ของหน้าหลัก; inventory brand/font preference; เลือกทิศทางห้าบรรทัดจากแผนหลักและตัวอย่างข้อมูลที่มีจริง

**ขอบเขต:** สำรวจและทำเอกสาร/หลักฐาน ไม่แก้ application ไม่เรียก paid generation/render/post เพื่อเติมข้อมูล

**ส่งมอบ:** baseline matrix, รายการ state, ข้อจำกัดจริง, ข้อเสนอ direction ที่ผู้ใช้ตรวจดูได้ และรายการ font ที่อนุมัติให้เปลี่ยนถ้ามี

**ผ่านเมื่อ:** ระบุ viewport/build/channel fixture ของภาพได้; ผู้ใช้เลือกหรือแก้ direction แล้ว; แยกภาพเก่าออกจาก baseline ใหม่

**โมเดล:** Terra High หรือ Gemini High; ทั้งคู่ต้องมีเครื่องมือภาพที่ทำงานได้ ถ้ายังเปิดหน้าจอไม่ได้ให้บันทึก blocker ไม่ถือว่า baseline ผ่าน

### Phase 01 — ตรวจความหมายสถานะและจุดเสี่ยง

**เป้าหมาย:** UI แสดงข้อมูลที่ตรวจแล้ว โดยเฉพาะความพร้อม render, save, QC และ publication

**ทำ:** trace ข้อมูลจาก parent ไป readiness chip; แยก unknown/loading/passed/warning/failed; ตรวจ saved/rendered/posted และ advisory score; ตรวจ shared field association/dialog focus ที่ใช้จริง

**ไฟล์หลัก:** `editor/RenderReadinessChip.jsx`, `EditorHeader.jsx`, `EditorShell.jsx`, `ui/Input.jsx`, `ui/Modal.jsx` และ lib/hook ที่พบว่าต้อง trace

**ขอบเขต:** พิสูจน์ source risks ก่อนแก้; แก้เฉพาะ defect ที่พิสูจน์ ไม่เปลี่ยน backend enum หรือเพิ่ม policy บล็อก render ตามความคิดใหม่

**ส่งมอบ:** state truth table, reproduction ของปัญหาที่พบ, diff จำกัดจุด และ meaningful regression tests

**ผ่านเมื่อ:** unknown ไม่ดูเหมือนผ่านโดยไม่มีหลักฐาน; status ไม่ข้าม lifecycle; error/keyboard/focus ถูกตรวจตามส่วนที่แตะ

**โมเดล:** Terra High หรือ Gemini High ใช้ได้; ถ้า logic ข้าม autosave/channel/revision หลายชั้น ให้ Sol High เป็นตัวเลือกสำหรับ review เฉพาะจุด

### Phase 02 — ทำระบบสี ระยะ และองค์ประกอบกลาง

**เป้าหมาย:** มี component states ที่หน้าอื่นใช้ต่อได้โดยไม่คิด style ใหม่ทุกครั้ง

**ทำ:** semantic tokens; theme compatibility; Button/Input/Select/Badge/PageHeader/Modal/Menu states; spacing/radius/icon contract; motion เฉพาะจำเป็น

**ไฟล์หลัก:** `index.css`, `lib/themeManager.js`, `components/ui/*`; caller ตัวอย่างที่จำเป็นต่อการพิสูจน์ component เท่านั้น

**ขอบเขต:** ห้าม global replace gradient/bold/pulse; ห้ามเปลี่ยน font face หรือ render typography โดยไม่ได้อนุมัติ; ไม่รีเซ็ต theme preferences

**ส่งมอบ:** token table ที่ใช้จริง, mapping ของ existing variants, ภาพ default/hover/focus/disabled/loading/error และรายการ exception ของ preview

**ผ่านเมื่อ:** contrast/keyboard ผ่านตาม component; theme เดิมอ่านได้; UI font/preview ไม่เปลี่ยนโดยผลข้างเคียง; pilot เล็กไม่ทำทุก action เป็น primary

**โมเดล:** Terra High เป็นค่าเริ่มต้นที่เสนอ; Gemini High ใช้แทนได้ โดยต้องผ่าน pilot เดียวกัน

### Phase 03 — ปรับ shell, navigation และ header

**เป้าหมาย:** ผู้ใช้รู้บริบทและหาทางไปงานหลักได้เร็ว โดยมีพื้นที่ให้เนื้อหา

**ทำ:** rail 72px เป็นฐาน; แบนส่วนตกแต่ง; label/tooltip/focus; Topbar/PageHeader ไม่ทวนข้อมูลโดยไม่มีหน้าที่; glossary ที่อนุมัติ; context channel ชัด

**ไฟล์หลัก:** `App.jsx`, `Sidebar.jsx`, `Topbar.jsx`, `ui/PageHeader.jsx`; context component เฉพาะ presentation ที่จำเป็น

**ขอบเขต:** คง route ID/ลำดับเมนู/history/channel behavior; Editor ซ่อน Topbar อยู่แล้ว ไม่แก้จากสมมติฐานว่ามีสองแถบซ้ำ

**ส่งมอบ:** ภาพ shell ทุกหน้าหลัก, nav state matrix และคำอธิบาย active/focus/disabled

**ผ่านเมื่อ:** context และ primary task อ่านออก; keyboard เข้าถึงครบ; viewport แคบและชื่อยาวไม่ทำ action หาย

**โมเดล:** Terra High หรือ Gemini High; phase นี้เหมาะใช้เป็น pilot ประเมินการทำตาม direction ของ candidate

### Phase 04 — ปรับ Editor เป็นหน้าต้นแบบ

**เป้าหมาย:** preview 9:16 เด่น และควบคุมงานตัดต่อได้โดยไม่เสียพื้นที่ให้ chrome

**ทำ:** ใช้ Header สามโซนล่าสุด; ปรับ hierarchy ระหว่าง project/save/tools/readiness/render; asset/inspector groups; timeline surrounding chrome; focus mode และชื่อโปรเจกต์ยาว

**ไฟล์หลัก:** `editor/EditorHeader.jsx`, `ProjectSelector.jsx`, `HeaderMenu.jsx`, `SaveStatusChip.jsx`, `ViewToggleGroup.jsx`, `RenderReadinessChip.jsx`, `AssetPanel.jsx`, `Inspector.jsx`, `Timeline.jsx`

**ขอบเขต:** preserve panel persistence, timeline math, preview coordinates, cue, font, safe zone และ render payload; `SequencePlayer`/subtitle engine อยู่นอกงานตกแต่ง

**ส่งมอบ:** ภาพก่อน/หลัง, walkthrough เปิด/เลือก/แก้/บันทึก/ตรวจพร้อม, ผล regression ที่เกี่ยวข้อง และรายการปัญหาที่ไม่รวมในเฟส

**ผ่านเมื่อ:** action render ไม่หลุดจอ; preview ยังเป็นชิ้นงานเดิม; save/undo/load ไม่ regress; ถ้าจำเป็นต้องแตะ output ต้องเปิด scope เพิ่มและผ่าน parity/FFmpeg gates

**โมเดล:** Terra High ทำได้เป็นหลัก; Gemini High ทำได้เมื่อ brief/file scope ชัด; code review จุดเสี่ยงเลือก Sol High ได้

### Phase 05 — ปรับสินค้าและมุมสคริปต์

**เป้าหมาย:** เลือกสินค้า อ่านมุมสคริปต์ และเปิดตัดต่องานที่ต้องทำต่อได้ชัด

**ทำ:** product selector, image/name/model/code hierarchy, angle list/review, next action, search/filter, empty/error/loading/long-name cases

**ไฟล์หลัก:** `ProductToClip.jsx`, product detail/review components ที่เกี่ยวข้อง

**ขอบเขต:** ใช้ canonical naming ล่าสุด ไม่ sanitize ชื่อซ้ำใน store; ไม่ rewrite script/caption; ไม่เริ่ม generation เพื่อ demo

**ส่งมอบ:** populated/empty/partial/bulk selection states และเส้นทางจากสินค้าไป Editor

**ผ่านเมื่อ:** แยกรุ่นสินค้าได้; ไม่ทำ badge ทุกชนิดเด่นเท่ากัน; กลับจาก Editor แล้ว context ถูกต้องตาม behavior ที่รองรับ

**โมเดล:** Terra High หรือ Gemini High ใช้ได้; ต้องอ่านผล naming ของ Antigravity ล่าสุดก่อนลงมือ

### Phase 06 — ปรับ Tracker, Gallery และการส่งงาน

**เป้าหมาย:** ผู้ใช้เข้าใจว่างานอยู่ขั้นใด ผ่าน QC หรือยัง และส่งต่อด้วยช่องทางใด

**ทำ:** card/row hierarchy, phase headers, filter/detail, QC/cover/caption/posting labels, download/mobile handoff และ schedule/activity presentation ที่เกี่ยวข้อง

**ไฟล์หลัก:** `ContentTrackerHub.jsx`, `ExportGallery.jsx`, `ScheduleAgenda.jsx`, `ActivityCenter.jsx`

**ขอบเขต:** ไม่เพิ่ม drag ข้ามสถานะ; ไม่รวม downloaded/scheduled/posted; ไม่เปลี่ยน export identity หรือ public receipt logic

**ส่งมอบ:** state matrix ของ lifecycle/QC/job/publication, ภาพรายการ/รายละเอียด และ walkthrough ส่งงานด้วย fixture

**ผ่านเมื่อ:** งานไม่มีปก/ยังไม่ผูก Angle/รอ QC ไม่ดูพร้อมโดยไม่มีข้อมูล; posted lock คงเดิม; ติดตามงานที่ error ได้

**โมเดล:** Terra High หรือ Gemini High; logic publication ที่เปลี่ยนจริงต้องผ่าน review และ regression เฉพาะทาง

### Phase 07 — ปรับ Assets และ Analytics

**เป้าหมาย:** สื่อและข้อมูลจริงเป็นจุดเด่น ควบคุมและอ่านได้ต่อเนื่องกับหน้าอื่น

**ทำ:** asset filter/preview/player states; selected item; shared/product/generated labels; KPI units/period; chart hierarchy/series; no-data/error ต่างกัน

**ไฟล์หลัก:** `MediaAssetsHub.jsx`, `analytics/AnalyticsHub.jsx`, `MetricKpiCard.jsx`, chart/tab components

**ขอบเขต:** ไม่แก้/ลบ raw/assets; ไม่สร้างข้อมูลกราฟหรืออ้างผล TikTok ที่ไม่มี; สี data series ไม่ถูกลบทิ้งเพราะนโยบายสี chrome

**ส่งมอบ:** ภาพ asset variants, analytics tabs และ key states พร้อมข้อมูล fixture ที่อธิบายได้

**ผ่านเมื่อ:** controls สม่ำเสมอ; รู้ว่า audio ใดเล่น; ข้อมูล zero/no-data/error ไม่ปะปน; chart อ่านได้โดยไม่พึ่งสีอย่างเดียว

**โมเดล:** Terra High หรือ Gemini High เลือกตามเครื่องมือและ workflow ที่สะดวก ไม่ต้องสลับรุ่นถ้า pilot ผ่านแล้ว

### Phase 08 — ปรับ Settings, Guide และหน้ารองเฉพาะทาง

**เป้าหมาย:** ไม่มีส่วนสำคัญหลุดจากระบบภาพและภาษาที่ตกลงไว้

**ทำ:** interface/provider/render setting scopes; Guide ตาม glossary; Login/session error; AI dock/approval; HyperFrames/Gadget workflow surrounding UI

**ไฟล์หลัก:** `SystemSettings.jsx`, `UserGuide.jsx`, `LoginScreen.jsx`, `agent/*`, `hyperframes/HyperFramesHub.jsx`, `gadget-media/*`

**ขอบเขต:** เปลี่ยนเฉพาะ chrome; ไม่เปลี่ยน approved master/composition/font/TTS; ไม่ลดการอนุมัติหรือซ่อนต้นทุนคำขอ

**ส่งมอบ:** coverage checklist ของหน้ารอง พร้อมภาพ/state ที่เกี่ยวข้อง และเอกสารชื่อปุ่มตรงกับของจริง

**ผ่านเมื่อ:** setting แสดง scope ชัด; theme เก่าไม่หาย; revision accepted/finalized ต่างกัน; approval ยังคงมีผลตามเดิม

**โมเดล:** Terra High หรือ Gemini High; หลังระบบนิ่ง งาน copy บางชิ้นใช้ Medium ได้ แต่ยังต้อง review glossary

**แบ่งงานย่อย:** 08A Settings/Guide/Login → 08B Agent/Approval → 08C HyperFrames/Gadget; ทำเป็นรอบย่อยตามขนาด diff

### Phase 09 — เก็บ mobile/tablet, regression และส่งมอบ

**เป้าหมาย:** ทุก flow หลักใช้ได้บนอุปกรณ์เป้าหมายและมีหลักฐานว่าปรับแล้วไม่ทำงานเดิมเสีย

**ทำ:** responsive shell กับ MobileShell แยกบริบท; touch/keyboard/safe-area; 200% zoom; long Thai text; offline/interrupted requests; regression และ visual review ทั้ง flow

**ไฟล์หลัก:** `mobile/MobileShell.jsx`, Today/Intake/Review/Post/Library และ responsive controls ที่ต้องแก้จริง

**ขอบเขต:** ไม่บีบ desktop Editor เป็นภาพย่อทั้งหน้า; ไม่เปลี่ยน route/history; ไม่เรียก paid generation/post จริงเพื่อ smoke test

**ส่งมอบ:** viewport/state matrix, ผล tests/build/visual review จริง, known limitations, accepted design decisions, rollback points และประวัติรอบงาน

**ผ่านเมื่อ:** primary action เข้าถึงได้; ไม่มี focus/keyboard/safe-area blocker; migrated surfaces ครบ; test artifacts อยู่ใน temp และ cleanup ตามกฎ; ฟอนต์และ output คง contract

**โมเดล:** Terra High หรือ Gemini High; reviewer อีกโมเดลเป็นตัวเลือกสำหรับจุดเสี่ยง ไม่แทนการเปิดดูภาพและรัน checks

**แบ่งงานย่อย:** 09A mobile/tablet defects → 09B end-to-end/regression → 09C review/documentation โดยไม่ขยาย scope ระหว่าง review

## 4. วิธีส่งงานให้โมเดลต่อหนึ่งเฟส

ใช้ prompt ร่วมนี้ เปลี่ยนเฉพาะชื่อเฟสและ state ที่ต้องตรวจ ไม่ต้องส่งเอกสารทั้งหมดซ้ำทุกครั้ง

```text
ทำเฉพาะ Phase <หมายเลข> จาก
_Docs/Plans/PLAN_OMNICUT_UNSLOP_PHASE_RUNBOOK_20261108.md
อ่านทิศทางและข้อจำกัดที่เกี่ยวข้องจากแผนหลัก 10 รอบ

ก่อนแก้: อ่าน TODO, git status และ diff ของไฟล์เป้าหมายล่าสุด
บันทึกแผนรอบนี้ใน TODO พร้อม agent/model และใช้ Jev ตามกฎโปรเจกต์
ใช้ unslop, impeccable, ui-ux-pro-max ตามขอบเขตงาน
สกิลต้องอยู่ในตำแหน่งที่ agent นั้นอ่านได้จริง

ทำตาม file scope, state matrix และ gate ของเฟสนี้
รักษา channel/project identity, font/text/render contract และข้อมูลจริง
ห้าม global replace style โดยไม่แยก chrome ออกจาก video/composition

ส่งภาพจริงและผล checks ของส่วนที่เปลี่ยน
รายงาน changed files, behavior, pass/fail, ข้อจำกัดและ rollback point
จบที่ checkpoint ของเฟสนี้ ไม่เริ่มเฟสถัดไปเอง
ถ้าเครื่องมือตรวจภาพใช้ไม่ได้ ให้บอกสิ่งที่ยังพิสูจน์ไม่ได้และไม่ติ๊ก visual gate
```

เมื่อใช้ Gemini ใน Antigravity ต้องให้ agent โหลด SKILL.md ที่เข้าถึงได้จริง การติดตั้ง Unslop ใน Codex ไม่ได้ยืนยันว่า Antigravity โหลดสกิลนั้นอัตโนมัติ ใช้ path จริงที่อ่านได้หรือ install ให้ถูกระบบในงานแยกเมื่อจำเป็น

## 5. การแบ่งงานและเกณฑ์เปลี่ยนโมเดล

- ให้หนึ่งโมเดลถือครองไฟล์ที่กำลังแก้ในหนึ่งรอบ; ถ้ามีงานร่วมให้แจ้ง ownership ใน TODO
- งาน review ทำ read-only ก่อน แล้วส่งข้อพบกลับให้ผู้แก้; ไม่ให้ reviewer rewrite งานพร้อมกัน
- ก่อน handoff บันทึก baseline/diff/status/ผลตรวจจริงและจุดที่ยังไม่ผ่าน ไม่พึ่งความทรงจำในแชท
- ถ้าโมเดลแก้เกิน scope ให้ย้อนเฉพาะ diff ของรอบที่ทำได้อย่างปลอดภัยและลดขนาดงาน ไม่สั่ง “ทำทั้งหมดใหม่”
- ถ้าติดซ้ำหลังมี reproduction และ test ที่ชัด ให้เปลี่ยน reviewer หรือเพิ่ม reasoning ตามปัญหาที่เหลือ ไม่สมมติว่ารุ่นใหญ่จะตรวจภาพแทนเครื่องมือได้
- คำแนะนำนี้ไม่มีการเปิด sub-agent, สลับโมเดล, ปรับ setting หรือเริ่ม implementation จริง

## 6. สิ่งที่ตรวจในรอบเอกสารนี้

- เปิดเอกสารทางการของ GPT-6.1 Terra และ Sol; อ่านหน้า Gemini 3.8 Flash ทางการผ่าน HTTP เพราะเครื่องมือเว็บไม่รองรับ content-type Markdown ของหน้านั้น
- แยกความสามารถที่ผู้พัฒนาระบุออกจากคำแนะนำเฉพาะงานและผลประเมินที่ยังไม่ได้ทำ
- จัด dependency ของ 10 เฟสให้ย้อนกลับไปหา file scope/gates ในแผนหลักได้
- Jev ก่อนจัดเอกสารได้ `noul 0.66`, `confidence null`, `verdict escalate`; ผลนี้ไม่ใช่หลักฐานอนุมัติ ทิศทางยังเป็นร่างตามการอนุญาตให้ทำเอกสารต่อก่อนหน้าและคำขอแตกเฟสโดยตรงของผู้ใช้
- Jev หลังจัดเอกสาร โดยส่ง excerpt จริง ได้ `noul 0.96`, `confidence null`, `verdict escalate` สำหรับคำถามว่าแยกแผน/คำแนะนำออกจาก implementation/benchmark ชัดหรือไม่ จึงไม่ถือเป็นการผ่าน confidence gate และไม่มีการเริ่ม implementation; ลบไฟล์ JSON ชั่วคราวที่สร้างเพื่อเรียก Jev แล้ว
- ยังไม่มีผลทดสอบ Terra เทียบ Gemini บน OmniCut, ไม่มีการวัดต้นทุนต่อเฟส และไม่มีการรับรองผลลัพธ์จาก model name

รอบลงมือแรกที่เสนอ: **Phase 00 ด้วย Terra High** หลังผู้ใช้สั่งเริ่มงาน ส่วนคำสั่งรอบปัจจุบันจบที่แผนและคำแนะนำโมเดล
