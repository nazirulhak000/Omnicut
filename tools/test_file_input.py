import sys
import subprocess
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import resolve_tab, run_cdp, wait_for_file_input

sys.stdout.reconfigure(encoding='utf-8')
tid = resolve_tab()
print(f"Tab ID: {tid}")

nid = wait_for_file_input(tab_id=tid)
print(f"wait_for_file_input nodeId: {nid}")

test_video = str(BASE_DIR / '04_Exports' / 'Ready_to_post' / 'ORI01-ปัญหาก่อนใช้_1_20260917_181224.mp4')
print(f"Testing video: {test_video}")
print(f"File exists: {Path(test_video).exists()}")

res = run_cdp('DOM.setFileInputFiles', {'files': [test_video], 'nodeId': nid}, tab_id=tid)
print("DOM.setFileInputFiles response:", res)
