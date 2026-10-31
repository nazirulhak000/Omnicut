# Theme Audit — PulseHub Glass × Professional SaaS

ดำเนินการโดย: Codex (GPT-6) · วันที่ 2026-10-31 (Asia/Bangkok)

สถานะ: **Source audit เสร็จ; visual/runtime audit ยังไม่ผ่านการตรวจ**

แผนต่อเนื่อง: [PLAN_THEME_GLASS_SAAS_20261031.md](../Plans/PLAN_THEME_GLASS_SAAS_20261031.md)

## 1. ข้อสรุปสำหรับเจ้าของ

ระบบเดิมมีพื้นฐานที่ควรเก็บ: 4 ธีม, 3 glass presets, ตัวปรับค่ากระจก, localStorage, shared UI components และ reduced-motion CSS อยู่แล้ว ปัญหาหลักที่ยืนยันจากโค้ดคือ **ค่าธีมยังไม่เป็นเจ้าของรูปลักษณ์ของทุกพื้นผิว** และตัวปรับแต่งไม่ได้ควบคุมรายละเอียดกระจกทั้งหมด

การเพิ่ม preset หรือเพิ่ม blur อย่างเดียวจึงไม่แก้รากปัญหา ควรจัดระบบ semantic tokens, แบ่งชั้นพื้นผิว, แยกค่าต่อธีม และทำ preview/apply/cancel ให้ชัดก่อนย้ายแต่ละหน้าเข้าระบบเดียวกัน

ข้อเสนอด้านรสนิยมคือ Balanced Glass Workspace: รักษาขอบแสงและความลึกที่ได้แรงบันดาลใจจาก Pulse-Hub ใน shell/navigation/floating surfaces แต่ทำพื้นที่อ่านข้อมูล ฟอร์ม และงานตัดต่อให้สงบกว่า ข้อนี้เป็นข้อเสนอ ยังไม่ใช่การอนุมัติเปลี่ยนธีม

## 2. ขอบเขต หลักฐาน และข้อจำกัด

- อ่านโค้ด OmniCut ใน working tree วันที่ตรวจ บน branch `feat/ai-editor-viral-s1`; HEAD ที่เริ่มตรวจ `34c5ba9`
- ต้นแบบที่ผู้ใช้ระบุจริง: `D:/Winona/Programmer/Pulse-Hub`
- เลือก `Pulse-Hub/public/index.html` เป็น reference หลัก เพราะเป็นหน้าแอปจริง มี CSS material tokens และกลไกปรับแต่งพร้อม persistence
- `Pulse-Hub/public/preview-themes.html` เป็น reference รองสำหรับแนวทางวัสดุ ไม่ใช่ authority ของฟอนต์หรือหน้าแอปจริง เพราะใช้ font stack ต่างจาก index
- ไฟล์ `test-*-glass.html` เป็นหน้า experiment ไม่ใช้แทน production reference
- ไม่แก้ Pulse-Hub, โค้ดแอป OmniCut, localStorage หรือ appearance settings ของผู้ใช้
- Working tree มีงานอื่นค้างใน `frontend/src/api.js`, `ExportGallery.jsx`, `scripts/api_server.py`, `scripts/couple_jobs.py`, frontend/dist และไฟล์ Cloud Archive ใหม่; ห้ามรวมเข้าการเปลี่ยนธีมโดยปริยาย
- พบ `_Docs/Plans/PRODUCT.md` ซึ่งอธิบาย Gadget Media เป็นหลัก ใช้เป็นบริบท workflow เท่านั้น ไม่ตีความว่าเป็น design authority ของทั้งโปรแกรม ไม่สร้าง PRODUCT.md/DESIGN.md ที่รากในรอบนี้

**เครื่องมือดูภาพจริง:** เรียก `cua.getState()` แล้ว browser access host unavailable และ native pipe unavailable จึงไม่มี screenshot ปัจจุบัน desktop/mobile ไม่มีการวัด computed styles, contrast ที่ composite แล้ว, FPS หรือความรู้สึกภาพจริง ไม่อ้างว่าสิ่งเหล่านี้ผ่าน

ผู้ใช้ยืนยันให้ทำแผนต่อจากโค้ด OmniCut/Pulse-Hub พร้อมระบุข้อจำกัดแล้ว การตรวจภาพจริงเป็น exit gate ของ Phase 0 ก่อน implementation ไม่ใช่งานที่ทำสำเร็จในรายงานนี้ ไม่มีภาพเก่าที่ตรวจ freshness ได้ถูกนำมาแทนภาพปัจจุบัน

## 3. Inventory และเส้นทางการทำงาน

| ส่วน | หลักฐาน | พฤติกรรมที่ตรวจจากโค้ด |
|---|---|---|
| Theme catalog | `frontend/src/lib/themeManager.js:14–58` | glassmorphism, obsidian, cyberpunk, slate; default glassmorphism |
| Glass catalog | `themeManager.js:60–87` | crystal / visionos / smoky; config 5 ค่า |
| Persistence | `themeManager.js:10–12, 96–187` | 3 keys: theme, global orbs boolean, global glass config |
| Apply | `themeManager.js:117–175` | theme เป็น `data-theme` บน html; glass เป็น 5 inline CSS custom properties |
| State ใน shell | `frontend/src/App.jsx:469–488` | App init theme, ถือ theme/orbs state; handlers ส่งให้ settings |
| Ambient layer | `App.jsx:1243–1255` | shell สี #030509 และ 3 ambient orbs ที่เปิดตาม boolean |
| Settings | `SystemSettings.jsx:82–129, 322–607` | state ฝั่ง component, live apply/persist ทันที, reset, demo box |
| Master surfaces | `frontend/src/index.css:122–168` | gradient+tint+blur+4 borders+หลาย shadow+2 pseudo-elements |
| Nested/control surfaces | `index.css:171–230` | tile/button/input/card ใช้สูตรต่างกัน มีค่าคงที่หลายส่วน |
| Theme overrides | `index.css:300–417` | selector ต่อ preset เขียนทับบาง class พร้อม !important |
| Shared UI | `components/ui/{Button,Input,Modal}.jsx` | shared primitives มีอยู่แล้ว แต่ใช้สี literal/utility ผสมกับ glass-panel |
| Desktop navigation | `Sidebar.jsx:114,178`, `Topbar.jsx:131` | tint 75–80% และ backdrop utility แยกจาก glass config |
| Editor | `editor/EditorHeader.jsx:70`, `EditorShell.jsx:2457,2720,2775` | outer glass-panel; header และพื้นที่งานหลายจุดสีคงที่ |
| Mobile | `mobile/MobileAppRoot.jsx:35–80` และ `MobileShell.jsx` | subviews มี bg-slate-950; ต้องตรวจ shell/portal ของ mobile เพิ่มขณะ migration |
| Motion | `index.css:785–792` | มี prefers-reduced-motion; ไม่เริ่มจากศูนย์ |
| Tests | `lib/themeManager.test.js:22,37,47,100` | 4 node tests; storage/normalize/DOM properties แบบ mock |

เส้นทางสำคัญ: Settings → applyGlassConfig → CSS vars + localStorage → เฉพาะ selector ที่อ่าน vars ได้รับผล ส่วน selector ที่มีค่า literal หรือ override จะยังใช้ค่าของตัวเอง การผ่าน JavaScript test ไม่ได้ยืนยันว่า UI ทุกชั้นเปลี่ยนจริง

## 4. เทียบ reference Pulse-Hub กับ OmniCut

| ประเด็น | Pulse-Hub source | OmniCut source | ผลต่อแผน |
|---|---|---|---|
| วัสดุแยกตาม mode | `public/index.html:124–211`: glass-bg/tint/border/shadow/tile tokens ต่อโหมด | master panel มีสูตรหลักคงที่ + preset overrides | ให้ material definition ต่อ family เป็นข้อมูลชุดเดียว |
| การปรับความใส | gradient stops ใช้ user-opacity-mult + tint alpha | --glass-opacity ปรับ tint เท่านั้น ไม่เปลี่ยน gradient stops | เปลี่ยนชื่อ/นิยาม control ให้ตรงผลที่เกิดจริง |
| ความแรงแสงขอบ | border และ inset shadows หลายจุดผูก user-specular-mult | --glare-opacity ผูกเส้น ::before; border/shadow ส่วนใหญ่คงที่ | รวม rim, border และ highlight ที่เกี่ยวข้องภายใต้ resolver |
| บันทึกค่ารายธีม | `index.html:2022–2070`: pulse_glass_overrides[mode] | glass config ชุดเดียวข้ามทุกธีม | เก็บ overrides แยก family; เปลี่ยนธีมแล้วไม่ปนค่ากัน |
| Consumer ของ token | `index.html:242–259`: master surface ใช้ var ของวัสดุ | `index.css:123–139`: หลายค่าฝังใน selector | ทำ surface role → resolved tokens แทนสูตรซ้ำ |
| Nested blur | reference ก็มี tile/button blur คงที่ | OmniCut มีเหมือนกัน | ไม่คัดลอกข้อจำกัดด้าน compositing ตามต้นฉบับ |

OmniCut ใช้องค์ประกอบบางสูตรใกล้กับ Pulse-Hub อยู่แล้ว เช่น gradient บน panel, เส้นขอบ 1px และ sheen สูง 38% การยืนยันนี้เป็น **source similarity** ไม่ใช่ pixel parity หรือการหักเหทางกายภาพจริง คำว่า “Refractive/Optical” ในคอมเมนต์หรือ UI ไม่ได้เป็นหลักฐานว่ามี displacement shader

## 5. ข้อค้นพบที่ยืนยันได้จากโค้ด

| ID / Priority | หลักฐาน | ปัญหาและผล | ขอบเขตความมั่นใจ |
|---|---|---|---|
| T01 P1 | `index.css:123–139`, `themeManager.js:168–172` | ความใสปรับเฉพาะ tint; gradient, borders, shadows ยังเข้มเท่าเดิม จึงไม่ใช่ control ของวัสดุทั้งหมด | ยืนยัน dependency จากโค้ด; ความรู้สึกต้องดูภาพ |
| T02 P1 | `index.css:171–230`, `Sidebar.jsx:114`, `Topbar.jsx:131` | tile/button/input/nav ใช้ blur/tint แยกจาก master; slider ไม่ได้ครอบคลุมทั่วแอป | ยืนยัน |
| T03 P1 | `index.css:315–417` | obsidian ปิด blur, slate ล็อก 16px, cyberpunk/slate ล็อก tint แต่ settings ยังให้ปรับค่าเดิม | ยืนยัน selector; runtime effect ต้องยืนยัน computed style |
| T04 P1 | `themeManager.js:137–175` | glass settings เป็นชุด global ไม่มี overrides รายธีม; ค่า smoky/crystal สามารถตามไปธีมอื่น | ยืนยัน storage schema |
| T05 P1 | `SystemSettings.jsx:111–116` | ทุก onChange เขียน DOM+storage ทันที ไม่มี draft/cancel transaction | ยืนยัน |
| T06 P2 | `SystemSettings.jsx:448–450` | active glass preset เทียบแค่ opacity+blur; เปลี่ยน glare/orbs/saturate ยังแสดง preset เดิมเป็น active ได้ | ยืนยัน condition |
| T07 P2 | `themeManager.js:143–147`, `SystemSettings.jsx:488–573` | ช่วงค่า engine/UI ไม่ตรง: opacity 5–70 vs 5–50, blur 2–36 vs 4–30, glare/orbs 10–100 vs 20–100 | ยืนยัน; ทดสอบค่าข้ามช่วงเพิ่มก่อนแก้ |
| T08 P2 | `themeManager.js:60–65`, Settings controls | มี saturate ใน model/preset แต่ไม่มี slider ของมันใน finetuner 4 ตัว; ความสามารถไม่สื่อครบ | ยืนยัน; จะซ่อนเป็น advanced หรือเลิกเปิดให้ปรับเป็นทางเลือก |
| T09 P1 | `index.css:122–230`, `ui/Modal.jsx:92–132` | modal/backdrop/header และ nested tiles มี blur หลายชั้น; master panel บังคับ overflow:hidden/radius24px | ยืนยันโครง; clipping และ GPU cost ยังไม่วัด |
| T10 P1 | `EditorHeader.jsx:70`, `ui/Input.jsx:26`, shell/nav | สีฝังใน component ทำให้ theme ownership กระจัดกระจาย | ยืนยัน; บางสีเป็น intentional ต้องจำแนกก่อนแทน |
| T11 P2 | `App.jsx:1243`, `index.css:309–312` | outer wrapper คง #030509 แม้ preset เปลี่ยน body/root; อาจปิดบัง canvas ของ preset | เป็นความเสี่ยงจาก DOM/CSS ต้องดู runtime ก่อนเรียก visual bug |
| T12 P2 | `themeManager.js:105–114`, `index.css:300–305,374–381` | orbs toggle เป็น global; บาง preset ซ่อน orbs/ล็อก opacity; UI อาจแสดงเปิดแต่ไม่มีผล | ยืนยัน rules; ต้องเทียบ effective state จริง |
| T13 P2 | `SystemSettings.jsx:578–607` | demo box ใช้ orb animation/ตำแหน่งคงที่ของตัวเอง ไม่ใช่ renderer เดียวกับ shell | ยืนยัน; ไม่ใช้ demo เป็นหลักฐานทั้งแอป |
| T14 P1 | `index.css` ไม่มี @supports | ยังไม่มี explicit no-backdrop material fallback ในไฟล์กลาง | ยืนยันขอบเขตไฟล์ ไม่อ้างว่าเบราว์เซอร์ใดพังแล้ว |
| T15 P2 | `SystemSettings.jsx:478–573` | range captions เป็น span ไม่ใช่ label ที่ผูก input และไม่มี aria-label ใน 4 range ที่อ่าน | ยืนยัน markup; ต้องทดสอบ accessible names จริง |
| T16 P1 | `themeManager.test.js` | mock tests ไม่ตรวจ cascade, contrast, portal หรือ preview/render visual isolation | ยืนยันขอบเขต test |

ตัวเลขสำรวจเฉพาะ source ปัจจุบัน: `index.css` มี `!important` 63 occurrences, `backdrop-filter:` แบบไม่รวม -webkit 12 declarations, @supports 0; 100 ไฟล์ .jsx/.js มี literal `bg/text/border-[#hex]` อย่างน้อยหนึ่งจุด ตัวเลขนี้ไม่ใช่จำนวน bug หรือจำนวน runtime layers และรวมสีที่มีเหตุผล เช่น video overlay/status/track จึงห้าม replace ทั้งหมดด้วย regex

ตัวอย่าง literal utility counts: ProductToClip 188, AssetPanel 138, ContentTrackerHub 120, Timeline 111, ExportGallery 91, EditorShell 63, SequencePlayer 52 จำนวนมาจาก regex แบบแคบ ไม่รวมทุก Tailwind color class/inline style และอาจเปลี่ยนได้เมื่อ agent อื่นทำงาน

## 6. สิ่งที่ควรเก็บและสิ่งที่เป็นรสนิยม

ควรเก็บ: theme ids เดิม, fallback/normalization, try/catch กรณี storage ใช้ไม่ได้, shared components, mobile safe-area และ z-index scale, reduced-motion rule, ตัวอย่าง preview เดิมในฐานะจุดเริ่มต้น และ contract ข้อความ/ฟอนต์ของวิดีโอ

ข้อเสนอด้านรสนิยมที่ยังต้องเลือก: ลดขอบชมพู/เงาสีรอบทุกการ์ด, ใช้ accent เดียวสำหรับ action หลัก, ให้ shell สื่อกระจกมากกว่า data cards, ลด animation ต่อเนื่อง และรักษา Editor ให้เป็นกลาง รายงานนี้ไม่เรียกข้อเสนอเหล่านี้ว่า bug และไม่ให้คะแนนความสวยจากการอ่าน source

## 7. Visual/runtime verification ที่ยังค้าง

| กลุ่ม | สิ่งที่ต้องดูจริง | สถานะ |
|---|---|---|
| App shell / Sidebar / Header | มิติพื้นผิว แสงขอบ ความสอดคล้องกับ reference | Pending |
| Dashboard/Analytics | hierarchy ของ KPI/ตาราง, ความชัด selected/error/loading | Pending |
| Editor / Timeline | distraction, track meanings, video neutral boundary | Pending |
| Gallery | ข้อความบนฉาก thumbnail สว่าง/มืด, dropdown/card state | Pending |
| Settings | slider effect ทุก preset, cancel/reset, visible active preset | Pending |
| Modal / Dropdown / Tooltip | opacity หลัง composite, clipping, stacking, focus visibility | Pending |
| Mobile | 390×844 และ 430×932, safe areas, scroll, keyboard, sheet | Pending |
| Performance | scroll/drag/playback baseline บนเครื่องเดียวกัน | Pending |

ไม่มี screenshots ที่สร้างในรอบนี้ ไม่มีการรัน FFmpeg/paid generative API หรือ full build เพราะเป็นเอกสารล้วนและ dist มีงานคนอื่นค้างอยู่

## 8. Validation ที่รันจริงและ Jev

- `node --test frontend/src/lib/themeManager.test.js`: **4 passed, 0 failed** เป็น baseline ของ logic เดิม ไม่ใช่การรับรองหน้าตา
- Jev ผ่าน `tools/jev_advisor.py fanout` ตรวจจาก **สรุป scope ไม่ได้อ่านโค้ดเอง**: noul **0.93**, confidence **null**, verdict **escalate**
- ผู้ใช้ตอบอนุญาตให้ทำแผนต่อจากหลักฐานโค้ดและระบุข้อจำกัด; ไม่ใช้ noul แทน confidence และไม่ใช้ผล Jev เป็นสิทธิ์อนุมัติ implementation
- รายงาน/แผนยังไม่ใช่ผลการเปลี่ยนก่อน–หลัง ไม่มีการอ้าง FPS, contrast ผ่าน หรือ PulseHub parity ที่ยังไม่ได้วัด
- Jev ประเมิน coverage จากสรุปเอกสาร ไม่ได้อ่านไฟล์เอง: score **2.62/3**, confidence **0.61**, verdict **escalate**; เป็นผลที่ต่ำกว่า gate ไม่ใช้รับรองแผนหรือเลือก direction แทนเจ้าของ ส่งเอกสารให้เจ้าของพิจารณาตามขอบเขตที่ยืนยันแล้ว

Snapshot SHA-256 ของ source สำคัญ (สำหรับตรวจ freshness ก่อน Phase 0):

| ไฟล์ | SHA-256 |
|---|---|
| OmniCut `frontend/src/lib/themeManager.js` | `009E06021676384BC339BEAFD0856F182F050928B9CC5D9CD32103AF670852B4` |
| OmniCut `frontend/src/index.css` | `6850387DFB5A09DBC2778F7A219B2E646A90F5293B7B6DF90E92C98E5C5D9219` |
| Pulse-Hub `public/index.html` | `FD4161BC951F20E2BBE7842C0479119066B988439BEF246E3A20EAC11A9C21BA` |

## 9. แหล่งอ้างอิงเชิงเทคนิค

- [W3C: Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html): ใช้เกณฑ์ข้อความปกติ ≥4.5:1; อย่าอ้างว่าคู่สีผ่านจาก hex foreground อย่างเดียวเมื่อพื้นโปร่ง
- [W3C: Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html): visual information ที่จำเป็นต่อการระบุ control/state ต้องมี contrast ≥3:1 กับสีข้างเคียง; ไม่ใช่บังคับทุก decorative border
- [MDN: backdrop-filter](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backdrop-filter): filter ทำกับบริเวณหลัง element และต้องมีความโปร่งให้เห็นผล; ใช้ประกอบการออกแบบ fallback และตรวจ backdrop roots จริง

อ้างอิงเว็บตรวจวันที่ 2026-10-31; ใช้เพื่อเกณฑ์ทดสอบและกลไก CSS เท่านั้น ไม่ใช้เป็น reference รสนิยมแทน Pulse-Hub ของผู้ใช้
