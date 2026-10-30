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

# 1. Click Discard on dialog
d_res = eval_tab('''(() => {
    const dialog = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal');
    if (dialog) {
        const d = Array.from(dialog.querySelectorAll('button')).find(b => (b.innerText||'').trim() === 'Discard');
        if (d) { d.click(); return { clicked_dialog: true }; }
    }
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find(btn => (btn.innerText||'').trim() === 'Discard');
    if (b) { b.click(); return { clicked_btn: true }; }
    return { none: true };
})()''')
print("Discard result:", d_res)

time.sleep(1)

# Check buttons on page
btns = eval_tab('''Array.from(document.querySelectorAll('button')).map(b => (b.innerText||'').trim()).filter(Boolean)''')
print("Buttons remaining:", btns)
