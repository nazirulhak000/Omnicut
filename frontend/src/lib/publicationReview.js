import { normalizeHandle } from './channelHandle.js';

function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}

export function publicationReviewIdentity(item, job, channelId) {
  if (!item?.posting_job_id || (item.channel_id && item.channel_id !== channelId)) fail('publication_job_missing', 'ไม่พบงานโพสต์เดิมของรายการในช่องนี้');
  if (!job || job.channel_id !== channelId || (job.job_id || job.id) !== item.posting_job_id) fail('publication_job_mismatch', 'งานโพสต์ที่ได้รับไม่ตรงรายการและช่อง กรุณาโหลดคิวใหม่');
  if (job.status !== 'scheduled_on_platform' || job.receipt?.outcome !== 'scheduled_on_platform') fail('publication_not_scheduled', 'งานนี้ไม่มีหลักฐานว่า TikTok รับตั้งเวลาแล้ว');
  const account = normalizeHandle(job.receipt?.source_account);
  const target = normalizeHandle(job.target_handle);
  if (!account.ok || !target.ok || account.value !== target.value) fail('publication_account_mismatch', 'บัญชีในหลักฐานไม่ตรงกับงานเดิม ต้องตรวจการเชื่อมก่อน');
  const videoId = String(job.receipt?.proof?.platform_post_id || '');
  if (!/^[0-9]{8,32}$/.test(videoId)) fail('publication_waiting_linkage', 'หลักฐานรับตั้งเวลายังไม่มีรหัสวิดีโอ ต้องยืนยันการเชื่อมกับงานเดิมก่อน ไม่สามารถเดาจาก Caption หรือเวลาได้');
  if (!Number.isInteger(job.revision) || job.revision < 1) fail('publication_revision_missing', 'งานโพสต์ไม่มี revision ที่ตรวจสอบได้ กรุณาโหลดคิวใหม่');
  return { jobId: item.posting_job_id, account: account.value, videoId, revision: job.revision,
    expectedUrl: `https://www.tiktok.com/${account.value}/video/${videoId}` };
}

export function bangkokPublicationIso(value, now = Date.now()) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(value || '')) fail('publication_timestamp_invalid', 'ระบุวันและเวลาที่เผยแพร่จริงตามเวลาไทย');
  const stamp = `${value.length === 16 ? `${value}:00` : value}+07:00`;
  const milliseconds = Date.parse(stamp);
  if (!Number.isFinite(milliseconds)) fail('publication_timestamp_invalid', 'วันและเวลาเผยแพร่ไม่ถูกต้อง');
  const local = new Date(milliseconds + 7 * 3600000).toISOString().slice(0, 19);
  if (local !== stamp.slice(0, 19)) fail('publication_timestamp_invalid', 'วันและเวลาเผยแพร่ไม่ถูกต้อง');
  if (milliseconds > now + 60000) fail('publication_timestamp_future', 'เวลาเผยแพร่จริงต้องไม่เป็นเวลาในอนาคต');
  return stamp;
}

export function buildPublicationReviewPayload(item, job, channelId, { url, publishedAt, reviewed, idempotencyKey }, now = Date.now()) {
  const identity = publicationReviewIdentity(item, job, channelId);
  let parsed;
  try { parsed = new URL(String(url || '').trim()); }
  catch { fail('publication_url_invalid', 'ใช้ลิงก์วิดีโอ TikTok ที่เผยแพร่แล้ว'); }
  if (parsed.protocol !== 'https:' || !['www.tiktok.com', 'tiktok.com'].includes(parsed.host)
      || parsed.username || parsed.password || parsed.search || parsed.hash
      || parsed.pathname.replace(/\/$/, '') !== `/${identity.account}/video/${identity.videoId}`) {
    fail('publication_url_mismatch', 'ลิงก์ต้องตรงบัญชีและรหัสวิดีโอในหลักฐานของงานเดิม');
  }
  if (reviewed !== true) fail('publication_review_required', 'ยืนยันว่าคุณเปิดลิงก์และเห็นวิดีโอเผยแพร่แล้วก่อนบันทึก');
  if (typeof idempotencyKey !== 'string' || !idempotencyKey || idempotencyKey.length > 200) fail('publication_key_invalid', 'ไม่พบรหัสบันทึกผล กรุณาเปิดหน้าตรวจผลใหม่');
  return { source_account: identity.account, platform_video_id: identity.videoId,
    observed_published_at: bangkokPublicationIso(publishedAt, now), evidence_url: String(url).trim(),
    review_confirmation: 'reviewed_published_video', idempotency_key: idempotencyKey,
    expected_job_revision: identity.revision };
}
