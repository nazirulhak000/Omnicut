import { useEffect } from 'react';

/**
 * useKeyboardShortcuts Hook
 * Global power-user keyboard shortcut listener for Desktop-grade workflows.
 * 
 * Shortcuts:
 * - 1..8: Switch active menu tabs
 * - Spacebar: Play / Pause active preview video without scrolling
 * - Esc: Close any active modal / overlay
 * - Ctrl+S / Cmd+S: Prevent browser save dialog & trigger save
 * - ?: Toggle Keyboard Shortcut Cheat Sheet
 *
 * The editor tab registers its own window listeners for Space (useEditorShortcuts ->
 * player toggle) and Ctrl+S (EditorShell handleManualSave). Which window listener runs
 * first is not stable (EditorShell is lazy-mounted), so on the editor tab this hook
 * leaves those two keys alone (`isEditorActive`), and on every tab it yields to an
 * event that another handler already claimed (`e.defaultPrevented`).
 */

// SequencePlayer keeps one 1px, off-screen, aria-hidden decode <video> per clip;
// Space must never drive those.
function isDecoyVideo(video) {
  return Boolean(video.closest?.('[aria-hidden="true"]'));
}

function isOnScreen(video, view) {
  const rect = video.getBoundingClientRect();
  if (!(rect.width > 2 && rect.height > 2)) return false;
  const viewW = view?.innerWidth ?? Infinity;
  const viewH = view?.innerHeight ?? Infinity;
  return rect.right > 0 && rect.bottom > 0 && rect.left < viewW && rect.top < viewH;
}

export function createGlobalKeyDownHandler({
  onTabChange,
  onSave,
  onToggleShortcutsModal,
  onEscape,
  isEditorActive = false,
  doc = typeof document !== 'undefined' ? document : null,
} = {}) {
  return (e) => {
    const target = e.target;
    const isInput =
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.tagName === 'SELECT' ||
      target.isContentEditable;
    // Read before this handler (or anything below) calls preventDefault itself.
    const claimedElsewhere = e.defaultPrevented;

    // 1. Esc: Universal Dismiss
    if (e.key === 'Escape') {
      onEscape?.();
      return;
    }

    // 2. Ctrl+S / Cmd+S: Quick Save
    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
      e.preventDefault(); // never let the browser open "Save page as"
      // The editor saves the project itself; this toast is only for the form pages.
      if (isEditorActive || claimedElsewhere) return;
      onSave?.();
      return;
    }

    // 3. Question mark (?): Toggle Shortcuts Cheat Sheet
    if (e.key === '?' && !isInput) {
      e.preventDefault();
      onToggleShortcutsModal?.();
      return;
    }

    // If user is typing inside an input/textarea, ignore single key shortcuts
    if (isInput) return;

    // 4. Spacebar: Play / Pause Active Video (prevent page scroll)
    if (e.code === 'Space') {
      // The editor owns Space (and decides about focused buttons/sliders itself).
      if (isEditorActive || claimedElsewhere) return;
      e.preventDefault();
      const activeVideos = Array.from(doc?.querySelectorAll('video') ?? []).filter((v) => !isDecoyVideo(v));
      if (activeVideos.length > 0) {
        // Find the most relevant video (visible or in open modal)
        const targetVideo = activeVideos.find((v) => isOnScreen(v, doc?.defaultView)) || activeVideos[0];

        if (targetVideo) {
          if (targetVideo.paused) {
            targetVideo.play().catch(() => {});
          } else {
            targetVideo.pause();
          }
        }
      }
      return;
    }

    // 5. Number keys 1..6 for Quick Tab Navigation
    const tabMap = {
      '1': 'flow',     // 1. สินค้า ➔ คลิป
      '2': 'tracker',  // 2. แทร็กเกอร์ 5 เฟส
      '3': 'editor',   // 3. ตัดต่อ & สร้างคลิป (เดิม Studio ถูกยุบเข้ามาที่นี่)
      '4': 'gallery',  // 4. Export Gallery
      '5': 'assets'    // 5. Assets & System
    };

    if (tabMap[e.key]) {
      e.preventDefault();
      onTabChange?.(tabMap[e.key]);
    }
  };
}

export function useKeyboardShortcuts({
  onTabChange,
  onSave,
  onToggleShortcutsModal,
  onEscape,
  isEditorActive = false
}) {
  useEffect(() => {
    const handleKeyDown = createGlobalKeyDownHandler({
      onTabChange,
      onSave,
      onToggleShortcutsModal,
      onEscape,
      isEditorActive,
    });

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onTabChange, onSave, onToggleShortcutsModal, onEscape, isEditorActive]);
}

export default useKeyboardShortcuts;
