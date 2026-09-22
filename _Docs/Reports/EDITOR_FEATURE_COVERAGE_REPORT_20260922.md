# Editor Feature Coverage Report

วันที่: 2026-09-22  
ดำเนินการโดย: Codex (GPT-5)  
แหล่งข้อมูล: `EDITOR_FEATURE_COVERAGE_MATRIX_20260922.json`

## ผลรวม

| สถานะ | จำนวน | ความหมาย |
| --- | ---: | --- |
| PASS | 2 | consumer chain และ automated evidence ครบ ไม่มี blocker ที่ทราบ |
| APPROXIMATION | 6 | Preview มีข้อจำกัดที่ต้องเปิดเผยต่อผู้ใช้ |
| BLOCKED | 2 | มี defect/contract conflict ที่ยังห้ามประกาศว่าพร้อม |
| UNTESTED | 10 | มีเส้นทางโค้ดครบ แต่ยังขาด production-path visual/behavioral gate |
| รวม | 20 | ครบทุก feature family ใน Master Plan |

`PASS + APPROXIMATION` ไม่ได้หมายความว่า Editor สมบูรณ์แล้ว โดยเฉพาะ `APPROXIMATION` ต้องมีข้อความแจ้งผู้ใช้ตาม policy ใน matrix ก่อน release

## Coverage ปัจจุบัน

| Feature | Readiness | หมายเหตุสำคัญ |
| --- | --- | --- |
| Project lifecycle | PASS | Save/autosave/reload และ queue มี regression |
| Timeline editing | UNTESTED | ขาด live boundary/overlap หลัง Save/Reload |
| Clip timing | UNTESTED | ขาด Canvas-vs-render trim/speed/freeze boundary |
| Clip transform | UNTESTED | contract ผ่าน แต่ยังไม่มี live pixel gate |
| Clip framing | UNTESTED | ขาด real-frame crop/blur หลัง rotate/zoom |
| Clip color | APPROXIMATION | Canvas brightness multiplier ต่างจาก FFmpeg additive offset |
| Transitions | APPROXIMATION | dissolve PRNG และ bridge easing ไม่ pixel-identical |
| Captions | UNTESTED | ขาด live Thai marks/emoji/1–3 line matrix |
| Motion Text | BLOCKED | IoU `0.1813699`, bbox delta `22 px` |
| Stickers | UNTESTED | ขาด live alpha/z-order/timing pair |
| Effects | UNTESTED | ขาด live decode/loop pair |
| Spotlight | UNTESTED | render payload defect แก้แล้ว แต่ยังขาด mask/feather pair |
| Background Isolation | APPROXIMATION | ใช้เฉพาะ Timeline window, block silent fallback, prefetch/cache/cancel พร้อม; temporal mask ยังขึ้นกับ footage/model |
| LUT | APPROXIMATION | browser ที่ไม่มี WebGL2 แสดงสีจริงไม่ได้ |
| Clip audio | APPROXIMATION | Preview playbackRate อาจเปลี่ยน pitch ต่างจาก atempo |
| Audio mix | APPROXIMATION | loudnorm/sidechaincompress ทำเหมือนใน browser ไม่ได้ |
| Track mute/solo | BLOCKED | กฎ playback-only ขัดกับ payload ที่ส่ง audio_mutes เข้า Render |
| Export job control | PASS | job identity, stale guard และ polling มี regression |
| Reliability/recovery | UNTESTED | ขาด disk-full/worker-death/restart E2E |
| Editor UX controls | UNTESTED | ขาด keyboard/focus/accessibility browser matrix |

## Defect ที่แก้แล้ว

`SpotlightV1` เคยถูก Preview และ Save ได้ แต่ `EditorShell` ไม่ส่ง `spotlight` ใน request ตอน Render ทั้งที่ backend และ `video_editor.py` รองรับอยู่แล้ว รอบนี้เพิ่ม `serializeRenderFeatures()` เป็น transport contract กลางสำหรับ stickers, effects, spotlight และ background isolation พร้อม regression test

Background Isolation เคยประมวลผลตั้งแต่ source time `0` ถึง EOF แม้ Timeline ใช้เพียงไม่กี่วินาที และ Preview/Render fallback เป็นภาพเดิมแบบเงียบ รอบ Phase 2 เปลี่ยนเป็น window artifact ที่บันทึก `source_start/source_duration`, แยก cache key ต่อช่วง, preflight runtime/model/disk, progress/cancel/retry, bounded prefetch และ block Render เมื่อ artifact ไม่พร้อมหรือชนกับพื้นหลังเบลอ หลักฐาน live probe ด้วย `u2net` ให้ alpha `0..255`, composite NMAE `0.0`, max delta `0` และ source hash ไม่เปลี่ยน

## Gate ที่เพิ่ม

คำสั่งตรวจ:

```powershell
.\.venv\Scripts\python.exe -m tools.editor_feature_coverage
.\.venv\Scripts\python.exe -m pytest tests/test_editor_feature_coverage.py -q -p no:cacheprovider
```

Validator จะ fail เมื่อ:

- canonical clip field ไม่มี feature owner หรือถูก claim ซ้ำ
- rendered feature ขาด UI/state/persistence/render payload/Preview/Render consumer
- source path หรือ token หลักฐานไม่อยู่จริง
- `PASS` ยังมี blocker
- `APPROXIMATION` ไม่มีเหตุผลหรือ UI disclosure policy
- `BLOCKED/UNTESTED` ไม่อธิบายช่องว่าง

## ลำดับถัดไป

Phase 2 ปิดช่องว่างเชิงการใช้งานของ Background Isolation แล้ว โดยคงสถานะ `APPROXIMATION` ไว้ตามจริงสำหรับ temporal edge quality ส่วนลำดับถัดไปคือ Motion Text ใน Phase 3 ซึ่ง strict live gate พร้อมใช้วัดการแก้แล้ว
