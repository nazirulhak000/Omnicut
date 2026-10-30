import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useBackToClose } from '../../hooks/useBackToClose';

const FORBIDDEN_PRICE_RE = /(?:ราคา|โปรโมชั่น|โปรโมชัน|ส่วนลด|บาท|฿|\b\d[\d,]*\s*บ\.)/i;
const FORBIDDEN_ELLIPSIS_RE = /(\.\.\.|…)/;

function validateDisplayLine(text) {
  const clean = String(text || '').trim();
  if (!clean) return 'ข้อความบนจอห้ามว่าง';
  if (FORBIDDEN_PRICE_RE.test(clean)) return 'ห้ามระบุราคาหรือโปรโมชั่นในข้อความแชท';
  if (FORBIDDEN_ELLIPSIS_RE.test(clean)) return 'ห้ามใช้เครื่องหมายจุดไข่ปลา (...)';
  return null;
}

export function ReviewSheet({
  isOpen,
  clip,
  onClose,
  onSaved,
}) {
  useBackToClose(Boolean(isOpen), onClose);

  const [turns, setTurns] = useState([]);
  const [timingOffsetSec, setTimingOffsetSec] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!isOpen || !clip) return;
    const initialTurns = Array.isArray(clip.turns)
      ? clip.turns.map((t, idx) => ({
          index: idx,
          speaker: t.speaker || (idx % 2 === 0 ? 'น้องนุ้ย' : 'พี่บ่าว'),
          display: t.display || '',
          spoken: t.spoken || t.display || '',
          photo: t.photo || null,
        }))
      : [];
    setTurns(initialTurns);
    setTimingOffsetSec(Number(clip.timing_offset_sec || 0));
    setErrorMsg('');
  }, [isOpen, clip]);

  if (!isOpen || !clip) return null;

  const availablePhotos = Array.isArray(clip.available_photos) ? clip.available_photos : [];

  const handleDisplayChange = (index, value) => {
    setTurns((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, display: value } : item))
    );
    setErrorMsg('');
  };

  const handleSelectPhoto = (index, photoUrl) => {
    setTurns((prev) =>
      prev.map((item, idx) =>
        idx === index ? { ...item, photo: item.photo === photoUrl ? null : photoUrl } : item
      )
    );
  };

  const adjustTiming = (delta) => {
    setTimingOffsetSec((prev) => {
      const next = Math.round((prev + delta) * 10) / 10;
      return Math.max(-2.0, Math.min(2.0, next));
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    for (let i = 0; i < turns.length; i += 1) {
      const err = validateDisplayLine(turns[i].display);
      if (err) {
        setErrorMsg(`เทิร์นที่ ${i + 1}: ${err}`);
        return;
      }
    }

    setSubmitting(true);
    setErrorMsg('');
    try {
      const payload = {
        turns: turns.map((t, idx) => ({
          index: idx,
          display: String(t.display || '').trim(),
          photo: t.photo || null,
        })),
        timing_offset_sec: timingOffsetSec,
        base_revision: clip.revision,
      };

      const res = await fetch(`/api/review/${encodeURIComponent(clip.clip_id)}/script`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let detail = 'บันทึกไม่สำเร็จ';
        try {
          const errJson = await res.json();
          detail = errJson.detail || detail;
        } catch {
          // ignore
        }
        throw new Error(detail);
      }

      const updated = await res.json();
      onSaved?.(updated);
      onClose?.();
    } catch (err) {
      setErrorMsg(err?.message || 'เกิดข้อผิดพลาดในการบันทึก');
    } finally {
      setSubmitting(false);
    }
  };

  const content = (
    <div
      className="fixed inset-0 z-[9999] flex items-end justify-center w-screen h-dvh max-h-dvh bg-black/80 backdrop-blur-sm overscroll-none"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`แก้ไขเบา ${clip.title || clip.clip_id}`}
        className="relative w-full max-w-xl max-h-[90dvh] bg-[#0B0F19] border-t border-white/15 rounded-t-3xl flex flex-col overflow-hidden pb-[env(safe-area-inset-bottom)] text-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/10 bg-[#0F1624]">
          <div className="min-w-0 flex-1">
            <h3 className="text-base font-bold text-white truncate">
              แก้ไขเบา: {clip.title || clip.clip_id}
            </h3>
            <p className="text-xs text-slate-400 truncate">
              รหัสคลิป {clip.clip_id} · รอบแก้ไข v{clip.revision || 1}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="min-h-11 min-w-11 px-3 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-medium text-slate-300"
          >
            ปิดหน้าต่าง
          </button>
        </div>

        {/* Scrollable body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
          {/* Timing Offset Stepper */}
          <div className="p-3.5 rounded-2xl bg-white/[0.04] border border-white/10">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-white">ขยับจังหวะซับและกล่องแชท</div>
                <div className="text-xs text-slate-400">ปรับทีละ 0.1 วินาที โดยไม่กระทบไฟล์เสียงพากย์</div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => adjustTiming(-0.1)}
                  className="min-h-11 min-w-11 px-3 rounded-xl bg-white/10 hover:bg-white/15 active:bg-white/20 text-sm font-bold text-white"
                >
                  -0.1s
                </button>
                <span className="min-w-[64px] text-center font-mono text-base font-bold text-emerald-400">
                  {timingOffsetSec > 0 ? `+${timingOffsetSec.toFixed(1)}s` : `${timingOffsetSec.toFixed(1)}s`}
                </span>
                <button
                  type="button"
                  onClick={() => adjustTiming(0.1)}
                  className="min-h-11 min-w-11 px-3 rounded-xl bg-white/10 hover:bg-white/15 active:bg-white/20 text-sm font-bold text-white"
                >
                  +0.1s
                </button>
              </div>
            </div>
          </div>

          {/* Turns editor */}
          <div className="space-y-4">
            {turns.map((turn, idx) => (
              <div
                key={`turn-${idx}`}
                className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/10 space-y-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-white/10 text-slate-200">
                    #{idx + 1} · {turn.speaker}
                  </span>
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-400/20">
                    เสียงพากย์ล็อกไว้
                  </span>
                </div>

                {/* Locked spoken reference */}
                <div className="px-3 py-2 rounded-xl bg-black/40 border border-white/5 text-xs text-slate-400">
                  <span className="text-slate-500 mr-1.5">บทพากย์ (spoken):</span>
                  <span className="text-slate-300">{turn.spoken}</span>
                </div>

                {/* Editable display text (16px font input to prevent iOS zoom) */}
                <div>
                  <label
                    htmlFor={`turn-display-${idx}`}
                    className="block text-xs font-medium text-slate-300 mb-1"
                  >
                    ข้อความบนจอแชท (display)
                  </label>
                  <input
                    id={`turn-display-${idx}`}
                    type="text"
                    value={turn.display}
                    onChange={(e) => handleDisplayChange(idx, e.target.value)}
                    className="w-full min-h-11 px-3.5 py-2.5 rounded-xl bg-[#131B2E] border border-white/15 text-base text-white focus:outline-none focus:border-emerald-400"
                    placeholder="พิมพ์ข้อความที่จะแสดงในแชท"
                  />
                </div>

                {/* Photo selector grid if available_photos exists or turn has a photo */}
                {(availablePhotos.length > 0 || turn.photo) && (
                  <div className="space-y-1.5">
                    <div className="text-xs font-medium text-slate-400">
                      รูปประกอบในเทิร์นนี้ {turn.photo ? `(เลือกแล้ว: ${turn.photo})` : '(ไม่ใส่รูป)'}
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      {availablePhotos.map((photoUrl) => {
                        const selected = turn.photo === photoUrl;
                        return (
                          <button
                            key={photoUrl}
                            type="button"
                            onClick={() => handleSelectPhoto(idx, photoUrl)}
                            className={`relative min-h-12 rounded-xl overflow-hidden border-2 p-1 text-left transition ${
                              selected
                                ? 'border-emerald-400 bg-emerald-500/15'
                                : 'border-white/10 bg-white/5'
                            }`}
                          >
                            <div className="text-[11px] text-slate-200 truncate px-1 py-1">
                              {photoUrl.split('/').pop() || photoUrl}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {errorMsg && (
            <div
              role="alert"
              className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-sm text-rose-200"
            >
              {errorMsg}
            </div>
          )}

          {/* Primary CTA */}
          <div className="pt-2 pb-2 sticky bottom-0 bg-[#0B0F19] border-t border-white/10">
            <button
              type="submit"
              disabled={submitting}
              className="w-full min-h-12 px-4 py-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-base font-bold text-slate-950 transition"
            >
              {submitting ? 'กำลังบันทึกและเข้าคิวเรนเดอร์ใหม่' : 'บันทึกและเรนเดอร์ใหม่คลิปนี้'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  if (typeof document !== 'undefined' && document.body) {
    return createPortal(content, document.body);
  }
  return content;
}

export default ReviewSheet;
