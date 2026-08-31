import React, { useState, useEffect } from 'react';
import { 
  Film, Sparkles, FolderDown, Lightbulb, Settings, Zap, 
  CheckCircle2, AlertTriangle, FileText, Maximize, Minimize, 
  Smartphone, QrCode, X, Copy, Check, ExternalLink, Wifi
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

export default function Header({ status, activeTab, setActiveTab }) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showMobileModal, setShowMobileModal] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(err => {
        console.error('Error attempting to enable fullscreen:', err);
      });
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };

  const mobileUrl = status?.mobile_url || `http://${window.location.hostname}:5173`;

  const copyMobileLink = () => {
    navigator.clipboard.writeText(mobileUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tabs = [
    { id: 'studio', label: '1. 1-Click Studio', icon: Sparkles, badge: 'ตัดต่อด่วน' },
    { id: 'capcut_studio', label: '2. CapCut Studio', icon: Film, badge: 'ไทม์ไลน์ Pro 🎬' },
    { id: 'gallery', label: '3. Export Gallery', icon: FolderDown, badge: `${status?.total_exports || 0} คลิป` },
    { id: 'script_lab', label: '4. AI Script Lab', icon: Lightbulb, badge: 'สูตรบทยอดฮิต' },
    { id: 'assets', label: '5. System & Assets', icon: Settings, badge: 'ระบบ & SFX' },
  ];

  return (
    <header className="mb-6">
      {/* Top Hero Bar */}
      <div className="glass-panel p-4 md:p-6 mb-4 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border border-white/10 shadow-2xl">
        <div className="flex items-center gap-3.5 sm:gap-4 w-full lg:w-auto">
          <div className="w-11 h-11 sm:w-13 sm:h-13 rounded-2xl bg-gradient-to-tr from-[#FE2C55] via-[#FF0050] to-[#25F4EE] flex items-center justify-center shadow-lg shadow-[#FE2C55]/30 flex-shrink-0">
            <Zap className="w-6 h-6 sm:w-7 sm:h-7 text-white animate-pulse" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl sm:text-2xl md:text-3xl font-black font-kanit tracking-tight bg-gradient-to-r from-[#FE2C55] via-[#FF0050] to-[#25F4EE] bg-clip-text text-transparent truncate">
                TikTok Auto-Cutter Pro Studio
              </h1>
              <span className="text-[10px] sm:text-xs font-bold px-2 py-0.5 rounded-full bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30">
                v2.5 Full-Screen & Mobile Sync
              </span>
            </div>
            <p className="text-[11px] sm:text-xs md:text-sm text-slate-400 font-prompt mt-0.5 line-clamp-1 sm:line-clamp-none">
              ระบบ AI ตัดต่อคลิปป้ายยาอัตโนมัติ — คิดบท • พากย์เสียง HD • ซอยคัตซูม • วิ่งซับ Kanit • SFX ครบวงจร
            </p>
          </div>
        </div>

        {/* Action Controls & System Badges */}
        <div className="flex flex-wrap items-center justify-between sm:justify-end gap-2 w-full lg:w-auto pt-2 lg:pt-0 border-t lg:border-t-0 border-white/5">
          {/* Mobile Upload Button with QR Modal Trigger */}
          <button
            onClick={() => setShowMobileModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-500/20 to-teal-500/20 hover:from-emerald-500/30 hover:to-teal-500/30 text-emerald-300 border border-emerald-500/30 shadow-lg shadow-emerald-500/10 transition-all hover:scale-105 active:scale-95 cursor-pointer"
            title="เชื่อมต่อมือถือผ่าน Wi-Fi เพื่ออัปโหลดวิดีโอไม่ต้องเสียบสาย"
          >
            <Smartphone className="w-4 h-4 text-emerald-400 animate-bounce" />
            <span className="hidden sm:inline">📱 อัปโหลดผ่านมือถือ</span>
            <span className="sm:hidden">📱 ส่งไฟล์มือถือ</span>
            <QrCode className="w-3.5 h-3.5 text-emerald-400" />
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={toggleFullscreen}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all hover:text-white"
            title={isFullscreen ? 'ออกจากโหมดเต็มจอ (Esc)' : 'เปิดโหมดเต็มจอ (F11)'}
          >
            {isFullscreen ? (
              <>
                <Minimize className="w-4 h-4 text-[#25F4EE]" />
                <span className="hidden sm:inline">ย่อจอ</span>
              </>
            ) : (
              <>
                <Maximize className="w-4 h-4 text-[#25F4EE]" />
                <span className="hidden sm:inline">เต็มจอ</span>
              </>
            )}
          </button>

          {/* CapCut Synced Badge */}
          <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[11px] font-semibold border shadow-sm ${
            status?.capcut_synced
              ? 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/30'
              : 'bg-[#FE2C55]/10 text-[#FE2C55] border-[#FE2C55]/30'
          }`}>
            {status?.capcut_synced ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                CapCut Synced
              </>
            ) : (
              <>
                <AlertTriangle className="w-3.5 h-3.5" />
                CapCut Local
              </>
            )}
          </div>

          {/* Export Count Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            <Film className="w-3.5 h-3.5 text-[#FE2C55]" />
            <span>{status?.total_exports || 0} คลิป</span>
          </div>
        </div>
      </div>

      {/* Main Tabs Navigation (Horizontal Swipe on Mobile) */}
      <nav className="flex items-center gap-2 p-1.5 bg-[#121622]/95 border border-white/10 rounded-2xl backdrop-blur-xl overflow-x-auto no-scrollbar shadow-xl">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 min-w-[140px] sm:min-w-[170px] flex items-center justify-center gap-2 py-2.5 sm:py-3 px-3 sm:px-4 rounded-xl font-bold text-xs sm:text-sm whitespace-nowrap transition-all duration-200 cursor-pointer ${
                isActive
                  ? 'bg-gradient-to-r from-[#222A3A] to-[#171E2B] text-white border border-[#25F4EE]/30 shadow-lg shadow-black/50 text-shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-[#25F4EE]' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className={`text-[10px] px-1.5 sm:px-2 py-0.5 rounded-full font-bold transition-colors ${
                  isActive ? 'bg-[#FE2C55] text-white' : 'bg-slate-800/80 text-slate-400'
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* MOBILE UPLOAD & QR CODE MODAL */}
      {showMobileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md p-6 glass-panel border border-[#25F4EE]/30 shadow-2xl rounded-3xl text-center space-y-4">
            {/* Close Button */}
            <button
              onClick={() => setShowMobileModal(false)}
              className="absolute top-4 right-4 p-2 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Modal Title */}
            <div className="space-y-1">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 to-[#25F4EE] flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
                <Smartphone className="w-6 h-6 text-slate-950" />
              </div>
              <h3 className="text-xl font-bold text-white font-kanit">
                สแกนเปิดบนมือถือ (Wireless Direct Upload)
              </h3>
              <p className="text-xs text-slate-400 font-prompt">
                อัปโหลดวิดีโอจากมือถือเข้าคอมพิวเตอร์ผ่าน Wi-Fi ได้ทันที ไม่ต้องต่อสาย USB
              </p>
            </div>

            {/* QR Code Container */}
            <div className="p-4 bg-white rounded-2xl inline-block shadow-xl mx-auto">
              <QRCodeSVG
                value={mobileUrl}
                size={190}
                level="M"
                includeMargin={false}
              />
            </div>

            {/* URL Display & Copy */}
            <div className="p-3 bg-black/50 rounded-xl border border-white/10 space-y-2">
              <div className="flex items-center justify-between gap-2 text-xs text-slate-300">
                <span className="flex items-center gap-1.5 font-medium text-emerald-400">
                  <Wifi className="w-3.5 h-3.5" />
                  ที่อยู่เว็บในวงแลน (Local Network):
                </span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={mobileUrl}
                  className="w-full py-1.5 px-2.5 rounded-lg bg-[#121622] border border-white/10 text-xs font-mono text-slate-200 select-all"
                />
                <button
                  onClick={copyMobileLink}
                  className="px-3 py-1.5 rounded-lg bg-[#232A3B] hover:bg-[#323B52] text-white text-xs font-bold flex items-center gap-1.5 transition-colors flex-shrink-0"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      คัดลอกแล้ว
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-[#25F4EE]" />
                      คัดลอก
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Instructions */}
            <div className="text-left text-[11px] text-slate-400 bg-white/5 p-3 rounded-xl space-y-1">
              <div className="font-semibold text-slate-300">💡 วิธีใช้งานง่ายๆ:</div>
              <div>1. ให้มือถือและคอมพิวเตอร์เชื่อมต่อ <b>Wi-Fi เดียวกัน</b></div>
              <div>2. ใช้กล้องมือถือ iPhone / Android สแกน QR Code ด้านบน</div>
              <div>3. กดเลือกวิดีโอจากคลังภาพหรือถ่ายใหม่เพื่อโยนไฟล์เข้าคอมได้ทันที!</div>
            </div>

            <button
              onClick={() => setShowMobileModal(false)}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#232A3B] to-[#1C2230] hover:bg-[#323B52] text-white text-xs font-bold border border-white/10 transition-colors"
            >
              ปิดหน้าต่าง
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
