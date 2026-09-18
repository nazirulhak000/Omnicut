# Text Motion Parity / UX Verification — 2026-09-18

ดำเนินการโดย: Codex (GPT-5)

## Scope

- Test/report files only; no live Canvas, ASS, or UI renderer code changed.
- No commit created.
- Coverage: all 34 motion presets, five normalized sample times, legacy IDs,
  In/Hold/Out order, short durations below 120 ms, reduced motion, Thai text
  safety metadata, and truthful UI capability metadata.

## Results

| Suite | Result |
| --- | --- |
| Python motion verification + contract + ASS adapter | 31 passed, 1 skipped |
| Node motion verification + existing UI/renderer adapter tests | 21 passed |
| `git diff --check` | No whitespace error in files changed for this verification; an existing modified file reports a pre-existing blank line at `tests/test_preview_render_parity.py:2458`. |

## Blocker / limitation

1. **P1 — Real preview/render frame diff is not available yet.**
   `tests/motion_frame_matrix.py:263-269` intentionally skips the browser
   Canvas capture and ASS/FFmpeg frame comparison. The current gates validate
   the declarative contract and adapter behavior, not pixel parity.

2. **Integration is correctly marked as not complete.**
   The catalog sets `renderer_bound: false` at
   `frontend/src/lib/motion/motionPresets.js:130-134`. This is not a false UI
   claim; it prevents the UI from advertising capabilities before the live
   renderer integration and frame-diff gate exist.

## Files added

- `tests/test_motion_parity_verification.py`
- `frontend/src/lib/motion/parityVerification.test.js`
- `TEXT_MOTION_PARITY_VERIFICATION_20260918.md`
