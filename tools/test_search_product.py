import sys
sys.path.insert(0, '.')
from tools.batch_tiktok_uploader import eval_js, resolve_tab, CLI_JS
import time
import json
import subprocess

sys.stdout.reconfigure(encoding='utf-8')
tid = resolve_tab()
product_id = "1736306705697900220" # HOYAUP พัดลมมือถือแม่เหล็ก
print(f"Testing search for product ID: {product_id}...")

# 1. Type into search input
search_res = eval_js(f'''(() => {{
    const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]') || document;
    const search = modal.querySelector('input.TUXTextInputCore-input, input[placeholder*="Search"], input[placeholder*="ค้นหา"]') ||
                   modal.querySelector('input[type="text"], input:not([type])');
    if (search) {{
        search.focus();
        search.select();
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
        if (setter) setter.call(search, "{product_id}"); else search.value = "{product_id}";
        search.dispatchEvent(new Event('input', {{ bubbles: true }}));
        search.dispatchEvent(new Event('change', {{ bubbles: true }}));
        
        const icon = modal.querySelector('.TUXTextInputCore-trailingIconWrapper, svg, button');
        if (icon && icon !== search) {{
            try {{ icon.click(); }} catch(e) {{}}
        }}
        return {{ success: true, val: search.value }};
    }}
    return {{ success: false }};
}})()''', tid)
print("Search input result:", json.dumps(search_res, indent=2))

# 2. Press Enter via CDP
cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', str(tid), '--method', 'Input.dispatchKeyEvent', '--params', json.dumps({'type': 'rawKeyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13})]
subprocess.run(cmd, capture_output=True, text=True)
cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', str(tid), '--method', 'Input.dispatchKeyEvent', '--params', json.dumps({'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13})]
subprocess.run(cmd, capture_output=True, text=True)

time.sleep(2.5)

# 3. Check search results
results = eval_js('''(() => {
    const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]') || document;
    const rows = Array.from(modal.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, tbody tr'))
        .filter(r => !r.querySelector('th') && (r.innerText || '').trim().length > 0);
    return rows.map(r => ({
        text: (r.innerText || '').trim().substring(0, 150),
        hasRadio: Boolean(r.querySelector('input[type="radio"], .TUXRadioStandalone')),
        isRadioDisabled: Boolean(r.querySelector('input[disabled], .TUXRadioStandalone--disabled'))
    }));
})()''', tid)
print("Search results:", json.dumps(results, indent=2, ensure_ascii=False))
