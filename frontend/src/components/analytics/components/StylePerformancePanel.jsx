import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Layers, RefreshCw } from 'lucide-react';
import { getTiktokStylePerformance } from '../../../api';
import {
  MIN_RELIABLE_SAMPLE,
  STYLE_GROUPS,
  buildStylePerformanceRows,
  formatCompletionRate,
  formatWatchTime,
  maxMedianViews,
} from '../../../lib/stylePerformanceModel';

const fmtViews = (n) => {
  const v = Math.round(Number(n) || 0);
  if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M`;
  if (v >= 1000) return `${(v / 1000).toFixed(1)}K`;
  return String(v);
};

const NO_DATA = 'ยังไม่มีข้อมูล';

// Low-sample bars carry a stripe as well as a lighter fill, so "not enough
// data" never rests on colour alone.
const LOW_SAMPLE_FILL = 'repeating-linear-gradient(135deg, rgba(37,244,238,0.45) 0 3px, rgba(37,244,238,0.12) 3px 6px)';

function Metric({ label, value }) {
  return (
    <div className="min-w-0">
      <div className="text-[10px] text-slate-500 sm:hidden">{label}</div>
      <div className={`text-xs tabular-nums ${value == null ? 'text-slate-500' : 'text-slate-200'}`}>
        {value ?? NO_DATA}
      </div>
    </div>
  );
}

function GroupRow({ row, scale }) {
  const width = row.medianViews != null && scale > 0 ? Math.max(2, (row.medianViews / scale) * 100) : 0;
  const watch = formatWatchTime(row.avgWatchTimeSec);
  const completion = formatCompletionRate(row.completionRate);
  const detail = [
    `${row.label}: ${row.count} คลิปที่วัดผลแล้ว`,
    `มัธยฐานวิว ${row.medianViews != null ? Math.round(row.medianViews).toLocaleString('th-TH') : NO_DATA}`,
    `เวลาดูเฉลี่ย ${watch ?? NO_DATA}`,
    `ดูจบ ${completion ?? NO_DATA}`,
    row.lowSample ? `ข้อมูลน้อย (ต่ำกว่า ${MIN_RELIABLE_SAMPLE} คลิป) ยังเทียบกับกลุ่มอื่นไม่ได้` : null,
  ].filter(Boolean).join('\n');

  return (
    <li
      title={detail}
      className="grid grid-cols-2 sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1.6fr)_5.5rem_4.5rem] gap-x-3 gap-y-2 items-center px-3 py-2.5 rounded-xl hover:bg-white/[0.03] transition-colors"
    >
      <div className="col-span-2 sm:col-span-1 min-w-0">
        <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
          <span className={`text-xs font-bold truncate ${row.lowSample ? 'text-slate-300' : 'text-white'}`}>{row.label}</span>
          {row.isTop && (
            <span className="shrink-0 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-bold leading-none text-emerald-300">
              มัธยฐานวิวสูงสุด
            </span>
          )}
        </div>
        <div className="mt-0.5 flex items-center gap-1.5 min-w-0 text-[10px]">
          {row.lowSample ? (
            <span className="shrink-0 rounded border border-amber-500/30 bg-amber-500/10 px-1 py-0.5 font-semibold leading-none text-amber-300">
              ข้อมูลน้อย · {row.count} คลิป
            </span>
          ) : (
            <span className="shrink-0 tabular-nums text-slate-400">{row.count} คลิป</span>
          )}
          {row.sublabel && <span className="truncate text-slate-500">{row.sublabel}</span>}
        </div>
      </div>

      <div className="col-span-2 sm:col-span-1 flex items-center gap-2 min-w-0">
        <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-white/[0.05]" aria-hidden="true">
          {width > 0 && (
            <div
              className="absolute inset-y-0 left-0 rounded-r"
              style={{
                width: `${width}%`,
                background: row.lowSample ? LOW_SAMPLE_FILL : 'rgba(37,244,238,0.75)',
              }}
            />
          )}
        </div>
        <span className={`w-14 shrink-0 text-right text-xs tabular-nums ${row.medianViews == null ? 'text-slate-500' : 'font-semibold text-slate-100'}`}>
          {row.medianViews != null ? fmtViews(row.medianViews) : NO_DATA}
        </span>
      </div>

      <Metric label="เวลาดูเฉลี่ย" value={watch} />
      <Metric label="ดูจบ" value={completion} />
    </li>
  );
}

/**
 * "ผลตามสไตล์": measured results per style preset / hook style / story
 * format from /api/tiktok-stats/style-performance (channel scoped by the
 * shared transport, like every tiktok-stats call). Every row shows its sample
 * size; a group under MIN_RELIABLE_SAMPLE posts is labelled ข้อมูลน้อย and is
 * never marked as the best.
 */
export default function StylePerformancePanel() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [groupBy, setGroupBy] = useState(STYLE_GROUPS[0].id);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await getTiktokStylePerformance());
    } catch (err) {
      console.error('Failed to load style performance:', err);
      setError('โหลดผลตามสไตล์ไม่สำเร็จ ตรวจว่า Backend รันอยู่แล้วลองอีกครั้ง');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const rows = useMemo(() => buildStylePerformanceRows(report, groupBy), [report, groupBy]);
  const scale = useMemo(() => maxMedianViews(rows), [rows]);
  const measured = Math.max(0, Number(report?.measured) || 0);
  const hasLowSample = rows.some((r) => r.lowSample);
  const groupCounts = useMemo(
    () => Object.fromEntries(STYLE_GROUPS.map((g) => [g.id, buildStylePerformanceRows(report, g.id).length])),
    [report],
  );

  return (
    <section className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg space-y-3" aria-labelledby="style-performance-title">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" aria-hidden="true" />
            <h3 id="style-performance-title" className="text-sm font-black text-white">ผลตามสไตล์</h3>
          </div>
          <p className="text-xs text-slate-400">
            นับเฉพาะคลิปที่โพสต์ครบ 48 ชั่วโมง{report ? ` · วัดผลแล้ว ${measured} คลิป` : ''}
          </p>
        </div>

        <div
          role="group"
          aria-label="จัดกลุ่มตาม"
          className="flex items-center gap-1 bg-black/40 p-1 rounded-xl border border-white/[0.08] self-start sm:self-auto overflow-x-auto max-w-full"
        >
          {STYLE_GROUPS.map((group) => {
            const active = group.id === groupBy;
            return (
              <button
                key={group.id}
                type="button"
                aria-pressed={active}
                onClick={() => setGroupBy(group.id)}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg whitespace-nowrap transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60 ${
                  active
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'border border-transparent text-slate-400 hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                {group.label}{report ? ` (${groupCounts[group.id]})` : ''}
              </button>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2 py-1" aria-busy="true" aria-label="กำลังโหลดผลตามสไตล์">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-11 rounded-xl bg-white/[0.03] animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="py-6 text-center space-y-3">
          <AlertTriangle className="w-6 h-6 text-amber-400 mx-auto" aria-hidden="true" />
          <p className="text-xs text-slate-300">{error}</p>
          <button
            type="button"
            onClick={load}
            className="px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.1] text-xs font-bold text-white transition-colors cursor-pointer inline-flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
            <span>โหลดอีกครั้ง</span>
          </button>
        </div>
      ) : rows.length === 0 ? (
        <div className="py-8 text-center space-y-1.5">
          <p className="text-sm text-slate-300">ยังไม่มีข้อมูล</p>
          <p className="text-xs text-slate-500 leading-relaxed">
            ผลตามสไตล์จะขึ้นเมื่อคลิปโพสต์ครบ 48 ชั่วโมงและซิงก์สถิติจาก Extension แล้ว
          </p>
        </div>
      ) : (
        <>
          <div className="hidden sm:grid grid-cols-[minmax(0,1.3fr)_minmax(0,1.6fr)_5.5rem_4.5rem] gap-x-3 px-3 text-[11px] font-semibold text-slate-500">
            <span>กลุ่ม · จำนวนคลิป</span>
            <span>มัธยฐานยอดวิว</span>
            <span>เวลาดูเฉลี่ย</span>
            <span>ดูจบ</span>
          </div>
          <ul className="divide-y divide-white/[0.04]">
            {rows.map((row) => <GroupRow key={row.id} row={row} scale={scale} />)}
          </ul>
          <p className="text-[11px] leading-relaxed text-slate-500 border-t border-white/[0.06] pt-2.5">
            {hasLowSample
              ? `กลุ่มที่มีไม่ถึง ${MIN_RELIABLE_SAMPLE} คลิปขึ้นป้ายข้อมูลน้อย ยังสรุปไม่ได้ว่าดีหรือแย่กว่ากลุ่มอื่น`
              : `ทุกกลุ่มมีอย่างน้อย ${MIN_RELIABLE_SAMPLE} คลิป ใช้มัธยฐานเพื่อไม่ให้คลิปปังคลิปเดียวดึงค่าเฉลี่ย`}
          </p>
        </>
      )}
    </section>
  );
}
