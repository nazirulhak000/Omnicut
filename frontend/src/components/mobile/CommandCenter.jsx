import React, { useEffect, useRef, useState } from 'react';

const QUICK_CHIPS = [
  { id: 'produce_couple_20', label: 'ผลิต 20 คลิปจากลิงก์นี้', prompt: 'ผลิต 20 คลิปจากลิงก์นี้' },
  { id: 'check_status', label: 'สถานะงาน', prompt: 'สถานะงาน' },
  { id: 'rerender_clip', label: 'เรนเดอร์ใหม่คลิป s07', prompt: 'เรนเดอร์ใหม่คลิป s07' },
  { id: 'post_next', label: 'โพสต์คลิปถัดไป', prompt: 'โพสต์คลิปถัดไป' },
  { id: 'system_health', label: 'เช็กระบบ', prompt: 'เช็กระบบ' },
];

const POWER_KEYS = [
  { id: 'esc', label: 'Esc', seq: '\x1b' },
  { id: 'tab', label: 'Tab', seq: '\t' },
  { id: 'ctrl', label: 'Ctrl', sticky: true },
  { id: 'up', label: 'ขึ้น', seq: '\x1b[A' },
  { id: 'down', label: 'ลง', seq: '\x1b[B' },
  { id: 'left', label: 'ซ้าย', seq: '\x1b[D' },
  { id: 'right', label: 'ขวา', seq: '\x1b[C' },
  { id: 'ctrl_c', label: 'Ctrl+C', seq: '\x03' },
  { id: 'paste', label: 'วาง', action: 'paste' },
];

export default function CommandCenter({ productCode = null, onSendTerminalKey = null }) {
  const [prompt, setPrompt] = useState('');
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [plan, setPlan] = useState(null);
  const [jobCard, setJobCard] = useState(null);
  const [aiStatus, setAiStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // Destructive confirmation bottom sheet (1.5s hold or explicit confirm after hold)
  const [showConfirmSheet, setShowConfirmSheet] = useState(false);
  const [holdProgress, setHoldProgress] = useState(0);
  const [holdUnlocked, setHoldUnlocked] = useState(false);
  const holdTimerRef = useRef(null);

  // Power Terminal Mode & visualViewport keyboard anchoring
  const [showPowerToolbar, setShowPowerToolbar] = useState(false);
  const [ctrlSticky, setCtrlSticky] = useState(false);
  const [keyboardOffset, setKeyboardOffset] = useState(0);

  useEffect(() => {
    let mounted = true;
    fetch('/api/settings/ai', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (mounted && data) setAiStatus(data);
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.visualViewport) return undefined;
    const vp = window.visualViewport;
    const handleViewportChange = () => {
      const offsetBottom = Math.max(0, window.innerHeight - (vp.height + vp.offsetTop));
      setKeyboardOffset(offsetBottom);
    };
    vp.addEventListener('resize', handleViewportChange);
    vp.addEventListener('scroll', handleViewportChange);
    handleViewportChange();
    return () => {
      vp.removeEventListener('resize', handleViewportChange);
      vp.removeEventListener('scroll', handleViewportChange);
    };
  }, []);

  const requestPlan = async (inputPrompt) => {
    const clean = (inputPrompt ?? prompt).trim();
    if (!clean) {
      setErrorMessage('กรุณาพิมพ์คำสั่งหรือแตะปุ่มทางลัดด้านบน');
      return;
    }
    setLoadingPlan(true);
    setErrorMessage('');
    setPlan(null);
    setShowConfirmSheet(false);
    setHoldProgress(0);
    setHoldUnlocked(false);

    try {
      const res = await fetch('/api/command/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          prompt: clean,
          product_code: productCode,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `สร้างแผนงานไม่สำเร็จ (${res.status})`);
      }
      const data = await res.json();
      setPlan(data);
    } catch (err) {
      setErrorMessage(err?.message || 'ไม่สามารถสร้างแผนงานได้ในขณะนี้');
    } finally {
      setLoadingPlan(false);
    }
  };

  const executePlan = async (confirmedToken = null) => {
    if (!plan) return;
    if (plan.requires_confirmation && !confirmedToken) {
      setShowConfirmSheet(true);
      setHoldProgress(0);
      setHoldUnlocked(false);
      return;
    }

    setExecuting(true);
    setErrorMessage('');
    try {
      const res = await fetch('/api/command/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          plan_id: plan.plan_id,
          intent: plan.intent,
          params: plan.params || {},
          confirm_token: confirmedToken,
        }),
      });

      if (res.status === 409) {
        setShowConfirmSheet(true);
        setExecuting(false);
        return;
      }

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `สั่งรันงานไม่สำเร็จ (${res.status})`);
      }

      const data = await res.json();
      setJobCard(data);
      setPlan(null);
      setShowConfirmSheet(false);
    } catch (err) {
      setErrorMessage(err?.message || 'เกิดข้อผิดพลาดระหว่างสั่งงาน');
    } finally {
      setExecuting(false);
    }
  };

  const startHoldConfirm = () => {
    if (holdUnlocked) return;
    const startTime = Date.now();
    const duration = 1500; // 1.5s hold required for destructive actions
    clearInterval(holdTimerRef.current);
    holdTimerRef.current = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const pct = Math.min(100, Math.round((elapsed / duration) * 100));
      setHoldProgress(pct);
      if (pct >= 100) {
        clearInterval(holdTimerRef.current);
        setHoldUnlocked(true);
      }
    }, 50);
  };

  const cancelHoldConfirm = () => {
    clearInterval(holdTimerRef.current);
    if (!holdUnlocked) {
      setHoldProgress(0);
    }
  };

  const handlePowerKey = async (keyDef) => {
    if (keyDef.sticky) {
      setCtrlSticky((prev) => !prev);
      return;
    }
    if (keyDef.action === 'paste') {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.readText) {
        try {
          const clipText = await navigator.clipboard.readText();
          if (clipText) {
            setPrompt((prev) => (prev ? `${prev} ${clipText}` : clipText));
            if (onSendTerminalKey) onSendTerminalKey(clipText);
          }
        } catch (_err) {
          setErrorMessage('ไม่สามารถอ่านคลิปบอร์ดได้ กรุณากดวางในช่องข้อความโดยตรง');
        }
      }
      return;
    }
    if (onSendTerminalKey && keyDef.seq) {
      onSendTerminalKey(keyDef.seq, { ctrlSticky });
    }
    if (ctrlSticky) {
      setCtrlSticky(false);
    }
  };

  return (
    <div data-oc-surface="workspace" className="flex min-h-0 flex-1 flex-col bg-slate-950 text-slate-100">
      {/* Top AI Status Strip */}
      <div data-oc-surface="data" className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 bg-slate-900/80 px-4 py-2.5 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-white">ศูนย์สั่งงาน AI</span>
          <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-0.5 text-slate-300">
            {aiStatus ? `คีย์พร้อมใช้ ${aiStatus.key_count} ชุด` : 'ไม่ทราบสถานะคีย์'}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setShowPowerToolbar((prev) => !prev)}
          className="min-h-[44px] min-w-[44px] rounded-xl border border-slate-700 bg-slate-800 px-3 text-xs font-medium text-slate-200 active:bg-slate-700"
        >
          {showPowerToolbar ? 'ซ่อนแถบปุ่มเทอร์มินัล' : 'เปิดแถบปุ่มเทอร์มินัล'}
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4 pb-32">
        {/* Quick Action Chips (44px height) */}
        <section aria-label="คำสั่งด่วน">
          <p className="mb-2 text-xs font-medium text-slate-400">เลือกคำสั่งด่วน</p>
          <div className="flex flex-wrap gap-2">
            {QUICK_CHIPS.map((chip) => (
              <button
                key={chip.id}
                type="button"
                onClick={() => {
                  setPrompt(chip.prompt);
                  requestPlan(chip.prompt);
                }}
                className="min-h-[44px] rounded-xl border border-slate-700/90 bg-slate-900 px-3.5 py-2 text-sm font-medium text-slate-100 active:bg-slate-800"
              >
                {chip.label}
              </button>
            ))}
          </div>
        </section>

        {/* Natural Language Input Form (16px font to prevent iOS auto-zoom) */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            requestPlan(prompt);
          }}
          className="space-y-2.5 rounded-2xl border border-slate-800 bg-slate-900/70 p-3.5"
        >
          <label htmlFor="command-center-input" className="block text-xs font-medium text-slate-300">
            สั่งงานด้วยภาษาไทยหรือวางลิงก์สินค้า
          </label>
          <div className="flex items-center gap-2">
            <input
              id="command-center-input"
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="เช่น ผลิต 20 คลิปจากลิงก์นี้ หรือ เรนเดอร์ใหม่คลิป s07"
              className="min-h-[44px] flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3.5 text-[16px] text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loadingPlan}
              className="min-h-[44px] min-w-[88px] shrink-0 rounded-xl bg-sky-500 px-4 text-sm font-semibold text-slate-950 disabled:opacity-50"
            >
              {loadingPlan ? 'กำลังวางแผน' : 'ดูแผนงาน'}
            </button>
          </div>
        </form>

        {errorMessage && (
          <div
            role="alert"
            className="rounded-xl border border-rose-500/40 bg-rose-950/50 px-4 py-3 text-sm text-rose-200"
          >
            {errorMessage}
          </div>
        )}

        {/* Plan Preview Card */}
        {plan && (
          <section
            aria-label="การ์ดตรวจสอบแผนงาน"
            className="rounded-2xl border border-sky-500/40 bg-slate-900 p-4 shadow-lg"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="inline-block rounded-full bg-sky-500/20 px-2.5 py-0.5 text-xs font-medium text-sky-300">
                  แผนการทำงาน ({plan.intent})
                </span>
                <h3 className="mt-1.5 text-base font-bold text-white">{plan.title}</h3>
              </div>
              {plan.destructive && (
                <span className="rounded-full border border-rose-500/50 bg-rose-500/20 px-2.5 py-0.5 text-xs font-semibold text-rose-300">
                  ต้องยืนยันก่อนทำ
                </span>
              )}
            </div>

            <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-sm text-slate-300">
              {(plan.steps || []).map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>

            <div className="mt-4 flex items-center gap-2.5">
              <button
                type="button"
                disabled={executing}
                onClick={() => executePlan(null)}
                className="min-h-[44px] flex-1 rounded-xl bg-emerald-500 px-4 text-sm font-bold text-slate-950 active:bg-emerald-400 disabled:opacity-50"
              >
                {executing ? 'กำลังส่งคำสั่ง' : 'เริ่มทำงานตามแผน'}
              </button>
              <button
                type="button"
                disabled={executing}
                onClick={() => {
                  setPlan(null);
                  setShowConfirmSheet(false);
                }}
                className="min-h-[44px] min-w-[88px] rounded-xl border border-slate-700 bg-slate-800 px-4 text-sm font-semibold text-slate-200 active:bg-slate-700"
              >
                ยกเลิก
              </button>
            </div>
          </section>
        )}

        {/* Active / Completed Job Card */}
        {jobCard && (
          <section
            aria-label="สถานะงานล่าสุด"
            className="rounded-2xl border border-emerald-500/30 bg-slate-900/90 p-4"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-white">รหัสงาน: {jobCard.job_id}</span>
              <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-medium text-emerald-300">
                {jobCard.status === 'completed' ? 'เสร็จสมบูรณ์' : 'อยู่ในคิวทำงาน'}
              </span>
            </div>
            <p className="mt-1.5 text-sm text-slate-300">{jobCard.message}</p>
          </section>
        )}
      </div>

      {/* Destructive Action Confirmation Bottom Sheet (1.5s Hold) */}
      {showConfirmSheet && plan && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="ยืนยันการล้างข้อมูลชั่วคราว"
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-3 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl border border-rose-500/40 bg-slate-900 p-5 shadow-2xl">
            <h4 className="text-base font-bold text-white">ยืนยันการดำเนินการที่มีผลลบไฟล์</h4>
            <p className="mt-1.5 text-sm text-slate-300">
              เป้าหมาย: <span className="font-mono text-rose-300">{plan.params?.target || plan.title}</span>
            </p>
            <p className="mt-1 text-xs text-slate-400">
              กรุณากดปุ่มด้านล่างค้างไว้ 1.5 วินาทีเพื่อปลดล็อก แล้วกดยืนยันเริ่มงาน
            </p>

            <div className="mt-4 space-y-2.5">
              <button
                type="button"
                onMouseDown={startHoldConfirm}
                onMouseUp={cancelHoldConfirm}
                onMouseLeave={cancelHoldConfirm}
                onTouchStart={startHoldConfirm}
                onTouchEnd={cancelHoldConfirm}
                className="relative min-h-[44px] w-full overflow-hidden rounded-xl border border-rose-500/50 bg-slate-800 px-4 text-sm font-semibold text-rose-200"
              >
                <span
                  className="absolute inset-y-0 left-0 bg-rose-600/40 transition-all duration-75"
                  style={{ width: `${holdProgress}%` }}
                />
                <span className="relative z-10">
                  {holdUnlocked
                    ? 'ปลดล็อกเรียบร้อยแล้ว'
                    : `กดค้าง 1.5 วินาทีเพื่อปลดล็อก (${holdProgress}%)`}
                </span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={!holdUnlocked || executing}
                  onClick={() => executePlan(plan.confirm_token)}
                  className="min-h-[44px] flex-1 rounded-xl bg-rose-500 px-4 text-sm font-bold text-white disabled:opacity-40"
                >
                  ยืนยันการล้างไฟล์
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowConfirmSheet(false);
                    setHoldProgress(0);
                    setHoldUnlocked(false);
                  }}
                  className="min-h-[44px] min-w-[88px] rounded-xl border border-slate-700 bg-slate-800 px-4 text-sm font-semibold text-slate-200"
                >
                  ปิดหน้าต่าง
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Collapsible Power Terminal Toolbar Anchored Above Mobile Keyboard */}
      {showPowerToolbar && (
        <div
          aria-label="แถบปุ่มพิเศษเทอร์มินัล"
          style={{ bottom: `${keyboardOffset}px` }}
          className="fixed inset-x-0 z-30 border-t border-slate-800 bg-slate-900/95 px-2 py-1.5 backdrop-blur-md"
        >
          <div className="flex items-center gap-1.5 overflow-x-auto">
            {POWER_KEYS.map((k) => {
              const isActiveSticky = k.sticky && ctrlSticky;
              return (
                <button
                  key={k.id}
                  type="button"
                  onClick={() => handlePowerKey(k)}
                  className={`min-h-[44px] min-w-[44px] shrink-0 rounded-lg border px-2.5 text-xs font-semibold ${
                    isActiveSticky
                      ? 'border-sky-400 bg-sky-500 text-slate-950'
                      : 'border-slate-700 bg-slate-800 text-slate-200 active:bg-slate-700'
                  }`}
                >
                  {k.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
