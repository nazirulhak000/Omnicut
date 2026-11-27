import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  Smartphone, Copy, Check, RefreshCw, Eye, EyeOff, KeyRound,
  ShieldAlert, Download, Loader2, Usb, Globe, Lock
} from 'lucide-react';
import { PopoverPanel } from './ui/PopoverPanel';
import {
  getMobileBridgeStatus,
  toggleMobileBridge,
  getMobileBridgePassword,
  rotateMobileBridgePassword,
} from '../api';

const BRIDGE_MODES = [
  { id: 'lan_https', label: 'Wi-Fi HTTPS :8443' },
  { id: 'tailscale', label: 'Tailscale HTTPS' },
  { id: 'public', label: 'Public URL' },
];

const DEEP_LINK_TARGETS = [
  { id: 'studio', label: 'เปิดสตูดิโอ' },
  { id: 'film', label: 'ถ่ายทำล่าสุด' },
  { id: 'quick-ref', label: 'Quick-Ref' },
];

function buildDeepLinkUrl(baseUrl, targetId, latestSessionId = '') {
  if (!baseUrl) return '';
  const cleanBase = String(baseUrl).replace(/\/+$/, '');
  if (targetId === 'film') {
    const sessionParam = latestSessionId ? `&session=${encodeURIComponent(latestSessionId)}` : '';
    return `${cleanBase}/?film=1${sessionParam}`;
  }
  if (targetId === 'quick-ref') {
    return `${cleanBase}/?view=quick-ref`;
  }
  return `${cleanBase}/`;
}

export default function MobileBridgePopover({
  anchorRef,
  onClose,
  status: externalStatus = null,
  onStatusChange,
  onOpenIPhoneModal,
  latestSessionId = '',
}) {
  const [bridgeStatus, setBridgeStatus] = useState(externalStatus);
  const [loading, setLoading] = useState(!externalStatus);
  const [toggling, setToggling] = useState(false);
  const [refreshingIp, setRefreshingIp] = useState(false);

  const [targetId, setTargetId] = useState('studio');
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copiedPassword, setCopiedPassword] = useState(false);

  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [rotatingPassword, setRotatingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    if (externalStatus) {
      setBridgeStatus(externalStatus);
      setLoading(false);
    }
  }, [externalStatus]);

  const applyStatus = useCallback((next) => {
    setBridgeStatus(next);
    onStatusChange?.(next);
  }, [onStatusChange]);

  const fetchStatus = useCallback(async () => {
    try {
      setActionError('');
      const data = await getMobileBridgeStatus();
      applyStatus(data);
    } catch (err) {
      setActionError(err?.friendlyMessage || 'ไม่สามารถดึงสถานะ Mobile Bridge ได้');
    } finally {
      setLoading(false);
      setRefreshingIp(false);
    }
  }, [applyStatus]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const enabled = Boolean(bridgeStatus?.enabled);
  const activeMode = bridgeStatus?.mode || 'lan_https';
  const baseUrl = bridgeStatus?.urls?.[activeMode] || '';

  const activeUrl = useMemo(
    () => buildDeepLinkUrl(baseUrl, targetId, latestSessionId),
    [baseUrl, targetId, latestSessionId]
  );

  const handleToggleEnabled = async () => {
    if (toggling) return;
    setToggling(true);
    setActionError('');
    try {
      const next = await toggleMobileBridge({ enabled: !enabled, mode: activeMode });
      applyStatus(next);
    } catch (err) {
      setActionError(err?.friendlyMessage || 'สลับสถานะ Mobile Bridge ไม่สำเร็จ');
    } finally {
      setToggling(false);
    }
  };

  const handleSelectMode = async (nextMode) => {
    if (toggling || nextMode === activeMode) return;
    setToggling(true);
    setActionError('');
    try {
      const next = await toggleMobileBridge({ enabled, mode: nextMode });
      applyStatus(next);
    } catch (err) {
      setActionError(err?.friendlyMessage || 'เปลี่ยนโหมดการเชื่อมต่อไม่สำเร็จ');
    } finally {
      setToggling(false);
    }
  };

  const handleRefreshIp = () => {
    if (refreshingIp) return;
    setRefreshingIp(true);
    fetchStatus();
  };

  const handleCopyUrl = async () => {
    if (!activeUrl) return;
    try {
      await navigator.clipboard.writeText(activeUrl);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 1800);
    } catch {
      setActionError('คัดลอกลิงก์ไม่สำเร็จ');
    }
  };

  const ensurePasswordLoaded = async () => {
    if (password) return password;
    setPasswordLoading(true);
    setPasswordError('');
    try {
      const res = await getMobileBridgePassword();
      const val = res?.password || '';
      setPassword(val);
      return val;
    } catch (err) {
      const msg = err?.response?.status === 403
        ? 'ดูรหัสผ่านได้เฉพาะบนเครื่องหลักเท่านั้น'
        : (err?.friendlyMessage || 'ดึงรหัสผ่านไม่สำเร็จ');
      setPasswordError(msg);
      return '';
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleTogglePassword = async () => {
    if (passwordVisible) {
      setPasswordVisible(false);
      return;
    }
    const val = await ensurePasswordLoaded();
    if (val) setPasswordVisible(true);
  };

  const handleCopyPassword = async () => {
    const val = await ensurePasswordLoaded();
    if (!val) return;
    try {
      await navigator.clipboard.writeText(val);
      setCopiedPassword(true);
      setTimeout(() => setCopiedPassword(false), 1800);
    } catch {
      setPasswordError('คัดลอกรหัสไม่สำเร็จ');
    }
  };

  const handleRotatePassword = async () => {
    if (rotatingPassword) return;
    setRotatingPassword(true);
    setPasswordError('');
    try {
      const res = await rotateMobileBridgePassword();
      const nextPw = res?.password || '';
      setPassword(nextPw);
      setPasswordVisible(true);
      fetchStatus();
    } catch (err) {
      setPasswordError(err?.friendlyMessage || 'ตั้งรหัสผ่านใหม่ไม่สำเร็จ');
    } finally {
      setRotatingPassword(false);
    }
  };

  const handleOpenIPhone = () => {
    onClose?.();
    onOpenIPhoneModal?.();
  };

  return (
    <PopoverPanel
      anchorRef={anchorRef}
      onClose={onClose}
      align="end"
      role="dialog"
      aria-label="เชื่อมต่อมือถือ Mobile HTTPS Bridge"
      className="w-[360px] max-w-[94vw] rounded-xl border border-[#23262D] bg-[#14161A] p-3.5 text-[#F4F4F5] shadow-2xl space-y-3"
    >
      {/* ── Header: Title + ON/OFF Switch ── */}
      <div className="flex items-center justify-between pb-2.5 border-b border-[#1E2026]">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-[#1B1D22] border border-[#2B2E36] flex items-center justify-center flex-shrink-0">
            <Smartphone className={`w-3.5 h-3.5 ${enabled ? 'text-[#34D399]' : 'text-[#8E929B]'}`} />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-[#F4F4F5] truncate">Mobile Bridge</div>
            <div className="text-[11px] text-[#8E929B] truncate">
              {enabled ? 'เปิดรับการเชื่อมต่อ HTTPS แล้ว' : 'ปิดการเชื่อมต่อภายนอกอยู่'}
            </div>
          </div>
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label="สลับสถานะ Mobile Bridge"
          disabled={toggling || loading}
          onClick={handleToggleEnabled}
          className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full border px-0.5 cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A] ${
            enabled
              ? 'bg-[#10241D] border-[#1E4D3B]'
              : 'bg-[#1B1D22] border-[#2B2E36]'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 rounded-full transition-transform duration-150 ${
              enabled ? 'translate-x-5 bg-[#34D399]' : 'translate-x-0 bg-[#5C6069]'
            }`}
          />
        </button>
      </div>

      {/* ── Auth Disabled Amber Warning ── */}
      {bridgeStatus?.auth_disabled_warning && (
        <div className="flex items-start gap-2 rounded-lg border border-[#523F1E] bg-[#241D10] px-2.5 py-2 text-[11px] text-[#FBBF24]">
          <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>คำเตือน: ปิดการยืนยันตัวตน (OMNICUT_DISABLE_AUTH) อยู่ ควรเปิดใช้งานเมื่อเชื่อมต่อผ่านเครือข่าย</span>
        </div>
      )}

      {actionError && (
        <div className="rounded-lg border border-[#52232A] bg-[#271417] px-2.5 py-1.5 text-[11px] text-[#F87171]">
          {actionError}
        </div>
      )}

      {/* ── Mode Switcher ── */}
      <div className="grid grid-cols-3 gap-1 rounded-lg bg-[#101114] border border-[#1E2026] p-1">
        {BRIDGE_MODES.map((m) => {
          const isSelected = activeMode === m.id;
          return (
            <button
              key={m.id}
              type="button"
              disabled={toggling}
              onClick={() => handleSelectMode(m.id)}
              className={`px-2 py-1.5 rounded-md text-[11px] font-semibold truncate cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A] ${
                isSelected
                  ? 'bg-[#1B1D22] text-[#F4F4F5] border border-[#2B2E36]'
                  : 'text-[#8E929B] hover:text-[#D4D4D8] border border-transparent'
              }`}
            >
              <span>{m.label}</span>
            </button>
          );
        })}
      </div>

      {/* ── Deep-Link Target Selector ── */}
      <div className="space-y-1">
        <div className="text-[11px] font-medium text-[#8E929B]">ปลายทางเมื่อสแกน QR</div>
        <div className="grid grid-cols-3 gap-1">
          {DEEP_LINK_TARGETS.map((target) => {
            const isSelected = targetId === target.id;
            return (
              <button
                key={target.id}
                type="button"
                onClick={() => setTargetId(target.id)}
                className={`px-2 py-1.5 rounded-lg text-[11px] font-semibold border cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A] ${
                  isSelected
                    ? 'bg-[#131E33] border-[#233B66] text-[#60A5FA]'
                    : 'bg-[#1B1D22] border-[#2B2E36] text-[#D4D4D8] hover:border-[#3A3E4A]'
                }`}
              >
                <span>{target.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── QR Code + URL ── */}
      <div className="rounded-lg border border-[#23262D] bg-[#101114] p-3 space-y-2.5">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-xs text-[#8E929B] gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>กำลังตรวจสอบเครือข่าย...</span>
          </div>
        ) : activeUrl ? (
          <>
            <div className="flex justify-center">
              <div className="p-2.5 bg-white rounded-xl">
                <QRCodeSVG value={activeUrl} size={136} level="M" includeMargin={false} />
              </div>
            </div>

            <div className="flex items-center gap-1.5 rounded-lg border border-[#23262D] bg-[#14161A] px-2.5 py-1.5">
              <Globe className="w-3.5 h-3.5 text-[#8E929B] flex-shrink-0" />
              <span className="font-mono text-[11px] text-[#D4D4D8] truncate select-all flex-1" title={activeUrl}>
                {activeUrl}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleCopyUrl}
                className="flex-1 h-8 px-2.5 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] hover:border-[#3A3E4A] text-xs font-semibold text-[#F4F4F5] flex items-center justify-center gap-1.5 cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
              >
                {copiedUrl ? <Check className="w-3.5 h-3.5 text-[#34D399]" /> : <Copy className="w-3.5 h-3.5 text-[#8E929B]" />}
                <span>{copiedUrl ? 'คัดลอกแล้ว' : 'คัดลอกลิงก์'}</span>
              </button>
              <button
                type="button"
                onClick={handleRefreshIp}
                disabled={refreshingIp}
                className="h-8 px-2.5 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] hover:border-[#3A3E4A] text-xs font-semibold text-[#D4D4D8] hover:text-[#F4F4F5] flex items-center justify-center gap-1.5 cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-[#8E929B] ${refreshingIp ? 'animate-spin' : ''}`} />
                <span>รีเฟรช IP</span>
              </button>
            </div>
          </>
        ) : (
          <div className="py-5 text-center space-y-2">
            <div className="text-xs text-[#8E929B]">
              {activeMode === 'tailscale'
                ? 'ไม่พบ Tailscale HTTPS บนเครื่องนี้'
                : activeMode === 'public'
                ? 'ยังไม่ได้ตั้งค่า OMNICUT_PUBLIC_URL'
                : 'ไม่พบ IP เครือข่ายท้องถิ่น'}
            </div>
            <button
              type="button"
              onClick={handleRefreshIp}
              disabled={refreshingIp}
              className="h-8 px-3 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] text-xs font-semibold text-[#D4D4D8] inline-flex items-center gap-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshingIp ? 'animate-spin' : ''}`} />
              <span>รีเฟรช IP</span>
            </button>
          </div>
        )}
      </div>

      {/* ── Local-only Password Reveal / Copy / Rotate ── */}
      <div className="rounded-lg border border-[#23262D] bg-[#101114] p-2.5 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#8E929B]">
            <Lock className="w-3.5 h-3.5" />
            <span>รหัสผ่านเข้าสู่ระบบ (Local Only)</span>
          </div>
          <span className="font-mono text-xs font-semibold text-[#F4F4F5] tracking-wider">
            {passwordLoading ? '...' : passwordVisible && password ? password : '••••••••'}
          </span>
        </div>

        {passwordError && (
          <div className="text-[11px] text-[#F87171]">{passwordError}</div>
        )}

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleTogglePassword}
            disabled={passwordLoading}
            className="flex-1 h-8 px-2 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] text-[11px] font-semibold text-[#D4D4D8] flex items-center justify-center gap-1 cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
          >
            {passwordVisible ? <EyeOff className="w-3.5 h-3.5 text-[#8E929B]" /> : <Eye className="w-3.5 h-3.5 text-[#8E929B]" />}
            <span>{passwordVisible ? 'ซ่อนรหัสผ่าน' : 'แสดงรหัสผ่าน'}</span>
          </button>
          <button
            type="button"
            onClick={handleCopyPassword}
            disabled={passwordLoading}
            className="h-8 px-2.5 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] text-[11px] font-semibold text-[#D4D4D8] flex items-center justify-center gap-1 cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
          >
            {copiedPassword ? <Check className="w-3.5 h-3.5 text-[#34D399]" /> : <Copy className="w-3.5 h-3.5 text-[#8E929B]" />}
            <span>คัดลอกรหัส</span>
          </button>
          <button
            type="button"
            onClick={handleRotatePassword}
            disabled={rotatingPassword}
            className="h-8 px-2.5 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] text-[11px] font-semibold text-[#D4D4D8] flex items-center justify-center gap-1 cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
          >
            <KeyRound className={`w-3.5 h-3.5 text-[#8E929B] ${rotatingPassword ? 'animate-spin' : ''}`} />
            <span>ตั้งรหัสใหม่</span>
          </button>
        </div>
      </div>

      {/* ── One-time iOS Root CA Helper (LAN HTTPS mode) ── */}
      {activeMode === 'lan_https' && (
        <div className="rounded-lg border border-[#23262D] bg-[#101114] p-2.5 space-y-2">
          <div className="text-[11px] text-[#8E929B] leading-relaxed">
            ติดตั้งใบรับรองครั้งแรกบน iOS: ดาวน์โหลดแล้วไปที่ <span className="text-[#D4D4D8]">Settings → General → VPN &amp; Device Management</span> จากนั้นเปิด Trust ใน <span className="text-[#D4D4D8]">Certificate Trust Settings</span>
          </div>
          <a
            href="/api/mobile-bridge/ca.crt"
            download="OmniCut-Root-CA.crt"
            className="h-8 px-2.5 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] hover:border-[#3A3E4A] text-xs font-semibold text-[#60A5FA] flex items-center justify-center gap-1.5 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
          >
            <Download className="w-3.5 h-3.5" />
            <span>ดาวน์โหลดใบรับรอง CA</span>
          </a>
        </div>
      )}

      {/* ── Footer: USB iPhone Direct Fallback ── */}
      <div className="pt-2 border-t border-[#1E2026]">
        <button
          type="button"
          onClick={handleOpenIPhone}
          className="w-full h-9 px-3 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] hover:border-[#3A3E4A] text-xs font-semibold text-[#D4D4D8] hover:text-[#F4F4F5] flex items-center justify-center gap-1.5 cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
        >
          <Usb className="w-3.5 h-3.5 text-[#60A5FA]" />
          <span>ดึงคลิปจาก iPhone (USB)</span>
        </button>
      </div>
    </PopoverPanel>
  );
}
