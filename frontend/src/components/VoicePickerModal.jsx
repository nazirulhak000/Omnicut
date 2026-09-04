import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Loader2, X, CheckCircle2, Play, Square, Mic2, Wand2, Info } from 'lucide-react';

/**
 * VoicePickerModal
 * ─────────────────
 * Full-screen overlay for auditioning all voice × tone combinations.
 * Uses pre-cached /voice_cache/{preset}__{tone}.wav files when available;
 * falls back to the live /api/voice/preview endpoint otherwise.
 *
 * Props:
 *   isOpen        boolean
 *   onClose       () => void
 *   selectedVoice string   current voice_preset id
 *   selectedTone  string   current ad_tone id
 *   onSelect      ({ voiceId, toneId }) => void
 */

const VOICE_GROUPS = {
  male:   { label: 'เสียงชาย', accent: '#60A5FA' },
  female: { label: 'เสียงหญิง', accent: '#F472B6' },
};

const TONE_ICONS = {
  commercial_premium:   '📢',
  commercial_hype:      '🔥',
  commercial_aesthetic: '✨',
  commercial_expert:    '🎙️',
};

export default function VoicePickerModal({ isOpen, onClose, selectedVoice, selectedTone, onSelect }) {
  const [manifest, setManifest]     = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [playingKey, setPlayingKey] = useState(null);
  const [localVoice, setLocalVoice] = useState(selectedVoice);
  const [localTone, setLocalTone]   = useState(selectedTone);
  const audioRef = useRef(null);

  // ── fetch manifest when opening ─────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    setLocalVoice(selectedVoice);
    setLocalTone(selectedTone);
    setLoading(true);
    setError(null);
    fetch('/api/voice/presets')
      .then((r) => r.json())
      .then((data) => { setManifest(data); setLoading(false); })
      .catch((e) => { setError('โหลด presets ไม่ได้: ' + e.message); setLoading(false); });
  }, [isOpen, selectedVoice, selectedTone]);

  // ── stop audio on close ─────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen && audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlayingKey(null);
    }
  }, [isOpen]);

  // ── play helper ─────────────────────────────────────────────────────────
  const playPreview = useCallback(async (combo) => {
    const key = combo.voice_id + '__' + combo.tone_id;
    if (playingKey === key) {
      audioRef.current?.pause();
      audioRef.current = null;
      setPlayingKey(null);
      return;
    }
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }

    let url = combo.ready ? combo.url : null;
    if (!url) {
      setPlayingKey(key + '_loading');
      try {
        const res = await fetch('/api/voice/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: 'สวัสดีครับ นี่คือตัวอย่างเสียงพากย์รีวิว ลองฟังดูนะครับ',
            voice_gender: combo.voice_id,
            ad_tone: combo.tone_id,
            speed: 1.15,
          }),
        });
        const data = await res.json();
        url = data.audio_url || data.url;
      } catch {
        setPlayingKey(null);
        return;
      }
    }
    if (!url) { setPlayingKey(null); return; }

    const audio = new Audio(url);
    audioRef.current = audio;
    setPlayingKey(key);
    audio.onended = () => { setPlayingKey(null); audioRef.current = null; };
    audio.onerror = () => { setPlayingKey(null); audioRef.current = null; };
    audio.play().catch(() => setPlayingKey(null));
  }, [playingKey]);

  const handleSelect = () => {
    onSelect?.({ voiceId: localVoice, toneId: localTone });
    onClose?.();
  };

  // ── group combos by voice ───────────────────────────────────────────────
  const grouped = React.useMemo(() => {
    if (!manifest?.combos) return { male: [], female: [] };
    const result = { male: [], female: [] };
    const seen = new Set();
    const voices = [];
    for (const c of manifest.combos) {
      if (!seen.has(c.voice_id)) {
        seen.add(c.voice_id);
        voices.push({ id: c.voice_id, label: c.voice_label, gender: c.voice_gender });
      }
    }
    for (const v of voices) {
      const tones = manifest.combos.filter((c) => c.voice_id === v.id);
      (result[v.gender] || result.male).push({ ...v, tones });
    }
    return result;
  }, [manifest]);

  if (!isOpen) return null;

  const selectedComboLabel = manifest?.combos?.find((c) => c.voice_id === localVoice)?.voice_label;
  const selectedToneLabel  = manifest?.combos?.find((c) => c.tone_id  === localTone)?.tone_label;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(14px)' }}
      onClick={(e) => e.target === e.currentTarget && onClose?.()}
    >
      <div
        className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-3xl border border-white/10 shadow-2xl overflow-hidden"
        style={{ background: 'linear-gradient(160deg, #0A0E1A 0%, #0D1224 100%)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.07] flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg,#E89274,#D97757)' }}>
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide">เลือกเสียงพากย์</h2>
              <p className="text-xs text-slate-400 mt-0.5">กดปุ่มเล่นเพื่อฟังตัวอย่างแต่ละสไตล์</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {manifest && (
              <span className="text-xs px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.04] text-slate-400">
                {manifest.ready}/{manifest.total} พร้อมฟัง
              </span>
            )}
            <button onClick={onClose} className="w-8 h-8 rounded-xl flex items-center justify-center border border-white/[0.08] bg-white/[0.04] hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-[#E89274]" />
              <span className="text-slate-400 text-sm">กำลังโหลดรายชื่อเสียง...</span>
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-300 text-sm">
              <Info className="w-4 h-4 flex-shrink-0" />{error}
            </div>
          )}

          {manifest && manifest.ready < manifest.total && (
            <div className="flex items-start gap-3 p-4 rounded-2xl border border-amber-500/20 bg-amber-500/[0.07]">
              <Wand2 className="w-4 h-4 flex-shrink-0 text-amber-400 mt-0.5" />
              <div className="text-xs text-amber-200 leading-relaxed">
                <strong>ยังไม่ได้เจนเสียงตัวอย่างล่วงหน้าทั้งหมด ({manifest.ready}/{manifest.total})</strong>
                <br />
                กดเล่นบนตัวที่ยังไม่พร้อม ระบบจะสร้างผ่าน API แบบ Live แทน (ช้ากว่า)<br />
                หรือรัน: <code className="bg-black/40 px-1 py-0.5 rounded text-amber-300">python scripts/generate_voice_cache.py</code> เพื่อเจนทั้งหมดล่วงหน้า
              </div>
            </div>
          )}

          {['male', 'female'].map((gender) => (
            <div key={gender}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-bold uppercase tracking-widest" style={{ color: VOICE_GROUPS[gender].accent }}>
                  {VOICE_GROUPS[gender].label}
                </span>
                <div className="flex-1 h-px bg-white/[0.05]" />
              </div>
              <div className="space-y-3">
                {(grouped[gender] || []).map((voice) => {
                  const isVoiceSel = localVoice === voice.id;
                  return (
                    <div key={voice.id} className={`rounded-2xl border transition-all ${isVoiceSel ? 'border-[#E89274]/50 bg-[#E89274]/[0.05]' : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.03]'}`}>
                      <button type="button" onClick={() => setLocalVoice(voice.id)} className="w-full flex items-center gap-3 px-4 py-3 cursor-pointer text-left">
                        <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-sm font-bold text-white"
                          style={{ background: isVoiceSel ? VOICE_GROUPS[gender].accent + '25' : 'rgba(255,255,255,0.05)', border: `1px solid ${isVoiceSel ? VOICE_GROUPS[gender].accent + '50' : 'rgba(255,255,255,0.08)'}` }}>
                          {voice.label[0]}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-white truncate">{voice.label}</div>
                        </div>
                        {isVoiceSel && <CheckCircle2 className="w-4 h-4 flex-shrink-0" style={{ color: VOICE_GROUPS[gender].accent }} />}
                      </button>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 px-4 pb-3">
                        {voice.tones.map((combo) => {
                          const key = combo.voice_id + '__' + combo.tone_id;
                          const isThisSel   = isVoiceSel && localTone === combo.tone_id;
                          const isPlaying   = playingKey === key;
                          const isLoadingT  = playingKey === key + '_loading';
                          return (
                            <div
                              key={combo.tone_id}
                              onClick={() => { setLocalVoice(voice.id); setLocalTone(combo.tone_id); }}
                              className={`relative rounded-xl border p-2.5 flex flex-col gap-1.5 transition-all cursor-pointer select-none ${isThisSel ? 'border-[#E89274]/60 bg-[#E89274]/10' : 'border-white/[0.05] bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/[0.12]'}`}
                            >
                              <div className={`absolute top-2 right-2 w-1.5 h-1.5 rounded-full ${combo.ready ? 'bg-emerald-400' : 'bg-slate-600'}`} title={combo.ready ? 'พร้อมฟังทันที' : 'จะสร้าง Live'} />
                              <span className="text-base leading-none">{TONE_ICONS[combo.tone_id] || '🎵'}</span>
                              <span className="text-[11px] font-semibold text-slate-200 leading-tight line-clamp-2">{combo.tone_label}</span>
                              <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); playPreview(combo); }}
                                className={`mt-auto flex items-center justify-center gap-1 h-7 w-full rounded-lg text-[11px] font-medium transition-all cursor-pointer ${isPlaying ? 'bg-[#E89274]/20 border border-[#E89274]/40 text-[#E89274]' : 'bg-white/[0.04] border border-white/[0.08] text-slate-300 hover:text-white hover:bg-white/[0.1]'}`}
                              >
                                {isLoadingT ? <Loader2 className="w-3 h-3 animate-spin" />
                                  : isPlaying ? <><Square className="w-2.5 h-2.5 fill-current" /><span>หยุด</span></>
                                  : <><Play className="w-2.5 h-2.5 fill-current" /><span>ฟัง</span></>}
                              </button>
                              {isThisSel && <CheckCircle2 className="absolute bottom-2 right-2 w-3 h-3 text-[#E89274]" />}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-6 py-4 border-t border-white/[0.07] flex-shrink-0 bg-black/30">
          <div className="text-xs text-slate-400">
            {localVoice && localTone ? (
              <>เลือก: <span className="text-white font-semibold">{selectedComboLabel || localVoice}</span> · <span className="text-[#E89274] font-semibold">{selectedToneLabel || localTone}</span></>
            ) : 'ยังไม่ได้เลือก'}
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={onClose} className="h-9 px-4 rounded-xl border border-white/[0.08] bg-white/[0.04] text-sm text-slate-300 hover:text-white hover:bg-white/[0.08] cursor-pointer transition-colors">
              ยกเลิก
            </button>
            <button
              type="button"
              onClick={handleSelect}
              disabled={!localVoice || !localTone}
              className="h-9 px-5 rounded-xl text-sm font-bold text-white cursor-pointer transition-all disabled:opacity-40"
              style={{ background: 'linear-gradient(135deg,#E89274,#D97757)' }}
            >
              ยืนยันเสียงนี้
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}