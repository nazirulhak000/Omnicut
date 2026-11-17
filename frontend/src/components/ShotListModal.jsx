import { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Clapperboard,
  ExternalLink,
  Film,
  Loader2,
  Mic,
  Play,
  QrCode,
  RotateCw,
  Scissors,
  Zap,
} from 'lucide-react';
import { Modal, Badge, SafeQRCode } from './ui';
import { toMediaUrl } from '../lib/mediaUrl';
import { DEFAULT_AD_TONE, DEFAULT_VOICE_PRESET } from '../lib/angleToForm';
import { createRecordingSession, getFlowJobs, generateFlowVideo } from '../api';
import { mapCameraTechnique, findFlowClipForBeat } from '../lib/flowUtils';
import GoogleFlowModal from './GoogleFlowModal';

const GEMINI_VOICE_OPTIONS = [
  { id: 'gemini_puck_male_hype', label: 'Puck — ชายพลังสูง สไตล์ TikTok' },
  { id: 'gemini_charon_male_pro', label: 'Charon — ชายทุ้มลึก น่าเชื่อถือ' },
  { id: 'gemini_kore_female_bright', label: 'Kore — หญิงสดใส ป้ายยาเก่ง' },
  { id: 'gemini_aoede_female_pro', label: 'Aoede — หญิงพรีเมียม นุ่มนวล' },
  { id: 'gemini_fenrir_male_strong', label: 'Fenrir — ชายสตรอง คมเข้ม' },
];

const ROLE_LABELS = {
  hook: { label: 'Hook', variant: 'rose' },
  feature: { label: 'Feature', variant: 'cyan' },
  cta: { label: 'CTA', variant: 'emerald' },
};

// "<camera angle> — <action>" as written by scripts/shot_list_builder.py.
function splitDirection(direction) {
  const parts = (direction || '').split('—').map((s) => s.trim());
  return { cameraAngle: parts[0] || '', actionText: parts.length > 1 ? parts.slice(1).join(' — ') : '' };
}

function formatSeconds(sec) {
  const s = Number(sec) || 0;
  return `${s.toFixed(1)}s`;
}

// Mirrors ExportGallery.jsx's buildQuickPostUrl for the guided-take filming
// flow -- see App.jsx's `filmingSessionId` handling and
// scripts/api_recording.py (Phase B/C of
// C:\Users\Winon\.claude\plans\cheeky-cooking-quokka.md).
function buildFilmingUrl(mobileBaseUrl, sessionId) {
  const params = new URLSearchParams({ film: '1', session: sessionId });
  return `${mobileBaseUrl}/?${params.toString()}`;
}

export default function ShotListModal({
  isOpen,
  onClose,
  productId,
  mobileBaseUrl,
  result,
  onRegenerate,
  regenerating = false,
  error = null,
  onOpenStoryboard,
}) {
  const [creatingSession, setCreatingSession] = useState(false);
  const [filmingUrl, setFilmingUrl] = useState(null);
  const [sessionError, setSessionError] = useState(null);

  // Google Flow AI generation states
  const [flowOpen, setFlowOpen] = useState(false);
  const [selectedShotForFlow, setSelectedShotForFlow] = useState(null);
  const [flowJobs, setFlowJobs] = useState([]);
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [batchFeedback, setBatchFeedback] = useState(null);
  const [previewClipIndex, setPreviewClipIndex] = useState(null);

  const engineType = result?.voice_params?.voice_engine_type || result?.angle?.voice_engine_type;
  const isEdgeTts = engineType === 'edge_tts' || (!result?.voice_params?.voice_preset && !result?.angle?.voice_preset);
  const activeVoicePreset = result?.voice_params?.voice_preset || result?.angle?.voice_preset || DEFAULT_VOICE_PRESET;
  const [selectedVoice, setSelectedVoice] = useState(activeVoicePreset);

  const loadJobs = useCallback(async () => {
    if (!productId) return;
    try {
      const data = await getFlowJobs(productId);
      setFlowJobs(data.jobs || []);
    } catch {
      // Silent error
    }
  }, [productId]);

  useEffect(() => {
    if (!isOpen || !productId) return;
    loadJobs();
  }, [isOpen, productId, loadJobs]);

  // Periodic poll if any job is queued or running
  useEffect(() => {
    if (!isOpen || !productId) return;
    const hasActive = flowJobs.some((j) => j.status === 'queued' || j.status === 'running');
    if (!hasActive) return;

    const interval = setInterval(() => {
      loadJobs();
    }, 4000);

    return () => clearInterval(interval);
  }, [isOpen, productId, flowJobs, loadJobs]);

  useEffect(() => {
    if (result?.voice_params?.voice_preset) {
      setSelectedVoice(result.voice_params.voice_preset);
    } else if (result?.angle?.voice_preset) {
      setSelectedVoice(result.angle.voice_preset);
    }
  }, [result?.voice_params?.voice_preset, result?.angle?.voice_preset]);

  if (!result) return null;
  const { angle, shot_list: shotList = [], voice_audio_path: voiceAudioPath, total_duration: totalDuration } = result;

  const handleTriggerRegenerate = () => {
    onRegenerate?.({
      voice_engine_type: 'gemini_tts',
      voice_preset: selectedVoice,
      voice_rate: '+15%',
      ad_tone: result?.voice_params?.ad_tone || result?.angle?.ad_tone || DEFAULT_AD_TONE,
    });
  };

  const handleStartSession = async () => {
    if (!productId || !angle?.angle_id) return;
    setCreatingSession(true);
    setSessionError(null);
    try {
      const res = await createRecordingSession(productId, angle.angle_id);
      setFilmingUrl(buildFilmingUrl(mobileBaseUrl, res.session_id));
    } catch (err) {
      setSessionError(err.friendlyMessage || err.message || 'สร้างเซสชันถ่ายทำไม่สำเร็จ');
    } finally {
      setCreatingSession(false);
    }
  };

  const handleClose = () => {
    setFilmingUrl(null);
    setSessionError(null);
    setBatchFeedback(null);
    setPreviewClipIndex(null);
    onClose?.();
  };

  // Trigger single shot generation modal with pre-bundled context
  const handleOpenFlowForShot = (beat) => {
    const dur = Math.round(beat.planned_duration || (beat.end - beat.start) || 8);
    setSelectedShotForFlow({
      beatIndex: beat.beat_index,
      text: beat.text,
      cameraDirection: beat.camera_direction,
      duration: dur,
      role: beat.role,
    });
    setFlowOpen(true);
  };

  // Trigger batch generation for all shots in this shotlist
  const handleBatchGenerate = async () => {
    if (!productId || shotList.length === 0 || batchGenerating) return;
    setBatchGenerating(true);
    setBatchFeedback(null);

    const scenes = shotList.map((beat) => {
      const { cameraAngle, actionText } = splitDirection(beat.camera_direction);
      const technique = mapCameraTechnique(beat.camera_direction);
      const dur = Math.min(10, Math.max(4, Math.round(beat.planned_duration || (beat.end - beat.start) || 8)));
      const shotNum = (beat.beat_index !== undefined ? beat.beat_index : 0) + 1;
      return {
        prompt: `Cinematic vertical commercial video of ${angle?.angle_name || angle?.title || 'product'}, ${beat.text}. Action: ${actionText || beat.camera_direction}. Camera: ${cameraAngle || 'orbit'}. Clean studio lighting, 9:16 vertical, hyper-realistic.`,
        type: 'video',
        aspect_ratio: '9:16',
        duration: dur,
        technique,
        shot_index: beat.beat_index,
        shot_label: `shot_${shotNum}_${beat.role || 'broll'}`,
        download_quality: 'original',
      };
    });

    try {
      await generateFlowVideo({
        product_id: productId,
        scenes,
        project_name: angle?.angle_name || angle?.title || 'batch_broll',
      });
      setBatchFeedback({
        type: 'success',
        text: `ส่งงานสร้าง AI B-roll อัตโนมัติ ${scenes.length} ช็อตเข้าคิว Google Flow สำเร็จ ระบบจะทยอยสร้างและดูดเข้าตัดต่อเบื้องหลัง`,
      });
      await loadJobs();
    } catch (err) {
      setBatchFeedback({
        type: 'error',
        text: err.response?.data?.detail || 'ส่งงานสร้าง AI B-roll อัตโนมัติไม่สำเร็จ กรุณาตรวจสอบสถานะ Flow Service',
      });
    } finally {
      setBatchGenerating(false);
    }
  };

  // Count ready AI clips
  const readyClipsCount = shotList.filter((beat) => {
    const flowClip = findFlowClipForBeat(beat, flowJobs);
    return flowClip?.status === 'ready';
  }).length;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={`แผนถ่าย: ${angle?.angle_name || ''}`}
      subtitle={`${shotList.length} ช็อต · ยาวรวม ${formatSeconds(totalDuration)} (${isEdgeTts ? 'จากจังหวะเสียง Edge-TTS เดิม' : 'จากจังหวะเสียง Gemini TTS จริง'})`}
      maxWidth="max-w-3xl"
    >
      <div className="space-y-4">
        {/* ── Google Flow Batch Generator Action Banner ── */}
        <section
          aria-label="Google Flow B-roll Action Bar"
          className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-gradient-to-r from-purple-950/40 via-zinc-900/60 to-cyan-950/30 border border-purple-500/25 shadow-inner"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-300 shrink-0">
              <Zap className="w-4 h-4 fill-amber-400 text-amber-400" />
            </div>
            <div className="min-w-0">
              <div className="text-xs font-bold text-white flex items-center gap-2 flex-wrap">
                <span>Google Flow (Veo AI) B-roll Auto-Pilot</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-medium bg-cyan-500/15 text-cyan-300 border border-cyan-500/25">
                  AI พร้อม: {readyClipsCount}/{shotList.length} ช็อต
                </span>
              </div>
              <div className="text-[11px] text-slate-400 truncate">
                สร้างฟุตเทจวิดีโอ 9:16 ด้วย Veo เบื้องหลังอัตโนมัติ พร้อมดูดเข้าตัดต่อ
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleBatchGenerate}
              disabled={batchGenerating || shotList.length === 0}
              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-purple-950/50 disabled:opacity-50 disabled:cursor-wait transition-all cursor-pointer"
              title="สั่งสร้าง B-roll อัตโนมัติทุกช็อตด้วย Google Flow"
            >
              {batchGenerating ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Zap className="w-3.5 h-3.5 fill-amber-300 text-amber-300" />
              )}
              <span>{batchGenerating ? 'กำลังสร้างทุกช็อต...' : 'สร้าง AI B-roll อัตโนมัติทุกช็อต'}</span>
            </button>
          </div>
        </section>

        {/* Batch Feedback Banner */}
        {batchFeedback && (
          <div
            className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
              batchFeedback.type === 'success'
                ? 'bg-emerald-950/60 border border-emerald-800 text-emerald-200'
                : 'bg-rose-950/60 border border-rose-800 text-rose-200'
            }`}
          >
            {batchFeedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            )}
            <span>{batchFeedback.text}</span>
          </div>
        )}

        {error && (
          <div role="alert" className="flex items-start gap-2 rounded-lg bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
            <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <span className="leading-relaxed"><strong className="font-bold text-rose-300">สังเคราะห์เสียงพากย์ไม่สำเร็จ:</strong> {error}</span>
          </div>
        )}

        {result.is_stale && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
            <span className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              บทเปลี่ยนหลังสร้างแผนถ่ายนี้ จังหวะเสียงอาจไม่ตรงกับบทล่าสุด
            </span>
            {onRegenerate && (
              <button
                type="button"
                onClick={handleTriggerRegenerate}
                disabled={regenerating}
                className="px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-100 text-xs font-bold whitespace-nowrap transition-colors disabled:opacity-50"
              >
                {regenerating ? 'กำลังสร้างใหม่' : 'อัปเดตแผนถ่าย'}
              </button>
            )}
          </div>
        )}

        {/* Guide voice: picker, regenerate and player in one surface. */}
        <section aria-label="เสียงนำถ่าย" className="rounded-xl bg-white/[0.03] p-3 space-y-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <Mic className="w-4 h-4 text-[#25F4EE] flex-shrink-0" />
            <span className="text-xs font-bold text-slate-200">เสียงนำถ่าย</span>
            <span className="text-[11px] text-slate-500">เปิดฟังคลอตอนถ่าย</span>
            {isEdgeTts && (
              <span className="text-[10px] font-bold text-amber-300 bg-amber-500/15 px-2 py-0.5 rounded-full">Edge-TTS เดิม</span>
            )}
            {onRegenerate && (
              <div className="w-full sm:w-auto sm:ml-auto flex items-center gap-2">
                <select
                  value={selectedVoice}
                  onChange={(e) => setSelectedVoice(e.target.value)}
                  disabled={regenerating}
                  aria-label="เสียงพากย์ Gemini TTS"
                  className="min-w-0 flex-1 sm:flex-initial bg-black/40 border border-white/[0.1] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#25F4EE] transition-colors cursor-pointer"
                >
                  {GEMINI_VOICE_OPTIONS.map((opt) => (
                    <option key={opt.id} value={opt.id}>{opt.label}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleTriggerRegenerate}
                  disabled={regenerating}
                  title="สังเคราะห์เสียงพากย์ Gemini Flash และคำนวณจังหวะช็อตใหม่"
                  className="px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-white text-xs font-bold flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-wait transition-colors whitespace-nowrap"
                >
                  {regenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCw className="w-3.5 h-3.5" />}
                  <span>{regenerating ? 'กำลังสร้าง' : 'สร้างใหม่ด้วยเสียงนี้'}</span>
                </button>
              </div>
            )}
          </div>
          {voiceAudioPath && <audio controls className="w-full h-9" src={toMediaUrl(voiceAudioPath)} />}
          {isEdgeTts && (
            <p className="text-[11px] text-amber-200/90">
              ไฟล์เสียงนี้สร้างด้วย Edge-TTS เดิม เลือกเสียง Gemini แล้วกด สร้างใหม่ด้วยเสียงนี้
            </p>
          )}
        </section>

        <p className="flex items-start gap-2 text-xs text-slate-400 leading-relaxed">
          <Camera className="w-3.5 h-3.5 text-amber-300 flex-shrink-0 mt-0.5" />
          <span>
            ตั้งกล้องมุมเดียวแล้ว<strong className="font-bold text-amber-200">ห้ามขยับตลอดเทกหลัก</strong>
            {' '}ทำแอคชั่นแต่ละช็อตให้ตรงจังหวะเสียง ซูมและเน้นจังหวะระบบใส่ให้ตอนตัดต่อ
          </span>
        </p>

        {/* Shots as a timeline: time on the left, what to say and do on the right. */}
        <ol aria-label="ช็อตในแผนถ่าย" className="max-h-[50vh] overflow-y-auto rounded-xl border border-white/[0.06] divide-y divide-white/[0.06]">
          {shotList.map((beat, i) => {
            const roleMeta = ROLE_LABELS[beat.role] || { label: beat.role, variant: 'slate' };
            const { cameraAngle, actionText } = splitDirection(beat.camera_direction);
            const sameCamera = i > 0 && cameraAngle && cameraAngle === splitDirection(shotList[i - 1].camera_direction).cameraAngle;
            const flowClip = findFlowClipForBeat(beat, flowJobs);
            const isPreviewing = previewClipIndex === beat.beat_index;

            return (
              <li key={beat.beat_index} className="grid grid-cols-[4.75rem_minmax(0,1fr)] gap-3 px-3 py-3">
                <div className="space-y-1.5">
                  <span className="block font-mono text-[11px] tabular-nums text-slate-300">
                    {formatSeconds(beat.start)}–{formatSeconds(beat.end)}
                  </span>
                  <div className="flex flex-wrap items-center gap-1">
                    <Badge variant={roleMeta.variant} size="sm">{roleMeta.label}</Badge>
                    {beat.is_separate_clip && <Badge variant="purple" size="sm" icon={Film}>แยกคลิป</Badge>}
                  </div>
                </div>

                <div className="min-w-0 space-y-2">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="text-sm text-white leading-snug flex-1 min-w-[200px]">{beat.text}</p>

                    {/* Flow AI Action / Status Indicator for this shot */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      {flowClip?.status === 'ready' ? (
                        <div className="flex items-center gap-1.5">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            <span>B-roll พร้อม</span>
                          </span>

                          <button
                            type="button"
                            onClick={() => setPreviewClipIndex(isPreviewing ? null : beat.beat_index)}
                            className="px-2 py-0.5 rounded text-[11px] font-semibold bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 border border-white/[0.1] flex items-center gap-1 transition-colors cursor-pointer"
                            title="ดูตัวอย่างวิดีโอ AI B-roll"
                          >
                            <Play className="w-3 h-3 text-cyan-400" />
                            <span>{isPreviewing ? 'ปิด' : 'พรีวิว'}</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => handleOpenFlowForShot(beat)}
                            className="text-[11px] text-slate-400 hover:text-cyan-300 transition-colors underline underline-offset-2 ml-0.5"
                            title="สร้างเทกใหม่สำหรับช็อตนี้"
                          >
                            เจนใหม่
                          </button>
                        </div>
                      ) : flowClip?.status === 'generating' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30 animate-pulse">
                          <Loader2 className="w-3 h-3 animate-spin text-amber-400" />
                          <span>กำลังเจน B-roll...</span>
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleOpenFlowForShot(beat)}
                          className="px-2.5 py-1 rounded-lg bg-gradient-to-r from-purple-500/15 to-cyan-500/15 hover:from-purple-500/25 hover:to-cyan-500/25 border border-purple-500/30 hover:border-cyan-500/40 text-cyan-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer shadow-sm"
                          title="สร้าง B-roll สำหรับช็อตนี้ด้วย Google Flow (Veo)"
                        >
                          <Zap className="w-3.5 h-3.5 text-amber-400 fill-amber-400/80 shrink-0" />
                          <span>เจน B-roll (Flow)</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <p className="flex items-start gap-1.5 text-xs text-amber-200/90 leading-relaxed">
                    <Clapperboard className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" aria-label="แอคชั่น" />
                    <span>{actionText || beat.camera_direction}</span>
                  </p>

                  {cameraAngle && (
                    <p className="flex items-start gap-1.5 text-xs text-slate-400 leading-relaxed">
                      <Camera className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" aria-label="มุมกล้อง" />
                      <span>{sameCamera ? 'กล้องมุมเดิม' : cameraAngle}</span>
                    </p>
                  )}

                  {/* Inline Mini-Preview Player when toggled */}
                  {isPreviewing && flowClip?.path && (
                    <div className="pt-1.5">
                      <div className="p-2 rounded-xl bg-black/60 border border-white/[0.12] inline-block shadow-lg">
                        <video
                          src={toMediaUrl(flowClip.path)}
                          controls
                          autoPlay
                          playsInline
                          className="w-48 max-w-full rounded-lg aspect-[9/16] object-cover bg-black"
                        />
                        <div className="mt-1 text-[10px] text-slate-400 text-center truncate max-w-[12rem]">
                          {flowClip.path.split(/[/\\]/).pop()}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>

        <div className="space-y-3">
          {filmingUrl ? (
            <div className="flex flex-col items-center gap-2 p-4 rounded-xl bg-white/[0.03]">
              <div className="p-2 bg-white rounded-xl">
                <SafeQRCode value={filmingUrl} size={150} level="M" />
              </div>
              <p className="text-[11px] text-slate-400 text-center">
                สแกนด้วยมือถือ (ต้องอยู่ Wi-Fi วงเดียวกับคอมพิวเตอร์เครื่องนี้) เพื่อเปิดหน้าถ่ายทำพร้อมไกด์ทีละช็อต
              </p>
              <button
                type="button"
                onClick={() => window.open(filmingUrl, '_blank', 'noopener')}
                className="text-xs text-[#25F4EE] hover:text-[#25F4EE]/80 flex items-center gap-1.5 font-bold transition-colors cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>เปิดหน้ากล้องบนเครื่องนี้ (ไม่ต้องสแกน)</span>
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[11px] text-slate-500">ถ่ายด้วยมือถือพร้อมไกด์ทีละช็อตตามแผนนี้</span>
              <div className="flex flex-wrap items-center gap-2">
                {onOpenStoryboard && (
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      onOpenStoryboard(angle);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-slate-200 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Scissors className="w-3.5 h-3.5" />
                    <span>วางแผนช็อตเอง (Storyboard)</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setSelectedShotForFlow(null);
                    setFlowOpen(true);
                  }}
                  className="px-3 py-1.5 rounded-xl bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 text-purple-300 text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors"
                >
                  <Film className="w-3.5 h-3.5" />
                  <span>สร้าง B-roll (Google Flow)</span>
                </button>
                <button
                  type="button"
                  onClick={handleStartSession}
                  disabled={creatingSession}
                  className="px-3 py-1.5 rounded-lg bg-[#25F4EE] hover:bg-[#4ff8f2] text-slate-950 text-xs font-bold flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-wait transition-colors cursor-pointer"
                >
                  {creatingSession ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <QrCode className="w-3.5 h-3.5" />}
                  <span>เริ่มถ่ายด้วยมือถือ (QR)</span>
                </button>
              </div>
            </div>
          )}
          {sessionError && <p className="text-[11px] text-rose-400">{sessionError}</p>}
        </div>
      </div>

      <GoogleFlowModal
        isOpen={flowOpen}
        onClose={() => {
          setFlowOpen(false);
          setSelectedShotForFlow(null);
          loadJobs();
        }}
        productId={productId}
        angleId={angle?.angle_id || angle?.id}
        productName={angle?.title || angle?.angle_name || ''}
        initialBeat={selectedShotForFlow}
        onClipIngested={() => loadJobs()}
      />
    </Modal>
  );
}
