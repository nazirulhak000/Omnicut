import React, { useState, useEffect, useRef } from 'react';
import { Play, Check, AlertCircle, RefreshCw, X, Film, CheckSquare, Square, Zap, Loader2 } from 'lucide-react';
import { Modal, Button, Badge } from './ui';
import { startBatchRender, getBatchRenderStatus, cancelBatchRender } from '../api';

const GEMINI_VOICE_OPTIONS = [
  { id: 'gemini_puck_male_hype', label: 'Puck — ชายพลังสูง TikTok (ค่าเริ่มต้น)', gender: 'male' },
  { id: 'gemini_charon_male_pro', label: 'Charon — ชายทุ้มลึก น่าเชื่อถือ', gender: 'male' },
  { id: 'gemini_kore_female_bright', label: 'Kore — หญิงสดใส ป้ายยาเก่ง', gender: 'female' },
  { id: 'gemini_aoede_female_pro', label: 'Aoede — หญิงพรีเมียม นุ่มนวล', gender: 'female' },
  { id: 'gemini_fenrir_male_strong', label: 'Fenrir — ชายสตรอง คมเข้ม', gender: 'male' },
];

export default function BatchRenderModal({
  isOpen,
  onClose,
  product,
  angles: propAngles,
  voicePreset: selectedVoicePreset = 'gemini_puck_male_hype',
  onBatchCompleted,
  showToast,
}) {
  const [selectedAngleIds, setSelectedAngleIds] = useState(new Set());
  const [voiceRate, setVoiceRate] = useState('+15%');
  const [stylePreset, setStylePreset] = useState('clean_tech_review');
  const [starting, setStarting] = useState(false);
  const [activeBatch, setActiveBatch] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const pollTimerRef = useRef(null);

  const angles = propAngles || product?.angles || [];
  const selectedVoiceOption = GEMINI_VOICE_OPTIONS.find(v => v.id === selectedVoicePreset);

  // Pre-select angles that are not posted and not already rendered
  useEffect(() => {
    if (isOpen) {
      const initialSelected = new Set();
      angles.forEach((a) => {
        const aid = a.angle_id || a.id;
        const isDone = a.status === 'posted' || a.status === 'rendered';
        if (!isDone && aid) {
          initialSelected.add(String(aid));
        }
      });
      setSelectedAngleIds(initialSelected);
      setActiveBatch(null);
    } else {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    }
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [isOpen, product?.id, angles.length]);

  const toggleSelectAngle = (aid) => {
    const next = new Set(selectedAngleIds);
    if (next.has(aid)) {
      next.delete(aid);
    } else {
      next.add(aid);
    }
    setSelectedAngleIds(next);
  };

  const selectAllUnrendered = () => {
    const next = new Set();
    angles.forEach((a) => {
      const aid = String(a.angle_id || a.id);
      if (a.status !== 'posted' && a.status !== 'rendered') {
        next.add(aid);
      }
    });
    setSelectedAngleIds(next);
  };

  const clearSelection = () => {
    setSelectedAngleIds(new Set());
  };

  const handleStartBatch = async () => {
    if (selectedAngleIds.size === 0) {
      showToast?.('กรุณาเลือกอย่างน้อย 1 มุมมองที่ต้องการเรนเดอร์', 'warning');
      return;
    }

    setStarting(true);
    try {
      const selectedOpt = GEMINI_VOICE_OPTIONS.find(v => v.id === selectedVoicePreset);
      const payload = {
        product_id: String(product.id),
        angle_ids: Array.from(selectedAngleIds),
        voice_gender: selectedOpt?.gender || 'male',
        voice_rate: voiceRate,
        voice_mode: 'gemini_tts',
        voice_preset: selectedVoicePreset,
        ad_tone: 'commercial_hype',
        style_preset: stylePreset,
        font_name: 'IBMPlex',
        bilingual_subtitles: true,
        use_ai_vision: true,
      };

      const res = await startBatchRender(payload);
      showToast?.(`เริ่มเรนเดอร์ ${res.total_items} มุมมองในเบื้องหลังเรียบร้อยแล้ว`);
      setActiveBatch(res);

      // Start polling batch status
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      pollTimerRef.current = setInterval(async () => {
        try {
          const statusRes = await getBatchRenderStatus(res.batch_id);
          setActiveBatch(statusRes);

          if (statusRes.status === 'completed' || statusRes.status === 'failed' || statusRes.status === 'cancelled') {
            clearInterval(pollTimerRef.current);
            onBatchCompleted?.(statusRes);
            if (statusRes.status === 'completed') {
              showToast?.(`เรนเดอร์ครบทั้งหมด ${statusRes.completed_items} คลิปเรียบร้อยแล้ว`);
            }
          }
        } catch {
          // Keep polling unless stopped
        }
      }, 2000);

    } catch (err) {
      showToast?.(err.response?.data?.detail || err.message || 'ไม่สามารถเริ่มคิวเรนเดอร์ได้', 'error');
    } finally {
      setStarting(false);
    }
  };

  const handleCancelBatch = async () => {
    if (!activeBatch?.batch_id) return;
    setCancelling(true);
    try {
      await cancelBatchRender(activeBatch.batch_id);
      showToast?.('ส่งคำสั่งยกเลิกคิวเรนเดอร์แล้ว');
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      const updated = await getBatchRenderStatus(activeBatch.batch_id);
      setActiveBatch(updated);
      onBatchCompleted?.(updated);
    } catch (err) {
      showToast?.('ไม่สามารถยกเลิกคิวได้: ' + err.message, 'error');
    } finally {
      setCancelling(false);
    }
  };

  const isRunning = activeBatch && (activeBatch.status === 'queued' || activeBatch.status === 'processing');
  const isFinished = activeBatch && (activeBatch.status === 'completed' || activeBatch.status === 'failed' || activeBatch.status === 'cancelled');

  return (
    <Modal
      isOpen={isOpen}
      onClose={isRunning ? () => showToast?.('คิวเรนเดอร์กำลังทำงานอยู่ในเบื้องหลัง สามารถดูสถานะได้จาก Activity Center', 'info') : onClose}
      title="เรนเดอร์หลายมุมมองพร้อมกัน (Batch Render Queue)"
      subtitle="ระบบต่อคิวเรนเดอร์วิดีโอ MP4 อัตโนมัติทีละมุมมอง ป้องกันเครื่องกระตุก และอัปเดตความคืบหน้ารวมทันที"
      maxWidth="max-w-2xl"
    >
      <div className="space-y-4">
        {/* Active Progress View */}
        {activeBatch ? (
          <div className="space-y-4 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  {isRunning && <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />}
                  {isFinished ? 'ผลการเรนเดอร์ชุด' : 'กำลังดำเนินการในคิวเบื้องหลัง'}
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  สินค้า: <span className="text-slate-200 font-medium">{product?.title || 'สินค้า'}</span>
                </p>
              </div>
              <Badge
                variant={
                  activeBatch.status === 'completed' ? 'success' :
                  activeBatch.status === 'processing' ? 'warning' :
                  activeBatch.status === 'failed' ? 'danger' : 'neutral'
                }
              >
                {activeBatch.status === 'completed' ? 'เสร็จสมบูรณ์' :
                 activeBatch.status === 'processing' ? 'กำลังเรนเดอร์' :
                 activeBatch.status === 'failed' ? 'ไม่สำเร็จ' :
                 activeBatch.status === 'cancelled' ? 'ยกเลิกแล้ว' : 'อยู่ในคิว'}
              </Badge>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono text-slate-300">
                <span>ความคืบหน้ารวม</span>
                <span>{activeBatch.progress || 0}% ({activeBatch.completed_items || 0}/{activeBatch.total_items || 0} คลิป)</span>
              </div>
              <div className="w-full h-2.5 bg-black/40 rounded-full overflow-hidden border border-white/10">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-300 rounded-full"
                  style={{ width: `${Math.max(activeBatch.progress || 0, isRunning ? 5 : 0)}%` }}
                />
              </div>
              {activeBatch.current_angle_name && isRunning && (
                <p className="text-[11px] text-cyan-300 truncate">
                  กำลังตัดต่อ: {activeBatch.current_angle_name}
                </p>
              )}
            </div>

            {/* Item List */}
            <div className="space-y-2 max-h-60 overflow-y-auto no-scrollbar pt-1">
              {(activeBatch.items || []).map((item, idx) => (
                <div
                  key={item.angle_id || idx}
                  className="flex items-center justify-between p-2.5 rounded-xl bg-black/30 border border-white/[0.05] text-xs"
                >
                  <div className="flex items-center gap-2.5 min-w-0 pr-2">
                    <span className="font-mono text-slate-500 text-[11px] w-5 text-right">{idx + 1}.</span>
                    <span className="font-medium text-slate-200 truncate">{item.angle_name}</span>
                  </div>
                  <div className="shrink-0">
                    {item.status === 'rendered' ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                        <Check className="w-3 h-3" /> เสร็จแล้ว
                      </span>
                    ) : item.status === 'in_production' ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-amber-300 font-bold bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                        <Loader2 className="w-3 h-3 animate-spin" /> กำลังตัดต่อ
                      </span>
                    ) : item.status === 'failed' ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-red-400 font-bold bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20" title={item.error || ''}>
                        <AlertCircle className="w-3 h-3" /> ติดปัญหา
                      </span>
                    ) : item.status === 'skipped' ? (
                      <span className="text-[11px] text-slate-400 bg-white/5 px-2 py-0.5 rounded-full">ข้าม (โพสต์แล้ว)</span>
                    ) : (
                      <span className="text-[11px] text-slate-400 bg-white/5 px-2 py-0.5 rounded-full">รอคิว</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Actions while running or finished */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
              {isRunning && (
                <Button
                  variant="danger"
                  size="sm"
                  onClick={handleCancelBatch}
                  loading={cancelling}
                >
                  ยกเลิกคิวเรนเดอร์
                </Button>
              )}
              {isFinished && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={onClose}
                >
                  ปิดหน้าต่าง
                </Button>
              )}
            </div>
          </div>
        ) : (
          /* Selection & Configuration View */
          <>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
              <div className="text-xs text-slate-300">
                เลือกมุมมองที่ต้องการเรนเดอร์ ({selectedAngleIds.size}/{angles.length} มุมมอง)
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={selectAllUnrendered}
                  className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
                >
                  เลือกที่ยังไม่ได้ตัดต่อทั้งหมด
                </button>
                <span className="text-slate-600">|</span>
                <button
                  type="button"
                  onClick={clearSelection}
                  className="text-xs text-slate-400 hover:text-slate-300 transition-colors cursor-pointer"
                >
                  ล้างการเลือก
                </button>
              </div>
            </div>

            {/* Angles Checklist */}
            <div className="space-y-2 max-h-64 overflow-y-auto no-scrollbar pr-1">
              {angles.map((ang, idx) => {
                const aid = String(ang.angle_id || ang.id || idx);
                const isSelected = selectedAngleIds.has(aid);
                const isPosted = ang.status === 'posted' || ang.status === 'rendered';
                const hasVideo = (ang.selected_videos && ang.selected_videos.length > 0) || !!ang.selected_video || (product?.default_videos && product.default_videos.length > 0);

                return (
                  <div
                    key={aid}
                    onClick={() => !isPosted && toggleSelectAngle(aid)}
                    className={`flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer select-none ${
                      isSelected
                        ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-100'
                        : isPosted
                        ? 'bg-white/[0.01] border-white/[0.04] text-slate-500 opacity-60 cursor-not-allowed'
                        : 'bg-white/[0.03] border-white/[0.08] hover:bg-white/[0.05] text-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0 pr-2">
                      <div className="shrink-0 text-cyan-400">
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-cyan-400" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-500" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-white truncate">
                            มุมที่ {idx + 1}: {ang.angle_name || 'มุมมองขาย'}
                          </span>
                          {ang.status === 'rendered' && (
                            <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                              ตัดต่อแล้ว
                            </span>
                          )}
                          {ang.status === 'posted' && (
                            <span className="text-[10px] text-purple-400 font-bold bg-purple-500/10 px-1.5 py-0.5 rounded border border-purple-500/20">
                              โพสต์แล้ว
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 truncate mt-0.5">
                          {ang.hook_title || 'ไม่มีข้อความพาดหัว'}
                        </p>
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center gap-2">
                      {hasVideo ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-300 bg-white/5 px-2 py-0.5 rounded">
                          <Film className="w-3 h-3 text-cyan-400" /> มีคลิป
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20" title="จะใช้คลิปดิบส่วนกลางในระบบ">
                          <AlertCircle className="w-3 h-3" /> ใช้คลิปกลาง
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between gap-3 rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2.5 text-xs">
              <div className="min-w-0">
                <p className="font-bold text-cyan-200">เสียงพากย์</p>
                <p className="mt-0.5 text-slate-400">ใช้เสียงที่เลือกจากแถบเตรียมเสียงด้านหน้าสินค้า</p>
              </div>
              <span className="shrink-0 max-w-[48%] truncate rounded-lg bg-black/20 px-2 py-1 font-semibold text-slate-200" title={selectedVoiceOption?.label || selectedVoicePreset}>
                {selectedVoiceOption?.label || selectedVoicePreset}
              </span>
            </div>

            {/* Quick Render Options */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
              <div className="hidden">
                <label className="block text-xs font-bold text-slate-300 mb-1.5">เสียงพากย์ Gemini TTS</label>
                <select
                  value={selectedVoicePreset}
                  disabled
                  className="w-full bg-[#0f172a] border border-white/10 rounded-xl px-3 py-2 text-xs font-medium text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors cursor-pointer"
                >
                  {GEMINI_VOICE_OPTIONS.map((opt) => (
                    <option key={opt.id} value={opt.id} className="bg-slate-900 text-slate-200">
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5">สไตล์วิดีโอ</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setStylePreset('clean_tech_review')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                      stylePreset === 'clean_tech_review'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10'
                    }`}
                  >
                    Clean Tech
                  </button>
                  <button
                    type="button"
                    onClick={() => setStylePreset('commercial_premium')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                      stylePreset === 'commercial_premium'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10'
                    }`}
                  >
                    Commercial
                  </button>
                </div>
              </div>
            </div>

            {/* Bottom Actions */}
            <div className="flex items-center justify-between pt-2 border-t border-white/10">
              <span className="text-xs text-slate-400">
                พร้อมตัดต่อ: <strong className="text-cyan-300">{selectedAngleIds.size}</strong> มุมมอง
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="neutral"
                  size="sm"
                  onClick={onClose}
                >
                  ปิด
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleStartBatch}
                  loading={starting}
                  disabled={selectedAngleIds.size === 0}
                  icon={Zap}
                >
                  เริ่มเรนเดอร์ {selectedAngleIds.size} มุมมอง
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
