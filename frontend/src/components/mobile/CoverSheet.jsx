import React, { useState, useEffect, useCallback } from 'react';
import {
  X, Check, RefreshCw, Image as ImageIcon, Sparkles, CheckCircle2, AlertTriangle, Loader2,
} from 'lucide-react';
import api, { getCoverHighlights, renderProCover, updateAngleCover } from '../../api.js';
import { toMediaUrl } from '../../lib/mediaUrl.js';
import { getCoverVariant, applyCoverResult } from '../../lib/coverVariant.js';
import { useBackToClose } from '../../hooks/useBackToClose.js';

/**
 * CoverSheet — Mobile bottom sheet for inspecting and replacing 9:16 & 3:4 covers (Phase 5.3).
 *
 * Implements a 3-tap cover replacement flow while preserving the canonical cover design (Rule 23):
 *   Tap 1: Open CoverSheet -> auto-loads candidate highlight frames from `/api/covers/highlights`
 *   Tap 2: Tap a highlight frame -> renders 9:16 + 3:4 covers via `/api/covers/render-pro`
 *          and binds both variants via `POST /api/covers/bind`
 *   Tap 3: Done / close or auto-updates parent clip item
 */
export function CoverSheet({
  open = false,
  clip = null,
  onClose,
  onCoverUpdated,
}) {
  useBackToClose(Boolean(open && clip), onClose);

  const clipIdentity = clip?.export_id || clip?.rel_path || clip?.path || clip?.name || '';
  const [candidates, setCandidates] = useState([]);
  const [loadingHighlights, setLoadingHighlights] = useState(false);
  const [renderingTs, setRenderingTs] = useState(null);
  const [error, setError] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [updatedOverlay, setUpdatedOverlay] = useState({ id: '', data: null });

  const localClip =
    updatedOverlay.id === clipIdentity && updatedOverlay.data
      ? { ...clip, ...updatedOverlay.data }
      : clip;

  const videoPath = localClip?.rel_path || localClip?.path || localClip?.video_url || '';
  const exportId = localClip?.export_id || null;

  const loadHighlights = useCallback(async () => {
    if (!videoPath) return;
    setLoadingHighlights(true);
    setError(null);
    try {
      const data = await getCoverHighlights(videoPath);
      const list = Array.isArray(data?.candidates) ? data.candidates : [];
      setCandidates(list);
    } catch (err) {
      setError(err?.friendlyMessage || err?.message || 'ไม่สามารถดึงเฟรมไฮไลต์จากคลิปได้');
    } finally {
      setLoadingHighlights(false);
    }
  }, [videoPath]);

  useEffect(() => {
    if (!open || !videoPath) return undefined;
    let cancelled = false;
    Promise.resolve().then(async () => {
      if (cancelled) return;
      setLoadingHighlights(true);
      setError(null);
      try {
        const data = await getCoverHighlights(videoPath);
        if (!cancelled) {
          setCandidates(Array.isArray(data?.candidates) ? data.candidates : []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.friendlyMessage || err?.message || 'ไม่สามารถดึงเฟรมไฮไลต์จากคลิปได้');
        }
      } finally {
        if (!cancelled) {
          setLoadingHighlights(false);
        }
      }
    });
    return () => {
      cancelled = true;
    };
  }, [open, videoPath]);

  if (!open || !localClip) return null;

  const cover9x16 = getCoverVariant(localClip, '9:16');
  const cover3x4 = getCoverVariant(localClip, '3:4');
  const url9x16 = toMediaUrl(cover9x16.url || cover9x16.path || localClip.thumbnail_url);
  const url3x4 = toMediaUrl(cover3x4.url || cover3x4.path || cover9x16.url || localClip.thumbnail_url);

  const isBound = Boolean(
    localClip.cover_revision ||
    localClip.cover_binding_revision ||
    localClip.cover_3x4_path ||
    localClip.cover_9x16_path ||
    localClip.cover_path,
  );

  const handleSelectCandidate = async (candidate) => {
    if (!videoPath || renderingTs !== null) return;
    const timestamp = Number(candidate?.timestamp ?? 1.0);
    setRenderingTs(timestamp);
    setError(null);
    setStatusMessage('กำลังสร้างปก 9:16 และ 3:4...');

    try {
      const hookText = localClip.hook_title || localClip.angle_name || localClip.product_name || '';
      const subText = localClip.product_name && localClip.product_name !== hookText ? localClip.product_name : '';

      // Step 2: Render canonical 9:16 & 3:4 cover via /api/covers/render-pro (Rule 23)
      const renderRes = await renderProCover({
        video_path: videoPath,
        export_id: exportId,
        at_seconds: timestamp,
        aspect_ratio: 'both',
        enable_hook_text: Boolean(hookText),
        hook_text: hookText,
        sub_text: subText,
        template: 'neon',
        hook_position: 'top',
      });

      const cover9x16Path = renderRes?.cover_path || '';
      const cover3x4Path = renderRes?.cover_3x4_path || cover9x16Path;

      // Step 3: Explicitly call POST /api/covers/bind to bind both 9:16 & 3:4 covers
      let bindRevision = renderRes?.cover_binding_revision || null;
      if (exportId && (cover9x16Path || cover3x4Path)) {
        try {
          const bindRes = await api.post('/covers/bind', {
            export_id: exportId,
            video_path: videoPath,
            cover_path: cover9x16Path,
            cover_3x4_path: cover3x4Path,
            selections: {
              ...(cover9x16Path ? { '9:16': cover9x16Path } : {}),
              ...(cover3x4Path ? { '3:4': cover3x4Path } : {}),
            },
          });
          if (bindRes?.data?.revision || bindRes?.data?.cover_binding_revision) {
            bindRevision = bindRes.data.revision || bindRes.data.cover_binding_revision;
          }
        } catch (bindErr) {
          // If /api/covers/render-pro already bound via ExportCoverBindingStore and
          // /api/covers/bind is not separately mounted, continue cleanly.
          if (bindErr?.response?.status && bindErr.response.status !== 404 && !bindRevision) {
            throw bindErr;
          }
        }
      }

      // Also sync angle cover metadata if product_id & angle_id exist
      if (localClip.product_id && localClip.angle_id && (cover9x16Path || cover3x4Path)) {
        try {
          await updateAngleCover(localClip.product_id, localClip.angle_id, {
            cover_path: cover9x16Path,
            cover_3x4_path: cover3x4Path,
            cover_9x16_path: cover9x16Path,
            export_id: exportId,
          });
        } catch {
          // Best-effort sync to angle record
        }
      }

      const nextClip = {
        ...applyCoverResult(localClip, renderRes),
        cover_revision: bindRevision || (localClip.cover_revision || 0) + 1,
        cover_binding_revision: bindRevision || (localClip.cover_binding_revision || 0) + 1,
      };
      setUpdatedOverlay({ id: clipIdentity, data: nextClip });
      setStatusMessage('บันทึกปก 9:16 และ 3:4 เรียบร้อยแล้ว');
      onCoverUpdated?.(nextClip);
    } catch (err) {
      setError(err?.friendlyMessage || err?.message || 'สร้างหรือผูกปกคลิปไม่สำเร็จ');
      setStatusMessage('');
    } finally {
      setRenderingTs(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end bg-black/75 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="จัดการปกคลิป"
    >
      <div
        className="w-full max-w-lg mx-auto bg-slate-900 border-t border-slate-700/80 rounded-t-3xl shadow-2xl max-h-[90dvh] flex flex-col overflow-hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 12px)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <div className="flex items-center gap-2 min-w-0">
            <ImageIcon className="w-5 h-5 text-cyan-400 shrink-0" />
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-white truncate">
                จัดการปกคลิป (9:16 & 3:4)
              </h2>
              <p className="text-xs text-slate-400 truncate">
                {localClip.hook_title || localClip.product_name || localClip.name || 'คลิปวิดีโอ'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {isBound ? (
              <span
                data-testid="cover-bound-pill"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>เลือกปกแล้ว</span>
              </span>
            ) : (
              <span
                data-testid="cover-unbound-pill"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/40"
              >
                <span>ปกยังไม่ยืนยัน</span>
              </span>
            )}

            <button
              type="button"
              onClick={onClose}
              aria-label="ปิดหน้าต่างเลือกปก"
              className="min-w-11 min-h-11 inline-flex items-center justify-center rounded-full bg-slate-800 text-slate-200 hover:bg-slate-700 active:scale-95 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          {/* Current 9:16 and 3:4 Previews */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-2.5 flex flex-col items-center">
              <div className="w-full flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-slate-300">ปก 9:16 (ฟีดเต็มจอ)</span>
                <span className="text-[11px] text-cyan-400">1080×1920</span>
              </div>
              <div className="w-28 aspect-[9/16] rounded-xl overflow-hidden bg-slate-900 border border-slate-800 flex items-center justify-center">
                {url9x16 ? (
                  <img
                    src={url9x16}
                    alt="ปก 9:16"
                    loading="lazy"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-xs text-slate-500">ไม่มีภาพ</span>
                )}
              </div>
            </div>

            <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-2.5 flex flex-col items-center">
              <div className="w-full flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-slate-300">ปก 3:4 (ตารางโปรไฟล์)</span>
                <span className="text-[11px] text-amber-400">1080×1440</span>
              </div>
              <div className="w-28 aspect-[3/4] rounded-xl overflow-hidden bg-slate-900 border border-slate-800 flex items-center justify-center my-auto">
                {url3x4 ? (
                  <img
                    src={url3x4}
                    alt="ปก 3:4"
                    loading="lazy"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-xs text-slate-500">ไม่มีภาพ</span>
                )}
              </div>
            </div>
          </div>

          {/* Feedback banner */}
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {statusMessage && !error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-950/50 border border-emerald-500/40 text-emerald-200 text-xs">
              {renderingTs !== null ? (
                <Loader2 className="w-4 h-4 text-emerald-400 animate-spin shrink-0" />
              ) : (
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
              )}
              <span>{statusMessage}</span>
            </div>
          )}

          {/* Candidate Highlight Frames (Tap 2 of 3-tap flow) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-medium text-white">
                  แตะเลือกเฟรมเพื่อสร้างปกใหม่ทันที
                </h3>
              </div>
              <button
                type="button"
                onClick={loadHighlights}
                disabled={loadingHighlights || renderingTs !== null}
                className="min-h-11 px-3 inline-flex items-center gap-1.5 rounded-xl bg-slate-800/80 text-xs text-slate-200 hover:bg-slate-700 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingHighlights ? 'animate-spin' : ''}`} />
                <span>โหลดเฟรมใหม่</span>
              </button>
            </div>

            {loadingHighlights ? (
              <div className="grid grid-cols-3 gap-2.5 py-4">
                {[0, 1, 2].map((idx) => (
                  <div
                    key={idx}
                    className="aspect-[9/16] rounded-xl bg-slate-800/60 animate-pulse border border-slate-700/50"
                  />
                ))}
              </div>
            ) : candidates.length === 0 ? (
              <div className="text-center py-6 bg-slate-950/50 rounded-2xl border border-slate-800/80">
                <p className="text-xs text-slate-400">ยังไม่มีเฟรมแนะนำสำหรับคลิปนี้</p>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2.5">
                {candidates.map((cand) => {
                  const isBusy = renderingTs === cand.timestamp;
                  const thumbSrc = toMediaUrl(cand.thumb_url);
                  return (
                    <button
                      key={`${cand.index}-${cand.timestamp}`}
                      type="button"
                      disabled={renderingTs !== null}
                      onClick={() => handleSelectCandidate(cand)}
                      className="group relative aspect-[9/16] rounded-xl overflow-hidden border border-slate-700 hover:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 bg-slate-950 text-left transition active:scale-[0.98] disabled:opacity-60"
                    >
                      {thumbSrc ? (
                        <img
                          src={thumbSrc}
                          alt={cand.label || `เฟรม ${cand.timestamp}s`}
                          loading="lazy"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xs text-slate-500">
                          {cand.timestamp}s
                        </div>
                      )}
                      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/60 to-transparent p-2">
                        <p className="text-[11px] font-medium text-white truncate">
                          {cand.label || 'เฟรมแนะนำ'}
                        </p>
                        <p className="text-[10px] text-cyan-300">
                          {Number(cand.timestamp || 0).toFixed(1)} วินาที
                        </p>
                      </div>
                      {isBusy && (
                        <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center gap-1">
                          <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
                          <span className="text-[11px] text-white font-medium">กำลังสร้าง...</span>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-800 bg-slate-900/95">
          <button
            type="button"
            onClick={onClose}
            className="w-full min-h-11 inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-800 hover:bg-slate-700 text-sm font-semibold text-white transition"
          >
            <Check className="w-4 h-4" />
            <span>เสร็จสิ้น</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default CoverSheet;
