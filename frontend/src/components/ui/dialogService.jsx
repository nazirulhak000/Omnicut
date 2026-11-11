import React, { useEffect, useState } from 'react';
import { ConfirmModal } from './ConfirmModal';
import { Toast } from './Toast';

/**
 * In-app replacements for window.confirm() / window.alert().
 *
 *   if (!(await confirmDialog('ลบไฟล์นี้?', { variant: 'danger', confirmText: 'ลบ' }))) return;
 *   notify('บันทึกไม่สำเร็จ');            // error toast
 *   notify('คัดลอกแล้ว', 'success');
 *
 * <DialogHost /> (mounted once in main.jsx) renders them with the app's own
 * ConfirmModal and Toast. If no host is mounted (unit tests, a standalone
 * fixture page) the calls fall back to the browser prompts so nothing is
 * silently swallowed.
 */
let host = null;
let nextId = 0;

export function confirmDialog(message, options = {}) {
  if (!host) {
    return Promise.resolve(typeof window !== 'undefined' && window.confirm(message));
  }
  return new Promise((resolve) => {
    host.pushConfirm({ id: ++nextId, message, options, resolve });
  });
}

export function notify(message, type = 'error', duration) {
  if (!message) return;
  if (!host) {
    if (typeof window !== 'undefined') window.alert(message);
    return;
  }
  // Long messages (an AI error with detail, a share text) need reading time.
  const fallback = Math.min(12000, 3500 + String(message).length * 40);
  host.pushToast({ id: ++nextId, message: String(message), type, duration: duration ?? fallback });
}

export function DialogHost() {
  const [confirms, setConfirms] = useState([]);
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const api = {
      pushConfirm: (entry) => setConfirms((prev) => [...prev, entry]),
      pushToast: (entry) => setToasts((prev) => [...prev, entry]),
    };
    host = api;
    return () => {
      if (host === api) host = null;
    };
  }, []);

  const current = confirms[0] || null;
  const settle = (answer) => {
    if (!current) return;
    current.resolve(answer);
    setConfirms((prev) => prev.filter((entry) => entry.id !== current.id));
  };

  const toast = toasts[0] || null;
  const dismissToast = () => setToasts((prev) => prev.slice(1));

  const options = current?.options || {};
  return (
    <>
      <ConfirmModal
        key={current ? `confirm-${current.id}` : 'confirm-idle'}
        isOpen={Boolean(current)}
        onClose={() => settle(false)}
        onConfirm={() => settle(true)}
        title={options.title || 'ยืนยันการดำเนินการ'}
        description={current?.message || ''}
        dangerNote={options.dangerNote ?? null}
        confirmText={options.confirmText || 'ยืนยัน'}
        cancelText={options.cancelText || 'ยกเลิก'}
        variant={options.variant || 'warning'}
      />
      <Toast
        key={toast ? `toast-${toast.id}` : 'toast-idle'}
        message={toast?.message || ''}
        type={toast?.type || 'error'}
        duration={toast?.duration}
        onClose={dismissToast}
      />
    </>
  );
}

export default DialogHost;
