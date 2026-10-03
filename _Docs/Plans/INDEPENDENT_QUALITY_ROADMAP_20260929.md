# แผนยกระดับ OmniCut ที่ไม่ทับงาน Antigravity — 2026-09-29

ดำเนินการโดย: Codex (GPT-6) · สถานะ: แผนใหม่ ยังไม่ลงมือแก้ฟีเจอร์

## เป้าหมาย

ลดคลิปที่ใช้วัตถุดิบผิด/มีซับต่างชาติ, ลดไฟล์เรนเดอร์เสียที่หลุดไปโพสต์ และทำให้กู้โปรเจกต์จาก backup ได้จริง โดยทำเครื่องมือตรวจที่อ่านไฟล์อย่างเดียวก่อนเชื่อมเข้าหน้าจอหลัก

## ขอบเขตที่กันชนกับงานอื่น

- **Antigravity กำลังทำ BiRefNet/Universal Badges**; SAM 2 เพิ่งปิดรอบ. แผนนี้ไม่แก้ segmentation, checkpoint, GPU runtime, sticker, `background_isolation*` หรือ `build_3d_pro_badges.py`.
- **Claude กำลังทำ Ghost Reveal** และ TODO เดิมมีงาน Editor/Preview parity. แผนนี้ไม่แก้ซับ, ฟอนต์, `SequencePlayer`, `EditorShell`, `video_editor.py` หรือ timeline.
- ไม่ติดตั้ง repository 6 รายการจากแผนเก่า ไม่แตะ TTS/WhisperX/CapCut Draft exporter. เครื่องมือตรวจรอบแรกเป็น standalone และ output ลง `.tmp/` เท่านั้น.
- ก่อนเริ่ม implementation แต่ละเฟสให้ตรวจ `git status`/`TODO.md` ใหม่ เพราะเจ้าของไฟล์และสถานะงานอาจเปลี่ยน.

## หลักฐานช่องว่างจากโค้ดปัจจุบัน

| สิ่งที่มีแล้ว | ช่องว่างที่แผนนี้จะปิด |
| :--- | :--- |
| `scripts/asset_dedup.py` ตรวจไฟล์ซ้ำด้วยขนาดและ SHA-256 | ยังไม่ตรวจความเสี่ยงซับต่างชาติฝังในภาพ, ภาพเสีย/เสียงเสีย และ model mismatch จากเนื้อภาพ |
| `scripts/gadget_media_quality.py` ตรวจความละเอียด, `product_key`, rights และ evidence ที่ผู้ใช้กรอก | ฟิลด์ที่กรอกไม่ได้พิสูจน์ว่าเฟรมวิดีโอสะอาดหรือเป็นสินค้ารุ่นเดียวกันจริง |
| `tools/golden_master_probe.py` ตรวจ metadata, เฟรมตัวอย่าง 3 จุด และระดับเสียงพื้นฐาน | อาจพลาดเฟรมดำ/ค้าง/เสียงหายกลางคลิป; ยังไม่มีรายงาน QA ของไฟล์ final แบบครอบคลุมทั้ง timeline |
| `scripts/backup_engine.py` สร้าง ZIP, มี manifest และ `verify_backup()` ตรวจความสมบูรณ์ของ ZIP | `scripts/api_backup.py` ไม่มี restore endpoint; ZIP เปิดอ่านได้ยังไม่พิสูจน์ว่าเอาไปเปิดโปรเจกต์บนเครื่องใหม่ได้ |

## แผนงานเรียงลำดับ

### Q1 — Media Intake Audit แบบอ่านอย่างเดียว (ทำก่อน)

**ผลที่ผู้ใช้ได้:** รายงานแต่ละคลิปว่า “ใช้ได้ / ต้องตรวจเอง / ใช้ไม่ได้” พร้อมเหตุผลและภาพตัวอย่างที่มีปัญหา ก่อนนำเข้าโปรเจกต์.

1. สร้าง `tools/media_intake_audit.py` และ test เฉพาะไฟล์นี้ โดยอ่านคลิปจาก path ที่ผู้ใช้ระบุ; ไม่ย้าย ลบ หรือเขียนทับ `00_Inbox/`, `01_Raw/`, `02_Assets/`.
2. ใช้ ffprobe ตรวจ codec, duration, resolution, fps, audio stream, ไฟล์อ่านได้จริง; ใช้ hash ที่มีอยู่เพื่อแจ้งไฟล์ซ้ำโดยไม่เพิ่มสำเนา.
3. ทำ spike ตรวจข้อความฝังในเฟรมจากหลายตำแหน่ง/ช่วงเวลา โดยวัดกับชุดคลิปที่คนติดป้ายว่า clean/foreign subtitle อย่างน้อยอย่างละ 10 คลิป. OCR ที่ไม่มั่นใจต้องออกสถานะ “ต้องตรวจเอง”; ห้ามประกาศว่าสะอาดจากการสุ่มเฟรมไม่กี่ภาพ.
4. ตรวจชื่อรุ่นจาก metadata/manifest ที่มีอยู่และแสดงความขัดแย้งเพื่อให้คนตรวจภาพจริง; ห้ามใช้ชื่อไฟล์หรือ OCR เพียงอย่างเดียวตัดสินว่ารุ่นถูก.
5. รายงาน JSON แบบ standalone ใน `.tmp/`; แสดง timestamp และข้อความ OCR ที่พบ. เมื่อ OCR ไม่มี/ขาดภาษาให้คงสถานะตรวจเอง; หลังพิสูจน์ false positive/false negative แล้วจึงวางแผนเชื่อม UI แยกรอบ.

**Gate:** สแกนไฟล์เสีย/ผิดสเปกได้แบบ deterministic; ไม่เขียนไฟล์ source; คลิปซับต่างชาติในชุดทดสอบต้องถูก flag ทุกคลิป โดยรายงานจำนวน clean ที่ flag ผิดจริง; ไม่ใช้ผล OCR เป็นหลักฐานอัตโนมัติเรื่องสิทธิ์หรือรุ่นสินค้า.

### Q2 — Final Export Audit ตลอดทั้งคลิป

**ผลที่ผู้ใช้ได้:** ก่อนโพสต์เห็นรายงานตำแหน่งเฟรมดำ/ภาพค้าง/เสียงเงียบผิดปกติ พร้อมสเปกไฟล์จริง โดยไม่ต้องเปิดตรวจแบบสุ่มเองอย่างเดียว.

1. เพิ่มโหมด scan ต่อเนื่องให้ `tools/golden_master_probe.py` หรือสร้าง adapter ใหม่ที่เรียก probe เดิม; ตรวจ resolution 1080×1920, 30 FPS, H.264/AAC, duration, audio peak และ A/V delta.
2. สแกนภาพดำ/เฟรมซ้ำต่อเนื่อง/ช่วงเงียบเป็นช่วงเวลา; แยกช่วงเว้นจังหวะตามเจตนาจากความผิดพลาดด้วยรายการ review ไม่ตัดสิน pass/fail แบบเดาสุ่ม.
3. สร้าง report พร้อม timestamp, signal, threshold และภาพตัวอย่างใน `.tmp/`; อ่านเฉพาะไฟล์ final ที่มีอยู่ ไม่สร้าง Demo ใน `04_Exports/` และไม่แก้ export registry.
4. เทียบผลกับคลิปดีและคลิปที่สร้างข้อผิดพลาดใน `tmp_path`; ดูเฟรมจริงและฟังช่วงที่แจ้งเตือนก่อนตั้ง threshold เป็น release gate.

**Gate:** fixture เฟรมดำ/ค้าง/เสียงหายที่รู้ตำแหน่งต้องถูกพบ; คลิปปกติไม่ถูก block ด้วย intentional pause; ใช้เวลาสแกน/พื้นที่ชั่วคราวที่วัดและบันทึกจริง; ไม่เปลี่ยนฟอนต์ ซับ หรือ render pipeline.

### Q3 — Backup Restore Drill และคู่มือย้ายเครื่องที่ตรวจได้

**ผลที่ผู้ใช้ได้:** รู้ว่า backup แต่ละชุดกู้โปรเจกต์กลับมาเปิดได้จริง ไม่ใช่เพียง ZIP ไม่เสีย.

1. ตรวจเนื้อหา `backup_manifest.json` กับ dependency ของโปรเจกต์: project files, DB snapshot, referenced media และ external files; แยกสิ่งที่ backup รวม/ไม่รวมให้ชัด. ไม่บรรจุ `.env` หรือ secret ลง ZIP.
2. สร้าง restore dry-run ใน `tools/` ที่แตก ZIP ลง `tmp_path`/`.tmp/` เท่านั้น ตรวจ path traversal, collision, checksum และ referential integrity แล้วลองโหลด manifest/DB จากพื้นที่ชั่วคราว.
3. ทำ fixture สำหรับ backup ปกติ, media หาย, manifest เสีย, ZIP เสีย และ path หลุด; รายงาน `restorable`, `partial`, `invalid` พร้อมรายการที่ขาด. ยังไม่เพิ่มปุ่ม Restore ที่เขียนทับโปรเจกต์จริงจน dry-run ผ่านและมี workflow สำรองก่อน restore.
4. อัปเดตคู่มือการย้ายเครื่องใน `_Docs/` ตามผลจริง: clone, install, model/cache ที่ต้องนำไปเอง, backup, dry-run, เปิดโปรเจกต์สำเนา.

**Gate:** กู้ fixture ลงโฟลเดอร์ชั่วคราวแล้วเปิดข้อมูลโปรเจกต์ได้; ทุกกรณีผิดพลาดรายงานไฟล์/สาเหตุชัด; ไม่มี write ไปยังงานจริง; ไม่อ้างว่า portable หาก media/model ที่โปรเจกต์ใช้ยังขาด.

## วิธีจัดรอบและวัดความสำเร็จ

- เปิด 3 รอบ implementation แยกกันใน `TODO.md`: Q1, Q2, Q3. จบทีละรอบพร้อมผล pass/fail จริงและรายงานใน `_Docs/Reports/`; อย่ารวมเป็น commit ใหญ่.
- ทุกเฟสใช้ไฟล์ใหม่/เครื่องมือ QA เป็นหลัก; ขอเปลี่ยนขอบเขตและตรวจเจ้าของไฟล์ใหม่หากจำเป็นต้องแตะ API/UI ที่ agent อื่นกำลังทำ.
- วัดก่อน/หลังเป็นตัวเลข: จำนวนคลิปเสี่ยงที่ค้นพบ, false alerts, เวลา scan ต่อคลิป, ไฟล์ final ที่พบปัญหาก่อนโพสต์ และอัตรา backup ที่ dry-run ผ่าน. ไม่ตั้งค่าความแม่นยำล่วงหน้าจากการเดา.
- เริ่มจาก Q1 เพราะกฎโปรเจกต์ห้ามซับต่างชาติฝังและห้ามวัตถุดิบผิดรุ่น; Q2 ป้องกันไฟล์เสียหลุดโพสต์; Q3 ป้องกันการสูญเสียงานตอนย้ายเครื่อง.

## ผล implementation รอบแรก — 2026-09-29

| งาน | ผล | ขอบเขตที่ยืนยันแล้ว |
| :--- | :--- | :--- |
| Q1 | เพิ่ม `tools/media_intake_audit.py`; hash ซ้ำ, ffprobe, sample timestamps และ OCR optional ผ่าน Tesseract | synthetic H.264/AAC 1080p ถูก probe ได้; PC นี้ไม่มี Tesseract จึงได้ `review_required`. OCR CJK/visible text มี behavioral tests แบบ mocked; OCR engine จริงยังไม่ทดสอบ |
| Q2 | เพิ่ม `tools/full_export_audit.py`; scan black/freeze/silence, sample peak, video/audio codec และสเปก | synthetic 2 วินาที 1080×1920/30 FPS H.264/AAC สแกนจริงได้ 0 black/freeze/silence; mean −21.1 dB, peak −16.1 dB |
| Q3 | เพิ่ม `tools/backup_restore_dry_run.py`; ตรวจ ZIP CRC, manifest membership, path traversal, JSON/SQLite integrity และแตกใน TemporaryDirectory | synthetic archive ผ่าน; archive เสีย, manifest mismatch, path traversal และ output overwrite ถูกปฏิเสธ; ไม่ restore เข้าข้อมูลจริง |

ไฟล์ที่เพิ่ม:

- `tools/media_intake_audit.py`, `tools/full_export_audit.py`, `tools/backup_restore_dry_run.py`
- `tests/test_media_intake_audit.py`, `tests/test_full_export_audit.py`, `tests/test_backup_restore_dry_run.py`

Verification: targeted **15 passed / 0 failed**; Python compile ผ่าน; import API ได้ **216 routes**; frontend **416 passed / 0 failed**, Vite build ผ่าน. Full backend suite **2174 passed / 3 failed / 8 skipped / 40 warnings**; failures เกิดใน cutout playback และ draft export preset tests นอกไฟล์รอบนี้. `git diff --check` พบ trailing whitespace ใน TODO/HISTORY ของงาน agent อื่น จึงยังไม่ปิด implementation round.

### วิธีเรียกใช้

เรียกจาก project root; รายงานปริยายเขียนลง `.tmp/` ด้วยชื่อไม่ซ้ำและไม่เขียนทับ input:

```powershell
.venv/Scripts/python.exe tools/media_intake_audit.py 01_Raw/ตัวอย่าง
.venv/Scripts/python.exe tools/full_export_audit.py 04_Exports/ตัวอย่าง.mp4
.venv/Scripts/python.exe tools/backup_restore_dry_run.py 06_Archive/Backups/omnicut_backup_ตัวอย่าง.zip
```
