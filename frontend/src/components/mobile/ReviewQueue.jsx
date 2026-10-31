import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ReviewSheet } from './ReviewSheet';

const STATUS_FILTERS = [
  { key: 'pending', label: 'รอตรวจ' },
  { key: 'passed', label: 'ผ่านแล้ว' },
  { key: 'rejected', label: 'ตีกลับ' },
  { key: 'all', label: 'ทั้งหมด' },
];

function statusBadgeMeta(status) {
  switch (status) {
    case 'passed':
      return { text: 'ผ่านแล้ว', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/25' };
    case 'rejected':
      return { text: 'ตีกลับ', cls: 'bg-rose-500/15 text-rose-300 border-rose-400/25' };
    default:
      return { text: 'รอตรวจ', cls: 'bg-amber-500/15 text-amber-300 border-amber-400/25' };
  }
}

export function ReviewQueue({ productCode = null }) {
  const [clips, setClips] = useState([]);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [seenClipIds, setSeenClipIds] = useState(() => new Set());
  const [activeProxyClipId, setActiveProxyClipId] = useState(null);
  const [rejectingClipId, setRejectingClipId] = useState(null);
  const [rejectNote, setRejectNote] = useState('');
  const [rejectError, setRejectError] = useState('');
  const [editingClip, setEditingClip] = useState(null);
  const [busyClipId, setBusyClipId] = useState(null);
  const [batchApproving, setBatchApproving] = useState(false);

  const cardRefs = useRef(new Map());

  const markClipSeen = useCallback((clipId) => {
    if (!clipId) return;
    setSeenClipIds((prev) => {
      if (prev.has(clipId)) return prev;
      const next = new Set(prev);
      next.add(clipId);
      return next;
    });
  }, []);

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const params = new URLSearchParams();
      if (productCode) params.set('product_code', productCode);
      if (statusFilter && statusFilter !== 'all') params.set('status', statusFilter);
      const qs = params.toString();
      const res = await fetch(`/api/review/queue${qs ? `?${qs}` : ''}`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('โหลดคิวตรวจไม่สำเร็จ');
      const data = await res.json();
      const list = Array.isArray(data) ? data : data?.items || data?.clips || [];
      setClips(list);
    } catch (err) {
      setErrorMsg(err?.message || 'ไม่สามารถโหลดรายการตรวจได้');
    } finally {
      setLoading(false);
    }
  }, [productCode, statusFilter]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  // Track cards scrolled into viewport via IntersectionObserver
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
            const cid = entry.target.getAttribute('data-clip-id');
            if (cid) markClipSeen(cid);
          }
        });
      },
      { threshold: [0.5] }
    );

    cardRefs.current.forEach((node) => {
      if (node) observer.observe(node);
    });

    return () => observer.disconnect();
  }, [clips, markClipSeen]);

  const seenPendingIds = useMemo(() => {
    return clips
      .filter((c) => c.qc_status === 'pending' && seenClipIds.has(c.clip_id))
      .map((c) => c.clip_id);
  }, [clips, seenClipIds]);

  const handleApproveClip = async (clip) => {
    const cid = clip.clip_id;
    markClipSeen(cid);
    setBusyClipId(cid);
    setErrorMsg('');
    try {
      const res = await fetch(`/api/review/${encodeURIComponent(cid)}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          decision: 'pass',
          note: '',
          seen: true,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'อนุมัติไม่สำเร็จ');
      }
      const updated = await res.json();
      setClips((prev) => prev.map((item) => (item.clip_id === cid ? updated : item)));
    } catch (err) {
      setErrorMsg(err?.message || 'เกิดข้อผิดพลาดในการอนุมัติ');
    } finally {
      setBusyClipId(null);
    }
  };

  const handleOpenReject = (clip) => {
    markClipSeen(clip.clip_id);
    setRejectingClipId(clip.clip_id);
    setRejectNote(clip.qc_note || '');
    setRejectError('');
  };

  const handleConfirmReject = async (clip) => {
    const cid = clip.clip_id;
    const cleanNote = String(rejectNote || '').trim();
    if (!cleanNote) {
      setRejectError('กรุณาระบุเหตุผลที่ตีกลับก่อนบันทึก');
      return;
    }

    setBusyClipId(cid);
    setRejectError('');
    try {
      const res = await fetch(`/api/review/${encodeURIComponent(cid)}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          decision: 'reject',
          note: cleanNote,
          seen: true,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'ตีกลับไม่สำเร็จ');
      }
      const updated = await res.json();
      setClips((prev) => prev.map((item) => (item.clip_id === cid ? updated : item)));
      setRejectingClipId(null);
      setRejectNote('');
    } catch (err) {
      setRejectError(err?.message || 'ไม่สามารถบันทึกการตีกลับได้');
    } finally {
      setBusyClipId(null);
    }
  };

  const handleBatchApproveSeen = async () => {
    if (seenPendingIds.length === 0) return;
    setBatchApproving(true);
    setErrorMsg('');
    try {
      const res = await fetch('/api/review/batch-approve-seen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ seen_clip_ids: seenPendingIds }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'อนุมัติกลุ่มไม่สำเร็จ');
      }
      await fetchQueue();
    } catch (err) {
      setErrorMsg(err?.message || 'เกิดข้อผิดพลาดในการอนุมัติรายการที่ตรวจดูแล้ว');
    } finally {
      setBatchApproving(false);
    }
  };

  const handleSavedLightEdit = (updatedClip) => {
    if (!updatedClip?.clip_id) return;
    setClips((prev) =>
      prev.map((item) => (item.clip_id === updatedClip.clip_id ? updatedClip : item))
    );
  };

  return (
    <div data-oc-surface="workspace" className="w-full min-h-dvh bg-[#070A12] text-white pb-28 px-3 pt-3 space-y-4">
      {/* Header + Filter Chips */}
      <div data-oc-surface="data" className="sticky top-0 z-20 bg-[#070A12]/95 backdrop-blur-md py-2.5 border-b border-white/10 space-y-2.5">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-white">คิวตรวจคลิปก่อนโพสต์</h2>
            <p className="text-xs text-slate-400">
              ตรวจดูแล้ว {seenClipIds.size} รายการ · รออนุมัติ {seenPendingIds.length} รายการ
            </p>
          </div>
          <button
            type="button"
            onClick={fetchQueue}
            className="min-h-11 px-3.5 rounded-xl bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-200 border border-white/10"
          >
            รีเฟรชรายการ
          </button>
        </div>

        {/* Filter chips */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-0.5">
          {STATUS_FILTERS.map((f) => {
            const active = statusFilter === f.key;
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => setStatusFilter(f.key)}
                className={`min-h-11 px-4 rounded-full text-sm font-semibold whitespace-nowrap transition ${
                  active
                    ? 'bg-emerald-500 text-slate-950 font-bold'
                    : 'bg-white/5 text-slate-300 border border-white/10'
                }`}
              >
                {f.label}
              </button>
            );
          })}
        </div>

        {/* Batch Approve Only Seen Clips */}
        {seenPendingIds.length > 0 && (
          <button
            type="button"
            disabled={batchApproving}
            onClick={handleBatchApproveSeen}
            className="w-full min-h-12 px-4 py-2.5 rounded-2xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/40 text-sm font-bold text-emerald-200 transition"
          >
            {batchApproving
              ? 'กำลังอนุมัติรายการที่ตรวจดูแล้ว'
              : `อนุมัติรายการที่ตรวจดูแล้ว (${seenPendingIds.length})`}
          </button>
        )}
      </div>

      {errorMsg && (
        <div
          role="alert"
          className="p-3.5 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-sm text-rose-200"
        >
          {errorMsg}
        </div>
      )}

      {loading && clips.length === 0 && (
        <div className="py-12 text-center text-sm text-slate-400">กำลังโหลดคิวตรวจคลิป</div>
      )}

      {!loading && clips.length === 0 && (
        <div className="py-12 text-center text-sm text-slate-400">ไม่มีคลิปรอตรวจในหมวดนี้</div>
      )}

      {/* Clip Cards */}
      <div className="space-y-4">
        {clips.map((clip) => {
          const badge = statusBadgeMeta(clip.qc_status);
          const isSeen = seenClipIds.has(clip.clip_id);
          const isPlayingProxy = activeProxyClipId === clip.clip_id;
          const isRejecting = rejectingClipId === clip.clip_id;
          const isBusy = busyClipId === clip.clip_id;

          return (
            <article
              key={clip.clip_id}
              data-clip-id={clip.clip_id}
              ref={(el) => {
                if (el) cardRefs.current.set(clip.clip_id, el);
                else cardRefs.current.delete(clip.clip_id);
              }}
              onClick={() => markClipSeen(clip.clip_id)}
              className="rounded-3xl bg-[#0D1322] border border-white/10 overflow-hidden shadow-xl space-y-3.5 p-3.5"
            >
              {/* Card Title & Status */}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-emerald-400 font-semibold">
                      {clip.product_code}
                    </span>
                    <span className="text-xs text-slate-400">· v{clip.revision || 1}</span>
                    {isSeen && (
                      <span className="text-[11px] text-slate-400 bg-white/5 px-2 py-0.5 rounded-full">
                        ตรวจดูแล้ว
                      </span>
                    )}
                  </div>
                  <h3 className="text-base font-bold text-white truncate mt-0.5">
                    {clip.title || clip.clip_id}
                  </h3>
                </div>
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full border ${badge.cls}`}
                >
                  {badge.text}
                </span>
              </div>

              {/* Side-by-Side 9:16 Visual Gate Snapshots: Chat & CTA */}
              <div className="grid grid-cols-2 gap-2.5">
                <div className="relative aspect-[9/16] rounded-2xl overflow-hidden bg-black/50 border border-white/10">
                  <img
                    src={clip.chat_snapshot_url}
                    alt={`เฟรมแชท ${clip.clip_id}`}
                    loading="lazy"
                    className="w-full h-full object-cover"
                  />
                  <span className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/75 text-[11px] font-semibold text-white">
                    เฟรมแชท
                  </span>
                </div>

                <div className="relative aspect-[9/16] rounded-2xl overflow-hidden bg-black/50 border border-white/10">
                  <img
                    src={clip.cta_snapshot_url}
                    alt={`เฟรมจบ CTA ${clip.clip_id}`}
                    loading="lazy"
                    className="w-full h-full object-cover"
                  />
                  <span className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-emerald-950/90 border border-emerald-400/30 text-[11px] font-semibold text-emerald-200">
                    เฟรมจบ CTA ({Number(clip.cta_t || 0).toFixed(1)}s)
                  </span>
                </div>
              </div>

              {/* 540p Proxy Video Player (Tap-to-Play or Direct Native Video) */}
              <div className="rounded-2xl overflow-hidden bg-black/60 border border-white/10">
                {!isPlayingProxy ? (
                  <button
                    type="button"
                    onClick={() => {
                      markClipSeen(clip.clip_id);
                      setActiveProxyClipId(clip.clip_id);
                    }}
                    className="w-full min-h-12 px-4 py-3 text-sm font-semibold text-slate-200 hover:bg-white/5 transition text-center"
                  >
                    เล่นวิดีโอพรีวิว 540p
                  </button>
                ) : null}
                <video
                  playsInline
                  controls
                  preload="none"
                  poster={clip.chat_snapshot_url}
                  src={clip.proxy_video_url}
                  className={`w-full aspect-[9/16] max-h-[420px] bg-black ${
                    isPlayingProxy ? 'block' : 'hidden'
                  }`}
                />
              </div>

              {/* Compact Chat Turns Preview */}
              {Array.isArray(clip.turns) && clip.turns.length > 0 && (
                <div className="rounded-2xl bg-black/35 border border-white/5 p-3 space-y-1.5">
                  {clip.turns.slice(0, 4).map((turn, idx) => (
                    <div key={`${clip.clip_id}-t-${idx}`} className="text-xs leading-relaxed">
                      <span className="font-bold text-slate-300 mr-1.5">{turn.speaker}:</span>
                      <span className="text-slate-100">{turn.display}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Existing QC Note if rejected */}
              {clip.qc_note && !isRejecting && (
                <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/25 text-xs text-rose-200">
                  หมายเหตุตีกลับ: {clip.qc_note}
                </div>
              )}

              {/* Inline Reject Note Prompt */}
              {isRejecting && (
                <div className="p-3 rounded-2xl bg-rose-950/30 border border-rose-500/30 space-y-2.5">
                  <label
                    htmlFor={`reject-note-${clip.clip_id}`}
                    className="block text-xs font-semibold text-rose-200"
                  >
                    ระบุสาเหตุที่ตีกลับคลิปนี้
                  </label>
                  <input
                    id={`reject-note-${clip.clip_id}`}
                    type="text"
                    value={rejectNote}
                    onChange={(e) => setRejectNote(e.target.value)}
                    placeholder="เช่น คำผิดเทิร์นที่ 2 หรือรูปไม่ตรง"
                    className="w-full min-h-11 px-3 py-2 rounded-xl bg-black/50 border border-rose-400/30 text-base text-white"
                  />
                  {rejectError && <div className="text-xs text-rose-300">{rejectError}</div>}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setRejectingClipId(null)}
                      className="flex-1 min-h-11 px-3 rounded-xl bg-white/10 text-sm font-semibold text-slate-200"
                    >
                      ยกเลิก
                    </button>
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleConfirmReject(clip)}
                      className="flex-1 min-h-11 px-3 rounded-xl bg-rose-500 text-sm font-bold text-white"
                    >
                      ยืนยันตีกลับ
                    </button>
                  </div>
                </div>
              )}

              {/* Sticky ≥48px Action Bar: ตีกลับ · แก้ไขเบา · อนุมัติผ่าน */}
              <div className="grid grid-cols-3 gap-2 pt-1">
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => handleOpenReject(clip)}
                  className="min-h-12 px-3 rounded-2xl bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-sm font-bold text-rose-200 transition"
                >
                  ตีกลับ
                </button>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => {
                    markClipSeen(clip.clip_id);
                    setEditingClip(clip);
                  }}
                  className="min-h-12 px-3 rounded-2xl bg-white/10 hover:bg-white/15 border border-white/15 text-sm font-bold text-white transition"
                >
                  แก้ไขเบา
                </button>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => handleApproveClip(clip)}
                  className="min-h-12 px-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-sm font-bold text-slate-950 transition"
                >
                  อนุมัติผ่าน
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {/* Light Edit Bottom Sheet */}
      <ReviewSheet
        isOpen={Boolean(editingClip)}
        clip={editingClip}
        onClose={() => setEditingClip(null)}
        onSaved={handleSavedLightEdit}
      />
    </div>
  );
}

export default ReviewQueue;
