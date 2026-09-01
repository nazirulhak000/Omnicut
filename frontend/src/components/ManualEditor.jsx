import React, { useState, useEffect } from 'react';
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
  FolderOpen, RefreshCw, Clapperboard
} from 'lucide-react';
import {
  getProjects, getProject, updateProjectCues, startReroll, getRenderStatus, getAllAssets
} from '../api';

function SortableClipRow({ clip, index, onChange, onRemove }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: clip.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  const fileName = (clip.source_path || '').split('\\').pop()?.split('/').pop() || clip.source_path;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2.5 p-2.5 rounded-xl bg-black/40 border border-white/[0.08]"
    >
      <button
        {...attributes}
        {...listeners}
        className="text-slate-500 hover:text-slate-300 cursor-grab active:cursor-grabbing flex-shrink-0 touch-none"
        title="ลากเพื่อสลับลำดับ"
      >
        <GripVertical className="w-4 h-4" />
      </button>

      <span className="w-6 h-6 rounded-lg bg-[#25F4EE]/10 text-[#25F4EE] flex items-center justify-center text-[10px] font-bold flex-shrink-0">
        {index + 1}
      </span>

      <div className="flex-1 min-w-0">
        <div className="text-xs font-bold text-white truncate" title={clip.source_path}>{fileName}</div>
        <div className="flex items-center gap-2 mt-1">
          <label className="text-[9px] text-slate-500">เข้า(วิ)</label>
          <input
            type="number" step="0.1" min="0"
            value={clip.trim_start}
            onChange={(e) => onChange(clip.id, 'trim_start', parseFloat(e.target.value) || 0)}
            className="w-16 py-1 px-1.5 rounded-md bg-[#080B11] border border-white/[0.1] text-[10px] text-slate-100 font-mono focus:outline-none focus:border-[#25F4EE]/50"
          />
          <label className="text-[9px] text-slate-500">ออก(วิ)</label>
          <input
            type="number" step="0.1" min="0"
            value={clip.trim_end ?? ''}
            placeholder="สุดคลิป"
            onChange={(e) => onChange(clip.id, 'trim_end', e.target.value === '' ? null : parseFloat(e.target.value))}
            className="w-20 py-1 px-1.5 rounded-md bg-[#080B11] border border-white/[0.1] text-[10px] text-slate-100 font-mono placeholder:text-slate-600 focus:outline-none focus:border-[#25F4EE]/50"
          />
        </div>
      </div>

      <button
        onClick={() => onRemove(clip.id)}
        className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 flex-shrink-0 cursor-pointer"
        title="เอาออกจากไทม์ไลน์"
      >
        <Trash2 className="w-3.5 h-3.5" />
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
      if (existingClips && existingClips.length > 0) {
        setClipList(existingClips.map((c, i) => ({ id: `clip-${i}-${Date.now()}`, ...c })));
      } else if (rp.raw_video_path) {
        setClipList([{ id: `clip-0-${Date.now()}`, source_path: rp.raw_video_path, trim_start: 0, trim_end: null }]);
      } else {
        setClipList([]);
      }

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
    setClipList(prev => [...prev, {
      id: `clip-${prev.length}-${Date.now()}`,
      source_path: video.path,
      trim_start: 0,
      trim_end: null,
    }]);
  };

  const updateClip = (id, field, value) => {
    setClipList(prev => prev.map(c => (c.id === id ? { ...c, [field]: value } : c)));
  };

  const removeClip = (id) => {
    setClipList(prev => prev.filter(c => c.id !== id));
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

      const cleanClipList = clipList.map(({ id, ...c }) => c);
      // Editing captions requires the "subtitles" stage (it cascades to
      // "video" too, per REROLL_STAGE) so the burned .ass actually
      // reflects the edit; timeline-only changes are cheaper via "video".
      const part = cuesDirty ? 'subtitles' : 'video';

      const res = await startReroll({
        project_name: selectedProject,
        part,
        clip_list: cleanClipList,
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
              ปรับลำดับคลิป/ตัดต่อ + แก้คำบรรยาย สำหรับโปรเจกต์ที่ 1-Click Studio สร้างไว้แล้ว — MVP: ยังไม่มี transition/keyframe/color curve แบบ CapCut เต็มรูปแบบ
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

          {/* ── Middle: Timeline + Apply ── */}
          <div className="space-y-4">
            <div className="glass-card p-4 space-y-3">
              <h3 className="text-xs font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
                <Scissors className="w-3.5 h-3.5 text-[#FE2C55]" />
                ไทม์ไลน์ ({clipList.length} คลิป) — ลากเพื่อสลับลำดับ
              </h3>

              {clipList.length === 0 ? (
                <div className="text-[11px] text-slate-500 text-center py-6">คลิกวิดีโอจากคลังด้านซ้ายเพื่อเพิ่มเข้าไทม์ไลน์</div>
              ) : (
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                  <SortableContext items={clipList.map(c => c.id)} strategy={verticalListSortingStrategy}>
                    <div className="space-y-2">
                      {clipList.map((clip, idx) => (
                        <SortableClipRow
                          key={clip.id}
                          clip={clip}
                          index={idx}
                          onChange={updateClip}
                          onRemove={removeClip}
                        />
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
