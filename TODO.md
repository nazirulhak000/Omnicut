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
- [ ] Import ที่ unmatched เก็บลง pending store ใหม่ (_Docs/store.db ตาราง tiktok_pending) กันแถวหายหลังปิดแถบข้าง
- [ ] API ใหม่: GET /api/tiktok-stats/pending + POST /api/tiktok-stats/attach (post_id + pending row → เก็บ video_id/url/metrics/posted_at แล้วลบ pending) + POST /ignore
- [ ] API รายการคลิปในคลัง (ProductStore exported clips) สำหรับ dropdown จับคู่
- [ ] Frontend PerformanceAnalyticsTab: กล่อง "ไม่เจอคู่ N แถว" + เลือกคลิปจากคลัง + ปุ่มจับคู่/เมิน (ui_clean_standard: ไม่มีสัญลักษณ์ซ้ำซ้อน)
- [ ] Tests: pytest (pending/attach/ignore + attach อัปเดต metrics จริง) + frontend vitest + build
- [ ] Gate: python -m compileall -q scripts + pytest เต็ม + npm test + npm run build

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


