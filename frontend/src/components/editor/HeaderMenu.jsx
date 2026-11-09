import React, { useEffect, useRef, useState } from 'react';
import { MoreHorizontal } from 'lucide-react';

/**
 * The header's overflow menu.
 *
 * Everything that is set once (interface size, watermark) or reached rarely (reload,
 * delete, shortcuts) lives here so the bar itself can carry only what a cut actually
 * needs. Supports command buttons, dividers, section headers, and toggle switches.
 *
 * items: [{ id, label, hint, icon, onSelect, disabled, danger, render, type, checked, onChange, badge }]
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

  const hasExplicitStructure = items.some(
    (i) => i.divider || i.type === 'divider' || i.type === 'section'
  );
  const commands = items.filter((i) => !i.danger);
  const dangers = items.filter((i) => i.danger);

  const renderItem = (item) => {
    if (item.type === 'divider' || item.divider) {
      return <div key={item.id} className="my-1 border-t border-white/[0.08]" />;
    }

    if (item.type === 'section') {
      return (
        <div
          key={item.id}
          className="px-2.5 pt-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-500"
        >
          {item.label}
        </div>
      );
    }

    if (item.type === 'toggle') {
      const Icon = item.icon;
      return (
        <label
          key={item.id}
          className={`flex h-9 w-full items-center justify-between gap-2.5 rounded-lg px-2.5 text-left text-sm font-medium transition-colors select-none ${
            item.disabled
              ? 'cursor-not-allowed opacity-50'
              : 'cursor-pointer hover:bg-white/[0.07] text-slate-200 hover:text-white'
          }`}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            {Icon && <Icon className="h-4 w-4 flex-shrink-0 text-slate-400" />}
            <span className="truncate">{item.label}</span>
          </div>
          <input
            type="checkbox"
            checked={Boolean(item.checked)}
            disabled={item.disabled}
            onChange={(e) => item.onChange?.(e.target.checked)}
            className="h-3.5 w-3.5 rounded accent-[#D97757] cursor-pointer flex-shrink-0"
          />
        </label>
      );
    }

    if (item.render) {
      return (
        <div key={item.id} className="px-2 py-1.5">
          {item.hint && <span className="mb-1 block text-xs text-slate-500">{item.hint}</span>}
          {item.render()}
        </div>
      );
    }

    const Icon = item.icon;
    const button = (
      <button
        key={item.id}
        type="button"
        role="menuitem"
        disabled={item.disabled}
        onClick={() => {
          setOpen(false);
          item.onSelect?.();
        }}
        className={`flex h-9 w-full items-center justify-between gap-2.5 rounded-lg px-2.5 text-left text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
          item.disabled
            ? 'cursor-not-allowed text-slate-600'
            : item.danger
              ? 'cursor-pointer text-rose-300 hover:bg-rose-500/15'
              : 'cursor-pointer text-slate-200 hover:bg-white/[0.07] hover:text-white'
        }`}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          {Icon && <Icon className="h-4 w-4 flex-shrink-0" />}
          <span className="truncate">{item.label}</span>
        </div>
        {item.badge && (
          <span className="rounded-full bg-amber-500/20 px-1.5 py-0.2 text-[10px] font-mono font-bold text-amber-300 border border-amber-500/30">
            {item.badge}
          </span>
        )}
      </button>
    );
    // wrapClassName limits an item to some viewports (e.g. a fallback for a
    // header control that is hidden at that width).
    return item.wrapClassName
      ? <div key={item.id} className={item.wrapClassName}>{button}</div>
      : button;
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
        className={`flex h-8 sm:h-9 w-8 sm:w-9 cursor-pointer items-center justify-center rounded-xl border border-white/[0.08] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
          open ? 'bg-white/[0.12] text-white' : 'bg-white/[0.05] text-slate-300 hover:bg-white/[0.1] hover:text-white'
        }`}
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-40 mt-1.5 w-64 space-y-0.5 rounded-xl border border-white/[0.1] bg-[#0F1420] p-1.5 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100"
        >
          {hasExplicitStructure ? (
            items.map(renderItem)
          ) : (
            <>
              {commands.map(renderItem)}
              {dangers.length > 0 && commands.length > 0 && (
                <div className="my-1 border-t border-white/[0.08]" />
              )}
              {dangers.map(renderItem)}
            </>
          )}
        </div>
      )}
    </div>
  );
}
