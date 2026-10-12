import { channelLocalStorage } from '../lib/channelStorage.js';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getRenderStatus, startRender } from '../api.js';

import {
  calculateJobProgress,
  clearActiveJob,
  formatJobError,
  getActiveJob,
  getActiveJobEntry,
  normalizeJobResult,
  saveActiveJob,
} from '../lib/renderJobModel.js';

/**
 * Poll a single backend render job without allowing overlapping requests.
 * Each start advances a generation, so a response belonging to an older job
 * cannot publish state or stop the timer for the newer job in the same tab.
 */
// How long a resumed job may go without answering before its stored id is
// treated as stale. A live job replies on the first poll (1s).
const RESUME_STATUS_TIMEOUT_MS = 8000;

export function createRenderJobPollController({
  fetchStatus,
  isActive = () => true,
  onResponse,
  onError,
  intervalMs = 1000,
  maxErrors = 5,
  setTimeoutFn = setTimeout,
  clearTimeoutFn = clearTimeout,
} = {}) {
  let generation = 0;
  let timer = null;
  let errorCount = 0;

  const stop = () => {
    generation += 1;
    if (timer !== null) {
      clearTimeoutFn(timer);
      timer = null;
    }
  };

  const start = (id, targetProject) => {
    stop();
    if (!id || !targetProject || typeof fetchStatus !== 'function') return;

    const currentGeneration = generation;
    const isCurrent = () => generation === currentGeneration && isActive(targetProject);
    errorCount = 0;

    const checkOnce = async () => {
      timer = null;
      if (!isCurrent()) return;

      let status;
      try {
        status = await fetchStatus(id);
        errorCount = 0;
      } catch (err) {
        if (!isCurrent()) return;
        errorCount += 1;
        const is404 = err?.response?.status === 404;
        const is401 = err?.response?.status === 401;
        if (is404 || is401 || errorCount >= maxErrors) {
          onError?.(err, id, targetProject);
          return;
        }
        if (isCurrent()) timer = setTimeoutFn(checkOnce, intervalMs);
        return;
      }

      if (!isCurrent()) return;
      onResponse?.(status, id, targetProject);
      const { isDone, isFailed, isCancelled } = calculateJobProgress(status);
      if (!isDone && !isFailed && !isCancelled && isCurrent()) {
        timer = setTimeoutFn(checkOnce, intervalMs);
      }
    };

    // Start immediately, then schedule only after the previous request has
    // settled. This prevents setInterval from creating overlapping requests.
    checkOnce();
  };

  return { start, stop };
}

/**
 * Hook for managing render jobs, status polling, unmount cleanup,
 * and project-scoped race condition protection.
 * Supports both manual startJob (EditorShell) and full payload executeRender (NewClipPanel).
 */
export function useRenderJob({
  projectName,
  fetchStatus = getRenderStatus,
  onComplete,
  onError,
  pollIntervalMs = 1000,
} = {}) {
  const [workspaceStorage] = useState(channelLocalStorage);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobProjectName, setJobProjectName] = useState(projectName || '');
  const [isRendering, setIsRendering] = useState(false);
  const [applyResult, setApplyResult] = useState(null);
  const [applyError, setApplyError] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [displayPercent, setDisplayPercent] = useState(0);

  const activeProjectRef = useRef(projectName);
  const isMountedRef = useRef(true);
  const callbacksRef = useRef({ onComplete, onError, fetchStatus });
  const pollControllerRef = useRef(null);
  callbacksRef.current = { onComplete, onError, fetchStatus };

  const clearTimer = useCallback(() => {
    pollControllerRef.current?.stop();
  }, []);

  if (!pollControllerRef.current) {
    pollControllerRef.current = createRenderJobPollController({
      fetchStatus: (id) => (callbacksRef.current.fetchStatus || getRenderStatus)(id),
      isActive: (targetProject) => (
        isMountedRef.current && activeProjectRef.current === targetProject
      ),
      onResponse: (st, id, targetProject) => {
        setJobStatus(st);
        const { isDone, isFailed, isCancelled } = calculateJobProgress(st);

        if (isDone) {
          clearTimer();
          setIsRendering(false);
          setJobStatus(null);
          setStartTime(null);
          setDisplayPercent(100);
          clearActiveJob(targetProject, workspaceStorage);
          const rawResult = st.result || {};
          const normalized = normalizeJobResult(rawResult);
          setApplyResult(rawResult);
          callbacksRef.current.onComplete?.(rawResult, id, targetProject, normalized);
        } else if (isCancelled) {
          clearTimer();
          setIsRendering(false);
          setJobStatus(null);
          setStartTime(null);
          clearActiveJob(targetProject, workspaceStorage);
        } else if (isFailed) {
          clearTimer();
          setIsRendering(false);
          setJobStatus(null);
          setStartTime(null);
          clearActiveJob(targetProject, workspaceStorage);
          const errorMsg = formatJobError(st.error || 'เกิดข้อผิดพลาดในการเรนเดอร์');
          setApplyError(errorMsg);
          callbacksRef.current.onError?.(errorMsg, id, targetProject);
        }
      },
      onError: (err, id, targetProject) => {
        clearTimer();
        setIsRendering(false);
        setJobStatus(null);
        setStartTime(null);
        clearActiveJob(targetProject, workspaceStorage);
        if (err?.response?.status === 404) {
          const errorMsg = 'ไม่พบงานเรนเดอร์นี้แล้ว (อาจถูกล้างหรือเซิร์ฟเวอร์รีสตาร์ท) กรุณาเรนเดอร์ใหม่';
          setApplyError(errorMsg);
          callbacksRef.current.onError?.(errorMsg, id, targetProject);
        } else if (err?.response?.status === 401) {
          const errorMsg = 'ไม่ได้รับอนุญาตให้เข้าถึง API (Unauthorized / Invalid API Key)';
          setApplyError(errorMsg);
          callbacksRef.current.onError?.(errorMsg, id, targetProject);
        }
      },
      intervalMs: pollIntervalMs,
    });
  }

  const stopJob = useCallback(() => {
    clearTimer();
    setIsRendering(false);
    setStartTime(null);
  }, [clearTimer]);

  const resetJob = useCallback(() => {
    clearTimer();
    setIsRendering(false);
    setJobId(null);
    setJobStatus(null);
    setApplyResult(null);
    setApplyError(null);
    setStartTime(null);
    setElapsedSeconds(0);
    setDisplayPercent(0);
  }, [clearTimer]);

  const clearResult = useCallback(() => setApplyResult(null), []);
  const clearError = useCallback(() => setApplyError(null), []);

  const pollJob = useCallback((id, targetProject) => {
    pollControllerRef.current?.start(id, targetProject);
  }, []);

  const startJob = useCallback((newJobId, initialStatus = null) => {
    if (!newJobId) return;
    const currentProject = activeProjectRef.current;
    setJobId(newJobId);
    setIsRendering(true);
    setStartTime((prev) => prev || Date.now());
    setApplyError(null);
    setApplyResult(null);

    if (initialStatus) {
      setJobStatus(initialStatus);
    } else {
      setJobStatus({ progress: 0.05, message: 'กำลังเตรียมข้อมูล...' });
    }

    if (currentProject) {
      saveActiveJob(currentProject, newJobId, workspaceStorage);
    }

    pollJob(newJobId, currentProject);
  }, [pollJob]);

  const executeRender = useCallback(async (payload) => {
    resetJob();
    const projName = payload?.project_name || payload?.product_name || 'วิดีโอ';
    setJobProjectName(projName);
    activeProjectRef.current = projName;
    const now = Date.now();
    setStartTime(now);
    setElapsedSeconds(0);
    setDisplayPercent(5);
    setIsRendering(true);
    setApplyError(null);
    setApplyResult(null);
    const initialStatus = { progress: 0.05, message: 'กำลังเตรียมข้อมูลและจัดโครงสร้างสคริปต์...' };
    setJobStatus(initialStatus);

    try {
      const res = await startRender(payload);
      if (res?.job_id) {
        startJob(res.job_id, initialStatus);
        return res.job_id;
      } else {
        throw new Error('ไม่พบ Job ID จากเซิร์ฟเวอร์');
      }
    } catch (err) {
      stopJob();
      const errMsg = err?.friendlyMessage || err?.response?.data?.detail || err?.message || 'เกิดข้อผิดพลาดในการสั่งเรนเดอร์';
      setApplyError(errMsg);
      callbacksRef.current.onError?.(errMsg);
      throw err;
    }
  }, [resetJob, startJob, stopJob]);

  // Handle project switching and resume active jobs
  useEffect(() => {
    activeProjectRef.current = projectName;
    clearTimer();
    setIsRendering(false);
    setJobStatus(null);
    setStartTime(null);
    setElapsedSeconds(0);
    setDisplayPercent(0);
    if (projectName) {
      setJobProjectName(projectName);
    }

    if (!projectName) {
      setJobId(null);
      return undefined;
    }

    // Check if there is an active background render job for this tab and project.
    const jobEntry = getActiveJobEntry(workspaceStorage);
    const storedJobId = jobEntry?.jobId;
    const isForCurrentProject = Boolean(
      storedJobId && (!jobEntry.projectKey || !projectName || jobEntry.projectKey === projectName)
    );

    if (isForCurrentProject) {
      // activeProjectRef drives the poller's isActive() check. On a fresh
      // mount it can still hold the previous project, in which case the poll
      // silently never starts while the UI already shows "rendering" at the
      // 10% placeholder -- a permanent phantom progress bar. Set it before
      // starting so the first poll is always accepted.
      activeProjectRef.current = projectName;
      setJobId(storedJobId);
      setIsRendering(true);
      setStartTime(Date.now());
      setJobStatus({ progress: 0.1, message: 'กำลังตรวจสอบสถานะการเรนเดอร์...' });
      pollJob(storedJobId, projectName);

      // A resumed job that never answers must not hang the UI forever: if no
      // status has arrived by the time this fires, drop the stale entry and
      // let the user render again. A live job answers within a second.
      const staleGuard = setTimeout(() => {
        if (!isMountedRef.current) return;
        setJobStatus((current) => {
          const unanswered = !current || current.progress === 0.1;
          if (!unanswered) return current;
          clearActiveJob(projectName, workspaceStorage);
          setIsRendering(false);
          setJobId(null);
          setStartTime(null);
          setApplyError('ไม่พบงานเรนเดอร์ที่ค้างอยู่ (เซิร์ฟเวอร์อาจรีสตาร์ท) กรุณาเรนเดอร์ใหม่');
          return null;
        });
      }, RESUME_STATUS_TIMEOUT_MS);

      return () => {
        clearTimeout(staleGuard);
        clearTimer();
      };
    } else {
      setJobId(null);
      setIsRendering(false);
      setJobStatus(null);
    }

    return () => {
      clearTimer();
    };
  }, [clearTimer, pollJob, projectName]);

  // Real-time 1-second elapsed timer
  useEffect(() => {
    if (!isRendering || !startTime) {
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
  }, [isRendering, startTime]);

  // Smooth micro-progress ticker ensuring line and percentage always visibly advance
  useEffect(() => {
    if (!isRendering) {
      if (!applyResult) setDisplayPercent(0);
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
        const cap = targetPct < 70 ? targetPct + 4 : (targetPct < 85 ? targetPct + 3 : Math.min(98, targetPct + 2));
        if (curr < cap && Math.random() < 0.35) {
          return curr + 1;
        }
        return curr;
      });
    }, 350);

    return () => clearInterval(ticker);
  }, [isRendering, jobStatus?.progress, applyResult]);

  // Smart ETA estimation based on progress & elapsed time
  const estimatedRemainingSeconds = useMemo(() => {
    if (!isRendering || elapsedSeconds < 3 || displayPercent < 8) {
      return 110; // Baseline ~1.5 - 2 minutes
    }
    if (displayPercent >= 98) return 5;
    const progressFraction = Math.max(0.08, displayPercent / 100);
    const totalEst = elapsedSeconds / progressFraction;
    const remaining = Math.max(5, Math.round(totalEst - elapsedSeconds));
    return Math.min(240, remaining);
  }, [isRendering, elapsedSeconds, displayPercent]);

  // Component lifecycle: set isMounted and cleanup timers
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearTimer();
    };
  }, [clearTimer]);

  const progress = calculateJobProgress(jobStatus);

  return {
    jobId,
    jobStatus,
    isRendering,
    rendering: isRendering,
    jobProjectName,
    setJobProjectName,
    applyResult,
    renderResult: applyResult,
    setApplyResult,
    applyError,
    renderError: applyError,
    setApplyError,
    progressPercent: progress.percent,
    progressMessage: progress.message,
    displayPercent,
    elapsedSeconds,
    estimatedRemainingSeconds,
    startJob,
    stopJob,
    executeRender,
    resetJob,
    clearResult,
    clearError,
  };
}

export default useRenderJob;
