import React, { useState, useEffect, useRef } from 'react';
import {
  Settings, Folder, HardDrive, CheckCircle2, Sliders, Type,
  Sparkles, RefreshCw, Smartphone, ShieldCheck, Cpu, Layers,
  BarChart3, Columns, List, ChevronRight, AlertTriangle, Bug, Trash2,
  Download, Archive, Copy, Loader2, Database
} from 'lucide-react';
import {
  openFolder,
  createSystemBackup,
  getSystemBackups,
  deleteSystemBackup,
  scanAssetDuplicates,
  cleanAssetDuplicates,
} from '../api';
import { PageHeader } from './ui';

export default function SystemSettings({
  status,
  uiFont = 'font-prompt',
  setUiFont,
  uiScale = 'normal',
  setUiScale,
  initialSubTab = 'appearance'
}) {
  const [activeTab, setActiveTab] = useState(initialSubTab); // 'appearance' | 'paths' | 'engine'
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'classic'

  // Round POST-2: TikTok auto-post extension toggle -- off by default, per
  // TIKTOK_AUTOPOST_PLAN.md Gate §4 ("ปิดไว้เป็นค่าเริ่มต้น เปิดผ่าน toggle นี้เท่านั้น").
  const [autopostEnabled, setAutopostEnabled] = useState(() => {
    try {
      return localStorage.getItem('omnicut_tiktok_autopost_enabled') === 'true';
    } catch {
      return false;
    }
  });
  const toggleAutopost = () => {
    setAutopostEnabled((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('omnicut_tiktok_autopost_enabled', next ? 'true' : 'false');
      } catch {}
      return next;
    });
  };

  const [backups, setBackups] = useState([]);
  const [backupLoading, setBackupLoading] = useState(false);
  const [backupMessage, setBackupMessage] = useState(null);
  const [dedupLoading, setDedupLoading] = useState(false);
  const [dedupResult, setDedupResult] = useState(null);
  // A raw-footage-heavy library can turn up hundreds of duplicate groups --
  // window the results list the same way the other galleries in this round
  // were, resetting on every fresh scan.
  const DEDUP_PAGE_SIZE = 30;
  const [dedupVisibleCount, setDedupVisibleCount] = useState(DEDUP_PAGE_SIZE);
  const [cleanLoading, setCleanLoading] = useState(false);
  const [cleanMessage, setCleanMessage] = useState(null);

  const fetchBackups = async () => {
    try {
      const res = await getSystemBackups();
      if (res.status === 'ok') setBackups(res.backups || []);
    } catch (err) {
      console.error('Failed to load backups', err);
    }
  };

  useEffect(() => {
    if (activeTab === 'maintenance') {
      fetchBackups();
    }
  }, [activeTab]);

  const handleCreateBackup = async () => {
    setBackupLoading(true);
    setBackupMessage(null);
    try {
      const res = await createSystemBackup();
      if (res.status === 'ok') {
        setBackupMessage({ type: 'success', text: `สำรองข้อมูลสำเร็จ: ${res.backup.backup_name} (${res.backup.size_mb} MB)` });
        fetchBackups();
      }
    } catch (err) {
      setBackupMessage({ type: 'error', text: `สำรองข้อมูลล้มเหลว: ${err?.response?.data?.detail || err.message}` });
    } finally {
      setBackupLoading(false);
    }
  };

  const handleDeleteBackup = async (filename) => {
    if (!window.confirm(`ยืนยันการลบไฟล์สำรอง ${filename}?`)) return;
    try {
      await deleteSystemBackup(filename);
      fetchBackups();
    } catch (err) {
      alert(`ลบล้มเหลว: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const handleScanDedup = async () => {
    setDedupLoading(true);
    setCleanMessage(null);
    try {
      const res = await scanAssetDuplicates();
      if (res.status === 'ok') {
        setDedupResult(res);
        setDedupVisibleCount(DEDUP_PAGE_SIZE);
      }
    } catch (err) {
      setCleanMessage({ type: 'error', text: `สแกนล้มเหลว: ${err?.response?.data?.detail || err.message}` });
    } finally {
      setDedupLoading(false);
    }
  };

  const handleCleanDedup = async () => {
    if (!dedupResult || !dedupResult.groups?.length) return;
    const allDups = dedupResult.groups.flatMap(g => g.duplicates.map(d => d.full_path));
    if (!window.confirm(`ยืนยันย้ายไฟล์ซ้ำ ${allDups.length} ไฟล์ เข้าถังขยะ (.trash) เพื่อคืนพื้นที่ ${dedupResult.reclaimable_mb} MB?`)) return;
    setCleanLoading(true);
    try {
      const res = await cleanAssetDuplicates(allDups, true);
      setCleanMessage({ type: 'success', text: `ย้ายไฟล์ซ้ำสำเร็จ ${res.cleaned_count} ไฟล์ (คืนพื้นที่ ${res.freed_mb} MB)` });
      handleScanDedup();
    } catch (err) {
      setCleanMessage({ type: 'error', text: `ทำความสะอาดล้มเหลว: ${err?.response?.data?.detail || err.message}` });
    } finally {
      setCleanLoading(false);
    }
  };

  const handleOpen = (target) => {
    openFolder(target);
  };

  const settingSections = [
    {
      id: 'appearance',
      name: 'การแสดงผล & ฟอนต์',
      desc: 'ปรับสเกลหน้าจอ (UI Scale) และเลือกฟอนต์ระบบภาษาไทย 10 แบบ',
      icon: Sliders,
      color: 'text-purple-400',
      badge: 'Appearance',
      badgeColor: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    },
    {
      id: 'paths',
      name: 'โฟลเดอร์ & ที่จัดเก็บ',
      desc: 'เข้าถึงโฟลเดอร์ไฟล์ดิบ, Assets, Projects และ CapCut PC',
      icon: Folder,
      color: 'text-amber-400',
      badge: 'Storage',
      badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    },
    {
      id: 'engine',
      name: 'สถานะ AI & ระบบ',
      desc: 'ตรวจสอบ FFmpeg, Gemini Flash Engine และการเชื่อมโยง CapCut Draft',
      icon: Cpu,
      color: 'text-emerald-400',
      badge: 'System Core',
      badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    },
    {
      id: 'maintenance',
      name: 'สำรองข้อมูล & ไฟล์ซ้ำ',
      desc: 'One-Click Backup สำรองฐานข้อมูล และสแกนลบไฟล์ซ้ำ (Asset Dedup) คืนพื้นที่ดิสก์',
      icon: HardDrive,
      color: 'text-cyan-400',
      badge: 'Maintenance',
      badgeColor: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    },
  ];

  const currentSection = settingSections.find(s => s.id === activeTab) || settingSections[0];

  const projectFolders = [
    { id: 'inbox', label: '00_Inbox (ไฟล์ดิบจากมือถือ)', icon: Smartphone, color: 'text-[#25F4EE]' },
    { id: 'raw', label: '01_Raw (ฟุตเทจต้นฉบับแยกสินค้า)', icon: Folder, color: 'text-blue-400' },
    { id: 'assets', label: '02_Assets (มีเดียส่วนกลาง)', icon: Layers, color: 'text-purple-400' },
    { id: 'projects', label: '03_Projects (ไฟล์โปรเจกต์/ดราฟต์)', icon: Folder, color: 'text-amber-400' },
    { id: 'exports', label: '04_Exports (วิดีโอที่ตัดเสร็จ)', icon: CheckCircle2, color: 'text-emerald-400' },
    { id: 'capcut', label: 'CapCut Drafts (โฟลเดอร์ CapCut PC)', icon: HardDrive, color: 'text-pink-400' },
  ];

  // ── Render Specific Section Workbench Content ──
  const renderWorkbenchContent = () => {
    switch (activeTab) {
      case 'appearance':
        return (
          <div className="space-y-4 sm:space-y-5 animate-fadeIn">
            {/* Section 1: UI Scale Control */}
            <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg space-y-3.5">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-[#25F4EE] flex-shrink-0">
                  <Sliders className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm sm:text-base font-bold text-white">
                    ขนาดการแสดงผล (UI Scale)
                  </h3>
                  <p className="text-xs text-slate-400">
                    ปรับอัตราส่วนตัวหนังสือและปุ่มให้พอดีสายตา เหมาะกับขนาดหน้าจอของคุณ
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
                {[
                  { id: 'compact', label: 'กะทัดรัด (90%)', desc: 'เหมาะกับจอโน้ตบุ๊กขนาดเล็กหรือเปิดหลายหน้าต่าง' },
                  { id: 'normal', label: 'ปกติ (100%)', desc: 'สัดส่วนมาตรฐาน สมดุลและคมชัด' },
                  { id: 'large', label: 'ใหญ่ (110%)', desc: 'ตัวหนังสือและปุ่มขนาดใหญ่ ชัดเจน สบายตา' },
                ].map((scale) => {
                  const isActive = uiScale === scale.id;
                  return (
                    <button
                      key={scale.id}
                      onClick={() => setUiScale && setUiScale(scale.id)}
                      className={`p-3.5 rounded-xl text-left border transition-all cursor-pointer relative active:scale-95 ${
                        isActive
                          ? 'bg-cyan-500/10 border-[#25F4EE] shadow-lg shadow-cyan-500/10 ring-1 ring-[#25F4EE]/40'
                          : 'bg-[#080B11] border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`font-bold text-xs sm:text-sm ${isActive ? 'text-[#25F4EE]' : 'text-white'}`}>
                          {scale.label}
                        </span>
                        {isActive && <CheckCircle2 className="w-4 h-4 text-[#25F4EE]" />}
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                        {scale.desc}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Section 2: Global UI Font Selector */}
            <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg space-y-3.5">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 flex-shrink-0">
                  <Type className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm sm:text-base font-bold text-white">
                    ฟอนต์ระบบ (Global UI Font)
                  </h3>
                  <p className="text-xs text-slate-400">
                    เลือกฟอนต์ภาษาไทยสำหรับเมนู หัวข้อ และปุ่มต่างๆ ทั้งระบบ
                  </p>
                </div>
              </div>

              {/* Font Grid Cards with Live Preview */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                {[
                  { id: 'font-prompt', name: 'Prompt', style: 'Modern Sans', preview: 'ฟอนต์ยอดนิยม ทันสมัย คมชัด อ่านง่ายมาก', tag: 'ค่าเริ่มต้น', bgClass: 'font-prompt' },
                  { id: 'font-anuphan', name: 'Anuphan', style: 'Modern Sans', preview: 'โค้งมน นุ่มนวล ดูมีระดับ สไตล์แอปสมัยใหม่', tag: 'ยอดเยี่ยม', bgClass: 'font-anuphan' },
                  { id: 'font-ibm', name: 'IBM Plex Sans Thai', style: 'Modern Sans', preview: 'คม ชัด ลึก สไตล์เทคโนโลยี เป็นทางการและน่าเชื่อถือ', tag: 'ทางการ', bgClass: 'font-ibm' },
                  { id: 'font-kanit', name: 'Kanit', style: 'Modern Sans', preview: 'หนักแน่น มีพลัง สไตล์วัยรุ่น TikTok ไวรัล', tag: 'วัยรุ่น', bgClass: 'font-kanit' },
                  { id: 'font-baijamjuree', name: 'Bai Jamjuree', style: 'Tech Geometric', preview: 'เหลี่ยมโมเดิร์น กึ่งแคบ ทรงพลัง ล้ำสมัย', tag: 'โมเดิร์น', bgClass: 'font-baijamjuree' },
                  { id: 'font-mitr', name: 'Mitr', style: 'Friendly Sans', preview: 'เป็นมิตร เข้าถึงง่าย นุ่มนวลและน่ารักกำลังดี', tag: 'เป็นมิตร', bgClass: 'font-mitr' },
                  { id: 'font-krub', name: 'Krub', style: 'Rounded Sans', preview: 'กลมมน อบอุ่น ฟีลไลฟ์สไตล์ สบายๆ', tag: 'ไลฟ์สไตล์', bgClass: 'font-krub' },
                  { id: 'font-sarabun', name: 'Sarabun', style: 'Official Loop', preview: 'มีหัว เรียบร้อย ชัดเจน ถูกต้องตามหลักราชการ', tag: 'ทางการ', bgClass: 'font-sarabun' },
                  { id: 'font-mali', name: 'Mali', style: 'Handwritten', preview: 'ลายมือน่ารัก มีเสน่ห์ เป็นกันเอง สไตล์วล็อก', tag: 'ลายมือ', bgClass: 'font-mali' },
                  { id: 'font-chonburi', name: 'Chonburi', style: 'High Contrast', preview: 'หรูหรา แฟชั่น หัวข้อตัวโตโดดเด่น สไตล์แม็กกาซีน', tag: 'หรูหรา', bgClass: 'font-chonburi' },
                ].map((f) => {
                  const isSelected = uiFont === f.id;
                  return (
                    <div
                      key={f.id}
                      onClick={() => setUiFont && setUiFont(f.id)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer relative group active:scale-95 ${
                        isSelected
                          ? 'bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border-[#25F4EE] shadow-md shadow-cyan-500/10 ring-1 ring-[#25F4EE]/40'
                          : 'bg-[#080B11] border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-xs sm:text-sm">
                            {f.name}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/[0.06] text-slate-400 border border-white/[0.08]">
                            {f.style}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                            isSelected
                              ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40'
                              : 'bg-white/[0.05] text-slate-400'
                          }`}>
                            {f.tag}
                          </span>
                          {isSelected && (
                            <CheckCircle2 className="w-3.5 h-3.5 text-[#25F4EE]" />
                          )}
                        </div>
                      </div>

                      <div className={`mt-2.5 p-2.5 rounded-lg bg-black/60 border border-white/[0.06] text-slate-200 text-xs sm:text-sm ${f.bgClass}`}>
                        {f.preview}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );

      case 'paths':
        return (
          <div className="space-y-4 animate-fadeIn">
            <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg space-y-3.5">
              <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2 pb-2.5 border-b border-white/[0.08]">
                <Folder className="w-4 h-4 text-[#25F4EE]" />
                ไดเรกทอรีโปรเจกต์มาตรฐาน (Project Workspace Directories)
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                {projectFolders.map((pf) => {
                  const Icon = pf.icon;
                  return (
                    <div
                      key={pf.id}
                      className="p-3 sm:p-3.5 rounded-xl bg-[#080B11] border border-white/[0.06] flex items-center justify-between group hover:border-[#25F4EE]/30 transition-all gap-2"
                    >
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
                          <Icon className={`w-4 h-4 ${pf.color}`} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <span className="font-bold text-xs sm:text-sm text-slate-200 block truncate">{pf.label}</span>
                          <span className="text-[10px] text-slate-500 font-mono">Windows Local Directory</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleOpen(pf.id)}
                        className="px-2.5 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 text-xs font-semibold border border-white/[0.08] transition-all flex-shrink-0 cursor-pointer active:scale-95"
                      >
                        เปิดโฟลเดอร์
                      </button>
                    </div>
                  );
                })}
              </div>

              <button
                onClick={() => handleOpen('root')}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-white/[0.06] to-white/[0.03] hover:from-white/[0.1] hover:to-white/[0.05] border border-white/[0.08] text-white text-xs font-bold transition-all shadow-sm cursor-pointer flex items-center justify-center gap-2 mt-2 active:scale-95"
              >
                <Folder className="w-4 h-4 text-[#25F4EE]" />
                เปิดโฟลเดอร์รากของโปรเจกต์ (Project Root)
              </button>
            </div>
          </div>
        );

      case 'engine':
        return (
          <div className="space-y-4 animate-fadeIn">
            {/* AI Providers Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
              {/* Box 1: Antigravity Pro */}
              <div className="p-4 sm:p-5 rounded-2xl bg-[#0B0F19] border border-[#25F4EE]/20 space-y-3 relative overflow-hidden shadow-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <ShieldCheck className="w-5 h-5 text-[#25F4EE]" />
                    <h4 className="font-bold text-white text-xs sm:text-sm">Antigravity Pro Engine</h4>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-bold bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30">
                    เชื่อมต่อแล้ว
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  ใช้งาน <b>Gemini 3.8 Flash (High)</b> สำหรับคิดบท Hook หยุดนิ้ว และแปลภาษาอังกฤษ ผ่านบัญชี Pro โดยตรง ไม่เสียเงินค่า API เพิ่มเติม
                </p>
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06] text-[11px] font-mono text-slate-400 space-y-1">
                  <div>• Path: ~/.gemini/bin/agy.exe</div>
                  <div>• Reasoning: High Effort</div>
                  <div>• API Cost: 0 THB (Included in subscription)</div>
                </div>
              </div>

              {/* Box 2: Google AI Studio Vision */}
              <div className="p-4 sm:p-5 rounded-2xl bg-[#0B0F19] border border-emerald-500/20 space-y-3 relative overflow-hidden shadow-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    <h4 className="font-bold text-white text-xs sm:text-sm">Gemini 2.5 Flash Vision</h4>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-bold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                    Free Tier
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  วิเคราะห์ฟุตเทจวิดีโอดิบแบบ 1 FPS ผ่าน Google File API ด้วยความเร็วสูง (4-7 วินาที) มาร์กจุดตัดอัตโนมัติ
                </p>
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06] text-[11px] font-mono text-slate-400 space-y-1">
                  <div>• Mode: Free Tier (1,500 requests/day)</div>
                  <div>• Max Video Upload: 2GB per clip</div>
                  <div>• Model: gemini-2.5-flash</div>
                </div>
              </div>
            </div>

            {/* System Environment Info */}
            <div className="p-4 sm:p-5 space-y-3.5 bg-[#0B0F19] rounded-2xl border border-white/[0.08] shadow-lg">
              <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2 pb-2 border-b border-white/[0.08]">
                <Settings className="w-4 h-4 text-[#25F4EE]" />
                สถานะการเรนเดอร์และ CapCut PC Integration
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
                <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] text-slate-200 flex flex-col justify-between space-y-1">
                  <span className="font-bold flex items-center gap-1.5 text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    FFmpeg Video Engine
                  </span>
                  <span className="text-xs font-mono font-bold text-white">
                    CPU Encode (libx264)
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex flex-col justify-between space-y-1">
                  <span className="font-bold flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    CapCut PC Draft Sync
                  </span>
                  <span className="text-xs font-mono font-bold text-emerald-300">
                    {status?.capcut_synced ? 'Synced' : 'Configured'}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] text-slate-200 flex flex-col justify-between space-y-1">
                  <span className="font-bold flex items-center gap-1.5 text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Wi-Fi Mobile Sync
                  </span>
                  <span className="text-xs font-mono font-bold text-white">
                    {status?.local_ip || '127.0.0.1'}:5173
                  </span>
                </div>
              </div>

              {/* Standard Specs Notice */}
              <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-1.5 text-xs text-slate-200">
                <div className="font-bold text-white flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#25F4EE]" />
                  สเปกวิดีโอมาตรฐาน OmniCut Pro Studio:
                </div>
                <ul className="space-y-1 text-slate-400 text-xs list-disc list-inside">
                  <li>ขนาดหน้าจอ: <b>1080 x 1920 (9:16 Vertical Video)</b></li>
                  <li>เฟรมเรต: <b>30 FPS H.264 High Profile</b></li>
                  <li>จังหวะการตัดต่อ: <b>1.5 - 2.5 วินาทีต่อ 1 ช็อต</b></li>
                  <li>ฟอนต์คำบรรยาย: <b>Prompt, IBM Plex Sans Thai, Kanit</b></li>
                </ul>
              </div>
            </div>

            {/* Round POST-2: TikTok Auto-Post Extension (experimental, risky) */}
            <div className="p-4 sm:p-5 space-y-3.5 bg-[#0B0F19] rounded-2xl border border-amber-500/20 shadow-lg">
              <div className="flex items-center justify-between gap-3 pb-2 border-b border-white/[0.08]">
                <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                  <Bug className="w-4 h-4 text-amber-400" />
                  TikTok Auto-Post Extension (ทดลอง — มีความเสี่ยง)
                </h3>
                <button
                  type="button"
                  onClick={toggleAutopost}
                  className={`relative w-11 h-6 rounded-full transition-colors cursor-pointer flex-shrink-0 ${
                    autopostEnabled ? 'bg-emerald-500' : 'bg-white/[0.12]'
                  }`}
                  title={autopostEnabled ? 'ปิดใช้งาน' : 'เปิดใช้งาน'}
                >
                  <span
                    className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                      autopostEnabled ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                ให้ Chrome extension เติม mp4 + ปก + แคปชั่นลงหน้า TikTok Studio ที่ล็อกอินอยู่แล้วให้อัตโนมัติ
                ผ่าน <code className="text-[10px] bg-black/40 px-1 py-0.5 rounded">chrome.debugger</code> —
                กลไกเดียวกับที่ Playwright/Puppeteer ใช้ทดสอบเว็บ ไม่ใช่บอทปลอมตัว แต่ Chrome จะโชว์แถบ
                "กำลัง debug เบราว์เซอร์นี้" ค้างตลอดเวลาที่ทำงาน (ซ่อนไม่ได้) และพี่ต้องกดเริ่มเองทุกครั้ง
                — ไม่มี schedule ไม่มี headless รายละเอียดเต็มดู{' '}
                <span className="font-mono text-amber-300">TIKTOK_AUTOPOST_PLAN.md</span>
              </p>

              <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-500/20 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-[11px] text-amber-200/90 leading-relaxed">
                  ยังไม่ผ่านการทดสอบกับหน้า TikTok Studio จริง (โครงสร้างหน้าเว็บอาจเปลี่ยนได้ทุกเมื่อ) —
                  ทดสอบกับคลิปทดลอง 3-5 คลิปก่อน แล้วสังเกตอาการบัญชี ก่อนใช้เป็นประจำ
                  ปุ่ม "เปิด TikTok Studio" แบบลากเองใน Post Studio ยังอยู่คู่กันเสมอ ปิดฟีเจอร์นี้ได้ทุกเมื่อ
                </p>
              </div>

              {autopostEnabled && (
                <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] text-[11px] text-slate-300 space-y-1.5">
                  <div className="font-bold text-white">วิธีติดตั้ง extension (ครั้งแรกครั้งเดียว):</div>
                  <ol className="list-decimal list-inside space-y-1 text-slate-400">
                    <li>เปิด <span className="font-mono text-slate-300">chrome://extensions</span> แล้วเปิด "Developer mode"</li>
                    <li>กด "Load unpacked" แล้วเลือกโฟลเดอร์ <span className="font-mono text-slate-300">tiktok_autopost_extension/</span> ในโปรเจกต์</li>
                    <li>เปิดแท็บ <span className="font-mono text-slate-300">tiktok.com/tiktokstudio/upload</span> ที่ล็อกอินไว้แล้ว</li>
                    <li>ในแอปนี้ กด "โพสต์ TikTok อัตโนมัติ" ใน Post Studio แล้วคลิกไอคอน extension เพื่อเริ่ม</li>
                  </ol>
                </div>
              )}
            </div>
          </div>
        );

      case 'maintenance':
        return (
          <div className="space-y-4 animate-fadeIn">
            {/* Box 1: One-Click System Backup */}
            <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
                <div>
                  <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                    <Database className="w-4 h-4 text-cyan-400" />
                    สำรองข้อมูลทั้งระบบ (One-Click System Backup)
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    สำรองข้อมูลโปรเจกต์ 03_Projects ทั้งหมด และฐานข้อมูล JSON / SQLite ใน _Docs เป็นไฟล์ Zip พร้อมกู้คืน
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleCreateBackup}
                  disabled={backupLoading}
                  className="px-3.5 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30 text-xs font-bold flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50 flex-shrink-0"
                >
                  {backupLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      กำลังบีบอัดไฟล์...
                    </>
                  ) : (
                    <>
                      <Archive className="w-3.5 h-3.5" />
                      สร้างไฟล์สำรองทันที
                    </>
                  )}
                </button>
              </div>

              {backupMessage && (
                <div className={`p-3 rounded-xl border text-xs ${
                  backupMessage.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                    : 'bg-red-500/10 border-red-500/20 text-red-300'
                }`}>
                  {backupMessage.text}
                </div>
              )}

              {/* Backups List */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-300 block">
                  ประวัติไฟล์สำรอง ({backups.length} ชุด)
                </span>
                {backups.length === 0 ? (
                  <div className="p-4 rounded-xl bg-black/40 border border-white/[0.06] text-center text-xs text-slate-500">
                    ยังไม่มีไฟล์สำรอง กดปุ่ม "สร้างไฟล์สำรองทันที" เพื่อสำรองข้อมูล
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto pr-1">
                    {backups.map((b) => (
                      <div
                        key={b.backup_name}
                        className="p-3 rounded-xl bg-black/40 border border-white/[0.06] flex items-center justify-between gap-3 text-xs"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="font-mono font-bold text-slate-200 truncate">{b.backup_name}</div>
                          <div className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-2">
                            <span>{b.created_at}</span>
                            <span>•</span>
                            <span className="text-cyan-400 font-bold">{b.size_mb} MB</span>
                            {b.file_count > 0 && (
                              <>
                                <span>•</span>
                                <span>{b.file_count} ไฟล์</span>
                              </>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <a
                            href={`/api/backup/download/${encodeURIComponent(b.backup_name)}`}
                            download={b.backup_name}
                            className="px-2.5 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-cyan-300 font-bold text-xs border border-white/[0.08] flex items-center gap-1.5 transition-all"
                          >
                            <Download className="w-3.5 h-3.5" />
                            ดาวน์โหลด
                          </a>
                          <button
                            type="button"
                            onClick={() => handleDeleteBackup(b.backup_name)}
                            className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-all cursor-pointer"
                            title="ลบไฟล์สำรองนี้"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Box 2: Asset Deduplication Engine */}
            <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
                <div>
                  <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                    <Copy className="w-4 h-4 text-amber-400" />
                    สแกนและคืนพื้นที่ดิสก์จากไฟล์ซ้ำ (Asset Deduplication)
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    ตรวจหาไฟล์วิดีโอ/ภาพที่ซ้ำกันใน 00_Inbox และ 01_Raw ด้วย SHA-256 เพื่อคืนพื้นที่ดิสก์อย่างปลอดภัย
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleScanDedup}
                  disabled={dedupLoading}
                  className="px-3.5 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 text-xs font-bold flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50 flex-shrink-0"
                >
                  {dedupLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      กำลังสแกนไฟล์...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3.5 h-3.5" />
                      เริ่มสแกนไฟล์ซ้ำ
                    </>
                  )}
                </button>
              </div>

              {cleanMessage && (
                <div className={`p-3 rounded-xl border text-xs ${
                  cleanMessage.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                    : 'bg-red-500/10 border-red-500/20 text-red-300'
                }`}>
                  {cleanMessage.text}
                </div>
              )}

              {dedupResult && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                      <span className="text-[10px] text-slate-500 block">สแกนทั้งหมด</span>
                      <span className="text-sm font-bold text-white"><span className="font-mono">{dedupResult.total_scanned_files}</span> ไฟล์</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                      <span className="text-[10px] text-slate-500 block">กลุ่มที่ซ้ำ</span>
                      <span className="text-sm font-bold text-amber-300"><span className="font-mono">{dedupResult.duplicate_groups_count}</span> กลุ่ม</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                      <span className="text-[10px] text-slate-500 block">ไฟล์ซ้ำส่วนเกิน</span>
                      <span className="text-sm font-bold text-red-300"><span className="font-mono">{dedupResult.total_duplicate_files}</span> ไฟล์</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-black/40 border border-emerald-500/20 bg-emerald-500/5">
                      <span className="text-[10px] text-emerald-400 block">คืนพื้นที่ได้</span>
                      <span className="text-sm font-bold font-mono text-emerald-300">{dedupResult.reclaimable_mb} MB</span>
                    </div>
                  </div>

                  {dedupResult.total_duplicate_files > 0 ? (
                    <div className="space-y-2 pt-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-300">รายการไฟล์ที่ซ้ำกัน</span>
                        <button
                          type="button"
                          onClick={handleCleanDedup}
                          disabled={cleanLoading}
                          className="px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/30 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                        >
                          {cleanLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                          ย้ายไฟล์ซ้ำเข้าถังขยะ ({dedupResult.reclaimable_mb} MB)
                        </button>
                      </div>

                      <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                        {dedupResult.groups.slice(0, dedupVisibleCount).map((g, idx) => (
                          <div key={idx} className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06] text-xs space-y-1.5">
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="text-slate-400 font-mono truncate max-w-[70%]">
                                ต้นฉบับ: <span className="text-emerald-400 font-bold">{g.original.relative_path}</span>
                              </span>
                              <span className="text-slate-500 font-mono">{g.size_mb} MB</span>
                            </div>
                            <div className="pl-3 border-l-2 border-amber-500/30 space-y-1 text-[11px] text-slate-400">
                              {g.duplicates.map((d, dIdx) => (
                                <div key={dIdx} className="truncate text-red-400/90 font-mono">
                                  ซ้ำ: {d.relative_path}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                        {dedupVisibleCount < dedupResult.groups.length && (
                          <button
                            type="button"
                            onClick={() => setDedupVisibleCount(c => c + DEDUP_PAGE_SIZE)}
                            className="w-full py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-dashed border-white/[0.12] text-slate-300 text-[11px] font-bold cursor-pointer transition-all"
                          >
                            โหลดเพิ่ม ({dedupResult.groups.length - dedupVisibleCount} กลุ่มที่เหลือ)
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center text-xs text-emerald-300">
                      ไม่พบไฟล์มีเดียซ้ำซ้อนในโฟลเดอร์ ระบบสะอาด 100%
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-4 animate-fadeIn pb-16">
      <PageHeader
        icon={Settings}
        eyebrow="ตั้งค่าระบบ"
        title={`${currentSection?.name} — ${currentSection?.desc}`}
        badges={
          <span className={`text-[10px] sm:text-xs font-bold px-2 py-0.5 rounded-full border ${currentSection?.badgeColor}`}>
            {currentSection?.name}
          </span>
        }
        quickSwitcher={
          <div className="sm:hidden relative flex-shrink-0">
            <select
              value={activeTab}
              onChange={(e) => setActiveTab(e.target.value)}
              className="bg-black/50 border border-white/[0.1] text-slate-200 text-xs font-bold py-1.5 px-2 rounded-xl focus:outline-none focus:border-[#25F4EE] cursor-pointer max-w-[125px] truncate"
            >
              {settingSections.map((s) => (
                <option key={s.id} value={s.id} className="bg-[#080B11] text-white">
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        }
        actions={
          <>
            {/* System Status Pill */}
            <div className="flex items-center gap-1.5 bg-black/40 px-2.5 py-1.5 rounded-xl border border-white/[0.08] text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-400 hidden xs:inline">สถานะ:</span>
              <span className="text-emerald-300 font-bold font-mono">
                {status?.capcut_synced ? 'CapCut Synced' : 'Ready'}
              </span>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center bg-black/40 p-0.5 rounded-xl border border-white/[0.08]">
              <button
                type="button"
                onClick={() => setViewMode('split')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === 'split'
                    ? 'bg-[#25F4EE]/15 text-[#25F4EE] shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="มุมมองแบบสตูดิโอ 2 ฝั่ง"
              >
                <Columns className="w-3.5 h-3.5" />
                <span className="hidden xs:inline">สตูดิโอ</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('classic')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === 'classic'
                    ? 'bg-[#25F4EE]/15 text-[#25F4EE] shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="มุมมองแบบแถบเดี่ยว"
              >
                <List className="w-3.5 h-3.5" />
                <span className="hidden xs:inline">แถบเดี่ยว</span>
              </button>
            </div>
          </>
        }
      />

      {/* ══════════════════════════════════════════════════════════
          2. MOBILE HORIZONTAL SWIPEABLE CAROUSEL (iPhone 15 PM)
         ══════════════════════════════════════════════════════════ */}
      <div className="lg:hidden space-y-1.5">
        <div className="flex items-center justify-between px-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            แตะสลับหมวดหมู่ตั้งค่า:
          </span>
          <span className="text-[11px] font-mono text-[#25F4EE] font-bold">
            {settingSections.findIndex(s => s.id === activeTab) + 1}/{settingSections.length}
          </span>
        </div>
        <div className="flex items-stretch gap-2 overflow-x-auto pb-2 pt-0.5 no-scrollbar snap-x snap-mandatory pr-2 scroll-smooth">
          {settingSections.map((s, idx) => {
            const Icon = s.icon;
            const isSelected = activeTab === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setActiveTab(s.id)}
                className={`flex-shrink-0 snap-center px-3 py-2 rounded-xl border text-left transition-all cursor-pointer flex items-center gap-2 max-w-[210px] active:scale-95 ${
                  isSelected
                    ? 'bg-[#25F4EE]/15 border-[#25F4EE] shadow-md shadow-[#25F4EE]/20 ring-1 ring-[#25F4EE]/40'
                    : 'bg-[#0B0F19] border-white/[0.08] hover:border-white/[0.2] text-slate-300'
                }`}
              >
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  isSelected ? 'bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] text-slate-950 font-bold' : 'bg-white/[0.06] text-slate-400'
                }`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                    {s.name}
                  </div>
                  <div className="text-[10px] text-slate-500 truncate mt-0.5">
                    {s.badge}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          3. MAIN WORKBENCH: MASTER-DETAIL STUDIO vs CLASSIC
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'split' ? (
        <div className="space-y-4 lg:space-y-0 lg:grid lg:grid-cols-12 lg:gap-4 items-start">
          {/* DESKTOP (lg+): Left Column Settings Playlist (4 cols) */}
          <div className="hidden lg:block lg:col-span-4 space-y-2 lg:sticky lg:top-4">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider px-1 pb-1">
              หมวดหมู่การตั้งค่า ({settingSections.length} รายการ)
            </div>
            {settingSections.map((s, idx) => {
              const Icon = s.icon;
              const isSelected = activeTab === s.id;
              return (
                <div
                  key={s.id}
                  onClick={() => setActiveTab(s.id)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer text-left group relative active:scale-98 ${
                    isSelected
                      ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE]/60 shadow-md shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/30'
                      : 'bg-[#080B11] border-white/[0.06] hover:border-white/[0.18] hover:bg-white/[0.02]'
                  }`}
                >
                  {/* Left Indicator */}
                  {isSelected && (
                    <div className="absolute left-0 top-2 bottom-2 w-1 bg-[#25F4EE] rounded-r-full shadow-sm shadow-[#25F4EE]" />
                  )}

                  <div className="flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${
                      isSelected
                        ? 'bg-gradient-to-tr from-[#25F4EE] to-blue-500 text-slate-950 shadow-sm'
                        : 'bg-white/[0.06] text-slate-400 border border-white/[0.08]'
                    }`}>
                      <Icon className="w-4 h-4" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1.5">
                        <span className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                          {s.name}
                        </span>
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${s.badgeColor}`}>
                          {s.badge}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-snug mt-1 line-clamp-2">
                        {s.desc}
                      </p>
                    </div>

                    <ChevronRight className={`w-4 h-4 self-center transition-transform ${
                      isSelected ? 'text-[#25F4EE] translate-x-0.5' : 'text-slate-600 group-hover:text-slate-400'
                    }`} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column: Dedicated Settings Workbench (8 cols on desktop, full width on mobile) */}
          <div className="lg:col-span-8">
            {renderWorkbenchContent()}
          </div>
        </div>
      ) : (
        /* Classic View: Desktop Tabs Row + Full Width Content */
        <div className="space-y-4">
          <div className="hidden lg:flex items-center gap-1.5 p-1 rounded-2xl bg-[#0B0F19] border border-white/[0.08]">
            {settingSections.map((t) => {
              const Icon = t.icon;
              const isActive = activeTab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex-1 justify-center ${
                    isActive
                      ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white shadow-md'
                      : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{t.name}</span>
                </button>
              );
            })}
          </div>

          <div>
            {renderWorkbenchContent()}
          </div>
        </div>
      )}
    </div>
  );
}
