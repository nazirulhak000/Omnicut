import React, { useEffect, useId, useRef, useState } from 'react';
import { Modal } from './ui';
import { getPostingJobForPublication, getPublicationObservations, recordPublicationObservation } from '../api';
import { captureChannel, isCurrentChannel } from '../lib/channelRuntime.js';
import { publicationReviewIdentity, buildPublicationReviewPayload } from '../lib/publicationReview.js';

export default function PublicationReviewModal({ item, channelId, onClose, onRecorded }) {
  const inputId = useId();
  const generation = useRef(0);
  const submission = useRef(null);
  const token = useRef(null);
  const [job, setJob] = useState(null);
  const [identity, setIdentity] = useState(null);
  const [url, setUrl] = useState('');
  const [publishedAt, setPublishedAt] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [recorded, setRecorded] = useState(false);
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    const requestGeneration = ++generation.current;
    const controller = new AbortController();
    token.current = captureChannel();
    submission.current = null;
    setJob(null); setIdentity(null); setUrl(''); setPublishedAt(''); setReviewed(false);
    setLoading(true); setSaving(false); setError(''); setRecorded(false); setLocked(false);
    const current = () => generation.current === requestGeneration && isCurrentChannel(token.current);
    if (token.current.channel_id !== channelId || !item?.posting_job_id) {
      setError('ไม่พบงานโพสต์เดิมในช่องที่เลือก กรุณาโหลดคิวใหม่');
      setLoading(false);
    } else {
      const options = { signal: controller.signal, channelToken: token.current };
      Promise.all([getPostingJobForPublication(item.posting_job_id, options), getPublicationObservations(item.posting_job_id, options)])
        .then(([response, observations]) => {
          if (!current()) return;
          const loaded = response.job;
          const binding = publicationReviewIdentity(item, loaded, channelId);
          setJob(loaded); setIdentity(binding); setUrl(binding.expectedUrl);
          setRecorded(loaded.publication_status === 'published' || observations.items?.some(event => event.status === 'verified' && event.effects_applied));
        })
        .catch(failure => { if (current() && failure.code !== 'ERR_CANCELED') setError(failure.response?.data?.detail || failure.message || 'โหลดหลักฐานงานเดิมไม่สำเร็จ'); })
        .finally(() => { if (current()) setLoading(false); });
    }
    return () => { generation.current += 1; controller.abort(); };
  }, [item?.posting_job_id, item?.channel_id, channelId]);

  const submit = async event => {
    event.preventDefault();
    if (saving || !job || !identity || recorded) return;
    const requestGeneration = generation.current;
    const requestToken = token.current;
    const current = () => generation.current === requestGeneration && isCurrentChannel(requestToken);
    if (!current() || requestToken.channel_id !== channelId) return;
    try {
      if (!submission.current) {
        const key = `publication-review:${crypto.randomUUID()}`;
        submission.current = buildPublicationReviewPayload(item, job, channelId, { url, publishedAt, reviewed, idempotencyKey: key });
      }
      setSaving(true); setLocked(true); setError('');
      const response = await recordPublicationObservation(identity.jobId, submission.current, { channelToken: requestToken });
      if (!current()) return;
      if (!response.observation?.effects_applied) {
        setError('หลักฐานยังเชื่อมกับงานเดิมไม่ครบ จึงยังไม่เปลี่ยนเป็นโพสต์แล้ว');
        return;
      }
      setRecorded(true);
      await onRecorded?.(response);
    } catch (failure) {
      if (current()) setError(failure.response?.data?.detail || failure.message || 'ยังบันทึกผลไม่ครบ กรุณาลองบันทึกผลเดิมอีกครั้ง');
    } finally {
      if (current()) setSaving(false);
    }
  };

  const close = () => { if (!saving) onClose?.(); };
  const inputClass = 'min-h-11 w-full rounded-lg border border-white/15 bg-black/30 px-3 py-2 text-sm text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:opacity-60';
  return (
    <Modal isOpen={Boolean(item)} onClose={close} title="ตรวจการเผยแพร่จริง" subtitle="บันทึกผลของงานตั้งเวลาเดิม หลังเปิดดูวิดีโอที่เผยแพร่บน TikTok" maxWidth="max-w-lg" showCloseButton={!saving}>
      {loading ? <p role="status" className="text-sm text-slate-300">กำลังโหลดหลักฐานงานเดิม</p> : (
        <form onSubmit={submit} className="space-y-4" aria-busy={saving}>
          {identity && <div className="space-y-1 text-sm text-slate-300"><p>บัญชี <strong className="text-white">{identity.account}</strong></p><p className="break-all">รหัสวิดีโอ <span className="text-white">{identity.videoId}</span></p></div>}
          {error && <p role="alert" className="rounded-lg border border-amber-400/25 bg-amber-500/10 p-3 text-sm text-amber-100">{error}</p>}
          {recorded ? <p role="status" className="text-sm text-emerald-200">บันทึกการเผยแพร่จริงครบแล้ว</p> : identity && <>
            <div className="space-y-2"><label htmlFor={`${inputId}-url`} className="block text-sm text-slate-200">ลิงก์วิดีโอที่เผยแพร่แล้ว</label>
              <input id={`${inputId}-url`} type="url" value={url} onChange={event => setUrl(event.target.value)} disabled={locked || saving} required className={inputClass} />
              <a href={identity.expectedUrl} target="_blank" rel="noopener noreferrer" className="inline-block text-sm text-cyan-200 underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">เปิดวิดีโอบน TikTok เพื่อตรวจ</a>
            </div>
            <div className="space-y-2"><label htmlFor={`${inputId}-time`} className="block text-sm text-slate-200">วันและเวลาที่เผยแพร่จริง (เวลาไทย UTC+7)</label>
              <input id={`${inputId}-time`} type="datetime-local" value={publishedAt} onChange={event => setPublishedAt(event.target.value)} disabled={locked || saving} required className={inputClass} />
              <p className="text-xs text-slate-400">ใช้เวลาเผยแพร่ที่ตรวจเห็นบน TikTok ไม่ใช่เวลาที่วางแผนไว้ในคิว</p>
            </div>
            <label className="flex items-start gap-3 text-sm text-slate-200"><input type="checkbox" checked={reviewed} onChange={event => setReviewed(event.target.checked)} disabled={locked || saving} className="mt-1 shrink-0 accent-cyan-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400" />
              <span>ฉันเปิดลิงก์แล้ว เห็นวิดีโอเผยแพร่จริง และตรวจว่าบัญชีตรงกับงานเดิม</span>
            </label>
            <p className="text-xs text-slate-400">เป็นการบันทึกผลจากการตรวจของคุณ ระบบจะไม่กดโพสต์หรือเริ่มงานใหม่</p>
            {locked && error && <p className="text-xs text-amber-200">ลองบันทึกหลักฐานเดิมซ้ำเพื่อซ่อมผลที่ค้าง โดยไม่ส่งวิดีโอใหม่</p>}
          </>}
          <div className="flex flex-wrap justify-end gap-2 pt-1">
            <button type="button" onClick={close} disabled={saving} className="min-h-11 rounded-lg border border-white/15 px-3 py-2 text-sm text-slate-200 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">ปิดหน้าต่าง</button>
            {!recorded && identity && <button type="submit" disabled={saving || !reviewed || !publishedAt} className="min-h-11 rounded-lg bg-cyan-400 px-3 py-2 text-sm font-semibold text-cyan-950 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white">{saving ? 'กำลังบันทึกผล' : locked ? 'ซ่อมผลจากหลักฐานเดิม' : 'บันทึกการเผยแพร่จริง'}</button>}
          </div>
        </form>
      )}
    </Modal>
  );
}
