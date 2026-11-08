import React, { useState, Suspense, lazy } from 'react';
import { MobileShell } from './MobileShell.jsx';
import IntakeScreen from './IntakeScreen.jsx';
import { ReviewQueue } from './ReviewQueue.jsx';
import MobilePostNext from './MobilePostNext.jsx';
import { MobileClipLibrary } from './MobileClipLibrary.jsx';
import CommandCenter from './CommandCenter.jsx';
import UploadTray from './UploadTray.jsx';
import LoadingSpinner from '../LoadingSpinner.jsx';

// Lazy-load classic studio & settings if requested from More menu
const MobileQuickStudio = lazy(() => import('../MobileQuickStudio.jsx'));
const SystemSettings = lazy(() => import('../SystemSettings.jsx'));

export function MobileAppRoot({ onSwitchToDesktop, onOpenFilmingSession }) {
  const [subView, setSubView] = useState(null); // 'library' | 'command' | 'settings' | 'classic_studio' | null
  const [trayOpen, setTrayOpen] = useState(false);

  const handleNavigateMoreAction = (actionId) => {
    if (actionId === 'library') {
      setSubView('library');
    } else if (actionId === 'command') {
      setSubView('command');
    } else if (actionId === 'settings') {
      setSubView('settings');
    } else if (actionId === 'classic_studio') {
      setSubView('classic_studio');
    } else if (actionId === 'exit_mobile' && typeof onSwitchToDesktop === 'function') {
      onSwitchToDesktop();
    }
  };

  if (subView === 'library') {
    return (
      <div className="flex h-full w-full flex-col bg-[#0A0D14]">
        <div className="flex min-h-[52px] items-center justify-between border-b border-white/[0.08] px-4 pt-[max(env(safe-area-inset-top,0px),8px)] pb-2 bg-[#0A0D14]/95 backdrop-blur-md">
          <span className="text-sm font-bold text-white">คลังคลิปวิดีโอ</span>
          <button
            type="button"
            onClick={() => setSubView(null)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-white/[0.08] active:scale-95 transition"
          >
            กลับสู่เมนูหลัก
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 pb-[max(env(safe-area-inset-bottom,0px),16px)]">
          <MobileClipLibrary />
        </div>
      </div>
    );
  }

  if (subView === 'command') {
    return (
      <div className="flex h-full w-full flex-col bg-[#0A0D14]">
        <div className="flex min-h-[52px] items-center justify-between border-b border-white/[0.08] px-4 pt-[max(env(safe-area-inset-top,0px),8px)] pb-2 bg-[#0A0D14]/95 backdrop-blur-md">
          <span className="text-sm font-bold text-white">สั่งงาน AI (Command Center)</span>
          <button
            type="button"
            onClick={() => setSubView(null)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-white/[0.08] active:scale-95 transition"
          >
            กลับสู่เมนูหลัก
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 pb-[max(env(safe-area-inset-bottom,0px),16px)]">
          <CommandCenter />
        </div>
      </div>
    );
  }

  if (subView === 'settings') {
    return (
      <div className="flex h-full w-full flex-col bg-[#0A0D14]">
        <div className="flex min-h-[52px] items-center justify-between border-b border-white/[0.08] px-4 pt-[max(env(safe-area-inset-top,0px),8px)] pb-2 bg-[#0A0D14]/95 backdrop-blur-md">
          <span className="text-sm font-bold text-white">ตั้งค่าระบบ</span>
          <button
            type="button"
            onClick={() => setSubView(null)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-white/[0.08] active:scale-95 transition"
          >
            กลับสู่เมนูหลัก
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 pb-[max(env(safe-area-inset-bottom,0px),16px)]">
          <Suspense fallback={<LoadingSpinner message="กำลังโหลดการตั้งค่า..." />}>
            <SystemSettings />
          </Suspense>
        </div>
      </div>
    );
  }

  if (subView === 'classic_studio') {
    return (
      <div className="flex h-full w-full flex-col bg-[#0A0D14]">
        <div className="flex min-h-[52px] items-center justify-between border-b border-white/[0.08] px-4 pt-[max(env(safe-area-inset-top,0px),8px)] pb-2 bg-[#0A0D14]/95 backdrop-blur-md">
          <span className="text-sm font-bold text-white">สตูดิโอดั้งเดิม (Classic MQS)</span>
          <button
            type="button"
            onClick={() => setSubView(null)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-white/[0.08] active:scale-95 transition"
          >
            กลับสู่เมนูหลัก
          </button>
        </div>
        <div className="flex-1 overflow-y-auto pb-[max(env(safe-area-inset-bottom,0px),16px)]">
          <Suspense fallback={<LoadingSpinner message="กำลังเปิด Classic Studio..." />}>
            <MobileQuickStudio
              onSwitchToDesktop={onSwitchToDesktop}
              onOpenFilmingSession={onOpenFilmingSession}
            />
          </Suspense>
        </div>
      </div>
    );
  }

  return (
    <>
      <MobileShell
        onExitMobile={onSwitchToDesktop}
        onNavigateMoreAction={handleNavigateMoreAction}
        renderCreate={() => (
          <div className="flex flex-col gap-4 pb-12">
            <IntakeScreen />
            <div className="border-t border-white/[0.08] pt-4 text-center">
              <button
                type="button"
                onClick={() => setSubView('classic_studio')}
                className="inline-flex min-h-[44px] items-center justify-center px-4 py-2 text-xs text-slate-400 underline decoration-slate-600 hover:text-slate-300 active:scale-95 transition"
              >
                สลับไปใช้สตูดิโอแบบเดิม (โหมดอัปโหลดฟุตเทจตัดต่อ)
              </button>
            </div>
          </div>
        )}
        renderReview={() => <ReviewQueue />}
        renderPost={() => <MobilePostNext />}
      />
      {trayOpen && (
        <UploadTray
          uploads={[]}
          onClose={() => setTrayOpen(false)}
        />
      )}
    </>
  );
}

export default MobileAppRoot;
