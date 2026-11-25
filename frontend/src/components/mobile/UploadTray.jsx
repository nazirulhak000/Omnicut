import React, { useState, useEffect } from 'react';
import {
  Upload, Pause, Play, RefreshCw, Trash2, X, ChevronDown, ChevronUp,
  Loader2, WifiOff, CheckCircle2, AlertCircle, Clock
} from 'lucide-react';
import { uploadQueue } from '../../lib/uploadQueue';

function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function getStatusBadge(status) {
  switch (status) {
    case 'uploading':
    case 'queued':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30">
          <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0" />
          <span>กำลังส่งข้อมูล</span>
        </span>
      );
    case 'paused':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
          <Pause className="w-3.5 h-3.5 flex-shrink-0" />
          <span>พักชั่วคราว</span>
        </span>
      );
    case 'interrupted':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-orange-500/15 text-orange-300 border border-orange-500/30 animate-pulse">
          <WifiOff className="w-3.5 h-3.5 flex-shrink-0" />
          <span>รอสัญญาณเน็ต</span>
        </span>
      );
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
          <span>อัปโหลดสำเร็จ</span>
        </span>
      );
    case 'error':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>ส่งไม่สำเร็จ</span>
        </span>
      );
    default:
      return null;
  }
}

export default function UploadTray() {
  const [items, setItems] = useState(() => uploadQueue.getSnapshot());
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    return uploadQueue.subscribe((snapshot) => {
      setItems(snapshot);
    });
  }, []);

  if (!items || items.length === 0) {
    return null;
  }

  const activeCount = items.filter(
    (i) => i.status === 'uploading' || i.status === 'queued' || i.status === 'interrupted'
  ).length;
  const isAllCompleted = items.every((i) => i.status === 'completed');

  return (
    <aside
      aria-label="แถบสถานะการอัปโหลดไฟล์"
      className="fixed z-50 left-3 right-3 sm:left-auto sm:right-6 sm:w-[420px] bottom-[calc(var(--nav-h,64px)+env(safe-area-inset-bottom,0px)+8px)] motion-press duration-300 animate-slideUp"
    >
      <div className="bg-[#0A0D14]/95 backdrop-blur-2xl border border-white/[0.14] rounded-2xl shadow-2xl overflow-hidden text-white flex flex-col">
        {/* Tray Header */}
        <div className="flex items-center justify-between px-3.5 py-2.5 bg-black/40 border-b border-white/[0.08]">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-[#25F4EE]/10 border border-[#25F4EE]/30 flex items-center justify-center text-[#25F4EE] flex-shrink-0">
              <Upload className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h3 className="text-xs font-bold truncate flex items-center gap-1.5">
                <span>{isAllCompleted ? 'อัปโหลดเสร็จสิ้นทั้งหมด' : 'รายการอัปโหลด'}</span>
                <span className="font-mono text-[11px] px-1.5 py-0.2 rounded bg-white/[0.08] text-slate-300">
                  {items.length}
                </span>
              </h3>
              {activeCount > 0 && (
                <p className="text-[10px] text-cyan-300/80 truncate">
                  กำลังประมวลผล {activeCount} รายการ (จอสว่างตลอดขณะส่ง)
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            {isAllCompleted && (
              <button
                type="button"
                onClick={() => uploadQueue.clearCompleted()}
                className="min-h-[44px] px-2.5 py-1 text-[11px] font-bold text-slate-400 hover:text-white rounded-lg hover:bg-white/[0.06] transition-colors cursor-pointer"
              >
                ล้างรายการ
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsExpanded((prev) => !prev)}
              aria-label={isExpanded ? 'ย่อแถบอัปโหลด' : 'ขยายแถบอัปโหลด'}
              className="min-h-[44px] min-w-[44px] flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.06] rounded-xl transition-colors cursor-pointer"
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Tray Body / Items List */}
        {isExpanded && (
          <div className="max-h-72 overflow-y-auto overscroll-contain p-2.5 space-y-2.5 no-scrollbar">
            {items.map((item) => {
              const isUploading = item.status === 'uploading' || item.status === 'queued';
              const isPaused = item.status === 'paused';
              const isInterrupted = item.status === 'interrupted';
              const isError = item.status === 'error';
              const isCompleted = item.status === 'completed';

              let barColor = 'bg-[#25F4EE]';
              if (isCompleted) barColor = 'bg-emerald-400';
              else if (isPaused) barColor = 'bg-amber-400';
              else if (isInterrupted) barColor = 'bg-orange-400';
              else if (isError) barColor = 'bg-rose-500';

              return (
                <div
                  key={item.localId}
                  className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-2.5"
                >
                  {/* Item Title & Status Badge */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-bold text-white truncate" title={item.filename}>
                        {item.filename}
                      </p>
                      <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                        {formatBytes(item.offset)} / {formatBytes(item.totalSize)} ({item.progress}%)
                      </p>
                    </div>
                    <div className="flex-shrink-0">
                      {getStatusBadge(item.status)}
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full h-1.5 bg-black/60 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${barColor} rounded-full transition-[width] duration-300 ease-linear relative overflow-hidden`}
                      style={{ width: `${Math.max(item.progress, item.status === 'uploading' ? 5 : 0)}%` }}
                    >
                      {isUploading && (
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full animate-shimmer" />
                      )}
                    </div>
                  </div>

                  {/* Error Message if any */}
                  {item.error && (
                    <div className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-lg p-2 leading-relaxed">
                      {item.error}
                    </div>
                  )}

                  {/* Action Buttons: Touch targets >= 44px */}
                  <div className="flex items-center justify-end gap-1.5 pt-1">
                    {/* Pause Button */}
                    {isUploading && (
                      <button
                        type="button"
                        onClick={() => uploadQueue.pause(item.localId)}
                        className="min-h-[44px] min-w-[44px] px-3 py-2 rounded-xl text-xs font-bold bg-white/[0.08] hover:bg-white/[0.14] text-white border border-white/[0.1] flex items-center justify-center gap-1.5 cursor-pointer motion-press active:duration-100 active:scale-95 disabled:active:scale-100"
                        title="พักการส่ง"
                      >
                        <Pause className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        <span>พักการส่ง</span>
                      </button>
                    )}

                    {/* Resume / Continue from point */}
                    {(isPaused || isInterrupted) && (
                      <button
                        type="button"
                        onClick={() => uploadQueue.resume(item.localId)}
                        className="min-h-[44px] min-w-[44px] px-3.5 py-2 rounded-xl text-xs font-bold bg-[#25F4EE] hover:bg-[#20ded8] text-slate-950 flex items-center justify-center gap-1.5 cursor-pointer motion-press active:duration-100 active:scale-95 disabled:active:scale-100 shadow-md shadow-[#25F4EE]/10"
                        title="ส่งต่อจากจุดเดิม"
                      >
                        <Play className="w-4 h-4 fill-current flex-shrink-0" />
                        <span>ส่งต่อจากจุดเดิม</span>
                      </button>
                    )}

                    {/* Retry Button */}
                    {isError && (
                      <button
                        type="button"
                        onClick={() => uploadQueue.retry(item.localId)}
                        className="min-h-[44px] min-w-[44px] px-3.5 py-2 rounded-xl text-xs font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 flex items-center justify-center gap-1.5 cursor-pointer motion-press active:duration-100 active:scale-95 disabled:active:scale-100 shadow-md"
                        title="ลองส่งใหม่"
                      >
                        <RefreshCw className="w-4 h-4 flex-shrink-0" />
                        <span>ลองส่งใหม่</span>
                      </button>
                    )}

                    {/* Remove from list */}
                    <button
                      type="button"
                      onClick={() => uploadQueue.remove(item.localId)}
                      className="min-h-[44px] min-w-[44px] px-3 py-2 rounded-xl text-xs font-bold bg-white/[0.04] hover:bg-rose-500/15 text-slate-400 hover:text-rose-300 border border-white/[0.08] hover:border-rose-500/30 flex items-center justify-center gap-1.5 cursor-pointer motion-press active:duration-100 active:scale-95 disabled:active:scale-100"
                      title="นำออกจากรายการ"
                    >
                      <Trash2 className="w-4 h-4 flex-shrink-0" />
                      <span>นำออกจากรายการ</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
