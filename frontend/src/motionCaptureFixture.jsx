import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import SequencePlayer from './components/SequencePlayer.jsx';
import { MOTION_PRESETS } from './lib/motion/motionPresets.js';
import {
  ANCHOR_TOP,
  HOOK_COMFORTABLE_LINES,
  HOOK_FS_RATIO,
  HOOK_TOP_Y,
} from './lib/overlayModel.js';

const VIEWPORT = { width: 1080, height: 1920 };
const DURATION_SECONDS = 2;
const DEFAULT_TEXT_LAYERS = ['Motion capture fixture', 'SequencePlayer Canvas'];

function createOverlay(presetIds, textLayers = DEFAULT_TEXT_LAYERS) {
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
    position: 'top',
    anchor: ANCHOR_TOP,
    x: 0.5,
    y: HOOK_TOP_Y,
    base_fs_ratio: HOOK_FS_RATIO,
    comfortable_lines: HOOK_COMFORTABLE_LINES,
    layer: 4,
    look: {
      font: 'IBM Plex Sans Thai',
      color: '#FFFFFF',
      accent_color: '#25F4EE',
      outline_color: '#000000',
      outline_px: 3,
      shadow: { color: '#000000', blur: 8, dx: 0, dy: 4 },
      bold: true,
    },
    tiers: textLayers.map((text, index) => ({
      text,
      look: { color: index === 0 ? '#FFFFFF' : '#25F4EE' },
    })),
    anim: {
      in: presetIds.in.split('.').at(-1),
      loop: presetIds.loop.split('.').at(-1),
      out: presetIds.out.split('.').at(-1),
      accent: 'none',
      stagger: false,
    },
    motionContract: { phases },
    motionMetadata: { role: 'hook' },
    scrim: false,
    hidden: false,
  };
}

export function Fixture() {
  const playerRef = useRef(null);
  const [fontsReady, setFontsReady] = useState(false);
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const presetIds = useMemo(() => ({
    in: params.get('in') || 'hook.in.bounce',
    loop: params.get('loop') || 'hook.loop.pulse',
    out: params.get('out') || 'hook.out.fade',
  }), [params]);
  const textLayers = useMemo(() => {
    const requested = params.getAll('line').map((value) => value.trim()).filter(Boolean);
    return requested.length ? requested.slice(0, 3) : DEFAULT_TEXT_LAYERS;
  }, [params]);
  const overlay = useMemo(() => createOverlay(presetIds, textLayers), [presetIds, textLayers]);
  const clips = useMemo(() => [{
    id: 'motion-capture-clip',
    // Keep the decode element's src non-empty so React does not emit a
    // runtime error. The fixture verifies overlays on a black canvas and does
    // not depend on decoded footage; this same-origin document request is
    // deterministic and never reaches the production media API.
    source_path: `${window.location.origin}/motion_capture.html`,
    trim_start: 0,
    trim_end: DURATION_SECONDS,
    speed: 1,
    transition_in: 'cut',
  }], []);

  useEffect(() => {
    let active = true;
    Promise.all([
      document.fonts.load("700 35px 'IBM Plex Sans Thai'"),
      document.fonts.ready,
    ]).then(() => { if (active) setFontsReady(true); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!fontsReady) return undefined;
    window.motionCapture = {
      schemaVersion: 1,
      renderer: 'SequencePlayer',
      width: VIEWPORT.width,
      height: VIEWPORT.height,
      fps: 30,
      durationSeconds: DURATION_SECONDS,
      presetIds,
      overlayContract: {
        anchor: overlay.anchor,
        x: overlay.x,
        y: overlay.y,
        baseFsRatio: overlay.base_fs_ratio,
        comfortableLines: overlay.comfortable_lines,
        font: overlay.look.font,
        outlinePx: overlay.look.outline_px,
        bold: overlay.look.bold,
        tiers: overlay.tiers.map((tier) => ({ text: tier.text, color: tier.look.color })),
      },
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
  }, [fontsReady, overlay, presetIds]);

  if (!fontsReady) return <main data-testid="motion-capture-font-loading" />;

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
