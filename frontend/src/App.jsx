import React, { useState, useEffect, Suspense, lazy } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import PresetsBar from './components/PresetsBar';
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
const SystemAssets = lazy(() => import('./components/SystemAssets'));

import { DEFAULT_STUDIO_FORM, getSavedStudioForm } from './lib/studioDefaults';
import { angleToForm } from './lib/angleToForm';

export default function App() {
  const savedForm = getSavedStudioForm();

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

  // 4. Studio Form State with Persistence
  const [selectedVideo, setSelectedVideo] = useState(savedForm.selectedVideo || '');
  const [productName, setProductName] = useState(savedForm.productName);
  const [hookTitle, setHookTitle] = useState(savedForm.hookTitle);
  const [painPoint, setPainPoint] = useState(savedForm.painPoint);
  const [priceDeal, setPriceDeal] = useState(savedForm.priceDeal);
  const [keyFeatures, setKeyFeatures] = useState(savedForm.keyFeatures);
  const [customScript, setCustomScript] = useState(savedForm.customScript);
  const [useCustomScript, setUseCustomScript] = useState(savedForm.useCustomScript);

  // Audio & Typography State
  const [voiceMode, setVoiceMode] = useState(savedForm.voiceMode);
  const [voiceGender, setVoiceGender] = useState(savedForm.voiceGender);
  const [voiceSpeed, setVoiceSpeed] = useState(savedForm.voiceSpeed);
  const [voicePreset, setVoicePreset] = useState(savedForm.voicePreset);
  const [adTone, setAdTone] = useState(savedForm.adTone);
  const [humanVoiceAudio, setHumanVoiceAudio] = useState(null);
  const [fontName, setFontName] = useState(savedForm.fontName);
  const [bilingualSubtitles, setBilingualSubtitles] = useState(savedForm.bilingualSubtitles);
  const [stickerBadge, setStickerBadge] = useState(savedForm.stickerBadge);
  const [bgmName, setBgmName] = useState(savedForm.bgmName);
  const [lutName, setLutName] = useState(savedForm.lutName);

  // Auto-save Studio Form to localStorage on any state change
  useEffect(() => {
    const formData = {
      selectedVideo,
      productName,
      hookTitle,
      painPoint,
      priceDeal,
      keyFeatures,
      customScript,
      useCustomScript,
      voiceMode,
      voiceGender,
      voiceSpeed,
      voicePreset,
      adTone,
      fontName,
      bilingualSubtitles,
      stickerBadge,
      bgmName,
      lutName
    };
    try {
      localStorage.setItem('capcut_studio_form', JSON.stringify(formData));
    } catch (e) {
      console.error('Failed to auto-save studio form:', e);
    }
  }, [
    selectedVideo, productName, hookTitle, painPoint, priceDeal,
    keyFeatures, customScript, useCustomScript, voiceMode, voiceGender,
    voiceSpeed, voicePreset, adTone, fontName, bilingualSubtitles,
    stickerBadge, bgmName, lutName
  ]);

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
      const formData = {
        selectedVideo,
        productName,
        hookTitle,
        painPoint,
        priceDeal,
        keyFeatures,
        customScript,
        useCustomScript,
        voiceMode,
        voiceGender,
        voiceSpeed,
        voicePreset,
        adTone,
        fontName,
        bilingualSubtitles,
        stickerBadge,
        bgmName,
        lutName
      };
      localStorage.setItem('capcut_studio_form', JSON.stringify(formData));
      setGlobalToast('บันทึกข้อมูลฟอร์มและสถานะระบบเรียบร้อยแล้ว (Auto-Saved)');
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

      if (!selectedVideo && vRes.videos?.length > 0) {
        setSelectedVideo(vRes.videos[0].path);
      }
    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  const handleSelectPreset = (data) => {
    setProductName(data.productName);
    setHookTitle(data.hookTitle);
    setPainPoint(data.painPoint);
    setPriceDeal(data.priceDeal);
    setKeyFeatures(data.keyFeatures);
    setUseCustomScript(false);
  };

  const handleSelectAngle = (index) => {
    if (!activeProductContext || !activeProductContext.angles || !activeProductContext.angles[index]) return;
    setSelectedAngleIndex(index);
    const patch = angleToForm(activeProductContext.angles[index], activeProductContext);
    if (!patch) return;

    setProductName(patch.productName);
    setHookTitle(patch.hookTitle);
    setCustomScript(patch.customScript);
    setUseCustomScript(patch.useCustomScript);
    setKeyFeatures(patch.keyFeatures);
    setPainPoint(patch.painPoint);
    setPriceDeal(patch.priceDeal);
    if (patch.adTone) setAdTone(patch.adTone);
  };

  const handleVideoUploaded = (newFile) => {
    setVideos(prev => [newFile, ...prev]);
    setSelectedVideo(newFile.path);
  };

  const handleVideoDeleted = (deletedPath) => {
    setVideos(prev => {
      const remaining = prev.filter(v => v.path !== deletedPath && v.rel_path !== deletedPath);
      if (selectedVideo === deletedPath && remaining.length > 0) {
        setSelectedVideo(remaining[0].path);
      } else if (remaining.length === 0) {
        setSelectedVideo('');
      }
      return remaining;
    });
  };

  const handleApplyScriptFromLab = (data) => {
    if (data.productId && data.angleId) {
      setActiveAngleContext({ productId: data.productId, angleId: data.angleId });
    }
    if (data.fullProduct) {
      setActiveProductContext(data.fullProduct);
      setSelectedAngleIndex(data.angleIndex || 0);
    } else {
      setActiveProductContext({
        id: data.productId || 'custom',
        title: data.productName || 'สินค้า',
        name: data.productName || 'สินค้า',
        description: data.keyFeatures || '',
        price_note: data.priceDeal || '',
        images: data.selectedVideo ? [{ rel_path: data.selectedVideo, name: 'media' }] : []
      });
    }
    if (data.productName) setProductName(data.productName);
    if (data.hookTitle) setHookTitle(data.hookTitle);
    if (data.customScript) {
      setCustomScript(data.customScript);
      setUseCustomScript(true);
    }
    if (data.keyFeatures) setKeyFeatures(data.keyFeatures);
    if (data.painPoint) setPainPoint(data.painPoint);
    if (data.priceDeal) setPriceDeal(data.priceDeal);
    if (data.adTone) setAdTone(data.adTone);

    setActiveTab('editor');
  };

  const handleResetStudioForm = () => {
    if (!window.confirm('คุณต้องการรีเซ็ตข้อมูลทั้งหมดใน Studio กลับเป็นค่าเริ่มต้นใช่หรือไม่?')) {
      return;
    }
    setSelectedVideo('');
    setProductName(DEFAULT_STUDIO_FORM.productName);
    setHookTitle(DEFAULT_STUDIO_FORM.hookTitle);
    setPainPoint(DEFAULT_STUDIO_FORM.painPoint);
    setPriceDeal(DEFAULT_STUDIO_FORM.priceDeal);
    setKeyFeatures(DEFAULT_STUDIO_FORM.keyFeatures);
    setCustomScript(DEFAULT_STUDIO_FORM.customScript);
    setUseCustomScript(DEFAULT_STUDIO_FORM.useCustomScript);
    setVoiceMode(DEFAULT_STUDIO_FORM.voiceMode);
    setVoiceGender(DEFAULT_STUDIO_FORM.voiceGender);
    setVoiceSpeed(DEFAULT_STUDIO_FORM.voiceSpeed);
    setVoicePreset(DEFAULT_STUDIO_FORM.voicePreset);
    setAdTone(DEFAULT_STUDIO_FORM.adTone);
    setHumanVoiceAudio(null);
    setFontName(DEFAULT_STUDIO_FORM.fontName);
    setBilingualSubtitles(DEFAULT_STUDIO_FORM.bilingualSubtitles);
    setStickerBadge(DEFAULT_STUDIO_FORM.stickerBadge);
    setBgmName(DEFAULT_STUDIO_FORM.bgmName);
    setLutName(DEFAULT_STUDIO_FORM.lutName);
    setActiveProductContext(null);
    setSelectedAngleIndex(0);
    setActiveAngleContext(null);

    localStorage.removeItem('capcut_studio_form');
    localStorage.removeItem('capcut_active_product_context');
    localStorage.removeItem('capcut_selected_angle_index');
    localStorage.removeItem('capcut_active_angle_context');
  };

  const handleRenderSuccess = async (result) => {
    if (activeAngleContext?.productId && activeAngleContext?.angleId) {
      try {
        const videoRelPath = result.final_video_path || result.video_path || result.output_path || result.project_name || '';
        await updateAngleStatus(activeAngleContext.productId, activeAngleContext.angleId, 'rendered', videoRelPath);
      } catch (err) {
        console.error('Failed to auto-update angle status on render:', err);
      }
    }
    refreshData();
  };

  return (
    <div className={`flex h-screen overflow-hidden ${uiFont} bg-[#07090E] text-slate-100`}>
      {/* ── Sidebar (desktop: left, mobile: bottom) ── */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status={status}
      />

      {/* ── Main Area ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#07090E]">
        {/* ── Topbar (Hidden on Manual Editor to maximize editing workspace) ── */}
        {activeTab !== 'editor' && (
          <Topbar
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            status={status}
            uiFont={uiFont}
            setUiFont={handleUiFontChange}
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
                  onAngleChange={handleSelectAngle}
                  onGoToProductFlow={() => setActiveTab('flow')}
                  onVideoUploaded={handleVideoUploaded}
                />
              </Suspense>
            </main>
          ) : (
          <main className="flex-1 overflow-y-auto overflow-x-hidden px-3 sm:px-6 lg:px-8 py-5 pb-20 md:pb-8 w-full min-w-0">
            <div className="max-w-[1600px] mx-auto animate-fadeIn space-y-5 w-full min-w-0">

              {/* SECTION: สินค้า → คลิป (Menu 1) */}
              {activeTab === 'flow' && (
                <Suspense fallback={<LoadingSpinner message="กำลังโหลดโมดูลสินค้า → คลิป..." />}>
                  <ProductToClip
                    status={status}
                    videos={videos}
                    onRefresh={refreshData}
                    onApplyToStudio={handleApplyScriptFromLab}
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
                  />
                </Suspense>
              )}



              {/* SECTION: System & Assets */}
              {activeTab === 'assets' && (
                <Suspense fallback={<LoadingSpinner message="กำลังโหลด System & Assets Hub..." />}>
                  <SystemAssets status={status} />
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
    </div>
  );
}
