# 📋 OmniCut Pro Studio — Todo กลาง

สมุดบันทึกรอบงานที่ **ยังไม่เสร็จ** ของโปรเจกต์นี้ — ทุกงานต้องผ่านไฟล์นี้ก่อนแตะโค้ด

| ไฟล์ | ใช้ทำอะไร |
| :--- | :--- |
| **TODO.md** (ไฟล์นี้) | งานที่ยังไม่เสร็จ + Backlog — เขียนแผนลงที่นี่ก่อนลงมือ |
| [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md) | รอบที่ปิดแล้ว ย้ายบล็อกเต็มไปเก็บไว้ที่นั่น ห้ามแก้ย้อนหลัง |
| [TEMPLATE_MOTION_PLAN.md](file:///d:/Winona/Programmer/Capcut/TEMPLATE_MOTION_PLAN.md) | แผนยาวของงาน motion ข้อความ (Round 3–7) — เหตุผลและตัวเลขที่วัดมา |
| [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md) | กติกาว่าหนึ่งรอบทำยังไง ติ๊กยังไง ปิดรอบยังไง |

---

## สถานะรวม

- [x] Round DOC-1 — ตรวจโค้ดและอัปเดตเอกสาร/กฎให้ตรงกับระบบปัจจุบัน
- [x] Round BUG-1 — แก้ปุ่มสร้างคลิปใหม่กดไม่ได้ (executeRender ใน useRenderJob)
- [x] Round 4 — per-word layout (static, พิสูจน์ว่าเหมือนเดิมเป๊ะ)
- [x] Round 5 — per-word animation (คำทยอยเข้าทีละคำ)
- [x] Round 6 — ช่องใหม่ที่ mirror ได้เป๊ะ
- [x] Round 7 — template v2 + แกลเลอรีที่ขยับได้
- [x] Round BUG-2 — แก้ข้อความและ Hook Header ซ้อนทับกันเป็นก้อนใน SequencePlayer
- [ ] Round POST-1 — Desktop Post Studio (ปก + ลากไฟล์ + แคปชั่น + ปิดวงจร Posted)
- [ ] Round POST-2 — TikTok auto-post extension (พักไว้ตามคำสั่ง User)
- [x] Round BUG-3 — ซ่อม angle ชนกัน (คลิปผิดสคริปต์) ใน Content Tracker Hub + ปุ่มปักตะกร้า TikTok
- [x] Round PROD-1 — เพิ่มช่องระบุ TikTok Product ID ตอนสร้างสคริปต์ใหม่ + Fallback ค้นหาด้วยชื่อสินค้า + Click-to-Edit Cart ID

**ปิดไปแล้ว** (บล็อกเต็มอยู่ใน [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md)):
Round 1 รวม overlay เป็นโมเดลเดียว · Round 2 วางกฎรอบงาน · Round 3 ซ่อมฐาน+easing · Round DOC-1 อัปเดตเอกสาร · Round BUG-1 ซ่อมปุ่มสร้างคลิป executeRender · Round 4 per-word layout static · Round 5 per-word animation (word_stagger_ms) · Round 6 ช่องใหม่ที่ mirror ได้เป๊ะ (loop/out/skew) · Round 7 template v2 + แกลเลอรีที่ขยับได้ (8 templates + motion presets + inspector animated gallery) · Round BUG-2 ซ่อมข้อความ/Hook Header ซ้อนทับกันใน SequencePlayer · Round BUG-3 ซ่อม angle ชนกัน + ปุ่มปักตะกร้า TikTok ใน Content Tracker Hub · Round PROD-1 เพิ่มช่อง TikTok Product ID + Fallback ค้นหาด้วยชื่อ + Click-to-Edit Cart ID ย้อนหลัง

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

## งานค้าง (Backlog)

รายการที่รู้แล้วว่าต้องทำ แต่ยังไม่ได้จัดเข้ารอบไหน
เจอของใหม่ระหว่างทาง → เขียนลงตรงนี้ทันที ห้ามทำเงียบๆ

### ยังไม่ได้ทดสอบ

- [ ] **กด generate เต็ม loop 1 รอบ** — Round 1 ยืนยันแล้วเฉพาะ ASS writer, เฟรม ffmpeg,
      save→reload, และ editor เปิดโปรเจกต์เก่า แต่ **ยังไม่เคยรัน `/api/render` ครบวงจร**
      (ต้องใช้วิดีโอดิบ + TTS key + เวลาหลายนาที)

### บั๊กที่เจอแล้วแต่ยังไม่ได้แก้

- [ ] **วรรณยุกต์ไทยชั้นสองยุบใน libass** — `เพิ่ง`→`เพีง`, `สิ่ง`→`สีง`
      (ส่วน `ซื้อ`/`นี้` ซ้อนถูก) กระทบทั้งแอป ไม่ใช่เฉพาะ overlay
      - หลักฐาน: เกิดที่ `bord0` ด้วย · เกิดครบทั้ง 6 ฟอนต์ (Prompt/Kanit/IBM Plex/Chakra Petch/Anuphan/Itim)
        · เกิดผ่าน caption path ที่ไม่ได้ถูกแก้เลย → เป็น mark positioning ของ libass เอง
      - ffmpeg build มี `--enable-libharfbuzz` แล้ว จึงไม่ใช่เรื่อง shaping ที่ปิดอยู่
      - ยังไม่ได้ทำ: หาสาเหตุจริง (font mark anchor? libass version?) และวิธีแก้

### ปรับปรุงที่ยังไม่จำเป็นเร่งด่วน

- [ ] `frontend/src/lib/overlayModel.js` มี export ที่ยังไม่มีใครเรียก (`baseFsRatio`, `ASS_ALIGNMENT`,
      `overlayToLegacy*`) — เก็บไว้เพราะเทสใช้ แต่ควรทบทวนว่าจะคงไว้หรือตัด

---

## รอบงาน

รอบที่ยังไม่ปิด เรียงจากที่ทำอยู่ไปข้างหน้า

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

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** กดปุ่มเดียวในแอป ให้ extension เติมไฟล์+ปก+แคปชั่นลงหน้าอัปโหลด TikTok ในเบราว์เซอร์ที่ login อยู่แล้ว
ไม่ต้องลาก ไม่ต้องพิมพ์เอง — รายละเอียด เหตุผล และหลักฐานความเสี่ยงทั้งหมดอยู่ที่
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
  ยังไม่ต้องแก้ตอนนี้เพราะพักรอบไว้แล้ว บันทึกไว้เผื่อพี่กลับมาเปิด auto-post-click ใหม่ในอนาคต

