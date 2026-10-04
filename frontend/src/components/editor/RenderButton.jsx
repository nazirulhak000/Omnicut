import React, { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Loader2, Rocket, ShieldCheck } from 'lucide-react';

/**
 * Render, plus the quality it renders at.
 *
 * A split button rather than a button beside a dropdown: the quality select
 * was 190px of the header -- 38% of it at 500px wide -- for a setting changed
 * far less often than the button beside it is pressed. Folding it into the
 * caret keeps the two together (the caret answers "at what quality?" about
 * this exact action) and gives the width back.
 *
 * The two halves are separate buttons so pressing the main one can never open
 * the menu by accident.
 */
export default function RenderButton({
  presets,
  value,
  onChange,
  onRender,
  busy = false,
  progress = 0,
  disabled = false,
  needsCover = false,
  isPosted = false,
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const caretRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (!wrapRef.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setOpen(false);
        caretRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey, true);
    };
  }, [open]);

  if (isPosted) {
    return (
      <div className="relative flex flex-shrink-0">
        <button
          type="button"
          disabled
          title="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม"
          className="flex h-9 cursor-not-allowed items-center gap-1.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 px-3 text-sm font-bold text-emerald-400 opacity-80 sm:px-4"
        >
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span>โพสต์แล้ว (ล็อก)</span>
        </button>
      </div>
    );
  }

  const current = presets.find((p) => p.id === value) || presets[0];

  return (
    <div ref={wrapRef} className="relative flex flex-shrink-0">
      <button
        type="button"
        onClick={() => onRender?.()}
        disabled={disabled || busy}
        title={needsCover ? 'กรุณาสร้างและบันทึกหน้าปกก่อน Render' : `เรนเดอร์แบบ${current?.label || ''}`}
        className="flex h-9 cursor-pointer items-center gap-1.5 rounded-l-xl bg-[#D97757] px-3 text-sm font-bold text-white transition-colors hover:bg-[#C2683D] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E89274] disabled:cursor-not-allowed disabled:opacity-50 sm:px-4"
      >
        {busy
          ? <><Loader2 className="h-4 w-4 animate-spin" /><span>{progress}%</span></>
          : <><Rocket className="h-4 w-4" /><span>เรนเดอร์</span></>}
      </button>

      <button
        ref={caretRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={busy}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`คุณภาพที่จะเรนเดอร์: ${current?.label || ''}`}
        title={`คุณภาพ: ${current?.label || ''}`}
        className={`flex h-9 w-8 cursor-pointer items-center justify-center rounded-r-xl border-l border-black/25 text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E89274] disabled:cursor-not-allowed disabled:opacity-50 ${
          open ? 'bg-[#C2683D]' : 'bg-[#D97757] hover:bg-[#C2683D]'
        }`}
      >
        <ChevronDown className="h-4 w-4" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-40 mt-1.5 w-64 space-y-0.5 rounded-xl border border-white/[0.1] bg-[#0F1420] p-1.5 shadow-2xl"
        >
          <span className="block px-2.5 py-1 text-xs text-slate-500">คุณภาพที่จะเรนเดอร์</span>
          {presets.map((p) => (
            <button
              key={p.id}
              type="button"
              role="menuitemradio"
              aria-checked={p.id === value}
              onClick={() => { onChange?.(p.id); setOpen(false); }}
              className={`flex w-full cursor-pointer items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
                p.id === value ? 'bg-[#D97757]/15' : 'hover:bg-white/[0.07]'
              }`}
            >
              <Check className={`mt-0.5 h-4 w-4 flex-shrink-0 ${p.id === value ? 'text-[#E89274]' : 'text-transparent'}`} />
              <span className="min-w-0">
                <span className="block text-sm font-bold text-white">{p.label}</span>
                <span className="block text-xs leading-relaxed text-slate-400">{p.hint}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
