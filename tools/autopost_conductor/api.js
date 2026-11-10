'use strict';
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..');

function readApiKey(env = process.env, envFile = path.join(ROOT, '.env')) {
  if (env.OMNICUT_API_KEY) return env.OMNICUT_API_KEY;
  try {
    const line = fs.readFileSync(envFile, 'utf8').split(/\r?\n/).find(l => /^\s*OMNICUT_API_KEY\s*=/.test(l));
    if (line) return line.slice(line.indexOf('=') + 1).trim().replace(/^["']|["']$/g, '');
  } catch (_) {}
  return '';
}

function createApi({ base = 'http://127.0.0.1:8000', apiKey = '', channelId = 'main', fetchImpl = globalThis.fetch, timeoutMs = 60_000 } = {}) {
  async function call(method, route, body) {
    let res;
    try {
      res = await fetchImpl(base + route, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey, 'X-OmniCut-Channel': channelId },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        signal: AbortSignal.timeout(timeoutMs),   // a hung backend must not hang an unattended run forever
      });
    } catch (error) {
      if (error?.name === 'TimeoutError' || error?.name === 'AbortError') throw new Error(`api_timeout: ${method} ${route} ไม่ตอบใน ${Math.round(timeoutMs / 1000)} วินาที`);
      throw error;
    }
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }
  return { get: route => call('GET', route), post: (route, body) => call('POST', route, body) };
}

module.exports = { readApiKey, createApi, ROOT };
