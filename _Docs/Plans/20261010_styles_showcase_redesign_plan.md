# 🎨 แผนการออกแบบหน้าจอ 4 Approved Styles Showcase (Creative Studio)
**เอกสารแผนงาน:** `_Docs/Plans/20261010_styles_showcase_redesign_plan.md`  
**ดำเนินการโดย:** Antigravity (Gemini 2.5 Pro)  
**อ้างอิงมาตรฐาน:** `/impeccable` (Craft Floor & Visual Hierarchy) + `/ui-ux-pro-max` (Dark Swiss / Studio Minimalist) + `AGENTS.md` กฎข้อ 3.8, 4.8, 4.10

---

## 🎯 1. วัตถุประสงค์ (Goal & Vision)
ปรับโฉมหน้าจอแท็บ **"4 สไตล์ที่อนุมัติ (Approved Styles)"** ใน `HyperFramesHub.jsx` จากเดิมที่เป็นเพียงการ์ดข้อความธรรมดา (Text-heavy Card) ให้กลายเป็น **"Editorial Visual Studio Showcase"**:
1. **มินิมอลแต่รายละเอียดครบ (Minimal yet Information-Dense):** สะอาดตา ไม่รกสายตา จัดวางแบบ Swiss Grid สบายตา
2. **เห็นภาพชัดเจนทันทีว่าสไตล์นั้นตัดต่ออย่างไร (Instant Visual Comprehension):**
   - มี **รูปปกจำลองแนวตั้ง 9:16 (Visual Poster Frame)** สวยงาม คมชัดระดับโปร สะท้อนอัตลักษณ์ของสไตล์นั้น 100%
   - มี **ไทม์ไลน์จังหวะการตัด (Timeline Rhythm Pills)** แยกเป็นช่วงวินาที (Beat-by-Beat) ให้อ่านและเข้าใจจังหวะการตัดต่อได้ใน 3 วินาที
3. **เชื่อมโยงการทำงานจริง (Actionable Production):** กดคลิกเดียวเลือกสไตล์นั้นแล้วกระโดดไปหน้า `เริ่มคลิปดราฟต์ใหม่` ได้ทันที

---

## 🖼️ 2. ดีไซน์รูปปกแนวตั้ง 9:16 ของทั้ง 4 สไตล์ (The 4 Signature Posters)

| สไตล์ | รูปปกแนวตั้ง 9:16 (Visual Identity) | โทนสีและ Accent | องค์ประกอบภาพเด่น |
| :--- | :--- | :--- | :--- |
| **1. VS Battle**<br>*(สายเกมต่อสู้)* | **Street Fighter HUD Battle:**<br>แบ่งจอทแยง 2 ฝั่ง ของเดิม vs ของใหม่ พร้อมหลอดเลือด HP Bar | Crimson Red (`#EF4444`) & Electric Amber (`#FACC15`) | • แถบ HP Bar ซ้าย-ขวา (`OLD 5W` vs `ESSAGER 65W`)<br>• ตัวเลขนับถอยหลัง `99`<br>• ตราสัญลักษณ์ `VS` ตรงกลางเปล่งแสงนีออน<br>• ป้ายคะแนนยก `ROUND 1 • FIGHT!` |
| **2. Tech Explainer**<br>*(สาย Vox)* | **Engineering Blueprint & Exploded View:**<br>ไดอะแกรมผ่าชิ้นส่วนแผงวงจร พร้อมเส้นบอกสเปกเทคนิค | Neon Cyan (`#06B6D4`) & Electric Blue (`#3B82F6`) | • ภาพโครงสร้างอุปกรณ์แบบผ่าขวาง (X-Ray)<br>• เส้นโยงชี้สเปก (GaN Semiconductor, Heat Sink)<br>• ตัวเลข Telemetry เกจวัดวัตต์ `100W` และอุณหภูมิ `38°C`<br>• ฟอนต์ตัวเลขแบบ Monospace เรียบหรูสไตล์สวิส |
| **3. Meme-PAS**<br>*(รีวิวสายมีม)* | **Viral Hook Problem Burst:**<br>ปรอทวัดไข้แตกกระจาย + สีหน้ามีมตกใจ + ป้ายเตือนบิลค่าไฟ | Flame Orange (`#F97316`) & Caution Yellow (`#EAB308`) | • กราฟิกหลอดปรอทแตกฟิสิกส์กระจาย (Mercury Burst)<br>• มีมสีหน้าช็อกเหงื่อตก (Key & Peele sweat meme)<br>• ป้ายเตือน Hook: `"ห้ามเปิดแอร์ถ้าไม่อยากจ่ายค่าไฟเดือนละ 3,500.-"`<br>• แถบป้ายส้ม/เหลือง ตะกร้า TikTok ชัดเจน |
| **4. POV Chat Story**<br>*(แชท LINE เล่าเรื่อง)* | **Authentic LINE Chat Interface:**<br>หน้าจอแชท LINE สมจริง 100% ตัวหนังสือคมชัด ดึงดูดสายตา | LINE Emerald Green (`#06C755`) & Pure White (`#FFFFFF`) | • แถบ Status Bar ด้านบน (เวลา, สัญญาณ 5G, แบตเตอรี่)<br>• แถบห้องแชทสีเขียว LINE แท้ พร้อมชื่อคู่สนทนา<br>• กล่องข้อความแชทมีหางชี้ (Chat Bubbles with Tails)<br>• ป้ายกำกับ `"อ่านแล้ว 14:02"` และจุดกำลังพิมพ์ (`typing...`)<br>• แถบเครื่องมือส่งข้อความด้านล่าง (ปุ่มกล้อง, รูปภาพ, ไมโครโฟน) |

---

## 📐 3. โครงสร้างเลย์เอาต์การ์ดสไตล์ (Card Architecture)

ใช้โครงสร้าง **Split-Frame Horizontal Card (สัดส่วน 9:16 ซ้าย + ข้อมูลขวา)** ใน Desktop Grid (2 คอลัมน์) และ Single Column ใน Tablet/Mobile:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [สไตล์การ์ด: VS Battle]                                          ขอบนีออนเรืองแสงเมื่อ Hover    │
├──────────────────────────┬──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐ │ 🥊 VS Battle (สายเกมต่อสู้)                  [ สเปกชนสเปก • 25s ]    │
│ │      9:16 POSTER     │ │ HUD เกม Street Fighter ซัดกัน 3 ยก K.O. เปรียบเทียบจุดเด่นชัดเจน     │
│ │                      │ ├──────────────────────────────────────────────────────────────────────┤
│ │    [HP]  VS  [HP]    │ │ ⚡ สูตรจังหวะการตัด (Editing Rhythm Blueprint):                       │
│ │    OLD       NEW     │ │  [0-3s: เปิดศึก VS] ➔ [3-10s: ยก 1 ความเร็ว] ➔ [10-18s: ยก 2 ร้อน]   │
│ │                      │ │  ➔ [18-22s: ยก 3 ราคา] ➔ [22-25s: K.O. ตะกร้า]                       │
│ │     ROUND 1 FIGHT!   │ ├──────────────────────────────────────────────────────────────────────┤
│ │                      │ │ ⏱️ ความยาว: ~25 วินาที    🎙️ เสียง: พากย์ Fenrir (1.0) + ดนตรี Upbeat│
│ │    [ปุ่มดูพรีวิว]    │ │ 🎯 จุดเด่น: เปรียบเทียบสินค้า 2 ตัวแบบหมัดต่อหมัด เห็นผลต่างใน 25 วิ  │
│ └──────────────────────┘ ├──────────────────────────────────────────────────────────────────────┤
│   (Hover ซูม 1.02x)     │ [คลิปอ้างอิง: ess02-vs-25s]              [ เลือกใช้สไตล์นี้ ➔ ]        │
└──────────────────────────┴──────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 4. Design System & Tokens (`/ui-ux-pro-max` + `/impeccable`)

1. **Canvas & Card Dark Theme:**
   - Base Canvas: `#080B11` (Deep Obsidian)
   - Card Background: `#0F172A` / `bg-slate-900/90` (แก้วการ์ดโปร่งแสงเล็กน้อย `backdrop-blur-md`)
   - Normal Border: `border-slate-800/80`
   - Active/Hover Border: สีตาม Signature Accent ของสไตล์ พร้อมแสงเงาละมุน `box-shadow: 0 0 20px rgba(...)`
2. **Typography Hierarchy:**
   - สไตล์ชื่อ: `font-semibold text-white text-base tracking-tight`
   - สโลแกน: `text-xs text-slate-400 font-normal`
   - ไทม์ไลน์ Pills: `font-mono text-[11px] text-slate-300 bg-slate-950/80 border border-slate-800`
   - รายละเอียดสเปก: `text-[12px] text-slate-400`
3. **Craft Floor & กฎเหล็ก UI (Rules Compliance):**
   - **Rule 3.8 & 4.8:** ปุ่ม Action ต้องขึ้นต้นด้วยคำกริยา เช่น `"เลือกใช้สไตล์นี้"`, `"เปิดพรีวิว"` ห้ามใส่ไอคอนซ้ำซ้อนหรือ emoji นำหน้าคำ
   - **Rule 1:1 Parity:** การพรีวิวต้องตรงกับวิดีโอที่เรนเดอร์จริง
   - **WCAG AA:** Contrast ratio ตัวหนังสือบนพื้นหลังเกิน 4.5:1 ทั้งหมด

---

## 🛠️ 5. ขั้นตอนการลงมือทำ (Implementation Steps)

1. **ขั้นตอนที่ 1 — ออกแบบ Component รูปปกจำลอง 9:16 (`StylePosterMockup.jsx`):**
   - สร้างโมดูลแสดงปก 9:16 ที่เรนเดอร์ด้วย SVG + CSS Glassmorphism คมกริบ 100% โหลดไว 0ms ไม่มีปัญหาไฟล์รูปหาย
   - ปรับแต่งความละเอียดของปกทั้ง 4 สไตล์ (VS Battle, Tech Explainer, Meme-PAS, POV Chat Story) ให้เป๊ะตามเอกลักษณ์ของคลิป
2. **ขั้นตอนที่ 2 — ปรับปรุง UI แท็บสไตล์ใน `HyperFramesHub.jsx`:**
   - เปลี่ยนจากการ์ดข้อความเดิมเป็น Split-Panel Editorial Grid
   - เพิ่มแถบไทม์ไลน์จังหวะการตัด (Beat Timeline Bar)
   - เพิ่มปุ่มกดดึงค่าสไตล์เข้าสู่แท็บ `เริ่มคลิปดราฟต์ใหม่` ได้อย่างราบรื่น
3. **ขั้นตอนที่ 3 — เพิ่ม Interactive Modal สำหรับดูรายละเอียดและคลิปอ้างอิง:**
   - เมื่อกดที่รูปปกหรือปุ่มดูรายละเอียด จะมี Modal ป๊อปอัปแสดงคำแนะนำการถ่ายทำ, Prompt ตัวอย่าง, และโครงสร้าง Beat เต็มรูปแบบ
4. **ขั้นตอนที่ 4 — ทดสอบและตรวจสอบคุณภาพ (Verification Pass):**
   - ตรวจสอบผ่าน Puppeteer ส่องดูหน้าจอจริงและถ่าย Screenshot
   - รัน `npm test --prefix frontend` และ `npm run build --prefix frontend` ผ่าน 100%
