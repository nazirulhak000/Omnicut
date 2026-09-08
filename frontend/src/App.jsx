import React, { useState, useEffect, useRef, Suspense, lazy } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorBoundary from './components/ErrorBoundary';
import ShortcutsModal from './components/ShortcutsModal';
import { Toast } from './components/ui';
import { useKeyboardShortcuts } from './hooks';
import { getSystemStatus, getRawVideos, getExports, updateAngleStatus, getProducts } from './api';

// ── Lazy-loaded view chunks for Code Splitting ──
const ProductToClip = lazy(() => import('./components/ProductToClip'));
const ContentTrackerHub = lazy(() => import('./components/ContentTrackerHub'));
const EditorShell = lazy(() => import('./components/editor/EditorShell'));
const ExportGallery = lazy(() => import('./components/ExportGallery'));
const MediaAssetsHub = lazy(() => import('./components/MediaAssetsHub'));
const SystemSettings = lazy(() => import('./components/SystemSettings'));
const MobileQuickPostPage = lazy(() => import('./components/MobileQuickPostPage'));

import { angleToForm } from './lib/angleToForm';
import { applyUiScale, initUiScale } from './lib/uiScale';
import { TaskProvider } from './context/TaskContext';
import { ActivityDrawer, GlobalTaskNotification, ActivityIndicatorButton, GlobalLiveRenderWidget } from './components/ActivityCenter';

export default function App() {
  // Check if opened via Mobile Quick Post QR code
  const [isQuickPostMode] = useState(() => {
    try {
      const p = new URLSearchParams(window.location.search);
      return p.get('quick_post') === '1' || p.get('mobile_post') === '1';
    } catch {
      return false;
    }
  });

  // 1. Active Tab Persistence with Fallback Migration
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem('capcut_active_tab') || 'flow';
    if (saved === 'sub_srt') return 'editor';
    if (saved === 'script_lab') return 'flow';
    // Studio was folded into the editor -- anyone whose last tab was studio
    // would otherwise land on a screen that no longer renders anything.
    if (saved === 'studio') return 'editor';
    return saved;
  });

  useEffect(() => {
    localStorage.setItem('capcut_active_tab', activeTab);
  }, [activeTab]);

  const [status, setStatus] = useState(null);
  const [videos, setVideos] = useState([]);
  const [exportsList, setExportsList] = useState([]);

  // 2. Global UI Font of the Application (Saved in localStorage)
  const [uiFont, setUiFont] = useState(() => localStorage.getItem('capcut_ui_font') || 'font-prompt');
  // Interface size. initUiScale writes --ui-scale before the first paint so a
  // saved choice does not flash at the default size first.
  const [uiScale, setUiScaleState] = useState(() => initUiScale());

  const handleUiScaleChange = (id) => setUiScaleState(applyUiScale(id));

  const handleUiFontChange = (fontClass) => {
    setUiFont(fontClass);
    localStorage.setItem('capcut_ui_font', fontClass);
  };

  // 3. Active Product Context Persistence (from Menu 1 & Menu 2)
  // Tracks whether the *current* activeProductContext is the one that was
  // lazily hydrated from localStorage on mount (and hasn't yet been
  // revalidated against the backend), vs. a fresh selection made this
  // session. Only the former should ever be silently cleared/replaced by
  // the revalidation effect below -- a brand-new pick must never look stale.
  const cameFromLocalStorageRef = useRef(false);
  const [activeProductContext, setActiveProductContext] = useState(() => {
    try {
      const raw = localStorage.getItem('capcut_active_product_context');
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (parsed) cameFromLocalStorageRef.current = true;
      return parsed;
    } catch {
      return null;
    }
  });

  const [selectedAngleIndex, setSelectedAngleIndex] = useState(() => {
    const raw = localStorage.getItem('capcut_selected_angle_index');
    return raw ? parseInt(raw, 10) || 0 : 0;
  });

  const [activeAngleContext, setActiveAngleContext] = useState(() => {
    try {
      const raw = localStorage.getItem('capcut_active_angle_context');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  const [selectedProductIdForFlow, setSelectedProductIdForFlow] = useState(null);
  // Plain ref, not state: this is fire-and-forget data for ProductToClip's
  // next mount, read exactly once. As state, clearing it after the child
  // consumes it becomes a second prop change the child observes -- which
  // collides with StrictMode's dev-only double-invoke of mount effects,
  // where the second synthetic mount sees the already-cleared value and
  // stomps the just-restored angle back to index 0.
  const pendingFlowAngleIdRef = useRef(null);
  const [initialProjectNameToLoad, setInitialProjectNameToLoad] = useState(null);


  // Auto-save Context Objects to localStorage
  useEffect(() => {
    try {
      if (activeProductContext) {
        localStorage.setItem('capcut_active_product_context', JSON.stringify(activeProductContext));
      } else {
        localStorage.removeItem('capcut_active_product_context');
      }
      localStorage.setItem('capcut_selected_angle_index', String(selectedAngleIndex));
      if (activeAngleContext) {
        localStorage.setItem('capcut_active_angle_context', JSON.stringify(activeAngleContext));
      } else {
        localStorage.removeItem('capcut_active_angle_context');
      }
    } catch (e) {
      console.error('Failed to save context to localStorage:', e);
    }
  }, [activeProductContext, selectedAngleIndex, activeAngleContext]);

  // 5. Global Keyboard Shortcuts & Modal State
  const [showShortcutsModal, setShowShortcutsModal] = useState(false);
  const [globalToast, setGlobalToast] = useState(null);

  useKeyboardShortcuts({
    onTabChange: (tab) => {
      setActiveTab(tab);
    },
    onSave: () => {
      // The create panel persists its form on every change, so there is
      // nothing to flush here -- just say so.
      setGlobalToast('บันทึกข้อมูลฟอร์มเรียบร้อยแล้ว (บันทึกอัตโนมัติอยู่แล้ว)');
      setTimeout(() => setGlobalToast(null), 2500);
    },
    onToggleShortcutsModal: () => {
      setShowShortcutsModal(prev => !prev);
    },
    onEscape: () => {
      setShowShortcutsModal(false);
    }
  });

  const refreshData = async () => {
    try {
      const [sRes, vRes, eRes] = await Promise.all([
        getSystemStatus(),
        getRawVideos(),
        getExports()
      ]);
      setStatus(sRes);
      setVideos(vRes.videos || []);
      setExportsList(eRes.exports || []);

    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  // Revalidate a product/angle context that was hydrated from localStorage
  // on mount against the backend's current product list. Cached data can go
  // stale silently (product renamed/edited/deleted since the last session),
  // so once fresh products are available: drop the cached context if the
  // product no longer exists, or replace it with the fresh copy if it does
  // but differs. Runs exactly once, and only for context that came from
  // localStorage -- a selection made during this session is never touched.
  useEffect(() => {
    if (!cameFromLocalStorageRef.current) return;

    let cancelled = false;

    (async () => {
      const productId = activeProductContext?.id;
      // Synthetic contexts (e.g. an ad-hoc script with no saved product
      // behind it) have no backend record to revalidate against -- leave
      // them alone.
      if (!productId || productId === 'custom') {
        cameFromLocalStorageRef.current = false;
        return;
      }

      try {
        const fresh = await getProducts();
        const freshList = Array.isArray(fresh) ? fresh : (fresh?.products || []);
        if (cancelled) return;

        const freshProduct = freshList.find((p) => p.id === productId);

        if (!freshProduct) {
          // Deleted since it was cached -- fall back to "nothing selected".
          setActiveProductContext(null);
          setSelectedAngleIndex(0);
          setActiveAngleContext(null);
        } else if (JSON.stringify(freshProduct) !== JSON.stringify(activeProductContext)) {
          // Still exists but edited/renamed/re-angled -- the cache should
          // only remember *which* product/angle was selected, not the
          // product's field values, so replace it with the current copy.
          setActiveProductContext(freshProduct);
          if (!freshProduct.angles?.[selectedAngleIndex]) {
            setSelectedAngleIndex(0);
          }
        }
      } catch (err) {
        // Backend unreachable/erroring -- keep showing the cached context
        // rather than clearing it out from under the user.
        console.error('Failed to revalidate cached product context:', err);
      } finally {
        if (!cancelled) cameFromLocalStorageRef.current = false;
      }
    })();

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectAngle = (index) => {
    // The create panel maps the angle to form fields itself (lib/angleToForm),
    // so switching angle is only a matter of which one is current.
    if (!activeProductContext?.angles?.[index]) return;
    setSelectedAngleIndex(index);
  };

  const handleVideoUploaded = (newFile) => {
    setVideos((prev) => [newFile, ...prev]);
  };

  const handleVideoDeleted = (deletedPath) => {
    setVideos((prev) => prev.filter((v) => v.path !== deletedPath && v.rel_path !== deletedPath));
  };

  const handleApplyScriptFromLab = (data) => {
    if (data.productId && data.angleId) {
      setActiveAngleContext({ productId: data.productId, angleId: data.angleId });
    }

    if (data.openProjectName) {
      setInitialProjectNameToLoad(data.openProjectName);
    } else {
      setInitialProjectNameToLoad(null);
    }

    if (data.fullProduct) {
      setActiveProductContext(data.fullProduct);
      setSelectedAngleIndex(data.angleIndex || 0);
    } else {
      // No saved product behind this script: wrap what was handed over as a
      // single angle so the editor's panel fills itself the same way.
      setActiveProductContext({
        id: data.productId || 'custom',
        title: data.productName || 'สินค้า',
        name: data.productName || 'สินค้า',
        description: data.keyFeatures || '',
        price_note: data.priceDeal || '',
        images: data.selectedVideo ? [{ rel_path: data.selectedVideo, name: 'media' }] : [],
        angles: [{
          angle_name: 'บทที่เพิ่งเลือก',
          product_name: data.productName || 'สินค้า',
          hook_title: [data.hookBrand, data.hookModel, data.hookLabel].filter(Boolean).join(' ') || '',
          script_text: data.customScript || '',
          key_features: data.keyFeatures || '',
          pain_point: data.painPoint || '',
          price_deal: data.priceDeal || '',
          ad_tone: data.adTone,
        }],
      });
      setSelectedAngleIndex(0);
    }

    setActiveTab('editor');
  };


  const handleRenderSuccess = async (result) => {
    if (activeAngleContext?.productId && activeAngleContext?.angleId) {
      try {
        const videoRelPath = result.final_video_path || result.video_path || result.output_path || '';
        const projectName = result.project_name || '';
        await updateAngleStatus(activeAngleContext.productId, activeAngleContext.angleId, 'rendered', videoRelPath, projectName);
      } catch (err) {
        console.error('Failed to auto-update angle status on render:', err);
      }
    }
    refreshData();
  };

  const [highlightExportVideo, setHighlightExportVideo] = useState(null);

  const handleNavigateTab = (tab, extra = null) => {
    if (tab === 'flow') {
      pendingFlowAngleIdRef.current = extra?.angleId || null;
    } else if (tab === 'gallery') {
      const target = extra?.targetId || extra?.taskResult?.project_name || extra?.taskResult?.final_video_path || extra?.taskResult?.mp4 || extra?.task?.payload?.project_name;
      if (target) {
        setHighlightExportVideo(target);
      }
      refreshData();
    } else if (tab === 'editor') {
      const projName = extra?.projectName || extra?.targetId || extra?.taskResult?.project_name || extra?.task?.payload?.project_name || extra?.task?.target_id;
      if (projName) {
        setInitialProjectNameToLoad(projName);
      }
      if (extra?.taskResult?.saved_product) {
        setActiveProductContext(extra.taskResult.saved_product);
      }
      refreshData();
    }
    setActiveTab(tab);
  };

  if (isQuickPostMode) {
    return (
      <div className={`h-screen w-screen overflow-y-auto bg-[#070A12] ${uiFont}`}>
        <Suspense fallback={<LoadingSpinner message="กำลังเปิดตัวช่วยโพสต์ Quick Post..." />}>
          <MobileQuickPostPage onExit={() => { window.location.href = window.location.pathname; }} />
        </Suspense>
      </div>
    );
  }

  return (
    <TaskProvider
      onNavigateTab={handleNavigateTab}
      onSelectProductForFlow={setSelectedProductIdForFlow}
    >
      <div className={`flex h-screen overflow-hidden ${uiFont} bg-[#07090E] text-slate-100`}>
        {/* ── Sidebar (desktop: left, mobile: bottom) ── */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          status={status}
        />

        {/* ── Main Area ── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#07090E] relative">
          {/* The editor renders its own activity indicator inside the header
              (EditorShell) -- floating it here covered the render button. */}

          {/* ── Topbar (Hidden on Manual Editor to maximize editing workspace) ── */}
          {activeTab !== 'editor' && (
            <Topbar
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              status={status}
              uiFont={uiFont}
              setUiFont={handleUiFontChange}
              uiScale={uiScale}
              setUiScale={handleUiScaleChange}
              onOpenShortcuts={() => setShowShortcutsModal(true)}
              onRefresh={refreshData}
              activeProductContext={activeProductContext}
              exportsCount={exportsList.length}
              videosCount={videos.length}
            />
          )}

          {/* ── Content (Enforce overflow-x-hidden so page never shifts horizontally under sidebar) ── */}
          <ErrorBoundary>
            {activeTab === 'editor' ? (
              <main className="min-h-0 flex-1 overflow-hidden p-0 md:p-1.5 pb-16 md:pb-1.5">
                <Suspense fallback={<LoadingSpinner message="กำลังโหลด Video Editor..." />}>
                  <EditorShell
                    key={initialProjectNameToLoad || 'editor-shell'}
                    videos={videos}
                    productContext={activeProductContext}
                    angleIndex={selectedAngleIndex}
                    initialProjectName={initialProjectNameToLoad}
                    onAngleChange={handleSelectAngle}
                    onGoToProductFlow={() => setActiveTab('flow')}
                    onVideoUploaded={handleVideoUploaded}
                  />
                </Suspense>
              </main>
            ) : (
            <main className="flex-1 overflow-y-auto overflow-x-hidden px-3 sm:px-5 lg:px-6 py-5 pb-20 md:pb-8 w-full min-w-0">
              <div className="mx-auto w-full min-w-0 max-w-[2200px] animate-fadeIn space-y-5">

                {/* SECTION: สินค้า → คลิป (Menu 1) */}
                {activeTab === 'flow' && (
                  <Suspense fallback={<LoadingSpinner message="กำลังโหลดโมดูลสินค้า → คลิป..." />}>
                    <ProductToClip
                      status={status}
                      videos={videos}
                      onRefresh={refreshData}
                      onApplyToStudio={handleApplyScriptFromLab}
                      onGoToGallery={() => setActiveTab('gallery')}
                      selectedProductId={selectedProductIdForFlow}
                      consumePendingAngleId={() => {
                        const id = pendingFlowAngleIdRef.current;
                        pendingFlowAngleIdRef.current = null;
                        return id;
                      }}
                    />
                  </Suspense>
                )}

                {/* SECTION: คลังสินค้า & Tracker (Menu 2) */}
                {activeTab === 'tracker' && (
                  <Suspense fallback={<LoadingSpinner message="กำลังโหลด Content Tracker..." />}>
                    <ContentTrackerHub
                      status={status}
                      onApplyToStudio={handleApplyScriptFromLab}
                      onRefresh={refreshData}
                      onGoToEditor={() => setActiveTab('editor')}
                      onGoToFlow={(productId) => {
                        if (productId) setSelectedProductIdForFlow(productId);
                        setActiveTab('flow');
                      }}
                      onGoToGallery={() => setActiveTab('gallery')}
                    />
                  </Suspense>
                )}


                {/* SECTION: Export Gallery */}
                {activeTab === 'gallery' && (
                  <Suspense fallback={<LoadingSpinner message="กำลังโหลด Export Gallery..." />}>
                    <ExportGallery
                      exportsList={exportsList}
                      onRefresh={refreshData}
                      initialHighlightVideo={highlightExportVideo}
                      onClearHighlightVideo={() => setHighlightExportVideo(null)}
                      status={status}
                    />
                  </Suspense>
                )}



                {/* SECTION: Media Assets Hub */}
                {activeTab === 'assets' && (
                  <Suspense fallback={<LoadingSpinner message="กำลังโหลด Media Assets Hub..." />}>
                    <MediaAssetsHub status={status} />
                  </Suspense>
                )}

                {/* SECTION: System Settings & Token Analytics */}
                {(activeTab === 'settings' || activeTab === 'dashboard') && (
                  <Suspense fallback={<LoadingSpinner message="กำลังโหลด System Settings & Analytics..." />}>
                    <SystemSettings
                      status={status}
                      uiFont={uiFont}
                      setUiFont={handleUiFontChange}
                      uiScale={uiScale}
                      setUiScale={handleUiScaleChange}
                      initialSubTab="tokens"
                    />
                  </Suspense>
                )}
              </div>
            </main>
            )}
          </ErrorBoundary>
        </div>

        {/* ── Global Keyboard Shortcuts Cheat Sheet Modal ── */}
        <ShortcutsModal
          isOpen={showShortcutsModal}
          onClose={() => setShowShortcutsModal(false)}
        />

        {/* ── Global Toast for Quick Save / Actions ── */}
        <Toast
          message={globalToast}
          onClose={() => setGlobalToast(null)}
        />

        {/* ── Global Persistent Activity Drawer & Task Notifications ── */}
        <ActivityDrawer />
        <GlobalTaskNotification />
        <GlobalLiveRenderWidget
          currentTab={activeTab}
          onNavigateToEditor={(projName) => handleNavigateTab('editor', { projectName: projName })}
          onNavigateToGallery={() => handleNavigateTab('gallery')}
        />
      </div>
    </TaskProvider>
  );
}
