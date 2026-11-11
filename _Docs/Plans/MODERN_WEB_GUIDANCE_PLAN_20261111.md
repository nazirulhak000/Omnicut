# แผนปรับ frontend ตาม Modern Web Guidance

วันที่: 2026-11-11 · ดำเนินการโดย: Claude Code (Claude Fable 5.2) · สถานะ: **ทำเสร็จแล้ว 2026-11-11** (ผู้ใช้ตัดสิน: รองรับ iPhone · ทำทุกเฟสพร้อมกัน · ฟอนต์ตามความเหมาะสม → ไม่แตะ) — ผลจริงและสิ่งที่ยังไม่ได้ตรวจดู `HISTORY.md` รอบ CLAUDE-MODERN-WEB-GUIDANCE-20261111

## 1. สรุปสั้น

frontend (`frontend/src`, 427 ไฟล์, React 19 + Vite 8 + Tailwind 4) ไม่ได้เก่า ไม่มี `innerHTML`, ไม่มี `execCommand`, ใช้ `structuredClone` / `navigator.clipboard` / `ResizeObserver` อยู่แล้ว

จุดที่ควรปรับมี 6 กลุ่ม ใหญ่สุดคือ **หน้าต่างป๊อปอัป (modal)** ที่แต่ละไฟล์เขียนเองไม่เหมือนกัน ควรย้ายไปใช้ `<dialog>` ของเบราว์เซอร์ตัวเดียว

ไม่มีข้อไหนเป็นบั๊กร้ายแรง ทั้งหมดเป็นงานลดโค้ดซ้ำ เพิ่มการเข้าถึง (accessibility) และความลื่น

## 2. วิธีตรวจ

- `npx modern-web-guidance legacy-scan frontend/src` — ตรวจ 35 กฎ (ราว 20% ของคลัง guide) พบ 2 จุด
- นับ pattern ด้วย grep ทั้ง `frontend/src` (ไม่รวมไฟล์ `.test.`) สำหรับส่วนที่ legacy-scan ไม่ครอบคลุม
- ยังไม่ได้เปิดแอปวัดจริงในเบราว์เซอร์ (Lighthouse / INP) ตัวเลขด้านล่างเป็นจำนวนที่นับจากโค้ด

## 3. สิ่งที่พบ และงานที่เสนอ

เรียงตามความคุ้ม (ผลมาก เสี่ยงน้อย ก่อน)

### เฟส A — Enter ชนกับ IME (เล็ก ทำได้ทันที)

- พบ 2 จุด: `components/editor/inspector/ClipInspector.jsx:71`, `components/editor/inspector/OverlayInspector.jsx:520`
- ปัญหา: กด Enter เพื่อยืนยันคำระหว่างพิมพ์ภาษาจีน/ญี่ปุ่น/เกาหลี จะถูกนับเป็น "บันทึก" ทันที
- แก้: เพิ่มเช็ก `e.nativeEvent.isComposing` บรรทัดเดียวต่อจุด
- ผลกับผู้ใช้ไทย: น้อย (คีย์บอร์ดไทยไม่ใช้ composition) แต่แก้ถูกและไม่เสี่ยง
- guide: `ime-safe-enter-submit`

### เฟส B — Modal ไปใช้ `<dialog>` (ใหญ่สุด คุ้มสุด)

- ตอนนี้: ไม่มี `<dialog>` เลย · 21 ไฟล์วาด overlay เองด้วย `fixed inset-0` · 17 ไฟล์ดัก Escape เอง · `ui/Modal.jsx` มีอยู่แต่ใช้แค่ 4 ไฟล์ · ล็อก scroll ด้วยการแก้ `body.style.overflow` · มี `z-[N]` 27 จุดใน 16 ไฟล์
- ปัญหา: แต่ละ modal ปิด/โฟกัส/ล็อก scroll ไม่เหมือนกัน คีย์บอร์ดหลุดไปกดของข้างหลังได้ และต้องไล่ z-index เอง
- แก้:
  1. เขียน `ui/Modal.jsx` ใหม่บน `<dialog>` + `showModal()` (ได้ top layer, focus trap, Escape, ปุ่ม back มือถือ จากเบราว์เซอร์เอง) คง props เดิมและ bottom sheet บนมือถือ
  2. ย้าย modal ที่เขียนเองมาใช้ `ui/Modal.jsx` ทีละไฟล์ เริ่มจากตัวเล็ก (`SSDSyncModal`, `VoicePickerModal`, `CloudArchiveModal`) จบที่ตัวใหญ่ (`CoverStudioModal`, `MediaPickerModal`, `RenderPreflightModal`)
  3. ลบโค้ดดัก Escape / ล็อก scroll / z-index ที่ไม่ต้องใช้แล้ว
- guide: `dialog`, `light-dismiss-a-dialog`, `prevent-page-scroll-under-modal-dialog`, `platform-controls-dismiss-dialog`, `declarative-dialog-popover-control`
- ความเสี่ยง: กลาง — modal ที่มีวิดีโอ/ลากวาง (`@dnd-kit`) ต้องลองมือทีละตัว

### เฟส C — เมนู dropdown ไปใช้ Popover API

- ตอนนี้: 5 ไฟล์ดัก `document.addEventListener('mousedown')` เพื่อปิดเมื่อคลิกข้างนอก — `EditorChannelSelector`, `HeaderMenu`, `ProjectSelector`, `RenderButton`, `RenderReadinessChip`
- แก้: ใช้ attribute `popover` (ปิดเมื่อคลิกนอก/Escape เอง อยู่ top layer ไม่โดนตัดขอบ) ลบ listener ทั้ง 5
- guide: `menu`, `app-menus`, `viewport-aware-dropdowns`
- ความเสี่ยง: ต่ำ-กลาง — ตำแหน่งเมนูต้องเทียบกับของเดิม

### เฟส D — เลิกใช้ `alert()` / `confirm()` ของเบราว์เซอร์

- ตอนนี้: 20 จุดใน 8 ไฟล์ (`ProducerHub`, `QuickRefPage`, `ScheduleAgenda`, `SystemSettings`, `OverlayInspector`, `AssetPanel`, `CoverStudioModal`, `StorageAnalyticsTab`)
- ปัญหา: หน้าต่างสีขาวของเบราว์เซอร์ ไม่เข้ากับธีม บล็อกทั้งหน้า และ `confirm` ลบไฟล์ใช้ปุ่มเดียวกับเรื่องทั่วไป
- แก้: `confirm` → `ConfirmDialog` บน `<dialog>` จากเฟส B (ปุ่มขึ้นต้นกริยา เช่น "ลบไฟล์" ตามกฎ UI คลีน) · `alert` → toast ที่มีอยู่ หรือ toast ใหม่ถ้ายังไม่มีตัวกลาง
- guide: `dialog`, `persistent-toast-notifications`
- ต้องทำหลังเฟส B

### เฟส E — Motion และ focus (accessibility)

- Motion: มี `animate-` / `@keyframes` 295 จุด แต่รองรับ `prefers-reduced-motion` แค่ 2 ไฟล์ → เพิ่มกฎกลางใน `index.css` ปิด/ย่อ animation เมื่อผู้ใช้ตั้งค่าลดการเคลื่อนไหว
- Focus: `outline-none` 245 จุดใน 64 ไฟล์ เทียบกับ `focus-visible` 82 จุดใน 32 ไฟล์ → ไล่หาปุ่ม/ช่องกรอกที่ลบ outline แล้วไม่มีวงโฟกัสแทน เติม `focus-visible:ring`
- guide: `motion`, `accessibility`
- ความเสี่ยง: ต่ำ · **ไม่แตะ** animation ของซับ/overlay ใน `SequencePlayer.jsx` (กฎ Preview = Render)

### เฟส F — ความเร็วโหลด

- ฟอนต์: `index.html` โหลด Google Fonts 14 ตระกูลในคำขอเดียวแบบบล็อกการวาดหน้า → เสนอโหลดเฉพาะฟอนต์ UI (Prompt) ก่อน ที่เหลือโหลดเมื่อเปิด editor **ต้องขออนุมัติก่อน** เพราะกฎข้อ 10 ห้ามกระทบฟอนต์ งานนี้เปลี่ยนแค่ "เวลาโหลด" ไม่เปลี่ยน family/ขนาด/น้ำหนัก และต้องพิสูจน์ด้วย `test_preview_render_parity.py`
- รูป: `<img>` 56 จุด มี `loading="lazy"` แค่ 8 · 17 ไฟล์ไม่มีเลย → เติม `loading="lazy"` + `decoding="async"` ให้รูปในรายการยาว (gallery, media hub, tracker) ยกเว้นรูปที่เห็นทันทีเมื่อเปิดหน้า
- รายการยาว: ไม่มี `content-visibility` เลย → ลองใส่ที่การ์ดใน `ExportGallery` / `MediaAssetsHub` แล้ววัดผล
- ขนาดไฟล์: `EditorShell` 426 KB, `ProductToClip` 359 KB, `ContentTrackerHub` 219 KB (ก่อนบีบอัด) → วัดก่อน แล้วค่อยตัดสินว่าต้องแยกย่อยไหม
- guide: `visually-stable-font-fallbacks`, `optimize-image-priority`, `lazy-load-video-and-audio`, `identify-inp-causes`
- ต้องวัดจริงในเบราว์เซอร์ก่อนและหลัง ไม่ทำตามความรู้สึก

## 4. สิ่งที่ตรวจแล้วไม่เสนอทำ

- `title=` 688 จุด — tooltip ของเบราว์เซอร์ใช้ได้อยู่ · tooltip แบบใหม่ (`interestfor`) ยังไม่ใช่ Baseline
- Container queries, View Transitions, Anchor positioning — ไม่มีปัญหาที่ต้องใช้ ไม่ใส่เพื่อให้ "ทันสมัย"
- `new Date(` 73 จุด / `Intl` 48 จุด — ใช้ API มาตรฐานอยู่แล้ว ไม่มี library วันที่ให้ถอด
- `SequencePlayer.jsx`, ฟอนต์ซับ, safe zone — นอกขอบเขตทั้งหมด

## 5. เรื่องที่ต้องให้เจ้าของตัดสิน

1. **เบราว์เซอร์ที่ต้องรองรับ** — ถ้าใช้แค่ Chrome/Edge บนเครื่องนี้ ไม่ต้องเขียน fallback (งานเฟส C เร็วขึ้นมาก) ถ้ายังเปิดบน iPhone ผ่าน LAN (`MobileFilmingPage`, `MobileQuickPostPage`) ต้องรองรับ Safari ด้วย · เสนอ: เขียนนโยบายนี้ลง `AGENTS.md` บรรทัดเดียว
2. **ขอบเขตรอบแรก** — เสนอ A + B (ตัว `ui/Modal.jsx` + modal เล็ก 3 ตัว) เป็นรอบนำร่อง ดูผลก่อนย้ายที่เหลือ
3. **เฟส F ฟอนต์** — อนุมัติให้เปลี่ยนวิธีโหลดฟอนต์หรือไม่

## 6. วิธีทำงานแต่ละเฟส

- หนึ่งเฟส = หนึ่งกิ่ง `feat/modern-web-<เฟส>` แตกจาก `main` ผ่านแล้ว merge และลบกิ่ง (กฎข้อ 25)
- ก่อนเขียนโค้ด: `retrieve` guide ของเฟสนั้น และเรียก Jev ตามกฎข้อ 19
- ตรวจผ่าน: `npm test` + `npm run lint` + `npm run build` (rebuild `dist`) + เปิดเบราว์เซอร์ลองจริง (คีย์บอร์ด Tab/Escape, มือถือ, ปุ่ม back) + `test_preview_render_parity.py` ถ้าแตะ editor
- ลำดับ: A → B → D → C → E → F (D ต้องรอ B · ที่เหลืออิสระต่อกัน)
