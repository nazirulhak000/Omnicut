# OmniCut TikTok Post Helper (Chrome extension, side panel)

Fills TikTok Studio's upload form from the OmniCut queue and posts / schedules / saves a draft, **one clip at a time**.
Talks to the backend through the `posting_jobs` protocol v2 (prepare → claim → attempt → ack/reconcile). The unattended,
headless twin of the same worker is `tools/autopost_conductor/`.

## What a run does (side panel → "เริ่มรันอัปโหลด")
1. **Readiness check** ("ตรวจความพร้อม", also runs automatically before every start): backend + protocol, TikTok login, upload page,
   logged-in account = the channel's handle, window size, quota. A failed item stops the run; a warning is shown in the confirm box.
2. Tick the clips you want (checkbox). Ticked clips are posted **exactly** — if none of them is usable nothing runs (it never falls
   back to the whole queue). Without ticks the queue is used, capped by the live TikTok quota (30 scheduled / 30 drafts).
3. Per clip: prepare job → claim → upload → fill caption/product/cover/schedule → **one** click (Post / Schedule / Save draft) →
   confirm on the page and on Studio > Content (or Drafts) → record the result. The click step is never retried.

## Modes
`Smart` (schedule until the schedule quota is full, then drafts) · `Schedule only` · `Draft only`. Each job carries its **intent**
(`schedule` / `draft` / `post_now`); the backend refuses a click or an outcome that contradicts it, and the worker reads the page's
primary button ("Schedule" vs "Post") before it presses anything. A scheduled clip without a date **and** time is refused.

## Publish a draft that sits on TikTok
A clip saved as a draft (queue status "บันทึกเป็นแบบร่างบน TikTok แล้ว") is a card of the main list: status "แบบร่างบน TikTok รอเผยแพร่",
its planned publish time, and its own date/time fields (a passed slot makes the card unselectable until a new time is set). Filter chip
"แบบร่าง" shows only them.
- **Scheduled**: tick the draft cards and press "เริ่มรันอัปโหลด" like any run (each draft is published at its own slot; drafts and normal
  clips can be mixed). A whole-queue run without ticks never publishes drafts by itself; a Draft-only run never publishes them.
- **Post now**: the button on the card. It goes live immediately, so it is its own run and asks for an explicit confirmation.
The extension opens **that** draft from Studio > Content > Drafts (matched by caption; none or more than one match = stop), checks the
editor shows the same caption, sets the slot (or "Now") and then uses the ordinary one-click Post step (same label/identity checks, single
attempt, same confirmation). Nothing is uploaded again. A scheduled publication uses one of the 30 schedule slots; when they are full the
run stops with that reason and only "post now" is possible. If a publication is cancelled before the click the row returns to
"draft on TikTok" (never to "planned": the draft still exists).

## Safety rules that are always on
- Price / discount text, unfilled `{placeholders}`, > 4000 characters, > 30 hashtags are refused everywhere (panel, worker, backend,
  conductor) by one rule set (`post_guard.js` ↔ `scripts/content_guard.py`; shared test cases in `tests/fixtures/`).
- The logged-in TikTok account must equal the channel handle at the click; unreadable = stop.
- A job whose Post was already pressed is **never** cancelled or re-prepared; an uncertain result is `confirmation_unknown`
  (queue status "รอตรวจผลจาก TikTok") and has to be checked on TikTok by a person. Errors after the click are unknown, not failed.
- Stop never cuts the verify/record step of a clip that was already clicked. Only one run at a time across all open panels.
- The API only accepts posting requests from a loopback `Host` (set `OMNICUT_ALLOWED_HOSTS` for another local name).

## When something goes wrong
- **Run history**: "คัดลอกประวัติรอบ" copies the last runs (every log line with its job id, a redacted page snapshot for failed /
  unconfirmed clips). It survives closing the panel.
- **Attention**: an unconfirmed / halted / failed run raises a browser notification and a red `!` badge until the panel is opened.
- A run cut off by closing the panel or a crash is detected the next time the panel opens and its claimed job is parked.
- Deleted a draft on TikTok? Reset the queue row to "planned" (the draft-reset button in the app).

## Files
`background.js` worker (CDP) · `sidepanel.html/js` panel · `batch_orchestrator.js` run loop · `post_guard.js` content + row rules ·
`limits.js` shared numbers · `preflight.js` readiness verdict · `run_history.js` history/redaction · `run_lock.js` one-run lock ·
`clip_state.js` selection · `quota_detector.js` / `stats_parser.js` readers. Tests: `*.test.cjs` (`node --test`).

**After changing the extension, bump `manifest.json` version and reload it at `chrome://extensions`** — Chrome caches the service
worker script per extension id + version, so an un-bumped reload can silently keep running old code.
