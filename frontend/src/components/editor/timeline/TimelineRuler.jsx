import React from 'react';
import { FPS, formatTimecode } from '../../../lib/timelineMath';
import { frameTickSpacing } from '../../../lib/timelineTrackModel';
import { formatPreflightTime } from '../../../lib/renderPreflight';

const FRAME_TICK_COLOR = '#4A4742';

// Viral Lint heatmap strip (warn / block spans). Sits on the ruler's bottom
// edge, below the tick labels. Severity is also carried by height and style, so
// it does not depend on hue alone: warn = 3px amber, block = 5px red with a
// light top edge. Both clear 3:1 against the #1C1B19 ruler.
const LINT_STYLE = {
  warn: { label: 'ข้อสังเกต', background: '#D9A441', height: 3, edge: null },
  block: { label: 'ต้องแก้', background: '#EF6A5E', height: 5, edge: '#FFD9D4' },
};
const LINT_MIN_PX = 3;

// One repeating-gradient layer draws every tick of a family in a single
// element, so a 60 second clip at full zoom (1800 frames) costs one node.
function tickLayer(period, height, widthPx) {
  return {
    width: widthPx,
    height,
    backgroundImage: `repeating-linear-gradient(to right, ${FRAME_TICK_COLOR} 0, ${FRAME_TICK_COLOR} 1px, transparent 1px, transparent ${period}px)`,
  };
}

export default function TimelineRuler({
  gutterW,
  rulerHeight = 22,
  ticks = [],
  pxPerSec,
  onStartScrub,
  onMoveScrub,
  onEndScrub,
  // { inTime, outTime } (seconds or null): the I / O marks of a range cut.
  rangeMark = null,
  // [{ code, severity, start, end, message }] from viralLintHeatmapSpans().
  lintSpans = null,
}) {
  // Frame ticks only exist when zoomed in far enough to tell frames apart; the
  // same condition switches the labels to mm:ss:ff so they agree with the toolbar.
  const framePx = frameTickSpacing(pxPerSec, FPS);
  const spanPx = ticks.length ? ticks[ticks.length - 1] * pxPerSec : 0;
  const markIn = Number.isFinite(rangeMark?.inTime) ? rangeMark.inTime : null;
  const markOut = Number.isFinite(rangeMark?.outTime) ? rangeMark.outTime : null;

  return (
    <div className="sticky top-0 z-20 flex bg-[#1C1B19]">
      <div style={{ width: gutterW }} className="flex-shrink-0" />
      <div
        onPointerDown={onStartScrub}
        onPointerMove={onMoveScrub}
        onPointerUp={onEndScrub}
        onPointerCancel={onEndScrub}
        className="relative flex-1 cursor-text touch-none border-b border-[#363430]"
        style={{ height: rulerHeight }}
        title="คลิกหรือลากเพื่อเลื่อนหัวอ่าน"
      >
        {/* In / Out of a range cut: a thin band behind the ticks, and a thin
            edge line for a lone mark. Never a pointer target, so scrubbing
            across it still works. */}
        {markIn !== null && markOut !== null && markOut > markIn && (
          <span
            aria-hidden="true"
            data-range-mark="band"
            className="pointer-events-none absolute top-0 h-full border-x border-[#D97757] bg-[#D97757]/25"
            style={{ left: markIn * pxPerSec, width: Math.max(2, (markOut - markIn) * pxPerSec) }}
          />
        )}
        {markIn !== null && (markOut === null || markOut <= markIn) && (
          <span
            aria-hidden="true"
            data-range-mark="in"
            className="pointer-events-none absolute top-0 h-full w-0.5 bg-[#D97757]"
            style={{ left: markIn * pxPerSec }}
          />
        )}
        {markOut !== null && markIn === null && (
          <span
            aria-hidden="true"
            data-range-mark="out"
            className="pointer-events-none absolute top-0 h-full w-0.5 -translate-x-full bg-[#D97757]"
            style={{ left: markOut * pxPerSec }}
          />
        )}
        {framePx !== null && (
          <>
            <span
              aria-hidden="true"
              data-frame-ticks="frame"
              className="pointer-events-none absolute left-0 top-0"
              style={tickLayer(framePx, 3, spanPx)}
            />
            <span
              aria-hidden="true"
              data-frame-ticks="five"
              className="pointer-events-none absolute left-0 top-0"
              style={tickLayer(framePx * 5, 5, spanPx)}
            />
          </>
        )}
        {Array.isArray(lintSpans) && lintSpans.length > 0 && (
          <div data-viral-heatmap className="pointer-events-none absolute inset-x-0 bottom-0 h-[5px]">
            {lintSpans.map((span, index) => {
              const look = LINT_STYLE[span.severity] || LINT_STYLE.warn;
              const range = `${formatPreflightTime(span.start)}${span.end > span.start ? ` – ${formatPreflightTime(span.end)}` : ''}`;
              const text = `${look.label} · ${range} · ${span.message}`;
              return (
                <span
                  key={`${span.code}-${span.start}-${index}`}
                  data-viral-span={span.severity}
                  role="img"
                  aria-label={text}
                  title={text}
                  className="pointer-events-auto absolute bottom-0 rounded-[1px]"
                  style={{
                    left: span.start * pxPerSec,
                    width: Math.max(LINT_MIN_PX, (span.end - span.start) * pxPerSec),
                    height: look.height,
                    background: look.background,
                    opacity: 0.9,
                    boxShadow: look.edge ? `inset 0 1px 0 ${look.edge}` : undefined,
                  }}
                />
              );
            })}
          </div>
        )}
        {ticks.map((t) => (
          <div key={t} className="pointer-events-none absolute top-0 h-full" style={{ left: t * pxPerSec }}>
            <span className="absolute top-0 h-2 w-px bg-[#4A4742]" />
            <span className="absolute top-2 -translate-x-1/2 font-mono text-xs text-[#9C968F]">
              {formatTimecode(t, { frames: framePx !== null })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
