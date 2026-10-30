import sys
sys.path.insert(0, '.')
from tools.probe_tab import eval_tab, get_active_tab

tid = get_active_tab()
res = eval_tab('''(() => {
    const el = document.querySelector('[data-e2e="upload_status_container"]');
    return el ? el.innerText : "NULL";
})()''', tid)
print("upload_status_container text:\n" + str(res))
