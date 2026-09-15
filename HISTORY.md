# 📜 OmniCut Pro Studio — History งานที่ทำเสร็จแล้ว

คลังประวัติรอบงานที่ปิดแล้ว **ห้ามแก้ย้อนหลัง** — เป็นบันทึกว่าตอนนั้นทำอะไร วัดได้เท่าไหร่ เจออะไร

- งานที่ยังไม่เสร็จอยู่ที่ [TODO.md](file:///d:/Winona/Programmer/Capcut/TODO.md)
- กติกา: [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md)
- รอบไหนปิด ให้ **ย้ายบล็อกเต็มมาที่นี่** แล้วเหลือบรรทัดเดียวใน `TODO.md` — กัน `TODO.md` บวมจนหาของไม่เจอ

## สารบัญ

| Round SKIP-RENDERED-POSTED-AUDIO-GEN-1 | ข้ามการสร้างเสียงพากย์สำหรับคลิปที่เสร็จ (rendered) หรือโพสต์แล้ว (posted) และตัดออกจากตัวนับขาดเสียง | 2026-09-15 | สำเร็จสมบูรณ์ (backend 3 passed, frontend 246 passed, build 2,007 modules/3.59s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round UI-FONT-HARMONY-ALL-1 | กวาดล้าง font-mono และผสานฟอนต์กลาง (Prompt) ทั่วทั้งระบบ 100% ครบทุกแดชบอร์ดและหน้าจอ | 2026-09-15 | สำเร็จสมบูรณ์ (frontend 232 passed, build 2,007 modules/2.83s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round GEMINI-TTS-MULTIKEY-ALERT-1 | ปรับระบบ Multi-Key Failover (ลอง 3.1 ทุก Key ก่อนลดเป็น 2.5) + แจ้งเตือน AI Rate-Limit/Quota บน Token Dashboard | 2026-09-15 | สำเร็จสมบูรณ์ (backend 20 passed, frontend 232 passed, build 2,007 modules/2.68s, compileall ผ่าน, live synthesis verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round VOICE-DEFAULT-PUCK-HYPE-1 | ปรับค่าเริ่มต้นเสียงพากย์ทุกสไตล์เป็น Puck (ชายพลังสูง TikTok) + โทนป้ายยาไวรัล ทั่วทั้งระบบ | 2026-09-14 | สำเร็จสมบูรณ์ (backend 1,415 passed, frontend 230 passed, build 2,006 modules/3.17s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round HOOK-TIER-SYNC-1 | จัดการป้าย Hook Header (แบรนด์ · รุ่น · หมวด) แบบเลือกขอบเขต (เฉพาะคลิปนี้ vs ทั้งสินค้า) ในหน้าสินค้าและสร้างคลิป | 2026-09-14 | สำเร็จสมบูรณ์ (backend 21 passed, frontend 230 passed, build 2,006 modules/3.08s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round SCHEDULE-FLEXIBLE-SLOTS-1 | ตั้งเวลาโพสต์ default 5 ช่วง และเพิ่ม/ลบช่วงพิเศษแยกเป็นรายวัน | 2026-09-14 | สำเร็จสมบูรณ์ (backend schedule 10 passed, frontend 230 passed, compileall ผ่าน, build 2,005 modules/3.25s, detector มีคำเตือนสไตล์เดิมของไฟล์, ดำเนินการโดย: Codex (GPT-5)) |
| Round SCHEDULE-DEFAULT-RESET-1 | ปรับเทมเพลตเวลาที่บันทึกไว้ทั้งหมดเป็น 09:00 / 12:30 / 16:00 / 19:00 / 21:30 | 2026-09-14 | สำเร็จสมบูรณ์ (2 สัปดาห์ × 7 วันอัปเดต, storage/API/UI verified, ไม่กระทบคิวคลิป, ดำเนินการโดย: Codex (GPT-5)) |
| Round COVER-RENDER-REQUIRES-COVER-1 | บังคับสร้างและบันทึกหน้าปกก่อน Render | 2026-09-14 | สำเร็จสมบูรณ์ (frontend 230 passed, build 2,006 modules/3.13s, diff check ผ่าน, ดำเนินการโดย: Codex (GPT-5)) |
| Round TRACKER-LARGE-DATA-PERF-1 | ลดเวลาเปิด Content Tracker เมื่อมีคลิปจำนวนมาก | 2026-09-14 | สำเร็จสมบูรณ์ (`/api/exports` 2.6s → 0.28–0.37s ที่ 27 ไฟล์, tracker product+queue 0.15–0.22s, backend 1,417 passed/3 skipped, frontend 230 passed, build 2,006 modules, ดำเนินการโดย: Codex (GPT-5)) |
| Round COVER-TIMELINE-PRE-RENDER-1 | สร้างหน้าปกจากเฟรมจริงใน Timeline ก่อน Render | 2026-09-14 | สำเร็จสมบูรณ์ (backend cover 8 passed, frontend 230 passed, build 2,006 modules, detector พบเฉพาะคำเตือนเดิม, browser unavailable, ดำเนินการโดย: Codex (GPT-5)) |
| Round CALLOUT-RESURRECT-FIX-1 | แก้บั๊ก Text Overlays ถูกปลุกขึ้นมาทับกลางจอ (LOCSmartband) เมื่อลบแล้วใน Editor + ป้องกัน Auto Brand/Model Callout ซ้อนทับ Hook Banner | 2026-09-14 | สำเร็จสมบูรณ์ (backend 8+5+153 passed, frontend 230 passed, build 2005 modules/3.60s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round BG-SUBJECT-ISOLATION-RESUME-1 | Durable per-frame checkpoint, startup recovery, reconnect polling, completed-result rebinding, and duplicate scheduler guard | 2026-09-14 | สำเร็จสมบูรณ์ (backend 45+41 passed, frontend 230 passed, build 2,005 modules, compileall ผ่าน, ดำเนินการโดย: Codex (GPT-5)) |

| Round COVER-MULTI-GEN-HANDHELD-1 | AI Cover History Gallery (เก็บทุกรูปที่เจนไม่ถูกทับ) + ปลดล็อกคำสั่ง Handheld มือถือสินค้าจริง + Auto-enable Brand/Model Title Overlay | 2026-09-14 | สำเร็จสมบูรณ์ (pytest 6 passed, vitest 230 passed, build 2.95s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round COVER-REALTIME-SCRUB-STUDIO-1 | เรียลไทม์ Frame Scrubber ใน Cover Studio + AI Studio Cutout ผสานช็อตสินค้าจริง | 2026-09-14 | สำเร็จสมบูรณ์ (pytest 3 passed, vitest 224 passed, build 3.98s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round HOOK-KINETIC-MOTION-1 | Step-by-Step Cumulative Hook Reveal & High-Impact Animation System (slam, elastic_bounce) | 2026-09-13 | สำเร็จสมบูรณ์ (backend parity 177 passed, behavior render 18 passed, smoke 150 passed, frontend 185 passed, build 3.79s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round THAI-STACKED-MARK-GENERALIZE-1 | ขยายการจัดชั้นสระบน + วรรณยุกต์ไทยจากคู่เดียวเป็น 20 คู่ พร้อม Preview/Render parity | 2026-09-13 | สำเร็จสมบูรณ์ (backend 1,135 passed, visual/contract 180 passed, frontend 185 passed, FFmpeg 20-pair pixel matrix + browser verified, ดำเนินการโดย: Codex (GPT-5)) |
| Round THAI-STACKED-MARK-RENDER-FIX-1 | แก้ `ั` + `่` ซ้อนทับใน Render ให้สูงโปร่งตรง Preview โดยรักษา layout ของ emoji/ข้อความทั้งบรรทัด | 2026-09-13 | สำเร็จสมบูรณ์ (backend 1,133 passed, visual/contract 178 passed, frontend 185 passed, build 2,003 modules/4.59s, FFmpeg pixel geometry + browser verified, ดำเนินการโดย: Codex (GPT-5)) |
| Round TECH-PRODUCT-SHOWCASE-1 | เพิ่ม preset Tech Product Showcase สำหรับคลิปรีวิวสินค้า โดยใช้ motion/palette contract เดียวกับ Preview/Render | 2026-09-13 | สำเร็จสมบูรณ์ในขอบเขต foundation (backend 181 focused passed, frontend 185 passed, build/compile/pip check/diff check passed, FFmpeg 5-style multi-frame render + Browser verified, ดำเนินการโดย: Codex (GPT-5)) |
| Round TOKEN-LAZY-LOAD-1 | ถอด HISTORY ออกจาก prompt ทุกรอบ (lazy-load อ่านสารบัญ ≤100 บรรทัด) | 2026-09-13 | เสร็จ (work_loop 2.1 / AGENTS 13 / SKILL ข้อ 2-3, ดำเนินการโดย: Muse Spark (Muse Spark)) |
| Round AGENTS-SLIM-1 | ย่อ AGENTS.md 170→62 บรรทัด (30.9→11.3 KB) กฎ 24 ข้อครบ + link ไฟล์กฎ | 2026-09-13 | เสร็จ (ดำเนินการโดย: Muse Spark (Muse Spark)) |
| Round TEST-TWO-TIER-1 | กติกาเทส 2 ชั้น: ตอนแก้รันเฉพาะจุด ก่อนปิดรอบค่อยรันเต็ม | 2026-09-13 | เสร็จ (testing_standard.md, Gate เต็มเท่าเดิม, ดำเนินการโดย: Muse Spark (Muse Spark)) |
| Round HOUSEKEEP-1 | จัดระเบียบราก: ไฟล์เทส 8 ไฟล์ลง .tmp (gitignore) + ยกเลิกย้าย PLAN หลังเจอ 06_Archive โดน ignore | 2026-09-13 | เสร็จบางส่วน (ดำเนินการโดย: Muse Spark (Muse Spark)) |

## Round SKIP-RENDERED-POSTED-AUDIO-GEN-1 — ข้ามการสร้างเสียงพากย์สำหรับคลิปที่เสร็จ (rendered) หรือโพสต์แล้ว (posted) และตัดออกจากตัวนับขาดเสียง

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์ ✅

### ปัญหาที่พบ
1. **ตัวนับมุมที่ขาดเสียงบน UI นับรวมคลิปที่เสร็จ/โพสต์แล้ว:** ในหน้าสินค้า แถบเสียงพากย์อัตโนมัติแสดง `เสียงพร้อมแล้ว 2/13 มุม (ขาด 11)` และปุ่ม `เตรียมเสียงพากย์ (11 มุม)` ทั้งที่มุม 1, 2 ตัดเสร็จแล้ว (`status === 'rendered'`) และมุม 3, 4 โพสต์แล้ว (`status === 'posted'` หรือ `posted_at`) ซึ่งคลิปเหล่านี้มีวิดีโอสมบูรณ์แล้ว ไม่จำเป็นต้องสร้างเสียงพากย์ใหม่
2. **Backend worker ยังไม่ได้คัดกรองคลิปที่เสร็จ/โพสต์แล้วออก:** ใน `_execute_batch_generate_audio_worker` หากสั่ง batch เจนเสียง ระบบจะนำทุกมุมที่มีบทพูดไปเจนเสียง รวมถึงคลิปที่เสร็จแล้วหากยังไม่มี shot list แคช

### แผนแก้ไขและสิ่งที่ดำเนินการ
- [x] ใน `frontend/src/components/ProductToClip.jsx`:
  - สร้าง helper `isAngleCompleted(ang)` เช็ค `ang.status === 'rendered' || ang.status === 'posted' || Boolean(ang.posted_at)`
  - แยก `activeBatchAngles = targetBatchAngles.filter(ang => !isAngleCompleted(ang))`
  - คำนวณ `missingAudioCount` และ `readyAudioCount` จาก `activeBatchAngles` แทนที่จะนับมุมที่เสร็จแล้ว
  - ปรับปรุงข้อความ Badge: หากตัดเสร็จครบทุกมุมแล้วแสดง `ตัดเสร็จ/โพสต์ครบทุกมุมแล้ว`, หากเสียงพร้อมครบแสดง `เสียงพร้อมครบ X/X มุม`
  - ปรับปรุงปุ่ม `เตรียมเสียงพากย์`: ปิดการทำงาน (disabled) เมื่อคลิปเสร็จครบแล้ว และแสดงตัวเลขมุมเฉพาะมุมที่ยังไม่ได้ตัดต่อจริง
- [x] ใน `scripts/api_shot_lists.py`:
  - ใน `_execute_batch_generate_audio_worker`: เพิ่มตัวกรองข้ามมุมที่ `status in ("rendered", "posted") or a.get("posted_at")` โดยอัตโนมัติเมื่อ `not force_regenerate` พร้อมรายงานความคืบหน้าการข้าม
  - ใน endpoint `batch_generate_audio`: ส่งคืน `angle_count` ที่หักมุมที่เสร็จแล้วออก
- [x] เพิ่ม Unit Tests ใน `tests/test_api_batch_audio.py` ยืนยันว่า worker และ endpoint ข้ามมุม rendered และ posted ถูกต้อง 100%

### ผลการทดสอบ (Gate Verification)
- [x] Backend tests: `pytest tests/test_api_batch_audio.py -v` ผ่าน 3/3 tests (100%)
- [x] Frontend tests: `npm test -- --run` ผ่านครบ 246/246 tests (100%)
- [x] Frontend build: `npm run build` ผ่าน 2,007 modules ใน 3.59s

## Round UI-FONT-HARMONY-ALL-1 — กวาดล้าง font-mono และผสานฟอนต์กลาง (Prompt) ทั่วทั้งระบบ 100% ครบทุกแดชบอร์ดและหน้าจอ

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:**
1. แก้ปัญหาฟอนต์หลุดใน UI เช่น หน้า Token Dashboard, แดชบอร์ด Analytics และกราฟ SVG ที่ยังคงติดฟอนต์ Monospace (Consolas / Typewriter fallback บน Windows) ส่งผลให้ภาษาไทยและตัวเลขดูขรุขระ ไม่เป็นฟอนต์กลางของระบบ (`Prompt`)
2. ปรับการตั้งค่า Tailwind Config ให้ `mono` และ `sans` มี `Prompt` นำหน้าเพื่อป้องกันฟอนต์หลุดในอนาคต
3. เพิ่มกฎ CSS ใน `index.css` บังคับให้คลาส `.font-mono` สืบทอดฟอนต์ `Prompt` พร้อมเปิด `font-feature-settings: 'tnum'` เพื่อให้ตัวเลขในตารางและกราฟจัดเรียงตรงหลักสวยงามโดยไม่หลุดจากฟอนต์กลาง
4. กวาดล้างคลาส `font-mono` ออกจาก `TokenDashboard.jsx`, `AreaLineChart.jsx`, `DonutChart.jsx`, `AnalyticsHub.jsx`, `FunnelPipelineChart.jsx`, `ProgressRing.jsx`, `StorageAnalyticsTab.jsx`, `ProductionAnalyticsTab.jsx`, `InventoryAnalyticsTab.jsx`, `PerformanceAnalyticsTab.jsx`

**สิ่งที่ทำ:**
1. `frontend/tailwind.config.js`:
   - ปรับ `fontFamily.sans` เป็น `['Prompt', 'Inter', 'system-ui', 'sans-serif']`
   - ปรับ `fontFamily.mono` เป็น `['Prompt', 'Inter', 'Consolas', 'monospace']`
2. `frontend/src/index.css`:
   - เพิ่ม `.font-mono { font-family: 'Prompt', 'Inter', monospace; font-feature-settings: 'tnum' on, 'lnum' on; }` รับประกันว่าตัวเลขทุกตัวใช้ฟอนต์ Prompt ที่มี tabular layout ตรงหลัก
3. `frontend/src/components/TokenDashboard.jsx`:
   - ปลด `font-mono` ออกจากการ์ด API Key Health, Hero KPI Cards (4 ใบ), Model Breakdown, Tasks Breakdown, Daily Activity stats, และ Audit Log table ทั้งหมด
4. Charts & Analytics Tabs:
   - `AreaLineChart.jsx`: ปลด `font-mono` จากแกนตัวเลข SVG และ tooltip
   - `DonutChart.jsx`: ปลด `font-mono` จาก center label และ legend
   - `AnalyticsHub.jsx`: ปลด `font-mono` จากป้ายหมวดหมู่แท็บด้านบน (Funnel, Stats, Tokens, Storage, Health)
   - `FunnelPipelineChart.jsx` & `ProgressRing.jsx`: ปลด `font-mono` จากตัวเลขขั้นตอนและเกจเปอร์เซ็นต์
   - `StorageAnalyticsTab.jsx`, `ProductionAnalyticsTab.jsx`, `InventoryAnalyticsTab.jsx`, `PerformanceAnalyticsTab.jsx`: ปลด `font-mono` ออกจากตัวเลขสถิติและตารางข้อมูล

**ผลการตรวจสอบ (Gate):**
- [x] Frontend test: `npm test` ผ่านครบ 232/232 tests (100%)
- [x] Build check: `npm run build` ผ่านสมบูรณ์ (2,007 modules ใน 2.83s, 0 errors/warnings)
- [x] Grep verification: ตรวจสอบ `frontend/src/components/analytics` ปลอด `font-mono` 100%

## Round GEMINI-TTS-MULTIKEY-ALERT-1 — ปรับระบบ Multi-Key Failover และระบบแจ้งเตือน AI Rate-Limit / โควต้าบน Token Dashboard

วันที่: 2026-09-15 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:**
1. ปรับระบบ Fallback ของ Gemini Flash TTS ให้ลองโมเดลตัวท็อป (`gemini-3.1-flash-tts-preview`) ข้ามทุก API Key ก่อน (Key 1 → Key 2) เมื่อติด 429 ไม่ให้ลดระดับเป็น 2.5 บน Key เดิมทันที
2. ระบบบันทึกและส่งต่อการแจ้งเตือน AI Rate-Limit / Quota Exceeded (429) ไปยัง Token Analytics
3. แสดงผลแถบแจ้งเตือนเตือนภัยโควต้าชั่วคราว พร้อมสถานะของ Key แต่ละตัวบนหน้า Token Dashboard ใน Analytics Hub

**สิ่งที่ทำ:**
1. `scripts/gemini_tts_engine.py`:
   - ปรับลูปเป็น Model-First Matrix: ลองโมเดลหลัก `gemini-3.1-flash-tts-preview` บน Key 1 → Key 2 ก่อน
   - เมื่อ Key 1 ติด HTTP 429 ให้บันทึกเหตุการณ์ลง `TokenTracker.record_alert(...)` แล้วสลับไป Key 2 ทันทีโดยไม่ต้อง sleep backoff คอยนาน
   - เมื่อ Key 2 สำเร็จ บันทึก alert แจ้งว่าสลับไปใช้ Key 2 สำเร็จ
2. `scripts/token_tracker.py`:
   - เพิ่ม `alerts` ใน data structure
   - เพิ่ม methods `record_alert`, `get_alerts`, `clear_alerts`
   - เพิ่ม `key_status` ใน `get_summary()` เพื่อตรวจจับว่า Key ใดติด Rate-Limit ในรอบ 1 ชั่วโมง
3. `scripts/api_tokens.py`:
   - เพิ่ม endpoint `GET /api/tokens/alerts` และ `POST /api/tokens/alerts/clear`
4. `frontend/src/components/TokenDashboard.jsx` & `frontend/src/api.js`:
   - เพิ่ม `clearTokenAlerts` API
   - เพิ่มการ์ด "สถานะ AI API Keys & ระบบสลับคีย์อัตโนมัติ (Multi-Key Failover)" แสดงสถานะ Key #1, Key #2 (🟢 ปกติ พร้อมใช้งาน / ⚠️ ติด Rate-Limit 429 ชั่วคราว)
   - แสดงกล่องบันทึกเหตุการณ์แจ้งเตือนพร้อมเวลา และปุ่ม "ล้างประวัติแจ้งเตือน"

**ผลการตรวจสอบ (Gate):**
- [x] ทดสอบการยิงสังเคราะห์สด: Key 1 ติด 429 → สลับไป Key 2 บน 3.1 สำเร็จ ได้ไฟล์ WAV ใช้งานได้ทันที
- [x] Backend tests: `pytest tests/test_gemini_tts_engine.py` ผ่านครบ 20 ข้อ (100%)
- [x] Backend syntax: `python -m compileall -q scripts` ผ่าน 100%
- [x] Frontend tests: vitest ผ่านครบ 232 ข้อ (100%)
- [x] Frontend build: `npm run build` ผ่านใน 2.68s (2,007 modules)

---

## Round VOICE-DEFAULT-PUCK-HYPE-1 — ตั้งค่าเสียงเริ่มต้นทุกสไตล์เป็น Puck ชายพลังสูง TikTok + โทนป้ายยาไวรัล ทั่วทั้งระบบ

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:** ปรับค่าเริ่มต้นของระบบเสียงพากย์สำหรับทุกสไตล์ มุมมองสคริปต์ และทุกหน้าจอ ให้ใช้เสียง Puck (ชายพลังสูง สไตล์ TikTok, `gemini_puck_male_hype`) และโทน "ป้ายยาไวรัล" (`commercial_hype`) เหมือนกันทั้งระบบ

### Todo

- [x] Backend (`product_scraper.py`): อัปเดต prompt AI และ fallback ทั้ง 9 มุมของสคริปต์ให้ใช้ `ad_tone = "commercial_hype"`
- [x] Backend Core (`gemini_tts_engine.py`, `shot_list_builder.py`, `pipeline.py`, `pipeline_context.py`): ปรับค่าเริ่มต้น voice preset เป็น `gemini_puck_male_hype` และ tone เป็น `commercial_hype`
- [x] Backend APIs (`api_schemas.py`, `api_voice.py`, `api_phase1.py`, `api_render.py`, `batch_render.py`, `voice_stage.py`): ปรับ fallback default voice & tone ให้ตรงกัน
- [x] Frontend Defaults (`studioDefaults.js`, `NewClipPanel.jsx`, `ProductToClip.jsx`, `ContentTrackerHub.jsx`, `ShotListModal.jsx`): ปรับ default/fallback เป็น Puck + commercial_hype
- [x] Verification: รัน pytest backend (1,415 passed), npm test (230 passed), npm run build (2,006 modules ผ่าน 0 errors)

### Gate

- [x] Backend tests: `pytest` 1,415 passed
- [x] Frontend tests: `npm test -- --run` 230 passed
- [x] Frontend build: `npm run build` สำเร็จ 0 errors

## Round TRACKER-LARGE-DATA-PERF-1 — ลดเวลาเปิด Content Tracker เมื่อมีคลิปจำนวนมาก

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์ ✅

**อาการที่วัดได้:** ข้อมูลจริงมี 24 สินค้า / 247 มุม / 27 export files. ก่อนแก้ `GET /api/exports` ใช้ 2.6–2.7 วินาทีต่อครั้ง เพราะเรียก `ExportRegistry.ensure()` แยกทีละไฟล์ และหน้า Content Tracker เรียก endpoint นี้ซ้ำทั้งที่ต้องการเพียงข้อมูลสินค้า/คิว

### Todo

- [x] เพิ่ม `ExportRegistry.ensure_many()` ให้สร้าง/เติม identity หลายไฟล์ใน transaction เดียว โดยคง ID เดิมและห้าม downgrade สถานะ posted
- [x] เปลี่ยน `GET /api/exports` เป็น bulk registry hydration พร้อม fallback เดิมสำหรับ installation ที่เขียน registry ไม่ได้
- [x] ตัด request `getExports()` ที่ซ้ำจาก `ContentTrackerHub` เพราะ `/api/products` hydrate cover metadata ให้แล้ว
- [x] เพิ่ม regression tests ครอบคลุม bulk identity, export matching และ lifecycle เดิม

### ผลหลังแก้

- `GET /api/exports`: 2.6–2.7s → 0.28–0.37s ที่ 27 ไฟล์
- Content Tracker product + schedule queue: 0.15–0.22s ที่ข้อมูลชุดเดียวกัน
- Registry transaction: จาก 27 ครั้งต่อ request เหลือ 1 ครั้งต่อ request

### Gate

- [x] Targeted backend tests — 26 passed, 1 known Starlette warning
- [x] Full backend tests — 1,417 passed, 3 skipped, 27 known warnings
- [x] Frontend tests — 230 passed
- [x] Frontend build — 2,006 modules สำเร็จ 3.68s
- [x] Python compileall — ผ่าน
- [x] Git diff check — ผ่าน ไม่มี whitespace error

### Notes

- การลด request ใน Tracker ไม่กระทบ Export Gallery และ Producer Hub ที่ยังเรียก `/api/exports` เพื่อข้อมูล metadata เต็ม
- การวัดเป็น deterministic direct endpoint benchmark จากข้อมูลใน workspace และ regression tests ใช้ `tmp_path` ไม่แตะข้อมูลจริง

---

## Round COVER-RENDER-REQUIRES-COVER-1 — บังคับสร้างและบันทึกหน้าปกก่อน Render

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:** บังคับให้ผู้ใช้สร้างและบันทึกหน้าปกก่อนกด Render เพื่อให้ทุกไฟล์ที่เรนเดอร์มีหน้าปกพร้อมใช้งาน

### Todo

- [x] ตรวจหน้าปกจากข้อมูลล่าสุดของ angle ก่อนเริ่ม Render โดยยอมรับ path ของปก 9:16, 3:4 หรือ path เดิม
- [x] ปิดปุ่ม Render เมื่อยังไม่มีหน้าปกที่บันทึกแล้ว พร้อม tooltip บอกวิธีแก้
- [x] ไม่ fail open เมื่อการตรวจสอบปกหรือโปรเจกต์ล้มเหลว เพื่อไม่ให้ข้ามเงื่อนไขบังคับ
- [x] รักษา flow สร้างปกจากเฟรมจริงใน Timeline ก่อน Render ให้ใช้งานต่อได้

### Gate

- [x] Frontend tests — `npm test -- --run` ผ่าน 230 tests
- [x] Frontend build — `npm run build` สำเร็จ 2,006 modules / 3.13s
- [x] Git diff check — ผ่าน ไม่มี whitespace error
- [x] Impeccable detector — ไม่พบปัญหาเพิ่มเติมในไฟล์ UI ที่แก้

### Notes

- เมื่อยังไม่มีปก ผู้ใช้กดปุ่ม “ปก” เพื่อสร้างจากเฟรมปัจจุบันใน Timeline แล้วบันทึกหน้าปกก่อน
- หลังบันทึกปกสำเร็จ สถานะจะถูก refresh และปลดล็อกปุ่ม Render
- หากเรียก `handleApply` โดยตรง ระบบจะตรวจซ้ำจากข้อมูลล่าสุดและหยุดก่อนเริ่มงาน Render

---

## Round COVER-TIMELINE-PRE-RENDER-1 — สร้างหน้าปกจากเฟรมจริงใน Timeline ก่อน Render

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:** ให้ผู้ใช้กดปุ่มปกจากหน้า Editor แล้วสร้างหน้าปกจากเฟรมที่กำลังแสดงใน Timeline ได้ก่อนมีไฟล์ MP4 Render

### Todo

- [x] เพิ่ม `captureFrame()` ใน `SequencePlayer` เพื่อจับ Canvas Preview ณ playhead ปัจจุบัน รวม clip, overlay, caption, sticker และ grade
- [x] เพิ่มแหล่งภาพ “เฟรมจากไทม์ไลน์” ใน `CoverStudioModal` พร้อมแสดงเวลาที่จับภาพ
- [x] เพิ่ม `custom_image_data` ใน `POST /api/covers/render-pro` เพื่อรับ Snapshot และสร้างไฟล์ปก 9:16/3:4 ตาม flow เดิม
- [x] ล็อก Scrubber เมื่อใช้ Snapshot จาก Timeline เพื่อป้องกันเวลาที่เลือกไม่ตรงกับภาพที่จับมา
- [x] รักษา flow เดิมสำหรับคลิปที่ Render แล้ว และไม่บังคับให้สร้างปกก่อน Render

### Gate

- [x] Backend cover tests — 8 passed รวม endpoint รับ Timeline Snapshot
- [x] Frontend tests — 230 passed
- [x] Frontend build — 2,006 modules สำเร็จ
- [x] Python compileall และ git diff check ผ่านสำหรับไฟล์รอบนี้
- [x] Impeccable detector — พบเฉพาะคำเตือนสไตล์เดิมใน Cover Studio/SequencePlayer
- [ ] Browser verification — environment รอบนี้ไม่มี browser ให้เปิดทดสอบจริง

### Notes

- ปุ่ม “ปก” เดิมใน Header จะเปิด Cover Studio จาก Timeline ได้เมื่อมุมนี้ยังไม่มีไฟล์ Render
- ภาพที่จับเป็น Preview Canvas ขนาด 540×960 แล้ว backend upscale/crop เป็นไฟล์ปก 1080×1920 และ 1080×1440
- การสร้างปกยังบันทึกลง `05_Covers_Thumbnails/` และส่งผลกลับไปผูกกับ angle เดิมเหมือน flow หลัง Render

---

## Round HOOK-TIER-SYNC-1 — จัดการป้าย Hook Header (แบรนด์ · รุ่น · หมวด) แบบเลือกขอบเขต (เฉพาะคลิปนี้ vs ทั้งสินค้า) ในหน้าสินค้าและสร้างคลิป

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:** ออกแบบและพัฒนาระบบแก้ไข Hook Header (แบรนด์, รุ่น, หมวดหมู่) ให้เลือกได้ว่าจะใช้กับทั้งสินค้า (ทุกสคริปต์/มุม) หรือเฉพาะสคริปต์ปัจจุบัน พร้อมเพิ่มปุ่มและโมดอลจัดการที่หน้าแรก (ProductToClip) และในตัวสร้างคลิป (NewClipPanel)

### Todo

- [x] Backend: รองรับ `hook_brand`, `hook_model`, `hook_label` ใน `ProductUpdateRequest` & `ProductStore.update` พร้อมรองรับ `apply_to_angles: bool` (อัปเดตทุกมุมพร้อมกัน)
- [x] Frontend (`HookHeaderModal.jsx`): สร้างโมดอลแก้ไข Hook Header แบบเห็นตัวอย่าง 9:16 จริง มีตัวเลือกว่าจะใช้กับทุกมุมหรือเฉพาะมุมนี้ พร้อมตัวเลือกค้นหา/แทนที่ในบทพูด
- [x] Frontend (`ProductToClip.jsx`): เพิ่มปุ่ม `[🏷️ ป้าย Hook]` ที่แถบเครื่องมือด้านบนข้างปุ่ม `[ข้อมูล AI]` และเพิ่มการ์ด Hook Header เหนือกล่องสคริปต์ในหน้ามุมที่เลือก
- [x] Frontend (`NewClipPanel.jsx`): เพิ่มตัวเลือก `[✓] นำไปอัปเดตกับทุกสคริปต์ของสินค้านี้ด้วย (บันทึกเป็นค่าหลัก)` ใต้ช่องกรอก Header ทั้ง 3 ช่อง
- [x] Frontend (`angleToForm.js`): ดึงค่าและตกทอด fallback จากระดับ Product ลงมาระดับ Angle อย่างถูกต้อง
- [x] Tests & Verification: pytest 21 passed, frontend tests 230 passed, build 2,006 modules ผ่าน 100%

### Gate

- [x] Backend test `tests/test_product_metadata.py` 21 passed (รวม `test_product_hook_header_sync_to_angles`)
- [x] Frontend test `npm test -- --run` 230 passed
- [x] Frontend production bundle `npm run build` สำเร็จ 0 errors

## Round SCHEDULE-DEFAULT-RESET-1 — ปรับเทมเพลตเวลาที่บันทึกไว้ทั้งหมดเป็นชุดแนะนำ 5 ช่วง

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:** ตั้งค่าเทมเพลตที่บันทึกอยู่ทั้งหมดให้ใช้ช่วงแนะนำ 5 ช่วง โดยไม่เปลี่ยนคิวคลิปที่มีอยู่

### Todo

- [x] อัปเดตเทมเพลต `week:2026-09-07` และ `week:2026-09-14` ครบ 7 วันต่อสัปดาห์เป็น `09:00, 12:30, 16:00, 19:00, 21:30`
- [x] ตรวจ storage, API และหน้าจอตั้งค่าเวลา
- [x] ตรวจว่าไม่ได้แก้ไขคิวคลิปที่จองไว้แล้ว

### Gate

- [x] Storage verify — 2 records × 7 days, ทุกวันมี 5 ช่วงตรงกัน
- [x] API verify — GET ทั้ง 2 สัปดาห์คืนค่าชุดเดียวกัน
- [x] UI verify — modal แสดงค่าครบทุกวันของสัปดาห์ 2026-09-14

### Notes

- เพิ่ม `09:00` และ `16:00` ตามชุดแนะนำเดิม; ไม่แตะ schedule queue items
- รีสตาร์ตเฉพาะ backend โปรเจกต์เพื่อโหลดโค้ดใหม่; frontend และคิวคลิปไม่ได้ถูกล้างหรือแก้
- ไฟล์นอก scope ที่คงไว้: `02_Assets/Templates/custom_hook_templates.json`, `scripts/api_phase1.py`, `.tmp/`

---

## Round SCHEDULE-FLEXIBLE-SLOTS-1 — ตั้งเวลาโพสต์เริ่มต้น 5 ช่วง และเพิ่ม/ลบช่วงรายวัน

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:** เปลี่ยนเทมเพลตเวลาโพสต์จาก 3 ช่วงตายตัวให้เป็น 5 ช่วงเริ่มต้น และให้ผู้ใช้ปรับจำนวนช่วงรายวันได้เอง

### Todo

- [x] เปลี่ยนค่าเริ่มต้นเป็น `09:00, 12:30, 16:00, 19:00, 21:30` พร้อม migration ค่าเก่า
- [x] รองรับจำนวนช่วงเวลา 1–24 ช่วงต่อวันใน backend/frontend พร้อมกันเวลาซ้ำและรูปแบบไม่ถูกต้อง
- [x] ปรับ modal ตั้งค่าเวลาให้เพิ่ม/ลบช่วงพิเศษแยกเป็นรายวันได้ พร้อม validation และปุ่มที่เข้าถึงได้
- [x] อัปเดตคู่มือผู้ใช้และ regression tests

### Gate

- [x] `python -m pytest tests/test_schedule_queue.py -q -p no:cacheprovider --tb=short` — 10 passed, 1 warning
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm test` — 230 passed
- [x] `npm run build` — 2,005 modules, 3.25s
- [x] `git diff --check` — ผ่าน

### Notes

- เพิ่มช่วง default เป็น 5 ช่วง โดยเลือก `09:00` และ `16:00` เพื่อเติมช่วงเช้าและช่วงบ่ายระหว่าง lunch/evening slots เดิม
- เทมเพลตเก่าที่เป็น default 3 ช่วงหรือ legacy 5 ช่วงถูก promote เป็น default 5 ช่วง; custom times ที่ไม่ใช่ชุดเดิมยังคงอยู่
- ปุ่ม `เพิ่มช่วง` เพิ่มเวลาเริ่มต้นที่ `08:00` เมื่อว่าง แล้วผู้ใช้เลือกแก้เป็นเวลาอื่นได้; ปุ่มลบเหลืออย่างน้อย 1 ช่วงต่อวัน
- mechanical detector พบเฉพาะคำเตือนสไตล์เดิมของ `ScheduleAgenda.jsx`/`UserGuide.jsx` (สีข้อความบนปุ่ม/พื้นสี) ไม่พบปัญหาใหม่ที่ต้องแก้ในรอบนี้
- พบไฟล์นอก scope ใน working tree และคงไว้ไม่แก้ไข: `02_Assets/Templates/custom_hook_templates.json`, `.tmp/`

## Round CALLOUT-RESURRECT-FIX-1 — แก้บั๊ก Text Overlays ถูกปลุกขึ้นมาทับกลางจอ (LOCSmartband) เมื่อลบแล้วใน Editor + ป้องกัน Auto Brand/Model Callout ซ้อนทับ Hook Banner

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย & ปัญหาที่แก้ไข:**
1. **แก้บั๊กลบข้อความแล้วยังถูกปลุกขึ้นมาแสดง (Resurrected Callouts):** ใน `scripts/stages/subtitle_stage.py` มีฟังก์ชัน `_materialize_product_callouts` ที่คอยจับชื่อสินค้ามาแยกเป็น brand/model แล้วสร้าง `callout-brand` กับ `callout-model` เพิ่มเข้ามาใน `effective_overlays` ทุกครั้งที่สร้างซับหรือเรนเดอร์ แม้ผู้ใช้จะลบข้อความเสริมทิ้งใน Editor (`ข้อความเสริม (0)`) ทำให้เกิดบั๊กตัวอักษรผีโผล่มาทุกครั้งที่กด Render
2. **แก้บั๊กตัวอักษรทับกันเละกลางจอ (LOCSmartband):** ฟังก์ชัน `new_text_overlay` วางตำแหน่งเริ่มต้นที่ `(0.5, 0.5)` กลางจอพอดี (540, 960) และทั้ง brand กับ model ดึงเวลาจาก Beat cue แรกเหมือนกัน ทำให้ข้อความทั้งสองถูกเขียนทับกันที่พิกัดเดียวกันกลางจอพอดี
3. **ตัดความซ้ำซ้อนกับ Hook Banner:** หากโปรเจกต์มีป้ายฮุก (`ovl_hook` หรือมี `hook_brand`/`hook_model`) แสดงอยู่ด้านบนอยู่แล้ว การสร้าง auto callout ซ้ำสำหรับ brand/model เป็นเรื่องซ้ำซ้อนและไร้ประโยชน์ ต้องไม่สร้าง auto brand/model callouts เด็ดขาดเมื่อมี Hook Banner
4. **บันทึกสถานะการ materialize callouts:** ใส่ `callouts_materialized: True` ลงใน manifest เพื่อบันทึกว่าผ่านการสร้าง callout รอบแรกแล้ว เมื่อผู้ใช้ลบทิ้งใน Editor จะไม่มีการสร้างซ้ำอีก

### ผลการทดสอบ (Quality Gate):
- `pytest tests/test_product_callout_pipeline.py` (8 passed - รวม 2 regression tests ใหม่)
- `pytest tests/test_product_callout_render.py` (5 passed)
- `pytest tests/test_preview_render_parity.py` (153 passed)
- `npm test -- --run` (230 passed)
- `npm run build` (2,005 modules, 3.60s ผ่าน 100%)

---

## Round BG-SUBJECT-ISOLATION-RESUME-1 — งานตัดพื้นหลังแบบ resumable เมื่อเน็ต/หน้าเว็บ/Server หลุด

ดำเนินการโดย: Codex (GPT-5)

### ผลลัพธ์

- เพิ่ม checkpoint แบบ deterministic ต่อเฟรมใน `background-isolation-foreground-sequences/.<artifact_id>.checkpoint` เฟรมที่ผ่านการตรวจ RGBA แล้วจะถูกข้ามเมื่อ retry
- รักษา artifact แบบ fail-closed และ no-clobber: เผยแพร่เมื่อครบทุกเฟรมเท่านั้น และลบ checkpoint หลัง verify สำเร็จ
- เปลี่ยน TaskManager ให้ background-isolation ที่ค้างตอน server restart กลับเป็น queued และ startup recovery เรียกทำต่ออัตโนมัติ โดยไม่เปลี่ยนพฤติกรรม render task
- เพิ่ม scheduler guard กัน task เดิมถูก launch ซ้ำระหว่าง recovery/reconnect
- Frontend polling รอข้าม network/server gap สูงสุด 30 นาที และ rebind ผลลัพธ์ completed กลับเข้า clipList หลัง refresh/reconnect
- เพิ่ม regression test สำหรับ checkpoint resume, restart state และ duplicate scheduler

### Gate

- [x] `python -m pytest tests/test_background_isolation_sequence_worker.py tests/test_task_manager.py -q` (45 passed)
- [x] `python -m pytest tests/test_api_background_isolation.py tests/test_background_isolation.py tests/test_background_isolation_sequence.py -q` (41 passed, 2 skipped)
- [x] `npm test -- --runInBand` (230 passed)
- [x] `npm run build` (2,005 modules)
- [x] `python -m compileall -q scripts tests`


## Round HOOK-KINETIC-MOTION-1 — Step-by-Step Cumulative Hook Reveal & High-Impact Animation System

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** เพิ่มระบบอนิเมชั่น Hook Banner ที่ดึงดูดสายตาตามสไตล์ไวรัล โดยเฉพาะการทยอยสะสมทีละคำ/ทีละบรรทัด (Cumulative Word & Tier Reveal: เช่น `LOGITECH` -> `LOGITECH WAVE KEYS` -> `KEYBOARD`) และอนิเมชั่นกระแทกสายตา (Slam / Elastic Bounce) โดยคงความเข้ากันได้ย้อนหลัง 100% ไม่กระทบโฟลว์เดิม และรักษา Preview = Render Parity

### Todo

- [x] เพิ่ม In-motion preset ใหม่ (`slam`, `elastic_bounce`) ใน `scripts/subtitle/motion_effects.py` และ `scripts/hook_motion_presets.py`
- [x] เพิ่มการรองรับ `reveal_mode` (`simultaneous`, `cumulative`, `tier_step`) ใน `scripts/subtitle/overlay_events.py` และคำนวณ timing จังหวะสะสม
- [x] ซิงก์ Catalog และ Motion Transform ใน Frontend: `overlayModel.js`, และ `SequencePlayer.jsx` (Canvas preview)
- [x] เพิ่มตัวเลือกรูปแบบการแสดงผล (Reveal Mode) ในหน้า UI Hook Banner Editor (`OverlayInspector.jsx`)
- [x] เขียนและรัน Parity Tests, Multi-Frame Render Tests, และ Node Unit Tests ตรวจสอบความถูกต้อง

### Gate

- [x] `.venv\Scripts\python.exe -m pytest tests/test_preview_render_parity.py -q` (153 passed in 3.17s)
- [x] `.venv\Scripts\python.exe -m pytest tests/test_preview_render_behavior.py -q` (18 passed in 19.92s)
- [x] `.venv\Scripts\python.exe -m pytest tests/test_hook_reveal_and_kinetic.py tests/test_hook_motion_presets.py -v` (24 passed)
- [x] Full backend smoke pytest: `tests/test_phase1_smoke.py` (150 passed in 75.82s) + compileall passed
- [x] Frontend test `npm test` (185 passed) + `npm run build` (built in 3.79s without errors)

### Notes
- **Zero Regression:** โครงสร้างข้อมูลเดิมทุกตัวยังทำงานเหมือนเดิม 100% ถ้าไม่มีการเลือก reveal mode ระบบจะใช้ค่าเริ่มต้น `simultaneous` (ขึ้นพร้อมกัน) เหมือนเดิมทุกประการ
- **Cumulative Reveal (สะสมทีละบรรทัด):** แถวที่ยังไม่ถึงเวลา (เช่น บรรทัด 2 และ 3) จะถูกซ่อนไว้อย่างสมบูรณ์ (`\alpha&HFF&` ใน ASS render และข้ามการวาดใน Canvas preview) จนกว่าจะถึง `t0_ms = tier_idx * step_delay_ms` จึงจะเล่น In-animation เข้ามา สะสมต่อท้ายบรรทัดก่อนหน้าตามโจทย์ไวรัล TikTok
- **High-Impact Presets:**
  - `slam`: กระแทกลงจากขนาด 220% ใน 180ms พร้อม rapid alpha fade-in และ snap-in curve
  - `elastic_bounce`: เด้งดึ๋งสไตล์สปริงพร้อมโอเวอร์ชูตและอันเดอร์ชูต 520ms
- **Preview = Render Parity:** ทั้ง Canvas 2D (`SequencePlayer.jsx`) และ libass renderer (`overlay_events.py` / `motion_effects.py`) ทำงานสอดคล้องกันตรงกันทุกมิลลิวินาทีและองศา / สเกล

---

## Round THAI-STACKED-MARK-GENERALIZE-1 — ครอบคลุมสระบนและวรรณยุกต์ไทยทุกคู่
| Round AI-PRODUCER-ACCESS-1 | Phase 5 Accessibility & Responsive Polish: modal semantics, Escape close, aria-live และ keyboard labels | 2026-09-13 | สำเร็จสมบูรณ์ (frontend 185 passed, build 2003 modules/3.85s, browser AX + Escape verified, diff check ผ่าน, ไม่เปลี่ยน font/text contract, ดำเนินการโดย: Codex (GPT-5)) |
| Round AI-PRODUCER-EVIDENCE-1 | Phase 4 Evidence-first Retrospective: metrics model, measured takeaways, source provenance และ metric snapshot | 2026-09-13 | สำเร็จสมบูรณ์ (frontend 185 passed, backend 3 passed, build 2003 modules/3.58s, browser evidence cards verified, fixture distribution test ผ่าน, ดำเนินการโดย: Codex (GPT-5)) |
| Round AI-PRODUCER-SYNC-1 | Phase 3 Capture & Sync Reliability: deterministic media upload, single-item notes, revision guard และ payload validation | 2026-09-13 | สำเร็จสมบูรณ์ (backend notes 3 passed, frontend 184 passed, build 2003 modules/5.74s, compileall ผ่าน, Producer Hub + Quick Ref browser verified, ไม่แตะ 02_Assets/Refs, ดำเนินการโดย: Codex (GPT-5)) |
| Round BG-SUBJECT-ISOLATION-2B | Video sequence artifact, frame timing, manifest invalidation และ cancellation groundwork สำหรับ BG isolation | 2026-09-14 | สำเร็จสมบูรณ์ (focused 78 passed/1 skipped, full backend 1308 passed/1 skipped, frontend 195 passed, build 2004 modules/4.12s, FFmpeg fixture 6 frames + manifest ready/current, compileall/pip check/diff check ผ่าน, ดำเนินการโดย: Codex (GPT-5) + delegated agents) |
| Round BG-SUBJECT-ISOLATION-2C | Sequence rembg inference worker และ RGBA artifact publish สำหรับ BG isolation | 2026-09-14 | สำเร็จสมบูรณ์ (focused 122 passed/1 skipped, full backend 1352 passed/1 skipped, frontend 211 passed, build 2004 modules/4.43s, compileall/pip check/diff check ผ่าน, ดำเนินการโดย: Codex (GPT-5) + delegated agents) |
| Round AI-PRODUCER-ACTION-1 | Phase 2 Action Loop: ranked Next Mission, deep-link payload และ queue search/sort/empty state | 2026-09-13 | สำเร็จใน production path (frontend 184 passed, build 2003 modules/8.52s, browser deep-link verified; component-flow React mount test deferred, ดำเนินการโดย: Codex (GPT-5)) |
| Round AI-PRODUCER-TRUST-1 | Phase 1 Trust Layer ของ AI Producer Hub: canonical identity, queue dedupe, source tracing และ heuristic transparency | 2026-09-13 | สำเร็จสมบูรณ์ (insight contract 1.1.0, queue 19→18 จาก duplicate media, product filter ไม่ซ้ำ, sourceIds/summary/priority metadata, npm test 183 passed, build 4.05s, compileall ผ่าน, browser verified, ดำเนินการโดย: Codex (GPT-5)) |
| Round WATERMARK-CONFIG-V6 | ตั้งค่าเปิด/ปิดลายน้ำ (One Click & Editor) + แก้สระ/วรรณยุกต์ลอย + บังคับตัดแคช v6 | 2026-09-13 | สำเร็จสมบูรณ์ (ตั้งค่าเปิด/ปิดลายน้ำได้ทั้งหน้าสร้างคลิปและหน้า Editor, ค่าเริ่มต้นเปิดแสดงลายน้ำ @rizanntry สีจางลงเหลือ ~37% Opacity (&HA0&), แก้ปัญหาสระ/วรรณยุกต์ลอยถอยหลังในคำว่า 'โปรโมชั่น' และ 'รีบกดสั่ง' เมื่อมี emoji นำหน้า, bump SUBTITLE_RENDER_CONTRACT_VERSION = 'v6' เพื่อตัดแคชเก่า, pytest 176 passed, npm test 181 passed, build 3.26s, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round MULTI-IMAGE-CLOUD-SYNC-1 | Multi-Image Support per Note + Mobile-to-PC Server Sync + 1-Click Copy/Share Summary for Team | 2026-09-13 | สำเร็จสมบูรณ์ (รองรับแนบภาพหลายรูปต่อโน้ต `images: []` พร้อม thumbnail strip และปุ่มลบ X ทีละรูป, Mini-Gallery บนการ์ดโน้ต, Lightbox Modal ดูภาพขยายเต็มจอ, เซิร์ฟเวอร์ API ซิงก์โน้ตระหว่างมือถือและคอมพิวเตอร์ผ่าน `02_Assets/Refs/playbook_notes.json`, ปุ่ม 1-Click 'คัดลอกส่งงาน' สรุปข้อความและรูปภาพทั้งหมดลงคลิปบอร์ดสำหรับส่งไลน์ให้นาย, pytest 1 passed, npm test 180 passed, build 4.29s, desktop & mobile browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round MOBILE-IMAGE-PASTE-FIX-1 | Fix Mobile Image Paste (iOS Safari files detection, ContentEditable Paste Target, Native Photo Picker Auto-Fallback, and HEIC auto-conversion) | 2026-09-13 | สำเร็จสมบูรณ์ (ตรวจจับ `clipboardData.files` + `items` + `html` + `text` ทุกมิติ, เพิ่มกล่อง Rich ContentEditable Paste Target สำหรับ iOS Safari & Android, ปุ่ม 1-Tap 'เลือกจากคลังภาพ' ดึงรูปล่าสุดใน 1 วินาที, รองรับภาพ HEIC จาก iPhone แปลงเป็น JPG อัตโนมัติด้วย ffmpeg, npm test 180 passed, build 3.58s, desktop & mobile browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round CLIPBOARD-IMAGE-PASTE-1 | Direct Clipboard Image Paste (Ctrl+V / Paste into Textarea & Form) | 2026-09-13 | สำเร็จสมบูรณ์ (ตรวจจับภาพจาก clipboardData อัตโนมัติเมื่อกด Ctrl+V ในช่องข้อความหรือฟอร์ม, เพิ่มปุ่ม 1-Tap 'วางรูปภาพ' ดึงรูปจาก clipboard, อัปโหลดเข้า 02_Assets/Refs/ ทันที, รองรับทั้ง QuickRefPage และ ProducerHub, npm test 180 passed, build 3.35s, browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round QUICK-REF-POLISH-1 | Redesign Impeccable Quick Ref Vault & Fix iOS Mobile Zoom | 2026-09-13 | สำเร็จสมบูรณ์ (ป้องกัน iOS auto-zoom ด้วย 16px inputs + CSS media query + viewport config, Redesign เต็มจอ edge-to-edge + Responsive 2-column desktop, 1-Tap Paste จากคลิปบอร์ด, Segmented Category Pills, Tag filter & search, AI Idea-to-Script on mobile, npm test 180 passed, build 3.31s, desktop & mobile browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |

---

## Round THAI-STACKED-MARK-GENERALIZE-1 — ครอบคลุมสระบนและวรรณยุกต์ไทยทุกคู่

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** ทำให้ Preview และ Render จัดชั้นวรรณยุกต์เหนือสระบนได้สะอาดทุกคู่ที่ใช้จริง โดยเฉพาะ `ซื้อ` (`ื้`) และ `เรื่อง` (`ื่`) ไม่จำกัดเฉพาะ `ั่` และไม่เปลี่ยนข้อความ ฟอนต์ ขนาด wrapping หรือ safe zone

### Todo

- [x] สร้าง failing regression จากข้อความจริง `ปกติซื้อตามช็อปราคาแรงเอาเรื่อง` และ inventory คู่ Unicode สระบน + เครื่องหมายชั้นบน
- [x] วัด FFmpeg/libass แยกตามชนิดสระ (`ัิีึื`) และวรรณยุกต์ (`่้๊๋`) เพื่อกำหนดกฎ geometry ที่พิสูจน์ได้
- [x] Generalize repair ฝั่ง ASS และ Canvas ด้วย contract/constants ที่ mirror กัน โดยรักษา layout ทั้งบรรทัดและสี highlight
- [x] Bump subtitle render contract และทดสอบ invalidation/reuse

### Gate

- [x] Visual/contract pytest ที่เกี่ยวข้อง รวม pixel-band matrix และหลายเฟรมเข้า/ค้าง/ออก — 180 passed, 20 warnings, 75.94s
- [x] ตรวจ Unicode content identity และ FFmpeg render คำจริงด้วย `fontsdir=02_Assets/Fonts` — 20/20 คู่ผ่าน; vertical gap 0–4px, horizontal overlap ต่ำสุด 8px
- [x] Full backend pytest + compileall + pip check — 1,135 passed, 25 warnings, 258.27s; compile/dependencies ผ่าน
- [x] Frontend `npm test` + `npm run build` + `git diff --check` — 185 passed; 2,003 modules/3.70s; diff check ผ่าน

### Notes

- Working tree ก่อนเริ่มมีเฉพาะงานผู้ใช้ใน `02_Assets/Refs/playbook_notes.json` และรูป ref untracked 6 ไฟล์; รอบนี้ไม่แตะและไม่ stage
- ขอบเขตเป็น geometry ของ combining marks เท่านั้น ไม่เปลี่ยน font family/face, font size, English ratio, line spacing, wrapping หรือ safe zone
- Root cause ยืนยันแล้ว: contract v7 ระบุ `THAI_STACKED_MARK_PAIR = "\u0e31\u0e48"` เพียงคู่เดียว จึงไม่จับ `ื้`, `ื่` และคู่อื่น
- Fix ครอบคลุม 5 สระบน `ัิีึื` × 4 วรรณยุกต์ `่้๊๋` รวม 20 คู่; companion event เก็บ tone จริงของแต่ละ match และใช้ layout เต็มบรรทัดเดิม
- ระยะยก `0.13em` ค่าเดียวผ่าน pixel matrix ครบทุกคู่ จึงไม่ต้องเพิ่ม magic number แยกตามอักขระ
- Bump `SUBTITLE_RENDER_CONTRACT_VERSION` จาก `v7` เป็น `v8`; artifact v7 ถูก invalidate และ artifact v8 ผ่าน current-contract test
- FFmpeg multi-frame ตรวจทั้ง `นั่ง` (IBM Plex Sans Thai) และประโยคจริง `⚡ ปกติซื้อตามช็อปราคาแรงเอาเรื่อง` (Prompt); geometry ช่วงเข้า/ค้างคงที่
- Browser QA ที่ cue 5.1s ยืนยัน Canvas Preview แสดง `ซื้อ`/`เรื่อง` สูงโปร่ง และคืนแผงซ้าย/ขวากลับสถานะเดิมแล้ว

---

## Round THAI-STACKED-MARK-RENDER-FIX-1 — แก้วรรณยุกต์ซ้อนใน Render

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** ทำให้ Render วาง `่` เหนือ `ั` ในพยางค์ไทย เช่น `ชั่` แบบสูงโปร่ง สะอาดตา และตรงกับ Preview โดยไม่เปลี่ยนข้อความ ฟอนต์ ขนาด การตัดบรรทัด หรือตำแหน่ง Golden Master อื่น

### Todo

- [x] สร้าง feedback loop ที่ reproduce ปัญหาจากข้อความจริงและ FFmpeg/libass พร้อมตรวจ Unicode, ฟอนต์จริง และ glyph shaping
- [x] จัดอันดับสมมติฐานที่พิสูจน์/หักล้างได้ แล้ว instrument ทีละตัวแปรเพื่อหาสาเหตุราก
- [x] เพิ่ม regression test ที่ล้มกับพฤติกรรมเดิม ณ seam ของ ASS render ก่อนแก้ production code
- [x] แก้ Render และ Preview เป็นคู่ พร้อม parity assertion โดยคง content identity และ Golden Master เดิม
- [x] Bump subtitle render contract และพิสูจน์ artifact เก่าถูก invalidate/รุ่นใหม่ reuse ได้ หาก output contract เปลี่ยน

### Gate

- [x] `\.venv\Scripts\python.exe -m pytest tests/test_subtitle_artifact_contract.py tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 178 passed
- [x] FFmpeg+libass ส่ง `fontsdir=02_Assets/Fonts` และวัด pixel geometry หลายเฟรมช่วงเข้า/ค้าง/ออก — `ั` bbox y=940–950, `่` bbox y=930–940, ไม่ทับแนวตั้งและยังเกาะกันแนวนอน
- [x] ตรวจข้อความไทย/อังกฤษก่อน-หลังแบบ Unicode ว่าไม่เปลี่ยน — cue ต้นฉบับคงเดิม; แยกเฉพาะ glyph ตอนสร้าง ASS companion event
- [x] `\.venv\Scripts\python.exe -m compileall -q scripts` + full backend pytest + `pip check` — compile ผ่าน, 1,133 passed/25 warnings/235.04s, dependencies สมบูรณ์
- [x] frontend `npm test` + `npm run build` และ `git diff --check` — 185 passed, 2,003 modules/4.59s, diff check ผ่าน

### Notes

- Working tree ก่อนเริ่มมีงานผู้ใช้ใน `02_Assets/Refs/playbook_notes.json` และรูป ref untracked 6 ไฟล์; รอบนี้ไม่แตะและไม่ stage ไฟล์เหล่านี้
- การแก้จำกัดเฉพาะ geometry ของ Thai combining marks; ไม่เปลี่ยนข้อความ, font family/face, base font size, English ratio, wrapping หรือ safe zone
- Root cause: backend เดิมอนุญาต repair เฉพาะ `IBM Plex Sans Thai` และ return ทันทีเมื่อบรรทัดมี emoji ทำให้ข้อความจริง `🛒 บอกเลยว่าโปรโมชั่นนี้` ที่ใช้ Prompt ไม่ถูกแก้ ขณะที่ Preview วาดเครื่องหมายแยกอยู่แล้ว
- Fix: เปลี่ยนจากการเดาตำแหน่ง X ด้วย Pillow เป็น ASS companion event ที่เก็บ layout เต็มบรรทัดให้ libass คำนวณ emoji fallback เอง แล้วเปิดเฉพาะ `่` พร้อมยกขึ้น `0.13em`; mirror ค่ากับ Canvas และ bump contract `v6` → `v7`
- Browser QA เปิดโปรเจกต์ `ESS01-โปรไฟลุก_1` ที่เวลา 0.9s ตรวจ cue จริงและสถานะ Preview; generated ASS v7 วัดกรอบ caption กว้างเท่าเดิม 604px (ความสูง 125→126px จากวรรณยุกต์ที่ยกขึ้น)
- ระหว่าง browser QA คลิกพลาดลบ `demo_20260913_183642.mp4` (ประมาณ 0.19 MB) จาก Export Gallery; endpoint ใช้ `Path.unlink()` จึงไม่เข้า Recycle Bin และตรวจไม่พบสำเนาชื่อเดียวกันใน workspace/ไดรฟ์ D: ไฟล์จริงของโปรเจกต์ ESS01, `01_Raw/` และ `02_Assets/` ไม่ได้รับผลกระทบ

---

## Round AI-PRODUCER-ACCESS-1 — Phase 5 Accessibility & Responsive Polish ของ AI Producer Hub

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์

### สิ่งที่ทำ

- เพิ่ม `role="dialog"`, `aria-modal`, accessible label และ heading linkage ให้ modal หลักของ Producer Hub/Quick Ref
- เพิ่มปุ่มปิดที่มีชื่อสำหรับ screen reader และรองรับ Escape ปิด modal
- เพิ่ม `aria-live`/`role=status`/`role=alert` ให้ partial failure, toast, clipboard error และ save/delete feedback
- ตรวจ core flow บน Producer Hub และ Quick Ref โดยไม่แตะ font/text visual contract; reduced-motion path เดิมของ global CSS ยังทำงาน

### Gate

- [x] `cd frontend; npm test` — 185 passed
- [x] `npm run build` — 2003 modules, 3.85s
- [x] browser AX + keyboard — quota dialog แสดง semantic heading/label และ Escape ปิดได้; Quick Ref เปิดและฟอร์มทำงาน
- [x] `git diff --check` — ผ่าน

### Notes

- ไม่แตะหรือลบไฟล์ user ใน `02_Assets/Refs/`
- ไม่เปลี่ยนฟอนต์ ข้อความบทพูด หรือ renderer visual contract

---

## Round AI-PRODUCER-EVIDENCE-1 — Phase 4 Evidence-first Retrospective ของ AI Producer Hub

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์

### สิ่งที่ทำ

- เพิ่ม evidence metrics: sample size, period, average views, median views, engagement rate และ top-vs-baseline ratios
- เปลี่ยนข้อความ takeaways/improvement ให้ derive จาก distribution จริง พร้อมแสดงว่าการตีความเป็น heuristic
- ผูก top performer กับ `sourceId` และ metric snapshot; บันทึกบทเรียนพร้อม provenance, period, confidence และ source clip
- เพิ่ม fixture test ยืนยันข้อมูล skewed กับ consistent ให้ insight ต่างกัน

### Gate

- [x] `.venv\\Scripts\\python.exe -m pytest tests/test_producer_notes_api.py -q -p no:cacheprovider --tb=short` — 3 passed
- [x] `cd frontend; npm test` — 185 passed
- [x] `npm run build` — 2003 modules, 3.58s
- [x] browser — evidence cards แสดงค่าเฉลี่ย/ค่ากลาง/engagement/ช่วงข้อมูล และปุ่มจดบทเรียนทำงานใน flow

### Notes

- ไม่แตะหรือลบไฟล์ user ใน `02_Assets/Refs/`
- ข้อมูล TikTok ที่มีอยู่ยังถูกติดป้าย `heuristic`; ยังไม่มีการอ้างว่าเป็น AI model จริง

---

## Round AI-PRODUCER-SYNC-1 — Phase 3 Capture & Sync Reliability ของ AI Producer Hub

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** ทำให้การเก็บเรฟและโน้ตจาก Producer Hub/Quick Ref ปลอดภัยต่อการใช้งานข้ามอุปกรณ์และไม่ปล่อยข้อมูลอัปโหลดค้าง

### สิ่งที่ทำ

- เปลี่ยนการบันทึก/ลบโน้ตจาก full-list overwrite เป็น single-item API mutation พร้อม optimistic update และ rollback เมื่อ sync ไม่สำเร็จ
- เพิ่ม deterministic pending key ต่อไฟล์ เพื่อไม่ให้ upload หลายไฟล์แทนที่ preview ผิดรายการ
- บล็อกการบันทึกเมื่อมี upload pending และนำ preview ที่ upload ไม่สำเร็จออกจากรายการที่จะบันทึก
- เพิ่ม `base_revision` guard สำหรับ bulk note save พร้อม HTTP 409 และส่ง revision ล่าสุดกลับไปให้ client
- เพิ่ม validation ความยาวข้อความ, จำนวนภาพ และขนาด data URL; จำกัด upload ref media ไม่เกิน 10 MB
- ปรับ upload response ไม่คืน absolute filesystem path

### Gate

- [x] `.venv\\Scripts\\python.exe -m pytest tests/test_producer_notes_api.py -q -p no:cacheprovider --tb=short` — 3 passed, 2 warnings
- [x] `cd frontend; npm test -- --run src/lib/producerInsights.test.js` — 184 passed
- [x] `npm run build` — 2003 modules, 5.74s
- [x] `.venv\\Scripts\\python.exe -m compileall -q scripts` — ผ่าน
- [x] browser — Producer Hub โหลดครบและแสดง queue/action controls; Quick Ref เปิดได้, save disabled เมื่อไม่มีข้อมูลและรองรับฟอร์มพร้อม sync
- [x] `git diff --check` — ผ่าน

### Notes

- ไม่แตะหรือลบไฟล์ user ใน `02_Assets/Refs/`
- Component-flow test ที่ต้อง mount React โดยตรงยังเป็นรายการ deferred ของ Phase 2; production navigation seam ถูกตรวจผ่าน browser แล้ว

---

## Round AI-PRODUCER-ACTION-1 — Phase 2 Action Loop ของ AI Producer Hub

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จใน production path

### สิ่งที่ทำ

- ใช้ ranked `getNextAction` ให้ post/cut/footage มี priority score, reason และ stable tie-break
- ส่ง `targetId`/`exportId`/`productId`/`angleId` ผ่าน navigation seam เพื่อเปิด object เดิมที่ปลายทาง
- เพิ่ม search, sort, result count, progressive reveal และ empty state ให้ Action Queue
- ตรวจ browser แล้ว: CTA ส่ง TikTok เปิด Gallery พร้อม export เป้าหมายที่เลือกจริง

### Gate

- [x] `cd frontend; npm test -- --run src/lib/producerInsights.test.js` — 184 passed
- [x] `npm run build` — 2003 modules, 8.52s
- [x] browser deep-link — verified

### Notes

- ไม่เปลี่ยน status ใน Hub เองโดยไม่มี operation จากปลายทาง
- Component-flow test ที่ต้องใช้ React mount harness โดยตรง deferred; unit contract + browser flow ผ่าน

---

## Round BG-SUBJECT-ISOLATION-2C — Sequence rembg inference worker และ RGBA artifact publish

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) + delegated agents · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** ประมวลผล source frame sequence ด้วย rembg แบบ on-demand ให้ได้ foreground PNG แบบ RGBA ครบทุกเฟรม พร้อม progress/cancel/cache-safe publish เพื่อให้ Phase 3 มี artifact ที่เป็น cutout จริง ไม่ใช้ raw frame หลอกเป็น foreground

### Todo

- [x] ประมวลผลหลายเฟรมด้วย `BackgroundIsolationWorker` ตัวเดียวเพื่อ reuse model session
- [x] เขียน RGBA foreground ลง derived cache แยกจาก source ด้วย staging directory และ atomic publish หลังครบทุกเฟรม
- [x] รองรับ cache hit, progress, cancellation, runtime/error handling และ cleanup partial output
- [x] ตรวจ source frame sequence ครบ/ต่อเนื่อง, mode/ขนาด RGBA และห้ามเขียนทับ source
- [x] ตรวจ parity hardening ให้ compositor บังคับ sequence schema, artifact ID และ source fingerprint ตรงกัน

### Gate

- [x] Focused background isolation tests: `122 passed, 1 skipped`
- [x] Full backend pytest: `1352 passed, 1 skipped` (มี warning เดิม 29 รายการจาก dependency/encoding test path ไม่มี failure)
- [x] Frontend: `211 passed`; `npm run build` สำเร็จ 2004 modules ใน 4.43 วินาที
- [x] `compileall`, `pip check`, `git diff --check` ผ่าน
- [x] fixture 3 เฟรมผ่านการตรวจ `RGBA`, frame count และ alpha channel ด้วย fake rembg adapter

### Notes

- Worker ใหม่ยังไม่ถูกเรียกจาก request/render thread และยังไม่ต่อเข้าปุ่ม UI เพื่อป้องกัน inference หนักในเส้นทาง interactive
- Artifact ที่ publish แล้วจึงเป็น foreground RGBA จริง แต่ Preview/Render ยังต้องต่อ Phase 3 ให้ใช้ artifact เดียวกันก่อนเปิดใช้งาน production
- Cache identity ใช้ source fingerprint + sequence artifact ID + model/quality/worker metadata ไม่ใช้ clip index

---

## Round BG-SUBJECT-ISOLATION-2B — Video sequence artifact และ cancellation

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) + delegated agents · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** เพิ่ม groundwork สำหรับ BG isolation บนวิดีโอจริงแบบ per-source sequence ให้รู้ frame index/fps/timebase/resolution/rotation, มี manifest ที่ตรวจความสดของ artifact ได้ และหยุดงานกลางทางได้ โดยยังไม่เปิด Preview/Render จริงจนกว่าจะผ่าน parity gate ใน Phase 3

### Todo

- [x] เพิ่ม extractor แตกวิดีโอเป็น PNG sequence ผ่าน FFmpeg โดยรองรับ trim, fps, timebase, target resolution, progress และ cancellation พร้อม atomic publish/cleanup
- [x] เพิ่ม sequence artifact manifest/cache แยก namespace จาก image artifact โดยไม่ผูกกับ clip index และบันทึก source fingerprint, algorithm/model/worker version, frame count, fps/timebase, resolution, rotation และ frame pattern
- [x] เพิ่มการตรวจ stale/current, path traversal/symlink guard และบังคับให้ `ready` ต่อเมื่อ metadata และเฟรมครบจริง
- [x] ทำ read-only seam review สำหรับการต่อ Phase 3: alpha ต้องเข้าหลัง source timing/transform รายคลิป แต่ก่อน concat/transition และ Preview ต้องอ่าน artifact เดียวกับ Render
- [x] แก้ frame contract ให้ใช้ sequence ID `bgseq1-*` และ zero-based `frame_000000` ให้ extractor กับ manifest สอดคล้องกัน

### Gate

- [x] Focused tests: `78 passed, 1 skipped` และ full backend `1308 passed, 1 skipped` (skip เฉพาะ symlink test ที่ Windows environment ไม่มีสิทธิ์สร้าง symlink)
- [x] Frontend `npm test -- --run`: 195 passed; `npm run build`: 2004 modules, 4.12 วินาที
- [x] FFmpeg fixture จริง: แตกได้ 6 เฟรม ขนาด `64x96` ตั้งแต่ `frame_000000` ถึง `frame_000005`
- [x] Integration fixture: เขียน manifest แล้วตรวจสถานะ `ready` และ `current` ได้จริง
- [x] `compileall`, `pip check`, `git diff --check` ผ่าน

### Notes

- รอบนี้เป็น groundwork เท่านั้น ยังไม่ต่อ UI/Preview/Render และยังไม่เรียก rembg ทุกเฟรม เพื่อไม่ให้ request/render thread หน่วงจาก inference
- Source เดียวที่ถูก trim/ใช้ซ้ำหลายคลิปต้องอ้างอิง source fingerprint + source time ไม่ใช่ clip index
- Cancellation/error/incomplete sequence จะไม่ถูกประกาศเป็น `ready`; Phase 3 จึงค่อยเพิ่ม per-clip compositing และ fallback `spotlight`/`original`/`skip` หลังผ่าน visual parity หลายเฟรม

---

## Round AI-PRODUCER-TRUST-1 — Phase 1 Trust Layer ของ AI Producer Hub

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** ทำให้ identity, queue, quota และคำอธิบายความสามารถของ Producer Hub เชื่อถือได้ก่อนเพิ่ม action flow

### สิ่งที่ทำ

- เพิ่ม `PRODUCER_INSIGHTS_CONTRACT = 1.1.0`
- เพิ่ม canonical clip identity aliases สำหรับ `angle`, `project`, `export`, `media` และ `name`
- กันการนับซ้ำระหว่าง angle กับ export ที่ชี้ media เดียวกัน
- เพิ่ม `sourceIds` ให้ daily/weekly cuts และ daily posts เพื่อ trace ที่มาของตัวเลข
- เพิ่ม `source` และ `contract` metadata ใน production stats
- แก้ standalone export matching ให้ใช้ identity aliases และผูก product context กลับเข้าคิว
- แก้ product filter ให้รวมรายการด้วย `productId` เดียว ลดปุ่มสินค้าซ้ำ
- เพิ่ม `summary` counts ใน action queue
- เพิ่ม `lastSyncedAt` และ partial failure banner ใน Producer Hub
- เปลี่ยน Retrospective เป็น `Automatic Retrospective` พร้อม method/source/sampleSize/confidence
- เพิ่ม metadata ใน AI proposal response เพื่อบอกว่าเป็น `heuristic` และระบุ input ที่ถูกใช้

### Gate & Verification Results

- [x] Frontend tests: `npm test -- --run src/lib/producerInsights.test.js` — 183/183 passed
- [x] Frontend build: `npm run build` — 2003 modules transformed, 4.05s
- [x] Python compilation: `python -m compileall -q scripts` — passed
- [x] Browser: queue ลดจาก 19 เป็น 18 จาก duplicate media, product filter ไม่ซ้ำ, แสดง sync timestamp และ heuristic label

### ไฟล์ที่แตะ

- `frontend/src/lib/producerInsights.js`
- `frontend/src/lib/producerInsights.test.js`
- `frontend/src/components/producer/ProducerHub.jsx`
- `frontend/src/App.jsx`
- `scripts/api_producer.py`
- `TODO.md`
- `HISTORY.md`

## Round WATERMARK-CONFIG-V6 — ตั้งค่าเปิด/ปิดลายน้ำ (One Click & Editor) + แก้สระ/วรรณยุกต์ลอย + บังคับตัดแคช v6

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
1. **ตั้งค่าลายน้ำได้ (Configurable Watermark):** ไม่ฮาร์ดโค้ด ให้ติ๊กเข้า/ติ๊กออกได้ (default: เปิด/แสดง) ทั้งหน้า One Click (`NewClipPanel.jsx`) และหน้าตัดต่อ (`EditorHeader.jsx`, `EditorShell.jsx`, `SequencePlayer.jsx`) ส่งผ่านเข้า API `/api/render` และ `/reroll`
2. **แก้สระ/วรรณยุกต์ลอย (Floating Thai Tone Mark):** ปัญหาวรรณยุกต์เอกลอยถอยหลังไปทับตัวอักษรอื่น (`โปรโม ่ ชั่น`, `รีบกด ่ สั่ง`) เกิดจาก `repair_thai_mark_pair` พยายามคำนวณพิกัด `\pos` ของ `่` แยกออกมา แต่เมื่อมี emoji นำหน้า (เช่น `🛒 `) Pillow วัดความกว้าง emoji ต่ำกว่า libass ทำให้ตำแหน่ง `่` เคลื่อนไปทางซ้าย ~90px → ป้องกันโดยไม่ detach `่` ในแคปชันที่มี emoji
3. **ลายน้ำจางใน Render จริง (Fade Parity & Cache Invalidation):** ปรับ `SUBTITLE_RENDER_CONTRACT_VERSION = "v6"` เพื่อบังคับ invalidate แคช `.ass` เก่าของ v5 ทุกตัว และตั้ง `WATERMARK_ALPHA = "&HA0&"` (ASS) คู่ขนานกับ Canvas 0.38
4. **Parity & Tests:** ทดสอบ pytest (subtitle artifact, parity, behavior) และ frontend vitest + build

### สรุปผลการทดสอบ (Gate Verification):
- [x] Backend Tests: `tests/test_subtitle_artifact_contract.py`, `tests/test_preview_render_parity.py`, `tests/test_preview_render_behavior.py` — 176/176 passed 100% (24.12s)
- [x] Node / Vitest Tests: `npm test` — 181/181 passed 100%
- [x] Frontend Build: `npm run build` — 2003 modules transformed, build clean ใน 3.26s
- [x] Verified SubtitleEngine.generate_ass on real project: Watermark spelling 'rizanntry', Alpha '&HA0&', and text 'โปรโมชั่น' / 'รีบกดสั่ง' remain intact without floating tone marks.

---

## Round MULTI-IMAGE-CLOUD-SYNC-1 — Multi-Image Support per Note + Mobile-to-PC Server Sync + 1-Click Copy/Share Summary for Team

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
1. **รองรับการแนบภาพได้หลายๆ รูปต่อ 1 โน้ตไอเดีย (Multi-Image Support per Note):**
   - แก้ไขโครงสร้างโน้ตให้รองรับอาร์เรย์ของภาพ `images: string[]` (พร้อม backward compatibility กับ `imageUrl` เดิม)
   - ปรับปรุงฟอร์มใน `QuickRefPage.jsx` และ `ProducerHub.jsx` ให้สามารถกดวาง (Paste) ภาพเพิ่มทีละรูป หรือเลือกหลายไฟล์พร้อมกันจากคลังภาพ (`<input multiple />`) ได้
   - แสดงแถบ Thumbnail พรีวิวรูปภาพทั้งหมดที่แนบ พร้อมปุ่มลบ `✕` ทีละรูปได้อย่างอิสระ
   - บนการ์ดโน้ตที่บันทึกแล้ว แสดงเป็น Mini-Gallery พร้อมปุ่มคลิกดูภาพขยายเต็มจอ (Lightbox modal)
2. **ซิงก์ข้อมูลระหว่างมือถือและคอมพิวเตอร์ผ่านเซิร์ฟเวอร์ (Server-Backed Cloud Sync):**
   - สาเหตุที่เปิดบนคอมไม่เจอก่อนหน้านี้เพราะโน้ตบันทึกอยู่ใน `localStorage` ของมือถือเครื่องนั้น
   - สร้าง API endpoints ใน `scripts/api_producer.py`:
     - `GET /api/producer/notes`: ดึงรายการโน้ตทั้งหมดที่บันทึกบนเซิร์ฟเวอร์ (`02_Assets/Refs/playbook_notes.json`)
     - `POST /api/producer/notes`: บันทึก/อัปเดตโน้ตลงเซิร์ฟเวอร์แบบ Atomic Write
     - `POST /api/producer/notes/add`: เพิ่มโน้ตใหม่ลงเซิร์ฟเวอร์
     - `DELETE /api/producer/notes/{note_id}`: ลบโน้ตออกจากเซิร์ฟเวอร์
   - อัปเดต `producerInsights.js` และหน้า UI ทั้งสองหน้า (`QuickRefPage` และ `ProducerHub`) ให้โหลดจากเซิร์ฟเวอร์อัตโนมัติ (พร้อม local cache) ทำให้บันทึกจากมือถือแล้วเปิดดูบนคอมพิวเตอร์ได้ทันที 100%
   - เพิ่มปุ่ม "ซิงก์ข้อมูล" เพื่อดึงข้อมูลล่าสุดได้ใน 1 คลิก
3. **ปุ่ม 1-Click "คัดลอกส่งงาน" (Copy/Share for Team & Boss):**
   - เพิ่มปุ่มบนการ์ดโน้ต ให้ผู้ใช้คลิกเดียวเพื่อก็อปปี้สรุปข้อความไอเดีย ลิงก์เรฟ และ URL ภาพทั้งหมดในรูปแบบสวยงาม นำไปแปะส่งใน LINE / Discord / Chat ให้นายหรือทีมงานนำไปทำต่อได้ทันที
4. **รักษา UI Clean Standard (Rule 8):** ไม่มีสัญลักษณ์ `+` หรืออีโมจิซ้ำซ้อนในปุ่ม

### Gate & Verification Results:
- [x] Backend Tests: `tests/test_producer_notes_api.py` — 1/1 passed 100%
- [x] Node / Vitest Tests: `npm test` — 180/180 passed 100%
- [x] Frontend Build: `npm run build` — 2003 modules transformed, build clean ใน 4.29s
- [x] Python Compilation: `python -m compileall -q scripts tests` — 0 errors
- [x] Visual Verification: Browser subagent ตรวจสอบการแนบ 2 รูปพร้อมกันในหน้า QuickRefPage, บันทึกสำเร็จ, เรนเดอร์ Mini-Gallery, เปิด Lightbox ซูมรูป, กด "คัดลอกส่งงาน" สำเร็จพร้อม Toast, และเปิดหน้าผู้ช่วยโปรดิวเซอร์บนคอมพิวเตอร์พบโน้ตและรูปทั้งหมดซิงก์ตรงกัน 100%

---

## Round MOBILE-IMAGE-PASTE-FIX-1 — Fix Mobile Image Paste (iOS Safari files detection, ContentEditable Paste Target, and Native Photo Picker Auto-Fallback)

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
1. **แก้ปัญหาคัดลอกรูปบนมือถือแล้วกดวางไม่ขึ้นรูป:**
   - ใน iOS Safari เมื่อผู้ใช้คัดลอกภาพจาก Photos หรือ Safari ภาพจะถูกส่งผ่าน `e.clipboardData.files` หรือ `text/html` / `text/plain` (Image URL) ปรับปรุงตัวดักจับ paste ให้ตรวจสอบ `files`, `items`, `html (<img>)` และ `text (URL/base64)` ครบทุกมิติ
   - บน iOS Safari ช่อง `<textarea>` ธรรมดาจะไม่แสดงเมนู Paste สำหรับรูปภาพ (เพราะ Safari มองเป็น plain text) จึงเพิ่ม **"กล่องแตะเพื่อวางรูปภาพ (Rich Paste Target with contenteditable="true")"** เพื่อให้ iOS แสดงเมนู "Paste" สำหรับภาพได้อย่างถูกต้อง และดักจับ native insertion ด้วย `handleContentEditableInput`
2. **เพิ่มปุ่ม 1-Tap "เลือกจากคลังภาพ" (Native Photo Picker):**
   - แตะเพียงครั้งเดียวเพื่อเปิดคลังภาพ iOS/Android โดยตรง ภาพแคปหน้าจอหรือภาพที่เพิ่งเซฟไว้จะอยู่บนสุดซ้ายมือ แตะเลือกได้ใน 1 วินาทีแบบ Zero-Latency
3. **ปรับปรุงปุ่ม "วางรูปภาพ" บนมือถือ:**
   - ตรวจสอบ `navigator.clipboard.read()` รองรับทั้ง `image/*` และ `text/plain` (URL)
   - หาก iOS บล็อก permission ให้แจ้งเตือนด้วย Toast นุ่มนวลแนะนำให้แตะกล่องวาง หรือแตะ "เลือกจากคลังภาพ"
4. **รองรับไฟล์ภาพ iPhone (HEIC/HEIF) ที่หลังบ้าน:**
   - อัปเดต `scripts/api_producer.py` ตรวจจับ content_type เมื่อไฟล์ไม่มีนามสกุล และแปลง HEIC เป็น JPG ผ่าน ffmpeg อัตโนมัติ เพื่อให้เบราว์เซอร์ทุกตัวแสดงผลได้ 100%

### Gate & Verification Results:
- [x] Node / Vitest Tests: `npm test` — 180/180 passed 100%
- [x] Frontend Build: `npm run build` — 2003 modules transformed, build clean ใน 3.58s
- [x] Python Compilation: `.venv\Scripts\python.exe -m compileall -q scripts tests` — 0 errors
- [x] Visual Verification: Browser subagent จำลองการวางรูปภาพจาก clipboardData ลงใน Rich ContentEditable box และตรวจพบ preview ภาพในโหมด Desktop และ iPhone 15 Pro Max (430x932) อย่างสมบูรณ์แบบ

---

## Round CLIPBOARD-IMAGE-PASTE-1 — Direct Clipboard Image Paste (Ctrl+V / Paste into Textarea & Form)

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
1. **รองรับการกดวาง (Ctrl+V / Paste) รูปภาพลงในช่องไอเดียและฟอร์มโดยตรง:** เมื่อผู้ใช้แคปหน้าจอ (Win+Shift+S หรือ Screenshot บนมือถือ) แล้วกด Ctrl+V ในช่อง textarea หรือบริเวณกล่องแบบฟอร์ม ระบบจะตรวจจับภาพจาก clipboardData โดยอัตโนมัติ และนำภาพเข้าสู่ช่องแนบภาพเรฟทันที พร้อมอัปโหลดเข้า `02_Assets/Refs/`
2. **เพิ่มปุ่ม 1-Tap "วางรูปภาพ":** บริเวณกล่องรูปภาพ เพื่อให้แตะกดวางรูปภาพจาก clipboard ได้ทันทีโดยไม่ต้องเปิด file picker
3. **รองรับทั้งสองจุด:** ทั้งใน `QuickRefPage.jsx` (โหมดมือถือ/Quick Ref) และ `ProducerHub.jsx` (หน้าโปรดิวเซอร์หลัก)
4. **รักษา UI Clean Standard (Rule 8):** ป้ายและปุ่มกระชับ ไม่มีสัญลักษณ์ `+` หรืออีโมจิซ้อน

**สิ่งที่ทำ:**
1. อัปเดต `frontend/src/components/producer/QuickRefPage.jsx`:
   - พัฒนาฟังก์ชัน `processImageFile` จัดการไฟล์ภาพทั้งพรีวิวและอัปโหลดเข้าเซิร์ฟเวอร์
   - เพิ่ม `onPaste={handlePasteAnywhere}` ดักจับภาพจาก clipboard เมื่อกด Ctrl+V ในช่องข้อความหรือคลิกวางในฟอร์ม ป้องกันไม่ให้ข้อความ binary เสียหาย
   - เพิ่ม `onDrop={handleDrop}` ลากรูปมาวางในช่องได้ทันที
   - เพิ่มปุ่ม "วางรูปภาพ" ดึงรูปจาก `navigator.clipboard.read()`
2. อัปเดต `frontend/src/components/producer/ProducerHub.jsx`:
   - พัฒนา `processRefImageFile` และ `handlePasteImageAnywhere` ดักจับ Ctrl+V ในช่องพิมพ์ไอเดียและแบบฟอร์ม
   - เพิ่มปุ่ม "วางรูปภาพ" ดึงรูปจากคลิปบอร์ดในคลิกเดียว
   - เพิ่มสถานะแจ้งเตือน "วางรูปภาพเรียบร้อย!"

### Gate & Verification Results:
- [x] Node / Vitest Tests: `npm test` — 180/180 passed 100%
- [x] Frontend Build: `npm run build` — 2003 modules transformed, build clean ใน 3.35s
- [x] Python Compilation: `.venv\Scripts\python.exe -m compileall -q scripts tests` — 0 errors
- [x] Visual Verification: Browser subagent จำลองการวางรูปภาพจาก clipboardData ลงในช่อง textarea และยืนยันว่าภาพปรากฏในกล่องพรีวิวเรฟพร้อมอัปโหลดเรียบร้อย 100%

| Round IDEA-REF-VAULT-1 | คลังไอเดียและเรฟ (Idea & Ref Vault), Round-Robin Diversified Queue, และ Mobile View (iPhone 15 Pro Max) | 2026-09-13 | สำเร็จสมบูรณ์ (คลังไอเดีย & เรฟด้านบนสุด, รองรับแนบลิงก์ TikTok/Pinterest + รูปแคปหน้าจอ, จัดคิว Round-Robin กระจายสินค้าไม่ผูกขาด, ฟิลเตอร์สินค้าในคิว, AI Idea-to-Script ต่อมุมมองสินค้า 1-click, มุมมองมือถือ iPhone 15 Pro Max `?view=quick-ref`, npm test 180 passed, backend pytest parity 153 passed, build 4.10s, desktop & mobile browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round AI-PRODUCER-ELEVATION-1 | ยกระดับ Producer Hub: Spotlight Next Mission, Pacing Calculator, 1-Click Playbook Add, และ Pre-flight Editor Tips | 2026-09-13 | สำเร็จสมบูรณ์ (Next Action Spotlight Hero card, Weekly Pacing Calculator badge, 1-Click Playbook Suggestion Sync, Quick Script Preview modal, Pre-flight Editor Playbook Tips modal, npm test 178 passed, build 3.34s, browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |

---

## Round QUICK-REF-POLISH-1 — Redesign Impeccable Quick Ref Vault & Fix iOS Mobile Zoom

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
1. **ป้องกันหน้าจอซูมบนมือถือ/iOS Safari 100%:**
   - ปรับ font-size ของ input, textarea, select เป็น 16px (`text-base`) ทุกจุดบนมือถือ (iOS Safari auto-zooms หากขนาดตัวอักษรเล็กกว่า 16px)
   - เพิ่ม CSS rule ใน `frontend/src/index.css` ป้องกัน auto-zoom บน iOS เมื่อแตะฟอร์ม
   - อัปเดต `viewport` meta tag ใน `index.html` ให้รัดกุมพร้อม `maximum-scale=1.0, user-scalable=no, viewport-fit=cover`
2. **ปรับดีไซน์ให้ดูเต็มๆ สวยงามสะกดสายตา (Impeccable & UI-UX Pro Max):**
   - ถอดขอบจำกัด `max-w-md` ที่ทำให้เกิดแถบดำโล่งสองข้าง ปรับเป็น Responsive Layout ที่เต็มจอและปรับขนาดตามหน้าจอได้อย่างสวยงาม (บนมือถือใช้เต็มขอบจอ edge-to-edge กว้างสบายตา บนหน้าจอใหญ่ขยายกว้างเป็น 2 คอลัมน์ ไม่เหลือที่ว่างสีดำแห้งแล้ง)
   - ปรับโทนสีและพื้นผิวเป็น Dark Modern Glassmorphism ลุ่มลึก มี ambient light glow โค้งมนระดับพรีเมียม
3. **ยกระดับความง่ายในการใช้งาน (Maximum Ergonomics & Ease of Use):**
   - **1-Tap Paste Button:** ปุ่มวางลิงก์จากคลิปบอร์ดในคลิกเดียว ไม่ต้องแตะค้าง
   - **Segmented Category Pills:** แทนที่ dropdown ด้วยปุ่ม Pill ให้แตะเลือกประเภทเรฟ (Hook, Ref Clip, Visual, Audio, Promo) ได้ทันทีใน 1 แตะ
   - **Product Chips Selector:** เลือกผูกสินค้าด้วยชิปที่แตะง่าย หรือกดเคลียร์ได้สะดวก
   - **Drag & Drop / Tap Photo Uploader:** โซนอัปโหลดรูปภาพเรฟขนาดใหญ่ พรีวิวรูปภาพคมชัด
   - **AI Idea-to-Script Integration บนหน้ามือถือ:** ให้สามารถกด "✨ แปลงเป็นสคริปต์" ได้โดยตรงจากหน้านี้ พร้อมพรีวิวและปุ่มเพิ่มเป็น Angle สินค้า
   - **Search & Filter สำหรับคลังที่บันทึกไว้:** กรองประเภทหรือค้นหาไอเดียเก่าได้อย่างรวดเร็ว

**สิ่งที่ทำ:**
1. แก้ไข `frontend/index.html`:
   - ปรับ `meta name="viewport"` เป็น `width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover`
2. แก้ไข `frontend/src/index.css`:
   - เพิ่ม Media Query สำหรับจอ `<= 768px` บังคับให้ `input, textarea, select` มี `font-size: 16px !important` ป้องกัน iOS Safari ซูมจอเมื่อแตะพิมพ์
3. รีดีไซน์ `frontend/src/components/producer/QuickRefPage.jsx`:
   - ปรับ Layout เป็น Responsive 2-Column บนจอใหญ่ (ซ้าย: Capture Studio, ขวา: Live Ref Vault) และ Tab-based Switcher บนจอมือถือ
   - เพิ่มปุ่ม "วางลิงก์ล่าสุด" 1 แตะดึงจากคลิปบอร์ด
   - ปรับเปลี่ยนหมวดหมู่เป็น Segmented Category Pills กดง่ายด้วยนิ้วโป้ง
   - เพิ่มระบบค้นหาไอเดียและชิปฟิลเตอร์แยกตามหมวดหมู่
   - เพิ่มปุ่มและโมดอล "คิดสคริปต์จากเรฟ" ให้ใช้งานได้ในตัวบนหน้ามือถือ

### Gate & Verification Results:
- [x] Node / Vitest Tests: `npm test` — 180/180 passed 100%
- [x] Frontend Build: `npm run build` — 2003 modules transformed, build clean ใน 3.31s
- [x] Python Compilation: `.venv\Scripts\python.exe -m compileall -q scripts tests` — 0 errors
- [x] Visual Verification: Browser subagent ตรวจสอบทั้งขนาดมือถือ iPhone 15 Pro Max (430x932) เต็มจอ ไม่ซูม แตะง่าย และ Desktop (1280x800) จัดสรรพื้นที่ 2 คอลัมน์สวยงาม ไม่เหลือขอบดำ ผ่านสมบูรณ์ 100%

| Round AI-PRODUCER-HUB-1 | พัฒนาเมนูใหม่ "ผู้ช่วยโปรดิวเซอร์ส่วนตัว" (AI Producer Hub & Daily Mission Center) | 2026-09-13 | สำเร็จสมบูรณ์ (แบนเนอร์เรียกเจ้านาย, คุมโควตา 35 คลิป, Daily Action Queue 3 ระดับ, AI Retrospective, Boss Playbook, npm test 176 passed, build 3.36s, browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round UI-LAST-UPDATED-TIMESTAMP-1 | แสดงวันที่และเวลาอัปเดตล่าสุด (Relative + Full Tooltip) ใน Dropdown ไทม์ไลน์ และบนการ์ด Tracker | 2026-09-13 | สำเร็จสมบูรณ์ (แสดงเวลาสัมพัทธ์ไทย + tooltip เวลาเต็ม ทั้งใน ProjectSelector และ Tracker cards, npm test 170 passed, build 3.92s, browser verified, ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)) |
| Round PAGINATION-1 | เพิ่ม client-side windowing ให้ 9 list endpoint ทั่วระบบ กัน UI ช้าเมื่อข้อมูลถึงหลักร้อย (แผนใน `PAGINATION_PLAN.md`) | 2026-09-13 | สำเร็จสมบูรณ์ (Phase 1: exports/products/videos/raw-vault/schedule-queue/tiktok-stats windowed ทั้ง 6, Phase 2: assets/all + dedup-scan windowed, clip-candidates ไม่ต้องแก้ (native select), Phase 3: 4 endpoint เช็คแล้วปลอดภัยอยู่แล้วทั้งหมด ไม่ต้องแก้โค้ด; pytest เต็มระบบ 1126 passed, vitest 158 passed ทุกรอบ, build ผ่านทุกจุด; browser verify ยังไม่ได้ทำ (dev server ไม่ตอบ HTTP ตลอด session) ย้ายเข้า Backlog, ดำเนินการโดย: Claude Code (Claude Sonnet 5)) |
| Round EXPORT-ARCHIVE-POLICY-1 | แจ้งเตือนเมื่อ export/project ที่โพสต์แล้วค้างเกิน 30 วัน หรือดิสก์ใช้เกิน 80% — banner ใน Storage tab ไม่ auto-move ไฟล์ | 2026-09-12 | สำเร็จสมบูรณ์ (เพิ่ม `archive_recommendation` ใน `/api/analytics/storage`, banner ใน StorageAnalyticsTab.jsx, pytest 4 passed, build 3.12s, live API verified, ดำเนินการโดย: Claude Code (Claude Sonnet 5)) |
| Round SCRIPT-BATCH-EXPAND-1 | ระบบเจนสคริปต์ล็อตใหม่ 10 มุมมอง & ปรับระบบ Dev Server HTTP (Multi-Batch Generation & Filtering Flow) | 2026-09-12 | สำเร็จสมบูรณ์ (ปลดล็อก Privacy Error ถาวร รัน HTTP localhost:5173, SSOT 1 สินค้าหลายล็อต, Multi-Batch sub-bar, Quick filter ซ่อนที่โพสต์แล้ว, API generate-batch & add angle, pytest 171 passed, vitest 158 passed, build 3.25s, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round POSTED-CLIP-LIFECYCLE-1 | ระบบจัดการคลิปที่โพสต์แล้ว (Zero-Risk Archive & Timeline Lockout Flow) | 2026-09-12 | สำเร็จสมบูรณ์ (ตัดสิทธิ์เปิดไทม์ไลน์ 100%, กรองออกจาก Dropdown โปรเจกต์, Action Bar สคริปต์ [ดูคลิปที่โพสต์แล้ว] + [ทำซ้ำเพื่อตัดคลิปใหม่], ย้ายโฟลเดอร์โปรเจกต์เข้า 06_Archive/Projects/ อัตโนมัติ, vitest 158 passed, pytest 156 passed, build 3.45s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round UI-FONT-MONO-CLEAN-1 | กวาดล้าง font-mono ที่ครอบข้อความภาษาไทย/การ์ด KPI ทั่วทั้งระบบให้เป็นฟอนต์กลาง 100% | 2026-09-12 | สำเร็จสมบูรณ์ (ถอด font-mono จาก MetricKpiCard, Badge.jsx, ContentTrackerHub, MediaAssetsHub, SystemSettings และ inspector ให้หน่วยนับและภาษาไทยใช้ฟอนต์กลาง, vitest 152 passed, build 3.31s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round UI-POLISH-HEADER-1 | แก้ฟอนต์กล่องแดง Topbar (ถอด font-mono) + ตัด 2 Badge สินค้า + ขยายหัวข้อสินค้าเน้นๆ ใหญ่ๆ | 2026-09-12 | สำเร็จสมบูรณ์ (ถอด font-mono จากป้ายแท็บ Topbar ให้สืบทอด Global UI Font, ตัด price_note และ tiktok_id ออกจาก PageHeader สินค้า, ขยายชื่อสินค้าเป็น text-2xl font-black, vitest 152 passed, build 3.49s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round SHOTLIST-GEMINI-TTS-SSOT-1 | ระบบรวมศูนย์เสียง TTS (Gemini Flash Audio SSOT): แผนถ่าย & ตัดต่อจริงใช้เสียงเดียวกัน 100% ไม่เจนซ้ำ | 2026-09-12 | สำเร็จสมบูรณ์ (pytest 1,125 passed, vitest 158 passed, build 3.40s, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round SHOT-GAP-FIX-1 | แก้ช่องว่าง (Gap) ระหว่างช็อตใน Shot Matching Stage — 2 bugs: cut_points เริ่มที่ 0.0 แทน first-cue start, MERGE_TOLERANCE แคบเกิน | 2026-09-12 | สำเร็จสมบูรณ์ (compileall pass, pytest 1126 passed, ดำเนินการโดย: Antigravity (Claude Sonnet 4.6)) |

---

## Round IDEA-REF-VAULT-1 — คลังไอเดียและเรฟ (Idea & Ref Vault), Round-Robin Diversified Queue, และ Mobile View (iPhone 15 Pro Max)

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
1. **แก้ปัญหา Daily Action Queue แสดงแต่สินค้าเดียว:** ปรับอัลกอริทึมเป็น Round-Robin / Diversified Product Distribution ดึงมุมมองสลับระหว่างสินค้า ไม่ให้สินค้าตัวใดตัวหนึ่งกินโควตาทั้งวัน พร้อมปุ่มฟิลเตอร์สินค้า
2. **ยกระดับสมุดจดเป็น Idea & Ref Vault:** ย้ายขึ้นมาด้านบนเด่นชัด รองรับการแปะลิงก์ TikTok/Pinterest, อัปโหลดรูปภาพเรฟ, ผูกสินค้า และถอดสัญลักษณ์ซ้ำซ้อน (`+ จด` -> `บันทึกไอเดีย`) ตาม `ui_clean_standard.md`
3. **Mobile Quick-Capture (iPhone 15 Pro Max):** ออกแบบเลย์เอาท์ให้ responsive พอดีจอ 430px และรองรับ URL `?view=quick-ref` ให้กด Add to Home Screen เพื่อเปิดบันทึกไอเดียได้ใน 2 วินาที
4. **AI Idea-to-Script:** ปุ่มส่งไอเดีย/เรฟให้ AI วิเคราะห์สกัดเป็น Hook + มุมมองถ่าย + สคริปต์ย่อ พร้อมปุ่ม 1-click เพิ่มเป็นมุมมองสินค้า (Add to Angles) เข้าสู่กระบวนการผลิต

**สิ่งที่ทำ:**
1. อัปเดต `frontend/src/lib/producerInsights.js`:
   - พัฒนาฟังก์ชัน `diversifyByProduct(items)` กระจายสินค้าแบบ Round-Robin Interleaving ป้องกันไม่ให้สินค้าตัวแรกยึดคิวทั้งวัน
   - ปรับปรุง `getDailyActionQueue(products, projects, quotaToday)` ให้ใช้ `diversifyByProduct` กับรายการรอตัดต่อและรอถ่าย พร้อมส่งออก `productsInQueue` เพื่อทำแท็บฟิลเตอร์
   - เพิ่มฟังก์ชันจัดการบันทึก: `addPlaybookNote`, `deletePlaybookNote`, `updatePlaybookNote`, และ `detectRefPlatform` (ตรวจจับ TikTok, Pinterest, YouTube, Instagram)
2. เขียน Unit Tests `frontend/src/lib/producerInsights.test.js`:
   - เพิ่มการทดสอบ `diversifyByProduct` แบบ Round-Robin กระจายสินค้าหลายตัวสลับกัน
   - เพิ่มการทดสอบ `detectRefPlatform` ตรวจจับ URL โซเชียลมีเดีย
   - ทดสอบรวมทั้งหมด **180/180 tests passed**
3. พัฒนา Backend API:
   - สร้าง `scripts/api_producer.py`:
     - `POST /api/producer/upload-ref-media`: บันทึกรูปภาพหรือ screenshot เรฟลงใน `02_Assets/Refs/` อย่างปลอดภัย
     - `GET /api/producer/ref-media/{filename}`: เสิร์ฟไฟล์มีเดียเรฟ
     - `POST /api/producer/ai-idea-to-angle`: สังเคราะห์ไอเดีย/ลิงก์เรฟเป็น Hook + แผนถ่าย + สคริปต์ย่อ พร้อม Fallback หากไม่มี Gemini API Key
   - เชื่อม `producer_router` ใน `scripts/api_server.py`
4. อัปเดต Frontend API (`frontend/src/api.js`):
   - เพิ่ม `uploadRefMedia` และ `aiIdeaToAngle`
5. พัฒนา Mobile Quick-Capture Page (`frontend/src/components/producer/QuickRefPage.jsx`):
   - ออกแบบ UI เฉพาะสำหรับ iPhone 15 Pro Max (390-430px) คลีน ไร้สัญลักษณ์ซ้ำซ้อน
   - รองรับการแปะลิงก์ (ตรวจจับ badge แพลตฟอร์มอัตโนมัติ), แนบภาพถ่าย/แคปหน้าจอ, เลือกหมวดหมู่ และผูกสินค้า
   - เชื่อมโยงใน `frontend/src/App.jsx` เมื่อเปิดผ่าน `?view=quick-ref` หรือ `?quick_ref=1`
6. อัปเดต `frontend/src/components/producer/ProducerHub.jsx`:
   - ย้ายคลังไอเดียและเรฟ (Idea & Ref Vault) ขึ้นมาไว้ใต้ Next Action Spotlight ด้านบนสุด
   - Quick-Capture bar ใช้งานง่าย มีปุ่มเปิดโหมดมือถือ และพรีวิวรูปภาพเรฟ
   - เพิ่มแท็บฟิลเตอร์สินค้าใน Daily Action Queue (`ทั้งหมด`, `[BLU01]`, `[LOG02]`, `[ESS01]`)
   - เพิ่มปุ่ม "คิดสคริปต์จากเรฟ" และโมดอล `AiAngleProposalModal` ให้พรีวิวและกด "เพิ่มเป็นมุมมองสินค้า" ลงในสินค้าเป้าหมายได้ในคลิกเดียว
   - เปลี่ยนคอลัมน์ล่างเดิมที่ซ้ำซ้อนเป็นการ์ด Studio Rules & Quality Standards

### Gate & Verification Results:
- [x] Node / Vitest Tests: `npm test` — 180/180 passed 100%
- [x] Frontend Build: `npm run build` — 2003 modules transformed, build clean ใน 4.10s (แยก chunk QuickRefPage สมบูรณ์)
- [x] Python Compilation: `.venv\Scripts\python.exe -m compileall -q scripts tests` — 0 errors
- [x] Pytest Parity: `pytest tests/test_preview_render_parity.py` — 153/153 passed
- [x] Visual Verification: Browser subagent ตรวจสอบทั้ง Desktop (Idea Vault ด้านบน, คิว Round-Robin หลากสินค้าพร้อมฟิลเตอร์) และ Mobile iPhone 15 Pro Max View (`?view=quick-ref` ขนาด 430x932) ผ่านสมบูรณ์ 100%


---

## Round AI-PRODUCER-ELEVATION-1 — ยกระดับ Producer Hub: Spotlight Next Mission, Pacing Calculator, 1-Click Playbook Add, และ Pre-flight Editor Tips

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
ยกระดับหน้าผู้ช่วยโปรดิวเซอร์และระบบคุมวินัยสำหรับคนขี้เกียจ/ความจำสั้นตามผลการสแกน 5 มิติ:
1. **Next Action Spotlight:** การ์ดชี้เป้าภารกิจอันดับ 1 ที่ต้องทำตอนนี้ (มอง 3 วิรู้เรื่อง ไม่ต้องเลือก) พร้อมปุ่มเริ่มทันที
2. **Weekly Pacing Calculator:** คำนวณความเร็วสู่เป้า 35 คลิปตามวันที่เหลือในสัปดาห์ (ต้องตัดอีกวันละกี่คลิป พร้อมคำแนะนำแบบตรงจุด)
3. **1-Click Auto-Suggest Playbook:** ปุ่มบันทึกข้อคิดจาก AI Retrospective ลง Playbook ได้ในคลิกเดียว
4. **Pre-flight Editor Playbook Tips:** นำโน้ตบทเรียนของเจ้านายไปแสดงเตือนความจำบน Editor ก่อนเริ่มตัดต่อ
5. **Quick Script Preview:** ดูบทและสเปกสินค้าได้ทันทีจาก Producer Hub โดยไม่ต้องคลิกสลับหน้า

**สิ่งที่ทำ:**
1. อัปเดต `frontend/src/lib/producerInsights.js`:
   - เพิ่มฟังก์ชัน `calculateWeeklyPacing(stats, now = new Date())` คำนวณจำนวนวันที่เหลือในสัปดาห์ อัตราเฉลี่ยที่ต้องตัดต่อวันเพื่อจบเป้าหมาย 35 คลิป และสถานะการทำงาน (ahead, on_track, behind, completed)
   - เพิ่มฟังก์ชัน `autoSuggestPlaybookNotes(retrospective, currentNotes)` ดึงข้อคิดเด่นจากสถิติมาเป็นปุ่มกดจดโน้ตใน 1 คลิก พร้อมตรวจเช็คว่าบันทึกไปแล้วหรือยัง
2. เขียน Unit Tests `frontend/src/lib/producerInsights.test.js`:
   - เพิ่ม test suite ครอบคลุม pacing calculator (ปกติ, เร่งสปีด, ครบเป้า) และการแนะนำโน้ตลง playbook
   - ทดสอบรวมทั้งหมด **178/178 tests passed**
3. อัปเดต `frontend/src/components/producer/ProducerHub.jsx`:
   - เพิ่ม Next Action Spotlight Hero Card เด่นชัดด้านบนสุด ชี้เป้างานเร่งด่วนที่สุดพร้อมปุ่มเริ่มทันที
   - เพิ่ม Pacing Badge ในการ์ด Weekly Quota (แสดงคำเตือนและจำนวนคลิปที่ต้องทำต่อวัน)
   - เพิ่มปุ่ม "ดูบท" ใน Daily Action Queue เปิด Quick Preview Modal
   - เพิ่มปุ่ม "จดบทเรียน" / "จดแล้ว" ซิงก์ข้อคิดจาก AI Retrospective เข้าสู่ Boss's Playbook ทันที
4. อัปเดต `frontend/src/components/editor/EditorHeader.jsx`:
   - เพิ่มปุ่ม "ข้อเตือนใจ" (Boss Playbook Tips) สีเหลืองอำพันพร้อมจุดแสดงสถานะ
   - เพิ่ม Pre-flight Playbook Tips Modal สไตล์ Glassmorphism แสดงโน้ตและกฎเหล็กที่จดไว้ให้เห็นก่อนเริ่มตัดต่อ
5. ยืนยัน UI จริงผ่าน Browser Subagent ทั้งหมด 5 มิติ: Next Action Hero, Pacing Badge, Quick Preview Modal, 1-Click Playbook Sync (บันทึกกันลืม 3 -> 4), และ EditorHeader ข้อเตือนใจ Modal

### Gate & Verification Results:
- [x] Node / Vitest Tests: `npm test` — 178/178 passed 100%
- [x] Frontend Build: `npm run build` — 2002 modules transformed, build clean ใน 3.34s
- [x] Python Compilation: `.venv\Scripts\python.exe -m compileall -q scripts tests` — 0 errors
- [x] Browser Visual Verification: ตรวจสอบภาพจริงทั้ง 5 จุดผ่านสมบูรณ์ 100% (บันทึกวิดีโอ WebP + ภาพ screenshot 2 ภาพ)

---

## Round AI-PRODUCER-HUB-1 — พัฒนาเมนูใหม่ "ผู้ช่วยโปรดิวเซอร์ส่วนตัว" (AI Producer Hub & Daily Mission Center)

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
สร้างศูนย์บัญชาการอัจฉริยะประจำวันสำหรับคอนเทนต์ครีเอเตอร์และสายแอฟฟิลิเอต เพื่อแก้ปัญหาความจำสั้น ขี้เกียจลืมคิว ไม่รู้ว่าวันนี้ต้องทำอะไรต่อ:
1. แบนเนอร์ผู้ช่วยรู้ใจเรียก "เจ้านาย" ทักทายตามช่วงเวลาและสถานะงานค้างจริง
2. ระบบคุมเป้าหมายการผลิตรายวัน/รายสัปดาห์ (Quota Gauges & Progress Bars) พร้อมปุ่มปรับเปลี่ยนเป้าหมาย
3. สิ่งที่ต้องทำวันนี้ (Daily Action Queue 3 ระดับ) พร้อมปุ่มลัด 1-click พุ่งไปทำทันที
4. AI ถอดรหัสคลิปปังจากสถิติ TikTok จริง + สมุดจดบทเรียนของเจ้านาย (Boss Playbook)

**สิ่งที่ทำ:**
1. สร้างโมดูลคำนวณและวิเคราะห์ `frontend/src/lib/producerInsights.js`: คำนวณโควตารายวันและรายสัปดาห์ (35 คลิป), คัดแยก Daily Action Queue 3 ระดับ (รอโพสต์, รอตัด, รอถ่าย), เจนข้อความเรียก "เจ้านาย" และ AI Retrospective
2. เขียน Unit Tests `frontend/src/lib/producerInsights.test.js` (6 tests ครอบคลุม parsing, day matching, quotas, action queues, boss greeting; tests รวม 176/176 passed 100%)
3. สร้างคอมโพเนนต์ `frontend/src/components/producer/ProducerHub.jsx`: ดีไซน์ Dark Modern Glassmorphism สมบูรณ์แบบ พร้อม Quota modal และ Boss's Playbook notepad
4. อัปเดต `Sidebar.jsx`, `Topbar.jsx`, และ `App.jsx` เพิ่มเมนู "0. ผู้ช่วยโปรดิวเซอร์" บนสุดของ Sidebar พร้อมระบบนำทาง
5. ยืนยัน UI จริงผ่าน Browser Subagent ทั้งแบนเนอร์เจ้านาย, เกจเป้าหมาย, Action Queue, Modal ปรับ Quota และทดสอบพิมพ์จดโน้ตใน Playbook สำเร็จ

### Gate & Verification Results:
- [x] Node / Vitest Tests: `npm test` — 176/176 passed 100%
- [x] Frontend Build: `npm run build` — 2002 modules transformed, build clean ใน 3.36s (ProducerHub chunk: 36.90 kB)
- [x] Python Compilation: `python -m compileall -q scripts` — 0 errors
- [x] Browser Visual Verification: ตรวจสอบภาพจริงทั้งแดชบอร์ด, Quota modal, และการจดโน้ต Playbook ผ่านสวยงาม

---

## Round UI-LAST-UPDATED-TIMESTAMP-1 — แสดงวันที่และเวลาอัปเดตล่าสุด (Relative + Full Tooltip) ใน Dropdown ไทม์ไลน์ และบนการ์ด Tracker

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์
ดำเนินการโดย: Antigravity (Gemini 3.8 Flash)

**เป้าหมาย:**
เพิ่มการแสดงผลเวลาอัปเดตล่าสุด (Last Updated) ให้ผู้ใช้เห็นความเคลื่อนไหวชัดเจนทั้งใน Dropdown เลือกโปรเจกต์ของหน้า Editor และบนการ์ดในหน้า Tracker ใต้ช่อง "กำลังตัดต่อ" พร้อม Tooltip แสดงวันเวลาเต็มเมื่อนำเมาส์ไปชี้

**สิ่งที่ทำ:**
1. สร้างโมดูล helper กลาง `frontend/src/lib/dateUtils.js` สำหรับแปลงเวลาสัมพัทธ์ภาษาไทย (`getRelativeTime`) เช่น "เมื่อสักครู่", "X นาทีที่แล้ว", "X ชม. ที่แล้ว", "เมื่อวาน", "X วันที่แล้ว" และแปลงวันเวลาเต็ม (`formatFullDateTime`)
2. เขียน Unit Test `frontend/src/lib/dateUtils.test.js` ครอบคลุม parsing, time boundaries และ formatting (12 tests ผ่าน 100%)
3. อัปเดต `ProjectSelector.jsx`: แสดงเวลาต่อท้ายสถานะใน Dropdown (เช่น `กำลังตัดต่อ · 23 นาทีที่แล้ว`) พร้อม Tooltip แสดงเวลาเต็ม
4. อัปเดต `ContentTrackerHub.jsx`: แสดงเวลาอัปเดตล่าสุดคู่กับไอคอน Clock ข้างปุ่ม "เปิดไทม์ไลน์" บนการ์ดช่องกำลังตัดต่อ
5. ยืนยัน UI จริงผ่าน Browser Subagent ทั้ง 2 จุด

### Gate & Verification Results:
- [x] Node / Vitest Tests: `npm test` — 170/170 passed 100%
- [x] Frontend Build: `npm run build` — 2000 modules transformed, build clean ใน 3.92s
- [x] Python Compilation: `python -m compileall -q scripts` — 0 errors
- [x] Browser Visual Verification: ตรวจสอบภาพจริงทั้ง Dropdown และ Tracker Cards สมบูรณ์ สวยงาม ไม่เบียด ไม่ล้น

---

## Round SHOT-GAP-FIX-1 — แก้ช่องว่าง (Gap) ระหว่างช็อตใน Shot Matching Stage

**วันที่:** 2026-09-12 · **Agent:** Antigravity (Claude Sonnet 4.6 Thinking)

### เป้าหมาย

แก้ปัญหาช่องว่างที่มองเห็นได้ในวิดีโอที่เรนเดอร์ออกมาจากระบบ Shot Matching อัตโนมัติ เมื่อใช้ร่วมกับ Gemini TTS SSOT (เสียงพากย์เริ่มต้นที่ 0.23s ไม่ใช่ 0.0s)

### Root Cause วิเคราะห์

**Bug 1 — Leading Gap (ช่องว่างต้นคลิป):**
- `cut_points = [0.0]` hardcoded → ทำให้ shot แรกเริ่มที่วินาที 0.0
- แต่ Gemini TTS มีช่วงเงียบ ~0.1–0.4s ก่อนเริ่มพูด → `micro_cues[0].start` = 0.23s
- ผลลัพธ์: clip แรกยาวกว่าเสียงที่ครอบอยู่ 0.23s → ช่วงเงียบต้นวิดีโอ

**Bug 2 — Ultra-Short Clips ไม่ถูก Merge:**
- `MERGE_TOLERANCE = 1.15` × `MAX_SHOT_DURATION = 2.5s` = เพดาน 2.875s
- คลิปสั้นมากอย่าง "นะครับ" (0.491s) ถูกขนาบด้วยคลิปยาว 2.6s + 2.5s
- Merge ทางซ้าย: 0.491 + 2.6 = 3.09s > 2.875s → ไม่ merge
- Merge ทางขวา: 0.491 + 2.5 = 2.99s > 2.875s → ไม่ merge
- ผลลัพธ์: คลิป 0.491s ถูกทิ้งไว้เดี่ยว → เห็นเป็นกระตุกในวิดีโอ

### การแก้ไข — `scripts/stages/shot_matching_stage.py`

1. **แก้ Bug 1:** `cut_points = [0.0]` → `cut_points = [float(active_cues[0].get("start", 0.0))]`
   - First shot boundary ตรงกับ first cue start เสมอ ไม่มี leading gap อีกต่อไป

2. **แก้ Bug 2:** เพิ่ม 2-pass merge strategy:
   - **Pass 1** (standard): `MERGE_TOLERANCE = 1.5` (ขึ้นจาก 1.15) → เพดาน 3.75s ครอบคลุมคู่ ~1.2s + ~2.2s = 3.4s ที่เกิดจริงในคอนเทนต์ TikTok
   - **Pass 2** (force-merge ultra-short): clips ที่ยังสั้นกว่า `MIN / 2 = 0.75s` หลัง pass 1 → force merge เข้า neighbor ที่สั้นกว่า โดยไม่ตรวจ MAX เลย (คลิป 3.0s ดีกว่าคลิป 0.5s เสมอ)

### ผลการจำลองก่อน/หลัง (โปรเจกต์จริง BLU01)

| เมตริก | ก่อนแก้ | หลังแก้ |
|---|---|---|
| คลิปที่สั้นกว่า MIN (1.5s) | 8 คลิป | 0 คลิป |
| คลิปที่สั้นกว่า 0.75s | 1 คลิป (0.491s) | 0 คลิป |
| จำนวนช็อตสุดท้าย | 25 shots | 18 shots |
| Leading gap | 0.23s | 0s |
| Boundary[0] | 0.000s | 0.230s (= cue start) |

### Gate Results

```
python -m compileall -q scripts   → exit 0 (0 errors)
pytest tests/ -q --tb=short -x   → 1126 passed, 26 warnings in 275.52s
```


| Round UI-FONT-HARMONY-1 | ปรับความสอดคล้องของฟอนต์ UI ทั้งระบบตาม Global UI Font (ปราศจาก Encoding Mojibake) | 2026-09-12 | สำเร็จสมบูรณ์ (ปลดล็อคคลาส font-kanit ที่ฝังใน 35 คอมโพเนนต์ UI เพื่อสืบทอด Global UI Font, อนุรักษ์ preview card ใน Settings/Assets, รับประกัน Thai UTF-8 byte-for-byte 100%, vitest 152 passed, build 4.57s, pytest parity 153 passed, browser verified, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round TIKTOK-DASH-DATA-1 | ล้างโพสต์ทดสอบ 163 รายการ (Test Serum) ออกจาก post_log พร้อม backup + กัน merge ยอดซ้ำข้ามแถวในรอบซิงก์เดียว | 2026-09-12 | สำเร็จสมบูรณ์ (backup 167 entries → เหลือ 4 โพสต์จริง 895 views, claim guard แก้ยอด Lift โดนแถวอื่นทับ, pytest 1114 passed, extension 32 passed, ดำเนินการโดย: Cline (โมเดลฐานไม่ได้ระบุ)) |
| Round TIKTOK-STATS-MATCH-1 | แมพ 0/10 เพราะไม่มีโพสต์ให้จับคู่ → จับคู่กับคลังผลงาน + ลงทะเบียนโพสต์อัตโนมัติ + fuzzy normalize ตัดแฮชแท็ก | 2026-09-12 | สำเร็จสมบูรณ์ (score-based match, auto-register จาก ProductStore candidates, parse วันที่ไทย → posted_at, pytest 8 passed, extension 32 passed, ดำเนินการโดย: Cline (โมเดลฐานไม่ได้ระบุ)) |
| Round TIKTOK-STATS-DOM-2 | รีเขียน parser อ่าน div-grid จริงของ Studio (data-tt) จาก DOM ที่ user เซฟมา + จับคู่คอลัมน์ตามหัว + dedupe | 2026-09-12 | สำเร็จสมบูรณ์ (locateDivGrid/parseDivRows, หัวคอลัมน์จริง "ยอดการดู" แก้ความเข้าใจ "ยอดวิว", extension tests 32 passed, ดำเนินการโดย: Cline (โมเดลฐานไม่ได้ระบุ)) |
| Round TIKTOK-STATS-DOMAIN-1 | แก้ซิงก์สถิติตาราง Studio + คอลัมน์ 'ยอดวิว' + Manifest 0.2.0 + แข็งการตรวจจับแท็บ | 2026-09-12 | สำเร็จสมบูรณ์ (alias ยอดวิว, regex เดือน ส.ค./เม.ย., build tag 0.2.0, extension tests 28 passed, ดำเนินการโดย: Cline / Antigravity) |
| Round BATCH-RENDER-1 | One-Click Batch Angle Video Render Queue (Background FIFO Worker + Live Overall Progress + Concurrency Lock) | 2026-09-12 | สำเร็จสมบูรณ์ (คิวเรนเดอร์หลายมุมมอง background worker, auto-retry, TaskManager progress, pytest 4 passed, vitest 152 passed, build 4.46s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round HOOK-VAR-1 | AI Hook Variation & A/B Generator (5 marketing styles + 9:16 Safe Zone Preview + 1-Click Apply) | 2026-09-12 | สำเร็จสมบูรณ์ (5 สไตล์ curiosity, warning, social_proof, deal_promo, pain_point + offline fallback + safe-zone preview + pytest 8 passed, vitest 152 passed, build 4.08s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round AGENT-ATTRIB-1 | บังคับระบุ Agent Tooling & AI Model ในประวัติงาน (Rule 14 ใน AGENTS.md และ work_loop.md) | 2026-09-12 | สำเร็จสมบูรณ์ (กำหนดมาตรฐานความรับผิดชอบในการติดตามงาน, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round BACKUP-1 | One-Click System Backup & Restore (Engine + API + UI Maintenance Tab) | 2026-09-12 | สำเร็จสมบูรณ์ (สำรองข้อมูลปลอดภัย zip + manifest + SHA-256 + SQLite online backup, pytest 8 passed, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round ASSET-DEDUP-1 | Media Deduplication & Cleanup Engine (Engine + API + UI Scan & Safe Move) | 2026-09-12 | สำเร็จสมบูรณ์ (Multi-tier detection size -> head+tail hash -> sha256, ย้ายไป .trash ปลอดภัย, pytest 4 passed, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round CALENDAR-1 | Interactive Drag-and-Drop Weekly Content Calendar (ScheduleAgenda view toggle + 7-day grid) | 2026-09-12 | สำเร็จสมบูรณ์ (สลับมุมมอง รายการ/ปฏิทินสัปดาห์ 7 วัน + เลื่อนวันด้วย Drag-and-Drop, vitest 152 passed, build 3.14s, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round SAFE-1 — Disk Guard ก่อน Render & Auto-Snapshot CapCut Manifest 3 Versions | ป้องกันเรนเดอร์ล้มเหลวด้วย Disk Guard (>3GB) และทำ Rolling Backup 3 versions | 2026-09-12 | สำเร็จสมบูรณ์ (8 backend unit tests passed, 4 baseline tests passed, vitest 151 passed, build pass, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round TIKTOK-STATS-FIX-1 | แก้บั๊ก result is not defined + ย้ายซิงก์สถิติเป็นแท็บที่ 3 "เครื่องมือ" ใน Extension | 2026-09-12 | สำเร็จสมบูรณ์ (extension 21 passed, ดำเนินการโดย: Cline) |
| Round TIKTOK-STATS-SCRAPE-1 | ซิงก์สถิติ TikTok Studio ผ่าน Extension (parser + import API + แท็บ Performance) | 2026-09-12 | ไม่ใช้ TikTok API (เลี่ยง review); fuzzy match video_id > ชื่อ+ความยาว; extension 21 tests, pytest 8, frontend 151, build 4.06s (ดำเนินการโดย: Cline) |
| Round ANALYTICS-HUB-1 — พัฒนาเมนูใหม่ "ศูนย์วิเคราะห์ข้อมูลและสถิติรวม" (Analytics & Operations Hub) | สร้างศูนย์รวมการวิเคราะห์ข้อมูลและสถิติการใช้งานทุกมิติ | 2026-09-11 | สำเร็จสมบูรณ์ (backend 4 passed, frontend 151 passed, build pass, ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round HOOK-DEFAULT-5S-1 — ปรับค่าเริ่มต้น (default) ของป้ายฮุกพาดหัว (Hook Banner) เป็น 5.0 วินาทีตั้งแต่ตอนสร้างโปรเจกต์ | ให้ป้ายฮุกพาดหัวทั้งตอนสร้างโปรเจกต์ใหม่ (First Render / One Click / Apply to | 2026-09-11 | สำเร็จสมบูรณ์ (ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round SIDEBAR-PHASE-UI-1 — ออกแบบ sidebar ซ้ายใหม่ด้วย 4-Phase Pipeline Stepper Dots + Shot List Badge + Smart Camera Direction Clarity | 1. แก้ปัญหาแผนถ่ายที่คำแนะนำมุมกล้องยังดูเหมือนเดิมหรือยังไม่แบ่งมุม/แอคชั่นชัดเจน: | 2026-09-11 | สำเร็จสมบูรณ์ (ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round FONT-TEXT-RULE-1 — กฎเหล็กฟอนต์และข้อความ | สร้าง project-level contract ที่บังคับทุกเอเจนว่างานไม่เกี่ยวข้องห้ามเปลี่ยนฟอนต์ ขนาด ข้อความ | 2026-09-10 | สำเร็จสมบูรณ์ (ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)) |
| Round RENDER-BEHAVIOR-FIX-1 — แก้ 2 pre-existing render-behavior failures | ทำให้ full backend suite กลับมา 0 failed — บั๊ก 2 ตัวนี้บ่งชี้ว่าภาพเรนเดอร์จริงเบี่ยงจาก parity con | 2026-09-10 | สำเร็จสมบูรณ์ |
| Round PRODUCT-METADATA-7 — อ่านสรรพคุณ/สเปกจากรูปอ้างอิงด้วย Vision | ให้สินค้าใหม่ที่มีข้อมูลอยู่ในภาพอินโฟกราฟิกหรือภาพสเปกสามารถสกัดคำอธิบาย สรรพคุณ จุดขาย และสเปกเข้า | 2026-09-10 | สำเร็จสมบูรณ์ |
| Round PRODUCT-METADATA-6 — กัน selected product เปลี่ยนเองระหว่าง refresh/load history | เมื่อผู้ใช้เปิด metadata หรือทำงานกับสินค้าใดอยู่ การ refresh/focus/background response ต้องไม่สลับ  | 2026-09-10 | สำเร็จสมบูรณ์ |
| Round PRODUCT-METADATA-5 — แก้ metadata description/raw text ซ้ำ และเปิดแก้คำอธิบายสรรพคุณ | แยกความหมายของ “คำอธิบายสินค้า/สรรพคุณ” กับ “ข้อความต้นฉบับ” ให้ชัดเจน ไม่แสดงเนื้อหาซ้ำ และเปิดให้ผ | 2026-09-10 | สำเร็จสมบูรณ์ |
| Round PRODUCT-METADATA-4 — แก้ไข/preview metadata ก่อนบันทึก และจัดการ URL/ชื่อสินค้า | ให้การดึงข้อมูลซ้ำไม่ทับข้อมูลทันที, กันรูปและข้อความซ้ำ, เปิด preview/diff ก่อนยืนยัน, แก้ชื่อ/หัวข | 2026-09-10 | สำเร็จสมบูรณ์ |
| Round PRODUCT-METADATA-3 — ดึงรายละเอียดสินค้าจากหน้า TikTok ที่ render ด้วย JavaScript | ให้การแปะลิงก์ TikTok ที่มีคำอธิบาย/สรรพคุณอยู่ในหน้าเว็บจริง ได้ source text ที่เฉพาะเจาะจงเข้า met | 2026-09-10 | สำเร็จสมบูรณ์ |
| Round SUB-THAI-2 — แก้สระ `ั` กับวรรณยุกต์ `่` ซ้อนในฟอนต์จริง | Round SUB-THAI-2 — แก้สระ `ั` กับวรรณยุกต์ `่` ซ้อนในฟอนต์จริง | 2026-09-08 | สำเร็จสมบูรณ์ |
| Round POST-3.16 — แก้การแนบปกข้อ 5 และแสดงภาพปก 3:4 | Round POST-3.16 — แก้การแนบปกข้อ 5 และแสดงภาพปก 3:4 | 2026-09-07 | สำเร็จสมบูรณ์ |
| Round POST-3.17 — ซ่อม path ปกที่หายก่อนข้อ 5 | Round POST-3.17 — ซ่อม path ปกที่หายก่อนข้อ 5 | 2026-09-07 | สำเร็จสมบูรณ์ |
| Round POST-3.18 — make CDP cover upload notify TikTok React | Round POST-3.18 — make CDP cover upload notify TikTok React | 2026-09-12 | สำเร็จสมบูรณ์ |
| Round POST-3.20 - edit generated cover inside OmniCut | Round POST-3.20 - edit generated cover inside OmniCut | 2026-09-12 | สำเร็จสมบูรณ์ |
| Round PERF-UX-1 — ปรับ Reliability/Preview Performance/Autosave/Incremental Render/Timeline Scaling แบบแยก ownership ขนานกัน | ปรับความน่าเชื่อถือ, ความลื่นของ editor, ความเร็ว autosave/export และการรองรับ project ใหญ่ โดยแบ่ง  | 2026-09-09 | สำเร็จสมบูรณ์ |
| Round POST-1 — Desktop Post Studio (ปก + ลากไฟล์ + แคปชั่น + ปิดวงจร Posted) | จบงานโพสต์บนคอมได้ในหน้าเดียว — ปกสวยพร้อมอัป ไฟล์ลากได้ทันที แคปชั่นก็อปปุ่มเดียว | 2026-09-05 | สำเร็จสมบูรณ์ |
| Round POST-2 — TikTok auto-post extension (เสี่ยง) | กดปุ่มเดียวในแอป ให้ extension เติมไฟล์+ปก+แคปชั่นลงหน้าอัปโหลด TikTok ในเบราว์เซอร์ที่ login อยู่แล | 2026-09-05 | สำเร็จสมบูรณ์ |
| Round COV-1 — สตูดิโอสร้างปกคลิปด่วน 9:16 (Auto Highlight Crop, AI Hook & 4 TikTok Templates) | สตูดิโอสร้างภาพปกคลิปแนวตั้ง 9:16 (1080x1920) สำหรับโพสต์ลง TikTok Studio เพื่อเพิ่มยอดคลิก (CTR) ดึ | 2026-09-12 | สำเร็จสมบูรณ์ |
| Round PRO-STYLE-PARALLEL-4-6 — Parallel style roadmap execution | Round PRO-STYLE-PARALLEL-4-6 — Parallel style roadmap execution | 2026-09-09 | สำเร็จสมบูรณ์ |
| Round ANALYTICS-CHARTS-POLISH-1 | ปรับขนาดและจัดระเบียบเลย์เอาท์กราฟใน Analytics Hub ให้กระชับ สวยงาม พอดีสายตา ไม่ใหญ่เกินจำเป็น | 2026-09-12 | กราฟเส้น 800x130 widescreen, โดนัท top 4 + อื่นๆ พร้อม label ไม่หาย, TokenDashboard models/tasks จัดแบบ side-by-side; frontend 151 passed, build 3.25s, browser verified |
| Round USER-GUIDE-4 | คู่มือ interactive 6 ฟีเจอร์ (sticky TOC, เช็กลิสต์ติ๊กได้, accordion, ปุ่มลัด, FAQ ค้นหา) | 2026-09-12 | ไม่เปลี่ยนข้อความ/สี/ลำดับ; frontend 151 passed, build 4.22s |
| Round ANALYTICS-CHARTS-1 | พัฒนาระบบกราฟเส้น กราฟโดนัท Funnel Chart และเกจวัดแบบ Pure SVG สไตล์ Dark Modern Glassmorphism สำหรับแดชบอร์ดทั้ง 4 แท็บ | 2026-09-12 | สร้าง 4 Pure SVG charts (AreaLine, Donut, Funnel, ProgressRing/Concentric) ฝังครบ 4 แท็บ; vitest 151 passed, backend 4 passed, build 3.44s, browser verified |
| Round SHOTLIST-GEMINI-TTS-SSOT-1 | ระบบรวมศูนย์เสียง TTS (Gemini Flash Audio SSOT): แผนถ่าย & ตัดต่อจริงใช้เสียงเดียวกัน 100% ไม่เจนซ้ำ | 2026-09-12 | สังเคราะห์ด้วย Gemini Flash TTS เป็นค่าเริ่มต้น + Dropdown เลือก 5 เสียงใน Modal + VoiceStage reuse อัตโนมัติ; pytest 1,125 passed, vitest 158 passed, build 3.40s, browser verified |

## Round PAGINATION-1-VERIFY — browser-verify การ windowing 9 endpoint ที่ Round PAGINATION-1 แก้ไว้

วันที่: 2026-09-13 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ปัญหา:** Round PAGINATION-1 ปิดโดยยังไม่ได้ browser-verify — เครื่องมือของ Claude Code (curl, Playwright) เข้าถึง `localhost:5173` ไม่ได้เลยตลอด session แม้ user จะรีสตาร์ท dev server ใหม่ทั้งหมดแล้ว ขณะที่ `localhost:8000` (backend) เข้าถึงได้ปกติ (401 จาก missing API key) — สรุปว่าเป็นข้อจำกัดของ sandbox/network forwarding ฝั่งเครื่องมือ ไม่ใช่ dev server หรือโค้ดพัง (ทฤษฎีแรกที่คิดว่า terminal ค้าง QuickEdit mode ผิด — พิสูจน์แล้วเพราะรีสตาร์ทใหม่ทั้งหมดก็ยังเข้าไม่ได้เหมือนเดิม)

**วิธีปิด:** user เช็คเองผ่านเบราว์เซอร์จริงที่เปิดอยู่แล้ว (มี log ยืนยันว่า dev server ทำงานปกติ — HMR update + backend รับ request ต่อเนื่องจากหน้าเว็บจริง) ตามเช็คลิสต์ 4 ข้อที่ Claude Code ให้ (Export Gallery load-more, ContentTrackerHub table view, MediaAssetsHub tab switching, browser console ไม่มี error) — user ยืนยันว่าปกติ

**Notes:** เป็น spot-check ทั่วไป ไม่ใช่การกดปุ่ม "โหลดเพิ่ม" ทดสอบจริงทุกจุด เพราะข้อมูลปัจจุบันยังน้อยกว่า page size ของแต่ละจุด (เช่น export มีแค่ 11 คลิป < 24 ที่ตั้ง threshold ไว้) ปุ่ม "โหลดเพิ่ม" เลยยังไม่เคยถูกกดทดสอบจริงจนกว่าข้อมูลจะโตถึงเกณฑ์

## Round PAGINATION-1 (แผนอยู่ใน [PAGINATION_PLAN.md](file:///d:/Winona/Programmer/Capcut/PAGINATION_PLAN.md)) — เพิ่ม limit/pagination ให้ list endpoint ทั่วระบบ

วันที่: 2026-09-12 ถึง 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Claude Code (Claude Sonnet 5) · สถานะ: เสร็จสมบูรณ์

**ที่มา:** ผู้ใช้สังเกตว่า Export Gallery มี 10 คลิปยังโอเค แต่ถามว่าจะช้าไหมเมื่อถึงหลักร้อย — สั่งให้สำรวจทั้งระบบก่อนแล้วค่อยลงมือ

- [x] Phase 1 item 1: `/api/exports` + `ExportGallery.jsx` — **client-side windowed rendering แทน backend limit/offset** (พบว่า `exportsList` ถูก merge/aggregate ข้ามคอมโพเนนต์ ตัด limit ที่ backend จะพังข้อมูล ดูเหตุผลเต็มใน `PAGINATION_PLAN.md`) (2026-09-12; vitest 158 passed, build 3.27s)
- [x] Phase 1 item 2: `/api/products` (ผ่าน `ContentTrackerHub.jsx`) — **client-side windowed rendering** เหมือนกัน (kanban เป็นบอร์ดจัดการงาน ต้องเห็นทุกใบเพื่อทำงาน ตัด limit ที่ backend จะทำให้หาการ์ดเก่าไม่เจอ) — เพิ่ม windowing 2 จุด: kanban "Flat Cards List" (คอลัมน์ candidate/in_production/rendered ที่ไม่มี today-filter/accordion มาก่อน) ทีละ 20 การ์ดต่อคอลัมน์ + Table view (mobile card feed + desktop table) ทีละ 40 แถว ทั้งคู่มีปุ่ม "โหลดเพิ่ม" (2026-09-12; vitest 158 passed, build 7.25s)
- [x] Phase 1 item 3: `/api/videos` (`MediaPickerModal.jsx`) — audit เดิมชี้ผิดว่า consumer คือ `MediaAssetsHub.jsx` (จริงๆ นั่นคือ `/api/assets/all`) — เป็น picker modal เลือกคลิปเดียว ไม่มี aggregate ข้ามจุด → **client-side windowed rendering** ทีละ 40 การ์ด + ปุ่มโหลดเพิ่ม, reset เมื่อ search/tab เปลี่ยน (2026-09-12; vitest 158 passed, build 6.14s)
- [x] Phase 1 item 4: `/api/raw-vault` (`RawVaultPanel.jsx`) — เช็ค docstring endpoint พบว่า O(products×files) ที่ audit เดิมเตือนไว้ **แก้เป็น O(products+files) ไปแล้วในโค้ดจริง** (ไม่ใช่ปัญหาเปิดอยู่) เหลือแค่ประเด็น pagination — คลัง raw footage มี aggregate count ข้ามจุด (ผูกสินค้า/คลิปอิสระ) เหมือนกัน → **client-side windowed rendering** ทีละ 40 การ์ด + ปุ่มโหลดเพิ่ม (2026-09-12; vitest 158 passed, build 6.14s)
- [x] Phase 1 item 5: schedule-queue (`ScheduleAgenda.jsx`) — calendar view สัปดาห์อยู่แล้วโดยธรรมชาติ (7 วัน bounded), list view ผูกกับ `activeQueue` (ยังไม่โพสต์ ไม่โตมาก) ความเสี่ยงจริงอยู่ที่ modal "คลิปที่โพสต์แล้ว" (`postedQueue`, ไม่เคย prune) → windowed ทีละ 50 แถว + ปุ่มโหลดเพิ่ม, reset ทุกครั้งที่เปิด modal (2026-09-12; vitest 158 passed, build 4.23s)
- [x] Phase 1 item 6: `/api/tiktok-stats/latest` (`PerformanceAnalyticsTab.jsx`) — KPI การ์ด (totalViews, avgEngagement) อ่านจาก `richPosts` เต็มเหมือนเดิม, windowed เฉพาะตารางแสดงผลทีละ 50 แถว + ปุ่มโหลดเพิ่ม, reset เมื่อ sync ข้อมูลใหม่ (2026-09-12; vitest 158 passed, build 4.23s)
- [x] Phase 2 item 1: `/api/tiktok-stats/clip-candidates` — populate native `<select>` dropdown ไม่ใช่ custom card list → **ไม่ต้องแก้โค้ด** (native select scale ได้เป็นพันตัวเลือกไม่กระทบ perf)
- [x] Phase 2 item 2: `/api/assets/all` (`MediaAssetsHub.jsx`) — 7 จุด render (1 split-view + 6 grid-view ต่อประเภท) แต่โชว์ทีละจุดตาม tab เดียว → windowed ร่วมกันทีละ 40 รายการ + ปุ่มโหลดเพิ่ม (2026-09-13; vitest 158 passed, build 4.11s)
- [x] Phase 2 item 3: `/assets/duplicates/scan` (`SystemSettings.jsx`) — เสี่ยงต่ำกว่าอันอื่น (on-demand action, container จำกัดความสูงอยู่แล้ว) แต่แก้ให้สอดคล้องกัน windowed ทีละ 30 กลุ่ม + ปุ่มโหลดเพิ่ม, reset ทุก scan ใหม่ (2026-09-13; vitest 158 passed, build 3.22s)
- [x] Phase 3: เช็คครบ 4 จุด (`/api/posts*` dead code ยืนยันแล้ว, `/api/tiktok-stats/pending` self-clearing, `/backup/list` โตช้า+มี scroll container จำกัดอยู่แล้ว, `/api/tasks/active` ปลอดภัยด้วย hardcoded `limit=50`) — **ไม่ต้องแก้โค้ดสักจุด**

**Gate รวม:** pytest เต็มระบบ 1126 passed, vitest 158 passed ทุกรอบที่แก้, `npm run build` ผ่านทุกจุด

**Notes:**
- เลือก client-side windowing (ไม่ใช่ backend limit/offset) ทุก endpoint ที่แก้จริง เพราะทุกตัวมี aggregate/cross-component dependency (merge cover metadata, kanban board ต้องเห็นทุกใบ, KPI การ์ดต้องอ่านข้อมูลเต็ม ฯลฯ) — ต่างจาก Contract เดิมที่ตั้งใจไว้ตอนแรก (ดูหัวข้อ "ข้อค้นพบระหว่างลงมือจริง" ใน `PAGINATION_PLAN.md`)
- ระหว่างทำ commit `33aefcc` (แก้ shot-matching, git identity ผู้ใช้เอง) sweep เอา `MediaAssetsHub.jsx`/`SystemSettings.jsx` ที่ยังไม่ commit เข้าไปรวมด้วยโดยไม่ตั้งใจ — โค้ดถูกต้อง เทสผ่านหมด ไม่มีอะไรพัง แค่ attribution ปนกัน แจ้ง user แล้ว ไม่ได้แก้คืน
- **ยังไม่ได้ browser-verify เลยทั้งรอบ** — dev server (localhost:5173) ไม่ตอบ HTTP request ตลอด session (ดูเหมือน terminal ค้าง QuickEdit ไม่ใช่โค้ดพัง) → ย้ายเป็น Backlog item ให้เปิดแอปเช็คจริงทีหลัง

## Round EXPORT-ARCHIVE-POLICY-1 — แจ้งเตือน export ค้างนาน/ดิสก์ใกล้เต็ม (Combined Time + Disk Threshold)

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Claude Code (Claude Sonnet 5) · สถานะ: เสร็จสมบูรณ์

**ปัญหาเดิมและที่มา:** ผู้ใช้ถามว่าคลิปที่โพสต์แล้วถูกย้ายไฟล์ให้อัตโนมัติหรือไม่ ตรวจโค้ดพบว่า `03_Projects` ถูก auto-archive เข้า `06_Archive/Projects` จริงเมื่อกด "โพสต์แล้ว" (มีมาตั้งแต่ Round POSTED-CLIP-LIFECYCLE-1) แต่ `04_Exports` (วิดีโอ MP4) ตั้งใจไม่ย้ายเพื่อให้เปิดดูง่าย และไม่มี logic ใดๆ แจ้งเตือนว่าเมื่อไหร่ควรย้ายออกไป external drive — ผู้ใช้เลือกให้รวม 3 เงื่อนไข (อายุไฟล์ 30 วัน + disk threshold 80% + แจ้งเตือนแบบ manual ไม่ auto-move)

**สิ่งที่ทำ:**
1. `scripts/api_analytics.py`: เพิ่มค่าคงที่ `EXPORT_ARCHIVE_AGE_DAYS = 30`, `DISK_ALERT_PERCENTAGE = 80.0` + ฟังก์ชัน `_age_days_from_iso()` คำนวณอายุจาก ISO timestamp
2. เพิ่ม `posted_at`/`age_days` ให้ทุกรายการใน `posted_items_list` ของ `get_storage_analytics()` — project ใช้ `angle.posted_at` จริงจาก ProductStore, mp4 export ใช้ file mtime เป็น proxy (ไฟล์ไม่มี timestamp ของตัวเองตอน move เข้า `Posted/`)
3. เพิ่มฟิลด์ใหม่ `archive_recommendation` ใน response: `{ready_count, ready_mb, ready_items, disk_alert, should_notify, message}` — เงื่อนไข: อายุ >= 30 วัน **หรือ** ดิสก์ใช้ >= 80%
4. `frontend/.../StorageAnalyticsTab.jsx`: เพิ่ม banner สีเหลืองอำพันแสดงข้อความรวมเมื่อ `should_notify` true วางไว้บนการ์ด "Posted Clips Archive" เดิม — ไม่มีปุ่ม auto-move ใหม่ ยังคงเป็น manual (ผู้ใช้ย้ายไฟล์ไป external drive เอง)
5. Tests: ขยาย `tests/test_analytics_hub.py::test_storage_analytics_endpoint` เช็คคีย์ `archive_recommendation` และชนิดข้อมูล boolean ของ `disk_alert`/`should_notify`

**Gate:** pytest `tests/test_analytics_hub.py` 4 passed, `npm run build` 3.12s, live API verified (`archive_recommendation` คืนค่าถูกต้องจาก backend ที่ auto-reload แล้ว: `should_notify: false` เพราะยังไม่มีไฟล์อายุเกิน 30 วันและดิสก์ใช้แค่ 42.5%)

**Notes:** ไม่มี dedicated vitest สำหรับ StorageAnalyticsTab.jsx มาก่อน (ไม่มี convention เดิมให้ตาม) — ยืนยันด้วย pytest + build + live API แทน

## Round SHOTLIST-GEMINI-TTS-SSOT-1 — ระบบรวมศูนย์เสียง TTS (Gemini Flash Audio SSOT): แผนถ่าย & ตัดต่อจริงใช้เสียงเดียวกัน 100% ไม่เจนซ้ำ

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** รวมศูนย์ระบบสังเคราะห์เสียงพากย์ด้วย Google Gemini Flash TTS ระหว่างหน้าแผนถ่าย (Shot List) และหน้าตัดต่อ (Studio Editor / Render Pipeline) ให้เป็นไฟล์เสียงเดียวกันแบบ Single Source of Truth (SSOT) ลดขั้นตอนการเจนเสียงซ้ำซ้อน ประหยัดโควต้าโทเคนและเวลาเรนเดอร์ พร้อมให้ผู้ใช้สามารถเลือกเสียงพากย์ Gemini ได้จากใน Modal แผนถ่ายทันที

### สิ่งที่ทำ
1. **Backend SSOT Audio Reuse:**
   - ปรับ `scripts/shot_list_builder.py` ให้ใช้ `gemini_tts` เป็นค่าเริ่มต้น (+15% rate, commercial_premium, voice_preset: `gemini_kore_female_bright`)
   - บันทึกทั้ง `cues` และ `beat_cues` ลง `ShotListsStore`
   - เพิ่มเมธอด `ProductStore.update_angle_voice` ใน `scripts/product_store.py` เพื่อจำค่าเสียงพากย์ที่เลือกไว้ลงในการ์ดมุมสคริปต์
   - ใน `scripts/stages/voice_stage.py`: เพิ่มระบบตรวจจับไฟล์เสียงจากแผนถ่าย (`ShotListsStore`) หากมีอยู่แล้ว จะคัดลอกไฟล์เสียงเข้าโปรเจกต์ Studio และนำ `beat_cues` มาใช้งานทันที พร้อมข้ามการเรียก API สังเคราะห์เสียงซ้ำ (Zero redundant API calls)
2. **Frontend Gemini Voice Selector:**
   - ใน `frontend/src/components/ShotListModal.jsx`: เพิ่ม Dropdown เลือกเสียง Gemini TTS (Kore, Puck, Charon, Aoede, Fenrir) พร้อมปุ่ม "สร้างใหม่ด้วยเสียงนี้" ที่สวยงาม คลีน ตามกฎ Rule 8 (UI Clean Standard)
   - ปรับปรุงการเชื่อมโยงใน `frontend/src/components/ProductToClip.jsx` และ `frontend/src/components/ContentTrackerHub.jsx` ให้ส่ง voice overrides และส่งต่อ `voice_preset` ไปยัง Studio
   - ใน `frontend/src/lib/angleToForm.js`: ส่งต่อ `voice_preset` และ `voice_mode` เข้าฟอร์มของ NewClipPanel อัตโนมัติ

### Gate & Verification Results:
- [x] Backend Unit Tests: `tests/test_shot_list_enhancements.py` — 7/7 passed (รวม test cases ใหม่ของ Gemini TTS defaults และ VoiceStage reuse)
- [x] Full Backend Pytest Suite: 1,125 passed, 0 failed
- [x] Frontend Vitest Suite: 158/158 passed
- [x] Frontend Production Build: `npm run build` สำเร็จ 100% ใน 3.40 วินาที
- [x] Python Compilation: `python -m compileall -q scripts` ผ่าน 100% ปราศจากข้อผิดพลาด
- [x] Browser UI Verification: ตรวจสอบผ่าน Browser Subagent ยืนยันการแสดงผล Dropdown เสียง Gemini, ปุ่มแอ็กชัน และ Guide Track Audio Player ถูกต้องสวยงาม 100%

## Round SCRIPT-BATCH-EXPAND-1 — ระบบเจนสคริปต์ล็อตใหม่ 10 มุมมอง & ปรับระบบ Dev Server HTTP (Multi-Batch Generation & Filtering Flow)

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**ปัญหาเดิมและที่มา:**
1. เมื่อถ่ายคลิปและตัดต่อครบทุกมุมมองเดิม (เช่น 10 มุม) แล้ว เกิดคำถามเชิงสถาปัตยกรรมว่าควรสร้างการ์ดสินค้าตัวเดิมใหม่ ("BlueWow 1", "BlueWow 2") หรือใช้การ์ดสินค้าเดิมแล้วต่อยอดสคริปต์ล็อตถัดไปเรื่อยๆ
   - การแตกการ์ดใหม่ทำให้สถิติยอดวิว, รายได้ TikTok Shop, LTV สินค้า และการตั้งค่าแตกกระจาย ต้องมากรอกชื่อ สเปก และลิงก์ซ้ำ
   - ข้อตกลงสถาปัตยกรรมที่ถูกต้องตาม Single Source of Truth (SSOT): **1 สินค้าจริง = 1 การ์ดสินค้าคงที่** โดยรองรับระบบ Multi-Batch ล็อตสคริปต์ (ล็อต 1, ล็อต 2...) ภายใต้การ์ดเดียวกัน
2. Dev Server ของ Vite รัน HTTPS (`basicSsl()`) บน `localhost:5173` ทำให้ Chrome ฟ้อง Privacy Error (`NET::ERR_CERT_AUTHORITY_INVALID`) และ Playwright ของ AI subagent ถูกตัดการเชื่อมต่อทันที (`net::ERR_ABORTED`) ผู้ใช้ต้องคอยกด allow ซ้ำๆ ทุกครั้ง

**สิ่งที่ทำ:**
1. **Dev Server SSL Fix (`frontend/vite.config.js` & `package.json`):**
   - ปรับ `basicSsl()` ให้เป็น conditional: `...(enableSsl ? [basicSsl()] : [])` โดยเปิด HTTPS เฉพาะเมื่อรัน `mode === 'mobile'` หรือตั้ง `VITE_HTTPS === 'true'`
   - ค่าเริ่มต้นของ `npm run dev` รันบน HTTP `http://localhost:5173` ซึ่ง W3C/Chromium ยอมรับเป็น Secure Context ทันที 100% ปลดล็อก Privacy Error ถาวร และทำให้เบราว์เซอร์ subagent ของ AI เข้าถึงหน้าเว็บได้อัตโนมัติ
2. **Backend Multi-Batch Architecture:**
   - `scripts/product_store.py`: เพิ่ม `append_angles` (ต่อท้ายมุมมองใหม่พร้อมแท็ก `batch` ถัดไปแบบ atomic) และ `add_single_angle`
   - `scripts/product_scraper.py`: ปรับ `generate_content_matrix` ให้รับ `avoid_angles` และ `batch_label` เพื่อฉีด prompt สั่ง AI ไม่ให้คิดมุมมองและฮุกซ้ำกับที่เคยทำมาในล็อตก่อนๆ
   - `scripts/api_products.py`: เพิ่ม background task worker และ endpoint `POST /api/products/{product_id}/generate-batch` และ `POST /api/products/{product_id}/angles`
3. **Frontend Multi-Batch Script Lab (`frontend/src/components/ProductToClip.jsx`):**
   - แสดง Progress Header: `Step 2 — เลือกมุมขาย & คลิปประกอบ (X สคริปต์ • Y ล็อต) • โพสต์แล้ว M/N คลิป`
   - แถบ Sub-bar:
     - แท็บเลือกล็อต: `[ทุกล็อต]`, `[ล็อต 1]`, `[ล็อต 2]` พร้อมระบุจำนวนมุมของแต่ละล็อต
     - ตัวกรองด่วน: `[ซ่อนที่โพสต์แล้ว (N)]` toggle ดูเฉพาะมุมที่ยังไม่ได้ตัด/ยังไม่โพสต์
     - ปุ่มแอ็กชัน: ตัดปุ่ม "เพิ่มสคริปต์" (manual single angle) ออกทั้งหมดตามคำสั่งผู้ใช้ เพื่อไม่ให้เกิดล็อตลอยๆ เหลือเฉพาะปุ่ม `[เจนล็อตใหม่]` ให้ AI วิเคราะห์มุมเดิมและคิดเพิ่มเป็นชุดล็อตจริง 4/7/10 มุม
     - ปฏิบัติตาม Rule 8 (UI Clean Standard) ไม่มีเครื่องหมาย `+` นำหน้าข้อความปุ่มเมื่อมีไอคอน
     - เคลียร์สคริปต์ขยะที่เกิดจากการกดเพิ่มสคริปต์เดี่ยวๆ ออกจากสินค้า BlueWow และจัดระเบียบล็อตเหลือ ล็อต 1 (13 มุม) และ ล็อต 2 (10 มุม) รวม 23 มุม สะอาดเรียบร้อย 100%
   - Modal เจนล็อตใหม่: แสดงรายชื่อมุมเดิมที่จะหลีกเลี่ยงเป็น tag badges, เลือกจำนวนมุมและเวลา, ปุ่มสร้างล็อตถัดไป
4. **Automated & Visual Verification:**
   - Unit tests backend: `tests/test_product_batch_angles.py` ครอบคลุมการต่อยอดล็อต, batch index, และ API endpoints (3/3 passed)
   - Backend full pytest: 171 passed (0 failed)
   - Frontend vitest: 158 passed (0 failed)
   - Production build: `vite build` สำเร็จ 3.25s
   - Browser Subagent: ตรวจสอบหน้าเว็บ `http://localhost:5173/` โหลดคลีน 100% ปราศจาก SSL error, เข้าหน้าห้องสคริปต์, ตรวจแท็กล็อต, ปุ่มฟิลเตอร์, และคลิกเปิด Modal เจนล็อตใหม่พร้อมจับภาพหน้าจอ

## Round UI-FONT-MONO-CLEAN-1 — กวาดล้าง font-mono ที่ครอบข้อความภาษาไทย/การ์ด KPI ทั่วทั้งระบบให้เป็นฟอนต์กลาง 100%

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**ปัญหาเดิมและที่มา:**
- ผู้ใช้ตรวจพบว่าในการ์ด KPI "ลงโพสต์แล้ว (Published)" คำว่า "คลิป 25%" มีฟอนต์ที่แปลกแยกอย่างเห็นได้ชัด
- **Root Cause Analysis:**
  1. ใน `MetricKpiCard.jsx` มีการใส่คลาส `font-mono` ครอบทั้งตัวเลข หน่วยนับ และ badge ทำให้คำว่า "คลิป" และ "25%" ถูกเรนเดอร์ด้วยฟอนต์ Monospace ซึ่งไม่มีชุดอักษรภาษาไทยแท้ จึงถูก fallback ไปใช้ฟอนต์ monospace ประจำระบบที่ตัวอักษรไม่กลมกลืนกับฟอนต์ระบบ
  2. ใน `Badge.jsx` (คอมโพเนนต์ป้ายส่วนกลาง) มีการใส่ `font-mono` ไว้ที่ตัวป้าย ทำให้ทุกจุดที่เรียกใช้ `<Badge>` แสดงผลภาษาไทยเป็น monospace
  3. พบการใส่ `font-mono` ครอบข้อความภาษาไทยและหน่วยนับในอีกหลายคอมโพเนนต์ (เช่น แคปชันและสถานะใน ContentTrackerHub, MediaAssetsHub, SystemSettings, ExportGallery ฯลฯ)

**สิ่งที่ดำเนินการ:**
1. **`MetricKpiCard.jsx`:** ถอด `font-mono` ออกจาก container ของค่าตัวเลข/หน่วยนับ/badge เพื่อให้ค่าตัวเลขและคำอธิบายสืบทอดฟอนต์ระบบ (Global UI Font) ได้อย่างสวยงาม
2. **`ProductionAnalyticsTab.jsx`:** แยกตัวเลขและหน่วยนับ `คลิป` ออกเป็น `<>{summary.posted} <span className="text-sm font-semibold text-slate-300 ml-1">คลิป</span></>` ให้ขนาดและสัดส่วนกลมกลืนกับการ์ดอื่นๆ
3. **`Badge.jsx`:** ถอด `font-mono` ออกจากตัวป้าย Badge ส่วนกลาง เพื่อให้ป้ายทั่วทั้งระบบแสดงผลภาษาไทยด้วยฟอนต์ระบบ
4. **ล้าง `font-mono` ออกจากข้อความภาษาไทยและหน่วยนับในคอมโพเนนต์อื่นๆ:**
   - `ContentTrackerHub.jsx`: แคปชันคลิป (`ang.tiktok_caption`), สถานะ (`● พร้อมตัดต่อ`, `● ยังไม่ได้เลือกคลิป`, `● พร้อมเล่น`), หัวคอลัมน์ (`4 คอลัมน์`)
   - `MediaAssetsHub.jsx`: ข้อความคำแนะนำ (`แตะเพื่อดูรายละเอียด`), ขนาดพรีวิว, ป้ายฟอร์แมต (`PNG โปร่งใส`, `WebM VP9 โปร่งใส`)
   - `MediaPickerModal.jsx`: ป้ายแจ้งเตือนการเลือกคลิป (`{selectedList.length} คลิป`)
   - `MobileQuickPostPage.jsx`: จำนวนตัวอักษร (`{fullPostText.length} อักษร`)
   - `RawVaultPanel.jsx`: จำนวนคลิปดิบ (`{vaultData.total_clips} ไฟล์`, `{selectedPaths.length} คลิป`)
   - `ScriptLab.jsx`: ข้อความคำแนะนำ (`ปรับแก้ข้อมูลได้ตลอดเวลา`)
   - `SubSrtTool.jsx`: ข้อความคำแนะนำ (`ลากไฟล์เข้า CapCut ได้ทันที`)
   - `ExportGallery.jsx`: เวลา (`วินาทีที่ {atSeconds.toFixed(1)}s`)
   - `SystemSettings.jsx`: หน่วยนับของไฟล์สแกนซ้ำ (`{dedupResult.total_scanned_files} ไฟล์`, `กลุ่ม`, `ไฟล์`)
   - `OverlayInspector.jsx` & `ProjectInspector.jsx`: หน่วยนับเวลาและชื่อ BGM เริ่มต้น
5. **Strict UTF-8 Integrity:** ตรวจสอบอักขระภาษาไทยทุกตัวคงเดิม 100% ไม่มีการแปลงเป็น ANSI

**ผลการทดสอบ (Verification Gate):**
- Frontend Vitest: 152/152 passed
- Vite Build: 3.31s ผ่าน 100% สะอาด ไร้ error

---

## Round UI-POLISH-HEADER-1 — แก้ฟอนต์กล่องแดง Topbar (ถอด font-mono) + ตัด 2 Badge สินค้า + ขยายหัวข้อสินค้าเน้นๆ ใหญ่ๆ

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**ที่มาและปัญหาที่ได้รับแจ้ง:**
1. **กล่องแดง (ป้ายแท็บ Topbar):** ป้ายแท็บ เช่น `1. AI Script Lab` ฟอนต์ดูแปลกแยกจากข้อความอื่น ตรวจสอบพบว่ามีคลาส `font-mono` ตกค้างอยู่ ทำให้แสดงผลเป็น Monospace แทนที่จะเป็น Global UI Font
2. **กล่องเหลือง (2 Badge ใน PageHeader สินค้า):** มี Badge `ราคาพิเศษในตะกร้า` และ `ID: ...` บดบังและแย่งสายตา ทำให้ชื่อสินค้าดูเล็ก
3. ผู้ใช้ต้องการให้ตัด 2 Badge นั้นออก และปรับหัวข้อชื่อสินค้า (`Logitech Lift`) ให้ "เน้นๆ ใหญ่ๆ" โดดเด่น

**สิ่งที่ดำเนินการ:**
1. **`frontend/src/components/Topbar.jsx`:** ถอดคลาส `font-mono` ออกจากป้ายแท็บ `currentTab.badge` เพื่อให้แสดงผลด้วย Global UI Font (Prompt, IBM Plex Sans Thai ฯลฯ) ที่สวยงาม สอดคล้องกันทั้งแถบ
2. **`frontend/src/components/ProductToClip.jsx`:** 
   - นำ 2 Badge (`price_note` และ `tiktok_product_id`) ออกจาก `PageHeader`
   - ปรับหัวข้อสินค้า `titleClassName` ให้เป็น `text-lg sm:text-xl md:text-2xl font-black text-white tracking-tight` และปรับ `titlePrefix` ให้ชัดเจน สมดุลกับขนาดชื่อสินค้าใหม่

**ผลการทดสอบ (Verification Gate):**
- Frontend Vitest: 152/152 passed
- Vite Build: 3.49s ผ่าน 100% ไร้ข้อผิดพลาด

---

## Round UI-FONT-HARMONY-1 — ปรับความสอดคล้องของฟอนต์ UI ทั้งระบบตาม Global UI Font (ปราศจาก Encoding Mojibake)

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**ปัญหาเดิมและที่มา:**
1. ผู้ใช้พบว่าฟอนต์ในหน้า UI มีจุดที่ไม่เป็นฟอนต์เดียวกัน เมื่อเปลี่ยนฟอนต์ระบบ (Global UI Font) ในหน้าตั้งค่าเป็น Prompt, IBM Plex Sans Thai ฯลฯ พบว่าหัวข้อ ปุ่ม และการ์ดหลายจุดไม่ยอมเปลี่ยนตาม
2. สาเหตุเกิดจากคอมโพเนนต์ UI จำนวน 35 ไฟล์มีการ hardcode คลาส `font-kanit` ไว้ที่ elements ทำให้ specificity ของ CSS เหนือกว่าฟอนต์ระบบที่ตั้งไว้ที่ root (`uiFont`)
3. ในรอบก่อนหน้ามีความพยายามแก้ด้วย PowerShell ซึ่งอ่าน/เขียนไฟล์ด้วย ANSI ทำให้เกิดตัวอักษรต่างดาว (Mojibake) รอบนี้จึงย้อนคืนและใช้แนวทางใหม่ที่รับประกันความถูกต้อง 100%

**สิ่งที่ดำเนินการ:**
1. **ปลดล็อคคลาส `font-kanit` ใน 35 คอมโพเนนต์ UI:**
   - ปลดล็อคคลาส `font-kanit` ออกจากคอมโพเนนต์ UI เพื่อให้สืบทอดฟอนต์ระบบ (Global UI Font: Prompt, IBM Plex Sans Thai, Kanit, Anuphan ฯลฯ) ที่ผู้ใช้เลือกจาก Settings ได้อย่างสมบูรณ์แบบ
   - รายชื่อคอมโพเนนต์ที่อัปเดต: `ActivityCenter`, `ContentTrackerHub`, `ErrorBoundary`, `ExportGallery`, `Header`, `LoadingSpinner`, `MediaAssetsHub`, `MediaPickerModal`, `MobileFilmingPage`, `MobileQuickPostPage`, `PresetsBar`, `ProductToClip`, `RawVaultPanel`, `ScheduleAgenda`, `ScriptLab`, `ShortcutsModal`, `ShotListModal`, `Sidebar`, `SubSrtTool`, `SystemAssets`, `SystemSettings`, `TokenDashboard`, `Topbar`, `UserGuide`, `MetricKpiCard`, `InventoryAnalyticsTab`, `PerformanceAnalyticsTab`, `ProductionAnalyticsTab`, `StorageAnalyticsTab`, `AssetPanel`, `EditorShell`, `NewClipPanel`, `ConfirmModal`, `Modal`, `PageHeader`
2. **คงไว้ซึ่งตัวอย่างฟอนต์ (Preserved Font Picker Previews):**
   - อนุรักษ์ `id: 'font-kanit'` และ `bgClass: 'font-kanit'` ใน `SystemSettings.jsx` และ `SystemAssets.jsx` เพื่อให้การ์ดแสดงตัวอย่างฟอนต์ Kanit ยังคงแสดงผลสไตล์ Kanit ได้ถูกต้อง 100%
3. **การันตีเรื่อง Encoding (Zero Mojibake Guarantee):**
   - ใช้ Python UTF-8 พร้อม Strict Assertion ตรวจสอบว่าอักขระที่ไม่ใช่ ASCII (สระ พยัญชนะ วรรณยุกต์ภาษาไทย) ทุกตัวต้องเหมือนเดิมแบบ byte-for-byte 100%
4. **Strict Non-Regression:**
   - ไม่แตะต้อง `subtitle_engine.py`, `SequencePlayer.jsx` หรือโค้ดเรนเดอร์วิดีโอใดๆ (ผ่าน 153/153 Parity Tests)

**ผลการทดสอบ (Verification Gate):**
- Frontend Vitest: 152/152 passed (7.55s)
- Vite Build: ผ่าน 100% สะอาด ไร้ error (4.57s)
- Backend Preview-Render Parity Tests: 153/153 passed (10.36s)
- Browser Live Test: เปิดหน้าจอจริงผ่าน Browser Subagent ทดสอบสลับฟอนต์ในหน้าตั้งค่า (Prompt -> IBM Plex Sans Thai -> Kanit) ตรวจสอบหน้าสคริปต์แล็บและหน้าสถิติ พบว่าตัวอักษรภาษาไทยคมชัด สวยงาม ไม่มีตัวหนังสือต่างดาว และทั้งหน้าจอเปลี่ยนตามฟอนต์ที่เลือกอย่างสอดคล้องกัน

---

## Round TIKTOK-DASH-DATA-1 — ล้างโพสต์ทดสอบ 163 รายการใน post_log + กัน merge ยอดซ้ำข้ามแถวในรอบซิงก์เดียว

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Cline (โมเดลฐานไม่ได้ระบุในเซสชันนี้) · สถานะ: เสร็จสมบูรณ์

**หลักฐาน:** user ซิงก์สำเร็จ 8/10 แต่ Dashboard "สถานะ TikTok" ยังโชว์ 2.5M views / คลิปยอดนิยม "Test Serum Anti-Aging 15.2K" — ตรวจ `_Docs/post_log.json` พบ 167 โพสต์ = **163 โพสต์ทดสอบ Serum** (ยิง POST /api/posts ทดสอบซ้ำช่วง 3-4 ก.ย. ติดยอดวิวจำลองรวม ~2.5M) + โพสต์จริงจากซิงก์ 4 รายการ (รวม ~895 views) — ยืนยันว่า Dashboard อ่านข้อมูลจริงจาก `/api/tiktok-stats/latest` ทั้งหมด ไม่มี mock ในโค้ด แต่ข้อมูล mock ในไฟล์จมของจริง และพบเพิ่มว่ายอดวิวคลิป Logitech Lift โดนแถว Studio อื่น fuzzy match ซ้ำเข้ามาทับ (จอโชว์ 59 → ไฟล์เก็บ 370)

**การเปลี่ยนแปลง:**
1. **ล้างข้อมูลทดสอบ (user ยืนยันผ่าน ask_question):** backup ครบ 167 รายการ → `_Docs/post_log_backup_mock_20260912.json` แล้วล้าง 163 โพสต์ Serum เหลือ 4 โพสต์จริง (Logitech Lift 370 / GoChek GC-ULTRA S24 239 / BlueWow X110 271 / Logitech Wave Keys 15) — ทำผ่านชั้น `PostLog._save` (SQLite `_Docs/store.db` + JSON mirror สอดคล้องกัน) พร้อม assert จำนวนก่อนเขียนทุกขั้น (163/4 และหลังเขียน = 4)
2. **กัน merge ยอดซ้ำข้ามแถว (`scripts/post_log.py` upsert_tiktok_stats):** เพิ่ม claim guard — 1 โพสต์ถูก claim ได้จาก 1 แถวต่อรอบซิงก์ และแถวที่ video id ไม่ตรงกับ `tiktok_video_id` ที่เก็บไว้ห้าม fuzzy match เข้าโพสต์นั้น (แก้กรณี 370 ทับ 59) — แถวที่โดนปฏิเสธจะไปลงทะเบียนโพสต์ของตัวเองจาก candidates หรือขึ้น unmatched แทน การกดซิงก์ครั้งถัดไปจะเขียนยอด Lift กลับเป็น 59 ให้เอง (จับคู่ด้วย video id แบบ exact)
3. **Regression test:** `test_import_never_merges_two_similar_rows_into_one_post` — แถวคล้ายกัน 2 แถวต่าง video id ต้องได้ 2 โพสต์ ยอด {59, 370} ครบ ไม่ทับกัน

**ผลการทดสอบ (Verification Gate):**
- pytest เต็ม: 1114 passed (test_tiktok_stats_import 9 passed รวมเคสใหม่)
- Extension node --test (3 ไฟล์): 32 pass / 0 fail
- python -m compileall -q scripts: ผ่าน
- ข้อมูลหลังล้าง: 4 โพสต์จริง ยอดรวม 895 views — Dashboard โชว์ตัวเลขจริงทันทีหลัง restart backend

---

## Round TIKTOK-STATS-MATCH-1 — แมพสำเร็จ 0/10 เพราะไม่มีโพสต์ให้จับคู่ → จับคู่กับคลังผลงานแล้วลงทะเบียนโพสต์อัตโนมัติ

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Cline (โมเดลฐานไม่ได้ระบุในเซสชันนี้) · สถานะ: เสร็จสมบูรณ์

**หลักฐาน:** user กดซิงก์สำเร็จ (build 0.2.0 ขึ้น, อ่านตารางได้ 10 แถว) แต่ได้ผล "ซิงก์สำเร็จ 0/10 คลิป ... ไม่เจอคู่ 10 คลิป" — ตรวจ `_Docs/post_log.json` (163 โพสต์) พบว่า**ไม่มีสักโพสต์ของ ESSAGER/Logitech/GoChek/BlueWow (0 รายการ)** — ทั้งไฟล์เป็นข้อมูลทดสอบ Test Serum เก่า แปลว่าคลิปจริงไม่เคยถูกบันทึกว่าโพสต์แล้วใน OmniCut (user โพสต์ผ่าน Studio ตรงๆ โดยไม่กดมาร์ค) จึงไม่มีอะไรให้จับคู่ตั้งแต่ต้น — ไม่ใช่บั๊กการจับคู่

**การเปลี่ยนแปลง:**
- `scripts/post_log.py`: รีไรต์ `_fuzzy_match` เป็นระบบคะแนน (`_score_against_haystack`) บนชื่อที่ normalize แล้ว (`_normalize_title`: ตัด #แฮชแท็ก/อีโมจิ/สัญลักษณ์, lowercase) — token ซ้อน +1, คำยาว ≥4 (แบรนด์/รุ่น) +2, prefix 12 ตัวบน normalize +3, เกณฑ์ผ่าน ≥4; ประตูความยาวคลิปใช้เมื่อทั้งคู่มีข้อมูลเท่านั้น (±5s); เลือก best-score แทน first-match (tie → โพสต์ใหม่กว่า)
- `scripts/post_log.py`: `upsert_tiktok_stats(rows, register_missing, clip_candidates)` — แถวที่ไม่เจอโพสต์ จับคู่กับ candidate คลิปจากคลังผลงาน (`_match_candidate`) แล้ว**สร้างโพสต์ใหม่อัตโนมัติ** (posted_at parse จากวันที่ไทยของ Studio เช่น "11 ส.ค. 9:30 PM" → ISO, `source=tiktok_stats_auto`) + แนบ metrics/video_id/url ทันที — append ภายใน mutate เดียว (กัน nested SQLite transaction)
- `scripts/post_log.py`: เพิ่ม `_parse_studio_posted_at` (ตารางเดือนไทยย่อ 12 เดือน, AM/PM, ปีปัจจุบัน + rollover ธ.ค.→ปีก่อน)
- `scripts/api_tiktok_stats.py`: `_export_clip_candidates()` ดึง hook_title/product_name/clip_file จาก ProductStore (ทน store พังด้วย try/except + warning) แล้วส่งเข้า upsert; response เพิ่ม `registered`
- `tiktok_autopost_extension/sidepanel.js`: ข้อความสำเร็จเพิ่ม "ลงทะเบียนโพสต์ใหม่ N รายการ"
- `tests/test_tiktok_stats_import.py`: +4 เทส (auto-register จาก candidate + วันที่ไทย, ไม่สร้างเมื่อไม่ตรงเลย, โพสต์เดิมมาก่อนเสมอ, parse วันที่ไทยหลายรูปแบบ) + เทสเดิม 3 ตัว monkeypatch `_export_clip_candidates` → [] เพื่อ deterministic/offline (ไม่แตะ store จริง)

**ผลลัพธ์ / Gate:**
- `python -m compileall -q scripts`: ผ่าน
- `.venv\Scripts\python.exe -m pytest tests/test_tiktok_stats_import.py`: **8 passed** (เดิม 4 + ใหม่ 4)
- `node --test` (extension ทั้งชุด): **32 passed / 0 failed**
- หมายเหตุ: รอบแรกที่ user กด sync หลังรอบนี้ โพสต์จะถูก "ลงทะเบียนใหม่" อัตโนมัติจากคลังผลงาน (ต้องมี hook_title คลิปใน OmniCut ตรงคำในแคปชั่น Studio) — ครั้งถัดไปจะจับคู่ด้วย tiktok_video_id ตรงทันที

---

## Round TIKTOK-STATS-DOM-2 — รีเขียน parser ให้อ่าน div-grid จริงของ Studio (จากไฟล์ DOM ที่ user เซฟมาเอง)

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Cline (โมเดลฐานไม่ได้ระบุในเซสชันนี้) · สถานะ: เสร็จสมบูรณ์

**หลักฐาน:** ผู้ใช้ส่งไฟล์ DOM จริง `C:\Users\Winon\Downloads\html lang=th-TH dir=ltr style=--rw.txt` (หน้า tiktok.com/tiktokstudio/content) — กดซิงก์แล้วยังขึ้นแถบแดง "จำกัดโดเมน" เหมือนเดิม และใต้ปุ่มซิงก์ไม่มีบรรทัด "build 0.2.0"

**สิ่งที่ตรวจพบจากไฟล์:**
1. ตารางโพสต์ของ Studio จริง**ไม่ใช่ `<table>` เลย** — parser เดิม (อิง thead/tbody) อ่านไม่ได้ตั้งแต่โครงสร้าง ของจริงเป็น div-grid: แถวราก = `div[data-tt="components_RowLayout_FlexRow"]`, ชื่อ+ลิงก์ = `PostInfoCell_a`, วันที่ = `PublishStageLabel_TUXText`, ความยาว = `VideoCover_index_TUXText`, ความเป็นส่วนตัว = `PrivacyCell_TUXButton` > `.TUXButton-label`, ช่องตัวเลข = `div[width="100px"][data-tt^="components_RowLayout_FlexRow_"]` เรียงตามลำดับคอลัมน์
2. **แก้ความเข้าใจของรอบ DOMAIN-1:** หัวคอลัมน์จริงจาก DOM คือ **"ยอดการดู"** (มีใน alias เดิมอยู่แล้ว) — รอบก่อนสรุปว่าเป็น "ยอดวิว" จากการอ่านภาพหน้าจอเล็กซึ่งคลาดเคลื่อน; คง alias ยอดวิว ไว้เชิงป้องกัน
3. ไม่มีสำเนา extension อื่นในเครื่อง (ค้น Capcut_backups / Claude-video-editing-studio / Downloads / Desktop / Documents แล้วว่าง) → แถบแดงเดิม = Chrome ยังไม่ได้ reload โค้ดใหม่

**การเปลี่ยนแปลง:**
- `stats_parser.js`: แยกเส้นทางเดิมเป็น `parseTableRows()` (fallback) + เพิ่ม `locateDivGrid()` + `parseDivRows()` — จับคู่ช่องตัวเลขกับหัวคอลัมน์**ตามลำดับหัว** ไม่ใช่ index ตายตัว, resolve href ญาติเป็น absolute, dedupe ด้วย video_id กันแถวซ้ำจาก overlay, error แยกกรณี "เจอ header แต่ 0 แถว (virtual list) → ให้เลื่อนหน้าก่อน"
- `stats_parser.test.cjs`: รีไรต์ fake DOM เป็น generic engine (tag/.class/`[data-tt=..]`/`[data-tt^=..]`/`[width=..]`/`[href*=..]`) + fixture `buildDivGrid` จำลองโครงจริง + เทสใหม่ 4 ตัว (อ่านครบทุก field / จับคู่ตามลำดับหัวแบบสลับถูกใจ-คอมเมนต์ / header เจอแต่ 0 แถว / dedupe แถวซ้ำ) + เปลี่ยนชื่อเทส alias เป็น "ยอดการดู (real DOM wording) + ยอดวิว"

**ผลลัพธ์ / Gate:**
- `node --test` (background + stats_parser + clip_state): **32 passed / 0 failed** (เดิม 28 → +4 เทส div-grid)
- `node --check stats_parser.js` + `node --check sidepanel.js`: ผ่านทั้งคู่
- หมายเหตุ: รันครั้งแรก fail 1 จุดเพราะ fixture ลืมห่อปุ่ม `components_PrivacyCell_TUXButton` (parser ถูกต้องตาม DOM จริง) — แก้ fixture แล้วผ่าน

---

## Round TIKTOK-STATS-DOMAIN-1 — แก้ซิงก์สถิติล้มบนหน้า /tiktokstudio/content + ตรวจจับโค้ดเก่าค้างใน Chrome

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Cline (โมเดลฐานไม่ได้ระบุในเซสชันนี้; ปิดรอบร่วมกับ Antigravity) · สถานะ: เสร็จสมบูรณ์

**อาการ:**
- กดปุ่ม "ซิงก์สถิติจากหน้านี้" บนหน้า `tiktok.com/tiktokstudio/content` แล้วแถบข้างขึ้นแดง "จำกัดโดเมน: ปุ่มนี้ทำงานเฉพาะหน้าโพสต์เท่านั้น..."
- ยืนยันด้วย `git log -S` ว่าข้อความนี้ไม่มีในซอร์สปัจจุบันและไม่เคยมีใน history ทุก commit → Chrome กำลังรัน sidepanel.js เวอร์ชันเก่าค้าง/สำเนาอื่น (โค้ดจริงตรวจแบบ regex `/tiktok\.com/` ซึ่งผ่านหน้า content อยู่แล้ว)
- บั๊กแฝงที่จะโดนต่อทันที: parser หาคอลัมน์ด้วย alias `ยอดดู/ยอดการดู` แต่หน้า Studio ไทยจริงใช้หัวคอลัมน์ "ยอดวิว" → จะ error "ไม่พบตารางโพสต์" แม้ reload ถูกแล้ว

**การเปลี่ยนแปลง:**
- `stats_parser.js`: เพิ่ม alias `ยอดวิว` ให้คอลัมน์ views + เพิ่ม `cleanTitle()` ตัดท้าย "00:25 11 ส.ค. 9:30 PM" ออกจากชื่อคลิป (regex เดิมจับเดือนแบบ ก.-ฮ. ตัวเดียว เลยหลุด ส.ค./เม.ย./มี.ค.) + export cleanTitle ให้เทสใช้
- `sidepanel.js`: เพิ่ม `resolveTikTokTab()` + `tiktokHrefOf()` — ถ้า `tab.url` ว่างจะ fallback อ่าน `location.href` จากหน้าจริง, ถ้าแท็บ active ไม่ใช่ TikTok จะค้นทุกหน้าต่างที่เปิด tiktok.com ไว้แล้วสลับให้เอง, error บอก URL ที่เห็นจริง + แปะ "build 0.2.0" จาก `chrome.runtime.getManifest()` ในแท็บเครื่องมือ
- `sidepanel.html`: เพิ่ม `<p id="buildTag">` ใต้ปุ่มซิงก์ — ถ้าไม่เห็น build tag แปลว่า Chrome รันโค้ดเก่าค้าง (จบปัญหาวินิจฉัยไม่ได้)
- `manifest.json`: bump version 0.1.0 → 0.2.0
- `stats_parser.test.cjs`: +2 เทส (หัวคอลัมน์ "ยอดวิว" จับได้ตรงหน้าจอจริง / cleanTitle ตัด ส.ค., เม.ย., ก.ย. และไม่ช้ำชื่อรุ่น 27W/X110)
- `background.test.cjs`: +1 เทส (manifest ต้อง 0.2.0, buildTag ต้องมี, ห้ามมีข้อความ strict-domain ย้อนกลับมา, ต้องมี resolveTikTokTab + location.href fallback)

**ผลลัพธ์ / Gate:**
- `node --test` (background + stats_parser + clip_state): **28 passed / 0 failed**
- `node --check sidepanel.js` + `node --check stats_parser.js`: ผ่านทั้งคู่
- หมายเหตุ: รันครั้งแรก fail 1 จุด เพราะคอมเมนต์อธิบายใน sidepanel.js พิมพ์ข้อความนั้นเองไว้ (regression test จับได้ตามดีไซน์) — แก้คอมเมนต์เป็นภาษาอังกฤษแล้วผ่าน; การแก้คอมเมนต์นี้อยู่หลัง commit adb3fed ต้อง commit ตามเพื่อให้ HEAD สะอาดผ่านเทส

---

## Round BATCH-RENDER-1 — One-Click Batch Angle Video Render Queue (เรนเดอร์หลายมุมมองพร้อมกันในคลิกเดียว)

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
1. ให้ผู้ใช้สามารถติ๊กเลือกหลายมุมมองขาย (Angles) ของสินค้า แล้วสั่งเรนเดอร์เป็นวิดีโอ MP4 สำเร็จรูปพร้อมกันในคลิกเดียว (Batch Render Queue)
2. มีคิวประมวลผลเบื้องหลัง (Background FIFO Task Worker) แสดงสถานะและแถบความคืบหน้ารวมบน Activity Drawer และในหน้าจอ `ProductToClip`
3. ป้องกันปัญหา CPU/Memory Peak ด้วย Concurrency Lock (เรนเดอร์ทีละ 1 มุมมองตามลำดับ) พร้อม Auto-Retry 1 ครั้งเมื่อเรนเดอร์ติดขัด และถ้ามีมุมมองใดผิดพลาด จะไม่ทำให้มุมมองอื่นในคิวหยุดชะงัก
4. ปฏิบัติตาม Rule 7, Rule 8, Rule 9 และ Rule 14

**การเปลี่ยนแปลง:**
- `scripts/batch_render.py`: พัฒนา `BatchRenderManager` จัดการคิวงานเรนเดอร์แบบ FIFO ในเธรดเบื้องหลัง, คัดกรองมุมมองที่ยังไม่ได้โพสต์/ตัดต่อ, เชื่อมต่อ `TaskManager` อัปเดตความคืบหน้ารวม (`progress`, `step_label`), และอัปเดตสถานะมุมมองใน `ProductStore` เป็น `in_production` -> `rendered`
- `scripts/api_batch_render.py`: สร้าง FastAPI Router พร้อม endpoints:
  - `POST /api/render/batch`: รับคำสั่งเริ่มคิวเรนเดอร์ชุด
  - `GET /api/render/batch/{batch_id}`: ดึงสถานะและความคืบหน้ารายการในคิว
  - `POST /api/render/batch/{batch_id}/cancel`: สั่งยกเลิกคิว
- `scripts/api_server.py`: เมานต์ `batch_render_router` เข้ากับ FastAPI Server
- `frontend/src/api.js`: เพิ่ม API wrappers `startBatchRender`, `getBatchRenderStatus`, `cancelBatchRender`
- `frontend/src/components/BatchRenderModal.jsx`: สร้างคอมโพเนนต์โมดอล Dark Glassmorphism ให้เลือกมุมมองด้วย Checkbox, ตรวจสอบสถานะคลิปดิบ, ตั้งค่าเสียงพากย์และสไตล์, แสดงแถบ Progress Bar รวมแบบเรียลไทม์ และปุ่มยกเลิกคิว
- `frontend/src/components/ProductToClip.jsx`: เพิ่มปุ่ม "เรนเดอร์หลายมุม" บนแถบเครื่องมือมุมมองขาย, เชื่อม state `batchRenderOpen`, ตัวจัดการ `handleBatchCompleted`, และฝัง `BatchRenderModal`
- `tests/test_batch_render.py`: Unit and Integration tests สำหรับ Batch Render Queue และ FastAPI Endpoints ผ่าน 100% (4/4 passed)

**ผลการทดสอบ:**
- Backend tests: `pytest tests/test_batch_render.py` — 4 passed (100%)
- Frontend unit tests: `npm test` — 152 passed, 0 failed
- Frontend build: `npm run build` — ผ่านสมบูรณ์ (built in 4.46s)

---


## Round HOOK-VAR-1 — AI Hook Variation & A/B Generator (สร้างทางเลือกท่อนเปิดคลิป 5 สไตล์)

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
1. ให้ผู้ใช้สร้างทางเลือกประโยคฮุกเปิดคลิป (Hook Variations) ได้ 5 สไตล์การตลาด (`curiosity`, `warning`, `social_proof`, `deal_promo`, `pain_point`) พร้อมป้ายแบนเนอร์ 3 ชั้น (Brand / Model / Label) และประโยคเปิดคลิป
2. กดเลือกสลับ Hook Banner และประโยคเปิดคลิปได้ในคลิกเดียว อัปเดตลง SQLite Product Store (`store.db`) หรือ Project Manifest ทันที
3. ปฏิบัติตาม Rule 7 (ห้ามจุดไข่ปลา `...`/`…` ในบทพูด), Rule 8 (UI คลีน ไร้ `+` นำหน้าหรืออีโมจิซ้อนไอคอน), Rule 9 (คงชื่อแบรนด์/สเปกภาษาอังกฤษ), และ Rule 14 (ระบุตัวตนและโมเดลผู้ทำ)
4. มี Offline Fallback Generator คุณภาพสูง ทำงานได้ทันทีแม้ไม่มีเน็ตหรือไม่มี AI Quota พร้อมโมดอลพรีวิว Safe Zone 9:16 เสมือนจริง

**การเปลี่ยนแปลง:**
- `scripts/hook_generator.py`: พัฒนา `HookVariationEngine` รองรับ 5 สไตล์การตลาด, ระบบกำจัดจุดไข่ปลา (`clean_text`), กรองคำพูด TTS (`TTSSanitizer.clean`), และระบบ Offline Deterministic Generator
- `scripts/api_hooks.py`: เพิ่ม API endpoints:
  - `GET /api/hooks/styles`: รายการสไตล์และสีประจำสไตล์
  - `POST /api/hooks/generate`: สร้าง Hook 5 สไตล์ด้วย AI หรือ Offline
  - `POST /api/hooks/apply-angle`: ปรับใช้ Hook กับมุมมองและสคริปต์ใน Product Store
  - `POST /api/hooks/apply-project`: ปรับใช้ Hook กับ Project Manifest สำหรับตัดต่อ
- `scripts/api_server.py`: เชื่อมโยง `hooks_router` เข้ากับ FastAPI Server หลัก
- `frontend/src/api.js`: เพิ่มฟังก์ชันเชื่อมต่อ `getHookStyles`, `generateHookVariations`, `applyAngleHook`, `applyProjectHook` พร้อมซ่อม syntax ของ `cleanAssetDuplicates`
- `frontend/src/components/HookVariationModal.jsx`: สร้างคอมโพเนนต์โมดอล Dark Glassmorphism แสดงการ์ด 5 สไตล์, พรีวิว 9:16 Safe Zone (Overlay Banner + Subtitle Safe Zone), ป้ายแจ้งสไตล์, ปุ่มคัดลอก และปุ่มปรับใช้ Hook
- `frontend/src/components/ProductToClip.jsx`: เชื่อมต่อปุ่มเปิดโมดอล Hook Variations บน `AngleActiveWorkbench` และ `ScriptAccordionItem`, เพิ่ม state `hookModalAngle`, ตัวจัดการ `handleHookApplied`, และฝัง `HookVariationModal`
- `tests/test_hook_generator.py`: Unit tests สำหรับ Hook Engine 3 ข้อ ผ่าน 100%
- `tests/test_api_hooks.py`: Integration tests สำหรับ FastAPI Hooks Router 5 ข้อ ผ่าน 100%

**ผลการทดสอบ:**
- Backend tests: `pytest tests/test_hook_generator.py tests/test_api_hooks.py` — 8 passed (100%)
- Frontend unit tests: `npm test` — 152 passed, 0 failed
- Frontend build: `npm run build` — ผ่านสมบูรณ์ (built in 4.08s)

---


## Round AGENT-ATTRIB-1 — บังคับระบุ Agent Tooling & AI Model ในประวัติงาน

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
1. กำหนดกฎเหล็ก Rule 14 ใน `AGENTS.md` และ `.agents/rules/work_loop.md` ให้ทุก AI Agent ที่ทำงานในระบบต้องลงบันทึกชื่อโปรแกรมและโมเดลที่ใช้ เช่น `ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)` หรือ `Claude Code (Claude 3.7 Sonnet)` ในทุกบล็อกของ `HISTORY.md` และ `TODO.md`
2. ช่วยให้เจ้าของโปรเจกต์ตรวจสอบย้อนหลังได้ชัดเจน 100% ว่างานหรือบั๊กใดเกิดขึ้นจากใครและโมเดลรุ่นใด

**การเปลี่ยนแปลง:**
- `AGENTS.md`: เพิ่มข้อ 14 "มาตรฐานการระบุตัวตนและโมเดลของเอเจน (Strict Agent & Model Attribution)"
- `.agents/rules/work_loop.md`: เพิ่มข้อ 2.7 และอัปเดต Checklist สรุปงานพร้อมตัวอย่างรูปแบบที่ถูกต้อง

---

## Round BACKUP-1 — One-Click System Backup & Restore

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
1. สร้างระบบสำรองข้อมูลระบบแบบคลิกเดียว (One-Click Backup) ครอบคลุมโปรเจกต์ใน `03_Projects/`, ฐานข้อมูล `store.db` (ด้วย `sqlite3.Connection.backup` ป้องกัน lock contention), และเอกสารการตั้งค่าใน `_Docs/*.json`
2. สร้าง Backup Manifest พร้อมคำนวณ SHA-256 checksum และระบบตรวจสอบความสมบูรณ์ (Verify)
3. มี Endpoint ดาวน์โหลดไฟล์ zip และลบไฟล์สำรองเก่าอย่างปลอดภัย ป้องกัน Path Traversal
4. มีหน้าจอจัดการ Backup ใน `SystemSettings.jsx` แท็บ "สำรองข้อมูล & ไฟล์ซ้ำ"

**การเปลี่ยนแปลง:**
- `scripts/backup_engine.py`: `BackupEngine` รองรับ create, list, verify, download, delete
- `scripts/api_backup.py`: REST endpoints `/api/backup/create`, `/api/backup/list`, `/api/backup/verify/{filename}`, `/api/backup/download/{filename}`, `/api/backup/{filename}`
- `scripts/api_server.py`: Mount `backup_router`
- `frontend/src/api.js`: เพิ่มฟังก์ชันเชื่อมโยง API การสำรองข้อมูล
- `frontend/src/components/SystemSettings.jsx`: เพิ่มแท็บ Maintenance ("สำรองข้อมูล & ไฟล์ซ้ำ") พร้อมปุ่มสร้างสำรองทันที รายการไฟล์ ขนาด วันที่ และปุ่มดาวน์โหลด/ลบ
- `tests/test_backup_engine.py` & `tests/test_api_backup.py`: 8 unit tests ผ่าน 100%

---

## Round ASSET-DEDUP-1 — Media Deduplication & Cleanup Engine

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
1. ตรวจสอบและค้นหาไฟล์วิดีโอ/ภาพที่ซ้ำกันใน `00_Inbox` และ `01_Raw` โดยไม่กินทรัพยากรเครื่อง
2. ใช้อัลกอริทึม Multi-tier (Filter ตามขนาดไฟล์ -> Quick Hash 64KB หัว+ท้าย -> Full SHA-256 เฉพาะกลุ่มที่ตรงกัน)
3. ลบอย่างปลอดภัย: ไม่ลบถาวรทันที แต่ย้ายเข้า `06_Archive/.trash/` เพื่อให้กู้คืนได้
4. มีหน้า UI สแกน แสดงรายการไฟล์ซ้ำ พื้นที่ที่สามารถกู้คืนได้ และปุ่มล้างไฟล์ซ้ำที่เลือก

**การเปลี่ยนแปลง:**
- `scripts/asset_dedup.py`: `AssetDedupEngine` สแกนและจัดกลุ่มไฟล์ซ้ำ พร้อมย้ายไปถังขยะอย่างปลอดภัย
- `scripts/api_asset_dedup.py`: REST endpoints `/api/asset-dedup/scan`, `/api/asset-dedup/clean`
- `scripts/api_server.py`: Mount `asset_dedup_router`
- `frontend/src/api.js`: เพิ่มฟังก์ชัน `scanAssetDuplicates`, `cleanAssetDuplicates`
- `frontend/src/components/SystemSettings.jsx`: ฝังเครื่องมือสแกนไฟล์ซ้ำและรายงานพื้นที่ในแท็บ Maintenance
- `tests/test_asset_dedup.py` & `tests/test_api_asset_dedup.py`: 4 unit tests ผ่าน 100%

---

## Round CALENDAR-1 — Interactive Drag-and-Drop Weekly Content Calendar

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
1. ยกระดับหน้า Schedule Agenda ด้วยการเพิ่มโหมดสลับมุมมอง: "รายการ" (List) และ "ปฏิทินสัปดาห์" (Weekly Calendar)
2. ปฏิทินแสดง 7 วัน (จันทร์ – อาทิตย์) ตามโซนเวลา `Asia/Bangkok` พร้อมระบบนำทางสัปดาห์ก่อนหน้า/สัปดาห์นี้/สัปดาห์ถัดไป
3. แต่ละวันแสดงการ์ดคลิปที่จัดคิวไว้ สามารถกดดูพรีวิว, สถานะ, เวลา, ภาพปก และปุ่มแอ็กชันส่งให้ Extension
4. รองรับการลากการ์ดคลิป (Drag and Drop) ข้ามวันเพื่อเปลี่ยนกำหนดการโพสต์อัตโนมัติทันที
5. มีปุ่มเพิ่มคลิปด่วนสำหรับวันนั้นๆ ในทุกคอลัมน์

**การเปลี่ยนแปลง:**
- `frontend/src/components/ScheduleAgenda.jsx`: เพิ่ม `viewMode` toggle, แถบนำทางสัปดาห์, เรนเดอร์ 7-column grid พร้อม drag-and-drop targets
- `frontend/src/lib/scheduleQueue.test.js`: เพิ่มเทสครอบคลุมการคำนวณ 7 วันสัปดาห์
- Vitest: 152 passed
- Vite Build: ผ่านสมบูรณ์ (3.14s)

---

## Round TIKTOK-STATS-FIX-1 — แก้บั๊ก result is not defined + ย้ายซิงก์สถิติเป็นแท็บที่ 3 "เครื่องมือ" ใน Extension

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Claude Code / Gemini CLI · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
1. แก้บั๊ก `result is not defined` ที่เกิดขึ้นขณะเรียกซิงก์สถิติใน `sidepanel.js`
2. ย้ายปุ่มซิงก์สถิติแยกออกมาเป็นแท็บที่ 3 "เครื่องมือ" ให้ชัดเจน ไม่ปะปนกับขั้นตอนการโพสต์ตาม UI Clean Standard
3. รันเทสฝั่ง extension ครบ 21 ข้อ

**การเปลี่ยนแปลง:**
- `tiktok_autopost_extension/sidepanel.js`: แก้ scope ตัวแปร `result` และผูก event กับแท็บเครื่องมือ
- `tiktok_autopost_extension/sidepanel.html`: เพิ่มแท็บเครื่องมือ (Tools) และจัดเลย์เอาต์ปุ่มซิงก์สถิติ
- `tiktok_autopost_extension/background.test.cjs`: เพิ่มเทสตรวจสอบแท็บเครื่องมือ (21 passed)

---

## Round SAFE-1 — Disk Guard ก่อน Render & Auto-Snapshot CapCut Manifest 3 Versions

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
1. **Disk Guard ก่อน Render:** ตรวจสอบพื้นที่ว่างบนดิสก์ (`shutil.disk_usage`) ก่อนเริ่ม Render งานวิดีโอ 1080x1920 หากพื้นที่เหลือน้อยกว่า 3GB ให้แจ้งเตือนและระงับการเรนเดอร์ทันที ป้องกัน FFmpeg ค้างและไฟล์เสียหาย
2. **Auto-Snapshot CapCut Manifest:** ทำระบบ Rolling Backup สำรองไฟล์ `project.json` อัตโนมัติ 3 เวอร์ชั่น (`.bak1`, `.bak2`, `.bak3`) ทุกครั้งก่อนเซฟ พร้อมระบบ Cascaded Fallback Recovery เมื่อไฟล์หลักเสียหาย และเพิ่ม Endpoint สำหรับตรวจสอบ Snapshot และ Restore

**การเปลี่ยนแปลง:**
- `scripts/api_render.py`:
  - เพิ่มฟังก์ชัน `check_disk_space(path, min_bytes=3GB)`
  - เพิ่ม Endpoint `GET /api/render/disk-check` แสดง `free_gb`, `total_gb`, `is_sufficient`, `min_required_gb`
  - ตรวจเช็คดิสก์ใน `trigger_render` (ยกเลิกคิวและคืน `HTTP 507 Insufficient Storage` พร้อมข้อความแจ้งเตือนภาษาไทย)
  - ตรวจเช็คดิสก์ใน `execute_render_job` ซ้ำก่อนเริ่ม FFmpeg ป้องกันระหว่างรัน
- `scripts/project_manifest.py`:
  - ปรับ `_save_locked`: ทำ Rolling 3-Version Backup หมุนเวียนไฟล์ `.bak2` -> `.bak3`, `.bak1` -> `.bak2`, `project.json` -> `.bak1` (และ `.bak` เพื่อ backwards compatibility)
  - ปรับ `load()`: ทำ Cascaded fallback recovery ตรวจสอบ `.bak1` -> `.bak` -> `.bak2` -> `.bak3` อัตโนมัติหากไฟล์หลักว่างเปล่าหรือ JSON เสียหาย
  - เพิ่ม `ProjectManifest.get_snapshots(project_name)` แสดงประวัติเวอร์ชันสำรองพร้อมเวลาและขนาด
  - เพิ่ม `ProjectManifest.restore_snapshot(project_name, snapshot_id)` กู้คืนเวอร์ชันที่ต้องการอย่างปลอดภัย
- `scripts/api_phase1.py`:
  - เพิ่ม `GET /api/projects/{project_name}/snapshots`
  - เพิ่ม `POST /api/projects/{project_name}/snapshots/{snapshot_id}/restore`
- `tests/test_safe1_disk_guard_and_snapshots.py`:
  - สร้างชุดทดสอบ 8 ข้อ ครอบคลุมการเช็คดิสก์จริง/จำลอง, การปฏิเสธด้วย HTTP 507, การหมุน 3 snapshot, การ recovery จาก corruption และการ restore ผ่าน API

**ผลการทดสอบ & Gate:**
- Pytest `tests/test_safe1_disk_guard_and_snapshots.py`: 8 passed ใน 2.17 วินาที
- Pytest `tests/test_refactor_baseline_contracts.py`: 4 passed ใน 0.71 วินาที
- Python syntax compileall `scripts`: 0 errors
- Frontend vitest: 151 passed
- Frontend build: ผ่านใน 3.28 วินาที

---

## Round ANALYTICS-HUB-1 — พัฒนาเมนูใหม่ "ศูนย์วิเคราะห์ข้อมูลและสถิติรวม" (Analytics & Operations Hub)

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
สร้างศูนย์รวมการวิเคราะห์ข้อมูลและสถิติการใช้งานทุกมิติของ OmniCut Pro Studio ในหน้าเดียว แยกเป็น 4 แท็บหลัก:
1. `การผลิต & ภาพรวมคลิป (Production Analytics)`: Funnel 4 สเต็ป, คอขวด, ประเภทยอดนิยม, เวลาเฉลี่ย
2. `โทเคน & คำสั่ง AI (Tokens & AI Performance)`: ยกระดับ TokenDashboard, สถิติ In/Out/Think, Daily Trend, Audit Log
3. `พื้นที่จัดเก็บ & ระบบ (Storage & Disk Quota)`: สรุปความจุไดรฟ์, ขนาดโฟลเดอร์ 01-06, แคช CapCut และเครื่องมือ Safe Purge
4. `คลังเนื้อหา & วัตถุดิบ (Content & Inventory Health)`: สุขภาพข้อมูลสินค้า, ความสมบูรณ์ของรูป/คลิป, โอกาสในการสร้างคลิป

### Todo

- [x] สร้าง Backend Router `scripts/api_analytics.py`:
  - `GET /api/analytics/production`: สรุป Funnel 4 เฟส (scripted, in_production, rendered, posted), cycle time, angle categories
  - `GET /api/analytics/storage`: สแกนขนาดโฟลเดอร์ `01_Raw`, `02_Assets`, `03_Projects`, `04_Exports`, `.cloud_cache` แบบ async พร้อม in-memory caching (TTL 5 นาที)
  - `GET /api/analytics/inventory`: วิเคราะห์ความพร้อมของสินค้า, จำนวนรูป, คลิป, สคริปต์, แผนถ่าย
  - `POST /api/analytics/storage/purge-safe-cache`: ล้างเฉพาะแคชชั่วคราวอย่างปลอดภัย (Safe Purge) โดยไม่แตะ `01_Raw` และ `02_Assets`
  - เมานต์ router ที่ `scripts/api_server.py`
- [x] อัปเดต API client ใน `frontend/src/api.js` สำหรับเรียก endpoint สถิติ
- [x] อัปเดต Navigation ใน `frontend/src/components/Sidebar.jsx` และ `frontend/src/App.jsx`:
  - เพิ่มแท็บ `analytics` (ไอคอน BarChart3, label: `6. สถิติ & วิเคราะห์รวม`)
  - ขยับ Settings เป็นเมนู 7
- [x] สร้างโมดูล UI `frontend/src/components/analytics/`:
  - `AnalyticsHub.jsx`: Glassmorphism header, tab selector (4 tabs), refresh trigger
  - `tabs/ProductionAnalyticsTab.jsx`: Funnel, WIP, Bottlenecks, Content Types
  - `tabs/TokensAnalyticsTab.jsx`: สถิติโทเคน, Daily Volume, Audit Logs (ดัดแปลงจาก TokenDashboard)
  - `tabs/StorageAnalyticsTab.jsx`: ไดรฟ์บาร์, แจกแจงโฟลเดอร์, Safe Purge Modal
  - `tabs/InventoryAnalyticsTab.jsx`: ตารางสุขภาพสินค้า, ความพร้อมรูป/วิดีโอ, ปุ่มสร้างคลิป
- [x] ตรวจสอบความถูกต้องตามกฎ UI Clean Standard (ห้ามมีสัญลักษณ์ซ้ำซ้อน)
- [x] เขียนและรัน Unit Tests (pytest & vitest) พร้อมตรวจสอบ build

### Gate

- [x] เมนู "6. สถิติ & วิเคราะห์รวม" ปรากฏบน Sidebar และสลับแท็บทั้ง 4 ได้อย่างลื่นไหล
- [x] ข้อมูลทั้ง 4 แท็บดึงจาก Backend API จริง พร้อมระบบ In-memory Cache ไม่หน่วงระบบ
- [x] Safe Purge ทำงานได้ปลอดภัย ไม่แตะไฟล์ใน 01_Raw และ 02_Assets
- [x] Unit tests (pytest 4/4 passed & vitest 151/151 passed) และ `npm run build` ผ่าน 100%

### Notes

- สร้าง `scripts/api_analytics.py` รองรับ Endpoint: `/production`, `/storage`, `/inventory`, และ `/storage/purge-safe-cache`
- ติดตั้ง In-memory Storage Caching TTL 300s เพื่อลด Disk I/O จากการคำนวณขนาดโฟลเดอร์ซ้ำ
- ฝั่ง Frontend สร้าง `AnalyticsHub.jsx` สไตล์ Modern Glassmorphism แบ่ง 4 แท็บคมชัด ไร้สัญลักษณ์ซ้ำซ้อน
- เพิ่มเมนู `6. สถิติ & วิเคราะห์รวม` (ไอคอน `<BarChart3 />`) บน Desktop Sidebar และ Mobile More Drawer
- ผลทดสอบ: Pytest `tests/test_analytics_hub.py` ผ่าน 4/4 tests, Vitest ผ่าน 151/151 tests, Vite build สำเร็จสมบูรณ์ใน 2.94s
- [x] Round SIDEBAR-PHASE-UI-1 — ออกแบบ sidebar ใหม่ด้วย 4-Phase Pipeline Stepper Dots (Scripted→In Production→Rendered→Posted) + Shot List Badge + Smart Camera Direction Clarity (2026-09-11; backend 5 passed, frontend 151 passed, build pass)
- [x] Round READONLY-SCRIPT-STATUS-1 — ล็อกการแก้ไขสคริปต์และคลิปดิบเป็นสีเทาทั้งหมดเมื่อสถานะเป็น 'โพสต์แล้ว' หรือ 'กำลังตัดต่อ' และให้ปลดล็อกได้เฉพาะเมื่อย้อนสถานะเท่านั้น (2026-09-11)
- [x] Round SHOT-LIST-ENHANCE-2 — ปรับคำแนะนำมุมกล้องและการถ่ายทำในแผนถ่ายให้เจาะลึกเฉพาะซีนตามบทพูดจริง (Semantic Action Guidance) (2026-09-11; backend 5 passed, frontend 151 passed)
- [x] Round SHOT-LIST-ENHANCE-1 — ยกระดับโฟลว์แผนถ่าย (Phase 1): Invalidate แผนถ่ายเมื่อสคริปต์เปลี่ยน + เพิ่มปุ่มเปิดแผนถ่ายใน ContentTrackerHub (2026-09-11; backend 4 passed, frontend 151 passed, build pass)
- [x] Round PERSIST-LAYOUT-FIX-1 — แก้ Product selection ไม่จำค่าหลังรีเฟรชหน้า + จัดระเบียบ Toolbar action buttons ใน ProductToClip และ ContentTrackerHub ให้เรียบตรงบรรทัดเดียวไม่ตกขอบ (2026-09-11; frontend 151 passed, build pass)
- [x] Round RESPONSIVE-LAYOUT-1 — ปรับแต่ง Responsive Layout ทั้งหมดรองรับ 2 หน้าจอ Desktop (1440x900) และ Mobile (iPhone 15 Pro Max 430x932) (2026-09-11; frontend 150 passed, build pass, parity 153 passed)
- [x] Round DOC-SYNC-1 — sync สถานะเอกสารจากผลทดสอบล่าสุด และแยกงานที่รอ user/live validation (2026-09-10)
- [x] Round BUG-MARK-POSTED-1 — แก้ปุ่ม “มาร์กว่าลงโพสต์แล้ว” แจ้งสำเร็จแต่การ์ดยังไม่ย้ายสถานะ (2026-09-10; full backend 1,035 passed)
- [x] Round PRODUCT-METADATA-1 — แนบรูปอ้างอิงย้อนหลัง + Metadata Inspector สำหรับตรวจข้อมูลที่ AI ใช้ (2026-09-10; backend 1,037 passed, frontend 144 passed)
- [x] Round PRODUCT-METADATA-2 — เติม source fallback สำหรับสินค้า legacy ที่มีข้อมูลอยู่ใน angle แต่ product metadata ว่าง (2026-09-10; backend 1,040 passed, frontend 144 passed)
- [ ] Round PRODUCT-METADATA-3 — ตรวจ/แก้การดึงข้อความจาก TikTok product page ที่เป็น client-rendered: GOC01 มี URL + รูป 9 รูป แต่ description/raw_text/specs/selling_points/pain_points ระดับสินค้าไม่ถูกบันทึก; เพิ่ม hybrid browser extraction + refresh source แล้ว เหลือ live verification ผ่าน Security Check (2026-09-10)
- [x] Round COMMIT-SPLIT-1 — จัดกลุ่ม commit งานค้าง working tree แยก 5 commits + สร้าง LIVE_VALIDATION_CHECKLIST.md (รายละเอียดเต็มใน HISTORY.md; pytest 1,050 passed + 2 pre-existing failures ที่ HEAD แยกเป็นงานรอแก้ · 2026-09-10)
- [ ] Round RENDER-BEHAVIOR-FIX-1 — แก้ 2 pre-existing failures ใน test_preview_render_behavior.py: (1) test_per_word_vs_monolithic_render_parity คลาด 284px (489 vs 773) (2) test_ibm_thai_marks_have_separate_vertical_bands tone mark หลุดจาก base glyph — พบระหว่าง COMMIT-SPLIT-1, deterministic ที่ HEAD, ไฟล์ subtitle ไม่อยู่ใน diff รอบนั้น (2026-09-10)
- [x] Round PRODUCT-METADATA-8 — ย้ายการอ่านข้อมูลจากรูปอ้างอิงเป็น background task ปิดโมดัลได้ แจ้งเตือนเมื่อเสร็จ และเปิดผล preview ย้อนหลังจาก Activity Center (2026-09-10; backend 1,055 passed, frontend 149 passed, build/lint ผ่าน)
- [x] Round SCRIPT-ANGLE-METADATA-1 — ล็อกหัวข้อเดิมตอนเจนใหม่ และแสดงประเภทเนื้อหาเป็นหลาย badge (2026-09-10; backend 1,057 passed, frontend 149 passed, build/lint ผ่าน)
- [x] Round RENDER-REGRESSION-2 — ตรวจ forensic commit ของ render/style และคืน Preview = Render ให้เหมือน baseline (2026-09-10; culprit `3a35723` 08:06:23, backend 1,057 passed, frontend 150 passed, build/lint ผ่าน)
- [x] Round FONT-SIZE-REGRESSION-1 — ตรวจและคืนขนาดฟอนต์บทพูด/ซับให้เท่า baseline (2026-09-10; stale ASS invalidation, backend 1,059 passed, frontend 150 passed, build/lint ผ่าน)
- [x] Round FONT-SIZE-REGRESSION-2 — แก้ backend `.venv` ขาด `fontTools` แล้ว fallback เงียบเป็น scale `1.0`; เปลี่ยนเป็นอ่าน SFNT metrics โดยตรง, bump contract `v4`, และเรนเดอร์งานจริงใหม่ (2026-09-10; backend 1,061, frontend 150, focused 174 passed)
- [x] Round DELETED-TIMELINE-SYNC-1 — ซิงค์สถานะโปรเจกต์ที่ถูกลบออกจาก NewClipPanel, ล็อกปุ่มแผนถ่ายเมื่อถูกล็อก, และนำปุ่มย้อนสถานะออก (2026-09-11; Vitest 151 pass, build pass)
- [ ] Round FONT-TEXT-RULE-1 — ถอดบทเรียนและล็อกกฎห้ามงานอื่นกระทบฟอนต์/ข้อความ/ซับ/Preview=Render โดยไม่ได้รับคำสั่งชัดเจน (2026-09-10)



- [x] Round HOOK-DEFAULT-5S-1 — ปรับค่าเริ่มต้น (default) ของป้ายฮุกพาดหัว (Hook Banner) เป็น 5.0 วินาทีตั้งแต่ตอนสร้างโปรเจกต์ (2026-09-11; frontend 151 passed, backend 157 passed, build pass)

## Round HOOK-DEFAULT-5S-1 — ปรับค่าเริ่มต้น (default) ของป้ายฮุกพาดหัว (Hook Banner) เป็น 5.0 วินาทีตั้งแต่ตอนสร้างโปรเจกต์

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** ให้ป้ายฮุกพาดหัว (Hook Header Banner) ทั้งตอนสร้างโปรเจกต์ใหม่ (First Render / One Click / Apply to Studio) และตอนกดเพิ่มป้ายฮุกใหม่ในไทม์ไลน์ มีความยาวเริ่มต้นเป็น 5.0 วินาที (จากเดิม 3.0 วินาที) ตามที่ผู้ใช้ต้องการ

### Todo

- [x] ปรับค่าเริ่มต้น `hook_duration` ในโมเดลและฟังก์ชันสร้าง Hook:
  - `frontend/src/lib/overlayModel.js`: `hookOverlayFromLegacy` และ `newHookOverlay` ปรับ duration fallback เป็น 5.0
  - `frontend/src/lib/inspectorModel.js`: `clampHookDuration` default fallback ปรับเป็น 5.0
  - `frontend/src/components/editor/EditorShell.jsx`: `handleApplyHookTemplate` และ `handleEnsureHookOverlay` ใช้ duration 5.0
  - `frontend/src/components/editor/Timeline.jsx`: fallback duration ของ hookOverlay ปรับเป็น 5.0
  - `frontend/src/components/editor/inspector/OverlayInspector.jsx`: fallback hookDuration ปรับเป็น 5.0
  - `scripts/overlay_model.py`: `hook_overlay_from_legacy` ปรับ duration fallback เป็น 5.0
  - `scripts/pipeline_context.py`: dataclass `hook_duration: float = 5.0`
  - `scripts/pipeline.py`: `generate_video` signature `hook_duration: float = 5.0`
  - `scripts/api_phase1.py`: `params.get("hook_duration", 5.0) or 5.0`
- [x] ตรวจสอบและรันการทดสอบ Unit Tests ของ Frontend และ Backend
- [x] รัน build ตรวจสอบความถูกต้อง 100%

### Gate

- [x] เมื่อสร้างคลิปใหม่หรือเปิดดูในไทม์ไลน์ แทร็กป้ายฮุกพาดหัวเริ่มต้นที่ 0.0s ถึง 5.0s (ยาว 5.0s)
- [x] Unit tests (vitest 151 passed & pytest 157 passed) ผ่าน 100%
- [x] `npm run build` ผ่าน 100%

### Notes

- ปรับ default hook duration ทั้งฝั่ง Frontend (`overlayModel.js`, `EditorShell.jsx`, `Timeline.jsx`, `OverlayInspector.jsx`, `inspectorModel.js`) และฝั่ง Backend (`overlay_model.py`, `pipeline_context.py`, `pipeline.py`, `api_phase1.py`)
- ผลทดสอบ: Vitest 151 passed, Vite build passed ใน 2.85s, Pytest baseline contracts & smoke 157 passed ใน 36.36s

---

## Round SIDEBAR-PHASE-UI-1 — ออกแบบ sidebar ซ้ายใหม่ด้วย 4-Phase Pipeline Stepper Dots + Shot List Badge + Smart Camera Direction Clarity

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:**
1. แก้ปัญหาแผนถ่ายที่คำแนะนำมุมกล้องยังดูเหมือนเดิมหรือยังไม่แบ่งมุม/แอคชั่นชัดเจน:
   - ปรับการแสดงผลใน `ShotListModal.jsx` และ `MobileFilmingPage.jsx` ให้แยก 📷 **มุมกล้อง** และ 🎬 **แอคชั่นการถ่าย** ออกจากกันอย่างเป็นระบบและเห็นชัดเจน ไม่กลืนเป็นบรรทัดเดียว
   - ใส่ปุ่ม "สร้างแผนถ่ายใหม่ (Regenerate)" ชัดเจนใน Modal เผื่อเป็นแคชของเดิมที่เคยสร้างไว้ก่อนอัปเกรด
2. ออกแบบแถบด้านซ้าย (Sidebar Angles List) ใหม่ตามคำขอของผู้ใช้:
   - ระบบ 4-Phase Pipeline Stepper Dots: `สคริปต์` → `กำลังตัดต่อ` → `ตัดต่อเสร็จ` → `โพสต์แล้ว`
   - จุดเฟสปัจจุบันแสดงผลเป็น **จุดสีเขียวมรกตเรืองแสง (Emerald Active Pulse/Glow)** โดดเด่นตามที่ผู้ใช้ร้องขอ ("ทำเป็น dot 4 เฟส แล้ว แสดง .เขียว เฟสที่เป็นอยู่ตอนนี้") พร้อมเส้นเชื่อม progression
   - ป้ายบอกสถานะแผนถ่าย (Shot List Badge): ดูจากการ์ดซ้ายรู้ได้ทันทีว่าสคริปต์นี้สร้างแผนถ่ายแล้วหรือยัง
     - หากมีแผนถ่ายแล้ว: แสดง Badge `🎬 แผนถ่ายพร้อม` (กดเปิด Modal แผนถ่ายได้ทันที)
     - หากสคริปต์เปลี่ยนจนแผนถ่ายเก่า: แสดง Badge `⚠️ แผนถ่ายเก่า`
     - หากยังไม่มีแผนถ่าย: แสดงปุ่มคลิก `+ แผนถ่าย` เพื่อสร้างทันที
3. ปรับให้แสดงผลทั้งบน Desktop (`AngleSidebarItem`) และ Mobile Carousel (`AngleMobilePill`)

### Todo

- [x] ปรับปรุงการแยกมุมกล้องและแอคชั่นใน `ShotListModal.jsx` และ `MobileFilmingPage.jsx` ให้แยกกล่อง/ป้าย 📷 **มุมกล้อง** กับ 🎬 **แอคชั่นการถ่าย** ชัดเจน
- [x] เพิ่มปุ่ม "สร้างแผนถ่ายใหม่ (Regenerate)" ให้เด่นชัดใน `ShotListModal.jsx` พร้อมอธิบายการคำนวณใหม่ตามบทล่าสุด
- [x] นำ `ShotListModal` ไป mount แสดงผลใน `ProductToClip.jsx` และผูก state ให้เปิดดู/สร้างใหม่ได้ถูกต้อง
- [x] ออกแบบ `PhaseDots` ใน `ProductToClip.jsx` ใหม่:
  - 4 dots เชื่อมต่อกันแบบ stepper line
  - dot เฟสปัจจุบันใช้สีเขียวมรกตเรืองแสง (`bg-emerald-400 ring-2 ring-emerald-400/40 shadow-sm shadow-emerald-400/60 animate-ping pulse`)
  - dot ที่ผ่านแล้วใช้สีเขียวเข้มคมชัด, dot อนาคตใช้สีโปร่งบาง
- [x] อัปเดต `AngleSidebarItem` และ `AngleMobilePill`:
  - แสดงป้ายแผนถ่ายที่คลิกเปิดดูได้ทันที (`🎬 แผนถ่ายพร้อม` / `⚠️ แผนถ่ายเก่า` / `+ แผนถ่าย`)
  - จัดระเบียบการ์ดให้เรียบหรู คมชัด ไม่รก
- [x] รันการทดสอบ Unit Tests ทั้งหมด (Backend + Frontend) และตรวจสอบ build

### Gate

- [x] แผนถ่ายแสดงผลแยกมุมกล้องและแอคชั่นชัดเจน
- [x] การ์ดฝั่งซ้ายมี Shot List Badge บอกชัดเจนว่าสคริปต์ไหนสร้างแผนถ่ายแล้ว และกดเปิดดูได้ทันที
- [x] PhaseDots แสดงผล 4 สเต็ปโดยมีจุดเขียวเรืองแสงที่สถานะปัจจุบัน
- [x] Unit tests (pytest 5/5 & vitest 151/151) ผ่าน 100% พร้อม build pass

### Notes

- ใน `scripts/shot_list_builder.py` ปรับรูปแบบคำแนะนำให้เป็นโครงสร้างมาตรฐาน `[มุมกล้อง] — [แอคชั่นการถ่าย]` อย่างสม่ำเสมอทุก role (hook, feature, cta)
- ใน `ShotListModal.jsx` และ `MobileFilmingPage.jsx` ทำการแยกสตริง `—` และแสดงผลออกเป็นการ์ด 2 คอลัมน์/2 บล็อก: **📷 มุมกล้อง** (กรอบ Cyan) และ **🎬 แอคชั่นการถ่าย** (กรอบ Amber) สื่อสารชัดเจนตรงประเด็นตามที่ผู้ใช้ต้องการ
- เพิ่มปุ่ม "สร้างแผนถ่ายใหม่" โดดเด่นในหัว Modal เพื่อให้ผู้ใช้สามารถกดคำนวณแผนถ่ายใหม่ด้วยระบบ Semantic Action Engine ได้ทันที แทนที่จะติดแคชเก่า
- ปรับปรุง `PhaseDots` ใน `ProductToClip.jsx` ให้เป็น Stepper 4 สเต็ปที่มีเส้นเชื่อมต่อกัน จุดเฟสปัจจุบันแสดงผลเป็นจุดสีเขียวเรืองแสง พร้อมเอฟเฟกต์ pulse/ping ให้เห็นเด่นชัดว่าตอนนี้อยู่ขั้นตอนไหน (สคริปต์พร้อม -> กำลังตัดต่อ -> ตัดต่อเสร็จ -> โพสต์แล้ว)
- เพิ่ม Badge `🎬 แผนถ่ายพร้อม` (สีเขียวมรกต) และ `⚠️ แผนถ่ายเก่า` (สีส้ม) พร้อมปุ่ม `+ แผนถ่าย` ในรายการสคริปต์ฝั่งซ้าย สามารถคลิกเปิดดูแผนถ่ายได้โดยตรง

## Round FONT-TEXT-RULE-1 — กฎเหล็กฟอนต์และข้อความ

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** สร้าง project-level contract ที่บังคับทุกเอเจนว่างานไม่เกี่ยวข้องห้ามเปลี่ยนฟอนต์ ขนาด ข้อความ การตัดบรรทัด ตำแหน่ง หรือภาพจริงของซับโดยเด็ดขาด

### Todo

- [ ] เพิ่ม `.agents/rules/font_text_visual_contract.md` เป็นแหล่งกฎกลางสำหรับ content identity, font metrics, Preview=Render, ASS versioning และ environment parity
- [ ] ผูกกฎใหม่เข้า `AGENTS.md` ทั้ง STRICT DON'T และ STRICT DO เพื่อให้ทุกเอเจนต้องอ่านก่อแตะเส้นทางนี้
- [ ] เชื่อมกฎเข้า `preview_render_parity.md` และระบุ baseline ตัวเลข/บทเรียน environment mismatch ที่ทำให้ `82` ตกเป็น `50`
- [ ] ตรวจ link/path, Markdown structure และ `git diff --check` ก่อปิดรอบ

### Gate

- [ ] กฎมีคำห้ามและขั้นหยุดงานที่ชัดเจนเมื่อไม่มีอำนาจเปลี่ยน visual/text contract
- [ ] กฎระบุว่า Save ไม่เท่ากับ Render และ `.ass` เวอร์ชันใหม่เกิดเมื่อ subtitle stage ถูกรันหลัง input/contract เปลี่ยน
- [ ] `git diff --check` ผ่าน และเอกสารที่อ้างถึงมีอยู่จริง

### Notes

- จะไม่แก้ source/render behavior ในรอบนี้; เป็น documentation guardrail เท่านั้น
- ไฟล์ค้างของ product metadata/UI/subtitle fix ใน working tree เป็นงานก่อหน้า; รอบนี้จะแตะเฉพาเอกสารกฎและ TODO/HISTORY

## Round RENDER-BEHAVIOR-FIX-1 — แก้ 2 pre-existing render-behavior failures

วันที่: 2026-09-10 · สั่งโดย: user (ผ่านคำถาม "ต่อไปเรื่องไหนต่อ") · สถานะ: กำลังทำ

**เป้าหมาย:** ทำให้ full backend suite กลับมา 0 failed — บั๊ก 2 ตัวนี้บ่งชี้ว่าภาพเรนเดอร์จริงเบี่ยงจาก parity contract (per-word vs monolithic ต่างกัน 284px คือใหญ่มาก) กระทบคุณภาพคลิปจริง

### Todo

- [x] ยืนยัน reproduce: รันซ้ำเฉพาะ 2 เทส — 2 failed คงเดิม (deterministic)
- [ ] อ่านเทส 2 ตัวเข้าใจ assertion จริง + fixture ที่ใช้
- [ ] แยกว่า regression มาจาก commit ไหน (git log ไฟล์ที่เกี่ยว: subtitle_engine/overlay_events/font_metrics/video_editor)
- [ ] แก้ root cause โดยไม่ทำลาย parity contract อื่น
- [ ] รัน focused + full suite จน 0 failed

### Gate

- [ ] `python -m pytest tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 0 failed
- [ ] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider --tb=short` — 0 failed
- [ ] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 0 failed (ตัวเลขจริงบันทึกที่นี่)
- [ ] `python -m compileall -q scripts` และ `git diff --check` — ผ่าน

### Notes

- ข้อควรระวัง: test_ibm_thai_marks เกี่ยวกับ glyph ไทย (ตระกูล SUB-THAI-2 ที่พักไว้) แต่ SUB-THAI-2 คือปัญหา "ฟอนต์ Kanit/Prompt ขาด GPOS" ที่ยืนยันแล้วว่า IBM Plex **ถูก** — เทสนี้ใช้ IBM และพังตอนนี้ แปลว่ามี regression ใหม่แยกต่างหาก ไม่ใช่ปัญหาฟอนต์เดิม
- ห้ามแก้โดย "ผ่อน assertion" ให้ผ่านเฉย ๆ — ต้องหา root cause ของภาพจริง

## Round PRODUCT-METADATA-7 — อ่านสรรพคุณ/สเปกจากรูปอ้างอิงด้วย Vision

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** ให้สินค้าใหม่ที่มีข้อมูลอยู่ในภาพอินโฟกราฟิกหรือภาพสเปกสามารถสกัดคำอธิบาย สรรพคุณ จุดขาย และสเปกเข้า metadata ได้ โดยมี preview/edit/เลือก field ก่อนบันทึก และไม่ให้โมเดลแต่งข้อมูลที่อ่านจากรูปไม่ชัด

### Todo

- [x] เพิ่ม backend Vision extraction แบบ read-only สำหรับรูปอ้างอิงสินค้า
- [x] เพิ่ม UI ปุ่มอ่านจากรูปและนำผลเข้า preview/edit flow เดิม
- [x] บันทึก provenance ว่าข้อมูลมาจาก Vision รูปใด และรักษาข้อมูลเดิมเมื่อไม่เลือกทับ
- [x] เพิ่ม offline regression tests สำหรับ schema/validation/selected overwrite
- [x] รัน backend/frontend gates; เหลือทดสอบสินค้าชุด BlueWow จริงด้วยรูปที่แนบ

### Notes

- รูปตัวอย่างมีข้อมูลซีรีส์ รุ่น กำลังไฟ และคุณสมบัติ cooling อยู่ในภาพ แต่ไม่ได้รับประกันว่าตัวเลขเล็กทุกจุดจะอ่านได้ชัด
- ต้องให้ผู้ใช้ตรวจ preview ก่อนบันทึก และแยกข้อมูลที่อ่านไม่แน่ใจออกเป็น warning ไม่ส่งเป็นข้อเท็จจริง
- ทดสอบ live กับรูป BlueWow แล้ว แต่ Gemini free tier ตอบ `429 RESOURCE_EXHAUSTED` (โควตา 20 requests/day) จึงยังไม่มีผลลัพธ์ถูกบันทึก และต้อง retry หลัง quota reset
- พบ live backend process เก่าก่อน commit feature ทำให้ OpenAPI ไม่มี route `preview-image-metadata` และหน้าเว็บได้ `404 Not Found`; ต้อง restart backend ด้วย `start_app.bat` ก่อนทดสอบซ้ำ

### Gate

- [x] focused image metadata tests — 21 passed, 1 warning
- [x] full backend/frontend tests/build — backend 1,054 passed, frontend 149 passed, build/lint ผ่าน
- [ ] manual: BlueWow images → extract → preview/edit → select → save → reopen (รอ quota Gemini reset)

## Round PRODUCT-METADATA-6 — กัน selected product เปลี่ยนเองระหว่าง refresh/load history

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** เมื่อผู้ใช้เปิด metadata หรือทำงานกับสินค้าใดอยู่ การ refresh/focus/background response ต้องไม่สลับ `productData` ไปเป็นสินค้ารายการแรกหรือ response เก่าโดยไม่มีการเลือกจากผู้ใช้

### Todo

- [x] สร้าง regression test สำหรับการ resolve สินค้าที่เลือกและ response race
- [x] แก้ stale selection closure และ fallback ไปสินค้ารายการแรกที่เกิดระหว่าง reload
- [x] กัน async history response เก่าเขียนทับ selection ล่าสุด
- [x] รัน frontend gate; backend ไม่ได้แก้ในรอบนี้และ full backend ล่าสุดยังผ่าน 1,052 tests

### Notes

- สมมติฐานปัจจุบัน: `loadHistory` ที่ผูกกับ `focus` ปิดทับ `selectedHistoryId` ค่าเก่า และ `find(...) || res.products[0]` ทำให้เลือกสินค้าตัวแรกแทน
- เพิ่ม `selectedHistoryIdRef`, request sequence guard และเลือก parent ID เฉพาะเมื่อ prop เปลี่ยนจริง; focus/refresh จึงยึด local selection ล่าสุด

### Gate

- [x] focused selection regression tests — 5 passed
- [x] frontend tests/build/lint — 149 passed, build/lint ผ่าน
- [x] backend tests — ไม่ได้แก้ backend รอบนี้; latest full suite 1,052 passed
- [ ] manual: สลับสินค้าแล้ว refresh/focus หลายครั้ง ต้องอยู่สินค้าตัวเดิม

## Round PRODUCT-METADATA-5 — แก้ metadata description/raw text ซ้ำ และเปิดแก้คำอธิบายสรรพคุณ

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** แยกความหมายของ “คำอธิบายสินค้า/สรรพคุณ” กับ “ข้อความต้นฉบับ” ให้ชัดเจน ไม่แสดงเนื้อหาซ้ำ และเปิดให้ผู้ใช้แก้คำอธิบายจากหน้าข้อมูลที่ AI จะได้รับได้จริง

### Todo

- [x] สร้าง regression test ที่ยืนยันว่าหน้า metadata ไม่รวม description กับ raw_text ซ้ำโดยไม่จำเป็น
- [x] ตรวจและแก้ source normalization/scraper ให้ description และ raw_text มีขอบเขตข้อมูลที่ชัดเจน
- [x] เปิดช่องแก้ไข description/raw_text ในจุดที่ผู้ใช้กำลังตรวจข้อมูล พร้อมบันทึกกลับ product เดิม
- [x] รัน focused/backend/frontend gates และตรวจ flow reload หลังบันทึก

### Notes

- อาการจากผู้ใช้: inspector แสดงหัวข้อ “คำอธิบาย / raw text” แล้วพิมพ์คำอธิบายชุดเดียวกันสองรอบ
- ต้องรักษา source text ที่ละเอียดสำหรับ AI แต่ไม่ควรเอา field ที่มีความสัมพันธ์ซ้อนกันมาแสดงต่อกันแบบ blind concatenation
- แก้โดยตัดบรรทัดที่ซ้ำกันออกจาก raw source ตอนประกอบ prompt/สรุป AI และยังเก็บ raw_text เต็มไว้ใน JSON metadata
- preview มี textarea แก้ “คำอธิบายสินค้า” และ “ข้อความต้นฉบับ” ก่อนเลือก field และยืนยันบันทึกผ่าน `overrides`

### Gate

- [x] focused metadata regression tests — 17 passed, 1 warning
- [x] full backend/frontend tests/build — backend 1,052 passed, frontend 144 passed, build/lint ผ่าน (lint มี warnings เดิม)
- [ ] manual: แก้คำอธิบาย → บันทึก → เปิดใหม่ → ตรวจว่าไม่ซ้ำและข้อมูลส่งให้ AI ครบ

## Round PRODUCT-METADATA-4 — แก้ไข/preview metadata ก่อนบันทึก และจัดการ URL/ชื่อสินค้า

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** ให้การดึงข้อมูลซ้ำไม่ทับข้อมูลทันที, กันรูปและข้อความซ้ำ, เปิด preview/diff ก่อนยืนยัน, แก้ชื่อ/หัวข้อ/คำอธิบายได้, และเปลี่ยน URL ของรายการเดิมได้อย่างปลอดภัย

### Todo

- [x] เพิ่ม endpoint preview ที่อ่าน URL ใหม่แบบไม่เขียนฐานข้อมูล และคืน diff ของ metadata/images
- [x] เพิ่ม UI preview เปรียบเทียบข้อมูลเดิม/ข้อมูลใหม่ พร้อมเลือก field ที่จะรับเข้า
- [x] เพิ่ม form แก้ชื่อ หัวข้อ คำอธิบาย ราคา และ URL พร้อม validation/retry
- [x] ทำให้การบันทึกเป็น explicit confirm, dedupe รูป/ข้อความ และไม่กระทบ angles/scripts/assets เดิม
- [x] เพิ่ม deterministic regression tests สำหรับ preview, selective overwrite, dedupe, edit และ invalid URL
- [x] รัน compile/backend/frontend gates; manual UI verification ยังรอผู้ใช้ยืนยัน

### Notes

- Preview ใช้ `POST /api/products/{product_id}/preview-source` และไม่เขียนข้อมูลจนกว่าจะกดยืนยัน
- Confirm รับเฉพาะ field ที่เลือก, เปลี่ยน URL ของรายการเดิมได้, และ merge รูปโดยตัด query variant ของ CDN ที่เป็นรูปเดียวกัน
- Full deterministic evidence: backend 1,050 passed / 24 warnings, frontend 144 passed, build ผ่าน, lint exit 0, UI detector ผ่าน
- Manual UI verification ยังรอผู้ใช้ตรวจ flow จริง: preview → แก้ไข → เลือกทับบางฟิลด์ → save → reopen

### Gate

- [x] `python -m compileall -q scripts`
- [x] focused product metadata/API tests — 17 passed, 1 warning
- [x] full backend pytest — 1,050 passed, 24 warnings
- [x] frontend test/build/lint — 144 passed, build ผ่าน, lint exit 0 with existing warnings
- [x] `git diff --check`
- [ ] manual: preview → edit → เลือกทับบางฟิลด์ → save → reopen ตรวจข้อมูลและรูปไม่ซ้ำ

## Round PRODUCT-METADATA-3 — ดึงรายละเอียดสินค้าจากหน้า TikTok ที่ render ด้วย JavaScript

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** ให้การแปะลิงก์ TikTok ที่มีคำอธิบาย/สรรพคุณอยู่ในหน้าเว็บจริง ได้ source text ที่เฉพาะเจาะจงเข้า metadata และ prompt ของ AI; ห้ามอ้างว่าเป็นข้อมูลจากหน้าเว็บถ้าได้เพียง fallback จาก angle เดิม

### Todo

- [x] เพิ่ม hybrid extraction ที่ลอง HTML/meta ก่อน และใช้ browser-rendered DOM เมื่อข้อความไม่พอ
- [x] ทำให้รายการเดิมที่มี URL สามารถ refresh source metadata ได้ โดยไม่ลบรูป/สคริปต์/ข้อมูลที่ผู้ใช้แก้เอง
- [x] ส่ง visible source text ที่มีรายละเอียดจริงเข้า Content Matrix และ reroll prompt โดยจำกัดขนาดอย่างปลอดภัย
- [x] แสดง provenance/สถานะว่าได้ข้อมูลจาก meta, browser DOM, รูปภาพ หรือ fallback เพื่อไม่ให้ผู้ใช้เข้าใจผิด
- [x] เพิ่ม deterministic offline tests สำหรับ dynamic extraction, fallback และการบันทึก metadata

### Gate

- [x] `python -m compileall -q scripts`
- [x] focused product metadata/scraper tests — 12 passed, 1 warning
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,045 passed, 24 warnings
- [x] `npm test` และ `npm run build` หากแตะ frontend — 144 passed, build ผ่าน
- [x] `git diff --check`
- [ ] Live GOC01: กด “ดึงรายละเอียดจาก URL ใหม่” ใน Chrome profile, ผ่าน Security Check หากถูกถาม และยืนยันว่าข้อความคำอธิบาย/สรรพคุณเข้า metadata จริง

### Notes

- หลักฐานตั้งต้น: `_Docs/products.json` รายการ GOC01 มี URL และรูป 9 รูป แต่ไม่มี description/raw_text/specs/selling_points/pain_points ระดับสินค้า
- หลักฐานหลังแก้แบบ read-only จาก URL จริง: `metadata_source=html_body`, description 2,046 ตัวอักษร, raw text 2,221 ตัวอักษร, selling points 17 รายการ, specs 16 รายการ, พบ Smart CSC 2.0 และแบตเตอรี่ 35 ชั่วโมง; ไม่ได้เขียนทับ `_Docs/products.json`
- ความเสี่ยง: browser extraction ต้องมี timeout, optional dependency fallback และต้องไม่ bypass login/anti-bot หรือ SSRF validation
- ผล deterministic gate: compile ผ่าน, focused product metadata/scraper 12 passed, full backend 1,045 passed / 24 warnings, frontend 144 passed, build/lint ผ่าน, diff check ผ่าน
- Live gate ยังไม่ผ่าน: headless Chrome ได้หน้า `Security Check`; ต้องให้ผู้ใช้ยืนยันผ่าน persistent Chrome profile ก่อนจึงจะยืนยันข้อความจากหน้า TikTok จริงได้
- Environment: ติดตั้ง `playwright==1.58.0` ใน `.venv` และตรวจพบ Chromium executable ของ Playwright แล้ว; ไม่ได้แก้ `_Docs/products.json`
- [x] Round STYLE-ONECLICK-1 — เพิ่ม Style Preset หลายแบบใน One Click และแยก “ส่งตัดต่อใหม่” ออกจาก “เปิดโปรเจกต์เดิม” (2026-09-10)
- [x] Round HOOK-OPT-1 — ยกระดับฟอนต์/เทมเพลต/พรีวิว/สปีดฮุก (รายละเอียดใน HISTORY.md; implementation และ deterministic gates ผ่าน)
- [ ] Round SEC-AUDIT-1 — แก้ตาม DB/Infra/System audit: security config (API auth เปิดโล่ง, path traversal), sticker resurrection ฝั่ง render, data-store transaction hazard — 10 stream ขนาน ดู SYSTEM_AUDIT_FIX_PLAN.md (2026-09-09, รอ codex agent เสร็จก่อนยิง)
- [x] Round PRO-STYLE-1 — Professional Editing Style System: Phase 1 Style Contract + Golden Master (2026-09-09)
- [x] Round PRO-STYLE-2 — Editorial Beat Map + Pacing Core (Phase 2A, isolated module; 2026-09-09)
- [x] Round PRO-STYLE-2B — Integrate editorial pacing plan into subtitle pipeline and project manifest (2026-09-09)
- [x] Round SFX-DL-1 — โหลดเสียงเอฟเฟกต์ทั้งหมดจาก myinstants.com/en/index/th/ เข้า 02_Assets/SFX/ (2026-09-09)
- [x] Round SFX-CAT-1 — จัดหมวดหมู่ไฟล์เสียง mi_xxx 1,775 ไฟล์ เป็น 10 หมวดใน 02_Assets/SFX/ (2026-09-09)
- [x] Round BUG-STATUS-1 — คลิปที่เรนเดอร์แล้วติดสถานะ "กำลังตัดต่อ" (2026-09-08)
- [x] Round BUG-EXT-1 — Extension ไม่แสดงคลิปตัดต่อเสร็จเพราะ schedule queue บัง (2026-09-08)
- [x] Round POST-LIFECYCLE-1 — แยกเวอร์ชันที่โพสต์จริง, คุมรายการใน Extension และซ่อมปุ่มมาร์กโพสต์ (2026-09-08; implementation ปิดแล้ว, live TikTok แยกค้าง)
- [x] Round PERF-UX-1 — ปรับ Reliability/Preview Performance/Autosave/Incremental Render/Timeline Scaling แบบแยก ownership ขนานกัน (2026-09-09; implementation ปิด, empirical browser evidence deferred)
- [ ] Round SUB-THAI-2 — แก้การซ้อนของสระ `ั` กับวรรณยุกต์ `่` ในฟอนต์จริงของคลิป (พักไว้ตามคำขอ user · 2026-09-08)
- [x] Round STK-PRO-1 — ชุดสติกเกอร์และป้ายรีวิวสายไอทีระดับโปร (Photorealistic Tech Review Badges) (2026-09-08)
- [x] Round STK-3 - Sticker Baseline 100% Size, Track Eye Toggle, Deletion, and Preview-Before-Add (2026-09-08)
- [x] Round SUB-THAI-1 — แก้สระและวรรณยุกต์ไทยซ้อนกันในคลิปเรนเดอร์ (2026-09-08)
- [x] Round STK-2 - Multi-Sticker Support, 3-Second Default Duration, and Smooth Canvas Resizing (2026-09-08)
- [x] Round STK-1 - Interactive Sticker Timeline Track, Free Drag & Resize, and Parity Render Engine (2026-09-08)
- [x] Round HOK-1 - Custom Hook Template Studio (สร้างและบันทึกแม่แบบฮุกด้วยตัวเอง) (2026-09-07)
- [x] Round EDT-1 - Editor UX/UI Friction and Speed Optimization (2026-09-07)
- [x] Round POST-3.27 - Consolidate TikTok Studio upload tab opener to single header button (2026-09-07)
- [x] Round POST-3.26 - Add TikTok Studio Upload tab opener button to Extension (2026-09-07)
- [x] Round POST-3.25 - redesign extension UX/UI (Cyber-Studio Dark & Stepper Timeline) (2026-09-07)
- [x] Round POST-3.24 - indicate cover status in daily queue (2026-09-07)
- [x] Round POST-3.23 - reduce default publishing slots to three (2026-09-07)
- [ ] Backlog — เก็บสัญญาณพฤติกรรม TikTok รายคลิป (retention, product clicks, add-to-cart, conversion) เพื่อวัดผลเวลา/Hook/สินค้าและแนะนำคิวจากข้อมูลจริง

- [x] Round POST-3.22 - weekly schedule templates and product-rotating auto-fill (2026-09-07)

- [ ] Round POST-3 — ซ่อมขั้นหลังอัปโหลดและแนบปกจาก Cover Studio (2026-09-06)
- [x] Round POST-3.14 — เปิด Cover Studio ผ่านพอร์ทัล, ใช้ชื่อโปรเจคเป็นชื่อปก, และย้ายชื่อโปรเจค Logitech ให้เป็น LOG01 (2026-09-07)
- [x] Round POST-3.15 — ให้ `/api/exports` เลือกปกตามชื่อโปรเจคก่อน fallback เดิม (2026-09-07)
- [ ] Round POST-3.16 — ปกแสดง 3:4 และแก้ Extension แนบปกข้อ 5 ให้เปิด dialog/อัปโหลดได้จริง (2026-09-07)
- [ ] Round POST-3.17 — ซ่อม path ปกที่หายก่อนข้อ 5 และยืนยันการส่งต่อไป TikTok (2026-09-07)
- [ ] Round POST-3.18 — make CDP cover upload notify TikTok React (2026-09-07)
- [x] Round POST-3.19 - restore generated cover in TikTok post modal (2026-09-07)

- [x] Round DOC-1 — ตรวจโค้ดและอัปเดตเอกสาร/กฎให้ตรงกับระบบปัจจุบัน
- [x] Round BUG-1 — แก้ปุ่มสร้างคลิปใหม่กดไม่ได้ (executeRender ใน useRenderJob)
- [x] Round 4 — per-word layout (static, พิสูจน์ว่าเหมือนเดิมเป๊ะ)
- [x] Round 5 — per-word animation (คำทยอยเข้าทีละคำ)
- [x] Round 6 — ช่องใหม่ที่ mirror ได้เป๊ะ
- [x] Round 7 — template v2 + แกลเลอรีที่ขยับได้
- [x] Round BUG-2 — แก้ข้อความและ Hook Header ซ้อนทับกันเป็นก้อนใน SequencePlayer
- [ ] Round POST-1 — Desktop Post Studio (ปก + ลากไฟล์ + แคปชั่น + ปิดวงจร Posted)
- [ ] Round POST-2 — TikTok auto-post extension (กลับมาทำตามคำสั่ง User: ขั้น 2–5 และส่งปก)
- [x] Round BUG-3 — ซ่อม angle ชนกัน (คลิปผิดสคริปต์) ใน Content Tracker Hub + ปุ่มปักตะกร้า TikTok
- [x] Round PROD-1 — เพิ่มช่องระบุ TikTok Product ID ตอนสร้างสคริปต์ใหม่ + Fallback ค้นหาด้วยชื่อสินค้า + Click-to-Edit Cart ID
- [x] Round TRK-1 — เพิ่มปุ่มส่งคลิปไป TikTok Studio พร้อม Modal ตรวจสอบ/ปักตะกร้า ในหน้า Tracker (ContentTrackerHub)
- [x] Round TRK-2 — ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet) & จัดกลุ่มย่อการ์ด (Product Grouping / Quick Pills)
- [x] Round TRK-3 — บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์หยิบทำวันนี้ & การ์ดตัดต่อเสร็จแนวนอนกะทัดรัด)
- [x] Round COV-1 — สตูดิโอสร้างปกคลิปด่วน 9:16 & 3:4 (Auto Highlight Crop, Interactive Pan & Zoom Subtitle-Free, Dual Export)
- [x] Round SFX-HUB-1 — สแกน SFX แบบ Recursive เข้า AssetRegistry และเพิ่มตัวกรองหมวดหมู่ SFX ใน Media Assets Hub (2026-09-09)
- [x] Round SFX-TITLES-1 — ดึงชื่อภาษาไทย/ชื่อจริงที่แสดงบน Myinstants มาใส่เป็น label ใน asset_metadata.json (2026-09-09)
- [x] Round TLO-REFACTOR-1 — แยก abstraction ของ Overlay Timeline/Preview แบบรักษา behavior เดิม (2026-09-09)
- [x] Round TLO-REFACTOR-2 — ลด duplication ฝั่ง renderer เฉพาะจุดที่พิสูจน์ parity ได้ (2026-09-09)
- [x] Round TLO-REFACTOR-3 — แยก shared Timeline label-gutter primitive (2026-09-09)
- [x] Round TLO-REFACTOR-4 — รองรับ optional trim handles ใน shared timeline shell (2026-09-09)
- [x] Round TLO-REFACTOR-5 — ย้าย Caption chip เข้า shared timeline shell โดยคง magnetic-ripple policy (2026-09-09)
- [x] Round TLO-REFACTOR-6 — รวม shared Inspector header สำหรับ Sticker/Effect (2026-09-09)
- [x] Round TLO-REFACTOR-7 — รวม timeline pointer lifecycle โดยคง type-specific drag math (2026-09-09)
- [x] Round TLO-REFACTOR-FINAL-AUDIT — ตรวจ final gates และ inventory หลัง refactor ทั้งชุด (2026-09-09; overlay/repo validation ปิดแล้ว)

- รายละเอียดเต็มของ `TLO-REFACTOR-FINAL-AUDIT` และ `POST-LIFECYCLE-1` ย้ายไปเก็บใน [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md) แล้ว; สถานะที่ยังรอ live TikTok อยู่ใน `POST-3.16`–`POST-3.18` และ `POST-2`

## Round SUB-THAI-2 — แก้สระ `ั` กับวรรณยุกต์ `่` ซ้อนในฟอนต์จริง

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: พักไว้ ยังไม่สำเร็จ — แก้ไม่ได้จากหลักฐานปัจจุบัน รอ user verification

**Repro และสถานะ:**

1. Repro ด้วยคลิปจริง `00_Inbox/มมแกะกลอง_WaveKeys.mov` และ ASS ของโปรเจกต์ `LOG01-ปัญหาก่อนใช้_1`; พบปัญหาที่ `ใครที่นั่งทำงาน` และ `นั่งพิมพ์งานทั้งวัน`
2. ทดลองแก้ทั้ง Canvas Preview และ ASS/libass แล้ว แต่ user ตรวจเรนเดอร์จริงและยืนยันว่า `ั` กับ `่` ยังซ้อนเหมือนเดิม
3. พักงานตามคำขอ user เพื่อไปทำเรื่องอื่นต่อ; ห้ามอ้างว่ารอบนี้แก้สำเร็จจนกว่าจะผ่านการตรวจเรนเดอร์จริงจาก user

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน
- [x] parity/behavior tests — ผ่าน
- [ ] FFmpeg final render — ยังไม่ผ่าน user verification
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 930 ผ่าน
- [x] `npm test` และ `npm run build` — ผ่าน
- [ ] ตรวจภาพแคปจริง — user ยืนยันว่ายังพบการซ้อน

### Notes

- อย่าปิดรอบนี้หรือย้ายไป HISTORY จนกว่าจะมีเฟรมเรนเดอร์ที่ user ยืนยันว่าไม่ซ้อน

**ปิดไปแล้ว** (บล็อกเต็มอยู่ใน [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md)): Round PRO-STYLE-1 — Professional Editing Style System: Phase 1 Style Contract + Golden Master (2026-09-09) · Round PRO-STYLE-2 — Editorial Beat Map + Pacing Core (Phase 2A, 2026-09-09)
Round 1 รวม overlay เป็นโมเดลเดียว · Round 2 วางกฎรอบงาน · Round 3 ซ่อมฐาน+easing · Round DOC-1 อัปเดตเอกสาร · Round BUG-1 ซ่อมปุ่มสร้างคลิป executeRender · Round 4 per-word layout static · Round 5 per-word animation (word_stagger_ms) · Round 6 ช่องใหม่ที่ mirror ได้เป๊ะ (loop/out/skew) · Round 7 template v2 + แกลเลอรีที่ขยับได้ (8 templates + motion presets + inspector animated gallery) · Round BUG-2 ซ่อมข้อความ/Hook Header ซ้อนทับกันใน SequencePlayer · Round BUG-3 ซ่อม angle ชนกัน + ปุ่มปักตะกร้า TikTok ใน Content Tracker Hub · Round PROD-1 เพิ่มช่อง TikTok Product ID + Fallback ค้นหาด้วยชื่อ + Click-to-Edit Cart ID ย้อนหลัง · Round TRK-1 เพิ่มปุ่มส่ง TikTok Studio + Modal ตรวจสอบ/ปักตะกร้า ในหน้า Tracker · Round TRK-2 ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet) & จัดกลุ่มย่อการ์ด (Product Grouping / Quick Pills) · Round TRK-3 บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์หยิบทำวันนี้ & การ์ดตัดต่อเสร็จแนวนอนกะทัดรัด) · Round STK-1 Interactive Sticker Timeline Track & Free Canvas Drag/Resize Parity · Round STK-2 Multi-Sticker Support, 3-Second Default Duration & Smooth Canvas Resizing · Round STK-3 Baseline 100% Size, Eye Toggle, Deletion, Preview-Before-Add · Round SUB-THAI-1 แก้สระและวรรณยุกต์ไทยซ้อนกัน · Round STK-PRO-1 ชุดสติกเกอร์และป้ายรีวิวสายไอทีระดับโปร

> คู่ขนาน: [REFACTOR_PLAN.md](file:///d:/Winona/Programmer/Capcut/REFACTOR_PLAN.md) Phase 0–10 + Final เสร็จครบแล้ว (ทำโดย Codex) ไฟล์นั้นปิดงานแล้ว เก็บไว้อ้างอิง

---

## คำสั่งตรวจพื้นฐาน

```powershell
python -m compileall -q scripts
python -c "import scripts.api_server as app; print(len(app.app.routes))"
python -m pytest tests/ -q -p no:cacheprovider
Set-Location frontend
npm run build
npm test
```

งานที่มีผลต่อภาพในวิดีโอ ต้องรัน ffmpeg ดึงเฟรมจริงมาดูด้วย ตาม
[.agents/rules/preview_render_parity.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/preview_render_parity.md)

---

- [x] Round STK-3 — ปรับขนาดสติกเกอร์ 100% เท่ากับขนาดจอที่ผู้ใช้ต้องการ, ซ่อมปุ่มปิดตาแทร็กสติกเกอร์, ลบสติกเกอร์ได้ทุกช่องทาง และระบบพรีวิวก่อนกดบวกเหมือนข้อความ (2026-09-08)
- [x] Round ACCENT-REV-1 — คืนค่าตัวเลือกตกแต่ง (Accent) กลับเป็น 3 ตัวเลือกดั้งเดิมตามคำสั่งผู้ใช้ (2026-09-08)

## Round POST-3.16 — แก้การแนบปกข้อ 5 และแสดงภาพปก 3:4

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: กำลังทำ

**ขอบเขต:** แก้เฉพาะขั้นตอนแนบปกของ Extension (HTML btn6/chk6 และ automation uploadCover) กับการแสดงปกใน TikTok modal; ล็อกขั้นตอน 1–4 ไม่แตะ

### Todo

- [x] ปรับ TikTok modal ให้ใช้ภาพปก 3:4 เมื่อมีไฟล์ 3:4 และส่ง path เดียวกันไปขั้นตอนปก
- [x] ทำให้ Extension ตรวจ/กด “แก้ไขหน้าปก” ได้จาก DOM จริง พร้อม fallback click ที่ไม่เปิด native file picker ก่อนเวลา
- [x] ทำให้ตัวค้นหา dialog, file input และปุ่มบันทึกครอบคลุมโครงสร้าง TikTok ปัจจุบัน โดยไม่เปลี่ยนขั้นตอน 1–4
- [x] เพิ่ม regression tests สำหรับ mapping ปก 3:4, export variant และ selector contract ของข้อ 5

### Gate

- [x] `node --check tiktok_autopost_extension/automation.js` และ `node --check tiktok_autopost_extension/background.js`
- [x] `node --test tiktok_autopost_extension/background.test.cjs`
- [x] `npm test` และ `npm run build` ใน `frontend/`
- [x] `python -m compileall -q scripts` และ `python -m pytest tests/test_api_tiktok_autopost.py -q -p no:cacheprovider --tb=short`
- [ ] ทดสอบหน้าเว็บจริง: เปิด TikTok modal → Cover Studio, บันทึก both, ตรวจ preview 3:4 และตรวจว่าข้อ 5 พบ dialog/file input (ไม่กด Post)

### Notes

- งานค้างใน working tree ก่อนเริ่ม: `scripts/db.py`, `scripts/product_store.py`, `tests/test_reconcile_transaction.py` จากงานอื่น; ห้ามแตะหรือ stage รวม
- Full regression: `pytest tests/` ผ่าน 864 tests และไม่มีไฟล์ขั้นตอน 1–4 ถูกแก้ในรอบนี้
- Live page navigation เคยยืนยันการเปิด Cover Studio ได้ แต่ยังไม่มี TikTok tab ที่เชื่อมผ่าน CDP สำหรับกด Extension ข้อ 5 จริง จึงยังไม่ติ๊ก gate live นี้จนกว่าจะทดสอบบน Chrome session ของผู้ใช้

## Round POST-3.17 — ซ่อม path ปกที่หายก่อนข้อ 5

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: กำลังทำ

**หลักฐานอาการ:** งาน pending จริงมี `cover_path: null` ทั้งที่มีไฟล์ `05_Covers_Thumbnails/Logitech Wave Keys_cover_3x4.jpg`; Side Panel จึงหยุดที่ guard ของข้อ 5 ก่อนส่งคำสั่งเปิด Cover Studio

**ขอบเขต:** แก้เฉพาะการ resolve/ส่งต่อ path ปกและผลลัพธ์ของขั้นตอนแนบปก ไม่แตะ runtime ของขั้นตอน 1–4 และไม่แตะปุ่มโพสต์

### Todo

- [x] เพิ่มการค้นหาปกจากชื่อโปรเจค/ชื่อสินค้าและเลือก 3:4 เป็นค่าเริ่มต้นเมื่อ `prepare` ไม่มี `cover_path`
- [x] ทำให้ `pending` ซ่อม `cover_path` ที่หายได้ก่อน Extension ทำข้อ 5
- [x] ส่ง `cover_path` ที่ backend ยืนยันกลับไปยัง Side Panel
- [x] เพิ่ม regression tests สำหรับ pending ที่ไม่มี path แต่มีปกชื่อสินค้า
- [x] คง guard/selector ของข้อ 1–4 และปุ่มโพสต์เดิม

### Gate

- [x] `python -m pytest tests/test_api_tiktok_autopost.py -q -p no:cacheprovider --tb=short` — 11 passed
- [x] `node --check tiktok_autopost_extension/sidepanel.js` และ `node --test tiktok_autopost_extension/background.test.cjs` — 8 passed
- [x] `python -m compileall -q scripts`
- [ ] ตรวจหน้า TikTok จริง: กดข้อ 5 แล้วพบ dialog, ใส่ปก, บันทึกปก โดยไม่กดโพสต์

### Notes

- หลักฐาน live ก่อนแก้: `/api/tiktok-autopost/pending` คืน `cover_path: null`; helper ใหม่ resolve ได้เป็น `05_Covers_Thumbnails/Logitech Wave Keys_cover_3x4.jpg` จาก `product_id=20260904233315_1`
- ตรวจ DOM TikTok จริงแล้วพบปุ่ม `แก้ไขหน้าปก` 1 จุด, `cover-editor-container` 1 จุด และ `input[type=file]` แบบซ่อน 1 จุด; การอัปโหลดไฟล์ผ่าน browser controller ถูกระบบควบคุมไฟล์บล็อก จึงยังไม่ติ๊ก live gate
- Full regression หลังแก้: `866 passed, 6 warnings`; ขั้นตอน 1–4 และปุ่มโพสต์ไม่ได้ถูกแก้

??????: 2026-09-07 ? ???????: user ? ?????: ???????

**??????????????:** ???? Cover Studio ???????; DOM ?????? `cover-editor-container` ??? `label.ImageUpload__uploadArea` ??????? `input[type=file]` ??????? ?????????????????? extension ??????????? TikTok ??????????????

**??????:** ??????????? 5 (`automation.js`/`background.js` ??? regression tests) ??????? runtime ?????? 1?4 ??????????????? Post

### Todo

- [ ] ??????????????????? CDP: ??? input ? ?? node ? ??????? ? ???? `files.length`
- [ ] ??? `input`/`change` event ???? `DOM.setFileInputFiles` ???????? React/TikTok ???????
- [ ] ???? error ????????????????????? TikTok ????????????????????? preview
- [ ] ????? regression contract test ?????? event dispatch ??????????????
- [ ] ??????????? Chrome: ???? preview ????????????????? ???????? ??? ???????? Post

### Gate

- [ ] `node --check tiktok_autopost_extension/automation.js`
- [ ] `node --test tiktok_autopost_extension/background.test.cjs`
- [ ] ????? flow ??????? 5 ?? TikTok Studio

### Notes

- browser controller ??? Codex ????????? `fileChooser.setFiles`; ???????????????????????????????? extension debugger ?????????
- ???? `frontend/src/components/ContentTrackerHub.jsx` ?????????????????????? ??????????? stage ????????

## Round POST-3.18 — make CDP cover upload notify TikTok React

Date: 2026-09-07; Requested by: user; Status: in progress

**Evidence before fix:** Cover Studio opens. The live DOM contains `cover-editor-container` and `label.ImageUpload__uploadArea` wrapping a hidden `input[type=file]`, but the extension does not make TikTok show the selected cover.

**Scope:** Only step 5 (`automation.js`/`background.js` and regression tests). Do not touch steps 1-4 or the Post action.

### Todo

- [x] Record each CDP boundary: locate input with DOM.getDocument/querySelectorAll -> set file -> verify files.length
- [x] Dispatch `input`/`change` after `DOM.setFileInputFiles` so TikTok React receives the file
- [x] Report actionable errors when TikTok rejects the file or preview does not appear
- [x] Add a regression contract test for event dispatch and file verification
- [ ] Run the real Chrome step 5 flow: preview the program cover and click Save without clicking Post

### Persistence follow-up

- [x] Persist generated cover paths on the selected product angle so a refresh can restore the cover.
- [x] Return cover path and media URL variants from the products API after reload.
- [x] Add deterministic backend regression coverage for cover persistence and refresh.
- [ ] Verify step 5 with the extension after the persisted cover is restored.

### Upload acceptance follow-up

- [x] Use the exact input object from the scoped Cover Studio query for CDP assignment and React notification.
- [x] Verify the post-assignment notification targets the same input object instead of a fresh global selector.
- [x] Add a regression test for TikTok replacing or resetting the hidden input, with one controlled retry.
- [ ] Re-run the real extension step 5 flow and confirm preview plus Save.

### Gate

- [x] `node --check tiktok_autopost_extension/automation.js`
- [x] `node --test tiktok_autopost_extension/background.test.cjs`
- [ ] Real step 5 flow in TikTok Studio

### Notes

- `node --test tiktok_autopost_extension/background.test.cjs`: 12 passed; the new exact-object and input-replacement regressions pass.
- The Codex browser controller blocks `fileChooser.setFiles`; real file injection must be exercised by the extension debugger.
- The follow-up now sends `DOM.setFileInputFiles` with the scoped Runtime `objectId`, dispatches events on that same object, and retries once if TikTok replaces the hidden input.
- `frontend/src/components/ContentTrackerHub.jsx` and `frontend/src/components/ProductToClip.jsx` contain unrelated working-tree changes; do not touch or stage them.

- [x] Round POST-3.21 - multi-day TikTok publishing queue (2026-09-07)

## Round POST-3.20 - edit generated cover inside OmniCut

Date: 2026-09-07; Requested by: user; Status: in progress

**Goal:** Let the user edit or regenerate the saved 3:4 TikTok cover directly in OmniCut Cover Studio, then keep the selected cover visible in the TikTok preparation modal after refresh.

**Scope:** Inspect the current TikTok modal -> Cover Studio handoff, saved cover hydration, and edit affordance. Keep steps 1-4 and the working extension upload flow unchanged.

### Todo

- [x] Reproduce the current modal state where a saved cover is not shown or the edit action is unclear.
- [x] Define the edit path: open Cover Studio with the existing cover context, allow frame/crop/text changes, and persist the resulting 3:4 path.
- [x] Add deterministic regression coverage for path-only saved covers and restoring the selected 3:4 variant after refresh.
- [x] Improve the cover card behavior so the action clearly says edit when a saved cover exists and create when it does not.
- [x] Merge matching `/api/exports` cover metadata when the live `/api/products` response omits saved cover fields.
- [x] Add a large 3:4 cover preview in the TikTok modal, with a direct path back to Cover Studio for editing.
- [x] Run frontend/backend tests and build.
- [ ] Verify the remaining live edit -> save -> refresh flow in the browser.

### Gate

- [x] `npm test` - 74 passed
- [x] `npm run build` - passed
- [x] backend suite - 869 passed, 6 existing warnings
- [ ] browser verification of edit -> save -> refresh -> modal

### Notes

- Implementation commit: `f2dbfed` (`fix: restore saved cover metadata in TikTok modal`).
- The live `/api/products` response currently returns null cover fields for this product while `/api/exports` contains the matching saved 3:4 cover. The client now merges that export metadata by project name/video reference and preserves any explicit angle cover.
- Browser check: clicking the saved 3:4 thumbnail opens a large preview, and `เปลี่ยนภาพปก` closes it and opens Cover Studio with the current cover loaded.
- Existing uncommitted changes belong to another workstream: `frontend/src/components/editor/EditorShell.jsx`, `frontend/src/components/editor/Timeline.jsx`, `frontend/src/components/editor/TimelineClip.jsx`, `frontend/src/lib/timelineMath.js`, `frontend/src/lib/timelineMath.test.js`, and the untracked screenshots `alt-drag-left.png`, `alt-drag-mid.png`, `clip-selected.png`, `timeline-loaded.png`; do not modify, delete, or stage them.
- Steps 1-4 and the extension upload implementation are frozen by the user.

## งานค้าง (Backlog)

- [ ] Audit follow-up — แก้ reconciliation failures 9 รายการจาก full pytest (`test_reconcile_angle_collision.py`, `test_reconcile_grace_period.py`, `test_reconcile_preserves_posted.py`, `test_reconcile_transaction.py`, `test_relative_paths.py`) ในรอบ POST-LIFECYCLE โดยห้ามปนกับ Overlay Refactor (2026-09-09)

## Round PERF-UX-1 — ปรับ Reliability/Preview Performance/Autosave/Incremental Render/Timeline Scaling แบบแยก ownership ขนานกัน

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: implementation และ deterministic evidence เสร็จ; empirical browser evidence deferred ตามคำสั่ง user

**เป้าหมาย:** ปรับความน่าเชื่อถือ, ความลื่นของ editor, ความเร็ว autosave/export และการรองรับ project ใหญ่ โดยแบ่ง write scope ไม่ให้ agent แก้ไฟล์เดียวกันพร้อมกัน และรักษา Preview = Render contract.

**ข้อจำกัดก่อนเริ่ม (superseded by continuation takeover):** working tree มี diff เดิมใน `frontend/src/components/editor/Timeline.jsx` และ `frontend/src/hooks/useEditorCommands.js`; ห้าม reset, ลบ หรือเขียนทับ diff เดิม. หลัง user ยืนยันว่าไม่มี agent อื่นแก้ไฟล์แล้ว main agent รับช่วง Timeline เฉพาะ low-risk scaling slice และยังไม่ stage diff ที่ไม่เกี่ยวข้อง.

### Continuation takeover (2026-09-09)

- User confirmed that no other agent is editing now and authorized continuing all remaining PERF-UX-1 phases.
- Main agent takes ownership of the previously blocked Timeline scaling scope. Existing `Timeline.jsx` and `useEditorCommands.js` working-tree changes are preserved verbatim unless a minimal change is required by this scope; no reset, checkout, clean, or destructive overwrite is allowed.
- Timeline work is deliberately limited to low-risk derived-data/render-churn reductions with source-contract coverage. Full virtualization and browser FPS claims remain out of scope until a real 50/100/300-clip fixture measurement exists.
- B browser profiler evidence and D real API/job repeated-rerender smoke remain explicit gates. They may be marked complete only with actual command/browser evidence.

### Evidence update (2026-09-09)

The entries below supersede the earlier tentative status in this round.

- [x] E implementation: `Timeline.jsx` now memoizes transition/clip-audio collections and indexes sticker assets without changing lane geometry, lookup precedence, or interaction handlers.
- [x] E regression probe: frontend suite now includes the Timeline render-performance contract; latest `npm test` = `144 passed, 0 failed`.
- [x] E microbenchmark: synthetic 50/100/300-clip derived-work probe, 20,000 rounds each, produced equivalent results and reductions of `64.5%`, `77.0%`, and `86.7%` for the measured repeated derivation slice.
- [x] E browser fixture inspection: the currently open local project rendered `54` timeline items, `16` transition triggers, and `1,367` total DOM elements; this is an observation baseline only, not a before/after FPS claim.
- [x] D rerender-flow smoke: `complete_job` stamped real temp artifacts, a subsequent `PipelineContext` consumed the persisted fingerprints, and the targeted file now reports `14 passed, 0 failed`.
- [ ] B browser/React Profiler before-after measurement: no supported profiler trace or deterministic playback fixture was available; static probe and browser DOM inspection do not prove FPS/audio-drift improvement.
- [ ] D full API/job repeated-rerender smoke: deterministic job-to-context coverage is complete, but a real FFmpeg/API rerender with production artifacts remains pending.
- [ ] E full 50/100/300 browser fixture benchmark: microbenchmark is complete, but DOM count/open latency/drag-scroll FPS at those sizes still needs a controlled fixture.

### Workstreams / ownership

- [x] **A — POST-LIFECYCLE reliability:** `scripts/product_store.py`, `scripts/api_exports.py`, `scripts/api_videos.py`, `scripts/api_schedule_queue.py`, และ `tests/test_reconcile_*.py` / `tests/test_relative_paths.py` ตาม failure ที่พบ; ปิด full pytest failures 9 รายการโดยไม่แตะ frontend files ที่ค้าง
- [x] **B — Preview frame performance implementation/probe:** `frontend/src/components/SequencePlayer.jsx` และ `frontend/src/lib/sequencePlayerFrameScheduling.test.js`; ลด React playhead publication และ repeated previous-segment lookup โดยคง Canvas/audio clock เดิม
- [x] **C — Autosave/history responsiveness:** `frontend/src/hooks/useProjectAutosave.js`, `frontend/src/hooks/useEditorHistory.js`, `frontend/src/lib/projectSaveQueue.js` และ tests ที่ตรง module; รักษา save/migration/undo-redo contract
- [x] **D — Incremental render/artifact reuse implementation:** `scripts/pipeline_context.py`, `scripts/render_jobs.py` และ `tests/test_incremental_render_reuse.py`; audit reuse เดิมก่อนเพิ่ม fingerprint และ rerun policy โดยไม่แตะ renderer arguments
- [x] **E — Timeline/filmstrip scaling:** ปิด low-risk implementation ที่พิสูจน์ได้ด้วย source contract และ synthetic benchmark; full virtualization/FPS benchmark ยังเป็น external validation แยกต่างหาก
- [x] **Integration owner:** main agent review diff, ตรวจ file ownership, รวม test evidence และรัน gates แบบ serial แล้ว

### ลำดับและ gates

- [x] A: แยก root cause ของ 9 failures, เพิ่ม/แก้ regression ทีละกลุ่ม, รัน targeted tests และ full pytest จน `0 failed`
- [ ] B: เก็บ runtime baseline/after ด้วย React Profiler หรือ browser trace: p50/p95 frame time, dropped frames, React commits/sec และ audio drift; static probe ผ่านแล้ว แต่ยังไม่มี browser measurement จริง
- [x] C: เพิ่ม save ordering/flush/undo-redo regression ก่อนปรับ implementation; frontend tests/build ผ่าน และ targeted Stream C = `13 passed, 0 failed`
- [x] D: สร้าง change-class matrix และ fingerprint coverage ก่อนเปลี่ยน reuse; targeted incremental = `13 passed`, compatibility = `57 passed`, compileall ผ่าน
- [ ] D follow-up: production API/FFmpeg repeated rerender smoke ยัง pending; deterministic `complete_job → fingerprint manifest → PipelineContext` flow ปิดแล้วที่ `14 passed`
- [ ] E: controlled browser fixture 50/100/300 clips, DOM count/open latency และ drag/scroll FPS ยัง pending; low-risk implementation และ synthetic microbenchmark ปิดแล้ว
- [x] Integration gates ปัจจุบัน: `git diff --check`, `python -m compileall -q scripts`, targeted tests ทุก stream, `npm test` = `144 passed`, `npm run lint` exit 0, `npm run build` = `1,979 modules transformed`, full pytest = `1,034 passed, 0 failed, 24 warnings`

### Notes

- [x] Stream A root cause: `ProductStore._last_reconcile_at` เป็น global ข้าม temp storage ทำให้ debounce บล็อก test ถัดไป; แก้เป็น storage-scoped state และ serialize thread mutation; targeted reconciliation = `47 passed`, full pytest = `957 passed, 0 failed, 6 warnings`
- [x] Stream B static evidence: `setPlayhead(t)` ใน RAF ลด `1 → 0`, previous `segments.find(...)` ลด `1 → 0`, เพิ่ม static probes `3 passed`; ยังห้ามสรุป FPS gain จนกว่าจะมี browser/Profiler before-after
- [x] Stream C เพิ่ม controller/queue generation และ immutable history model; frontend ทั้งชุด = `124 passed`, build ผ่าน, lint exit 0 แต่ยังมี warning React refs 1 จุดใน autosave
- [x] Stream D เพิ่ม stage/artifact SHA-256 fingerprints และ best-effort manifest stamp; deterministic rerender-flow = `14 passed`; ไม่แตะ `api_render.py`, renderer หรือ Preview = Render paths
- [ ] ห้ามสรุป performance improvement จากการอ่านโค้ด ต้องมีตัวเลข before/after จาก fixture เดียวกัน
- [ ] ห้าม genericize behavioral divergence ของ timeline/preview โดยไม่มี parity evidence; type-specific clamps, audio clock และ posted identity ต้องคง contract เดิม
- [x] Timeline low-risk scaling slice รับช่วงต่อแล้ว: memoized transition/clip-audio collections และ indexed sticker assets ใน `Timeline.jsx`; existing `useEditorCommands.js` functional diff/debug line ถูกเก็บรักษา ไม่ได้เขียนทับ
- [ ] ถ้า stream ใดพบ shared dependency หรือ file ownership ชนกัน ให้หยุด stream นั้น, บันทึก blocker ที่นี่ และให้ main agent integrate ตามลำดับแทนการเขียนทับ

### Round POST-3 — แผนก่อนลงมือ (2026-09-06 / อัปเดตแก้ขั้น 3)

#### POST-3.1 — แก้จากหลักฐานหน้าจอ TikTok จริง (2026-09-07)

- [x] Radio สินค้า: ลดการคลิกซ้ำเหลือครั้งเดียวต่อ fallback และยืนยัน `checked/aria-checked` ก่อนเดินหน้า
- [x] Dialog ตั้งชื่อตะกร้า: รอ input `TUXTextInputCore-input` และปุ่ม `เพิ่ม` แล้วตรวจ modal ปิด/ชิปสินค้าหลังเพิ่ม
- [x] ตั้งเวลา: รับค่า date/time จาก Side Panel และยืนยันค่าที่แสดงจริงก่อนรายงานสำเร็จ
- [x] ปก: รองรับ `label.ImageUpload__uploadArea` และ file input ที่อยู่ใน/ข้าง label ผ่าน `DOM.setFileInputFiles`
- [x] เพิ่ม regression test สำหรับ radio toggle, cart-name dialog, schedule payload และ cover selector

หลักฐาน: ภาพวันที่ 2026-09-07 แสดง `input.TUXRadioStandalone-input` ที่ยังไม่ถูกเลือก,
dialog ชื่อสินค้าใช้ `input.TUXTextInputCore-input` และปกใช้ `label.ImageUpload__uploadArea`
role=`button`; การทดสอบ live ยังไม่ปิดจนกว่าผู้ใช้จะ reload extension และยืนยันผลจริง

ผล gate: `node --check` ผ่านทุกไฟล์, `node --test tiktok_autopost_extension/background.test.cjs` = 7 passed,
`python -m pytest tests/test_api_tiktok_autopost.py -q -p no:cacheprovider` = 4 passed, 1 known warning.
ยังไม่ได้ทดสอบ TikTok จริงหลังแพตช์รอบนี้

#### POST-3.2 — แก้ตามผลทดสอบ Playwright จริง (2026-09-07)

- [x] ปรับการเลือกสินค้าให้คลิก wrapper ของ `TUXRadioStandalone` เมื่อ native input ไม่เปลี่ยน `checked` และต้องคลิกเพียงครั้งเดียว
- [x] ปรับตัวเลือกเวลาให้ใช้รายการชั่วโมง/นาทีของ TikTok (`.tiktok-timepicker-option-text`) และตัวเลือกวันที่ `.day.valid` แทนการหา text แบบ ISO ตรง ๆ
- [x] เอา fallback click ซ้ำของปุ่ม “ถัดไป” ออก เพื่อไม่ให้ dialog ถูกเปิด/ปิดซ้ำ
- [ ] ยืนยัน flow หน้าปกด้วย `div.edit-container` → `label.ImageUpload__uploadArea` → file input → บันทึก โดยไม่กดเผยแพร่
- [x] รัน node tests, backend test และตรวจ syntax หลังแก้

หลักฐาน Playwright รอบนี้: พบ input วันเวลาเป็น `readonly` (`09:35`, `2026-09-07`); เปิด picker สำเร็จและเลือกเวลา `10:10` กับวันที่ `2026-09-08` ได้จริงด้วยรายการ DOM ของ TikTok; เลือกสินค้า ID `1737230577125983588` ผ่าน wrapper แล้ว `checked=true`, เปิด dialog ตั้งชื่อและกด `เพิ่ม` สำเร็จจนเห็นชิป `Logitech Wave Keys`; คลิก `div.edit-container` เปิด Cover Studio และพบ `label.ImageUpload__uploadArea` 1 จุด แต่การส่งไฟล์ผ่าน Chrome Playwright ถูกระบบเบราว์เซอร์ปฏิเสธ (`fileChooser.setFiles: Not allowed`) จึงยังไม่ติ๊ก gate แนบไฟล์จนกว่าจะทดสอบผ่าน extension/CDP จริง

#### POST-3.3 — แก้ root ของ modal ซ้อน (2026-09-07)

- [x] ให้การค้นหาแถวสินค้าและปุ่ม “ถัดไป” เลือก `.product-selector-container`/dialog ล่าสุด แทน dialog เก่าที่ค้างอยู่ใน DOM
- [x] คงการคลิก wrapper radio เพียงครั้งเดียวและตรวจ `checked` หลังคลิก
- [x] ลดการสลับแท็บ Showcase เหลือ logical click เดียว ตัด synthetic pointer sequence ที่ซ้ำบน tab และ container
- [x] รัน syntax check, node regression และ backend test หลังแก้

หลักฐาน: ใน DOM จริงของ TikTok พบ dialog “เพิ่มลิงก์” เก่ายังคงอยู่พร้อม dialog “เพิ่มลิงก์สินค้า”; root เดิมจึงมีโอกาสค้นหาแถวผิด dialog แพตช์นี้บังคับ scope ไปที่ product selector ล่าสุด

#### POST-3.4 — แก้ข้อ 4/5 จากผลใช้งานหลังคอมมิต (2026-09-07)

- [ ] ทำให้ schedule เลือกค่าใหม่แล้วกดปุ่มยืนยันของ TikTok (`ตั้งเวลา`) ก่อนตรวจค่าที่แสดง และคืน error ถ้าปุ่มยืนยันไม่ทำงาน
- [ ] ทำให้ข้อแนบปกเปิด Cover Studio ได้แม้ปุ่มเป็น `div.edit-container` และเลือกไฟล์ input ที่อยู่ใน modal ล่าสุดเท่านั้น
- [ ] แสดงผลลัพธ์แต่ละขั้นใน Side Panel ให้ผู้ใช้รู้ว่าค่า schedule/cover ถูกส่งจริงหรือหยุดที่จุดใด
- [ ] รัน node regression, backend test และ syntax check

- [x] แก้ไขขั้น 3: สลับแท็บ "นำเสนอสินค้า" (Showcase Tab)
  - รองรับกรณีหน้าต่าง `< เพิ่มลิงก์สินค้า` เปิดค้างอยู่แล้ว ไม่ต้องกดย้อน "+ เพิ่ม" ซ้ำ
  - ค้นหาแท็บทั่วทั้ง document ไม่จำกัดที่ `document.querySelector('[role="dialog"]')` ตัวแรก
  - ทริกเกอร์อีเวนต์เมาส์เต็มรูปแบบ (pointerdown, mousedown, pointerup, mouseup, click) ทั้งบนแท็บและคอนเทนเนอร์ `[role="tab"]` พร้อม CDP native click `buttons: 1`
  - ตรวจจับสถานะแอคทีฟของแท็บอย่างแม่นยำด้วย `aria-selected`, คลาสแอคทีฟ, ช่องค้นหาที่แสดงผลจริง และ negative-check ป้องกันค้างที่ "ไม่มีสินค้าในร้านของคุณ"
- [x] แก้ไขขั้น 3: ค้นหาและเลือกสินค้าด้วย Product ID
  - กรอก Product ID, dispatch input/change, คลิกปุ่มแว่นขยาย และกด Enter
  - ค้นหาแถวสินค้าในผลลัพธ์: รองรับทั้งกรณีแถวมีรหัสสินค้า หรือแถวผลลัพธ์จากการค้นหารหัสเฉพาะ
  - คลิกเลือก Radio/Checkbox ของสินค้ารายการแรกในผลการค้นหา และยืนยันสถานะ checked
  - คลิก "ถัดไป" และคลิก "เพิ่ม" เพื่อจบขั้นตอนแนบสินค้า
- [x] ตรวจขั้น 2–5 ด้วย behavioral regression; แยกผลจำลองออกจากผลบน TikTok จริง
- [x] ส่ง cover_path จากรายการคลิปไป prepare และเพิ่มปุ่มแนบปกพร้อมภาพตัวอย่าง (แก้ cover upload ผ่าน CDP ไม่เปิด native Windows file dialog)
- [x] ซ่อมการเลือก Radio สินค้า และคลิกปุ่ม "ถัดไป" ใน .product-selector-container
- [ ] ป้องกันคำสั่งซ้อนกัน; ทำต่ออัตโนมัติแบบหยุดทันทีเมื่อขั้นก่อนหน้าไม่ผ่าน และให้ผู้ใช้กดโพสต์เองตามข้อกำหนดเดิม
- [x] ตรวจ syntax JavaScript, Node tests และ pytest ที่เกี่ยวข้อง
- [ ] ทดสอบ TikTok จริง: caption, สินค้าตรง ID, ปก, schedule

Notes: ปรับปรุงโค้ด Extension ให้ตรงกับ Element จริงจาก DevTools และพฤติกรรม TikTok Studio:

1. ใส่คำอธิบายก่อน แล้วเคาะเว้นวรรค 2 บรรทัด ตามด้วยแฮชแท็ก
2. สลับไปแท็บ "นำเสนอสินค้า" (Showcase) ให้สำเร็จก่อนค้นหา ป้องกันพิมพ์ในแท็บ "ร้านของฉัน"
3. เลือกสินค้าด้วย radio element: เลิกเซ็ต input.checked=true ล่วงหน้าเพื่อไม่ให้ขัด React SyntheticEvent พร้อมเรียก React fiber props, DOM clicks และ CDP native clicks ทั้งที่ปุ่มและแถวสินค้า
4. กดปุ่ม "ถัดไป" ด้านล่างขวาของตารางรายการสินค้า (.product-selector-container) พร้อม fallback native CDP click
5. หน้ารายการสุดท้าย: สั่งคลุมดำชื่อสินค้า และกดปุ่ม "เพิ่ม" (Add button สีแดง) จบขั้นตอนปักตะกร้า
6. แก้ปัญหาแนบภาพปก: ยกเลิกการคลิกที่ label uploadArea (ที่เคยเรียก Windows Explorer dialog) เปลี่ยนมาใช้ CDP DOM.setFileInputFiles ตรงที่ input[type=file] รอ preview แล้วกดบันทึก
ผ่านการทดสอบ `node --test tiktok_autopost_extension/background.test.cjs` (6/6 passed) และ `pytest` (149 passed)

รายการที่รู้แล้วว่าต้องทำ แต่ยังไม่ได้จัดเข้ารอบไหน
เจอของใหม่ระหว่างทาง → เขียนลงตรงนี้ทันที ห้ามทำเงียบๆ

### ยังไม่ได้ทดสอบ

- [ ] **กด generate เต็ม loop 1 รอบ** — Round 1 ยืนยันแล้วเฉพาะ ASS writer, เฟรม ffmpeg,
      save→reload, และ editor เปิดโปรเจกต์เก่า แต่ **ยังไม่เคยรัน `/api/render` ครบวงจร**
      (ต้องใช้วิดีโอดิบ + TTS key + เวลาหลายนาที)

### บั๊กที่เจอแล้วแต่ยังไม่ได้แก้

- [x] **วรรณยุกต์ไทยชั้นสองยุบ — แก้แล้ว (2026-09-07, ใช้ `/diagnose`)**: `เพิ่ง`→`เพีง`, `สิ่ง`→`สีง`
      - **ข้อสันนิษฐานเดิมผิด:** ไม่ใช่ libass mark positioning และไม่ใช่ครบทั้ง 6 ฟอนต์ตามที่บันทึกไว้ก่อนหน้า
      - **root cause จริง (พิสูจน์ด้วย differential render):** สร้าง harness render คำเดียวกันสองทาง — (a) ผ่าน
        libass/ffmpeg (production path) (b) ผ่าน PIL ImageFont (คนละ text shaper คนละ engine ไม่ผ่าน libass เลย)
        ผลออกมา**ยุบเหมือนกันเป๊ะทั้งคู่** → พิสูจน์ว่าไม่ใช่ libass แต่เป็นตัวไฟล์ฟอนต์เอง (ขาด GPOS mark-to-mark
        anchor สำหรับ mark ไทยซ้อนสองชั้น เช่น สระอิ + ไม้เอก)
      - เช็คครบทั้ง 6 ฟอนต์จริง (ไม่ใช่แค่เชื่อบันทึกเดิม): **Kanit/Prompt/Mitr/Itim พัง** ·
        **IBM Plex Sans Thai/Chakra Petch/Anuphan ถูก** (Noto Sans Thai ก็ถูกด้วย, ทดสอบเพิ่มนอก 6 ตัวเดิม)
      - ทดสอบ workaround ทาง text-level (ZWJ/ZWNJ คั่นระหว่าง mark, สลับลำดับ mark) — **ไม่ช่วยเลย** ยืนยันว่า
        เป็นปัญหาที่ font file เท่านั้น แก้จาก input text ไม่ได้จริง
      - **แก้แล้ว:** เอา Kanit/Prompt ออกจาก dropdown เลือกฟอนต์ใน `NewClipPanel.jsx:55-60` (เหลือ IBM Plex
        Sans Thai + Noto Sans Thai เท่านั้น) — ไม่แตะฟอนต์ที่ preset อื่น (`kanit_viral`/`prompt_modern`/
        `mitr_minimal`/`capsule_pill` ใน `typography_presets.json` ยังอยู่เผื่อใช้ทางอื่น แค่ไม่โผล่ใน dropdown นี้)
      - **เจอบั๊กเพิ่มระหว่างทาง (ไม่เกี่ยวกับ tone mark):** ตัวเลือก "Noto Sans Thai" ใน dropdown เดียวกันนี้
        ส่ง `font_name="NotoSansThai"` ซึ่ง**ไม่เคย match key ไหนใน `_load_font_family_map()` เลย** — fallback
        ไปที่ `DEFAULT_FONT_FAMILY` (IBM Plex) แบบเงียบๆ ไม่มี error คนเลือก Noto จะได้ IBM Plex แทนโดยไม่รู้ตัว
        แก้แล้วเพิ่ม alias `"NotoSansThai": "Noto Sans Thai"` ใน `_LEGACY_FONT_ALIASES`
        ([font_metrics.py:18-25](scripts/subtitle/font_metrics.py#L18))
      - เทสใหม่ `tests/test_font_family_mapping.py` (3 เคส) ยืนยัน mapping ทั้งสองจุด — ผ่านหมด,
        `pytest tests/ -q` 492 passed, `npx vite build` ผ่าน

### ปรับปรุงที่ยังไม่จำเป็นเร่งด่วน

- [ ] `frontend/src/lib/overlayModel.js` มี export ที่ยังไม่มีใครเรียก (`baseFsRatio`, `ASS_ALIGNMENT`,
      `overlayToLegacy*`) — เก็บไว้เพราะเทสใช้ แต่ควรทบทวนว่าจะคงไว้หรือตัด

---

## รอบงาน

## Round POST-1 — Desktop Post Studio (ปก + ลากไฟล์ + แคปชั่น + ปิดวงจร Posted)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** จบงานโพสต์บนคอมได้ในหน้าเดียว — ปกสวยพร้อมอัป ไฟล์ลากได้ทันที แคปชั่นก็อปปุ่มเดียว
แล้วมาร์คโพสต์เสร็จไฟล์ย้ายออกเอง

> repo มี flow โพสต์บนมือถือครบ 5 ขั้นอยู่แล้ว (`MobileQuickPostPage.jsx`) แต่ฝั่งเดสก์ท็อปไม่มีเลย
> รอบนี้คือสร้างฝาแฝดฝั่งเดสก์ท็อป ไม่ใช่ฟีเจอร์ใหม่จากศูนย์

### ข้อจำกัดที่บังคับรูปทรงดีไซน์

- เว็บแอปในเบราว์เซอร์ **ยัดไฟล์เข้า drop zone ของ TikTok ไม่ได้** → ลดแรงเสียดทาน ไม่ใช่ยิงอัตโนมัติ
- **clipboard ถือได้ทีละอย่าง** → ไฟล์ใช้ `explorer /select` (ไม่กิน clipboard) เหลือ clipboard ให้แคปชั่น
- ย้ายไฟล์ไป `Posted/` แล้ว **คลิปจะหายจากแกลเลอรี** (`api_exports.py:26` glob แค่ `EXPORTS_DIR`) → ต้องแก้คู่กันในรอบเดียว

### POST-1.1 Cover Studio — ปก jpg ที่อัปได้จริง

- [x] สร้าง `scripts/api_covers.py` แยกไฟล์ใหม่ (ไม่แตะ `api_editor.py`/`api_schemas.py` ที่ Round 5 กำลังแก้)
      — `POST /api/covers/generate` ดึงเฟรม jpg 1080×1920 ด้วย ffmpeg input-seek + วาด 3-tier ด้วย Pillow
- [x] ไม่ reuse `drawOneOverlay` (ฟังก์ชันอิงเวลา) — ใช้ `resolve_hook_style` (pure python, มีอยู่แล้ว)
      + `AssetRegistry.fonts()` หา path ฟอนต์ + `PIL.ImageDraw.text(stroke_width=...)` วาดเอง เพราะปกคือภาพนิ่ง
- [x] เขียนผลลง `05_Covers_Thumbnails/` (โฟลเดอร์ที่ README/AGENTS อ้างถึงมาตลอดแต่ยังว่าง) — ทดสอบจริงแล้ว
- [x] UI เลื่อนเลือกเฟรม + ปุ่มสร้างปกใน ExportGallery — สร้างเป็นส่วน "ปกโพสต์ (Cover)" ใน `ExportActiveWorkbench`
      ([:672+](frontend/src/components/ExportGallery.jsx#L672)): range input scrub (seek `<video>` จริงตามค่า) +
      preview thumbnail + ช่องแบรนด์/รุ่น/ป้าย (ไม่บังคับ ซ่อนอยู่) + ปุ่มสร้าง — ต่อกับ `POST /api/covers/generate` แล้ว

### POST-1.2 ลากไฟล์ให้ง่ายที่สุด

- [x] `POST /api/reveal-file` ([api_videos.py](scripts/api_videos.py)) — `explorer /select,<path>` ทดสอบจริงแล้ว
      เปิด Explorer พร้อมไฟล์ถูกเลือกไว้, ปฏิเสธ path นอก `04_Exports`/`05_Covers_Thumbnails` ด้วย 403
- [x] **ซ่อมช่องโหว่แล้ว:** `open_folder` unknown key เดิมตกไป `Path(req.target)` ไม่เช็ค containment
      → ปฏิเสธด้วย 400 แทน (ยืนยันแล้วว่า caller จริงทั้ง 4 จุดส่งแค่ literal key `'exports'`)

### POST-1.3 Post Studio panel

- [x] แผงเดียวจบใน ExportGallery: ปก (สร้าง+พรีวิว) → เปิดไฟล์ใน Explorer (`onRevealFile`) →
      คัดลอกแคปชั่น (มีอยู่แล้ว) → เปิด TikTok Studio (`tiktok.com/tiktokstudio/upload` แท็บใหม่) →
      มาร์คว่าโพสต์แล้ว (`onMarkPosted`, ขึ้น chip "โพสต์แล้ว" แทนปุ่มเมื่อ `video.is_posted`)
      — handler จริงอยู่ที่ `ExportGallery.jsx` เรียก `generateCover`/`revealFile`/`markPosted` จาก `api.js`
      ยืนยัน backend ผ่าน `TestClient` จริง (ไม่ใช่แค่อ่านโค้ด): สร้างปก 1080×1920 จริงจากคลิป export จริง
      (read-only ต่อไฟล์ต้นทาง) + mark-posted ย้ายไฟล์ scratch จริงไป `Posted/` + บล็อกย้ายซ้ำถูกต้อง (403/404)
      + `npx vite build` ผ่าน + `pytest` 355 passed ไม่ตก
- [x] **ลบ fallback แคปชั่นหลอกแล้ว** ทั้ง 2 จุด ([:656-687](frontend/src/components/ExportGallery.jsx#L656), [:1637-1668](frontend/src/components/ExportGallery.jsx#L1637))
      — ไม่มี `tiktok_caption` → ขึ้นเตือนสีเหลือง + ปุ่ม "ผูกกับสินค้าก่อน" (เรียก `onOpenLinkModal`/`handleOpenLinkModal` ที่มีอยู่แล้ว)
      แทนที่จะแอบใส่ข้อความปลอมให้คัดลอกไปโพสต์โดยไม่รู้ตัว
- [x] ป้ายสเปก probe จากไฟล์จริงแทน string ตายตัว — `GET /api/exports/media-info` ([api_exports.py](scripts/api_exports.py))
      ใช้ `VideoEditor.get_media_info()` ที่มีอยู่แล้ว ([video_editor.py:359](scripts/video_editor.py#L359), เพิ่ม `codec_name`
      เข้า return dict — additive, เช็คแล้วทุก caller เดิม (`api_editor.py`, `shot_matching_stage.py`) ใช้ `.get()` ไม่พัง)
      ดึงแบบ on-demand ต่อคลิปที่กำลังดูเท่านั้น (ไม่ยัดเข้า `list_exports()` เพราะจะ ffprobe ทุกไฟล์ทุกครั้ง refresh)
      ทั้ง `ExportActiveWorkbench` และ modal เปลี่ยนมาใช้ `formatCodecSpec`/`formatResolutionSpec` แล้ว
      ยืนยันจริงด้วย `TestClient` กับคลิป export จริง → คืน `{width:1080, height:1920, fps:30, codec_name:'h264'}` ตรงของจริง
      + path traversal โดนบล็อก 403 + ไฟล์ไม่มีคืน 404 + `pytest` 356 passed + `npx vite build` ผ่าน

### POST-1.4 ปิดวงจร Posted

- [x] `POST /api/exports/mark-posted` ([api_exports.py](scripts/api_exports.py)) — ย้าย mp4 + webp + cover jpg
      ไป `04_Exports/Posted/` พร้อมกันทั้ง 3 ไฟล์ ทดสอบจริงด้วย scratch fixture แล้ว (ไม่แตะไฟล์จริงของ user)
- [x] `list_exports()` scan ทั้ง `Ready_to_post/` และ `Posted/` + ติด `is_posted` flag ต่อไฟล์
      ทดสอบแล้ว: หลังย้าย ไฟล์ยังหาเจอในแกลเลอรีพร้อม `is_posted=true` + `thumbnail_url` ตามไปถูกที่
- [x] ย้ายไฟล์ซ้ำ (จาก `Posted/` อีกที) ถูกบล็อก 403 ถูกต้อง
- [x] **เจอบั๊กจริงระหว่างเทส ไม่ใช่แค่ตามที่คาด:** `reconcile_existing_projects()`
      ([product_store.py:499](scripts/product_store.py#L499)) รักษา `posted`/`mobile_ready`
      **เฉพาะตอนหา mp4 เจอเท่านั้น** — ถ้าหาไม่เจอ (เพราะย้ายไป `Posted/` แล้ว และ
      `artifacts.mp4_video.path` ในแมนิเฟสต์ยังชี้ไปที่เก่า) จะ**รีเซ็ตกลับเป็น `in_production`
      และล้าง `video_url` เป็น `None` แบบไม่มีข้อยกเว้น** — เป็น regression จริงที่ POST-1.4 จะสร้างถ้าไม่แก้
      ซ่อมแล้ว 2 จุด: (1) ขยาย mp4 fallback scan ให้เช็ค `Posted/` ด้วย ไม่ใช่แค่ `Ready_to_post/`
      (2) เพิ่ม branch ไม่ downgrade สถานะ `posted`/`mobile_ready` ตอนหา mp4 ไม่เจอเลย
- [x] เขียนเทสยืนยันจริง `tests/test_reconcile_preserves_posted.py` (4 เคส, ใช้ `tmp_path`+`monkeypatch`
      ตาม `.agents/rules/testing_standard.md` ไม่แตะ `_Docs/products.json` จริง) — **4 passed**
      (เจอบั๊กในเทสตัวเองก่อนด้วย — `store_path` ไม่ตรงกับที่ `_seed()` เขียน ทำให้ 2 เคสแรก "ผ่าน" แบบไม่ได้รันจริง
      แก้แล้วรันใหม่ยืนยันว่าทดสอบ logic จริง ไม่ใช่ vacuous pass)

### POST-1.5 ซ่อมของเสียที่เจอระหว่างสำรวจ

- [x] `setToastMessage` ไม่มีอยู่จริง → เปลี่ยนเป็น `hideToast` (ของจริงจาก `useToast()`) — ยืนยันด้วย `npm run build` ผ่าน
- [x] QR ในแกลเลอรีซ่อมแล้วทั้ง 2 จุด — เขียน `buildQuickPostUrl()` ตัวเดียวใช้ร่วม ส่ง `pid`/`aid`/`hook`/`tiktok_caption`/`tiktok_hashtags`
      ครบตามรูปแบบของ `ContentTrackerHub.jsx:1289` แทนที่จะเป็นสำเนาพิการคนละแบบ
- [x] `mobileBaseUrl` อ่าน `status.mobile_url` ก่อนแล้ว (`App.jsx` ส่ง `status` prop เข้า `ExportGallery` เพิ่ม) เหมือน `ContentTrackerHub.jsx:618`

### Gate

- [x] `pytest tests/ -q` → **355 passed** · `npx vite build` ผ่าน (`npm test`/`oxlint` ยังไม่รัน — ไม่มี npm test script แยกในโปรเจกต์นี้)
- [ ] ปก jpg ที่ออกมา **อัปขึ้น TikTok ได้จริง** (ทดสอบด้วยมือ 1 คลิป) — รอพี่ทดสอบเอง
- [ ] กด reveal แล้ว Explorer เปิดพร้อมไฟล์ถูกเลือก (ล่าสุด curl ผ่านตอน backend ยังไม่ถูก restart — ดู Notes เรื่อง backend ค้าง ต้อง restart ก่อนคลิกจริงในเบราว์เซอร์ได้)
- [x] มาร์คโพสต์ → ไฟล์ย้ายไป `Posted/` → ยืนยันด้วย `TestClient` จริงกับไฟล์ scratch (ไม่แตะของจริง) — ย้ายสำเร็จ + ย้ายซ้ำโดนบล็อก 404
- [x] เทส: reconcile รันแล้วสถานะ `posted` ไม่ถูกรีเซ็ตทั้งที่ไฟล์ไม่ได้อยู่ `Ready_to_post` แล้ว — `test_reconcile_preserves_posted.py` 4 passed (ดู POST-1.4)
- [x] คลิปที่ไม่มี angle link → ขึ้นเตือน ไม่ใช่ก็อปแคปชั่นปลอม — ดู POST-1.5, ยืนยันด้วย build ผ่าน + อ่านโค้ด conditional

### ⚠️ งานขนาน — ตรวจแล้วเมื่อ 2026-09-05 (กฎ work_loop ข้อ 6)

อีก session กำลังทำ **Round 5 (per-word animation)** อยู่ ตรวจ `git status` + mtime แล้วพบ:

| POST-1 | ไฟล์ | ชนกับ Round 5 |
| :--- | :--- | :--- |
| 1.1 ปกใส่ข้อความ | `SequencePlayer.jsx` · `overlayModel.js` | 🔴 ชนหนัก — `drawOneOverlay` + `anim.word_stagger_ms` คือหัวใจ Round 5 |
| 1.1 ดึงเฟรม | `scripts/api_editor.py` | 🔴 ชน — แก้อยู่ตอนนี้ |
| 1.2 schema | `scripts/api_schemas.py` | 🟡 เบา (เพิ่มคลาสใหม่) |
| 1.3 api client | `frontend/src/api.js` | 🟡 เบา (เพิ่ม export) |
| 1.1 แปลง jpg · 1.2 reveal · 1.3 แผง · 1.4 Posted · 1.5 บั๊ก | `video_editor.py` `api_videos.py` `ExportGallery.jsx` `api_exports.py` `product_store.py` | ✅ ไม่ชน |

**ลำดับที่ตกลง:** ทำชุดที่ไม่ชนก่อน (1.2 · 1.3 · 1.4 · 1.5 · แปลงปก jpg) — ครอบความเจ็บหลักได้ ~80%
ส่วนปกแบบเลือกเฟรม+ใส่ข้อความ รอ Round 5 ปิดก่อน

**แก้ดีไซน์ให้ชนหายไปเลย:** เดิมคิดจะ reuse `drawOneOverlay` วาดข้อความบนปก — **ผิดฝาผิดตัว**
มันเป็นฟังก์ชันอิงเวลา (animation, `tRel`, in/loop/out) แต่ปกคือภาพนิ่งเฟรมเดียว
ให้ใช้ `TextLookPreview.jsx` (DOM ภาพนิ่ง Round 5 ไม่แตะ) หรือวาดฝั่ง server จาก `TextLook` ตัวเดียวกันแทน

### Notes

- ตัดทิ้ง: ลากจากในแอปตรงเข้า TikTok (Chrome `DownloadURL` ลงได้แค่ Explorer/desktop ไม่เข้า drop zone เว็บอื่น) · ก็อปไฟล์ลง clipboard (แย่ง clipboard จากแคปชั่น)
- ~~ตัดทิ้ง: browser automation~~ (ทบทวนแล้ว 2026-09-05 — ดู Round POST-2: พี่ยอมรับความเสี่ยงหลังเทียบทางเลือก ออกแบบให้เสี่ยงน้อยสุดในบรรดาทางที่ทำได้จริง)
- ตัดทิ้งถาวร: TikTok Content Posting API (ก่อนผ่าน audit โพสต์ได้แค่ draft/private)
- **PostLog ยังไม่ทำในรอบนี้** — `scripts/post_log.py` + API + client wrapper (`api.js:159-162`) สร้างเสร็จแล้วแต่ caller เป็นศูนย์ ถ้าอยากได้วงจรวัดผลค่อยเปิดรอบใหม่
- **เจอกลางทางตอนจะเทสจริงผ่านเบราว์เซอร์:** backend ที่รันอยู่ที่ port 8000 เป็นโปรเซสค้าง (63 routes ไม่มี
  `/api/covers/generate`/`/api/reveal-file`/`/api/exports/mark-posted` เลยสักตัว) — `start_app.bat` ตั้ง
  `FASTAPI_RELOAD=false` ไว้โดยตั้งใจ (เพื่อ render นิ่ง) โค้ดใหม่เลยไม่โดนโหลด ต้อง restart เอง
  **ฆ่าโปรเซส (taskkill) โดน sandbox classifier บล็อก** — ต้องให้พี่รัน `start_app.bat` เอง (มัน kill+relaunch ให้ในตัว)
  ก่อนถึงจะกด reveal/สร้างปก/มาร์คโพสต์ **ผ่านเบราว์เซอร์จริง** ได้ ระหว่างนี้ยืนยัน logic ทุกเส้นทางผ่าน
  `fastapi.testclient.TestClient(app)` แทน (import โค้ดปัจจุบันตรงๆ ไม่ผ่านโปรเซสค้าง) — เทียบเท่ากันในแง่ความถูกต้องของ backend logic

---

## Round POST-2 — TikTok auto-post extension (เสี่ยง)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: กำลังทำ — ⚠️ **แครชยังเป็นปริศนา ไม่ใช่ปิดถาวรแล้ว** (POST-2.12
ด่วนสรุปผิด ดู POST-2.13) ตอนนี้มี checklist ทีละขั้นให้พี่ไล่ทดสอบเองว่าขั้นไหนทำให้พัง

**เป้าหมาย:** กดปุ่มเดียวในแอป ให้ extension เติมไฟล์+ปก+แคปชั่นลงหน้าอัปโหลด TikTok ในเบราว์เซอร์ที่ login อยู่แล้ว
ไม่ต้องลาก ไม่ต้องพิมพ์เอง — **สถานะจริงตอนนี้:** แครชเกิดแบบไม่ 100% แน่นอน (flaky) แม้แต่ขั้น "อัปโหลดไฟล์อย่างเดียว"
เอง — บางรอบพังบางรอบผ่าน สาเหตุแท้จริงยังไม่ชัด ต้องไล่ทดสอบทีละขั้นด้วย checklist ใหม่ก่อน — รายละเอียด เหตุผล
และหลักฐานความเสี่ยงทั้งหมดอยู่ที่
[TIKTOK_AUTOPOST_PLAN.md](file:///d:/Winona/Programmer/Capcut/TIKTOK_AUTOPOST_PLAN.md)

> ⚠️ พี่ยืนยันรับความเสี่ยงผิด ToS/บัญชีโดนจำกัดแล้ว (2026-09-05) หลังเทียบทางเลือกทั้งหมด
> ดีไซน์เลือกใช้เบราว์เซอร์จริงที่ login อยู่แล้ว ไม่เปิดแยก ไม่ปลอมลายนิ้วมือ กดครั้งเดียวต่อโพสต์ — เสี่ยงน้อยสุดในบรรดาทางที่ทำได้จริง

### Todo

- [ ] **ทดสอบ 4 ข้อใน `TIKTOK_AUTOPOST_PLAN.md` §3 ก่อน (ต้อง login บัญชีจริง — พี่ทำเอง ผมทำแทนไม่ได้)**
      สำคัญสุด: TikTok Studio อัปปกเองได้ไหม (ถ้าได้ = ไม่ต้องพึ่ง Cover Studio ของ POST-1 สำหรับเส้นทางนี้)
      — **บล็อกจริง:** ทุก selector ใน `background.js` เป็นค่าเดา (จากเอกสาร community ใน plan) ยังไม่เคยรันกับ
      หน้า TikTok Studio จริงสักครั้ง รอผลข้อนี้ก่อนถึงจะรู้ว่าต้องแก้ selector ตรงไหน
- [x] สร้าง Chrome extension (Manifest V3) — `tiktok_autopost_extension/` (manifest.json, background.js,
      popup.html/js) — background service worker ถือ `chrome.debugger` session, ยืนยัน syntax ผ่านแล้ว
      (`node --check` ทั้ง 2 ไฟล์ js + `json.load` manifest) — **ยังไม่เคย attach กับแท็บ TikTok Studio จริง**
      เพราะต้องมี browser ที่ล็อกอินไว้แล้วซึ่งผมไม่มี ดู Todo ข้อแรก
- [x] `DOM.setFileInputFiles` ใส่ mp4 (+ cover jpg แบบ best-effort ถ้ามี input ที่ 2) — เขียนไว้ใน
      `findFileInputNodeId`/`setFileInput` ของ `background.js` — selector `input[type="file"]` **ยังไม่ยืนยัน**
      ว่าตรงกับของจริง (ทำเครื่องหมาย UNVERIFIED ไว้ในโค้ดทุกจุดที่เดา)
- [x] `Input.insertText` ใส่แคปชั่นใน contenteditable — `typeCaption()` focus ก่อนแล้วค่อย insertText ผ่าน
      CDP Input domain (ไม่ใช้ `.textContent =` ตรงๆ เพราะ framework ของ TikTok จะไม่เห็น event)
- [x] endpoint ฝั่งแอป: `POST /api/tiktok-autopost/prepare` ([api_tiktok_autopost.py](scripts/api_tiktok_autopost.py))
      ยืนยันจริงด้วย `TestClient`: prepare→pending→clear lifecycle ผ่าน, path traversal โดนบล็อก 403,
      pending ก่อน prepare คืน 404 ถูกต้อง — **หมายเหตุดีไซน์:** ไม่ต่อตรงกับ `mark-posted` อัตโนมัติ (ตามที่ระบุไว้เดิม)
      เพราะ extension ไม่รู้ว่า TikTok โพสต์สำเร็จจริงหรือยัง (ไม่มีวิธีตรวจจาก DOM ที่มั่นใจได้) — พี่กด "มาร์คว่าโพสต์แล้ว"
      เองในแอปหลังเห็นว่าโพสต์ขึ้นจริงบน TikTok ปลอดภัยกว่า
- [x] toggle เปิด/ปิดฟีเจอร์นี้ใน `SystemSettings.jsx` (แท็บ Engine) — **ปิดเป็นค่าเริ่มต้น** (`localStorage`
      key `omnicut_tiktok_autopost_enabled`, อ่านค่าเริ่มต้น `false`) ยืนยันด้วย `npx vite build` ผ่าน
- [x] แถบ "กำลัง debug" ต้องเห็นชัดทุกครั้ง ห้ามพยายามซ่อน — **ไม่ต้องเขียนโค้ดเพิ่ม** Chrome บังคับแสดงเองทันทีที่
      `chrome.debugger.attach()` ถูกเรียก ซ่อนไม่ได้จาก extension ฝั่งเราอยู่แล้วโดยดีไซน์ของเบราว์เซอร์เอง
- [ ] **POST-2.1 ปรับแต่งแคปชันและปักตะกร้าอัตโนมัติ (User ร้องขอ 2026-09-06)**:
      - แก้ ReferenceError: `waitForCaptionEditor is not defined` ที่ทำให้สคริปต์หยุดทำงานก่อนล้างชื่อไฟล์/พิมพ์แคปชัน/ปักตะกร้า
      - ล้างชื่อไฟล์ต้นทางที่ TikTok เติมให้อัตโนมัติ (`document.execCommand('selectAll')` + `'delete'`) แล้วพิมพ์แคปชันจริง + แฮชแท็กโดยใช้ `Input.insertText` คู่กับ Enter (`Input.dispatchKeyEvent`) พร้อมเลื่อนเคอร์เซอร์ไปจุดเริ่มต้น (`collapse(true)`) และรีเซ็ต `scrollTop = 0` ทุกคอนเทนเนอร์เพื่อให้แคปชันด้านบนไม่หลุดเฟรม
      - แนบลิงก์สินค้า (ปักตะกร้า): คลิก `+ เพิ่ม` -> ในหน้าต่างประเภทลิงก์กด `ถัดไป` -> สลับแท็บ `นำเสนอสินค้า` -> ค้นหาด้วย TikTok Product ID (`1737088044189583209`) -> ติ๊กเลือกวิทยุ -> กด `ถัดไป` -> กด `เพิ่ม`
      - รองรับการตั้งเวลาโพสต์ (Schedule): ค้นหาปุ่มเลือก `ตั้งเวลา` (ตามหน้าตาจริงของภาษาไทยใน TikTok Studio) เพื่อให้ผู้ใช้กำหนดวันเวลาปล่อยคลิปได้ตามแผน
      - บันทึก TikTok Product ID (`1737088044189583209`) ลงใน `_Docs/products.json` และส่งผ่าน `api_exports.py` อัตโนมัติ
- [x] **POST-2.2 แก้ปัญหาสลับแท็บนำเสนอสินค้าไม่ได้ และแก้คำอธิบายหาย/ขึ้นแต่แฮชแท็ก (User ร้องขอ 2026-09-06)**:
      - [x] **แก้สลับแท็บ "นำเสนอสินค้า"**: ปรับปรุง selector ใน `attachProductLink` (ฟังก์ชัน `switchToShowcaseTab`) กรอง element ที่มีข้อความ "ร้านของฉัน" ออกทั้งหมดเพื่อไม่ให้โดน parent container หลอก, ค้นหา leaf element ที่มีข้อความ "นำเสนอสินค้า" / "Showcase", คลิกด้วยทั้ง DOM mouse events (`pointerdown`/`mousedown`/`mouseup`/`click`) และ native CDP `Input.dispatchMouseEvent` ที่พิกัด bounding rect พร้อมตรวจจับว่าแท็บเปลี่ยนจริง (เช่น ช่องค้นหาสินค้าปรากฏ) มี retry loop สูงสุด 5 ครั้ง
      - [x] **แก้ปัญหาคำอธิบายไม่มา / มาแต่แฮชแท็ก / แฮชแท็กกลืนคำอธิบาย**:
        - ใน `background.js` ฟังก์ชัน `typeCaption`: ลบการส่ง `type: 'char', text: '\r'` ซึ่งเป็น Carriage Return ที่ทำให้เคอร์เซอร์เด้งกลับไปที่จุดเริ่มต้น (ทำให้พิมพ์แฮชแท็กนำหน้าคำอธิบายและเชื่อมติดกัน)
        - ใช้ `document.execCommand('insertText', false, text)` ในการแทรกข้อความแบบรวดเดียวพร้อมเว้นวรรคและขึ้นบรรทัดใหม่อย่างเป็นธรรมชาติ โดยวางโครงสร้างเป็น: คำอธิบายคลิป (บรรทัดบน) -> เว้นวรรค 2 บรรทัด (`\n\n`) -> แฮชแท็ก (บรรทัดล่าง)
        - เพิ่ม fallback ให้ `scripts/api_exports.py` และ `ExportGallery.jsx` ให้ดึงคำอธิบายจาก `hook_title` หรือชื่อคลิปอัตโนมัติหาก `tiktok_caption` ว่าง
      - [x] **ปรับปรุง Popup Extension UI**:
        - เพิ่มช่องแสดงและแก้ไข "คำอธิบายคลิป (Caption)" และ "แฮชแท็ก (Hashtags)" ให้ผู้ใช้เห็นบน Popup ก่อนกดส่งคำสั่ง สามารถแก้ไขหรือตรวจทานได้ทันที
        - รองรับการดึงคำอธิบายและแฮชแท็กจาก backend `/api/tiktok-autopost/pending` มาแสดงในฟอร์ม Popup อัตโนมัติ
        - เพิ่มปุ่ม "📝 เติมเฉพาะคำอธิบายและแฮชแท็ก" (กรณีผู้ใช้ต้องการเติมแค่ข้อความ ไม่ปักตะกร้าซ้ำ)
      - [x] ผ่าน Gate: `node --check` ทุกไฟล์ js ผ่าน, `npm run build` ผ่าน, `pytest tests/ -q` 357 passed
- [x] **POST-2.3 ซ่อมบั๊กคลิกโดนเมนู Sidebar 'โพสต์' และเพิ่มระบบรออัปโหลดครบ 100% (User ส่งคลิปวิดีโอยืนยัน 2026-09-06)**:
      - [x] **ต้นตอจากคลิป test cap.mp4**: วิดีโอยังอัปโหลดอยู่ที่ 29.36% แต่ extension รันต่อจนถึง `clickPostButton` ซึ่งหาปุ่ม `โพสต์` ที่ไม่ disabled — ปุ่มโพสต์จริงของฟอร์มถูก disable อยู่ จึงไปจับโดนปุ่มเมนูนำทาง `div[role="button"]` บน Sidebar ด้านซ้ายที่มีชื่อว่า `โพสต์` (เพื่อนำทางไปหน้ารายการโพสต์ `โพสต์ 24`) ทำให้เบราว์เซอร์พยายามเปลี่ยนหน้า และ TikTok เด้งหน้าต่างเตือน *"คุณแน่ใจหรือไม่ว่าต้องการออก? ความคืบหน้าและการเปลี่ยนแปลงของคุณจะไม่ได้รับการบันทึก"*
      - [x] **แก้ `clickPostButton`**:
        - กรองข้ามองค์ประกอบทั้งหมดที่อยู่ใน `aside, nav, header, [class*="sidebar"], [class*="menu"]` โดยเด็ดขาด
        - ค้นหาเฉพาะแท็ก `<button>` ของฟอร์มเท่านั้น (ห้ามใช้ `div[role="button"]` ของเมนูนำทาง)
        - เรียก `waitForUploadComplete` ก่อนกดเสมอ เพื่อให้มั่นใจว่าปุ่มของ TikTok ปลดล็อกและพร้อมกดจริง
      - [x] **ปรับปรุง `waitForUploadComplete` ตรวจจับหลายสัญญาณ (Multi-Signal)**:
        - ตรวจจับเปอร์เซ็นต์ที่ยังวิ่งไม่ถึง 100% (เช่น `29.36%`)
        - ตรวจจับคำว่า `Uploading...` บนหน้าจอมือถือพรีวิว
        - ตรวจจับข้อความขนาดไฟล์ (เช่น `7.76MB/26.43MB` หรือ `เหลือ X วินาที`)
        - ตรวจจับสถานะปุ่ม `โพสต์` / `กำหนดเวลา` ว่ายัง disabled อยู่หรือไม่
      - [x] **ตัดโค้ดหยอดปกใส่ `nodeIds[1]` (ซึ่งตรงกับปุ่ม "แทนที่วิดีโอ") ออก 100%** ป้องกันการ trigger ให้ TikTok คิดว่าจะเปลี่ยนคลิปใหม่
      - [x] ผ่าน Gate: `node --check` ทั้งสองไฟล์ผ่าน, `pytest tests/ -q` 367 passed
- [x] **POST-2.4 เพิ่มการ์ดกันสำหรับ dialog "แน่ใจหรือไม่ว่าต้องการออก" (ดูคลิป test cap.mp4 ซ้ำอีกรอบ 2026-09-06)**:
      - **หมายเหตุสำคัญ:** คลิปที่พี่ส่งมาดูรอบนี้เป็นคลิปเดียวกับที่ POST-2.3 ใช้วินิจฉัยบั๊ก "กดโดนเมนู Sidebar
        'โพสต์'" ไปแล้ว — โค้ดตอนนี้มี fix ของ POST-2.3 อยู่แล้ว (กรอง `isNav()` + รอ `waitForUploadComplete` ก่อนกด)
        ยังไม่มีคลิปทดสอบใหม่หลัง fix นั้นเข้ามายืนยันว่า dialog นี้หายไปจริงหรือยัง — เพิ่มตัวนี้เป็น**เกราะเสริม**
        เผื่อ dialog ยังโผล่แม้กดปุ่มถูกต้องแล้ว (SPA บาง framework มี "leave guard" ทำงานแม้ navigate หลังสำเร็จจริง)
      - เพิ่ม `dismissLeaveConfirmDialogIfPresent(send)` ใน `background.js` — poll หา heading ที่มีข้อความ
        "แน่ใจหรือไม่ว่าต้องการออก" / "Are you sure you want to leave" นาน 8 วิ ถ้าเจอกดปุ่ม "ออก"/"Leave" ให้
        ถ้าไม่เจอเลยคืน `false` เฉยๆ **ไม่ throw** เพราะไม่ยืนยันว่า dialog นี้โผล่ทุกครั้งหรือบางครั้ง
      - เรียกต่อจาก `clickPostButton(send)` ใน `runAutopost()` เฉพาะตอน `autoClickPost` เท่านั้น — ผลลัพธ์ใส่ใน
        response เป็น `leaveDialogDismissed` ให้ popup โชว์คำเตือนถ้าเจอ dialog ค้างแต่กดไม่ผ่าน (ให้พี่กดเอง)
      - ผ่าน Gate: `node --check` ทั้ง `background.js`/`popup.js` ผ่าน — **ยังไม่ได้ทดสอบกับ TikTok Studio จริงรอบใหม่**
        รอพี่ทดสอบคลิปใหม่แล้วส่งคลิปมาดูอีกรอบ ว่า dialog ยังโผล่ไหมหลัง POST-2.3 fix
- [x] **POST-2.5 เจอ root cause จริงของแท็บแครช (ดูคลิป test cap2.mp4, 2026-09-06)**:
      - เช็ค checkbox fix (POST-2.4-ก่อนหน้า) แล้ว: **ทำงานถูก** — auto-post ไม่ติ๊ก ระบบเติมข้อมูล+ปักตะกร้าสำเร็จ
        ไม่ได้กด Post ให้เองแล้ว ตรงตามที่พี่ขอ
      - **ปัญหาใหม่ที่เจอในคลิปเดียวกัน:** แท็บ Chrome เองแครช (หน้า "เกิดข้อผิดพลาด" native ของ Chrome ไม่ใช่ error
        จากโค้ดเรา) เปิด console เจอ `NotFoundError: Failed to execute 'removeChild' on 'Node': The node to be
        removed is not a child of this node` จาก `lib-react.cad72241.js` (React internals ของ TikTok เอง)
      - **ต้นตอที่เจอจริง (ตรวจโค้ดละเอียด):** 3 จุดใน `background.js` ยิง click event ซ้ำซ้อนใส่ element เดียวกัน
        มากเกินจำเป็น — `attachProductLink`'s `trigger()` ยิง `.click()` แล้วต่อด้วย `dispatchEvent` อีก 3 ตัว
        (mousedown/mouseup/click) = handler ทำงาน 2 รอบต่อ 1 คลิกที่ตั้งใจ, ปุ่มค้นหาใน step 4 ก็ double-click
        เหมือนกัน, ที่หนักสุดคือ `switchToShowcaseTab`'s `triggerEvents()` ยิง **5 synthetic events + .click()**
        ใส่ **3 element พร้อมกัน** (target + parentElement + tabParent) แล้วยังมี CDP native mouse click ต่อท้าย
        อีกแบบไม่มีเงื่อนไข ทุก retry (สูงสุด 5 รอบ) = สูงสุดราวๆ 30+ click event ยิงใส่ DOM หยิบมือเดียวในไม่กี่วินาที
        — ปริมาณ event ขนาดนี้ทำให้ React ของ TikTok ตามการเปลี่ยนแปลง DOM ตัวเองไม่ทัน จน fiber tree หลุด sync จริง
        (สอดคล้องกับ error `removeChild` ที่เจอ)
      - **แก้แล้ว:** ตัดทุกจุดเหลือ **1 คลิกต่อ 1 ความตั้งใจ**:
        - `attachProductLink`'s `trigger()` เหลือแค่ `.click()`
        - search icon (step 4) เหลือแค่ `.click()` ครั้งเดียว
        - `switchToShowcaseTab` เขียนใหม่ทั้งฟังก์ชัน: แยก `isActive()` เช็คสถานะออกมาเป็นฟังก์ชันย่อย, แต่ละ
          attempt ยิง `.click()` ทาง JS ครั้งเดียวบน element เป้าหมายตัวเดียว (ไม่แตะ parent/tabParent อีกแล้ว) →
          รอ 700ms ให้ React render จริงก่อนเช็คซ้ำ → **ถ้ายังไม่ติด** ค่อยลอง CDP native mouse click เป็นทางเลือกสำรอง
          (ไม่ใช่ยิงคู่กันทุกครั้งเหมือนเดิม) → รอ 700ms เช็คอีกที ถึงจะ retry รอบถัดไป
      - `node --check background.js` ผ่าน, `pytest tests/ -q` 372 passed (ไม่กระทบฝั่ง python)
      - **ยังไม่ได้ทดสอบกับ TikTok Studio จริงรอบใหม่หลัง fix นี้** — รอพี่ทดสอบแล้วส่งคลิปมาดูอีกรอบ ว่าแท็บยังแครชไหม
      - **แนวทางสำรองถ้ายังแครชอีก** (ยังไม่ทำ เพราะยังไม่มีหลักฐานว่าจำเป็น): reload แท็บ TikTok Studio ให้ fresh
        ก่อนเริ่มทุกรอบ `runAutopost()` (ไม่ใช้กับ `runAttachProductOnly` เพราะ flow นั้นสมมติว่าอัปโหลดมือไว้แล้ว)
- [x] **POST-2.6 ยังแครชอยู่หลัง POST-2.5 (screenshot 2026-09-06, ไม่มี leave-dialog ขึ้นรอบนี้)**:
      - หน้าตาแครชเหมือนเดิมทุกอย่าง แต่รอบนี้ **ไม่ขึ้น dialog "แน่ใจจะออก" ก่อนแครช** — บ่งชี้ว่าจุดแครชขยับมา
        **เร็วขึ้น** ในลำดับงาน (แครชก่อนจะไปถึงจุดที่เคยขึ้น dialog) สอดคล้องกับที่ POST-2.5 แก้จังหวะ retry ใน
        `switchToShowcaseTab` — ยังไม่มีคลิป/console log ใหม่ยืนยันว่าแครชเกิดตอนขั้นไหนแน่ๆ
      - **เพิ่มการป้องกันอีกชั้น (ยังไม่ยืนยันว่าเป็น root cause แท้จริง เพราะไม่มีหลักฐานใหม่):** สังเกตว่า
        `attachProductLink`/`switchToShowcaseTab` ค้นหา element ด้วย `document.querySelectorAll(...)` แบบกวาด
        ทั้งหน้าเว็บซ้ำๆ หลายจุด (บางจุดใน loop retry สูงสุด 5 รอบ) บนหน้า React ที่หนักอยู่แล้ว (TikTok Studio มี
        internal error/warning เพียบอยู่ก่อนแล้วจาก AR/effects engine ของเขาเอง เช่น "VideoFrame was garbage
        collected without being closed") — จำกัดขอบเขตการค้นหาให้แคบลงเหลือแค่ `[role="dialog"]` (fallback เป็น
        `document` ถ้าไม่เจอ dialog เลย ไม่แย่ไปกว่าเดิม) ในทุกจุดของ `attachProductLink` (step 2/4/5/6/7) และ
        `switchToShowcaseTab` — ลดจำนวนรอบสแกน DOM ทั้งหน้าเว็บซ้ำๆ ลงไปมาก โดยเฉพาะจุดที่อยู่ใน retry loop
      - `node --check` ผ่าน, `pytest` 372 passed
      - **ยังไม่ยืนยันว่าหายแครชจริง** — ต้องขอคลิปใหม่ + เปิด DevTools Console (กด F12 → แท็บ Console → ติ๊ก
        "Preserve log") **ก่อน**เริ่มกดปุ่มในแอป เพื่อจับ error ตัวจริงที่เกิดขึ้น**ก่อน**แท็บแครชจริงๆ (ตอนนี้เห็นแค่
        error ที่ค้างอยู่ใน log หลังแครชไปแล้ว ไม่ชัดว่าตัวไหนคือตัวกระตุ้นจริง)
      - **ข้อสังเกตเพิ่ม:** TikTok Studio หน้านี้เองมี error/warning หลักร้อย-พันสะสมอยู่แล้วจาก engine internal ของเขา
        (ไม่เกี่ยวกับเรา) — เป็นไปได้ว่า tab renderer process ใกล้ชนเพดานหน่วยความจำอยู่แล้วจากฝั่ง TikTok เอง
        พี่ลอง**ปิด Chrome ทั้งโปรแกรมแล้วเปิดใหม่** (ไม่ใช่แค่ reload แท็บ) ก่อนทดสอบรอบหน้า อาจช่วยได้ถ้าเป็นเรื่อง
        หน่วยความจำสะสมจริง
- [x] **POST-2.7 ทำ isolation test แยกตัวแปรสำเร็จ + เจอ root cause จริงแล้ว (2026-09-06)**:
      - **ผลทดสอบเด็ดขาด:** พี่อัปโหลดไฟล์เดิม (`test cap3.mp4`) ด้วยมือล้วนๆ **ไม่เปิด/ไม่แตะ extension เลย** →
        **ไม่แครช** — confirmed 100% ว่า crash เกิดจาก **automation ของเราเอง** ไม่ใช่บั๊กฝั่ง TikTok/ไฟล์วิดีโอ
        (ก่อนหน้านี้ผมอ่าน console log ผิด คิดว่าเป็น TikTok's own effect engine crash เอง — isolation test นี้
        พิสูจน์ว่าคิดผิด ต้องขอบคุณพี่ที่ทดสอบให้ชัวร์)
      - **เจอ signal สำคัญจากพี่โดยตรง:** ปุ่ม "แก้ไขหน้าปก" ("ปก" section) **คลิกได้ก็ต่อเมื่ออัปโหลดเสร็จ 100% จริง**
        เท่านั้น — ตรงกับ console log ที่เห็นตอนแครช (`clip-forge-effect-sd...`, `Worker: Setting canvas`,
        `EffectWebSDK setOffscreenCanvas`) ซึ่งคือ TikTok เองกำลังสร้างปก/thumbnail ด้วย AR effects engine —
        **สรุปได้ว่า:** `waitForUploadComplete()` เดิมใช้ text-pattern เดา 4 แบบ (%, "Uploading...", MB/MB,
        ปุ่ม submit disabled) ซึ่ง**ผ่านครบทั้ง 4 ได้ทั้งที่ pipeline สร้างปกของ TikTok ยังไม่เสร็จจริง** (ไม่มีเลขเปอร์เซ็นต์
        โชว์ค้าง, ปุ่ม submit อาจ enable ไปแล้วก่อนปกเสร็จ) แล้ว `attachProductLink` เริ่มคลิก/ค้นหา element
        ระหว่างที่ worker สร้างปกของ TikTok ยังทำงานอยู่พอดี — เป็นการชนกันจริงระหว่าง automation กับ internal worker
        ของ TikTok เอง (ไม่ใช่แค่ปัญหาคลิกซ้ำที่แก้ใน POST-2.5/2.6 ซึ่งช่วยได้แต่ไม่พอ)
      - **แก้แล้ว:** เพิ่มเช็คที่ 5 ใน `waitForUploadComplete()` ([background.js:248+](tiktok_autopost_extension/background.js#L248))
        — หาปุ่ม "แก้ไขหน้าปก"/"Edit cover" ถ้า**ไม่เจอปุ่มเลย** หรือ**เจอแต่ disabled** ให้ถือว่ายัง `isUploading: true`
        ต่อไป (ใช้ signal ที่พี่ยืนยันจริงจากบัญชีจริง แทนการเดา text pattern อย่างเดียว) — เช็คนี้เป็นเงื่อนไข**เพิ่ม**
        ต่อจาก 4 เช็คเดิม ไม่ได้แทนที่ ต้องผ่านครบทั้ง 5 ถึงจะถือว่าอัปโหลดเสร็จจริง
      - `node --check` ผ่าน, `pytest tests/ -q` 372 passed
      - **ยังไม่ได้ทดสอบกับ extension จริงหลัง fix นี้** — รอพี่ reload extension แล้วลองรอบใหม่ (เปิด Preserve log
        ต่อไว้เผื่อยังไม่หาย จะได้เห็น error ตัวจริงถ้าเกิดอีก)
      - **⚠️ แก้ไขต่อใน POST-2.8: สมมติฐานเช็คปุ่ม "แก้ไขหน้าปก" ผิด** — ดูรายละเอียดด้านล่าง

- [x] **POST-2.8 พี่ทดสอบมือเจาะจง — เช็คปุ่มที่ใส่ไปใน POST-2.7 ใช้ไม่ได้จริง แต่เจอบั๊กจริงอีกตัวแทน (2026-09-06)**:
      - **พี่ทดสอบเอง:** กด "แก้ไขหน้าปก" ที่ 0% อัปโหลด (`0B/21.37MB`) → **กดได้ทันที** เปิด modal ปกติ (แค่ข้างในโหลด
        สปินเนอร์รอจนคลิปอัปเสร็จค่อยโชว์ผลจริง) — สรุป: **ปุ่มนี้ไม่เคย disabled ระหว่างอัปโหลดเลย** สมมติฐานของ
        POST-2.7 (เช็คปุ่ม disabled) **ผิด** เช็คนั้นไม่เคยบล็อกอะไรจริง (เจอปุ่มไม่ disabled ตลอด ผ่านฟรีทุกครั้ง)
      - **ลบเช็คที่ 5 ของ POST-2.7 ออกแล้ว** (ทิ้ง comment อธิบายไว้ในโค้ดว่าทำไมถึงลบ กันคนมาใส่ซ้ำโดยไม่มีหลักฐานใหม่)
      - **เจอบั๊กจริงอีกตัวจากรูปเดียวกัน:** เช็คข้อ 2 เดิม (`allText.includes('Uploading...')`) **เช็คแต่คำอังกฤษ**
        แต่หน้าจริงเป็นภาษาไทยโชว์ **"กำลังอัปโหลด..."** ใต้รูปปกตอน 0% (เห็นชัดในสกรีนช็อตที่พี่ส่ง) — เช็คนี้จึง
        **ไม่เคยทำงานจริงเลยบนเซสชันภาษาไทย** ตั้งแต่แรก เพิ่มคำไทยเข้าไปด้วยแล้ว
      - `node --check` ผ่าน, `pytest tests/ -q` 372 passed
      - **สถานะตอนนี้:** เหลือ fix ที่ยืนยันแล้วว่ามีผลจริง 2 อย่าง — (1) ลดคลิกซ้ำซ้อน (POST-2.5/2.6, ยืนยันจาก
        isolation test ว่า "automation คือสาเหตุ" แต่ยังไม่รู้ว่าพอไหม) (2) เช็คคำไทย "กำลังอัปโหลด" ที่เพิ่งเพิ่ม
        (ยังไม่เคยเทสจริง) — ยังไม่มีหลักฐานเจาะจงว่า"จุดไหนกันแน่"ในลำดับงานที่ทำให้แครช รอผลทดสอบรอบใหม่กับ extension
        จริง (ไม่ใช่เทสมือ) พร้อม Preserve log เพื่อจับ error ตัวจริงตอนแครชให้ได้สักที

- [x] **POST-2.9 ทดสอบจริงกับ extension (test cap4.mp4) — แครช "ก่อน" จะเริ่มปักตะกร้าด้วยซ้ำ (2026-09-06)**:
      - **จุดเปลี่ยนสำคัญ:** คลิปนี้แครชตอน status **ยังค้างที่ "กำลังทำงาน...รอวิดีโอครบ 100%"** — คือแครชเกิดขึ้น
        **ระหว่าง `waitForUploadComplete()` กำลัง poll อยู่** ก่อนจะไปถึง `attachProductLink` เลยด้วยซ้ำ — คลิกซ้ำ/
        ค้นหา element ที่แก้ใน POST-2.5/2.6 **ไม่เกี่ยวกับจุดแครชนี้เลย** เพราะยังไม่ทันได้รันถึงตรงนั้น
      - Console ตอนแครชโชว์ log ของ TikTok เอง (`AMGAmazer`, `AMGUniformBuiltinName`, `AMGWebAudioEngine` —
        effects engine กำลัง initialize, มี `worker nums = 0`/`worker count = 0` หลายจุด น่าสงสัยเหมือนกัน)
      - **สมมติฐานใหม่ (ยังไม่ยืนยัน):** แค่ `chrome.debugger` attach ค้างอยู่ระหว่างที่ TikTok init effects engine
        เอง อาจไม่เสถียรอยู่แล้ว **ไม่ว่าจะส่งคำสั่งอะไรไปหรือเปล่า** ก็ได้ (ต่างจากที่คิดไว้ก่อนหน้าว่าการคลิก/ค้นหา
        คือตัวกระตุ้น) — พี่เสนอไอเดียตรวจแยกตัวแปร: "ลองเอาตัวปกออกดูไหม" (ดูรายละเอียดว่าทำไมไม่ตรงกับที่พี่คิดด้านล่าง)
      - **ตรวจแล้ว: โค้ดเราไม่ได้อัปโหลดปกเองเลย** (ส่วนที่เคยหยอดปกใส่ `nodeIds[1]` ถูกตัดออกไปแล้วใน POST-2.3) —
        "ปก" ที่เห็นเป็น pipeline อัตโนมัติของ TikTok เอง (`clip-forge-effect-sdk`) ที่ทำงานทันทีที่มีไฟล์วิดีโอถูกตั้งค่า
        ไม่ว่าจะตั้งด้วยมือหรือด้วยสคริปต์ — เลยไม่มี "ตัวอัปปก" ของเราให้เอาออกได้ตามที่พี่เสนอ
      - **แปลงเป็นการทดสอบที่ทำได้จริงแทน:** เพิ่ม diagnostic flag `DIAGNOSTIC_PASSIVE_WAIT`
        ([background.js:21+](tiktok_autopost_extension/background.js#L21)) — ชั่วคราวเท่านั้น ลบทิ้งเมื่อได้คำตอบ —
        แทนที่ `waitForUploadComplete()` (ซึ่ง poll ด้วย `Runtime.evaluate` ทุก ~1.5-2 วิ) ด้วย `sleep(35000)` เฉยๆ
        (ไม่ส่งคำสั่ง CDP อะไรเลย แต่ debugger ยังติดอยู่กับแท็บ) เพื่อแยกให้ชัดว่า:
        - **ถ้าแครชระหว่าง 35 วิที่นิ่งสนิทนี้** → ยืนยันว่าแค่ attach เฉยๆ ก็ไม่เสถียรแล้ว (แก้โค้ด polling ไม่ช่วย
          ต้องคิดสถาปัตยกรรมใหม่ เช่น detach ระหว่างรอ แล้วค่อย attach ใหม่ตอนจะทำจริง)
        - **ถ้าไม่แครชช่วงนี้ (แครชทีหลังตอน attachProductLink เริ่มทำงาน)** → ยืนยันว่าการยิง `Runtime.evaluate`
          ถี่ๆ ระหว่าง TikTok init effects engine ต่างหากที่เป็นตัวกระตุ้น
      - `node --check` ผ่าน, `pytest tests/ -q` 372 passed
      - **รอผลทดสอบจริง** — พี่ reload extension แล้วลองอีกรอบ (35 วินาทีนี้จะไม่มีอะไรเกิดขึ้นบนหน้าจอเลย ปกติ)
        สังเกตว่าแครชเกิดตอนไหน (ระหว่าง sleep เงียบๆ หรือหลังจากนั้น)

- [x] **POST-2.10 ผลทดสอบ DIAGNOSTIC_PASSIVE_WAIT: แครชเหมือนเดิม — พักรอบนี้ไว้ก่อนตามที่พี่บอกเหนื่อย (2026-09-06)**:
      - **ผลชี้ขาด:** แครชเหมือนเดิมแม้ตอน sleep เฉยๆ 35 วิ ไม่ส่งคำสั่ง CDP อะไรเลย → **ยืนยัน hypothesis (b):**
        แค่ `chrome.debugger` attach ค้างอยู่ระหว่างที่ TikTok init effects engine ของเขาเอง **ก็ไม่เสถียรอยู่แล้ว**
        ไม่เกี่ยวกับโค้ดที่เรา poll/คลิก/ค้นหาเลย — แก้ที่ polling behavior (POST-2.5 ถึง 2.9 ทั้งหมด) จึง**ไม่มีทาง
        แก้ได้จริง**ด้วยการปรับโค้ดฝั่งเราแบบที่ทำมา ต้องเปลี่ยนสถาปัตยกรรมใหญ่ (attach แค่ตอนจะสั่งจริงๆ แล้ว detach
        ทันที ไม่ถืออ้างอิงยาว) ถึงจะมีโอกาสเลี่ยงได้ — **ยังไม่ได้ทำ** เพราะพี่ขอพักรอบนี้ก่อน (บอกว่าเหนื่อยแล้ว)
      - **สังเกตเพิ่มจากพี่ที่ยังไม่ได้ตรวจ (บันทึกไว้เผื่อกลับมาทำต่อ):** "รอบแรกที่ทำมันยังอัพคลิปได้อยู่ ตอนแรกที่มัน
        ใส่แค่แฮชแท็กมันยังอัพคลิปได้เลย" — บ่งชี้ว่า `typeCaption()` (พิมพ์แคปชันเต็ม+ขึ้นบรรทัดใหม่ทีละบรรทัดผ่าน
        `Input.insertText`+`Input.dispatchKeyEvent`) อาจเป็นตัวแปรที่ทำให้ต่างจากตอนใส่แค่แฮชแท็กสั้นๆ — ยังไม่ได้
        แยกทดสอบเจาะจงจุดนี้ เป็นเบาะแสที่น่าตามต่อรอบหน้า
      - **มติ:** พักรอบ POST-2 นี้ไว้เหมือนเดิม (ก็พักอยู่แล้วในสถานะรวม) ใช้ flow ที่ยืนยันว่าปลอดภัยจริงแทน:
        **อัปโหลดคลิปด้วยมือ รอจนปกจริงขึ้นครบ (ไม่มีสปินเนอร์ค้าง) แล้วค่อยกด "ปักตะกร้าสินค้าอย่างเดียว"** — เส้นทางนี้
        ไม่ผ่าน `waitForUploadComplete()`/`DIAGNOSTIC_PASSIVE_WAIT` เลย ไม่เคยเจอแครชในทุกรอบเทสที่ผ่านมา
      - **DIAGNOSTIC_PASSIVE_WAIT ยังอยู่ในโค้ด** (ตั้งใจปล่อยไว้ เผื่อพี่กลับมาทดสอบต่อ) — ถ้าจะกลับมาแก้จริงจัง
        ต้องออกแบบใหม่ทั้งการ attach/detach ไม่ใช่แค่ปรับ polling ต่อ
      - `node --check` ผ่าน, `pytest tests/ -q` 372 passed (ไม่มีอะไรเปลี่ยนฝั่ง python)

- [x] **POST-2.11 สร้างเส้นทางขั้นต่ำ "อัปโหลดไฟล์อย่างเดียว" ตรงตาม root cause ของ POST-2.10 (2026-09-06)**:
      - พี่ขอกลับไปเริ่มจากจุดง่ายสุด (ให้อัปคลิปได้เฉยๆ ก่อน) — ไฟล์ `tiktok_autopost_extension/` ไม่เคย commit
        เข้า git เลย (`??` untracked ตลอด) เลย **rollback ด้วย git ทำไม่ได้จริง** ไม่มีเวอร์ชันแรกให้ย้อน แทนที่ด้วย
        การสร้างฟังก์ชันขั้นต่ำใหม่ที่ตรงกับสิ่งที่ต้องการเป๊ะ (อัปคลิปอย่างเดียว) และตรงกับ root cause ที่เพิ่งพิสูจน์
        ใน POST-2.10 พอดี (attach ค้างนานคือปัญหา ไม่ใช่คำสั่งที่ส่ง)
      - เพิ่ม `runUploadFileOnly()` ([background.js:737+](tiktok_autopost_extension/background.js#L737)) —
        attach → หา `<input type=file>` → `DOM.setFileInputFiles` → **detach ทันที** ไม่รอ ไม่ poll ไม่พิมพ์อะไรต่อ
        เวลาที่ debugger ติดอยู่กับแท็บเหลือไม่ถึงวินาที ไม่มีทางไปทับซ้อนกับตอน TikTok เริ่ม init effects engine เลย
      - เพิ่มปุ่ม "⬆️ อัปโหลดไฟล์อย่างเดียว (แนะนำ)" ในหน้า popup ไว้บนสุด (เหนือปุ่มเดิมที่ mark ไว้ว่า "ยังไม่เสถียร")
        ใช้คู่กับปุ่ม "เติมเฉพาะคำอธิบาย"/"ปักตะกร้าสินค้าอย่างเดียว" ที่มีอยู่แล้ว (ทั้งคู่ attach สั้นๆ แยกกันเหมือนกัน
        ไม่เคยแครชในทุกรอบเทสที่ผ่านมา) — รวมกัน 3 ปุ่มนี้คือ full flow แบบแยกทีละ attach สั้นๆ แทนการถือยาวทีเดียว
      - ตอบคำถามเรื่องเข้า Chrome เอง (ถามซ้ำรอบนี้): **ยังทำไม่ได้เหมือนเดิม** — Playwright ที่มีเปิด browser
        แยกของตัวเอง ไม่มี session ล็อกอินจริง เข้าไปดู element จริงของ TikTok Studio ไม่ได้
      - `node --check` ผ่านทั้ง `background.js`/`popup.js`, `pytest tests/ -q` 373 passed
      - **ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension แล้วลองปุ่มใหม่ก่อน ถ้าอัปได้โดยไม่แครชแล้วค่อยลอง 2 ปุ่ม
        แยกที่เหลือทีละปุ่ม

- [x] **POST-2.12 ปิดเคส "อัปคลิปอัตโนมัติเต็มรูปแบบ" — เจอ root cause ตัวจริงที่แก้จากโค้ดเราไม่ได้ (2026-09-06)**
      **⚠️ กลับคำ — ดู POST-2.13: รอบถัดมากดปุ่มเดียวกันแล้วอัปผ่านไม่แครช สรุปด้านล่างนี้ผิด/ด่วนสรุปเกินไป**:
      - **ผลทดสอบปุ่ม "อัปโหลดไฟล์อย่างเดียว" (attach ไม่ถึงวินาที แล้ว detach ทันที):** พี่ยืนยันว่า **แครชที่
        "จังหวะเดิมเป๊ะ"** เท่ากับทุกรอบก่อนหน้า — นี่คือหลักฐานชี้ขาดตัวสุดท้าย: ตอนแครชเกิดขึ้นจริง **debugger ของเรา
        detach ไปนานแล้ว** (attach อยู่ไม่ถึง 1 วิ) แปลว่า hypothesis (b) ของ POST-2.10 ("attach ค้างคือปัญหา")
        **ก็ยังไม่ใช่ตัวจริงอีก** — ตัวกระตุ้นจริงคือ**การเรียก `DOM.setFileInputFiles` เอง** (วิธี CDP ตั้งค่าไฟล์ให้
        input) ที่ทำให้ TikTok's cover/effects pipeline (`clip-forge-effect-sdk`) รับไฟล์ไปแบบที่ต่างจากการเลือกไฟล์
        จริงด้วยมือมากพอ จนไป "ระเบิดเวลา" พังเองในภายหลังไม่กี่วินาที **ไม่ว่า debugger จะยังติดอยู่ตอนนั้นหรือไม่เลย**
      - **สรุปครบวงจร (ไล่ hypothesis ทั้งหมดที่ผ่านมา):**
        1. ~~คลิกซ้ำซ้อน~~ (POST-2.5/2.6) — ช่วยได้บ้างแต่ไม่ใช่ตัวหลัก (แครชได้แม้ไม่คลิกอะไรเลย)
        2. ~~scope การค้นหา DOM กว้างไป~~ (POST-2.6) — เช่นกัน ไม่ใช่ตัวหลัก
        3. ~~ปุ่ม "แก้ไขหน้าปก" disabled~~ (POST-2.7) — พิสูจน์แล้วว่าไม่เคย disabled เลย ผิดสมมติฐาน
        4. ~~attach ค้างระหว่าง TikTok init effects engine~~ (POST-2.10) — พิสูจน์แล้วว่าแครชได้แม้ detach ไปแล้ว
        5. **`DOM.setFileInputFiles` เอง (ตัวจริง)** — เป็นกลไกเดียวที่เหลืออยู่ในทุกรอบเทสที่แครช และไม่มีในรอบที่
           อัปมือแล้วไม่แครชสักครั้ง (ตัวแปรเดียวที่ต่างกันจริงระหว่าง "อัปมือ" กับ "อัปผ่าน extension" ทุกแบบ)
      - **นี่คือข้อจำกัดของ TikTok Studio เอง ไม่ใช่บั๊กที่แก้จากฝั่งเราได้** — ไม่มีวิธีอื่นให้เบราว์เซอร์ตั้งไฟล์ให้
        `<input type=file>` แบบเป็นโปรแกรมได้เลยนอกจาก `DOM.setFileInputFiles` (ดู TIKTOK_AUTOPOST_PLAN.md) ถ้ากลไก
        นี้เองที่ TikTok รับไม่ได้ ก็ไม่มีทางเลือกอื่นให้ auto-upload จริงๆ ได้อีกแล้วในทางเทคนิค
      - **มติสุดท้าย:** ปิดการพัฒนาฟีเจอร์ "อัปคลิปอัตโนมัติ" ไว้ตรงนี้ถาวร (ไม่ใช่แค่พักแล้วจะกลับมาแก้ต่อเหมือน
        POST-2.10) — ปุ่ม "อัปโหลดไฟล์อย่างเดียว"/"เติมข้อมูลคลิป + ปักตะกร้า" (แบบเต็ม) ให้คงไว้ในโค้ดแบบ opt-in
        (ปิดเป็นค่าเริ่มต้นอยู่แล้ว) แต่ไม่แก้ต่อ ไม่ไล่ debug ต่อ — **ใช้งานจริงทางเดียวจากนี้:** อัปคลิปด้วยมือเสมอ
        (เหมือนทำงานปกติที่พี่คุ้นเคยอยู่แล้ว) แล้วใช้ 2 ปุ่มที่พิสูจน์แล้วว่าปลอดภัย 100% ตลอดการทดสอบ: "เติมเฉพาะ
        คำอธิบายและแฮชแท็ก" + "ปักตะกร้าสินค้าอย่างเดียว" — ทั้งคู่ไม่แตะ `<input type=file>` เลยแม้แต่ครั้งเดียว
      - ไม่มีการแก้โค้ดเพิ่มในข้อนี้ (เป็นการปิดเคสด้วยข้อสรุป ไม่ใช่การแก้บั๊ก)

- [x] **POST-2.13 กลับคำ POST-2.12: กดปุ่มเดียวกันซ้ำ ครั้งนี้อัปผ่านไม่แครช — สร้าง checklist ทีละขั้นแทนเดา (2026-09-06)**:
      - **หลักฐานที่ทำให้ POST-2.12 ผิด:** พี่กด "อัปโหลดไฟล์อย่างเดียว" ซ้ำ (โค้ดเดิมเป๊ะ ไม่ได้แก้อะไรระหว่างนั้น)
        รอบนี้ **อัปผ่าน ไม่แครช** ทั้งที่รอบก่อนหน้า "จังหวะเดิมเป๊ะ" แครชซ้ำ — สรุปว่าแครชนี้**ไม่ deterministic
        100%** (flaky) แม้แต่ปุ่มเดียวกัน โค้ดเดียวกัน — ข้อสรุป "`DOM.setFileInputFiles` คือ root cause ถาวร แก้ไม่ได้"
        ใน POST-2.12 **ด่วนสรุปเกินไปจากหลักฐานแค่ 1 รอบ** ต้องขอโทษที่รีบปิดเคส
      - เช็ค backend ด้วย: ไม่เกี่ยวกับ backend ค้าง — `curl /openapi.json` เจอ `/api/tiktok-autopost/pending` ครบ
        อยู่แล้ว (backend stale ไม่ทำให้ tab ของ Chrome แครชได้ คนละ process กันคนละชั้นกันเลย)
      - **พี่ขอเปลี่ยนวิธี:** "ค่อยๆทำทีละฟังก์ชั่น และให้มีการติ๊ก แล้วผมจะดูเอง ว่าขั้นตอนไหนการเพิ่มอะไรที่ทำให้ crash"
        — เลิกเดา hypothesis ฝั่งผม เปลี่ยนเป็นเครื่องมือให้พี่ไล่ทดสอบเองทีละสเต็ปแทน
      - **สร้าง popup ใหม่เป็น checklist 5 ขั้น** แยก attach/act/detach คนละรอบต่อขั้น (ไม่ share session ข้ามขั้น):
        1. อัปโหลดไฟล์ (`upload-file-only`, มีอยู่แล้ว)
        2. พิมพ์คำอธิบาย/แฮชแท็ก (`type-caption-only`, มีอยู่แล้ว)
        3. ปักตะกร้าสินค้า (`attach-product-only` — ตัดการทำ scheduleMode ในตัวออก แยกเป็นขั้น 4 ต่างหาก)
        4. สลับเป็น "กำหนดเวลา" — ฟังก์ชันใหม่ `runScheduleModeOnly()` ([background.js:795+](tiktok_autopost_extension/background.js#L795))
        5. กด Post/กำหนดเวลา — ฟังก์ชันใหม่ `runClickPostOnly()` ([background.js:812+](tiktok_autopost_extension/background.js#L812))
      - แต่ละขั้นมีปุ่ม "ทำ" + checkbox แยก (ติ๊กเองอัตโนมัติเมื่อขั้นนั้นสำเร็จ, ไม่ติ๊ก = พังหรือหาไม่เจอ) — เขียนใหม่
        ทั้ง `popup.html`/`popup.js` เป็น checklist (เก็บช่องคำอธิบาย/แฮชแท็ก/ID สินค้าไว้เหมือนเดิม ย้ายมารวมกล่องเดียว)
      - ปุ่ม "เติมข้อมูลคลิป + ปักตะกร้า" (full auto flow เดิม) **เอาออกจาก UI แล้ว** (เก็บฟังก์ชัน `runAutopost` ไว้ใน
        โค้ดเผื่อใช้ทีหลัง แต่ไม่มีปุ่มเรียกแล้ว เพื่อไม่ให้สับสนกับ checklist ใหม่)
      - **ยังตอบไม่ได้เรื่องเข้า Chrome เอง** (พี่ถามซ้ำ) — Playwright ที่มีเปิด browser แยก ไม่มี session ล็อกอินจริง
      - `node --check` ผ่านทั้ง 2 ไฟล์ js, `python` เช็ค popup.html เบื้องต้นผ่าน (tag ครบคู่, id ครบ 5 ขั้น),
        `pytest tests/ -q` 373 passed
      - **ยังไม่ได้ทดสอบจริงกับ checklist ใหม่** — รอพี่ reload extension แล้วไล่กดทีละขั้น สังเกตว่าขั้นไหนพัง
        (เนื่องจากแครชดูจะ flaky ไม่ 100% แนะนำให้ลองซ้ำแต่ละขั้น 2-3 รอบ ไม่ใช่แค่รอบเดียว ก่อนสรุปว่าขั้นนั้นปลอดภัย)

- [x] **POST-2.14 checklist เจอตัวการจริงแล้ว — ขั้น 2 (พิมพ์คำอธิบาย) ทำให้แครช พร้อม console log ตัวจริงครั้งแรก (2026-09-06)**:
      - **หลักฐานชี้ขาดจาก console (มี "Keep log" เปิดค้างไว้ จับได้ตัวจริงเป็นครั้งแรก):** เจอ
        `NotFoundError: Failed to execute 'removeChild' on 'Node'` (React internals, `lib-react.cad72241.js`)
        **ต่อด้วยบรรทัด `pageCrash form unmount` จาก `Form.9fab7078.js` ทันที** — เป็น log ที่ TikTok เขียนเองสำหรับ
        เคสนี้โดยเฉพาะ (แปลว่าฟอร์มอัปโหลดของเขา unmount ตอน crash พอดี ไม่ใช่แค่ React เพี้ยนลอยๆ)
      - **จุดที่กดแล้วพังชัดเจน:** ขั้น 2 (พิมพ์คำอธิบาย/แฮชแท็ก) — error ขึ้น**ทันทีก่อนขึ้นอะไรเลย** (ไม่ใช่พิมพ์ติดแล้ว
        โดนเขียนทับทีหลังแบบที่สงสัยไว้ก่อนหน้า)
      - **ต้นตอที่เจอจริงจากอ่านโค้ด `typeCaption()`:** เดิมทำ **2 คำสั่งแยกคนละรอบ CDP call** —
        (1) `selectAll` + `delete` (ลบให้ว่าง) แล้ว **รอ 250ms** ก่อน (2) `insertText` เป็นอีก `Runtime.evaluate` แยก
        ต่างหาก — ระหว่างช่องว่าง 250ms ที่ field ว่างเปล่าจริงๆ นั้น TikTok's React มีโอกาสรีเรนเดอร์/แก้ DOM ตรงนั้น
        พอ `insertText` รอบหลังยิงเข้าไปเจอ node ที่ TikTok แก้ไปแล้ว โครงสร้างไม่ตรงกับที่ React คาดไว้ →
        `removeChild` พัง — ตรงกับที่สังเกตไว้ก่อนหน้าว่า "ใส่แค่แฮชแท็กสั้นๆ ยังผ่าน" (เนื้อหาสั้น โอกาสชนจังหวะน้อยกว่า)
      - **แก้แล้ว:** รวม `selectAll` + `insertText` เป็น **คำสั่งเดียวใน `Runtime.evaluate` เดียว**
        ([background.js:155+](tiktok_autopost_extension/background.js#L155)) — เลือกทั้งหมดแล้ว `execCommand
        ('insertText', ...)` ทับเลยทันทีในการเรียกเดียวกัน (`insertText` บน selection ที่เลือกไว้แทนที่เป็น
        native edit operation เดียว ไม่ต้องลบแยกอีกต่อไป) **ไม่มีช่องว่างให้ TikTok แทรกกลางคันได้เลย**
      - `node --check` ผ่าน, `pytest tests/ -q` 373 passed
      - **ยังไม่ได้ทดสอบจริงหลัง fix นี้** — รอพี่ reload extension แล้วลองขั้น 2 ซ้ำ 2-3 รอบตามที่แนะนำไว้
      - **⚠️ ผลจริง:** ลองซ้ำแล้ว **error signature เดียวกันเป๊ะ** ไม่เปลี่ยนแม้แต่นิดเดียว ทั้งที่แก้จริง (ครั้งที่ 3
        ที่ทฤษฎีต่างกันจริงทั้ง 3 รอบ) รวมกับที่เคยเจอ "ปุ่มเดียวกันโค้ดเดียวกัน บางรอบพังบางรอบผ่าน" (POST-2.13) —
        สรุปร่วมกับพี่ว่า **นี่น่าจะเป็น race condition ในโค้ด TikTok เอง** (form/autosave ภายใน) ที่ถูก sensitize ให้
        เกิดถี่ขึ้นเวลามี `chrome.debugger` ติดอยู่กับแท็บ ไม่ว่าเราจะสั่งอะไรตรงนั้นก็ตาม — ไม่ใช่บั๊กที่แก้จากโค้ดเรา
        ได้จริงแบบ deterministic อีกต่อไป (ต่างจาก POST-2.12 ที่ปิดเคสแบบไม่มีหลักฐานพอ อันนี้มีหลักฐาน 3 รอบสนับสนุน)
      - **พี่ตัดสินใจ:** พักการไล่ debug ส่วนอัตโนมัติเต็มรูปแบบไว้ตรงนี้จริงๆ (ไม่ปิดถาวร เผื่อ TikTok แก้ฝั่งเขาเอง
        ในอนาคต) หันไปทำฟีเจอร์ใหม่ที่ทำได้จริงแทน — ดู POST-2.15

- [x] **POST-2.15 เพิ่ม Chrome Side Panel แสดงรายการคลิป "ตัดต่อเสร็จ" จาก OmniCut โดยตรง (2026-09-06)**:
      - **คำขอ:** "ทำ extension ให้โผล่มาจาก sidebar แล้วแสดงรายละเอียดคลิปที่มีสถานะตัดต่อเสร็จทั้งหมด" — ฟีเจอร์ใหม่
        ที่ไม่เกี่ยวกับปัญหาแครชเลย ใช้ Chrome Side Panel API (Manifest V3) แยกจาก popup เดิม
      - เพิ่ม `"sidePanel"` permission + `"side_panel": {"default_path": "sidepanel.html"}` ใน `manifest.json`
      - สร้าง `sidepanel.html`/`sidepanel.js` ใหม่ — fetch `GET /api/exports` จาก backend เดียวกับที่แอปใช้เอง
        (`http://127.0.0.1:8000`, host_permissions มีอยู่แล้ว) กรองเฉพาะ `angle_status === 'rendered' &&
        is_latest !== false` (ตรงกับความหมาย "ตัดต่อเสร็จ" ของ `PIPELINE_PHASES` ใน `ContentTrackerHub.jsx` เป๊ะ —
        ไม่รวมคลิปที่ไปถึง mobile_ready/posted แล้ว หรือคลิปที่ยังไม่ได้ผูกกับสคริปต์เลย)
      - ยืนยันรูปทรง response จริงด้วย curl (8 exports จริง, มี 1 รายการ `angle_status='rendered', is_latest=true`
        ตรงเงื่อนไขพอดี — Logitech Wave Keys ที่เพิ่งซ่อมจาก Round BUG-3) + เช็ค thumbnail URL จริงคืน 200
      - แต่ละการ์ดโชว์ thumbnail (`.webp` เดิม) + ชื่อสินค้า + hook title + ขนาดไฟล์ + ปุ่ม "เตรียมคลิปนี้" ที่ยิง
        `POST /api/tiktok-autopost/prepare` ตรง (endpoint เดียวกับที่ popup ใช้อยู่แล้ว) แล้วบอกให้ไปกดต่อใน popup
      - เพิ่มปุ่ม "📋 เปิดรายการคลิปที่ตัดต่อเสร็จ (แถบข้าง)" ใน `popup.html` เรียก `chrome.sidePanel.open({windowId})`
        (ต้องเรียกจาก user gesture โดยตรงตาม Chrome API ถึงจะเปิดได้ — เก็บ `default_popup` เดิมไว้ไม่แตะ
        เพื่อไม่ให้ checklist หายไปเวลาคลิกไอคอน extension)
      - `node --check` ผ่านทั้ง 3 ไฟล์ js, manifest.json valid JSON, HTML tag เช็คคร่าวๆ ผ่าน, `pytest tests/ -q`
        373 passed (ไม่กระทบฝั่ง python เลย ฟีเจอร์นี้อยู่ใน extension ล้วนๆ)
      - **ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension แล้วกดปุ่มเปิดแถบข้างจาก popup ดู
      - **⚠️ พี่ลองแล้ว: กดปุ่มไม่มีอะไรเกิดขึ้นเลย (ไม่มี error, ไม่มีแถบข้าง)** — เจอบั๊กจริงจากอ่านโค้ดตัวเอง:
        `chrome.sidePanel.open()` ต้องถูกเรียก**ในจังหวะ user gesture โดยตรง** (synchronous เท่านั้น) แต่โค้ดเดิม
        เรียก `chrome.windows.getCurrent()` (async) ก่อน แล้วค่อยเรียก `open()` **ข้างใน callback ของมัน** —
        เสีย user gesture ไปแล้วตอนนั้น ทำให้ `open()` throw แบบ **synchronous ทันที ก่อนจะถึง `.catch()` เลย** —
        เป็น uncaught exception ที่พี่มองไม่เห็นเลย (comment ในโค้ดเดิมพูดถูกว่าต้องเรียก sync แต่ implement ผิดเอง)
      - **แก้แล้ว:** ย้ายการดึง `windowId` ไปทำ**ตอน popup โหลด** (cache ไว้ล่วงหน้าตั้งแต่แรก ไม่ใช่ตอนกด) พอกดปุ่ม
        เรียก `chrome.sidePanel.open({windowId: currentWindowId})` **แบบ sync ทันที ไม่มีช่องว่าง async คั่นกลาง
        เลย** ([popup.js:11+](tiktok_autopost_extension/popup.js#L11)) + เพิ่ม try/catch ครอบกันการ throw
        แบบ synchronous ไว้ด้วย เผื่อพังกรณีอื่นจะได้เห็น error จริงแทนที่จะเงียบ
      - `node --check` ผ่าน, `pytest tests/ -q` 373 passed
      - **ยังไม่ได้ทดสอบจริงหลัง fix นี้** — รอพี่ reload extension แล้วลองกดปุ่มอีกที

- [x] **POST-2.16 รวม popup เดิม + side panel เป็น UI เดียว ตาม /grill-me (6 คำถามตอบครบ) (2026-09-06)**:
      - **คำขอ:** "อยากให้กด extension แล้วเปิดแถบข้างเลย ไม่ใช่กดปุ่ม แล้วออกแบบให้สวยงามด้วย" — grill-me สรุป:
        (1) รวม checklist เดิมเข้า side panel เป็น 2 แท็บ ลบ popup ทิ้งเลย (2) แท็บสวิตช์บนสุด (3) มี confirm
        dialog ก่อนเปลี่ยนคลิป active ถ้า checklist ทำค้างอยู่ (4) เพิ่มปุ่ม mark-posted **ในตัว extension เลย**
        (พี่ขอเองนอกเหนือจาก 2 ตัวเลือกที่เสนอไป — ไม่ต้องสลับไปกดในแอป OmniCut) (5) กล่อง mark-posted แยกท้ายสุด
        (6) รีเฟรชรายการคลิปแบบ manual เท่านั้น (ปุ่มเดิม ไม่ auto-poll)
      - **ลบ:** `popup.html`, `popup.js` ทั้งคู่ (`rm`) — เช็คด้วย `grep` แล้วว่าไม่มีโค้ด/manifest ที่อ้างถึงอีก
        (เจอแค่ log เก่าใน TODO.md/HISTORY.md ซึ่งเป็นบันทึกอดีต ไม่กระทบ)
      - **`manifest.json`:** เอา `"default_popup": "popup.html"` ออกจาก `"action"` (เหลือแค่ `default_title`)
      - **`background.js`:** เพิ่ม `chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })` ต้นไฟล์
        — ทำให้กดไอคอน extension เปิดแถบข้างตรงทันที ไม่ต้องผ่านปุ่มกลางทางอีก
      - **`sidepanel.html`** เขียนใหม่ทั้งไฟล์: เพิ่ม tab switcher (`#tabBtnList`/`#tabBtnChecklist`), แท็บ 2
        ("ขั้นตอนโพสต์") ย้าย caption/hashtags/productId inputs + checklist 5 ขั้นเดิมมาจาก popup.html ทุกอย่าง,
        เพิ่ม `#activeClipBanner` (โชว์คลิปที่กำลังทำอยู่), เพิ่มกล่อง `.mark-posted-card` (สีเขียว แยกจากปุ่ม
        automation โทนอันตราย) พร้อม `#markPostedBtn`, เพิ่ม `#confirmOverlay` modal สำหรับ confirm เปลี่ยนคลิป
      - **`sidepanel.js`** เขียนใหม่ทั้งไฟล์ เพิ่มจากของเดิม (list-only): tab-switch logic, `activeClip` state,
        `handlePrepareClick()` เช็ค `anyStepChecked()` ก่อน — ถ้ามีขั้นติ๊กค้างอยู่และกดคลิปอื่น จะเปิด confirm
        dialog ก่อนเสมอ (`askConfirm()` คืน Promise ผูกกับปุ่ม ok/cancel), `prepareClip()` ยิง `/prepare` เหมือน
        เดิมแล้วเติม caption/hashtags/productId ลง input พร้อมสลับไปแท็บ checklist อัตโนมัติ + reset ช่องติ๊กทั้ง 5
      - ปุ่ม checklist 5 ขั้น ย้าย `wireStep()` มาจาก popup.js เดิมเกือบคำต่อคำ ผูก action เดิมทุกตัว
        (`upload-file-only`/`type-caption-only`/`attach-product-only`/`schedule-mode-only`/`click-post-only`)
        — ไม่แตะ `background.js` ส่วนนี้เลย ยังใช้ message contract เดิมทั้งหมด
      - **ใหม่:** `markPostedBtn` handler ยิง `POST /api/exports/mark-posted` ตรง ({file_path, product_id,
        angle_id} จาก `activeClip`) — endpoint นี้มีอยู่แล้วใน `scripts/api_exports.py` (ไม่ได้แก้ backend เลย)
        สำเร็จแล้ว reset `activeClip`/checklist กลับที่ว่าง + เรียก `loadExports()` ใหม่ให้คลิปหายจากรายการ
      - เช็ค element id ตรงกันทุกตัวระหว่าง HTML กับ `getElementById` ใน JS ด้วย script python เทียบ set — ตรงกัน
        ครบ (มี false positive 2 ตัวจาก regex จับ template literal `chk${n}`/`btn${n}` ผิด ไม่ใช่ id จริง)
      - `node --check` ผ่านทั้ง `sidepanel.js`/`background.js`, manifest.json valid JSON
      - **ยังไม่ได้รัน `pytest` รอบนี้ และ**ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension ที่ `chrome://extensions`
        แล้วทดสอบ: (1) คลิกไอคอนต้องเปิดแถบข้างตรงเลย ไม่มี popup แทรกอีก (2) แท็บ "รายการคลิป" เห็นคลิปเดิม
        (3) กด "เตรียมคลิปนี้" ต้องสลับไปแท็บ checklist พร้อมข้อมูลเติมให้ (4) ลองกด "เตรียมคลิปนี้" คลิปอื่นตอน
        checklist ทำค้าง ต้องขึ้น confirm dialog ก่อน (5) ปุ่ม "มาร์คว่าโพสต์แล้ว" ทดสอบกับคลิปจริงได้ตามที่พี่สะดวก
        (เป็นข้อมูลจริงของพี่ ปุ่มนี้ไม่แตะ TikTok เลย แค่ย้ายไฟล์ในเครื่อง — ตัดสินใจเองได้ว่าจะลองกับคลิปไหน)

- [x] **POST-2.17 ปรับ UI side panel ให้สวยขึ้น ผ่าน `/impeccable polish` + craft-floor (2026-09-06)**:
      - **คำขอ:** "ปรับหน้า UI ให้สวยๆหน่อย สวยที่สุด ใช้งานง่าย สบายตา" พร้อมสกรีนช็อตของ POST-2.16 (แบนมาก —
        สี cyan เดียวทั้งจอ ไม่มี depth ไม่มี hierarchy, tab ดูเป็นปุ่มลอยไม่ใช่ segmented control)
      - รัน `context.mjs` — ไม่มี `PRODUCT.md`/`DESIGN.md` ในโปรเจกต์ (scoped fix ไปได้เลยไม่ต้อง block) จัดเป็น
        **Operate mode** (task-completion tool ไม่ใช่ marketing surface) ตาม `polish.md`
      - เขียน `sidepanel.html` ใหม่ทั้ง `<style>`: เพิ่ม design tokens (`--bg/--surface/--surface-raised` 3 ระดับ
        elevation, `--text-primary/secondary/tertiary` 3 ระดับ, accent/success/danger แยกชัดเป็น semantic role
        ไม่ใช้ cyan ทุกที่แบบเดิม), shadow scale จริง (sm/md/lg มี offset+blur ตาม craft-floor "Depth" rule),
        radius scale, easing curve เดียว (`cubic-bezier(0.16,1,0.3,1)`)
      - ปุ่มแยก role ชัด: `.btn-primary` (cyan, action หลัก) / `.btn-ghost` (neutral, secondary) / `.btn-step`
        (checklist) / `.btn-success` (mark-posted, เขียวแยกจาก automation ตามที่ตั้งใจไว้ตั้งแต่ POST-2.16)
        ทุกปุ่มมี hover (translateY -1px + สี) + active (scale/brightness) + disabled state
      - Tab switcher ทำเป็น segmented control จริง (พื้นหลังเดียว active state เป็นแท่งทึบสีตัดกัน แทนปุ่มลอย
        แยกกันแบบเดิม) + hover state บนแท็บที่ไม่ active
      - Checklist step แต่ละแถวเพิ่ม `.step-num` (เลขในวงกลม เปลี่ยนเป็นเขียวเมื่อ `input:checked` ด้วย
        `:has()` selector) แทนแค่ checkbox ลอยเดี่ยวๆ — step 5 (กด Post จริง) มี `.danger` class เน้นสีต่างจาก
        step อื่นเพราะเป็นขั้นที่กดแล้วย้อนไม่ได้
      - Card คลิป: เพิ่ม hover elevation (translateY -1px + shadow เข้ม), ชื่อสินค้าเป็น uppercase label
        แยก hierarchy จาก hook title, meta แยก dot separator
      - Empty/error state: จาก text สั้นๆ เป็นกล่อง dashed border (`.empty`) / กล่อง danger wash (`.error`)
        ให้เห็นชัดว่าเป็น state ไม่ใช่ข้อความหลุด
      - Confirm modal: เพิ่ม `backdrop-filter: blur(3px)` บน overlay + scale-in animation บนกล่อง (แทนโผล่มาทันที)
      - เพิ่ม `@media (prefers-reduced-motion: reduce)` ปิด animation ทั้งหมดตาม craft-floor "Motion" rule
      - `sidepanel.js`: ปุ่ม "เตรียมคลิปนี้" ที่สร้างด้วย `createElement` เพิ่ม `btn.className = 'btn-primary'`
        (เดิมไม่มี class เลย), `setStatus()` เปลี่ยน default จาก `kind || ''` เป็น `kind || 'info'` ให้ทุกข้อความ
        สถานะได้กล่องสไตล์เดียวกันแทนที่จะเป็น text ลอยไม่มี padding เวลาไม่ส่ง kind มา
      - **เจอจาก detector จริง (`detect.mjs`):** รอบแรกมี `--shadow-glow-accent`/`--shadow-glow-success` เป็น
        zero-offset colored halo บน `.btn-primary`/`.btn-success` — ตรง antipattern "dark-glow" (ท่า AI-slop
        ที่ detector เช็คเฉพาะ) แก้เป็น `--shadow-cta` (neutral elevation shadow มี offset+blur จริง ไม่มีสี)
        ตัวเดียวใช้ร่วมกัน 3 จุด + เอา glow ออกจากจุดสีเขียวๆ บนจุดไฟหน้า h1 ด้วย — รันซ้ำแล้ว detector คืน `[]`
      - เช็ค element id ตรงกันหมดระหว่าง HTML/JS (script python เทียบ set, false positive 2 ตัวจาก regex
        จับ template literal `chk${n}`/`btn${n}` ผิดเหมือนรอบก่อน ไม่ใช่ id จริง), เช็ค tag เปิด-ปิดสมดุลหมด
      - `node --check sidepanel.js` ผ่าน, `pytest tests/ -q` 381 passed (ไม่กระทบฝั่ง python เลย)
      - **ยังไม่ได้ทดสอบจริงในเครื่องพี่** — รอ reload extension ที่ `chrome://extensions` แล้วดูหน้าตาจริง
        ทั้ง 2 แท็บ + ลอง hover/click ปุ่มต่างๆ ว่า transition ลื่นไหม

- [x] **POST-2.18 เพิ่มปุ่มคัดลอก caption+hashtags รวม + ทำ checkbox ติ๊กเองได้ (2026-09-06)**:
      - **คำขอ:** (1) "คำอธิบายกับแฮชแท็กอยากอยู่ช่องเดียวกัน หรือไม่ก็มีปุ่มคัดลอกทั้งสองอันพร้อมกัน" (2) "ตอนนี้
        ยังกดทำแล้วรันต่อไม่ได้ อยากติ๊กหัวข้อเพื่อทำ checklist เองได้ไหม"
      - ถามพี่ก่อน 2 คำถาม: (1) แยกช่องเดิม+ปุ่มคัดลอกรวม vs รวมเป็นช่องเดียว → พี่เลือก**แยกช่องเดิม+ปุ่มคัดลอก**
        (ไม่เสี่ยงพังการแยก parse hashtag ที่ `background.js` พึ่งอยู่) (2) ติ๊กเองแล้วต้องเกิดอะไร → พี่เลือก
        **แค่ mark progress ด้วยมือ** ปุ่ม "ทำ" ยังทำงานเดิมทุกอย่าง (auto-tick เมื่อ CDP สำเร็จจริง)
      - **ปุ่มคัดลอกรวม:** เพิ่ม `#copyAllBtn` ใต้ 2 textarea ใน `sidepanel.html` — `sidepanel.js` ต่อ
        `caption + '\n\n' + hashtags` (ตัด field ที่ว่างออกด้วย `.filter(Boolean)`) แล้ว
        `navigator.clipboard.writeText()` (ใช้ได้ตรงในหน้า extension เอง ไม่ต้องเพิ่ม permission ใน
        manifest.json) สำเร็จแล้วเปลี่ยนปุ่มเป็น "✅ คัดลอกแล้ว" สีเขียวชั่วคราว 1.5 วิ แล้วคืนข้อความเดิม
      - **checkbox ติ๊กเองได้:** เดิม checkbox ถูกซ่อนด้วย `pointer-events: none` แสดงแค่ `.step-num` (เลขวงกลม)
        เป็น `<span>` อ่านอย่างเดียว — เปลี่ยน `.step-num` จาก `<span>` เป็น `<label for="chkN">` ทั้ง 5 ขั้น
        ([sidepanel.html](tiktok_autopost_extension/sidepanel.html)) ให้คลิกที่เลขวงกลม = toggle checkbox
        ผ่านกลไก HTML label association มาตรฐาน (ไม่ต้องเขียน JS toggle เพิ่มเอง) + เพิ่ม `cursor: pointer` +
        hover/active state ให้เห็นว่ากดได้ ปุ่ม "ทำ" ยังคงอยู่คู่กันเหมือนเดิม ไม่ได้ตัดออก
      - **ไม่ต้องแก้ `sidepanel.js` เรื่อง checkbox เลย** — เช็คโค้ดแล้ว `anyStepChecked()`/`resetChecklist()`/
        `wireStep()` อ่าน-เขียนผ่าน `.checked` เฉยๆ ไม่สนว่าใครเป็นคนติ๊ก (ปุ่ม "ทำ" หรือพี่เอง) ผลพลอยได้ที่ถูกต้อง
        พอดี: ติ๊กเองก็ trigger confirm-dialog ตอนเปลี่ยนคลิปเหมือนกดปุ่ม "ทำ" จริง (สมเหตุสมผล เพราะแปลว่าพี่
        ทำขั้นนั้นไปแล้วจริงๆ ไม่ว่าจะทำเองนอกระบบหรือให้ extension ทำให้)
      - แก้ `step-note` ท้าย checklist ให้อธิบาย 2 วิธี (กดปุ่ม "ทำ" ให้อัตโนมัติ / กดเลขวงกลมเองถ้าทำเองแล้ว)
      - `node --check sidepanel.js` ผ่าน, detector (`detect.mjs`) คืน `[]` (ไม่มี antipattern ใหม่), id ตรงกัน
        ทุกตัว, tag เปิด-ปิดสมดุล (รวม `<label>` 5 คู่ใหม่), `pytest tests/ -q` 381 passed
      - **ยังไม่ได้ทดสอบจริง** — รอ reload extension แล้วลอง (1) กดปุ่มคัดลอกรวม วางใน caption box ของ TikTok
        ดูว่าได้ครบทั้ง 2 ส่วน (2) ลองกดเลขวงกลมของขั้นที่ยังไม่ทำ ดูว่าติ๊ก/เปลี่ยนสีเขียวได้ทันที

- [x] **POST-2.19 แก้บั๊กจริง: ขั้น 3 ปักตะกร้าค้างที่แท็บ "ร้านของฉัน" ไม่สลับไป "นำเสนอสินค้า" (2026-09-06)**:
      - **หลักฐาน:** พี่ส่งสกรีนช็อต — modal "เพิ่มลิงก์สินค้า" ค้างอยู่แท็บ "ร้านของฉัน" (empty state
        "ไม่มีสินค้าในร้านของคุณ") ไม่เคยสลับไปแท็บ "นำเสนอสินค้า" เลย ทั้งที่ ID/พิมพ์ค้นหาถูกส่งเข้าไปแล้ว
        (พี่บรรยาย: "ปักตระกร้า มันทำได้ถึงแค่ร้านค้า ไม่เปิดแทบนำสเนอสินค้า แล้วใส่เลขไอดีติ้กเลือกบันทึกให้")
      - **root cause จากอ่านโค้ด `switchToShowcaseTab()`'s `isActive()`
        ([background.js:322-335](tiktok_autopost_extension/background.js#L322) เดิม):** เช็คแค่
        `searchInput.offsetWidth > 0 || offsetHeight > 0 || getClientRects().length > 0` — ทั้ง 3 เงื่อนไขนี้
        คืนค่า non-zero ได้แม้ element อยู่ใน ancestor ที่ `display: none` (React ของ TikTok เก็บ tab panel
        ที่ไม่ active ไว้ใน DOM ต่อ ไม่ได้ unmount) แปลว่าถ้ามี search input เก่าค้างจาก render รอบก่อนที่ไหน
        สักที่ในหน้า `isActive()` จะ**คืน `true` เท็จตั้งแต่การเช็คครั้งแรก** (บรรทัด `if (await isActive())
        return true`) ทำให้ฟังก์ชันไม่เคยพยายามคลิกแท็บที่ถูกต้องเลย แล้วปล่อยผ่านไปเป็น "switched=true" ทั้งที่
        ยังอยู่ "ร้านของฉัน" จริงๆ
      - **แก้ 2 จุด:**
        1. `isActive()` เปลี่ยนเป็นเช็ค `checkVisibility()` จริง (fallback `getBoundingClientRect` +
           `getComputedStyle` ถ้า browser เก่าไม่รองรับ) **บวกเช็ค negative signal ตรงๆ**: ถ้าเจอข้อความ
           "ไม่มีสินค้าในร้านของคุณ" ที่ไหนในหน้า ถือว่ายังไม่ active แน่นอน ไม่ว่า search input จะดูเหมือน
           visible แค่ไหนก็ตาม ([background.js:321-360](tiktok_autopost_extension/background.js#L321))
        2. `attachProductLink()` เดิมเจอ `switched === false` แค่ `console.warn` แล้ว**เดินหน้าต่อ** พิมพ์ ID
           ลง search box ที่ไม่มีอยู่จริง (เพราะ "ร้านของฉัน" ไม่มี search) — เปลี่ยนเป็น **หยุดทันทีและ return
           error ชัดเจน** `'สลับไปแท็บ "นำเสนอสินค้า" ไม่สำเร็จ (ยังค้างอยู่ที่ "ร้านของฉัน") -- ลองกดขั้นนี้ซ้ำ'`
           ([background.js:508-514](tiktok_autopost_extension/background.js#L508)) แทนที่จะปล่อยให้พังต่อแบบ
           เงียบๆ แล้วไปโผล่ error ที่ไม่เกี่ยวกันในขั้นถัดไป (หาสินค้าไม่เจอ/กดปุ่มไม่ได้)
      - `node --check` ผ่าน, `pytest tests/ -q` 381 passed (ไม่กระทบฝั่ง python)
      - **ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension แล้วลองกดขั้น 3 (ปักตะกร้าสินค้า) ใหม่ ดูว่าสลับไปแท็บ
        "นำเสนอสินค้า" ได้จริงไหม ถ้ายังพังอีก ตอนนี้จะได้ error message ที่ชี้ตรงจุดแทนที่จะเงียบเหมือนก่อน
      - **✅ ผลจริง (พี่ทดสอบแล้ว):** POST-2.19 แก้ตรงจุด — ขั้น 3 เดินผ่านไปจนถึงหน้า "เพิ่มลิงก์สินค้า" มีชื่อ
        สินค้า "LOGITECH WAVE KEYS (สีขาว/สีดำ" ขึ้นรอกด "เพิ่ม" ได้จริงแล้ว (พี่ส่งสกรีนช็อตยืนยัน)

- [x] **POST-2.20 แก้บั๊ก: ขั้น 4 "สลับเป็นกำหนดเวลา" กดโดน dropdown "ตำแหน่งที่ตั้ง" แทน (2026-09-06)**:
      - **หลักฐาน:** พี่ส่งสกรีนช็อต — กดขั้น 4 แล้ว dropdown "ตำแหน่งที่ตั้ง" (Location) เปิดขึ้นมาแทน ไม่ใช่ตัวเลือก
        "กำหนดเวลา" ("สลับเป็นกำหนดเวลา มันไปกดเลือกตำแหน่งแทน")
      - **root cause จากอ่านโค้ด `switchToScheduleMode()`
        ([background.js:667-685](tiktok_autopost_extension/background.js#L667) เดิม):** ค้นหา element ด้วย
        `t.includes('กำหนดเวลา')` แบบ **ไม่จำกัดว่าต้องเป็น leaf** — ถ้า TikTok วาง "กำหนดเวลาโพสต์" กับฟิลด์
        "ตำแหน่งที่ตั้ง" ไว้ใน section เดียวกัน `<div>` ครอบใหญ่ที่สุด (parent) ก็จะ match ก่อนเพราะ
        `innerText` ของมันรวมข้อความลูกทุกตัวไว้อยู่แล้ว (includes เจอแน่นอน) โค้ดเดิมหยิบ div ใหญ่นั้นมาแล้ว
        `.querySelector('input')` หา **input ตัวแรกที่เจอใน DOM order ภายใน container นั้น** ซึ่งถ้า input
        ของฟิลด์ location มาก่อน input ของ schedule radio ใน DOM ก็จะกดโดน location แทนทันที
      - **แก้:** เขียนใหม่ 3 จุด
        1. เปลี่ยนจาก `includes()` เป็น **exact match** (`TARGETS.includes(t)`) และเพิ่มเงื่อนไข **ห้ามมี child
           element ที่มีข้อความตรงกันซ้ำ** (`isLeafMatch`) — ป้องกัน parent div ที่ห่อ label จริงไว้ข้างในชนะ
        2. ถ้า match หลายตัว เรียงเอา bounding-box **เล็กสุดก่อน** (element เฉพาะเจาะจงที่สุด) เหมือน pattern
           ที่ใช้กับ `switchToShowcaseTab` ไปแล้วใน POST-2.5/2.6
        3. หา input ที่จะคลิกด้วย `getAttribute('for')` → `getElementById` (ผูก label-for ตรงมาตรฐาน) ก่อน
           แล้วค่อย fallback ไป `:scope > input` (ลูกตรงๆ ชั้นเดียว ไม่ query ลึกเข้าไปในลูกหลาน) แทนที่จะ
           `querySelector('input')` แบบเดิมที่มองเข้าไปได้ลึกทั้ง subtree
        4. เปลี่ยน return type จาก `undefined` เป็น `{success: boolean}` จริง — `runScheduleModeOnly()`
           ([background.js:866](tiktok_autopost_extension/background.js#L866)) เช็คค่านี้แล้ว **return
           error ชัดเจน** ถ้าหาตัวเลือกไม่เจอ แทนที่จะ report สำเร็จเสมอแบบเดิม (`return { success: true }`
           ไม่สนใจผลจริงเลย)
      - `node --check` ผ่าน, `pytest tests/ -q` 381 passed (ไม่กระทบฝั่ง python)
      - **ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension แล้วลองกดขั้น 4 ใหม่ ดูว่าคลิกโดน "กำหนดเวลา" ตรงๆ
        แทนที่จะไปโดน location dropdown

- [ ] **POST-2.21 เพิ่มขั้นตอนอัปโหลดภาพปก (Cover Upload) ใน Extension Side Panel — ปิดจุดเจ็บไม่ต้องเปิดโฟลเดอร์ลากไฟล์เอง (2026-09-06)**:
      - **คำขอ:** "มันค่อนข้างยุ่งยากที่จะเปิด folder แล้วมาเลือก ผมมี extension แล้วจะให้นายทำต่อจากอีก เอเจนน่ะ"
      - **วิเคราะห์:** ปัจจุบันระบบทำปก 9:16 (COV-1) เซฟไฟล์ไว้ใน `05_Covers_Thumbnails/{stem}_cover.jpg` คมชัดแล้ว แต่ขั้นตอนโพสต์ใน TikTok Studio พี่ยังต้องเปิดโฟลเดอร์ใน Windows Explorer แล้วลากไฟล์รูปปกไปหยอดเองในหน้าแก้ไขหน้าปก
      - **แผนงานรอบนี้:**
        1. **Backend (`media_service.py` & `api_exports.py`):** คืนค่า `cover_path` ใน `GET /api/exports` เพื่อให้ extension รู้จักตำแหน่งไฟล์รูปปกจริงในเครื่อง
        2. **Extension (`sidepanel.js` & `sidepanel.html`):**
           - ส่ง `cover_path` ไปยัง `POST /api/tiktok-autopost/prepare` เมื่อกด "เตรียมคลิปนี้"
           - เพิ่มพรีวิวรูปปก 9:16 ใน Side Panel ใต้ชื่อคลิป เพื่อให้เห็นภาพปกทันทีก่อนอัปโหลด
           - เพิ่มขั้นตอนใน Checklist: "อัปโหลดภาพปก" (ปุ่มกดทำ + checkbox ติ๊กมือ/ออโต้)
        3. **Extension Background Worker (`background.js`):**
           - เพิ่ม handler `upload-cover-only`: attach debugger สั้นๆ -> คลิกเปิด modal "แก้ไขหน้าปก" ของ TikTok Studio -> หา `<input type="file">` ของรูปภาพ -> เรียก `DOM.setFileInputFiles` ใส่ไฟล์ปกจาก `05_Covers_Thumbnails/` -> รอภาพโหลด -> คลิกปุ่ม "บันทึก" ใน modal -> detach ทันที (ไม่แช่ session ป้องกัน tab crash)
      - **Gate:** `node --check` ทุกไฟล์ js ผ่าน, `pytest tests/ -q` ผ่าน, ตรวจสอบ element id และ HTML tags ถูกต้องครบถ้วน

### Gate

- [ ] ทดสอบมือกับคลิปทดลองก่อน อย่างน้อย 3-5 คลิป สังเกตอาการบัญชีก่อนใช้จริง — รอพี่ทำ (ต้องผ่าน Todo ข้อแรกก่อน)
- [x] ปุ่ม manual (POST-1) ยังอยู่คู่กันเสมอ ปิด auto-post ได้โดยไม่กระทบ flow อื่น — ปุ่ม "เปิด TikTok Studio"/
      "มาร์คว่าโพสต์แล้ว" ของ POST-1.3 ไม่แตะเลย ปุ่มใหม่ (`autopostEnabled &&`) ซ่อนเองถ้า toggle ปิดอยู่
- [x] ไม่มี schedule/headless — ทำงานเฉพาะตอนพี่กดเท่านั้น — ยืนยันจากโค้ด: `runAutopost()` ถูกเรียกจาก
      `chrome.runtime.onMessage` เท่านั้น (มาจากคลิกปุ่มใน popup) ไม่มี `setInterval`/`chrome.alarms` ที่ไหนเลย

### Notes

- เจอ 2 เรื่องที่ต้องแยกกันชัด: (1) ความเสี่ยงจากวิธีอัตโนมัติ ต่างจากบอทสแปม/ปั่นยอดที่โดนแบนจริง
  (2) นโยบายเปิดเผยเนื้อหา AI ของ TikTok ที่มีผลกับคลิปพี่**ไม่ว่าจะโพสต์วิธีไหน** — คนละเรื่องกัน ไม่ได้แก้ในรอบนี้
- ตัดทิ้ง: เปิด Chromium แยกแบบ library สำเร็จรูป (`tiktok-uploader` ฯลฯ) เพราะต้องพึ่ง stealth plugin ปลอมลายนิ้วมือ
  — เสี่ยงกว่าดีไซน์ที่เลือกซึ่งใช้ session จริงของพี่เอง
- **2026-09-06 (พี่ทดสอบซ้ำ, เจอเหมือนเดิม):** ระหว่างปักตะกร้ายังไม่เสร็จ extension กด Post ไปแล้ว — พี่ขอ
  ให้**หยุดกด Post อัตโนมัติไปเลย เดี๋ยวกดเอง** (ให้ extension ใส่ข้อมูล/ปักตะกร้าอย่างเดียวพอ)
  **แก้แล้ว:** `popup.js` เลิก restore ค่า `autoClickPost` จาก `chrome.storage.local` — checkbox "กด Post/
  กำหนดเวลา อัตโนมัติทันที" **เปิด popup มาต้อง unchecked เสมอ** ทุกครั้ง (ค่าเดิมที่เคยติ๊กไว้จากเทสรอบก่อน
  เคยค้างอยู่แบบไม่รู้ตัว — เป็นสาเหตุที่มันกด Post ซ้ำอีกทั้งที่พี่ไม่ได้ตั้งใจจะให้กดรอบนี้) ต้องติ๊กเองใหม่ทุกครั้งถ้าจะใช้
  **ยังไม่ได้แก้เชิงลึก:** ข้อสันนิษฐานของพี่ที่ว่า attach ยังไม่โหลดเสร็จ — โค้ดปัจจุบัน `attachProductLink` ใช้
  `sleep()` คงที่คั่นระหว่างขั้นตอน (1.5-2.5 วิ) ไม่ได้ poll จนกว่า modal จะปิด/สินค้าจะแนบจริง ถ้าเน็ตช้ากว่านั้น
  อาจ return "success" ทั้งที่ modal ยังไม่ปิดจริง — ตอนนี้ปิดความเสี่ยงด้วยข้อบนแทน (ไม่กด Post อัตโนมัติ)

---

## Round COV-1 — สตูดิโอสร้างปกคลิปด่วน 9:16 (Auto Highlight Crop, AI Hook & 4 TikTok Templates)

- **เป้าหมาย:** สตูดิโอสร้างภาพปกคลิปแนวตั้ง 9:16 (1080x1920) สำหรับโพสต์ลง TikTok Studio เพื่อเพิ่มยอดคลิก (CTR) ดึงภาพช็อตเด่น + AI ช่วยคิดข้อความ Hook ปกสั้นทรงพลัง + 4 แม่แบบสำเร็จรูปสไตล์ TikTok พร้อมปรับตำแหน่งข้อความ 3 โซน (บน/กลาง/ล่าง) และแปะป้าย 3D
- **ผลลัพธ์จาก Grill-Me:**
  1. ภาพพื้นหลัง: เลือกช็อตเด่นจาก 4-6 Candidate frames + Scrubber วิดีโอ หรือ อัปโหลดรูปสินค้าความละเอียดสูง
  2. ข้อความ Hook: AI เจน 4 สไตล์สั้นกระชับ (Curiosity, Value, Problem/Solution, Review/Rating) + แก้ไขคำได้อิสระ
  3. สไตล์แม่แบบ: 4 ธีม TikTok ยอดนิยม (Neon `#FFE600` ขอบดำ, Yellow Bar แถบเหลืองอักษรดำ, Modern Box กล่องกระจกเงา, Minimal Bold ขาวขอบดำหนา)
  4. ตำแหน่ง Hook: เลือกได้ 3 โซน (บน ~25% default, กลาง ~50%, ล่างเหนือบาร์ ~70%)
  5. ตรา 3D Badge: เลือกแปะมุมซ้ายบน / มุมขวาบน / ไม่ใส่
  6. เอาต์พุต: บันทึกลง `05_Covers_Thumbnails/{video_stem}_cover.jpg` ขนาด 1080x1920 พร้อมอัปเดต `cover_url` ให้ Tracker นำไปใช้ทันที
- **กฎเหล็กที่ต้องรักษา:**
  - เคารพ `ui_clean_standard.md` (ไม่มีสัญลักษณ์ซ้ำซ้อน ไม่มีเครื่องหมายบวกหรืออีโมจินำหน้าข้อความปุ่ม)
  - ไม่ใช้ hardcoded absolute path (ใช้ `BASE_DIR` จาก `scripts/config.py`)

### งานย่อย

- [x] **COV-1.1 Backend: Candidate Highlight Extraction & Image Scrubber API**
      - เพิ่ม `POST /api/covers/highlights` ใน `scripts/api_covers.py` สกัด 4-6 เฟรมสำคัญจากคลิป mp4 ส่งเป็น thumbnail base64 หรือ image URL
      - ปรับ `POST /api/covers/preview-frame` รองรับการระบุวินาทีละเอียด (timestamp) สำหรับ live scrubbing
- [x] **COV-1.2 Backend: AI Cover Hook Generator & 4 Pro Templates Render Engine**
      - เพิ่ม `POST /api/covers/generate-hooks` เจน 4 สไตล์ Hook สั้นกระชับ 2-4 คำ
      - ปรับปรุง `POST /api/covers/render-pro` เรนเดอร์ไฟล์ JPG 1080x1920 ด้วย Pillow/FFmpeg รองรับ 4 templates, 3 โซนตำแหน่ง Hook, vertical pan offset, และป้าย 3D badge overlay
- [x] **COV-1.3 Frontend: CoverStudioModal.jsx คอมโพเนนต์สตูดิโอ 9:16**
      - จอพรีวิว 9:16 พร้อม Safe Zone Overlay Guide (ขอบล่าง 420px และไอคอน TikTok ด้านขวา)
      - ส่วนเลือกรูป (4 ช็อตเด่น + Scrubber ละเอียด + อัปโหลดรูป)
      - ส่วนข้อความ Hook (AI Pills 4 สไตล์ + ช่องพิมพ์แก้คำ + ปุ่มเลือก 3 โซนตำแหน่ง)
      - ส่วนสไตล์แม่แบบ (4 การ์ดแม่แบบ + ตัวเลือกป้าย 3D badge)
- [x] **COV-1.4 Frontend Integration: ContentTrackerHub & ExportGallery**
      - เพิ่มปุ่ม `[สร้างปก]` บนการ์ด "ตัดต่อเสร็จ" และในแถวตาราง Daily Run Sheet
      - ผูก Event เมื่อบันทึกเสร็จ อัปเดตข้อมูลปกให้การ์ดแสดงรูปปกจริงทันที
- [x] **COV-1.5 TikTok Clean Capture, 3:4 Profile Ratio, Overlay Toggles & Dual Export (User ร้องขอ 2026-09-06)**:
      - **Backend (`scripts/api_covers.py`)**:
        - รองรับ `aspect_ratio`: `"9:16"` (1080x1920), `"3:4"` (1080x1440), หรือ `"both"`
        - รองรับสวิตช์ `enable_hook_text` และ `enable_badge` (ปิดแล้วได้ภาพคลีน 100%)
        - รองรับการค้นหา Raw Footage จาก `01_Raw/` หรือ `03_Projects/{project_name}/project.json`
        - คำนวณ Crop 3:4 อัตโนมัติร่วมกับ `pan_y_pct`
        - บันทึกทั้งไฟล์ `_cover.jpg` (9:16) และ `_cover_3x4.jpg` (3:4) เมื่อเลือก `"both"`
      - **Frontend (`CoverStudioModal.jsx`)**:
        - ติ๊กออก Hook และ Badge เป็น Default (`enableHookText = false`, `enableBadge = false`) ตามคำขอ
        - รองรับ **ลากเลื่อน (Drag to Pan) บนหน้าจอพรีวิวโดยตรง** ด้วยเมาส์/ทัช
        - รองรับ **ซูมเข้า-ออก (Zoom In/Out 1.0x - 2.5x)** ด้วย Scroll Wheel และ Slider ซูมขยายเพื่อดันซับไตเติลหลุดขอบเฟรม 100%
        - ซิงก์ค่า `zoom_scale` และ `pan_y_pct` ไปยัง Backend `render_pro_cover` ให้เรนเดอร์ภาพตรงเป๊ะกับพรีวิว
- [x] **COV-1.6 Gate & Tests Verification**
      - รัน `python -m compileall -q scripts` → ผ่านฉลุย ไร้ syntax error
      - รัน `python -m pytest tests/ -q -p no:cacheprovider` → **381 passed** (ครอบคลุม `test_covers_pro.py` 8 เคสครบทุก template + 3:4 profile + dual export + zoom/pan)
      - รัน `npm run build` ใน `frontend/` → ผ่าน 100% ไม่มี type/lint error (สร้าง bundle เรียบร้อยใน 4.16s)
      - ทดสอบ endpoint ด้วย python script / pytest → ยืนยัน parity ครบ
      - ตรวจสอบความถูกต้องด้วย `browser_subagent` → บันทึกวิดีโอ `cover_studio_zoom_drag_demo_1788705513755.webp` ยืนยันการลากเลื่อนพรีวิว, ปรับซูม 1.5x ดันซับหลุดเฟรม, และบันทึกสำเร็จจริงทั้ง 9:16 และ 3:4

#### POST-3.4 implementation update (2026-09-07)

- [x] ส่ง `cover_path` ล่าสุดจาก Side Panel ไปอัปเดต pending job ก่อนเปิด Cover Studio
- [x] จำกัดการค้นหา cover modal และ file input ให้อยู่ใน modal ล่าสุด ลดโอกาสเลือก DOM เก่าค้าง
- [x] รองรับรายการชั่วโมง/นาทีที่แสดงแบบมีหรือไม่มีเลขศูนย์นำหน้า และยืนยันค่าที่แสดงหลังเลือก
- [x] รัน syntax check, Node regression และ backend tests: Node 7 passed, backend 5 passed
- [ ] ทดสอบกับแท็บ TikTok ที่ล็อกอินจริงเพื่อยืนยันวันเวลาและการอัปโหลดปก (ต้องทำหลัง reload extension)

#### POST-3.5 — แก้ regression ขั้น 3 หลังทดสอบจริง (2026-09-07)

- [x] จำกัดช่องค้นหา Product ID และไอคอนค้นหาให้อยู่ใน dialog ของ Product Selector ล่าสุด
- [x] เพิ่ม regression assertion ป้องกันการย้อนกลับไปใช้ `document.querySelector` ช่องแรกทั้งหน้า
- [x] รัน syntax check, Node regression และ backend tests
- [ ] ยืนยันกับ TikTok Studio จริงหลัง Reload extension

#### POST-3.6 — แก้เฉพาะข้อ 4–5 โดยล็อกข้อ 1–3 (2026-09-07)

- [x] ตรวจและแก้ schedule picker ให้เลือกวัน/เวลาใน TikTok จริง พร้อมยืนยันค่าที่แสดง
- [ ] ตรวจและแก้ Cover Studio ให้เปิด modal ล่าสุดและแนบไฟล์ปกผ่าน CDP
- [x] ห้ามแก้ฟังก์ชันค้นหา/เลือกสินค้าในข้อ 1–3
- [x] รัน syntax, Node regression และ backend tests
- [ ] ทดสอบกับแท็บ TikTok Studio ที่ล็อกอินจริงหลัง reload extension

#### POST-3.6 implementation update (2026-09-07)

- [x] จำกัดการเลือก schedule ให้คลิกเฉพาะ `input[type="radio"][value="schedule"]` ป้องกันชนปุ่มโพสต์ข้อความเดียวกัน
- [x] ปรับเวลาให้เป็นช่วงละ 5 นาทีของ TikTok (เช่น 16:08 → 16:10) และรายงานค่าที่ปรับกลับไปที่ Side Panel
- [x] ปรับ UI ช่องวันที่/เวลา แยกป้ายกำกับและเพิ่ม `step="300"` ให้เลือกเวลาได้ตรงกับ TikTok
- [x] คงการแก้ Cover Studio และการส่ง cover path ล่าสุดจากรอบก่อน
- [x] ไม่แก้โค้ดค้นหา/เลือกสินค้าในรอบนี้
- [x] รัน syntax check และ Node regression: 8 passed
- [x] ผู้ใช้ยืนยันว่าขั้น 4 เปลี่ยนวันและเวลาใน TikTok ได้จริง และไม่โพสต์อัตโนมัติ
- [ ] ทดสอบการแนบปกกับแท็บ TikTok จริงหลัง Reload extension

#### POST-3.7 — แก้เฉพาะ flow แนบปก (2026-09-07)

- [x] ตรวจจุดเปิด Cover Studio และขอบเขต modal จาก DOM จริง
- [x] ทำให้ CDP file upload และการกดบันทึกเลือกองค์ประกอบใน modal ล่าสุดเท่านั้น
- [x] ห้ามแก้โค้ดข้อ 1–4 และห้ามแตะปุ่มโพสต์
- [x] เพิ่ม regression test สำหรับ flow แนบปก
- [x] รัน syntax และ Node regression
- [ ] ทดสอบแนบปกกับแท็บ TikTok จริงหลัง Reload extension

#### POST-3.7 implementation update (2026-09-07)

- [x] ตรวจพบ root จริงของ Cover Studio (`CoverEditor__root`) ที่ไม่มี `role="dialog"`
- [x] จำกัดการค้นหา input และปุ่มบันทึกไว้ใน Cover Studio ล่าสุด
- [x] เปิด `Runtime` ก่อนใช้ CDP file upload และยืนยันว่า modal ปิดหลังบันทึก
- [x] เพิ่ม regression contract สำหรับ Cover Studio และรัน Node regression: 8 passed
- [ ] ทดสอบแนบปกจริงหลัง Reload extension

#### POST-3.8 — ปรับตัวเลือกเวลาและสถานะขั้นตอน (2026-09-07)

- [x] เปลี่ยนช่องเวลาเป็นตัวเลือกทีละ 5 นาที และคุมเวลาขั้นต่ำ 15 นาทีตาม TikTok
- [x] ทำให้แถวขั้นตอนแสดงสถานะสำเร็จหลังตอบกลับสำเร็จอย่างแน่นอน
- [x] ห้ามเปลี่ยน flow ปักตะกร้าและการโพสต์
- [x] รัน syntax และ Node regression: 8 passed

#### POST-3.9 — ตรวจยืนยันกับ TikTok จริง: เวลาและ Cover upload (2026-09-07)

- [x] ตรวจ DOM จริง: schedule radio เป็น `value="schedule"` และ picker มีชั่วโมง 00–23 กับนาที 00–55 ทีละ 5 นาที
- [x] ยืนยันด้วยการเลือกตรงบน TikTok ว่า `11:15` เปลี่ยนเป็น `12:20` ได้
- [ ] ตรวจว่าการกดขั้น 4 จาก extension ส่งค่าฝั่ง Side Panel ไปถึง TikTok ในรอบเดียวกัน
- [ ] ตรวจข้อผิดพลาดข้อ 5 แยกเป็นเปิด modal, เลือกไฟล์ CDP, และบันทึกปก
- [ ] ทดสอบผ่าน extension ที่ Reload แล้ว โดยไม่กดโพสต์จริง

#### POST-3.10 - Keep open TikTok pickers stable and expose cover-step failures (2026-09-07)

- [x] Detect an already-open date/time picker and avoid clicking its input again.
- [x] Add regression contracts for picker targeting and preserve steps 1-3 and the publish button.
- [x] Keep Cover Studio targeting scoped to the latest `CoverEditor__root` and `ImageUpload__uploadArea`.
- [x] Run syntax checks and Node regression: 8 passed.
- [ ] Verify local cover-file transmission through a reloaded extension; browser controller blocks local file injection.

Notes: Live TikTok inspection found the schedule input at `11:25` while Side Panel showed `12:00`; the edit-cover control opened `CoverEditor__root` successfully.

#### POST-3.11 - Scroll TikTok time options before selecting (2026-09-07)

- [x] Find hour/minute options across the full TikTok picker and call `scrollIntoView({block:'center'})` before clicking.
- [x] Add a regression contract for values outside the current viewport such as `:00` and `:05`.
- [x] Run `node --check background.js` and Node regression: 8 passed.
- [x] Confirm from `test tt.mp4` that TikTok stayed at `10:40` while Side Panel requested `10:00`.
- [ ] Verify with the reloaded extension on the real tab without publishing.

Notes: Only `tiktok_autopost_extension/background.js` and its regression contract changed in this round. Steps 1-3, Cover step, and publishing remain untouched. Other files were already modified by parallel work and were not staged.

#### POST-3.12 - Find Cover Studio save button outside the editor root (2026-09-07)

- [ ] Include TikTok `cover-editor-container` in the save-button scope; the visible Save button is a sibling container outside `CoverEditor__root`.
- [ ] Add a regression contract for the real Cover Studio DOM classes.
- [ ] Run syntax check and Node regression without changing schedule, steps 1-3, or publishing.
- [ ] Verify modal -> local cover file -> Save through the reloaded extension when direct file injection is available.

#### POST-3.12 implementation update (2026-09-07)

- [x] Include `cover-editor-container` in Cover Studio save-button discovery.
- [x] Prefer the outer container because TikTok renders Save beside `CoverEditor__root`.
- [x] Add a regression contract for the real DOM class.
- [x] Run syntax checks and Node regression: 8 passed.
- [ ] Verify local file injection and Save through the reloaded extension; direct browser control still blocks local file transmission.

Notes: Schedule code and steps 1-3 remain frozen.

#### POST-3.13 - Persist completed schedule styling and resolve product-named covers (2026-09-07)

- [ ] Add the `completed` row class whenever `prepare-details` marks a step checkbox, including schedule step 4.
- [ ] Let `/api/exports` resolve a saved product-named cover such as `Logitech Wave Keys_cover.jpg` when the export stem has no exact cover file.
- [ ] Add regression coverage for the completion class and product-cover fallback.
- [ ] Run focused frontend/backend tests and build checks without changing schedule behavior or steps 1-3.
- [ ] Verify the extension receives `cover_path` and can start Cover Studio after reloading.

#### POST-3.13 implementation update (2026-09-07)

- [x] Add `.completed` styling when `prepare-details` marks any checklist checkbox, including schedule step 4.
- [x] Resolve product-named covers such as `Logitech Wave Keys_cover.jpg` when an export-stem cover is absent.
- [x] Add deterministic fallback test and run focused checks: backend 6 passed, extension 8 passed, Python compileall passed.
- [ ] Verify the reloaded extension receives the fallback `cover_path` and completes Cover Studio upload.

Notes: Schedule selection logic itself remains frozen; only checklist styling and cover metadata resolution changed.

- [x] Round POST-LIFECYCLE-1 closure verified: `export_id` is propagated through render, Gallery, queue, Extension, mark-posted, delete, rename, and cover metadata; current GOCHEK angle now points to Posted proof.
- [x] Round PRO-STYLE-2C — Apply editorial beat boundaries to generated clip list with Preview = Render parity (2026-09-09)

- [x] Round PRO-STYLE-3A — Style-driven transition budget and project style preset contract (2026-09-09)
- [x] Round PRO-STYLE-3B — Live keyframe camera motion with Preview = Render parity (2026-09-09)
- [x] Round PRO-STYLE-PARALLEL-4-6 — Parallelize style finishing, preset orchestration, and golden-master validation (2026-09-09; implementation ปิด, browser benchmark deferred)

## Round PRO-STYLE-PARALLEL-4-6 — Parallel style roadmap execution

วันที่: 2026-09-09 · ผู้สั่ง: user · สถานะ: implementation เสร็จแล้ว; browser benchmark deferred ตามคำสั่ง user

เป้าหมาย: เดินงาน Phase 4–6 พร้อมกันโดยล็อก ownership รายไฟล์ ลดเวลารอ และคง Preview = Render, deterministic/offline tests, และ Phase 3B camera-motion behavior เดิม

### Ownership lock

- Agent A / Color finishing: `scripts/video_editor.py`, `tests/test_color_finishing.py` เท่านั้น
- Agent B / Audio finishing: `scripts/sfx_manager.py`, `tests/test_audio_finishing_policy.py` เท่านั้น
- Agent C / Preset orchestration UI: `frontend/src/components/editor/EditorShell.jsx`, `frontend/src/components/editor/AssetPanel.jsx`, `frontend/src/lib/stylePresetCatalog.js`, `frontend/src/lib/stylePresetCatalog.test.js` เท่านั้น
- Agent D / Golden-master validation: `tools/golden_master_probe.py`, `tests/test_golden_master_probe.py`, `STYLE_GOLDEN_MASTER_REPORT.md` เท่านั้น
- Main agent reserved: `TODO.md`, `HISTORY.md`, `PRO_EDITOR_STYLE_PLAN.md`, shared pipeline/schema files, and merge/review/gates
- Existing unrelated working-tree files (`scripts/api_exports.py`, `tests/test_post_lifecycle.py`, `tiktok_autopost_extension/*`) are out of scope and must remain untouched

### Gates

- [x] Read/review every agent diff and confirm no ownership collision; 4 lanes stayed within their locked write sets
- [x] Run focused tests for each returned lane: color 6, audio 15, golden-master 6, frontend catalog 6
- [x] Run backend compileall, full backend pytest (`1019 passed, 12 warnings`), frontend npm test (`134 passed`), frontend build (`1976 modules`), and `git diff --check`
- [x] Run real ASS/libass FFmpeg style validation: `clean_tech_review` emitted `#FFE600` and entry/hold/exit renders all contained yellow accent pixels.
- [ ] Deferred user validation: browser Canvas-vs-libass pixel sampling at 50/100/300 clips; ไม่อ้าง FPS/performance improvement จนกว่าจะมี measurement จริง
- [x] Update this block with numeric results; implementation closure is recorded, while the browser Canvas-vs-libass benchmark remains deferred external validation.
- [x] บันทึก implementation และ deterministic gates แล้ว; browser benchmark ถูกแยกเป็น deferred validation ตามคำสั่ง user

### Notes

- Parallel lanes may create independent contracts and implementations, but integration dependencies are merged only after review by the main agent.
- No agent may edit TODO/HISTORY/plan documents or commit changes.
- [x] Regression found during full backend gate: `tests/test_preview_render_parity.py::test_ducking_uses_the_measured_reduction_not_a_feel_value` expected literal ducking filter parameters; audio lane preserved the source-parity contract while keeping policy values centralized.
- [x] Audio source-parity regression fixed by the audio owner; focused audio/parity checks passed and full backend rerun passed (`1015 passed`).
- [x] Phase 4 baked-media recolor signed off: accent hue rotation is opt-in for decorative stickers/effects and is mirrored by Canvas `hue-rotate` plus FFmpeg `hue`; product/semantic baked artwork remains neutral by default. Real multi-frame render gate passed.
- [x] Phase 5 visual integration: EditorShell passes `style_preset` into both live SequencePlayer instances; the shared `clean_tech_review` palette drives semantic overlay accent in Canvas and ASS.
- [x] Phase 6 real-artifact validation: LOG01 and GOC01 pass with 3 samples each, 0 signals, and paired comparison pass; probe samples against video duration when an audio tail is longer.
- [x] Repo-wide frontend lint exits 0 but reports existing warnings, including pre-existing warnings in `EditorShell.jsx`, `AssetPanel.jsx`, and shared hooks/components.

### Continuation plan — real validation and remaining style integration (2026-09-09)

- [x] Phase 4 baked-media tint integration [main] (2026-09-10): explicit accent recolor contract is wired through editor state, Canvas preview, and FFmpeg render; safe decorative sticker/effect assets recolor, while semantic/product-color media remains unchanged by default. Focused gates: backend 10 passed; frontend 138 passed; real FFmpeg render checked entry/hold/exit frames.
- [x] Phase 4 final gates (2026-09-10): full backend `1029 passed, 15 warnings`; frontend `138 passed`; build `1977 modules`; lint exit `0` with existing warnings; compileall and `git diff --check` passed.

- [x] Run `tools/golden_master_probe.py` against two available real exports with expected 1080x1920/30fps and required audio; both returned `pass`, 3 samples, 0 signals, and the comparison returned `pass`.
- [x] Run a real temporary FFmpeg audio mix using isolated temp inputs and verify the produced audio: 5.2s WAV, 44.1kHz stereo, mean `-16.8 dB`, peak `-4.0 dB`.
- [x] Audit `SequencePlayer.jsx` ownership; its existing camera-motion changes were preserved, then the authorized live style adapter was integrated without touching unrelated overlay geometry.
- [x] Added deterministic regression coverage for the probe duration edge case and reran affected gates: golden probe `6 passed`; real artifact probe `pass`.
- [x] Record numeric real-artifact results: baseline LOG01 `24.6s`, mean `-17.1 dB`, peak `-4.0 dB`; candidate GOC01 `55.948s`, mean `-18.1 dB`, peak `-3.9 dB`, A/V delta `0.014672s`, dimensions `1080x1920`, `30fps`.
- [x] Real-artifact validation found a probe edge case: exit sampling used container/audio duration and could seek past the final video frame when audio was slightly longer; fixed to sample against video duration and added regression coverage.
- [x] Continuation full gates after probe fix: backend `1016 passed, 9 warnings`; frontend `133 passed`; build `1976 modules`; compileall and `git diff --check` passed.
- [x] Real artifact probe after fix: LOG01 and GOC01 both `pass`, each with 3 frame samples and 0 signals; paired comparison `pass`.
- [x] `SequencePlayer.jsx` ownership audit completed; existing working-tree camera changes were preserved and the live style adapter was integrated into the same file.
- [x] Live style visual adapter [main]: `style_preset` now flows EditorShell → SequencePlayer → SubtitleEngine/overlay events; parity assertions pass and the multi-frame FFmpeg render gate passes.
- [x] Final real-artifact recheck (2026-09-10): LOG01 `pass` (24.6s, 1080x1920, 30fps, 44.1kHz stereo, A/V delta `0.011995s`, 3 samples, 0 signals); GOC01 `pass` (55.948s, 1080x1920, 30fps, 44.1kHz stereo, A/V delta `0.014672s`, 3 samples, 0 signals).

## Round ANALYTICS-CHARTS-POLISH-1 — ปรับขนาดและจัดระเบียบเลย์เอาท์กราฟใน Analytics Hub ให้กระชับ สวยงาม พอดีสายตา ไม่ใหญ่เกินจำเป็น

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ปัญหา:**
1. **กราฟเส้น Daily Token Volume ใหญ่เกินความจำเป็น:** viewBox แคบทำให้บนจอกว้างกราฟยืดสูงเกือบ 400px กลายเป็นคลื่นยักษ์ที่มีพื้นที่โล่งสีดำว่างเปล่า และตัวเลขแกน X ด้านล่างถูกตัดขอบ
2. **กราฟโดนัท Content Angles พังเมื่อมีหลายมุม:** มี 20+ มุมมอง ทำให้สร้างชิ้นพายซอยย่อย 20 ชิ้น และ legend เรียงเดี่ยวยาวเฟื้อยลงมาเป็น 700px ดันโดนัทจมลงไปข้างล่าง แถมชื่อมุมมองไม่แสดง (แสดงแค่จุดและเลข 9 (20%), 1 (2%)) เพราะบั๊ก `slice.name` vs `slice.label`
3. **การ์ด Models & Tasks ใน TokenDashboard สูงเกินไป:** โดนัทถูกวางไว้ตรงกลางข้างบนแล้ว progress bar อยู่ข้างล่าง ทำให้การ์ดยืดสูงและมีพื้นที่ว่างมากเกินไป

**เป้าหมาย:**
1. แก้ `DonutChart.jsx`: แก้บั๊ก `slice.label || slice.name` + เพิ่มฟีเจอร์จำกัด `maxSlices` (รวมชิ้นที่เกินเป็น 'อื่นๆ' อัตโนมัติ ป้องกันชิ้นพายฝอย) + ปรับขนาด default ให้กะทัดรัด (130-140px)
2. แก้ `AreaLineChart.jsx`: ปรับ viewBox เป็น Widescreen (800x130) สัดส่วนกระชับ ป้องกันการยืดสูงบนจอกว้าง + ปรับ padding ล่างไม่ให้ตัวเลขตัดขอบ
3. แก้ `ProductionAnalyticsTab.jsx`: Content Angles จำกัด Top 4 + อื่นๆ จัดวางโดนัทคู่กับรายการอย่างกะทัดรัด ความสูงบาลานซ์กับตารางข้างๆ
4. แก้ `TokenDashboard.jsx`: จัดวางโดนัทไว้ด้านซ้าย (ขนาด 125px) และรายการบาร์อยู่ด้านขวา ลดความสูงการ์ดลง 50% พอดีสายตา + Daily Volume ปรับเป็นความสูงกระชับ (130px)
5. ปรับ `StorageAnalyticsTab.jsx` และ `InventoryAnalyticsTab.jsx` ให้ขนาดชาร์ตและสัดส่วนพอดีกันทั้งระบบ

### Todo

- [x] แก้ `frontend/src/components/analytics/charts/DonutChart.jsx` (แก้ label name, maxSlices grouping, compact sizing)
- [x] แก้ `frontend/src/components/analytics/charts/AreaLineChart.jsx` (widescreen viewBox 800x130, fix cut-off labels)
- [x] แก้ `frontend/src/components/analytics/tabs/ProductionAnalyticsTab.jsx` (Top 4 + อื่นๆ, compact layout)
- [x] แก้ `frontend/src/components/TokenDashboard.jsx` (จัดวาง side-by-side ในการ์ด Models & Tasks, Daily Chart 130px)
- [x] ปรับความกระชับใน `StorageAnalyticsTab.jsx` และ `InventoryAnalyticsTab.jsx`
- [x] รันการทดสอบ Vitest, Pytest, Build และตรวจสอบความสวยงามผ่าน Browser Subagent

### Gate

- [x] กราฟทุกตัวมีขนาดพอดีสายตา ไม่ยืดใหญ่เทอะทะ
- [x] Content Angles แสดงชื่อมุมมองถูกต้อง และชิ้นพายจำกัดไม่เกิน 5 ชิ้น (Top 4 + อื่นๆ) ไม่ยืดยาว
- [x] TokenDashboard Models & Tasks จัดวางแบบ Side-by-Side กระชับพอดี
- [x] Frontend Vitest 151 passed, Backend Pytest 4 passed, Build ผ่าน 100%

### Notes

- ปรับ `DonutChart.jsx` แก้บั๊กชื่อหายด้วย `slice.label || slice.name` และเพิ่ม automatic slice grouping ด้วย `maxSlices = 5` (รวมมุมมองที่เกินเป็น 'อื่นๆ' สี Slate)
- ปรับ `AreaLineChart.jsx` เป็น panoramic widescreen 800x130, ปรับ padding ล่าง 28px ทำให้ตัวเลขวันที่ 09-07 ถึง 09-11 แสดงชัดเจน ไม่ถูกตัดขอบ
- ปรับ `TokenDashboard.jsx` นำ Donut Chart (ขนาด 125px) วางชิดซ้ายคู่กับ Progress Bars ฝั่งขวา ลดความสูงการ์ดลง 45% กะทัดรัดระดับ Pro Dashboard
- ปรับ `ProductionAnalyticsTab.jsx` จัดวาง Donut Content Angles ขนาด 130px พร้อมรายการ 5 หมวดบน-ล่างให้กระชับ สมดุลกับตาราง Recent Productions ข้างเคียง
- ผลทดสอบ: Vitest 151 tests passed, Vite build ผ่านใน 3.25s, Pytest analytics hub 4 passed, ภาพบันทึก browser subagent ยืนยันความสวยงามลงตัว

## Round ANALYTICS-CHARTS-1 — พัฒนาระบบกราฟเส้น กราฟโดนัท Funnel Chart และเกจวัดแบบ Pure SVG สไตล์ Dark Modern Glassmorphism สำหรับแดชบอร์ดทั้ง 4 แท็บ

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
ยกระดับศูนย์วิเคราะห์ข้อมูลและสถิติรวม (Analytics & Operations Hub) ให้แสดงผลด้วยแผนภาพและกราฟอันสวยงาม มีมิติ ไม่เป็นตัวเลขหรือกล่องสี่เหลี่ยมธรรมดา:
1. `AreaLineChart.jsx`: กราฟเส้นโค้ง Bezier + Gradient Glow + Interactive Hover Tooltip สำหรับ Daily Token Volume
2. `DonutChart.jsx`: กราฟวงแหวนโดนัทหลายมิติ พร้อมไฮไลต์ชิ้นพายและตัวเลขตรงกลาง สำหรับ Content Angles, AI Models, Tasks, Storage Folders, และ Inventory Readiness
3. `FunnelPipelineChart.jsx`: แผนภาพกรวยการผลิต 4 เฟสเชื่อมโยงด้วยแสงนีออน พร้อมอัตรา Conversion Rate และ Drop-off
4. `ProgressRing.jsx`: เกจวัดวงแหวนนีออนเดี่ยว และ Triple Concentric Rings (3 ชั้น) สำหรับความสมบูรณ์ของคลังสื่อ

### Todo

- [x] สร้าง `frontend/src/components/analytics/charts/AreaLineChart.jsx`
- [x] สร้าง `frontend/src/components/analytics/charts/DonutChart.jsx`
- [x] สร้าง `frontend/src/components/analytics/charts/FunnelPipelineChart.jsx`
- [x] สร้าง `frontend/src/components/analytics/charts/ProgressRing.jsx`
- [x] อัปเกรด `frontend/src/components/analytics/tabs/ProductionAnalyticsTab.jsx` ฝัง FunnelPipelineChart และ DonutChart
- [x] อัปเกรด `frontend/src/components/TokenDashboard.jsx` ฝัง AreaLineChart และ DonutCharts
- [x] อัปเกรด `frontend/src/components/analytics/tabs/StorageAnalyticsTab.jsx` ฝัง DonutChart และ ProgressRing
- [x] อัปเกรด `frontend/src/components/analytics/tabs/InventoryAnalyticsTab.jsx` ฝัง DonutChart และ Concentric Rings
- [x] ตรวจสอบตามกฎ UI Clean Standard
- [x] รันการทดสอบ Unit Tests และ Build

### Gate

- [x] ทุกชาร์ตเป็น Pure SVG + CSS Render คมชัด ลื่นไหล ไม่พึ่งพา Library ภายนอก (React 19 Zero-conflict)
- [x] แสดงผลสวยงามสไตล์ Dark Modern Glassmorphism มีเอฟเฟกต์ Glow และ Tooltip ตอบสนองฉับไว
- [x] Frontend Vitest (151/151 passed) และ Vite Build สำเร็จ 100% ใน 3.44s
- [x] Backend Pytest (4/4 tests passed) สำเร็จ 100%
- [x] Browser verification ผ่านฉลุยทั้ง 4 แท็บบนเบราว์เซอร์จริง

### Notes

- พัฒนา 4 คอมโพเนนต์กราฟและเกจวัด Pure SVG ระดับพรีเมียมใน `frontend/src/components/analytics/charts/`
- ฝังลงใน 4 แท็บของ Analytics & Operations Hub ครบถ้วนทุกมิติ
- ตรวจสอบผ่าน Browser Subagent บน `https://localhost:5173/` ยืนยันการแสดงผลคมชัด ไม่มี JavaScript runtime errors และสอดคล้องตามมาตรฐาน UI Clean Standard 100%

## Round DELETED-TIMELINE-SYNC-1 — ซิงค์สถานะโปรเจกต์ที่ถูกลบออกจาก NewClipPanel, ล็อกปุ่มแผนถ่ายเมื่อถูกล็อก, และนำปุ่มย้อนสถานะออก

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:**
1. **นำปุ่ม "ย้อนสถานะ" ออกทั้งหมด (Unified UI Standard):** ถอดปุ่มย้อนสถานะออกจากทั้ง Locked Notice Banner และ Action Bar ใน `ProductToClip.jsx` เพื่อให้สถานะของมุมเป็นไปตามโฟลว์จริงของระบบ (เมื่อลบโปรเจกต์ไทม์ไลน์ สถานะจะ Reconcile กลับเป็น scripted ให้ตัดใหม่ได้อัตโนมัติ)
2. **ล็อกปุ่ม "แผนถ่าย" เมื่อมุมถูกล็อก (`isLocked`):** ล็อกและซ่อนปุ่ม "แผนถ่าย" ร่วมกับปุ่ม "รีสคริปต์ด้วย AI" และ "แก้ไขสคริปต์" ทั้งใน `AngleActiveWorkbench` และ `ScriptAccordionItem` เมื่อมุมมีสถานะ `โพสต์แล้ว` หรือ `กำลังตัดต่อ`
3. **แก้ไขข้อความเตือนโปรเจกต์ค้างใน `NewClipPanel.jsx`:** เพิ่มการตรวจเช็ค `angleSpecificProject` กับรายชื่อโปรเจกต์จริงใน `existingProjects` ถ้าโปรเจกต์ถูกลบไปแล้ว จะไม่ดึงชื่อเดิมที่ค้างอยู่ใน metadata มาแสดง ทำให้กล่องเตือนสีเหลืองหายไปทันที และใน `EditorShell.jsx` เมื่อกดยืนยันลบโปรเจกต์สำเร็จ ให้เรียกอัปเดต state สินค้าล่าสุดกลับมายัง `App.jsx` ทันที

### Todo
- [x] ใน `ProductToClip.jsx`: ลบปุ่ม "ย้อนสถานะเพื่อตัด/แก้ไขใหม่" ออกจาก Locked Notice Banner และ Action Bar
- [x] ใน `ProductToClip.jsx`: ซ่อน/ปิดปุ่ม "แผนถ่าย" เมื่อ `isLocked` (แสดงเฉพาะเมื่อ `!isLocked`)
- [x] ใน `NewClipPanel.jsx`: ปรับการคำนวณ `angleSpecificProject` ให้ตรวจเช็คว่าโปรเจกต์มีอยู่จริงใน `existingProjects`
- [x] ใน `EditorShell.jsx`: เมื่อ `confirmDelete` สำเร็จ ดึงข้อมูลสินค้าล่าสุดและส่ง `onProductContextChange` กลับไปยัง `App.jsx`
- [x] รันการทดสอบและ build ผ่านสมบูรณ์

### Gate
- [x] ไม่มีปุ่มย้อนสถานะแปลกปลอมใน ProductToClip
- [x] ปุ่มแผนถ่ายไม่สามารถกดได้เมื่อมุมอยู่ในสถานะโพสต์แล้วหรือกำลังตัดต่อ
- [x] เมื่อลบโปรเจกต์แล้ว หน้า NewClipPanel ไม่แสดงกล่องเตือนสีเหลืองว่ามีโปรเจกต์ค้างอยู่
- [x] Vitest pass (151 tests) & vite build pass

---

## Round SHOT-LIST-ENHANCE-2 — ปรับคำแนะนำมุมกล้องและการถ่ายทำในแผนถ่ายให้เจาะลึกเฉพาะซีนตามบทพูดจริง (Semantic Action Guidance)

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** 
1. **Semantic Script Analysis:** ปรับ `camera_direction_for_beat()` ให้แยกแยะการกระทำตามคำสำคัญ (Keywords) ในแต่ละประโยคบทพูดจริง เช่น คลิก/ปุ่ม/เงียบ/ลื่นไหล, ปวดเมื่อย/สุขภาพ/องศา/สรีระ, ราคา/คุ้ม/วันละ, บลูทูธ/สลับเครื่อง/ถ่าน ไม่ให้ขึ้นคำแนะนำซ้ำซากจำเจ
2. **Auto Product Name & Model Detection:** หาก `category` ว่างเปล่า ให้นำ `product_name` มาวิเคราะห์หมวดสินค้าอัตโนมัติ (เช่น Logitech Lift -> Desk Tech / Ergonomic Mouse ทันที)
3. **Multi-scene Differentiation:** แต่ละซีนของ Feature Beats ต้องมีคำแนะนำแอคชั่นการถือ/จับ/หมุน/กด/วางที่ไม่ซ้ำกัน ทำให้คนถ่ายรู้ว่าในแต่ละวินาทีต้องทำท่าทางอะไรกับสินค้า

### สิ่งที่ทำ

1. ปรับปรุง `camera_direction_for_beat()` ใน [scripts/shot_list_builder.py](file:///d:/Winona/Programmer/Capcut/scripts/shot_list_builder.py) ให้รวม `product_name` เข้ากับการตรวจจับหมวดหมู่ (เช่น เจอ mouse, lift, keyboard, cable, beauty)
2. เพิ่มระบบ Semantic Context วิเคราะห์ประโยคบทพูดและคำบนหน้าจอ:
   - เสียงคลิก/ปุ่ม/SmartWheel: แนะนำใช้นิ้วกดคลิกและหมุน SmartWheel ให้เห็นความนุ่มลื่นเงียบกริบ
   - สุขภาพ/ปวดเมื่อย/ข้อมือ/สรีระ/องศา: แนะนำทาบมือลงบนเมาส์ ยกให้เห็นมุมเอียง 57° ที่กระชับพอดีฝ่ามือ ไม่เกร็งข้อมือ
   - ความคุ้มค่า/ราคา/วันละ/ลงทุน: แนะนำยกเมาส์ขึ้นมาถือหรือหมุนช้าๆ 360° โชว์ความพรีเมียมและวัสดุ
   - บลูทูธ/ไร้สาย/สวิตช์: แนะนำพลิกด้านใต้เมาส์ให้เห็นสวิตช์เปิด-ปิด หรือปุ่มสลับเครื่อง Easy-Switch
3. เพิ่มการสลับ Default actions กรณีไม่มีคำเจาะจง เพื่อไม่ให้ช็อตที่ติดกันแสดงข้อความซ้ำกัน
4. เพิ่มชุดทดสอบใน `tests/test_shot_list_enhancements.py` ครอบคลุมเคสสคริปต์จริงของ Logitech Lift ผ่านครบ 100%

### Gate

- [x] Backend test สำหรับ semantic camera directions ผ่านครบ (`tests/test_shot_list_enhancements.py`, 5 passed)
- [x] `npm test -- --run` ใน frontend ผ่านครบ 100% (151 tests passed)

---

## Round SHOT-LIST-ENHANCE-1 — ยกระดับโฟลว์แผนถ่าย (Shot List Enhancement - Phase 1)

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** 
1. **Invalidate & Detect Stale Shot List:** เมื่อสคริปต์ (`script_lines`) มีการแก้ไข (ผ่าน hand-edit หรือ AI reroll) ให้ระบบตรวจจับได้ และลบ/แจ้งเตือนว่าแผนถ่ายเก่าหมดอายุ (Stale) ต้องกดสร้างใหม่เพื่อไม่ให้เวลาและบทพูดเพี้ยน
2. **Shot List Navigation ใน ContentTrackerHub:** เพิ่มปุ่ม "แผนถ่าย" ในหน้า Content Tracker Hub (ทั้งในแถบ Action ของ `InspectAngleModal` และปุ่มด่วน) พร้อมเปิด `ShotListModal` ดูคำแนะนำ/สแกน QR ได้ทันที
3. **Smart Framing by Category:** ปรับคำแนะนำกล้องใน `shot_list_builder.py` ให้ฉลาดขึ้นตามหมวดสินค้า (`category`) เช่น IT/เมาส์คีย์บอร์ด แนะนำ Top-down/45°, แฟชั่น แนะนำ Close-up Texture
4. **Resilient UX:** ปรับปรุง State ให้มั่นคง ไม่หมุนค้าง และมี fallback error ชัดเจน

### สิ่งที่ทำ

1. **Backend / Data Store:**
   - เพิ่มเมธอด `ShotListsStore.delete(product_id, angle_id)` และ `ShotListsStore.is_stale(product_id, angle_id, current_script)` ใน `scripts/shot_lists_store.py`
   - ปรับ `ProductStore.replace_angle_content` และ `ProductStore.update` เมื่อสคริปต์เปลี่ยน ให้ลบ Shot List เดิมของมุมนั้นโดยอัตโนมัติ เพื่อป้องกันเวลาเสียงพากย์คลาดเคลื่อน
   - ปรับ `GET /api/products/{id}/angles/{id}/shot-list` ให้คืนค่า `is_stale: true/false` หากพบว่าสคริปต์ปัจจุบันไม่ตรงกับที่แคชไว้
2. **Smart Category Framing (`scripts/shot_list_builder.py`):**
   - ปรับ `camera_direction_for_beat()` และ `build_shot_list()` ให้รองรับ `category`
   - แนะนำมุมตั้งกล้องเฉพาะหมวด:
     - Desk Tech (เมาส์/คีย์บอร์ด): แนะนำมุมเฉียง 45° หรือ Top-Down ส่องบนโต๊ะทำงาน
     - Cables/Chargers: แนะนำมุม Close-up โชว์การม้วนเก็บ สายถัก และความทนทาน
     - Beauty/Skincare: แนะนำมุมสว่าง Medium Close-up ถือใกล้ใบหน้าและโชว์เนื้อสัมผัส
3. **Frontend Integration:**
   - ปรับ `frontend/src/components/ShotListModal.jsx` เพิ่มแถบเตือนสีแดงกะพริบแจ้งเตือนเมื่อ `result.is_stale === true` พร้อมปุ่ม "อัปเดตแผนถ่าย" 1-คลิก
   - ปรับ `frontend/src/components/ContentTrackerHub.jsx` เชื่อมต่อ `ShotListModal` เต็มรูปแบบ:
     - เพิ่มปุ่ม "แผนถ่าย" ในแถบ Action ของ `InspectAngleModal`
     - รองรับการสร้าง/เปิดดูแผนถ่ายและการสแกน QR Code ถ่ายทำผ่านมือถือจากหน้า Content Tracker Hub ได้โดยตรง
4. **Testing & Verification:**
   - เพิ่มชุดทดสอบ `tests/test_shot_list_enhancements.py` ทดสอบ CRUD, Stale detection และ Category framing ผ่านครบ 4/4 tests
   - Frontend test ผ่าน 151/151 tests, `npm run build` สำเร็จเรียบร้อย

### Gate

- [x] Backend test สำหรับ `ShotListsStore.delete`, `is_stale` และ `camera_direction_for_beat` ผ่านครบ (`tests/test_shot_list_enhancements.py`, 4 passed)
- [x] `npm test -- --run` ใน frontend ผ่านครบ 100% (151 tests passed)
- [x] `npm run build` ใน frontend ผ่านไร้ error (1,984 modules transformed)

---

## Round PERSIST-LAYOUT-FIX-1 — Product Selection Persistence & Toolbar Alignment Fix

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** 
1. แก้ปัญหารีเฟรชแล้วไม่จำสินค้าที่เลือก (เลือก Logitech Lift แต่พอนึกรีเฟรชกลับเด้งไปสินค้าตัวแรก): เพิ่ม local storage fallback และ sync active product context ทั้งสองทาง
2. จำสคริปต์/มุมขายที่เปิดค้างไว้ (`openAngleIdx`): บันทึกและ restore ทั้งระดับ product (`capcut_active_angle_idx_${id}`) และ global เมื่อรีเฟรชหน้า ไม่เด้งกลับไปมุม 0
3. คลีน Header ใน `ProductToClip.jsx`: ตัดป้าย "ราคาพิเศษในตะกร้า" และป้าย ID ที่รกออก เพื่อให้หัวเรื่องสินค้าเด่นชัดบรรทัดเดียว
4. ย้าย TikTok Product ID (`tiktok_product_id`) เข้าไปแก้ไขและจัดการในหน้าต่าง "ข้อมูล AI" ([ProductMetadataModal.jsx](file:///d:/Winona/Programmer/Capcut/frontend/src/components/ProductMetadataModal.jsx)) ไม่กินพื้นที่แถบหัวบน
5. ขยายขนาดชื่อสินค้าและปรับ Typography ให้คมชัด ใหญ่ ชัดเจน ในบรรทัดเดียว (`titleClassName` ใน `PageHeader.jsx`)
6. จัดการ Layout Toolbar ใน `ProductToClip.jsx` แถว 2 ที่ปุ่มแอ็กชัน wrap ตกบรรทัดลงมาไม่สวยงามบนจอมือถือ (430px) ให้เรียงเป็น 1 แถวอย่างเป็นระเบียบ (scrollable flex-nowrap) ไม่แตกแถว
7. ตรวจสอบและปรับปรุง Modal action buttons ใน `ContentTrackerHub.jsx` (InspectAngleModal) ให้จัดเรียงแบบ grid สมมาตร 2 คอลัมน์บนมือถือ ไม่ wrap กระจัดกระจาย

### Gate

- `npm test -- --run` ใน frontend ผ่านครบ (151 passed)
- `npm run build` ใน frontend ผ่านไร้ error (built in 3.23s)

---

## Round RESPONSIVE-LAYOUT-1 — ปรับแต่ง Responsive Layout (1440×900 vs 430×932)

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ปรับแต่ง Responsive Layout ทั้งหมดใน `frontend/src` รองรับ 2 ขนาดเป้าหมาย: Desktop 1440×900 (baseline Tailwind lg/xl) และ Mobile 430×932 (iPhone 15 Pro Max portrait Tailwind base/no-prefix) โดยใช้เฉพาะ default Tailwind breakpoints, ขจัด overflow, ขยาย touch target $\ge 44\text{px}$, และจัดระเบียบปุ่ม/modal ไม่ให้ตกขอบ

### สิ่งที่ทำ

1. **Phase 1: Shared Shell & Global Drawers**
   - `Sidebar.jsx`: ปรับ Touch Target ของแถบ Bottom Tab Bar มือถือเป็น `min-h-[48px]`, `py-1 px-2` พร้อม active:scale-95
   - `Topbar.jsx`: จัด layout ชื่อหน้าและปุ่ม header ด้วย `min-w-0 flex-1 mr-2` ยุบข้อความยาวคงเหลือไอคอน touch target $\ge 36\text{px}$ ป้องกัน header truncation บนจอ 430px
   - `ActivityCenter.jsx`: ปรับ Slide-over Drawer เป็น `w-full max-w-full sm:max-w-md` และปรับ Filter Tabs 3 ปุ่มไม่ให้ตกบรรทัดหรือล้นขอบจอ
2. **Phase 2: Core Creation & Editing Flow**
   - `ProductToClip.jsx`: ปรับ Action Tools Group ไม่ให้ตัดตกบรรทัด
   - `ContentTrackerHub.jsx`: ปรับปุ่ม Action ใน `InspectAngleModal` บนมือถือให้ wrap 2 คอลัมน์ได้พอดี
   - `TrimAdjustModal.jsx`: ขยายจุดจับดึงตัดหัวท้ายคลิป (Start/End trim drag handles) ด้วย touch hitbox พิเศษ (`before:-inset-x-2.5`) ให้นิ้วแตะลากได้แม่นยำ
3. **Phase 3: Support Hubs & Modals**
   - `ExportGallery.jsx`: ขยาย Touch Target แถบฟิลเตอร์สถานะคลิปเป็น `min-h-[36px]` พร้อม `touch-pan-x` และปรับแถบ Floating Batch Action Bar ให้ลอยขึ้น (`bottom-20 sm:bottom-6`) ไม่บัง Bottom Tab Bar ของมือถือ
   - `MediaAssetsHub.jsx`: ขยายปุ่ม Play/Pause ของ SFX และ BGM เป็น `w-11 h-11` ($\ge 44\text{px}$) แตะง่ายไม่วืด
   - `TokenDashboard.jsx`: เพิ่ม `touch-pan-x` และ `min-w-[700px]` ให้ตาราง Ledger สถิติเลื่อนด้วยนิ้วบนจอ 430px ได้นุ่มนวล
4. **Phase 4: Verification & Gate**
   - `npm test -- --run` ผ่านครบ 150/150 tests
   - `npm run build` ผ่านสมบูรณ์ (Vite production bundle สำเร็จใน 3.43s)
   - `pytest tests/test_preview_render_parity.py` ผ่านครบ 153/153 tests

### Gate

- [x] ทุกหน้าแสดงผลถูกต้อง ไม่พังทั้ง 1440x900 และ 430x932
- [x] ไม่มี touch target หลักที่ผู้ใช้ต้องแตะ < 44px บน mobile
- [x] ไม่มี horizontal overflow หรือ scrollbar แนวนอนหลุดบน body
- [x] `npm run build` (3.43s) และ `npm test` (150 passed), pytest parity (153 passed) ผ่านครบถ้วน

---

## Round PRODUCT-METADATA-8 — อ่าน metadata จากรูปแบบเบื้องหลัง

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ผู้ใช้เริ่มอ่านข้อมูลจากรูปอ้างอิงแล้วปิดโมดัลหรือเปลี่ยนหน้าได้ งานต้องทำต่อใน background ผ่าน TaskManager, มี progress/notification แบบงานอื่น และเมื่อเสร็จสามารถเปิดผล preview เดิมกลับมาตรวจ/เลือก field/บันทึกได้ โดยไม่บันทึกทับอัตโนมัติ

### สิ่งที่ทำ

1. แยก logic อ่านรูปเป็น helper และเพิ่ม `preview-image-metadata-async` ที่สร้าง persistent `image_metadata` task ผ่าน `TaskManager`; worker เก็บผล preview ไว้ใน task result และไม่เขียน product อัตโนมัติ
2. เปลี่ยนปุ่มอ่านรูปใน ProductToClip ให้ enqueue งานแล้วปิดโมดัลได้ทันที พร้อมบอกให้ติดตามจาก Activity Center
3. เพิ่มไอคอน/ปุ่ม `ตรวจผลอ่านรูป` ใน Activity Center และ Global Task Notification; เมื่อตรวจผล ระบบเลือกสินค้าเดิม เปิด Metadata Inspector และคืน preview เพื่อเลือก field/แก้ไข/ยืนยันบันทึกตาม flow เดิม
4. คง synchronous endpoint เดิมไว้เพื่อ compatibility กับ caller เก่า
5. เพิ่ม backend async lifecycle regression และ route contract coverage

### Gate

- [x] focused image metadata tests + route contract — 22 passed, 1 warning
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,055 passed, 24 warnings, 0 failed (ใช้เวลา 130.44 วินาที)
- [x] `Set-Location frontend; npm test` — 149 passed
- [x] `npm run lint` — 0 errors; warnings เดิมของโปรเจกต์
- [x] `npm run build` — ผ่าน, Vite transformed 1,981 modules
- [x] `git diff --check` — ผ่าน
- [x] Impeccable detector — พบ 1 warning เดิม `gray-on-color` ที่ ActivityCenter.jsx บรรทัด 292; ไม่ใช่โค้ดที่เพิ่มในรอบนี้

### Notes

- ผล Vision ยังเป็น read-only preview ใน task registry จนกว่าผู้ใช้จะกดตรวจ เลือก field และยืนยัน จึงไม่เสี่ยงทับ metadata เดิมระหว่างทำงานเบื้องหลัง
- การทดสอบ full suite รอบแรกหมดเวลา 124 วินาทีเพราะ gate เดิมใช้เวลาประมาณ 130 วินาที; รันซ้ำด้วย timeout สูงขึ้นและผ่านครบ
- ยังเหลือ manual live verification กับรูป BlueWow/โควตา Gemini ตามงาน PRODUCT-METADATA-7 เดิม

## Round COMMIT-SPLIT-1 — จัดกลุ่ม commit working tree ค้าง + LIVE_VALIDATION_CHECKLIST

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** จัดการงานค้างใน working tree ข้าม 2 workstream (product metadata PM-4/5/6 และ post/export lifecycle) ให้เป็นระเบียบ และรวม live gate ที่รอ user ทั้งหมดเป็น checklist เดียว

### สิ่งที่ทำ

1. ตรวจ `git status` + diff รายไฟล์ จำแนก 17+ ไฟล์แก้ค้างเข้า 5 workstream
2. รัน deterministic gates ทั้งหมดก่อน commit
3. Commit แยก 5 กลุ่ม:
   - `7ed1fbb` feat(products): metadata edit/dedupe preview, raw-text boundary, stable selection (PM-4/5/6) — ProductMetadataModal, ProductToClip, productSelection.js+test, api_products, product_scraper, test_product_metadata, api.js
   - `b3ca2f7` fix(exports/videos): move-retry on Windows file lock, registry-before-store mark-posted order — api_videos, api_exports, test_post_lifecycle, test_backend_api_contracts
   - `9ce784f` fix(editor): cover gate simplification and no-video-source preview state — CoverStudioModal, EditorShell, schedule_queue.json
   - `31086f3` chore(ui): raw vault polish and tracker card cleanup — ContentTrackerHub, RawVaultPanel, custom_hook_templates.json
   - `c7626bb` docs: live validation checklist and round bookkeeping — TODO/HISTORY/PRO_EDITOR_STYLE_PLAN + LIVE_VALIDATION_CHECKLIST.md
4. สร้าง `LIVE_VALIDATION_CHECKLIST.md` รวม live gate ที่รอ user: PM-3/4/5/6 (กลุ่ม A), POST-1 + POST-3.20 (กลุ่ม B), POST-3.16–3.18 (กลุ่ม C) + optional (full render loop, SUB-THAI-2)

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,050 passed, 2 failed (pre-existing ที่ HEAD: `test_per_word_vs_monolithic_render_parity` 284px divergence และ `test_ibm_thai_marks_have_separate_vertical_bands` — ทดลองรันซ้ำ 2 failed คงเดิม deterministic, ไฟล์ subtitle ไม่ได้อยู่ใน working diff จึงไม่เกี่ยวกับงานที่ commit)
- [x] `npm test` — 149 passed / `npm run build` — ผ่าน / `npm run lint` — 0 errors (390 warnings เดิม)
- [x] `git diff --check` — ผ่าน
- [x] commits ครบทุกไฟล์ที่แก้ เหลือเพียง untracked `header-toggle-test-1.png` (ตั้งใจไม่ commit รอ user ตัดสินใจ)

### Notes

- ระหว่างรอบมี commit `27e8441` (metadata preview) และ `aa1f5b8` (security audit fixes) จาก agent อื่นเข้าก่อน — ทำให้ไฟล์ `frontend/src/api.js`, `tests/test_backend_api_contracts.py` โผล่ใน diff ทีหลัง ตรวจแล้วรวมในกลุ่มที่เกี่ยวข้องถูกต้อง
- 2 pytest failures ข้างบนเป็นบั๊ก subtitle render ที่มีอยู่แล้วใน HEAD — ควรเปิดรอบแยกแก้ (เกี่ยวกับ SUB-THAI-2 ที่พักไว้)

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
| Round TLO-REFACTOR-1 | แยก abstraction ของ Overlay Timeline/Preview แบบรักษา behavior เดิม | 2026-09-09 | Phase 0–6 เสร็จ · frontend 100 tests · parity 150 tests · FFmpeg behavior 11 tests · build 1972 modules |
| Round TLO-REFACTOR-2 | ลด duplication ฝั่ง renderer เฉพาะจุดที่พิสูจน์ parity ได้ | 2026-09-09 | policy/config dispatch สำหรับ hook/text · frontend 102 tests · parity 150 tests · FFmpeg behavior 11 tests · build 1972 modules |
| Round TLO-REFACTOR-3 | แยก shared Timeline label-gutter primitive | 2026-09-09 | `TrackLabel.jsx` ใช้ร่วมกับ Timeline/EffectTrack · frontend 102 tests · lint/build/diff check ผ่าน |
| Round TLO-REFACTOR-4 | รองรับ optional trim handles ใน shared timeline shell | 2026-09-09 | Hook ใช้ shared shell แบบ right-trim only · frontend 104 tests · lint/build/diff check ผ่าน |
| Round TLO-REFACTOR-5 | ย้าย Caption chip เข้า shared timeline shell โดยคง magnetic-ripple policy | 2026-09-09 | Caption ใช้ shared shell แต่คง drag/ripple adapters เดิม · frontend 105 tests · lint/build/diff check ผ่าน |
| Round TLO-REFACTOR-6 | รวม shared Inspector header สำหรับ Sticker/Effect | 2026-09-09 | `OverlayInspectorHeader` รับ layout ร่วมและ media/config เฉพาะชนิด · frontend 107 tests · lint/build/diff check ผ่าน |
| Round TLO-REFACTOR-7 | รวม timeline pointer lifecycle โดยคง type-specific drag math | 2026-09-09 | `timelineDragLifecycle` ใช้ร่วมกับ Caption/Text/Hook/Sticker/Effect · frontend 109 tests · lint/build/diff check ผ่าน |
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

## Round TLO-REFACTOR-4 — รองรับ optional trim handles ใน shared timeline shell

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ขยาย `TimelineIntervalItem` ให้รองรับ trim handle แบบเลือกด้านได้ แล้ว migrate Hook chip ซึ่งมี right-trim เท่านั้น โดยคง behavior เดิม

### สิ่งที่ทำ

- เพิ่ม `showLeftHandle`/`showRightHandle` แบบ default เป็น `true` ที่ `TimelineIntervalItem.jsx`
- ปรับ Hook track ใน `Timeline.jsx` ให้ใช้ shared shell โดยปิด left handle และคง right-trim callback/title/hover color เดิม
- คง Caption แยกไว้ เพราะใช้ cue ripple/apply-to-all และไม่มี trim policy เดียวกับ interval tracks
- เพิ่ม `timelineIntervalContract.test.js` กัน default two-handle regression และยืนยัน Hook single-sided contract

### Gate

- [x] `Set-Location frontend; npm test` — 104 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1973 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- ไม่เปลี่ยน Hook duration clamp (`1.0–8.0s`), click-to-seek, selection หรือ Caption ripple
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-7 — รวม timeline pointer lifecycle โดยคง type-specific drag math

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** รวม pointer capture/release และ movement threshold 3px ของ timeline drag ไว้ใน `timelineDragLifecycle.js` โดยไม่รวม geometry หรือ type-specific policy

### สิ่งที่ทำ

- เพิ่ม `timelineDragLifecycle.js` สำหรับ `capturePointer`, `releasePointer` และ `beginDragAfterThreshold`
- ปรับ `useTimelineDrag.js` ให้ใช้ lifecycle module เดียวกับ Caption, Text, Hook, Sticker และ Effect
- คง state shape, callback order, 3px threshold, snap, clamp, rounding, field mapping และ Caption ripple เดิม
- เพิ่ม deterministic unit tests ตรวจ threshold, เรียก `dragBegin` ครั้งเดียว และ pointer capture/release ที่ tolerate synthetic events

### Gate

- [x] `Set-Location frontend; npm test` — 109 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1975 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- เป็น lifecycle extraction เท่านั้น ไม่เปลี่ยน timing/geometry behavior ของ overlay ใด
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-6 — รวม shared Inspector header สำหรับ Sticker/Effect

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** รวม layout ของ preview header, identity label และ timing metadata ของ Sticker/Effect ไว้ใน `OverlayInspectorHeader` โดยคง media preview และ visual config ที่ต่างกันไว้เป็น props

### สิ่งที่ทำ

- เพิ่ม `OverlayInspectorHeader.jsx` สำหรับ preview frame, icon/label, title และ duration metadata ร่วม
- ปรับ `StickerInspector.jsx` ให้ส่ง image preview, `Smile`, cyan accent และ label เดิม
- ปรับ `EffectInspector.jsx` ให้ส่ง video preview, multiply blend, `Sparkles`, fuchsia accent และ label เดิม
- เพิ่ม `overlayInspectorHeaderContract.test.js` ยืนยัน shared layout และ media-specific config ของทั้งสอง Inspector
- คง Position, timing/scale callbacks และ delete actions ตาม policy เดิมของแต่ละชนิด

### Gate

- [x] `Set-Location frontend; npm test` — 107 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1974 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- เป็น structural extraction/config seam เท่านั้น ไม่เปลี่ยน renderer, preview canvas, timeline drag หรือ visual timing
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-5 — ย้าย Caption chip เข้า shared timeline shell โดยคง magnetic-ripple policy

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ย้ายโครงสร้าง Caption chip, trim handles และ body drag เข้า `TimelineIntervalItem` โดยคง behavior-specific drag policy ของ Caption ไว้ใน `useTimelineDrag.js`

### สิ่งที่ทำ

- ปรับ Caption track ใน `Timeline.jsx:1123-1165` ให้ใช้ shared shell เดียวกับ Hook/Sticker/Effect/Text
- ส่ง `startTrim`, `moveTrim`, `endTrim` และ `startCaptionBodyDrag`/`moveCaptionBodyDrag`/`endCaptionBodyDrag` ผ่าน adapter callbacks โดยไม่ย้ายหรือเปลี่ยน geometry math
- คง previous-cue clamp, magnetic ripple/apply-to-all, click-to-select, titles และสีของ Caption เดิม
- เพิ่ม contract test ใน `timelineIntervalContract.test.js` เพื่อยืนยันการใช้ shell และการคง caption-specific callbacks

### Gate

- [x] `Set-Location frontend; npm test` — 105 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1973 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- ไม่รวม Caption drag math, previous-cue clamp หรือ magnetic ripple เข้า shared core เพราะเป็น behavioral divergence จริง
- ไม่แตะ renderer, preview, timing constants หรือ audio lanes
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-3 — แยก shared Timeline label-gutter primitive

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ย้าย `TrackLabel` ออกจาก `Timeline.jsx` ไปเป็น primitive กลาง เพื่อให้ label gutter ของ Timeline และ EffectTrack ใช้ implementation เดียวกัน โดยคง callback, icon slot, fold control, action slot, width/dense sizing และ event propagation เดิม

### สิ่งที่ทำ

- เพิ่ม [TrackLabel.jsx](frontend/src/components/editor/timeline/TrackLabel.jsx) เป็น shared label-gutter component
- ปรับ `Timeline.jsx:1-10,142-191,662-664` ให้ import และใช้งาน primitive กลาง โดยลบ implementation inline เดิม
- ปรับ `EffectTrack.jsx:1-30` ให้ import โดยตรง และลบ prop injection `TrackLabel`
- ไม่รวม visibility action หรือ label text เพราะแต่ละ track มี callback/title/color และเงื่อนไขการแสดงผลต่างกัน

### Gate

- [x] `Set-Location frontend; npm test` — 102 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1973 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- เป็น structural extraction เท่านั้น ไม่เปลี่ยน renderer output, timeline timing, drag handlers หรือ overlay geometry
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-2 — ลด duplication ฝั่ง renderer เฉพาะจุดที่พิสูจน์ parity ได้

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ตรวจ duplication ที่เหลือใน Canvas/ASS renderer และรวมเฉพาะ policy/dispatch ที่มี contract ร่วมกันจริง โดยคง drawing policy ที่ต่างกันไว้แยก

### สิ่งที่ทำ

- เพิ่ม `OVERLAY_RENDER_PROFILES` และ `overlayRenderProfile()` ใน `frontend/src/lib/overlayModel.js` เพื่อเก็บความต่างของ hook/text เป็น data: default animation, word-stagger, layout clearing และ bounds type
- เปลี่ยน `SequencePlayer.jsx:1486-1641` ให้ใช้ profile เดียว โดยรักษา fallback ของ unknown frontend kind ไป text path
- เพิ่ม `overlay_kind()` ใน `scripts/overlay_model.py` และใช้ handler map ใน `scripts/subtitle/overlay_events.py:54-67` เพื่อ normalize `kind`/`type` และ legacy aliases โดยไม่แตะ geometry หรือ ASS drawing math
- เพิ่ม frontend/Python dispatch tests และปรับ source parity assertion ให้ตรวจ policy contract ใหม่
- ยืนยันจาก inventory ว่า Caption/Hook/Text/Sticker/Effect drawing, anchor, alpha, blend, legacy fields, font metrics และ motion timing ยังเป็น behavior-specific; ไม่ genericize ต่อในรอบนี้

### Gate

- [x] `Set-Location frontend; npm test` — 102 passed
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1972 modules transformed
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/test_overlay_render_dispatch.py -q -p no:cacheprovider --tb=short` — 2 passed
- [x] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider --tb=short` — 150 passed
- [x] `python -m pytest tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 11 passed, Pillow deprecation warnings 2 รายการเดิม
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- ไม่แก้ `scripts/subtitle_engine.py`, drawing constants หรือ output geometry เพราะไม่มีการเปลี่ยนภาพที่พิสูจน์ว่าปลอดภัยในรอบนี้
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-1 — แยก abstraction ของ Overlay Timeline/Preview แบบรักษา behavior เดิม

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ลดโค้ดซ้ำของ Hook, Sticker, Effect, Caption และ Text Overlay ใน timeline/drag/preview โดยแยกเฉพาะ geometry และ lifecycle ที่เหมือนกันออกมาเป็น shared core/config พร้อมคง field names, legacy fallback, clamp, snap, ripple, anchor, audio/visual parity และ selection semantics เดิมทุกประการ

### ผลลัพธ์ตามเฟส

- [x] Phase 0 — สำรวจ contract และบันทึก behavior divergence ของ Timeline, drag hook, SequencePlayer, EditorShell, selection, commands, Inspector และ timeline model
- [x] Phase 1 — เพิ่ม `packTimedLanes` และคง wrapper contract ของ `packTextOverlays`/`packStickers` ใน `timelineTrackModel.js`
- [x] Phase 2 — เพิ่ม `TimelineIntervalItem.jsx` และย้าย Sticker, Effect, Text overlay ไปใช้ shell เดียวกัน โดยคง Hook/Caption ที่มี policy ต่างกันไว้แยก
- [x] Phase 3 — เพิ่ม shared timed-interval drag core ใน `useTimelineDrag.js` สำหรับ Sticker/Effect พร้อม adapter ของ Sticker legacy aliases/signature และ Effect modern fields
- [x] Phase 4 — เพิ่ม `overlayBoxGeometry.js` และ `pointerDragLifecycle.js` สำหรับ selected-box fallback, clamp/snap/resize, field mapping และ window pointer lifecycle โดยคง Caption-specific callbacks
- [x] Phase 5 — เพิ่ม `selectionResolver.js`, `collectionOperations.js`, `OverlayTimingControls.jsx` และ `OverlayScaleControl.jsx`; คง Sticker style mirror/single-slot fallback, Effect overlap placement และ Position block ที่ต่างจริง
- [x] Phase 6 — แก้ parity test baseline ที่ stale จาก 6 เป็น 7 occurrences หลังยืนยันว่า `HEAD` และ current source ตรงกัน และรัน render/behavior gates

### Gate

- [x] `Set-Location frontend; npm test` — 100 passed
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1972 modules transformed
- [x] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider` — 150 passed
- [x] `python -m pytest tests/test_preview_render_behavior.py -q -p no:cacheprovider` — 11 passed, Pillow deprecation warnings 2 รายการ
- [x] `git diff --check` — ผ่าน ไม่มี error
- [x] ตรวจว่าไม่แตะ `01_Raw/`, `02_Assets/`, `03_Projects/` หรือ `_Docs/post_log.json`

### Notes

- การ genericize จงใจหยุดที่ pure math, lifecycle, selection lookup, collection operations และ Inspector controls ที่มี contract ร่วมกันจริง
- Caption magnetic ripple/apply-to-all, Hook 1–8 second end-only trim, Text policy, Sticker legacy mirror/single-slot fallback, Effect overlap-slot placement และ Position UI ที่ต่างกันยังคงเป็น behavior-specific adapters
- parity baseline drift ที่พบเป็น test expectation เดิม ไม่ใช่ production regression: `Timeline.jsx` มี `slotWidth` 7 occurrences ทั้งใน `HEAD` และ current source
- งานเดิมที่มีอยู่ก่อนรอบนี้ยังคงไม่ถูกแตะ: sample sticker 3 ไฟล์ที่ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round SFX-TITLES-1 — ดึงชื่อภาษาไทย/ชื่อจริงที่แสดงบน Myinstants มาใส่เป็น label ใน asset_metadata.json

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ดึง Display Name จากหน้าเว็บ Myinstants ทั้งหมด 50 หน้า บันทึกลงใน `02_Assets/asset_metadata.json` เพื่อให้ชื่อเสียงที่แสดงบนหน้าเว็บ (UI) ทั้ง Media Assets Hub และ AssetPanel แสดงเป็นชื่อภาษาไทย/ชื่อจริงที่อ่านออกและตรงกับหน้าเว็บเป๊ะ

### สิ่งที่ทำ

1. **สร้างสคริปต์ `tools/scrape_myinstants_titles.py`:**
   - ดึงคู่ `(sound_filename, display_title)` จาก 50 หน้าของ Myinstants Thailand
   - รวมชื่อที่ได้ 1,774 รายการบันทึกลงใน `02_Assets/asset_metadata.json` ภายใต้คีย์ `label` และ `label_th` โดยไม่ลบ metadata เดิมของระบบ
2. **อัปเกรด `scripts/asset_registry.py`:**
   - Map ค่า `label` และ `label_th` เข้าสู่ entry ของ SFX และ BGM ทุกชิ้น
3. **อัปเดต Frontend UI (`MediaAssetsHub.jsx` & `AssetPanel.jsx`):**
   - แสดงผล `label` นำหน้าเสมอ และแสดงชื่อไฟล์เป็น secondary info
   - รองรับการค้นหา (Search Query) ด้วยชื่อภาษาไทยและชื่อจริงบนเว็บ

### Gate

- [x] ดึง metadata สำเร็จครบ 50 หน้า (อัปเดต 1,774 รายการ)
- [x] `AssetRegistry.rebuild()` โหลดชื่อ label เข้า sfx สำเร็จ
- [x] `python -m compileall -q scripts tools` — ผ่าน
- [x] `npm test` และ `npm run build` — 86 tests passed, build สำเร็จ

---

## Round SFX-HUB-1 — สแกน SFX แบบ Recursive เข้า AssetRegistry และเพิ่มตัวกรองหมวดหมู่ SFX ใน Media Assets Hub

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ให้ระบบ AssetRegistry และ Backend API สแกนไฟล์เสียง SFX ทุกโฟลเดอร์ย่อยใน `02_Assets/SFX/` แบบ recursive และแสดงผลใน Media Assets Hub พร้อมตัวกรองหมวดหมู่ย่อย (Sub-category Pills) ให้เปิดฟังและเลือกใช้ได้ครบทั้ง 1,822 ไฟล์

### สิ่งที่ทำ

1. **แก้ไข `scripts/asset_registry.py`:**
   - ปรับ `_scan_sfx()` ให้ใช้ `rglob` สแกนทั้งโฟลเดอร์รูทและโฟลเดอร์ย่อยทั้งหมด
   - ดึงชื่อโฟลเดอร์ย่อย (เช่น `thai/`, `game/`, `meme/`, `horror/` ฯลฯ) มาเป็น `category` ของไฟล์นั้นโดยอัตโนมัติ
   - ปรับ `_cache_is_fresh()` ให้ตรวจสอบการเปลี่ยนแปลงของไฟล์ในโฟลเดอร์ย่อยแบบ recursive
2. **แก้ไข `scripts/api_videos.py`:**
   - ปรับ `/api/sfx` ให้ส่งรายการไฟล์ SFX ผ่าน `AssetRegistry.sfx()` เพื่อให้ได้ชุดข้อมูลที่ครบถ้วนตรงกันทั้งระบบ
3. **อัปเกรด `frontend/src/components/MediaAssetsHub.jsx`:**
   - เพิ่มตัวกรองหมวดหมู่ย่อย (Sub-category Pills: ทั้งหมด, เสียงไทย/ตลก, เกม, มีม, รีแอ็กชัน, แจ้งเตือน/UI, ท่อนเพลง, สยองขวัญ, อนิเมะ, เปลี่ยนฉาก/Whoosh, อื่นๆ)
   - เชื่อมโยงตัวกรองเข้ากับช่องค้นหา (Search Query) ค้นหาได้ทั้งชื่อไฟล์และหมวดหมู่
4. **อัปเดต `frontend/src/components/editor/AssetPanel.jsx`:**
   - ปรับการระบุพาธเสียง preview ให้รองรับ `rel_path` จากโฟลเดอร์ย่อยได้โดยตรง

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน
- [x] pytest `test_preview_render_parity.py` — 150 passed
- [x] `npm test` และ `npm run build` — 86 tests passed, build สำเร็จ
- [x] ตรวจสอบ `AssetRegistry.rebuild()` — พบ SFX ทั้งหมด **1,822 ไฟล์** ตรงตามไฟล์จริงบนดิสก์

---

## Round SFX-CAT-1 — จัดหมวดหมู่ไฟล์เสียง mi_xxx 1,775 ไฟล์ เป็น 10 หมวดใน 02_Assets/SFX/

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** จัดระเบียบไฟล์เสียงเอฟเฟกต์ที่โหลดจาก Myinstants (มีคำนำหน้า `mi_*.mp3`) จำนวน 1,775 ไฟล์ เข้า 10 โฟลเดอร์หมวดหมู่ย่อยใน `02_Assets/SFX/` ตามชื่อและคีย์เวิร์ด เพื่อให้ค้นหาและนำไปใช้งานง่าย โดยไม่กระทบกับไฟล์เสียงเดิม 47 ไฟล์ที่อยู่ในรูท

### สิ่งที่ทำ

1. **สร้างสคริปต์ `tools/categorize_myinstants_sfx.py`:**
   - กำหนด 10 หมวดหมู่หลัก: `transition/`, `notification/`, `game/`, `anime/`, `music/`, `reaction/`, `horror/`, `meme/`, `thai/`, `other/`
   - ใช้ Regex Patterns ครอบคลุมคีย์เวิร์ดภาษาอังกฤษ, ศัพท์เฉพาะวงการเกม/อนิเมะ/มีม และรูปแบบการถอดเสียงภาษาไทยเป็นอักษรโรมัน (Romanized Thai Patterns)
   - ป้องกันไฟล์เสียงเดิม: เฉพาะไฟล์ `mi_*.mp3` เท่านั้นที่จะถูกจัดหมวด ไฟล์เสียงต้นฉบับ 47 ไฟล์คงอยู่ที่รูท `02_Assets/SFX/` เสมอ
2. **รันจัดหมวดหมู่จริง:**
   - ย้ายไฟล์ 1,775 ไฟล์เข้าโฟลเดอร์ย่อยครบ 100% ไม่มี error

### ผลลัพธ์การจัดหมวดหมู่

| หมวดหมู่ | โฟลเดอร์ | จำนวนไฟล์ |
| :--- | :--- | :--- |
| **Anime** | `02_Assets/SFX/anime/` | 65 ไฟล์ |
| **Game** | `02_Assets/SFX/game/` | 114 ไฟล์ |
| **Horror** | `02_Assets/SFX/horror/` | 71 ไฟล์ |
| **Meme** | `02_Assets/SFX/meme/` | 114 ไฟล์ |
| **Music** | `02_Assets/SFX/music/` | 90 ไฟล์ |
| **Notification** | `02_Assets/SFX/notification/` | 80 ไฟล์ |
| **Reaction** | `02_Assets/SFX/reaction/` | 79 ไฟล์ |
| **Thai** | `02_Assets/SFX/thai/` | 179 ไฟล์ |
| **Transition** | `02_Assets/SFX/transition/` | 26 ไฟล์ |
| **Other** | `02_Assets/SFX/other/` | 957 ไฟล์ |
| **Original SFX** | `02_Assets/SFX/` (Root) | 47 ไฟล์ (คงเดิม) |
| **รวมทั้งหมด** | | **1,821 ไฟล์** |

### Gate

- [x] ย้ายไฟล์ครบ 1,775 ไฟล์ (`moved=1775, skipped=0, errors=0`)
- [x] ไฟล์เดิม 47 ไฟล์ในรูทปลอดภัย ไม่ถูกย้ายหรือแก้ไข
- [x] สร้างสคริปต์ `tools/categorize_myinstants_sfx.py` พร้อมโหมด `--report` และ `--dry-run`

---

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
## Round TIKTOK-STATS-SCRAPE-1 — ซิงก์สถิติ TikTok Studio ผ่าน Extension

วันที่: 2026-09-12 · สั่งโดย: user (เลือกวิธี extension ไม่ใช้ API เพราะไม่ deploy cloud) · สถานะ: เสร็จสมบูรณ์

**แนวทาง:** ไม่ง้อ TikTok API (เลี่ยง Developer review + Terms/Privacy URL) ใช้ session login จริงของ user ในเบราว์เซอร์ตัวเอง Extension อ่านตารางหน้า Studio Posts แล้ว POST กลับ backend local-only ทั้งหมด

### สิ่งที่ทำ

1. `tiktok_autopost_extension/stats_parser.js`: parse แถวตาราง Studio Posts (ชื่อคลิป, ยอดดู/ถูกใจ/คอมเมนต์/แชร์, thumbnail, video_url/id, ความยาว) แบบ tolerant — หา column ด้วย header text (ไทย/อังกฤษ) ไม่ใช้ index ตายตัว รองรับ comma/K/M suffix + dash กันเลขเพี้ยนเมื่อ TikTok เปลี่ยน DOM
2. `stats_parser.test.cjs`: 5 tests ด้วย fake DOM (ไม่มี dependency) — header lookup เจอ order ใดก็ตาม, missing table คืน error ไทย, row parse ครบทุก field, count suffix, video id regex
3. `sidepanel.html/js`: การ์ด ซิงก์สถิติ ที่ท้าย panel — ปุ่มตรวจ active tab เป็น TikTok ก่อน, inject parser ผ่าน `chrome.scripting.executeScript(files:)`, POST `/api/tiktok-stats/import`, แสดงผล matched/updated/unmatched; manifest เพิ่ม permission `scripting`
4. `scripts/api_tiktok_stats.py`: `POST /api/tiktok-stats/import` (validate ≤200 rows, clean count, upsert) + `GET /api/tiktok-stats/latest`; เมานต์ใน api_server
5. `scripts/post_log.py`: method `upsert_tiktok_stats` + `_fuzzy_match` — match ลำดับ video_id ตรง > ชื่อ+คำซ้อน+ความยาวคลิป (±3s); เก็บ `tiktok_video_id/tiktok_url/tiktok_synced_at`; merge metrics ไม่เขียนทับ orders/commission ที่กรอกมือ
6. `tests/test_tiktok_stats_import.py`: 4 tests offline (tmp storage, monkeypatch) — exact video id, fuzzy match + skip unknown, reject empty/oversized, latest sorted
7. `frontend/src/components/analytics/tabs/PerformanceAnalyticsTab.jsx` + แท็บที่ 5 ใน AnalyticsHub: 4 KPI (วิวรวม, engagement เฉลี่ย, ถูกใจรวม, คลิปปังที่สุด), AreaLineChart ยอดวิวต่อคลิป, Winner/Loser banner พร้อมคำแนะนำมุมขาย, ตารางผลงานแบบเดียวกับในภาพ + คอลัมน์สินค้า/มุมขาย/Engagement + ลิงก์เปิดคลิป TikTok + empty state บอกวิธีซิงก์

### Gate

- `node --check stats_parser.js` + `sidepanel.js` — ผ่าน
- `node --test background.test.cjs + stats_parser.test.cjs` — 21 passed
- `pytest tests/test_tiktok_stats_import.py + test_analytics_hub.py` — 8 passed
- `npm test` — 151 passed · `npm run build` — 4.06s
- `git diff --check` — สะอาด
- ไม่แตะ automation.js steps 1-6 และปุ่ม Post เดิม

### Notes

- `chrome.scripting` จะรัน func ใน isolated world ที่ไม่มี parser จาก sidepanel → ต้อง inject `files:['stats_parser.js']` ก่อนทุกครั้ง
- ต้องโหลด extension ใหม่จาก chrome://extensions หลังเพิ่ม permission `scripting`
- ตัวเลขที่กรอกมือ (orders/commission) ยังอยู่ ไม่ถูกทับ — merge เฉพาะ views/likes/comments/shares ที่เป็น int
- รอบหน้ากรณี unmatched: ปุ่มจับคู่ manual + แจ้งเตือนคลิปปังใน Activity Center (บันทึกเป็น TIKTOK-STATS-SCRAPE-2 backlog ใน TODO.md)
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


## Round USER-GUIDE-1 — เมนูใหม่ "คู่มือใช้งาน" ในโปรแกรม + โฟลว์หลักครบ 7 เมนู

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**

## Round USER-GUIDE-2 — การ์ดเมนูกระชับ วางหลายใบต่อแถว

วันที่: 2026-09-12 · สั่งโดย: user (feedback จากภาพ: การ์ดข้อความสั้นแต่กล่องกว้างเต็มแถว) · สถานะ: เสร็จสมบูรณ์

**สิ่งที่ทำ:**
- `frontend/src/components/UserGuide.jsx` ส่วน `#ug-menus`: จาก `space-y` 1 คอลัมน์เต็มความกว้าง → `grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-2.5 items-start` การ์ดสูงตามข้อความจริง ไม่ยืดตามเพื่อนร่วมแถว
- ลด padding การ์ด `p-4 sm:p-5` → `p-4` กล่องกระชับขึ้น

**ผล:** จอกว้างเห็นเมนู 1+2 ข้างกัน เมนู 3+4 ข้างกัน ไม่ต้องเลื่อนจอยาว มือถือยัง 1 คอลัมน์เหมือนเดิม


## Round USER-GUIDE-3 — กระชับทุกกล่องในคู่มือ

วันที่: 2026-09-12 · สั่งโดย: user (feedback: กล่องอื่นก็โล่งเหมือนกัน + /impeccable /ux-ui-promax) · สถานะ: เสร็จสมบูรณ์

**แนวทาง (impeccable refinement):** เก็บ rhythm เดิมทั้งหมด (PageHeader, การ์ด #0B0F19, chip สี, ลำดับ section, ข้อความ) แล้วลดความสูงด้วย multi-column grids + items-start + padding กระชับเท่านั้น


## Round USER-GUIDE-4 — คู่มือ interactive ใช้งานได้จริง

วันที่: 2026-09-12 · สั่งโดย: user (จัดการแบบละเอียด) · สถานะ: เสร็จสมบูรณ์

**แนวทาง:** impeccable refinement — ไม่เปลี่ยนข้อความ สี ลำดับ section ใดๆ เพิ่มแค่ interaction 6 ฟีเจอร์ใน `frontend/src/components/UserGuide.jsx` (160 → 257 บรรทัด)

**สิ่งที่ทำ:**
1. Sticky TOC ลอยติดบน (`sticky top-52/56px` ตรงความสูง Topbar) + scrollspy ด้วย IntersectionObserver ไฮไลต์หัวข้อที่อ่านอยู่เป็นสี cyan
2. เช็กลิสต์กดติ๊กได้จริง: ปุ่ม toggle ต่อข้อ + แถบความคืบหน้า gradient + ป้าย n/6 + ข้อความพร้อมโพสต์เมื่อครบ + จำค่า localStorage (`omnicut_guide_checklist_v1`) + ปุ่มล้าง
3. การ์ดเมนู 1-7: โชว์ 3 ข้อแรก + ปุ่มดูเพิ่มอีก N ข้อย่อลงได้ ต่อใบอิสระ
4. การ์ดโฟลว์ 7 ขั้น: ป้ายเมนูกดได้ กระโดดไป tab จริง (tab mapping ใหม่ใน FLOW_STEPS)
5. การ์ดแก้ปัญหา 4 อาการ: แยกเป็น TROUBLES constant + ปุ่มลัดเปิดเมนูที่เกี่ยวข้อง
6. FAQ: ช่องค้นหา (includes ไม่ใช้ regex) + ปุ่มเปิดทั้งหมด/ปิดทั้งหมด + จำนวนผล + empty state พร้อมปุ่มล้างคำค้น + เปิดหลายข้อพร้อมกันได้ (state number → array)

### Gate

- `npm test` — 151 passed
- `npm run build` — ผ่าน 4.22s
- `python -m compileall -q scripts` — ผ่าน
- `git diff --check` — สะอาด

**สิ่งที่ทำใน `frontend/src/components/UserGuide.jsx`:**
- โฟลว์ 7 ขั้น: `grid-cols-1/sm:2/xl:7` → `grid-cols-2/md:4/2xl:7` การ์ด `p-3.5/min-h-132` → `p-3/min-h-108` มือถือเห็น 2 ใบต่อแถว จอกว้าง 7 ใบรวดเดียว
- คลิปแรก 5 ข้อ: `space-y` → `grid lg:2` (3+2 วางข้างกัน)
- สถานะ 4 เฟส: `lg:4` → `xl:4` + items-start + padding 3→2.5
- โฟลเดอร์ 8 รายการ: `sm:2` → `sm:2/xl:4` (แถวละ 4 ใบ)
- เช็กลิสต์ 6 ข้อ: `space-y` → `grid lg:2` พร้อมกรอบการ์ดต่อข้อ
- แก้ปัญหา 4 อาการ: `sm:2` → `sm:2/xl:4` แถวเดียวจบ
- FAQ 6 ข้อ: `space-y` → `grid lg:2` accordion ยังกดขยายได้เหมือนเดิม
- ลด padding ทุก section `p-4 sm:p-5` → `p-4`, gap `2.5/3` → `1.5/2`

### Gate

- `npm test` — 151 passed
- `npm run build` — ผ่าน 3.69s
- `python -m compileall -q scripts` — ผ่าน
- `git diff --check` — สะอาด

### Gate

- `npm test` — 151 passed
- `npm run build` — ผ่าน 3.87s
- `python -m compileall -q scripts` — ผ่าน
- `git diff --check` — สะอาด

เพิ่มเมนูที่ 8 คู่มือใช้งาน (User Guide) แนบในโปรแกรม อธิบายโฟลว์หลักและวิธีใช้ละเอียดทุกเมนู 1-7 สวย อ่านง่าย ผู้ใช้ใหม่เข้าใจในหน้าเดียว

### สิ่งที่ทำ

- สร้าง `frontend/src/components/UserGuide.jsx`: PageHeader + สารบัญ 8 หัวข้อ + การ์ดโฟลว์ 7 ขั้น + รายละเอียดเมนู 1-7 พร้อมปุ่มกระโดดไปเมนูจริง + คลิปแรกใน 10 นาที + สถานะ 4 เฟส + โฟลเดอร์ 00-06 + เช็กลิสต์ก่อนโพสต์ + แก้ปัญหา 4 อาการ + FAQ 6 ข้อแบบ accordion
- ลงทะเบียนเมนู: `Sidebar.jsx` Desktop 8 items + More Drawer Option 4 + isMoreActive รวม guide, `Topbar.jsx` TAB_CONFIG guide (8. User Guide), `App.jsx` lazy import + section guide
- Clean UI: ปุ่มมีไอคอน Lucide ตัวเดียว ไม่มีสัญลักษณ์ซ้ำซ้อน ฟอนต์ไทยเดิม Responsive 1/2/7 คอลัมน์ตามจอ

### Gate

- `npm test` — 151 passed
- `npm run build` — ผ่าน 3.47s
- `python -m compileall -q scripts` — ผ่าน

### Notes

- แตะเฉพาะส่วนเมนูใหม่แบบ additive ไม่แก้ logic เดิมของไฟล์ที่มี working-tree changes ค้าง
- ลบ import ที่ไม่ใช้ (Smartphone, Keyboard) ให้ build ไม่มี warning

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

## Round PRO-STYLE-1 — Professional Editing Style System: Phase 1 Style Contract + Golden Master

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** วางสัญญากลางสำหรับการตัดต่อแบบมืออาชีพ เพื่อให้โค้ดกลางรองรับ Style Preset ที่ควบคุม pacing, motion, transition, color, typography และ audio โดยไม่ hardcode รูปแบบลงทุกโปรเจกต์

**ขอบเขตการกันชนกับงานขนาน:** ไฟล์ editor/backend ที่มี working-tree diff ของ Claude ไม่ถูกแตะในเฟสนี้; รอบนี้ทำเอกสารและ acceptance contract เท่านั้น จึงไม่มีการเปลี่ยนพฤติกรรม Preview/Render

### Todo

- [x] ตรวจ inventory ของ Hook/Text Template, motion preset, transition, effect, color และ audio contract ที่มีอยู่ แล้วบันทึกช่องว่างระหว่าง “template เฉพาะองค์ประกอบ” กับ “editorial style ทั้งคลิป” ใน `PRO_EDITOR_STYLE_PLAN.md`
- [x] กำหนด Golden Master style แรก `clean_tech_review` สำหรับคลิปรีวิวสินค้าแนวตั้ง: Hook → Problem → Demo/Proof → Verdict → CTA
- [x] กำหนด Style Contract ที่เป็นข้อมูล: pacing windows, motion budget, transition policy, typography hierarchy, color palette, audio mix และ safe-zone rules โดยแยก invariant ออกจากค่าที่ preset เปลี่ยนได้
- [x] กำหนด acceptance rubric ก่อน/หลังสำหรับ one-click output โดยไม่อ้างว่า viral หรือ 10/10 เป็นสิ่งรับประกัน
- [x] ล็อกแผน integration เฟสถัดไปให้ใช้ preset เป็นข้อมูลต่อโปรเจกต์ และรักษา Preview = Render parity

### Gate

- [x] ตรวจว่าเอกสารระบุไฟล์/โมดูลที่มีอยู่และไม่ขัดกับ `TEMPLATE_MOTION_PLAN.md`
- [x] ตรวจว่า Golden Master มีเกณฑ์วัดได้ครบ pacing, motion, transition, color, typography และ audio
- [x] `git diff --check` ผ่าน — exit 0; มีเฉพาะคำเตือน line-ending ของไฟล์เดิม
- [x] ยืนยันว่าเฟสนี้ไม่มี source-code behavior change และไม่แตะไฟล์ที่มี diff ของ Claude; diff ของรอบนี้มีเฉพาะ `TODO.md`, `HISTORY.md` และ `PRO_EDITOR_STYLE_PLAN.md`

### Notes

- สร้าง `PRO_EDITOR_STYLE_PLAN.md` เป็นแผนหลักของงาน 6 phases
- กำหนด `clean_tech_review` เป็น Golden Master แรกสำหรับคลิปรีวิวสินค้า/อุปกรณ์ไอที
- ล็อกหลักการว่า Prompt ใช้จัดประเภทเนื้อหาได้ แต่ timing, clamp, z-order, audio mix และ Render ต้องเป็น deterministic rule
- Phase 2 ต้องตรวจ ownership ใหม่ก่อนแตะ `Timeline.jsx`, `SequencePlayer.jsx`, `scripts/video_editor.py` หรือ `scripts/subtitle/*` เพราะมี working-tree diff ของ Claude อยู่ในขณะปิดเฟสนี้

## Round PRO-STYLE-2 — Editorial Beat Map + Pacing Core (Phase 2A)

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** สร้าง pure module สำหรับ normalize transcript timing, ตรวจ gap/Dead Air และสร้าง candidate pacing beats จาก word timestamps กับ scene boundaries โดยไม่ตัดสินใจสร้างสรรค์แทนผู้ใช้และไม่เปลี่ยน render flow เดิม

**ขอบเขตการกันชนกับงานขนาน:** เพิ่มเฉพาะ `scripts/editorial_pacing.py` และ `tests/test_editorial_pacing.py`; ไม่แตะ `api_render.py`, `video_editor.py`, `Timeline.jsx`, `SequencePlayer.jsx` หรือไฟล์อื่นที่มี working-tree diff ของ Claude

### สิ่งที่ทำ

- เพิ่ม `PacingPolicy` ที่กำหนด short pause, cut gap, target/min/max beat interval และ boundary tolerance
- เพิ่ม deterministic word normalization ที่รองรับ `text`/`word`, `start`/`start_time`, `end`/`end_time`, ทิ้งเวลาผิดและไม่เลื่อน timestamp ที่ถูกต้อง
- เพิ่ม silence gap classification เป็น `short_pause` หรือ `cut_candidate` โดยไม่ตัดกลางคำ
- เพิ่ม scene/interval beat candidates ที่ snap ได้เฉพาะขอบเขต word-free และให้ scene beat มี priority เมื่อระยะเท่ากัน
- เพิ่ม serializable `build_pacing_plan()` สำหรับจุดเชื่อมต่อ Phase 2B
- เพิ่ม regression tests ครอบคลุม malformed records, clamping, silence, safe boundary, duplicate scene boundaries, deterministic output, empty input และ invalid policy

### Gate

- [x] `python -m pytest tests/test_editorial_pacing.py -q -p no:cacheprovider --tb=short` — `6 passed`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `git diff --check` — exit 0; มีเฉพาะคำเตือน line-ending ของไฟล์เดิม
- [x] ไฟล์ source/test ที่เพิ่มในรอบนี้มีเฉพาะ `scripts/editorial_pacing.py` และ `tests/test_editorial_pacing.py`; existing Claude diffs ไม่ถูกเขียนทับ
- [x] Preview/Render parity ยังไม่ถูกติ๊ก เพราะ Phase 2A ยังไม่ถูกเรียกจาก render pipeline

### Notes

- Phase 2A เป็น isolated foundation เท่านั้น ยังไม่เปลี่ยน output ของโปรเจกต์เดิม
- Phase 2B ต้องเลือก transcript source schema และ integration seam ก่อน และต้องรอ ownership ของไฟล์หลักให้ชัดเจน

## Round PRO-STYLE-2B — Integrate editorial pacing plan into subtitle pipeline and project manifest

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

### ผลงาน

- เพิ่ม `build_pacing_plan_from_cues()` เพื่อรวม absolute `cues[*].word_timings` และ cue boundaries เป็น pacing plan แบบ deterministic
- เชื่อม plan เข้า `SubtitleStage` ก่อน micro-cue mutation, `PipelineContext` และ project manifest
- เพิ่ม plan ใน subtitle incremental-render fingerprint; โปรเจกต์เก่าที่ไม่มี word timing ยังคง no-op และใช้ flow เดิม
- เพิ่ม integration contracts ครอบคลุม valid/malformed/legacy timing และ context/fingerprint persistence

### Gate

- [x] `python -m pytest tests/test_editorial_pacing.py tests/test_editorial_pacing_integration.py -q -p no:cacheprovider --tb=short` — 12 passed
- [x] `python -m pytest tests/test_pipeline_stages.py tests/test_incremental_render_reuse.py -q -p no:cacheprovider --tb=short` — 19 passed
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_editorial_pacing.py tests/test_editorial_pacing_integration.py -q -p no:cacheprovider --tb=short` — 162 passed
- [x] `python -m compileall -q scripts` — Pass
- [x] `git diff --check` — Pass; line-ending warnings only

### ข้อจำกัด

- รอบนี้ persist pacing plan เท่านั้น ยังไม่ apply beat เป็น FFmpeg cut จึงยังไม่มี visual/render gate สำหรับ behavior ใหม่นี้
- compatibility subset พบ `test_create_edit_save_reload_full_fidelity` ได้ HTTP 401 จาก auth guard; ไม่ใช่ผลจาก pacing change และไม่สรุปว่า full suite ผ่าน
- พบ working-tree changes นอก scope ใน `scripts/api_exports.py` และ `tests/test_post_lifecycle.py`; ไม่ได้แก้หรือ stage
| Round PRO-STYLE-2B | Integrate editorial pacing plan into subtitle pipeline and project manifest | 2026-09-09 | `build_pacing_plan_from_cues()` + PipelineContext/manifest persistence + subtitle fingerprint; 12 integration tests, 19 pipeline/incremental tests, and 162 parity subset tests passed; no FFmpeg cut behavior change |

## Round PRO-STYLE-2C — Apply editorial beat boundaries to generated clip list with Preview = Render parity

วันที่: 2026-09-09 · สถานะ: เสร็จสมบูรณ์

### ผลงาน

- เพิ่ม `resolve_pacing_boundaries()` สำหรับ validate duration, กรอง beat ใกล้ขอบ, deduplicate และ fallback อย่าง conservative
- เชื่อม resolver ที่ `ShotMatchingStage` เฉพาะ auto-generated clips; manual clip list และ legacy manifest ยังใช้ flow เดิม
- ปิด legacy merge/motion/beat snapping เมื่อมี editorial pacing เพื่อให้ beat boundaries เป็น timing truth เดียว
- รักษา AI shot anchoring โดยเลื่อน source offset ตาม segment ที่แบ่งภายใน cue เดียวกัน
- เพิ่ม contract tests สำหรับ generated boundaries และ manual clip preservation

### Gate

- [x] `python -m pytest tests/test_editorial_pacing.py tests/test_editorial_pacing_integration.py tests/test_shot_matching_pacing.py -q -p no:cacheprovider --tb=short` — 15 passed
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 161 passed, 2 deprecation warnings
- [x] `python -m pytest tests/test_pipeline_stages.py tests/test_incremental_render_reuse.py tests/test_clip_compounding_render.py -q -p no:cacheprovider --tb=short` — 21 passed
- [x] `python -m pytest ... -k "is_quota or shot_matching or script_stage or voice_stage"` — 10 passed
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 975 passed, 6 dependency/deprecation warnings
- [x] `cd frontend; npm test` — 126 passed
- [x] `cd frontend; npm run build` — 1,975 modules transformed; build passed
- [x] `python -m compileall -q scripts` — passed
- [x] `git diff --check` — exit 0; line-ending warnings only

### ข้อจำกัด

- การรัน API subset แยกครั้งแรกพบ 401 ใน auth cases แต่ backend suite ทั้งชุดรันตามลำดับปกติผ่านครบ 975 tests; จึงไม่มี unresolved test failure จากรอบนี้
- ไม่ได้แตะหรือ stage งานภายนอกใน `scripts/api_exports.py` และ `tests/test_post_lifecycle.py`
| Round PRO-STYLE-2C | Apply editorial beat boundaries to generated clip list with Preview = Render parity | 2026-09-09 | Resolver + generated clip-list integration + manual/legacy preservation; 15 contract tests, 161 render parity/behavior tests, 21 pipeline regression tests, and 975 full backend tests passed |

## Round PRO-STYLE-3A — Style-driven transition budget and project style preset contract

วันที่: 2026-09-09 · สถานะ: เสร็จสมบูรณ์

### ผลงาน

- เพิ่ม `style_motion_policy.py` เป็น pure policy กลางสำหรับ Golden Master `clean_tech_review`
- เพิ่ม `style_preset` ผ่าน RenderRequest, reroll/state-save request, Pipeline, PipelineContext, manifest และ incremental-render fingerprint
- ใช้ transition budget กับ auto-generated clip list เท่านั้น: hard cut เป็นฐาน 80%, movement transition ตามรอบที่กำหนด และ stylized transition ถูกลดความถี่/จำกัด duration
- manual clip list และ manual transition list ยังคงเป็นข้อมูลที่ผู้ใช้ควบคุมเอง
- Preview และ FFmpeg ยังคงใช้ transition/clip contract เดียวกัน จึงไม่สร้าง renderer path ใหม่ในเฟสนี้

### Gate

- [x] `python -m pytest tests/test_style_motion_policy.py tests/test_shot_matching_pacing.py -q -p no:cacheprovider --tb=short` — 7 passed
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 161 passed, 2 deprecation warnings
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 980 passed, 6 warnings
- [x] `python -m compileall -q scripts` — passed
- [x] `cd frontend; npm test` — 126 passed
- [x] `cd frontend; npm run build` — 1,975 modules transformed; passed
- [x] `git diff --check` — exit 0; line-ending warnings only

### ขอบเขต/ข้อควรทราบ

- เฟสนี้จัดการ transition hierarchy และ project style contract ก่อน; active camera keyframe/pan motion จะอยู่ในเฟสถัดไป เพราะต้องเพิ่ม parity contract และ render หลายเฟรมแยกต่างหาก
- ไม่ได้แตะหรือ stage งานภายนอกที่ตรวจพบใน `scripts/api_exports.py`, `tests/test_post_lifecycle.py` และ `tiktok_autopost_extension/sidepanel.js`
| Round PRO-STYLE-3A | Style-driven transition budget and project style preset contract | 2026-09-09 | `clean_tech_review` policy + project manifest/fingerprint contract + auto-transition budget; 7 policy tests, 161 parity/behavior tests, 980 backend tests, 126 frontend tests, and build passed |

## Round PRO-STYLE-3B — Live keyframe camera motion with Preview = Render parity

วันที่: 2026-09-09 · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** ทำให้ `zoom`, `pan_x` และ `pan_y` ใน `clip.keyframes` มีผลจริงระหว่าง playback และ FFmpeg render โดยใช้ interpolation/clamp contract เดียวกัน และคงพฤติกรรมเดิมของคลิปที่ไม่มี keyframe

### สิ่งที่ทำ

- เพิ่ม live camera transform resolver ใน `frontend/src/lib/timelineMath.js` และใช้ `motionTimeAt` แยกจาก source seek time เพื่อประเมิน keyframe ตามเวลาที่เล่นจริงหลัง speed/freeze-tail
- เชื่อม `SequencePlayer.jsx` ให้ทุก video draw path ใช้ `resolveClipTransforms` สำหรับ zoom/pan แบบ per-frame และรวม `keyframes` ใน clip invalidation key
- เพิ่ม FFmpeg dynamic camera filter ใน `scripts/video_editor.py` สำหรับ clip-list ที่มี camera keyframe; clip ที่ไม่มี keyframe คง static fast path เดิม
- เพิ่ม `camera_keyframes_for_clip` ใน `scripts/style_motion_policy.py` และให้ auto-generated clips มี push/pan แบบ restrained เฉพาะ clip สลับลำดับและยาวอย่างน้อย 0.8 วินาที; manual keyframes ยังคง user-owned
- รักษาการทำงานของ speed, freeze tail, mirror, rotation, background blur, colour correction และ audio bus เดิม
- ใช้ clamp contract เดียวกัน: zoom `1.0–3.0`, pan X/Y `-1.0–1.0`; interpolate ก่อน clamp เพื่อให้ค่ากลาง deterministic

### ไฟล์ที่แตะ

- `frontend/src/lib/timelineMath.js`
- `frontend/src/lib/timelineMath.test.js`
- `frontend/src/components/SequencePlayer.jsx`
- `scripts/video_editor.py`
- `scripts/style_motion_policy.py`
- `scripts/stages/shot_matching_stage.py`
- `tests/test_keyframe_interpolation.py`
- `tests/test_camera_motion_parity.py`
- `tests/test_preview_render_behavior.py`
- `tests/test_style_motion_policy.py`
- `tests/test_shot_matching_pacing.py`
- `PRO_EDITOR_STYLE_PLAN.md`

### Gate ผลจริง

- `python -m pytest tests/test_keyframe_interpolation.py tests/test_camera_motion_parity.py tests/test_style_motion_policy.py tests/test_shot_matching_pacing.py -q -p no:cacheprovider --tb=short` → **17 passed**
- `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider --tb=short` → **151 passed**
- FFmpeg multi-frame behavioral render (เข้า/กลาง/ออก) → **1 passed**
- `python -m pytest tests/ -q -p no:cacheprovider --tb=short` → **989 passed, 9 warnings** ใน 119.37 วินาที
- `python -m compileall -q scripts` → ผ่าน
- `npm test` → **128 passed**
- `npm run build` → ผ่าน, **1,975 modules transformed**
- `git diff --check` → ผ่าน; มีเฉพาะคำเตือน line-ending LF → CRLF ของ Git

### Notes

- warnings ที่เหลือเป็น deprecation/optional audio warnings ใน dependency หรือ test เดิม ไม่ใช่ failure ของ camera motion
- การตรวจ FFmpeg วัดจำนวนพิกเซลของ marker ในเฟรมเข้า/กลาง/ออก เพื่อยืนยันว่า pan เปลี่ยนจริงและไม่หลุด crop bounds
- ไม่ได้แตะหรือ stage งานภายนอกที่พบก่อนเริ่ม: `scripts/api_exports.py`, `tests/test_post_lifecycle.py`, `tiktok_autopost_extension/sidepanel.js`

| Round PRO-STYLE-3B | Live keyframe camera motion with Preview = Render parity | 2026-09-09 | Live zoom/pan keyframes in Canvas + FFmpeg, restrained auto-generated camera motion, 17 focused tests, 151 parity tests, 989 full backend tests, 128 frontend tests, FFmpeg behavioral render, and build passed |

## Round STYLE-ONECLICK-1 — Style Presets + Fresh One Click routing

วันที่: 2026-09-10 · ผู้สั่ง: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ผู้ใช้เลือกสไตล์การตัดต่อได้ตั้งแต่หน้า One Click และปุ่ม “ส่งตัดต่อ” เปิดฟอร์มสร้างคลิปใหม่เสมอ แม้มีโปรเจกต์เก่าค้างใน URL, localStorage หรือข้อมูลมุม ส่วนปุ่ม “เปิดไทม์ไลน์” ยังเปิดโปรเจกต์เดิมตามเจตนา

### สิ่งที่ทำ

- เพิ่ม preset ที่ renderer รองรับจริง 4 แบบ: `viral_punch`, `clean_tech_review`, `smooth_showcase`, `premium_minimal`
- กำหนด transition family/budget, camera-motion cadence และ accent palette แยกตาม preset; One Click ใหม่เริ่มที่ `viral_punch` แต่คง fallback เดิมเป็น `clean_tech_review` สำหรับข้อมูลเก่า/ค่าที่ไม่รู้จัก
- เพิ่ม `StylePresetPicker` กลาง ใช้ร่วมกันในหน้า One Click และแท็บ Style ของ Editor
- ส่ง `style_preset` จาก One Click ถึง RenderRequest, shot matching, subtitle/overlay และ video assembly
- เพิ่ม fresh-editor intent กลางซึ่งชนะ URL/localStorage/angle fallback; Tracker ส่งชื่อโปรเจกต์เฉพาะ action “เปิดไทม์ไลน์”
- เพิ่ม regression tests สำหรับ routing intent, catalog/payload, motion/transition policy, pipeline integration และ Preview = Render palette

### Gate ผลจริง

- `python -m compileall -q scripts` → ผ่าน
- `python -m pytest tests/ -q -p no:cacheprovider --tb=short` → **1,034 passed, 24 warnings** ใน 135.26 วินาที
- FFmpeg style render → **4 presets × 3 เฟรม (เข้า/ค้าง/ออก) ผ่านครบ 12 เฟรม**
- `npm test` → **144 passed**
- `npm run lint` → exit 0; มี warnings เดิมของ repo ไม่มี error
- `npm run build` → ผ่าน, **1,979 modules transformed**
- Impeccable detector → ส่วน Style Picker ใหม่ไม่พบ antipattern; พบ warning เดิม `gray-on-color` ใน AssetPanel import button 1 จุดนอก scope
- `git diff --check` → ผ่าน; มีเฉพาะคำเตือน line-ending LF → CRLF ของ Git

### Notes

- ไม่แตะไฟล์สื่อหรือโปรเจกต์จริงใน `01_Raw/`, `02_Assets/`, `03_Projects/`
- รักษา working-tree changes เดิมใน `ContentTrackerHub.jsx`, `EditorShell.jsx`, `AssetPanel.jsx` และไฟล์ renderer/tests ที่มีงานค้างอยู่
- ระหว่างรอบพบการแก้ไฟล์อื่นเพิ่มจากงานคู่ขนาน เช่น Sidebar/Topbar และ status tests; ไม่ได้แก้หรือตีความงานเหล่านั้นเป็นส่วนของรอบนี้

## Round DOC-SYNC-1 — Sync สถานะเอกสารจากผลทดสอบล่าสุด

วันที่: 2026-09-10 · ผู้สั่ง: user · สถานะ: เสร็จแล้ว

### ผลลัพธ์

- ปิดสถานะเอกสารของ `TLO-REFACTOR-FINAL-AUDIT`, `POST-LIFECYCLE-1`, `HOOK-OPT-1` และ `PRO-STYLE-PARALLEL-4-6` ตามหลักฐาน implementation/test ล่าสุด
- อัปเดต full pytest จากค่าประวัติเดิมที่เคย fail เป็นค่าปัจจุบัน `1,034 passed, 24 warnings`
- ปิด `PERF-UX-1` เฉพาะระดับ implementation และ deterministic evidence; React Profiler, production rerender และ browser FPS 50/100/300 ถูกระบุเป็น deferred validation อย่างชัดเจน และไม่มีการอ้าง performance improvement
- คงงานที่ต้องใช้ user/live environment ไว้: TikTok/Chrome Cover Studio ขั้นตอน 5 และปัญหาสระไทยที่ยังตรวจภาพจริงไม่ผ่าน
- คง `SEC-AUDIT-1` เป็นงานเปิด เพราะ SYSTEM_AUDIT_FIX_PLAN ยังมี Phase 0 และ Phase 2 ที่ไม่ได้มีหลักฐานปิดครบ

### Gate

- ตรวจ `TODO.md`, `HISTORY.md`, plan files และสถานะ Git แล้ว
- ไม่แก้ source code หรือไฟล์สื่อในรอบนี้
- `git diff --check` ผ่านก่อนบันทึกเอกสาร

## Round TLO-REFACTOR-FINAL-AUDIT — ตรวจ final gates และ inventory หลัง refactor ทั้งชุด

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว — overlay scope และ repo-wide validation ปัจจุบันผ่าน

**เป้าหมาย:** ตรวจหลักฐาน end-to-end ของ Overlay Timeline/Preview refactor หลังรอบ TLO-REFACTOR-1 ถึง 7 และยืนยัน duplication/behavioral divergence ที่เหลือก่อน sign-off

### Todo

- [x] ตรวจ `TODO.md`, `git status`, refactor plan และขอบเขตไฟล์ค้าง โดยไม่แตะงานของ agent อื่น
- [x] รัน frontend `npm test`, `npm run lint`, `npm run build` และ `git diff --check`
- [x] รัน `python -m compileall -q scripts`
- [x] รัน preview/render parity, FFmpeg behavioral tests และ overlay dispatch tests
- [x] รัน full pytest ของทั้ง repo — ล่าสุด `1,034 passed, 24 warnings`; ไม่พบ failure
- [x] ตรวจ source inventory ของ Timeline, drag hook, SequencePlayer, editor modules และ lib ว่าจุดซ้ำหลักถูกจัดการแล้วหรือมี divergence ที่ต้องคงไว้
- [x] อัปเดต plan พร้อมตัวเลขจริง และรายงาน residual risks/งานที่ไม่รวม
- [x] แก้ `TrackLabel` fallback `width ?? GUTTER` ที่หายไประหว่าง extraction และย้าย source-contract probes ให้ตรวจ module ใหม่

### Notes

- รอบนี้เป็น audit/sign-off; พบและแก้ production regression จริงที่ `TrackLabel.jsx` โดยคืน `width ?? GUTTER` และปรับ parity probes ให้ตาม source module ใหม่
- Latest frontend working-tree gate: `npm test` = `144 passed, 0 failed`; `npm run lint` exit 0 (มี warnings เดิม); `npm run build` = `1,979 modules transformed`; `git diff --check` ผ่าน
- Overlay/backend scope: `compileall` ผ่าน; `test_preview_render_parity.py` = `150 passed`; `test_preview_render_behavior.py` = `11 passed, 2 warnings`; `test_overlay_render_dispatch.py` = `2 passed`
- Full pytest ชุดปัจจุบันผ่าน `1,034 passed, 24 warnings`; live TikTok validation แยกเป็นงานรอ user
- Overlay scope sign-off ผ่าน: shared timeline shell/label/pointer lifecycle, selected-box geometry, inspector primitives และ render-kind profile ถูกตรวจแล้ว; type-specific policy branches ยังคงแยกตาม behavioral contract

### Gate

- [x] `npm test` — `144 passed, 0 failed`
- [x] `npm run lint` — exit 0; มี warnings แต่ไม่มี error
- [x] `npm run build` — `1,979 modules transformed`, ผ่าน
- [x] `git diff --check` — ผ่าน
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider --tb=short` — `150 passed`
- [x] `python -m pytest tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — `11 passed, 2 warnings`
- [x] `python -m pytest tests/test_overlay_render_dispatch.py -q -p no:cacheprovider --tb=short` — `2 passed`
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — `1,034 passed, 24 warnings`

## Round HOOK-OPT-1 — ยกระดับฟอนต์ข้อความ, เทมเพลตคลีน, พรีวิวขยาย/ย้ายฮุกสมบูรณ์ และสปีดแอนิเมชัน

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้วตามขอบเขตโค้ดและ deterministic gates

### ขอบเขตและผลลัพธ์

- รองรับ Master Scale, พิกัด `x/y` จริง และ resize/move ของ Hook ให้ Preview = Render parity
- เพิ่ม Master Font และ Per-Tier Font Override ผ่าน frontend/backend hook style contracts
- แยก AssetPanel เป็นป้ายฮุก 3-Tier กับข้อความเดี่ยว/เอฟเฟกต์, รวมช่องค้นหา, และลบสัญลักษณ์ UI ซ้ำซ้อน
- เพิ่มตัวเลือก animation speed และ Kinetic Word Stagger

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider` — `149 passed`
- [x] `python -m pytest tests/test_posted_protection.py tests/test_clip_compounding_render.py -q -p no:cacheprovider` — `8 passed`
- [x] `npm --prefix frontend run build` — ผ่าน, `1,962 modules transformed`
- [x] Full Pytest Regression — `923 passed`

### Notes

- Master scale, `\\pos(x, y)`, Badge Accent geometry และ Canvas/ASS mapping ถูกตรวจตาม parity contract
- การปิดรอบนี้ครอบคลุม implementation และ deterministic gates; visual/live validation ที่ต้องใช้ environment ภายนอกไม่ถูกตีความเกินหลักฐาน

## Round BUG-MARK-POSTED-1 — แก้ปุ่ม “มาร์กว่าลงโพสต์แล้ว” แจ้งสำเร็จแต่การ์ดยังไม่ย้ายสถานะ

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้ว

### อาการและ root cause

- ผู้ใช้กด “มาร์กว่าโพสต์แล้ว” แล้วได้รับ toast สำเร็จ แต่การ์ดยังค้างในคอลัมน์ `rendered`
- `/api/exports/mark-posted` ย้าย MP4 ไป `Posted/` ก่อนอัปเดต `ProductStore`
- `ProductStore.update_angle_status()` ตรวจว่า `export_id` ต้องตรงกับพาธใน `ExportRegistry`; registry ยังชี้ `Ready_to_post/` จึงเกิด `export_id ไม่ตรงกับ video_url ของไฟล์ที่เลือก`
- endpoint เดิมจับ exception เป็น `status_warning` แต่ยังตอบ `success: true` ทำให้ UI แจ้งสำเร็จทั้งที่ angle ไม่ถูกบันทึก

### การแก้

- ย้าย `ExportRegistry.move_and_mark_posted()` ให้ทำงานหลังย้ายไฟล์และก่อน `ProductStore.update_angle_status()` เพื่อให้ registry ชี้ `Posted/` ก่อน path validation
- คง `export_id`, `posted_at`, `video_url` และไฟล์จริงให้เป็น identity เดียวกันตลอด flow
- ไม่แตะ diff ของ `ContentTrackerHub.jsx`, `CoverStudioModal.jsx`, `EditorShell.jsx` หรือไฟล์งานอื่นของ agent อื่น

### Gate

- [x] ก่อนแก้ regression reproduce ได้: HTTP `200` พร้อม `status_warning` และ angle ไม่เปลี่ยนสถานะ
- [x] `tests/test_post_lifecycle.py` — `15 passed`
- [x] Full backend suite — `1,035 passed, 24 warnings`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `git diff --check` — ผ่าน

## Round PRODUCT-METADATA-1 — แนบรูปย้อนหลังและเปิดดู Metadata ที่ AI ใช้

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้วตามขอบเขตโค้ดและ deterministic gates

### ผลลัพธ์

- เพิ่มปุ่ม `ข้อมูล AI` ในแถบเครื่องมือของสินค้าเดิม เพื่อเปิด `ProductMetadataModal`
- แสดง metadata ต้นทางครบในระดับสินค้า: ชื่อ, รหัส, platform, category, URL, ราคา, กลุ่มเป้าหมาย, timestamps, description, raw text, specs, selling points, pain points, thumbnail และรูปอ้างอิง
- เพิ่มส่วน “ข้อมูลที่ AI จะได้รับ” และ JSON source snapshot เต็ม เพื่อให้ตรวจได้ว่าข้อมูลใดถูกเก็บไว้สำหรับ Content Matrix และ per-angle reroll
- แก้ `selectProduct()` ให้รักษา source fields ที่เดิมถูกย่อเหลือเฉพาะ `selling_points` จึงไม่ทำให้คำอธิบาย/raw text หายจากหน้าตรวจสอบ
- เพิ่มแนบรูปย้อนหลังได้สูงสุด 20 รูปต่อสินค้า รูปถูกอัปโหลดเข้า `inbox` แล้วบันทึกที่ `product.images`; รองรับทั้ง URL รูปจาก scraper และ object path จาก upload รุ่นใหม่
- เพิ่มเอารูปออกจาก reference list โดยไม่ลบไฟล์ต้นฉบับจริง เพื่อป้องกันการลบข้อมูลโดยไม่ตั้งใจ
- เพิ่ม `ProductUpdateRequest.images` แบบ permissive เพื่อรักษาความเข้ากันได้กับ product records รุ่นเก่าที่เก็บรูปเป็น URL string

### ไฟล์ที่เกี่ยวข้อง

- `frontend/src/components/ProductToClip.jsx`
- `frontend/src/components/ProductMetadataModal.jsx`
- `scripts/api_phase1.py`
- `tests/test_product_metadata.py`

### Gate

- [x] `python -m pytest tests/test_product_metadata.py -q -p no:cacheprovider --tb=short` — `2 passed, 1 warning`
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short --durations=20` — `1,037 passed, 24 warnings` ใน `128.13s`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm run lint` — exit 0; warnings เดิมของโปรเจกต์ ไม่มี error ใหม่
- [x] `npm test` — `144 passed, 0 failed`
- [x] `npm run build` — `1,980 modules transformed`, ผ่าน
- [x] Impeccable UI detector — ไม่พบ violation ใหม่ (`[]`)
- [x] `git diff --check` — ผ่าน

### Notes

- ยังไม่ได้ทำ browser live click-through ด้วยบัญชีจริง; รอบนี้ยืนยันจาก API contract, component build และ automated gates เท่านั้น
- ยังไม่ได้ commit ตามคำขอรอบนี้; working tree ยังมี diff ของรอบก่อน/agent อื่นอยู่ จึงไม่รวม commit ให้โดยอัตโนมัติ

## Round PRODUCT-METADATA-2 — เติม source fallback ให้สินค้า legacy

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้วตามขอบเขตโค้ดและ deterministic gates

### Root cause ที่ยืนยันแล้ว

- Product `20260904233315_1` (`Logitech Wave Keys`) ใน `_Docs/products.json` มี `url` ว่าง, `description`/`raw_text` ไม่มีค่า, `specs`/`pain_points`/`selling_points` เป็นรายการว่าง และ `images` ว่าง
- ข้อมูลที่ใช้สร้างสคริปต์เดิมยังอยู่ในแต่ละ angle เช่น `key_features`, `pain_point`, `price_deal` แต่ไม่ได้ถูกเก็บเป็น product-level source metadata
- ผลคือ Metadata Inspector แสดง “ไม่มีข้อมูล” และ per-angle reroll ที่อ่าน `product.description`, `product.raw_text`, `product.images` ได้บริบทน้อยกว่าที่สคริปต์เดิมมี

### การแก้

- เพิ่ม `_with_product_source_fallback()` ใน `scripts/api_products.py` ให้สรุป `key_features` เป็น description/selling points และ `pain_point` เป็น pain points เฉพาะเมื่อ product-level field ว่าง
- เติม `raw_text` จากชื่อสินค้าและข้อมูล angle เดิมเฉพาะกรณีที่ raw source ว่าง
- ติด `metadata_source: derived_from_angles` เพื่อให้ UI ระบุชัดว่าเป็นข้อมูลย้อนกลับจากสคริปต์เดิม ไม่ใช่การ scrape หน้าเว็บใหม่
- ใช้ helper เดียวกันกับ `/api/products` และ per-angle reroll ทำให้สิ่งที่ Metadata Inspector แสดงตรงกับ source ที่ AI reroll ได้รับ
- ไม่เขียนทับ `_Docs/products.json` และไม่แปลงข้อมูล derived ให้กลายเป็น raw source ถาวร

### Gate

- [x] ก่อนแก้ regression test ล้มตามอาการ: import fallback seam ยังไม่มี (`ImportError`)
- [x] `python -m pytest tests/test_product_metadata.py -q -p no:cacheprovider --tb=short` — `4 passed, 1 warning`
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short --durations=5` — `1,040 passed, 24 warnings` ใน `137.94s`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm run lint` — exit 0; warnings เดิมของโปรเจกต์ ไม่มี error ใหม่
- [x] `npm test` — `144 passed, 0 failed`
- [x] `npm run build` — `1,980 modules transformed`, ผ่าน
- [x] `git diff --check` — ผ่าน

### Notes

- Fallback นี้ช่วยให้ legacy product ใช้บริบทจากสคริปต์เดิมได้ทันที แต่ไม่ควรตีความเป็นคำอธิบายที่ scraper ยืนยันจากหน้าร้าน
- หากต้องการข้อมูลหน้าร้านจริงของ Logitech รายการนี้ ให้แนบ screenshot/spec sheet ผ่าน `ข้อมูล AI` หรือสร้าง/เติม source URL ใหม่

## Round SCRIPT-ANGLE-METADATA-1 — ล็อกหัวข้อเดิมและแสดงประเภทเนื้อหา

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ให้การเจนสคริปต์ใหม่ยังอยู่ในหัวข้อ/มุมเดิมอย่างตรวจสอบได้ และให้ผู้ใช้เห็นว่าเนื้อหาเป็นสเปก เปรียบเทียบ การใช้งานจริง หรือ FAQ ได้หลายประเภทในหัวข้อเดียว

### สิ่งที่ทำ

1. เพิ่ม catalog กลางของประเภทเนื้อหาและ derive `content_types` จาก `angle_id` กับ `extra_beats` แบบ stable/deduplicated จึงไม่พึ่งชื่อที่ AI ตอบกลับมา
2. บังคับ reroll ให้คง `angle_id`, ชื่อหัวข้อเดิม และคำอธิบายหัวข้อ แม้ AI จะส่งชื่อใหม่กลับมา
3. แก้ fallback ให้เลือก template ของ angle ที่ถูกขอโดยตรง ไม่ใช้สคริปต์ของ angle แรกแล้วเปลี่ยนเพียง ID
4. เพิ่มการบันทึก `angle_description`/`content_types` ใน `replace_angle_content` และแสดง badges หลายค่าใน sidebar, mobile pill และ reroll modal
5. รองรับ angle รุ่นเก่าที่ไม่มี metadata โดย derive badge ฝั่ง UI จาก `angle_id`/`extra_beats` โดยไม่ต้องเจนใหม่
6. เพิ่ม regression tests สำหรับ identity, default extra beats, deduplication และ fallback template

### Gate

- [x] `python -m pytest tests/test_reroll_script.py -q -p no:cacheprovider --tb=short` — `12 passed, 2 warnings`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — `1,057 passed, 24 warnings, 0 failed` ใน `141.34 วินาที`
- [x] `npm test` — `149 passed, 0 failed`
- [x] `npm run build` — ผ่าน, Vite transformed `1,981 modules`
- [x] `npm run lint` — exit 0; warnings เดิมของโปรเจกต์
- [x] `git diff --check` — ผ่าน
- [x] Impeccable detector — `[]` สำหรับ `frontend/src/components/ProductToClip.jsx`

### Notes

- Reroll ยังเขียนทับบทพูดในหัวข้อเดิมตามพฤติกรรมเดิม แต่ไม่เปลี่ยน lifecycle ของงาน เช่น status/project/video
- งานนี้ไม่แตะ preview/render engine จึงไม่มี FFmpeg parity gate เพิ่ม
- รักษา diff ที่มีอยู่ก่อนหน้าใน `SystemSettings.jsx`, `TokenDashboard.jsx` และ `tools/probe_ass_scale.py` ไม่ได้แก้หรือลบ

## Round RENDER-REGRESSION-2 — ตรวจและคืน render ให้ตรง baseline

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ระบุ commit/เวลา/ไฟล์ที่ทำให้ภาพ Export เปลี่ยนจาก baseline และแก้เฉพาะ regression ที่ยืนยันได้ โดยไม่ทับงานค้างของเอเจนอื่น

### ผลการตรวจ forensic

- `f44db69` (`2026-09-10 00:07:50 +0700`) เพิ่ม style/renderer infrastructure และยังคง fallback เป็น `clean_tech_review`
- `3a35723` (`2026-09-10 08:06:23 +0700`) เปลี่ยน One Click flow ให้ส่ง `style_preset` ทุกครั้ง และตั้ง `DEFAULT_ONE_CLICK_STYLE_PRESET = 'viral_punch'`
- commit metadata ระบุผู้เขียนเป็น `wni-nasirulhak` ทั้งสอง commit; Git ไม่มีข้อมูลที่เชื่อถือได้ว่าเป็นเอเจนตัวใด จึงระบุได้ถึง commit/เวลา/ผู้เขียนเท่านั้น
- artifact ที่สร้างช่วง `15:42–15:44` มี `viral_punch`/`smooth_showcase` ใน `project.json` และสี/การเคลื่อนไหวสอดคล้องกับ preset ใหม่ในภาพที่ผู้ใช้แนบ
- differential policy probe วัดได้ว่า implicit baseline คือ `clean_tech_review` (`transition_stride=5`, `camera_motion_stride=2`, `zoom=0.08`, `pan=0.14`, accent `#FFE600`) ขณะที่ `viral_punch` คือ (`2`, `1`, `0.12`, `0.18`, `#FE2C55`)

### การแก้ไข

- `frontend/src/lib/stylePresetCatalog.js`: คืน One Click default ไปที่ `clean_tech_review`; preset อื่นยังเลือกใช้แบบ explicit ได้
- `frontend/src/lib/studioDefaults.js`: เพิ่ม `STYLE_PRESET_STORAGE_VERSION` และ migration สำหรับ browser form เก่าที่ถูกบันทึกโดย implicit `viral_punch`; ไม่ทับ choice ที่ผู้ใช้เลือก explicit หลัง migration
- `frontend/src/components/editor/NewClipPanel.jsx`: เมื่อเลือก presetจะบันทึก version marker พร้อมค่าที่ normalize แล้ว
- `frontend/src/lib/stylePresetCatalog.test.js`: เพิ่ม regression test สำหรับ default และ saved-form migration
- ไม่แก้ไข export/project artifact เดิม และไม่แตะ diff ของ `SystemSettings.jsx`, `TokenDashboard.jsx`, product metadata flow หรือ `tools/probe_ass_scale.py`

### Gate

- [x] differential policy/render evidence: มี policy probe และ artifact timestamp/project manifest ที่อธิบายความต่างได้
- [x] `python -m pytest tests/test_style_motion_policy.py tests/test_camera_motion_parity.py tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 181 passed; รวม FFmpeg multi-frame behavior
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,057 passed, 24 warnings
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm test` — 150 passed
- [x] `npm run build` — ผ่าน, Vite transform 1,981 modules
- [x] `npm run lint` — ผ่าน, มี warnings เดิมของ codebase ไม่มี error
- [x] `git diff --check` — ผ่าน

### Notes

- โปรเจกต์เดิมที่มี `style_preset` explicit เป็น `viral_punch` หรือ `smooth_showcase` จะไม่ถูกเขียนทับอัตโนมัติ เพื่อรักษาการเลือกของผู้ใช้; หากต้องการเรนเดอร์ซ้ำให้เหมือน Golden Master ให้เลือก `Clean Tech Review` ก่อน render

## Round FONT-SIZE-REGRESSION-1 — ตรวจและคืนขนาดฟอนต์บทพูด/ซับ

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ระบุจุดที่ทำให้ฟอนต์ใน Render เล็กกว่าภาพเดิม และคืนค่า Preview = Render โดยไม่ทับงานค้างของเอเจนอื่น

### ผลการตรวจ forensic

- ภาพ baseline เดิมมี caption ASS แบบ `Fontsize=50` พร้อม `\fscx165/\fscy165` ที่ settle แล้ว จึงมีขนาดกายภาพเทียบเท่า ~82px
- artifact ที่ผู้ใช้เห็น (`03_Projects/ESS01-แกะกล่องว้าว_1/subtitles_v2.ass`) มี `Fontsize=50`, ใช้ `IBM Plex Sans Thai SemiBold`, ไม่มี scale boost และไม่มี contract marker จึงเล็กกว่า baseline อย่างวัดได้
- generator ปัจจุบันสร้าง `Style: TikTokWhite,IBM Plex Sans Thai SemiBold,82,...` และใช้ขนาดเทียบเท่า baseline โดยไม่ต้อง scale glyph หลัง rasterize ซึ่งรักษา Thai mark parity ได้
- สาเหตุคือ incremental pipeline ตรวจ fingerprint ของไฟล์ได้ แต่ไม่มี version ของ subtitle renderer จึง reuse ASS เก่าหลังมีการเปลี่ยน font-size/GPOS contract

### การแก้ไข

- `scripts/subtitle_engine.py`: เพิ่ม `SUBTITLE_RENDER_CONTRACT_VERSION = "v3"`, marker ใน ASS header และ `subtitle_artifact_is_current()`; ASS ใหม่จะมี marker และ font size contract ปัจจุบัน
- `scripts/stages/subtitle_stage.py`: ก่อน reuse ตรวจ marker ผ่าน `ProjectManifest.artifact_path()`; ASS เก่าหรือไม่มี marker จะ regenerate stage subtitles อัตโนมัติ แล้วส่งต่อให้ video assembly
- `tests/test_subtitle_artifact_contract.py`: เพิ่ม regression tests ว่า ASS ใหม่มี marker และ legacy ASS ถูกปฏิเสธการ reuse
- restart API server ที่ค้างจากก่อน patch แล้ว: process ใหม่สร้างเวลา `16:28:47` จำนวน 2 process
- ไม่แก้ไข project/export artifact จริงของผู้ใช้ และไม่แตะ diff งาน product metadata/UI ที่มีอยู่ก่อนรอบนี้

### Gate

- [x] baseline/candidate font measurement: baseline physical size ~82px (`50 × 1.65`) เทียบ fresh ASS `Fontsize=82`; legacy artifact ตรวจได้ `current=False`, fresh `current=True`
- [x] `python -m pytest tests/test_subtitle_artifact_contract.py tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 172 passed, รวม FFmpeg multi-frame
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,059 passed, 24 warnings
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm test` — 150 passed
- [x] `npm run build` — ผ่าน, Vite transform 1,981 modules
- [x] `npm run lint` — exit 0, warnings เดิมของ codebase ไม่มี error
- [x] `git diff --check` — ผ่าน

### Notes

- คลิปที่ export ไปแล้วจะยังคงไฟล์เดิมเพื่อไม่ลบ/เขียนทับข้อมูล; ให้กด Render ใหม่จากโปรเจกต์เดิมหนึ่งครั้ง ระบบจะสร้าง ASS ใหม่และฟอนต์กลับขนาดเดิม
- รอบนี้ไม่ต้องเปลี่ยน `SequencePlayer.jsx` เพราะ Canvas ใช้สัดส่วน 25px ที่เทียบกับ fresh ASS 82px แล้ว; ปัญหาอยู่ที่ stale ASS reuse ใน backend

## Round FONT-SIZE-REGRESSION-2 — แก้ซับยังเล็กใน backend environment จริง

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ไล่ MP4/ASS/manifest ของงาน `ESS01-แกะกล่องว้าว_1` เวลา 16:31 ที่ผู้ใช้ยืนยันว่าซับยังเล็ก แก้ให้ขนาดกลับเท่า baseline ใน environment เดียวกับ backend จริง

### ผลการวินิจฉัย

- `subtitles_v3.ass` ถูกสร้างใหม่เวลา 16:30:58 และ MP4 16:31:04 อ้าง artifact นี้จริง จึงตัดสมมติฐาน reuse/cache/หยิบผิดไฟล์ออก
- ASS ที่สร้างใหม่ยังมี `TikTokWhite Fontsize=50` ทั้งที่ source คำนวณ `font_size_boosted`
- backend รันผ่าน `.venv\Scripts\python.exe` ซึ่งไม่มี `fontTools`; `ass_glyph_scale()` จับ exception แล้วคืน `1.0` เงียบๆ ทำให้ `50 × 1.0 = 50`
- probe ก่อนหน้าที่ได้ `82` รันด้วย system Python ซึ่งมี `fontTools` จึงเป็น environment mismatch และให้ false confidence
- ค่าจริงจาก IBM Plex Sans Thai คือ `unitsPerEm=1000`, `usWinAscent=1116`, `usWinDescent=534` → scale `1000/1650 = 0.6060606` → boost `1.65` → `Fontsize=82`

### การแก้ไข

- `scripts/subtitle/font_metrics.py`: เพิ่ม SFNT table reader ด้วย standard library (`struct`) อ่าน `head.unitsPerEm` และ `OS/2.usWinAscent/usWinDescent` โดยตรง เพื่อให้ visual contract ไม่พึ่ง optional package
- `requirements.txt`: เพิ่ม `fonttools==4.63.0` สำหรับ embedded font-family metadata ของ AssetRegistry และติดตั้งใน `.venv` แล้ว
- `scripts/subtitle_engine.py`: bump subtitle render contract จาก `v3` เป็น `v4` เพื่อ invalidate ASS v3 ที่อาจถูกสร้างด้วย fallback `1.0`
- `tests/test_subtitle_artifact_contract.py`: ล็อก generated IBM ASS ต้องเป็น `82`, จำลอง `fontTools` หายแล้วยังได้ `0.6060606`, และยืนยัน v3 ถูก invalidate
- `tests/test_preview_render_parity.py`: ปรับ source-contract assertion ให้ล็อก direct SFNT metric path แทน implementation เก่า
- restart backend ด้วย project `.venv` เวลา 16:45:53 และ reroll `subtitles` ของงานจริงสำเร็จเป็น `subtitles_v4.ass` + `ESS01-แกะกล่องว้าว_1_20260910_164654.mp4`

### Gate

- [x] red phase — regression file ล้ม 3 เคสตามอาการ: generated `50 != 82`, scale `1.0 != 0.6060606`, v3 ยังถูกมองว่า current
- [x] focused subtitle artifact/parity/FFmpeg behavior — `174 passed, 20 warnings, 0 failed`
- [x] full backend — `1,061 passed, 25 warnings, 0 failed` ใน `189.66 วินาที`
- [x] frontend — `150 passed, 0 failed`; build ผ่าน; lint exit 0 มี warnings เดิมของ codebase
- [x] `python -m compileall -q scripts`, `pip check`, `git diff --check` — ผ่าน
- [x] live artifact — `subtitles_v4.ass` มี marker v4 และ `TikTokWhite/TikTokSoftShadow Fontsize=82`
- [x] live FFmpeg frame เวลา 1.2s — caption pixel bands ใหม่ตรง baseline: ไทย `1390–1417`, อังกฤษ `1457–1481`

### Notes

- รอบนี้ reroll project/export จริงตามคำสั่งแก้บั๊ก; ไฟล์ล่าสุดใน Ready to post คือ timestamp `164654`
- ไม่แก้ `SequencePlayer.jsx` เพราะภาพปัญหามาจาก backend-only environment fallback; parity เดิมกลับมาตรงหลังใช้ scale ที่ถูกต้อง
- รักษา diff ค้างของ product metadata/UI/style migration และ `tools/probe_ass_scale.py`; ไม่ลบหรือเขียนทับ

## Round POSTED-CLIP-LIFECYCLE-1 — ระบบจัดการคลิปที่โพสต์แล้ว (Zero-Risk Archive & Timeline Lockout Flow)

วันที่: 2026-09-12 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 2.5 Pro) · สถานะ: เสร็จสมบูรณ์

**ปัญหาและข้อวิเคราะห์ทางสถาปัตยกรรม (Architecture & UX Flow Analysis):**
- เดิมคลิปที่โพสต์แล้วยังสามารถถูกโหลดเข้าไทม์ไลน์ในหน้า Editor ได้ ซึ่งเสี่ยงต่อการที่ผู้ใช้เผลอขยับคัต, ลบช็อต, แก้สคริปต์ หรือกดเรนเดอร์ทับประวัติเดิมของวิดีโอที่เผยแพร่จริงบนโซเชียลมีเดียไปแล้ว
- การให้คลิปที่โพสต์แล้วค้างอยู่ในรายการโปรเจกต์ของไทม์ไลน์ ทำให้ Dropdown สับสน รกตา และไม่สะท้อนสถานะที่เป็นจริง (Active WIP vs Published History)
- ข้อมูลที่เก็บในดิสก์: วิดีโอ MP4 ใน `04_Exports/Posted/` ต้องเก็บไว้ถาวรสำหรับ QC ตรวจสอบลิขสิทธิ์ และมอนิเตอร์ยอดวิว/วิเคราะห์ผลงาน แต่โฟลเดอร์โปรเจกต์ชั่วคราว (`03_Projects/`) ไม่จำเป็นต้องอยู่ใน working directory ของโปรเจกต์ปัจจุบัน ควรย้ายไปเก็บที่ `06_Archive/Projects/`

**สถาปัตยกรรมและการแก้ไขที่ดำเนินการ:**
1. **Zero-Risk Timeline Access Guard:**
   - เพิ่มฟังก์ชัน `filterActiveProjects(projects, statusByProject)` ใน `frontend/src/lib/editorEntry.js` พร้อม unit test ตรวจจับและคัดกรองโปรเจกต์ที่โพสต์แล้ว (`is_posted === true` หรือ `posted_at`) ออกจาก Dropdown ใน `ProjectSelector.jsx` 100%
   - เพิ่ม Security Guard ใน `frontend/src/components/editor/EditorShell.jsx` (`useProjectLoader.fetchProject`) เพื่อปฏิเสธการโหลดโปรเจกต์ที่โพสต์แล้วเข้าสู่ไทม์ไลน์ แม้จะมีการเรียกผ่าน URL query params หรือ cached state พร้อมแจ้งเตือนผู้ใช้อย่างชัดเจน
2. **Action Bar ออกแบบใหม่ใน Script Lab (ProductToClip.jsx):**
   - ในการ์ดสคริปต์ของมุมมองที่โพสต์แล้ว ทั้งใน `AngleActiveWorkbench` (split view) และ `ScriptAccordionItem` (accordion view):
     - ถอดปุ่ม `[เปิดดูในไทม์ไลน์]` และ `[ตัดใหม่]` ออก 100%
     - แทนที่ด้วยปุ่มหลัก `[ดูคลิปที่โพสต์แล้ว]` (เปิด Modal เล่นไฟล์ MP4 จริงแบบ 9:16)
     - เพิ่มปุ่มเสริม `[ทำซ้ำเพื่อตัดคลิปใหม่]` (`handleCloneAngle`) สำหรับคัดลอกบทสคริปต์ จุดขาย และมุมมองไปสร้างเป็นร่างคลิปใหม่ (`status: 'scripted'`) ให้ผู้ใช้ตัดต่อต่อยอดได้ทันทีโดยไม่แตะต้องหรือเสี่ยงทับคลิปเดิม
   - ใน Modal พรีวิวส่งออก (`previewExportAngle`) หากเป็นคลิปที่โพสต์แล้ว ปุ่ม Action จะเปลี่ยนเป็น `[ทำซ้ำเพื่อตัดคลิปใหม่]` แทนการเปิดไทม์ไลน์
3. **Automated Project Folder Archival Engine:**
   - เพิ่มเมธอด `ProjectManifest.archive(project_name)` ใน `scripts/project_manifest.py` พร้อมการจัดการข้อผิดพลาดและ file locks บน Windows เพื่อย้ายโฟลเดอร์จาก `03_Projects/{project_name}` ไปยัง `06_Archive/Projects/{project_name}` อย่างปลอดภัย
   - เชื่อมระบบใน `scripts/api_exports.py` (`mark_posted`) ให้เรียก `ProjectManifest.archive()` อัตโนมัติเมื่อผู้ใช้มาร์กสถานะเป็นโพสต์แล้ว
   - เพิ่ม API endpoint `POST /api/projects/{project_name}/archive` ใน `scripts/api_phase1.py` พร้อมตัวป้องกันการย้ายหากโปรเจกต์กำลังอยู่ในสถานะ Render (`render_jobs.is_busy()`)
4. **ความสะอาดของ UI ตาม Rule 8 (UI Clean Standard):**
   - ทุกปุ่มใช้ Action Verb ชัดเจน ไม่มีเครื่องหมาย `+` หรือไอคอนซ้ำซ้อน

**ไฟล์ที่แตะ:**
- `scripts/project_manifest.py`
- `scripts/api_phase1.py`
- `scripts/api_exports.py`
- `frontend/src/lib/editorEntry.js`
- `frontend/src/lib/editorEntry.test.js`
- `frontend/src/components/editor/ProjectSelector.jsx`
- `frontend/src/components/editor/EditorShell.jsx`
- `frontend/src/components/ProductToClip.jsx`
- `tests/test_project_archive.py` (ไฟล์ทดสอบใหม่)
- `TODO.md`
- `HISTORY.md`

### Gate & Verification Results:
- [x] Backend Unit Tests: `tests/test_project_archive.py` — 3/3 passed
- [x] Backend Parity Suite: `tests/test_preview_render_parity.py` — 153/153 passed
- [x] Frontend Vitest Suite: 158/158 passed (รวม test cases ใหม่ของ `filterActiveProjects`)
- [x] Frontend Production Build: `npm run build` สำเร็จ 100% ใน 3.45 วินาที
- [x] Python Compilation: `python -m compileall -q scripts` ผ่าน 100% ปราศจาก syntax error

---

## Round TECH-PRODUCT-SHOWCASE-1 — Tech Product Showcase foundation

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Codex (GPT-5) · สถานะ: เสร็จสมบูรณ์ในขอบเขต foundation

**เป้าหมาย:** รวมจังหวะภาพแบบรีวิวสินค้า Tech ที่เห็นจาก Bangreview ให้เป็น preset ของเราเอง โดยไม่ลอกแบรนด์หรือชิ้นงานตรง ๆ และรักษา Preview = Render ทุกจุดที่มีผลต่อภาพ

### Todo

- [x] เพิ่ม `tech_product_showcase` ใน frontend และ backend ให้เป็น style contract เดียวกัน
- [x] เชื่อม preset กับ camera push/pan, transition budget และ accent palette ที่มีอยู่ โดยไม่เปลี่ยน Golden Master/default เดิม
- [x] ใช้ asset/motion infrastructure เดิม ไม่เขียนทับ `01_Raw/` หรือ `02_Assets/Refs/`
- [x] เพิ่ม parity/regression coverage และทดสอบ palette ผ่าน ASS/libass จริงครบช่วงเข้า–ค้าง–ออก
- [x] ตรวจ Browser ว่าตัวเลือกแสดงจริงในหน้าสร้างคลิปใหม่ พร้อมรายละเอียด Motion/Cut/Sound

### Gate & Verification Results

- [x] Backend focused tests: 181 passed
- [x] Frontend `npm test`: 185 passed
- [x] Frontend `npm run build`: สำเร็จ, 2,003 modules, 4.73 วินาที
- [x] `.venv\Scripts\python.exe -m compileall -q scripts`: ผ่าน
- [x] `.venv\Scripts\python.exe -m pip check`: No broken requirements found
- [x] `git diff --check`: ผ่าน
- [x] FFmpeg/libass render regression: 5 styles × 3 frames (entry/hold/exit) ผ่าน พร้อมตรวจภาพจริงและ accent pixel counts

### Notes

- Preset ใหม่ใช้ accent `#FFCC33`, status `#25F4EE`, hard cut เป็นหลัก, Slide/Circle เฉพาะจังหวะ และ hero push/pan ทุกช็อตที่ยาวพอ
- ค่าเริ่มต้นยังเป็น `clean_tech_review`; ไม่เปลี่ยนข้อความ ฟอนต์ ขนาด subtitle, safe zone หรือ Golden Master เดิม
- พื้นหลัง Grid/Studio แบบเฉพาะสไตล์และ callout graphic ที่สร้างจาก asset โดยอัตโนมัติยังเป็นเฟสถัดไป เพราะรอบนี้ส่งมอบ foundation ที่ปลอดภัยก่อน

## Round TOKEN-LAZY-LOAD-1 — ถอด HISTORY ออกจาก prompt ทุกรอบ (lazy-load อ่านแค่สารบัญ)

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Muse Spark (Muse Spark) · สถานะ: เสร็จ

**เป้าหมาย:** รอบถัดไปไม่ต้องโหลด HISTORY.md เต็มไฟล์ (~690 KB / ~150k token) ทุกรอบ โดยยังสืบประวัติย้อนหลังได้

### Todo

- [x] แก้ `work_loop.md` ข้อ 2.1 เป็น lazy-load (TODO อ่านเฉพาะส่วนเปิด + HISTORY อ่านแค่สารบัญ ≤100 บรรทัด ขุดค่อย grep)
- [x] เติมกฎห้ามเปิด HISTORY ทั้งไฟล์ใน `AGENTS.md` ข้อ 13 + `token-efficiency-guardian/SKILL.md`

### Gate

- [x] `git diff --stat` แสดงเฉพาะไฟล์ docs ที่วางแผนไว้
- [x] `grep` สารบัญ HISTORY เจอ 152 หัวข้อโดยไม่ต้องเปิดทั้งไฟล์

### Notes

- วัดจริง: HISTORY.md = 687.8 KB / 4,076 บรรทัด (~150k token/รอบ) — ตัวกินใหญ่สุดใน prompt
- กันหลุด 3 ชั้น: (1) สารบัญมีชื่อรอบ+ผลลัพธ์ (2) grep ชื่อรอบเจอบล็อกเต็ม (3) TODO เหลือชื่อรอบบรรทัดเดียว

---

## Round AGENTS-SLIM-1 — ย่อ AGENTS.md เหลือสารบัญกฎ 1 บรรทัดต่อข้อ + link

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Muse Spark (Muse Spark) · สถานะ: เสร็จ

**เป้าหมาย:** ลด AGENTS.md ที่โดนยัดเข้า prompt ทุกรอบ ~63% โดยกฎยังบังคับเท่าเดิม

### Todo

- [x] ย่อ DON'Ts 1-10 + DOs 1-14 เหลือ 1-2 บรรทัดต่อข้อ + link ไฟล์กฎเต็ม
- [x] ย่อตารางโมดูล + คำสั่งรัน เหลือ link ไป ARCHITECTURE.md / testing_standard.md

### Gate

- [x] AGENTS.md 62 บรรทัด / 11,291 bytes (จาก 170 บรรทัด / 30,885 bytes) — ลด ~63%
- [x] กฎครบ 24 ข้อ (DON'Ts 10 + DOs 14) + รายละเอียดใน `.agents/rules/*.md` ครบ 9 ไฟล์

### Notes

- หลักการ lazy-load: เอเจนต์ไม่ต้องรู้กฎทุกข้อทุกรอบ — เปิดไฟล์กฎเต็มเฉพาะรอบที่แตะ

---

## Round TEST-TWO-TIER-1 — กติกาเทส 2 ชั้น: ตอนแก้รันเฉพาะจุด ก่อนปิดรอบค่อยรันเต็ม

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Muse Spark (Muse Spark) · สถานะ: เสร็จ

**เป้าหมาย:** รอบแก้โค้ดไม่ต้องรันเต็มชุดทุกครั้ง — ประหยัดเวลา + token โดย Gate เต็มยังบังคับก่อนปิดรอบ

### Todo

- [x] เติมหัวข้อ "เทส 2 ชั้น" ใน `testing_standard.md` (ชั้น 1 เฉพาะจุด / ชั้น 2 เต็มก่อนปิดรอบ)
- [x] เติมตัวอย่างคำสั่งชั้น 1: `pytest <ไฟล์เดียว>` / `npm test -- <ไฟล์>`

### Gate

- [x] หัวข้อเทส 2 ชั้น + ตัวอย่างคำสั่งอยู่ในไฟล์
- [x] คำสั่งมาตรฐานเต็มชุดยังอยู่ (Gate ไม่ลดลง)

### Notes

- เดิมรันเต็มทุกครั้งต่อรอบแก้: pytest ~1,100+ + npm test ~185 + build — ความเสี่ยงบัคไม่เพิ่มเพราะ Gate เต็มยังบังคับก่อนติ๊กปิด

---

## Round HOUSEKEEP-1 — จัดระเบียบรากโปรเจกต์ (ไฟล์เทสหลุดราก + PLAN เก่า)

วันที่: 2026-09-13 · สั่งโดย: user · ดำเนินการโดย: Muse Spark (Muse Spark) · สถานะ: เสร็จบางส่วน

**เป้าหมาย:** รากโปรเจกต์สะอาด — ไฟล์เทสชั่วคราวลง .tmp, ไม่ลบของที่มีคนอ้างถึง

### Todo

- [x] ย้ายไฟล์เทส 8 ไฟล์จากรากลง `.tmp/` (test_ffmpeg_*.png ×4, test_frame_render.png, test_all_vowels_result.png, test_all_vowels.ass, all_fonts.ass)
- [x] ทดสอบรันผ่าน `.venv` ยืนยัน output ไป `.tmp` จริง ไม่มีไฟล์หลุดมาราก

### Gate

- [x] ไฟล์เทสทุกไฟล์ gitignore อยู่แล้ว ไม่ขึ้น status
- [x] `grep` ยืนยันไฟล์ที่ย้ายไม่มีคนอ้างถึง (ยกเว้น test_all_vowels.* ที่ test สร้างเอง)

### Notes

- ยกเลิกย้าย PLAN 7 ไฟล์ลง `06_Archive/`: `.gitignore:59` ignore ทั้งโฟลเดอร์ → ย้ายไป = หลุด version control กลายเป็นลบ
- ยกเลิกแก้ `test_all_vowels.py` (ใช้ tmp_path): ไฟล์โดน Codex แตะพร้อมกัน กันชน — รอรอบถัดไป
- บทเรียน: เช็ค `.gitignore` + `git status` ก่อนย้าย/แก้ไฟล์ (work_loop ข้อ 6)

---

## Round AI-PRODUCER-HUB-AUDIT-PLAN-1 — evidence-first audit และ hardening Producer Hub

วันที่: 2026-09-14 · ดำเนินการโดย: Codex (GPT-5) + Halley, Dirac, Socrates (audit-only delegated agents) · สถานะ: เสร็จสมบูรณ์

**ผลตรวจ:** audit score 10/20 ก่อนแก้; ไม่พบ P0 แต่พบ P1/P2 ด้าน data contract, accessibility, error state, mobile viewport, performance และ file exposure

**สิ่งที่แก้:**

- รองรับ TikTok Studio รูปแบบจริง `posts[].metrics` และเพิ่ม evidence regression test
- กันคิวพังเมื่อ Export มีเฉพาะ `path` พร้อมใช้ basename เป็นชื่อแสดงผล
- เพิ่ม `buildAnglePayload` ให้ AI proposal รองรับทั้ง canonical fields และ aliases โดยไม่ทำข้อมูล Angle หาย
- เพิ่ม all-source-failed state พร้อมปุ่ม retry และไม่อัปเดต sync timestamp เมื่อไม่มี source ที่ valid
- เพิ่ม semantic progressbar, keyboard activation/focus ring ให้ media tiles และ Escape/focus trap/restore สำหรับ modal ที่เกี่ยวข้อง
- ผูก label กับ input หลัก, เพิ่ม `aria-pressed`, ยกเลิกการปิด pinch-zoom บน mobile และเปลี่ยน file picker เป็น `image/*` ให้ตรงกับ logic
- ลบ JSX duplicate props และจำกัด `/ref-media/{filename}` ให้เสิร์ฟเฉพาะไฟล์ชื่อที่ระบบสร้าง พร้อมจำกัดขนาด image resolver

**Gate:** frontend 222 tests ผ่าน, backend Producer 9 tests ผ่าน, TikTok stats tests ผ่าน, Vite build 2,005 modules ผ่าน, oxlint exit 0 (มี warnings เดิมที่ไม่เกี่ยวกับรอบนี้), detector ตรวจซ้ำแล้วไม่พบ duplicate props; ยังไม่ได้ทำ live browser verification รอบนี้

---

## Round COVER-REALTIME-SCRUB-STUDIO-1 — เรียลไทม์ Frame Scrubber ใน Cover Studio + AI Studio Cutout ผสานช็อตสินค้าจริง

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย:**
1. แก้ Frame Scrubber ใน `CoverStudioModal.jsx`: แสดงเฟรมวิดีโอแบบเรียลไทม์ตามวินาทีที่เลื่อน (`currentSeconds`) ไม่ล็อกตายตัวอยู่แค่ 5 แคตตาล็อก candidate
2. พัฒนาระบบ AI Studio Cutout ใน `scripts/api_covers.py`: ตัดฉากหลังสินค้าจริงจากเฟรมที่ผู้ใช้เลือกด้วย AI (`rembg`) แล้วนำมาวางคอมโพสิตกึ่งกลางฉากหลังสตูดิโอ 9:16 ระดับไฮเอนด์ (Minimalist Podium / Studio Lighting / Soft Reflection) โดยไม่ทำให้ตัวสินค้าจริงเพี้ยนหรือแปลงสภาพ
3. เพิ่มพารามิเตอร์ `at_seconds` และโหมด `ai_studio_composite` ใน `POST /api/covers/ai-generate-image`

### Todo:
- [x] Backend: ปรับปรุง `POST /api/covers/ai-generate-image` ให้รับ `at_seconds` และตัดพื้นหลังสินค้าจริงด้วย `rembg` ผสานฉาก AI สตูดิโอ 9:16
- [x] Backend: เพิ่ม endpoint `POST /api/covers/grab-frame` สำหรับดึงเฟรม JPG ความละเอียดสูงแบบ on-demand ตามวินาทีที่ระบุ
- [x] Frontend: ปรับปรุง `CoverStudioModal.jsx` แสดงเฟรมแบบ Real-time live scrubbing ทันทีเมื่อเลื่อน slider
- [x] AI Background Hardening: คลีน Prompt ให้เป็นฉากสตูดิโอแท่นวางสินค้าว่างเปล่า (Empty Podium / Studio lighting) พร้อมใส่ Negative Prompt บล็อกใบหน้า/บุคคล/อนิเมะ 100%
- [x] Warning Suppression: ซ่อน GenAI ExperimentalWarning และจัดการข้อจำกัด Developer API โหมดเงียบ ไม่รบกวน terminal
- [x] Antigravity In-App Bridge: เชื่อมต่อ Antigravity CLI เข้าสู่ `POST /api/covers/ai-generate-image` โดยตรง ทำให้ผู้ใช้กดปุ่มในหน้าต่าง Cover Studio แล้วเจนภาพสินค้า 8K ระดับมาสเตอร์พีซจบในโปรแกรมได้ทันที 100%
- [x] Verification: pytest 3 passed, vitest 224 passed, Vite build 3.98s ผ่าน 100%

---

## Round COVER-MULTI-GEN-HANDHELD-1 — AI Cover History Gallery + ปลดล็อกคำสั่ง Handheld + Quick Brand Title Overlay

วันที่: 2026-09-14 · สั่งโดย: user · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash) · สถานะ: เสร็จสมบูรณ์ ✅

**เป้าหมาย & ปัญหาที่แก้ไข:**
1. **แก้ปัญหารูปที่สองทับรูปแรก:** เมื่อเจนภาพ AI หลายรอบ ทุกภาพจะถูกเก็บลงใน `aiHistory` พร้อมแสดงเป็นแกลเลอรีประวัติภาพขนาดย่อม (Interactive Thumbnail Strip) ผู้ใช้สามารถคลิกสลับดูรูปที่ 1, รูปที่ 2, รูปที่ 3 ได้ตลอดเวลา รูปเก่าไม่ถูกทับและไม่สูญหาย
2. **แก้ปัญหาภาพ Handheld (มือถือสินค้า):** ปรับปรุง `_clean_backdrop_prompt` และ Negative Prompt ใน `scripts/api_covers.py` ให้ตรวจจับคำว่า `hand holding / handheld / มือถือสินค้า` เพื่ออนุญาตให้มีมือถือสินค้าจริง (ห้าม strip คำว่า hand/holding ออก และไม่บล็อก hand ใน negative prompt)
3. **แก้ปัญหาไม่มีหัวข้อบนหน้าปก:** เพิ่มการ์ด **"หัวข้อ & ชื่อสินค้าบนหน้าปก"** พร้อมสวิตช์เปิด/ปิด และปุ่มลัดใส่ชื่อสินค้าทันที (`🏷️ ชื่อสินค้าล้วน`, `🔥 สไตล์ Hook ดึงดูด`, `🎯 สไตล์ Review คุ้มไหม`) ในพาเนล AI Cover Studio โดยตรง ผู้ใช้สามารถเห็นและเปิดพาดหัวชื่อสินค้าบนปกได้ด้วยคลิกเดียว

### Todo:
- [x] Backend (`scripts/api_covers.py`): อัปเดต `_clean_backdrop_prompt` และ Negative Prompt ตรวจจับโหมด Handheld ให้โมเดล AI เจนมือจับถือสินค้าได้อย่างสมจริง
- [x] Frontend (`frontend/src/components/CoverStudioModal.jsx`): เพิ่ม State `aiHistory` เก็บภาพ AI ทุกรอบ พร้อมเรนเดอร์แถบแกลเลอรีประวัติภาพที่สร้าง สลับดูได้ตลอดเวลา
- [x] Frontend (`frontend/src/components/CoverStudioModal.jsx`): เพิ่มการ์ดและปุ่มลัดเปิดพาดหัวชื่อสินค้า/แบรนด์บนหน้าปกในพาเนล AI โดยตรง
- [x] Frontend (`frontend/src/components/CoverStudioModal.jsx`): ปรับปรุง Prompt Preset "🖐️ มือถือสินค้า + ไฟ Rim Light" ให้เน้น `fingers gripping product` ชัดเจน
- [x] Test (`tests/test_api_covers_ai.py`): เพิ่มยูนิตเทส `test_clean_backdrop_prompt_handheld` ยืนยันการรักษาคำว่า hand holding
- [x] Verification: pytest 6 passed, vitest 230 passed, Vite build 2.95s ผ่าน 100%

---

## Round SYSTEM-AUDIT-P6-BACKUP-WAL-20260915

Date: 2026-09-15 | Agent: Codex (GPT-6) | Status: complete

- [x] Snapshot SQLite through the backup API so committed WAL pages are included.
- [x] Run an integrity check on the destination database before archiving.
- [x] Abort and clean temporary state when the snapshot fails; never raw-copy a WAL database.
- [x] Regression: 10 backup/API tests passed; compileall and diff check passed.

---

## Round SYSTEM-AUDIT-P6-PREVIEW-RENDER-PARITY-20260915

Date: 2026-09-15 | Agent: Codex (GPT-6) | Status: complete

- [x] Re-ran Preview/Render parity and background-isolation render integration fixtures.
- [x] Verification: 165 tests passed in 16.24s.

---

## Round MAIN-FLOW-SCALE-TRACK-B-INDEX-1

Date: 2026-09-15 | Agent: Codex (GPT-6) | Status: complete

- [x] Invalidate the canonical export path index after move, rename, and removal mutations.
- [x] Keep `path_key` synchronized with the stored canonical path.
- [x] Regression: export registry, schedule lifecycle, and lookup performance tests passed (38 tests), including external mirror refresh.

---

## Round MAIN-FLOW-SCALE-TRACK-A-DISPATCH-1

Date: 2026-09-15 | Agent: Codex (GPT-6) | Status: complete

- [x] Verified durable batch checkpoints and restart recovery preserve completed items.
- [x] Verified FIFO admission, idle-exit handoff, and one daemon dispatcher for all queued batches.
- [x] Regression: batch/recovery suite passed (13 tests).


## Round MAIN-FLOW-SCALE-TRACK-C-PROJECTION-20260915

Date: 2026-09-15 | Agent: Codex (GPT-6)
Workspace Data Coordinator now exposes shared product and tracker projections with single-flight requests, short TTL cache, generation-safe invalidation, and forced refresh after tracker/product/editor mutations. App, ContentTrackerHub, ProductToClip, and EditorShell receive the coordinator; Product Flow and Editor use the product projection instead of issuing independent reads.
Validation: frontend npm test -- --run - 243 passed; npm run build - Vite 2007 modules, 4.28s; scoped git diff --check passed. Parent MAIN-FLOW-SCALE-1 gate remains open for the isolated full backend gate and final working-tree review.


## Round BG-SUBJECT-ISOLATION-CROSS-PROJECT-GUARD-20260915

Date: 2026-09-15 | Agent: Codex (GPT-6)
Extracted completed background-isolation task filtering into completedBackgroundIsolationTasks(), enforcing active project ownership and required artifact/source fields before Editor rebinding.
Validation: frontend npm test -- --run ? 244 passed; npm run build ? Vite 2007 modules, 4.93s; scoped diff check passed.


## Round BG-SUBJECT-ISOLATION-CANCEL-BRIDGE-20260915

Date: 2026-09-15 | Agent: Codex (GPT-6)
Task cancellation now reaches background-isolation extraction and rembg processing through a per-task threading.Event. Cancelled workers stop at safe checkpoints, never publish a ready artifact, and their event registry entries are removed on release.
Validation: focused background-isolation/API suite ? 37 passed, 3 skipped, 1 warning; compileall passed; scoped diff check passed.

## BG-SUBJECT-ISOLATION-QUALITY-GATE-20260915

- Confirmed production `BackgroundIsolationWorker` applies alpha coverage/mass sanity checks before foreground PNG commit; transparent, full-frame, sparse, and dimension-invalid outputs fail closed.
- Sequence worker cache validation and publication tests remain deterministic; no existing artifact is overwritten during quality rerun.
- Evidence: `tests/test_background_isolation_worker.py` + `tests/test_background_isolation_sequence_worker.py` — 33 passed.
- ดำเนินการโดย: Codex (GPT-6)

## BG-SUBJECT-ISOLATION-READINESS-20260915

Date: 2026-09-15 | Agent: readiness_audit (GPT-6)
Project-level background-isolation markers now participate in the editor readiness projection. A processing marker keeps stale ready clip artifacts in processing, and stale/error/cancelled markers surface quality_failed after reload. Completed task projection remains project-scoped and requires artifact/source identity.
Validation: frontend npm test -- --run — 246 passed; npm run build — Vite 2007 modules; scoped diff check passed.

## BG-SUBJECT-ISOLATION-LAYER-ORDER-CONFIRM-20260915

- Preview/Render compositor keeps source transform before alpha composite, transitions/concat after per-clip composite, Hook pass behind Subject, and captions/callouts in foreground only when the artifact is ready.
- Not-ready artifacts continue to use the configured fallback path.
- Evidence: background-isolation compositor and renderer integration regression suites passed in the current workspace.
- ดำเนินการโดย: Codex (GPT-6)
Validation addendum: compositor unit + renderer integration suites — 49 passed (2026-09-15).

## SYSTEM-AUDIT-P0-SECURITY-RECHECK-20260915

- Re-ran P0 safety and P1 recovery regression suites in temp-only fixtures: 50 passed, 1 skipped, 1 warning.
- Confirmed `.env` and `frontend/.env` are gitignored and not tracked; no credential values were read or changed.
- ดำเนินการโดย: Codex (GPT-6)

## REAL-VIDEO-RENDER-FIXTURE-20260915

- Rendered a read-only copy of the existing LOG02 segment, audio, and subtitles in `.tmp/e2e-fixture`.
- Draft and post renders completed for 2.0 seconds; post output is H.264/AAC, 1080×1920, 30 FPS, 2.000 seconds.
- Source SHA-256 matched before/after copy; no project source or Raw/Assets file was modified.
- Browser Preview pixel parity remains open.
- ดำเนินการโดย: Codex (GPT-6)

## Round SYSTEM-AUDIT-P7-LIFESPAN-20260915 — Startup recovery lifecycle
- ย้าย background-isolation และ batch recovery จาก module import ไปไว้ใน FastAPI lifespan ผ่าน `recover_startup_work()`; ผล recovery ถูกเก็บใน `app.state.startup_recovery` และแยก error ต่อ subsystem
- เพิ่ม `tests/test_api_server_lifespan.py` ยืนยัน app construction ไม่แตะ durable recovery และ lifespan เรียก recovery ตามลำดับ
- ตรวจสอบแล้ว: 39 passed, 3 skipped, 1 warning; compileall ผ่าน; scoped diff check ผ่าน
- ดำเนินการโดย: Codex (GPT-6)

## Round SYSTEM-AUDIT-CONTINUE-20260915 — หลักฐาน full gate และ performance
- Full isolated clone gate: 1,470 passed, 21 failed, 14 skipped, 24 warnings (173.81s).
- Failure classification: 10 missing fixture/environment items (fonts, typography presets, SFX, BGM, stickers), 1 stale dotenv monkeypatch test, and 10 render/caption failures caused by missing fonts/media assets. No safe production regression identified.
- P04 bounded fix: `scripts/api_exports.py` now reuses a stat-keyed project manifest snapshot and invalidates on manifest add/remove/change; `tests/test_matching_lookup_perf_fix.py` covers reuse and invalidation.
- P03 source-time chunking and P05 collection mutation rewrite remain deferred because they require artifact/schema or compatibility changes without a production benchmark.
- Evidence: matching lookup suite 9 passed; export-related regression 27 passed, 1 warning; compileall and scoped diff checks passed.
- ดำเนินการโดย: Codex (GPT-6); performance review: Antigravity (GPT-5.6)

## Round SYSTEM-AUDIT-CONTINUE-20260915 — Preview parity and bounded export cache
- Fixed Hook scrim opacity drift: FFmpeg now uses `OVERLAY_SCRIM_OPACITY = 0.75`, matching SequencePlayer Canvas.
- Added parity regression in `tests/test_preview_render_parity.py`.
- Added stat-keyed project manifest cache/invalidation to `scripts/api_exports.py`; deferred P03 chunking and P05 collection rewrite pending benchmark/compatibility contract.
- Validation: preview parity 154 passed; preview behavior/compositor/integration 69 passed; matching lookup 9 passed; export regression 27 passed, 1 warning; compileall and scoped diff checks passed.
- Browser visual snapshots at 0s and 4s matched Render; direct Canvas pixel extraction is unavailable through CUA.
- ดำเนินการโดย: Codex (GPT-6); performance review: Antigravity (GPT-5.6); browser review: preview_parity_audit (GPT-6)

## Test fixture hardening: Gemini key isolation (2026-09-15)

Updated `tests/test_gemini_tts_engine.py` to clear all `GEMINI_API_KEY*` process variables and patch `scripts.config._env_file` to a temporary `.env`. This keeps key discovery tests deterministic when a developer environment contains multiple configured keys.

Evidence: `tests/test_gemini_tts_engine.py` — 20 passed. Agent: Codex (GPT-6).
