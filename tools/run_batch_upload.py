"""
Batch Upload Runner with dynamic quota tracking, live flush, out-of-stock auto-skip, and exact quota fulfilment:
- Target Schedule: 30 clips total (Already reached: 33 clips scheduled)
- Target Draft: 30 clips total (1 already drafted -> 29 remaining)
- Untouched: Remaining clips in queue (including all 5 out-of-stock Orsen S6 clips)
"""
import sys
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.schedule_store import ScheduleQueueStore
from tools.batch_tiktok_uploader import process_single_clip, sleep_s, clean_reset_upload_page

def log(msg):
    print(msg, flush=True)

def run():
    sys.stdout.reconfigure(encoding='utf-8')
    items = ScheduleQueueStore.list_items()
    non_couple = [c for c in items if not c.get('is_couple')]
    
    # 84 non-couple clips in the active schedule window
    target_batch = [c for c in non_couple if (c.get('scheduled_at') or '') >= '2026-10-16']
    already_posted = [c for c in target_batch if c.get('status') == 'posted']
    already_draft = [c for c in target_batch if c.get('status') == 'draft']
    planned = [c for c in target_batch if c.get('status') == 'planned']
    
    # Strict exclude of out-of-stock items (Orsen S6 and Hatari 16") per user directive
    out_of_stock_ids = {'1731512091369702645', '1730405090572077252'}
    valid_pool = [c for c in planned if c.get('tiktok_product_id') not in out_of_stock_ids]
    skipped_oos_clips = [c for c in planned if c.get('tiktok_product_id') in out_of_stock_ids]
    
    TARGET_SCHEDULE_TOTAL = 30
    TARGET_DRAFT_TOTAL = 30
    
    needed_schedule = max(0, TARGET_SCHEDULE_TOTAL - len(already_posted))
    needed_drafts = max(0, TARGET_DRAFT_TOTAL - len(already_draft))
    
    log(f"=======================================================")
    log(f"📊 BATCH TIKTOK AUTO-UPLOAD STATUS (Profile 1)")
    log(f"Total active non-couple clips in batch: {len(target_batch)}")
    log(f"Already Scheduled (posted): {len(already_posted)} clips (Quota: {TARGET_SCHEDULE_TOTAL}) -> {'COMPLETE ✅' if needed_schedule == 0 else f'Needs {needed_schedule}'}")
    log(f"Already Drafted (draft):    {len(already_draft)} clips (Quota: {TARGET_DRAFT_TOTAL}) -> Needs {needed_drafts} more")
    log(f"Currently Planned:          {len(planned)} clips (Valid in-stock: {len(valid_pool)}, Out-of-stock skipped: {len(skipped_oos_clips)})")
    log(f"Target Untouched Planned:   {len(planned) - needed_drafts} clips (includes all {len(skipped_oos_clips)} out-of-stock clips)")
    log(f"=======================================================")

    # Ensure dropzone is completely clean before starting
    clean_reset_upload_page()
    sleep_s(2)

    scheduled_clips = []
    drafted_clips = []
    pool_index = 0

    # 1. SCHEDULE BATCH (if needed)
    if needed_schedule > 0:
        log(f"\n=== BATCH 1: SCHEDULE MODE (Target: {needed_schedule} new clips to reach {TARGET_SCHEDULE_TOTAL}) ===")
        while len(scheduled_clips) < needed_schedule and pool_index < len(valid_pool):
            clip = valid_pool[pool_index]
            pool_index += 1
            cid = clip.get('id', '')
            
            fresh = ScheduleQueueStore.get_item(cid)
            if not fresh or fresh.get('status') != 'planned':
                log(f"⏩ Skipping {cid[:8]} (already {fresh.get('status') if fresh else 'none'})")
                continue
                
            pname = clip.get('product_name', '')
            vpath = clip.get('video_path', '')
            log(f"\n=======================================================")
            log(f">>> [SCHEDULE {len(scheduled_clips)+1}/{needed_schedule}] Clip {cid[:8]} | {pname}")
            log(f"    Video: {vpath}")
            log(f"=======================================================")
            try:
                ok = process_single_clip(clip, mode='schedule')
                if ok:
                    scheduled_clips.append(clip)
                    log(f"✅ Finished Schedule Clip {cid[:8]} ({len(scheduled_clips)}/{needed_schedule}) [Total Scheduled: {len(already_posted) + len(scheduled_clips)}/{TARGET_SCHEDULE_TOTAL}]")
                else:
                    log(f"⚠️ Skipped / Failed Schedule Clip {cid[:8]} -> moving to next candidate in pool")
            except Exception as e:
                log(f"❌ Exception on clip {cid[:8]}: {e}")
            
            log("⏳ Cooldown 20 seconds before next clip...")
            sleep_s(20)
    else:
        log(f"\n✅ SCHEDULE QUOTA ALREADY FULFILLED ({len(already_posted)}/{TARGET_SCHEDULE_TOTAL} scheduled). Skipping directly to Draft Mode!")

    # 2. DRAFT BATCH
    log(f"\n=== BATCH 2: DRAFT MODE (Target: {needed_drafts} new drafts -> {len(already_draft)} + {needed_drafts} = {TARGET_DRAFT_TOTAL} total) ===")
    while len(drafted_clips) < needed_drafts and pool_index < len(valid_pool):
        clip = valid_pool[pool_index]
        pool_index += 1
        cid = clip.get('id', '')
        
        fresh = ScheduleQueueStore.get_item(cid)
        if not fresh or fresh.get('status') != 'planned':
            log(f"⏩ Skipping {cid[:8]} (already {fresh.get('status') if fresh else 'none'})")
            continue

        pname = clip.get('product_name', '')
        vpath = clip.get('video_path', '')
        log(f"\n=======================================================")
        log(f">>> [DRAFT {len(drafted_clips)+1}/{needed_drafts}] Clip {cid[:8]} | {pname}")
        log(f"    Video: {vpath}")
        log(f"=======================================================")
        try:
            ok = process_single_clip(clip, mode='draft')
            if ok:
                drafted_clips.append(clip)
                log(f"✅ Finished Draft Clip {cid[:8]} ({len(drafted_clips)}/{needed_drafts}) [Total Drafts: {len(already_draft) + len(drafted_clips)}/{TARGET_DRAFT_TOTAL}]")
            else:
                log(f"⚠️ Skipped / Failed Draft Clip {cid[:8]} -> moving to next candidate in pool")
        except Exception as e:
            log(f"❌ Exception on draft clip {cid[:8]}: {e}")
        
        log("⏳ Cooldown 20 seconds before next clip...")
        sleep_s(20)
        
    # Final Untouched summary
    items_now = ScheduleQueueStore.list_items()
    target_now = [c for c in items_now if not c.get('is_couple') and (c.get('scheduled_at') or '') >= '2026-10-16']
    posted_final = [c for c in target_now if c.get('status') == 'posted']
    draft_final = [c for c in target_now if c.get('status') == 'draft']
    planned_final = [c for c in target_now if c.get('status') == 'planned']
    
    log(f"\n=======================================================")
    log("🎉 BATCH RUN COMPLETE!")
    log(f"Scheduled: {len(posted_final)}/{TARGET_SCHEDULE_TOTAL} total clips posted")
    log(f"Drafted:   {len(draft_final)}/{TARGET_DRAFT_TOTAL} total clips drafted")
    log(f"Untouched: {len(planned_final)} clips remain planned (includes all {len(skipped_oos_clips)} out-of-stock Orsen S6)")
    log("=======================================================")

if __name__ == '__main__':
    run()
