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

# Try clicking label or input or standalone
res = eval_tab('''(() => {
    const row = document.querySelector('tr.product-tb-row, [class*="product-tb-row"]');
    if (!row) return { error: 'no row' };
    const label = row.querySelector('label.TUXRadio-label, label');
    const input = row.querySelector('input.TUXRadioStandalone-input, input[type="radio"]');
    const standalone = row.querySelector('.TUXRadioStandalone');

    // Click label
    if (label) {
        label.click();
    } else if (standalone) {
        standalone.click();
    } else if (input) {
        input.click();
    }

    // Check if next button is now enabled
    const modal = document.querySelector('.product-selector-modal') || document.querySelector('[role="dialog"]');
    const nextBtn = Array.from(modal.querySelectorAll('button')).find(b => (b.innerText||'').trim() === 'Next');

    return {
        inputChecked: input ? input.checked : null,
        nextBtnClasses: nextBtn ? nextBtn.className : null,
        nextBtnDisabled: nextBtn ? nextBtn.disabled : null
    };
})()''')

print("Result after clicking label:", json.dumps(res, ensure_ascii=False, indent=2))
