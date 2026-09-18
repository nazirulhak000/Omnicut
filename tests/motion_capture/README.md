# ASS/libass motion fixture seam

This directory contains the non-production side of the Canvas-vs-ASS parity
work. `ass_fixture.py` consumes the existing motion contract and ASS adapter,
then writes an `.ass`, one rendered PNG frame, and JSON metadata to a caller
provided temporary directory.

Example:

```powershell
python -m tests.motion_capture.ass_fixture --preset hook.in.snap
```

The default output is `.tmp/motion_capture/`. The tooling rejects
`04_Exports` paths. The JSON deliberately records `pixel_diff_status` as
`not_compared` until a real Canvas capture is supplied. Cross-rasterizer
comparison uses foreground-mask IoU, bounding-box edge delta, centroid delta,
and normalized mean absolute error; exact pixels are diagnostic only.

## Live app Canvas capture

`app_capture.py` is the app-level seam for a real `SequencePlayer` canvas. It
accepts a URL and CSS selector, uses Playwright to wait for that selector, then
reads the live `<canvas>` pixels through `toDataURL('image/png')`. All output
must be under `.tmp/` and the manifest is deliberately marked
`pixel_parity_claim: false` until a deterministic timeline seek and matching
ASS frame are supplied.

```powershell
python -m tests.motion_capture.app_capture `
  --url 'https://127.0.0.1:5173/motion_capture.html?in=hook.in.bounce&loop=hook.loop.pulse&out=hook.out.fade' `
  --selector 'canvas' `
  --ready-selector '[data-testid="motion-capture-sequence-player"]' `
  --output-dir .tmp/motion-live-sequence-player `
  --frames 5
```

`frontend/motion_capture.html` mounts the real `SequencePlayer` component and
exposes `window.motionCapture.capture({ frameIndex })`, so captures from this
fixture use a deterministic 30 FPS frame index. For the full app, pass
`--active-tab editor` and use the preview selector below after supplying a
project query string:

```css
div[class*="rounded-2xl"][class*="shadow-2xl"] canvas
```

For the opt-in pytest gate, set `MOTION_CAPTURE_APP_URL` and
`MOTION_CAPTURE_APP_CANVAS_SELECTOR`. If the app is not running, the selector
is absent, or Playwright/Chromium cannot launch, the test skips with the exact
reason instead of claiming that the live capture passed.
