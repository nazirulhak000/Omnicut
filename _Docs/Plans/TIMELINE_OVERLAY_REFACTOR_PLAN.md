# Timeline Overlay Refactor Plan

วันที่เริ่ม: 2026-09-09

## เป้าหมาย

ลด implementation ที่ซ้ำกันของ Hook, Sticker, Effect, Caption และ Text Overlay ใน timeline และ preview โดยคง behavior เดิมทุกจุดที่เป็น visual/editor contract

## หลักการแบ่งเฟส

1. เริ่มจาก pure math ที่ไม่มี React หรือ pointer side effect
2. แยก shared structure ออกจาก type-specific policy
3. ใช้ compatibility wrapper เมื่อ field name หรือ callback contract ต่างกัน
4. ห้ามรวม behavior ที่มีความหมายเฉพาะ เช่น caption magnetic ripple, hook duration clamp, sticker legacy aliases และ caption apply-to-all
5. ทุกเฟสต้องผ่าน targeted tests ก่อนขยับไปเฟสถัดไป

## Phase 0 — Baseline/contract map

สถานะ: เสร็จในรอบสำรวจ

ขอบเขตที่ตรวจ:

- `frontend/src/components/editor/Timeline.jsx`
- `frontend/src/components/editor/timeline/EffectTrack.jsx`
- `frontend/src/hooks/useTimelineDrag.js`
- `frontend/src/components/SequencePlayer.jsx`
- `frontend/src/components/editor/EditorShell.jsx`
- `frontend/src/hooks/useEditorSelection.js`
- `frontend/src/hooks/useEditorCommands.js`
- `frontend/src/components/editor/Inspector.jsx`
- `frontend/src/components/editor/inspector/StickerInspector.jsx`
- `frontend/src/components/editor/inspector/EffectInspector.jsx`
- `frontend/src/lib/timelineTrackModel.js`
- `frontend/src/lib/editorProjectState.js`

## Phase 1 — Shared interval lane-packing core

สถานะ: เสร็จ

ผลลัพธ์ที่ต้องการ:

- มี primitive เดียวสำหรับจัด timed items ลง lane
- `packTextOverlays` และ `packStickers` ยังมี API เดิม
- Effect ใช้ primitive เดียวกันผ่าน existing Sticker-compatible path
- ไม่มีการเปลี่ยน epsilon, sort order, lane numbering หรือ input mutation

Gate:

- Node tests ผ่าน
- build ผ่าน
- diff check ผ่าน

## Phase 2 — Shared timeline chip shell

สถานะ: เสร็จ

ขอบเขต:

- label gutter config
- chip positioning/width/lane height
- left/body/right visual shell
- selection and click-to-seek adapter

คงแยก:

- Hook ที่มี right trim อย่างเดียว
- Caption ที่ใช้ cue ripple
- Sticker legacy aliases
- Effect asset/media label

ผลที่ทำแล้ว:

- เพิ่ม `frontend/src/components/editor/timeline/TimelineIntervalItem.jsx`
- Sticker, Effect และ Text overlay ใช้ shell เดียวกัน
- Hook และ Caption ยังใช้ markup เดิมเพราะ interaction policy แตกต่าง
- Gate: frontend 89 tests ผ่าน, build ผ่าน, diff check ผ่าน

## Phase 3 — Shared timeline drag lifecycle

สถานะ: เสร็จ

ขอบเขต:

- pointer capture/release
- movement threshold
- drag begin/end
- common interval trim and body-shift math

คง policy เฉพาะชนิด:

- Caption: previous-cue clamp และ magnetic ripple
- Text: no ripple และไม่มี upper timeline clamp ใน body drag แบบเดิม
- Hook: 1–8 second end-only trim
- Sticker: `startTime/endTime` compatibility
- Effect: modern fields เท่านั้น

ผลที่ทำแล้ว:

- `useTimelineDrag.js` มี timed-interval drag core เดียวสำหรับ trim และ body shift ของ Sticker/Effect
- Sticker เก็บทั้ง modern `start/end` และ legacy `startTime/endTime` ผ่าน adapter เดิม รวมถึงรองรับ legacy argument order
- Effect เก็บเฉพาะ `start/end` ผ่าน adapter ของตัวเอง
- Caption, Text และ Hook handlers ยังแยกตาม policy เดิม
- Gate: frontend 89 tests ผ่าน, build ผ่าน 1966 modules, diff check ผ่าน

## Phase 4 — SequencePlayer geometry/commit adapter

สถานะ: เสร็จ

ขอบเขต:

- selected-box fallback metrics
- normalized position clamp/snap
- projected resize scale
- common pointer listener lifecycle

ลำดับเริ่มต้น:

- แยก pure selected-box geometry resolver ก่อน
- เพิ่ม deterministic boundary tests
- ค่อยประเมินการรวม pointer lifecycle หลัง geometry contract คง behavior ได้

ผลที่ทำแล้วใน geometry slice:

- เพิ่ม `frontend/src/lib/overlayBoxGeometry.js` สำหรับ selected-box fallback, normalized clamp/snap, rounding และ resize projection
- `SequencePlayer.jsx` เรียกใช้ pure helpers แต่ยังคง callback dispatch และ Caption apply-to-all ไว้ใน component
- เพิ่ม `pointerDragLifecycle.js` ให้ box drag และ resize ใช้ bind/cleanup lifecycle เดียวกัน
- เพิ่ม `overlayBoxGeometry.test.js` ครอบคลุม measured-bounds precedence, type-specific fallback, hidden sticker, snap guides และ scale limits
- เพิ่ม `pointerDragLifecycle.test.js` ตรวจการ bind/remove ของ listener ทั้งสามชนิด
- Gate pointer lifecycle slice: frontend 94 tests ผ่าน, build ผ่าน 1968 modules, diff check ผ่าน

Phase 4 เสร็จตามขอบเขต: geometry, pointer lifecycle และ field-mapping adapter ถูกแยกแล้ว; Caption-specific callback policy ยังอยู่ใน component ตามเดิม

Gate Phase 4: frontend 95 tests ผ่าน, build ผ่าน 1968 modules, diff check ผ่าน

คงแยก:

- caption `x/y/scale` และ apply-to-all
- overlay `x/y` และ `look.size_pct`
- sticker `normX/normY/scale` + image aspect ratio
- effect square media box + multiply blend
- Hook top anchor และ Text middle anchor

ต้องตรวจ:

- bounds จาก actual renderer ยังมาก่อน fallback
- preview bounds ยังสอดคล้องกับ renderer output
- start/hold/end visual behavior ไม่เปลี่ยน

## Phase 5 — State/Inspector branching

สถานะ: เสร็จ

ขอบเขต:

- Sticker/Effect CRUD adapter
- selection resolver
- delete command dispatch
- Inspector shared form primitives

ข้อควรระวัง:

- ห้ามลบ sticker legacy style mirror
- ห้ามลบ effect overlap slot placement
- ห้ามรวม Hook/Text Inspector จนทำให้ tier/template behavior เปลี่ยน

ผลที่ทำแล้วใน Phase 5:

- เพิ่ม `selectionResolver.js` สำหรับ selected item lookup แบบ type, fallback และ custom matcher
- `useEditorSelection.js` ใช้ resolver ร่วมกับ clip, caption และ text/hook พร้อมคง legacy `_uid/id` และ hook fallback
- `Inspector.jsx` ใช้ resolver ร่วมกับ text, sticker และ effect พร้อมคง Sticker first-item fallback และ Effect null behavior
- เพิ่ม `collectionOperations.js` สำหรับ pure update/remove by id
- `useEditorCommands.js` และ `EditorShell.jsx` ใช้ primitive นี้เฉพาะส่วน array operation; Sticker style mirror/single-slot fallback และ selection clearing ยังเป็น adapter เดิม
- เพิ่ม `OverlayTimingControls.jsx` ให้ Sticker/Effect Inspector ใช้ timing form shell เดียวกัน โดยส่ง accent และ end-boundary เป็น config
- เพิ่ม `OverlayScaleControl.jsx` ให้ Sticker/Effect Inspector ใช้ scale form shell เดียวกัน โดยส่ง accent และ update/reset callback เป็น config
- Position block ยังแยกตามเดิม เพราะ Sticker มี drag guidance แต่ Effect เป็น numeric-only
- Add/Clear/Effect overlap-slot placement ยังไม่รวม เพราะมี behavior divergence จริง
- Gate Phase 5: frontend 100 tests ผ่าน, build ผ่าน 1972 modules, diff check ผ่าน

## Phase 6 — Final parity/sign-off

สถานะ: เสร็จ

- `npm test`
- `npm run build`
- `git diff --check`
- preview/render parity tests
- FFmpeg behavioral render หลายเฟรม: เข้า, ค้าง, ออก
- ตรวจทุก clamp, rounding, snap, hidden state และ selection path

ผลตรวจล่าสุด:

- `test_preview_render_behavior.py`: 11 passed, 2 Pillow deprecation warnings
- `test_preview_render_parity.py`: 150 passed หลังแก้ stale source-contract expectation จาก 6 เป็น 7 occurrences; production label gutter ไม่ได้เปลี่ยน
- frontend: 100 tests passed, build ผ่าน 1972 modules, diff check ผ่าน

รอบนี้ปิดได้ตาม Gate ครบทุกข้อ โดยยังคง behavior-specific branches ที่มีความต่างจริงไว้แยก

## Post-Phase 6 hardening / final audit — 2026-09-09

สถานะ: overlay scope ผ่าน; repo-wide sign-off ยังรอการแก้ POST-LIFECYCLE-1

- TLO-REFACTOR-1 ถึง 7 เสร็จแล้ว ครอบคลุม timeline shell, label gutter, optional trim handles, Caption migration, Inspector primitives และ pointer lifecycle
- `TrackLabel.jsx` ถูก audit พบ fallback regression จริง จึงคืน `width ?? GUTTER`; parity source-contract probes ถูกย้ายให้ตรวจ module ที่ถูก extraction แล้ว
- Overlay gates ผ่าน: frontend `109 passed`, lint exit 0, build `1975 modules transformed`, parity `150 passed`, behavior `11 passed`, dispatch `2 passed`, `compileall` ผ่าน และ `git diff --check` ผ่าน
- Full pytest ล่าสุด `934 passed, 9 failed, 6 warnings`; ทั้ง 9 failures อยู่ใน reconciliation/posted lifecycle (`ProductStore`) และไม่พบหลักฐานว่าเกิดจาก Overlay Timeline/Preview refactor
- คง divergence ที่เป็น behavioral contract: Caption magnetic ripple/apply-to-all, Hook end-only clamp/anchor, Text word-stagger/trim policy, Sticker legacy adapter, Effect media/overlap policy และ source clip trim/speed/freeze semantics
