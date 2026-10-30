import React from 'react';
import { CloudOff, RefreshCw } from 'lucide-react';

function formatLastSeen(lastSeenAt) {
  if (!lastSeenAt) return null;
  try {
    const date = typeof lastSeenAt === 'number' ? new Date(lastSeenAt) : new Date(String(lastSeenAt));
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleTimeString('th-TH', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return null;
  }
}

export function ServerSleepingBanner({
  status = 'online',
  onRetry,
  lastSeenAt = null,
  mode = 'banner',
  retrying = false,
}) {
  const isSleepingOrOffline = status === 'sleeping' || status === 'offline';
  if (!isSleepingOrOffline) return null;

  const lastSeenText = formatLastSeen(lastSeenAt);
  const isCard = mode === 'card';

  return (
    <div
      role="alert"
      aria-live="assertive"
      data-testid="server-sleeping-banner"
      data-status={status}
      className={
        isCard
          ? 'w-full rounded-2xl border border-amber-500/30 bg-amber-950/40 p-5 text-amber-100 shadow-lg'
          : 'w-full rounded-xl border border-amber-500/30 bg-amber-950/60 px-4 py-3 text-amber-100'
      }
    >
      <div className={isCard ? 'flex flex-col gap-4' : 'flex flex-wrap items-center justify-between gap-3'}>
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-300">
            <CloudOff className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-bold text-amber-100">
              เซิร์ฟเวอร์ Colab หลับหรือขาดการเชื่อมต่อ
            </p>
            <p className="mt-0.5 text-xs text-amber-200/80">
              {status === 'sleeping'
                ? 'รันไทม์อาจหยุดพักชั่วคราว กรุณาปลุก Colab หรือตรวจสอบเครือข่ายแล้วเชื่อมต่อใหม่'
                : 'ไม่สามารถติดต่อเซิร์ฟเวอร์ได้ในขณะนี้ กรุณาตรวจสอบสัญญาณอินเทอร์เน็ตหรือสถานะเซิร์ฟเวอร์'}
              {lastSeenText ? ` (เชื่อมต่อล่าสุด ${lastSeenText})` : ''}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onRetry && onRetry()}
          disabled={retrying}
          data-testid="server-retry-button"
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-amber-300 active:scale-[0.99] disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 shrink-0 ${retrying ? 'animate-spin' : ''}`} aria-hidden="true" />
          <span>ลองเชื่อมต่อใหม่</span>
        </button>
      </div>
    </div>
  );
}

export default ServerSleepingBanner;
