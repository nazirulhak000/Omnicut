import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import PresetsBar from './components/PresetsBar';
import StudioStep1Media from './components/StudioStep1Media';
import StudioStep2Script from './components/StudioStep2Script';
import StudioStep3Audio from './components/StudioStep3Audio';
import StudioStep4Render from './components/StudioStep4Render';
import ManualEditor from './components/ManualEditor';
import ExportGallery from './components/ExportGallery';
import ScriptLab from './components/ScriptLab';
import SystemAssets from './components/SystemAssets';
import ProductToClip from './components/ProductToClip';
import ContentTrackerHub from './components/ContentTrackerHub';
import { getSystemStatus, getRawVideos, getExports, updateAngleStatus } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('flow');
  const [status, setStatus] = useState(null);
  const [videos, setVideos] = useState([]);
  const [exportsList, setExportsList] = useState([]);

  // Active Product Context (from Menu 1 & Menu 2)
  const [activeProductContext, setActiveProductContext] = useState(null);
  const [selectedAngleIndex, setSelectedAngleIndex] = useState(0);
  const [activeAngleContext, setActiveAngleContext] = useState(null);

  // Studio Form State
  const [selectedVideo, setSelectedVideo] = useState('');
  const [productName, setProductName] = useState('Esseger สายชาร์จแม่เหล็ก');
  const [hookTitle, setHookTitle] = useState('🔥 อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก');
  const [painPoint, setPainPoint] = useState('สายชาร์จพังง่าย เสียบยากในที่มืด');
  const [priceDeal, setPriceDeal] = useState('ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง');
  const [keyFeatures, setKeyFeatures] = useState('แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก');
  const [customScript, setCustomScript] = useState('');
  const [useCustomScript, setUseCustomScript] = useState(false);

  // Audio & Typography State
  const [voiceMode, setVoiceMode] = useState('gemini_tts');
  const [voiceGender, setVoiceGender] = useState('male');
  const [voiceSpeed, setVoiceSpeed] = useState('+15%');
  const [voicePreset, setVoicePreset] = useState('gemini_puck_male_hype');
  const [adTone, setAdTone] = useState('commercial_premium');
  const [humanVoiceAudio, setHumanVoiceAudio] = useState(null);
  const [fontName, setFontName] = useState('IBMPlex');
  const [bilingualSubtitles, setBilingualSubtitles] = useState(true);
  const [stickerBadge, setStickerBadge] = useState('badge_flash_sale_3d.png');
  // null = backend default (SFXManager's channel-wide signature BGM / no LUT grade)
  const [bgmName, setBgmName] = useState(null);
  const [lutName, setLutName] = useState(null);

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

    if (data.selectedVideo) {
      setSelectedVideo(data.selectedVideo);
    } else {
      // Intelligently select video matching product name if available, else don't force unrelated video
      const pNameLow = (data.productName || '').toLowerCase();
      const match = videos.find(v => {
        const vName = v.name.toLowerCase();
        return (pNameLow.includes('logitech') && vName.includes('logitech')) ||
               (pNameLow.includes('esseger') && vName.includes('esseger')) ||
               (pNameLow.includes('cable') && vName.includes('cable')) ||
               (pNameLow.includes('keyboard') && vName.includes('keyboard'));
      });
      if (match) {
        setSelectedVideo(match.path);
      } else {
        // If no matching video, keep empty or select none so user is prompted to upload or use product images
        setSelectedVideo('');
      }
    }
    setActiveTab('studio');
  };

  const handleRenderSuccess = async (result) => {
    if (activeAngleContext && activeAngleContext.productId && activeAngleContext.angleId) {
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
    <div className="flex h-screen overflow-hidden font-prompt bg-[#07090E]">
      {/* ── Sidebar (desktop: left, mobile: bottom) ── */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status={status}
      />

      {/* ── Main Area ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* ── Topbar ── */}
        <Topbar activeTab={activeTab} setActiveTab={setActiveTab} status={status} />

        {/* ── Content ── */}
        <main className="flex-1 overflow-y-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-5 pb-20 md:pb-6">
          <div className="max-w-[1600px] mx-auto animate-fadeIn space-y-4">

            {/* SECTION: สินค้า → คลิป (Menu 1) */}
            {activeTab === 'flow' && (
              <ProductToClip
                status={status}
                videos={videos}
                onRefresh={refreshData}
                onApplyToStudio={handleApplyScriptFromLab}
              />
            )}

            {/* SECTION: คลังสินค้า & Tracker (Menu 2) */}
            {activeTab === 'tracker' && (
              <ContentTrackerHub
                onApplyToStudio={handleApplyScriptFromLab}
                onRefresh={refreshData}
              />
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

            {/* SECTION: ตัดต่อมือ (Manual Editor) */}
            {activeTab === 'editor' && (
              <ManualEditor videos={videos} />
            )}

            {/* SECTION: Export Gallery (Menu 4) */}
            {activeTab === 'gallery' && (
              <ExportGallery
                exportsList={exportsList}
                onRefresh={refreshData}
              />
            )}

            {/* SECTION: System & Assets (Menu 5) */}
            {activeTab === 'assets' && (
              <SystemAssets status={status} />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
