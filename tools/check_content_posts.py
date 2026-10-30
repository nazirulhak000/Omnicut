import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import eval_js, resolve_tab, run_cdp, defuse_beforeunload

tid = resolve_tab()
print("Tab ID:", tid)

# Check posts by navigating to content page in a new tab or this tab
# Let's open a new tab or check current tab
# Wait, let's open content in a new tab via open-browser-use or CDP Target.createTarget
res = run_cdp('Target.createTarget', {'url': 'https://www.tiktok.com/tiktokstudio/content'}, tab_id=tid)
target_id = res.get('result', {}).get('targetId')
print("Created content tab:", target_id)
