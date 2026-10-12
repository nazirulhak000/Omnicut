import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  X,
  Sparkles,
  Check,
  Crop,
  Layers,
  Image as ImageIcon,
  Film,
  RefreshCw,
  ShieldAlert,
  Save,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Move,
  Folder,
  Loader2,
  ShoppingBag,
  Type,
  History,
} from 'lucide-react';
import {
  getCoverBadges,
  getCoverHighlights,
  generateCoverHooks,
  renderProCover,
  getCoverRawSources,
  getCoverProductRefImages,
  generateAiCoverImage,
  grabCoverFrame,
  revealFile,
} from '../api';
import { resolveCoverExportStem } from '../lib/coverNaming.js';
import { toMediaUrl } from '../lib/mediaUrl.js';
import { captureChannel, isCurrentChannel, registerChannelSwitchParticipant } from '../lib/channelRuntime.js';
import { createChannelDraftParticipant } from '../lib/channelDraft.js';

export default function CoverStudioModal({
  isOpen,
  onClose,
  videoItem,
  onCoverSaved,
}) {
  // Paths & info
  const videoPath = videoItem?.path || videoItem?.rel_path || '';
  const productName = videoItem?.product_name || videoItem?.name || 'สินค้า';
  const angleTitle = videoItem?.hook_title || videoItem?.angle_name || '';
  const timelineSnapshot = videoItem?.timeline_snapshot || null;
  const timelineSnapshotDataUrl = timelineSnapshot?.data_url || '';
  const timelineSnapshotSeconds = Number(timelineSnapshot?.seconds || 0);

  // State
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');
  const [savedResult, setSavedResult] = useState(null);
  const savedPreviewSignatureRef = useRef('');

  // Source selection: 'exported' | 'raw' | 'upload'
  const [activeSourceType, setActiveSourceType] = useState(
    timelineSnapshotDataUrl ? 'timeline' : 'exported',
  );
  const [rawSources, setRawSources] = useState([]);
  const [selectedRawPath, setSelectedRawPath] = useState('');

  // Frame selection
  const [duration, setDuration] = useState(15.0);
  const [candidates, setCandidates] = useState([]);
  const [currentSeconds, setCurrentSeconds] = useState(0.5);
  const [liveFrameUrl, setLiveFrameUrl] = useState(null);
  const [customImage, setCustomImage] = useState(null);
  const [customImageFile, setCustomImageFile] = useState(null);

  // Product reference images (scraped from TikTok Shop / catalog)
  const [productRefImages, setProductRefImages] = useState([]);
  const [selectedRefImage, setSelectedRefImage] = useState(null);

  // AI Cover Generation (Imagen 3 / Smart Frame Hunt)
  const [aiPrompt, setAiPrompt] = useState('');
  const [generatingAi, setGeneratingAi] = useState(false);
  const [aiGenMethod, setAiGenMethod] = useState('');
  const [lastAiCover, setLastAiCover] = useState(null); // { url, file, method }
  const [aiHistory, setAiHistory] = useState([]); // Array of { url, file, method, prompt, ts }

  // Zoom & Pan 2D (User request: drag directly on preview & zoom in/out to push subtitles away!)
  const [zoom, setZoom] = useState(1.15); // Default 1.15x to give a clean edge
  const [panX, setPanX] = useState(50);
  const [panY, setPanY] = useState(15); // Default 15% to bias towards upper part and eliminate bottom subtitles

  // Overlay Toggles (User request: DEFAULT UNCHECKED / OFF for clean frame mode!)
  const [enableHookText, setEnableHookText] = useState(false);
  const [enableBadge, setEnableBadge] = useState(false);

  // Aspect ratio choice: 'both' (default) | '3:4' | '9:16'
  const [aspectRatio, setAspectRatio] = useState('both');
  // Preview mode in modal: '9:16' (with 3:4 guide box) | '3:4' (direct profile card)
  const [previewMode, setPreviewMode] = useState('9:16');

  // Hooks & Copy
  const [hookIdeas, setHookIdeas] = useState([]);
  const [hookText, setHookText] = useState(
    angleTitle ? angleTitle : `อย่าเพิ่งซื้อ ${productName}\nถ้ายังไม่รู้สิ่งนี้!`
  );
  const [subText, setSubText] = useState('พิกัดในตะกร้าลดพิเศษ');
  const [hookPosition, setHookPosition] = useState('top'); // "top" | "center" | "bottom"

  // Template & Styling
  const [template, setTemplate] = useState('neon'); // "neon" | "yellow_bar" | "modern_box" | "minimal_bold"
  const [badges, setBadges] = useState([]);
  const [selectedBadge, setSelectedBadge] = useState('badge_best_seller_3d.png');
  const [badgePosition, setBadgePosition] = useState('top_left'); // "top_left" | "top_right" | "none"
  const [showSafeZone, setShowSafeZone] = useState(true);

  // Dragging state on preview canvas
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0, panX: 50, panY: 15 });

  // File input ref
  const fileInputRef = useRef(null);
  const ownerRef = useRef(captureChannel());
  const initializedDraftRef = useRef(false);
  const userEditedRef = useRef(false);
  const draftValue = { hookText, subText, aiPrompt, activeSourceType, selectedRawPath,
    currentSeconds, customImage, customImageFile, zoom, panX, panY, enableHookText,
    enableBadge, template, hookPosition, selectedBadge, badgePosition, aspectRatio };
  const draftRef = useRef(null);
  if (!draftRef.current) draftRef.current = createChannelDraftParticipant(draftValue);
  const draft = draftRef.current;
  draft.observe(draftValue, { reset: value => {
    setHookText(value.hookText); setSubText(value.subText); setAiPrompt(value.aiPrompt);
    setActiveSourceType(value.activeSourceType); setSelectedRawPath(value.selectedRawPath);
    setCurrentSeconds(value.currentSeconds); setCustomImage(value.customImage);
    setCustomImageFile(value.customImageFile); setZoom(value.zoom); setPanX(value.panX);
    setPanY(value.panY); setEnableHookText(value.enableHookText); setEnableBadge(value.enableBadge);
    setTemplate(value.template); setHookPosition(value.hookPosition);
    setSelectedBadge(value.selectedBadge); setBadgePosition(value.badgePosition);
    setAspectRatio(value.aspectRatio);
  } });
  const busyRef = useRef(false);
  busyRef.current = saving || generatingAi;
  useEffect(() => registerChannelSwitchParticipant({
    isDirty: () => busyRef.current || draft.isDirty(),
    save: async () => { throw new Error('บันทึกปกก่อนสลับช่อง หรือเลือกทิ้งการแก้ไข'); },
    discard: async () => {
      if (busyRef.current) throw new Error('รอให้การสร้างหรือบันทึกปกเสร็จก่อนทิ้งการแก้ไข');
      await draft.discard();
    },
  }), [draft]);
  useEffect(() => {
    const guardUnload = event => {
      if (!isOpen || (!busyRef.current && !draft.isDirty())) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', guardUnload);
    return () => window.removeEventListener('beforeunload', guardUnload);
  }, [draft, isOpen]);
  useEffect(() => {
    if (initializedDraftRef.current && !loading) {
      if (!userEditedRef.current) draft.markSaved(draftValue);
      initializedDraftRef.current = false;
    }
  });
  const handleClose = async () => {
    if (saving || generatingAi) return;
    if (draft.isDirty() && !window.confirm('ปิดสตูดิโอและทิ้งการแก้ไขปกที่ยังไม่ได้บันทึก?')) return;
    await draft.discard();
    onClose();
  };

  // Load initial data: badges, highlights, hooks, raw sources
  useEffect(() => {
    let mounted = true;
    if (!isOpen || !videoItem) return undefined;
    setLoading(true);
    setError(null);
    // ล้าง status การบันทึกปกจากสคริปก่อนหน้าทุกครั้งที่เปิด modal ใหม่
    setSuccessMsg('');
    setSavedResult(null);
    setActiveSourceType(timelineSnapshotDataUrl ? 'timeline' : 'exported');
    setCustomImage(timelineSnapshotDataUrl || null);
    setCustomImageFile(null);
    setCurrentSeconds(timelineSnapshotDataUrl ? timelineSnapshotSeconds : 0.5);
    setLiveFrameUrl(null);

    Promise.all([
      getCoverBadges().catch(() => ({ badges: [] })),
      generateCoverHooks(productName, angleTitle).catch(() => ({ hooks: [] })),
      videoPath
        ? getCoverHighlights(videoPath).catch(() => ({ candidates: [], duration: 15 }))
        : Promise.resolve({ candidates: [], duration: 15 }),
      videoPath
        ? getCoverRawSources(videoPath).catch(() => ({ raw_sources: [] }))
        : Promise.resolve({ raw_sources: [] }),
      getCoverProductRefImages({
        video_path: videoPath,
        product_id: videoItem?.product_id,
        product_name: productName,
      }).catch(() => ({ ref_images: [] })),
    ])
      .then(([bRes, hRes, hlRes, rawRes, refRes]) => {
        if (!mounted) return;
        setBadges(bRes.badges || []);
        setHookIdeas(hRes.hooks || []);
        if (hRes.hooks && hRes.hooks.length > 0 && !angleTitle) {
          setHookText(hRes.hooks[0].text);
        }
        if (hlRes.candidates && hlRes.candidates.length > 0) {
          setCandidates(hlRes.candidates);
          setDuration(hlRes.duration || 15);
          setCurrentSeconds(hlRes.candidates[0].timestamp);
          setLiveFrameUrl(hlRes.candidates[0].thumb_url);
        }
        if (rawRes.raw_sources && rawRes.raw_sources.length > 0) {
          setRawSources(rawRes.raw_sources);
          setSelectedRawPath(rawRes.raw_sources[0].path);
        }
        if (refRes?.ref_images && refRes.ref_images.length > 0) {
          setProductRefImages(refRes.ref_images);
        }
        setAiPrompt((prev) => prev || `Commercial 8k product photography of ${productName || 'product'}, sleek studio lighting, minimalist podium, vibrant cinematic colors, 9:16 vertical orientation, advertising poster quality`);
        initializedDraftRef.current = true;
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError('โหลดข้อมูลสตูดิโอไม่สำเร็จ: ' + (err.message || String(err)));
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [isOpen, videoPath, productName, angleTitle, videoItem?.product_id, timelineSnapshotDataUrl, timelineSnapshotSeconds]);

  // Live real-time frame fetching when scrubbing across any arbitrary seconds
  useEffect(() => {
    if (!isOpen || customImage) return undefined;
    const activeTarget = activeSourceType === 'raw' ? selectedRawPath : videoPath;
    if (!activeTarget) return undefined;

    // First check if currentSeconds closely matches an already pre-extracted candidate
    const matched = candidates.find((c) => Math.abs(c.timestamp - currentSeconds) < 0.25);
    if (matched) {
      setLiveFrameUrl(matched.thumb_url);
      return undefined;
    }

    // Otherwise, debounce grabCoverFrame from the backend to deliver the real frame
    const timer = setTimeout(async () => {
      try {
        const res = await grabCoverFrame(activeTarget, currentSeconds);
        if (res && res.media_url) {
          setLiveFrameUrl(res.media_url);
        }
      } catch {
        // ignore frame grab transient error while scrubbing fast
      }
    }, 90);

    return () => clearTimeout(timer);
  }, [isOpen, currentSeconds, activeSourceType, selectedRawPath, videoPath, customImage, candidates]);

  // Keep hook order stable across closed -> open transitions.
  if (!isOpen || !videoItem) return null;

  // When switching source to raw clip, load highlights from the raw clip
  const handleSwitchToRawSource = async (rawPath) => {
    setSelectedRawPath(rawPath);
    setActiveSourceType('raw');
    setCustomImage(null);
    setCustomImageFile(null);
    try {
      setLoading(true);
      const res = await getCoverHighlights(rawPath);
      if (res.candidates && res.candidates.length > 0) {
        setCandidates(res.candidates);
        setDuration(res.duration || 15);
        setCurrentSeconds(res.candidates[0].timestamp);
        setLiveFrameUrl(res.candidates[0].thumb_url);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  // Switch back to exported video
  const handleSwitchToExported = async () => {
    setActiveSourceType('exported');
    setCustomImage(null);
    setCustomImageFile(null);
    if (videoPath) {
      try {
        setLoading(true);
        const res = await getCoverHighlights(videoPath);
        if (res.candidates && res.candidates.length > 0) {
          setCandidates(res.candidates);
          setDuration(res.duration || 15);
          setCurrentSeconds(res.candidates[0].timestamp);
          setLiveFrameUrl(res.candidates[0].thumb_url);
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
  };

  const handleSwitchToTimeline = () => {
    if (!timelineSnapshotDataUrl) return;
    setActiveSourceType('timeline');
    setCustomImage(timelineSnapshotDataUrl);
    setCustomImageFile(null);
    setCurrentSeconds(timelineSnapshotSeconds);
    setLiveFrameUrl(null);
  };

  // Handle custom image upload
  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCustomImageFile(file);
    const url = URL.createObjectURL(file);
    setCustomImage(url);
    setActiveSourceType('upload');
  };

  // Handle AI Cover Image Generation (Imagen 3 / AI Studio Cutout)
  const handleGenerateAiCover = async (promptOverride) => {
    try {
      setGeneratingAi(true);
      setError(null);
      setSuccessMsg('');
      const targetPrompt = promptOverride || aiPrompt;
      const activeVideoTarget = activeSourceType === 'raw' ? selectedRawPath : (videoPath || rawSources[0]?.path || null);
      const activeRefSource = selectedRefImage?.local_path || selectedRefImage?.url || (activeSourceType === 'product_ref' ? customImageFile : null);
      const res = await generateAiCoverImage({
        product_name: productName,
        hook_title: hookText,
        style_prompt: targetPrompt,
        video_path: activeVideoTarget,
        at_seconds: Number(currentSeconds),
        source_image_path: activeRefSource,
      });
      if (res && res.success) {
        setCustomImage(res.media_url);
        setCustomImageFile(res.image_path);
        setAiGenMethod(res.method || 'imagen_3');
        const newCover = {
          url: res.media_url,
          file: res.image_path,
          method: res.method || 'imagen_3',
          prompt: targetPrompt,
          ts: Date.now(),
        };
        setLastAiCover(newCover);
        setAiHistory((prev) => [newCover, ...prev.filter((x) => x.url !== newCover.url)]);
        setActiveSourceType('ai_gen');
        setSuccessMsg(res.message || 'สร้างรูปหน้าปกด้วย AI สำเร็จแล้ว!');
      } else {
        throw new Error(res?.detail || 'สร้างรูปภาพไม่สำเร็จ');
      }
    } catch (err) {
      setError('สร้างภาพปกด้วย AI ไม่สำเร็จ: ' + (err.response?.data?.detail || err.message));
    } finally {
      setGeneratingAi(false);
    }
  };

  // Switch to product reference images from TikTok Shop / catalog
  const handleSwitchToProductRef = () => {
    setActiveSourceType('product_ref');
    if (selectedRefImage) {
      setCustomImage(selectedRefImage.url);
      setCustomImageFile(selectedRefImage.local_path || selectedRefImage.url);
    } else if (productRefImages.length > 0) {
      const first = productRefImages[0];
      setSelectedRefImage(first);
      setCustomImage(first.url);
      setCustomImageFile(first.local_path || first.url);
    }
  };

  const handleSelectProductRefImage = (img) => {
    setSelectedRefImage(img);
    setCustomImage(img.url);
    setCustomImageFile(img.local_path || img.url);
  };

  // Switch to AI Generated Cover tab (instantly restore previous AI cover if already generated)
  const handleSwitchToAiGen = () => {
    setActiveSourceType('ai_gen');
    if (lastAiCover?.url) {
      setCustomImage(lastAiCover.url);
      setCustomImageFile(lastAiCover.file);
      if (lastAiCover.method) setAiGenMethod(lastAiCover.method);
    }
  };

  // Switch to a candidate frame
  const handleSelectCandidate = (cand) => {
    setCurrentSeconds(cand.timestamp);
    setLiveFrameUrl(cand.thumb_url);
    setCustomImage(null);
    setCustomImageFile(null);
  };


  const getPreviewSignature = () => JSON.stringify([
    videoPath,
    activeSourceType,
    selectedRawPath,
    currentSeconds,
    customImage,
    zoom,
    panX,
    panY,
    enableHookText,
    enableBadge,
    template,
    hookText,
    subText,
    hookPosition,
    selectedBadge,
    badgePosition,
    aspectRatio,
  ]);

  // Find active preview image source
  const getPreviewImageSrc = () => {
    if (customImage) return customImage;
    if (liveFrameUrl) return liveFrameUrl;
    const matched = candidates.find((c) => Math.abs(c.timestamp - currentSeconds) < 0.25);
    if (matched) return matched.thumb_url;
    if (candidates.length > 0) return candidates[0].thumb_url;
    return videoItem.thumbnail_url || videoItem.cover_url || '';
  };

  // Once saved, show the exact 3:4 file only while the editor still matches
  // the saved settings. Any subsequent edit automatically returns to the
  // live frame preview, so the user never mistakes a stale render for a draft.
  const getSavedPreviewImageSrc = () => {
    if (previewMode !== '3:4' || !savedResult) return '';
    if (savedPreviewSignatureRef.current !== getPreviewSignature()) return '';
    return savedResult.media_url_3x4 || (aspectRatio === '3:4' ? savedResult.media_url : '');
  };

  // Drag handlers on preview screen
  const handleMouseDown = (e) => {
    isDraggingRef.current = true;
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      panX,
      panY,
    };
  };

  const handleMouseMove = (e) => {
    if (!isDraggingRef.current) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    // Dragging down pulls top frame down (decreases panY)
    const deltaPanX = (dx / 270) * 100;
    const deltaPanY = (dy / 480) * 100;
    setPanX(Math.max(0, Math.min(100, Math.round(dragStartRef.current.panX - deltaPanX))));
    setPanY(Math.max(0, Math.min(100, Math.round(dragStartRef.current.panY - deltaPanY))));
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  // Touch handlers for mobile/tablet screens
  const handleTouchStart = (e) => {
    if (!e.touches || e.touches.length === 0) return;
    isDraggingRef.current = true;
    dragStartRef.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
      panX,
      panY,
    };
  };

  const handleTouchMove = (e) => {
    if (!isDraggingRef.current || !e.touches || e.touches.length === 0) return;
    const dx = e.touches[0].clientX - dragStartRef.current.x;
    const dy = e.touches[0].clientY - dragStartRef.current.y;
    const deltaPanX = (dx / 270) * 100;
    const deltaPanY = (dy / 480) * 100;
    setPanX(Math.max(0, Math.min(100, Math.round(dragStartRef.current.panX - deltaPanX))));
    setPanY(Math.max(0, Math.min(100, Math.round(dragStartRef.current.panY - deltaPanY))));
  };

  // Wheel zoom handler
  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.05 : 0.05;
    setZoom((prev) => Math.max(1.0, Math.min(2.5, +(prev + delta).toFixed(2))));
  };

  // Reset Zoom & Pan
  const handleResetPanZoom = () => {
    setZoom(1.0);
    setPanX(50);
    setPanY(25);
  };

  // Save Cover (3:4, 9:16, or both)
  const handleSaveCover = async () => {
    if (saving || generatingAi || !isCurrentChannel(ownerRef.current)) return;
    const savedDraft = structuredClone(draftValue);
    const savedSignature = getPreviewSignature();
    try {
      setSaving(true);
      setError(null);
      setSuccessMsg('');

      const activeVideoTarget = activeSourceType === 'raw' ? selectedRawPath : videoPath;
      const exportStem = resolveCoverExportStem(videoItem);
      const isTimelineSnapshot = activeSourceType === 'timeline' && customImage?.startsWith('data:image/');

      const payload = {
        video_path: videoItem?.export_id ? videoPath : (isTimelineSnapshot ? null : activeVideoTarget),
        raw_video_path: activeSourceType === 'raw' ? selectedRawPath : null,
        custom_image_data: isTimelineSnapshot ? customImage : null,
        export_filename: exportStem,
        export_id: videoItem?.export_id || null,
        at_seconds: Number(currentSeconds),
        pan_y_pct: Number(panY),
        pan_x_pct: Number(panX),
        zoom_scale: Number(zoom),
        aspect_ratio: aspectRatio,
        enable_hook_text: enableHookText,
        enable_badge: enableBadge,
        template,
        hook_text: enableHookText ? hookText : '',
        sub_text: enableHookText ? subText : '',
        hook_position: hookPosition,
        badge: enableBadge ? selectedBadge : null,
        badge_position: enableBadge ? badgePosition : 'none',
        custom_image_path: customImageFile || null,
      };

      const res = await renderProCover(payload, ownerRef.current);
      if (!isCurrentChannel(ownerRef.current)) return;
      if (res && res.success) {
        draft.markSaved(savedDraft);
        savedPreviewSignatureRef.current = savedSignature;
        setSavedResult(res);
        const ratioLabel =
          aspectRatio === 'both' ? 'ทั้ง 9:16 และ 3:4' : aspectRatio === '3:4' ? '3:4' : '9:16';
        setSuccessMsg(`บันทึกภาพปก (${ratioLabel}) สำเร็จแล้ว!`);
        if (onCoverSaved) {
          await onCoverSaved({
            cover_path: res.cover_path,
            media_url: res.media_url,
            cover_3x4_path: res.cover_3x4_path || null,
            media_url_3x4: res.media_url_3x4 || null,
          }, ownerRef.current);
        }
      } else {
        throw new Error(res?.detail || 'บันทึกไม่สำเร็จ');
      }
    } catch (err) {
      setError('สร้างภาพปกไม่สำเร็จ: ' + (err.friendlyMessage || err.message || String(err)));
    } finally {
      setSaving(false);
    }
  };

  // Calculate 3:4 Guide Frame Box position inside 270x480 preview
  // In 270x480 container, 3:4 target height is 270 * (4 / 3) = 360px
  // Max vertical offset = 480 - 360 = 120px
  const guideBoxH = 360;
  const guideBoxTop = Math.round(120 * (panY / 100));
  const savedPreviewImageSrc = getSavedPreviewImageSrc();
  const previewImageSrc = savedPreviewImageSrc || getPreviewImageSrc();
  const showingSavedPreview = Boolean(savedPreviewImageSrc);
  // videoPath empty means the angle has no rendered export at all -- there is
  // no frame to ever load, so the "loading" spinner would spin forever.
  // Distinguish that from a genuinely in-flight fetch.
  const noVideoSource = !loading && !previewImageSrc && !videoPath;

  return createPortal(
    <div role="dialog" aria-label="สตูดิโอสร้างปก" onChangeCapture={() => { userEditedRef.current = true; }} className="fixed inset-0 z-[10000] flex items-center justify-center p-3 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-5xl max-h-[94vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <ImageIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
                สตูดิโอสร้างปกคลิป TikTok (Cover & Hook Studio)
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-medium">
                  3:4 & 9:16
                </span>
              </h2>
              <p className="text-xs text-slate-400 truncate max-w-xl">
                {productName} {angleTitle ? `• ${angleTitle}` : ''}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            aria-label="ปิดสตูดิโอสร้างปก"
            disabled={saving || generatingAi}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 gap-0">
          {/* Left Column: Live Canvas Preview (5 cols) */}
          <div className="lg:col-span-5 bg-slate-950/90 p-5 flex flex-col items-center justify-center border-r border-slate-800/80 relative select-none">
            {/* Aspect Ratio Preview Mode Switcher */}
            <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800 mb-2.5 text-xs">
              <button
                type="button"
                onClick={() => setPreviewMode('9:16')}
                className={`px-3 py-1 rounded-lg font-bold transition-colors cursor-pointer ${
                  previewMode === '9:16'
                    ? 'bg-amber-500 text-slate-950 shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                9:16 เต็มจอ (กรอบ 3:4)
              </button>
              <button
                type="button"
                onClick={() => setPreviewMode('3:4')}
                className={`px-3 py-1 rounded-lg font-bold transition-colors cursor-pointer ${
                  previewMode === '3:4'
                    ? 'bg-amber-500 text-slate-950 shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                3:4 การ์ดหน้าโปรไฟล์
              </button>
            </div>

            {/* Interactive Preview Canvas Container */}
            {previewMode === '9:16' ? (
              /* 9:16 Full Screen Preview with 3:4 Red Outline Guide & Interactive Drag */
              <div
                className="relative w-[270px] h-[480px] rounded-2xl overflow-hidden shadow-2xl border-2 border-slate-700/80 bg-slate-900 flex items-center justify-center cursor-grab active:cursor-grabbing group"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleMouseUp}
                onWheel={handleWheel}
                title="คลิกค้างแล้วลากเพื่อเลื่อนตำแหน่งภาพ | หมุนลูกกลิ้งเมาส์เพื่อซูมเข้า-ออก"
              >
                {/* Background Frame with Zoom & Pan */}
                {previewImageSrc ? (
                  <img
                    src={toMediaUrl(previewImageSrc, ownerRef.current.channel_id)}
                    alt="Cover Frame"
                    className="absolute inset-0 w-full h-full object-cover select-none pointer-events-none transition-transform duration-75"
                    style={{
                      objectPosition: `${panX}% ${panY}%`,
                      transform: `scale(${zoom})`,
                      transformOrigin: `${panX}% ${panY}%`,
                    }}
                    draggable={false}
                  />
                ) : noVideoSource ? (
                  <div className="flex flex-col items-center gap-2 px-6 text-center text-slate-400">
                    <ShieldAlert className="w-8 h-8 text-amber-400" />
                    <span className="text-xs font-semibold text-slate-300">ยังไม่มีคลิปที่เรนเดอร์</span>
                    <span className="text-[11px] text-slate-500">เรนเดอร์คลิปให้เสร็จก่อน แล้วค่อยสร้างปก</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <Film className="w-8 h-8 opacity-40 animate-pulse" />
                    <span className="text-xs">กำลังโหลดเฟรมวิดีโอ...</span>
                  </div>
                )}

                {/* 3:4 TikTok Profile Red Guide Frame with outside shadow */}
                <div
                  className="absolute inset-x-0 border-2 border-red-500/90 pointer-events-none z-20 transition-all shadow-[0_0_0_9999px_rgba(0,0,0,0.42)]"
                  style={{
                    top: `${guideBoxTop}px`,
                    height: `${guideBoxH}px`,
                  }}
                >
                  <div className="absolute top-1.5 left-2 px-1.5 py-0.5 rounded bg-red-600/95 text-white font-bold text-[9px] tracking-wider shadow">
                    กรอบโปรไฟล์ TikTok (3:4)
                  </div>
                </div>

                {/* Hook Text Layer (Only when enableHookText is True) */}
                {enableHookText && (
                  <div
                    className="absolute inset-x-3 pointer-events-none transition-all flex flex-col items-center text-center z-30"
                    style={{
                      top:
                        hookPosition === 'top' ? '22%' : hookPosition === 'center' ? '46%' : '65%',
                    }}
                  >
                    {template === 'yellow_bar' && (
                      <div className="flex flex-col items-center gap-1.5 max-w-full">
                        {hookText.split('\n').map((line, idx) => (
                          <span
                            key={idx}
                            className="bg-[#FFE600] text-black font-black px-3.5 py-1 rounded-lg text-sm shadow-md leading-tight"
                          >
                            {line}
                          </span>
                        ))}
                        {subText && (
                          <span className="bg-black/90 text-white font-bold px-2.5 py-0.5 rounded-md text-[11px] mt-0.5 shadow">
                            {subText}
                          </span>
                        )}
                      </div>
                    )}

                    {template === 'modern_box' && (
                      <div className="bg-slate-900/85 border border-[#25F4EE] rounded-xl px-4 py-2.5 shadow-xl backdrop-blur-sm max-w-full">
                        {hookText.split('\n').map((line, idx) => (
                          <p
                            key={idx}
                            className="text-white font-black text-sm drop-shadow leading-tight"
                          >
                            {line}
                          </p>
                        ))}
                        {subText && (
                          <p className="text-[#FFE600] font-bold text-[11px] mt-1 drop-shadow">
                            {subText}
                          </p>
                        )}
                      </div>
                    )}

                    {template === 'minimal_bold' && (
                      <div className="flex flex-col items-center gap-1 max-w-full">
                        {hookText.split('\n').map((line, idx) => (
                          <span
                            key={idx}
                            className="text-white font-black text-base leading-tight"
                            style={{
                              textShadow:
                                '0 0 4px #000, 0 0 6px #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000',
                            }}
                          >
                            {line}
                          </span>
                        ))}
                        {subText && (
                          <span
                            className="text-[#FFE600] font-extrabold text-xs mt-0.5"
                            style={{
                              textShadow:
                                '0 0 3px #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000',
                            }}
                          >
                            {subText}
                          </span>
                        )}
                      </div>
                    )}

                    {template === 'neon' && (
                      <div className="flex flex-col items-center gap-1 max-w-full">
                        {hookText.split('\n').map((line, idx) => (
                          <span
                            key={idx}
                            className="text-[#FFE600] font-black text-base leading-tight"
                            style={{
                              textShadow:
                                '0 0 6px #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 2px 4px 6px rgba(0,0,0,0.8)',
                            }}
                          >
                            {line}
                          </span>
                        ))}
                        {subText && (
                          <span
                            className="text-white font-bold text-xs mt-0.5"
                            style={{
                              textShadow:
                                '0 0 3px #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000',
                            }}
                          >
                            {subText}
                          </span>
                        )}
                      </div>
                    )}

                    {template === 'tech_neon' && (
                      <div className="flex flex-col items-center gap-0.5 max-w-full">
                        {hookText.split('\n').map((line, idx) => {
                          const isBrand = idx === 0;
                          return (
                            <span
                              key={idx}
                              className={`font-black uppercase tracking-wider leading-none ${
                                isBrand
                                  ? 'text-white text-base sm:text-lg'
                                  : 'text-[#39FF14] text-lg sm:text-xl italic'
                              }`}
                              style={{
                                textShadow:
                                  '0 0 4px #000, 0 0 8px #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0 3px 6px rgba(0,0,0,0.95)',
                              }}
                            >
                              {line}
                            </span>
                          );
                        })}
                        {subText && (
                          <div className="mt-1 bg-black/85 border border-[#39FF14]/80 px-2.5 py-0.5 rounded-full shadow-lg">
                            <span className="text-white font-bold text-[10px] tracking-wide">
                              {subText}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* 3D Badge (Only when enableBadge is True) */}
                {enableBadge && selectedBadge && badgePosition !== 'none' && (
                  <div
                    className="absolute pointer-events-none z-30"
                    style={{
                      top: '16px',
                      left: badgePosition === 'top_left' ? '12px' : 'auto',
                      right: badgePosition === 'top_right' ? '12px' : 'auto',
                    }}
                  >
                    {badges.find((b) => b.id === selectedBadge) ? (
                      <img
                        src={toMediaUrl(badges.find((b) => b.id === selectedBadge)?.url, ownerRef.current.channel_id)}
                        alt="3D Badge"
                        className="w-16 h-auto drop-shadow-lg object-contain"
                      />
                    ) : null}
                  </div>
                )}

                {/* Safe Zone Guide */}
                {showSafeZone && (
                  <div className="absolute inset-0 pointer-events-none z-35">
                    <div className="absolute bottom-0 inset-x-0 h-[100px] bg-red-500/20 border-t border-red-500/40 flex flex-col items-center justify-center px-2 text-center">
                      <span className="text-[10px] text-red-300 font-bold">
                        TikTok Caption & Audio Zone
                      </span>
                      <span className="text-[8px] text-red-300/80">Safe Zone 420px</span>
                    </div>
                  </div>
                )}

                {/* Drag hint overlay on hover */}
                <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/70 text-slate-300 text-[9px] pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-40 flex items-center gap-1">
                  <Move className="w-2.5 h-2.5" />
                  ลากเพื่อจัดตำแหน่ง
                </div>
              </div>
            ) : (
              /* 3:4 Direct Profile Card Preview */
              <div
                className="relative w-[270px] h-[360px] rounded-2xl overflow-hidden shadow-2xl border-2 border-red-500/80 bg-slate-900 flex items-center justify-center cursor-grab active:cursor-grabbing group"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleMouseUp}
                onWheel={handleWheel}
                title="คลิกค้างแล้วลากเพื่อเลื่อนตำแหน่งภาพ | หมุนลูกกลิ้งเมาส์เพื่อซูมเข้า-ออก"
              >
                {previewImageSrc ? (
                  <img
                    src={toMediaUrl(previewImageSrc, ownerRef.current.channel_id)}
                    alt="Cover Frame 3:4"
                    className="absolute inset-0 w-full h-full object-cover select-none pointer-events-none transition-transform duration-75"
                    style={{
                      objectPosition: `${panX}% ${panY}%`,
                      transform: `scale(${zoom})`,
                      transformOrigin: `${panX}% ${panY}%`,
                    }}
                    draggable={false}
                  />
                ) : noVideoSource ? (
                  <div className="flex flex-col items-center gap-2 px-6 text-center text-slate-400">
                    <ShieldAlert className="w-8 h-8 text-amber-400" />
                    <span className="text-xs font-semibold text-slate-300">ยังไม่มีคลิปที่เรนเดอร์</span>
                    <span className="text-[11px] text-slate-500">เรนเดอร์คลิปให้เสร็จก่อน แล้วค่อยสร้างปก</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <Film className="w-8 h-8 opacity-40 animate-pulse" />
                    <span className="text-xs">กำลังโหลดเฟรมวิดีโอ...</span>
                  </div>
                )}

                {/* Hook Text Layer (if enabled) */}
                {enableHookText && !showingSavedPreview && (
                  <div
                    className="absolute inset-x-3 pointer-events-none transition-all flex flex-col items-center text-center z-30"
                    style={{
                      top:
                        hookPosition === 'top' ? '18%' : hookPosition === 'center' ? '42%' : '65%',
                    }}
                  >
                    {template === 'yellow_bar' && (
                      <div className="flex flex-col items-center gap-1 max-w-full">
                        {hookText.split('\n').map((line, idx) => (
                          <span
                            key={idx}
                            className="bg-[#FFE600] text-black font-black px-3 py-0.5 rounded-lg text-xs shadow leading-tight"
                          >
                            {line}
                          </span>
                        ))}
                      </div>
                    )}
                    {template === 'neon' && (
                      <div className="flex flex-col items-center gap-0.5 max-w-full">
                        {hookText.split('\n').map((line, idx) => (
                          <span
                            key={idx}
                            className="text-[#FFE600] font-black text-sm leading-tight drop-shadow-md"
                          >
                            {line}
                          </span>
                        ))}
                      </div>
                    )}
                    {template === 'modern_box' && (
                      <div className="bg-slate-900/85 border border-[#25F4EE] rounded-xl px-3 py-2 shadow-lg max-w-full">
                        {hookText.split('\n').map((line, idx) => (
                          <p key={idx} className="text-white font-black text-xs leading-tight">
                            {line}
                          </p>
                        ))}
                      </div>
                    )}
                    {template === 'minimal_bold' && (
                      <div className="flex flex-col items-center gap-0.5 max-w-full">
                        {hookText.split('\n').map((line, idx) => (
                          <span key={idx} className="text-white font-black text-sm leading-tight">
                            {line}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 3D Badge */}
                {enableBadge && !showingSavedPreview && selectedBadge && badgePosition !== 'none' && (
                  <div
                    className="absolute pointer-events-none z-30"
                    style={{
                      top: '12px',
                      left: badgePosition === 'top_left' ? '10px' : 'auto',
                      right: badgePosition === 'top_right' ? '10px' : 'auto',
                    }}
                  >
                    {badges.find((b) => b.id === selectedBadge) ? (
                      <img
                        src={toMediaUrl(badges.find((b) => b.id === selectedBadge)?.url, ownerRef.current.channel_id)}
                        alt="3D Badge"
                        className="w-14 h-auto drop-shadow-lg object-contain"
                      />
                    ) : null}
                  </div>
                )}

                <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-black/70 text-white font-mono text-[10px]">
                  ตัวอย่างการ์ดช่อง (3:4)
                </div>
              </div>
            )}

            {/* Zoom & Pan Live Controls Bar */}
            <div className="w-[270px] mt-2.5 space-y-1.5">
              {/* Zoom slider + quick presets */}
              <div className="flex items-center justify-between text-[11px] text-slate-300">
                <span className="flex items-center gap-1 font-bold text-amber-400">
                  <ZoomIn className="w-3.5 h-3.5" />
                  ซูม: {zoom.toFixed(2)}x
                </span>
                <div className="flex items-center gap-1">
                  {[
                    { val: 1.0, label: '1x' },
                    { val: 1.25, label: '1.25x' },
                    { val: 1.5, label: '1.5x' },
                  ].map((preset) => (
                    <button
                      key={preset.val}
                      type="button"
                      onClick={() => setZoom(preset.val)}
                      className={`px-1.5 py-0.2 rounded text-[10px] cursor-pointer transition-colors ${
                        zoom === preset.val
                          ? 'bg-amber-500 text-slate-950 font-bold'
                          : 'bg-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={handleResetPanZoom}
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer"
                    title="รีเซ็ตการซูมและตำแหน่ง"
                  >
                    <RotateCcw className="w-2.5 h-2.5" />
                  </button>
                </div>
              </div>

              <input
                type="range"
                min="1.0"
                max="2.5"
                step="0.05"
                value={zoom}
                onChange={(e) => setZoom(parseFloat(e.target.value))}
                className="w-full accent-amber-400 h-1.5 bg-slate-700 rounded-lg cursor-pointer"
              />

              <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
                <label className="flex items-center gap-1 cursor-pointer hover:text-slate-200">
                  <input
                    type="checkbox"
                    checked={showSafeZone}
                    onChange={(e) => setShowSafeZone(e.target.checked)}
                    className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0 w-3 h-3 cursor-pointer"
                  />
                  <span>Safe Zone ล่างจอ</span>
                </label>

                <span className="font-mono text-cyan-400/80">
                  {currentSeconds.toFixed(1)}s
                </span>
              </div>
            </div>
          </div>

          {/* Right Column: Controls & Customization (7 cols) */}
          <div className="lg:col-span-7 p-6 overflow-y-auto max-h-[calc(94vh-130px)] space-y-5">
            {/* Section 1: Image Source & Frame Selection */}
            <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                  <Film className="w-4 h-4" />
                  1. แหล่งภาพ & เลือกช็อตเด่น
                </label>

                {/* Hidden File Input */}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleImageUpload}
                  accept="image/*"
                  className="hidden"
                />
              </div>

              {/* Source Type Selector Tabs */}
              <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                {timelineSnapshotDataUrl && (
                  <button
                    type="button"
                    onClick={handleSwitchToTimeline}
                    className={`flex-1 py-1.5 px-2 rounded-lg font-bold transition-all text-center cursor-pointer ${
                      activeSourceType === 'timeline'
                        ? 'bg-cyan-500/20 text-cyan-300 shadow border border-cyan-500/40'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    เฟรมจากไทม์ไลน์ ({timelineSnapshotSeconds.toFixed(1)}s)
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleSwitchToExported}
                  disabled={!videoPath}
                  className={`flex-1 py-1.5 px-2 rounded-lg font-bold transition-all text-center cursor-pointer ${
                    activeSourceType === 'exported'
                      ? 'bg-slate-800 text-white shadow border border-slate-700'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  วิดีโอ Export (มีไตเติล)
                </button>

                {rawSources.length > 0 && (
                  <button
                    type="button"
                    onClick={() => handleSwitchToRawSource(rawSources[0].path)}
                    className={`flex-1 py-1.5 px-2 rounded-lg font-bold transition-all text-center cursor-pointer ${
                      activeSourceType === 'raw'
                        ? 'bg-emerald-500/20 text-emerald-300 shadow border border-emerald-500/40'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    วิดีโอ Raw ต้นฉบับ (ไร้ซับ)
                  </button>
                )}

                {productRefImages.length > 0 && (
                  <button
                    type="button"
                    onClick={handleSwitchToProductRef}
                    className={`py-1.5 px-3 rounded-lg font-bold transition-all text-center cursor-pointer flex items-center gap-1.5 ${
                      activeSourceType === 'product_ref'
                        ? 'bg-amber-500/25 text-amber-300 shadow border border-amber-500/50 ring-1 ring-amber-400/30'
                        : 'text-amber-400/80 hover:text-amber-200'
                    }`}
                  >
                    <ShoppingBag className="w-3.5 h-3.5 text-amber-400" />
                    รูปสินค้า TikTok ({productRefImages.length})
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className={`py-1.5 px-3 rounded-lg font-bold transition-all text-center cursor-pointer flex items-center gap-1 ${
                    activeSourceType === 'upload'
                      ? 'bg-cyan-500/20 text-cyan-300 shadow border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Crop className="w-3 h-3" />
                  อัปโหลดรูป
                </button>

                <button
                  type="button"
                  onClick={handleSwitchToAiGen}
                  className={`py-1.5 px-3 rounded-lg font-bold transition-all text-center cursor-pointer flex items-center gap-1 ${
                    activeSourceType === 'ai_gen'
                      ? 'bg-purple-500/25 text-purple-300 shadow border border-purple-500/50 ring-1 ring-purple-400/30'
                      : 'text-purple-400 hover:text-purple-200'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  AI สร้างรูป 9:16
                </button>
              </div>

              {activeSourceType === 'timeline' && timelineSnapshotDataUrl && (
                <div className="flex items-start gap-2 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.06] px-3 py-2 text-[11px] leading-relaxed text-cyan-100/80">
                  <Film className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-cyan-300" />
                  <span>ใช้ภาพจาก Timeline ณ {timelineSnapshotSeconds.toFixed(1)} วินาที รวม Overlay, ซับ และสีที่กำลังแสดงใน Preview แล้ว สร้างปกได้ทันทีโดยไม่ต้องรอ Render</span>
                </div>
              )}

              {/* TikTok Shop Scraped Reference Images Panel */}
              {activeSourceType === 'product_ref' && (
                <div className="p-3.5 rounded-xl bg-gradient-to-br from-amber-950/30 via-slate-900 to-slate-950 border border-amber-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShoppingBag className="w-4 h-4 text-amber-400" />
                      <span className="text-xs font-bold text-amber-200">
                        รูปสินค้าคมชัดจาก TikTok Shop / แคตตาล็อก ({productRefImages.length} รูป)
                      </span>
                    </div>
                    <span className="text-[10px] text-amber-300/80 font-mono">
                      คลิกเลือกรูปเพื่อใช้เป็นปก หรือส่งให้ AI
                    </span>
                  </div>
                  <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 gap-2 max-h-48 overflow-y-auto pr-1">
                    {productRefImages.map((img, idx) => {
                      const isSelected = (selectedRefImage?.url === img.url) || (customImage === img.url);
                      return (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSelectProductRefImage(img)}
                          className={`group relative aspect-square rounded-lg overflow-hidden border transition-all cursor-pointer ${
                            isSelected
                              ? 'border-amber-400 ring-2 ring-amber-400/60 shadow-lg scale-95'
                              : 'border-white/10 hover:border-amber-400/50 hover:scale-100'
                          }`}
                        >
                          <img src={toMediaUrl(img.url, ownerRef.current.channel_id)} alt={img.name} className="w-full h-full object-cover" />
                          <div className="absolute inset-x-0 bottom-0 bg-black/60 px-1 py-0.5 text-[9px] text-white truncate text-center font-mono">
                            #{idx + 1}
                          </div>
                          {isSelected && (
                            <div className="absolute top-1 right-1 bg-amber-500 text-slate-950 p-0.5 rounded-full shadow">
                              <Check className="w-2.5 h-2.5 stroke-[3]" />
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                  <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400 border-t border-white/[0.06]">
                    <span>เลือกรูปนี้แล้ว สามารถเปิดแท็บ <b>AI สร้างรูป 9:16</b> ให้ AI นำรูปไปจัดฉากสตูดิโอใหม่ได้ทันที</span>
                    <button
                      type="button"
                      onClick={handleSwitchToAiGen}
                      className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white rounded-md text-xs font-bold transition-all flex items-center gap-1 shadow cursor-pointer"
                    >
                      <Sparkles className="w-3 h-3" />
                      ส่งรูปนี้ให้ AI ผสานฉาก
                    </button>
                  </div>
                </div>
              )}

              {/* AI Image Generator Panel */}
              {activeSourceType === 'ai_gen' && (
                <div className="p-3.5 rounded-xl bg-gradient-to-br from-purple-950/40 via-slate-900 to-slate-950 border border-purple-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-400" />
                      <span className="text-xs font-bold text-purple-200">
                        AI Product Studio (ผสานช็อตสินค้าจริง + ฉากสตูดิโอ 9:16)
                      </span>
                    </div>
                    {aiGenMethod && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">
                        {aiGenMethod.includes('cutout')
                          ? '✨ ช็อตสินค้าจริง + ฉาก AI Studio'
                          : aiGenMethod === 'imagen_3'
                          ? '⚡ Imagen 3 (9:16)'
                          : aiGenMethod === 'ai_free'
                          ? '✨ AI Studio (9:16)'
                          : '🎯 Smart Studio'}
                      </span>
                    )}
                  </div>

                  {/* AI Generated Covers Gallery (เก็บทุกรูปที่สร้างในรอบนี้ ไม่ถูกทับ สลับเลือกได้ตลอด) */}
                  {(aiHistory.length > 0 || lastAiCover?.url) && (
                    <div className="p-2.5 rounded-lg bg-purple-950/60 border border-purple-500/40 space-y-2 shadow-inner">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-[11px] font-bold text-purple-200">
                          <History className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                          <span>คลังภาพ AI ที่สร้างรอบนี้ ({(aiHistory.length > 0 ? aiHistory : [lastAiCover]).length} รูป ไม่ถูกทับ/บันทึกถาวร)</span>
                        </div>
                        <span className="text-[10px] text-purple-300/80">คลิกที่รูปเพื่อเลือกแสดงบนปก</span>
                      </div>

                      <div className="flex gap-2 overflow-x-auto pb-1 pt-0.5 scrollbar-thin">
                        {(aiHistory.length > 0 ? aiHistory : [lastAiCover]).map((item, idx) => {
                          const isActive = customImage === item.url;
                          return (
                            <button
                              key={item.url || idx}
                              type="button"
                              onClick={() => {
                                setCustomImage(item.url);
                                setCustomImageFile(item.file);
                                if (item.method) setAiGenMethod(item.method);
                                setLastAiCover(item);
                              }}
                              className={`group relative shrink-0 w-16 h-28 rounded-lg overflow-hidden border-2 transition-all cursor-pointer flex flex-col ${
                                isActive
                                  ? 'border-amber-400 ring-2 ring-amber-400/50 scale-105 shadow-lg'
                                  : 'border-purple-800/80 opacity-75 hover:opacity-100 hover:border-purple-400'
                              }`}
                              title={`ภาพ AI รอบที่ ${idx + 1}`}
                            >
                              <img
                                src={toMediaUrl(item.url, ownerRef.current.channel_id)}
                                alt={`AI Cover ${idx + 1}`}
                                className="w-full h-full object-cover"
                              />
                              <span className="absolute top-1 left-1 px-1 py-0.2 rounded bg-black/80 font-mono text-[9px] text-amber-300 font-bold">
                                #{idx + 1}
                              </span>
                              {isActive ? (
                                <span className="absolute bottom-0 inset-x-0 bg-amber-500 text-slate-950 font-bold text-[9px] text-center py-0.5 shadow">
                                  ใช้งานอยู่
                                </span>
                              ) : (
                                <span className="absolute bottom-0 inset-x-0 bg-black/70 text-slate-300 text-[9px] text-center py-0.5 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                                  คลิกสลับ
                                </span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Brand & Product Title Hook Toggle Card */}
                  <div className="p-2.5 rounded-lg bg-slate-950/80 border border-purple-500/30 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Type className="w-4 h-4 text-amber-400" />
                        <div>
                          <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                            <span>หัวข้อ & ชื่อสินค้าบนหน้าปก</span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-medium">
                              แนะนำสำหรับ TikTok
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-400">
                            {enableHookText
                              ? 'เปิดอยู่: กำลังแสดงชื่อสินค้า/หัวข้อบนปกคลิป'
                              : 'ปิดอยู่: โหมดภาพคลีน (หากต้องการให้มีชื่อสินค้าบนปก กรุณาเปิดสวิตช์)'}
                          </div>
                        </div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={enableHookText}
                          onChange={(e) => setEnableHookText(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-500"></div>
                      </label>
                    </div>

                    {enableHookText && (
                      <div className="pt-1 space-y-1.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[10px] text-slate-400">ปุ่มลัดใส่ชื่อสินค้า:</span>
                          <button
                            type="button"
                            onClick={() => {
                              const words = (productName || 'GADGET PRODUCT').trim().split(/\s+/);
                              const brand = words[0]?.toUpperCase() || 'BRAND';
                              const model = words.slice(1, 3).join(' ')?.toUpperCase() || words[1]?.toUpperCase() || 'PRO REVIEW';
                              setHookText(`${brand}\n${model}`);
                              setSubText('รีวิวการใช้งานจริง');
                              setTemplate('tech_neon');
                              setEnableHookText(true);
                            }}
                            className="px-2 py-0.5 text-[10px] rounded bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/60 font-bold cursor-pointer shadow flex items-center gap-1"
                          >
                            <span>🔥 สไตล์ Tech Reviewer (ตามเรฟ)</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setHookText(productName || 'สินค้าพรีเมียม');
                              setSubText('รีวิวการใช้งานจริง');
                            }}
                            className="px-2 py-0.5 text-[10px] rounded bg-purple-900/50 hover:bg-purple-800 text-purple-200 border border-purple-700/60 cursor-pointer"
                          >
                            🏷️ ชื่อสินค้าล้วน: {productName || 'สินค้า'}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setHookText(`อย่าเพิ่งซื้อ ${productName || 'สินค้านี้'}\nถ้ายังไม่รู้สิ่งนี้!`);
                              setSubText('พิกัดในตะกร้าลดพิเศษ');
                            }}
                            className="px-2 py-0.5 text-[10px] rounded bg-amber-900/40 hover:bg-amber-800/60 text-amber-200 border border-amber-700/60 cursor-pointer"
                          >
                            🔥 สไตล์ Hook ดึงดูด
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setHookText(`รีวิวชัดๆ ${productName || 'สินค้า'}\nคุ้มไหมกับราคานี้?`);
                              setSubText('ดูคลิปจบตัดสินใจได้เลย');
                            }}
                            className="px-2 py-0.5 text-[10px] rounded bg-cyan-900/40 hover:bg-cyan-800/60 text-cyan-200 border border-cyan-700/60 cursor-pointer"
                          >
                            🎯 สไตล์ Review คุ้มไหม
                          </button>
                        </div>
                        <input
                          type="text"
                          value={hookText}
                          onChange={(e) => setHookText(e.target.value)}
                          placeholder="พิมพ์ข้อความหัวข้อบนปก..."
                          className="w-full text-xs px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-amber-300 font-semibold focus:outline-none focus:border-amber-400"
                        />
                      </div>
                    )}
                  </div>

                  {/* Product Reference Shot Selector for AI */}
                  {productRefImages.length > 0 && (
                    <div className="p-2.5 rounded-lg bg-slate-950/70 border border-purple-500/20 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-purple-200 font-semibold flex items-center gap-1.5">
                          <ShoppingBag className="w-3.5 h-3.5 text-amber-400" />
                          ช็อตสินค้าต้นแบบสำหรับ AI (เลือกรูปจาก TikTok Shop หรือเฟรมวิดีโอ):
                        </span>
                        {selectedRefImage && (
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedRefImage(null);
                              setCustomImage(null);
                              setCustomImageFile(null);
                            }}
                            className="text-[10px] text-purple-400 hover:text-purple-200 hover:underline cursor-pointer"
                          >
                            รีเซ็ตเป็นเฟรมวิดีโอ
                          </button>
                        )}
                      </div>
                      <div className="flex gap-1.5 overflow-x-auto pb-1 pt-0.5">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedRefImage(null);
                            setCustomImage(null);
                            setCustomImageFile(null);
                          }}
                          className={`shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] font-medium transition-all cursor-pointer ${
                            !selectedRefImage
                              ? 'bg-purple-600/30 border-purple-400 text-purple-200 shadow'
                              : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          <Film className="w-3 h-3 text-purple-400" />
                          เฟรมคลิป ({currentSeconds.toFixed(1)}s)
                        </button>
                        {productRefImages.map((img, idx) => {
                          const isSel = selectedRefImage?.url === img.url;
                          return (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => {
                                setSelectedRefImage(img);
                                setCustomImage(img.url);
                                setCustomImageFile(img.local_path || img.url);
                              }}
                              className={`shrink-0 flex items-center gap-1.5 px-2 py-1 rounded-lg border text-[10px] font-medium transition-all cursor-pointer ${
                                isSel
                                  ? 'bg-amber-500/20 border-amber-400 text-amber-200 ring-1 ring-amber-400/50 shadow'
                                  : 'bg-slate-900/80 border-slate-800 text-slate-400 hover:border-amber-400/40'
                              }`}
                            >
                              <img src={toMediaUrl(img.url, ownerRef.current.channel_id)} alt="" className="w-4 h-4 object-cover rounded" />
                              <span>รูป TT #{idx + 1}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Prompt Textarea */}
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">
                      {selectedRefImage ? (
                        <span className="text-amber-300">
                          คำสั่ง Prompt ฉากหลังสตูดิโอ (AI จะใช้รูปสินค้าคมชัดจาก TikTok Shop มาจัดวางกึ่งกลางอย่างลงตัว):
                        </span>
                      ) : (
                        <span>
                          คำสั่ง Prompt ฉากหลังสตูดิโอ (AI จะตัดสินค้าจริงจากวินาทีที่ {currentSeconds.toFixed(1)}s มาจัดวางกึ่งกลางอย่างลงตัว):
                        </span>
                      )}
                    </label>
                    <textarea
                      rows={3}
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="อธิบายสไตล์ฉากสตูดิโอ โทนแสง โพเดียม และบรรยากาศ..."
                      className="w-full text-xs p-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 focus:outline-none focus:border-purple-500 transition-colors resize-none placeholder-slate-600"
                    />
                  </div>

                  {/* Preset Buttons */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] text-slate-400 font-medium">สไตล์ฉากหลังยอดฮิตบน TikTok (ไม่มีคน ไม่รบกวนสินค้า):</span>
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        {
                          label: '🎯 แผ่นรองตัดโมเดล (Dark Grid)',
                          prompt: `Commercial 8k product hero photography of ${productName || 'product'}, placed flat at center on a dark charcoal gray precision model cutting mat with sharp white metric millimeter grid lines, ruler centimeter numbers, and alignment crosshair markings, professional tech reviewer desk setup, 45-degree high-angle view, clean diffused top softbox light casting subtle soft contact shadows under product edges, ultra-crisp macro texture, minimal modern gadget aesthetic, no people, no human, 9:16 vertical`,
                        },
                        {
                          label: '⚡ ผนังระแนงเทค + ไฟคู่ ส้ม/ฟ้า',
                          prompt: `Commercial 8k product showcase of ${productName || 'product'}, centered on a sleek matte dark stage in front of a modern vertical acoustic wooden slat wall, vibrant dual studio rim lighting with warm golden-amber backlight on one side and cool electric cyan backlight on the other side, dramatic contrast outlining product contours, clean high-end tech YouTuber backdrop, no people, no human, 9:16 vertical`,
                        },
                        {
                          label: '🖐️ มือโปรจับสินค้าจริง (Handheld)',
                          prompt: `Commercial 8k close-up shot of a clean human hand holding ${productName || 'product'} firmly and neatly at center, fingers gripping sides naturally without obstructing logo or buttons, dark minimalist studio background with subtle warm orange and cool blue accent lights, sharp macro focus on the product, professional tech unboxing aesthetic, 9:16 vertical`,
                        },
                        {
                          label: '🏆 แท่นโชว์ดาร์กมินิมอล',
                          prompt: `Ultra-clean commercial 8k product showcase, empty dark graphite round podium pedestal for ${productName || 'product'}, subtle overhead focused spotlight creating a smooth vignette shadow gradient, premium minimal matte surface with faint reflection, moody aesthetic, no people, no human, 9:16 vertical`,
                        },
                        {
                          label: '✨ คลีนมินิมอลเกรย์ (Clean Studio)',
                          prompt: `High-end commercial 8k product catalog photography for ${productName || 'product'}, centered on a smooth light gray seamless cyclorama curve background, bright balanced diffused softbox studio illumination, delicate natural contact shadow, ultra-clean Scandinavian minimal tech aesthetic, razor-sharp details, no people, no human, 9:16 vertical`,
                        },
                      ].map((preset, pIdx) => (
                        <button
                          key={pIdx}
                          type="button"
                          onClick={() => {
                            setAiPrompt(preset.prompt);
                            handleGenerateAiCover(preset.prompt);
                          }}
                          disabled={generatingAi}
                          className="px-2.5 py-1 text-[11px] rounded-md bg-purple-950/60 hover:bg-purple-900 text-purple-200 border border-purple-800/60 transition-colors disabled:opacity-50 cursor-pointer"
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Generate Button */}
                  <div className="pt-1 flex items-center justify-end">
                    <button
                      type="button"
                      onClick={() => handleGenerateAiCover()}
                      disabled={generatingAi || !aiPrompt.trim()}
                      className="w-full sm:w-auto px-4 py-2 rounded-lg font-bold text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-600/20 disabled:opacity-50 transition-all flex items-center justify-center gap-2 cursor-pointer"
                    >
                      {generatingAi ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          กำลังสร้างภาพ 9:16 ด้วย AI...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5" />
                          สร้างรูปหน้าปกด้วย AI (9:16)
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Raw Footage dropdown if multiple */}
              {activeSourceType === 'raw' && rawSources.length > 1 && (
                <div className="flex items-center gap-2 pt-1">
                  <span className="text-xs text-slate-400 shrink-0">เลือกไฟล์ Raw:</span>
                  <select
                    value={selectedRawPath}
                    onChange={(e) => handleSwitchToRawSource(e.target.value)}
                    className="w-full text-xs px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 focus:outline-none"
                  >
                    {rawSources.map((r, i) => (
                      <option key={i} value={r.path}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Highlight Candidate Thumbnails */}
              {candidates.length > 0 && activeSourceType !== 'upload' && (
                <div className="grid grid-cols-5 gap-2 pt-1">
                  {candidates.map((cand, idx) => {
                    const isSelected =
                      Math.abs(cand.timestamp - currentSeconds) < 0.2 && !customImage;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSelectCandidate(cand)}
                        className={`group relative rounded-lg overflow-hidden border transition-all text-left flex flex-col cursor-pointer ${
                          isSelected
                            ? 'border-amber-400 ring-2 ring-amber-400/30 shadow-md scale-102'
                            : 'border-slate-700 hover:border-slate-500 opacity-80 hover:opacity-100'
                        }`}
                      >
                        <div className="aspect-[9/16] w-full bg-slate-950 relative overflow-hidden">
                          <img
                            src={toMediaUrl(cand.thumb_url, ownerRef.current.channel_id)}
                            alt={cand.label}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                          />
                          <span className="absolute bottom-1 right-1 px-1 py-0.2 rounded bg-black/80 font-mono text-[9px] text-white">
                            {cand.timestamp.toFixed(1)}s
                          </span>
                        </div>
                        <div className="p-1 bg-slate-900/90 text-center">
                          <p className="text-[10px] font-medium text-slate-300 truncate">
                            {cand.label}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Scrubber & Pan Sliders */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div>
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>เลื่อนวินาทีในคลิป (Scrubber)</span>
                    <span className="font-mono text-cyan-400">
                      {currentSeconds.toFixed(1)} วินาที
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max={duration}
                    step="0.2"
                    value={currentSeconds}
                    disabled={activeSourceType === 'timeline'}
                    onChange={(e) => {
                      setCurrentSeconds(parseFloat(e.target.value));
                      setCustomImage(null);
                      setCustomImageFile(null);
                    }}
                    className="w-full accent-cyan-400 h-1.5 bg-slate-700 rounded-lg cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>เลื่อนแนวตั้ง (Pan Vertical)</span>
                    <span className="font-mono text-amber-400">
                      {panY}%{' '}
                      <span className="text-[10px] text-slate-400">
                        {panY <= 30 ? '(หลบซับล่าง)' : panY >= 70 ? '(ล่าง)' : '(กลาง)'}
                      </span>
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={panY}
                    onChange={(e) => setPanY(parseInt(e.target.value))}
                    className="w-full accent-amber-400 h-1.5 bg-slate-700 rounded-lg cursor-pointer"
                  />
                </div>
              </div>
            </div>

            {/* Section 2: Hook Copy & Positioning (Default OFF / unchecked) */}
            <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={enableHookText}
                    onChange={(e) => setEnableHookText(e.target.checked)}
                    className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0 w-4 h-4 cursor-pointer"
                  />
                  <Sparkles className="w-4 h-4" />
                  2. ข้อความ Hook บนปก (AI Copy & Positioning)
                </label>
                <span
                  className={`text-[11px] font-bold px-2 py-0.5 rounded-full transition-colors ${
                    enableHookText
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {enableHookText ? 'เปิดใช้งาน' : 'ปิดข้อความ (ภาพคลีน)'}
                </span>
              </div>

              {!enableHookText ? (
                <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-slate-300 text-xs flex items-center gap-2.5">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span className="min-w-0 flex-1">
                    โหมดภาพคลีน: ปิดข้อความ Hook แล้ว ระบบจะไม่วาดตัวอักษรใดๆ ทับ
                    ทำให้ภาพคมชัดไม่ทับฟอนต์ที่คุณจัดไว้
                  </span>
                </div>
              ) : (
                <>
                  {/* AI Quick Hook Ideas */}
                  {hookIdeas.length > 0 && (
                    <div>
                      <p className="text-[11px] text-slate-400 mb-1.5">
                        คลิกเลือกไอเดีย Hook ทำยอดวิว (AI Suggester):
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {hookIdeas.map((h, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => setHookText(h.text)}
                            className={`text-xs px-2.5 py-1 rounded-lg border transition-all text-left cursor-pointer ${
                              hookText === h.text
                                ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-semibold'
                                : 'bg-slate-800/80 border-slate-700 hover:border-slate-500 text-slate-300'
                            }`}
                          >
                            <span className="text-[10px] text-cyan-400/80 mr-1.5">
                              [{h.category}]
                            </span>
                            {h.text.replace('\n', ' ')}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Hook Text Inputs */}
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>ข้อความหลักบนปก (เคาะ Enter เพื่อขึ้นบรรทัดใหม่)</span>
                        <span className="text-[10px] text-slate-500">แนะนำ 2-3 บรรทัดสั้นๆ</span>
                      </div>
                      <textarea
                        rows={2}
                        value={hookText}
                        onChange={(e) => setHookText(e.target.value)}
                        placeholder="ใส่ข้อความ Hook บนปก..."
                        className="w-full px-3 py-2 text-sm bg-slate-950 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-400 font-semibold"
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">
                          ข้อความรอง (Sub-text ตัวเล็ก)
                        </label>
                        <input
                          type="text"
                          value={subText}
                          onChange={(e) => setSubText(e.target.value)}
                          placeholder="เช่น พิกัดในตะกร้าลด 50%"
                          className="w-full px-3 py-1.5 text-xs bg-slate-950 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-400"
                        />
                      </div>

                      <div>
                        <label className="block text-xs text-slate-400 mb-1">
                          ตำแหน่งวางข้อความ (Hook Zone)
                        </label>
                        <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-700">
                          {[
                            { id: 'top', label: 'บน ~25%' },
                            { id: 'center', label: 'กลาง ~50%' },
                            { id: 'bottom', label: 'ล่าง ~70%' },
                          ].map((pos) => (
                            <button
                              key={pos.id}
                              type="button"
                              onClick={() => setHookPosition(pos.id)}
                              className={`text-xs py-1 rounded-md transition-colors font-medium cursor-pointer ${
                                hookPosition === pos.id
                                  ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                                  : 'text-slate-400 hover:text-white'
                              }`}
                            >
                              {pos.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Section 3: Template Style & 3D Badges */}
            <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-4 space-y-4">
              <label className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <Layers className="w-4 h-4" />
                3. สไตล์แม่แบบ & ป้าย 3D (TikTok Templates)
              </label>

              {/* 5 TikTok Templates Cards */}
              {enableHookText && (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
                  {[
                    {
                      id: 'tech_neon',
                      name: '🔥 Tech Reviewer',
                      desc: 'แบรนด์ขาว + รุ่นนีออน (ตามเรฟ)',
                      badgeBg: 'bg-black border border-[#39FF14] text-[#39FF14] font-black',
                    },
                    {
                      id: 'neon',
                      name: 'นีออนเหลือง',
                      desc: 'ขอบดำหนา ล็อคตา สะดุดตา',
                      badgeBg: 'bg-[#FFE600] text-black font-black',
                    },
                    {
                      id: 'yellow_bar',
                      name: 'แถบคาดเหลือง',
                      desc: 'สไตล์ไวรัล ชัดทุกขนาด',
                      badgeBg: 'bg-[#FFE600] text-black font-black',
                    },
                    {
                      id: 'modern_box',
                      name: 'กล่องโมเดิร์น',
                      desc: 'กระจกเงา ขอบฟ้าเรืองแสง',
                      badgeBg: 'bg-slate-900 border border-[#25F4EE] text-white',
                    },
                    {
                      id: 'minimal_bold',
                      name: 'มินิมอลขาว',
                      desc: 'ขาวขอบดำหนา เรียบหรู',
                      badgeBg: 'bg-white text-black font-black',
                    },
                  ].map((t) => {
                    const isSel = template === t.id;
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setTemplate(t.id)}
                        className={`p-2.5 rounded-xl border text-left transition-all flex flex-col justify-between cursor-pointer ${
                          isSel
                            ? 'border-emerald-400 bg-emerald-500/10 ring-2 ring-emerald-400/20'
                            : 'border-slate-700 bg-slate-900/60 hover:border-slate-600'
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-1.5">
                            <span className={`text-[11px] px-2 py-0.5 rounded ${t.badgeBg}`}>
                              ตัวอย่าง
                            </span>
                            {isSel && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                          </div>
                          <p className="text-xs font-bold text-white">{t.name}</p>
                          <p className="text-[10px] text-slate-400 leading-tight mt-0.5">
                            {t.desc}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* 3D Badge Selection (Default OFF / unchecked) */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs text-slate-300 font-semibold flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={enableBadge}
                      onChange={(e) => setEnableBadge(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0 w-4 h-4 cursor-pointer"
                    />
                    <span>เลือกป้ายสติกเกอร์ 3D (3D Badges)</span>
                  </label>

                  {enableBadge && (
                    <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-700 text-[11px]">
                      {[
                        { id: 'top_left', label: 'มุมซ้ายบน' },
                        { id: 'top_right', label: 'มุมขวาบน' },
                        { id: 'none', label: 'ไม่ใส่ป้าย' },
                      ].map((bp) => (
                        <button
                          key={bp.id}
                          type="button"
                          onClick={() => setBadgePosition(bp.id)}
                          className={`px-2 py-0.5 rounded transition-colors cursor-pointer ${
                            badgePosition === bp.id
                              ? 'bg-slate-700 text-white font-bold'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          {bp.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {enableBadge && badgePosition !== 'none' ? (
                  <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
                    {badges.map((b) => {
                      const isBActive = selectedBadge === b.id;
                      return (
                        <button
                          key={b.id}
                          type="button"
                          onClick={() => setSelectedBadge(b.id)}
                          className={`p-1 rounded-lg border transition-all flex flex-col items-center justify-center cursor-pointer ${
                            isBActive
                              ? 'border-amber-400 bg-amber-500/10 ring-1 ring-amber-400/40 shadow'
                              : 'border-slate-800 bg-slate-950/60 hover:border-slate-700'
                          }`}
                          title={b.title}
                        >
                          <img
                            src={toMediaUrl(b.url, ownerRef.current.channel_id)}
                            alt={b.title}
                            className="w-10 h-10 object-contain drop-shadow"
                          />
                          <span className="text-[9px] text-slate-400 truncate w-full text-center mt-1">
                            {b.title.split(' ')[0]}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                ) : !enableBadge ? (
                  <div className="p-2.5 rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs">
                    <span>ปิดการแปะป้าย 3D แล้ว</span>
                  </div>
                ) : null}
              </div>
            </div>

            {/* Feedback messages */}
            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {savedResult && (
              <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 space-y-2 animate-fadeIn">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-emerald-300 font-bold text-xs">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{successMsg || 'บันทึกภาพปกเรียบร้อยแล้ว'}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => revealFile(savedResult.cover_path)}
                    className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-200 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer active:scale-95"
                  >
                    <Folder className="w-3.5 h-3.5" />
                    <span>เปิดไฟล์ใน Explorer</span>
                  </button>
                </div>
                <div className="text-[11px] text-slate-300 bg-black/40 p-2 rounded-lg border border-white/[0.05] font-mono select-all break-all space-y-1">
                  <div>
                    <span className="text-slate-500">ไฟล์ 9:16: </span>
                    <span className="text-emerald-300">{savedResult.cover_path}</span>
                  </div>
                  {savedResult.cover_3x4_path && (
                    <div>
                      <span className="text-slate-500">ไฟล์ 3:4: </span>
                      <span className="text-cyan-300">{savedResult.cover_3x4_path}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer with Dual Export Options */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-950 flex flex-wrap items-center justify-between gap-3">
          {/* Aspect Ratio Selector Pills */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-semibold">ขนาดภาพที่บันทึก:</span>
            <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs">
              {[
                { id: 'both', label: 'ทั้งสองขนาด (9:16 + 3:4)' },
                { id: '3:4', label: '3:4 หน้าช่อง TikTok' },
                { id: '9:16', label: '9:16 สตอรี่/คลิป' },
              ].map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setAspectRatio(r.id)}
                  className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                    aspectRatio === r.id
                      ? 'bg-amber-500 text-slate-950 shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {savedResult && (
              <button
                type="button"
                onClick={() => revealFile(savedResult.cover_path)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-200 transition-all flex items-center gap-1.5 cursor-pointer active:scale-95"
              >
                <Folder className="w-3.5 h-3.5" />
                <span>เปิดโฟลเดอร์ไฟล์ปก</span>
              </button>
            )}
            <button
              type="button"
              onClick={handleClose}
              disabled={saving || generatingAi}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              {savedResult ? 'เสร็จสิ้น' : 'ยกเลิก'}
            </button>
            <button
              type="button"
              onClick={handleSaveCover}
              disabled={saving}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-500/20 transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
            >
              {saving ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  กำลังบันทึกภาพปก...
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  {savedResult
                    ? 'บันทึกใหม่อีกครั้ง'
                    : aspectRatio === 'both'
                    ? 'บันทึกทั้งสองขนาด (9:16 + 3:4)'
                    : aspectRatio === '3:4'
                    ? 'บันทึกภาพปก 3:4'
                    : 'บันทึกภาพปก 9:16'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
