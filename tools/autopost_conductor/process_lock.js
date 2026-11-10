'use strict';
// One conductor per machine: two runs would fight over the same Chrome (port 9333) and the same TikTok tab.
// A lock file holds the owner's pid; a lock whose process is gone is stale and is taken over.
const fs = require('node:fs');
const path = require('node:path');

function pidAlive(pid, kill = process.kill.bind(process)) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try { kill(pid, 0); return true; }
  catch (error) { return error?.code === 'EPERM'; }   // EPERM = exists but not ours
}

// -> { ok: true, release() } or { ok: false, owner: {pid, startedAt} }
function acquireProcessLock(file, { pid = process.pid, alive = pidAlive, now = () => new Date().toISOString() } = {}) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      fs.writeFileSync(file, JSON.stringify({ pid, startedAt: now() }), { flag: 'wx' });
      let released = false;
      return { ok: true, release() { if (released) return; released = true; try { if (JSON.parse(fs.readFileSync(file, 'utf8')).pid === pid) fs.unlinkSync(file); } catch (_) {} } };
    } catch (error) {
      if (error?.code !== 'EEXIST') throw error;
      let owner = null;
      try { owner = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (_) {}
      if (owner && owner.pid !== pid && alive(owner.pid)) return { ok: false, owner };
      try { fs.unlinkSync(file); } catch (_) {}      // stale (dead owner / unreadable): take over and try once more
    }
  }
  return { ok: false, owner: null };
}

module.exports = { acquireProcessLock, pidAlive };
