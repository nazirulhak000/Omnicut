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

# Click trailing icon
click_icon = eval_tab('''(() => {
    const icon = document.querySelector('.TUXTextInputCore-trailingIconWrapper');
    if (icon) {
        icon.click();
        const r = icon.getBoundingClientRect();
        return { clicked: true, point: { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) } };
    }
    return { clicked: false };
})()''')
print("Click trailing icon:", click_icon)

time.sleep(2)

rows = eval_tab('''(() => {
    const dialog = document.querySelector('.product-selector-modal') || document.querySelector('[role="dialog"]');
    const trs = Array.from(dialog.querySelectorAll('tr, [role="row"]')).filter(r => !r.querySelector('th'));
    return trs.map(r => ({
        text: (r.innerText || '').trim(),
        hasRadio: Boolean(r.querySelector('input[type="radio"]')),
        radioDisabled: r.querySelector('input[type="radio"]')?.disabled
    }));
})()''')
print("Filtered rows:\n", json.dumps(rows, ensure_ascii=False, indent=2))
