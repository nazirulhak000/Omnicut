import { useChannel } from '../../context/ChannelContext.jsx';
import { projectWatermark } from '../../lib/channelIdentity.js';
import { channelLocalStorage } from '../../lib/channelStorage.js';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, AlertTriangle, CheckCircle2, Loader2, Maximize2, Minimize2,
  RefreshCw, Rocket, Scissors, Film, Layers, Sliders, Sparkles, Trash2,
  FolderOpen, Play, Copy, Check, X, Save,
  ChevronLeft, ChevronRight, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, Columns3,
} from 'lucide-react';
import {
  deleteProject, getAllAssets, getBackgroundIsolationManifest, getHookMotionPresets, getProducts, getProject, getProjectOrigin, getProjects, getRenderStatus, getTaskStatus, preflightBackgroundIsolation, startBackgroundIsolation, interactiveSegment, startReroll, updateProjectCues, updateProjectClips, updateProjectState, openFolder, updateAngleStatus, updateAngleCover,
  getHookTemplates, saveCustomHookTemplate, deleteCustomHookTemplate, getBgmBeats, getMediaSilences,
} from '../../api';
import {
  EMPTY_BEAT_GRID, beatSnapPoints as beatSnapPointsOf, hasBeats, normalizeBeatGrid,
} from '../../lib/beatGrid.js';
import {
  EMPTY_RANGE_MARK, clipRangesFromSegments, describeRippleBlocked, describeRippleConfirm, hasRangeMark, isRippleDelete,
  markRangePoint, rangeMarkToRanges, resolveRippleScope, silenceSpansToProgramRanges, voiceCutSignature,
} from '../../lib/rippleUi.js';
import {
  FADE_DURATION, buildSegments, formatTimecode, resolveSplitTarget, snapSeekTime, splitClipAt, snapCandidates, snapTime,
  totalDuration as totalDurationOf,
} from '../../lib/timelineMath';
import { resolveTrimHead, resolveTrimTail } from '../../lib/timelineTrimOps.js';
import {
  DEFAULT_PX_PER_SEC, ZOOM_PRESETS, clampPxPerSec, fitPxPerSec, stepZoomPreset, zoomPresetIndex,
} from '../../lib/timelineZoom.js';
import { useEditorHistory } from '../../hooks/useEditorHistory';
import { useProjectAutosave } from '../../hooks/useProjectAutosave';
import { getProjectRevision, rememberProjectRevision } from '../../lib/projectRevision.js';
import { POST_RENDER_ACTIONS, decidePostRenderSync, fetchSettledProject } from '../../lib/postRenderRevision.js';
import { useProjectLoader } from '../../hooks/useProjectLoader';
import { useRenderJob } from '../../hooks/useRenderJob';
import useWakeLock from '../../hooks/useWakeLock';
import {
  usePanelLayout,
  ASSET_MIN_W,
  ASSET_MAX_W,
  ASSET_DEFAULT_W,
  INSPECTOR_MIN_W,
  INSPECTOR_MAX_W,
  INSPECTOR_DEFAULT_W,
  TIMELINE_MAX_H,
  MOBILE_PREVIEW_MIN_H,
  MOBILE_PREVIEW_DEFAULT,
} from '../../hooks/usePanelLayout';
import { useEditorSelection } from '../../hooks/useEditorSelection';
import { useEditorCommands } from '../../hooks/useEditorCommands';
import { useEditorShortcuts } from '../../hooks/useEditorShortcuts';
import { toMediaUrl } from '../../lib/mediaUrl';
import { editorStateToSavePayload, manifestToEditorState, serializeRenderClips, serializeRenderFeatures } from '../../lib/editorProjectState';
import { effectiveDuration as effectiveVoiceDuration } from '../../lib/voiceCutMap.js';
import { AUDIO_TRACKS, effectiveAudioMutes } from '../../lib/trackMix.js';
import { clampBusVolume, SFX_VOLUME_DEFAULT, VOICE_VOLUME_DEFAULT } from '../../lib/audioBusLevels.js';
import {
  normalizeStylePreset,
  stylePresetFromManifest,
  withStylePresetPayload,
} from '../../lib/stylePresetCatalog.js';
import { removeItemById, updateItemById } from '../../lib/collectionOperations.js';
import { cameraKeyframeSummary, clearCameraMotionPatch } from '../../lib/inspectorModel.js';
import { getOverlayRecolorMetadata } from '../../lib/overlayRecolor.js';
import {
  backgroundIsolationWindowContainsClip,
  clearBackgroundIsolationConflicts,
  completedBackgroundIsolationTasks,
  findBackgroundIsolationConflicts,
  groupBackgroundIsolationClips,
  groupScopedBackgroundIsolationClips,
  resolveBackgroundIsolationConfig,
  summarizeBackgroundIsolationPlan,
  scopedArtifactCoversClip,
  summarizeBackgroundIsolationStatus,
} from '../../lib/backgroundIsolationPreview.js';
import { resolveEditorProjectName } from '../../lib/editorEntry.js';
import {
  addSubjectPointToConfig,
  buildPrepareBaseConfig,
  clearSubjectPointsOnConfig,
} from '../../lib/cutoutSubjectPointState.js';
import { readPreviewQuality, writePreviewQuality } from '../../lib/previewQuality.js';
import SequencePlayer from '../SequencePlayer';
import AssetPanel from './AssetPanel';
import Inspector from './Inspector';
import Timeline, { tracksFitHeight } from './Timeline';
import TrimAdjustModal from './timeline/TrimAdjustModal';
import EditorHeader from './EditorHeader';
import { DEFAULT_HOOK_TEMPLATE, HOOK_TEMPLATES, registerCustomHookTemplates } from '../../lib/hookStyles';
import {
  guessBrandModel,
  newHookOverlay,
  newTextOverlay,
  overlayFromTextTemplate,
  overriddenTierFields,
  restyleOverlayFromTemplate,
  resolveLook,
  STYLE_PRESET_TO_TEMPLATE,
  templateForAdTone,
  templateForStylePreset,
  withHookTemplate,
  withHookTemplateReset,
  withTierLook,
  withTierText,
} from '../../lib/overlayModel';
import Toolbar from './Toolbar';
import NewClipPanel from './NewClipPanel';
import CoverStudioModal from '../CoverStudioModal';
import { ActivityIndicatorButton } from '../ActivityCenter';
import { useTaskManager } from '../../context/TaskContext';
import HeaderMenu from './HeaderMenu';
import RenderButton from './RenderButton';
import MixDegradedNotice from './MixDegradedNotice';
import ProjectRevisionNotice from './ProjectRevisionNotice';
import VoiceEditNotice from './VoiceEditNotice';
import RenderPreflightNotice from './RenderPreflightNotice';
import { analyzeRenderPreflight, preflightBlockingMessage } from '../../lib/renderPreflight.js';
import { planSfxEvents } from '../../lib/sfxPlan.js';

function formatErrorText(err) {
  if (!err) return '';
  if (typeof err === 'string') return err;
  const detail = err.response?.data?.detail ?? err.detail ?? err.message;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(d => (typeof d === 'object' ? (d.msg || JSON.stringify(d)) : String(d))).join(', ');
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return String(err.message || 'เกิดข้อผิดพลาดในการประมวลผล');
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForBackgroundIsolationTask(taskId, fetchStatus) {
  // The backend owns the durable job. Keep polling across temporary network
  // or server-reload gaps instead of converting a healthy task into a local
  // editor error. The deadline is intentionally long because rembg can take
  // several minutes for a full source sequence.
  const deadline = Date.now() + 30 * 60 * 1000;
  let networkFailures = 0;
  while (Date.now() < deadline) {
    try {
      const task = await fetchStatus(taskId);
      networkFailures = 0;
      if (['completed', 'failed', 'cancelled'].includes(task?.status)) return task;
      await wait(1000);
    } catch (error) {
      networkFailures += 1;
      await wait(Math.min(8000, 500 * (2 ** Math.min(networkFailures, 4))));
    }
  }
  throw new Error('background isolation task timed out while waiting for the backend');
}

const SNAP_PX = 6;
const EXPORT_PRESETS = [
  { id: 'post', label: 'โพสต์จริง 1080p', hint: 'คุณภาพเต็ม สำหรับอัปขึ้น TikTok' },
  { id: 'draft', label: 'ทดลอง 720p', hint: 'เร็วกว่าประมาณ 2 เท่า ไฟล์มี _draft ต่อท้าย ไม่ใช่ไฟล์สำหรับโพสต์' },
];

// The dock's own chrome: the drag handle plus the toolbar above the tracks.
const TIMELINE_CHROME_H = 8 + 44;
// Derived from the tracks themselves rather than hand-tuned. These were fixed
// numbers sized for a five-row timeline, so the four audio lanes pushed the
// video track past the bottom edge where nothing could reach it.
const TIMELINE_DEFAULT_H = TIMELINE_CHROME_H + tracksFitHeight();
// Folded audio still shows picture, hook, captions and one audio row.
const TIMELINE_MIN_H = TIMELINE_CHROME_H + tracksFitHeight({ audioCollapsed: true });

// Where the editor switches between its mobile and desktop layout trees.
// Tailwind `lg` (1024px): below it the desktop tree's own default panel
// widths (250 asset + 380 inspector + gutters = ~668px) leave under 100px
// for the preview, which is not a usable editor.
const LAYOUT_BREAKPOINT = 1024;
// The stems the preview mixes, in the order the timeline lanes show them.
// The Toolbar row inside the phone's timeline tab.
const MOBILE_TOOLBAR_H = 44;
// The timeline/assets/inspector tab strip above it.
const MOBILE_TAB_ROW_H = 48;

// Mirrors asset_registry.py's LEGACY_SFX_ALIASES: an old manifest's cue can
// still say "whoosh" where the registry id is "sfx_whoosh_fast".
const LEGACY_SFX_ALIASES = {
  whoosh: 'sfx_whoosh_fast',
  pop: 'sfx_pop_bubble',
  ding: 'sfx_bell_ding',
  cash: 'sfx_cash_register',
  boom: 'sfx_vine_boom',
};

// microCuesList and voiceEdit live in the history state too, so ONE Ctrl+Z takes a
// whole ripple delete back (rippleRange.js changes both together with the clips).
const EMPTY = { clipList: [], cuesList: [], microCuesList: [], voiceEdit: null, voiceEditStale: false, voiceEditNotice: null, overlays: [], stickers: [], effects: [], spotlight: null, backgroundIsolation: null, trackMix: { mute: {}, solo: {} }, style: { fontName: 'IBMPlex', bgmName: null, lutName: null, lutIntensity: 1, stickerBadge: null, bgmVolume: 0.12, bgmDucking: false, voiceVolume: VOICE_VOLUME_DEFAULT, sfxVolume: SFX_VOLUME_DEFAULT, captionPosition: 'bottom', captionColor: '#FFFFFF', captionScale: 1, stickerPosition: 'top_right', stickerScale: 1, style_preset: 'clean_tech_review', showWatermark: true } };

const DEFAULT_EDITOR_SPOTLIGHT = Object.freeze({
  schema_version: 1,
  enabled: false,
  shape: 'ellipse',
  focus: { x: 0.5, y: 0.5, width: 0.62, height: 0.42 },
  dim_opacity: 0.42,
  feather: 0.035,
  corner_radius: 0.08,
});

let idCounter = 0;
const newId = () => `clip-${Date.now().toString(36)}-${++idCounter}`;

export default function EditorShell({
  videos = [],
  productContext = null,
  angleIndex = 0,
  initialProjectName = null,
  onAngleChange,
  onGoToProductFlow,
  onVideoUploaded,
  onProductContextChange,
  workspaceData,
  onOpenShortcuts,
}) {
  const [workspaceStorage] = useState(channelLocalStorage);
  const channel = useChannel();
  const [channelIdentitySnapshot, setChannelIdentitySnapshot] = useState(null);
  const { state, set, setSilent, beginDrag, endDrag, undo, redo, reset, canUndo, canRedo } = useEditorHistory(EMPTY);
  const { clipList, cuesList, style, overlays, stickers = [], effects = [], spotlight = null, backgroundIsolation = null, trackMix = { mute: {}, solo: {} }, microCuesList = [], voiceEdit = null, voiceEditStale = false, voiceEditNotice = null } = state;

  const [projectList, setProjectList] = useState([]);
  const [projectName, setProjectName] = useState(() => {
    const urlProject = typeof window !== 'undefined'
      ? new URLSearchParams(window.location.search).get('project')
      : '';
    const storedProject = typeof window !== 'undefined'
      ? workspaceStorage.getItem('omnicut_active_project')
      : '';
    return resolveEditorProjectName({
      intent: initialProjectName,
      urlProject,
      storedProject,
      angleProject: productContext?.angles?.[angleIndex]?.project_name,
    });
  });
  // `default_bgm` comes from the server, which is where the render's own
  // default lives. Keeping a copy here is what let the timeline claim one
  // track while the file played another.
  const [assets, setAssets] = useState({ sfx: [], music: [], fonts: [], stickers: [], luts: [], effects: [], default_bgm: null });
  const { tasks = [], pollTasks, cancelTask } = useTaskManager();
  const readProducts = useCallback((options = {}) => workspaceData?.loadProducts
    ? workspaceData.loadProducts(options)
    : getProducts(), [workspaceData]);

  const [durations, setDurations] = useState({});
  // Length of the voice file as loaded. The voice on the timeline is that minus
  // the ripple cuts; the cuts live in the history state, so Ctrl+Z restores the
  // length with no extra bookkeeping. Without usable cuts nothing changes.
  const [loadedAudioDuration, setAudioDuration] = useState(0);
  // `activeVoiceEdit` is the edit the preview and the render actually apply:
  // null when there are no cuts or the server marked them stale (voice re-made).
  const activeVoiceEdit = useMemo(() => (
    voiceEdit && !voiceEditStale && Array.isArray(voiceEdit.cuts) && voiceEdit.cuts.length > 0
      ? voiceEdit
      : null
  ), [voiceEdit, voiceEditStale]);
  const audioDuration = useMemo(() => (
    activeVoiceEdit
      ? effectiveVoiceDuration(activeVoiceEdit.cuts, activeVoiceEdit.source?.duration)
      : loadedAudioDuration
  ), [activeVoiceEdit, loadedAudioDuration]);
  const [playhead, setPlayhead] = useState(0);
  // Timeline zoom is continuous px/s (Ctrl+wheel, fit); buttons and +/- hop
  // between ZOOM_PRESETS. zoomIndex only feeds the toolbar's "N/count".
  const [pxPerSec, setPxPerSec] = useState(DEFAULT_PX_PER_SEC);
  const zoomIndex = zoomPresetIndex(pxPerSec);
  const zoomStep = useCallback((dir) => setPxPerSec((px) => stepZoomPreset(px, dir)), []);
  const zoomTo = useCallback((px) => setPxPerSec(clampPxPerSec(px)), []);
  const [snapEnabled, setSnapEnabled] = useState(true);
  const [previewQuality, setPreviewQuality] = useState(() => readPreviewQuality());
  const [highResStillEnabled, setHighResStillEnabled] = useState(true);
  const handlePreviewQualityChange = useCallback((quality) => {
    setPreviewQuality(quality);
    writePreviewQuality(undefined, quality);
  }, []);
  // Beat grid for the current BGM. `null` means "not analyzed yet"; an empty
  // grid means "analyzed, no beats" -- the two must stay distinguishable or
  // the UI cannot tell "loading" from "this track has no beats".
  const [beatGrid, setBeatGrid] = useState(null);
  const [beatSnapEnabled, setBeatSnapEnabled] = useState(true);
  const [applyToAllCaptions, setApplyToAllCaptions] = useState(true);
  const [backgroundIsolationPreparing, setBackgroundIsolationPreparing] = useState(false);
  const [backgroundIsolationTaskIds, setBackgroundIsolationTaskIds] = useState([]);
  const [backgroundIsolationError, setBackgroundIsolationError] = useState('');
  const [cutoutBatchState, setCutoutBatchState] = useState({
    activeIndex: 0,
    totalCount: 0,
    activeClipIds: [],
    queuedClipIds: [],
  });
  const cutoutContextRef = useRef({ projectName, generation: 0 });
  if (cutoutContextRef.current.projectName !== projectName) {
    cutoutContextRef.current = { projectName, generation: cutoutContextRef.current.generation + 1 };
  }
  const isLocalPreparingRef = useRef(false);
  const [subjectContours, setSubjectContours] = useState([]);
  const [subjectContourLoading, setSubjectContourLoading] = useState(false);

  const backgroundIsolationGroups = useMemo(() => {
    const sourceClips = (clipList || []).filter((clip) => clip?.source_path);
    return backgroundIsolation?.scope_mode === 'behind_text_windows'
      ? groupScopedBackgroundIsolationClips(clipList || [], overlays, { sourceDurations: durations })
      : groupBackgroundIsolationClips(sourceClips, { sourceDurations: durations });
  }, [clipList, durations, overlays, backgroundIsolation?.scope_mode]);

  // Rehydrate running background isolation task if the page was reloaded during a cutout job
  useEffect(() => {
    if (backgroundIsolationPreparing) return;
    const runningCutoutTask = tasks.find(
      (task) => (task.type === 'background_isolation' || task.task_type === 'background_isolation')
        && ['pending', 'processing'].includes(task.status)
        && (!task.payload?.project_name || task.payload?.project_name === projectName)
    );
    if (!runningCutoutTask) return;
    setBackgroundIsolationPreparing(true);
    setBackgroundIsolationTaskIds((curr) => [...new Set([...curr, runningCutoutTask.id])]);

    if (backgroundIsolationGroups.length > 0) {
      const activeGroupIdx = backgroundIsolationGroups.findIndex((g) => {
        const pathMatch = g.sourcePath?.toLowerCase() === String(runningCutoutTask.payload?.source_path || '').toLowerCase();
        if (!pathMatch) return false;
        if (runningCutoutTask.payload?.start == null) return true;
        return Math.abs(g.start - Number(runningCutoutTask.payload.start)) < 0.2;
      });
      const safeIdx = Math.max(0, activeGroupIdx);
      const activeClipIds = (backgroundIsolationGroups[safeIdx]?.clips || []).map((c) => c.id);
      const queuedClipIds = backgroundIsolationGroups.slice(safeIdx + 1).flatMap((g) => (g.clips || []).map((c) => c.id));
      setCutoutBatchState({
        activeIndex: safeIdx,
        totalCount: backgroundIsolationGroups.length,
        activeClipIds,
        queuedClipIds,
      });
    }
  }, [tasks, projectName, backgroundIsolationPreparing, backgroundIsolationGroups]);

  // Clean up ONLY when a rehydrated background isolation finishes or fails (not during active local loop)
  useEffect(() => {
    if (!backgroundIsolationPreparing) return;
    if (isLocalPreparingRef.current) return;
    if (backgroundIsolationTaskIds.length > 0) {
      const activeTasks = backgroundIsolationTaskIds.map((id) => tasks.find((t) => t.id === id)).filter(Boolean);
      const stillRunning = activeTasks.some((t) => ['pending', 'processing'].includes(t.status));
      if (!stillRunning && activeTasks.length > 0) {
        setBackgroundIsolationPreparing(false);
        setCutoutBatchState({ activeIndex: 0, totalCount: 0, activeClipIds: [], queuedClipIds: [] });
      }
    }
  }, [backgroundIsolationPreparing, backgroundIsolationTaskIds, tasks]);
  const backgroundIsolationPlan = useMemo(() => {
    const relevantClips = backgroundIsolation?.scope_mode === 'behind_text_windows'
      ? backgroundIsolationGroups.flatMap((group) => group.clips)
      : clipList;
    const conflictClips = findBackgroundIsolationConflicts(relevantClips);
    return {
      ...summarizeBackgroundIsolationPlan(backgroundIsolationGroups, { fps: 30 }),
      conflictCount: conflictClips.length,
      conflictClips,
    };
  }, [backgroundIsolationGroups, clipList, backgroundIsolation?.scope_mode]);
  const backgroundIsolationProgress = useMemo(() => {
    const active = backgroundIsolationTaskIds
      .map((id) => tasks.find((task) => task.id === id))
      .filter(Boolean);
    if (!active.length && !backgroundIsolationPreparing) return null;
    const currentTask = active.at(-1);
    const currentTaskProgress = Number(currentTask?.progress) || 0;
    const totalCount = Math.max(1, cutoutBatchState.totalCount || backgroundIsolationGroups.length || 1);
    const activeIndex = Math.min(totalCount - 1, Math.max(0, cutoutBatchState.activeIndex || 0));

    // Smooth aggregate progress across all clips
    const progress = Math.min(0.99, Math.max(0.01, (activeIndex + currentTaskProgress) / totalCount));

    const step = currentTask?.step_label || 'กำลังตัดพื้นหลังสินค้า';
    const label = totalCount > 1
      ? `กำลังตัดช็อตที่ ${activeIndex + 1}/${totalCount}: ${step} (${Math.round(progress * 100)}%)`
      : `${step} (${Math.round(progress * 100)}%)`;

    return { progress, label };
  }, [backgroundIsolationTaskIds, tasks, backgroundIsolationPreparing, cutoutBatchState, backgroundIsolationGroups.length]);

  // Isolation artifacts belong to individual timeline clips. Keep this
  // summary aligned with the preview resolver so explicit project disable and
  // failed/stale artifacts cannot look ready in the editor chrome.
  const activeCutoutClips = useMemo(() => backgroundIsolation?.scope_mode === 'behind_text_windows'
    ? [...new Map(backgroundIsolationGroups.flatMap((group) => group.clips).map((clip) => [clip.id, clip])).values()]
    : clipList, [backgroundIsolation?.scope_mode, backgroundIsolationGroups, clipList]);
  const scopedCutoutClipIntervals = useMemo(() => Object.fromEntries(
    backgroundIsolationGroups.flatMap((group) => group.clips.map((clip) => [clip.id, group.active_intervals])),
  ), [backgroundIsolationGroups]);
  const cutoutArtifactIds = useMemo(() => [...new Set((activeCutoutClips || []).map((clip) => {
    const artifact = resolveBackgroundIsolationConfig(clip, backgroundIsolation)?.artifact;
    return artifact?.id || artifact?.sequence_id;
  }).filter(Boolean))], [backgroundIsolation, activeCutoutClips]);
  const [cutoutArtifactAvailability, setCutoutArtifactAvailability] = useState({});
  useEffect(() => {
    let cancelled = false;
    const verify = async () => {
      const results = await Promise.all(cutoutArtifactIds.map(async (id) => {
        try {
          const manifest = await getBackgroundIsolationManifest(id);
          return [id, manifest?.artifact_id === id && manifest?.status === 'ready'];
        } catch {
          return [id, false];
        }
      }));
      if (!cancelled) setCutoutArtifactAvailability(Object.fromEntries(results));
    };
    setCutoutArtifactAvailability({});
    verify();
    const timer = window.setInterval(verify, 15000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [cutoutArtifactIds.join('|')]);
  const backgroundIsolationStatus = useMemo(() => {
    if (backgroundIsolation?.scope_mode === 'behind_text_windows' && !backgroundIsolationGroups.length) {
      return { state: 'off', label: 'ไม่มีข้อความหลังสินค้าที่ต้องใช้ Cutout', readyCount: 0, totalCount: 0 };
    }
    const status = summarizeBackgroundIsolationStatus({
      clips: activeCutoutClips,
      projectConfig: backgroundIsolation,
      preparing: backgroundIsolationPreparing,
      artifactAvailability: cutoutArtifactAvailability,
    });
    if (backgroundIsolation?.scope_mode !== 'behind_text_windows') return status;
    if (status.state === 'off') return { ...status, state: 'missing', label: 'Cutout เฉพาะข้อความยังไม่พร้อม' };
    if (status.state !== 'ready') return status;
    const stale = backgroundIsolationGroups.some((group) => group.clips.some((clip) => {
      const config = resolveBackgroundIsolationConfig(clip, backgroundIsolation);
      return JSON.stringify(config?.active_intervals) !== JSON.stringify(group.active_intervals)
        || !scopedArtifactCoversClip(config, clip, { sourceDurations: durations });
    }));
    return stale ? { ...status, state: 'missing', label: 'ช่วง Cutout เปลี่ยนแล้ว กรุณาเตรียมใหม่' } : status;
  }, [backgroundIsolation, backgroundIsolationPreparing, activeCutoutClips, cutoutArtifactAvailability, backgroundIsolationGroups, durations]);

  // Mobile Mode Switcher: 'timeline' | 'assets' | 'inspector'
  const [cutoutPreviewMode, setCutoutPreviewMode] = useState('composite');
  const [mobileTab, setMobileTab] = useState('timeline');

  // Phones start with the audio group folded: four stem lanes are a desk-sized
  // amount of detail, and the gutter has no room for their names next to the
  // mute/solo chips. One tap opens them.
  const [audioCollapsed, setAudioCollapsed] = useState(
    () => (typeof window !== 'undefined' ? window.innerWidth < LAYOUT_BREAKPOINT : false)
  );

  const [zen, setZen] = useState(false);
  const [confirmGap, setConfirmGap] = useState(0);
  const pendingRenderBaseline = useRef(null);
  // Set further down once the loader exists: re-reads the project after a
  // render so the remembered save revision can catch up safely (L7-04).
  const syncAfterRenderRef = useRef(null);
  // 'conflict' (a save got 409) | 'render-dirty' (render rewrote the project
  // while edits were unsaved) | null. Nothing is replaced until the user asks.
  const [revisionNotice, setRevisionNotice] = useState(null);
  const [revisionReloading, setRevisionReloading] = useState(false);

  const handleRenderComplete = useCallback((rawResult, id, targetProject) => {
    const pending = pendingRenderBaseline.current;
    if (pending?.jobId === id && pending.projectName === targetProject) {
      loadedAudioStyle.current = pending.audioStyle;
      loadedAudioMutes.current = pending.audioMutes;
      loadedCaptionStyle.current = pending.captionStyle;
      cuesDirty.current = false;
      pendingRenderBaseline.current = null;
    }
    syncAfterRenderRef.current?.(targetProject, { allowReload: true });
    if (productContext?.id && productContext?.angles?.[angleIndex]?.angle_id) {
      try {
        const vPath = rawResult?.mp4 || rawResult?.final_video_path || rawResult?.video_path || '';
        updateAngleStatus(productContext.id, productContext.angles[angleIndex].angle_id, 'rendered', vPath, targetProject)
          .then(() => workspaceData?.invalidateTrackerData?.()).catch(() => {});
      } catch (e) {}
    }
  }, [productContext, angleIndex, workspaceData]);

  const handleRenderError = useCallback((_errorMsg, id, targetProject) => {
    if (pendingRenderBaseline.current?.jobId === id
      && pendingRenderBaseline.current?.projectName === targetProject) {
      pendingRenderBaseline.current = null;
    }
    // A failed render may still have written part of the manifest. Catch up
    // only when nothing the editor owns changed; otherwise ask the user.
    syncAfterRenderRef.current?.(targetProject, { allowReload: false });
    if (productContext?.id && productContext?.angles?.[angleIndex]?.angle_id) {
      try {
        updateAngleStatus(productContext.id, productContext.angles[angleIndex].angle_id, 'scripted')
          .then(() => workspaceData?.invalidateTrackerData?.()).catch(() => {});
      } catch (e) {}
    }
  }, [productContext, angleIndex, workspaceData]);

  const {
    jobId,
    jobStatus,
    isRendering: applying,
    applyResult,
    setApplyResult,
    applyError,
    setApplyError,
    progressPercent,
    startJob,
    stopJob,
  } = useRenderJob({
    projectName,
    fetchStatus: getRenderStatus,
    onComplete: handleRenderComplete,
    onError: handleRenderError,
  });

  useWakeLock(Boolean(applying));
  // Draft = 720p/crf26/veryfast. Measured on this machine: a 12s clip took
  // 25.5s at post quality vs 12.5s as a draft (12.18 MB vs 1.82 MB).
  const [exportPreset, setExportPreset] = useState('post');
  const [previewModalVideo, setPreviewModalVideo] = useState(null);
  const [copiedPath, setCopiedPath] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [voiceUrl, setVoiceUrl] = useState(null);
  // The raw project-relative path behind voiceUrl. Silence detection runs on
  // the file, so it needs the path the backend can open, not the media URL
  // the browser plays.
  const [voiceAudioPath, setVoiceAudioPath] = useState(null);
  // Ripple cut awaiting confirmation: { ranges, scope, source, reason, text }
  // (text = describeRipplePlan). Delete on a clip with a voiceover, Shift+Delete
  // on the I/O range and the silence button all end here: a ripple moves every
  // later clip, caption and voice cut, so it is shown before it is done.
  const [cutConfirm, setCutConfirm] = useState(null);
  const [silencePlan, setSilencePlan] = useState(null);
  const [silenceError, setSilenceError] = useState('');
  const [silenceScanning, setSilenceScanning] = useState(false);
  // Why a cut did not happen (nothing found, planner refused, scan failed).
  const [cutMessage, setCutMessage] = useState('');
  // What Delete does to the voice and captions: 'all' | 'video' | null (untouched
  // = the default for this project). Per session on purpose: a saved "video only"
  // would silently desync the next project's voice.
  const [rippleScopeChoice, setRippleScopeChoice] = useState(null);
  // I / O marks (program seconds) for a range cut. Not history state: they are a
  // pointer, not an edit, and any applied cut clears them.
  const [rangeMark, setRangeMark] = useState(EMPTY_RANGE_MARK);
  // The voice-edit notice the user already acknowledged ("project|kind|reason").
  const [dismissedVoiceNotice, setDismissedVoiceNotice] = useState('');
  // Read off the manifest so the banner can dress itself the way the script's
  // own narration tone asks for, and name the product without being told.
  const [projectAdTone, setProjectAdTone] = useState(null);
  const [projectProductName, setProjectProductName] = useState('');
  const [isProjectPosted, setIsProjectPosted] = useState(false);
  const [hookMotionCatalog, setHookMotionCatalog] = useState(null);
  const [hookMotionDefault, setHookMotionDefault] = useState(null);
  const [customHookTemplates, setCustomHookTemplates] = useState({});

  const handleSaveCustomHookTemplate = useCallback(async (payload) => {
    try {
      const res = await saveCustomHookTemplate(payload);
      if (res?.templates) {
        setCustomHookTemplates(res.templates);
        registerCustomHookTemplates(res.templates);
      }
      return res;
    } catch (err) {
      console.error('Save custom hook template error:', err);
      throw err;
    }
  }, []);

  const handleDeleteCustomHookTemplate = useCallback(async (templateId) => {
    try {
      const res = await deleteCustomHookTemplate(templateId);
      if (res?.templates) {
        setCustomHookTemplates(res.templates);
        registerCustomHookTemplates(res.templates);
      }
      return res;
    } catch (err) {
      console.error('Delete custom hook template error:', err);
      throw err;
    }
  }, []);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [deleteScope, setDeleteScope] = useState('project');
  const [deleteOrigin, setDeleteOrigin] = useState(null);
  const [trimAdjustSeg, setTrimAdjustSeg] = useState(null); // seg being edited in TrimAdjustModal, or null when closed
  // Opened from the header's "ปก" button (openCoverStudioManually).
  // null when closed; otherwise the videoItem shape CoverStudioModal expects.
  const [coverGateItem, setCoverGateItem] = useState(null);
  const [coverGateChecking, setCoverGateChecking] = useState(false);
  // Surfaced in the header as a status badge so the user can tell whether
  // this project's angle already has a cover without having to hit render
  // and get blocked to find out. null = not yet resolved (no matching
  // angle, or still checking); true/false once a fresh fetch resolves it.
  const [coverStatus, setCoverStatus] = useState(null);
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  // Per-stem mute/solo affects Preview and Export through one audibility rule.
  // Lives in the undo history alongside the other editable state so
  // Ctrl+Z/Ctrl+Y can take a mute/solo toggle back.
  const handleTrackMix = useCallback((track, kind) => {
    set((prev) => {
      const prevMix = prev.trackMix || { mute: {}, solo: {} };
      const next = { mute: { ...prevMix.mute }, solo: { ...prevMix.solo } };
      // 'all' is the folded group's own control: it flips every stem together,
      // so a row labelled for the group actually acts on the group.
      const targets = track === 'all' ? AUDIO_TRACKS : [track];
      const turningOn = !targets.every((k) => next[kind][k]);
      for (const k of targets) {
        next[kind][k] = turningOn;
        // Muting a track that is soloed would read as a contradiction on screen.
        if (kind === 'mute' && turningOn) next.solo[k] = false;
        if (kind === 'solo' && turningOn) next.mute[k] = false;
      }
      return { ...prev, trackMix: next };
    });
  }, [set]);
  const [isCaptionHidden, setIsCaptionHidden] = useState(false);
  const [isCutoutHidden, setIsCutoutHidden] = useState(false);
  const [subjectPickMode, setSubjectPickMode] = useState(false);
  const [subjectPickLabel, setSubjectPickLabel] = useState(1);

  // The banner and the text overlays are one array now, and it lives inside
  // the undo history. The banner used to sit outside it as seven loose
  // useStates, so retyping a brand was the one edit in this editor that
  // Ctrl+Z could not take back.
  const hookOverlay = useMemo(() => overlays.find((o) => o.kind === 'hook') || null, [overlays]);
  const textOverlays = useMemo(() => overlays.filter((o) => o.kind === 'text'), [overlays]);
  // The eye in the track gutter still speaks per track, so it reads and
  // writes `hidden` across every overlay of that kind.
  const isTextOverlayHidden = textOverlays.length > 0 && textOverlays.every((o) => o.hidden);
  const showHookHeader = !!hookOverlay && !hookOverlay.hidden;

  const markOverlaysDirty = useCallback(() => {
    cuesDirty.current = true;
    setSaveStatus('dirty');
  }, []);

  // `options` (L3-10): { silent: true } for a canvas drag between
  // beginDrag/endDrag (one undo step per drag), or { coalesceKey } so typing
  // shares one undo step. Omitted, every call is its own step as before.
  const handleUpdateOverlay = useCallback((id, patch, options) => {
    (options?.silent ? setSilent : set)((s) => ({
      ...s,
      overlays: s.overlays.map((o) => (o.id === id ? { ...o, ...patch } : o)),
    }), options);
    markOverlaysDirty();
  }, [set, setSilent, markOverlaysDirty]);

  /** Replace one overlay wholesale, for the withX helpers in overlayModel. */
  const handleReplaceOverlay = useCallback((id, next, options) => {
    (options?.silent ? setSilent : set)((s) => ({ ...s, overlays: s.overlays.map((o) => (o.id === id ? next : o)) }), options);
    markOverlaysDirty();
  }, [set, setSilent, markOverlaysDirty]);

  const handleAddOverlay = useCallback((overlay, select = true) => {
    set((s) => ({ ...s, overlays: [...s.overlays, overlay] }));
    if (select) setSelection({ type: overlay.kind === 'hook' ? 'hook' : 'text_overlay', id: overlay.id });
    markOverlaysDirty();
  }, [set, markOverlaysDirty]);

  const handleDeleteOverlay = useCallback((id) => {
    set((s) => ({ ...s, overlays: s.overlays.filter((o) => o.id !== id) }));
    setSelection((prev) => (prev?.id === id ? null : prev));
    markOverlaysDirty();
  }, [set, markOverlaysDirty]);

  const handleToggleOverlayKindHidden = useCallback((kind) => {
    set((s) => {
      const of = s.overlays.filter((o) => o.kind === kind);
      const hiding = !(of.length > 0 && of.every((o) => o.hidden));
      return { ...s, overlays: s.overlays.map((o) => (o.kind === kind ? { ...o, hidden: hiding } : o)) };
    });
    markOverlaysDirty();
  }, [set, markOverlaysDirty]);

  /**
   * A banner look picked from the left panel. It creates the banner if there
   * is not one yet, so the gallery is a way in rather than something that
   * silently does nothing until the right panel has been opened first.
   */
  const handleApplyHookTemplate = useCallback((template) => {
    if (!hookOverlay) {
      const guess = guessBrandModel(projectProductName || productContext?.title || '');
      const fresh = newHookOverlay({
        brand: guess.brand, model: guess.model, template, duration: 5.0,
      });
      if (fresh) handleAddOverlay(fresh);
      return;
    }
    handleReplaceOverlay(hookOverlay.id, withHookTemplate(hookOverlay, template));
    setSelection({ type: 'hook', id: hookOverlay.id });
  }, [hookOverlay, handleAddOverlay, handleReplaceOverlay, projectProductName, productContext]);

  const handleResetHookTemplate = useCallback(() => {
    if (!hookOverlay) return;
    handleReplaceOverlay(hookOverlay.id, withHookTemplateReset(hookOverlay));
  }, [hookOverlay, handleReplaceOverlay]);

  /** A template card dropped on the timeline, starting where it was let go. */
  const handleDropTextTemplate = useCallback((tpl, atSeconds) => {
    if (!tpl) return;
    const start = Math.round(atSeconds * 100) / 100;
    handleAddOverlay(overlayFromTextTemplate(tpl, {
      id: `ovl_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      start,
      end: start + 2.5,
    }));
  }, [handleAddOverlay]);

  const handleAddTextOverlay = useCallback(() => {
    const startSec = Math.round(playhead * 100) / 100;
    handleAddOverlay(newTextOverlay({
      id: `ovl_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      text: 'ข้อความใหม่',
      start: startSec,
      end: startSec + 2.5,
      look: { color: '#FFE600' },
    }));
  }, [playhead, handleAddOverlay]);

  /**
   * The banner, made on demand. It is an ordinary overlay, so "there isn't
   * one yet" is simply an empty array rather than a visibility flag that
   * could disagree with the three strings behind it.
   */
  const handleEnsureHookOverlay = useCallback(() => {
    if (hookOverlay) {
      handleUpdateOverlay(hookOverlay.id, { hidden: !hookOverlay.hidden });
      return;
    }
    // The tone the script was written in picks the look, the same mapping a
    // first render uses, so turning the banner on by hand lands on the same
    // dressing the pipeline would have chosen.
    const guess = guessBrandModel(projectProductName || productContext?.title || '');
    const fresh = newHookOverlay({
      brand: guess.brand,
      model: guess.model,
      template: templateForStylePreset(style?.style_preset) || templateForAdTone(projectAdTone),
      duration: 5.0,
    });
    if (fresh) handleAddOverlay(fresh);
  }, [hookOverlay, handleUpdateOverlay, handleAddOverlay, productContext,
      projectProductName, projectAdTone, style?.style_preset]);

  const [previewTextTemplate, setPreviewTextTemplate] = useState(null);
  const [previewSticker, setPreviewSticker] = useState(null);
  const [isStickerHidden, setIsStickerHidden] = useState(false);
  const handleToggleHideSticker = useCallback(() => setIsStickerHidden((v) => !v), []);
  const handlePreviewSticker = useCallback((badgeName) => {
    setPreviewSticker((prev) => (prev === badgeName ? null : badgeName));
  }, []);
  const handleDismissPreviewSticker = useCallback(() => setPreviewSticker(null), []);
  const [showSafeZone, setShowSafeZone] = useState(false);
  const handleToggleSafeZone = useCallback(() => setShowSafeZone((v) => !v), []);


  const mobilePlayerRef = useRef(null);
  const desktopPlayerRef = useRef(null);
  // Must be the SAME breakpoint the two layout trees are gated on (lg,
  // 1024px). The trees are chosen by CSS while the players are chosen by
  // this flag, so any disagreement leaves a viewport range where the visible
  // tree's player never mounts and the preview is simply blank.
  const [isMobileView, setIsMobileView] = useState(
    () => (typeof window !== 'undefined' ? window.innerWidth < LAYOUT_BREAKPOINT : false),
  );

  useEffect(() => {
    const handleResize = () => setIsMobileView(window.innerWidth < LAYOUT_BREAKPOINT);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Dismiss ephemeral text template preview whenever clicking anywhere that isn't the template card or its plus button
  useEffect(() => {
    if (!previewTextTemplate) return;
    const handleGlobalClick = (e) => {
      // If clicking inside a text template card or add button, let their specific handlers run
      if (e.target.closest('[data-text-template-card="true"]')) return;
      setPreviewTextTemplate(null);
    };
    window.addEventListener('pointerdown', handleGlobalClick, true);
    return () => window.removeEventListener('pointerdown', handleGlobalClick, true);
  }, [previewTextTemplate]);

  // Dismiss ephemeral sticker preview whenever clicking anywhere that isn't the sticker card
  useEffect(() => {
    if (!previewSticker) return;
    const handleGlobalClick = (e) => {
      if (e.target.closest('[data-sticker-card="true"]')) return;
      setPreviewSticker(null);
    };
    window.addEventListener('pointerdown', handleGlobalClick, true);
    return () => window.removeEventListener('pointerdown', handleGlobalClick, true);
  }, [previewSticker]);

  const cuesDirty = useRef(false);
  const initialCuesRef = useRef([]);
  const isLoadedRef = useRef(false);

  // Music lives in the mix, not the video pass. Apply has to ask for the
  // "bgm" re-roll when any of it changed, or the render happily reuses the
  // old mixed_audio.wav and the new track is silently ignored.
  const loadedAudioStyle = useRef({ bgmName: null, bgmVolume: 0.12, bgmDucking: false, voiceVolume: VOICE_VOLUME_DEFAULT, sfxVolume: SFX_VOLUME_DEFAULT });
  const loadedAudioMutes = useRef({});
  // Caption look is baked into the .ass, which the "video" part reuses -- so a
  // caption style change has to ask for the subtitles part instead.
  const loadedCaptionStyle = useRef({ captionPosition: 'bottom', captionColor: '#FFFFFF', captionScale: 1 });

  const activeStylePreset = normalizeStylePreset(style?.style_preset);
  const savePayload = useMemo(() => editorStateToSavePayload({
    clipList,
    cuesList,
    style,
    overlays,
    stickers,
    effects,
    spotlight,
    backgroundIsolation,
    trackMix,
    microCuesList,
    voiceEdit,
  }), [clipList, cuesList, overlays, stickers, effects, spotlight, backgroundIsolation, style, trackMix, microCuesList, voiceEdit]);
  const projectSavePayload = useMemo(
    () => withStylePresetPayload(savePayload, activeStylePreset),
    [savePayload, activeStylePreset],
  );
  const {
    saveStatus,
    setSaveStatus,
    flush: flushAutosave,
    saveNow: handleManualSave,
    setBaseline: setSaveBaseline,
    saveConflict,
    hasUnsavedWork,
  } = useProjectAutosave({
    projectName,
    payload: projectSavePayload,
    enabled: !!projectName && isLoadedRef.current && (channel?.writable ?? true),
    saveProject: updateProjectState,
    unsavedAtRisk: revisionNotice !== null,
  });

  const mapProject = useCallback((manifest) => manifestToEditorState(manifest, {
    createClipId: () => newId(),
    createCueId: (index) => `cue-${index}-${Date.now().toString(36)}`,
  }), []);

  const applyLoadedProject = useCallback((name, loaded, manifest) => {
    rememberProjectRevision(name, manifest?._editor_revision, channel?.channelId);
    setChannelIdentitySnapshot(manifest?.channel_identity_snapshot || null);
    const loadedStylePreset = stylePresetFromManifest(manifest, loaded.style);
    const loadedEditorState = {
      ...loaded,
      style: { ...loaded.style, style_preset: loadedStylePreset },
    };
    setProjectName(name);
    try {
      if (name) {
        workspaceStorage.setItem('omnicut_active_project', name);
        const url = new URL(window.location.href);
        if (url.searchParams.get('project') !== name) {
          url.searchParams.set('project', name);
          window.history.replaceState(null, '', url.toString());
        }
      }
    } catch {}
    setIsProjectPosted(Boolean(manifest?.is_posted || manifest?.angle_status === 'posted' || manifest?.posted_at));
    initialCuesRef.current = JSON.parse(JSON.stringify(loaded.cuesList || []));
    setProjectAdTone(loaded.adTone);
    setProjectProductName(loaded.productName);
    setAudioUrl(loaded.mixedAudioPath ? toMediaUrl(loaded.mixedAudioPath) : null);
    setVoiceUrl(loaded.voiceAudioPath ? toMediaUrl(loaded.voiceAudioPath) : null);
    setVoiceAudioPath(loaded.voiceAudioPath || null);
    loadedCaptionStyle.current = {
      captionPosition: loadedEditorState.style.captionPosition,
      captionColor: loadedEditorState.style.captionColor,
      captionScale: loadedEditorState.style.captionScale,
    };
    loadedAudioStyle.current = {
      bgmName: loadedEditorState.style.bgmName,
      bgmVolume: loadedEditorState.style.bgmVolume,
      bgmDucking: loadedEditorState.style.bgmDucking,
      voiceVolume: loadedEditorState.style.voiceVolume,
      sfxVolume: loadedEditorState.style.sfxVolume,
    };
    loadedAudioMutes.current = manifest?.audio_mutes || effectiveAudioMutes(loadedEditorState.trackMix);
    pendingRenderBaseline.current = null;
    reset({
      clipList: loadedEditorState.clipList,
      cuesList: loadedEditorState.cuesList,
      microCuesList: loadedEditorState.microCuesList || [],
      voiceEdit: loadedEditorState.voiceEdit || null,
      voiceEditStale: Boolean(loadedEditorState.voiceEditStale),
      voiceEditNotice: loadedEditorState.voiceEditNotice || null,
      overlays: loadedEditorState.overlays,
      stickers: loadedEditorState.stickers || [],
      effects: loadedEditorState.effects || [],
      spotlight: loadedEditorState.spotlight || null,
      backgroundIsolation: loadedEditorState.backgroundIsolation || null,
      trackMix: loadedEditorState.trackMix || { mute: {}, solo: {} },
      style: loadedEditorState.style,
    });
    setAudioDuration(loadedEditorState.audioDuration);
    cuesDirty.current = false;
    setSaveBaseline(
      name,
      withStylePresetPayload(editorStateToSavePayload(loadedEditorState), loadedStylePreset),
    );
    isLoadedRef.current = true;
  }, [reset, setSaveBaseline]);

  const {
    loadProject,
    loading,
    loadError,
    setLoadError,
  } = useProjectLoader({
    fetchProject: async (name) => {
      const manifest = await getProject(name);
      const isPosted = Boolean(manifest?.is_posted || manifest?.angle_status === 'posted' || manifest?.posted_at);
      if (isPosted) {
        throw new Error(`คลิป '${name}' โพสต์ลง TikTok แล้ว ระบบล็อกไม่ให้เปิดเข้าไทม์ไลน์ เพื่อป้องกันประวัติไฟล์เดิมเสียหาย`);
      }
      return manifest;
    },
    beforeLoad: async () => {
      if (projectName && isLoadedRef.current) await flushAutosave();
    },
    mapProject,
    onStart: () => {
      isLoadedRef.current = false;
      setIsProjectPosted(false);
      setSelection(null);
      setApplyError(null);
      setApplyResult(null);
      setConfirmGap(0);
    },
    onLoaded: applyLoadedProject,
  });

  // ── Revision catch-up after a render (L7-04) ──
  // The pipeline rewrites the manifest, so the server revision moves on while
  // this editor still holds the one it loaded. Catch up only when that cannot
  // hide anyone's work: see lib/postRenderRevision.js for the decision.
  const syncInputsRef = useRef({});
  syncInputsRef.current = { projectName, projectSavePayload, saveStatus, hasUnsavedWork };
  const manifestToSavePayload = useCallback((manifest) => {
    const loaded = mapProject(manifest);
    const preset = stylePresetFromManifest(manifest, loaded.style);
    return withStylePresetPayload(
      editorStateToSavePayload({ ...loaded, style: { ...loaded.style, style_preset: preset } }),
      preset,
    );
  }, [mapProject]);
  const isEditorClean = () => syncInputsRef.current.saveStatus === 'saved'
    && !syncInputsRef.current.hasUnsavedWork();
  const reloadProjectFromServer = useCallback(async (name) => {
    // Let an in-flight or queued save settle first. With a stale revision the
    // server refuses it (409), so it cannot overwrite the newer project.
    await flushAutosave().catch(() => {});
    const manifest = await getProject(name);
    if (syncInputsRef.current.projectName !== name) return false;
    setSelection(null);
    applyLoadedProject(name, mapProject(manifest), manifest);
    setRevisionNotice(null);
    return true;
    // `setSelection` comes from useEditorSelection further down. A deps entry is
    // read while rendering, before that declaration exists (temporal dead zone);
    // the call above runs later, so the closure reaches the initialised binding.
  }, [applyLoadedProject, flushAutosave, mapProject]);
  syncAfterRenderRef.current = async (targetProject, { allowReload }) => {
    const name = syncInputsRef.current.projectName;
    if (!name || name !== targetProject) return;
    const revisionAtStart = getProjectRevision(name);
    const manifest = await fetchSettledProject(() => getProject(name));
    // One tick for an edit made during the fetch to reach the autosave queue.
    await wait(50);
    const decide = () => decidePostRenderSync({
      fetchOk: !!manifest,
      manifest,
      projectName: syncInputsRef.current.projectName,
      targetProject,
      revisionAtStart,
      revisionNow: getProjectRevision(name),
      editorClean: isEditorClean(),
      currentPayload: syncInputsRef.current.projectSavePayload,
      toPayload: manifestToSavePayload,
      allowReload,
    });
    let decision = decide();
    // Re-check synchronously right before replacing editor state.
    if (decision.action === POST_RENDER_ACTIONS.RELOAD) {
      const again = decide();
      if (again.action !== POST_RENDER_ACTIONS.RELOAD) decision = again;
    }
    if (decision.action === POST_RENDER_ACTIONS.REMEMBER) {
      rememberProjectRevision(name, decision.revision);
    } else if (decision.action === POST_RENDER_ACTIONS.NOTIFY) {
      setRevisionNotice('render-dirty');
    } else if (decision.action === POST_RENDER_ACTIONS.RELOAD) {
      setSelection(null);
      applyLoadedProject(name, mapProject(manifest), manifest);
    }
  };
  useEffect(() => {
    if (saveConflict) setRevisionNotice('conflict');
  }, [saveConflict]);
  useEffect(() => {
    setRevisionNotice(null);
  }, [projectName]);
  const handleRevisionReload = useCallback(async () => {
    if (!projectName) return;
    setRevisionReloading(true);
    try {
      await reloadProjectFromServer(projectName);
    } catch (err) {
      setLoadError(formatErrorText(err));
    } finally {
      setRevisionReloading(false);
    }
  }, [projectName, reloadProjectFromServer, setLoadError]);

  // Latest layout for seekPlayer, which is declared before `segments` exists.
  const seekSegmentsRef = useRef([]);
  // Every seek lands on a whole 30 fps frame (stored value is still seconds).
  const seekPlayer = useCallback((t) => {
    const frameTime = snapSeekTime(t, seekSegmentsRef.current);
    setPlayhead(frameTime);
    if (isMobileView) {
      mobilePlayerRef.current?.seek(frameTime);
    } else {
      desktopPlayerRef.current?.seek(frameTime);
    }
  }, [isMobileView]);

  const togglePlayer = useCallback(() => {
    if (isMobileView) {
      mobilePlayerRef.current?.toggle();
    } else {
      desktopPlayerRef.current?.toggle();
    }
  }, [isMobileView]);

  /**
   * Deleting is permanent and there is no undo, so it goes through a dialog
   * that names the project and says what survives (the exported mp4).
   */
  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteProject(pendingDelete, deleteScope);
      const data = await getProjects().catch(() => null);
      setProjectList(data?.projects || []);

      // Refresh product context so any deleted project links are cleared immediately
      if (productContext?.id) {
        workspaceData?.invalidateTrackerData?.();
        readProducts({ force: true }).then((freshRes) => {
          const list = Array.isArray(freshRes) ? freshRes : (freshRes?.products || []);
          const updated = list.find((p) => p.id === productContext.id);
          if (updated && onProductContextChange) {
            onProductContextChange(updated);
          }
        }).catch(() => {});
      }

      if (projectName === pendingDelete) {
        setProjectName('');
        setSelection(null);
        try {
          workspaceStorage.removeItem('omnicut_active_project');
          const url = new URL(window.location.href);
          url.searchParams.delete('project');
          window.history.replaceState(null, '', url.toString());
        } catch {}
      }
      setPendingDelete(null);
    } catch (err) {
      setDeleteError(err.response?.data?.detail || err.friendlyMessage || 'ลบไม่สำเร็จ');
    } finally {
      setDeleting(false);
    }
  };

  /**
   * A render started from the create panel lands straight in the timeline.
   * loadProject only reads the name it is handed (everything else it touches
   * is a setter), so capturing the first instance here is safe.
   */
  const handleClipCreated = useCallback((newProjectName) => {
    const curAngle = productContext?.angles?.[angleIndex];
    if (productContext?.id && curAngle?.angle_id) {
      updateAngleStatus(productContext.id, curAngle.angle_id, 'in_production', null, newProjectName)
        .then(() => workspaceData?.invalidateTrackerData?.()).catch(() => {});
    }
    getProjects()
      .then((data) => setProjectList(data?.projects || []))
      .catch(() => {})
      .finally(() => loadProject(newProjectName));
  }, [productContext?.id, productContext?.angles, angleIndex, workspaceData]);

  // Load project list + assets on mount
  useEffect(() => {
    getProjects()
      .then((data) => setProjectList(data?.projects || []))
      .catch((err) => setLoadError(err.message || 'โหลดรายการโปรเจกต์ไม่สำเร็จ'));

    getAllAssets()
      .then(setAssets)
      .catch((err) => console.warn('Asset fetch failed:', err));

    // Motion pickers render from the backend's own catalog rather than a
    // duplicated list here, so a preset added server-side appears without a
    // frontend change (and one that isn't there can't be picked).
    getHookMotionPresets()
      .then((data) => {
        setHookMotionCatalog(data?.catalog || null);
        setHookMotionDefault(data?.default || null);
      })
      .catch((err) => console.warn('Hook motion preset fetch failed:', err));

    getHookTemplates()
      .then((data) => {
        if (data?.custom) {
          setCustomHookTemplates(data.custom);
          registerCustomHookTemplates(data.custom);
        }
      })
      .catch((err) => console.warn('Hook templates fetch failed:', err));
  }, []);

  // Load project handed down from script lab or flow, or restored from storage/URL
  useEffect(() => {
    const urlProject = typeof window !== 'undefined'
      ? new URLSearchParams(window.location.search).get('project')
      : '';
    const storedProject = typeof window !== 'undefined'
      ? workspaceStorage.getItem('omnicut_active_project')
      : '';
    const targetProject = resolveEditorProjectName({
      intent: initialProjectName,
      urlProject,
      storedProject,
      angleProject: productContext?.angles?.[angleIndex]?.project_name,
    });
    if (targetProject) loadProject(targetProject);
  }, [initialProjectName, productContext, angleIndex]);

  // Clip thumbnails are loaded per clip, lazily, by TimelineClip's
  // ClipFilmstrip (one sprite per source + trim window).
  const segments = useMemo(() => buildSegments(clipList, durations), [clipList, durations]);
  const totalDuration = useMemo(() => totalDurationOf(segments), [segments]);
  const renderPreflight = useMemo(() => analyzeRenderPreflight({
    clips: clipList, durations, segments, expectedDuration: audioDuration,
  }), [clipList, durations, segments, audioDuration]);
  useEffect(() => { seekSegmentsRef.current = segments; }, [segments]);

  const {
    selection,
    setSelection,
    handleSelect,
    selectedClipIds,
    selectClipWithMode,
    clearSelection: clearClipSelection,
    selectedSeg,
    selectedCaption,
    selectedOverlay,
  } = useEditorSelection({
    segments,
    cuesList,
    overlays,
    hookOverlay,
    playhead,
    seekPlayer,
  });

  const [toastMessage, setToastMessage] = useState(null);
  const toastTimeoutRef = useRef(null);

  const showToast = useCallback((msg) => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    setToastMessage(msg);
    toastTimeoutRef.current = setTimeout(() => {
      setToastMessage(null);
      toastTimeoutRef.current = null;
    }, 2500);
  }, []);

  const {
    addClip,
    patchClip,
    patchAllClips,
    reorderClip,
    splitAtPlayhead,
    trimHeadAtPlayhead,
    trimTailAtPlayhead,
    duplicateSelected,
    copyClipSettings,
    pasteClipSettings,
    hasCopiedClipSettings,
    deleteSelected,
    planRipple,
    rippleRanges,
    addTextAtPlayhead,
    patchCaption,
    patchAllCaptions,
    handleUpdateCuesList,
    handleSplitCue,
    handleSplitCueAtPlayhead,
    handleMergeCue,
    handleMergeWithPrevious,
    handleReorderCues,
    handleBatchFindAndReplace,
    handleBatchFormatClean,
    handleDeleteCue,
    handleInsertCueAfter,
    handleImportCues,
  } = useEditorCommands({
    set,
    setSilent,
    newId,
    durations,
    playhead,
    segments,
    selectedSeg,
    selection,
    setSelection,
    selectedClipIds,
    cuesDirtyRef: cuesDirty,
    handleDeleteOverlay,
    onImportSuccess: () => setMobileTab('timeline'),
    onNotify: (msg) => showToast(msg),
    onSeek: seekPlayer,
    // Ripple delete (rippleRange.js) plans against the history state and needs
    // the voice length; the commands exist but no control is bound to them yet.
    editorState: state,
    hasVoice: !!voiceAudioPath,
    audioDuration,
  });

  // Timeline content is `duration * pxPerSec + 240` wide (see Timeline.jsx),
  // so at the default 50 px/s it outruns a 1440px viewport from about the
  // twelfth 2-second clip and every session starts with manual scrolling.
  // Zoom is continuous, so "fit" uses the exact px/s that fills the track
  // (clamped to the zoom range) instead of the nearest lower step.
  const timelineViewportRef = useRef(null);
  const zoomToFit = useCallback(() => {
    // Falls back to the window when no visible timeline has claimed the ref
    // yet (see the visibility guard in Timeline.jsx), so the button still
    // does something sensible rather than nothing.
    const width = timelineViewportRef.current?.clientWidth || window.innerWidth;
    if (!width || !totalDuration) return;
    const usable = Math.max(120, width - 240 - 92); // ruler gutter + trailing pad
    const fitted = fitPxPerSec(usable, totalDuration);
    if (fitted) setPxPerSec(fitted);
  }, [totalDuration]);

  useEditorShortcuts({
    undo,
    redo,
    splitAtPlayhead,
    trimHeadAtPlayhead,
    trimTailAtPlayhead,
    segments,
    cues: cuesList,
    deleteSelected,
    togglePlayer,
    seekPlayer,
    playhead,
    totalDuration,
    audioDuration,
    onZoomStep: zoomStep,
    onZoomFit: zoomToFit,
    selectedSeg,
    patchClip,
    zen,
    setZen,
    multiSelectCount: selectedClipIds.length,
    clearSelection: clearClipSelection,
    copyClipSettings,
    pasteClipSettings,
    onKeyframeToggled: (result) => {
      const msg = {
        added: '◆ เพิ่มคีย์เฟรมที่หัวอ่านแล้ว',
        removed: '◇ ลบคีย์เฟรมที่หัวอ่านแล้ว',
        outside: 'เลื่อนหัวอ่านเข้ามาในคลิปที่เลือกก่อนวางคีย์เฟรม',
        noClip: 'เลือกคลิปวิดีโอก่อนวางคีย์เฟรม',
      }[result];
      if (msg) showToast(msg);
    },
    onToggleSnap: () => {
      setSnapEnabled((v) => {
        const next = !v;
        showToast(next ? 'แม่เหล็กดูด Timeline: เปิด' : 'แม่เหล็กดูด Timeline: ปิด');
        return next;
      });
    },
    onCycleCutoutMode: () => {
      setCutoutPreviewMode((curr) => {
        const order = ['composite', 'checkerboard', 'matte'];
        const nextIdx = (order.indexOf(curr) + 1) % order.length;
        const next = order[nextIdx];
        const titles = {
          composite: 'ปกติ (Composite)',
          checkerboard: 'ตารางหมากรุก (Checkerboard)',
          matte: 'มาสก์ขาวดำ (Alpha Matte)',
        };
        showToast(`✂️ โหมดตรวจเช็ก Cutout: ${titles[next]}`);
        return next;
      });
    },
  });


  // Split button state comes from the same resolver the Split command runs.
  const splitTarget = useMemo(
    () => resolveSplitTarget(segments, selectedSeg, playhead),
    [segments, selectedSeg, playhead],
  );
  const trimHeadTarget = useMemo(
    () => resolveTrimHead(segments, selectedSeg, playhead),
    [segments, selectedSeg, playhead],
  );
  const trimTailTarget = useMemo(
    () => resolveTrimTail(segments, selectedSeg, playhead),
    [segments, selectedSeg, playhead],
  );

  const hasTransformOverride = !!selectedSeg?.clip && (
    (selectedSeg.clip.zoom !== undefined && selectedSeg.clip.zoom !== 1) ||
    (selectedSeg.clip.pan_x !== undefined && selectedSeg.clip.pan_x !== 0) ||
    (selectedSeg.clip.pan_y !== undefined && selectedSeg.clip.pan_y !== 0) ||
    cameraKeyframeSummary(selectedSeg.clip).points > 0
  );

  // Scan the voiceover for dead air and propose an all-lane ripple cut.
  // Cuts across video, voiceover, subtitles, and overlays together (User Choice 2. ก).
  const handleScanSilences = useCallback(async () => {
    if (!voiceAudioPath) {
      setSilenceError('ยังไม่มีไฟล์เสียงพากย์ในโปรเจกต์นี้');
      return;
    }
    setSilenceScanning(true);
    setSilenceError('');
    setSilencePlan(null);
    try {
      const data = await getMediaSilences(voiceAudioPath);
      const rawSilences = data?.silences || [];
      const programRanges = silenceSpansToProgramRanges(
        rawSilences,
        activeVoiceEdit,
        loadedAudioDuration || audioDuration
      );
      if (!programRanges.length) {
        setSilenceError('ไม่พบช่วงเงียบที่ตัดได้');
        return;
      }
      const plan = planRipple(programRanges, 'all', { reason: 'silence' });
      if (plan.blocked) {
        setSilenceError(describeRippleBlocked(plan.blocked, { source: 'silence' }));
      } else if (!plan.changed) {
        setSilenceError('ไม่พบช่วงเงียบที่ตัดได้');
      } else {
        const confirm = describeRippleConfirm(plan, { source: 'silence', count: rawSilences.length });
        setSilencePlan({
          plan,
          description: confirm.summary || confirm.subtitle,
          confirmTitle: confirm.title,
          confirmSubtitle: confirm.subtitle,
          ranges: programRanges,
        });
      }
    } catch (err) {
      setSilenceError(err?.friendlyMessage || err?.message || 'ตรวจช่วงเงียบไม่สำเร็จ');
    } finally {
      setSilenceScanning(false);
    }
  }, [voiceAudioPath, activeVoiceEdit, loadedAudioDuration, audioDuration, planRipple]);

  // Apply the confirmed plan across all tracks in ONE state change, so a single Ctrl+Z
  // puts the timeline back exactly as it was.
  const handleApplySilencePlan = useCallback(() => {
    const ranges = silencePlan?.ranges || silencePlan?.plan?.ranges;
    if (!ranges || !ranges.length) return;
    const plan = rippleRanges(ranges, 'all', { reason: 'silence' });
    setSilencePlan(null);
    setSelection(null);
    if (plan && plan.changed && !plan.blocked) {
      showToast('✂️ ตัดช่วงเงียบสำเร็จ (ขยับภาพ เสียง และซับครบ)');
    }
  }, [silencePlan, rippleRanges, setSelection, showToast]);

  const handleCancelSilencePlan = useCallback(() => {
    setSilencePlan(null);
    setSilenceError('');
  }, []);

  const handleResetClipTransform = useCallback(() => {
    if (!selectedSeg?.clip) return;
    // Camera keyframes beat the static zoom/pan, so they go too -- otherwise
    // this reset would leave the clip moving.
    patchClip(selectedSeg.clip.id, {
      zoom: 1,
      pan_x: 0,
      pan_y: 0,
      ...(cameraKeyframeSummary(selectedSeg.clip).points > 0 ? clearCameraMotionPatch(selectedSeg.clip) : {}),
    });
  }, [selectedSeg?.clip, patchClip]);

  // Beat grid follows whichever BGM the project is using. Analysis is cached
  // server-side, so re-selecting a track is cheap. A failure is not surfaced
  // as an error: beats are an editing aid, and losing them must not block
  // the timeline -- the markers simply do not appear.
  useEffect(() => {
    const bgmName = style?.bgmName;
    if (!bgmName) { setBeatGrid(null); return; }
    let cancelled = false;
    setBeatGrid(null);
    getBgmBeats(bgmName)
      .then((data) => { if (!cancelled) setBeatGrid(normalizeBeatGrid(data)); })
      .catch(() => { if (!cancelled) setBeatGrid({ ...EMPTY_BEAT_GRID }); });
    return () => { cancelled = true; };
  }, [style?.bgmName]);

  // Only beats inside the sequence can be snap targets: a marker past the end
  // of the timeline is unreachable, and feeding it to snapCandidates would
  // let a drag jump to a point the user cannot see.
  const beatSnapPoints = useMemo(() => {
    if (!snapEnabled || !beatSnapEnabled) return [];
    return beatSnapPointsOf(beatGrid, Math.max(totalDuration || 0, audioDuration || 0));
  }, [snapEnabled, beatSnapEnabled, beatGrid, totalDuration, audioDuration]);

  // Snapping candidates for subtitles when magnetic snap is active
  const cueSnapPoints = useMemo(() => {
    if (!snapEnabled) return [];
    const pts = [];
    cuesList.forEach((c) => {
      if (typeof c.start === 'number') pts.push(c.start);
      if (typeof c.end === 'number') pts.push(c.end);
    });
    return pts;
  }, [snapEnabled, cuesList]);

  const handleAddTextTemplate = useCallback((tpl) => {
    const isHook = tpl?.category === 'hook';
    const startSec = isHook ? 0.0 : Math.round(playhead * 100) / 100;
    const defaultDur = isHook ? Math.min(3.5, totalDuration || 3.5) : 2.5;
    const endSec = Math.round((startSec + defaultDur) * 100) / 100;
    const overlay = overlayFromTextTemplate(tpl, {
      id: `ovl_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      start: startSec,
      end: endSec,
    });
    if (isHook) {
      // An opening hook belongs at the top of the frame, above the caption
      // band, which is where the card's own preview shows it.
      overlay.position = 'top';
      overlay.y = 0.35;
    }
    set((prev) => ({ ...prev, overlays: [...prev.overlays, overlay] }));
    setSelection({ type: 'text_overlay', id: overlay.id, focusText: true });
    setPreviewTextTemplate(null);
    cuesDirty.current = true;
    setSaveStatus('dirty');
  }, [playhead, totalDuration, set]);

  const handleSelectTextTemplate = useCallback((tpl) => {
    if (!tpl) return;
    // With an overlay selected, the card re-dresses it and keeps its words.
    if (selection?.type === 'text_overlay' && selection.id) {
      const current = overlays.find((o) => o.id === selection.id);
      if (current) handleReplaceOverlay(current.id, restyleOverlayFromTemplate(current, tpl));
      setPreviewTextTemplate(null);
      return;
    }
    // Otherwise the card previews itself on the canvas until dismissed. It is
    // drawn as a real overlay by the one drawing path, so what is shown is
    // exactly what committing it produces.
    setPreviewTextTemplate((prev) => {
      if (prev?.template_id === tpl.id) return null;
      const preview = overlayFromTextTemplate(tpl, {
        id: '__preview__',
        start: 0,
        end: Number.MAX_SAFE_INTEGER,
      });
      preview.position = 'middle';
      return preview;
    });
  }, [selection, overlays, handleReplaceOverlay]);

  const handleAddSticker = useCallback((badgeName, asset = null) => {
    const dur = 3.0; // DEFAULT 3 SECONDS
    const start = Math.round(playhead * 10) / 10;
    const maxEnd = totalDuration > 0 ? totalDuration : (start + dur);
    const end = Math.round(Math.min(maxEnd, start + dur) * 10) / 10;
    const recolorMeta = asset?.recolorable
      ? asset
      : getOverlayRecolorMetadata('sticker', badgeName);
    const newSticker = {
      id: `sticker-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
      badge: badgeName,
      start,
      end,
      normX: 0.5,
      normY: 0.35,
      scale: 1.0,
      hidden: false,
      ...(recolorMeta.recolorable ? {
        recolor: 'accent',
        recolorSourceHue: Number(recolorMeta.recolor_source_hue),
      } : {}),
    };
    set((prev) => ({
      ...prev,
      stickers: [...(prev.stickers || []), newSticker],
      style: {
        ...prev.style,
        stickerBadge: badgeName,
        stickerStartTime: start,
        stickerEndTime: end,
      },
    }));
    setSelection({ type: 'sticker', id: newSticker.id });
  }, [playhead, totalDuration, set]);

  // `options` as in handleUpdateOverlay: { silent: true } inside a canvas drag.
  const handleUpdateSticker = useCallback((idOrPatch, maybePatch, options) => {
    let id = null;
    let patch = {};
    if (typeof idOrPatch === 'string') {
      id = idOrPatch;
      patch = maybePatch || {};
    } else if (typeof idOrPatch === 'object' && idOrPatch !== null) {
      if (idOrPatch.id) {
        id = idOrPatch.id;
        patch = idOrPatch;
      } else {
        patch = idOrPatch;
      }
    }

    (options?.silent ? setSilent : set)((prev) => {
      const currentList = prev.stickers || [];
      const targetId = id || selection?.id;
      if (!targetId || !currentList.some((s) => s.id === targetId)) {
        return prev; // nothing to update — do not fabricate or misapply the patch
      }
      const nextList = updateItemById(currentList, targetId, patch);
      return {
        ...prev,
        stickers: nextList,
        style: {
          ...prev.style,
          ...(patch.scale != null ? { stickerScale: patch.scale } : {}),
          ...(patch.normX != null ? { stickerNormX: patch.normX } : {}),
          ...(patch.normY != null ? { stickerNormY: patch.normY } : {}),
          ...(patch.start != null ? { stickerStartTime: patch.start } : (patch.startTime != null ? { stickerStartTime: patch.startTime } : {})),
          ...(patch.end != null ? { stickerEndTime: patch.end } : (patch.endTime != null ? { stickerEndTime: patch.endTime } : {})),
          ...(patch.badge ? { stickerBadge: patch.badge } : {}),
        },
      };
    }, options);
  }, [set, setSilent, selection]);

  const handleDeleteSticker = useCallback((id) => {
    set((prev) => {
      const targetId = id || selection?.id;
      const nextList = removeItemById(prev.stickers, targetId);
      return {
        ...prev,
        stickers: nextList,
        style: {
          ...prev.style,
          stickerBadge: nextList.length > 0 ? nextList[0].badge : '',
        },
      };
    });
    if (selection?.type === 'sticker' && (!id || selection.id === id)) {
      setSelection(null);
    }
  }, [set, selection]);

  const handleClearStickers = useCallback(() => {
    set((prev) => ({
      ...prev,
      stickers: [],
      style: {
        ...prev.style,
        stickerBadge: '',
      },
    }));
    if (selection?.type === 'sticker') {
      setSelection(null);
    }
  }, [set, selection]);

  // Video overlay effects (transparent-preview via multiply blend) -- same
  // instance shape/CRUD pattern as stickers, no legacy single-slot mirror
  // since this is a new feature with nothing to stay back-compatible with.
  const handleAddEffect = useCallback((effectId, asset = null) => {
    const dur = 3.0;
    const start = Math.round(playhead * 10) / 10;
    const maxEnd = totalDuration > 0 ? totalDuration : (start + dur);
    const end = Math.round(Math.min(maxEnd, start + dur) * 10) / 10;
    const newId = `effect-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
    set((prev) => {
      const existing = prev.effects || [];
      // Every effect defaults to dead center -- fine for one at a time, but
      // stacking several that overlap in time (e.g. clicking + repeatedly)
      // means every one of them multiply-blends onto the exact same pixels
      // as the last, compounding into an unreadable dark smudge instead of
      // showing any single icon cleanly. Spread same-instant adds across a
      // small preset grid instead; effects that don't overlap in time reuse
      // center since they're never composited together anyway.
      const overlapCount = existing.filter((e) => e && !e.hidden && (e.start ?? 0) < end && (e.end ?? 0) > start).length;
      const slots = [
        { normX: 0.5, normY: 0.35 },
        { normX: 0.25, normY: 0.2 },
        { normX: 0.75, normY: 0.2 },
        { normX: 0.25, normY: 0.55 },
        { normX: 0.75, normY: 0.55 },
      ];
      const { normX, normY } = slots[overlapCount % slots.length];
      const recolorMeta = asset?.recolorable
        ? asset
        : getOverlayRecolorMetadata('effect', effectId);
      const newEffect = {
        id: newId, effectId, start, end, normX, normY, scale: 1.0, hidden: false,
        ...(recolorMeta.recolorable ? {
          recolor: 'accent',
          recolorSourceHue: Number(recolorMeta.recolor_source_hue),
        } : {}),
      };
      return { ...prev, effects: [...existing, newEffect] };
    });
    setSelection({ type: 'effect', id: newId });
  }, [playhead, totalDuration, set]);

  const handleUpdateEffect = useCallback((idOrPatch, maybePatch, options) => {
    let id = null;
    let patch = {};
    if (typeof idOrPatch === 'string') {
      id = idOrPatch;
      patch = maybePatch || {};
    } else if (typeof idOrPatch === 'object' && idOrPatch !== null) {
      id = idOrPatch.id || null;
      patch = idOrPatch;
    }
    (options?.silent ? setSilent : set)((prev) => {
      const currentList = prev.effects || [];
      const targetId = id || selection?.id;
      const nextList = updateItemById(currentList, targetId, patch);
      return { ...prev, effects: nextList };
    }, options);
  }, [set, setSilent, selection]);

  const handleDeleteEffect = useCallback((id) => {
    set((prev) => {
      const targetId = id || selection?.id;
      return { ...prev, effects: removeItemById(prev.effects, targetId) };
    });
    if (selection?.type === 'effect' && (!id || selection.id === id)) {
      setSelection(null);
    }
  }, [set, selection]);

  const handleClearEffects = useCallback(() => {
    set((prev) => ({ ...prev, effects: [] }));
    if (selection?.type === 'effect') {
      setSelection(null);
    }
  }, [set, selection]);


  const handleResetSubtitleTimings = useCallback(() => {
    if (!initialCuesRef.current || initialCuesRef.current.length === 0) return;
    cuesDirty.current = true;
    set((prev) => {
      const restored = prev.cuesList.map((c, i) => {
        const init = initialCuesRef.current[i] || initialCuesRef.current.find((ic) => ic._uid === c._uid || ic.id === c.id);
        if (init && typeof init.start === 'number' && typeof init.end === 'number') {
          return {
            ...c,
            start: init.start,
            end: init.end,
          };
        }
        return c;
      });
      return {
        ...prev,
        cuesList: restored.sort((a, b) => a.start - b.start),
      };
    });
    setSaveStatus('dirty');
    showToast('รีเซ็ตเวลาคำบรรยายกลับสู่ค่าตั้งต้นแล้ว');
  }, [set, showToast]);

  const handleCloseAllCaptionGaps = useCallback(() => {
    cuesDirty.current = true;
    set((prev) => {
      if (!prev.cuesList || !prev.cuesList.length) return prev;
      const sorted = [...prev.cuesList].sort((a, b) => a.start - b.start);
      let curTime = sorted[0].start;
      const closed = sorted.map((c) => {
        const dur = Math.max(0.2, Math.round((c.end - c.start) * 100) / 100);
        const start = Math.round(curTime * 100) / 100;
        const end = Math.round((start + dur) * 100) / 100;
        curTime = end;
        return { ...c, start, end };
      });
      return { ...prev, cuesList: closed };
    });
    setSaveStatus('dirty');
    showToast('ดูดกล่องคำบรรยายให้เรียงชิดติดกันเรียบร้อยแล้ว');
  }, [set, showToast]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleManualSave();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleManualSave]);

  // `options` as in handleUpdateOverlay: { silent: true } inside a canvas drag.
  const patchStyle = useCallback((patch, options) => {
    (options?.silent ? setSilent : set)((prev) => ({ ...prev, style: { ...prev.style, ...patch } }), options);
  }, [set, setSilent]);

  const patchSpotlight = useCallback((patch) => {
    set((prev) => {
      const base = prev.spotlight || DEFAULT_EDITOR_SPOTLIGHT;
      return { ...prev, spotlight: { ...base, ...patch, focus: { ...base.focus, ...(patch.focus || {}) } } };
    });
  }, [set]);

  const patchSpotlightLive = useCallback((patch) => {
    setSilent((prev) => {
      const base = prev.spotlight || DEFAULT_EDITOR_SPOTLIGHT;
      return { ...prev, spotlight: { ...base, ...patch, focus: { ...base.focus, ...(patch.focus || {}) } } };
    });
  }, [setSilent]);

  // What the PLAYER draws. Never what any editor control reads: this copy is
  // deliberately disabled while the user is previewing without the cutout,
  // and writing it back would disable the feature for real.
  const previewBackgroundIsolation = useMemo(
    () => {
      const config = backgroundIsolation?.scope_mode === 'behind_text_windows'
        ? { ...backgroundIsolation, active_clip_ids: activeCutoutClips.map((clip) => clip.id),
          active_intervals_by_clip: scopedCutoutClipIntervals }
        : backgroundIsolation;
      return isCutoutHidden ? { ...(config || {}), enabled: false } : config;
    },
    [isCutoutHidden, backgroundIsolation, activeCutoutClips, scopedCutoutClipIntervals],
  );

  const patchBackgroundIsolation = useCallback((next) => {
    cutoutContextRef.current.generation += 1;
    set((prev) => ({ ...prev, backgroundIsolation: next || null }));
  }, [set]);

  // Product points picked on the preview. They are project-level config, so
  // they go through patchBackgroundIsolation only: previewBackgroundIsolation
  // is a view-only mask and writing it back would persist "hidden" for real.
  const hasReadyCutoutClipArtifact = useMemo(
    () => (clipList || []).some((clip) => clip?.background_isolation?.artifact?.status === 'ready'),
    [clipList],
  );
  const handlePickSubjectPoint = useCallback(async (point, reference) => {
    if (backgroundIsolationPreparing) return;
    const next = addSubjectPointToConfig(backgroundIsolation, point,
      { hasReadyClipArtifact: hasReadyCutoutClipArtifact, reference });
    if (next !== backgroundIsolation) patchBackgroundIsolation(next);

    // Call interactive SAM 2 daemon on GPU for instant glowing shimmer outline (<50ms)
    if (reference?.sourcePath && next?.subject_points?.length > 0) {
      setSubjectContourLoading(true);
      try {
        const res = await interactiveSegment({
          source_path: reference.sourcePath,
          timestamp: reference.sourceStart ?? 0.0,
          points: next.subject_points,
          width: 540,
          height: 960,
        });
        if (res?.ok && res.contours) {
          setSubjectContours(res.contours);
        }
      } catch (err) {
        console.warn('Interactive segment preview failed:', err);
      } finally {
        setSubjectContourLoading(false);
      }
    }
  }, [backgroundIsolation, backgroundIsolationPreparing, hasReadyCutoutClipArtifact, patchBackgroundIsolation]);
  const handleClearSubjectPoints = useCallback(() => {
    if (backgroundIsolationPreparing) return;
    const next = clearSubjectPointsOnConfig(backgroundIsolation,
      { hasReadyClipArtifact: hasReadyCutoutClipArtifact });
    if (next !== backgroundIsolation) patchBackgroundIsolation(next);
    setSubjectContours([]);
  }, [backgroundIsolation, backgroundIsolationPreparing, hasReadyCutoutClipArtifact, patchBackgroundIsolation]);
  const handleToggleSubjectPick = useCallback((nextActive) => {
    setSubjectPickMode((current) => (typeof nextActive === 'boolean' ? nextActive : !current));
  }, []);
  // Picking only makes sense while the cutout is on, visible and idle.
  const subjectPickAllowed = backgroundIsolation?.enabled === true
    && !isCutoutHidden && !backgroundIsolationPreparing;
  // Reset during render (React's documented derived-state pattern) so a stale
  // `true` cannot come back when the cutout is switched on again.
  if (subjectPickMode && !subjectPickAllowed) setSubjectPickMode(false);

  // A page reload or a short network outage can happen after the backend has
  // already finished. Rebind a completed task's artifact to the matching
  // timeline clips so the user does not need to run cutout again manually.
  useEffect(() => {
    if (backgroundIsolationPreparing) return;
    if (!backgroundIsolation?.request_id) return;
    const completed = completedBackgroundIsolationTasks(tasks, projectName, backgroundIsolation.request_id);
    if (!completed.length || !clipList?.length) return;

    const updates = completed.map((task) => ({
      sourcePath: String(task.payload.source_path).toLowerCase(),
      rotation: [0, 90, 180, 270].includes(Number(task.payload.rotation)) ? Number(task.payload.rotation) : 0,
      start: Number(task.payload.start) || 0,
      duration: task.payload.duration == null ? null : Number(task.payload.duration),
      config: task.result,
    }));
    const matchingUpdate = (clip) => clip.background_isolation?.artifact?.status === 'ready' ? null : updates
      .filter((update) => backgroundIsolationWindowContainsClip(update, clip, { sourceDurations: durations }))
      .sort((left, right) => (left.duration ?? Infinity) - (right.duration ?? Infinity))[0];
    const needsBinding = clipList.some((clip) => {
      const update = matchingUpdate(clip);
      return update
        && clip.background_isolation?.artifact?.id !== update.config.artifact.id;
    });
    if (!needsBinding) return;

    setSilent((prev) => ({
      ...prev,
      clipList: (prev.clipList || []).map((clip) => {
        const update = matchingUpdate(clip);
        return update ? { ...clip, background_isolation: update.config } : clip;
      }),
    }));
  }, [clipList, durations, projectName, setSilent, tasks, backgroundIsolation?.request_id, backgroundIsolationPreparing]);

  const prepareBackgroundIsolation = useCallback(async () => {
    const sourceClips = (clipList || []).filter((clip) => clip?.source_path);
    if (!sourceClips.length) {
      showToast('ยังไม่มีคลิปใน Timeline สำหรับตัดพื้นหลัง');
      return;
    }
    const unique = backgroundIsolationGroups;
    if (backgroundIsolation?.scope_mode === 'behind_text_windows' && !unique.length) {
      showToast('ไม่มีข้อความหลังสินค้าที่ต้องเตรียม Cutout');
      return;
    }
    const unresolved = unique.filter((group) => group.unresolved);
    if (unresolved.length) {
      showToast(`ยังอ่านความยาวคลิปไม่ครบ ${unresolved.length} ช่วง กรุณารอ Preview โหลดแล้วลองอีกครั้ง`);
      return;
    }
    if (backgroundIsolationPlan.conflictCount > 0) {
      showToast(`กรุณาปิดพื้นหลังเบลอ ${backgroundIsolationPlan.conflictCount} คลิปก่อนเตรียม Cutout`);
      return;
    }
    // Picked product points (subject_points) travel inside this config to the
    // backend; buildPrepareBaseConfig keeps them even for a fresh config.
    const baseConfig = buildPrepareBaseConfig(backgroundIsolation, crypto.randomUUID());
    patchBackgroundIsolation({
      ...baseConfig,
      enabled: true,
      artifact: { ...(baseConfig.artifact || {}), id: null, status: 'processing' },
    });
    // Reset all target clips in unique groups to pending/queued state so timeline immediately clears old purple
    set((prev) => ({
      ...prev,
      clipList: (prev.clipList || []).map((clip) => {
        const inUnique = unique.some((g) => (g.clips || []).some((c) => c.id === clip.id));
        if (!inUnique) return clip;
        return {
          ...clip,
          background_isolation: {
            ...(clip.background_isolation || {}),
            enabled: true,
            artifact: {
              ...(clip.background_isolation?.artifact || {}),
              id: null,
              status: 'queued',
            },
          },
        };
      }),
    }));
    const jobContext = { ...cutoutContextRef.current };
    const isCurrentJob = () => cutoutContextRef.current.projectName === jobContext.projectName
      && cutoutContextRef.current.generation === jobContext.generation;
    setBackgroundIsolationError('');
    setBackgroundIsolationTaskIds([]);
    setBackgroundIsolationPreparing(true);
    isLocalPreparingRef.current = true;
    setCutoutBatchState({
      activeIndex: 0,
      totalCount: unique.length,
      activeClipIds: (unique[0]?.clips || []).map((c) => c.id),
      queuedClipIds: unique.slice(1).flatMap((g) => (g.clips || []).map((c) => c.id)),
    });
    try {
      for (let i = 0; i < unique.length; i++) {
        const item = unique[i];
        if (!isCurrentJob()) return;
        setCutoutBatchState({
          activeIndex: i,
          totalCount: unique.length,
          activeClipIds: (item.clips || []).map((c) => c.id),
          queuedClipIds: unique.slice(i + 1).flatMap((g) => (g.clips || []).map((c) => c.id)),
        });
        const request = {
          source_path: item.sourcePath,
          config: baseConfig,
          start: item.start,
          duration: item.duration,
          active_intervals: backgroundIsolation?.scope_mode === 'behind_text_windows'
            ? item.active_intervals.map(({ start, end }) => [start, end]) : null,
          fps: 30,
          width: 1080,
          height: 1920,
          rotation: item.rotation,
          project_name: projectName,
        };
        const preflight = await preflightBackgroundIsolation(request);
        if (!isCurrentJob()) return;
        if (!preflight?.ok) {
          const issue = preflight?.issues?.find((candidate) => candidate.severity === 'error');
          throw new Error(issue?.message || 'เครื่องยังไม่พร้อมประมวลผล Cutout');
        }
        const response = await startBackgroundIsolation(request);
        if (!isCurrentJob()) return;
        setBackgroundIsolationTaskIds((current) => [...new Set([...current, response.task_id])]);
        pollTasks?.();
        const task = await waitForBackgroundIsolationTask(response.task_id, getTaskStatus);
        if (!isCurrentJob()) return;
        if (task?.status === 'cancelled') {
          const cancelled = new Error('ยกเลิกการเตรียม Cutout แล้ว');
          cancelled.cancelled = true;
          throw cancelled;
        }
        if (task?.status !== 'completed' || !task.result?.artifact?.id) {
          throw new Error(task?.error || 'background isolation task did not complete');
        }
        const completedConfig = { ...task.result,
          scope_mode: backgroundIsolation?.scope_mode || 'legacy_clip',
          active_intervals: item.active_intervals };
        set((prev) => prev.backgroundIsolation?.request_id !== baseConfig.request_id ? prev : ({
          ...prev,
          clipList: (prev.clipList || []).map((clip) => {
            const before = item.clips.find((candidate) => candidate.id === clip.id);
            const covered = Boolean(before)
              && backgroundIsolationWindowContainsClip(item, clip, { sourceDurations: durations });
            if (!covered) return clip;
            const previous = clip.background_isolation;
            const legacy = previous?.scope_mode === 'behind_text_windows'
              ? previous.legacy_background_isolation : previous;
            return { ...clip, background_isolation: {
              ...completedConfig,
              ...(backgroundIsolation?.scope_mode === 'behind_text_windows' && legacy
                ? { legacy_background_isolation: legacy } : {}),
            } };
          }),
        }));
      }
      // Ready artifacts are stored per clip because each trim range has its
      // own extracted sequence.  Keep the project-level marker honest: it is
      // only a default/fallback config and has no single artifact id.
      patchBackgroundIsolation({ ...baseConfig, enabled: true, artifact: { ...(baseConfig.artifact || {}), id: null, status: 'missing' } });
      showToast(`เตรียม cutout สำเร็จ ${sourceClips.length} คลิป จาก ${unique.length} ช่วงวิดีโอ`);
    } catch (error) {
      if (!isCurrentJob()) return;
      const message = error?.friendlyMessage || error?.message || 'เตรียม cutout ไม่สำเร็จ';
      const status = error?.cancelled ? 'cancelled' : 'error';
      patchBackgroundIsolation({ ...baseConfig, enabled: true, artifact: { ...(baseConfig.artifact || {}), id: null, status } });
      setBackgroundIsolationError(message);
      showToast(message);
    } finally {
      isLocalPreparingRef.current = false;
      if (cutoutContextRef.current.projectName === jobContext.projectName) {
        setBackgroundIsolationPreparing(false);
        setCutoutBatchState({ activeIndex: 0, totalCount: 0, activeClipIds: [], queuedClipIds: [] });
      }
      setBackgroundIsolationTaskIds([]);
      pollTasks?.();
    }
  }, [backgroundIsolation, backgroundIsolationGroups, backgroundIsolationPlan.conflictCount, clipList, getTaskStatus, patchBackgroundIsolation, projectName, pollTasks, set, showToast, startBackgroundIsolation]);

  const cancelBackgroundIsolation = useCallback(async () => {
    isLocalPreparingRef.current = false;
    const ids = [...backgroundIsolationTaskIds];
    await Promise.all(ids.map((taskId) => cancelTask?.(taskId)));
    setBackgroundIsolationError('ยกเลิกการเตรียม Cutout แล้ว');
    setBackgroundIsolationPreparing(false);
    setCutoutBatchState({ activeIndex: 0, totalCount: 0, activeClipIds: [], queuedClipIds: [] });
    pollTasks?.();
  }, [backgroundIsolationTaskIds, cancelTask, pollTasks]);

  const handleClearAllBgBlur = useCallback(() => {
    set((prev) => ({
      ...prev,
      clipList: clearBackgroundIsolationConflicts(prev.clipList),
    }));
    showToast('ปิดพื้นหลังเบลอทุกคลิปเรียบร้อยแล้ว');
  }, [set, showToast]);

  const handleSelectClipById = useCallback((clipId) => {
    handleSelect({ type: 'clip', id: clipId });
    showToast('เลือกคลิปบน Timeline เรียบร้อยแล้ว');
  }, [handleSelect, showToast]);

  const patchStylePreset = useCallback((presetId) => {
    const normalized = normalizeStylePreset(presetId);
    patchStyle({ style_preset: normalized });
    const matchedHook = templateForStylePreset(normalized);
    if (hookOverlay && matchedHook) {
      const isStyleHook = Object.values(STYLE_PRESET_TO_TEMPLATE).includes(hookOverlay.template)
        || hookOverlay.template === DEFAULT_HOOK_TEMPLATE
        || !hookOverlay.template;
      if (isStyleHook) {
        handleReplaceOverlay(hookOverlay.id, withHookTemplate(hookOverlay, matchedHook));
      }
    }
  }, [patchStyle, hookOverlay, handleReplaceOverlay]);


  // Building the videoItem CoverStudioModal expects from whatever the editor
  // currently knows about this angle -- same shape ContentTrackerHub's
  // handleOpenCoverStudio builds, minus the fields only the tracker's list
  // view has (cover_url/cover_3x4_url), which the modal re-fetches itself.
  const buildCoverGateItem = useCallback((angle, product) => ({
    path: angle?.video_url || '',
    rel_path: angle?.video_url || '',
    name: product?.name || '',
    product_name: product?.name || '',
    project_name: angle?.project_name || projectName || '',
    hook_title: angle?.hook_title || '',
    angle_name: angle?.angle_name || '',
    cover_path: angle?.cover_path || '',
    cover_3x4_path: angle?.cover_3x4_path || '',
    cover_9x16_path: angle?.cover_9x16_path || '',
    parentProduct: product,
    angle_id: angle?.angle_id,
  }), [projectName]);

  // Shared by handleApply's render-blocking gate and the proactive
  // coverStatus check below -- both need to resolve, by project_name
  // against a FRESH product fetch (not the productContext/angleIndex props,
  // which are null whenever the editor was reached via the header dropdown
  // rather than the product-flow tab), which angle this project belongs to
  // and whether it already has a cover.
  const findMatchingAngle = useCallback(async (targetProjectName) => {
    const fresh = await readProducts({ force: true });
    const freshList = Array.isArray(fresh) ? fresh : (fresh?.products || []);
    for (const p of freshList) {
      const a = (p.angles || []).find((ang) => ang.project_name === targetProjectName);
      if (a) return { matchProduct: p, matchAngle: a };
    }
    return { matchProduct: null, matchAngle: null };
  }, [readProducts]);

  // Lets the user check/create a cover from the header's "ปก" button once
  // the angle has a rendered export -- Cover Studio can only pull a frame
  // from an actual export file, so this stays blocked pre-render too.
  const openCoverStudioManually = useCallback(async () => {
    if (!projectName) return;
    setCoverGateChecking(true);
    try {
      const { matchProduct, matchAngle } = await findMatchingAngle(projectName);
      if (!matchAngle) {
        setApplyError('ไม่พบข้อมูลสินค้า/มุมของโปรเจกต์นี้ ไม่สามารถสร้างปกได้');
      } else if (!matchAngle.video_url) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
        const player = isMobileView ? mobilePlayerRef.current : desktopPlayerRef.current;
        const snapshot = await player?.captureCoverFrame?.();
        if (!snapshot) {
          setApplyError('ยังจับภาพจาก Timeline ไม่ได้ กรุณารอให้ Preview โหลดเสร็จแล้วลองอีกครั้ง');
        } else {
          const item = buildCoverGateItem(matchAngle, matchProduct);
          item.timeline_snapshot = {
            data_url: snapshot,
            seconds: Number(playhead.toFixed(2)),
          };
          setCoverGateItem(item);
        }
        setCoverGateChecking(false);
        return;
      } else {
        setCoverGateItem(buildCoverGateItem(matchAngle, matchProduct));
      }
    } catch (e) {
      setApplyError('ตรวจสอบข้อมูลปกไม่สำเร็จ: ' + (e.response?.data?.detail || e.message));
    }
    setCoverGateChecking(false);
  }, [projectName, findMatchingAngle, buildCoverGateItem, isMobileView, playhead]);

  // Refreshed whenever the loaded project changes so the header's cover
  // badge reflects this project's actual state instead of staying stuck on
  // whatever the previously-loaded project showed.
  useEffect(() => {
    if (!projectName) { setCoverStatus(null); return; }
    let cancelled = false;
    findMatchingAngle(projectName)
      .then(({ matchAngle }) => {
        if (cancelled) return;
        if (!matchAngle) { setCoverStatus(null); return; }
        setCoverStatus(!!(matchAngle.cover_path || matchAngle.cover_3x4_path || matchAngle.cover_9x16_path));
      })
      .catch(() => { if (!cancelled) setCoverStatus(null); });
    return () => { cancelled = true; };
  }, [projectName, findMatchingAngle]);

  const handleApply = async (requestedCutoutOverride = false) => {
    const forceDisableCutout = requestedCutoutOverride === true;
    if (forceDisableCutout) {
      setApplyError(null);
      showToast('เริ่มเรนเดอร์แบบไม่ใช้ Cutout ชั่วคราว...');
    }
    if (!projectName) { setApplyError('เลือกโปรเจกต์ก่อน'); return; }
    if (!clipList.length) { setApplyError('เพิ่มคลิปในไทม์ไลน์ก่อน'); return; }
    if (!renderPreflight.canRender) {
      setApplyError(preflightBlockingMessage(renderPreflight));
      return;
    }
    if (isProjectPosted) {
      setApplyError('คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม');
      return;
    }
    const effectiveBgIsolation = forceDisableCutout
      ? { ...(backgroundIsolation || {}), schema_version: 1, enabled: false }
      : backgroundIsolation?.scope_mode === 'behind_text_windows'
        ? { ...backgroundIsolation, active_clip_ids: activeCutoutClips.map((clip) => clip.id),
          active_intervals_by_clip: scopedCutoutClipIntervals }
        : backgroundIsolation;

    if (!forceDisableCutout && effectiveBgIsolation?.enabled === true && backgroundIsolationPlan.conflictCount > 0) {
      setApplyError(`ปิดพื้นหลังเบลอ ${backgroundIsolationPlan.conflictCount} คลิปก่อน Render ด้วย Cutout`);
      return;
    }
    if (!forceDisableCutout && effectiveBgIsolation?.enabled === true
      && !(effectiveBgIsolation.scope_mode === 'behind_text_windows' && backgroundIsolationGroups.length === 0)
      && backgroundIsolationStatus.state !== 'ready'
      && !(effectiveBgIsolation.scope_mode !== 'behind_text_windows' && backgroundIsolationStatus.state === 'partial')) {
      setApplyError('Cutout ยังไม่พร้อม กรุณากดเตรียม Cutout ให้สถานะพร้อมก่อน Render');
      return;
    }

    // Re-check posted status and the persisted cover fresh (not just the
    // isProjectPosted/coverStatus props) before letting a render start. The
    // pre-render Cover Studio flow can create a cover from the current
    // Timeline frame, so a first render is safe to gate behind a saved cover.
    setCoverGateChecking(true);
    try {
      const { matchAngle } = await findMatchingAngle(projectName);
      if (!matchAngle) {
        setApplyError('ไม่พบข้อมูลโปรเจกต์นี้ กรุณาสร้างและบันทึกหน้าปกก่อน Render');
        setCoverGateChecking(false);
        return;
      }
      if (matchAngle?.status === 'posted' || matchAngle?.posted_at) {
        setApplyError('คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม');
        setCoverGateChecking(false);
        setIsProjectPosted(true);
        return;
      }
      const hasSavedCover = Boolean(
        matchAngle.cover_path || matchAngle.cover_3x4_path || matchAngle.cover_9x16_path,
      );
      if (!hasSavedCover) {
        setApplyError('กรุณาสร้างและบันทึกหน้าปกก่อน Render — กดปุ่ม “ปก” แล้วบันทึกหน้าปกก่อน');
        setCoverGateChecking(false);
        return;
      }
    } catch (e) {
      // Do not fail open: without a fresh cover check, rendering could bypass
      // the required pre-render cover step.
      setApplyError('ตรวจสอบหน้าปกไม่สำเร็จ กรุณาลองใหม่ก่อน Render');
      setCoverGateChecking(false);
      return;
    }
    setCoverGateChecking(false);

    const base = loadedAudioStyle.current;
    const audioMutes = effectiveAudioMutes(trackMix);
    const baselineMutes = loadedAudioMutes.current;
    const audioDirty = (style.bgmName ?? null) !== (base.bgmName ?? null)
      || (style.bgmVolume ?? 0.12) !== (base.bgmVolume ?? 0.12)
      || !!style.bgmDucking !== !!base.bgmDucking
      || clampBusVolume(style.voiceVolume, VOICE_VOLUME_DEFAULT) !== clampBusVolume(base.voiceVolume, VOICE_VOLUME_DEFAULT)
      || clampBusVolume(style.sfxVolume, SFX_VOLUME_DEFAULT) !== clampBusVolume(base.sfxVolume, SFX_VOLUME_DEFAULT)
      || AUDIO_TRACKS.some((track) => !!audioMutes[track] !== !!baselineMutes[track]);

    const capBase = loadedCaptionStyle.current;
    const captionDirty = (style.captionPosition || 'bottom') !== capBase.captionPosition
      || (style.captionColor || '#FFFFFF') !== capBase.captionColor
      || (style.captionScale ?? 1) !== capBase.captionScale;

    // The old two-click confirm here guarded a tail that came out with sound
    // and no picture. The renderer holds the last frame across that gap now,
    // so there is nothing left to confirm.
    setConfirmGap(0);

    // Mark angle as in_production only when user actually triggers the render
    if (productContext?.id && productContext?.angles?.[angleIndex]?.angle_id) {
      try {
        updateAngleStatus(productContext.id, productContext.angles[angleIndex].angle_id, 'in_production')
          .then(() => workspaceData?.invalidateTrackerData?.()).catch(() => {});
      } catch (e) {}
    }
    try {
      await updateProjectState(projectName, projectSavePayload);
      const res = await startReroll({
        project_name: projectName,
        part: audioDirty ? 'bgm' : 'subtitles',
        // Scoped Cutout references the current editor clip ids. Persistence
        // still strips these local ids; the render request needs them only
        // for this run so the backend can resolve each active clip.
        clip_list: serializeRenderClips(clipList, effectiveBgIsolation?.scope_mode),
        transitions: savePayload.transitions,
        overlays,
        // Both of these were missing from the render request: bilingual was
        // pinned to true and ghost_reveal was never sent at all, so their
        // toggles changed the preview and then the export ignored them.
        bilingual_subtitles: style.bilingualSubtitles !== false,
        ghost_reveal: !!style.ghostReveal,
        show_watermark: style.showWatermark !== false,
        font_name: style.fontName,
        bgm_name: style.bgmName,
        lut_name: style.lutName,
        // "" is meaningful here: it clears the badge stored on the project.
        sticker_badge: style.stickerBadge ?? '',
        lut_intensity: style.lutIntensity ?? 1,
        bgm_volume: style.bgmVolume ?? 0.12,
        bgm_ducking: !!style.bgmDucking,
        audio_mutes: audioMutes,
        export_preset: exportPreset,
        style_preset: activeStylePreset,
        caption_position: style.captionPosition || 'bottom',
        caption_color: style.captionColor || '#FFFFFF',
        caption_scale: style.captionScale ?? 1,
        sticker_position: style.stickerPosition || 'top_right',
        sticker_scale: style.stickerScale ?? 1,
        ...serializeRenderFeatures({
          stickers,
          effects,
          spotlight,
          backgroundIsolation: effectiveBgIsolation,
        }),
      });
      pendingRenderBaseline.current = {
        jobId: res.job_id,
        projectName,
        audioStyle: {
          bgmName: style.bgmName ?? null,
          bgmVolume: style.bgmVolume ?? 0.12,
          bgmDucking: !!style.bgmDucking,
          voiceVolume: clampBusVolume(style.voiceVolume, VOICE_VOLUME_DEFAULT),
          sfxVolume: clampBusVolume(style.sfxVolume, SFX_VOLUME_DEFAULT),
        },
        audioMutes,
        captionStyle: {
          captionPosition: style.captionPosition || 'bottom',
          captionColor: style.captionColor || '#FFFFFF',
          captionScale: style.captionScale ?? 1,
        },
      };
      startJob(res.job_id);
      pollTasks?.();
    } catch (err) {
      pendingRenderBaseline.current = null;
      stopJob();
      setApplyError(formatErrorText(err));
      if (err?.response?.status === 409) setRevisionNotice('conflict');
    }
  };

  // Cover saved from the modal: persist it to the angle, then just close and
  // update the badge -- the user opened this proactively to check/create a
  // cover, not to render.
  const handleCoverGateSaved = useCallback(async (res) => {
    const productId = coverGateItem?.parentProduct?.id;
    const angleId = coverGateItem?.angle_id;
    if (productId && angleId && (res?.cover_path || res?.cover_3x4_path || res?.cover_9x16_path)) {
      try {
        await updateAngleCover(productId, angleId, {
          cover_path: res.cover_path || null,
          cover_3x4_path: res.cover_3x4_path || null,
          cover_9x16_path: res.cover_9x16_path || null,
        });
        workspaceData?.invalidateTrackerData?.();
      } catch (e) {
        setApplyError('บันทึกภาพปกไม่สำเร็จ: ' + (e.response?.data?.detail || e.message));
        return;
      }
      setCoverStatus(true);
    }
    setCoverGateItem(null);
  }, [coverGateItem, workspaceData]);

  // What the preview plays instead of a baked mix: the voice stem plus the
  // same BGM and per-cue SFX files the renderer will mix, resolved to media
  // URLs from the asset registry (each entry already carries an absolute
  // path). Changing BGM or dropping an SFX on a cue is then audible at once,
  // where before it needed a full re-render to hear.
  //
  // Every lookup here mirrors a backend resolver so the preview never plays a
  // different file than the render: resolve_bgm_path()'s default-then-first
  // fallback (sfx_manager.py:41-60), resolve_sfx_path()'s legacy short-name
  // aliases (asset_registry.py:244-258), and which hits the mix keeps:
  // plan_sfx_events() (sfx_manager.py) enforces SFX_MIN_GAP_S between hits and
  // lays down the hook boom at t=0 only when the hook line has no opener SFX of
  // its own -- planSfxEvents (lib/sfxPlan.js) is the same rule set.
  const audioStems = useMemo(() => {
    const music = assets.music || [];
    const sfxList = assets.sfx || [];

    const findSfx = (name) => {
      if (!name) return null;
      const canonical = LEGACY_SFX_ALIASES[name] || name;
      return sfxList.find((s) => s.id === canonical) || null;
    };

    // resolve_bgm_path: the named file, else the default track, else the first
    // one in the folder -- so "no BGM chosen" still has music in the render.
    const bgmEntry =
      (style.bgmName ? music.find((m) => m.id === style.bgmName || m.name === style.bgmName) : null)
      || music.find((m) => m.id === assets.default_bgm || m.name === assets.default_bgm)
      || music[0]
      || null;

    // Hidden overlays stay silent in the preview (they are not drawn either).
    const liveOverlays = (overlays || []).filter((o) => o && !o.hidden);
    const boom = findSfx('boom');
    const plan = planSfxEvents(cuesList || [], liveOverlays, {
      totalDuration: audioDuration > 0 ? audioDuration : null,
      boomAvailable: !!boom,
      sfxFilename: (tag) => findSfx(tag)?.name || null,
    });
    const sfxShots = [];
    plan.forEach((ev) => {
      if (ev.source === 'boom') {
        // Only when the hook line carries no opener of its own.
        sfxShots.push({ time: 0, id: 'boom', name: boom.name, url: toMediaUrl(boom.path) });
        return;
      }
      const entry = findSfx(ev.sfx);
      if (!entry) return;
      const shot = {
        time: ev.start,
        id: ev.sfx,
        // The render's pre-roll test reads the resolved *filename*, not the cue
        // tag (sfx_manager.py:107) -- pass it through so the preview fires early
        // on exactly the same files.
        name: entry.name,
        url: toMediaUrl(entry.path),
      };
      if (ev.source === 'overlay') shot.overlayId = liveOverlays[ev.index].id;
      sfxShots.push(shot);
    });

    return {
      voiceUrl,
      bgm: bgmEntry
        ? {
            url: toMediaUrl(bgmEntry.path),
            volume: style.bgmVolume ?? 0.12,
            ducking: !!style.bgmDucking,
          }
        : null,
      sfx: sfxShots,
      // Track Mix levels (L4-05): the same clamped values the save payload
      // sends to the render's mix stage.
      voiceVolume: clampBusVolume(style.voiceVolume, VOICE_VOLUME_DEFAULT),
      sfxVolume: clampBusVolume(style.sfxVolume, SFX_VOLUME_DEFAULT),
    };
  }, [voiceUrl, style.bgmName, style.bgmVolume, style.bgmDucking, style.voiceVolume, style.sfxVolume, assets.music, assets.sfx, cuesList, overlays, audioDuration]);

  // The colour grade the preview should show, resolved the same way the
  // renderer resolves it (registry id or filename -- see resolve_lut_path).
  const grade = useMemo(() => {
    if (!style.lutName) return null;
    const entry = (assets.luts || []).find((l) => l.id === style.lutName || l.name === style.lutName);
    if (!entry) return null;
    return { url: toMediaUrl(entry.path), intensity: style.lutIntensity ?? 1 };
  }, [style.lutName, style.lutIntensity, assets.luts]);

  // The stem files the timeline draws waveforms from.
  const stemUrls = useMemo(() => ({
    voice: voiceUrl || audioUrl || null,
    bgm: audioStems?.bgm?.url || null,
  }), [voiceUrl, audioUrl, audioStems]);

  // Height the phone's timeline tab wants: its toolbar plus exactly the rows on
  // show. Folded audio and no text overlays make it short; unfolding grows it.
  const mobileTimelineH = MOBILE_TOOLBAR_H + tracksFitHeight({
    textOverlays: (textOverlays?.length || 0) > 0,
    sticker: (stickers?.length || 0) > 0,
    effect: (effects?.length || 0) > 0,
    audioCollapsed,
  });

  const {
    timelineH,
    applyTimelineH,
    assetW,
    applyAssetW,
    leftSidebarCollapsed,
    toggleLeftSidebar,
    inspectorW,
    applyInspectorW,
    rightSidebarCollapsed,
    toggleRightSidebar,
    mobilePreviewH,
    applyMobilePreviewH,
    resetPanelSizes,
    resizeRef,
    assetResizeRef,
    inspectorResizeRef,
    mobileWrapRef,
    mobileResizeRef,
    activeSplitter,
    setActiveSplitter,
  } = usePanelLayout({ mobileTimelineH });

  // The drag clamp has to reserve the timeline's real height, not a guess.
  const reserve = MOBILE_TAB_ROW_H + (Number.isFinite(mobileTimelineH) ? mobileTimelineH : 0);

  const progress = Math.round((jobStatus?.progress || 0) * 100);
  const bgmLabel = useMemo(() => {
    // With nothing chosen this used to read "เสียงหลักของช่อง" -- a fixed
    // string naming a track the render does not use. Name the one that will
    // actually play, and say that it is the default.
    const pick = style.bgmName || assets.default_bgm;
    const found = assets.music?.find((m) => m.id === pick || m.name === pick);
    const label = found ? (found.label_th || found.name) : pick;
    if (!label) return '';
    return style.bgmName ? label : `${label} (ค่าเริ่มต้น)`;
  }, [style.bgmName, assets.music, assets.default_bgm]);

  return (
    <div data-oc-surface="workspace" className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl glass-panel">
      {/* ── HEADER / TOPBAR ── */}
      <EditorHeader
        projectName={projectName}
        setProjectName={setProjectName}
        projectList={projectList}
        loadProject={loadProject}
        loading={loading}
        playhead={playhead}
        totalDuration={totalDuration}
        audioDuration={audioDuration}
        saveStatus={saveStatus}
        handleManualSave={handleManualSave}
        leftSidebarCollapsed={leftSidebarCollapsed}
        toggleLeftSidebar={toggleLeftSidebar}
        rightSidebarCollapsed={rightSidebarCollapsed}
        toggleRightSidebar={toggleRightSidebar}
        zen={zen}
        setZen={setZen}
        resetPanelSizes={resetPanelSizes}
        setSelection={setSelection}
        applying={applying || coverGateChecking}
        handleApply={handleApply}
        exportPreset={exportPreset}
        setExportPreset={setExportPreset}
        exportPresets={EXPORT_PRESETS}
        progress={progress}
        isPosted={isProjectPosted}
        setDeleteError={setDeleteError}
        setDeleteScope={setDeleteScope}
        setDeleteOrigin={setDeleteOrigin}
        setPendingDelete={setPendingDelete}
        coverStatus={coverStatus}
        coverChecking={coverGateChecking}
        onOpenCoverStudio={openCoverStudioManually}
        showWatermark={style.showWatermark !== false}
        onToggleWatermark={(val) => patchStyle({ showWatermark: val })}
        onOpenShortcuts={onOpenShortcuts}
      />

      {loadError && projectName && (
        <div className="flex flex-shrink-0 items-center gap-2 border-b border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300">
          <AlertCircle className="h-3.5 w-3.5" />{loadError}
        </div>
      )}

      {projectName && projectWatermark(channelIdentitySnapshot, channel?.channelId || 'main') === null && (
        <p role="alert" className="border-b border-amber-300/20 bg-amber-300/10 px-4 py-2 text-sm text-amber-200">???????????????????????????????????????????? ???????????????????????</p>
      )}
      <RenderPreflightNotice report={renderPreflight} onSeek={seekPlayer} />
      <ProjectRevisionNotice
        kind={projectName ? revisionNotice : null}
        reloading={revisionReloading}
        onReload={handleRevisionReload}
        onDismiss={() => setRevisionNotice(null)}
      />

      {/* Confirm before a ripple cut. The plan is already computed, so this
          shows exactly what will happen -- how many clips, and how much
          shorter the result is -- rather than asking the user to trust a
          number they cannot check. Applying is one undo step. */}
      {silencePlan && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-4 w-screen h-[100dvh] bg-black/80 backdrop-blur-md animate-fadeIn"
          onClick={handleCancelSilencePlan}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="ยืนยันการตัดช่วงเงียบ"
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-md space-y-4 rounded-2xl sm:rounded-3xl border border-white/[0.14] bg-[#0F1420]/95 backdrop-blur-2xl p-5 sm:p-6 shadow-2xl"
          >
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-300">
                <Scissors className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h2 className="text-lg font-bold text-white">
                  {silencePlan.confirmTitle || 'ตัดช่วงเงียบออก?'}
                </h2>
                <p className="pt-0.5 text-sm text-slate-400">
                  {silencePlan.confirmSubtitle || 'ภาพ เสียงพากย์ ซับ และข้อความหลังจุดนี้จะเลื่อนมาชิดกัน'}
                </p>
              </div>
            </div>

            <p className="rounded-xl bg-white/[0.04] px-3 py-2.5 text-sm text-slate-200">
              {silencePlan.description}
            </p>

            <p className="text-xs text-slate-500">กด Ctrl+Z ย้อนกลับได้ทันทีถ้าไม่ถูกใจ</p>

            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={handleCancelSilencePlan}
                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-white/[0.06] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757]"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                onClick={handleApplySilencePlan}
                className="rounded-lg bg-[#D97757] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#C56646] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757]"
              >
                ตัดเลย
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Why a scan found nothing, or could not run. Dismissible and quiet --
          this is not an error the user caused. */}
      {silenceError && !silencePlan && (
        <div
          className="fixed bottom-4 left-1/2 z-[100] -translate-x-1/2 rounded-xl border border-white/[0.14] bg-[#0F1420]/95 px-4 py-2.5 text-sm text-slate-200 shadow-2xl backdrop-blur-xl"
          role="status"
        >
          <span>{silenceError}</span>
          <button
            type="button"
            onClick={() => setSilenceError('')}
            aria-label="ปิดข้อความ"
            className="ml-3 text-slate-400 transition-colors hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757]"
          >
            <X className="inline h-4 w-4" />
          </button>
        </div>
      )}

      {pendingDelete && (() => {
        const meta = projectList.find((p) => p.project_name === pendingDelete);
        return (
          <div
            className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-4 w-screen h-[100dvh] max-h-[100dvh] overflow-hidden overscroll-none bg-black/80 backdrop-blur-md animate-fadeIn"
            onClick={() => !deleting && setPendingDelete(null)}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-label="ยืนยันการลบโปรเจกต์"
              onClick={(e) => e.stopPropagation()}
              className="relative w-full max-w-md space-y-4 rounded-2xl sm:rounded-3xl border border-white/[0.14] bg-[#0F1420]/95 backdrop-blur-2xl p-5 sm:p-6 shadow-2xl max-h-[85dvh] overflow-y-auto no-scrollbar my-auto"
            >
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-rose-500/15 text-rose-300">
                  <Trash2 className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <h2 className="text-lg font-bold text-white">ลบโปรเจกต์นี้ถาวร?</h2>
                  <p className="truncate pt-0.5 font-mono text-sm text-slate-400">{pendingDelete}</p>
                </div>
              </div>

              {(() => {
                const origin = deleteOrigin;
                const product = origin?.product;
                const angle = origin?.angle;
                const isAnglePosted = angle?.status === 'posted' || !!angle?.posted_at || isProjectPosted;
                const isProductPosted = isAnglePosted || (product?.angles || []).some((a) => a.status === 'posted' || a.posted_at);

                const OPTIONS = [
                  {
                    id: 'project',
                    label: 'ลบเฉพาะโปรเจกต์ตัดต่อ',
                    detail: `บท เสียงพากย์ ซับ ไฟล์เสียงที่มิกซ์แล้ว${meta?.size_mb ? ` · ${meta.size_mb} MB` : ''}`,
                    enabled: true,
                  },
                  {
                    id: 'angle',
                    label: 'ลบมุม/สคริปต์ในเมนูสินค้าด้วย',
                    detail: isAnglePosted
                      ? 'มุมนี้โพสต์ลง TikTok แล้ว — ล็อกเก็บเป็นหลักฐาน (ไม่อนุญาตให้ลบ)'
                      : angle
                      ? `มุม “${angle.angle_name || angle.hook_title}” จะหายจากเมนูสินค้าและแทร็กเกอร์`
                      : 'หามุมที่ตรงกับโปรเจกต์นี้ไม่เจอ (คลิปเก่าที่ยังไม่ได้บันทึกที่มา)',
                    enabled: !!angle && !isAnglePosted,
                  },
                  {
                    id: 'product',
                    label: 'ลบสินค้านี้ทั้งหมด',
                    detail: isProductPosted
                      ? 'สินค้านี้มีคลิปที่โพสต์ลง TikTok แล้ว — ล็อกเก็บเป็นหลักฐาน (ไม่อนุญาตให้ลบ)'
                      : product
                      ? `“${product.name}” พร้อมสคริปต์ทั้ง ${product.angle_count} มุม จะหายทั้งหมด`
                      : 'หาสินค้าที่ผูกกับโปรเจกต์นี้ไม่เจอ',
                    enabled: !!product && !isProductPosted,
                  },
                ];
                return (
                  <div className="space-y-2">
                    {!origin && <p className="text-sm text-slate-400">กำลังตรวจว่าผูกกับอะไรอยู่...</p>}
                    {isAnglePosted && (
                      <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-2.5 text-xs text-emerald-300 leading-relaxed">
                        🛡️ <strong>โปรเจกต์นี้โพสต์ลง TikTok แล้ว:</strong> สามารถลบเฉพาะไฟล์ตัดต่อเพื่อคืนพื้นที่ดิสก์ได้ โดยวิดีโอที่โพสต์แล้วใน Export และประวัติสคริปต์ใน Tracker จะยังคงอยู่ครบถ้วน 100%
                      </div>
                    )}
                    {OPTIONS.map((o) => (
                      <label
                        key={o.id}
                        className={`flex gap-2.5 rounded-xl border p-3 ${
                          o.enabled ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
                        } ${
                          deleteScope === o.id
                            ? 'border-rose-500/60 bg-rose-500/10'
                            : 'border-white/[0.08] bg-black/40 hover:border-white/[0.2]'
                        }`}
                      >
                        <input
                          type="radio"
                          name="delete-scope"
                          checked={deleteScope === o.id}
                          disabled={!o.enabled}
                          onChange={() => setDeleteScope(o.id)}
                          className="mt-0.5 h-[18px] w-[18px] flex-shrink-0 accent-rose-500"
                        />
                        <span className="min-w-0">
                          <span className="block text-sm font-bold text-white">{o.label}</span>
                          <span className="block pt-0.5 text-sm leading-relaxed text-slate-400">{o.detail}</span>
                        </span>
                      </label>
                    ))}
                    <p className="pt-1 text-sm leading-relaxed text-slate-400">
                      <span className="font-bold text-emerald-300">วิดีโอ mp4 ที่เรนเดอร์ไปแล้วไม่หายทุกกรณี</span> — อยู่คนละที่ใน Export Gallery ·
                      ที่ลบแล้วกู้คืนไม่ได้
                    </p>
                  </div>
                );
              })()}

              {deleteError && (
                <p className="flex items-start gap-1.5 text-sm text-[#E0A9A2]">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />{deleteError}
                </p>
              )}

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setPendingDelete(null)}
                  disabled={deleting}
                  className="h-11 flex-1 cursor-pointer rounded-xl border border-white/[0.1] bg-white/[0.05] text-base font-bold text-slate-200 hover:bg-white/[0.1] disabled:opacity-40"
                >
                  ยกเลิก
                </button>
                <button
                  type="button"
                  onClick={confirmDelete}
                  disabled={deleting}
                  className="flex h-11 flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl bg-rose-600 text-base font-bold text-white hover:bg-rose-500 disabled:opacity-50"
                >
                  {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  {deleting ? 'กำลังลบ...' : 'ลบถาวร'}
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {loading ? (
        <div className="flex-1 flex items-center justify-center p-8 bg-[#07090E]">
          <div className="flex flex-col items-center gap-3 text-slate-300">
            <Loader2 className="w-8 h-8 animate-spin text-[#25F4EE]" />
            <span className="text-sm font-bold">กำลังโหลดข้อมูลไทม์ไลน์...</span>
          </div>
        </div>
      ) : !projectName ? (
        <div className="min-h-0 flex-1">
          <NewClipPanel
            videos={videos}
            productContext={productContext}
            angleIndex={angleIndex}
            onAngleChange={onAngleChange}
            existingProjects={projectList.map((p) => p.project_name || p)}
            projectList={projectList}
            onGoToProductFlow={onGoToProductFlow}
            onVideoUploaded={onVideoUploaded}
            onCreated={handleClipCreated}
          />
        </div>
      ) : (
        <>
          {/* Render failures belong to neither layout tree: this sat inside
              the desktop centre column only, so a failed render on mobile
              reported nothing at all and looked like it had simply stalled.
              Shared placement is also the only version that can't drift
              between the two trees again. */}
          {applyError && (
            <div className="flex flex-shrink-0 items-center gap-2 border-b border-rose-500/30 bg-rose-950/40 px-3 py-1.5 text-sm text-rose-200">
              <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="min-w-0 flex-1">{applyError}</span>
              {(applyError.includes('Cutout') || applyError.includes('Background Cutout')) && (
                <button
                  type="button"
                  onClick={() => {
                    handleApply(true);
                  }}
                  className="flex-shrink-0 rounded-lg bg-rose-500/25 px-2.5 py-1 text-xs font-bold text-rose-100 hover:bg-rose-500/40 border border-rose-400/40 cursor-pointer transition shadow-sm"
                >
                  เรนเดอร์แบบไม่ใช้ Cutout
                </button>
              )}
              <button
                type="button"
                onClick={() => setApplyError(null)}
                className="flex-shrink-0 rounded-lg px-1.5 py-0.5 text-xs font-bold text-rose-300 hover:bg-rose-500/20 hover:text-white cursor-pointer"
              >
                ปิด
              </button>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════
              📱 MOBILE LAYOUT (< md breakpoint) - CapCut Mobile UX
             ══════════════════════════════════════════════════════════ */}
          <div ref={mobileWrapRef} className="lg:hidden flex flex-col flex-1 min-h-0 overflow-hidden bg-[#07090E]">
            {/* Top: 9:16 Video Player Preview (Expands to fill top area, zero wasted space) */}
            <div
              // Grows into whatever the timeline's rows do not need, so no black
              // band sits between the two, and shrinks with the window down to
              // its own floor. `1 0` here starved the timeline instead: a
              // preview height saved on a tall window refused to give any of it
              // back and crushed the tracks to 82px.
              className="relative flex w-full min-h-0 flex-col items-center justify-center bg-black/60 p-2"
              style={{ flex: '1 1 auto', height: mobilePreviewH, minHeight: MOBILE_PREVIEW_MIN_H }}
            >
              {isMobileView && (
                <SequencePlayer
                  channelIdentitySnapshot={channelIdentitySnapshot}
                  channelId={channel?.channelId || 'main'}
                  ref={mobilePlayerRef}
                  clips={clipList}
                  cues={cuesList}
                  overlays={overlays}
                  voiceEdit={activeVoiceEdit}
                  audioUrl={audioUrl}
                  audioStems={audioStems}
                  grade={grade}
                  stylePreset={activeStylePreset}
                  trackMix={trackMix}
                  captionStyle={{
                    captionPosition: style.captionPosition,
                    captionColor: style.captionColor,
                    captionScale: style.captionScale,
                    fontName: style.fontName,
                    // Both of these change what the caption looks like, so the
                    // preview has to be told: without them it drew the English
                    // line whatever the project said, and could not reveal at all.
                    bilingualSubtitles: style.bilingualSubtitles,
                    ghostReveal: style.ghostReveal,
                    hidden: isCaptionHidden,
                  }}
                  isMuted={isAudioMuted}
                  stickerStyle={{
                    badge: style.stickerBadge,
                    position: style.stickerPosition || 'top_right',
                    scale: style.stickerScale || 1.0,
                    startTime: style.stickerStartTime ?? 0.5,
                    endTime: style.stickerEndTime ?? (totalDuration || 999999),
                    normX: style.stickerNormX,
                    normY: style.stickerNormY,
                    stickers: assets.stickers,
                  }}
                  stickers={stickers}
                  effects={effects}
                  spotlight={spotlight}
                  // A view-only mask for the player. It must not be handed to
                  // any control that writes state back: AssetPanel spreads its
                  // backgroundIsolation prop straight into onChange, so giving
                  // it this {enabled: false} copy let the preview-only "hide
                  // cutout" toggle persist that false into the saved project
                  // and the render payload -- the export then came out with
                  // the hook text over the product.
                  backgroundIsolation={previewBackgroundIsolation}
                  subjectPoints={backgroundIsolation?.subject_points ?? []}
                  subjectContours={subjectContours}
                  subjectPickMode={subjectPickMode && subjectPickAllowed}
                  subjectPickLabel={subjectPickLabel}
                  onPickSubjectPoint={handlePickSubjectPoint}
                  backgroundIsolationStatus={backgroundIsolationStatus}
                  onToggleBackgroundIsolation={(nextEnabled) => patchBackgroundIsolation({
                    ...(backgroundIsolation || {}),
                    schema_version: 1,
                    enabled: typeof nextEnabled === 'boolean' ? nextEnabled : !(backgroundIsolation?.enabled === true),
                  })}
                  cutoutPreviewMode={cutoutPreviewMode}
                  onCutoutPreviewModeChange={setCutoutPreviewMode}
                  onSpotlightChange={patchSpotlight}
                  onSpotlightChangeLive={patchSpotlightLive}
                  onBeginDrag={beginDrag}
                  onEndDrag={endDrag}
                  effectAssets={assets.effects}
                  onUpdateEffect={handleUpdateEffect}
                  compact
                  onPlayhead={setPlayhead}
                  onDurations={setDurations}
                  selection={selection}
                  onSelect={handleSelect}
                  onUpdateOverlay={handleUpdateOverlay}
                  onDeleteOverlay={handleDeleteOverlay}
                  onUpdateCaption={patchCaption}
                  applyToAllCaptions={applyToAllCaptions}
                  onUpdateAllCaptions={patchAllCaptions}
                  onStyleChange={patchStyle}
                  onUpdateSticker={handleUpdateSticker}
                  isStickerHidden={isStickerHidden}
                  previewSticker={previewSticker}
                  onDismissPreviewSticker={handleDismissPreviewSticker}
                  previewTextTemplate={previewTextTemplate}
                  onCommitPreviewTextTemplate={handleAddTextTemplate}
                  onDismissPreviewTextTemplate={() => setPreviewTextTemplate(null)}
                  showSafeZone={showSafeZone}
                  onToggleSafeZone={handleToggleSafeZone}
                  showWatermark={style.showWatermark !== false}
                  previewQuality={previewQuality}
                  onPreviewQualityChange={handlePreviewQualityChange}
                  highResStillEnabled={highResStillEnabled}
                  onToggleHighResStill={() => setHighResStillEnabled((v) => !v)}
                />
              )}
              {applying && (
                <div className="absolute bottom-2 left-4 right-4 bg-black/80 backdrop-blur-md p-2 rounded-xl border border-white/[0.1] space-y-1 z-10">
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300" style={{ width: `${Math.max(5, progress)}%` }} />
                  </div>
                  <p className="text-center text-sm text-[#25F4EE] font-bold">{jobStatus?.message || `กำลังเรนเดอร์ ${progress}%`}</p>
                </div>
              )}
              {applyResult && !applying && (
                <div className="absolute bottom-2 left-3 right-3 z-20 flex flex-col gap-1.5 rounded-2xl border border-emerald-500/30 bg-[#0F1420]/95 p-2.5 shadow-2xl backdrop-blur-md animate-fadeIn">
                  <div className="flex items-center justify-between">
                    <p className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                      <span>เรนเดอร์เสร็จสมบูรณ์!</span>
                    </p>
                    <button
                      type="button"
                      onClick={() => setApplyResult(null)}
                      className="text-slate-400 hover:text-white p-1 text-xs"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <MixDegradedNotice result={applyResult} />
                  <div className="flex gap-1.5 pt-0.5">
                    {(applyResult.video_url || applyResult.mp4_video) && (
                      <button
                        type="button"
                        onClick={() => setPreviewModalVideo(applyResult.video_url || toMediaUrl(applyResult.mp4_video))}
                        className="flex-1 flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold transition-all cursor-pointer"
                      >
                        <Play className="h-3 w-3 fill-current" />
                        <span>ดูคลิป</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => openFolder('exports').catch(() => {})}
                      className="flex-1 flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] border border-white/[0.1] text-slate-200 text-xs font-bold transition-all cursor-pointer"
                    >
                      <FolderOpen className="h-3 w-3 text-amber-400" />
                      <span>โฟลเดอร์</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Drag to trade preview height against the panel below;
                double-tap to go back to the default third. */}
            <div
              role="separator"
              aria-orientation="horizontal"
              aria-label="ปรับขนาดพรีวิว"
              title="ลากขึ้น-ลงเพื่อปรับขนาดพรีวิว · แตะสองครั้งเพื่อรีเซ็ต"
              onPointerDown={(e) => {
                mobileResizeRef.current = { startY: e.clientY, startH: mobilePreviewH };
                try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag still works */ }
              }}
              onPointerMove={(e) => {
                const d = mobileResizeRef.current;
                if (!d) return;
                applyMobilePreviewH(d.startH + (e.clientY - d.startY));
              }}
              onPointerUp={(e) => {
                mobileResizeRef.current = null;
                try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
              }}
              onPointerCancel={() => { mobileResizeRef.current = null; }}
              onDoubleClick={() => applyMobilePreviewH(Math.round(window.innerHeight * MOBILE_PREVIEW_DEFAULT))}
              className="group flex h-5 flex-shrink-0 cursor-ns-resize touch-none items-center justify-center border-b border-white/[0.08] bg-[#0B0E17]"
            >
              <span className="h-1 w-12 rounded-full bg-[#4A4742] transition-colors duration-150 group-hover:bg-[#D97757]" />
            </div>

            {/* Mobile Mode Switcher Tabs */}
            <div className="flex-shrink-0 flex items-center justify-around border-b border-white/[0.08] glass-panel p-1">
              {[
                { id: 'timeline', label: 'ไทม์ไลน์', icon: Layers },
                { id: 'assets', label: 'คลังวัตถุดิบ & ซับ', icon: Sparkles },
                { id: 'inspector', label: 'แก้ไขคำบรรยาย', icon: Sliders },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = mobileTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setMobileTab(tab.id)}
                    className={`flex-1 py-2 px-2 min-h-[44px] rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer active:scale-[0.98] ${
                      isActive
                        ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Bottom: Adaptive Workspace Panel */}
            {mobileTab === 'timeline' ? (
              /* TAB 1: TIMELINE, sized to the rows it has to show rather than
                 to a fixed 215px. That height showed three rows and clipped the
                 other four once the audio lanes existed, and left a black void
                 under itself; filling the space instead only moved the void
                 below the tracks. It shrinks when the preview leaves less, and
                 the tracks scroll rather than clip. */
              <div
                className="flex min-h-0 flex-col border-t border-white/[0.08] bg-[#0F1420]"
                style={{ flex: '0 1 auto', height: mobileTimelineH, maxHeight: mobileTimelineH }}
              >
                <Toolbar
                  playhead={playhead}
                  totalDuration={totalDuration}
                  hasClipSelected={!!selectedSeg}
                  hasSelection={!!selection}
                  selectedClip={selectedSeg?.clip}
                  canSplit={!!splitTarget.seg}
                  splitBlockedReason={splitTarget.message}
                  canTrimHead={Boolean(trimHeadTarget.seg)}
                  trimHeadBlockedReason={trimHeadTarget.message}
                  onTrimHead={trimHeadAtPlayhead}
                  canTrimTail={Boolean(trimTailTarget.seg)}
                  trimTailBlockedReason={trimTailTarget.message}
                  onTrimTail={trimTailAtPlayhead}
                  canUndo={canUndo}
                  canRedo={canRedo}
                  onUndo={undo}
                  onRedo={redo}
                  onSplit={splitAtPlayhead}
                  onAddText={addTextAtPlayhead}
                  onDuplicate={duplicateSelected}
                  onCopySettings={copyClipSettings}
                  onPasteSettings={pasteClipSettings}
                  canPasteSettings={hasCopiedClipSettings}
                  selectedCount={selectedClipIds.length}
                  onDelete={deleteSelected}
                  onToggleMirror={() => selectedSeg && patchClip(selectedSeg.clip.id, { mirror: !selectedSeg.clip.mirror })}
                  onCycleSpeed={() => {
                    if (!selectedSeg) return;
                    const order = [0.5, 1, 1.5, 2];
                    const cur = selectedSeg.clip.speed || 1;
                    const next = order[(order.indexOf(cur) + 1) % order.length] || 1;
                    patchClip(selectedSeg.clip.id, { speed: next === 1 ? undefined : next });
                  }}
                  onResetClipTransform={handleResetClipTransform}
                  hasTransformOverride={hasTransformOverride}
                  currentHookTemplate={hookOverlay?.template || DEFAULT_HOOK_TEMPLATE}
                  customHookTemplates={customHookTemplates}
                  onApplyHookTemplate={handleApplyHookTemplate}
                  showSafeZone={showSafeZone}
                  onToggleSafeZone={handleToggleSafeZone}
                  zoomIndex={zoomIndex}
                  zoomCount={ZOOM_PRESETS.length}
                  pxPerSec={pxPerSec}
                  onZoomTo={zoomTo}
                  onZoomToFit={zoomToFit}
                  onZoom={zoomStep}
                  snapEnabled={snapEnabled}
                  onToggleSnap={() => setSnapEnabled((v) => !v)}
                  beatSnapEnabled={beatSnapEnabled}
                  onToggleBeatSnap={() => setBeatSnapEnabled((v) => !v)}
                  beatGridAvailable={hasBeats(beatGrid)}
                  beatBpm={beatGrid?.bpm ?? null}
                  onScanSilences={handleScanSilences}
                  canScanSilences={!!voiceAudioPath && clipList.length > 0}
                  silenceScanning={silenceScanning}
                  previewQuality={previewQuality}
                  onPreviewQualityChange={handlePreviewQualityChange}
                  highResStillEnabled={highResStillEnabled}
                  onToggleHighResStill={() => setHighResStillEnabled((v) => !v)}
                />
                <div className="min-h-0 flex-1">
                  <Timeline
                    segments={segments}
                    backgroundIsolation={backgroundIsolation}
                    cutoutIntervals={scopedCutoutClipIntervals}
                    cutoutArtifactAvailability={cutoutArtifactAvailability}
                    cutoutProcessingClipIds={cutoutBatchState.activeClipIds}
                    cutoutQueuedClipIds={cutoutBatchState.queuedClipIds}
                    isCutoutHidden={isCutoutHidden}
                    onToggleCutout={() => setIsCutoutHidden((v) => !v)}
                    totalDuration={totalDuration}
                    audioDuration={audioDuration}
                    voiceEdit={activeVoiceEdit}
                    cues={cuesList}
                    bgmLabel={bgmLabel}
                    beatGrid={beatSnapEnabled ? beatGrid : null}
                    pxPerSec={pxPerSec}
                    playhead={playhead}
                    selection={selection}
                    onSelect={handleSelect}
                    selectedClipIds={selectedClipIds}
                    onSelectClipWithMode={selectClipWithMode}
                    onCopySettings={copyClipSettings}
                    onPasteSettings={pasteClipSettings}
                    canPasteSettings={hasCopiedClipSettings}
                    onSeek={seekPlayer}
                    onClipChange={patchClip}
                    onCaptionChange={patchCaption}
                    onReorder={reorderClip}
                    onReorderSilent={(id, dir) => reorderClip(id, dir, true)}
                    onDropClip={addClip}
                    audioUrl={audioUrl || voiceUrl}
                    stemUrls={stemUrls}
                    trackMix={trackMix}
                    onTrackMix={handleTrackMix}
                    audioCollapsed={audioCollapsed}
                    onToggleAudioGroup={() => setAudioCollapsed((v) => !v)}
                    dense={isMobileView}
                    isAudioMuted={isAudioMuted}
                    onToggleMuteAudio={() => setIsAudioMuted((v) => !v)}
                    isCaptionHidden={isCaptionHidden}
                    onToggleHideCaption={() => setIsCaptionHidden((v) => !v)}
                    onSplit={splitAtPlayhead}
                    onDuplicate={duplicateSelected}
                    onDelete={deleteSelected}
                    onToggleMirror={() => selectedSeg && patchClip(selectedSeg.clip.id, { mirror: !selectedSeg.clip.mirror })}
                    onAdjustTrim={setTrimAdjustSeg}
                    onBeginDrag={beginDrag}
                    onEndDrag={endDrag}
                    onZoom={zoomStep}
                    onZoomTo={zoomTo}
                    viewportRef={timelineViewportRef}
                    snapCandidates={snapEnabled ? snapCandidates(segments, playhead, [...(audioDuration > 0 ? [audioDuration] : []), ...cueSnapPoints, ...beatSnapPoints]) : []}
                    snapFunction={snapEnabled ? (t, c) => snapTime(t, c, SNAP_PX / pxPerSec) : (t) => t}
                    snapEnabled={snapEnabled}
                    onCuesChange={handleUpdateCuesList}
                    onCaptionRippleShift={handleUpdateCuesList}
                    overlays={overlays}
                    onUpdateOverlay={handleUpdateOverlay}
                    onAddTextOverlay={handleAddTextOverlay}
                    onDropTextTemplate={handleDropTextTemplate}
                    onSelectOverlay={(id, kind) => handleSelect({ type: kind === 'hook' ? 'hook' : 'text_overlay', id })}
                    onToggleOverlayKindHidden={handleToggleOverlayKindHidden}
                    onEnsureHookOverlay={handleEnsureHookOverlay}
                    stickerStyle={{
                      badge: style.stickerBadge,
                      scale: style.stickerScale || 1.0,
                      startTime: style.stickerStartTime ?? 0.5,
                      endTime: style.stickerEndTime ?? (totalDuration || 15.0),
                      normX: style.stickerNormX,
                      normY: style.stickerNormY,
                    }}
                    stickers={stickers}
                    stickerAssets={assets.stickers}
                    isStickerHidden={isStickerHidden}
                    onToggleHideSticker={handleToggleHideSticker}
                    onUpdateSticker={handleUpdateSticker}
                    onSelectSticker={(id) => handleSelect({ type: 'sticker', id })}
                    effects={effects}
                    effectAssets={assets.effects}
                    onSelectEffect={(id) => handleSelect({ type: 'effect', id })}
                    onUpdateEffect={handleUpdateEffect}
                  />
                </div>
              </div>
            ) : (
              /* TAB 2 & 3: ASSETS / INSPECTOR (Scrollable full height) */
              <div className="flex-1 min-h-0 overflow-y-auto">
                {mobileTab === 'assets' && (
                  <div className="h-full">
                    <AssetPanel
                      videos={videos}
                      clipList={clipList}
                      durations={durations}
                      assets={assets}
                      style={style}
                      stylePreset={activeStylePreset}
                      onStylePresetChange={patchStylePreset}
                      stickers={stickers}
                      selectedStickerId={selection?.type === 'sticker' ? selection.id : null}
                      previewSticker={previewSticker}
                      onPreviewSticker={handlePreviewSticker}
                      onAddSticker={(badge, asset) => {
                        handleAddSticker(badge, asset);
                        setPreviewSticker(null);
                      }}
                      onUpdateSticker={handleUpdateSticker}
                      onDeleteSticker={handleDeleteSticker}
                      onClearStickers={handleClearStickers}
                      onSelectSticker={(id) => handleSelect({ type: 'sticker', id })}
                      effects={effects}
                      spotlight={spotlight}
                      backgroundIsolation={backgroundIsolation}
                      backgroundIsolationStatus={backgroundIsolationStatus}
                      cutoutMode={cutoutPreviewMode}
                      onCutoutModeChange={setCutoutPreviewMode}
                      onSpotlightChange={patchSpotlight}
                      onBackgroundIsolationChange={patchBackgroundIsolation}
                      onPrepareBackgroundIsolation={prepareBackgroundIsolation}
                      backgroundIsolationPreparing={backgroundIsolationPreparing}
                      backgroundIsolationPlan={backgroundIsolationPlan}
                      backgroundIsolationProgress={backgroundIsolationProgress}
                      backgroundIsolationError={backgroundIsolationError}
                      onCancelBackgroundIsolation={cancelBackgroundIsolation}
                      subjectPoints={backgroundIsolation?.subject_points ?? []}
                      subjectPickMode={subjectPickMode}
                      subjectPickLabel={subjectPickLabel}
                      onToggleSubjectPick={handleToggleSubjectPick}
                      onSelectPickLabel={setSubjectPickLabel}
                      onClearSubjectPoints={handleClearSubjectPoints}
                      onClearAllBgBlur={handleClearAllBgBlur}
                      onSelectClip={handleSelectClipById}
                      onAddEffect={handleAddEffect}
                      playhead={playhead}
                      totalDuration={totalDuration}
                      selectedCaption={selectedCaption}
                      onAddClip={addClip}
                      onAddTextAtPlayhead={handleAddTextOverlay}
                      onAddTextTemplate={handleAddTextTemplate}
                      onSelectTextTemplate={handleSelectTextTemplate}
                      hookTemplates={HOOK_TEMPLATES}
                      customHookTemplates={customHookTemplates}
                      onDeleteCustomHookTemplate={handleDeleteCustomHookTemplate}
                      activeHookTemplate={hookOverlay?.template || null}
                      hookOverlay={hookOverlay}
                      onApplyHookTemplate={handleApplyHookTemplate}
                      onResetHookTemplate={handleResetHookTemplate}
                      previewTextTemplate={previewTextTemplate}
                      activeTextTemplateId={selection?.type === 'text_overlay' ? overlays.find((o) => o.id === selection.id)?.template_id : null}
                      onStyleChange={patchStyle}
                      onAssignSfx={(sfxId) => selectedCaption && patchCaption(selectedCaption._uid, { sfx: sfxId })}
                      onImportCues={handleImportCues}
                      onVideoUploaded={onVideoUploaded}
                      projectName={projectName}
                    />
                  </div>
                )}

                {mobileTab === 'inspector' && (
                  <div className="h-full">
                    <Inspector
                      selection={selection}
                      multiSelectCount={selectedClipIds.length}
                      onCopySettings={copyClipSettings}
                      onPasteSettings={pasteClipSettings}
                      canPasteSettings={hasCopiedClipSettings}
                      selectedSeg={selectedSeg}
                      selectedCaption={selectedCaption}
                      cuesList={cuesList}
                      playhead={playhead}
                      style={style}
                      totalDuration={totalDuration}
                      audioDuration={audioDuration}
                      assets={assets}
                      hookOverlay={hookOverlay}
                      hookMotionCatalog={hookMotionCatalog}
                      hookMotionDefault={hookMotionDefault}
                      hookTemplates={HOOK_TEMPLATES}
                      customHookTemplates={customHookTemplates}
                      onSaveCustomHookTemplate={handleSaveCustomHookTemplate}
                      onDeleteCustomHookTemplate={handleDeleteCustomHookTemplate}
                      fonts={assets.fonts}
                      onToggleHookHeader={handleEnsureHookOverlay}
                      onAddTextAtPlayhead={addTextAtPlayhead}
                      onStyleChange={patchStyle}
                      onClipChange={(patch, options) => selectedSeg && patchClip(selectedSeg.clip.id, patch, false, options)}
                      clipList={clipList}
                      onPatchAllClips={patchAllClips}
                      onCaptionChange={(cueUid, patch, options) => patchCaption(cueUid, patch, false, options)}
                      applyToAll={applyToAllCaptions}
                      onToggleApplyToAll={setApplyToAllCaptions}
                      onPatchAllCaptions={(patch, options) => patchAllCaptions(patch, false, options)}
                      onSplitCue={handleSplitCue}
                      onSplitCueAtPlayhead={handleSplitCueAtPlayhead}
                      onMergeCue={handleMergeCue}
                      onMergeWithPrevious={handleMergeWithPrevious}
                      onDeleteCue={handleDeleteCue}
                      onInsertCueAfter={handleInsertCueAfter}
                      onReorderCues={handleReorderCues}
                      onBatchFindAndReplace={handleBatchFindAndReplace}
                      onBatchFormatClean={handleBatchFormatClean}
                      onSeek={seekPlayer}
                      onSelectCue={(uid) => handleSelect({ type: 'caption', id: uid })}
                      overlays={overlays}
                      onAddTextOverlay={handleAddTextOverlay}
                      onUpdateOverlay={handleUpdateOverlay}
                      onReplaceOverlay={handleReplaceOverlay}
                      onDeleteOverlay={handleDeleteOverlay}
                      onSelectOverlay={(id, kind) => handleSelect({ type: kind === 'hook' ? 'hook' : 'text_overlay', id })}
                      onSelectHook={() => handleSelect({ type: 'hook' })}
                      onSelect={handleSelect}
                      trackMix={trackMix}
                      onTrackMix={handleTrackMix}
                      onCloseAllCaptionGaps={handleCloseAllCaptionGaps}
                      onResetSubtitleTimings={handleResetSubtitleTimings}
                      stickers={stickers}
                      onUpdateSticker={handleUpdateSticker}
                      onDeleteSticker={handleDeleteSticker}
                      effects={effects}
                      onUpdateEffect={handleUpdateEffect}
                      onDeleteEffect={handleDeleteEffect}
                      backgroundIsolation={backgroundIsolation}
                      backgroundIsolationStatus={backgroundIsolationStatus}
                      onToggleBackgroundIsolation={(nextEnabled) => patchBackgroundIsolation({
                        ...(backgroundIsolation || {}),
                        schema_version: 1,
                        enabled: typeof nextEnabled === 'boolean' ? nextEnabled : !(backgroundIsolation?.enabled === true),
                      })}
                      cutoutPreviewMode={cutoutPreviewMode}
                      onCutoutPreviewModeChange={setCutoutPreviewMode}
                      subjectPoints={backgroundIsolation?.subject_points ?? []}
                      subjectPickMode={subjectPickMode && subjectPickAllowed}
                      onToggleSubjectPickMode={() => setSubjectPickMode((v) => !v)}
                      onClearSubjectPoints={handleClearSubjectPoints}
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ══════════════════════════════════════════════════════════
              🖥️ DESKTOP PRO LAYOUT (>= md breakpoint) - 3 Columns
             ══════════════════════════════════════════════════════════ */}
          <div className={`hidden lg:flex flex-col flex-1 min-h-0 ${activeSplitter ? 'select-none' : ''}`}>
            {/* Middle Row (AssetPanel + Video + Inspector) */}
            <div className="flex min-h-0 flex-1">
              {!zen && (
                leftSidebarCollapsed ? (
                  <div className="flex-shrink-0 flex flex-col items-center border-r border-white/[0.08] bg-[#0A0D14] z-20 py-2 select-none w-10">
                    <button
                      type="button"
                      onClick={toggleLeftSidebar}
                      title="เปิดแถบซ้าย (คลังสื่อ)"
                      className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.06] text-slate-400 hover:bg-[#25F4EE]/20 hover:text-[#25F4EE] border border-white/[0.08] transition-all cursor-pointer shadow-sm"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={toggleLeftSidebar}
                      title="เปิดแถบซ้าย (คลังสื่อ)"
                      className="mt-6 text-[11px] font-medium text-slate-500 hover:text-[#25F4EE] transition-colors py-2 [writing-mode:vertical-rl] tracking-widest uppercase flex items-center gap-1.5 cursor-pointer"
                    >
                      <span>คลังสื่อ</span>
                    </button>
                  </div>
                ) : (
                  <div className="relative flex flex-shrink-0">
                    <div style={{ width: assetW }} className="relative flex-shrink-0 flex flex-col border-r border-white/[0.08] min-w-0">
                      <div className="absolute top-2 right-2 z-20">
                        <button
                          type="button"
                          onClick={toggleLeftSidebar}
                          title="ซ่อนแถบซ้าย"
                          className="flex h-6 w-6 items-center justify-center rounded-lg bg-black/40 text-slate-400 hover:bg-white/[0.1] hover:text-white border border-white/[0.08] transition-all cursor-pointer"
                        >
                          <ChevronLeft className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <AssetPanel
                        videos={videos}
                        clipList={clipList}
                        durations={durations}
                        assets={assets}
                        style={style}
                        stylePreset={activeStylePreset}
                        onStylePresetChange={patchStylePreset}
                        stickers={stickers}
                        selectedStickerId={selection?.type === 'sticker' ? selection.id : null}
                        previewSticker={previewSticker}
                        onPreviewSticker={handlePreviewSticker}
                        onAddSticker={(badge, asset) => {
                          handleAddSticker(badge, asset);
                          setPreviewSticker(null);
                        }}
                        onUpdateSticker={handleUpdateSticker}
                        onDeleteSticker={handleDeleteSticker}
                        onClearStickers={handleClearStickers}
                        onSelectSticker={(id) => handleSelect({ type: 'sticker', id })}
                        effects={effects}
                        spotlight={spotlight}
                        backgroundIsolation={backgroundIsolation}
                        backgroundIsolationStatus={backgroundIsolationStatus}
                        cutoutMode={cutoutPreviewMode}
                        onCutoutModeChange={setCutoutPreviewMode}
                        onSpotlightChange={patchSpotlight}
                        onBackgroundIsolationChange={patchBackgroundIsolation}
                        onPrepareBackgroundIsolation={prepareBackgroundIsolation}
                        backgroundIsolationPreparing={backgroundIsolationPreparing}
                        backgroundIsolationPlan={backgroundIsolationPlan}
                        backgroundIsolationProgress={backgroundIsolationProgress}
                        backgroundIsolationError={backgroundIsolationError}
                        onCancelBackgroundIsolation={cancelBackgroundIsolation}
                        subjectPoints={backgroundIsolation?.subject_points ?? []}
                        subjectPickMode={subjectPickMode}
                        subjectPickLabel={subjectPickLabel}
                        onToggleSubjectPick={handleToggleSubjectPick}
                        onSelectPickLabel={setSubjectPickLabel}
                        onClearSubjectPoints={handleClearSubjectPoints}
                        onClearAllBgBlur={handleClearAllBgBlur}
                        onSelectClip={handleSelectClipById}
                        onAddEffect={handleAddEffect}
                        playhead={playhead}
                        totalDuration={totalDuration}
                        selectedCaption={selectedCaption}
                        onAddClip={addClip}
                        onAddTextAtPlayhead={handleAddTextOverlay}
                        onAddTextTemplate={handleAddTextTemplate}
                        onSelectTextTemplate={handleSelectTextTemplate}
                        hookTemplates={HOOK_TEMPLATES}
                        customHookTemplates={customHookTemplates}
                        onDeleteCustomHookTemplate={handleDeleteCustomHookTemplate}
                        activeHookTemplate={hookOverlay?.template || null}
                        hookOverlay={hookOverlay}
                        onApplyHookTemplate={handleApplyHookTemplate}
                        onResetHookTemplate={handleResetHookTemplate}
                        previewTextTemplate={previewTextTemplate}
                        activeTextTemplateId={selection?.type === 'text_overlay' ? overlays.find((o) => o.id === selection.id)?.template_id : null}
                        onStyleChange={patchStyle}
                        onAssignSfx={(sfxId) => selectedCaption && patchCaption(selectedCaption._uid, { sfx: sfxId })}
                        onImportCues={handleImportCues}
                        onVideoUploaded={onVideoUploaded}
                        projectName={projectName}
                      />
                    </div>
                    {/* Left Resizer with Pro Specular Rim & Pill Handle */}
                    <div
                      role="separator"
                      tabIndex={0}
                      aria-orientation="vertical"
                      aria-label="ปรับความกว้างแผงซ้าย"
                      aria-valuenow={Math.round(assetW)}
                      aria-valuemin={ASSET_MIN_W}
                      aria-valuemax={ASSET_MAX_W}
                      title="ลากซ้าย-ขวาเพื่อปรับความกว้าง · ดับเบิลคลิกเพื่อรีเซ็ต · ลูกศรซ้าย/ขวาเพื่อปรับ"
                      onKeyDown={(e) => {
                        const step = e.shiftKey ? 40 : 10;
                        if (e.key === 'ArrowLeft') { e.preventDefault(); applyAssetW(assetW - step); }
                        else if (e.key === 'ArrowRight') { e.preventDefault(); applyAssetW(assetW + step); }
                        else if (e.key === 'Home') { e.preventDefault(); applyAssetW(ASSET_MIN_W); }
                        else if (e.key === 'End') { e.preventDefault(); applyAssetW(ASSET_MAX_W); }
                      }}
                      onPointerDown={(e) => {
                        assetResizeRef.current = { startX: e.clientX, startW: assetW };
                        setActiveSplitter('asset');
                        try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
                      }}
                      onPointerMove={(e) => {
                        const d = assetResizeRef.current;
                        if (!d) return;
                        applyAssetW(d.startW + (e.clientX - d.startX));
                      }}
                      onPointerUp={(e) => {
                        assetResizeRef.current = null;
                        setActiveSplitter(null);
                        try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
                      }}
                      onPointerCancel={() => {
                        assetResizeRef.current = null;
                        setActiveSplitter(null);
                      }}
                      onDoubleClick={() => applyAssetW(ASSET_DEFAULT_W)}
                      className={`group relative w-2 flex-shrink-0 cursor-col-resize touch-none select-none transition-colors flex items-center justify-center z-20 focus:outline-none focus:ring-1 focus:ring-[#25F4EE] ${
                        activeSplitter === 'asset'
                          ? 'bg-[#25F4EE]/40 ring-1 ring-[#25F4EE]/60'
                          : 'bg-white/[0.04] hover:bg-[#25F4EE]/30'
                      }`}
                    >
                      <span className={`h-8 w-1 rounded-full transition-all duration-150 ${
                        activeSplitter === 'asset' ? 'bg-[#25F4EE] shadow-[0_0_8px_#25F4EE]' : 'bg-white/20 group-hover:bg-[#25F4EE]/80'
                      }`} />
                      {activeSplitter === 'asset' && (
                        <div className="absolute top-1/2 left-4 -translate-y-1/2 px-2 py-0.5 rounded bg-[#0A0D14]/95 border border-[#25F4EE]/40 text-[#25F4EE] text-[10px] font-mono tracking-wider shadow-lg pointer-events-none whitespace-nowrap z-30">
                          {Math.round(assetW)}px
                        </div>
                      )}
                    </div>
                  </div>
                )
              )}

              {/* Center: SequencePlayer */}
              <div className="flex min-h-0 flex-1 flex-col items-center gap-2 overflow-hidden p-3 bg-black/40">
                {!isMobileView && (
                  <SequencePlayer
                  channelIdentitySnapshot={channelIdentitySnapshot}
                  channelId={channel?.channelId || 'main'}
                    ref={desktopPlayerRef}
                    clips={clipList}
                    cues={cuesList}
                    overlays={overlays}
                    voiceEdit={activeVoiceEdit}
                    audioUrl={audioUrl}
                    audioStems={audioStems}
                    grade={grade}
                    stylePreset={activeStylePreset}
                    trackMix={trackMix}
                    captionStyle={{
                      captionPosition: style.captionPosition,
                      captionColor: style.captionColor,
                      captionScale: style.captionScale,
                      fontName: style.fontName,
                      // Both of these change what the caption looks like, so the
                      // preview has to be told: without them it drew the English
                      // line whatever the project said, and could not reveal at all.
                      bilingualSubtitles: style.bilingualSubtitles,
                      ghostReveal: style.ghostReveal,
                      hidden: isCaptionHidden,
                    }}
                    isMuted={isAudioMuted}
                    stickerStyle={{
                      badge: style.stickerBadge,
                      position: style.stickerPosition || 'top_right',
                      scale: style.stickerScale || 1.0,
                      startTime: style.stickerStartTime ?? 0.5,
                      endTime: style.stickerEndTime ?? (totalDuration || 999999),
                      normX: style.stickerNormX,
                      normY: style.stickerNormY,
                      stickers: assets.stickers,
                    }}
                    stickers={stickers}
                    effects={effects}
                    spotlight={spotlight}
                    // View-only mask -- see the note on the desktop tree.
                    backgroundIsolation={previewBackgroundIsolation}
                    subjectPoints={backgroundIsolation?.subject_points ?? []}
                    subjectContours={subjectContours}
                    subjectPickMode={subjectPickMode && subjectPickAllowed}
                    subjectPickLabel={subjectPickLabel}
                    onPickSubjectPoint={handlePickSubjectPoint}
                    backgroundIsolationStatus={backgroundIsolationStatus}
                    onToggleBackgroundIsolation={(nextEnabled) => patchBackgroundIsolation({
                      ...(backgroundIsolation || {}),
                      schema_version: 1,
                      enabled: typeof nextEnabled === 'boolean' ? nextEnabled : !(backgroundIsolation?.enabled === true),
                    })}
                    cutoutPreviewMode={cutoutPreviewMode}
                    onCutoutPreviewModeChange={setCutoutPreviewMode}
                    onSpotlightChange={patchSpotlight}
                    onSpotlightChangeLive={patchSpotlightLive}
                    onBeginDrag={beginDrag}
                    onEndDrag={endDrag}
                    effectAssets={assets.effects}
                    onUpdateEffect={handleUpdateEffect}
                    compact
                    onPlayhead={setPlayhead}
                    onDurations={setDurations}
                    selection={selection}
                    onSelect={handleSelect}
                    onUpdateOverlay={handleUpdateOverlay}
                    onDeleteOverlay={handleDeleteOverlay}
                    onUpdateCaption={patchCaption}
                    applyToAllCaptions={applyToAllCaptions}
                    onUpdateAllCaptions={patchAllCaptions}
                    onStyleChange={patchStyle}
                    onUpdateSticker={handleUpdateSticker}
                    isStickerHidden={isStickerHidden}
                    previewSticker={previewSticker}
                    onDismissPreviewSticker={handleDismissPreviewSticker}
                    previewTextTemplate={previewTextTemplate}
                    onCommitPreviewTextTemplate={handleAddTextTemplate}
                    onDismissPreviewTextTemplate={() => setPreviewTextTemplate(null)}
                    showSafeZone={showSafeZone}
                    onToggleSafeZone={handleToggleSafeZone}
                    showWatermark={style.showWatermark !== false}
                    previewQuality={previewQuality}
                    onPreviewQualityChange={handlePreviewQualityChange}
                    highResStillEnabled={highResStillEnabled}
                    onToggleHighResStill={() => setHighResStillEnabled((v) => !v)}
                  />
                )}
                {applying && (
                  <div className="w-full max-w-[260px] flex-shrink-0">
                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                      <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300" style={{ width: `${Math.max(5, progress)}%` }} />
                    </div>
                    <p className="pt-1 text-center text-sm text-slate-400">{jobStatus?.message}</p>
                  </div>
                )}
                {applyResult && !applying && (
                  <div className="w-full max-w-[340px] flex-shrink-0 space-y-2 rounded-2xl border border-emerald-500/30 bg-[#0F1420]/95 p-3 shadow-2xl backdrop-blur-md animate-fadeIn">
                    <div className="flex items-center justify-between">
                      <p className="flex items-center gap-1.5 text-xs font-bold text-emerald-300">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                        <span>เรนเดอร์เสร็จสมบูรณ์!</span>
                      </p>
                      <button
                        type="button"
                        onClick={() => setApplyResult(null)}
                        className="text-slate-400 hover:text-white p-1 cursor-pointer"
                        title="ปิดการแจ้งเตือน"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <MixDegradedNotice result={applyResult} />
                    <div className="flex gap-2">
                      {(applyResult.video_url || applyResult.mp4_video) && (
                        <button
                          type="button"
                          onClick={() => setPreviewModalVideo(applyResult.video_url || toMediaUrl(applyResult.mp4_video))}
                          className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-xl bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/40 text-[#25F4EE] text-xs font-bold transition-all cursor-pointer"
                        >
                          <Play className="h-3.5 w-3.5 fill-current" />
                          <span>ดูคลิปตัวเต็ม</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => openFolder('exports').catch(() => {})}
                        className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-xl bg-white/[0.08] hover:bg-white/[0.15] border border-white/[0.1] text-slate-200 text-xs font-bold transition-all cursor-pointer"
                      >
                        <FolderOpen className="h-3.5 w-3.5 text-amber-400" />
                        <span>04_Exports</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {!zen && (
                rightSidebarCollapsed ? (
                  <div className="flex-shrink-0 flex flex-col items-center border-l border-white/[0.08] bg-[#0A0D14] z-20 py-2 select-none w-10">
                    <button
                      type="button"
                      onClick={toggleRightSidebar}
                      title="เปิดแถบขวา (แก้ไขคำบรรยาย/ตัวควบคุม)"
                      className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.06] text-slate-400 hover:bg-[#D97757]/20 hover:text-[#D97757] border border-white/[0.08] transition-all cursor-pointer shadow-sm"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={toggleRightSidebar}
                      title="เปิดแถบขวา (แก้ไขคำบรรยาย/ตัวควบคุม)"
                      className="mt-6 text-[11px] font-medium text-slate-500 hover:text-[#D97757] transition-colors py-2 [writing-mode:vertical-rl] tracking-widest uppercase flex items-center gap-1.5 cursor-pointer"
                    >
                      <span>ตัวควบคุม</span>
                    </button>
                  </div>
                ) : (
                  <div className="relative flex flex-shrink-0">
                    {/* Right Resizer with Pro Specular Rim & Pill Handle */}
                    <div
                      role="separator"
                      tabIndex={0}
                      aria-orientation="vertical"
                      aria-label="ปรับความกว้างแผงขวา"
                      aria-valuenow={Math.round(inspectorW)}
                      aria-valuemin={INSPECTOR_MIN_W}
                      aria-valuemax={INSPECTOR_MAX_W}
                      title="ลากซ้าย-ขวาเพื่อปรับความกว้าง · ดับเบิลคลิกเพื่อรีเซ็ต · ลูกศรซ้าย/ขวาเพื่อปรับ"
                      onKeyDown={(e) => {
                        const step = e.shiftKey ? 40 : 10;
                        if (e.key === 'ArrowLeft') { e.preventDefault(); applyInspectorW(inspectorW + step); }
                        else if (e.key === 'ArrowRight') { e.preventDefault(); applyInspectorW(inspectorW - step); }
                        else if (e.key === 'Home') { e.preventDefault(); applyInspectorW(INSPECTOR_MIN_W); }
                        else if (e.key === 'End') { e.preventDefault(); applyInspectorW(INSPECTOR_MAX_W); }
                      }}
                      onPointerDown={(e) => {
                        inspectorResizeRef.current = { startX: e.clientX, startW: inspectorW };
                        setActiveSplitter('inspector');
                        try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag still works */ }
                      }}
                      onPointerMove={(e) => {
                        const d = inspectorResizeRef.current;
                        if (!d) return;
                        // Dragging left (negative dx) widens the panel -- it sits on the right edge of the screen.
                        applyInspectorW(d.startW - (e.clientX - d.startX));
                      }}
                      onPointerUp={(e) => {
                        inspectorResizeRef.current = null;
                        setActiveSplitter(null);
                        try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
                      }}
                      onPointerCancel={() => {
                        inspectorResizeRef.current = null;
                        setActiveSplitter(null);
                      }}
                      onDoubleClick={() => applyInspectorW(INSPECTOR_DEFAULT_W)}
                      className={`group relative w-2 flex-shrink-0 cursor-col-resize touch-none select-none transition-colors flex items-center justify-center z-20 focus:outline-none focus:ring-1 focus:ring-[#D97757] ${
                        activeSplitter === 'inspector'
                          ? 'bg-[#D97757]/40 ring-1 ring-[#D97757]/60'
                          : 'bg-white/[0.04] hover:bg-[#D97757]/30'
                      }`}
                    >
                      <span className={`h-8 w-1 rounded-full transition-all duration-150 ${
                        activeSplitter === 'inspector' ? 'bg-[#D97757] shadow-[0_0_8px_#D97757]' : 'bg-white/20 group-hover:bg-[#D97757]/80'
                      }`} />
                      {activeSplitter === 'inspector' && (
                        <div className="absolute top-1/2 right-4 -translate-y-1/2 px-2 py-0.5 rounded bg-[#0A0D14]/95 border border-[#D97757]/40 text-[#D97757] text-[10px] font-mono tracking-wider shadow-lg pointer-events-none whitespace-nowrap z-30">
                          {Math.round(inspectorW)}px
                        </div>
                      )}
                    </div>
                    <div style={{ width: inspectorW }} className="relative flex-shrink-0 border-l border-white/[0.08] flex flex-col min-w-0">
                      {/* Collapse button for right panel */}
                      <div className="absolute top-2 left-2 z-20">
                        <button
                          type="button"
                          onClick={toggleRightSidebar}
                          title="ซ่อนแถบขวา"
                          className="flex h-6 w-6 items-center justify-center rounded-lg bg-black/40 text-slate-400 hover:bg-white/[0.1] hover:text-white border border-white/[0.08] transition-all cursor-pointer"
                        >
                          <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <Inspector
                        selection={selection}
                        multiSelectCount={selectedClipIds.length}
                        onCopySettings={copyClipSettings}
                        onPasteSettings={pasteClipSettings}
                        canPasteSettings={hasCopiedClipSettings}
                        selectedSeg={selectedSeg}
                        selectedCaption={selectedCaption}
                        cuesList={cuesList}
                        playhead={playhead}
                        style={style}
                        totalDuration={totalDuration}
                        audioDuration={audioDuration}
                        assets={assets}
                        hookOverlay={hookOverlay}
                        hookMotionCatalog={hookMotionCatalog}
                        hookMotionDefault={hookMotionDefault}
                        hookTemplates={HOOK_TEMPLATES}
                        customHookTemplates={customHookTemplates}
                        onSaveCustomHookTemplate={handleSaveCustomHookTemplate}
                        onDeleteCustomHookTemplate={handleDeleteCustomHookTemplate}
                        fonts={assets.fonts}
                        onToggleHookHeader={handleEnsureHookOverlay}
                        onAddTextAtPlayhead={addTextAtPlayhead}
                        onStyleChange={patchStyle}
                        onClipChange={(patch, options) => selectedSeg && patchClip(selectedSeg.clip.id, patch, false, options)}
                        clipList={clipList}
                        onPatchAllClips={patchAllClips}
                        onCaptionChange={(cueUid, patch, options) => patchCaption(cueUid, patch, false, options)}
                        applyToAll={applyToAllCaptions}
                        onToggleApplyToAll={setApplyToAllCaptions}
                        onPatchAllCaptions={(patch, options) => patchAllCaptions(patch, false, options)}
                        onSplitCue={handleSplitCue}
                        onSplitCueAtPlayhead={handleSplitCueAtPlayhead}
                        onMergeCue={handleMergeCue}
                        onMergeWithPrevious={handleMergeWithPrevious}
                        onDeleteCue={handleDeleteCue}
                        onInsertCueAfter={handleInsertCueAfter}
                        onReorderCues={handleReorderCues}
                        onBatchFindAndReplace={handleBatchFindAndReplace}
                        onBatchFormatClean={handleBatchFormatClean}
                        onSeek={seekPlayer}
                        onSelectCue={(uid) => handleSelect({ type: 'caption', id: uid })}
                        overlays={overlays}
                        onAddTextOverlay={handleAddTextOverlay}
                        onUpdateOverlay={handleUpdateOverlay}
                        onReplaceOverlay={handleReplaceOverlay}
                        onDeleteOverlay={handleDeleteOverlay}
                        onSelectOverlay={(id, kind) => handleSelect({ type: kind === 'hook' ? 'hook' : 'text_overlay', id })}
                        onSelectHook={() => handleSelect({ type: 'hook' })}
                        onSelect={handleSelect}
                        trackMix={trackMix}
                        onTrackMix={handleTrackMix}
                        onCloseAllCaptionGaps={handleCloseAllCaptionGaps}
                        onResetSubtitleTimings={handleResetSubtitleTimings}
                        stickers={stickers}
                        onUpdateSticker={handleUpdateSticker}
                        onDeleteSticker={handleDeleteSticker}
                        effects={effects}
                        onUpdateEffect={handleUpdateEffect}
                        onDeleteEffect={handleDeleteEffect}
                        backgroundIsolation={backgroundIsolation}
                        backgroundIsolationStatus={backgroundIsolationStatus}
                        onToggleBackgroundIsolation={(nextEnabled) => patchBackgroundIsolation({
                          ...(backgroundIsolation || {}),
                          schema_version: 1,
                          enabled: typeof nextEnabled === 'boolean' ? nextEnabled : !(backgroundIsolation?.enabled === true),
                        })}
                        cutoutPreviewMode={cutoutPreviewMode}
                        onCutoutPreviewModeChange={setCutoutPreviewMode}
                        subjectPoints={backgroundIsolation?.subject_points ?? []}
                        subjectPickMode={subjectPickMode && subjectPickAllowed}
                        onToggleSubjectPickMode={() => setSubjectPickMode((v) => !v)}
                        onClearSubjectPoints={handleClearSubjectPoints}
                      />
                    </div>
                  </div>
                )
              )}
            </div>

            {/* Bottom Row: Multi-track Timeline */}
            {!zen && (
              <div
                className="flex flex-shrink-0 flex-col border-t border-white/[0.08]"
                style={{ height: timelineH }}
              >
                {/* Timeline Bottom Resizer with Specular Rim & Pill Handle */}
                <div
                  role="separator"
                  tabIndex={0}
                  aria-orientation="horizontal"
                  aria-label="ปรับความสูงไทม์ไลน์"
                  aria-valuenow={Math.round(timelineH)}
                  aria-valuemin={TIMELINE_MIN_H}
                  aria-valuemax={TIMELINE_MAX_H}
                  title="ลากขึ้น-ลงเพื่อปรับความสูงไทม์ไลน์ · ดับเบิลคลิกเพื่อรีเซ็ต · ลูกศรขึ้น/ลงเพื่อปรับ"
                  onKeyDown={(e) => {
                    const step = e.shiftKey ? 30 : 10;
                    if (e.key === 'ArrowUp') { e.preventDefault(); applyTimelineH(timelineH + step); }
                    else if (e.key === 'ArrowDown') { e.preventDefault(); applyTimelineH(timelineH - step); }
                    else if (e.key === 'Home') { e.preventDefault(); applyTimelineH(TIMELINE_MIN_H); }
                    else if (e.key === 'End') { e.preventDefault(); applyTimelineH(TIMELINE_MAX_H); }
                  }}
                  onPointerDown={(e) => {
                    resizeRef.current = { startY: e.clientY, startH: timelineH };
                    setActiveSplitter('timeline');
                    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag */ }
                  }}
                  onPointerMove={(e) => {
                    const d = resizeRef.current;
                    if (!d) return;
                    applyTimelineH(d.startH - (e.clientY - d.startY));
                  }}
                  onPointerUp={(e) => {
                    resizeRef.current = null;
                    setActiveSplitter(null);
                    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* released */ }
                  }}
                  onPointerCancel={() => {
                    resizeRef.current = null;
                    setActiveSplitter(null);
                  }}
                  onDoubleClick={() => applyTimelineH(TIMELINE_DEFAULT_H)}
                  className={`group relative flex h-2.5 flex-shrink-0 cursor-ns-resize touch-none select-none items-center justify-center transition-colors focus:outline-none focus:ring-1 focus:ring-[#25F4EE] z-20 ${
                    activeSplitter === 'timeline'
                      ? 'bg-[#25F4EE]/30'
                      : 'bg-[#0F1420] hover:bg-white/[0.06]'
                  }`}
                >
                  <span className={`h-1 w-12 rounded-full transition-all duration-150 ${
                    activeSplitter === 'timeline' ? 'bg-[#25F4EE] shadow-[0_0_8px_#25F4EE]' : 'bg-slate-600 group-hover:bg-[#25F4EE]/80'
                  }`} />
                  {activeSplitter === 'timeline' && (
                    <div className="absolute left-1/2 -top-6 -translate-x-1/2 px-2 py-0.5 rounded bg-[#0A0D14]/95 border border-[#25F4EE]/40 text-[#25F4EE] text-[10px] font-mono tracking-wider shadow-lg pointer-events-none whitespace-nowrap z-30">
                      {Math.round(timelineH)}px
                    </div>
                  )}
                </div>
                <Toolbar
                  playhead={playhead}
                  totalDuration={totalDuration}
                  hasClipSelected={!!selectedSeg}
                  hasSelection={!!selection}
                  selectedClip={selectedSeg?.clip}
                  canSplit={!!splitTarget.seg}
                  splitBlockedReason={splitTarget.message}
                  canTrimHead={Boolean(trimHeadTarget.seg)}
                  trimHeadBlockedReason={trimHeadTarget.message}
                  onTrimHead={trimHeadAtPlayhead}
                  canTrimTail={Boolean(trimTailTarget.seg)}
                  trimTailBlockedReason={trimTailTarget.message}
                  onTrimTail={trimTailAtPlayhead}
                  canUndo={canUndo}
                  canRedo={canRedo}
                  onUndo={undo}
                  onRedo={redo}
                  onSplit={splitAtPlayhead}
                  onAddText={addTextAtPlayhead}
                  onDuplicate={duplicateSelected}
                  onCopySettings={copyClipSettings}
                  onPasteSettings={pasteClipSettings}
                  canPasteSettings={hasCopiedClipSettings}
                  selectedCount={selectedClipIds.length}
                  onDelete={deleteSelected}
                  onToggleMirror={() => selectedSeg && patchClip(selectedSeg.clip.id, { mirror: !selectedSeg.clip.mirror })}
                  onCycleSpeed={() => {
                    if (!selectedSeg) return;
                    const order = [0.5, 1, 1.5, 2];
                    const cur = selectedSeg.clip.speed || 1;
                    const next = order[(order.indexOf(cur) + 1) % order.length] || 1;
                    patchClip(selectedSeg.clip.id, { speed: next === 1 ? undefined : next });
                  }}
                  onResetClipTransform={handleResetClipTransform}
                  hasTransformOverride={hasTransformOverride}
                  currentHookTemplate={hookOverlay?.template || DEFAULT_HOOK_TEMPLATE}
                  customHookTemplates={customHookTemplates}
                  onApplyHookTemplate={handleApplyHookTemplate}
                  showSafeZone={showSafeZone}
                  onToggleSafeZone={handleToggleSafeZone}
                  zoomIndex={zoomIndex}
                  zoomCount={ZOOM_PRESETS.length}
                  pxPerSec={pxPerSec}
                  onZoomTo={zoomTo}
                  onZoomToFit={zoomToFit}
                  onZoom={zoomStep}
                  snapEnabled={snapEnabled}
                  onToggleSnap={() => setSnapEnabled((v) => !v)}
                  beatSnapEnabled={beatSnapEnabled}
                  onToggleBeatSnap={() => setBeatSnapEnabled((v) => !v)}
                  beatGridAvailable={hasBeats(beatGrid)}
                  beatBpm={beatGrid?.bpm ?? null}
                  onScanSilences={handleScanSilences}
                  canScanSilences={!!voiceAudioPath && clipList.length > 0}
                  silenceScanning={silenceScanning}
                  previewQuality={previewQuality}
                  onPreviewQualityChange={handlePreviewQualityChange}
                  highResStillEnabled={highResStillEnabled}
                  onToggleHighResStill={() => setHighResStillEnabled((v) => !v)}
                />
                <div className="min-h-0 flex-1">
                  <Timeline
                    segments={segments}
                    backgroundIsolation={backgroundIsolation}
                    cutoutIntervals={scopedCutoutClipIntervals}
                    cutoutArtifactAvailability={cutoutArtifactAvailability}
                    cutoutProcessingClipIds={cutoutBatchState.activeClipIds}
                    cutoutQueuedClipIds={cutoutBatchState.queuedClipIds}
                    totalDuration={totalDuration}
                    audioDuration={audioDuration}
                    voiceEdit={activeVoiceEdit}
                    cues={cuesList}
                    bgmLabel={bgmLabel}
                    beatGrid={beatSnapEnabled ? beatGrid : null}
                    pxPerSec={pxPerSec}
                    playhead={playhead}
                    selection={selection}
                    onSelect={handleSelect}
                    selectedClipIds={selectedClipIds}
                    onSelectClipWithMode={selectClipWithMode}
                    onCopySettings={copyClipSettings}
                    onPasteSettings={pasteClipSettings}
                    canPasteSettings={hasCopiedClipSettings}
                    onSeek={seekPlayer}
                    onClipChange={patchClip}
                    onCaptionChange={patchCaption}
                    onReorder={reorderClip}
                    onReorderSilent={(id, dir) => reorderClip(id, dir, true)}
                    onDropClip={addClip}
                    audioUrl={audioUrl || voiceUrl}
                    stemUrls={stemUrls}
                    trackMix={trackMix}
                    onTrackMix={handleTrackMix}
                    audioCollapsed={audioCollapsed}
                    onToggleAudioGroup={() => setAudioCollapsed((v) => !v)}
                    dense={isMobileView}
                    isAudioMuted={isAudioMuted}
                    onToggleMuteAudio={() => setIsAudioMuted((v) => !v)}
                    isCaptionHidden={isCaptionHidden}
                    onToggleHideCaption={() => setIsCaptionHidden((v) => !v)}
                    isCutoutHidden={isCutoutHidden}
                    onToggleCutout={() => setIsCutoutHidden((v) => !v)}
                    onSplit={splitAtPlayhead}
                    onDuplicate={duplicateSelected}
                    onDelete={deleteSelected}
                    onToggleMirror={() => selectedSeg && patchClip(selectedSeg.clip.id, { mirror: !selectedSeg.clip.mirror })}
                    onAdjustTrim={setTrimAdjustSeg}
                    onBeginDrag={beginDrag}
                    onEndDrag={endDrag}
                    onZoom={zoomStep}
                    onZoomTo={zoomTo}
                    viewportRef={timelineViewportRef}
                    snapCandidates={snapEnabled ? snapCandidates(segments, playhead, [...(audioDuration > 0 ? [audioDuration] : []), ...cueSnapPoints, ...beatSnapPoints]) : []}
                    snapFunction={snapEnabled ? (t, c) => snapTime(t, c, SNAP_PX / pxPerSec) : (t) => t}
                    snapEnabled={snapEnabled}
                    onCuesChange={handleUpdateCuesList}
                    onCaptionRippleShift={handleUpdateCuesList}
                    overlays={overlays}
                    onUpdateOverlay={handleUpdateOverlay}
                    onAddTextOverlay={handleAddTextOverlay}
                    onDropTextTemplate={handleDropTextTemplate}
                    onSelectOverlay={(id, kind) => handleSelect({ type: kind === 'hook' ? 'hook' : 'text_overlay', id })}
                    onToggleOverlayKindHidden={handleToggleOverlayKindHidden}
                    onEnsureHookOverlay={handleEnsureHookOverlay}
                    stickerStyle={{
                      badge: style.stickerBadge,
                      scale: style.stickerScale || 1.0,
                      startTime: style.stickerStartTime ?? 0.5,
                      endTime: style.stickerEndTime ?? (totalDuration || 15.0),
                      normX: style.stickerNormX,
                      normY: style.stickerNormY,
                    }}
                    stickers={stickers}
                    stickerAssets={assets.stickers}
                    isStickerHidden={isStickerHidden}
                    onToggleHideSticker={handleToggleHideSticker}
                    onUpdateSticker={handleUpdateSticker}
                    onSelectSticker={(id) => handleSelect({ type: 'sticker', id })}
                    effects={effects}
                    effectAssets={assets.effects}
                    onSelectEffect={(id) => handleSelect({ type: 'effect', id })}
                    onUpdateEffect={handleUpdateEffect}
                  />
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════
          🎬 FULL RENDERED VIDEO PREVIEW MODAL
         ══════════════════════════════════════════════════════════ */}
      {previewModalVideo && (
        <div
          className="fixed inset-0 z-[120] flex items-center justify-center bg-black/90 backdrop-blur-md p-4 animate-fadeIn"
          onClick={() => setPreviewModalVideo(null)}
        >
          <div
            className="relative max-w-sm w-full bg-[#0F1420] border border-white/[0.14] rounded-3xl p-4 shadow-2xl flex flex-col items-center gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between w-full">
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Film className="w-4 h-4 text-[#25F4EE]" />
                <span>พรีวิววิดีโอผลงานจริง (9:16)</span>
              </h3>
              <button
                type="button"
                onClick={() => setPreviewModalVideo(null)}
                className="p-1.5 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="w-full aspect-[9/16] bg-black rounded-2xl overflow-hidden border border-white/[0.08] relative">
              <video
                src={previewModalVideo}
                controls
                autoPlay
                playsInline
                className="w-full h-full object-contain"
              />
            </div>
            <div className="flex w-full gap-2 pt-1">
              <button
                type="button"
                onClick={() => openFolder('exports').catch(() => {})}
                className="flex-1 py-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-xs font-bold text-slate-200 flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                <span>เปิดโฟลเดอร์ 04_Exports</span>
              </button>
              <button
                type="button"
                onClick={() => setPreviewModalVideo(null)}
                className="flex-1 py-2 rounded-xl bg-[#D97757] hover:bg-[#C2683D] text-xs font-bold text-white transition-colors cursor-pointer"
              >
                ปิดหน้าต่าง
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Feedback Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] pointer-events-none animate-in fade-in slide-in-from-bottom-3 duration-200">
          <div className="px-4 py-2 rounded-xl bg-[#1E1D1A]/95 border border-[#D97757]/60 text-white text-xs font-semibold shadow-2xl backdrop-blur-md flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[#25F4EE] animate-pulse" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      <TrimAdjustModal
        isOpen={!!trimAdjustSeg}
        onClose={() => setTrimAdjustSeg(null)}
        clip={trimAdjustSeg?.clip}
        onConfirm={(clipId, patch) => patchClip(clipId, patch)}
      />

      {/* Opened from the header's "ปก" button (openCoverStudioManually). */}
      <CoverStudioModal
        isOpen={!!coverGateItem}
        onClose={() => setCoverGateItem(null)}
        videoItem={coverGateItem}
        onCoverSaved={handleCoverGateSaved}
      />
    </div>
  );
}
