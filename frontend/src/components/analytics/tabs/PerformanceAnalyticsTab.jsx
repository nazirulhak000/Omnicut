import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Eye, ThumbsUp, TrendingUp, Trophy, ExternalLink,
  AlertTriangle, RefreshCw, BarChart3, Siren, Link2, X
} from 'lucide-react';
import {
  getTiktokStatsLatest, getTiktokPending, getTiktokClipCandidates,
  attachTiktokPending, ignoreTiktokPending, ignoreAllTiktokPending,
  getTiktokIgnored, restoreTiktokIgnored
} from '../../../api';
import { buildCandidateOptions, buildAttachPayload, metricSummary } from '../../../lib/manualMatch';
import MetricKpiCard from '../components/MetricKpiCard';
import LoadingSpinner from '../../LoadingSpinner';
import AreaLineChart from '../charts/AreaLineChart';
import PaginationControls from '../../PaginationControls';
import { sortChronological, aggregateDailyTrends } from '../../../lib/chartModel';

const fmt = (n) => {
  const v = Number(n) || 0;
  if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M`;
  if (v >= 1000) return `${(v / 1000).toFixed(1)}K`;
  return String(v);
};

export default function PerformanceAnalyticsTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getTiktokStatsLatest();
      setData(res);
    } catch (err) {
      console.error('Failed to load TikTok performance:', err);
      setError('ไม่สามารถโหลดสถิติผลงาน TikTok ได้ — ตรวจว่า Backend รันอยู่ และกดซิงก์สถิติจาก Extension ก่อน');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Manual matching state (แถวที่ยังไม่ได้จับคู่ + รายการที่ข้ามไว้) ──
  const [pendingRows, setPendingRows] = useState([]);
  const [candidateOptions, setCandidateOptions] = useState([]);
  const [chosenKeys, setChosenKeys] = useState({});
  const [matchBusy, setMatchBusy] = useState(false);
  const [ignoredRows, setIgnoredRows] = useState([]);
  const [showIgnored, setShowIgnored] = useState(false);
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingPageSize, setPendingPageSize] = useState(10);
  const [ignoredPage, setIgnoredPage] = useState(1);
  const [ignoredPageSize, setIgnoredPageSize] = useState(10);

  const loadPending = useCallback(async () => {
    try {
      const [pend, cands, ign] = await Promise.all([
        getTiktokPending(),
        getTiktokClipCandidates(),
        getTiktokIgnored(),
      ]);
      setPendingRows(Array.isArray(pend?.rows) ? pend.rows : []);
      setCandidateOptions(buildCandidateOptions(cands?.candidates));
      setIgnoredRows(Array.isArray(ign?.rows) ? ign.rows : []);
    } catch {
      setPendingRows([]);
      setCandidateOptions([]);
      setIgnoredRows([]);
    }
  }, []);

  useEffect(() => { loadPending(); }, [loadPending]);

  const visiblePendingRows = useMemo(
    () => pendingRows.slice((pendingPage - 1) * pendingPageSize, pendingPage * pendingPageSize),
    [pendingRows, pendingPage, pendingPageSize]
  );
  const visibleIgnoredRows = useMemo(
    () => ignoredRows.slice((ignoredPage - 1) * ignoredPageSize, ignoredPage * ignoredPageSize),
    [ignoredRows, ignoredPage, ignoredPageSize]
  );
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(pendingRows.length / pendingPageSize));
    setPendingPage((page) => Math.min(page, totalPages));
  }, [pendingRows.length, pendingPageSize]);
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(ignoredRows.length / ignoredPageSize));
    setIgnoredPage((page) => Math.min(page, totalPages));
  }, [ignoredRows.length, ignoredPageSize]);

  const handleAttach = useCallback(async (row) => {
    const option = candidateOptions.find((o) => o.key === chosenKeys[row.id]);
    const payload = buildAttachPayload(row, option);
    if (!payload) return;
    setMatchBusy(true);
    try {
      await attachTiktokPending(payload);
      setPendingRows((prev) => prev.filter((r) => r.id !== row.id));
      await fetchData();
    } finally {
      setMatchBusy(false);
    }
  }, [candidateOptions, chosenKeys, fetchData]);

  const handleIgnore = useCallback(async (row) => {
    setMatchBusy(true);
    try {
      await ignoreTiktokPending(row.id);
      await loadPending();
    } finally {
      setMatchBusy(false);
    }
  }, [loadPending]);

  const handleIgnoreAll = useCallback(async () => {
    if (pendingRows.length === 0) return;
    setMatchBusy(true);
    try {
      await ignoreAllTiktokPending();
      await loadPending();
    } finally {
      setMatchBusy(false);
    }
  }, [pendingRows.length, loadPending]);

  const handleRestore = useCallback(async (item) => {
    setMatchBusy(true);
    try {
      await restoreTiktokIgnored(item.id);
      await loadPending();
    } finally {
      setMatchBusy(false);
    }
  }, [loadPending]);

  const posts = useMemo(() => (Array.isArray(data?.posts) ? data.posts : []), [data]);
  const summary = data?.summary || {};

  const richPosts = useMemo(() => posts
    .map((p) => {
      const m = p.metrics || {};
      const views = Number(m.views) || 0;
      const likes = Number(m.likes) || 0;
      const comments = Number(m.comments) || 0;
      const shares = Number(m.shares) || 0;
      const engagement = views > 0 ? Math.round(((likes + comments + shares) / views) * 1000) / 10 : 0;
      return {
        ...p,
        views,
        likes,
        comments,
        shares,
        engagement,
        product: p.product_name || '-',
        angle: p.angle_title || p.angle_key || '-',
      };
    })
    .filter((p) => p.views > 0 || p.likes > 0), [posts]);

  const sorted = useMemo(() => [...richPosts].sort((a, b) => b.views - a.views), [richPosts]);

  // PostLog is never pruned server-side -- window the table so a year of
  // daily posts doesn't mount hundreds of rows at once. KPI cards above
  // (totalViews, avgEngagement, etc.) still read the full richPosts.
  const [perfPage, setPerfPage] = useState(1);
  const [perfPageSize, setPerfPageSize] = useState(20);
  useEffect(() => {
    setPerfPage(1);
  }, [data]);
  const visibleSorted = useMemo(
    () => sorted.slice((perfPage - 1) * perfPageSize, perfPage * perfPageSize),
    [sorted, perfPage, perfPageSize]
  );
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(sorted.length / perfPageSize));
    setPerfPage((page) => Math.min(page, totalPages));
  }, [sorted.length, perfPageSize]);
  const winner = sorted[0] || null;
  const loser = sorted.length > 1 ? sorted[sorted.length - 1] : null;

  const totalViews = richPosts.reduce((s, p) => s + p.views, 0);
  const avgEngagement = richPosts.length
    ? Math.round((richPosts.reduce((s, p) => s + p.engagement, 0) / richPosts.length) * 10) / 10
    : 0;

  const [trendMode, setTrendMode] = useState('clips'); // 'clips' | 'daily'

  // 1. Sort posts strictly chronological (oldest -> newest)
  const chronoPosts = useMemo(() => {
    return sortChronological(
      richPosts.filter((p) => p.posted_at),
      'posted_at'
    );
  }, [richPosts]);

  // 2. Trend data for per-clip mode (each point is one clip on the timeline)
  const perClipTrendData = useMemo(() => {
    return chronoPosts.map((p) => {
      const d = new Date(p.posted_at);
      const timeStr = !isNaN(d.getTime())
        ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
        : '';
      return {
        label: (p.posted_at || '').slice(0, 10),
        rawDate: p.posted_at,
        time: timeStr,
        product: p.product,
        angle: p.angle,
        value: p.views,
        likes: p.likes,
        comments: p.comments,
        shares: p.shares,
        engagement: p.engagement,
      };
    });
  }, [chronoPosts]);

  // 3. Trend data for daily aggregated mode (sums multiple clips posted on same date)
  const dailyAggregatedTrendData = useMemo(() => {
    return aggregateDailyTrends(chronoPosts, {
      dateKey: 'posted_at',
      valueKey: 'views',
      metricsKeys: ['likes', 'comments', 'shares'],
    }).map((d) => ({
      ...d,
      label: d.date,
      value: d.value,
      count: d.count,
      likes: d.metrics?.likes || 0,
      comments: d.metrics?.comments || 0,
      shares: d.metrics?.shares || 0,
      engagement: d.value > 0
        ? Math.round((((d.metrics?.likes || 0) + (d.metrics?.comments || 0) + (d.metrics?.shares || 0)) / d.value) * 1000) / 10
        : 0,
    }));
  }, [chronoPosts]);

  const activeTrendData = trendMode === 'daily' ? dailyAggregatedTrendData : perClipTrendData;
if (loading) return <LoadingSpinner message="กำลังประมวลผลสถิติผลงาน TikTok..." />;

  if (error || !data) {
    return (
      <div className="p-8 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" />
        <p className="text-sm text-slate-300">{error || 'ไม่พบข้อมูล'}</p>
        <button
          onClick={fetchData}
          className="px-4 py-2 rounded-xl bg-white/[0.08] hover:bg-white/[0.12] text-xs font-bold text-white transition-all cursor-pointer inline-flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>ลองใหม่อีกครั้ง</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── 4 Top KPI Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricKpiCard
          title="ยอดวิวรวม (ซิงก์แล้ว)"
          value={fmt(totalViews)}
          subtitle={`จาก ${richPosts.length} คลิปที่มีตัวเลข`}
          icon={Eye}
          accentColor="text-cyan-400"
          badge={summary.total_posted != null ? `โพสต์ ${summary.total_posted}` : null}
        />
        <MetricKpiCard
          title="Engagement เฉลี่ย"
          value={`${avgEngagement}%`}
          subtitle="(ถูกใจ+คอมเมนต์+แชร์) / วิว"
          icon={TrendingUp}
          accentColor="text-emerald-400"
          borderColor="border-emerald-500/20"
        />
        <MetricKpiCard
          title="ยอดถูกใจรวม"
          value={fmt(richPosts.reduce((s, p) => s + p.likes, 0))}
          subtitle={`คอมเมนต์ ${fmt(richPosts.reduce((s, p) => s + p.comments, 0))} · แชร์ ${fmt(richPosts.reduce((s, p) => s + p.shares, 0))}`}
          icon={ThumbsUp}
          accentColor="text-rose-400"
          borderColor="border-rose-500/20"
        />
        <MetricKpiCard
          title="คลิปปังที่สุด"
          value={winner ? fmt(winner.views) : '—'}
          subtitle={winner ? `${winner.product} · ${winner.angle}` : 'ยังไม่มีข้อมูลซิงก์'}
          icon={Trophy}
          accentColor="text-amber-400"
          borderColor="border-amber-500/20"
          badge={winner ? `${winner.engagement}%` : null}
        />
      </div>
      {/* ── Trend Chart ── */}
      {activeTrendData.length > 1 && (
        <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-black text-white">
                  {trendMode === 'daily' ? 'ยอดวิวรวมรายวัน (Daily Views Trend)' : 'ยอดวิวต่อคลิป (เรียงตามลำดับเวลาที่โพสต์)'}
                </h3>
              </div>
              <p className="text-xs text-slate-400">
                {trendMode === 'daily'
                  ? `สรุปแนวโน้มยอดวิวรวมแต่ละวัน (${dailyAggregatedTrendData.length} วันที่มีการโพสต์)`
                  : `เรียงคลิปตามไทม์ไลน์เวลาที่โพสต์จริง (${perClipTrendData.length} คลิปจากอดีตถึงปัจจุบัน)`}
              </p>
            </div>

            {/* View Mode Switcher */}
            <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-xl border border-white/[0.08] self-start sm:self-auto">
              <button
                type="button"
                onClick={() => setTrendMode('clips')}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  trendMode === 'clips'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                แยกรายคลิป ({perClipTrendData.length})
              </button>
              <button
                type="button"
                onClick={() => setTrendMode('daily')}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  trendMode === 'daily'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                รวมรายวัน ({dailyAggregatedTrendData.length})
              </button>
            </div>
          </div>

          <AreaLineChart
            data={activeTrendData}
            height={140}
            valueKey="value"
            dateKey="label"
            unit="views"
            valueLabel="ยอดวิว"
            lineColor="#25F4EE"
            gradientFrom="#25F4EE"
            gradientTo="#3B82F6"
          />
        </div>
      )}

      {/* ── Viral Milestone Alert (คลิปปังเกิน 10,000 วิว) ── */}
      {richPosts.some((p) => p.views >= 10000) && (
        <div className="bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/5 border border-amber-500/30 rounded-2xl p-4 sm:p-5 shadow-lg">
          <div className="flex items-center gap-2.5 mb-2">
            <Trophy className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-black text-amber-200">ยินดีด้วย! มีคลิปปังทะลุเป้า 10,000 วิว 🔥</h3>
          </div>
          <div className="text-xs text-slate-300 leading-relaxed">
            พบคลิปที่ทำยอดวิวเกิน 10,000 วิว จำนวน {richPosts.filter(p => p.views >= 10000).length} คลิป — แนะนำให้ถอดรหัส Hook และโครงสร้างคลิปเหล่านี้เพื่อนำไปต่อยอดเป็นซีรีส์คลิปใหม่
          </div>
        </div>
      )}

      {/* ── Winner / Loser banner ── */}
      {winner && (
        <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg">
          <div className="flex items-center gap-2.5 mb-3">
            <Siren className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-black text-white">เรียนรู้อะไรจากข้อมูล</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-2.5">
            {winner && (
              <div className="p-3 rounded-2xl bg-emerald-500/[0.06] border border-emerald-500/25">
                <div className="text-[11px] font-bold text-emerald-300">ใช้มุมขายนี้บ่อยขึ้น</div>
                <div className="mt-1 text-xs font-bold text-white">{winner.product}</div>
                <div className="text-[11px] text-slate-300 mt-0.5">{winner.angle} — {fmt(winner.views)} วิว · {winner.engagement}%</div>
              </div>
            )}
            {loser && loser !== winner && (
              <div className="p-3 rounded-2xl bg-rose-500/[0.06] border border-rose-500/25">
                <div className="text-[11px] font-bold text-rose-300">มุมขายนี้อาจต้องปรับ Hook</div>
                <div className="mt-1 text-xs font-bold text-white">{loser.product}</div>
                <div className="text-[11px] text-slate-300 mt-0.5">{loser.angle} — {fmt(loser.views)} วิว · {loser.engagement}%</div>
              </div>
            )}
          </div>
        </div>
      )}
      {/* ── Manual matching (แถวที่ยังไม่ได้จับคู่) ── */}
      {pendingRows.length > 0 && (
        <div className="bg-[#0B0F19] border border-amber-500/25 rounded-2xl p-4 sm:p-5 shadow-lg">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2.5">
              <Link2 className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-black text-white">แถวที่ยังไม่ได้จับคู่ ({pendingRows.length})</h3>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {ignoredRows.length > 0 && (
                <button
                  onClick={() => setShowIgnored((v) => !v)}
                  className={`px-2.5 py-1.5 rounded-lg border text-xs font-bold transition-all cursor-pointer ${
                    showIgnored
                      ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                      : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/[0.1] text-slate-300'
                  }`}
                >
                  {showIgnored ? 'ซ่อนรายการที่ข้าม' : `ดูรายการที่ข้ามไว้ (${ignoredRows.length})`}
                </button>
              )}
              <button
                onClick={handleIgnoreAll}
                disabled={matchBusy || pendingRows.length === 0}
                title="บันทึกว่าไม่ใช่คลิปเราทั้งหมด และจะไม่ถูกดึงกลับมาอีกเมื่อซิงก์ใหม่"
                className="px-2.5 py-1.5 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-xs font-bold text-rose-300 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                ข้ามทั้งหมด ({pendingRows.length})
              </button>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mb-3">
            แถวเหล่านี้มาจาก TikTok Studio แต่ระบบจับคู่กับคลิปในคลังไม่ได้อัตโนมัติ เลือกคลิปที่ตรงกันแล้วกดจับคู่ได้เลย (หากกดข้าม ระบบจะบันทึกจำไว้ถาวรและไม่ดึงกลับมาอีก)
          </p>
          <div className="space-y-2">
            {visiblePendingRows.map((row) => (
              <div key={row.id} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col lg:flex-row lg:items-center gap-2">
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-bold text-slate-200 truncate">{row.title || row.video_id || 'แถวไม่มีชื่อ'}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    {metricSummary(row)}{row.posted_text ? ` · ${row.posted_text}` : ''}
                  </div>
                </div>
                <select
                  value={chosenKeys[row.id] || ''}
                  onChange={(e) => setChosenKeys((prev) => ({ ...prev, [row.id]: e.target.value }))}
                  className="lg:w-72 flex-shrink-0 px-2.5 py-1.5 rounded-lg bg-[#111827] border border-white/[0.12] text-xs text-slate-200 focus:outline-none focus:border-cyan-400/50"
                >
                  <option value="">เลือกคลิปในคลัง…</option>
                  {candidateOptions.map((o) => (
                    <option key={o.key} value={o.key}>{o.label}</option>
                  ))}
                </select>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <button
                    onClick={() => handleAttach(row)}
                    disabled={matchBusy || !chosenKeys[row.id]}
                    className="px-3 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-[11px] font-bold text-cyan-300 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  >
                    <span>จับคู่</span>
                  </button>
                  <button
                    onClick={() => handleIgnore(row)}
                    disabled={matchBusy}
                    title="คลิปนี้ไม่ใช่ของเรา ตัดออกจากรายการถาวร"
                    className="px-2.5 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.1] text-[11px] font-bold text-slate-300 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  >
                    <span>ข้ามรายการ</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
          <PaginationControls
            page={pendingPage}
            pageSize={pendingPageSize}
            totalItems={pendingRows.length}
            onPageChange={setPendingPage}
            onPageSizeChange={(size) => {
              setPendingPageSize(size);
              setPendingPage(1);
            }}
            itemLabel="แถวรอจับคู่"
            disabled={matchBusy}
          />

          {/* Expanded ignored list */}
          {showIgnored && ignoredRows.length > 0 && (
            <div className="p-3.5 rounded-xl bg-amber-500/[0.04] border border-amber-500/20 space-y-2 mt-4">
              <div className="flex items-center justify-between text-[11px] text-amber-300 font-bold">
                <span>รายการที่ข้ามไว้ถาวร ({ignoredRows.length} รายการ — จะไม่กลับมาเมื่อซิงก์ใหม่)</span>
              </div>
              <div className="space-y-1.5 pr-1">
                {visibleIgnoredRows.map((item) => (
                  <div key={item.id} className="p-2.5 rounded-lg bg-black/40 border border-white/[0.05] flex items-center justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="text-xs text-slate-300 truncate">{item.title || item.video_id || 'แถวไม่มีชื่อ'}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {metricSummary(item)}{item.posted_text ? ` · ${item.posted_text}` : ''}
                      </div>
                    </div>
                    <button
                      onClick={() => handleRestore(item)}
                      disabled={matchBusy}
                      title="นำกลับเข้ามารอจับคู่ใหม่"
                      className="px-2.5 py-1 rounded bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-[11px] font-bold text-amber-300 transition-all cursor-pointer whitespace-nowrap"
                    >
                      นำกลับมาจับคู่
                    </button>
                  </div>
                ))}
              </div>
              <PaginationControls
                page={ignoredPage}
                pageSize={ignoredPageSize}
                totalItems={ignoredRows.length}
                onPageChange={setIgnoredPage}
                onPageSizeChange={(size) => {
                  setIgnoredPageSize(size);
                  setIgnoredPage(1);
                }}
                itemLabel="รายการที่ข้าม"
                disabled={matchBusy}
              />
            </div>
          )}
        </div>
      )}

      {/* ── If all pending rows resolved, but user has persistent ignored rows ── */}
      {pendingRows.length === 0 && ignoredRows.length > 0 && (
        <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 shadow-lg">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="text-xs text-slate-400">
              ไม่มีคลิปค้างรอจับคู่ (มีรายการที่ข้ามไว้ถาวร <span className="text-amber-400 font-bold">{ignoredRows.length}</span> รายการ ซึ่งจะไม่ถูกดึงกลับมาซ้ำ)
            </div>
            <button
              onClick={() => setShowIgnored((v) => !v)}
              className={`px-2.5 py-1.5 rounded-lg border text-xs font-bold transition-all cursor-pointer ${
                showIgnored
                  ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                  : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/[0.1] text-slate-300'
              }`}
            >
              {showIgnored ? 'ซ่อนรายการที่ข้าม' : `ดูรายการที่ข้ามไว้ (${ignoredRows.length})`}
            </button>
          </div>
          {showIgnored && (
            <div className="p-3.5 rounded-xl bg-amber-500/[0.04] border border-amber-500/20 space-y-2 mt-3">
              <div className="flex items-center justify-between text-[11px] text-amber-300 font-bold">
                <span>รายการที่ข้ามไว้ถาวร ({ignoredRows.length} รายการ — จะไม่กลับมาเมื่อซิงก์ใหม่)</span>
              </div>
              <div className="space-y-1.5 pr-1">
                {visibleIgnoredRows.map((item) => (
                  <div key={item.id} className="p-2.5 rounded-lg bg-black/40 border border-white/[0.05] flex items-center justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="text-xs text-slate-300 truncate">{item.title || item.video_id || 'แถวไม่มีชื่อ'}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {metricSummary(item)}{item.posted_text ? ` · ${item.posted_text}` : ''}
                      </div>
                    </div>
                    <button
                      onClick={() => handleRestore(item)}
                      disabled={matchBusy}
                      title="นำกลับเข้ามารอจับคู่ใหม่"
                      className="px-2.5 py-1 rounded bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-[11px] font-bold text-amber-300 transition-all cursor-pointer whitespace-nowrap"
                    >
                      นำกลับมาจับคู่
                    </button>
                  </div>
                ))}
              </div>
              <PaginationControls
                page={ignoredPage}
                pageSize={ignoredPageSize}
                totalItems={ignoredRows.length}
                onPageChange={setIgnoredPage}
                onPageSizeChange={(size) => {
                  setIgnoredPageSize(size);
                  setIgnoredPage(1);
                }}
                itemLabel="รายการที่ข้าม"
                disabled={matchBusy}
              />
            </div>
          )}
        </div>
      )}
      {/* ── Clips Table (เหมือนตาราง TikTok Studio + คอลัมน์โปรแกรมเรา) ── */}
      <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg">
        <div className="flex items-center gap-2.5 mb-3">
          <Eye className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-black text-white">ผลงานแต่ละคลิป</h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-cyan-500/10 text-cyan-300 border-cyan-500/30">
            {richPosts.length} คลิป
          </span>
        </div>

        {richPosts.length === 0 ? (
          <div className="py-10 text-center space-y-3">
            <BarChart3 className="w-8 h-8 text-slate-500 mx-auto" />
            <p className="text-sm text-slate-300">ยังไม่มีสถิติจาก TikTok</p>
            <p className="text-xs text-slate-500 leading-relaxed">
              เปิดหน้า TikTok Studio แท็บ โพสต์ จากนั้นกดปุ่ม ซิงก์สถิติ ใน Extension<br />
              (ไอคอน OmniCut ข้างแถบที่อยู่ → แถบข้าง → การ์ดล่างสุด)
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[720px]">
              <thead>
                <tr className="border-b border-white/[0.08] text-slate-400 font-semibold">
                  <th className="py-2.5 px-3">คลิป</th>
                  <th className="py-2.5 px-3">สินค้า / มุมขาย</th>
                  <th className="py-2.5 px-3 text-right">วิว</th>
                  <th className="py-2.5 px-3 text-right">ถูกใจ</th>
                  <th className="py-2.5 px-3 text-right">คอมเมนต์</th>
                  <th className="py-2.5 px-3 text-right">Engagement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {visibleSorted.map((p, idx) => (
                  <tr key={p.id || idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        {idx === 0 && <Trophy className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />}
                        {p.thumbnail ? (
                          <img src={p.thumbnail} alt="" className="w-9 h-14 object-cover rounded-md flex-shrink-0" />
                        ) : (
                          <div className="w-9 h-14 rounded-md bg-white/[0.04] border border-white/[0.08] flex-shrink-0" />
                        )}
                        <div className="min-w-0">
                          <div className="text-slate-200 font-semibold truncate max-w-[220px]">
                            {p.hook_title || p.title || p.clip_file || 'คลิป'}
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5 truncate max-w-[220px]">
                            {p.posted_at ? `โพสต์ ${p.posted_at.slice(0, 16).replace('T', ' ')}` : '—'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="text-slate-200 max-w-[160px] truncate">{p.product}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5 max-w-[160px] truncate">{p.angle}</div>
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-200">{fmt(p.views)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-300">{fmt(p.likes)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-300">{fmt(p.comments)}</td>
                    <td className="py-2.5 px-3 text-right">
                      <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold ${p.engagement >= 5 ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' : p.engagement >= 2 ? 'bg-amber-500/10 text-amber-300 border-amber-500/30' : 'bg-white/[0.04] text-slate-400 border-white/[0.1]'}`}>
                        {p.engagement}%
                      </span>
                      {p.tiktok_url && (
                        <a href={p.tiktok_url} target="_blank" rel="noreferrer" title="เปิดคลิปบน TikTok" className="ml-2 inline-flex text-cyan-400 hover:text-cyan-200">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <PaginationControls
              page={perfPage}
              pageSize={perfPageSize}
              totalItems={sorted.length}
              onPageChange={setPerfPage}
              onPageSizeChange={(size) => {
                setPerfPageSize(size);
                setPerfPage(1);
              }}
              itemLabel="คลิป"
              disabled={loading}
            />
          </div>
        )}
      </div>
    </div>
  );
}
