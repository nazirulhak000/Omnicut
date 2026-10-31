import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  HardDrive,
  UploadCloud,
  DownloadCloud,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  FolderCheck,
  ExternalLink,
  ShieldCheck,
  Coffee,
  Laptop,
  Home,
  ArrowRight,
  Trash2,
  Sparkles,
  X,
  FileCheck2,
  Clock,
  Layers,
  CheckSquare,
  Square,
  Archive,
  Film,
  Tag,
  Calendar,
} from 'lucide-react';
import { getSSDDrives, inspectSSDDrive, stageToSSD, reconcileFromSSD, getScheduleQueue } from '../api';
import { toMediaUrl } from '../lib/mediaUrl';
import { Button } from './ui';

export default function SSDSyncModal({ isOpen, onClose, onRefreshData }) {
  const [activeTab, setActiveTab] = useState('stage'); // 'stage' | 'reconcile' | 'guide'
  const [drives, setDrives] = useState([]);
  const [selectedDrive, setSelectedDrive] = useState('');
  const [loadingDrives, setLoadingDrives] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const [vaultInfo, setVaultInfo] = useState(null);

  // Staging states
  const [pendingClips, setPendingClips] = useState([]);
  const [loadingClips, setLoadingClips] = useState(false);
  const [selectedExportIds, setSelectedExportIds] = useState(new Set());
  const [staging, setStaging] = useState(false);
  const [stageProgress, setStageProgress] = useState(null);
  const [stageSuccess, setStageSuccess] = useState(null);
  const [stageError, setStageError] = useState(null);

  // Reconcile states
  const [reconciling, setReconciling] = useState(false);
  const [retentionMode, setRetentionMode] = useState('archive'); // 'archive' | 'delete' | 'keep'
  const [reconcileSuccess, setReconcileSuccess] = useState(null);
  const [reconcileError, setReconcileError] = useState(null);

  // 1. Fetch drives
  const fetchDrives = useCallback(async () => {
    setLoadingDrives(true);
    setStageError(null);
    setReconcileError(null);
    try {
      const res = await getSSDDrives();
      const list = res.drives || [];
      setDrives(list);
      const candidate = list.find((d) => d.is_external_candidate) || list.find((d) => d.letter !== 'C') || list[0];
      if (candidate) {
        setSelectedDrive(candidate.drive);
      }
    } catch (err) {
      console.error('Failed to scan drives:', err);
      setStageError('ไม่สามารถตรวจจับไดรฟ์บนเครื่องได้ กรุณากรอกพาธไดรฟ์ด้วยตนเอง');
    } finally {
      setLoadingDrives(false);
    }
  }, []);

  // 2. Fetch pending clips from schedule queue
  const fetchPendingClips = useCallback(async () => {
    setLoadingClips(true);
    try {
      const queueRes = await getScheduleQueue();
      const rawItems = Array.isArray(queueRes) ? queueRes : (queueRes?.items || []);
      const filtered = rawItems.filter(
        (item) => item.status !== 'posted' && !item.posted_at
      );
      setPendingClips(filtered);
      // Default: select all pending clips
      const idSet = new Set(filtered.map((item) => item.export_id || item.id));
      setSelectedExportIds(idSet);
    } catch (err) {
      console.error('Failed to load pending queue:', err);
    } finally {
      setLoadingClips(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchDrives();
      fetchPendingClips();
      setStageSuccess(null);
      setReconcileSuccess(null);
      setStageError(null);
      setReconcileError(null);
    }
  }, [isOpen, fetchDrives, fetchPendingClips]);

  // 3. Inspect selected drive
  useEffect(() => {
    let isMounted = true;
    if (!selectedDrive) {
      setVaultInfo(null);
      return;
    }

    const checkVault = async () => {
      setInspecting(true);
      try {
        const info = await inspectSSDDrive(selectedDrive);
        if (isMounted) setVaultInfo(info);
      } catch (err) {
        if (isMounted) setVaultInfo(null);
      } finally {
        if (isMounted) setInspecting(false);
      }
    };

    checkVault();
    return () => {
      isMounted = false;
    };
  }, [selectedDrive]);

  // Clip selection helpers
  const toggleSelectClip = (exportId) => {
    setSelectedExportIds((prev) => {
      const next = new Set(prev);
      if (next.has(exportId)) {
        next.delete(exportId);
      } else {
        next.add(exportId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    const all = new Set(pendingClips.map((c) => c.export_id || c.id));
    setSelectedExportIds(all);
  };

  const handleDeselectAll = () => {
    setSelectedExportIds(new Set());
  };

  // 4. Handle 1-Click Staging
  const handleStartStaging = async () => {
    if (!selectedDrive || selectedExportIds.size === 0) return;
    setStaging(true);
    setStageProgress('กำลังคัดลอกคลิปและคำนวณ SHA-256...');
    setStageError(null);
    setStageSuccess(null);

    try {
      const res = await stageToSSD({
        target_drive: selectedDrive,
        export_ids: Array.from(selectedExportIds),
        include_all_pending: false,
      });

      setStageProgress('กำลัง Flush Disk Buffer...');
      setStageSuccess({
        batchId: res.batch_id,
        stagedCount: res.staged_count,
        vaultPath: res.vault_path,
        safeToEject: res.safe_to_eject,
      });

      // Refresh inspect and pending
      const updatedInfo = await inspectSSDDrive(selectedDrive);
      setVaultInfo(updatedInfo);
      fetchPendingClips();
    } catch (err) {
      console.error('Staging failed:', err);
      setStageError(err.response?.data?.detail || err.message || 'เกิดข้อผิดพลาดในการส่งออกลง SSD');
    } finally {
      setStaging(false);
      setStageProgress(null);
    }
  };

  // 5. Handle 1-Click Reconciliation
  const handleStartReconcile = async () => {
    if (!selectedDrive) return;
    setReconciling(true);
    setReconcileError(null);
    setReconcileSuccess(null);

    try {
      const res = await reconcileFromSSD({
        target_drive: selectedDrive,
        retention_mode: retentionMode,
        clean_ssd_after: retentionMode === 'delete',
      });

      if (res.status === 'ok') {
        setReconcileSuccess({
          reconciledCount: res.reconciled_count,
          alreadyPostedCount: res.already_posted_count,
          cleanedCount: res.cleaned_media_count,
          archivedCount: res.archived_media_count,
          pendingUnpostedCount: res.pending_unposted_count,
          retentionMode: res.retention_mode,
        });
        onRefreshData?.();
        const updatedInfo = await inspectSSDDrive(selectedDrive);
        setVaultInfo(updatedInfo);
      } else {
        setReconcileError(res.message || 'ไม่พบข้อมูลที่ต้องซิงค์');
      }
    } catch (err) {
      console.error('Reconciliation failed:', err);
      setReconcileError(err.response?.data?.detail || err.message || 'เกิดข้อผิดพลาดในการซิงค์ข้อมูลกลับ');
    } finally {
      setReconciling(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-3xl rounded-3xl bg-[#070b14] border border-white/[0.12] shadow-2xl flex flex-col max-h-[92vh] overflow-hidden relative">
        {/* Ambient Top Glow */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-emerald-500/10 via-[#25F4EE]/10 to-transparent rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-white/[0.08] flex items-center justify-between relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-400 to-[#25F4EE] flex items-center justify-center shadow-lg shadow-emerald-500/20 text-black">
              <HardDrive className="w-5 h-5 font-bold" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-bold text-white tracking-wide">
                  ศูนย์จัดการ External SSD (Sneakernet Hub)
                </h2>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono border border-emerald-500/30">
                  100% GUI
                </span>
              </div>
              <p className="text-xs text-slate-400">
                ส่งออกคลิปไปอัปโหลดที่คาเฟ่ผ่าน Chrome Extension และซิงค์ผลกลับบ้านแบบ 1-Click
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white flex items-center justify-center transition-all cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Drive Selector Bar (Always Visible) */}
        <div className="px-5 py-3 bg-black/40 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative z-10">
          <div className="flex items-center gap-2 flex-1">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5 flex-shrink-0">
              <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
              ไดรฟ์ External SSD:
            </span>
            <select
              value={selectedDrive}
              onChange={(e) => setSelectedDrive(e.target.value)}
              className="flex-1 bg-slate-900/90 border border-white/[0.15] focus:border-emerald-400 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none transition-all cursor-pointer font-mono"
            >
              {drives.length === 0 ? (
                <option value="">-- ไม่พบไดรฟ์ภายนอก --</option>
              ) : (
                drives.map((d) => (
                  <option key={d.drive} value={d.drive}>
                    {d.drive} {d.is_external_candidate ? '⭐ [External/USB]' : `[${d.drive_type}]`} — ว่าง {d.free_gb} GB / {d.total_gb} GB
                  </option>
                ))
              )}
            </select>
          </div>
          <button
            type="button"
            onClick={fetchDrives}
            disabled={loadingDrives}
            className="px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.1] text-xs font-medium text-slate-300 hover:text-white flex items-center justify-center gap-1.5 transition-all cursor-pointer flex-shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingDrives ? 'animate-spin text-emerald-400' : ''}`} />
            <span>ค้นหาไดรฟ์ใหม่</span>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-5 pt-3 border-b border-white/[0.06] flex items-center gap-2 relative z-10 bg-[#070b14]/50">
          <button
            type="button"
            onClick={() => setActiveTab('stage')}
            className={`px-4 py-2.5 rounded-t-2xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all cursor-pointer border-b-2 ${
              activeTab === 'stage'
                ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/[0.02]'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            <span>1. ส่งออกไป SSD (ก่อนไปคาเฟ่)</span>
            {pendingClips.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px]">
                {pendingClips.length} คลิปพร้อมส่ง
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('reconcile')}
            className={`px-4 py-2.5 rounded-t-2xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all cursor-pointer border-b-2 ${
              activeTab === 'reconcile'
                ? 'border-[#25F4EE] text-[#25F4EE] bg-[#25F4EE]/10'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/[0.02]'
            }`}
          >
            <DownloadCloud className="w-4 h-4" />
            <span>2. ซิงค์ผลกลับบ้าน (เมื่อกลับมา)</span>
            {vaultInfo?.posted_count > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/30 text-emerald-300 text-[10px]">
                {vaultInfo.posted_count} โพสต์แล้ว
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('guide')}
            className={`px-4 py-2.5 rounded-t-2xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all cursor-pointer border-b-2 ${
              activeTab === 'guide'
                ? 'border-amber-400 text-amber-300 bg-amber-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/[0.02]'
            }`}
          >
            <Coffee className="w-4 h-4" />
            <span>3. ขั้นตอนที่คาเฟ่</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 flex-1 overflow-y-auto space-y-4 relative z-10 custom-scrollbar">
          {/* TAB 1: STAGE TO SSD */}
          {activeTab === 'stage' && (
            <div className="space-y-4">
              {/* Status Banner */}
              <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-950/40 to-slate-900/60 border border-emerald-500/30 flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    เตรียมคลิปและข้อมูลลง External SSD
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    คุณสามารถเลือกติ๊กคลิปที่ต้องการนำไปโพสต์วันนี้ได้ ระบบจะคัดลอกไฟล์วิดีโอ, ภาพปก, แคปชัน, แฮชแท็ก,
                    รหัสสินค้าตะกร้า และตัว <strong>Chrome Extension</strong> ลงใน SSD ให้อัตโนมัติ
                  </p>
                </div>
              </div>

              {/* Clip Selector Card */}
              <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">เลือกคลิปที่จะส่งออกไป SSD:</span>
                    <span className="text-xs font-mono text-emerald-400">
                      ({selectedExportIds.size} / {pendingClips.length} คลิป)
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs">
                    <button
                      type="button"
                      onClick={handleSelectAll}
                      className="px-2 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white transition-all cursor-pointer"
                    >
                      เลือกทั้งหมด
                    </button>
                    <button
                      type="button"
                      onClick={handleDeselectAll}
                      className="px-2 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-slate-200 transition-all cursor-pointer"
                    >
                      ยกเลิกทั้งหมด
                    </button>
                  </div>
                </div>

                {/* Clips Scroll List */}
                {loadingClips ? (
                  <div className="py-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2 font-mono">
                    <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
                    <span>กำลังโหลดรายการคลิป...</span>
                  </div>
                ) : pendingClips.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-400 border border-dashed border-white/[0.1] rounded-xl">
                    🎉 ไม่มีคลิปค้างรอโพสต์ในระบบ ทุกคลิปถูกโพสต์หมดแล้ว!
                  </div>
                ) : (
                  <div className="max-h-56 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                    {pendingClips.map((clip) => {
                      const expId = clip.export_id || clip.id;
                      const isSelected = selectedExportIds.has(expId);
                      return (
                        <div
                          key={expId}
                          onClick={() => toggleSelectClip(expId)}
                          className={`p-2.5 rounded-xl border transition-all flex items-center justify-between gap-3 cursor-pointer select-none ${
                            isSelected
                              ? 'bg-emerald-500/10 border-emerald-500/40 shadow-sm'
                              : 'bg-slate-900/40 border-white/[0.06] hover:border-white/[0.15]'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                            ) : (
                              <Square className="w-4 h-4 text-slate-500 flex-shrink-0" />
                            )}
                            <div className="w-8 h-12 rounded-lg bg-black border border-white/[0.1] overflow-hidden flex-shrink-0 relative">
                              {clip.cover_path || clip.cover_url ? (
                                <img
                                  src={toMediaUrl(clip.cover_url || clip.cover_path)}
                                  alt="Cover"
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <Film className="w-4 h-4 text-slate-500 m-auto mt-3" />
                              )}
                            </div>
                            <div className="min-w-0">
                              <div className="text-xs font-bold text-white truncate">
                                {clip.hook_title || clip.product_name || clip.project_name || 'คลิปวิดีโอ'}
                              </div>
                              <div className="text-[11px] text-slate-400 truncate max-w-sm">
                                {clip.caption || 'ไม่มีแคปชัน'}
                              </div>
                              <div className="flex items-center gap-2 pt-0.5 text-[10px] text-slate-400 font-mono">
                                {clip.tiktok_product_id && (
                                  <span className="text-amber-300 flex items-center gap-1">
                                    <Tag className="w-2.5 h-2.5" /> ตะกร้า: {clip.tiktok_product_id}
                                  </span>
                                )}
                                {clip.scheduled_at && (
                                  <span className="flex items-center gap-1">
                                    <Clock className="w-2.5 h-2.5" /> {clip.scheduled_at.replace('T', ' ').slice(0, 16)}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono border border-emerald-500/30 flex-shrink-0">
                            พร้อมส่งออก
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Staging Action Row */}
                <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-white/[0.06]">
                  <div>
                    <div className="text-[10px] text-slate-400 font-mono">ปลายทาง: {selectedDrive}OmniCut_Portable_Vault</div>
                    <div className="text-xs text-slate-300">
                      พร้อมส่งออก: <span className="font-bold text-emerald-400">{selectedExportIds.size}</span> คลิป
                    </div>
                  </div>
                  <Button
                    onClick={handleStartStaging}
                    disabled={!selectedDrive || staging || selectedExportIds.size === 0}
                    variant="primary"
                    size="md"
                    className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-black font-bold px-6 py-2.5 rounded-xl shadow-lg shadow-emerald-500/20 cursor-pointer"
                  >
                    {staging ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-black" />
                    ) : (
                      <UploadCloud className="w-4 h-4 text-black" />
                    )}
                    <span>{staging ? 'กำลังคัดลอกข้อมูล...' : `เริ่มส่งออก ${selectedExportIds.size} คลิปที่เลือก`}</span>
                  </Button>
                </div>

                {/* Progress Text */}
                {stageProgress && (
                  <div className="p-3 rounded-xl bg-slate-900 border border-emerald-500/30 text-xs text-emerald-300 flex items-center gap-2 animate-pulse font-mono">
                    <RefreshCw className="w-4 h-4 animate-spin flex-shrink-0" />
                    <span>{stageProgress}</span>
                  </div>
                )}

                {/* Success Card */}
                {stageSuccess && (
                  <div className="p-4 rounded-2xl bg-emerald-950/60 border border-emerald-400/50 space-y-2">
                    <div className="flex items-center gap-2 text-emerald-300 font-bold text-sm">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <span>บันทึกข้อมูลและสร้าง Vault บน SSD สำเร็จสมบูรณ์!</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs pt-1 text-slate-200">
                      <div className="p-2 rounded-lg bg-black/40">
                        <span className="text-slate-400 block text-[10px]">จำนวนคลิปที่ส่งออก</span>
                        <span className="font-bold text-white text-sm">{stageSuccess.stagedCount} คลิป</span>
                      </div>
                      <div className="p-2 rounded-lg bg-black/40">
                        <span className="text-slate-400 block text-[10px]">รหัสรอบส่งออก</span>
                        <span className="font-mono text-emerald-300 truncate block">{stageSuccess.batchId}</span>
                      </div>
                      <div className="p-2 rounded-lg bg-black/40 col-span-2 sm:col-span-1">
                        <span className="text-slate-400 block text-[10px]">สถานะความปลอดภัย</span>
                        <span className="font-bold text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> ถอดสาย USB ได้ทันที
                        </span>
                      </div>
                    </div>
                    <div className="text-[11px] text-slate-400 pt-1">
                      💡 <strong>พร้อมแล้ว:</strong> คุณสามารถถอด External SSD ตัวนี้ใส่กระเป๋าไปทำงานที่คาเฟ่ได้เลย!
                    </div>
                  </div>
                )}

                {/* Error Box */}
                {stageError && (
                  <div className="p-3 rounded-xl bg-red-950/50 border border-red-500/40 text-xs text-red-200 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                    <span>{stageError}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: RECONCILE FROM SSD */}
          {activeTab === 'reconcile' && (
            <div className="space-y-4">
              {/* Status Banner */}
              <div className="p-4 rounded-2xl bg-gradient-to-r from-cyan-950/40 to-slate-900/60 border border-[#25F4EE]/30 flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#25F4EE]/20 text-[#25F4EE] flex items-center justify-center flex-shrink-0 mt-0.5">
                  <DownloadCloud className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    ซิงค์ผลการโพสต์กลับเข้าเครื่องหลัก (เมื่อกลับถึงบ้าน)
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    ระบบจะอ่านสถานะจาก Extension บน SSD ว่าคลิปไหนโพสต์สำเร็จแล้วบ้าง จากนั้นจะปรับสถานะเป็น <strong>posted</strong> ย้ายไฟล์เข้าโฟลเดอร์ <strong>Posted/</strong> และจัดการไฟล์บน SSD ตามนโยบายที่คุณเลือก
                  </p>
                </div>
              </div>

              {/* Current Vault Inspection Status */}
              <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">สถานะข้อมูลบน External SSD ปัจจุบัน:</span>
                  {inspecting && (
                    <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                      <RefreshCw className="w-3 h-3 animate-spin text-[#25F4EE]" /> กำลังตรวจสอบ...
                    </span>
                  )}
                </div>

                {vaultInfo?.has_vault ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    <div className="p-3 rounded-xl bg-slate-900/70 border border-white/[0.06]">
                      <div className="text-[10px] text-slate-400">คลิปทั้งหมดบน SSD</div>
                      <div className="text-lg font-bold text-white font-mono">{vaultInfo.total_items} คลิป</div>
                    </div>
                    <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30">
                      <div className="text-[10px] text-emerald-300">โพสต์สำเร็จจากคาเฟ่แล้ว</div>
                      <div className="text-lg font-bold text-emerald-400 font-mono">{vaultInfo.posted_count} คลิป</div>
                    </div>
                    <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-500/30 col-span-2 sm:col-span-1">
                      <div className="text-[10px] text-amber-300">ยังไม่ได้โพสต์ (ค้างอยู่)</div>
                      <div className="text-lg font-bold text-amber-400 font-mono">{vaultInfo.pending_count} คลิป</div>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-xl bg-slate-900/40 text-xs text-slate-400 text-center border border-dashed border-white/[0.1]">
                    ไม่พบโฟลเดอร์ Vault บนไดรฟ์ที่เลือก กรุณาตรวจสอบว่าเสียบ SSD ถูกไดรฟ์หรือไม่
                  </div>
                )}

                {/* SSD Retention Policy Radio Options */}
                <div className="pt-2 space-y-2">
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Archive className="w-3.5 h-3.5 text-cyan-400" />
                    <span>นโยบายจัดการไฟล์บน External SSD หลังซิงค์:</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div
                      onClick={() => setRetentionMode('archive')}
                      className={`p-3 rounded-xl border transition-all cursor-pointer select-none ${
                        retentionMode === 'archive'
                          ? 'bg-cyan-500/10 border-cyan-400/50 shadow-sm ring-1 ring-cyan-400/30'
                          : 'bg-black/30 border-white/[0.08] hover:border-white/[0.2]'
                      }`}
                    >
                      <div className="text-xs font-bold text-white flex items-center gap-1.5">
                        <Archive className="w-3.5 h-3.5 text-cyan-400" />
                        <span>ย้ายเข้า Posted_Archive</span>
                      </div>
                      <div className="text-[10px] text-slate-400 pt-1 leading-normal">
                        (แนะนำ) เก็บสำรองถาวรบน SSD ในโฟลเดอร์แยก เป็นระเบียบ ไม่ปนกับคลิปใหม่
                      </div>
                    </div>

                    <div
                      onClick={() => setRetentionMode('delete')}
                      className={`p-3 rounded-xl border transition-all cursor-pointer select-none ${
                        retentionMode === 'delete'
                          ? 'bg-red-500/10 border-red-400/50 shadow-sm ring-1 ring-red-400/30'
                          : 'bg-black/30 border-white/[0.08] hover:border-white/[0.2]'
                      }`}
                    >
                      <div className="text-xs font-bold text-white flex items-center gap-1.5">
                        <Trash2 className="w-3.5 h-3.5 text-red-400" />
                        <span>ลบไฟล์บน SSD ทันที</span>
                      </div>
                      <div className="text-[10px] text-slate-400 pt-1 leading-normal">
                        ล้างไฟล์คลิปบน SSD เพื่อประหยัดพื้นที่ความจุ เตรียมพร้อมรอบใหม่
                      </div>
                    </div>

                    <div
                      onClick={() => setRetentionMode('keep')}
                      className={`p-3 rounded-xl border transition-all cursor-pointer select-none ${
                        retentionMode === 'keep'
                          ? 'bg-amber-500/10 border-amber-400/50 shadow-sm ring-1 ring-amber-400/30'
                          : 'bg-black/30 border-white/[0.08] hover:border-white/[0.2]'
                      }`}
                    >
                      <div className="text-xs font-bold text-white flex items-center gap-1.5">
                        <FolderCheck className="w-3.5 h-3.5 text-amber-400" />
                        <span>คงไฟล์เดิมไว้</span>
                      </div>
                      <div className="text-[10px] text-slate-400 pt-1 leading-normal">
                        ปล่อยไฟล์ไว้ที่เดิมใน media/videos/ ไม่ลบและไม่ย้าย
                      </div>
                    </div>
                  </div>
                </div>

                {/* Reconcile Button */}
                <div className="pt-2">
                  <Button
                    onClick={handleStartReconcile}
                    disabled={!selectedDrive || reconciling || !vaultInfo?.has_vault}
                    variant="primary"
                    size="md"
                    className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-black font-bold py-2.5 rounded-xl shadow-lg shadow-cyan-500/20 cursor-pointer flex items-center justify-center gap-2"
                  >
                    {reconciling ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-black" />
                    ) : (
                      <FolderCheck className="w-4 h-4 text-black" />
                    )}
                    <span>{reconciling ? 'กำลังซิงค์และอัปเดตระบบ...' : 'ซิงค์สถานะและย้ายคลิปเข้า Posted ทันที'}</span>
                  </Button>
                </div>

                {/* Reconcile Success Box */}
                {reconcileSuccess && (
                  <div className="p-4 rounded-2xl bg-cyan-950/60 border border-cyan-400/50 space-y-2">
                    <div className="flex items-center gap-2 text-cyan-300 font-bold text-sm">
                      <CheckCircle2 className="w-5 h-5 text-cyan-400" />
                      <span>ซิงค์สถานะกลับเครื่องหลักเรียบร้อยสมบูรณ์!</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs pt-1 text-slate-200">
                      <div className="p-2 rounded-lg bg-black/40">
                        <span className="text-slate-400 block text-[10px]">อัปเดตเป็น Posted</span>
                        <span className="font-bold text-emerald-400 text-sm">{reconcileSuccess.reconciledCount} คลิป</span>
                      </div>
                      <div className="p-2 rounded-lg bg-black/40">
                        <span className="text-slate-400 block text-[10px]">ค้างยังไม่โพสต์</span>
                        <span className="font-bold text-amber-300 text-sm">{reconcileSuccess.pendingUnpostedCount} คลิป</span>
                      </div>
                      <div className="p-2 rounded-lg bg-black/40">
                        <span className="text-slate-400 block text-[10px]">ย้ายเข้า Archive</span>
                        <span className="font-bold text-cyan-400 text-sm">{reconcileSuccess.archivedCount || 0} ไฟล์</span>
                      </div>
                      <div className="p-2 rounded-lg bg-black/40">
                        <span className="text-slate-400 block text-[10px]">ลบจาก SSD</span>
                        <span className="font-bold text-slate-400 text-sm">{reconcileSuccess.cleanedCount || 0} ไฟล์</span>
                      </div>
                    </div>
                    {reconcileSuccess.pendingUnpostedCount > 0 && (
                      <div className="text-[11px] text-amber-300 bg-amber-950/40 p-2 rounded-lg border border-amber-500/30">
                        💡 <strong>บันทึกความปลอดภัย:</strong> ยังมีคลิปอีก {reconcileSuccess.pendingUnpostedCount} คลิปที่ยังไม่ได้โพสต์ ระบบจะคงไว้ในคิวพร้อมให้คุณส่งออกไปโพสต์ในรอบหน้าได้ทันทีครับ
                      </div>
                    )}
                    <div className="text-[11px] text-slate-300 pt-1">
                      📁 ไฟล์วิดีโอบนเครื่องหลักถูกย้ายไปยังโฟลเดอร์ <code className="text-cyan-300 font-mono">04_Exports/Posted/</code> เรียบร้อยแล้วครับ
                    </div>
                  </div>
                )}

                {/* Error Box */}
                {reconcileError && (
                  <div className="p-3 rounded-xl bg-red-950/50 border border-red-500/40 text-xs text-red-200 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                    <span>{reconcileError}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: CAFE GUIDE */}
          {activeTab === 'guide' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-500/30 flex items-start gap-3">
                <Coffee className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-amber-200">
                    ขั้นตอนเมื่อไปถึงคาเฟ่ (โน้ตบุ๊ก + เน็ตแรง)
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    เมื่อคุณอยู่ที่คาเฟ่หรือ Co-working space ไม่ต้องติดตั้งโปรแกรมตัดต่อหรือโมเดล AI ใด ๆ บนโน้ตบุ๊กเลย แค่ทำตาม 3 ขั้นตอนนี้:
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3">
                {/* Step 1 */}
                <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-amber-500/20 text-amber-300 font-bold flex items-center justify-center flex-shrink-0 text-xs">
                    1
                  </div>
                  <div className="space-y-1">
                    <h5 className="text-xs font-bold text-white">เสียบ External SSD เข้ากับโน้ตบุ๊ก</h5>
                    <p className="text-xs text-slate-400">
                      เชื่อมต่อ Wi-Fi คาเฟ่ที่มีความเร็วสูง (Upload Gigabit / 5G)
                    </p>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-amber-500/20 text-amber-300 font-bold flex items-center justify-center flex-shrink-0 text-xs">
                    2
                  </div>
                  <div className="space-y-1">
                    <h5 className="text-xs font-bold text-white">ดับเบิลคลิกไฟล์ START_CAFE_UPLOADER.bat</h5>
                    <p className="text-xs text-slate-400">
                      เข้าไปที่ไดรฟ์ SSD ➡️ โฟลเดอร์ <code className="text-emerald-300 font-mono">OmniCut_Portable_Vault/</code> ➡️ ดับเบิลคลิกไฟล์ <code className="text-emerald-300 font-mono">START_CAFE_UPLOADER.bat</code>
                    </p>
                    <p className="text-[11px] text-slate-500">
                      * สคริปต์จะค้นหาทั้ง Portable Embedded Python บน SSD และ System Python ในเครื่อง จากนั้นเปิดหน้าต่างเซิร์ฟเวอร์จิ๋ว และเปิดหน้า TikTok Studio ใน Chrome ให้อัตโนมัติใน 1 วินาที
                    </p>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-amber-500/20 text-amber-300 font-bold flex items-center justify-center flex-shrink-0 text-xs">
                    3
                  </div>
                  <div className="space-y-1">
                    <h5 className="text-xs font-bold text-white">เปิด Chrome Extension แล้วกดปุ่มโพสต์</h5>
                    <p className="text-xs text-slate-400">
                      เปิดแถบข้างของส่วนขยาย <strong>OmniCut TikTok Post Helper</strong> ทางขวามือ รายการคลิปพร้อมปก แคปชัน และตะกร้าสินค้าจะโผล่ขึ้นมาทันที กดปุ่มโพสต์ทีละคลิปได้เลย!
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-white/[0.08] bg-black/50 flex items-center justify-between relative z-10">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Zero-Command Interface: ทุกขั้นตอนจัดการผ่านการกดปุ่ม 100%</span>
          </div>
          <Button onClick={onClose} variant="secondary" size="sm" className="px-4 py-1.5 rounded-xl cursor-pointer">
            ปิดหน้าต่าง
          </Button>
        </div>
      </div>
    </div>
  );
}
