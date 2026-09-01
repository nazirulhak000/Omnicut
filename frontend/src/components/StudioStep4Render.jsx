import React, { useState, useEffect } from 'react';
import { Rocket, Download, Folder, CheckCircle2, AlertCircle, Loader2, Sparkles } from 'lucide-react';
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
  onRenderSuccess
}) {
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
        sticker_badge: stickerBadge || null,
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

  return (
    <div className="glass-card p-5 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 text-xs font-black tracking-wider text-white uppercase rounded-full bg-gradient-to-r from-[#FE2C55] to-[#FF0050] shadow-md shadow-[#FE2C55]/30">
            STEP 4
          </span>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Rocket className="w-5 h-5 text-[#25F4EE]" />
            เรนเดอร์จบในตัว (All-in-One Auto Render)
          </h2>
        </div>
        <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
          ✓ Full Standalone Pipeline
        </span>
      </div>

      {/* Standalone Pipeline Feature Banner */}
      <div className="p-3.5 rounded-2xl bg-black/40 border border-white/5 mb-5 flex items-center justify-between text-xs text-slate-300">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FE2C55]/20 to-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE] flex-shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-white">ตัดต่อเสร็จสมบูรณ์ 100% พร้อมโพสต์ (9:16 Vertical MP4)</div>
            <div className="text-[11px] text-slate-400">ตัดจังหวะไวรัล + บากซับไตเติล + ใส่เสียงพากย์ AI + SFX + BGM Ducking จบในรอบเดียว</div>
          </div>
        </div>
      </div>

      {/* BIG HERO CTA BUTTON */}
      <button
        onClick={handleStartRender}
        disabled={rendering}
        className={`w-full py-4 px-6 rounded-2xl font-black text-base md:text-lg flex items-center justify-center gap-3 transition-all duration-300 shadow-2xl ${
          rendering
            ? 'bg-slate-800 text-slate-400 cursor-not-allowed border border-white/10'
            : 'bg-gradient-to-r from-[#FE2C55] via-[#FF0050] to-[#E02449] hover:from-[#FF0050] hover:to-[#FE2C55] text-white shadow-[#FE2C55]/40 hover:shadow-[#FE2C55]/60 hover:scale-[1.01] active:scale-[0.99] border-none cursor-pointer'
        }`}
      >
        {rendering ? (
          <>
            <Loader2 className="w-6 h-6 animate-spin text-[#25F4EE]" />
            <span>กำลังตัดต่อและใส่เอฟเฟกต์... ({Math.round((jobStatus?.progress || 0) * 100)}%)</span>
          </>
        ) : (
          <>
            <Sparkles className="w-6 h-6" />
            <span>เริ่มต้นตัดต่อวิดีโออัตโนมัติ (Start Auto-Cut Studio)</span>
          </>
        )}
      </button>

      {/* Live Processing Progress Display */}
      {rendering && (
        <div className="mt-5 p-4 rounded-2xl bg-black/60 border border-white/10 space-y-3 animate-fadeIn">
          <div className="flex items-center justify-between text-xs font-semibold">
            <span className="text-slate-300 flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-[#25F4EE] animate-spin" />
              {jobStatus?.message || 'กำลังประมวลผล...'}
            </span>
            <span className="text-[#25F4EE] font-mono font-bold text-sm">
              {Math.round((jobStatus?.progress || 0) * 100)}%
            </span>
          </div>

          <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden p-0.5 border border-white/5">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#FE2C55] via-[#FF0050] to-[#25F4EE] transition-all duration-300"
              style={{ width: `${Math.max(5, (jobStatus?.progress || 0) * 100)}%` }}
            />
          </div>

          {/* Activity Log Feed */}
          {jobStatus?.logs && jobStatus.logs.length > 0 && (
            <div className="max-h-24 overflow-y-auto space-y-1 pt-2 border-t border-white/5 text-[11px] font-mono text-slate-400">
              {jobStatus.logs.slice(-3).map((log, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="text-slate-500">[{log.time}]</span>
                  <span className="text-slate-300">{log.msg}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Error Notice */}
      {renderError && (
        <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-2.5 animate-fadeIn">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{renderError}</span>
        </div>
      )}

      {/* Render Result Victory Box */}
      {renderResult && (
        <div className="mt-6 p-5 rounded-2xl bg-gradient-to-b from-[#212838] to-[#161B26] border border-[#25F4EE]/40 shadow-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-sm font-bold text-[#25F4EE]">
              <CheckCircle2 className="w-5 h-5" />
              🎉 ผลงานวิดีโอตัดต่อเสร็จสมบูรณ์ 100%!
            </div>
            <button
              onClick={handleOpenExportsFolder}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer border border-white/10"
            >
              <Folder className="w-3.5 h-3.5 text-[#25F4EE]" />
              เปิดโฟลเดอร์ Exports
            </button>
          </div>

          {renderResult.mp4_url && (
            <div className="space-y-3">
              <div className="rounded-xl overflow-hidden bg-black border border-white/10 max-h-[380px] flex items-center justify-center">
                <video
                  controls
                  autoPlay
                  playsInline
                  src={renderResult.mp4_url}
                  className="w-full max-h-[380px] object-contain"
                />
              </div>

              <div className="flex flex-wrap gap-2.5">
                <a
                  href={renderResult.mp4_url}
                  download
                  className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:opacity-90 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-[#FE2C55]/30 transition-all cursor-pointer"
                >
                  <Download className="w-4 h-4" />
                  ดาวน์โหลดไฟล์ .MP4 พร้อมโพสต์
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
