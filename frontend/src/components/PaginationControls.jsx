import React, { useMemo } from 'react';

const buildPageWindow = (page, totalPages) => {
  const start = Math.max(1, Math.min(page - 2, totalPages - 4));
  const end = Math.min(totalPages, start + 4);
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
};

export default function PaginationControls({
  page,
  pageSize,
  totalItems,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50],
  itemLabel = 'รายการ',
  disabled = false,
}) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const pages = useMemo(() => buildPageWindow(page, totalPages), [page, totalPages]);
  const firstItem = totalItems === 0 ? 0 : ((page - 1) * pageSize) + 1;
  const lastItem = Math.min(page * pageSize, totalItems);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-2 pt-3 border-t border-white/[0.06]">
      <div className="flex items-center gap-2 text-[11px] text-slate-500">
        <span>{totalItems === 0 ? `ไม่พบ${itemLabel}` : `แสดง ${firstItem}-${lastItem} จาก ${totalItems} ${itemLabel}`}</span>
        {onPageSizeChange && (
          <label className="inline-flex items-center gap-1.5 whitespace-nowrap">
            <span>ต่อหน้า</span>
            <select
              value={pageSize}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
              disabled={disabled}
              className="rounded-lg bg-black/30 border border-white/[0.1] px-1.5 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-[#25F4EE]/50 disabled:opacity-50"
              aria-label={`จำนวน${itemLabel}ต่อหน้า`}
            >
              {pageSizeOptions.map((size) => <option key={size} value={size}>{size}</option>)}
            </select>
          </label>
        )}
      </div>

      <nav className="flex items-center gap-1" aria-label={`หน้า${itemLabel}`}>
        <button
          type="button"
          onClick={() => onPageChange(1)}
          disabled={disabled || page <= 1}
          className="px-2 py-1.5 rounded-lg border border-white/[0.1] text-xs text-slate-300 hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="หน้าแรก"
        >
          «
        </button>
        <button
          type="button"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={disabled || page <= 1}
          className="px-2.5 py-1.5 rounded-lg border border-white/[0.1] text-xs text-slate-300 hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="หน้าก่อนหน้า"
        >
          ‹
        </button>
        {pages.map((pageNumber) => (
          <button
            key={pageNumber}
            type="button"
            onClick={() => onPageChange(pageNumber)}
            disabled={disabled && pageNumber === page}
            aria-current={pageNumber === page ? 'page' : undefined}
            className={`min-w-8 px-2 py-1.5 rounded-lg border text-xs font-bold transition-colors ${
              pageNumber === page
                ? 'border-[#25F4EE]/50 bg-[#25F4EE]/15 text-[#25F4EE]'
                : 'border-white/[0.1] text-slate-300 hover:bg-white/[0.08]'
            } disabled:opacity-50`}
          >
            {pageNumber}
          </button>
        ))}
        <button
          type="button"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={disabled || page >= totalPages}
          className="px-2.5 py-1.5 rounded-lg border border-white/[0.1] text-xs text-slate-300 hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="หน้าถัดไป"
        >
          ›
        </button>
        <button
          type="button"
          onClick={() => onPageChange(totalPages)}
          disabled={disabled || page >= totalPages}
          className="px-2 py-1.5 rounded-lg border border-white/[0.1] text-xs text-slate-300 hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="หน้าสุดท้าย"
        >
          »
        </button>
      </nav>
    </div>
  );
}
