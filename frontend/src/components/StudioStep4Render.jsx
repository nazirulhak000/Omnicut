import React, { useState } from 'react';
import { Rocket, Download, Folder, CheckCircle2, AlertCircle, Loader2, Sparkles, Eye, Play, Film, ArrowRight, Check } from 'lucide-react';
import { openFolder } from '../api';
import { useRenderJob } from '../hooks';
import { Button, Badge } from './ui';

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

  // Custom Hook managing background polling, anti-hang timeout, and error state
  const {
    rendering,
    jobStatus,
    progressPercent,
    renderResult,
    renderError,
    executeRender
  } = useRenderJob({
    onComplete: (result) => {
      onRenderSuccess?.(result);
    }
  });

  const handleStartRender = async () => {
    if (!selectedVideo) {
      alert('กรุณาเลือกไฟล์วิดีโอใน STEP 1 ก่อนครับ!');
      return;
    }

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

    try {
      await executeRender(payload);
    } catch (err) {
      console.error('Failed to trigger render:', err);
    }
  };

  const handleOpenExportsFolder = () => {
    openFolder('exports');
  };

  return (
    <section className="space-y-2.5">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="w-7 h-7 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-xs font-bold text-white shadow-md shadow-[#FE2C55]/20">
            4
          </span>
          <h3 className="text-sm font-bold text-white font-kanit">
            เรนเดอร์ & ออโต้คัต (Auto-Render)
          </h3>
        </div>

        <Badge variant="cyan" size="sm">
          1-Click Pipeline
        </Badge>
      </div>

      <div className="glass-card p-4 space-y-4">
        {/* Gemini Vision Matcher Toggle Box */}
        <div 
          onClick={() => setUseAiVision(!useAiVision)}
          className={`p-3.5 rounded-2xl border cursor-pointer transition-all duration-150 flex items-center justify-between ${
            useAiVision 
              ? 'bg-[#25F4EE]/10 border-[#25F4EE]/40 shadow-sm' 
              : 'bg-black/30 border-white/[0.08] opacity-70 hover:opacity-100 hover:border-white/[0.15]'
          }`}
        >
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${
              useAiVision ? 'bg-[#25F4EE] text-slate-950 shadow-md' : 'bg-black/40 text-slate-400 border border-white/[0.08]'
            }`}>
              <Eye className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white flex items-center gap-2 text-xs">
                <span>Gemini 2.5 Vision Matcher</span>
                <Badge variant="cyan" size="sm">
                  AI Smart Cut
                </Badge>
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                AI สแกนช็อตสินค้าในคลิปจริง และตัดเลือกฉากให้ตรงกับเนื้อหาสคริปต์อัตโนมัติ
              </div>
            </div>
          </div>
          <div className="pl-2">
            <div className={`w-9 h-5 rounded-full transition-colors relative p-0.5 ${useAiVision ? 'bg-[#25F4EE]' : 'bg-white/[0.15]'}`}>
              <div className={`w-4 h-4 rounded-full bg-slate-950 transition-transform shadow-sm ${useAiVision ? 'translate-x-4' : 'translate-x-0'}`} />
            </div>
          </div>
        </div>

        {/* Big Action Render Button */}
        <Button
          onClick={handleStartRender}
          loading={rendering}
          variant="primary"
          size="lg"
          icon={Rocket}
          className="w-full text-sm sm:text-base py-4"
        >
          {rendering
            ? `กำลังตัดต่อวิดีโออัตโนมัติ... (${progressPercent}%)`
            : 'เริ่มตัดต่อวิดีโอ 1-Click'}
        </Button>

        {/* Live Rendering Progress Box */}
        {rendering && (
          <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-white font-bold">
                <Loader2 className="w-4 h-4 text-[#25F4EE] animate-spin" />
                <span>{jobStatus?.message || 'กำลังประมวลผล...'}</span>
              </div>
              <span className="font-mono text-[#25F4EE] font-bold">{progressPercent}%</span>
            </div>

            <div className="w-full h-2 rounded-full bg-white/[0.1] overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300"
                style={{ width: `${Math.max(5, progressPercent)}%` }}
              />
            </div>

            {/* 4-Stage Progress Tracker Chips */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 pt-1 text-xs font-mono">
              <div className={`p-2 rounded-xl border text-center transition-all ${progressPercent >= 15 ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 font-bold' : 'bg-white/[0.02] border-white/[0.06] text-slate-500'}`}>
                1. สคริปต์
              </div>
              <div className={`p-2 rounded-xl border text-center transition-all ${progressPercent >= 40 ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 font-bold' : 'bg-white/[0.02] border-white/[0.06] text-slate-500'}`}>
                2. เสียง AI
              </div>
              <div className={`p-2 rounded-xl border text-center transition-all ${progressPercent >= 70 ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 font-bold' : 'bg-white/[0.02] border-white/[0.06] text-slate-500'}`}>
                3. Vision Match
              </div>
              <div className={`p-2 rounded-xl border text-center transition-all ${progressPercent >= 95 ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 font-bold' : 'bg-white/[0.02] border-white/[0.06] text-slate-500'}`}>
                4. เรนเดอร์ซับ
              </div>
            </div>
          </div>
        )}

        {/* Render Error */}
        {renderError && (
          <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2 animate-fadeIn">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
            <span>{renderError}</span>
          </div>
        )}

        {/* Finished Video Player & Actions */}
        {renderResult && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-3.5 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>ตัดต่อสำเร็จเรียบร้อยแล้ว (Render Ready)</span>
              </div>
              <Badge variant="emerald" size="sm">
                1080x1920 9:16 Full HD
              </Badge>
            </div>

            {/* Video Player Preview */}
            {renderResult.video_url && (
              <div className="aspect-[9/16] max-h-[320px] w-full max-w-[200px] mx-auto rounded-xl overflow-hidden bg-black border border-white/10 shadow-2xl">
                <video
                  src={`${renderResult.video_url}?t=${Date.now()}`}
                  controls
                  autoPlay
                  playsInline
                  className="w-full h-full object-cover"
                />
              </div>
            )}

            {/* Ready-to-Post TikTok Packager: Caption & Hashtags */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-2 text-left">
              <div className="flex items-center justify-between text-xs font-bold text-slate-200">
                <span>แคปชัน & แฮชแท็กสำหรับโพสต์ TikTok:</span>
                <button
                  onClick={() => {
                    const cap = `ใครเจอปัญหานี้อยู่ต้องลอง! ${productName || 'ของดีบอกต่อ'} พิกัดในตะกร้าซ้ายล่างได้เลยครับ\n\n#tiktokป้ายยา #ของดีบอกต่อ #รีวิวของใช้ #พิกัดในตะกร้า #fyp`;
                    navigator.clipboard.writeText(cap);
                    alert('คัดลอกแคปชันและแฮชแท็กแล้ว');
                  }}
                  className="px-2.5 py-1 rounded-lg bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 text-[#25F4EE] text-[11px] font-bold transition-colors cursor-pointer border border-[#25F4EE]/30"
                >
                  คัดลอก
                </button>
              </div>
              <div className="text-[11px] text-slate-300 leading-relaxed font-mono select-all bg-black/30 p-2 rounded-lg border border-white/[0.04]">
                ใครเจอปัญหานี้อยู่ต้องลอง! {productName || 'ของดีบอกต่อ'} พิกัดในตะกร้าซ้ายล่างได้เลยครับ<br/>
                <span className="text-[#25F4EE] font-semibold">#tiktokป้ายยา #ของดีบอกต่อ #รีวิวของใช้ #พิกัดในตะกร้า #fyp</span>
              </div>
            </div>

            {/* AI Vision Matches List */}
            {renderResult.ai_matched_shots && renderResult.ai_matched_shots.length > 0 && (
              <div className="p-3 rounded-xl bg-black/30 border border-[#25F4EE]/20 space-y-1.5 text-left">
                <div className="text-[11px] font-bold text-[#25F4EE] flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5" />
                  <span>ช็อตที่ AI Vision คัดเลือก ({renderResult.ai_matched_shots.length} ช็อต):</span>
                </div>
                <div className="max-h-24 overflow-y-auto space-y-1 pr-1 font-mono text-[10px]">
                  {renderResult.ai_matched_shots.map((shot, sIdx) => (
                    <div key={sIdx} className="bg-white/[0.02] p-1.5 rounded border border-white/[0.04] flex items-center justify-between text-slate-300">
                      <span>ช็อตที่ {sIdx + 1}: {shot.text || `ฉากที่ ${sIdx + 1}`}</span>
                      <span className="text-[#25F4EE]">{shot.start_time}s - {shot.end_time}s</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              <Button
                onClick={handleOpenExportsFolder}
                variant="secondary"
                size="md"
                icon={Folder}
              >
                เปิดโฟลเดอร์ไฟล์ Export
              </Button>

              <Button
                onClick={onGoToGallery}
                variant="neon"
                size="md"
                icon={Film}
                iconRight={ArrowRight}
                className="bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 hover:brightness-110"
              >
                ดูใน Export Gallery
              </Button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
