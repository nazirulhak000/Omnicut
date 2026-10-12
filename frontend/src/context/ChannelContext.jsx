import React, { createContext, useContext, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { getChannels } from '../api.js';
import { activeChannel, subscribeChannel, activateChannel, dirtyChannelParticipants, channelSelectionError, channelRuntimeRevision,
  saveBeforeChannelSwitch, discardBeforeChannelSwitch } from '../lib/channelRuntime.js';

const ChannelContext = createContext(null);

export function ChannelProvider({ children }) {
  useSyncExternalStore(subscribeChannel, channelRuntimeRevision, () => 0);
  const channelId = activeChannel();
  const [channels, setChannels] = useState([]);
  const [registryRevision, setRegistryRevision] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(null);
  const [switching, setSwitching] = useState(false);
  const dialogRef = useRef(null);
  useEffect(() => {
    if (!pending) return;
    const previous = document.activeElement;
    const dialog = dialogRef.current;
    const onKey = event => {
      if (event.key === 'Escape' && !switching) { event.preventDefault(); setPending(null); }
      if (event.key !== 'Tab') return;
      const buttons = [...dialog.querySelectorAll('button:not(:disabled)')];
      if (!buttons.length) { event.preventDefault(); dialog.focus(); return; }
      const first = buttons[0], last = buttons.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    dialog.addEventListener('keydown', onKey);
    return () => { dialog.removeEventListener('keydown', onKey); previous?.focus(); };
  }, [pending, switching]);
  async function refresh() {
    setLoading(true);
    try { const data = await getChannels(); setChannels(data.channels || []); setRegistryRevision(data.revision ?? null); setError(''); }
    catch (failure) { setError(failure.friendlyMessage || failure.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { refresh(); }, []);
  const selected = channels.find(item => item.id === channelId);
  async function finishSwitch(next, decision) {
    setSwitching(true);
    try {
      if (decision === 'save') await saveBeforeChannelSwitch();
      if (decision === 'discard') await discardBeforeChannelSwitch();
      activateChannel(next);
      setPending(null);
      setError('');
    } catch (failure) { setError(failure.friendlyMessage || failure.message); }
    finally { setSwitching(false); }
  }
  function switchChannel(next) {
    if ((next === channelId && !channelSelectionError()) || switching) return;
    if (!channels.some(item => item.id === next)) { setError('ไม่พบช่องที่เลือก กรุณาโหลดรายการใหม่'); return; }
    if (dirtyChannelParticipants().length) setPending(next);
    else finishSwitch(next);
  }
  return <ChannelContext.Provider value={{ channelId, channels, selected, error: channelSelectionError() || error, selectionInvalid: !!channelSelectionError(), loading, switching, registryRevision,
    switchChannel, refresh, writable: !channelSelectionError() && !loading && ['active', 'draft'].includes(selected?.status), canStart: !channelSelectionError() && !loading && selected?.status === 'active' }}>
    {children}
    {pending && <div className="fixed inset-0 z-[100] bg-black/70 flex items-center justify-center p-4">
      <section ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="channel-switch-title" aria-describedby="channel-switch-description" aria-busy={switching}
        className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-700 p-6 text-slate-100">
        <h2 id="channel-switch-title" className="text-lg font-semibold">บันทึกก่อนสลับช่อง</h2>
        <p id="channel-switch-description" className="mt-2 text-sm text-slate-300">โปรเจกต์ในช่อง {selected?.display_name || channelId} มีการแก้ไขที่ยังไม่ได้บันทึก จะสลับไป {channels.find(item => item.id === pending)?.display_name || pending}</p>
        {error && <p role="alert" className="mt-3 text-sm text-red-300">{error}</p>}
        <div className="mt-5 flex flex-wrap gap-3">
          <button autoFocus disabled={switching} onClick={() => finishSwitch(pending, 'save')}
            className="min-h-11 rounded-lg bg-cyan-300 text-slate-950 px-4 py-2 focus-visible:outline-2 focus-visible:outline-cyan-200 disabled:opacity-50">{switching ? 'กำลังจัดการงานที่ค้าง' : 'บันทึกและสลับ'}</button>
          <button disabled={switching} onClick={() => finishSwitch(pending, 'discard')}
            className="min-h-11 rounded-lg border border-slate-500 px-4 py-2 focus-visible:outline-2 focus-visible:outline-cyan-200 disabled:opacity-50">ทิ้งการแก้ไขและสลับ</button>
          <button disabled={switching} onClick={() => setPending(null)} className="min-h-11 rounded-lg px-4 py-2 focus-visible:outline-2 focus-visible:outline-cyan-200">อยู่ช่องเดิม</button>
        </div>
      </section>
    </div>}
  </ChannelContext.Provider>;
}

export function useChannel() { return useContext(ChannelContext); }

export function ChannelSelector() {
  const state = useChannel();
  if (!state) return null;
  return <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-200">
    <label className="flex min-w-0 items-center gap-2">
    <span className="text-slate-400">ช่อง</span>
    <select aria-label="เลือกช่อง" value={state.channelId} disabled={state.loading || state.switching}
      onChange={event => state.switchChannel(event.target.value)}
      className="min-h-11 w-full max-w-[190px] rounded-lg border border-slate-600 bg-slate-900 px-3 focus-visible:outline-2 focus-visible:outline-cyan-300 disabled:opacity-50">
      {!state.selected && <option value={state.channelId}>{state.channelId}</option>}
      {state.channels.map(item => <option key={item.id} value={item.id}>
        {item.display_name || item.id}{item.status === 'archived' ? ' · เก็บถาวร' : item.status === 'draft' ? ' · แบบร่าง' : ''}
      </option>)}
    </select>
    </label>
    {state.selectionInvalid && <button onClick={() => state.switchChannel(state.channelId)} className="min-h-11 rounded-lg border border-slate-500 px-3 focus-visible:outline-2 focus-visible:outline-cyan-300">เปิดช่องหลัก</button>}
    {state.selected?.handle && <span className="max-w-[190px] truncate text-xs text-slate-400">{state.selected.handle}</span>}
    {state.error && <div className="flex w-full flex-wrap items-center gap-2 text-xs text-rose-300"><span role="alert">{state.error}</span><button onClick={state.refresh} className="min-h-11 rounded px-2 underline focus-visible:outline-2 focus-visible:outline-cyan-300">โหลดรายการใหม่</button></div>}
  </div>;
}

export function ChannelWorkspaceBar() {
  const state = useChannel();
  if (!state) return null;
  const status = state.loading ? 'กำลังโหลดข้อมูลช่อง' : !state.selected ? 'ไม่พบช่องนี้ เลือกช่องหรือโหลดรายการใหม่' :
    state.selected.status === 'archived' ? 'เก็บถาวร · อ่านอย่างเดียว' :
    state.selected.status === 'draft' ? 'แบบร่าง · ยังเริ่มผลิตหรือโพสต์ไม่ได้' : 'พร้อมผลิต';
  return <div className="flex flex-shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-white/10 bg-slate-950 px-4 py-2">
    <ChannelSelector /><span role="status" className={`text-xs ${state.canStart ? 'text-emerald-300' : 'text-amber-200'}`}>{status}</span>
  </div>;
}
