import React from 'react';
import { ModalLayer } from '../ui/ModalLayer';
import {
  Sparkles,
  Minimize2,
  Maximize2,
  Columns3,
  RefreshCw,
  Trash2,
  Lightbulb,
  X,
  Tag,
  Keyboard,
  BookOpen,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

import HeaderMenu from './HeaderMenu.jsx';
import RenderButton from './RenderButton.jsx';
import ProjectSelector from './ProjectSelector.jsx';
import EditorChannelSelector from './EditorChannelSelector.jsx';
import SaveStatusChip from './SaveStatusChip.jsx';
import ViewToggleGroup from './ViewToggleGroup.jsx';
import RenderReadinessChip from './RenderReadinessChip.jsx';
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
  isFocusMode,
  toggleFocusMode,
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
  onOpenShortcuts,
  isAgentOpen = false,
  onToggleAgent,
  preflightReport = null,
  preflightLoading = false,
  onOpenPreflightModal = null,
  isImmersive = false,
  onToggleImmersive = null,
}) {
  const [showPlaybookModal, setShowPlaybookModal] = React.useState(false);
  const playbookNotes = React.useMemo(() => loadPlaybookNotes(), [showPlaybookModal]);
  const renderNeedsCover = coverStatus !== true;

  const handleDeleteRequest = React.useCallback(
    (name = projectName) => {
      if (!name) return;
      setDeleteError?.(null);
      setDeleteScope?.('project');
      setDeleteOrigin?.(null);
      setPendingDelete?.(name);
      getProjectOrigin(name)
        .then((orig) => setDeleteOrigin?.(orig))
        .catch(() => setDeleteOrigin?.({}));
    },
    [projectName, setDeleteError, setDeleteScope, setDeleteOrigin, setPendingDelete]
  );

  const headerMenuItems = React.useMemo(() => {
    const list = [
      { id: 'sec-view', type: 'section', label: 'มุมมอง' },
      {
        id: 'immersive',
        label: isImmersive ? 'ออกจากโหมดตัดต่อเต็มจอ (Esc)' : 'โหมดตัดต่อเต็มจอ (ซ่อนแถบนำทาง) (Shift+F)',
        icon: isImmersive ? Minimize2 : Maximize2,
        onSelect: () => onToggleImmersive?.(),
      },
      {
        id: 'zen',
        label: zen ? 'ย่อพรีวิวกลับ' : 'ขยายพรีวิวเต็มพื้นที่',
        icon: zen ? Minimize2 : Maximize2,
        disabled: !projectName,
        onSelect: () => setZen?.((v) => !v),
      },
      {
        // The view toggles in the header centre only show from xl (1280px);
        // between lg and xl this is the way into focus mode.
        id: 'focus-mode',
        label: isFocusMode ? 'ออกจากโหมดโฟกัส (เปิดพาเนลข้าง)' : 'เข้าโหมดโฟกัส (ซ่อนพาเนลข้างทั้งหมด)',
        icon: isFocusMode ? PanelLeftOpen : PanelLeftClose,
        disabled: !projectName || zen || !toggleFocusMode,
        onSelect: () => toggleFocusMode?.(),
        wrapClassName: 'hidden lg:block xl:hidden',
      },
      {
        id: 'reset-panels',
        label: 'รีเซ็ตขนาดพาเนล',
        icon: Columns3,
        disabled: !projectName,
        onSelect: resetPanelSizes,
      },
    ];

    if (projectName && onToggleWatermark) {
      list.push(
        { id: 'div-settings', type: 'divider' },
        { id: 'sec-settings', type: 'section', label: 'ค่าตั้งโปรเจกต์' },
        {
          id: 'watermark',
          type: 'toggle',
          label: 'ลายน้ำช่อง (@rizanntry)',
          checked: showWatermark !== false,
          disabled: applying,
          onChange: (checked) => onToggleWatermark?.(checked),
        }
      );
    }

    list.push(
      { id: 'div-help', type: 'divider' },
      { id: 'sec-help', type: 'section', label: 'ตัวช่วย' }
    );

    if (projectName) {
      list.push({
        id: 'playbook',
        label: 'ข้อเตือนใจเจ้านาย',
        icon: BookOpen,
        badge: playbookNotes.length > 0 ? playbookNotes.length : null,
        onSelect: () => setShowPlaybookModal(true),
      });
    }

    list.push({
      id: 'shortcuts',
      label: 'ดูคีย์ลัด',
      icon: Keyboard,
      disabled: !onOpenShortcuts,
      onSelect: onOpenShortcuts,
    });

    list.push(
      { id: 'div-proj', type: 'divider' },
      { id: 'sec-proj', type: 'section', label: 'โปรเจกต์' },
      {
        id: 'reload',
        label: loading ? 'กำลังโหลด...' : 'โหลดโปรเจกต์ใหม่',
        icon: RefreshCw,
        disabled: !projectName || loading,
        onSelect: () => loadProject?.(projectName),
      },
      {
        id: 'delete',
        label: 'ลบโปรเจกต์นี้...',
        icon: Trash2,
        danger: true,
        disabled: !projectName || loading || applying,
        onSelect: () => handleDeleteRequest(projectName),
      }
    );

    return list;
  }, [
    isImmersive,
    onToggleImmersive,
    isFocusMode,
    toggleFocusMode,
    zen,
    projectName,
    setZen,
    resetPanelSizes,
    showWatermark,
    applying,
    onToggleWatermark,
    playbookNotes.length,
    onOpenShortcuts,
    loading,
    loadProject,
    handleDeleteRequest,
  ]);

  return (
    <header className="flex flex-shrink-0 items-center justify-between gap-1 sm:gap-2 border-b border-white/[0.08] bg-[#0A0D14] px-2 sm:px-3 lg:px-4 py-1.5 select-none min-w-0">
      {/* ── Zone 1 (Left): Project Identity & Quick Save ── */}
      <div className="flex min-w-0 flex-1 items-center gap-1.5 sm:gap-2">
        <EditorChannelSelector />

        <div className="hidden sm:block h-4 w-px bg-white/10 flex-shrink-0" />

        <ProjectSelector
          projectName={projectName}
          projectList={projectList}
          loadProject={loadProject}
          onRequestDelete={handleDeleteRequest}
          onNewProject={() => {
            setProjectName?.('');
            setSelection?.(null);
          }}
        />

        {projectName && (
          <SaveStatusChip
            saveStatus={saveStatus}
            onSave={() => {
              handleManualSave?.()?.catch(() => {});
            }}
            disabled={applying}
          />
        )}
      </div>

      {/* ── Zone 2 (Center): Viewport Panel Controllers ── */}
      <div className="hidden xl:flex items-center justify-center flex-shrink-0">
        <ViewToggleGroup
          projectName={projectName}
          zen={zen}
          leftSidebarCollapsed={leftSidebarCollapsed}
          toggleLeftSidebar={toggleLeftSidebar}
          rightSidebarCollapsed={rightSidebarCollapsed}
          toggleRightSidebar={toggleRightSidebar}
          isFocusMode={isFocusMode}
          toggleFocusMode={toggleFocusMode}
        />
      </div>

      {/* ── Zone 3 (Right): AI Tools, Overflow Menu & Render Flow ── */}
      <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
        {/* Immersive Studio Toggle Button (Like CapCut Fullscreen/Collapse Bars) */}
        {onToggleImmersive && (
          <button
            type="button"
            onClick={() => onToggleImmersive?.()}
            data-testid="toggle-immersive-studio-btn"
            title={isImmersive ? "ออกจากโหมดตัดต่อเต็มจอ (Esc)" : "โหมดตัดต่อเต็มจอ (ซ่อนแถบนำทาง) (Shift+F)"}
            className={`flex h-8 sm:h-9 items-center gap-1.5 rounded-xl border px-2 sm:px-2.5 text-xs font-bold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/70 ${
              isImmersive
                ? 'border-[#25F4EE]/50 bg-[#25F4EE]/15 text-[#25F4EE] shadow-sm'
                : 'border-white/[0.08] bg-white/[0.04] text-slate-300 hover:border-white/[0.2] hover:text-white'
            }`}
          >
            {isImmersive ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
            <span className="hidden lg:inline">{isImmersive ? 'ย่อแถบ' : 'เต็มจอ'}</span>
            <span className="sr-only lg:hidden">{isImmersive ? 'ออกจากโหมดตัดต่อเต็มจอ' : 'โหมดตัดต่อเต็มจอ'}</span>
          </button>
        )}

        {/* In-App AI Agent Trigger */}
        <button
          type="button"
          onClick={onToggleAgent}
          data-testid="toggle-ai-agent-btn"
          title="สั่งงาน Antigravity AI Agent (Ctrl+K)"
          aria-label="สั่งงาน AI Agent"
          className={`flex h-8 sm:h-9 items-center gap-1.5 rounded-xl border px-1.5 sm:px-2.5 text-xs font-bold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 ${
            isAgentOpen
              ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/20'
              : 'border-white/[0.08] bg-white/[0.04] text-slate-300 hover:border-emerald-500/40 hover:text-white'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
          <span className="hidden sm:inline">AI Agent</span>
        </button>

        {/* Global Activity Center Button */}
        <ActivityIndicatorButton className="hidden sm:flex h-8 sm:h-9" />

        {/* Overflow Action Menu */}
        <HeaderMenu items={headerMenuItems} />

        {/* Unified Render Readiness Indicator (Cover + Audit + Playbook) */}
        {projectName && (
          <RenderReadinessChip
            coverStatus={coverStatus}
            coverChecking={coverChecking}
            preflightLoading={preflightLoading}
            onOpenCoverStudio={onOpenCoverStudio}
            preflightReport={preflightReport}
            onOpenPreflightModal={onOpenPreflightModal}
            playbookNotes={playbookNotes}
            onOpenPlaybookModal={() => setShowPlaybookModal(true)}
            disabled={applying}
          />
        )}

        {/* Primary Action: Render Button */}
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
        <ModalLayer onClose={() => setShowPlaybookModal(false)} aria-label="เช็กลิสต์ก่อนเรนเดอร์"
          className="fixed inset-0 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
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
        </ModalLayer>
      )}
    </header>
  );
}
