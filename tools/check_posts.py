import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import eval_js, resolve_tab, run_cdp, defuse_beforeunload

tid = resolve_tab()
print("Checking tab:", tid)

# Check posts on Posts page if available, or navigate to https://www.tiktok.com/tiktokstudio/content
# First, let's see what is currently in TikTok Studio tabs or open content in a new tab or inspect current page
# Let's inspect the current form values:
vals = eval_js('''(() => {
    const title = document.querySelector('[contenteditable="true"]')?.innerText;
    const postNowRadio = document.querySelector('input[type="radio"][value="post_now"]')?.checked;
    const scheduleRadio = document.querySelector('input[type="radio"][value="schedule"]')?.checked;
    const postBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Post');
    const schedBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Schedule');
    const draftBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Save draft');

    return {
        title,
        postNowRadio,
        scheduleRadio,
        hasPostBtn: !!postBtn,
        hasSchedBtn: !!schedBtn,
        hasDraftBtn: !!draftBtn
    };
})()''', tid)

print("Current Form state:", vals)
