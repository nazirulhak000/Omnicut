import React from 'react';
import {
  Scissors, Loader2, Check, Sparkles, Save, PanelLeftOpen, PanelLeftClose,
  PanelRightOpen, PanelRightClose, Minimize2, Maximize2, Columns3, RefreshCw, Trash2,
} from 'lucide-react';

import { formatTimecode } from '../../lib/timelineMath.js';
import HeaderMenu from './HeaderMenu.jsx';
import RenderButton from './RenderButton.jsx';
import ProjectSelector from './ProjectSelector.jsx';
import { ActivityIndicatorButton } from '../ActivityCenter.jsx';
import { getProjectOrigin } from '../../api.js';

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
}) {
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
            onClick={handleManualSave}
            disabled={saveStatus === 'saving' || applying}
            title="บันทึกการแก้ไขลงโปรเจกต์ (Ctrl+S)"
            className="flex h-9 items-center gap-1.5 rounded-xl border border-white/[0.12] bg-white/[0.06] hover:bg-white/[0.12] px-2.5 text-xs font-bold text-slate-200 hover:text-white transition-colors cursor-pointer disabled:opacity-50"
          >
            {saveStatus === 'saving' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
            ) : (
              <Save className="w-3.5 h-3.5 text-emerald-400" />
            )}
            <span className="hidden sm:inline">บันทึก</span>
          </button>
        )}

        <RenderButton
          presets={exportPresets}
          value={exportPreset}
          onChange={setExportPreset}
          onRender={handleApply}
          busy={applying}
          progress={progress}
          disabled={!projectName || isPosted}
          isPosted={isPosted}
        />
      </div>
    </div>
  );
}
