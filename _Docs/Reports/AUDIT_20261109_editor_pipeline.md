# AUDIT 2026-11-09 — OmniCut ทั้งสาย: ดึงสินค้า → สคริปต์/TTS → Auto-cut → Editor → ซับ/Parity → Render/Registry

ดำเนินการโดย: Claude Code (Claude Opus 5.5) + read-only sub-agents 6 ตัว (Claude Opus 5.5)
สถานะ: **ตรวจ + วางแผนเท่านั้น — ยังไม่แก้โค้ด รอผู้ใช้ตอบ "อนุมัติแผน"**

## สรุป 1 หน้า

| ด่าน | P0 | P1 | P2 | P3 | รวม |
|---|---|---|---|---|---|
| 1 Sourcing | 2 | 10 | 5 | 2 | 19 |
| 2 สคริปต์/TTS/เสียง | 0 | 8 | 9 | 4 | 21 |
| 3 Auto-cut | 0 | 7 | 7 | 3 | 17 |
| 4 Editor (6 ข้อมาจาก diff ที่ยังไม่ commit) | 0 | 2 | 9 | 4 | 15 |
| 5 ซับ/Callout/Parity | 1 | 7 | 6 | 2 | 16 |
| 6 Render/Export/Registry | 1 | 7 | 3 | 3 | 14 |
| รอยต่อ (เฉพาะข้อใหม่ X-01, 02, 06, 07; X-03..05 เป็นกลุ่มของข้อเดิม) | 1 | 2 | 1 | 0 | 4 |
| **รวม** | **5** | **43** | **40** | **18** | **106** |

**P0 ทั้ง 5 ข้อ**
1. **S5-01** — cache `02_Assets/asset_registry.json` ยังชี้ path `D:\Winona\Programmer\Capcut\...` → font scale = 1.0 → **ทุก render ตอนนี้ซับเล็กลง ~40% (Fontsize 50 แทน 82) และ hook line หายเงียบ** (ยืนยันซ้ำแล้ว)
2. **X-01** (ต้นเหตุร่วม) — `scripts/db.py:501` import JSON mirror ที่ใหม่กว่าด้วย `DELETE FROM` ทั้งตาราง
3. **S1-01** — `tools/batch_produce_*` เขียน `products.json` ตรง → สินค้าที่แอปเพิ่มหายได้
4. **S6-01** — `tools/batch_render_*` เขียน `export_registry.json` ตรง + read error = `[]` → registry เหลือ 1 แถวได้
5. **S1-07** — `scrape-and-plan` HTTP 500 เมื่อเพจไม่มี description

**ภาพรวม:** เทส node 1,226 + parity 357 ผ่านหมด แต่ไม่จับบั๊กใหญ่ เพราะ (ก) conftest สร้าง font registry ใหม่ (ข) contract test เช็คแค่ string (ค) browser E2E ที่จับได้จริงพัง 77 ข้อมาตั้งแต่ commit `93a8ca4` และไม่มีใครรัน. ถ้าจะใช้คำว่า "ผ่าน 100%" ต้องนับ `tests/motion_capture` ด้วย

ลำดับแก้: ดูหัวข้อ 8 · ต้องให้ผู้ใช้ตัดสินใจ 13 ข้อ: หัวข้อ 8.4 · เทสที่ต้องเพิ่ม: หัวข้อ 9

## 0. Pre-flight

- Working tree ตอนเริ่ม: งานค้างไม่ commit 9 ไฟล์ (`EditorShell.jsx` +281 บรรทัด, `SequencePlayer.jsx`, `usePanelLayout.js`, `EditorHeader.jsx`, `ProjectSelector.jsx`, `SaveStatusChip.jsx`, `ActivityCenter.jsx`, `TODO.md`, `HISTORY.md`) + `frontend/dist` rebuild — เป็นของรอบ Antigravity (Gemini 3.8 Flash) 20261109 ที่ติ๊ก `[x]` ใน TODO แต่ยังไม่ commit. ตรวจตามสภาพ ไม่ stash/commit แทน
- Jev ก่อนเริ่ม: `approach=as_is` conf 1.0 · `safe_to_start` noul 0.92 แต่ conf `null` (SDK ไม่คืน confidence ให้ noul → `jev_advisor.py:164` escalate ทุกครั้ง) → ถามผู้ใช้ → อนุมัติให้เริ่ม
- วิธี: แต่ละด่านอ่าน path จริง → สมมติฐาน → ยืนยันด้วยโค้ด/เทสเดี่ยว/repro ใน `.tmp/audit_20261109_sN/` (mock network + AI, lavfi clip) → ลบโฟลเดอร์ทิ้งทุกด่าน
- เทสทั้งชุด: frontend `npm test` = **1,226/1,226 pass** (เป็น `node --test` ไม่ใช่ Vitest — ชื่อใน TODO/รายงานเก่าคลาดเคลื่อน) · parity + subtitle 8 ไฟล์ = **357/357 pass** · browser E2E `tests/motion_capture` = **77 fail / 101 pass** (X-07) · full `pytest tests/` รอบแรกรันชนกับ agent 6 ตัวจนช้า (2% ใน ~25 นาที) จึงหยุดเอง — **ยังไม่มีผล full suite ที่ไม่ใช่ motion_capture** (รันเดี่ยวเฉพาะไฟล์ที่เกี่ยวในแต่ละด่านแทน)
- หลังตรวจ: `01_Raw`, `02_Assets`, `03_Projects`, `04_Exports`, `05_Covers_Thumbnails` รายชื่อไฟล์ตรงกับ snapshot ก่อนเริ่ม 100%; `export_registry.json`, `export_cover_bindings.json`, `products.json` sha256 ตรงเดิม; `.tmp/audit_20261109_s1..s6` ลบแล้ว; `.tmp/motion-vite-b6ue1bd3` จากเทส browser ลบแล้ว

ระดับ: **P0** พังงาน/ข้อมูลหาย/ช่องโหว่ · **P1** ผลผิดกฎโปรเจกต์ · **P2** UX/perf · **P3** cleanup · ขนาด S/M/L

---

## 1. ด่าน 1 — Sourcing (ลิงก์ → scraper → ProductStore → 01_Raw)

Flow จริง: `api_intake.preview` / `api_products.scrape_and_plan` → `ProductScraper.scrape_url` (urllib + SSRF-safe opener → TikTok PDP JSON → og/meta → Playwright fallback) → `generate_content_matrix` (Gemini) → `ProductStore.add` (SQLite `store.db` + mirror `products.json`). ภาพสินค้าเก็บแค่ URL; ไฟล์ใน `01_Raw/<product_id>/` มาจาก mobile/guided-take upload เท่านั้น

| ID | Sev | ไฟล์:บรรทัด | อาการ | สาเหตุ | หลักฐาน | วิธีแก้เสนอ | ขนาด | ความเสี่ยง |
|---|---|---|---|---|---|---|---|---|
| S1-01 | P0 | `tools/batch_produce_*_20.py` (~30 ไฟล์ เช่น `batch_produce_essager_20.py:518-535`), `scripts/couple_engine/finalize.py:150,305` | สินค้าที่แอปเพิ่มหายเงียบเมื่อ batch tool รันพร้อมแอป | tools อ่าน-แก้-เขียน `products.json` นอก lock SQLite `BEGIN IMMEDIATE`; `db.py` import mirror ที่ใหม่กว่าเป็น "external edit" ทับ DB; `finalize.py` ใช้ `FileLock` ของตัวเองที่ store ไม่รู้จัก | repro temp store: add A → อ่านไฟล์ → add B → เขียนสำเนาเก่ากลับ → `snapshot()` = `['Product A']` B หาย | ให้ทุกตัวผ่าน `ProductStore.update_angle()`/`_mutate()` หรือ helper กลางที่ถือ lock; เทส lint ห้าม `json.dump` ลง `products.json` นอก `db.py` | M | กลาง (หลายไฟล์ แต่ mechanical) |
| S1-07 | P0 | `scripts/product_scraper.py:1141,1225` → `_extract_specs_from_text:837` | `scrape-and-plan` HTTP 500 `'NoneType' object has no attribute 'replace'` เมื่อเพจไม่มี description/og:description | `description = html_product_text or meta_description` เป็น `None` ได้ | repro crash ที่ :837 | `or ""` + guard None ใน `_extract_specs_from_text` | S | ต่ำ |
| S1-08 | P1 (security) | `scripts/api_products.py:75-112` (`POST /api/products/resolve-tiktok-id`) | SSRF: ยิง URL ใดก็ได้รวม localhost/169.254 metadata; ตัวเลข 15+ หลักใดๆ ถูกถือเป็น product ID | `urllib.request.urlopen` เปล่า ไม่ผ่าน `_validate_scrape_url` | repro (stub urlopen) จับ request ไป `127.0.0.1:8000/admin` และ `169.254.169.254`; `"ออเดอร์ 202611091234567890"` → product_id ผิด | ใช้ `_validate_scrape_url` + `_build_safe_opener`; ตัด fallback ตัวเลขล้วน | S | ต่ำ |
| S1-09 | P1 (security) | `api_products.py:280-288` → `product_scraper.py:1605-1615` | ไฟล์ local ใดก็ได้ใน `image_paths` (เช่น `.env`) ถูกอ่านส่ง Gemini + absolute path ถูกเก็บใน product | ไม่มี containment check | อ่านโค้ด: `Path(raw_path).read_bytes()` ไม่มี `relative_to` | resolve + บังคับอยู่ใต้ upload/media root + จำกัดนามสกุลภาพ | S | ต่ำ |
| S1-02 | P1 | `product_scraper.py:741` (step 8 `clean_product_title`), `:718` | ชื่อรุ่นเสียขีด: `WH-1000XM5`→`WH 1000XM5`, `USB-C`→`USB C` (ผิดกฎ 9) | regex `[\s/|•,，\-–—]+`→`' '`; `Type‑?C` ใช้ U+2011 ไม่ match ASCII `-` | repro ผลตามอาการ | แยกเฉพาะขีดที่มีเว้นวรรครอบ `\s+[-–—]\s+`; แก้ U+2011 | S | ต่ำ |
| S1-03 | P1 | `product_scraper.py:649-751`, `script_rules.py:291-322`, `product_store.py:652,772`, `api_products.py:1018,1058` | ราคา/ส่วนลด/อีโมจิในชื่อผู้ขายหลุดเข้าชื่อสินค้า + prompt AI; sanitizer ทำไทยเพี้ยน (`ลดราคา`→`ลดความคุ้ม`) ตัวเลขราคายังอยู่ | `clean_product_title` ไม่ตัด `฿/บาท/%/Sale/ลด N%`/emoji; `sanitize_text_for_rules` ใช้แค่ `api_intake` ไม่ใช้ใน `ProductStore.add`/`scrape_and_plan` | `"🔥ลดราคา 50%🔥 … ราคา 299 บาท ฿299"` → clean ไม่เปลี่ยน; clean+sanitize = `"ลดความคุ้ม 50% … ความคุ้ม 299 299"` lint=None | เพิ่ม step ตัดราคา/โปร/emoji ใน `clean_product_title` เรียกจาก add/update; reject ถ้า `find_price_term` ยังเจอ | S | ต่ำ |
| S1-04 | P1 | `product_scraper.py:1148-1151`, `:904-910`, `:849-882` | ภาพสินค้าอื่น/แบรนด์อื่น + thumbnail ความละเอียดต่ำถูกเก็บ ส่ง Gemini (prompt สั่งให้เชื่อภาพมากกว่าข้อความ) และใช้เป็น thumbnail | เก็บทุก `<img>` ในเพจรวม carousel สินค้าแนะนำ; ไม่มี host allowlist / dimension gate | mock เพจ Anker ได้ `~100:100.jpg`, `~tplv-crop.jpeg`, `cdn.other.com/jbl-tune.png` | เก็บจาก PDP gallery + og:image เท่านั้น, allowlist CDN, ตัด `100:100/300:300/crop` หรืออัปเป็น 800:800, เช็คขนาด ≥1080 / ≥100KB | M | กลาง (ภาพน้อยลง) |
| S1-05 | P1 | `product_scraper.py:1098-1166`, `api_intake.py:101-123` | หน้า captcha/WAF/ลิงก์ตาย ถือว่า scrape สำเร็จ ชื่อสินค้าเป็นชื่อหน้า captcha | `_looks_like_browser_challenge` รันแค่ Playwright path; timeout → slug/`"สินค้าแนะนำ"` ไม่มี warning | mock Shopee captcha → title `'Shopee Security Verification Page Please Wait'`, `intake_flags_waf=False`; timeout → `needs_manual=False` | ตรวจ challenge บน direct-fetch ด้วย; slug_fallback ไม่มี desc/ภาพ → `needs_manual=True` + warning ไทย | S | ต่ำ |
| S1-06 | P1 | `product_scraper.py:28,1245` | scrape ไม่ได้อะไร → คำกล่าวอ้างแต่งเอง `"การันตีของแท้"` กลายเป็น description แล้ว AI เขียนสคริปต์จากมัน | ใช้ placeholder constant เป็น source จริง | เห็นใน repro S1-05 | description ว่าง + mark source missing ห้ามแต่ง claim | S | ต่ำ |
| S1-10 | P1 | `tools/download_gadget_pack.py:36,68-69`, `tools/media_intake_audit.py` | กฎ 12 (ซับต่างชาติฝัง) ไม่ถูกตรวจจริง — hardcode `"no_foreign_subtitles": True`; OCR auditor ไม่มีใครเรียก; yt-dlp อาจได้ 360p | flags hardcode, audit tool ไม่ wire, ไม่มี min-res check | grep ไม่พบ caller ของ `media_intake_audit` | รัน `media_intake_audit` + ffprobe height ≥1080 ก่อนเขียน `info.json`; ใส่ใน raw upload intake ด้วย | M | ต่ำ |
| S1-11 | P1 (security) | `tools/download_gadget_pack.py:17-19,35,44,58` | command injection/คำสั่งพังถ้า URL/path มี quote หรือ `&` | `subprocess.run(cmd, shell=True)` + f-string | อ่านโค้ด | list args + `shell=False` | S | ต่ำ |
| S1-12 | P1 | `scripts/asset_dedup.py:142-239`, `api_asset_dedup.py:21-53` | clean duplicate อาจลบไฟล์ที่ product/angle อ้างอิงอยู่ → ลิงก์เสีย; `/scan` เห็นไฟล์ทุกช่อง | safety check ดูแค่มี survivor byte-identical ไม่ดู reference; scan ไม่ filter scope | อ่านโค้ด | ปฏิเสธลบ path ที่ถูกอ้าง หรือ rewrite reference ใน transaction เดียว; filter ตามช่อง | M | กลาง |
| S1-13 | P2 | `scripts/mobile_quick_studio.py:328-340` | upload คลิปเดียวกันพร้อมกัน 2 ครั้ง → เซฟซ้ำ (กฎ 13) | hash check แล้ว write ไม่มี lock; ชื่อไฟล์มี uuid; `write_bytes` ไม่ atomic | อ่านโค้ด | per-product Lock + temp→`os.replace` | S | ต่ำ |
| S1-14 | P2 | `scripts/product_store.py:667-669` | ลิงก์เดียวกันต่าง query string → สินค้าซ้ำ | URL dedup เทียบ string ตรงตัว | repro `…/pdp/111?source=share` ได้ product ที่ 2 | normalize URL + dedup ด้วย `tiktok_product_id` | S | ต่ำ |
| S1-15 | P2 | `product_scraper.py:884-1008` | เจอ challenge → เปิด Chrome แบบมีหน้าต่างบน server บล็อก request ถึง 60s; scrape พร้อมกันชน profile เดียว | `headless=False` retry, `RENDERED_PROFILE_DIR` ร่วม | อ่านโค้ด | flag `allow_headed=False` สำหรับ API, lock browser หรือ profile ต่อ request | S | ต่ำ |
| S1-16 | P2 | `couple_engine/finalize.py:290-303` | เก็บ absolute `video_url`/`cover_url` ลง `products.json` (ผิดกฎ 2) | `str(mp4_file.resolve())` | อ่านโค้ด | เก็บ path relative BASE_DIR | S | ต่ำ |
| S1-17 | P2 | `api_products.py:563-580` | ผูกไฟล์ absolute ใดก็ได้เป็นวิดีโอสินค้า | ไม่มี containment check `video_path` | อ่านโค้ด | `_resolve_allowed_video_path` (INBOX/RAW/PROJECTS) | S | ต่ำ |
| S1-18 | P3 | `product_scraper.py:850-860` | URL ภาพที่มีคำ `star/arrow/icon` ตรงไหนก็โดนทิ้ง | substring blacklist | อ่านโค้ด | match เฉพาะชื่อไฟล์/segment | S | ต่ำ |
| S1-19 | P3 | `mobile_quick_studio.py:328`, `recording_sessions.py:288` | 01_Raw ใช้ UUID ไม่ใช่ `YYYYMMDD_ชื่อสินค้า-ประเด็น` (containment ปลอดภัย) | design ขัดกฎ 2 | อ่านโค้ด | **ต้องตัดสินใจ:** แก้กฎให้ตรง UUID หรือเพิ่ม alias folder | S | ต่ำ |

ผ่าน: ProductStore เขียนผ่าน SQLite transaction + `threading.Lock` + mirror atomic (tmp→`os.replace`); scraper opener เช็ค SSRF ทุก redirect; `generate_content_matrix` ไม่ส่ง `price_note` + มี NO_PRICE_RULE; ไม่พบ absolute path ใน stage-1 modules. เทสที่รัน: `test_product_title_cleaning.py` 7/7 (ไม่มีเคสขีด)

ยังไม่ยืนยัน: `price_note` ถูก copy เข้า HyperFrames snapshot (`api_hyperframes_workflow.py:138`, `hyperframes_finalize.py:131`) — ยังไม่เช็คว่า template render ไหม · `api_covers.py:1432-1441` `urlopen` URL ใดก็ได้ (SSRF pattern เดียวกับ S1-08) · `gdrive_archive_engine.py:359-363` `rmtree` โฟลเดอร์ 01_Raw จาก `project_name` · body text ทั้งเพจเข้า `raw_text` (สินค้าแนะนำปน prompt) · log scraper เป็นอังกฤษ · `mobile_quick_studio.py:170` ส่ง `price_note` ใน mobile catalog

---

## 2. ด่าน 2 — สคริปต์ / TTS / เสียง

เทสที่รัน: `test_voice_engine_line_failure_timeline.py` + `test_gemini_tts_retry.py` 8 pass · `test_gemini_tail_artifacts.py` + `test_tts_display_separation.py` 5 pass

| ID | Sev | ไฟล์:บรรทัด | อาการ | สาเหตุ | หลักฐาน | วิธีแก้เสนอ | ขนาด | ความเสี่ยง |
|---|---|---|---|---|---|---|---|---|
| S2-01 | P1 | `scripts/stages/voice_stage.py:695-697` (human 533-560, shot-list 569) | เสียงคนจริง: ซับช้ากว่าเสียงเท่าช่วงเงียบต้นไฟล์ (repro 1.16s); cue สุดท้ายเลยท้าย audio | cue ได้จาก `_rms_aligned_cues` บนไฟล์ก่อน trim; `trim_silence_and_tail_artifacts_wav` เขียนทับไฟล์ทีหลัง re-probe แค่ `total_duration` ไม่ลบ `head_t` | repro เงียบ 1.2s + 3 บรรทัด: cues (1.18,2.72)…(4.62,7.3), หลัง trim head 1.16 duration 5.42 แต่ cue ไม่ขยับ; `test_voice_stage_alignment_and_duration.py:241` assert `cues[0].start != 0` (เทสล็อกบั๊กไว้) | trim ก่อน align หรือ shift cue + `word_timings` ด้วย `-head_t` แล้ว clamp | S | ต่ำ |
| S2-02 | P1 | `voice_stage.py:688-697` | voice reuse + ผู้ใช้ ripple-cut แล้ว: `total_duration` หลังตัดถูกทับด้วยความยาวเต็ม; trim เปลี่ยน mtime → render ถัดไปถือว่า cut ของผู้ใช้ stale แล้วทิ้ง (**งานผู้ใช้หาย**) | trim รันหลัง `_apply_voice_edit` และแก้ไฟล์; edit ผูกกับ `voice_file_identity` (path,size,mtime_ns); trim ไม่ idempotent | 20 take สังเคราะห์: trim รอบ 2 เขียนไฟล์ใหม่ 9/20 (หาง 1–5ms) | ข้าม trim เมื่อ `voice_reused` / trim ครั้งเดียวตอนสร้าง + ทำให้ idempotent | S | ต่ำ |
| S2-03 | P1 | `scripts/tts_sanitizer.py:390-392` (`enforce_male_tone`) | คำไทยจริงพังทั้ง display และ TTS: `คะแนน→ครับแนน`, `จ้าง→ครับง`, TTS `หน้าจอ→หนะจอ` | regex substring `คะ`/`จ้า`/`น้า` ไม่มีขอบคำ; ตัวซ่อม `หนะจอ` อยู่แค่ display path | `"หน้าจอใหญ่ คะแนนเต็มสิบ จ้างช่างได้"` → display `"…ครับแนน… ครับงช่าง…"` | แทนเฉพาะคำลงท้ายวลี `(?<=\S)คะ(?=\s\|$\|[!?])`; ตัด/anchor `น้า→นะ` | S | กลาง |
| S2-04 | P1 | `scripts/api_voice.py:328-335` | `/api/script/ai-generate` เขียนข้อความ TTS-phonetic ลง display (`script_text`, `hook_title`, `caption`): `บลูทูธ`, `ยูเอสบีซี`, `5 กรัม`; hashtag ใน caption หาย (ผิดกฎ 9) | เรียก `TTSSanitizer.clean()` แทน `clean_display_text` | repro `clean("สาย USB-C … Bluetooth 5.3")` → `"สาย ยูเอสบีซี … บลูทูธ 5.3"`; prompt :262 ห้ามเรื่องนี้ตรงๆ | ใช้ `clean_display_text` / `process_angle` เก็บ `tts_lines` แยก | S | ต่ำ |
| S2-05 | P1 | `scripts/hook_generator.py:89`, `scripts/api_hooks.py:116-130` | apply hook `opening_line` ด้วย `update_script_first_line` → ข้อความทับศัพท์เข้า `script_lines[0]` = ซับ | `clean_opening = clean_text(TTSSanitizer.clean(raw))` แล้ว copy เข้าทั้ง display และ tts | อ่านโค้ด + กลไกเดียวกับ S2-04 | เก็บ display variant แยก, `tts_lines[0]` ใช้ `clean()` | S | ต่ำ |
| S2-06 | P1 | `tts_sanitizer.py:311-315, 59` | TTS อ่าน `5G` เป็น "5 กรัม" (4G ด้วย) | `_NUM_UNIT_PATTERN` ใช้ `re.IGNORECASE` → `G` ชน unit `g` | `"รองรับ 5G และ 4G"` → `"รองรับ 5 กรัม และ 4 กรัม"` | unit case-sensitive + เพิ่ม `5G/4G` ใน WORD_MAP | S | ต่ำ |
| S2-07 | P1 | `pipeline_context.py:609`, `api_schemas.py:33/55`, `api_render.py:186`, `api_phase1.py:1340`, `voice_stage.py:605`, `gemini_tts_engine.py:344`, `api_voice.py:162`; FE `lib/angleToForm.js:59-63`, `VoicePickerModal.jsx:34-41`, `ShotListModal.jsx:47` | tone default = `commercial_hype` ทุกที่ แต่ AGENTS §4.5 = `commercial_premium`; FE แปลง premium→hype ทิ้ง; voice default บางที่ Puck บางที่ Fenrir | spec กับโค้ด drift | อ่านโค้ด (`normalizeTone`, ternary ใน `angleToForm`) | **ต้องตัดสินใจ** source of truth แล้วรวมเป็น constant เดียว BE+FE | M | กลาง (เสียงเปลี่ยน) |
| S2-08 | P1 | `scripts/mobile_quick_studio.py:636` vs `config.py:147`; AGENTS §4.17, checklist:72, SOP:151 | BGM ไม่ตรงกัน: config/`sfx_manager`/`SequencePlayer AUDIO_MIX.BGM_GAIN`/EditorShell/AssetPanel = 0.12, Mobile Quick Studio = 0.14, เอกสาร gadget = 0.14 แต่ desktop gadget ไม่มี path ไหนใช้ | hardcode ทางเดียว ไม่ reconcile เอกสาร (Voice 1.0 / SFX 0.28 ตรงกันทั้ง preview+render) | grep | **ต้องตัดสินใจ** 0.12 หรือ 0.14 สำหรับ gadget แล้วทำเป็น style policy ที่ preview+render อ่านร่วม | S | ต่ำ |
| S2-09 | P2 | `scripts/voice_engine.py:256` | Edge-TTS `+15%` ส่งจริง `+14%` (`+20%`→`+19%`) | `int((1.15-1.0)*100)` float error | `python -c` ได้ `14 19 10` | `round()` | S | ต่ำ |
| S2-10 | P2 | `voice_engine.py:216-219, 318` | Edge stream หลุดกลางบรรทัด → MP3 ขาดถูกใช้เป็น take เต็ม ข้าม CLI fallback | partial file ไม่ถูกลบ caller เช็คแค่ `size==0` | mock edge_tts 1 chunk แล้ว raise: 1500B ถูกรับ | unlink `out_mp3` ใน except | S | ต่ำ |
| S2-11 | P2 | `voice_engine.py:337-344` | Edge ล้ม → gTTS เสียงผู้หญิง Google rate ปกติ แทรกกลางคลิปเงียบๆ | fallback ไม่สน gender/rate | อ่านโค้ด | ตัด gTTS หรือ flag cue แจ้งผู้ใช้ | S | ต่ำ |
| S2-12 | P2 | `voice_stage.py:599-619`, `quota.py:107` | ทุก key/model ได้ 429 แล้ว ยัง retry ทั้ง matrix อีกรอบ (request x2 บน quota ที่หมด) | `GEMINI_TTS_RATE_LIMITED` ไม่ใช่ `is_quota_error` | mock 429: 4 call/`generate_speech` ×2 | ข้าม outer retry เมื่อ code นี้ | S | ต่ำ |
| S2-13 | P2 | `scripts/gemini_tts_engine.py:105-120` | กฎตัด "EOF glitch" ท้าย take ตัดคำสุดท้ายจริงได้ (เช่น "ครับ") | heuristic แยก glitch กับคำสั้นไม่ได้ | พูด 2.0s, gap 80ms, คำ 300ms -12dB ไม่มีเงียบท้าย → ถูกตัดทั้ง 0.30s (เกิดเฉพาะไม่มีเงียบท้าย) | ตัดเมื่อ burst < ~120ms หรือเบา/เป็น noise กว่าเสียงพูดมาก | S | กลาง |
| S2-14 | P2 | `scripts/script_rules.py:325-326`, `couple_script_generator.py:94` | persona น้องนุ้ยทำคำพัง: `บังคับ→บังนะพี่บ่าว`, `คับแคบ→นะพี่บ่าวแคบ` | regex `คับ` ไม่มีขอบคำ | repro | anchor ท้ายวลี | S | ต่ำ |
| S2-15 | P2 | `voice_stage.py:471-512` | shot-list voice ถูก reuse แม้ `voice_rate`/`ad_tone` เปลี่ยน; script บันทึกว่างก็นับว่า match | reuse key มีแค่ preset/engine/script | อ่านโค้ด | ใส่ speed+ad_tone ใน key; script ว่าง = mismatch | S | ต่ำ |
| S2-16 | P2 | `config.py:136`, `pipeline_context.py:604`, `voice_engine.py:251`, `tts_sanitizer.clean()` | Edge default เสียงหญิง (Premwadee) แต่ข้อความถูกบังคับเป็น "ครับ"; preset หญิง Gemini (Kore/Aoede) ก็โดน | `enforce_male_tone` รันใน `clean()` ไม่ดูเพศเสียง | `clean("…ค่ะ ใช่ไหมคะ ดีจ้า")` → `"…ครับ ใช่ไหมครับ ดีครับ"` | ส่ง gender เข้า `clean()` หรือเปลี่ยน default เป็นชาย | S | ต่ำ |
| S2-17 | P2 | `voice_stage.py:540` | แปลงไฟล์เสียงคนล้มไม่ถูกเช็ค returncode | ไม่มี check | อ่านโค้ด | เช็ค + `AppError` ไทย | S | ต่ำ |
| S2-18 | P3 | `shot_matching_stage.py:50-52` | J-cut lead < 150ms เมื่อ cue สั้นกว่า 0.6s (`min(j, dur*0.25)`) | legacy clamp | อ่านโค้ด (J-cut 180ms อยู่ใน shot times ฝั่ง server → preview=render) | บันทึกข้อยกเว้นใน `j_cut_rules.md` หรือ floor 0.15 | S | ต่ำ |
| S2-19 | P3 | `cloud_runner.py:258,773`, `tools/align_pad_8_subtitles.py:18` | Whisper default `device="cpu"` (ผิดกฎ 21) | hardcode (pipeline หลัก `word_alignment.resolve_device` ถูกต้อง) | grep | ใช้ `resolve_device()` | S | ต่ำ |
| S2-20 | P3 | `voice_engine.py:518`, `gemini_tts_engine.py:695` (`__main__`) | self-test เขียนลง `02_Assets/Voiceover/` | demo code ค้าง | อ่านโค้ด | เขียน `.tmp/` | S | ต่ำ |
| S2-21 | P3 | `tts_sanitizer.py:156` vs `script_rules.py:70` | map ไทย→อังกฤษ (กฎ 9) 2 ชุดไม่ตรงกัน | duplicate | อ่านโค้ด | รวมเป็นชุดเดียว | S | ต่ำ |

คำตอบ checklist: "..." ถูกตัดหลายชั้นจนถึง `subtitle_engine.py:483-487` → ซับปลอดภัย แต่ยังค้างใน data/custom script (แค่ warning) · กฎ 9 enforce หลัง generate เฉพาะ `process_angle`/couple; AIBridge ใน script_stage พึ่ง prompt อย่างเดียว; custom script ไม่เช็ค · J-cut 180ms ใน `shot_matching_stage` (window 150–250ms) preview อ่าน shot times เดียวกัน · Gemini ไม่ fallback Edge (by design); Edge line fail ใส่ silence ตามเวลา (มีเทส) · cache key preview ไม่ชน

ยังไม่ยืนยัน: FE preview render `cue.text` ดิบที่ไหนอีกไหม · hook fields จาก `/hooks/apply-project` เก็บดิบ ไม่ strip "…"/emoji · Gemini คืน audio สั้นผิดปกติไม่มี plausibility check · เน็ตล่ม worst-case ~30 นาที (2 model × N key × 2 × 75s × 2) — คำนวณ ไม่ได้รัน · `_trim_silence` -42dB ตัดตัวสะกดไทยเบาๆ

---

## 3. ด่าน 3 — Auto-cut (shot matching / source resolution / assembly)

| ID | Sev | ไฟล์:บรรทัด | อาการ | สาเหตุ | หลักฐาน | วิธีแก้เสนอ | ขนาด | ความเสี่ยง |
|---|---|---|---|---|---|---|---|---|
| S3-01 | P1 | `scripts/stages/shot_matching_stage.py:1455-1467` (group 1077-1096, split 1271-1286) | **Strict Topic Hold พังเมื่อไม่มี AI match**: ประโยคเดียว 8s กลายเป็น 4 ช็อตจากฟุตเทจคนละช่วง | ชิ้นที่ split จากประโยคเดียวกันเรียก `_compute_smart_fallback_offset(g_idx)` แยกกัน กระจาย offset ทั้งไฟล์; cut-in zoom (1544) ใส่บนฟุตเทจไม่ต่อเนื่อง | repro raw 60s: trims 0.8→2.97, 15.61→17.61, 29.22→31.22, 44.96→46.79 | ถ้า group ก่อนหน้าเป็นประโยคเดียวกัน → ต่อจาก `prev raw_offset + prev duration` | S | ต่ำ |
| S3-02 | P1 | `shot_matching_stage.py:551-552, 579-583, 1452` | raw สั้นกว่าเสียง → ช่วงสั้นเดิมซ้ำติดกัน + ขอฟุตเทจเกินความยาวจริง ไม่มี `hold_reason` | `max_start<=0.5` คืน 0.0; anti-duplicate ทำงานเฉพาะ `max_start>=4`; legacy AI path clamp ผิด | raw 1.5s/เสียง 8s: 4 คลิป trim 0→2.0–2.17 (เกิน 1.5s); raw 3s คลิป 2,3 = 0→2.0 เหมือนกัน | ส่ง raw สั้นผ่าน `SourceWindowLedger` (เล่นครั้งเดียวแล้ว hold + notify), cap `trim_end ≤ raw_duration`, guard ห้าม trim ซ้ำติดกัน | M | กลาง |
| S3-03 | P1 | `scripts/video_editor.py:2246, 2333-2336, 2356` | ช็อตที่ source หมดก่อน → จบเร็วเงียบๆ จุดตัดถัดไปเลื่อนก่อนเสียงทั้งคลิป ท้ายค้างภาพ | per-clip pad แค่ 3 เฟรม; seek เกินท้าย = 0 เฟรม exit 0; `tpad` ท้ายบังอาการ | ffmpeg: source 1s `-ss 0.5 -t 2` แผน 60 เฟรม ได้ 18 (รวม 78/120); `-ss 5` ได้ 0 เฟรม exit 0 | pad ถึงจำนวนเฟรมที่วางแผน (`stop=-1` ก่อน `trim end_frame`) + warning ไทย หรือ fail ถ้าขาด >3 เฟรม; preflight `trim_end ≤ duration` | S | กลาง |
| S3-04 | P1 | `video_editor.py:1662-1715`, `shot_matching_stage.py:871-876`, `source_resolution.py:79-81` | raw เสีย/probe ไม่ได้ ยังถูกวางแผน: truncated = 0.0s, probe timeout = **แต่ง 60.0s** | fallback ไม่สม่ำเสมอ, เช็คแค่ size <1024B | `get_media_info`: truncated 0.0, missing 0.0, timeout (mock) 60.0 | probe fail → None/raise; SourceResolution ปฏิเสธ `duration<=0` ด้วย `AppError` ไทย | S | ต่ำ |
| S3-05 | P1 | `shot_matching_stage.py:1757-1765` (+builder ~790-794) | manual pin สั้นกว่า 1/4 beat → คลิปสั้นกว่าแผน beat ถัดไป drift | speed clamp 0.25 แต่ duration = target; ไม่มี `trim_end` → span 0.05 | pin 0–0.5s ใน beat 4s: แผน 4.0 render 2.0; ไม่มี trim_end: render 0.8 | clamp แล้วใส่ `freeze_tail`/loop ส่วนที่เหลือ; reject `trim_end<=trim_start` | S | ต่ำ |
| S3-06 | P1 | `shot_matching_stage.py:632-646, 670-674, 712-722` | guided-take/proportional ทิ้งช่วงเงียบระหว่าง beat → ภาพนำเสียง ตัดหนีก่อนจบประโยค | `_beat_slot_durations` ใช้ `end-start` ของ cue แต่คลิปต่อกันจาก t=0 | beats 0.3–2.0 / 2.5–4.0 / 4.6–6.0: ภาพ 0–1.7 / 1.7–3.2 / 3.2–4.6 (beat 3 มาก่อน 1.4s, รวม 4.6 vs 6.2s); เทสเดิมไม่มี gap | ใช้ `calculate_contiguous_beat_durations` หรือรวม gap เข้า slot ข้างเคียง | S | กลาง |
| S3-07 | P1 | `scripts/api_phase1.py:1184, 1374`, `shot_matching_stage.py:879` | reroll voice/script ใช้ cut plan เก่า → จุดตัดไม่ตามประโยคใหม่ ท้ายค้าง/ตัดภาพขาด | reroll copy `clip_list` เดิมทุก stage; ShotMatching ถือเป็น manual แล้วข้ามการวางแผน | pytest audit: `_execute_reroll(...,"voice",{})` ส่ง `resume_from="voice"` + clip_list เก่า | reroll ≤ voice → ทิ้ง clip_list ที่ auto-generated (flag `auto_generated`); ของ user เก็บไว้ + เตือน | S | กลาง |
| S3-08 | P2 | `frontend/src/lib/timelineMath.js:157-163`, `editorProjectState.js:142`, `timelineSchema.js:317` vs `video_editor.py:1867-1869` | preview vs render ความยาวคลิปไม่ตรงเมื่อ speed นอก 0.25–4 | preview ไม่ clamp, render clamp; `PATCH /clips` รับ dict ใดก็ได้ | node: speed 8 → preview 1.0/render 2.0; 0.1 → 80/32; -2 → 0.2/32 | clamp ใน `clipDuration` + ตอน load + validate `UpdateClipsRequest` | S | ต่ำ |
| S3-09 | P2 | `video_editor.py:2103-2109` (vs 2187) | raw แนวนอนใน auto-cut ถูก center-crop 9:16 เสียความกว้าง ~68% สินค้าไม่อยู่กลางโดนตัด | blur-pad มีแค่ legacy path; ShotMatching ไม่ตั้ง `fit_mode` | อ่านโค้ด | ตั้ง `fit_mode:"blur"` เมื่อ w>h | S | ต่ำ |
| S3-10 | P2 | `scripts/motion_analyzer.py:125,147` | ฟุตเทจ VFR (มือถือ) เวลา motion ผิด → snap/hook hero/fallback peak ผิดจุด | `frame_idx / CAP_PROP_FPS` | VFR 30→10fps: OpenCV 17.05fps; เฟรม 60 จริง 2.0s คำนวณได้ 3.52s | `CAP_PROP_POS_MSEC` ต่อเฟรม | S | ต่ำ |
| S3-11 | P2 | (ไม่มีใน pipeline) `tools/full_export_audit.py:111` เท่านั้น | ไม่มีเช็คเฟรมดำ/ภาพค้างตอน auto-cut/render | `STILL_MOTION_THRESHOLD` ใช้แค่ snap/hook | grep `blackdetect/freezedetect` เจอแค่ offline tool | ข้ามหน้าต่าง motion ต่ำ + post-render warning `blackdetect/freezedetect` | M | ต่ำ |
| S3-12 | P2 | `scripts/background_isolation_video_worker.py:325,345` | cache SAM 2 cutout เสีย → ติดถาวร (ข้อความอังกฤษ "rebuild" แต่ไม่มี route rebuild) | fail-closed ไม่มีทาง reclaim | repro checksum ผิด → RuntimeError ทุกครั้ง | quarantine แล้ว rebuild หรือ DELETE route + ข้อความไทย | S | ต่ำ |
| S3-13 | P2 | `scripts/cutout_runtime.py:67-86` | CUDA probe ล้ม/timeout ถูก cache จน restart server | `lru_cache` เก็บผล error ด้วย | อ่านโค้ด | ไม่ cache ผลที่มี error | S | ต่ำ |
| S3-14 | P2 | `scripts/stages/source_resolution.py:36-41, 83-89` | raw path เก่า → เลือก `RAW_DIR/**/<basename>` ตัวแรก อาจเป็นไฟล์สินค้าอื่น (กฎ 13); clip_list ไฟล์หายถูกข้ามเงียบ | `glob()[0]`; `if c_path.exists()` | อ่านโค้ด | match >1 → fail; ไฟล์หาย → `FileNotFoundError` ไทย | S | ต่ำ |
| S3-15 | P3 | `source_resolution.py:69` | ลำดับ slideshow ภาพขึ้นกับ filesystem | `iterdir()` ไม่ sort | อ่านโค้ด | `sorted()` | S | ต่ำ |
| S3-16 | P3 | `scripts/script_tone_analyzer.py:57-62`, `motion_analyzer.py:62-91` | cache ใน `02_Assets` read-modify-write ไม่มี lock ขณะ render 4 งานพร้อมกัน; tone cache `write_text` ไม่ atomic → ไฟล์ขาด → transition ต่างกันรอบต่อรอบ | ไม่มี lock/atomic | อ่านโค้ด | Lock + `mkstemp`/`os.replace` | S | ต่ำ |
| S3-17 | P3 | `video_editor.py:2945,2990`, `background_isolation_sam2_worker.py:126` | error ffmpeg/SAM 2 เป็นอังกฤษ (กฎ 6) | hardcode | อ่านโค้ด | ข้อความไทย + เก็บ stderr ใน details | S | ต่ำ |

ผ่าน: SAM 2 `device="cuda"` ไม่ hardcode cpu + error ชัดถ้าไม่มี CUDA · temp frames ลบใน `finally` · cutout cache key ครอบ fingerprint/model/prompt/interval · mp4 ค้างถูกลบเมื่อ render ล้ม · ไม่มี audio track รองรับ (`video_editor.py:2116`) · AI window เล่นครั้งเดียวแล้ว hold พร้อม `hold_reason` · ไม่มี random ไม่ seed · planning error เป็น `AppError` ไทย

ยังไม่ยืนยัน: `coalesce_short_windows` ต่อฟุตเทจข้างเคียงอาจข้ามหัวข้อ (ขึ้นกับเนื้อหา) · S3-03 พิสูจน์ด้วย filter graph เทียบเท่า ไม่ใช่ `assemble_tiktok_video` เต็ม · motion cache key (md5 size + 8MB แรก) อาจชนกับไฟล์ re-export · `image_motion_footage.mp4` ค้างเมื่อ Image-Motion ล้ม

---

## 4. ด่าน 4 — Editor (Frontend)

**UNC** = มาจาก diff ที่ยังไม่ commit ของ Antigravity · **COM** = โค้ดที่ commit แล้ว. เทสเดี่ยวที่รัน: immersive contract, projectAutosave, projectSaveQueue, editorShortcutKeys 43/43 · timelineTrimOps, timelineMath, editorHistory, projectRevision 74/74. **ข้อสังเกต:** `editorImmersiveStudioContract.test.js` เช็คแค่ว่ามี string ในซอร์ส จับบั๊กพฤติกรรมด้านล่างไม่ได้เลย

| ID | Sev | ไฟล์:บรรทัด | อาการ | สาเหตุ | หลักฐาน | วิธีแก้เสนอ | ขนาด | ความเสี่ยง |
|---|---|---|---|---|---|---|---|---|
| S4-06 COM | P1 | `EditorShell.jsx:1770-1780` vs `lib/editorShortcutKeys.js:129` / `hooks/useEditorShortcuts.js:125` | กด F ตอนเลือกคลิป (ไม่ใช่คลิปแรก) → สลับ immersive **และ** สลับ `transition_in` cut↔fade ของคลิปเงียบๆ → **ผลเรนเดอร์เปลี่ยน**; F ไม่สน modal; Esc ครั้งเดียวทั้งปิด modal/ล้าง selection **และ** ออก immersive | window keydown 2 ตัวแย่ง key เดียว; handler immersive ไม่เช็ค editable target / `[role=dialog]` / `defaultPrevented` | F handler อยู่ใน HEAD ตั้งแต่ 5238c55; cheat sheet map F = toggleFade อย่างเดียว (`editorShortcutKeys.js:212`) | ย้าย immersive เข้า `classifyShortcut` ใช้ปุ่มอื่น (Shift+F หรือ `\`) + guard เดียวกัน; Esc ออก immersive เฉพาะเมื่อไม่มี Esc action ลำดับสูงกว่า | M | ต่ำ |
| S4-08 UNC | P1 | `EditorShell.jsx:~2686-2696` (mini capsule) | mini capsule โชว์จุด**เขียวกระพริบ**เสมอ แม้ dirty/error/409 — จอ <768px ใช้ mini เป็น default → ผู้ใช้มือถือไม่เห็นสถานะเซฟจริง (ผิดกฎ สถานะตามจริง) | hardcode `bg-emerald-400 animate-pulse` ไม่ผูก `saveStatus` | อ่านโค้ด | สีตาม `saveStatus` + aria-label หรือใช้ `SaveStatusChip` compact | S | ต่ำ |
| S4-01 UNC | P2 | `EditorShell.jsx:1760-1785` | มือถือ: ลากปรับพรีวิวแล้วกด F → ทำกลับด้าน (พรีวิวหด + navbar ซ่อน) | effect อ่าน `mobilePreviewH`, `isMobileView`, `handleToggleMobileFullPreview` แต่ deps มีแค่ `[handleManualSave, isImmersive, onToggleImmersive]` → stale closure; ตัวแปรประกาศหลัง (~2510) | oxlint `exhaustive-deps` error ที่ 1767 | ย้าย effect ลงใต้ `usePanelLayout` หรืออ่านผ่าน ref | S | ต่ำ |
| S4-02 UNC | P2 | `EditorShell.jsx:2514-2526, ~2650`; `hooks/usePanelLayout.js:154-165` | "ย่อพรีวิว"/ปุ่ม "แสดงแถบ"/Esc อาจขยายพรีวิวเต็มแทน พร้อมออก immersive | เกณฑ์ "ขยายอยู่ไหม" 2 แบบ: Shell `prev >= innerHeight*0.55` vs hook `prev >= maxH*0.75` (maxH โตใน immersive) | จำลอง innerHeight 844: immersive พรีวิว 470/520/590 → immersive OFF + โตเป็น 792 | ฟังก์ชัน pure เดียว `isPreviewEnlarged(prev, box, ih)` ใน usePanelLayout | S | ต่ำ |
| S4-03 UNC | P2 | `EditorShell.jsx:2999-3003, 3249`; `usePanelLayout.js:144-151` | "Full preview" ไม่เต็มจริง; ตัวจับลากไม่ตาม pointer | clamp เลิกกันที่ให้ timeline (`reserve` กลายเป็น dead) แต่ flex หดทั้งคู่ตามสัดส่วน; คอมเมนต์ที่ถูกลบอธิบายบั๊กนี้เอง ("crushed the tracks to 82px") | Chromium จำลอง: box 700 ตั้ง 648 → แสดงจริง **438px** / timeline 196 | full-preview: timeline `flex: 0 0 0`; โหมดปกติคืน reserve | M | กลาง |
| S4-04 UNC | P2 | `EditorShell.jsx:4133-4147` (ใน separator 4086-4090) | ปุ่ม "ขยายไทม์ไลน์" คลิกเมาส์ไม่ทำงาน | อยู่ใน separator ที่ `setPointerCapture` ตอน pointerdown | Playwright Chromium: click ไปที่ separator, handler ปุ่มไม่รัน | ย้ายปุ่มออกนอก separator หรือ stopPropagation `onPointerDown` | S | ต่ำ |
| S4-05 UNC | P2 | `EditorShell.jsx:4065-4066` | ลาก timeline desktop หน่วงตาม pointer | `transition-all duration-150` บน container ที่ height เปลี่ยนทุกเฟรม | อ่านโค้ด | ใส่ transition เฉพาะตอน collapse/expand | S | ต่ำ |
| S4-07 COM | P2 | `SequencePlayer.jsx:4846-4855` vs `4038-4047` | effect `.webm` (loop) ยัง decode ต่อหลังปิด editor/เปลี่ยนโปรเจกต์ (memory/CPU leak) | map เก็บ `<video>` ตรงๆ แต่ teardown เช็ค `item?.video` = undefined | `syncEffectVideos` ใช้ค่าเป็น video element (1762) | `const v = item?.video ?? item; v.pause(); v.removeAttribute('src'); v.load()` | S | ต่ำ |
| S4-09 COM | P2 (a11y) | `Sidebar.jsx:191-194` | bottom nav ซ่อนใน immersive แต่ 5 ปุ่มยังอยู่ใน Tab order | ซ่อนด้วย translate/opacity/pointer-events | อ่านโค้ด | `inert={isImmersive}` + `aria-hidden` | S | ต่ำ |
| S4-10 COM | P2 | `App.jsx:1364-1366`, `Sidebar.jsx:192`, `index.html:9` | immersive บนมือถือมี notch/home indicator: แท็บล่าง + scrollbar timeline อยู่ใต้ home indicator; capsule บนไม่เผื่อ inset-top | `pb-0` ตัด `--nav-h` ที่เป็นที่เดียวที่มี `env(safe-area-inset-bottom)` | grep EditorShell ไม่มี safe-area | `pb-[env(safe-area-inset-bottom)]` ตอน immersive; capsule `top-[calc(env(safe-area-inset-top)+0.625rem)]` | S | ต่ำ |
| S4-11 COM | P2 | `EditorShell.jsx:2724` | แจ้งเตือน channel watermark แสดง `????????…` แทนไทย | string ไทยเสียเป็น `?` ตอน commit 0269099 | `git show HEAD:` มี `?` จริง (ที่เดียวใน `frontend/src`) | คืนข้อความไทย | S | ไม่มี |
| S4-12 UNC | P3 | `EditorShell.jsx:3160-3183` | separator พรีวิวมือถือมี `title`/`aria-label` ซ้ำ; `tabIndex=0` ไม่มี keyboard handler; สี active เช็ค `activeSplitter==='mobilePreview'` ที่ไม่เคย set | copy/paste | oxlint `jsx-no-duplicate-props` 3165/3166 | ลบซ้ำ + ArrowUp/Down + `aria-valuenow` + set/clear activeSplitter | S | ไม่มี |
| S4-13 UNC | P3 | `ProjectSelector.jsx:169`, `EditorHeader.jsx:223` | selector กว้างกว่าที่ 640–767px มากกว่า 768px; view toggles ซ่อนใต้ xl → focus-mode เข้าไม่ได้ที่ 1024–1279px | breakpoint ใน diff | อ่าน class | `sm:min-w-[160px] lg:min-w-[180px]` + ใส่ Focus mode ใน HeaderMenu | S | ไม่มี |
| S4-14 COM | P3 | `EditorShell.jsx:1763`, `hooks/useProjectAutosave.js:308` | Ctrl+S เซฟล้ม (network/409) → unhandled promise rejection | ไม่มี `.catch` | อ่านโค้ด | `handleManualSave()?.catch(() => {})` | S | ไม่มี |
| S4-15 COM | P3 | `ActivityCenter.jsx:1006-1019` | polling render 1s ไม่มี in-flight guard (request ซ้อน); error ครั้งเดียวหยุด poll ถาวร; `setTimeout` 4s ไม่ clear ตอน unmount | เขียนเป็น interval | อ่านโค้ด (fallback TaskManager → กระทบต่ำ) | self-scheduling timeout + retry/backoff + clear | S | ต่ำ |

ผ่าน: autosave 409 → `error` + ProjectRevisionNotice (เห็นใน immersive); network fail คง `dirty` retry แล้ว `error` หลัง 2 ครั้ง; save ที่ถูก supersede ไม่ทับ; สลับโปรเจกต์ใช้ `setBaseline`/`discard` + invalidation generation; `useProjectLoader` guard ด้วย sequence · wheel listener `{passive:false}` ไม่มี warning; ruler `sticky top-0` · rAF playback cancel ตอน cleanup; history cap 50

ยังไม่ยืนยัน: immersive จำใน localStorage global (`omnicut_editor_immersive` ไม่แยกช่อง) + capsule ยุบ default บนมือถือ → กลับมาเจอ editor ไม่มี header (design call) · notch overlap ต้องใช้ iOS จริง · header ล้นที่ 360px ยังไม่ render · timeline ยุบ desktop ล้น 4px · wheel อาจสลับเป็นแนวตั้งเมื่อ overflow 1px

### `frontend/dist` — แนะนำเลิก track แล้ว build ตอน deploy (ผู้ใช้ตัดสินใจ, ไม่ลบเอง)

- ถูก un-ignore ใน 4b498df ("Cloudflare Tunnel launch") — `.gitignore` ทั้ง 2 ไฟล์ comment บรรทัดไว้; track อยู่ 48 ไฟล์ (~17MB)
- ใช้โดย `scripts/api_server.py:345-411` (serve `DIST_DIR`, `/assets` immutable, SPA fallback); launcher local `tools/launch_omnicut.ps1:72` ใช้ `npm run dev` → dist จำเป็นแค่ cloud/FastAPI-only
- ปัญหา: ทุก commit ฟีเจอร์ churn ~30 ไฟล์ hash; **ตอนนี้ dist ใน tree build จากซอร์สที่ยังไม่ commit** → commit ไปเท่ากับส่งโค้ดที่ไม่อยู่ใน git; merge conflict ใน bundle แก้ไม่ได้; `sw.js` churn
- ทางเลือก A (แนะนำ): เปิด `frontend/dist/` ใน .gitignore + `git rm -r --cached frontend/dist` + เพิ่ม `npm ci && npm run build` ใน cloud runner (หรือ CI artifact)
- ทางเลือก B (ถ้า cloud รัน Node ไม่ได้): track ต่อ แต่ commit dist เฉพาะ commit `build: dist from <sha>` จาก tree สะอาด ห้ามปนกับ commit ฟีเจอร์
---

## 5. ด่าน 5 — ซับ / Callout / Preview = Render

เทส parity ที่รัน (.venv): `test_preview_render_parity`, `test_preview_render_behavior`, `test_subtitle_artifact_contract`, `test_overlay_model`, `test_thai_chunking`, `test_thai_clause_wrap`, `test_product_callout_builder`, `test_hook_line` = **357 pass / 0 fail**. ค่าคงที่ร่วม 14 ตัว `overlay_model.py` ↔ `overlayModel.js` ตรงกันหมด. **แต่เทสจับ S5-01 ไม่ได้** เพราะ `conftest` ชี้ data root ชั่วคราวแล้ว build registry ใหม่

| ID | Sev | ไฟล์:บรรทัด | อาการ | สาเหตุ | หลักฐาน | วิธีแก้เสนอ | ขนาด | ความเสี่ยง |
|---|---|---|---|---|---|---|---|---|
| S5-01 | **P0** | `scripts/asset_registry.py` `_compute_cache_is_fresh` (~292-306) + `scripts/subtitle/font_metrics.py:216-232` | **ทุก render ใน workspace นี้ซับเล็กลง ~40%**: `TikTokWhite` Fontsize **50** แทน **82** (em ~30px vs 50px ใน preview); hook/watermark/SpecBar หดตาม; **hook line หายเงียบ** (`_fit_size_pct` คืน None); ghost-reveal anchor ใช้ width ประมาณ (ซับเยื้องซ้าย) | cache `02_Assets/asset_registry.json` (gitignored, build 2026-09-26) เก็บ absolute path `D:\Winona\Programmer\Capcut\02_Assets\...` — โปรเจกต์ย้ายมา `Omnicut` แล้ว; freshness เทียบแค่ mtime → ถือว่าสด; font 27/27 path หาย → `_sfnt_ass_vertical_metrics` OSError → scale = 1.0 เงียบ (อาการเดียวกับ FONT-SIZE-REGRESSION-2) | **ยืนยันซ้ำโดย main agent:** registry มี path `Capcut` 1,958 จุด, `ass_glyph_scale('IBM Plex Sans Thai')=1.0`; agent: ASS ได้ `TikTokWhite,...,50`, registry ใหม่ใน temp ได้ 82 (Mali 106, Prompt 76); hook fit stale → None×3, fresh → 166/166/182; เฟรม stale ซับเล็ก+เยื้องซ้าย; โปรเจกต์จริงล่าสุด (2026-09-27) ยังเป็น 82/106 → พังหลังย้ายโฟลเดอร์ | (a) freshness ต้องเช็คว่า path มีจริงและอยู่ใต้ `FONTS_DIR` ปัจจุบัน หรือเก็บ `rel_path` แล้ว resolve ตอน load (b) rebuild cache 1 ครั้ง (ไฟล์อยู่ใน `02_Assets` → **ต้องขออนุญาตผู้ใช้**) (c) S5-02 | S | ต่ำ |
| S5-02 | P1 | `font_metrics.py:216-232`, `subtitle/word_layout.py:72-120`, `scripts/hook_line.py:230-233` | font หาย → ถอยเงียบเป็น scale 1.0 / width ประมาณ 0.55×/0.62× / ทิ้ง hook | `except` กว้าง → ค่า default; ขัด font_text_visual_contract §3/§5.3 ("ห้าม fallback 1.0 แบบเงียบ") | อ่านโค้ด + reproduce ผ่าน S5-01 | raise / log error ไทยแล้ว fail subtitle stage เมื่อ font path หาย | S | กลาง (จะเห็น failure ที่ซ่อนอยู่) |
| S5-03 | P1 | `subtitle_engine.py:883` (SpecBar style), `:1480` | SpecBar (`on_screen` spec) burn ออกมาเป็น**กล่องดำทึบ ตัวหนังสือมองไม่เห็น** | `BorderStyle=3` libass ทาสีกล่องด้วย **OutlineColour** (`&H00000000`) ไม่ใช่ BackColour; ตัวหนังสือก็ดำ | เฟรม: crop ดำทั้งกล่อง pixel (990,410)=`0 0 0`; เทสเดิมเช็คแค่มี Dialogue | OutlineColour = `&H0000E6FF` หรือ BorderStyle 1 + ตัวขาว + pixel test | S | ต่ำ |
| S5-04 | P1 | `subtitle_engine.py` reveal companion (~1335-1390), `ghost_reveal_ass.py:61-68`; preview `SequencePlayer.jsx:1524-1536` | คำที่**กำลังพูด** (เขียว 114%): วรรณยุกต์แยก (`ที่`,`นี่`,`เปลี่ยน`,`นั่ง`) render เป็น**สีขาว**และจม/ทับสระบน; `นั่ง` ไม้หันอากาศหาย | companion tone event วางที่ scale 100% สี style ขาว ไม่มี `\c&H0000FF66&` / `\fscx114` ขณะตัวคำ pop จากขอบซ้าย (`\an1`); preview scale รอบกลางคำสีเขียว → render ผิด + ไม่ตรง preview | เฟรม t=0.20/1.90/3.10 ซูม 4×: ขีดขาวบน ี/ั สีเขียว | emit companion ของคำ active ด้วยสี+scale active วางตาม glyph ที่ scale แล้ว หรือ `ACTIVE_SCALE_PCT` 100 สำหรับคำที่มีวรรณยุกต์แยก; ให้ origin scale ของ preview ตรง libass | M | กลาง (geometry วรรณยุกต์ไทย) |
| S5-05 | P1 | `subtitle/word_reveal.py:177-180`, `ghost_reveal_ass.py:239-244` | คำสุดท้ายค้าง**เขียว 114% จนจบ cue** ไม่มีช่วง settle ขาวล้วนตามกฎ 17 | `reveal[-1].end` ถูกบังคับ = `cue_end` → เงื่อนไข `cue_end > last_end` ไม่เคยจริง (คอมเมนต์บอกตรงข้าม) | ASS: event สุดท้าย 5.41–5.71 / 5.71–6.00 คำสุดท้าย active ไม่มี settle | จบคำสุดท้ายที่เวลาพูดจริง (หรือ `MIN_WORD_DUR`) + mirror ใน `ghostRevealSegments` | S | ต่ำ |
| S5-06 | P1 | preview `SequencePlayer.jsx:1347-1355,1421`; render `subtitle_engine.py:533` | scale/position/fontName ต่อซับที่ตั้งใน `CaptionInspector` เห็นใน preview แต่**render ไม่สน** (ผิด Preview=Render) | `generate_micro_cues` copy `position`/`scale` แต่ `generate_ass` ไม่อ่าน (อ่านแค่ x/y); `fontName` ทิ้ง | grep: ไม่มี `cue.get("scale"/"position"/"fontName")` ใน engine | apply ใน `generate_ass` หรือซ่อน control ใน inspector | M | กลาง |
| S5-07 | P1 | `SequencePlayer.jsx:1042` vs `subtitle_engine.py:183-187` | ซับตำแหน่ง **top**: preview ต่ำกว่า render 80px (260 vs 180 /1920) | mirror มือ drift คอมเมนต์เก่า | ASS `\an7\pos(...,180.0)` vs JS `top: 260/1920`; `CAPTION_Y`/`CAPTION_POSITIONS` ไม่มีเทส | JS = 180/1920 + parity assert | S | ต่ำ |
| S5-13 | P1 | `tools/render_sample_gadget_clip.py:136,246`, `tools/generate_precision_ass.py:105` | badge ช่องปลอม "TECH MX" hardcode/เป็น default (กฎ 17) | โค้ด tool เก่า | grep (production `scripts/` สะอาด มีแค่คอมเมนต์ `subtitle_engine.py:927`) | ลบ default + literal | S | ต่ำ |
| S5-08 | P2 | `SequencePlayer.jsx:1355-1365` | ซับ Kanit: preview weight 900 vs render Bold(700); Prompt 800 vs Bold | `ass_caption_face` ให้ Bold=1 → 700; แก้ Mali แล้วแต่ Kanit/Prompt ยัง | libass probe: `Kanit` Bold=1 ink 13808px width 469; `Kanit Black` 16881px width 487 | preview weight 700 + parity test | S | ต่ำ |
| S5-09 | P2 | `SequencePlayer.jsx:1517-1520` vs `subtitle_engine.py:1428-1434` | preview วาด drop shadow ใต้ ghost-reveal; render ไม่มี soft-shadow สำหรับ reveal cue (default ของ cue หลายคำ) | engine ตั้งใจตัด preview ไม่ mirror | ASS ไม่มี `TikTokSoftShadow` สำหรับ reveal | preview ข้าม shadow เมื่อ reveal | S | ต่ำ |
| S5-10 | P2 | `SequencePlayer.jsx:368,2395-2399` vs `subtitle_engine.py:174,711-716,886` | watermark ต่าง 3 จุด: alpha 0.40 vs 0.373; outline 2.1 vs 3.4px; preview ล็อก IBM Plex 600 แต่ render ใช้ font ซับ | mirror มือ ไม่มีเทส | style `Watermark,IBM Plex Sans Thai SemiBold,68,...,3.4` | ปรับให้ตรง + parity assert | S | ต่ำ |
| S5-11 | P2 | `subtitle_engine.py:199-206` `_format_ass_time` | 367/1000 เวลา centisecond ถูกเขียนเร็ว 10ms (0.29→`0.28`) ไม่ตรง `ghost_reveal_ass._ass_time` (round) → วรรณยุกต์ companion กับตัวคำจบต่าง cs (4.81 vs 4.82) กระพริบ 1 เฟรมได้ | `int((s-int(s))*100)` float truncation | script เทียบ 2 formatter | `round(s*100)` integer ใน formatter กลางตัวเดียว | S | ต่ำ |
| S5-12 | P2 | `subtitle_engine.py:538-551` | `generate_micro_cues` เรียก GoogleTranslator ทุกครั้งแม้ `bilingual=False` → network latency + nondeterminism ทุก render | แปลไม่มีเงื่อนไข | อ่านโค้ด (ต้อง monkeypatch ถึงจะรัน offline ได้) | ส่ง `bilingual` เข้าไป ข้ามเมื่อปิด | S | ต่ำ |
| S5-14 | P2 | `subtitle_engine.py:883` | SpecBar ชิดขวาบน (MarginR 50, MarginV 380) กล่อง x≈922–1060 ทับ rail ปุ่ม TikTok ขวา (960–1080, y 180–1500) | Alignment 9 + margin 50 | เฟรม + safe-zone overlay | ย้ายซ้ายของ x 960 (MarginR ≥130) หรือกึ่งกลาง | S | ต่ำ |
| S5-15 | P3 | `subtitle_engine.py:263-345` | มี burst คำเดียว (`กล้อง` 0.56s) กฎให้ 2–4 คำ | tail ≥5 ตัวอักษรไม่ถูก merge | micro-cue output | merge token เดี่ยวท้ายเข้าวลีก่อนหน้าถ้ายังพอดี | S | ต่ำ |
| S5-16 | P3 | `config.py:128-129`, `subtitle_engine.py:623`, `stages/subtitle_stage.py:18-27`, `product_callout_builder.py` | `DEFAULT_FONT_NAME="Kanit"` ไม่ได้ใช้; engine default "Kanit" แต่ pipeline ใช้ "IBMPlex"; auto callout ปิดอยู่ `build_product_callouts` import แต่ตาย; `source_credit`/`channel_badge` pipeline ไม่เคยส่ง | ของค้าง | grep | ลบหรือทำให้ตรง | S | ต่ำ |

### กฎขัดกันเอง — โค้ดใช้ค่าไหนจริง (ต้องให้ผู้ใช้ตัดสินใจ)

1. **ขนาด/ตำแหน่งซับ:** production `scripts/` ใช้ตามกฎข้อ 3/12 + font contract: IBM Plex Sans Thai SemiBold (default pipeline), em 50px (ASS 82 IBM / 106 Mali), outline `max(1.8, 0.04·fs)` = 2.0px, MarginV 420 (render 410 optical), L/R 60, EN 68% `#EAEAEA`. ส่วนข้อ 17 **Mali-Bold 88 / outline 5.2 / MarginV 380** มีแค่ใน `tools/*.py` one-off — และ "88" ใน tools เป็น ASS Fontsize = em **41.5px** เล็กกว่า golden master 50px. `subtitle_kinetic_rules.md §3` เป็นชุดที่ 3 (outline 5.5 / shadow 2.5 / 78–84px / EN 55%) → ต้องเลือกสเปกเดียว และนิยามว่า "88px" คือ ASS Fontsize หรือ em
2. **สีไฮไลต์:** Ghost Reveal (ข้อ 17: `#66FF00` 114%, พูดแล้ว `#FFFFFF`) **เปิด default** และ**ลบไฮไลต์ keyword ข้อ 3 ทั้งหมด** (`#FFE600`/`#00E5FF`/`#FF3B30`) — ยืนยัน: cue เดียวกัน `ghost_reveal=False` มีเหลือง, `True` ไม่มี; Kinetic Pop (`\fscx125→100`) ถูกแทนด้วย alpha fade 70ms (กันวรรณยุกต์เพี้ยน) → keyword ควรคงเหลืองใต้ reveal ไหม
3. **Callout 2 ชั้น** (ข้อ 17: Prompt-Bold 76 ขาว MarginV 250 + Prompt-Black 94 `#FF6622` MarginV 530) **ไม่มีใน `scripts/` เลย**; product callout เป็น Kanit ชั้นเดียว y=0.5 และปิด auto; SpecBar legacy ดำ/เหลือง (S5-03). Golden master ที่ checklist อ้าง `tools/build_60s_mali_burst_ass.py:483-488` เองก็ขัดข้อ 17 (header Prompt 44 **เขียว** MarginV 170, metric Prompt-Black 72 **ขาว** MarginV 230, Spacing 3/1 ขณะ parity test บังคับ 0) → callout 2 ชั้นเป็น requirement ของ pipeline หรือ legacy
4. **Source Attribution:** กฎ Prompt 24px MarginV 36; โค้ด font ซับ Fontsize 26 ไม่ boost (em ≈16px), `\pos` 35px จากล่าง — ไม่ได้ wire เข้า pipeline และ preview ไม่วาด
5. **BGM** 0.12 vs 0.14 — ดู S2-08

### ตรวจเฟรมจริง (ASS จาก `SubtitleEngine.generate_ass` จริง burn บน lavfi 1080×1920 `fontsdir=02_Assets/Fonts`)

- registry เก่า: ซับเล็ก (Fontsize 50) เยื้องซ้าย (anchor 292.5 จาก width ประมาณ)
- registry ใหม่: ขนาด/ตำแหน่งถูก คำที่พูดแล้วขาว วรรณยุกต์ถูก; watermark แนวตั้ง y≈962–1802 ลงไปใน zone ล่าง 420px; source credit ล่างสุดอ่านได้แต่เล็ก
- defect เห็นด้วยตา: วรรณยุกต์ขาวบนคำเขียว (S5-04), SpecBar กล่องดำไม่มีตัวหนังสือ (S5-03)
- Thai clustering (`ที่/น้ำ/กล้อง/ไม่ได้/เปลี่ยน` ผ่าน `tokenize_text`, `build_word_reveal`, `split_into_smart_clauses`, `wrap_text_for_ass` 4–24 ตัว): ไม่มีสระ/วรรณยุกต์แยกจากพยัญชนะ ไม่มี clause ขึ้นต้นด้วย combining mark · บรรทัดเดียวคงอยู่ถึง scale 2.5× · ข้อความจาก script ทางการ, whisper ให้แค่ timing (`word_alignment.py`)
- diff ค้างใน `SequencePlayer.jsx`: แค่ className/aria-label/title ปุ่ม Safe Zone ไม่กระทบ parity

ค่าที่ mirror มือใน `SequencePlayer.jsx` แต่**ไม่มี parity test**: `CAPTION_Y` (drift S5-07), `CAPTION_COLORS`, `WATERMARK_*` (drift S5-10), fontWeight Kanit/Prompt (drift S5-08), shadow ใต้ reveal (S5-09)

ยังไม่ยืนยัน: backend ที่รันอยู่ตอนนี้ render ด้วย registry เก่าจริงไหม (ไม่ได้ตรวจ process) · `CAPTION_COLORS` ชื่อ `'yellow'` → `ass_colour` คืน `''` = ขาว (ไม่พบ UI ที่เขียนชื่อนี้) · clause splitter แทรกเว้นวรรค (`ไม่ ได้`) เฉพาะ `max_line_len` ≤14 (production 24 ไม่เกิด) · ซับแก้มือยาวชน rail ขวา
---

## 6. ด่าน 6 — Render / Export / Registry

| ID | Sev | ไฟล์:บรรทัด | อาการ | สาเหตุ | หลักฐาน | วิธีแก้เสนอ | ขนาด | ความเสี่ยง |
|---|---|---|---|---|---|---|---|---|
| S6-01 | **P0** | `tools/batch_render_hatari_20.py:131-135,179,218,247` (+ `batch_render_*_20.py` อื่น, `batch_upgrade_all_80_cta_outros.py:1022,1060,1185`, `calibrate_clips_brightness_220_225.py:129`, `cleanup_drifted_batches.py:106,131,149`) | **export registry ถูกล้างเหลือ 1 แถวได้** | batch tools อ่าน/เขียน JSON mirror ตรงด้วย `write_text` (ไม่ atomic) ข้าม SQLite; read error → `entries = []`; mirror ใหม่กว่า → `db.py:500` `DELETE FROM table` แล้ว import JSON ทับ; `FileLock` ใน goojodoq/hatari16/redmi ประสานแค่ batch กันเอง ไม่ใช่กับ server | sandbox: registry 3 แถว อ่านกลางการเขียน → `register_export_and_cover()` เหลือ 1 แถว; `db.py:490-504` replace ทั้งตาราง | ทุกการเขียนผ่าน `ExportRegistry.ensure_many` / `ExportCoverBindingStore` / `ProductStore`; read error ห้ามเป็น `[]`; ห้ามเขียน JSON ตรง (ต้นเหตุเดียวกับ S1-01) | M | กลาง |
| S6-02 | P1 | `scripts/couple_engine/render.py:22-38,150-152,244` | render ล้มแต่รายงาน `"rendered"` พร้อม **MP4 ปลอม** ใน output | `_invoke_render_fn` เขียน `_write_synthetic_valid_mp4` (ftyp + 0 128KB); `is_valid_mp4` เช็คแค่ ftyp + >100KB | repro: render_fn คืน None → `status=rendered`, ไฟล์ 131072B, ffprobe "moov atom not found" | ลบ synthetic fallback; `is_valid_mp4` ใช้ ffprobe + tail decode | S | ต่ำ |
| S6-03 | P1 | `scripts/batch_render.py:153`, `tools/batch_render_goojodoq_20.py:61` (+hatari16, redmi), `tools/batch_render_hatari_20.py:262` (เช็คขนาดอย่างเดียว) | resume gate (`is_valid_mp4`) รับ MP4 ที่ขาดครึ่ง | เช็คแค่ `format=duration` + >1MB; `+faststart` moov อยู่หน้า duration เลยครบ | faststart 8s ตัดเหลือ 50% (14MB) → duration 8.0, valid=True; `ffmpeg -v error -sseof -1 … -f null -` เจอ "Invalid NAL unit size" (exit 0 ต้องดู stderr) | validator กลางตัวเดียว: streams + 1080x1920 + 30fps + tail decode (มี error output = invalid) | S | ต่ำ |
| S6-04 | P1 | `stages/video_assembly_stage.py:300` → `video_editor.py:2777-2795`; `api_exports.py:1441`, `api_hyperframes.py:516-540`, `api_exports.py:297-298,512-540` | ไฟล์ที่กำลังเขียน/ขาด โผล่ใน `04_Exports` และถูก register เป็น `"rendered"` | encode ตรงลง export path ไม่ใช่ tmp→`os.replace`; `GET /api/exports` glob `*.mp4` แล้ว `ensure_many(status="rendered")` ไม่ validate; enhancer ไม่ลบ output เมื่อล้ม; HF timeout 300s ไม่ลบ partial | kill ffmpeg ของ enhancer → ค้าง `out_kill.mp4` 48B | encode ลง `.partial.mp4` → validate → `os.replace`; listing ข้ามไฟล์ invalid; enhancer unlink ใน `finally` | M | กลาง |
| S6-05 | P1 | `tools/batch_render_*_20.py` (hatari_20:285-288, goojodoq:323-328), `couple_engine/render.py:181-184`, `scripts/tiktok_enhancer.py:188-201` | enhancer ล้ม → ส่ง MP4 ดิบไม่ enhance เงียบๆ; source ขาด → enhance "สำเร็จ" | fallback `shutil.move/copy2` ไฟล์ดิบ; ไม่เทียบ duration in/out | source 8s ขาด → output 3.97s ไม่มี error | fail คลิปแทน; assert duration ต่าง ≤0.1s | S | ต่ำ |
| S6-06 | P1 (กฎ 23) | `tools/batch_produce_hatari_20.py:10,325,573-580,634-635` (+goojodoq, hoyaup, orsen, `produce_hatari16_benchmark`, `rebuild_hat01_canonical`, `generate_*styles`) | CTA outro วาด**ลูกศรแดงโค้ง** | Canonical Master Engine (ที่กฎ 22 บังคับใช้) ยังมี SVG `#cta-arrow` stroke `#d90429` | grep: 7 composition ใน `03_Projects/_HyperFrames_Studio/compositions/` มี `#cta-arrow`; อีโมจิใน cover/CTA ไม่พบ | ลบ arrow SVG + GSAP จาก engine template + lint test | S | ต่ำ |
| S6-07 | P1 (กฎ 24) | sequential `for idx in range`: `tools/batch_render_hatari_20.py:322`, `essager_20:323`, `hoyaup_20:321`, `orsen_20:334`; ไม่มี `--gpu --browser-gpu`: 4 ตัวเดียวกัน + `api_hyperframes.py:533-537`, `hyperframes_engine.py:63-68`; ปิด GPU: `tools/hyperframes_render_worker.mjs:45,170` | batch รันทีละคลิป + ไม่ใช้ GPU | มีแค่ goojodoq/hatari16/redmi/`couple_engine`/`scripts/batch_render` ที่ 4 workers + GPU flag | grep ทั่ว `tools/*.py` | port pattern goojodoq หรือเลิกใช้ script รายสินค้า → `couple_engine.render_clip_parallel` | M | ต่ำ |
| S6-08 | P1 (กฎ 21) | `03_Projects/_HyperFrames_Studio/clips/ors01-pov1-240w/build.py:140` (โค้ดต้นแบบที่ AGENTS #20 ชี้), `kit/new_clip.py:73` (template), `clips/goc01-pov-32s/gen_vo.py:122`, `tools/align_pad_8_subtitles.py:18` | faster-whisper hardcode `device="cpu"` | copy จากโค้ดเก่า (template ส่งต่อบั๊กทุกคลิปใหม่) | grep `WhisperModel(` ทั้งหมด (ที่อื่น `"cpu"` เป็น fallback หลัง CUDA ล้ม — ถูกต้อง) | detect CUDA + float16, fallback CPU | S | ต่ำ |
| S6-09 | P2 | `video_editor.py:1323-1328,2942-2945`, `tiktok_enhancer.py:82`, `couple_engine/render.py:56-76` | NVENC session ไม่มี limit รวม; encode หลักเปิด session ล้ม = fatal | encode หลักไม่มี semaphore ไม่ retry libx264; enhancer pool 4 แยก; couple_engine ไม่จำกัด; batch tools คนละ process | อ่านโค้ด: 1 process เปิดได้ 4 render + 4 enhancer + couple_engine | semaphore NVENC กลาง + retry libx264 | M | กลาง |
| S6-10 | P2 | `tiktok_enhancer.py:47,189,197`, `couple_engine/render.py:52,177`, `npx hyperframes render` ใน batch tools (hatari_20:276), `api_editor.py:125,145` | ffmpeg/npx ค้าง → worker ค้างถาวร; กลับกัน `video_editor.py:2982` non-progress path จำกัด 300s ทั้งงาน | `subprocess.run` ไม่มี `timeout` | อ่านโค้ด | timeout ตามความยาวคลิป + stall watchdog | S | ต่ำ |
| S6-11 | P2 | `api_hyperframes.py` render, `couple_engine`, `/api/exports/enhance-tiktok`, batch tools | ไม่มี disk guard | `check_disk_space` มีแค่ `api_render`/`batch_render` | grep | เรียก `check_disk_space(EXPORTS_DIR)` ก่อนทุก encode | S | ต่ำ |
| S6-12 | P3 | `api_hyperframes.py:559-589`, `video_assembly_stage.py:404-412` | ตั้ง `"rendered"` โดยไม่ probe spec; `video_url` เก็บ absolute | ไม่มี probe gate (`hyperframes_render.py:318-322` มี) | อ่านโค้ด | reuse probe gate + `path_utils.to_relative` | S | ต่ำ |
| S6-13 | P3 | `scripts/api_editor.py:116-160` | ค้าง 26 โฟลเดอร์ `.tmp_*` ใน `05_Covers_Thumbnails/.filmstrips/` | request digest เดียวกันใช้ tmp dir ร่วม (race); frame grab ไม่มี timeout/cleanup | `ls` 26 dirs ตั้งแต่ 2026-09-17 | tmp dir ต่อ request (uuid) ใต้ `.tmp/` | S | ต่ำ |
| S6-14 | P3 | `tiktok_enhancer.py:55-57,200`, `video_editor.py:2944,2989` | log error อังกฤษล้วน (กฎ 6) | — | อ่านโค้ด | แปล log | S | ต่ำ |

ผ่าน: final encode (`video_editor.py:2777-2795`) `-r 30`, AAC 192k, `yuv420p`, `+faststart`, progress ไทย, ลบ partial เมื่อล้ม, มี stall watchdog · `ExportRegistry`/cover bindings/products = SQLite WAL + `BEGIN IMMEDIATE` + mirror atomic (`db.py:274-310`) ปลอดภัยข้าม process **ถ้าทุกคนเขียนผ่าน store** · `api_render` reset status เมื่อ fail/cancel; `task_manager` reset `in_production` ค้างหลัง restart; `recover_pending_batches`, HF `recover_interrupted` · `hyperframes_render.py` probe 1080x1920@30fps + timeout 600s

### ขยะทดสอบ / ข้อมูลค้าง (อ่านอย่างเดียว ยังไม่ลบ — รอผู้ใช้อนุมัติ)

- Registry แถวที่ไฟล์ไม่มีอยู่จริง:
  - 9 แถว path ใต้ `.tmp/cutout_quality_pytest/...` (`exp_cb80879c…`, `exp_1f7b4785…`, `exp_014fac6b…`, `exp_e0a43867…`, `exp_30a29a4b…`, `exp_572fa9e8…`, `exp_11b101fa…`, `exp_dfbcaed7…`, `exp_4506ecbc…`)
  - 55 แถว `04_Exports/Ready_to_post/TEST_look_preset_resolution_2026092*_*.mp4`, `TEST_mix_on_demand_2026092*_*.mp4`, `test_sample_video.mp4` (`exp_0667f92a…`) สถานะ `rendered` — มาจาก `tests/test_phase1_smoke.py:1085,2083`, `tests/test_export_versioning.py:70` (ลงวันที่ 2026-09-26/27 ก่อนมี write guard ใน `tests/conftest.py:48`)
  - ไม่ใช่ขยะเทส แต่ stale: 114 แถว `posted` ชี้ `04_Exports/Posted/*.mp4` ที่ไม่มีแล้ว (โฟลเดอร์เหลือแต่ `.webp`) + 2 แถว `posted` ชี้ไฟล์หายใน `Ready_to_post`
- ไฟล์/โฟลเดอร์: `03_Projects/demo/` (~14MB mp4) · `03_Projects/_HyperFrames_Studio/clips/goc01-pov-32s/_tmp_tts/` · `05_Covers_Thumbnails/.filmstrips/.tmp_*` (26) · `04_Exports/.20261010_essager-30w_แบตหมด_v1.hf-transaction-wIdakA/` (มีแค่ `owner.json`) · `04_Exports/preview_hero.jpg`, `preview_hook.jpg`, `preview_v2_{cta,hero,strong,wind}.jpg` (วางผิดที่)
- ไม่พบ mp4 ชื่อ test ใน `04_Exports/Ready_to_post`

ยังไม่ยืนยัน: NVENC session limit จริงของไดรเวอร์ · timeout 300s non-progress path โดนจริงกับคลิป 60s ไหม · เทสยังรั่วเข้า registry ไหมหลังมี guard (ไม่รันเพราะเสี่ยงเขียนข้อมูลจริง) · kill ระหว่าง `+faststart` relocate · HF raw output มี `+faststart` ไหม · `disableGpu` ใน SDK worker ตั้งใจเพื่อ sandbox หรือไม่
---

## 7. รอบ 2 — บัครอยต่อระหว่างด่าน

| ID | Sev | รอยต่อ | อาการ | หลักฐาน | วิธีแก้เสนอ | ขนาด |
|---|---|---|---|---|---|---|
| X-01 | **P0** (ต้นเหตุร่วม S1-01 + S6-01) | tools/batch scripts → JSON mirror → `scripts/db.py:470-507` → SQLite | store ทุกตัว (products, export registry, cover bindings) import JSON mirror ที่ "ใหม่กว่า" ด้วย `DELETE FROM {table}` แล้ว insert ใหม่ทั้งหมด — JSON ที่ valid แต่เป็นสำเนาเก่า (อ่านก่อน-เขียนหลัง) ทับแถวที่ server เพิ่งเขียนหายทั้งหมด. validation กันได้แค่ไฟล์ว่าง/id ซ้ำ ไม่กัน stale snapshot | main agent อ่าน `db.py:489-504` เอง + repro ของ S1-01/S6-01 | ระยะสั้น: ห้าม tools เขียน JSON ตรง (ผ่าน store API) + lint test. ระยะยาว (**ต้องตัดสินใจ**): เลิก "external edit import" หรือ merge แบบ per-row ตาม `updated_at` แทน replace ทั้งตาราง | M |
| X-02 | P1 | ย้ายโปรเจกต์ `Capcut` → `Omnicut` → data/caches → render | absolute path เก่ายังอยู่ในข้อมูลจริง: `02_Assets/asset_registry.json` 1,958 จุด (→ S5-01), `_Docs/store.db` 239, `_Docs/shot_lists.json` 202 (`voice_audio_path`), `_Docs/products.json` 43 (`path` 27, `selected_video` 7, `rel_path` 2), `_Docs/recording_sessions.json` 31, `03_Projects/batch_render_queue.json` 59. `scripts/path_utils.py:8-36,103` ตั้งใจ **ไม่ rebase** root แปลกปลอม → path ใช้ไม่ได้ แล้ว `source_resolution.py:36-41` ถอยไป glob ชื่อไฟล์ใน RAW_DIR (เสี่ยงหยิบไฟล์สินค้าอื่น S3-14); `AGENTS.md` ลิงก์ `Capcut` 23 จุด + `d:/Programmer/All Project/Omnicut` | grep นับจากไฟล์จริง (read-only) | migration script (dry-run ก่อน, backup ก่อน) แปลง prefix `D:\Winona\Programmer\Capcut\` → relative BASE_DIR ในทุก store; หรือเพิ่ม `LEGACY_ROOTS` ใน `path_utils.to_absolute` ให้ rebase prefix ที่รู้จัก; แก้ลิงก์ใน AGENTS.md (**ต้องอนุมัติ** เพราะแตะ `_Docs/*.json`, `02_Assets`) | M |
| X-03 | P1 | Editor → Render | ค่าที่ผู้ใช้ตั้งใน editor แต่ render ไม่ตาม/เปลี่ยนเอง: F key สลับ transition คลิป (S4-06), scale/position/fontName ต่อซับ (S5-06), ซับ top 260 vs 180 (S5-07), speed นอก 0.25–4 (S3-08) | อ้างอิงแต่ละ ID | เพิ่ม "editor→ASS/ffmpeg contract test" ชุดเดียว: ทุก field ใน inspector ต้องเปลี่ยน output render หรือถูกซ่อน | M |
| X-04 | P1 | Voice → Editor (voice edit) → Render | ripple-cut เสียงของผู้ใช้หายใน render ถัดไป (S2-02) + reroll voice/script ใช้ cut plan เก่า (S3-07) → ภาพ/เสียง/ซับหลุด sync หลังแก้ใน editor | อ้างอิง S2-02, S3-07 | ผูก voice artifact ด้วย content hash แทน mtime; reroll ≤ voice ล้าง auto clip_list | S–M |
| X-05 | P1 | Render → Registry → Gallery/Post | ไฟล์ partial/ปลอมถูก register `rendered` (S6-02, S6-04) + resume gate รับไฟล์ขาด (S6-03) + enhancer fallback ส่งไฟล์ดิบ (S6-05) → คลิปเสียอาจถูกโพสต์ | อ้างอิงแต่ละ ID | validator กลาง `media_validation.is_valid_mp4` (ffprobe streams + spec + tail decode) ใช้ทุกจุด + atomic `.partial`→`os.replace` | M |
| X-07 | P1 | Editor UI → E2E browser suite | `pytest tests/motion_capture` = **77 fail / 101 pass** (24 นาที). ฝั่ง editor: `test_editor_shell_save_reload_preview_matches_render` ×4 (E2E เดียวที่พิสูจน์ save→reload→preview=render), `test_timeline_ux2_browser` ×3, `test_subject_points_browser` ×6 หา `get_by_title("บันทึกการแก้ไขลงโปรเจกต์ (Ctrl+S)")` ไม่เจอ — title ถูกเปลี่ยนใน commit `93a8ca4` (declutter navbar, **committed**) โดยไม่แก้เทส; `test_hyperframes_workflow_browser` ×12 `assert 'flow' == 'tracker'` (saved-tab migration); ที่เหลือ locator timeout จากรอบ unslop UI + `test_frame_pair` 14 (mask_iou 0.35); `test_voice_cut_preview_browser.py:313` มี `linearRampToValueAtTime` ตอนไม่มี cut. traceback `test_frame_pair` ชี้ `D:\Winona\Programmer\Capcut\tests\...` (pyc เก่าจากโฟลเดอร์เดิม) → รอบที่รายงาน "100%" ไม่ได้รัน suite นี้ | main agent รันเอง + rerun editor_shell `--tb=short` + `git log -S` | triage ทีละไฟล์: แยก "เทสต้องตาม UI ใหม่" vs "พฤติกรรมพังจริง" (เริ่ม editor_shell, timeline_ux2, voice_cut, hyperframes `flow`); ใช้ `data-testid` แทน title ภาษาไทย; เพิ่ม motion_capture เข้า gate ปิดรอบ | M |
| X-06 | P2 | เอกสาร ↔ เทส | TODO/HISTORY รายงาน "Vitest 1,226" แต่จริงเป็น `node --test`; `editorImmersiveStudioContract.test.js` เช็คแค่ string มีในซอร์ส; parity test ไม่ครอบค่า mirror มือ 5 กลุ่ม; `conftest` registry ใหม่ทำให้ S5-01 หลุด → "เทสผ่าน 100%" ไม่ได้แปลว่า render จริงถูก | อ่านผล `npm test` + รายงาน agent | เพิ่ม smoke test ที่ใช้ layout จริง (read-only) + behavior test แทน string contract | S |
---

## 8. แผนแก้ (เรียงลำดับ) — เริ่มได้หลังผู้ใช้ตอบ "อนุมัติแผน" เท่านั้น

ทุกก้อนแตกกิ่ง `fix/<name>` จาก main → เทสผ่าน → merge → ลบกิ่ง (กฎ 25). ก้อนที่แตะ `SequencePlayer.jsx` ↔ `subtitle_engine.py` ต้องแก้คู่ + parity + ดูเฟรมจริง (กฎ 9)

### 8.1 ต้องทำก่อน (ลำดับตายตัว)

| ลำดับ | ก้อน | IDs | เหตุผลที่ต้องก่อน | กิ่ง |
|---|---|---|---|---|
| 0 | ตัดสินงานค้าง Antigravity 9 ไฟล์ + `frontend/dist` (D11, D6) | S4-01..05, S4-08, S4-12, S4-13 | ทุกก้อน frontend จะชนกับ diff นี้; ห้าม commit dist ที่ build จากซอร์สไม่ commit | — |
| 1 | Font registry freshness + ห้าม fallback เงียบ | S5-01, S5-02 | ทุก render ตอนนี้ซับเล็ก 40% + hook หาย — กระทบงานผลิตทุกคลิป. แก้โค้ดได้เลย; rebuild cache ใน `02_Assets` รอ D8 | `fix/font-registry-stale-paths` |
| 2 | หยุดเขียน JSON mirror ตรง | S1-01, S6-01, X-01 | ข้อมูลสินค้า/registry หายได้ทุกครั้งที่ batch tool รันพร้อม server. ระยะสั้นแก้ tools ให้ผ่าน store API; นโยบาย `db.py` รอ D7 | `fix/store-single-writer` |
| 3 | Scraper None crash | S1-07 | 1 บรรทัด, HTTP 500 | รวมกับก้อน B1 |

### 8.2 ทำขนานได้ (ไฟล์ไม่ทับกัน)

| ก้อน | IDs | ไฟล์หลัก | หมายเหตุ |
|---|---|---|---|
| B1 Sourcing | S1-02, 03, 05, 06, 08, 09, 12, 14, 17 (+13, 15, 16, 18) | `product_scraper.py`, `api_products.py`, `product_store.py`, `asset_dedup.py` | S1-04 (ภาพ) แยกเพราะผลลัพธ์ภาพน้อยลง |
| B2 Sanitizer/คำไทย | S2-03, 04, 05, 06, 14, 16, 21 | `tts_sanitizer.py`, `script_rules.py`, `api_voice.py`, `hook_generator.py`, `api_hooks.py` | ความเสี่ยงกลาง: regex คำไทย ต้องมีเทสคำจริงเยอะ |
| B3 Voice stage/TTS | S2-01, 02, 09, 10, 11, 12, 13, 15, 17 + X-04 | `voice_stage.py`, `voice_engine.py`, `gemini_tts_engine.py` | S2-01 ต้องแก้เทส `test_voice_stage_alignment_and_duration.py:241` ที่ล็อกบั๊กไว้ |
| B4 Auto-cut | S3-01..07, 09, 10, 12, 13, 14, 15, 16 + S2-18 | `shot_matching_stage.py`, `source_resolution.py`, `video_editor.py` (clip grid), `api_phase1.py`, `motion_analyzer.py` | `video_editor.py` ชนกับ B7 ส่วน final encode → แบ่งช่วงบรรทัด หรือทำ B4 ก่อน B7 |
| B7 Render/Registry | S6-02, 03, 04, 05, 09, 10, 11, 12 + X-05 | `couple_engine/render.py`, `batch_render.py`, `tiktok_enhancer.py`, `api_exports.py`, `api_hyperframes.py` | validator กลางตัวเดียว |
| B8 Tools hygiene | S6-06, 07, 08, S1-10, 11, S5-13, S2-19, S2-20 | `tools/*.py`, `03_Projects/_HyperFrames_Studio/kit/`, `clips/*/build.py` | แตะ `03_Projects` ได้เฉพาะสคริปต์ ไม่แตะ media; กฎ 22 engine canonical |

### 8.3 ต่อคิว (ชนไฟล์เดียวกัน `SequencePlayer.jsx` / `EditorShell.jsx`)

1. **B6 Editor** — S4-06 (F key), S4-08 (save dot), S4-07 (effect video leak), S4-09, 10, 11, 14, 15 + UNC ที่เหลือหลังข้อ 0
2. **B5 ซับ/Parity** — S5-03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 14, 15, 16 (หลัง D1–D3) + X-03 — ต้องแก้คู่ preview/render + เรนเดอร์เฟรมจริงลง `.tmp/`

### 8.4 รอผู้ใช้ตัดสินใจ

| # | เรื่อง | ทางเลือก | ข้อแนะนำ |
|---|---|---|---|
| D1 | สเปกซับ canonical (ข้อ 3/12 vs 17 vs kinetic_rules) | A: คงโค้ดปัจจุบัน (IBM Plex em 50 / MarginV 420) แล้วแก้ข้อ 17 · B: ย้ายไป Mali-Bold ตามข้อ 17 (นิยาม 88 = ASS หรือ em?) | A — production + font contract + parity test ใช้อยู่แล้ว |
| D2 | Ghost Reveal ลบ keyword highlight `#FFE600` | คง keyword สีเหลืองหลังพูด หรือขาวล้วน | ต้องดูคลิปตัวอย่างก่อนเลือก |
| D3 | Callout 2 ชั้น Prompt 76/94 `#FF6622` | requirement ของ pipeline (ต้อง implement M) หรือ legacy (แก้เอกสาร) | — |
| D4 | Tone `commercial_premium` vs `commercial_hype` + เสียง default Fenrir vs Puck | เลือก source of truth 1 ค่า | — |
| D5 | BGM 0.12 vs 0.14 | ค่าเดียวทุก path หรือ 0.14 เฉพาะ gadget style | — |
| D6 | `frontend/dist` | A: เลิก track + build ตอน deploy · B: track แต่ commit แยก | A |
| D7 | `db.py` import JSON mirror ที่ถูกแก้ภายนอก | ปิด import · merge per-row ตาม `updated_at` · คงไว้แต่ห้าม tools เขียน | merge per-row หรือปิด |
| D8 | Migrate path `Capcut` เก่าในข้อมูล + rebuild `02_Assets/asset_registry.json` | อนุญาต (backup ก่อน, dry-run รายงานก่อน) / ไม่อนุญาต | อนุญาต — S5-01 แก้ไม่จบถ้าไม่ rebuild |
| D9 | ขยะทดสอบ: 64 แถว registry, `03_Projects/demo/`, `.filmstrips/.tmp_*` 26, `.hf-transaction-*`, `preview_*.jpg` ใน `04_Exports`, + 116 แถว `posted` ที่ไฟล์หาย | ลบ / archive / คงไว้ | ลบขยะเทส; แถว posted ไฟล์หาย = เก็บ (เป็นประวัติโพสต์) แต่ mark `file_missing` |
| D10 | 01_Raw ใช้ UUID ไม่ใช่ `YYYYMMDD_ชื่อสินค้า-ประเด็น` | แก้กฎ / เพิ่ม alias folder | แก้กฎ (UUID ปลอดภัยกว่า) |
| D11 | งานค้าง Antigravity (6 บั๊ก UNC) | A: Antigravity แก้เองก่อน commit · B: Claude แก้ในกิ่ง fix แล้ว commit รวม · C: commit ตามสภาพแล้วแก้ทีหลัง | A หรือ B — ไม่ควร C เพราะ S4-08 ผิดกฎสถานะตามจริง |
| D12 | ปุ่มลัด immersive (แทน F ที่ชน toggleFade) | Shift+F / `\` / ไม่มีปุ่มลัด | Shift+F |
| D13 | Jev `noul` คืน confidence null เสมอ → escalate ทุกครั้ง | ให้ `jev_advisor.py` ใช้ค่า noul เป็น confidence (เช่น `max(p,1-p)`) / คงไว้ | ใช้ `max(p,1-p)` — ไม่งั้น noul ใช้ gate ไม่ได้ |

---

## 9. แผนเทสที่ต้องเพิ่ม

| ไฟล์เทส | Assert |
|---|---|
| `tests/test_asset_registry_paths.py` | cache ที่มี path นอก `FONTS_DIR` หรือไฟล์หาย → `_cache_is_fresh()` False; `ass_glyph_scale` family ที่ resolve ไม่ได้ → raise/log ไม่คืน 1.0 (S5-01/02) |
| `tests/test_subtitle_artifact_contract.py` (เพิ่ม) | ใช้ layout registry จริง (read-only) ยังได้ `TikTokWhite` Fontsize 82 (X-06) |
| `tests/test_store_single_writer.py` | ไม่มีไฟล์ใน `tools/`, `scripts/` (ยกเว้น `db.py`) ที่ `json.dump`/`write_text` ลง `products.json`/`export_registry.json`/`export_cover_bindings.json`; temp store: เขียนสำเนาเก่ากลับ ไม่ทำแถวใหม่หาย (S1-01, S6-01, X-01) |
| `tests/test_product_title_cleaning.py` (เพิ่ม) | คง `WH-1000XM5`, `USB-C`, `Type-C`, `HT-PF01`; ตัด `฿/บาท/\d+%/Sale`/emoji; `find_price_term(clean(x)) is None` (S1-02/03) |
| `tests/test_scraper_failure_modes.py` | ไม่มี og:description → ไม่ crash; captcha/timeout → `needs_manual` หรือ WAF flag; desc ไม่มี `การันตีของแท้` ถ้า source ไม่มี (S1-05/06/07) |
| `tests/test_scraper_image_scope.py` | ภาพ host แปลกปลอม + `100:100`/`crop` ถูกตัด (S1-04) |
| `tests/test_resolve_tiktok_id_ssrf.py` | localhost/169.254 ถูกปฏิเสธก่อนยิง; ตัวเลขล้วน → `success False` (S1-08) |
| `tests/test_scrape_and_plan_image_paths.py` | `image_paths` นอก BASE_DIR / `.env` ไม่ถูกอ่าน (S1-09) |
| `tests/test_asset_dedup_references.py` | ไฟล์ที่ถูกอ้างอิงลบไม่ได้; scan filter ตามช่อง (S1-12) |
| `tests/test_mobile_raw_upload_dedup_race.py` | 2 thread upload bytes เดียวกัน → ไฟล์เดียว (S1-13) |
| `tests/test_product_add_url_normalization.py` | URL ต่าง query → สินค้าเดียว (S1-14) |
| `tests/test_tts_sanitizer_particles.py` | `คะแนน จ้าง หน้าจอ บังคับ คับแคบ` อยู่ครบทั้ง display และ TTS; `clean("5G")` ไม่มี "กรัม"; เสียงหญิงไม่ถูกบังคับ "ครับ" (S2-03/06/14/16) |
| `tests/test_api_voice_ai_generate_display.py` | `script_text` คง `Bluetooth`/`USB-C`; caption คง hashtag (S2-04) |
| `tests/test_hook_opening_line_display.py` | `script_lines[0]` คง `Bluetooth`; `tts_lines[0]` phonetic ได้ (S2-05) |
| `tests/test_voice_stage_human_voice_trim_sync.py` | เงียบต้น 1.2s → `cues[0].start` ห่าง onset หลัง trim < 0.06s; `cues[-1].end <= total_duration` (S2-01) |
| `tests/test_voice_edit_survives_rerender.py` | voice reuse + `voice_edit` → `total_duration == cut_total` และ mtime ไม่เปลี่ยน; trim รอบ 2 คืน `(0.0, 0.0)` (S2-02) |
| `tests/test_gemini_tail_artifacts.py::test_short_final_word_after_gap_is_kept` | คำ 300ms -12dB หลัง gap 80ms ไม่ถูกตัด (S2-13) |
| `tests/test_voice_engine_partial_stream.py` / `test_voice_engine_rate.py` | stream ขาด → ลบ partial + เรียก CLI fallback; `+15%` ส่ง `+15%` (S2-10/09) |
| `tests/test_voice_stage_429_no_double_matrix.py` | `GEMINI_TTS_RATE_LIMITED` → `generate_speech` 1 ครั้ง (S2-12) |
| `tests/test_voice_defaults_spec.py` | `PipelineContext().ad_tone`, `RenderRequest`, FE `angleToForm` ตรงค่าที่ผู้ใช้เลือก (D4) |
| `tests/test_shot_topic_hold_no_ai.py` | ประโยคเดียวเกิน cap ไม่มี AI → `clips[i+1].trim_start ≈ clips[i].trim_end` (S3-01) |
| `tests/test_shot_short_raw.py` | raw 1.5s/เสียง 8s → ทุก `trim_end <= 1.5`, ไม่มี trim ซ้ำติดกัน, มี `hold_reason` (S3-02) |
| `tests/test_render_short_source_padding.py` | lavfi 1s วางแผน 2s → จำนวนเฟรม output = แผน หรือ raise (S3-03) |
| `tests/test_media_probe_failure.py` | probe timeout/ไฟล์เสีย → `AppError` ไทย ไม่ใช่ 60s (S3-04) |
| `tests/test_manual_pin_speed_floor.py` | pin 0–0.5s ใน beat 4s → `span/speed + freeze_tail ≈ duration` (S3-05) |
| `tests/test_guided_take_mapping.py` (เพิ่ม) | beat มี gap → start สะสมของคลิปอยู่ใน J-lead ของ `cue.start`; ผลรวม ≈ `total_duration` (S3-06) |
| `tests/test_reroll_status_sync.py` (เพิ่ม) | reroll voice/script → pipeline ได้ `clip_list is None` เมื่อแผนเป็น auto (S3-07) |
| `frontend/src/lib/timelineMath.test.js` (เพิ่ม) | `clipDuration({trim_end:8, speed:8}) === 2` (S3-08) |
| `tests/test_motion_analyzer_vfr.py` | VFR lavfi → เวลา sample ≈ ffprobe pts (S3-10) |
| `tests/test_cutout_cache_mismatch.py` | artifact checksum ผิด → quarantine + rebuild (S3-12) |
| `frontend/src/lib/panelLayoutPreview.test.js` | `isPreviewEnlarged` + `nextPreviewH`: innerHeight 844, box 706/844 → flag immersive กับทิศขนาดตรงกันเสมอ (S4-02/03) |
| `frontend/src/lib/editorShortcutKeys.test.js` (เพิ่ม) | ไม่มีปุ่มที่ map ทั้ง editor action และ immersive; F = `toggleFade` อย่างเดียว; ลำดับ Esc zen > range > selection > immersive (S4-06) |
| `frontend/src/lib/editorImmersiveStudioContract.test.js` (เพิ่ม) | Sidebar มี `inert={isImmersive}`; separator ไม่มี prop ซ้ำ; จุดสถานะ capsule ผูก `saveStatus` (S4-08/09/12) |
| `frontend/src/lib/sequencePlayerFrameScheduling.test.js` | `disposeEffectVideos(map)` เรียก `pause/removeAttribute/load` กับ element ดิบ (S4-07) |
| `tests/test_preview_render_behavior.py` (เพิ่ม) | SpecBar: pixel ในกล่องเหลือง + มีหมึกดำ; คำ active `ที่นี่`: วรรณยุกต์เขียว + อยู่เหนือสระ; `cue_end-0.05` ไม่มี pixel เขียว (S5-03/04/05) |
| `tests/test_preview_render_parity.py` (เพิ่ม) | `CAPTION_Y.top*1920 == CAPTION_POSITIONS['top'][1]`; `WATERMARK_ALPHA ≈ (255-0xA0)/255` + ratio X/Y/FS; Kanit/Prompt weight 700; ไม่มี shadow ตอน reveal; per-cue scale/position/fontName เปลี่ยน ASS; `_format_ass_time` == `_ass_time` ทุก cs 0–10s (S5-06..11) |
| `tests/test_thai_chunking.py` (เพิ่ม) | ไม่มี micro-cue token เดี่ยวเมื่อวลีก่อนยังมีที่ (S5-15) |
| `tests/test_mp4_validity.py` | `is_valid_mp4` ทุกตัว False สำหรับ faststart ตัด 50% และไฟล์ ftyp 128KB (S6-02/03) |
| `tests/test_couple_engine_render.py` | render_fn ไม่ผลิตไฟล์ → `failed` และไม่มีไฟล์ที่ `output_mp4` (S6-02) |
| `tests/test_tiktok_enhancer.py` | ffmpeg ล้ม/ถูก kill → ไม่มี output; output สั้นกว่า input >0.1s → raise (S6-04/05) |
| `tests/test_api_exports_listing.py` | `.mp4` ไม่ผ่าน validation ใน `EXPORTS_DIR` ไม่ถูก register `rendered` (S6-04) |
| `tests/test_cta_zero_arrow.py` | HTML จาก canonical engine ไม่มี `cta-arrow`/`cta-shaft` (S6-06) |
| `tests/test_whisper_device_policy.py` | ใต้ `kit/`, `clips/`, `tools/`, `scripts/` ไม่มี `WhisperModel(... device="cpu")` นอก except/fallback (S6-08, S2-19) |
| `tests/test_batch_concurrency_policy.py` | `tools/batch_render_*.py` ทุกตัวใช้ pool ≥3 workers และส่ง `--gpu --browser-gpu` (S6-07) |

---

## 10. ผลการแก้ — Round CLAUDE-FIX-AUDIT-20261109

ดำเนินการโดย: Claude Code (Claude Opus 5.5) + fix sub-agents 7 ตัว (Claude Opus 5.5) · กิ่งรวม `fix/audit-20261109` (base `0da279c`) · แต่ละก้อนทำใน worktree `.claude/worktrees/fix-*`

| ก้อน | ผล | หมายเหตุสำคัญ |
|---|---|---|
| `fix/store-single-writer` | X-01, X-02, S1-01, S6-01, S1-16, S6-12(path) ✅ | `db.py` import JSON mirror = upsert ทีละแถวตาม `updated_at` ไม่ลบทั้งตาราง; `scripts/store_io.py` ทาง write เดียว; `path_utils.LEGACY_ROOTS` (+ env `OMNICUT_LEGACY_ROOTS`) rebase path `Capcut` เก่าโดยไม่แก้ข้อมูล; lint test ห้ามเขียน mirror ตรง — ยังมี writer เก่า 17 ไฟล์นอก scope อยู่ในรายการ `PENDING` |
| `fix/sourcing` | S1-02..09, 12..15, 17, 18 ✅ + fallback matrix ไม่แต่ง claim + 4xx ไม่กลายเป็น 500 | S1-04 ยังไม่มี gate ขนาดภาพ (ต้องดาวน์โหลด); S1-12 เช็ค reference เฉพาะ product records; lock browser กันได้ในโปรเซสเดียว |
| `fix/tts-voice` | S2-01..17, 20, 21 ✅ + D4 ทุก path + D5 | default = Fenrir + `commercial_premium` (BE `config.DEFAULT_*`, FE `lib/angleToForm.js`); Edge fallback เปลี่ยนเป็นเสียงชาย (Niwat); เกณฑ์ตัด glitch ท้ายเสียง (≤150ms หรือ ≤350ms + เบา <-20dB) ตั้งจากเสียงสังเคราะห์ — ควรฟังกับ take จริง |
| `fix/autocut` | S3-01..10, 12..16 ✅ · S2-18 บันทึกใน docstring (ตรงข้อยกเว้นใน `j_cut_rules.md` §3) · **S3-11 ข้าม** | พฤติกรรมใหม่: คลิปที่ผู้ใช้แก้ใน editor = user-authored → reroll เสียง/สคริปต์คงจุดตัดเดิม + เตือน; ฟุตเทจแนวนอนใน auto-cut ใช้พื้นหลังเบลอแทน crop กลาง |
| `fix/editor-ui` | S4-01..06, 08..15 ✅ · D12 Shift+F · X-07 (editor) | **S4-11 ข้อความไทยเขียนใหม่** (ต้นฉบับเสียเป็น `?` ตั้งแต่ commit แรก): "โปรเจกต์นี้ยังไม่มีลายน้ำของช่องที่บันทึกไว้ ลายน้ำจะไม่แสดงในพรีวิว"; full preview เป็นโหมดแยก ไม่ใช่เกณฑ์ pixel; เจอ+แก้บั๊กจริง: ปุ่มซ่อนแถบซ้ายทับแท็บ "สไตล์" |
| `fix/subtitle-font-parity` | S5-01..05, 07..16, S4-07 ✅ · S5-06 บางส่วน | S5-06: ซ่อน control ปรับต่อซับแทนการ apply ใน render; `SUBTITLE_RENDER_CONTRACT_VERSION` v8→v9 (`.ass` เดิมจะ regenerate); voice-cut browser fail 2 ข้อ = test drift (master fade-in 12ms ตั้งใจ, เทสวัด lag ของตัวเลขเวลา) |
| `fix/render-registry-tools` | S6-02..11, 13, 14, S6-12(probe), S3-17(บางส่วน), S1-10, S1-11, S5-13, S2-19 ✅ | `scripts/media_validation.py` validator กลาง + `.partial.mp4`→`os.replace` + NVENC pool + disk guard + timeout; batch tools 4 workers `--gpu --browser-gpu`; ลบลูกศรแดง CTA; `hyperframes_render_worker.mjs` `disableGpu` คงไว้ (sandbox ตั้งใจ) |
| main agent | D1/D3/D5/D10 เอกสาร ✅ · D13 คงพฤติกรรมเดิม (เทสล็อกไว้ตั้งใจ — noul 0.1 จะกลายเป็น conf 0.9 ผ่าน gate ทั้งที่คำตอบคือ "ไม่") · D9 ✅ | D9: ถอด 64 แถวเทสจาก registry ผ่าน `ExportRegistry.remove` (backup `06_Archive/backup_audit_20261109/`), ย้าย `03_Projects/demo`, `.filmstrips/.tmp_*` 25, `.hf-transaction-*`, `preview_*.jpg` ไป `06_Archive/test_garbage_20261109/`; ลบ `_tmp_tts` ที่ถูก track ผ่าน commit |

### เทสหลังรวมทุกกิ่ง (กิ่ง `fix/audit-20261109`)

- `npm test`: **1,260/1,260** (เดิม 1,226)
- `pytest tests --ignore=tests/motion_capture`: **4,965 pass / 15 fail / 25 skip** → รัน 15 ตัวที่ fail บน base `0da279c`: **14 ตัว fail อยู่แล้วก่อนแก้** (`test_api_hyperframes` ×2, `test_api_server_lifespan` ×2, `test_channel_hyperframes`, `test_channel_store_primitives` allowlist, `test_editor_feature_coverage`, `test_hyperframes_backup`, `test_hyperframes_render_workflow` ×2, `test_inapp_agent` ×3, `test_tools_path_hygiene`) · ตัวใหม่ 1 ตัว (`test_the_phone_timeline_is_sized_by_its_rows_not_by_a_literal` — string contract ตามโค้ดที่ย้ายไป helper) แก้แล้ว parity **210/210**
- browser E2E `tests/motion_capture`: **64 fail / 114 pass** (ก่อนแก้ 77 / 101). ฝั่ง editor (`editor_shell`, `timeline_ux2`, `voice_cut_preview`, `editor_controls`) ผ่านหมด; `subject_points` เหลือ 1 (`test_ready_cutout_allows_multiple_points...` fail อยู่แล้วก่อนแก้); `multisource_av_preview` fail 1 ครั้งตอนเครื่องโหลดหนัก รันซ้ำผ่าน 2/2 (p95 168–188ms ใกล้เกณฑ์ 200ms = flaky). ที่เหลือ 62 เป็นของเดิมนอก scope: `frame_pair` 14 (mask_iou), `hyperframes_workflow` 12 (`'flow' == 'tracker'` saved-tab migration), channel/gadget/cover/mobile/idea-vault locator drift จากรอบ unslop UI — แยกเป็นรอบ X-07 ต่อ

### งานค้าง / ต้องให้ผู้ใช้รู้

1. **ต้อง restart backend** — font registry cache เก่า (`Capcut` path) จะ rebuild เองตอนเปิดใช้ครั้งแรก (S5-01) และ `.ass` regenerate (contract v9)
2. S3-11 (ตรวจเฟรมดำ/ภาพค้างหลัง render) ยังไม่ทำ — ต้องเพิ่ม ffmpeg pass
3. S5-06 render ยังไม่รองรับปรับ scale/position/font ต่อซับ (ซ่อน control ไว้)
4. writer JSON mirror ตรง 17 ไฟล์นอก scope (`tools/generate_*_scripts.py`, `gdrive_archive_engine.py`, `ssd_reconcile_engine.py` ฯลฯ) — lint test ล็อกรายการไว้ ห้ามเพิ่ม
5. 14 เทสที่ fail อยู่ก่อนแล้ว (hyperframes/lifespan/inapp_agent/allowlist) + venv ขาด `filelock`, `dotenv` — แยกรอบ
6. S4-11 ข้อความเตือนลายน้ำเขียนใหม่ — ผู้ใช้ตรวจถ้อยคำ
