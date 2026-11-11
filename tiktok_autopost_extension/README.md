# OmniCut TikTok Post Helper (Chrome extension, side panel)

Fills TikTok Studio's upload form from the OmniCut queue and posts / schedules / saves a draft, **one clip at a time**.
Talks to the backend through the `posting_jobs` protocol v2 (prepare → claim → attempt → ack/reconcile). The unattended,
headless twin of the same worker is `tools/autopost_conductor/`.

## What a run does (side panel → "เริ่มรันอัปโหลด")
Before a manual handoff, **เตรียมคลิปนี้** opens an editable dialog for caption, hashtags and an explicit schedule or draft intent. Missing dates and unresolved placeholders can be fixed there. Confirmation freezes that job's data; it does not bulk-rewrite the queue. Posted, missing and QC-rejected exports remain blocked.
The dialog auto-saves incomplete edits in `chrome.storage.local`, isolated by channel, export and queue row. **บันทึกข้อมูล** saves without preparing or posting; closing/reloading restores those edits. This is local extension storage, not a rewrite of the central queue. A known product name fills `{product_name}`; unknown placeholders and missing date/time are identified together before Prepare can proceed.
**เตรียมคลิปต่อ** keeps the dialog open until the backend has prepared the job and the worker has claimed it. While waiting, controls are disabled to prevent duplicate requests. Backend and unexpected errors appear inside the dialog with the saved values retained for retry; structured API validation errors include their field names.
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
run stops with that reason and only "post now" is possible. **Slot already passed?** The clip keeps its draft on TikTok and goes to "needs a new time" (status "แบบร่างเลยเวลา — ต้องจัดเวลาใหม่", chip
"ต้องจัดเวลาใหม่"). Either edit the card's date/time (saved to the queue row, 5-minute steps, >= 15 min ahead) or press "จัดเวลาใหม่ให้คลิปที่
เกินเวลา": a preview lists old -> new for every planned/draft clip whose slot passed (next free template slot, never the same product or
hook colour on one day, never another clip's slot), and nothing changes until you confirm. Drafts are not touched; the new time is put on the
draft when it is published (no re-upload). The queue row is the single source of truth for the time: a stale panel is refused (409).
Delete-and-re-upload is only worth it when the caption, cover or video must change.
**Deleted or posted by hand on TikTok?** The button "ตรวจกับ TikTok" (also run automatically before a run that contains drafts) reads the
Drafts tab and Studio > Content, read-only, and tells for each draft: still there (ok) / gone from Drafts but the same caption is in Content
("posted outside" -> confirm to close the row, the export is marked posted) / gone everywhere ("deleted" -> reset to planned) / still a draft
but the same caption is already posted ("duplicate risk"). Flagged drafts cannot be ticked. Content is read back only as far as the oldest
draft was saved (minus one day, at most TikTok's 60-day draft lifetime, stopping after 5 consecutive older rows); if the read is cut short the
verdict is "unknown", never "deleted". Match key = the first 20 letters/digits of the caption.
If a publication is cancelled before the click the row returns to
"draft on TikTok" (never to "planned": the draft still exists).

## EP numbers (episode ids)
Every clip lineage (product + angle; a re-render keeps its number) gets a permanent number the first time it enters the queue or is prepared:
`EP1`, `EP2`, ... per channel, atomic, never reused (not even when a draft is deleted or the slot is re-arranged), counter starts at 1 and
can only be raised (`PUT /api/episodes/next`). The backend adds the hashtag `#EP12` (the clip's number) to the job's hashtags (idempotent; another clip's EP tag is
refused), the content guard accepts it, the card shows `EP:1731`, log titles start with it, and the checks against TikTok use the tag to tell
clips apart when it is visible in the list (Studio cuts long captions, so without a visible tag the caption key is still the fallback).
`GET /api/episodes` lists numbers and how many really went out through the app. Old clips get their numbers once with
`python tools/backfill_episodes.py` (PREVIEW by default, `--apply` to write; counts from EP1 = the oldest clip that went out, writes nothing to TikTok and edits no old caption).

## Safety rules that are always on
- Price / discount text, unfilled `{placeholders}`, > 4000 characters, > 30 hashtags are refused everywhere (panel, worker, backend,
  conductor) by one rule set (`post_guard.js` ↔ `scripts/content_guard.py`; shared test cases in `tests/fixtures/`).
- The logged-in TikTok account must equal the channel handle at the click; unreadable = stop.
- A job whose Post was already pressed is **never** cancelled or re-prepared; an uncertain result is `confirmation_unknown`
  (queue status "รอตรวจผลจาก TikTok") and has to be checked on TikTok by a person. Errors after the click are unknown, not failed.
- Stop never cuts the verify/record step of a clip that was already clicked. Only one run at a time across all open panels.
- The API only accepts posting requests from a loopback `Host` (set `OMNICUT_ALLOWED_HOSTS` for another local name).

## When something goes wrong
- Draft checks fail closed: a disconnected worker, missing/duplicate result ids, changed channel or unknown verdict stops the run before confirmation or prepare.
- Saving a draft first reads the complete Drafts inventory in a temporary background tab. A unique new row (EP when visible, otherwise exact caption) must be absent before the click. An existing or ambiguous draft stops the save; insufficient proof after a click remains `confirmation_unknown`. The temporary tab is closed on success and failure.
- Older interrupted draft jobs without a pre-click inventory cannot be automatically confirmed from a list row alone. Check TikTok and use the existing manual confirmation flow.
- **Run history**: "คัดลอกประวัติรอบ" copies the last runs (every log line with its job id, a redacted page snapshot for failed /
  unconfirmed clips). It survives closing the panel.
- **Attention**: an unconfirmed / halted / failed run raises a browser notification and a red `!` badge until the panel is opened.
- A run cut off by closing the panel or a crash is detected the next time the panel opens and its claimed job is parked.
- Run-lock mutations use Web Locks across the extension origin. A second panel cannot change the active run's job/page. Recovery keeps the orphan marker until parking succeeds, and reports failure if it does not.
- A missing draft is classified as deleted only when the Drafts inventory and Content scan are complete. An unreadable or changed account aborts that scan.
- Deleted a draft on TikTok? Reset the queue row to "planned" (the draft-reset button in the app).

## Files
`background.js` worker (CDP) · `sidepanel.html/js` panel · `batch_orchestrator.js` run loop · `post_guard.js` content + row rules ·
`limits.js` shared numbers · `preflight.js` readiness verdict · `run_history.js` history/redaction · `run_lock.js` one-run lock ·
`clip_state.js` selection · `quota_detector.js` / `stats_parser.js` readers. Tests: `*.test.cjs` (`node --test`).
`draft_evidence.js` identifies unique draft rows and checks the pre-click inventory. `tools/extension_p0_check.py` exercises the actual docked sidebar and worker/CDP against isolated fixtures; it never publishes production clips.

**After changing the extension, bump `manifest.json` version and reload it at `chrome://extensions`** — Chrome caches the service
worker script per extension id + version, so an un-bumped reload can silently keep running old code.
