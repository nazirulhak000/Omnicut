import React, { useState, useMemo, useEffect, useRef } from "react";
import api from "../../api.js";
import {
  lintCoupleScript,
  normalizeSpeaker,
  extractTurnPhrases,
} from "../../lib/scriptRules";

/**
 * Normalize an angle's turns into editable `[{ speaker, display, spoken, photo }]`.
 */
function normalizeEditableTurns(rawTurns = []) {
  return rawTurns.map((turn, idx) => {
    const [spkRaw, phrases] = extractTurnPhrases(turn);
    const spk = normalizeSpeaker(spkRaw) || (idx % 2 === 0 ? "nui" : "bao");
    const first = phrases[0] || { display: "", spoken: "" };
    const photo =
      turn && typeof turn === "object" && !Array.isArray(turn)
        ? turn.photo ?? null
        : Array.isArray(turn) && turn.length >= 3
          ? turn[2]
          : null;
    return {
      speaker: spk,
      display: first.display || "",
      spoken: first.spoken || first.display || "",
      photo,
    };
  });
}

/**
 * Full-height Mobile Card Deck (`100dvh`) for reviewing 20 Couple Paper Chat scripts.
 *
 * Enforces:
 * - Synchronous `<300ms` live lint validation via `scriptRules.js`
 * - Disables `อนุมัติบทนี้` and `บันทึกการแก้ไข` when any lint rule fails (`NO_ELLIPSIS`, `NO_PRICE`, `NO_EMOJI`, `NO_THAI_TECH_TRANSLITERATION`, `TURN_STRUCTURE`)
 * - Bottom ≥48px (`min-h-12`) verb-first action buttons with zero redundant icons
 * - 5-second Undo bar after approve/regenerate actions
 * - Optimistic concurrency (`base_revision`) handling with 409 conflict notice
 */
export default function ScriptReviewDeck({
  productId,
  initialAngles = [],
  onAllApproved,
  onAnglesChange,
}) {
  const [angles, setAngles] = useState(() => initialAngles);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isEditingSheetOpen, setIsEditingSheetOpen] = useState(false);
  const [draftTurns, setDraftTurns] = useState([]);
  const [regenerateReason, setRegenerateReason] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [errorBanner, setErrorBanner] = useState("");
  const [conflictDialog, setConflictDialog] = useState(null);
  const [undoState, setUndoState] = useState(null);
  const undoTimerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    };
  }, []);

  const currentAngle = angles[currentIndex] || null;

  // Live lint check on current angle (or active draft turns while editing)
  const currentLint = useMemo(() => {
    if (!currentAngle) return { valid: false, violations: [] };
    const turnsToCheck = isEditingSheetOpen
      ? draftTurns
      : normalizeEditableTurns(currentAngle.turns || []);
    return lintCoupleScript({ turns: turnsToCheck });
  }, [currentAngle, isEditingSheetOpen, draftTurns]);

  const approvedCount = useMemo(
    () =>
      angles.filter((a) => (a.script_review?.state || "") === "approved")
        .length,
    [angles],
  );

  const scheduleUndo = (label, snapshotAngles, snapshotIndex) => {
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    setUndoState({
      label,
      snapshotAngles,
      snapshotIndex,
    });
    undoTimerRef.current = setTimeout(() => {
      setUndoState(null);
    }, 5000);
  };

  const handleUndo = () => {
    if (!undoState) return;
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    setAngles(undoState.snapshotAngles);
    setCurrentIndex(undoState.snapshotIndex);
    if (onAnglesChange) onAnglesChange(undoState.snapshotAngles);
    setUndoState(null);
  };

  const updateLocalAngles = (nextAngles) => {
    setAngles(nextAngles);
    if (onAnglesChange) onAnglesChange(nextAngles);
  };

  const handleOpenEditor = () => {
    if (!currentAngle) return;
    setErrorBanner("");
    setDraftTurns(normalizeEditableTurns(currentAngle.turns || []));
    setIsEditingSheetOpen(true);
  };

  const handleCloseEditor = () => {
    setIsEditingSheetOpen(false);
    setConflictDialog(null);
  };

  const handleDraftTurnChange = (turnIdx, field, value) => {
    setDraftTurns((prev) =>
      prev.map((turn, idx) =>
        idx === turnIdx ? { ...turn, [field]: value } : turn,
      ),
    );
  };

  const handleSaveEditedTurns = async () => {
    if (!currentAngle || !currentLint.valid) return;
    const angleId = currentAngle.angle_id || currentAngle.id;
    const baseRevision = currentAngle.revision ?? 1;
    setIsBusy(true);
    setErrorBanner("");

    try {
      if (productId) {
        const res = await api.patch(
          `/scripts/${productId}/angles/${angleId}`,
          {
            turns: draftTurns,
            base_revision: baseRevision,
          },
        );
        const updatedAngle = res.data?.angle || {
          ...currentAngle,
          turns: draftTurns,
          revision: baseRevision + 1,
          lint: currentLint,
        };
        const nextAngles = angles.map((a, idx) =>
          idx === currentIndex ? updatedAngle : a,
        );
        updateLocalAngles(nextAngles);
      } else {
        const nextAngles = angles.map((a, idx) =>
          idx === currentIndex
            ? {
                ...a,
                turns: draftTurns,
                revision: baseRevision + 1,
                lint: currentLint,
              }
            : a,
        );
        updateLocalAngles(nextAngles);
      }
      setIsEditingSheetOpen(false);
    } catch (err) {
      if (err?.response?.status === 409) {
        setConflictDialog(
          err.response.data?.detail || {
            message: "บทนี้ถูกแก้ไขจากอุปกรณ์อื่นแล้ว กรุณาโหลดข้อมูลล่าสุด",
          },
        );
      } else {
        setErrorBanner(
          err?.response?.data?.detail ||
            err?.message ||
            "บันทึกการแก้ไขบทไม่สำเร็จ",
        );
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleRegenerateCurrent = async () => {
    if (!currentAngle) return;
    const prevSnapshot = [...angles];
    const prevIdx = currentIndex;
    const angleId = currentAngle.angle_id || currentAngle.id;
    const baseRevision = currentAngle.revision ?? 1;
    setIsBusy(true);
    setErrorBanner("");

    try {
      if (productId) {
        const res = await api.patch(
          `/scripts/${productId}/angles/${angleId}`,
          {
            regenerate: true,
            reason: regenerateReason,
            base_revision: baseRevision,
          },
        );
        const updatedAngle = res.data?.angle;
        if (updatedAngle) {
          const nextAngles = angles.map((a, idx) =>
            idx === currentIndex ? updatedAngle : a,
          );
          updateLocalAngles(nextAngles);
          scheduleUndo("เขียนบทใหม่แล้ว", prevSnapshot, prevIdx);
        }
      }
      setRegenerateReason("");
    } catch (err) {
      setErrorBanner(
        err?.response?.data?.detail?.message ||
          err?.response?.data?.detail ||
          err?.message ||
          "ไม่สามารถเขียนบทนี้ใหม่ได้",
      );
    } finally {
      setIsBusy(false);
    }
  };

  const handleApproveCurrent = async () => {
    if (!currentAngle || !currentLint.valid) return;
    const prevSnapshot = [...angles];
    const prevIdx = currentIndex;
    const angleId = currentAngle.angle_id || currentAngle.id;
    setIsBusy(true);
    setErrorBanner("");

    try {
      let nextAngles = angles.map((a, idx) =>
        idx === currentIndex
          ? {
              ...a,
              script_review: {
                state: "approved",
                at: new Date().toISOString(),
                note: "",
              },
              revision: (a.revision || 1) + 1,
            }
          : a,
      );

      if (productId) {
        const res = await api.post(`/scripts/${productId}/angles/review`, {
          angle_id: angleId,
          state: "approved",
        });
        if (Array.isArray(res.data?.angles) && res.data.angles.length > 0) {
          nextAngles = res.data.angles;
        }
      }

      updateLocalAngles(nextAngles);
      scheduleUndo(
        `อนุมัติบทที่ ${currentIndex + 1} แล้ว`,
        prevSnapshot,
        prevIdx,
      );

      if (currentIndex < nextAngles.length - 1) {
        setCurrentIndex(currentIndex + 1);
      } else if (onAllApproved) {
        onAllApproved(nextAngles);
      }
    } catch (err) {
      setErrorBanner(
        err?.response?.data?.detail?.message ||
          err?.response?.data?.detail ||
          err?.message ||
          "อนุมัติบทนี้ไม่สำเร็จ",
      );
    } finally {
      setIsBusy(false);
    }
  };

  const handleApproveAllValid = async () => {
    const prevSnapshot = [...angles];
    const prevIdx = currentIndex;
    setIsBusy(true);
    setErrorBanner("");

    try {
      let nextAngles = angles.map((ang) => {
        const check = lintCoupleScript(ang);
        if (!check.valid) return ang;
        return {
          ...ang,
          script_review: {
            state: "approved",
            at: new Date().toISOString(),
            note: "อนุมัติหมู่ทุกบทที่ผ่านกฎ",
          },
          revision: (ang.revision || 1) + 1,
        };
      });

      if (productId) {
        const res = await api.post(`/scripts/${productId}/angles/review`, {
          approve_all_valid: true,
          state: "approved",
        });
        if (Array.isArray(res.data?.angles) && res.data.angles.length > 0) {
          nextAngles = res.data.angles;
        }
      }

      updateLocalAngles(nextAngles);
      scheduleUndo("อนุมัติทุกบทที่ผ่านกฎแล้ว", prevSnapshot, prevIdx);
      if (onAllApproved) {
        onAllApproved(nextAngles);
      }
    } catch (err) {
      setErrorBanner(
        err?.response?.data?.detail?.message ||
          err?.response?.data?.detail ||
          err?.message ||
          "อนุมัติทุกบทไม่สำเร็จ",
      );
    } finally {
      setIsBusy(false);
    }
  };

  if (!currentAngle) {
    return (
      <div className="h-dvh bg-slate-950 text-slate-200 flex items-center justify-center p-6 text-center">
        <p className="text-base">ยังไม่มีสคริปต์ให้ตรวจในชุดนี้</p>
      </div>
    );
  }

  const turns = normalizeEditableTurns(currentAngle.turns || []);
  const reviewState = currentAngle.script_review?.state || "pending";

  return (
    <div
      style={{ height: "100dvh" }}
      className="h-dvh bg-slate-950 text-slate-100 flex flex-col overflow-hidden select-none"
    >
      {/* Top Deck Header */}
      <header className="px-4 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between gap-2 shrink-0">
        <div>
          <span className="inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-700/60">
            {currentAngle.category || "Couple Paper Chat"}
          </span>
          <h1 className="text-sm font-bold text-white mt-1 line-clamp-1">
            บทที่ {currentIndex + 1}/{angles.length}: {currentAngle.title}
          </h1>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-slate-800 text-emerald-300">
            อนุมัติแล้ว {approvedCount}/{angles.length}
          </span>
        </div>
      </header>

      {/* Live Lint Status Bar */}
      <div className="px-4 py-2 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between gap-2 shrink-0">
        {currentLint.valid ? (
          <span
            data-testid="lint-badge-valid"
            className="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700/60"
          >
            ผ่านกฎครบ 100% ({turns.length} เทิร์น)
          </span>
        ) : (
          <span
            data-testid="lint-badge-invalid"
            className="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full bg-rose-950 text-rose-200 border border-rose-600"
          >
            พบจุดผิดกฎ {currentLint.violations.length} จุด:{" "}
            {currentLint.violations[0]?.code} ({currentLint.violations[0]?.message})
          </span>
        )}

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
            disabled={currentIndex === 0}
            className="min-h-11 px-3 rounded-lg bg-slate-800 text-xs font-medium text-slate-200 disabled:opacity-40"
          >
            ดูบทก่อนหน้า
          </button>
          <button
            type="button"
            onClick={() =>
              setCurrentIndex((i) => Math.min(angles.length - 1, i + 1))
            }
            disabled={currentIndex >= angles.length - 1}
            className="min-h-11 px-3 rounded-lg bg-slate-800 text-xs font-medium text-slate-200 disabled:opacity-40"
          >
            ดูบทถัดไป
          </button>
        </div>
      </div>

      {errorBanner && (
        <div
          role="alert"
          className="mx-4 mt-2 rounded-xl bg-rose-950 border border-rose-700 px-3 py-2 text-xs text-rose-200 shrink-0"
        >
          {errorBanner}
        </div>
      )}

      {/* Turn-by-turn Nui / Bao Paper Chat Bubbles */}
      <main className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5">
        {turns.map((turn, idx) => {
          const isNui = turn.speaker === "nui";
          const turnViolations = currentLint.violations.filter(
            (v) => v.turn_index === idx,
          );
          return (
            <div
              key={idx}
              className={`flex items-start gap-2.5 ${
                isNui ? "justify-start" : "justify-end"
              }`}
            >
              {isNui && (
                <div
                  aria-label="น้องนุ้ย"
                  className="w-8 h-8 rounded-full bg-pink-500 text-white font-bold text-sm flex items-center justify-center shrink-0"
                >
                  น
                </div>
              )}

              <div
                className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 shadow-sm border ${
                  isNui
                    ? "bg-white text-slate-900 border-slate-200"
                    : "bg-[#8de07a] text-slate-950 border-emerald-400"
                } ${turnViolations.length > 0 ? "ring-2 ring-rose-500" : ""}`}
              >
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span className="text-[11px] font-bold opacity-75">
                    {isNui ? "น้องนุ้ย" : "พี่บ่าว"} · เทิร์น {idx + 1}
                  </span>
                </div>
                <p className="text-sm font-bold leading-snug">{turn.display}</p>
                <p className="text-xs opacity-80 mt-1 leading-relaxed">
                  เสียงพากย์: {turn.spoken}
                </p>
                {turnViolations.length > 0 && (
                  <p className="text-xs font-semibold text-rose-700 mt-1">
                    {turnViolations.map((v) => v.message).join(" · ")}
                  </p>
                )}
              </div>

              {!isNui && (
                <div
                  aria-label="พี่บ่าว"
                  className="w-8 h-8 rounded-full bg-sky-500 text-white font-bold text-sm flex items-center justify-center shrink-0"
                >
                  บ
                </div>
              )}
            </div>
          );
        })}
      </main>

      {/* 5-Second Undo Bar */}
      {undoState && (
        <div
          role="status"
          className="mx-4 mb-2 px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-between text-xs text-slate-100 shrink-0"
        >
          <span>{undoState.label}</span>
          <button
            type="button"
            onClick={handleUndo}
            className="min-h-11 px-3 rounded-lg bg-amber-400 text-slate-950 font-bold"
          >
            เลิกทำ
          </button>
        </div>
      )}

      {/* Bottom Action Bar (≥48px buttons, verb-first) */}
      <footer className="px-4 py-3 bg-slate-900 border-t border-slate-800 space-y-2 shrink-0">
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={handleRegenerateCurrent}
            disabled={isBusy}
            className="min-h-12 px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 font-semibold text-sm transition disabled:opacity-50"
          >
            เขียนบทนี้ใหม่
          </button>
          <button
            type="button"
            onClick={handleOpenEditor}
            disabled={isBusy}
            className="min-h-12 px-3 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition disabled:opacity-50"
          >
            แก้ไขบท
          </button>
          <button
            type="button"
            onClick={handleApproveCurrent}
            disabled={isBusy || !currentLint.valid}
            className="min-h-12 px-3 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {reviewState === "approved" ? "อนุมัติซ้ำบทนี้" : "อนุมัติบทนี้"}
          </button>
        </div>

        <button
          type="button"
          onClick={handleApproveAllValid}
          disabled={isBusy}
          className="w-full min-h-12 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-emerald-500/40 text-emerald-300 font-semibold text-sm transition disabled:opacity-50"
        >
          อนุมัติทุกบทที่ผ่านกฎ
        </button>
      </footer>

      {/* Bottom Sheet Turn Editor (16px inputs, instant <300ms lint validation) */}
      {isEditingSheetOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="แก้ไขบทสนทนา"
          className="fixed inset-0 z-50 bg-black/75 flex flex-col justify-end"
        >
          <div className="max-h-[90dvh] bg-slate-900 border-t border-slate-700 rounded-t-3xl flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white">
                  แก้ไขบทที่ {currentIndex + 1}
                </h2>
                {currentLint.valid ? (
                  <span className="text-xs text-emerald-400 font-semibold">
                    ผ่านกฎทุกข้อ พร้อมบันทึก
                  </span>
                ) : (
                  <span
                    role="alert"
                    className="text-xs text-rose-400 font-semibold"
                  >
                    ผิดกฎ {currentLint.violations.length} จุด:{" "}
                    {currentLint.violations[0]?.message}
                  </span>
                )}
              </div>

              <button
                type="button"
                onClick={handleCloseEditor}
                className="min-h-11 px-3 rounded-xl bg-slate-800 text-sm text-slate-200 font-medium"
              >
                ปิดหน้าต่าง
              </button>
            </div>

            {conflictDialog && (
              <div
                role="alert"
                className="m-4 p-3 rounded-xl bg-amber-950 border border-amber-600 text-xs text-amber-200 space-y-2"
              >
                <p className="font-bold">{conflictDialog.message}</p>
                {conflictDialog.current_angle && (
                  <button
                    type="button"
                    onClick={() => {
                      const fresh = conflictDialog.current_angle;
                      const nextAngles = angles.map((a, idx) =>
                        idx === currentIndex ? fresh : a,
                      );
                      updateLocalAngles(nextAngles);
                      setDraftTurns(normalizeEditableTurns(fresh.turns || []));
                      setConflictDialog(null);
                    }}
                    className="min-h-11 px-3 rounded-lg bg-amber-400 text-slate-950 font-bold"
                  >
                    โหลดบทล่าสุดมาทับ
                  </button>
                )}
              </div>
            )}

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {draftTurns.map((turn, idx) => {
                const turnErrs = currentLint.violations.filter(
                  (v) => v.turn_index === idx,
                );
                return (
                  <div
                    key={idx}
                    className={`p-3 rounded-2xl border space-y-2 ${
                      turnErrs.length > 0
                        ? "bg-rose-950/30 border-rose-600"
                        : "bg-slate-950 border-slate-800"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-300">
                        เทิร์นที่ {idx + 1} ·{" "}
                        {turn.speaker === "nui" ? "น้องนุ้ย" : "พี่บ่าว"}
                      </span>
                      {turnErrs.length > 0 && (
                        <span className="text-xs font-semibold text-rose-400">
                          {turnErrs.map((e) => e.code).join(", ")}
                        </span>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs text-slate-400 mb-1">
                        ข้อความในกล่องแชท (display)
                      </label>
                      <input
                        type="text"
                        value={turn.display}
                        onChange={(e) =>
                          handleDraftTurnChange(idx, "display", e.target.value)
                        }
                        style={{ fontSize: "16px" }}
                        className="w-full min-h-11 rounded-xl bg-slate-900 border border-slate-700 px-3 py-2 text-base text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-slate-400 mb-1">
                        คำพูดเสียงพากย์ (spoken)
                      </label>
                      <input
                        type="text"
                        value={turn.spoken}
                        onChange={(e) =>
                          handleDraftTurnChange(idx, "spoken", e.target.value)
                        }
                        style={{ fontSize: "16px" }}
                        className="w-full min-h-11 rounded-xl bg-slate-900 border border-slate-700 px-3 py-2 text-base text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    {turnErrs.length > 0 && (
                      <p className="text-xs text-rose-300 font-medium">
                        {turnErrs.map((e) => e.message).join(" | ")}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-900">
              <button
                type="button"
                onClick={handleSaveEditedTurns}
                disabled={isBusy || !currentLint.valid}
                className="w-full min-h-12 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-base transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                บันทึกการแก้ไขบทนี้
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
