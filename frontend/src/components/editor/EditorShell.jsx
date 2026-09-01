import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, AlertTriangle, CheckCircle2, Loader2, Maximize2, Minimize2, RefreshCw, Rocket, Scissors,
} from 'lucide-react';
import {
  getAllAssets, getProject, getProjects, getRenderStatus, startReroll, updateProjectCues,
} from '../../api';
import {
  ZOOM_LEVELS, buildSegments, formatTimecode, splitClipAt, snapCandidates, snapTime,
  totalDuration as totalDurationOf,
} from '../../lib/timelineMath';
import { useEditorHistory } from '../../hooks/useEditorHistory';
import SequencePlayer from '../SequencePlayer';
import AssetPanel from './AssetPanel';
import Inspector from './Inspector';
import Timeline from './Timeline';
import Toolbar from './Toolbar';

// Frames per strip scale with clip length so the filmstrip reads as frames
// rather than one stretched still: each frame is a separate ffmpeg seek, so
// this trades a few seconds of one-time cold render for legibility.
const framesFor = (seconds) => Math.max(6, Math.min(40, Math.round((seconds || 12) / 3)));
const SNAP_PX = 6;
const TIMELINE_MIN_H = 196;
const TIMELINE_MAX_H = 460;
const TIMELINE_DEFAULT_H = 212;

const EMPTY = { clipList: [], cuesList: [], style: { fontName: 'IBMPlex', bgmName: null, lutName: null, stickerBadge: null } };

let idCounter = 0;
const newId = () => `clip-${Date.now().toString(36)}-${++idCounter}`;

export default function EditorShell({ videos = [] }) {
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

  // How much of the pane the timeline gets. Fixed at 212px it starved the
  // preview on a 800px-tall window (canvas came out ~220px wide), so the
  // divider is draggable and the choice is remembered.
  const [timelineH, setTimelineH] = useState(() => {
    const saved = parseInt(localStorage.getItem('editor.timelineH') || '', 10);
    return Number.isFinite(saved) ? Math.min(TIMELINE_MAX_H, Math.max(TIMELINE_MIN_H, saved)) : TIMELINE_DEFAULT_H;
  });
  const resizeRef = useRef(null);

  // Even at the smallest timeline a 9:16 preview is only ~270px wide on a
  // 800px-tall screen. Zen hides the side panels and the timeline so the
  // frame can actually be looked at; Esc or the button brings them back.
  const [zen, setZen] = useState(false);

  // A render is minutes of CPU. If the clips are shorter than the voiceover
  // the tail comes out with sound and no picture (measured: 13.6s of video in
  // a 28.3s file), so Apply asks once instead of spending the time silently.
  const [confirmGap, setConfirmGap] = useState(0);

  const applyTimelineH = (px) => {
    const clamped = Math.min(TIMELINE_MAX_H, Math.max(TIMELINE_MIN_H, Math.round(px)));
    setTimelineH(clamped);
    try { localStorage.setItem('editor.timelineH', String(clamped)); } catch (err) { /* private mode */ }
  };

  const [applying, setApplying] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [applyError, setApplyError] = useState(null);
  const [applyResult, setApplyResult] = useState(null);

  const playerRef = useRef(null);
  const cuesDirty = useRef(false);

  const pxPerSec = ZOOM_LEVELS[zoomIndex];
  const segments = useMemo(() => buildSegments(clipList, durations), [clipList, durations]);
  const totalDuration = totalDurationOf(segments);
  const selectedSeg = selection?.type === 'clip' ? segments.find((s) => s.clip.id === selection.id) : null;
  const selectedCaption = selection?.type === 'caption' ? cuesList.find((c) => c._uid === selection.id) : null;

  const filmstrips = useMemo(() => {
    const out = {};
    clipList.forEach((c) => {
      const p = encodeURIComponent(c.source_path);
      const count = framesFor(durations[c.id]);
      out[c.id] = { url: `/api/editor/filmstrip?path=${p}&count=${count}` };
    });
    return out;
  }, [clipList, durations]);

  const bgmLabel = useMemo(() => {
    if (!style.bgmName) return '';
    const m = (assets.music || []).find((x) => x.id === style.bgmName);
    return m?.label_th || style.bgmName;
  }, [style.bgmName, assets.music]);

  // ── load ────────────────────────────────────────────────────────────
  useEffect(() => {
    getProjects().then((d) => setProjectList(d.projects || [])).catch(() => {});
    getAllAssets().then(setAssets).catch(() => {});
  }, []);

  const loadProject = useCallback(async (name) => {
    if (!name) return;
    setLoading(true);
    setLoadError(null);
    setApplyResult(null);
    setApplyError(null);
    setSelection(null);
    setPlayhead(0);
    cuesDirty.current = false;
    try {
      const data = await getProject(name);
      const rp = data.render_params || {};
      const savedTransitions = rp.transitions || [];

      let clips = [];
      if (rp.clip_list?.length) {
        clips = rp.clip_list.map((c, i) => ({
          id: newId(),
          transition_in: i === 0 ? 'cut' : (savedTransitions[i - 1] || 'cut'),
          ...c,
        }));
      } else if (rp.raw_video_path) {
        clips = [{ id: newId(), source_path: rp.raw_video_path, trim_start: 0, trim_end: null, transition_in: 'cut' }];
      }

      setProjectName(name);
      setAudioDuration(data.total_duration || 0);
      setDurations({});
      reset({
        clipList: clips,
        cuesList: (data.cues || []).map((c, i) => ({ ...c, _uid: `cue-${i}-${Date.now().toString(36)}` })),
        style: {
          fontName: rp.font_name || 'IBMPlex',
          bgmName: rp.bgm_name || null,
          lutName: rp.lut_name || null,
          stickerBadge: rp.sticker_badge || null,
        },
      });
    } catch (err) {
      setLoadError(err.response?.data?.detail || err.message || 'โหลดโปรเจกต์ไม่สำเร็จ');
    } finally {
      setLoading(false);
    }
  }, [reset]);

  // ── clip / caption edits ────────────────────────────────────────────
  const patchClip = (id, patch, silent = false) => {
    const apply = (prev) => ({
      ...prev,
      clipList: prev.clipList.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    });
    (silent ? setSilent : set)(apply);
  };

  const addClip = (video) => {
    const id = newId();
    set((prev) => ({
      ...prev,
      clipList: [...prev.clipList, {
        id, source_path: video.path, trim_start: 0, trim_end: null, transition_in: 'cut',
      }],
    }));
    setSelection({ type: 'clip', id });
  };

  const duplicateSelected = () => {
    if (!selectedSeg) return;
    const id = newId();
    set((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === selectedSeg.clip.id);
      const copy = { ...prev.clipList[idx], id };
      const next = [...prev.clipList];
      next.splice(idx + 1, 0, copy);
      return { ...prev, clipList: next };
    });
    setSelection({ type: 'clip', id });
  };

  const splitAtPlayhead = () => {
    const seg = segments.find((s) => playhead > s.segStart && playhead < s.segEnd);
    if (!seg) return;
    const parts = splitClipAt(seg, playhead, newId);
    if (!parts) return;
    set((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === seg.clip.id);
      if (idx === -1) return prev;
      const next = [...prev.clipList];
      next.splice(idx, 1, ...parts);
      return { ...prev, clipList: next };
    });
    setSelection({ type: 'clip', id: parts[1].id });
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
        _uid: `cue-${i}-${Date.now().toString(36)}`
      }))
    }));
  }, [set]);

  const reorderClip = (id, direction, silent = false) => {
    (silent ? setSilent : set)((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === id);
      const target = idx + direction;
      if (idx === -1 || target < 0 || target >= prev.clipList.length) return prev;
      const next = [...prev.clipList];
      [next[idx], next[target]] = [next[target], next[idx]];
      return { ...prev, clipList: next };
    });
  };

  const patchCaption = (uid, patch, silent = false) => {
    cuesDirty.current = true;
    const apply = (prev) => ({
      ...prev,
      cuesList: prev.cuesList.map((c) => (c._uid === uid ? { ...c, ...patch } : c)),
    });
    (silent ? setSilent : set)(apply);
  };

  const seek = (t) => {
    const clamped = Math.max(0, Math.min(Math.max(totalDuration, audioDuration), t));
    const snapped = snapEnabled
      ? snapTime(clamped, snapCandidates(segments, clamped), SNAP_PX / pxPerSec)
      : clamped;
    setPlayhead(snapped);
    playerRef.current?.seekTo(snapped);
  };

  // ── keyboard ────────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        e.shiftKey ? redo() : undo();
        return;
      }
      if (mod && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); return; }
      if (e.key === 'Escape' && zen) { e.preventDefault(); setZen(false); return; }

      switch (e.key) {
        case ' ':
          e.preventDefault();
          playerRef.current?.toggle();
          break;
        case 's': case 'S':
          e.preventDefault(); splitAtPlayhead(); break;
        case 'Delete': case 'Backspace':
          e.preventDefault(); deleteSelected(); break;
        case 'ArrowLeft':
          e.preventDefault(); seek(playhead - (e.shiftKey ? 1 : 1 / 30)); break;
        case 'ArrowRight':
          e.preventDefault(); seek(playhead + (e.shiftKey ? 1 : 1 / 30)); break;
        case '+': case '=':
          e.preventDefault(); setZoomIndex((i) => Math.min(ZOOM_LEVELS.length - 1, i + 1)); break;
        case '-': case '_':
          e.preventDefault(); setZoomIndex((i) => Math.max(0, i - 1)); break;
        case 'f': case 'F':
          if (selectedSeg && selectedSeg.index > 0) {
            e.preventDefault();
            patchClip(selectedSeg.clip.id, {
              transition_in: selectedSeg.clip.transition_in === 'fade' ? 'cut' : 'fade',
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

  // ── apply ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!jobId || !applying) return;
    const timer = setInterval(async () => {
      try {
        const st = await getRenderStatus(jobId);
        setJobStatus(st);
        if (st.status === 'completed') {
          setApplying(false);
          setApplyResult(st.result);
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

    const gap = (audioDuration || 0) - totalDuration;
    if (gap > 0.5 && !confirmGap) {
      setConfirmGap(gap);
      setApplyError(null);
      setTimeout(() => setConfirmGap(0), 8000);
      return;
    }
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
        // Caption edits need the subtitles stage (it cascades into video);
        // timeline-only changes get the cheaper video-only pass.
        part: cuesDirty.current ? 'subtitles' : 'video',
        clip_list: clipList.map(({ id, transition_in, ...c }) => c),
        transitions: clipList.slice(1).map((c) => c.transition_in || 'cut'),
        font_name: style.fontName,
        bgm_name: style.bgmName,
        lut_name: style.lutName,
      });
      setJobId(res.job_id);
      cuesDirty.current = false;
    } catch (err) {
      setApplying(false);
      setApplyError(err.response?.data?.detail || err.message || 'เริ่มเรนเดอร์ไม่สำเร็จ');
    }
  };

  const progress = Math.round((jobStatus?.progress || 0) * 100);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-[#363430] bg-[#181716]">
      {/* header */}
      <div className="flex flex-shrink-0 items-center gap-2 border-b border-[#363430] bg-[#232220] px-3 py-1.5">
        <Scissors className="h-4 w-4 flex-shrink-0 text-[#D97757]" />
        <span className="flex-shrink-0 text-[12px] font-semibold text-[#EDE9E3]">ตัดต่อมือ</span>

        <select
          value={projectName}
          onChange={(e) => loadProject(e.target.value)}
          className="claude-input ml-2 max-w-[260px] flex-1 px-2 py-1 text-[11px]"
        >
          <option value="">— เลือกโปรเจกต์ —</option>
          {projectList.map((p) => (
            <option key={p.project_name} value={p.project_name}>{p.project_name}</option>
          ))}
        </select>

        <button
          type="button"
          onClick={() => loadProject(projectName)}
          disabled={!projectName || loading}
          title="โหลดใหม่"
          className="claude-btn-secondary flex h-7 w-7 items-center justify-center disabled:opacity-40"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
        </button>

        <span className="ml-auto font-mono text-[11px] text-[#9C968F]">
          {formatTimecode(playhead)} / {formatTimecode(Math.max(totalDuration, audioDuration))}
        </span>

        <button
          type="button"
          onClick={() => setZen((v) => !v)}
          disabled={!projectName}
          title={zen ? 'กลับไปหน้าตัดต่อ (Esc)' : 'ขยายพรีวิวเต็มพื้นที่'}
          aria-pressed={zen}
          className="claude-btn-secondary flex h-7 items-center gap-1.5 px-2 text-[11px] disabled:opacity-40"
        >
          {zen
            ? <><Minimize2 className="h-3.5 w-3.5" />ย่อ</>
            : <><Maximize2 className="h-3.5 w-3.5" />ขยายพรีวิว</>}
        </button>

        <button
          type="button"
          onClick={handleApply}
          disabled={applying || !projectName}
          className="claude-btn-primary flex h-7 items-center gap-1.5 px-3 text-[11px] disabled:opacity-50"
        >
          {applying
            ? <><Loader2 className="h-3.5 w-3.5 animate-spin" />เรนเดอร์ {progress}%</>
            : confirmGap
              ? <><AlertTriangle className="h-3.5 w-3.5" />ท้ายคลิปไม่มีภาพ {confirmGap.toFixed(1)} วิ — กดอีกครั้งเพื่อเรนเดอร์</>
              : <><Rocket className="h-3.5 w-3.5" />Apply</>}
        </button>
      </div>

      {loadError && (
        <div className="flex flex-shrink-0 items-center gap-2 border-b border-[#5C2B26] bg-[#2E1D1B] px-3 py-1.5 text-[11px] text-[#E0A9A2]">
          <AlertCircle className="h-3.5 w-3.5" />{loadError}
        </div>
      )}

      {!projectName ? (
        <div className="flex flex-1 items-center justify-center p-8 text-center text-[12px] text-[#6B6660]">
          เลือกโปรเจกต์ที่ 1-Click Studio เรนเดอร์ไว้แล้ว เพื่อเริ่มตัดต่อ
        </div>
      ) : (
        <>
          {/* middle row */}
          <div className="flex min-h-0 flex-1">
            {!zen && (
            <div className="w-[240px] flex-shrink-0">
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

            <div className="flex min-h-0 flex-1 flex-col items-center gap-2 overflow-hidden p-3">
              <SequencePlayer
                ref={playerRef}
                clips={clipList}
                cues={cuesList}
                compact
                onPlayhead={setPlayhead}
                onDurations={setDurations}
              />
              {applying && (
                <div className="w-full max-w-[260px] flex-shrink-0">
                  <div className="h-1.5 overflow-hidden rounded-full bg-[#363430]">
                    <div className="h-full bg-[#D97757] transition-all duration-300" style={{ width: `${Math.max(5, progress)}%` }} />
                  </div>
                  <p className="pt-1 text-center text-[10px] text-[#9C968F]">{jobStatus?.message}</p>
                </div>
              )}
              {applyError && (
                <p className="flex flex-shrink-0 items-center gap-1 text-[10px] text-[#E0A9A2]">
                  <AlertCircle className="h-3 w-3" />{applyError}
                </p>
              )}
              {applyResult && (
                <p className="flex flex-shrink-0 items-center gap-1 text-[10px] text-[#8FBF9F]">
                  <CheckCircle2 className="h-3 w-3" />เรนเดอร์เสร็จ — ดูไฟล์ได้ที่ Export Gallery
                </p>
              )}
            </div>

            {!zen && (
            <div className="w-[280px] flex-shrink-0">
              <Inspector
                selection={selection}
                selectedSeg={selectedSeg}
                selectedCaption={selectedCaption}
                style={style}
                totalDuration={totalDuration}
                audioDuration={audioDuration}
                onClipChange={(patch) => selectedSeg && patchClip(selectedSeg.clip.id, patch)}
                onCaptionChange={(patch) => selectedCaption && patchCaption(selectedCaption._uid, patch)}
              />
            </div>
            )}
          </div>

          {/* timeline -- drag the grip to trade height with the preview,
              double-click it to go back to the default */}
          {!zen && (
          <div
            className="flex flex-shrink-0 flex-col border-t border-[#363430]"
            style={{ height: timelineH }}
          >
            <div
              role="separator"
              aria-orientation="horizontal"
              aria-label="ปรับความสูงไทม์ไลน์"
              title="ลากขึ้น-ลงเพื่อปรับความสูงไทม์ไลน์ · ดับเบิลคลิกเพื่อรีเซ็ต"
              onPointerDown={(e) => {
                resizeRef.current = { startY: e.clientY, startH: timelineH };
                try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag still works */ }
              }}
              onPointerMove={(e) => {
                const d = resizeRef.current;
                if (!d) return;
                applyTimelineH(d.startH - (e.clientY - d.startY));
              }}
              onPointerUp={(e) => {
                resizeRef.current = null;
                try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
              }}
              onDoubleClick={() => applyTimelineH(TIMELINE_DEFAULT_H)}
              className="group flex h-2 flex-shrink-0 cursor-ns-resize touch-none items-center justify-center bg-[#1C1B19]"
            >
              <span className="h-0.5 w-10 rounded-full bg-[#4A4742] transition-colors duration-150 group-hover:bg-[#D97757]" />
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
                onSeek={seek}
                onSelectClip={(id) => setSelection({ type: 'clip', id })}
                onSelectCaption={(id) => setSelection({ type: 'caption', id })}
                onTrim={(id, patch) => patchClip(id, patch, true)}
                onTrimBegin={beginDrag}
                onTrimEnd={endDrag}
                onToggleTransition={(id) => {
                  const seg = segments.find((s) => s.clip.id === id);
                  patchClip(id, { transition_in: seg?.clip.transition_in === 'fade' ? 'cut' : 'fade' });
                }}
                onCaptionShift={(uid, patch) => patchCaption(uid, patch, true)}
                onReorder={reorderClip}
                onReorderSilent={(id, dir) => reorderClip(id, dir, true)}
              />
            </div>
          </div>
          )}
        </>
      )}
    </div>
  );
}
