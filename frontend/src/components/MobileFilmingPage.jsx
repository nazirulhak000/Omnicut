import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Home, Camera, Circle, Square, RotateCcw, CheckCircle2, Loader2,
  AlertCircle, Volume2, Clapperboard, ArrowRight,
} from 'lucide-react';
import {
  getRecordingSession, getShotList, uploadRecordingSegment,
  deleteRecordingSegment, finalizeRecordingSession, getTaskStatus,
} from '../api';
import { toMediaUrl } from '../lib/mediaUrl';

const ROLE_LABELS = { hook: 'Hook', feature: 'Feature', cta: 'CTA' };

// Tries mimeTypes roughly in quality order; whatever the phone's browser
// actually supports is normalized to a consistent codec server-side anyway
// (scripts/recording_sessions.py's _normalize_segment), so this only needs
// to find SOMETHING MediaRecorder will accept, not the "best" one.
function pickSupportedMimeType() {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
    'video/mp4',
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

// Mobile companion page for the guided-take filming feature: opened via a
// QR code scanned from ShotListModal.jsx. Records one segment per script
// beat (tap to start/stop), uploads each immediately, and only allows
// retaking the most-recently-recorded segment (server-enforced in
// scripts/recording_sessions.py -- this page's own restriction is just the
// matching UX). See C:\Users\Winon\.claude\plans\cheeky-cooking-quokka.md
// (Phase C).
export default function MobileFilmingPage({ sessionId, onExit }) {
  const [session, setSession] = useState(null);
  const [shotList, setShotList] = useState([]);
  const [voiceAudioPath, setVoiceAudioPath] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [cameraError, setCameraError] = useState(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [retaking, setRetaking] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeError, setFinalizeError] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const videoPreviewRef = useRef(null);
  const guideAudioRef = useRef(null);
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

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

  // Camera: acquired once and kept alive across every beat's recording, not
  // re-requested per segment -- re-prompting permission every beat would be
  // both slow and jarring on a phone.
  useEffect(() => {
    let cancelled = false;
    async function start() {
      try {
        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: 1080, height: 1920 },
            audio: false,
          });
        } catch {
          // Some browsers are unreliable with a video-only MediaRecorder
          // session -- fall back to capturing audio too. It's discarded
          // anyway: guided-take segments are always rendered with their
          // own audio muted (the real narration is the separate TTS
          // track), so this fallback costs nothing but a mic permission
          // prompt.
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: 1080, height: 1920 },
            audio: true,
          });
        }
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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070A12] text-white flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#25F4EE]" />
      </div>
    );
  }

  if (loadError || !session) {
    return (
      <div className="min-h-screen bg-[#070A12] text-white flex flex-col items-center justify-center gap-3 p-6 text-center">
        <AlertCircle className="w-8 h-8 text-rose-400" />
        <p className="text-sm text-slate-300">{loadError || 'ไม่พบเซสชันถ่ายทำ'}</p>
        {onExit && (
          <button onClick={onExit} className="mt-2 py-2 px-4 rounded-xl bg-white/[0.08] text-xs font-bold flex items-center gap-1.5">
            <Home className="w-3.5 h-3.5" /> หน้าหลัก
          </button>
        )}
      </div>
    );
  }

  const segments = session.segments || [];
  const currentIndex = segments.findIndex((s) => s.status !== 'uploaded');
  const isComplete = currentIndex === -1;
  const currentSegment = !isComplete ? segments[currentIndex] : null;
  const currentBeat = currentSegment ? shotList.find((b) => b.beat_index === currentSegment.beat_index) : null;
  const lastUploadedIndex = segments.reduce((acc, s, i) => (s.status === 'uploaded' ? i : acc), -1);

  const playGuideAudioForBeat = (beat) => {
    const audio = guideAudioRef.current;
    if (!audio || !beat) return;
    audio.currentTime = beat.start || 0;
    audio.play().catch(() => {});
    const onTick = () => {
      if (audio.currentTime >= (beat.end || Infinity)) {
        audio.pause();
        audio.removeEventListener('timeupdate', onTick);
      }
    };
    audio.addEventListener('timeupdate', onTick);
  };

  const handleStartRecording = () => {
    const stream = streamRef.current;
    if (!stream || !currentSegment) return;
    const mimeType = pickSupportedMimeType();
    try {
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => handleSegmentRecorded(mimeType || 'video/webm');
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
      if (voiceAudioPath && currentBeat) playGuideAudioForBeat(currentBeat);
    } catch (err) {
      showToast('เริ่มอัดไม่สำเร็จ: ' + err.message);
    }
  };

  const handleStopRecording = () => {
    guideAudioRef.current?.pause();
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const handleSegmentRecorded = async (mimeType) => {
    if (!currentSegment) return;
    const blob = new Blob(chunksRef.current, { type: mimeType });
    chunksRef.current = [];
    const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
    setUploading(true);
    try {
      await uploadRecordingSegment(sessionId, currentSegment.beat_index, blob, `seg_${currentSegment.beat_index}.${ext}`);
      await loadSession();
      showToast(`บันทึกช็อตที่ ${currentSegment.beat_index + 1} แล้ว`);
    } catch (err) {
      showToast('อัปโหลดไม่สำเร็จ: ' + (err.friendlyMessage || err.message));
    } finally {
      setUploading(false);
    }
  };

  const handleRetakeLast = async () => {
    if (lastUploadedIndex < 0) return;
    setRetaking(true);
    try {
      await deleteRecordingSegment(sessionId, lastUploadedIndex);
      await loadSession();
    } catch (err) {
      showToast('ย้อนถ่ายไม่สำเร็จ: ' + (err.friendlyMessage || err.message));
    } finally {
      setRetaking(false);
    }
  };

  const handleFinalize = async () => {
    setFinalizing(true);
    setFinalizeError(null);
    try {
      const res = await finalizeRecordingSession(sessionId);
      for (let attempt = 0; attempt < 60; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        const task = await getTaskStatus(res.task_id);
        if (task.status === 'completed') {
          await loadSession();
          return;
        }
        if (task.status === 'failed') {
          setFinalizeError(task.error || 'รวมคลิปไม่สำเร็จ');
          return;
        }
      }
      setFinalizeError('รวมคลิปใช้เวลานานเกินไป กรุณาลองใหม่');
    } catch (err) {
      setFinalizeError(err.friendlyMessage || err.message || 'รวมคลิปไม่สำเร็จ');
    } finally {
      setFinalizing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070A12] text-white flex flex-col max-w-lg mx-auto p-4 sm:p-6 font-prompt">
      {toastMessage && (
        <div className="fixed top-4 left-4 right-4 z-50 p-3.5 rounded-2xl bg-[#25F4EE] text-slate-950 font-bold text-xs text-center shadow-2xl border border-white/20">
          {toastMessage}
        </div>
      )}

      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-amber-400 to-[#25F4EE] flex items-center justify-center text-slate-950 shadow-md">
            <Clapperboard className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-xs font-black uppercase tracking-wider text-amber-300 font-mono">Guided Filming</h1>
            <p className="text-[11px] text-slate-400">
              ช็อตที่ {Math.min(currentIndex + 1, segments.length) || segments.length}/{segments.length}
            </p>
          </div>
        </div>
        {onExit && (
          <button onClick={onExit} className="py-1.5 px-3 rounded-xl bg-white/[0.06] border border-white/[0.08] text-xs font-bold text-slate-300 flex items-center gap-1">
            <Home className="w-3.5 h-3.5" /> หน้าหลัก
          </button>
        )}
      </div>

      <div className="flex-1 py-4 space-y-4">
        <div className="rounded-2xl overflow-hidden bg-black border border-white/[0.1] shadow-2xl relative aspect-[9/16] max-h-[45vh] mx-auto">
          <video ref={videoPreviewRef} autoPlay playsInline muted className="w-full h-full object-cover" />
          {cameraError && (
            <div className="absolute inset-0 flex items-center justify-center p-4 bg-black/80 text-center text-xs text-rose-300">
              <div className="flex flex-col items-center gap-2">
                <Camera className="w-6 h-6" />
                {cameraError}
              </div>
            </div>
          )}
          {isRecording && (
            <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 rounded-full bg-rose-600/90 text-[10px] font-bold">
              <Circle className="w-2 h-2 fill-white animate-pulse" /> REC
            </div>
          )}
        </div>

        <audio ref={guideAudioRef} src={voiceAudioPath ? toMediaUrl(voiceAudioPath) : undefined} className="hidden" />

        {!isComplete && currentBeat && (
          <div className="p-3.5 rounded-2xl bg-[#0B0F19] border border-white/[0.08] space-y-1.5 shadow-lg">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                {ROLE_LABELS[currentBeat.role] || currentBeat.role}
              </span>
              <span className="text-[11px] font-mono text-slate-400">{formatSeconds(currentBeat.planned_duration)}</span>
            </div>
            <p className="text-xs text-slate-300 font-kanit leading-snug">{currentBeat.text}</p>
            <p className="text-xs text-amber-200/90 flex items-start gap-1.5">
              <Clapperboard className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>{currentBeat.camera_direction}</span>
            </p>
            {voiceAudioPath && (
              <button
                type="button"
                onClick={() => playGuideAudioForBeat(currentBeat)}
                className="text-[11px] text-cyan-300 flex items-center gap-1 font-bold"
              >
                <Volume2 className="w-3.5 h-3.5" /> ฟังเสียงนำช็อตนี้
              </button>
            )}
          </div>
        )}

        {isComplete && (
          <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/25 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
            <p className="text-sm font-bold text-emerald-300">ถ่ายครบทุกช็อตแล้ว!</p>
            <p className="text-xs text-slate-400">กด "รวมคลิป" เพื่อรวมเป็นวิดีโอเดียวและส่งเข้าโปรเจกต์</p>
          </div>
        )}

        {finalizeError && (
          <p className="text-xs text-rose-400 text-center">{finalizeError}</p>
        )}

        {session.status === 'completed' && (
          <div className="p-4 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-center space-y-1">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
            <p className="text-xs font-bold text-emerald-300">รวมคลิปเสร็จแล้ว วิดีโอถูกส่งเข้าโปรเจกต์แล้ว</p>
          </div>
        )}
      </div>

      <div className="space-y-2 pb-2">
        {!isComplete && (
          <button
            type="button"
            onClick={isRecording ? handleStopRecording : handleStartRecording}
            disabled={uploading || !!cameraError || !cameraReady}
            className={`w-full py-4 rounded-2xl text-sm font-black flex items-center justify-center gap-2 shadow-xl active:scale-95 transition-all disabled:opacity-50 ${
              isRecording ? 'bg-rose-600 text-white' : 'bg-gradient-to-r from-amber-400 to-[#25F4EE] text-slate-950'
            }`}
          >
            {uploading ? (
              <><Loader2 className="w-5 h-5 animate-spin" /> กำลังอัปโหลด...</>
            ) : isRecording ? (
              <><Square className="w-5 h-5" /> หยุด & บันทึกช็อตนี้</>
            ) : (
              <><Circle className="w-5 h-5" /> เริ่มอัดช็อตนี้</>
            )}
          </button>
        )}

        {lastUploadedIndex >= 0 && !isRecording && session.status !== 'completed' && (
          <button
            type="button"
            onClick={handleRetakeLast}
            disabled={retaking || uploading}
            className="w-full py-2.5 rounded-xl bg-white/[0.06] border border-white/[0.08] text-xs font-bold text-slate-300 flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            {retaking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
            ย้อนถ่ายช็อตล่าสุดใหม่
          </button>
        )}

        {isComplete && session.status !== 'completed' && (
          <button
            type="button"
            onClick={handleFinalize}
            disabled={finalizing}
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white text-sm font-black flex items-center justify-center gap-2 shadow-xl active:scale-95 transition-all disabled:opacity-50"
          >
            {finalizing ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
            รวมคลิปและส่งเข้าโปรเจกต์
          </button>
        )}
      </div>
    </div>
  );
}
