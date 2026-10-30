import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import (
    resolve_tab, run_cdp, eval_js, sleep_s, clean_reset_upload_page,
    wait_for_file_input, wait_for_upload_badge, type_caption,
    attach_product_link
)

sys.stdout.reconfigure(encoding='utf-8')

test_video = str(BASE_DIR / '04_Exports' / 'Ready_to_post' / 'ess02-pov-chat-28s.mp4')
test_pid = '1736306705697900220' # HOYAUP พัดลมมือถือแม่เหล็ก
test_pname = 'HOYAUP พัดลมมือถือแม่เหล็ก'

print(f"Testing on video: {Path(test_video).name}")
print(f"Product: {test_pname} (ID: {test_pid})")

tid = 1319910483
print(f"Resolved Tab ID: {tid}")

# 1. Clean reset
clean_reset_upload_page(tab_id=tid)
sleep_s(1)

# 2. File input
nid = wait_for_file_input(tab_id=tid)
print(f"File input nodeId: {nid}")
if not nid:
    print("Failed to find file input!")
    sys.exit(1)

print("Setting file input...")
run_cdp('DOM.setFileInputFiles', {'files': [test_video], 'nodeId': nid}, tab_id=tid)
sleep_s(1)

# 3. Wait for upload badge
ok_upload = wait_for_upload_badge(tab_id=tid, timeout_s=180)
print(f"Upload badge confirmed: {ok_upload}")
if not ok_upload:
    print("Upload badge timed out!")
    sys.exit(1)

# 4. Attach product link
ok_prod = attach_product_link(test_pid, cart_name=test_pname, tab_id=tid)
print(f"Product link attachment result: {ok_prod}")

# 5. Clean up
clean_reset_upload_page(tab_id=tid)
print("Test completed cleanly!")
