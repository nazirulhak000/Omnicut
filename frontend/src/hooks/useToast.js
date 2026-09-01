import { useState, useCallback } from 'react';

/**
 * useToast Hook
 * Manages toast notification state with automatic dismiss timer
 */
export function useToast(defaultDuration = 3000) {
  const [toast, setToast] = useState(null); // { message, type: 'success' | 'error' | 'warning' | 'info' } | null

  const showToast = useCallback((message, type = 'success', duration = defaultDuration) => {
    if (!message) return;
    setToast({ message, type });
  }, [defaultDuration]);

  const hideToast = useCallback(() => {
    setToast(null);
  }, []);

  return {
    toast,
    toastMessage: toast?.message || null,
    toastType: toast?.type || 'success',
    showToast,
    hideToast
  };
}

export default useToast;
