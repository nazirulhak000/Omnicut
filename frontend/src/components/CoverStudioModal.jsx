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
} from 'lucide-react';
import {
  getCoverBadges,
  getCoverHighlights,
  generateCoverHooks,
  renderProCover,
  getCoverRawSources,
  generateAiCoverImage,
  revealFile,
} from '../api';
import { resolveCoverExportStem } from '../lib/coverNaming.js';

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

  // State
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');
  const [savedResult, setSavedResult] = useState(null);
  const savedPreviewSignatureRef = useRef('');

  // Source selection: 'exported' | 'raw' | 'upload'
  const [activeSourceType, setActiveSourceType] = useState('exported');
  const [rawSources, setRawSources] = useState([]);
  const [selectedRawPath, setSelectedRawPath] = useState('');

  // Frame selection
  const [duration, setDuration] = useState(15.0);
  const [candidates, setCandidates] = useState([]);
  const [currentSeconds, setCurrentSeconds] = useState(0.5);
  const [customImage, setCustomImage] = useState(null);
  const [customImageFile, setCustomImageFile] = useState(null);

  // AI Cover Generation (Imagen 3 / Smart Frame Hunt)
  const [aiPrompt, setAiPrompt] = useState('');
  const [generatingAi, setGeneratingAi] = useState(false);
  const [aiGenMethod, setAiGenMethod] = useState('');

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

  // Load initial data: badges, highlights, hooks, raw sources
  useEffect(() => {
    let mounted = true;
    if (!isOpen || !videoItem) return undefined;
    setLoading(true);
    setError(null);

    Promise.all([
      getCoverBadges().catch(() => ({ badges: [] })),
      generateCoverHooks(productName, angleTitle).catch(() => ({ hooks: [] })),
      videoPath
        ? getCoverHighlights(videoPath).catch(() => ({ candidates: [], duration: 15 }))
        : Promise.resolve({ candidates: [], duration: 15 }),
      videoPath
        ? getCoverRawSources(videoPath).catch(() => ({ raw_sources: [] }))
        : Promise.resolve({ raw_sources: [] }),
    ])
      .then(([bRes, hRes, hlRes, rawRes]) => {
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
        }
        if (rawRes.raw_sources && rawRes.raw_sources.length > 0) {
          setRawSources(rawRes.raw_sources);
          setSelectedRawPath(rawRes.raw_sources[0].path);
        }
        setAiPrompt((prev) => prev || `Commercial 8k product photography of ${productName || 'product'}, sleek studio lighting, minimalist podium, vibrant cinematic colors, 9:16 vertical orientation, advertising poster quality`);
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
  }, [isOpen, videoPath, productName, angleTitle, videoItem]);

  // Keep hook order stable across closed -> open transitions. Previously this
  // component returned before its hooks, so opening it from the TikTok modal
  // caused React's "rendered more hooks" error and no editor appeared.
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
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
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

  // Handle AI Cover Image Generation (Imagen 3 / Smart Frame Hunt)
  const handleGenerateAiCover = async (promptOverride) => {
    try {
      setGeneratingAi(true);
      setError(null);
      setSuccessMsg('');
      const targetPrompt = promptOverride || aiPrompt;
      const res = await generateAiCoverImage({
        product_name: productName,
        hook_title: hookText,
        style_prompt: targetPrompt,
        video_path: videoPath || (rawSources[0]?.path || null),
      });
      if (res && res.success) {
        setCustomImage(res.media_url);
        setCustomImageFile(res.image_path);
        setAiGenMethod(res.method || 'imagen_3');
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

  // Switch to a candidate frame
  const handleSelectCandidate = (cand) => {
    setCurrentSeconds(cand.timestamp);
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
    const matched = candidates.find((c) => Math.abs(c.timestamp - currentSeconds) < 0.2);
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
    try {
      setSaving(true);
      setError(null);
      setSuccessMsg('');

      const activeVideoTarget = activeSourceType === 'raw' ? selectedRawPath : videoPath;
      const exportStem = resolveCoverExportStem(videoItem);

      const payload = {
        video_path: activeVideoTarget,
        raw_video_path: activeSourceType === 'raw' ? selectedRawPath : null,
        export_filename: exportStem,
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

      const res = await renderProCover(payload);
      if (res && res.success) {
        savedPreviewSignatureRef.current = getPreviewSignature();
        setSavedResult(res);
        const ratioLabel =
          aspectRatio === 'both' ? 'ทั้ง 9:16 และ 3:4' : aspectRatio === '3:4' ? '3:4' : '9:16';
        setSuccessMsg(`บันทึกภาพปก (${ratioLabel}) สำเร็จแล้ว!`);
        if (onCoverSaved) {
          onCoverSaved({
            cover_path: res.cover_path,
            media_url: res.media_url,
            cover_3x4_path: res.cover_3x4_path || null,
            media_url_3x4: res.media_url_3x4 || null,
          });
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
    <div className="fixed inset-0 z-[10000] flex items-center justify-center p-3 bg-black/80 backdrop-blur-md animate-fadeIn">
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
            onClick={onClose}
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
                    src={previewImageSrc}
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
                        src={badges.find((b) => b.id === selectedBadge)?.url}
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
                    src={previewImageSrc}
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
                        src={badges.find((b) => b.id === selectedBadge)?.url}
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
                <button
                  type="button"
                  onClick={handleSwitchToExported}
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
                  onClick={() => {
                    setActiveSourceType('ai_gen');
                  }}
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

              {/* AI Image Generator Panel */}
              {activeSourceType === 'ai_gen' && (
                <div className="p-3.5 rounded-xl bg-gradient-to-br from-purple-950/40 via-slate-900 to-slate-950 border border-purple-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-400" />
                      <span className="text-xs font-bold text-purple-200">
                        AI Image Studio (Google Imagen 3 / Smart Frame Hunt)
                      </span>
                    </div>
                    {aiGenMethod && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">
                        {aiGenMethod === 'imagen_3' ? '⚡ Imagen 3 (9:16)' : '🎯 Smart Frame Hunter'}
                      </span>
                    )}
                  </div>

                  {/* Prompt Textarea */}
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">
                      คำสั่ง Prompt สำหรับสร้างภาพพื้นหลัง (สัดส่วน 9:16 ปรับแต่งอัตโนมัติ):
                    </label>
                    <textarea
                      rows={3}
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="อธิบายภาพสินค้า มุมกล้อง โทนแสง และฉากหลัง..."
                      className="w-full text-xs p-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 focus:outline-none focus:border-purple-500 transition-colors resize-none placeholder-slate-600"
                    />
                  </div>

                  {/* Preset Buttons */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] text-slate-400 font-medium">สไตล์ภาพยอดนิยม:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        {
                          label: 'สตูดิโอระดับโปร',
                          prompt: `High-end commercial product photography of ${productName || 'the product'}, centered hero composition, 8k resolution, cinematic studio lighting with soft gradient reflections, clean modern aesthetic, sharp focus, 9:16 vertical ratio`,
                        },
                        {
                          label: 'นีออนจัดจ้าน',
                          prompt: `Dynamic cyberpunk neon commercial shot of ${productName || 'the product'}, glowing ambient highlights, modern tech background, high energy, bold contrast, ultra-detailed 9:16 vertical framing`,
                        },
                        {
                          label: 'มินิมอลโมเดิร์น',
                          prompt: `Minimalist aesthetic product photography for ${productName || 'the product'}, pastel tones, soft natural morning sunlight, clean podium surface, elegant and premium, 9:16 vertical composition`,
                        },
                        {
                          label: 'ไลฟ์สไตล์ธรรมชาติ',
                          prompt: `Authentic lifestyle product placement of ${productName || 'the product'} in everyday cozy aesthetic environment, warm lighting, natural depth of field bokeh, photorealistic 9:16 portrait view`,
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
                            src={cand.thumb_url}
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

              {/* 4 TikTok Templates Cards */}
              {enableHookText && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {[
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
                            src={b.url}
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
              onClick={onClose}
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
