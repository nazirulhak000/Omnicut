import test from 'node:test';
import assert from 'node:assert/strict';
import { publicationReviewIdentity, bangkokPublicationIso, buildPublicationReviewPayload } from './publicationReview.js';

const item = { channel_id: 'main', posting_job_id: 'job-1' };
const job = { id: 'job-1', channel_id: 'main', status: 'scheduled_on_platform', revision: 4, target_handle: '@mainuser',
  receipt: { outcome: 'scheduled_on_platform', source_account: '@mainuser', proof: { platform_post_id: '123456789' } } };
const form = { url: 'https://www.tiktok.com/@mainuser/video/123456789', publishedAt: '2026-10-11T09:30', reviewed: true, idempotencyKey: 'review-1' };
const now = Date.parse('2026-10-11T12:00:00+07:00');

test('review freezes exact account/video/job revision and explicit attestation', () => {
  const payload = buildPublicationReviewPayload(item, job, 'main', form, now);
  assert.equal(payload.review_confirmation, 'reviewed_published_video');
  assert.equal(payload.observed_published_at, '2026-10-11T09:30:00+07:00');
  assert.equal(payload.expected_job_revision, 4);
  assert.equal(payload.platform_video_id, '123456789');
  assert.equal(job.status, 'scheduled_on_platform');
  assert.ok(!('published' in payload));
});
test('secondary channel uses its own frozen identity without main fallback', () => {
  const secondItem = { ...item, channel_id: 'second' };
  const secondJob = { ...job, channel_id: 'second', target_handle: '@seconduser', receipt: { ...job.receipt, source_account: '@seconduser' } };
  const payload = buildPublicationReviewPayload(secondItem, secondJob, 'second', { ...form, url: 'https://www.tiktok.com/@seconduser/video/123456789' }, now);
  assert.equal(payload.source_account, '@seconduser');
});

for (const [name, value, code] of [
  ['foreign channel', { ...job, channel_id: 'second' }, 'publication_job_mismatch'],
  ['foreign job', { ...job, id: 'other' }, 'publication_job_mismatch'],
  ['wrong phase', { ...job, status: 'publishing' }, 'publication_not_scheduled'],
  ['missing frozen ID', { ...job, receipt: { ...job.receipt, proof: {} } }, 'publication_waiting_linkage'],
  ['wrong frozen account', { ...job, receipt: { ...job.receipt, source_account: '@seconduser' } }, 'publication_account_mismatch'],
]) test(name, () => assert.throws(() => publicationReviewIdentity(item, value, 'main'), error => error.code === code));

for (const url of ['https://www.tiktok.com/@seconduser/video/123456789', 'https://www.tiktok.com/@mainuser/video/987654321',
  'https://evil.example/@mainuser/video/123456789', 'https://www.tiktok.com/@mainuser/video/123456789?x=1',
  'https://www.tiktok.com/@mainuser/video/123456789#x', 'https://mainuser@www.tiktok.com/@mainuser/video/123456789']) {
  test(`reject unrelated URL ${url}`, () => assert.throws(() => buildPublicationReviewPayload(item, job, 'main', { ...form, url }, now), error => error.code === 'publication_url_mismatch'));
}
test('review confirmation must be an explicit user action', () => assert.throws(() => buildPublicationReviewPayload(item, job, 'main', { ...form, reviewed: false }, now), error => error.code === 'publication_review_required'));
test('Bangkok time is independent of the browser timezone', () => assert.equal(bangkokPublicationIso('2026-10-11T09:30', now), '2026-10-11T09:30:00+07:00'));
for (const value of ['2026-02-30T09:00', '2026-10-12T09:00', '', 'invalid']) {
  test(`reject invalid/future published time ${value}`, () => assert.throws(() => bangkokPublicationIso(value, now)));
}
