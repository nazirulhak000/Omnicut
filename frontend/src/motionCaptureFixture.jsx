import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import SequencePlayer from './components/SequencePlayer.jsx';
import { MOTION_PRESETS } from './lib/motion/motionPresets.js';
import { buildSegments, getDrawPlan as planAt } from './lib/timelineMath.js';
import {
  ANCHOR_TOP,
  HOOK_COMFORTABLE_LINES,
  HOOK_FS_RATIO,
  HOOK_TOP_Y,
} from './lib/overlayModel.js';

const VIEWPORT = { width: 1080, height: 1920 };
const DEFAULT_DURATION_SECONDS = 2;
const DEFAULT_TEXT_LAYERS = ['Motion capture fixture', 'SequencePlayer Canvas'];
const DEFAULT_CAPTION_TEXT = 'นั่งนิ่งจริงครับ';

function parseJsonParam(params, key, fallback = null) {
  const raw = params.get(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(`invalid ${key} query parameter`);
  }
}

function waitForImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`capture image failed to load: ${url}`));
    image.src = url;
  });
}

function waitForVideo(url) {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.muted = true;
    video.playsInline = true;
    const finish = () => { video.pause(); resolve(video); };
    video.onloadeddata = finish;
    video.onerror = () => reject(new Error(`capture video failed to load: ${url}`));
    video.src = url;
    video.load();
  });
}

function waitForDecodedClip(url) {
  return new Promise((resolve, reject) => {
    const started = performance.now();
    const tick = () => {
      const match = [...document.querySelectorAll('video')].find((video) => (
        video.src === url || video.currentSrc === url
      ));
      if (match?.readyState >= 2) {
        resolve(match);
        return;
      }
      if (performance.now() - started > 8000) {
        reject(new Error(`capture clip did not decode: ${url}`));
        return;
      }
      setTimeout(tick, 50);
    };
    tick();
  });
}

function waitForClipSeek(url, sourceSeconds) {
  return new Promise((resolve, reject) => {
    const started = performance.now();
    const tick = () => {
      const video = [...document.querySelectorAll('video')].find((item) => (
        item.src === url || item.currentSrc === url
      ));
      if (video && !video.seeking && Math.abs((video.currentTime || 0) - sourceSeconds) < 1 / 120) {
        resolve(video);
        return;
      }
      if (performance.now() - started > 8000) {
        reject(new Error(`capture clip did not seek to ${sourceSeconds}s`));
        return;
      }
      setTimeout(tick, 25);
    };
    tick();
  });
}

function createOverlay(presetIds, textLayers = DEFAULT_TEXT_LAYERS, durationSeconds = DEFAULT_DURATION_SECONDS) {
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
    end: durationSeconds,
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
  const mode = params.get('mode') || 'motion';
  const isCaptionMode = mode === 'caption';
  const isMotionMode = mode === 'motion';
  const durationSeconds = Math.max(0.2, Number(params.get('duration')) || DEFAULT_DURATION_SECONDS);
  const requestedClipSource = params.get('clip');
  const clipSource = requestedClipSource || `${window.location.origin}/motion_capture.html`;
  const hasDecodedClip = Boolean(requestedClipSource);
  const clipConfig = useMemo(() => parseJsonParam(params, 'clipConfig', {}) || {}, [params]);
  const secondClipSource = params.get('clip2') || '';
  const secondClipConfig = useMemo(() => parseJsonParam(params, 'clip2Config', {}) || {}, [params]);
  const clipSources = useMemo(
    () => (secondClipSource ? [clipSource, secondClipSource] : [clipSource]),
    [clipSource, secondClipSource],
  );
  const stickerPath = params.get('sticker') || '';
  const effectPath = params.get('effect') || '';
  const effectId = params.get('effectId') || 'fx-capture';
  const spotlight = useMemo(() => parseJsonParam(params, 'spotlight'), [params]);
  const presetIds = useMemo(() => ({
    in: params.get('in') || 'hook.in.bounce',
    loop: params.get('loop') || 'hook.loop.pulse',
    out: params.get('out') || 'hook.out.fade',
  }), [params]);
  const textLayers = useMemo(() => {
    const requested = params.getAll('line').map((value) => value.trim()).filter(Boolean);
    return requested.length ? requested.slice(0, 3) : DEFAULT_TEXT_LAYERS;
  }, [params]);
  const captionText = params.get('caption')?.trim() || DEFAULT_CAPTION_TEXT;
  const fontSample = useMemo(
    () => (isCaptionMode ? captionText : textLayers.join('\n')),
    [captionText, isCaptionMode, textLayers],
  );
  const overlay = useMemo(
    () => (isMotionMode ? createOverlay(presetIds, textLayers, durationSeconds) : null),
    [durationSeconds, isMotionMode, presetIds, textLayers],
  );
  const captureStickers = useMemo(
    () => (stickerPath ? [{
      id: 'sticker-capture',
      badge: 'sticker-capture.png',
      start: 0.5,
      end: durationSeconds,
      normX: 0.72,
      normY: 0.22,
      scale: 1,
    }] : []),
    [durationSeconds, stickerPath],
  );
  const captureEffects = useMemo(
    () => (effectPath ? [{
      id: 'effect-capture',
      effectId,
      start: 0.5,
      end: durationSeconds,
      normX: 0.52,
      normY: 0.34,
      scale: 1,
    }] : []),
    [durationSeconds, effectId, effectPath],
  );
  const cues = useMemo(
    () => (isCaptionMode ? [{
      id: 'caption-capture-cue',
      start: 0,
      end: durationSeconds,
      text: captionText,
      bilingual: false,
      fontName: 'IBM Plex Sans Thai',
      position: 'bottom',
    }] : []),
    [captionText, durationSeconds, isCaptionMode],
  );
  const clips = useMemo(() => [clipConfig, ...(secondClipSource ? [secondClipConfig] : [])]
    .map((config, index) => ({
      ...config,
      id: `motion-capture-clip-${index + 1}`,
      source_path: clipSources[index],
      trim_start: Number(config.trim_start) || 0,
      trim_end: config.trim_end ?? durationSeconds,
      speed: Number(config.speed) || 1,
      transition_in: config.transition_in || 'cut',
    })), [clipConfig, clipSources, durationSeconds, secondClipConfig, secondClipSource]);

  useEffect(() => {
    let active = true;
    Promise.all([
      document.fonts.load("700 35px 'IBM Plex Sans Thai'"),
      // FontFaceSet.load() otherwise probes only a Latin sample. Explicitly
      // request Thai glyph coverage so the first captured Thai frame cannot
      // race ahead using a system fallback while the bundled face activates.
      document.fonts.load("700 35px 'IBM Plex Sans Thai'", 'ทดสอบวรรณยุกต์ไทย นั่งนิ่งจริงครับ'),
      // The fixture accepts arbitrary matrix text through query parameters.
      // Wait for the exact glyph run that will be painted, including digits,
      // punctuation, symbols and emoji, instead of assuming the fixed probe
      // above represents every case.
      document.fonts.load("700 35px 'IBM Plex Sans Thai'", fontSample),
      document.fonts.ready,
    ]).then(() => {
      if (!active) return;
      const fontSpec = "700 35px 'IBM Plex Sans Thai'";
      if (!document.fonts.check(fontSpec, fontSample)) {
        throw new Error(`required fixture font is not ready for ${fontSample}`);
      }
      setFontsReady(true);
    });
    return () => { active = false; };
  }, [fontSample]);

  useEffect(() => {
    if (!fontsReady) return undefined;
    window.motionCapture = {
      schemaVersion: 1,
      renderer: 'SequencePlayer',
      width: VIEWPORT.width,
      height: VIEWPORT.height,
      fps: 30,
      durationSeconds,
      mode,
      overlayFeatureContract: {
        sticker: captureStickers.length ? {
          id: captureStickers[0].id,
          start: captureStickers[0].start,
          end: captureStickers[0].end,
          normX: captureStickers[0].normX,
          normY: captureStickers[0].normY,
          scale: captureStickers[0].scale,
        } : null,
        effect: captureEffects.length ? {
          id: captureEffects[0].id,
          effectId: captureEffects[0].effectId,
          start: captureEffects[0].start,
          end: captureEffects[0].end,
          normX: captureEffects[0].normX,
          normY: captureEffects[0].normY,
          scale: captureEffects[0].scale,
        } : null,
        spotlight: spotlight || null,
      },
      clipContracts: clips.map((clip) => ({
        trim_start: clip.trim_start,
        trim_end: clip.trim_end,
        speed: clip.speed,
        freeze_tail: Number(clip.freeze_tail) || 0,
        zoom: clip.zoom ?? clip.scale ?? 1,
        pan_x: clip.pan_x ?? clip.x ?? 0,
        pan_y: clip.pan_y ?? clip.y ?? 0,
        rotation: Number(clip.rotation) || 0,
        mirror: Boolean(clip.mirror),
        bg_blur: Boolean(clip.bg_blur),
        fit_mode: clip.fit_mode || null,
        keyframes: Array.isArray(clip.keyframes) ? clip.keyframes : [],
        transition_in: clip.transition_in,
        transition_duration: clip.transition_duration ?? null,
      })),
      presetIds,
      fontReady: document.fonts.check("700 35px 'IBM Plex Sans Thai'", fontSample),
      fontSample,
      captionContract: isCaptionMode ? {
        text: captionText,
        position: 'bottom',
        font: 'IBM Plex Sans Thai',
        bilingual: false,
      } : null,
      overlayContract: overlay ? {
        anchor: overlay.anchor,
        x: overlay.x,
        y: overlay.y,
        baseFsRatio: overlay.base_fs_ratio,
        comfortableLines: overlay.comfortable_lines,
        font: overlay.look.font,
        outlinePx: overlay.look.outline_px,
        bold: overlay.look.bold,
        tiers: overlay.tiers.map((tier) => ({ text: tier.text, color: tier.look.color })),
      } : null,
      capture: async ({ frameIndex = 0 } = {}) => {
        const lastFrame = Math.max(0, Math.ceil(durationSeconds * 30) - 1);
        const frame = Math.max(0, Math.min(lastFrame, Number(frameIndex) || 0));
        const timestampMs = Math.round((frame * 1000) / 30);
        if (stickerPath) await waitForImage(stickerPath);
        if (effectPath) await waitForVideo(effectPath);
        if (hasDecodedClip) {
          await Promise.all(clipSources.map(waitForDecodedClip));
          playerRef.current?.seekTo(timestampMs / 1000);
          // Effects are decoded into detached video elements by SequencePlayer.
          // Give the browser one deterministic decode window before sampling;
          // the hook remains seek-driven and never depends on wall-clock frame
          // progression for the requested timestamp.
          if (captureEffects.length) await new Promise((resolve) => setTimeout(resolve, 350));
          playerRef.current?.seekTo(timestampMs / 1000);
          const durations = Object.fromEntries(clips.map((clip) => [
            clip.id,
            Number(clip.trim_end) || durationSeconds,
          ]));
          const activePlan = planAt(buildSegments(clips, durations), timestampMs / 1000);
          await Promise.all(activePlan.map(({ seg, localTime }) => (
            waitForClipSeek(seg.clip.source_path, localTime)
          )));
          await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
          playerRef.current?.captureFrame?.();
        } else {
          // Preserve the original fixture's synchronous seek contract for
          // motion/caption pairs that intentionally use a black canvas.
          playerRef.current?.seekTo(timestampMs / 1000);
        }
        const canvas = document.querySelector('[data-testid="motion-capture-sequence-player"] canvas');
        if (!(canvas instanceof HTMLCanvasElement)) throw new Error('SequencePlayer canvas is not ready');
        const dataUrl = canvas.toDataURL('image/png');
        return { frameIndex: frame, timestampMs, dataUrl };
      },
    };
    return () => { delete window.motionCapture; };
  }, [
    captureEffects,
    captureStickers,
    clipSources,
    clipConfig,
    clipSource,
    clips,
    durationSeconds,
    effectPath,
    fontsReady,
    hasDecodedClip,
    mode,
    overlay,
    presetIds,
    spotlight,
    stickerPath,
  ]);

  if (!fontsReady) return <main data-testid="motion-capture-font-loading" />;

  return (
    <main data-testid="motion-capture-sequence-player" className="flex flex-col" style={{ width: '100vw', height: '100vh' }}>
      <SequencePlayer
        initialPreviewQuality={params.get('previewQuality') || 'smooth540'}
        ref={playerRef}
        clips={clips}
        cues={cues}
        overlays={overlay ? [overlay] : []}
        compact={params.get('playbackProbe') !== '1'}
        showWatermark={params.get('watermark') === '1'}
        channelId={params.get('channel') || 'main'}
        channelIdentitySnapshot={parseJsonParam(params, 'channelIdentity')}
        isMuted
        captionStyle={isCaptionMode ? {
          hidden: false,
          bilingualSubtitles: false,
          captionPosition: 'bottom',
          fontName: 'IBM Plex Sans Thai',
        } : { hidden: true }}
        stickerStyle={{
          stickers: stickerPath ? [{ name: 'sticker-capture.png', id: 'sticker-capture.png', img_url: stickerPath }] : [],
        }}
        stickers={captureStickers}
        effects={captureEffects}
        effectAssets={effectPath ? [{ id: effectId, video_url: effectPath }] : []}
        spotlight={spotlight}
      />
    </main>
  );
}

createRoot(document.getElementById('root')).render(<Fixture />);
