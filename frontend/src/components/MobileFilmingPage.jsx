import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Home, Camera, Circle, X, Check, CheckCircle2, Loader2,
  AlertCircle, Volume2, Clapperboard, RotateCw,
} from 'lucide-react';
import {
  getRecordingSession, getShotList, uploadRecordingSegment,
  finalizeRecordingSession, getTaskStatus,
} from '../api';
import { toMediaUrl } from '../lib/mediaUrl';

const ROLE_LABELS = { hook: 'Hook', feature: 'Feature', cta: 'CTA' };

// Tries mimeTypes roughly in quality order; whatever the phone's browser
// actually supports is normalized to a consistent codec server-side anyway
// (scripts/recording_sessions.py's _normalize_segment), so this only needs
// to find SOMETHING MediaRecorder will accept, not the "best" one.
// mp4/h264 is listed first even though it's not the highest-quality codec:
// Safari only recently (iOS 17.5+) added VP9 MediaRecorder support and its
// encoder is still unreliable feeding from a canvas.captureStream() source
// -- isTypeSupported() reports true but the produced file's container is
// sometimes malformed (ffprobe can't read duration). h264/mp4 has been
// stable on Safari since iOS 14.3, so prefer it wherever available.
function pickSupportedMimeType() {
  const candidates = [
    'video/mp4;codecs=avc1',
    'video/mp4',
    'video/webm;codecs=vp8,opus',
    'video/webm;codecs=vp9,opus',
    'video/webm',
  ];
  for (const type of candidates) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported?.(type)) {
      return type;
    }
  }
  return '';
}

function formatSeconds(sec) {
  const s = Number(sec) || 0;
  return `${s.toFixed(1)}s`;
}

// Mobile companion page for the guided-take filming feature: opened via a QR
// code scanned from ShotListModal.jsx. Records one segment per script beat,
// auto-cut to that beat's real planned duration, with a review step before
// each beat counts. See C:\Users\Winon\.claude\plans\cheeky-cooking-quokka.md
// for the original design and the /grill-me session in-thread for this
// recording-flow redesign.
//
// Recording model (all local until the very end -- nothing hits the server
// until every beat is confirmed):
//   'ready'     -- about to record shotList[confirmedClips.length]. Tapping
//                  the record button starts a countdown timer set to that
//                  beat's planned_duration.
//   'recording' -- countdown running; auto-stops at 0, or the user can tap
//                  to stop early.
//   'reviewing' -- plays back the just-recorded (unconfirmed) clip. Confirm
//                  keeps it and advances; Back discards it and re-arms the
//                  SAME beat.
//   'sending'   -- every confirmed clip uploads in one batch, then finalize
//                  is triggered -- see handleSendAll.
//   'done'      -- session.status is 'completed' server-side.
//
// Back (X) is a single "undo the most recent thing" action across both
// 'reviewing' and 'ready': in 'reviewing' there IS a fresh unconfirmed take
// to discard, so it re-arms the same beat; in 'ready' there's nothing fresh
// yet, so it un-confirms and re-arms the last CONFIRMED beat instead. Both
// cases reduce to the same rule: drop the most recent recording and make
// its beat redo-able. Pressed repeatedly from 'ready' it keeps stepping
// back one confirmed beat at a time, with no bound other than beat 0.
export default function MobileFilmingPage({ sessionId, onExit }) {
  // "เปิดหน้ากล้องบนเครื่องนี้เลย" opens this page via window.open() from the
  // ProductToClip tab, which stays open in the background on the SAME
  // device/script/angle -- window.close() returns focus to that exact tab
  // (which already refetches on focus, so it picks up the just-attached
  // guided-take video with no extra plumbing). That only works for
  // script-opened tabs though: the QR-scanned-on-another-device flow lands
  // here as a plain top-level navigation, where close() is silently
  // blocked by the browser, so fall back to the old "go to app home"
  // behavior after a short delay in that case.
  const handleExit = useCallback(() => {
    window.close();
    window.setTimeout(() => { if (onExit) onExit(); }, 300);
  }, [onExit]);

  const [session, setSession] = useState(null);
  const [shotList, setShotList] = useState([]);
  const [voiceAudioPath, setVoiceAudioPath] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [cameraError, setCameraError] = useState(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [canvasReady, setCanvasReady] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);

  const [phase, setPhase] = useState('ready'); // ready | recording | reviewing | sending | done
  const [confirmedClips, setConfirmedClips] = useState([]); // [{blob, mimeType}], always a prefix of shotList
  const [countdown, setCountdown] = useState(0);
  const [activeDuration, setActiveDuration] = useState(0);
  const [reviewUrl, setReviewUrl] = useState(null);
  const [sendError, setSendError] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const videoPreviewRef = useRef(null);
  const canvasRef = useRef(null);
  const guideAudioRef = useRef(null);
  const activeAudioTickRef = useRef(null);
  const streamRef = useRef(null);
  const canvasStreamRef = useRef(null);
  const zoomLevelRef = useRef(1);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const pendingBlobRef = useRef(null);
  const pendingMimeTypeRef = useRef('');

  useEffect(() => { zoomLevelRef.current = zoomLevel; }, [zoomLevel]);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const stopGuideAudio = useCallback(() => {
    const audio = guideAudioRef.current;
    if (audio) {
      if (activeAudioTickRef.current) {
        audio.removeEventListener('timeupdate', activeAudioTickRef.current);
        activeAudioTickRef.current = null;
      }
      try {
        audio.pause();
      } catch (e) {
        // ignore
      }
    }
  }, []);

  useEffect(() => {
    return () => {
      stopGuideAudio();
    };
  }, [stopGuideAudio]);

  const loadSession = useCallback(async () => {
    const sess = await getRecordingSession(sessionId);
    setSession(sess);
    if (!sess) return sess;
    const sl = await getShotList(sess.product_id, sess.angle_id).catch(() => null);
    if (sl) {
      setShotList(sl.shot_list || []);
      setVoiceAudioPath(sl.voice_audio_path || null);
    }
    return sess;
  }, [sessionId]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    loadSession()
      .catch((err) => { if (mounted) setLoadError(err.friendlyMessage || err.message || 'โหลดเซสชันไม่สำเร็จ'); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [loadSession]);

  // Camera: acquired once and kept alive for the whole session -- recording
  // reads from the canvas below, not this stream directly, so no mic
  // permission is needed here at all.
  useEffect(() => {
    let cancelled = false;
    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1920 }, frameRate: { ideal: 30 } },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoPreviewRef.current) {
          videoPreviewRef.current.srcObject = stream;
        }
        setCameraReady(true);
      } catch (err) {
        if (!cancelled) setCameraError(err.message || 'เปิดกล้องไม่สำเร็จ กรุณาอนุญาตการใช้กล้อง');
      }
    }
    start();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, []);

  // Draws the raw camera feed onto a visible <canvas> every frame, applying
  // the digital zoom crop -- this canvas (not the raw camera stream) is BOTH
  // what's shown on screen AND what MediaRecorder records from
  // (canvas.captureStream()), so zoom always matches between preview and
  // recording.
  useEffect(() => {
    if (!cameraReady) return;
    const video = videoPreviewRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    // Fixed output resolution -- matches the server's own final normalize
    // target anyway (scripts/recording_sessions.py's _normalize_segment).
    // Always downscaled for display (object-cover below fits it to the real
    // screen), never upscaled, so it never looks blocky regardless of
    // device pixel density.
    canvas.width = 1080;
    canvas.height = 1920;
    const ctx = canvas.getContext('2d');
    canvasStreamRef.current = canvas.captureStream(30);
    setCanvasReady(true);

    let rafId;
    const draw = () => {
      const vw = video.videoWidth;
      const vh = video.videoHeight;
      if (vw && vh) {
        const zoom = Math.max(1, zoomLevelRef.current);
        const cropW = vw / zoom;
        const cropH = vh / zoom;
        const scale = Math.max(canvas.width / cropW, canvas.height / cropH);
        const sw = Math.min(vw, canvas.width / scale);
        const sh = Math.min(vh, canvas.height / scale);
        const sx = (vw - sw) / 2;
        const sy = (vh - sh) / 2;
        ctx.drawImage(video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      }
      rafId = requestAnimationFrame(draw);
    };
    rafId = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(rafId);
      canvasStreamRef.current?.getTracks().forEach((t) => t.stop());
      canvasStreamRef.current = null;
      setCanvasReady(false);
    };
  }, [cameraReady]);

  // Countdown while recording -- auto-stops at 0. Re-armed fresh every time
  // `phase` becomes 'recording' (once per beat attempt).
  useEffect(() => {
    if (phase !== 'recording') return undefined;
    const startedAt = performance.now();
    let rafId;
    const tick = () => {
      const elapsed = (performance.now() - startedAt) / 1000;
      const remaining = Math.max(0, activeDuration - elapsed);
      setCountdown(remaining);
      if (remaining <= 0) {
        stopRecorder();
        return;
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- activeDuration is fixed for the lifetime of one 'recording' phase
  }, [phase]);

  const cleanupReview = () => {
    stopGuideAudio();
    if (reviewUrl) URL.revokeObjectURL(reviewUrl);
    setReviewUrl(null);
    pendingBlobRef.current = null;
    pendingMimeTypeRef.current = '';
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black text-white flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#25F4EE]" />
      </div>
    );
  }

  if (loadError || !session) {
    return (
      <div className="fixed inset-0 bg-black text-white flex flex-col items-center justify-center gap-3 p-6 text-center">
        <AlertCircle className="w-8 h-8 text-rose-400" />
        <p className="text-sm text-slate-300">{loadError || 'ไม่พบเซสชันถ่ายทำ'}</p>
        {onExit && (
          <button onClick={handleExit} className="mt-2 py-2 px-4 rounded-xl bg-white/[0.08] text-xs font-bold flex items-center gap-1.5 cursor-pointer">
            <Home className="w-3.5 h-3.5" /> หน้าหลัก
          </button>
        )}
      </div>
    );
  }

  const totalBeats = shotList.length;
  const currentIndex = confirmedClips.length; // next beat to record; == totalBeats once all confirmed
  const isComplete = currentIndex >= totalBeats;
  const currentBeat = !isComplete ? shotList[currentIndex] : null;
  const isDone = session.status === 'completed' || phase === 'done';

  const playGuideAudioForBeat = (beat) => {
    const audio = guideAudioRef.current;
    if (!audio || !beat) return;
    // Always stop and remove any active listener before starting new playback
    stopGuideAudio();

    const startTime = Math.max(0, Number(beat.start) || 0);
    const endTime = (beat.end && Number(beat.end) > startTime) ? Number(beat.end) : Infinity;

    try {
      audio.currentTime = startTime;
    } catch (e) {
      console.warn('[MobileFilmingPage] failed setting audio currentTime:', e);
    }

    const onTick = () => {
      if (audio.currentTime >= endTime) {
        stopGuideAudio();
      }
    };
    activeAudioTickRef.current = onTick;
    audio.addEventListener('timeupdate', onTick);

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        console.warn('[MobileFilmingPage] auto guide audio play prevented:', err);
      });
    }
  };

  const handleStartRecording = () => {
    const stream = canvasStreamRef.current;
    if (!stream || !currentBeat) return;
    const mimeType = pickSupportedMimeType();
    try {
      // Explicit bitrate: MediaRecorder's own default for a canvas-sourced
      // stream can be conservative, and this is a redraw+re-encode of the
      // camera feed -- a low bitrate here would visibly compound as extra
      // compression noise/blockiness in the final saved video.
      const recorderOptions = { videoBitsPerSecond: 6_000_000, ...(mimeType ? { mimeType } : {}) };
      const recorder = new MediaRecorder(stream, recorderOptions);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        // recorder.mimeType is what MediaRecorder actually used, which can
        // differ from the mimeType we asked for -- using it here (rather
        // than our own guess) keeps the Blob's declared type honest, so a
        // container/codec mismatch never gets mislabeled going into upload.
        const actualMimeType = recorder.mimeType || mimeType || 'video/webm';
        const blob = new Blob(chunksRef.current, { type: actualMimeType });
        chunksRef.current = [];
        console.log('[MobileFilmingPage] segment recorded', { beat: currentIndex, mimeType: actualMimeType, size: blob.size });
        if (blob.size < 5000) {
          showToast(`เตือน: ไฟล์ที่อัดดูเล็กผิดปกติ (${blob.size} bytes) อาจอัปโหลดไม่ได้`);
        }
        pendingBlobRef.current = blob;
        pendingMimeTypeRef.current = actualMimeType;
        setReviewUrl(URL.createObjectURL(blob));
        setPhase('reviewing');
      };
      mediaRecorderRef.current = recorder;
      // Timeslice (fire ondataavailable periodically) rather than buffering
      // everything until stop() -- Safari's MediaRecorder has documented
      // issues delivering a complete final chunk on stop() for some stream
      // sources when never given a timeslice.
      recorder.start(500);
      setActiveDuration(currentBeat.planned_duration || 0);
      setCountdown(currentBeat.planned_duration || 0);
      setPhase('recording');
      if (voiceAudioPath) playGuideAudioForBeat(currentBeat);
    } catch (err) {
      showToast('เริ่มอัดไม่สำเร็จ: ' + err.message);
    }
  };

  // Stops the active MediaRecorder -- shared by the countdown's auto-cut and
  // a manual early-stop tap. Guards against double-stop (both firing near
  // the same instant).
  function stopRecorder() {
    stopGuideAudio();
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state === 'recording') {
      recorder.stop();
    }
  }

  const handleConfirm = async () => {
    stopGuideAudio();
    if (!pendingBlobRef.current) return;
    const clip = { blob: pendingBlobRef.current, mimeType: pendingMimeTypeRef.current };
    const next = [...confirmedClips, clip];
    cleanupReview();
    setConfirmedClips(next);
    if (next.length >= totalBeats) {
      await handleSendAll(next);
    } else {
      setPhase('ready');
    }
  };

  // Back: discards the most recent recording (the fresh unconfirmed take in
  // 'reviewing', or the last CONFIRMED beat if there's no fresh take, i.e.
  // 'ready') and re-arms that beat. Repeatable -- each press steps back one
  // more beat once there's nothing fresh left to discard.
  const handleBack = () => {
    stopGuideAudio();
    if (phase === 'reviewing') {
      cleanupReview();
      setPhase('ready');
      return;
    }
    if (confirmedClips.length === 0) return;
    setConfirmedClips((prev) => prev.slice(0, -1));
    setPhase('ready');
  };

  const handleSendAll = async (clips) => {
    setPhase('sending');
    setSendError(null);
    try {
      // Re-check current server state before (re-)sending: on a retry after
      // a partial failure, some segments (or even finalize itself) may have
      // already succeeded server-side -- scripts/recording_sessions.py's
      // upload_segment rejects any beat_index that isn't the next pending
      // one, so blindly re-uploading from 0 again would 400 on the very
      // first already-accepted segment instead of resuming past it.
      const current = await getRecordingSession(sessionId);
      if (current?.status === 'completed') {
        await loadSession();
        setPhase('done');
        return;
      }
      const alreadyUploaded = new Set(
        (current?.segments || []).filter((s) => s.status === 'uploaded').map((s) => s.beat_index)
      );
      for (let i = 0; i < clips.length; i += 1) {
        if (alreadyUploaded.has(i)) continue;
        const { blob, mimeType } = clips[i];
        const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
        console.log('[MobileFilmingPage] uploading segment', { beat: i, mimeType, size: blob.size });
        try {
          await uploadRecordingSegment(sessionId, i, blob, `seg_${i}.${ext}`);
        } catch (uploadErr) {
          const detail = uploadErr.response?.data?.detail || uploadErr.friendlyMessage || uploadErr.message;
          throw new Error(`ช็อตที่ ${i + 1}: ${detail} (ไฟล์ ${(blob.size / 1024).toFixed(0)} KB, ${mimeType})`);
        }
      }
      const res = await finalizeRecordingSession(sessionId);
      for (let attempt = 0; attempt < 60; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        const task = await getTaskStatus(res.task_id);
        if (task.status === 'completed') {
          await loadSession();
          setPhase('done');
          return;
        }
        if (task.status === 'failed') {
          setSendError(task.error || 'รวมคลิปไม่สำเร็จ');
          return;
        }
      }
      setSendError('รวมคลิปใช้เวลานานเกินไป กรุณาลองใหม่');
    } catch (err) {
      // Clips stay in confirmedClips -- retry just re-sends from memory,
      // no need to re-film anything.
      setSendError(err.friendlyMessage || err.message || 'ส่งวิดีโอไม่สำเร็จ');
    }
  };

  return (
    <div className="fixed inset-0 bg-black text-white font-prompt overflow-hidden">
      {toastMessage && (
        <div className="fixed top-[calc(env(safe-area-inset-top)+0.75rem)] left-4 right-4 z-50 p-3.5 rounded-2xl bg-[#25F4EE] text-slate-950 font-bold text-xs text-center shadow-2xl border border-white/20">
          {toastMessage}
        </div>
      )}

      {/* The <video> is a hidden decode source only (drawImage reads its
          frames) -- the visible, full-bleed live preview is the <canvas>,
          which is also what gets recorded. During 'reviewing' the just-
          recorded clip plays back over it instead (see below). */}
      <video
        ref={videoPreviewRef}
        autoPlay
        playsInline
        muted
        style={{ position: 'absolute', width: 1, height: 1, opacity: 0, pointerEvents: 'none' }}
      />
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full object-cover" />

      {phase === 'reviewing' && reviewUrl && (
        <video
          key={reviewUrl}
          src={reviewUrl}
          autoPlay
          playsInline
          loop
          className="absolute inset-0 w-full h-full object-cover z-[5] bg-black"
        />
      )}

      {cameraError && (
        <div className="absolute inset-0 z-10 flex items-center justify-center p-6 bg-black text-center">
          <div className="flex flex-col items-center gap-2 max-w-xs">
            <Camera className="w-8 h-8 text-rose-400" />
            <p className="text-sm text-rose-300">{cameraError}</p>
          </div>
        </div>
      )}

      <audio ref={guideAudioRef} src={voiceAudioPath ? toMediaUrl(voiceAudioPath) : undefined} className="hidden" />

      {/* Top overlay: no scrim panel -- full camera stays visible, each
          control carries its own small pill/circle background instead. */}
      <div className="absolute top-0 inset-x-0 z-20" style={{ paddingTop: 'env(safe-area-inset-top)' }}>
        <div className="flex items-center justify-between px-4 pt-3 pb-2">
          {onExit ? (
            <button
              onClick={handleExit}
              aria-label="หน้าหลัก"
              className="w-11 h-11 rounded-full bg-black/45 border border-white/15 backdrop-blur-sm flex items-center justify-center text-slate-200 active:scale-90 transition-transform cursor-pointer"
            >
              <Home className="w-5 h-5" />
            </button>
          ) : <div className="w-11 h-11" />}

          <div className="px-3 py-1.5 rounded-full bg-black/45 border border-white/15 backdrop-blur-sm flex items-center gap-1.5">
            <Clapperboard className="w-3.5 h-3.5 text-amber-300" />
            <span className="text-xs font-bold font-mono">
              ช็อตที่ {Math.min(currentIndex + 1, totalBeats) || totalBeats}/{totalBeats}
            </span>
          </div>

          <div className="w-11 h-11" />
        </div>
      </div>

      {phase === 'recording' && (
        <div className="absolute top-[calc(env(safe-area-inset-top)+4.5rem)] left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-600 shadow-lg">
          <Circle className="w-2.5 h-2.5 fill-white animate-pulse" />
          <span className="text-xs font-bold font-mono">{countdown.toFixed(1)}s</span>
        </div>
      )}

      {/* Bottom overlay: no scrim panel -- legibility comes from a strong
          drop-shadow on each text line instead of a background block. */}
      <div className="absolute bottom-0 inset-x-0 z-20" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        <div className="px-4 pt-3 pb-5 space-y-3">
          {(phase === 'ready' || phase === 'recording') && (
            <div className="flex items-center justify-center gap-2">
              {[1, 1.5, 2, 3].map((z) => (
                <button
                  key={z}
                  type="button"
                  onClick={() => setZoomLevel(z)}
                  className={`w-11 h-8 rounded-full text-xs font-bold border backdrop-blur-sm transition-all cursor-pointer ${
                    zoomLevel === z
                      ? 'bg-amber-400 text-slate-950 border-amber-400'
                      : 'bg-black/45 text-white border-white/20'
                  }`}
                >
                  {z}x
                </button>
              ))}
            </div>
          )}

          {(phase === 'ready' || phase === 'recording') && currentBeat && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-amber-500/25 text-amber-300 border border-amber-500/40">
                  {ROLE_LABELS[currentBeat.role] || currentBeat.role}
                </span>
                <span className="text-xs font-mono text-white [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">{formatSeconds(currentBeat.planned_duration)}</span>
              </div>
              <p className="text-sm text-white leading-snug [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">{currentBeat.text}</p>
              {(() => {
                const parts = (currentBeat.camera_direction || '').split('—').map((s) => s.trim());
                const cameraAngle = parts[0] || '';
                const actionText = parts.length > 1 ? parts.slice(1).join(' — ') : '';
                return (
                  <div className="space-y-1 pt-0.5">
                    {cameraAngle && (
                      <div className="p-1.5 rounded-lg bg-cyan-950/40 border border-cyan-500/30 text-cyan-200 text-xs flex items-start gap-1.5 [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">
                        <Camera className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold text-cyan-400 text-[10px] block uppercase">มุมกล้อง:</span>
                          <span>{cameraAngle}</span>
                        </div>
                      </div>
                    )}
                    <div className="p-1.5 rounded-lg bg-amber-950/40 border border-amber-500/30 text-amber-200 text-xs flex items-start gap-1.5 [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">
                      <Clapperboard className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-amber-400 text-[10px] block uppercase">แอคชั่นการถ่าย:</span>
                        <span>{actionText || currentBeat.camera_direction}</span>
                      </div>
                    </div>
                  </div>
                );
              })()}
              {voiceAudioPath && phase === 'ready' && (
                <button
                  type="button"
                  onClick={() => playGuideAudioForBeat(currentBeat)}
                  className="text-xs text-cyan-300 flex items-center gap-1.5 font-bold cursor-pointer [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]"
                >
                  <Volume2 className="w-3.5 h-3.5" /> ฟังเสียงนำช็อตนี้
                </button>
              )}
            </div>
          )}

          {phase === 'reviewing' && (
            <p className="text-center text-sm font-bold text-white [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">
              พอใจกับช็อตนี้ไหม?
            </p>
          )}

          {phase === 'sending' && !sendError && (
            <div className="text-center space-y-1 [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">
              <Loader2 className="w-7 h-7 text-[#25F4EE] mx-auto animate-spin" />
              <p className="text-sm font-bold text-white">กำลังส่งวิดีโอและรวมคลิป...</p>
            </div>
          )}

          {sendError && (
            <div className="text-center space-y-1 [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">
              <AlertCircle className="w-7 h-7 text-rose-400 mx-auto" />
              <p className="text-xs font-bold text-rose-300">{sendError}</p>
            </div>
          )}

          {isDone && (
            <div className="text-center space-y-1 [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">
              <CheckCircle2 className="w-7 h-7 text-emerald-400 mx-auto drop-shadow" />
              <p className="text-xs font-bold text-emerald-300">รวมคลิปเสร็จแล้ว วิดีโอถูกส่งเข้าโปรเจกต์แล้ว</p>
            </div>
          )}

          <div className="flex items-center justify-center gap-4 pt-1">
            {phase === 'ready' && (
              <>
                {confirmedClips.length > 0 && (
                  <button
                    type="button"
                    onClick={handleBack}
                    aria-label="ย้อนถ่ายช็อตก่อนหน้า"
                    className="w-12 h-12 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-slate-200 active:scale-90 transition-transform cursor-pointer"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleStartRecording}
                  disabled={!!cameraError || !cameraReady || !canvasReady}
                  aria-label="เริ่มอัดช็อตนี้"
                  className="relative w-20 h-20 rounded-full flex items-center justify-center shadow-2xl active:scale-90 transition-transform disabled:opacity-50 cursor-pointer ring-4 ring-white"
                >
                  <span className="w-14 h-14 rounded-full bg-rose-500" />
                </button>
              </>
            )}

            {phase === 'recording' && (
              <button
                type="button"
                onClick={stopRecorder}
                aria-label="หยุดก่อนเวลา"
                className="relative w-20 h-20 rounded-full flex items-center justify-center shadow-2xl active:scale-90 transition-transform cursor-pointer ring-4 ring-rose-500"
              >
                <span className="text-2xl font-black font-mono text-white">{Math.ceil(countdown)}</span>
              </button>
            )}

            {phase === 'reviewing' && (
              <>
                <button
                  type="button"
                  onClick={handleBack}
                  aria-label="ไม่พอใจ อัดใหม่"
                  className="w-16 h-16 rounded-full bg-white/10 border-2 border-white/30 flex items-center justify-center text-white active:scale-90 transition-transform cursor-pointer"
                >
                  <X className="w-7 h-7" />
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  aria-label="ยืนยันช็อตนี้"
                  className="w-20 h-20 rounded-full bg-emerald-500 flex items-center justify-center shadow-2xl active:scale-90 transition-transform cursor-pointer ring-4 ring-white"
                >
                  <Check className="w-9 h-9 text-white" strokeWidth={3} />
                </button>
              </>
            )}

            {sendError && (
              <button
                type="button"
                onClick={() => handleSendAll(confirmedClips)}
                className="px-5 py-3 rounded-2xl bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 text-sm font-black flex items-center justify-center gap-2 shadow-xl active:scale-95 transition-all cursor-pointer"
              >
                <RotateCw className="w-5 h-5" /> ลองส่งอีกครั้ง
              </button>
            )}

            {isDone && onExit && (
              <button
                type="button"
                onClick={handleExit}
                className="flex-1 py-4 rounded-2xl bg-gradient-to-r from-[#25F4EE] to-blue-500 text-slate-950 text-sm font-black flex items-center justify-center gap-2 shadow-xl active:scale-95 transition-all cursor-pointer"
              >
                <Home className="w-5 h-5" />
                เสร็จแล้ว กลับไปหน้าหลัก
              </button>
            )}
          </div>

          {phase === 'ready' && (
            <p className="text-center text-xs text-white font-bold [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">
              แตะเพื่อเริ่มอัดช็อตนี้ ({formatSeconds(currentBeat?.planned_duration)})
            </p>
          )}
          {phase === 'recording' && (
            <p className="text-center text-xs text-white font-bold [text-shadow:0_1px_4px_rgba(0,0,0,0.9)]">
              แตะเพื่อหยุดก่อนเวลา
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
