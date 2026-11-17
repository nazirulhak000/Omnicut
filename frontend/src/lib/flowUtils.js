import api from '../api.js';

/**
 * Utilities for Google Flow (Veo AI) Video Generation.
 */

/**
 * Default fallback schema for Google Flow account pool (5 accounts).
 */
export const DEFAULT_FLOW_ACCOUNTS_FALLBACK = {
  active_account_id: 'acc_1',
  auto_failover: true,
  min_failover_credits: 25,
  total_pool_credits: 4810,
  accounts: [
    { id: 'acc_1', name: 'Google Pro #1', email: 'nazirulhak.000@gmail.com', user_index: 0, status: 'active', credits: 810, plan: 'pro' },
    { id: 'acc_2', name: 'Google Pro #2', email: 'Account 2', user_index: 1, status: 'active', credits: 1000, plan: 'pro' },
    { id: 'acc_3', name: 'Google Pro #3', email: 'Account 3', user_index: 2, status: 'active', credits: 1000, plan: 'pro' },
    { id: 'acc_4', name: 'Google Pro #4', email: 'Account 4', user_index: 3, status: 'active', credits: 1000, plan: 'pro' },
    { id: 'acc_5', name: 'Google Pro #5', email: 'Account 5', user_index: 4, status: 'active', credits: 1000, plan: 'pro' },
  ],
};

/**
 * Fetches the Google Flow multi-account pool status and list of accounts.
 * @returns {Promise<{
 *   active_account_id: string,
 *   auto_failover: boolean,
 *   min_failover_credits: number,
 *   total_pool_credits?: number,
 *   accounts: Array<{
 *     id: string,
 *     name: string,
 *     email: string,
 *     user_index: number,
 *     status: string,
 *     credits: number,
 *     plan: string
 *   }>
 * }>}
 */
export async function getFlowAccounts() {
  try {
    const res = await api.get('/flow/accounts');
    return res.data;
  } catch (err) {
    console.warn('getFlowAccounts API unreachable, using fallback pool:', err?.message || err);
    return DEFAULT_FLOW_ACCOUNTS_FALLBACK;
  }
}

/**
 * Switches the active Google Flow account.
 * @param {string} accountId - The ID of the target account (e.g. 'acc_1').
 * @returns {Promise<object>}
 */
export async function switchFlowAccount(accountId) {
  const res = await api.post('/flow/accounts/switch', { account_id: accountId });
  return res.data;
}

/**
 * Updates metadata or label for a specific account.
 * @param {string} accountId - The target account ID.
 * @param {object} data - Object containing updated properties (name, email, plan, status, etc.).
 * @returns {Promise<object>}
 */
export async function updateFlowAccount(accountId, data = {}) {
  const payload = { account_id: accountId, ...(data || {}) };
  const res = await api.post('/flow/accounts/update', payload);
  return res.data;
}

/**
 * Toggles auto-failover on or off for the Google Flow pool.
 * @param {boolean} enabled - True to enable, false to disable.
 * @returns {Promise<object>}
 */
export async function toggleAutoFailover(enabled) {
  const res = await api.post('/flow/accounts/auto-failover', { enabled: Boolean(enabled) });
  return res.data;
}

/**
 * Triggers Chrome CDP to open 'Account details' -> 'Switch account' modal,
 * allowing user to sign in to additional Google accounts.
 * @returns {Promise<object>}
 */
export async function openFlowLoginChrome() {
  const res = await api.post('/flow/accounts/open-login');
  return res.data;
}

/**
 * Fetches the bundled 5 script beats for Google Flow generation for a given angle.
 * @param {string} productId - Product UUID
 * @param {string} [angleId] - Angle ID
 * @returns {Promise<{
 *   product_id: string,
 *   angle_id: string,
 *   shots: Array<{
 *     beat_index: number,
 *     role: string,
 *     role_label?: string,
 *     text: string,
 *     camera_direction: string,
 *     technique: string,
 *     duration: number,
 *     prompt?: string,
 *     reference_image?: string
 *   }>
 * }>}
 */
export async function getAngleShotsFlow(productId, angleId) {
  if (!productId) return null;
  const endpoint = angleId
    ? `/flow/product/${encodeURIComponent(productId)}/angles/${encodeURIComponent(angleId)}/shots-flow`
    : `/flow/product/${encodeURIComponent(productId)}/shots-flow`;
  const res = await api.get(endpoint);
  return res.data;
}

/**
 * Maps a human or shot-list camera direction into a supported Flow camera technique.
 * @param {string} direction - The camera direction string (Thai or English).
 * @returns {'orbit' | 'macro' | 'dolly_in' | 'reveal' | 'floating'}
 */
export function mapCameraTechnique(direction = '') {
  if (!direction) return 'orbit';
  const dir = direction.toLowerCase();
  if (dir.includes('orbit') || dir.includes('หมุน') || dir.includes('360')) return 'orbit';
  if (dir.includes('macro') || dir.includes('close') || dir.includes('โคลส') || dir.includes('detail') || dir.includes('ดีเทล')) return 'macro';
  if (dir.includes('dolly') || dir.includes('ดัน') || dir.includes('เข้าหา') || dir.includes('zoom in')) return 'dolly_in';
  if (dir.includes('reveal') || dir.includes('เสย') || dir.includes('มุมต่ำ') || dir.includes('low angle')) return 'reveal';
  if (dir.includes('float') || dir.includes('ลอย') || dir.includes('slow') || dir.includes('สโลว์')) return 'floating';
  return 'orbit';
}

/**
 * Checks whether a given beat has an AI Flow clip available or generating.
 * @param {object} beat - The shot beat object.
 * @param {Array} jobsList - List of flow jobs from getFlowJobs.
 * @returns {{ status: 'ready' | 'generating', path?: string, job: object } | null}
 */
export function findFlowClipForBeat(beat, jobsList = []) {
  if (!jobsList || jobsList.length === 0 || !beat) return null;
  const shotNum = (beat.beat_index !== undefined ? beat.beat_index : 0) + 1;
  const beatIndex = beat.beat_index;

  // 1. Search completed jobs first
  for (const job of jobsList) {
    if (job.status !== 'completed') continue;

    // A. Check scenes with matching shot_index or shot_label or single scene job for beat 0
    const hasMatchingScene =
      job.scenes?.some(
        (s) =>
          s.shot_index === beatIndex ||
          s.shot_label === `shot_${shotNum}` ||
          (typeof s.shot_label === 'string' && s.shot_label.startsWith(`shot_${shotNum}_`)) ||
          s.shot_label === `scene-0${shotNum}` ||
          (beatIndex === 0 && (!s.shot_label || s.shot_label === 'scene-02' || s.shot_label === 'scene-01'))
      ) || (beatIndex === 0 && (!job.scenes || job.scenes.length <= 1));

    if (hasMatchingScene) {
      const rawIngested = job.ingested_files?.[0];
      const ingested = typeof rawIngested === 'object' && rawIngested !== null
        ? (rawIngested.path || rawIngested.relative_path || rawIngested.filename)
        : rawIngested;
      const resultPath = job.results?.[0]?.path || job.results?.[0]?.file_path;
      if (ingested || resultPath) {
        return { status: 'ready', path: ingested || resultPath, job };
      }
    }

    // B. Check ingested_files filenames for shot pattern
    for (const f of job.ingested_files || []) {
      const p = typeof f === 'object' && f !== null ? (f.path || f.filename || '') : String(f || '');
      if (p.includes(`shot_${shotNum}_`) || p.includes(`shot_${shotNum}.`) || (beatIndex === 0 && p.includes('scene-02'))) {
        return { status: 'ready', path: p, job };
      }
    }
  }

  // 2. Search running or queued jobs
  for (const job of jobsList) {
    if (job.status === 'running' || job.status === 'queued' || job.status === 'processing') {
      const hasMatchingScene = job.scenes?.some(
        (s) => s.shot_index === beatIndex ||
               s.shot_label === `shot_${shotNum}` ||
               (typeof s.shot_label === 'string' && s.shot_label.startsWith(`shot_${shotNum}_`))
      );
      if (hasMatchingScene) {
        return { status: 'generating', job };
      }
    }
  }

  return null;
}
