'use strict';
// Minimal `chrome.*` replacement backed by raw Chrome DevTools Protocol, so the
// verified extension worker (tiktok_autopost_extension/background.js) can run
// headless in Node against a real Chrome started with --remote-debugging-port.
// Only the API surface background.js actually uses is implemented.
const fs = require('node:fs');
const path = require('node:path');

function matchPatternToRegex(pattern) {
  if (pattern === '<all_urls>') return /^https?:\/\//;
  const escaped = String(pattern).replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*');
  return new RegExp('^' + escaped + '$');
}

function urlMatches(url, patterns) {
  if (!patterns) return true;
  return [].concat(patterns).some(p => matchPatternToRegex(p).test(url || ''));
}

function createStorage({ file, secrets = {} }) {
  let data = {};
  try { data = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (_) {}
  const clone = v => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));
  const persist = () => {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const tmp = file + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(data));
    fs.renameSync(tmp, file);
  };
  const finish = (value, cb) => (typeof cb === 'function' ? (cb(value), undefined) : Promise.resolve(value));
  return {
    get(keys, cb) {
      const all = { ...data, ...secrets };
      let out = all;
      if (typeof keys === 'string') out = { [keys]: all[keys] };
      else if (Array.isArray(keys)) out = Object.fromEntries(keys.filter(k => k in all).map(k => [k, all[k]]));
      return finish(clone(out), cb);
    },
    set(values, cb) {
      for (const [k, v] of Object.entries(values || {})) if (!(k in secrets)) data[k] = clone(v);
      persist();
      return finish(undefined, cb);
    },
  };
}

function createChromeShim({ port, storageFile, secrets = {}, WebSocketImpl = globalThis.WebSocket, fetchImpl = globalThis.fetch }) {
  const base = `http://127.0.0.1:${port}`;
  const idByTarget = new Map();
  const targetById = new Map();
  let nextTabId = 1;
  const sessions = new Map();
  const detachListeners = [];
  const messageListeners = [];

  const tabFor = (target, active = false) => {
    let id = idByTarget.get(target.id);
    if (!id) { id = nextTabId++; idByTarget.set(target.id, id); targetById.set(id, target.id); }
    return { id, url: target.url, title: target.title, windowId: 1, active, status: 'complete' };
  };
  async function listTargets() {
    const res = await fetchImpl(`${base}/json/list`);
    return (await res.json()).filter(t => t.type === 'page');
  }
  async function targetOf(tabId) {
    const targetId = targetById.get(tabId);
    const target = (await listTargets()).find(t => t.id === targetId);
    if (!target) throw new Error(`No tab with id: ${tabId}.`);
    return target;
  }

  function openSession(target) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocketImpl(target.webSocketDebuggerUrl);
      const session = { ws, pending: new Map(), nextId: 1, closing: false };
      ws.addEventListener('open', () => resolve(session));
      ws.addEventListener('error', () => reject(new Error('Cannot attach to the target tab')));
      ws.addEventListener('message', event => {
        const msg = JSON.parse(typeof event.data === 'string' ? event.data : String(event.data));
        const waiter = msg.id && session.pending.get(msg.id);
        if (!waiter) return;
        session.pending.delete(msg.id);
        if (msg.error) waiter.reject(new Error(msg.error.message || 'CDP error'));
        else waiter.resolve(msg.result || {});
      });
      session.onClose = () => {};
      ws.addEventListener('close', () => {
        for (const waiter of session.pending.values()) waiter.reject(new Error('Debugger detached'));
        session.pending.clear();
        session.onClose();
      });
    });
  }
  const sendOn = (session, method, params) => new Promise((resolve, reject) => {
    const id = session.nextId++;
    session.pending.set(id, { resolve, reject });
    session.ws.send(JSON.stringify({ id, method, params: params || {} }));
  });
  async function withTarget(tabId, fn) {
    if (sessions.has(tabId)) return fn((m, p) => sendOn(sessions.get(tabId), m, p));
    const session = await openSession(await targetOf(tabId));
    try { return await fn((m, p) => sendOn(session, m, p)); } finally { session.closing = true; session.ws.close(); }
  }

  // A half-filled upload form makes Chrome raise a native "Leave site?"
  // (beforeunload) prompt that blocks Page.navigate until someone answers.
  // In a real browser a person clicks it; the unattended host accepts it.
  async function navigate(tabId, url) {
    const session = await openSession(await targetOf(tabId));
    try {
      session.ws.addEventListener('message', event => {
        let msg;
        try { msg = JSON.parse(typeof event.data === 'string' ? event.data : String(event.data)); } catch (_) { return; }
        if (msg.method === 'Page.javascriptDialogOpening' && msg.params?.type === 'beforeunload') {
          sendOn(session, 'Page.handleJavaScriptDialog', { accept: true }).catch(() => {});
        }
      });
      await sendOn(session, 'Page.enable');
      await sendOn(session, 'Page.navigate', { url });
      await new Promise(resolve => setTimeout(resolve, 1200));
    } finally {
      session.closing = true;
      session.ws.close();
    }
  }

  const tabs = {
    async query(info = {}) {
      const targets = await listTargets();
      let list = targets.map((t, i) => tabFor(t, i === 0));
      if (info.url) list = list.filter(t => urlMatches(t.url, info.url));
      if (info.active) list = list.filter(t => t.active);
      return list;
    },
    async get(tabId) { return tabFor(await targetOf(tabId)); },
    async update(tabId, props = {}) {
      const target = await targetOf(tabId);
      if (props.url) await navigate(tabId, props.url);
      if (props.active) await fetchImpl(`${base}/json/activate/${target.id}`);
      return { ...tabFor(target, !!props.active), url: props.url || target.url };
    },
    async create({ url = 'about:blank' } = {}) {
      const res = await fetchImpl(`${base}/json/new?${url}`, { method: 'PUT' });
      return tabFor(await res.json(), true);
    },
    async remove(tabId) {
      const target = await targetOf(tabId);
      await fetchImpl(`${base}/json/close/${target.id}`);
    },
    async sendMessage() {},
  };

  const debuggerApi = {
    async attach({ tabId }) {
      if (sessions.has(tabId)) throw new Error(`Another debugger is already attached to the tab with id: ${tabId}.`);
      const session = await openSession(await targetOf(tabId));
      session.onClose = () => {
        if (sessions.get(tabId) !== session) return;
        sessions.delete(tabId);
        if (!session.closing) detachListeners.forEach(fn => fn({ tabId }, 'target_closed'));
      };
      sessions.set(tabId, session);
    },
    async detach({ tabId }) {
      const session = sessions.get(tabId);
      if (!session) throw new Error(`Debugger is not attached to the tab with id: ${tabId}.`);
      session.closing = true;
      sessions.delete(tabId);
      session.ws.close();
    },
    sendCommand({ tabId }, method, params) {
      const session = sessions.get(tabId);
      if (!session) return Promise.reject(new Error(`Debugger is not attached to the tab with id: ${tabId}.`));
      return sendOn(session, method, params);
    },
    onDetach: { addListener: fn => detachListeners.push(fn) },
  };

  const runtime = {
    lastError: undefined,
    onMessage: { addListener: fn => messageListeners.push(fn) },
    onConnect: { addListener() {} },
    getManifest: () => ({ version: 'conductor-host' }),
  };

  // Delivers a message exactly like chrome.runtime.sendMessage from the side panel.
  function dispatch(message) {
    return new Promise(resolve => {
      let answered = false;
      const respond = value => { if (!answered) { answered = true; resolve(value); } };
      let async = false;
      for (const listener of messageListeners) {
        if (listener(message, {}, respond) === true) async = true;
      }
      if (!async) respond(undefined);
    });
  }

  return {
    chrome: {
      tabs, debugger: debuggerApi, runtime,
      windows: { async update() {} },
      sidePanel: { async setPanelBehavior() {} },
      storage: { local: createStorage({ file: storageFile, secrets }) },
    },
    dispatch,
    async screenshot(tabId, file) {
      const { data } = await withTarget(tabId, send => send('Page.captureScreenshot', { format: 'png' }));
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, Buffer.from(data, 'base64'));
      return file;
    },
    async evaluate(tabId, expression) {
      const out = await withTarget(tabId, send => send('Runtime.evaluate', { expression, returnByValue: true }));
      return out.result?.value;
    },
  };
}

module.exports = { createChromeShim, createStorage, matchPatternToRegex, urlMatches };
