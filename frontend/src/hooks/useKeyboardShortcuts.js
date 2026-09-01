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
 */
export function useKeyboardShortcuts({
  onTabChange,
  onSave,
  onToggleShortcutsModal,
  onEscape
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      const target = e.target;
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable;

      // 1. Esc: Universal Dismiss
      if (e.key === 'Escape') {
        onEscape?.();
        return;
      }

      // 2. Ctrl+S / Cmd+S: Quick Save
      if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
        e.preventDefault();
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
        e.preventDefault();
        const activeVideos = Array.from(document.querySelectorAll('video'));
        if (activeVideos.length > 0) {
          // Find the most relevant video (visible or in open modal)
          const targetVideo = activeVideos.find(v => {
            const rect = v.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
          }) || activeVideos[0];

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

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onTabChange, onSave, onToggleShortcutsModal, onEscape]);
}

export default useKeyboardShortcuts;
