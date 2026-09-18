import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Package, Image as ImageIcon, Video, FileText, CheckCircle2,
  AlertCircle, ArrowRight, Play, RefreshCw, Sparkles, Filter
} from 'lucide-react';
import { getInventoryHealth } from '../../../api';
import MetricKpiCard from '../components/MetricKpiCard';
import LoadingSpinner from '../../LoadingSpinner';
import DonutChart from '../charts/DonutChart';
import { ProgressRing, ConcentricRings } from '../charts/ProgressRing';

export default function InventoryAnalyticsTab({ onNavigateToFlow }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterReadiness, setFilterReadiness] = useState('all'); // 'all' | 'ready' | 'need_footage' | 'need_script'
  const [searchQuery, setSearchQuery] = useState('');
  const INVENTORY_PAGE_SIZE = 40;
  const [visibleProductCount, setVisibleProductCount] = useState(INVENTORY_PAGE_SIZE);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getInventoryHealth();
      setData(res);
    } catch (err) {
      console.error('Failed to load inventory health:', err);
      setError('ไม่สามารถโหลดข้อมูลสุขภาพสินค้าได้');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const { summary = {}, products = [] } = data || {};

  const mediaRings = useMemo(() => [
    {
      label: 'รูปภาพสินค้า (Images)',
      percentage: summary?.with_images_percentage || 0,
      color: '#25F4EE',
      detail: 'มีรูปอ้างอิงและรูปถ่ายสำหรับตัดต่อ',
    },
    {
      label: 'วิดีโอ B-roll (Footage)',
      percentage: summary?.with_videos_percentage || 0,
      color: '#F59E0B',
      detail: 'มีฟุตเทจวิดีโอดิบพร้อมใช้',
    },
    {
      label: 'สคริปต์ AI (Scripts)',
      percentage: summary?.with_scripts_percentage || 0,
      color: '#A855F7',
      detail: 'มีสคริปต์บทพูดและฮุกที่เจนแล้ว',
    },
  ], [summary]);

  const readinessData = useMemo(() => {
    const readyCount = products.filter((p) => p.readiness === 'ready').length;
    const needFootageCount = products.filter((p) => p.readiness === 'need_footage').length;
    const needScriptCount = products.filter((p) => p.readiness === 'need_script').length;

    return [
      { label: 'พร้อมตัดต่อทันที', value: readyCount, color: '#10B981' },
      { label: 'ขาดฟุตเทจวิดีโอ', value: needFootageCount, color: '#F59E0B' },
      { label: 'ขาดสคริปต์ AI', value: needScriptCount, color: '#8B5CF6' },
    ];
  }, [products]);

  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      if (filterReadiness !== 'all' && p.readiness !== filterReadiness) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = (p.name || '').toLowerCase().includes(q);
        const matchCode = (p.product_code || '').toLowerCase().includes(q);
        if (!matchName && !matchCode) return false;
      }
      return true;
    });
  }, [products, filterReadiness, searchQuery]);

  useEffect(() => {
    setVisibleProductCount(INVENTORY_PAGE_SIZE);
  }, [filterReadiness, searchQuery]);

  const visibleProducts = useMemo(
    () => filteredProducts.slice(0, visibleProductCount),
    [filteredProducts, visibleProductCount]
  );

  if (loading && !data) {
    return <LoadingSpinner message="กำลังตรวจสอบความสมบูรณ์ของคลังสินค้าและวัตถุดิบ..." />;
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-400 mx-auto" />
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
          title="สินค้าทั้งหมดในระบบ"
          value={summary.total_products}
          subtitle={`มีคลิปแล้ว ${summary.covered_products} · ยังไม่มีคลิป ${summary.uncovered_products}`}
          icon={Package}
          accentColor="text-rose-400"
          borderColor="border-rose-500/20"
          bgColor="bg-rose-500/[0.03]"
        />
        <MetricKpiCard
          title="อัตราสินค้ามีคลิป (Coverage)"
          value={`${summary.coverage_percentage}%`}
          subtitle="สัดส่วนสินค้าที่มีวิดีโอตัดต่อแล้ว"
          icon={CheckCircle2}
          accentColor="text-emerald-400"
          borderColor="border-emerald-500/20"
          bgColor="bg-emerald-500/[0.03]"
          badge={`${summary.covered_products}/${summary.total_products}`}
          badgeColor="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
          rightElement={
            <ProgressRing
              percentage={summary.coverage_percentage}
              size={42}
              strokeWidth={4.5}
              color="#10B981"
            />
          }
        />
        <MetricKpiCard
          title="ความสมบูรณ์เฉลี่ย (Score)"
          value={`${summary.avg_completeness_score}%`}
          subtitle="คำนวณจากรูปภาพ ฟุตเทจ สคริปต์ และแผนถ่าย"
          icon={Sparkles}
          accentColor="text-cyan-400"
          borderColor="border-cyan-500/20"
          bgColor="bg-cyan-500/[0.03]"
        />
        <MetricKpiCard
          title="โอกาสใหม่ (ยังไม่มีคลิป)"
          value={`${summary.uncovered_products} สินค้า`}
          subtitle="สินค้าที่พร้อมนำมาเขียนสคริปต์และผลิตคลิป"
          icon={AlertCircle}
          accentColor="text-amber-400"
          borderColor="border-amber-500/20"
          bgColor="bg-amber-500/[0.03]"
          badge="รอผลิต"
          badgeColor="bg-amber-500/10 text-amber-400 border-amber-500/20"
        />
      </div>

      {/* ── Media Completeness & Readiness Visual Hub ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Concentric Activity Rings */}
        <div className="p-5 sm:p-6 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4 flex flex-col justify-between shadow-xl">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h3 className="text-sm sm:text-base font-bold text-white">มาตรวัดความพร้อมวัตถุดิบ (Media Completeness)</h3>
              <p className="text-xs text-slate-400">อัตราความพร้อมของรูปภาพ ฟุตเทจวิดีโอ และสคริปต์ในคลัง</p>
            </div>
            <button
              onClick={fetchData}
              disabled={loading}
              className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              title="รีเฟรชข้อมูล"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          <div className="pt-2">
            <ConcentricRings rings={mediaRings} size={135} strokeWidth={9} gap={4} />
          </div>
        </div>

        {/* Right: Readiness Donut Chart */}
        <div className="p-5 sm:p-6 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4 flex flex-col justify-between shadow-xl">
          <div className="space-y-1">
            <h3 className="text-sm sm:text-base font-bold text-white">สัดส่วนความพร้อมสินค้า (Readiness Ratio)</h3>
            <p className="text-xs text-slate-400">จำแนกตามความพร้อมในการกดผลิตคลิปได้ทันที</p>
          </div>

          <div className="pt-2 flex-1 flex flex-col items-center justify-center">
            <DonutChart
              data={readinessData}
              size={135}
              strokeWidth={18}
              centerLabel="สินค้าทั้งหมด"
              centerValue={summary.total_products}
              unit="รายการ"
              legendLayout="vertical"
            />
          </div>
        </div>
      </div>

      {/* ── Product Health Catalog Table ── */}
      <div className="p-5 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-white">ตารางความสมบูรณ์และสถานะสินค้า (Catalog Health Grid)</h3>
            <p className="text-xs text-slate-400">ตรวจสอบวัตถุดิบและเริ่มตัดต่อคลิปได้ทันที</p>
          </div>

          {loading && (
            <span className="inline-flex items-center gap-1.5 text-[11px] text-cyan-300" role="status">
              <RefreshCw className="w-3 h-3 animate-spin" /> กำลังอัปเดตข้อมูลเดิม...
            </span>
          )}

          <div className="flex items-center gap-2">
            {/* Search Input */}
            <input
              type="text"
              placeholder="ค้นหาชื่อหรือรหัสสินค้า..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-black/30 border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE] w-48"
            />

            {/* Filter */}
            <select
              value={filterReadiness}
              onChange={(e) => setFilterReadiness(e.target.value)}
              className="bg-black/30 border border-white/[0.1] rounded-xl px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-[#25F4EE]"
            >
              <option value="all">สถานะทั้งหมด</option>
              <option value="ready">พร้อมตัดต่อทันที</option>
              <option value="need_footage">ขาดวิดีโอถ่ายทำ</option>
              <option value="need_script">ขาดสคริปต์</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-400 font-semibold">
                <th className="py-2.5 px-3">สินค้า</th>
                <th className="py-2.5 px-3">รูปภาพ</th>
                <th className="py-2.5 px-3">วิดีโอ</th>
                <th className="py-2.5 px-3">สคริปต์</th>
                <th className="py-2.5 px-3">คลิปที่ตัดแล้ว</th>
                <th className="py-2.5 px-3">คะแนนความพร้อม</th>
                <th className="py-2.5 px-3 text-right">ดำเนินการ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredProducts.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    ไม่พบสินค้าที่ตรงตามเงื่อนไข
                  </td>
                </tr>
              )}
              {visibleProducts.map((p) => (
                <tr key={p.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 px-3 font-semibold text-white max-w-[200px] truncate">
                    {p.product_code && (
                      <span className="mr-1.5 text-[10px] font-semibold px-1 py-0.5 rounded bg-white/[0.08] text-cyan-300">
                        {p.product_code}
                      </span>
                    )}
                    <span>{p.name}</span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${p.images_count > 0 ? 'bg-cyan-500/10 text-cyan-400' : 'bg-slate-800 text-slate-500'}`}>
                      {p.images_count} รูป
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${p.videos_count > 0 ? 'bg-amber-500/10 text-amber-400' : 'bg-slate-800 text-slate-500'}`}>
                      {p.videos_count} คลิป
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${p.angles_count > 0 ? 'bg-purple-500/10 text-purple-400' : 'bg-slate-800 text-slate-500'}`}>
                      {p.angles_count} มุม
                    </span>
                  </td>
                  <td className="py-3 px-3 font-bold text-slate-200">
                    {p.rendered_clips > 0 ? (
                      <span className="text-emerald-400">{p.rendered_clips} คลิป</span>
                    ) : (
                      <span className="text-slate-500">-</span>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                        <div
                          className={`h-full rounded-full ${p.completeness_score >= 80 ? 'bg-emerald-400' : p.completeness_score >= 50 ? 'bg-amber-400' : 'bg-rose-400'}`}
                          style={{ width: `${p.completeness_score}%` }}
                        />
                      </div>
                      <span className="font-bold text-[11px] text-slate-300">
                        {p.completeness_score}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    {onNavigateToFlow && (
                      <button
                        onClick={() => onNavigateToFlow(p.id)}
                        className="px-2.5 py-1 rounded-lg bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-[11px] font-bold transition-all cursor-pointer inline-flex items-center gap-1"
                      >
                        <Play className="w-3 h-3" />
                        <span>สร้างคลิป</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredProducts.length > visibleProducts.length && (
          <div className="flex justify-center pt-1">
            <button
              type="button"
              onClick={() => setVisibleProductCount((count) => count + INVENTORY_PAGE_SIZE)}
              className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.1] text-xs font-bold text-slate-200 transition-colors cursor-pointer"
            >
              โหลดเพิ่ม ({filteredProducts.length - visibleProducts.length} รายการที่เหลือ)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
