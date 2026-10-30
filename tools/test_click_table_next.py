import sys
import subprocess
import json
import time

sys.stdout.reconfigure(encoding='utf-8')
CLI_JS = r'C:\Users\nazir\AppData\Roaming\npm\node_modules\open-browser-use\cli\open-browser-use.js'

def eval_tab(expr):
    cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', '1319910483', '--method', 'Runtime.evaluate', '--params', json.dumps({'expression': expr, 'returnByValue': True})]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    data = json.loads(res.stdout)
    return data.get('result', {}).get('result', {}).get('value')

# Click Next in product selector modal
res = eval_tab('''(() => {
    const modal = document.querySelector('.product-selector-modal') || document.querySelector('[role="dialog"]');
    const nextBtn = Array.from(modal.querySelectorAll('button')).find(b => (b.innerText||'').trim() === 'Next');
    if (nextBtn) {
        nextBtn.click();
        return { clicked: true };
    }
    return { clicked: false };
})()''')
print("Click Next result:", res)

time.sleep(1.5)

# Inspect what is open now
dialogs = eval_tab('''Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .TUXModal')).map(d => ({
    text: d.innerText.substring(0, 200),
    classes: d.className
}))''')
print("Dialogs open now:\n", json.dumps(dialogs, ensure_ascii=False, indent=2))
