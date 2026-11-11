import React, { useState, useEffect, useCallback } from 'react';
import { ModalLayer } from './ui/ModalLayer';
import {
  Cloud,
  CloudCheck,
  CheckCircle2,
  AlertCircle,
  HardDrive,
  FolderOpen,
  RefreshCw,
  X,
  ShieldCheck,
  FolderSync,
  Layers,
  ArrowDownToLine,
  FileVideo,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import Button from './ui/Button';
import { getArchiveStatus, getArchiveProgress, executeArchive, revealInExplorer } from '../api';

export default function CloudArchiveModal({ isOpen, onClose, onRefreshData }) {
  const [loading, setLoading] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [statusData, setStatusData] = useState(null);
  const [selectedProductIds, setSelectedProductIds] = useState(new Set());
  const [scope, setScope] = useState('video_only'); // 'video_only' or 'full'
  const [archiveResult, setArchiveResult] = useState(null);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);

  // 1. Fetch Archive Status from Backend
  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getArchiveStatus();
      setStatusData(data);
      // Default: select all products that have eligible clips
      if (data?.products) {
        const eligibleProds = data.products
          .filter((p) => p.eligible_bytes > 0)
          .map((p) => p.product_id);
        setSelectedProductIds(new Set(eligibleProds));
      }
    } catch (err) {
      console.error('Failed to load archive status:', err);
      setError(err.response?.data?.detail || err.message || 'ไม่สามารถโหลดข้อมูล Cloud Archive ได้');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setArchiveResult(null);
      setProgress(null);
      setError(null);
    }
  }, [isOpen, fetchStatus]);

  // 2. Selection Helpers
  const toggleProduct = (prodId) => {
    setSelectedProductIds((prev) => {
      const next = new Set(prev);
      if (next.has(prodId)) {
        next.delete(prodId);
      } else {
        next.add(prodId);
      }
      return next;
    });
  };

  const selectAll = () => {
    if (!statusData?.products) return;
    const allIds = statusData.products.filter((p) => p.eligible_bytes > 0).map((p) => p.product_id);
    setSelectedProductIds(new Set(allIds));
  };

  const deselectAll = () => {
    setSelectedProductIds(new Set());
  };

  // 3. Execute Archiving
  const handleStartArchive = async () => {
    if (selectedProductIds.size === 0) return;
    setArchiving(true);
    setError(null);
    setArchiveResult(null);
    setProgress({
      status: 'running',
      percent: 0,
      current_index: 0,
      total_items: selectedProductIds.size,
      current_file: 'กำลังเริ่มต้นกระบวนการ...',
      reclaimed_formatted: '0 B',
    });

    try {
      const res = await executeArchive({
        product_ids: Array.from(selectedProductIds),
        scope,
        async_mode: true,
      });

      if (res.status === 'started' || res.status === 'already_running') {
        const pollTimer = setInterval(async () => {
          try {
            const prog = await getArchiveProgress();
            setProgress(prog);

            if (prog.status === 'completed') {
              clearInterval(pollTimer);
              setArchiving(false);
              setArchiveResult(prog.result || {
                status: 'ok',
                archived_count: prog.total_items,
                reclaimed_formatted: prog.reclaimed_formatted,
                gdrive_vault: statusData?.gdrive_root,
              });
              onRefreshData?.();
              fetchStatus();
            } else if (prog.status === 'error') {
              clearInterval(pollTimer);
              setArchiving(false);
              setError(prog.error || 'เกิดข้อผิดพลาดในการสำรองข้อมูล');
            }
          } catch (pollErr) {
            console.warn('Progress poll warning:', pollErr);
          }
        }, 800);
      } else if (res.status === 'ok') {
        setArchiveResult(res);
        setArchiving(false);
        onRefreshData?.();
        fetchStatus();
      } else {
        setArchiving(false);
        setError(res.message || 'เกิดข้อผิดพลาดในการสำรองขึ้น Google Drive');
      }
    } catch (err) {
      setArchiving(false);
      console.error('Archiving failed:', err);
      setError(err.response?.data?.detail || err.message || 'เกิดข้อผิดพลาดในการสำรองข้อมูล');
    }
  };

  // 4. Open Explorer
  const handleOpenFolder = async (path) => {
    try {
      await revealInExplorer(path);
    } catch (err) {
      console.error('Failed to open explorer:', err);
    }
  };

  if (!isOpen) return null;

  const totalEligibleBytesSelected = (statusData?.products || [])
    .filter((p) => selectedProductIds.has(p.product_id))
    .reduce((sum, p) => sum + (p.eligible_bytes || 0), 0);

  const formatReclaim = (bytes) => {
    if (!bytes) return '0 MB';
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  return (
    <ModalLayer onClose={onClose} className="fixed inset-0 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-3xl rounded-3xl bg-[#0A0D14]/95 backdrop-blur-md border border-white/[0.08] shadow-2xl flex flex-col max-h-[92vh] overflow-hidden relative">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-white/[0.08] flex items-center justify-between relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE]">
              <Cloud className="w-5 h-5 font-bold" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-bold text-white tracking-wide">
                  ศูนย์สำรองข้อมูล Google Drive & คืนพื้นที่ดิสก์
                </h2>
                <span className="px-2 py-0.5 rounded-full bg-white/[0.06] text-slate-300 text-[10px] font-mono border border-white/[0.08]">
                  Smart Breadcrumbs
                </span>
              </div>
              <p className="text-xs text-slate-400">
                ย้ายไฟล์วิดีโอหนักที่โพสต์แล้วขึ้นคลาวด์ พร้อมคงรูปปกและประวัติในแอป 100%
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/[0.06] hover:bg-white/[0.12] text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer border border-white/[0.06]"
            aria-label="ปิดหน้าต่าง"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1 relative z-10 custom-scrollbar">
          {/* Top Banner: Google Drive Health & Reclaimable Space */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Google Drive Status Card */}
            <div className="p-3.5 rounded-2xl bg-[#0D111A] border border-white/[0.08] flex items-start gap-3">
              <div className="w-8 h-8 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE] flex-shrink-0 mt-0.5">
                <HardDrive className="w-4 h-4" />
              </div>
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold text-white">Google Drive Desktop</span>
                  {statusData?.gdrive_available ? (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400 text-[9px] border border-emerald-500/30">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      เชื่อมต่อแล้ว (G:)
                    </span>
                  ) : (
                    <span className="text-[10px] text-rose-400">ไม่พบไดรฟ์ G:</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 truncate" title={statusData?.gdrive_root || ''}>
                  {statusData?.gdrive_root || 'กำลังค้นหา Google Drive...'}
                </p>
              </div>
            </div>

            {/* Reclaimable Space Card */}
            <div className="p-3.5 rounded-2xl bg-[#0D111A] border border-[#25F4EE]/30 flex items-start gap-3">
              <div className="w-8 h-8 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE] flex-shrink-0 mt-0.5">
                <ArrowDownToLine className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-slate-300">พื้นที่พร้อมคืนลงไดรฟ์หลัก</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg font-black text-[#25F4EE]">
                    {statusData?.total_reclaimable_formatted || '0 GB'}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    ({statusData?.eligible_clips_count || 0} คลิปโพสต์แล้ว)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Backup Scope Options (Radio buttons) */}
          <div className="p-3.5 rounded-2xl bg-[#0D111A] border border-white/[0.08] space-y-2.5">
            <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-[#25F4EE]" />
              <span>เลือกระดับความลึกในการสำรองข้อมูล:</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <label
                className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                  scope === 'video_only'
                    ? 'bg-[#25F4EE]/[0.06] border-[#25F4EE]/40'
                    : 'bg-black/40 border-white/[0.08] hover:bg-white/[0.02]'
                }`}
              >
                <input
                  type="radio"
                  name="archiveScope"
                  value="video_only"
                  checked={scope === 'video_only'}
                  onChange={() => setScope('video_only')}
                  className="mt-0.5 accent-[#25F4EE] cursor-pointer"
                />
                <div className="space-y-0.5">
                  <span className="text-xs font-bold text-white block">
                    เฉพาะวิดีโอที่โพสต์แล้ว (แนะนำ)
                  </span>
                  <p className="text-[11px] text-slate-400 leading-tight">
                    ย้ายเฉพาะไฟล์ MP4 ที่โพสต์แล้วขึ้น Drive คืนพื้นที่เร็วที่สุด ปลอดภัย 100%
                  </p>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                  scope === 'full'
                    ? 'bg-[#25F4EE]/[0.06] border-[#25F4EE]/40'
                    : 'bg-black/40 border-white/[0.08] hover:bg-white/[0.02]'
                }`}
              >
                <input
                  type="radio"
                  name="archiveScope"
                  value="full"
                  checked={scope === 'full'}
                  onChange={() => setScope('full')}
                  className="mt-0.5 accent-[#25F4EE] cursor-pointer"
                />
                <div className="space-y-0.5">
                  <span className="text-xs font-bold text-white block">
                    ครบทั้งโปรเจกต์ (Full Product Archive)
                  </span>
                  <p className="text-[11px] text-slate-400 leading-tight">
                    ย้ายทั้งวิดีโอ + ฟุตเทจดิบ (01_Raw) + แคชดราฟต์ (03_Projects) คืนพื้นที่สูงสุด
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Product List with Selection */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300">
                รายการสินค้าที่พร้อมสำรอง ({selectedProductIds.size} / {statusData?.products?.length || 0} รายการ)
              </span>
              <div className="flex items-center gap-2 text-[11px]">
                <button
                  type="button"
                  onClick={selectAll}
                  className="text-[#25F4EE] hover:text-[#25F4EE]/80 cursor-pointer font-medium"
                >
                  เลือกทั้งหมด
                </button>
                <span className="text-slate-600">|</span>
                <button
                  type="button"
                  onClick={deselectAll}
                  className="text-slate-400 hover:text-slate-300 cursor-pointer font-medium"
                >
                  ยกเลิกทั้งหมด
                </button>
              </div>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1 custom-scrollbar">
              {loading ? (
                <div className="p-8 text-center text-slate-500 text-xs flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-[#25F4EE]" />
                  <span>กำลังสแกนคลิปที่โพสต์แล้ว...</span>
                </div>
              ) : (statusData?.products || []).length === 0 ? (
                <div className="p-6 text-center text-slate-400 text-xs rounded-xl bg-[#0D111A] border border-white/[0.08]">
                  ยังไม่มีคลิปที่โพสต์แล้ว หรือคลิปทั้งหมดถูกสำรองขึ้น Google Drive เรียบร้อยแล้วครับ
                </div>
              ) : (
                (statusData?.products || []).map((prod) => {
                  const isSelected = selectedProductIds.has(prod.product_id);
                  const isArchived = prod.all_archived;

                  return (
                    <div
                      key={prod.product_id}
                      onClick={() => !isArchived && toggleProduct(prod.product_id)}
                      className={`p-2.5 rounded-xl border flex items-center gap-3 transition-colors ${
                        isArchived
                          ? 'bg-white/[0.02] border-white/[0.06] opacity-70 cursor-default'
                          : isSelected
                          ? 'bg-[#25F4EE]/[0.06] border-[#25F4EE]/40 cursor-pointer'
                          : 'bg-[#0D111A] border-white/[0.08] hover:border-white/[0.15] hover:bg-white/[0.02] cursor-pointer'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected || isArchived}
                        disabled={isArchived}
                        onChange={() => toggleProduct(prod.product_id)}
                        className="accent-[#25F4EE] w-4 h-4 rounded cursor-pointer"
                        onClick={(e) => e.stopPropagation()}
                      />

                      {/* 3:4 Cover Art Preview */}
                      <div className="w-9 h-12 rounded-lg bg-black/60 border border-white/[0.08] overflow-hidden flex-shrink-0 flex items-center justify-center">
                        {prod.cover_url ? (
                          <img loading="lazy" decoding="async"
                            src={prod.cover_url}
                            alt={prod.product_name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <FileVideo className="w-4 h-4 text-slate-500" />
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-white truncate block">
                            {prod.product_name}
                          </span>
                          {isArchived && (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 text-[9px] font-mono border border-cyan-500/20">
                              <Cloud className="w-2.5 h-2.5" />
                              <span>อยู่ใน Drive แล้ว</span>
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-0.5">
                          <span>{prod.clips?.length || 0} คลิป</span>
                          <span>•</span>
                          <span className="text-[#25F4EE] font-mono">
                            {formatReclaim(prod.eligible_bytes || prod.total_bytes)}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Safety Notice */}
          <div className="p-3 rounded-xl bg-[#0D111A] border border-white/[0.08] flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-[#25F4EE] flex-shrink-0 mt-0.5" />
            <p className="text-[11px] text-slate-300 leading-relaxed">
              <strong>นโยบาย Smart Breadcrumbs:</strong> ระบบจะเก็บภาพปก 3:4 ในโฟลเดอร์{' '}
              <code className="text-[#25F4EE] font-mono">05_Covers_Thumbnails/</code> และประวัติการโพสต์ไว้ในแอปเสมอ
              หน้า Gallery จะยังเห็นรูปปกและสถิติครบถ้วน ไม่ว่างเปล่าแน่นอนครับ
            </p>
          </div>

          {/* Live Progress Bar Box */}
          {archiving && (
            <div className="p-4 rounded-2xl bg-[#0D111A] border border-[#25F4EE]/30 space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-[#25F4EE] font-bold">
                  <RefreshCw className="w-4 h-4 animate-spin text-[#25F4EE]" />
                  <span>กำลังสำรองข้อมูลขึ้น Google Drive...</span>
                </div>
                <span className="font-mono font-bold text-sm text-[#25F4EE]">
                  {progress?.percent ?? 0}%
                </span>
              </div>

              {/* Progress Track */}
              <div className="w-full bg-black/60 rounded-full h-2.5 overflow-hidden border border-white/[0.08] p-0.5">
                <div
                  className="bg-[#25F4EE] h-full rounded-full transition-all duration-300"
                  style={{ width: `${Math.max(3, progress?.percent ?? 0)}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-300">
                <div className="flex items-center gap-1.5 truncate max-w-md">
                  <span className="px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-300 font-mono text-[10px] border border-white/[0.08]">
                    {progress?.current_index ?? 0} / {progress?.total_items ?? selectedProductIds.size} รายการ
                  </span>
                  <span className="truncate text-slate-300 font-medium">
                    {progress?.current_file || progress?.product_name || 'กำลังประมวลผล...'}
                  </span>
                </div>
                <div className="text-right flex-shrink-0 text-slate-400">
                  คืนพื้นที่แล้ว: <strong className="text-emerald-400 font-mono">{progress?.reclaimed_formatted || '0 B'}</strong>
                </div>
              </div>
            </div>
          )}

          {/* Archive Result Box */}
          {archiveResult && (
            <div className="p-4 rounded-2xl bg-[#0D111A] border border-emerald-500/30 space-y-2.5 animate-in fade-in">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span>สำรองขึ้น Google Drive และคืนพื้นที่ดิสก์สำเร็จ!</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs pt-1 text-slate-200">
                <div className="p-2 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-slate-400 block text-[10px]">จำนวนคลิปที่สำรอง</span>
                  <span className="font-bold text-emerald-400 text-sm">
                    {archiveResult.archived_count} คลิป
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-slate-400 block text-[10px]">พื้นที่ที่ได้คืนทันที</span>
                  <span className="font-bold text-[#25F4EE] text-sm">
                    {archiveResult.reclaimed_formatted}
                  </span>
                </div>
              </div>
              <div className="pt-1 flex items-center justify-between">
                <span className="text-[11px] text-slate-300 truncate max-w-sm flex items-center gap-1.5" title={archiveResult.gdrive_vault}>
                  <FolderOpen className="w-3.5 h-3.5 text-[#25F4EE] flex-shrink-0" />
                  <span>เก็บที่:</span>
                  <code className="text-[#25F4EE]">{archiveResult.gdrive_vault}</code>
                </span>
                <button
                  type="button"
                  onClick={() => handleOpenFolder(archiveResult.gdrive_vault)}
                  className="px-3 py-1 rounded-xl bg-white/[0.08] hover:bg-white/[0.14] text-white border border-white/[0.1] text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  <span>เปิดโฟลเดอร์ใน Drive</span>
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-[#0D111A] border border-rose-500/30 text-xs text-rose-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                <span>{error}</span>
              </div>
              <button
                type="button"
                onClick={fetchStatus}
                className="px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/30 text-[11px] font-bold flex items-center gap-1 cursor-pointer transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                <span>ลองใหม่</span>
              </button>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-white/[0.08] bg-[#0A0D14] flex items-center justify-between relative z-10">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-[#25F4EE]" />
            <span>
              คืนพื้นที่ดิสก์:{' '}
              <strong className="text-white font-mono">{formatReclaim(totalEligibleBytesSelected)}</strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={onClose}
              variant="secondary"
              size="sm"
              className="px-4 py-1.5 rounded-xl cursor-pointer"
            >
              ปิดหน้าต่าง
            </Button>
            <Button
              onClick={handleStartArchive}
              disabled={selectedProductIds.size === 0 || archiving || !statusData?.gdrive_available}
              variant="primary"
              size="sm"
              className="px-5 py-1.5 rounded-xl bg-[#25F4EE] hover:bg-[#20ded8] text-slate-950 font-bold cursor-pointer flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {archiving ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>กำลังสำรองและคืนพื้นที่...</span>
                </>
              ) : (
                <>
                  <CloudCheck className="w-4 h-4" />
                  <span>สำรองขึ้น Google Drive ทันที</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </ModalLayer>
  );
}
