import React, { useState, useEffect, Suspense, lazy } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorBoundary from './components/ErrorBoundary';
import ShortcutsModal from './components/ShortcutsModal';
import { Toast } from './components/ui';
import { useKeyboardShortcuts } from './hooks';
import { getSystemStatus, getRawVideos, getExports, updateAngleStatus } from './api';

// ── Lazy-loaded view chunks for Code Splitting ──
const ProductToClip = lazy(() => import('./components/ProductToClip'));
const ContentTrackerHub = lazy(() => import('./components/ContentTrackerHub'));
const EditorShell = lazy(() => import('./components/editor/EditorShell'));
const ExportGallery = lazy(() => import('./components/ExportGallery'));
const MediaAssetsHub = lazy(() => import('./components/MediaAssetsHub'));
const SystemSettings = lazy(() => import('./components/SystemSettings'));

import { angleToForm } from './lib/angleToForm';
import { applyUiScale, initUiScale } from './lib/uiScale';
import { TaskProvider } from './context/TaskContext';
import { ActivityDrawer, GlobalTaskNotification, ActivityIndicatorButton, GlobalLiveRenderWidget } from './components/ActivityCenter';

export default function App() {

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
  const [activeProductContext, setActiveProductContext] = useState(() => {
    try {
      const raw = localStorage.getItem('capcut_active_product_context');
      return raw ? JSON.parse(raw) : null;
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
    if (tab === 'gallery') {
      const target = extra?.targetId || extra?.taskResult?.project_name || extra?.taskResult?.final_video_path || extra?.taskResult?.mp4 || extra?.task?.payload?.project_name;
      if (target) {
        setHighlightExportVideo(target);
      }
      refreshData();
    }
    setActiveTab(tab);
  };

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
                    />
                  </Suspense>
                )}

                {/* SECTION: คลังสินค้า & Tracker (Menu 2) */}
                {activeTab === 'tracker' && (
                  <Suspense fallback={<LoadingSpinner message="กำลังโหลด Content Tracker..." />}>
                    <ContentTrackerHub
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
          onNavigateToEditor={() => setActiveTab('editor')}
          onNavigateToGallery={() => handleNavigateTab('gallery')}
        />
      </div>
    </TaskProvider>
  );
}
