import React, { useState, useEffect, useRef } from 'react';
import {
  Smartphone,
  Video,
  Sparkles,
  Share2,
  Download,
  ChevronRight,
  ArrowLeft,
  CheckCircle2,
  RefreshCw,
  Play,
  Copy,
  Layers,
  Flame,
  Volume2,
  Type,
  Plus,
  Upload,
  Music,
  X,
  Search,
  FileVideo,
  Check,
  AlertCircle
} from 'lucide-react';
import {
  fetchMobileCatalog,
  createMobileSession,
  triggerMobileAssemble,
  fetchMobileTask,
  createMobileQuickAngle,
  uploadMobileVideo,
  quickAddMobileProduct,
  previewMobileVoice,
  cancelMobileTask,
  getRecordingSession,
  markPosted
} from '../api';
import { ConfirmModal } from './ui';
import { MOBILE_WORKFLOW_KEY, catalogPageParams, filmingUrl, mergeCatalogPage, pollMobileTask, progressPercent } from '../lib/mobileStudioFlow.js';
import useWakeLock from '../hooks/useWakeLock';

export default function MobileQuickStudio({ onSwitchToDesktop, onOpenFilmingSession }) {
  const [step, setStep] = useState(1); // 1: Select Product, 2: Filming / Intake, 3: Auto-Assemble & Render, 4: Done/Share
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [catalog, setCatalog] = useState([]);
  // P2-4: catalog pagination — one page at a time + "load more"
  const [catalogPage, setCatalogPage] = useState(1);
  const [catalogTotal, setCatalogTotal] = useState(0);
  const [hasMoreCatalog, setHasMoreCatalog] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  // Selected State
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedAngle, setSelectedAngle] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [sessionData, setSessionData] = useState(null);

  // New Product Modal
  const [showAddProductModal, setShowAddProductModal] = useState(false);
  const [newProductInput, setNewProductInput] = useState('');
  const [addingProduct, setAddingProduct] = useState(false);

  // Custom Angle Modal
  const [showCustomAngleModal, setShowCustomAngleModal] = useState(false);
  const [customHookInput, setCustomHookInput] = useState('');
  const [customScriptInput, setCustomScriptInput] = useState('');
  const [creatingAngle, setCreatingAngle] = useState(false);

  // Mobile Video Upload
  const [uploadedVideoPath, setUploadedVideoPath] = useState(null);
  const [uploadedVideoName, setUploadedVideoName] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  // Audio Preview & BGM
  const [previewingVoice, setPreviewingVoice] = useState(false);
  const [voiceAudioUrl, setVoiceAudioUrl] = useState(null);
  const [bgmEnabled, setBgmEnabled] = useState(true);
  const audioPlayerRef = useRef(null);

  // Render Task State
  const [taskId, setTaskId] = useState(null);
  const [taskProgress, setTaskProgress] = useState(0);
  const [taskStepLabel, setTaskStepLabel] = useState('');
  const [renderResult, setRenderResult] = useState(null);
  const [copiedCaption, setCopiedCaption] = useState(false);

  // Polling ref
  const pollIntervalRef = useRef(null);
  const mountedRef = useRef(true);
  const workflowRef = useRef(null);
  const catalogVersionRef = useRef(0);
  const [pollPaused, setPollPaused] = useState(false);

  // P0 preflight + cancel controls (see _Docs/Plans/PLAN_MOBILE_STUDIO_FLOW_V2_20261004.md)
  const [confirming, setConfirming] = useState(false);
  const [sessionFootageReady, setSessionFootageReady] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [markingPosted, setMarkingPosted] = useState(false);
  const [postedDone, setPostedDone] = useState(false);

  // P2-3: keep the screen awake while the SOP render runs, otherwise the phone
  // sleeps mid-render and polling stalls.
  useWakeLock(step === 3 && Boolean(taskId) && !renderResult);

  const stopPolling = () => { pollIntervalRef.current?.(); pollIntervalRef.current = null; };

  // Load Catalog on mount
  useEffect(() => {
    mountedRef.current = true;
    loadCatalog();
    return () => {
      mountedRef.current = false;
      catalogVersionRef.current += 1;
      stopPolling();
    };
  }, []);

  // P0-1: when we return from the guided-take camera the frontend has no
  // uploadedVideoPath (upload never happened here) and the angle record may not
  // carry attached_raw yet -- only the recording session knows its own raw
  // video. Read that once so the render button is not blocked on a valid take.
  const refreshSessionFootage = async (sid) => {
    if (!sid) {
      setSessionFootageReady(false);
      return false;
    }
    try {
      const sess = await getRecordingSession(sid);
      const ready = Boolean(sess?.status === 'completed' && sess?.raw_video_path);
      if (mountedRef.current) setSessionFootageReady(ready);
      return ready;
    } catch {
      return false;
    }
  };

  const loadCatalog = async () => {
    const version = ++catalogVersionRef.current;
    try {
      setLoading(true);
      setError(null);
      let res = await fetchMobileCatalog(catalogPageParams(1));
      if (!mountedRef.current || version !== catalogVersionRef.current) return;
      if (!Array.isArray(res?.catalog)) throw new Error('รายการสินค้าไม่ถูกต้อง');
      let items = res.catalog;
      let hasMore = Boolean(res.has_more);
      let total = Number(res.total) || items.length;
      let saved = null;
      try { saved = JSON.parse(sessionStorage.getItem(MOBILE_WORKFLOW_KEY)); } catch { /* optional session memory */ }
      const params = new URLSearchParams(window.location.search);
      const productId = params.get('product') || saved?.productId;
      const angleId = params.get('angle') || saved?.angleId;
      // P2-4: สินค้าที่เคยเลือกอาจอยู่หน้าถัดไป — ดึงทั้งคลังครั้งเดียวตอนกู้สถานะเท่านั้น
      if (productId && hasMore && !items.some(p => p.id === productId)) {
        const full = await fetchMobileCatalog();
        if (!mountedRef.current || version !== catalogVersionRef.current) return;
        if (Array.isArray(full?.catalog)) {
          items = full.catalog;
          hasMore = false;
          total = Number(full.total) || items.length;
        }
      }
      setCatalog(items);
      setCatalogTotal(total);
      setHasMoreCatalog(hasMore);
      setCatalogPage(1);
      const prod = items.find(p => p.id === productId) || items[0];
      const angle = prod?.angles?.find(a => (a.angle_id || a.id) === angleId) || prod?.angles?.[0];
      setSelectedProduct(prod || null);
      setSelectedAngle(angle || null);
      const restoredSession = params.get('mobile_session') || saved?.sessionId;
      const currentAid = angle?.angle_id || angle?.id;
      workflowRef.current = { productId: prod?.id, angleId: currentAid, sessionId: restoredSession };

      if (prod?.id === productId && currentAid === angleId) {
        if (saved?.renderResult) {
          setRenderResult(saved.renderResult);
          setStep(4);
        } else if (saved?.taskId) {
          setTaskId(saved.taskId);
          setStep(3);
          startPolling(saved.taskId);
        } else if (restoredSession) {
          setSessionId(restoredSession);
          setStep(2);
          refreshSessionFootage(restoredSession);
        }
      }
    } catch (err) {
      console.error('[MobileQuickStudio] load error:', err);
      if (mountedRef.current && version === catalogVersionRef.current) setError('ไม่สามารถโหลดรายการสินค้าได้ กรุณาตรวจสอบการเชื่อมต่อ');
    } finally {
      if (mountedRef.current && version === catalogVersionRef.current) setLoading(false);
    }
  };

  // P2-4: append the next catalog page without dropping the current selection.
  const loadMoreCatalog = async () => {
    if (!hasMoreCatalog || loadingMore) return;
    const version = catalogVersionRef.current;
    const nextPage = catalogPage + 1;
    try {
      setLoadingMore(true);
      const res = await fetchMobileCatalog(catalogPageParams(nextPage));
      if (!mountedRef.current || version !== catalogVersionRef.current) return;
      if (!Array.isArray(res?.catalog)) throw new Error('รายการสินค้าไม่ถูกต้อง');
      setCatalog(prev => mergeCatalogPage(prev, res.catalog));
      setCatalogPage(nextPage);
      setHasMoreCatalog(Boolean(res.has_more));
      if (Number.isFinite(Number(res.total))) setCatalogTotal(Number(res.total));
    } catch (err) {
      console.error('[MobileQuickStudio] load more error:', err);
      if (mountedRef.current && version === catalogVersionRef.current) {
        setError('โหลดสินค้าเพิ่มไม่สำเร็จ กรุณาลองใหม่');
      }
    } finally {
      if (mountedRef.current && version === catalogVersionRef.current) setLoadingMore(false);
    }
  };

  // Step 1: Select Angle
  const handleSelectProduct = (prod) => {
    setSessionId(null);
    setSessionData(null);
    setSelectedProduct(prod);
    setUploadedVideoPath(null);
    setUploadedVideoName('');
    if (prod.angles && prod.angles.length > 0) {
      setSelectedAngle(prod.angles[0]);
    } else {
      setSelectedAngle(null);
    }
  };

  const handleConfirmStep1 = async () => {
    if (!selectedProduct) return;
    try {
      setConfirming(true);
      setError(null);
      let targetAngle = selectedAngle;
      if (!targetAngle) {
        const quickRes = await createMobileQuickAngle(selectedProduct.id);
        if (quickRes?.angle) {
          targetAngle = quickRes.angle;
          setSelectedAngle(quickRes.angle);
        }
      }
      const angleIdToUse = targetAngle?.id || targetAngle?.angle_id || 'quick_take';
      const sessionRes = await createMobileSession(selectedProduct.id, angleIdToUse);
      if (!mountedRef.current) return;
      if (!sessionRes?.session?.id) throw new Error('ไม่ได้รับเซสชันถ่ายทำจากเซิร์ฟเวอร์');
      setSessionId(sessionRes.session.id);
      setSessionData(sessionRes.session);
      setSessionFootageReady(false);
      rememberWorkflow(sessionRes.session.id);
      setStep(2);
    } catch (err) {
      console.error('[MobileQuickStudio] session create error:', err);
      setError(err?.response?.data?.detail || 'เกิดข้อผิดพลาดในการสร้างเซสชันถ่ายทำ');
    } finally {
      if (mountedRef.current) setConfirming(false);
    }
  };

  const handleCreateQuickAngle = async (customTitle = null, customScript = null) => {
    if (!selectedProduct) return;
    try {
      setCreatingAngle(true);
      setError(null);
      const res = await createMobileQuickAngle(selectedProduct.id, customTitle, customScript);
      if (res?.angle) {
        setSelectedAngle(res.angle);
        setShowCustomAngleModal(false);
        setCustomHookInput('');
        setCustomScriptInput('');
        const sRes = await createMobileSession(selectedProduct.id, res.angle.angle_id || res.angle.id);
        if (sRes?.session?.id) {
          setSessionId(sRes.session.id);
          setSessionData(sRes.session);
          setSessionFootageReady(false);
          rememberWorkflow(sRes.session.id);
          setStep(2);
        }
      }
    } catch (err) {
      console.error('[handleCreateQuickAngle] error:', err);
      setError(err?.response?.data?.detail || 'ไม่สามารถสร้างมุมนำเสนอได้');
    } finally {
      setCreatingAngle(false);
    }
  };

  const handleQuickAddProduct = async () => {
    if (!newProductInput.trim()) return;
    try {
      setAddingProduct(true);
      setError(null);
      const res = await quickAddMobileProduct(newProductInput.trim());
      if (res?.product) {
        setShowAddProductModal(false);
        setNewProductInput('');
        await loadCatalog();
        setSelectedProduct(res.product);
        if (res.product.angles?.length > 0) {
          setSelectedAngle(res.product.angles[0]);
        }
      }
    } catch (err) {
      console.error('[handleQuickAddProduct] error:', err);
      setError(err?.response?.data?.detail || 'ไม่สามารถเพิ่มสินค้าได้');
    } finally {
      setAddingProduct(false);
    }
  };

  const handleUploadMobileVideo = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !selectedProduct) return;
    try {
      setIsUploading(true);
      setUploadProgress(0);
      setError(null);
      const targetAngleId = selectedAngle?.id || selectedAngle?.angle_id || 'quick_take';
      const res = await uploadMobileVideo(selectedProduct.id, targetAngleId, file, (pct) => {
        setUploadProgress(pct);
      });
      if (res?.success) {
        setUploadedVideoPath(res.video_path);
        setUploadedVideoName(file.name);
      }
    } catch (err) {
      console.error('[handleUploadMobileVideo] error:', err);
      setError(err?.response?.data?.detail || 'อัปโหลดคลิปจากมือถือไม่สำเร็จ');
    } finally {
      setIsUploading(false);
    }
  };

  const handlePreviewVoice = async () => {
    const textToSpeak = selectedAngle?.script_full || selectedAngle?.script_preview || selectedProduct?.name;
    if (!textToSpeak) return;
    try {
      setPreviewingVoice(true);
      setError(null);
      const res = await previewMobileVoice(textToSpeak.slice(0, 100));
      if (res?.audio_url) {
        setVoiceAudioUrl(res.audio_url);
        if (audioPlayerRef.current) {
          audioPlayerRef.current.src = res.audio_url;
          audioPlayerRef.current.play().catch(e => console.warn('Audio play error:', e));
        }
      }
    } catch (err) {
      console.error('[handlePreviewVoice] error:', err);
      setError(err?.response?.data?.detail || 'ไม่สามารถทดสอบเสียงพากย์ได้');
    } finally {
      setPreviewingVoice(false);
    }
  };

  const rememberWorkflow = (sid, tid = null, extra = {}) => {
    const pid = selectedProduct?.id || workflowRef.current?.productId;
    const aid = selectedAngle?.angle_id || selectedAngle?.id || workflowRef.current?.angleId;
    workflowRef.current = {
      productId: pid,
      angleId: aid,
      sessionId: sid !== undefined ? sid : workflowRef.current?.sessionId,
      taskId: tid !== undefined ? tid : workflowRef.current?.taskId,
      ...extra
    };
    try { sessionStorage.setItem(MOBILE_WORKFLOW_KEY, JSON.stringify(workflowRef.current)); } catch { /* storage may be disabled */ }

    try {
      const url = new URL(window.location.href);
      if (pid) url.searchParams.set('product', pid);
      if (aid) url.searchParams.set('angle', aid);
      if (sid) url.searchParams.set('mobile_session', sid);
      window.history.replaceState(null, '', url);
    } catch { /* URL sync best-effort */ }
  };

  // P0-1: the render needs SOME footage -- an explicit mobile upload, a raw
  // already attached to the angle, or a completed guided-take session.
  const hasFootage = Boolean(uploadedVideoPath || selectedAngle?.attached_raw || sessionFootageReady);

  // Step 2: Launch Filming
  const handleOpenFilming = () => {
    if (sessionId && onOpenFilmingSession) {
      onOpenFilmingSession(sessionId, selectedProduct.id, selectedAngle.id);
    } else {
      // Fallback open direct path
      window.location.href = filmingUrl(sessionId, selectedProduct.id, selectedAngle.id);
    }
  };

  // Step 3: Trigger Auto-Assemble & Render
  const handleStartAssemble = async () => {
    if (!selectedProduct || !selectedAngle) return;
    if (!hasFootage) {
      setError('ยังไม่มีคลิปวัตถุดิบ กรุณาถ่ายทำหรือแนบคลิปก่อนประกอบคลิป');
      return;
    }
    try {
      setError(null);
      setStep(3);
      stopPolling();
      setRenderResult(null);
      setPostedDone(false);
      setPollPaused(false);
      setTaskProgress(5);
      setTaskStepLabel('กำลังส่งข้อมูลไปยังเซิร์ฟเวอร์ PC เวิร์กสเตชัน...');

      const rawToUse = uploadedVideoPath || null;
      const angleIdToUse = selectedAngle.angle_id || selectedAngle.id;
      const res = await triggerMobileAssemble(
        selectedProduct.id,
        angleIdToUse,
        sessionId,
        rawToUse,
        bgmEnabled
      );

      if (!mountedRef.current) return;
      if (res && res.task_id) {
        setTaskId(res.task_id);
        rememberWorkflow(sessionId, res.task_id);
        startPolling(res.task_id);
      } else {
        throw new Error('ไม่ได้รับ Task ID จากเซิร์ฟเวอร์');
      }
    } catch (err) {
      console.error('[MobileQuickStudio] assemble error:', err);
      setError(err?.response?.data?.detail || err.message || 'เกิดข้อผิดพลาดในการสั่งประกอบคลิป');
      setStep(2);
    }
  };

  // P0-2: ask the server to stop the in-flight render; the poll loop then sees
  // the terminal `cancelled` status on its next tick and routes back to step 2.
  const handleCancelRender = async () => {
    if (!taskId) return;
    try {
      setCancelling(true);
      await cancelMobileTask(taskId);
    } catch (err) {
      setError(err?.response?.data?.detail || 'ยกเลิกงานไม่สำเร็จ');
    } finally {
      setCancelling(false);
      setShowCancelConfirm(false);
    }
  };

  const startPolling = (tid) => {
    stopPolling();
    setPollPaused(false);
    setError(null);
    pollIntervalRef.current = pollMobileTask({
      fetchTask: () => fetchMobileTask(tid),
      onTask: (t) => {
        setTaskProgress(progressPercent(t.progress));
        setTaskStepLabel(t.step_label || 'กำลังประมวลผล');
        if (t.status === 'completed') {
          if (!t.result?.video_url) {
            setError('งานเสร็จแล้วแต่ไม่พบไฟล์วิดีโอ กรุณาตรวจสอบและลองใหม่');
            setStep(2);
          } else {
            setRenderResult(t.result);
            setStep(4);
            rememberWorkflow(sessionId, tid, { renderResult: t.result });
          }
          return false;
        }
        if (t.status === 'failed' || t.status === 'cancelled') {
          setError(t.error || (t.status === 'cancelled' ? 'งานถูกยกเลิก' : 'การเรนเดอร์ไม่สำเร็จ'));
          rememberWorkflow(sessionId);
          setStep(2);
          return false;
        }
        return true;
      },
      onError: (err) => {
        setPollPaused(true);
        setError(err?.response?.status === 404 ? 'ไม่พบงานในเซิร์ฟเวอร์ กรุณาตรวจสอบสถานะก่อนเริ่มงานใหม่' : 'ขาดการเชื่อมต่อกับเซิร์ฟเวอร์ กดตรวจสถานะอีกครั้งเพื่อดูงานเดิม');
      },
    });
  };

  // Web Share API Action
  const handleShareToTikTok = async () => {
    const videoUrl = renderResult?.video_url;
    const title = renderResult?.hook_headline || selectedAngle?.hook_headline || 'รีวิวแกดเจ็ต';
    const caption = `${title}\n\n${renderResult?.hashtags || '#รีวิวไอที #tiktokshop #omnicut'}`;

    // Auto copy caption to clipboard
    try {
      await navigator.clipboard.writeText(caption);
      setCopiedCaption(true);
      setTimeout(() => setCopiedCaption(false), 3000);
    } catch (clipErr) {
      console.warn('Copy failed:', clipErr);
    }

    if (navigator.share && videoUrl) {
      try {
        const fullUrl = new URL(videoUrl, window.location.origin).href;
        // Attempt file share if supported
        const response = await fetch(fullUrl);
        if (!response.ok) throw new Error(`ดาวน์โหลดวิดีโอไม่สำเร็จ (${response.status})`);
        const blob = await response.blob();
        const file = new File([blob], `${renderResult?.project_name || 'video'}.mp4`, { type: 'video/mp4' });

        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          await navigator.share({
            files: [file],
            title: title,
            text: caption,
          });
          return;
        }

        // Fallback to URL share
        await navigator.share({
          title: title,
          text: caption,
          url: fullUrl,
        });
      } catch (shareErr) {
        if (shareErr.name !== 'AbortError') {
          console.warn('[MobileQuickStudio] Web Share error:', shareErr);
          // Fallback direct download
          window.open(videoUrl, '_blank');
        }
      }
    } else if (videoUrl) {
      window.open(videoUrl, '_blank');
    }
  };

  // P1-3: close the loop on the phone -- move the finished clip into Posted/
  // and flip the angle status, same endpoint the desktop gallery uses.
  const handleMarkPosted = async () => {
    const filePath = renderResult?.video_path;
    if (!filePath) {
      setError('ไม่พบตำแหน่งไฟล์วิดีโอสำหรับมาร์คว่าโพสต์แล้ว');
      return;
    }
    try {
      setMarkingPosted(true);
      const aid = selectedAngle?.angle_id || selectedAngle?.id || null;
      const eid = renderResult?.export_id || selectedAngle?.export_id || null;
      const res = await markPosted(filePath, selectedProduct?.id || null, aid, eid);
      if (res?.status_warning) {
        setError(`บันทึกสถานะเรียบร้อย แต่มีคำเตือน: ${res.status_warning}`);
      }
      setPostedDone(true);
    } catch (err) {
      setError(err?.response?.data?.detail || 'มาร์คว่าโพสต์แล้วไม่สำเร็จ');
    } finally {
      setMarkingPosted(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans pb-12">
      {/* Mobile Top App Bar */}
      <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800/80 px-4 pb-3 pt-[calc(env(safe-area-inset-top)+0.75rem)] flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-cyan-500/20 shadow-md">
            <Smartphone className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
              OmniCut Mobile Studio
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-semibold border border-emerald-500/30">
                P2P Host
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">จบงานในมือถือ 3 สเต็ป</p>
          </div>
        </div>

        {/* Switch to Desktop Button */}
        {onSwitchToDesktop && (
          <button
            onClick={onSwitchToDesktop}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 border border-slate-700 transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">สลับไป</span>โหมดคอม
          </button>
        )}
      </header>

      {/* Progress Step Bar */}
      <div className="bg-slate-900/60 border-b border-slate-800/60 px-4 py-2.5">
        <div className="max-w-md mx-auto flex items-center justify-between text-xs font-medium text-slate-400">
          <div className={`flex items-center gap-1.5 ${step >= 1 ? 'text-cyan-400 font-semibold' : ''}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] ${step >= 1 ? 'bg-cyan-500 text-white' : 'bg-slate-800 text-slate-500'}`}>1</span>
            เลือกสินค้า
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          <div className={`flex items-center gap-1.5 ${step >= 2 ? 'text-cyan-400 font-semibold' : ''}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] ${step >= 2 ? 'bg-cyan-500 text-white' : 'bg-slate-800 text-slate-500'}`}>2</span>
            ถ่ายคลิป
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          <div className={`flex items-center gap-1.5 ${step >= 3 ? 'text-cyan-400 font-semibold' : ''}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] ${step >= 3 ? 'bg-cyan-500 text-white' : 'bg-slate-800 text-slate-500'}`}>3</span>
            เรนเดอร์ & แชร์
          </div>
        </div>
      </div>

      {/* Main Container */}
      <main className="flex-1 max-w-md mx-auto w-full px-4 py-4 flex flex-col">
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2 shadow-lg">
            <span className="text-sm">⚠️</span>
            <div className="flex-1">{error}</div>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white font-bold">✕</button>
          </div>
        )}

        {/* STEP 1: Select Product & Angle */}
        {step === 1 && (
          <div className="flex-1 flex flex-col space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">สเต็ป 1: เลือกสินค้า & สคริปต์</h2>
                <p className="text-xs text-slate-400">เลือกสินค้าหรือเพิ่มสินค้าใหม่เพื่อผลิตคลิป 9:16</p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddProductModal(true)}
                className="py-1.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-90 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-cyan-500/20 shrink-0 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>เพิ่มสินค้า</span>
              </button>
            </div>

            {loading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
                <span className="text-xs">กำลังโหลดคลังสินค้า...</span>
              </div>
            ) : catalog.length === 0 ? (
              <div className="py-10 flex flex-col items-center gap-3 text-center">
                <AlertCircle className="w-7 h-7 text-amber-400" />
                <p className="text-xs text-slate-400 max-w-xs">{error || 'ยังไม่มีสินค้าในคลัง เพิ่มสินค้าใหม่เพื่อเริ่มผลิตคลิป'}</p>
                <button
                  type="button"
                  onClick={loadCatalog}
                  className="px-4 py-2 rounded-xl bg-slate-800 border border-slate-700 text-cyan-300 text-xs font-bold cursor-pointer"
                >
                  ลองโหลดใหม่
                </button>
              </div>
            ) : (
              <div className="space-y-3 flex-1 overflow-y-auto max-h-[60vh] pr-1">
                {catalog.map((prod, prodIdx) => {
                  const isSelected = selectedProduct?.id === prod.id;
                  const prodKey = prod.id || `prod_${prodIdx}`;
                  const hasAngles = prod.angles && prod.angles.length > 0;
                  return (
                    <div
                      key={prodKey}
                      onClick={() => handleSelectProduct(prod)}
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-slate-900 border-cyan-500 ring-2 ring-cyan-500/20 shadow-lg shadow-cyan-500/5'
                          : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex gap-3">
                        {prod.cover_url ? (
                          <img
                            src={prod.cover_url}
                            alt={prod.name}
                            className="w-14 h-14 rounded-xl object-cover bg-slate-800 shrink-0"
                          />
                        ) : (
                          <div className="w-14 h-14 rounded-xl bg-slate-800 flex items-center justify-center shrink-0 text-slate-500 font-bold">
                            📦
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <h3 className="font-semibold text-sm text-white truncate">{prod.name}</h3>
                            {isSelected && <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />}
                          </div>
                          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                            <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-medium">
                              {prod.category}
                            </span>
                            {prod.price && (
                              <span className="text-xs font-semibold text-emerald-400">
                                {prod.price}
                              </span>
                            )}
                            {prod.product_status === 'completed' && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" /> ตัดเสร็จครบแล้ว ({prod.rendered_count}/{prod.total_angles || prod.angles?.length || 0})
                              </span>
                            )}
                            {prod.product_status === 'in_progress' && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-bold flex items-center gap-1">
                                <Sparkles className="w-3 h-3 text-amber-400" /> ตัดแล้ว {prod.rendered_count || 0}/{prod.total_angles || prod.angles?.length || 0} {prod.footage_count > 0 ? `• มีคลิป ${prod.footage_count}` : ''}
                              </span>
                            )}
                            {(!prod.product_status || prod.product_status === 'not_started') && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60 font-medium">
                                ยังไม่เริ่มตัด ({prod.total_angles || prod.angles?.length || 0} มุม)
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Expanded Angle selector if this product is active and HAS angles */}
                      {isSelected && hasAngles && (
                        <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                              เลือกมุมและประเด็น (Angle):
                            </span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setShowCustomAngleModal(true);
                              }}
                              className="text-[11px] text-cyan-400 font-medium hover:text-cyan-300 flex items-center gap-1"
                            >
                              <Plus className="w-3 h-3" />
                              <span>เพิ่มมุมใหม่</span>
                            </button>
                          </div>
                          <div className="grid grid-cols-1 gap-2">
                            {prod.angles.map((ang, angIdx) => {
                              const angKey = ang.id || `ang_${prodKey}_${angIdx}`;
                              const isAngActive = selectedAngle?.id === ang.id;
                              return (
                                <button
                                  key={angKey}
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedAngle(ang);
                                  }}
                                  className={`text-left p-2.5 rounded-xl border transition-all text-xs ${
                                    isAngActive
                                      ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-300 font-medium'
                                      : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:border-slate-700'
                                  }`}
                                >
                                  <div className="flex items-start justify-between gap-2">
                                    <span className="font-bold flex-1 leading-snug">{ang.hook_headline}</span>
                                    <div className="flex items-center gap-1.5 shrink-0">
                                      {ang.is_rendered ? (
                                        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-bold flex items-center gap-1">
                                          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> ตัดแล้ว
                                        </span>
                                      ) : ang.has_footage ? (
                                        <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold flex items-center gap-1" title={ang.attached_raw_name || 'มีคลิปแล้ว'}>
                                          <Video className="w-3 h-3 text-cyan-400" /> มีคลิป
                                        </span>
                                      ) : (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                          รอถ่ายคลิป
                                        </span>
                                      )}
                                      {ang.shot_count > 0 && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                          {ang.shot_count} ช็อต
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  {ang.has_footage && ang.attached_raw_name && (
                                    <div className="text-[10px] text-cyan-300/90 font-mono flex items-center gap-1 mt-1 truncate">
                                      <span>📎 ไฟล์: {ang.attached_raw_name}</span>
                                    </div>
                                  )}
                                  {ang.is_rendered && ang.video_url && (
                                    <div className="text-[10px] text-emerald-300/90 font-mono flex items-center gap-1 mt-1 truncate">
                                      <span>🎬 คลิปพร้อมโพสต์: {ang.video_url.split('/').pop()}</span>
                                    </div>
                                  )}
                                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                                    {ang.script_preview}
                                  </p>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Empty Angle State: Unblocks user immediately */}
                      {isSelected && !hasAngles && (
                        <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-3">
                          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                            <p className="font-bold flex items-center gap-1.5">
                              <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
                              สินค้านี้ยังไม่มีมุมนำเสนอ
                            </p>
                            <p className="text-[11px] text-slate-300 mt-1">
                              เลือกปุ่มด่วนด้านล่างเพื่อเริ่มถ่ายทำหรือใส่บทสคริปต์ได้ทันที:
                            </p>
                          </div>

                          <div className="grid grid-cols-1 gap-2">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCreateQuickAngle();
                              }}
                              className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:opacity-90 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md shadow-emerald-500/20"
                            >
                              <Flame className="w-4 h-4 text-white" />
                              <span>ถ่ายด่วนฟรีสไตล์ (สร้างมุมอัตโนมัติ)</span>
                            </button>

                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setShowCustomAngleModal(true);
                              }}
                              className="w-full py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-xs flex items-center justify-center gap-2"
                            >
                              <Plus className="w-4 h-4 text-cyan-400" />
                              <span>เขียนมุม / สคริปต์พูดเอง</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
                {hasMoreCatalog && (
                  <button
                    type="button"
                    onClick={loadMoreCatalog}
                    disabled={loadingMore}
                    className="w-full py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-cyan-300 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {loadingMore && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>
                      {loadingMore
                        ? 'กำลังโหลด...'
                        : `โหลดเพิ่ม (${catalog.length} จาก ${catalogTotal})`}
                    </span>
                  </button>
                )}
              </div>

            )}

            {/* Bottom Floating Action: NEVER blocked */}
            <div className="pt-2 sticky bottom-[calc(env(safe-area-inset-bottom)+1rem)]">
              <button
                disabled={!selectedProduct || confirming || creatingAngle}
                onClick={handleConfirmStep1}
                className="w-full py-3.5 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-lg shadow-cyan-500/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all active:scale-[0.98] cursor-pointer"
              >
                {confirming && <RefreshCw className="w-4 h-4 animate-spin" />}
                <span>
                  {!selectedAngle
                    ? 'ถ่ายด่วนฟรีสไตล์ (ไปหน้าถ่ายทำ)'
                    : 'ยืนยันสคริปต์ & ไปหน้าถ่ายทำ'}
                </span>
                {!confirming && <ChevronRight className="w-4 h-4" />}
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Guided Filming & Media Intake */}
        {step === 2 && (
          <div className="flex-1 flex flex-col space-y-4 pb-20">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">สเต็ป 2: ถ่ายคลิปหน้ากล้อง</h2>
                <p className="text-xs text-slate-400">{selectedProduct?.name} • {selectedAngle?.hook_headline || 'รีวิวทั่วไป'}</p>
              </div>
              <button
                onClick={() => setStep(1)}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
                title="ย้อนกลับ"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
            </div>

            {/* Script Card Preview */}
            <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-cyan-400 flex items-center gap-1">
                  <Flame className="w-3.5 h-3.5 text-amber-400" />
                  Hook บทพูด 60 วินาที
                </span>
                <span className="text-slate-400 text-[11px]">
                  {selectedAngle?.shot_count || 5} ช็อตแนะนำ
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs leading-relaxed text-slate-200 max-h-32 overflow-y-auto">
                {selectedAngle?.script_full || selectedAngle?.script_preview || 'บทรีวิวมาตรฐาน'}
              </div>
            </div>

            {/* Footage Status Notice */}
            {(selectedAngle?.attached_raw || uploadedVideoPath) ? (
              <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-200 text-xs space-y-1.5 shadow-md">
                <div className="flex items-center justify-between">
                  <span className="font-bold flex items-center gap-1.5 text-emerald-400">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    มีคลิปวัตถุดิบพร้อมใช้งาน
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono font-bold">
                    พร้อมเรนเดอร์ทันที
                  </span>
                </div>
                <p className="text-[11px] text-slate-300">
                  ไฟล์วัตถุดิบ: <span className="font-mono text-cyan-300 font-medium">
                    {uploadedVideoName || selectedAngle.attached_raw_name || selectedAngle.attached_raw.split(/[\\/]/).pop()}
                  </span>
                </p>
                <p className="text-[10px] text-emerald-400/90 leading-tight">
                  💡 มีคลิปวัตถุดิบอยู่แล้ว คุณสามารถกดปุ่ม <span className="font-bold text-white">"ประกอบคลิปและเรนเดอร์"</span> ด้านล่างได้ทันที หรือเลือกถ่ายใหม่/แนบไฟล์ใหม่ด้านล่างเพื่อแทนที่
                </p>
              </div>
            ) : (
              <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/25 text-amber-200 text-xs flex items-start gap-2 shadow-sm">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div className="text-[11px] leading-relaxed">
                  <span className="font-bold text-amber-300 block">ยังไม่มีคลิปวัตถุดิบ</span>
                  กรุณาเลือก <span className="font-semibold text-white">ถ่ายสดหน้ากล้อง (Guided Take)</span> หรือ <span className="font-semibold text-white">เลือกคลิปจากอัลบั้มมือถือ</span> ด้านล่าง เพื่อใช้ประกอบคลิป
                </div>
              </div>
            )}

            {/* Dual Video Intake: Filming Camera OR Upload from Camera Roll */}
            <div className="grid grid-cols-1 gap-2.5">
              {/* Option A: Open Camera Teleprompter */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-cyan-500/30 text-center space-y-2.5 shadow-lg">
                <div className="flex items-center gap-3 text-left">
                  <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center text-lg shrink-0">
                    📹
                  </div>
                  <div>
                    <h3 className="font-bold text-xs text-white">ถ่ายสดหน้ากล้อง (Teleprompter)</h3>
                    <p className="text-[11px] text-slate-400">มีบทลอยอ่านง่าย ถ่ายทีละท่อน ซิงค์เข้า PC อัตโนมัติ</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleOpenFilming}
                  className="w-full py-2.5 px-3 rounded-xl font-bold text-xs bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-md shadow-cyan-500/20 flex items-center justify-center gap-2 cursor-pointer transition-transform active:scale-[0.98]"
                >
                  <Video className="w-3.5 h-3.5" />
                  <span>กดเปิดกล้องถ่ายทำ (Guided Take)</span>
                </button>
              </div>

              {/* Option B: Direct Mobile Camera Roll Upload */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-indigo-500/30 space-y-2.5 shadow-lg">
                <div className="flex items-center gap-3 text-left">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center text-lg shrink-0">
                    📁
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-xs text-white">แนบคลิปจากมือถือ (Camera Roll / Files)</h3>
                    <p className="text-[11px] text-slate-400">เลือกไฟล์วิดีโอที่มีอยู่ในเครื่องมือถือ เพื่อใช้ตัดต่อทันที</p>
                  </div>
                </div>

                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleUploadMobileVideo}
                  accept="video/*"
                  className="hidden"
                />

                {uploadedVideoPath ? (
                  <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
                    <span className="flex items-center gap-1.5 font-medium truncate">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      แนบคลิปแล้ว: {uploadedVideoName}
                    </span>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-[11px] underline text-emerald-400 hover:text-white shrink-0 ml-2 font-semibold"
                    >
                      เปลี่ยนคลิป
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    disabled={isUploading}
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full py-2.5 px-3 rounded-xl font-bold text-xs bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-500/30 flex items-center justify-center gap-2 cursor-pointer transition-transform active:scale-[0.98]"
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
                        <span>กำลังอัปโหลดวิดีโอ ({uploadProgress}%)...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="w-3.5 h-3.5 text-indigo-400" />
                        <span>เลือกคลิปจากอัลบั้มมือถือ</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Audio & Voice Control Box */}
            <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Volume2 className="w-4 h-4 text-cyan-400" />
                  เสียงพากย์ Fenrir (Commercial Premium)
                </span>
                <button
                  type="button"
                  onClick={handlePreviewVoice}
                  disabled={previewingVoice}
                  className="px-2.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-[11px] font-medium hover:bg-cyan-500/20 flex items-center gap-1 cursor-pointer"
                >
                  {previewingVoice ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                  <span>{previewingVoice ? 'กำลังสร้างเสียง...' : 'ฟังตัวอย่างเสียง'}</span>
                </button>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-xs">
                <span className="text-slate-300 flex items-center gap-1.5">
                  <Music className="w-3.5 h-3.5 text-amber-400" />
                  ดนตรี BGM ไอทีคึกคัก (0.14)
                </span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={bgmEnabled}
                    onChange={(e) => setBgmEnabled(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500"></div>
                </label>
              </div>
            </div>

            {/* Big Action: Proceed to Auto-Assemble */}
            <div className="pt-2 sticky bottom-[calc(env(safe-area-inset-bottom)+1rem)] space-y-2">
              <button
                disabled={!hasFootage}
                onClick={handleStartAssemble}
                title={hasFootage ? undefined : 'ต้องถ่ายทำหรือแนบคลิปก่อน'}
                className="w-full py-4 px-4 rounded-2xl font-extrabold text-base bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-slate-950 shadow-xl shadow-emerald-500/25 flex items-center justify-center gap-2 transition-all active:scale-[0.98] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100 disabled:shadow-none"
              >
                <Sparkles className="w-5 h-5 text-slate-950 fill-slate-950" />
                <span>ประกอบคลิปและเรนเดอร์</span>
              </button>
              {hasFootage ? (
                <p className="text-[11px] text-center text-slate-400">
                  AI จะประกอบคลิป + ซับ Mali-Bold + สเปกสีส้ม + เสียง Fenrir ให้อัตโนมัติ
                </p>
              ) : (
                <p className="text-[11px] text-center text-amber-300">
                  ยังไม่มีคลิปวัตถุดิบ — กรุณาถ่ายทำหรือแนบคลิปก่อน{' '}
                  <button
                    type="button"
                    onClick={() => refreshSessionFootage(sessionId)}
                    className="underline font-semibold text-amber-200 cursor-pointer"
                  >
                    ตรวจสอบคลิปอีกครั้ง
                  </button>
                </p>
              )}
            </div>
          </div>
        )}


        {/* STEP 3: Auto-Assemble Rendering Progress */}
        {step === 3 && (
          <div className="flex-1 flex flex-col items-center justify-center text-center space-y-6 py-8">
            <div className="relative w-28 h-28 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-4 border-slate-800 animate-pulse"></div>
              <div className="absolute inset-0 rounded-full border-4 border-cyan-500 border-t-transparent animate-spin"></div>
              <div className="text-2xl font-black text-cyan-400">
                {taskProgress}%
              </div>
            </div>

            <div className="space-y-2 max-w-xs">
              <h3 className="font-extrabold text-lg text-white">กำลังประกอบคลิปอัตโนมัติ</h3>
              <p className="text-xs text-cyan-400 font-medium animate-pulse">
                {taskStepLabel || 'ระบบกำลังประมวลผลคลิปตาม SOP...'}
              </p>
            </div>

            {pollPaused && (
              <button onClick={() => startPolling(taskId)} className="px-4 py-3 rounded-xl bg-cyan-500 text-slate-950 font-bold">ตรวจสถานะอีกครั้ง</button>
            )}

            {/* SOP Specifications Active */}
            <div className="w-full p-4 rounded-2xl bg-slate-900 border border-slate-800 text-left space-y-2 text-xs">
              <span className="font-semibold text-slate-400 text-[11px] block uppercase tracking-wider">
                สูตรตัดต่อระดับโปร (Gadget Master SOP):
              </span>
              <div className="flex items-center gap-2 text-slate-300">
                <Volume2 className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>เสียงพากย์ Fenrir (Commercial Premium)</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <Type className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>ซับไทย Mali-Bold (Ghost Reveal เขียวนีออน #66FF00)</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <Flame className="w-4 h-4 text-amber-500 shrink-0" />
                <span>กล่องสเปกหัวข้อขาว + ค่าสเปกสีส้มไฟนีออน (#FF6622)</span>
              </div>
            </div>

            {!pollPaused && (
              <button
                type="button"
                onClick={() => setShowCancelConfirm(true)}
                className="px-4 py-2.5 rounded-xl bg-slate-900 border border-rose-500/30 text-rose-300 font-semibold text-xs hover:bg-rose-500/10 cursor-pointer"
              >
                ยกเลิกการเรนเดอร์
              </button>
            )}
          </div>
        )}

        {/* STEP 4: Completed & 1-Click TikTok Share */}
        {step === 4 && (
          <div className="flex-1 flex flex-col space-y-4">
            <div className="text-center space-y-1">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold border border-emerald-500/30">
                <CheckCircle2 className="w-3.5 h-3.5" />
                เรนเดอร์สำเร็จ 100% พร้อมโพสต์!
              </div>
              <h2 className="text-lg font-extrabold text-white tracking-tight">
                {renderResult?.product_name || selectedProduct?.name}
              </h2>
            </div>

            {/* Video Player */}
            {renderResult?.video_url ? (
              <div className="w-full aspect-[9/16] max-h-[48vh] rounded-2xl overflow-hidden bg-black border border-slate-800 shadow-2xl relative">
                <video
                  src={renderResult.video_url}
                  controls
                  playsInline
                  className="w-full h-full object-contain"
                />
              </div>
            ) : (
              <div className="w-full aspect-[9/16] max-h-[40vh] rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 text-xs">
                ไม่พบไฟล์วิดีโอ
              </div>
            )}

            {/* Auto-generated Cover Preview (M04) */}
            {(renderResult?.cover_url || renderResult?.cover_9x16_url || renderResult?.cover_3x4_url || selectedAngle?.cover_url) && (
              <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    <span>ภาพปกที่สร้างอัตโนมัติ (Cover Preview)</span>
                  </div>
                  <span className="text-[10px] text-cyan-400 font-medium">9:16 Feed & 3:4 Grid</span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {/* Cover 9:16 */}
                  {(renderResult?.cover_9x16_url || renderResult?.cover_url || selectedAngle?.cover_9x16_url || selectedAngle?.cover_url) && (
                    <div className="relative rounded-xl overflow-hidden bg-black border border-slate-800 flex flex-col justify-between">
                      <div className="aspect-[9/16] w-full bg-slate-950 flex items-center justify-center">
                        <img
                          src={renderResult?.cover_9x16_url || renderResult?.cover_url || selectedAngle?.cover_9x16_url || selectedAngle?.cover_url}
                          alt="Cover 9:16"
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="p-1.5 bg-slate-900/90 flex items-center justify-between border-t border-slate-800">
                        <span className="text-[10px] font-bold text-slate-300">9:16 Feed</span>
                        <a
                          href={renderResult?.cover_9x16_url || renderResult?.cover_url || selectedAngle?.cover_9x16_url || selectedAngle?.cover_url}
                          download={`cover_9x16_${renderResult?.project_name || 'video'}.jpg`}
                          target="_blank"
                          rel="noreferrer"
                          className="py-0.5 px-1.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-[10px] font-bold flex items-center gap-1"
                        >
                          <Download className="w-2.5 h-2.5" /> โหลด
                        </a>
                      </div>
                    </div>
                  )}

                  {/* Cover 3:4 */}
                  {(renderResult?.cover_3x4_url || selectedAngle?.cover_3x4_url) && (
                    <div className="relative rounded-xl overflow-hidden bg-black border border-slate-800 flex flex-col justify-between">
                      <div className="aspect-[3/4] w-full bg-slate-950 flex items-center justify-center">
                        <img
                          src={renderResult?.cover_3x4_url || selectedAngle?.cover_3x4_url}
                          alt="Cover 3:4"
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="p-1.5 bg-slate-900/90 flex items-center justify-between border-t border-slate-800">
                        <span className="text-[10px] font-bold text-slate-300">3:4 Grid</span>
                        <a
                          href={renderResult?.cover_3x4_url || selectedAngle?.cover_3x4_url}
                          download={`cover_3x4_${renderResult?.project_name || 'video'}.jpg`}
                          target="_blank"
                          rel="noreferrer"
                          className="py-0.5 px-1.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-[10px] font-bold flex items-center gap-1"
                        >
                          <Download className="w-2.5 h-2.5" /> โหลด
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {renderResult?.mix_degraded && (
              <p role="status" className="text-xs text-amber-400">เสียงประกอบบางส่วนไม่พร้อม: {renderResult.mix_degraded_reason || 'ใช้เสียงพากย์เป็นหลัก'}</p>
            )}

            {/* Action Buttons */}
            <div className="space-y-2.5 pt-2">
              <button
                onClick={handleShareToTikTok}
                className="w-full py-4 px-4 rounded-2xl font-extrabold text-base bg-gradient-to-r from-pink-500 via-rose-500 to-amber-500 hover:from-pink-400 hover:to-amber-400 text-white shadow-xl shadow-rose-500/25 flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
              >
                <span>เปิดเมนูแชร์วิดีโอ</span>
              </button>

              {copiedCaption && (
                <p className="text-[11px] text-center text-emerald-400 font-semibold animate-bounce">
                  ✓ คัดลอกแคปชันและแฮชแท็กให้เรียบร้อยแล้ว!
                </p>
              )}

              <div className="flex gap-2">
                {renderResult?.video_url && (
                  <a
                    href={renderResult.video_url}
                    download
                    className="flex-1 py-3 px-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Download className="w-4 h-4 text-cyan-400" />
                    <span>เซฟลงอัลบั้ม</span>
                  </a>
                )}
                <button
                  onClick={() => {
                    stopPolling();
                    try { sessionStorage.removeItem(MOBILE_WORKFLOW_KEY); } catch { /* optional session memory */ }
                    const url = new URL(window.location.href);
                    ['mobile_session', 'product', 'angle'].forEach(key => url.searchParams.delete(key));
                    window.history.replaceState(null, '', url);
                    setStep(1);
                    setSessionId(null);
                    setSessionData(null);
                    setTaskId(null);
                    setRenderResult(null);
                    setPostedDone(false);
                  }}
                  className="flex-1 py-3 px-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                >
                  <RefreshCw className="w-4 h-4 text-emerald-400" />
                  <span>เริ่มทำคลิปใหม่</span>
                </button>
              </div>

              <button
                type="button"
                disabled={markingPosted || postedDone || !renderResult?.video_path}
                onClick={handleMarkPosted}
                className="w-full py-3 px-3 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{postedDone ? 'มาร์คว่าโพสต์แล้วเรียบร้อย' : 'มาร์คว่าโพสต์แล้ว'}</span>
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Hidden Audio Player for Voice Preview */}
      <audio ref={audioPlayerRef} className="hidden" />

      {/* P0-2: confirm before cancelling an in-flight render */}
      <ConfirmModal
        isOpen={showCancelConfirm}
        onClose={() => setShowCancelConfirm(false)}
        onConfirm={handleCancelRender}
        title="ยกเลิกการเรนเดอร์?"
        description="งานเรนเดอร์ที่กำลังทำจะหยุดกลางคัน และจะไม่สร้างไฟล์วิดีโอ"
        dangerNote="คลิปที่กำลังประกอบจะถูกยกเลิก"
        confirmText="ยืนยันยกเลิก"
        cancelText="ทำต่อ"
        loading={cancelling}
        variant="warning"
      />

      {/* Modal: Quick Add Product */}
      {showAddProductModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-end sm:items-center justify-center p-3 sm:p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-2xl relative space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <Plus className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">เพิ่มสินค้าใหม่</h3>
                  <p className="text-[11px] text-slate-400">วางลิงก์ TikTok หรือพิมพ์ชื่อสินค้า</p>
                </div>
              </div>
              <button
                onClick={() => { setShowAddProductModal(false); setNewProductInput(''); }}
                className="p-1.5 rounded-xl bg-slate-800/60 text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">
                ชื่อสินค้า หรือ ลิงก์ TikTok Shop
              </label>
              <textarea
                rows={3}
                value={newProductInput}
                onChange={(e) => setNewProductInput(e.target.value)}
                placeholder="เช่น หูฟังบลูทูธ Baseus Bowie M2 หรือวางลิงก์ https://vt.tiktok.com/..."
                className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors resize-none"
              />
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => { setShowAddProductModal(false); setNewProductInput(''); }}
                className="flex-1 py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                disabled={!newProductInput.trim() || addingProduct}
                onClick={handleQuickAddProduct}
                className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-cyan-500/20 transition-all flex items-center justify-center gap-1.5"
              >
                {addingProduct ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>กำลังเพิ่มสินค้า...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>เพิ่มสินค้าทันที</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Custom Angle & Script */}
      {showCustomAngleModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-end sm:items-center justify-center p-3 sm:p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-2xl relative space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <Flame className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">เขียนมุมและบทพูดเอง</h3>
                  <p className="text-[11px] text-slate-400">{selectedProduct?.name || 'กำหนดสคริปต์ตามต้องการ'}</p>
                </div>
              </div>
              <button
                onClick={() => { setShowCustomAngleModal(false); setCustomHookInput(''); setCustomScriptInput(''); }}
                className="p-1.5 rounded-xl bg-slate-800/60 text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  หัวข้อ Hook / จุดขายหลัก
                </label>
                <input
                  type="text"
                  value={customHookInput}
                  onChange={(e) => setCustomHookInput(e.target.value)}
                  placeholder="เช่น หูฟังตัดเสียงรบกวน 45dB ราคาหลักร้อย"
                  className="w-full bg-slate-950 border border-slate-800 rounded-2xl px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  บทพูดพากย์เสียง (สคริปต์สั้นกระชับ)
                </label>
                <textarea
                  rows={4}
                  value={customScriptInput}
                  onChange={(e) => setCustomScriptInput(e.target.value)}
                  placeholder="เช่น เบื่อไหมเสียงรอบข้างกวนใจเวลาทำงาน ตัวนี้ตัดเสียงเงียบกริบ แบตอึด 40 ชม. เบสนุ่มลึกเกินราคา กดที่ตะกร้าด่วน!"
                  className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors resize-none leading-relaxed"
                />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => { setShowCustomAngleModal(false); setCustomHookInput(''); setCustomScriptInput(''); }}
                className="flex-1 py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                disabled={!customHookInput.trim() || creatingAngle}
                onClick={() => handleCreateQuickAngle(customHookInput.trim(), customScriptInput.trim())}
                className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-1.5"
              >
                {creatingAngle ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>กำลังบันทึกมุม...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>บันทึกและไปต่อ</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
