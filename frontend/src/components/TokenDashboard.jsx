import React, { useState, useEffect, useCallback, useMemo, forwardRef, useImperativeHandle } from 'react';
import {
  Zap, Coins, Cpu, Clock, ArrowUpRight,
  Sparkles, CheckCircle2, AlertCircle, BarChart3, Layers, Filter,
  Search, ShieldCheck, Eye, Mic, FileText, ChevronRight
} from 'lucide-react';
import { getTokenSummary, resetTokenAnalytics } from '../api';
import { Badge, ConfirmModal, Toast } from './ui';

// Title/refresh/reset live in SystemSettings' own command bar now (this
// panel used to carry a second, duplicate header) -- refresh() and
// openReset() are exposed via ref so that bar can drive this panel's state
// without lifting all of it up.
const TokenDashboard = forwardRef(function TokenDashboard({ onRefreshingChange }, ref) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [taskFilter, setTaskFilter] = useState('all');
  const [showResetModal, setShowResetModal] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const fetchSummary = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const data = await getTokenSummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to load token analytics:', err);
      setToastMessage('ไม่สามารถโหลดข้อมูล Token Analytics ได้');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  useEffect(() => {
    onRefreshingChange?.(refreshing);
  }, [refreshing, onRefreshingChange]);

  useImperativeHandle(ref, () => ({
    refresh: () => fetchSummary(true),
    openReset: () => setShowResetModal(true),
  }), [fetchSummary]);

  const handleReset = async () => {
    setResetting(true);
    try {
      await resetTokenAnalytics();
      setToastMessage('รีเซ็ตสถิติโทเคนเรียบร้อยแล้ว');
      setShowResetModal(false);
      fetchSummary();
    } catch (err) {
      setToastMessage('เกิดข้อผิดพลาดในการรีเซ็ต: ' + err.message);
    } finally {
      setResetting(false);
    }
  };

  const totals = summary?.totals || {
    total_tokens: 0,
    input_tokens: 0,
    output_tokens: 0,
    thinking_tokens: 0,
    total_calls: 0,
    total_cost_saved_thb: 0,
    avg_latency_seconds: 0
  };

  const recentEvents = summary?.recent_events || [];

  // Filtered Events for Ledger Table
  const filteredEvents = useMemo(() => {
    return recentEvents.filter((ev) => {
      const matchSearch =
        !searchFilter ||
        ev.task?.toLowerCase().includes(searchFilter.toLowerCase()) ||
        ev.model?.toLowerCase().includes(searchFilter.toLowerCase()) ||
        ev.project_name?.toLowerCase().includes(searchFilter.toLowerCase());

      const matchTask = taskFilter === 'all' || ev.task === taskFilter;

      return matchSearch && matchTask;
    });
  }, [recentEvents, searchFilter, taskFilter]);

  const getTaskBadge = (task) => {
    switch (task) {
      case 'script':
        return { label: 'เขียนสคริปต์ 2 ภาษา', icon: FileText, color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' };
      case 'vision_match':
        return { label: 'AI Vision ดูคลิปดิบ', icon: Eye, color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' };
      case 'tts':
        return { label: 'สังเคราะห์เสียงพูด', icon: Mic, color: 'bg-purple-500/20 text-purple-300 border-purple-500/40' };
      case 'product_enrich':
        return { label: 'วิเคราะห์จุดขายสินค้า', icon: Sparkles, color: 'bg-amber-500/20 text-amber-300 border-amber-500/40' };
      default:
        return { label: task, icon: Cpu, color: 'bg-slate-700/40 text-slate-300 border-slate-600' };
    }
  };

  const getProviderBadge = (provider) => {
    if (provider === 'antigravity_pro') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gradient-to-r from-[#FE2C55]/20 to-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm">
          <ShieldCheck className="w-3 h-3 text-[#25F4EE]" />
          Antigravity Pro (ฟรี)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
        AI Studio Free
      </span>
    );
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* ── 4 Hero KPI Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Tokens */}
        <div className="glass-panel p-5 rounded-2xl border border-white/[0.08] relative overflow-hidden group hover:border-[#25F4EE]/30 transition-all duration-200 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">โทเคนทั้งหมดที่ใช้ไป</span>
            <div className="w-8 h-8 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE]">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl sm:text-3xl font-black text-white font-mono tracking-tight">
              {totals.total_tokens.toLocaleString()}
            </div>
            <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400 font-mono">
              <span className="text-cyan-400">In: {totals.input_tokens.toLocaleString()}</span>
              <span>•</span>
              <span className="text-emerald-400">Out: {totals.output_tokens.toLocaleString()}</span>
              {totals.thinking_tokens > 0 && (
                <>
                  <span>•</span>
                  <span className="text-purple-400">Think: {totals.thinking_tokens.toLocaleString()}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Card 2: Cost Saved in THB */}
        <div className="glass-panel p-5 rounded-2xl border border-white/[0.08] relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-200 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">มูลค่าที่ประหยัดได้ (เทียบเท่า)</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Coins className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl sm:text-3xl font-black text-emerald-400 font-mono tracking-tight flex items-baseline gap-1">
              ฿{totals.total_cost_saved_thb.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              <span className="text-xs font-sans font-bold text-slate-400">บาท</span>
            </div>
            <div className="mt-1 flex items-center gap-1 text-[11px] text-emerald-400/90">
              <ShieldCheck className="w-3 h-3" />
              <span>ใช้ฟรี 100% จากสิทธิ์ Pro & Free Tier</span>
            </div>
          </div>
        </div>

        {/* Card 3: Total AI Calls */}
        <div className="glass-panel p-5 rounded-2xl border border-white/[0.08] relative overflow-hidden group hover:border-purple-500/30 transition-all duration-200 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">จำนวนครั้งที่เรียกใช้ AI</span>
            <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl sm:text-3xl font-black text-white font-mono tracking-tight">
              {totals.total_calls.toLocaleString()} <span className="text-sm font-sans font-semibold text-slate-400">ครั้ง</span>
            </div>
            <div className="mt-1 text-[11px] text-purple-300/80">
              ครอบคลุมเขียนสคริปต์, ตรวจคลิป และพากย์เสียง
            </div>
          </div>
        </div>

        {/* Card 4: Avg Generation Latency */}
        <div className="glass-panel p-5 rounded-2xl border border-white/[0.08] relative overflow-hidden group hover:border-amber-500/30 transition-all duration-200 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">ความเร็วเฉลี่ยในการตอบกลับ</span>
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl sm:text-3xl font-black text-amber-300 font-mono tracking-tight">
              {totals.avg_latency_seconds} <span className="text-sm font-sans font-semibold text-slate-400">วินาที</span>
            </div>
            <div className="mt-1 text-[11px] text-amber-300/80">
              รวดเร็วด้วย Gemini Flash Architecture
            </div>
          </div>
        </div>
      </div>

      {/* ── Breakdown Sections (Model Share & Tasks) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Section A: Models Distribution */}
        <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-white/[0.08] space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#25F4EE]" />
              <h3 className="text-sm font-bold text-white font-kanit">สัดส่วนการใช้งานตามโมเดล (Models)</h3>
            </div>
            <span className="text-xs text-slate-400">{Object.keys(summary?.tokens_by_model || {}).length} โมเดล</span>
          </div>

          <div className="space-y-3.5 pt-1">
            {Object.entries(summary?.tokens_by_model || {}).length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">ยังไม่มีประวัติการเรียกใช้โมเดล</p>
            ) : (
              Object.entries(summary.tokens_by_model).map(([modelName, tokens]) => {
                const total = totals.total_tokens || 1;
                const percent = Math.round((tokens / total) * 100);
                const calls = summary?.calls_by_model?.[modelName] || 0;

                const isPro = modelName.includes('3.8') || modelName.includes('pro') || modelName.includes('claude');

                return (
                  <div key={modelName} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-slate-200">{modelName}</span>
                        {isPro ? (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#FE2C55]/20 text-[#25F4EE] border border-[#25F4EE]/30">
                            PRO
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                            FREE
                          </span>
                        )}
                      </div>
                      <div className="text-slate-400 font-mono">
                        <span className="text-white font-bold">{tokens.toLocaleString()}</span> tok ({percent}%) • {calls} ครั้ง
                      </div>
                    </div>
                    {/* Visual Bar */}
                    <div className="h-2 w-full bg-white/[0.05] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          isPro
                            ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE]'
                            : 'bg-gradient-to-r from-emerald-500 to-teal-400'
                        }`}
                        style={{ width: `${Math.max(percent, 3)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Section B: Tasks Breakdown */}
        <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-white/[0.08] space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-bold text-white font-kanit">สัดส่วนตามประเภทงาน (Tasks)</h3>
            </div>
            <span className="text-xs text-slate-400">{Object.keys(summary?.tokens_by_task || {}).length} หมวดหมู่งาน</span>
          </div>

          <div className="space-y-3.5 pt-1">
            {Object.entries(summary?.tokens_by_task || {}).length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">ยังไม่มีประวัติการทำ Task</p>
            ) : (
              Object.entries(summary.tokens_by_task).map(([taskKey, tokens]) => {
                const total = totals.total_tokens || 1;
                const percent = Math.round((tokens / total) * 100);
                const calls = summary?.calls_by_task?.[taskKey] || 0;
                const badge = getTaskBadge(taskKey);
                const Icon = badge.icon;

                return (
                  <div key={taskKey} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <Icon className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-semibold text-slate-200 font-kanit">{badge.label}</span>
                      </div>
                      <div className="text-slate-400 font-mono">
                        <span className="text-white font-bold">{tokens.toLocaleString()}</span> tok ({percent}%) • {calls} ครั้ง
                      </div>
                    </div>
                    {/* Visual Bar */}
                    <div className="h-2 w-full bg-white/[0.05] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-500"
                        style={{ width: `${Math.max(percent, 3)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* ── Daily Activity Chart ── */}
      {summary?.daily_stats && summary.daily_stats.length > 0 && (
        <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-white/[0.08] space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white font-kanit">ประวัติการใช้งานย้อนหลัง (Daily Token Volume)</h3>
            </div>
            <span className="text-xs text-slate-400">{summary.daily_stats.length} วันล่าสุด</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5 pt-2">
            {summary.daily_stats.map((day) => (
              <div
                key={day.date}
                className="p-3 rounded-xl bg-black/40 border border-white/[0.06] flex flex-col justify-between space-y-2 hover:border-[#25F4EE]/30 transition-colors"
              >
                <span className="text-[11px] font-mono text-slate-400">{day.date}</span>
                <div>
                  <div className="text-base font-bold text-white font-mono">
                    {day.tokens > 1000 ? `${(day.tokens / 1000).toFixed(1)}k` : day.tokens}
                  </div>
                  <div className="text-[10px] text-emerald-400 font-mono">
                    ฿{day.cost_saved_thb} ประหยัด
                  </div>
                </div>
                <span className="text-[10px] text-slate-500">{day.calls} ครั้ง</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Detailed Audit Log / Ledger ── */}
      <div className="glass-panel rounded-2xl border border-white/[0.08] overflow-hidden">
        {/* Table Header Controls */}
        <div className="p-4 sm:p-5 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white/[0.02]">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#25F4EE]" />
            <h3 className="text-sm font-bold text-white font-kanit">ประวัติการเรียกใช้งาน AI ล่าสุด (Audit Log)</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/[0.08] text-slate-300 font-mono">
              {filteredEvents.length} รายการ
            </span>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="ค้นหางาน, โมเดล, สินค้า..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-xl bg-black/40 border border-white/[0.1] text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]/50 w-44 sm:w-56"
              />
            </div>

            <select
              value={taskFilter}
              onChange={(e) => setTaskFilter(e.target.value)}
              className="py-1.5 px-2.5 rounded-xl bg-black/40 border border-white/[0.1] text-xs text-slate-200 focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer"
            >
              <option value="all">ทุกงาน (All Tasks)</option>
              <option value="script">สคริปต์ 2 ภาษา (Script)</option>
              <option value="vision_match">ตรวจฟุตเทจ (Vision)</option>
              <option value="tts">พากย์เสียง (TTS)</option>
              <option value="product_enrich">วิเคราะห์จุดขาย</option>
            </select>
          </div>
        </div>

        {/* Table Container */}
        <div className="overflow-x-auto touch-pan-x pb-2 no-scrollbar">
          <table className="w-full text-left text-xs text-slate-300 min-w-[700px]">
            <thead className="bg-white/[0.03] text-slate-400 uppercase font-mono text-[10px] border-b border-white/[0.06]">
              <tr>
                <th className="py-3 px-4">เวลา</th>
                <th className="py-3 px-4">งาน (Task)</th>
                <th className="py-3 px-4">สินค้า / โปรเจกต์</th>
                <th className="py-3 px-4">โมเดล & แหล่งสิทธิ์</th>
                <th className="py-3 px-4 text-right">โทเคน (In / Out)</th>
                <th className="py-3 px-4 text-right">รวมโทเคน</th>
                <th className="py-3 px-4 text-right">เวลาประมวลผล</th>
                <th className="py-3 px-4 text-right">ประหยัดเงิน</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-500">
                    <p className="text-xs">ไม่พบข้อมูลประวัติที่ตรงกับเงื่อนไข</p>
                  </td>
                </tr>
              ) : (
                filteredEvents.map((ev) => {
                  const badge = getTaskBadge(ev.task);
                  const Icon = badge.icon;
                  const timeFormatted = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-';

                  return (
                    <tr key={ev.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                        {timeFormatted}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-semibold font-kanit ${badge.color}`}>
                          <Icon className="w-3 h-3" />
                          {badge.label}
                        </span>
                      </td>
                      <td className="py-3 px-4 max-w-[180px] truncate font-medium text-slate-200">
                        {ev.project_name || '-'}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap space-y-1">
                        <div className="font-mono text-[11px] text-slate-300 font-semibold">{ev.model}</div>
                        <div>{getProviderBadge(ev.provider)}</div>
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-[11px] text-slate-400 whitespace-nowrap">
                        <span className="text-cyan-400">{ev.input_tokens.toLocaleString()}</span> /{' '}
                        <span className="text-emerald-400">{ev.output_tokens.toLocaleString()}</span>
                        {ev.thinking_tokens > 0 && (
                          <span className="text-purple-400 block text-[10px]">+{ev.thinking_tokens} think</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-white whitespace-nowrap">
                        {ev.total_tokens.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-amber-300 whitespace-nowrap">
                        {ev.latency_seconds > 0 ? `${ev.latency_seconds}s` : '-'}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-emerald-400 font-bold whitespace-nowrap">
                        ฿{ev.cost_saved_thb}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Reset Confirmation Modal ── */}
      <ConfirmModal
        isOpen={showResetModal}
        onClose={() => setShowResetModal(false)}
        onConfirm={handleReset}
        title="ยืนยันการล้างประวัติโทเคน"
        message="คุณแน่ใจหรือไม่ว่าต้องการล้างสถิติและประวัติการใช้โทเคนทั้งหมด? การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText={resetting ? 'กำลังล้าง...' : 'ล้างสถิติ'}
        confirmVariant="danger"
      />

      {/* ── Toast Notifications ── */}
      {toastMessage && (
        <Toast
          message={toastMessage}
          onClose={() => setToastMessage(null)}
        />
      )}
    </div>
  );
});

export default TokenDashboard;
