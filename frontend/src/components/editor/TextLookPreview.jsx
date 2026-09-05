import React from 'react';
import {
  ACCENT_COLOR,
  CANVAS_SCALE,
  PILL_PAD_X_EM,
  PILL_PAD_Y_EM,
  PILL_RADIUS_MAX_PX,
  TEXT_FS_RATIO,
  fontWeight,
  resolveLook,
} from '../../lib/overlayModel';

// The canvas the real overlay is drawn on. A preview is a fraction of it, so
// every size here is the canvas size times `scale` -- the card cannot drift
// from the frame because it is not carrying its own numbers.
const CANVAS_W = 540;

/**
 * One tier of an overlay, drawn in DOM at whatever size the caller has room
 * for, from the same TextLook the canvas and the ASS writer read.
 *
 * The template gallery used to carry a fourth style representation
 * (`cssPreview`: a hand-written CSS object per card) that mapped to neither
 * engine. Cards were tuned by eye against a preview that was itself tuned by
 * eye against the render, so "what the card shows" and "what you get" were
 * two independent guesses. There is one description of a look now, and this
 * renders it.
 */
export default function TextLookPreview({
  look,
  text,
  accentColor = '#FFE600',
  baseFsRatio = TEXT_FS_RATIO,
  scale = 0.5,
  className = '',
  style: extraStyle = null,
}) {
  const resolved = resolveLook(look, null);
  const canvasFs = CANVAS_W * baseFsRatio * ((resolved.size_pct || 100) / 100);
  const fs = Math.max(8, Math.round(canvasFs * scale));
  const colour = resolved.color === ACCENT_COLOR ? accentColor : resolved.color;
  const lines = String(text || '').split('\n');

  // ctx.strokeText centres its stroke and so does -webkit-text-stroke, so the
  // same number describes the same edge on both -- scaled with the text.
  const strokeW = resolved.outline_px > 0.01
    ? Math.max(0.5, resolved.outline_px * scale)
    : 0;

  const shadow = resolved.shadow
    ? `${(resolved.shadow.dx * CANVAS_SCALE * scale).toFixed(1)}px `
      + `${(resolved.shadow.dy * CANVAS_SCALE * scale).toFixed(1)}px `
      + `${(resolved.shadow.blur * CANVAS_SCALE * scale * 2).toFixed(1)}px `
      + 'rgba(0,0,0,0.9)'
    : 'none';

  const pill = resolved.pill;
  const padX = pill ? Math.round(fs * (pill.pad_x_em ?? PILL_PAD_X_EM)) : 0;
  const padY = pill ? Math.round(fs * (pill.pad_y_em ?? PILL_PAD_Y_EM)) : 0;

  return (
    <span
      className={className}
      style={{
        display: 'inline-block',
        maxWidth: '100%',
        padding: pill ? `${padY}px ${padX}px` : 0,
        background: pill ? pill.fill : 'transparent',
        border: pill?.border ? `1.5px solid ${pill.border}` : 'none',
        borderRadius: pill
          ? Math.min(
            (fs + padY * 2) / 2,
            PILL_RADIUS_MAX_PX * CANVAS_SCALE * scale,
          )
          : 0,
        // libass advances exactly one font size per line, so the preview does
        // too -- a looser card would misrepresent a two-line overlay.
        lineHeight: 1,
        textAlign: 'center',
        ...extraStyle,
      }}
    >
      {lines.map((line, i) => (
        <span
          key={i}
          style={{
            display: 'block',
            fontFamily: `'${resolved.font}', sans-serif`,
            fontWeight: fontWeight(resolved.font),
            fontSize: fs,
            color: colour,
            textTransform: resolved.upper ? 'uppercase' : 'none',
            WebkitTextStroke: strokeW ? `${strokeW}px ${resolved.outline_color}` : undefined,
            paintOrder: 'stroke fill',
            textShadow: shadow,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {line}
        </span>
      ))}
    </span>
  );
}
