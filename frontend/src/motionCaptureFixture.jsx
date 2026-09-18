import React, { useEffect, useMemo, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import SequencePlayer from './components/SequencePlayer.jsx';
import { MOTION_PRESETS } from './lib/motion/motionPresets.js';

const VIEWPORT = { width: 1080, height: 1920 };
const DURATION_SECONDS = 2;

function createOverlay(presetIds) {
  const phases = {};
  for (const phase of ['in', 'loop', 'out']) {
    const id = presetIds?.[phase] || `hook.${phase}.${phase === 'in' ? 'bounce' : phase === 'loop' ? 'pulse' : 'fade'}`;
    const contract = MOTION_PRESETS[id];
    if (!contract) throw new Error(`Unknown motion preset: ${id}`);
    phases[phase] = contract;
  }

  return {
    id: 'motion-capture-overlay',
    kind: 'hook',
    start: 0,
    end: DURATION_SECONDS,
    position: 'middle',
    x: 0.5,
    y: 0.5,
    base_fs_ratio: 0.075,
    comfortable_lines: 2,
    layer: 4,
    look: {
      font: 'IBM Plex Sans Thai',
      color: '#FFFFFF',
      accent_color: '#25F4EE',
      outline_color: '#000000',
      outline_px: 3,
      shadow: { color: '#000000', blur: 8, offset_x: 0, offset_y: 4 },
    },
    tiers: [
      { text: 'Motion capture fixture', look: { color: '#FFFFFF' } },
      { text: 'SequencePlayer Canvas', look: { color: '#25F4EE' } },
    ],
    anim: { in: 'none', loop: 'none', out: 'fade' },
    motionContract: { phases },
    motionMetadata: { role: 'hook' },
    scrim: false,
    hidden: false,
  };
}

export function Fixture() {
  const playerRef = useRef(null);
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const presetIds = useMemo(() => ({
    in: params.get('in') || 'hook.in.bounce',
    loop: params.get('loop') || 'hook.loop.pulse',
    out: params.get('out') || 'hook.out.fade',
  }), [params]);
  const overlay = useMemo(() => createOverlay(presetIds), [presetIds]);
  const clips = useMemo(() => [{
    id: 'motion-capture-clip',
    source_path: '',
    trim_start: 0,
    trim_end: DURATION_SECONDS,
    speed: 1,
    transition_in: 'cut',
  }], []);

  useEffect(() => {
    window.motionCapture = {
      schemaVersion: 1,
      renderer: 'SequencePlayer',
      width: VIEWPORT.width,
      height: VIEWPORT.height,
      fps: 30,
      durationSeconds: DURATION_SECONDS,
      presetIds,
      capture: ({ frameIndex = 0 } = {}) => {
        const frame = Math.max(0, Math.min(59, Number(frameIndex) || 0));
        const timestampMs = Math.round((frame * 1000) / 30);
        playerRef.current?.seekTo(timestampMs / 1000);
        const canvas = document.querySelector('[data-testid="motion-capture-sequence-player"] canvas');
        if (!(canvas instanceof HTMLCanvasElement)) throw new Error('SequencePlayer canvas is not ready');
        const dataUrl = canvas.toDataURL('image/png');
        return { frameIndex: frame, timestampMs, dataUrl };
      },
    };
    return () => { delete window.motionCapture; };
  }, [presetIds]);

  return (
    <main data-testid="motion-capture-sequence-player" style={{ width: '100vw', height: '100vh' }}>
      <SequencePlayer
        ref={playerRef}
        clips={clips}
        overlays={[overlay]}
        compact
        showWatermark={false}
        isMuted
        captionStyle={{ hidden: true }}
        stickerStyle={{}}
      />
    </main>
  );
}

createRoot(document.getElementById('root')).render(<Fixture />);
