# Multi-day TikTok publishing queue plan

## Product job

The queue is an agenda for exported clips that are ready to send to TikTok Studio. The user must be able to answer, at a glance, which clip will be prepared for which day and time, then hand one selected item to the existing Extension checklist.

## Data contract

Each queue item is keyed by the normalized export filename under `04_Exports`; the Ready_to_post/Posted directory is a lifecycle location. It stores the source references needed to prepare a post, the `scheduled_at` timestamp in `Asia/Bangkok`, lifecycle status, and `created_at`/`updated_at` timestamps. A clip can have at most one active queue item. Posted items remain as history and cannot be scheduled again.

Lifecycle: `planned` (รอจัดส่ง) → `ready_for_extension` (พร้อมทำใน Extension) → `awaiting_post` (รอกดโพสต์) → `posted` (โพสต์แล้ว), with `failed` (ผิดพลาด) and retry/reset actions. Removing a queue item never deletes its export; it returns the clip to the ready pool.

## API shape

- `GET /api/schedule-queue` with optional date range/status filters, sorted ascending by `scheduled_at`.
- `POST /api/schedule-queue` creates one or many validated items; rejects duplicate `video_path`, invalid time increments, missing export files, and occupied timestamps.
- `PATCH /api/schedule-queue/{id}` reschedules or updates a guarded lifecycle state.
- `DELETE /api/schedule-queue/{id}` removes an item from the plan without deleting media.
- `POST /api/schedule-queue/{id}/prepare` reuses the existing TikTok prepare contract for exactly one item and marks it ready for Extension.

The backend store uses the existing document-store/SQLite mirror pattern so reloads and server restarts preserve the queue. The existing single pending Extension job remains unchanged; the queue only prepares one selected item at a time. The Extension now prefers active queue rows and receives their scheduled date/time when a row is prepared; when the queue is empty it keeps the previous ready-export fallback.

## UI direction

Operate-mode Agenda, replacing the four-column today-only slot grid. A compact toolbar provides refresh, single add, bulk add, and a queue count. The main surface groups rows by local calendar date and sorts each group by time. Every row keeps the thumbnail, project/clip name, exact date/time, status, cover/product readiness, and one clear Extension action visible.

Single add opens a ready-export picker. Bulk add opens a review step where the selected order can be rearranged, a start date/time and interval can be set, collisions are previewed, and the final batch is committed atomically. All times snap to five-minute increments.

Drag and drop moves a planned row to another date/time and snaps to the nearest free five-minute slot. Keyboard/date-time controls provide the same operation without dragging. Items already handed to the Extension must be reset before moving; posted items are locked. Duplicate attempts focus the existing row instead of creating another item.

## Verification

Cover single-item and bulk creation, duplicate rejection, five-minute validation, chronological sorting, date-range loading, drag/reschedule guards, remove-without-delete, restart persistence, one-at-a-time Extension handoff, and the current frozen steps 1-4/cover flows through deterministic tests and browser verification.
