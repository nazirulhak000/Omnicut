import React, { useState, useEffect, useCallback } from "react";
import api from "../../api.js";

/**
 * Mobile Product Intake Screen (`frontend/src/components/mobile/IntakeScreen.jsx`).
 *
 * Features:
 * - Auto-reads `?intake=1&url=...&text=...` from URL when shared from TikTok (`share_target`).
 * - Verb-first ≥44px button `วางลิงก์จากคลิปบอร์ด` (no leading icons per UI Clean Standard).
 * - Product confirmation card with Hero photo star selection (Strict Zero-Price: NO price field/display).
 * - Manual spec fallback sheet when `needs_manual` is true (WAF/Challenge fallback).
 * - Sticky bottom CTA `สร้าง 20 สคริปต์คู่รัก`.
 */
export default function IntakeScreen({
  onScriptsReady,
  onProductCommitted,
  initialSearch = typeof window !== "undefined" ? window.location.search : "",
}) {
  const [rawInput, setRawInput] = useState(() => {
    if (!initialSearch) return "";
    const params = new URLSearchParams(initialSearch);
    const sharedUrl = params.get("url") || "";
    const sharedText = params.get("text") || params.get("title") || "";
    if (params.get("intake") === "1" || sharedUrl || sharedText) {
      return `${sharedText} ${sharedUrl}`.trim();
    }
    return "";
  });
  const [parsedInfo, setParsedInfo] = useState(null);
  const [preview, setPreview] = useState(null);
  const [productName, setProductName] = useState("");
  const [specsText, setSpecsText] = useState("");
  const [photos, setPhotos] = useState([]);
  const [needsManual, setNeedsManual] = useState(false);
  const [loadingStage, setLoadingStage] = useState(""); // "" | "parsing" | "previewing" | "generating"
  const [errorMsg, setErrorMsg] = useState("");
  const [statusBanner, setStatusBanner] = useState("");

  const runIntakeFlow = useCallback(async (inputText, explicitUrl = "") => {
    const combined = `${explicitUrl || ""} ${inputText || ""}`.trim();
    if (!combined) return;

    setErrorMsg("");
    setStatusBanner("");
    setLoadingStage("parsing");

    try {
      const parseRes = await api.post("/intake/parse", {
        text: inputText || combined,
        url: explicitUrl || undefined,
      });
      const parsed = parseRes.data;
      setParsedInfo(parsed);

      if (parsed.duplicate && parsed.existing_product) {
        setStatusBanner("มีสินค้านี้ในระบบแล้ว สามารถใช้ข้อมูลเดิมหรือสร้างสคริปต์ต่อได้ทันที");
      }

      setLoadingStage("previewing");
      const previewRes = await api.post("/intake/preview", {
        url: parsed.url || explicitUrl,
        text: inputText || combined,
      });
      const prev = previewRes.data;
      setPreview(prev);
      setProductName(prev.name || parsed.existing_product?.name || "");

      const initialSpecs = (prev.specs || [])
        .map((s) => (typeof s === "string" ? s : `${s.label || ""} ${s.value || ""}`.trim()))
        .filter(Boolean)
        .join("\n");
      setSpecsText(initialSpecs);

      const initialPhotos = Array.isArray(prev.photos) ? prev.photos : [];
      setPhotos(
        initialPhotos.map((p, idx) =>
          typeof p === "string"
            ? { url: p, name: `hero_${idx + 1}`, starred: idx === 0 }
            : { ...p, starred: Boolean(p.starred ?? idx === 0) },
        ),
      );
      setNeedsManual(Boolean(prev.needs_manual));
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        "ไม่สามารถแยกข้อมูลลิงก์สินค้าได้ กรุณากรอกข้อมูลสินค้าด้วยตนเอง";
      setErrorMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
      setNeedsManual(true);
    } finally {
      setLoadingStage("");
    }
  }, []);

  // Auto-read `?intake=1&url=...&text=...` on mount
  useEffect(() => {
    if (!initialSearch) return;
    const params = new URLSearchParams(initialSearch);
    const sharedUrl = params.get("url") || "";
    const sharedText = params.get("text") || params.get("title") || "";
    if (params.get("intake") === "1" || sharedUrl || sharedText) {
      const combined = `${sharedText} ${sharedUrl}`.trim();
      if (combined) {
        Promise.resolve().then(() => {
          runIntakeFlow(sharedText, sharedUrl);
        });
      }
    }
  }, [initialSearch, runIntakeFlow]);

  const handlePasteFromClipboard = async () => {
    setErrorMsg("");
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const clipText = await navigator.clipboard.readText();
        if (clipText && clipText.trim()) {
          setRawInput(clipText.trim());
          await runIntakeFlow(clipText.trim());
          return;
        }
      }
      setErrorMsg("คลิปบอร์ดว่างเปล่า หรือเบราว์เซอร์ไม่อนุญาตให้อ่านอัตโนมัติ กรุณาวางลิงก์ในช่องด้านล่าง");
    } catch {
      setErrorMsg("ไม่สามารถอ่านคลิปบอร์ดอัตโนมัติได้ กรุณากดค้างเพื่อวางลิงก์ในช่องข้อความ");
    }
  };

  const handleToggleStarPhoto = (index) => {
    setPhotos((prev) =>
      prev.map((photo, idx) =>
        idx === index ? { ...photo, starred: !photo.starred } : photo,
      ),
    );
  };

  const handleCommitAndGenerate20 = async () => {
    const cleanName = productName.trim();
    if (!cleanName) {
      setErrorMsg("กรุณาระบุชื่อสินค้าก่อนสร้างสคริปต์");
      setNeedsManual(true);
      return;
    }

    setErrorMsg("");
    setLoadingStage("generating");

    try {
      const specLines = specsText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

      const commitRes = await api.post("/intake/commit", {
        url: parsedInfo?.url || preview?.url || rawInput.trim(),
        name: cleanName,
        code: preview?.code || undefined,
        tiktok_product_id:
          parsedInfo?.tiktok_product_id || preview?.tiktok_product_id || undefined,
        specs: specLines.map((line) => ({ label: "จุดเด่น", value: line })),
        selling_points: specLines,
        photos,
        raw_text: specsText,
      });

      const savedProduct = commitRes.data?.product;
      if (onProductCommitted && savedProduct) {
        onProductCommitted(savedProduct);
      }

      const genRes = await api.post("/scripts/generate-couple-20", {
        product_id: savedProduct?.id,
        product: savedProduct,
      });

      if (onScriptsReady) {
        onScriptsReady({
          product: savedProduct,
          angles: genRes.data?.angles || [],
        });
      }
      setStatusBanner("สร้าง 20 สคริปต์คู่รักครบทุกหมวดเรียบร้อยแล้ว");
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        "เกิดข้อผิดพลาดในการสร้าง 20 สคริปต์คู่รัก";
      setErrorMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    } finally {
      setLoadingStage("");
    }
  };

  return (
    <div data-oc-surface="workspace" className="min-h-dvh bg-slate-950 text-slate-100 flex flex-col pb-28">
      <header data-oc-surface="data" className="px-4 pt-4 pb-3 border-b border-slate-800 bg-slate-900/80 sticky top-0 z-10">
        <h1 className="text-lg font-bold text-white">นำเข้าสินค้า TikTok Shop</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          แชร์ลิงก์จากแอป TikTok หรือวางข้อความแชร์เพื่อเตรียมสร้าง 20 สคริปต์คู่รัก
        </p>
      </header>

      <main className="flex-1 px-4 py-4 space-y-4">
        {/* Step 1: Link Input & Clipboard Action */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <button
              type="button"
              onClick={handlePasteFromClipboard}
              disabled={Boolean(loadingStage)}
              className="min-h-12 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-base transition disabled:opacity-50"
            >
              วางลิงก์จากคลิปบอร์ด
            </button>
            <button
              type="button"
              onClick={() => runIntakeFlow(rawInput)}
              disabled={!rawInput.trim() || Boolean(loadingStage)}
              className="min-h-12 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 font-medium text-base transition disabled:opacity-50"
            >
              ดึงข้อมูลสินค้า
            </button>
          </div>

          <div>
            <label
              htmlFor="intake-raw-input"
              className="block text-xs font-medium text-slate-400 mb-1"
            >
              ลิงก์หรือข้อความที่แชร์จาก TikTok
            </label>
            <textarea
              id="intake-raw-input"
              rows={2}
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              placeholder="วางข้อความแชร์ เช่น ดูสินค้านี้บน TikTok https://vt.tiktok.com/..."
              className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2.5 text-base text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {parsedInfo?.url && (
            <div className="text-xs text-slate-300 bg-slate-950/90 border border-slate-800 rounded-xl p-2.5 space-y-1">
              <div className="truncate">
                <span className="text-slate-400">ลิงก์สะอาด: </span>
                <span className="font-mono text-emerald-400">{parsedInfo.url}</span>
              </div>
              {parsedInfo.tiktok_product_id && (
                <div>
                  <span className="text-slate-400">รหัสสินค้า TikTok: </span>
                  <span className="font-mono text-indigo-300">
                    {parsedInfo.tiktok_product_id}
                  </span>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Loading skeleton */}
        {loadingStage && (
          <section
            aria-live="polite"
            className="bg-slate-900 border border-slate-800 rounded-2xl p-4 animate-pulse space-y-2"
          >
            <div className="h-4 w-48 bg-slate-800 rounded" />
            <div className="h-3 w-full bg-slate-800 rounded" />
            <p className="text-xs text-indigo-300 pt-1">
              {loadingStage === "parsing" && "กำลังแยกลิงก์และตรวจสินค้าซ้ำ..."}
              {loadingStage === "previewing" && "กำลังดึงข้อมูลและรูปสินค้า..."}
              {loadingStage === "generating" && "กำลังบันทึกสินค้าและสร้าง 20 สคริปต์คู่รัก..."}
            </p>
          </section>
        )}

        {/* Duplicate or status banner */}
        {statusBanner && (
          <div className="rounded-xl bg-emerald-950/70 border border-emerald-700/60 px-3.5 py-2.5 text-sm text-emerald-200">
            {statusBanner}
          </div>
        )}

        {/* Error banner */}
        {errorMsg && (
          <div
            role="alert"
            className="rounded-xl bg-rose-950/80 border border-rose-700/70 px-3.5 py-2.5 text-sm text-rose-200"
          >
            {errorMsg}
          </div>
        )}

        {/* Step 2: Product Confirmation Card (Strict Zero-Price: No price input or display) */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">ยืนยันข้อมูลสินค้า</h2>
            {preview?.code && (
              <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-800 text-indigo-300">
                {preview.code}
              </span>
            )}
          </div>

          <div>
            <label
              htmlFor="intake-product-name"
              className="block text-xs font-medium text-slate-300 mb-1"
            >
              ชื่อสินค้าสำหรับใช้ในบทพูด
            </label>
            <input
              id="intake-product-name"
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="ระบุชื่อรุ่นและแบรนด์สินค้า (ห้ามใส่ราคา)"
              className="w-full min-h-11 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-base text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Hero Photo Star Selection */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300">
                เลือกรูป Hero สินค้า (แตะเพื่อติดดาวใช้ในฉากแชท)
              </span>
              <span className="text-xs text-amber-300">
                เลือกแล้ว {photos.filter((p) => p.starred).length}/{photos.length} รูป
              </span>
            </div>

            {photos.length > 0 ? (
              <div className="grid grid-cols-3 gap-2.5">
                {photos.map((photo, idx) => (
                  <button
                    key={`${photo.url}_${idx}`}
                    type="button"
                    onClick={() => handleToggleStarPhoto(idx)}
                    className={`relative rounded-xl overflow-hidden border-2 transition min-h-24 bg-slate-950 text-left ${
                      photo.starred
                        ? "border-amber-400 ring-2 ring-amber-400/30"
                        : "border-slate-800 opacity-75"
                    }`}
                  >
                    <img
                      src={photo.url}
                      alt={photo.name || `รูปสินค้า ${idx + 1}`}
                      loading="lazy"
                      className="w-full h-24 object-cover"
                    />
                    <span
                      className={`block text-center text-xs font-semibold py-1 ${
                        photo.starred
                          ? "bg-amber-400 text-slate-950"
                          : "bg-slate-900/90 text-slate-300"
                      }`}
                    >
                      {photo.starred ? "ติดดาว Hero" : "แตะเพื่อเลือก"}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 bg-slate-950 border border-slate-800 rounded-xl p-3">
                ยังไม่มีรูปสินค้าจากลิงก์ สามารถเพิ่มสเปกด้านล่างเพื่อสร้างสคริปต์ก่อนได้
              </p>
            )}
          </div>

          {/* Manual Spec Fallback Sheet when needs_manual is true or user toggles */}
          {(needsManual || specsText || preview) && (
            <div className="space-y-2 pt-2 border-t border-slate-800">
              {needsManual && (
                <div className="rounded-xl bg-amber-950/60 border border-amber-700/60 px-3 py-2 text-xs text-amber-200">
                  {preview?.warning ||
                    "เว็บไซต์ติดระบบตรวจความปลอดภัย กรุณาวางสเปกหรือจุดเด่นสินค้าด้านล่างแทน"}
                </div>
              )}
              <label
                htmlFor="intake-specs-textarea"
                className="block text-xs font-medium text-slate-300"
              >
                จุดเด่นและสเปกสินค้า (บรรทัดละ 1 ข้อ — ห้ามระบุราคาหรือส่วนลด)
              </label>
              <textarea
                id="intake-specs-textarea"
                rows={4}
                value={specsText}
                onChange={(e) => setSpecsText(e.target.value)}
                placeholder={
                  "เช่น มีสายชาร์จ Type-C ในตัว 2 เส้น\nรองรับ Fast Charge\nมีหน้าจอดิจิทัลบอกเปอร์เซ็นต์แบต"
                }
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2.5 text-base text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          )}
        </section>
      </main>

      {/* Sticky Bottom CTA */}
      <footer className="fixed bottom-0 inset-x-0 bg-slate-950/95 backdrop-blur border-t border-slate-800 p-3 z-20">
        <button
          type="button"
          onClick={handleCommitAndGenerate20}
          disabled={Boolean(loadingStage) || !productName.trim()}
          className="w-full min-h-12 rounded-xl bg-emerald-500 hover:bg-emerald-400 active:bg-emerald-600 text-slate-950 font-bold text-base shadow-lg transition disabled:opacity-50"
        >
          สร้าง 20 สคริปต์คู่รัก
        </button>
      </footer>
    </div>
  );
}
