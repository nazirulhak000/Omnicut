'use strict';
// Loads the real extension service worker (background.js) inside a vm context
// wired to the CDP-backed chrome shim. Same code path as the side panel drives,
// minus the panel, the MV3 worker lifetime limit and the debugger infobar.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const EXT_DIR = path.resolve(__dirname, '..', '..', 'tiktok_autopost_extension');

function loadWorker({ shim, extDir = EXT_DIR, extraGlobals = {} }) {
  const ctx = vm.createContext({
    console, URL, URLSearchParams, setTimeout, clearTimeout, setInterval, clearInterval,
    fetch: globalThis.fetch, Headers, Request, Response, FormData, Blob, Date, Math, JSON, Promise, TextEncoder, TextDecoder, AbortController,
    crypto: globalThis.crypto, structuredClone, performance, queueMicrotask, atob, btoa,
    chrome: shim.chrome, ...extraGlobals,
  });
  ctx.importScripts = (...files) => files.forEach(file =>
    vm.runInContext(fs.readFileSync(path.join(extDir, file), 'utf8'), ctx, { filename: file }));
  vm.runInContext(fs.readFileSync(path.join(extDir, 'background.js'), 'utf8'), ctx, { filename: 'background.js' });
  return {
    ctx,
    // send('upload-file-only') === chrome.runtime.sendMessage({action}) from the side panel.
    async send(action, payload = {}) {
      const reply = await shim.dispatch({ action, ...payload });
      if (reply === undefined) throw new Error(`worker_no_reply: ${action}`);
      return reply;
    },
  };
}

module.exports = { loadWorker, EXT_DIR };
