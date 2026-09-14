import React from 'react';
import {
  Scissors, Loader2, Check, Sparkles, Save, PanelLeftOpen, PanelLeftClose,
  PanelRightOpen, PanelRightClose, Minimize2, Maximize2, Columns3, RefreshCw, Trash2,
  Image as ImageIcon, AlertTriangle, BookOpen, Lightbulb, X, Tag,
} from 'lucide-react';

import { formatTimecode } from '../../lib/timelineMath.js';
import HeaderMenu from './HeaderMenu.jsx';
import RenderButton from './RenderButton.jsx';
import ProjectSelector from './ProjectSelector.jsx';
import { ActivityIndicatorButton } from '../ActivityCenter.jsx';
import { getProjectOrigin } from '../../api.js';
import { loadPlaybookNotes } from '../../lib/producerInsights.js';

export default function EditorHeader({
  projectName,
  setProjectName,
  projectList = [],
  loadProject,
  loading = false,
  playhead = 0,
  totalDuration = 0,
  audioDuration = 0,
  saveStatus = 'saved',
  handleManualSave,
  leftSidebarCollapsed = false,
  toggleLeftSidebar,
  rightSidebarCollapsed = false,
  toggleRightSidebar,
  zen = false,
  setZen,
  resetPanelSizes,
  setSelection,
  applying = false,
  handleApply,
  exportPreset = 'post',
  setExportPreset,
  exportPresets = [],
  progress = 0,
  isPosted = false,
  setDeleteError,
  setDeleteScope,
  setDeleteOrigin,
  setPendingDelete,
  coverStatus = null,
  coverChecking = false,
  onOpenCoverStudio,
  showWatermark = true,
  onToggleWatermark,
}) {
  const [showPlaybookModal, setShowPlaybookModal] = React.useState(false);
  const playbookNotes = React.useMemo(() => loadPlaybookNotes(), [showPlaybookModal]);
  const renderNeedsCover = coverStatus !== true;

  const handleDeleteRequest = (name = projectName) => {
    if (!name) return;
    setDeleteError?.(null);
    setDeleteScope?.('project');
    setDeleteOrigin?.(null);
    setPendingDelete?.(name);
    getProjectOrigin(name)
      .then((orig) => setDeleteOrigin?.(orig))
      .catch(() => setDeleteOrigin?.({}));
  };

  return (
    <div className="flex flex-shrink-0 items-center justify-between gap-2 border-b border-white/[0.08] bg-[#0F1420] px-2.5 sm:px-4 py-2">
      {/* ── Left: Project selector, timecode, save status ── */}
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <Scissors className="hidden h-4 w-4 flex-shrink-0 text-[#D97757] sm:block" />

        <ProjectSelector
          projectName={projectName}
          projectList={projectList}
          loadProject={loadProject}
          onRequestDelete={handleDeleteRequest}
        />

        {projectName && (
          <div className="flex items-center gap-2">
            <span className="flex-shrink-0 font-mono text-sm font-bold text-slate-400">
              <span className="text-[#E89274]">{formatTimecode(playhead)}</span>
              <span className="hidden sm:inline"> / {formatTimecode(Math.max(totalDuration, audioDuration))}</span>
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] font-mono text-slate-400 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
              {saveStatus === 'saving' ? (
                <span className="text-amber-400 flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span className="hidden md:inline">กำลังบันทึก...</span>
                </span>
              ) : saveStatus === 'error' ? (
                <span className="text-red-400 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-red-400" />
                  <span className="hidden md:inline">บันทึกไม่สำเร็จ — ลองอีกครั้ง</span>
                </span>
              ) : saveStatus === 'dirty' ? (
                <span className="flex items-center gap-1 text-slate-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  <span className="hidden md:inline">มีการแก้ไข...</span>
                </span>
              ) : (
                <span className="text-emerald-400 flex items-center gap-1">
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="hidden md:inline">บันทึกแล้ว</span>
                </span>
              )}
            </span>
          </div>
        )}
      </div>

      {/* ── Right: Sidebar Toggles, Action Buttons & Render ── */}
      <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
        {/* Quick Sidebar Toggles (Desktop) */}
        <div className="hidden lg:flex items-center gap-1 bg-black/40 border border-white/[0.08] p-0.5 rounded-xl">
          <button
            type="button"
            onClick={toggleLeftSidebar}
            disabled={!projectName || zen}
            title={zen ? 'ปิดโหมดเต็มจอก่อน (Esc)' : leftSidebarCollapsed ? 'เปิดแถบซ้าย (คลังสื่อ)' : 'ซ่อนแถบซ้าย'}
            className={`h-7 px-2 rounded-lg text-xs font-bold flex items-center gap-1 transition-all cursor-pointer disabled:opacity-40 ${
              leftSidebarCollapsed
                ? 'text-slate-400 hover:text-white'
                : 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30'
            }`}
          >
            {leftSidebarCollapsed ? <PanelLeftOpen className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
            <span className="text-[11px]">ซ้าย</span>
          </button>
          <button
            type="button"
            onClick={toggleRightSidebar}
            disabled={!projectName || zen}
            title={zen ? 'ปิดโหมดเต็มจอก่อน (Esc)' : rightSidebarCollapsed ? 'เปิดแถบขวา (คำบรรยาย)' : 'ซ่อนแถบขวา'}
            className={`h-7 px-2 rounded-lg text-xs font-bold flex items-center gap-1 transition-all cursor-pointer disabled:opacity-40 ${
              rightSidebarCollapsed
                ? 'text-slate-400 hover:text-white'
                : 'bg-[#D97757]/15 text-[#D97757] border border-[#D97757]/30'
            }`}
          >
            <span className="text-[11px]">ขวา</span>
            {rightSidebarCollapsed ? <PanelRightOpen className="h-3.5 w-3.5" /> : <PanelRightClose className="h-3.5 w-3.5" />}
          </button>
        </div>

        <button
          type="button"
          onClick={() => { setProjectName(''); setSelection?.(null); }}
          disabled={applying}
          title="กลับไปหน้าสร้างคลิปใหม่"
          className="flex h-9 items-center gap-1 rounded-xl border border-white/[0.08] bg-black/40 px-2 text-sm font-bold text-slate-200 hover:text-white disabled:opacity-50 cursor-pointer"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">คลิปใหม่</span>
        </button>

        <ActivityIndicatorButton className="hidden h-9 md:flex" />

        <HeaderMenu
          items={[
            {
              id: 'zen',
              label: zen ? 'ย่อพรีวิวกลับ' : 'ขยายพรีวิวเต็มพื้นที่',
              icon: zen ? Minimize2 : Maximize2,
              disabled: !projectName,
              onSelect: () => setZen((v) => !v),
            },
            {
              id: 'reset-panels',
              label: 'รีเซ็ตขนาดพาเนล',
              icon: Columns3,
              disabled: !projectName,
              onSelect: resetPanelSizes,
            },
            {
              id: 'reload',
              label: loading ? 'กำลังโหลด...' : 'โหลดโปรเจกต์ใหม่',
              icon: loading ? Loader2 : RefreshCw,
              disabled: !projectName || loading,
              onSelect: () => loadProject(projectName),
            },
            {
              id: 'delete',
              label: 'ลบโปรเจกต์นี้...',
              icon: Trash2,
              danger: true,
              disabled: !projectName || loading || applying,
              onSelect: handleDeleteRequest,
            },
          ]}
        />

        {projectName && (
          <button
            type="button"
            // handleManualSave() returns a promise (it wraps the autosave
            // hook's saveNow). Its rejection already flows into saveStatus
            // ('dirty' then, after retries are exhausted, 'error') via the
            // save queue's onError callback, so this catch only exists to
            // stop it from surfacing as an unhandled promise rejection.
            onClick={() => { handleManualSave?.()?.catch(() => {}); }}
            disabled={saveStatus === 'saving' || applying}
            title="บันทึกการแก้ไขลงโปรเจกต์ (Ctrl+S)"
            className="flex h-9 items-center gap-1.5 rounded-xl border border-white/[0.12] bg-white/[0.06] hover:bg-white/[0.12] px-2.5 text-xs font-bold text-slate-200 hover:text-white transition-colors cursor-pointer disabled:opacity-50"
          >
            {saveStatus === 'saving' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
            ) : saveStatus === 'error' ? (
              <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
            ) : (
              <Save className="w-3.5 h-3.5 text-emerald-400" />
            )}
            <span className="hidden sm:inline">บันทึก</span>
          </button>
        )}

        {projectName && (
          <button
            type="button"
            onClick={onOpenCoverStudio}
            disabled={coverChecking || applying}
            title={
              coverChecking
                ? 'กำลังตรวจสอบภาพปก...'
                : coverStatus === true
                  ? 'มีภาพปกแล้ว — คลิกเพื่อแก้ไข'
                  : coverStatus === false
                    ? 'ยังไม่มีภาพปก — คลิกเพื่อสร้าง (ต้องมีก่อนเรนเดอร์)'
                    : 'เปิดตัวช่วยสร้างภาพปก'
            }
            className={`flex h-9 items-center gap-1.5 rounded-xl border px-2.5 text-xs font-bold transition-colors cursor-pointer disabled:opacity-50 ${
              coverStatus === false
                ? 'border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20'
                : 'border-white/[0.12] bg-white/[0.06] text-slate-200 hover:bg-white/[0.12] hover:text-white'
            }`}
          >
            {coverChecking ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400" />
            ) : coverStatus === true ? (
              <ImageIcon className="w-3.5 h-3.5 text-emerald-400" />
            ) : coverStatus === false ? (
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            ) : (
              <ImageIcon className="w-3.5 h-3.5 text-slate-400" />
            )}
            <span className="hidden sm:inline">ปก</span>
          </button>
        )}

        {projectName && (
          <button
            type="button"
            onClick={() => setShowPlaybookModal(true)}
            title="ข้อเตือนใจเจ้านาย (Boss Playbook Tips)"
            className="flex h-9 items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 px-2.5 text-xs font-bold text-amber-300 hover:text-amber-200 transition-colors cursor-pointer"
          >
            <BookOpen className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">ข้อเตือนใจ</span>
            {playbookNotes.length > 0 && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            )}
          </button>
        )}

        {projectName && (
          <label className="hidden sm:flex items-center gap-1.5 px-2.5 h-9 rounded-xl border border-white/[0.08] bg-white/[0.04] hover:bg-white/[0.08] text-xs text-slate-300 hover:text-white cursor-pointer transition-colors" title="เปิด/ปิดลายน้ำช่อง (@rizanntry) บนวิดีโอ">
            <input
              type="checkbox"
              checked={showWatermark !== false}
              onChange={(e) => onToggleWatermark?.(e.target.checked)}
              disabled={applying}
              className="h-3.5 w-3.5 rounded accent-[#D97757] cursor-pointer"
            />
            <span className="font-medium">ลายน้ำ</span>
          </label>
        )}

        <RenderButton
          presets={exportPresets}
          value={exportPreset}
          onChange={setExportPreset}
          onRender={handleApply}
          busy={applying}
          progress={progress}
          disabled={!projectName || isPosted || renderNeedsCover}
          needsCover={renderNeedsCover}
          isPosted={isPosted}
        />
      </div>

      {/* ── Playbook Tips Modal (Pre-flight Reminders) ── */}
      {showPlaybookModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
          onClick={() => setShowPlaybookModal(false)}
        >
          <div
            className="w-full max-w-lg rounded-2xl bg-[#0F1420] border border-white/[0.12] p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2.5">
                <span className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <Lightbulb className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-white">ข้อเตือนใจเจ้านายก่อนตัดต่อ</h3>
                  <p className="text-xs text-slate-400">กฎเหล็กและบทเรียนที่จดไว้ใน Boss's Playbook</p>
                </div>
              </div>
              <button
                onClick={() => setShowPlaybookModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                title="ปิด"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 text-xs">
              {playbookNotes.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  ยังไม่มีข้อเตือนใจที่บันทึกไว้ — สามารถจดเพิ่มได้จากหน้า ผู้ช่วยโปรดิวเซอร์ (Producer Hub)
                </div>
              ) : (
                playbookNotes.map((note, idx) => (
                  <div
                    key={note.id || idx}
                    className="p-3 rounded-xl bg-slate-800/50 border border-white/5 hover:border-amber-500/30 transition-all space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                        <Tag className="w-2.5 h-2.5" />
                        {note.tag || 'Rule'}
                      </span>
                      {note.createdAt && (
                        <span className="text-[10px] text-slate-500">
                          {new Date(note.createdAt).toLocaleDateString('th-TH')}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-200 text-xs leading-relaxed font-medium">
                      {note.text}
                    </p>
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
              <span>จดเพิ่มหรือแก้ไขได้ที่แท็บ <strong>โปรดิวเซอร์</strong></span>
              <button
                onClick={() => setShowPlaybookModal(false)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white font-semibold cursor-pointer transition-colors"
              >
                เข้าใจแล้ว
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
