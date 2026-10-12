import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createChannel, updateChannel, activateChannelProfile, archiveChannelProfile, getChannelReadiness } from '../api.js';
import { useChannel } from '../context/ChannelContext.jsx';
import { captureChannel, isCurrentChannel, registerChannelSwitchParticipant } from '../lib/channelRuntime.js';
import { profileForm, captureProfile, profileDirty, buildProfilePatch, buildDraftPayload, assertProfileOwner, profileFailure } from '../lib/channelProfileForm.js';

const fields = [
  ['display_name', 'ชื่อช่อง', 'ชื่อที่ใช้แสดงใน OmniCut'],
  ['handle', 'TikTok handle', '@ชื่อบัญชี หรือ URL โปรไฟล์ TikTok'],
  ['watermark_text', 'ข้อความลายน้ำ', 'ใช้เป็นตัวตนของคลิปที่สร้างใหม่'],
  ['follow_title', 'ข้อความชวนติดตาม', 'ข้อความที่ใช้กับคลิปใหม่'],
  ['avatar_asset_path', 'ไฟล์รูปประจำช่อง', 'พาธจากโปรเจกต์ เช่น 02_Assets/Brand/channel.jpg'],
];
const inputStyle = 'min-h-11 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-slate-100 focus-visible:outline-2 focus-visible:outline-cyan-300 disabled:opacity-50';
const buttonStyle = 'min-h-11 rounded-lg border border-slate-600 px-4 py-2 focus-visible:outline-2 focus-visible:outline-cyan-300 disabled:opacity-40';
const statusName = {active:'ใช้งาน',draft:'แบบร่าง',archived:'เก็บถาวร'};

export default function ChannelSettings() {
  const context = useChannel();
  const contextRef = useRef(context);
  useLayoutEffect(() => {contextRef.current=context;},[context]);
  const [model, setModel] = useState({snapshot:null,form:profileForm()});
  const modelRef = useRef(model);
  const [readiness, setReadiness] = useState(null);
  const [failure, setFailure] = useState(null);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState({id:'',...profileForm()});
  const draftRef = useRef(draft);
  const creatingRef = useRef(creating);
  const [confirmation, setConfirmation] = useState(null);
  const readinessSequence = useRef(0);
  const actionsRef = useRef({});
  const selected = context?.selected;
  const dirty = profileDirty(model.snapshot,model.form);
  const readOnly = busy || context?.loading || !selected || selected.status === 'archived';
  const hasDraft = () => creatingRef.current && ['id','display_name','handle'].some(key => draftRef.current[key].trim());
  function replaceModel(next) { modelRef.current=next; setModel(next); }
  function setWorking(value) { busyRef.current=value; setBusy(value); }

  async function loadReadiness(channel) {
    if (!channel) return;
    const sequence = ++readinessSequence.current, token=captureChannel();
    try {
      const result=await getChannelReadiness(channel.id);
      if (sequence !== readinessSequence.current || !isCurrentChannel(token) || contextRef.current?.selected?.id !== channel.id) return;
      if (result.channel_id !== channel.id || result.revision !== contextRef.current.selected.revision) return;
      setReadiness(result);
    } catch (error) {
      if (sequence === readinessSequence.current && isCurrentChannel(token)) setFailure(profileFailure(error));
    }
  }
  useEffect(() => {
    if (!selected) return;
    const old=modelRef.current;
    if (old.snapshot?.id !== selected.id || !profileDirty(old.snapshot,old.form)) {
      replaceModel({snapshot:captureProfile(selected,captureChannel()),form:profileForm(selected)});
      setFailure(null); setNotice(''); setConfirmation(null);
    }
    setReadiness(null); loadReadiness(selected);
    return () => {readinessSequence.current+=1;};
  }, [selected]);

  async function saveProfile() {
    if (busyRef.current) throw new Error('กำลังบันทึกช่อง กรุณารอให้เสร็จ');
    const captured=modelRef.current;
    try {
      const payload=buildProfilePatch(captured.snapshot,{...captured.form},contextRef.current?.selected,isCurrentChannel(captured.snapshot?.token));
      if (!payload) {replaceModel({...captured,form:{...captured.snapshot.baseline}}); return;}
      setWorking(true); setFailure(null); setNotice('');
      const result=await updateChannel(captured.snapshot.id,payload);
      if (!isCurrentChannel(captured.snapshot.token) || contextRef.current?.selected?.id !== captured.snapshot.id) throw new Error('ช่องเปลี่ยนระหว่างบันทึก ผลของช่องเดิมไม่ถูกนำมาแสดง');
      if (result.channel?.id !== captured.snapshot.id) throw new Error('ผลบันทึกไม่ตรงกับช่องที่แก้ไข');
      replaceModel({snapshot:captureProfile(result.channel,captureChannel()),form:profileForm(result.channel)});
      await contextRef.current.refresh();
      setNotice('บันทึกตัวตนช่องแล้ว คลิปเดิมคงตัวตนที่บันทึกไว้');
      await loadReadiness(result.channel);
    } catch (error) {setFailure(profileFailure(error)); throw error;}
    finally {setWorking(false);}
  }
  async function saveDraft() {
    if (busyRef.current) throw new Error('กำลังบันทึกช่อง กรุณารอให้เสร็จ');
    const token=captureChannel(), revision=contextRef.current?.registryRevision;
    try {
      const payload=buildDraftPayload({...draftRef.current},revision);
      setWorking(true); setFailure(null);
      const result=await createChannel(payload);
      if (!isCurrentChannel(token)) throw new Error('ช่องเปลี่ยนระหว่างสร้าง กรุณาโหลดทะเบียนช่องใหม่');
      if (result.channel?.id !== payload.id) throw new Error('ผลสร้างไม่ตรงกับรหัสช่อง');
      creatingRef.current=false; setCreating(false);
      draftRef.current={id:'',...profileForm()}; setDraft(draftRef.current);
      await contextRef.current.refresh();
      setNotice(`สร้าง ${result.channel.display_name} เป็นแบบร่างแล้ว เลือกช่องนี้เพื่อเติมตัวตนและตรวจความพร้อม`);
    } catch (error) {setFailure(profileFailure(error)); throw error;}
    finally {setWorking(false);}
  }
  useLayoutEffect(() => {actionsRef.current={save:async () => {
    if (profileDirty(modelRef.current.snapshot,modelRef.current.form)) await saveProfile();
    if (hasDraft()) await saveDraft();
  },discard:() => {
    if (busyRef.current) throw new Error('กำลังบันทึกช่อง กรุณารอให้เสร็จก่อนทิ้งการแก้ไขหรือสลับช่อง');
    const channel=contextRef.current?.selected;
    if (channel) replaceModel({snapshot:captureProfile(channel,captureChannel()),form:profileForm(channel)});
    creatingRef.current=false; setCreating(false); draftRef.current={id:'',...profileForm()}; setDraft(draftRef.current);
    setFailure(null); setConfirmation(null);
  }};});
  useEffect(() => registerChannelSwitchParticipant({isDirty:() => busyRef.current || profileDirty(modelRef.current.snapshot,modelRef.current.form) || hasDraft(),
    save:() => actionsRef.current.save(),discard:() => actionsRef.current.discard()}), []);

  async function changeLifecycle() {
    const snapshot=modelRef.current.snapshot, action=confirmation;
    try {
      assertProfileOwner(snapshot,contextRef.current?.selected,isCurrentChannel(snapshot?.token));
      if (profileDirty(snapshot,modelRef.current.form)) throw new Error('บันทึกหรือทิ้งการแก้ไขก่อนเปลี่ยนสถานะช่อง');
      setWorking(true); setFailure(null);
      const result=await (action === 'activate' ? activateChannelProfile : archiveChannelProfile)(snapshot.id,snapshot.revision);
      if (!isCurrentChannel(snapshot.token) || result.channel?.id !== snapshot.id) throw new Error('ผลเปลี่ยนสถานะไม่ตรงกับช่องที่เลือก');
      replaceModel({snapshot:captureProfile(result.channel,captureChannel()),form:profileForm(result.channel)});
      setConfirmation(null); await contextRef.current.refresh();
      setNotice(action === 'activate' ? 'เปิดช่องสำหรับงานใหม่แล้ว' : 'เก็บช่องถาวรแล้ว ข้อมูลเดิมยังอ่านได้');
    } catch (error) {setFailure(profileFailure(error));}
    finally {setWorking(false);}
  }
  const binding=selected?.account_binding || {};
  const canEnablePosting=selected?.status === 'active' && binding.status === 'verified' && binding.verified_handle === model.form.handle && readiness?.posting_ready;
  const issues=[...(readiness?.issues || []),...(readiness?.posting_issues || [])];

  if (!context) return <p className="text-slate-400">โหลดทะเบียนช่องก่อนตั้งค่าตัวตน</p>;
  return <section className="space-y-6 text-slate-100" aria-label="ตั้งค่าช่อง">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h2 className="text-lg font-semibold">ตัวตนช่อง</h2><p className="mt-1 text-sm text-slate-400">{selected?.display_name || context.channelId} · {statusName[selected?.status] || 'กำลังโหลด'} · {selected?.id}</p></div>
      <button className={buttonStyle} disabled={busy || context.loading} onClick={() => {
        if (creating) {draftRef.current={id:'',...profileForm()};setDraft(draftRef.current);creatingRef.current=false;setCreating(false);}
        else {creatingRef.current=true;setCreating(true);}
        setFailure(null);
      }}>{creating?'ยกเลิกแบบร่าง':'สร้างช่องใหม่'}</button>
    </div>
    {context.error && <p role="alert" className="text-sm text-rose-300">{context.error}</p>}
    {failure && <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-3 text-sm text-rose-200">{failure.message}{failure.code === 'revision_conflict' && <span> ทิ้งการแก้ไขแล้วโหลดข้อมูลล่าสุดก่อนลองใหม่</span>}</div>}
    {notice && <p role="status" className="text-sm text-emerald-300">{notice}</p>}
    {creating && <form className="space-y-4 rounded-xl border border-slate-600 bg-slate-900 p-4" onSubmit={event=>{event.preventDefault();saveDraft().catch(()=>{});}}>
      <h3 className="font-semibold">สร้างช่องแบบร่าง</h3><p className="text-sm text-slate-400">รหัสช่องเปลี่ยนภายหลังไม่ได้ ช่องใหม่ยังไม่เปิดผลิตหรือโพสต์</p>
      {[['id','รหัสช่อง'],['display_name','ชื่อช่อง'],['handle','TikTok handle (เติมภายหลังได้)']].map(([key,label])=><label className="block text-sm" key={key}><span>{label}</span><input className={`${inputStyle} mt-2`} value={draft[key]} disabled={busy} required={key!=='handle'} aria-invalid={failure?.field===key} onChange={event=>{const next={...draftRef.current,[key]:event.target.value};draftRef.current=next;setDraft(next);}} /></label>)}
      <button className={`${buttonStyle} bg-cyan-300 text-slate-950`} disabled={busy || context.loading || !Number.isInteger(context.registryRevision)}>สร้างแบบร่าง</button>
    </form>}
    {selected && <form className="space-y-4" onSubmit={event=>{event.preventDefault();saveProfile().catch(()=>{});}}>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{fields.map(([key,label,help])=><label key={key} className={`block text-sm ${key==='avatar_asset_path'?'md:col-span-2':''}`}>
        <span>{label}</span><input aria-label={label} className={`${inputStyle} mt-2`} value={model.form[key]} disabled={readOnly} aria-describedby={`channel-${key}-help`} aria-invalid={failure?.field===key} onChange={event=>replaceModel({...modelRef.current,form:{...modelRef.current.form,[key]:event.target.value}})} />
        <span id={`channel-${key}-help`} className="mt-1 block text-xs text-slate-400">{help}</span>
      </label>)}</div>
      <div className="rounded-xl border border-slate-700 bg-slate-900 p-4 text-sm">
        <p>บัญชี TikTok: {binding.status==='verified'?`ตรวจแล้ว ${binding.verified_handle}`:'ยังไม่ได้ตรวจบัญชีจริง'}</p>
        <p className="mt-2 text-xs text-slate-400">ตรวจบัญชีจากหน้า TikTok Studio ก่อนเปิดโพสต์ เปลี่ยน handle แล้วต้องตรวจบัญชีใหม่</p>
        <label className="mt-3 flex min-h-11 items-center gap-3"><input type="checkbox" checked={model.form.posting_enabled} disabled={readOnly || (!model.form.posting_enabled && !canEnablePosting)} onChange={event=>replaceModel({...modelRef.current,form:{...modelRef.current.form,posting_enabled:event.target.checked}})} /><span>เปิดโพสต์สำหรับช่องนี้</span></label>
      </div>
      <div className="flex flex-wrap gap-3"><button disabled={readOnly || !dirty} className={`${buttonStyle} bg-cyan-300 text-slate-950`}>{busy?'กำลังบันทึก':'บันทึกตัวตนช่อง'}</button>
        <button type="button" disabled={busy || !dirty} className={buttonStyle} onClick={()=>actionsRef.current.discard()}>ทิ้งการแก้ไข</button>
        <button type="button" disabled={busy} className={buttonStyle} onClick={async()=>{await context.refresh();loadReadiness(contextRef.current.selected);}}>ตรวจความพร้อมอีกครั้ง</button>
      </div>
    </form>}
    <div className="rounded-xl border border-slate-700 p-4"><h3 className="font-semibold">ความพร้อมของช่อง</h3>
      <p className="mt-2 text-sm text-slate-300">{selected?.status==='archived'?'ช่องเก็บถาวร อ่านข้อมูลได้เท่านั้น':!readiness?'กำลังตรวจความพร้อม':readiness.ready?(selected?.status==='draft'?'ตัวตนครบ เปิดใช้งานช่องเพื่อเริ่มงานใหม่ได้':'ตัวตนครบสำหรับการสร้างงาน'):'ยังมีข้อมูลที่ต้องเติมก่อนสร้างงาน'}</p>
      {issues.length>0 && <ul className="mt-3 space-y-2 text-sm text-amber-200">{issues.map((issue,index)=><li key={`${issue.code}-${index}`}>{issue.message || issue.detail || issue.code}{issue.field?` (${issue.field})`:''}</li>)}</ul>}
      <div className="mt-4 flex flex-wrap gap-3">
        {selected?.status==='draft' && <button className={buttonStyle} disabled={busy || dirty || !readiness?.ready} onClick={()=>setConfirmation('activate')}>เปิดใช้งานช่อง</button>}
        {selected && selected.id!=='main' && selected.status!=='archived' && <button className={buttonStyle} disabled={busy || dirty} onClick={()=>setConfirmation('archive')}>เก็บช่องถาวร</button>}
      </div>
      {confirmation && <div className="mt-4 rounded-lg border border-amber-400/40 p-3" role="alertdialog" aria-label="ยืนยันสถานะช่อง" onKeyDown={event=>{if(event.key==='Escape'&&!busy)setConfirmation(null);}}>
        <p className="text-sm">{confirmation==='activate'?'เปิดช่องนี้ให้เริ่มสร้างงานใหม่ได้หรือไม่':'เก็บช่องนี้ถาวรหรือไม่ งานใหม่และโพสต์จะหยุด ข้อมูลเดิมยังอ่านได้'}</p>
        <div className="mt-3 flex flex-wrap gap-3"><button autoFocus className={buttonStyle} disabled={busy} onClick={changeLifecycle}>ยืนยัน</button><button className={buttonStyle} disabled={busy} onClick={()=>setConfirmation(null)}>ยกเลิก</button></div>
      </div>}
    </div>
  </section>;
}
