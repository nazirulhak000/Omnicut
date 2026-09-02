import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { startRender, getRenderStatus } from '../api';

export const ACTIVE_RENDER_STORAGE_KEY = 'capcut_active_render_job';

const getInitialRenderJob = () => {
  try {
    const saved = localStorage.getItem(ACTIVE_RENDER_STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      // Valid for up to 15 minutes (900,000 ms)
      if (parsed?.jobId && Date.now() - (parsed.startedAt || 0) < 900000) {
        return parsed;
      }
    }
  } catch (e) {}
  return null;
};

/**
 * useRenderJob Hook
 * Robust background polling engine for video render tasks
 * - Persists active job to localStorage to survive page refreshes and tab changes
 * - Real-time elapsed time counter and dynamic ETA calculation
 * - Smooth micro-progress interpolation so the bar is always alive and moving
 * - Includes Anti-Hang fail-safe (600s max), consecutive error tolerance, and clean unmounting
 */
export function useRenderJob({ onComplete, onError } = {}) {
  const initialJob = getInitialRenderJob();

  const [rendering, setRendering] = useState(!!initialJob?.jobId);
  const [jobId, setJobId] = useState(initialJob?.jobId || null);
  const [jobProjectName, setJobProjectName] = useState(initialJob?.projectName || '');
  const [jobStatus, setJobStatus] = useState(
    initialJob ? { progress: 0.1, message: 'กำลังเชื่อมต่อกับงานเรนเดอร์...' } : null
  );
  const [renderResult, setRenderResult] = useState(null);
  const [renderError, setRenderError] = useState(null);

  const [startTime, setStartTime] = useState(() => initialJob?.startedAt || (initialJob?.jobId ? Date.now() : null));
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [displayPercent, setDisplayPercent] = useState(() => Math.round((initialJob ? 0.1 : 0) * 100));

  const pollCountRef = useRef(0);
  const consecutiveErrorsRef = useRef(0);
  const timerRef = useRef(null);

  const clearPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const resetJob = useCallback(() => {
    clearPolling();
    try {
      localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
    } catch (e) {}
    setRendering(false);
    setJobId(null);
    setJobProjectName('');
    setJobStatus(null);
    setRenderResult(null);
    setRenderError(null);
    setStartTime(null);
    setElapsedSeconds(0);
    setDisplayPercent(0);
    pollCountRef.current = 0;
    consecutiveErrorsRef.current = 0;
  }, [clearPolling]);

  // Real-time 1-second elapsed timer
  useEffect(() => {
    if (!rendering || !startTime) {
      setElapsedSeconds(0);
      return;
    }
    const updateElapsed = () => {
      const elapsed = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
      setElapsedSeconds(elapsed);
    };
    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    return () => clearInterval(interval);
  }, [rendering, startTime]);

  // Smooth micro-progress ticker ensuring line and percentage always visibly advance
  useEffect(() => {
    if (!rendering) {
      if (!renderResult) setDisplayPercent(0);
      return;
    }

    const targetPct = Math.round((jobStatus?.progress || 0.05) * 100);

    const ticker = setInterval(() => {
      setDisplayPercent((curr) => {
        if (curr < targetPct) {
          const step = Math.max(1, Math.ceil((targetPct - curr) / 3));
          return Math.min(targetPct, curr + step);
        }
        // Micro-trickle while waiting for long stages:
        // Cap so we never cross into future stages prematurely
        const cap = targetPct < 70 ? targetPct + 4 : (targetPct < 85 ? targetPct + 3 : Math.min(98, targetPct + 2));
        if (curr < cap && Math.random() < 0.35) {
          return curr + 1;
        }
        return curr;
      });
    }, 350);

    return () => clearInterval(ticker);
  }, [rendering, jobStatus?.progress, renderResult]);

  // Smart ETA estimation based on progress & elapsed time
  const estimatedRemainingSeconds = useMemo(() => {
    if (!rendering || elapsedSeconds < 3 || displayPercent < 8) {
      return 110; // Baseline ~1.5 - 2 minutes
    }
    if (displayPercent >= 98) return 5;
    const progressFraction = Math.max(0.08, displayPercent / 100);
    const totalEst = elapsedSeconds / progressFraction;
    const remaining = Math.max(5, Math.round(totalEst - elapsedSeconds));
    return Math.min(240, remaining);
  }, [rendering, elapsedSeconds, displayPercent]);

  // Initial immediate status check on mount if restored from localStorage
  useEffect(() => {
    if (initialJob?.jobId && !renderResult && !renderError) {
      getRenderStatus(initialJob.jobId)
        .then((status) => {
          setJobStatus(status);
          if (status.status === 'completed') {
            try {
              localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
            } catch (e) {}
            setRendering(false);
            setRenderResult(status.result);
            onComplete?.(status.result);
          } else if (status.status === 'failed') {
            try {
              localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
            } catch (e) {}
            setRendering(false);
            setRenderError(status.error || 'การตัดต่อล้มเหลว');
            onError?.(status.error);
          }
        })
        .catch((err) => {
          if (err.response?.status === 404) {
            // Job already cleaned up on server
            try {
              localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
            } catch (e) {}
            setRendering(false);
            setJobId(null);
          }
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Polling loop effect
  useEffect(() => {
    if (!jobId || !rendering) {
      clearPolling();
      return;
    }

    pollCountRef.current = 0;
    consecutiveErrorsRef.current = 0;

    timerRef.current = setInterval(async () => {
      pollCountRef.current += 1;

      // Fail-safe: 10 minutes maximum (600 seconds)
      if (pollCountRef.current > 600) {
        clearPolling();
        try {
          localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
        } catch (e) {}
        setRendering(false);
        const errMsg = 'กระบวนการตัดต่อใช้เวลานานเกิน 10 นาที ระบบได้ยกเลิกการรออัตโนมัติ กรุณาตรวจสอบคลิปต้นฉบับ';
        setRenderError(errMsg);
        onError?.(errMsg);
        return;
      }

      try {
        const status = await getRenderStatus(jobId);
        consecutiveErrorsRef.current = 0;
        setJobStatus(status);

        if (status.status === 'completed') {
          clearPolling();
          try {
            localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
          } catch (e) {}
          setRendering(false);
          setRenderResult(status.result);
          onComplete?.(status.result);
        } else if (status.status === 'failed') {
          clearPolling();
          try {
            localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
          } catch (e) {}
          setRendering(false);
          const errMsg = status.error || 'การตัดต่อล้มเหลว กรุณาตรวจสอบไฟล์วิดีโอหรือลองใหม่อีกครั้ง';
          setRenderError(errMsg);
          onError?.(errMsg);
        }
      } catch (err) {
        if (err.response?.status === 404) {
          clearPolling();
          try {
            localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
          } catch (e) {}
          setRendering(false);
          setJobId(null);
          return;
        }

        console.error('Render polling error:', err);
        consecutiveErrorsRef.current += 1;
        if (consecutiveErrorsRef.current >= 8) {
          clearPolling();
          setRendering(false);
          const errMsg = 'สูญเสียการเชื่อมต่อกับเซิร์ฟเวอร์ระหว่างติดตามสถานะการตัดต่อ กรุณาตรวจสอบสถานะเซิร์ฟเวอร์';
          setRenderError(errMsg);
          onError?.(errMsg);
        }
      }
    }, 1000);

    return () => clearPolling();
  }, [jobId, rendering, clearPolling, onComplete, onError]);

  const executeRender = useCallback(async (payload) => {
    resetJob();
    setRendering(true);
    const now = Date.now();
    setStartTime(now);
    setElapsedSeconds(0);
    setDisplayPercent(5);
    const projName = payload.project_name || payload.product_name || 'วิดีโอ';
    setJobProjectName(projName);
    setJobStatus({ progress: 0.05, message: 'กำลังเตรียมข้อมูลและจัดโครงสร้างสคริปต์...' });

    try {
      const res = await startRender(payload);
      if (res.job_id) {
        try {
          localStorage.setItem(
            ACTIVE_RENDER_STORAGE_KEY,
            JSON.stringify({
              jobId: res.job_id,
              projectName: projName,
              startedAt: now
            })
          );
        } catch (e) {}
        setJobId(res.job_id);
        return res.job_id;
      } else {
        throw new Error('ไม่พบ Job ID จากเซิร์ฟเวอร์');
      }
    } catch (err) {
      try {
        localStorage.removeItem(ACTIVE_RENDER_STORAGE_KEY);
      } catch (e) {}
      setRendering(false);
      const errMsg = err.friendlyMessage || err.response?.data?.detail || err.message || 'เกิดข้อผิดพลาดในการสั่งเรนเดอร์';
      setRenderError(errMsg);
      onError?.(errMsg);
      throw err;
    }
  }, [resetJob, onError]);

  const progressPercent = Math.round((jobStatus?.progress || 0) * 100);

  return {
    rendering,
    jobId,
    jobProjectName,
    jobStatus,
    progressPercent,
    displayPercent,
    elapsedSeconds,
    estimatedRemainingSeconds,
    renderResult,
    renderError,
    executeRender,
    resetJob
  };
}

export default useRenderJob;
