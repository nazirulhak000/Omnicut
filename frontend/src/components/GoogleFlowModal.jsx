import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Video,
  Sparkles,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Download,
  Zap,
  ChevronDown,
  Check,
  Users,
  ShieldCheck,
  Plus,
  Sliders,
} from 'lucide-react';
import { Modal } from './ui';
import {
  mapCameraTechnique,
  findFlowClipForBeat,
  getFlowAccounts,
  switchFlowAccount,
  toggleAutoFailover,
  openFlowLoginChrome,
  getAngleShotsFlow,
  DEFAULT_FLOW_ACCOUNTS_FALLBACK,
} from '../lib/flowUtils';
import {
  getFlowStatus,
  startFlowService,
  stopFlowService,
  getFlowPresets,
  expandFlowPrompt,
  generateFlowVideo,
  getFlowJobs,
  ingestFlowClip,
} from '../api';

export default function GoogleFlowModal({
  isOpen,
  onClose,
  productId,
  angleId = null,
  productName = '',
  initialPrompt = '',
  initialBeat = null,
  onClipIngested = null,
}) {
  // Navigation Tabs: 'flow' (Default Active Tab) | 'custom'
  const [activeTab, setActiveTab] = useState('flow');

  const [status, setStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [startingService, setStartingService] = useState(false);
  const [stoppingService, setStoppingService] = useState(false);

  // Account Pool States
  const [accountsData, setAccountsData] = useState(DEFAULT_FLOW_ACCOUNTS_FALLBACK);
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [switchingAccount, setSwitchingAccount] = useState(false);
  const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);
  const [openingLogin, setOpeningLogin] = useState(false);
  const dropdownRef = useRef(null);

  // Flow-First 5-shots States
  const [flowShots, setFlowShots] = useState([]);
  const [loadingShots, setLoadingShots] = useState(false);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [generatingShotIndex, setGeneratingShotIndex] = useState(null);

  // Form states (Custom Prompt Tab)
  const [mode, setMode] = useState('text'); // 'text' | 'image'
  const [prompt, setPrompt] = useState(initialPrompt);
  const [thaiNotes, setThaiNotes] = useState('');
  const [technique, setTechnique] = useState('orbit');
  const [lighting, setLighting] = useState('studio_clean');
  const [referencePath, setReferencePath] = useState('');
  const [expandingPrompt, setExpandingPrompt] = useState(false);

  // Presets & Jobs
  const [jobs, setJobs] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [ingestingId, setIngestingId] = useState(null);

  // Close dropdown when clicked outside
  useEffect(() => {
    if (!accountDropdownOpen) return;
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setAccountDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [accountDropdownOpen]);

  const refreshStatus = useCallback(async () => {
    setLoadingStatus(true);
    try {
      const data = await getFlowStatus(false);
      setStatus(data);
    } catch {
      setStatus({ service_online: false, hint: 'ไม่สามารถเชื่อมต่อ flow-mcp service ได้' });
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  const loadAccounts = useCallback(async () => {
    setLoadingAccounts(true);
    try {
      const data = await getFlowAccounts();
      if (data && Array.isArray(data.accounts)) {
        setAccountsData(data);
      }
    } catch (err) {
      console.warn('Could not load flow accounts:', err);
    } finally {
      setLoadingAccounts(false);
    }
  }, []);

  const handleSwitchAccount = async (targetId) => {
    if (switchingAccount || targetId === accountsData?.active_account_id) return;
    setSwitchingAccount(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await switchFlowAccount(targetId);
      if (res?.needs_login) {
        const targetAcc = accountsData?.accounts?.find((a) => a.id === targetId);
        setErrorMsg(`บัญชี ${targetAcc?.name || targetId} ยังไม่ได้เข้าสู่ระบบ Google ใน Chrome กรุณากด "เชื่อมต่อบัญชี Google ใน Chrome" ด้านล่าง`);
        await loadAccounts();
        return;
      }
      setAccountsData((prev) => ({
        ...prev,
        active_account_id: targetId,
        ...(res && res.accounts ? res : {}),
      }));
      await loadAccounts();
      await refreshStatus();
      const targetAcc = accountsData?.accounts?.find((a) => a.id === targetId);
      setSuccessMsg(`สลับไปใช้งานบัญชี ${targetAcc?.name || targetId} สำเร็จ`);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'สลับบัญชีไม่สำเร็จ');
    } finally {
      setSwitchingAccount(false);
    }
  };

  const handleToggleAutoFailover = async (enabled) => {
    try {
      await toggleAutoFailover(enabled);
      setAccountsData((prev) => ({
        ...prev,
        auto_failover: enabled,
      }));
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'ตั้งค่า Auto-Failover ไม่สำเร็จ');
    }
  };

  const handleOpenLoginChrome = async () => {
    setOpeningLogin(true);
    setErrorMsg(null);
    try {
      await openFlowLoginChrome();
      setSuccessMsg('สั่งเปิดหน้าต่าง Google Chrome เรียบร้อยแล้ว กรุณาล็อกอินใน Chrome แล้วกดปุ่มรีเฟรช');
      await loadAccounts();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'เปิดหน้าล็อกอินใน Chrome ไม่สำเร็จ');
    } finally {
      setOpeningLogin(false);
    }
  };

  const accounts = accountsData?.accounts || [];
  const activeAccountId = accountsData?.active_account_id || accounts[0]?.id;
  const activeAccount = accounts.find((a) => a.id === activeAccountId) || accounts[0];
  const totalPoolCredits =
    typeof accountsData?.total_pool_credits === 'number'
      ? accountsData.total_pool_credits
      : accounts.reduce((acc, curr) => acc + (Number(curr.credits) || 0), 0);

  const getCreditBadgeConfig = (credits, isLinked = true) => {
    if (!isLinked) {
      return {
        dot: 'bg-zinc-600',
        text: 'text-zinc-500',
        badge: 'bg-zinc-800/40 text-zinc-400 border-zinc-700/50',
        label: 'ยังไม่ได้เชื่อมต่อใน Chrome',
      };
    }
    const cr = Number(credits) || 0;
    if (cr >= 200) {
      return {
        dot: 'bg-emerald-400',
        text: 'text-emerald-400',
        badge: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
        label: 'พร้อมใช้งาน (>= 200 cr)',
      };
    }
    if (cr >= 50) {
      return {
        dot: 'bg-amber-400',
        text: 'text-amber-400',
        badge: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
        label: 'โควตาปานกลาง (>= 50 cr)',
      };
    }
    return {
      dot: 'bg-rose-400',
      text: 'text-rose-400',
      badge: 'bg-rose-500/10 text-rose-300 border-rose-500/20',
      label: 'โควตาใกล้หมด (< 50 cr)',
    };
  };

  const loadPresets = useCallback(async () => {
    try {
      await getFlowPresets();
    } catch {
      // Fallback defaults
    }
  }, []);

  const loadJobs = useCallback(async () => {
    if (!productId) return;
    try {
      const data = await getFlowJobs(productId);
      setJobs(data.jobs || []);
    } catch {
      // Silent error
    }
  }, [productId]);

  // Load 5 Flow Shots from Backend with fallback
  const loadFlowShots = useCallback(async () => {
    if (!productId) return;
    setLoadingShots(true);
    try {
      const data = await getAngleShotsFlow(productId, angleId);
      let rawShots = null;
      if (data) {
        if (Array.isArray(data.shots)) rawShots = data.shots;
        else if (Array.isArray(data)) rawShots = data;
      }
      if (rawShots && rawShots.length > 0) {
        setFlowShots(rawShots);
        return;
      }
    } catch (err) {
      console.warn('getAngleShotsFlow fallback to default beats:', err?.message || err);
    } finally {
      setLoadingShots(false);
    }

    // Default 5-beat fallback
    const fallbackBeats = [
      {
        beat_index: 0,
        role: 'hook',
        role_label: 'Hook (เปิดหัว)',
        text: initialBeat?.beatIndex === 0 ? initialBeat.text : `เปิดตัว ${productName || 'สินค้า'} สุดพรีเมียม ดึงดูดสายตา 3 วินาทีแรก`,
        camera_direction: 'Orbit 360 (หมุนรอบสินค้า)',
        technique: 'orbit',
        duration: 6,
        prompt: `Cinematic vertical 9:16 commercial establishing shot of ${productName || 'premium gadget'}, smooth 360 orbit camera rotation, luxury clean studio background, dramatic studio lighting, photorealistic, 4k ultra-detailed.`,
      },
      {
        beat_index: 1,
        role: 'feature',
        role_label: 'Feature 1 (จุดเด่นหลัก)',
        text: initialBeat?.beatIndex === 1 ? initialBeat.text : `เจาะลึกดีเทลและวัสดุงานประกอบของ ${productName || 'สินค้า'} โคลสอัพคมชัด`,
        camera_direction: 'Macro Texture (โคลสอัพดีเทล)',
        technique: 'macro',
        duration: 8,
        prompt: `Extreme macro close-up vertical 9:16 shot of ${productName || 'tech gadget'}, showing premium material texture and tactile finish, smooth slow motion glide, shallow depth of field, sharp focus, studio lighting.`,
      },
      {
        beat_index: 2,
        role: 'feature',
        role_label: 'Feature 2 (สเปก & ประสิทธิภาพ)',
        text: initialBeat?.beatIndex === 2 ? initialBeat.text : `โชว์ระบบการทำงานและฟีเจอร์เด่น ดันกล้องเข้าหามุมตรงสุดคม`,
        camera_direction: 'Dolly In (ดันกล้องเข้าหา)',
        technique: 'dolly_in',
        duration: 8,
        prompt: `Cinematic slow dolly-in vertical 9:16 shot moving straight towards ${productName || 'tech device'}, subtle LED glowing indicators, modern minimalist aesthetic, pristine tech commercial look.`,
      },
      {
        beat_index: 3,
        role: 'feature',
        role_label: 'Feature 3 (การใช้งานจริง)',
        text: initialBeat?.beatIndex === 3 ? initialBeat.text : `ภาพการใช้งานจริงในบรรยากาศพรีเมียม สโลว์โมชันลอยตัวเนียนตา`,
        camera_direction: 'Floating (ลอยตัวสโลว์โมชัน)',
        technique: 'floating',
        duration: 8,
        prompt: `Cinematic floating vertical 9:16 shot of ${productName || 'product'}, gentle slow-motion levitation, soft warm ambient lighting, elegant lifestyle tech aesthetic, high frame rate feel.`,
      },
      {
        beat_index: 4,
        role: 'cta',
        role_label: 'CTA (ปิดการขาย)',
        text: initialBeat?.beatIndex === 4 ? initialBeat.text : `ปิดท้ายช็อตเสยมุมต่ำ สรุปโปรโมชั่นเด็ด กดสั่งซื้อที่ตะกร้าด่วน`,
        camera_direction: 'Low Angle Reveal (เสยมุมต่ำ)',
        technique: 'reveal',
        duration: 6,
        prompt: `Heroic low angle reveal vertical 9:16 shot tilting upward to showcase ${productName || 'product'}, bold confident composition, sleek rim lighting, clean product showcase, advertising grade.`,
      },
    ];

    if (initialBeat && initialBeat.beatIndex !== undefined && initialBeat.beatIndex < 5) {
      fallbackBeats[initialBeat.beatIndex] = {
        ...fallbackBeats[initialBeat.beatIndex],
        text: initialBeat.text || fallbackBeats[initialBeat.beatIndex].text,
        camera_direction: initialBeat.cameraDirection || fallbackBeats[initialBeat.beatIndex].camera_direction,
        technique: mapCameraTechnique(initialBeat.cameraDirection) || fallbackBeats[initialBeat.beatIndex].technique,
        duration: initialBeat.duration ? Math.round(Number(initialBeat.duration)) : fallbackBeats[initialBeat.beatIndex].duration,
        prompt: initialPrompt || fallbackBeats[initialBeat.beatIndex].prompt,
      };
    }

    setFlowShots(fallbackBeats);
  }, [productId, angleId, productName, initialBeat, initialPrompt]);

  // Sync state whenever modal opens
  useEffect(() => {
    if (!isOpen) return;

    if (initialBeat) {
      setThaiNotes(`${initialBeat.text || ''}${initialBeat.cameraDirection ? ` (${initialBeat.cameraDirection})` : ''}`.trim());
      setTechnique(mapCameraTechnique(initialBeat.cameraDirection));
      if (initialPrompt) {
        setPrompt(initialPrompt);
      } else {
        setPrompt(
          `Cinematic commercial vertical video of ${productName || 'product'}, ${initialBeat.text || ''}. 9:16 aspect ratio, clean studio lighting, high resolution.`
        );
      }
    } else {
      setPrompt(initialPrompt || '');
      setThaiNotes('');
      setTechnique('orbit');
    }

    refreshStatus();
    loadPresets();
    loadJobs();
    loadAccounts();
    loadFlowShots();
  }, [isOpen, productId, angleId, initialBeat, initialPrompt, productName, refreshStatus, loadPresets, loadJobs, loadAccounts, loadFlowShots]);

  // Auto-poll active jobs while open
  useEffect(() => {
    if (!isOpen || !productId) return;
    const hasActiveJob = jobs.some((j) => j.status === 'queued' || j.status === 'running');
    if (!hasActiveJob) return;

    const timer = setInterval(() => {
      loadJobs();
    }, 4000);

    return () => clearInterval(timer);
  }, [isOpen, productId, jobs, loadJobs]);

  const handleStartService = async () => {
    setStartingService(true);
    setErrorMsg(null);
    try {
      await startFlowService();
      await new Promise((r) => setTimeout(r, 2000));
      await refreshStatus();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'เปิดบริการ flow-mcp ไม่สำเร็จ');
    } finally {
      setStartingService(false);
    }
  };

  const handleStopService = async () => {
    setStoppingService(true);
    setErrorMsg(null);
    try {
      await stopFlowService();
      await new Promise((r) => setTimeout(r, 1000));
      await refreshStatus();
      setSuccessMsg('ปิดระบบ Google Flow เรียบร้อยแล้ว');
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'ปิดระบบ Google Flow ไม่สำเร็จ');
    } finally {
      setStoppingService(false);
    }
  };

  const handleExpandPrompt = async () => {
    if (!thaiNotes.trim() && !prompt.trim()) return;
    setExpandingPrompt(true);
    setErrorMsg(null);
    try {
      const res = await expandFlowPrompt({
        thai_description: thaiNotes.trim() || prompt.trim(),
        product_name: productName,
        technique,
        lighting,
      });
      if (res.prompt) {
        setPrompt(res.prompt);
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'สร้าง Prompt อัตโนมัติไม่สำเร็จ กรุณาลองใหม่');
    } finally {
      setExpandingPrompt(false);
    }
  };

  // Submit manual custom prompt
  const handleSubmitGenerate = async () => {
    if (!prompt.trim()) {
      setErrorMsg('กรุณาระบุ Prompt สำหรับสร้างวิดีโอ');
      return;
    }
    setSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    let shotDuration = 8;
    if (initialBeat?.duration) {
      const raw = Math.round(Number(initialBeat.duration));
      const valid = [4, 6, 8, 10];
      shotDuration = valid.reduce((prev, curr) => (Math.abs(curr - raw) < Math.abs(prev - raw) ? curr : prev));
    }

    const shotNum = initialBeat?.beatIndex !== undefined ? initialBeat.beatIndex + 1 : undefined;

    const scene = {
      prompt: prompt.trim(),
      type: 'video',
      aspect_ratio: '9:16',
      duration: shotDuration,
      technique: technique || undefined,
      download_quality: 'original',
      max_credits: 100,
      shot_index: initialBeat?.beatIndex,
      shot_label: shotNum ? `shot_${shotNum}_${initialBeat?.role || 'broll'}` : undefined,
    };

    if (mode === 'image' && referencePath.trim()) {
      scene.reference_images = [referencePath.trim()];
    }

    try {
      await generateFlowVideo({
        product_id: productId,
        scenes: [scene],
        project_name: productName || (initialBeat ? `shot_${shotNum}` : undefined),
      });
      setSuccessMsg(`ส่งงานเข้าคิว Google Flow สำเร็จ${shotNum ? ` (สำหรับช็อตที่ ${shotNum})` : ''}`);
      await loadJobs();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'ส่งงานสร้างวิดีโอไม่สำเร็จ');
    } finally {
      setSubmitting(false);
    }
  };

  // Generate single shot from Flow-First tab
  const handleGenerateSingleShot = async (shot, index) => {
    if (!status?.service_online) {
      setErrorMsg('ระบบ Flow Service ออฟไลน์ กรุณากดปุ่ม "เปิดระบบ Flow Service" ด้านบนก่อน');
      return;
    }
    setGeneratingShotIndex(index);
    setErrorMsg(null);
    setSuccessMsg(null);

    const shotNum = (shot.beat_index !== undefined ? shot.beat_index : index) + 1;
    const scene = {
      prompt: shot.prompt || `Cinematic commercial vertical video of ${productName || 'product'}, ${shot.text}. 9:16 aspect ratio, clean studio lighting, high resolution.`,
      type: 'video',
      aspect_ratio: '9:16',
      duration: shot.duration || (index === 0 || index === 4 ? 6 : 8),
      technique: shot.technique || mapCameraTechnique(shot.camera_direction),
      download_quality: 'original',
      max_credits: 100,
      shot_index: shot.beat_index !== undefined ? shot.beat_index : index,
      shot_label: `shot_${shotNum}_${shot.role || 'broll'}`,
    };
    if (shot.reference_image) {
      scene.reference_images = [shot.reference_image];
    }

    try {
      await generateFlowVideo({
        product_id: productId,
        scenes: [scene],
        project_name: productName ? `${productName} shot_${shotNum}` : `shot_${shotNum}`,
      });
      setSuccessMsg(`ส่งคำสั่งสร้างวิดีโอช็อตที่ ${shotNum} (${shot.role_label || shot.role || 'B-roll'}) สำเร็จ`);
      await loadJobs();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || `สั่งสร้างช็อตที่ ${shotNum} ไม่สำเร็จ`);
    } finally {
      setGeneratingShotIndex(null);
    }
  };

  // 1-Click: Generate all 5 shots sequence
  const handleGenerateAll5Shots = async () => {
    if (!status?.service_online) {
      setErrorMsg('ระบบ Flow Service ออฟไลน์ กรุณากดปุ่ม "เปิดระบบ Flow Service" ด้านบนก่อน');
      return;
    }
    if (!flowShots || flowShots.length === 0) {
      setErrorMsg('ไม่พบรายการช็อตสคริปต์ 5 ช็อต');
      return;
    }
    setGeneratingAll(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const scenes = flowShots.map((shot, idx) => {
      const shotNum = (shot.beat_index !== undefined ? shot.beat_index : idx) + 1;
      const scene = {
        prompt: shot.prompt || `Cinematic vertical 9:16 commercial video of ${productName || 'product'}, ${shot.text}. Clean studio lighting, 4k ultra-detailed.`,
        type: 'video',
        aspect_ratio: '9:16',
        duration: shot.duration || (idx === 0 || idx === 4 ? 6 : 8),
        technique: shot.technique || mapCameraTechnique(shot.camera_direction),
        download_quality: 'original',
        max_credits: 100,
        shot_index: shot.beat_index !== undefined ? shot.beat_index : idx,
        shot_label: `shot_${shotNum}_${shot.role || 'broll'}`,
      };
      if (shot.reference_image) {
        scene.reference_images = [shot.reference_image];
      }
      return scene;
    });

    try {
      await generateFlowVideo({
        product_id: productId,
        scenes,
        project_name: productName ? `${productName} 5-Shots Flow` : '5-Shots Flow Sequence',
      });
      setSuccessMsg('สั่งสร้าง AI B-roll อัตโนมัติครบ 5 ช็อตเข้าคิว Google Flow สำเร็จ');
      await loadJobs();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'สั่งสร้างครบ 5 ช็อตไม่สำเร็จ');
    } finally {
      setGeneratingAll(false);
    }
  };

  const handleIngest = async (job, resultItem) => {
    const srcPath = resultItem?.path || resultItem?.file_path;
    if (!srcPath) return;
    setIngestingId(job.id);
    try {
      const shotLabel = initialBeat
        ? `shot_${initialBeat.beatIndex + 1}_${initialBeat.role || 'broll'}`
        : (job.scenes?.[0]?.shot_label || 'flow_broll');

      const res = await ingestFlowClip({
        product_id: productId,
        source_path: srcPath,
        shot_label: shotLabel,
      });
      setSuccessMsg(`นำเข้าคลิปสำเร็จ: ${res.metadata.filename}`);
      if (onClipIngested) onClipIngested(res.metadata);
      await loadJobs();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'นำเข้าคลิปไม่สำเร็จ');
    } finally {
      setIngestingId(null);
    }
  };

  const getRoleBadge = (role, index) => {
    const r = (role || '').toLowerCase();
    if (r === 'hook' || index === 0) {
      return {
        label: 'Hook (เปิดหัว)',
        badge: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
      };
    }
    if (r === 'cta' || index === 4) {
      return {
        label: 'CTA (ปิดการขาย)',
        badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
      };
    }
    return {
      label: `Feature ${index || 1}`,
      badge: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
    };
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="สร้างวิดีโอด้วย Google Flow (Veo)" size="2xl">
      <div className="space-y-6 text-sm text-zinc-300">
        {/* Account Pool Status Bar & Dropdown */}
        <div className="relative p-3.5 rounded-xl bg-gradient-to-r from-zinc-950 via-zinc-900 to-zinc-950 border border-zinc-800 shadow-md">
          <div className="flex flex-wrap items-center justify-between gap-3">
            {/* Left: Active Account Dropdown Badge */}
            <div className="flex items-center gap-2.5">
              <span className="text-xs text-zinc-400 font-medium">บัญชีที่ใช้:</span>
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  onClick={() => setAccountDropdownOpen((prev) => !prev)}
                  className="px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-600 text-xs font-medium text-zinc-100 flex items-center gap-2 transition-colors cursor-pointer shadow-sm group max-w-full"
                  title="คลิกเพื่อเลือกหรือสลับบัญชี Google Flow"
                  aria-expanded={accountDropdownOpen}
                  aria-haspopup="true"
                >
                  <span className={`w-2 h-2 rounded-full ${getCreditBadgeConfig(activeAccount?.credits, activeAccount?.authenticated !== false).dot} shrink-0`} />
                  <span className="font-semibold text-zinc-200 shrink-0">{activeAccount?.name || 'Google Pro #1'}</span>
                  <span className="text-[11px] text-zinc-400 font-mono hidden sm:inline max-w-[170px] truncate" title={activeAccount?.email}>
                    ({activeAccount?.email || 'nazirulhak.000@gmail.com'})
                  </span>
                  <span className={`font-mono font-bold shrink-0 ${getCreditBadgeConfig(activeAccount?.credits, activeAccount?.authenticated !== false).text}`}>
                    {(activeAccount?.credits ?? 810).toLocaleString()} cr
                  </span>
                  <ChevronDown className={`w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-200 transition-transform duration-200 shrink-0 ${accountDropdownOpen ? 'rotate-180' : ''}`} />
                </button>

                {/* Account Selector Popover */}
                {accountDropdownOpen && (
                  <div
                    className="absolute top-full left-0 mt-2 z-50 w-[340px] sm:w-[460px] p-4 rounded-xl bg-zinc-950 backdrop-blur-xl border border-zinc-800 shadow-2xl shadow-black/80 space-y-3.5 origin-top-left animate-in fade-in zoom-in-95 duration-150"
                    role="menu"
                  >
                    {/* Popover Header */}
                    <div className="flex items-center justify-between pb-2.5 border-b border-zinc-800">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-zinc-400" />
                        <div>
                          <h4 className="text-xs font-bold text-zinc-100 uppercase tracking-wide">
                            Google Flow Account Pool
                          </h4>
                          <p className="text-[11px] text-zinc-400">
                            เชื่อมต่อแล้ว {accountsData?.linked_accounts_count ?? (accounts.filter(a => a.authenticated).length || 1)} จาก {accounts.length || 5} บัญชี
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={loadAccounts}
                        disabled={loadingAccounts}
                        className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                        title="รีเฟรชเครดิตบัญชี"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${loadingAccounts ? 'animate-spin' : ''}`} />
                      </button>
                    </div>

                    {/* Auto-Failover Toggle */}
                    <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-between">
                      <label className="flex items-center gap-2.5 cursor-pointer text-xs text-zinc-200 select-none">
                        <input
                          type="checkbox"
                          checked={Boolean(accountsData?.auto_failover)}
                          onChange={(e) => handleToggleAutoFailover(e.target.checked)}
                          className="w-4 h-4 rounded border-zinc-700 bg-zinc-950 text-emerald-500 focus:ring-0 focus:ring-offset-0 cursor-pointer accent-emerald-500"
                        />
                        <div>
                          <div className="font-semibold text-zinc-200 flex items-center gap-1.5">
                            <span>Auto-Failover อัตโนมัติ</span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 font-mono border border-zinc-700">
                              &lt; {accountsData?.min_failover_credits ?? 25} cr
                            </span>
                          </div>
                          <div className="text-[10px] text-zinc-400">
                            สลับบัญชีถัดไปอัตโนมัติเมื่อเครดิตใกล้หมด ป้องกัน Batch หลุด
                          </div>
                        </div>
                      </label>
                    </div>

                    {/* Account List */}
                    <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                      {accounts.map((acc) => {
                        const isActive = acc.id === activeAccountId;
                        const isLinked = acc.authenticated !== false && Boolean(acc.email && acc.email.includes('@'));
                        const badgeCfg = getCreditBadgeConfig(acc.credits, isLinked);
                        return (
                          <div
                            key={acc.id}
                            className={`p-2.5 rounded-lg border transition-colors ${
                              isActive
                                ? 'bg-zinc-900 border-zinc-700 shadow-sm'
                                : 'bg-zinc-950/60 border-zinc-800 hover:bg-zinc-900/40 hover:border-zinc-700'
                            } flex items-center justify-between gap-3`}
                          >
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${badgeCfg.dot} shrink-0`} />
                                <span className="font-semibold text-xs text-zinc-100 truncate">
                                  {acc.name}
                                </span>
                                <span className="px-1.5 py-0.5 rounded font-mono text-[10px] bg-zinc-900 text-zinc-400 border border-zinc-800 shrink-0">
                                  /u/{acc.user_index ?? 0}
                                </span>
                                {acc.plan && isLinked && (
                                  <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono text-zinc-400 bg-zinc-800 border border-zinc-700 shrink-0">
                                    {acc.plan}
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] font-mono truncate pl-4 mt-0.5">
                                {isLinked ? (
                                  <span className="text-zinc-300">{acc.email}</span>
                                ) : (
                                  <span className="text-zinc-500 italic">ยังไม่ได้เชื่อมต่อใน Chrome</span>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${badgeCfg.badge}`}
                                title={badgeCfg.label}
                              >
                                {isLinked ? `${(acc.credits ?? 0).toLocaleString()} cr` : '-'}
                              </span>

                              {isActive ? (
                                <span className="px-2.5 py-1 rounded bg-zinc-800 text-emerald-400 border border-emerald-500/30 text-[11px] font-medium flex items-center gap-1">
                                  <Check className="w-3 h-3 text-emerald-400" />
                                  กำลังใช้งาน
                                </span>
                              ) : isLinked ? (
                                <button
                                  type="button"
                                  onClick={() => handleSwitchAccount(acc.id)}
                                  disabled={switchingAccount}
                                  className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 hover:border-zinc-600 text-[11px] font-medium transition-colors cursor-pointer disabled:opacity-50"
                                >
                                  สลับใช้บัญชีนี้
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={handleOpenLoginChrome}
                                  disabled={openingLogin}
                                  className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white border border-zinc-700 hover:border-zinc-600 text-[11px] font-medium transition-colors cursor-pointer disabled:opacity-50"
                                  title="เปิดหน้าสลับบัญชีใน Chrome เพื่อเข้าสู่ระบบบัญชีนี้"
                                >
                                  เชื่อมต่อ
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Action Button: Open Login in Chrome */}
                    <div className="pt-2.5 border-t border-zinc-800 space-y-1.5">
                      <button
                        type="button"
                        onClick={handleOpenLoginChrome}
                        disabled={openingLogin}
                        className="w-full py-2 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-200 hover:text-white border border-zinc-700 hover:border-zinc-600 text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-sm disabled:opacity-50"
                      >
                        <Plus className="w-3.5 h-3.5 text-zinc-400" />
                        <span>{openingLogin ? 'กำลังเปิดหน้าสลับบัญชีใน Chrome...' : 'เชื่อมต่อบัญชี Google ใน Chrome'}</span>
                      </button>
                      <p className="text-[10px] text-zinc-400 text-center">
                        กดปุ่มด้านบนเพื่อเปิด Chrome สำหรับเข้าสู่ระบบบัญชี 2-5 แล้วกลับมากดรีเฟรชเครดิต
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Total Pool Indicator */}
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              <div className="px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center gap-1.5 text-xs text-zinc-300">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-zinc-400">เครดิตรวม:</span>
                <span className="font-mono font-semibold text-zinc-100">
                  {totalPoolCredits.toLocaleString()} cr
                </span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  ({accountsData?.linked_accounts_count ?? (accounts.filter(a => a.authenticated).length || 1)}/{accounts.length || 5} บัญชี)
                </span>
              </div>

              <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-zinc-400 bg-zinc-900/80 px-2.5 py-1.5 rounded-lg border border-zinc-800">
                <ShieldCheck className="w-3.5 h-3.5 text-zinc-400" />
                <span>Auto-failover:</span>
                <span className={accountsData?.auto_failover ? 'text-emerald-400 font-semibold' : 'text-zinc-500'}>
                  {accountsData?.auto_failover ? 'เปิด' : 'ปิด'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${status?.service_online ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
            <div>
              <div className="font-semibold text-zinc-100 flex items-center gap-2">
                Flow Engine (Port 8787): {status?.service_online ? 'ออนไลน์พร้อมใช้งาน' : 'ออฟไลน์'}
              </div>
              <div className="text-xs text-zinc-400">
                {status?.service_online
                  ? `เครดิตคงเหลือ: ${(activeAccount?.credits !== undefined ? activeAccount.credits : (status.credits_remaining !== undefined ? status.credits_remaining : 50)).toLocaleString()} cr · บัญชี ${activeAccount?.name || 'Active'}`
                  : 'กดปุ่มด้านขวาเพื่อเปิด Service เบื้องหลัง'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {status?.service_online ? (
              <button
                type="button"
                onClick={handleStopService}
                disabled={stoppingService}
                className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white border border-zinc-700 text-xs font-medium disabled:opacity-50 transition-colors"
                title="ปิดระบบ Flow และ Chrome เพื่อประหยัดแรม"
              >
                {stoppingService ? 'กำลังปิด...' : 'ปิดระบบ Flow'}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStartService}
                disabled={startingService}
                className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium disabled:opacity-50 transition-colors"
              >
                {startingService ? 'กำลังเริ่มระบบ...' : 'เปิดระบบ Flow Service'}
              </button>
            )}
            <button
              type="button"
              onClick={refreshStatus}
              disabled={loadingStatus}
              className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs transition-colors"
              title="รีเฟรชสถานะ"
            >
              <RefreshCw className={`w-4 h-4 ${loadingStatus ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Selected Shot Context Badge (if opened from ShotListModal) */}
        {initialBeat && (
          <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/25 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 min-w-0">
              <Zap className="w-4 h-4 text-amber-400 shrink-0 fill-amber-400/80" />
              <span className="font-bold text-purple-200 shrink-0">
                ช็อตที่ {(initialBeat.beatIndex !== undefined ? initialBeat.beatIndex : 0) + 1} ({initialBeat.role?.toUpperCase() || 'B-ROLL'}):
              </span>
              <span className="text-slate-300 truncate max-w-sm sm:max-w-md">
                {initialBeat.text}
              </span>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-cyan-500/15 text-cyan-300 border border-cyan-500/25">
                {initialBeat.duration}s
              </span>
              {initialBeat.cameraDirection && (
                <span className="px-2 py-0.5 rounded text-[11px] bg-white/[0.06] text-slate-300 border border-white/[0.1] truncate max-w-[140px]">
                  {initialBeat.cameraDirection}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Alerts */}
        {errorMsg && (
          <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-200 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* 2 Navigation Tabs */}
        <div className="flex border-b border-zinc-800 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('flow')}
            className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 motion-press active:duration-100 active:scale-[0.97] disabled:active:scale-100 cursor-pointer ${
              activeTab === 'flow'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>ช็อตตามบทสคริปต์ 5 ช็อต (ตามโฟลว์)</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-500/15 text-cyan-300 border border-cyan-500/25">
              5 ช็อต
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('custom')}
            className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 motion-press active:duration-100 active:scale-[0.97] disabled:active:scale-100 cursor-pointer ${
              activeTab === 'custom'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>กำหนดเองอิสระ (Custom Prompt)</span>
          </button>
        </div>

        {/* Tab 1: Flow-First 5-Shots Generation */}
        {activeTab === 'flow' && (
          <div className="space-y-4">
            {/* Top Prominent Action Bar */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-zinc-900 via-zinc-950 to-zinc-900 border border-zinc-800 flex flex-wrap items-center justify-between gap-3 shadow-md">
              <div>
                <h4 className="text-xs font-bold text-zinc-100 uppercase tracking-wide flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <span>สร้าง B-roll อัตโนมัติ 5 ช็อตตามสคริปต์</span>
                </h4>
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  ระบบจัดเตรียมมุมกล้องและ Prompt ตรงกับ 5 ท่อนสคริปต์ (Hook, Feature 1-3, CTA) สามารถสั่งสร้างได้ในคลิกเดียว
                </p>
              </div>
              <button
                type="button"
                onClick={handleGenerateAll5Shots}
                disabled={generatingAll || !status?.service_online}
                className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs flex items-center gap-2 motion-press active:duration-100 cursor-pointer disabled:opacity-50 active:scale-[0.98] disabled:active:scale-100"
              >
                <Zap className="w-3.5 h-3.5 fill-current" />
                <span>{generatingAll ? 'กำลังสั่งสร้างครบ 5 ช็อต...' : 'สั่งสร้าง B-roll ครบ 5 ช็อต'}</span>
              </button>
            </div>

            {/* List of 5 Shot Cards */}
            <div className="space-y-3">
              {loadingShots ? (
                <div className="p-6 text-center text-zinc-400 text-xs flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                  <span>กำลังโหลดข้อมูล 5 ช็อตของมุมนี้...</span>
                </div>
              ) : (
                flowShots.map((shot, index) => {
                  const clipInfo = findFlowClipForBeat(shot, jobs);
                  const isReady = clipInfo?.status === 'ready';
                  const isGenerating = clipInfo?.status === 'generating' || generatingShotIndex === index;
                  const roleCfg = getRoleBadge(shot.role, index);
                  const shotNumber = (shot.beat_index !== undefined ? shot.beat_index : index) + 1;

                  return (
                    <div
                      key={index}
                      className="p-4 rounded-xl bg-zinc-950/80 border border-zinc-800/80 hover:border-zinc-700 motion-press active:duration-100 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm"
                    >
                      {/* Shot Details */}
                      <div className="min-w-0 flex-1 space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${roleCfg.badge}`}>
                            {shot.role_label || roleCfg.label}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[11px] bg-zinc-800 text-zinc-300 border border-zinc-700 font-mono">
                            ช็อตที่ {shotNumber}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[11px] bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-medium">
                            🎥 {shot.camera_direction || 'Orbit 360'}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[11px] bg-zinc-800 text-zinc-400 font-mono">
                            ⏱️ {shot.duration || (index === 0 || index === 4 ? 6 : 8)}s
                          </span>
                        </div>

                        <p className="text-xs font-semibold text-zinc-100">
                          {shot.text}
                        </p>

                        {shot.prompt && (
                          <p className="text-[11px] text-zinc-400 italic line-clamp-1 truncate" title={shot.prompt}>
                            {shot.prompt}
                          </p>
                        )}
                      </div>

                      {/* Action / Status */}
                      <div className="flex items-center gap-2 shrink-0">
                        {isReady ? (
                          <div className="flex items-center gap-2">
                            <span className="px-2.5 py-1 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1.5">
                              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                              คลิปพร้อม
                            </span>
                            <button
                              type="button"
                              onClick={() => handleIngest(clipInfo.job, { path: clipInfo.path })}
                              disabled={ingestingId === clipInfo.job?.id}
                              className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1 transition-colors"
                              title="นำเข้าคลิปลง 01_Raw"
                            >
                              <Download className="w-3.5 h-3.5 text-emerald-400" />
                              <span>{ingestingId === clipInfo.job?.id ? 'นำเข้า...' : 'นำเข้า 01_Raw'}</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleGenerateSingleShot(shot, index)}
                              disabled={generatingShotIndex !== null || generatingAll || !status?.service_online}
                              className="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 text-xs border border-zinc-800"
                              title="สร้างช็อตนี้ใหม่อีกครั้ง"
                            >
                              เจนใหม่
                            </button>
                          </div>
                        ) : isGenerating ? (
                          <span className="px-3 py-1.5 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30 text-xs font-medium flex items-center gap-2">
                            <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
                            กำลังเจนคลิป...
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleGenerateSingleShot(shot, index)}
                            disabled={generatingShotIndex !== null || generatingAll || !status?.service_online}
                            className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md flex items-center gap-1.5 transition-colors cursor-pointer shrink-0"
                          >
                            <Video className="w-3.5 h-3.5" />
                            <span>เจนช็อตนี้</span>
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Custom Prompt Form */}
        {activeTab === 'custom' && (
          <div className="space-y-4 bg-zinc-900/60 p-5 rounded-xl border border-zinc-800">
            {/* Mode Switcher */}
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <span className="text-xs uppercase font-semibold text-zinc-400 tracking-wider">รูปแบบการสร้าง</span>
              <div className="flex rounded-lg bg-zinc-950 p-1 border border-zinc-800 text-xs">
                <button
                  type="button"
                  onClick={() => setMode('text')}
                  className={`px-3 py-1 rounded-md font-medium transition ${
                    mode === 'text' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Text-to-Video
                </button>
                <button
                  type="button"
                  onClick={() => setMode('image')}
                  className={`px-3 py-1 rounded-md font-medium transition ${
                    mode === 'image' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Image-to-Video (ภาพสินค้า)
                </button>
              </div>
            </div>

            {/* Thai Concept for AI Expansion */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1">
                แนวคิดภาพหรือช็อตที่ต้องการ (ภาษาไทย)
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={thaiNotes}
                  onChange={(e) => setThaiNotes(e.target.value)}
                  placeholder="เช่น สินค้าตั้งตระหง่านบนโต๊ะ ไฟสถานะ LED กระพริบสวยงาม"
                  className="flex-1 px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
                />
                <button
                  type="button"
                  onClick={handleExpandPrompt}
                  disabled={expandingPrompt || (!thaiNotes.trim() && !prompt.trim())}
                  className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 shrink-0 transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {expandingPrompt ? 'กำลังเขียน...' : 'ขยาย Prompt ด้วย AI'}
                </button>
              </div>
            </div>

            {/* Presets Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">มุมกล้อง (Camera Motion)</label>
                <select
                  value={technique}
                  onChange={(e) => setTechnique(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="orbit">Orbit 360 (หมุนรอบสินค้า)</option>
                  <option value="macro">Macro Texture (โคลสอัพดีเทล)</option>
                  <option value="dolly_in">Dolly In (ดันกล้องเข้าหา)</option>
                  <option value="reveal">Low Angle Reveal (เสยมุมต่ำ)</option>
                  <option value="floating">Floating (ลอยตัวสโลว์โมชัน)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">โทนแสง (Lighting Style)</label>
                <select
                  value={lighting}
                  onChange={(e) => setLighting(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="studio_clean">Studio Clean (สตูดิโอขาวพรีเมียม)</option>
                  <option value="dramatic_dark">Dramatic Dark (สตูดิโอดำขอบนีออน)</option>
                  <option value="warm_lifestyle">Warm Lifestyle (แสงธรรมชาติอบอุ่น)</option>
                  <option value="futuristic_tech">Futuristic Tech (ห้องแล็บแสงฟ้า)</option>
                </select>
              </div>
            </div>

            {/* Reference Image input if mode == image */}
            {mode === 'image' && (
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  พาทภาพสินค้าอ้างอิง (Absolute Path ใน 01_Raw)
                </label>
                <input
                  type="text"
                  value={referencePath}
                  onChange={(e) => setReferencePath(e.target.value)}
                  placeholder="D:\Programmer\All Project\Omnicut\01_Raw\... หรือชื่อไฟล์"
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>
            )}

            {/* Final Cinematic Prompt */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1">
                คำสั่งสร้างภาพภาษาอังกฤษ (Cinematic English Prompt)
              </label>
              <textarea
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Cinematic vertical commercial shot of tech gadget, slow 360 orbital pan, studio lighting, 9:16 vertical..."
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Submit Button */}
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={handleSubmitGenerate}
                disabled={submitting || !status?.service_online}
                className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-emerald-950/40 flex items-center gap-2 transition-colors cursor-pointer"
              >
                <Video className="w-4 h-4" />
                <span>{submitting ? 'กำลังส่งงานเข้าคิว...' : 'สร้างวิดีโอบน Google Flow'}</span>
              </button>
            </div>
          </div>
        )}

        {/* Recent Jobs & Ingestion Table */}
        {jobs.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-semibold text-zinc-400 tracking-wider">
                คิวงานสร้างวิดีโอล่าสุด ({jobs.length})
              </span>
              <button
                type="button"
                onClick={loadJobs}
                className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                รีเฟรชคิว
              </button>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-between gap-3 text-xs"
                >
                  <div className="truncate flex-1">
                    <div className="font-medium text-zinc-200 truncate">
                      {job.scenes?.[0]?.prompt || job.id}
                    </div>
                    <div className="text-zinc-500 text-[11px] mt-0.5">
                      สถานะ: <span className="text-zinc-300 font-semibold">{job.status}</span> · สร้างเมื่อ: {new Date(job.created_at).toLocaleTimeString('th-TH')}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {job.results?.map((res, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleIngest(job, res)}
                        disabled={ingestingId === job.id}
                        className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1 transition-colors"
                        title="นำเข้าคลิปลง 01_Raw"
                      >
                        <Download className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{ingestingId === job.id ? 'กำลังนำเข้า...' : 'นำเข้าคลัง 01_Raw'}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
