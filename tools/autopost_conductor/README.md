# Autopost Conductor — unattended TikTok posting (one clip at a time)

Runs the **real extension worker** (`tiktok_autopost_extension/background.js`) headless in Node,
talking to a real Chrome over CDP (`--remote-debugging-port`). No side panel, no MV3 worker timeout,
no "is debugging this browser" bar. Same selectors and same backend `posting_jobs` protocol
(prepare → claim → attempt → ack), so duplicate-post protection is unchanged.

## Use
```
tools\start_autopost.bat --health            # open Studio, check login + upload input. No upload.
tools\start_autopost.bat --dry-run --limit 3 # fill everything, screenshot, DO NOT click post, release job
tools\start_autopost.bat --limit 10          # real posting of queue items (status planned/ready_for_extension)
tools\start_autopost.bat --mode draft --limit 5   # save as DRAFTS (Save draft button), never Post, no schedule needed
```
Options: `--mode schedule|draft` (default schedule) `--channel main` `--queue-id ID` `--port 9333` `--no-launch` `--allow-price-caption` `--cover-fallback`
Test/fault options: `--viewport 1366x768` (set window size) · `--net slow|blip|offline` (throttle / drop network) · `--clip-budget-min N` (time budget per clip, default 25)

First time: run `--health`. It opens Chrome with profile `tools/tiktok_browser_profile`.
If it lands on the login page, **log in by hand once** in that window, then run again.

## Known facts from the live check (2026-11-09)
- This account's Studio build has **no custom-cover upload** in "Edit cover" (only frame / Sticker / Text), so the
  prepared 3:4 cover cannot be applied. A real run **fails the clip** unless you pass `--cover-fallback`
  (keeps TikTok's automatic cover, first frame). `--dry-run` always falls back so the rest can be verified.
- Studio runs in English here; the extension selectors are bilingual and worked.
- Queue clips whose slot already passed (or < 15 min ahead) are skipped. In `--dry-run` a synthetic slot (+2 days) is used instead.

## Testing the extension's own side panel (not the conductor)
`node tools/autopost_conductor/extension_e2e.js` loads the unpacked extension into the same Chrome over CDP
(`Extensions.loadUnpacked`, needs `--enable-unsafe-extension-debugging`), opens the real `sidepanel.html`, sets the API key,
filters the list to ONE queue clip and presses the real batch button. The final post click is stubbed (nothing is published)
unless you pass `--real-post`. `--kill-worker-at=30` stops the MV3 service worker 30 s into the run.
Other modes: `--clips=5` (5 clips in a row, live progress printed) · `--verify-probe` (Content-page check against clips that were
really scheduled + one that was not) · `--leave-probe` (reset a page that has a real beforeunload handler: must not hang).
The extension is always loaded from a FRESH COPY (`.tmp/e2e_ext/`): Chrome caches the service-worker script per extension id +
manifest version, so reloading the same path can silently run OLD worker code. **In your own Chrome, reload the extension at
`chrome://extensions` after updating it (the manifest version is bumped for exactly this reason).**
Evidence: `.tmp/extension_e2e/<run>/` (`panel_log.txt`, `panel.png`, `upload_tab.png`).

## Draft mode and the live quota
- `--mode draft` uses the worker's `save-draft-only` step: it presses **Save draft** only (never Post), waits for TikTok to open
  Content > Drafts, checks the draft row, acks `draft_saved` (queue status `draft_on_platform`, the export is NOT marked posted),
  then checks Content > Drafts once more (`verify-draft-content`). A draft has no publish time, so passed slots are fine.
- Before every real run it reads the live quota (`detect-tiktok-quota`): scheduled posts are counted from the Content list rows with a
  future badge, drafts from the "Drafts N" tab. It never plans more clips than what is left of 30 (per mode) and stops with
  `quota_full_schedule` / `quota_full_draft` when full. If the counts cannot be read it says so and `--limit` is the only guard.
- Deleted the draft on TikTok? Reset the clip with `PATCH /api/schedule-queue/<id> {"status":"planned"}` (or the "รีเซ็ตแบบร่าง" button in the app).

## Safety rules (built in)
- Sequential only; random 20–40 s cooldown between clips. Never concurrent (account-ban risk).
- Only queue items with a future slot (>= 15 min) + TikTok product id. Price/discount text in the
  caption is skipped (`price_in_caption`) unless `--allow-price-caption`.
- A job that was already clicked is never cancelled (parked + reconciled) → no double post.
- Stops and writes `.tmp/autopost_ALERT.txt` (never guesses) on: login lost, captcha/verify,
  account mismatch, unsent receipt, 3 failures in a row, 2 unconfirmed posts in a row.
- Ctrl+C finishes the current clip, then stops. Windows sleep is blocked while it runs.

## Output
`.tmp/autopost_runs/<run>/run.jsonl · summary.json · *.png` · DOM snapshots `.tmp/autopost_dom/` ·
health `.tmp/autopost_health.json` · posting state (resume) `.tmp/autopost_state.json`
Exit codes: 0 ok · 1 some clips failed/unknown · 2 aborted (needs a human) · 3 browser/login/backend problem

## Schedule (optional)
`powershell -File tools\autopost_conductor\install_task.ps1` previews daily health + run tasks; add `-Apply` to register.

## What was verified live (2026-11-09, real account)
- 3 real scheduled posts end to end (upload → caption → product → schedule → post → ack → Content-page check): all `scheduled`, `verified: true`.
- TikTok shows the bare toast **"Video published"** even for scheduled posts → backend now accepts it (scheduled jobs only), the worker records those as `scheduled_on_platform`.
- After every post the clip must also appear on Studio > Content (reloaded up to ~90 s; list lags the toast) with the right caption + slot, else the clip is `unknown`.
- Window sizes 1024x700, 820x900, 1366x768, 1920x1080: TikTok's "Add product links" modal is clipped below ~1200 px → the runner enlarges the window, or emulates a 1440x900 viewport, before starting.
- Queue items whose export no longer exists / is posted / QC-rejected are skipped up front (19 of 41 were stale).
- Each clip has a time budget (zombie browser actions are killed), one retry for hiccups *before* the post click (never after), backend calls time out after 30 s.

## Not covered yet
TikTok scheduled-quota (30) is not auto-detected → use `--limit`. No in-app Start button
(needs a backend route + frontend change). Selectors were verified on past live runs, not re-verified today.

Tests: `node --test tools/autopost_conductor/*.test.cjs`
