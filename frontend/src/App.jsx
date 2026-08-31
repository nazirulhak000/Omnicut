import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PresetsBar from './components/PresetsBar';
import StudioStep1Media from './components/StudioStep1Media';
import StudioStep2Script from './components/StudioStep2Script';
import StudioStep3Audio from './components/StudioStep3Audio';
import StudioStep4Render from './components/StudioStep4Render';
import ExportGallery from './components/ExportGallery';
import ScriptLab from './components/ScriptLab';
import SystemAssets from './components/SystemAssets';
import CapCutTimelineStudio from './components/CapCutTimelineStudio';
import { getSystemStatus, getRawVideos, getExports } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('capcut_studio'); // default to CapCut Timeline Studio to let user see it immediately!
  const [status, setStatus] = useState(null);
  const [videos, setVideos] = useState([]);
  const [exportsList, setExportsList] = useState([]);

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
  const [voiceMode, setVoiceMode] = useState('edge_tts');
  const [voiceGender, setVoiceGender] = useState('male');
  const [voiceSpeed, setVoiceSpeed] = useState('+20%');
  const [f5Preset, setF5Preset] = useState('tiktok_male_pro');
  const [humanVoiceAudio, setHumanVoiceAudio] = useState(null);
  const [fontName, setFontName] = useState('IBMPlex');
  const [bilingualSubtitles, setBilingualSubtitles] = useState(true);
  const [stickerBadge, setStickerBadge] = useState('badge_flash_sale_3d.png');

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

  const handleRenderSuccess = (result) => {
    refreshData();
  };

  return (
    <div className="w-full max-w-[1920px] 2xl:max-w-none mx-auto px-3 sm:px-6 lg:px-8 xl:px-10 py-4 sm:py-6 font-prompt min-h-screen flex flex-col justify-between">
      <div>
        {/* Top Header & Navigation */}
        <Header
          status={status}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />

        {/* TAB 1: STUDIO CREATOR (1-CLICK) */}
        {activeTab === 'studio' && (
          <main className="space-y-6">
            {/* Quick Presets */}
            <PresetsBar onSelectPreset={handleSelectPreset} />

            {/* 2-Column Responsive Layout (Stacks on mobile/tablet, side-by-side on desktop) */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
              {/* Left Column: STEP 1 (Media) & STEP 2 (Script) */}
              <div className="space-y-6">
                <StudioStep1Media
                  videos={videos}
                  selectedVideo={selectedVideo}
                  setSelectedVideo={setSelectedVideo}
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

              {/* Right Column: STEP 3 (Audio) & STEP 4 (Render) */}
              <div className="space-y-6">
                <StudioStep3Audio
                  voiceMode={voiceMode}
                  setVoiceMode={setVoiceMode}
                  voiceGender={voiceGender}
                  setVoiceGender={setVoiceGender}
                  voiceSpeed={voiceSpeed}
                  setVoiceSpeed={setVoiceSpeed}
                  f5Preset={f5Preset}
                  setF5Preset={setF5Preset}
                  humanVoiceAudio={humanVoiceAudio}
                  setHumanVoiceAudio={setHumanVoiceAudio}
                  productName={productName}
                  fontName={fontName}
                  setFontName={setFontName}
                  bilingualSubtitles={bilingualSubtitles}
                  setBilingualSubtitles={setBilingualSubtitles}
                  stickerBadge={stickerBadge}
                  setStickerBadge={setStickerBadge}
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
                  f5Preset={f5Preset}
                  humanVoiceAudio={humanVoiceAudio}
                  fontName={fontName}
                  bilingualSubtitles={bilingualSubtitles}
                  stickerBadge={stickerBadge}
                  onRenderSuccess={handleRenderSuccess}
                />
              </div>
            </div>
          </main>
        )}

        {/* TAB 2: CAPCUT TIMELINE PRO STUDIO */}
        {activeTab === 'capcut_studio' && (
          <CapCutTimelineStudio
            onSwitchToSimpleStudio={() => setActiveTab('studio')}
          />
        )}

        {/* TAB 2: EXPORT GALLERY */}
        {activeTab === 'gallery' && (
          <ExportGallery
            exportsList={exportsList}
            onRefresh={refreshData}
          />
        )}

        {/* TAB 3: AI SCRIPT LAB */}
        {activeTab === 'script_lab' && (
          <ScriptLab />
        )}

        {/* TAB 4: SYSTEM & ASSETS */}
        {activeTab === 'assets' && (
          <SystemAssets status={status} />
        )}
      </div>

      {/* Footer */}
      <footer className="mt-12 text-center text-xs text-slate-500 pb-6 border-t border-white/5 pt-6 flex flex-col sm:flex-row items-center justify-between gap-2">
        <span>⚡ TikTok Auto-Cutter Pro Studio • CapCut Engine Sync</span>
        <span className="font-mono text-[11px] text-slate-600">
          Full-Screen & Wireless Mobile Sync Active • LAN IP: {status?.local_ip || '127.0.0.1'}
        </span>
      </footer>
    </div>
  );
}
