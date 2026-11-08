# OmniCut Pro Studio — แผนปรับประสบการณ์และหน้าตา UI จากการตรวจ 10 รอบ

วันที่: 2026-11-08 · ดำเนินการโดย: Codex (GPT-6.1-sol)

สถานะ: **จัดทำแผนเท่านั้น — ยังไม่ได้ปรับ UI หรือยืนยันภาพผลลัพธ์หลังปรับ**

ขอบเขตที่ผู้ใช้ยืนยัน: ตรวจทั้งระบบ โดยให้น้ำหนักห้องตัดต่อและคลังสินค้า ผู้ใช้ยืนยันให้ทำเอกสารต่อหลัง Jev ได้ confidence ต่ำกว่าเกณฑ์

เอกสารนี้ใช้ `/unslop`, `/impeccable` และ `/ui-ux-pro-max` ร่วมกับกฎโปรเจกต์ โดยให้คำสั่งผู้ใช้และข้อจำกัดงานวิดีโอเป็นหลัก แนวคิด Unslop โดย Damir Sokolovsky [@heydamir](https://x.com/heydamir) เผยแพร่ภายใต้ CC BY 4.0

## สารบัญ

1. [ผลที่ต้องการและข้อจำกัดหลักฐาน](#1-ผลที่ต้องการและข้อจำกัดหลักฐาน)
2. [ทิศทางการออกแบบที่เสนอ](#2-ทิศทางการออกแบบที่เสนอ)
3. [บันทึกตรวจและปรับแผนครบ-10-รอบ](#3-บันทึกตรวจและปรับแผนครบ-10-รอบ)
4. [ระบบภาพและองค์ประกอบกลาง](#4-ระบบภาพและองค์ประกอบกลาง)
5. [แผนรายหน้าจอและโครงสร้างงาน](#5-แผนรายหน้าจอและโครงสร้างงาน)
6. [สถานะข้อความและข้อมูล](#6-สถานะข้อความและข้อมูล)
7. [แผนดำเนินงานและไฟล์ที่เกี่ยวข้อง](#7-แผนดำเนินงานและไฟล์ที่เกี่ยวข้อง)
8. [เกณฑ์ตรวจรับและแผนพิสูจน์ผล](#8-เกณฑ์ตรวจรับและแผนพิสูจน์ผล)
9. [ความเสี่ยงการย้อนกลับและจุดตัดสินใจ](#9-ความเสี่ยงการย้อนกลับและจุดตัดสินใจ)
10. [ผลตรวจเอกสารและการส่งต่อ](#10-ผลตรวจเอกสารและการส่งต่อ)

## 1. ผลที่ต้องการและข้อจำกัดหลักฐาน

### 1.1 เป้าหมาย

ให้ OmniCut อ่านเป็นเครื่องมือผลิตคลิปที่เจ้าของช่องใช้ทำงานจริง: เห็นสินค้าที่ทำอยู่ รู้ว่างานอยู่ขั้นใด หาสิ่งที่ต้องทำต่อได้ และมีพื้นที่ดูคลิปมากพอ ภาพจำควรเกิดจากคลิป 9:16 สินค้าจริง และเส้นทางการผลิตที่ตรวจสอบได้

คำว่า “ไม่เหมือน AI” ในแผนนี้แปลงเป็นสิ่งตรวจรับได้ดังนี้

- ลำดับความสำคัญของข้อความ ปุ่ม และพื้นที่ทำงานชัดเจนในแต่ละหน้า
- สีบนส่วนควบคุมมีหน้าที่ ไม่แจกสีเฉพาะให้ทุกการ์ดและทุกไอคอน
- ระยะ ขนาดแถว รูปแบบปุ่ม และชื่อคำสั่งใช้ระบบเดียวกัน
- ภาพสินค้า คลิป และข้อมูลการผลิตเป็นส่วนที่เด่นที่สุด
- สถานะบอกข้อเท็จจริง รวมถึงกำลังตรวจ ไม่ทราบผล และข้อมูลเก่า
- ความเป็นไทยอยู่ในการอ่านและภาษาที่ใช้ทำงาน ไม่ต้องใส่เอฟเฟกต์เพื่อสร้างบุคลิก

### 1.2 สิ่งที่ตรวจจริงในรอบนี้

| ประเภท | หลักฐานที่มี | ขอบเขตการสรุป |
|---|---|---|
| Source ปัจจุบัน | React 19, Vite 8, Tailwind 4, Lucide และไฟล์ส่วน UI ที่อ้างในแต่ละรอบ | ยืนยันโครงสร้างและ class ที่พบได้ |
| การค้นทั้ง source | 285 ไฟล์ `.jsx/.js/.css` ใต้ `frontend/src` ยกเว้นชื่อไฟล์ที่มี `.test.` | เป็นจำนวนข้อความที่ตรง pattern ไม่ใช่จำนวน defect หรือจำนวน element ใน DOM |
| ภาพเก่า | `.tmp/hf7-browser-review/desktop.png` ลงวันที่ 2026-10-12 เปิดดูแล้ว | ใช้เข้าใจ shell รุ่นเก่าเท่านั้น ภาพเป็น fixture และไม่ใช่ baseline ปัจจุบัน |
| ภาพที่คัดออก | `.tmp/current_chrome_state.png` ลงวันที่ 2026-10-16 เป็นหน้า TikTok Studio | ไม่ใช้เป็นหลักฐาน OmniCut |
| หน้าจอปัจจุบัน | เครื่องมือ Computer Use ไม่สามารถยืนยัน URL บน Windows และหยุด session | **ยังไม่ได้ตรวจภาพ live, contrast จริง, clipping หรือ keyboard behavior จริง** |
| บริบทโปรเจกต์ | `ARCHITECTURE.md`, `TODO.md`, กฎ UI, font/text, preview/render, testing | ใช้กำหนดขอบเขตและสิ่งที่ต้องรักษา |

การประเมิน: พบสัญญาณเชิง source กระจายหลายชั้น จึงเหมาะกับแผนปรับระบบส่วนควบคุมทั้งชุด แต่ยังไม่ตัดสินว่าทุกหน้าเป็น heavy slop จากภาพจริง ต้องจัดระดับรายหน้าจออีกครั้งเมื่อมี baseline ปัจจุบัน

อัปเดตระหว่างปิดเอกสาร: TODO ล่าสุดระบุว่างาน canonical naming และ Navbar ของ Antigravity ปิดแล้ว โดย Navbar มีการนำแถบ RenderPreflightNotice ใต้ header ออกจากหน้าทำงานด้วย ข้อมูลว่า “ค้าง” ในบันทึกตรวจหมายถึงสถานะเมื่อเริ่มสำรวจ ไม่ใช่สถานะสุดท้าย ให้ตรวจ diff ปัจจุบันอีกครั้งก่อน implementation ตัวเลขผลทดสอบที่เอเจนต์นั้นบันทึกไม่ใช่ผลทดสอบของแผนนี้

### 1.3 ขนาดพื้นที่ที่ต้องจัดการ

| Pattern | จำนวนที่พบ | จำนวนไฟล์ | การตีความที่ถูกต้อง |
|---|---:|---:|---|
| `bg-gradient` / CSS linear หรือ radial gradient | 295 | 56 | แยก gradient ตกแต่ง UI ออกจากสี/เอฟเฟกต์ในชิ้นงาน |
| `transition-all` / `transition: all` | 716 | 85 | ตรวจ property ที่เปลี่ยนจริงก่อนเปลี่ยนเป็นรายการเฉพาะ |
| `font-bold`, `font-black`, `font-extrabold` | 1,907 | 112 | ชี้ความเสี่ยงน้ำหนักข้อความเท่ากันทั้งหน้า ไม่ใช่คำสั่งลบทั้งหมด |
| `text-[6px]` ถึง `text-[11px]` | 1,323 | 98 | แยก label UI ออกจาก time ruler และข้อความใน video preview |
| backdrop blur/filter | 151 | 54 | ประเมินความจำเป็นและขอบเขต compositing |
| `animate-pulse` / `animate-ping` | 55 | 33 | แยกสถานะงานจริงออกจากการเต้นตกแต่ง |

ห้ามใช้จำนวนเหล่านี้เป็นเป้าหมายให้ลดเป็นศูนย์ทั้ง repository เพราะ `SequencePlayer`, inspector และ style preview มีหน้าที่แสดงงานวิดีโอจริงอยู่ด้วย

## 2. ทิศทางการออกแบบที่เสนอ

### 2.1 Direction ห้าบรรทัดตาม Unslop

- **Product:** เครื่องมือสำหรับเจ้าของช่องที่เปลี่ยนข้อมูลสินค้าและวัตถุดิบเป็นคลิปแนวตั้ง แล้วตรวจงาน ส่งออก และติดตามการโพสต์
- **Character:** แม่นยำ กระชับ มีจังหวะของคนตัดต่อ
- **World:** โต๊ะทำงานตัดต่อที่ใช้ดูฟุตเทจ จัดช็อต และส่งงานจริง ใช้สัดส่วนและวัสดุภาพแบบเครื่องมือทำงานโดยไม่จำลองอุปกรณ์ตกแต่ง
- **Moments:** ภาพ preview 9:16 ใน Editor และภาพสินค้าหรือภาพปกจริงในคลังเป็นจุดที่มีรายละเอียดและสีเต็มที่
- **Signature:** ตัวบอกเส้นทางงานของคลิปที่เลือก วางชื่อขั้นปัจจุบันและสิ่งที่ต้องทำต่อจากสถานะจริงในตำแหน่งสม่ำเสมอ

ชื่อทิศทางเพื่อใช้อ้างในเอกสาร: **OmniCut Production Desk** ชื่อนี้เป็นแนวทางออกแบบ ไม่ใช่ชื่อผลิตภัณฑ์ใหม่ และไม่ต้องแสดงใน UI

### 2.2 วิธีทำให้ต่างจาก template ทั่วไป

1. หน้าสินค้าแสดงความสัมพันธ์สินค้า → มุมสคริปต์ → คลิป จากข้อมูลเดิม ให้เห็นงานค้างแทนการวาง KPI ที่ไม่มีผลต่อการตัดสินใจ
2. Editor ให้ภาพแนวตั้งจริงเป็นจุดนำสายตา รายละเอียดของงานอยู่ใน inspector และ timeline ตามที่ผู้ใช้คุ้นเคย
3. Gallery แสดงคลิปตามความพร้อมส่งงาน พร้อมสถานะ QC/ปก/โพสต์ที่แยกความหมายได้
4. ภาษาบนปุ่มบอกงาน เช่น “เปิดตัดต่อ”, “สร้างสคริปต์”, “ส่งออกคลิป” มากกว่าการขายคำว่า AI หรือคำว่า Studio ซ้ำหลายจุด
5. Signature ใช้สถานะที่ระบบมีอยู่ ไม่สร้างคะแนนความสำเร็จ ไม่สร้าง progress เทียม และไม่ให้ผู้ใช้กดข้ามสถานะ

**การทดสอบเอกลักษณ์:** ปิดชื่อ OmniCut แล้วผู้ตรวจควรยังอธิบายได้ว่าเป็นเครื่องมือผลิตคลิปจากสินค้า ไม่ใช่ dashboard รายรับหรือเครื่องมือจัดการทีมที่เปลี่ยนชื่อมา

### 2.3 การใช้สามสกิลเมื่อคำแนะนำต่างกัน

| ประเด็น | แนวทางในแผนนี้ | เหตุผล |
|---|---|---|
| Unslop ให้ quiet chrome; Impeccable เปิดพื้นที่ให้สีมากขึ้น | ส่วนควบคุม neutral ที่ต่างระดับชัด; สีที่มากขึ้นอยู่ในภาพจริงและสถานะที่มีความหมาย | เป็นพื้นผิว Operate ที่ต้องอ่านต่อเนื่อง |
| คำแนะนำ sidebar 240–280px | ใช้ rail 72px ปัจจุบันเป็นฐาน; เสนอแบบมี label ให้พิจารณาภายหลัง | ไม่ยึดขนาดสำเร็จรูปจนกินพื้นที่ Editor |
| ฟอนต์ใหม่ในตัวอย่างสกิล | รักษา family และค่าฟอนต์ที่ผู้ใช้ตั้งไว้; ทำรายการปรับ typography แยกไว้รออนุมัติ | AGENTS ข้อ 10 และ font/text contract มาก่อน |
| UI Pro Max ตอบ `Hero + Features + CTA` จากคำค้นแรก | ไม่ใช้ผลนั้นเป็นโครงหน้า; ค้นใหม่แบบ `style` ได้ `data-dense-dashboard` | คำตอบแรกไม่ตรงงาน Editor ใช้เฉพาะหลัก density/ข้อมูลจากผลใหม่ ไม่คัดทั้งชุด |
| สกิลมี flow สร้าง mockup/ภาพ/วิดีโอ | ทำ brief, wireframe แบบข้อความ และข้อเสนอในเอกสาร | ผู้ใช้ระบุแผนอย่างเดียว จึงไม่มีการสร้าง UI หรือวิดีโอ |

## 3. บันทึกตรวจและปรับแผนครบ 10 รอบ

ทั้ง 10 รอบด้านล่างคือการตรวจและทบทวนแผนคนละมุมที่ทำใน session นี้ ไม่ใช่การอ้างว่าแก้โค้ดหรือทดสอบหน้าจอครบ 10 ครั้ง ทุกข้อเสนอเป็นร่าง และทุกเกณฑ์รับงานเป็นงานของรอบ implementation ภายหลัง

### รอบ 01 — ตรวจผลิตภัณฑ์ งานหลัก และขอบเขต

**หลักฐาน:** `ARCHITECTURE.md`; `frontend/src/App.jsx` ส่วน lazy views และ route rendering; `Sidebar.jsx:18–40`; `frontend/package.json`

**สิ่งที่พบ**

- เมนูหลักปัจจุบันมีสินค้า, Tracker, Editor, Gallery, Assets, Analytics, Settings, Guide
- ระบบมี channel scope, project autosave, durable jobs, QC และเส้นทางส่งต่อมือถือที่มีความหมายจริง
- งานใน working tree มีการปรับ Navbar และ product ingestion พร้อมกับงานเอกสารนี้
- ผู้ใช้ยืนยันให้ตรวจทั้งระบบโดยเน้น Editor กับคลังสินค้า

**สิ่งที่ปรับในแผน:** ใช้โครงสร้างงานและลำดับเมนูเดิมเป็นฐาน แยก navigation ออกจากตัวบอกขั้นตอนผลิต ห้ามใช้เลขเมนูเป็นเหมือน progress ของงานทุกประเภท

**งานที่เสนอ:** ทำ surface inventory ให้ทุกหน้าและ drawer ที่ใช้งานจริงอยู่ใน scope matrix; ระบุ owner ของ channel/project/clip context ให้ชัดก่อนปรับ shell

**เกณฑ์รับภายหลัง:** เข้าแต่ละหน้าแล้วรู้ว่าอยู่ช่องใด ใช้สินค้าหรือโปรเจกต์ใด และย้อนกลับได้ตามพฤติกรรมเดิม; ไม่มี route หายหรือสถานะข้ามขั้น

**ผลตรวจรอบนี้:** ยืนยันขอบเขตได้จาก source; พฤติกรรม end-to-end ยังรอตรวจ live

### รอบ 02 — ตรวจภาพจำและแหล่งกำเนิดความตกแต่ง

**หลักฐาน:** `index.css:27–33, 237–277`; `App.jsx:1250–1252`; `lib/themeManager.js:14–64`; `Sidebar.jsx:115–150`

**สิ่งที่พบ**

- ธีมเริ่มต้นในโค้ดเป็น `glassmorphism` มี orbs สามสีและค่า glare/saturate สูง
- มีธีม obsidian ที่ลดแสงอยู่แล้ว จึงไม่จำเป็นต้องสร้าง theme engine ใหม่
- โลโก้ใน rail เป็น Sparkles บน gradient tile และ active rail มีขอบเรืองแสง
- ภาพ HF เก่ามี sidebar และพื้นที่ทำงานจริง แต่ไม่ใช้ตัดสินสัดส่วนของ build ปัจจุบัน

**สิ่งที่ปรับในแผน:** ต้นเหตุระดับ shell มาก่อนการไล่แต่งแต่ละการ์ด; เสนอ studio neutral เป็นฐานโดยยังรักษา preference เดิมไว้

**งานที่เสนอ:** แยกชั้น background/surface/border/text/accent; เสนอ wordmark หรือ mark แบบแบนจากทรัพย์สินแบรนด์ที่ตรวจพบจริงก่อน ถ้าไม่พบต้องให้ผู้ใช้เลือก ไม่วาดโลโก้ใหม่แล้วถือว่าอนุมัติ

**เกณฑ์รับภายหลัง:** ปิดภาพสินค้าชั่วคราวแล้ว chrome ไม่แย่งจุดเด่น; เปิดภาพแล้วมองสินค้าหรือคลิปก่อนปุ่ม utility; ไม่มี hue gradient/glow ในชุดควบคุมที่ย้ายระบบแล้ว

**ผลตรวจรอบนี้:** พบสัญญาณกระจายหลายชั้นจาก source; การเลือกธีมและแบรนด์ยังเป็นข้อเสนอ

### รอบ 03 — ตรวจสี Token และการตั้งค่าธีม

**หลักฐาน:** `ui/Button.jsx:27–38`; `ui/Badge.jsx:12–28`; `ui/PageHeader.jsx`; `SystemSettings.jsx:419–595`; `index.css:309–415`

**สิ่งที่พบ**

- Button กลางมีหลาย gradient, neon และ colored shadow
- Badge กลางมี variant ตามชื่อสี ไม่ได้บอก intent จึงเสี่ยงใช้สีเดียวกันคนละความหมาย
- แต่ละ theme override glass classes แต่ JSX หลายหน้ามี raw colors ของตัวเอง
- หน้า Settings เปิดให้ปรับกระจกและ orbs อยู่แล้ว การลบ preference จะกระทบผู้ใช้เดิม

**สิ่งที่ปรับในแผน:** มี semantic token contract และ compatibility layer; เปลี่ยนเฉพาะ label/สีบน UI ไม่เปลี่ยน enum หรือค่าที่ backend ใช้

**งานที่เสนอ:** neutral, selection, primary action, success, warning, error, pending/unknown; chart/track palette แยกจาก chrome และไม่ใช้ semantic error กับสี track

**เกณฑ์รับภายหลัง:** ทุก variant มีครบ default/hover/focus/disabled/loading; existing theme ID ยังโหลดได้; ทุก foreground/background คู่ที่ใช้จริงผ่าน contrast ไม่ใช้การเดาจาก hex

**ผลตรวจรอบนี้:** ได้รายการ token ที่ต้องมี; palette ตัวเลขในหัวข้อ 4 เป็นค่าเสนอที่ต้องทดลองกับภาพจริง

### รอบ 04 — ตรวจระยะ ความหนาแน่น และ typography

**หลักฐาน:** `index.css:1–24, 66–82`; `ui/PageHeader.jsx`; `ui/Badge.jsx`; `ProductToClip.jsx:148, 305`; `hooks/usePanelLayout.js:4–18`

**สิ่งที่พบ**

- มี text 9–11px ในหลายส่วน และมี font-bold/black กระจายมาก
- Body ใช้ letter spacing ติดลบ; CSS ยังมี Anuphan จาก Google Fonts และ local face ชื่อเดียวกันที่ map weight 400–700 ไปไฟล์ Bold
- Badge size `sm` ใช้ `text-sm` แต่ `md` ใช้ `text-xs` เป็นลำดับขนาดที่กลับกันใน source
- Editor มี panel width และ layout persistence อยู่แล้ว ไม่ควรแทนด้วย layout ตายตัว

**สิ่งที่ปรับในแผน:** ล็อกฟอนต์เดิมไว้และแยก “สำรวจความเสี่ยง font mapping” ออกจากการแก้ภาพ UI; ปรับระยะและการจัดกลุ่มก่อนคิดเรื่องเปลี่ยนตัวอักษร

**งานที่เสนอ:** spacing 4px grid; ตรวจแถวชนิดเดียวกันให้เท่ากัน; Thai mark clipping; ดูขนาด small/medium ของ component ให้เป็นลำดับเดียวกัน

**เกณฑ์รับภายหลัง:** ไม่เปลี่ยน family/size/weight ของข้อความในคลิป; ปุ่มและแถว UI ที่อนุมัติปรับมีรูปแบบสม่ำเสมอ; ไทย อังกฤษ ตัวเลขและชื่อรุ่นอ่านครบเมื่อ zoom

**ผลตรวจรอบนี้:** พบ source risk จริง; ยังไม่ยืนยันว่าฟอนต์ที่ browser โหลดอยู่เป็น face ใดหรือเกิด clipping จริง

### รอบ 05 — ตรวจไอคอน ข้อความ และลำดับคำสั่ง

**หลักฐาน:** `Sidebar.jsx:18–40, 115–150`; `Topbar.jsx:10–65`; `EditorHeader.jsx:227–241`; `ui/PageHeader.jsx:30–47`

**สิ่งที่พบ**

- มี Lucide อยู่แล้ว จึงใช้ระบบเดียวต่อได้
- Sidebar, Topbar และ PageHeader มีชื่อบริบทซ้ำหลายชั้น; ชื่อไทย/อังกฤษและเลขขั้นตอนผสมกัน
- บางหน้าใช้ Sparkles และป้าย AI เป็นตัวนำ แม้งานหลักคือแก้ไขหรือส่งงาน
- Button กฎโปรเจกต์กำหนด Lucide + กริยาไทย จึงไม่ทำตามคำแนะนำทั่วไปที่ลบ icon จากทุกปุ่ม

**สิ่งที่ปรับในแผน:** glossary หนึ่งชุดและ primary action ตามงาน; ข้อมูล API/โควตา/ค่าใช้จ่าย AI ยังต้องเห็นก่อนเรียกจริง ไม่ซ่อนจนตัดสินใจไม่ได้

**งานที่เสนอ:** ลด badge ที่บอกชื่อหน้าซ้ำ, เปลี่ยนป้าย menu ด้วย mapping ที่ไม่เปลี่ยน ID, tooltip ใช้ได้ทั้ง hover และ focus, icon-only มี accessible name

**เกณฑ์รับภายหลัง:** ปุ่มอ่านแล้วรู้ว่าจะเกิดอะไร; ไม่มี emoji ใช้ตกแต่ง chrome; ชื่อแบรนด์และศัพท์เทคนิคยังใช้ภาษาอังกฤษตามเดิม

**ผลตรวจรอบนี้:** ได้ glossary ร่างในหัวข้อ 6; ยังไม่เปลี่ยนข้อความจริง

### รอบ 06 — ตรวจ Editor ที่เป็นหัวใจของงาน

**หลักฐาน:** `EditorHeader.jsx:180–276`; `EditorShell.jsx:1174–1191, 2148–2156`; `RenderReadinessChip.jsx:57–66, 75–112, 149`; `usePanelLayout.js`

**สิ่งที่พบ**

- Header ล่าสุดแบ่งสามโซน มี SaveStatusChip/ViewToggleGroup/RenderReadinessChip แล้ว แผนเก่าที่บอก “16 ปุ่ม” จึงไม่ใช่ baseline ปัจจุบัน
- `RenderReadinessChip` ใช้ default `coverStatus=null`, report errors/warnings เป็น empty array แล้วคำนวณว่าพร้อมเมื่อไม่มี errors/warnings
- Parent มี local preflight ที่คำนวณจริง แต่ cover unknown และผล asynchronous อื่นยังต้อง trace เพิ่ม จึงไม่สรุปว่าระบบปล่อยเรนเดอร์ผิดจริง
- มีข้อความ “พร้อมเรนเดอร์ 100%” ใน chip ซึ่งเสี่ยงสื่อกว้างกว่าขอบเขตที่ตรวจ
- ค่าปัจจุบัน Asset 260px, Inspector 380px และ panel ย่อ/ขยายได้อยู่แล้ว

**สิ่งที่ปรับในแผน:** รักษาโครงสามโซนล่าสุด; ทำ state semantics ให้ตรงก่อนลดสี; ใช้ panel sizing เดิมเป็นจุดเริ่มต้น

**งานที่เสนอ:** identity/save ทางซ้าย, view controls ตรงกลาง, tools/readiness/render ทางขวา; สี primary ของกลุ่มงานนี้อยู่ที่ Render; pending/unknown ไม่แสดงเป็นผ่าน; viral score เป็นข้อมูลคำแนะนำและมีชื่อ ไม่ลอยเป็นเลขไร้หน่วย

**เกณฑ์รับภายหลัง:** ชื่อโปรเจกต์ยาวไม่ผลัก Render หลุด; ปุ่มยังเข้าถึงเมื่อจอแคบ; ชิปไม่ตีความ unknown เป็น pass; advisory lint ไม่กลายเป็น hard blocker โดยงานออกแบบ

**ผลตรวจรอบนี้:** โครง Header ตรวจจาก source ล่าสุด; สถานะ unknown เป็นประเด็นตรวจ P0 ไม่ใช่คำกล่าวว่าเกิด defect end-to-end แล้ว

### รอบ 07 — ตรวจคลังสินค้า Tracker และคลังคลิปให้ต่อเนื่อง

**หลักฐาน:** `ProductToClip.jsx:148–246, 288, 368–440`; `ContentTrackerHub.jsx:34–41, 380–415`; `ExportGallery.jsx:179–214, 668, 930, 1089–1118`

**สิ่งที่พบ**

- ProductToClip มี selector สินค้า, angle และสถานะจริง แต่มี gradient/ping และ metadata ขนาดเล็กมาก
- Tracker ใช้สี่ phase จริง: scripted/in_production/rendered/posted และมี QC เป็นรายละเอียดของ rendered
- Gallery มีข้อมูลปก, ความคม, caption, posted และ actions หลายแบบ ไม่ควรทำให้ทุกอย่างเป็น badge เท่ากัน
- มีคำเตือนกรณีคลิปยังไม่ได้ผูก Angle จึงต้องรักษาทางออกสำหรับ clip ที่ข้อมูลไม่ครบ

**สิ่งที่ปรับในแผน:** แยก lifecycle, QC readiness, และ background-job progress เป็นข้อมูลคนละแกน โดยไม่เพิ่ม phase enum ใหม่

**งานที่เสนอ:** ชุด row/card ร่วมกันด้วยภาพจริง ชื่อสินค้า รุ่น/รหัสที่แยกได้ สถานะหลัก และ next action; metadata เพิ่มเปิดในรายละเอียด

**เกณฑ์รับภายหลัง:** คลิปไม่มี Angle/ไม่มีปก/รอ QC ไม่ดูเหมือนพร้อมโพสต์; เปลี่ยนมุมหรือกลับจาก Editor แล้วยังคง context และ filter เดิมตามพฤติกรรมที่รองรับ

**ผลตรวจรอบนี้:** ได้การแบ่งข้อมูลระดับคลิป; ไม่เปลี่ยนชื่อสินค้าใน store และไม่ทับงาน ingestion ของ Antigravity

### รอบ 08 — ตรวจการเข้าถึงและภาวะผิดปกติ

**หลักฐาน:** `ui/Input.jsx:16–41, 55–80`; `ui/Modal.jsx`; `editor/HeaderMenu.jsx`; `index.css:785`; `Sidebar.jsx`

**สิ่งที่พบ**

- Input/Textarea มี label และ error ที่มองเห็น แต่ wrapper ไม่ผูก htmlFor/id หรือ aria-describedby ให้อัตโนมัติ ต้องตรวจแต่ละ caller ก่อนสรุปผล DOM
- Modal มี Escape, initial focus และ restore focus แล้ว แต่ใน wrapper ที่อ่านไม่พบ focus trap หรือ inert background
- HeaderMenu มี menu roles และ focus-visible บางจุด ต้องตรวจ Arrow/Home/End และ focus order จริงเพิ่มเติม
- มี reduced-motion rule อยู่แล้ว จึงห้ามเขียนรายงานว่าไม่มีทั้งระบบ
- UI มี safe-area และ touch sizing หลายจุดอยู่แล้ว เป็นของที่ต้องรักษา

**สิ่งที่ปรับในแผน:** รายการตรวจแยก confirmed source gap ออกจาก runtime hypothesis; ให้ loading/error/empty/stale เป็นส่วนหนึ่งของ design system

**งานที่เสนอ:** field association, keyboard menu/dialog, focus ไม่ถูก overlay บัง, error ใกล้ field, no-data ต่างจาก fetch-failed, action สำคัญบอกเหตุผลเมื่อ disabled

**เกณฑ์รับภายหลัง:** ทำงานหลักด้วย keyboard ได้; ไม่ใช้สีอย่างเดียว; screen reader อ่านชื่อ field/error; ปุ่มมือถือแตะได้สะดวกและไม่มี sticky UI ทับ

**ผลตรวจรอบนี้:** source review เสร็จ; accessibility audit ใน browser ยังไม่ได้ทำและไม่รับรอง conformance

### รอบ 09 — ตรวจหน้ารอง มือถือ และต้นทุนการแสดงผล

**หลักฐาน:** `MediaAssetsHub.jsx:498–616`; `AnalyticsHub.jsx`; `MetricKpiCard.jsx`; `SystemSettings.jsx`; `mobile/MobileShell.jsx`; `mobile/TodayScreen.jsx`

**สิ่งที่พบ**

- Assets และ KPI cards มี blur/shadow/หลาย accent ซ้อนกับ shell
- Analytics แบ่งหลาย tab และมีสีรายหมวด จึงต้องแยก chart series จริงออกจากสีตกแต่ง tab
- ระบบมีมือถือสองบริบท: desktop shell ที่ responsive และ MobileShell เฉพาะทาง ไม่ควรรวม nav ด้วยการแทนทั้งชุด
- TodayScreen มีงานต้องทำและสถานะจริงอยู่แล้ว เหมาะกับ task-first UI โดยไม่สร้าง dashboard ใหม่
- ยังไม่มี profile วัด FPS/LCP/memory ในรอบนี้ จึงไม่อ้างว่าลด blur แล้วเร็วขึ้นกี่เปอร์เซ็นต์

**สิ่งที่ปรับในแผน:** ให้มือถือเป็น flow ทำงานแบบสั้น; Desktop Editor ยังคงเครื่องมือเต็ม; กำหนด performance budget เป็นเป้าหมายที่ต้องวัด

**งานที่เสนอ:** thumbnail lazy-load ตาม viewport, ไม่ autoplay ทุก card, chart ใช้สีตาม series, utility states ทนเน็ตขาด; preserve mobile keyboard/safe-area/back behavior

**เกณฑ์รับภายหลัง:** ไม่มี page-level horizontal overflow ยกเว้น timeline/table ที่ตั้งใจเลื่อน; เปิด modal บนมือถือแล้ว action ยังแตะได้; no unnecessary repeated paint จาก ambient decoration

**ผลตรวจรอบนี้:** ครอบคลุมหน้ารองในเชิง source และกำหนด matrix สำหรับพิสูจน์ ไม่อ้างผลวัดประสิทธิภาพ

### รอบ 10 — ตรวจย้อนแผน ความขัดแย้ง และลำดับส่งมอบ

**หลักฐาน:** กฎ font/text, preview/render parity, testing; `TODO.md`; แผน Navbar ของ Antigravity; ข้อค้นพบรอบ 01–09 และแผนรายหน้าด้านล่าง

**สิ่งที่ทบทวนและปรับ**

- เลิกใช้เอกสาร Navbar เก่าเป็นข้อเท็จจริงเรื่องจำนวนปุ่ม แล้วอ้าง Header ล่าสุดที่แบ่งสามโซน
- เปลี่ยนการกล่าว “ชิปเรนเดอร์ผิด” เป็น “มี source risk เมื่อข้อมูลยังไม่ครบ ต้อง trace/พิสูจน์ก่อนแก้”
- ไม่ยึด sidebar กว้างจากสกิล; รักษา rail 72px เป็นฐานเพื่อไม่เสียพื้นที่ภาพ 9:16
- ข้อเสนอ typography ถูกกั้นเป็นรายการรออนุมัติ ไม่ถือว่าสั่ง redesign เท่ากับสั่งเปลี่ยนฟอนต์ในคลิป
- ตัดผลค้นแบบ landing page, ภาพ TikTok Studio และ fixture เก่าออกจากหลักฐานตัดสิน live UI
- กำหนด phase ทำงานเริ่มจาก baseline และ semantic states แล้วจึง migrate visual ทีละ surface
- แยก “ตรวจแผนครบสิบรอบ” ออกจาก “ทดสอบ implementation ผ่าน” และบันทึกข้อจำกัดท้ายเอกสาร

**งานที่เสนอ:** ใช้ implementation gates ในหัวข้อ 8; ต้องมี visual baseline ใหม่และล็อก direction ก่อนแก้ application

**เกณฑ์รับเอกสารรอบนี้:** มีสิบรอบจริงพร้อมหลักฐานและผลต่อแผน; มี scope รายหน้าทั้งระบบ, file map, priority, state matrix, rollback และจุดตัดสินใจ; ไม่สร้าง UI/artifact วิดีโอ

**ผลตรวจรอบนี้:** แผนพร้อมใช้คุยทิศทางและแตกงาน; การออกแบบและความสำเร็จของ implementation ยังไม่ถูกอนุมัติหรือพิสูจน์

## 4. ระบบภาพและองค์ประกอบกลาง

### 4.1 Palette ที่เสนอสำหรับทดลอง

นี่เป็นสเปกของร่างทิศทาง ไม่ใช่ค่าที่เปลี่ยนแล้ว และไม่ใช้กับตัวอักษรหรือสีภายในวิดีโอ

| Role | ค่าเสนอ | หน้าที่ |
|---|---|---|
| Canvas | `#141415` | พื้นหลังงานทั่วไป |
| Rail/deep surface | `#0F0F10` | แยก navigation และขอบเขตพื้นที่ |
| Panel | `#19191B` | pane, card, toolbar |
| Raised/hover | `#232325` | input, hover, selection พื้นบาง |
| Primary text | `#EDEDED` | ข้อมูลหลักและคำสั่ง |
| Secondary text | `#A1A1A6` | คำอธิบายและ metadata ที่ยังต้องอ่าน |
| Muted text | `#85858B` | ใช้หลังตรวจ contrast กับ surface จริง |
| Accent | `#25F4EE` | คงสีที่มีในโค้ดเป็น candidate สำหรับ selection/primary แบบจำกัด |
| Text on accent | `#101415` | ตัวอักษรเข้มบน accent สว่าง; ตรวจ contrast จริงก่อนใช้ |
| Success | `#4CC38A` | เฉพาะสิ่งที่ผ่านหรือสำเร็จจริง |
| Warning | `#F2C166` | สิ่งที่ต้องพิจารณา |
| Error | `#F0747A` | ข้อผิดพลาดและการกระทำที่มีผลเสีย |
| Unknown/pending | neutral + ข้อความ | ไม่ใช้สีเขียวแทนข้อมูลที่ยังไม่ทราบ |
| Divider | ขาว 8% เป็นค่าเริ่มต้น | เส้นแบ่งตกแต่ง; ขอบ control สำคัญต้องผ่าน non-text contrast แยก |

ไม่ถือสี TikTok บนปุ่มปัจจุบันเป็นเหตุผลให้ใช้ gradient ของแพลตฟอร์มกับทุกคำสั่ง โลโก้และ asset แบรนด์จริงไม่ดัดแปลงโดยอัตโนมัติ

Theme strategy: ทดลอง base จากความสามารถ obsidian ที่มีอยู่ แล้วประเมินว่าจะ map token เข้าธีมเดิมหรือเพิ่ม version ของ theme contract; ไม่ลบ `glassmorphism/cyberpunk/slate` และไม่ reset localStorage ใน migration

### 4.2 ระยะและขนาดโครงสร้าง

| รายการ | ค่าเริ่มต้นเสนอ | หมายเหตุ |
|---|---:|---|
| Spacing scale | 4/8/12/16/20/24/32/40/48px | 2px ใช้ optical adjustment ภายใน control เมื่อจำเป็น |
| Desktop rail | 72px | ยึดปัจจุบัน; expanded navigation เป็นทางเลือกแยก |
| Header | 56–64px | Editor อาจ compact ตามพื้นที่จริง |
| Page gutter | desktop 24px, tablet 20px, mobile 16px | หน้า Editor ใช้พื้นที่เต็มตาม pane model |
| Panel padding | 16px | card เนื้อหา 20–24px ตาม density |
| Desktop row | 36–40px | row ที่มีเนื้อหาหลายบรรทัดไม่บังคับความสูงจนตัดไทย |
| Touch target | อย่างน้อย 44×44px เป็นเป้าหมายผลิตภัณฑ์ | คง pointer-coarse rules เดิม |
| Control radius | 8px | ไม่บังคับ pill ทุกปุ่ม |
| Card radius | 12px | ใช้ inner radius = outer − padding เมื่อเหมาะกับโครงจริง |
| Dialog radius | 16px desktop; mobile sheet ตาม platform | ไม่เปลี่ยน gesture โดยงาน theme |
| Icon | 16/18px ใน control; 20px navigation | บทบาทเดียวกันใช้ขนาด/stroke เดียวกัน |

ตัวเลขเหล่านี้เป็นจุดทดลอง ไม่แทน min/max ใน `usePanelLayout.js` โดยอัตโนมัติ และไม่ใช้ `max-width` กลางแบบหน้า landing กับ Editor

### 4.3 Typography: รักษา contract ก่อน

- รอบปรับ chrome ระยะแรกไม่เปลี่ยน family/size/weight/line break/ตำแหน่งของข้อความในคลิป, cue, Hook, ASS หรือ Canvas
- UI ใช้ family และ preference ปัจจุบันต่อ; สำรวจ computed font แยกก่อนแตะ `@font-face` เพราะชื่อเดียวกันครอบคลุมหลายบริบท
- แยกข้อเสนอปรับ UI typography ให้ผู้ใช้อนุมัติชัดเจน: body 14–16px, meta 12–13px, UI title 20–24px, weight หลัก 400/500 และ emphasis 600 เป็น candidate ไม่ใช่ค่าที่ใช้ทันที
- หากอนุมัติปรับ UI typography ให้ใช้ namespace เฉพาะ chrome หลีกเลี่ยง selector สืบทอดเข้า preview และเนื้อหาที่ต้อง parity
- ทดสอบสระบน/ล่างและวรรณยุกต์ในชื่อสินค้า ปุ่ม ข้อผิดพลาด; ไม่ใช้ negative tracking กับไทยขนาดเล็ก
- ตัวเลข count/เวลาใช้ tabular figures ถ้า face รองรับ; timecode, frame count และ duration ต้องคงความหมายและรูปแบบเดิม
- ปรับ weight hierarchy หลัง spacing/copy/layout ตกลงแล้ว ไม่ใช่สั่งแก้ 1,907 จุดจาก regex

### 4.4 Motion และรายละเอียด

- Micro feedback 120ms; menu/popover 160ms; dialog 200ms เป็นค่าเสนอ; easing `cubic-bezier(0.2, 0, 0, 1)`
- Transition เฉพาะ color/background-color/border-color/opacity/transform ตามแต่ละ component
- Menu ขยับขึ้นได้ประมาณ 4px พร้อม fade; hover card เปลี่ยน surface ไม่ขยายภาพทั้งการ์ด
- ไม่มี loop บนสถานะสำเร็จหรือป้ายที่ไม่ใช่งานสด; spinner ทำงานเฉพาะ request/job จริง
- ใช้ progress จริงเมื่อมีข้อมูล; ถ้าไม่มี total ใช้ indeterminate พร้อมชื่อขั้น ไม่สร้างเปอร์เซ็นต์
- รักษา reduced-motion ที่มีอยู่ และตรวจ third-party/canvas/JS animation แยกจาก CSS
- ห้ามเอานโยบาย motion ของ chrome ไปปิดเอฟเฟกต์ที่เป็นตัวอย่างงานวิดีโอหรือเปลี่ยน renderer

### 4.5 Component contract ที่ต้องมี

| Component | สิ่งที่ต้องออกแบบร่วมกัน | ความเสี่ยงที่ต้องคุม |
|---|---|---|
| Button | primary/secondary/ghost/danger, loading, disabled, icon-only | primary หนึ่งต่อกลุ่มงาน; disabled บอกเหตุผลเมื่อจำเป็น |
| Input/Select/Textarea | label, required, helper, invalid, loading option | htmlFor/id, describedby, ไม่ใช้ placeholder แทน label |
| Badge/Status | lifecycle, QC, job, advisory แยกชื่อและระดับ | อย่า map ตามชื่อสีจนความหมายปะปน |
| PageHeader | title, context, actions, optional filter row | ตัด title/badge ที่บอกซ้ำ; ไม่ซ่อน channel สำคัญ |
| Product/Clip row | thumbnail, identity, state, next action, overflow | ชื่อยาวไม่กิน action; แยก selection/focus |
| Modal/Drawer/Menu | keyboard, return focus, nested overlay, scroll | Escape ไม่ปิดหลายชั้นพร้อมกัน; focus ไม่หลุด |
| Toast/Inline alert | success/error/progress, persistence, action | error สำคัญไม่หายก่อนอ่าน; screen reader ไม่ประกาศซ้ำทุก tick |
| Empty/Loading/Error | initial empty, filter empty, offline, stale | fetch failed ไม่แสดงว่าไม่มีสินค้า |

## 5. แผนรายหน้าจอและโครงสร้างงาน

### 5.1 Shell และ navigation

ใช้ rail 72px ปัจจุบันและลำดับเมนูเดิมก่อน ลดสีและกรอบที่แย่งเนื้อหา เพิ่ม accessible labels และ focus tooltip; การเปิดเมนูแบบมีข้อความเป็นข้อเสนอทดลอง ไม่ใช่ข้อบังคับเริ่มต้น

Topbar แสดงชื่อหน้า, channel และบริบทที่จำเป็นเท่านั้น PageHeader ในเนื้อหามีหน้าที่ถือ action/filter ไม่ต้องทวนชื่อ Studio/ชื่อหน้า/หมายเลขเต็มชุด หาก title จำเป็นทั้งสองตำแหน่งให้กำหนดคนละระดับอย่างชัดเจน

ข้อสำคัญจากโค้ด: `App.jsx` ซ่อน Topbar เมื่อเป็น Editor อยู่แล้ว จึงไม่วางแผน “ลบ Topbar ซ้ำใน Editor” จากสมมติฐานผิด

### 5.2 คลังสินค้าและการสร้างคลิป — P1

โครงตามส่วนที่มีอยู่: แถวบริบท/คำสั่ง → เลือกสินค้า → ข้อมูลสินค้าและมุมสคริปต์ → คำสั่งไปขั้นถัดไป คงลำดับเนื้อหาหลัก และไม่ย้ายส่วนทั่วหน้าโดยไม่มีการยืนยัน

- แผงเลือกสินค้า: รูปจริง, ชื่อสั้นที่อ่านแยกรุ่นได้, รหัส, จำนวนงานค้างจากข้อมูลจริง
- เนื้อหาหลัก: มุมสคริปต์เป็นรายการที่เลือกอ่านได้; เนื้อหาเต็มอยู่ในพื้นที่ review ไม่ย่อจนเหลือแต่ badge
- Primary เปลี่ยนตามบริบทที่มีจริง เช่น “สร้างสคริปต์” หรือ “เปิดตัดต่อ”; ไม่ให้ทุก row ใช้ gradient button
- Technical detail ของ scraper/provider อยู่ในรายละเอียดเมื่อมีปัญหาหรือต้องตัดสินใจเรื่องโควตา
- ชื่อสินค้าใช้ผล canonical naming ปัจจุบันจากงานอีกเอเจนต์ UI ต้องรองรับชื่อยาวและเปิดดูเต็มได้ ไม่ตัดชื่อใน store ซ้ำ
- ตรวจกรณีไม่มีรูป, ไม่มี raw, ไม่มีสคริปต์, กำลังสร้าง, สร้างไม่สำเร็จ, filtered empty, เลือกหลายรายการ

### 5.3 ห้องตัดต่อ — P0/P1

แผนผังนี้อธิบายการจัดลำดับงาน ไม่ใช่ HTML ใหม่

```text
rail | channel / project / save | view controls | tools / readiness / Render
     | asset pane              | preview 9:16  | inspector ของสิ่งที่เลือก
     |------------------------- transport / timecode --------------------|
     |------------------------------ timeline --------------------------|
```

- ใช้ Header สามโซนล่าสุด ปรับน้ำหนัก/ช่องว่าง/การล้นโดยไม่รื้อ feature
- Preview เป็นจุดมีสีเด่น; surrounding matte neutral ลดแสงรบกวนการประเมินสีคลิป
- Inspector แสดง identity ของสิ่งที่เลือกและกลุ่มค่าที่ใช้จริง ไม่ทำทุก subsection เป็น card หนาหลายชั้น
- Timeline คง clip colors/track semantics, ruler, waveform และ selection ที่จำเป็นต่อการตัดต่อ
- ตรวจความหมายของ focus mode, panel toggle และ reset layout โดยไม่ reset ค่าผู้ใช้ระหว่างเปลี่ยน theme
- AI dock เป็นเครื่องมือหนึ่ง: ใช้คำสั่งชัด มีสถานะ/ต้นทุน/การอนุมัติที่เดิมกำหนด ไม่มี glow ทำให้ดูเหมือน primary ตลอดเวลา
- Readiness แสดงชื่อรายการที่ตรวจจริง; ข้อมูลไม่ครบ = “ยังตรวจไม่ครบ” หรือ “กำลังตรวจ”; ไม่บอก “100%” โดยไม่มีขอบเขต
- Render button ต้องอ่านได้ใน viewport แคบและชื่อโปรเจกต์ยาว; ปุ่ม options ไม่ใช่ช่องทางเดียวของการเริ่ม render
- ไม่แก้ `SequencePlayer.jsx`, subtitle engine หรือ save/render payload เพื่อทำสี chrome

### 5.4 Tracker — P1

- คงสี่ phase เดิมและลำดับเดิม; QC เป็นรายละเอียดภายใน rendered ไม่ใช่ phase ใหม่
- Column header ใช้ชื่อ phase + จำนวน + คำอธิบายสั้นเฉพาะจำเป็น
- Card แสดง thumbnail, product/angle, stage และคำสั่งหลัก; จำนวน metadata ที่เห็นปรับตามพื้นที่
- ถ้ารายการมาก ใช้ scroll/container policy ที่มองเห็นตำแหน่งชัดก่อนพิจารณา virtualization จากการวัด
- ไม่เพิ่ม drag-and-drop เปลี่ยนสถานะและไม่เปลี่ยน logic `onStatusChange` ด้วยเหตุผลจัดหน้าตา
- “พร้อมโพสต์” ต้องไม่เกิดจากมี MP4 เพียงอย่างเดียว ถ้า workflow เดิมยังต้อง QC หรือเตรียม package

### 5.5 Export Gallery และการส่งงาน — P1

- ให้ภาพปก/คลิปจริงเด่นพร้อม duration/identity ที่อ่านได้
- Card ใช้สถานะหลักหนึ่งชุด; แยก QC, ปก, sharpness และ posted ในรายละเอียดที่เปิดดูได้
- รายละเอียดเป็นพื้นที่ตรวจคลิปและส่งต่อ: preview, metadata สำคัญ, caption จริง, cover, download/post actions
- การคัดลอก caption ที่ไม่มี Angle ต้องอธิบายสิ่งที่ขาดและเปิดเส้นทางผูกข้อมูลเดิม ไม่แต่ง caption ใหม่เพื่อเติมช่องว่าง
- QR/mobile handoff บอกปลายทางและข้อมูลที่ส่ง; scheduled, downloaded และ posted ใช้คนละข้อความ
- ไม่เปลี่ยนงานที่โพสต์แล้วเป็นงาน editable โดยการเอา badge หรือ disabled style ออก

### 5.6 Media Assets และ Product Library — P2

- Filter/scoping อยู่เหนือรายการที่มีผล; preview เล่น/หยุดและ selection อ่านออก
- ภาพใช้ crop ที่เหมาะกับสินค้าหรือชนิด asset; ไม่ zoom/crop จนตัวสินค้าเสียรูป
- จำนวนและ metadata เป็นข้อความรอง ไม่ใช้ pill สีทุกจุด
- เสียงมี play state ที่สัมพันธ์กับไฟล์ที่เล่นจริง หยุดเสียงเดิมเมื่อสลับตามพฤติกรรมที่ระบบรองรับ
- แยก global shared assets, product-scoped raw และ generated project media ด้วย label ที่ใช้ตัดสินใจได้
- ห้ามใช้รอบปรับ UI ลบ/ย้าย/เขียนทับ `01_Raw/` หรือ `02_Assets/`

### 5.7 Analytics — P2

- คง tab และข้อมูลที่มีจริง เลือก chart หลักตามคำถามของ tab ไม่ทำทุก panel น้ำหนักเท่ากัน
- KPI แสดง label/value/unit/ช่วงเวลา และสิ่งที่เปรียบเทียบถ้ามี; ไม่สร้าง trend เมื่อไม่มีข้อมูล
- สี chart ใช้เพื่อแยก series จริง; selection/tooltip มี label และไม่พึ่งสีอย่างเดียว
- ค่าไม่มีข้อมูลแสดง “ยังไม่มีข้อมูล”; ศูนย์คือศูนย์; error คือ error
- ไม่เพิ่ม sparkline/กราฟตกแต่งในทุก stat card
- ผลงาน TikTok ไม่เท่ากับจำนวนการผลิต และ token ไม่เท่ากับต้นทุนจริงถ้าไม่มีข้อมูลราคา

### 5.8 Settings, Guide, Login และ utility — P2/P3

- Settings แบ่งกลุ่มตามที่มีอยู่และสโคปค่าตั้ง: interface/channel/render/provider/security ให้ผู้ใช้รู้ว่าค่าไหนมีผลต่อคลิป
- Appearance แสดงตัวอย่าง chrome ที่ไม่ชวนให้คิดว่ากำลังเปลี่ยน output; preference เดิมยังอ่านกลับได้
- คำอธิบาย glass/orbs ที่เป็นการตลาดทบทวนได้ แต่ยังต้องมีทางเข้าค่าตั้งเดิมตาม compatibility policy
- Guide เริ่มจากงานที่ต้องทำและผลลัพธ์ที่เห็นจริง ลิงก์ชื่อปุ่มตรงกับ glossary
- Login/session expired แสดงสิ่งที่ต้องทำโดยไม่เลียนแบบ marketing hero และไม่เผยรายละเอียด credentials
- ActivityCenter: queued/running/failed/finished ตาม backend; แยก actionable failure จาก notification ทั่วไป
- ScheduleAgenda: วันที่ เวลา timezone และ receipt ชัด; การตั้งเวลาไม่ใช้คำว่าโพสต์แล้ว

### 5.9 HyperFrames, Gadget Media และ approval surfaces — P2

- รักษา brief → revision → acceptance → render → QC → finalize ตาม workflow ที่มีอยู่
- AI action ระบุว่าเริ่มคำขอใหม่ ใช้ provider ใด และมีขอบเขต/โควตาอะไรตามข้อมูลจริง
- Revision, approved master และ exported artifact เป็น identity คนละอย่าง ไม่รวมเป็น badge “สำเร็จ”
- ส่วนที่เป็น preview/poster/composition ไม่รับกฎห้าม gradient หรือเปลี่ยนฟอนต์ของ chrome โดยอัตโนมัติ
- Agent approval card รักษาการอนุมัติและชื่อผลกระทบ; ไม่เปลี่ยนปุ่มอนุมัติเป็น default action ที่กดพลาดง่าย

### 5.10 มือถือและ tablet — P1/P2

- Responsive desktop shell กับ MobileShell เฉพาะทางคงเส้นทางของตัวเอง ไม่เปลี่ยน tab ID เพื่อทำหน้าตาเหมือนกัน
- Today → สร้าง/ตรวจ/ส่งงาน ใช้ข้อมูลและคำสั่งเดิม ลดคำอธิบายซ้ำก่อนลดเนื้อหาจำเป็น
- Bottom nav สูงพอและ safe-area ถูกต้อง; มือถือเปิด keyboard แล้ว field/error/submit ยังมองเห็น
- Editor จอแคบใช้ pane/tab/focus mode ที่รองรับ ไม่บีบ desktop สี่ pane ให้ text เล็กลงทั้งชุด
- เพิ่มทางเลือกควบคุมที่ไม่พึ่ง hover; ปิด sheet ได้ด้วยปุ่มและ back/Escape ตามแพลตฟอร์ม ไม่บังคับ drag
- กำหนด viewport matrix: 360×800, 390×844, 768×1024, 1024×768, 1366×768, 1440×900, 1920×1080
- ตรวจ 200% browser zoom, compact/default UI scale และชื่อยาวพร้อมกันโดยแยกกรณีที่ระบบตั้งใจให้ scroll

## 6. สถานะ ข้อความ และข้อมูล

### 6.1 สถานะที่ต้องใช้คนละความหมาย

| แกนข้อมูล | ตัวอย่าง | กฎการแสดง |
|---|---|---|
| Lifecycle | scripted, in_production, rendered, posted | จาก record/receipt ที่ระบบกำหนด ไม่ใช่เลือกสีแล้วเปลี่ยน stage |
| QC/readiness | ยังไม่ตรวจ, กำลังตรวจ, ผ่าน, เตือน, ไม่ผ่าน, ข้อมูลไม่ครบ | บอกขอบเขตที่ตรวจ ไม่เรียกทุกอย่างว่า “พร้อม” |
| Background job | queued, running, cancel requested, cancelled, failed, finished | ใช้ state backend จริงและไม่สมมติว่า cancel สำเร็จทันที |
| Save | dirty, saving, saved, failed | คง revision fencing; saved ไม่เท่ากับ rendered |
| Connectivity | online, offline, reconnecting, stale | Offline ไม่แปลว่างานที่ server หยุดแน่นอน |
| Publication | prepared, scheduled, handed off, observed published | ข้อความตามหลักฐานจริง ไม่ map เป็น posted ก่อนมีการยืนยัน |

### 6.2 Glossary ร่าง

| จุดใช้งาน | ชื่อที่เสนอให้ทดลอง | เงื่อนไข |
|---|---|---|
| `สินค้า → คลิป` | สินค้าและสคริปต์ | route ID `flow` คงเดิม |
| `แทร็กเกอร์ 4 เฟส` | ติดตามการผลิต | ไม่เปลี่ยนสี่ phase |
| `ตัดต่อ & สร้างคลิป` | ห้องตัดต่อ | ไม่เปลี่ยนชื่อผลิตภัณฑ์ |
| `Export Gallery` | คลังคลิป | ปุ่ม export ภายในยังใช้ศัพท์ให้สม่ำเสมอ |
| `Media Assets Hub` | คลังวัตถุดิบ | ต้องแยก raw/shared/generated ในเนื้อหา |
| `AI Agent` บนปุ่ม | เปิดผู้ช่วย | แสดง AI/provider/โควตาชัดใน dock ก่อนเริ่มคำขอ |
| `พร้อมเรนเดอร์ 100%` | ผ่านรายการตรวจที่จำเป็น | ใช้ได้ต่อเมื่อทราบผลครบ และต้องไม่สื่อรับประกันผลโพสต์ |
| Error ทั่วไป | โหลดรายการไม่สำเร็จ + ลองอีกครั้ง | คงข้อมูลเก่าและระบุเวลาอัปเดตเมื่อมี |

ข้อความเหล่านี้เป็น UI draft เท่านั้น ห้ามใช้เพื่อ rewrite script/caption/ชื่อแบรนด์/ชื่อรุ่นหรือข้อความใน export

### 6.3 State coverage ขั้นต่ำต่อหน้าสำคัญ

| หน้า | ต้องมีกรณีสำหรับออกแบบและตรวจ |
|---|---|
| สินค้า | empty, filtered empty, loading, partial item, long title, scraper error, bulk selection |
| Editor | no project, loading, dirty, saving, save failed, render pending/running/failed, posted locked, cover unknown |
| Tracker | empty phase, many cards, QC pending, stale export, orphan reference, action disabled |
| Gallery | no exports, unbound clip, no cover/caption, posted, handoff pending, download error |
| Assets | missing thumbnail, unsupported preview, audio playing, upload pending/failed, permission denial |
| Analytics | zero, no data, unavailable period, stale provider, chart empty/error |
| Mobile | offline, keyboard open, narrow screen, safe-area, interrupted upload, back closes sheet |
| AI/approval | queued, generating, cancellation pending, provider failure, revision ready, awaiting approval |

## 7. แผนดำเนินงานและไฟล์ที่เกี่ยวข้อง

อัปเดต 2026-11-08 · ดำเนินการโดย: Codex (GPT-6.1-sol): มี [แผนปฏิบัติการรายเฟสและการเลือกโมเดล](PLAN_OMNICUT_UNSLOP_PHASE_RUNBOOK_20261108.md) แล้ว โดยแตก phase กว้างด้านล่างเป็น 10 เฟส 00–09 พร้อม scope, dependency, output, gate และ prompt ส่งงานให้ Terra/Gemini แต่ละรอบ ให้ใช้ runbook นั้นสำหรับลำดับลงมือ ส่วนเอกสารนี้ยังเป็นแหล่งหลักของ audit, direction และข้อจำกัด

### 7.1 ลำดับ phase ภายหลังอนุมัติ

| Phase | งาน | Output ที่ต้อง review | ประตูผ่าน |
|---|---|---|---|
| 0 | ตรวจ baseline ปัจจุบัน + scope/brand/font decision | desktop/mobile captures, state inventory, pinned constraints | ผู้ใช้เลือก direction จากหลักฐานปัจจุบัน |
| 1 | Trace unknown/readiness/save semantics และตรวจ a11y shared controls | state table + แผนแก้จุดที่พิสูจน์ว่ามีปัญหา | ไม่แสดง pass โดยไม่มีผลตรวจ; UI text ตรง contract |
| 2 | Semantic tokens + Button/Input/Badge/PageHeader/Menu/Dialog | component states และ compatibility mapping | contrast/keyboard/theme preference ผ่าน |
| 3 | Shell + Editor + สินค้า เป็น pilot | ภาพก่อน/หลังและ task walkthrough | preview/render content คงเดิม; primary action ชัด |
| 4 | Tracker + Gallery | เดินงานต่อจาก pilot ได้โดยไม่หลุด context | stage/QC/publication ไม่ปะปน |
| 5 | Assets + Analytics + Settings + Guide + utility + specialized studios | surface coverage ครบ | ไม่มีหน้าหลุดระบบ token โดยไม่มีเหตุผล |
| 6 | Mobile/tablet + edge cases + regression + handoff | matrix ผลจริง + accepted design documentation | ไม่มี blocker และมี rollback point |

ข้อเสนอเรื่อง effort: ให้ประเมินหลัง Phase 0 เพราะยังไม่เห็น live UI ปัจจุบัน ไม่ให้ตัวเลขวันหรือเปอร์เซ็นต์เร็วขึ้นที่ไม่มี baseline

### 7.2 File map สำหรับแตกงาน

| กลุ่ม | ไฟล์หลัก | วิธีเข้าทำงาน |
|---|---|---|
| Tokens/theme | `frontend/src/index.css`, `lib/themeManager.js`, `SystemSettings.jsx` | จำกัด chrome scope; migration ของ storage เขียนแยกและไม่ reset preference |
| Primitives | `components/ui/Button.jsx`, `Input.jsx`, `Select.jsx`, `Badge.jsx`, `PageHeader.jsx`, `Modal.jsx`, `Toast.jsx` | ทำ component state inventory ก่อนเปลี่ยน class กลาง |
| Shell | `App.jsx`, `Sidebar.jsx`, `Topbar.jsx`, `context/ChannelContext.jsx` | เปลี่ยน presentation; channel behavior ต้องคงเดิม |
| Editor chrome | `editor/EditorHeader.jsx`, `ProjectSelector.jsx`, `HeaderMenu.jsx`, `SaveStatusChip.jsx`, `ViewToggleGroup.jsx`, `RenderReadinessChip.jsx`, `RenderButton.jsx` | ใช้ผลงาน Navbar ล่าสุดเป็นฐาน; ประสานเจ้าของไฟล์ก่อนแก้ |
| Editor panes | `editor/AssetPanel.jsx`, `Inspector.jsx`, `Timeline.jsx`, `hooks/usePanelLayout.js` | ไม่เปลี่ยน coordinates/timeline math/persisted layout เพื่อการตกแต่ง |
| สินค้า/Tracker | `ProductToClip.jsx`, `ContentTrackerHub.jsx` | ใช้ canonical title จากงาน ingestion; คง status IDs |
| ส่งงาน | `ExportGallery.jsx`, `ScheduleAgenda.jsx`, `ActivityCenter.jsx` | คง package identity, publication evidence และ cancellation flow |
| Assets/Analytics | `MediaAssetsHub.jsx`, `analytics/AnalyticsHub.jsx`, `analytics/components/MetricKpiCard.jsx`, chart/tab components | ย้าย surface token โดยไม่เปลี่ยนข้อมูลหรือ invent metric |
| Specialized | `hyperframes/HyperFramesHub.jsx`, `gadget-media/*`, `agent/*` | เฉพาะ surrounding UI; คง accepted revision/master |
| Mobile | `mobile/MobileShell.jsx`, `TodayScreen.jsx`, Intake/Review/Post/Library และ responsive Sidebar | คง route/history/keyboard/safe-area behavior |
| Contract-sensitive | `SequencePlayer.jsx`, `scripts/subtitle_engine.py`, serializer, caption/font defaults | **อยู่นอกงาน chrome; ถ้าจำเป็นต้องแตะ ให้เปิด scope เฉพาะและผ่าน parity gate** |

ให้ใช้ path เทียบจากรากโปรเจกต์ใน implementation ไม่ hardcode drive; ไม่แก้ `frontend/dist` โดยตรง สร้างจาก source ตามขั้นตอน build ของรอบที่ได้รับอนุญาต

### 7.3 Priority backlog

| ID | ระดับ | รายการ | หลักฐาน/การพึ่งพา |
|---|---|---|---|
| U01 | P0 ตรวจ | unknown readiness อาจแสดงผ่าน | ต้อง trace report completeness + cover policy ก่อนแก้ behavior |
| U02 | P0 ป้องกัน | style สืบทอดกระทบ font/preview/render | แยก chrome namespace และล็อก sensitive files |
| U03 | P1 | ปุ่มกลาง gradient/neon และ intent ไม่สม่ำเสมอ | เริ่ม Button variants ก่อน callers |
| U04 | P1 | glass/orbs/glare ทำให้หลายชั้นแข่งกัน | theme compatibility ก่อน shell migration |
| U05 | P1 | label/field/error association และ dialog focus | ตรวจ caller/DOM ก่อนตัดสิน; แก้ semantic controls ร่วมกับ visual |
| U06 | P1 | UI text เล็กและน้ำหนักสูงหลายระดับ | สำรวจ computed font; typography ต้องอนุมัติแยก |
| U07 | P1 | Editor context กับ Render แข่งพื้นที่ | ใช้ Header สามโซนล่าสุด + viewport tests |
| U08 | P1 | Product/angle/state/action hierarchy | รอข้อสรุป naming ที่กำลังทำคู่ขนาน |
| U09 | P1 | QC/lifecycle/posting แสดงน้ำหนักเท่ากัน | state mapping ร่วม Tracker/Gallery |
| U10 | P2 | transition-all/pulse/blur กระจาย | จัด intent ก่อน mechanical cleanup |
| U11 | P2 | tab/icon colors และ KPI chrome หนา | คง data-series semantics และ units |
| U12 | P2 | responsive กับ MobileShell ต่างบริบท | matrix แยกเส้นทาง; ไม่รวม nav ID |
| U13 | P3 | Guide/Settings copy และ specialized surface drift | ทำหลัง glossary/components stable |

## 8. เกณฑ์ตรวจรับและแผนพิสูจน์ผล

### 8.1 หลักฐานก่อนเริ่มลงมือ

1. เก็บภาพ build ปัจจุบันของทุกหน้าหลักและ state สำคัญ พร้อมวัน/commit/working-tree fingerprint, channel fixture และ viewport
2. ใช้ข้อมูลทดสอบที่แยกจากข้อมูลจริง ไม่เรียก paid TTS/AI ไม่เริ่ม render/post เพื่อถ่าย UI
3. เก็บ temporary screenshots ใน `.tmp/` เท่านั้น หากต้องเก็บหลักฐานระยะยาวให้ขอขอบเขตเอกสารที่เหมาะสมและไม่ทิ้ง probe assets ใน production folders
4. วัด task baseline: หาปุ่มถัดไป, เปิดโปรเจกต์เดิม, เข้าใจว่าทำไมยัง render/post ไม่ได้; บันทึกค่าจริงก่อนตั้ง target เปรียบเทียบ
5. ใช้ baseline ปัจจุบันตัดสิน light/heavy/no-slop รายหน้า; หน้าที่ออกแบบดีแล้วทำเฉพาะช่องว่างที่พบ

### 8.2 Acceptance matrix

| หมวด | เกณฑ์รับ | วิธีพิสูจน์ |
|---|---|---|
| ความชัดเจน | ผู้ตรวจบอก channel/context/state/next action ได้โดยไม่อาศัยคำอธิบายนอกจอ | task walkthrough กับข้อมูลเดิม; ค่าความเร็วเป็นเป้าหมายหลังวัด baseline |
| เอกลักษณ์ | ชื่อสินค้า/angle/preview/output เชื่อมกันและอ่านเป็นงานผลิตคลิป | ปิดชื่อผลิตภัณฑ์แล้วอธิบายงานจากภาพ |
| Chrome | migrated controls ไม่มี hue-gradient/glow/emoji ตกแต่ง; exception มีเหตุผล | inventory + screenshot + scoped source scan |
| ระยะ | component ชนิดเดียวกันมีขนาดและ alignment ตาม contract | ภาพ/DOM measurement ทุก viewport ที่เกี่ยวข้อง |
| Typography | ฟอนต์ UI เปลี่ยนเฉพาะที่อนุมัติ; ไม่มี text clipping; output text ไม่เปลี่ยน | computed styles, Thai cases, output/manifest comparison ตาม scope |
| Contrast | normal text ≥4.5:1; large text ≥3:1; essential non-text boundaries/focus ตรวจตามเกณฑ์ที่เกี่ยวข้อง | วัดคู่สีจริงทุก state ไม่วัด palette เดี่ยว |
| Keyboard | navigation/menu/dialog/workflow action ใช้ keyboard ได้และ focus มองเห็น | Tab/Shift+Tab/Escape/Arrow/Home/End ตาม pattern ของ control |
| Touch | product target 44×44px สำหรับ coarse pointer; ไม่พึ่ง hover | DOM bounds + device viewport walkthrough |
| State truth | unknown ไม่แสดง pass; saved/rendered/posted ต่างกัน; no-data ไม่แทน error | deterministic fixtures ของ state table |
| Motion | reduced motion ใช้ได้; ไม่มี loop ตกแต่งใน migrated chrome | media emulation + ตรวจ JS/CSS ที่เกี่ยวข้อง |
| Responsive | ไม่มี action สำคัญหลุดจอ; keyboard/safe-area ไม่ทับ | matrix ใน 5.10 + zoom/long text |
| Performance | ไม่มี regression เกิน budget ที่ตกลงจาก baseline | profile ก่อน/หลังชุดข้อมูล/เครื่อง/viewport เดียวกัน |
| Data safety | channel scoping, autosave, revision, export identity คงเดิม | meaningful regression tests และ walkthrough เฉพาะ path ที่แตะ |

WCAG อ้างอิง: [Contrast และข้อกำหนดฉบับเต็ม](https://www.w3.org/TR/WCAG22/), [Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum), [Focus Not Obscured Minimum](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum)

44×44px เป็นเป้าหมาย touch ของผลิตภัณฑ์นี้ ไม่กล่าวว่า WCAG AA บังคับ 44px ทุก control; WCAG 2.2 AA SC 2.5.8 ใช้ขั้นต่ำ 24×24 CSS px พร้อมข้อยกเว้น/ระยะห่างตามเกณฑ์ ส่วน focus ขั้นต่ำต้องไม่ถูก UI บังทั้งหมด; แผนตั้งเป้าให้เห็นเต็มเพื่อใช้งานสะดวก

### 8.3 การทดสอบสำหรับรอบ implementation ภายหลัง

- งานเอกสารรอบนี้ไม่รัน build/test/render เพราะไม่มี application change
- เมื่อแก้ presentation ให้รัน `npm test` และ `npm run build` ใน `frontend/` ตามกฎโปรเจกต์ และตรวจภาพจริงของหน้าที่เปลี่ยน
- ถ้าปรับ state/save/load/channel ต้องมี test ที่พิสูจน์ behavior ของ path นั้น ไม่เขียน test ซ้ำ class string เพียงเพื่อให้มีจำนวน pass
- ถ้าแตะภาพที่ส่งออก/preview ให้รัน `.venv/Scripts/python.exe -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider --tb=short` และชุด behavior ที่เกี่ยวข้อง พร้อม FFmpeg render/probe ใน `.tmp/` และตรวจเฟรมจริงตามกฎ
- ใช้คู่ `SequencePlayer`/subtitle engine ตาม contract เมื่อมีผลต่อภาพจริง การเปลี่ยน chrome ไม่ควรนำไปสู่การแก้คู่นี้โดยไม่จำเป็น
- ทำ visual QA เป็น batch ตามหน้าที่เปลี่ยน: desktop/mobile รอบแรก แล้วแก้สิ่งที่พบเป็นชุดและยืนยันอีกหนึ่งรอบตามความจำเป็น; ไม่สับสนกับสิบรอบการวางแผนครั้งนี้
- รัน Impeccable detector หนึ่งครั้งกับไฟล์ UI ที่แก้ตอน implementation เสร็จ พร้อม review ข้อยกเว้นของ video preview; ไม่รัน detector เพื่อตีความว่ารอบวางแผนผ่าน visual QA
- Gate ที่ต้องจ่าย API, render หรือส่งโพสต์ ให้ใช้ขอบเขตการอนุญาตเฉพาะงาน; ห้ามปล่อยผลทดสอบเข้า `04_Exports/`, registry หรือข้อมูลจริง
- บันทึกคำสั่ง ผล pass/fail และข้อจำกัดจริง ไม่คัดตัวเลขเทสจาก Antigravity มาอ้างเป็นผลของแผนนี้

## 9. ความเสี่ยง การย้อนกลับ และจุดตัดสินใจ

### 9.1 ความเสี่ยงที่ต้องมีวิธีรับมือ

| ความเสี่ยง | สิ่งป้องกัน | วิธีถอยกลับ |
|---|---|---|
| Global CSS เปลี่ยน preview/video text | จำกัด selector, sensitive-file list, computed-style comparison | revert chrome token slice ของรอบนั้น; ไม่แก้ manifest เพื่อชดเชย |
| กวาด regex ทำลาย composition gradient หรือ track color | class inventory และ exceptions ตามบทบาท | เปลี่ยนทีละ component/surface ไม่มี global replace |
| Theme เก่าพังหรือ preference หาย | retain IDs/storage, mapping มี version, fallback ชัด | กลับ token adapter เดิมและอ่าน preference เดิมได้ |
| หน้าใช้ Button กลางแล้วทุกปุ่มกลายเป็น primary | audit intent ใน caller พร้อม migration | rollout primitives + pilot แล้วค่อยขยาย |
| ลดข้อความจนไม่รู้ channel/AI cost/status | content contract ต่อ surface | restore context label/inline explanation ที่จำเป็น |
| งานหลายเอเจนต์ชนกัน | status/diff ก่อนเริ่ม, ownership ของไฟล์, ไม่ทับงานค้าง | เก็บงานแยก branch/worktree เมื่อเหมาะสม ห้าม reset ไฟล์คนอื่น |
| เปลี่ยนสีแล้ว state meaning เปลี่ยน | semantic mapping และ fixtures | rollback presentation โดยคง backend records |
| ปรับขนาดใหม่ทำ layout saved ใช้ไม่ได้ | ตรวจ min/max และ saved dimensions ก่อน migration | ใช้ persistence เดิม; reset เฉพาะที่ผู้ใช้สั่ง |
| พยายามแตกต่างจนใช้งานยาก | Operate mode และ standard controls | เลือก task clarity เหนือตกแต่ง |

### 9.2 ข้อตัดสินใจก่อนเริ่ม implementation

1. ยอมรับ direction ห้าบรรทัดและ matte studio neutral หรือแก้เฉพาะส่วนที่ไม่ตรงภาพจำที่ผู้ใช้ต้องการ
2. ยืนยันบทบาท accent ที่มีอยู่, แบรนด์/mark ที่ต้องรักษา และนโยบาย theme สำหรับผู้ใช้เดิม
3. อนุมัติรายการ UI typography แยกต่างหากถ้าต้องการเปลี่ยน; output fonts และ caption presets ยังคงตาม Golden Master เฉพาะ workflow
4. เลือก pilot เป็น Editor + สินค้า ตามขอบเขตที่ยืนยัน โดยเริ่มที่ baseline/current states
5. กำหนดว่าเปลี่ยน label เมนูตาม glossary หรือรักษาคำเดิม แล้วอัปเดต Guide ให้ตรงเมื่อทำจริง

สิ่งเหล่านี้เป็นจุดตัดสินใจของรอบลงมือ ไม่ใช่ข้อบังคับให้ผู้ใช้ตอบก่อนอ่านแผนนี้ และไม่ถือว่าการขอแผนอนุมัติ application change แล้ว

## 10. ผลตรวจเอกสารและการส่งต่อ

### 10.1 สิ่งที่ทำเสร็จในรอบวางแผน

- อ่านโครงสร้างผลิตภัณฑ์และงานค้างที่เกี่ยวข้อง; ได้ scope ที่ผู้ใช้ยืนยัน
- ตรวจและทบทวนสิบมุม พร้อมหลักฐานและการปรับแผนตามข้อค้นพบ
- ทำ file map, priority backlog, semantic state table, glossary, viewport matrix และ acceptance gates
- แยกข้อเท็จจริงจาก source, ภาพเก่า, hypothesis และข้อเสนอ
- ไม่แก้ application code, dist, raw/assets, project manifests หรือข้อมูลสินค้า
- ไม่สร้าง mockup HTML, ภาพ AI, วิดีโอทดสอบ หรือ production export

### 10.2 Jev และข้อจำกัด

- ก่อนดำเนินแผน: Jev ให้คะแนน **3.35/4, confidence 0.44, verdict escalate**
- ผู้ใช้ยืนยันผ่านคำถามว่าให้ทำแผนเอกสารต่อ โดยข้อเสนอเป็นร่างและไม่แก้ UI
- หลังเขียนเอกสาร: การประเมินจากคำสรุปโครงสร้างเอกสารได้ **0.26/3, confidence 0.75, verdict escalate** ไม่ได้ส่งเอกสารเต็มให้ Jev และไม่ใช้ผลนี้รับรองความครบถ้วน ผู้ใช้อนุญาตการทำแผนเอกสารต่อไว้แล้ว จึงส่งมอบเป็นร่างเพื่อพิจารณาและหยุดก่อน implementation ตามขอบเขตเดิม
- ผล Jev เป็นความเห็นประกอบ ไม่ใช่หลักฐานยืนยันคุณภาพ UI หรือสิทธิ์ข้ามกฎโปรเจกต์
- ไม่มี current live screenshots จึงยังไม่ให้คะแนนความสวย, accessibility conformance หรือประสิทธิภาพของแอป
- เก็บ fixture เก่าและภาพ TikTok ออกจาก baseline ปัจจุบัน; ไม่มีการอ้างว่าได้เห็น Editor ล่าสุดจริง
- งาน Antigravity ยังเปลี่ยน source ได้ระหว่าง session; ก่อนลงมือต้องอ่าน diff/เอกสารสถานะใหม่อีกครั้ง

ผลตรวจโครงสร้างเอกสารด้วยเครื่องมือ: พบหัวข้อหลัก 10 ส่วน, รอบตรวจ 01–10 ครบและไม่ซ้ำ, ไม่พบ Unicode replacement character; ตรวจ path ของ RenderButton/Inspector/Timeline/TodayScreen และ parity test พบครบ การตรวจนี้ยืนยันโครงเอกสารและ path ที่เลือก ไม่ใช่ผล visual test

### 10.3 รูปแบบการส่งต่อที่ต้องการ

ผู้เริ่ม implementation อ่านเอกสารนี้ → ตรวจ TODO/status/source ใหม่ → เก็บ baseline ปัจจุบัน → ยืนยัน direction/รายการ font ที่มีผล → เลือก phase เล็กที่ตรวจรับได้ → ปรับและทดสอบตาม scope → สรุปผลจริงพร้อม rollback point

ผลส่งมอบรอบนี้คือ **แผนพร้อมตรวจทิศทางและแตกงานต่อ** ไม่ใช่ UI ที่แก้แล้ว และไม่ใช่การรับรองว่าการเปลี่ยนแปลงทั้งระบบผ่านการทดสอบ
