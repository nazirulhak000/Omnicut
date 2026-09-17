import React, { useState } from 'react';
import {
  Zap, CheckCircle2, AlertCircle, Clock, X, Trash2, ArrowRight,
  Loader2, Sparkles, Film, Rocket, Mic, RefreshCw, Layers, ExternalLink, Play, Scissors, ImagePlus, Trophy, Eye
} from 'lucide-react';
import { useTaskManager } from '../context/TaskContext';
import { getRenderStatus } from '../api';
import { ACTIVE_RENDER_STORAGE_KEY } from '../lib/renderJobModel';

function getTaskIcon(type) {
  switch (type) {
    case 'scrape_and_plan':
      return <Rocket className="w-4 h-4 text-[#25F4EE]" />;
    case 'render_video':
      return <Film className="w-4 h-4 text-[#FE2C55]" />;
    case 'edit_project':
    case 'one_click':
      return <Scissors className="w-4 h-4 text-[#25F4EE]" />;
    case 'voice_gen':
      return <Mic className="w-4 h-4 text-amber-400" />;
    case 'image_metadata':
      return <ImagePlus className="w-4 h-4 text-violet-300" />;
    case 'scene_indexing':
      return <Eye className="w-4 h-4 text-emerald-400" />;
    default:
      return <Zap className="w-4 h-4 text-[#25F4EE]" />;
  }
}

function isImageMetadataTask(task) {
  return task?.type === 'image_metadata' || task?.task_type === 'image_metadata';
}

function getStatusBadge(status) {
  switch (status) {
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 animate-pulse">
          <Loader2 className="w-2.5 h-2.5 animate-spin" />
          กำลังประมวลผล
        </span>
      );
    case 'queued':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30">
          <Clock className="w-2.5 h-2.5" />
          รอคิว
        </span>
      );
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
          <CheckCircle2 className="w-2.5 h-2.5" />
          เสร็จสมบูรณ์
        </span>
      );
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30">
          <AlertCircle className="w-2.5 h-2.5" />
          ล้มเหลว
        </span>
      );
    case 'cancelled':
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-500/15 text-slate-400 border border-slate-500/30">
          ยกเลิกแล้ว
        </span>
      );
    default:
      return null;
  }
}

export function ActivityIndicatorButton({ className = '' }) {
  const {
    activeCount,
    activeTasks,
    toggleActivityDrawer,
    tasks,
    viralMilestones = [],
    isActivityDrawerOpen,
    taskSyncState,
  } = useTaskManager();
  const hasViral = viralMilestones.some(m => m.views >= 10000);
  const isStale = taskSyncState?.status === 'stale';

  if (activeCount > 0) {
    const primaryTask = activeTasks[0];
    const pct = Math.round((primaryTask?.progress || 0) * 100);

    return (
      <button
        type="button"
        onClick={toggleActivityDrawer}
        aria-haspopup="dialog"
        aria-expanded={isActivityDrawerOpen}
        aria-controls="activity-drawer"
        aria-label={`${activeCount} งานกำลังประมวลผล ${pct}% เปิดศูนย์ติดตามกิจกรรม${isStale ? ' ข้อมูลอาจไม่ใช่ข้อมูลล่าสุด' : ''}`}
        className={`px-2.5 sm:px-3 py-1 rounded-xl bg-gradient-to-r from-[#25F4EE]/15 to-[#FE2C55]/15 hover:from-[#25F4EE]/25 hover:to-[#FE2C55]/25 border border-[#25F4EE]/40 text-[#25F4EE] shadow-lg shadow-[#25F4EE]/10 flex items-center gap-2 cursor-pointer transition-all active:scale-95 group ${className}`}
        title="คลิกเพื่อเปิดศูนย์ติดตามกิจกรรม (Activity Center)"
      >
        <div className="relative flex items-center justify-center">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-[#25F4EE]" />
          <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-[#FE2C55] animate-ping" />
        </div>
        <div className="flex items-center gap-1.5 text-xs font-bold font-mono">
          <span className="text-white">{activeCount} งาน</span>
          <span className="text-[#25F4EE]">({pct}%)</span>
          {isStale && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" title="ข้อมูลกิจกรรมอาจไม่ใช่ข้อมูลล่าสุด" />}
        </div>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggleActivityDrawer}
      aria-haspopup="dialog"
      aria-expanded={isActivityDrawerOpen}
      aria-controls="activity-drawer"
      aria-label={`เปิดศูนย์ติดตามกิจกรรม${isStale ? ' ข้อมูลอาจไม่ใช่ข้อมูลล่าสุด' : ''}`}
      className={`p-1.5 sm:px-2.5 sm:py-1 rounded-xl bg-black/40 hover:bg-white/[0.08] active:bg-white/[0.12] border border-white/[0.08] text-slate-300 hover:text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors ${className}`}
      title="ศูนย์ติดตามกิจกรรม (Activity Center)"
    >
      {hasViral ? (
        <span className="relative flex items-center justify-center">
          <Trophy className="w-3.5 h-3.5 text-amber-400" />
          <span className="absolute -top-1 -right-1 w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
        </span>
      ) : (
        <Layers className="w-3.5 h-3.5 text-[#25F4EE]" />
      )}
      <span className="hidden sm:inline">กิจกรรม</span>
      {tasks.length > 0 && (
        <span className="px-1.5 py-0.2 rounded-full bg-white/[0.08] text-[10px] font-mono text-slate-400">
          {tasks.length}
        </span>
      )}
      {isStale && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" title="ข้อมูลกิจกรรมอาจไม่ใช่ข้อมูลล่าสุด" />}
    </button>
  );
}

export function ActivityDrawer() {
  const {
    tasks,
    activeTasks,
    activeCount,
    isActivityDrawerOpen,
    setIsActivityDrawerOpen,
    cancelTask,
    deleteTask,
    clearCompleted,
    jumpToTaskResult,
    viralMilestones = [],
    fetchViralMilestones,
    taskSyncState,
  } = useTaskManager();

  const [tabFilter, setTabFilter] = useState('all'); // all | active | completed | viral
  const drawerRef = React.useRef(null);

  React.useEffect(() => {
    if (tabFilter === 'viral' && fetchViralMilestones) {
      fetchViralMilestones();
    }
  }, [tabFilter, fetchViralMilestones]);

  React.useEffect(() => {
    if (!isActivityDrawerOpen) return undefined;
    const previouslyFocused = document.activeElement;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setIsActivityDrawerOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    drawerRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [isActivityDrawerOpen, setIsActivityDrawerOpen]);

  if (!isActivityDrawerOpen) return null;

  const viralCount = viralMilestones.length;

  const filteredTasks = tasks.filter(t => {
    if (tabFilter === 'active') return t.status === 'processing' || t.status === 'queued';
    if (tabFilter === 'completed') return t.status === 'completed';
    return true;
  });

  return (
    <div className="fixed inset-0 z-[100] w-screen h-[100dvh] max-h-[100dvh] overflow-hidden flex justify-end animate-fadeIn overscroll-none" role="presentation">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-md transition-opacity"
        aria-hidden="true"
        onClick={() => setIsActivityDrawerOpen(false)}
      />

      {/* Slide-over Panel */}
      <aside
        ref={drawerRef}
        id="activity-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="activity-drawer-title"
        tabIndex={-1}
        className="relative w-full max-w-full sm:max-w-md bg-[#080B11]/95 backdrop-blur-2xl border-l border-white/[0.12] shadow-2xl flex flex-col h-[100dvh] max-h-[100dvh] z-10 animate-slideLeft overflow-hidden"
      >
        {/* Header */}
        <div className="p-4 border-b border-white/[0.08] flex items-center justify-between bg-black/40">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 text-[#25F4EE]">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 id="activity-drawer-title" className="text-sm font-black text-white flex items-center gap-2">
                ศูนย์ติดตามกิจกรรม
                {activeCount > 0 && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/30 animate-pulse">
                    {activeCount} กำลังทำงาน
                  </span>
                )}
              </h2>
              <p className="text-[11px] text-slate-400">สถานะงานเบื้องหลัง & แจ้งเตือนยอดคลิป</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {tasks.filter(t => t.status === 'completed' || t.status === 'failed' || t.status === 'cancelled').length > 0 && (
              <button
                type="button"
                onClick={clearCompleted}
                aria-label="ล้างรายการงานที่เสร็จแล้ว"
                className="min-h-[36px] min-w-[36px] flex items-center justify-center p-2 text-slate-400 hover:text-rose-400 hover:bg-white/[0.06] rounded-xl transition-colors cursor-pointer"
                title="ล้างงานที่เสร็จสิ้นแล้ว"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsActivityDrawerOpen(false)}
              aria-label="ปิดศูนย์ติดตามกิจกรรม"
              className="min-h-[36px] min-w-[36px] flex items-center justify-center p-2 text-slate-400 hover:text-white hover:bg-white/[0.06] rounded-xl transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {taskSyncState?.status === 'stale' && (
          <div
            role="status"
            aria-live="polite"
            className="mx-3 mt-3 rounded-xl border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200"
          >
            เชื่อมต่อ backend ไม่สำเร็จ ข้อมูลกิจกรรมที่แสดงอาจไม่ใช่ข้อมูลล่าสุด
          </div>
        )}

        {/* Filter Tabs */}
        <div
          role="tablist"
          aria-label="ตัวกรองกิจกรรม"
          className="px-3 sm:px-4 py-2 border-b border-white/[0.06] flex items-center justify-between gap-1 bg-black/20 overflow-x-auto no-scrollbar"
        >
          {[
            { id: 'all', label: `ทั้งหมด (${tasks.length})` },
            { id: 'active', label: `กำลังทำ (${activeCount})` },
            { id: 'completed', label: `เสร็จ (${tasks.filter(t => t.status === 'completed').length})` },
            { id: 'viral', label: `🔥 คลิปปัง (${viralCount})` }
          ].map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setTabFilter(tab.id)}
              id={`activity-tab-${tab.id}`}
              role="tab"
              aria-selected={tabFilter === tab.id}
              aria-controls="activity-tabpanel"
              className={`flex-1 min-h-[36px] py-1.5 px-2 rounded-xl text-xs font-bold cursor-pointer transition-all whitespace-nowrap text-center ${
                tabFilter === tab.id
                  ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Task List / Viral Milestones List */}
        <div
          id="activity-tabpanel"
          role="tabpanel"
          aria-labelledby={`activity-tab-${tabFilter}`}
          tabIndex={0}
          className="flex-1 overflow-y-auto p-4 space-y-3"
        >
          {tabFilter === 'viral' ? (
            viralMilestones.length === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-2">
                <Trophy className="w-8 h-8 opacity-40 text-amber-500" />
                <p className="text-xs">ยังไม่มีคลิปที่ยอดวิวทะลุ 1,000 วิว</p>
                <p className="text-[11px] text-slate-600">เมื่อซิงก์ข้อมูลจาก TikTok Studio แล้ว คลิปยอดวิวสูงจะโผล่ที่นี่ทันที</p>
              </div>
            ) : (
              viralMilestones.map(m => (
                <div
                  key={m.post_id}
                  className="p-3.5 rounded-xl border border-amber-500/30 bg-gradient-to-br from-[#0B0F19] to-amber-950/20 shadow-lg space-y-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 min-w-0">
                      <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 flex-shrink-0">
                        <Trophy className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <h3 className="text-xs font-bold text-white truncate">
                            {m.product_name}
                          </h3>
                          <span className="text-[10px] px-2 py-0.2 rounded-full font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            {m.tier_label}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300 mt-0.5 truncate">{m.hook || m.angle_title}</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 py-1.5 px-2.5 rounded-lg bg-black/40 border border-white/[0.05] text-center font-mono">
                    <div>
                      <div className="text-[9px] text-slate-400 font-sans">ยอดวิว</div>
                      <div className="text-xs font-bold text-amber-400">{m.views.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-400 font-sans">ไลก์</div>
                      <div className="text-xs font-bold text-slate-200">{m.likes.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-400 font-sans">แชร์</div>
                      <div className="text-xs font-bold text-cyan-400">{m.shares.toLocaleString()}</div>
                    </div>
                  </div>

                  {m.tiktok_url && (
                    <div className="flex items-center justify-end pt-1">
                      <a
                        href={m.tiktok_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] font-bold text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1"
                      >
                        <span>เปิดดูคลิปจริงบน TikTok</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                </div>
              ))
            )
          ) : filteredTasks.length === 0 ? (
            <div className="h-48 flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-2">
              <Layers className="w-8 h-8 opacity-40 text-slate-500" />
              <p className="text-xs">ไม่มีรายการกิจกรรมในหมวดนี้</p>
            </div>
          ) : (
            filteredTasks.map(task => {
              const isRunning = task.status === 'processing' || task.status === 'queued';
              const isDone = task.status === 'completed';
              const pct = Math.round((task.progress || 0) * 100);

              return (
                <div
                  key={task.id}
                  className={`p-3.5 rounded-xl border transition-all space-y-2.5 ${
                    isRunning
                      ? 'bg-[#0B0F19] border-[#25F4EE]/40 shadow-lg shadow-[#25F4EE]/5 ring-1 ring-[#25F4EE]/20'
                      : isDone
                      ? 'bg-[#080B11] border-emerald-500/20'
                      : 'bg-[#080B11] border-white/[0.06]'
                  }`}
                >
                  {/* Title Row */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 min-w-0">
                      <div className="mt-0.5 p-1.5 rounded-lg bg-black/40 border border-white/[0.08] flex-shrink-0">
                        {getTaskIcon(task.type || task.task_type)}
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-xs font-bold text-white truncate leading-snug">
                          {task.title}
                        </h3>
                        <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-500 font-mono">
                          <span>{task.created_at}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex-shrink-0">
                      {getStatusBadge(task.status)}
                    </div>
                  </div>

                  {/* Progress Bar & Dynamic Step Label */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className={`truncate font-medium ${isRunning ? 'text-cyan-300' : 'text-slate-400'}`}>
                        {task.step_label || 'กำลังทำงาน...'}
                      </span>
                      <span className="font-mono text-xs font-bold text-white flex-shrink-0 ml-2">
                        {pct}%
                      </span>
                    </div>

                    <div className="h-2 w-full bg-black/60 rounded-full overflow-hidden border border-white/[0.06]">
                      <div
                        className={`h-full rounded-full transition-all duration-300 relative overflow-hidden ${
                          isRunning
                            ? 'bg-gradient-to-r from-[#D97757] via-[#FF8A65] to-[#25F4EE]'
                            : isDone
                            ? 'bg-emerald-400'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${Math.max(4, pct)}%` }}
                      >
                        {isRunning && (
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full animate-shimmer" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Error Callout if Failed */}
                  {task.error && (
                    <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px]">
                      {task.error}
                    </div>
                  )}

                  {/* Actions Row */}
                  <div className="flex items-center justify-between pt-1 border-t border-white/[0.04]">
                    <span className="text-[10px] font-mono text-slate-500">ID: {task.id.slice(-8)}</span>
                    <div className="flex items-center gap-1.5">
                      {isRunning && (
                        <button
                          type="button"
                          onClick={() => cancelTask(task.id)}
                          className="px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-rose-500/20 text-white hover:text-rose-100 text-[11px] font-bold transition-colors cursor-pointer"
                        >
                          ยกเลิก
                        </button>
                      )}

                      {isDone && (() => {
                        const hasVideo = Boolean(
                          task.result?.mp4 ||
                          task.result?.mp4_video ||
                          task.result?.output_video ||
                          task.result?.final_video_path ||
                          task.result?.video_url
                        );
                        const isEditTask = Boolean(
                          task.type === 'edit_project' ||
                          task.type === 'one_click' ||
                          task.type === 'pipeline' ||
                          task.task_type === 'edit_project' ||
                          (typeof task.title === 'string' && task.title.includes('ตัดต่อ'))
                        );
                        // A true render task requires explicit render type AND has actual exported video
                        const isRealRenderTask = !isEditTask && (
                          task.type === 'render_video' ||
                          task.type === 'render' ||
                          task.task_type === 'render_video' ||
                          task.task_type === 'render' ||
                          (typeof task.title === 'string' && task.title.includes('เรนเดอร์'))
                        ) && hasVideo;

                        if (isRealRenderTask) {
                          return (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => jumpToTaskResult(task, 'gallery')}
                                className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                                title="พรีวิวดูคลิปที่เรนเดอร์เสร็จแล้วในคลังผลงาน"
                              >
                                <Play className="w-3.5 h-3.5 fill-current" />
                                <span>พรีวิวคลิป</span>
                              </button>
                              <button
                                onClick={() => jumpToTaskResult(task, 'editor')}
                                className="px-2.5 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1 cursor-pointer transition-all"
                                title="เปิดแก้ไขต่อในไทม์ไลน์"
                              >
                                <span>เปิดไทม์ไลน์</span>
                                <ArrowRight className="w-3 h-3" />
                              </button>
                            </div>
                          );
                        }

                        if (isImageMetadataTask(task)) {
                          return (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => jumpToTaskResult(task, 'flow')}
                                className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                                title="เปิดผลอ่านข้อมูลจากรูปเพื่อตรวจสอบก่อนบันทึก"
                              >
                                <span>ตรวจผลอ่านรูป</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          );
                        }

                        // For scrape_and_plan (วิเคราะห์สินค้า / เขียนสคริปต์):
                        // Show "เปิดดูสคริปต์" routing to Product -> Clip ('flow')
                        const isScrapeOrPlan = Boolean(
                          task.type === 'scrape_and_plan' ||
                          task.task_type === 'scrape_and_plan' ||
                          (typeof task.title === 'string' && task.title.includes('วิเคราะห์สินค้า'))
                        );

                        if (isScrapeOrPlan) {
                          return (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => jumpToTaskResult(task, 'flow')}
                                className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                                title="เปิดดูสคริปต์สินค้าในหน้าสินค้า → คลิป"
                              >
                                <span>เปิดดูสคริปต์</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          );
                        }

                        // For reroll_script: open the exact angle that was
                        // just rerolled, not a blank editor timeline.
                        const isRerollTask = Boolean(
                          task.type === 'reroll_script' ||
                          task.task_type === 'reroll_script'
                        );

                        if (isRerollTask) {
                          return (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => jumpToTaskResult(task, 'flow')}
                                className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                                title="เปิดสคริปต์ที่รีสคริปต์ใหม่"
                              >
                                <span>เปิดสคริปต์ที่รีแล้ว</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          );
                        }

                        // For generate_shot_list and batch_generate_audio (scripts/api_shot_lists.py):
                        // opens the product -> clip script page, same as
                        // reroll_script above -- this task never touches the
                        // timeline/editor at all.
                        const isShotListTask = Boolean(
                          task.type === 'generate_shot_list' ||
                          task.task_type === 'generate_shot_list' ||
                          task.type === 'batch_generate_audio' ||
                          task.task_type === 'batch_generate_audio' ||
                          (typeof task.title === 'string' && task.title.includes('เตรียมเสียงพากย์'))
                        );

                        if (isShotListTask) {
                          return (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => jumpToTaskResult(task, 'flow')}
                                className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                                title="เปิดดูสคริปต์และแผนถ่ายของสินค้านี้"
                              >
                                <span>เปิดหน้าสคริปต์</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          );
                        }

                        // For finalize_recording_session (scripts/api_recording.py):
                        // the guided-take video was just attached to a
                        // specific script's angle -- same "flow" page as
                        // shot-list generation, never the editor/timeline.
                        const isFinalizeRecordingTask = Boolean(
                          task.type === 'finalize_recording_session' ||
                          task.task_type === 'finalize_recording_session'
                        );

                        if (isFinalizeRecordingTask) {
                          return (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => jumpToTaskResult(task, 'flow')}
                                className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                                title="เปิดหน้าสคริปต์ที่เพิ่งถ่ายทำเสร็จ"
                              >
                                <span>เปิดหน้าสคริปต์</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          );
                        }

                        // For timeline cuts (edit_project / 1-click edit):
                        // Show ONLY "เปิดไทม์ไลน์" (Primary prominent button)
                        return (
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => jumpToTaskResult(task, 'editor')}
                              className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                              title="เปิดโปรเจกต์ในหน้าไทม์ไลน์เพื่อตรวจสอบหรือแก้ไข"
                            >
                              <span>เปิดไทม์ไลน์</span>
                              <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        );
                      })()}

                      {!isRunning && (
                        <button
                          type="button"
                          onClick={() => deleteTask(task.id)}
                          aria-label={`ลบรายการงาน ${task.title || task.id}`}
                          className="p-1 text-slate-500 hover:text-rose-400 rounded-md transition-colors cursor-pointer"
                          title="ลบรายการนี้"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>
    </div>
  );
}

export function GlobalTaskNotification() {
  const { notificationToast, setNotificationToast, jumpToTaskResult } = useTaskManager();

  if (!notificationToast) return null;

  const isSuccess = notificationToast.type === 'success';

  return (
    <div
      role={isSuccess ? 'status' : 'alert'}
      aria-live={isSuccess ? 'polite' : 'assertive'}
      aria-atomic="true"
      aria-label="การแจ้งเตือนงาน"
      className="fixed bottom-5 right-5 z-50 max-w-sm w-full animate-slideUp"
    >
      <div className={`p-4 rounded-2xl backdrop-blur-2xl border shadow-2xl space-y-3 ${
        isSuccess
          ? 'bg-[#080B11]/95 border-[#25F4EE]/40 shadow-[#25F4EE]/15 ring-1 ring-[#25F4EE]/30'
          : 'bg-[#080B11]/95 border-rose-500/40 shadow-rose-500/15'
      }`}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
              notificationToast.milestone
                ? 'bg-amber-500/20 text-amber-400'
                : isSuccess
                ? 'bg-[#25F4EE]/20 text-[#25F4EE]'
                : 'bg-rose-500/20 text-rose-400'
            }`}>
              {notificationToast.milestone ? (
                <Trophy className="w-4 h-4" />
              ) : isSuccess ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <AlertCircle className="w-4 h-4" />
              )}
            </div>
            <h4 className="text-xs font-bold text-white">
              {notificationToast.title}
            </h4>
          </div>
          <button
            type="button"
            onClick={() => setNotificationToast(null)}
            aria-label="ปิดการแจ้งเตือน"
            className="text-slate-400 hover:text-white p-1 rounded-md cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-snug">
          {notificationToast.message}
        </p>

        {notificationToast.milestone && (
          <div className="flex items-center justify-end gap-2 pt-1">
            {notificationToast.milestone.tiktok_url && (
              <a
                href={notificationToast.milestone.tiktok_url}
                target="_blank"
                rel="noreferrer"
                className="py-1.5 px-3 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-amber-500/10 cursor-pointer active:scale-95 transition-all"
              >
                <span>เปิดดูบน TikTok</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        )}

        {isSuccess && notificationToast.task && (() => {
          const task = notificationToast.task;
          const hasVideo = Boolean(
            task.result?.mp4 ||
            task.result?.mp4_video ||
            task.result?.output_video ||
            task.result?.final_video_path ||
            task.result?.video_url
          );
          const isEditTask = Boolean(
            task.type === 'edit_project' ||
            task.type === 'one_click' ||
            task.type === 'pipeline' ||
            task.task_type === 'edit_project' ||
            (typeof task.title === 'string' && task.title.includes('ตัดต่อ'))
          );
          const isRealRenderTask = !isEditTask && (
            task.type === 'render_video' ||
            task.type === 'render' ||
            task.task_type === 'render_video' ||
            task.task_type === 'render' ||
            (typeof task.title === 'string' && task.title.includes('เรนเดอร์'))
          ) && hasVideo;

          if (isRealRenderTask) {
            return (
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  onClick={() => jumpToTaskResult(task, 'gallery')}
                  className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>พรีวิวคลิปที่เสร็จทันที</span>
                </button>
              </div>
            );
          }

          if (isImageMetadataTask(task)) {
            return (
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  onClick={() => jumpToTaskResult(task, 'flow')}
                  className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                  title="เปิดผลอ่านข้อมูลจากรูปเพื่อตรวจสอบก่อนบันทึก"
                >
                  <span>ตรวจผลอ่านรูป</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          }

          const isScrapeOrPlan = Boolean(
            task.type === 'scrape_and_plan' ||
            task.task_type === 'scrape_and_plan' ||
            (typeof task.title === 'string' && task.title.includes('วิเคราะห์สินค้า'))
          );

          if (isScrapeOrPlan) {
            return (
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  onClick={() => jumpToTaskResult(task, 'flow')}
                  className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                >
                  <span>เปิดดูสคริปต์ทันที</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          }

          const isRerollTask = Boolean(
            task.type === 'reroll_script' ||
            task.task_type === 'reroll_script'
          );

          if (isRerollTask) {
            return (
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  onClick={() => jumpToTaskResult(task, 'flow')}
                  className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                >
                  <span>เปิดสคริปต์ที่รีแล้ว</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          }

          const isShotListTask = Boolean(
            task.type === 'generate_shot_list' ||
            task.task_type === 'generate_shot_list'
          );

          if (isShotListTask) {
            return (
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  onClick={() => jumpToTaskResult(task, 'flow')}
                  className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                >
                  <span>เปิดหน้าสคริปต์</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          }

          const isFinalizeRecordingTask = Boolean(
            task.type === 'finalize_recording_session' ||
            task.task_type === 'finalize_recording_session'
          );

          if (isFinalizeRecordingTask) {
            return (
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  onClick={() => jumpToTaskResult(task, 'flow')}
                  className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                >
                  <span>เปิดหน้าสคริปต์</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          }

          return (
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                onClick={() => jumpToTaskResult(task, 'editor')}
                className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
              >
                <span>เปิดหน้าไทม์ไลน์ทันที</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })()}
      </div>
    </div>
  );
}

export function GlobalLiveRenderWidget({ currentTab, onNavigateToEditor, onNavigateToGallery }) {
  const { activeTasks } = useTaskManager();
  const [liveStatus, setLiveStatus] = useState(null);
  const timerRef = React.useRef(null);

  // Poll /api/render/status/{jobId} directly — this gives the SAME data as terminal output
  React.useEffect(() => {
    function startPolling(jobId) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(async () => {
        try {
          const data = await getRenderStatus(jobId);
          setLiveStatus(data);
          if (['completed', 'done', 'failed', 'error', 'cancelled'].includes(data.status)) {
            clearInterval(timerRef.current);
            setTimeout(() => setLiveStatus(null), 4000); // linger 4s after done
          }
        } catch {
          clearInterval(timerRef.current);
          setLiveStatus(null);
        }
      }, 1000);
    }

    // Watch localStorage for active render job
    function checkStorage() {
      try {
        const raw = localStorage.getItem(ACTIVE_RENDER_STORAGE_KEY);
        if (!raw) { clearInterval(timerRef.current); setLiveStatus(null); return; }
        const { jobId } = JSON.parse(raw);
        if (jobId) startPolling(jobId);
      } catch { setLiveStatus(null); }
    }

    checkStorage();
    // Also re-check when storage changes (another tab)
    window.addEventListener('storage', checkStorage);
    return () => {
      window.removeEventListener('storage', checkStorage);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Decide what to show: prefer live render status, fall back to TaskManager
  const renderTask = activeTasks.find(
    (t) => ((t.type || t.task_type) === 'render_video' || (t.type || t.task_type) === 'render') &&
           (t.status === 'processing' || t.status === 'queued')
  );

  const liveStatusCode = String(liveStatus?.status || '').toLowerCase();
  const isLive   = liveStatus && ['processing', 'queued', 'rendering', 'completed', 'done'].includes(liveStatusCode);
  const isDone   = liveStatusCode === 'completed' || liveStatusCode === 'done';
  const isFailed = liveStatusCode === 'failed' || liveStatusCode === 'error';

  if (!isLive && !renderTask) return null;
  if (currentTab === 'editor' && !isDone && !isFailed) return null;

  const pct = isLive
    ? Math.round((liveStatus.progress || 0) * 100)
    : Math.round((renderTask?.progress || 0) * 100);

  const label = isLive
    ? (liveStatus.step_label || liveStatus.message || 'กำลังตัดต่อ...')
    : (renderTask?.step_label || 'กำลังประมวลผล...');

  const title = liveStatus?.title
    || renderTask?.payload?.project_name
    || renderTask?.title
    || 'กำลังตัดต่อวิดีโอ';

  const barColor = isDone
    ? 'from-emerald-500 to-emerald-400'
    : isFailed
    ? 'from-red-500 to-red-400'
    : 'from-[#D97757] via-[#FF8A65] to-[#25F4EE]';

  const borderColor = isDone ? 'border-emerald-500/40 ring-emerald-500/20' : isFailed ? 'border-red-500/40 ring-red-500/20' : 'border-[#D97757]/40 ring-[#D97757]/20';

  return (
    <div className="fixed bottom-20 md:bottom-5 right-4 z-40 w-[92%] max-w-sm animate-slideUp">
      <div className={`p-3 rounded-2xl bg-[#080B11]/95 border ${borderColor} shadow-2xl backdrop-blur-2xl flex items-center justify-between gap-3 ring-1`}>
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${isDone ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400' : 'bg-[#D97757]/15 border border-[#D97757]/30 text-[#D97757]'}`}>
            {isDone
              ? <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              : <Loader2 className="w-4 h-4 animate-spin" />
            }
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between text-xs font-bold text-white mb-1">
              <span className="truncate">{isDone ? 'ตัดต่อเสร็จแล้ว!' : title}</span>
              <span className={`font-mono ml-2 flex-shrink-0 ${isDone ? 'text-emerald-400' : 'text-[#E89274]'}`}>{pct}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-white/[0.08] overflow-hidden">
              <div
                className={`h-full bg-gradient-to-r ${barColor} transition-all duration-500 rounded-full relative overflow-hidden`}
                style={{ width: `${Math.max(5, pct)}%` }}
              >
                {!isDone && <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full animate-shimmer" />}
              </div>
            </div>
            <p className="text-[11px] text-slate-400 truncate mt-0.5">{label}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            const proj = liveStatus?.project_name || renderTask?.payload?.project_name || renderTask?.target_id;
            if (isDone && onNavigateToEditor) {
              onNavigateToEditor(proj);
            } else if (onNavigateToEditor) {
              onNavigateToEditor();
            }
          }}
          className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1 cursor-pointer transition-all shadow-md flex-shrink-0 active:scale-95 ${
            isDone
              ? 'bg-gradient-to-r from-[#25F4EE] to-blue-500 text-slate-950 hover:brightness-110 shadow-[#25F4EE]/20'
              : 'bg-[#D97757] hover:bg-[#C2683D] text-white'
          }`}
        >
          <span>{isDone ? 'เปิดไทม์ไลน์' : 'ดูหน้าตัดต่อ'}</span>
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
