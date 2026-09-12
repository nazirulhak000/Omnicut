import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, CircleDot, FileEdit, Rocket, Trash2 } from 'lucide-react';
import { getProducts } from '../../api';
import { filterActiveProjects } from '../../lib/editorEntry';

const STATUS_LABEL = {
  scripted: 'ร่างสคริปต์',
  in_production: 'กำลังตัดต่อ',
  rendered: 'ตัดเสร็จแล้ว',
  posted: 'โพสต์แล้ว',
};

// Status is the first thing this list needs to convey -- text alone reads
// slowly in a list this dense, so each row also gets a color + icon that
// don't depend on each other (color for a glance, icon for anyone who can't
// tell them apart).
const STATUS_STYLE = {
  scripted: {
    icon: FileEdit,
    row: 'border-transparent',
    icon_color: 'text-slate-500',
    label_color: 'text-slate-400',
  },
  in_production: {
    icon: CircleDot,
    row: 'border-amber-500/30 bg-amber-500/[0.06]',
    icon_color: 'text-amber-400',
    label_color: 'text-amber-300',
  },
  rendered: {
    icon: Check,
    row: 'border-sky-500/30 bg-sky-500/[0.06]',
    icon_color: 'text-sky-400',
    label_color: 'text-sky-300',
  },
  posted: {
    icon: Rocket,
    row: 'border-emerald-500/30 bg-emerald-500/[0.06]',
    icon_color: 'text-emerald-400',
    label_color: 'text-emerald-300',
  },
};

/**
 * Project picker with a required-cover-style project list: every project has
 * a manifest (GET /api/projects) but only ones tied to a product angle carry
 * a status -- joined here by project_name against a fresh product fetch,
 * fetched once on mount and again each time the dropdown opens so a status
 * change made elsewhere (e.g. marking posted from Tracker in another tab)
 * shows up without needing a full page reload.
 *
 * Posted projects are hidden by default: once a clip is posted, its
 * 03_Projects folder is usually a project the user is done with, and this
 * list otherwise grows forever. "แสดงทั้งหมด" un-hides them for the rare
 * case of wanting to re-open or delete one on purpose.
 */
export default function ProjectSelector({ projectName, projectList = [], loadProject, onRequestDelete }) {
  const [open, setOpen] = useState(false);
  const [statusByProject, setStatusByProject] = useState({});
  const wrapRef = useRef(null);
  const buttonRef = useRef(null);

  const refreshStatuses = () => {
    getProducts()
      .then((res) => {
        const list = Array.isArray(res) ? res : (res?.products || []);
        const map = {};
        for (const p of list) {
          for (const a of (p.angles || [])) {
            if (a.project_name) map[a.project_name] = a.status;
          }
        }
        setStatusByProject(map);
      })
      .catch(() => {});
  };

  useEffect(() => { refreshStatuses(); }, []);

  useEffect(() => {
    if (!open) return undefined;
    refreshStatuses();
    const onDown = (e) => { if (!wrapRef.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const decorated = useMemo(
    () => projectList.map((p) => ({ ...p, status: statusByProject[p.project_name] })),
    [projectList, statusByProject]
  );
  // Zero-Risk Studio Lockout: Exclude posted projects completely from editor dropdown
  const visible = useMemo(
    () => filterActiveProjects(decorated, statusByProject),
    [decorated, statusByProject]
  );

  const current = projectList.find((p) => p.project_name === projectName);

  return (
    <div ref={wrapRef} className="relative min-w-0 flex-1 sm:max-w-[420px]">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="โปรเจกต์ที่กำลังแก้"
        className="flex h-9 w-full min-w-0 cursor-pointer items-center gap-1 truncate rounded-xl border border-transparent bg-transparent pl-1 pr-2 text-base font-bold text-white hover:border-white/[0.12] hover:bg-black/40 focus:border-[#D97757] focus:outline-none"
      >
        <span className="truncate">{current ? current.project_name : '— เลือกโปรเจกต์ —'}</span>
        <ChevronDown className="h-4 w-4 flex-shrink-0 text-slate-500" />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-0 top-full z-40 mt-1.5 max-h-96 w-full min-w-[320px] overflow-y-auto rounded-xl border border-white/[0.1] bg-[#0F1420] p-1.5 shadow-2xl"
        >
          {visible.length === 0 && (
            <p className="px-2.5 py-3 text-center text-sm text-slate-500">ไม่มีโปรเจกต์ที่กำลังตัดต่อ</p>
          )}

          {visible.map((p) => {
            const style = STATUS_STYLE[p.status] || STATUS_STYLE.scripted;
            const StatusIcon = style.icon;
            const isCurrent = p.project_name === projectName;
            return (
            <div
              key={p.project_name}
              role="option"
              aria-selected={isCurrent}
              className={`group flex w-full items-center gap-1.5 rounded-lg border pl-2 pr-1 transition-colors ${style.row} ${
                isCurrent ? 'ring-1 ring-inset ring-[#E89274]' : ''
              }`}
            >
              <button
                type="button"
                onClick={() => { loadProject(p.project_name); setOpen(false); }}
                className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 py-2 text-left"
              >
                <StatusIcon className={`h-4 w-4 flex-shrink-0 ${style.icon_color}`} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-bold text-white">{p.project_name}</span>
                  {p.status && (
                    <span className={`block text-xs font-semibold ${style.label_color}`}>{STATUS_LABEL[p.status] || p.status}</span>
                  )}
                </span>
              </button>
              <button
                type="button"
                onClick={() => { setOpen(false); onRequestDelete?.(p.project_name); }}
                title="ลบโปรเจกต์นี้..."
                aria-label={`ลบโปรเจกต์ ${p.project_name}`}
                className="flex h-7 w-7 flex-shrink-0 cursor-pointer items-center justify-center rounded-lg text-slate-600 opacity-0 transition-colors hover:bg-rose-500/15 hover:text-rose-300 focus:opacity-100 focus-visible:ring-2 focus-visible:ring-rose-400 group-hover:opacity-100"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
