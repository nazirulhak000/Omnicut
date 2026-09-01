import { useState, useEffect, useCallback, useRef } from 'react';
import { startRender, getRenderStatus } from '../api';

/**
 * useRenderJob Hook
 * Robust background polling engine for video render tasks
 * Includes Anti-Hang fail-safe (600s max), consecutive error tolerance, and clean unmounting.
 */
export function useRenderJob({ onComplete, onError } = {}) {
  const [rendering, setRendering] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [renderResult, setRenderResult] = useState(null);
  const [renderError, setRenderError] = useState(null);

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
    setRendering(false);
    setJobId(null);
    setJobStatus(null);
    setRenderResult(null);
    setRenderError(null);
    pollCountRef.current = 0;
    consecutiveErrorsRef.current = 0;
  }, [clearPolling]);

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
          setRendering(false);
          setRenderResult(status.result);
          onComplete?.(status.result);
        } else if (status.status === 'failed') {
          clearPolling();
          setRendering(false);
          const errMsg = status.error || 'การตัดต่อล้มเหลว กรุณาตรวจสอบไฟล์วิดีโอหรือลองใหม่อีกครั้ง';
          setRenderError(errMsg);
          onError?.(errMsg);
        }
      } catch (err) {
        console.error('Render polling error:', err);
        consecutiveErrorsRef.current += 1;
        if (consecutiveErrorsRef.current >= 5) {
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
    setJobStatus({ progress: 0.05, message: 'กำลังเตรียมข้อมูลและจัดโครงสร้างสคริปต์...' });

    try {
      const res = await startRender(payload);
      if (res.job_id) {
        setJobId(res.job_id);
        return res.job_id;
      } else {
        throw new Error('ไม่พบ Job ID จากเซิร์ฟเวอร์');
      }
    } catch (err) {
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
    jobStatus,
    progressPercent,
    renderResult,
    renderError,
    executeRender,
    resetJob
  };
}

export default useRenderJob;
