# รายงานความเร็วรอบสอง — ช่วงที่ 1: วัดอย่างเดียว (2026-11-18)

> ดำเนินการโดย: Claude Code (Claude Sonnet 5.5) · ต่อจาก [DRAFT_TO_RENDER_SPEED_AUDIT_20261111.md](DRAFT_TO_RENDER_SPEED_AUDIT_20261111.md) และ [SPEED_OVERNIGHT_20261112.md](SPEED_OVERNIGHT_20261112.md)
> ช่วงนี้**ไม่ได้แก้โค้ด product แม้แต่บรรทัดเดียว** (`git status`: แก้เฉพาะ `TODO.md`, `HISTORY.md` + ไฟล์รายงานนี้) · สคริปต์วัดและผลดิบอยู่ `.tmp/speed_audit/r2/` และ `.tmp/speed_audit/out/r2_*` · ไม่เรนเดอร์ลง `04_Exports/` · ไม่แตะ `01_Raw/` `02_Assets/` `export_registry.json` (ทุกอย่างรันใน data root สำเนาที่ `.tmp/speed_audit/data`)

## 0. เครื่องที่วัด และข้อจำกัดที่ต้องรู้ก่อนอ่านตัวเลข

| รายการ | ค่า |
| :-- | :-- |
| CPU | AMD Ryzen 7 7735HS (8 คอร์ / 16 เธรด) |
| GPU | AMD Radeon ในตัว (2 GB) · **ไม่มี NVIDIA / CUDA** (`ffmpeg -encoders` แสดง `h264_nvenc` เพราะ build มาพร้อมรหัส แต่เปิดใช้จริงไม่ได้ — เข้ารหัสด้วย `h264_amf`) |
| RAM | 13.7 GB รวม · **ว่าง 1.0–4.9 GB ระหว่างวัด** (VS Code, Chrome, language server ของผู้ใช้เปิดอยู่ ผมไม่ได้ปิดอะไร) |
| `.venv` | **ไม่มี `faster-whisper`** (ทั้งที่ `requirements.txt` ปักไว้ 1.2.1) · มี `psutil` |
| commit ที่วัด | `55f8a5a` (main) · โค้ด render ไม่เปลี่ยนตั้งแต่ `8be3372` (`git diff` ของ `video_editor.py`, `video_assembly_stage.py`, `pipeline.py`, `media_validation.py` ว่างเปล่า) |
| เวลาที่วัด | 16:25–18:00 วันที่ 2026-11-18 |

1. **ตัวเลขข้ามเครื่องเทียบกันไม่ได้** รอบก่อนมีสองเครื่อง (Ryzen + AMD ช่วง 1–2, i7-14700 + RTX 4060 ช่วง 3–5) รอบนี้วัดบน Ryzen เครื่องเดียวกับช่วงที่ 1 ตารางเทียบข้อ 2 จึงบอกชัดว่าเทียบกับเครื่องไหน
2. **เครื่องนี้แกว่งมาก** คำสั่งเรนเดอร์เดียวกันได้ 25.5 ถึง 47.4 วินาทีในช่วงเวลาใกล้กัน (RAM ว่างต่ำ, Defender, แอปอื่น) จึงรายงานเป็นค่ากลางหรือช่วงทุกที่ และระบุ n
3. **Gemini API ช้าผิดปกติจากเครือข่ายนี้ในวันนี้** ยิงคำถามสั้น ๆ ของตัวจำแนกโทน: 8.6 วิ (แบบ minimal thinking) แทนที่จะเป็น 1–1.5 วิ ตามช่วงที่ 5 และ 3 จาก 4 ครั้งได้ `504 DEADLINE_EXCEEDED` ที่ ~11–12 วิ ตัวเลขทุกขั้นที่ยิง Gemini (เสียง, โทน, vision, บท) จึง**สูงกว่าปกติ**
4. **ข้อที่ต้องใช้ CUDA / NVENC / VRAM วัดไม่ได้** ลง "ยังไม่ได้วัด" ในข้อ 6 ไม่ได้ประเมินเอา

**ยิง API จริงไปเท่าไหร่ (ค่าใช้จ่าย):** Gemini TTS 6 ครั้ง (ดราฟต์ 4 + ดราฟต์ 60 วิ 2) · Gemini สร้างบท 2 ครั้ง · Gemini ตัวจำแนกโทน 4 ครั้งในโพรบ + 1–3 ครั้งต่อดราฟต์ (6 ดราฟต์) · Gemini vision 2 งาน (ดราฟต์ cold + ดราฟต์ 60 วิรอบแรก ที่ข้อความใหม่) + อัปโหลด 1 ครั้ง · Antigravity CLI 1 ครั้งสำเร็จ (prompt สั้น) + 1 ครั้งล้มทันที · Google Translate 2 request (ถูกปฏิเสธ) + MyMemory ตามที่ translator ถอยไปใช้ในดราฟต์ cold · **Google Flow: 0 ครั้ง** (ไม่ได้ login ไม่ได้สร้างวิดีโอ)

## 1. คอขวดใหม่ เรียงตามวินาทีที่ลดได้ต่อคลิป (เครื่องนี้)

ขนาดงาน S/M/L · "วัด/ประเมิน" ระบุกำกับทุกแถว · แยกเป็นสองกลุ่มตามที่ขอ

### กลุ่ม ก — ไม่เปลี่ยนภาพ/เสียง/ข้อความที่ได้

| # | ที่ | สิ่งที่พบ | วิธีแก้ | ลดได้ | ขนาด |
| :-: | :-- | :-- | :-- | :-- | :-: |
| ก1 | [render_jobs.py:85-96,185](../../scripts/render_jobs.py) · [batch_render.py:54](../../scripts/batch_render.py) | ค่าเริ่มต้น 4 งานพร้อมกันไม่ดู RAM · วัดแล้ว 1 pipeline กิน RAM ~3.1 GB (RAM ว่าง 4.9 → 1.65–1.8 GB) · ที่ concurrency 2/3/4 RAM ว่างตกเหลือ 86/227/231 MB ภายใน 18–24 วินาที (guard ผมตัดงานที่ 300 MB) · คอมเมนต์ในโค้ดเขียนว่า "สี่งาน ~4.5 GB" ซึ่งไม่ตรงกับค่าวัด | จำนวนงานพร้อมกัน = min(4, RAM ว่าง ÷ 3.5 GB) ตอนเริ่ม batch · แก้คอมเมนต์ | ไม่ใช่วินาทีต่อคลิปโดยตรง แต่กัน ENOMEM/swap ที่ทำให้ batch ล้มหรือช้ากว่าเดิม (วัด: guard ตัดจริง) | S |
| ก2 | [proxy_manager.py:150-195](../../scripts/proxy_manager.py) · [api_proxy.py:108-170](../../scripts/api_proxy.py) | proxy คือ libx264 ใช้ทุกคอร์ ไม่จำกัดจำนวนพร้อมกัน (จำกัดแค่ต่อ source ไม่ซ้ำ) · วัด: 3 source พร้อมกัน wall 98 วิ **มากกว่าผลรวมทำทีละตัว 84 วิ** CPU 99% · เรนเดอร์ที่รันพร้อมกันช้าลงเป็น 88.7 วิ จาก 42.0–47.4 วิ (+~100%) | semaphore 1 งาน + priority ต่ำกว่าปกติ (Windows `BELOW_NORMAL_PRIORITY_CLASS`) · proxy ใช้พรีวิวอย่างเดียว ไม่ผ่านเข้า render | ขณะสร้าง proxy: เรนเดอร์ไม่ช้าลง ~40+ วิ (วัด n=1 ที่ 88.7 vs ~44.7 · ผลหลังแก้ประเมิน) | S |
| ก3 | [api_editor.py:85-168](../../scripts/api_editor.py) · [timelineFilmstrip.js:57-60](../../frontend/src/lib/timelineFilmstrip.js) | key filmstrip รวมจุด trim (step 0.1 วิ) → trim ทุกครั้ง = sprite ใหม่ = ffmpeg `count+2` ตัวทีละตัว: 8 tile 2.3 วิ / 16 tile 4.0 วิ / 24 tile 6.2 วิ (วัด n=3 ต่อค่า) | sprite ต่อ source แล้วตัดหน้าต่างด้วย CSS offset (ผู้ใช้เห็นแค่ภาพย่อ ไม่ผ่านเข้า render) | trim 1 ครั้ง −4 วิ CPU · เปิดโปรเจกต์ใหม่ 18 คลิป −~60 วิ CPU (ประเมินจาก 18 × 3.5 วิ) | M |
| ก4 | [EditorShell.jsx:2306](../../frontend/src/components/editor/EditorShell.jsx) · [project_manifest.py:322](../../scripts/project_manifest.py) | ปุ่มเรนเดอร์ใน editor ส่ง `part: 'subtitles'` หรือ `'bgm'` เสมอ → resume_from=subtitles ทำ `.ass` ใหม่ แม้แก้แค่คลิป · วัด: stage subtitles 2.26–2.90 วิ (ค่ากลาง 2.45) เทียบ resume_from=video 0.00 วิ | ส่ง `part:'video'` เมื่อ caption/style/bgm ไม่ถูกแก้ (editor มี `captionDirty`, `audioDirty` อยู่แล้ว) | −2.3 วิ ต่อการเรนเดอร์จาก editor (วัด) | M (แตะ UI ต้องรัน motion_capture) |
| ก5 | [api_server.py:184-198](../../scripts/api_server.py) · [flow_client.py:63-87,196-236](../../scripts/flow_client.py) | `recover_startup_work()` ใน lifespan รันแบบบล็อก: ถ้า daemon Flow ยังไม่รัน `start_service_daemon()` นอนหลับ 1.2 วิ + วนเช็ก 0.5 วิ · วัดเปิด backend: daemon ไม่รัน 7.0 วิ (n=1) · daemon รันอยู่ 3.1/6.7/3.1 วิ (n=3) · เปรียบเทียบเปิดโดยตัด Flow ออก 3.6/5.5/4.8 วิ · daemon นิ่ง ๆ กิน 115 MB / CPU 1.7% | ย้ายเรียก Flow ไป background thread (ไม่รอ) | −1 ถึง −3 วิ ต่อการเปิด backend (วัดแล้วแกว่ง ±2 วิ ชี้ได้แค่ทิศ) | S |
| ก6 | [flow_service.py:118-133](../../scripts/flow_service.py) · [Topbar.jsx:113-118](../../frontend/src/components/Topbar.jsx) | Topbar ถาม `/api/flow/status` ทุก 30 วิ ต่อแท็บ · daemon ล่ม = 2.0 วิ ต่อครั้ง (timeout ของ `is_healthy`) บล็อก thread ของ server · daemon ทำงาน 25 ms (วัด n=5 / n=10) | ลด timeout health check เป็น ~0.3 วิ เมื่อพอร์ตไม่ listen · หรือ backoff เมื่อ offline | −1.7 วิ thread-time ต่อ poll เมื่อ Flow ปิด | S |
| ก7 | [Timeline.jsx:163,355-359,1111](../../frontend/src/components/editor/Timeline.jsx) | ไม่มี `memo` · ลากหัวอ่านในฟิกซ์เจอร์ EditorShell (**dev build + StrictMode** ตัวเลขสูงกว่า production): 2.0 commit ต่อ pointer move · long task ต่อ move ค่ากลาง ~73 ms (18 คลิป) → ~105 ms (50 คลิป) · event ช้าสุด 200–312 ms | `memo` ต่อคลิป + ส่ง state ที่เปลี่ยนเฉพาะ playhead ผ่าน store (เหมือนที่ทำกับตอนเล่น) | ยังไม่ทราบตัวเลข production · ต้องวัดซ้ำบน build จริงก่อนแก้ | M |
| ก8 | [shot_matching_stage.py](../../scripts/stages/shot_matching_stage.py) · [gemini_vision_matcher.py](../../scripts/gemini_vision_matcher.py) · [motion_analyzer.py](../../scripts/motion_analyzer.py) | แหล่งที่มาใหม่ครั้งแรก (cold): `match_script_to_video` **119.3 วิ** (proxy 640 px 17.0 + อัปโหลด 29.8 + generate ≈72) · motion analysis **45.8 วิ** · `get_rms_energy` 10.0 วิ (import librosa) → ขั้น shot_matching รวม 199 วิ (วัด n=1, API ช้ากว่าปกติ) · ซ้ำ 26–29 วิ · ดราฟต์ 60 วิ ข้อความใหม่ 170 วิ → 13.4 วิ | วิเคราะห์ที่จุด ingest แบบ background แทนรอตอนสร้างร่าง (ผลเดิมทุกบิต แค่ย้ายเวลา) | ร่างแรกของ source ใหม่ −~165 วิ (ย้ายไปนอกเส้นทางที่ผู้ใช้รอ) | L |

### กลุ่ม ข — อาจเปลี่ยนภาพ / เสียง / ข้อความ (ต้องให้เจ้าของตัดสิน)

| # | ที่ | สิ่งที่พบ | วิธีแก้ | ลดได้ | ความเสี่ยง | ขนาด |
| :-: | :-- | :-- | :-- | :-- | :-- | :-: |
| **ข1** | [auto_sharpen.py:97-117](../../scripts/auto_sharpen.py) · [tiktok_enhancer.py:44-60,150-212](../../scripts/tiktok_enhancer.py) · เรียกจาก [batch_render.py:951](../../scripts/batch_render.py), [api_render.py:280](../../scripts/api_render.py), [api_phase1.py:1541](../../scripts/api_phase1.py) | **ถดถอยจาก commit `f5b61c8` (2026-11-12):** ทุกคลิปที่เรนเดอร์เสร็จถูกเข้ารหัสซ้ำทั้งไฟล์ (libx264 crf 17 preset medium + `unsharp` + `eq`) บนเครื่องนี้ **51.6 วิ** (50.55 / 51.58 / 53.04) ต่อคลิป 42 วิ · ไฟล์ใหญ่ขึ้น 46.8 → 59.2 MB (+26%) · ก่อนเข้ารหัสจริงลอง NVENC ก่อนแล้วล้ม เพราะ `HAS_NVENC` ตรวจจากข้อความ `-encoders` · ผ่าน batch จริง c=1: คลิปละ **85 วิ** (เปิด sharpen) เทียบ **33 วิ** (ปิด) = ครึ่งเวลา 61% ไปกับขั้นนี้ | (ก) ใส่ `unsharp`+`eq` เข้าในกราฟ filter ของการเข้ารหัสรอบเดียว แล้วเลิกเข้ารหัสรอบสอง · (ข) หรือใช้ตัวเข้ารหัสเดียวกับที่ `VideoEditor` เลือก (AMF/NVENC) · (ค) ตรวจ `HAS_NVENC` ด้วยการทดเข้ารหัสจริงตามที่ `video_editor._probe_hardware_encoder` ทำ (ได้แค่ ~0.1 วิ) | **−51.6 วิ ต่อคลิปบนเครื่องนี้ (วัด)** · บนเครื่อง RTX 4060 ยังไม่ได้วัด (NVENC น่าจะเหลือไม่กี่วิ แต่อย่าประเมินเอา) | (ก) ภาพต่างเล็กน้อย (sharpen ก่อนบีบอัดแทนหลังบีบอัด · ต้อง framemd5/SSIM + ดูตา) · (ข) ขนาดไฟล์/คุณภาพต่าง · ต้องให้เจ้าของเลือก | M |
| ข2 | [script_tone_analyzer.py:124-235](../../scripts/script_tone_analyzer.py) | ตัวจำแนกโทนใช้งบเวลา 20 วิ + timeout ต่อ request 12 วิ · วันนี้ Gemini ช้า → ตัน**ทั้งงบ** แล้วตกไปกฎเดิม: cProfile `classify_tone_shifts` **24.2 วิ** จาก shot_matching 29.3 วิ (ดราฟต์ warm 3 ครั้ง: 26.2–29.3 วิ) · คำตอบไม่ถูกแคช เมื่อล้ม → ซ้ำทุกดราฟต์ · เทียบช่วงที่ 5 (RTX, API เร็ว): 4.6–6.8 วิ | circuit breaker: ล้ม/timeout 2 ครั้งติดกันใน session → ข้ามไปกฎเดิมทันที 10 นาที · หรือลดงบเหลือ ~8 วิ | **−15 ถึง −20 วิ ต่อดราฟต์ เมื่อ API ช้า (ประเมินจาก 24 → ~8)** · เมื่อ API ปกติ ไม่เปลี่ยน | เมื่อ API ช้าแต่ยังตอบได้ในเวลาเกินงบใหม่ → ได้ transition จากกฎเดิมแทนโทนจาก AI (ภาพต่าง) | S |
| ข3 | [video_assembly_stage.py:296-399](../../scripts/stages/video_assembly_stage.py) · [subtitle_second_pass.py](../../scripts/subtitle_second_pass.py) | ข6 เผาซับสองรอบ (เปิดทุกครั้งที่ resume_from มีค่า = เรนเดอร์จาก editor ทุกครั้ง) · วัดบน GOC01 42 วิ ผ่าน pipeline จริง: รอบแรกหลังแก้ timeline **43.0 วิ** (รอบ 1: 26.7 + รอบ 2: 10.7 + QA 2.8) เทียบรอบเดียว **33.3 วิ** (34.0/32.6/33.3) → **+9.7 วิ (+29%)** · เรนเดอร์ซ้ำที่ภาพใต้ซับไม่เปลี่ยน **15.8–16.1 วิ** (−17.2 วิ) · เครื่องนี้ส่วนเกินของรอบแรกมากกว่าเครื่อง RTX (+1.3 วิ) เพราะ AMF เข้ารหัสไฟล์กลางช้า | เปิดสองรอบเฉพาะเมื่อ editor รู้ว่า "แก้เฉพาะซับ/ข้อความ Hook" (ใช้ dirty flag เดียวกับ ก4) ส่วนแก้ timeline → รอบเดียว | แก้ซับอย่างเดียว −17 วิ (วัดแล้วมีอยู่) · แก้ timeline ได้คืน −9.7 วิ | แก้ timeline จะกลับไปได้ผลรอบเดียวเหมือนก่อนช่วงที่ 4 (SSIM ต่างจากสองรอบ 0.0018) | M |
| ข4 | ค้างจากรอบก่อน | `zoompan` (−3 วิ, SSIM Y 0.975, ภาพเลื่อน) · ข5 ตรวจเฟรมดำในกราฟ (สุทธิ ≤1 วิ) · ก2 cache ผลทดสอบตัวเข้ารหัส (1.19 วิ ต่อการเปิด backend — วัดซ้ำในรอบนี้ใน cProfile `_probe_hardware_encoder` 1.191 วิ) | ไม่ทำใหม่ — ดูรายการ "ต้องตัดสิน" | | | |

### เรื่องความถูกต้อง (ไม่ใช่ความเร็ว แต่พบระหว่างวัดและควรแก้ก่อนความเร็ว)

| # | ที่ | สิ่งที่พบ | หลักฐาน |
| :-: | :-- | :-- | :-- |
| **R1** | [audio_mix_stage.py:198-203](../../scripts/stages/audio_mix_stage.py) (commit `55f8a5a`) | `AudioMixStage` เรียก `trim_silence_and_tail_artifacts_wav(ctx.voice_audio_path)` **เขียนทับ `voiceover.wav` ในโปรเจกต์ทุกครั้งที่ stage นี้รัน** (รวมกรณีใช้มิกซ์เดิมซ้ำ) → เหตุเดียวกับ 2026-11-08 และ**ย้อนผล `tools/restore_voice_lead.py`** (`8be3372`) | (1) สำเนาของ `voiceover.wav` ทั้ง 59 ไฟล์ในเครื่องนี้: **58 ไฟล์จะถูกเขียนทับ** (ตัดหัวค่ากลาง **0.171 วิ** สูงสุด 0.27 วิ · ตัดท้าย 56 ไฟล์) (2) รัน pipeline จริงกับสำเนา `HOY01-โปรไฟลุก_1` (`--resume-from mix`): sha256 เปลี่ยน, ความยาว 45.047 → 44.700 วิ, เสียงพูดในมิกซ์เดิมเริ่ม**ช้ากว่าไฟล์เสียง 0.17025 วิ** (วัดด้วยฟังก์ชัน cross-correlation ของ `restore_voice_lead`) · รอบสองไม่เปลี่ยนซ้ำ (idempotent) (3) ตัวกรองสองชั้นเพิ่มเวลา **11 ms ต่อไฟล์** (ค่ากลาง n=59, สูงสุด 1.08 วิรอบแรก) · ผลต่อมิกซ์: เมื่อแก้ BGM/SFX ครั้งถัดไป เสียงพูดจะนำซับ ~0.17 วิ (**ยังไม่ได้รันรีมิกซ์ยืนยัน** ใช้ผลวัดออฟเซตข้างบน) |
| | | **ไม่ได้ทดสอบ:** เส้นทาง fingerprint แบบเข้ม (`incremental_render`) ว่าเสียงถูกเขียนทับแล้วสั่งยิง TTS ใหม่ไหม — data root สำเนาไม่มี metadata แบบเข้ม · อ่านโค้ด: `finalize_incremental_render` ประทับหลัง pipeline จบ จึงน่าจะตรงกับไฟล์ที่ถูกตัดแล้ว แต่ยังเป็นการอ่านโค้ด · **ไฟล์เสียง 7 คลิป TRA03 ไม่มีในเครื่องนี้** (ไม่มีโปรเจกต์ TRA ใน `03_Projects`) จึงตรวจไฟล์จริงของ TRA03 ไม่ได้ ตรวจได้เฉพาะโค้ดและไฟล์ 59 ไฟล์ที่มี · ไม่ได้แก้ไฟล์เสียงใด ๆ |
| **R2** | [batch_render.py:128-141](../../scripts/batch_render.py) → [media_validation.py:169-230](../../scripts/media_validation.py) | `is_valid_mp4` (ประตู resume ของ batch) ตอบ **valid** ให้ไฟล์ +faststart ที่ถูกตัดครึ่ง ขัดกับ docstring (audit S6-03): ffprobe เห็น moov ครบ, การถอดท้าย `-sseof -1` ไม่ error, แต่ `ffmpeg -i` ถอดทั้งไฟล์ได้ `partial file` | ทดสอบสำเนาไฟล์ 41.8 MB ตัดครึ่ง → `validate_mp4(use_cache=False)` = `ok True` duration 42.07 วิ · ผลคือ item ที่ค้างครึ่งไฟล์อาจถูกข้ามแล้วนับว่า rendered |
| R3 | [api_iphone.py:94-132](../../scripts/api_iphone.py) | ดึงสถานะ iPhone เรียก PowerShell ใหม่ทุกครั้ง 1.3–1.8 วิ (ไม่มีอุปกรณ์) และบนเครื่องไทยเกิด `UnicodeDecodeError` (ผลลัพธ์ cp874 ถูกถอดเป็น utf-8) → `error: 'NoneType' object has no attribute 'strip'` · เรียกเมื่อเปิดหน้าต่างเท่านั้น (ไม่ poll) | รันตรง `get_iphone_status()` 3 ครั้ง (ไม่ใช้ `PYTHONUTF8`) |

## 2. ตารางเทียบกับรอบก่อน

> เปรียบเทียบเฉพาะเครื่องเดียวกัน (Ryzen 7 7735HS, ช่วงที่ 1) · ตัวเลขช่วงที่ 3–5 เป็นเครื่อง RTX จึงใส่เป็นข้อมูลอ้างอิงแต่ไม่ตัดสินดีขึ้น/ถดถอย

| รายการ | รอบก่อน | ตอนนี้ (Ryzen) | สถานะ | เหตุ |
| :-- | :-- | :-- | :-: | :-- |
| ร่างแรก: ซับสองภาษา (cold cache) | 125.6 วิ (110.8–147.9, n=4) | **25.5 วิ** (n=1) | ดีขึ้น | ช่วง 2: ข้าม Google เมื่อโดน 429 ไปตัวสำรองทันที |
| ร่างแรก: ซับ (warm) | — | 2.1 วิ (n=3) | ดีขึ้น | cache คำแปลลงดิสก์ (ก1 ช่วง 2) |
| ร่างแรก: shot_matching warm | 2.5 วิ (ช่วง 1, โทน cache) / 4.6–6.8 วิ (ช่วง 5 RTX) | **26.2–29.3 วิ** (n=3) | **ถดถอย (สภาพแวดล้อม)** | Gemini ช้าวันนี้ + ไม่มี circuit breaker (ข2) · ไม่ใช่การเปลี่ยนโค้ดตั้งแต่ 11-12 (`shot_matching_stage.py` เพิ่มแค่การสแกนโฟลเดอร์ Flow) |
| ร่างแรก: ทั้งก้อน (AI เขียนบทไม่นับ) | ~162 วิ (ช่วง 1) | **70 / 81 / 86 วิ** warm · 277 วิ cold | ดีขึ้น (warm) | ซับ −123 วิ · เสียง API 12.5–21.1 วิ (n=4) |
| ร่างแรก: ขั้นสร้างบท | 31.5 วิ (CLI ล้ม + API) | API 44.4–47.4 วิ (n=1 ต่อค่า) · CLI ล้มที่ 0.00 วิ | เท่าเดิม/แกว่ง | เวลา = API ล้วน (ข้อ 3.1) |
| เรนเดอร์ 1 คลิป ~42 วิ (รอบเดียว) | 42.96 วิ (HOY01, ช่วง 1) | **33.3 วิ** (GOC01 18 คลิป, n=3) | ดีขึ้น (คนละโปรเจกต์) | เงา Hook (ข2 ช่วง 2) · ยืนยันคำสั่งเหมือนเดิม |
| เรนเดอร์ซ้ำ (เผาซับรอบสอง) | 7.4 วิ (RTX) | **15.8–16.1 วิ** (n=2) | เท่าเดิมตามเครื่อง | ภาพใต้ซับไม่เปลี่ยน |
| เรนเดอร์ซ้ำหลังแก้ timeline (รอบสองครั้งแรก) | +1.3 วิ (RTX) | **+9.7 วิ** | ถดถอยบนเครื่องนี้ | ไฟล์กลาง 26.7 วิบน AMF (ข3) |
| **หลังเรนเดอร์ต่อคลิป** | ไม่มี | **+51.6 วิ** sharpen + 0.5 วิ ปก | **ถดถอย** | commit `f5b61c8` (ข1) |
| Batch คลิป/นาที (c=1) | 1.48 (ช่วง 1, replay คำสั่ง) | **1.80** ปิด sharpen (n=3) / **0.71** เปิด sharpen (n=3) | เปิด sharpen = ถดถอย | ข1 · ครั้งนี้ผ่าน `BatchRenderManager` จริง |
| Batch c=2/3/4 | 1.92 / — / 2.22 คลิป/นาที, RAM เต็ม 13.7 GB ที่ 4 งาน | **วัดไม่ได้** (guard ตัด 3 ครั้ง) | ถดถอย/ไม่ปลอดภัย | RAM 3.1 GB ต่องาน · ก1 |
| Editor seek ท้าย 100 คลิป | 478 ms (RTX) | 345 / 557 / 483 ms (ค่ากลาง 483) | เท่าเดิม | ข้อ 4.1 (เป็นเวลาโหลด ไม่ใช่ seek) |
| Editor seek ท้าย 50 คลิป | 40 ms (RTX) | 200 / 85 / 111 ms | — | |
| Lighthouse (หน้าแรก, desktop) | ไม่ได้รัน | **100** ทั้ง 3 รอบ · FCP/LCP 309 ms · TBT 0 · CLS 0 · 530 KB | ใหม่ | วัดเฉพาะหน้าแรก (`/`) |
| ถอดรหัส VP9 alpha (cutout) | ไม่ได้วัด | 0.8–1.0 วิ / 148 เฟรม (≈ h264 ช่วงเวลาเท่ากัน 1.08 วิ) | ใหม่ | ข้อ 3.5 |

## 3. ที่รอบก่อนยังไม่ได้วัด (หัวข้อ B)

### 3.1 ค1 — Antigravity CLI ล้มด้วย WinError 206
- **ยังเกิดอยู่** prompt สร้างบทจริงยาว **47,868 ตัวอักษร** > 32,767 (ขีดจำกัด CreateProcess) → `FileNotFoundError: [WinError 206]` ที่ **0.00 วิ** (ล้มก่อนสร้าง process)
- **เวลาที่ทิ้งเปล่าก่อนถอยไป API = ~0** เวลา 31.5 วิในรายงานเดิมเป็นของ API ทั้งก้อน
- `generate()` เรียก CLI ก่อน 44.4 วิ เทียบ API ตรง 47.4 วิ (n=1 ต่อค่า อยู่ในความแกว่ง)
- CLI ด้วย prompt สั้น ("ตอบ ok") ใช้ **67.9 วิ** → ต่อให้แก้ 206 (ส่งผ่าน stdin) CLI ก็ช้ากว่า API · **ไม่ควรแก้** นอกจากข้ามการเรียก CLI เมื่อ prompt ยาวเกินเพื่อตัด log รก

### 3.2 ค2 — `word_alignment` (faster-whisper)
- **ยังไม่ได้วัด** เครื่องนี้ไม่มี CUDA และ `.venv` ไม่มี `faster-whisper` ขั้นนี้ถูกข้ามเงียบ ๆ (editorial pacing/SpecBar ตามคำพูดไม่ทำงานบนเครื่องนี้)
- ที่อ่านโค้ด (`scripts/word_alignment.py:68-143`, ไม่ใช่การวัด): โมเดลโหลดครั้งเดียวต่อ process (`_MODELS` + lock) ไม่โหลดซ้ำทุกงาน · ถอดเสียงถูก serialize ด้วย `_TRANSCRIBE_LOCK` · ถ้าไม่มี CUDA ใช้ `cpu/int8`
- ต้องวัดบนเครื่อง RTX: cuda/float16 เวลาจริง, VRAM ขณะ 4 render

### 3.3 Vision cold / motion ครั้งแรก — วัดแล้ว (ข้อ ก8)
ดราฟต์ cold (cache vision/motion/tone/คำแปลของสำเนา data root ถูกย้ายออก ไม่ใช่ cache จริง): total 277.4 วิ · voice 12.5 · subtitles 25.5 · shot_matching **199.2** (vision 119.3 = proxy 17.0 + upload 29.8 + generate ≈72 · motion 45.8 · rms 10.0) · ffmpeg 38.8 · ใหม่ครั้งแรกเท่านั้น API ช้ากว่าปกติ (ข้อ 0.3)

### 3.4 โปรเจกต์ 60 วินาที
สคริปต์ GOC01 เสริมให้เสียงยาวขึ้น (9 บรรทัด / 876 ตัวอักษร) → ได้ **56.3 วิ** และ **61.3 วิ** (n=2 ดราฟต์ใหม่):

| ขั้น | รอบ a (ข้อความใหม่ cold) | รอบ b |
| :-- | --: | --: |
| voice | 17.5 | 31.1 |
| subtitles | 2.5 | 3.2 |
| mix | 1.7 | 1.9 |
| shot_matching | **170.0** (vision รอบข้อความใหม่) | 13.4 |
| ffmpeg_assembly | **42.4** | **37.3** |
| รวม | 235.0 | 87.8 |

เรนเดอร์ขยายตามความยาวเกือบเส้นตรง (33.3 วิ/42 วิ → 37–42 วิ/56–61 วิ) · sharpen ของคลิป 60 วิ ไม่ได้วัด (ประเมิน ≈ 51.6 × 60/42 ≈ 74 วิ จากสัดส่วนความยาว)

### 3.5 cutout VP9 alpha
- **สร้าง:** `process_background_isolation_video` หน้าต่าง 1.5 วิ (45 เฟรม) rembg u2net CPU = **56.0 วิ wall** (1.24 วิ/เฟรม รวมโหลดโมเดล) · manifest เก่าบันทึกไว้ 0.845 วิ/เฟรม (เครื่องอื่น) · RSS ใน process 1.1 GB → คลิป 5 วิ (150 เฟรม) ≈ **3 นาที**
- **ถอดรหัส:** `libvpx-vp9` alpha 148 เฟรม 1080x1920: 0.79 / 1.02 / 0.90 วิ เทียบ h264 60fps 4.93 วิ: 1.07–1.11 วิ → ถอดไม่แพงกว่าฟุตเทจปกติ
- **ยังไม่ได้วัด:** ต้นทุน composite ใน render จริง (โปรเจกต์ตัวอย่างปิด cutout และ artifact ไม่ตรง id)

### 3.6 แปลหลายท่อนต่อ request (batching)
**ทดสอบไม่ได้** Google Translate ตอบ `TooManyRequests` ทั้ง request เดี่ยวและแบบรวม 8 ท่อน (1.2–1.5 วิ ต่อครั้ง) จากเครื่องนี้ ไม่มีโค้ดใหม่ที่พิสูจน์ความตรงของบรรทัดไม่ได้

## 4. Editor (หัวข้อ C)

### 4.1 Seek ท้ายคลิป 100 คลิป (478 ms)
- ทำซ้ำได้: 3 รอบ 100 คลิป = 345 / 557 / 483 ms · 50 คลิป = 200 / 85 / 111 ms · 10 คลิป ~48 ms
- **สาเหตุ = เวลาโหลดของ `<video preload="auto">` 100 ตัว ไม่ใช่การ seek:** เมื่อรอให้พรีวิวนิ่ง 1.5 วิก่อน (โพรบแยก) ทุกตัว readyState 4 และ seek ท้ายใช้ **54–65 ms ที่ 50 คลิป · 64–67 ms ที่ 75 · 80–97 ms ที่ 100** ไม่มี long task ระหว่าง seek · เทสเดิมจับเวลาเริ่มทันทีหลัง mount จึงรวมเวลารอโหลด
- ผลกับงานจริง: โปรเจกต์จริง ~18 คลิปไม่ถึงจุดนี้ → **ไม่ต้องแก้**

### 4.2 proxy · filmstrip · audioPeaks · autosave · reroll · scrub — สรุปตัวเลข

| หัวข้อ | ผลวัด | ข้อสรุป |
| :-- | :-- | :-- |
| proxy | alone 12.7 วิ (223 MB) / 48.5 วิ (517 MB) / 23.1 วิ (252 MB) · 3 ตัวพร้อมกัน wall 98 วิ (> 84 วิ ทำทีละตัว) CPU เฉลี่ย 99% · เรนเดอร์ขณะนั้น 88.7 วิ เทียบ 42.0–47.4 วิ | ก2 · จำนวนพร้อมกัน = จำนวน source ไม่ซ้ำ (GOC01: 18 คลิป / 1 source) |
| `preload="auto"` | ที่ 100 คลิป: media request 14–18 ครั้ง, JS heap 42–50 MB (1 คลิป 33 MB) · ไม่ได้วัดแบนด์วิดท์ต้นฉบับก่อนสลับ proxy แยก | ไม่พบปัญหาที่ขนาดจริง · **ไม่ได้วัดแยกเรื่องแบนด์วิดท์** |
| filmstrip | ก3 | |
| audioPeaks | decode 98–126 ms (ครั้งแรก 438 ms, อยู่นอก main thread) · reduce 5–16 ms บน main thread · **long task 0 ครั้ง** (wav 45.2 วิ, 8 MB) · แต่ละ LOD (600/2400/9600) decode ซ้ำ ครั้งละ ~100 ms | ไม่ใช่คอขวด |
| autosave (`PATCH /state`, payload 7.4 KB) | ว่าง: ค่ากลาง 55–62 ms, p95 79–90, สูงสุด 149–187 · **ระหว่างเรนเดอร์ใน process เดียวกัน** (n=98): ค่ากลาง **113 ms**, p95 **320 ms**, สูงสุด **1,573 ms** · ตัวควบคุม (ffmpeg กิน CPU ไม่แตะ manifest, n=19): ค่ากลาง 158 ms สูงสุด 188 ms | UI ไม่ค้างนาน แต่มี spike ถึง 1.6 วิ ที่ CPU อย่างเดียวอธิบายไม่ได้ · **ยังไม่ได้แยกว่าเป็น `_SAVE_LOCK` หรืออย่างอื่น** |
| reroll | ก4 | −2.3 วิ ต่อเรนเดอร์จาก editor |
| scrub (INP) | ก7 · ฟิกซ์เจอร์ dev build | ต้องวัดบน build จริง |
| Lighthouse ×3 | ตารางข้อ 2 | หน้าแรกอย่างเดียว |

## 5. Batch (หัวข้อ D)

ผ่าน `BatchRenderManager` จริง ผลิต 3 คลิปต่อรอบ (ใช้ angle ของสินค้าจริงในสำเนา, TTS แทนด้วยสำเนาไฟล์เสียงเดิม, โทน=[] , vision/สองภาษาปิด ไม่เสียค่า API ในรอบ batch) · ต้องหยุดทดสอบ N ใหญ่เพราะ RAM

| concurrency | sharpen | N | wall | คลิป/นาที | CPU เฉลี่ย | RAM ว่างต่ำสุด | ผล |
| :-: | :-: | :-: | --: | --: | --: | --: | :-- |
| 1 | เปิด | 3 | 254.4 วิ | **0.71** (85 วิ/คลิป: 88/178/254) | 68% | 1,821 MB | สำเร็จ 3 |
| 1 | ปิด | 3 | 100.1 วิ | **1.80** (33 วิ/คลิป: 36/68/100) | 36% | 1,653 MB | สำเร็จ 3 |
| 2 | เปิด | 2 | 56 วิ | — | | 21 MB | **guard ตัด** (RAM ว่าง < 300 MB) |
| 2 | ปิด | 4 | 24 วิ | — | | 86 MB | **guard ตัด** (เริ่มที่ว่าง 3,777 MB) |
| 3 | ปิด | 6 | 18 วิ | — | | 227 MB | **guard ตัด** (เริ่มที่ว่าง 4,253 MB) |
| 4 | ปิด | 8 | 24 วิ | — | | 231 MB | **guard ตัด** (เริ่มที่ว่าง 4,740 MB) |

- **batch 20 คลิป ที่ concurrency 2/3/4 ทำไม่ได้บนเครื่องนี้** ตามที่ผู้ใช้สั่งห้ามเกิน 4 · จึงไม่มีตัวเลขคลิป/นาที, ตัวไหนตันก่อน: ตอบได้ว่า **RAM ตันก่อน CPU** (CPU เฉลี่ย 28–35% ตอน guard ตัด) · ผมตั้ง guard ที่ 300 MB เพื่อไม่ให้เครื่องผู้ใช้ค้าง ไม่ได้ปล่อยให้ swap
- ประเมิน (ไม่ใช่วัด) 20 คลิป c=1: เปิด sharpen ≈ 28 นาที (20 × 85 วิ) · ปิด sharpen ≈ 11 นาที (20 × 33 วิ)
- `is_valid_mp4`: ตรวจไฟล์ 41.8 MB ครั้งแรก 373 ms ครั้งถัดไปจาก cache 0.2–0.4 ms · **การข้ามเมื่อรันซ้ำจริงทั้ง batch ไม่ได้ทดสอบ** (guard ตัดรอบที่เตรียมไว้) · พบช่องความถูกต้อง R2
- VRAM / GPU: ไม่ได้วัด (ไม่มี NVIDIA)

## 6. ถดถอยหลัง 2026-11-12 (หัวข้อ A) — สรุปตาม commit

| ที่ตรวจ | ผล | สถานะ |
| :-- | :-- | :-- |
| Flow B-roll เข้า shot matching / draft (`6c59962`, `1be00dd`, `6f8c587`) | เส้นทาง pipeline ทำแค่ glob โฟลเดอร์ `01_Raw/<id>/AI_Flow/` ในเครื่อง (ไม่มี network, ไม่ ffprobe) ถ้าไม่มี `beat_cues` หรือไม่มีคลิป Flow คืนค่าทันที · ในเครื่องนี้ไม่มีโฟลเดอร์ `AI_Flow` ดราฟต์ 6 รอบไม่มีสายเรียก Flow · `draft_generator.py` ไม่มีผู้เรียกใน pipeline | **ไม่ทำให้ร่างแรกรอ Flow** · Flow ล่ม/ไม่ login = ข้ามทันที · **ยังไม่ได้วัด**เวลา glob เมื่อมีคลิป Flow จริงหลายสิบไฟล์ |
| backend poller / auto-ingest แย่ง CPU/ดิสก์/lock กับ render | poller ตั้งต่อ job เท่านั้น (thread หลับ 4 วิ) ไม่มี job Flow → ไม่ทำงาน · daemon นิ่ง 115 MB RSS / CPU 1.7% · เปิด backend ช้าลง ก5 · Topbar poll ก6 | ผลกระทบเล็ก · **ยังไม่ได้วัดตอนมี job Flow จริงกับ render พร้อมกัน** (ต้อง login + ใช้เครดิต) |
| TTS tail fix (`55f8a5a`) | R1 · ตัวกรองสองชั้น +11 ms | **ถดถอยด้านความถูกต้อง** |
| iPhone direct ingest + LAN chunked upload | อัปโหลด 224 MB ผ่าน loopback 1.2 วิ (188 MB/s) · handler 43 ms/chunk (ค่ากลาง, สูงสุด 99) · `complete` (sha256 + ย้ายไฟล์) 1.34 วิ · API ping ค่ากลาง 16 → 21 ms, p95 27 → 52, สูงสุด 39 → **277 ms** ตอนอัปโหลด | เล็กน้อย (`append_upload_chunk` เป็น `async def` เขียนไฟล์แบบ sync บน event loop แต่ไม่ถึงขั้นค้าง) · ดึงผ่าน USB ยังไม่ได้วัด (ไม่มี iPhone) |
| ปกอัตโนมัติ (`ensure_default_cover`) | 0.5 วิ ต่อคลิป (ครั้งแรก +1.8 วิ เลือกเฟรม) | ไม่ใช่ปัญหา |
| auto sharpen (`f5b61c8`) | ข1 | **ถดถอยใหญ่สุด** |
| โค้ด render (`video_editor`, `video_assembly_stage`, `pipeline`) | ไม่เปลี่ยน | — |
| `GOC01-รีวิวสเปก_1` เทียบ 10.1 / 8.1 | RTX 17.9–19.2 วิ (8.1) ↔ Ryzen 33.3 วิ (รอบเดียว) · คำสั่ง ffmpeg ไม่ต่าง | เทียบข้ามเครื่องไม่ได้ |

## 7. ต้องตัดสิน (รวมของรอบก่อน)

1. **R1** ถอด `trim_silence_and_tail_artifacts_wav` ออกจาก `AudioMixStage` (ตัดแล้วตอนสร้างเสียงอยู่แล้ว) · ต้องตัดสินว่าจะ**คืนช่วงเงียบต้นไฟล์**ให้ 58 โปรเจกต์ที่ถูกตัดได้ทันทีหรือไม่ (`tools/restore_voice_lead.py` ทำได้ แต่ไม่ได้รันในรอบนี้)
2. **ข1** auto-sharpen: ทางใดจาก (ก) รวมเข้ากราฟ render รอบเดียว (ข) ใช้ตัวเข้ารหัสเดียวกับ render (ค) ปิดบนเครื่องที่ไม่มี NVENC — แลกกับภาพ/ขนาดไฟล์ต่างเล็กน้อย
3. **ข2** circuit breaker ของตัวจำแนกโทน (ภาพต่างเมื่อ API ช้า)
4. **ข3** เปิดเผาซับสองรอบเฉพาะแก้ซับอย่างเดียว
5. **ก1** concurrency อัตโนมัติตาม RAM (ลดจาก 4 เมื่อ RAM ว่างน้อย)
6. ถอด `02_Assets` ออกจาก `delete_file` — `SystemAssets.jsx:101` และ `MediaAssetsHub.jsx:209` ยังใช้ endpoint นี้ลบไฟล์ที่ผู้ใช้อัปโหลดเอง (รอเจ้าของตัดสินมาตั้งแต่รอบก่อน)
7. **ข4 `zoompan`** (ภาพเลื่อน SSIM 0.975) · **ข5** ตรวจเฟรมดำในกราฟ (สุทธิ ≤1 วิ) · **ก2 เดิม** cache ผลทดสอบตัวเข้ารหัส (1.2 วิ ต่อการเปิด backend) — ขอยืนยัน "ปิด ไม่ทำ"
8. **R2** ซ่อม `validate_mp4` ให้จับไฟล์ที่ถูกตัดครึ่ง (ถอดทั้งไฟล์หรือเทียบ duration จาก mdat กับ moov) — แก้ความถูกต้อง ราคาคือเวลาตรวจ
9. ติดตั้ง `faster-whisper` ใน `.venv` ของเครื่องนี้ (ตาม requirements) หรือไม่ — ทำให้ขั้น word alignment รันบน CPU (int8, เพิ่มเวลาร่างแรก) ซึ่งยังไม่ได้วัด
10. ลบ `.tmp/speed_audit/` — ขนาดรวม `.tmp/` **2.9 GB** (เกิน 1 GB ที่ตกลงไว้ ไม่ได้ลบ ถามก่อน)

## 8. ยังไม่ได้วัด (และเหตุผล)

| รายการ | เหตุผล |
| :-- | :-- |
| faster-whisper cuda/float16, VRAM ตอน 4 render, NVENC ของ sharpen/render, batch ที่ RTX 4060 | เครื่องนี้ไม่มี CUDA/NVENC และไม่มี `faster-whisper` ใน `.venv` |
| batch 20 คลิป ที่ concurrency 2/3/4 · `is_valid_mp4` skip ทั้ง batch | RAM ว่างไม่พอ (guard ตัดที่ 300 MB ทั้ง 4 ครั้ง) · เครื่องผู้ใช้ใช้งานอยู่ |
| ไฟล์เสียง 7 คลิป TRA03 · เส้นทาง fingerprint แบบเข้มหลังถูก trim (ยิง TTS ใหม่ไหม) · รีมิกซ์หลัง trim จริง | ไม่มีไฟล์ TRA03 ในเครื่องนี้ · data root สำเนาไม่มี metadata `incremental_render` · ไม่อยากเสียค่า TTS |
| Flow poller / auto-ingest ขณะเรนเดอร์จริง · เวลา glob Flow เมื่อมีคลิปหลายสิบไฟล์ | ต้อง login และใช้เครดิต Google Flow |
| iPhone ดึงผ่าน USB | ไม่มีอุปกรณ์ |
| แปล batching | Google ปฏิเสธ (TooManyRequests) |
| cutout composite ใน render | โปรเจกต์ตัวอย่างปิด cutout · artifact ไม่ตรง id |
| scrub INP / จำนวน render บน production build | ฟิกซ์เจอร์ใช้ Vite dev (StrictMode) |
| `preload="auto"` ปริมาณแบนด์วิดท์ก่อนสลับ proxy | ไม่ได้ตั้งเครื่องมือจับแบนด์วิดท์ |
| Lighthouse หน้าอื่นนอกหน้าแรก | หน้าอื่นต้องเข้าผ่าน UI/โปรเจกต์ ไม่มี URL ตรง |
| pytest เต็มชุด | ช่วงที่ 1 ไม่แก้โค้ด · `test_sam2_preflight_check` รันเดี่ยวผ่าน (6 ผ่าน 1 ข้าม) หลัง stub RAM/ดิสก์ในเทส · ยังไม่ได้รันทั้งชุดซ้ำเพื่อดูว่ายังล้มตอนรันรวมไหม |

## 9. วิธีวัดซ้ำ

- `tools/speed_audit/harness.py rerender <โปรเจกต์> <label> --resume-from video [--fresh] [--no-export]` (OMNICUT_SUBTITLE_SECOND_PASS=0 เพื่อรอบเดียว)
- สคริปต์รอบนี้ (ใน `.tmp/speed_audit/r2/`): `a_post_render.py` (sharpen/ปก), `a3_trim_probe.py` + `e_offset.py` (R1), `a1_backend_start.py` / `a1_compare.py` (เปิด backend + Flow), `a_upload.py`, `a_flow_status.py`, `b_c1_cli.py`, `b_tone_probe.py`, `b_cutout_create.py`, `c_proxy.py`, `c_filmstrip.py`, `c_peaks.py`, `c_autosave.py` / `c_autosave_ctrl.py`, `c_lh.py`, `d_batch.py`, `pt/test_seek_probe.py`, `pt/test_scrub_probe.py`
- data root: คัดลอก `02_Assets` + โฟลเดอร์โปรเจกต์ลง `.tmp/speed_audit/data/` → `fix_paths.py` (ใช้ `01_Raw` สำเนาด้วยถ้าต้องผ่าน API ที่ตรวจ ownership) · `_Docs/products.json` ต้องคัดลอกด้วยถ้าเรียกผ่าน API
