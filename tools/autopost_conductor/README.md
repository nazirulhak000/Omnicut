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
```
Options: `--channel main` `--queue-id ID` `--port 9333` `--no-launch` `--allow-price-caption`

First time: run `--health`. It opens Chrome with profile `tools/tiktok_browser_profile`.
If it lands on the login page, **log in by hand once** in that window, then run again.

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

## Not covered yet
TikTok scheduled-quota (30) is not auto-detected → use `--limit`. No in-app Start button
(needs a backend route + frontend change). Selectors were verified on past live runs, not re-verified today.

Tests: `node --test tools/autopost_conductor/*.test.cjs`
