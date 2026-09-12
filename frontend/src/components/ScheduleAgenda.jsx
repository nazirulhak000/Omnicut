import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Archive, Calendar, CalendarDays, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Clock, Copy, GripVertical, Image as ImageIcon, Layers, List, Plus, RefreshCw, Rocket, RotateCcw, Settings2, Shuffle, Trash2 } from 'lucide-react';
import { Modal, Badge } from './ui';
import { commitScheduleAutofill, copyScheduleTemplate, createScheduleQueue, getScheduleQueue, getScheduleTemplate, prepareScheduleQueue, previewScheduleAutofill, removeScheduleQueue, resetScheduleTemplate, saveScheduleTemplate, updateScheduleQueue } from '../api';
import { addDays, buildScheduleIso, dateOnly, DEFAULT_PRIMARY_TIMES, groupScheduleItems, localParts, mergeScheduleDraft, nextTemplateSlotAfterLatest, parseDateOnly, primaryTimeOptions, PROJECT_TIME_ZONE, scheduleTimeOptions, templateForWeek, toLocalDateTime, WEEKDAY_LABELS, weekStartForDate } from '../lib/scheduleQueue';

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
  if (clip?.export_id) return `export:${String(clip.export_id)}`;
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
    export_id: clip.export_id || null,
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
  if (item?.export_id) return `export:${String(item.export_id)}`;
  return String(item?.video_path || '').replaceAll('\\', '/').toLowerCase();
}

function clipToAutofillPayload(clip) {
  const product = clip.parentProduct || {};
  return {
    video_path: clip.video_url,
    export_id: clip.export_id || null,
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
  const [viewMode, setViewMode] = useState('list');
  const [calendarWeekStart, setCalendarWeekStart] = useState(() => weekStartForDate(dateOnly()));
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
  const [postedOpen, setPostedOpen] = useState(false);
  // Posted history never gets pruned server-side -- window it here so
  // opening this modal after a year of daily posts doesn't mount hundreds
  // of rows at once.
  const POSTED_MODAL_PAGE_SIZE = 50;
  const [postedVisibleCount, setPostedVisibleCount] = useState(POSTED_MODAL_PAGE_SIZE);
  useEffect(() => {
    if (postedOpen) setPostedVisibleCount(POSTED_MODAL_PAGE_SIZE);
  }, [postedOpen]);
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

  const queuedKeys = useMemo(() => new Set(queue.map(queueKey)), [queue]);
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
  // Posted items are a permanent record (matches how the rest of this app
  // treats "posted" as sealed proof, never demoted or deleted), but they
  // don't belong mixed into the active daily run sheet -- once a clip is
  // actually posted there's nothing left to schedule, so it just clutters
  // "today's queue" instead of reading as done. Split them into their own
  // collapsed history list instead of showing them (un-removable) alongside
  // clips still waiting to go out.
  const activeQueue = useMemo(() => queue.filter((item) => item.status !== 'posted'), [queue]);
  const postedQueue = useMemo(
    () => queue.filter((item) => item.status === 'posted').sort((a, b) => new Date(b.scheduled_at) - new Date(a.scheduled_at)),
    [queue],
  );
  const grouped = useMemo(() => groupScheduleItems(activeQueue), [activeQueue]);
  const dates = Object.keys(grouped);
  const calendarDays = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = addDays(calendarWeekStart, i);
      const dayDateObj = parseDateOnly(d);
      return {
        date: d,
        dayName: WEEKDAY_LABELS[i],
        dayNumber: dayDateObj.getUTCDate(),
        monthLabel: new Intl.DateTimeFormat('th-TH', { month: 'short' }).format(dayDateObj),
        isToday: d === dateOnly(),
        items: grouped[d] || [],
      };
    });
  }, [calendarWeekStart, grouped]);

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
                <h2 className="text-base sm:text-lg font-black text-white">คิวโพสต์หลายวัน</h2>
                <p className="text-xs text-slate-400 mt-1">เรียงตามวันที่และเวลาในเขต Asia/Bangkok · รอบละ 5 นาที · {activeQueue.length} คลิปในคิว</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center rounded-xl bg-white/[0.04] p-1 border border-white/[0.08] mr-1">
                <button
                  type="button"
                  onClick={() => setViewMode('list')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors ${
                    viewMode === 'list'
                      ? 'bg-cyan-400 text-slate-950 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <List className="w-3.5 h-3.5" />
                  รายการ
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('calendar')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors ${
                    viewMode === 'calendar'
                      ? 'bg-cyan-400 text-slate-950 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Calendar className="w-3.5 h-3.5" />
                  ปฏิทินสัปดาห์
                </button>
              </div>
              <button type="button" onClick={openAutofill} className="px-3.5 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black flex items-center gap-1.5 hover:brightness-110"><Shuffle className="w-4 h-4" />จัดคิวอัตโนมัติ</button>
              <button type="button" onClick={openTemplate} className="px-3.5 py-2 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.05] text-cyan-100 text-xs font-bold flex items-center gap-1.5 hover:bg-cyan-400/[0.12]"><Settings2 className="w-4 h-4" />ตั้งค่าเวลารายสัปดาห์</button>
              <button type="button" onClick={openSingle} className="px-3.5 py-2 rounded-xl border border-white/[0.12] bg-white/[0.05] text-white text-xs font-bold flex items-center gap-1.5 hover:bg-white/[0.1]"><Plus className="w-4 h-4" />เพิ่มคลิป</button>
              <button type="button" onClick={openBulk} className="px-3.5 py-2 rounded-xl border border-white/[0.12] bg-white/[0.05] text-white text-xs font-bold flex items-center gap-1.5 hover:bg-white/[0.1]"><Layers className="w-4 h-4" />เพิ่มเป็นชุด</button>
              {postedQueue.length > 0 && (
                <button type="button" onClick={() => setPostedOpen(true)} className="px-3.5 py-2 rounded-xl border border-emerald-400/30 bg-emerald-400/[0.08] text-emerald-200 text-xs font-bold flex items-center gap-1.5 hover:bg-emerald-400/[0.15]" title="เปิดดูคลิปที่โพสต์แล้วทั้งหมดในคิวนี้"><Archive className="w-4 h-4" />โพสต์แล้ว ({postedQueue.length})</button>
              )}
              <button type="button" onClick={loadQueue} className="p-2 rounded-xl border border-white/[0.1] text-slate-300 hover:text-white" aria-label="รีเฟรชคิว"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></button>
            </div>
          </div>
        </div>

        {loading ? <div className="p-10 text-center text-sm text-slate-500">กำลังโหลดคิวโพสต์...</div> : viewMode === 'calendar' ? (
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-3 border-b border-white/[0.06] bg-black/25">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCalendarWeekStart((prev) => addDays(prev, -7))}
                  className="p-1.5 rounded-xl border border-white/[0.1] text-slate-400 hover:text-white hover:bg-white/[0.05]"
                  title="สัปดาห์ก่อนหน้า"
                  aria-label="สัปดาห์ก่อนหน้า"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setCalendarWeekStart(weekStartForDate(dateOnly()))}
                  className="px-2.5 py-1 rounded-xl border border-cyan-400/25 bg-cyan-400/[0.05] text-cyan-200 text-xs font-bold hover:bg-cyan-400/[0.12]"
                >
                  สัปดาห์นี้
                </button>
                <button
                  type="button"
                  onClick={() => setCalendarWeekStart((prev) => addDays(prev, 7))}
                  className="p-1.5 rounded-xl border border-white/[0.1] text-slate-400 hover:text-white hover:bg-white/[0.05]"
                  title="สัปดาห์ถัดไป"
                  aria-label="สัปดาห์ถัดไป"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <span className="text-xs font-black text-white ml-2">
                  {calendarDays[0]?.dayNumber} {calendarDays[0]?.monthLabel} – {calendarDays[6]?.dayNumber} {calendarDays[6]?.monthLabel} ({calendarWeekStart})
                </span>
              </div>
              <span className="text-[11px] text-cyan-300/80 bg-cyan-400/[0.06] border border-cyan-400/15 rounded-full px-3 py-1 w-fit">
                ลากการ์ดคลิปเพื่อเลื่อนข้ามวัน หรือกดเพิ่มคลิปในแต่ละวันได้ทันที
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3 p-4 sm:p-5">
              {calendarDays.map((day) => (
                <div
                  key={day.date}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => onDropDate(day.date)}
                  className={`rounded-2xl border transition-all flex flex-col min-h-[340px] overflow-hidden ${
                    day.isToday
                      ? 'border-cyan-400/40 bg-cyan-500/[0.03] shadow-[0_0_20px_rgba(37,244,238,0.04)]'
                      : 'border-white/[0.08] bg-black/20'
                  }`}
                >
                  <div className={`p-3 border-b flex items-center justify-between ${
                    day.isToday ? 'border-cyan-400/25 bg-cyan-400/[0.08]' : 'border-white/[0.06] bg-white/[0.02]'
                  }`}>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-black text-white">{day.dayName}</span>
                        {day.isToday && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-black bg-cyan-400 text-slate-950">
                            วันนี้
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400">{day.dayNumber} {day.monthLabel}</span>
                    </div>
                    <span className="text-[10px] font-mono text-cyan-300 font-bold bg-white/[0.05] px-1.5 py-0.5 rounded-md">
                      {day.items.length}
                    </span>
                  </div>

                  <div className="p-2 space-y-2 flex-1 overflow-y-auto max-h-[520px]">
                    {day.items.map((item) => {
                      const parts = localParts(item.scheduled_at);
                      const clip = readyClips.find((candidate) => clipKey(candidate) === queueKey(item));
                      const coverPath = coverValue(item, clip);
                      const hasCover = Boolean(coverPath);
                      const overdue = item.is_overdue || (item.status === 'planned' && new Date(item.scheduled_at).getTime() < Date.now());

                      return (
                        <div
                          key={item.id}
                          draggable={item.status === 'planned'}
                          onDragStart={() => setDraggedId(item.id)}
                          className={`p-2.5 rounded-xl border bg-slate-900/90 shadow-sm transition-all text-left group ${
                            item.status === 'planned' ? 'cursor-grab hover:border-cyan-400/40 hover:bg-slate-900' : 'cursor-default'
                          } ${overdue ? 'border-red-500/40' : 'border-white/[0.08]'}`}
                        >
                          <div className="flex items-center justify-between gap-1 mb-1.5">
                            <span className="text-[10px] font-mono font-bold text-cyan-300 flex items-center gap-1">
                              <Clock className="w-3 h-3 text-cyan-400" />
                              {parts.time}
                            </span>
                            <Badge className={`text-[9px] px-1.5 py-0 ${STATUS_STYLES[item.status] || STATUS_STYLES.planned}`}>
                              {STATUS_LABELS[item.status] || item.status}
                            </Badge>
                          </div>

                          <div className="flex items-start gap-2 mb-2">
                            <button
                              type="button"
                              onClick={() => clip?.video_url && onPreviewVideo?.(clip.video_url, clip)}
                              className="w-10 h-14 rounded-lg overflow-hidden bg-black border border-white/[0.1] flex-shrink-0 relative group/thumb"
                            >
                              {coverSrc(coverPath) ? (
                                <img src={coverSrc(coverPath)} alt="" className="w-full h-full object-cover" />
                              ) : (
                                <video src={`/api/media/${item.video_path}`} muted className="w-full h-full object-cover" />
                              )}
                              <span className="absolute inset-0 bg-black/60 opacity-0 group-hover/thumb:opacity-100 transition-opacity flex items-center justify-center text-[8px] text-white">
                                ดู
                              </span>
                            </button>
                            <div className="min-w-0 flex-1">
                              <p className="text-[11px] font-bold text-slate-200 line-clamp-2 leading-snug">
                                {item.hook_title || item.product_name || item.video_path}
                              </p>
                              <p className="text-[9px] text-slate-500 truncate mt-0.5">
                                {item.product_name || 'ไม่ระบุสินค้า'}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center justify-between pt-1 border-t border-white/[0.06] text-[10px]">
                            <div className="flex items-center gap-1">
                              {item.status === 'planned' || item.status === 'failed' ? (
                                <button
                                  type="button"
                                  onClick={() => prepareItem(item)}
                                  className="p-1 rounded bg-cyan-400/15 hover:bg-cyan-400/25 text-cyan-300"
                                  title="เตรียมให้ Extension"
                                  aria-label="เตรียมให้ Extension"
                                >
                                  <Rocket className="w-3 h-3" />
                                </button>
                              ) : item.status === 'ready_for_extension' ? (
                                <button
                                  type="button"
                                  onClick={() => resetForMove(item)}
                                  className="px-1.5 py-0.5 rounded border border-amber-400/25 text-amber-200 text-[9px]"
                                  title="รีเซ็ตเพื่อย้าย"
                                >
                                  รีเซ็ต
                                </button>
                              ) : null}
                              {clip && onOpenCoverStudio && (
                                <button
                                  type="button"
                                  onClick={() => onOpenCoverStudio(clip)}
                                  className={`p-1 rounded border ${
                                    hasCover ? 'border-emerald-400/40 text-emerald-300' : 'border-white/[0.1] text-slate-600'
                                  }`}
                                  title="ปกคลิป"
                                  aria-label="ปกคลิป"
                                >
                                  <ImageIcon className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                            {item.status === 'planned' && (
                              <button
                                type="button"
                                onClick={() => removeItem(item)}
                                className="p-1 text-slate-600 hover:text-red-400"
                                title="นำออกจากคิว"
                                aria-label="นำออกจากคิว"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {day.items.length === 0 && (
                      <div className="h-full min-h-[140px] flex flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] p-3 text-center">
                        <span className="text-[10px] text-slate-600">ไม่มีคลิป</span>
                        <span className="text-[9px] text-slate-600 mt-0.5">ลากคลิปมาวางได้</span>
                      </div>
                    )}
                  </div>

                  <div className="p-2 pt-0">
                    <button
                      type="button"
                      onClick={() => {
                        setSingleDraft({ clip: null, date: day.date, time: '12:30' });
                        setSingleOpen(true);
                      }}
                      className="w-full py-1.5 rounded-xl border border-white/[0.08] hover:border-cyan-400/30 hover:bg-cyan-400/[0.05] text-[10px] text-slate-400 hover:text-cyan-200 font-bold flex items-center justify-center gap-1 transition-colors"
                    >
                      <Plus className="w-3 h-3" />
                      เพิ่มคลิป
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : dates.length === 0 ? (
          <div className="p-12 text-center"><CalendarDays className="w-8 h-8 mx-auto text-slate-600 mb-3" /><p className="text-sm text-slate-300 font-bold">ยังไม่มีคลิปในคิว</p><p className="text-xs text-slate-500 mt-1">เพิ่มคลิปเดี่ยวหรือเลือกหลายคลิปเพื่อวางแผนล่วงหน้าได้เลย</p></div>
        ) : (
          <div className="p-4 sm:p-5 space-y-4">
            {dates.map((date) => (
              <section key={date} onDragOver={(event) => event.preventDefault()} onDrop={() => onDropDate(date)} className="rounded-2xl border border-white/[0.08] bg-black/20 overflow-hidden">
                <div className="px-4 py-3 flex items-center justify-between bg-white/[0.035] border-b border-white/[0.08]"><div><h3 className="text-sm font-black text-white">{thaiDate(date)}</h3><p className="text-[11px] text-slate-500 mt-0.5">{date} · {grouped[date].length} คลิป</p></div><span className="text-[10px] text-cyan-300 border border-cyan-400/20 rounded-full px-2 py-1">ลากคลิปมาวางเพื่อย้ายวัน</span></div>
                <div className="divide-y divide-white/[0.06]">
                  {grouped[date].map((item) => {
                    const parts = localParts(item.scheduled_at);
                    const clip = readyClips.find((candidate) => clipKey(candidate) === queueKey(item));
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

      <Modal
        isOpen={postedOpen}
        onClose={() => setPostedOpen(false)}
        title="คลิปที่โพสต์แล้ว"
        subtitle="เก็บไว้เป็นประวัติ ไม่นับรวมในคิวที่ต้องจัดการต่อ"
        maxWidth="max-w-2xl"
      >
        <div className="space-y-1 max-h-[60vh] overflow-y-auto">
          {postedQueue.length === 0 ? (
            <p className="py-8 text-center text-xs text-slate-500">ยังไม่มีคลิปที่โพสต์แล้วในคิวนี้</p>
          ) : (
            <>
              {postedQueue.slice(0, postedVisibleCount).map((item) => (
                <div key={item.id} className="flex items-center gap-3 py-2.5 border-b border-white/[0.06] last:border-0">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-white truncate">{item.product_name || 'ไม่ระบุสินค้า'}</span>
                      <Badge className={STATUS_STYLES.posted}>{STATUS_LABELS.posted}</Badge>
                    </div>
                    <p className="text-[11px] text-cyan-200 truncate mt-0.5">{item.hook_title || item.project_name || item.video_path}</p>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500 whitespace-nowrap">{item.scheduled_at?.slice(0, 16).replace('T', ' ')}</span>
                </div>
              ))}
              {postedVisibleCount < postedQueue.length && (
                <button
                  type="button"
                  onClick={() => setPostedVisibleCount(c => c + POSTED_MODAL_PAGE_SIZE)}
                  className="w-full py-2.5 text-xs font-bold text-cyan-300 hover:text-cyan-200 cursor-pointer"
                >
                  โหลดเพิ่ม ({postedQueue.length - postedVisibleCount} รายการที่เหลือ)
                </button>
              )}
            </>
          )}
        </div>
      </Modal>
    </div>
  );
}
