import { subjectPointFromFramePointer } from './subjectPoints.js';

/**
 * Turn a click on the preview frame into a product point.
 *
 * A plain click marks the product (label 1); shift- or alt-click marks
 * background (label 0). `rect` is the live bounding rect of the 9:16 frame, so
 * the result stays correct under any preview resize, zoom or letterbox.
 * Returns null when the frame has no size.
 */
export function subjectPointFromPickClick(event, rect) {
  const point = subjectPointFromFramePointer(event, rect);
  if (!point) return null;
  return { ...point, label: event?.shiftKey || event?.altKey ? 0 : 1 };
}

/**
 * True when a pick-mode event should be swallowed before overlays, drag
 * handles or play/pause see it. Real buttons (cutout mode, 1080p toggle) stay
 * usable so the user can still change the view while picking. A button that
 * only covers the frame (the full-frame play overlay) carries
 * `data-subject-pick-passthrough` and is treated as the frame, not a control.
 */
export function shouldCaptureSubjectPick(pickMode, target) {
  if (!pickMode) return false;
  const button = target?.closest?.('button');
  return !button || button.hasAttribute('data-subject-pick-passthrough');
}
