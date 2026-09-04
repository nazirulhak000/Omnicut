import React, { useState } from 'react';
import {
  Settings, Folder, HardDrive, CheckCircle2, Sliders, Type,
  Sparkles, RefreshCw, Smartphone, ShieldCheck, Cpu, Terminal, Layers,
  BarChart3
} from 'lucide-react';
import { openFolder } from '../api';
import TokenDashboard from './TokenDashboard';

export default function SystemSettings({
  status,
  uiFont = 'font-prompt',
  setUiFont,
  uiScale = 'normal',
  setUiScale,
  initialSubTab = 'tokens'
}) {
  const [activeTab, setActiveTab] = useState(initialSubTab); // 'tokens' | 'appearance' | 'paths' | 'engine'

  const handleOpen = (target) => {
    openFolder(target);
  };

  const projectFolders = [
    { id: 'inbox', label: '00_Inbox (ไฟล์ดิบจากมือถือ)', icon: Smartphone, color: 'text-[#25F4EE]' },
    { id: 'raw', label: '01_Raw (ฟุตเทจต้นฉบับแยกสินค้า)', icon: Folder, color: 'text-blue-400' },
    { id: 'assets', label: '02_Assets (มีเดียส่วนกลาง)', icon: Layers, color: 'text-purple-400' },
    { id: 'projects', label: '03_Projects (ไฟล์โปรเจกต์/ดราฟต์)', icon: Folder, color: 'text-amber-400' },
    { id: 'exports', label: '04_Exports (วิดีโอที่ตัดเสร็จ)', icon: CheckCircle2, color: 'text-emerald-400' },
    { id: 'capcut', label: 'CapCut Drafts (โฟลเดอร์ CapCut PC)', icon: HardDrive, color: 'text-pink-400' },
  ];

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* ── Page Header ── */}
      <div className="glass-panel p-5 sm:p-6 rounded-3xl border border-white/[0.08] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#25F4EE] to-blue-600 flex items-center justify-center text-slate-950 font-bold shadow-lg shadow-[#25F4EE]/20 flex-shrink-0">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold font-kanit text-white flex items-center gap-2">
              ตั้งค่าระบบ & สถิติ AI (Settings & Analytics)
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              ศูนย์รวมการวิเคราะห์โทเคน AI, ปรับขนาดหน้าจอ ฟอนต์ระบบ, จัดการโฟลเดอร์ และตรวจสอบความพร้อมของระบบ
            </p>
          </div>
        </div>

        {/* Navigation Sub-tabs */}
        <div className="flex items-center gap-1.5 p-1 rounded-2xl bg-black/40 border border-white/[0.08] flex-wrap">
          {[
            { id: 'tokens', label: 'สถิติ & โทเคน AI', icon: BarChart3 },
            { id: 'appearance', label: 'การแสดงผล & ฟอนต์', icon: Sliders },
            { id: 'paths', label: 'โฟลเดอร์ & ที่จัดเก็บ', icon: Folder },
            { id: 'engine', label: 'สถานะ AI & ระบบ', icon: Cpu },
          ].map((t) => {
            const Icon = t.icon;
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  isActive
                    ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white shadow-md'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── 0. AI TOKEN ANALYTICS SUB-TAB ── */}
      {activeTab === 'tokens' && (
        <div className="animate-fadeIn">
          <TokenDashboard />
        </div>
      )}

      {/* ── 1. APPEARANCE & TYPOGRAPHY TAB ── */}
      {activeTab === 'appearance' && (
        <div className="space-y-6 animate-fadeIn">
          {/* Section 1: UI Scale Control */}
          <div className="glass-card p-5 sm:p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-[#25F4EE]">
                <Sliders className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base sm:text-lg font-bold font-kanit text-white">
                  ขนาดการแสดงผล (UI Scale)
                </h3>
                <p className="text-xs text-slate-400">
                  ปรับอัตราส่วนและขนาดตัวหนังสือของโปรแกรมให้สบายตา เหมาะกับขนาดหน้าจอของคุณ
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              {[
                { id: 'compact', label: 'กะทัดรัด (90%)', desc: 'เหมาะกับจอโน้ตบุ๊กขนาดเล็ก มองเห็นข้อมูลได้เยอะขึ้น' },
                { id: 'normal', label: 'ปกติ (100%)', desc: 'สัดส่วนมาตรฐาน สมดุลและคมชัด' },
                { id: 'large', label: 'ใหญ่ (110%)', desc: 'ตัวหนังสือและปุ่มขนาดใหญ่ ชัดเจน สบายตา' },
              ].map((scale) => {
                const isActive = uiScale === scale.id;
                return (
                  <button
                    key={scale.id}
                    onClick={() => setUiScale && setUiScale(scale.id)}
                    className={`p-4 rounded-xl text-left border transition-all cursor-pointer relative ${
                      isActive
                        ? 'bg-cyan-500/10 border-[#25F4EE] shadow-lg shadow-cyan-500/10'
                        : 'bg-black/40 border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-bold text-sm ${isActive ? 'text-[#25F4EE]' : 'text-white'}`}>
                        {scale.label}
                      </span>
                      {isActive && <CheckCircle2 className="w-4 h-4 text-[#25F4EE]" />}
                    </div>
                    <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                      {scale.desc}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 2: Global UI Font Selector */}
          <div className="glass-card p-5 sm:p-6 space-y-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <Type className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-bold font-kanit text-white">
                    ฟอนต์ระบบ (Global UI Font)
                  </h3>
                  <p className="text-xs text-slate-400">
                    เลือกฟอนต์ภาษาไทยสำหรับเมนู หัวข้อ และปุ่มต่างๆ ทั้งโปรแกรม
                  </p>
                </div>
              </div>
            </div>

            {/* Font Grid Cards with Live Preview */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
              {[
                { id: 'font-prompt', name: 'Prompt', style: 'Modern Sans', preview: 'ฟอนต์ยอดนิยม ทันสมัย คมชัด อ่านง่ายมาก', tag: 'ค่าเริ่มต้น', bgClass: 'font-prompt' },
                { id: 'font-anuphan', name: 'Anuphan', style: 'Modern Sans', preview: 'โค้งมน นุ่มนวล ดูมีระดับ ทันสมัยสไตล์แอปสมัยใหม่', tag: 'ยอดเยี่ยม', bgClass: 'font-anuphan' },
                { id: 'font-ibm', name: 'IBM Plex Sans Thai', style: 'Modern Sans', preview: 'คม ชัด ลึก สไตล์เทคโนโลยี เป็นทางการและน่าเชื่อถือ', tag: 'ทางการ', bgClass: 'font-ibm' },
                { id: 'font-kanit', name: 'Kanit', style: 'Modern Sans', preview: 'หนักแน่น มีพลัง สไตล์วัยรุ่น TikTok คอนเทนต์ไวรัล', tag: 'วัยรุ่น', bgClass: 'font-kanit' },
                { id: 'font-baijamjuree', name: 'Bai Jamjuree', style: 'Tech Geometric', preview: 'เหลี่ยมโมเดิร์น กึ่งแคบ ทรงพลัง ทรงเหลี่ยมแบบล้ำสมัย', tag: 'โมเดิร์น', bgClass: 'font-baijamjuree' },
                { id: 'font-mitr', name: 'Mitr', style: 'Friendly Sans', preview: 'เป็นมิตร เข้าถึงง่าย นุ่มนวลและน่ารักกำลังดี', tag: 'เป็นมิตร', bgClass: 'font-mitr' },
                { id: 'font-krub', name: 'Krub', style: 'Rounded Sans', preview: 'กลมมน อบอุ่น ฟีลไลฟ์สไตล์ สบายๆ', tag: 'ไลฟ์สไตล์', bgClass: 'font-krub' },
                { id: 'font-sarabun', name: 'Sarabun', style: 'Official Loop', preview: 'มีหัว เรียบร้อย ชัดเจน ถูกต้องตามหลักราชการและสิ่งพิมพ์', tag: 'ทางการ', bgClass: 'font-sarabun' },
                { id: 'font-mali', name: 'Mali', style: 'Handwritten', preview: 'ลายมือน่ารัก มีเสน่ห์ เป็นกันเอง สไตล์วล็อกและรีวิวของกิน', tag: 'ลายมือ', bgClass: 'font-mali' },
                { id: 'font-chonburi', name: 'Chonburi', style: 'High Contrast', preview: 'หรูหรา แฟชั่น หัวข้อตัวโตโดดเด่น สไตล์แม็กกาซีนพรีเมียม', tag: 'หรูหรา', bgClass: 'font-chonburi' },
              ].map((f) => {
                const isSelected = uiFont === f.id;
                return (
                  <div
                    key={f.id}
                    onClick={() => setUiFont && setUiFont(f.id)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer relative group ${
                      isSelected
                        ? 'bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border-[#25F4EE] shadow-lg shadow-cyan-500/10'
                        : 'bg-black/40 border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">
                          {f.name}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-white/[0.06] text-slate-400 border border-white/[0.08]">
                          {f.style}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                          isSelected
                            ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40'
                            : 'bg-white/[0.05] text-slate-400'
                        }`}>
                          {f.tag}
                        </span>
                        {isSelected && (
                          <CheckCircle2 className="w-4 h-4 text-[#25F4EE]" />
                        )}
                      </div>
                    </div>

                    <div className={`mt-3 p-3 rounded-lg bg-black/60 border border-white/[0.06] text-slate-200 text-sm ${f.bgClass}`}>
                      {f.preview}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── 2. PATHS & STORAGE TAB ── */}
      {activeTab === 'paths' && (
        <div className="space-y-6 animate-fadeIn">
          <div className="glass-card p-5 sm:p-6 space-y-4">
            <h3 className="text-sm font-bold text-white font-kanit flex items-center gap-2 pb-2 border-b border-white/[0.08]">
              <Folder className="w-4 h-4 text-[#25F4EE]" />
              ไดเรกทอรีโปรเจกต์มาตรฐาน (Project Workspace Directories)
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
              {projectFolders.map((pf) => {
                const Icon = pf.icon;
                return (
                  <div
                    key={pf.id}
                    className="p-4 rounded-xl bg-black/40 border border-white/[0.06] flex items-center justify-between group hover:border-[#25F4EE]/30 transition-all"
                  >
                    <div className="flex items-center gap-3 min-w-0 pr-2">
                      <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
                        <Icon className={`w-5 h-5 ${pf.color}`} />
                      </div>
                      <div className="min-w-0">
                        <span className="font-bold text-xs sm:text-sm text-slate-200 block truncate">{pf.label}</span>
                        <span className="text-[11px] text-slate-500 font-mono">Windows Local Folder</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleOpen(pf.id)}
                      className="px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 text-xs font-semibold border border-white/[0.08] transition-colors flex-shrink-0 cursor-pointer"
                    >
                      เปิดโฟลเดอร์
                    </button>
                  </div>
                );
              })}
            </div>

            <button
              onClick={() => handleOpen('root')}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-white/[0.06] to-white/[0.03] hover:from-white/[0.1] hover:to-white/[0.05] border border-white/[0.08] text-white text-xs font-bold transition-all shadow-sm cursor-pointer flex items-center justify-center gap-2 mt-2"
            >
              <Folder className="w-4 h-4 text-[#25F4EE]" />
              เปิดโฟลเดอร์รากของโปรเจกต์ (Project Root)
            </button>
          </div>
        </div>
      )}

      {/* ── 3. AI ENGINE & PIPELINE HEALTH TAB ── */}
      {activeTab === 'engine' && (
        <div className="space-y-6 animate-fadeIn">
          {/* AI Providers Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Box 1: Antigravity Pro */}
            <div className="p-5 rounded-2xl glass-card border border-[#25F4EE]/20 space-y-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-5 h-5 text-[#25F4EE]" />
                  <h4 className="font-bold text-white text-sm font-kanit">Antigravity Pro Engine</h4>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30">
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
            <div className="p-5 rounded-2xl glass-card border border-emerald-500/20 space-y-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <h4 className="font-bold text-white text-sm font-kanit">Gemini 2.5 Flash Vision</h4>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
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
          <div className="p-5 space-y-4 glass-card rounded-2xl">
            <h3 className="text-sm font-bold text-white font-kanit flex items-center gap-2 pb-2 border-b border-white/[0.08]">
              <Settings className="w-4 h-4 text-[#25F4EE]" />
              สถานะการเรนเดอร์และ CapCut PC Integration
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] text-slate-200 flex flex-col justify-between space-y-1.5">
                <span className="font-bold flex items-center gap-2 text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  FFmpeg Video Engine
                </span>
                <span className="text-xs font-mono font-bold text-white">
                  CPU Encode (libx264)
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex flex-col justify-between space-y-1.5">
                <span className="font-bold flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  CapCut PC Draft Sync
                </span>
                <span className="text-xs font-mono font-bold text-emerald-300">
                  {status?.capcut_synced ? 'Synced' : 'Configured'}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] text-slate-200 flex flex-col justify-between space-y-1.5">
                <span className="font-bold flex items-center gap-2 text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Wi-Fi Mobile Sync
                </span>
                <span className="text-xs font-mono font-bold text-white">
                  {status?.local_ip || '127.0.0.1'}:5173
                </span>
              </div>
            </div>

            {/* Standard Specs Notice */}
            <div className="p-4 rounded-xl bg-black/40 border border-white/[0.06] space-y-2 text-xs text-slate-200">
              <div className="font-bold text-white flex items-center gap-2 font-kanit">
                <Sparkles className="w-4 h-4 text-[#25F4EE]" />
                สเปกวิดีโอมาตรฐาน OmniCut Pro Studio:
              </div>
              <ul className="space-y-1 text-slate-400 text-sm list-disc list-inside">
                <li>ขนาดหน้าจอ: <b>1080 x 1920 (9:16 Vertical Video)</b></li>
                <li>เฟรมเรต: <b>30 FPS H.264 High Profile</b></li>
                <li>จังหวะการตัดต่อ: <b>1.5 - 2.5 วินาทีต่อ 1 ช็อต</b></li>
                <li>ฟอนต์คำบรรยาย: <b>Prompt, IBM Plex Sans Thai, Kanit</b></li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
