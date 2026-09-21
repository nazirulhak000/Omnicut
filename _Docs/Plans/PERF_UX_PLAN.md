# PERF-UX-1 — Parallel Reliability, Performance and UX Plan

วันที่: 2026-09-09
สถานะ: implementation complete; evidence gates pending
คำสั่ง: user อนุญาตให้แยก agent ขนานเมื่อ write scope ไม่ทับกัน

## Objective

ทำให้ OmniCut Pro Studio ใช้งานลื่นขึ้น, autosave/export รอไม่นาน, project ใหญ่ยังตอบสนองได้ และสถานะ posted/reconciliation เชื่อถือได้ โดยเริ่มจากหลักฐานที่วัดได้และไม่ทำลาย Preview = Render parity.

## Continuation takeover (2026-09-09)

- The user confirmed that no other agent is editing and authorized the main agent to finish the remaining phases.
- The main agent now owns the previously blocked Timeline scope while preserving the existing working-tree diffs in `Timeline.jsx` and `useEditorCommands.js`; no reset, checkout, clean, or destructive overwrite is permitted.
- The Timeline slice is limited to low-risk derived-data/render-churn reductions plus deterministic source-contract coverage. Full virtualization and browser FPS claims stay pending until real 50/100/300-clip fixture measurements exist.
- Browser profiler evidence for B and a real API/job repeated-rerender smoke for D remain explicit evidence gates and will not be marked complete from static inspection alone.

## Evidence update (2026-09-09)

The entries below supersede the earlier tentative status in this plan.

- E implementation is complete for the low-risk slice: `Timeline.jsx` memoizes repeated transition/clip-audio collections and uses a name/path sticker-asset index while preserving existing lookup order and handlers.
- E regression probe is complete: `npm test` = `124 passed, 0 failed`.
- E synthetic microbenchmark is complete: 20,000 rounds at 50/100/300 clips produced equivalent results and measured reductions of `64.5%`, `77.0%`, and `86.7%` for the repeated derivation slice.
- Browser observation of the open local project found `54` timeline items, `16` transition triggers, and `1,367` DOM elements. This is a current-fixture observation, not a before/after FPS claim.
- D deterministic rerender-flow smoke is complete: `complete_job` stamped real temp artifacts and a subsequent `PipelineContext` consumed the persisted fingerprints; targeted file = `14 passed, 0 failed`.
- B browser/React Profiler before-after evidence remains pending because the available browser evaluation surface did not expose a supported playback profiler trace; static probes do not prove FPS or audio-drift improvement.
- D production API/FFmpeg repeated-rerender smoke and E controlled 50/100/300 browser fixture benchmark remain pending evidence gates.

## Current constraints

- Working tree มี diff เดิมของผู้ใช้ใน `frontend/src/components/editor/Timeline.jsx` และ `frontend/src/hooks/useEditorCommands.js`; รอบนี้รับช่วง Timeline เฉพาะ low-risk slice และรักษา diff เดิมที่ไม่เกี่ยวข้องไว้
- ห้าม reset, checkout, clean หรือลบ diff เดิม; การแก้ Timeline รอบนี้ต้องคง geometry/interaction contract และไม่เขียนทับ functional diff ของ `useEditorCommands.js`
- รอบก่อน overlay refactor commit คือ `4929d60`
- Full pytest baseline ล่าสุด: `934 passed, 9 failed, 6 warnings`; failures อยู่ใน reconciliation/posted lifecycle
- Frontend baseline ล่าสุด: `109 passed`, lint exit 0 แต่มี warnings, build `1975 modules transformed`

## Parallel workstreams

### A — POST-LIFECYCLE reliability

Write scope: `scripts/product_store.py`, `scripts/api_exports.py`, `scripts/api_videos.py`, `scripts/api_schedule_queue.py`, reconciliation tests และ relative-path tests ที่จำเป็น

Outcome: แยก root cause ของ 9 failures, ทำสถานะ/identity/path/transaction ให้ deterministic และ full pytest กลับมา `0 failed`.

Risk: สูงกว่างาน UI เพราะแตะข้อมูล lifecycle และไฟล์จริง จึงต้องใช้ temp storage และ regression tests.

### B — Preview Frame Scheduler

Write scope: `frontend/src/components/SequencePlayer.jsx` และ tests เฉพาะ preview/frame scheduling

Evidence: playback RAF ทำ Canvas drawing และ `setPlayhead` ต่อ frame; มี repeated segment lookup และ derived-key serialization.

Outcome: วัดและลด frame/state churn โดยคง interface ของ preview และ parity seam กับ renderer.

Risk: กลาง; audio clock, drift correction, selection box และ entrance/hold/exit animation เป็น behavioral contract.

### C — Autosave and history

Write scope: `frontend/src/hooks/useProjectAutosave.js`, `frontend/src/hooks/useEditorHistory.js`, `frontend/src/lib/projectSaveQueue.js` และ tests ของ module เหล่านี้

Evidence: save payload และ payload key ใช้ JSON serialization; history clone state ใหญ่ใน discrete edit, drag, undo และ redo; baseline ยังระบุ ordering/flush gaps.

Outcome: ลด bytes/requests/deep clone และปิด stale-write/flush gaps โดยไม่เปลี่ยน manifest/migration/undo semantics.

Risk: สูง; interface ของ save และ history ต้องมี contract tests ครบ.

### D — Incremental render and artifact reuse

Write scope: `scripts/pipeline_context.py`, `scripts/render_jobs.py`, `scripts/api_render.py` และ tests/stage fixtures ที่จำเป็น

Evidence: มี `resume_from`, `should_run`, `reuse` อยู่แล้ว และเครื่อง render ใช้ CPU/single render slot.

Outcome: audit reuse เดิม, เพิ่ม fingerprint/change-class policy เท่าที่พิสูจน์ได้ และรายงาน stage ที่ rerun ให้ UX เข้าใจได้.

Risk: สูง; artifact เก่าอาจถูกใช้ผิดถ้า fingerprint ไม่ครบ ต้องมี FFmpeg smoke และ output correctness checks.

### E — Timeline and filmstrip scaling

Write scope: read-only ระหว่าง `Timeline.jsx` มีงานผู้ใช้ค้าง; implementation จะเปิดได้เมื่อ user-owned diff หาย/ได้รับอนุญาตแล้ว

Evidence: Timeline map ทุก segment/overlay/audio row และ filmstrip ใช้ FFmpeg สร้างต่อ source.

Outcome: benchmark ก่อนเลือก viewport/lazy loading/filmstrip cache adapter.

Risk: กลาง; pointer hit-testing, selection และ playhead locality ต้องคง behavior.

## Current verification snapshot

- Stream A: targeted reconciliation `47 passed, 0 failed`; full pytest `956 passed, 0 failed, 6 warnings`
- Stream B: frame scheduling probe `3 passed, 0 failed`; frontend suite `122 passed, 0 failed`; build `1975 modules transformed`
- Stream C: targeted autosave/history `13 passed, 0 failed`; frontend suite/build pass; lint exit 0 with existing warnings plus one autosave refs warning
- Stream D: incremental reuse `14 passed`; compatibility/phase smoke and full pytest pass; compileall pass; no FFmpeg renderer argument changes
- Timeline low-risk scaling slice is implemented and tested; full browser fixture benchmark remains pending

## Integration order

1. Agents ทำเฉพาะ write scope ของตัวเอง
2. Main agent ตรวจ diff และ test evidence ของแต่ละ stream
3. Merge logical commits ตาม dependency: A → B/C/D → E (เมื่อ scope ว่าง)
4. รัน repo-wide gates หลังหยุด parallel writes แล้ว

## Remaining gates before closing this round

- Browser/React Profiler before-after measurement for Stream B: frame time p50/p95, dropped frames, React commits/sec และ audio drift
- End-to-end repeated rerender smoke for Stream D with real artifacts through job flow
- Timeline 50/100/300 clip benchmark after the user-owned `Timeline.jsx` diff is resolved
- Review and explicitly exclude unrelated `Timeline.jsx` / `useEditorCommands.js` working-tree changes from the PERF-UX commit unless the user assigns them to this round

## Required measurements

- Preview: frame time p50/p95, dropped frames, React commits/sec, audio drift
- Timeline: open time, drag/scroll FPS, DOM node count ที่ 50/100/300 clips
- Autosave: payload bytes, save requests/minute, stale-write count, flush success
- Render: total duration แยก stage, reuse-hit ratio, queue wait, output hash correctness
- Reliability: full pytest pass/fail และ targeted regression counts

## Safety gates

- ไม่ติ๊ก TODO `[x]` เพราะแก้โค้ดเสร็จ ต้องมี command output จริง
- งานที่กระทบภาพต้องผ่าน frontend tests, parity tests และ FFmpeg behavioral render หลายเฟรม
- งานที่กระทบ save ต้องผ่าน ordering, flush, reload, migration และ undo/redo tests
- งาน backend ต้องใช้ temp storage และไม่แตะ `01_Raw/`, `02_Assets/`, `03_Projects/` หรือ `_Docs/post_log.json`
- ทุก commit ต้องตรวจ `git diff --check` และ file ownership
