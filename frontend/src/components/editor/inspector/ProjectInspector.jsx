import React from 'react';
import { AlertTriangle, Volume2, VolumeX, Music } from 'lucide-react';

const TRACKS = [
  { id: 'voice', label: 'เสียงพากย์ (Voice)', color: '#25F4EE' },
  { id: 'bgm', label: 'ดนตรีประกอบ (BGM)', color: '#D97757' },
  { id: 'sfx', label: 'เสียงเอฟเฟกต์ (SFX)', color: '#E6C24A' },
  { id: 'clip', label: 'เสียงจากคลิปวิดีโอ (Clip)', color: '#A78BFA' },
];

export default function ProjectInspector({
  style = {},
  totalDuration = 0,
  audioDuration = 0,
  trackMix = { mute: {}, solo: {} },
  onTrackMix,
}) {
  const gap = (audioDuration || 0) - totalDuration;

  const toggleMute = (trackId) => {
    if (!onTrackMix) return;
    const isMuted = !!trackMix?.mute?.[trackId];
    onTrackMix({
      ...trackMix,
      mute: {
        ...(trackMix?.mute || {}),
        [trackId]: !isMuted,
      },
    });
  };

  const toggleSolo = (trackId) => {
    if (!onTrackMix) return;
    const isSolo = !!trackMix?.solo?.[trackId];
    onTrackMix({
      ...trackMix,
      solo: {
        ...(trackMix?.solo || {}),
        [trackId]: !isSolo,
      },
    });
  };

  return (
    <div className="space-y-3">
      {/* Project Specs Summary */}
      <div className="space-y-2 rounded-2xl bg-black/40 border border-white/[0.08] p-3 text-xs">
        <div className="flex justify-between text-slate-300">
          <span>ฟอนต์มาตรฐานของโปรเจกต์:</span>
          <span className="font-bold text-[#25F4EE]">{style.fontName || 'Kanit'}</span>
        </div>
        <div className="flex justify-between text-slate-300">
          <span>เพลงประกอบ BGM:</span>
          <span className="text-slate-200">{style.bgmName || 'เสียงหลักของช่อง'}</span>
        </div>
        <div className="flex justify-between text-slate-300 border-t border-white/[0.06] pt-2">
          <span>ความยาววิดีโอรวม:</span>
          <span className="font-mono font-bold text-white">{totalDuration.toFixed(2)}s</span>
        </div>
        <div className="flex justify-between text-slate-300">
          <span>ความยาวเสียงพากย์:</span>
          <span className="font-mono font-bold text-white">{audioDuration.toFixed(2)}s</span>
        </div>
      </div>

      {/* Audio Track Mix / Mute / Solo */}
      <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
            <Music className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span>มิกเซอร์เสียง 4 แทร็ก (Track Mix)</span>
          </span>
          <span className="text-[10px] text-slate-500">M/S มีผลกับ Preview และ Export</span>
        </div>

        <div className="space-y-1.5">
          {TRACKS.map((track) => {
            const isMuted = !!trackMix?.mute?.[track.id];
            const isSolo = !!trackMix?.solo?.[track.id];

            return (
              <div
                key={track.id}
                className="flex items-center justify-between p-1.5 rounded-xl bg-black/50 border border-white/[0.06] text-xs"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: track.color }}
                  />
                  <span className={`font-medium ${isMuted ? 'text-slate-500 line-through' : 'text-slate-200'}`}>
                    {track.label}
                  </span>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => toggleMute(track.id)}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border transition-all cursor-pointer ${
                      isMuted
                        ? 'bg-rose-500/20 border-rose-500/40 text-rose-400'
                        : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                    }`}
                    title={isMuted ? 'เปิดเสียงแทร็กนี้' : 'ปิดเสียงแทร็กนี้ (Mute)'}
                  >
                    M
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleSolo(track.id)}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border transition-all cursor-pointer ${
                      isSolo
                        ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                        : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                    }`}
                    title={isSolo ? 'ยกเลิกฟังเดี่ยว' : 'ฟังแทร็กนี้เดี่ยว (Solo)'}
                  >
                    S
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Gap Warning */}
      {gap > 0.5 && (
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
          <p>
            วิดีโอสั้นกว่าเสียงพากย์ {gap.toFixed(1)} วิ — ช่วงท้ายจะค้างภาพเฟรมสุดท้ายไว้จนเสียงจบ
            เพิ่มคลิปหรือลดความเร็วถ้าไม่อยากให้ภาพนิ่ง
          </p>
        </div>
      )}
    </div>
  );
}
