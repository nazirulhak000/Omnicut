# 📱 แผน Mobile-First End-to-End — OmniCut Pro Studio

- **วันที่:** 2026-10-30 · **สถานะ:** รอเจ้าของอนุมัติ (ยังไม่แตะโค้ด)
- **ดำเนินการโดย:** Claude Code (Claude Opus 5.5) + 10 เอเจนต์ตรวจแบบ read-only (Plan agents)
- **ฐานโค้ด:** `main` @ `8238fc8` (pull แล้ว: Already up to date)
- **รอบงาน:** `CLAUDE-MOBILE-FIRST-E2E-UX-AUDIT-AND-PLAN-20261030`
- **Jev (ก่อนเริ่มงาน):** `split_axis` = journey, confidence 1.0 · `touches_protected_data` noul 0.14, confidence null → escalate ตามกฎ. ไม่ได้ตัดสินแทนเงียบ ๆ: ผู้ใช้สั่ง "ตรวจสอบได้เลย" และทุกเอเจนต์เป็นแบบอ่านอย่างเดียว (ผล Jev ไม่ใช่หลักฐานหรือการอนุมัติ)
- **ข้อจำกัด:** เอเจนต์ #1 (การเข้าแอป/Auth/PWA) ชนโควตา API กลางทาง ส่วนที่ขาดถูกตรวจซ้ำจากเอเจนต์ #2/#6/#8/#10 แล้ว และช่องโหว่ความปลอดภัยใน §3 ผู้ประสานงานยืนยันจากโค้ดเอง

---

## 0. TL;DR

1. **ต้องแก้ความปลอดภัยก่อนทุกอย่าง (P0):** repo เป็น **public** และมี Cloudflare tunnel token เขียนค่าจริงไว้ใน `scripts/build_colab_notebook.py:50`. บน Colab ไม่มี auth เลย (`scripts/api_server.py:244-249`). path ที่ไม่ขึ้นต้นด้วย `/api` ข้าม gate ไป (`api_server.py:286`) และ ttyd เปิดแบบเขียนได้ (`-W ... || bash`, `build_colab_notebook.py:220`) ผลคือใครมี URL ก็ได้ shell
2. **วันนี้ทำงานหลักบนมือถือแทบไม่ได้:** คะแนนเฉลี่ย 2.8/10. โหมดมือถือ (`MobileQuickStudio`) ผูกกับ pipeline ฟุตเทจแบบเก่า ส่วน **Couple Paper Chat ซึ่งเป็นงานหลัก ทำบนมือถือไม่ได้เลย** เพราะทุกขั้นอยู่ในสคริปต์ CLI แยกตามสินค้า 17 ไฟล์ (ประมาณ 12k บรรทัด ซ้ำกัน 92–97%) ที่ต้องสั่งผ่าน AI agent/terminal
3. **โครงที่เสนอ:** ทำให้มือถือเป็นแค่ "รีโมต + ห้องอนุมัติ" ส่วนงานหนักให้เซิร์ฟเวอร์ทำต่อเนื่องเอง ถึงจะล็อกจอหรือสลับแอปก็ไม่หลุด
   - หน้าจอมือถือ 5 แท็บ: **วันนี้ · สร้าง · ตรวจ · โพสต์ · อื่นๆ**
   - ฝั่ง backend เพิ่ม `couple_jobs` (job ที่ทนทาน + จุดอนุมัติ + SSE) แทนสคริปต์ CLI
4. **เป้าหมาย:** แชร์ลิงก์ TikTok Shop แล้วได้ 20 คลิปเข้าคิวโพสต์ โดยแตะประมาณ 60 ครั้งตลอดทั้งชุด ผู้ใช้ไม่ต้องพิมพ์คำสั่ง และไม่ต้องเปิดคอม (ยกเว้นถ้าเลือกใช้ autopost extension)
5. **ลำดับทำ:** Phase 0 Security → 1 Foundation → 2 Engine → 3 Intake/Script → 4 Review → 5 Library/Notify → 6 Post → 7 AI Command Center (→ 8 Upload/Gadget lane ถ้ายังใช้) **รวมประมาณ 45–55 วันทำงาน** ถ้าทำ Phase 0–2 + 6 ก่อน (ประมาณ 20 วัน) ก็ใช้ end-to-end บนมือถือได้จริงแล้ว

---

## 1. คะแนนความพร้อมรายส่วน (10 เอเจนต์)

| # | ส่วนที่ตรวจ | คะแนน | สิ่งที่ขวางใหญ่สุด |
|---|---|---|---|
| 1 | การเข้าแอป / Auth / PWA / เครือข่าย | 3/10 | ไม่มี auth บน Colab/tunnel; ถ้าเปิด `OMNICUT_API_KEY` แอปจะพังเพราะไม่มีหน้า login; ไม่มี service worker และไม่มีจอบอกว่า "เซิร์ฟเวอร์หลับ" |
| 2 | โครงแอป / การนำทาง / ชิ้น UI กลาง | 4/10 | ไม่มีการใช้ `pushState`/`popstate` เลย (back = ออกจากแอป); โหมดมือถืออยู่นอก `TaskProvider` และเป็นทางตัน |
| 3 | MobileQuickStudio เทียบแผนเก่า 4 ฉบับ | 3/10 | ผูกกับ `TikTokAutoCutterPipeline` ที่ต้องมีฟุตเทจ; ใน 10 ขั้นของ journey มี 8 ขั้นที่ต้องไปทำในโหมดคอมหรือให้ agent ทำ |
| 4 | นำเข้าสินค้า + สคริปต์ | 2/10 | สร้าง/แก้/อนุมัติบท couple 20 บทในแอปไม่ได้; ข้อมูลแยก 2 ที่ (`_Docs/*_20_scripts.json` กับ ProductStore) |
| 5 | Production engine | 2/10 | ไม่มี orchestrator หรือ endpoint ที่สั่ง couple pipeline; มีแต่ CLI แยกตามสินค้า |
| 6 | ถ่าย / อัปโหลดสื่อ | 4/10 | POST ก้อนเดียว ไม่แบ่ง chunk และ resume ไม่ได้; timeout 60s; ไฟล์ที่ใหญ่กว่าประมาณ 100MB ผ่าน tunnel ไม่ได้ |
| 7 | พรีวิว / ตรวจ / แก้บนจอสัมผัส | 2/10 | Studio ผูก `localhost:3002`; Visual Gate (กฎ 22) มีแค่ CLI และเขียนผลลง `.tmp` |
| 8 | เรนเดอร์ / งาน / ปก / ดาวน์โหลด | 3/10 | batch 20 คลิปทำแค่ `print()` ไม่มีสถานะในระบบ; render เป็น sync HTTP สูงสุด 300s; ปกจากทางลัดไม่ bind |
| 9 | ตั้งเวลา / โพสต์ / Tracker / สถิติ | 3/10 | โพสต์จริงต้องใช้ Chrome extension ที่ผูก `127.0.0.1:8000`; QR ชี้ LAN:5173; ไม่มี "คลิปถัดไป" |
| 10 | AGY Terminal / Copilot / Settings | 2/10 | ได้ root shell สาธารณะ; terminal สูงแค่ 150px ไม่มีปุ่ม Esc/Ctrl; Copilot ใส่เสียง sine tone แล้วส่งลง Ready_to_post |

**ของดีที่มีอยู่แล้วและควรใช้ต่อ:**
- `media_service.py:146-231` รองรับ Range/206 (เล่นวิดีโอบน iOS ได้)
- `DocumentTable` บน SQLite WAL (`db.py:321`) และ `BatchRenderManager` มี startup recovery
- `TaskManager` (`api_tasks.py:18-66`), `proxy_manager` ทำ proxy 540p, endpoint `grab-frame` (`api_covers.py:1263`)
- `posting_jobs.py` รองรับหลักฐานแบบ `manual_user_confirmation` แล้ว
- ใน MQS: wake lock, poll retry, ปุ่มยกเลิก; `ActivityDrawer` ใช้ `dvh`; bottom bar 5 ช่อง; กฎ input 16px (ใช้เฉพาะ ≤768px)

---

## 2. รากปัญหา 8 ข้อ (รวมจากทุกส่วน)

| R | รากปัญหา | หลักฐานหลัก | ส่วนที่ได้รับผล |
|---|---|---|---|
| R1 | **ระบบเปิดสาธารณะ** ไม่มี auth / token อยู่ใน repo public / shell ผ่านเว็บ | `api_server.py:244-249,286`; `build_colab_notebook.py:50,209,220`; `gh repo view` → PUBLIC | ทุกส่วน |
| R2 | **โหมดมือถือเป็นเลนฟุตเทจแบบเก่า** ไม่รองรับ Couple Paper Chat | `MobileQuickStudio.jsx:393,1071`; `mobile_quick_studio.py:526-527,668`; `api_mobile_studio.py:123-128` | 3,4,5,7 |
| R3 | **ไม่มี orchestrator ฝั่งเซิร์ฟเวอร์** pipeline เป็นสคริปต์ CLI 17 ไฟล์ แก้ทีละสินค้า | `tools/batch_produce_ttz_k106_20.py:974-1000`; `batch_produce_couple_canonical.py:768-940`; `tools/batch_render_*_20.py` | 4,5,7,8,10 |
| R4 | **งานยาวผูกกับ HTTP แบบ sync** (render ≤300s, quick-add, agent chat) เจอ Cloudflare ตัดที่ประมาณ 100s และ axios 60s; ฝั่ง client ไม่ resync | `api_hyperframes.py:513,541,603`; `api.js:9,616-641`; `TaskContext.jsx:245-251` | 3,5,7,8,10 |
| R5 | **ไม่มีชั้นการนำทางบนมือถือ:** back = ออกจากแอป; โหมดมือถือไม่มีเมนูและอยู่นอก `TaskProvider`; สถานะเก็บใน sessionStorage | `App.jsx:127-140,507-523`; `channelRuntime.js:12`; `MobileQuickStudio.jsx:370-387` | 2,3,8,9,10 |
| R6 | **ข้อมูลแยกหลายที่ + ไม่ทนทาน:** สคริปต์อยู่ใน JSON กับ store; tools เขียน registry ตรงโดยไม่มี lock ร่วม; Colab ไม่ mount Drive และสั่ง `git reset --hard` ทุกครั้งที่บูต | `sync_scripts_to_products.py:276-283`; `batch_render_redmi_buds8_20.py:163-282`; `db.py:25-37,343`; `.gitignore:98` | 4,5,8 |
| R7 | **ปลายทางผูกเดสก์ท็อป:** extension ผูก `127.0.0.1:8000`; QR/ลิงก์ใช้ `https://<LAN-IP>:5173`; ลิงก์ Studio ชี้ localhost | `background.js:31`; `api_render.py:456`; `ExportGallery.jsx:1646`; `ContentTrackerHub.jsx:539,724,902,985` | 6,7,8,9 |
| R8 | **ชิ้น UI ไม่รองรับการแตะ:** `Button` สูง 28–36px, ปุ่มปิด Modal 32px, input 12px, `h-screen`, เนื้อหาที่ต้อง hover 41 จุด, `text-[8–11px]` 1,183 จุด | `ui/Button.jsx:20-25`; `ui/Modal.jsx:41,52,72`; `index.css:43,54-65`; `App.jsx:487-530` | ทุกส่วน |

### 2.1 จุดที่ผิดกฎโปรเจกต์ซึ่งเจอระหว่างตรวจ (แก้ใน Phase 0)

| กฎ | สิ่งที่เจอ | หลักฐาน |
|---|---|---|
| ห้ามแสดงราคาในคลิป (memory + rule) | prompt/เทมเพลตยังชวนใส่ราคา: "พิกัดราคาโปรโมชั่น"; หน้า Gallery แสดง `price_deal`; dead code `ScriptLab.jsx` มี "149 บาท" | `product_scraper.py:1136,1149,1174,1207,1345,1385`; `ai_bridge.py:237`; `mobile_quick_studio.py:424-429`; `MobileQuickStudio.jsx:1426`; `ExportGallery.jsx:819-822,2243-2246`; `ScriptLab.jsx:15,37` |
| ข้อ 11 ห้ามคลิปทดสอบ/ขยะใน `Ready_to_post` | Copilot build/render ใส่เสียง sine 440/220Hz แล้วมาร์กว่า Rendered ลง Ready_to_post | `copilot_engine.py:564-638`; `api_copilot.py:161,193-211` |
| ข้อ 8 สถานะต้องตรงความจริง | Settings แสดง "เชื่อมต่อแล้ว", "1,500 req/day" ตายตัว; mark-posted ใช้ `scheduled_at` ในอนาคตเป็น posted_at; ป้าย "สคริปต์พร้อม" ติดให้ทุกบทอัตโนมัติ | `SystemSettings.jsx:397-407,446,818-823`; `api_exports.py:910-926`; `sync_scripts_to_products.py:246` |
| ข้อ 1/13 ห้ามทับ 01_Raw / ห้ามไฟล์ซ้ำ | finalize ของ Guided Take ใช้ `ffmpeg -y` เขียนลง `01_Raw` ตรงและไม่ idempotent; `/api/upload` ไม่ dedupe | `recording_sessions.py:278-317`; `api_videos.py:511-517` |
| ข้อ 22 Visual Gate | probe อ่าน `window.CTA_T`/`window.tl` ที่ไม่มีอยู่จริง จึงเสี่ยงได้ PASS หลอก; Whisper gate ไม่เคย fail | `probe_visual_gate.py:73-76` เทียบ `batch_produce_couple_canonical.py:412-450`; `batch_produce_ttz_k106_20.py:323-328`; `batch_produce_hatari_20.py:178-185` |
| ข้อ 20 โมเดล TTS | ทุกสคริปต์ fallback ไป `gemini-2.5-flash-preview-tts` ซึ่งอยู่นอก allowlist | `batch_produce_ttz_k106_20.py:125`; `batch_produce_hatari_20.py:106` |
| AGENTS ข้อ 1–4 ต้องยืนยันก่อนทำลาย | AGY มี chip `!rm -rf 01_Raw/test_protect`; ปุ่ม Git pull ไม่มี confirm; tool call ของ agent ไม่ต้องอนุมัติ; denylist หลบได้ | `api_agy.py:502,531,754`; `agy_cloud_agent.py:47-58,118-124,865-892` |

---

## 3. North Star — การใช้งานบนมือถือที่ต้องการ

**หน้าจอมือถือ (แทน MQS แบบเดิม):** bottom nav 5 ช่อง มีทั้งไอคอนและข้อความ ขนาด ≥48px เผื่อ `safe-area`

| แท็บ | หน้าที่ |
|---|---|
| **วันนี้** | การ์ดงานที่กำลังรัน (x/20, ETA), "ต้องทำ" (สคริปต์รออนุมัติ / คลิปรอตรวจ / ถึงเวลาโพสต์), สถานะระบบ (Colab/GPU/คีย์) |
| **สร้าง** | วาง/แชร์ลิงก์ → ยืนยันสินค้า → สร้าง 20 สคริปต์ → swipe อนุมัติ → "ผลิต 20 คลิป" |
| **ตรวจ** | Review Queue: การ์ดภาพแชท + ภาพ CTA ต่อคลิป, พรีวิว proxy 540p, ปุ่ม ผ่าน / ตีกลับ / แก้เบา |
| **โพสต์** | การ์ด "คลิปถัดไป" → แชร์เข้า TikTok → checklist ปักตะกร้า → ยืนยัน → คลิปถัดไป, agenda 7 วัน |
| **อื่นๆ** | คลังคลิป, ปก, สถิติ, สั่งงาน AI (Command Center), Terminal (power mode), ตั้งค่า, สลับไป "โหมดเต็ม" |

**ลำดับการใช้งาน 1 สินค้า (เป้าหมาย):**

| ขั้น | ผู้ใช้ทำ | ระบบทำ | แตะ |
|---|---|---|---|
| 1 | เปิด PWA จากหน้าโฮม (ล็อกอินครั้งแรกครั้งเดียว, cookie จำ 30 วัน) | เปิดแท็บ "วันนี้" + resync งานค้าง | 1 |
| 2 | ในแอป TikTok กด Share → OmniCut (Android `share_target`) / iOS กด "วางลิงก์" หรือใช้ Shortcut | `intake/parse` แยก URL ออกจากข้อความ, resolve `vt.tiktok`, กันสินค้าซ้ำด้วย product ID | 2–3 |
| 3 | ยืนยันข้อมูลสินค้า + ติดดาวรูป hero (ไม่แสดงราคา) → "สร้าง 20 สคริปต์" | job สร้างบท couple (5 หมวด × 4 บท) + ตรวจกฎ (ไม่มี …, ไม่มีราคา, ทับศัพท์ถูก) | 3 |
| 4 | Swipe อนุมัติ 20 บท (หรือ "อนุมัติทุกบทที่ผ่านกฎ") | บันทึก `script_review` + revision | ≤40 |
| 5 | กด "ผลิต 20 คลิป" | `couple_jobs`: TTS → split → whisper → compose → snapshot คลิปแรก → รออนุมัติ | 1 |
| 6 | แจ้งเตือน LINE "คลิปแรกพร้อมตรวจ" → การ์ดตรวจ → ผ่าน | render pool (local 4 workers) → enhance → ปก → registry | 2–3 |
| 7 | ตรวจที่เหลือแบบการ์ด (อนุมัติเฉพาะใบที่เลื่อนผ่านตาแล้ว) | ใบที่ตีกลับ → แก้เบา → เรนเดอร์ใหม่ 1 คลิป | 5–10 |
| 8 | เมื่อถึงรอบ: "โพสต์" → แชร์ → ปักตะกร้า → ยืนยัน | `mobile-post/handoff` → `confirm` (manual evidence) → คลิปถัดไป | 4–5 ต่อคลิป |

---

## 4. สถาปัตยกรรมเป้าหมาย

### 4.1 Backend (ใหม่ / แก้)

| โมดูล | หน้าที่ | อ้างอิงของเดิม |
|---|---|---|
| `scripts/auth.py` + pure-ASGI middleware | cookie session (HttpOnly, Secure, SameSite=Strict) ครอบ**ทุก path รวม WebSocket** + ตรวจ Origin; ยังรับ X-API-Key/service token ให้ extension | ลบ bypass `api_server.py:244-249`, `build_colab_notebook.py:209` |
| `scripts/couple_engine/{tts,audio,verify,compose,inspect,render,finalize}.py` | รวมสคริปต์ CLI ตระกูล single-take เป็นชุดเดียวที่รับพารามิเตอร์ได้; ข้อมูลรายสินค้าอยู่ที่ `_Docs/couple_products/{CODE}.json` | `batch_produce_ttz_k106_20.py`, `batch_produce_couple_canonical.py:498-940` |
| `scripts/couple_jobs.py` + `api_couple_production.py` (`/api/couple`) | job model ที่ทนทาน (`DocumentTable("couple_jobs")` + events แบบ append-only), state machine `queued→running→awaiting_approval→paused_quota→…`, recovery, idempotency, SSE (`Last-Event-ID`, heartbeat 15s) + polling fallback | `batch_render.py:164-225`, `hyperframes_render.py:65-127,261-267` |
| `scripts/api_intake.py` | `parse` / `preview` (async, ถ้าเรียกจาก remote คืน `needs_manual` แทนการเปิดเบราว์เซอร์มีหน้าต่าง) / `commit` (กันซ้ำด้วย ID, ไม่ทับ angles) | `api_products.py:75-114`, `product_scraper.py:652-685` |
| `scripts/couple_script_generator.py` + `script_rules.py` (คู่กับ `lib/scriptRules.js`) | สร้าง 20 บทเป็น task async + lint ร่วมกันทั้ง BE/FE + `POST /api/scripts/lint` | few-shot `_Docs/ttz_k106_20_scripts.json`, `.agents/skills/couple/SKILL.md` |
| ProductStore (ขยาย) | `angles[].format="couple_v1"`, `turns[{speaker, phrases[{display, spoken}], photo}]`, `script_review{state,at,note}`, `revision` (409 เมื่อชนกัน), export กลับเป็นไฟล์ JSON เดิมเพื่อให้ batch เก่ายังใช้ได้ | `product_store.py:283-288,808,1054-1116` |
| `scripts/api_review.py` | `GET /queue`, `POST /{cid}/snapshots` (job), `POST /{cid}/decision`, `PATCH /{cid}/script` (แก้ display, เปลี่ยนรูป, ขยับเวลา ±0.1s); ภาพเก็บที่ `03_Projects/.cache/review/` | `api_covers.py:1263-1296`, `api_videos.py:1369-1370` |
| `/api/hyperframes/render` แบบ async | คืน 202 + task_id ผ่าน `TaskManager.run_in_background` (quick win) | `api_hyperframes.py:512-608` |
| `scripts/api_mobile_posting.py` | `GET /schedule-queue/next-due`, `POST /mobile-post/handoff` (claim `phone:<device>` → `awaiting_post`), `/confirm` (`manual_user_confirmation`, posted_at = เวลาจริง), `/abandon` | `posting_jobs.py:58-62,170-175`, `api_tiktok_autopost.py:529-635` |
| `scripts/notifier.py` | push LINE Messaging API (รวมเป็น 1 ข้อความต่อ batch, แจ้ง fail ไม่เกิน 1 ครั้งต่อ 10 นาที) + deep link | ใหม่ |
| `scripts/api_uploads.py` | upload แบบ chunk ต่อได้ (8 MiB, offset) → ตรวจ magic + SHA-256 dedupe → staging → publish (ไม่เขียน `01_Raw` ตรง) | `asset_dedup.py`, `upload_storage.py` |
| `media_service.py` | `?download=1` → Content-Disposition, ETag, Cache-Control; `GZipMiddleware` + `immutable` สำหรับ `/assets` | `media_service.py:146-235`, `api_server.py:385-403` |
| `/api/system/health`, `/api/couple/preflight` | สถานะ GPU, ทดลอง encode NVENC จริง, เวอร์ชัน hf/node, whisper cache, จำนวนคีย์และโควตาที่ประเมินไว้ | ใหม่ |
| `/api/command/*` | intents → plan (ไม่มี side-effect, ใช้ function-calling แบบ closed schema) → jobs (ต้องมี `confirm_token` สำหรับงานทำลาย มิฉะนั้นตอบ 409) | reuse `agy_cloud_agent.py:718-770` |

### 4.2 Frontend (ใหม่ / แก้)

- `frontend/src/components/mobile/`: `MobileShell.jsx` (5 แท็บ อยู่ใน `TaskProvider`), `TodayScreen`, `IntakeScreen`, `ScriptReviewDeck`, `ProductionJobCard`, `ReviewQueue`/`ReviewSheet`, `MobileClipLibrary`, `CoverSheet`, `MobilePostNext`, `CommandCenter`, `UploadTray`
- `lib/appNav.js` (`?tab=` + `pushState` / `popstate`), hook `useBackToClose(open,onClose)`, `lib/saveToDevice.js` (โหลดแบบ Range เป็น chunk แล้วเรียก `navigator.share` เป็นคำสั่งแรกใน handler), `lib/uploadQueue.js` (IndexedDB + backoff), `lazyWithRetry`
- **ชิ้น UI กลาง:** `Button` `max-md:min-h-11`; `Modal` เป็น bottom sheet เมื่อจอ <640px + ปุ่มปิด 44px + ปิดด้วย back; `Toast` ใช้ `inset-x-3` ลอยเหนือ `--nav-h`; เปลี่ยน `h-screen` เป็น `h-dvh`; `--nav-h: calc(56px + env(safe-area-inset-bottom))`
- **การเก็บสถานะ:** channel + workflow ย้ายไป localStorage; ใส่ task id ใน URL; `visibilitychange`/`pageshow`/`online` → resync ทันที และหยุด poll ตอนแอปถูกซ่อน
- **ห้ามแตะ:** `SequencePlayer.jsx` (ถ้าจำเป็นต้องแก้คู่กับ `scripts/subtitle_engine.py` + `tests/test_preview_render_parity.py`), ภาพ/ฟอนต์/ซับของคลิป, ดีไซน์ปก (rule 23)

---

## 5. Roadmap

> Effort: S < 0.5 วัน · M 1–2 วัน · L 3 วันขึ้นไป · AC = เกณฑ์ผ่าน (ทดสอบที่ 390×844 และ 360px เว้นแต่ระบุ)
> ทุก Phase ต้องลงบล็อกรอบใน `TODO.md` ก่อนเริ่ม · test แบบ offline/deterministic ใช้ `tmp_path` · งาน batch ใช้ concurrency 4 ตามกฎ 24

### Phase 0 — Security + แก้จุดผิดกฎด่วน (1.5–2 วัน) 🔴 ต้องทำก่อน

| ID | งาน | ไฟล์ | Effort | AC |
|---|---|---|---|---|
| 0.1 | **เจ้าของทำเอง:** rotate tunnel token ใน Cloudflare, เปิด Cloudflare Access ครอบทั้งโดเมน, หยุด runner ที่รันอยู่, rotate Gemini keys ถ้าเคยเปิด runner ค้างไว้ | Cloudflare dashboard / Google AI Studio | S | เข้า `studio.nazirulhak.com` จาก browser ที่ไม่ได้ล็อกอินแล้วเจอหน้า Access |
| 0.2 | ย้าย tunnel token ไปเก็บใน Colab Secret, เอาค่าจริงออกจากโค้ดและ ipynb | `build_colab_notebook.py:50`, `Omnicut_Cloud_Runner.ipynb` | S | grep ทั้ง repo ไม่พบ tunnel token literal |
| 0.3 | Auth ในแอป: cookie session + หน้า login (input 16px, ปุ่ม 44px) + ASGI middleware ครอบ `/terminal`, `/token`, `/ws`, `/terminal/ws`, `/agy`; ลบ bypass Colab; extension ใช้ service token | `api_server.py`, `auth.py`, `api_agy.py`, `api.js`, `tests/test_api_auth.py` | M | ไม่มี cookie → `/terminal`, `/api/agy/status` ได้ 401 หรือถูกพาไปหน้า login; WS ถูกปฏิเสธ; extension ยังทำงาน |
| 0.4 | ttyd bind เฉพาะ loopback, ตัด `|| bash`, ใช้ tmux | `build_colab_notebook.py:218-223` | S | `ss -ltn` ไม่เห็น 7681 ฟังบน 0.0.0.0 |
| 0.5 | ลบคำสั่งและตัวอย่างเรื่องราคาจาก prompt/เทมเพลต, ไม่ส่ง `price_note` เข้า prompt, ซ่อน `price_deal` ใน Gallery, ลบ ScriptLab (dead code) | `product_scraper.py`, `ai_bridge.py:237`, `mobile_quick_studio.py:424-429`, `MobileQuickStudio.jsx:1426`, `ExportGallery.jsx:819,2243`, `ScriptLab.jsx` | S | grep `ราคา|บาท|โปร|ส่วนลด` ใน prompt = 0; test lint ผ่าน |
| 0.6 | Copilot: ซ่อน/ปิด 1-Click render ที่ใช้ sine tone และห้ามลง Ready_to_post | `AICoPilotChat.jsx:559-575`, `copilot_engine.py:564-638`, `api_copilot.py:161-211` | S | ไม่มี endpoint ไหนสร้าง MP4 เสียง sine ลง `04_Exports/` |
| 0.7 | AGY: ลบ chip `rm -rf`, เพิ่ม confirm ให้ Git pull | `api_agy.py:502,531` | S | — |
| 0.8 | Settings: ลบ badge สถานะปลอม ให้แสดง "ไม่ทราบ" จนกว่าจะมี health จริง | `SystemSettings.jsx:397-407,446,818-823` | S | ไม่มีข้อความสถานะที่ hard-code |

### Phase 1 — Mobile foundation (4–5 วัน)

| ID | งาน | ไฟล์ | Effort | AC |
|---|---|---|---|---|
| 1.1 | ชั้น navigation: `appNav.js` + `useBackToClose` ใช้กับ Modal / sheet / drawer / สเต็ป | `App.jsx`, `Sidebar.jsx`, `ui/Modal.jsx`, `ActivityCenter.jsx`, `MobileQuickStudio.jsx:387` | M | Tracker→Gallery แล้ว back กลับ Tracker; เปิด sheet แล้ว back ปิด sheet; reload แล้วอยู่แท็บเดิม |
| 1.2 | `MobileShell` 5 แท็บอยู่ใน `TaskProvider` (ตอนแรกให้ห่อ MQS เดิมไว้ในแท็บ "สร้าง") | `App.jsx:507-523`, `components/mobile/MobileShell.jsx` | M | จากเปิดแอปถึงคิวโพสต์/คลังใช้ ≤2 แตะ และเห็น progress งาน |
| 1.3 | Viewport: `h-dvh`, `--nav-h`, safe-area ของ sheet และแถบช่อง, ย้าย toast/notification/LiveRender ขึ้นเหนือ nav | `index.css`, `App.jsx:487-585`, `ActivityCenter.jsx:746,1052-1095`, `ui/Toast.jsx:53` | S | iOS Safari เลื่อนถึงรายการสุดท้ายได้ทุกแท็บ; ไม่มีอะไรทับ nav; ไม่ล้นจอที่ 360px |
| 1.4 | ชิ้น UI กลาง: Button ≥44px, Modal→bottom sheet, ปุ่มปิด 44px, input 16px (ไม่จำกัดแค่ ≤768px) | `ui/Button.jsx`, `ui/Modal.jsx`, `ui/Toast.jsx`, `index.css:61-65` | S–M | Playwright: ไม่มี control ใดเล็กกว่า 44×44; ฟอนต์ input ≥16px |
| 1.5 | ปุ่มที่ต้อง hover 41 จุด → `[@media(hover:none)]:opacity-100` เริ่มจากปุ่มลบ; ปุ่มลบต้องมี confirm | `MediaAssetsHub.jsx`, `ProductToClip.jsx`, `ExportGallery.jsx`, `ScheduleAgenda.jsx` | S | บนจอสัมผัสมองเห็นปุ่มทุกปุ่ม; ปุ่มลบมี confirm |
| 1.6 | Topbar มือถือแถวเดียว 56px; ย้าย AGY และ channel ไปไว้ใน "อื่นๆ"; ปุ่มสลับ "โหมดง่าย/โหมดเต็ม" แบบมีข้อความ | `Topbar.jsx:105-205`, `Sidebar.jsx:178-339` | S | — |
| 1.7 | การเก็บสถานะ: channel + workflow ย้ายไป localStorage; resync เมื่อ `visibilitychange`; หยุด poll ตอนซ่อน; banner "ระหว่างไม่อยู่: เสร็จ N · ล้มเหลว M" | `channelRuntime.js`, `TaskContext.jsx:121-251` | S | kill PWA แล้วเปิดใหม่ได้ช่องและสเต็ปเดิม; กลับเข้าแอปแล้ว banner ขึ้นภายใน ≤1s |
| 1.8 | ลิงก์ origin: เปลี่ยน `mobileBaseUrl`/QR/`mobile_url` เป็น `window.location.origin` (หรือ public URL ที่ตั้งค่าไว้); ซ่อนลิงก์ localhost/Studio เมื่อ host ไม่ใช่ localhost | `ContentTrackerHub.jsx:985,2424`, `ExportGallery.jsx:1646`, `ProductToClip.jsx:2258`, `Sidebar.jsx:37`, `api_render.py:456`, `HyperFramesHub.jsx:546-555,771-779` | S | ไม่มีลิงก์ `localhost`/`127.0.0.1`/`:5173` ที่มองเห็นได้เมื่อเข้าผ่าน tunnel |
| 1.9 | Performance: ตัด Google Fonts ที่ self-host อยู่แล้ว, ฟอนต์ UI ใช้ `swap` (ไม่แตะฟอนต์ preview/render), GZip + Cache-Control `immutable`, `lazyWithRetry`, แก้ `manualChunks` | `index.html:24`, `index.css:7-24`, `api_server.py:385-403`, `vite.config.js:86-95`, `ErrorBoundary.jsx:23-25` | M | LCP ≤3s บน "Fast 4G"; shell ≤150KB gz |
| 1.10 | PWA: service worker แบบเบา (เก็บ app shell + หน้า offline/"เซิร์ฟเวอร์หลับ" + ปุ่มลองใหม่), `start_url` ที่ถูก, `shortcuts` | `public/manifest.webmanifest`, `src/sw.js` ใหม่ | M | ปิด backend แล้วเปิด PWA ขึ้นจอ "เซิร์ฟเวอร์หลับ" ไม่ใช่จอเปล่า |

### Phase 2 — Couple Production Engine + Job API (8–10 วัน) — แกนหลัก

> ⚠️ ประสานกับรอบ Antigravity ที่กำลังผลิต TTZ01: ห้ามแก้หรือลบ `tools/batch_produce_ttz_k106_20.py` ระหว่างรอบนั้นยังเปิดอยู่ ให้ทำ engine ใหม่คู่ขนานไปก่อน

| ID | งาน | ไฟล์ | Effort | AC |
|---|---|---|---|---|
| 2.0 | Quick wins: `/hyperframes/render` เป็น async 202 + task_id; ทุก tool เขียน registry ผ่าน `ExportRegistry`/`ExportCoverBindingStore`/`ProductStore` (มี lock); whisper เขียน `verify.json` และ fail จริง; ตรึง `DATE_STR` ต่อ batch; NVENC fallback ตอน runtime; sync ใส่ `clip_id` | `api_hyperframes.py:512-608`, `tools/batch_render_*`, `batch_produce_*` | S×5 | ล็อกจอ 3 นาทีแล้วกลับมาเห็นสถานะจริง; ไม่มีไฟล์ `_v2` ซ้ำ |
| 2.1 | แยก `scripts/couple_engine/*` ออกจากตระกูล single-take (TTZ/RED01/HAT01); ข้อมูลรายสินค้าอยู่ใน `_Docs/couple_products/{CODE}.json`; TTS ใช้ allowlist ตามกฎ 20 และเมื่อโควตาหมดให้ `paused_quota` ห้าม fallback ไป 2.5 | ใหม่ + `gemini_tts_engine.py` | L | **golden test: HTML ตรงกับ canonical ทุก byte ใน 3 สินค้า** (ภาพคลิปห้ามเปลี่ยน) |
| 2.2 | `couple_jobs` store + state machine + recovery ตอนบูต (`api_server.py:93-160`) + executor token/pid | `scripts/couple_jobs.py` | L | ปิด API กลาง render แล้วเปิดใหม่ job เดินต่อเอง; คลิปที่ valid ไม่ถูกเรนเดอร์ซ้ำ; registry มี 20 แถวพอดี |
| 2.3 | Router `/api/couple`: `POST /jobs` (idempotency 200/409), `GET /jobs/{id}`, SSE `/events`, checkpoints approve/reject (`expected_revision`), pause/resume/cancel, `clips/{idx}/retry`, `/preflight`; ฉายเข้า `/api/tasks/active` | `scripts/api_couple_production.py` | L | SSE reconnect แล้วไม่มี event ขาด; revision เก่าได้ 409 |
| 2.4 | ลำดับ executor: TTS pool 2–3 → whisper (โมเดลเดียว + lock, ทำเสร็จก่อน render เพื่อประหยัด VRAM 8GB) → compose → snapshot คลิปแรกแล้วเปิด checkpoint (ระหว่างรอทำคลิปที่เหลือต่อ) → render pool 4 (`--gpu --browser-gpu`) → enhance NVENC → ปก 9:16/3:4/WebP จากเฟรม CTA → finalize | `couple_engine/*` | L | WebP 2 ไฟล์ต่อ checkpoint ขนาด ≤150KB; render ทำหลัง approve เท่านั้น |
| 2.5 | Colab persistence: mount Drive, snapshot `store.db`/exports หลังแต่ละคลิป (ไม่วาง SQLite บน Drive ตรง), เลิก `git reset --hard` ตอนรันซ้ำ, watchdog ดูแล ttyd/cloudflared ด้วย | `build_colab_notebook.py:62,74,314-337` | M | รีไซเคิล VM แล้ว job/registry/คลิปยังอยู่ |
| 2.6 | `tools/couple_produce.py --product CODE` แบบบาง ๆ; ย้าย 17 สคริปต์เก่าไป archive **หลังเจ้าของอนุมัติ** และอัปเดต AGENTS ข้อ 22 | `tools/`, `AGENTS.md` | S | agent ใช้คำสั่งเดียวผลิตได้ทุกสินค้า |
| 2.7 | Tests: `test_couple_audio.py`, `test_couple_tts.py` (429 → สลับคีย์ → paused, ห้ามใช้โมเดลนอก allowlist), `test_couple_compose_parity.py`, `test_couple_jobs.py`, `test_couple_recovery.py` (ข้ามเที่ยงคืนต้องไม่เรนเดอร์ซ้ำ), `test_couple_finalize.py` (4 threads → 20 แถว), `test_api_couple_production.py` | `tests/` | M | ผ่านแบบ offline |

### Phase 3 — Intake + สคริปต์บนมือถือ (5–6 วัน)

| ID | งาน | ไฟล์ | Effort | AC |
|---|---|---|---|---|
| 3.0 | Quick wins: แยก URL ออกจากข้อความที่แชร์มา (FE+BE); ไม่ล้างช่องจนกว่า task สำเร็จ; ตอน focus โหลดใหม่แต่ไม่รีเซ็ตบทที่เปิดอยู่; quick-add เป็น async | `ProductToClip.jsx:2576,2644,3190,4399`, `api_products.py:75-114`, `mobile_quick_studio.py:381,393-431` | S×4 | วางข้อความแชร์จาก TikTok แล้วได้ชื่อสินค้าถูกต้อง |
| 3.1 | ทำให้สคริปต์มีแหล่งข้อมูลเดียว: เพิ่ม field ใน ProductStore + export `?format=couple20` + sync แบบ merge ตาม `angle_id` ไม่ทับบทที่อนุมัติแล้ว; generate tools ห้ามเขียน products.json ตรง | `product_store.py`, `api_products.py`, `sync_scripts_to_products.py`, `generate_*_20_scripts.py` | M | แก้บทที่ 7 บนมือถือแล้วไฟล์ export เปลี่ยน; รัน sync ซ้ำแล้วบทที่อนุมัติไม่เปลี่ยน |
| 3.2 | `script_rules.py` + `scriptRules.js` + `POST /api/scripts/lint` | ใหม่ | M | พิมพ์ "149 บาท" แล้ว badge แดงขึ้นภายใน ≤300ms และปุ่มอนุมัติถูกปิด |
| 3.3 | Couple generator: task async สร้าง 20 บท วนซ่อมจนผ่านกฎ แสดง progress x/20; `regenerate-couple` พร้อมให้เลือกเหตุผล; ห้ามใช้ `enforce_male_tone` กับบทของน้องนุ้ย | `scripts/couple_script_generator.py`, `api_products.py:1306-1324` | L | 20 บทผ่านกฎ 100%, มี display/spoken ครบ, ล็อกจอแล้วกลับมายังเห็น progress |
| 3.4 | `IntakeScreen` + `share_target` (Android, GET `/?intake=1`) + ปุ่ม "วางลิงก์" (`clipboard.readText`) + คู่มือ iOS Shortcut; `api_intake.py` parse/preview/commit; ถ้าเจอ challenge ให้ทางแก้ "วางสเปก/แนบสกรีนช็อต" | `components/mobile/IntakeScreen.jsx`, `manifest.webmanifest`, `scripts/api_intake.py` | M | แชร์จาก TikTok แล้ว skeleton ขึ้นภายใน ≤100ms; แชร์ลิงก์เดิมซ้ำขึ้น "มีอยู่แล้ว"; CTA เดียวติดล่างจอ |
| 3.5 | `ScriptReviewDeck`: การ์ด `100dvh` ปัดหรือกดปุ่ม ≥48px (เขียนใหม่/แก้/อนุมัติ) + undo 5s; แก้ทีละเทิร์นใน sheet 16px, บันทึกร่างอัตโนมัติ; `POST /angles/review` แบบหลายบท; `PATCH .../script` พร้อม `base_revision` | ใหม่ + `api_products.py` | L | อนุมัติ 20 บทได้ใน ≤40 แตะ; back ปิด sheet ก่อน; สองเครื่องแก้ชนกันขึ้น dialog |

### Phase 4 — Review Queue + พรีวิว + แก้เบา (5 วัน)

| ID | งาน | ไฟล์ | Effort | AC |
|---|---|---|---|---|
| 4.0 | Quick wins: badge "QC ไม่ผ่าน" กดแล้วเปิดพรีวิว (ไม่ใช่ `onQcPass`) ขนาด 44px; แก้ probe ให้ seek ผ่าน `__timelines[cid]` + อ่าน `#b-cta[data-start]` + เขียนผลลง `.cache`; เพิ่ม `cta_t` ใน metadata; editor บน coarse pointer ใช้ preview 540p เป็นค่าเริ่มต้น | `ContentTrackerHub.jsx:212-234`, `probe_visual_gate.py:71-116`, `api_hyperframes.py:176-206`, `EditorShell.jsx:273` | S×4 | probe จับภาพ CTA ได้จริง (ไม่ใช่เฟรมเริ่ม) |
| 4.1 | `api_review.py` + `ReviewQueue`/`ReviewSheet`: การ์ดภาพแชท / CTA + บรรทัดแชทเป็นตัวอักษร, ปุ่ม sticky [ตีกลับ][แก้][ผ่าน], เปลี่ยนคลิปด้วยปุ่ม (ไม่ใช้ edge-swipe), "อนุมัติที่เหลือ" นับเฉพาะใบที่เลื่อนผ่านตาแล้ว, ผลเขียนผ่าน `mark_qc_passed`/`qc_note` | ใหม่ + `product_store.py:1054-1116` | L | 20 การ์ดโหลดใน ≤3s (WebP ≤80KB); ตีกลับต้องใส่ note |
| 4.2 | พรีวิวด้วย **proxy MP4 540p** (`/api/proxy/for-clip`) ไม่ใช่ live HTML; `<video playsInline controls preload="none" poster>` | `api_proxy.py:128-183`, `proxy_manager.py` | S–M | เฟรมแรกขึ้นใน ≤2s บน 4G; fullscreen native บน iPhone ใช้ได้ |
| 4.3 | แก้เบา: แยก `generate_clip(product, idx)`; `PATCH /api/review/{cid}/script` (แก้ display เท่านั้น ส่วน spoken ล็อกไว้, เปลี่ยนรูปจาก `photos`, stepper ขยับเวลา ±0.1s ขนาด 44px); "เรนเดอร์ใหม่ 1 คลิป" เป็น job | `couple_engine/compose.py`, `api_review.py` | L | แก้คำผิดแล้วเห็นภาพใหม่ใน ≤15s; ล็อกจอแล้วยังเห็นสถานะ job |
| 4.4 | Editor บนจอสัมผัส (ขั้นต่ำ): lane ใช้ `touch-action: pan-x pan-y`, long-press 300ms เพื่อเริ่มลาก, ปุ่ม "ปรับช่วงตัด" เปิด TrimAdjustModal, handle มีพื้นที่แตะ ≥44px | `Timeline.jsx`, `TimelineClip.jsx`, `useTimelineDrag.js`, `Toolbar.jsx` | M | ปัดบน lane แล้ว playhead ไม่กระโดด |

### Phase 5 — คลัง, ดาวน์โหลด, ปก, แจ้งเตือน (5 วัน)

| ID | งาน | ไฟล์ | Effort | AC |
|---|---|---|---|---|
| 5.0 | Quick wins: ใช้ WebP ก่อน + `loading="lazy"` + ETag; `?download=1`; copy แคปชันแบบ await + จับ error; input 16px / เป้าแตะ 44px; คลังฟัง `refreshTrigger`; แก้บั๊ก `modified`/`modified_raw` | `ExportGallery.jsx:136,302,355,448,1375,1576,1770-1803`, `media_service.py` | S×5 | หน้าแรกของคลังโหลด ≤800KB |
| 5.1 | `MobileClipLibrary`: grid 3 คอลัมน์ WebP, chip [พร้อมโพสต์][ปกยังไม่ยืนยัน][QC ปัดตก][โพสต์แล้ว], viewer ปัดแนวตั้ง `preload="none"`, กดค้างเพื่อเลือกหลายคลิป; `/api/exports?scope=ready&limit=24&cursor=&lite=1` | ใหม่ + `api_exports.py:290` | M–L | ไม่แสดงราคา; ไม่มี scroll แนวนอนที่ 360px |
| 5.2 | `saveToDevice.js`: โหลดแบบ Range ทีละ 4MB มี % และโหลดต่อได้ → แตะแล้วเรียก `navigator.share({files})` ทันที (ใช้ helper ร่วมกับ Phase 6) | ใหม่, `MobileQuickStudio.jsx:498-546`, `MobileQuickPostPage.jsx:97-128` | M | iPhone คลิป 31MB: แตะครั้งเดียวเห็นตัวเลือก "บันทึกวิดีโอ"; ล็อกจอกลางทางแล้วโหลดต่อได้ |
| 5.3 | `CoverSheet`: ปก 3:4 + 9:16, ป้าย "เลือกแล้ว" เมื่อมี binding, `POST /api/covers/bind`, เลือกเฟรมใหม่ผ่าน `/highlights` (ภาพ 270×480) → `/render-pro` (ดีไซน์เดิม ตาม rule 23); ให้ `/covers/generate` bind ด้วย | `api_covers.py:264-276,1242-1255`, ใหม่ | M | เปลี่ยนปกใน 3 แตะ; คลังกับคิวโพสต์ใช้ไฟล์ปกเดียวกัน |
| 5.4 | `hf_batch_jobs` / ฉาย `couple_jobs` เข้า ActivityCenter: progress done/total, ETA, รายการ fail + ปุ่ม [ลองใหม่], นับ `awaiting_review` เป็น "ต้องทำ" | `scripts/hf_batch_jobs.py`, `hyperframes_activity.py:35`, `TaskContext.jsx` | M | ล็อกจอ 5 นาทีแล้วตัวเลขถูกภายใน ≤1s; restart API แล้ว batch ยังอยู่ |
| 5.5 | แจ้งเตือน LINE Messaging API (`notifier.py`) + deep link `?tab=today&job=` (Telegram เป็นทางสำรอง, Web Push ไว้ทีหลัง) | ใหม่, `App.jsx` | M | batch เสร็จหรือ checkpoint เปิด → LINE ได้ข้อความภายใน 30s; แตะแล้วเปิดตรงการ์ดนั้น |

### Phase 6 — โพสต์จากมือถือ + คิว + สถิติ (5 วัน)

| ID | งาน | ไฟล์ | Effort | AC |
|---|---|---|---|---|
| 6.0 | Quick wins: confirm + กันกดซ้ำก่อน mark-posted; ScheduleAgenda: ยืนยันก่อนลบ, ซ่อนข้อความ "ลาก" บนจอสัมผัส, ป้ายไทยใหม่, ซ่อน video_path, รีเฟรชเมื่อกลับเข้าแอป; AnalyticsHub ใช้ shortLabel และเปิดแท็บ performance บนมือถือ; แก้ route ใน `api.js:371-372` | `MobileQuickPostPage.jsx:174-187`, `MobileQuickStudio.jsx:550-570`, `ScheduleAgenda.jsx`, `AnalyticsHub.jsx:11,79-90` | S×4 | — |
| 6.1 | Backend โพสต์จากมือถือ: `next-due`, `handoff` (→ `awaiting_post`, `pending()` ไม่คืนงานนี้ให้ extension), `confirm` (posted_at = เวลาจริง, รับ `evidence_url`), `abandon`; ขยายการรีเซ็ตคิว; mark-posted ยกเลิก posting job ที่ค้าง | `scripts/api_mobile_posting.py`, `api_schedule_queue.py:47-56,563-568`, `api_tiktok_autopost.py:617`, `posting_jobs.py`, `tests/test_channel_posting_protocol.py` | M | หลัง handoff `/pending` ไม่คืนงาน; confirm ซ้ำได้ 200; abandon แล้วกลับเป็น planned |
| 6.2 | `MobilePostNext`: ① เริ่ม (handoff + prefetch File) ② แชร์ (`clipboard.writeText` แคปชัน → `navigator.share({files})` โดยไม่มี await คั่น) ③ checklist ปักตะกร้า + ปุ่มคัดลอกรหัสสินค้า/ชื่อในตะกร้า ④ กลับเข้าแอปแล้ว sheet ยืนยันเด้งเอง [โพสต์แล้ว][ตั้งเวลาในแอปแล้ว][ยังไม่โพสต์] → คลิปถัดไป | ใหม่, `MobileShell` | L | จากเปิดแอปถึง share sheet ≤2 แตะ; ปิดแอปกลางทางแล้วเปิดใหม่ยังเห็น sheet เดิม; คลิปถัดไปขึ้นใน ≤1s |
| 6.3 | เตือนรอบโพสต์: banner เมื่อเหลือ 10 นาที + `GET /api/schedule-queue/calendar.ics` (VALARM + deep link `?post_next=1&queue=`) | `api_schedule_queue.py` | S–M | เพิ่ม .ics ลงปฏิทินมือถือแล้วได้เตือนตรงรอบ |
| 6.4 | Agenda บนมือถือ: แถบ 7 วันแทนมุมมอง "สัปดาห์" (ที่ต้องลาก), ปุ่มเดียวต่อสถานะ, เมนู ⋯ (ย้ายเวลาด้วย sheet + ชิปรอบ, แก้ปก, ลบแบบมี confirm), โหลดเฉพาะช่วงวัน | `ScheduleAgenda.jsx:170,239-254,1181-1376,1550` | M | ย้ายเวลาได้โดยไม่ต้องลาก |
| 6.5 | สถิติมือถือ: การ์ด "วันนี้" (โพสต์ x/y, รอบถัดไป, เลยกำหนด, คลิปพอโพสต์อีกกี่วัน, Top 3 ตามวิว), กราฟใช้ ResizeObserver + แตะเลือกจุด, ตารางเปลี่ยนเป็นการ์ด, ฟอร์มกรอกยอด 48 ชม. | `analytics/*`, `AreaLineChart.jsx` | M | ตัวอักษรในกราฟ ≥10px; ไม่มีราคา |

### Phase 7 — AI Command Center + Terminal power mode (4 วัน)

| ID | งาน | ไฟล์ | Effort | AC |
|---|---|---|---|---|
| 7.1 | Terminal: pane ใช้ `display:flex; flex:1; min-height:0`; ttyd + tmux + `fontSize=15`; หน้า xterm ของเราเองพร้อมแถบปุ่มพิเศษ (Esc, Tab, Ctrl แบบ sticky, ลูกศร, Ctrl+C/D, วาง, คัดลอก 50 บรรทัด, A−/A+, ต่อใหม่) ตรึงเหนือคีย์บอร์ดด้วย `visualViewport`; หน้า `/agy` ใช้ input 16px, ปุ่ม 44px, เช็ก `res.ok` + ปุ่มลองใหม่ | `api_agy.py:241,312-357,514-582,681-691`, `build_colab_notebook.py:220` | M | ตอนคีย์บอร์ดเปิด terminal ใช้พื้นที่ ≥60% ของ viewport; Ctrl+C หยุด `sleep 100` ได้; ล็อกจอ 2 นาทีแล้วยังอยู่ใน session เดิม |
| 7.2 | `CommandCenter`: แถบสถานะ → การ์ดงาน → chips 44px ('ผลิต 20 คลิปจากลิงก์นี้', 'สถานะงาน', 'เรนเดอร์ใหม่คลิป s07', 'โพสต์คลิปถัดไป', 'เช็กระบบ') → plan card → "เริ่มงาน"/"ยกเลิก" → job card; งานทำลายต้องผ่าน sheet ที่ระบุเป้าหมาย + กดค้าง 1.5s; LLM ใช้ได้เฉพาะ domain tools ใน whitelist ไม่มี raw shell | `components/mobile/CommandCenter.jsx`, `/api/command/*` (พึ่ง Phase 2/6) | L | จากเปิดแอปถึงเริ่มงาน ≤4 แตะ; ส่งงานทำลายโดยไม่มี `confirm_token` ได้ 409; ล็อกจอ 5 นาทีแล้ว progress ถูกและไม่มีงานซ้ำ |
| 7.3 | Settings "AI และการเชื่อมต่อ": `GET /api/settings/ai` (จำนวนคีย์, 4 ตัวท้าย, 429 ล่าสุด, โมเดล, สถานะ agy login), `PUT .../keys` แบบเขียนอย่างเดียว + test, wizard ล็อกอิน agy (`login/start` คืน URL, `login/complete` รับ code) | `SystemSettings.jsx`, `api_agy.py`, `colab_login_helper.py:78,124-141` | M | response ไม่มีค่า `AIza…` เลย; สถานะตรงกับ `/api/agy/status` |

### Phase 8 — ถ่าย/อัปโหลด (เลน gadget ที่มีฟุตเทจ) (4–5 วัน) — ทำเมื่อยังใช้เลนนี้

| ID | งาน | Effort | AC |
|---|---|---|---|
| 8.0 | Quick wins: timeout ของ `uploadMobileVideo` เป็น 600s, reset `input.value`, แสดง error ใต้ปุ่ม + ลองใหม่, เตือนเมื่อไฟล์ >95MB ผ่าน tunnel; `onProgress` ของ Guided Take; ถามยืนยันก่อน Home + `beforeunload`; error กล้องเป็นภาษาไทย + `isSecureContext`; MQS ล้าง `uploadedVideoPath` เมื่อเปลี่ยนมุม (บั๊กฟุตเทจข้ามมุม) + แก้เงื่อนไขแบนเนอร์ + อ่าน `rendered_video_url` | S×5 | — |
| 8.1 | `api_uploads.py` แบบ chunk ต่อได้ + SHA-256 dedupe + staging (ไม่เขียน `01_Raw` ตรง) | M | ไฟล์ 600MB ผ่าน tunnel ได้; ปิด Wi-Fi กลางทางแล้วส่งต่อจาก chunk ล่าสุด; อัปไฟล์ซ้ำแล้วไม่มีไฟล์ใหม่ |
| 8.2 | `uploadQueue` + `UploadTray` (IndexedDB, backoff, ส่งต่อเองเมื่อ `online`/`visibilitychange`, wake lock) | L | เปิด airplane mode 30s แล้วส่งต่อเองได้ |
| 8.3 | Guided Take ส่งทีละช็อตระหว่างถ่าย + กู้สถานะจาก `session.segments` + finalize แบบ idempotent ผ่าน staging | M | ล็อกจอหลังช็อต 2 แล้วกลับมาถ่ายช็อต 3 ต่อได้; finalize ซ้ำได้ไฟล์เดียว |
| 8.4 | ปุ่มกล้อง `capture="environment"` + อัลบั้มแบบ `multiple`; poster + proxy 540p หลังอัปเก็บไว้ใน cache; sheet "คลิปของสินค้านี้" | M | thumbnail จริงขึ้นใน ≤30s |

### สรุปเวลา

| Phase | วัน (ประมาณ) | ได้อะไร |
|---|---|---|
| 0 | 1.5–2 | ปลอดภัย + ไม่ผิดกฎ |
| 1 | 4–5 | ใช้แอปบนมือถือได้ลื่น นำทางได้ ไม่หลุด |
| 2 | 8–10 | **ผลิต 20 คลิปด้วยแตะเดียว** โดยไม่ต้องพิมพ์คำสั่ง |
| 3 | 5–6 | ลิงก์ → 20 สคริปต์ → อนุมัติ บนมือถือ |
| 4 | 5 | ตรวจคลิปตามกฎ 22 บนมือถือ |
| 5 | 5 | คลัง / เซฟลงเครื่อง / ปก / แจ้งเตือน LINE |
| 6 | 5 | โพสต์จากมือถือทีละคลิปต่อเนื่อง |
| 7 | 4 | สั่งงานด้วยแชท + terminal ใช้ได้จริง |
| 8 | 4–5 | อัปโหลดคลิปใหญ่ / ถ่ายเองได้เสถียร |
| **รวม** | **≈ 45–55** | |

**ลำดับแนะนำถ้าอยากได้ผลเร็ว:** 0 → 1 (1.1–1.4, 1.7–1.8) → 2.0 → 6.0–6.2 (โพสต์จากมือถือได้ก่อน เพราะใช้กับคลิปเก่าที่ทำเสร็จแล้วได้ทันที) → 2 → 3 → 4 → 5 → 7 → 8

---

## 6. Quick wins รวม — ทำได้ใน 2–3 วันแรก (≤0.5 วันต่อข้อ)

1. Phase 0 ทั้งหมด (security + ราคา + sine tone + สถานะปลอม)
2. ห่อโหมดมือถือด้วย `TaskProvider` + `GlobalTaskNotification` (`App.jsx:507-523`)
3. `h-dvh` + `--nav-h` + ย้าย Toast/Notification/LiveRender ขึ้นเหนือ nav
4. ปุ่มปิดทุกตัว 44px + Modal เป็น bottom sheet ที่จอ <640px + input 16px
5. `mobileBaseUrl` → origin ปัจจุบัน (QR/ลิงก์โพสต์ใช้ผ่าน tunnel ได้)
6. `/hyperframes/render` เป็น async 202 + task_id
7. TaskContext: `visibilitychange` + หยุด poll ตอนซ่อน
8. Confirm + กันกดซ้ำตอน mark-posted; ตอน mark-posted ใช้ posted_at เป็นเวลาจริง
9. แยก URL จากข้อความที่แชร์มา + ไม่ล้างช่อง input
10. MQS: แก้บั๊กฟุตเทจข้ามมุม, อ่าน `rendered_video_url`, แก้เงื่อนไขแบนเนอร์
11. แก้ probe Visual Gate ให้ seek เวลา CTA ได้จริง
12. Gallery ใช้ WebP + lazy + ETag; terminal pane แสดงเต็มความสูง

---

## 7. แผนทดสอบ

| ชั้น | เครื่องมือ | สิ่งที่วัด |
|---|---|---|
| Unit/API (offline) | `pytest tests/` + `tmp_path` ตาม `.agents/rules/testing_standard.md` | job state machine, idempotency, recovery, lint กฎสคริปต์, auth ครอบทุก path รวม WS, posting protocol |
| Frontend unit | `npm test` | `appNav`, `scriptRules.js` (ใช้ชุดทดสอบเดียวกับ Python), `saveToDevice`, `uploadQueue` |
| Mobile layout gate (อัตโนมัติ) | Playwright ที่ 360×740, 390×844, 430×932 + landscape 844×390 ต่อยอดจาก `motion_capture/test_mobile_studio_browser.py` | ทุก control ≥44×44, ฟอนต์ input ≥16px, `scrollWidth ≤ innerWidth`, back ปิด sheet, ไม่มีลิงก์ localhost/:5173 ที่มองเห็นได้, ไม่มีข้อความราคา |
| อุปกรณ์จริง | iPhone (Safari + PWA ติดตั้งแล้ว) + Android (Chrome + PWA) | share_target / Shortcut, `navigator.share` (ต้องเห็น TikTok ใน share sheet), บันทึกลง Photos, ล็อกจอ 5 นาทีระหว่างงาน, airplane mode ระหว่างอัปโหลด, คีย์บอร์ดเปิดใน terminal |
| ทนทาน | ทดสอบด้วยมือ + test | kill API กลาง render, รีไซเคิล Colab VM, รันข้ามเที่ยงคืน |
| Visual (กฎ 22) | สกัดเฟรมจริง | golden HTML parity 3 สินค้า + snapshot แชท/CTA ต่อคลิป ห้ามเชื่อแค่ exit 0 |

---

## 8. กรอบกฎที่ต้องรักษาระหว่างทำ

- **ห้ามเปลี่ยนภาพ/เสียงของคลิป:** golden test ใน 2.1; ห้ามแตะฟอนต์/ซับ (rule 10, 12, 17); TTS ใช้ prompt/guard เดิม 100% (rule 20)
- **Preview = Render:** ไม่แตะ `SequencePlayer.jsx` ในแผนนี้ ถ้าจำเป็นต้องแก้คู่กับ `subtitle_engine.py` + `test_preview_render_parity.py`
- **ไม่มีราคา** ในคลิป แคปชัน หน้าคลัง หรือการ์ดสถิติ
- **01_Raw / 02_Assets:** อัปโหลดผ่าน staging เท่านั้น ห้าม `-y` ทับ; dedupe ด้วย SHA-256 (rule 13)
- **สถานะตรงความจริง:** badge ทุกตัวมาจาก record จริง (rule 8)
- **Concurrency 4 + `is_valid_mp4` + Lock** สำหรับไฟล์ทะเบียนกลาง (rule 24)
- **ไฟล์ทดสอบ:** ใช้ `.tmp/`/`tmp_path` แล้วลบทิ้ง 100% ห้ามลง `04_Exports` (rule 11, 15)
- **Jev:** เรียกตาม 6 จุดบังคับในทุก Phase; ถ้า confidence <0.80 ให้ถามเจ้าของ

---

## 9. คำถามที่ต้องให้เจ้าของตัดสิน (ถ้าตัดสินแล้วแผนจะชัดขึ้น)

| # | คำถาม | กระทบ |
|---|---|---|
| Q1 | **มือถือหลักเป็น iPhone หรือ Android?** ติดตั้ง PWA ลงหน้าโฮมแล้วหรือยัง? | share_target (Android ใช้ได้, iOS ต้องใช้ Shortcut/ปุ่มวาง), Web Push, ทางบันทึกลง Photos |
| Q2 | **เวลาใช้มือถือ เครื่องที่ทำงานหลักคือ PC (RTX 4060) ที่เปิดค้างไว้ หรือ Colab?** | persistence, concurrency, Chrome extension (ใช้บน Colab ไม่ได้เลย) |
| Q3 | ยอมให้แอปเรียก Gemini เขียน 20 บทเองไหม (ใช้โควตา) และใช้สินค้าไหนเป็นต้นแบบคุณภาพ (เช่น TTZ01)? | Phase 3.3 |
| Q4 | **ไฟล์ไหนคือ canonical จริง?** กฎ 22 ชี้ `batch_produce_hatari_20.py` (ยิง TTS ทีละเทิร์น) แต่ STYLE.md:181 ห้ามยิงทีละเทิร์น เสนอให้ใช้ตระกูล single-take (TTZ/RED01) | Phase 2.1 |
| Q5 | นโยบายโมเดล TTS: ล็อก `gemini-3.1-flash-tts-preview` ตัวเดียว หรือยอมให้ใช้ `3.8-flash-tts` ด้วย? และถ้าโควตาหมดให้ "รอ" แทน fallback ไป 2.5 ใช่ไหม? | Phase 2.1 |
| Q6 | การอนุมัติ: สคริปต์ต้องครบ 20/20 ก่อนผลิต หรืออนุมัติบทไหนผลิตบทนั้น? คลิปต้องตรวจทุกใบ หรือ "อนุมัติที่เหลือ" ได้เมื่อเลื่อนผ่านตาแล้ว? | Phase 3.5, 4.1 |
| Q7 | การโพสต์บนมือถือ: แชร์เข้าแอป TikTok เองทีละคลิปตามรอบ (เตือน 7 ครั้งต่อวัน) หรือตั้งเวลาในแอป TikTok ทีละหลายคลิป? กดยืนยันเองถือเป็นหลักฐานพอไหม? | Phase 6 |
| Q8 | ช่องแจ้งเตือน: LINE OA ฟรี (จำกัดราว 300 ข้อความ/เดือน — สมมติฐาน) หรือ Telegram (ฟรี ส่งไฟล์ ≤50MB เข้าเครื่องได้)? | Phase 5.5 |
| Q9 | ยังใช้เลนถ่ายฟุตเทจ gadget อยู่ไหม? ถ้าไม่ใช้ Phase 8 ลดเหลือแค่ quick wins และซ่อนเลนนี้ไว้ในเมนูรอง | Phase 8 |
| Q10 | ยอมใส่ Cloudflare Access ครอบทั้งโดเมนไหม (extension ต้องเปลี่ยนไปใช้ service token) และยังต้องการ raw shell บนมือถือไหม? | Phase 0, 7 |

---

## 10. ภาคผนวก — หลักฐานเด่นรายส่วน

- **#2 Shell:**
  - `pushState` ทั้ง `src` = 0
  - ใช้แค่ `replaceState` (`App.jsx:102`, `channelRuntime.js:42`, `MobileQuickStudio.jsx:387`, `EditorShell.jsx:860`)
  - fixed px width 52 จุด (`StageForms.jsx:275` min-w 920, `ScheduleAgenda.jsx:1903` 760)
  - Tailwind v4 ไม่อ่าน `tailwind.config.js` (ไม่มี `@config`) ทำให้ animation ของ sheet ไม่ทำงาน
- **#3 MQS:**
  - DTO ส่ง `rendered_video_url` แต่ UI อ่าน `video_url` (MQS:794 เทียบ `mobile_quick_studio.py:235`)
  - ฟุตเทจข้ามมุม (MQS:756-759,899,1277-1290)
  - แผนเก่า: ส่วน V2 P0 ทำครบ ส่วนค้นหาสินค้า, "AI คิด 7 มุม", จุดขาย 3 ข้อ ยังไม่ได้ทำ
- **#4 Intake:**
  - quick-add เป็น sync และสร้างบท "พิกัดราคาโปรโมชั่น" (`mobile_quick_studio.py:375-431`)
  - focus reload เด้งกลับบทที่ 1 (`ProductToClip.jsx:2576,2644`)
  - ID สินค้าใน `sync_scripts_to_products.py:66-67,81-82,165-166` ดูเป็นเลขสมมติ (…746001–008) ควรตรวจก่อนปักตะกร้า
- **#5 Engine:**
  - สคริปต์ซ้ำกัน: hatari_20 กับ hoyaup ต่างกันแค่ 147/891 บรรทัด
  - PRODUCT_ID ฝั่ง produce กับ render ไม่ตรงกัน (GOO01, RED01)
  - hyperframes มี 3 เวอร์ชัน
  - `_RENDER_LOCK` ให้ render ได้ทีละ 1 (`api_hyperframes.py:51,513`)
- **#6 Upload:**
  - backend ยอมรับไฟล์ถึง 2GB (`api_videos.py:191`) แต่ tunnel ตัดที่ประมาณ 100MB
  - WebM จาก Android อาจได้ duration 0 จน segment ถูกปฏิเสธ (สมมติฐาน, `video_editor.py:1405`)
  - Colab เก็บไฟล์ที่ `/content/Omnicut` ซึ่งหายเมื่อรีเซ็ต runtime
- **#7 Preview:**
  - Studio/`/open-studio` สั่ง `webbrowser.open` บนเครื่อง server (`api_hyperframes.py:618-659`)
  - tunnel เปิดแค่ :8000
  - `.tmp` ถูก `/api/media` ปฏิเสธ (`api_videos.py:1339-1371`)
  - ปุ่ม "รอตรวจ QC" อนุมัติได้โดยไม่ต้องดูคลิป
- **#8 Render:**
  - ปก JPG ค่ากลาง 235KB เทียบ WebP 40KB (ประมาณ 4.7MB ต่อหน้า)
  - toast duration 0 + คิว 8 อัน (`TaskContext.jsx:55,64`)
  - Gallery แสดง `price_deal`
- **#9 Post:**
  - ไฟล์ใน Ready_to_post 53 ไฟล์ ขนาด 17–76MB (ค่ากลาง 33MB)
  - คิวราว 200 แถว (JSON ราว 367KB) โหลดทั้งก้อน
  - ค่าเริ่มต้นในโค้ด 5 รอบต่อวัน แต่กฎใช้ 7 รอบ (`api_schedule_queue.py:38`)
- **#10 AI:**
  - Cell 1 ของ notebook วน `while True` ไม่จบ ทำให้ Cell 2 (login) ไม่เคยได้รัน (`build_colab_notebook.py:314,352-362`)
  - session ของ agent อยู่ใน RAM ล็อกจอแล้ว loop หยุด (`agy_cloud_agent.py:684,825-894`)
  - Co-Pilot ชี้ preview ไป `localhost:3002`
