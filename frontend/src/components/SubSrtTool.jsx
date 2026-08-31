import React, { useState } from 'react';
import { FileText, Sparkles, Download, Loader2, CheckCircle2, Globe, Volume2, Video } from 'lucide-react';
import { transcribeMedia } from '../api';

export default function SubSrtTool({ videos, selectedVideo }) {
  const [targetVideo, setTargetVideo] = useState(selectedVideo || (videos[0]?.path || ''));
  const [subMode, setSubMode] = useState('bilingual'); // 'bilingual' | 'mono' | 'dual'
  const [subLang, setSubLang] = useState('th');
  const [wordsPerLine, setWordsPerLine] = useState(5);
  const [transcribing, setTranscribing] = useState(false);
  const [transcribeResult, setTranscribeResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleTranscribe = async () => {
    if (!targetVideo) {
      alert('กรุณาเลือกไฟล์วิดีโอหรือเสียงก่อนครับ');
      return;
    }

    setTranscribing(true);
    setErrorMsg(null);
    setTranscribeResult(null);

    try {
      const res = await transcribeMedia({
        media_path: targetVideo,
        mode: subMode,
        lang: subLang || null,
        words_per_line: wordsPerLine,
        fast: true
      });
      setTranscribeResult(res);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'การถอดเสียงล้มเหลว');
    } finally {
      setTranscribing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="p-5 glass-panel">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#25F4EE] to-blue-600 flex items-center justify-center shadow-lg shadow-[#25F4EE]/30">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              ⚡ AI Auto-SRT Generator (ถอดซับแม่นยำ 100% สไตล์ CapCut)
            </h2>
            <p className="text-xs text-slate-400">
              ขับเคลื่อนด้วย <code>sub-srt</code> (faster-whisper + PyThaiNLP) — ถอดเสียงตรงเป๊ะ ไม่เดาเวลา แบ่งท่อนคำสั้นพอดีจอ พร้อมคำแปลภาษาอังกฤษ
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Settings Column */}
        <div className="glass-card p-5 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
            <Video className="w-4 h-4 text-[#25F4EE]" />
            เลือกคลิปที่ต้องการทำซับไตเติล
          </h3>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              ไฟล์วิดีโอหรือเสียง:
            </label>
            <select
              value={targetVideo}
              onChange={(e) => setTargetVideo(e.target.value)}
              className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#25F4EE]"
            >
              {videos.map((v) => (
                <option key={v.path} value={v.path}>
                  {v.name} ({v.size_mb} MB)
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                รูปแบบซับไตเติล:
              </label>
              <select
                value={subMode}
                onChange={(e) => setSubMode(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#25F4EE]"
              >
                <option value="bilingual">✨ ซับ 2 ภาษา (ไทย + แปลอังกฤษ)</option>
                <option value="mono">🇹🇭 ซับภาษาไทยอย่างเดียว (Mono)</option>
                <option value="dual">📑 แยก 2 ไฟล์ (.srt ไทย + .srt อังกฤษ)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                ภาษาพูดในคลิป:
              </label>
              <select
                value={subLang}
                onChange={(e) => setSubLang(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#25F4EE]"
              >
                <option value="th">🇹🇭 ภาษาไทย (Thai)</option>
                <option value="en">🇬🇧 ภาษาอังกฤษ (English)</option>
                <option value="zh">🇨🇳 ภาษาจีน (Chinese)</option>
                <option value="">🌐 ตรวจจับภาษาอัตโนมัติ (Auto)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              จำนวนคำต่อ 1 กล่องซับ (Words per Line):
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="3"
                max="8"
                value={wordsPerLine}
                onChange={(e) => setWordsPerLine(parseInt(e.target.value))}
                className="flex-1 accent-[#25F4EE]"
              />
              <span className="text-xs font-bold text-[#25F4EE] w-12 text-right">
                {wordsPerLine} คำ
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              💡 แนะนำ 4-5 คำสำหรับ TikTok / Shorts เพื่อให้ตัวหนังสือใหญ่ อ่านง่าย
            </p>
          </div>

          <button
            onClick={handleTranscribe}
            disabled={transcribing}
            className={`w-full py-3.5 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg ${
              transcribing
                ? 'bg-slate-800 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-[#25F4EE] to-blue-600 hover:from-blue-600 hover:to-[#25F4EE] text-slate-950 font-black shadow-[#25F4EE]/30'
            }`}
          >
            {transcribing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                กำลังถอดเสียงด้วย faster-whisper... (~10-20 วิ)
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                เริ่มถอดเสียงสร้างไฟล์ .SRT และ .VTT
              </>
            )}
          </button>

          {errorMsg && (
            <p className="text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
              {errorMsg}
            </p>
          )}
        </div>

        {/* Results Column */}
        <div className="glass-card p-5 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
            <FileText className="w-4 h-4 text-[#FE2C55]" />
            ผลลัพธ์ไฟล์ซับไตเติล (.SRT / .VTT)
          </h3>

          {transcribeResult ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 bg-emerald-500/10 p-2.5 rounded-lg border border-emerald-500/20">
                <CheckCircle2 className="w-4 h-4" />
                ถอดเสียงและสร้างไฟล์ซับสำเร็จ!
              </div>

              {/* Subtitle Preview Box */}
              <div className="p-3 bg-black/60 rounded-xl border border-white/10 font-mono text-xs text-slate-300 max-h-[220px] overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {transcribeResult.content}
              </div>

              {/* Download Buttons */}
              <div className="flex flex-wrap gap-2.5">
                {transcribeResult.srt_url && (
                  <a
                    href={transcribeResult.srt_url}
                    download
                    className="flex-1 py-2.5 px-3 rounded-xl bg-[#232A3B] hover:bg-[#FE2C55] text-white text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-md"
                  >
                    <Download className="w-4 h-4" />
                    ดาวน์โหลด .SRT
                  </a>
                )}
                {transcribeResult.vtt_url && (
                  <a
                    href={transcribeResult.vtt_url}
                    download
                    className="flex-1 py-2.5 px-3 rounded-xl bg-[#232A3B] hover:bg-[#25F4EE] hover:text-black text-white text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-md"
                  >
                    <Download className="w-4 h-4" />
                    ดาวน์โหลด .VTT
                  </a>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500 text-xs">
              <FileText className="w-10 h-10 mx-auto mb-2 opacity-40" />
              เลือกคลิปและกด "เริ่มถอดเสียง" เพื่อดูตัวอย่างไฟล์ .SRT และดาวน์โหลดไปใช้ใน CapCut ได้เลยครับ
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
