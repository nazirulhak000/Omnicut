import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  HardDrive, Folder, Trash2, RefreshCw, AlertTriangle,
  FolderOpen, CheckCircle2, ShieldCheck, Info,
  Archive, FolderArchive, ChevronDown, ChevronUp, FileVideo, FileCode
} from 'lucide-react';
import { getStorageAnalytics, purgeSafeStorageCache, openFolder } from '../../../api';
import MetricKpiCard from '../components/MetricKpiCard';
import LoadingSpinner from '../../LoadingSpinner';
import { ConfirmModal } from '../../ui';
import DonutChart from '../charts/DonutChart';
import PaginationControls from '../../PaginationControls';

export default function StorageAnalyticsTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [purging, setPurging] = useState(false);
  const [showPurgeModal, setShowPurgeModal] = useState(false);
  const [showArchiveDetail, setShowArchiveDetail] = useState(false);
  const [archivePage, setArchivePage] = useState(1);
  const [archivePageSize, setArchivePageSize] = useState(10);
  const [purgeResult, setPurgeResult] = useState(null);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async (forceScan = false) => {
    if (forceScan) setScanning(true);
    else setLoading(true);
    setError(null);
    try {
      const res = await getStorageAnalytics(forceScan);
      setData(res);
    } catch (err) {
      console.error('Failed to load storage analytics:', err);
      setError('ไม่สามารถโหลดข้อมูลสถิติพื้นที่จัดเก็บได้');
    } finally {
      setLoading(false);
      setScanning(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const {
    drive = {},
    directories = [],
    capcut_draft_gb = 0,
    safe_purge_mb = 0,
    safe_purge_items = [],
    heavy_products = [],
    posted_archive_potential = {},
    archive_recommendation = {}
  } = data || {};
  const totalFolderBytes = directories.reduce((acc, d) => acc + (d.size_bytes || 0), 0);
  const totalFolderGb = (totalFolderBytes / (1024 ** 3)).toFixed(2);
  const archiveItems = posted_archive_potential.items || [];
  const visibleArchiveItems = useMemo(
    () => archiveItems.slice((archivePage - 1) * archivePageSize, archivePage * archivePageSize),
    [archiveItems, archivePage, archivePageSize]
  );
  useEffect(() => {
    setArchivePage(1);
  }, [data]);
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(archiveItems.length / archivePageSize));
    setArchivePage((page) => Math.min(page, totalPages));
  }, [archiveItems.length, archivePageSize]);
  const archiveCandidateBytes = posted_archive_potential.archive_candidate_bytes ?? posted_archive_potential.total_reclaimable_bytes ?? 0;
  const archiveCandidateMb = posted_archive_potential.archive_candidate_mb ?? posted_archive_potential.total_reclaimable_mb ?? 0;
  const archiveCandidateGb = posted_archive_potential.archive_candidate_gb ?? posted_archive_potential.total_reclaimable_gb ?? 0;

  const folderChartData = useMemo(() => {
    const COLOR_MAP = {
      '00_Inbox': '#94A3B8',
      '01_Raw': '#25F4EE',
      '02_Assets': '#3B82F6',
      '03_Projects': '#8B5CF6',
      '04_Exports': '#10B981',
      '05_Covers_Thumbnails': '#F59E0B',
      '06_Archive': '#64748B',
    };
    return directories
      .filter((d) => (d.size_bytes || 0) > 0)
      .map((d) => ({
        label: d.name,
        value: d.size_mb || 0,
        color: COLOR_MAP[d.name] || '#A855F7',
      }));
  }, [directories]);

  const handlePurge = async () => {
    setPurging(true);
    try {
      const res = await purgeSafeStorageCache();
      setPurgeResult(res);
      setShowPurgeModal(false);
      fetchData(true);
    } catch (err) {
      console.error('Purge error:', err);
      alert('เกิดข้อผิดพลาดในการล้างไฟล์แคช: ' + err.message);
    } finally {
      setPurging(false);
    }
  };

  if (loading && !scanning) {
    return <LoadingSpinner message="กำลังสแกนและคำนวณขนาดพื้นที่จัดเก็บ..." />;
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" />
        <p className="text-sm text-slate-300">{error || 'ไม่พบข้อมูล'}</p>
        <button
          onClick={() => fetchData(true)}
          className="px-4 py-2 rounded-xl bg-white/[0.08] hover:bg-white/[0.12] text-xs font-bold text-white transition-all cursor-pointer inline-flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>สแกนพื้นที่ใหม่อีกครั้ง</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── 4 Top KPI Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricKpiCard
          title="พื้นที่โปรเจกต์ทั้งหมด"
          value={`${totalFolderGb} GB`}
          subtitle={`รวม 6 โฟลเดอร์หลักในโปรเจกต์`}
          icon={HardDrive}
          accentColor="text-purple-400"
          borderColor="border-purple-500/20"
          bgColor="bg-purple-500/[0.03]"
        />
        <MetricKpiCard
          title="ความจุไดรฟ์ที่ใช้งาน"
          value={`${drive.used_percentage}%`}
          subtitle={`ว่างเหลือ ${(drive.free_bytes / (1024 ** 3)).toFixed(1)} GB จาก ${(drive.total_bytes / (1024 ** 3)).toFixed(0)} GB`}
          icon={HardDrive}
          accentColor={drive.used_percentage > 85 ? 'text-rose-400' : 'text-blue-400'}
          borderColor={drive.used_percentage > 85 ? 'border-rose-500/30' : 'border-blue-500/20'}
          bgColor="bg-blue-500/[0.03]"
          badge={drive.used_percentage > 85 ? 'ดิสก์ใกล้เต็ม' : 'ปกติ'}
          badgeColor={drive.used_percentage > 85 ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}
        />
        <MetricKpiCard
          title="ดราฟต์แคช CapCut"
          value={`${capcut_draft_gb} GB`}
          subtitle="ไฟล์งานและพรีวิวใน CapCut PC"
          icon={Folder}
          accentColor="text-amber-400"
          borderColor="border-amber-500/20"
          bgColor="bg-amber-500/[0.03]"
        />
        <MetricKpiCard
          title="ไฟล์แคชที่ล้างได้ปลอดภัย"
          value={`${safe_purge_mb} MB`}
          subtitle="Temp render & audio cache ชั่วคราว"
          icon={ShieldCheck}
          accentColor="text-emerald-400"
          borderColor="border-emerald-500/20"
          bgColor="bg-emerald-500/[0.03]"
          badge="ปลอดภัย 100%"
          badgeColor="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
        />
      </div>

      {/* ── Purge Success Alert ── */}
      {purgeResult && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-emerald-200 text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{purgeResult.message}</span>
          </div>
          <button
            onClick={() => setPurgeResult(null)}
            className="text-xs text-slate-400 hover:text-white"
          >
            ปิด
          </button>
        </div>
      )}

      {/* ── Action Toolbar: Rescan & Safe Purge ── */}
      <div className="p-4 rounded-2xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Info className="w-4 h-4 text-slate-500" />
          <span>ระบบแคชสถิติไว้ 5 นาทีเพื่อป้องกันดิสก์ทำงานหนัก สแกนล่าสุดเมื่อ: {new Date(data.last_scanned_at).toLocaleTimeString('th-TH')}</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchData(true)}
            disabled={scanning}
            className="px-3 py-1.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-xs font-bold text-slate-200 transition-all cursor-pointer flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
            <span>{scanning ? 'กำลังสแกน...' : 'สแกนพื้นที่ใหม่'}</span>
          </button>

          {safe_purge_mb > 0 && (
            <button
              onClick={() => setShowPurgeModal(true)}
              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-purple-500/20 to-pink-500/20 hover:from-purple-500/30 hover:to-pink-500/30 border border-purple-500/30 text-purple-200 text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5 text-purple-400" />
              <span>ล้างไฟล์แคช ({safe_purge_mb} MB)</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Archive Recommendation Banner (age-based + disk threshold) ── */}
      {archive_recommendation.should_notify && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3 text-amber-100">
          <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
          <div className="text-xs space-y-0.5">
            <p className="font-bold text-amber-200">แนะนำย้ายไฟล์ออกไปสำรอง</p>
            <p className="text-amber-100/90">{archive_recommendation.message}</p>
          </div>
        </div>
      )}

      {/* ── Posted Clips Archive & Backup Potential ── */}
      <div className="p-5 sm:p-6 rounded-3xl bg-gradient-to-br from-[#0B0F19]/90 via-[#071324]/80 to-[#0F1424]/90 border border-cyan-500/25 shadow-xl shadow-cyan-950/20 backdrop-blur-xl space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-[#25F4EE]">
                <Archive className="w-4 h-4" />
              </div>
              <h3 className="text-sm sm:text-base font-bold text-white">
                คลิปที่โพสต์แล้ว & โอกาสประหยัดพื้นที่คอม (Posted Clips Archive)
              </h3>
            </div>
            <p className="text-xs text-slate-300">
              ตัวเลขนี้เป็นขนาดไฟล์ที่เข้าเกณฑ์สำหรับย้ายไปสำรอง (Backup) บน External Drive หรือ Cloud ไม่ใช่ไฟล์ที่ระบบลบได้ทันที
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => openFolder('04_Exports/Posted')}
              className="px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-xs font-semibold text-slate-300 hover:text-white transition-all cursor-pointer inline-flex items-center gap-1.5"
            >
              <FolderOpen className="w-3.5 h-3.5" />
              <span>เปิด 04_Exports/Posted</span>
            </button>
            <button
              type="button"
              onClick={() => setShowArchiveDetail(!showArchiveDetail)}
              className="px-3 py-1.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-[#25F4EE] text-xs font-bold transition-all cursor-pointer inline-flex items-center gap-1.5 active:scale-95"
            >
              <FolderArchive className="w-3.5 h-3.5" />
              <span>{showArchiveDetail ? 'ซ่อนรายการ' : `ดูรายการ (${posted_archive_potential.items_count || 0} รายการ)`}</span>
              {showArchiveDetail ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* 3 Metrics Mini Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div className="p-3.5 rounded-2xl bg-black/30 border border-white/[0.06] space-y-1">
            <span className="text-[11px] font-bold text-slate-400">จำนวนคลิปที่โพสต์แล้ว</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-[#25F4EE]">
                {posted_archive_potential.posted_clips_count || 0}
              </span>
              <span className="text-xs text-slate-400">คลิป ({posted_archive_potential.posted_angles_count || 0} มุมมอง)</span>
            </div>
            <p className="text-[10px] text-slate-400">อยู่ใน 04_Exports/Posted/ และ ProductStore</p>
          </div>

          <div className="p-3.5 rounded-2xl bg-black/30 border border-white/[0.06] space-y-1">
            <span className="text-[11px] font-bold text-slate-400">ขนาดที่เข้าเกณฑ์ย้ายสำรอง</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-emerald-400">
                {archiveCandidateMb >= 1024
                  ? `${archiveCandidateGb} GB`
                  : `${archiveCandidateMb} MB`}
              </span>
              <span className="text-xs text-emerald-400/80">ต้อง Backup ก่อน reclaim</span>
            </div>
            <p className="text-[10px] text-slate-400">รวมวิดีโอส่งออก + ดราฟต์โปรเจกต์งานตัด</p>
          </div>

          <div className="p-3.5 rounded-2xl bg-black/30 border border-white/[0.06] space-y-1">
            <span className="text-[11px] font-bold text-slate-400">สัดส่วนที่ลดได้จากโปรเจกต์</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-purple-400">
                {totalFolderBytes ? Math.round((archiveCandidateBytes / totalFolderBytes) * 100) : 0}%
              </span>
              <span className="text-xs text-purple-400/80">ของพื้นที่โปรเจกต์</span>
            </div>
            <p className="text-[10px] text-slate-400">เป็น archive candidate estimate ไม่ใช่ safe-delete</p>
          </div>
        </div>

        {/* Breakdown Badges */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
          <span className="text-slate-400 font-bold">รายละเอียดที่พร้อมย้าย:</span>
          <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-slate-200">
            วิดีโอส่งออก MP4: <strong className="text-white font-semibold">{posted_archive_potential.posted_exports_mb || 0} MB</strong> ({posted_archive_potential.posted_clips_count || 0} ไฟล์)
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-slate-200">
            โฟลเดอร์ดราฟต์โปรเจกต์: <strong className="text-white font-semibold">{posted_archive_potential.posted_projects_mb || 0} MB</strong> ({posted_archive_potential.posted_projects_count || 0} โปรเจกต์)
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-slate-200">
            วัตถุดิบที่ครบทุกมุมโพสต์: <strong className="text-white font-semibold">{posted_archive_potential.completed_products_raw_mb || 0} MB</strong> ({posted_archive_potential.completed_products_raw_count || 0} โฟลเดอร์)
          </span>
        </div>

        {/* Collapsible Details Table */}
        {showArchiveDetail && (
          <div className="pt-3 border-t border-white/[0.08] space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="text-xs font-bold text-slate-200">
                รายการไฟล์และโปรเจกต์ที่พร้อมย้ายสำรอง ({archiveItems.length} รายการ)
              </div>
              <div className="text-[11px] text-slate-400">
                สามารถย้ายไป External Drive โดยประวัติสถิติและยอดวิวยังคงอยู่ครบ
              </div>
            </div>

            <div className="overflow-hidden rounded-2xl border border-white/[0.08] bg-black/40">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-[#0B0F19] border-b border-white/[0.08] text-slate-400 font-semibold z-10">
                  <tr>
                    <th className="py-2.5 px-3">ประเภท</th>
                    <th className="py-2.5 px-3">ชื่อไฟล์ / โปรเจกต์</th>
                    <th className="py-2.5 px-3 text-right">ขนาดพื้นที่</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {visibleArchiveItems.map((item, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-2 px-3 whitespace-nowrap">
                        {item.type === 'export_mp4' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[10px] font-bold">
                            <FileVideo className="w-3 h-3" />
                            <span>วิดีโอ MP4</span>
                          </span>
                        ) : item.type === 'raw_source' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[10px] font-bold">
                            <FolderArchive className="w-3 h-3" />
                            <span>วัตถุดิบที่เข้าเกณฑ์ Archive</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-300 border border-purple-500/20 text-[10px] font-bold">
                            <FileCode className="w-3 h-3" />
                            <span>ดราฟต์โปรเจกต์</span>
                          </span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-slate-200 truncate max-w-[360px]">
                        <div className="truncate font-semibold">{item.name}</div>
                        {item.product_name && (
                          <div className="text-[10px] text-slate-500 truncate font-sans">{item.product_name}</div>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right text-white font-bold whitespace-nowrap">
                        {item.size_mb} MB
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <PaginationControls
                page={archivePage}
                pageSize={archivePageSize}
                totalItems={archiveItems.length}
                onPageChange={setArchivePage}
                onPageSizeChange={(size) => {
                  setArchivePageSize(size);
                  setArchivePage(1);
                }}
                itemLabel="รายการ Archive"
                disabled={scanning}
              />
            </div>

            <div className="p-3 rounded-xl bg-cyan-500/[0.06] border border-cyan-500/20 text-xs text-slate-300 space-y-1">
              <div className="font-bold text-cyan-300 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5" />
                <span>คำแนะนำการย้ายและสำรองข้อมูล (Archive & Backup Strategy)</span>
              </div>
              <p className="text-[11px] text-slate-400">
                เมื่อย้ายไฟล์ MP4 ใน <code className="text-slate-300">04_Exports/Posted/</code> และโฟลเดอร์ใน <code className="text-slate-300">03_Projects/</code> ไปไว้บน External Drive หรือ Cloud Storage แล้วตรวจสอบ Backup เรียบร้อย จึงค่อย reclaim พื้นที่ โดยฐานข้อมูลสถิติ ยอดวิว และผลวิเคราะห์ใน OmniCut Pro Studio จะยังคงอยู่ครบ 100% ไม่สูญหาย
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Directory Storage Breakdown & Donut Chart ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Donut Chart of storage distribution */}
        <div className="p-5 sm:p-6 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4 flex flex-col justify-between">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-white">แผนภาพสัดส่วนพื้นที่ (Storage Share)</h3>
            <p className="text-xs text-slate-400">การกระจายขนาดพื้นที่ตามโครงสร้างโฟลเดอร์</p>
          </div>

          <div className="pt-2 flex-1 flex flex-col items-center justify-center">
            {folderChartData.length === 0 ? (
              <div className="text-xs text-slate-500 py-6 text-center">ยังไม่มีข้อมูลขนาดโฟลเดอร์</div>
            ) : (
              <DonutChart
                data={folderChartData}
                size={135}
                strokeWidth={18}
                centerLabel="พื้นที่รวม"
                centerValue={`${totalFolderGb} GB`}
                unit=""
                legendLayout="vertical"
                maxSlices={6}
              />
            )}
          </div>
        </div>

        {/* Right Col: Directory Cards */}
        <div className="lg:col-span-2 p-5 sm:p-6 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-white">รายละเอียดโฟลเดอร์ระบบ (00_Inbox - 06_Archive)</h3>
              <p className="text-xs text-slate-400">ขนาดความจุและทางลัดเปิดโฟลเดอร์ใน Windows Explorer</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {directories.map((dir, idx) => {
              const pct = totalFolderBytes ? Math.round((dir.size_bytes / totalFolderBytes) * 100) : 0;
              return (
                <div key={idx} className="p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2 hover:border-white/[0.12] transition-colors">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-200">
                    <span className="truncate">{dir.name}</span>
                    <span className="text-purple-400 font-semibold">{pct}%</span>
                  </div>
                  <div className="flex items-baseline justify-between text-xs">
                    <span className="text-base font-bold text-white">
                      {dir.size_gb >= 1 ? `${dir.size_gb} GB` : `${dir.size_mb} MB`}
                    </span>
                    <button
                      onClick={() => openFolder(dir.folder)}
                      className="p-1 rounded bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white transition-all cursor-pointer"
                      title={`เปิดโฟลเดอร์ ${dir.folder} ใน Explorer`}
                    >
                      <FolderOpen className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all"
                      style={{ width: `${Math.max(4, pct)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Top Heaviest Product Folders in 01_Raw ── */}
      <div className="p-5 rounded-3xl bg-[#0D111A]/80 border border-white/[0.08] backdrop-blur-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-white">โฟลเดอร์วัตถุดิบสินค้าที่ใช้พื้นที่มากที่สุด (Top Heavy Raw)</h3>
            <p className="text-xs text-slate-400">10 อันดับโฟลเดอร์ใน 01_Raw ที่มีไฟล์วิดีโอและรูปภาพขนาดใหญ่</p>
          </div>
          <button
            onClick={() => openFolder('01_Raw')}
            className="px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-xs font-semibold text-slate-300 hover:text-white transition-all cursor-pointer inline-flex items-center gap-1.5"
          >
            <FolderOpen className="w-3.5 h-3.5" />
            <span>เปิด 01_Raw</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-400 font-semibold">
                <th className="py-2.5 px-3">ชื่อโฟลเดอร์สินค้า</th>
                <th className="py-2.5 px-3 text-right">ขนาดพื้นที่</th>
                <th className="py-2.5 px-3 text-right">การจัดการ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {heavy_products.length === 0 && (
                <tr>
                  <td colSpan={3} className="py-8 text-center text-slate-500">
                    ยังไม่มีข้อมูลโฟลเดอร์สินค้า
                  </td>
                </tr>
              )}
              {heavy_products.map((item, idx) => (
                <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-2.5 px-3 font-semibold text-white truncate max-w-[280px]">
                    {item.name}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-200">
                    {item.size_mb > 1024
                      ? `${(item.size_mb / 1024).toFixed(2)} GB`
                      : `${item.size_mb} MB`}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => openFolder(`01_Raw/${item.name}`)}
                      className="px-2.5 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-[11px] font-semibold transition-all cursor-pointer inline-flex items-center gap-1"
                    >
                      <FolderOpen className="w-3 h-3 text-purple-400" />
                      <span>เปิดโฟลเดอร์</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Purge Confirmation Modal ── */}
      <ConfirmModal
        isOpen={showPurgeModal}
        title="ยืนยันการล้างไฟล์แคชชั่วคราว"
        message={`ระบบจะล้างเฉพาะไฟล์ชั่วคราวที่สร้างขึ้นใหม่ได้ รวมประมาณ ${safe_purge_mb} MB${safe_purge_items && safe_purge_items.length > 0 ? `:\n\n` + safe_purge_items.map(item => `• ${item.label}: ${item.mb} MB (${item.count} ไฟล์)`).join('\n') : ''}\n\nการกระทำนี้ปลอดภัย 100% และจะไม่แตะต้องไฟล์วัตถุดิบต้นฉบับใน 01_Raw และ 02_Assets เด็ดขาด`}
        confirmLabel={purging ? 'กำลังล้าง...' : 'ยืนยันล้างไฟล์แคช'}
        cancelLabel="ยกเลิก"
        onConfirm={handlePurge}
        onCancel={() => setShowPurgeModal(false)}
        variant="warning"
      />
    </div>
  );
}
