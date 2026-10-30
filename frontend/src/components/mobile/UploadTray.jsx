import React, { useEffect, useState } from 'react';
import { uploadQueue } from '../../lib/uploadQueue';

function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return '0 MB';
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  const kb = bytes / 1024;
  return `${Math.round(kb)} KB`;
}

function getStatusBadge(status) {
  switch (status) {
    case 'uploading':
      return { text: 'กำลังส่งข้อมูล', className: 'bg-sky-500/20 text-sky-300 border-sky-500/40' };
    case 'paused':
      return { text: 'พักชั่วคราว', className: 'bg-amber-500/20 text-amber-300 border-amber-500/40' };
    case 'interrupted':
      return { text: 'รอสัญญาณเน็ต', className: 'bg-amber-500/20 text-amber-300 border-amber-500/40' };
    case 'completed':
      return { text: 'อัปโหลดสำเร็จ', className: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' };
    case 'error':
      return { text: 'ส่งไม่สำเร็จ', className: 'bg-rose-500/20 text-rose-300 border-rose-500/40' };
    default:
      return { text: 'รอคิวอัปโหลด', className: 'bg-slate-700 text-slate-300 border-slate-600' };
  }
}

export default function UploadTray({ queue = uploadQueue, defaultExpanded = false }) {
  const [items, setItems] = useState([]);
  const [expanded, setExpanded] = useState(defaultExpanded);

  useEffect(() => {
    const unsubscribe = queue.subscribe((snapshot) => {
      setItems(snapshot);
    });
    return unsubscribe;
  }, [queue]);

  if (!items || items.length === 0) {
    return null;
  }

  const activeCount = items.filter((i) => i.status === 'uploading' || i.status === 'queued').length;
  const totalProgress = Math.round(
    items.reduce((acc, i) => acc + (i.progress || 0), 0) / Math.max(1, items.length)
  );

  return (
    <div
      className="fixed inset-x-0 bottom-[calc(var(--nav-h,64px)+env(safe-area-inset-bottom,0px)+8px)] z-40 mx-auto max-w-lg px-3"
      role="region"
      aria-label="ถาดรายการอัปโหลดไฟล์"
    >
      <div className="overflow-hidden rounded-2xl border border-slate-700/80 bg-slate-900/95 text-slate-100 shadow-2xl backdrop-blur-md">
        {/* Header Bar */}
        <div className="flex items-center justify-between gap-2 px-4 py-2.5">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">
                {activeCount > 0
                  ? `กำลังอัปโหลด ${activeCount} ไฟล์ (${totalProgress}%)`
                  : `รายการอัปโหลดทั้งหมด ${items.length} ไฟล์`}
              </span>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-sky-400 transition-all duration-300"
                style={{ width: `${totalProgress}%` }}
              />
            </div>
          </div>

          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="min-h-[44px] min-w-[44px] rounded-xl bg-slate-800 px-3 text-sm font-medium text-slate-200 active:bg-slate-700"
          >
            {expanded ? 'ซ่อนรายการ' : 'ดูรายการ'}
          </button>
        </div>

        {/* Expanded Upload Items */}
        {expanded && (
          <div className="max-h-72 divide-y divide-slate-800 overflow-y-auto border-t border-slate-800 px-4 py-2">
            {items.map((item) => {
              const badge = getStatusBadge(item.status);
              return (
                <div key={item.localId} className="py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-100">{item.filename}</p>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {formatBytes(item.offset)} / {formatBytes(item.totalSize)} ({item.progress || 0}%)
                        {item.result?.deduplicated ? ' · ใช้ไฟล์เดิมที่มีอยู่แล้ว' : ''}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${badge.className}`}
                    >
                      {badge.text}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className={`h-full transition-all duration-200 ${
                        item.status === 'completed'
                          ? 'bg-emerald-400'
                          : item.status === 'error'
                          ? 'bg-rose-400'
                          : 'bg-sky-400'
                      }`}
                      style={{ width: `${item.progress || 0}%` }}
                    />
                  </div>

                  {item.error && (
                    <p className="mt-1.5 text-xs text-rose-300" role="alert">
                      {item.error}
                    </p>
                  )}

                  {/* Touch Action Buttons (>= 44px) */}
                  <div className="mt-2.5 flex flex-wrap items-center gap-2">
                    {(item.status === 'uploading' || item.status === 'queued') && (
                      <button
                        type="button"
                        onClick={() => queue.pause(item.localId)}
                        className="min-h-[44px] min-w-[44px] rounded-xl border border-slate-700 bg-slate-800 px-3.5 text-xs font-semibold text-slate-200 active:bg-slate-700"
                      >
                        พักการส่ง
                      </button>
                    )}

                    {(item.status === 'paused' || item.status === 'interrupted') && (
                      <button
                        type="button"
                        onClick={() => queue.resume(item.localId)}
                        className="min-h-[44px] min-w-[44px] rounded-xl bg-sky-500 px-3.5 text-xs font-semibold text-slate-950 active:bg-sky-400"
                      >
                        ส่งต่อจากจุดเดิม
                      </button>
                    )}

                    {item.status === 'error' && (
                      <button
                        type="button"
                        onClick={() => queue.retry(item.localId)}
                        className="min-h-[44px] min-w-[44px] rounded-xl bg-amber-500 px-3.5 text-xs font-semibold text-slate-950 active:bg-amber-400"
                      >
                        ลองส่งใหม่
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => queue.remove(item.localId)}
                      className="min-h-[44px] min-w-[44px] rounded-xl border border-slate-700/80 bg-transparent px-3.5 text-xs font-medium text-slate-400 active:bg-slate-800"
                    >
                      นำออกจากรายการ
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
