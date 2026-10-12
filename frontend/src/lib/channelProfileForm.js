import { assertChannelId } from './channelId.js';
import { normalizeHandle } from './channelHandle.js';

export const PROFILE_FIELDS = Object.freeze(['display_name', 'handle', 'watermark_text', 'follow_title', 'avatar_asset_path', 'posting_enabled']);

function fail(code, message, field) {
  const error = new Error(message); error.code = code; error.field = field; throw error;
}

export function profileForm(channel = {}) {
  return Object.fromEntries(PROFILE_FIELDS.map(key => [key, key === 'posting_enabled' ? Boolean(channel[key]) : String(channel[key] || '')]));
}

export function captureProfile(channel, token) {
  assertChannelId(channel.id);
  return Object.freeze({ id: channel.id, revision: channel.revision, status: channel.status,
    baseline: Object.freeze(profileForm(channel)), token });
}

export function profileDirty(snapshot, form) {
  return Boolean(snapshot && PROFILE_FIELDS.some(key => form[key] !== snapshot.baseline[key]));
}

export function assertProfileOwner(snapshot, current, tokenCurrent = true) {
  if (!snapshot || !current || !tokenCurrent || snapshot.id !== current.id || snapshot.revision !== current.revision) {
    fail('channel_profile_stale', 'ช่องหรือข้อมูลช่องเปลี่ยนแล้ว กรุณาโหลดใหม่ก่อนบันทึก');
  }
  if (snapshot.status === 'archived') fail('channel_archived', 'ช่องที่เก็บถาวรเป็นข้อมูลอ่านอย่างเดียว');
}

function normalizedForm(form) {
  const result = profileForm(form);
  result.display_name = result.display_name.trim();
  if (!result.display_name) fail('display_name_required', 'กรุณาตั้งชื่อช่อง', 'display_name');
  if (result.handle.trim()) {
    const handle = normalizeHandle(result.handle);
    if (!handle.ok) fail(handle.code, handle.message, 'handle');
    result.handle = handle.value;
  } else result.handle = '';
  return result;
}

export function buildProfilePatch(snapshot, form, current, tokenCurrent = true) {
  assertProfileOwner(snapshot, current, tokenCurrent);
  const normalized = normalizedForm(form);
  const changed = Object.fromEntries(PROFILE_FIELDS.filter(key => normalized[key] !== snapshot.baseline[key]).map(key => [key, normalized[key]]));
  return Object.keys(changed).length ? { ...changed, expected_revision: snapshot.revision } : null;
}

export function buildDraftPayload(form, registryRevision) {
  assertChannelId(form.id);
  if (!Number.isInteger(registryRevision) || registryRevision < 0) fail('registry_revision_required', 'โหลดทะเบียนช่องก่อนสร้างช่องใหม่');
  const values = normalizedForm(form);
  return { id: form.id, ...values, posting_enabled: false, expected_registry_revision: registryRevision };
}

export function profileFailure(error) {
  const body = error?.response?.data;
  const validation = Array.isArray(body?.detail) ? body.detail : [];
  const detail = validation.length ? validation.map(issue => `${issue.loc?.at(-1) || 'ข้อมูล'}: ${issue.msg || 'ข้อมูลไม่ถูกต้อง'}`).join(' · ')
    : typeof body?.detail === 'string' ? body.detail : null;
  return { message: detail || error?.friendlyMessage || error?.message || 'บันทึกช่องไม่สำเร็จ',
    code: body?.code || error?.code, field: body?.field || validation[0]?.loc?.at(-1) || error?.field };
}
