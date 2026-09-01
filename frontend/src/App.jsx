import React, { useState, useEffect, Suspense, lazy } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import PresetsBar from './components/PresetsBar';
import StudioStep1Media from './components/StudioStep1Media';
import StudioStep2Script from './components/StudioStep2Script';
import StudioStep3Audio from './components/StudioStep3Audio';
import StudioStep4Render from './components/StudioStep4Render';
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

const DEFAULT_STUDIO_FORM = {
  selectedVideo: '',
  productName: 'Esseger สายชาร์จแม่เหล็ก',
  hookTitle: 'อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก',
  painPoint: 'สายชาร์จพังง่าย เสียบยากในที่มืด',
  priceDeal: 'ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง',
  keyFeatures: 'แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก',
  customScript: '',
  useCustomScript: false,
  voiceMode: 'gemini_tts',
  voiceGender: 'male',
  voiceSpeed: '+15%',
  voicePreset: 'gemini_puck_male_hype',
  adTone: 'commercial_premium',
  fontName: 'IBMPlex',
  bilingualSubtitles: true,
  stickerBadge: 'badge_flash_sale_3d.png',
  bgmName: null,
  lutName: null
};

function getSavedStudioForm() {
  try {
    const raw = localStorage.getItem('capcut_studio_form');
    if (raw) {
      const parsed = JSON.parse(raw);
      return { ...DEFAULT_STUDIO_FORM, ...parsed };
    }
  } catch (e) {
    console.error('Failed to parse saved studio form:', e);
  }
  return DEFAULT_STUDIO_FORM;
}

export default function App() {
  const savedForm = getSavedStudioForm();

  // 1. Active Tab Persistence with Fallback Migration
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem('capcut_active_tab') || 'flow';
    if (saved === 'sub_srt') return 'editor';
    if (saved === 'script_lab') return 'flow';
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
    const angle = activeProductContext.angles[index];
    const scriptText = Array.isArray(angle.script_lines)
      ? angle.script_lines.join('\n')
      : (angle.script_text || '');

    setProductName(angle.product_name || activeProductContext.title || 'สินค้า');
    setHookTitle(angle.hook_title || '');
    setCustomScript(scriptText);
    setUseCustomScript(true);
    setKeyFeatures(angle.key_features || activeProductContext.description || '');
    setPainPoint(angle.pain_point || '');
    setPriceDeal(angle.price_deal || activeProductContext.price_note || '');
    if (angle.ad_tone) setAdTone(angle.ad_tone);
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

    setActiveTab('studio');
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
                <EditorShell videos={videos} />
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

              {/* SECTION: 1-Click Studio (Menu 3) */}
              {activeTab === 'studio' && (
                <div className="space-y-4">
                  {/* Active Product Angle Switcher / Presets Bar */}
                  <PresetsBar
                    activeProductContext={activeProductContext}
                    selectedAngleIndex={selectedAngleIndex}
                    onSelectAngle={handleSelectAngle}
                    onSelectPreset={handleSelectPreset}
                    onGoToProductFlow={() => setActiveTab('flow')}
                    onClearProductContext={() => setActiveProductContext(null)}
                    onResetForm={handleResetStudioForm}
                  />

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5 items-start">
                    {/* Left Column: Stage 1 (Media) + Stage 2 (Script) */}
                    <div className="space-y-4 sm:space-y-5">
                      <StudioStep1Media
                        videos={videos}
                        selectedVideo={selectedVideo}
                        setSelectedVideo={setSelectedVideo}
                        productName={productName}
                        activeProductContext={activeProductContext}
                        onVideoUploaded={handleVideoUploaded}
                        onVideoDeleted={handleVideoDeleted}
                      />
                      <StudioStep2Script
                        productName={productName}
                        setProductName={setProductName}
                        hookTitle={hookTitle}
                        setHookTitle={setHookTitle}
                        painPoint={painPoint}
                        setPainPoint={setPainPoint}
                        priceDeal={priceDeal}
                        setPriceDeal={setPriceDeal}
                        keyFeatures={keyFeatures}
                        setKeyFeatures={setKeyFeatures}
                        customScript={customScript}
                        setCustomScript={setCustomScript}
                        useCustomScript={useCustomScript}
                        setUseCustomScript={setUseCustomScript}
                      />
                    </div>

                    {/* Right Column: Stage 3 (Audio/Style) + Stage 4 (Render) */}
                    <div className="space-y-4 sm:space-y-5">
                      <StudioStep3Audio
                        voiceMode={voiceMode}
                        setVoiceMode={setVoiceMode}
                        voiceGender={voiceGender}
                        setVoiceGender={setVoiceGender}
                        voiceSpeed={voiceSpeed}
                        setVoiceSpeed={setVoiceSpeed}
                        voicePreset={voicePreset}
                        setVoicePreset={setVoicePreset}
                        adTone={adTone}
                        setAdTone={setAdTone}
                        humanVoiceAudio={humanVoiceAudio}
                        setHumanVoiceAudio={setHumanVoiceAudio}
                        productName={productName}
                        fontName={fontName}
                        setFontName={setFontName}
                        bilingualSubtitles={bilingualSubtitles}
                        setBilingualSubtitles={setBilingualSubtitles}
                        stickerBadge={stickerBadge}
                        setStickerBadge={setStickerBadge}
                        bgmName={bgmName}
                        setBgmName={setBgmName}
                        lutName={lutName}
                        setLutName={setLutName}
                      />
                      <StudioStep4Render
                        productName={productName}
                        selectedVideo={selectedVideo}
                        keyFeatures={keyFeatures}
                        painPoint={painPoint}
                        priceDeal={priceDeal}
                        hookTitle={hookTitle}
                        customScript={customScript}
                        useCustomScript={useCustomScript}
                        voiceMode={voiceMode}
                        voiceGender={voiceGender}
                        voiceSpeed={voiceSpeed}
                        voicePreset={voicePreset}
                        adTone={adTone}
                        humanVoiceAudio={humanVoiceAudio}
                        fontName={fontName}
                        bilingualSubtitles={bilingualSubtitles}
                        stickerBadge={stickerBadge}
                        bgmName={bgmName}
                        lutName={lutName}
                        onRenderSuccess={handleRenderSuccess}
                        onGoToGallery={() => setActiveTab('gallery')}
                      />
                    </div>
                  </div>
                </div>
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
