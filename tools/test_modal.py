import sys
import subprocess
import json

sys.stdout.reconfigure(encoding='utf-8')
CLI_JS = r'C:\Users\nazir\AppData\Roaming\npm\node_modules\open-browser-use\cli\open-browser-use.js'

def eval_tab(expr):
    cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', '1319910483', '--method', 'Runtime.evaluate', '--params', json.dumps({'expression': expr, 'returnByValue': True})]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    try:
        data = json.loads(res.stdout)
        return data.get('result', {}).get('result', {}).get('value')
    except Exception as e:
        return {'err': str(e), 'raw': res.stdout}

# Test already_open
js = '''(() => {
    const isVisible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
    };
    const texts = Array.from(document.querySelectorAll('h1, h2, h3, h4, [role="tab"], div, span'))
        .filter(isVisible)
        .map(el => (el.innerText || el.textContent || '').trim());
    return texts.filter(t => t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase' || t.includes('Showcase products'));
})()'''

print("Matches:", eval_tab(js))
