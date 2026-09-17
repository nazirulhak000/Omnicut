import { useState, useCallback, useEffect, useRef } from 'react';

export const DEFAULT_TOAST_QUEUE_LIMIT = 8;

export function normalizeToastDuration(duration, fallback = 3000) {
  const parsed = Number(duration);
  if (!Number.isFinite(parsed)) {
    const fallbackValue = Number(fallback);
    return Number.isFinite(fallbackValue) ? Math.max(0, fallbackValue) : 3000;
  }
  return Math.max(0, parsed);
}

export function enqueueBoundedNotification(queue, notification, limit = DEFAULT_TOAST_QUEUE_LIMIT) {
  const safeQueue = Array.isArray(queue) ? queue : [];
  const safeLimit = Math.max(1, Math.floor(Number(limit) || DEFAULT_TOAST_QUEUE_LIMIT));
  if (!notification) return safeQueue;

  // Preserve the currently visible notification. When the queue is full,
  // discard an older pending item rather than replacing what the user is
  // currently reading.
  const preserved = safeQueue.length >= safeLimit
    ? safeQueue.slice(0, safeLimit - 1)
    : safeQueue;
  return [...preserved, notification];
}

/**
 * useToast Hook
 * Manages toast notification state with automatic dismiss timer
 */
export function useToast(defaultDuration = 3000, queueLimit = DEFAULT_TOAST_QUEUE_LIMIT) {
  const [toasts, setToasts] = useState([]);
  const nextIdRef = useRef(0);
  const toast = toasts[0] || null;

  const showToast = useCallback((message, type = 'success', duration = defaultDuration, metadata = {}) => {
    if (!message) return;
    const notification = {
      id: ++nextIdRef.current,
      message,
      type,
      duration: normalizeToastDuration(duration, defaultDuration),
      ...metadata,
    };
    setToasts(prev => enqueueBoundedNotification(prev, notification, queueLimit));
  }, [defaultDuration, queueLimit]);

  const hideToast = useCallback(() => {
    setToasts(prev => prev.slice(1));
  }, []);

  useEffect(() => {
    if (!toast || toast.duration <= 0) return undefined;
    const timer = setTimeout(hideToast, toast.duration);
    return () => clearTimeout(timer);
  }, [toast, hideToast]);

  return {
    toast,
    toastMessage: toast?.message || null,
    toastType: toast?.type || 'success',
    toastDuration: toast?.duration ?? normalizeToastDuration(defaultDuration),
    showToast,
    hideToast
  };
}

export default useToast;
