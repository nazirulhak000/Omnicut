import subprocess
import json
import time
import sys
from pathlib import Path

CLI_JS = r'C:\Users\nazir\AppData\Roaming\npm\node_modules\open-browser-use\cli\open-browser-use.js'
TAB_ID = 1319910107

def run_cdp(method, params, tab_id=TAB_ID):
    cmd = ['node', CLI_JS, 'cdp', '--tab-id', str(tab_id), '--method', method, '--params', json.dumps(params)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.stdout:
        return json.loads(res.stdout)
    return {'error': res.stderr}

def eval_js(js, tab_id=TAB_ID):
    res = run_cdp('Runtime.evaluate', {'expression': js, 'returnByValue': True}, tab_id=tab_id)
    return res.get('result', {}).get('result', {}).get('value')

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    video_abs = str(Path('04_Exports/Ready_to_post/GOC01-รีวิวสเปก_1_20260916_145649.mp4').resolve())
    print(f'Target video: {video_abs}')
    if not Path(video_abs).exists():
        print('Error: Video file does not exist!')
        return

    # 1. Enable DOM and Runtime
    run_cdp('DOM.enable', {})
    run_cdp('Runtime.enable', {})

    # 2. Get Document and find file input
    doc = run_cdp('DOM.getDocument', {'depth': -1, 'pierce': True})
    root_id = doc.get('result', {}).get('root', {}).get('nodeId')
    node = run_cdp('DOM.querySelector', {'nodeId': root_id, 'selector': 'input[type="file"]'})
    node_id = node.get('result', {}).get('nodeId')
    print(f'File input nodeId: {node_id}')

    if not node_id:
        print('Error: Could not find file input on page!')
        return

    # 3. Set file input
    print('Setting video file via DOM.setFileInputFiles...')
    set_res = run_cdp('DOM.setFileInputFiles', {'files': [video_abs], 'nodeId': node_id})
    print('setFileInputFiles result:', set_res)

    # 4. Wait a few seconds and check what appears on the page
    print('Waiting 5 seconds for TikTok to parse video...')
    time.sleep(5)

    check_dom = eval_js('''(() => {
        const text = document.body ? document.body.innerText.slice(0, 500) : '';
        const hasEditor = Boolean(document.querySelector('[contenteditable="true"]'));
        const buttons = Array.from(document.querySelectorAll('button')).map(b => (b.innerText || b.textContent || '').trim()).filter(Boolean);
        return {
            hasEditor,
            buttons: buttons.slice(0, 15),
            textSnippet: text.replace(/\\n+/g, ' ')
        };
    })()''')
    print('DOM check after 5s:', json.dumps(check_dom, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
