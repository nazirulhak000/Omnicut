import React, { useState, useEffect } from 'react';
import { 
  Film, Sparkles, FolderDown, Lightbulb, Settings, Zap, Rocket,
  Maximize, Minimize,
  Smartphone, QrCode, X, Copy, Check, Wifi
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
    { id: 'flow', label: '1. สินค้า → คลิป', icon: Rocket, badge: 'ไล่ 4 ขั้นจบ' },
    { id: 'studio', label: '2. 1-Click Studio', icon: Sparkles, badge: 'ตัดต่อด่วน' },
    { id: 'gallery', label: '3. Export Gallery', icon: FolderDown, badge: `${status?.total_exports || 0} คลิป` },
    { id: 'script_lab', label: '4. AI Script Lab', icon: Lightbulb, badge: 'สูตรบทยอดฮิต' },
    { id: 'assets', label: '5. System & Assets', icon: Settings, badge: 'ระบบ & SFX' },
  ];

  return (
    <header className="mb-6">
      {/* Top Hero Bar */}
      <div className="p-4 md:p-6 mb-4 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 glass-panel border border-white/[0.08] rounded-3xl shadow-xl text-slate-100">
        <div className="flex items-center gap-3.5 sm:gap-4 w-full lg:w-auto">
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-white shadow-lg shadow-[#FE2C55]/20 flex-shrink-0">
            <Zap className="w-6 h-6 sm:w-6 sm:h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold font-kanit text-white tracking-tight truncate">
                CapCut Studio Pro
              </h1>
              <span className="text-[10px] sm:text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30">
                v2.5 AI Video Production
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 line-clamp-1 sm:line-clamp-none">
              ระบบ AI ตัดต่อคลิปป้ายยาอัตโนมัติ — คิดบท • พากย์เสียง HD • ซอยคัตซูม • วิ่งซับ Typography • SFX ครบวงจร
            </p>
          </div>
        </div>

        {/* Action Controls & System Badges */}
        <div className="flex flex-wrap items-center justify-between sm:justify-end gap-2 w-full lg:w-auto pt-2 lg:pt-0 border-t lg:border-t-0 border-white/[0.08]">
          {/* Mobile Upload Button with QR Modal Trigger */}
          <button
            onClick={() => setShowMobileModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 shadow-sm transition-all cursor-pointer"
            title="เชื่อมต่อมือถือผ่าน Wi-Fi เพื่ออัปโหลดวิดีโอไม่ต้องเสียบสาย"
          >
            <Smartphone className="w-4 h-4 text-emerald-400" />
            <span className="hidden sm:inline">อัปโหลดผ่านมือถือ</span>
            <span className="sm:hidden">ส่งไฟล์มือถือ</span>
            <QrCode className="w-3.5 h-3.5 text-emerald-400" />
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={toggleFullscreen}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 border border-white/[0.08] transition-all cursor-pointer"
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

          {/* Export Count Badge */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-bold bg-white/[0.05] text-slate-300 border border-white/[0.08]">
            <Film className="w-3.5 h-3.5 text-[#FE2C55]" />
            <span>{status?.total_exports || 0} คลิป</span>
          </div>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <nav className="flex items-center gap-2 p-1.5 glass-panel border border-white/[0.08] rounded-2xl overflow-x-auto no-scrollbar shadow-lg">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 min-w-[140px] sm:min-w-[170px] flex items-center justify-center gap-2 py-2.5 sm:py-3 px-3 sm:px-4 rounded-xl font-bold text-xs sm:text-sm whitespace-nowrap transition-all duration-200 cursor-pointer ${
                isActive
                  ? 'bg-gradient-to-r from-[#FE2C55] to-[#FF0050] text-white shadow-lg shadow-[#FE2C55]/25 border border-transparent'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.05] border border-transparent'
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold transition-colors ${
                  isActive ? 'bg-black/30 text-white' : 'bg-white/[0.05] text-slate-400 border border-white/[0.08]'
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Mobile QR Modal */}
      {showMobileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md p-6 glass-panel border border-white/[0.15] shadow-2xl rounded-3xl text-center space-y-4 text-slate-100">
            <button
              onClick={() => setShowMobileModal(false)}
              className="w-8 h-8 rounded-full bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white flex items-center justify-center absolute top-4 right-4 transition-colors cursor-pointer text-base font-bold"
            >
              ✕
            </button>

            <div className="space-y-1">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center mx-auto text-white shadow-lg">
                <Smartphone className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white font-kanit">
                ส่งวิดีโอจากมือถือเข้าเครื่อง
              </h3>
              <p className="text-xs text-slate-400">
                สแกน QR Code ด้วยมือถือเพื่อเปิดหน้าอัปโหลดไฟล์วิดีโอทันที
              </p>
            </div>

            <div className="p-4 bg-white border border-white/20 rounded-2xl inline-block shadow-2xl mx-auto">
              <QRCodeSVG 
                value={mobileUrl}
                size={180}
                level="M"
                includeMargin={false}
              />
            </div>

            <div className="p-3 bg-black/40 rounded-2xl border border-white/[0.08] space-y-2">
              <div className="flex items-center justify-between gap-2 text-xs text-slate-300">
                <span className="font-bold">🌐 ลิงก์สำหรับเข้าผ่าน Wi-Fi:</span>
                <span className="text-[10px] text-[#25F4EE] flex items-center gap-1 font-mono">
                  <Wifi className="w-3 h-3" /> เชื่อมต่อ Wi-Fi เดียวกัน
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={mobileUrl}
                  className="w-full py-2 px-3 rounded-xl bg-black/50 border border-white/[0.1] text-xs font-mono text-white select-all focus:outline-none"
                />
                <button
                  onClick={copyMobileLink}
                  className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-bold flex items-center gap-1.5 transition-all flex-shrink-0 cursor-pointer shadow-md"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-slate-950" />
                      <span>คัดลอกแล้ว</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-slate-950" />
                      <span>คัดลอก</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="text-left text-xs text-slate-400 bg-black/30 border border-white/[0.06] p-3.5 rounded-2xl space-y-1">
              <div className="font-bold text-white">วิธีใช้งานง่ายๆ:</div>
              <ol className="list-decimal list-inside space-y-0.5 text-slate-300">
                <li>เชื่อมต่อมือถือเข้า Wi-Fi เดียวกับคอมพิวเตอร์เครื่องนี้</li>
                <li>เปิดกล้องมือถือสแกน QR Code ด้านบน</li>
                <li>เลือกวิดีโอที่ถ่ายไว้เพื่ออัปโหลดเข้าโปรแกรมทันที</li>
              </ol>
            </div>

            <button
              onClick={() => setShowMobileModal(false)}
              className="w-full py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 text-xs font-bold border border-white/[0.08] transition-colors cursor-pointer"
            >
              ปิดหน้าต่าง
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
