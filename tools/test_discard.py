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

# 1. Click Discard
click_res = eval_tab('''(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const dBtn = btns.find(b => (b.innerText || '').trim() === 'Discard' || (b.innerText || '').trim() === 'ละทิ้ง');
    if (dBtn) {
        dBtn.click();
        return { clicked: true, text: dBtn.innerText };
    }
    return { clicked: false };
})()''')
print("Click banner Discard:", click_res)

time.sleep(1)

# 2. Check if a confirmation modal opened
dialog_res = eval_tab('''(() => {
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .TUXModal'));
    return dialogs.map(d => ({
        text: d.innerText,
        buttons: Array.from(d.querySelectorAll('button')).map(b => b.innerText)
    }));
})()''')
print("Dialog after banner Discard:", json.dumps(dialog_res, ensure_ascii=False, indent=2))
