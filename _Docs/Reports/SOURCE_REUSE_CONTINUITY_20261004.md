# Source reuse continuity — 2026-10-04
ดำเนินการโดย: Codex (GPT-6), delegated A1, round CODEX-PARALLEL-EDITING-QUALITY-20261004

## ผลลัพธ์
ฉากที่ระบบเลือกซ้ำใช้ภาพต่อจากช่วงที่เล่นจริงไปแล้ว เมื่อหมดช่วง semantic ที่อนุญาตจะค้างเฟรมสุดท้ายพร้อมแจ้ง `footage_shortage` และข้อความไทย ไม่วนกลับไปเริ่มฉาก ไม่ดึงภาพจาก feature ถัดไป และกรณีกลับมายังฉากเดิมหลังแทรก topic อื่นใช้มุมกล้องสุดท้ายของฉากเดิม

## สาเหตุและการแก้
- Catalog เดิมคำนวณ progression จากจำนวนครั้งใช้ × ความยาวประโยคปัจจุบัน × 0.8 และ clamp ให้เหลือความยาวพอประโยค จึงเกิด overlap/rewind โดยเฉพาะประโยคยาวไม่เท่ากันหรือฉากหมด เปลี่ยนเป็น cursor ของช่วงใช้แล้วแยกตาม scene/window พร้อมระบุ cursor เมื่อฉากหมด
- Stage เดิมผูก anchor ด้วย `id(dict)` และระยะเวลาบน timeline จึงมอง dictionary ใหม่ของ scene เดิมเป็นภาพใหม่ และอาจกิน source ระหว่าง gap เปลี่ยนเป็น `SourceWindowLedger` ที่นับ frame-rounded `source_end` ของภาพที่จัดสรรจริง หลัง beat/J-lead ปรับช่วงแล้ว Cursor นี้มีลำดับเหนือคำแนะนำ nominal จาก catalog/cache และไม่นับ frozen tail
- Ledger แยก source path, scene id และ semantic start/end; ระหว่าง stage นี้ raw video เป็นแหล่งเดียวและ ledger มีอายุเพียงการสร้าง plan รอบนั้น ใช้ earliest approved window ของการใช้ครั้งแรกและไม่ขยาย semantic end
- Hold เดิมใช้ pose ของ clip ก่อนหน้าเสมอ เปลี่ยนเป็น pose ของ scene เดียวกันที่เคยใช้ล่าสุด กรณีไม่มี pose เดิมใช้ pose คงที่ของ clip เอง
- ทำเฉพาะ auto-generated AI-bounded shots; ไม่ rewrite manual/explicit clip plans ไม่เปลี่ยน feature-first scoring, font/subtitle/เสียง

## การวัดก่อนและหลัง
Baseline focused regression 4 tests: **4 failed** (catalog 2 variants, distinct dictionaries of reused scene, revisit exhausted topic)
- Stage baseline `trim_start` ของสามช็อตแรกเป็น `[2, 2, 2]` แทนการเล่นต่อ
- Catalog เมื่อเปิด sweet spot เริ่ม reuse ที่ 4.1s ทั้งที่ภาพก่อนหน้าถูกใช้ถึง 5.5s
- หลังแก้ next clip เริ่มตรง frame boundary ของ `source_end` ก่อนหน้า โดยใช้ความยาว picture จริงรวม J-lead ไม่ใช้ความยาว cue สมมติ
- FFmpeg synthetic continuous case: 48 เฟรมก่อน source หมดเป็น indices **60..107** ต่อกัน ไม่มีการเล่นซ้ำ; 24 เฟรมที่เหลือค้างที่ **107**
- FFmpeg synthetic revisit case: topic อื่นยังปรากฏ (source index 120) จากนั้น 12 เฟรมท้ายค้างที่ **74**; grayscale difference จาก pose ที่ฉากเดิมค้างไว้ <1.0
- Real decoded frames เทียบ production `buildSegments/getDrawPlan` ของ `timelineMath.js` ทั้ง 72 output frames ต่อ case: error ≤1 source frame

## Validation
- `pytest tests/test_source_reuse_continuity.py -q -p no:cacheprovider --tb=short`: **8 passed** รวม 2 short FFmpeg regressions และ production preview planner probes (2.25s)
- Final focused offline run: `test_source_reuse_continuity.py`, `test_shot_source_window.py`, `test_feature_first_selection.py`, `test_shot_matching_cut_quality.py`, `test_shot_matching_pacing.py`, `test_manual_shot_map.py`, `test_manual_shot_map_sync.py`, `-m 'not render_regression'`: **77 passed, 2 deselected**, 0 warnings (1.79s)
- `git diff --check`: ไม่มี whitespace error; Git แจ้ง normalization LF→CRLF ของไฟล์บางส่วน
- ทุก media probe อยู่ใน `TemporaryDirectory` ใต้ pytest `tmp_path`; tests assert ว่าไม่มี `.mp4` ค้าง ไม่มีการเขียน real Raw/Assets/Projects/Exports/registry ไม่มี install, commit, push หรือ restart

## Jev advisory
ตรวจเฉพาะข้อความสรุป ไม่ได้อ่าน diff หรือดูภาพเอง; ไม่ถือเป็นหลักฐาน visual correctness
- ก่อนเริ่ม: noul **0.62**, confidence **null**, verdict escalate; ใช้ regression/measurement fallback ที่ผู้ใช้อนุญาตไว้
- ก่อน FFmpeg: risk score **0.65**, confidence **0.64**, verdict escalate ผลจากคำสั่งแบบต่อเนื่องมาถึงพร้อมผล tests ที่เริ่มไปแล้ว จึงแจ้ง root ให้ตรวจ scope การอนุญาต fallback สำหรับ low non-null confidence; ไม่รัน FFmpeg เพิ่มหลังพบผลนี้
- เทียบก่อน/หลัง: noul **0.86**, confidence **null**, verdict escalate; correctness อ้างอิง regression/decoded frames เท่านั้น
- หลังเขียนรายงาน: completeness score **2.72/4**, confidence **0.68**, verdict escalate
- Root แจ้งว่าผู้ใช้อนุมัติ regression tests/real measurements เป็น gate สำหรับ confidence <0.80 และ null เพิ่มเติมแล้ว; ไม่เรนเดอร์ซ้ำ case ที่ผ่านเพราะไม่มีการเปลี่ยน behavior ที่ probes เหล่านั้นครอบคลุม

## ขอบเขตและ integration
- แก้ `scripts/gemini_vision_matcher.py`, `scripts/shot_source_window.py`, `scripts/stages/shot_matching_stage.py`; เพิ่ม `tests/test_source_reuse_continuity.py`
- Contract ส่ง frontend เดิม: `source_window`, `trim_start/end`, `freeze_tail`, `held_source_time`, `footage_shortage.missing_seconds/reason` (`source_window_exhausted`); internal reuse key ไม่ถูก serialize ไป clip
- Preview check เรียก production planner ผ่าน Node; ไม่ได้ควบคุม browser/วัด native decoder ใน lane นี้ งานนั้นเป็น A2
- ไม่แก้ legacy unbounded heuristic offsets หรือ existing manual plans ไม่มี claim ว่าห้ามภาพซ้ำทุกแหล่ง/ทุกกรณี
- Root ดูแล TODO/HISTORY และ final integration ร่วมกับ A2/A3
