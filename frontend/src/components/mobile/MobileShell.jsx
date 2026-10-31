import React, { useState, useEffect, useCallback } from 'react';
import {
  CalendarCheck,
  PlusSquare,
  CheckSquare,
  Send,
  MoreHorizontal,
  Film,
  Sparkles,
  Terminal,
  Settings,
  Monitor,
} from 'lucide-react';
import { TodayScreen } from './TodayScreen.jsx';
import { ServerSleepingBanner } from './ServerSleepingBanner.jsx';

export const MOBILE_TABS = Object.freeze([
  { id: 'today', label: 'วันนี้', icon: CalendarCheck },
  { id: 'create', label: 'สร้าง', icon: PlusSquare },
  { id: 'review', label: 'ตรวจ', icon: CheckSquare },
  { id: 'post', label: 'โพสต์', icon: Send },
  { id: 'more', label: 'อื่นๆ', icon: MoreHorizontal },
]);

export const VALID_MOBILE_TAB_IDS = Object.freeze(MOBILE_TABS.map((t) => t.id));

export function normalizeMobileTab(raw) {
  if (typeof raw !== 'string') return null;
  const trimmed = raw.trim().toLowerCase();
  return VALID_MOBILE_TAB_IDS.includes(trimmed) ? trimmed : null;
}

export function readMobileTabFromSearch(search = '') {
  try {
    const params = new URLSearchParams(search);
    return normalizeMobileTab(params.get('tab'));
  } catch {
    return null;
  }
}

export function buildMobileTabUrl(href = '/', tab = 'today') {
  const normalized = normalizeMobileTab(tab) || 'today';
  const url = new URL(href, 'http://local.invalid');
  url.searchParams.set('tab', normalized);
  return `${url.pathname}${url.search}${url.hash}`;
}

export function MobileShell({
  activeTab: controlledTab,
  initialTab = 'today',
  onTabChange,
  badges = {},
  todoCounts = {},
  jobs = [],
  health = {},
  serverStatus = 'online',
  lastSeenAt = null,
  onRetryServer,
  renderToday,
  renderCreate,
  renderReview,
  renderPost,
  renderMore,
  onNavigateMoreAction,
  onExitMobile,
  win = typeof window !== 'undefined' ? window : null,
}) {
  const isControlled = controlledTab !== undefined && controlledTab !== null;

  const [internalTab, setInternalTab] = useState(() => {
    if (isControlled) {
      return normalizeMobileTab(controlledTab) || 'today';
    }
    const fromUrl = win?.location ? readMobileTabFromSearch(win.location.search) : null;
    return fromUrl || normalizeMobileTab(initialTab) || 'today';
  });

  const currentTab = isControlled
    ? normalizeMobileTab(controlledTab) || 'today'
    : internalTab;

  const syncUrlTab = useCallback(
    (nextTab, replace = false) => {
      if (!win?.history || !win?.location) return;
      try {
        const currentInUrl = readMobileTabFromSearch(win.location.search);
        if (currentInUrl === nextTab && !replace) return;
        const nextUrl = buildMobileTabUrl(win.location.href, nextTab);
        const state = {
          ...(win.history.state && typeof win.history.state === 'object' ? win.history.state : {}),
          omnicutMobileTab: nextTab,
        };
        if (replace) {
          win.history.replaceState(state, '', nextUrl);
        } else {
          win.history.pushState(state, '', nextUrl);
        }
      } catch {
        // Ignore history errors in restricted environments
      }
    },
    [win]
  );

  // Ensure initial URL has ?tab= synced on mount
  useEffect(() => {
    if (!win?.location) return;
    const inUrl = readMobileTabFromSearch(win.location.search);
    if (!inUrl) {
      syncUrlTab(currentTab, true);
    }
  }, [win, currentTab, syncUrlTab]);

  // Listen to browser back/forward (popstate)
  useEffect(() => {
    if (!win || typeof win.addEventListener !== 'function') return undefined;
    const handlePopState = () => {
      const fromUrl = readMobileTabFromSearch(win.location?.search || '') || 'today';
      if (!isControlled) {
        setInternalTab(fromUrl);
      }
      if (typeof onTabChange === 'function') {
        onTabChange(fromUrl);
      }
    };
    win.addEventListener('popstate', handlePopState);
    return () => {
      if (typeof win.removeEventListener === 'function') {
        win.removeEventListener('popstate', handlePopState);
      }
    };
  }, [win, isControlled, onTabChange]);

  const handleSelectTab = useCallback(
    (tabId) => {
      const normalized = normalizeMobileTab(tabId);
      if (!normalized) return;
      syncUrlTab(normalized, false);
      if (!isControlled) {
        setInternalTab(normalized);
      }
      if (typeof onTabChange === 'function') {
        onTabChange(normalized);
      }
    },
    [isControlled, onTabChange, syncUrlTab]
  );

  const handleMoreAction = (actionId) => {
    if (actionId === 'exit_mobile' && typeof onExitMobile === 'function') {
      onExitMobile();
      return;
    }
    if (typeof onNavigateMoreAction === 'function') {
      onNavigateMoreAction(actionId);
      return;
    }
    if (actionId === '/agy' && win?.location) {
      win.location.href = '/agy';
    }
  };

  const renderMoreSection = () => {
    if (typeof renderMore === 'function') {
      return renderMore({
        onNavigateTab: handleSelectTab,
        onNavigateMoreAction: handleMoreAction,
        onExitMobile,
      });
    }

    return (
      <div className="flex flex-col gap-3 pb-6" data-testid="mobile-more-menu">
        <h2 className="text-base font-bold text-white">เมนูเพิ่มเติม</h2>

        <button
          type="button"
          onClick={() => handleMoreAction('library')}
          data-testid="more-action-library"
          className="flex min-h-11 w-full items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-left text-sm font-bold text-white transition hover:bg-white/[0.08]"
        >
          <Film className="h-5 w-5 shrink-0 text-[#25F4EE]" aria-hidden="true" />
          <span>เปิดคลังคลิป</span>
        </button>

        <button
          type="button"
          onClick={() => handleMoreAction('command')}
          data-testid="more-action-command"
          className="flex min-h-11 w-full items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-left text-sm font-bold text-white transition hover:bg-white/[0.08]"
        >
          <Sparkles className="h-5 w-5 shrink-0 text-amber-400" aria-hidden="true" />
          <span>สั่งงาน AI</span>
        </button>

        <button
          type="button"
          onClick={() => handleMoreAction('/agy')}
          data-testid="more-action-agy"
          className="flex min-h-11 w-full items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-left text-sm font-bold text-white transition hover:bg-white/[0.08]"
        >
          <Terminal className="h-5 w-5 shrink-0 text-emerald-400" aria-hidden="true" />
          <span>เปิด AGY Terminal</span>
        </button>

        <button
          type="button"
          onClick={() => handleMoreAction('settings')}
          data-testid="more-action-settings"
          className="flex min-h-11 w-full items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-left text-sm font-bold text-white transition hover:bg-white/[0.08]"
        >
          <Settings className="h-5 w-5 shrink-0 text-slate-300" aria-hidden="true" />
          <span>ตั้งค่าระบบ</span>
        </button>

        <button
          type="button"
          onClick={() => {
            if (typeof onExitMobile === 'function') {
              onExitMobile();
            } else {
              handleMoreAction('exit_mobile');
            }
          }}
          data-testid="more-action-desktop"
          className="flex min-h-11 w-full items-center gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-left text-sm font-bold text-rose-200 transition hover:bg-rose-500/20"
        >
          <Monitor className="h-5 w-5 shrink-0 text-rose-300" aria-hidden="true" />
          <span>สลับไปโหมดเดสก์ท็อป</span>
        </button>
      </div>
    );
  };

  const renderActiveContent = () => {
    switch (currentTab) {
      case 'today':
        return typeof renderToday === 'function' ? (
          renderToday({ onNavigateTab: handleSelectTab })
        ) : (
          <TodayScreen
            onNavigateTab={handleSelectTab}
            jobs={jobs}
            todoCounts={todoCounts}
            health={health}
          />
        );
      case 'create':
        return typeof renderCreate === 'function' ? (
          renderCreate({ onNavigateTab: handleSelectTab })
        ) : (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-sm text-slate-300" data-testid="mobile-tab-create-default">
            สร้าง 20 คลิปจากลิงก์สินค้า
          </div>
        );
      case 'review':
        return typeof renderReview === 'function' ? (
          renderReview({ onNavigateTab: handleSelectTab })
        ) : (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-sm text-slate-300" data-testid="mobile-tab-review-default">
            คิวตรวจคลิปก่อนโพสต์
          </div>
        );
      case 'post':
        return typeof renderPost === 'function' ? (
          renderPost({ onNavigateTab: handleSelectTab })
        ) : (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-sm text-slate-300" data-testid="mobile-tab-post-default">
            คิวโพสต์คลิปถัดไป
          </div>
        );
      case 'more':
        return renderMoreSection();
      default:
        return null;
    }
  };

  return (
    <div
      data-oc-surface="workspace"
      className="flex min-h-dvh w-full flex-col bg-[#07090E] text-slate-100"
      data-testid="mobile-shell"
      data-active-tab={currentTab}
    >
      {/* Top Status / Server Sleeping Alert */}
      {(serverStatus === 'sleeping' || serverStatus === 'offline') && (
        <div className="px-4 pt-3">
          <ServerSleepingBanner
            status={serverStatus}
            lastSeenAt={lastSeenAt}
            onRetry={onRetryServer}
          />
        </div>
      )}

      {/* Main Content Area */}
      <main
        className="flex-1 overflow-y-auto px-4 pt-4"
        style={{ paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 0px))' }}
      >
        {renderActiveContent()}
      </main>

      {/* Bottom 5-Tab Navigation Bar */}
      <nav
        aria-label="เมนูหลักมือถือ"
        data-oc-surface="shell"
        data-testid="mobile-bottom-nav"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-[#07090E]/95 backdrop-blur-md"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <div className="mx-auto grid max-w-lg grid-cols-5 gap-1 px-2 py-1">
          {MOBILE_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = currentTab === tab.id;
            const badgeCount = Number(badges?.[tab.id] ?? 0);

            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                data-testid={`mobile-tab-${tab.id}`}
                onClick={() => handleSelectTab(tab.id)}
                className={`oc-ui-nav-item ${isActive ? 'oc-ui-nav-active' : ''} relative flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl px-1 py-1.5 text-xs font-bold transition ${
                  isActive
                    ? 'bg-white/[0.08] text-[#25F4EE]'
                    : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200'
                }`}
              >
                <div className="relative flex items-center justify-center">
                  <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                  {badgeCount > 0 && (
                    <span
                      data-testid={`mobile-tab-badge-${tab.id}`}
                      className="absolute -right-3 -top-1.5 inline-flex min-w-[18px] items-center justify-center rounded-full bg-[#FE2C55] px-1 text-[10px] font-extrabold leading-4 text-white"
                    >
                      {badgeCount > 99 ? '99+' : badgeCount}
                    </span>
                  )}
                </div>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

export default MobileShell;
