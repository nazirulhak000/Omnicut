import { useCallback, useRef, useState } from 'react';
import { tracksFitHeight } from '../components/editor/Timeline.jsx';

export const TIMELINE_CHROME_H = 8 + 44;
export const TIMELINE_DEFAULT_H = TIMELINE_CHROME_H + tracksFitHeight();
export const TIMELINE_MIN_H = TIMELINE_CHROME_H + tracksFitHeight({ audioCollapsed: true });
export const TIMELINE_MAX_H = 560;

export const ASSET_MIN_W = 180;
export const ASSET_MAX_W = 480;
export const ASSET_DEFAULT_W = 250;

export const INSPECTOR_MIN_W = 280;
export const INSPECTOR_MAX_W = 680;
export const INSPECTOR_DEFAULT_W = 380;

export const MOBILE_PREVIEW_MIN_H = 160;
export const MOBILE_PREVIEW_DEFAULT = 0.45;
export const MOBILE_TAB_ROW_H = 48;

/**
 * Hook for managing panel widths, timeline heights, and collapse states across desktop & mobile.
 */
export function usePanelLayout({ mobileTimelineH = 0 } = {}) {
  const resizeRef = useRef(null);
  const assetResizeRef = useRef(null);
  const inspectorResizeRef = useRef(null);
  const mobileWrapRef = useRef(null);
  const mobileResizeRef = useRef(null);

  // Desktop timeline height
  const [timelineH, setTimelineH] = useState(() => {
    try {
      const saved = Number(localStorage.getItem('capcut_timeline_h'));
      return saved >= TIMELINE_MIN_H && saved <= TIMELINE_MAX_H ? saved : TIMELINE_DEFAULT_H;
    } catch (_) {
      return TIMELINE_DEFAULT_H;
    }
  });

  const applyTimelineH = useCallback((nextH) => {
    const clamped = Math.max(TIMELINE_MIN_H, Math.min(TIMELINE_MAX_H, nextH));
    setTimelineH(clamped);
    try { localStorage.setItem('capcut_timeline_h', String(clamped)); } catch (_) {}
  }, []);

  // Desktop left asset-panel width & collapse
  const [assetW, setAssetW] = useState(() => {
    try {
      const saved = Number(localStorage.getItem('editor.assetW'));
      return saved >= ASSET_MIN_W && saved <= ASSET_MAX_W ? saved : ASSET_DEFAULT_W;
    } catch (_) {
      return ASSET_DEFAULT_W;
    }
  });

  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('editor.leftSidebarCollapsed') === 'true';
    } catch (_) {
      return false;
    }
  });

  const applyAssetW = useCallback((nextW) => {
    const clamped = Math.max(ASSET_MIN_W, Math.min(ASSET_MAX_W, nextW));
    setAssetW(clamped);
    try { localStorage.setItem('editor.assetW', String(clamped)); } catch (_) {}
  }, []);

  const toggleLeftSidebar = useCallback(() => {
    setLeftSidebarCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem('editor.leftSidebarCollapsed', String(next)); } catch (_) {}
      return next;
    });
  }, []);

  // Desktop inspector-panel width & collapse
  const [inspectorW, setInspectorW] = useState(() => {
    try {
      const saved = Number(localStorage.getItem('editor.inspectorW'));
      return saved >= INSPECTOR_MIN_W && saved <= INSPECTOR_MAX_W ? saved : INSPECTOR_DEFAULT_W;
    } catch (_) {
      return INSPECTOR_DEFAULT_W;
    }
  });

  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('editor.rightSidebarCollapsed') === 'true';
    } catch (_) {
      return false;
    }
  });

  const applyInspectorW = useCallback((nextW) => {
    const clamped = Math.max(INSPECTOR_MIN_W, Math.min(INSPECTOR_MAX_W, nextW));
    setInspectorW(clamped);
    try { localStorage.setItem('editor.inspectorW', String(clamped)); } catch (_) {}
  }, []);

  const toggleRightSidebar = useCallback(() => {
    setRightSidebarCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem('editor.rightSidebarCollapsed', String(next)); } catch (_) {}
      return next;
    });
  }, []);

  // Mobile preview height
  const [mobilePreviewH, setMobilePreviewH] = useState(() => {
    const fallback = Math.round(window.innerHeight * MOBILE_PREVIEW_DEFAULT);
    try {
      const saved = parseInt(localStorage.getItem('editor.mobilePreviewH') || '', 10);
      if (!Number.isFinite(saved)) return fallback;
      return Math.max(MOBILE_PREVIEW_MIN_H, Math.min(saved, Math.round(window.innerHeight * 0.9)));
    } catch (_) {
      return fallback;
    }
  });

  const applyMobilePreviewH = useCallback((px) => {
    const box = mobileWrapRef.current?.getBoundingClientRect();
    const reserve = MOBILE_TAB_ROW_H + (Number.isFinite(mobileTimelineH) ? mobileTimelineH : 0);
    const max = box ? Math.max(MOBILE_PREVIEW_MIN_H, box.height - reserve) : 640;
    const clamped = Math.min(max, Math.max(MOBILE_PREVIEW_MIN_H, Math.round(px)));
    setMobilePreviewH(clamped);
    try { localStorage.setItem('editor.mobilePreviewH', String(clamped)); } catch (_) {}
  }, [mobileTimelineH]);

  const resetPanelSizes = useCallback(() => {
    setTimelineH(TIMELINE_DEFAULT_H);
    setAssetW(ASSET_DEFAULT_W);
    setInspectorW(INSPECTOR_DEFAULT_W);
    setMobilePreviewH(Math.round(window.innerHeight * MOBILE_PREVIEW_DEFAULT));
    setLeftSidebarCollapsed(false);
    setRightSidebarCollapsed(false);
    const keys = [
      'capcut_timeline_h',
      'editor.assetW',
      'editor.inspectorW',
      'editor.mobilePreviewH',
      'editor.leftSidebarCollapsed',
      'editor.rightSidebarCollapsed',
    ];
    for (const key of keys) {
      try { localStorage.removeItem(key); } catch (_) {}
    }
  }, []);

  return {
    timelineH,
    setTimelineH,
    applyTimelineH,
    resizeRef,
    assetW,
    setAssetW,
    applyAssetW,
    leftSidebarCollapsed,
    setLeftSidebarCollapsed,
    toggleLeftSidebar,
    assetResizeRef,
    inspectorW,
    setInspectorW,
    applyInspectorW,
    rightSidebarCollapsed,
    setRightSidebarCollapsed,
    toggleRightSidebar,
    inspectorResizeRef,
    mobilePreviewH,
    setMobilePreviewH,
    applyMobilePreviewH,
    mobileWrapRef,
    mobileResizeRef,
    resetPanelSizes,
  };
}
