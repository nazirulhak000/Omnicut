import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import ClipInspector from './components/editor/inspector/ClipInspector.jsx';
import Inspector from './components/editor/Inspector.jsx';
import Timeline from './components/editor/Timeline.jsx';
import { CLIP_DRAG_TYPE } from './components/editor/AssetPanel.jsx';
import SequencePlayer from './components/SequencePlayer.jsx';
import { useEditorHistory } from './hooks/useEditorHistory.js';
import { editorStateToSavePayload, manifestToEditorState } from './lib/editorProjectState.js';
import { buildSegments, snapTime, splitClipAt, totalDuration } from './lib/timelineMath.js';

const initialClip = {
  id: 'audit-clip', source_path: 'fixture.mp4',
  trim_start: 0, trim_end: 3, speed: 1, zoom: 1, volume: 0.5,
};
const requestedClipCount = Math.min(100, Math.max(1, Number(new URLSearchParams(window.location.search).get('clipCount')) || 2));
const mediaClipSource = new URLSearchParams(window.location.search).get('mediaClip');
const initialTimelineClips = requestedClipCount === 2
  ? [
    { id: 'left', source_path: 'left.mp4', trim_start: 0, trim_end: 2, speed: 1 },
    { id: 'right', source_path: 'right.mp4', trim_start: 0, trim_end: 2, speed: 1 },
  ]
  : Array.from({ length: requestedClipCount }, (_, index) => ({
    id: `clip-${index}`, source_path: `clip-${index}.mp4`, trim_start: 0, trim_end: 2, speed: 1,
  }));

function EditorControlsFixture() {
  const [clip, setClip] = useState(initialClip);
  const [saved, setSaved] = useState(null);
  const save = () => setSaved(editorStateToSavePayload({ clipList: [clip] }));
  const reload = () => {
    if (saved) setClip(manifestToEditorState(saved).clipList[0]);
  };
  const {
    state: timelineState, set: setTimelineState, setSilent: setTimelineSilent,
    beginDrag, endDrag, undo, redo, reset: resetTimeline,
    canUndo, canRedo,
  } = useEditorHistory({ clipList: initialTimelineClips });
  const timelineClips = timelineState.clipList;
  const setTimelineClips = (updater, silent = false) => (silent ? setTimelineSilent : setTimelineState)((previous) => ({
    ...previous,
    clipList: typeof updater === 'function' ? updater(previous.clipList) : updater,
  }));
  const [selectedClipId, setSelectedClipId] = useState(null);
  const [timelineSaved, setTimelineSaved] = useState(null);
  const segments = buildSegments(timelineClips, Object.fromEntries(timelineClips.map((item) => [item.id, 2])));
  const reorder = (id, direction) => setTimelineClips((previous) => {
    const index = previous.findIndex((item) => item.id === id);
    const destination = index + direction;
    if (index < 0 || destination < 0 || destination >= previous.length) return previous;
    const next = [...previous];
    [next[index], next[destination]] = [next[destination], next[index]];
    return next;
  });
  const split = () => {
    const index = segments.findIndex((item) => item.clip.id === selectedClipId);
    if (index < 0) return;
    const pieces = splitClipAt(segments[index], segments[index].segStart + 1, () => crypto.randomUUID());
    if (pieces) setTimelineClips((previous) => [
      ...previous.slice(0, index), ...pieces, ...previous.slice(index + 1),
    ]);
  };
  return (
    <main data-testid="editor-controls-ready" className="mx-auto max-w-md p-4">
      <div className="mb-3 flex gap-2">
        <button type="button" onClick={save}>Save fixture</button>
        <button type="button" onClick={reload}>Reload fixture</button>
      </div>
      <ClipInspector
        selectedSeg={{ clip, index: 0, dur: (clip.trim_end - clip.trim_start) / (clip.speed || 1) }}
        onClipChange={(patch) => setClip((previous) => ({ ...previous, ...patch }))}
      />
      <pre data-testid="editor-controls-state" className="sr-only">
        {JSON.stringify({ clip, saved })}
      </pre>
      <section data-testid="timeline-controls-ready" className="mt-8">
        <div className="mb-3 flex gap-2">
          <button type="button" onClick={() => setTimelineSaved(editorStateToSavePayload({ clipList: timelineClips }))}>
            Save timeline
          </button>
          <button type="button" onClick={() => timelineSaved && resetTimeline({ clipList: manifestToEditorState(timelineSaved).clipList })}>
            Reload timeline
          </button>
          <button type="button" disabled={!canUndo} onClick={undo}>Undo timeline</button>
          <button type="button" disabled={!canRedo} onClick={redo}>Redo timeline</button>
          <div
            data-testid="timeline-source-clip"
            draggable
            onDragStart={(event) => event.dataTransfer.setData(CLIP_DRAG_TYPE, JSON.stringify({
              path: 'added.mp4', name: 'added.mp4', duration: 2,
            }))}
          >Drag new clip</div>
        </div>
        <div style={{ width: 720, height: 420 }}>
          <Timeline
            segments={segments}
            totalDuration={totalDuration(segments)}
            audioDuration={0}
            cues={[]}
            pxPerSec={100}
            playhead={1}
            selection={selectedClipId ? { type: 'clip', id: selectedClipId } : null}
            onSelectClip={setSelectedClipId}
            onSeek={() => {}}
            onReorder={reorder}
            onSplit={split}
            onDelete={() => setTimelineClips((previous) => previous.filter((item) => item.id !== selectedClipId))}
            onTrim={(id, patch) => setTimelineClips((previous) => previous.map((item) => item.id === id ? { ...item, ...patch } : item), true)}
            onTrimBegin={beginDrag}
            onTrimEnd={endDrag}
            onClipChange={(id, patch) => setTimelineClips((previous) => previous.map((item) => item.id === id ? { ...item, ...patch } : item))}
            onDropClip={(item, at) => setTimelineClips((previous) => [
              ...previous.slice(0, at),
              { id: crypto.randomUUID(), source_path: item.path, trim_start: 0, trim_end: item.duration, speed: 1 },
              ...previous.slice(at),
            ])}
            snapCandidates={[1.5, 2.5]}
            snapFunction={(time, candidates) => snapTime(time, candidates, 0.1)}
          />
        </div>
        <pre data-testid="timeline-controls-state" className="sr-only">
          {JSON.stringify({ timelineClips, timelineSaved, selectedClipId })}
        </pre>
      </section>
      {new URLSearchParams(window.location.search).has('missingClip') && (
        <div data-testid="missing-media-preview" style={{ width: 270, height: 520 }}>
          <SequencePlayer clips={[{
            id: 'missing-probe', source_path: '/definitely-missing-editor-probe.mp4',
            trim_start: 0, trim_end: 1, speed: 1,
          }]} />
        </div>
      )}
      {mediaClipSource && (
        <div data-testid="real-media-preview" style={{ display: 'flex', width: 270, height: 520 }}>
          <SequencePlayer clips={Array.from({ length: requestedClipCount }, (_, index) => ({
            id: `media-clip-${index}`,
            source_path: mediaClipSource,
            trim_start: 0,
            trim_end: 2,
            speed: 1,
          }))} />
        </div>
      )}
    </main>
  );
}

function InspectorAuditFixture() {
  const [kind, setKind] = useState('clip');
  const cue = { _uid: 'audit-cue', start: 0, end: 1.5, text: 'ข้อความตัวอย่าง' };
  const overlay = { id: 'audit-overlay', kind: 'text', start: 0, end: 2, tiers: [{ text: 'ข้อความเสริม' }] };
  const sticker = { id: 'audit-sticker', badge: 'Universal_Badge.png', start: 0, end: 2 };
  const effect = { id: 'audit-effect', effectId: 'audit-effect', start: 0, end: 2 };
  const selection = kind === 'project' || kind === 'cues' ? null : {
    type: kind,
    id: kind === 'text_overlay' ? overlay.id : `audit-${kind}`,
  };
  return (
    <main className="flex h-full flex-col gap-3 p-3">
      <nav aria-label="Audit Inspector panels" className="flex flex-wrap gap-2">
        {['clip', 'caption', 'text_overlay', 'hook', 'sticker', 'effect', 'project', 'cues'].map((item) => (
          <button key={item} type="button" data-testid={`inspector-audit-${item}`} onClick={() => setKind(item)}>
            {item}
          </button>
        ))}
      </nav>
      <div data-testid="inspector-audit-panel" className="min-h-0 w-[460px] max-w-full flex-1">
        <Inspector
          selection={selection}
          selectedSeg={kind === 'clip' ? { clip: initialClip, index: 0, dur: 3 } : null}
          selectedCaption={kind === 'caption' ? cue : null}
          cuesList={[cue]}
          overlays={[overlay]}
          stickers={[sticker]}
          effects={[effect]}
          assets={{ fonts: [], sfx: [], effects: [] }}
          style={{}}
          totalDuration={3}
          onSelectCue={() => setKind('caption')}
          onSelectOverlay={() => setKind('text_overlay')}
          onSelect={(item) => setKind(item?.type || 'clip')}
          onTrackMix={() => {}}
        />
      </div>
    </main>
  );
}

createRoot(document.getElementById('root')).render(
  new URLSearchParams(window.location.search).has('inspectorAudit')
    ? <InspectorAuditFixture /> : <EditorControlsFixture />,
);
