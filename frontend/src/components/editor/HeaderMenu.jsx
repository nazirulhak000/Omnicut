import React, { useEffect, useRef, useState } from 'react';
import { MoreHorizontal } from 'lucide-react';

/**
 * The header's overflow menu.
 *
 * Everything that is set once (interface size) or reached rarely (reload,
 * delete) lives here so the bar itself can carry only what a cut actually
 * needs. Items are given as data rather than children so the destructive one
 * can be pushed to the end behind a divider without every caller remembering
 * to do it.
 *
 * items: [{ id, label, hint, icon, onSelect, disabled, danger, render }]
 *   render -- for an item that is a control rather than a command (the size
 *   switch); it is drawn in place and the menu does not close on click.
 */
export default function HeaderMenu({ items = [], label = 'เมนูเพิ่มเติม' }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const buttonRef = useRef(null);

  // Close on outside click and on Escape, and hand focus back to the button --
  // a menu that cannot be dismissed by either is a trap.
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();     // Esc in the editor also exits zen mode
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey, true);
    };
  }, [open]);

  const commands = items.filter((i) => !i.danger);
  const dangers = items.filter((i) => i.danger);

  const renderItem = (item) => {
    if (item.render) {
      return (
        <div key={item.id} className="px-2 py-1.5">
          {item.hint && <span className="mb-1 block text-xs text-slate-500">{item.hint}</span>}
          {item.render()}
        </div>
      );
    }
    const Icon = item.icon;
    return (
      <button
        key={item.id}
        type="button"
        role="menuitem"
        disabled={item.disabled}
        onClick={() => { setOpen(false); item.onSelect?.(); }}
        className={`flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-left text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
          item.disabled
            ? 'cursor-not-allowed text-slate-600'
            : item.danger
              ? 'cursor-pointer text-rose-300 hover:bg-rose-500/15'
              : 'cursor-pointer text-slate-200 hover:bg-white/[0.07] hover:text-white'
        }`}
      >
        {Icon && <Icon className="h-4 w-4 flex-shrink-0" />}
        <span className="truncate">{item.label}</span>
      </button>
    );
  };

  return (
    <div ref={wrapRef} className="relative flex-shrink-0">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        title={label}
        className={`flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border border-white/[0.08] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
          open ? 'bg-white/[0.12] text-white' : 'bg-white/[0.05] text-slate-300 hover:bg-white/[0.1] hover:text-white'
        }`}
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-40 mt-1.5 w-60 space-y-0.5 rounded-xl border border-white/[0.1] bg-[#0F1420] p-1.5 shadow-2xl"
        >
          {commands.map(renderItem)}
          {dangers.length > 0 && commands.length > 0 && (
            <div className="my-1 border-t border-white/[0.08]" />
          )}
          {dangers.map(renderItem)}
        </div>
      )}
    </div>
  );
}
