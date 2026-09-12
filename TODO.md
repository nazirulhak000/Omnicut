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

---

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

## Round SHOT-GAP-FIX-1 — แก้ช่องว่าง (Gap) ระหว่างช็อตใน Shot Matching Stage

**วันที่:** 2026-09-12 · **Agent:** Antigravity (Claude Sonnet 4.6) · **สถานะ:** กำลังดำเนินการ

**Root Cause ที่ค้นพบ:**
1. `cut_points[0] = 0.0` (hardcoded) แทนที่จะเป็น `active_cues[0].start` — ทำให้ shot แรกเริ่มเร็วกว่าเสียงจริง (เช่น 0.23s) ส่งผลให้ clip แรกมีช่วงเงียบ
2. MERGE_TOLERANCE 1.15 × MAX_SHOT_DURATION=2.5 = 2.875s ใช้ไม่ได้จริง — กลุ่มสั้นมาก (เช่น `นะครับ` 0.491s) ถูกขนาบด้วยกลุ่มยาว 2.5+ วิ ทำให้ไม่สามารถ merge ได้ และกลายเป็น shot 0.491s ที่ไม่ควรเกิด

**แผนแก้ไข:**
- [ ] แก้ `cut_points = [0.0]` → `cut_points = [float(active_cues[0].get("start", 0.0))]` ใน `scripts/stages/shot_matching_stage.py` line 318
- [ ] แก้ MERGE_TOLERANCE ให้ force-merge กลุ่มที่สั้นมาก (< MIN_SHOT_DURATION * 0.5 = 0.75s) แม้ผลรวมจะเกิน MAX_SHOT_DURATION — เพราะดีกว่ามีช็อตที่สั้นกว่า MIN
- [ ] Gate: python -m compileall -q scripts + pytest (ไม่แตะ vitest/build เพราะเป็น backend pure)
- [x] Round UI-FONT-HARMONY-1 — ปรับความสอดคล้องของฟอนต์ UI ทั้งระบบตาม Global UI Font (ปราศจาก Encoding Mojibake) (2026-09-12; vitest 152 passed, build 4.57s, pytest parity 153 passed, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round UI-FONT-MONO-CLEAN-1 — กวาดล้าง font-mono ที่ครอบข้อความภาษาไทย/การ์ด KPI ทั่วทั้งระบบให้เป็นฟอนต์กลาง 100% (2026-09-12; vitest 152 passed, build 3.31s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round POSTED-CLIP-LIFECYCLE-1 — ระบบจัดการคลิปที่โพสต์แล้ว (Zero-Risk Archive & Timeline Lockout Flow) (2026-09-12; vitest 158 passed, pytest 156 passed, build 3.45s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round EXPORT-ARCHIVE-POLICY-1 — แจ้งเตือน export ค้างนาน/ดิสก์ใกล้เต็ม (Combined Time + Disk Threshold) (2026-09-12; pytest 4 passed, build 3.12s, live API verified, ดำเนินการโดย: Claude Code (Claude Sonnet 5))

- [x] Round SCRIPT-BATCH-EXPAND-1 — ระบบเจนสคริปต์ล็อตใหม่ 10 มุมมอง & ปรับระบบ Dev Server HTTP (Multi-Batch Generation & Filtering Flow) (2026-09-12; vitest 158 passed, pytest 171 passed, build 3.25s, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

- [x] Round SHOTLIST-GEMINI-TTS-SSOT-1 — ระบบรวมศูนย์เสียง TTS (Gemini Flash Audio SSOT): แผนถ่าย & ตัดต่อจริงใช้เสียงเดียวกัน 100% ไม่เจนซ้ำ (2026-09-12; pytest 1,125 passed, vitest 158 passed, build 3.40s, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))

## Round TIKTOK-MANUAL-MATCH-1 — ปุ่มจับคู่ manual ในแท็บ Performance สำหรับแถว Studio ที่ fuzzy match ไม่เจอ
- [ ] Import ที่ unmatched เก็บลง pending store ใหม่ (_Docs/store.db ตาราง tiktok_pending) กันแถวหายหลังปิดแถบข้าง
- [ ] API ใหม่: GET /api/tiktok-stats/pending + POST /api/tiktok-stats/attach (post_id + pending row → เก็บ video_id/url/metrics/posted_at แล้วลบ pending) + POST /ignore
- [ ] API รายการคลิปในคลัง (ProductStore exported clips) สำหรับ dropdown จับคู่
- [ ] Frontend PerformanceAnalyticsTab: กล่อง "ไม่เจอคู่ N แถว" + เลือกคลิปจากคลัง + ปุ่มจับคู่/เมิน (ui_clean_standard: ไม่มีสัญลักษณ์ซ้ำซ้อน)
- [ ] Tests: pytest (pending/attach/ignore + attach อัปเดต metrics จริง) + frontend vitest + build
- [ ] Gate: python -m compileall -q scripts + pytest เต็ม + npm test + npm run build

## Round PAGINATION-1 (แผนอยู่ใน [PAGINATION_PLAN.md](file:///d:/Winona/Programmer/Capcut/PAGINATION_PLAN.md)) — เพิ่ม limit/pagination ให้ list endpoint ทั่วระบบ

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: วางแผนแล้ว ยังไม่ลงมือ (user สั่งให้ทำแผนก่อน ยังไม่ให้แก้โค้ด)

**เป้าหมาย:** กัน Export Gallery และหน้าอื่นๆ ที่ list โต (products, raw vault, schedule queue, tiktok-stats) ช้าลงเมื่อข้อมูลถึงหลักร้อย — ดูรายละเอียด phase/priority/endpoint ทั้งหมดใน `PAGINATION_PLAN.md`

- [x] Phase 1 item 1: `/api/exports` + `ExportGallery.jsx` — **client-side windowed rendering แทน backend limit/offset** (พบว่า `exportsList` ถูก merge/aggregate ข้ามคอมโพเนนต์ ตัด limit ที่ backend จะพังข้อมูล ดูเหตุผลเต็มใน `PAGINATION_PLAN.md`) (2026-09-12; vitest 158 passed, build 3.27s, ดำเนินการโดย: Claude Code (Claude Sonnet 5))
- [x] Phase 1 item 2: `/api/products` (ผ่าน `ContentTrackerHub.jsx`) — **client-side windowed rendering** เหมือนกัน (kanban เป็นบอร์ดจัดการงาน ต้องเห็นทุกใบเพื่อทำงาน ตัด limit ที่ backend จะทำให้หาการ์ดเก่าไม่เจอ) — เพิ่ม windowing 2 จุด: kanban "Flat Cards List" (คอลัมน์ candidate/in_production/rendered ที่ไม่มี today-filter/accordion มาก่อน) ทีละ 20 การ์ดต่อคอลัมน์ + Table view (mobile card feed + desktop table) ทีละ 40 แถว ทั้งคู่มีปุ่ม "โหลดเพิ่ม" (2026-09-12; vitest 158 passed, build 7.25s, ดำเนินการโดย: Claude Code (Claude Sonnet 5); หมายเหตุ: ยังไม่ได้ browser-verify เพราะ dev server ไม่ตอบ HTTP request ตอนเช็ค — คาดว่า terminal ค้าง ไม่ใช่โค้ดพัง)
- [x] Phase 1 item 3: `/api/videos` (`MediaPickerModal.jsx`) — audit เดิมชี้ผิดว่า consumer คือ `MediaAssetsHub.jsx` (จริงๆ นั่นคือ `/api/assets/all`) แก้ไว้ในเกณฑ์แล้ว — เป็น picker modal เลือกคลิปเดียว ไม่มี aggregate ข้ามจุด → **client-side windowed rendering** ทีละ 40 การ์ด + ปุ่มโหลดเพิ่ม, reset เมื่อ search/tab เปลี่ยน (2026-09-12; vitest 158 passed, build 6.14s, ดำเนินการโดย: Claude Code (Claude Sonnet 5))
- [x] Phase 1 item 4: `/api/raw-vault` (`RawVaultPanel.jsx`) — เช็ค docstring endpoint พบว่า O(products×files) ที่ audit เดิมเตือนไว้ **แก้เป็น O(products+files) ไปแล้วในโค้ดจริง** (ไม่ใช่ปัญหาเปิดอยู่) เหลือแค่ประเด็น pagination — คลัง raw footage มี aggregate count ข้ามจุด (ผูกสินค้า/คลิปอิสระ) เหมือนกัน → **client-side windowed rendering** ทีละ 40 การ์ด + ปุ่มโหลดเพิ่ม (2026-09-12; vitest 158 passed, build 6.14s, ดำเนินการโดย: Claude Code (Claude Sonnet 5))
- [x] Phase 1 item 5: schedule-queue (`ScheduleAgenda.jsx`) — calendar view สัปดาห์อยู่แล้วโดยธรรมชาติ (7 วัน bounded), list view ผูกกับ `activeQueue` (ยังไม่โพสต์ ไม่โตมาก) ความเสี่ยงจริงอยู่ที่ modal "คลิปที่โพสต์แล้ว" (`postedQueue`, ไม่เคย prune) → windowed ทีละ 50 แถว + ปุ่มโหลดเพิ่ม, reset ทุกครั้งที่เปิด modal (2026-09-12; vitest 158 passed, build 4.23s, ดำเนินการโดย: Claude Code (Claude Sonnet 5))
- [x] Phase 1 item 6: `/api/tiktok-stats/latest` (`PerformanceAnalyticsTab.jsx`) — KPI การ์ด (totalViews, avgEngagement) อ่านจาก `richPosts` เต็มเหมือนเดิม, windowed เฉพาะตารางแสดงผลทีละ 50 แถว + ปุ่มโหลดเพิ่ม, reset เมื่อ sync ข้อมูลใหม่ (2026-09-12; vitest 158 passed, build 4.23s, ดำเนินการโดย: Claude Code (Claude Sonnet 5))
- [x] **Phase 1 ครบ 6/6 endpoint แล้ว** — ยังไม่ได้ browser-verify item 2-6 เลย (dev server ไม่ตอบ HTTP ตลอดรอบนี้ ดูเหมือน terminal ค้าง ไม่ใช่โค้ดพัง) — ต้องเปิดแอปจริงเช็คก่อนถือว่าปิดสนิท 100%
- [ ] Phase 2 (ยังไม่เริ่ม)
- [ ] Phase 2 (Medium): `/api/tiktok-stats/clip-candidates`, `/api/assets/all`, `/assets/duplicates/scan`
- [ ] Phase 3 (Low, ไม่รีบ): `/api/posts*` (dead code ตอนนี้), `/api/tiktok-stats/pending`, `/backup/list`, `/api/tasks/active` (ปลอดภัยแล้ว)

## Round TIKTOK-STATS-SCRAPE-2 (backlog)
## Round TIKTOK-STATS-SCRAPE-2 (backlog) — แท็บ Performance เพิ่มลิงก์ คลิปปัง threshold + แมพ manual สำหรับ unmatched rows
- [ ] หลังใช้งานจริง: ปุ่มจับคู่ manual ในแท็บ Performance สำหรับแถวที่ fuzzy match ไม่เจอ
- [ ] แจ้งเตือนคลิปปังเกิน threshold (เช่น 10k views) ใน Activity Center

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


