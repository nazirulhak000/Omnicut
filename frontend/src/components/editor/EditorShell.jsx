import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, AlertTriangle, CheckCircle2, Loader2, Maximize2, Minimize2,
  RefreshCw, Rocket, Scissors, Film, Layers, Sliders, Sparkles, Trash2
} from 'lucide-react';
import {
  deleteProject, getAllAssets, getProject, getProjectOrigin, getProjects, getRenderStatus, startReroll, updateProjectCues,
} from '../../api';
import {
  FADE_DURATION, ZOOM_LEVELS, buildSegments, formatTimecode, splitClipAt, snapCandidates, snapTime,
  totalDuration as totalDurationOf,
} from '../../lib/timelineMath';
import { useEditorHistory } from '../../hooks/useEditorHistory';
import { toMediaUrl } from '../../lib/mediaUrl';
import SequencePlayer from '../SequencePlayer';
import AssetPanel from './AssetPanel';
import Inspector from './Inspector';
import Timeline from './Timeline';
import Toolbar from './Toolbar';
import NewClipPanel from './NewClipPanel';
import { ActivityIndicatorButton } from '../ActivityCenter';
import HeaderMenu from './HeaderMenu';
import RenderButton from './RenderButton';
import UiScaleControl from '../UiScaleControl';

const framesFor = (seconds) => Math.max(6, Math.min(40, Math.round((seconds || 12) / 3)));
const SNAP_PX = 6;
const EXPORT_PRESETS = [
  { id: 'post', label: 'โพสต์จริง 1080p', hint: 'คุณภาพเต็ม สำหรับอัปขึ้น TikTok' },
  { id: 'draft', label: 'ทดลอง 720p', hint: 'เร็วกว่าประมาณ 2 เท่า ไฟล์มี _draft ต่อท้าย ไม่ใช่ไฟล์สำหรับโพสต์' },
];

const TIMELINE_MIN_H = 196;
const MOBILE_PREVIEW_MIN_H = 160;
const MOBILE_PREVIEW_DEFAULT = 0.45;   // share of the window height
const TIMELINE_MAX_H = 460;
const TIMELINE_DEFAULT_H = 212;
const INSPECTOR_MIN_W = 320;
const INSPECTOR_MAX_W = 640;
const INSPECTOR_DEFAULT_W = 350;

const EMPTY = { clipList: [], cuesList: [], style: { fontName: 'IBMPlex', bgmName: null, lutName: null, lutIntensity: 1, stickerBadge: null, bgmVolume: 0.12, bgmDucking: false, captionPosition: 'bottom', captionColor: '#FFFFFF', captionScale: 1, stickerPosition: 'top_right', stickerScale: 1 } };

let idCounter = 0;
const newId = () => `clip-${Date.now().toString(36)}-${++idCounter}`;

export default function EditorShell({
  videos = [],
  productContext = null,
  angleIndex = 0,
  onAngleChange,
  onGoToProductFlow,
  onVideoUploaded,
}) {
  const { state, set, setSilent, beginDrag, endDrag, undo, redo, reset, canUndo, canRedo } = useEditorHistory(EMPTY);
  const { clipList, cuesList, style } = state;

  const [projectList, setProjectList] = useState([]);
  const [projectName, setProjectName] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [assets, setAssets] = useState({ sfx: [], music: [], fonts: [], stickers: [], luts: [] });

  const [durations, setDurations] = useState({});
  const [audioDuration, setAudioDuration] = useState(0);
  const [selection, setSelection] = useState(null);
  const [playhead, setPlayhead] = useState(0);
  const [zoomIndex, setZoomIndex] = useState(2);
  const [snapEnabled, setSnapEnabled] = useState(true);

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

  // Desktop inspector-panel width resizer -- the caption/script text lives in
  // here, and a fixed 350px column is what made it unreadable at 8 chars.
  // Letting someone drag it wider is the general fix; the row layout can only
  // be so generous on its own.
  const [inspectorW, setInspectorW] = useState(() => {
    try {
      const saved = Number(localStorage.getItem('editor.inspectorW'));
      return saved >= INSPECTOR_MIN_W && saved <= INSPECTOR_MAX_W ? saved : INSPECTOR_DEFAULT_W;
    } catch (err) {
      return INSPECTOR_DEFAULT_W;
    }
  });
  const inspectorResizeRef = useRef(null);
  const applyInspectorW = (nextW) => {
    const clamped = Math.max(INSPECTOR_MIN_W, Math.min(INSPECTOR_MAX_W, nextW));
    setInspectorW(clamped);
    try { localStorage.setItem('editor.inspectorW', String(clamped)); } catch (err) { /* private mode */ }
  };

  // Mobile split. The preview used to be locked to 28vh on every tab except
  // the timeline, which is why editing captions left the clip as a thumbnail.
  const mobileWrapRef = useRef(null);
  const mobileResizeRef = useRef(null);
  const [mobilePreviewH, setMobilePreviewH] = useState(() => {
    const saved = parseInt(localStorage.getItem('editor.mobilePreviewH') || '', 10);
    return Number.isFinite(saved) ? saved : Math.round(window.innerHeight * MOBILE_PREVIEW_DEFAULT);
  });

  const applyMobilePreviewH = (px) => {
    const box = mobileWrapRef.current?.getBoundingClientRect();
    // leave the panel enough for its tab row plus a couple of rows
    const max = box ? Math.max(MOBILE_PREVIEW_MIN_H, box.height - 220) : 640;
    const clamped = Math.min(max, Math.max(MOBILE_PREVIEW_MIN_H, Math.round(px)));
    setMobilePreviewH(clamped);
    try { localStorage.setItem('editor.mobilePreviewH', String(clamped)); } catch (err) { /* private mode */ }
  };

  const applyTimelineH = (nextH) => {
    const clamped = Math.max(TIMELINE_MIN_H, Math.min(TIMELINE_MAX_H, nextH));
    setTimelineH(clamped);
    try { localStorage.setItem('capcut_timeline_h', String(clamped)); } catch (err) { /* ignore */ }
  };

  const [zen, setZen] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState(null);
  const [applyResult, setApplyResult] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [confirmGap, setConfirmGap] = useState(0);
  // Draft = 720p/crf26/veryfast. Measured on this machine: a 12s clip took
  // 25.5s at post quality vs 12.5s as a draft (12.18 MB vs 1.82 MB).
  const [exportPreset, setExportPreset] = useState('post');
  const [audioUrl, setAudioUrl] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [deleteScope, setDeleteScope] = useState('project');
  const [deleteOrigin, setDeleteOrigin] = useState(null);

  const mobilePlayerRef = useRef(null);
  const desktopPlayerRef = useRef(null);
  const cuesDirty = useRef(false);
  // Music lives in the mix, not the video pass. Apply has to ask for the
  // "bgm" re-roll when any of it changed, or the render happily reuses the
  // old mixed_audio.wav and the new track is silently ignored.
  const loadedAudioStyle = useRef({ bgmName: null, bgmVolume: 0.12, bgmDucking: false });
  // Caption look is baked into the .ass, which the "video" part reuses -- so a
  // caption style change has to ask for the subtitles part instead.
  const loadedCaptionStyle = useRef({ captionPosition: 'bottom', captionColor: '#FFFFFF', captionScale: 1 });

  const seekPlayer = useCallback((t) => {
    setPlayhead(t);
    mobilePlayerRef.current?.seek(t);
    desktopPlayerRef.current?.seek(t);
  }, []);

  const togglePlayer = useCallback(() => {
    mobilePlayerRef.current?.toggle();
    desktopPlayerRef.current?.toggle();
  }, []);

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
    getProjects()
      .then((data) => setProjectList(data?.projects || []))
      .catch(() => {})
      .finally(() => loadProject(newProjectName));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load project list + assets on mount
  useEffect(() => {
    getProjects()
      .then((data) => setProjectList(data?.projects || []))
      .catch((err) => setLoadError(err.message || 'โหลดรายการโปรเจกต์ไม่สำเร็จ'));

    getAllAssets()
      .then(setAssets)
      .catch((err) => console.warn('Asset fetch failed:', err));
  }, []);

  const loadProject = async (name) => {
    if (!name) return;
    setLoading(true);
    setLoadError(null);
    setSelection(null);
    setApplyError(null);
    setApplyResult(null);
    setConfirmGap(0);
    try {
      const data = await getProject(name);
      setProjectName(name);

      // Support clips from data.clip_list or data.render_params.clip_list or fallback to raw_video_path
      const rawClips = (data.clip_list && data.clip_list.length > 0)
        ? data.clip_list
        : (data.render_params?.clip_list && data.render_params.clip_list.length > 0)
        ? data.render_params.clip_list
        : (data.render_params?.raw_video_path || data.raw_video_path)
        ? [{ source_path: data.render_params?.raw_video_path || data.raw_video_path, trim_start: 0, trim_end: null }]
        : [];

      const clips = rawClips.map((c, i) => ({
        id: newId(),
        source_path: c.source_path || c.path || '',
        trim_start: Number(c.trim_start) || 0,
        trim_end: c.trim_end != null ? Number(c.trim_end) : null,
        duration: Number(c.duration) || 0,
        speed: Number(c.speed) || 1,
        transition_in: c.transition_in || (i === 0 ? 'cut' : 'cut'),
        mirror: !!c.mirror,
      }));

      // Support cues from data.cues or data.micro_cues
      const rawCues = (data.cues && data.cues.length > 0)
        ? data.cues
        : (data.micro_cues && data.micro_cues.length > 0)
        ? data.micro_cues
        : [];

      const cues = rawCues.map((c, i) => ({
        start: Number(c.start) || 0,
        end: Number(c.end) || 0,
        text: c.text || '',
        translation: c.translation || '',
        sfx: c.sfx || null,
        _uid: `cue-${i}-${Date.now().toString(36)}`,
      }));

      const fontName = data.font_name || data.render_params?.font_name || 'IBMPlex';
      const bgmName = data.bgm_name || data.render_params?.bgm_name || null;
      const lutName = data.lut_name || data.render_params?.lut_name || null;
      const stickerBadge = data.sticker_badge || data.render_params?.sticker_badge || null;
      const mixedAudio = data.artifacts?.mixed_audio?.path || null;
      setAudioUrl(mixedAudio ? toMediaUrl(mixedAudio) : null);
      const lutIntensity = data.render_params?.lut_intensity ?? 1;
      const bgmVolume = data.render_params?.bgm_volume ?? 0.12;
      const bgmDucking = !!data.render_params?.bgm_ducking;
      const captionPosition = data.render_params?.caption_position || 'bottom';
      const captionColor = data.render_params?.caption_color || '#FFFFFF';
      const captionScale = data.render_params?.caption_scale ?? 1;
      const stickerPosition = data.render_params?.sticker_position || 'top_right';
      const stickerScale = data.render_params?.sticker_scale ?? 1;
      loadedCaptionStyle.current = { captionPosition, captionColor, captionScale };
      // Baseline for "did the music change?" -- without this the first Apply
      // after loading would always take the slower re-mix path.
      loadedAudioStyle.current = { bgmName, bgmVolume, bgmDucking };

      reset({
        clipList: clips,
        cuesList: cues,
        style: {
          fontName,
          bgmName,
          lutName,
          lutIntensity,
          stickerBadge,
          bgmVolume,
          bgmDucking,
          captionPosition,
          captionColor,
          captionScale,
          stickerPosition,
          stickerScale,
        },
      });

      setAudioDuration(Number(data.audio_duration || data.total_duration) || 0);
      cuesDirty.current = false;
    } catch (err) {
      setLoadError(err.message || `โหลดโปรเจกต์ ${name} ไม่สำเร็จ`);
    } finally {
      setLoading(false);
    }
  };

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
    (silent ? setSilent : set)((prev) => ({
      ...prev,
      cuesList: prev.cuesList.map((c) => (c._uid === uid ? { ...c, ...patch } : c)),
    }));
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

  const selectedSeg = useMemo(
    () => (selection?.type === 'clip' ? segments.find((s) => s.clip.id === selection.id) || null : null),
    [selection, segments]
  );
  const selectedCaption = useMemo(
    () => (selection?.type === 'caption' ? cuesList.find((c) => c._uid === selection.id) || null : null),
    [selection, cuesList]
  );

  const splitAtPlayhead = () => {
    if (!selectedSeg) return;
    const seg = selectedSeg;
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
    const dup = { ...orig, id: newId() };
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
    }
  };

  // Editor keyboard verbs. The app-level useKeyboardShortcuts hook covers tab
  // switching and save; these are the timeline ones, and they stay off while
  // the caret is in a field so typing "s" types an s.
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
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

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

      const cue1 = { ...target, end: splitTime, text: text1 };
      const cue2 = { ...target, start: splitTime, text: text2, _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` };

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

      const cue1 = { ...target, end: Number(playheadTime.toFixed(2)), text: text1 };
      const cue2 = { ...target, start: Number(playheadTime.toFixed(2)), text: text2, _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` };

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

  // Render polling
  useEffect(() => {
    if (!jobId || !applying) return;
    const timer = setInterval(async () => {
      try {
        const st = await getRenderStatus(jobId);
        setJobStatus(st);
        if (st.status === 'done' || st.status === 'completed') {
          setApplying(false);
          setApplyResult(st.result || {});
          clearInterval(timer);
        } else if (st.status === 'failed') {
          setApplying(false);
          setApplyError(st.error || 'เรนเดอร์ล้มเหลว');
          clearInterval(timer);
        }
      } catch (err) { /* keep polling */ }
    }, 1000);
    return () => clearInterval(timer);
  }, [jobId, applying]);

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

    setApplying(true);
    setApplyError(null);
    setApplyResult(null);
    setJobStatus({ progress: 0.05, message: 'กำลังเตรียมข้อมูล...' });

    try {
      if (cuesDirty.current) {
        await updateProjectCues(projectName, { cues: cuesList.map(({ _uid, ...c }) => c) });
      }
      const res = await startReroll({
        project_name: projectName,
        part: audioDirty ? 'bgm' : ((cuesDirty.current || captionDirty) ? 'subtitles' : 'video'),
        clip_list: clipList.map(({ id, transition_in, transition_duration, ...c }) => c),
        transitions: clipList.slice(1).map((c) => ({
          type: c.transition_in || 'cut',
          duration: c.transition_duration ?? FADE_DURATION,
        })),
        font_name: style.fontName,
        bgm_name: style.bgmName,
        lut_name: style.lutName,
        // "" is meaningful here: it clears the badge stored on the project.
        sticker_badge: style.stickerBadge ?? '',
        lut_intensity: style.lutIntensity ?? 1,
        bgm_volume: style.bgmVolume ?? 0.12,
        bgm_ducking: !!style.bgmDucking,
        export_preset: exportPreset,
        caption_position: style.captionPosition || 'bottom',
        caption_color: style.captionColor || '#FFFFFF',
        caption_scale: style.captionScale ?? 1,
        sticker_position: style.stickerPosition || 'top_right',
        sticker_scale: style.stickerScale ?? 1,
      });
      setJobId(res.job_id);
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
      setApplying(false);
      setApplyError(err.response?.data?.detail || err.message || 'เริ่มเรนเดอร์ไม่สำเร็จ');
    }
  };

  const progress = Math.round((jobStatus?.progress || 0) * 100);
  const bgmLabel = useMemo(() => {
    if (!style.bgmName) return 'เสียงหลักของช่อง';
    const found = assets.music?.find((m) => m.id === style.bgmName);
    return found ? found.label_th || found.name : style.bgmName;
  }, [style.bgmName, assets.music]);

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
            <span className="flex-shrink-0 font-mono text-sm font-bold text-slate-400">
              <span className="text-[#E89274]">{formatTimecode(playhead)}</span>
              <span className="hidden sm:inline"> / {formatTimecode(Math.max(totalDuration, audioDuration))}</span>
            </span>
          )}
        </div>

        {/* Right: Fullscreen & Apply / Render Buttons */}
        <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
          <button
            type="button"
            onClick={() => setZen((v) => !v)}
            disabled={!projectName}
            title={zen ? 'กลับไปหน้าตัดต่อ (Esc)' : 'ขยายพรีวิวเต็มพื้นที่'}
            className="hidden sm:flex h-9 items-center gap-1 px-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white border border-white/[0.08] text-xs font-bold cursor-pointer transition-colors disabled:opacity-40"
          >
            {zen ? <><Minimize2 className="h-3.5 w-3.5" /> ย่อ</> : <><Maximize2 className="h-3.5 w-3.5" /> ขยาย</>}
          </button>

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
                // the bar's own zen button is hidden below sm, so the menu is
                // the only way to reach it on a narrow window
                id: 'zen',
                label: zen ? 'ย่อพรีวิวกลับ' : 'ขยายพรีวิวเต็มพื้นที่',
                icon: zen ? Minimize2 : Maximize2,
                disabled: !projectName,
                onSelect: () => setZen((v) => !v),
              },
              {
                id: 'reload',
                label: loading ? 'กำลังโหลด...' : 'โหลดโปรเจกต์ใหม่',
                icon: loading ? Loader2 : RefreshCw,
                disabled: !projectName || loading,
                onSelect: () => loadProject(projectName),
              },
              {
                id: 'scale',
                hint: 'ขนาดตัวอักษรทั้งระบบ',
                render: () => <UiScaleControl variant="menu" />,
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
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
            onClick={() => !deleting && setPendingDelete(null)}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-label="ยืนยันการลบโปรเจกต์"
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md space-y-4 rounded-2xl border border-white/[0.1] bg-[#0F1420] p-5 shadow-2xl"
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

      {!projectName ? (
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
          {/* ══════════════════════════════════════════════════════════
              📱 MOBILE LAYOUT (< md breakpoint) - CapCut Mobile UX
             ══════════════════════════════════════════════════════════ */}
          <div ref={mobileWrapRef} className="md:hidden flex flex-col flex-1 min-h-0 overflow-hidden bg-[#07090E]">
            {/* Top: 9:16 Video Player Preview (Expands to fill top area, zero wasted space) */}
            <div
              className="relative flex w-full flex-shrink-0 flex-col items-center justify-center bg-black/60 p-2"
              style={{ height: mobilePreviewH }}
            >
              <SequencePlayer
                ref={mobilePlayerRef}
                clips={clipList}
                cues={cuesList}
                captionStyle={{
                  captionPosition: style.captionPosition,
                  captionColor: style.captionColor,
                  captionScale: style.captionScale,
                }}
                compact
                onPlayhead={setPlayhead}
                onDurations={setDurations}
              />
              {applying && (
                <div className="absolute bottom-2 left-4 right-4 bg-black/80 backdrop-blur-md p-2 rounded-xl border border-white/[0.1] space-y-1 z-10">
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300" style={{ width: `${Math.max(5, progress)}%` }} />
                  </div>
                  <p className="text-center text-sm text-[#25F4EE] font-bold">{jobStatus?.message || `กำลังเรนเดอร์ ${progress}%`}</p>
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
              /* TAB 1: TIMELINE (Compact fixed height, perfect snug fit with no empty black void) */
              <div className="flex-shrink-0 h-[215px] flex flex-col border-t border-white/[0.08] bg-[#0F1420]">
                <Toolbar
                  hasClipSelected={!!selectedSeg}
                  hasSelection={!!selection}
                  selectedClip={selectedSeg?.clip}
                  canUndo={canUndo}
                  canRedo={canRedo}
                  onUndo={undo}
                  onRedo={redo}
                  onSplit={splitAtPlayhead}
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
                    onSelect={setSelection}
                    onSeek={seekPlayer}
                    onClipChange={patchClip}
                    onCaptionChange={patchCaption}
                    onReorder={reorderClip}
                    onReorderSilent={(id, dir) => reorderClip(id, dir, true)}
                    onDropClip={addClip}
                    audioUrl={audioUrl}
                    onBeginDrag={beginDrag}
                    onEndDrag={endDrag}
                    snapCandidates={snapEnabled ? snapCandidates(segments, playhead, audioDuration > 0 ? [audioDuration] : []) : []}
                    snapFunction={snapEnabled ? (t, c) => snapTime(t, c, SNAP_PX / pxPerSec) : (t) => t}
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
                      assets={assets}
                      style={style}
                      selectedCaption={selectedCaption}
                      onAddClip={addClip}
                      onStyleChange={(patch) => set((prev) => ({ ...prev, style: { ...prev.style, ...patch } }))}
                      onAssignSfx={(sfxId) => selectedCaption && patchCaption(selectedCaption._uid, { sfx: sfxId })}
                      onImportCues={handleImportCues}
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
                      onClipChange={(patch) => selectedSeg && patchClip(selectedSeg.clip.id, patch)}
                      onCaptionChange={(cueUid, patch) => patchCaption(cueUid, patch)}
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
                      onSelectCue={(uid) => setSelection({ type: 'caption', id: uid })}
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ══════════════════════════════════════════════════════════
              🖥️ DESKTOP PRO LAYOUT (>= md breakpoint) - 3 Columns
             ══════════════════════════════════════════════════════════ */}
          <div className="hidden md:flex flex-col flex-1 min-h-0">
            {/* Middle Row (AssetPanel + Video + Inspector) */}
            <div className="flex min-h-0 flex-1">
              {!zen && (
                <div className="w-[240px] flex-shrink-0 border-r border-white/[0.08]">
                  <AssetPanel
                    videos={videos}
                    clipList={clipList}
                    assets={assets}
                    style={style}
                    selectedCaption={selectedCaption}
                    onAddClip={addClip}
                    onStyleChange={(patch) => set((prev) => ({ ...prev, style: { ...prev.style, ...patch } }))}
                    onAssignSfx={(sfxId) => selectedCaption && patchCaption(selectedCaption._uid, { sfx: sfxId })}
                    onImportCues={handleImportCues}
                  />
                </div>
              )}

              {/* Center: SequencePlayer */}
              <div className="flex min-h-0 flex-1 flex-col items-center gap-2 overflow-hidden p-3 bg-black/40">
                <SequencePlayer
                  ref={desktopPlayerRef}
                  clips={clipList}
                  cues={cuesList}
                captionStyle={{
                  captionPosition: style.captionPosition,
                  captionColor: style.captionColor,
                  captionScale: style.captionScale,
                }}
                  compact
                  onPlayhead={setPlayhead}
                  onDurations={setDurations}
                />
                {applying && (
                  <div className="w-full max-w-[260px] flex-shrink-0">
                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                      <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300" style={{ width: `${Math.max(5, progress)}%` }} />
                    </div>
                    <p className="pt-1 text-center text-sm text-slate-400">{jobStatus?.message}</p>
                  </div>
                )}
                {applyError && (
                  <p className="flex flex-shrink-0 items-center gap-1 text-sm text-rose-300">
                    <AlertCircle className="h-3 w-3" />{applyError}
                  </p>
                )}
                {applyResult && (
                  <p className="flex flex-shrink-0 items-center gap-1 text-sm text-emerald-300 font-bold">
                    <CheckCircle2 className="h-3 w-3" />เรนเดอร์เสร็จ — ดูไฟล์ได้ที่ Export Gallery
                  </p>
                )}
              </div>

              {!zen && (
                <div className="relative flex flex-shrink-0">
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
                    className="w-1.5 flex-shrink-0 cursor-col-resize touch-none bg-white/[0.08] transition-colors hover:bg-[#D97757]/60"
                  />
                  <div style={{ width: inspectorW }} className="flex-shrink-0 border-l border-white/[0.08]">
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
                    onClipChange={(patch) => selectedSeg && patchClip(selectedSeg.clip.id, patch)}
                    onCaptionChange={(cueUid, patch) => patchCaption(cueUid, patch)}
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
                    onSelectCue={(uid) => setSelection({ type: 'caption', id: uid })}
                  />
                  </div>
                </div>
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
                  onDoubleClick={() => applyTimelineH(TIMELINE_DEFAULT_H)}
                  className="group flex h-2 flex-shrink-0 cursor-ns-resize touch-none items-center justify-center bg-[#0F1420]"
                >
                  <span className="h-0.5 w-10 rounded-full bg-slate-600 transition-colors duration-150 group-hover:bg-[#25F4EE]" />
                </div>
                <Toolbar
                  hasClipSelected={!!selectedSeg}
                  hasSelection={!!selection}
                  selectedClip={selectedSeg?.clip}
                  canUndo={canUndo}
                  canRedo={canRedo}
                  onUndo={undo}
                  onRedo={redo}
                  onSplit={splitAtPlayhead}
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
                    onSelect={setSelection}
                    onSeek={seekPlayer}
                    onClipChange={patchClip}
                    onCaptionChange={patchCaption}
                    onReorder={reorderClip}
                    onReorderSilent={(id, dir) => reorderClip(id, dir, true)}
                    onDropClip={addClip}
                    audioUrl={audioUrl}
                    onBeginDrag={beginDrag}
                    onEndDrag={endDrag}
                    snapCandidates={snapEnabled ? snapCandidates(segments, playhead, audioDuration > 0 ? [audioDuration] : []) : []}
                    snapFunction={snapEnabled ? (t, c) => snapTime(t, c, SNAP_PX / pxPerSec) : (t) => t}
                  />
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
