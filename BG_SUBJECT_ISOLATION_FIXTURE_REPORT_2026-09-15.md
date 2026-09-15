# BG Subject Isolation - Real Fixture Gate (2026-09-15)

Executed by: Codex (GPT-6)

## Scope

Validated the real project fixture path using `.tmp/e2e-fixture/source.mp4` and rembg RGBA output under `.tmp` only. No files in `01_Raw/`, `02_Assets/`, or CapCut drafts were changed. Production model and threshold were unchanged.

## Preview contract

- Artifact manifest: `bgseq1-3fb2f77c0672ee6f/manifest.json`, status `ready`, 1080x1920, 30 frames, 30 FPS, timebase `1/30`.
- Node verification passed: source times `0`, `1/30`, `0.5`, and `0.99` map to frame indexes `0`, `1`, `4`, and `4`. Frame URLs stay under `/api/background-isolation/sequences/<id>/frames/`.
- `splitBackgroundIsolationOverlays()` puts the Hook in `behindSubject` and captions/badges in `foreground`.

## Render contract

- `VideoEditor.assemble_tiktok_video()` rendered a 1.0 second clip from the real source with the fixture sequence and existing ASS subtitles.
- FFmpeg completed at 1080x1920 and 30 FPS. The subject overlay is applied after the Hook pass, so the subject covers Hook pixels where the alpha mask is present.
- At frame 15 (0.5 seconds), isolated versus legacy output differs across the full frame. Mean absolute RGB difference is approximately `[53.52, 55.30, 57.46]`.
- Output: `.tmp/bg-isolation-real-fixture-20260915/render-isolated.mp4`.

## Fixture limitation

The measured rembg sample contains 5 frames at 540x960. The renderer requires the sequence dimensions to match the transformed 1080x1920 clip and correctly fails closed when they do not. For this graph test, a temp-only copy was resized to 1080x1920 and its final sample frame was repeated to make 30 frames. This validates lifecycle, URL/frame mapping, compositing, and fallback behavior; it is not sufficient evidence to change segmentation model or threshold.

Browser Canvas pixel extraction was unavailable through CUA, so the Preview side was verified through the pure adapter with the real manifest and the Render side through FFmpeg.

## Conclusion

The phase is closed for the verifiable scope: ready artifacts are consumed by Preview, real FFmpeg Render uses the artifact and correct layer order, size mismatches fail closed, and the production `u2net`/threshold defaults remain unchanged.
