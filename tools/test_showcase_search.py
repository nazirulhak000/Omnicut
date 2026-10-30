import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from tools.batch_tiktok_uploader import eval_js, run_cdp, sleep_s, navigate_to_upload, wait_for_file_input

def test_showcase():
    print("Navigating to upload...")
    navigate_to_upload()
    sleep_s(2)

    # We need a dummy video or just see if "+ เพิ่ม" exists
    # If on upload page, "+ เพิ่ม" only appears after a video is uploaded or file selected
    # Let's check if "+ เพิ่ม" is visible right now
    state = eval_js('''(() => {
        const text = document.body.innerText;
        return {
            hasUpload: text.includes('Select video') || text.includes('เลือกวิดีโอ'),
            url: window.location.href
        };
    })()''')
    print("State:", state)

if __name__ == '__main__':
    test_showcase()
