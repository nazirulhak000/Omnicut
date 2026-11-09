#!/usr/bin/env node
'use strict';
// End-to-end test of the REAL side panel (the extension's own UI + service worker) in a
// real Chrome: loads the unpacked extension over CDP, opens sidepanel.html, presses the
// real batch button and watches the log. By default the final "post" click is stubbed
// (the post click itself is proven by the conductor), so nothing is published.
//
//   node tools/autopost_conductor/extension_e2e.js            # stubbed post (safe)
//   node tools/autopost_conductor/extension_e2e.js --real-post  # REALLY posts that clip
const fs = require('node:fs');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { createApi, readApiKey, ROOT } = require('./api');
const { pickClips } = require('./conductor');

const PORT = Number(process.env.OMNICUT_PORT || 9333);
const CHROME_EXE = process.env.OMNICUT_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PROFILE_DIR = path.join(ROOT, 'tools', 'tiktok_browser_profile');
const EXT_DIR = path.join(ROOT, 'tiktok_autopost_extension');
const UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const portUp = async () => { try { return (await fetch(`http://127.0.0.1:${PORT}/json/version`)).ok; } catch (_) { return false; } };

function killConductorChrome() {
  spawnSync('powershell', ['-NoProfile', '-Command',
    `Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -like '*tiktok_browser_profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }`]);
}

async function launchChrome() {
  const child = spawn(CHROME_EXE, [
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE_DIR}`,
    '--enable-unsafe-extension-debugging', '--no-first-run', '--no-default-browser-check',
    '--lang=th-TH', '--window-size=1440,960',
    '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
    UPLOAD_URL,
  ], { detached: true, stdio: 'ignore' });
  child.unref();
  for (let i = 0; i < 40; i += 1) { if (await portUp()) return; await sleep(500); }
  throw new Error('Chrome ไม่เปิดพอร์ต debug');
}

class Cdp {
  constructor(url) { this.url = url; this.id = 0; this.pending = new Map(); }
  async open() {
    this.ws = new WebSocket(this.url);
    await new Promise((res, rej) => { this.ws.addEventListener('open', res); this.ws.addEventListener('error', () => rej(new Error('ws error'))); });
    this.ws.addEventListener('message', e => {
      const m = JSON.parse(e.data);
      const w = m.id && this.pending.get(m.id);
      if (w) { this.pending.delete(m.id); m.error ? w.rej(new Error(m.error.message)) : w.res(m.result || {}); }
    });
    return this;
  }
  call(method, params = {}, timeout = 60000) {
    return new Promise((res, rej) => {
      const id = ++this.id;
      const t = setTimeout(() => { this.pending.delete(id); rej(new Error(`cdp_timeout ${method}`)); }, timeout);
      this.pending.set(id, { res: v => { clearTimeout(t); res(v); }, rej: e => { clearTimeout(t); rej(e); } });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async eval(expression, awaitPromise = true) {
    const r = await this.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result?.value;
  }
  close() { try { this.ws.close(); } catch (_) {} }
}

async function browser() {
  const v = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
  return new Cdp(v.webSocketDebuggerUrl).open();
}

async function loadExtension() {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const b = await browser();
    try {
      const { id } = await b.call('Extensions.loadUnpacked', { path: EXT_DIR });
      b.close();
      return id;
    } catch (error) {
      b.close();
      if (attempt) throw new Error(`โหลด extension ไม่ได้: ${error.message}`);
      console.log(`[info] loadUnpacked ไม่สำเร็จ (${error.message}) — เปิด Chrome ใหม่พร้อมแฟล็ก extension debugging`);
      killConductorChrome();
      await sleep(2500);
      await launchChrome();
      await sleep(3000);
    }
  }
}

async function pageTarget(urlPrefix) {
  for (let i = 0; i < 30; i += 1) {
    const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
    const t = list.find(x => x.type === 'page' && x.url.startsWith(urlPrefix));
    if (t) return t;
    await sleep(500);
  }
  throw new Error(`ไม่พบแท็บ ${urlPrefix}`);
}

async function main() {
  const realPost = process.argv.includes('--real-post');
  const apiKey = readApiKey();
  const api = createApi({ apiKey, channelId: 'main' });
  const outDir = path.join(ROOT, '.tmp', 'extension_e2e', new Date().toISOString().replace(/[:.]/g, '-'));
  fs.mkdirSync(outDir, { recursive: true });
  const report = { steps: [], ok: false };
  const step = (name, detail = '') => { console.log(`[step] ${name} ${detail}`); report.steps.push({ name, detail }); };

  // 1) pick ONE eligible clip so the panel's search filter leaves exactly one
  const { clips } = await pickClips(api, { limit: 1 });
  if (!clips.length) throw new Error('ไม่มีคลิปพร้อมโพสต์ในคิว (ตรวจเวลา/export)');
  const clip = clips[0];
  step('clip', clip.title);

  // 2) Chrome + extension
  if (!(await portUp())) await launchChrome();
  const extId = await loadExtension();
  step('extension loaded', extId);
  await sleep(1500);

  // 3) TikTok tab must be on the upload page
  const tiktok = await pageTarget('https://www.tiktok.com/tiktokstudio');
  const tt = await new Cdp(tiktok.webSocketDebuggerUrl).open();
  if (!/\/tiktokstudio\/upload/.test(tiktok.url)) await tt.call('Page.navigate', { url: UPLOAD_URL });
  await sleep(4000);

  // 4) the side panel, in its own window so the upload tab stays visible
  const b = await browser();
  await b.call('Target.createTarget', { url: `chrome-extension://${extId}/sidepanel.html`, newWindow: true, width: 520, height: 900 });
  b.close();
  const panelTarget = await pageTarget(`chrome-extension://${extId}/sidepanel.html`);
  const panel = await new Cdp(panelTarget.webSocketDebuggerUrl).open();
  await panel.call('Runtime.enable');
  await panel.eval(`new Promise(r => chrome.storage.local.set({omnicutApiKey: ${JSON.stringify(apiKey)}}, r))`);
  await panel.call('Page.reload');
  await sleep(4000);
  step('panel open');

  try {
    // 5) wait for the clip list, filter to the one clip, choose options
    let count = 0;
    for (let i = 0; i < 40 && count < 1; i += 1) {
      count = await panel.eval(`typeof allClips === 'undefined' ? -1 : allClips.length`, false).catch(() => -1);
      if (count < 1) await sleep(1500);
    }
    if (count < 1) throw new Error('แผงข้างโหลดรายการคลิปไม่ได้ (ตรวจ API key/Backend)');
    step('panel clips loaded', String(count));
    const title = clip.title.slice(0, 40);
    await panel.eval(`(() => {
      const set = (id, v) => { const el = document.getElementById(id); el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); };
      set('clipSearchInput', ${JSON.stringify(title)});
      set('batchModeSelect', 'schedule_only');
      set('batchLimitSelect', 'all');
      const cf = document.getElementById('coverFallbackToggle'); if (cf && !cf.checked) cf.click();
      return true;
    })()`, false);
    await sleep(800);
    const filtered = await panel.eval(`document.getElementById('batchCountBadge')?.innerText || ''`, false);
    step('filtered', filtered);

    if (!realPost) {
      // Stub ONLY the final post click; every other worker message is the real thing.
      await panel.eval(`(() => {
        const original = chrome.runtime.sendMessage.bind(chrome.runtime);
        chrome.runtime.sendMessage = (message, cb) => {
          if (message && message.action === 'click-post-only') {
            setTimeout(() => cb && cb({ success: true, clicked: false, outcome: 'scheduled_on_platform', stubbed: true }), 300);
            return;
          }
          return original(message, cb);
        };
        window.__e2eStubbed = true;
      })()`, false);
      step('post click stubbed');
    }

    // 6) press the REAL start button and confirm
    await panel.eval(`document.getElementById('batchStartBtn').click()`, false);
    await sleep(800);
    await panel.eval(`document.getElementById('confirmOkBtn').click()`, false);
    step('batch started');

    // optional fault: Chrome stops the MV3 service worker in the middle of the batch
    const killAt = Number((process.argv.find(a => a.startsWith('--kill-worker-at=')) || '').split('=')[1]) || 0;
    if (killAt) {
      setTimeout(async () => {
        try {
          const sw = await new Cdp((await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json()).webSocketDebuggerUrl).open();
          const { targetInfos } = await sw.call('Target.getTargets');
          const workers = targetInfos.filter(t => t.type === 'service_worker' && t.url.startsWith(`chrome-extension://${extId}/`));
          console.log(`[fault] stopping ${workers.length} extension service worker(s) at t=${killAt}s`);
          await panel.call('ServiceWorker.enable').catch(() => {});
          await panel.call('ServiceWorker.stopAllWorkers').catch(e => console.log('[fault] stopAllWorkers:', e.message));
          for (const w of workers) await sw.call('Target.closeTarget', { targetId: w.targetId }).catch(() => {});
          sw.close();
        } catch (e) { console.log('[fault] failed:', e.message); }
      }, killAt * 1000);
    }

    // 7) wait for the panel's own log to finish
    const t0 = Date.now();
    let log = '';
    while (Date.now() - t0 < 15 * 60 * 1000) {
      await sleep(5000);
      log = await panel.eval(`document.getElementById('batchLogBox')?.innerText || ''`, false).catch(() => '');
      if (/อัปโหลดครบชุด|สรุปผลลัพธ์|ระบบลูปหยุดทำงาน|หยุดลูป/.test(log)) break;
    }
    fs.writeFileSync(path.join(outDir, 'panel_log.txt'), log);
    await tt.call('Page.captureScreenshot', { format: 'png' }).then(r => fs.writeFileSync(path.join(outDir, 'upload_tab.png'), Buffer.from(r.data, 'base64'))).catch(() => {});
    const shot = await panel.call('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, 'panel.png'), Buffer.from(shot.data, 'base64'));
    console.log('---- panel log ----\n' + log.split('\n').slice(-14).join('\n'));
    report.ok = /สำเร็จ:/.test(log) && !/ล้มเหลวที่ขั้น/.test(log);
    report.log_tail = log.split('\n').slice(-14);
  } finally {
    // 8) leave nothing claimed behind
    await panel.eval(`new Promise(r => chrome.runtime.sendMessage({action: 'release-posting-job', park: true}, r))`).catch(() => {});
    panel.close();
    tt.close();
    fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 2));
  }
  console.log(report.ok ? '[E2E PASS] แผงข้างทำงานครบทั้งสาย' : '[E2E FAIL] ดู panel_log.txt');
  console.log(`evidence: ${outDir}`);
  process.exitCode = report.ok ? 0 : 1;
}

main().catch(error => { console.error('[E2E ERROR]', error.message); process.exitCode = 2; })
  .finally(() => setTimeout(() => process.exit(process.exitCode || 0), 300));
