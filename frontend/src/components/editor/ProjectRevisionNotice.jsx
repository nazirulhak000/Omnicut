import React from 'react';
import { AlertTriangle } from 'lucide-react';

// Shown when the server's copy of the project moved on while this editor
// still holds edits the server will not accept (HTTP 409), or when a render
// rewrote the project while the user kept editing. Nothing is replaced until
// the user picks "reload".
const COPY = {
  conflict: 'บันทึกไม่ได้ เพราะโปรเจกต์ถูกแก้จากที่อื่น (เช่น งานเรนเดอร์หรืออีกแท็บ) การแก้ที่ยังไม่บันทึกจะหายถ้าปิดหน้านี้',
  'render-dirty': 'เรนเดอร์เสร็จแล้ว และโปรเจกต์บนเซิร์ฟเวอร์ถูกปรับระหว่างที่คุณแก้ต่อ การแก้ล่าสุดจะบันทึกไม่ได้จนกว่าจะโหลดโปรเจกต์ใหม่',
};

export default function ProjectRevisionNotice({ kind, reloading, onReload, onDismiss }) {
  if (!kind || !COPY[kind]) return null;
  return (
    <div
      role="alert"
      className="flex flex-shrink-0 flex-wrap items-center gap-2 border-b border-amber-500/25 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-200"
    >
      <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
      <span className="min-w-0 flex-1">{COPY[kind]}</span>
      <button
        type="button"
        onClick={onReload}
        disabled={reloading}
        className="rounded-md border border-amber-400/40 bg-amber-500/20 px-2 py-1 font-semibold text-amber-100 hover:bg-amber-500/30 disabled:opacity-50"
      >
        {reloading ? 'กำลังโหลดโปรเจกต์ใหม่' : 'โหลดโปรเจกต์ใหม่ (ทิ้งการแก้ที่ยังไม่บันทึก)'}
      </button>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-md border border-white/10 px-2 py-1 text-amber-100/80 hover:bg-white/5"
        >
          คงการแก้ไว้ก่อน
        </button>
      )}
    </div>
  );
}
