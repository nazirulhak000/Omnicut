import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CalendarDays, ChevronDown, ChevronUp, Clock, Copy, GripVertical, Image as ImageIcon, Layers, Plus, RefreshCw, Rocket, RotateCcw, Settings2, Shuffle, Trash2 } from 'lucide-react';
import { Modal, Badge } from './ui';
import { commitScheduleAutofill, copyScheduleTemplate, createScheduleQueue, getScheduleQueue, getScheduleTemplate, prepareScheduleQueue, previewScheduleAutofill, removeScheduleQueue, resetScheduleTemplate, saveScheduleTemplate, updateScheduleQueue } from '../api';
import { addDays, buildScheduleIso, dateOnly, DEFAULT_PRIMARY_TIMES, groupScheduleItems, localParts, mergeScheduleDraft, nextTemplateSlotAfterLatest, primaryTimeOptions, PROJECT_TIME_ZONE, scheduleTimeOptions, templateForWeek, toLocalDateTime, weekStartForDate } from '../lib/scheduleQueue';

const STATUS_LABELS = {
  planned: 'รอจัดส่ง',
  ready_for_extension: 'พร้อมทำใน Extension',
  awaiting_post: 'รอกดโพสต์',
  posted: 'โพสต์แล้ว',
  failed: 'ผิดพลาด',
};

const STATUS_STYLES = {
  planned: 'text-amber-200 bg-amber-500/10 border-amber-500/25',
  ready_for_extension: 'text-cyan-200 bg-cyan-500/10 border-cyan-500/25',
  awaiting_post: 'text-violet-200 bg-violet-500/10 border-violet-500/25',
  posted: 'text-emerald-200 bg-emerald-500/10 border-emerald-500/25',
  failed: 'text-red-200 bg-red-500/10 border-red-500/25',
};

function clipKey(clip) {
  return String(clip?.video_url || '').replaceAll('\\', '/').toLowerCase();
}

function coverSrc(path) {
  if (!path) return '';
  return path.startsWith('/') ? path : `/api/media/${path}`;
}

function coverValue(item, clip) {
  return item?.cover_url
    || item?.cover_path
    || item?.cover_3x4_url
    || item?.cover_3x4_path
    || item?.cover_9x16_url
    || item?.cover_9x16_path
    || clip?.cover_url
    || clip?.cover_path
    || clip?.cover_3x4_url
    || clip?.cover_3x4_path
    || clip?.cover_9x16_url
    || clip?.cover_9x16_path
    || '';
}

function clipToPayload(clip, scheduledAt) {
  const product = clip.parentProduct || {};
  return {
    video_path: clip.video_url,
    scheduled_at: scheduledAt,
    product_id: product.id || null,
    angle_id: clip.angle_id || null,
    product_name: product.name || clip.product_name || null,
    project_name: clip.project_name || null,
    hook_title: clip.hook_title || null,
    cover_path: clip.cover_path || null,
    cover_url: clip.cover_url || null,
    caption: clip.tiktok_caption || clip.hook_title || '',
    hashtags: clip.tiktok_hashtags || '',
    tiktok_product_id: product.tiktok_product_id || clip.tiktok_product_id || null,
  };
}

function thaiDate(dateKey) {
  const [year, month, day] = dateKey.split('-').map(Number);
  if (!year || !month || !day) return dateKey;
  return new Intl.DateTimeFormat('th-TH', { timeZone: PROJECT_TIME_ZONE, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(Date.UTC(year, month - 1, day, 5)));
}

function nextSlot() {
  const now = new Date(Date.now() + 15 * 60 * 1000);
  now.setMinutes(Math.ceil(now.getMinutes() / 5) * 5, 0, 0);
  return toLocalDateTime(now);
}

function queueKey(item) {
  return String(item?.video_path || '').replaceAll('\\', '/').toLowerCase();
}

function clipToAutofillPayload(clip) {
  const product = clip.parentProduct || {};
  return {
    video_path: clip.video_url,
    product_id: product.id || clip.product_id || null,
    angle_id: clip.angle_id || null,
    product_name: product.name || clip.product_name || null,
    project_name: clip.project_name || null,
    hook_title: clip.hook_title || null,
    cover_path: clip.cover_path || null,
    cover_url: clip.cover_url || null,
    caption: clip.tiktok_caption || clip.hook_title || '',
    hashtags: clip.tiktok_hashtags || '',
    tiktok_product_id: product.tiktok_product_id || clip.tiktok_product_id || null,
  };
}

function errorText(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

function defaultTemplateDraft(weekStart) {
  return templateForWeek({ week_start: weekStart, days: Object.fromEntries(
    Array.from({ length: 7 }, (_, index) => [String(index), { enabled: true, times: DEFAULT_PRIMARY_TIMES }]),
  ) }, weekStart);
}

export default function ScheduleAgenda({ readyClips = [], onPreviewVideo, onOpenCoverStudio, showToast }) {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [singleOpen, setSingleOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [singleDraft, setSingleDraft] = useState({ clip: null, ...nextSlot() });
  const [bulkSelected, setBulkSelected] = useState([]);
  const [bulkDraft, setBulkDraft] = useState({ ...nextSlot(), interval: 5 });
  const [saving, setSaving] = useState(false);
  const [draggedId, setDraggedId] = useState(null);
  const timeOptions = useMemo(() => scheduleTimeOptions(), []);
  const [templateOpen, setTemplateOpen] = useState(false);
  const [templateWeek, setTemplateWeek] = useState(weekStartForDate(dateOnly()));
  const [templateDraft, setTemplateDraft] = useState(defaultTemplateDraft(weekStartForDate(dateOnly())));
  const [templateBusy, setTemplateBusy] = useState(false);
  const [autofillOpen, setAutofillOpen] = useState(false);
  const [autofillRange, setAutofillRange] = useState('today');
  const [autofillStart, setAutofillStart] = useState(dateOnly());
  const [autofillEnd, setAutofillEnd] = useState(dateOnly());
  const [autofillProduct, setAutofillProduct] = useState('all');
  const [autofillLimit, setAutofillLimit] = useState('');
  const [autofillPreview, setAutofillPreview] = useState(null);
  const [autofillBusy, setAutofillBusy] = useState(false);
  const [requeueOpen, setRequeueOpen] = useState(false);
  const [requeueTarget, setRequeueTarget] = useState(null);
  const [requeueDraft, setRequeueDraft] = useState({ date: '', time: '' });
  const [requeueLoading, setRequeueLoading] = useState(false);
  const scheduleDrafts = useRef(new Map());
  const scheduleRequestIds = useRef(new Map());
  const requeueRequestId = useRef(0);
  const primaryOptions = useMemo(() => primaryTimeOptions(), []);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const response = await getScheduleQueue();
      setQueue(response.items || []);
      scheduleDrafts.current.clear();
      scheduleRequestIds.current.clear();
    } catch (error) {
      showToast?.(`โหลดคิวไม่สำเร็จ: ${error.response?.data?.detail || error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadQueue(); }, []);

  const queuedKeys = useMemo(() => new Set(queue.map((item) => String(item.video_path || '').replaceAll('\\', '/').toLowerCase())), [queue]);
  const availableClips = useMemo(() => {
    const seen = new Set();
    return readyClips.filter((clip) => {
      const key = clipKey(clip);
      if (!key || seen.has(key) || queuedKeys.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [readyClips, queuedKeys]);
  const productOptions = useMemo(() => {
    const values = new Map();
    availableClips.forEach((clip) => {
      const product = clip.parentProduct || {};
      const id = String(product.id || clip.product_id || product.name || clip.product_name || 'other');
      values.set(id, product.name || clip.product_name || 'ไม่ระบุสินค้า');
    });
    return [...values.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [availableClips]);
  const grouped = useMemo(() => groupScheduleItems(queue), [queue]);
  const dates = Object.keys(grouped);

  const saveSingle = async () => {
    if (!singleDraft.clip || !singleDraft.date || !singleDraft.time) return;
    setSaving(true);
    try {
      await createScheduleQueue(clipToPayload(singleDraft.clip, buildScheduleIso(singleDraft.date, singleDraft.time)));
      setSingleOpen(false);
      showToast?.('เพิ่มคลิปลงคิวแล้ว');
      await loadQueue();
    } catch (error) {
      showToast?.(error.response?.data?.detail || error.message || 'เพิ่มคิวไม่สำเร็จ', 'error');
    } finally { setSaving(false); }
  };

  const bulkPreview = useMemo(() => {
    const start = new Date(`${bulkDraft.date}T${bulkDraft.time}:00+07:00`);
    return bulkSelected.map((clip, index) => {
      const at = new Date(start.getTime() + index * Number(bulkDraft.interval || 5) * 60000);
      const parts = localParts(at.toISOString());
      return { clip, ...parts, scheduledAt: buildScheduleIso(parts.date, parts.time) };
    });
  }, [bulkDraft, bulkSelected]);

  const saveBulk = async () => {
    if (!bulkPreview.length) return;
    setSaving(true);
    try {
      await createScheduleQueue({ items: bulkPreview.map(({ clip, scheduledAt }) => clipToPayload(clip, scheduledAt)) });
      setBulkOpen(false);
      setBulkSelected([]);
      showToast?.(`เพิ่มคิว ${bulkPreview.length} คลิปแล้ว`);
      await loadQueue();
    } catch (error) {
      showToast?.(error.response?.data?.detail || error.message || 'เพิ่มคิวชุดไม่สำเร็จ รายการเดิมยังอยู่ครบ', 'error');
    } finally { setSaving(false); }
  };

  const reschedule = async (item, date, time) => {
    const requestId = (scheduleRequestIds.current.get(item.id) || 0) + 1;
    scheduleRequestIds.current.set(item.id, requestId);
    scheduleDrafts.current.set(item.id, { date, time });
    try {
      const updated = await updateScheduleQueue(item.id, { scheduled_at: buildScheduleIso(date, time) });
      if (scheduleRequestIds.current.get(item.id) === requestId) {
        scheduleDrafts.current.set(item.id, localParts(updated.scheduled_at));
        setQueue((prev) => prev.map((row) => row.id === item.id ? updated : row));
        showToast?.('ย้ายเวลาในคิวแล้ว');
      }
    } catch (error) {
      if (scheduleRequestIds.current.get(item.id) === requestId) {
        scheduleDrafts.current.delete(item.id);
        showToast?.(error.response?.data?.detail || error.message || 'ย้ายเวลาไม่สำเร็จ', 'error');
      }
    }
  };

  const updateScheduleField = (item, field, value) => {
    const current = scheduleDrafts.current.get(item.id) || localParts(item.scheduled_at);
    const next = mergeScheduleDraft(current, field, value);
    scheduleDrafts.current.set(item.id, next);
    void reschedule(item, next.date, next.time);
  };

  const resetForMove = async (item) => {
    try {
      const updated = await updateScheduleQueue(item.id, { status: 'planned' });
      setQueue((prev) => prev.map((row) => row.id === item.id ? updated : row));
    } catch (error) { showToast?.(error.response?.data?.detail || error.message, 'error'); }
  };

  const removeItem = async (item) => {
    try {
      await removeScheduleQueue(item.id);
      setQueue((prev) => prev.filter((row) => row.id !== item.id));
      showToast?.('นำคลิปออกจากคิวแล้ว ไฟล์ MP4 ยังอยู่ครบ');
    } catch (error) { showToast?.(error.response?.data?.detail || error.message, 'error'); }
  };

  const prepareItem = async (item) => {
    try {
      const updated = await prepareScheduleQueue(item.id);
      setQueue((prev) => prev.map((row) => row.id === item.id ? updated : row));
      showToast?.('ส่งคลิปนี้ให้ Extension แล้ว เปิด Extension เพื่อทำ checklist ต่อ');
    } catch (error) { showToast?.(error.response?.data?.detail || error.message, 'error'); }
  };

  const onDropDate = async (date) => {
    if (!draggedId) return;
    const item = queue.find((row) => row.id === draggedId);
    setDraggedId(null);
    if (!item || item.status !== 'planned') {
      showToast?.('ต้องรีเซ็ตคลิปกลับเป็นรอจัดส่งก่อนจึงจะย้ายวันได้', 'error');
      return;
    }
    const current = localParts(item.scheduled_at);
    if (current.date !== date) await reschedule(item, date, current.time);
  };

  const openRequeue = async (item) => {
    const requestId = requeueRequestId.current + 1;
    requeueRequestId.current = requestId;
    const now = new Date();
    setRequeueTarget(item);
    setRequeueDraft({ date: '', time: '' });
    setRequeueLoading(true);
    setRequeueOpen(true);
    try {
      const latestMs = queue
        .filter((row) => row?.status !== 'posted')
        .map((row) => new Date(row?.scheduled_at || '').getTime())
        .filter(Number.isFinite)
        .reduce((latest, value) => Math.max(latest, value), 0);
      const startDate = dateOnly(new Date(Math.max(now.getTime(), latestMs)));
      const templates = {};
      let slot = null;
      for (let offset = 0; offset < 366 && !slot; offset += 7) {
        const week = weekStartForDate(addDays(startDate, offset));
        templates[week] = await getScheduleTemplate(week);
        slot = nextTemplateSlotAfterLatest(queue, templates, now);
      }
      if (requestId !== requeueRequestId.current) return;
      setRequeueDraft(slot || { date: '', time: '' });
      if (!slot) showToast?.('ไม่พบช่องว่างตามเทมเพลต กรุณาเลือกวันเวลาเอง', 'error');
    } catch (error) {
      if (requestId === requeueRequestId.current) {
        setRequeueDraft({ date: '', time: '' });
        showToast?.(errorText(error, 'โหลดเทมเพลตเวลาไม่สำเร็จ กรุณาเลือกวันเวลาเอง'), 'error');
      }
    } finally {
      if (requestId === requeueRequestId.current) setRequeueLoading(false);
    }
  };

  const saveRequeue = async () => {
    if (!requeueTarget) return;
    setSaving(true);
    try {
      await reschedule(requeueTarget, requeueDraft.date, requeueDraft.time);
      setRequeueOpen(false);
      setRequeueTarget(null);
    } finally { setSaving(false); }
  };

  const loadTemplate = async (week = templateWeek) => {
    setTemplateBusy(true);
    try {
      const response = await getScheduleTemplate(week);
      setTemplateDraft(templateForWeek(response, week));
    } catch (error) {
      setTemplateDraft(defaultTemplateDraft(week));
      showToast?.(errorText(error, 'โหลดเวลารายสัปดาห์ไม่สำเร็จ'), 'error');
    } finally { setTemplateBusy(false); }
  };

  const openTemplate = async () => {
    setTemplateOpen(true);
    await loadTemplate();
  };

  const saveTemplate = async () => {
    setTemplateBusy(true);
    try {
      const response = await saveScheduleTemplate({ week_start: templateWeek, days: templateDraft.days });
      setTemplateDraft(templateForWeek(response, templateWeek));
      showToast?.('บันทึกเวลารายสัปดาห์แล้ว');
    } catch (error) { showToast?.(errorText(error, 'บันทึกเวลาไม่สำเร็จ'), 'error'); }
    finally { setTemplateBusy(false); }
  };

  const copyPreviousTemplate = async () => {
    setTemplateBusy(true);
    try {
      const response = await copyScheduleTemplate({ source_week_start: addDays(templateWeek, -7), target_week_start: templateWeek });
      setTemplateDraft(templateForWeek(response, templateWeek));
      showToast?.('คัดลอกเวลาจากสัปดาห์ก่อนแล้ว');
    } catch (error) { showToast?.(errorText(error, 'คัดลอกเวลาไม่สำเร็จ'), 'error'); }
    finally { setTemplateBusy(false); }
  };

  const resetTemplate = async () => {
    setTemplateBusy(true);
    try {
      const response = await resetScheduleTemplate(templateWeek);
      setTemplateDraft(templateForWeek(response, templateWeek));
      showToast?.('คืนค่าเวลาเริ่มต้นแล้ว');
    } catch (error) { showToast?.(errorText(error, 'คืนค่าเวลาไม่สำเร็จ'), 'error'); }
    finally { setTemplateBusy(false); }
  };

  const chooseAutofillRange = (mode) => {
    const today = dateOnly();
    const week = weekStartForDate(today);
    setAutofillRange(mode);
    if (mode === 'today') {
      setAutofillStart(today); setAutofillEnd(today);
    } else if (mode === 'week') {
      setAutofillStart(week); setAutofillEnd(addDays(week, 6));
    }
    setAutofillPreview(null);
  };

  const runAutofillPreview = async () => {
    if (!autofillStart || !autofillEnd) return;
    setAutofillBusy(true);
    try {
      const response = await previewScheduleAutofill({
        start_date: autofillStart,
        end_date: autofillEnd,
        product_ids: autofillProduct === 'all' ? [] : [autofillProduct],
        limit: autofillLimit ? Number(autofillLimit) : null,
        seed: Math.floor(Math.random() * 2147483647),
        clips: availableClips.map((clip) => {
          const product = clip.parentProduct || {};
          return {
            ...clipToAutofillPayload(clip),
            product_id: product.id || clip.product_id || null,
          };
        }),
      });
      setAutofillPreview(response);
    } catch (error) { showToast?.(errorText(error, 'สร้างตัวอย่าง auto-fill ไม่สำเร็จ'), 'error'); }
    finally { setAutofillBusy(false); }
  };

  const saveAutofill = async () => {
    if (!autofillPreview?.items?.length) return;
    setAutofillBusy(true);
    try {
      await commitScheduleAutofill({ items: autofillPreview.items });
      setAutofillOpen(false);
      setAutofillPreview(null);
      showToast?.(`จัดคิวอัตโนมัติ ${autofillPreview.items.length} คลิปแล้ว`);
      await loadQueue();
    } catch (error) { showToast?.(errorText(error, 'บันทึก auto-fill ไม่สำเร็จ อาจมีคิวซ้อนกัน'), 'error'); }
    finally { setAutofillBusy(false); }
  };

  const openSingle = () => { setSingleDraft({ clip: null, ...nextSlot(queue) }); setSingleOpen(true); };
  const openBulk = () => { setBulkDraft({ ...nextSlot(queue), interval: 5 }); setBulkOpen(true); };
  const openAutofill = () => { chooseAutofillRange('today'); setAutofillOpen(true); };

  return (
    <div className="space-y-5">
      <div className="rounded-3xl border border-white/[0.1] bg-[#080B11] shadow-xl overflow-hidden">
        <div className="px-5 py-5 border-b border-white/[0.08] bg-gradient-to-r from-cyan-500/[0.08] to-transparent">
          <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-2xl bg-cyan-400/10 text-cyan-300"><CalendarDays className="w-5 h-5" /></div>
              <div>
                <h2 className="text-base sm:text-lg font-black text-white font-kanit">คิวโพสต์หลายวัน</h2>
                <p className="text-xs text-slate-400 mt-1">เรียงตามวันที่และเวลาในเขต Asia/Bangkok · รอบละ 5 นาที · {queue.length} คลิปในคิว</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={openAutofill} className="px-3.5 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black flex items-center gap-1.5 hover:brightness-110"><Shuffle className="w-4 h-4" />จัดคิวอัตโนมัติ</button>
              <button type="button" onClick={openTemplate} className="px-3.5 py-2 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.05] text-cyan-100 text-xs font-bold flex items-center gap-1.5 hover:bg-cyan-400/[0.12]"><Settings2 className="w-4 h-4" />ตั้งค่าเวลารายสัปดาห์</button>
              <button type="button" onClick={openSingle} className="px-3.5 py-2 rounded-xl border border-white/[0.12] bg-white/[0.05] text-white text-xs font-bold flex items-center gap-1.5 hover:bg-white/[0.1]"><Plus className="w-4 h-4" />เพิ่มคลิป</button>
              <button type="button" onClick={openBulk} className="px-3.5 py-2 rounded-xl border border-white/[0.12] bg-white/[0.05] text-white text-xs font-bold flex items-center gap-1.5 hover:bg-white/[0.1]"><Layers className="w-4 h-4" />เพิ่มเป็นชุด</button>
              <button type="button" onClick={loadQueue} className="p-2 rounded-xl border border-white/[0.1] text-slate-300 hover:text-white" aria-label="รีเฟรชคิว"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></button>
            </div>
          </div>
        </div>

        {loading ? <div className="p-10 text-center text-sm text-slate-500">กำลังโหลดคิวโพสต์...</div> : dates.length === 0 ? (
          <div className="p-12 text-center"><CalendarDays className="w-8 h-8 mx-auto text-slate-600 mb-3" /><p className="text-sm text-slate-300 font-bold">ยังไม่มีคลิปในคิว</p><p className="text-xs text-slate-500 mt-1">เพิ่มคลิปเดี่ยวหรือเลือกหลายคลิปเพื่อวางแผนล่วงหน้าได้เลย</p></div>
        ) : (
          <div className="p-4 sm:p-5 space-y-4">
            {dates.map((date) => (
              <section key={date} onDragOver={(event) => event.preventDefault()} onDrop={() => onDropDate(date)} className="rounded-2xl border border-white/[0.08] bg-black/20 overflow-hidden">
                <div className="px-4 py-3 flex items-center justify-between bg-white/[0.035] border-b border-white/[0.08]"><div><h3 className="text-sm font-black text-white">{thaiDate(date)}</h3><p className="text-[11px] text-slate-500 mt-0.5">{date} · {grouped[date].length} คลิป</p></div><span className="text-[10px] text-cyan-300 border border-cyan-400/20 rounded-full px-2 py-1">ลากคลิปมาวางเพื่อย้ายวัน</span></div>
                <div className="divide-y divide-white/[0.06]">
                  {grouped[date].map((item) => {
                    const parts = localParts(item.scheduled_at);
                    const clip = readyClips.find((candidate) => clipKey(candidate) === String(item.video_path || '').replaceAll('\\', '/').toLowerCase());
                    const coverPath = coverValue(item, clip);
                    const hasCover = Boolean(coverPath);
                    const overdue = item.is_overdue || (item.status === 'planned' && new Date(item.scheduled_at).getTime() < Date.now());
                    return (
                      <article key={item.id} draggable onDragStart={() => setDraggedId(item.id)} className="p-3 sm:p-4 flex flex-col lg:flex-row lg:items-center gap-3 hover:bg-white/[0.025] transition-colors">
                        <GripVertical className="hidden lg:block w-4 h-4 text-slate-600 cursor-grab flex-shrink-0" />
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          <button type="button" onClick={() => clip?.video_url && onPreviewVideo?.(clip.video_url, clip)} className="w-14 h-20 rounded-xl overflow-hidden bg-black border border-white/[0.12] flex-shrink-0 relative group">
                            {coverSrc(coverPath) ? <img src={coverSrc(coverPath)} alt="" className="w-full h-full object-cover" /> : <video src={`/api/media/${item.video_path}`} muted className="w-full h-full object-cover" />}
                            <span className="absolute inset-x-1 bottom-1 text-[9px] rounded bg-black/75 text-white py-0.5">พรีวิว</span>
                          </button>
                          <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-1.5"><span className="text-xs font-bold text-white truncate">{item.product_name || 'ไม่ระบุสินค้า'}</span><Badge className={STATUS_STYLES[item.status] || STATUS_STYLES.planned}>{STATUS_LABELS[item.status] || item.status}</Badge>{overdue && <Badge className="text-red-200 bg-red-500/10 border-red-500/25">เลยกำหนด</Badge>}</div><p className="text-sm text-cyan-200 font-bold mt-1 line-clamp-2">{item.hook_title || item.project_name || item.video_path}</p><p className="text-[10px] text-slate-500 font-mono mt-1 truncate">{item.video_path}</p></div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                          <label className="flex items-center gap-1.5 text-[10px] text-slate-500"><CalendarDays className="w-3.5 h-3.5" /><input type="date" value={scheduleDrafts.current.get(item.id)?.date || parts.date} disabled={item.status !== 'planned'} onChange={(event) => updateScheduleField(item, 'date', event.target.value)} className="px-2 py-1.5 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white" /></label>
                          <label className="flex items-center gap-1.5 text-[10px] text-slate-500"><Clock className="w-3.5 h-3.5 text-cyan-300" /><select value={scheduleDrafts.current.get(item.id)?.time || parts.time} disabled={item.status !== 'planned'} onChange={(event) => updateScheduleField(item, 'time', event.target.value)} className="px-2 py-1.5 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white font-mono">{timeOptions.map((time) => <option key={time} value={time}>{time}</option>)}</select></label>
                          {overdue && item.status === 'planned' && <button type="button" onClick={() => openRequeue(item)} className="px-2.5 py-1.5 rounded-lg border border-red-400/30 text-red-200 text-[11px]">จัดคิวใหม่</button>}
                          {item.status === 'planned' || item.status === 'failed' ? <button type="button" onClick={() => prepareItem(item)} className="px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white text-[11px] font-bold flex items-center gap-1"><Rocket className="w-3.5 h-3.5" />เตรียมให้ Extension</button> : item.status === 'ready_for_extension' ? <button type="button" onClick={() => resetForMove(item)} className="px-2.5 py-1.5 rounded-lg border border-amber-400/25 text-amber-200 text-[11px]">รีเซ็ตเพื่อย้าย</button> : null}
                          {clip && onOpenCoverStudio ? <button type="button" data-cover-state={hasCover ? 'ready' : 'missing'} onClick={() => onOpenCoverStudio(clip)} className={`p-1.5 rounded-lg border transition-colors ${hasCover ? 'border-emerald-400/45 bg-emerald-400/10 text-white shadow-[0_0_12px_rgba(52,211,153,0.16)] hover:bg-emerald-400/20' : 'border-white/[0.1] text-slate-600 hover:text-white hover:border-white/[0.2]'}`} title={hasCover ? 'มีภาพปกแล้ว · คลิกเพื่อแก้ไข' : 'ยังไม่มีภาพปก · คลิกเพื่อสร้าง'} aria-label={hasCover ? 'มีภาพปกแล้ว คลิกเพื่อแก้ไข' : 'ยังไม่มีภาพปก คลิกเพื่อสร้าง'}><ImageIcon className="w-3.5 h-3.5" /></button> : <span role="img" data-cover-state={hasCover ? 'ready' : 'missing'} className={`p-1.5 rounded-lg border ${hasCover ? 'border-emerald-400/45 bg-emerald-400/10 text-white' : 'border-white/[0.08] text-slate-700'}`} title={hasCover ? 'มีภาพปกแล้ว' : 'ยังไม่มีภาพปก'} aria-label={hasCover ? 'มีภาพปกแล้ว' : 'ยังไม่มีภาพปก'}><ImageIcon className="w-3.5 h-3.5" /></span>}
                          {item.status === 'planned' ? <button type="button" onClick={() => removeItem(item)} className="p-1.5 rounded-lg border border-white/[0.1] text-slate-500 hover:text-red-300" title="นำออกจากคิว"><Trash2 className="w-3.5 h-3.5" /></button> : null}
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>

      <Modal isOpen={singleOpen} onClose={() => setSingleOpen(false)} title="เพิ่มคลิปลงคิว" subtitle="เลือกคลิปที่ตัดต่อเสร็จแล้ว แล้วกำหนดวันและเวลาโพสต์" maxWidth="max-w-2xl">
        <div className="space-y-4"><div className="space-y-2"><label className="text-xs font-bold text-slate-300">คลิป</label><select value={singleDraft.clip ? clipKey(singleDraft.clip) : ''} onChange={(event) => setSingleDraft((prev) => ({ ...prev, clip: availableClips.find((clip) => clipKey(clip) === event.target.value) || null }))} className="w-full px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-sm text-white"><option value="">เลือกคลิปที่ตัดต่อเสร็จแล้ว</option>{availableClips.map((clip) => <option key={clipKey(clip)} value={clipKey(clip)}>{clip.parentProduct?.name || 'ไม่ระบุสินค้า'} · {clip.hook_title || clip.project_name}</option>)}</select></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-3"><label className="space-y-1 text-xs font-bold text-slate-300">วันที่<input type="date" value={singleDraft.date} onChange={(event) => setSingleDraft((prev) => ({ ...prev, date: event.target.value }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" /></label><label className="space-y-1 text-xs font-bold text-slate-300">เวลา (รอบละ 5 นาที)<select value={singleDraft.time} onChange={(event) => setSingleDraft((prev) => ({ ...prev, time: event.target.value }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white font-mono">{timeOptions.map((time) => <option key={time} value={time}>{time}</option>)}</select></label></div><p className="text-[11px] text-slate-500">ระบบจะกันคลิปซ้ำและกันเวลาชนกันให้ก่อนบันทึก</p><div className="flex justify-end gap-2"><button type="button" onClick={() => setSingleOpen(false)} className="px-3 py-2 rounded-xl text-xs text-slate-300">ยกเลิก</button><button type="button" disabled={!singleDraft.clip || saving} onClick={saveSingle} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black disabled:opacity-50">บันทึกเข้าคิว</button></div></div>
      </Modal>

      <Modal isOpen={bulkOpen} onClose={() => setBulkOpen(false)} title="เพิ่มคลิปเป็นชุด" subtitle="เลือกหลายคลิป กำหนดเวลาเริ่มต้น และตรวจสอบตารางก่อนบันทึกพร้อมกัน" maxWidth="max-w-4xl">
        <div className="space-y-4"><div className="grid grid-cols-1 sm:grid-cols-3 gap-3"><label className="space-y-1 text-xs font-bold text-slate-300">เริ่มวันที่<input type="date" value={bulkDraft.date} onChange={(event) => setBulkDraft((prev) => ({ ...prev, date: event.target.value }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" /></label><label className="space-y-1 text-xs font-bold text-slate-300">เริ่มเวลา<select value={bulkDraft.time} onChange={(event) => setBulkDraft((prev) => ({ ...prev, time: event.target.value }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white font-mono">{timeOptions.map((time) => <option key={time} value={time}>{time}</option>)}</select></label><label className="space-y-1 text-xs font-bold text-slate-300">ระยะห่าง<select value={bulkDraft.interval} onChange={(event) => setBulkDraft((prev) => ({ ...prev, interval: Number(event.target.value) }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white"><option value="5">ทุก 5 นาที</option><option value="10">ทุก 10 นาที</option><option value="15">ทุก 15 นาที</option><option value="30">ทุก 30 นาที</option><option value="60">ทุก 1 ชั่วโมง</option></select></label></div><div className="grid grid-cols-1 lg:grid-cols-2 gap-4"><div className="rounded-2xl border border-white/[0.1] p-3 max-h-80 overflow-y-auto space-y-1"><div className="flex items-center justify-between mb-2"><span className="text-xs font-bold text-white">คลิปที่ตัดต่อเสร็จแล้ว</span><button type="button" onClick={() => setBulkSelected(availableClips)} className="text-[10px] text-cyan-300">เลือกทั้งหมด</button></div>{availableClips.length === 0 ? <p className="text-xs text-slate-500 py-8 text-center">ไม่มีคลิปที่ว่างสำหรับจัดคิว</p> : availableClips.map((clip) => { const key = clipKey(clip); const selected = bulkSelected.some((item) => clipKey(item) === key); return <label key={key} className="flex items-center gap-2 p-2 rounded-xl hover:bg-white/[0.05] cursor-pointer"><input type="checkbox" checked={selected} onChange={() => setBulkSelected((prev) => selected ? prev.filter((item) => clipKey(item) !== key) : [...prev, clip])} className="accent-cyan-400" /><span className="text-xs text-slate-200 truncate">{clip.parentProduct?.name || 'ไม่ระบุสินค้า'} · {clip.hook_title || clip.project_name}</span></label>; })}</div><div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.03] p-3 max-h-80 overflow-y-auto"><div className="flex items-center justify-between mb-2"><span className="text-xs font-bold text-white">ตัวอย่างคิว ({bulkPreview.length})</span><span className="text-[10px] text-slate-500">ลากในหน้าหลักเพื่อปรับวันภายหลัง</span></div>{bulkPreview.length === 0 ? <p className="text-xs text-slate-500 py-8 text-center">เลือกคลิปเพื่อดูวันที่และเวลาที่คำนวณ</p> : bulkPreview.map(({ clip, date, time }, index) => <div key={clipKey(clip)} className="flex items-center gap-2 py-2 border-b border-white/[0.06] last:border-0"><span className="w-5 h-5 rounded-full bg-cyan-400/15 text-cyan-200 text-[10px] flex items-center justify-center">{index + 1}</span><span className="text-[11px] text-white font-mono whitespace-nowrap">{date} {time}</span><span className="text-xs text-slate-400 truncate flex-1">{clip.hook_title || clip.project_name}</span><button type="button" disabled={index === 0} onClick={() => setBulkSelected((prev) => { const next = [...prev]; [next[index - 1], next[index]] = [next[index], next[index - 1]]; return next; })} className="p-1 rounded border border-white/[0.1] text-slate-400 disabled:opacity-25" title="??????????" aria-label="????????????????????????"><ChevronUp className="w-3.5 h-3.5" /></button><button type="button" disabled={index === bulkPreview.length - 1} onClick={() => setBulkSelected((prev) => { const next = [...prev]; [next[index], next[index + 1]] = [next[index + 1], next[index]]; return next; })} className="p-1 rounded border border-white/[0.1] text-slate-400 disabled:opacity-25" title="????????" aria-label="??????????????????????"><ChevronDown className="w-3.5 h-3.5" /></button></div>)}</div></div><div className="flex justify-end gap-2"><button type="button" onClick={() => setBulkOpen(false)} className="px-3 py-2 rounded-xl text-xs text-slate-300">ยกเลิก</button><button type="button" disabled={!bulkPreview.length || saving} onClick={saveBulk} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black disabled:opacity-50">บันทึกทั้งชุด</button></div></div>
      </Modal>

      <Modal isOpen={templateOpen} onClose={() => setTemplateOpen(false)} title="ตั้งค่าเวลารายสัปดาห์" subtitle="สัปดาห์จันทร์–อาทิตย์ · เวลาเหล่านี้ใช้เฉพาะจัดคิวอัตโนมัติ" maxWidth="max-w-4xl">
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-end gap-3">
            <label className="flex-1 text-xs font-bold text-slate-300">สัปดาห์ที่เริ่มวันจันทร์
              <input type="date" value={templateWeek} onChange={async (event) => { const week = weekStartForDate(event.target.value); setTemplateWeek(week); await loadTemplate(week); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" />
            </label>
            <div className="flex gap-2">
              <button type="button" disabled={templateBusy} onClick={copyPreviousTemplate} className="px-3 py-2 rounded-xl border border-white/[0.1] text-xs text-slate-200 flex items-center gap-1.5"><Copy className="w-3.5 h-3.5" />คัดลอกสัปดาห์ก่อน</button>
              <button type="button" disabled={templateBusy} onClick={resetTemplate} className="px-3 py-2 rounded-xl border border-white/[0.1] text-xs text-slate-200 flex items-center gap-1.5"><RotateCcw className="w-3.5 h-3.5" />คืนค่าเริ่มต้น</button>
            </div>
          </div>
          <div className="rounded-2xl border border-white/[0.1] overflow-x-auto">
            <div className="min-w-[620px]">
              <div className="grid grid-cols-[120px_76px_repeat(3,minmax(120px,1fr))] gap-2 px-3 py-2 text-[10px] text-slate-500 border-b border-white/[0.08]"><span>วัน</span><span>เปิดใช้</span>{DEFAULT_PRIMARY_TIMES.map((time) => <span key={time}>ช่วงที่ {time}</span>)}</div>
              {Object.entries(templateDraft.days).map(([index, day]) => <div key={index} className="grid grid-cols-[120px_76px_repeat(3,minmax(120px,1fr))] gap-2 items-center px-3 py-2 border-b border-white/[0.06] last:border-0"><span className="text-xs text-white font-bold">{['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์'][Number(index)]}</span><label className="flex items-center"><input type="checkbox" checked={day.enabled !== false} onChange={(event) => setTemplateDraft((prev) => ({ ...prev, days: { ...prev.days, [index]: { ...prev.days[index], enabled: event.target.checked } } }))} className="accent-cyan-400" /><span className="sr-only">เปิดใช้</span></label>{day.times.map((time, timeIndex) => <select key={`${index}-${timeIndex}`} value={time} onChange={(event) => setTemplateDraft((prev) => { const times = [...prev.days[index].times]; times[timeIndex] = event.target.value; return { ...prev, days: { ...prev.days, [index]: { ...prev.days[index], times } } }; })} className="px-2 py-2 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white font-mono">{primaryOptions.map((option) => <option key={option} value={option}>{option}</option>)}</select>)}</div>)}
            </div>
          </div>
          <p className="text-[11px] text-slate-500">ต้องเลือกเวลาไม่ซ้ำกัน 3 เวลา และเป็นรอบละ 5 นาที · การแก้เทมเพลตไม่เปลี่ยนคิวที่บันทึกไว้แล้ว</p>
          <div className="flex justify-end gap-2"><button type="button" onClick={() => setTemplateOpen(false)} className="px-3 py-2 rounded-xl text-xs text-slate-300">ยกเลิก</button><button type="button" disabled={templateBusy} onClick={saveTemplate} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black disabled:opacity-50">บันทึกเทมเพลต</button></div>
        </div>
      </Modal>

      <Modal isOpen={autofillOpen} onClose={() => setAutofillOpen(false)} title="จัดคิวอัตโนมัติ" subtitle="ดูตัวอย่างก่อนบันทึก · ระบบจะสุ่มสินค้าแบบไม่ซ้ำติดกัน และใช้คลิปที่ยังไม่อยู่ในคิวเท่านั้น" maxWidth="max-w-5xl">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2"><button type="button" onClick={() => chooseAutofillRange('today')} className={`px-3 py-2 rounded-xl text-xs font-bold ${autofillRange === 'today' ? 'bg-cyan-400 text-slate-950' : 'border border-white/[0.1] text-slate-200'}`}>วันนี้</button><button type="button" onClick={() => chooseAutofillRange('week')} className={`px-3 py-2 rounded-xl text-xs font-bold ${autofillRange === 'week' ? 'bg-cyan-400 text-slate-950' : 'border border-white/[0.1] text-slate-200'}`}>สัปดาห์นี้</button><button type="button" onClick={() => chooseAutofillRange('custom')} className={`px-3 py-2 rounded-xl text-xs font-bold ${autofillRange === 'custom' ? 'bg-cyan-400 text-slate-950' : 'border border-white/[0.1] text-slate-200'}`}>กำหนดช่วงเอง</button></div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"><label className="text-xs font-bold text-slate-300">เริ่มวันที่<input type="date" value={autofillStart} onChange={(event) => { setAutofillStart(event.target.value); setAutofillRange('custom'); setAutofillPreview(null); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" /></label><label className="text-xs font-bold text-slate-300">ถึงวันที่<input type="date" value={autofillEnd} onChange={(event) => { setAutofillEnd(event.target.value); setAutofillRange('custom'); setAutofillPreview(null); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" /></label><label className="text-xs font-bold text-slate-300">สินค้า<select value={autofillProduct} onChange={(event) => { setAutofillProduct(event.target.value); setAutofillPreview(null); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white"><option value="all">สินค้าทั้งหมด</option>{productOptions.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label><label className="text-xs font-bold text-slate-300">จำนวนคลิป (ว่าง = ทั้งหมด)<input type="number" min="1" max="10000" value={autofillLimit} onChange={(event) => { setAutofillLimit(event.target.value); setAutofillPreview(null); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" /></label></div>
          <div className="flex items-center justify-between gap-3"><p className="text-[11px] text-slate-500">คิวจะเริ่มหลังเวลาล่าสุดที่มีอยู่ และข้ามช่วงเวลาที่ผ่านไปแล้ว</p><button type="button" disabled={autofillBusy || !availableClips.length} onClick={runAutofillPreview} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black flex items-center gap-1.5 disabled:opacity-50"><Shuffle className="w-4 h-4" />{autofillBusy ? 'กำลังคำนวณ' : 'สร้างตัวอย่างคิว'}</button></div>
          <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.03] p-3 max-h-96 overflow-y-auto">{!autofillPreview ? <p className="py-12 text-center text-xs text-slate-500">กดสร้างตัวอย่างเพื่อดูวัน เวลา และลำดับคลิปก่อนบันทึก</p> : autofillPreview.items?.length ? <div className="space-y-1">{autofillPreview.items.map((item, index) => <div key={`${item.video_path}-${item.scheduled_at}`} className="flex items-center gap-2 py-2 border-b border-white/[0.06] last:border-0"><span className="w-6 h-6 rounded-full bg-cyan-400/15 text-cyan-100 text-[10px] flex items-center justify-center">{index + 1}</span><span className="text-xs font-mono text-white whitespace-nowrap">{item.scheduled_at.slice(0, 16).replace('T', ' ')}</span><span className="text-xs text-cyan-100 truncate flex-1">{item.product_name || 'ไม่ระบุสินค้า'} · {item.hook_title || item.project_name || item.video_path}</span></div>)}{autofillPreview.reason && <p className="text-xs text-amber-200 mt-3">{autofillPreview.reason}</p>}</div> : <div className="py-10 text-center"><p className="text-sm text-slate-300">ยังจัดคิวไม่ได้</p><p className="text-xs text-slate-500 mt-1">{autofillPreview.reason || 'ไม่มีรายการที่พร้อม'}</p></div>}</div>
          {autofillPreview?.skipped_invalid?.length > 0 && <p className="text-xs text-red-200">ข้ามไฟล์ที่ตรวจสอบไม่ได้ {autofillPreview.skipped_invalid.length} รายการ</p>}
          {autofillPreview?.skipped_slots > 0 && <p className="text-xs text-amber-200">เว้นช่วงเวลาอีก {autofillPreview.skipped_slots} ช่อง เพราะไม่มีคลิปหรือช่วงเวลาที่ว่าง</p>}
          <div className="flex justify-end gap-2"><button type="button" onClick={() => setAutofillOpen(false)} className="px-3 py-2 rounded-xl text-xs text-slate-300">ยกเลิก</button><button type="button" disabled={!autofillPreview?.items?.length || autofillBusy} onClick={saveAutofill} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black disabled:opacity-50">บันทึกคิวที่แสดง</button></div>
        </div>
      </Modal>

      <Modal isOpen={requeueOpen} onClose={() => setRequeueOpen(false)} title="จัดคิวคลิปที่เลยกำหนดใหม่" subtitle="ระบบจะอัปเดตรายการเดิมและไม่สร้างคลิปซ้ำ" maxWidth="max-w-xl">
        <div className="space-y-4"><div className="rounded-xl border border-red-400/20 bg-red-500/[0.06] p-3 text-xs text-red-100">{requeueTarget?.product_name || 'คลิป'} · {requeueTarget?.hook_title || requeueTarget?.video_path}</div>{requeueLoading && <p className="text-xs text-cyan-200">กำลังหาช่องว่างถัดไปตามเทมเพลต...</p>}<div className="grid grid-cols-1 sm:grid-cols-2 gap-3"><label className="space-y-1 text-xs font-bold text-slate-300">วันที่<input type="date" value={requeueDraft.date || ''} disabled={requeueLoading} onChange={(event) => setRequeueDraft((prev) => ({ ...prev, date: event.target.value }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white disabled:opacity-50" /></label><label className="space-y-1 text-xs font-bold text-slate-300">เวลา<input type="time" step="300" value={requeueDraft.time || ''} disabled={requeueLoading} onChange={(event) => setRequeueDraft((prev) => ({ ...prev, time: event.target.value }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white font-mono disabled:opacity-50" /></label></div><div className="flex justify-end gap-2"><button type="button" onClick={() => setRequeueOpen(false)} className="px-3 py-2 rounded-xl text-xs text-slate-300">ยกเลิก</button><button type="button" disabled={saving || requeueLoading || !requeueDraft.date || !requeueDraft.time} onClick={saveRequeue} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black disabled:opacity-50">บันทึกคิวใหม่</button></div></div>
      </Modal>
    </div>
  );
}
