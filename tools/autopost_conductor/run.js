#!/usr/bin/env node
'use strict';
// Unattended TikTok auto-post runner.
//   node tools/autopost_conductor/run.js --channel main --limit 5 --dry-run
//   node tools/autopost_conductor/run.js --health
// Exit codes: 0 ok · 1 some clips failed · 2 aborted (needs a human) · 3 login/browser problem
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { createChromeShim } = require('./chrome_shim');
const { loadWorker } = require('./host');
const { createApi, readApiKey, ROOT } = require('./api');
const { pickClips, runBatch } = require('./conductor');

const UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload';
const CHROME_EXE = process.env.OMNICUT_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PROFILE_DIR = path.join(ROOT, 'tools', 'tiktok_browser_profile');

function parseArgs(argv) {
  const args = { channel: 'main', limit: 10, port: 9333, dryRun: false, health: false, noLaunch: false, queueId: null, allowPriceCaption: false };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--dry-run') args.dryRun = true;
    else if (a === '--health') args.health = true;
    else if (a === '--no-launch') args.noLaunch = true;
    else if (a === '--allow-price-caption') args.allowPriceCaption = true;
    else if (a === '--channel') args.channel = argv[++i];
    else if (a === '--limit') args.limit = Number(argv[++i]);
    else if (a === '--port') args.port = Number(argv[++i]);
    else if (a === '--queue-id') args.queueId = argv[++i];
    else throw new Error(`unknown argument: ${a}`);
  }
  if (!Number.isInteger(args.limit) || args.limit < 1) throw new Error('--limit ต้องเป็นจำนวนเต็ม >= 1');
  return args;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function portUp(port) {
  try { return (await fetch(`http://127.0.0.1:${port}/json/version`)).ok; } catch (_) { return false; }
}

async function ensureChrome({ port, noLaunch }) {
  if (await portUp(port)) return 'attached';
  if (noLaunch) throw Object.assign(new Error(`ไม่พบ Chrome ที่พอร์ต ${port}`), { exitCode: 3 });
  const child = spawn(CHROME_EXE, [
    `--remote-debugging-port=${port}`, `--user-data-dir=${PROFILE_DIR}`,
    '--no-first-run', '--no-default-browser-check', '--lang=th-TH', '--window-size=1280,1000',
    '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
    UPLOAD_URL,
  ], { detached: true, stdio: 'ignore' });
  child.unref();
  for (let i = 0; i < 40; i += 1) {
    if (await portUp(port)) return 'launched';
    await sleep(500);
  }
  throw Object.assign(new Error('เปิด Chrome พร้อมพอร์ต debug ไม่สำเร็จ — ปิด Chrome ที่ใช้โปรไฟล์ tools/tiktok_browser_profile ก่อน แล้วรันใหม่'), { exitCode: 3 });
}

// Prevents Windows sleep while the run is alive (child dies with us).
function keepAwake() {
  if (process.platform !== 'win32') return () => {};
  const script = `$sig='[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);';` +
    `Add-Type -MemberDefinition $sig -Name K -Namespace W;` +
    `while (Get-Process -Id ${process.pid} -ErrorAction SilentlyContinue) { [W.K]::SetThreadExecutionState(0x80000001) | Out-Null; Start-Sleep 30 }`;
  const child = spawn('powershell', ['-NoProfile', '-WindowStyle', 'Hidden', '-Command', script], { stdio: 'ignore' });
  return () => { try { child.kill(); } catch (_) {} };
}

async function findStudioTab(shim) {
  const tabs = await shim.chrome.tabs.query({ url: '*://www.tiktok.com/*' });
  return tabs.find(t => /\/tiktokstudio/.test(t.url)) || tabs[0] || null;
}

async function checkStudioReady(shim, port) {
  let tab = await findStudioTab(shim);
  if (!tab) tab = await shim.chrome.tabs.create({ url: UPLOAD_URL });
  else if (!/\/tiktokstudio\/upload/.test(tab.url)) tab = await shim.chrome.tabs.update(tab.id, { url: UPLOAD_URL, active: true });
  const checks = { login: false, file_input: false, url: '' };
  for (let i = 0; i < 30; i += 1) {
    await sleep(1000);
    const now = await shim.chrome.tabs.get(tab.id);
    checks.url = now.url;
    if (/login|passport/.test(now.url)) break;
    checks.file_input = Boolean(await shim.evaluate(tab.id, `!!document.querySelector('input[type="file"]')`).catch(() => false));
    if (/\/tiktokstudio\/upload/.test(now.url) && checks.file_input) { checks.login = true; break; }
  }
  return { tab, checks };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const runId = new Date().toISOString().replace(/[:.]/g, '-');
  const runDir = path.join(ROOT, '.tmp', 'autopost_runs', runId);
  fs.mkdirSync(runDir, { recursive: true });
  const logFile = path.join(runDir, 'run.jsonl');
  const log = (level, message) => {
    console.log(`[${level}] ${message}`);
    fs.appendFileSync(logFile, JSON.stringify({ t: new Date().toISOString(), level, message }) + '\n');
  };
  const alert = message => {
    fs.writeFileSync(path.join(runDir, 'ALERT.txt'), message);
    fs.writeFileSync(path.join(ROOT, '.tmp', 'autopost_ALERT.txt'), `${runId}\n${message}\n`);
    log('error', `ต้องมีคนช่วย: ${message}`);
  };

  const apiKey = readApiKey();
  const api = createApi({ apiKey, channelId: args.channel });
  const caps = await api.get('/api/tiktok-autopost/capabilities').catch(() => ({ ok: false }));
  if (!caps.ok) { alert('Backend (127.0.0.1:8000) ไม่ตอบหรือ API key ผิด'); process.exit(3); }

  const stopAwake = keepAwake();
  try {
    log('info', `Chrome: ${await ensureChrome(args)}`);
    const shim = createChromeShim({
      port: args.port, storageFile: path.join(ROOT, '.tmp', 'autopost_state.json'),
      secrets: { omnicutApiKey: apiKey },
    });
    const { tab, checks } = await checkStudioReady(shim, args.port);
    fs.writeFileSync(path.join(ROOT, '.tmp', 'autopost_health.json'),
      JSON.stringify({ ok: checks.login, checked_at: new Date().toISOString(), checks }, null, 2));
    if (!checks.login) {
      alert(`TikTok Studio ยังไม่พร้อม (url=${checks.url}) — login มือในหน้าต่าง Chrome นี้หนึ่งครั้ง แล้วรันใหม่`);
      process.exit(3);
    }
    log('info', 'TikTok Studio พร้อม (login แล้ว, พบ input อัปโหลดไฟล์)');
    if (args.health) { log('info', 'health ok'); return; }

    const worker = loadWorker({ shim });
    const { clips, skipped } = await pickClips(api, args);
    skipped.forEach(s => log('warn', `ข้าม ${s.title}: ${s.reason}`));
    if (!clips.length) { log('info', 'ไม่มีคลิปพร้อมโพสต์ในคิว'); return; }

    let stopRequested = false;
    process.on('SIGINT', () => { stopRequested = true; log('warn', 'รับสัญญาณหยุด — จบคลิปปัจจุบันแล้วหยุด'); });
    const tabId = async () => (await findStudioTab(shim))?.id ?? tab.id;
    const deps = {
      worker, api, log, sleep,
      shot: async label => shim.screenshot(await tabId(), path.join(runDir, `${label}.png`)).catch(e => log('warn', `screenshot: ${e.message}`)),
      dumpDom: async label => {
        const html = await shim.evaluate(await tabId(), 'document.documentElement.outerHTML').catch(() => '');
        if (html) {
          const dir = path.join(ROOT, '.tmp', 'autopost_dom');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, `${label}.html`), html);
        }
      },
    };
    const summary = await runBatch(deps, { clips, dryRun: args.dryRun, channelId: args.channel, shouldStop: () => stopRequested });
    fs.writeFileSync(path.join(runDir, 'summary.json'), JSON.stringify(summary, null, 2));
    log('info', `สรุป: โพสต์ ${summary.posted} · ตั้งเวลา ${summary.scheduled} · dry-run ${summary.dry_run_ok} · ข้าม ${summary.skipped} · ล้ม ${summary.failed} · ไม่ชัด ${summary.unknown}`);
    if (summary.aborted) { alert(summary.aborted); process.exitCode = 2; }
    else if (summary.failed || summary.unknown) process.exitCode = 1;
  } catch (error) {
    alert(error.message);
    process.exitCode = error.exitCode || 2;
  } finally {
    stopAwake();
  }
}

if (require.main === module) main();

module.exports = { parseArgs };
