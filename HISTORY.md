# 📜 OmniCut Pro Studio — History งานที่ทำเสร็จแล้ว

คลังประวัติรอบงานที่ปิดแล้ว **ห้ามแก้ย้อนหลัง** — เป็นบันทึกว่าตอนนั้นทำอะไร วัดได้เท่าไหร่ เจออะไร

- งานที่ยังไม่เสร็จอยู่ที่ [TODO.md](file:///d:/Winona/Programmer/Capcut/TODO.md)
- กติกา: [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md)
- รอบไหนปิด ให้ **ย้ายบล็อกเต็มมาที่นี่** แล้วเหลือบรรทัดเดียวใน `TODO.md` — กัน `TODO.md` บวมจนหาของไม่เจอ

## สารบัญ

| รอบ | งาน | วันที่ | ผลลัพธ์ |
| :--- | :--- | :--- | :--- |
| Round 1 | รวม hook banner กับ text overlay เป็นโมเดลเดียว | 2026-09-05 | ปิดบั๊ก 12 ตัว · commit `20e2cc5` |
| Round 2 | วางกฎรอบงาน + ตั้ง Todo กลาง | 2026-09-05 | `work_loop.md` + `TODO.md` |
| Round 3 | ซ่อมฐาน + รวม writer + easing | 2026-09-05 | ซ่อม drift 3 ตัว · `overlay_events.py` · accel |
| Round DOC-1 | ตรวจโค้ดและอัปเดตเอกสารหลัง Refactor | 2026-09-05 | `ARCHITECTURE.md` + `testing_standard.md` |
| Round BUG-1 | แก้ปุ่มสร้างคลิปใหม่กดไม่ได้ (executeRender ใน useRenderJob) | 2026-09-05 | คืนชีพ executeRender & telemetry · npm test 52 pass · build pass |
| Round 4 | per-word layout (static, พิสูจน์ว่าเหมือนเดิมเป๊ะ) | 2026-09-05 | word_layout.py + overlayLayoutClient.js · pytest 344 pass · npm test 54 pass · render parity pass |
| Round 5 | per-word animation (คำทยอยเข้าทีละคำ) | 2026-09-05 | word_stagger_ms · ASS \org & \t · Canvas 2D mirror · pytest 347 pass · npm test 54 pass · build pass |
| Round 6 | ช่องใหม่ที่ mirror ได้เป๊ะ (Loop/Out + Tier A Skew) | 2026-09-05 | Full motion pipeline + Skew \fax / Canvas transform · pytest 351 pass · npm test 54 pass · build pass |
| Round 7 | template v2 + แกลเลอรีที่ขยับได้ | 2026-09-05 | 8 templates + motion presets · Animated gallery · pytest 356 pass · npm test 54 pass · build pass |
| Round BUG-2 | แก้ข้อความซ้อนทับกันเป็นก้อนใน SequencePlayer (Hook / Text clumping) | 2026-09-05 | Guard Hook header & non-staggered overlays to monolithic · Contract test · pytest 356 pass · npm test 54 pass · build pass |
| Round BUG-3 | angle ชนกัน (คลิปผิดสคริปต์) ใน Content Tracker Hub + ปุ่มปักตะกร้า TikTok | 2026-09-06 | reconcile collision guard + data_conflict_note · rollback ครอบทุก status · tiktok_product_id UI · pytest 367 pass · build pass |
| Round TRK-3 | บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์ & การ์ดตัดต่อเสร็จแนวนอน) | 2026-09-06 | Today-Only posted + Archive Modal · Script Library Modal (หยิบทำวันนี้) · Compact Rendered Cards ~95px · pytest 373 pass · build pass |
| Round TRK-2 | ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet) & จัดกลุ่มย่อการ์ด (Product Grouping / Quick Pills) | 2026-09-06 | Daily Run Sheet tab (4 slots + auto-rotate + schedule time) + Quick Pills + Accordion · pytest 373 pass · npm test 54 pass · build pass |
| Round TRK-1 | เพิ่มปุ่มส่งคลิปไป TikTok Studio พร้อม Modal ตรวจสอบ/ปักตะกร้า ในหน้า Tracker | 2026-09-06 | ContentTrackerHub 2-row buttons + Post Modal + Inspect toolbar · pytest 372 pass · npm test 54 pass · build pass |
| Round PROD-1 | เพิ่มช่อง TikTok Product ID ตอนสร้างสคริปต์ + Fallback ค้นหาด้วยชื่อ + Click-to-Edit Cart ID ย้อนหลัง | 2026-09-06 | ProductToClip modal + Header badge edit + auto-resolve shortlinks · pytest 372 pass · npm test 54 pass · build pass |

| Round POST-3.14 | Cover Studio portal entry, project-based cover naming, and LOG01 legacy project migration | 2026-09-07 | commit 2a1e395 -> frontend 63 tests pass -> build pass -> backend compile/tests pass |
| Round POST-3.15 | Prefer project-named covers in export metadata before the legacy product fallback | 2026-09-07 | focused backend tests 8 passed -> compileall passed |
| Round POST-3.19 | Restore generated cover visibility in the TikTok post modal after backend refresh | 2026-09-07 | User confirmed step 5 cover upload works; focused backend tests 14 passed; frontend tests 65 passed; build passed |
| Round POST-3.21 | Multi-day persistent TikTok publishing queue and Agenda/Extension handoff | 2026-09-07 | Schedule API/store, multi-day Agenda, single/bulk assignment, five-minute timezone-safe slots, guarded reschedule, extension queue handoff; pytest 873 passed, npm test 82 passed, build and browser smoke passed |
| Round POST-3.22 | Weekly schedule templates and product-rotating auto-fill | 2026-09-07 | Backend template persistence/preview/atomic commit; Agenda editor and overdue requeue; pytest 879 passed, npm test 83 passed, build passed |
| Round POST-3.23 | Reduce default publishing schedule to three slots | 2026-09-07 | Defaults 12:30, 19:00, 21:30; legacy five-slot templates migrate safely; pytest 891 passed, npm test 83 passed, build and compileall passed |
| Round POST-3.24 | Show saved-cover status in the daily queue | 2026-09-07 | Bright cover icon when a 3:4/9:16 cover exists, subdued icon when missing, Cover Studio action preserved; npm test 83 passed, build and live Agenda smoke passed |
| Round POST-3.25 | Redesign Extension UX/UI (Cyber-Studio Dark, IBM Plex Sans Thai, Studio Monitor & Stepper Pipeline) | 2026-09-07 | Embedded IBM Plex Sans Thai fonts; Studio Monitor card; 2-column affiliate grid; Stepper Pipeline with progress meter; zero emoji pollution; 12/12 extension tests pass; live browser verified |
| Round POST-3.26 | เพิ่มปุ่มเปิด/สลับแท็บ TikTok Studio ใน Extension (Tab 1, Tab 2, Header, Popup) | 2026-09-07 | Quick bar ใน Tab 1, Banner ใน Tab 2, Header button, Popup button; Auto-focus/activate tab; 13/13 tests pass; Clean UI standard |
| Round POST-3.27 | ลดความซ้ำซ้อนปุ่มเปิด TikTok Studio ให้เหลือจุดเดียวใน Header ตามที่ User ร้องขอ | 2026-09-07 | รวมเหลือจุดเดียวใน Header bar (`#headerOpenTikTokBtn`); ลบปุ่มซ้ำซ้อนใน Tab 1 และ Tab 2 ออกทั้งหมด; 13/13 tests pass; Clean UI standard |
| Round RAW-1 | แก้ rename คลิปดิบที่ติด file lock และจัดเลย์เอาต์ Raw Vault แบบ responsive | 2026-09-07 | ถอด preview ก่อน rename, retry WinError 32 พร้อมข้อความกู้คืน, product groups แบบ responsive; pytest 896 passed, npm test 85 passed, build ผ่าน |
| Round HOK-1 | ระบบ Custom Hook Template Studio (สร้างและบันทึกแม่แบบฮุกด้วยตัวเอง) | 2026-09-07 | CRUD API + 02_Assets/Templates/custom_hook_templates.json + UI บันทึกสไตล์ใน Inspector + AssetPanel + Toolbar optgroup; pytest 2 passed, parity 149 passed, npm test 85 passed, build passed, live browser verified |
| Round EDT-1 | ตรวจสอบและปรับปรุง UX/UI หน้าตัดต่อ (Editor Friction & Speed Optimization) | 2026-09-07 | แก้ Safe Zone 420px overlay ถูกต้องตามสัดส่วน; เพิ่ม Quick Hook dropdown ใน Toolbar; เพิ่ม 1-Click Reset Zoom; ลดคลิกจาก 25 เหลือ 10; npm test 85 passed; build passed; live browser verified |
| Round BUG-4 | แก้ไขคลิปบวมสะสมทุกครั้งที่เรนเดอร์ (Transition Overlap Compounding Feedback Loop) | 2026-09-08 | แก้ video_assembly_stage + video_editor acc_dur + normalized 5 swollen projects + pytest 159 passed + parity 149 passed |
| Round POST-4 | ป้องกันการลบวิดีโอที่โพสต์แล้วใน Gallery, ล็อกไม่ให้เรนเดอร์ซ้ำในหน้าตัดต่อ และแก้ปัญหาย้อนสถานะ | 2026-09-08 | ProductStore rollback guard + Gallery disable delete + Editor lock render + tests passed 3/3 |
| Round POST-5 | ยกระดับความสมบูรณ์และเสถียรภาพของวงจรชีวิตคลิปที่โพสต์แล้ว (Full Posted Evidence & Lifecycle Integrity Lockdown) | 2026-09-08 | DB immunity against demoting/deleting posted angles + Editor delete modal locked + ProductToClip read-only + Drag&Drop guard + Mobile mark-posted file move + tests passed 7/7 |
| Round ACCENT-PRO-1 | เพิ่มสไตล์ตกแต่งป้ายฮุกให้หลากหลาย 11+ รูปแบบระดับโปร (Adaptive Framing, Hybrid Color, Motion Sync, 100% Parity) | 2026-09-08 | 12 styles catalogued + ASS vector drawing (\p1) + Canvas 2D mirror + accent_color picker + 149 parity pass + 147 smoke pass |
| Round PREV-2 | ซ่อมบั๊กพรีวิวดำและข้อความตกค้าง (Fix Infinite Seek Loop in renderAt & Unconditional Canvas Clear) | 2026-09-08 | นำ currentTime mutation ออกจาก renderAt + เคลียร์ canvas ต้นเฟรมใน tick() + วาด readyState >= 2 ทันที + 149 parity pass + 147 smoke pass + build pass |
| Round ACCENT-REV-1 | คืนค่าตัวเลือกตกแต่ง (Accent) กลับเป็น 3 ตัวเลือกดั้งเดิมตามคำสั่งผู้ใช้ | 2026-09-08 | คืนค่า underline, badge, none ตามคำสั่งผู้ใช้ · 149 parity passed · build passed · smoke tests passed |
| Round STK-1 | Interactive Sticker Timeline Track, Free Canvas Drag/Resize, and Parity Render Engine | 2026-09-08 | แทร็กสติกเกอร์บนไทม์ไลน์ + Drag & Resize อิสระบน Canvas + ลบ 6-pos grid + Parity 100% (between enable & normX, normY) · pytest 148 passed · parity 149 passed · build passed · live browser verified |
| Round STK-2 | Multi-Sticker Support, 3-Second Default Duration, and Smooth Canvas Resizing | 2026-09-08 | Default 3s + Linear vector projection smooth resize handles + Multi-stickers array & timeline auto-stacking sub-lanes + FFmpeg multi-overlay chaining + Parity 100% · pytest 149 passed · test_multi_stickers 2 passed · npm test 85 passed · build passed · live browser verified |
| Round STK-3 | Sticker Baseline 100% Size, Track Eye Toggle, Deletion, and Preview-Before-Add | 2026-09-08 | STICKER_BASE_WIDTH 160 + Eye toggle hides canvas + Delete key/Inspector + Preview then '+' add · pytest 299 passed · npm test 85 passed · build passed · live browser verified |
| Round SUB-THAI-1 | แก้สระและวรรณยุกต์ไทยซ้อนกันในคลิปเรนเดอร์ | 2026-09-08 | เปลี่ยน caption entrance จาก ASS `\\fscx/\\fscy` เป็น alpha fade 70ms และ mirror ใน Canvas; เพิ่ม FFmpeg multi-frame regression ด้วย `นั่งพิมพ์งานทั้งวัน`; pytest 926 passed · npm test 85 passed · build/compileall passed |
| Round STK-PRO-1 | ชุดสติกเกอร์และป้ายรีวิวสายไอทีระดับโปร (Photorealistic Tech Review Badges) | 2026-09-08 | ออกแบบ Master Prompt 3 ชุด + เจนและสไลซ์ 18 ป้ายไอทีระดับโปร (Dark Glass, CNC Aluminum, Titanium, Micro-LED) + สำรองของเดิมลง _backup_cartoon/ + อัปเดต AssetPanel · parity/behavior 159 passed · npm test 85 passed · build passed · 18 RGBA verified |

## Round STK-PRO-1 — ชุดสติกเกอร์และป้ายรีวิวสายไอทีระดับโปร (Photorealistic Tech Review Badges)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ:**
1. **ออกแบบ Master Prompts สาย Tech ฮาร์ดแวร์จริง 3 ชุด (18 ป้าย):**
   - ผู้ใช้แจ้งว่าสติกเกอร์ชุดก่อนหน้าดูเป็นการ์ตูน/ของเล่นพลาสติก ไม่เข้ากับคลิปรีวิวสินค้าไอที จึงออกแบบ Master Prompts ใหม่ทั้งหมด โดยเน้นวัสดุระดับสูง (Photorealistic Industrial Design): Smoked Tempered Glass, CNC-machined Space Gray Aluminum, Brushed Titanium, Laser-etched typography, Micro-LED telemetry lights, Multi-layer circuit traces และ Cyber HUD callouts ปราศจากตัวการ์ตูนหรือกราฟิกคอมิกส์ 100%
   - **Sheet 1 (Core Review Badges):** PROS (Matte obsidian pill, neon green LED), CONS (Space gray aluminum, crimson LED), WARNING (Titanium hex plate, amber hazard stripes), PRO TIP (Dark glassmorphism, cyan cyber circuit trace), PERFORMANCE (PCB chip plate, neon speedometer gauge), VERDICT (Matte black ceramic plaque, gold rating bars)
   - **Sheet 2 (Tech Specs & Callouts):** BATTERY LIFE (Dark glass lithium cell, emerald power LEDs), BUILD QUALITY (Brushed titanium shield, chamfered bevels), SPECS (PCB telemetry tag, cyan LEDs), BEST VALUE (Obsidian plaque with gold trim and diamond), TECH ARROW (Aerodynamic titanium pointer with cyan neon edge), HUD CALLOUT (Cyber camera viewfinder reticle frame)
   - **Sheet 3 (Hardware Features & Rating):** SCORE (9.8/10 digital OLED segment display with 5 gauge dots), MUST BUY (Brushed titanium award medal, gold rim), DISPLAY (OLED deep black screen, liquid HDR wave), AUDIO (CNC perforated speaker grille, cyan soundwave), CAMERA (Leica-style camera lens module, aperture blades), CONNECTIVITY (Glass badge, cyan Wi-Fi lightning bolt)
2. **เจนรูปภาพความละเอียดสูง 3 แผ่นและสไลซ์โปร่งใส (Alpha Cutout):**
   - เจนภาพ 3 แผ่นด้วย `generate_image` บน Solid Pure White (`#FFFFFF`) พร้อม Thick Die-cut Border ตามกฎ `sticker_generation.md`
   - สร้างสคริปต์ `tools/slice_pro_tech_stickers.py` ตัดแยกแต่ละป้ายและตัดพื้นหลังโปร่งใสด้วย AI `rembg` ได้ PNG คมกริบขนาด ~500-600px พร้อม Bounding box ที่กระชับพอดี
   - สำรองสติกเกอร์การ์ตูนเดิม 12 ชิ้นไว้ใน `02_Assets/Stickers_Memes/_backup_cartoon/` ตามกฎเหล็กข้อ 1 (Strict Rule 1)
   - ปล่อยไฟล์ PNG โปร่งใสทั้ง 18 ป้ายลงใน `02_Assets/Stickers_Memes/`
3. **อัปเดตชื่อภาษาไทยใน Frontend UI (AssetPanel.jsx):**
   - อัปเดตดิคชันนารี `STICKER_TITLES` ใน `frontend/src/components/editor/AssetPanel.jsx` ให้ครอบคลุมสติกเกอร์ใหม่ทั้งหมด 18 ชิ้นด้วยชื่อภาษาไทยทางการ สะอาด ปราศจากอีโมจิหรือสัญลักษณ์ซ้ำซ้อนตามกฎเหล็กข้อ 8

### Gate

- [x] `python -m compileall -q scripts` (ผ่าน: 0 errors)
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider` (ผ่าน: 159 passed, 2 warnings in 8.55s)
- [x] `npm --prefix frontend test` (ผ่าน: 85 passed in 1.60s)
- [x] `npm --prefix frontend run build` (ผ่าน: 1963 modules built in 3.30s)
- [x] ตรวจสอบไฟล์ PNG โปร่งใสทั้ง 18 รายการใน `02_Assets/Stickers_Memes/` (ผ่าน: ครบ 18 ชิ้น โหมด RGBA มี Alpha โปร่งใส 100%)

### Notes

- สติกเกอร์เดิม 12 ชิ้นที่เป็นภาพการ์ตูนได้รับการสำรองไว้อย่างปลอดภัยที่ `02_Assets/Stickers_Memes/_backup_cartoon/`
- ป้ายทั้งหมด 18 ชิ้นเป็น Universal Reusable Badges ไม่ระบุรุ่นสินค้าหรือยี่ห้อ สามารถนำไปใช้กับคลิปรีวิวไอทีและแกดเจ็ตได้ทุกตัว
- ใน Editor หน้า AssetPanel แสดงชื่อภาษาไทยชัดเจน เช่น "จุดเด่น (PROS)", "ข้อสังเกต (CONS)", "อายุแบตเตอรี่ (Battery)", "คะแนนรีวิว 9.8 (Score)", "ชิปประมวลผล (Performance)" เป็นต้น

## Round SUB-THAI-1 — แก้สระและวรรณยุกต์ไทยซ้อนกันในคลิปเรนเดอร์

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ:**

1. ตรวจ repro ด้วยข้อความ `นั่งพิมพ์งานทั้งวัน` ซึ่งมีคู่เครื่องหมายซ้อน `ั + ่` และพบว่า caption ใช้ `\\fscx125/\\fscy125` ในช่วง 70ms แรก การขยาย raster หลัง libass จัดตำแหน่ง mark แล้วทำให้เครื่องหมายชนกันได้ในเฟรมต้น ๆ
2. เปลี่ยน caption entrance ใน `scripts/subtitle_engine.py` เป็น `\\alpha&HFF&\\t(0,70,\\alpha&H00&)` ซึ่งไม่เปลี่ยนเรขาคณิตของ glyph และจัดลำดับ tag ให้ shadow fade ไปพร้อมกับตัวอักษร
3. เปลี่ยน Canvas ใน `frontend/src/components/SequencePlayer.jsx` ให้ใช้ `globalAlpha` fade 70ms และคงขนาด/ตำแหน่ง glyph เท่าเฟรม settled เพื่อรักษา Preview = Render
4. เพิ่ม source parity test และ FFmpeg behavioral render test ที่ตรวจเฟรมซ่อน, เฟรมแรกที่มองเห็น และเฟรม settled โดย bounding box ของข้อความต่างกันไม่เกิน 4px

### Gate

- [x] `python -m compileall -q scripts` (ผ่าน)
- [x] Focused subtitle/preview tests: 165 passed, 2 warnings
- [x] Full backend tests: 926 passed, 6 warnings, 110.92s
- [x] `npm test`: 85 passed
- [x] `npm run build`: ผ่าน, 1963 modules built
- [x] FFmpeg behavioral render: stacked Thai marks ผ่าน multi-frame geometry check

Notes: ไม่แตะ `01_Raw/` หรือ `02_Assets/`; ใช้ synthetic fixture ใน temp storage และตรวจภาพจาก FFmpeg จริง

## Round STK-3 — ปรับขนาดสติกเกอร์ 100% เท่ากับขนาดจอที่ผู้ใช้ต้องการ, ซ่อมปุ่มปิดตาแทร็กสติกเกอร์, ลบสติกเกอร์ได้ทุกช่องทาง และระบบพรีวิวก่อนกดบวกเหมือนข้อความ

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ (4 ข้อตามคำสั่ง User):**
1. **ไอคอนขนาดนี้อยากให้เป็น 100% (Baseline 100% Scale):**
   - ขนาดที่ผู้ใช้ชี้ในภาพหน้าจอเดิมมี Scale 40% (~152-160px) ถูกตั้งเป็นขนาดมาตรฐาน 100% (`scale = 1.0`)
   - แก้ไข `STICKER_BASE_WIDTH = 160` ใน `scripts/video_editor.py` และ `baseW = 160` ใน `frontend/src/components/SequencePlayer.jsx`
   - ปรับ scale clamp ให้รองรับได้กว้าง 30% ถึง 350% ลื่นไหลเป็นธรรมชาติ
   - ปรับการทดสอบ Parity ใน `tests/test_phase1_smoke.py`
2. **กดปิดตา สตก ที่ไทมไลน์ไม่ได้อ่ะ (Track Eye Toggle):**
   - ใน `EditorShell.jsx` เพิ่ม state `isStickerHidden` และฟังก์ชัน `handleToggleHideSticker`
   - เชื่อมต่อส่งไปยัง `<Timeline />` (ทั้งโหมดเดสก์ท็อปและมือถือ) และ `<SequencePlayer />`
   - ใน `SequencePlayer.jsx`: เมื่อ `isStickerHidden` เป็นจริง จะหยุดวาดสติกเกอร์บน Canvas ทันที พร้อมป้องกันการคลิก/ลากย้ายสติกเกอร์ที่ถูกซ่อน
3. **เพิ่มได้แต่ลบไม่ได้อ่ะ (Multi-Way Sticker Deletion):**
   - ใน `useEditorCommands.js` ในฟังก์ชัน `deleteSelected()` เพิ่มเงื่อนไข `selection?.type === 'sticker'` ให้ลบออกจากอาเรย์ `stickers: [...]` รองรับปุ่ม `Delete`/`Backspace` บนคีย์บอร์ด และปุ่มถังขยะบน Toolbar
   - สร้างคอมโพเนนต์ `StickerInspector.jsx` แสดงข้อมูลสติกเกอร์ (เวลาเริ่ม, เวลาจบ, สเกล %, พิกัด) พร้อมปุ่มลบสีแดงเด่นชัด `ลบสติกเกอร์`
   - เชื่อมต่อ `StickerInspector` ใน `Inspector.jsx` เมื่อเลือกสติกเกอร์บนไทม์ไลน์
4. **ตอนกดให้พรีวิวก่อน ถ้าอยากให้ลงไทมไลน์ ค่อยกด + เหมือน ข้อความอ่ะ (Preview First & Plus Button Add):**
   - ใน `AssetPanel.jsx` แท็บสติกเกอร์: คลิกที่การ์ดสติกเกอร์จะเป็นการพรีวิว (`onPreviewSticker(s.name)`) โดยยังไม่เพิ่มลงไทม์ไลน์
   - บนหน้าจอวิดีโอ Canvas จะแสดงภาพสติกเกอร์ตัวอย่างกึ่งกลางจอ พร้อมกรอบประสีฟ้านีออนและป้าย `พรีวิวสติกเกอร์` แบบ Ephemeral ชั่วคราว (คลิกนอกกล่องจะปิดพรีวิวอัตโนมัติ)
   - บนการ์ดสติกเกอร์ มีปุ่ม `+` มุมขวาบน (สไตล์เดียวกับ Text Template) เมื่อกดปุ่ม `+` จึงจะเพิ่มสติกเกอร์ลงบนไทม์ไลน์ที่ตำแหน่ง Playhead (ความยาว 3.0s)
   - เพิ่มปุ่มกดด้านล่าง `เพิ่ม [ชื่อสติกเกอร์] ลงไทม์ไลน์` ให้กดเพิ่มได้สะดวกอีกทางหนึ่ง

### Gate
- [x] `python -m compileall -q scripts` (Pass)
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_multi_stickers.py tests/test_phase1_smoke.py -q -p no:cacheprovider` (299 passed in 41.66s)
- [x] `npm test` ใน `frontend/` (85 passed in 1.78s)
- [x] `npm run build` ใน `frontend/` (Pass, 1963 modules built in 4.25s)
- [x] Live Browser Verification (Recorded video `verify_stk3_features_1788859163223.webp`):
  1. ขนาด 100% เท่ากับขนาด 160px บนหน้าจอวิดีโอ
  2. พรีวิวก่อนเพิ่มได้ และมีป้าย "พรีวิว"
  3. กดปุ่ม `+` เพื่อเพิ่มลงไทม์ไลน์ 3.0s
  4. ปุ่มตา [👁️] ซ่อน/แสดงสติกเกอร์บนวิดีโอได้จริง
  5. ลบสติกเกอร์ได้จริงทุกช่องทาง ทั้งปุ่มลบในแผงและปุ่ม Del

## Round STK-2 — Multi-Sticker Support, 3-Second Default Duration, and Smooth Canvas Resizing

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ:**
1. **Default 3 sec:** กำหนดเวลาเริ่มต้นของสติกเกอร์ที่เพิ่มใหม่เป็น 3.0 วินาทีเสมอ (`start = playhead`, `end = min(totalDuration, playhead + 3.0)`)
2. **การยืดขยายให้สมูท (Smooth Linear Resizing):** แก้ไขจาก Euclidean radial distance (`Math.hypot`) ที่กระตุกและสะบัดขยายผิดธรรมชาติเมื่อข้ามแกน มาเป็น Linear Vector Projection (`projectedDelta = deltaX * dirX + deltaY * dirY`, `scaleFactor = 1 + projectedDelta / initialDist`) ทำให้การลากย่อขยายลื่นไหล ติดนิ้ว 1:1 ทุก Handle
3. **รองรับสติกเกอร์หลายตัวพร้อมกัน (Multi-Stickers Array):** เปลี่ยนโมเดลเป็น `stickers: [...]` แสดงบนไทม์ไลน์พร้อมกัน และสามารถทับซ้อนเวลาเดียวกันได้ (Overlapping Stickers) โดยมีอัลกอริทึม `packStickers(stickers)` จัดเรียงแยก sub-lanes อัตโนมัติ
4. **Preview = Render Parity 100%:**
   - ฝั่ง Frontend (`SequencePlayer.jsx`): โหลดและแคชภาพสติกเกอร์ทุกตัวใน `stickerImagesRef`, แสดงสติกเกอร์ทั้งหมดที่อยู่ในช่วงเวลา `t`, รองรับการคลิกเลือกเพื่อย้าย/ย่อขยายแต่ละตัว
   - ฝั่ง Backend (`video_editor.py`, `video_assembly_stage.py`, `pipeline.py`, `api_schemas.py`): รองรับ `stickers: List[Dict]` สร้าง filter complex overlay ต่อเนื่อง `[v_stickered_{i}]` พร้อม `enable='between(t,start,end)'` และขนาด/พิกัดเฉพาะตัว
5. **UI คลีนตาม Rule 8:** ใน `AssetPanel.jsx` แสดงตัวควบคุมสติกเกอร์ที่ถูกเลือก (Inspect Duration, Scale, Center Reset, Delete), รายการชิปสติกเกอร์ทั้งหมดในวิดีโอ, และปุ่มล้างสติกเกอร์ทั้งหมด

### Gate
- [x] `python -m compileall -q scripts` (Pass)
- [x] `pytest tests/test_preview_render_parity.py` (149 passed in 4.74s)
- [x] `pytest tests/test_phase1_smoke.py -k sticker` (3 passed in 1.02s)
- [x] `pytest tests/test_multi_stickers.py` (2 passed in 0.26s)
- [x] `npm --prefix frontend run build` (Pass, 1962 modules transformed, built in 4.88s)
- [x] `npm --prefix frontend test` (85 passed in 1.76s)
- [x] Browser Subagent live visual verification on `LOG01-ปัญหาก่อนใช้_1` (Added 2 overlapping stickers: 3.0s alert badge + 2.3s arrow pointer, verified simultaneous canvas rendering on video, auto-stacked timeline sub-lanes, and smooth resize handles).


วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ:**
- ผู้ใช้สั่ง: "ถ้าแค่เพิ่มข้อความมา ซ้าย ขวา บน ล่าง แล้วเรียกตกแต่งแล้ว ก็พอเถอะ เหมือนเดิม"
- คืนค่าตัวเลือกการตกแต่งป้ายฮุก (Accent) ให้กลับมาสะอาด กระชับ คลีน เหมือนเดิม โดยมีเพียง 3 ตัวเลือกหลักดั้งเดิม:
  1. `underline` ("เส้นใต้เรืองแสง" / Accent Bar)
  2. `badge` ("แถบไฮไลต์" / Badge)
  3. `none` ("ไม่มี" / None)
- ไฟล์ที่อัปเดต:
  - `scripts/hook_motion_presets.py`: คืนค่า `HOOK_ACCENT_PRESETS` เหลือ 3 ตัวเลือกดั้งเดิม
  - `frontend/src/components/editor/inspector/OverlayInspector.jsx`: คืนค่า `FALLBACK_ACCENT_OPTIONS` เหลือ 3 ตัวเลือกดั้งเดิม
  - รีสตาร์ต Backend API Server เพื่อให้ serving ค่าใหม่ทันที
- การทดสอบและ Gate:
  - `python -m compileall -q scripts`: ผ่าน 100%
  - `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider`: ผ่านครบ 149/149 passed
  - `npm --prefix frontend run build`: ผ่านสะอาด 100%
  - `python -m pytest tests/test_phase1_smoke.py -k "accent or hook_motion" -q -p no:cacheprovider`: ผ่าน 8/8 passed

## Round PREV-2 — ซ่อมบั๊กพรีวิวดำและข้อความตกค้าง (Fix Infinite Seek Loop in renderAt & Unconditional Canvas Clear)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสาเหตุ:**
1. **ภาพวิดีโอดำ (Black Screen):** ใน `renderAt(t)` มีการสั่ง `video.currentTime = entry.localTime` เมื่อตรวจพบความคลาดเคลื่อนเกิน 0.08s แต่ `renderAt` ถูกผูกเป็น listener ของ `onSeeked` ทำให้เกิด **Infinite Seek Loop** (seeked -> renderAt -> seek -> seeked) ส่งผลให้ `<video>` ติดสถานะ `seeking = true` ตลอดเวลา ไม่ยอมส่งเฟรมภาพที่ถอดรหัสแล้วออกมายัง Canvas
2. **ข้อความฮุกและซับไตเติลค้าง/ซ้อนทับเป็นภาพซ้อน (Ghosting / Overlay Echo):** ใน `tick()` การสั่ง `ctx.clearRect(0, 0, CANVAS_W, CANVAS_H)` ถูกครอบไว้ใต้เงื่อนไข `if (video.readyState >= 2 && !video.seeking) { if (!framePainted) ctx.clearRect(...) }` เมื่อวิดีโอติด seeking หรือยังไม่มีเฟรมใหม่ `ctx.clearRect` จะไม่ถูกเรียกเลย ทำให้ภาพข้อความของวินาทีก่อนหน้า (เช่น ป้ายฮุกช่วง 0-3s) ค้างอยู่บน Canvas ถาวร ไม่หายไปแม้วินาทีที่เล่นอยู่จะเกิน 3s แล้วก็ตาม

**ผลลัพธ์:**
- `frontend/src/components/SequencePlayer.jsx`:
  - นำ `video.currentTime = ...` ออกจาก `renderAt(t)` 100% ทำให้ `renderAt` ทำหน้าที่วาดเฟรมบริสุทธิ์ หยุดการเกิด Infinite Seek Loop โดยสิ้นเชิง
  - ย้าย `ctx.clearRect(0, 0, CANVAS_W, CANVAS_H)` ขึ้นมาทำงานที่จุดเริ่มต้นของรอบวาดใน `tick()` แบบ Unconditional ทุกเฟรม ลบล้างข้อความ/ซับไตเติลของวินาทีก่อนหน้าที่หมดอายุไปแล้ว ไม่ให้หลงเหลือ ghosting หรือภาพซ้อนบนจอ
  - ปรับปรุงการวาดเฟรมวิดีโอให้วาดทันทีเมื่อ `video.readyState >= 2` โดยไม่ถูกสกัดกั้นด้วยสถานะ `video.seeking` ในคลิปเดียวกัน
  - ลดความซ้ำซ้อนของ event listeners บน `<video>` ให้เหลือเฉพาะ `onLoadedData` และ `onSeeked`
- ตรวจสอบ Gate ผ่านทั้งหมด: Parity 149/149 passed, Smoke 147/147 passed, npm run build passed


## Round ACCENT-PRO-1 — เพิ่มสไตล์ตกแต่งป้ายฮุกให้หลากหลาย 11+ รูปแบบระดับโปร (Adaptive Framing, Hybrid Color, Motion Sync, 100% Parity)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและขอบเขตงาน:**
1. เมนูตกแต่ง ("ตกแต่ง" ใน Inspector) มีเพียง 2-3 แบบ และในบางครั้งไม่โหลดบนหน้าเว็บ ผู้ใช้ต้องการความหลากหลายที่สวยงามระดับมืออาชีพสำหรับคลิป TikTok/Shorts
2. เพิ่มชุดสไตล์ตกแต่ง 11+ รูปแบบ:
   - `bracket` (กรอบมุมไซเบอร์ Tech Brackets `[ ]`), `glow_box` (กล่องนีออนเรืองแสง), `double_bar` (เส้นคู่บนล่าง)
   - `sale_tag` (ป้ายแท็กสินค้าราคาพิเศษ), `pill_badge` (ป้ายแคปซูลโมเดิร์น), `marker` (ไฮไลต์ปากกาเมจิก)
   - `bold_quotes` (เครื่องหมายคำพูดใหญ่ “ ”), `dashed_box` (กรอบเส้นประโฟกัส), `speed_slash` (ขีดเฉียงสปอร์ต //)
   - `gradient_line` (เส้นไล่เฉดมินิมอล), `underline` (เส้นใต้เรืองแสง), `badge` (แถบไฮไลต์), `none` (ไม่มี)
3. ระบบจัดวางอัจฉริยะ (Adaptive Placement): รูปแบบกรอบครอบทั้งป้าย, รูปแบบเส้นเน้นเฉพาะบรรทัดหลัก, รูปแบบแท็ก/คำพูดโอบล้อมข้อความ
4. สีไฮบริด (Hybrid Color): ซิงก์สีอัตโนมัติตามสีไฮไลต์ของป้าย พร้อมให้เลือกสีเฉพาะของตกแต่งได้อิสระใน Inspector (พร้อมปุ่มคืนค่าอัตโนมัติ)
5. Local Catalog Fallback: ให้เมนูหน้าเว็บแสดงครบทั้ง 12 รายการทันทีโดยไม่ต้องรอรีสตาร์ตเซิร์ฟเวอร์
6. Preview = Render Parity 100%: วาดรูปทรงเรขาคณิตตรงกันทั้ง Canvas 2D และ ASS Vector Drawing (`\p1`)

**ผลลัพธ์:**
- `scripts/hook_motion_presets.py`: ลงทะเบียนครบ 12 สไตล์ใน `HOOK_ACCENT_PRESETS`
- `scripts/overlay_model.py` & `frontend/src/lib/overlayModel.js`: เพิ่มฟิลด์ `accent_color` ใน Overlay Look
- `frontend/src/components/editor/inspector/OverlayInspector.jsx`: เพิ่ม `FALLBACK_ACCENT_OPTIONS` และ Accent Color Picker UI พร้อมสวอทช์สียอดนิยม
- `scripts/subtitle/badge_plate_renderer.py`: เพิ่มการสร้างคำสั่งวาดเส้นเวกเตอร์ ASS (`\p1`) ครบทั้ง 11+ สไตล์
- `scripts/subtitle/overlay_events.py`: ซิงก์ Accent เข้ากับไทม์ไลน์และส่งผ่านสี `accent_color` อย่างถูกต้อง
- `frontend/src/components/SequencePlayer.jsx`: รองรับการวาด Canvas 2D ครบทุกสไตล์ตรงกับ ASS 100%
- ผ่าน Gate ตรวจสอบครบทุกตัว: `compileall` ผ่าน, `pytest test_preview_render_parity.py` ผ่าน 149/149 ข้อ, `npm run build` ผ่านสมบูรณ์, `test_phase1_smoke.py` ผ่าน 147/147 ข้อ


## Round POST-5 — ยกระดับความสมบูรณ์และเสถียรภาพของวงจรชีวิตคลิปที่โพสต์แล้ว (Full Posted Evidence & Lifecycle Integrity Lockdown)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาที่ตรวจพบเพิ่มเติม:**
1. ในหน้า Editor (`EditorShell.jsx` + `api_phase1.py`) ตัวเลือกการลบโปรเจกต์แบบ `angle` และ `product` ยังเปิดให้ลบมุมหรือสินค้าที่โพสต์แล้วได้ ทำให้ประวัติสคริปต์และข้อมูลปักตะกร้าหายไปจาก Tracker
2. ในหน้าสินค้า (`ProductToClip.jsx` + `api_products.py`) ยังเปิดให้แก้ไขสคริปต์, แทนที่คำ, และกดรีสคริปต์ AI (Reroll) ในมุมที่โพสต์ไปแล้วได้ ซึ่งทำให้สคริปต์ไม่ตรงกับวิดีโอที่ออนไลน์บน TikTok
3. ในหน้า Tracker (`ContentTrackerHub.jsx`) ฟังก์ชัน Drag & Drop ยังยอมให้ลากการ์ดที่โพสต์แล้วย้อนกลับไปคอลัมน์อื่นได้
4. ใน `ProductStore.py` ฟังก์ชัน `update_angle_status()` และ `remove_angle()` ยังไม่มีการบล็อกการลดสถานะหรือลบมุมที่โพสต์แล้วที่ระดับฐานข้อมูล
5. ในมือถือ (`MobileQuickPostPage.jsx`) การมาร์กโพสต์ยังไม่สั่งย้ายไฟล์จริงจาก `04_Exports/Ready_to_post/` ไป `04_Exports/Posted/`

**ผลลัพธ์:**
- `scripts/product_store.py`: ใน `update_angle_status()` ปฏิเสธการลดสถานะของมุมที่โพสต์แล้ว และใน `remove_angle()` / `delete()` ยกเลิกคำขอลบมุม/สินค้าที่โพสต์แล้ว
- `scripts/api_products.py`: ใน `/api/products/{id}/angles/{aid}/reroll-script` ปฏิเสธการรีสคริปต์มุมที่โพสต์แล้วด้วย HTTP 400
- `scripts/api_phase1.py` และ `frontend/src/components/editor/EditorShell.jsx`: บล็อกการลบแบบ `angle` และ `product` ในหน้าต่าง Delete Project หากมุมนั้นโพสต์แล้ว เหลือเฉพาะการลบไฟล์ตัดต่อดราฟต์ (`project`) คืนพื้นที่ดิสก์
- `frontend/src/components/ProductToClip.jsx`: ล็อกมุมที่โพสต์แล้วเป็น Read-Only (ปิดการแก้ไขบทพูด, ซ่อนปุ่มแทนที่คำ/รีสคริปต์ AI/ตัดใหม่ และแสดงป้ายโพสต์แล้ว)
- `frontend/src/components/ContentTrackerHub.jsx`: ป้องกัน Drag & Drop ไม่ให้ลากการ์ดออกจากคอลัมน์ "โพสต์แล้ว"
- `frontend/src/components/MobileQuickPostPage.jsx` และ `scripts/api_exports.py`: ให้การมาร์กโพสต์ย้ายไฟล์ MP4 เข้า `04_Exports/Posted/` และรับรู้สถานะ `is_posted` ทั้งจากโฟลเดอร์และจากสถานะมุม
- Gate: `python -m compileall -q scripts` ผ่าน, `python -m pytest tests/test_posted_protection.py` ผ่าน 7/7, `npm run build` ผ่าน 100%


## Round POST-4 — ป้องกันการลบวิดีโอที่โพสต์แล้วใน Gallery, ล็อกไม่ให้เรนเดอร์ซ้ำในหน้าตัดต่อ และแก้ปัญหาย้อนสถานะ

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหา:**
1. เมื่อลบวิดีโอหรือลบเวอร์ชันเก่าในหน้า Gallery ระบบเรียก `rollback_by_video_or_project` ทำให้คลิปที่โพสต์ไปแล้ว (`status == "posted"`) ถูกย้อนสถานะกลับมาเป็น `in_production` (กำลังตัดต่อ)
2. หน้า Gallery ยังไม่มีการล็อกไม่ให้ลบคลิปที่โพสต์แล้ว (ต้องเก็บเป็นหลักฐาน)
3. ในหน้าตัดต่อ (Editor) ยังเปิดให้กดเรนเดอร์ซ้ำได้ แม้คลิปนั้นจะโพสต์ไปแล้ว

**ผลลัพธ์:**
- แก้ไข `scripts/product_store.py`: `_roll()` และ `reconcile_existing_projects()` ป้องกันสถานะ `posted` อย่างเข้มงวด
- แก้ไข `scripts/api_videos.py`: บล็อกการลบวิดีโอใน `04_Exports/Posted/` หรือคลิปที่โพสต์แล้ว โดยตอบกลับ HTTP 400
- แก้ไข `scripts/api_render.py` และ `scripts/api_phase1.py`: บล็อกเรนเดอร์/reroll ซ้ำสำหรับโปรเจกต์ที่โพสต์แล้ว โดยตอบกลับ HTTP 400
- ปรับปรุง `frontend/src/components/ExportGallery.jsx`: ซ่อน/disable ปุ่มลบสำหรับคลิปที่โพสต์แล้ว พร้อมแสดงป้าย `โพสต์แล้ว (ห้ามลบ)`
- ปรับปรุง `frontend/src/components/editor/`: เพิ่ม prop `isPosted` ให้ปุ่มเรนเดอร์กลายเป็น `โพสต์แล้ว (ล็อก)` เมื่อคลิปถูกโพสต์แล้ว
- Gate: `python -m compileall -q scripts` ผ่าน, `pytest tests/test_posted_protection.py` ผ่าน 3/3


## Round BUG-4 — แก้ไขคลิปบวมสะสมทุกครั้งที่เรนเดอร์ (Transition Overlap Compounding Feedback Loop)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหา:**
ทุกครั้งที่กด Render ซ้ำหรือเข้าโปรเจกต์เดิมมาเรนเดอร์ใหม่ คลิปในไทม์ไลน์จะยาวขึ้นเรื่อยๆ เกินความยาวเสียงจริง (เช่น `LOG01-สเปก_1` เสียงจริง 27.24s แต่คลิปบวมไปถึง 44.28s) เกิดจาก `video_assembly_stage.py` ไปบวก transition overlap (+0.25s ต่อรอยต่อ) เข้ากับ `clip["duration"]` และ `clip["trim_end"]` ซ้ำทุกครั้งที่เรนเดอร์ แล้วเซฟกลับลง `project.json`

**ผลลัพธ์:**
- แยกระหว่างคลิปที่เจนใหม่สด (`is_newly_generated_clips = True`) กับคลิปที่ส่งมาจาก Editor ใน `shot_matching_stage.py` / `video_assembly_stage.py`
- ป้องกันไม่ให้ `video_assembly_stage.py` ขยาย duration/trim_end ซ้ำกับคลิปที่มีอยู่แล้ว
- แก้ไขการคำนวณ `video_span` ใน `scripts/video_editor.py` ให้ใช้ `acc_dur` เพื่อคำนวณ `tail_gap` และ `tpad` ให้ตรงกับความยาวจริงหลัง xfade
- รัน `tools/repair_swollen_projects.py` เพื่อ normalize duration ของโปรเจกต์เดิมทั้งหมดใน `03_Projects/` กลับมาสอดคล้องกับ audio duration จริง
- Gate: `pytest tests/test_preview_render_parity.py` ผ่าน 149, `pytest tests/test_clip_compounding_render.py` ผ่าน 2, `pytest tests/test_transition_single_clip.py tests/test_phase1_smoke.py` ผ่าน 159


## Round HOK-1 — ระบบ Custom Hook Template Studio (สร้างและบันทึกแม่แบบฮุกด้วยตัวเอง)

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ผลลัพธ์:**
- **Custom Template Storage & CRUD Backend:**
  - สร้างไฟล์เก็บข้อมูล `02_Assets/Templates/custom_hook_templates.json` รองรับการเก็บสไตล์ฮุกส่วนตัว (font, size, colors, motion, layout, text tiers)
  - พัฒนาโมดูล `scripts/hook_styles.py` ให้มีฟังก์ชัน `load_custom_hook_templates()`, `save_custom_hook_template()`, `delete_custom_hook_template()` พร้อม atomic write
  - เพิ่ม API routes ใน `scripts/api_editor.py`: `GET /api/editor/hook-templates`, `POST /api/editor/hook-templates`, `DELETE /api/editor/hook-templates/{template_id}`
- **Frontend Sync & Dynamic Registration:**
  - เพิ่ม API client ใน `frontend/src/api.js`: `getHookTemplates()`, `saveCustomHookTemplate()`, `deleteCustomHookTemplate()`
  - อัปเดต `frontend/src/lib/hookStyles.js` ให้มีฟังก์ชัน `registerCustomHookTemplates()` รวมแม่แบบส่วนตัวเข้ากับ Built-in 8 รูปแบบแบบไร้รอยต่อ
- **Inspector & Quick Save UI:**
  - เพิ่มการ์ด "บันทึกเป็นสไตล์ของฉัน" ใน `OverlayInspector.jsx` พร้อมช่องกรอกชื่อและปุ่มบันทึก
  - เมื่อบันทึกสำเร็จ แม่แบบจะขึ้นในการ์ดเลือกสไตล์ทันที พร้อมกรอบสีนีออนไซเบอร์ `#25F4EE`, ป้ายชื่อ, แท็ก motion, และปุ่มถังขยะลบแม่แบบ
- **AssetPanel & Toolbar Integration:**
  - แถบ "ข้อความ" ใน `AssetPanel.jsx` แบ่งหมวดหมู่ชัดเจน: "แม่แบบของฉัน" และ "แม่แบบมาตรฐาน" พร้อมปุ่มลบ
  - เมนูดรอปดาวน์ `ฮุก:` บน Quick Toolbar ใน `Toolbar.jsx` แสดง `<optgroup label="🌟 แม่แบบของฉัน">` และ `<optgroup label="⚡ แม่แบบมาตรฐาน">` ซิงก์ข้อมูลอัตโนมัติ
- **Gates & Verification:**
  - `pytest tests/test_hook_templates_custom.py` ผ่าน 2/2 tests
  - `pytest tests/test_preview_render_parity.py` ผ่าน 149/149 tests
  - `python -m compileall -q scripts` ผ่าน
  - `npm test` ใน frontend ผ่าน 85/85 tests
  - `npm run build` ผ่านใน 3.22 วินาที
  - ทดสอบสดบนเบราว์เซอร์จริงผ่าน `browser_subagent` (บันทึกคลิป `hook_template_studio_1788801788848.webp`) สร้างแม่แบบ `Cyber Neon Pro` สำเร็จ แสดงผลใน Inspector, AssetPanel, และ Toolbar ครบถ้วน

## Round EDT-1 — ตรวจสอบและปรับปรุง UX/UI หน้าตัดต่อ (Editor Friction & Speed Optimization)

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ผลลัพธ์:**
- **Friction Audit:** ตรวจสอบหน้าตัดต่อบนเบราว์เซอร์จริงกับโปรเจกต์ `LOG01-ปัญหาหลังใช้_1` พบว่ากระบวนการตัดต่อ 1 คลิปเดิมใช้ 22–28 คลิก ปรับปรุงลดลงเหลือ 9–12 คลิก (ลดลงกว่า 55%)
- **Safe Zone 420px Parity & Guide:**
  - แก้ไขการคำนวณและเลย์เอาต์ Safe Zone ใน `SequencePlayer.jsx` จากเดิมที่ใช้ `top-[56.25%]` (ทำให้เส้นแดงพาดกลางสินค้า/จอ) เปลี่ยนเป็น:
    - พื้นที่อันตรายล่าง (Bottom Danger Zone): `bottom-0`, ความสูง `21.9%` (420px ของ 1920px) พร้อมเส้นประแดง `#FE2C55` และป้ายเตือน Safe Zone 420px ชัดเจน
    - พื้นที่อันตรายขวา (Right Action Icons Zone): ความกว้าง `11.1%` (120px ของ 1080px) พร้อม Ghost icons ของ TikTok
    - พื้นที่หัวคลิปบน (Top Margin): ความสูง `9.4%` (180px ของ 1920px)
    - กล่อง Safe Zone เขียวนีออนตรงกลางจอ สัดส่วนปลอดภัย 9:16
  - เพิ่มปุ่มลัด `Safe Zone` ใน Timeline Toolbar ทำงาน Sync สองทางกับปุ่มบน Preview Stage
- **Quick Action Toolbar:**
  - เพิ่มปุ่ม `รีเซ็ตซูม` (RotateCcw) ใน Toolbar: เมื่อคลิปถูกครอบตัดหรือซูม/เลื่อนตำแหน่ง ปุ่มจะไฮไลต์ และสามารถคลิก 1 ครั้งเพื่อคืนค่าซูม 100% และตำแหน่ง (x:0, y:0) ทันที (เดิมต้องเปิด Inspector และเลื่อนหา 3 sliders เสีย 5 คลิก)
  - เพิ่มตัวเลือก `สไตล์ฮุก` (Quick Hook Preset Dropdown) ใน Toolbar: มี 8 สไตล์ให้เลือกสลับทันที (Tech, Cute, Bold Pop, Plain, Clean, Flash Sale, Neon, Luxury) คลิกเลือกแล้วอัปเดตสไตล์บนคลิปทันที ไม่ต้องเปิดแถบ Inspector
- **Gates:**
  - `npm test` ใน frontend ผ่าน 85/85 tests
  - `npm run build` ผ่านใน 4.39 วินาที
  - `python -m compileall -q scripts` ผ่าน
  - `pytest tests/test_preview_render_parity.py` ผ่าน 149/149 tests
  - ทดสอบจริงบนเบราว์เซอร์ผ่าน `browser_subagent` บันทึกวิดีโอ `verify_fix_editor_ux_1788799770233.webp`

## Round RAW-1 — แก้เปลี่ยนชื่อคลิปดิบและจัดเลย์เอาต์ Raw Vault

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ผลลัพธ์:**

1. ถอดตัวเล่น preview ออกจากคลิปที่กำลังจะเปลี่ยนชื่อ และถอดซ้ำก่อนส่งคำขอ เพื่อคืน file handle ให้ Windows
2. เพิ่ม retry สำหรับ `WinError 32` และตอบ `409` พร้อมข้อความให้ปิด preview เมื่อ lock ยังอยู่
3. เปลี่ยนกลุ่มสินค้าเป็น responsive grid (เดสก์ท็อป 2–3 คอลัมน์, จอเล็ก 1 คอลัมน์) และให้ชั้นคลิปอิสระเต็มความกว้าง ลดพื้นที่ว่างจากกลุ่มที่มีคลิปน้อย
4. รักษา flow อัปโหลด, ผูกสินค้า, ลบ, เลือก, preview, ค้นหา และการ์ดเดิมทั้งหมด

### Gate

- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 896 passed
- [x] `python -m compileall -q scripts/api_videos.py`
- [x] `npm test` — 85 passed
- [x] `npm run build`
- [x] Impeccable layout detector — ไม่พบ findings

### Notes

- เพิ่ม `tests/test_api_videos_rename.py` ครอบคลุม retry lock และการตอบ conflict เมื่อ lock ค้าง

## Round POST-3.27 — ลดความซ้ำซ้อนปุ่มเปิด TikTok Studio ให้เหลือจุดเดียวใน Header

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**หลักฐานและคำสั่ง:** User แจ้งว่า "ซ้ำซ้อนมากมีหลายจุดมา ขอจุดเดียวพอครับ" พร้อมภาพถ่ายหน้าจอที่ชี้ให้เห็นปุ่มเปิด TikTok 3 จุดพร้อมกัน (Header, Tab 1 quick bar, Tab 2 launcher banner)

**ผลลัพธ์:**
1. รวมเหลือจุดเดียวใน **Header bar** (`#headerOpenTikTokBtn` "เปิด TikTok Studio") สไตล์ Cyber-Studio Pill พร้อมไอคอน External Link สะอาดตา มองเห็นและเข้าถึงได้ตลอดเวลาไม่ว่าจะอยู่แท็บใด
2. นำปุ่ม `#listOpenTikTokBtn` ออกจาก Tab 1 คืนค่าปุ่ม `#refreshBtn` เป็นปุ่มเต็มกว้าง (`.btn-refresh-full`) เรียบหรู ไม่เกะกะรายการคลิป
3. นำ `.tiktok-launcher-banner` และ `#openTikTokBtn` ออกจาก Tab 2 ให้เข้าสู่แผงคำสั่งหลักโดยตรง
4. ทำความสะอาด event listeners ใน `sidepanel.js` และ CSS selectors ที่ไม่ใช้งาน
5. อัปเดต assertion ใน `background.test.cjs` ยืนยันการมีอยู่เฉพาะปุ่ม Header ใน sidepanel และ Popup ใน popup window พร้อมตรวจจับว่าไม่มีปุ่มซ้ำซ้อน

### Todo

- [x] ปรับ `sidepanel.html`: เอา `#listOpenTikTokBtn` ใน Tab 1 ออก และคืนค่า `#refreshBtn` ให้สะอาดตา
- [x] ปรับ `sidepanel.html`: เอา `.tiktok-launcher-banner` และ `#openTikTokBtn` ใน Tab 2 ออก
- [x] เก็บกวาด CSS ที่เกี่ยวข้องใน `sidepanel.html`
- [x] ปรับ `sidepanel.js`: เอา listeners ของปุ่มที่ลบออก คงไว้เฉพาะ `#headerOpenTikTokBtn`
- [x] อัปเดต contract test ใน `background.test.cjs`
- [x] รัน Gate ตรวจสอบ (`node --check`, `node --test`) และถ่ายภาพ snapshot ตรวจความเรียบร้อย

### Gate

- [x] `node --check tiktok_autopost_extension/sidepanel.js` (ผ่าน)
- [x] `node --test tiktok_autopost_extension/background.test.cjs` (ผ่านครบ 13/13 tests)
- [x] ตรวจภาพ Sidepanel UI ทั้ง Tab 1 และ Tab 2 ไม่เหลือปุ่มซ้ำซ้อน ยืนยันผ่าน browser snapshot

## Round POST-3.26 — เพิ่มปุ่มเปิด/สลับแท็บอัปโหลด TikTok Studio ใน Extension

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** เพิ่มปุ่มเปิด/สลับแท็บอัปโหลด TikTok Studio (`https://www.tiktok.com/tiktokstudio/upload`) ที่เด่นชัดและกดใช้งานได้ทันทีใน Chrome Extension:
- มีปุ่ม Quick Launch ที่หัวตาราง Tab 1 (รายการคลิป) เคียงข้างปุ่มรีเฟรช ให้ผู้ใช้เปิดแท็บ TikTok Studio ได้ทันทีตั้งแต่เปิด Extension
- มีปุ่มเปิดหน้าอัปโหลดที่ชัดเจนใน Tab 2 (ขั้นตอนโพสต์) และ Header
- เพิ่มปุ่มใน `popup.html` ด้วย
- ปรับปรุงฟังก์ชัน `openTikTokUploadTab()` ให้ตรวจจับทั้ง `tiktokstudio/upload`, `creator-center/upload` และ `tiktokstudio` ถ้ามีเปิดอยู่แล้วให้ switch tab + focus window ทันที ถ้ายังไม่มีให้เปิดแท็บใหม่
- ปฏิบัติตามกฎ UI Clean Standard (ไม่มี emoji หรือ symbol ซ้ำซ้อน, ใช้ clean SVG) และไม่แตะขั้นตอน automation

### Todo

- [x] เพิ่มปุ่ม Quick Launch "เปิดหน้าอัปโหลด TikTok" ใน Tab 1 (`#panelList`) ใน `sidepanel.html`
- [x] ปรับปรุงการแสดงผลปุ่มเปิด TikTok ใน Header (`#headerOpenTikTokBtn`) และ Tab 2 (`#openTikTokBtn`) ให้เด่นชัดและใช้งานง่าย
- [x] ปรับปรุงฟังก์ชัน `openTikTokUploadTab()` ใน `sidepanel.js` ให้ค้นหาแท็บ TikTok ได้รอบด้าน (ทุก pattern) และสลับแท็บพร้อม focus window หรือเปิดใหม่หากยังไม่มี
- [x] เพิ่มปุ่มเปิด TikTok Studio ใน `popup.html` และเชื่อมต่อกับ `openTikTokUploadTab()` ใน `popup.js`
- [x] ทดสอบ syntax (`node --check`) และรัน test suite `background.test.cjs`

### Gate

- [x] `node --check tiktok_autopost_extension/sidepanel.js` (ผ่าน)
- [x] `node --check tiktok_autopost_extension/popup.js` (ผ่าน)
- [x] `node --test tiktok_autopost_extension/background.test.cjs` (13/13 ผ่าน)
- [x] UI ทดสอบแสดงผลปุ่มเปิดแท็บชัดเจน สวยงามตาม Cyber-Studio Dark ทั้งใน Tab 1, Tab 2, Header และ Popup

### Notes

- รักษากฎ `ui_clean_standard.md` ไม่ใส่ emoji หรือเครื่องหมายซ้ำซ้อน
- ไม่กระทบ logic automation 1-6

## Round POST-3.25 — Redesign Extension UX/UI (Cyber-Studio Dark & Stepper Timeline)

Date: 2026-09-07; Requested by: user; Status: complete

**Goal:** ปรับโฉม UX/UI ของ Chrome Extension (`sidepanel.html`, `sidepanel.js`, `popup.html`) สู่ระดับ Cyber-Studio Dark Glassmorphism, ลบ Emoji รกตาและใช้ Clean SVG Icons ทั้งหมดตามกฎ `ui_clean_standard.md`, ปรับ Checklist เป็น Interactive Stepper Timeline พร้อมฝังฟอนต์ `IBM Plex Sans Thai` โดยไม่แตะต้อง Logic และขั้นตอนการทำงานเดิม 100%

### Todo

- [x] ออกแบบ Design System ใน `sidepanel.html`: โทน Cyber-Studio Dark (`#070a11`, `#121828`, `#22d3ee`, `#34d399`, `#f43f5e`), backdrop blur, crisp micro-borders
- [x] ฝังฟอนต์ `IBM Plex Sans Thai` (Medium & Bold) เข้า `fonts/` โหลดผ่าน `@font-face`
- [x] เปลี่ยน Emoji ทั้งหมดในหัวข้อ, แท็บ, ปุ่ม, ป้าย, และสถานะ เป็น Clean inline SVG Icons (Lucide-style) ตามกฎ `ui_clean_standard.md`
- [x] พัฒนา Active Clip Studio Monitor: รวม 3:4 Preview Monitor, live aspect ratio badge, hook title, product badge, และเวลาโพสต์
- [x] ปรับโฉม Checklist 1-6 ให้เป็น Stepper Pipeline Command Center: เส้นเชื่อม vertical stepper, glowing node rings, badge แสดงสถานะ, hover/active tactile micro-interactions, แยก Danger style ให้ Step 6 เด่นชัด พร้อมหลอดนีออนความคืบหน้าเรียลไทม์
- [x] ปรับปรุง Section Cards, Input Textareas, Copy button, Schedule date/time selector และ Status notification ให้โมเดิร์น สบายตา
- [x] ตรวจสอบว่า DOM IDs, classes สำคัญ, และ String patterns ที่ `background.test.cjs` ตรวจสอบยังคงอยู่ครบถ้วน 100%
- [x] ปรับ `popup.html` ให้มีสไตล์ Cyber-Studio Dark สอดคล้องกัน

### Gate

- [x] `node --check tiktok_autopost_extension/sidepanel.js` และ `popup.js` — passed
- [x] `node --test tiktok_autopost_extension/background.test.cjs` — 12/12 passed
- [x] `python -m pytest tests/test_api_tiktok_autopost.py` — 11 passed
- [x] เปิดดู UI จริงผ่าน Browser ตรวจสอบความสวยงาม การแสดงผล ไม่มี overflow, responsive บน side panel width, และ contrast ratio

## Round POST-3.24 - indicate cover status in daily queue

Date: 2026-09-07; Requested by: user; Status: complete

**Goal:** Make the daily queue answer at a glance whether each scheduled clip already has a saved cover.

**Scope:** Reuse cover metadata from the queue item and its ready export; show the existing Cover Studio image action in a bright semantic state when a cover exists and a subdued state when it does not; preserve the preview, schedule controls, Extension handoff, and steps 1-5.

### Todo

- [x] Resolve cover presence from URL/path fields for the queue item and matched clip, including 3:4 and 9:16 variants.
- [x] Use a bright cover icon with a clear tooltip/accessible label for saved covers.
- [x] Use a subdued cover icon with a create-cover tooltip when no saved cover exists.
- [x] Keep the icon clickable for the existing Cover Studio flow whenever the ready clip is available.
- [x] Use the resolved cover for the row thumbnail so saved covers remain visible after queue refresh.

### Gate

- [x] `npm test` — 83 passed.
- [x] `npm run build` — passed.
- [x] `git diff --check` — passed.
- [x] Impeccable detector — completed; remaining warnings are existing file-wide color-pattern findings outside this narrow state change.
- [x] Browser smoke — live Agenda rendered two saved-cover rows with `data-cover-state="ready"`, bright icon styling, and the accessible label `มีภาพปกแล้ว คลิกเพื่อแก้ไข`.

### Notes

- The missing-cover branch is intentionally dark and keeps the title/ARIA text `ยังไม่มีภาพปก คลิกเพื่อสร้าง`.
- No backend, queue identity, schedule timestamp, Extension step, or frozen posting step was changed.
- Unrelated editor files and local schedule JSON artifacts remained unstaged.


## Round POST-3.23 - reduce default publishing slots to three

Date: 2026-09-07; Requested by: user; Status: complete (browser gate deferred)

**Goal:** Reduce the default weekly publishing schedule to three practical TikTok windows: 12:30, 19:00, and 21:30.

**Scope:** Update the frontend template editor and backend schedule defaults; migrate templates saved with the previous five-slot defaults; keep custom three-slot weekly overrides, queue records, Extension handoff, cover flow, and steps 1-4 unchanged.

### Todo

- [x] Change the shared frontend default slots to 12:30, 19:00, 21:30.
- [x] Change the backend default slots and validation to three unique five-minute slots.
- [x] Migrate legacy five-slot templates to the new three-slot defaults on read/save.
- [x] Resize the weekly template editor grid and helper text for three columns.
- [x] Add frontend and backend regression coverage for the new defaults and migration.
- [x] Run the full backend/frontend gates and inspect the isolated diff.

### Gate

- [x] `python -m pytest tests/test_schedule_queue.py -q -p no:cacheprovider --tb=short` — 9 passed.
- [x] `node --test frontend/src/lib/scheduleQueue.test.js` — 3 passed.
- [x] `python -m compileall -q scripts` — passed.
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 891 passed, 6 existing warnings.
- [x] `npm test` — 83 passed.
- [x] `npm run build` — passed.
- [ ] Browser verification — deferred; no browser runtime gate was available in this round.

### Notes

- Existing queue timestamps are untouched; only the reusable template defaults change.
- A saved five-slot legacy template is readable and normalised to the three new defaults instead of causing a validation failure.
- Custom weekly templates may still use three distinct times, so a later week can override the defaults without changing existing queue items.
- Unrelated editor and pipeline changes already present in the working tree were left unstaged.

## Round POST-3.22 - weekly schedule templates and product-rotating auto-fill

Date: 2026-09-07; Requested by: user; Status: complete (browser gate deferred; browser runtime was unavailable after automated smoke finalization)

**Goal:** Add reusable weekly time templates and an explicit auto-fill flow that appends ready clips to the durable multi-day queue while rotating products fairly.

**Scope:** Persist Monday-Sunday templates in the backend; support per-week overrides, enabled days, five primary times per day, previewed auto-fill for today/this week/custom ranges, product rotation, random clip selection, overdue reuse, and append-after-latest semantics. Keep existing queue records, Extension handoff, cover flow, steps 1-4, and editor work unchanged.

### Todo

- [x] Add backend template storage/API with default and week-specific Monday-Sunday schedules.
- [x] Add Agenda controls for weekly template editing, copying, resetting, enabled days, and saved week selection.
- [x] Add auto-fill preview for today, this week, or custom date range with optional clip limit and product filter.
- [x] Implement append-after-latest scheduling, skip past slots, preserve existing queue, and show empty-slot reasons.
- [x] Implement random product order with no adjacent product repeat across day boundaries and random clip choice within each product.
- [x] Mark overdue unposted rows and provide a reviewable requeue flow without duplicating MP4 identities.
- [x] Add deterministic tests for template persistence, week boundaries, append cursor, fairness, limits, overdue reuse, and collisions.
- [x] Run backend/frontend tests, build, syntax checks; browser verification deferred because the runtime was unavailable.

### Gate

- [x] Backend schedule template/auto-fill tests pass.
- [x] Frontend tests pass.
- [x] `npm run build` passes.
- [ ] Browser verification: deferred; browser runtime was unavailable after automated smoke finalization.

### Notes

- `pytest tests/ -q`: 879 passed, 6 warnings; `npm test`: 83 passed; `npm run build` and `python -m compileall -q scripts` passed.
- Browser UI gate was not rerun in this environment because the prior browser runtime had already finalized; API and component behavior are covered by deterministic tests/build.

- Week means Monday-Sunday in `Asia/Bangkok`; changing a template never mutates existing queue timestamps.
- Auto-fill uses only ready, unqueued, unposted exports, preserves the one-MP4-once rule, and requires explicit confirmation after preview.
- If a selected range has no future primary slot, the preview continues after the latest queue item into the next enabled day.
- Existing editor files remain another workstream and must not be modified or staged.
---

## Round TRK-3 — บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์หยิบทำวันนี้ & การ์ดตัดต่อเสร็จแนวนอนกะทัดรัด)

วันที่: 2026-09-06 · สั่งโดย: user (ผ่าน /grill-me) · สถานะ: เสร็จสิ้น

**เป้าหมาย:** แก้ปัญหาบอร์ดหลักยืดยาวและรกเมื่อมีคลิปและสคริปต์สะสม 20-30+ รายการ ตามมติการสัมภาษณ์ `/grill-me` (3 ข้อ):
1. คอลัมน์ "โพสต์แล้ว (Posted)": แสดงเฉพาะคลิปที่โพสต์วันนี้ (Today Only) เพื่อไม่ให้รกบอร์ด ส่วนคลิปเก่าในอดีตย้ายเข้าคลังประวัติอัตโนมัติ พร้อมปุ่มเปิดดูคลังประวัติ (Archive Modal)
2. คอลัมน์ "สคริปต์พร้อม (Scripted)": คลังสคริปต์ (Script Library Modal) เก็บไว้ด้านหลัง บนบอร์ดหลักแสดงเฉพาะ 3-5 สคริปต์ที่เราหยิบมาทำวันนี้ พร้อมปุ่มหยิบเข้า/ปลดออก
3. คอลัมน์ "ตัดต่อเสร็จ / ตรวจ QC (Rendered)": ปรับการ์ดเป็นการ์ดแนวนอนกะทัดรัด (Compact Horizontal Card สูง ~95px) ซ้ายเป็นมินิพรีวิว 9:16 ขวาเป็นชื่อสินค้า + QC ผ่าน + Hook 1 บรรทัด + แถบปุ่มแอ็กชันครบครัน (`ส่ง TikTok`, `มือถือ`, `QC`, `ตัดใหม่`)

**สิ่งที่แก้ไข:**
1. **TRK-3.1 คอลัมน์โพสต์แล้ว: Today-Only + Archive Modal**:
   - กรองรายการคลิปในคอลัมน์ `posted` ให้แสดงเฉพาะคลิปที่มี `posted_at` หรือ `updated_at` เป็นวันปัจจุบัน (Local Time `YYYY-MM-DD`)
   - คลิปที่โพสต์ก่อนหน้านี้ย้ายเข้าคลังประวัติอัตโนมัติ ไม่เปลืองพื้นที่บนบอร์ด
   - มีปุ่ม `[คลัง (N)]` บนหัวคอลัมน์ และปุ่ม `[คลังประวัติคลิปเก่า (N คลิป)]` เพื่อเปิดดู Modal ประวัติคลิปทั้งหมดในอดีต (ค้นหาได้, ดูพรีวิววิดีโอ, ก๊อปปี้แคปชัน, ส่ง TikTok ซ้ำได้)
   - อัปเดต `scripts/product_store.py` ให้บันทึกฟิลด์ `posted_at` เมื่อย้ายสถานะเป็น `posted`
2. **TRK-3.2 คอลัมน์สคริปต์พร้อม: คลังสคริปต์ (Script Library) + สคริปต์หยิบทำวันนี้**:
   - เพิ่ม State `pickedScriptIds` เก็บลง `localStorage` บันทึกสคริปต์ที่เลือกมาทำประจำวัน
   - คอลัมน์บนบอร์ดหลักแสดงเฉพาะสคริปต์ที่หยิบมาทำวันนี้ ทำให้บอร์ดไม่ยาวเฟื้อย
   - เพิ่มปุ่ม `[คลัง (N)]` บนหัวคอลัมน์ เปิด `ScriptLibraryModal` คลังสคริปต์ทั้งหมดเพื่อกดเลือก `[หยิบมาทำวันนี้]` หรือ `[อยู่ในคิววันนี้]` มีปุ่มลัด `[เลือก 4 รายการแรก]` และ `[ล้างคิว]`
   - การ์ดสคริปต์บนบอร์ดมีปุ่ม `[X]` ปลดออกจากคิววันนี้ส่งกลับเข้าคลังได้ทันที
3. **TRK-3.3 คอลัมน์ตัดต่อเสร็จ / ตรวจ QC: การ์ดแนวนอนกะทัดรัด (Compact Horizontal Card ~95px)**:
   - ปรับความสูงการ์ดจาก ~350px ลงเหลือเพียง ~95px
   - ด้านซ้าย: มินิพรีวิววิดีโอ 9:16 (52px) พร้อมปุ่ม Play เปิดดูตัวอย่าง
   - ด้านขวา: ชื่อสินค้า + ป้ายสถานะ `QC ผ่าน` + Hook 1 บรรทัด + แถบปุ่มคำสั่งแถวเดียว (`[ส่ง TikTok]`, `[มือถือ]`, `[QC]`, `[ตัดใหม่]`, `[โพสต์แล้ว]`)
   - สามารถจุคลิปตัดเสร็จได้ 5-10 คลิปในหน้าจอเดียวโดยไม่ต้องเลื่อนสกอร์ยาว
4. **ผลการทดสอบ (Gate)**:
   - `python -m compileall -q scripts` ผ่าน 100%
   - `pytest tests/ -q` ผ่าน 373/373 tests (7 warnings เก่า)
   - `npm run build` ผ่าน 100% ใน 4.06s
   - `npm test` ผ่าน 54/54 tests
   - ทดสอบจริงบนเบราว์เซอร์ผ่าน browser subagent และบันทึกภาพหน้าจอเรียบร้อย
   - ปฏิบัติตามกฎ `ui_clean_standard.md` ไม่มีสัญลักษณ์ซ้ำซ้อน

---

## Round TRK-2 — ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet) & จัดกลุ่มย่อการ์ด (Product Grouping / Quick Pills)

วันที่: 2026-09-06 · สั่งโดย: user (ผ่าน /grill-me + /scrutinize) · สถานะ: เสร็จสิ้น

**เป้าหมาย:** แก้ปัญหาการ์ดล้นจอเมื่อมีสคริปต์จำนวนมาก และรองรับ workflow โพสต์คลิปวันละ 3-5 คลิปแบบสลับสินค้าตามช่วงเวลา (เช้า A / เที่ยง B / เย็น C / ดึก D) โดยเพิ่มมุมมอง "คิวโพสต์ประจำวัน (Daily Run Sheet)" พร้อมระบบจัดคิวและสลับสินค้าอัตโนมัติ, ตั้งเวลาโพสต์ (Schedule Time), แถบ Quick Product Pills เลือกสินค้าเร็ว, Accordion Grouping ย่อการ์ดในบอร์ด 5 เฟส, และตัวกรองซ่อนคลิปที่โพสต์ไปแล้วเกิน 24 ชม.

**สิ่งที่แก้ไข:**

1. **TRK-2.1 แถบปุ่มลัดเลือกสินค้า (Quick Product Pills) & Accordion Grouping ในบอร์ด 5 เฟส**:
   - เพิ่มแถบ Pills สินค้าใต้ Search bar: `[สินค้าทั้งหมด]` `[Logitech Wave Keys]` `[ESSAGER]`... สลับกรองสินค้าได้ในคลิกเดียว ไม่ต้องเลื่อนหาใน Dropdown
   - เพิ่มโหมด Accordion Group by Product ในคอลัมน์ "สคริปต์พร้อม": พับ/กางตามชื่อสินค้าได้ ช่วยลดความยาวการ์ดจาก 20-30 ใบเหลือไม่กี่แถว
   - เพิ่มระบบ Truncate ในคอลัมน์ "โพสต์แล้ว": ซ่อนคลิปที่โพสต์แล้วเมื่อมีเกิน 3 รายการ พร้อมปุ่ม "+ ดูคลิปเก่าทั้งหมด"

2. **TRK-2.2 แท็บมุมมองใหม่ "คิวโพสต์ประจำวัน (Daily Run Sheet)"**:
   - เพิ่มปุ่มสลับมุมมองที่ Header: `[บอร์ด 5 เฟส]` | `[คิวประจำวัน]` | `[ตารางข้อมูล]`
   - โครงสร้าง 4 สล็อตมาตรฐานประจำวัน (เช้า 08:30 / เที่ยง 12:30 / เย็น 18:00 / ดึก 21:30) สามารถปรับตั้งเวลาได้อิสระ
   - ปุ่ม `[เพิ่มรอบพิเศษ]` รองรับคลิปที่ 5 ของวัน
   - เซฟสถานะคิวลง `localStorage` ตามวันที่อัตโนมัติ

3. **TRK-2.3 อัลกอริทึม "จัดคิวสลับสินค้าอัตโนมัติ (Auto-Rotate Products)"**:
   - ปุ่ม `[จัดคิวสลับสินค้าอัตโนมัติ]`: ดึงคลิปที่ตัดเสร็จมากระจายลง 4 สล็อตแบบ Round-Robin ไม่ให้สินค้าซ้ำกันติดๆ กัน
   - รองรับการคลิก `[สลับคลิป]` หรือ `[เลือกคลิปที่ตัดเสร็จ]` ด้วย Modal แสดงคลิปทั้งหมดให้เลือกหยอดลงสล็อต

4. **TRK-2.4 การส่งโพสต์และปักตะกร้าตรงจากสล็อตพร้อม Schedule Time**:
   - รองรับการระบุเวลา Schedule Time ทั้งใน Daily Run Sheet และ TikTok Modal
   - อัปเดต `scripts/api_tiktok_autopost.py` และ `frontend/src/api.js` และ `popup.js` รองรับ `schedule_time`
   - เพิ่ม unit test `tests/test_api_tiktok_autopost.py`

5. **ผลการทดสอบ (Gate)**:
   - `npm run build` ผ่าน 100%
   - `npm test` ผ่าน 54/54 tests
   - `python -m compileall -q scripts` ผ่าน 100%
   - `pytest tests/ -q` ผ่าน 373 passed (7 warnings)

---

## Round TRK-1 — เพิ่มปุ่มส่งคลิปไป TikTok Studio พร้อม Modal ตรวจสอบ/ปักตะกร้า ในหน้า Tracker (ContentTrackerHub)

วันที่: 2026-09-06 · สั่งโดย: user (ผ่าน /grill-me) · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ในหน้า Tracker (`ContentTrackerHub.jsx`) เพิ่มปุ่ม "ส่ง TikTok" บนการ์ดในเฟส 3 "ตัดต่อเสร็จ / ตรวจ QC" คู่กับปุ่ม "ส่งมือถือ" พร้อมหน้าต่าง Modal สำหรับพรีวิวคลิป ตรวจทาน/แก้ไขแคปชั่น, แฮชแท็ก, และ TikTok Product ID ก่อนส่งข้อมูลไปยัง Extension และเปิด TikTok Studio

**สิ่งที่แก้ไข:**

1. **TRK-1.1 ปรับเลย์เอาต์การ์ด Kanban ในเฟส `rendered` (ตัดต่อเสร็จ) และ `mobile_ready`**:
   - ปรับเลย์เอาต์การ์ด Kanban ในเฟส `rendered` เป็น 2 แถวสมดุล สวยงาม สะอาดตา:
     - แถวบน (Publishing channels):
       - ปุ่ม `[ส่ง TikTok]` (ไล่เฉด TikTok `#FE2C55` / `#25F4EE`) พร้อมไอคอน `<Rocket />` สำหรับเปิด Modal เตรียมโพสต์
       - ปุ่ม `[ส่งมือถือ]` (สีม่วง) พร้อมไอคอน `<Smartphone />` สำหรับเปิด QR Code
     - แถวล่าง (QC & Editing tools):
       - ปุ่ม `[ตรวจ QC]` สำหรับเปิดดูพรีวิววิดีโอ
       - ปุ่ม `[ตัดใหม่]` สำหรับส่งกลับไปตัดต่อใหม่
     - แถบยืนยัน: ปุ่ม `[มาร์กว่าโพสต์แล้ว]` ย้ายลงมาเป็นปุ่มยืนยันปิดงาน
   - เพิ่มปุ่ม `[ส่ง TikTok]` ในเฟส `mobile_ready`, ตาราง Mobile/Desktop View ด้วย

2. **TRK-1.2 สร้าง Modal "เตรียมโพสต์ TikTok Studio (พร้อมปักตะกร้า)"**:
   - เพิ่มหน้าต่าง Modal แบบ Interactive รองรับ:
     - พรีวิวคลิปวิดีโอ 9:16 แบบฝังในหน้าต่าง พร้อมตัวเล่นวิดีโอ
     - ช่องแก้ไข "คำอธิบายคลิป (Caption)" ดึงค่าอัตโนมัติจาก angle
     - ช่องแก้ไข "แฮชแท็ก (Hashtags)" ดึงค่าอัตโนมัติจาก angle
     - ช่องแก้ไข "รหัสสินค้าปักตะกร้า (TikTok Product ID / Search Keyword)" ดึงค่าจาก parent product หรือใช้ชื่อสินค้าเป็น fallback
     - สรุป Checklist ความพร้อม: วิดีโอพร้อมอัปโหลด, แคปชั่น & แฮชแท็ก, และสถานะการปักตะกร้า
     - ปุ่ม Action: `[ส่งข้อมูลเข้า Extension & เปิด TikTok Studio]` ทำการบันทึกข้อมูลเข้า extension ผ่าน `prepareTiktokAutopost` และเปิดหน้า TikTok Studio upload ทันที
     - ปุ่มยืนยัน `[มาร์กว่าโพสต์แล้ว]` เพื่ออัปเดตสถานะเป็น `posted` เมื่อยืนยันว่าโพสต์บน TikTok สำเร็จ

3. **TRK-1.3 เพิ่มปุ่มส่ง TikTok ใน Inspect Modal (Deep-Dive Modal)**:
   - เพิ่มปุ่ม `[ส่ง TikTok]` ในแถบ Action Toolbar ด้านบนของ Inspect Modal ให้สามารถคลิกส่งโพสต์ได้โดยตรงจากหน้าต่างดูรายละเอียดเชิงลึก

4. **ผลการทดสอบ (Gate)**:
   - `npm run build` ผ่าน 100% (0 error)
   - `npm test` ผ่าน 54/54 tests
   - `python -m compileall -q scripts` ผ่าน 100%
   - `pytest tests/ -q` ผ่าน 372 passed (7 warnings)

---

## Round PROD-1 — เพิ่มช่องระบุ TikTok Product ID ตอนสร้างสคริปต์ใหม่ + Fallback ค้นหาด้วยชื่อสินค้า + Click-to-Edit Cart ID

วันที่: 2026-09-06 · สั่งโดย: user · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ในหน้าต่างโมดอลสร้างสินค้า/สคริปต์ใหม่ (`ProductToClip.jsx`) เพิ่มช่องให้ระบุ "ไอดีสินค้า (TikTok Product ID)" สำหรับปักตะกร้า เพื่อให้ระบบบันทึกและส่งต่อไปยังขั้นตอนปักตะกร้าสินค้าอัตโนมัติ โดยใช้ไอดีเป็นหลัก หากไม่ระบุให้สำรองเป็นชื่อสินค้าเพื่อค้นหาให้ตรงที่สุด พร้อมรองรับการแก้ไข/ใส่ไอดีหรือลิงก์แชร์ย้อนหลังได้จาก Header สินค้าปัจจุบัน และมีผลกับทุกสคริปต์ในชุดนั้นทันที

**สิ่งที่แก้ไข:**

1. **PROD-1.1 Frontend Modal (`ProductToClip.jsx`)**:
   - เพิ่ม state `tiktokProductId` ใน `ProductToClip.jsx`
   - เพิ่มช่อง Input: "ไอดีสินค้าสำหรับปักตะกร้า (TikTok Product ID):" วางในโมดอลสร้างสินค้า/สคริปต์ใหม่ รองรับทุกโหมด พร้อมระบบตรวจจับและดึง ID จาก URL อัตโนมัติ
   - ส่ง `tiktok_product_id` ไปกับ payload ของ `scrapeAndPlanProduct` และ `scrapeAndPlanProductAsync`
   - ล้างค่าเมื่อส่งหรือปิดโมดอล

2. **PROD-1.2 Backend API & Store (`api_products.py` & `product_store.py`)**:
   - ใน `scrape_and_plan` และ `_execute_scrape_and_plan_worker`: รับ `tiktok_product_id` จาก payload
   - อัปเดต `ProductStore.add(...)` ให้รองรับ parameter `tiktok_product_id` และบันทึกลงในสินค้า
   - เพิ่ม endpoint `POST /api/products/resolve-tiktok-id` และฟังก์ชัน `resolve_tiktok_product_id` รองรับการแกะ ID จาก URL หรือแกะ redirect ของ shortlink (`vt.tiktok.com`)

3. **PROD-1.3 Fallback logic: ไอดีก่อนเป็นหลัก สำรองเป็นชื่อสินค้า**:
   - ใน `scripts/api_exports.py`: ให้ `info["tiktok_product_id"] = matched_prod.get("tiktok_product_id") or matched_prod.get("name", "")`
   - ใน `frontend/src/components/ContentTrackerHub.jsx`: อนุญาตให้ปุ่มเตรียมปักตะกร้าทำงานได้แม้ไม่มีตัวเลข ID โดยใช้ชื่อสินค้าเป็น fallback

4. **PROD-1.4 Click-to-Edit Cart ID ย้อนหลัง & Auto-resolve Shortlinks**:
   - ใน `ProductToClip.jsx`: ปรับ Badge ตะกร้าที่หัวสินค้า `[ID: ...]` / `[ปักตะกร้าด้วยชื่อ]` ให้ใช้ไอคอน Lucide `<ShoppingBag />` (ตาม Clean UI) และสามารถคลิกเพื่อเปิด Modal แก้ไข/ใส่ไอดีสินค้าภายหลังได้
   - Modal แก้ไขไอดีสินค้า: ระบุชัดเจนว่าไอดีนี้จะแนบกับทุกสคริปต์ในชุดนี้ ({angles.length} สคริปต์) รองรับการกรอกเลขตรงๆ หรือวางลิงก์แชร์ (`vt.tiktok.com`) พร้อม auto-resolve และปุ่มล้างค่า
   - ในฟอร์มสร้างสินค้าใหม่: รองรับการวางลิงก์แชร์ลงในช่อง TikTok Product ID หรือช่องลิงก์สินค้า แล้ว auto-resolve ผ่าน `resolveTiktokProductId`

**ผลการทดสอบ (Gate):**
- `npm run build` ผ่าน (3.26s)
- `npm test` ผ่าน 54 tests (0 failures)
- `python -m compileall -q scripts` ผ่าน
- `pytest tests/ -q` ผ่าน 372 passed (7 warnings)

---

## Round BUG-3 — angle ชนกัน (คลิปผิดสคริปต์) ใน Content Tracker Hub + ปุ่มปักตะกร้า TikTok

วันที่: 2026-09-06 · สั่งโดย: user (แนบภาพหน้า Content Tracker Hub) · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ปิดช่องโหว่ที่ 2 angle คนละสคริปต์ชี้ไปคลิปเดียวกันได้ (ข้อมูลจริงพัง ณ ตอนนั้น),
ปิดช่องโหว่ที่ลบคลิปจาก gallery แล้ว Tracker ไม่รู้ตัว, และเพิ่มปุ่มส่ง TikTok ปักตะกร้าตรงจากหน้านี้

**สืบสวนแล้ว (/scrutinize, ยืนยันด้วยข้อมูลจริงใน `_Docs/products.json` ไม่ใช่เดา):**
- ContentTrackerHub ทั้ง 3 จุดที่โชว์วิดีโอ (kanban card, compact card, inspect modal) อ่าน `ang.video_url`
  ตรงๆ ไม่มี matching logic ฝั่ง frontend เลย → บั๊กร้อยเปอร์เซ็นต์อยู่ backend/data
- **หลักฐานจริง:** `pain_point` กับ `unboxing` (Logitech Wave Keys) มี `project_name` + `video_url` **ตรงกันเป๊ะ**
  ทั้งที่ `unboxing` ไม่มีโฟลเดอร์ของตัวเองใน `03_Projects/` เลย — วิดีโอที่ unboxing โชว์คือของ pain_point จริง
- **ต้นตอ:** `reconcile_existing_projects()` วนลูป angle ทุกตัวต่อ 1 โฟลเดอร์โปรเจกต์ **ไม่มี `break`** —
  ถ้า 2 angle เข้าเงื่อนไข `angle.project_name == p_folder.name` (self-referential) พร้อมกัน จะได้ `video_url`
  เดียวกันทั้งคู่ ทุกรอบ reconcile ยืนยันซ้ำบั๊กเดิมเอง (self-perpetuating) — ต้นตอที่ผิดตั้งแต่แรกหาไม่ได้ 100%
  (ไม่มี log ประวัติ) แต่ไม่กระทบการแก้: ต้องปิดช่องโหว่ที่โครงสร้างไม่ว่าจะมาจากไหน
- `delete_file()` เรียก `rollback_by_video_or_project()` จริง แต่ทำงานเฉพาะ `status in ("rendered", "in_production")`
  — ถ้า angle ไปถึง `mobile_ready`/`posted` แล้ว ลบไฟล์ไม่ทำอะไรเลย

**ตัดสินใจ (grill กับ user 2026-09-06):** ชนกัน → auto-แก้ตัวที่แพ้กลับเป็น `scripted` + ขึ้นเตือนถาวรบนการ์ด
(ไม่ใช่ toast ที่พลาดดูได้) · แก้ข้อมูลจริงที่ชนอยู่ตอนนั้นทันที · rollback ใช้กับทุก status เหมือนกันหมด ·
เพิ่มช่องตั้งค่า `tiktok_product_id` ต่อสินค้าคู่กับปุ่มปักตะกร้า (เดิมมีแค่ ESSAGER ที่ตั้งด้วยมือใน products.json ตรงๆ)

**สิ่งที่แก้ไข:**

1. **BUG-3.1 — ปิดช่องโหว่ reconcile จับ 2 angle ชนกัน:**
   - `reconcile_existing_projects()` ([product_store.py:473+](scripts/product_store.py#L473)) แยก
     `authoritative_match` (เงื่อนไข #1: exact product_id+angle_id จาก manifest ของโปรเจกต์เอง — ชนะเสมอ)
     กับ `self_ref_matches` (เงื่อนไข #2: self-referential) ก่อนอัปเดตอะไร ผู้ชนะมีได้แค่ 1 ต่อ 1 โฟลเดอร์ต่อรอบ
     ทุก `self_ref_matches` ที่ไม่ใช่ผู้ชนะโดน unlink กลับเป็น `scripted` พร้อมเซ็ต `angle["data_conflict_note"]`
   - `ContentTrackerHub.jsx` เพิ่ม banner เหลือง (mirror `qc_note` banner) ทั้งใน `KanbanCard` และ inspect modal
     พร้อมปุ่ม "เข้าใจแล้ว" → `handleDismissConflict` เรียก `update_angle_status(..., clear_conflict_note=True)`
     (field ใหม่นี้เพิ่มเข้า `update_angle_status`/PATCH endpoint/`api.js` ครบ)
   - **รันซ่อมข้อมูลจริงแล้ว:** เรียก `reconcile_existing_projects()` เวอร์ชันใหม่กับ real `_Docs/products.json`
     (backup ไว้ที่ scratchpad ก่อน) — `unboxing` หลุดจาก `pain_point`'s folder กลับเป็น `scripted` +
     มี `data_conflict_note`, `pain_point` ไม่กระทบ — สแกนทั้งไฟล์ยืนยันไม่มี `video_url` ซ้ำที่ไหนอีกเลย
   - เทส `tests/test_reconcile_angle_collision.py` (2 เคส) — ไล่ตรรกะโค้ดเดิมด้วยมือยืนยันว่าทั้ง 2 เคส
     จะ fail ถ้าไม่มี fix นี้ — 2 passed

2. **BUG-3.2 — ลบคลิปจาก gallery ต้องเคลียร์ Tracker ด้วยทุกสถานะ:**
   - `rollback_by_video_or_project()` ([product_store.py:222](scripts/product_store.py#L222)) เอาเงื่อนไข
     `status in ("rendered", "in_production")` ออก ทำงานกับทุก status รวม `mobile_ready`/`posted`
   - เทส `tests/test_rollback_all_statuses.py` — parametrize 4 status × มี/ไม่มีโฟลเดอร์โปรเจกต์เหลืออยู่ — 6 passed

3. **BUG-3.3 — ปุ่มส่ง TikTok ปักตะกร้าใน Content Tracker Hub:**
   - เพิ่ม `tiktok_product_id` เข้า `ProductUpdateRequest` ([api_phase1.py:225](scripts/api_phase1.py#L225))
     — `ProductStore.update()` เดิมรับ kwarg ไม่รู้จักอยู่แล้ว ไม่ต้องแก้ store เพิ่ม
   - เพิ่มช่อง input `tiktok_product_id` ต่อสินค้า + ปุ่ม "บันทึก" + ปุ่ม "ส่ง TikTok ปักตะกร้า" ใน inspect modal
     ([:1014+](frontend/src/components/ContentTrackerHub.jsx#L1014)) — เรียก `prepareTiktokAutopost(...)`
     ตัวเดียวกับ ExportGallery ส่ง `product_id`/`angle_id`/`tiktok_product_id` จริง ปิดปุ่มถ้าไม่มี
     `tiktok_product_id` หรือยังไม่มี `video_url`
   - เทส `tests/test_bug3_tiktok_product_id_and_conflict_clear.py` — ยิงผ่าน `TestClient` จริง — 2 passed

**Gate:**
- `pytest tests/ -q -p no:cacheprovider` → 367 passed (รวมเทสใหม่ 10 เคส)
- `npx vite build` → ผ่าน · `python -m compileall -q scripts` → ผ่าน · routes = 84
- ข้อมูลจริง: `unboxing` ไม่ชนกับ `pain_point` อีกต่อไป — ยืนยันด้วยสคริปต์อ่าน `_Docs/products.json` จริงหลัง
  reconcile รันจริงแล้ว + สแกนทั้งไฟล์ไม่พบ `video_url` ซ้ำที่ไหนอีกเลย
- เช็คขนาน: ไฟล์ที่แก้ในรอบนี้ (`product_store.py`, `api_phase1.py`, `ContentTrackerHub.jsx`) ไม่ชนกับ
  POST-1/POST-2 ที่กำลังทำขนานอยู่เลย

---

## Round BUG-2 — แก้ข้อความและ Hook Header ซ้อนทับกันเป็นก้อนใน SequencePlayer

วันที่: 2026-09-05 · สั่งโดย: user (แนบรูปภาพบั๊กตัวอักษรซ้อนกัน) · สถานะ: เสร็จสิ้น

**สาเหตุรากเหง้า (Root Cause):**
1. `SequencePlayer.jsx` ยิงขอ `overlay.layout` ให้ Hook Header (`overlay.kind === 'hook'`) รวม 3 tiers เป็นสตริงเดียวด้วยขนาดฟอนต์ของ Brand
2. `lineWords && lineWords.length > 0` ทำงานแบบ unconditional แม้ `wordStaggerSec == 0` หรือเป็น Hook Header ทำให้บายพาสการวาด monolithic ปกติ
3. `word_layout.py` ใช้ `scaled_fs = font_size_px * ass_glyph_scale` ทำให้คำนวณตำแหน่ง `x` บีบแคบลง 37% (สำหรับ Kanit) แต่ฝั่ง Canvas วาดด้วยฟอนต์ 100% ตัวอักษรเลยชนและซ้อนทับกันเละ

**สิ่งที่แก้ไข:**
1. ใน `frontend/src/components/SequencePlayer.jsx`:
   - ป้องกัน Hook Header (`overlay.kind === 'hook'`) ไม่ให้ขอหรือใช้ `overlay.layout` โดยเด็ดขาด
   - สั่งล้าง `overlay.layout` เก่าทันทีถ้าเป็น Hook Header
   - กำหนด `isWordStagger = !isHook && wordStaggerSec > 0`
   - ให้ `lineWords` ทำงานเฉพาะเมื่อ `isWordStagger` เท่านั้น
   - กรณีปกติและ Hook Header ทั้งหมดวิ่งเข้า monolithic drawing (`drawTextWithMonoEmoji(ctx, w.line, lineX, lineY)`) ตัวอักษรและสระไทยทุกระดับเรียงตัวสวยงาม คมชัด 100% ไม่ชนกัน
2. ใน `tests/test_preview_render_parity.py`:
   - เพิ่ม contract test `test_hook_overlay_guarded_against_per_word_layout` เพื่อการันตีว่า Hook Header จะไม่ถูกแบ่งคำหรือขอ word layout อีกต่อไป

**Gate:**
- `python -m compileall -q scripts` → ผ่าน
- `python -c "import scripts.api_server as app; print(len(app.app.routes))"` → 84 routes
- `pytest tests/test_preview_render_parity.py -q` → 149 passed
- `pytest tests/ -q -p no:cacheprovider` → 356 passed
- `npm run build` (Vite) → built in 3.32s
- `node --test frontend/src/lib/*.test.js` → 6 passed

---

## Round 7 — template v2 + แกลเลอรีที่ขยับได้

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ยกระดับเทมเพลตข้อความให้มี motion personality ครบวงจร (Template v2) พร้อมสร้าง Animated Template Gallery ใน Inspector ที่แสดงการเคลื่อนไหวจริง (Micro-animation) ให้ผู้ใช้เห็นภาพก่อนเลือก ปลดล็อกป้ายฮุกและข้อความระดับไวรัล CapCut ทั้งใน Renderer และ Preview 100%

### Todo

- [x] Template v2 Models & Motion Presets:
  - เพิ่ม template ใหม่ใน `HOOK_TEMPLATES` ทั้งฝั่ง `scripts/hook_styles.py` และ `frontend/src/lib/hookStyles.js`:
    - `flash_sale` (โปรไฟลุก — แดงสด ป้ายส้มเหลืองสะดุดตา): Kanit, แดงสดตัดเหลือง ขอบหนาป้ายแดง, motion: pop + flicker + slide + badge + stagger
    - `neon_cyber` (นีออน — ฟ้าไซเบอร์ ขอบมืดเรืองแสง): Chakra Petch, ฟ้านีออน Glow ขอบดำ, motion: pop_zoom + wave + glitch + underline + stagger
    - `minimal_luxury` (ลักชัวรี — ทองขาว คมชัด สไตล์แบรนด์เนม): Prompt, ขาว/ทอง ขอบบางเรียบหรู, motion: quick_fade + lightsweep + fade + underline + stagger
  - กำหนด signature motion preset ประจำแต่ละ template ครบทั้ง 8 templates ใน `HOOK_TEMPLATES` (`motion: { in, loop, out, accent, stagger }`)
  - รองรับการ sync เมื่อเลือก template: `withHookTemplate` และ `withHookTemplateReset` นำ template motion ไปใส่ใน `overlay.anim`
  - รองรับ `motion` ใน `resolve_hook_style` (Python) และ `resolveHookStyle` (JS) ให้ได้ dict เดียวกันแบบ parity 100%
- [x] Animated Template Gallery (แกลเลอรีที่ขยับได้ใน Inspector):
  - ปรับปรุง UI แกลเลอรีสไตล์ใน `frontend/src/components/editor/inspector/OverlayInspector.jsx`:
    - แทนที่ปุ่มข้อความแบบเดิมด้วยการ์ด Template Preview เกรดโปร (Dark Card + Glow Border + Font tag + Motion badge)
    - แสดงภาพจำลอง 3 ชั้น (Brand, Model, Label) พร้อมสี, ฟอนต์, outline และ pill badge จริงผ่าน `TextLookPreview`
    - ใส่ CSS Micro-animations ใน `frontend/src/index.css` (`templatePulse`, `templateWave`, `templateShake`, `templateFlicker`, `templateLightsweep`, `templatePopZoom`)
    - รองรับ Interactive Hover: เมื่อเอาเมาส์ชี้ การ์ดจะเล่น motion preview ทันที
  - ยกระดับ Text Template Preview ใน `AssetPanel.jsx`:
    - แสดง motion badge พร้อม micro-animation preview ตอน hover สำหรับ Hook templates
    - เพิ่ม 3 templates ใหม่ลงใน `TEXT_TEMPLATES`: `tpl_hook_flash_sale`, `tpl_hook_neon_cyber`, `tpl_hook_minimal_luxury`
  - ยกระดับ Text Overlay Preset Styles ใน Inspector:
    - เพิ่ม micro-animation scale และ glow shadow เมื่อ hover
- [x] Automated Tests & Verification:
  - Parity test `test_hook_templates_are_identical_on_both_sides` และ `test_both_resolvers_agree_on_templates_overrides_and_colours` ตรวจสอบทั้ง 8 templates และ motion preset
  - Multi-frame FFmpeg behavioral render test `test_new_hook_templates_render_with_ffmpeg` ใน `tests/test_preview_render_behavior.py` ยืนยันการเรนเดอร์ template ใหม่ทั้ง 3 ตัวด้วย FFmpeg
  - Pass all gates: compileall, 78+ routes, pytest 356 passed, npm test 54 passed, npm run build passed

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน 0 error
- [x] `python -c "import scripts.api_server as app; print(len(app.app.routes))"` — 80 routes
- [x] `python -m pytest tests/ -q -p no:cacheprovider` — 356 passed, 0 failed
- [x] `npm test` — 54 passed, 0 failed
- [x] `npm run build` — ผ่านฉลุย 0 warning (built in 3.18s)
- [x] FFmpeg behavioral render ดึงเฟรมตรวจสอบ visual output ของ template v2 (`test_new_hook_templates_render_with_ffmpeg` ผ่าน 100%)

### Notes

- การรวม motion preset เข้ากับแต่ละ template ทำให้การสลับลุคเพียงคลิกเดียวได้ทั้ง typography hierarchy และ dynamic motion behavior ที่เข้ากันโดยอัตโนมัติ
- สไตล์แอนิเมชัน CSS ฝั่ง preview มี timing และ easing สอดคล้องกับพฤติกรรมของ FFmpeg/libass ASS tags ตามหลัก Preview = Render Parity

---

## Round 6 — ช่องใหม่ที่ mirror ได้เป๊ะ (Full Motion Pipeline + Tier A Skew)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** เชื่อมต่อช่อง Animation ที่เหลือ (`loop`, `out`) ให้ Text Overlay ทำงานได้เต็มรูปเหมือน Hook Header ทั้งใน Renderer (libass) และ Preview (Canvas 2D) พร้อมเพิ่มช่องสไตล์ Tier A `skew` (`\fax`) สำหรับข้อความเอียงที่ไม่มีผลกระทบต่อ layout advance และต่อ UI Inspector ให้ผู้ใช้ปรับแต่งได้อย่างสมบูรณ์

### Todo

- [x] Model channels:
  - เพิ่ม `skew` (float, default 0.0) ใน `TEXT_LOOK_FIELDS` และ `DEFAULT_TEXT_LOOK` ทั้งใน `scripts/overlay_model.py` และ `frontend/src/lib/overlayModel.js`
  - ตรวจสอบ `DEFAULT_ANIM` และ contract ให้มี parity 100%
- [x] Backend ASS writer (`scripts/subtitle/overlay_events.py`):
  - ใน `_text_overlay_events`:
    - อ่าน `loop` จาก `anim` (default `none`) และเรียก `loop_builder(max_entry_end_ms, exit_start_ms)`
    - อ่าน `out` จาก `anim` (default `fade`) และเรียก `out_builder(exit_start_ms, exit_end_ms, target_scale)`
    - ผูก `loop_tag` และ `out_tag` (รวมถึง `move_dy_out` สำหรับ `slide` out) เข้ากับ main text และ shadow layers
    - รองรับ `loop == 'lightsweep'` สำหรับ text overlay
    - รองรับ `look.get("skew")`: ถ้ามีค่า skew ให้ใส่ `\fax{skew:.2f}` ลงในแท็ก ASS
- [x] Frontend Canvas mirror (`frontend/src/components/SequencePlayer.jsx`):
  - ใน `drawOneOverlay`:
    - ยืนยันการผสาน `loopFx` และ `outFx` ให้ครบทุก preset สำหรับ text overlay ทั้งระดับคำและระดับบรรทัด
    - รองรับ `w.look.skew`: ทำ affine skew ผ่าน `ctx.transform(1, 0, w.look.skew, 1, 0, 0)` รอบจุดกึ่งกลางคำ/บรรทัด
    - รองรับ skew ใน lightsweep highlight pass
- [x] UI Inspector (`frontend/src/components/editor/inspector/OverlayInspector.jsx`):
  - เพิ่มตัวเลือกแอนิเมชันตอนค้าง (Loop Animation): None, Pulse, Wave, Shake, Flicker, Light Sweep
  - เพิ่มตัวเลือกแอนิเมชันตอนออก (Out Animation): Fade, Slide, Zoom, Glitch, Cut
  - เพิ่มตัวเลือกความเร็วการทยอยเข้าของคำ (Word Stagger): 0ms (พร้อมกัน), 50ms (เร็ว), 70ms (ปานกลาง), 100ms (ช้า)
  - เชื่อมปุ่ม "I" (Italic) ให้สลับค่า `skew` (0.0 <-> -0.25) เพื่อให้ข้อความเอียงจริงทั้งในพรีวิวและเรนเดอร์
- [x] Automated tests & behavioral validation:
  - Parity test ใน `tests/test_preview_render_parity.py` ยืนยัน `TEXT_LOOK_FIELDS` และ `DEFAULT_TEXT_LOOK`
  - Contract test ยืนยัน ASS tags สำหรับ `loop`, `out`, และ `\fax` (`test_text_overlay_events_wires_loop_out_and_skew`)
  - Multi-frame FFmpeg behavioral render test ยืนยัน visual output ของ `loop` (pulse), `out` (slide), และ `skew` (`\fax-0.25`)
  - Zero-regression test สำหรับ overlay ที่ใช้ค่า default

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน 0 error
- [x] `python -c "import scripts.api_server as app; print(len(app.app.routes))"` — 78 routes
- [x] `python -m pytest tests/ -q -p no:cacheprovider` — 351 passed, 0 failed
- [x] `npm test` — 54 passed, 0 failed
- [x] `npm run build` — ผ่านฉลุย 0 warning (built in 3.38s)
- [x] FFmpeg behavioral render ดึงเฟรมตรวจสอบ:
  - Skew: `\fax-0.25` ให้ forward italic slant โดย top pixels เลื่อนขวามากกว่า bottom pixels เมื่อเทียบกับ straight text (`d_top - d_bot = +6.68px`)
  - Loop pulse: hold phase มี alpha modulation ชัดเจน (`diff_pixels > 50`)
  - Out slide: exit phase เลื่อนลงด้านล่างตามแกน Y อย่างถูกต้อง (`exit_y > hold_y + 5.0px`)

### Notes

- การใช้ affine shear `\fax` ใน libass และ `ctx.transform(1, 0, skew, 1, 0, 0)` ใน Canvas 2D ช่วยแก้ปัญหาการขาดแคลน native italic font cut ของฟอนต์ไทยบน Google Fonts (Kanit, Prompt, Chakra Petch) ได้อย่างสมบูรณ์แบบ
- การทำ shear รอบจุดกึ่งกลางคำ/บรรทัดไม่กระทบต่อ layout advance width หรือ word bounding measurement ใดๆ ทำให้ zero-regression invariant ยังคงอยู่อย่างสมบูรณ์

---

## Round 5 — per-word animation (คำทยอยเข้าทีละคำ)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ทำ Animation ให้ข้อความทยอยเข้าทีละคำ (Word Stagger Animation) โดยใช้พิกัดจาก Word Layout Engine ของ Round 4 เพื่อให้ทั้ง Preview (Canvas 2D) และ Render (libass) แสดงผลการทยอยเข้าของคำด้วยจังหวะเวลา (Timing) และทรานส์ฟอร์มเดียวกัน 100%

### Todo

- [x] `anim.word_stagger_ms`: เพิ่มช่องพารามิเตอร์ `word_stagger_ms` ใน overlay model (`anim`) ค่าเริ่มต้น ~60-80ms สำหรับ per-word animation (default 0)
- [x] Backend ASS writer (`scripts/subtitle/overlay_events.py`):
  - ใน `_text_overlay_events` เมื่อมี `word_stagger_ms > 0`:
  - คำนวณ `t_word_in = word_idx * word_stagger_ms`
  - ก่อน `t_word_in` คำจะซ่อนอยู่ (`\alpha&HFF&`)
  - เมื่อถึง `t_word_in` คำจะเริ่มเล่น in-animation ตาม preset (`snap`, `pop_zoom`, `stamp`, `quick_fade`, `rise`, `none`)
  - กำหนด transform origin `\org(w_cx, w_cy)` ต่อคำเพื่อให้ scale และ rotate รอบจุดกึ่งกลางคำของตัวเอง
  - Duplicate shadow events ให้มี timing ตรงกับ main text ของคำนั้นๆ
  - ถ้า `word_stagger_ms == 0` หรือไม่ระบุ ให้รักษารูปแบบพร้อมกันทุกคำ (เหมือน Round 4 เป๊ะ)
- [x] Frontend Canvas mirror (`frontend/src/components/SequencePlayer.jsx`):
  - ใน `drawOneOverlay` อ่าน `motion.word_stagger_ms` และคำนวณ `wordStaggerSec`
  - ใน word drawing loop คำนวณ `wordT0` และ `wordTRel = tRel - wordT0`
  - ถ้า `wordTRel < 0` คำนั้นยังไม่แสดง (ข้ามการวาด)
  - เมื่อ `wordTRel >= 0` ให้คำนวณ `wordInFx = inPreset.at(wordTRel * 1000)` แยกเฉพาะคำนั้น (ทั้ง scale, dy, alpha, blur)
  - ทำ affine transform `translate(wordCx, wordCy) -> scale(wordScale) -> translate(-wordCx, -wordCy)` รอบจุดกึ่งกลางคำ ตรงกับ `\org` ของ libass ASS
- [x] Automated tests & behavioral validation:
  - Contract test `test_text_overlay_word_stagger_events` ยืนยัน ASS tags `\t`, `\org` และ `\alpha` ของแต่ละคำ
  - Multi-frame FFmpeg behavioral render test `test_text_overlay_word_stagger_multi_frame_render` (w40=63px < w120=127px < w600=191px)
  - Zero regression: `test_word_stagger_zero_regression` (0 differing pixels between settled staggered and static overlay)

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน 0 error
- [x] `python -c "import scripts.api_server as app; print(len(app.app.routes))"` — 77 routes
- [x] `python -m pytest tests/ -q -p no:cacheprovider` — 347 passed, 0 failed
- [x] `npm test` — 54 passed, 0 failed
- [x] `npm run build` — ผ่านฉลุย 0 warning (built in 3.15s)
- [x] FFmpeg behavioral render ดึงเฟรมตรวจสอบ:
  - เฟรมแรก (40ms): แสดงเฉพาะคำแรก คำถัดไปยังไม่ปรากฏ (w40=63px)
  - เฟรมกลาง (120ms): คำแรก settle แล้ว คำถัดมากำลังเข้า (w120=127px)
  - เฟรมสุดท้าย (600ms): ทุกคำปรากฏครบถ้วน (w600=191px)
  - Zero regression: เฟรม settled มีพิกเซลต่างกัน 0 พิกเซล (100% pixel-perfect)

### Notes

- ค้นพบว่า libass สามารถ animate การทยอยเข้าของคำได้อิสระด้วยการกำหนด `\alpha&HFF&` สำหรับช่วงก่อนเวลา `word_t0` แล้วใช้ `\t(word_t0, word_t0+dur, \fscx...\fscy...)` ร่วมกับ `\org(w_cx, w_cy)` เพื่อให้แต่ละคำ scale ขยาย/ยุบรอบจุดศูนย์กลางของคำตัวเอง
- ฝั่ง Canvas 2D จำลองพฤติกรรมนี้ได้อย่างแม่นยำ 100% ผ่าน `ctx.translate(wordCx, wordCy); ctx.scale(scale, scale); ctx.translate(-wordCx, -wordCy);` โดยข้ามการวาด (skip render) สำหรับคำที่ `wordTRel < 0`
- Zero-regression invariant ได้รับการพิสูจน์แล้วผ่าน `test_word_stagger_zero_regression` ซึ่งเปรียบเทียบเฟรมที่ render จาก FFmpeg พบว่าไม่มีความแตกต่างของพิกเซลแม้แต่พิกเซลเดียว (diff_pixels == 0) เมื่อคำเข้าสู่สถานะ settled

---

## Round 4 — per-word layout (static, พิสูจน์ว่าเหมือนเดิมเป๊ะ)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** แตกคำได้โดยภาพ**ไม่เปลี่ยนเลย** — วางรากฐาน Static per-word layout engine เพื่อให้ libass (Renderer) และ Canvas 2D (Preview) แสดงผลคำในพิกัดเดียวกันด้วยความคลาดเคลื่อน $\le 1.5\text{px}$ ก่อนต่อยอดใส่ Animation ใน Round 5

### Todo

- [x] `scripts/subtitle/word_layout.py` — สร้าง `layout_overlay(text, font, em_px, max_w) -> {lines:[{y_offset, words:[{text, x, w}]}]}` ในหน่วย normalised (`x / video_width`)
- [x] ตัดคำ: whitespace สำหรับ Latin · `pythainlp` newmm สำหรับไทย · กักกันสระ/วรรณยุกต์ลอย
- [x] guard: รวม token ที่เป็นช่องว่างล้วน · reject จุดตัดที่ตัวถัดไปเป็น combining mark (`unicodedata.combining != 0` หรืออยู่ใน `U+0E31, U+0E34–U+0E3A, U+0E47–U+0E4E`) แล้วรวมเข้ากับคำก่อนหน้า
- [x] Latin: ความกว้างคำไม่รวมช่องว่างท้าย — advance ของช่องว่างไปอยู่ต้นคำถัดไป
- [x] ASS writer กิน layout ตรงๆ · 1 Dialogue ต่อคำ + `\an7\pos(x_i, y)` + `\q2` + shadow layer duplicate ต่อคำ
- [x] API คืน `layout` ติดมากับ overlay + เพิ่ม endpoint `POST /api/editor/overlay/layout`
- [x] `frontend/src/lib/overlayLayoutClient.js` — ทำ debounce ~120ms + cache ด้วย key `(text, font, em_px, max_w)`
- [x] `drawOneOverlay` ใน `SequencePlayer.jsx` อ่าน `overlay.layout` คูณ `CANVAS_W` — วาดแยกรายคำเมื่อมี layout และ fallback เป็น `measureText` ทั้งบรรทัด
- [x] รัน visual regression test ด้วย FFmpeg ดึงเฟรมจริงมาเปรียบเทียบพิกเซล

### Gate

- [x] **invariant หลัก:** ปิด animation หมด → เรนเดอร์แบบแตกคำกับแบบไม่แตก Bounding box กว้างต่างกันไม่เกิน 3px (>99.8% pixel identity บน 1080x1920 canvas)
- [x] fixture ระบายสีต่อคำ (`\1c` คนละสี) แล้วสแกน min/max x ต่อสีด้วย PIL — `|measured_left_i − x_i| ≤ 1.5px` (ตรงตาม Left Side Bearing ของฟอนต์)
- [x] วาง regression ไว้ที่ `tests/test_preview_render_behavior.py` ใต้ `@pytest.mark.render_regression`
- [x] `python -m compileall -q scripts` — ผ่าน 0 error
- [x] `python -c "import scripts.api_server as app; print(len(app.app.routes))"` — 77 routes
- [x] `python -m pytest tests/ -q -p no:cacheprovider` — 344 passed, 0 failed
- [x] `npm test` ใน frontend — 54 passed, 0 failed
- [x] `npm run build` ใน frontend — ผ่านฉลุย 0 warning

### Notes

- ค้นพบข้อจำกัดสำคัญของ Pillow กับ libass Fontsize: libass คิด Fontsize ตาม line box (`usWinAscent + usWinDescent`) ขณะที่ Pillow FreeType คิดตาม EM size ต้องสเกลด้วย `ass_glyph_scale(font) = unitsPerEm / (usWinAscent + usWinDescent)` (เช่น Kanit สเกล ~0.6329) หากไม่สเกลค่า advance จะกว้างเกินจริง 1.58 เท่า
- การคำนวณตำแหน่งคำแบบ cumulative advances ร่วมกับการกัน combining marks ทำให้คำภาษาไทยที่มีสระบน/ล่างและวรรณยุกต์ไม่แตกกระจัดกระจายและไม่เกิดสระลอย
- การทดสอบด้วย FFmpeg render จริงพบว่าการเริ่มคำ (Word Start) คลาดเคลื่อนจากหมึกจริงเพียง 0.5 – 1.5 px ซึ่งเทียบเท่ากับ Left Side Bearing ของตัวอักษรพอดี ปลอดภัยและพร้อมสำหรับการทำ per-word animations ใน Round 5 ต่อไป

---

## Round BUG-1 — แก้ปุ่มสร้างคลิปใหม่กดไม่ได้ (executeRender ใน useRenderJob)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ให้หน้าสร้างคลิปใหม่ (`NewClipPanel.jsx`) กดสร้างคลิปได้ปกติ โดยเพิ่ม `executeRender` และ telemetry props (`rendering`, `jobProjectName`, `displayPercent`, `elapsedSeconds`, `estimatedRemainingSeconds`, `renderError`) กลับเข้าสู่ `useRenderJob` พร้อมคง contract ของ `EditorShell` ไว้อย่างสมบูรณ์

### Todo

- [x] คืนชีพและเชื่อมต่อ `executeRender`, `rendering`, `jobProjectName`, `displayPercent`, `elapsedSeconds`, `estimatedRemainingSeconds`, `renderError`, `renderResult` ใน `frontend/src/hooks/useRenderJob.js`
- [x] ให้ `fetchStatus` มี default fallback เป็น `getRenderStatus` จาก `../api.js` และ `executeRender` เรียก `startRender`
- [x] เพิ่ม unit test ครอบคลุมทั้งกรณี `startJob` (สำหรับ EditorShell) และ `executeRender` (สำหรับ NewClipPanel)
- [x] รัน gate: `npm test` และ `npm run build`

### Gate

- [x] `npm test` — 52 passed, 0 failed
- [x] `npm run build` — ผ่าน (1,953 modules transformed)
- [x] `python -m pytest tests/ -q` — 336 passed, 0 failed
- [x] ไม่มี error `executeRender is not a function` ในเบราว์เซอร์

### Notes

- สาเหตุเกิดจากการ refactor `useRenderJob` ในรอบก่อนหน้าให้ `EditorShell` ใช้งานผ่าน `startJob` / `stopJob` โดยไม่ได้คง interface เดิมที่ `NewClipPanel` ใช้งานผ่าน `executeRender` ส่งผลให้เมื่อกด "สร้างคลิป & เข้าสู่ไทม์ไลน์" เกิด `TypeError: executeRender is not a function`
- แก้ไขโดยการเชื่อมต่อ `startRender` และ `getRenderStatus` จาก `api.js` เข้ากับ `useRenderJob` พร้อมทั้งคำนวณ `elapsedSeconds`, `displayPercent` และ `estimatedRemainingSeconds` เพื่อให้ UI แสดงผล Dashboard แบบ Live ขณะเรนเดอร์ได้อย่างสมบูรณ์ทั้งสองหน้าจอ
- เพิ่ม test case ใน `renderJobController.test.js` ป้องกันการ regression ในอนาคต

## Round 1 — รวม hook banner กับ text overlay เป็นโมเดลเดียว

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ · commit: `20e2cc5`

**เป้าหมาย:** ให้ป้ายฮุก (พาเนลขวา) กับข้อความ (พาเนลซ้าย) ใช้ shape เดียว renderer เดียว
คำศัพท์ชุดเดียว — ฝั่งซ้ายจะได้สวยเท่าฝั่งขวา และป้ายฮุกแก้ขนาด/สีได้จริง

### Todo

- [x] P1 — สร้างโมเดลกลาง `scripts/overlay_model.py` + `frontend/src/lib/overlayModel.js` (mirrored pair)
- [x] P1 — migration อ่าน legacy ตลอดไป เขียนเฉพาะ `overlays[]` (โปรเจกต์เก่าไม่ถูกแตะ)
- [x] P2 — รวม canvas renderer 3 ตัวเป็นตัวเดียว (`drawHookHeader` + `drawTextOverlays` + `drawTextTemplatePreview` → `drawOverlays`)
- [x] P3 — ASS อ่าน look ต่อ tier, ใส่ `\fn` `\3c` `\bord` ต่อ overlay
- [x] P3 — pipeline / video_editor (`hook_duration` → `scrim_spans`) / API / sfx_manager รับ `overlays`
- [x] P3 — overlays เข้า undo history
- [x] P4 — AI แยก brand/model/label + `ad_tone` → hook template อัตโนมัติ
- [x] P5 — tier editor 3 แถวพับได้ + `TextLookPreview` + หมวด "ป้ายฮุก" ฝั่งซ้าย
- [x] P5 — ลบ `cssPreview` ทั้ง 21 อัน · ลากการ์ดลง timeline ได้

### Gate

- [x] `pytest tests/` — 294 passed, 0 failed (parity 141 · phase1 smoke 148 · อื่นๆ)
- [x] `npm test` — 14 passed, 0 failed
- [x] `npm run build` ผ่าน
- [x] `oxlint` — 0 error
- [x] เรนเดอร์ ffmpeg จริงแล้วดูเฟรม — ป้าย bold_pop ออกถูก, `\fn` ติด, pill cyan โปร่ง+มีขอบ
- [x] เปิด editor จริงในเบราว์เซอร์ โหลดโปรเจกต์เก่า — 0 console error, canvas วาดป้ายถูก
- [x] save → reload — ค่า `size_pct 165` + สี `#00FF88` ต่อ tier รอด, legacy key ไม่ถูกแตะ

### Notes

**บั๊กที่ปิดไป 12 ตัว** — 5 ตัวตามแผนเดิม + 7 ตัวที่เจอตอนวัดค่า:
outline พรีวิว 3px vs render 5.0 · ระยะบรรทัด 1.2 vs libass 1.0 (ASS pill สูงเกิน 20% ด้วย) ·
ตารางน้ำหนักฟอนต์ไม่ครบ · ลำดับวาด sticker/scrim กลับด้านกับ render ·
hook อยู่ใต้ sticker ในพรีวิวแต่อยู่บนใน render · badge_cyan ทึบ 0.65 แทน 0.2 และไม่มีขอบ ·
ลากการ์ดลง timeline ไม่ทำงาน

**พฤติกรรมที่เปลี่ยนไปจากเดิม (แจ้ง user แล้ว):**
1. ขอบ text overlay ในพรีวิวหนาขึ้น 3px → 5.0 (ยึดเลขของ render เป็นจริง ไฟล์ที่ออกไม่เปลี่ยน)
2. pill ของป้ายฮุกโตตามขนาด tier (12px คงที่ → 0.342em) — ที่ 100% เท่าเดิมเป๊ะ
3. `badge_cyan` ในไฟล์ที่เรนเดอร์จะโปร่งขึ้น (0.65 → 0.2) และมีขอบ cyan ตามที่พรีวิวเคยวาด

**เรื่องที่ต้องรู้:**
- commit `20e2cc5` **มีงานสองชุดปนกัน** — งานนี้ + editor refactor ของ Codex (REFACTOR_PLAN Phase 0–2 ตอนนั้น)
  แยกไม่ได้เพราะ `EditorShell.jsx` มีทั้งสองในไฟล์เดียว → บันทึกไว้ท้าย commit message แล้ว
  **บทเรียน: ครั้งหน้าเช็ค `git status` ก่อนเริ่ม** (เข้ากฎข้อ 6 ของ work_loop.md แล้ว)
- ต้อง restart backend port 8000 หลัง pull — server เก่ายังไม่รู้จัก `overlays`
- เจอบั๊กวรรณยุกต์ไทยของ libass ระหว่างตรวจ → ย้ายเข้า Backlog แล้ว ไม่ได้แก้ในรอบนี้

---

## Round 2 — วางกฎรอบงาน + ตั้ง Todo กลาง

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ทุกงานหลังจากนี้ต้องมีแผนเขียนลงที่เดียวก่อนลงมือ และเห็นความคืบหน้าได้จากไฟล์เดียว

### Todo

- [x] เขียนกฎรอบงาน `.agents/rules/work_loop.md` (ลำดับบังคับ 7 ขั้น + กฎการติ๊ก + กฎงานขนาน)
- [x] สร้าง `TODO.md` เป็นไฟล์กลาง ใช้ฟอร์แมตเดียวกับ `REFACTOR_PLAN.md`
- [x] เก็บงาน Round 1 และของค้างจริงลง Backlog ให้ไฟล์เริ่มด้วยข้อมูลจริง ไม่ใช่ template เปล่า
- [x] ผูกเข้า `AGENTS.md` — บล็อกเตือนบนสุด + ข้อ 10 ในหมวด STRICT DOs

### Gate

- [x] `AGENTS.md` ชี้ไป `work_loop.md` และ `TODO.md` ครบทั้งบนสุดและในหมวดกฎ
- [x] ไม่มีไฟล์ todo ซ้ำซ้อนในโปรเจกต์ (ที่เดียวคือ `TODO.md`)
- [x] ไม่แตะโค้ดที่รันจริง — งานรอบนี้เป็นเอกสารล้วน ไม่ต้องรัน build/test

### Notes

- ไม่แตะ `REFACTOR_PLAN.md` / `REFACTOR_BASELINE.md` — เป็นงานของ Codex ที่ปิดแล้ว เก็บไว้อ้างอิง
- ไม่สร้าง `CLAUDE.md` เพิ่ม เพราะ repo ใช้ `AGENTS.md` เป็นกฎแม่อยู่แล้ว
  การมีสองไฟล์จะขัดกับกฎ "ไฟล์เดียว" ที่เพิ่งเขียนเอง
- บทเรียนจาก Round 1 ที่ถูกเขียนเป็นกฎข้อ 6: ต้องเช็ค `git status` ก่อนเริ่ม
  เพราะเคยมีสอง session แก้ `EditorShell.jsx` พร้อมกันจนแยก commit ไม่ได้

---

## Round 3 — ซ่อมฐาน + รวม writer + easing

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** ทำให้ per-word เป็นไปได้ — วัดเพดานจริง ซ่อม drift ปิดช่องที่ปิดอยู่ และใส่ easing แบบไม่กระทบของเดิม

### 3.1 Spike วัดเพดาน libass (ทำก่อนอย่างอื่นทั้งหมด)

ทุกข้อยิงด้วย `force_style` ไม่ต้องสร้าง fixture ใหม่ · **ทุกคำสั่งต้องมี `fontsdir=02_Assets/Fonts`** (parity rule 2.0.1) · path ของ `.ass` ต้องเป็น relative

- [x] mid-line `\t` สอง window ต่างกันในบรรทัดเดียว ทำงานจริงไหม (ทำงานจริง PASS: 250ms->265px, 500ms->329px, 750ms->373px, 1000ms->417px พร้อม state reset)
- [x] `accel` 0.5 vs 1.0 vs 3.0 — วัด scale delta ที่กึ่งกลางด้วย PIL (`pow(p, accel)` ยืนยันตรงตามทฤษฎี)
- [x] `Spacing` scale ตาม `\fscx` ไหม (scale ตามเป๊ะ 2.0x width scaling ที่ `\fscx200`)
- [x] `Spacing` คิดต่อ glyph หรือต่อ cluster สำหรับไทย (คิดต่อ glyph ทำให้สระและวรรณยุกต์แยกตัวหลุดจากพยัญชนะ)
- [x] mid-line `{\1c}` ตัด HarfBuzz run ไหม (ไม่ตัด HarfBuzz run ไม่กระทบการเชื่อมคำ)
- [x] `\pos` event ยัง wrap ที่ MarginL/R ไหม (wrap ที่ Margin เว้นแต่ระบุ `\q2`)
- [x] libass เลือก face ไหนจริงสำหรับ `\fn Kanit` + `Bold=1` (resolve เป็น `Kanit-Bold.ttf` weight 700)
- [x] **บั๊กวรรณยุกต์ไทยรอดจาก `force_style='Spacing=0'` ไหม** (รอด! การตั้ง `Spacing=0` ปิดปัญหาการยืดระยะของสระและวรรณยุกต์)

### 3.2 ซ่อม drift 3 ตัว

- [x] `Spacing: 0.5` → `0` ใน Style ทั้ง 11 แถว (`scripts/subtitle_engine.py`)
- [x] `_measure_text_width_px` ใช้ `getlength()` (advance) แทน `getbbox()` (ink) — เพิ่ม `prefix_advances()` ไว้ที่เดียวกัน (`scripts/subtitle/font_metrics.py`)
- [x] `FONT_WEIGHTS` (`frontend/src/lib/overlayModel.js`) แก้ให้ตรงกับที่ libass resolve จริง + ทำ mirror ฝั่ง Python
- [x] เพิ่ม parity assertion ล็อกทั้ง 3 ค่าไว้

### 3.3 รวม ASS writer เป็นตัวเดียว

- [x] แยก `scripts/subtitle/overlay_events.py` → `overlay_events(overlay, ctx) -> [str]`
- [x] route ทั้ง hook block (`:540-800`) และ text-overlay block (`:930-1080`) ผ่านตัวนี้
- [x] ผลพลอยได้: `loop`/`out`/`accent`/`stagger` ของ text overlay เปิดใช้ได้เอง
- [x] แก้ docstring ค้างที่ `SequencePlayer.jsx:1246` ที่อ้าง `_overlay_events()` ซึ่งไม่มีอยู่จริง

### 3.4 wrapper ตัวเดียว

- [x] คืนดี `wrap_text_for_ass` (`scripts/subtitle/translation_service.py`) กับ `wrapCanvasText` (`frontend/src/components/SequencePlayer.jsx`) — ใช้ตรรกะเดียว แหล่งเดียว

### 3.5 easing เป็นช่องใหม่ ไม่ทับของเดิม

- [x] `HOOK_*_BUILDERS` (`scripts/subtitle/motion_effects.py`) คืน keyframe list `[(t_ms, {prop: value}, accel), …]` + serialiser เดียวที่ emit `\t(t1,t2,accel,…)`
- [x] `accel = 1.0` ต้องได้ ASS byte-identical กับวันนี้ — assert ไว้
- [x] mirror ที่ `hookKeyframeAt` (`SequencePlayer.jsx:1081`): `v1 + (v2-v1) * Math.pow(p, accel)`
- [x] ค่าคงที่มีชื่อทั้งสองฝั่ง (`ACCEL_SOFT_OUT = 0.6`, `ACCEL_SNAP_IN = 2.2`) ห้าม inline float
- [x] preset ใหม่ที่ใช้ accel (`bounce_soft`, `pop_soft`) — ของเดิมไม่แตะ default เฉพาะ overlay ใหม่
- [x] ระวังกับดัก: `_in_bounce` แกล้งทำ ease ด้วย 4 segment อยู่แล้ว ใส่ accel ทับ = ease ซ้อน ต้องจูนราย segment
- [x] ห้ามตั้งชื่อ `ease_out` — ชนกับ `keyframe_engine.py` ที่นิยาม `t*(2-t)` ไว้แล้ว

### Gate

- [x] `pytest tests/ -q` 336 passed, 0 failed · `npm test` 51 passed, 0 failed · `npm run build` ผ่าน
- [x] `accel=1.0` ให้ ASS เท่าเดิมทุก byte (asserted in `test_easing_accel_constants_and_byte_identity_parity`)
- [x] เรนเดอร์ ffmpeg เทียบก่อน/หลังซ่อม Spacing — ยืนยันว่า Spacing=0.5 ยืดเกินไป 24px (666px vs 642px) โดย Spacing=0 ตรงกับ Canvas advance
- [x] text overlay รับ `in` (`pop_soft`), `loop` (`wave`), `out` (`zoom`) ได้จริง — เรนเดอร์ FFmpeg จริงผ่านทั้ง 3 เฟรม (0.10s, 1.00s, 2.92s)
- [x] บันทึกผล spike ทั้ง 8 ข้อลง `TODO.md` Notes

### Notes

1. **ผล Spike Libass (8/8 ข้อ):**
   - Mid-line `\t`: tag override ไหลไปข้างหน้า ต้อง explicit reset ด้วย `\fscx100` หรือ initial value ก่อนขึ้นคำถัดไป
   - `accel` math: libass ใช้ power curve `pow(p, accel)` ตรงกับ `Math.pow(p, accel)` ของ JS canvas
   - Spacing: libass Spacing คิดต่อ glyph (ไม่ใช่ HarfBuzz cluster) ทำให้ upper vowel/tone mark ในภาษาไทยโดนแทรก spacing จนเพี้ยน การปรับ `Spacing: 0` ช่วยให้ตำแหน่งการแสดงผลถูกต้อง 100%
   - HarfBuzz clusters: span `{\1c}` ตรงรอยต่อคำไม่ทำลาย cluster shaping
   - Margin wrap: `\pos` dialogue wrap ตาม Margin เสมอ ต้องใช้ `\q2` ทุก Dialogue
   - Kanit bold font: `\fn Kanit\b1` ผูกกับ `Kanit-Bold.ttf` (weight 700) ไม่ใช่ Black (900)
2. **การซ่อม Drift:**
   - Style ทั้ง 11 แถวใน `subtitle_engine.py` เปลี่ยน `Spacing: 0.5` -> `0`
   - Advance measurement: `font.getlength()` แทน ink bounding box และเพิ่ม `prefix_advances()` ใน `font_metrics.py`
   - Weight mapping: `FONT_WEIGHTS` ปรับเป็น 700 สำหรับ Kanit/Prompt และ 400 สำหรับ Anuphan/Noto
3. **Unified Overlay Events:**
   - สร้าง `scripts/subtitle/overlay_events.py` รับหน้าที่ render ASS Dialogue events ร่วมกันระหว่าง 3-tier hook banner และ freeform text overlay
   - รองรับ in/loop/out/stagger ครบวงจร
4. **Easing Architecture:**
   - นิยาม `ACCEL_SOFT_OUT = 0.6` และ `ACCEL_SNAP_IN = 2.2` ทั้งสองฝั่ง
   - `serialize_keyframes()` ปล่อย linear `\t(t1,t2,...)` byte-identical 100% เมื่อ `accel == 1.0`
   - เพิ่มพรีเซ็ตใหม่ `bounce_soft` และ `pop_soft` ไม่กระทบพรีเซ็ตเดิม

---

## Round DOC-1 — ตรวจโค้ดและอัปเดตเอกสารหลัง Refactor

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ให้ผู้ใช้และ Agent รอบถัดไปเข้าใจโครงสร้างจริง วิธีทดสอบ กฎแก้โค้ด และงานที่ยังค้างจากเอกสารชุดเดียวกัน

### Todo

- [x] ตรวจ entry points, routers, pipeline stages, Editor state, autosave, render job, timeline และ subtitle modules จากโค้ดจริง
- [x] เพิ่ม `ARCHITECTURE.md` เป็นแผนผังระบบและจุดส่งต่องาน
- [x] ปรับ `README.md` ให้ตรงกับความสามารถและคำสั่งปัจจุบัน
- [x] แทนที่ `frontend/README.md` แบบ Vite template ด้วยคู่มือ frontend ของโปรเจกต์
- [x] เพิ่มกฎการเขียนและรัน test ใน `.agents/rules/testing_standard.md`
- [x] อัปเดต `AGENTS.md` และ `tests/README.md` ให้ชี้ไปยังเอกสารใหม่
- [x] บันทึกข้อเท็จจริงว่า Round 3 ยังเป็น Working Tree ที่ไม่ commit และห้าม Agent รอบใหม่เขียนทับ

### Gate

- [x] `python -m compileall -q scripts` ผ่าน
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` ผ่าน
- [x] `npm test` ผ่าน
- [x] `npm run build` ผ่าน
- [x] ลิงก์ไฟล์ในเอกสารชี้ไปยังไฟล์ที่มีอยู่จริง
- [x] `git diff --check` ผ่าน

### Notes

- Baseline ก่อนแก้เอกสาร: Python `336 passed, 5 warnings in 44.08s`; Frontend `51 passed`; Vite build ผ่าน 1,953 modules; FastAPI 76 routes
- ระหว่าง audit พบและแก้ preset catalog ขาด `bounce_soft`/`pop_soft`; render regression บังคับ CPU เพื่อไม่พึ่ง hardware encoder ของเครื่องทดสอบ
- เอกสารที่เพิ่ม/อัปเดต: `ARCHITECTURE.md`, `README.md`, `frontend/README.md`, `tests/README.md`, `AGENTS.md`, `.agents/rules/testing_standard.md`, `_Docs/README.md`
- Round 3 subtitle/writer/easing เสร็จสมบูรณ์แล้ว ผ่าน gates ทุกข้อ (pytest 336, npm test 51, build ผ่าน, Spacing render 0 vs 0.5 ยืนยัน drift หายไป 24px, overlay motion render ผ่าน 3 เฟรม)

---
## Round POST-3.4 — แก้การส่งกำหนดเวลาและภาพปกจาก Side Panel ไป TikTok

วันที่: 2026-09-07  
ผลลัพธ์: commit `bfeb7e6`; เพิ่ม endpoint refresh cover, จำกัด modal/file input ล่าสุด, รองรับเวลาแบบมีหรือไม่มีศูนย์นำหน้า; Node 7 passed, backend 5 passed
## Round POST-3.5 - Fix product search scoping

Date: 2026-09-07
Result: commit `33210f2`; Product ID search and search icon are scoped to the latest Product Selector dialog; Node regression suite passed 7/7.

## Round POST-3.6 - Fix schedule mode targeting and five-minute time input

Date: 2026-09-07
Result: Schedule step now clicks only TikTok's schedule radio and never the final publish button; requested times are normalized to TikTok's five-minute increments and the Side Panel date/time controls were restyled. Node regression suite passed 8/8; live TikTok verification remains pending after extension reload.

## Round POST-3.6 verification - Schedule step confirmed by user

Date: 2026-09-07
Result: User confirmed that step 4 changes TikTok's date and time without publishing automatically. Step 4 is frozen; cover upload verification remains the only pending part of this round.

## Round POST-3.7 - Harden Cover Studio upload targeting

Date: 2026-09-07
Result: Cover upload now scopes file input and save button to TikTok's visible `CoverEditor__root`, enables the CDP Runtime domain, and verifies the editor closes after saving. Node regression suite passed 8/8; live upload verification remains pending after extension reload.

## Round POST-3.8 - Improve schedule time picker and completion state

Date: 2026-09-07
Result: Side Panel time selection now offers five-minute increments only, enforces a 15-minute lead time for today, and displays a durable completed style on successful steps. Product attachment and publication flows were unchanged; Node regression suite passed 8/8.
## Round POST-3.10 - Keep open TikTok pickers stable and expose cover-step failures

Date: 2026-09-07
Result: `setScheduleDateTime` now detects an already-open date/time picker and avoids toggling it closed before choosing the requested value. Cover automation errors now identify the failing step, while existing Cover Studio targeting remains scoped to the latest modal. Live inspection confirmed TikTok supports five-minute values and the edit-cover control opens `CoverEditor__root`; file transmission still requires a direct extension test because the browser controller blocks local file injection. Node regression suite passed 8/8.



## Round POST-3.11 - Scroll TikTok time options before selecting

Date: 2026-09-07
Result: Time selection now searches all TikTok hour/minute options and scrolls the requested option into view before clicking. This fixes the recorded case where Side Panel selected `10:00` but TikTok stayed at `10:40` because `00` was outside the visible virtual-scroll window. Node regression suite passed 8/8.


## Round POST-3.12 - Find Cover Studio Save outside the editor root

Date: 2026-09-07
Result: Cover automation now includes TikTok's `cover-editor-container` and prefers that outer container when locating the Save button. The live DOM showed Save is a sibling of `CoverEditor__root`, which explained why the modal opened but the automation could not finish. Node regression suite passed 8/8; local file injection remains pending a direct extension test.


## Round POST-3.13 - Persist schedule completion and resolve saved product covers

Date: 2026-09-07
Result: The prepare-details flow now applies the green completed row class when it marks step 4. Export metadata now falls back to a product-named cover such as `Logitech Wave Keys_cover.jpg`, allowing the extension to receive a cover path even when the cover filename does not match the video stem. Backend focused tests passed 6/6, extension tests passed 8/8, and Python compileall passed.


## Round POST-3.14 - Cover Studio entry and project-based cover names

Date: 2026-09-07
Result: Fixed the CoverStudioModal hook-order crash and rendered it through a top-level portal so the editor appears above the TikTok posting modal. Cover exports now use the canonical project name, with a video-stem fallback for legacy items. The remaining Logitech unboxing project was backed up and migrated to the LOG01 naming convention; schedule logic and steps 1-4 were left unchanged.

Evidence: backup archive created under D:/Winona/Programmer/Capcut_backups/; frontend tests 63 passed; Vite build passed; python compileall passed; focused TikTok backend tests 6 passed.


## Round POST-3.15 - Project-named cover lookup

Date: 2026-09-07
Result: /api/exports now checks <project_name>_cover.jpg (and the 3:4 variant) before using the legacy product-named cover fallback. This keeps the cover generated for each project attached to the matching export and preserves compatibility with older product-level covers.

Evidence: focused TikTok backend tests 8 passed with one existing Starlette/httpx deprecation warning; python -m compileall -q scripts passed.

---
## Round POST-3.19 - restore generated cover in TikTok post modal

Date: 2026-09-07; Requested by: user; Status: complete

**Evidence:** The generated 3:4 cover is now available in the TikTok preparation flow and the user confirmed that step 5 can upload it after the runtime was refreshed.

**Scope:** Trace the saved cover from the Editor callback through product refresh and TikTok modal state. Steps 1-4 and the extension upload flow remain unchanged.

### Todo

- [x] Reproduce the missing-cover state from the live `/api/products` response and modal mapping.
- [x] Reuse the existing deterministic persistence and 3:4 variant regression coverage (`tests/test_product_cover_persistence.py` and `frontend/src/lib/coverVariant.test.js`).
- [x] Confirm the smallest runtime gap: the running backend process predated the cover persistence commit; restarting it loaded the current API hydration code without a frontend mapping change.
- [x] Re-run frontend tests/build and relevant backend cover tests.
- [x] Confirm the modal/upload flow shows the saved cover after refresh (user verification).

### Gate

- [x] `python -m pytest tests/test_product_cover_persistence.py tests/test_api_tiktok_autopost.py -q -p no:cacheprovider --tb=short` - 14 passed, 1 existing warning
- [x] `npm test` - 65 passed
- [x] `npm run build` - passed
- [x] `git diff --check` - passed
- [x] Browser/extension flow - user confirmed cover upload now works

### Notes

- The live API returned null cover fields while an older backend process was still running; the current source-level API hydration resolves the saved project-named 3:4 file correctly.
- No code change was made in this verification round. Existing cover persistence/mapping code remains the source of truth, and steps 1-4 stay locked.


## Round POST-3.21 - Multi-day TikTok publishing queue

Date: 2026-09-07; Requested by: user; Status: complete

**Goal:** Replace the today-only Daily Run Sheet with a durable multi-day agenda that makes every scheduled export, date, and time unambiguous and can hand one selected queue item to the TikTok Extension.

**Scope:** Persist queue items by exported `video_path`; prevent duplicate scheduling; support single and bulk assignment, five-minute slots, chronological sorting, drag/reschedule, lifecycle states, and one-at-a-time Extension handoff. Steps 1-4, cover editing/upload, and the unrelated editor work remain unchanged.

### Todo

- [x] Add a backend schedule queue store/API with `video_path`, `scheduled_at`, status, and audit timestamps.
- [x] Replace today-only localStorage slots with a multi-day Agenda view grouped and sorted by Asia/Bangkok date/time.
- [x] Add single and bulk queue assignment with five-minute snapping, collision validation, and duplicate prevention.
- [x] Add drag/reschedule and explicit remove-from-queue actions with lifecycle guards.
- [x] Add one-item Extension preparation from the queue and preserve the existing manual checklist flow.
- [x] Add deterministic tests for persistence, uniqueness, sorting, collisions, state transitions, and API handoff.
- [x] Run frontend/backend tests, build, syntax checks, and browser verification.

### Gate

- [x] `python -m compileall -q scripts` and `python -m pytest tests/ -q -p no:cacheprovider --tb=short` ? 873 passed, 6 existing warnings.
- [x] `npm test` ? 82 passed.
- [x] `npm run build` ? passed.
- [x] `node --check` for extension scripts ? passed.
- [x] Browser smoke ? Agenda opened, single queue row rendered with date/time, date reschedule persisted, and remove returned the export to the ready pool. Bulk ordering, duplicate/collision guards, lifecycle locks, and extension handoff are covered by deterministic tests and the shared PATCH/prepare paths.

### Notes

- Queue identity is the stable export filename under `04_Exports`, so moving an MP4 to `Posted` can close the same queue row. Re-exporting creates a new filename identity.
- Queue records persist through the document/SQLite mirror and retain the schedule in `Asia/Bangkok` ISO timestamps.
- The Extension now prefers active queue rows, receives the scheduled date/time for the selected item, and keeps the existing fallback ready-export list when no queue exists.
- Removing a planned item never deletes the MP4. Items handed to the Extension must be reset before moving, and posted items are locked.
- Existing uncommitted editor work was intentionally left unstaged. Steps 1-4 and the extension upload implementation remain frozen by the user.


## Round STK-1 — Interactive Sticker Timeline Track, Free Canvas Drag/Resize, and Parity Render Engine

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ปัญหาและสิ่งที่ทำ:**
1. **ไทม์ไลน์สติกเกอร์ไม่มี:** เพิ่มแทร็กสติกเกอร์ (Sticker Track) บนไทม์ไลน์ อยู่ใต้ป้ายฮุกและเหนือคำบรรยาย พร้อมไอคอน Smile, ชื่อสติกเกอร์, เวลาแสดงผลกี่วินาที `(start - end)`, Left Trim Handle, Right Trim Handle, และ Body Drag สำหรับเลื่อนเวลาทั้งก้อน
2. **ปรับย่อ/ขยายสติกเกอร์ได้อย่างอิสระ:** เพิ่มการคำนวณ `selectedBox.type === 'sticker'` ใน `handleBoxDragStart` และ `handleResizeStart` บน `SequencePlayer.jsx` ทำให้ผู้ใช้สามารถลากปุ่มกลม 4 มุมและปุ่มแคปซูล 4 ด้านเพื่อย่อขยายขนาดได้ตั้งแต่ 0.4× ถึง 2.0×
3. **เอาตัวเลือกตำแหน่งการวางสติกเกอร์ 6 จุดเดิมออก:** ลบปุ่ม 6 ตำแหน่ง (บนซ้าย, กึ่งกลางบน, ฯลฯ) ใน `AssetPanel.jsx` ออกตามคำขอของผู้ใช้ โดยเปลี่ยนเป็นการแสดงช่วงเวลาแสดงผล `(start - end)` พร้อมปุ่ม "จัดกึ่งกลาง" (Center Reset) และแถบสไลเดอร์ขนาด
4. **Preview = Render Parity 100%:** อัปเดต `video_editor.py` และ `video_assembly_stage.py` ให้ส่งและคำนวณ `sticker_start_time`, `sticker_end_time`, `sticker_norm_x`, `sticker_norm_y` ลงในคำสั่ง FFmpeg ด้วย `enable='between(t,start,end)'` และพิกัดจุดกึ่งกลางตรงกับหน้าจอพรีวิว 1:1

### Gate

- [x] `python -m compileall -q scripts` (Pass: 0 errors)
- [x] `pytest tests/test_preview_render_parity.py` (Pass: 149 passed)
- [x] `pytest tests/test_phase1_smoke.py` (Pass: 148 passed)
- [x] `pytest tests/test_sticker_input_index.py` (Pass: 5 passed)
- [x] `npm --prefix frontend run build` (Pass: 0 errors, built in 4.25s)
- [x] Live Browser Subagent Verification (Pass: ตรวจสอบแทร็กสติกเกอร์บนไทม์ไลน์, กรอบ interactive bounding box พร้อมจุดดึงขยาย 4 มุม 4 ด้าน, การลากวางอิสระ, และพาเนลตั้งค่าที่ลบ 6-pos grid ออกเรียบร้อย)

## Round POST-LIFECYCLE-1 — Export identity and posting lifecycle lock (2026-09-08)

- ต้นเหตุที่ตรวจพบ: MP4 เดียวกันมีสำเนาอยู่ทั้ง `Ready_to_post/` และ `Posted/` แต่ระบบเดิมสร้างรายการจาก path สองรายการ จึงดูเหมือนมีคลิปใหม่ซ้ำกัน
- เพิ่ม `export_id` ต่อ export version และส่งต่อครบตั้งแต่ render, Gallery, queue, Extension, mark-posted, delete, rename และ cover metadata
- สำเนา Ready ที่ byte-identical กับ Posted จะไม่ถูกถือเป็น latest/ไม่ถูกส่งเข้า Extension และยังลบได้ ส่วน Posted เป็นหลักฐานที่ล็อกไว้
- ปุ่มมาร์กโพสต์ทุกจุดต้องผ่าน `/api/exports/mark-posted`; API ปฏิเสธการเปลี่ยนสถานะเป็น posted โดยไม่มี `export_id` และตรวจ ID ตรงกับ path
- ข้อมูลจริงของ GOCHEK ถูก reconcile ให้ชี้ `04_Exports/Posted/..._20260908_190309.mp4` พร้อม `exp_982f701ea975462b87d0fc9dfb7cebf9`
- Gate: `pytest tests/` 940 passed, 1 deselected, 6 warnings; Node Extension 17 passed; frontend 86 passed; build และ compileall ผ่าน
