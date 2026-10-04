// Test-only instrumentation. Every frame is drawn by the production player.
import React, { useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import SequencePlayer from './components/SequencePlayer.jsx';
import { buildSegments, getDrawPlan } from './lib/timelineMath.js';

const params = new URLSearchParams(location.search);
const clips = JSON.parse(params.get('clips') || '[]');
const segments = buildSegments(clips);
const samples = [];
const presented = new WeakMap();
const tracked = new WeakSet();
let lastRecordedDraw = new WeakMap();
function observeVideo(video) {
  if (tracked.has(video)) return;
  tracked.add(video);
  const observe = (_now, metadata) => {
    presented.set(video, { pts: metadata.mediaTime, callbackWall: performance.now(), frames: metadata.presentedFrames });
    if (video.isConnected) video.requestVideoFrameCallback(observe);
  };
  video.requestVideoFrameCallback(observe);
}
const observer = new MutationObserver(() => document.querySelectorAll('video').forEach(observeVideo));
observer.observe(document.documentElement, { childList: true, subtree: true });
const originalDraw = CanvasRenderingContext2D.prototype.drawImage;
CanvasRenderingContext2D.prototype.drawImage = function (source, ...args) {
  const result = originalDraw.call(this, source, ...args);
  if (source instanceof HTMLVideoElement && samples.length < 3000) {
    const canvas = document.querySelector('[data-testid="sequence-preview-canvas"]');
    const t = Number(canvas?.dataset.previewTime);
    const clock = presented.get(source);
    const entry = getDrawPlan(segments, t).find(({ seg }) => new URL(seg.clip.source_path, location.href).href === source.currentSrc);
    if (entry && clock && lastRecordedDraw.get(source) !== t) {
      lastRecordedDraw.set(source, t);
      samples.push({ timeline: t, audio: document.querySelector('audio')?.currentTime,
      audioPaused: document.querySelector('audio')?.paused, playing: canvas?.dataset.previewPlaying === 'true',
      id: entry.seg.clip.id, expected: entry.localTime, role: entry.role,
      presentedTimeline: entry.seg.segStart + (clock.pts - entry.seg.clip.trim_start) / entry.seg.clip.speed,
      pts: clock.pts, callbackAgeMs: performance.now() - clock.callbackWall,
      currentTime: source.currentTime, seeking: source.seeking, rate: source.playbackRate });
    }
  }
  return result;
};
function Fixture() {
  const player = useRef(null);
  useEffect(() => {
    window.avProbe = { samples, segments, reset() { samples.length = 0; lastRecordedDraw = new WeakMap(); }, seek(t) { player.current.seekTo(t); } };
    return () => { observer.disconnect(); CanvasRenderingContext2D.prototype.drawImage = originalDraw; delete window.avProbe; };
  }, []);
  return <main data-testid="multisource-av-preview" style={{ width: '100vw', height: '100vh' }} className="flex flex-col">
    <SequencePlayer ref={player} clips={clips} audioUrl={params.get('audio')} initialPreviewQuality="smooth540"
      captionStyle={{ hidden: true }} showWatermark={false} highResStillEnabled={false} />
  </main>;
}
createRoot(document.getElementById('root')).render(<Fixture />);
