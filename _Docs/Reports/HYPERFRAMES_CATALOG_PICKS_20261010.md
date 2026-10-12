# HyperFrames Catalog — ของที่แนะนำให้ OmniCut ใช้ (392 ชิ้น)

- **ดำเนินการโดย:** Claude Code (Claude Sonnet 5.5)
- **วันที่:** 2026-10-10
- **ที่มาข้อมูล:** `http://localhost:3002/api/registry/blocks` (Studio) + โค้ดของชิ้นที่คัดไว้จาก `raw.githubusercontent.com/heygen-com/hyperframes/main/registry`
- **ขอบเขต:** อ่านชื่อ/คำอธิบาย/แท็ก/ขนาด/ความยาวครบทั้ง 392 ชิ้น แล้วสแกนโค้ดแบบหยาบเฉพาะ ~90 ชิ้นที่คัดไว้ (วิธีแยกตัวอักษร, WebGL, ฟอนต์) **ยังไม่ได้ติดตั้งหรือเรนเดอร์ชิ้นไหนจริง และยังไม่ได้ทดสอบกับภาษาไทย**

## 1. ภาพรวม

| | จำนวน |
|---|---|
| ทั้งหมด | 392 = blocks 170 + components 222 |
| block แนวตั้ง 1080x1920 | 12 (อีก 157 แนวนอน 1920x1080, 1 ชิ้น 1440x2560) |
| components | ไม่มีขนาดของตัวเอง วางในคอมโพซิชัน 9:16 ได้เลย |
| มี preview ใช้ได้ใน Catalog | 121 (เหลือ 271 ต้องติดตั้งก่อนถึงจะดู) |
| experimental | 18 (ไม่แนะนำ) |
| license | 383 ไม่ระบุ (สันนิษฐานตาม repo = Apache-2.0), 9 ระบุเอง (Apache-2.0 / MIT / OFL-1.1) |

## 2. เกณฑ์คัด (มาจากกฎโปรเจกต์)

1. **9:16 / safe zone** — components หรือ block แนวตั้งเท่านั้น (block แนวนอนต้องดัดแปลง)
2. **ของจริงก่อน** (`kit/STYLE.md` ข้อ 1–2) — ไม่เอาพื้นหลังเปล่า การ์ด UI มืด glassmorphism โมเดล 3D/จักรวาล
3. **ภาษาไทย** — เอฟเฟกต์ที่ตัดเป็นรายตัวอักษรทำให้สระ/วรรณยุกต์แตก ต้องเป็นรายคำ/วลี (บทของเราเว้นวรรคธรรมชาติอยู่แล้ว) · ส่วนใหญ่ใช้ `var(--font-display, Inter…)` เปลี่ยนเป็น Anuphan/Kanit ผ่านตัวแปรได้ · `hw-*` ใช้ Caveat (ไม่มีไทย) ใช้ได้เฉพาะเส้นวาด
4. **ซับคงมาตรฐานเดิม** — `caption-*` (17) ไม่แทนซับของเรา
5. **เบาเครื่อง** — WebGL/WebGPU/html-in-canvas บนการ์ดจอ Intel UHD เสี่ยงช้า/ไม่เหมือนกันทุกครั้ง
6. **ตัดแบบคนตัด** — ไม่เอา shader transition ฟุ้งๆ ใช้ hard cut + whoosh + punch-in

## 3. Tier A — แนะนำติดตั้งก่อน (ตรงกับ 4 สไตล์ที่อนุมัติ)

### Meme-PAS (เจ็บ → ฮา → ขาย)
| ชิ้น | ใช้ทำอะไร |
|---|---|
| `camera-shake` | จอสั่นตอนมุก/กระแทก (ตอนนี้เขียน `shake()` เอง) |
| `beat-accent` | แฟลช + ชีพจรตอนเสียงกระแทก |
| `headline-slam` | หัวข้อกระแทกลงจอ (แยกรายคำ) |
| `shutter-slam` | คำเดียวกระแทกพร้อม motion blur (แยกตัวอักษร → ทดสอบไทย) |
| `count-up`, `number-wheel` | ตัวเลขนับ: บิลค่าไฟ, แบต %, ราคา |
| `spring-pop`, `gloss-sweep` | ตราประทับ/ป้ายราคาเด้ง, การ์ดโปรโมชันมีแสงเฉียง |
| `confetti` | ฉลอง/ปิดการขาย |
| `oversized-cursor` | เมาส์ใหญ่ชี้ "กดตะกร้าเหลือง" แทนลูกศรวาดเอง |
| `cta-lockup`, `cta-close` | ปิดคลิป CTA |
| `freeze-frame-dressing`, `beat-freeze-cut` | หยุดภาพ + กระดาษ/เทป สไตล์สติกเกอร์ ตรงกับ die-cut ของเรา |
| `whip-pan-cut`, `cut-the-curve`, `match-cut` | ตัดแบบคนตัด (ความเร็วต่อเนื่อง ไม่ใช่ shader) |
| `grain-overlay`, `vignette`, `organic-light-leak-overlay`, `editorial-flash-overlay` | ซ้อนเบาๆ ด้วย CSS ล้วน |

### Tech Explainer (สาย Vox)
| ชิ้น | ใช้ทำอะไร |
|---|---|
| `vox-annotate` | มาร์กเกอร์วาดเน้นคำสำคัญ — ตรงสไตล์ Vox ที่สุด (แยกตัวอักษร → ทดสอบไทย) |
| `marker-highlight`, `inline-highlight`, `hw-underline`, `hw-callout-circle`, `hw-arrow` | ขีด/วงกลม/ลูกศรวาดมือ (เส้นอย่างเดียว ไม่ใส่ตัวหนังสือ Caveat) |
| `yt-feather-highlight` | หรี่ทั้งเฟรมเหลือวงนุ่มรอบฟีเจอร์ที่พูดถึง |
| `yt-circle-pointer`, `outline-draw` | วงกลมล้อมจุด + นับถอยหลัง / กรอบวาดรอบสินค้า |
| `push-in`, `pull-back-reveal`, `focus-rack`, `yt-camera-move`, `drift-hold` | กล้องซูม/ดึงออก/โฟกัสเลื่อน |
| `mk-specs-list` | รายการสเปกซ้อนบนฟุตเทจ (เหมาะกับแกดเจ็ตมาก) |
| `mk-progress-stat`, `mk-usage-arc`, `conic-progress-ring` | ตัวเลขใหญ่ + หลอด/วงแหวนเปอร์เซ็นต์ |
| `chart-story`, `animated-bar-chart`, `decline-chart` | กราฟเทียบ/กราฟตก (ค่าไฟพุ่ง) |
| `before-after-wipe`, `comparison-split`, `grade-split-reveal` | ก่อน-หลัง / เทียบสองฝั่ง (`grade-split-reveal` ใช้ canvas) |
| `star-rating-fill` | ดาวรีวิวเติมตามคะแนน |
| `telemetry-hud`, `tracing-beam` | HUD ตัวเลขสเปกรอบสินค้า / เส้นแสงวิ่งผ่านจุดขาย |

### VS Battle
`split-tilt-cards` (สองการ์ดเปิดเหมือนหนังสือ) · `comparison-split` · `conic-progress-ring` · `outline-draw` · `physical-exit` (K.O. ร่วงหลุดจอแบบมีแรง) · `rubber-band-bumper` · `gloss-sweep` (ผู้ชนะ) · `camera-shake` · `number-wheel` · `logo-sting`

### POV Chat Story
**เก็บ `kit/line-chat.css` ของเราไว้** (หน้าตา LINE ไทย เจ้าของช่องอนุมัติแล้ว) ยืมจาก catalog เฉพาะ:
`typing-indicator`, `chat-message` (จังหวะเข้า scale 0.75 / 0.12 วิ) · `notification-stack`, `native-notification-pop`, `notification-pileup` (แจ้งเตือนรัวๆ เป็น hook "แบตจะหมด") · `gesture-tap`, `touch-indicator`, `press-ripple` (นิ้วกดสั่งซื้อ) · `sheet-spring-up`

## 4. Tier B — เก็บไว้ ใช้ตามสไตล์อนาคต

| สไตล์ที่น่าจะมา | ชิ้นที่ใช้ได้ |
|---|---|
| **ตอบคอมเมนต์** (ยอดนิยมในร้านค้า TikTok) | `yt-comment-card` (พิมพ์ทีละตัว → ต้องตัดตามพยางค์), `tiktok-follow` (block แนวตั้ง) |
| **ความเชื่อผิด vs ความจริง** | `strikethrough-replace`, `text-state-swap`, `line-swap`, `kinetic-type-swap`, `text-match-cut` |
| **ลดราคา/ดีลด่วน** | `number-wheel`, `slot-machine-roll`, `ticker-takeover`, `split-flap-board`, `yt-circle-pointer` (นับถอยหลัง), `confetti`, `beat-accent` |
| **จัดอันดับ Top-N** | `animated-bar-chart`, `bar-chart-race` (แนวนอน ต้องดัดแปลง), `spring-pop`, `number-pop-in` |
| **ทดสอบ/ก่อน-หลัง** | `before-after-wipe`, `comparison-split`, `grade-split-reveal`, `decline-chart` |
| **แกะกล่อง/ASMR** (ต้องมีฟุตเทจ 60fps ตาม STYLE.md) | `motion-blur`, `camera-shake` (handheld), light-leak, `grain-overlay`, `freeze-frame-dressing` |
| **ทัวร์ฟีเจอร์** | `pan-stations`, `velocity-throw-snap`, `constellation-hub`, `tracing-beam` |
| **ป้ายชื่อรุ่นสินค้า** | `lt-accent-underline`, `lt-kicker-name`, `lt-mask-reveal` (แบบไม่มีการ์ด · ฟอนต์เดิมเป็น Oswald/Montserrat ต้องเปลี่ยนเป็น Anuphan/Kanit) |
| **ข่าวด่วนแนวมีม** | `news-ticker`, `lower-third-bild`, `x-post`, `reddit-post` |
| **โชว์หลายสี/หลายรุ่น** | `carousel-*` 26 ชิ้น (แนวนอน ใช้แค่ภาพนิ่ง ต้องปรับ 9:16) |
| **โลโก้ช่อง rizanntry** | `logo-sting`, `logo-brand-close` (เมื่อมีโลโก้) |

## 5. Tier C — ไม่แนะนำ

| กลุ่ม | จำนวน | เหตุผล |
|---|---|---|
| shader transition | 14 | ฟุ้ง/ดูเป็น AI ขัดกับ "ตัดแบบคนตัด" + ใช้ WebGL |
| `transitions-*` showcase | 13 | เป็นชุดโชว์ ไม่ใช่ของใช้ |
| WebGL/WebGPU/html-in-canvas/3D (ไม่นับ transition) | 26 | หนักเครื่อง, หน้าตา AI (liquid-glass, nebula, cosmic-orb, halftone, 3D iPhone/MacBook) |
| ตัวอย่างโค้ด/terminal | 12 | ไม่ใช่เนื้อหาเรา |
| แผนที่ | 8 | ไม่เกี่ยว |
| mockup แชท AI (ChatGPT/Claude/AI chat) + showcase ของแบรนด์ HeyGen | ~8 | เป็น UI/แบรนด์คนอื่น |
| `lt-*` สำหรับพอดแคสต์ (ที่เหลือ) | 10 | การ์ด/บล็อกหนักแบบรายการสัมภาษณ์ |
| `caption-*` | 17 | ซับของเราตายตัวตามสัญญาฟอนต์/ซับ (Mali/Anuphan) |
| พื้นหลังล้วน (`mesh-gradient`, `aurora`, `grain-field`, `yt-lcd-background` ฯลฯ) | 16 | กฎ "ห้ามพื้นดำ/พื้นเปล่า" |
| ตัวหนังสือวาดมือ Caveat (`hw-title`, `hw-write-title`, `hw-text-cloud` ฯลฯ) | ~8 | ไม่มีอักษรไทย |
| แยกรายตัวอักษร (`bottom-up-letters`, `top-down-letters`, `matrix-decode`, `scramble-reveal`, `char-slam-explode`, `split-flap-board` กับข้อความไทย) | ~8 | สระ/วรรณยุกต์แตก |
| experimental | 18 | ยังไม่เสถียร |

## 6. ข้อควรระวังก่อนใช้จริง

1. **ทดสอบภาษาไทยทุกชิ้นใน Tier A ก่อน** โดยเฉพาะที่สแกนพบการแยกตัวอักษร: `shutter-slam`, `vox-annotate`, `marker-highlight`, `line-swap`, `kinetic-type-swap`, `count-up`, `chart-story`, `telemetry-hud`, `yt-comment-card`, `cta-close` — ถ้าแตก ต้องแก้ให้ตัดตามพยางค์/`Intl.Segmenter('th')`
2. **สแกนเป็นแบบหยาบ** (regex) ธงแจ้ง `Math.random/Date.now` ใน `camera-shake`, `beat-freeze-cut`, `notification-stack`, `radial-surround` อาจเป็นแค่คอมเมนต์หรือ PRNG แบบ seed — ต้องเปิดอ่านก่อนใช้ (กฎ: ห้ามสุ่ม ต้อง deterministic)
3. **ฟอนต์**: ส่วนใหญ่ใช้ `var(--font-display)` ให้ผูกเป็น Anuphan/Kanit ที่ `kit/fonts/` ส่วนชิ้นที่ฝังฟอนต์ตายตัว (Montserrat, Oswald, Caveat) ต้องแก้เอง
4. **license**: ชิ้นที่ไม่ระบุ สันนิษฐานตาม repo (Apache-2.0) — ถ้านำชิ้นไหนมาใช้ในเชิงพาณิชย์จริง ควรเปิดดู header ของไฟล์นั้นอีกครั้ง
5. **ติดตั้งแล้วจะมีไฟล์ในโปรเจกต์** — ติดตั้งทีละชิ้นที่จะใช้ อย่าลงทั้ง 392 (Lint จะบวม ปัจจุบัน 1030 เตือนจากคลิปเดิม)
6. ติดตั้ง: `npx hyperframes@0.8.143 add <ชื่อ>` (ชิ้นที่ไม่มี preview ใน Catalog จะโผล่ในแท็บ Compositions หลังติดตั้ง กดดูได้)
