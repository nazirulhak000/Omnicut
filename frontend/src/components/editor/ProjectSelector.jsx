import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, CircleDot, FileEdit, Rocket, Search, Trash2, X } from 'lucide-react';
import { getProducts } from '../../api';
import { filterActiveProjects, filterProjectsByTab, countProjectsByTab } from '../../lib/editorEntry';
import { getRelativeTime, formatFullDateTime } from '../../lib/dateUtils';
import PaginationControls from '../PaginationControls';

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
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTab, setFilterTab] = useState('active'); // 'active' | 'rendered' | 'all'
  const [projectPage, setProjectPage] = useState(1);
  const [projectPageSize, setProjectPageSize] = useState(20);
  const wrapRef = useRef(null);
  const buttonRef = useRef(null);
  const searchInputRef = useRef(null);

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

  const decorated = useMemo(
    () => projectList.map((p) => ({ ...p, status: statusByProject[p.project_name] })),
    [projectList, statusByProject]
  );
  // Zero-Risk Studio Lockout: Exclude posted projects completely from editor dropdown
  const visible = useMemo(
    () => filterActiveProjects(decorated, statusByProject),
    [decorated, statusByProject]
  );

  const counts = useMemo(() => countProjectsByTab(visible), [visible]);

  useEffect(() => {
    if (!open) {
      setSearchQuery('');
      setProjectPage(1);
      return undefined;
    }
    refreshStatuses();
    // Always default to 'active' ('กำลังตัดต่อ') to keep editor dropdown clean and focused
    setFilterTab('active');
    const timer = setTimeout(() => {
      searchInputRef.current?.focus();
    }, 50);

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
      clearTimeout(timer);
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey, true);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const tabFiltered = useMemo(
    () => filterProjectsByTab(visible, filterTab),
    [visible, filterTab]
  );

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return tabFiltered;
    const q = searchQuery.trim().toLowerCase();
    return tabFiltered.filter((p) => {
      const nameMatch = p.project_name?.toLowerCase().includes(q);
      const statusLabel = STATUS_LABEL[p.status] || p.status || '';
      const statusMatch = statusLabel.toLowerCase().includes(q);
      return nameMatch || statusMatch;
    });
  }, [tabFiltered, searchQuery]);

  const searchMatchesInAll = useMemo(() => {
    if (!searchQuery.trim() || filterTab === 'all') return 0;
    const q = searchQuery.trim().toLowerCase();
    return visible.filter((p) => {
      const nameMatch = p.project_name?.toLowerCase().includes(q);
      const statusLabel = STATUS_LABEL[p.status] || p.status || '';
      const statusMatch = statusLabel.toLowerCase().includes(q);
      return nameMatch || statusMatch;
    }).length;
  }, [visible, searchQuery, filterTab]);

  const displayed = useMemo(() => {
    return filtered.slice((projectPage - 1) * projectPageSize, projectPage * projectPageSize);
  }, [filtered, projectPage, projectPageSize]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filtered.length / projectPageSize));
    setProjectPage((page) => Math.min(page, totalPages));
  }, [filtered.length, projectPageSize]);

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
          className="absolute left-0 top-full z-40 mt-1.5 flex max-h-[460px] w-full min-w-[340px] flex-col rounded-xl border border-white/[0.1] bg-[#0F1420] p-1.5 shadow-2xl backdrop-blur-xl"
        >
          {/* Quick Search Header */}
          <div className="mb-1.5 flex-shrink-0 px-0.5">
            <div className="relative flex items-center">
              <Search className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-slate-400" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setProjectPage(1);
                }}
                placeholder="ค้นหาชื่อโปรเจกต์..."
                aria-label="ค้นหาโปรเจกต์"
                className="w-full rounded-lg border border-white/10 bg-black/40 py-1.5 pl-8 pr-7 text-xs text-white placeholder-slate-500 focus:border-[#D97757] focus:outline-none"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    searchInputRef.current?.focus();
                  }}
                  className="absolute right-2 text-slate-400 hover:text-white"
                  title="ล้างคำค้นหา"
                  aria-label="ล้างคำค้นหา"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Status Filter Tabs */}
          <div className="mb-1.5 flex items-center gap-1 px-0.5 border-b border-white/[0.08] pb-1.5 flex-shrink-0" role="tablist" aria-label="กรองสถานะโปรเจกต์">
            <button
              type="button"
              role="tab"
              aria-selected={filterTab === 'active'}
              onClick={() => { setFilterTab('active'); setProjectPage(1); }}
              className={`flex-1 flex items-center justify-center gap-1 py-1 px-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                filterTab === 'active'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05] border border-transparent'
              }`}
              title="แสดงเฉพาะงานที่กำลังตัดต่อ / ร่างสคริปต์"
            >
              <CircleDot className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">กำลังตัดต่อ</span>
              <span className={`text-[10px] font-mono px-1 rounded-full ${
                filterTab === 'active' ? 'bg-amber-500/30 text-amber-200' : 'bg-white/[0.08] text-slate-400'
              }`}>
                {counts.active}
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={filterTab === 'rendered'}
              onClick={() => { setFilterTab('rendered'); setProjectPage(1); }}
              className={`flex-1 flex items-center justify-center gap-1 py-1 px-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                filterTab === 'rendered'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05] border border-transparent'
              }`}
              title="แสดงงานที่เรนเดอร์ตัดต่อเสร็จแล้ว"
            >
              <Check className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">ตัดเสร็จแล้ว</span>
              <span className={`text-[10px] font-mono px-1 rounded-full ${
                filterTab === 'rendered' ? 'bg-sky-500/30 text-sky-200' : 'bg-white/[0.08] text-slate-400'
              }`}>
                {counts.rendered}
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={filterTab === 'all'}
              onClick={() => { setFilterTab('all'); setProjectPage(1); }}
              className={`flex-none flex items-center justify-center gap-1 py-1 px-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                filterTab === 'all'
                  ? 'bg-white/[0.15] text-white border border-white/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05] border border-transparent'
              }`}
              title="แสดงโปรเจกต์ทั้งหมด"
            >
              <span>ทั้งหมด</span>
              <span className={`text-[10px] font-mono px-1 rounded-full ${
                filterTab === 'all' ? 'bg-white/20 text-white' : 'bg-white/[0.08] text-slate-400'
              }`}>
                {counts.all}
              </span>
            </button>
          </div>

          {/* Scrollable Project Items */}
          <div className="flex-1 space-y-1 overflow-y-auto pr-0.5 max-h-80">
            {visible.length === 0 && (
              <p className="px-2.5 py-6 text-center text-sm text-slate-500">ไม่มีโปรเจกต์ในระบบ</p>
            )}

            {visible.length > 0 && tabFiltered.length === 0 && !searchQuery && (
              filterTab === 'active' ? (
                <div className="px-3 py-6 text-center text-xs">
                  <CircleDot className="w-6 h-6 mx-auto mb-2 text-slate-500 opacity-60" />
                  <p className="text-slate-300 font-bold mb-1">ไม่มีงานที่กำลังตัดต่อ</p>
                  <p className="text-slate-500 mb-3 text-[11px]">งานทั้งหมดถูกเรนเดอร์เสร็จแล้ว ({counts.rendered} โปรเจกต์)</p>
                  {counts.rendered > 0 && (
                    <button
                      type="button"
                      onClick={() => { setFilterTab('rendered'); setProjectPage(1); }}
                      className="px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 text-sky-300 font-bold text-xs cursor-pointer transition-colors inline-flex items-center gap-1.5"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>ดูงานที่ตัดเสร็จแล้ว</span>
                    </button>
                  )}
                </div>
              ) : filterTab === 'rendered' ? (
                <div className="px-3 py-6 text-center text-xs">
                  <Check className="w-6 h-6 mx-auto mb-2 text-slate-500 opacity-60" />
                  <p className="text-slate-300 font-bold mb-1">ยังไม่มีงานที่ตัดเสร็จแล้ว</p>
                  <p className="text-slate-500 mb-3 text-[11px]">มีงานกำลังตัดต่ออยู่ {counts.active} โปรเจกต์</p>
                  {counts.active > 0 && (
                    <button
                      type="button"
                      onClick={() => { setFilterTab('active'); setProjectPage(1); }}
                      className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 font-bold text-xs cursor-pointer transition-colors inline-flex items-center gap-1.5"
                    >
                      <CircleDot className="w-3.5 h-3.5" />
                      <span>ดูงานกำลังตัดต่อ</span>
                    </button>
                  )}
                </div>
              ) : null
            )}

            {visible.length > 0 && displayed.length === 0 && searchQuery && (
              <div className="px-3 py-6 text-center text-xs">
                <p className="text-slate-300 font-semibold mb-1">
                  ไม่พบโปรเจกต์ที่ตรงกับ &ldquo;{searchQuery}&rdquo;
                </p>
                {searchMatchesInAll > 0 && filterTab !== 'all' ? (
                  <button
                    type="button"
                    onClick={() => { setFilterTab('all'); setProjectPage(1); }}
                    className="mt-2 px-3 py-1.5 rounded-lg bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/35 text-[#25F4EE] font-bold text-xs cursor-pointer transition-colors inline-flex items-center gap-1"
                  >
                    <span>ค้นหาใน &ldquo;ทั้งหมด&rdquo; ({searchMatchesInAll} รายการ)</span>
                  </button>
                ) : (
                  <p className="text-slate-500 text-[11px] mt-1">ลองเปลี่ยนคำค้นหา หรือตรวจการสะกดคำ</p>
                )}
              </div>
            )}

            {displayed.map((p) => {
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
                      <span className="flex items-center gap-1.5 text-xs">
                        {p.status && (
                          <span className={`font-semibold ${style.label_color}`}>{STATUS_LABEL[p.status] || p.status}</span>
                        )}
                        {p.updated_at && (
                          <span
                            className="text-slate-400 font-normal truncate"
                            title={formatFullDateTime(p.updated_at)}
                          >
                            {p.status ? `· ${getRelativeTime(p.updated_at)}` : getRelativeTime(p.updated_at)}
                          </span>
                        )}
                      </span>
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

          {/* Footer Pagination / Status Bar */}
          {filtered.length > 0 && (
            <div className="mt-1.5 border-t border-white/10 pt-1.5 px-1.5">
              <PaginationControls
                page={projectPage}
                pageSize={projectPageSize}
                totalItems={filtered.length}
                onPageChange={setProjectPage}
                itemLabel="โปรเจกต์"
                compact={true}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
