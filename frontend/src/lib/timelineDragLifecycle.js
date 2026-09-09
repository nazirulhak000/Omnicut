export const TIMELINE_DRAG_THRESHOLD_PX = 3;

export function capturePointer(event) {
  try {
    event.currentTarget.setPointerCapture(event.pointerId);
  } catch {
    // Pointer capture is an enhancement; the drag can still continue.
  }
}

export function releasePointer(event) {
  try {
    event.currentTarget.releasePointerCapture(event.pointerId);
  } catch {
    // The pointer may already have been released or the event may be synthetic.
  }
}

export function beginDragAfterThreshold(state, clientX, dragBegin, threshold = TIMELINE_DRAG_THRESHOLD_PX) {
  if (!state) return false;
  if (!state.moved && Math.abs(clientX - state.startX) < threshold) return false;
  if (!state.moved) {
    state.moved = true;
    dragBegin?.();
  }
  return true;
}
