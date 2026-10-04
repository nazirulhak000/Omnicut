# A3 Preflight edge audit — CODEX-EDITING-VALIDATION-20261004

ดำเนินการโดย: Codex (GPT-6)

ผล: ตรวจพบและแก้ false positive/false negative ที่ทำซ้ำได้ใน metadata gate ไม่เปลี่ยน API ของ component/helper และไม่แก้ EditorShell หรือ shared files

## ข้อมูลจริงที่ใช้เป็นบริบท

A1 ส่งสรุปจาก read-only audit ของ `03_Projects/HOY01-เทียบของเดิม_1/project.json`: 5 คลิป manual_pinned, speed 0.8291–1.2809, source เดียว, ไม่มี source_window/freeze_tail/held_source_time; รอยต่ออยู่ top-level `transitions` 4 จุด circleclose/circleopen ระยะ .35 วินาที ไม่ได้อยู่ใน clip.transition_in ข้อมูลนี้ใช้พิจารณารูปร่าง saved plan เท่านั้น A3 ไม่อ่าน manifest จริงใน tests

Synthetic regression สร้าง references `synthetic.mp4` ในหน่วยความจำและผ่าน `manifestToEditorState` ของจริง พิสูจน์ว่ารอยต่อ legacy hydrate เป็น clip transition อย่างถูกต้องก่อนเรียก preflight ไม่เพิ่มตัว hydrate สำรองใน helper

## ปัญหาที่ทำซ้ำและแก้

- 7 tests ใหม่ตกก่อนแก้: valid hold-only รายงานช่วงค้างข้ามเฟรมแรก, source_window malformed กลับด้าน/ติดลบถูกข้าม, held_source_time invalid ถูกข้าม, segment position หายไม่มี pending notice, clip duration pending แต่ incoming transition ยังเดาเวลาเริ่ม, transition_duration ไม่ finite ไม่ถูกแจ้ง, และ speed นอกช่วง renderer normalize ไม่ถูกแจ้ง
- Legacy synthetic saved plan เกิด false trailing gap `27.233333–27.237667` (~4.33ms) ทั้งสอง endpoint อยู่ frame index เดียวกัน แก้ gap comparison ให้ใช้ `sequenceFrameIndex` ตัวเดิมของ timeline ช่องว่างเต็มหนึ่งเฟรมยังแจ้งได้
- อีก 2 regressions ตกก่อนแก้: helper ยอมรับ whitespace/array เป็นตัวเลข และ segment กลับช่วงสร้าง hold range `start > end` แก้ numeric predicate กับการซ่อนตำแหน่งที่ไม่เชื่อถือ

พฤติกรรมหลังแก้:
- declared source_window ต้องเป็น object มี start/end finite, start >= 0 และ end > start จึงใช้ตรวจขอบเขต หาก malformed แจ้ง advisory
- held_source_time ของช็อต hold ต้องเป็นตัวเลข finite ใน trim/source_window/source duration ที่ทราบ ใช้ end-exclusive เพื่อไม่รับ timestamp ของเฟรมหัวข้อถัดไป invalid เป็น advisory และยังไม่บล็อก freeze_tail ที่อนุญาต
- valid hold-only แสดง static interval เต็มตั้งแต่ segStart รวมเฟรมต้นฉบับแรก; holdSeconds สำหรับยอดภาพไม่พอยังคงเป็น freeze_tail จริง
- unsupported transition_in, NaN/invalid transition duration และ speed นอก 0.25–4 แจ้ง advisory ชัดเจน ไม่อ้างเฟรมดำ
- missing/nonfinite/reversed segment positions เป็น unknown_position advisory ไม่สร้างช่องว่างหรือ hold range จากเวลาที่ไม่ทราบ
- duration pending ของ incoming transition ใช้ start=null เพราะ overlap ต้องทราบความยาว current clip; ไม่แสดงเวลาเริ่มที่เดาขึ้น
- missing source, explicit invalid trim หรือ speed ไม่เป็นบวกยังเป็น blocking เหมือนเดิม numeric type ที่ renderer แปลงไม่ได้ถูกบล็อกเพิ่ม

## การตรวจจริง

`node --test frontend/src/lib/renderPreflight.test.js frontend/src/lib/footageCoverageSummary.test.js`

**28 passed, 0 failed, 0 skipped** (26 preflight + 2 coverage เดิม) ครอบคลุม transition handles clamp กับ .3s clips/20s request, valid hold-only หนึ่งเฟรม, held timestamp NaN/Infinity/string/out-of-window, source window malformed, speed normalize, missing/reversed positions, legacy hydration, subframe endpoint และหนึ่งเฟรม gap

`git diff --check -- frontend/src/lib/renderPreflight.js frontend/src/lib/renderPreflight.test.js frontend/src/components/editor/RenderPreflightNotice.jsx`: ผ่าน ไม่มี output

Root แจ้ง integration stage-generated source plans → production JS preflight/draw-plan 2 passed ใน `tests/test_editing_quality_integration.py` ก่อน patch ชุดนี้; root เป็นผู้ rerun integration/build/browser หลังรวมผล A3 ไม่อ้างว่าได้รันชุดนั้นเอง

ไฟล์ที่ A3 แก้รอบนี้: `frontend/src/lib/renderPreflight.js`, `frontend/src/lib/renderPreflight.test.js`; notice ไม่มี Play icon อยู่แล้วหลัง root แก้รอบก่อน A3 รักษาไว้

## Jev และข้อจำกัด

Jev ผ่าน `tools/jev_advisor.py`: ก่อนเริ่ม noul=.79 confidence=null; หลัง scoped regressions noul=.90 confidence=null ทั้งคู่ verdict=escalate ใช้ regression/measurement gate ที่ผู้ใช้อนุญาตเมื่อ confidence=null หรือ <.80 ค่า noul ไม่ใช่ confidence Jev อ่านสรุปข้อความ ไม่อ่าน diff เอง

ยังตรวจเพียง metadata ไม่พิสูจน์ source file existence/decoder/blackpixels หรือความตรงหัวข้อเชิง semantic Source duration จาก preview อาจเป็น fallback จึงคง source_bounds เป็น advisory ส่วน malformed values ที่ manifestToEditorState normalize ทิ้งก่อนถึง preflight ไม่สามารถวินิจฉัยค่าดิบเดิมได้ ไม่มีการเปลี่ยน loader หรือ backend ใน scope นี้

Cleanup: tests อยู่ในหน่วยความจำทั้งหมด ไม่สร้าง media หรือแตะ production Raw/Assets/Projects/Exports/registry; ลบ `.tmp/jev_preflight_edge_state.json` หลังใช้งาน ไม่มี commit/push/install/restart/full suite
