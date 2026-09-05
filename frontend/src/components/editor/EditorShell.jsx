import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, AlertTriangle, CheckCircle2, Loader2, Maximize2, Minimize2,
  RefreshCw, Rocket, Scissors, Film, Layers, Sliders, Sparkles, Trash2,
  FolderOpen, Play, Copy, Check, X, Save,
  ChevronLeft, ChevronRight, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, Columns3,
} from 'lucide-react';
import {
  deleteProject, getAllAssets, getHookMotionPresets, getProject, getProjectOrigin, getProjects, getRenderStatus, startReroll, updateProjectCues, updateProjectClips, updateProjectState, openFolder, updateAngleStatus,
} from '../../api';
import {
  FADE_DURATION, ZOOM_LEVELS, buildSegments, formatTimecode, splitClipAt, snapCandidates, snapTime,
  totalDuration as totalDurationOf,
} from '../../lib/timelineMath';
import { useEditorHistory } from '../../hooks/useEditorHistory';
import { useProjectAutosave } from '../../hooks/useProjectAutosave';
import { useProjectLoader } from '../../hooks/useProjectLoader';
import { useRenderJob } from '../../hooks/useRenderJob';
import { toMediaUrl } from '../../lib/mediaUrl';
import { editorStateToSavePayload, manifestToEditorState } from '../../lib/editorProjectState';
import SequencePlayer from '../SequencePlayer';
import AssetPanel from './AssetPanel';
import Inspector from './Inspector';
import Timeline, { tracksFitHeight } from './Timeline';
import { DEFAULT_HOOK_TEMPLATE, HOOK_TEMPLATES } from '../../lib/hookStyles';
import {
  guessBrandModel,
  newHookOverlay,
  newTextOverlay,
  overlayFromTextTemplate,
  overriddenTierFields,
  restyleOverlayFromTemplate,
  resolveLook,
  templateForAdTone,
  withHookTemplate,
  withHookTemplateReset,
  withTierLook,
  withTierText,
} from '../../lib/overlayModel';
import Toolbar from './Toolbar';
import NewClipPanel from './NewClipPanel';
import { ActivityIndicatorButton } from '../ActivityCenter';
import { useTaskManager } from '../../context/TaskContext';
import HeaderMenu from './HeaderMenu';
import RenderButton from './RenderButton';

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

const framesFor = (seconds) => Math.max(6, Math.min(40, Math.round((seconds || 12) / 3)));
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
const MOBILE_PREVIEW_MIN_H = 160;
const MOBILE_PREVIEW_DEFAULT = 0.45;   // share of the window height
const TIMELINE_MAX_H = 560;
// Where the editor switches between its mobile and desktop layout trees.
// Tailwind `lg` (1024px): below it the desktop tree's own default panel
// widths (250 asset + 380 inspector + gutters = ~668px) leave under 100px
// for the preview, which is not a usable editor.
const LAYOUT_BREAKPOINT = 1024;
// The stems the preview mixes, in the order the timeline lanes show them.
const AUDIO_TRACKS = ['voice', 'bgm', 'sfx', 'clip'];
// The Toolbar row inside the phone's timeline tab.
const MOBILE_TOOLBAR_H = 44;
// The timeline/assets/inspector tab strip above it.
const MOBILE_TAB_ROW_H = 48;
const ASSET_MIN_W = 180;
const ASSET_MAX_W = 480;
const ASSET_DEFAULT_W = 250;
const INSPECTOR_MIN_W = 280;
const INSPECTOR_MAX_W = 680;
const INSPECTOR_DEFAULT_W = 380;

// Mirrors asset_registry.py's LEGACY_SFX_ALIASES: an old manifest's cue can
// still say "whoosh" where the registry id is "sfx_whoosh_fast".
const LEGACY_SFX_ALIASES = {
  whoosh: 'sfx_whoosh_fast',
  pop: 'sfx_pop_bubble',
  ding: 'sfx_bell_ding',
  cash: 'sfx_cash_register',
  boom: 'sfx_vine_boom',
};

const EMPTY = { clipList: [], cuesList: [], overlays: [], style: { fontName: 'IBMPlex', bgmName: null, lutName: null, lutIntensity: 1, stickerBadge: null, bgmVolume: 0.12, bgmDucking: false, captionPosition: 'bottom', captionColor: '#FFFFFF', captionScale: 1, stickerPosition: 'top_right', stickerScale: 1 } };

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
}) {
  const { state, set, setSilent, beginDrag, endDrag, undo, redo, reset, canUndo, canRedo } = useEditorHistory(EMPTY);
  const { clipList, cuesList, style, overlays } = state;

  const [projectList, setProjectList] = useState([]);
  const [projectName, setProjectName] = useState('');
  // `default_bgm` comes from the server, which is where the render's own
  // default lives. Keeping a copy here is what let the timeline claim one
  // track while the file played another.
  const [assets, setAssets] = useState({ sfx: [], music: [], fonts: [], stickers: [], luts: [], default_bgm: null });
  const { pollTasks } = useTaskManager();

  const [durations, setDurations] = useState({});
  const [audioDuration, setAudioDuration] = useState(0);
  const [selection, setSelection] = useState(null);
  const [playhead, setPlayhead] = useState(0);
  const [zoomIndex, setZoomIndex] = useState(2);
  const [snapEnabled, setSnapEnabled] = useState(true);
  const [applyToAllCaptions, setApplyToAllCaptions] = useState(true);

  // Mobile Mode Switcher: 'timeline' | 'assets' | 'inspector'
  const [mobileTab, setMobileTab] = useState('timeline');

  // Desktop timeline height resizer
  const [timelineH, setTimelineH] = useState(() => {
    try {
      const saved = Number(localStorage.getItem('capcut_timeline_h'));
      return saved >= TIMELINE_MIN_H && saved <= TIMELINE_MAX_H ? saved : TIMELINE_DEFAULT_H;
    } catch (err) {
      return TIMELINE_DEFAULT_H;
    }
  });
  const resizeRef = useRef(null);

  // Desktop left asset-panel width resizer & collapse
  const [assetW, setAssetW] = useState(() => {
    try {
      const saved = Number(localStorage.getItem('editor.assetW'));
      return saved >= ASSET_MIN_W && saved <= ASSET_MAX_W ? saved : ASSET_DEFAULT_W;
    } catch (err) {
      return ASSET_DEFAULT_W;
    }
  });
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('editor.leftSidebarCollapsed') === 'true';
    } catch (err) {
      return false;
    }
  });
  const assetResizeRef = useRef(null);
  const applyAssetW = (nextW) => {
    const clamped = Math.max(ASSET_MIN_W, Math.min(ASSET_MAX_W, nextW));
    setAssetW(clamped);
    try { localStorage.setItem('editor.assetW', String(clamped)); } catch (err) {}
  };
  const toggleLeftSidebar = () => {
    setLeftSidebarCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem('editor.leftSidebarCollapsed', String(next)); } catch (err) {}
      return next;
    });
  };

  // Desktop inspector-panel width resizer & collapse
  const [inspectorW, setInspectorW] = useState(() => {
    try {
      const saved = Number(localStorage.getItem('editor.inspectorW'));
      return saved >= INSPECTOR_MIN_W && saved <= INSPECTOR_MAX_W ? saved : INSPECTOR_DEFAULT_W;
    } catch (err) {
      return INSPECTOR_DEFAULT_W;
    }
  });
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('editor.rightSidebarCollapsed') === 'true';
    } catch (err) {
      return false;
    }
  });
  const inspectorResizeRef = useRef(null);
  const applyInspectorW = (nextW) => {
    const clamped = Math.max(INSPECTOR_MIN_W, Math.min(INSPECTOR_MAX_W, nextW));
    setInspectorW(clamped);
    try { localStorage.setItem('editor.inspectorW', String(clamped)); } catch (err) { /* private mode */ }
  };
  const toggleRightSidebar = () => {
    setRightSidebarCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem('editor.rightSidebarCollapsed', String(next)); } catch (err) {}
      return next;
    });
  };

  // Mobile split. The preview used to be locked to 28vh on every tab except
  // the timeline, which is why editing captions left the clip as a thumbnail.
  const mobileWrapRef = useRef(null);
  const mobileResizeRef = useRef(null);
  const [mobilePreviewH, setMobilePreviewH] = useState(() => {
    // Range-checked and try/caught like the other three panel sizes below.
    // Without either, a stale or hand-edited value went straight into
    // style.height (a negative one collapsed the preview outright), and a
    // localStorage that throws (private mode, blocked site data) took the
    // whole initializer down with it.
    const fallback = Math.round(window.innerHeight * MOBILE_PREVIEW_DEFAULT);
    try {
      const saved = parseInt(localStorage.getItem('editor.mobilePreviewH') || '', 10);
      if (!Number.isFinite(saved)) return fallback;
      return Math.max(MOBILE_PREVIEW_MIN_H, Math.min(saved, Math.round(window.innerHeight * 0.9)));
    } catch (err) {
      return fallback;
    }
  });

  const applyMobilePreviewH = (px) => {
    const box = mobileWrapRef.current?.getBoundingClientRect();
    // Leave room for the tab row and the timeline's own rows. This was a flat
    // 220px, sized for a timeline that no longer has a fixed height.
    const reserve = MOBILE_TAB_ROW_H + (Number.isFinite(mobileTimelineH) ? mobileTimelineH : 0);
    const max = box ? Math.max(MOBILE_PREVIEW_MIN_H, box.height - reserve) : 640;
    const clamped = Math.min(max, Math.max(MOBILE_PREVIEW_MIN_H, Math.round(px)));
    setMobilePreviewH(clamped);
    try { localStorage.setItem('editor.mobilePreviewH', String(clamped)); } catch (err) { /* private mode */ }
  };

  const resetPanelSizes = () => {
    setTimelineH(TIMELINE_DEFAULT_H);
    setAssetW(ASSET_DEFAULT_W);
    setInspectorW(INSPECTOR_DEFAULT_W);
    setMobilePreviewH(Math.round(window.innerHeight * MOBILE_PREVIEW_DEFAULT));
    setLeftSidebarCollapsed(false);
    setRightSidebarCollapsed(false);
    for (const key of ['capcut_timeline_h', 'editor.assetW', 'editor.inspectorW',
                       'editor.mobilePreviewH', 'editor.leftSidebarCollapsed',
                       'editor.rightSidebarCollapsed']) {
      try { localStorage.removeItem(key); } catch (err) { /* private mode */ }
    }
  };

  const applyTimelineH = (nextH) => {
    const clamped = Math.max(TIMELINE_MIN_H, Math.min(TIMELINE_MAX_H, nextH));
    setTimelineH(clamped);
    try { localStorage.setItem('capcut_timeline_h', String(clamped)); } catch (err) { /* ignore */ }
  };

  const [zen, setZen] = useState(false);
  const [confirmGap, setConfirmGap] = useState(0);

  const handleRenderComplete = useCallback((rawResult, _id, targetProject) => {
    if (productContext?.id && productContext?.angles?.[angleIndex]?.angle_id) {
      try {
        const vPath = rawResult?.mp4 || rawResult?.final_video_path || rawResult?.video_path || '';
        updateAngleStatus(productContext.id, productContext.angles[angleIndex].angle_id, 'rendered', vPath, targetProject).catch(() => {});
      } catch (e) {}
    }
  }, [productContext, angleIndex]);

  const handleRenderError = useCallback((_errorMsg, _id, _targetProject) => {
    if (productContext?.id && productContext?.angles?.[angleIndex]?.angle_id) {
      try {
        updateAngleStatus(productContext.id, productContext.angles[angleIndex].angle_id, 'scripted').catch(() => {});
      } catch (e) {}
    }
  }, [productContext, angleIndex]);

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
  // Draft = 720p/crf26/veryfast. Measured on this machine: a 12s clip took
  // 25.5s at post quality vs 12.5s as a draft (12.18 MB vs 1.82 MB).
  const [exportPreset, setExportPreset] = useState('post');
  const [previewModalVideo, setPreviewModalVideo] = useState(null);
  const [copiedPath, setCopiedPath] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [voiceUrl, setVoiceUrl] = useState(null);
  // Read off the manifest so the banner can dress itself the way the script's
  // own narration tone asks for, and name the product without being told.
  const [projectAdTone, setProjectAdTone] = useState(null);
  const [projectProductName, setProjectProductName] = useState('');
  const [hookMotionCatalog, setHookMotionCatalog] = useState(null);
  const [hookMotionDefault, setHookMotionDefault] = useState(null);
  const [microCuesList, setMicroCuesList] = useState([]);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [deleteScope, setDeleteScope] = useState('project');
  const [deleteOrigin, setDeleteOrigin] = useState(null);
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  // Phones start with the audio group folded: four stem lanes are a desk-sized
  // amount of detail, and the gutter has no room for their names next to the
  // mute/solo chips. One tap opens them.
  const [audioCollapsed, setAudioCollapsed] = useState(
    () => (typeof window !== 'undefined' ? window.innerWidth < LAYOUT_BREAKPOINT : false)
  );
  // Per-stem mute/solo for the preview. Playback-only -- it never reaches a
  // render payload, so soloing the BGM to check a level cannot change output.
  const [trackMix, setTrackMix] = useState({ mute: {}, solo: {} });
  const handleTrackMix = useCallback((track, kind) => {
    setTrackMix((prev) => {
      const next = { mute: { ...prev.mute }, solo: { ...prev.solo } };
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
      return next;
    });
  }, []);
  const [isCaptionHidden, setIsCaptionHidden] = useState(false);

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

  const handleUpdateOverlay = useCallback((id, patch) => {
    set((s) => ({
      ...s,
      overlays: s.overlays.map((o) => (o.id === id ? { ...o, ...patch } : o)),
    }));
    markOverlaysDirty();
  }, [set, markOverlaysDirty]);

  /** Replace one overlay wholesale, for the withX helpers in overlayModel. */
  const handleReplaceOverlay = useCallback((id, next) => {
    set((s) => ({ ...s, overlays: s.overlays.map((o) => (o.id === id ? next : o)) }));
    markOverlaysDirty();
  }, [set, markOverlaysDirty]);

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
        brand: guess.brand, model: guess.model, template, duration: 3.0,
      });
      if (fresh) handleAddOverlay(fresh);
      return;
    }
    handleReplaceOverlay(hookOverlay.id, withHookTemplate(hookOverlay, template));
    setSelection({ type: 'hook', id: hookOverlay.id });
  }, [hookOverlay, handleAddOverlay, handleReplaceOverlay, projectProductName, productContext]);

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
      template: templateForAdTone(projectAdTone),
      duration: 3.0,
    });
    if (fresh) handleAddOverlay(fresh);
  }, [hookOverlay, handleUpdateOverlay, handleAddOverlay, productContext,
      projectProductName, projectAdTone]);

  const [previewTextTemplate, setPreviewTextTemplate] = useState(null);


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

  const cuesDirty = useRef(false);
  const initialCuesRef = useRef([]);
  const isLoadedRef = useRef(false);

  // Music lives in the mix, not the video pass. Apply has to ask for the
  // "bgm" re-roll when any of it changed, or the render happily reuses the
  // old mixed_audio.wav and the new track is silently ignored.
  const loadedAudioStyle = useRef({ bgmName: null, bgmVolume: 0.12, bgmDucking: false });
  // Caption look is baked into the .ass, which the "video" part reuses -- so a
  // caption style change has to ask for the subtitles part instead.
  const loadedCaptionStyle = useRef({ captionPosition: 'bottom', captionColor: '#FFFFFF', captionScale: 1 });

  const savePayload = useMemo(() => editorStateToSavePayload({
    clipList,
    cuesList,
    style,
    overlays,
    trackMix,
  }), [clipList, cuesList, overlays, style, trackMix]);
  const {
    saveStatus,
    setSaveStatus,
    flush: flushAutosave,
    saveNow: handleManualSave,
    setBaseline: setSaveBaseline,
  } = useProjectAutosave({
    projectName,
    payload: savePayload,
    enabled: !!projectName && isLoadedRef.current,
    saveProject: updateProjectState,
  });

  const mapProject = useCallback((manifest) => manifestToEditorState(manifest, {
    createClipId: () => newId(),
    createCueId: (index) => `cue-${index}-${Date.now().toString(36)}`,
  }), []);

  const applyLoadedProject = useCallback((name, loaded) => {
    setProjectName(name);
    initialCuesRef.current = JSON.parse(JSON.stringify(loaded.cuesList || []));
    setMicroCuesList(loaded.microCuesList);
    setProjectAdTone(loaded.adTone);
    setProjectProductName(loaded.productName);
    setAudioUrl(loaded.mixedAudioPath ? toMediaUrl(loaded.mixedAudioPath) : null);
    setVoiceUrl(loaded.voiceAudioPath ? toMediaUrl(loaded.voiceAudioPath) : null);
    setTrackMix(loaded.trackMix);
    loadedCaptionStyle.current = {
      captionPosition: loaded.style.captionPosition,
      captionColor: loaded.style.captionColor,
      captionScale: loaded.style.captionScale,
    };
    loadedAudioStyle.current = {
      bgmName: loaded.style.bgmName,
      bgmVolume: loaded.style.bgmVolume,
      bgmDucking: loaded.style.bgmDucking,
    };
    reset({
      clipList: loaded.clipList,
      cuesList: loaded.cuesList,
      overlays: loaded.overlays,
      style: loaded.style,
    });
    setAudioDuration(loaded.audioDuration);
    cuesDirty.current = false;
    setSaveBaseline(name, editorStateToSavePayload(loaded));
    isLoadedRef.current = true;
  }, [reset, setSaveBaseline]);

  const {
    loadProject,
    loading,
    loadError,
    setLoadError,
  } = useProjectLoader({
    fetchProject: getProject,
    beforeLoad: async () => {
      if (projectName && isLoadedRef.current) await flushAutosave();
    },
    mapProject,
    onStart: () => {
      isLoadedRef.current = false;
      setSelection(null);
      setApplyError(null);
      setApplyResult(null);
      setConfirmGap(0);
    },
    onLoaded: applyLoadedProject,
  });

  const seekPlayer = useCallback((t) => {
    setPlayhead(t);
    if (isMobileView) {
      mobilePlayerRef.current?.seek(t);
    } else {
      desktopPlayerRef.current?.seek(t);
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
      if (projectName === pendingDelete) {
        setProjectName('');
        setSelection(null);
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
      updateAngleStatus(productContext.id, curAngle.angle_id, 'in_production', null, newProjectName).catch(() => {});
    }
    getProjects()
      .then((data) => setProjectList(data?.projects || []))
      .catch(() => {})
      .finally(() => loadProject(newProjectName));
  }, [productContext?.id, productContext?.angles, angleIndex]);

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
  }, []);

  // Load project handed down from script lab or flow
  useEffect(() => {
    if (initialProjectName) {
      loadProject(initialProjectName);
    } else if (!projectName) {
      const angleProj = productContext?.angles?.[angleIndex]?.project_name;
      if (angleProj) {
        loadProject(angleProj);
      }
    }
  }, [initialProjectName, productContext, angleIndex]);

  // Filmstrip thumbnails
  const filmstrips = useMemo(() => {
    const map = {};
    clipList.forEach((c) => {
      if (!c.source_path || map[c.source_path]) return;
      const count = framesFor(durations[c.source_path] || 12);
      map[c.source_path] = Array.from(
        { length: count },
        (_, i) => `/api/media/${c.source_path}?thumb=1&idx=${i}&count=${count}`
      );
    });
    return map;
  }, [clipList, durations]);

  const segments = useMemo(() => buildSegments(clipList, durations), [clipList, durations]);
  const totalDuration = useMemo(() => totalDurationOf(segments), [segments]);
  const pxPerSec = ZOOM_LEVELS[zoomIndex];

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

  // Timeline content is `duration * pxPerSec + 240` wide (see Timeline.jsx),
  // so at the default 50 px/s it outruns a 1440px viewport from about the
  // twelfth 2-second clip and every session starts with manual scrolling.
  // Picks the largest zoom step whose content still fits the track, so
  // "fit" never lands on a level that scrolls anyway.
  const timelineViewportRef = useRef(null);
  const zoomToFit = useCallback(() => {
    // Falls back to the window when no visible timeline has claimed the ref
    // yet (see the visibility guard in Timeline.jsx), so the button still
    // does something sensible rather than nothing.
    const width = timelineViewportRef.current?.clientWidth || window.innerWidth;
    if (!width || !totalDuration) return;
    const usable = Math.max(120, width - 240 - 92); // ruler gutter + trailing pad
    const wanted = usable / totalDuration;
    let best = 0;
    for (let i = 0; i < ZOOM_LEVELS.length; i++) {
      if (ZOOM_LEVELS[i] <= wanted) best = i;
    }
    setZoomIndex(best);
  }, [totalDuration]);

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

  // Clip / Caption mutation helpers
  const patchClip = useCallback((id, patch, silent = false) => {
    // silent = mid-gesture: no undo step of its own, the drag pushes one
    (silent ? setSilent : set)((prev) => ({
      ...prev,
      clipList: prev.clipList.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    }));
  }, [set, setSilent]);

  const reorderClip = useCallback((id, direction, silent = false) => {
    (silent ? setSilent : set)((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === id);
      const target = idx + direction;
      if (idx === -1 || target < 0 || target >= prev.clipList.length) return prev;
      const next = [...prev.clipList];
      [next[idx], next[target]] = [next[target], next[idx]];
      return { ...prev, clipList: next };
    });
  }, [set, setSilent]);

  const patchCaption = useCallback((uid, patch, silent = false) => {
    cuesDirty.current = true;
    (silent ? setSilent : set)((prev) => {
      const nextList = prev.cuesList.map((c) => ((c._uid === uid || c.id === uid) ? { ...c, ...patch } : c));
      const sorted = (!silent && ('start' in patch || 'end' in patch))
        ? [...nextList].sort((a, b) => a.start - b.start)
        : nextList;
      return { ...prev, cuesList: sorted };
    });
  }, [set, setSilent]);

  const patchAllCaptions = useCallback((patch, silent = false) => {
    cuesDirty.current = true;
    (silent ? setSilent : set)((prev) => {
      const nextList = prev.cuesList.map((c) => ({ ...c, ...patch }));
      return { ...prev, cuesList: nextList };
    });
  }, [set, setSilent]);

  const handleUpdateCuesList = useCallback((newCues, silent = false) => {
    cuesDirty.current = true;
    (silent ? setSilent : set)((prev) => ({
      ...prev,
      cuesList: newCues,
    }));
  }, [set, setSilent]);

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

  const handleSelect = useCallback((sel, autoSeek = true) => {
    setSelection(sel);
    if (!sel || !autoSeek) return;
    if (sel.type === 'caption') {
      const cue = cuesList.find(c => c._uid === sel.id || c.id === sel.id);
      if (cue && typeof cue.start === 'number') {
        const cueEnd = typeof cue.end === 'number' ? cue.end : cue.start + 2.0;
        if (playhead < cue.start - 0.05 || playhead > cueEnd + 0.05) {
          seekPlayer(cue.start);
        }
      }
    } else if (sel.type === 'clip') {
      const seg = segments.find(s => s.clip?.id === sel.id);
      if (seg && typeof seg.segStart === 'number') {
        const segEnd = typeof seg.segEnd === 'number' ? seg.segEnd : seg.segStart + 2.0;
        if (playhead < seg.segStart - 0.05 || playhead > segEnd + 0.05) {
          seekPlayer(seg.segStart);
        }
      }
    } else if (sel.type === 'text_overlay' || sel.type === 'hook') {
      // The banner has a start of its own now, so both kinds seek the same way.
      const item = overlays.find((o) => o.id === sel.id)
        || (sel.type === 'hook' ? hookOverlay : null);
      if (item && typeof item.start === 'number') {
        const itemEnd = typeof item.end === 'number' ? item.end : item.start + 2.0;
        if (playhead < item.start - 0.05 || playhead > itemEnd + 0.05) {
          seekPlayer(item.start);
        }
      }
    }
  }, [cuesList, segments, overlays, hookOverlay, playhead, seekPlayer]);

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

  const patchStyle = useCallback((patch) => {
    set((prev) => ({ ...prev, style: { ...prev.style, ...patch } }));
  }, [set]);

  /** insertAt = null appends (the click path); a number drops it in place. */
  const addClip = useCallback((video, insertAt = null) => {
    const rawDur = video.duration || durations[video.path] || 10;
    const dur = Math.min(rawDur, 12);
    set((prev) => {
      const clip = {
        id: newId(),
        source_path: video.path,
        trim_start: 0,
        trim_end: dur,
        duration: dur,
        speed: 1,
        transition_in: 'cut',
        mirror: false,
      };
      const next = [...prev.clipList];
      const at = insertAt === null ? next.length : Math.max(0, Math.min(next.length, insertAt));
      next.splice(at, 0, clip);
      return { ...prev, clipList: next };
    });
  }, [durations, set]);

  const addTextAtPlayhead = useCallback(() => {
    const curTime = Number(playhead.toFixed(2));
    const dur = 2.5;
    const newCue = {
      start: curTime,
      end: Number((curTime + dur).toFixed(2)),
      text: 'ข้อความใหม่',
      translation: 'New text',
      scale: 1.0,
      _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    };
    set((prev) => {
      const next = [...prev.cuesList, newCue].sort((a, b) => a.start - b.start);
      return { ...prev, cuesList: next };
    });
    setSelection({ type: 'caption', id: newCue._uid });
    cuesDirty.current = true;
  }, [playhead, set]);

  const selectedSeg = useMemo(
    () => (selection?.type === 'clip' ? segments.find((s) => s.clip.id === selection.id) || null : null),
    [selection, segments]
  );
  const selectedCaption = useMemo(
    () => (selection?.type === 'caption' ? cuesList.find((c) => c._uid === selection.id || c.id === selection.id) || null : null),
    [selection, cuesList]
  );

  const splitAtPlayhead = () => {
    const seg = selectedSeg || segments.find((s) => playhead >= s.segStart && playhead < s.segEnd);
    if (!seg) return;
    // splitClipAt takes the segment and a global sequence time, and returns
    // null when either half would be shorter than MIN_CLIP_DURATION.
    const pieces = splitClipAt(seg, playhead, newId);
    if (!pieces) return;
    const [left, right] = pieces;
    set((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === seg.clip.id);
      if (idx === -1) return prev;
      const next = [...prev.clipList];
      next.splice(idx, 1, left, right);
      return { ...prev, clipList: next };
    });
    setSelection({ type: 'clip', id: right.id });
  };

  const duplicateSelected = () => {
    if (!selectedSeg) return;
    const orig = selectedSeg.clip;
    // transition_in describes the boundary with whatever clip used to precede
    // this one, not a property of the clip itself. Copying it verbatim onto a
    // duplicate placed right after the original would crossfade orig into its
    // own copy -- splitClipAt already resets this for the same reason.
    const dup = { ...orig, id: newId(), transition_in: 'cut' };
    set((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === orig.id);
      if (idx === -1) return prev;
      const next = [...prev.clipList];
      next.splice(idx + 1, 0, dup);
      return { ...prev, clipList: next };
    });
    setSelection({ type: 'clip', id: dup.id });
  };

  const deleteSelected = () => {
    if (selection?.type === 'clip') {
      set((prev) => ({ ...prev, clipList: prev.clipList.filter((c) => c.id !== selection.id) }));
      setSelection(null);
    } else if (selection?.type === 'caption') {
      cuesDirty.current = true;
      set((prev) => ({ ...prev, cuesList: prev.cuesList.filter((c) => c._uid !== selection.id) }));
      setSelection(null);
    } else if (selection?.type === 'text_overlay' || selection?.type === 'hook') {
      handleDeleteOverlay(selection.id);
    }
  };

  // Editor keyboard verbs. The app-level useKeyboardShortcuts hook covers tab
  // switching and save; these are the timeline ones, and they stay off while
  // the caret is in a field so typing "s" types an s.
  const keyHandlerRef = useRef(null);
  useEffect(() => {
    const onKey = (e) => {
      const el = e.target;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable)) return;

      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) redo(); else undo();
        return;
      }
      if (mod && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); return; }
      if (mod && e.key.toLowerCase() === 'b') { e.preventDefault(); splitAtPlayhead(); return; }
      if (e.key === 'Escape' && zen) { e.preventDefault(); setZen(false); return; }

      const jump = (delta) => {
        const next = Math.max(0, Math.min(Math.max(totalDuration, audioDuration || 0), playhead + delta));
        seekPlayer(next);
      };

      switch (e.key) {
        case ' ':
          e.preventDefault(); togglePlayer(); break;
        case 's': case 'S':
          e.preventDefault(); splitAtPlayhead(); break;
        case 'j': case 'J':
          e.preventDefault(); jump(-1.0); break;
        case 'k': case 'K':
          e.preventDefault(); togglePlayer(); break;
        case 'l': case 'L':
          e.preventDefault(); jump(1.0); break;
        case 'Delete': case 'Backspace':
          e.preventDefault(); deleteSelected(); break;
        case 'ArrowLeft':
          e.preventDefault(); jump(-(e.shiftKey ? 1 : 1 / 30)); break;
        case 'ArrowRight':
          e.preventDefault(); jump(e.shiftKey ? 1 : 1 / 30); break;
        case '+': case '=':
          e.preventDefault(); setZoomIndex((i) => Math.min(ZOOM_LEVELS.length - 1, i + 1)); break;
        case '-': case '_':
          e.preventDefault(); setZoomIndex((i) => Math.max(0, i - 1)); break;
        case 'f': case 'F':
          if (selectedSeg && selectedSeg.index > 0) {
            e.preventDefault();
            patchClip(selectedSeg.clip.id, {
              transition_in: selectedSeg.clip.transition_in && selectedSeg.clip.transition_in !== 'cut' ? 'cut' : 'fade',
            });
          }
          break;
        default:
          break;
      }
    };
    // Stashed rather than subscribed: this effect deliberately has no
    // dependency array so the handler is never stale, but binding the
    // listener here too meant tearing down and re-adding a window listener
    // on every single render (once per playhead frame while playing). The
    // one-time subscription below reads through the ref instead.
    keyHandlerRef.current = onKey;
  });

  useEffect(() => {
    const listener = (e) => keyHandlerRef.current?.(e);
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);

  const handleSplitCue = useCallback((cueUid, cursorIndex) => {
    set((prev) => {
      const idx = prev.cuesList.findIndex((c) => c._uid === cueUid);
      if (idx === -1) return prev;
      const target = prev.cuesList[idx];
      const fullText = target.text || '';
      const splitIdx = Math.max(1, Math.min(fullText.length - 1, cursorIndex || Math.floor(fullText.length / 2)));

      const text1 = fullText.slice(0, splitIdx).trim();
      const text2 = fullText.slice(splitIdx).trim();

      const ratio = text1.length / (text1.length + text2.length || 1);
      const dur = target.end - target.start;
      const splitTime = Number((target.start + dur * ratio).toFixed(2));

      // Proportionally split English translation words across the two split cues
      const fullTrans = (target.translation || '').trim();
      let trans1 = fullTrans;
      let trans2 = '';
      if (fullTrans) {
        const words = fullTrans.split(/\s+/);
        if (words.length > 1) {
          const splitWordIdx = Math.max(1, Math.min(words.length - 1, Math.round(words.length * ratio)));
          trans1 = words.slice(0, splitWordIdx).join(' ');
          trans2 = words.slice(splitWordIdx).join(' ');
        }
      }

      const cue1 = { ...target, end: splitTime, text: text1, translation: trans1 };
      const cue2 = { ...target, start: splitTime, text: text2, translation: trans2, _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` };

      const next = [...prev.cuesList];
      next.splice(idx, 1, cue1, cue2);
      cuesDirty.current = true;
      return { ...prev, cuesList: next };
    });
  }, [set]);

  const handleSplitCueAtPlayhead = useCallback((cueUid, playheadTime) => {
    set((prev) => {
      const idx = prev.cuesList.findIndex((c) => c._uid === cueUid);
      if (idx === -1) return prev;
      const target = prev.cuesList[idx];
      if (playheadTime <= target.start + 0.1 || playheadTime >= target.end - 0.1) return prev;

      const fullText = target.text || '';
      const timeRatio = (playheadTime - target.start) / (target.end - target.start);
      const splitCharIdx = Math.round(fullText.length * timeRatio);

      const text1 = fullText.slice(0, splitCharIdx).trim() || fullText.slice(0, Math.floor(fullText.length / 2)).trim();
      const text2 = fullText.slice(splitCharIdx).trim() || fullText.slice(Math.floor(fullText.length / 2)).trim();

      const fullTrans = (target.translation || '').trim();
      let trans1 = fullTrans;
      let trans2 = '';
      if (fullTrans) {
        const words = fullTrans.split(/\s+/);
        if (words.length > 1) {
          const splitWordIdx = Math.max(1, Math.min(words.length - 1, Math.round(words.length * timeRatio)));
          trans1 = words.slice(0, splitWordIdx).join(' ');
          trans2 = words.slice(splitWordIdx).join(' ');
        }
      }

      const cue1 = { ...target, end: Number(playheadTime.toFixed(2)), text: text1, translation: trans1 };
      const cue2 = { ...target, start: Number(playheadTime.toFixed(2)), text: text2, translation: trans2, _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` };

      const next = [...prev.cuesList];
      next.splice(idx, 1, cue1, cue2);
      cuesDirty.current = true;
      return { ...prev, cuesList: next };
    });
  }, [set]);

  const handleMergeCue = useCallback((cueUid) => {
    set((prev) => {
      const idx = prev.cuesList.findIndex((c) => c._uid === cueUid);
      if (idx === -1 || idx >= prev.cuesList.length - 1) return prev;
      const cur = prev.cuesList[idx];
      const next = prev.cuesList[idx + 1];

      const merged = {
        ...cur,
        end: next.end,
        text: `${cur.text || ''} ${next.text || ''}`.trim(),
        translation: `${cur.translation || ''} ${next.translation || ''}`.trim(),
      };

      const list = [...prev.cuesList];
      list.splice(idx, 2, merged);
      cuesDirty.current = true;
      return { ...prev, cuesList: list };
    });
  }, [set]);

  const handleMergeWithPrevious = useCallback((cueUid) => {
    set((prev) => {
      const idx = prev.cuesList.findIndex((c) => c._uid === cueUid);
      if (idx <= 0) return prev;
      const prevCue = prev.cuesList[idx - 1];
      const curCue = prev.cuesList[idx];

      const merged = {
        ...prevCue,
        end: curCue.end,
        text: `${prevCue.text || ''} ${curCue.text || ''}`.trim(),
        translation: `${prevCue.translation || ''} ${curCue.translation || ''}`.trim(),
      };

      const list = [...prev.cuesList];
      list.splice(idx - 1, 2, merged);
      cuesDirty.current = true;
      return { ...prev, cuesList: list };
    });
  }, [set]);

  const handleReorderCues = useCallback((fromIdx, toIdx) => {
    set((prev) => {
      if (fromIdx < 0 || fromIdx >= prev.cuesList.length || toIdx < 0 || toIdx >= prev.cuesList.length) return prev;
      const list = [...prev.cuesList];
      const [moved] = list.splice(fromIdx, 1);
      list.splice(toIdx, 0, moved);
      cuesDirty.current = true;
      return { ...prev, cuesList: list };
    });
  }, [set]);

  const handleBatchFindAndReplace = useCallback((findText, replaceText) => {
    if (!findText) return 0;
    let count = 0;
    set((prev) => {
      const regex = new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      const list = prev.cuesList.map((c) => {
        const hasMatch = regex.test(c.text || '') || regex.test(c.translation || '');
        if (hasMatch) {
          count++;
          return {
            ...c,
            text: (c.text || '').replace(regex, replaceText),
            translation: c.translation ? c.translation.replace(regex, replaceText) : c.translation,
          };
        }
        return c;
      });
      if (count > 0) cuesDirty.current = true;
      return { ...prev, cuesList: list };
    });
    return count;
  }, [set]);

  const handleBatchFormatClean = useCallback(() => {
    set((prev) => {
      const list = prev.cuesList.map((c) => {
        let txt = (c.text || '')
          .replace(/\s+/g, ' ')
          .replace(/^[,\.\-_\s]+|[,\.\-_\s]+$/g, '')
          .trim();
        return { ...c, text: txt };
      });
      cuesDirty.current = true;
      return { ...prev, cuesList: list };
    });
  }, [set]);

  const handleDeleteCue = useCallback((cueUid) => {
    cuesDirty.current = true;
    set((prev) => ({ ...prev, cuesList: prev.cuesList.filter((c) => c._uid !== cueUid) }));
    setSelection(null);
  }, [set]);

  const handleInsertCueAfter = useCallback((afterCueUid) => {
    set((prev) => {
      const list = [...prev.cuesList];
      if (!afterCueUid) {
        const newCue = {
          start: 0,
          end: 3.0,
          text: 'ข้อความคำบรรยายใหม่...',
          translation: '',
          sfx: null,
          _uid: `cue-${Date.now().toString(36)}`,
        };
        cuesDirty.current = true;
        return { ...prev, cuesList: [newCue] };
      }

      const idx = list.findIndex((c) => c._uid === afterCueUid);
      if (idx === -1) return prev;
      const cur = list[idx];
      const start = cur.end;
      const end = Number((cur.end + 2.5).toFixed(2));
      const newCue = {
        start,
        end,
        text: 'ข้อความคำบรรยายใหม่...',
        translation: '',
        sfx: null,
        _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
      };
      list.splice(idx + 1, 0, newCue);
      cuesDirty.current = true;
      return { ...prev, cuesList: list };
    });
  }, [set]);

  const handleImportCues = useCallback((cues) => {
    if (!cues || !Array.isArray(cues)) return;
    cuesDirty.current = true;
    set((prev) => ({
      ...prev,
      cuesList: cues.map((c, i) => ({
        start: c.start,
        end: c.end,
        text: c.text,
        translation: c.translation || '',
        sfx: c.sfx || null,
        _uid: `cue-${i}-${Date.now().toString(36)}`,
      })),
    }));
    // Auto switch to timeline on mobile to see imported cues
    setMobileTab('timeline');
  }, [set]);

  const handleApply = async () => {
    if (!projectName) { setApplyError('เลือกโปรเจกต์ก่อน'); return; }
    if (!clipList.length) { setApplyError('เพิ่มคลิปในไทม์ไลน์ก่อน'); return; }

    const base = loadedAudioStyle.current;
    const audioDirty = (style.bgmName ?? null) !== (base.bgmName ?? null)
      || (style.bgmVolume ?? 0.12) !== (base.bgmVolume ?? 0.12)
      || !!style.bgmDucking !== !!base.bgmDucking;

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
        updateAngleStatus(productContext.id, productContext.angles[angleIndex].angle_id, 'in_production').catch(() => {});
      } catch (e) {}
    }
    try {
      await updateProjectState(projectName, savePayload).catch(() => {});
      const audioMutes = trackMix.mute || {};

      const res = await startReroll({
        project_name: projectName,
        part: audioDirty ? 'bgm' : 'subtitles',
        clip_list: savePayload.clip_list,
        transitions: savePayload.transitions,
        overlays,
        bilingual_subtitles: true,
        font_name: style.fontName,
        bgm_name: style.bgmName,
        lut_name: style.lutName,
        // "" is meaningful here: it clears the badge stored on the project.
        sticker_badge: style.stickerBadge ?? '',
        lut_intensity: style.lutIntensity ?? 1,
        // Track mute is a render setting as well as a preview control. BGM is
        // already an independent mixer input, so preserve the user's mute in
        // the rerender payload instead of silently restoring it.
        bgm_volume: audioMutes.bgm ? 0 : (style.bgmVolume ?? 0.12),
        bgm_ducking: !!style.bgmDucking,
        audio_mutes: audioMutes,
        export_preset: exportPreset,
        caption_position: style.captionPosition || 'bottom',
        caption_color: style.captionColor || '#FFFFFF',
        caption_scale: style.captionScale ?? 1,
        sticker_position: style.stickerPosition || 'top_right',
        sticker_scale: style.stickerScale ?? 1,
      });
      startJob(res.job_id);
      pollTasks?.();
      cuesDirty.current = false;
      loadedAudioStyle.current = {
        bgmName: style.bgmName ?? null,
        bgmVolume: style.bgmVolume ?? 0.12,
        bgmDucking: !!style.bgmDucking,
      };
      loadedCaptionStyle.current = {
        captionPosition: style.captionPosition || 'bottom',
        captionColor: style.captionColor || '#FFFFFF',
        captionScale: style.captionScale ?? 1,
      };
    } catch (err) {
      stopJob();
      setApplyError(formatErrorText(err));
    }
  };

  // What the preview plays instead of a baked mix: the voice stem plus the
  // same BGM and per-cue SFX files the renderer will mix, resolved to media
  // URLs from the asset registry (each entry already carries an absolute
  // path). Changing BGM or dropping an SFX on a cue is then audible at once,
  // where before it needed a full re-render to hear.
  //
  // Every lookup here mirrors a backend resolver so the preview never plays a
  // different file than the render: resolve_bgm_path()'s default-then-first
  // fallback (sfx_manager.py:41-60), resolve_sfx_path()'s legacy short-name
  // aliases (asset_registry.py:244-258), and the boom the mix always lays down
  // at t=0 (sfx_manager.py:90-97).
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

    const sfxShots = [];
    const boom = findSfx('boom');
    if (boom) sfxShots.push({ time: 0, id: 'boom', name: boom.name, url: toMediaUrl(boom.path) });
    (cuesList || []).forEach((c) => {
      if (!c.sfx) return;
      const entry = findSfx(c.sfx);
      if (!entry) return;
      sfxShots.push({
        time: Number(c.start) || 0,
        id: c.sfx,
        // The render's pre-roll test reads the resolved *filename*, not the cue
        // tag (sfx_manager.py:107) -- pass it through so the preview fires early
        // on exactly the same files.
        name: entry.name,
        url: toMediaUrl(entry.path),
      });
    });

    (overlays || []).forEach((o) => {
      if (!o.sfx || o.hidden) return;
      const entry = findSfx(o.sfx);
      if (!entry) return;
      sfxShots.push({
        time: Number(o.start) || 0,
        id: o.sfx,
        name: entry.name,
        url: toMediaUrl(entry.path),
        overlayId: o.id,
      });
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
    };
  }, [voiceUrl, style.bgmName, style.bgmVolume, style.bgmDucking, assets.music, assets.sfx, cuesList, overlays]);

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
    audioCollapsed,
  });

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
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-[#0A0D14]">
      {/* ── HEADER / TOPBAR ── */}
      <div className="flex flex-shrink-0 items-center justify-between gap-2 border-b border-white/[0.08] bg-[#0F1420] px-2.5 sm:px-4 py-2">
        {/* ── Identity: which clip is open, and where the playhead is. The
              project name is the title of this screen, so it gets the room. ── */}
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Scissors className="hidden h-4 w-4 flex-shrink-0 text-[#D97757] sm:block" />

          <div className="relative min-w-0 flex-1 sm:max-w-[420px]">
            <select
              value={projectName}
              onChange={(e) => loadProject(e.target.value)}
              aria-label="โปรเจกต์ที่กำลังแก้"
              className="h-9 w-full min-w-0 cursor-pointer truncate rounded-xl border border-transparent bg-transparent pl-1 pr-6 text-base font-bold text-white hover:border-white/[0.12] hover:bg-black/40 focus:border-[#D97757] focus:outline-none"
            >
              <option value="">— เลือกโปรเจกต์ —</option>
              {projectList.map((p) => (
                <option key={p.project_name} value={p.project_name} className="bg-[#0D111A] text-slate-200">
                  {p.project_name}
                </option>
              ))}
            </select>
          </div>

          {projectName && (
            <div className="flex items-center gap-2">
              <span className="flex-shrink-0 font-mono text-sm font-bold text-slate-400">
                <span className="text-[#E89274]">{formatTimecode(playhead)}</span>
                <span className="hidden sm:inline"> / {formatTimecode(Math.max(totalDuration, audioDuration))}</span>
              </span>
              {/* Shown at every width: hidden below md, a phone user had no
                  way at all to tell whether their edits had been saved. Only
                  the wording collapses on narrow screens, not the state. */}
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

        {/* Right: Sidebar Toggles, Fullscreen & Apply / Render Buttons */}
        <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
          {/* Quick Sidebar Toggles (Desktop) */}
          {/* lg, not md: these collapse the desktop tree's own columns, so
              below the layout breakpoint they have nothing to act on. */}
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
            onClick={() => { setProjectName(''); setSelection(null); }}
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
                // the only control for zen mode -- there is no button for it
                // on the bar itself
                id: 'zen',
                label: zen ? 'ย่อพรีวิวกลับ' : 'ขยายพรีวิวเต็มพื้นที่',
                icon: zen ? Minimize2 : Maximize2,
                disabled: !projectName,
                onSelect: () => setZen((v) => !v),
              },
              {
                // Each handle resets on double-click, but nothing advertises
                // that, so a panel dragged somewhere awkward (or a stale
                // stored size) had no discoverable way back.
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
                onSelect: () => {
                  setDeleteError(null);
                  setDeleteScope('project');
                  setDeleteOrigin(null);
                  setPendingDelete(projectName);
                  getProjectOrigin(projectName).then(setDeleteOrigin).catch(() => setDeleteOrigin({}));
                },
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
            presets={EXPORT_PRESETS}
            value={exportPreset}
            onChange={setExportPreset}
            onRender={handleApply}
            busy={applying}
            progress={progress}
            disabled={!projectName}
          />
        </div>
      </div>

      {loadError && (
        <div className="flex flex-shrink-0 items-center gap-2 border-b border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300">
          <AlertCircle className="h-3.5 w-3.5" />{loadError}
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
                    detail: angle
                      ? `มุม “${angle.angle_name || angle.hook_title}” จะหายจากเมนูสินค้าและแทร็กเกอร์`
                      : 'หามุมที่ตรงกับโปรเจกต์นี้ไม่เจอ (คลิปเก่าที่ยังไม่ได้บันทึกที่มา)',
                    enabled: !!angle,
                  },
                  {
                    id: 'product',
                    label: 'ลบสินค้านี้ทั้งหมด',
                    detail: product
                      ? `“${product.name}” พร้อมสคริปต์ทั้ง ${product.angle_count} มุม จะหายทั้งหมด`
                      : 'หาสินค้าที่ผูกกับโปรเจกต์นี้ไม่เจอ',
                    enabled: !!product,
                  },
                ];
                return (
                  <div className="space-y-2">
                    {!origin && <p className="text-sm text-slate-400">กำลังตรวจว่าผูกกับอะไรอยู่...</p>}
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
            <span className="text-sm font-bold font-kanit">กำลังโหลดข้อมูลไทม์ไลน์...</span>
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
            <div className="flex flex-shrink-0 items-center gap-1.5 border-b border-rose-500/30 bg-rose-950/40 px-3 py-1.5 text-sm text-rose-200">
              <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="min-w-0 flex-1">{applyError}</span>
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
                  ref={mobilePlayerRef}
                  clips={clipList}
                  cues={cuesList}
                  overlays={overlays}
                  audioUrl={audioUrl}
                  audioStems={audioStems}
                  grade={grade}
                  trackMix={trackMix}
                  captionStyle={{
                    captionPosition: style.captionPosition,
                    captionColor: style.captionColor,
                    captionScale: style.captionScale,
                    fontName: style.fontName,
                    hidden: isCaptionHidden,
                  }}
                  isMuted={isAudioMuted}
                  stickerStyle={{
                    badge: style.stickerBadge,
                    position: style.stickerPosition || 'top_right',
                    scale: style.stickerScale || 1.0,
                    startTime: 0.5,
                    stickers: assets.stickers,
                  }}
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
                  onUpdateSticker={(patch) => patchStyle(patch)}
                  previewTextTemplate={previewTextTemplate}
                  onCommitPreviewTextTemplate={handleAddTextTemplate}
                  onDismissPreviewTextTemplate={() => setPreviewTextTemplate(null)}
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
            <div className="flex-shrink-0 flex items-center justify-around border-b border-white/[0.08] bg-[#0D111A] p-1">
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
                    className={`flex-1 py-1.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
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
                  canSplit={!!selectedSeg || segments.some((s) => playhead >= s.segStart + 0.2 && playhead <= s.segEnd - 0.2)}
                  canUndo={canUndo}
                  canRedo={canRedo}
                  onUndo={undo}
                  onRedo={redo}
                  onSplit={splitAtPlayhead}
                  onAddText={addTextAtPlayhead}
                  onDuplicate={duplicateSelected}
                  onDelete={deleteSelected}
                  onToggleMirror={() => selectedSeg && patchClip(selectedSeg.clip.id, { mirror: !selectedSeg.clip.mirror })}
                  onCycleSpeed={() => {
                    if (!selectedSeg) return;
                    const order = [0.5, 1, 1.5, 2];
                    const cur = selectedSeg.clip.speed || 1;
                    const next = order[(order.indexOf(cur) + 1) % order.length] || 1;
                    patchClip(selectedSeg.clip.id, { speed: next === 1 ? undefined : next });
                  }}
                  zoomIndex={zoomIndex}
                  zoomCount={ZOOM_LEVELS.length}
                  onZoomToFit={zoomToFit}
                  onZoom={(dir) => setZoomIndex((i) => Math.max(0, Math.min(ZOOM_LEVELS.length - 1, i + dir)))}
                  snapEnabled={snapEnabled}
                  onToggleSnap={() => setSnapEnabled((v) => !v)}
                />
                <div className="min-h-0 flex-1">
                  <Timeline
                    segments={segments}
                    totalDuration={totalDuration}
                    audioDuration={audioDuration}
                    cues={cuesList}
                    bgmLabel={bgmLabel}
                    filmstrips={filmstrips}
                    pxPerSec={pxPerSec}
                    playhead={playhead}
                    selection={selection}
                    onSelect={handleSelect}
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
                    onBeginDrag={beginDrag}
                    onEndDrag={endDrag}
                    onZoom={(dir) => setZoomIndex((i) => Math.max(0, Math.min(ZOOM_LEVELS.length - 1, i + dir)))}
                    viewportRef={timelineViewportRef}
                    snapCandidates={snapEnabled ? snapCandidates(segments, playhead, [...(audioDuration > 0 ? [audioDuration] : []), ...cueSnapPoints]) : []}
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
                      selectedCaption={selectedCaption}
                      onAddClip={addClip}
                      onAddTextAtPlayhead={handleAddTextOverlay}
                      onAddTextTemplate={handleAddTextTemplate}
                      onSelectTextTemplate={handleSelectTextTemplate}
                      hookTemplates={HOOK_TEMPLATES}
                      activeHookTemplate={hookOverlay?.template || null}
                      onApplyHookTemplate={handleApplyHookTemplate}
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
                      fonts={assets.fonts}
                      onToggleHookHeader={handleEnsureHookOverlay}
                      onAddTextAtPlayhead={addTextAtPlayhead}
                      onStyleChange={patchStyle}
                      onClipChange={(patch) => selectedSeg && patchClip(selectedSeg.clip.id, patch)}
                      onCaptionChange={(cueUid, patch) => patchCaption(cueUid, patch)}
                      applyToAll={applyToAllCaptions}
                      onToggleApplyToAll={setApplyToAllCaptions}
                      onPatchAllCaptions={patchAllCaptions}
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
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ══════════════════════════════════════════════════════════
              🖥️ DESKTOP PRO LAYOUT (>= md breakpoint) - 3 Columns
             ══════════════════════════════════════════════════════════ */}
          <div className="hidden lg:flex flex-col flex-1 min-h-0">
            {/* Middle Row (AssetPanel + Video + Inspector) */}
            <div className="flex min-h-0 flex-1">
              {!zen && (
                leftSidebarCollapsed ? (
                  <div className="flex-shrink-0 flex items-start border-r border-white/[0.08] bg-[#0A0D14] z-20">
                    <button
                      type="button"
                      onClick={toggleLeftSidebar}
                      title="เปิดแถบซ้าย (คลังสื่อ)"
                      className="m-2 flex h-8 w-7 items-center justify-center rounded-lg bg-white/[0.06] text-slate-400 hover:bg-[#25F4EE]/20 hover:text-[#25F4EE] border border-white/[0.08] transition-all cursor-pointer shadow-sm"
                    >
                      <ChevronRight className="h-4 w-4" />
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
                        selectedCaption={selectedCaption}
                        onAddClip={addClip}
                        onAddTextAtPlayhead={handleAddTextOverlay}
                        onAddTextTemplate={handleAddTextTemplate}
                        onSelectTextTemplate={handleSelectTextTemplate}
                        hookTemplates={HOOK_TEMPLATES}
                        activeHookTemplate={hookOverlay?.template || null}
                        onApplyHookTemplate={handleApplyHookTemplate}
                        previewTextTemplate={previewTextTemplate}
                        activeTextTemplateId={selection?.type === 'text_overlay' ? overlays.find((o) => o.id === selection.id)?.template_id : null}
                        onStyleChange={patchStyle}
                        onAssignSfx={(sfxId) => selectedCaption && patchCaption(selectedCaption._uid, { sfx: sfxId })}
                        onImportCues={handleImportCues}
                        onVideoUploaded={onVideoUploaded}
                        projectName={projectName}
                      />
                    </div>
                    {/* Left Resizer */}
                    <div
                      role="separator"
                      aria-orientation="vertical"
                      aria-label="ปรับความกว้างแผงซ้าย"
                      title="ลากซ้าย-ขวาเพื่อปรับความกว้าง · ดับเบิลคลิกเพื่อรีเซ็ต"
                      onPointerDown={(e) => {
                        assetResizeRef.current = { startX: e.clientX, startW: assetW };
                        try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
                      }}
                      onPointerMove={(e) => {
                        const d = assetResizeRef.current;
                        if (!d) return;
                        applyAssetW(d.startW + (e.clientX - d.startX));
                      }}
                      onPointerUp={(e) => {
                        assetResizeRef.current = null;
                        try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
                      }}
                      onPointerCancel={() => { assetResizeRef.current = null; }}
                      onDoubleClick={() => applyAssetW(ASSET_DEFAULT_W)}
                      className="group relative w-1.5 flex-shrink-0 cursor-col-resize touch-none bg-white/[0.04] transition-colors hover:bg-[#25F4EE]/60 flex items-center justify-center"
                    >
                      <span className="h-6 w-0.5 rounded-full bg-white/20 group-hover:bg-[#25F4EE] transition-colors" />
                    </div>
                  </div>
                )
              )}

              {/* Center: SequencePlayer */}
              <div className="flex min-h-0 flex-1 flex-col items-center gap-2 overflow-hidden p-3 bg-black/40">
                {!isMobileView && (
                  <SequencePlayer
                    ref={desktopPlayerRef}
                    clips={clipList}
                    cues={cuesList}
                    overlays={overlays}
                    audioUrl={audioUrl}
                    audioStems={audioStems}
                    grade={grade}
                    trackMix={trackMix}
                    captionStyle={{
                      captionPosition: style.captionPosition,
                      captionColor: style.captionColor,
                      captionScale: style.captionScale,
                      fontName: style.fontName,
                      hidden: isCaptionHidden,
                    }}
                    isMuted={isAudioMuted}
                    stickerStyle={{
                      badge: style.stickerBadge,
                      position: style.stickerPosition || 'top_right',
                      scale: style.stickerScale || 1.0,
                      startTime: 0.5,
                      stickers: assets.stickers,
                    }}
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
                    onUpdateSticker={(patch) => patchStyle(patch)}
                    previewTextTemplate={previewTextTemplate}
                    onCommitPreviewTextTemplate={handleAddTextTemplate}
                    onDismissPreviewTextTemplate={() => setPreviewTextTemplate(null)}
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
                  <div className="flex-shrink-0 flex items-start border-l border-white/[0.08] bg-[#0A0D14] z-20">
                    <button
                      type="button"
                      onClick={toggleRightSidebar}
                      title="เปิดแถบขวา (แก้ไขคำบรรยาย)"
                      className="m-2 flex h-8 w-7 items-center justify-center rounded-lg bg-white/[0.06] text-slate-400 hover:bg-[#D97757]/20 hover:text-[#D97757] border border-white/[0.08] transition-all cursor-pointer shadow-sm"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <div className="relative flex flex-shrink-0">
                    {/* Right Resizer */}
                    <div
                      role="separator"
                      aria-orientation="vertical"
                      aria-label="ปรับความกว้างแผงขวา"
                      title="ลากซ้าย-ขวาเพื่อปรับความกว้าง · ดับเบิลคลิกเพื่อรีเซ็ต"
                      onPointerDown={(e) => {
                        inspectorResizeRef.current = { startX: e.clientX, startW: inspectorW };
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
                        try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
                      }}
                      onPointerCancel={() => { inspectorResizeRef.current = null; }}
                      onDoubleClick={() => applyInspectorW(INSPECTOR_DEFAULT_W)}
                      className="group relative w-1.5 flex-shrink-0 cursor-col-resize touch-none bg-white/[0.04] transition-colors hover:bg-[#D97757]/60 flex items-center justify-center"
                    >
                      <span className="h-6 w-0.5 rounded-full bg-white/20 group-hover:bg-[#D97757] transition-colors" />
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
                        fonts={assets.fonts}
                        onToggleHookHeader={handleEnsureHookOverlay}
                        onAddTextAtPlayhead={addTextAtPlayhead}
                        onStyleChange={patchStyle}
                        onClipChange={(patch) => selectedSeg && patchClip(selectedSeg.clip.id, patch)}
                        onCaptionChange={(cueUid, patch) => patchCaption(cueUid, patch)}
                        applyToAll={applyToAllCaptions}
                        onToggleApplyToAll={setApplyToAllCaptions}
                        onPatchAllCaptions={patchAllCaptions}
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
                <div
                  role="separator"
                  aria-orientation="horizontal"
                  aria-label="ปรับความสูงไทม์ไลน์"
                  title="ลากขึ้น-ลงเพื่อปรับความสูงไทม์ไลน์ · ดับเบิลคลิกเพื่อรีเซ็ต"
                  onPointerDown={(e) => {
                    resizeRef.current = { startY: e.clientY, startH: timelineH };
                    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag */ }
                  }}
                  onPointerMove={(e) => {
                    const d = resizeRef.current;
                    if (!d) return;
                    applyTimelineH(d.startH - (e.clientY - d.startY));
                  }}
                  onPointerUp={(e) => {
                    resizeRef.current = null;
                    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* released */ }
                  }}
                  onPointerCancel={() => { resizeRef.current = null; }}
                  onDoubleClick={() => applyTimelineH(TIMELINE_DEFAULT_H)}
                  className="group flex h-2 flex-shrink-0 cursor-ns-resize touch-none items-center justify-center bg-[#0F1420]"
                >
                  <span className="h-0.5 w-10 rounded-full bg-slate-600 transition-colors duration-150 group-hover:bg-[#25F4EE]" />
                </div>
                <Toolbar
                  playhead={playhead}
                  totalDuration={totalDuration}
                  hasClipSelected={!!selectedSeg}
                  hasSelection={!!selection}
                  selectedClip={selectedSeg?.clip}
                  canSplit={!!selectedSeg || segments.some((s) => playhead >= s.segStart + 0.2 && playhead <= s.segEnd - 0.2)}
                  canUndo={canUndo}
                  canRedo={canRedo}
                  onUndo={undo}
                  onRedo={redo}
                  onSplit={splitAtPlayhead}
                  onAddText={addTextAtPlayhead}
                  onDuplicate={duplicateSelected}
                  onDelete={deleteSelected}
                  onToggleMirror={() => selectedSeg && patchClip(selectedSeg.clip.id, { mirror: !selectedSeg.clip.mirror })}
                  onCycleSpeed={() => {
                    if (!selectedSeg) return;
                    const order = [0.5, 1, 1.5, 2];
                    const cur = selectedSeg.clip.speed || 1;
                    const next = order[(order.indexOf(cur) + 1) % order.length] || 1;
                    patchClip(selectedSeg.clip.id, { speed: next === 1 ? undefined : next });
                  }}
                  zoomIndex={zoomIndex}
                  zoomCount={ZOOM_LEVELS.length}
                  onZoomToFit={zoomToFit}
                  onZoom={(dir) => setZoomIndex((i) => Math.max(0, Math.min(ZOOM_LEVELS.length - 1, i + dir)))}
                  snapEnabled={snapEnabled}
                  onToggleSnap={() => setSnapEnabled((v) => !v)}
                />
                <div className="min-h-0 flex-1">
                  <Timeline
                    segments={segments}
                    totalDuration={totalDuration}
                    audioDuration={audioDuration}
                    cues={cuesList}
                    bgmLabel={bgmLabel}
                    filmstrips={filmstrips}
                    pxPerSec={pxPerSec}
                    playhead={playhead}
                    selection={selection}
                    onSelect={handleSelect}
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
                    onBeginDrag={beginDrag}
                    onEndDrag={endDrag}
                    onZoom={(dir) => setZoomIndex((i) => Math.max(0, Math.min(ZOOM_LEVELS.length - 1, i + dir)))}
                    viewportRef={timelineViewportRef}
                    snapCandidates={snapEnabled ? snapCandidates(segments, playhead, [...(audioDuration > 0 ? [audioDuration] : []), ...cueSnapPoints]) : []}
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
    </div>
  );
}
