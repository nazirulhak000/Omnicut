import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Layers, Clapperboard, Video, CheckCircle2, Clock,
  AlertTriangle, ArrowRight, Play, ExternalLink, RefreshCw
} from 'lucide-react';
import { getProductionAnalytics } from '../../../api';
import MetricKpiCard from '../components/MetricKpiCard';
import LoadingSpinner from '../../LoadingSpinner';
import FunnelPipelineChart from '../charts/FunnelPipelineChart';
import DonutChart from '../charts/DonutChart';
import { ProgressRing } from '../charts/ProgressRing';

export default function ProductionAnalyticsTab({ onNavigateToEditor, onNavigateToTracker }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getProductionAnalytics();
      setData(res);
    } catch (err) {
      console.error('Failed to load production analytics:', err);
      setError('ไม่สามารถโหลดข้อมูลสถิติการผลิตคลิปได้');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const { summary = {}, angle_types = [], recent_productions = [] } = data || {};
  const totalAngles = summary.total_angles || 1;

  const pipelineStages = useMemo(() => [
    { key: 'scripted', label: 'สคริปต์พร้อม', count: summary.scripted || 0, percentage: Math.round(((summary.scripted || 0) / totalAngles) * 100) },
    { key: 'in_production', label: 'กำลังตัดต่อ', count: summary.in_production || 0, percentage: Math.round(((summary.in_production || 0) / totalAngles) * 100) },
    { key: 'rendered', label: 'ตัดต่อเสร็จ', count: summary.rendered || 0, percentage: Math.round(((summary.rendered || 0) / totalAngles) * 100) },
    { key: 'posted', label: 'ลงโพสต์แล้ว', count: summary.posted || 0, percentage: Math.round(((summary.posted || 0) / totalAngles) * 100) },
  ], [summary, totalAngles]);

  const bottleneck = useMemo(() => {
    if (!summary.bottleneck_note) return null;
    const isProd = (summary.in_production || 0) > (summary.rendered || 0);
    return {
      stage: isProd ? 'in_production' : 'scripted',
      stage_label: isProd ? 'กำลังตัดต่อ' : 'สคริปต์พร้อม',
      count: Math.max(summary.in_production || 0, summary.scripted || 0),
    };
  }, [summary]);

  const angleChartData = useMemo(() => {
    return angle_types.map((type) => ({
      label: type.name,
      value: type.count,
    }));
  }, [angle_types]);

  if (loading) {
    return <LoadingSpinner message="กำลังประมวลผลสถิติการผลิตคลิป..." />;
  }

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
          title="คลิปทั้งหมดในระบบ"
          value={summary.total_angles}
          subtitle={`จากสินค้าทั้งหมด ${summary.total_products} รายการ`}
          icon={Layers}
          accentColor="text-cyan-400"
          borderColor="border-cyan-500/20"
          bgColor="bg-cyan-500/[0.03]"
        />
        <MetricKpiCard
          title="กำลังดำเนินการ (WIP)"
          value={summary.scripted + summary.in_production}
          subtitle={`สคริปต์พร้อม ${summary.scripted} · กำลังตัดต่อ ${summary.in_production}`}
          icon={Clapperboard}
          accentColor="text-amber-400"
          borderColor="border-amber-500/20"
          bgColor="bg-amber-500/[0.03]"
          badge="รอคิว"
          badgeColor="bg-amber-500/10 text-amber-400 border-amber-500/20"
        />
        <MetricKpiCard
          title="ตัดต่อสำเร็จ (Ready)"
          value={summary.rendered}
          subtitle="ไฟล์พร้อมตรวจสอบ QC และลงโพสต์"
          icon={Video}
          accentColor="text-blue-400"
          borderColor="border-blue-500/20"
          bgColor="bg-blue-500/[0.03]"
        />
        <MetricKpiCard
          title="ลงโพสต์แล้ว (Published)"
          value={`${summary.posted} คลิป`}
          subtitle={`คิดเป็น ${summary.published_percentage}% ของคลิปทั้งหมด`}
          icon={CheckCircle2}
          accentColor="text-emerald-400"
          borderColor="border-emerald-500/20"
          bgColor="bg-emerald-500/[0.03]"
          badge={`${summary.published_percentage}%`}
          badgeColor="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
          rightElement={
            <ProgressRing
              percentage={summary.published_percentage}
              size={42}
              strokeWidth={4.5}
              color="#10B981"
            />
          }
        />
      </div>

      {/* ── Bottleneck Notice (if any) ── */}
      {summary.bottleneck_note && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-3 text-amber-200 text-xs">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
          <span className="font-semibold">{summary.bottleneck_note}</span>
        </div>
      )}

      {/* ── 4-Phase Pipeline Funnel Visualization ── */}
      <div className="p-5 sm:p-6 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-sm sm:text-base font-bold text-white">แผนภาพ Funnel การผลิต 4 ขั้นตอน (Pipeline Health)</h3>
            <p className="text-xs text-slate-400">อัตราการส่งต่อคลิปข้ามเฟสและการกระจายตัวของปริมาณงานในระบบ</p>
          </div>
          <button
            onClick={fetchData}
            className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white transition-all cursor-pointer"
            title="รีเฟรชข้อมูล"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        <FunnelPipelineChart
          stages={pipelineStages}
          bottleneck={bottleneck}
          totalProjects={totalAngles}
        />
      </div>

      {/* ── Two Columns: Angle Types Distribution & Recent Activity ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Angle Types */}
        <div className="p-5 sm:p-6 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4 flex flex-col justify-start">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-white">สัดส่วนมุมมองคลิป (Content Angles)</h3>
            <p className="text-xs text-slate-400">หมวดหมู่และรูปแบบคอนเทนต์ที่สร้าง (5 อันดับแรก)</p>
          </div>

          <div className="pt-4 flex flex-col items-center justify-center">
            {angleChartData.length === 0 ? (
              <div className="text-xs text-slate-500 py-6 text-center">ยังไม่มีข้อมูลมุมมองคลิป</div>
            ) : (
              <DonutChart
                data={angleChartData}
                size={130}
                strokeWidth={18}
                centerLabel="มุมมองคลิป"
                centerValue={summary.total_angles}
                unit="คลิป"
                legendLayout="vertical"
                maxSlices={5}
              />
            )}
          </div>
        </div>

        {/* Right Col: Recent Productions Table */}
        <div className="lg:col-span-2 p-5 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-white">ความเคลื่อนไหวล่าสุด (Recent Productions)</h3>
              <p className="text-xs text-slate-400">รายการคลิปล่าสุดที่มีการอัปเดตสถานะ</p>
            </div>
            {onNavigateToTracker && (
              <button
                onClick={onNavigateToTracker}
                className="text-xs font-semibold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer"
              >
                <span>เปิดดูใน Tracker</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.08] text-slate-400 font-semibold">
                  <th className="py-2.5 px-3">สินค้า</th>
                  <th className="py-2.5 px-3">พาดหัวคลิป</th>
                  <th className="py-2.5 px-3">สถานะ</th>
                  <th className="py-2.5 px-3 text-right">ดำเนินการ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {recent_productions.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      ยังไม่มีรายการผลิตคลิป
                    </td>
                  </tr>
                )}
                {recent_productions.map((item, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-white max-w-[140px] truncate">
                      {item.product_code && (
                        <span className="mr-1.5 text-[10px] font-mono px-1 py-0.5 rounded bg-white/[0.08] text-cyan-300">
                          {item.product_code}
                        </span>
                      )}
                      <span>{item.product_name}</span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300 max-w-[200px] truncate">
                      {item.hook_title}
                    </td>
                    <td className="py-2.5 px-3">
                      {item.status === 'posted' && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold">
                          โพสต์แล้ว
                        </span>
                      )}
                      {item.status === 'rendered' && (
                        <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-bold">
                          ตัดต่อเสร็จ
                        </span>
                      )}
                      {item.status === 'in_production' && (
                        <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-bold">
                          กำลังตัดต่อ
                        </span>
                      )}
                      {item.status === 'scripted' && (
                        <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[10px] font-bold">
                          สคริปต์พร้อม
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {item.project_name && onNavigateToEditor && (
                        <button
                          onClick={() => onNavigateToEditor(item.project_name)}
                          className="px-2 py-1 rounded bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-[11px] font-semibold transition-all cursor-pointer inline-flex items-center gap-1"
                        >
                          <Play className="w-3 h-3 text-[#25F4EE]" />
                          <span>ไทม์ไลน์</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
