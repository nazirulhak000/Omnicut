// Dev-only fixture for the shared overlay primitives (ui/ModalLayer, ui/Modal,
// ui/dialogService, ui/Toast, ui/PopoverPanel). Open /overlay_primitives.html
// on the Vite dev server; tools/ and browser checks drive it by data-testid.
// It talks to no API and stores nothing.
import React, { StrictMode, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { Modal } from './components/ui/Modal.jsx';
import { ModalLayer } from './components/ui/ModalLayer.jsx';
import { PopoverPanel } from './components/ui/PopoverPanel.jsx';
import { DialogHost, confirmDialog, notify } from './components/ui/dialogService.jsx';

function Dropdown({ testid, align = 'end', wrapClassName = '' }) {
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState('');
  const buttonRef = useRef(null);
  return (
    <div className={`relative inline-block ${wrapClassName}`}>
      <button
        ref={buttonRef}
        type="button"
        data-testid={`${testid}-trigger`}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm"
      >
        เปิดเมนู {picked}
      </button>
      {open && (
        <PopoverPanel
          anchorRef={buttonRef}
          onClose={() => setOpen(false)}
          align={align}
          data-testid={`${testid}-panel`}
          className="w-56 space-y-1 rounded-xl border border-white/10 bg-[#0F1420] p-1.5 shadow-2xl"
        >
          {['หนึ่ง', 'สอง', 'สาม'].map((label) => (
            <button
              key={label}
              type="button"
              data-testid={`${testid}-item-${label}`}
              onClick={() => { setPicked(label); setOpen(false); }}
              className="block h-9 w-full rounded-lg px-2.5 text-left text-sm hover:bg-white/10"
            >
              รายการ{label}
            </button>
          ))}
        </PopoverPanel>
      )}
    </div>
  );
}

function Fixture() {
  const [modalOpen, setModalOpen] = useState(false);
  const [lockedOpen, setLockedOpen] = useState(false);
  const [guardedOpen, setGuardedOpen] = useState(false);
  const [guardHits, setGuardHits] = useState(0);
  const [confirmResult, setConfirmResult] = useState('-');
  const [pageClicks, setPageClicks] = useState(0);

  const askConfirm = async () => {
    const ok = await confirmDialog('ลบรายการทดสอบนี้?\nบรรทัดที่สอง', { variant: 'danger', confirmText: 'ลบ' });
    setConfirmResult(ok ? 'yes' : 'no');
  };

  return (
    <div className="min-h-[220vh] p-6 font-prompt">
      <h1 className="text-lg font-bold">Overlay primitives</h1>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="button" data-testid="open-modal" onClick={() => setModalOpen(true)} className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-bold text-black">เปิด Modal</button>
        <button type="button" data-testid="open-locked" onClick={() => setLockedOpen(true)} className="rounded-lg bg-white/10 px-3 py-2 text-sm">เปิด layer ที่ Escape ปิดไม่ได้</button>
        <button type="button" data-testid="open-guarded" onClick={() => { setGuardHits(0); setGuardedOpen(true); }} className="rounded-lg bg-white/10 px-3 py-2 text-sm">เปิด layer ที่ต้องยืนยันก่อนปิด</button>
        <button type="button" data-testid="page-confirm" onClick={askConfirm} className="rounded-lg bg-white/10 px-3 py-2 text-sm">ถามยืนยัน</button>
        <button type="button" data-testid="page-toast" onClick={() => notify('แจ้งเตือนทดสอบ', 'success')} className="rounded-lg bg-white/10 px-3 py-2 text-sm">แสดง toast</button>
        <button type="button" data-testid="page-counter" onClick={() => setPageClicks((n) => n + 1)} className="rounded-lg bg-white/10 px-3 py-2 text-sm">นับคลิกหน้าเพจ</button>
        <button type="button" data-testid="bare-outline" className="rounded-lg bg-white/10 px-3 py-2 text-sm outline-none">ปุ่ม outline-none</button>
        <Dropdown testid="dd-end" align="end" />
        <Dropdown testid="dd-start" align="start" />
      </div>
      <p className="mt-3 text-sm">
        confirm: <span data-testid="confirm-result">{confirmResult}</span> · page clicks: <span data-testid="page-clicks">{pageClicks}</span> · guard hits: <span data-testid="guard-hits">{guardHits}</span>
      </p>

      <div className="fixed bottom-4 right-4">
        <Dropdown testid="dd-bottom" align="end" />
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Modal ทดสอบ" subtitle="native dialog">
        <input data-testid="modal-input" autoFocus placeholder="ช่องแรก" className="w-full rounded-lg border border-white/20 bg-black/40 px-3 py-2 text-sm" />
        <div className="flex flex-wrap gap-2">
          <button type="button" data-testid="modal-confirm" onClick={askConfirm} className="rounded-lg bg-rose-600 px-3 py-2 text-sm">ถามยืนยันซ้อน</button>
          <button type="button" data-testid="modal-toast" onClick={() => notify('toast จากใน modal')} className="rounded-lg bg-white/10 px-3 py-2 text-sm">toast ใน modal</button>
          <button type="button" data-testid="modal-last" className="rounded-lg bg-white/10 px-3 py-2 text-sm">ปุ่มสุดท้าย</button>
        </div>
        <div style={{ height: '120vh' }} className="rounded-lg border border-dashed border-white/10 p-3 text-xs text-slate-400">เนื้อหายาวสำหรับลองเลื่อน</div>
      </Modal>

      {lockedOpen && (
        <ModalLayer aria-label="layer ล็อก" className="fixed inset-0 flex items-center justify-center bg-black/80 p-4">
          <div className="rounded-2xl bg-slate-900 p-6">
            <p className="text-sm">Escape ต้องไม่ปิด</p>
            <button type="button" data-testid="locked-close" onClick={() => setLockedOpen(false)} className="mt-3 rounded-lg bg-white/10 px-3 py-2 text-sm">ปิด</button>
          </div>
        </ModalLayer>
      )}

      {guardedOpen && (
        <ModalLayer
          aria-label="layer มี guard"
          onClose={() => setGuardHits((n) => n + 1)}
          className="fixed inset-0 flex items-center justify-center bg-black/80 p-4"
        >
          <div className="rounded-2xl bg-slate-900 p-6">
            <p className="text-sm">onClose ไม่ยอมปิด ต้องกดปุ่ม</p>
            <button type="button" data-testid="guarded-close" onClick={() => setGuardedOpen(false)} className="mt-3 rounded-lg bg-white/10 px-3 py-2 text-sm">ปิดจริง</button>
          </div>
        </ModalLayer>
      )}

      <DialogHost />
    </div>
  );
}

// StrictMode on purpose: the app runs under it in development, and its
// double-invoked effects are exactly what once made every modal close itself.
createRoot(document.getElementById('root')).render(<StrictMode><Fixture /></StrictMode>);
