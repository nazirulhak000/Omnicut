# แผนแก้ Cutout ให้เป็นวิดีโอต่อเนื่อง (2026-09-26)

ดำเนินการโดย: Codex (GPT-6)  
สถานะ: ลงมือทำแล้ว; ผลตรวจและงานค้างติดตามใน TODO.md

## เป้าหมายที่ผู้ใช้ต้องเห็น

- กดเตรียม Cutout ครั้งเดียวแล้วได้ภาพสินค้าเคลื่อนไหวต่อเนื่องตามวิดีโอต้นฉบับใน Preview และไฟล์ Export รวมถึงเลเยอร์สินค้าอยู่หน้าข้อความตามที่ตั้งไว้
- แคชที่พร้อมใช้งานเป็น **วิดีโอโปร่งใสหนึ่งไฟล์ต่อช่วงต้นฉบับ** พร้อม manifest ไม่ใช่ PNG หนึ่งไฟล์ต่อเฟรม; ระบบประมวลผลวิดีโอเป็นเฟรมภายในได้ตามปกติ แต่ไม่เก็บหรือส่ง PNG ทีละภาพเป็นผลลัพธ์ถาวร
- ขอบวัตถุต้องไม่กะพริบหรือกระโดดระหว่างเฟรม และเมื่อ mask ยังไม่พร้อมต้องแสดงสถานะจริง ไม่ค้างภาพสินค้าจากเฟรมก่อนเพื่อกลบข้อผิดพลาด

## หลักฐานจากโค้ดปัจจุบัน

1. `scripts/api_background_isolation.py` เรียก `extract_background_isolation_sequence()` แล้ว `process_background_isolation_sequence()`; artifact ที่ publish ยังเป็น `background-isolation-foreground-sequences/.../frames/frame_*.png`.
2. `scripts/background_isolation_sequence_worker.py` เรียก rembg ต่อ PNG แล้วคัดลอก checkpoint ของภาพไป publish; การลบ source sequence หลังงานจบลดพื้นที่เพียงส่วนหนึ่ง ยังเหลือ PNG ผลลัพธ์.
3. API ให้ manifest และ `/sequences/{id}/frames/{index}` เป็น `image/png`; `SequencePlayer.jsx` ใช้ `new Image()` โหลดตามเวลา และมี `lastKnownIsolatedFrames` สำหรับแสดงเฟรมเก่าระหว่างโหลด.
4. `video_editor.py` ตรวจ PNG ครบทุกใบ แล้วส่ง `-framerate ... -start_number ... -i frame_%06d.png` เข้า FFmpeg. ดังนั้น Render ก็ยังใช้ภาพชุด แม้ไฟล์ Export สุดท้ายเป็นวิดีโอ.
5. แผนเดิม `CUTOUT_COMPRESSED_VIDEO_PIPELINE_PLAN.md` ระบุ WebM alpha และตัวเลข 25–35 MB / เร็วขึ้น 25% แต่ขั้น worker, API, Preview, Render ยังไม่ได้ทำ และตัวเลขนั้นยังไม่ใช่ผลวัดจากคลิปนี้. การเปลี่ยน container อย่างเดียวก็ไม่แก้ mask กระพริบจากการแยกภาพแบบอิสระ.

## รูปแบบเป้าหมาย

`source video → FFmpeg decode แบบสตรีม → rembg + ปรับ mask ต่อเนื่องตามเวลา → VP9 alpha encoder → cutout.webm + manifest`

- ใช้ **WebM VP9 alpha** เป็น artifact หลักหลังพิสูจน์กับ FFmpeg และ Chromium บนเครื่องนี้จริง: Preview วาดวิดีโอโปร่งใสบน Canvas; Render ใช้ decoder `libvpx-vp9` เพื่อรักษา alpha แล้ว `alphamerge`/composite สินค้าทับเลเยอร์ข้อความ.
- ระหว่างทดสอบพบว่า Chromium ยังไม่วาดพิกเซลหลัง `loadeddata` ทันที ต้องรอเฟรมจาก `requestVideoFrameCallback`. จึงห้ามขึ้นสถานะพร้อมหรือวาดภาพก่อนเฟรมที่ต้องการแสดงจริง; หาก browser อื่นไม่ผ่าน codec gate ให้พัฒนา mask video + RGB source เป็น fallback ในรอบต่อไป.
- Manifest รุ่นใหม่ระบุ `schema_version`, artifact id, fingerprint ต้นฉบับ, `source_start`, duration, จำนวนเฟรม, timebase/FPS, ขนาด, orientation, codec, mask polarity, checksum และสถานะ `ready`. ระบุเส้นทางจาก ID ที่ backend สร้างเท่านั้น ไม่รับ path จาก project JSON.
- ผลลัพธ์ใหม่ต้องเก็บใน namespace ใหม่แบบ staging → ตรวจจำนวนเฟรม/เวลา/ไฟล์ → atomic publish; reader ต้องไม่เห็นไฟล์ครึ่งงาน. โปรเจกต์เก่าอ่าน PNG เดิมต่อได้ในช่วงย้ายระบบ แต่การเตรียมงานใหม่ต้องสร้างวิดีโอ.

## ลำดับงานและเกณฑ์ผ่าน

### 0. Baseline และ feasibility gate

- บันทึกคลิปตัวอย่างจริงที่ได้รับอนุญาตแบบอ่านอย่างเดียว: FPS/VFR, rotation, ช่วง trim 5 ช่วง, ขนาดแคช, เวลาประมวลผล/Render, อาการ Preview ค้างและขอบสั่น. งานทดสอบที่สร้างไฟล์ใช้ `.tmp/` เท่านั้น.
- ทดลอง encode/decode mask video และ WebM alpha ด้วยภาพสังเคราะห์ที่รู้ค่า alpha จริง; เทียบพิกเซลหลัง decode ทั้ง browser ที่ใช้จริงและ FFmpeg. เลือกรูปแบบจากผลตรวจ ไม่ใช้ตัวเลขหรือสมมติฐานในแผนเดิม.
- สร้างตัววัด pass/fail สำหรับ clip ที่มีการเคลื่อนไหว: จำนวนเฟรมและ timestamp ตรง, ไม่มีเฟรมหาย/ซ้ำผิดเวลา, ตรวจขอบ mask ข้ามเฟรมพร้อมดูภาพจริงอย่างน้อยต้น/กลาง/ท้ายและช่วงเคลื่อนไหวเร็ว.

### 1. สร้างวิดีโอโปร่งใสโดยไม่ publish PNG

- เพิ่ม worker แบบ bounded streaming: FFmpeg decode เฉพาะ source window → rembg ได้ mask → encoder เขียน staging video. จำกัดคิว/หน่วยความจำ, รองรับ cancel/retry, ตรวจ exit code/stderr และปิด subprocess ทุกกรณี.
- เพิ่ม temporal mask stabilization แบบเปิดใช้หลังวัด baseline: ลด jitter ที่ขอบโดยไม่ทำให้วัตถุเคลื่อนไหวมีเงาซ้อน; เปรียบเทียบเฟรมต่อเนื่องและช็อตเคลื่อนไหวเร็วด้วยเกณฑ์เดียวกัน. รีเซ็ต state เมื่อ scene cut.
- ตรวจ artifact ก่อนประกาศ `ready`: decode ได้ทุกเฟรม, count/PTS/duration ตรง source window, polarity และขนาดถูกต้อง, checksum ผ่าน; failure คง artifact เดิมที่พร้อมใช้งาน ไม่ publish ของเสีย.

### 2. เชื่อม API และ Editor Preview

- เพิ่ม API ส่ง manifest รุ่นใหม่และไฟล์วิดีโอแบบรองรับ Range/seek พร้อม cache headers ตาม artifact id; ไม่ส่ง `frame_*.png` สำหรับงานใหม่.
- เปลี่ยน Preview ให้ใช้ alpha video ที่ sync ด้วย **source time** เดียวกับ timeline รวม trim, split, speed, seek, pause, loop และการสลับคลิป; วาดบน Canvas ตามลำดับเลเยอร์เดิม.
- เอาการแสดง `lastKnownIsolatedFrames` ออกจากเส้นทางวิดีโอใหม่; หากวิดีโอ seek/decode ไม่ทัน ให้แสดง loading/quality_failed ที่สื่อจริงและไม่วาดสินค้าเฟรมเก่า. สถานะ `ready` ต้องหมายถึงเฟรมปัจจุบันพร้อมแสดง ไม่ใช่ manifest พร้อมอย่างเดียว.

### 3. เชื่อม Render และ compatibility

- ให้ `video_editor.py` รับ video artifact รุ่นใหม่ผ่าน validator กลางเดียวกับ API; map ช่วงเวลา source → video PTS แล้วแยก RGB/alpha จาก WebM เพื่อ composite สินค้าเหนือ hook/text. ตรวจ trim/speed/freeze/rotation/zoom/transition และ audio indices.
- คงตัวอ่าน PNG เดิมเฉพาะ artifact เก่าระหว่าง migration; เพิ่ม action `สร้าง Cutout ใหม่` เพื่อแทนที่เฉพาะ clip ที่เลือก. ห้ามลบแคชเดิมอัตโนมัติหรือแตะ `01_Raw/`/`02_Assets/`.
- Save/Reload ต้องรักษา artifact version และ source fingerprint; หากไฟล์หายหรือ fingerprint ไม่ตรง ให้ fail closed และชี้ให้สร้างใหม่.

### 4. Gate ก่อนประกาศว่าใช้ได้จริง

- Automated: worker/API/manifest/cancel/retry/seek; frontend sync และ Save/Reload; integration Preview ↔ Render; FFmpeg output จริงบน fixture ใน `tmp_path`/`.tmp/`.
- Manual visual gate บนคลิปจริงที่ผู้ใช้แจ้งปัญหา: เล่นและ scrub ทุกจุดตัด 5 ช่วง, ตรวจเฟรมต้น/กลาง/ท้าย, ฉากเคลื่อนไหวเร็ว, ขอบสินค้า, ข้อความอยู่หลังสินค้า และ export 9:16 30 FPS. เทียบ Preview กับ Export จาก timestamp เดียวกันและบันทึกภาพ/metric ในรายงานใต้ `_Docs/Reports/`.
- วัดขนาดแคชและเวลาประมวลผล/Render เทียบ baseline จริง แล้วรายงานตัวเลขพร้อมข้อจำกัด; ไม่อ้างว่าจะเหลือ 25 MB, 98% หรือเร็วขึ้น 25% จนกว่าจะวัดผ่าน.
- ทำตาม `.agents/rules/testing_standard.md`, parity gate และ cleanup 100% ของ probe; ปิดรอบใน TODO/HISTORY ต่อเมื่อหลักฐาน Preview และไฟล์ Render ผ่านจริง.

## ความเสี่ยงที่ต้องปิดก่อนแก้ระบบจริง

- WebM alpha ต้องตรวจทั้ง browser และ FFmpeg จริง: `ffprobe pix_fmt=yuv420p` ไม่ได้ยืนยันว่า alpha หาย; browser ต้องรอเฟรมที่แสดงจริง และ FFmpeg ต้องใช้ `libvpx-vp9` decoder. รูปแบบ mask video + RGB source เป็น fallback หากเครื่องอื่นไม่ผ่าน.
- rembg ทีละเฟรมยังอาจกะพริบแม้เก็บเป็นวิดีโอ จึงต้องมี temporal quality gate.
- วิดีโอ variable frame rate, การ seek กลาง GOP และ clip speed อาจทำให้ mask เลื่อนเวลา; ใช้ PTS/timebase ไม่ประมาณจาก `round(t * fps)` อย่างเดียว.
- แคช/โปรเจกต์จริงมีงานค้างจาก agent อื่น; migration ต้องเพิ่มรูปแบบใหม่และทดสอบใน temp ก่อนแตะข้อมูลจริง.
