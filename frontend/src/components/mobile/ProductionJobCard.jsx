import React, { useState } from 'react';

const STAGE_LABELS_TH = {
  tts: 'สร้างเสียงพากย์คู่รัก (TTS)',
  whisper: 'ถอดจังหวะคำพูด (Whisper)',
  compose: 'ประกอบฉากกระดาษแชท',
  checkpoint: 'รอตรวจภาพคลิปแรก',
  render: 'เรนเดอร์วิดีโอ 1080×1920',
  finalize: 'สร้างปกและลงทะเบียนคลิป',
};

const STATUS_META = {
  queued: {
    label: 'อยู่ในคิว',
    pillClass: 'bg-slate-500/20 text-slate-200 border-slate-400/30',
  },
  running: {
    label: 'กำลังผลิต',
    pillClass: 'bg-[#25F4EE]/15 text-[#25F4EE] border-[#25F4EE]/40',
  },
  awaiting_approval: {
    label: 'รออนุมัติคลิปแรก',
    pillClass: 'bg-amber-500/20 text-amber-300 border-amber-400/40',
  },
  paused_quota: {
    label: 'พักรอโควตา TTS',
    pillClass: 'bg-orange-500/20 text-orange-300 border-orange-400/40',
  },
  paused: {
    label: 'หยุดชั่วคราว',
    pillClass: 'bg-slate-500/20 text-slate-300 border-slate-400/30',
  },
  completed: {
    label: 'เสร็จสมบูรณ์',
    pillClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/40',
  },
  failed: {
    label: 'เกิดข้อผิดพลาด',
    pillClass: 'bg-rose-500/20 text-rose-300 border-rose-400/40',
  },
  cancelled: {
    label: 'ยกเลิกแล้ว',
    pillClass: 'bg-slate-600/20 text-slate-400 border-slate-500/30',
  },
};

function estimateEtaText(job) {
  if (!job) return '';
  if (job.status === 'completed') return 'พร้อมโพสต์ครบทั้งชุด';
  if (job.status === 'cancelled') return 'ยกเลิกงานแล้ว';
  if (job.status === 'awaiting_approval') return 'รออนุมัติเพื่อเรนเดอร์ต่อ';
  if (job.status === 'paused_quota') return 'รอคีย์พร้อมใช้งาน';
  if (job.status === 'paused') return 'หยุดชั่วคราว';
  if (job.eta_text) return job.eta_text;

  const total = Math.max(1, Number(job.total_clips || 20));
  const done = Math.min(total, Math.max(0, Number(job.completed_clips || 0)));
  const remaining = Math.max(0, total - done);
  if (remaining === 0) return 'กำลังสรุปผล';
  const estMinutes = Math.max(1, Math.ceil((remaining * 35) / 60));
  return `ประมาณ ${estMinutes} นาที`;
}

export function ProductionJobCard({
  job,
  onCheckpointDecision,
  onResume,
  onPause,
  onCancel,
  onRetryClip,
  onJobUpdated,
}) {
  const [rejectNote, setRejectNote] = useState('');
  const [busyAction, setBusyAction] = useState(null);
  const [actionError, setActionError] = useState(null);

  if (!job) return null;

  const totalClips = Math.max(1, Number(job.total_clips || 20));
  const completedClips = Math.min(totalClips, Math.max(0, Number(job.completed_clips || 0)));
  const progressPct = Math.round((completedClips / totalClips) * 100);
  const stageLabel = STAGE_LABELS_TH[job.current_stage] || job.current_stage || 'เตรียมการผลิต';
  const statusMeta = STATUS_META[job.status] || STATUS_META.queued;
  const etaText = estimateEtaText(job);
  const checkpoint = job.checkpoint || {};
  const failedClips = Array.isArray(job.clips)
    ? job.clips.filter((c) => c && c.status === 'failed')
    : [];

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const msg = data?.detail?.message || data?.detail || 'ไม่สามารถดำเนินการได้ กรุณาลองใหม่';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  }

  async function handleCheckpoint(decision) {
    setBusyAction(decision);
    setActionError(null);
    const payload = {
      decision,
      expected_revision: job.revision,
      note: decision === 'reject' ? rejectNote.trim() : '',
    };
    try {
      let updated;
      if (typeof onCheckpointDecision === 'function') {
        updated = await onCheckpointDecision(job.job_id, payload, job);
      } else {
        updated = await postJson(`/api/couple/jobs/${encodeURIComponent(job.job_id)}/checkpoint`, payload);
      }
      if (updated && typeof onJobUpdated === 'function') {
        onJobUpdated(updated);
      }
    } catch (err) {
      setActionError(err?.message || 'เกิดข้อผิดพลาดในการส่งผลตรวจ');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleResume() {
    setBusyAction('resume');
    setActionError(null);
    try {
      let updated;
      if (typeof onResume === 'function') {
        updated = await onResume(job.job_id, job);
      } else {
        updated = await postJson(`/api/couple/jobs/${encodeURIComponent(job.job_id)}/resume`);
      }
      if (updated && typeof onJobUpdated === 'function') {
        onJobUpdated(updated);
      }
    } catch (err) {
      setActionError(err?.message || 'ไม่สามารถทำต่องานได้');
    } finally {
      setBusyAction(null);
    }
  }

  async function handlePause() {
    setBusyAction('pause');
    setActionError(null);
    try {
      let updated;
      if (typeof onPause === 'function') {
        updated = await onPause(job.job_id, job);
      } else {
        updated = await postJson(`/api/couple/jobs/${encodeURIComponent(job.job_id)}/pause`, { reason: 'user' });
      }
      if (updated && typeof onJobUpdated === 'function') {
        onJobUpdated(updated);
      }
    } catch (err) {
      setActionError(err?.message || 'ไม่สามารถหยุดงานชั่วคราวได้');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCancel() {
    setBusyAction('cancel');
    setActionError(null);
    try {
      let updated;
      if (typeof onCancel === 'function') {
        updated = await onCancel(job.job_id, job);
      } else {
        updated = await postJson(`/api/couple/jobs/${encodeURIComponent(job.job_id)}/cancel`);
      }
      if (updated && typeof onJobUpdated === 'function') {
        onJobUpdated(updated);
      }
    } catch (err) {
      setActionError(err?.message || 'ไม่สามารถยกเลิกงานได้');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRetryClip(clipIdx) {
    setBusyAction(`retry_${clipIdx}`);
    setActionError(null);
    try {
      let updated;
      if (typeof onRetryClip === 'function') {
        updated = await onRetryClip(job.job_id, clipIdx, job);
      } else {
        updated = await postJson(
          `/api/couple/jobs/${encodeURIComponent(job.job_id)}/clips/${encodeURIComponent(clipIdx)}/retry`
        );
      }
      if (updated && typeof onJobUpdated === 'function') {
        onJobUpdated(updated);
      }
    } catch (err) {
      setActionError(err?.message || 'ไม่สามารถสั่งเรนเดอร์คลิปใหม่ได้');
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section
      aria-label={`งานผลิต ${job.product_code}`}
      className="w-full rounded-2xl border border-white/10 bg-slate-900/90 p-4 text-slate-100 shadow-lg"
    >
      {/* Header: Product Code & Status Pill */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-base font-extrabold tracking-tight text-white">
              {job.product_code}
            </span>
            <span className="text-xs text-slate-400">#{job.job_id}</span>
          </div>
          <p className="mt-0.5 text-sm font-medium text-slate-300">{stageLabel}</p>
        </div>

        <span
          className={`inline-flex shrink-0 items-center rounded-full border px-3 py-1 text-xs font-bold ${statusMeta.pillClass}`}
        >
          {statusMeta.label}
        </span>
      </div>

      {/* Progress Bar & Counter */}
      <div className="mt-3">
        <div className="flex items-baseline justify-between text-xs text-slate-300">
          <span className="font-semibold">
            ความคืบหน้า {completedClips} / {totalClips} คลิป ({progressPct}%)
          </span>
          {etaText && <span className="text-slate-400">{etaText}</span>}
        </div>
        <div className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Paused Quota Notice */}
      {job.status === 'paused_quota' && (
        <div
          role="alert"
          className="mt-3 rounded-xl border border-orange-400/40 bg-orange-500/10 p-3 text-sm text-orange-200"
        >
          <p className="font-bold text-orange-300">โควตา TTS เต็มชั่วคราว</p>
          <p className="mt-1 text-xs text-orange-200/90">
            ระบบหยุดพักอัตโนมัติเพื่อรักษาคุณภาพเสียงพากย์ คลิปที่ทำเสร็จแล้วถูกเก็บไว้ครบถ้วน
          </p>
          <div className="mt-3">
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleResume}
              className="min-h-11 w-full rounded-xl bg-[#25F4EE] px-4 py-2.5 text-sm font-bold text-slate-950 transition active:scale-[0.99] disabled:opacity-50"
            >
              ทำต่อทันที
            </button>
          </div>
        </div>
      )}

      {/* Awaiting Approval Checkpoint Gate */}
      {job.status === 'awaiting_approval' && (
        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 p-3">
          <p className="text-sm font-bold text-amber-200">
            ตรวจภาพคลิปแรก ({checkpoint.clip_id || `${String(job.product_code || '').toLowerCase()}_01`})
          </p>
          <p className="mt-0.5 text-xs text-slate-300">
            ตรวจสอบเลย์เอาต์แชทและป้าย CTA ก่อนสั่งเรนเดอร์ครบทั้งชุด
          </p>

          <div className="mt-3 grid grid-cols-2 gap-2.5">
            <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-950/70">
              {checkpoint.chat_snapshot_url ? (
                <img
                  src={checkpoint.chat_snapshot_url}
                  alt="ภาพตัวอย่างฉากแชทคลิปแรก"
                  loading="lazy"
                  className="aspect-[9/16] w-full object-cover"
                />
              ) : (
                <div className="flex aspect-[9/16] items-center justify-center p-2 text-center text-xs text-slate-400">
                  ภาพฉากแชท
                </div>
              )}
              <div className="border-t border-white/10 px-2 py-1 text-center text-xs font-semibold text-slate-300">
                ฉากแชทคู่รัก
              </div>
            </div>

            <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-950/70">
              {checkpoint.cta_snapshot_url ? (
                <img
                  src={checkpoint.cta_snapshot_url}
                  alt="ภาพตัวอย่างฉากป้ายตะกร้า CTA คลิปแรก"
                  loading="lazy"
                  className="aspect-[9/16] w-full object-cover"
                />
              ) : (
                <div className="flex aspect-[9/16] items-center justify-center p-2 text-center text-xs text-slate-400">
                  ภาพฉากป้าย CTA
                </div>
              )}
              <div className="border-t border-white/10 px-2 py-1 text-center text-xs font-semibold text-slate-300">
                ฉากป้ายตะกร้า CTA
              </div>
            </div>
          </div>

          <div className="mt-3">
            <input
              type="text"
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              placeholder="ระบุหมายเหตุหากต้องการตีกลับแก้ไข"
              className="min-h-11 w-full rounded-xl border border-white/15 bg-slate-950/80 px-3 py-2 text-base text-slate-100 placeholder:text-slate-500 focus:border-[#25F4EE] focus:outline-none"
            />
          </div>

          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() => handleCheckpoint('approve')}
              className="min-h-11 flex-1 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] px-4 py-2.5 text-sm font-bold text-white shadow-md transition active:scale-[0.99] disabled:opacity-50"
            >
              อนุมัติและเรนเดอร์ทั้งชุด
            </button>
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() => handleCheckpoint('reject')}
              className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-bold text-slate-200 transition hover:bg-white/10 active:scale-[0.99] disabled:opacity-50"
            >
              ตีกลับแก้ไข
            </button>
          </div>
        </div>
      )}

      {/* Failed Clips List */}
      {failedClips.length > 0 && (
        <div className="mt-3 space-y-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3">
          <p className="text-xs font-bold text-rose-300">
            คลิปที่พบปัญหาระหว่างผลิต ({failedClips.length} คลิป)
          </p>
          {failedClips.map((clip) => (
            <div
              key={clip.idx}
              className="flex items-center justify-between gap-2 rounded-lg bg-slate-950/60 px-3 py-2 text-xs"
            >
              <div className="min-w-0">
                <span className="font-bold text-slate-200">คลิปที่ {clip.idx}</span>
                {clip.error && <p className="truncate text-rose-300">{clip.error}</p>}
              </div>
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={() => handleRetryClip(clip.idx)}
                className="min-h-11 shrink-0 rounded-lg border border-rose-400/40 bg-rose-500/20 px-3 py-2 text-xs font-bold text-rose-200 transition active:scale-[0.99] disabled:opacity-50"
              >
                ลองใหม่คลิปนี้
              </button>
            </div>
          ))}
        </div>
      )}

      {/* General Pause / Resume / Cancel controls */}
      {(job.status === 'running' || job.status === 'queued' || job.status === 'paused') && (
        <div className="mt-3 flex flex-wrap gap-2">
          {job.status === 'paused' ? (
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleResume}
              className="min-h-11 flex-1 rounded-xl bg-[#25F4EE] px-4 py-2.5 text-sm font-bold text-slate-950 transition active:scale-[0.99] disabled:opacity-50"
            >
              ทำต่อทันที
            </button>
          ) : (
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handlePause}
              className="min-h-11 flex-1 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-bold text-slate-200 transition active:scale-[0.99] disabled:opacity-50"
            >
              หยุดชั่วคราว
            </button>
          )}
          <button
            type="button"
            disabled={busyAction !== null}
            onClick={handleCancel}
            className="min-h-11 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm font-bold text-rose-300 transition active:scale-[0.99] disabled:opacity-50"
          >
            ยกเลิกงาน
          </button>
        </div>
      )}

      {actionError && (
        <p role="alert" className="mt-2 text-xs font-semibold text-rose-400">
          {actionError}
        </p>
      )}
    </section>
  );
}

export default ProductionJobCard;
