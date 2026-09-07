# Weekly schedule templates and product-rotating auto-fill

## Confirmed behavior

- Store a durable Monday-Sunday weekly template in `Asia/Bangkok`. Each day has five primary times, enabled-day flags, and optional week-specific overrides.
- The default template is 07:00, 10:00, 12:00, 16:00, and 20:00. Users can edit, copy, reset, and save a selected week. Existing queue records never change when a template changes.
- Auto-fill supports today, this week, or a custom date range. It previews generated rows and allows an optional product filter and clip limit before atomic confirmation.
- Auto-fill starts after the latest scheduled queue timestamp. It skips past slots, preserves existing rows, continues into the next enabled day when needed, and never overwrites a deliberate gap.
- Product order is shuffled once per run and rotates without adjacent repeats across day boundaries. A clip is randomly chosen within each product. Ready, unqueued, unposted exports only are eligible.
- If no clip is available for a slot, the preview leaves it empty and explains why. Posted clips stay permanently unavailable; removed planned clips return to the ready pool.
- A planned row whose timestamp is in the past is shown as overdue. Requeue opens a review dialog with the next free slot, updates the same record, and never creates a duplicate MP4 identity.

## Implementation contract

- `schedule_templates` document store/API: read default/weekly effective template, upsert a week override, copy/reset, and validate exactly five unique five-minute times per enabled day.
- `schedule_queue` auto-fill endpoint: accept range, enabled days, template week, product filter, optional limit, and a random seed; compute a complete preview against the current queue; commit atomically only after the caller confirms.
- Agenda UI: add a weekly template editor and an auto-fill modal with range choice, product filter, limit, preview order, skipped-slot reasons, and explicit save. Keep manual single/bulk add and drag/reschedule intact.
- Tests cover persistence/restart, Monday boundaries, append cursor after manual times, no adjacent product repeats, no duplicate MP4s, past-slot skipping, overdue requeue, atomic collision failure, and deterministic seeded previews.
