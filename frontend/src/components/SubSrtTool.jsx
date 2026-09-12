import React, { useState } from 'react';
import { FileText, Sparkles, Download, Loader2, CheckCircle2, Globe, Volume2, Video, Copy, Check } from 'lucide-react';
import { transcribeMedia } from '../api';

export default function SubSrtTool({ videos = [], selectedVideo }) {
  const [targetVideo, setTargetVideo] = useState(selectedVideo || (videos[0]?.path || ''));
  const [subMode, setSubMode] = useState('bilingual'); // 'bilingual' | 'mono' | 'dual'
  const [subLang, setSubLang] = useState('th');
  const [wordsPerLine, setWordsPerLine] = useState(5);
  const [transcribing, setTranscribing] = useState(false);
  const [transcribeResult, setTranscribeResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleTranscribe = async () => {
    if (!targetVideo) {
      setErrorMsg('กรุณาเลือกไฟล์วิดีโอหรือเสียงก่อนครับ');
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
      setErrorMsg(err.friendlyMessage || err.response?.data?.detail || err.message || 'การถอดเสียงล้มเหลว');
    } finally {
      setTranscribing(false);
    }
  };

  const copySrtContent = () => {
    if (!transcribeResult?.content) return;
    navigator.clipboard.writeText(transcribeResult.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const DENSITY_PRESETS = [
    { label: 'สั้นกระชับ (4 คำ)', count: 4, desc: 'เน้น TikTok/Reels ตัวใหญ่สะใจ' },
    { label: 'มาตรฐาน (5-6 คำ)', count: 5, desc: 'สมดุล ความเร็วอ่านพอดี' },
    { label: 'ประโยคยาว (7-8 คำ)', count: 7, desc: 'สำหรับบรรยายยาว/รีวิวเจาะลึก' },
  ];

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Header Bar */}
      <div className="p-5 sm:p-6 glass-panel">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#25F4EE] to-blue-600 flex items-center justify-center shadow-lg shadow-[#25F4EE]/30 flex-shrink-0">
            <FileText className="w-6 h-6 text-slate-950 font-bold" />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2">
              AI Auto-SRT Generator (ถอดซับแม่นยำ 100% สไตล์ CapCut)
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              ขับเคลื่อนด้วย <code>faster-whisper + PyThaiNLP</code> — ถอดเสียงตรงเป๊ะ ไม่เดาเวลา ตัดแบ่งท่อนคำสั้นพอดีจอ พร้อมคำแปลภาษาอังกฤษ
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Settings Column */}
        <div className="glass-card p-5 sm:p-6 space-y-4">
          <h3 className="text-xs font-bold text-white flex items-center gap-2 pb-2 border-b border-white/[0.08]">
            <Video className="w-4 h-4 text-[#25F4EE]" />
            เลือกคลิปและตั้งค่าการถอดซับ
          </h3>

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1.5">
              ไฟล์วิดีโอหรือเสียง:
            </label>
            <select
              value={targetVideo}
              onChange={(e) => setTargetVideo(e.target.value)}
              className="w-full py-2.5 px-3.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-xs sm:text-sm font-bold focus:outline-none focus:border-[#25F4EE]/50 shadow-inner cursor-pointer"
            >
              {videos.map((v) => (
                <option key={v.path} value={v.path}>
                  {v.name} ({v.size_mb} MB)
                </option>
              ))}
              {videos.length === 0 && <option value="">ยังไม่มีไฟล์วิดีโอในระบบ</option>}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1.5">
                รูปแบบซับไตเติล:
              </label>
              <select
                value={subMode}
                onChange={(e) => setSubMode(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-xs font-bold focus:outline-none focus:border-[#25F4EE]/50 shadow-inner cursor-pointer"
              >
                <option value="bilingual">ซับ 2 ภาษา (ไทย + อังกฤษ)</option>
                <option value="mono">ซับภาษาไทยอย่างเดียว</option>
                <option value="dual">แยกไฟล์ไทยและอังกฤษ</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1.5">
                ภาษาพูดในคลิป:
              </label>
              <select
                value={subLang}
                onChange={(e) => setSubLang(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-xs font-bold focus:outline-none focus:border-[#25F4EE]/50 shadow-inner cursor-pointer"
              >
                <option value="th">ภาษาไทย</option>
                <option value="en">ภาษาอังกฤษ</option>
                <option value="zh">ภาษาจีน</option>
                <option value="">ตรวจจับอัตโนมัติ</option>
              </select>
            </div>
          </div>

          {/* Density Preset Chips */}
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2">
              ความยาวประโยคต่อกล่องซับ:
            </label>
            <div className="grid grid-cols-3 gap-2">
              {DENSITY_PRESETS.map((p) => {
                const isSel = wordsPerLine === p.count;
                return (
                  <button
                    key={p.count}
                    type="button"
                    onClick={() => setWordsPerLine(p.count)}
                    className={`p-2.5 rounded-xl border text-center transition-all cursor-pointer ${
                      isSel
                        ? 'bg-[#25F4EE]/20 border-[#25F4EE]/60 text-white shadow-md ring-1 ring-[#25F4EE]/40'
                        : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white hover:border-white/[0.15]'
                    }`}
                  >
                    <div className="text-xs font-bold">{p.label}</div>
                    <div className="text-sm text-slate-400 mt-0.5 truncate">{p.desc}</div>
                  </button>
                );
              })}
            </div>
          </div>

          <button
            onClick={handleTranscribe}
            disabled={transcribing || !targetVideo}
            className={`w-full py-3.5 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg ${
              transcribing || !targetVideo
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/[0.06]'
                : 'bg-gradient-to-r from-[#25F4EE] to-blue-600 hover:brightness-110 text-slate-950 font-black shadow-[#25F4EE]/30 cursor-pointer active:scale-95'
            }`}
          >
            {transcribing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin text-slate-950" />
                <span>กำลังถอดเสียงด้วย faster-whisper... (~10-20 วิ)</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5 text-slate-950" />
                <span>เริ่มถอดเสียงสร้างไฟล์ .SRT และ .VTT</span>
              </>
            )}
          </button>

          {errorMsg && (
            <p className="text-xs text-rose-300 bg-rose-500/10 p-3 rounded-xl border border-rose-500/20">
              {errorMsg}
            </p>
          )}
        </div>

        {/* Results Column */}
        <div className="glass-card p-5 sm:p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
            <h3 className="text-xs font-bold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#FE2C55]" />
              ผลลัพธ์ไฟล์ซับไตเติล (.SRT / .VTT)
            </h3>
            {transcribeResult?.content && (
              <button
                onClick={copySrtContent}
                className="text-xs font-bold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer"
              >
                {copied ? <><Check className="w-3.5 h-3.5 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3.5 h-3.5" /> คัดลอกทั้งหมด</>}
              </button>
            )}
          </div>

          {transcribeResult ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>สร้างสำเร็จ: <strong className="text-emerald-400">{transcribeResult.cue_count} ท่อนซับ</strong></span>
                <span className="font-mono">{transcribeResult.srt_path?.split('\\').pop()?.split('/').pop()}</span>
              </div>

              {/* SRT Textbox */}
              <textarea
                readOnly
                value={transcribeResult.content}
                rows={12}
                className="w-full p-3.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-200 font-mono text-xs focus:outline-none resize-none leading-relaxed shadow-inner"
              />

              {/* Download Buttons */}
              <div className="flex items-center gap-2 pt-1">
                {transcribeResult.srt_url && (
                  <a
                    href={transcribeResult.srt_url}
                    download
                    className="flex-1 py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-white text-xs font-bold flex items-center justify-center gap-2 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>ดาวน์โหลด .SRT</span>
                  </a>
                )}
                {transcribeResult.vtt_url && (
                  <a
                    href={transcribeResult.vtt_url}
                    download
                    className="flex-1 py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-white text-xs font-bold flex items-center justify-center gap-2 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5 text-blue-400" />
                    <span>ดาวน์โหลด .VTT</span>
                  </a>
                )}
              </div>
            </div>
          ) : (
            <div className="py-20 text-center space-y-2">
              <FileText className="w-10 h-10 mx-auto text-slate-500" />
              <p className="text-xs text-slate-400 font-medium">กดปุ่ม "เริ่มถอดเสียง" เพื่อสร้างไฟล์ซับไตเติล</p>
              <p className="text-sm text-slate-500">ลากไฟล์เข้า CapCut ได้ทันที</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
