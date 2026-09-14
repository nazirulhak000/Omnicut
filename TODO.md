# 📋 OmniCut Pro Studio — Todo กลาง

สมุดบันทึกรอบงานที่ **ยังไม่เสร็จ** ของโปรเจกต์นี้ — ทุกงานต้องผ่านไฟล์นี้ก่อนแตะโค้ด

| ไฟล์ | ใช้ทำอะไร |
| :--- | :--- |
| **TODO.md** (ไฟล์นี้) | งานที่ยังไม่เสร็จ + Backlog — เขียนแผนลงที่นี่ก่อนลงมือ |
| [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md) | รอบที่ปิดแล้ว ย้ายบล็อกเต็มไปเก็บไว้ที่นั่น ห้ามแก้ย้อนหลัง |
| [TEMPLATE_MOTION_PLAN.md](file:///d:/Winona/Programmer/Capcut/TEMPLATE_MOTION_PLAN.md) | แผนยาวของงาน motion ข้อความ (Round 3–7) — เหตุผลและตัวเลขที่วัดมา |
| [SYSTEM_AUDIT_2026-09-09.md](file:///d:/Winona/Programmer/Capcut/SYSTEM_AUDIT_2026-09-09.md) | รายงาน DB/Infra/System audit เต็ม (4-agent, read-only) |
| [SYSTEM_AUDIT_FIX_PLAN.md](file:///d:/Winona/Programmer/Capcut/SYSTEM_AUDIT_FIX_PLAN.md) | แผนแก้ตาม audit ข้างบน แบ่ง 10 stream ขนาน + phase สำหรับยิง agent พร้อมกัน |
| [PRO_EDITOR_STYLE_PLAN.md](file:///d:/Winona/Programmer/Capcut/PRO_EDITOR_STYLE_PLAN.md) | แผนยกระดับคุณภาพการตัดต่ออัตโนมัติด้วย Editorial Style Preset กลาง |
| [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md) | กติกาว่าหนึ่งรอบทำยังไง ติ๊กยังไง ปิดรอบยังไง |

---

## สถานะรวม

- [x] Round UI-FONT-HARMONY-ALL-1 — กวาดล้าง font-mono และผสานฟอนต์กลาง (Prompt) ทั่วทั้งระบบ 100% ครบทุกแดชบอร์ดและหน้าจอ (2026-09-15; frontend vitest 232 passed, build 2.83s ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round GEMINI-TTS-MULTIKEY-ALERT-1 — ปรับระบบ Multi-Key Failover (ลอง 3.1 ทุก Key ก่อนลดเป็น 2.5) + แจ้งเตือน AI Rate-Limit/Quota บน Token Dashboard (2026-09-15; backend 20 passed, frontend 232 passed, build 2,007 modules/2.68s, compileall ผ่าน, live synthesis verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round SCHEDULE-FLEXIBLE-SLOTS-1 — ตั้งเวลาโพสต์เริ่มต้น 5 ช่วง และเพิ่ม/ลบช่วงรายวัน (2026-09-14; backend schedule 10 passed, frontend 230 passed, compileall ผ่าน, build 2,005 modules/3.25s, ดำเนินการโดย: Codex (GPT-5))
- [x] Round SCHEDULE-DEFAULT-RESET-1 — ปรับเทมเพลตเวลาที่บันทึกไว้ทั้งหมดเป็นชุดแนะนำ 5 ช่วง (2026-09-14; อัปเดต 2 สัปดาห์ × 7 วันครบ, API/UI verified, ไม่กระทบคิวคลิป, ดำเนินการโดย: Codex (GPT-5))
- [x] Round COVER-TIMELINE-PRE-RENDER-1 — สร้างหน้าปกจากเฟรมจริงใน Timeline ก่อน Render (2026-09-14; backend cover 8 passed, frontend 230 passed, build 2,006 modules, detector พบเฉพาะคำเตือนเดิม, browser unavailable, ดำเนินการโดย: Codex (GPT-5))

- [x] Round COVER-RENDER-REQUIRES-COVER-1 — บังคับสร้างและบันทึกหน้าปกก่อน Render (2026-09-14; frontend 230 passed, build 2,006 modules/3.13s, diff check ผ่าน, ดำเนินการโดย: Codex (GPT-5))

- [x] Round TRACKER-LARGE-DATA-PERF-1 — ลดเวลาเปิด Content Tracker เมื่อมีคลิปจำนวนมาก (2026-09-14; `/api/exports` 2.6s → 0.28–0.37s ที่ 27 ไฟล์, tracker product+queue 0.15–0.22s, backend 1,417 passed/3 skipped, frontend 230 passed, build 2,006 modules, ดำเนินการโดย: Codex (GPT-5))

- [ ] Round MAIN-FLOW-SCALE-1 — ทำคิว Render ที่ทน restart และลด read-path ที่โตตามจำนวนคลิป (2026-09-14; ดำเนินการโดย: Codex (GPT-5))
- [ ] Round RENDER-DEDUPE-1 — ตัดงาน probe, Vision cache และ Image Motion ที่ทำซ้ำ (2026-09-15; ดำเนินการโดย: Codex (GPT-5))

- [x] Round HOOK-TIER-SYNC-1 — จัดการป้าย Hook Header (แบรนด์ · รุ่น · หมวด) แบบเลือกขอบเขต (เฉพาะคลิปนี้ vs ทั้งสินค้า) ในหน้าสินค้าและสร้างคลิป (2026-09-14; backend 21 passed, frontend 230 passed, build 2,006 modules/3.08s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round VOICE-DEFAULT-PUCK-HYPE-1 — ตั้งค่าเสียงเริ่มต้นทุกสไตล์เป็น Puck ชายพลังสูง TikTok + โทนป้ายยาไวรัล ทั่วทั้งระบบ (2026-09-14; backend 1,415 passed, frontend 230 passed, build 2,006 modules/3.17s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round HOOK-KINETIC-MOTION-1 — Step-by-Step Cumulative Hook Reveal & High-Impact Animation System (2026-09-13; backend parity 177 passed, behavior render 18 passed, smoke 150 passed, frontend 185 passed, build 3.79s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))

- [x] Round THAI-STACKED-MARK-GENERALIZE-1 — ครอบคลุมสระบน `ัิีึื` × วรรณยุกต์ `่้๊๋` ทั้ง 20 คู่ใน Preview/Render (2026-09-13; backend 1,135 passed, visual/contract 180 passed, frontend 185 passed, build/browser verified, ดำเนินการโดย: Codex (GPT-5))

- [x] Round THAI-STACKED-MARK-RENDER-FIX-1 — แก้ `ั` + `่` ซ้อนทับใน Render ด้วย layout-preserving ASS companion event (2026-09-13; backend 1,133 passed, visual/contract 178 passed, frontend 185 passed, build ผ่าน, ดำเนินการโดย: Codex (GPT-5))

- [x] Round AI-PRODUCER-VISION-1 — ยกระดับ AI Gemini Vision วิเคราะห์ภาพเรฟเฟอเรนซ์ใน Quick Ref Vault และ Producer Hub สังเคราะห์เป็นสคริปต์และมุมมองวิดีโอ TikTok (2026-09-14; pytest 20 passed, vitest 219 passed, build 3.59s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round COVER-AI-IMAGEN-1 — AI สร้างรูปหน้าปกคลิป 9:16 ใน Cover Studio (Imagen 3 + Smart Frame Hunt) (2026-09-14; pytest 2 passed, vitest 219 passed, build ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round STORAGE-OPTIMIZER-1 — ระบบล้างแคชคืนพื้นที่ดิสก์ & ความปลอดภัย Safe Storage Optimizer (2026-09-14; pytest 8 passed, vitest 219 passed, build ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round TIKTOK-STATS-SCRAPE-2 — แท็บ Performance เพิ่มลิงก์ คลิปปัง threshold + แมพ manual สำหรับ unmatched rows (2026-09-14; pytest 13 passed, vitest 222 passed, build ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))

- [x] Round COVER-REALTIME-SCRUB-STUDIO-1 — เรียลไทม์ Frame Scrubber ใน Cover Studio (Scrub ทุกวินาทีแสดงเฟรมจริงทันที) + AI Studio Cutout นำช็อตสินค้าจริงผสานฉากสตูดิโอ 9:16 (2026-09-14; pytest 2 passed, vitest 223 passed, build 2.94s ผ่าน 100%, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round COVER-AI-PERSISTENCE-1 — จดจำและกู้คืนภาพปก AI อัตโนมัติ (In-App Cover Memory) สลับไปดูวิดีโอปกติแล้วกลับมาแท็บ AI รูปเดิมไม่หาย ไม่ต้องกดเจนใหม่ + ไฟล์บันทึกถาวรใน 05_Covers_Thumbnails (2026-09-14; pytest 3 passed, vitest 225 passed, build 4.12s ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round COVER-MINIMAL-IT-PROMPT-1 — ยกระดับ Prompt ฉากหลัง Minimal IT คมชัดสมจริง (แผ่นรองตัด Grid/ผนังระแนง Rim Light/มือจับเทค) + เทมเพลต Hook สไตล์ Tech Reviewer (Brand ขาว + Model นีออน) + แก้ UnicodeDecodeError ใน Subprocess (2026-09-14; pytest 7 passed, vitest 230 passed, build ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round COVER-MULTI-GEN-HANDHELD-1 — AI Cover History Gallery (เก็บทุกรูปที่เจนไม่ถูกทับ) + ปลดล็อกคำสั่ง Handheld มือถือสินค้าจริง + Auto-enable Brand/Model Title Overlay (2026-09-14; pytest 6 passed, vitest 230 passed, build 3.19s ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [ ] Round AI-PRODUCER-HUB-AUDIT-PLAN-1 — ตรวจสอบการใช้งาน AI Producer Hub และจัดทำแผนยกระดับแบบ evidence-first (2026-09-13; วิเคราะห์โค้ด + browser snapshot แล้ว, รออนุมัติ scope, ดำเนินการโดย: Codex (GPT-5))
- [ ] Round BG-SUBJECT-ISOLATION-4 — แก้ artifact ติด processing และตรวจลำดับเลเยอร์ให้ Hook อยู่หลัง Subject (2026-09-14; ดำเนินการโดย: Codex (GPT-5))
- [x] Round BG-SUBJECT-ISOLATION-RESUME-1 — ทำงานตัดพื้นหลังแบบ resumable เมื่อเน็ต/หน้าเว็บ/Server หลุด (2026-09-14; backend 45+41 passed, frontend 230 passed, build 2005 modules, compileall ผ่าน; ดำเนินการโดย: Codex (GPT-5))
- [x] Round CALLOUT-RESURRECT-FIX-1 — แก้บั๊ก Text Overlays ถูกปลุกขึ้นมาทับกลางจอ (LOCSmartband) เมื่อลบแล้วใน Editor + ป้องกัน Auto Brand/Model Callout ซ้อนทับ Hook Banner (2026-09-14; pytest backend 8+5+153 passed, vitest 230 passed, build ผ่าน, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round HOOK-DEFAULT-5S-1 — ปรับค่าเริ่มต้น (default) ของป้ายฮุกพาดหัว (Hook Banner) เป็น 5.0 วินาทีตั้งแต่ตอนสร้างโปรเจกต์ (2026-09-11; frontend 151 passed, backend 157 passed, build pass)
- [x] Round ANALYTICS-HUB-1 — พัฒนาเมนูใหม่ "ศูนย์วิเคราะห์ข้อมูลและสถิติรวม" (Analytics & Operations Hub) รวมแดชบอร์ด 4 มิติ (Production, Tokens, Storage, Inventory) (2026-09-11; backend 4 passed, frontend 151 passed, build pass)
- [x] Round SETTINGS-TOKEN-REMOVAL-1 — ถอดแท็บและสถิติโทเคนออกจากหน้าตั้งค่าระบบ (System Settings) ปรับ Eyebrow และเมนูเป็น 'ตั้งค่าระบบ' เต็มรูปแบบ (2026-09-11; frontend 151 passed, build pass)
- [x] Round ANALYTICS-HEADER-DATA-FIX-1 — ตัด Header ซ้ำซ้อนใน AnalyticsHub + ปลดล็อกพอร์ต 8000 จาก process ค้าง ทำให้โหลดข้อมูลสถิติได้สมบูรณ์ 100% (2026-09-11; backend 4 passed, frontend 151 passed, build pass)
- [x] Round POSTED-ARCHIVE-STORAGE-1 — วิดเจ็ตสรุปจำนวนคลิปที่โพสต์แล้วและพื้นที่ประหยัดได้หากย้ายสำรอง (Archive & Storage Reclamation) บน Analytics Hub (2026-09-12; backend 4 passed, frontend 151 passed, build pass)
- [x] Round USER-GUIDE-1 — เมนูใหม่ "คู่มือใช้งาน" แนบในโปรแกรม + อธิบายโฟลว์หลักครบ 7 เมนู (2026-09-12; frontend 151 passed, build 3.47s)
- [x] Round ANALYTICS-CHARTS-1 — พัฒนาระบบกราฟเส้น กราฟโดนัท Funnel Chart และเกจวัดแบบ Pure SVG สไตล์ Dark Modern Glassmorphism สำหรับแดชบอร์ดทั้ง 4 แท็บ (2026-09-12; frontend 151 passed, backend 4 passed, build 3.44s, browser verified)
- [x] Round ANALYTICS-CHARTS-POLISH-1 — ปรับขนาดและจัดระเบียบเลย์เอาท์กราฟใน Analytics Hub ให้กระชับ สวยงาม พอดีสายตา ไม่ใหญ่เกินจำเป็น (2026-09-12; frontend 151 passed, build 3.25s, browser verified)
- [x] Round USER-GUIDE-2 — ปรับการ์ดเมนู 1-7 เป็น grid หลายคอลัมน์บนจอกว้าง กล่องกระชับตามข้อความ (2026-09-12; frontend 151 passed, build 3.87s)
- [x] Round USER-GUIDE-3 — กระชับทุกกล่องในคู่มือ (โฟลว์ 7 ขั้น, คลิปแรก, 4 เฟส, โฟลเดอร์, เช็กลิสต์, ปัญหา, FAQ) (2026-09-12; frontend 151 passed, build 3.69s)
- [x] Round USER-GUIDE-4 — ยกระดับคู่มือเป็น interactive (sticky TOC + scrollspy, เช็กลิสต์ติ๊กได้, การ์ดเมนู accordion, โฟลว์กดไปเมนูได้, ปัญหามีปุ่มลัด, FAQ ค้นหาได้) (2026-09-12; frontend 151 passed, build 4.22s)
- [x] Round SAFE-1 — Disk Guard ก่อน Render & Auto-Snapshot CapCut Manifest 3 Versions (2026-09-12; backend 8+4 passed, frontend 151 passed, build pass)
- [x] Round TIKTOK-STATS-SCRAPE-1 — ซิงก์สถิติ TikTok Studio ผ่าน Extension (parser ตาราง + endpoint import + แมพ tiktok_video_id + แท็บ Performance) (2026-09-12; extension 21 passed + pytest 8 passed, frontend 151 passed, build 4.06s)
- [x] Round TIKTOK-STATS-FIX-1 — แก้บั๊ก `result is not defined` + ย้ายซิงก์สถิติเป็นแท็บที่ 3 "เครื่องมือ" แยกจากขั้นตอนโพสต์ (2026-09-12; extension 21 passed)
- [x] Round AGENT-ATTRIB-1 — บังคับระบุ Agent Tooling & AI Model ในประวัติงาน (Rule 14 ใน AGENTS.md และ work_loop.md) (2026-09-12; ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round BACKUP-1 — One-Click System Backup & Restore (Engine + API + UI ใน SystemSettings maintenance tab) (2026-09-12; pytest 8 passed, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round ASSET-DEDUP-1 — Media Deduplication & Cleanup Engine (Engine + API + UI สแกน/ล้างไฟล์ซ้ำปลอดภัย) (2026-09-12; pytest 4 passed, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round CALENDAR-1 — Interactive Drag-and-Drop Weekly Content Calendar (สลับมุมมอง รายการ/ปฏิทินสัปดาห์ 7 วัน + เลื่อนวันด้วย Drag-and-Drop) (2026-09-12; vitest 152 passed, build 3.14s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round HOOK-VAR-1 — AI Hook Variation & A/B Generator (5 สไตล์ curiosity, warning, social_proof, deal_promo, pain_point + 9:16 safe-zone preview + 1-click apply) (2026-09-12; pytest 8 passed, vitest 152 passed, build 4.08s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round TIKTOK-STATS-DOMAIN-1 — แก้ซิงก์สถิติบนหน้า Studio Content + Alias 'ยอดวิว' + Manifest 0.2.0 + แข็งการจับแท็บ (2026-09-12; extension 28 passed, ดำเนินการโดย: Cline / Antigravity)
- [x] Round TIKTOK-STATS-DOM-2 — รีเขียน parser อ่าน div-grid จริงของ Studio (data-tt components) ตามไฟล์ DOM ที่ user เซฟมา + จับคู่คอลัมน์ตามลำดับหัว + dedupe (2026-09-12; extension 32 passed, ดำเนินการโดย: Cline)
- [x] Round TIKTOK-STATS-MATCH-1 — แมพ 0/10 เพราะไม่มีโพสต์ให้จับคู่ → จับคู่กับคลังผลงานแล้วลงทะเบียนโพสต์อัตโนมัติ + fuzzy match normalize ตัดแฮชแท็ก (2026-09-12; pytest 8 passed, extension 32 passed, ดำเนินการโดย: Cline)
- [x] Round TIKTOK-DASH-REFRESH-1 — วินิจฉัย dashboard ยังโชว์ mock: ยิง live API /latest ด้วย API key ยืนยันคืน 4 โพสต์จริง (Lift 370/GoChek 239/BlueWow 271/Wave Keys 15), DB+mirror สะอาดทั้งคู่ — สาเหตุคือหน้าเว็บค้าง state เก่า แก้ด้วยการรีเฟรชหน้า (F5) ไม่มีการแก้โค้ด (2026-09-12; live API verified, ดำเนินการโดย: Cline)
- [x] Round TIKTOK-DASH-DATA-1 — ล้างโพสต์ทดสอบ Test Serum 163 รายการออกจาก post_log (backup ครบ 167) + claim guard กัน merge ยอดซ้ำข้ามแถวในรอบซิงก์เดียว (2026-09-12; pytest 1114 passed (tiktok 9), extension 32 passed, ข้อมูล 167→4 โพสต์จริง 895 views, ดำเนินการโดย: Cline)

- [x] Round UI-POLISH-HEADER-1 — แก้ฟอนต์กล่องแดง Topbar (ถอด font-mono) + ตัด 2 Badge สินค้า + ขยายหัวข้อสินค้าเน้นๆ ใหญ่ๆ (2026-09-12; vitest 152 passed, build 3.49s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round SHOT-GAP-FIX-1 — แก้ช่องว่าง (Gap) ระหว่างช็อตใน Shot Matching Stage + 2-pass merge ป้องกันคลิปสั้นกระตุก (2026-09-13; pytest 1126 passed, ดำเนินการโดย: Antigravity (Claude Sonnet 4.6))

- [x] Round UI-LAST-UPDATED-TIMESTAMP-1 — แสดงวันที่และเวลาอัปเดตล่าสุด (Relative + Full Tooltip) ใน Dropdown ไทม์ไลน์ และบนการ์ด Tracker (2026-09-13; npm test 170 passed, build 3.92s, browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))

- [x] Round AI-PRODUCER-HUB-1 — พัฒนาเมนูใหม่ "ผู้ช่วยโปรดิวเซอร์ส่วนตัว" (AI Producer Hub & Daily Mission Center) (2026-09-13; npm test 176 passed, build 3.36s, browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round AI-PRODUCER-ELEVATION-1 — ยกระดับ Producer Hub: Spotlight Next Mission, Pacing Calculator, 1-Click Playbook Add, และ Pre-flight Editor Tips (2026-09-13; npm test 178 passed, build 3.34s, browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))

- [x] Round IDEA-REF-VAULT-1 — คลังไอเดียและเรฟ (Idea & Ref Vault), Round-Robin Diversified Queue, และ Mobile View (iPhone 15 Pro Max) (2026-09-13; npm test 180 passed, backend parity 153 passed, build 4.10s, desktop & mobile browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))

- [x] Round QUICK-REF-POLISH-1 — Redesign Impeccable Quick Ref Vault & Fix iOS Mobile Zoom (2026-09-13; npm test 180 passed, build 3.31s, desktop & mobile browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))

- [x] Round MOBILE-IMAGE-PASTE-FIX-1 — Fix Mobile Image Paste (iOS Safari files detection, ContentEditable Paste Target, Native Photo Picker Auto-Fallback, and HEIC auto-conversion) (2026-09-13; npm test 180 passed, build 3.58s, desktop & mobile browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))

- [x] Round MULTI-IMAGE-CLOUD-SYNC-1 — Multi-Image Support per Note + Mobile-to-PC Server Sync + 1-Click Copy/Share Summary for Team (2026-09-13; pytest 1 passed, npm test 180 passed, build 4.29s, desktop & mobile browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round IOS-SAFARI-CLIPBOARD-PERFECTION-1 — iOS Safari HTTP Clipboard Fallback & 1-Tap Photo Library UX (แก้ปัญหา iOS Safari บน HTTP บล็อก clipboard read โดยเพิ่ม auto-fallback เปิดคลังภาพทันที, ใส่ pointer-events-none กัน text selection ดักปุ่มวาง, และยกปุ่ม 'เลือกจากคลังภาพ' เป็น Hero Action) (2026-09-13; npm test 180 passed, build 8.59s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round PRODUCER-NOTE-DELETE-PERFECTION-1 — Make Note Delete Function Obvious & 1-Tap on Mobile & Desktop (แก้ปุ่มลบซ่อนตัว opacity-0 บนจอสัมผัส, ปรับปุ่มลบสีแดงพร้อมป้ายชัดเจน, และเพิ่มโน้ตล่าสุดพร้อมปุ่มลบใต้ฟอร์มมือถือ) (2026-09-13; npm test 180 passed, build 4.13s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round GLOBAL-PASTE-AND-DROPZONE-REWRITE-1 — Global Window Paste + Elimination of ContentEditable Text Highlight (เปลี่ยนกล่องวางเป็น Dropzone ปลอดไฮไลต์ 100%, เพิ่มระบบกด Ctrl+V วางรูปได้ทุกที่บนหน้าจอ, และปรับปรุงปุ่มวางรูปภาพให้ตรงไปตรงมา) (2026-09-13; npm test 180 passed, build 3.38s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round IOS-DIRECT-PASTE-SURFACE-PERFECTION-1 — 2-Layer Zero-Highlight iOS Native Paste Box (คืนชีพกล่องแตะวางรูปตรงๆ บน iPhone ด้วย empty contentEditable surface + non-selectable overlay) (2026-09-13; npm test 180 passed, build 3.42s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round IOS-PASTE-DEDUP-1 — แก้ปัญหาวางรูปแล้วได้รูปเบิ้ล 2 รูปบน iOS Safari (Deduplicate & Debounce Lock กัน onPaste ซ้อนกับ window listener และ onInput DOM insertion) (2026-09-13; npm test 180 passed, build 3.36s, browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round IOS-PASTE-CRASH-PREVENTION-1 — แก้ปัญหาจอดำเวลาวางรูป (React 19 reconciliation removeChild exception จาก synchronous innerHTML wipe + หุ้ม ErrorBoundary รอบ QuickRefPage + ป้องกัน Type error ใน isDuplicateImage) (2026-09-13; vitest 181 passed, build 7.89s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round WATERMARK-CONFIG-V6 — ตั้งค่าเปิด/ปิดลายน้ำ (One Click & Editor) + แก้สระ/วรรณยุกต์ลอย + บังคับตัดแคช v6 (2026-09-13; pytest 176 passed, vitest 181 passed, build 3.26s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))



- [x] Round UI-FONT-HARMONY-1 — ปรับความสอดคล้องของฟอนต์ UI ทั้งระบบตาม Global UI Font (ปราศจาก Encoding Mojibake) (2026-09-12; vitest 152 passed, build 4.57s, pytest parity 153 passed, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round UI-FONT-MONO-CLEAN-1 — กวาดล้าง font-mono ที่ครอบข้อความภาษาไทย/การ์ด KPI ทั่วทั้งระบบให้เป็นฟอนต์กลาง 100% (2026-09-12; vitest 152 passed, build 3.31s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round POSTED-CLIP-LIFECYCLE-1 — ระบบจัดการคลิปที่โพสต์แล้ว (Zero-Risk Archive & Timeline Lockout Flow) (2026-09-12; vitest 158 passed, pytest 156 passed, build 3.45s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round EXPORT-ARCHIVE-POLICY-1 — แจ้งเตือน export ค้างนาน/ดิสก์ใกล้เต็ม (Combined Time + Disk Threshold) (2026-09-12; pytest 4 passed, build 3.12s, live API verified, ดำเนินการโดย: Claude Code (Claude Sonnet 5))
- [x] Round PAGINATION-1 — เพิ่ม client-side windowing ให้ 9 list endpoint ทั่วระบบ กัน UI ช้าเมื่อข้อมูลถึงหลักร้อย (2026-09-13; pytest 1126 passed, vitest 158 passed, build ผ่านทุกจุด, ดำเนินการโดย: Claude Code (Claude Sonnet 5))
- [x] Round PAGINATION-1-VERIFY — user เช็คแอปจริงด้วยตัวเอง (เครื่องมือผมเข้าถึง localhost:5173 จาก sandbox ไม่ได้) ยืนยันปกติ (2026-09-13; user spot-check, ดำเนินการโดย: user)

- [x] Round SCRIPT-BATCH-EXPAND-1 — ระบบเจนสคริปต์ล็อตใหม่ 10 มุมมอง & ปรับระบบ Dev Server HTTP (Multi-Batch Generation & Filtering Flow) (2026-09-12; vitest 158 passed, pytest 171 passed, build 3.25s, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round SHOTLIST-GEMINI-TTS-SSOT-1 — ระบบรวมศูนย์เสียง TTS (Gemini Flash Audio SSOT): แผนถ่าย & ตัดต่อจริงใช้เสียงเดียวกัน 100% ไม่เจนซ้ำ (2026-09-12; pytest 1,125 passed, vitest 158 passed, build 3.40s, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

## Round WATERMARK-1 — ลายน้ำลิขสิทธิ์แนวตั้งถาวร (ทุกคลิปที่เรนเดอร์)

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Claude Code (Claude Sonnet 5) · สถานะ: กำลังทำ (รอ user เช็คเบราว์เซอร์จริง)

**เป้าหมาย:** เพิ่มข้อความ "สงวนลิขสิทธิ์ช่อง rizantry ห้ามคัดลอก/ดัดแปลง" แนวตั้ง (หมุน 90° อ่านบนลงล่าง) ตรงคอลัมน์ safe zone ขวา (ที่กันไว้สำหรับปุ่มไลค์/แชร์ของ TikTok อยู่แล้ว) ให้ **ทุกคลิปที่เรนเดอร์อัตโนมัติ** ไม่ต้องเปิด/ปิดเอง ไม่ใช่ overlay ที่แก้ไข/ลบได้จากอีดิเตอร์

**สิ่งที่ทำ:**
1. `scripts/subtitle_engine.py`: เพิ่ม constants `WATERMARK_TEXT/X_RATIO/Y_RATIO/FS_RATIO` + ASS Style `Watermark` + Dialogue event ที่ยิงแบบไม่มีเงื่อนไข (ไม่ผูกกับ hook/overlays ที่ผู้ใช้แก้ได้) ใช้ `\frz-90` หมุนคงที่ (ไม่มี `\t()` keyframe ต่างจาก wobble animation เดิม) ที่ตำแหน่ง x=94.5%, y=43.75% ของเฟรม
2. Bump `SUBTITLE_RENDER_CONTRACT_VERSION` v4→v5 (เปลี่ยน output contract จริง ต้อง invalidate `.ass` เก่า ตามกฎ `.agents/rules/font_text_visual_contract.md` section 4)
3. `frontend/src/components/SequencePlayer.jsx`: เพิ่ม `drawWatermark(ctx)` วาดลายน้ำเดียวกันในพรีวิว canvas (พรีวิว/เรนเดอร์ parity ตามกฎ font/text contract) เรียกจากทั้ง 2 จุดที่ `drawOverlays` ถูกเรียก
4. เจอ regression test เดิมพัง (`test_thai_stacked_marks_keep_settled_geometry_during_caption_entrance` เช็คว่าเฟรมแรกต้องไม่มี ink เลย ซึ่งลายน้ำถาวรทำให้เป็นเท็จเสมอ) — **หยุดถาม user ก่อนแก้ตามกฎ section 7** user เลือกให้ mask เฉพาะคอลัมน์ลายน้ำออกก่อนเช็ค ink_bbox แทนการลดมาตรฐานเทส
5. เขียน regression test ใหม่ 2 ตัวใน `tests/test_subtitle_artifact_contract.py` (ยืนยันลายน้ำโผล่ทุกครั้งแม้ไม่มี overlay, ยืนยัน v4 ถูก invalidate)

**Gate:**
- [x] `.venv\Scripts\python.exe -m pytest tests/test_subtitle_artifact_contract.py tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q` → 176 passed
- [x] Render จริงด้วย FFmpeg+libass (`fontsdir=02_Assets/Fonts`) + ดูเฟรมจริง → ตำแหน่ง/การหมุนตรงกับภาพตัวอย่างที่ user ส่งมา (อ่านบนลงล่าง ไม่ทับคลิป/แคปชัน)
- [x] Full backend pytest 1128 passed, `python -m compileall -q scripts` pass, `pip check` pass, `git diff --check` pass (แค่ LF/CRLF warning ไม่ใช่ error)
- [x] Frontend: vitest 178 passed, `npm run build` pass
- [ ] **ยังไม่ได้เช็คพรีวิว SequencePlayer.jsx ในเบราว์เซอร์จริง** — ทิศทางการหมุน (`ctx.rotate(Math.PI/2)`) ให้เหตุผลไว้ในโค้ดว่าตรงกับ `\frz-90` ฝั่งเรนเดอร์ แต่ยังไม่เห็นภาพจริงในอีดิเตอร์ ต้องให้ user เปิดโปรเจกต์แล้วดูว่าพรีวิวตรงกับที่เรนเดอร์จริงไหม

**Notes:** Gate ข้อ "motion ต้องดึงอย่างน้อย 3 เฟรม (เข้า/ค้าง/ออก)" ไม่ apply เพราะลายน้ำนี้หมุนคงที่ ไม่มี motion/animation ให้ดึงหลายเฟรม — ดูรูปเดียวก็พอสำหรับ static element

## Round WATERMARK-FIX-1 — แก้ชื่อช่อง rizantry → rizanntry + ทำลายน้ำจางลง + แก้สระลอย Preview

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Claude Opus 4.6) · สถานะ: เสร็จ ✅

**เป้าหมาย:**
1. แก้ชื่อช่อง `rizantry` → `rizanntry` (n สองตัว) ทั้ง backend ASS และ frontend Canvas preview
2. ปรับ alpha ลายน้ำให้จางลงเป็นลายน้ำ (เดิม ASS `&H30&` ≈ 81% opaque, Canvas 0.8) → จาง ~40% opaque เหมือนลายน้ำจริง
3. แก้สระลอยใน Preview: `drawCaptionText` ใช้ `segmentWidths` ที่วัดจากข้อความรวม pair `ั่` แต่ body ที่วาดจริงลบ tone แล้ว → advance ไม่ตรง → segment ถัดไปถูกวางผิด

**สิ่งที่แก้:**
- `scripts/subtitle_engine.py`: WATERMARK_TEXT rizantry→rizanntry, WATERMARK_ALPHA `&H30&`→`&H99&`
- `frontend/src/components/SequencePlayer.jsx`: WATERMARK_TEXT, WATERMARK_ALPHA 0.8→0.4, segmentWidths วัดจาก repaired body text

**Gate:**
- [x] pytest (subtitle_artifact_contract + preview_render_parity + preview_render_behavior): 176 passed
- [x] npm test: 180 passed
- [x] npm run build: ✓ built in 11.65s

## Round TIKTOK-MANUAL-MATCH-1 — ปุ่มจับคู่ manual ในแท็บ Performance สำหรับแถว Studio ที่ fuzzy match ไม่เจอ
วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅
- [x] Import ที่ unmatched เก็บลง pending store ใหม่ (_Docs/store.db ตาราง tiktok_pending) กันแถวหายหลังปิดแถบข้าง
- [x] API ใหม่: GET /api/tiktok-stats/pending + POST /api/tiktok-stats/attach (post_id + pending row → เก็บ video_id/url/metrics/posted_at แล้วลบ pending) + POST /ignore
- [x] API รายการคลิปในคลัง (ProductStore exported clips) สำหรับ dropdown จับคู่
- [x] Frontend PerformanceAnalyticsTab: กล่อง "ไม่เจอคู่ N แถว" + เลือกคลิปจากคลัง + ปุ่มจับคู่/เมิน (ui_clean_standard: ไม่มีสัญลักษณ์ซ้ำซ้อน) + Viral Milestone Alert 10k+
- [x] Tests: pytest (pending/attach/ignore + attach อัปเดต metrics จริง 12 passed) + frontend vitest 219 passed + build
- [x] Gate: python -m compileall -q scripts + pytest เต็ม + npm test + npm run build

## Round AI-PRODUCER-WORKFLOW-1 — Edit Note, Pin/Favorite, และ Live Update ใน Producer Hub & Quick Ref
วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅
- [x] API ใหม่: PUT /api/producer/notes/{note_id} รองรับ text, tag, productName, url, isPinned, isFavorite พร้อม optimistic concurrency check
- [x] ระบบจัดลำดับ Note อัตโนมัติ: โน้ตที่ isPinned จะถูกดึงขึ้นมาอยู่ด้านบนสุดเสมอ ทั้งฝั่ง Backend API และ Local State
- [x] UI ปุ่มปักหมุด (Pin Toggle) บนการ์ดโน้ต ทั้งใน ProducerHub และ QuickRefPage
- [x] UI หน้าต่างแก้ไขโน้ต (Edit Note Modal ใน ProducerHub และ Inline Edit Mode ใน QuickRefPage)
- [x] Tests: pytest tests/test_producer_notes_api.py (4 passed) + npm test (219 passed) + npm run build ผ่าน

## Round AI-PRODUCER-VISION-1 — ยกระดับ AI Gemini Vision วิเคราะห์ภาพเรฟใน Quick Ref Vault & Producer Hub
วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅
- [x] Backend: ระบบแปลง reference image เป็น multimodal input สำหรับ Gemini 2.5 Flash Vision (`scripts/api_producer.py`)
- [x] Backend: Prompt วิเคราะห์สไตล์ภาพ (มุมกล้อง, แบนเนอร์พาดหัว, อารมณ์, การสาธิตสินค้า) สังเคราะห์เป็นสคริปต์ 9:16 สไตล์ TikTok
- [x] Backend: ระบบ Fallback ออฟไลน์/ไร้ API key ทำงานราบรื่น 100% ป้องกัน crash
- [x] Frontend: การ์ดแสดงผล `👁️ ข้อมูลเชิงลึกจากภาพเรฟ (Visual Insights)` ใน Modal ข้อเสนอของ ProducerHub และ QuickRefPage
- [x] Tests: pytest tests/test_producer_vision_api.py (4 passed) + producer_notes_api (4 passed) + tiktok (12 passed) + vitest 219 passed + build ผ่าน 100%

## Round COVER-AI-IMAGEN-1 — AI สร้างรูปหน้าปกคลิป 9:16 ใน Cover Studio
วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅
- [x] Backend: เพิ่ม endpoint POST /api/covers/ai-generate-image สร้างภาพปก 9:16 ด้วย Imagen 3 (หรือ Smart Frame Hunt fallback) (`scripts/api_covers.py`)
- [x] Backend: ระบบ Auto-Prompting สำหรับ Commercial Product Photography อัตราส่วน 9:16 พร้อม 4 สไตล์ยอดนิยม
- [x] Frontend: เพิ่มแท็บ "AI สร้างรูป 9:16" พร้อมกล่องปรับแต่ง Prompt และปุ่มสั่งเจนภาพใน CoverStudioModal.jsx
- [x] Tests: pytest tests/test_api_covers_ai.py (2 passed) + vitest (219 passed) + build ผ่าน 100%

## Round STORAGE-OPTIMIZER-1 — ระบบล้างแคชคืนพื้นที่ดิสก์ & ความปลอดภัย Safe Storage Optimizer
วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅
- [x] Backend: เครื่องมือสแกนและล้างแคชปลอดภัย `scripts/storage_cleaner.py` (กวาดล้าง .vision_proxies, temp files, CapCut transient cache) พร้อม Rule 1 Guards ห้ามแตะ 01_Raw และ 02_Assets 100%
- [x] Backend: เชื่อมโยงเข้ากับ GET /api/analytics/storage และ POST /api/analytics/storage/purge-safe-cache
- [x] Frontend: การ์ด Safe Cache Cleaner แสดงขนาดขยะที่ล้างได้ + ปุ่มล้างคืนพื้นที่ดิสก์ใน StorageAnalyticsTab
- [x] Tests: pytest tests/test_storage_cleaner.py + test_analytics_hub.py (8 passed) + vitest (219 passed) + build ผ่าน 100%

## Round TIKTOK-STATS-SCRAPE-2 — แท็บ Performance เพิ่มลิงก์ คลิปปัง threshold + แมพ manual สำหรับ unmatched rows
วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅
- [x] Backend: เพิ่ม endpoint `GET /api/tiktok-stats/milestones` รองรับกรองคลิปปังตาม threshold (1k, 5k, 10k, 50k) พร้อมระบุระดับเทียร์ (เติบโตน่าจับตา, ดาวเด่น, ไวรัลปัง, เมกะไวรัล)
- [x] Frontend TaskContext: ระบบตรวจสอบคลิปปังอัตโนมัติ (Viral Milestone Monitor) แจ้งเตือน Toast "🔥 คลิปปังทะลุเป้า!" เมื่อยอดวิวทะลุ 10,000 วิว
- [x] Frontend ActivityCenter: เพิ่มแท็บ "🔥 คลิปปัง (N)" พร้อมปุ่มลิงก์ตรงไปยังคลิปจริงบน TikTok และไอคอน Trophy แถบแจ้งเตือน
- [x] Frontend PerformanceAnalyticsTab: ระบบจับคู่ manual rows ที่ค้าง (attach/ignore) และแสดงสถานะยอดวิว/metrics
- [x] Tests: pytest tests/test_tiktok_stats_import.py (13 passed) + vitest (222 passed) + build ผ่าน 100%

---

 - [x] Round AI-PRODUCER-TRUST-1 — Phase 1 Trust Layer เสร็จสมบูรณ์ (2026-09-13; frontend 183 passed, build 2003 modules/4.05s, compileall + browser verified, ดำเนินการโดย: Codex (GPT-5))

---

 - [x] Round AI-PRODUCER-ACTION-1 — Phase 2 Action Loop เสร็จใน production path; component-flow React mount test deferred (2026-09-13; frontend 184 passed, build 2003 modules/8.52s, browser deep-link verified, ดำเนินการโดย: Codex (GPT-5))

---

 - [x] Round AI-PRODUCER-SYNC-1 — Phase 3 Capture & Sync Reliability เสร็จสมบูรณ์ (2026-09-13; backend 3 passed, frontend 184 passed, build 2003 modules/5.74s, compileall + diff check ผ่าน, browser verified, ไม่แตะ 02_Assets/Refs, ดำเนินการโดย: Codex (GPT-5))

---

 - [x] Round AI-PRODUCER-EVIDENCE-1 — Phase 4 Evidence-first Retrospective เสร็จสมบูรณ์ (2026-09-13; frontend 185 passed, backend 3 passed, build 2003 modules/3.58s, browser evidence cards verified, ดำเนินการโดย: Codex (GPT-5))
 - [x] Round AI-PRODUCER-ACCESS-1 — Phase 5 Accessibility & Responsive Polish เสร็จสมบูรณ์ (2026-09-13; frontend 185 passed, build 2003 modules/3.85s, browser AX + Escape verified, diff check ผ่าน, ไม่เปลี่ยน font/text contract, ดำเนินการโดย: Codex (GPT-5))

---

## สรุปสถานะระบบปัจจุบัน
- ครบถ้วนทั้ง 5 ฟังก์ชันใหม่ความคุ้มค่าสูง (High-ROI Boosters):
  1. `Round BACKUP-1` (One-Click System Backup & Restore)
  2. `Round ASSET-DEDUP-1` (Media Deduplication & Safe Cleanup)
  3. `Round CALENDAR-1` (Interactive Drag-and-Drop Weekly Content Calendar)
  4. `Round HOOK-VAR-1` (AI Hook Variation & A/B Generator)
  5. `Round BATCH-RENDER-1` (One-Click Batch Angle Video Render Queue)
- ผ่านเกตทดสอบ Unit & Integration Tests ทุกระดับ: Backend 100% Pass, Frontend Vitest 152/152 Pass, Frontend Vite Build Clean
- ทุกรอบงานปฏิบัติตาม Rule 14 บันทึกชื่อ Agent Tooling และโมเดลที่ดำเนินการครบถ้วน 100%


# ๐“‹ OmniCut Pro Studio โ€” Todo เธเธฅเธฒเธ

## Round MAIN-FLOW-SCALE-1 — Render queue, export snapshot และ workspace data flow สำหรับ 220+ คลิป

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: กำลังทำ

**เป้าหมาย:** รองรับการสั่งงาน 220+ คลิปเป็นคิวที่ทน server restart โดยไม่เพิ่ม render concurrency เกิน 1 และตัดงานอ่าน/ส่งข้อมูลซ้ำที่โตตามประวัติคลิป.

### Todo

- [ ] Track A — เพิ่ม durable Render Dispatcher ในโมดูลใหม่: persist batch/item checkpoint, FIFO admission, restart recovery และไม่เปิด daemon worker ต่อ batch; แตะ `scripts/batch_render.py`, `scripts/api_batch_render.py`, `scripts/render_jobs.py`, `scripts/task_manager.py` เฉพาะ hunk ที่ตรวจว่าทับงานค้างไม่ได้
- [ ] Track B — แยก Export Catalog snapshot/canonical path identity จาก read path: GET exports และ schedule queue อ่าน index ที่พร้อมใช้ แทนการ resolve path/synchronize ทุก request; แตะ `scripts/api_exports.py`, `scripts/export_registry.py`, `scripts/api_schedule_queue.py`, `scripts/product_store.py` อย่างรักษา diff งานค้าง
- [ ] Track C — เพิ่ม client-side Workspace Data Coordinator แบบ single-flight/cache และใช้ projection ที่เหมาะกับ App/Tracker/Editor เพื่อลด full Products payload และการเรียกซ้ำ; แตะ `frontend/src/` โดยไม่ทับ pending UI ของผู้อื่น
- [ ] เพิ่ม deterministic regression tests แบบ temp storage สำหรับ queue persistence/admission, export snapshot invalidation และ data coordinator contract

### Gate

- [ ] `python -m compileall -q scripts`
- [ ] pytest เฉพาะจุดของ Track A/B และ `python -m pytest tests/ -q -p no:cacheprovider --tb=short`
- [ ] frontend targeted test, `npm test`, `npm run build`
- [ ] `git diff --check` และตรวจว่าไม่แก้/ลบไฟล์ผู้ร่วมงานนอกขอบเขต

### Notes

- Audit วัดเมื่อ 2026-09-14: status 6.8 ms, raw videos 9.1 ms, products 18.4 ms / 878 KB, exports 277 ms median (profiler 474 ms), schedule 136 ms median. Render slot ปัจจุบัน 1 active + 3 waiting และต้องคงไว้เพราะ RAM ว่างประมาณ 3.9 GB.
- Working tree มีงานค้างจำนวนมาก โดยเฉพาะ `scripts/api_exports.py`, `scripts/api_render.py`, `scripts/batch_render.py`, `scripts/product_store.py`, `frontend/src/components/ContentTrackerHub.jsx`, `frontend/src/components/editor/EditorShell.jsx`; ทุก track ต้องใช้ patch แบบ hunk-preserving และไม่ revert/format ทั้งไฟล์.

## Round RENDER-DEDUPE-1 — รวมงานซ้ำใน render pipeline

วันที่: 2026-09-15 | สั่งโดย: user | ดำเนินการโดย: Codex (GPT-5) | สถานะ: implementation เสร็จ; รอแก้ regression นอกขอบเขตเพื่อให้ full gate ผ่าน

**เป้าหมาย:** ลดงานอ่าน metadata/hash/encode ที่ทำซ้ำ โดยรักษา output, cache invalidation และ interface ของ UI/API เดิม

### Todo

- [x] เพิ่ม `MediaProbeCache` ต่อหนึ่ง render: 32 clips จาก source เดียวต้อง probe เพียงครั้งเดียว
- [x] รวม Vision hash + local cache decision เป็น `VisionRequestContext` ที่ส่งข้าม seam จาก ShotMatching ไป Matcher โดยไม่เปลี่ยน public fallback behavior
- [x] ทำ Image Motion artifact reusable ตาม fingerprint ของภาพและ cue timing; reroll subtitle ที่ไม่เปลี่ยนภาพ/เวลาไม่ encode ซ้ำ
- [x] เพิ่ม deterministic regression tests, compileall, targeted tests และ diff check

### Gate

- [x] `python -m compileall -q scripts`
- [x] pytest media probe / Vision / image motion / pipeline: 199 passed, 6 warnings
- [ ] full `python -m pytest tests/ -q -p no:cacheprovider --tb=short`: 1428 passed, 3 skipped, 1 failed ที่ `tests/test_gemini_tts_retry.py::test_all_keys_and_models_failed_raises_runtime_error` จาก TTS multi-key flow นอกขอบเขตรอบนี้
- [x] `git diff --check`; ไม่แตะไฟล์ TTS/Token Dashboard ที่ทำงานร่วมกัน

### Notes

- Evidence: `GOC01-แกะกล่องว้าว_1` มี 32 clips / 1 source, จึงมี ffprobe ซ้ำได้ 31 ครั้งต่อ render ก่อนแก้.
- Image Motion ยังไม่พบ artifact จริงใน `03_Projects`; ทำ cache contract + test ก่อนเพื่อให้พร้อมใช้โดยไม่เดา performance gain.
- Media probe / Vision / Image Motion targeted suite ผ่าน; full suite failure เกิดหลังการเปลี่ยน TTS ของงานร่วมกันและไม่อยู่ในไฟล์ของรอบนี้ จึงไม่แก้ทับเพื่อรักษา ownership.

## Round AI-PRODUCER-HUB-AUDIT-PLAN-1 — ปิด audit และ hardening Producer Hub (2026-09-14; ดำเนินการโดย: Codex (GPT-5))

## Round BG-SUBJECT-ISOLATION-3 — Preview/Render parity + usable per-clip processing

ดำเนินการโดย: Codex (GPT-5)

สถานะ: เสร็จแล้ว — เพิ่ม API ประมวลผล sequence, state persistence, Preview/Render compositing, UI control และ fallback safety

Gate: backend 1386 passed / 3 skipped, BG focused 151 passed / 3 skipped, frontend 219 passed, Vite build ผ่าน 2005 modules, compileall ผ่าน, FFmpeg fixture ตรวจ pixel แล้ว

## Round BG-SUBJECT-ISOLATION-4 — แก้ artifact ติด processing และตรวจลำดับเลเยอร์ให้ Hook อยู่หลัง Subject

ดำเนินการโดย: Codex (GPT-5)

**แผนตรวจ Artifact Lifecycle (Artifact Lifecycle Agent):** ดำเนินการโดย: Codex (GPT-5)
- [x] ตรวจ sequence worker/store และ test seam สำหรับ artifact คุณภาพต่ำแบบ read-only
- [x] ยืนยัน reproduction/contract ของ cache hit, invalidation และ re-generate โดยห้ามแตะ artifact เดิม
- [x] ถ้าพบ patch ที่ bounded ให้เพิ่ม behavior regression test และแก้เฉพาะ backend worker
- [x] รัน targeted tests, compileall และ diff check; ไม่แตะ frontend/API covers

**งานต่อรอบนี้:** dedupe งาน cutout เมื่อหลาย clip ใช้ source เดียวกัน โดยประมวลผล sequence ที่ครอบคลุมช่วง source ร่วมกัน แล้วนำผลไปผูกกลับทุก clip ที่อยู่ใน source เดียวกัน

**งานต่อรอบนี้ (Preview):** ให้ API manifest/frame อ่าน derived foreground cache namespace เดียวกับ Renderer เพื่อให้ artifact `ready` แสดงใน Preview ได้จริง

**เป้าหมาย:** เมื่อเตรียม cutout เสร็จ ระบบต้องแสดงสถานะพร้อมใช้งานจริง และวาง Hook/Text ไว้หลัง Subject ทั้ง Preview และ Render โดยไม่ทำให้คลิปที่ไม่มี artifact พัง

### Todo

**รอบแก้ไขคุณภาพ Background Isolation:** ดำเนินการโดย: Codex (GPT-5)
- [x] ปิด master switch ต้องคืนภาพต้นฉบับทั้ง Preview และ Render แม้ clip เดิมมี artifact พร้อมใช้
- [ ] ตรวจคุณภาพ mask จริงจาก rembg และแยกปัญหาขอบแตก/ดูดมือ/พื้นหลังติดออกจากปัญหา compositing
- [x] เพิ่ม regression test สำหรับ master switch และ fallback ที่ปลอดภัยก่อนปรับคุณภาพ mask
- [ ] ทดสอบ Preview/Render จาก fixture จริง แล้วค่อยสรุปแนวทางปรับ model/threshold โดยไม่ทำลายโปรเจกต์เดิม

- [x] ทำ reproduction จาก contract จริง: config → per-clip artifact → manifest/frame → compositing order
- [ ] แก้สถานะ readiness ระดับโปรเจกต์ให้สะท้อนผล artifact ระดับคลิป และป้องกัน stale processing
- [ ] แก้ลำดับ compositing ให้ Subject อยู่หน้า Hook/Text เฉพาะเมื่อ artifact พร้อม
- [x] เพิ่ม regression tests สำหรับสถานะเสร็จและลำดับ layer Preview/Render
- [x] รัน targeted tests และตรวจ diff (ยังไม่เปิดใช้ quality model ใหม่กับ artifact เดิม)

### Notes

- ตรวจพบว่า mask ของ `rembg/u2netp` บน footage ที่มือจับสายชาร์จอยู่มี false foreground สูง: ปัญหาคุณภาพ segmentation แยกจาก compositing แล้ว และยังไม่ควรเปิดใช้ artifact เดิมต่ออัตโนมัติ
- แก้ master switch ให้ `enabled: false` ระดับโปรเจกต์ชนะ config/artifact ระดับ clip ทั้ง Preview และ Render; commit `95683c6`
- Artifact เดิมที่มี RGBA/ขนาดครบแต่ segmentation คุณภาพต่ำยังถูก sequence worker มองเป็น cache hit เพราะ lifecycle ตรวจ technical validity ไม่ใช่ semantic mask quality; จึงต้องใช้ `worker_version` ใหม่เป็น explicit regeneration identity และส่ง ID ที่คืนกลับไปให้ consumer แทนการเขียนทับ ID เดิม
- แก้ `scripts/background_isolation_sequence_worker.py` ให้ publish แบบ no-clobber: ถ้า target artifact มีอยู่แล้วจะ fail closed และไม่ย้าย/ลบ/แก้ target เดิม; manifest ถูก publish เป็นขั้นสุดท้ายเพื่อให้ consumer เห็นเฉพาะ ready artifact
- เพิ่ม regression tests ใน `tests/test_background_isolation_sequence_worker.py` สำหรับ target เดิมไม่ถูกแทนที่ และ quality rerun ที่ได้ ID ใหม่พร้อมคง bytes เดิม; gate: 78 passed, 3 skipped, 1 warning, compileall ผ่าน, scoped diff check ผ่าน
- ไม่แตะ `frontend/`, `scripts/api_covers.py` หรือ `tests/test_api_covers_ai.py`; full repository diff check ยังติด blank line ที่ EOF ใน `tests/test_api_covers_ai.py` ซึ่งเป็นงานค้างนอกขอบเขต

---

## Round COVER-MINIMAL-IT-PROMPT-1 — ยกระดับ Prompt ฉากหลัง Minimal IT คมชัดสมจริง (แผ่นรองตัด Grid/ผนังระแนง Rim Light/มือจับเทค) + เทมเพลต Hook สไตล์ Tech Reviewer (Brand ขาว + Model นีออน) + แก้ UnicodeDecodeError ใน Subprocess

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย & ปัญหาที่แก้ไข:**
1. **แก้บั๊ก UnicodeDecodeError (Image 1):** ใน `scripts/api_covers.py` สายเรียก subprocess CLI สำหรับสร้างภาพ AI ติด `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9e` บนระบบ Windows ภาษาไทย (cp874) ต้องเพิ่ม `encoding="utf-8", errors="replace"` ให้ปลอดภัย 100%
2. **ชุด Prompt สไตล์ Minimal IT ระดับโปร (Image 3):** ปรับปรุง Preset Prompt ใน `CoverStudioModal.jsx` และ Backend ให้ตรงกับเรฟช่องไอที TikTok สวย คลีน ไม่เวอร์วัง เหมาะกับทุกสินค้า:
   - `🎯 แผ่นรองตัดโมเดล (Dark Cutting Mat Grid)`: แผ่นรองตัดสีเทาเข้มตารางกริดและสเกลไม้บรรทัดขาว มุมมอง 45 องศา คมชัดสไตล์รีวิวเกดเจ็ต
   - `⚡ ผนังระแนงเทค + ไฟสตูดิโอคู่ (Tech Slat Wall + Dual Rim Lights)`: ผนังระแนงไม้/แผงซับเสียงสีดำ พร้อมไฟ LED สตูดิโอขอบสีส้ม Amber และฟ้า Cyan
   - `🖐️ มือโปรจับสินค้าจริง (Handheld Tech Review Grip)`: มือจับสินค้าจริงแบบโปร ไม่บังปุ่ม/หน้าจอ แสงขอบสตูดิโอ คมชัด
   - `🏆 แท่นโชว์ดาร์กมินิมอล (Dark Minimalist Pedestal)`: แท่นวางสินค้าสีเทาเข้ม ดาร์กสปอตไลต์นุ่มนวล
   - `✨ คลีนมินิมอลสตูดิโอ (Clean Minimal Studio)`: ฉากหลังสตูดิโอโค้งสีเทาอ่อน สว่าง คมชัดระดับแคตตาล็อก
3. **รูปสินค้าจริงไม่เพี้ยน (Real Product Composite):** ระบบนำภาพสินค้าจริง (จากเฟรมวิดีโอ หรือรูป TikTok Shop) มาตัดฉากหลัง (Cutout) แล้วนำมาวางบนฉาก AI ด้วย Ambient/Contact Shadow ให้ภาพสินค้าจริงคงความคมชัด ตัวหนังสือ/ปุ่ม/โลโก้ไม่บิดเบี้ยว 100%
4. **เทมเพลต Hook สไตล์ Tech Reviewer (`tech_neon`):**
   - เพิ่มเทมเพลตข้อความ `tech_neon` ให้เลือกทั้งใน Frontend และ Backend Canvas/Pillow Renderer
   - บรรทัด 1: ชื่อแบรนด์สีขาว ตัวหนาใหญ่ ขอบดำสนิท
   - บรรทัด 2: ชื่อรุ่น/จุดเด่น สีเขียวนีออน (`#39FF14`) / ฟ้าไซแอน (`#00E5FF`) / ส้มนีออน (`#FF6B00`) / ชมพูนีออน (`#FF2A85`) เอียงสไตล์ไดนามิก
   - บรรทัด 3: หมวดหมู่/สเปกภาษาไทย (เช่น `พัดลมมือถือระบายความร้อน`, `เพาเวอร์แบงค์ 20000 mAh`, `สมาร์ทวอทช์สายลุย`)
   - ปุ่มลัด 1-Click จัดฟอร์แมต Brand / Model / Spec อัตโนมัติตามชื่อสินค้า

### Todo:
- [x] Backend (`scripts/api_covers.py`): แก้ไข `subprocess.run` ใน `_generate_image_cli` และ `_grab_frame_fallback` ให้ใส่ `encoding="utf-8", errors="replace"` ป้องกัน UnicodeDecodeError บน Windows
- [x] Backend (`scripts/api_covers.py`): เพิ่มการรองรับเทมเพลต `tech_neon` ใน `render_pro_cover` (วาดแบรนด์ขาว + รุ่นนีออน + ป้ายสเปกไทย พร้อมขอบดำคมชัด)
- [x] Frontend (`frontend/src/components/CoverStudioModal.jsx`): อัปเดตชุด Prompt Preset สำหรับ Minimal IT ทั้ง 5 สไตล์ที่แม่นยำ ละเอียด ใช้ได้กับสินค้าทุกชนิด
- [x] Frontend (`frontend/src/components/CoverStudioModal.jsx`): เพิ่มตัวเลือกเทมเพลต `tech_neon` ในระบบพรีวิว 9:16 และ 3:4
- [x] Frontend (`frontend/src/components/CoverStudioModal.jsx`): ปรับปรุงปุ่มลัดสร้างชื่อแบรนด์ + รุ่นนีออน + จุดเด่นภาษาไทย ให้กรอกข้อมูลได้ในคลิกเดียว
---

## Round CALLOUT-RESURRECT-FIX-1 — ถอดระบบ Auto-Materialize Text Overlays (แบรนด์/รุ่น โผล่กลางจอ) ออกถาวร & คืนสิทธิ์การควบคุมข้อความให้ User 100%

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์ ✅

**ที่มาและผู้ที่ทำไว้:**
- ค้นพบจากประวัติ Git commit `71b93c5` (วันที่ 13 ก.ย. 2026) โดยโมเดล **Codex (GPT-5)** ภายใต้รอบ Editorial Contracts / Tech Product Showcase
- ปัญหา: โค้ดเดิมใส่ฟังก์ชัน `_materialize_product_callouts` ใน `scripts/stages/subtitle_stage.py` ซึ่งจะดึงชื่อ Brand และ Model มาแยกคำ แล้วยัดเข้าเป็น Text Overlays พิกัดกึ่งกลางจอ (`50%, 50%`) ให้อัตโนมัติทุกครั้งที่มีการรัน Subtitle Stage หรือ Render ทำให้เมื่อผู้ใช้กดลบใน Editor UI แล้ว ข้อความ `BCD` และ `LOOP Smartband` ก็ยังถูกปลุกฟื้นคืนชีพกลับมาใหม่ซ้ำๆ

**การแก้ไขที่ทำ:**
1. **ปิดระบบ Auto-Materialize ใน Pipeline:** ปรับฟังก์ชัน `_materialize_product_callouts` ใน `scripts/stages/subtitle_stage.py` ให้เป็น pure pass-through คืนเฉพาะ overlays ที่ผู้ใช้สร้าง/กำหนดเองเท่านั้น ไม่มีการเจาะจง auto-inject Brand/Model เข้าแทร็กข้อความอีกต่อไป
2. **ปรับปรุง Test Suite:** ปรับ `tests/test_product_callout_pipeline.py` ให้ยืนยันว่าไม่มีการ auto-materialize callouts เมื่อ overlays ว่างเปล่า และรักษา overlays เดิมของผู้ใช้ไว้โดยไม่เปลี่ยนแปลง
3. **คลีนโปรเจกต์ BCD01-โปรไฟลุก_1:**
   - นำ phantom overlays ออกจาก `03_Projects/BCD01-โปรไฟลุก_1/project.json`
   - ล้างบล็อก `TextOverlayMain`, `TextOverlayShadow`, `TextOverlayPill` ออกจาก `subtitles.ass` และ `subtitles_v1.ass`
4. **การทดสอบ:**
   - `pytest tests/test_product_callout_pipeline.py` (3 passed)
   - `pytest tests/test_product_callout_render.py` (5 passed)
   - `pytest tests/test_preview_render_parity.py` (153 passed)
   - `npm test -- --run` (230 passed)
   - `npm run build` (ผ่าน 100%)
