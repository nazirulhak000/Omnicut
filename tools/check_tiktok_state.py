import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from tools.batch_tiktok_uploader import eval_js, run_cdp

def check():
    state = eval_js('''(() => {
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .TUXModal, .modal, .semi-modal')).map(d => ({
            text: d.innerText.slice(0, 300),
            buttons: Array.from(d.querySelectorAll('button')).map(b => b.innerText.trim())
        }));
        const buttons = Array.from(document.querySelectorAll('button')).filter(b => b.offsetWidth > 0).map(b => b.innerText.trim());
        const bodyTextSnippet = document.body.innerText.slice(0, 500);
        return {
            url: window.location.href,
            dialogs: dialogs,
            visibleButtons: buttons.slice(0, 30),
            bodyTextSnippet: bodyTextSnippet
        };
    })()''')
    print(json.dumps(state, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    check()
