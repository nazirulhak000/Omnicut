import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, Trash2 } from 'lucide-react';

import SequencePlayer from '../../SequencePlayer.jsx';
import Timeline from '../../editor/Timeline.jsx';
import { buildSegments, totalDuration as totalDurationOf } from '../../../lib/timelineMath.js';
import { timelineWithClips } from '../../../lib/gadgetMediaProject.js';
import { projectWatermark } from '../../../lib/channelIdentity.js';
import { useGadgetDraft } from '../useGadgetDraft.js';


export default function GadgetMediaTimelineHost({ timeline, onSave, saving = false, channelId = 'main', channelIdentitySnapshot = null }) {
  const [working, setWorking] = useState(timeline);
  const draftParticipant = useGadgetDraft(working, { reset: setWorking, save: () => onSave(working) });
  useEffect(() => {
    if (draftParticipant.acceptExternal(timeline)) setWorking(timeline);
  }, [timeline, draftParticipant]);
  const [durations, setDurations] = useState({});
  const [playhead, setPlayhead] = useState(0);
  const [selection, setSelection] = useState(null);
  const playerRef = useRef(null);
  const viewportRef = useRef(null);
  const clips = useMemo(() => working?.clips || [], [working]);
  const segments = useMemo(() => buildSegments(clips, durations), [clips, durations]);
  const totalDuration = totalDurationOf(segments);

  const setClips = (nextClips) => setWorking((current) => timelineWithClips(current, nextClips));
  const patchClip = (id, patch) => setClips(clips.map((clip) => (clip.id === id ? { ...clip, ...patch } : clip)));
  const reorderClip = (id, direction) => {
    const from = clips.findIndex((clip) => clip.id === id);
    const to = Math.max(0, Math.min(clips.length - 1, from + direction));
    if (from < 0 || from === to) return;
    const next = [...clips];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    setClips(next);
  };
  const deleteClip = (id) => {
    setClips(clips.filter((clip) => clip.id !== id));
    setSelection((current) => (current?.id === id ? null : current));
  };
  const splitSelected = () => {
    if (selection?.type !== 'clip') return;
    const segment = segments.find((item) => item.clip.id === selection.id);
    if (!segment || playhead <= segment.segStart + 0.2 || playhead >= segment.segEnd - 0.2) return;
    const clip = segment.clip;
    const sourceSplit = Number(clip.trim_start || 0) + (playhead - segment.segStart) * Number(clip.speed || 1);
    const next = [];
    clips.forEach((item) => {
      if (item.id !== clip.id) {
        next.push(item);
        return;
      }
      next.push({ ...item, trim_end: sourceSplit });
      next.push({ ...item, id: `${item.id}-b-${Date.now().toString(36)}`, trim_start: sourceSplit, transition_in: 'cut' });
    });
    setClips(next);
  };
  const seek = (time) => {
    setPlayhead(time);
    playerRef.current?.seek(time);
  };

  return (
    <div className="space-y-3">
      {(!channelIdentitySnapshot || projectWatermark(channelIdentitySnapshot, channelId) === null) && <p role="alert" className="text-xs text-amber-200">โปรเจกต์นี้ยังไม่มีตัวตนช่องที่บันทึกไว้ กรุณา Render ใหม่เพื่อบันทึกตัวตนก่อนตรวจ Preview</p>}
      <div className="grid gap-3 xl:grid-cols-[minmax(260px,340px)_minmax(0,1fr)]">
        <div className="rounded-2xl bg-black/35 p-3 ring-1 ring-white/[0.08]">
          <div className="mx-auto max-w-[285px]">
            <SequencePlayer
              channelId={channelId}
              channelIdentitySnapshot={channelIdentitySnapshot}
              ref={playerRef}
              clips={clips}
              cues={working?.cues || []}
              overlays={working?.overlays || []}
              compact
              onPlayhead={setPlayhead}
              onDurations={setDurations}
              selection={selection}
              onSelect={setSelection}
              captionStyle={{ captionPosition: 'bottom', captionColor: '#FFFFFF', captionScale: 1, fontName: 'IBMPlex' }}
              showWatermark
            />
          </div>
        </div>

        <div className="min-w-0 rounded-2xl bg-[#090D15] p-3 ring-1 ring-white/[0.08]">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3">
            <div>
              <h3 className="text-sm font-black text-white">ไทม์ไลน์คลิป</h3>
              <p className="mt-0.5 text-[11px] text-slate-500">ปรับช็อตและบันทึกการตัดต่อของโปรเจกต์นี้</p>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={splitSelected} disabled={selection?.type !== 'clip'} className="flex min-h-11 items-center gap-1.5 rounded-xl px-3 text-xs font-bold text-slate-200 ring-1 ring-white/[0.1] hover:bg-white/[0.06] disabled:opacity-40">แบ่งช็อต</button>
              <button type="button" onClick={() => draftParticipant.save()} disabled={saving || !clips.length} className="flex min-h-11 items-center gap-1.5 rounded-xl bg-cyan-300 px-3 text-xs font-black text-[#061116] disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />} บันทึก Timeline</button>
            </div>
          </div>
          <div ref={viewportRef} className="h-[350px] min-w-0 overflow-hidden rounded-xl bg-[#07090E] ring-1 ring-white/[0.06]">
            <Timeline
              segments={segments}
              totalDuration={totalDuration}
              audioDuration={0}
              cues={working?.cues || []}
              bgmLabel="Gadget Media"
              pxPerSec={25}
              playhead={playhead}
              selection={selection}
              onSelect={setSelection}
              onSeek={seek}
              onClipChange={patchClip}
              onReorder={reorderClip}
              onReorderSilent={reorderClip}
              onDelete={deleteClip}
              onCuesChange={() => {}}
              viewportRef={viewportRef}
              overlays={working?.overlays || []}
              snapEnabled
              dense
            />
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl bg-[#0B0F19] ring-1 ring-white/[0.08]">
        <table className="w-full min-w-[760px] text-left text-xs">
          <thead className="text-[10px] text-slate-500"><tr><th className="px-3 py-2.5">ช็อต</th><th>Source in</th><th>Source out</th><th>Speed</th><th>Story block</th><th className="pr-3 text-right">ลบ</th></tr></thead>
          <tbody className="divide-y divide-white/[0.06]">
            {clips.map((clip, index) => (
              <tr key={clip.id} className={selection?.id === clip.id ? 'bg-cyan-300/[0.06]' : ''}>
                <td className="px-3 py-2 font-bold text-white">{index + 1}. {clip.id}</td>
                <td><NumberInput value={clip.trim_start} onChange={(value) => patchClip(clip.id, { trim_start: value })} /></td>
                <td><NumberInput value={clip.trim_end} onChange={(value) => patchClip(clip.id, { trim_end: value })} /></td>
                <td><NumberInput value={clip.speed || 1} step="0.25" onChange={(value) => patchClip(clip.id, { speed: value })} /></td>
                <td className="max-w-[220px] truncate text-slate-400">{clip.story_block_id || '—'}</td>
                <td className="pr-3 text-right"><button type="button" onClick={() => deleteClip(clip.id)} aria-label={`ลบช็อต ${index + 1}`} className="rounded-lg p-2 text-rose-200/70 hover:bg-rose-500/10 hover:text-rose-100"><Trash2 className="h-4 w-4" /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function NumberInput({ value, onChange, step = '0.1' }) {
  return <input type="number" min="0" step={step} value={value ?? 0} onChange={(event) => onChange(Number(event.target.value))} className="h-8 w-20 rounded-lg bg-black/25 px-2 text-xs text-white outline-none ring-1 ring-white/[0.1] focus:ring-cyan-300/70" />;
}
