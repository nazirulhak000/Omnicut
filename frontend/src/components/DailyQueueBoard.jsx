import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  CalendarClock,
  Clock,
  GripVertical,
  Image as ImageIcon,
  Play,
  RefreshCw,
  Rocket,
  Send,
} from 'lucide-react';
import {
  getAutopostAutomationStatus,
  triggerAutopostRun,
  updateAutopostAutomationSettings,
} from '../api';
import { useChannel } from '../context/ChannelContext.jsx';
import {
  buildDayColumns,
  canDragQueueItem,
  computeBoardSummary,
  DAILY_TARGET_CAPACITY,
} from '../lib/dailyQueueBoard.js';
import { toThumbUrl } from '../lib/mediaUrl.js';
import { dateOnly, localParts, scheduleTimeOptions } from '../lib/scheduleQueue.js';

const POLL_INTERVAL_MS = 5000;

const STATUS_LABELS = {
  planned: 'รอจัดส่ง',
  ready_for_extension: 'พร้อมส่ง Extension',
  awaiting_post: 'รอกดโพสต์',
  scheduled_on_platform: 'ตั้งเวลาบน TikTok แล้ว',
  draft_on_platform: 'แบบร่างบน TikTok',
  confirmation_unknown: 'รอตรวจผล',
  posted: 'โพสต์แล้ว',
  failed: 'ผิดพลาด',
};

const STATUS_BADGE_STYLES = {
  planned: 'text-amber-200 bg-amber-500/10 border-amber-500/25',
  ready_for_extension: 'text-cyan-200 bg-cyan-500/10 border-cyan-500/25',
  awaiting_post: 'text-violet-200 bg-violet-500/10 border-violet-500/25',
  scheduled_on_platform: 'text-blue-200 bg-blue-500/10 border-blue-500/25',
  draft_on_platform: 'text-slate-200 bg-slate-500/10 border-slate-500/25',
  confirmation_unknown: 'text-amber-200 bg-amber-500/10 border-amber-500/25',
  posted: 'text-emerald-200 bg-emerald-500/10 border-emerald-500/25',
  failed: 'text-red-200 bg-red-500/10 border-red-500/25',
};

function resolveCoverThumb(item) {
  const raw =
    item?.cover_url ||
    item?.cover_path ||
    item?.cover_3x4_url ||
    item?.cover_3x4_path ||
    item?.cover_9x16_url ||
    item?.cover_9x16_path ||
    '';
  return raw ? toThumbUrl(raw, 160) : '';
}

function formatEpisodeLabel(item) {
  const ep = item?.ep ?? item?.episode ?? item?.angle_ep;
  const productName = item?.product_name || item?.project_name || 'ไม่ระบุสินค้า';
  return ep !== undefined && ep !== null && ep !== '' ? `${productName} · EP ${ep}` : productName;
}

export default function DailyQueueBoard({
  queue = [],
  loading = false,
  onRefreshQueue,
  onPrepareItem,
  onRescheduleDate,
  onUpdateTime,
  showToast,
}) {
  const channel = useChannel();
  const channelId = channel?.channelId || 'main';
  const channelName = channel?.currentChannel?.name || channel?.channelName || channelId;

  const [rangeDays, setRangeDays] = useState(7);
  const [includeOverdue, setIncludeOverdue] = useState(false);
  const [draggedId, setDraggedId] = useState(null);
  const [dragOverDate, setDragOverDate] = useState(null);
  const [editingItemId, setEditingItemId] = useState(null);
  const [editingTime, setEditingTime] = useState('09:00');
  const [busyIds, setBusyIds] = useState(() => new Set());

  const [automationStatus, setAutomationStatus] = useState(null);
  const [togglingAuto, setTogglingAuto] = useState(false);
  const [triggeringRun, setTriggeringRun] = useState(false);

  const timeOptions = useMemo(() => scheduleTimeOptions(), []);
  const todayKey = dateOnly();
  const mountedRef = useRef(true);
  const channelRef = useRef(channelId);
  channelRef.current = channelId;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchAutomationStatus = useCallback(async (targetChannel = channelRef.current) => {
    try {
      const data = await getAutopostAutomationStatus(targetChannel);
      if (mountedRef.current && channelRef.current === targetChannel) {
        setAutomationStatus(data);
      }
    } catch {
      // Keep previous status if endpoint is temporarily unreachable
    }
  }, []);

  // Re-fetch immediately on channelId change + poll every 5s while tab is visible
  useEffect(() => {
    let timerId = null;

    const tick = () => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return;
      void fetchAutomationStatus(channelId);
      void onRefreshQueue?.({ silent: true });
    };

    void fetchAutomationStatus(channelId);

    const startPolling = () => {
      if (timerId !== null) return;
      timerId = window.setInterval(tick, POLL_INTERVAL_MS);
    };

    const stopPolling = () => {
      if (timerId !== null) {
        window.clearInterval(timerId);
        timerId = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        tick();
        startPolling();
      } else {
        stopPolling();
      }
    };

    if (typeof document === 'undefined' || document.visibilityState === 'visible') {
      startPolling();
    }
    document?.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      stopPolling();
      document?.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [channelId, fetchAutomationStatus, onRefreshQueue]);

  const summary = useMemo(
    () => computeBoardSummary(queue, automationStatus, todayKey),
    [queue, automationStatus, todayKey],
  );

  const columns = useMemo(
    () => buildDayColumns(queue, { rangeDays, includeOverdue, todayKey }),
    [queue, rangeDays, includeOverdue, todayKey],
  );

  const autoEnabled = Boolean(automationStatus?.automation_settings?.enabled ?? automationStatus?.enabled);
  const conductorRunning = Boolean(automationStatus?.conductor_state?.running ?? automationStatus?.conductor?.running);

  const handleToggleAutomation = async () => {
    if (togglingAuto) return;
    setTogglingAuto(true);
    try {
      const next = await updateAutopostAutomationSettings(
        { enabled: !autoEnabled, mode: 'hybrid' },
        channelId,
      );
      setAutomationStatus((prev) => ({ ...(prev || {}), automation_settings: next }));
      showToast?.(!autoEnabled ? 'เปิดโพสต์อัตโนมัติ (Hybrid) แล้ว' : 'ปิดโพสต์อัตโนมัติแล้ว');
    } catch (error) {
      showToast?.(error?.response?.data?.detail || error?.message || 'อัปเดตการตั้งค่าไม่สำเร็จ', 'error');
    } finally {
      setTogglingAuto(false);
    }
  };

  const handleTriggerRun = async () => {
    if (triggeringRun) return;
    setTriggeringRun(true);
    try {
      const res = await triggerAutopostRun({ mode: 'hybrid' }, channelId);
      if (res?.started) {
        showToast?.('เริ่มรัน Auto-Post ทันทีแล้ว');
      } else {
        showToast?.(res?.reason || 'Auto-Post กำลังทำงานอยู่แล้ว');
      }
      await fetchAutomationStatus(channelId);
    } catch (error) {
      showToast?.(error?.response?.data?.detail || error?.message || 'สั่งรัน Auto-Post ไม่สำเร็จ', 'error');
    } finally {
      setTriggeringRun(false);
    }
  };

  const withItemBusy = async (id, fn) => {
    setBusyIds((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });
    try {
      await fn();
    } finally {
      setBusyIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleDropOnColumn = async (targetDateKey) => {
    setDragOverDate(null);
    if (!draggedId) return;
    const item = queue.find((row) => row.id === draggedId);
    setDraggedId(null);
    if (!item || !canDragQueueItem(item)) {
      showToast?.('ย้ายวันได้เฉพาะคิวสถานะรอจัดส่งหรือผิดพลาด', 'error');
      return;
    }
    const { date, time } = localParts(item.scheduled_at);
    if (date === targetDateKey) return;
    await withItemBusy(item.id, async () => {
      await onRescheduleDate?.(item, targetDateKey, time);
    });
  };

  const handleSaveInlineTime = async (item) => {
    const { date } = localParts(item.scheduled_at);
    setEditingItemId(null);
    await withItemBusy(item.id, async () => {
      await onUpdateTime?.(item, date, editingTime);
    });
  };

  return (
    <div className="space-y-4">
      {/* ── Top Live Sync & Auto-Post Bar ── */}
      <div className="rounded-2xl border border-[#23262D] bg-[#14161A] p-4 space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#1B1D22] border border-[#2B2E36] text-xs font-bold text-white">
              ช่อง: {channelName}
            </span>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold tabular-nums ${
                conductorRunning
                  ? 'bg-cyan-500/15 border-cyan-400/35 text-cyan-200'
                  : 'bg-white/[0.04] border-white/[0.08] text-slate-300'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${conductorRunning ? 'bg-cyan-400 animate-pulse' : 'bg-emerald-400'}`} />
              {conductorRunning ? 'กำลังรัน Auto-Post...' : 'ซิงก์สดทุก 5 วินาที'}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              role="switch"
              aria-checked={autoEnabled}
              disabled={togglingAuto}
              onClick={handleToggleAutomation}
              className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-bold transition-colors cursor-pointer disabled:opacity-60 ${
                autoEnabled
                  ? 'bg-emerald-500/15 border-emerald-400/40 text-emerald-200 hover:bg-emerald-500/20'
                  : 'bg-white/[0.04] border-white/[0.1] text-slate-300 hover:bg-white/[0.08]'
              }`}
            >
              <span
                aria-hidden="true"
                className={`w-7 h-4 rounded-full p-0.5 transition-colors flex items-center ${
                  autoEnabled ? 'bg-emerald-400 justify-end' : 'bg-slate-600 justify-start'
                }`}
              >
                <span className="w-3 h-3 rounded-full bg-[#0B0F17]" />
              </span>
              <span>เปิดโพสต์อัตโนมัติ (Hybrid)</span>
            </button>

            <button
              type="button"
              disabled={triggeringRun || conductorRunning}
              onClick={handleTriggerRun}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 text-xs font-black transition-colors cursor-pointer disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{triggeringRun ? 'กำลังสั่งรัน...' : 'รัน Auto-Post ทันที'}</span>
            </button>
          </div>
        </div>

        {/* Summary Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
          <div className="rounded-xl bg-[#0E1014] border border-white/[0.06] px-3 py-2.5">
            <p className="text-[11px] text-slate-400">คิววันนี้</p>
            <p className="mt-0.5 text-lg font-black text-white tabular-nums">
              {summary.todayCount} <span className="text-xs font-semibold text-slate-500">คลิป</span>
            </p>
          </div>
          <div className="rounded-xl bg-[#0E1014] border border-white/[0.06] px-3 py-2.5">
            <p className="text-[11px] text-slate-400">คิวถัดไป</p>
            <p className="mt-0.5 text-lg font-black text-cyan-200 tabular-nums">{summary.nextSlotTime}</p>
          </div>
          <div className="rounded-xl bg-[#0E1014] border border-white/[0.06] px-3 py-2.5">
            <p className="text-[11px] text-slate-400">โควตาตั้งเวลา TikTok</p>
            <p
              className={`mt-0.5 text-lg font-black tabular-nums ${
                summary.scheduledQuotaUsed >= 25 ? 'text-amber-300' : 'text-white'
              }`}
            >
              {summary.scheduledQuotaUsed}/{summary.scheduledQuotaMax}
            </p>
          </div>
          <div className="rounded-xl bg-[#0E1014] border border-white/[0.06] px-3 py-2.5">
            <p className="text-[11px] text-slate-400">ค้างเลยกำหนด</p>
            <p
              className={`mt-0.5 text-lg font-black tabular-nums ${
                summary.overdueCount > 0 ? 'text-red-300' : 'text-emerald-300'
              }`}
            >
              {summary.overdueCount} <span className="text-xs font-semibold text-slate-500">คลิป</span>
            </p>
          </div>
        </div>
      </div>

      {/* ── Range & Overdue Controls ── */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 px-1">
        <div className="flex items-center gap-1.5 rounded-xl bg-[#14161A] p-1 border border-[#23262D]">
          {[
            { id: 7, label: '7 วัน' },
            { id: 14, label: '14 วัน' },
            { id: 'all', label: 'ทั้งหมด' },
          ].map((opt) => (
            <button
              key={String(opt.id)}
              type="button"
              onClick={() => setRangeDays(opt.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                rangeDays === opt.id
                  ? 'bg-cyan-400 text-slate-950 font-black'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {(summary.overdueCount > 0 || includeOverdue) && (
            <button
              type="button"
              onClick={() => setIncludeOverdue((v) => !v)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold transition-colors cursor-pointer tabular-nums ${
                includeOverdue
                  ? 'bg-red-500/15 border-red-400/40 text-red-200'
                  : 'bg-[#14161A] border-[#23262D] text-slate-300 hover:text-white'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{includeOverdue ? 'ซ่อนวันเลยกำหนด' : `แสดงวันเลยกำหนด (${summary.overdueCount})`}</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              void onRefreshQueue?.();
              void fetchAutomationStatus(channelId);
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#14161A] border border-[#23262D] text-xs font-bold text-slate-300 hover:text-white transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>รีเฟรช</span>
          </button>
        </div>
      </div>

      {/* ── Horizontal Kanban Daily Columns ── */}
      {loading && queue.length === 0 ? (
        <div className="p-10 text-center text-sm text-slate-400 rounded-2xl border border-[#23262D] bg-[#14161A]">
          กำลังโหลดคิวโพสต์รายวัน...
        </div>
      ) : (
        <div className="flex overflow-x-auto snap-x gap-3 pb-3">
          {columns.map((col) => {
            const total = col.items.length;
            const isDropTarget = dragOverDate === col.dateKey;
            return (
              <section
                key={col.dateKey}
                onDragOver={(e) => {
                  e.preventDefault();
                  if (dragOverDate !== col.dateKey) setDragOverDate(col.dateKey);
                }}
                onDragLeave={() => {
                  if (dragOverDate === col.dateKey) setDragOverDate(null);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  void handleDropOnColumn(col.dateKey);
                }}
                className={`min-w-[300px] xl:min-w-[320px] snap-start flex-shrink-0 rounded-2xl border p-3 flex flex-col gap-2.5 transition-colors ${
                  isDropTarget
                    ? 'border-cyan-400/60 bg-cyan-500/[0.06]'
                    : col.isToday
                      ? 'border-cyan-500/35 bg-[#12161F]'
                      : col.isPast
                        ? 'border-red-500/30 bg-[#191317]'
                        : 'border-[#23262D] bg-[#101217]'
                }`}
              >
                {/* Column Header */}
                <div className="space-y-2 pb-2 border-b border-white/[0.06]">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className={`text-sm font-black truncate ${col.isToday ? 'text-cyan-200' : col.isPast ? 'text-red-200' : 'text-white'}`}>
                        {col.title}
                      </h3>
                      <p className="text-[11px] text-slate-500 tabular-nums">{col.dateKey}</p>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded-lg border text-xs font-black tabular-nums flex-shrink-0 ${
                        total >= DAILY_TARGET_CAPACITY
                          ? 'bg-emerald-500/15 border-emerald-400/30 text-emerald-200'
                          : 'bg-white/[0.05] border-white/[0.1] text-slate-200'
                      }`}
                    >
                      {total}/{DAILY_TARGET_CAPACITY}
                    </span>
                  </div>

                  {/* Compact Stacked Status Bar */}
                  <div className="h-1.5 w-full rounded-full overflow-hidden flex bg-white/[0.06]" aria-hidden="true">
                    {total > 0 && (
                      <>
                        {col.statusCounts.posted > 0 && (
                          <div className="bg-emerald-400 h-full" style={{ width: `${(col.statusCounts.posted / total) * 100}%` }} />
                        )}
                        {col.statusCounts.scheduled_on_platform > 0 && (
                          <div className="bg-blue-400 h-full" style={{ width: `${(col.statusCounts.scheduled_on_platform / total) * 100}%` }} />
                        )}
                        {col.statusCounts.ready > 0 && (
                          <div className="bg-cyan-400 h-full" style={{ width: `${(col.statusCounts.ready / total) * 100}%` }} />
                        )}
                        {col.statusCounts.planned > 0 && (
                          <div className="bg-amber-400 h-full" style={{ width: `${(col.statusCounts.planned / total) * 100}%` }} />
                        )}
                        {col.statusCounts.issue > 0 && (
                          <div className="bg-red-400 h-full" style={{ width: `${(col.statusCounts.issue / total) * 100}%` }} />
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Cards List */}
                <div className="space-y-2.5 flex-1">
                  {col.items.length === 0 ? (
                    <div className="py-8 px-3 text-center rounded-xl border border-dashed border-white/[0.08] text-xs text-slate-500">
                      ยังไม่มีคิวในวันนี้
                    </div>
                  ) : (
                    col.items.map((item) => {
                      const { time } = localParts(item.scheduled_at);
                      const thumbUrl = resolveCoverThumb(item);
                      const draggable = canDragQueueItem(item);
                      const isBusy = busyIds.has(item.id);
                      const isEditingTime = editingItemId === item.id;
                      const canPrepare = item.status === 'planned' || item.status === 'failed';
                      const canPostNow =
                        item.status === 'planned' ||
                        item.status === 'failed' ||
                        item.status === 'ready_for_extension';
                      const canEditTime = item.status !== 'posted';

                      return (
                        <article
                          key={item.id}
                          draggable={draggable}
                          onDragStart={() => {
                            if (draggable) setDraggedId(item.id);
                          }}
                          onDragEnd={() => {
                            setDraggedId(null);
                            setDragOverDate(null);
                          }}
                          className={`rounded-xl border border-white/[0.08] bg-[#161922] p-2.5 space-y-2 transition-colors ${
                            draggable ? 'hover:border-cyan-400/35' : ''
                          } ${draggedId === item.id ? 'opacity-50' : ''}`}
                        >
                          {/* Top Row: Time + Status Badge */}
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5 min-w-0">
                              {draggable && (
                                <GripVertical className="w-3.5 h-3.5 text-slate-500 flex-shrink-0 cursor-grab" />
                              )}
                              <span className="text-sm font-black text-white tabular-nums">{time}</span>
                            </div>
                            <span
                              className={`px-2 py-0.5 rounded-md border text-[10px] font-bold truncate ${
                                STATUS_BADGE_STYLES[item.status] || STATUS_BADGE_STYLES.planned
                              }`}
                            >
                              {STATUS_LABELS[item.status] || item.status}
                            </span>
                          </div>

                          {/* Body: 3:4 Thumbnail + Product/EP + Hook */}
                          <div className="flex gap-2.5">
                            <div className="w-12 aspect-[3/4] rounded-lg overflow-hidden bg-black/50 border border-white/[0.08] flex-shrink-0 flex items-center justify-center">
                              {thumbUrl ? (
                                <img
                                  src={thumbUrl}
                                  alt={item.hook_title || item.product_name || 'ปกคลิป'}
                                  loading="lazy"
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <ImageIcon className="w-4 h-4 text-slate-600" />
                              )}
                            </div>
                            <div className="min-w-0 flex-1 space-y-1">
                              <p className="text-[11px] font-bold text-cyan-200 truncate">
                                {formatEpisodeLabel(item)}
                              </p>
                              <p className="text-xs font-semibold text-slate-100 line-clamp-2 leading-snug">
                                {item.hook_title || item.caption || item.project_name || 'ไม่มีหัวข้อ'}
                              </p>
                            </div>
                          </div>

                          {/* Inline Time Editor */}
                          {isEditingTime && (
                            <div className="flex items-center gap-1.5 pt-1">
                              <select
                                value={editingTime}
                                onChange={(e) => setEditingTime(e.target.value)}
                                className="flex-1 px-2 py-1 rounded-lg bg-black/60 border border-white/[0.15] text-xs text-white font-bold tabular-nums"
                              >
                                {timeOptions.map((opt) => (
                                  <option key={opt} value={opt}>
                                    {opt}
                                  </option>
                                ))}
                              </select>
                              <button
                                type="button"
                                onClick={() => void handleSaveInlineTime(item)}
                                className="px-2.5 py-1 rounded-lg bg-cyan-400 text-slate-950 text-[11px] font-black cursor-pointer"
                              >
                                บันทึก
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingItemId(null)}
                                className="px-2 py-1 rounded-lg bg-white/[0.06] text-slate-300 text-[11px] font-bold cursor-pointer"
                              >
                                ยกเลิก
                              </button>
                            </div>
                          )}

                          {/* Quick Actions */}
                          {(canPrepare || canPostNow || canEditTime) && (
                            <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-white/[0.06]">
                              {canPrepare && (
                                <button
                                  type="button"
                                  disabled={isBusy}
                                  onClick={() => void withItemBusy(item.id, () => onPrepareItem?.(item, { intent: 'schedule' }))}
                                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-400/30 text-cyan-200 text-[11px] font-bold transition-colors cursor-pointer disabled:opacity-50"
                                >
                                  <Rocket className="w-3 h-3" />
                                  <span>เตรียมส่ง</span>
                                </button>
                              )}
                              {canPostNow && (
                                <button
                                  type="button"
                                  disabled={isBusy}
                                  onClick={() => void withItemBusy(item.id, () => onPrepareItem?.(item, { intent: 'post_now' }))}
                                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-400/30 text-emerald-200 text-[11px] font-bold transition-colors cursor-pointer disabled:opacity-50"
                                >
                                  <Send className="w-3 h-3" />
                                  <span>โพสต์เลย</span>
                                </button>
                              )}
                              {canEditTime && (
                                <button
                                  type="button"
                                  disabled={isBusy}
                                  onClick={() => {
                                    setEditingTime(time);
                                    setEditingItemId(isEditingTime ? null : item.id);
                                  }}
                                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 text-[11px] font-bold transition-colors cursor-pointer disabled:opacity-50"
                                >
                                  <CalendarClock className="w-3 h-3" />
                                  <span>แก้เวลา</span>
                                </button>
                              )}
                            </div>
                          )}
                        </article>
                      );
                    })
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
