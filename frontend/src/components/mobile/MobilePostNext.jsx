import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Share2,
  Copy,
  Check,
  ShoppingBag,
  Clock,
  Calendar,
  CheckCircle2,
  RotateCcw,
  RefreshCw,
  AlertCircle,
  Download,
  Film,
  Sparkles,
  X,
} from 'lucide-react';
import { toMediaUrl } from '../../lib/mediaUrl.js';
import { activeChannel } from '../../lib/channelRuntime.js';

const STANDARD_SLOTS = ['07:00', '09:20', '11:40', '14:00', '16:20', '18:40', '21:00'];
const DEVICE_STORAGE_KEY = 'omnicut_mobile_device_id';

function getOrCreateDeviceId() {
  if (typeof window === 'undefined') return 'mobile-default';
  try {
    let existing = window.localStorage.getItem(DEVICE_STORAGE_KEY);
    if (!existing) {
      existing = `dev-${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
      window.localStorage.setItem(DEVICE_STORAGE_KEY, existing);
    }
    return existing;
  } catch {
    return 'mobile-session';
  }
}

function formatThaiSlotTime(isoString) {
  if (!isoString) return 'ยังไม่กำหนดรอบเวลา';
  try {
    const dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) return isoString;
    return dt.toLocaleString('th-TH', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

function formatShortDayLabel(dateStr) {
  try {
    const [y, m, d] = String(dateStr).split('-').map(Number);
    const dt = new Date(y, m - 1, d);
    return dt.toLocaleDateString('th-TH', { weekday: 'short', day: 'numeric', month: 'short' });
  } catch {
    return dateStr;
  }
}

export default function MobilePostNext() {
  const [channel] = useState(activeChannel);
  const [deviceId] = useState(getOrCreateDeviceId);

  const [currentClip, setCurrentClip] = useState(null);
  const [loadingClip, setLoadingClip] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [toastMsg, setToastMsg] = useState('');

  // Step 1 & 2 state: Handoff + Prefetch File for synchronous navigator.share
  const [preparingShare, setPreparingShare] = useState(false);
  const [prefetchProgress, setPrefetchProgress] = useState(0);
  const [preparedFile, setPreparedFile] = useState(null);
  const [isClaimedByMe, setIsClaimedByMe] = useState(false);
  const [hasSharedToTikTok, setHasSharedToTikTok] = useState(false);

  // Step 3 state: Product tagging checklist
  const [copiedCaption, setCopiedCaption] = useState(false);
  const [copiedProductId, setCopiedProductId] = useState(false);
  const [copiedProductName, setCopiedProductName] = useState(false);
  const [checklistState, setChecklistState] = useState({
    sharedVideo: false,
    pastedCaption: false,
    taggedProduct: false,
  });

  // Step 4 state: Confirmation bottom sheet (auto-opens on visibilitychange return)
  const [showConfirmSheet, setShowConfirmSheet] = useState(false);
  const [submittingConfirm, setSubmittingConfirm] = useState(false);

  // 7-Day Agenda Strip & Reschedule bottom sheet
  const [agendaDays, setAgendaDays] = useState([]);
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const [rescheduleTarget, setRescheduleTarget] = useState(null);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduling, setRescheduling] = useState(false);

  const hasSharedRef = useRef(false);
  useEffect(() => {
    hasSharedRef.current = hasSharedToTikTok;
  }, [hasSharedToTikTok]);

  const showToast = useCallback((msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 3200);
  }, []);

  const apiFetch = useCallback(
    async (path, options = {}) => {
      const headers = {
        'Content-Type': 'application/json',
        'X-OmniCut-Channel': channel || 'main',
        ...(options.headers || {}),
      };
      const res = await fetch(path, { ...options, headers });
      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const errJson = await res.json();
          detail = errJson.detail || errJson.message || detail;
        } catch {
          // ignore
        }
        throw new Error(detail);
      }
      return res.json();
    },
    [channel]
  );

  const resolveMedia = useCallback(
    (rawPath) => {
      if (!rawPath) return '';
      try {
        return toMediaUrl(String(rawPath), channel);
      } catch {
        return String(rawPath);
      }
    },
    [channel]
  );

  const loadAgenda = useCallback(async () => {
    try {
      const data = await apiFetch('/api/mobile-post/agenda');
      if (Array.isArray(data.days)) {
        setAgendaDays(data.days);
      }
    } catch {
      // Agenda is secondary; ignore transient errors
    }
  }, [apiFetch]);

  const loadNextDue = useCallback(
    async (silent = false) => {
      if (!silent) setLoadingClip(true);
      setErrorMsg('');
      try {
        const query = new URLSearchParams({ device_id: deviceId });
        const urlQueue =
          typeof window !== 'undefined'
            ? new URLSearchParams(window.location.search).get('queue')
            : null;
        if (urlQueue) query.set('queue_id', urlQueue);

        const data = await apiFetch(`/api/mobile-post/next-due?${query.toString()}`);
        const item = data?.item || (data?.queue_id ? data : null);
        setCurrentClip(item);

        const myClaim = `phone:${deviceId}`;
        const claimed = Boolean(item && item.status === 'awaiting_post' && item.claimed_by === myClaim);
        setIsClaimedByMe(claimed);
        setPreparedFile(null);
        setPrefetchProgress(0);
        setHasSharedToTikTok(false);
        setChecklistState({
          sharedVideo: false,
          pastedCaption: false,
          taggedProduct: false,
        });
      } catch (err) {
        setErrorMsg(err.message || 'ไม่สามารถโหลดคิวโพสต์ถัดไปได้');
      } finally {
        if (!silent) setLoadingClip(false);
      }
    },
    [apiFetch, deviceId]
  );

  useEffect(() => {
    loadNextDue();
    loadAgenda();
  }, [loadNextDue, loadAgenda]);

  // Step 4: Listen to visibilitychange when returning from TikTok app
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        if (hasSharedRef.current || isClaimedByMe) {
          setShowConfirmSheet(true);
        }
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [isClaimedByMe]);

  const fullCaptionText = currentClip
    ? [currentClip.caption, currentClip.hashtags].filter(Boolean).join('\n\n').trim()
    : '';

  // Step 1: Claim handoff + prefetch MP4 into memory as a File object
  const handlePrepareShare = async () => {
    if (!currentClip?.queue_id) return;
    setPreparingShare(true);
    setPrefetchProgress(10);
    setErrorMsg('');
    try {
      const handoffRes = await apiFetch('/api/mobile-post/handoff', {
        method: 'POST',
        body: JSON.stringify({
          queue_id: currentClip.queue_id,
          device_id: deviceId,
        }),
      });
      const updatedItem = handoffRes?.item || handoffRes;
      setCurrentClip(updatedItem);
      setIsClaimedByMe(true);
      setPrefetchProgress(35);

      const mediaUrl = resolveMedia(updatedItem.video_url || updatedItem.video_path);
      if (mediaUrl) {
        const response = await fetch(mediaUrl);
        if (!response.ok) {
          throw new Error('ไม่สามารถดึงไฟล์วิดีโอเพื่อเตรียมแชร์ได้');
        }
        setPrefetchProgress(75);
        const blob = await response.blob();
        const fileName = `${updatedItem.stem || updatedItem.clip_id || 'tiktok_clip'}.mp4`;
        const fileObj = new File([blob], fileName, { type: 'video/mp4' });
        setPreparedFile(fileObj);
      }
      setPrefetchProgress(100);
      showToast('เตรียมไฟล์วิดีโอพร้อมแชร์เข้า TikTok แล้ว');
    } catch (err) {
      setErrorMsg(err.message || 'เตรียมไฟล์ไม่สำเร็จ');
    } finally {
      setPreparingShare(false);
    }
  };

  // Step 2: Copy caption+hashtags and call navigator.share({ files }) synchronously
  const handleShareToTikTok = () => {
    if (!currentClip) return;

    if (fullCaptionText && navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(fullCaptionText).catch(() => {});
      setCopiedCaption(true);
      setTimeout(() => setCopiedCaption(false), 2500);
    }

    setHasSharedToTikTok(true);
    setChecklistState((prev) => ({
      ...prev,
      sharedVideo: true,
      pastedCaption: Boolean(fullCaptionText),
    }));

    if (preparedFile && typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
      const shareData = {
        files: [preparedFile],
        title: currentClip.product_name || 'OmniCut TikTok Clip',
        text: fullCaptionText,
      };
      navigator
        .share(shareData)
        .then(() => {
          setShowConfirmSheet(true);
        })
        .catch(() => {
          // User may still have switched to TikTok or dismissed share sheet
          setShowConfirmSheet(true);
        });
      return;
    }

    // Fallback when Web Share Level 2 is unavailable on current browser
    const mediaUrl = resolveMedia(currentClip.video_url || currentClip.video_path);
    if (mediaUrl) {
      const a = document.createElement('a');
      a.href = `${mediaUrl}${mediaUrl.includes('?') ? '&' : '?'}download=1`;
      a.download = `${currentClip.stem || currentClip.clip_id || 'tiktok_clip'}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
    setShowConfirmSheet(true);
  };

  // Step 3: 1-tap copy helpers for TikTok Shop product tagging
  const handleCopyProductId = () => {
    const pid = currentClip?.tiktok_product_id || currentClip?.product_code || '';
    if (!pid) return;
    navigator.clipboard?.writeText(pid).then(() => {
      setCopiedProductId(true);
      setChecklistState((prev) => ({ ...prev, taggedProduct: true }));
      showToast(`คัดลอกรหัสสินค้า ${pid} แล้ว`);
      setTimeout(() => setCopiedProductId(false), 2500);
    });
  };

  const handleCopyProductName = () => {
    const name = currentClip?.product_name || '';
    if (!name) return;
    navigator.clipboard?.writeText(name).then(() => {
      setCopiedProductName(true);
      setChecklistState((prev) => ({ ...prev, taggedProduct: true }));
      showToast(`คัดลอกชื่อสินค้า "${name}" แล้ว`);
      setTimeout(() => setCopiedProductName(false), 2500);
    });
  };

  const handleCopyCaptionOnly = () => {
    if (!fullCaptionText) return;
    navigator.clipboard?.writeText(fullCaptionText).then(() => {
      setCopiedCaption(true);
      setChecklistState((prev) => ({ ...prev, pastedCaption: true }));
      showToast('คัดลอกแคปชันและแฮชแท็กแล้ว');
      setTimeout(() => setCopiedCaption(false), 2500);
    });
  };

  // Step 4: Confirm or Abandon outcome and load next clip in <= 1s
  const handleConfirmOutcome = async (mode) => {
    if (!currentClip?.queue_id) return;
    setSubmittingConfirm(true);
    setErrorMsg('');
    try {
      await apiFetch('/api/mobile-post/confirm', {
        method: 'POST',
        body: JSON.stringify({
          queue_id: currentClip.queue_id,
          device_id: deviceId,
          mode,
        }),
      });
      setShowConfirmSheet(false);
      showToast(
        mode === 'scheduled_in_app'
          ? 'บันทึกสถานะตั้งเวลาในแอป TikTok แล้ว'
          : 'ยืนยันโพสต์สำเร็จ กำลังโหลดคลิปถัดไป'
      );
      await Promise.all([loadNextDue(true), loadAgenda()]);
    } catch (err) {
      setErrorMsg(err.message || 'บันทึกผลการโพสต์ไม่สำเร็จ');
    } finally {
      setSubmittingConfirm(false);
    }
  };

  const handleAbandonClaim = async () => {
    if (!currentClip?.queue_id) {
      setShowConfirmSheet(false);
      return;
    }
    setSubmittingConfirm(true);
    setErrorMsg('');
    try {
      await apiFetch('/api/mobile-post/abandon', {
        method: 'POST',
        body: JSON.stringify({
          queue_id: currentClip.queue_id,
          device_id: deviceId,
        }),
      });
      setShowConfirmSheet(false);
      setIsClaimedByMe(false);
      setPreparedFile(null);
      showToast('คืนคลิปกลับเข้าคิวรอจัดส่งแล้ว');
      await Promise.all([loadNextDue(true), loadAgenda()]);
    } catch (err) {
      setErrorMsg(err.message || 'คืนคิวไม่สำเร็จ');
    } finally {
      setSubmittingConfirm(false);
    }
  };

  // Reschedule via slot chip bottom sheet (no drag-and-drop)
  const openRescheduleSheet = (item, defaultDate) => {
    if (!item) return;
    const itemDate = (item.scheduled_at || '').slice(0, 10) || defaultDate || agendaDays[0]?.date || '';
    setRescheduleTarget(item);
    setRescheduleDate(itemDate);
  };

  const handleSelectSlotChip = async (slotTime) => {
    if (!rescheduleTarget?.queue_id || !rescheduleDate) return;
    setRescheduling(true);
    setErrorMsg('');
    try {
      const scheduledAt = `${rescheduleDate}T${slotTime}:00+07:00`;
      await apiFetch('/api/mobile-post/reschedule', {
        method: 'POST',
        body: JSON.stringify({
          queue_id: rescheduleTarget.queue_id,
          scheduled_at: scheduledAt,
        }),
      });
      setRescheduleTarget(null);
      showToast(`ย้ายเวลาไปรอบ ${slotTime} เรียบร้อยแล้ว`);
      await Promise.all([loadNextDue(true), loadAgenda()]);
    } catch (err) {
      setErrorMsg(err.message || 'ย้ายเวลาไม่สำเร็จ');
    } finally {
      setRescheduling(false);
    }
  };

  const handleDownloadCalendarIcs = () => {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://studio.omniflow.local';
    const url = `/api/mobile-post/calendar.ics?base_url=${encodeURIComponent(origin)}`;
    const link = document.createElement('a');
    link.href = url;
    link.download = 'omnicut-schedule.ics';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('กำลังดาวน์โหลดไฟล์ปฏิทินแจ้งเตือน (.ics)');
  };

  const activeDay = agendaDays[selectedDayIndex] || agendaDays[0] || null;
  const isDueWithin10Min =
    currentClip &&
    typeof currentClip.minutes_until_due === 'number' &&
    currentClip.minutes_until_due <= 10;

  return (
    <div className="min-h-dvh bg-slate-950 text-slate-100 pb-28 px-4 pt-4 select-none">
      {/* Toast Banner */}
      {toastMsg && (
        <div
          role="status"
          className="fixed inset-x-3 bottom-20 z-50 rounded-xl bg-emerald-600/95 px-4 py-3 text-sm font-medium text-white shadow-lg flex items-center gap-2"
        >
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-4">
        <div>
          <h1 className="text-lg font-bold text-white">โพสต์คลิปถัดไป</h1>
          <p className="text-xs text-slate-400">ส่งคลิปเข้าแอป TikTok และปักตะกร้าใน 4 ขั้นตอน</p>
        </div>
        <button
          type="button"
          onClick={() => {
            loadNextDue();
            loadAgenda();
          }}
          className="min-h-11 min-w-11 px-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 flex items-center gap-1.5 text-xs font-medium active:scale-95 transition"
        >
          <RefreshCw className="w-4 h-4" />
          <span>รีเฟรชคิว</span>
        </button>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="mb-4 rounded-xl bg-rose-950/80 border border-rose-700/60 p-3 text-xs text-rose-200 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Countdown Alert Banner when <= 10 mins away */}
      {isDueWithin10Min && (
        <div
          data-testid="countdown-alert-banner"
          className="mb-4 rounded-xl bg-amber-500/15 border border-amber-400/50 px-3.5 py-2.5 flex items-center justify-between gap-2 text-amber-200"
        >
          <div className="flex items-center gap-2 text-xs font-semibold">
            <Clock className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              {currentClip.minutes_until_due <= 0
                ? 'ถึงเวลาโพสต์รอบนี้แล้ว พร้อมส่งเข้า TikTok ทันที'
                : `อีก ${currentClip.minutes_until_due} นาทีจะถึงรอบโพสต์ (${formatThaiSlotTime(currentClip.scheduled_at)})`}
            </span>
          </div>
        </div>
      )}

      {/* Main Next-Due Clip Card */}
      {loadingClip ? (
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 text-center text-sm text-slate-400">
          กำลังค้นหาคลิปถัดไปในคิว...
        </div>
      ) : !currentClip ? (
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 text-center space-y-3">
          <Film className="w-8 h-8 text-slate-500 mx-auto" />
          <div className="text-sm font-semibold text-slate-200">ยังไม่มีคลิปรอโพสต์ในคิว</div>
          <p className="text-xs text-slate-400">
            เมื่ออนุมัติคลิปหรือมีไฟล์ใน Google Drive (01_Ready_to_post) รายการจะปรากฏที่นี่อัตโนมัติ
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Step 1: เตรียมคลิปถัดไป */}
          <section className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/20 px-2.5 py-1 text-xs font-semibold text-indigo-300">
                <Sparkles className="w-3.5 h-3.5" />
                <span>คลิปถัดไป</span>
              </span>
              <button
                type="button"
                onClick={() => openRescheduleSheet(currentClip)}
                className="min-h-11 px-3 rounded-lg bg-slate-800/90 text-xs text-slate-200 flex items-center gap-1.5"
              >
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span>{formatThaiSlotTime(currentClip.scheduled_at)}</span>
              </button>
            </div>

            <div className="flex gap-3.5 items-start">
              {/* 9:16 Cover Preview */}
              <div className="w-24 aspect-[9/16] rounded-xl bg-slate-800 overflow-hidden shrink-0 border border-slate-700/60 flex items-center justify-center">
                {currentClip.cover_9x16_url ? (
                  <img
                    src={resolveMedia(currentClip.cover_9x16_url)}
                    alt={currentClip.product_name || 'ปกคลิป 9:16'}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <Film className="w-6 h-6 text-slate-500" />
                )}
              </div>

              <div className="flex-1 min-w-0 space-y-1.5">
                <div className="text-xs font-medium text-slate-400">
                  {currentClip.product_code || 'สินค้าในคิว'}
                </div>
                <h2 className="text-base font-bold text-white leading-snug break-words">
                  {currentClip.product_name}
                </h2>
                {currentClip.tiktok_product_id && (
                  <div className="text-xs text-emerald-300 font-mono truncate">
                    ID: {currentClip.tiktok_product_id}
                  </div>
                )}
                {fullCaptionText && (
                  <p className="text-xs text-slate-300 line-clamp-3 bg-slate-950/70 rounded-lg p-2 border border-slate-800">
                    {fullCaptionText}
                  </p>
                )}
              </div>
            </div>

            <button
              type="button"
              disabled={preparingShare}
              onClick={handlePrepareShare}
              className="w-full min-h-12 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-md active:scale-[0.99] transition"
            >
              <Download className="w-4 h-4" />
              <span>
                {preparingShare
                  ? `กำลังเตรียมไฟล์ (${prefetchProgress}%)`
                  : preparedFile
                  ? 'เตรียมไฟล์พร้อมแชร์แล้ว'
                  : 'เตรียมไฟล์พร้อมแชร์'}
              </span>
            </button>
          </section>

          {/* Step 2: แชร์เข้า TikTok */}
          <section className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">ขั้นตอนที่ 2: แชร์เข้าแอป TikTok</h3>
              <button
                type="button"
                onClick={handleCopyCaptionOnly}
                className="min-h-11 px-3 rounded-lg bg-slate-800 text-xs text-slate-200 flex items-center gap-1.5"
              >
                {copiedCaption ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>คัดลอกแคปชัน</span>
              </button>
            </div>

            <button
              type="button"
              onClick={handleShareToTikTok}
              className="w-full min-h-12 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md active:scale-[0.99] transition"
            >
              <Share2 className="w-4 h-4" />
              <span>แชร์เข้า TikTok ทันที</span>
            </button>
          </section>

          {/* Step 3: Checklist ปักตะกร้า */}
          <section className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <ShoppingBag className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-white">ขั้นตอนที่ 3: Checklist ปักตะกร้าสินค้า</h3>
            </div>

            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                onClick={handleCopyProductId}
                className="w-full min-h-11 px-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-left text-xs font-medium text-slate-100 flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {copiedProductId ? (
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <Copy className="w-4 h-4 text-amber-400 shrink-0" />
                  )}
                  <span className="truncate">
                    คัดลอกรหัสสินค้า ({currentClip.tiktok_product_id || currentClip.product_code || 'ไม่มีรหัส'})
                  </span>
                </div>
              </button>

              <button
                type="button"
                onClick={handleCopyProductName}
                className="w-full min-h-11 px-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-left text-xs font-medium text-slate-100 flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {copiedProductName ? (
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <Copy className="w-4 h-4 text-sky-400 shrink-0" />
                  )}
                  <span className="truncate">คัดลอกชื่อสินค้า</span>
                </div>
              </button>
            </div>

            {/* Interactive Checklist toggles */}
            <div className="space-y-1.5 pt-1">
              {[
                { key: 'sharedVideo', label: 'เลือกคลิปวิดีโอและปกใน TikTok แล้ว' },
                { key: 'pastedCaption', label: 'วางแคปชันและแฮชแท็กเรียบร้อย' },
                { key: 'taggedProduct', label: 'ปักตะกร้าสินค้าตรงรุ่นเรียบร้อย' },
              ].map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() =>
                    setChecklistState((prev) => ({ ...prev, [item.key]: !prev[item.key] }))
                  }
                  className="w-full min-h-11 px-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center gap-2.5 text-xs text-slate-200"
                >
                  <CheckCircle2
                    className={`w-4 h-4 shrink-0 ${
                      checklistState[item.key] ? 'text-emerald-400' : 'text-slate-600'
                    }`}
                  />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setShowConfirmSheet(true)}
              className="w-full min-h-11 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center gap-2"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>เปิดหน้าต่างยืนยันผลโพสต์</span>
            </button>
          </section>
        </div>
      )}

      {/* 7-Day Agenda Strip (Touch-friendly, no drag-and-drop) */}
      <section className="mt-6 rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-white">ตารางโพสต์ 7 วัน</h3>
            <p className="text-xs text-slate-400">แตะเปลี่ยนรอบเวลาได้ทันทีโดยไม่ต้องลาก</p>
          </div>
          <button
            type="button"
            onClick={handleDownloadCalendarIcs}
            className="min-h-11 px-3 rounded-xl bg-indigo-600/20 border border-indigo-500/40 text-indigo-200 text-xs font-semibold flex items-center gap-1.5"
          >
            <Calendar className="w-4 h-4" />
            <span>เพิ่มการแจ้งเตือนลงปฏิทิน (.ics)</span>
          </button>
        </div>

        {/* 7-Day selector pills */}
        {agendaDays.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {agendaDays.map((dayObj, idx) => {
              const isSelected = idx === selectedDayIndex;
              const scheduledCount = (dayObj.items || []).length;
              return (
                <button
                  key={dayObj.date}
                  type="button"
                  onClick={() => setSelectedDayIndex(idx)}
                  className={`min-h-11 px-3 py-1.5 rounded-xl text-xs font-semibold shrink-0 flex flex-col items-center justify-center border transition ${
                    isSelected
                      ? 'bg-indigo-600 text-white border-indigo-400'
                      : 'bg-slate-950 text-slate-300 border-slate-800'
                  }`}
                >
                  <span>{formatShortDayLabel(dayObj.date)}</span>
                  <span className="text-[11px] opacity-80">{scheduledCount} คลิป</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Day slots list */}
        {activeDay && (
          <div className="grid grid-cols-1 gap-2 pt-1">
            {(activeDay.slots || []).map((slot) => {
              const slotItem = slot.item;
              return (
                <div
                  key={slot.time}
                  className="min-h-11 rounded-xl bg-slate-950/80 border border-slate-800 px-3 py-2 flex items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="px-2 py-1 rounded-md bg-slate-800 text-xs font-mono font-semibold text-amber-300">
                      {slot.time}
                    </span>
                    {slotItem ? (
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-white truncate">
                          {slotItem.product_name}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          สถานะ: {slotItem.status === 'posted' ? 'โพสต์แล้ว' : 'รอจัดส่ง'}
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-500">ว่าง</span>
                    )}
                  </div>

                  {slotItem && slotItem.status !== 'posted' && (
                    <button
                      type="button"
                      onClick={() => openRescheduleSheet(slotItem, activeDay.date)}
                      className="min-h-11 px-3 rounded-lg bg-slate-800 text-xs text-slate-200 flex items-center gap-1"
                    >
                      <Clock className="w-3.5 h-3.5" />
                      <span>ย้ายรอบ</span>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Step 4: Bottom Sheet Confirmation on Returning from TikTok */}
      {showConfirmSheet && currentClip && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/75 flex items-end justify-center p-3"
        >
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-700 p-5 space-y-3 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">ยืนยันผลการโพสต์ใน TikTok</h3>
              <button
                type="button"
                onClick={() => setShowConfirmSheet(false)}
                className="min-h-11 min-w-11 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-300">
              คลิป: <span className="font-semibold text-white">{currentClip.product_name}</span>
            </p>

            <div className="space-y-2 pt-1">
              <button
                type="button"
                disabled={submittingConfirm}
                onClick={() => handleConfirmOutcome('posted')}
                className="w-full min-h-12 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm flex items-center justify-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>โพสต์สำเร็จแล้ว</span>
              </button>

              <button
                type="button"
                disabled={submittingConfirm}
                onClick={() => handleConfirmOutcome('scheduled_in_app')}
                className="w-full min-h-12 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm flex items-center justify-center gap-2"
              >
                <Clock className="w-4 h-4" />
                <span>ตั้งเวลาในแอป TikTok แล้ว</span>
              </button>

              <button
                type="button"
                disabled={submittingConfirm}
                onClick={handleAbandonClaim}
                className="w-full min-h-12 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-sm flex items-center justify-center gap-2"
              >
                <RotateCcw className="w-4 h-4" />
                <span>ยังไม่ได้โพสต์ (คืนเข้าคิว)</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reschedule Slot Chip Bottom Sheet */}
      {rescheduleTarget && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/75 flex items-end justify-center p-3"
        >
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-700 p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">เลือกรอบเวลาโพสต์มาตรฐาน (7 รอบ)</h3>
              <button
                type="button"
                onClick={() => setRescheduleTarget(null)}
                className="min-h-11 min-w-11 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-400">วันที่ต้องการโพสต์</label>
              <input
                type="date"
                value={rescheduleDate}
                onChange={(e) => setRescheduleDate(e.target.value)}
                className="w-full min-h-11 rounded-xl bg-slate-950 border border-slate-800 px-3 text-base text-white"
              />
            </div>

            <div className="grid grid-cols-3 gap-2">
              {STANDARD_SLOTS.map((slotTime) => (
                <button
                  key={slotTime}
                  type="button"
                  disabled={rescheduling}
                  onClick={() => handleSelectSlotChip(slotTime)}
                  className="min-h-11 rounded-xl bg-slate-800 hover:bg-indigo-600 text-sm font-mono font-semibold text-white flex items-center justify-center gap-1.5"
                >
                  <Clock className="w-3.5 h-3.5 text-amber-400" />
                  <span>{slotTime}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
