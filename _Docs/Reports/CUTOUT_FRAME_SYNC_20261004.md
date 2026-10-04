# Cutout frame synchronization
ดำเนินการโดย: Codex (GPT-6)
Round: CODEX-CUTOUT-FRAME-SYNC-20261004

## Changes
- Preview follows the original video's presented frame timestamp rather than independently following the timeline clock for the alpha decoder.
- A paired source RGB snapshot and its alpha-masked copy supply both sandwich passes. Cutout artifact RGB cannot introduce a second product position or colour.
- Both layers use drawVideoFrame geometry. Rotation, mirror, crop and motion therefore share the footage path.
- A lagging alpha decoder holds the complete last matched pair for at most 250ms; seek, artifact/source changes and larger discontinuities invalidate the pair. Beyond this window the existing pending state applies.
- At most four source pairs and frame subscriptions are retained, with disposal on eviction/unmount; canvases are reused at unchanged dimensions.
- Video and legacy PNG artifacts, high-resolution stills and cover captures use source RGB with artifact alpha.
- Render splits the transformed original footage for RGB and extracts only alpha from the transformed artifact. FFmpeg requires explicit format=rgba before alphaextract.
- Two Inspector props receive the real project config instead of the hidden-preview mask, preserving editable Cutout state on desktop/mobile.
- Browser fixtures were updated for the current editor controls: the opt-in playback probe mounts the full production player controls; clear-point selectors target the named subject-point panel.

## Verification
- Frontend: 700 tests passed; production build passed.
- Scoped Python: 232 tests passed, including actual Chromium playback at 0.5/1/1.3155/2x in 540p and 1080p, render integration and preview-render parity.
- Additional real Canvas pixel regression: transparent alpha exposes the yellow hook; opaque subject stays source blue even when artifact RGB is red; lag holds both source/subject snapshots and seeks clear them.
- Production NVENC FFmpeg probe used a green RGB artifact over blue/red source. Actual output samples were (0,0,252)/(252,0,0); inspected the extracted frame and removed temporary probe media.
- Compileall passed; API import exposes 225 routes.
- First full Python run: 2779 passed, 14 failed, 12 skipped, 54 warnings in 934.72s. Failures included stale editor/compact control selectors, concurrent undefined clearSubjectPoints, duplicate clear-point buttons, and the old artifact-RGB expectation. EditorShell rerun passed all four cases; render-click rerun passed; worker suite passed 11 tests after updating the RGB contract. Subsequent verification is recorded below.
- Final focused acceptance: 249 passed in 91.36s, covering the entire high-resolution playback module, video/Canvas Cutout tests, real preview/render parity, integration graph, source parity and the video worker. Node 700 passed and build passed after the final changes.
- Remaining integration limitation: the separate subject-point browser module last reported six failures (play-overlay selectors and visible-frame geometry after picker re-entry). These UI interaction checks require follow-up; no all-green full-suite claim is made. The round remains open in TODO for that integration gate.

## Limits
Follow-up requested by the user: transient decoder waiting now retains original footage in composite mode and omits the unmatched subject, instead of painting the pending mood background over a healthy video. Missing/error artifacts retain the previous unavailable-artifact behavior. Incoming videos without decoded frames use the existing outgoing-frame hold. Browser wait tests passed across 540p/1080p and 0.5/1/1.3155/2x; nine pixel comparisons passed for alpha/zoom/mirror/rotation. Video/parity gate passed 214 tests and the new pixel test passed separately; frontend 799 passed/build passed. The editing-quality roadmap is in `_Docs/Plans/EDITING_QUALITY_PRIORITY_20261004.md`; no new Cutout feature work is planned after this follow-up.

The user's original footage was not exported or modified. This corrects the frame/RGB compositing mechanism; a segmentation mask that changes shape between frames can still need a separate temporal-stability adjustment. Browsers without requestVideoFrameCallback approximate the displayed timestamp using currentTime. Holding a pair is bounded to avoid stale pictures persisting after a seek.

## Jev
Final follow-up gate: 214 passed and one fractional decoder seek-count failure (4 seeks, all 60 samples visible). The same case passed on isolated rerun without loosening its assertion. This intermittent timing limit is recorded rather than claiming a stable all-green full suite. Follow-up Jev: before code 0.85, before FFmpeg 0.81, documentation/before-after 0.90, confidence null throughout, under the already approved round exception.

Text-summary review only: before work noul 0.68, before FFmpeg 0.85, before/after 0.81, documentation 0.74; confidence null in all responses. The user explicitly authorized regression tests and actual probe inspection instead of the confidence gate for this round. These scores are not visual evidence.
