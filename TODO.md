# 📋 OmniCut Pro Studio — Todo กลาง

สมุดบันทึกรอบงานที่ **ยังไม่เสร็จ** ของโปรเจกต์นี้ — ทุกงานต้องผ่านไฟล์นี้ก่อนแตะโค้ด

| ไฟล์ | ใช้ทำอะไร |
| :--- | :--- |
| **TODO.md** (ไฟล์นี้) | งานที่ยังไม่เสร็จ + Backlog — เขียนแผนลงที่นี่ก่อนลงมือ |
| [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md) | รอบที่ปิดแล้ว ย้ายบล็อกเต็มไปเก็บไว้ที่นั่น ห้ามแก้ย้อนหลัง |
| [TEMPLATE_MOTION_PLAN.md](file:///d:/Winona/Programmer/Capcut/TEMPLATE_MOTION_PLAN.md) | แผนยาวของงาน motion ข้อความ (Round 3–7) — เหตุผลและตัวเลขที่วัดมา |
| [SYSTEM_AUDIT_2026-09-09.md](file:///d:/Winona/Programmer/Capcut/SYSTEM_AUDIT_2026-09-09.md) | รายงาน DB/Infra/System audit เต็ม (4-agent, read-only) |
| [SYSTEM_AUDIT_FIX_PLAN.md](file:///d:/Winona/Programmer/Capcut/SYSTEM_AUDIT_FIX_PLAN.md) | แผนแก้ตาม audit ข้างบน แบ่ง 10 stream ขนาน + phase สำหรับยิง agent พร้อมกัน |
| [SYSTEM_AUDIT_2026-09-15.md](file:///d:/Winona/Programmer/Capcut/SYSTEM_AUDIT_2026-09-15.md) | Audit ปัจจุบัน 17 ส่วน พร้อม baseline และลำดับแก้ไข |
| [PRO_EDITOR_STYLE_PLAN.md](file:///d:/Winona/Programmer/Capcut/PRO_EDITOR_STYLE_PLAN.md) | แผนยกระดับคุณภาพการตัดต่ออัตโนมัติด้วย Editorial Style Preset กลาง |
| [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md) | กติกาว่าหนึ่งรอบทำยังไง ติ๊กยังไง ปิดรอบยังไง |

---

## สถานะรวม

- [x] Round WATERMARK-1 - permanent vertical watermark verified in Render and live Preview (2026-09-15; executed by: Claude Code + Codex (GPT-6))
- [x] Round WATERMARK-BROWSER-VERIFY-20260915 - verified static watermark in the live SequencePlayer browser preview (2026-09-15; executed by: Codex (GPT-6); report: WATERMARK_BROWSER_VERIFY_2026-09-15.md)
- [x] Round AUDIT-LEDGER-CLOSEOUT-20260915 - reconciled audit checkboxes with verified gates and recorded deferred medium-term work (2026-09-15; executed by: Codex (GPT-6))
- [x] Round STRICT-GEMINI-DEFAULT-NO-EDGE-TTS-GUARD-1 - Gemini TTS is the default at every public entry point; Edge-TTS requires explicit opt-in (2026-09-15; backend 392 passed, frontend 246 passed, compileall passed, executed by: Codex (GPT-6))
- [x] Round MAIN-PAGE-VOICE-TYPE-INDICATOR-1 — แสดงสัญลักษณ์ระบุประเภทเสียง (Gemini TTS vs Edge-TTS vs ยังไม่มีเสียง) บนหน้าหลัก ทั้งการ์ดรายการมุมและการ์ดสคริปต์ โดยไม่ต้องกดเข้าไปดูด้านใน (2026-09-15; backend 4 passed, frontend 246 passed, build 2,007 modules/3.34s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round EDGE-TTS-DETECT-AND-UPGRADE-BADGE-1 — ตรวจจับเสียง Edge-TTS เดิม + แสดง Badge เตือนทั้งในหน้าสคริปต์และในแผนถ่าย พร้อมอัปเกรดเป็น Gemini TTS (2026-09-15; backend 4 passed, frontend 246 passed, build 2,007 modules/3.32s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round SKIP-RENDERED-POSTED-AUDIO-GEN-1 — ข้ามการสร้างเสียงพากย์สำหรับคลิปที่เสร็จ (rendered) หรือโพสต์แล้ว (posted) และตัดออกจากตัวนับขาดเสียง (2026-09-15; backend 3 passed, frontend 246 passed, build 2,007 modules/3.59s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round SYSTEM-AUDIT-REMEDIATION-20260915 — แก้ findings ใน System Audit 2026-09-15 ตามเฟส; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P0-20260915 — ป้องกัน SQLite data loss, upload overwrite และ media secret disclosure; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P1-RECOVERY-20260915 — ป้องกัน task registry เสียทำ startup ล้ม และกู้ manifest จาก backup-only; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P1-BATCH-20260915 — ปิด race ตอน batch dispatcher กำลัง idle-exit; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P2-CUTOUT-20260915 — กู้ publish ที่ค้างและ deduplicate งานตัดพื้นหลัง; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P3-MEDIA-RANGE-20260915 — ทำ HTTP Range parser ให้ไม่คืน 500 สำหรับ request ปกติ/ผิดรูปแบบ; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P6-BACKUP-WAL-20260915 - SQLite backup includes WAL pages and fails closed when snapshot API errors (10 backup/API tests passed; compileall + diff check passed); agent: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P4-WORKSPACE-CACHE-20260915 — กัน response เก่าเขียนทับ cache หลัง invalidate; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P4-AUTOSAVE-AUTH-20260915 — ส่ง API key กับ lifecycle autosave; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P4-RENDER-POLLING-20260915 — กันผลตอบกลับ polling ของ render job เก่าเขียนทับงานใหม่; ดำเนินการโดย: Antigravity (GPT-5.6)
- [x] Round SYSTEM-AUDIT-P4-FRAME-RETRY-20260915 — ทำให้ cached background-isolation frame ที่โหลดพลาด retry แบบมี backoff และล้าง timer ตอน unmount; ดำเนินการโดย: Antigravity (GPT-5.6)
- [x] Round SYSTEM-AUDIT-P5-ANALYTICS-MAPPING-20260915 — แก้ analytics trend chart ให้ส่ง key ตรงกับ AreaLineChart (frontend 237 passed; build 2.63s); ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P5-READINESS-SCAN-20260915 — ลดการสแกน frame ซ้ำใน readiness endpoint (backend 50 passed, 3 skipped); ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P5-PREVIEW-CACHE-20260915 — จำกัด cache frame ของ Preview 120 รายการพร้อมยกเลิก timer/revoke URL ตอน eviction; ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P5-QR-A11Y-20260915 — เพิ่ม dialog semantics, Escape และ focus กลับสำหรับ QR modal (frontend 238 passed; build 2.63s); ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P6-REGRESSION-CONTRACT-20260915 — แยก full-gate failures และแก้เฉพาะ contract regression ที่ยืนยันได้ (workspace contract subset 26 passed; full clone failures classified as stale/missing fixtures); ดำเนินการโดย: Codex (GPT-6)
- [x] Round SYSTEM-AUDIT-P6-SOURCE-BOUNDARY-20260915 — จำกัด source background-isolation ให้อยู่ใน workspace media roots และป้องกัน symlink escape (66 passed, 4 skipped); ดำเนินการโดย: Codex (GPT-6)
- [x] Round BATCH-TTS-AUDIO-PREGEN-1 — ระบบ Batch เตรียมเสียงพากย์อัตโนมัติ พร้อมตัวเลือกเสียง (default: Puck) & พักรอ 429 Cooldown อัตโนมัติใน background task (2026-09-15; backend 13 passed, frontend 242 passed, build 2,007 modules/3.04s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round STALE-RENDER-RESUME-CLEANUP-1 — ป้องกันสถานะค้าง 'กำลังตรวจสอบสถานะการเรนเดอร์...' 10% เมื่อเปิดโปรเจกต์อื่น/หลังรีสตาร์ต (2026-09-15; frontend vitest 239 passed, build 2,007 modules/2.97s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round IMAGE-MOTION-PROGRESS-OPTIMIZE-1 — รายงานความคืบหน้ารายช็อต (Progress Callback) ขณะแปลงภาพนิ่งเป็นวิดีโอ 9:16 Ken-Burns + เร่งความเร็ว FFmpeg & ปิดการแสดง Error 404 หลอกใน Editor (2026-09-15; backend 17 passed, compileall ผ่าน, frontend 237 passed, build 2,007 modules ผ่าน, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro))
- [x] Round GEMINI-TTS-NO-FALLBACK-LOUD-ERROR-1 — ยกเลิก Edge-TTS Fallback & แสดง Error แจ้งเตือนเวลาลิมิต Gemini TTS + ซิงค์เสียงเริ่มต้นแผนถ่าย (2026-09-15; backend 50 passed, frontend 232 passed, build 2,007 modules/3.18s, compileall ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round UI-FONT-HARMONY-ALL-1 — กวาดล้าง font-mono และผสานฟอนต์กลาง (Prompt) ทั่วทั้งระบบ 100% ครบทุกแดชบอร์ดและหน้าจอ (2026-09-15; frontend vitest 232 passed, build 2.83s ผ่าน, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round GEMINI-TTS-MULTIKEY-ALERT-1 — ปรับระบบ Multi-Key Failover (ลอง 3.1 ทุก Key ก่อนลดเป็น 2.5) + แจ้งเตือน AI Rate-Limit/Quota บน Token Dashboard (2026-09-15; backend 20 passed, frontend 232 passed, build 2,007 modules/2.68s, compileall ผ่าน, live synthesis verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash))
- [x] Round SCHEDULE-FLEXIBLE-SLOTS-1 — ตั้งเวลาโพสต์เริ่มต้น 5 ช่วง และเพิ่ม/ลบช่วงรายวัน (2026-09-14; backend schedule 10 passed, frontend 230 passed, compileall ผ่าน, build 2,005 modules/3.25s, ดำเนินการโดย: Codex (GPT-5))
- [x] Round SCHEDULE-DEFAULT-RESET-1 — ปรับเทมเพลตเวลาที่บันทึกไว้ทั้งหมดเป็นชุดแนะนำ 5 ช่วง (2026-09-14; อัปเดต 2 สัปดาห์ × 7 วันครบ, API/UI verified, ไม่กระทบคิวคลิป, ดำเนินการโดย: Codex (GPT-5))
- [x] Round COVER-TIMELINE-PRE-RENDER-1 — สร้างหน้าปกจากเฟรมจริงใน Timeline ก่อน Render (2026-09-14; backend cover 8 passed, frontend 230 passed, build 2,006 modules, detector พบเฉพาะคำเตือนเดิม, browser unavailable, ดำเนินการโดย: Codex (GPT-5))

- [x] Round COVER-RENDER-REQUIRES-COVER-1 — บังคับสร้างและบันทึกหน้าปกก่อน Render (2026-09-14; frontend 230 passed, build 2,006 modules/3.13s, diff check ผ่าน, ดำเนินการโดย: Codex (GPT-5))

- [x] Round TRACKER-LARGE-DATA-PERF-1 — ลดเวลาเปิด Content Tracker เมื่อมีคลิปจำนวนมาก (2026-09-14; `/api/exports` 2.6s → 0.28–0.37s ที่ 27 ไฟล์, tracker product+queue 0.15–0.22s, backend 1,417 passed/3 skipped, frontend 230 passed, build 2,006 modules, ดำเนินการโดย: Codex (GPT-5))

- [x] Round MAIN-FLOW-SCALE-1 — ทำคิว Render ที่ทน restart และลด read-path ที่โตตามจำนวนคลิป (2026-09-14; ดำเนินการโดย: Codex (GPT-5)) (full backend gate: 1512 passed, 5 skipped, 29 warnings; executed by: Codex (GPT-6))
- [x] Round MAIN-FLOW-SCALE-TRACK-C-PROJECTION-20260915 - shared Workspace Data Coordinator wired to App, Content Tracker, Product Flow, and Editor; ดำเนินการโดย: Codex (GPT-6)
- [x] Round RENDER-DEDUPE-1 — ตัดงาน probe, Vision cache และ Image Motion ที่ทำซ้ำ (2026-09-15; ดำเนินการโดย: Codex (GPT-5))

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
- [x] Round AI-PRODUCER-HUB-AUDIT-READONLY-20260915 - Evidence-first read-only audit completed; findings recorded in AI_PRODUCER_HUB_AUDIT_2026-09-15.md; hardening scope remains pending (executed by: Codex (GPT-6))
- [x] Round AI-PRODUCER-HUB-AUDIT-PLAN-1 — ตรวจสอบการใช้งาน AI Producer Hub และจัดทำแผนยกระดับแบบ evidence-first (2026-09-13; วิเคราะห์โค้ด + browser snapshot แล้ว, รออนุมัติ scope, ดำเนินการโดย: Codex (GPT-5)) (read-only findings and evidence-first hardening plan recorded in AI_PRODUCER_HUB_AUDIT_2026-09-15.md; executed by: Codex (GPT-6))
- [x] Round AI-PRODUCER-HUB-HARDENING-1 - Implement SSRF/local-path containment, notes concurrency/rollback, and mobile input hardening from the audit; executed by: Codex (GPT-6) (SSRF/private-address and local-path containment implemented; 12 Producer tests passed; compileall passed; executed by: Codex (GPT-6))
- [x] Round BG-SUBJECT-ISOLATION-4 - close artifact lifecycle and real Preview/Render fixture gate (2026-09-15; executed by: Codex (GPT-6); report: BG_SUBJECT_ISOLATION_FIXTURE_REPORT_2026-09-15.md)
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

## Round BATCH-TTS-AUDIO-PREGEN-1 — ระบบ Batch เตรียมเสียงพากย์อัตโนมัติ พร้อมตัวเลือกเสียง (default: Puck) & พักรอ 429 Cooldown อัตโนมัติใน background task

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

### ปัญหาที่พบ
1. **คอขวดตอนตัดต่อ & คอขวด 429 Rate Limit:** เวลาเริ่มตัดต่อต้องรอเจนเสียงพากย์ทำให้ช้า แต่พอกดแผนถ่ายเพื่อเตรียมเสียงพากย์ล่วงหน้าทีละมุม จะติด Rate Limit 429 (Google Gemini API RPM ~10-15) ระบบเดิมตัดจบเป็น Error ทันที ผู้ใช้ต้องคอยเฝ้าจอรอนับถอยหลังแล้วกดเองทีละมุม
2. **ไม่มีฟังก์ชันเตรียมเสียงแบบ Batch รวดเดียว:** ในหน้าสินค้ามี 10 สคริปต์ แต่ต้องกดทีละมุม ขาดปุ่มสั่งรันคิวเบื้องหลังแบบรวมศูนย์ที่สามารถข้ามมุมที่เคยมีเสียงแล้ว และพักรออัตโนมัติเมื่อติด Rate Limit

### แผนแก้ไข
- [x] ใน `scripts/api_shot_lists.py`: เพิ่ม Endpoint `POST /api/products/{product_id}/batch-generate-audio` รับ `voice_preset` (default: Puck), `ad_tone`, `batch_index`, `force_regenerate`
- [x] ใน `scripts/api_shot_lists.py`: สร้าง `_execute_batch_generate_audio_worker` สแกนมุม กรองข้ามมุมที่มีเสียงอยู่แล้วใน `ShotListsStore` และวนเจนเสียง
- [x] ใน `scripts/api_shot_lists.py` และ `gemini_tts_engine.py`: ดักจับ Rate Limit 429 ไม่ตัดจบ แต่เข้าโหมดพักรอ (Sleep Cooldown) ตามเวลาที่ Google แนะนำ พร้อมอัปเดตเวลานับถอยหลังบน TaskManager ให้เห็นสดๆ แล้ว retry ทำงานต่อจนครบทุกมุม
- [x] ใน `frontend/src/api.js`: เพิ่ม API client `batchGenerateAudio`
- [x] ใน `frontend/src/components/ProductToClip.jsx`: เพิ่มแถบ Action Bar พร้อมตัวเลือกเสียง (Voice Selector Dropdown ดีฟอลต์ Puck) และปุ่ม `เตรียมเสียงพากย์` (Batch TTS) แสดงจำนวนมุมที่ขาด/พร้อม และ progress bar นับถอยหลังเมื่อติด 429
- [x] รัน unit tests ทั้ง backend และ frontend ให้ผ่าน 100% (backend 13 passed, frontend 242 passed, build 2,007 modules/3.04s)

## Round STALE-RENDER-RESUME-CLEANUP-1 — ป้องกันสถานะค้าง 'กำลังตรวจสอบสถานะการเรนเดอร์...' 10% เมื่อเปิดโปรเจกต์อื่น/หลังรีสตาร์ต

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

### ปัญหาที่พบ
1. **สถานะค้าง 'กำลังตรวจสอบสถานะการเรนเดอร์...' 10%:** เมื่อเปิดโปรเจกต์ (เช่น `LOG02-เจาะกลุ่ม_1`) `useRenderJob` ดึง `storedJobId` เก่าที่ค้างใน localStorage (ซึ่งมาจากโปรเจกต์อื่นหรือเซิร์ฟเวอร์รอบก่อน) มาเซ็ต `isRendering = true` และ `message = 'กำลังตรวจสอบสถานะการเรนเดอร์...'` ทันที ทั้งที่ใน backend และ Activity Center (`กิจกรรม 36`) ไม่มีงานเรนเดอร์ใดๆ ทำงานอยู่
2. **การกู้คืนข้ามโปรเจกต์:** `getActiveJob` คืนค่า jobId ใดๆ ในแท็บโดยไม่สนว่า projectKey ตรงกับโปรเจกต์ที่กำลังเปิดอยู่หรือไม่
3. **ขาดการเคลียร์สถานะเมื่อ poll ล้มเหลว/unmount:** ใน `onError` หากได้ error อื่น หรือตอน effect cleanup ไม่ได้รีเซ็ต `jobStatus` และ `isRendering` ทำให้ UI ค้าง 10% ตลอดเวลา

### แผนแก้ไข
- [x] ใน `frontend/src/hooks/useRenderJob.js`: ตรวจสอบ `jobEntry.projectKey` ผ่าน `getActiveJobEntry()` ก่อนกู้คืนงานเรนเดอร์เก่า ถ้าไม่ตรงกับโปรเจกต์ปัจจุบันให้ข้ามและเคลียร์สถานะ
- [x] ใน `useRenderJob.js`: เมื่อเกิด error (404/401/network limits) ให้รีเซ็ต `setJobStatus(null)`, `setIsRendering(false)` และ `clearActiveJob(targetProject)`
- [x] ใน `useRenderJob.js`: ตอน effect cleanup หรือ project switch ให้เคลียร์ `jobStatus` และ `isRendering` ป้องกัน zombie timer
- [x] รัน unit tests ทั้งหมดให้ผ่าน 100% (frontend 239 passed, build 2,007 modules/2.97s ผ่าน)

## Round IMAGE-MOTION-PROGRESS-OPTIMIZE-1 — รายงานความคืบหน้ารายช็อต (Progress Callback) & เร่งความเร็ว FFmpeg ขณะแปลงภาพนิ่งเป็นวิดีโอ 9:16 + ซ่อน Error 404 หลอกใน Editor

Date: 2026-09-15 | requested by: user | executed by: Antigravity (Gemini 2.5 Pro) | status: complete

### ปัญหาที่พบ
1. **ค้างที่ 73% นาน >4 นาที:** เมื่อสินค้าเป็นภาพนิ่งและสคริปต์มี 16 ท่อน `ImageMotionEngine` สั่ง FFmpeg เรนเดอร์แยก 16 ช็อต (`seg_000` ถึง `seg_015`) โดยไม่มี progress callback ย่อย ทำให้ UI นิ่งสนิทที่ 70-73% ผู้ใช้นึกว่าระบบค้าง
2. **Error 404 หลอกบนหัวจอ Editor:** ขณะเริ่มตัดต่อ `EditorShell` พยายามโหลด `getProject(newProjectName)` ทันที ทั้งที่วิดีโอยังเรนเดอร์ไม่เสร็จ จึงได้ 404 และแสดงเป็นแถบแดง `Request failed with status code 404`

### แผนแก้ไข
- [x] เพิ่ม `progress_callback` ใน `ImageMotionEngine.ensure_motion_video_from_images` และ `generate_motion_video_from_images`
- [x] ปรับจูน FFmpeg preset เป็น `ultrafast` สำหรับภาพนิ่ง และข้าม segment ที่มีไฟล์สมบูรณ์แล้ว (resume ได้ทันที)
- [x] เชื่อมโยง `ShotMatchingStage` ส่งความคืบหน้ารายช็อต (`🖼️ [Image Motion] สร้างวิดีโอจากภาพสินค้า ช็อตที่ X/Y...`)
- [x] ใน `frontend/src/components/editor/EditorShell.jsx` และ `useProjectLoader.js`: ซ่อน loadError เมื่อยังไม่มีโปรเจกต์เปิด หรือกำลังเรนเดอร์ และใช้ friendlyMessage
- [x] รัน unit tests ทั้งหมดผ่าน 100% (backend 17 passed, compileall ผ่าน, frontend 237 passed, build 2,007 modules ผ่าน)

## Round SYSTEM-AUDIT-REMEDIATION-20260915 — ปิด findings จาก Audit ปัจจุบัน

Date: 2026-09-15 | requested by: user | executed by: Codex (GPT-6) | status: complete for bounded remediation; P03/P05 deferred

อ้างอิง: [SYSTEM_AUDIT_2026-09-15.md](SYSTEM_AUDIT_2026-09-15.md)

- [x] เฟส 0: บันทึกรายงาน 17 ส่วนและสร้างแผนงานใน TODO นี้
- [x] Phase 1: P0 safety and data durability verified by the full backend gate (1512 passed, 5 skipped); isolated clone failures were fixture/environment blockers.
- [x] Phase 2: startup/task recovery and batch processing verified by focused recovery/batch gates and the full backend gate.
- [x] Phase 3: cutout retry, cancellation, progress, cache, and deduplication verified by focused background-isolation gates.
- [x] Phase 4: autosave, polling, workspace cache, and client error recovery verified by frontend suite (246 passed) and build.
- [x] Phase 5: HTTP Range, analytics, accessibility, readiness, and cache paths verified; P03/P05 remain deferred pending a compatibility benchmark.
- [x] เฟส 6: security findings ที่ต้องยืนยันพฤติกรรม และ FFmpeg parity fixtures (background source boundary + backup/WAL เสร็จ; end-to-end Preview/Render parity verified (165 tests passed))
- [x] Phase 7: lifespan, full regression classification, documentation, and ledger closeout completed; environment-only fixture gaps remain recorded.

## Round SYSTEM-AUDIT-P0-20260915 — ปกป้องข้อมูล SQLite, การอัปโหลด และ media endpoint

Date: 2026-09-15 | requested by: user | executed by: Codex (GPT-6) | status: complete; isolated clone fixture gaps recorded

- [x] เขียน regression tests: mirror ที่ว่าง/เสีย, id ไม่ถูกต้องหรือซ้ำ, upload ชื่อซ้ำและขาดกลางทาง, HEIC และ media allowlist/symlink
- [x] ป้องกัน JSON mirror ที่ไม่สมบูรณ์แทนที่ข้อมูล SQLite โดยให้ `[]` ที่เป็น JSON ถูกต้องล้างข้อมูลได้ตาม contract เดิม
- [x] เขียน staged upload แบบ atomic no-clobber สำหรับไฟล์ปกติ, asset และ HEIC conversion พร้อมเก็บไฟล์เดิมเมื่อ conversion ล้มเหลว
- [x] จำกัด `/api/media` ให้เหลือ artifact media ที่อนุญาตใน root ที่ตั้งใจ พร้อมตรวจ containment หลัง resolve
- [x] Focused backend/API regression: 88 passed, 3 skipped, 2 warnings; compileall และ import api_server ผ่าน (168 routes)
- [x] Frontend regression: 232 passed; Vite build ผ่าน 2.66s
- [x] Full isolated pytest classification: latest clone 1470 passed, 21 failed, 14 skipped, 24 warnings; failures are missing fonts/assets/environment, not P0 paths.
- [x] `git diff --check` passed for the closeout changes and completed rounds were recorded in HISTORY.md.

**Notes:** working tree มีงานร่วมสมัยใน `HISTORY.md`, `TODO.md`, frontend และ TTS อยู่แล้ว จึงแก้เฉพาะไฟล์ในรอบนี้และไม่เขียนทับงานเหล่านั้น. Full suite ใช้สำเนาแยกเพื่อไม่แตะ `01_Raw`, `02_Assets`, `03_Projects` หรือ `_Docs/post_log.json` จริง.

## Round SYSTEM-AUDIT-P1-RECOVERY-20260915 — Startup และ manifest recovery

Date: 2026-09-15 | requested by: user | executed by: Codex (GPT-6) | status: complete

- [x] เขียน red regression: task registry มี `null`/row ผิดรูปแบบยัง boot ได้โดยเก็บ snapshot เดิมไว้ และ valid task ฟื้นตามเดิม
- [x] แก้ TaskManager validate/quarantine malformed rows ก่อน recovery
- [x] เขียน red regression: มีเฉพาะ `project.json.bak1`, `.bak2`, `.bak3` แต่ไม่มี primary/.bak ต้อง load ได้
- [x] แก้ ProjectManifest ค้น backup ทุก candidate ก่อนสรุปว่าไม่มี manifest
- [x] Focused recovery tests: 49 passed, 2 warnings

**Notes:** P0 ยังเปิดเพราะ full isolated gate ถูกขวางด้วย fixture/font และงาน Gemini TTS ร่วมสมัย; บันทึกผลจริงไว้ข้างต้นแล้ว. P1 แก้เฉพาะ `scripts/task_manager.py`, `scripts/project_manifest.py` และ regression tests ใน tmp_path.

## Round SYSTEM-AUDIT-P1-BATCH-20260915 — Batch dispatcher handoff

Date: 2026-09-15 | requested by: user | executed by: Codex (GPT-6) | status: complete

- [x] เขียน deterministic race regression: enqueue ขณะ dispatcher เห็นคิวว่างแต่ยังไม่ exit ต้องถูกประมวลผล
- [x] ทำ idle-exit และ `_ensure_dispatcher()` handoff ภายใต้ lock เดียวกัน พร้อมตรวจคิวซ้ำก่อน exit
- [x] รัน focused batch/recovery tests: 56 passed, 2 warnings

**Notes:** ขอบเขตจำกัดที่ `scripts/batch_render.py` และ test tmp-path; ไม่เปลี่ยนลำดับ FIFO หรือ worker render.

## Round SYSTEM-AUDIT-P2-CUTOUT-20260915 — Cutout publication และ idempotency

Date: 2026-09-15; executed by: Codex (GPT-6); status: complete

- [x] Regression: crash หลังย้าย frames ก่อน ready manifest ต้อง retry ได้จาก checkpoint โดยไม่ run inference ซ้ำ
- [x] Recover derived target ที่ไม่ ready อย่างปลอดภัย โดยไม่แตะ artifact ready ที่ valid
- [x] Regression: request payload เดิมพร้อมกันต้องได้ task id เดียวและ schedule งานเดียว
- [x] Deduplicate background-isolation task ด้วย normalized payload ภายใต้ lock
- [x] Focused worker/API tests และตรวจ cancellation/checkpoint contract: 36 passed, 2 skipped, 2 warnings

**Notes:** ขอบเขต `scripts/background_isolation_sequence_worker.py`, `scripts/api_background_isolation.py` และ fixture temp only. ไม่เรียก rembg จริง.

## Round SYSTEM-AUDIT-P3-MEDIA-RANGE-20260915 — HTTP byte-range correctness

Date: 2026-09-15; executed by: Codex (GPT-6); status: complete

- [x] Regression: suffix range, end-clamp, out-of-file, reversed, multi-range และ empty file
- [x] Parse only valid single `bytes=` range; malformed/unsatisfiable ตอบ 416 พร้อม Content-Range
- [x] Focused API/media tests: 69 passed, 1 skipped, 2 warnings; compileall ผ่าน

**Notes:** จำกัดที่ `scripts/media_service.py`; ไม่เปลี่ยน media allowlist หรือ frontend. ระหว่าง import gate จาก workspace พบ orphaned render task จริง 1 รายการและ recovery เปลี่ยน angle `in_production` → `scripted`; ห้ามรัน import gate กับ workspace ซ้ำ รอบถัดไปใช้สำเนาแยกเท่านั้น.

**รวม focused isolated gate ณ จุดนี้:** 186 passed, 5 skipped, 2 warnings; `compileall scripts` และ import API ผ่าน 168 routes. Full isolated suite ก่อนหน้านี้ 1,437 passed / 24 failed จาก fixture ฟอนต์/asset ที่ไม่ได้อยู่ในสำเนาและ Gemini TTS ร่วมสมัย จึงยังไม่ปิดรอบทั้งหมด.

## Round SYSTEM-AUDIT-P4-WORKSPACE-CACHE-20260915 — Workspace cache generation guard

Date: 2026-09-15 | requested by: user | executed by: Codex (GPT-6) | status: complete

- [x] Regression: old request resolve หลัง invalidate และ request ใหม่ ต้องไม่ overwrite ค่าใหม่
- [x] เพิ่ม generation guard ใน coordinator โดยรักษา request coalescing และ forced refresh
- [x] รัน focused Node tests (3 passed), full frontend tests (233 passed) และ build (4.16s)

**Notes:** จำกัด `frontend/src/lib/workspaceData.*`; ไม่แตะ component ที่มีงาน UI ร่วมสมัย.

## Round SYSTEM-AUDIT-P4-AUTOSAVE-AUTH-20260915 — Lifecycle autosave authentication

Date: 2026-09-15 | requested by: user | executed by: Codex (GPT-6) | status: complete

- [x] Regression: lifecycle save ต้องแนบ `X-API-Key` เมื่อ key ถูกตั้งค่า และไม่ส่ง header ว่าง
- [x] ใช้ header helper เดียวกับ fetch keepalive ตอน pagehide/beforeunload
- [x] รัน focused 9 passed, full frontend tests 234 passed และ build 3.38s

**Notes:** จำกัด `frontend/src/hooks/useProjectAutosave.js` และ unit test; ไม่เปลี่ยน queue ordering.

## Round SYSTEM-AUDIT-P4-RENDER-POLLING-20260915 — ป้องกัน stale render polling

Date: 2026-09-15 | requested by: user | executed by: Antigravity (GPT-5.6) | status: complete

- [x] เขียน red regression ให้ response จาก poll ของ job เก่าที่มาช้าหลังเริ่ม job ใหม่ไม่เปลี่ยนสถานะ/ผลลัพธ์ของ job ใหม่
- [x] เพิ่ม generation guard ต่อการเริ่ม polling แต่ละ job และยกเลิกผลลัพธ์/terminal callback ของ generation เก่า
- [x] รัน focused Node regression และ frontend test suite; บันทึกตัวเลขจริงและ diff check

**Notes:** จำกัดการแก้ `frontend/src/hooks/useRenderJob.js` กับ `frontend/src/lib/renderJobPolling.test.js`; focused 2 passed, frontend 236 passed, Vite build 3.32s ผ่าน, `git diff --check` ผ่าน. เปลี่ยนจาก `setInterval` เป็น schedule หลัง request จบ และใช้ generation guard ต่อ job; รักษางานค้างของเอเจนต์อื่นใน workspace.

## Round SYSTEM-AUDIT-P4-FRAME-RETRY-20260915 — กู้คืน cached frame ที่โหลดพลาด

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Antigravity (GPT-5.6) · สถานะ: เสร็จสมบูรณ์

- [x] Reproduce: frame cache ที่เป็น `error` คืน `null` ถาวรและไม่ยิง request ใหม่
- [x] เพิ่ม bounded retry แบบ deterministic backoff 250ms, 1s, 4s และ reset counter เมื่อโหลดสำเร็จ
- [x] กัน callback/timer จาก cache entry เก่าหลัง unmount และคืน object URL เมื่อ frame ล้มเหลว
- [x] Regression focused: source contract test 4 passed; frontend build 2.71s ผ่าน; `git diff --check` ผ่าน
- [x] Full frontend suite ผ่านหลังรวม B09: 239 passed; Vite build 2.96s

**Notes:** จำกัด production change ที่ `frontend/src/components/SequencePlayer.jsx` และ regression assertion ใน `frontend/src/lib/sequencePlayerFrameScheduling.test.js`; ไม่เปลี่ยน geometry, caption, watermark, font หรือ renderer contract.

## Round SYSTEM-AUDIT-P6-SOURCE-BOUNDARY-20260915 — Background-isolation source containment

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-6) · สถานะ: เสร็จสิ้น

- [x] จำกัด source ให้เป็น video extension ที่อนุญาตและอยู่ใต้ workspace media roots
- [x] ปฏิเสธ direct symlink และ resolved path ที่ escape ออกจาก workspace
- [x] Regression: source boundary + P0 safety tests 66 passed, 4 skipped

**Notes:** รองรับ relative path เดิมและ temp workspace ที่ test จัดเตรียม โดยยัง fail-closed สำหรับไฟล์นอก root หรือชนิดไฟล์อื่น

## Round SYSTEM-AUDIT-P6-REGRESSION-CONTRACT-20260915 — Full-gate failure classification

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-6) · สถานะ: เสร็จสิ้น

- [x] Full isolated clone gate: 1,451 passed, 24 failed, 14 skipped, 23 warnings
- [x] Re-ran the suspected contract subset in the current workspace using temp-only fixtures: 26 passed
- [x] Classified remaining clone failures as stale source/missing fonts, assets, `.agents/rules`, and `frontend/index.html`; Gemini TTS, font mapping, subtitle artifact, and callout contracts pass in the workspace

**Notes:** ไม่แก้ production เพิ่มจาก failures ที่เกิดเฉพาะ clone ซึ่งไม่มีไฟล์ประกอบ; full round ยังไม่ปิดจนกว่าจะสร้าง isolated fixture bundle ที่ครบ

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

Date: 2026-09-14; executed by: Codex (GPT-6); status: complete

**เป้าหมาย:** รองรับการสั่งงาน 220+ คลิปเป็นคิวที่ทน server restart โดยไม่เพิ่ม render concurrency เกิน 1 และตัดงานอ่าน/ส่งข้อมูลซ้ำที่โตตามประวัติคลิป.

### Todo

- [x] Track A — เพิ่ม durable Render Dispatcher ในโมดูลใหม่: persist batch/item checkpoint, FIFO admission, restart recovery และไม่เปิด daemon worker ต่อ batch; แตะ `scripts/batch_render.py`, `scripts/api_batch_render.py`, `scripts/render_jobs.py`, `scripts/task_manager.py` เฉพาะ hunk ที่ตรวจว่าทับงานค้างไม่ได้ (durable checkpoint/recovery, FIFO selection, idle handoff, single dispatcher verified; 13 tests passed)
- [x] Track B — แยก Export Catalog snapshot/canonical path identity จาก read path: GET exports และ schedule queue อ่าน index ที่พร้อมใช้ แทนการ resolve path/synchronize ทุก request; แตะ `scripts/api_exports.py`, `scripts/export_registry.py`, `scripts/api_schedule_queue.py`, `scripts/product_store.py` อย่างรักษา diff งานค้าง (path-index invalidation/key mutation fixed; export/schedule lifecycle 38 tests passed)
- [x] Track C ? Workspace Data Coordinator single-flight/cache plus shared product projection is wired across App/Tracker/Editor; mutation paths force invalidation. Remaining work is only the parent round gate.
- [x] deterministic regression tests for queue persistence/admission, export snapshot invalidation, and coordinator contracts (frontend 243 passed; identity: Codex (GPT-6))

### Gate

- [x] `python -m compileall -q scripts` (passed; identity: Codex (GPT-6))
- [x] Full pytest gate: 1512 passed, 5 skipped, 29 warnings; pytest เฉพาะจุดของ Track A/B และ `python -m pytest tests/ -q -p no:cacheprovider --tb=short`
- [x] frontend targeted test, `npm test`, `npm run build` (243 passed; Vite 2007 modules / 3.22s; identity: Codex (GPT-6))
- [x] `git diff --check` และตรวจว่าไม่แก้/ลบไฟล์ผู้ร่วมงานนอกขอบเขต

### Notes

- Audit วัดเมื่อ 2026-09-14: status 6.8 ms, raw videos 9.1 ms, products 18.4 ms / 878 KB, exports 277 ms median (profiler 474 ms), schedule 136 ms median. Render slot ปัจจุบัน 1 active + 3 waiting และต้องคงไว้เพราะ RAM ว่างประมาณ 3.9 GB.
- Working tree มีงานค้างจำนวนมาก โดยเฉพาะ `scripts/api_exports.py`, `scripts/api_render.py`, `scripts/batch_render.py`, `scripts/product_store.py`, `frontend/src/components/ContentTrackerHub.jsx`, `frontend/src/components/editor/EditorShell.jsx`; ทุก track ต้องใช้ patch แบบ hunk-preserving และไม่ revert/format ทั้งไฟล์.

## Round AI-PRODUCER-HUB-AUDIT-PLAN-1 — ปิด audit และ hardening Producer Hub (2026-09-14; ดำเนินการโดย: Codex (GPT-5))

## Round BG-SUBJECT-ISOLATION-3 — Preview/Render parity + usable per-clip processing

ดำเนินการโดย: Codex (GPT-5)

สถานะ: เสร็จแล้ว — เพิ่ม API ประมวลผล sequence, state persistence, Preview/Render compositing, UI control และ fallback safety

Gate: backend 1386 passed / 3 skipped, BG focused 151 passed / 3 skipped, frontend 219 passed, Vite build ผ่าน 2005 modules, compileall ผ่าน, FFmpeg fixture ตรวจ pixel แล้ว

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

---

## Round GEMINI-TTS-NO-FALLBACK-LOUD-ERROR-1 — ยกเลิก Edge-TTS Fallback & แสดง Error แจ้งเตือนเวลาลิมิต Gemini TTS + ซิงค์เสียงเริ่มต้นแผนถ่าย

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย & ปัญหาที่แก้ไขตามคำขอผู้ใช้:**
1. **หน้าแผนถ่าย (Shot List Modal):**
   - ตั้งค่าเสียงเริ่มต้นให้ตรงกับหน้าตัดต่อ: `gemini_puck_male_hype` (Puck — ชายพลังสูง สไตล์ TikTok) และโทน `commercial_hype`
   - ปรับลิสต์ใน Dropdown ให้ Puck อยู่ลำดับแรกสุด #1
2. **ยกเลิก Edge-TTS Fallback ถาวรเมื่อใช้ Gemini TTS:**
   - ผู้ใช้ยืนยันชัดเจนว่าจะไม่ใช้เสียง Edge-TTS ในระบบ หาก Gemini TTS สร้างเสียงไม่ได้ **ต้องหยุดการทำงานทันที (Halt & Fail)** ไม่ fallback ไป Edge-TTS
   - ครอบคลุมทั้ง Pipeline ตัดต่อวิดีโอ (`VoiceStage.run`), Shot List แผนถ่าย (`scripts/shot_list_builder.py`), และ Voice Preview (`api_voice.py`)
3. **แจ้งเตือนสาเหตุและเวลาที่ต้องรออย่างละเอียด (Actionable Error Reporting):**
   - หากติด Rate Limit (HTTP 429) หรือ Quota Exceeded ให้ดึงและวิเคราะห์เวลาที่ต้องรอ (เช่น `retryDelay`, `Retry-After`)
   - แจ้งเตือนว่าติดขีดจำกัดแบบใด (เจนถี่เกินไป / RPM / โควตารายวัน RPD) พร้อมระบุเวลารอชัดเจน (เช่น กี่วินาที หรือกี่นาที) หรือแนะนำให้เพิ่ม API Key ใน `.env`
   - ส่งต่อข้อความ Error ที่สมบูรณ์ไปยัง Task Card, Toast และหน้าต่าง Modal

### สรุปสิ่งที่ทำเสร็จ:
- [x] Backend (`scripts/gemini_tts_engine.py`): ปรับปรุงระบบตรวจจับ HTTP 429 และ Quota ให้แยกแยะสาเหตุและเวลาที่ต้องรอ พร้อม raise `GeminiTTSError` ที่สมบูรณ์
- [x] Backend (`scripts/stages/voice_stage.py`): ยกเลิก Edge-TTS fallback ทั้งหมดเมื่อ `voice_engine_type == "gemini_tts"` โดยสั่งหยุดและ raise error ทันที
- [x] Backend (`scripts/api_shot_lists.py` & `scripts/api_render.py` & `scripts/api_voice.py`): ส่งต่อ error message ละเอียดไปยัง TaskManager และ HTTP response
- [x] Frontend (`frontend/src/components/ShotListModal.jsx`): ปรับค่าเริ่มต้นและ Dropdown เสียงพากย์เป็น Puck TikTok และโทนป้ายยาไวรัล พร้อมแสดงกล่องแจ้งเตือน Error เมื่อเจนไม่ผ่าน
- [x] Frontend (`frontend/src/components/ProductToClip.jsx` & `ContentTrackerHub.jsx`): ส่ง state error ให้ ShotListModal
- [x] Tests: อัปเดตและรัน pytest 50 passed และ vitest 232 passed build ผ่าน 100%

## Round BG-SUBJECT-ISOLATION-QUALITY-GATE-1 — ตรวจ alpha mask sanity ก่อน publish

ดำเนินการโดย: Codex (GPT-6)

### แผนรอบนี้
- [x] เพิ่ม deterministic alpha coverage sanity gate ใน sequence worker โดยไม่เปลี่ยน schema และไม่แตะ artifact เดิม (verified existing production gate in scripts/background_isolation_worker.py)
- [x] เพิ่ม regression tests สำหรับ fully transparent / fully opaque / plausible alpha frames และยืนยันว่าไม่ publish ready เมื่อ gate ไม่ผ่าน (transparent/opaque/sparse regression coverage; 33 focused tests passed)
- [x] รัน focused background-isolation tests, compileall และ scoped diff check (focused tests + compileall passed; scoped source diff check passed)

### Subplan BG-SUBJECT-ISOLATION-READINESS-20260915
- [x] ตรวจ project-level background-isolation marker เทียบกับ artifact ระดับคลิป และระบุ stale processing หลัง reload
- [x] เพิ่ม pure regression tests สำหรับ processing/error marker ที่ต้อง override สถานะ ready ของ clip เดิม
- [x] แก้เฉพาะ readiness projection หากพบ behavior ผิดจริง แล้วรัน frontend focused tests/build
ดำเนินการโดย: readiness_audit (GPT-6)

### Fixture evidence update (2026-09-15)
- Inspected `.tmp/bg-isolation-investigation/source-2.8s.png`, `u2net-2.8s.png`, and `u2netp-2.8s.png` as real rembg outputs.
- Measured u2net visible alpha 7.9174%, alpha mass 6.5538%, bbox `(138,441)-(331,774)`; u2netp visible alpha 12.0644%, alpha mass 6.3803%, bbox `(46,204)-(540,960)`.
- u2netp mask reaches the frame edge, consistent with the previously observed hand/background false foreground. Keep project default `u2net`; do not change existing artifacts automatically.
- End-to-end video Preview/Render fixture remains open; no production threshold change made.
- ดำเนินการโดย: Codex (GPT-6)

### Security regression recheck (2026-09-15)
- [x] P0 safety + P1 recovery suites: 50 passed, 1 skipped, 1 warning; `.env` files ignored/untracked and values not read or changed. Agent: Codex (GPT-6)

### Real video Render fixture evidence (2026-09-15)
- Copied existing project fixture `03_Projects/LOG02-รีวิวสเปก_1/seg_000.mp4` plus its audio/subtitle into `.tmp/e2e-fixture` only.
- `VideoEditor.assemble_tiktok_video` completed a 2.0s draft render and a 2.0s post render without modifying the source project.
- Post output probe: H.264 + AAC, 1080×1920, 30/1 FPS, 2.000s; frame inspection shows Hook and bilingual subtitle layers present.
- Browser Preview pixel parity is still open; no model/threshold change made.
- ดำเนินการโดย: Codex (GPT-6)

## Round SYSTEM-AUDIT-P7-LIFESPAN-20260915 — แยก startup recovery ออกจาก import side effects

ดำเนินการโดย: Codex (GPT-6)

### แผนรอบนี้
- [x] แยก background-isolation และ batch recovery ให้อยู่ใน lifecycle ที่ควบคุมได้
- [x] เพิ่ม regression ให้ import/app construction ไม่ทำ recovery ซ้ำหรือทำให้ test fixture พัง
- [x] รัน focused API tests, compileall และ scoped diff check

### Subplan SYSTEM-AUDIT-P7-LIFESPAN-20260915 / startup recovery control
- [x] เพิ่ม `recover_startup_work()` และ FastAPI lifespan ให้ background-isolation/batch recovery ทำงานเมื่อ server เริ่มจริง ไม่ทำงานตอน import module
- [x] เพิ่ม regression ทดสอบ helper/lifespan เรียก recovery อย่างควบคุมได้และแยก error ต่อ subsystem
- [x] รัน focused API/recovery tests, compileall และ scoped diff check
ดำเนินการโดย: Codex (GPT-6)

### Evidence SYSTEM-AUDIT-P7-LIFESPAN-20260915
- Importing `scripts.api_server` and constructing `app` no longer executes durable background-isolation or batch recovery.
- `recover_startup_work()` is called by FastAPI `lifespan`; it records counts in `app.state.startup_recovery` and isolates subsystem failures.
- Regression/recovery suite: 39 passed, 3 skipped, 1 warning; `python -m compileall -q scripts tests/test_api_server_lifespan.py` passed; scoped `git diff --check` passed.
ดำเนินการโดย: Codex (GPT-6)

## Round SYSTEM-AUDIT-CONTINUE-20260915 — ปิดงานค้างด้วยหลักฐานแยกชุด
ดำเนินการโดย: Codex (GPT-6)
### แผนรอบนี้
- [x] ตรวจ full isolated gate และแยก failure ที่แก้ได้จาก fixture/environment blocker
- [x] ตรวจ Preview/Render parity จากโค้ดและ browser/fixture ที่มีอยู่ โดยไม่แก้ visual contract เอง
- [x] ตรวจ P03–P05 performance paths และเลือก bounded fix ที่มี regression รองรับ
- [x] รัน focused tests/build/diff check แล้วบันทึกผลใน HISTORY และ system audit
### Evidence SYSTEM-AUDIT-CONTINUE-20260915
- [x] Full isolated clone gate classified: 1,470 passed, 21 fixture/environment failures, 14 skipped, 24 warnings; no safe production regression found.
- [x] Preview/Render parity fixed: FFmpeg Hook scrim now uses the same 0.75 peak opacity as SequencePlayer Canvas (`scripts/video_editor.py` + `tests/test_preview_render_parity.py`). Browser visual snapshot at 0s and 4s matched Render; pixel extraction from Canvas is unavailable through CUA.
- [x] P04 export read path bounded cache added in `scripts/api_exports.py`; P03 source chunking and P05 collection rewrite deferred pending benchmark/compatibility contract.
- [x] Validation: preview parity 154 passed; behavior/compositor/integration 69 passed; matching lookup 9 passed; export regression 27 passed, 1 warning; compileall and scoped diff checks passed.
ดำเนินการโดย: Codex (GPT-6); performance review: Antigravity (GPT-5.6); browser review: preview_parity_audit (GPT-6)
- [x] Deterministic Gemini key test fixture: clear every `GEMINI_API_KEY*` process variable and patch `scripts.config._env_file` to tmp path; `tests/test_gemini_tts_engine.py` now passes 20/20.
- ดำเนินการโดย: Codex (GPT-6)

## Round SYSTEM-AUDIT-NEXT-20260915 — ปลดล็อกงาน P03/P05 ด้วย benchmark และ contract
ดำเนินการโดย: Codex (GPT-6)
### แผนรอบนี้
- [x] วัดต้นทุน rembg แบบ temp-only เพื่อประเมิน source-time chunking โดยไม่สร้าง artifact ใหม่ในโปรเจกต์จริง
- [x] ตรวจ ProductStore mutation path และออกแบบ bounded row-level contract พร้อม regression ก่อนพิจารณาแก้
- [x] ตรวจ full-gate fixture failures ว่าทำให้ self-contained ได้หรือควรคงเป็น environment blocker
- [x] สรุปผลและคอมมิตเฉพาะเมื่อมีการเปลี่ยนแปลงที่ปลอดภัย
### Evidence SYSTEM-AUDIT-NEXT-20260915
- [x] Temp-only rembg benchmark: at 540×960, u2net warm average 1.953s/frame and u2netp 0.744s/frame; a 2.8s chunk is ~3.6% of a 77.8s source. Source-time chunking is valuable but requires artifact identity/frame mapping redesign, so no production change was made.
- [x] P05 row-level mutation contract: `_MutateCtx` now emits only changed-row UPDATE/INSERT/DELETE statements, rejects duplicate IDs, and preserves transaction rollback/API compatibility. SQLite/reconcile 22 focused tests passed in this workspace.
- [x] Full-gate fixture review: missing fonts, typography presets, SFX, BGM, stickers, and media explain remaining isolated failures; no real assets or secrets will be added to the repository.
- [x] Validation: `tests/test_sqlite_store_migration.py` 22 passed; `tests/test_api_batch_audio.py` 4 passed; compileall and scoped diff checks passed.
ดำเนินการโดย: Codex (GPT-6); benchmark: cutout_benchmark (GPT-6); mutation review: mutation_contract (GPT-6)

### Evidence MAIN-PAGE-VOICE-TYPE-INDICATOR-1
- [x] หน้าหลักโหลดสถานะแผนถ่าย/เสียงตาม product และ angle โดยอัตโนมัติ
- [x] แสดงสถานะ Edge-TTS เดิม, Gemini preset และแผนถ่ายเก่าบน desktop/mobile cards
- [x] Active Workbench แสดง Voice & Audio Track Banner และ action ตามประเภทเสียง
- [x] Validation: frontend tests 246 passed; Vite build 2,007 modules / 3.03s
ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)

## Round AI-PRODUCER-HUB-HARDENING-1

Date: 2026-09-15; executed by: Codex (GPT-6); status: complete

Plan before code:
- [x] Restrict remote reference fetches to public addresses and reject unsafe redirects.
- [x] Restrict local reference reads to approved workspace roots with resolved-path containment.
- [x] Add deterministic regression tests for private URLs, redirects, and local-path escape.
- [x] Run focused Producer tests, compileall, and diff check.
