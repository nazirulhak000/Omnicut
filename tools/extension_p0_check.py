"""Regression checks in a loaded extension, including the docked Chrome side panel.

Uses an isolated profile, intercepted backend/TikTok fixtures and real runtime,
storage and chrome.debugger APIs. Never prepares or posts production data.
Run: .venv/Scripts/python.exe tools/extension_p0_check.py
"""
from __future__ import annotations

import base64
import json
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / 'tiktok_autopost_extension'
UPLOAD = 'https://www.tiktok.com/tiktokstudio/upload'
DRAFTS = 'https://www.tiktok.com/tiktokstudio/content?tab=draft'


class Sidebar:
    """CDP access to the actual docked sidebar target (not a tab of the same HTML)."""
    def __init__(self, browser, target, pump):
        self.cdp = browser.new_browser_cdp_session()
        self.session = self.cdp.send('Target.attachToTarget', {'targetId': target, 'flatten': False})['sessionId']
        self.responses = {}
        self.sequence = 0
        self.pump = pump
        self.cdp.on('Target.receivedMessageFromTarget', self.receive)

    def receive(self, event):
        if event.get('sessionId') == self.session:
            message = json.loads(event['message'])
            if 'id' in message:
                self.responses[message['id']] = message

    def call(self, method, params=None, timeout=45):
        self.sequence += 1
        seq = self.sequence
        self.cdp.send('Target.sendMessageToTarget', {'sessionId': self.session, 'message': json.dumps({'id': seq, 'method': method, 'params': params or {}})})
        until = time.monotonic() + timeout
        while seq not in self.responses:
            if time.monotonic() > until:
                raise TimeoutError(method)
            self.pump.wait_for_timeout(20)
        message = self.responses.pop(seq)
        if 'error' in message:
            raise RuntimeError(str(message['error']))
        return message.get('result', {})

    def evaluate(self, expression, timeout=45):
        result = self.call('Runtime.evaluate', {'expression': expression, 'awaitPromise': True, 'returnByValue': True, 'userGesture': True}, timeout)
        if result.get('exceptionDetails'):
            raise RuntimeError(str(result['exceptionDetails']))
        return result.get('result', {}).get('value')


def main():
    checks = []
    def check(name, condition, detail=None):
        checks.append({'name': name, 'passed': bool(condition), 'detail': detail})
        print(('PASS ' if condition else 'FAIL ') + name, flush=True)
        if not condition:
            raise AssertionError(f'{name}: {detail}')

    with sync_playwright() as p, tempfile.TemporaryDirectory(prefix='autopost-p0-', dir=ROOT / '.tmp') as profile:
        ctx = p.chromium.launch_persistent_context(profile, headless=False, args=[
            '--headless=new', f'--disable-extensions-except={EXT}', f'--load-extension={EXT}',
            '--window-size=1440,1000', '--disable-background-timer-throttling'], viewport={'width': 1440, 'height': 900})
        try:
            worker = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event('serviceworker')
            ext_id = worker.url.split('/')[2]
            state = {'rows': ['Same product review OLD #EP1'], 'clicks': 0, 'add': True, 'loading': False}
            writes = []

            def backend(route):
                request = route.request
                if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                    writes.append(request.method + ' ' + request.url)
                path = request.url.split(':8000')[-1].split('?')[0]
                payload = {'channel_id': 'main', 'items': []}
                if path == '/api/channels':
                    payload = {'channels': [{'id': 'main', 'handle': '@fixture', 'display_name': 'Fixture', 'status': 'active'}]}
                elif path.endswith('/capabilities'):
                    payload = {'protocol_version': 2, 'durable_jobs': True}
                elif path == '/api/exports':
                    payload = {'exports': []}
                route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))
            ctx.route('http://127.0.0.1:8000/**', backend)

            def tiktok(route):
                if '/tiktokstudio/upload' in route.request.url:
                    html = '''<a data-e2e="profile-icon" href="/@fixture">@fixture</a>
                    <input type="file"><div contenteditable="true">Same product review NEW #EP2</div>
                    <button data-e2e="save_draft_button" onclick="fetch('/fixture-save',{method:'POST'}).then(()=>location.href='/tiktokstudio/content?tab=draft')">Save draft</button>
                    <button data-e2e="post_video_button" onclick="throw Error('MUST NEVER POST')">Post</button>'''
                elif '/fixture-save' in route.request.url:
                    state['clicks'] += 1
                    if state['add']:
                        state['rows'].append('Same product review NEW #EP2')
                    route.fulfill(status=200, content_type='application/json', body='{}')
                    return
                else:
                    import html as html_module
                    rows = ''.join('<div data-tt="components_DraftRowLayout_FlexRow">' + html_module.escape(title) + '<br>00:30<br>Nov 12, 2026</div>' for title in state['rows'])
                    html = '<a data-e2e="profile-icon" href="/@fixture">@fixture</a><h1>Drafts ' + str(state.get('countOverride', len(state['rows']))) + '</h1>' + rows
                    if not state['rows']:
                        html += '<p>No drafts</p>'
                    if state['loading']:
                        html += '<div aria-busy="true">Loading</div>'
                route.fulfill(status=200, content_type='text/html', body='<!doctype html><meta charset="utf-8">' + html)
            ctx.route('https://www.tiktok.com/**', tiktok)

            opener = ctx.new_page()
            opener.goto(f'chrome-extension://{ext_id}/sidepanel.html')
            opener.evaluate('''async () => { const w=await chrome.windows.getCurrent(); const b=document.createElement('button'); b.id='test-open-sidebar'; b.textContent='Open sidebar'; b.onclick=()=>chrome.sidePanel.open({windowId:w.id}); document.body.appendChild(b); }''')
            before = {t['targetId'] for t in ctx.browser.new_browser_cdp_session().send('Target.getTargets')['targetInfos']}
            opener.locator('#test-open-sidebar').click()
            opener.wait_for_timeout(1000)
            targets = ctx.browser.new_browser_cdp_session().send('Target.getTargets')['targetInfos']
            target = next(t for t in targets if t['targetId'] not in before and t['url'].endswith('/sidepanel.html'))
            sidebar = Sidebar(ctx.browser, target['targetId'], opener)
            check('actual docked sidebar target opened', sidebar.evaluate('location.href').endswith('/sidepanel.html'))
            # Playwright routes ordinary tabs but does not own the docked sidebar target.
            # Replace only its HTTP transport; production panel handlers and Chrome APIs remain intact.
            sidebar.evaluate('''globalThis.fixtureWrites=[]; authedFetch=async(url,key,options={})=>{
              if(options.method && !['GET','HEAD','OPTIONS'].includes(options.method))fixtureWrites.push(url);
              let data={channel_id:'main',items:[]};
              if(url.includes('/api/channels'))data={channels:[{id:'main',handle:'@fixture',display_name:'Fixture',status:'active'}]};
              else if(url.includes('/capabilities'))data={protocol_version:2,durable_jobs:true};
              else if(url.includes('/api/exports'))data={exports:[]};
              return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});
            }; channelHandles.set('main','@fixture'); loadExports();''')
            opener.wait_for_timeout(1200)
            check('sidebar list loaded through extension origin', sidebar.evaluate("document.getElementById('headerStatusText').textContent.trim().toUpperCase()") in ('READY', 'ONLINE', 'พร้อม'))

            # Backend/availability are fixtures; all panel handlers, runtime messaging and sync validation remain real.
            worker.evaluate('''() => {
              runPreflight=async()=>({success:true,loggedIn:true,uploadInput:true,handle:'@fixture',viewport:{w:1440,h:900},quota:{remainingSchedule:10,remainingDraft:10}});
              runDetectTikTokQuota=async()=>({success:true,remainingSchedule:10,remainingDraft:10});
              globalThis.fixtureSyncReply={success:true,results:[]};
              runSyncDraftsWithTikTok=async()=>{if(globalThis.fixtureSyncError)throw Error('fixture disconnected');return globalThis.fixtureSyncReply;};
            }''')
            # Exercise the real batch-start button with one selected draft. No confirmation or prepare is allowed on failure.
            sidebar.evaluate('''allClips=[{id:'draft-1',export_id:'exp-1',caption:'Same product review NEW',tiktok_caption:'Same product review NEW',is_draft:true,publish_draft:true,is_scheduled:true,schedule_date:'2030-01-01',schedule_time:'12:00',video_path:'fixture.mp4',name:'Fixture'}]; exportRecordIndex=new Map([['exp-1',{export_id:'exp-1'}]]); selectedClipKeys.clear();selectedClipKeys.add(selectionKey(allClips[0])); filterAndRenderClips();''')
            for label, error, reply in [
                ('worker disconnected', True, None),
                ('missing results', False, {'success': True, 'results': []}),
                ('unknown result', False, {'success': True, 'results': [{'id': 'draft-1', 'state': 'unknown', 'label': 'Unknown'}]}),
            ]:
                worker.evaluate('(v)=>{globalThis.fixtureSyncError=v.error;globalThis.fixtureSyncReply=v.reply;}', {'error': error, 'reply': reply})
                sidebar.evaluate("document.getElementById('batchStartBtn').click()")
                opener.wait_for_timeout(800)
                info = sidebar.evaluate("({starting:batchStarting,dialog:document.getElementById('confirmOverlay').open,text:document.getElementById('status').textContent})")
                check('draft run blocked: ' + label, not info['starting'] and not info['dialog'] and bool(info['text']), info)
            # Clear stale verdicts and prove the complete response reaches confirmation through the same button.
            worker.evaluate("() => {globalThis.fixtureSyncReply={success:true,results:[{id:'draft-1',state:'ok'}]};}")
            sidebar.evaluate("draftSyncState.clear();filterAndRenderClips();document.getElementById('batchStartBtn').click()")
            opener.wait_for_timeout(800)
            check('complete draft sync reaches the real confirmation dialog', sidebar.evaluate("document.getElementById('confirmOverlay').open"))
            sidebar.evaluate("document.getElementById('confirmCancelBtn').click()")
            opener.wait_for_timeout(300)
            check('cancelled confirmation sends no backend writes', not writes and sidebar.evaluate('fixtureWrites.length') == 0, writes)

            # The reported Prepare button must open editable data even when the batch guard blocks it.
            worker.evaluate("() => {fetchPendingJob=async()=>({job_id:'fixture-prepare',channel_id:'main'});}")
            sidebar.evaluate('''globalThis.originalFixtureFetch=authedFetch;globalThis.preparePayloads=[];
              authedFetch=async(url,key,options={})=>{if(url.endsWith('/prepare')){const body=JSON.parse(options.body);preparePayloads.push(body);return new Response(JSON.stringify({job_id:'fixture-prepare',protocol_version:2,channel_id:'main'}),{status:200});}return originalFixtureFetch(url,key,options);};
              globalThis.originalOpenUpload=openTikTokUploadTab;openTikTokUploadTab=async()=>({id:0});
              globalThis.originalLoadExports=loadExports;loadExports=async()=>{};
              exportRecordIndex=new Map([['exp-1',{export_id:'exp-1'}]]);
              activeClip=null;allClips=[{id:'edit-1',export_id:'exp-1',rel_path:'fixture.mp4',name:'Editable clip',tiktok_caption:'Feature {value}',tiktok_hashtags:'#test'}];
              draftSyncState.clear();filterAndRenderClips();document.querySelector('.card .btn-primary').click();''')
            opener.wait_for_timeout(250)
            check('blocked card opens editable preparation dialog', sidebar.evaluate("document.querySelector('.clip-setup-dialog')?.open === true"))
            check('preparation dialog fits the actual sidebar and has an opaque surface', sidebar.evaluate("(()=>{const d=document.querySelector('.clip-setup-dialog'),r=d.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&getComputedStyle(d).backgroundColor!=='rgba(0, 0, 0, 0)';})()"))
            axe_file = ROOT / '.tmp' / 'autopost-axe.min.js'
            if axe_file.exists():
                sidebar.evaluate(axe_file.read_text(encoding='utf-8'))
                for theme in ['dark','light']:
                    sidebar.evaluate(f"applyTheme('{theme}')")
                    opener.wait_for_timeout(350)  # evaluate the settled theme, not interpolated transition colors
                    violations = sidebar.evaluate("axe.run(document).then(r=>r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({html:n.html,summary:n.failureSummary}))})))")
                    check('preparation dialog axe accessibility: '+theme, not violations, violations)
                sidebar.evaluate("applyTheme('dark')")
            screenshot = sidebar.call('Page.captureScreenshot', {'format':'png'})
            (ROOT / '.tmp' / 'autopost-prepare-dialog.png').write_bytes(base64.b64decode(screenshot['data']))
            sidebar.evaluate("document.getElementById('clipSetupIntent').value='draft';document.getElementById('clipSetupIntent').dispatchEvent(new Event('change'));document.getElementById('clipSetupForm').requestSubmit()")
            check('unresolved placeholder stays editable without preparing', sidebar.evaluate("preparePayloads.length===0 && document.getElementById('clipSetupError').textContent.length>0"))
            sidebar.evaluate("document.getElementById('clipSetupCaption').value='Feature works well';document.getElementById('clipSetupIntent').value='schedule';document.getElementById('clipSetupIntent').dispatchEvent(new Event('change'));document.getElementById('clipSetupForm').requestSubmit()")
            check('missing schedule cannot silently become a live post', sidebar.evaluate('preparePayloads.length===0'))
            sidebar.evaluate("document.getElementById('clipSetupDate').value='2030-01-01';document.getElementById('clipSetupTime').value='12:00';exportRecordIndex=new Map([['exp-1',{export_id:'exp-1'}]]);document.getElementById('clipSetupForm').requestSubmit()")
            opener.wait_for_timeout(500)
            check('corrected caption and explicit slot prepare a claimed job', sidebar.evaluate("preparePayloads.length===1 && preparePayloads[0].intent==='schedule' && preparePayloads[0].caption==='Feature works well' && activeClip?.job_id==='fixture-prepare'"), sidebar.evaluate("({payloads:preparePayloads,active:activeClip,status:document.getElementById('status').textContent})"))
            sidebar.evaluate("activeClip=null;resetChecklist();renderActiveClipBanner();openTikTokUploadTab=originalOpenUpload;authedFetch=originalFixtureFetch;loadExports=originalLoadExports")

            # Cross-document Web Locks serialize storage mutations in the actual extension origin.
            opener.evaluate("window.fixtureLock=OmniRunLock.acquire(chrome.storage.local,'fixture-owner-A');true")
            other = sidebar.evaluate("OmniRunLock.acquire(chrome.storage.local,'fixture-owner-B')")
            first = opener.evaluate('window.fixtureLock')
            check('two real extension documents grant exactly one run owner', sum(bool(r['ok']) for r in [first,other]) == 1)
            blocked = sidebar.evaluate("new Promise(r=>chrome.runtime.sendMessage({action:'select-posting-channel',channelId:'main'},r))")
            check('worker refuses foreign manual action during another run', blocked.get('success') is False and 'posting_run_owned' in blocked.get('error',''), blocked)
            opener.evaluate("OmniRunLock.release(chrome.storage.local,'fixture-owner-A')")
            sidebar.evaluate("OmniRunLock.release(chrome.storage.local,'fixture-owner-B')")
            worker.evaluate("() => {globalThis.originalRelease=releasePostingJob;releasePostingJob=async()=>{throw Error('fixture backend offline');};}")
            sidebar.evaluate("chrome.storage.local.set({omnicutBatchRunLock:{owner:'fixture-orphan',beat:1}})")
            sidebar.evaluate('recoverInterruptedRun()')
            check('failed recovery retains the orphan marker', sidebar.evaluate("OmniRunLock.read(chrome.storage.local)").get('owner') == 'fixture-orphan')
            worker.evaluate("() => {releasePostingJob=originalRelease;}")
            sidebar.evaluate('recoverInterruptedRun()')
            check('successful recovery clears the old marker', sidebar.evaluate('OmniRunLock.read(chrome.storage.local)') is None)

            upload = ctx.new_page()
            upload.goto(UPLOAD)
            # Only the backend protocol and upload processing are stubbed. Baseline tab, identity DOM,
            # save click, navigation, draft DOM reader, storage and runtime use actual Chromium APIs.
            worker.evaluate('''() => {
              waitForUploadComplete=async()=>true;
              openUploadPage=async()=>{};
              globalThis.fixtureReceipts=[];
              globalThis.fixtureSnapshots=[];
              const originalEvidence=readDraftRowEvidence;
              readDraftRowEvidence=async(...args)=>{const result=await originalEvidence(...args);fixtureSnapshots.push(result.page);return result;};
              savePostingReceipt=async(job,source,outcome,proof)=>{globalThis.fixtureReceipts.push({outcome,proof});};
              guardPostingAction=async(job,send,tab,opts)=>{
                if(opts?.beginPublish){job.publish_attempted_at=Date.now()/1000; job.status='publishing';}
                return checkPostingAccount(job,await readStudioAccount(send));
              };
              fetchPendingJob=async()=>globalThis.fixtureJob;
            }''')
            def seed():
                worker.evaluate('''() => {globalThis.fixtureJob={job_id:'fixture-job',protocol_version:2,channel_id:'main',caption:'Same product review NEW',hashtags:'#EP2',target_handle:'@fixture',lease_expires_at:Date.now()/1000+300,status:'claimed'};globalThis.fixtureReceipts=[];}''')
            seed()
            message = "new Promise(r=>chrome.runtime.sendMessage({action:'save-draft-only'},r))"
            result = sidebar.evaluate(message)
            check('draft saved using real CDP click and new row evidence', result.get('outcome') == 'draft_saved' and state['clicks'] == 1, {'result':result,'snapshots':worker.evaluate('fixtureSnapshots.slice(-3)')})
            check('receipt records the confirmed draft only once', worker.evaluate("fixtureReceipts.map(r=>r.outcome)") == ['draft_saved'])
            check('baseline tab was cleaned up', len([x for x in ctx.pages if 'tab=draft' in x.url]) == 1)
            check('baseline persisted for reconciliation', worker.evaluate("(async()=>{const s=await postingState();return s.activeJob?.draft_baseline?.complete===true;})()"))

            # A partial inventory must stop before consuming the attempt, including cleanup.
            state['countOverride'] = 3
            upload.goto(UPLOAD)
            seed()
            result = sidebar.evaluate(message)
            check('incomplete baseline stops before any additional click', result.get('success') is False and result.get('postAttempted') is False and 'draft_baseline_incomplete' in result.get('error','') and state['clicks'] == 1, result)
            check('temporary baseline tab closes even on a failed scan', not [x for x in ctx.pages if 'tab=draft' in x.url])
            del state['countOverride']
            # Existing draft is refused before another click.
            upload.goto(UPLOAD)
            seed()
            result = sidebar.evaluate(message)
            check('existing draft stops before Save draft click', result.get('success') is False and 'draft_already_exists' in result.get('error','') and state['clicks'] == 1, result)
            # Successful click followed only by an old/common-prefix row must remain unknown.
            state['rows'] = ['Same product review OLD #EP1']
            state['add'] = False
            upload.goto(UPLOAD)
            seed()
            result = sidebar.evaluate(message, timeout=40)
            check('old common-prefix row cannot confirm a failed save', result.get('success') is False and result.get('postAttempted') is True, result)
            check('uncertain save records unknown without a retry click', worker.evaluate("fixtureReceipts.map(r=>r.outcome)") == ['confirmation_unknown'] and state['clicks'] == 2)
            check('no production API writes escaped fixtures', not writes, writes)
            screenshot = sidebar.call('Page.captureScreenshot', {'format':'png'})
            (ROOT / '.tmp' / 'autopost-p0-sidebar.png').write_bytes(base64.b64decode(screenshot['data']))
        finally:
            ctx.close()
    output = ROOT / '.tmp' / 'autopost-p0-browser-results.json'
    output.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'TOTAL {len(checks)} passed', flush=True)


if __name__ == '__main__':
    main()
