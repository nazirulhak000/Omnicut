import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Zap, Coins, Cpu, Clock,
  Sparkles, CheckCircle2, AlertCircle, BarChart3, Layers,
  Search, ShieldCheck, Eye, Mic, FileText,
  AlertTriangle, Key, RotateCcw,
  Flame, Activity, PiggyBank, Calendar, ChevronDown, ChevronUp
} from 'lucide-react';
import { getTokenSummary, getTokenHistory, resetTokenAnalytics, clearTokenAlerts } from '../api';
import { ConfirmModal, Toast } from './ui';
import AreaLineChart from './analytics/charts/AreaLineChart';
import DonutChart from './analytics/charts/DonutChart';
import PaginationControls from './PaginationControls';

const getTokenLoadError = (err) => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (typeof err?.message === 'string' && err.message.trim()) return err.message;
  return 'ไม่สามารถโหลดข้อมูล Token Analytics ได้';
};

const formatAuditDateTime = (timestamp) => {
  if (!timestamp) return { date: '-', time: '-' };
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return { date: '-', time: '-' };
  return {
    date: date.toLocaleDateString('th-TH', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }),
    time: date.toLocaleTimeString('th-TH', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }),
  };
};

const TokenDashboard = function TokenDashboard({ refreshKey = 0 }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [taskFilter, setTaskFilter] = useState('all');
  const [showResetModal, setShowResetModal] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [historyEvents, setHistoryEvents] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyTotal, setHistoryTotal] = useState(null);
  const [historyTotalPages, setHistoryTotalPages] = useState(1);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPageSize, setHistoryPageSize] = useState(20);
  const [historyError, setHistoryError] = useState(null);
  const historyRequestRef = useRef(0);

  // Time range filter & breakdown state for Daily Activity Chart
  const [tokenDaysFilter, setTokenDaysFilter] = useState('14');
  const [showDailyBreakdown, setShowDailyBreakdown] = useState(false);
  const [dailyPage, setDailyPage] = useState(1);
  const [dailyPageSize, setDailyPageSize] = useState(10);

  const filteredDailyStats = useMemo(() => {
    const stats = summary?.daily_stats || [];
    if (tokenDaysFilter === 'all') return stats;
    const days = parseInt(tokenDaysFilter, 10) || 14;
    return stats.slice(-days);
  }, [summary?.daily_stats, tokenDaysFilter]);

  const peakDay = useMemo(() => {
    if (!filteredDailyStats.length) return null;
    return [...filteredDailyStats].sort((a, b) => (Number(b.tokens) || 0) - (Number(a.tokens) || 0))[0];
  }, [filteredDailyStats]);

  const dailyAvgTokens = useMemo(() => {
    if (!filteredDailyStats.length) return 0;
    const sum = filteredDailyStats.reduce((acc, d) => acc + (Number(d.tokens) || 0), 0);
    return Math.round(sum / filteredDailyStats.length);
  }, [filteredDailyStats]);

  const totalSavedInPeriod = useMemo(() => {
    const sum = filteredDailyStats.reduce((acc, d) => acc + (Number(d.cost_saved_thb) || 0), 0);
    return sum.toFixed(2);
  }, [filteredDailyStats]);

  const latestDay = useMemo(() => {
    return filteredDailyStats[filteredDailyStats.length - 1] || null;
  }, [filteredDailyStats]);

  const dailyBreakdownRows = useMemo(
    () => [...filteredDailyStats].reverse(),
    [filteredDailyStats]
  );
  const visibleDailyBreakdownRows = useMemo(
    () => dailyBreakdownRows.slice((dailyPage - 1) * dailyPageSize, dailyPage * dailyPageSize),
    [dailyBreakdownRows, dailyPage, dailyPageSize]
  );
  useEffect(() => {
    setDailyPage(1);
  }, [tokenDaysFilter]);
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(dailyBreakdownRows.length / dailyPageSize));
    setDailyPage((page) => Math.min(page, totalPages));
  }, [dailyBreakdownRows.length, dailyPageSize]);

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await getTokenSummary();
      if (!data || typeof data !== 'object') {
        throw new Error('Token Analytics returned an empty response');
      }
      setSummary(data);
    } catch (err) {
      console.error('Failed to load token analytics:', err);
      setLoadError(getTokenLoadError(err));
      setToastMessage('ไม่สามารถโหลดข้อมูล Token Analytics ได้');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    const requestId = ++historyRequestRef.current;
    setHistoryLoading(true);
    setHistoryError(null);

    try {
      const result = await getTokenHistory({
        limit: historyPageSize,
        page: historyPage,
        task: taskFilter === 'all' ? undefined : taskFilter,
        q: searchFilter.trim() || undefined,
      });
      if (requestId !== historyRequestRef.current) return;

      const events = Array.isArray(result?.events) ? result.events : [];
      setHistoryEvents(events);
      setHistoryTotal(typeof result?.total === 'number' ? result.total : null);
      setHistoryTotalPages(Math.max(1, Number(result?.total_pages) || 1));
    } catch (err) {
      if (requestId !== historyRequestRef.current) return;
      console.error('Failed to load token history:', err);
      setHistoryError('ไม่สามารถโหลดประวัติ Token ได้');
    } finally {
      if (requestId === historyRequestRef.current) {
        setHistoryLoading(false);
      }
    }
  }, [historyPage, historyPageSize, searchFilter, taskFilter]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary, refreshKey]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory, refreshKey]);

  const handleReset = async () => {
    setResetting(true);
    try {
      await resetTokenAnalytics();
      setToastMessage('รีเซ็ตสถิติโทเคนเรียบร้อยแล้ว');
      setShowResetModal(false);
      fetchSummary();
      fetchHistory();
    } catch (err) {
      setToastMessage('เกิดข้อผิดพลาดในการรีเซ็ต: ' + err.message);
    } finally {
      setResetting(false);
    }
  };

  const handleClearAlerts = async () => {
    try {
      await clearTokenAlerts();
      setToastMessage('ล้างประวัติแจ้งเตือนเรียบร้อยแล้ว');
      fetchSummary();
      fetchHistory();
    } catch (err) {
      setToastMessage('ไม่สามารถล้างแจ้งเตือนได้: ' + err.message);
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

  const recentEvents = historyEvents;
  const alerts = summary?.alerts || [];
  const keyStatus = summary?.key_status || {};

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

  const visibleHistoryPages = useMemo(() => {
    const start = Math.max(1, Math.min(historyPage - 2, historyTotalPages - 4));
    const end = Math.min(historyTotalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }, [historyPage, historyTotalPages]);

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

  // Keep Jev visible in the model inventory even before its first metered call.
  const modelUsage = useMemo(() => ({
    ...(summary?.tokens_by_model || {}),
    'Jev (TypeSafe)': Number(summary?.tokens_by_model?.['Jev (TypeSafe)'] || 0),
  }), [summary?.tokens_by_model]);
  const modelChartData = useMemo(() => {
    return Object.entries(modelUsage).map(([modelName, tokens]) => ({
      label: modelName,
      value: tokens,
    }));
  }, [modelUsage]);

  const taskChartData = useMemo(() => {
    return Object.entries(summary?.tokens_by_task || {}).map(([taskKey, tokens]) => ({
      label: getTaskBadge(taskKey).label,
      value: tokens,
    }));
  }, [summary?.tokens_by_task]);

  if (loading && !summary) {
    return (
      <div className="space-y-6 animate-fadeIn pb-12" role="status" aria-live="polite">
        <div className="glass-panel min-h-40 p-6 rounded-2xl border border-white/[0.08] flex items-center justify-center gap-3 text-sm text-slate-300">
          <RotateCcw className="w-4 h-4 animate-spin text-[#25F4EE]" />
          กำลังโหลดข้อมูล Token Analytics...
        </div>
      </div>
    );
  }

  if (!summary && loadError) {
    return (
      <div className="space-y-6 animate-fadeIn pb-12">
        <div className="glass-panel p-6 rounded-2xl border border-rose-500/30 bg-rose-500/[0.06]" role="alert">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0 text-rose-300" />
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-bold text-white">โหลด Token Analytics ไม่สำเร็จ</h2>
              <p className="mt-1 text-xs text-rose-100/80 break-words">{loadError}</p>
              <button
                type="button"
                onClick={fetchSummary}
                disabled={loading}
                className="mt-4 inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-rose-300/30 bg-rose-400/10 text-xs font-bold text-rose-100 hover:bg-rose-400/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                ลองใหม่
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
      {loadError && (
        <div className="glass-panel p-4 rounded-2xl border border-amber-500/30 bg-amber-500/[0.06]" role="alert">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-300" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-amber-100">รีเฟรช Token Analytics ไม่สำเร็จ จึงกำลังแสดงข้อมูลครั้งล่าสุด</p>
              <p className="mt-1 text-[11px] text-amber-100/70 break-words">{loadError}</p>
              <button
                type="button"
                onClick={fetchSummary}
                disabled={loading}
                className="mt-2 inline-flex items-center gap-1.5 text-[11px] font-bold text-amber-100 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RotateCcw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
                ลองใหม่
              </button>
            </div>
          </div>
        </div>
      )}
      {loading && summary && (
        <div className="text-[11px] text-slate-400 flex items-center gap-2" role="status" aria-live="polite">
          <RotateCcw className="w-3 h-3 animate-spin text-[#25F4EE]" />
          กำลังรีเฟรชข้อมูล Token Analytics...
        </div>
      )}
      {/* ── AI Key Health & Quota Alerts Center ── */}
      <div className="glass-panel p-5 rounded-2xl border border-white/[0.08] relative overflow-hidden space-y-4 shadow-lg">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                สถานะ AI API Keys & ระบบสลับคีย์อัตโนมัติ (Multi-Key Failover)
              </h3>
              <p className="text-xs text-slate-400">
                เมื่อโมเดล 3.1 บน Key 1 ชน Rate-Limit (429) ระบบจะเด้งไปใช้ Key 2 ทันที ก่อนลดระดับเป็น 2.5
              </p>
            </div>
          </div>
          {alerts.length > 0 && (
            <button
              onClick={handleClearAlerts}
              className="text-xs text-slate-400 hover:text-white px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              ล้างประวัติแจ้งเตือน
            </button>
          )}
        </div>

        {/* Key Health Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Object.keys(keyStatus).length === 0 ? (
            <div className="text-xs text-slate-400 col-span-2 py-2">
              กำลังตรวจสอบสถานะ API Keys...
            </div>
          ) : (
            Object.entries(keyStatus).map(([keyName, info]) => {
              const isRateLimited = info.status === 'rate_limited';
              return (
                <div
                  key={keyName}
                  className={`p-3.5 rounded-xl border transition-all ${
                    isRateLimited
                      ? 'bg-amber-500/[0.06] border-amber-500/30'
                      : 'bg-white/[0.02] border-white/[0.06]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5 text-slate-400" />
                      {keyName}
                    </span>
                    {isRateLimited ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                        <AlertTriangle className="w-3 h-3 text-amber-400" />
                        ติด Rate-Limit 429 ชั่วคราว
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        ปกติ พร้อมใช้งาน
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {info.message}
                  </p>
                </div>
              );
            })
          )}
        </div>

        {/* Alerts List Banner (if any recent alerts) */}
        {alerts.length > 0 && (
          <div className="mt-2 space-y-2 pt-2 border-t border-white/[0.04]">
            <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
              บันทึกเหตุการณ์และการสลับคีย์อัตโนมัติล่าสุด:
            </div>
            <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
              {alerts.slice(0, 5).map((alt) => {
                const isWarn = alt.level === 'warning' || alt.error_type === 'RATE_LIMIT_429';
                const timeStr = alt.timestamp ? new Date(alt.timestamp).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
                return (
                  <div
                    key={alt.id}
                    className={`text-xs px-3 py-2 rounded-lg border flex items-center justify-between gap-3 ${
                      isWarn
                        ? 'bg-amber-500/[0.08] border-amber-500/20 text-amber-200'
                        : 'bg-emerald-500/[0.08] border-emerald-500/20 text-emerald-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {isWarn ? (
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                      ) : (
                        <Sparkles className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                      )}
                      <span className="truncate">{alt.message}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 whitespace-nowrap">
                      {timeStr}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

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
            <div className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              {totals.total_tokens.toLocaleString()}
            </div>
            <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400">
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
            <div className="text-2xl sm:text-3xl font-black text-emerald-400 tracking-tight flex items-baseline gap-1">
              ฿{totals.total_cost_saved_thb.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              <span className="text-xs font-bold text-slate-400">บาท</span>
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
            <div className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              {totals.total_calls.toLocaleString()} <span className="text-sm font-semibold text-slate-400">ครั้ง</span>
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
            <div className="text-2xl sm:text-3xl font-black text-amber-300 tracking-tight">
              {totals.avg_latency_seconds} <span className="text-sm font-semibold text-slate-400">วินาที</span>
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
        <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-white/[0.08] space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#25F4EE]" />
              <h3 className="text-sm font-bold text-white">สัดส่วนการใช้งานตามโมเดล (Models)</h3>
            </div>
            <span className="text-xs text-slate-400">{Object.keys(modelUsage).length} โมเดล</span>
          </div>

          {modelChartData.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-6">ยังไม่มีประวัติการเรียกใช้โมเดล</p>
          ) : (
            <div className="flex flex-col sm:flex-row items-center gap-5 pt-1">
              <div className="flex-shrink-0 flex justify-center">
                <DonutChart
                  data={modelChartData}
                  size={125}
                  strokeWidth={17}
                  centerLabel="โมเดลรวม"
                  centerValue={totals.total_tokens >= 1000 ? `${(totals.total_tokens / 1000).toFixed(0)}k` : totals.total_tokens}
                  unit="tok"
                  showLegend={false}
                />
              </div>
              <div className="flex-1 w-full space-y-2.5">
                {Object.entries(modelUsage).map(([modelName, tokens]) => {
                  const total = totals.total_tokens || 1;
                  const percent = Math.round((tokens / total) * 100);
                  const calls = summary?.calls_by_model?.[modelName] || 0;
                  const isJev = modelName === 'Jev (TypeSafe)';
                  const isPro = !isJev && (modelName.includes('3.8') || modelName.includes('pro') || modelName.includes('claude'));

                  return (
                    <div key={modelName} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{modelName}</span>
                          {isJev ? (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-violet-500/20 text-violet-300 border border-violet-500/30">
                              DECISION
                            </span>
                          ) : isPro ? (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#FE2C55]/20 text-[#25F4EE] border border-[#25F4EE]/30">
                              PRO
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                              FREE
                            </span>
                          )}
                        </div>
                        <div className="text-slate-400 text-[11px]">
                          <span className="text-white font-bold">{tokens.toLocaleString()}</span> tok ({percent}%) • {calls} ครั้ง
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-white/[0.05] rounded-full overflow-hidden">
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
                })}
              </div>
            </div>
          )}
        </div>

        {/* Section B: Tasks Breakdown */}
        <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-white/[0.08] space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-bold text-white">สัดส่วนตามประเภทงาน (Tasks)</h3>
            </div>
            <span className="text-xs text-slate-400">{Object.keys(summary?.tokens_by_task || {}).length} หมวดหมู่งาน</span>
          </div>

          {taskChartData.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-6">ยังไม่มีประวัติการทำ Task</p>
          ) : (
            <div className="flex flex-col sm:flex-row items-center gap-5 pt-1">
              <div className="flex-shrink-0 flex justify-center">
                <DonutChart
                  data={taskChartData}
                  size={125}
                  strokeWidth={17}
                  centerLabel="งานทั้งหมด"
                  centerValue={totals.total_calls}
                  unit="ครั้ง"
                  showLegend={false}
                />
              </div>
              <div className="flex-1 w-full space-y-2.5">
                {Object.entries(summary.tokens_by_task).map(([taskKey, tokens]) => {
                  const total = totals.total_tokens || 1;
                  const percent = Math.round((tokens / total) * 100);
                  const calls = summary?.calls_by_task?.[taskKey] || 0;
                  const badge = getTaskBadge(taskKey);
                  const Icon = badge.icon;

                  return (
                    <div key={taskKey} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <Icon className="w-3.5 h-3.5 text-slate-400" />
                          <span className="font-semibold text-slate-200">{badge.label}</span>
                        </div>
                        <div className="text-slate-400 text-[11px]">
                          <span className="text-white font-bold">{tokens.toLocaleString()}</span> tok ({percent}%) • {calls} ครั้ง
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-white/[0.05] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-500"
                          style={{ width: `${Math.max(percent, 3)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Daily Activity Chart ── */}
      {summary?.daily_stats && summary.daily_stats.length > 0 && (
        <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-white/[0.08] space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">ประวัติการใช้งานย้อนหลัง (Daily Token Volume)</h3>
              </div>
              <p className="text-xs text-slate-400">กราฟแนวโน้มปริมาณโทเคนและมูลค่าที่ประหยัดได้ในแต่ละวัน</p>
            </div>

            {/* Time Filter Controls */}
            <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-xl border border-white/[0.08] self-start sm:self-auto">
              {[
                { id: '7', label: '7 วัน' },
                { id: '14', label: '14 วัน' },
                { id: '30', label: '30 วัน' },
                { id: 'all', label: `ทั้งหมด (${summary.daily_stats.length} วัน)` },
              ].map((btn) => (
                <button
                  key={btn.id}
                  type="button"
                  onClick={() => setTokenDaysFilter(btn.id)}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                    tokenDaysFilter === btn.id
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
                  }`}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>

          {/* Pure SVG Area & Line Chart */}
          <div className="pt-1">
            <AreaLineChart
              data={filteredDailyStats}
              height={140}
              valueKey="tokens"
              dateKey="date"
              secondaryKey="cost_saved_thb"
              lineColor="#25F4EE"
              gradientFrom="#25F4EE"
              gradientTo="#3B82F6"
            />
          </div>

          {/* ── High-Level Performance KPI Strip (Replaces the clunky 100-box grid) ── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
            {/* Peak Day */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] hover:border-amber-500/30 transition-all flex flex-col justify-between space-y-1.5">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="flex items-center gap-1.5 font-medium">
                  <Flame className="w-3.5 h-3.5 text-amber-400" />
                  วันใช้งานสูงสุด
                </span>
                <span className="text-[10px] text-slate-500 font-mono">{peakDay?.date || '-'}</span>
              </div>
              <div className="text-lg font-black text-white">
                {peakDay ? (peakDay.tokens >= 1000 ? `${(peakDay.tokens / 1000).toFixed(1)}k` : peakDay.tokens) : 0}{' '}
                <span className="text-xs font-normal text-slate-400">โทเคน</span>
              </div>
              <div className="text-[11px] text-amber-300/90 font-medium">
                เรียกใช้งาน {peakDay?.calls || 0} ครั้ง
              </div>
            </div>

            {/* Daily Average */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] hover:border-cyan-500/30 transition-all flex flex-col justify-between space-y-1.5">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="flex items-center gap-1.5 font-medium">
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  เฉลี่ยต่อวัน
                </span>
                <span className="text-[10px] text-cyan-400/80 font-medium">{filteredDailyStats.length} วัน</span>
              </div>
              <div className="text-lg font-black text-white">
                {dailyAvgTokens >= 1000 ? `${(dailyAvgTokens / 1000).toFixed(1)}k` : dailyAvgTokens}{' '}
                <span className="text-xs font-normal text-slate-400">โทเคน/วัน</span>
              </div>
              <div className="text-[11px] text-slate-400">
                ปริมาณเฉลี่ยในช่วงเวลา
              </div>
            </div>

            {/* Total Saved */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] hover:border-emerald-500/30 transition-all flex flex-col justify-between space-y-1.5">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="flex items-center gap-1.5 font-medium">
                  <PiggyBank className="w-3.5 h-3.5 text-emerald-400" />
                  ประหยัดสะสม
                </span>
                <span className="text-[10px] text-emerald-400/80 font-medium">THB</span>
              </div>
              <div className="text-lg font-black text-emerald-400">
                ฿{totalSavedInPeriod}
              </div>
              <div className="text-[11px] text-slate-400">
                ประหยัดจาก Local Cache & Prompts
              </div>
            </div>

            {/* Latest Activity */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] hover:border-blue-500/30 transition-all flex flex-col justify-between space-y-1.5">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="flex items-center gap-1.5 font-medium">
                  <Calendar className="w-3.5 h-3.5 text-blue-400" />
                  บันทึกล่าสุด
                </span>
                <span className="text-[10px] text-slate-500 font-mono">{latestDay?.date || '-'}</span>
              </div>
              <div className="text-lg font-black text-white">
                {latestDay ? (latestDay.tokens >= 1000 ? `${(latestDay.tokens / 1000).toFixed(1)}k` : latestDay.tokens) : 0}{' '}
                <span className="text-xs font-normal text-slate-400">โทเคน</span>
              </div>
              <div className="text-[11px] text-emerald-400 font-medium">
                ฿{latestDay?.cost_saved_thb || 0} ประหยัด ({latestDay?.calls || 0} ครั้ง)
              </div>
            </div>
          </div>

          {/* ── Optional Collapsible Detailed Breakdown Table ── */}
          <div className="pt-1">
            <button
              type="button"
              onClick={() => setShowDailyBreakdown((prev) => !prev)}
              className="w-full flex items-center justify-between px-3.5 py-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] text-xs text-slate-300 font-medium transition-all cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                <span>ดูรายละเอียดตารางรายวัน ({filteredDailyStats.length} วัน)</span>
              </span>
              <span className="flex items-center gap-1 text-[11px] text-slate-400">
                <span>{showDailyBreakdown ? 'ซ่อนตาราง' : 'แสดงตาราง'}</span>
                {showDailyBreakdown ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </span>
            </button>

            {showDailyBreakdown && (
              <div className="mt-2.5 rounded-xl border border-white/[0.06] bg-black/40 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-white/[0.04] text-slate-400 font-semibold border-b border-white/[0.06] sticky top-0 backdrop-blur-md">
                    <tr>
                      <th className="py-2 px-3">วันที่</th>
                      <th className="py-2 px-3">ปริมาณโทเคน</th>
                      <th className="py-2 px-3">มูลค่าประหยัด</th>
                      <th className="py-2 px-3 text-right">จำนวนครั้ง</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04] text-slate-300">
                    {visibleDailyBreakdownRows.map((day) => (
                      <tr key={day.date} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-2 px-3 font-mono text-white">{day.date}</td>
                        <td className="py-2 px-3 font-bold text-white">
                          {Number(day.tokens).toLocaleString()}
                        </td>
                        <td className="py-2 px-3 text-emerald-400 font-medium">
                          ฿{day.cost_saved_thb}
                        </td>
                        <td className="py-2 px-3 text-right text-slate-400">
                          {day.calls} ครั้ง
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <PaginationControls
                  page={dailyPage}
                  pageSize={dailyPageSize}
                  totalItems={dailyBreakdownRows.length}
                  onPageChange={setDailyPage}
                  onPageSizeChange={(size) => {
                    setDailyPageSize(size);
                    setDailyPage(1);
                  }}
                  itemLabel="วัน"
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Detailed Audit Log / Ledger ── */}
      <div className="glass-panel rounded-2xl border border-white/[0.08] overflow-hidden">
        {/* Table Header Controls */}
        <div className="p-4 sm:p-5 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white/[0.02]">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#25F4EE]" />
            <h3 className="text-sm font-bold text-white">ประวัติการเรียกใช้งาน AI ล่าสุด (Audit Log)</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/[0.08] text-slate-300">
              {historyTotal ?? filteredEvents.length} รายการ
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
                onChange={(e) => {
                  setSearchFilter(e.target.value);
                  setHistoryPage(1);
                }}
                className="pl-8 pr-3 py-1.5 rounded-xl bg-black/40 border border-white/[0.1] text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]/50 w-44 sm:w-56"
              />
            </div>

            <select
              value={taskFilter}
              onChange={(e) => {
                setTaskFilter(e.target.value);
                setHistoryPage(1);
              }}
              className="py-1.5 px-2.5 rounded-xl bg-black/40 border border-white/[0.1] text-xs text-slate-200 focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer"
            >
              <option value="all">ทุกงาน (All Tasks)</option>
              <option value="script">สคริปต์ 2 ภาษา (Script)</option>
              <option value="vision_match">ตรวจฟุตเทจ (Vision)</option>
              <option value="tts">พากย์เสียง (TTS)</option>
              <option value="product_enrich">วิเคราะห์จุดขาย</option>
            </select>

            <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-400 whitespace-nowrap">
              <span>ต่อหน้า</span>
              <select
                value={historyPageSize}
                onChange={(e) => {
                  setHistoryPageSize(Number(e.target.value));
                  setHistoryPage(1);
                }}
                className="py-1.5 px-2 rounded-xl bg-black/40 border border-white/[0.1] text-xs text-slate-200 focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer"
                aria-label="จำนวนประวัติต่อหน้า"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
              <span>รายการ</span>
            </label>
          </div>
        </div>

        {/* Table Container */}
        <div className="overflow-x-auto touch-pan-x pb-2 no-scrollbar">
          <table className="w-full text-left text-xs text-slate-300 min-w-[700px]">
            <thead className="bg-white/[0.03] text-slate-400 uppercase text-[10px] border-b border-white/[0.06]">
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
              {historyLoading && filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-400">
                    <RotateCcw className="w-4 h-4 animate-spin text-[#25F4EE] inline-block mr-2 align-[-2px]" />
                    กำลังโหลดประวัติ Token...
                  </td>
                </tr>
              ) : filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-500">
                    <p className="text-xs">ไม่พบข้อมูลประวัติที่ตรงกับเงื่อนไข</p>
                  </td>
                </tr>
              ) : (
                filteredEvents.map((ev) => {
                  const badge = getTaskBadge(ev.task);
                  const Icon = badge.icon;
                  const dateTime = formatAuditDateTime(ev.timestamp);

                  return (
                    <tr key={ev.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 px-4 text-[11px] text-slate-400 whitespace-nowrap">
                        <div>{dateTime.date}</div>
                        <div className="text-[10px] text-slate-500">{dateTime.time}</div>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-semibold ${badge.color}`}>
                          <Icon className="w-3 h-3" />
                          {badge.label}
                        </span>
                      </td>
                      <td className="py-3 px-4 max-w-[180px] truncate font-medium text-slate-200">
                        {ev.project_name || '-'}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap space-y-1">
                        <div className="text-[11px] text-slate-300 font-semibold">{ev.model}</div>
                        <div>{getProviderBadge(ev.provider)}</div>
                      </td>
                      <td className="py-3 px-4 text-right text-[11px] text-slate-400 whitespace-nowrap">
                        <span className="text-cyan-400">{ev.input_tokens.toLocaleString()}</span> /{' '}
                        <span className="text-emerald-400">{ev.output_tokens.toLocaleString()}</span>
                        {ev.thinking_tokens > 0 && (
                          <span className="text-purple-400 block text-[10px]">+{ev.thinking_tokens} think</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-white whitespace-nowrap">
                        {ev.total_tokens.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right text-amber-300 whitespace-nowrap">
                        {ev.latency_seconds > 0 ? `${ev.latency_seconds}s` : '-'}
                      </td>
                      <td className="py-3 px-4 text-right text-emerald-400 font-bold whitespace-nowrap">
                        ฿{ev.cost_saved_thb}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 px-4 py-3 border-t border-white/[0.06] bg-white/[0.015]">
          <p className="text-[11px] text-slate-500" role={historyError ? 'alert' : undefined}>
            {historyError || (filteredEvents.length > 0
              ? `หน้า ${historyPage} จาก ${historyTotalPages} · แสดง ${filteredEvents.length} จาก ${historyTotal ?? filteredEvents.length} รายการ`
              : 'ประวัติจะโหลดเมื่อมีข้อมูล')}
          </p>
          <nav className="flex items-center gap-1" aria-label="หน้าประวัติ Token">
            <button
              type="button"
              onClick={() => setHistoryPage(1)}
              disabled={historyLoading || historyPage <= 1}
              className="px-2 py-1.5 rounded-lg border border-white/[0.1] text-xs text-slate-300 hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="หน้าแรก"
            >
              «
            </button>
            <button
              type="button"
              onClick={() => setHistoryPage((page) => Math.max(1, page - 1))}
              disabled={historyLoading || historyPage <= 1}
              className="px-2.5 py-1.5 rounded-lg border border-white/[0.1] text-xs text-slate-300 hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="หน้าก่อนหน้า"
            >
              ‹
            </button>
            {visibleHistoryPages.map((page) => (
              <button
                key={page}
                type="button"
                onClick={() => setHistoryPage(page)}
                disabled={historyLoading && page === historyPage}
                aria-current={page === historyPage ? 'page' : undefined}
                className={`min-w-8 px-2 py-1.5 rounded-lg border text-xs font-bold transition-colors ${
                  page === historyPage
                    ? 'border-[#25F4EE]/50 bg-[#25F4EE]/15 text-[#25F4EE]'
                    : 'border-white/[0.1] text-slate-300 hover:bg-white/[0.08]'
                } disabled:opacity-50`}
              >
                {page}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setHistoryPage((page) => Math.min(historyTotalPages, page + 1))}
              disabled={historyLoading || historyPage >= historyTotalPages}
              className="px-2.5 py-1.5 rounded-lg border border-white/[0.1] text-xs text-slate-300 hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="หน้าถัดไป"
            >
              ›
            </button>
            <button
              type="button"
              onClick={() => setHistoryPage(historyTotalPages)}
              disabled={historyLoading || historyPage >= historyTotalPages}
              className="px-2 py-1.5 rounded-lg border border-white/[0.1] text-xs text-slate-300 hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="หน้าสุดท้าย"
            >
              »
            </button>
          </nav>
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
};

export default TokenDashboard;
