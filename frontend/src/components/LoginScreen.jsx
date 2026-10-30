import React, { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from 'react';
import { Eye, EyeOff, Loader2, Lock, RefreshCw, Sparkles, WifiOff } from 'lucide-react';
import {
  getAuthMe, loginWithPassword, logout as logoutRequest,
  LOGIN_REQUIRED_EVENT, AUTH_RESTORED_EVENT,
} from '../api';
import { readSafeNext, stripLoginParams } from '../lib/appNav.js';

// ── Auth state shared with the shell (Sidebar "ออกจากระบบ", mobile studio) ──
const AuthContext = createContext({ authRequired: false, authenticated: true, logout: async () => {} });

/** { authRequired, authenticated, logout } -- logout clears the cookie and returns to the login screen. */
export function useAuth() {
  return useContext(AuthContext);
}

function loginErrorMessage(error) {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;
  if (status === 401) return typeof detail === 'string' && detail ? detail : 'รหัสผ่านไม่ถูกต้อง';
  if (status === 429) {
    return typeof detail === 'string' && detail
      ? detail
      : 'ลองหลายครั้งเกินไป กรุณารอสักครู่แล้วลองใหม่';
  }
  if (status === 503) {
    return typeof detail === 'string' && detail
      ? detail
      : 'ยังไม่ได้ตั้งรหัสผ่านแอปบนเซิร์ฟเวอร์ กรุณาตั้งค่าก่อนเข้าใช้งาน';
  }
  if (!error?.response) return 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจสอบอินเทอร์เน็ตหรือสถานะ Colab แล้วลองใหม่';
  return typeof detail === 'string' && detail ? detail : `เข้าสู่ระบบไม่สำเร็จ (${status})`;
}

function FullScreen({ children, overlay = false }) {
  return (
    <div
      role={overlay ? 'dialog' : undefined}
      aria-modal={overlay ? 'true' : undefined}
      aria-labelledby={overlay ? 'login-title' : undefined}
      className={`${overlay ? 'fixed inset-0 z-[10000]' : 'min-h-dvh'} w-full overflow-y-auto bg-[#07090E] text-slate-100 font-prompt flex items-center justify-center px-4 pt-[max(1.5rem,env(safe-area-inset-top))] pb-[max(1.5rem,env(safe-area-inset-bottom))]`}
    >
      <div className="w-full max-w-sm">{children}</div>
    </div>
  );
}

function BrandMark() {
  return (
    <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center shadow-lg shadow-[#FE2C55]/20 text-white mx-auto">
      <Sparkles className="w-7 h-7" aria-hidden="true" />
    </div>
  );
}

/**
 * Full-screen password login. `notice` explains why it is shown (session
 * expired, password not configured); `onSuccess` runs after the cookie is set.
 */
export default function LoginScreen({ onSuccess, notice = '', overlay = false, passwordConfigured = true }) {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const errorId = useId();
  const noticeId = useId();

  const submit = async (event) => {
    event.preventDefault();
    if (submitting) return;
    if (!password) {
      setError('กรุณาใส่รหัสผ่าน');
      inputRef.current?.focus();
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await loginWithPassword(password);
      setPassword('');
      await onSuccess?.();
    } catch (err) {
      setError(loginErrorMessage(err));
      inputRef.current?.focus();
      inputRef.current?.select?.();
    } finally {
      setSubmitting(false);
    }
  };

  const describedBy = [notice ? noticeId : null, error ? errorId : null].filter(Boolean).join(' ') || undefined;

  return (
    <FullScreen overlay={overlay}>
      <main className="space-y-6" aria-labelledby="login-title">
        <div className="text-center space-y-3">
          <BrandMark />
          <div className="space-y-1">
            <h1 id="login-title" className="text-xl font-bold text-white">เข้าสู่ระบบ OmniCut</h1>
            <p className="text-sm text-slate-400">ใส่รหัสผ่านแอปเพื่อเปิดสตูดิโอ</p>
          </div>
        </div>

        {(notice || !passwordConfigured) && (
          <p
            id={noticeId}
            role="status"
            className="rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200 leading-relaxed"
          >
            {notice || 'ยังไม่ได้ตั้งรหัสผ่านแอปบนเซิร์ฟเวอร์ กรุณาตั้งค่าก่อนเข้าใช้งาน'}
          </p>
        )}

        <form onSubmit={submit} noValidate className="rounded-3xl border border-white/[0.1] bg-[#0D111A] p-5 space-y-4 shadow-2xl">
          {/* Lets iOS Keychain / password managers save the credential pair. */}
          <input type="text" name="username" autoComplete="username" value="omnicut" readOnly tabIndex={-1} aria-hidden="true" className="sr-only" />

          <div className="space-y-2">
            <label htmlFor="omnicut-password" className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Lock className="w-4 h-4 text-[#25F4EE]" aria-hidden="true" />
              รหัสผ่าน
            </label>
            <div className="relative">
              <input
                ref={inputRef}
                id="omnicut-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                enterKeyHint="go"
                value={password}
                onChange={(e) => { setPassword(e.target.value); if (error) setError(''); }}
                aria-invalid={error ? 'true' : 'false'}
                aria-describedby={describedBy}
                disabled={submitting}
                className={`w-full min-h-12 rounded-2xl bg-black/50 border pl-4 pr-14 text-base text-white placeholder:text-slate-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60 disabled:opacity-60 ${error ? 'border-rose-500/70' : 'border-white/[0.12]'}`}
                placeholder="รหัสผ่านแอป"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'ซ่อนรหัสผ่าน' : 'แสดงรหัสผ่าน'}
                aria-pressed={showPassword}
                aria-controls="omnicut-password"
                className="absolute right-1 top-1/2 -translate-y-1/2 w-11 h-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.06] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60 cursor-pointer"
              >
                {showPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
              </button>
            </div>
            {error && (
              <p id={errorId} role="alert" className="text-sm text-rose-300 leading-snug">
                {error}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full min-h-12 rounded-2xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white text-base font-bold flex items-center justify-center gap-2 shadow-lg shadow-[#FE2C55]/20 hover:opacity-95 active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer transition"
          >
            {submitting && <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />}
            <span>{submitting ? 'กำลังเข้าสู่ระบบ' : 'เข้าสู่ระบบ'}</span>
          </button>
        </form>
      </main>
    </FullScreen>
  );
}

function CheckingScreen() {
  return (
    <FullScreen>
      <div className="flex flex-col items-center gap-3 text-slate-400" role="status" aria-live="polite">
        <Loader2 className="w-7 h-7 animate-spin text-[#25F4EE]" aria-hidden="true" />
        <p className="text-sm">กำลังตรวจสอบการเข้าสู่ระบบ</p>
      </div>
    </FullScreen>
  );
}

function UnreachableScreen({ onRetry, retrying }) {
  return (
    <FullScreen>
      <div className="text-center space-y-5">
        <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center justify-center mx-auto">
          <WifiOff className="w-7 h-7" aria-hidden="true" />
        </div>
        <div className="space-y-1.5">
          <h1 className="text-xl font-bold text-white">เชื่อมต่อเซิร์ฟเวอร์ไม่ได้</h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            ตรวจสอบอินเทอร์เน็ต หรือดูว่า Colab ยังทำงานอยู่ แล้วลองเชื่อมต่ออีกครั้ง
          </p>
        </div>
        <button
          type="button"
          onClick={onRetry}
          disabled={retrying}
          className="w-full min-h-12 rounded-2xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.12] text-white text-base font-bold flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
        >
          {retrying ? <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" /> : <RefreshCw className="w-5 h-5" aria-hidden="true" />}
          <span>{retrying ? 'กำลังเชื่อมต่อ' : 'ลองเชื่อมต่ออีกครั้ง'}</span>
        </button>
      </div>
    </FullScreen>
  );
}

function goToNextOrClean() {
  const next = readSafeNext(window.location.search);
  if (next) {
    window.location.replace(next);
    return true;
  }
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.has('login') || params.has('next')) {
      window.history.replaceState(window.history.state, '', stripLoginParams(window.location.href));
    }
  } catch { /* history unavailable */ }
  return false;
}

/**
 * Wraps the whole app. Boot: GET /api/auth/me. Unreachable server -> retry
 * screen (not the login form). Login required -> LoginScreen. A 401
 * {login_required} later in the session (the `omnicut:login-required` event)
 * shows the login screen as an overlay so open, unsaved work stays mounted.
 */
export function AuthGate({ children }) {
  // checking | ready | login | unreachable
  const [phase, setPhase] = useState('checking');
  const [me, setMe] = useState(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const readyRef = useRef(false);

  const check = useCallback(async () => {
    try {
      const data = await getAuthMe();
      setMe(data || null);
      const mustLogin = Boolean(data?.auth_required) && !data?.authenticated;
      if (mustLogin) {
        setPhase('login');
        return;
      }
      // Already signed in: honour /?login=1&next=/agy straight away.
      if (goToNextOrClean()) return;
      readyRef.current = true;
      setPhase('ready');
    } catch (error) {
      const status = error?.response?.status;
      if (status === 401) {
        setPhase('login');
        return;
      }
      if (status === 404 || status === 405) {
        // Backend without the auth module: nothing to log into.
        setMe({ auth_required: false, authenticated: true });
        readyRef.current = true;
        setPhase('ready');
        return;
      }
      setPhase('unreachable');
    }
  }, []);

  useEffect(() => { void check(); }, [check]);

  useEffect(() => {
    const onLoginRequired = () => {
      if (readyRef.current) setSessionExpired(true);
      else setPhase('login');
    };
    window.addEventListener(LOGIN_REQUIRED_EVENT, onLoginRequired);
    return () => window.removeEventListener(LOGIN_REQUIRED_EVENT, onLoginRequired);
  }, []);

  const retry = async () => {
    setRetrying(true);
    try { await check(); } finally { setRetrying(false); }
  };

  const handleLoginSuccess = useCallback(async () => {
    setMe((prev) => ({ ...(prev || {}), authenticated: true }));
    if (goToNextOrClean()) return;
    if (readyRef.current) {
      setSessionExpired(false);
      try { window.dispatchEvent(new CustomEvent(AUTH_RESTORED_EVENT)); } catch { /* ignore */ }
      return;
    }
    readyRef.current = true;
    setPhase('ready');
  }, []);

  const logout = useCallback(async () => {
    try { await logoutRequest(); } catch { /* cookie may already be gone */ }
    window.location.reload();
  }, []);

  const authValue = {
    authRequired: Boolean(me?.auth_required),
    authenticated: Boolean(me?.authenticated) || !me?.auth_required,
    logout,
  };

  if (phase === 'checking') return <CheckingScreen />;
  if (phase === 'unreachable') return <UnreachableScreen onRetry={retry} retrying={retrying} />;
  if (phase === 'login') {
    return (
      <LoginScreen
        onSuccess={handleLoginSuccess}
        passwordConfigured={me?.password_configured !== false}
      />
    );
  }

  return (
    <AuthContext.Provider value={authValue}>
      {children}
      {sessionExpired && (
        <LoginScreen
          overlay
          onSuccess={handleLoginSuccess}
          notice="เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้ง งานที่เปิดค้างไว้ยังอยู่"
        />
      )}
    </AuthContext.Provider>
  );
}
