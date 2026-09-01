import React, { useState, useEffect, useRef } from 'react';
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors
} from '@dnd-kit/core';
import {
  SortableContext, verticalListSortingStrategy, useSortable, arrayMove
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Scissors, Film, Plus, Trash2, GripVertical, Loader2, Rocket,
  CheckCircle2, AlertCircle, Type, Music, Palette, MessageSquare,
  FolderOpen, RefreshCw, Clapperboard, Waves, Eye
} from 'lucide-react';
import {
  getProjects, getProject, updateProjectCues, startReroll, getRenderStatus, getAllAssets
} from '../api';
import { toMediaUrl } from '../lib/mediaUrl';
import SequencePlayer from './SequencePlayer';

function SortableClipRow({ clip, index, isActive, onSelect, onRemove }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: clip.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  const fileName = (clip.source_path || '').split('\\').pop()?.split('/').pop() || clip.source_path;
  const trimLabel = `${clip.trim_start.toFixed(1)}s – ${clip.trim_end != null ? `${clip.trim_end.toFixed(1)}s` : 'สุดคลิป'}`;

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={() => onSelect(clip.id)}
      className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition-colors ${
        isActive ? 'bg-[#25F4EE]/10 border-[#25F4EE]/50' : 'bg-black/40 border-white/[0.08] hover:border-white/20'
      }`}
    >
      <button
        {...attributes}
        {...listeners}
        onClick={(e) => e.stopPropagation()}
        className="text-slate-500 hover:text-slate-300 cursor-grab active:cursor-grabbing flex-shrink-0 touch-none"
        title="ลากเพื่อสลับลำดับ"
      >
        <GripVertical className="w-4 h-4" />
      </button>

      <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
        isActive ? 'bg-[#25F4EE] text-slate-950' : 'bg-[#25F4EE]/10 text-[#25F4EE]'
      }`}>
        {index + 1}
      </span>

      <div className="flex-1 min-w-0">
        <div className="text-xs font-bold text-white truncate" title={clip.source_path}>{fileName}</div>
        <div className="text-[9px] text-slate-500 font-mono mt-0.5">{trimLabel}</div>
      </div>

      <button
        onClick={(e) => { e.stopPropagation(); onRemove(clip.id); }}
        className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 flex-shrink-0 cursor-pointer"
        title="เอาออกจากไทม์ไลน์"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

// Visual, frame-accurate trim -- click a clip in the timeline to load it
// here: real video preview + draggable in/out handles on a scrub bar,
// closer to how CapCut's trim actually feels than bare number boxes.
function ClipPreviewTrimmer({ clip, onChange }) {
  const videoRef = useRef(null);
  const trackRef = useRef(null);
  const draggingRef = useRef(null);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    setDuration(0);
  }, [clip.id]);

  const mediaUrl = toMediaUrl(clip.source_path);
  const trimEnd = clip.trim_end ?? duration;

  const timeFromClientX = (clientX) => {
    if (!trackRef.current || !duration) return 0;
    const rect = trackRef.current.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    return Math.round(ratio * duration * 10) / 10;
  };

  const onHandleDown = (which) => (e) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    draggingRef.current = which;
  };

  const onHandleUp = (e) => {
    draggingRef.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
  };

  const onHandleMove = (which) => (e) => {
    if (draggingRef.current !== which || !duration) return;
    const t = timeFromClientX(e.clientX);
    if (which === 'start') {
      const val = Math.max(0, Math.min(t, trimEnd - 0.2));
      onChange('trim_start', val);
      if (videoRef.current) videoRef.current.currentTime = val;
    } else {
      const clamped = Math.max(t, clip.trim_start + 0.2);
      const val = clamped >= duration - 0.1 ? null : clamped;
      onChange('trim_end', val);
      if (videoRef.current) videoRef.current.currentTime = val ?? Math.max(0, duration - 0.05);
    }
  };

  const pct = (t) => (duration ? `${Math.min(100, Math.max(0, (t / duration) * 100))}%` : '0%');

  return (
    <div className="space-y-2.5">
      <video
        key={clip.id}
        ref={videoRef}
        src={mediaUrl}
        controls
        playsInline
        onLoadedMetadata={(e) => setDuration(e.target.duration || 0)}
        className="w-full max-h-[320px] rounded-xl bg-black border border-white/10"
      />
      {duration > 0 ? (
        <div
          ref={trackRef}
          className="relative h-9 rounded-lg bg-black/60 border border-white/10 select-none"
        >
          <div
            className="absolute top-0 bottom-0 bg-[#25F4EE]/20 border-x-2 border-[#25F4EE] pointer-events-none"
            style={{ left: pct(clip.trim_start), right: `calc(100% - ${pct(trimEnd)})` }}
          />
          <div
            onPointerDown={onHandleDown('start')}
            onPointerMove={onHandleMove('start')}
            onPointerUp={onHandleUp}
            className="absolute top-0 bottom-0 w-4 -ml-2 bg-[#25F4EE] rounded cursor-ew-resize touch-none flex items-center justify-center"
            style={{ left: pct(clip.trim_start) }}
            title="ลากปรับจุดเริ่ม"
          >
            <div className="w-0.5 h-4 bg-slate-950/60" />
          </div>
          <div
            onPointerDown={onHandleDown('end')}
            onPointerMove={onHandleMove('end')}
            onPointerUp={onHandleUp}
            className="absolute top-0 bottom-0 w-4 -ml-2 bg-[#25F4EE] rounded cursor-ew-resize touch-none flex items-center justify-center"
            style={{ left: pct(trimEnd) }}
            title="ลากปรับจุดจบ"
          >
            <div className="w-0.5 h-4 bg-slate-950/60" />
          </div>
        </div>
      ) : (
        <div className="h-9 rounded-lg bg-black/40 border border-white/10 flex items-center justify-center text-[10px] text-slate-500">
          กำลังโหลดวิดีโอ...
        </div>
      )}
      <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
        <span>เข้า {clip.trim_start.toFixed(1)}s</span>
        <span className="text-[#25F4EE] font-bold">ยาว {duration ? (trimEnd - clip.trim_start).toFixed(1) : '…'}s</span>
        <span>ออก {duration ? trimEnd.toFixed(1) : '…'}s / {duration.toFixed(1)}s</span>
      </div>
    </div>
  );
}

function TransitionToggle({ value, onToggle }) {
  const isFade = value === 'fade';
  return (
    <div className="flex items-center justify-center py-0.5">
      <button
        onClick={onToggle}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-bold border transition-all cursor-pointer ${
          isFade
            ? 'bg-purple-500/15 text-purple-300 border-purple-500/40'
            : 'bg-white/[0.03] text-slate-500 border-white/[0.08] hover:text-slate-300'
        }`}
        title="สลับ cut / fade ระหว่าง 2 คลิปนี้"
      >
        {isFade ? <><Waves className="w-3 h-3" /> Fade 0.4s</> : <><Scissors className="w-3 h-3" /> Cut</>}
      </button>
    </div>
  );
}

export default function ManualEditor({ videos = [] }) {
  const [projectList, setProjectList] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [loadingProject, setLoadingProject] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const [clipList, setClipList] = useState([]);
  const [activeClipId, setActiveClipId] = useState(null);
  const [cuesList, setCuesList] = useState([]);
  const [cuesDirty, setCuesDirty] = useState(false);

  const [fontName, setFontName] = useState('IBMPlex');
  const [bgmName, setBgmName] = useState(null);
  const [lutName, setLutName] = useState(null);

  const [bgmOptions, setBgmOptions] = useState([]);
  const [lutOptions, setLutOptions] = useState([]);
  const [sfxOptions, setSfxOptions] = useState([]);

  const [applying, setApplying] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [applyError, setApplyError] = useState(null);
  const [applyResult, setApplyResult] = useState(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  useEffect(() => {
    getProjects().then(d => setProjectList(d.projects || [])).catch(() => {});
    getAllAssets().then(d => {
      setBgmOptions(d.music || []);
      setLutOptions(d.luts || []);
      setSfxOptions(d.sfx || []);
    }).catch(() => {});
  }, []);

  // Poll the reroll job the same way StudioStep4Render does.
  useEffect(() => {
    let interval = null;
    if (jobId && applying) {
      interval = setInterval(async () => {
        try {
          const st = await getRenderStatus(jobId);
          setJobStatus(st);
          if (st.status === 'completed') {
            setApplying(false);
            setApplyResult(st.result);
            clearInterval(interval);
          } else if (st.status === 'failed') {
            setApplying(false);
            setApplyError(st.error || 'เรนเดอร์ล้มเหลว');
            clearInterval(interval);
          }
        } catch (err) {
          console.error(err);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [jobId, applying]);

  const loadProject = async (name) => {
    if (!name) return;
    setLoadingProject(true);
    setLoadError(null);
    setApplyResult(null);
    setApplyError(null);
    try {
      const data = await getProject(name);
      setSelectedProject(name);
      const rp = data.render_params || {};

      const existingClips = rp.clip_list;
      const existingTransitions = rp.transitions || [];
      let seededClips = [];
      if (existingClips && existingClips.length > 0) {
        seededClips = existingClips.map((c, i) => ({
          id: `clip-${i}-${Date.now()}`,
          transition_in: i === 0 ? 'cut' : (existingTransitions[i - 1] || 'cut'),
          ...c,
        }));
      } else if (rp.raw_video_path) {
        seededClips = [{ id: `clip-0-${Date.now()}`, source_path: rp.raw_video_path, trim_start: 0, trim_end: null, transition_in: 'cut' }];
      }
      setClipList(seededClips);
      setActiveClipId(seededClips[0]?.id || null);

      setCuesList((data.cues || []).map((c, i) => ({ ...c, _uid: `cue-${i}-${Date.now()}` })));
      setCuesDirty(false);
      setFontName(rp.font_name || 'IBMPlex');
      setBgmName(rp.bgm_name || null);
      setLutName(rp.lut_name || null);
    } catch (err) {
      setLoadError('โหลดโปรเจกต์ไม่สำเร็จ: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoadingProject(false);
    }
  };

  const addClipFromBin = (video) => {
    const newId = `clip-${clipList.length}-${Date.now()}`;
    setClipList(prev => [...prev, {
      id: newId,
      source_path: video.path,
      trim_start: 0,
      trim_end: null,
      transition_in: 'cut',
    }]);
    setActiveClipId(newId);
  };

  const updateClip = (id, field, value) => {
    setClipList(prev => prev.map(c => (c.id === id ? { ...c, [field]: value } : c)));
  };

  const toggleTransition = (id) => {
    setClipList(prev => prev.map(c => (
      c.id === id ? { ...c, transition_in: c.transition_in === 'fade' ? 'cut' : 'fade' } : c
    )));
  };

  const removeClip = (id) => {
    setClipList(prev => {
      const next = prev.filter(c => c.id !== id);
      if (activeClipId === id) setActiveClipId(next[0]?.id || null);
      return next;
    });
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setClipList(prev => {
      const oldIndex = prev.findIndex(c => c.id === active.id);
      const newIndex = prev.findIndex(c => c.id === over.id);
      return arrayMove(prev, oldIndex, newIndex);
    });
  };

  const updateCue = (uid, field, value) => {
    setCuesList(prev => prev.map(c => (c._uid === uid ? { ...c, [field]: value } : c)));
    setCuesDirty(true);
  };

  const removeCue = (uid) => {
    setCuesList(prev => prev.filter(c => c._uid !== uid));
    setCuesDirty(true);
  };

  const handleApply = async () => {
    if (!selectedProject) {
      setApplyError('เลือกโปรเจกต์ก่อน');
      return;
    }
    if (clipList.length === 0) {
      setApplyError('เพิ่มอย่างน้อย 1 คลิปในไทม์ไลน์ก่อน');
      return;
    }

    setApplying(true);
    setApplyError(null);
    setApplyResult(null);
    setJobStatus({ progress: 0.05, message: 'กำลังเตรียมข้อมูล...' });

    try {
      if (cuesDirty) {
        await updateProjectCues(selectedProject, {
          cues: cuesList.map(({ _uid, ...c }) => c),
        });
      }

      const cleanClipList = clipList.map(({ id, transition_in, ...c }) => c);
      // One transition per boundary, i.e. clipList[1..].transition_in --
      // the first clip has no "before" boundary.
      const transitionsList = clipList.slice(1).map(c => c.transition_in || 'cut');
      // Editing captions requires the "subtitles" stage (it cascades to
      // "video" too, per REROLL_STAGE) so the burned .ass actually
      // reflects the edit; timeline-only changes are cheaper via "video".
      const part = cuesDirty ? 'subtitles' : 'video';

      const res = await startReroll({
        project_name: selectedProject,
        part,
        clip_list: cleanClipList,
        transitions: transitionsList,
        font_name: fontName,
        bgm_name: bgmName,
        lut_name: lutName,
      });
      setJobId(res.job_id);
      setCuesDirty(false);
    } catch (err) {
      setApplying(false);
      setApplyError(err.response?.data?.detail || err.message || 'เริ่มเรนเดอร์ไม่สำเร็จ');
    }
  };

  const progressPercent = Math.round((jobStatus?.progress || 0) * 100);
  const selectClass = "w-full py-2 px-3 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-xs focus:outline-none focus:border-[#25F4EE]/50 transition-colors shadow-inner";
  const activeClip = clipList.find(c => c.id === activeClipId) || null;

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 sm:p-6 glass-panel border border-white/10 shadow-2xl">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#FE2C55] via-[#FF0050] to-[#25F4EE] flex items-center justify-center shadow-lg shadow-[#FE2C55]/30 flex-shrink-0">
            <Scissors className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-black font-kanit text-white">
              ตัดต่อมือ (Manual Editor)
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 font-prompt mt-0.5">
พรีวิววิดีโอ ลากตัดต้น-จบ สลับลำดับ ใส่ fade + แก้คำบรรยาย สำหรับโปรเจกต์ที่ 1-Click Studio สร้างไว้แล้ว — MVP: ยังไม่มี keyframe/color curve แบบ CapCut เต็มรูปแบบ
            </p>
          </div>
        </div>

        {/* Project picker */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={selectedProject}
            onChange={(e) => loadProject(e.target.value)}
            className="flex-1 md:w-64 py-2.5 px-3.5 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-xs focus:outline-none focus:border-[#25F4EE]"
          >
            <option value="">— เลือกโปรเจกต์ —</option>
            {projectList.map((p) => (
              <option key={p.project_name} value={p.project_name}>
                {p.project_name}{p.product_name ? ` (${p.product_name})` : ''}
              </option>
            ))}
          </select>
          <button
            onClick={() => loadProject(selectedProject)}
            disabled={!selectedProject || loadingProject}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer disabled:opacity-40"
            title="โหลด/รีเฟรชโปรเจกต์"
          >
            {loadingProject ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {loadError && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{loadError}</span>
        </div>
      )}

      {!selectedProject ? (
        <div className="glass-card p-10 text-center text-slate-400 text-sm">
          <Clapperboard className="w-10 h-10 mx-auto mb-3 text-slate-600" />
          เลือกโปรเจกต์ที่ render ผ่าน 1-Click Studio มาแล้วอย่างน้อย 1 ครั้ง เพื่อเริ่มปรับลำดับคลิป/แก้คำบรรยาย
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr_300px] gap-4">
          {/* ── Left: Media Bin ── */}
          <div className="glass-card p-4 space-y-3">
            <h3 className="text-xs font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
              <FolderOpen className="w-3.5 h-3.5 text-[#25F4EE]" />
              คลังวิดีโอ (Media Bin)
            </h3>
            <div className="space-y-1.5 max-h-[500px] overflow-y-auto pr-1">
              {videos.map((v) => (
                <button
                  key={v.path}
                  onClick={() => addClipFromBin(v)}
                  className="w-full flex items-center gap-2 p-2 rounded-xl bg-white/[0.02] hover:bg-[#25F4EE]/10 border border-white/[0.06] hover:border-[#25F4EE]/40 text-left transition-all cursor-pointer group"
                >
                  <Film className="w-3.5 h-3.5 text-slate-500 group-hover:text-[#25F4EE] flex-shrink-0" />
                  <span className="text-[11px] text-slate-300 group-hover:text-white truncate flex-1">{v.name}</span>
                  <Plus className="w-3.5 h-3.5 text-slate-600 group-hover:text-[#25F4EE] flex-shrink-0" />
                </button>
              ))}
              {videos.length === 0 && (
                <div className="text-[11px] text-slate-500 text-center py-4">ยังไม่มีวิดีโอในระบบ — อัปโหลดที่ tab 1-Click Studio ก่อน</div>
              )}
            </div>
          </div>

          {/* ── Middle: Sequence Preview + Trim + Timeline + Apply ── */}
          <div className="space-y-4">
            {clipList.length > 0 && (
              <div className="glass-card p-4 space-y-3">
                <h3 className="text-xs font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
                  <Eye className="w-3.5 h-3.5 text-[#25F4EE]" />
                  ดูรวมทั้งไทม์ไลน์ ({clipList.length} คลิปต่อกัน)
                </h3>
                <SequencePlayer clips={clipList} cues={cuesList} />
              </div>
            )}

            {activeClip && (
              <div className="glass-card p-4 space-y-3">
                <h3 className="text-xs font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
                  <Film className="w-3.5 h-3.5 text-[#25F4EE]" />
                  ตัดคลิป (คลิปที่ {clipList.findIndex(c => c.id === activeClipId) + 1})
                </h3>
                <ClipPreviewTrimmer
                  clip={activeClip}
                  onChange={(field, value) => updateClip(activeClip.id, field, value)}
                />
              </div>
            )}

            <div className="glass-card p-4 space-y-3">
              <h3 className="text-xs font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
                <Scissors className="w-3.5 h-3.5 text-[#FE2C55]" />
                ไทม์ไลน์ ({clipList.length} คลิป) — คลิกเพื่อเลือก/ลากเพื่อสลับลำดับ
              </h3>

              {clipList.length === 0 ? (
                <div className="text-[11px] text-slate-500 text-center py-6">คลิกวิดีโอจากคลังด้านซ้ายเพื่อเพิ่มเข้าไทม์ไลน์</div>
              ) : (
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                  <SortableContext items={clipList.map(c => c.id)} strategy={verticalListSortingStrategy}>
                    <div className="space-y-0.5">
                      {clipList.map((clip, idx) => (
                        <React.Fragment key={clip.id}>
                          {idx > 0 && (
                            <TransitionToggle
                              value={clip.transition_in || 'cut'}
                              onToggle={() => toggleTransition(clip.id)}
                            />
                          )}
                          <SortableClipRow
                            clip={clip}
                            index={idx}
                            isActive={clip.id === activeClipId}
                            onSelect={setActiveClipId}
                            onRemove={removeClip}
                          />
                        </React.Fragment>
                      ))}
                    </div>
                  </SortableContext>
                </DndContext>
              )}
            </div>

            {/* Apply button */}
            <div className="glass-card p-4 space-y-3">
              <button
                onClick={handleApply}
                disabled={applying}
                className={`w-full py-3.5 px-5 rounded-2xl font-extrabold text-sm flex items-center justify-center gap-2.5 transition-all shadow-xl cursor-pointer ${
                  applying
                    ? 'bg-slate-800 text-slate-400 cursor-not-allowed border border-white/5'
                    : 'bg-gradient-to-r from-[#FE2C55] via-[#FF0050] to-[#25F4EE] text-white hover:opacity-95 active:scale-[0.99]'
                }`}
              >
                {applying ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>กำลังเรนเดอร์... ({progressPercent}%)</span>
                  </>
                ) : (
                  <>
                    <Rocket className="w-5 h-5" />
                    <span>Apply — เรนเดอร์จริงตามไทม์ไลน์นี้</span>
                  </>
                )}
              </button>
              <p className="text-[10px] text-slate-500 text-center">
                พรีวิวแบบ ffmpeg จริง (ไม่ใช่ real-time) — เครื่องนี้ไม่มีการ์ดจอ ต้องรอเรนเดอร์จริงทุกครั้งที่กด Apply
              </p>

              {applying && (
                <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300"
                    style={{ width: `${Math.max(5, progressPercent)}%` }}
                  />
                </div>
              )}

              {applyError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{applyError}</span>
                </div>
              )}

              {applyResult && (
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-2.5">
                  <div className="flex items-center gap-2 text-emerald-300 font-bold text-xs">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>เรนเดอร์เสร็จแล้ว!</span>
                  </div>
                  {applyResult.video_url && (
                    <video
                      src={`${applyResult.video_url}?t=${Date.now()}`}
                      controls
                      playsInline
                      className="w-full max-w-[180px] mx-auto rounded-xl bg-black border border-white/10"
                    />
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── Right: Inspector + Captions ── */}
          <div className="space-y-4">
            <div className="glass-card p-4 space-y-3">
              <h3 className="text-xs font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
                <Palette className="w-3.5 h-3.5 text-cyan-400" />
                สไตล์
              </h3>

              <div>
                <label className="block text-[10px] font-semibold text-slate-300 mb-1 flex items-center gap-1">
                  <Type className="w-3 h-3 text-[#25F4EE]" /> ฟอนต์ซับไตเติล
                </label>
                <select value={fontName} onChange={(e) => setFontName(e.target.value)} className={selectClass}>
                  <option value="IBMPlex">IBM Plex Sans Thai</option>
                  <option value="Kanit">Kanit</option>
                  <option value="Prompt">Prompt</option>
                  <option value="NotoSansThai">Noto Sans Thai</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-slate-300 mb-1 flex items-center gap-1">
                  <Music className="w-3 h-3 text-purple-400" /> BGM
                </label>
                <select value={bgmName || ''} onChange={(e) => setBgmName(e.target.value || null)} className={selectClass}>
                  <option value="">🎵 เสียงหลักของช่อง (ค่าเริ่มต้น)</option>
                  {bgmOptions.map((m) => (
                    <option key={m.id} value={m.id}>{m.label_th || m.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-slate-300 mb-1 flex items-center gap-1">
                  <Palette className="w-3 h-3 text-cyan-400" /> LUT (ไม่บังคับ)
                </label>
                <select
                  value={lutName || ''}
                  onChange={(e) => setLutName(e.target.value || null)}
                  className={selectClass}
                  title="เครื่องนี้ไม่มีการ์ดจอ — ใส่ LUT ช้าลง ~90%"
                >
                  <option value="">⚪ ไม่ใช้ (เร็วกว่า)</option>
                  {lutOptions.map((l) => (
                    <option key={l.id} value={l.id}>{l.name.replace(/\.cube$/i, '')}</option>
                  ))}
                </select>
                {lutName && <div className="text-[9px] text-amber-400 mt-1">⚠️ เรนเดอร์ช้าลง ~90% บนเครื่องนี้</div>}
              </div>

              <p className="text-[9px] text-slate-500 pt-1 border-t border-white/5">
                หมายเหตุ: ป้ายสติกเกอร์ยังปรับจากที่นี่ไม่ได้ในเวอร์ชันนี้ — ใช้ตามที่ตั้งไว้ตอน render ครั้งแรก
              </p>
            </div>

            <div className="glass-card p-4 space-y-3">
              <h3 className="text-xs font-bold text-white flex items-center justify-between pb-2 border-b border-white/10">
                <span className="flex items-center gap-2">
                  <MessageSquare className="w-3.5 h-3.5 text-amber-400" />
                  คำบรรยาย ({cuesList.length})
                </span>
                {cuesDirty && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-bold">แก้ไขแล้ว</span>
                )}
              </h3>
              <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                {cuesList.map((cue) => (
                  <div key={cue._uid} className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      <input
                        type="number" step="0.1"
                        value={cue.start}
                        onChange={(e) => updateCue(cue._uid, 'start', parseFloat(e.target.value) || 0)}
                        className="w-14 py-1 px-1.5 rounded-md bg-[#080B11] border border-white/[0.1] text-[9px] text-slate-300 font-mono focus:outline-none"
                      />
                      <span className="text-[9px] text-slate-600">-</span>
                      <input
                        type="number" step="0.1"
                        value={cue.end}
                        onChange={(e) => updateCue(cue._uid, 'end', parseFloat(e.target.value) || 0)}
                        className="w-14 py-1 px-1.5 rounded-md bg-[#080B11] border border-white/[0.1] text-[9px] text-slate-300 font-mono focus:outline-none"
                      />
                      <select
                        value={cue.sfx || ''}
                        onChange={(e) => updateCue(cue._uid, 'sfx', e.target.value || null)}
                        className="flex-1 py-1 px-1.5 rounded-md bg-[#080B11] border border-white/[0.1] text-[9px] text-slate-300 focus:outline-none"
                      >
                        <option value="">🔇 ไม่มี SFX</option>
                        {sfxOptions.map((s) => (
                          <option key={s.id} value={s.id}>{s.label_th || s.name}</option>
                        ))}
                      </select>
                      <button
                        onClick={() => removeCue(cue._uid)}
                        className="p-1 text-slate-500 hover:text-red-400 cursor-pointer flex-shrink-0"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                    <textarea
                      value={cue.text}
                      onChange={(e) => updateCue(cue._uid, 'text', e.target.value)}
                      rows={2}
                      className="w-full py-1.5 px-2 rounded-md bg-[#080B11] border border-white/[0.1] text-[11px] text-slate-100 resize-none focus:outline-none focus:border-[#25F4EE]/50"
                    />
                  </div>
                ))}
                {cuesList.length === 0 && (
                  <div className="text-[11px] text-slate-500 text-center py-4">โปรเจกต์นี้ยังไม่มี cue คำบรรยาย</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
