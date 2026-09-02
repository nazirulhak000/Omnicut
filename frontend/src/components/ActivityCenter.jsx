import React, { useState } from 'react';
import {
  Zap, CheckCircle2, AlertCircle, Clock, X, Trash2, ArrowRight,
  Loader2, Sparkles, Film, Rocket, Mic, RefreshCw, Layers
} from 'lucide-react';
import { useTaskManager } from '../context/TaskContext';

function getTaskIcon(type) {
  switch (type) {
    case 'scrape_and_plan':
      return <Rocket className="w-4 h-4 text-[#25F4EE]" />;
    case 'render_video':
      return <Film className="w-4 h-4 text-[#FE2C55]" />;
    case 'voice_gen':
      return <Mic className="w-4 h-4 text-amber-400" />;
    default:
      return <Zap className="w-4 h-4 text-[#25F4EE]" />;
  }
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
  const { activeCount, activeTasks, toggleActivityDrawer, tasks } = useTaskManager();

  if (activeCount > 0) {
    const primaryTask = activeTasks[0];
    const pct = Math.round((primaryTask?.progress || 0) * 100);

    return (
      <button
        onClick={toggleActivityDrawer}
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
        </div>
      </button>
    );
  }

  return (
    <button
      onClick={toggleActivityDrawer}
      className={`p-1.5 sm:px-2.5 sm:py-1 rounded-xl bg-black/40 hover:bg-white/[0.08] active:bg-white/[0.12] border border-white/[0.08] text-slate-300 hover:text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors ${className}`}
      title="ศูนย์ติดตามกิจกรรม (Activity Center)"
    >
      <Layers className="w-3.5 h-3.5 text-[#25F4EE]" />
      <span className="hidden sm:inline">กิจกรรม</span>
      {tasks.length > 0 && (
        <span className="px-1.5 py-0.2 rounded-full bg-white/[0.08] text-[10px] font-mono text-slate-400">
          {tasks.length}
        </span>
      )}
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
    jumpToTaskResult
  } = useTaskManager();

  const [tabFilter, setTabFilter] = useState('all'); // all | active | completed

  if (!isActivityDrawerOpen) return null;

  const filteredTasks = tasks.filter(t => {
    if (tabFilter === 'active') return t.status === 'processing' || t.status === 'queued';
    if (tabFilter === 'completed') return t.status === 'completed';
    return true;
  });

  return (
    <div className="fixed inset-0 z-[100] w-screen h-[100dvh] max-h-[100dvh] overflow-hidden flex justify-end animate-fadeIn overscroll-none">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-md transition-opacity"
        onClick={() => setIsActivityDrawerOpen(false)}
      />

      {/* Slide-over Panel */}
      <aside className="relative w-full max-w-md bg-[#080B11]/95 backdrop-blur-2xl border-l border-white/[0.12] shadow-2xl flex flex-col h-[100dvh] max-h-[100dvh] z-10 animate-slideLeft overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 flex items-center justify-center text-[#25F4EE]">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white font-kanit flex items-center gap-2">
                <span>ศูนย์ติดตามกิจกรรม</span>
                {activeCount > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-[#25F4EE]/20 text-[#25F4EE] text-[10px] font-mono font-bold animate-pulse">
                    {activeCount} กำลังทำ
                  </span>
                )}
              </h2>
              <p className="text-[11px] text-slate-400">งานเบื้องหลังทั้งหมดไม่สูญหายแม้กดรีเฟรช</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {tasks.some(t => t.status === 'completed' || t.status === 'failed') && (
              <button
                onClick={clearCompleted}
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] rounded-lg text-xs transition-colors cursor-pointer"
                title="ล้างงานที่เสร็จสิ้นแล้ว"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => setIsActivityDrawerOpen(false)}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="px-4 py-2 border-b border-white/[0.06] flex items-center gap-1.5 bg-black/20">
          {[
            { id: 'all', label: `ทั้งหมด (${tasks.length})` },
            { id: 'active', label: `กำลังทำ (${activeCount})` },
            { id: 'completed', label: `เสร็จสิ้น (${tasks.filter(t => t.status === 'completed').length})` }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setTabFilter(tab.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                tabFilter === tab.id
                  ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Task List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {filteredTasks.length === 0 ? (
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
                        {getTaskIcon(task.type)}
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

                    <div className="h-1.5 w-full bg-black/60 rounded-full overflow-hidden border border-white/[0.06]">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          isRunning
                            ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] animate-pulse'
                            : isDone
                            ? 'bg-emerald-400'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
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
                          onClick={() => cancelTask(task.id)}
                          className="px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 text-[11px] font-bold transition-colors cursor-pointer"
                        >
                          ยกเลิก
                        </button>
                      )}

                      {isDone && (
                        <button
                          onClick={() => jumpToTaskResult(task)}
                          className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
                        >
                          <span>ดูผลลัพธ์</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      )}

                      {!isRunning && (
                        <button
                          onClick={() => deleteTask(task.id)}
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
    <div className="fixed bottom-5 right-5 z-50 max-w-sm w-full animate-slideUp">
      <div className={`p-4 rounded-2xl backdrop-blur-2xl border shadow-2xl space-y-3 ${
        isSuccess
          ? 'bg-[#080B11]/95 border-[#25F4EE]/40 shadow-[#25F4EE]/15 ring-1 ring-[#25F4EE]/30'
          : 'bg-[#080B11]/95 border-rose-500/40 shadow-rose-500/15'
      }`}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
              isSuccess ? 'bg-[#25F4EE]/20 text-[#25F4EE]' : 'bg-rose-500/20 text-rose-400'
            }`}>
              {isSuccess ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            </div>
            <h4 className="text-xs font-bold text-white font-kanit">
              {notificationToast.title}
            </h4>
          </div>
          <button
            onClick={() => setNotificationToast(null)}
            className="text-slate-400 hover:text-white p-1 rounded-md cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-snug">
          {notificationToast.message}
        </p>

        {isSuccess && notificationToast.task && (
          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              onClick={() => jumpToTaskResult(notificationToast.task)}
              className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer active:scale-95 transition-all"
            >
              <span>กดเพื่อเปิดดูผลงานทันที</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
