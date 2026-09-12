import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Eye, ThumbsUp, TrendingUp, Trophy, ExternalLink,
  AlertTriangle, RefreshCw, BarChart3, Siren
} from 'lucide-react';
import { getTiktokStatsLatest } from '../../../api';
import MetricKpiCard from '../components/MetricKpiCard';
import LoadingSpinner from '../../LoadingSpinner';
import AreaLineChart from '../charts/AreaLineChart';

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
  const winner = sorted[0] || null;
  const loser = sorted.length > 1 ? sorted[sorted.length - 1] : null;

  const totalViews = richPosts.reduce((s, p) => s + p.views, 0);
  const avgEngagement = richPosts.length
    ? Math.round((richPosts.reduce((s, p) => s + p.engagement, 0) / richPosts.length) * 10) / 10
    : 0;

  const trendData = useMemo(() => richPosts
    .map((p) => ({ label: (p.posted_at || '').slice(0, 10) || '—', value: p.views }))
    .reverse(), [richPosts]);
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
      {trendData.length > 1 && (
        <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg">
          <div className="flex items-center gap-2.5 mb-3">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-black text-white font-kanit">ยอดวิวต่อคลิป (เรียงตามวันที่โพสต์)</h3>
          </div>
          <AreaLineChart data={trendData} height={130} />
        </div>
      )}

      {/* ── Winner / Loser banner ── */}
      {winner && (
        <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg">
          <div className="flex items-center gap-2.5 mb-3">
            <Siren className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-black text-white font-kanit">เรียนรู้อะไรจากข้อมูล</h3>
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
      {/* ── Clips Table (เหมือนตาราง TikTok Studio + คอลัมน์โปรแกรมเรา) ── */}
      <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg">
        <div className="flex items-center gap-2.5 mb-3">
          <Eye className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-black text-white font-kanit">ผลงานแต่ละคลิป</h3>
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
                {sorted.map((p, idx) => (
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
                    <td className="py-2.5 px-3 text-right font-mono text-slate-200">{fmt(p.views)}</td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-300">{fmt(p.likes)}</td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-300">{fmt(p.comments)}</td>
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
          </div>
        )}
      </div>
    </div>
  );
}