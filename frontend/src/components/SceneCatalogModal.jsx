import React from 'react';
import {
  Film, Sparkles, Clock, Eye, ZoomIn, Compass, Tag, RefreshCw, X, CheckCircle2, RotateCw
} from 'lucide-react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';

function formatTime(seconds = 0) {
  const s = Math.max(0, Number(seconds) || 0);
  const m = Math.floor(s / 60);
  const rem = Math.floor(s % 60);
  const ms = Math.floor((s % 1) * 10);
  return `${String(m).padStart(2, '0')}:${String(rem).padStart(2, '0')}.${ms}`;
}

const ACTION_MAP = {
  turntable_spin: { label: 'หมุนสินค้า 360', color: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
  unboxing: { label: 'แกะกล่อง/อุปกรณ์', color: 'bg-purple-500/20 text-purple-300 border-purple-500/40' },
  port_connection: { label: 'พอร์ต/เสียบชาร์จ', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' },
  closeup: { label: 'โคลสอัพดีเทล', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
  hands_on: { label: 'จับถือใช้งาน', color: 'bg-blue-500/20 text-blue-300 border-blue-500/40' },
  cta_showcase: { label: 'ป้ายยา/โชว์สินค้า', color: 'bg-rose-500/20 text-rose-300 border-rose-500/40' },
  overview: { label: 'ภาพรวมสินค้า', color: 'bg-teal-500/20 text-teal-300 border-teal-500/40' },
};

const ANGLE_MAP = {
  front: 'มุมหน้าตรง',
  '45deg': 'มุมเฉียง 45°',
  side: 'มุมด้านข้าง',
  macro_closeup: 'ซูมเจาะลึก Macro',
  back: 'มุมด้านหลัง',
};

export default function SceneCatalogModal({
  isOpen,
  onClose,
  catalog,
  videoName,
  videoPath,
  onRescan,
  isRescanning = false
}) {
  if (!isOpen) return null;

  const scenes = catalog?.scenes || [];
  const isSpin = Boolean(catalog?.is_spin_footage);
  const summary = catalog?.summary || '';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2 text-white">
          <Eye className="w-5 h-5 text-[#25F4EE]" />
          <span>สารบัญฉาก Vision AI</span>
        </div>
      }
      subtitle={videoName || videoPath || 'รายละเอียดการแบ่งฉากคลิปดิบ'}
      maxWidth="max-w-4xl"
    >
      <div className="space-y-4 p-1">
        {/* Top Summary Banner */}
        <div className="p-4 rounded-2xl bg-gradient-to-r from-cyan-500/10 via-slate-900/60 to-emerald-500/10 border border-white/[0.1] space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2.5">
            <div className="flex items-center gap-2 flex-wrap">
              {isSpin ? (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 shadow-sm">
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>หมุนสินค้า 360 (Turntable Showcase)</span>
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 flex items-center gap-1.5 shadow-sm">
                  <Film className="w-3.5 h-3.5" />
                  <span>หลากหลายแอ็กชัน (Multi-Action Footage)</span>
                </span>
              )}
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-white/10 text-slate-200 border border-white/20">
                ⚡ สแกนพบ {scenes.length} ฉาก
              </span>
            </div>

            {onRescan && (
              <Button
                variant="secondary"
                size="sm"
                icon={RefreshCw}
                onClick={onRescan}
                loading={isRescanning}
                disabled={isRescanning}
                className="text-xs"
              >
                สแกนฉากใหม่
              </Button>
            )}
          </div>

          {summary ? (
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed bg-black/40 p-3 rounded-xl border border-white/[0.06]">
              {summary}
            </p>
          ) : (
            <p className="text-xs text-slate-400 italic">
              AI วิเคราะห์ฉากในคลิปดิบพร้อมแล้ว ระบบจะนำสารบัญฉากนี้ไปแมพกับสคริปต์ทุกมุมมองโดยไม่ต้องสแกนซ้ำ
            </p>
          )}
        </div>

        {/* Scene Cards List */}
        <div className="space-y-2.5 max-h-[55vh] overflow-y-auto pr-1">
          {scenes.length === 0 ? (
            <div className="text-center py-12 text-slate-500 space-y-2">
              <Film className="w-10 h-10 mx-auto text-slate-600" />
              <p className="text-sm">ไม่พบข้อมูลฉากในสารบัญคลิปนี้</p>
            </div>
          ) : (
            scenes.map((sc, idx) => {
              const actInfo = ACTION_MAP[sc.action_type] || {
                label: sc.action_type || 'ทั่วไป',
                color: 'bg-white/10 text-slate-300 border-white/20'
              };
              const angleText = ANGLE_MAP[sc.angle_phase] || sc.angle_phase || 'มุมกล้องปกติ';
              const dur = ((sc.end || 0) - (sc.start || 0)).toFixed(1);

              return (
                <div
                  key={sc.id || idx}
                  className="p-3 sm:p-3.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] transition-all space-y-2.5"
                >
                  {/* Scene Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="w-6 h-6 rounded-lg bg-white/10 font-mono text-xs font-bold text-white flex items-center justify-center">
                        #{idx + 1}
                      </span>

                      {/* Timestamp Pill */}
                      <span className="px-2.5 py-0.5 rounded-lg bg-black/60 font-mono text-xs text-[#25F4EE] border border-[#25F4EE]/30 flex items-center gap-1">
                        <Clock className="w-3 h-3 text-[#25F4EE]" />
                        <span>{formatTime(sc.start)} - {formatTime(sc.end)}</span>
                        <span className="text-[10px] text-slate-400 font-normal">({dur}s)</span>
                      </span>

                      {/* Action Type Badge */}
                      <span className={`px-2.5 py-0.5 rounded-lg text-xs font-bold border ${actInfo.color}`}>
                        {actInfo.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      {/* Angle Phase */}
                      <span className="px-2 py-0.5 rounded-md bg-white/[0.05] text-slate-300 border border-white/[0.1] flex items-center gap-1">
                        <Compass className="w-3 h-3 text-slate-400" />
                        <span>{angleText}</span>
                      </span>

                      {/* Punch Zoom */}
                      {sc.punch_zoom && (
                        <span className="px-2 py-0.5 rounded-md bg-white/[0.05] text-slate-300 border border-white/[0.1] flex items-center gap-1 font-mono">
                          <ZoomIn className="w-3 h-3 text-cyan-400" />
                          <span>{Number(sc.punch_zoom).toFixed(2)}x</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Scene Description */}
                  {sc.description && (
                    <p className="text-xs sm:text-sm text-slate-200 leading-normal pl-8">
                      {sc.description}
                    </p>
                  )}

                  {/* Keywords Pills */}
                  {sc.keywords && Array.isArray(sc.keywords) && sc.keywords.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap pl-8 pt-0.5">
                      <Tag className="w-3 h-3 text-slate-500" />
                      {sc.keywords.map((kw, kIdx) => (
                        <span
                          key={kIdx}
                          className="px-2 py-0.5 rounded-md bg-white/[0.04] text-[11px] text-slate-400 border border-white/[0.06]"
                        >
                          #{kw}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-white/[0.08] text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>จับคู่กับบทพูดสคริปต์อัตโนมัติด้วยคำศัพท์และจังหวะเล่าเรื่อง</span>
          </div>
          <Button variant="secondary" size="sm" onClick={onClose}>
            ปิด
          </Button>
        </div>
      </div>
    </Modal>
  );
}
