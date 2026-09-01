import React, { useState, useEffect } from 'react';
import { Rocket, Download, Folder, CheckCircle2, AlertCircle, Loader2, Sparkles, Eye, Play, Film, ArrowRight, Check } from 'lucide-react';
import { startRender, getRenderStatus, openFolder } from '../api';

export default function StudioStep4Render({
  productName,
  selectedVideo,
  keyFeatures,
  painPoint,
  priceDeal,
  hookTitle,
  customScript,
  useCustomScript,
  voiceMode,
  voiceGender,
  voiceSpeed,
  voicePreset,
  adTone,
  humanVoiceAudio,
  fontName,
  bilingualSubtitles,
  stickerBadge,
  bgmName,
  lutName,
  onRenderSuccess,
  onGoToGallery
}) {
  const [useAiVision, setUseAiVision] = useState(true);
  const [rendering, setRendering] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [renderResult, setRenderResult] = useState(null);
  const [renderError, setRenderError] = useState(null);

  // Poll render status if jobId exists
  useEffect(() => {
    let interval = null;
    if (jobId && rendering) {
      interval = setInterval(async () => {
        try {
          const status = await getRenderStatus(jobId);
          setJobStatus(status);

          if (status.status === 'completed') {
            setRendering(false);
            setRenderResult(status.result);
            if (onRenderSuccess) onRenderSuccess(status.result);
            clearInterval(interval);
          } else if (status.status === 'failed') {
            setRendering(false);
            setRenderError(status.error || 'การตัดต่อล้มเหลว');
            clearInterval(interval);
          }
        } catch (err) {
          console.error(err);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [jobId, rendering]);

  const handleStartRender = async () => {
    if (!selectedVideo) {
      alert('กรุณาเลือกไฟล์วิดีโอใน STEP 1 ก่อนครับ!');
      return;
    }

    setRendering(true);
    setRenderError(null);
    setRenderResult(null);
    setJobStatus({ progress: 0.05, message: 'กำลังเตรียมข้อมูลและจัดโครงสร้างสคริปต์...' });

    try {
      const payload = {
        product_name: productName,
        raw_video_path: selectedVideo,
        key_features: keyFeatures,
        pain_point: painPoint,
        price_deal: priceDeal,
        hook_title: hookTitle,
        custom_script: useCustomScript ? customScript : null,
        voice_mode: voiceMode,
        voice_gender: voiceGender,
        voice_preset: voicePreset,
        ad_tone: adTone || 'commercial_premium',
        human_voice_audio: humanVoiceAudio,
        font_name: fontName || 'IBMPlex',
        bilingual_subtitles: bilingualSubtitles !== false,
        use_ai_vision: useAiVision,
        sticker_badge: stickerBadge || null,
        bgm_name: bgmName || null,
        lut_name: lutName || null,
        export_mp4: true,
        export_capcut: false
      };

      const res = await startRender(payload);
      setJobId(res.job_id);
    } catch (err) {
      setRendering(false);
      setRenderError(err.message || 'ไม่สามารถเริ่มกระบวนการตัดต่อได้');
    }
  };

  const handleOpenExportsFolder = () => {
    openFolder('exports');
  };

  const progressPercent = Math.round((jobStatus?.progress || 0) * 100);

  return (
    <section className="space-y-2.5">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-lg bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-[11px] font-black text-slate-950 shadow-md shadow-[#FE2C55]/20">
            4
          </span>
          <h3 className="text-sm font-bold text-white flex items-center gap-2 font-kanit">
            <span>เรนเดอร์ & ออโต้คัต (Auto-Render)</span>
          </h3>
        </div>

        <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20 font-mono">
          ⚡ 1-Click Pipeline
        </span>
      </div>

      <div className="glass-card p-4 space-y-4">
        {/* Gemini Vision Matcher Toggle Box */}
        <div 
          onClick={() => setUseAiVision(!useAiVision)}
          className={`p-3.5 rounded-xl border cursor-pointer transition-all duration-200 flex items-center justify-between ${
            useAiVision 
              ? 'bg-[#25F4EE]/10 border-[#25F4EE]/40 shadow-md shadow-[#25F4EE]/5' 
              : 'bg-white/[0.02] border-white/[0.06] opacity-70 hover:opacity-100'
          }`}
        >
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${
              useAiVision ? 'bg-[#25F4EE] text-slate-950 shadow-md shadow-[#25F4EE]/30' : 'bg-white/[0.05] text-slate-400'
            }`}>
              <Eye className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white flex items-center gap-2 text-xs">
                <span>Gemini 2.5 Vision Matcher</span>
                <span className="px-1.5 py-0.2 text-[9px] font-bold rounded-full bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/30">
                  AI Smart Cut
                </span>
              </div>
              <div className="text-[11px] text-slate-300 mt-0.5">
                AI สแกนช็อตสินค้าในคลิปจริง และตัดเลือกฉากให้ตรงกับเนื้อหาสคริปต์อัตโนมัติ
              </div>
            </div>
          </div>
          <div className="pl-2">
            <div className={`w-8 h-[18px] rounded-full transition-colors relative p-0.5 ${useAiVision ? 'bg-[#25F4EE]' : 'bg-white/[0.12]'}`}>
              <div className={`w-3.5 h-3.5 rounded-full bg-slate-950 transition-transform ${useAiVision ? 'translate-x-3.5' : 'translate-x-0'}`} />
            </div>
          </div>
        </div>

        {/* Big Action Render Button */}
        <button
          onClick={handleStartRender}
          disabled={rendering}
          className={`w-full py-4 px-5 rounded-2xl font-extrabold text-sm sm:text-base flex items-center justify-center gap-3 transition-all duration-200 shadow-2xl cursor-pointer ${
            rendering
              ? 'bg-slate-800 text-slate-400 cursor-not-allowed border border-white/5'
              : 'bg-gradient-to-r from-[#FE2C55] via-[#FF0050] to-[#25F4EE] text-white hover:opacity-95 active:scale-[0.99] animate-pulse-glow'
          }`}
        >
          {rendering ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin text-[#25F4EE]" />
              <span>กำลังตัดต่อวิดีโออัตโนมัติ... ({progressPercent}%)</span>
            </>
          ) : (
            <>
              <Rocket className="w-5 h-5 text-white" />
              <span>🎬 เริ่มตัดต่อวิดีโอ 1-Click (Start Auto-Cut)</span>
            </>
          )}
        </button>

        {/* Live Rendering Progress Box */}
        {rendering && (
          <div className="p-4 rounded-xl bg-black/60 border border-[#25F4EE]/30 space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-white font-bold">
                <Loader2 className="w-4 h-4 text-[#25F4EE] animate-spin" />
                <span>{jobStatus?.message || 'กำลังประมวลผล...'}</span>
              </div>
              <span className="font-mono text-[#25F4EE] font-extrabold">{progressPercent}%</span>
            </div>

            <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300"
                style={{ width: `${Math.max(5, progressPercent)}%` }}
              />
            </div>

            {/* 4-Stage Progress Tracker Chips */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 pt-1 text-[10px] font-mono">
              <div className={`p-1.5 rounded-lg border text-center ${progressPercent >= 15 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-white/[0.02] border-white/[0.04] text-slate-500'}`}>
                1. สคริปต์
              </div>
              <div className={`p-1.5 rounded-lg border text-center ${progressPercent >= 40 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-white/[0.02] border-white/[0.04] text-slate-500'}`}>
                2. เสียง AI
              </div>
              <div className={`p-1.5 rounded-lg border text-center ${progressPercent >= 70 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-white/[0.02] border-white/[0.04] text-slate-500'}`}>
                3. Vision Match
              </div>
              <div className={`p-1.5 rounded-lg border text-center ${progressPercent >= 95 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-white/[0.02] border-white/[0.04] text-slate-500'}`}>
                4. เรนเดอร์ซับ
              </div>
            </div>
          </div>
        )}

        {/* Render Error */}
        {renderError && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs flex items-center gap-2 animate-fadeIn">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{renderError}</span>
          </div>
        )}

        {/* Finished Video Player & Actions */}
        {renderResult && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-3.5 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-300 font-bold text-xs">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>ตัดต่อสำเร็จเรียบร้อยแล้ว! (Video Ready)</span>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/20 px-2 py-0.5 rounded-full">
                1080x1920 9:16
              </span>
            </div>

            {/* Video Player Preview */}
            {renderResult.video_url && (
              <div className="aspect-[9/16] max-h-[300px] w-full max-w-[200px] mx-auto rounded-xl overflow-hidden bg-black border border-white/10 shadow-2xl">
                <video
                  src={`${renderResult.video_url}?t=${Date.now()}`}
                  controls
                  autoPlay
                  playsInline
                  className="w-full h-full object-cover"
                />
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              <button
                onClick={handleOpenExportsFolder}
                className="py-2.5 px-3 rounded-xl bg-[#1E293B] hover:bg-[#334155] text-white text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-md"
              >
                <Folder className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>เปิดโฟลเดอร์ไฟล์ Export</span>
              </button>

              <button
                onClick={onGoToGallery}
                className="py-2.5 px-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:opacity-90 text-slate-950 text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-md"
              >
                <Film className="w-3.5 h-3.5" />
                <span>ดูใน Export Gallery</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
