import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Archive, Calendar, CalendarDays, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Clock, Copy, GripVertical, Image as ImageIcon, Layers, List, MoreHorizontal, Plus, RefreshCw, Rocket, RotateCcw, Search, Settings2, Shuffle, Trash2 } from 'lucide-react';
import { Modal, Badge } from './ui';
import PaginationControls from './PaginationControls';
import PublicationReviewModal from './PublicationReviewModal.jsx';
import { useChannel } from '../context/ChannelContext.jsx';
import { commitScheduleAutofill, copyScheduleTemplate, createScheduleQueue, getScheduleQueue, getScheduleTemplate, prepareScheduleQueue, previewScheduleAutofill, removeScheduleQueue, resetScheduleTemplate, saveScheduleTemplate, updateScheduleQueue } from '../api';
import { addDays, buildScheduleIso, dateOnly, DEFAULT_PRIMARY_TIMES, estimateQueueCoverage, groupScheduleItems, localParts, mergeScheduleDraft, nextTemplateSlotAfterLatest, parseDateOnly, primaryTimeOptions, PROJECT_TIME_ZONE, scheduleTimeOptions, templateForWeek, toLocalDateTime, WEEKDAY_LABELS, weekStartForDate } from '../lib/scheduleQueue';
import { getStylePreset } from '../lib/stylePresetCatalog';
import { useChannelDraft } from '../hooks/useChannelDraft.js';
import { toMediaUrl } from '../lib/mediaUrl.js';

const STATUS_LABELS = {
  planned: 'รอจัดส่ง',
  ready_for_extension: 'พร้อมทำใน Extension',
  awaiting_post: 'รอกดโพสต์',
  scheduled_on_platform: 'TikTok รับตั้งเวลาแล้ว',
  confirmation_unknown: 'รอตรวจผลจาก TikTok',
  posted: 'โพสต์แล้ว',
  failed: 'ผิดพลาด',
};

const STATUS_STYLES = {
  planned: 'text-amber-200 bg-amber-500/10 border-amber-500/25',
  ready_for_extension: 'text-cyan-200 bg-cyan-500/10 border-cyan-500/25',
  awaiting_post: 'text-violet-200 bg-violet-500/10 border-violet-500/25',
  scheduled_on_platform: 'text-blue-200 bg-blue-500/10 border-blue-500/25',
  confirmation_unknown: 'text-amber-200 bg-amber-500/10 border-amber-500/25',
  posted: 'text-emerald-200 bg-emerald-500/10 border-emerald-500/25',
  failed: 'text-red-200 bg-red-500/10 border-red-500/25',
};

function clipKey(clip) {
  if (clip?.export_id) return `export:${String(clip.export_id)}`;
  return String(clip?.video_url || '').replaceAll('\\', '/').toLowerCase();
}

function coverSrc(path) {
  return toMediaUrl(path);
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
  const stylePreset = clip.style_preset || clip.stylePreset || product.style_preset || product.stylePreset;
  const hookColor = stylePreset ? (clip.hook_color || clip.hookColor || getStylePreset(stylePreset).hookColor) : null;
  return {
    video_path: clip.video_url,
    scheduled_at: scheduledAt,
    export_id: clip.export_id || null,
    product_id: product.id || null,
    angle_id: clip.angle_id || null,
    product_name: product.name || clip.product_name || null,
    project_name: clip.project_name || null,
    hook_title: clip.hook_title || null,
    style_preset: stylePreset || null,
    hook_color: hookColor || null,
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
  const stylePreset = clip.style_preset || clip.stylePreset || product.style_preset || product.stylePreset;
  const hookColor = stylePreset ? (clip.hook_color || clip.hookColor || getStylePreset(stylePreset).hookColor) : null;
  return {
    video_path: clip.video_url,
    export_id: clip.export_id || null,
    product_id: product.id || clip.product_id || null,
    angle_id: clip.angle_id || null,
    product_name: product.name || clip.product_name || null,
    project_name: clip.project_name || null,
    hook_title: clip.hook_title || null,
    style_preset: stylePreset || null,
    hook_color: hookColor || null,
    cover_path: clip.cover_path || null,
    cover_url: clip.cover_url || null,
    caption: clip.tiktok_caption || clip.hook_title || '',
    hashtags: clip.tiktok_hashtags || '',
    tiktok_product_id: product.tiktok_product_id || clip.tiktok_product_id || null,
  };
}

function resolveClipHookColor(clip) {
  if (clip.hook_color || clip.hookColor) return String(clip.hook_color || clip.hookColor).trim().toUpperCase();
  const stylePreset = clip.style_preset || clip.stylePreset || clip.parentProduct?.style_preset || clip.parentProduct?.stylePreset;
  if (stylePreset) {
    const preset = getStylePreset(stylePreset);
    return String(preset?.hookColor || preset?.accentColor || '#FFE600').trim().toUpperCase();
  }
  return null;
}

function resolveRowHookColor(row) {
  if (row.hook_color) return String(row.hook_color).trim().toUpperCase();
  if (row.style_preset) {
    const preset = getStylePreset(row.style_preset);
    return String(preset?.hookColor || preset?.accentColor || '#FFE600').trim().toUpperCase();
  }
  return null;
}

function resolveClipProductKey(clip) {
  const p = clip.parentProduct || {};
  return String(p.id || clip.product_id || p.name || clip.product_name || 'other').trim().toLowerCase();
}

function resolveRowProductKey(row) {
  return String(row.product_id || row.product_name || 'other').trim().toLowerCase();
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
  const channel = useChannel();
  const [publicationReview, setPublicationReview] = useState(null);
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [singleOpen, setSingleOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [singleDraft, setSingleDraft] = useState({ clip: null, ...nextSlot() });
  const [bulkSelected, setBulkSelected] = useState([]);
  const [bulkDraft, setBulkDraft] = useState({ ...nextSlot(), interval: 5, mode: 'daily', autoCount: 5, filterProduct: 'all' });
  const [saving, setSaving] = useState(false);
  const [draggedId, setDraggedId] = useState(null);
  const [viewMode, setViewMode] = useState('list');
  const [calendarWeekStart, setCalendarWeekStart] = useState(() => weekStartForDate(dateOnly()));
  const timeOptions = useMemo(() => scheduleTimeOptions(), []);
  const currentTemplateWeek = useMemo(() => weekStartForDate(dateOnly()), []);
  const [templateOpen, setTemplateOpen] = useState(false);
  const [templateWeek, setTemplateWeek] = useState(currentTemplateWeek);
  const [templateDraft, setTemplateDraft] = useState(defaultTemplateDraft(currentTemplateWeek));
  const [capacityTemplate, setCapacityTemplate] = useState(() => defaultTemplateDraft(currentTemplateWeek));
  const [templateBusy, setTemplateBusy] = useState(false);
  const [autofillOpen, setAutofillOpen] = useState(false);
  const [autofillRange, setAutofillRange] = useState('today');
  const [autofillStart, setAutofillStart] = useState(dateOnly());
  const [autofillEnd, setAutofillEnd] = useState(dateOnly());
  const [autofillProduct, setAutofillProduct] = useState('all');
  const [autofillUseStats, setAutofillUseStats] = useState(true);
  const [autofillLimit, setAutofillLimit] = useState('');
  const [autofillPreview, setAutofillPreview] = useState(null);
  const [autofillBusy, setAutofillBusy] = useState(false);
  const [requeueOpen, setRequeueOpen] = useState(false);
  const [requeueTarget, setRequeueTarget] = useState(null);
  const [requeueDraft, setRequeueDraft] = useState({ date: '', time: '' });
  const [requeueLoading, setRequeueLoading] = useState(false);
  const [postedOpen, setPostedOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [bulkRemoving, setBulkRemoving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFilter, setDateFilter] = useState('all');
  const [productFilter, setProductFilter] = useState('all');
  // Posted history never gets pruned server-side -- window it here so
  // opening this modal after a year of daily posts doesn't mount hundreds
  // of rows at once.
  const POSTED_MODAL_PAGE_SIZE = 20;
  const [postedPage, setPostedPage] = useState(1);
  const [postedPageSize, setPostedPageSize] = useState(POSTED_MODAL_PAGE_SIZE);
  const postedQueue = useMemo(
    () => queue.filter((item) => item.status === 'posted').sort((a, b) => new Date(b.scheduled_at) - new Date(a.scheduled_at)),
    [queue],
  );
  useEffect(() => {
    if (postedOpen) setPostedPage(1);
  }, [postedOpen]);
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(postedQueue.length / postedPageSize));
    setPostedPage((page) => Math.min(page, totalPages));
  }, [postedQueue.length, postedPageSize]);
  const scheduleDrafts = useRef(new Map());
  const scheduleRequestIds = useRef(new Map());
  const requeueRequestId = useRef(0);
  const templateRequestId = useRef(0);
  const primaryOptions = useMemo(() => primaryTimeOptions(), []);
  const singleController = useChannelDraft(singleDraft, {
    save: value => persistSingle(value),
    reset: value => { setSingleDraft(value); setSingleOpen(false); },
  });
  const bulkController = useChannelDraft({ draft: bulkDraft, selected: bulkSelected }, {
    save: value => persistBulk(value),
    reset: value => { setBulkDraft(value.draft); setBulkSelected(value.selected); setBulkOpen(false); },
  });
  const templateController = useChannelDraft(templateDraft, {
    save: value => persistTemplate(value),
    reset: value => { setTemplateDraft(value); setTemplateWeek(value.week_start); setTemplateOpen(false); },
  });
  const requeueController = useChannelDraft({ targetId: requeueTarget?.id || null, ...requeueDraft }, {
    save: value => persistRequeue(value),
    reset: value => { setRequeueDraft({ date: value.date, time: value.time }); setRequeueOpen(false); },
  });

  const loadQueue = async () => {
    setLoading(true);
    try {
      const response = await getScheduleQueue();
      setQueue(response.items || []);
      setSelectedIds(new Set());
      scheduleDrafts.current.clear();
      scheduleRequestIds.current.clear();
    } catch (error) {
      showToast?.(`โหลดคิวไม่สำเร็จ: ${error.response?.data?.detail || error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadQueue(); }, []);

  useEffect(() => {
    let cancelled = false;
    getScheduleTemplate(currentTemplateWeek)
      .then((response) => {
        if (!cancelled) setCapacityTemplate(templateForWeek(response, currentTemplateWeek));
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [currentTemplateWeek]);

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

  const activeProductOptions = useMemo(() => {
    const map = new Map();
    activeQueue.forEach((item) => {
      const key = resolveRowProductKey(item);
      const name = item.product_name || 'ไม่ระบุสินค้า';
      if (!map.has(key)) {
        map.set(key, { key, name, count: 0 });
      }
      map.get(key).count += 1;
    });
    return Array.from(map.values()).sort((a, b) => b.count - a.count);
  }, [activeQueue]);

  const dailyAnalysis = useMemo(() => {
    const fullGrouped = groupScheduleItems(activeQueue);
    const map = {};

    Object.entries(fullGrouped).forEach(([date, items]) => {
      const timeCounts = {};
      items.forEach((item) => {
        const t = localParts(item.scheduled_at).time;
        timeCounts[t] = (timeCounts[t] || 0) + 1;
      });
      const duplicateTimes = new Set(Object.keys(timeCounts).filter((t) => timeCounts[t] > 1));

      const productCounts = {};
      items.forEach((item) => {
        const p = resolveRowProductKey(item);
        if (p && p !== 'other') {
          productCounts[p] = (productCounts[p] || 0) + 1;
        }
      });
      const duplicateProducts = new Set(Object.keys(productCounts).filter((p) => productCounts[p] > 1));

      const colors = [];
      const colorCounts = {};
      items.forEach((item) => {
        const c = resolveRowHookColor(item);
        if (c) {
          colors.push(c);
          colorCounts[c] = (colorCounts[c] || 0) + 1;
        }
      });
      const duplicateColors = new Set(Object.keys(colorCounts).filter((c) => colorCounts[c] > 1));

      map[date] = {
        itemsCount: items.length,
        duplicateTimes,
        duplicateProducts,
        duplicateColors,
        uniqueColors: Array.from(new Set(colors)),
        hasTimeConflict: duplicateTimes.size > 0,
        hasProductConflict: duplicateProducts.size > 0,
        hasColorConflict: duplicateColors.size > 0,
      };
    });

    return map;
  }, [activeQueue]);

  const filteredActiveQueue = useMemo(() => {
    const today = dateOnly();
    const max7 = addDays(today, 7);
    const max30 = addDays(today, 30);
    const q = searchQuery.trim().toLowerCase();

    return activeQueue.filter((item) => {
      const parts = localParts(item.scheduled_at);
      if (dateFilter === 'today' && parts.date !== today) return false;
      if (dateFilter === '7days' && (parts.date < today || parts.date > max7)) return false;
      if (dateFilter === '30days' && (parts.date < today || parts.date > max30)) return false;

      if (productFilter !== 'all') {
        const pKey = resolveRowProductKey(item);
        if (pKey !== productFilter) return false;
      }

      if (q) {
        const pName = (item.product_name || '').toLowerCase();
        const hook = (item.hook_title || '').toLowerCase();
        const proj = (item.project_name || '').toLowerCase();
        const path = (item.video_path || '').toLowerCase();
        if (!pName.includes(q) && !hook.includes(q) && !proj.includes(q) && !path.includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [activeQueue, searchQuery, dateFilter, productFilter]);

  const grouped = useMemo(() => groupScheduleItems(filteredActiveQueue), [filteredActiveQueue]);
  const dates = Object.keys(grouped);
  const todayKey = dateOnly();
  const todayQueue = useMemo(
    () => activeQueue
      .filter((item) => localParts(item.scheduled_at).date === todayKey)
      .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at)),
    [activeQueue, todayKey],
  );
  const nextToday = todayQueue.find((item) => new Date(item.scheduled_at).getTime() >= Date.now());
  const overdueTodayCount = todayQueue.filter((item) => item.status === 'planned' && new Date(item.scheduled_at).getTime() < Date.now()).length;
  const selectableQueue = useMemo(() => activeQueue.filter((item) => item.status === 'planned'), [activeQueue]);
  const queueEndDate = useMemo(
    () => activeQueue.reduce((latest, item) => {
      const date = localParts(item.scheduled_at).date;
      return date > latest ? date : latest;
    }, ''),
    [activeQueue],
  );
  const queueEndWeekStart = queueEndDate ? weekStartForDate(queueEndDate) : '';
  const latestActiveScheduledAt = useMemo(
    () => activeQueue.reduce((latest, item) => {
      const timestamp = new Date(item.scheduled_at || '').getTime();
      return Number.isFinite(timestamp) && timestamp > latest ? timestamp : latest;
    }, 0),
    [activeQueue],
  );
  const capacityEstimate = useMemo(() => estimateQueueCoverage({
    readyCount: availableClips.length,
    template: capacityTemplate,
    startDate: todayKey,
    now: new Date(),
    latestScheduledAt: latestActiveScheduledAt ? new Date(latestActiveScheduledAt).toISOString() : null,
  }), [availableClips.length, capacityTemplate, latestActiveScheduledAt, todayKey]);
  const capacityStatus = !capacityEstimate.readyCount
    ? { label: 'ยังไม่มีคลิปพร้อมจัด', className: 'text-red-200 bg-red-500/10 border-red-400/20' }
    : capacityEstimate.coveredDays <= 2
      ? { label: 'ควรเร่งถ่ายและตัดต่อเพิ่ม', className: 'text-red-200 bg-red-500/10 border-red-400/20' }
      : capacityEstimate.coveredDays <= 5
        ? { label: 'เตรียมถ่าย/ตัดต่อชุดถัดไป', className: 'text-amber-200 bg-amber-500/10 border-amber-400/20' }
        : { label: 'ยังมี buffer', className: 'text-emerald-200 bg-emerald-500/10 border-emerald-400/20' };
  const allSelectableSelected = selectableQueue.length > 0 && selectableQueue.every((item) => selectedIds.has(item.id));
  const calendarDays = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = addDays(calendarWeekStart, i);
      const dayDateObj = parseDateOnly(d);
      return {
        date: d,
        dayName: WEEKDAY_LABELS[i],
        dayNumber: dayDateObj.getUTCDate(),
        monthLabel: new Intl.DateTimeFormat('th-TH', { month: 'short' }).format(dayDateObj),
        isToday: d === todayKey,
        items: grouped[d] || [],
        analysis: dailyAnalysis[d] || null,
      };
    });
  }, [calendarWeekStart, grouped, todayKey, dailyAnalysis]);

  const persistSingle = async (value) => {
    if (!value.clip || !value.date || !value.time) throw new Error('เลือกคลิป วัน และเวลาก่อนบันทึกคิว');
    const clip = availableClips.find(item => clipKey(item) === clipKey(value.clip));
    if (!clip) throw new Error('คลิปที่เลือกเปลี่ยนแล้ว กรุณาเลือกคลิปใหม่');
    setSaving(true);
    try {
      await createScheduleQueue(clipToPayload(clip, buildScheduleIso(value.date, value.time)));
      setSingleOpen(false);
      showToast?.('เพิ่มคลิปลงคิวแล้ว');
      await loadQueue();
    } catch (error) {
      showToast?.(error.response?.data?.detail || error.message || 'เพิ่มคิวไม่สำเร็จ', 'error');
      throw error;
    } finally { setSaving(false); }
  };
  const saveSingle = () => singleController.save().catch(() => {});

  const occupiedIso = useMemo(() => {
    return new Set(queue.filter((row) => row.status !== 'posted').map((row) => row.scheduled_at));
  }, [queue]);

  const queueDayConstraints = useMemo(() => {
    const map = {};
    queue.forEach((row) => {
      const parts = localParts(row.scheduled_at);
      if (!parts?.date) return;
      if (!map[parts.date]) {
        map[parts.date] = { products: new Set(), colors: new Set() };
      }
      const pKey = resolveRowProductKey(row);
      if (pKey && pKey !== 'other') map[parts.date].products.add(pKey);
      const color = resolveRowHookColor(row);
      if (color) map[parts.date].colors.add(color);
    });
    return map;
  }, [queue]);

  const bulkPreview = useMemo(() => {
    if (!bulkDraft.date || !bulkDraft.time) return [];
    const isDaily = bulkDraft.mode === 'daily';
    const start = new Date(`${bulkDraft.date}T${bulkDraft.time}:00+07:00`);
    return bulkSelected.map((clip, index) => {
      let parts;
      if (isDaily) {
        const d = addDays(bulkDraft.date, index);
        parts = { date: d, time: bulkDraft.time };
      } else {
        const at = new Date(start.getTime() + index * Number(bulkDraft.interval || 5) * 60000);
        parts = localParts(at.toISOString());
      }
      const scheduledAt = buildScheduleIso(parts.date, parts.time);
      const isOccupied = occupiedIso.has(scheduledAt);

      const dayConstraint = queueDayConstraints[parts.date] || { products: new Set(), colors: new Set() };
      const pKey = resolveClipProductKey(clip);
      const hookColor = resolveClipHookColor(clip);
      const hasProductConflict = Boolean(pKey && pKey !== 'other' && dayConstraint.products.has(pKey));
      const hasColorConflict = Boolean(hookColor && dayConstraint.colors.has(hookColor));

      return {
        clip,
        ...parts,
        scheduledAt,
        isOccupied,
        hookColor,
        hasProductConflict,
        hasColorConflict,
      };
    });
  }, [bulkDraft, bulkSelected, occupiedIso, queueDayConstraints]);

  const hasOccupiedConflict = useMemo(() => {
    return bulkPreview.some((item) => item.isOccupied);
  }, [bulkPreview]);

  const autoSelectClips = (desiredCount, filterProduct) => {
    const count = Number(desiredCount) || 5;
    const prod = (filterProduct || 'all').toLowerCase();
    let pool = [...availableClips];
    if (prod !== 'all') {
      pool = pool.filter((c) => resolveClipProductKey(c) === prod);
    }
    if (!pool.length) {
      setBulkSelected([]);
      showToast?.('ไม่พบคลิปที่พร้อมจัดคิวตามเงื่อนไขที่เลือก', 'error');
      return;
    }

    // Shuffle pool to give fresh random picks on every click
    pool.sort(() => Math.random() - 0.5);

    const isDaily = bulkDraft.mode === 'daily';
    const startDate = bulkDraft.date || dateOnly();
    const targetCount = Math.min(Math.max(1, count), pool.length);
    const picked = [];

    // Clone existing day constraints so newly assigned clips also update constraints
    const dynamicConstraints = {};
    Object.entries(queueDayConstraints).forEach(([d, info]) => {
      dynamicConstraints[d] = {
        products: new Set(info.products),
        colors: new Set(info.colors),
      };
    });

    for (let i = 0; i < targetCount; i++) {
      if (!pool.length) break;
      const targetDate = isDaily ? addDays(startDate, i) : startDate;
      if (!dynamicConstraints[targetDate]) {
        dynamicConstraints[targetDate] = { products: new Set(), colors: new Set() };
      }
      const dayConstraint = dynamicConstraints[targetDate];

      // Tier 1 (Best): Neither Product nor Hook Color is used on that date
      let chosenIdx = pool.findIndex((c) => {
        const pKey = resolveClipProductKey(c);
        const color = resolveClipHookColor(c);
        const pColl = pKey && pKey !== 'other' && dayConstraint.products.has(pKey);
        const cColl = color && dayConstraint.colors.has(color);
        return !pColl && !cColl;
      });

      // Tier 2: Product NOT used on that date (even if Color repeats)
      if (chosenIdx === -1) {
        chosenIdx = pool.findIndex((c) => {
          const pKey = resolveClipProductKey(c);
          return !pKey || pKey === 'other' || !dayConstraint.products.has(pKey);
        });
      }

      // Tier 3: Color NOT used on that date (even if Product repeats)
      if (chosenIdx === -1) {
        chosenIdx = pool.findIndex((c) => {
          const color = resolveClipHookColor(c);
          return !color || !dayConstraint.colors.has(color);
        });
      }

      // Tier 4 (Fallback if clips are limited and overlap is unavoidable):
      if (chosenIdx === -1) {
        chosenIdx = 0;
      }

      const [selectedClip] = pool.splice(chosenIdx, 1);
      picked.push(selectedClip);

      // Track newly selected clip in this day's constraints
      const pKey = resolveClipProductKey(selectedClip);
      if (pKey && pKey !== 'other') dayConstraint.products.add(pKey);
      const color = resolveClipHookColor(selectedClip);
      if (color) dayConstraint.colors.add(color);
    }

    setBulkSelected(picked);
    showToast?.(`สุ่มเลือก ${picked.length} คลิปตามเงื่อนไข (สแกนสินค้าและสีของแต่ละวันแล้ว)`);
  };

  const persistBulk = async (value) => {
    if (!value.selected.length || !value.draft.date || !value.draft.time) throw new Error('เลือกคลิป วัน และเวลาก่อนบันทึกคิวชุด');
    // Re-resolve every selected clip from the current channel's live list and
    // recompute times at commit, rather than submitting a rendered preview.
    const selected = value.selected.map(item => availableClips.find(clip => clipKey(clip) === clipKey(item)));
    if (selected.some(clip => !clip)) throw new Error('รายการคลิปเปลี่ยนแล้ว กรุณาเลือกคลิปใหม่ก่อนบันทึก');
    const start = new Date(`${value.draft.date}T${value.draft.time}:00+07:00`);
    const items = selected.map((clip, index) => {
      const parts = value.draft.mode === 'daily'
        ? { date: addDays(value.draft.date, index), time: value.draft.time }
        : localParts(new Date(start.getTime() + index * Number(value.draft.interval || 5) * 60000).toISOString());
      const at = buildScheduleIso(parts.date, parts.time);
      if (occupiedIso.has(at)) throw new Error('เวลาที่เลือกมีคิวแล้ว กรุณาจัดเวลาใหม่');
      return clipToPayload(clip, at);
    });
    setSaving(true);
    try {
      await createScheduleQueue({ items });
      setBulkOpen(false);
      showToast?.(`เพิ่มคิว ${items.length} คลิปแล้ว`);
      await loadQueue();
    } catch (error) {
      showToast?.(error.response?.data?.detail || error.message || 'เพิ่มคิวชุดไม่สำเร็จ รายการเดิมยังอยู่ครบ', 'error');
      throw error;
    } finally { setSaving(false); }
  };
  const saveBulk = () => bulkController.save().catch(() => {});

  const reschedule = async (item, date, time, { throwOnError = false } = {}) => {
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
      if (throwOnError) throw error;
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
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
      showToast?.('นำคลิปออกจากคิวแล้ว ไฟล์ MP4 ยังอยู่ครบ');
    } catch (error) { showToast?.(error.response?.data?.detail || error.message, 'error'); }
  };

  const toggleSelectionMode = () => {
    setSelectionMode((prev) => !prev);
    setSelectedIds(new Set());
  };

  const toggleSelected = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelectedIds(allSelectableSelected ? new Set() : new Set(selectableQueue.map((item) => item.id)));
  };

  const removeSelected = async () => {
    const ids = [...selectedIds].filter((id) => selectableQueue.some((item) => item.id === id));
    if (!ids.length || bulkRemoving) return;
    if (!window.confirm(`นำ ${ids.length} คิวออกจากระบบหรือไม่? ไฟล์ MP4 จะไม่ถูกลบ`)) return;

    setBulkRemoving(true);
    const results = await Promise.allSettled(ids.map((id) => removeScheduleQueue(id)));
    const removedIds = ids.filter((id, index) => results[index].status === 'fulfilled');
    const failedCount = ids.length - removedIds.length;
    setQueue((prev) => prev.filter((row) => !removedIds.includes(row.id)));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      removedIds.forEach((id) => next.delete(id));
      return next;
    });
    if (failedCount) {
      showToast?.(`ลบสำเร็จ ${removedIds.length} คิว · ลบไม่ได้ ${failedCount} คิว`, 'error');
    } else {
      showToast?.(`ลบ ${removedIds.length} คิวแล้ว ไฟล์ MP4 ยังอยู่ครบ`);
    }
    setBulkRemoving(false);
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
    if (requeueController.isDirty()) { setRequeueOpen(true); return; }
    const requestId = requeueRequestId.current + 1;
    requeueRequestId.current = requestId;
    const now = new Date();
    setRequeueTarget(item);
    requeueController.markSaved({ targetId: item.id, date: '', time: '' });
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
      const loaded = slot || { date: '', time: '' };
      requeueController.markSaved({ targetId: item.id, ...loaded });
      setRequeueDraft(loaded);
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

  const persistRequeue = async (value) => {
    const target = queue.find(item => item.id === value.targetId);
    if (!target || !value.date || !value.time) throw new Error('เลือกคิว วัน และเวลาก่อนบันทึกคิวใหม่');
    setSaving(true);
    try {
      await reschedule(target, value.date, value.time, { throwOnError: true });
      setRequeueOpen(false);
    } finally { setSaving(false); }
  };
  const saveRequeue = () => requeueController.save().catch(() => {});

  const loadTemplate = async (week = templateWeek) => {
    if (templateController.isDirty()) {
      showToast?.('บันทึกหรือทิ้งการแก้ไขเทมเพลตก่อนโหลดสัปดาห์ใหม่', 'error');
      return;
    }
    const requestId = ++templateRequestId.current;
    setTemplateBusy(true);
    try {
      const response = await getScheduleTemplate(week);
      const normalized = templateForWeek(response, week);
      if (requestId !== templateRequestId.current) return;
      if (templateController.acceptExternal(normalized)) setTemplateDraft(normalized);
      setTemplateWeek(week);
      if (week === currentTemplateWeek) setCapacityTemplate(normalized);
    } catch (error) {
      showToast?.(errorText(error, 'โหลดเวลารายสัปดาห์ไม่สำเร็จ'), 'error');
    } finally { if (requestId === templateRequestId.current) setTemplateBusy(false); }
  };

  const openTemplate = async () => {
    setTemplateOpen(true);
    await loadTemplate();
  };

  const persistTemplate = async (value) => {
    if (Object.values(value.days).some(day => !day.times.length || new Set(day.times).size !== day.times.length)) throw new Error('ตรวจช่วงเวลาของเทมเพลตก่อนบันทึก');
    setTemplateBusy(true);
    try {
      const response = await saveScheduleTemplate({ week_start: value.week_start, days: value.days });
      const normalized = templateForWeek(response, value.week_start);
      if (value.week_start === currentTemplateWeek) setCapacityTemplate(normalized);
      showToast?.('บันทึกเวลารายสัปดาห์แล้ว');
    } catch (error) { showToast?.(errorText(error, 'บันทึกเวลาไม่สำเร็จ'), 'error'); throw error; }
    finally { setTemplateBusy(false); }
  };
  const saveTemplate = () => templateController.save().catch(() => {});

  const updateTemplateDay = (index, update) => {
    setTemplateDraft((prev) => ({
      ...prev,
      days: {
        ...prev.days,
        [index]: update(prev.days[index]),
      },
    }));
  };

  const updateTemplateTime = (index, timeIndex, value) => {
    updateTemplateDay(index, (day) => {
      const times = [...day.times];
      times[timeIndex] = value;
      return { ...day, times };
    });
  };

  const addTemplateTime = (index) => {
    updateTemplateDay(index, (day) => {
      const preferredExtraTimes = ['08:00', '10:00', '14:00', '17:00', '22:00', '23:00'];
      const next = [...preferredExtraTimes, ...primaryOptions].find((option) => !day.times.includes(option));
      return next ? { ...day, times: [...day.times, next].sort() } : day;
    });
  };

  const removeTemplateTime = (index, timeIndex) => {
    updateTemplateDay(index, (day) => {
      if (day.times.length <= 1) return day;
      return { ...day, times: day.times.filter((_, currentIndex) => currentIndex !== timeIndex) };
    });
  };

  const templateHasInvalidTimes = Object.values(templateDraft.days).some(({ times }) => {
    return !times?.length || new Set(times).size !== times.length;
  });

  const copyPreviousTemplate = () => templateController.run(async () => {
    setTemplateBusy(true);
    try {
      const response = await copyScheduleTemplate({ source_week_start: addDays(templateWeek, -7), target_week_start: templateWeek });
      const normalized = templateForWeek(response, templateWeek);
      templateController.markSaved(normalized);
      setTemplateDraft(normalized);
      if (templateWeek === currentTemplateWeek) setCapacityTemplate(normalized);
      showToast?.('คัดลอกเวลาจากสัปดาห์ก่อนแล้ว');
    } catch (error) { showToast?.(errorText(error, 'คัดลอกเวลาไม่สำเร็จ'), 'error'); }
    finally { setTemplateBusy(false); }
  }).catch(() => {});

  const autofillDateError = autofillStart && autofillEnd && autofillStart > autofillEnd
    ? 'วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่มต้น'
    : '';
  const autofillLimitValue = autofillLimit === '' ? null : Number(autofillLimit);
  const autofillLimitError = autofillLimit !== ''
    && (!Number.isInteger(autofillLimitValue) || autofillLimitValue < 1 || autofillLimitValue > 10000)
    ? 'จำนวนคลิปต้องเป็นเลขจำนวนเต็ม 1–10,000'
    : '';

  const resetTemplate = () => templateController.run(async () => {
    setTemplateBusy(true);
    try {
      const response = await resetScheduleTemplate(templateWeek);
      const normalized = templateForWeek(response, templateWeek);
      templateController.markSaved(normalized);
      setTemplateDraft(normalized);
      if (templateWeek === currentTemplateWeek) setCapacityTemplate(normalized);
      showToast?.('คืนค่าเวลาเริ่มต้นแล้ว');
    } catch (error) { showToast?.(errorText(error, 'คืนค่าเวลาไม่สำเร็จ'), 'error'); }
    finally { setTemplateBusy(false); }
  }).catch(() => {});

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
    if (!autofillStart || !autofillEnd || autofillDateError || autofillLimitError) return;
    setAutofillBusy(true);
    try {
      const response = await previewScheduleAutofill({
        start_date: autofillStart,
        end_date: autofillEnd,
        product_ids: autofillProduct === 'all' ? [] : [autofillProduct],
        limit: autofillLimitValue,
        optimize_by_stats: autofillUseStats,
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

  const openSingle = () => { if (singleController.isDirty()) { setSingleOpen(true); return; } const initial = { clip: null, ...nextSlot(queue) }; singleController.markSaved(initial); setSingleDraft(initial); setSingleOpen(true); };
  const openBulk = () => {
    if (bulkController.isDirty()) { setBulkOpen(true); return; }
    const initial = {
      ...nextSlot(queue),
      interval: 5,
      mode: 'daily',
      autoCount: 5,
      filterProduct: 'all',
    };
    bulkController.markSaved({ draft: initial, selected: [] });
    setBulkDraft(initial);
    setBulkSelected([]);
    setBulkOpen(true);
  };
  const openAutofill = () => { chooseAutofillRange('today'); setAutofillOpen(true); };
  const closeMoreAnd = (action) => { setMoreOpen(false); action(); };

  return (
    <div className="space-y-5">
      <div className="obsidian-card px-4 sm:px-5 py-3.5 rounded-2xl border border-cyan-400/20 bg-gradient-to-r from-cyan-950/20 via-slate-900/40 to-slate-950/80">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px]">
          <span className="text-slate-400">คลิปพร้อมจัด <strong className="text-white font-black">{capacityEstimate.readyCount}</strong> คลิป</span>
          <span className="text-cyan-200">รองรับอีก <strong className="text-white font-black">{capacityEstimate.coveredDays}</strong> วันโพสต์</span>
          <span className="text-slate-400">เทมเพลต {capacityEstimate.weeklyCapacity} คิว/สัปดาห์</span>
          {capacityEstimate.endDate && <span className="text-slate-400">คาดหมด {capacityEstimate.endDate} · สัปดาห์เริ่ม {capacityEstimate.endWeekStart}</span>}
          <span className={`px-2.5 py-0.5 rounded-full border text-[10px] font-bold ${capacityStatus.className}`}>{capacityStatus.label}</span>
        </div>
        <p className="mt-1.5 text-[10px] text-slate-500">อิงเทมเพลตสัปดาห์ปัจจุบันและการหมุนเวียนสินค้า (Fair Round-Robin) · คิวที่วางไว้ถึง {queueEndDate || 'ยังไม่มีคิว'}{queueEndDate ? ` · สัปดาห์เริ่ม ${queueEndWeekStart}` : ''}</p>
      </div>
      <div className="obsidian-card rounded-3xl border border-white/[0.1] bg-[#07090E]/95 shadow-2xl overflow-hidden backdrop-blur-xl">
        <div className="px-5 py-5 border-b border-white/[0.08] bg-gradient-to-r from-cyan-500/[0.08] via-transparent to-purple-500/[0.05]">
          <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-2xl bg-cyan-400/10 text-cyan-300 border border-cyan-400/20 shadow-[0_0_15px_rgba(34,211,238,0.15)]"><CalendarDays className="w-5 h-5" /></div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base sm:text-lg font-black text-white tracking-tight">คิวเผยแพร่วิดีโอ</h2>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-cyan-500/15 text-cyan-300 border border-cyan-400/30">Auto Rotation</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">ดูคิววันนี้เป็นหลัก · Asia/Bangkok · หมุนเวียนสินค้าและสี Hook อัตโนมัติ</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center rounded-xl bg-white/[0.04] p-1 border border-white/[0.08] mr-1">
                <button
                  type="button"
                  onClick={() => setViewMode('list')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${
                    viewMode === 'list' ? 'bg-cyan-400 text-slate-950 shadow-md font-black' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <List className="w-3.5 h-3.5" />
                  รายการ
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('calendar')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${
                    viewMode === 'calendar' ? 'bg-cyan-400 text-slate-950 shadow-md font-black' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Calendar className="w-3.5 h-3.5" />
                  สัปดาห์
                </button>
              </div>
              <button type="button" onClick={openAutofill} className="obsidian-hero-btn px-4 py-2 text-xs flex items-center gap-1.5 shadow-lg"><Shuffle className="w-4 h-4" />จัดคิวอัตโนมัติ</button>
              <button type="button" onClick={openSingle} className="px-3.5 py-2 rounded-xl border border-white/[0.12] bg-white/[0.05] text-white text-xs font-bold flex items-center gap-1.5 hover:bg-white/[0.1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"><Plus className="w-4 h-4" />เพิ่มคลิป</button>
              <button type="button" onClick={openBulk} className="px-3.5 py-2 rounded-xl border border-cyan-400/30 bg-cyan-400/10 text-cyan-200 text-xs font-bold flex items-center gap-1.5 hover:bg-cyan-400/20 hover:border-cyan-400/50 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 shadow-sm"><Layers className="w-4 h-4 text-cyan-300" />เพิ่มเป็นชุด</button>
              <button type="button" onClick={toggleSelectionMode} className="px-3 py-2 rounded-xl border border-white/[0.12] bg-white/[0.03] text-slate-200 text-xs font-bold flex items-center gap-1.5 hover:bg-white/[0.08] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300">
                <List className="w-4 h-4" />{selectionMode ? 'เสร็จสิ้น' : 'เลือกหลายคิว'}
              </button>
              {selectionMode && selectableQueue.length > 0 && (
                <button type="button" onClick={toggleSelectAll} className="px-3 py-2 rounded-xl border border-cyan-400/25 text-cyan-200 text-xs font-bold hover:bg-cyan-400/[0.08]">
                  {allSelectableSelected ? 'ล้างการเลือก' : `เลือกคิวที่ลบได้ (${selectableQueue.length})`}
                </button>
              )}
              {selectionMode && selectedIds.size > 0 && (
                <button type="button" disabled={bulkRemoving} onClick={removeSelected} className="px-3 py-2 rounded-xl border border-red-400/30 text-red-200 text-xs font-bold flex items-center gap-1.5 hover:bg-red-500/[0.08] disabled:opacity-50">
                  <Trash2 className="w-4 h-4" />{bulkRemoving ? 'กำลังลบ...' : `ลบที่เลือก (${selectedIds.size})`}
                </button>
              )}
              <div className="relative">
                <button type="button" onClick={() => setMoreOpen((open) => !open)} className="p-2 rounded-xl border border-white/[0.1] text-slate-300 hover:text-white hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300" aria-label="เมนูเพิ่มเติม" aria-expanded={moreOpen} aria-haspopup="menu">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
                {moreOpen && (
                  <div className="absolute right-0 top-full mt-2 z-30 w-56 rounded-2xl border border-white/[0.12] bg-[#10151e] p-1.5 shadow-2xl" role="menu">
                    <button type="button" role="menuitem" onClick={() => closeMoreAnd(openBulk)} className="w-full px-3 py-2.5 rounded-xl text-left text-xs font-bold text-slate-200 hover:bg-white/[0.07] flex items-center gap-2"><Layers className="w-4 h-4 text-cyan-300" />เพิ่มเป็นชุด</button>
                    <button type="button" role="menuitem" onClick={() => closeMoreAnd(openTemplate)} className="w-full px-3 py-2.5 rounded-xl text-left text-xs font-bold text-slate-200 hover:bg-white/[0.07] flex items-center gap-2"><Settings2 className="w-4 h-4 text-cyan-300" />ตั้งค่าเวลารายสัปดาห์</button>
                    {postedQueue.length > 0 && <button type="button" role="menuitem" onClick={() => closeMoreAnd(() => setPostedOpen(true))} className="w-full px-3 py-2.5 rounded-xl text-left text-xs font-bold text-slate-200 hover:bg-white/[0.07] flex items-center gap-2"><Archive className="w-4 h-4 text-emerald-300" />โพสต์แล้ว ({postedQueue.length})</button>}
                    <button type="button" role="menuitem" onClick={() => closeMoreAnd(loadQueue)} className="w-full px-3 py-2.5 rounded-xl text-left text-xs font-bold text-slate-200 hover:bg-white/[0.07] flex items-center gap-2"><RefreshCw className={`w-4 h-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />รีเฟรชคิว</button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 border-b border-white/[0.08] bg-black/20">
          <div className="px-4 sm:px-5 py-3 border-r border-b md:border-b-0 border-white/[0.06]">
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">วันนี้</p>
            <p className="mt-1 text-lg font-black text-white">{todayQueue.length} <span className="text-xs font-bold text-slate-500">คลิป</span></p>
          </div>
          <div className="px-4 sm:px-5 py-3 md:border-r border-b md:border-b-0 border-white/[0.06]">
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">คิวถัดไป</p>
            <p className="mt-1 text-lg font-black text-cyan-200">{nextToday ? localParts(nextToday.scheduled_at).time : 'ยังไม่มี'}</p>
          </div>
          <div className="px-4 sm:px-5 py-3 border-r border-white/[0.06]">
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">พร้อมจัด</p>
            <p className="mt-1 text-lg font-black text-white">{availableClips.length} <span className="text-xs font-bold text-slate-500">คลิป</span></p>
          </div>
          <div className="px-4 sm:px-5 py-3">
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">สถานะวันนี้</p>
            <p className={`mt-1 text-sm font-black ${overdueTodayCount ? 'text-amber-200' : 'text-emerald-200'}`}>{overdueTodayCount ? `เลยกำหนด ${overdueTodayCount} คลิป` : todayQueue.length ? 'ตามแผน' : 'พร้อมเริ่ม'}</p>
          </div>
        </div>

        {/* Quick Search & Filters Bar */}
        <div className="px-4 sm:px-5 py-2.5 border-b border-white/[0.08] bg-black/30 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[280px]">
            <div className="relative flex-1 min-w-[180px] max-w-xs">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="ค้นหาชื่อสินค้า / หัวข้อ Hook..."
                className="w-full pl-8 pr-7 py-1.5 rounded-xl bg-black/50 border border-white/[0.1] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/30"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white text-xs font-bold"
                  title="ล้างข้อความค้นหา"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex items-center rounded-xl bg-white/[0.04] p-0.5 border border-white/[0.08] text-[11px]">
              {[
                { id: 'all', label: 'ทั้งหมด' },
                { id: 'today', label: 'วันนี้' },
                { id: '7days', label: '7 วัน' },
                { id: '30days', label: '30 วัน' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setDateFilter(tab.id)}
                  className={`px-2.5 py-1 rounded-lg font-bold transition-all ${
                    dateFilter === tab.id
                      ? 'bg-cyan-400 text-slate-950 font-black shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {activeProductOptions.length > 1 && (
              <select
                value={productFilter}
                onChange={(e) => setProductFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-xl bg-black/50 border border-white/[0.1] text-xs text-slate-200 font-bold focus:outline-none focus:border-cyan-400/50"
              >
                <option value="all">สินค้าทั้งหมด ({activeQueue.length})</option>
                {activeProductOptions.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.name} ({opt.count})
                  </option>
                ))}
              </select>
            )}
          </div>

          {(searchQuery || dateFilter !== 'all' || productFilter !== 'all') && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-cyan-300 font-bold">
                แสดง {filteredActiveQueue.length} จาก {activeQueue.length} คลิป
              </span>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setDateFilter('all');
                  setProductFilter('all');
                }}
                className="text-slate-400 hover:text-white underline underline-offset-2 text-[11px]"
              >
                ล้างตัวกรอง
              </button>
            </div>
          )}
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
                        {day.analysis?.hasTimeConflict && (
                          <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" title={`มีเวลาชนกันในวันนี้: ${Array.from(day.analysis.duplicateTimes).join(', ')}`} />
                        )}
                        {day.analysis?.hasProductConflict && (
                          <span className="w-2 h-2 rounded-full bg-amber-400" title="มีสินค้าซ้ำในวันนี้" />
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] text-slate-400">{day.dayNumber} {day.monthLabel}</span>
                        {day.analysis?.uniqueColors?.length > 0 && (
                          <div className="flex items-center gap-0.5">
                            {day.analysis.uniqueColors.map((c) => (
                              <span
                                key={c}
                                className="w-1.5 h-1.5 rounded-full inline-block shadow-[0_0_4px_currentColor]"
                                style={{ backgroundColor: c }}
                                title={`สี Hook: ${c}`}
                              />
                            ))}
                          </div>
                        )}
                      </div>
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
                      const itemHookColor = resolveRowHookColor(item);
                      const itemPreset = item.style_preset ? getStylePreset(item.style_preset) : null;
                      const isTimeDuplicate = day.analysis?.duplicateTimes?.has(parts.time);
                      const isProductDuplicate = day.analysis?.duplicateProducts?.has(resolveRowProductKey(item));

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
                              {itemHookColor && (
                                <span
                                  className="w-2 h-2 rounded-full inline-block shadow-[0_0_5px_currentColor] ml-0.5"
                                  style={{ backgroundColor: itemHookColor }}
                                  title={`Hook Color: ${itemHookColor}${itemPreset?.label ? ` (${itemPreset.label})` : ''}`}
                                />
                              )}
                            </span>
                            <div className="flex items-center gap-1">
                              {isTimeDuplicate && (
                                <span className="px-1 py-0.2 rounded text-[8px] font-bold bg-red-500/20 text-red-300 border border-red-500/30">
                                  ซ้ำ
                                </span>
                              )}
                              {isProductDuplicate && (
                                <span className="px-1 py-0.2 rounded text-[8px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                  สินค้าซ้ำ
                                </span>
                              )}
                              {selectionMode && item.status === 'planned' && (
                                <input
                                  type="checkbox"
                                  checked={selectedIds.has(item.id)}
                                  onChange={() => toggleSelected(item.id)}
                                  aria-label={`เลือกคิว ${parts.time} ${item.product_name || item.video_path}`}
                                  className="accent-cyan-400"
                                />
                              )}
                              <Badge className={`text-[9px] px-1.5 py-0 ${STATUS_STYLES[item.status] || STATUS_STYLES.planned}`}>
                                {STATUS_LABELS[item.status] || item.status}
                              </Badge>
                              {item.status === 'scheduled_on_platform' && item.posting_job_id && <button type="button" aria-label="ตรวจว่าโพสต์จริงแล้ว" onClick={() => setPublicationReview(item)} className="min-h-11 rounded-lg border border-cyan-400/30 px-2 text-xs text-cyan-200 focus-visible:outline-2 focus-visible:outline-cyan-300">ตรวจโพสต์จริง</button>}
                            </div>
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
                              <video src={toMediaUrl(item.video_path)} muted className="w-full h-full object-cover" />
                              )}
                              <span className="absolute inset-0 bg-black/60 opacity-0 group-hover/thumb:opacity-100 transition-opacity flex items-center justify-center text-[8px] text-white">
                                ดู
                              </span>
                            </button>
                            <div className="min-w-0 flex-1">
                              <p className="text-[11px] font-bold text-slate-200 line-clamp-2 leading-snug">
                                {item.hook_title || item.product_name || item.video_path}
                              </p>
                              <div className="flex items-center justify-between gap-1 mt-0.5">
                                <p className="text-[9px] text-slate-500 truncate">
                                  {item.product_name || 'ไม่ระบุสินค้า'}
                                </p>
                                {itemHookColor && (
                                  <span
                                    className="text-[8px] font-mono font-bold px-1 rounded border flex-shrink-0"
                                    style={{
                                      backgroundColor: `${itemHookColor}15`,
                                      borderColor: `${itemHookColor}35`,
                                      color: itemHookColor,
                                    }}
                                  >
                                    {itemPreset?.label || itemHookColor}
                                  </span>
                                )}
                              </div>
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
          <div className="p-10 sm:p-12 text-center">
            <div className="w-12 h-12 mx-auto rounded-2xl bg-cyan-400/[0.08] border border-cyan-400/15 flex items-center justify-center"><CalendarDays className="w-6 h-6 text-cyan-300" /></div>
            {activeQueue.length > 0 ? (
              <>
                <p className="text-sm text-slate-200 font-black mt-4">ไม่พบคลิปตามเงื่อนไขที่ค้นหา</p>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  ลองเปลี่ยนคำค้นหา หรือกดล้างตัวกรองเพื่อดูคิวทั้งหมด ({activeQueue.length} รายการ)
                </p>
                <div className="mt-5">
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery('');
                      setDateFilter('all');
                      setProductFilter('all');
                    }}
                    className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black hover:brightness-110"
                  >
                    ล้างตัวกรองทั้งหมด
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="text-sm text-slate-200 font-black mt-4">วันนี้ยังไม่มีคิว</p>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">เริ่มจากจัดคิวอัตโนมัติเพื่อให้ระบบเลือกคลิปที่ยังไม่ซ้ำ หรือเพิ่มคลิปเองก็ได้</p>
                <div className="flex flex-wrap justify-center gap-2 mt-5">
                  <button type="button" onClick={openAutofill} className="px-3.5 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"><Shuffle className="w-3.5 h-3.5 inline-block mr-1.5" />จัดคิวอัตโนมัติ</button>
                  <button type="button" onClick={openSingle} className="px-3.5 py-2 rounded-xl border border-white/[0.12] text-slate-200 text-xs font-bold hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"><Plus className="w-3.5 h-3.5 inline-block mr-1.5" />เพิ่มคลิป</button>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="p-4 sm:p-5 space-y-4">
            {dates.map((date) => {
              const dayItems = grouped[date];
              const analysis = dailyAnalysis[date];
              return (
                <section key={date} onDragOver={(event) => event.preventDefault()} onDrop={() => onDropDate(date)} className="rounded-2xl border border-white/[0.08] bg-black/20 overflow-hidden">
                  <div className="px-4 py-3 flex flex-wrap items-center justify-between gap-2 bg-white/[0.035] border-b border-white/[0.08]">
                    <div>
                      <h3 className="text-sm font-black text-white">{thaiDate(date)}</h3>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="text-[11px] text-slate-400 font-bold">{date} · {dayItems.length} คลิป</span>
                        {analysis?.uniqueColors?.length > 0 && (
                          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.08]">
                            <span className="text-[9px] text-slate-400 font-bold mr-0.5">ชุดสี Hook:</span>
                            {analysis.uniqueColors.map((c) => (
                              <span
                                key={c}
                                className="w-2 h-2 rounded-full inline-block shadow-[0_0_5px_currentColor]"
                                style={{ backgroundColor: c }}
                                title={`สี Hook วันนี้: ${c}`}
                              />
                            ))}
                          </div>
                        )}
                        {analysis?.hasTimeConflict && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/15 text-red-300 border border-red-500/30 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-red-400" />
                            เวลาชนกัน ({Array.from(analysis.duplicateTimes).join(', ')})
                          </span>
                        )}
                        {analysis?.hasProductConflict && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-amber-400" />
                            สินค้าซ้ำในวันนี้
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-[10px] text-cyan-300 border border-cyan-400/20 rounded-full px-2 py-1">ลากคลิปมาวางเพื่อย้ายวัน</span>
                  </div>
                  <div className="divide-y divide-white/[0.06]">
                    {dayItems.map((item) => {
                      const parts = localParts(item.scheduled_at);
                      const clip = readyClips.find((candidate) => clipKey(candidate) === queueKey(item));
                      const coverPath = coverValue(item, clip);
                      const hasCover = Boolean(coverPath);
                      const overdue = item.is_overdue || (item.status === 'planned' && new Date(item.scheduled_at).getTime() < Date.now());
                      const itemHookColor = resolveRowHookColor(item);
                      const itemPreset = item.style_preset ? getStylePreset(item.style_preset) : null;
                      const isTimeDuplicate = analysis?.duplicateTimes?.has(parts.time);
                      const isProductDuplicate = analysis?.duplicateProducts?.has(resolveRowProductKey(item));
                      return (
                        <article key={item.id} draggable onDragStart={() => setDraggedId(item.id)} className="p-3 sm:p-4 flex flex-col lg:flex-row lg:items-center gap-3 hover:bg-white/[0.025] transition-colors">
                          <GripVertical className="hidden lg:block w-4 h-4 text-slate-600 cursor-grab flex-shrink-0" />
                          {selectionMode && item.status === 'planned' && (
                            <input
                              type="checkbox"
                              checked={selectedIds.has(item.id)}
                              onChange={() => toggleSelected(item.id)}
                              aria-label={`เลือกคิว ${parts.time} ${item.product_name || item.video_path}`}
                              className="accent-cyan-400"
                            />
                          )}
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <button type="button" onClick={() => clip?.video_url && onPreviewVideo?.(clip.video_url, clip)} className="w-14 h-20 rounded-xl overflow-hidden bg-black border border-white/[0.12] flex-shrink-0 relative group">
                              {coverSrc(coverPath) ? <img src={coverSrc(coverPath)} alt="" className="w-full h-full object-cover" /> : <video src={toMediaUrl(item.video_path)} muted className="w-full h-full object-cover" />}
                              <span className="absolute inset-x-1 bottom-1 text-[9px] rounded bg-black/75 text-white py-0.5">พรีวิว</span>
                            </button>
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="text-xs font-bold text-white truncate">{item.product_name || 'ไม่ระบุสินค้า'}</span>
                                <Badge className={STATUS_STYLES[item.status] || STATUS_STYLES.planned}>{STATUS_LABELS[item.status] || item.status}</Badge>
                                {item.status === 'scheduled_on_platform' && item.posting_job_id && <button type="button" onClick={() => setPublicationReview(item)} className="min-h-11 rounded-lg border border-cyan-400/30 px-3 text-xs text-cyan-200 hover:bg-cyan-400/10 focus-visible:outline-2 focus-visible:outline-cyan-300">ตรวจว่าโพสต์จริงแล้ว</button>}
                                {overdue && <Badge className="text-red-200 bg-red-500/10 border-red-500/25">เลยกำหนด</Badge>}
                                {isTimeDuplicate && (
                                  <Badge className="text-red-300 bg-red-500/15 border-red-500/30">
                                    ⚠️ เวลาซ้ำ
                                  </Badge>
                                )}
                                {isProductDuplicate && (
                                  <Badge className="text-amber-300 bg-amber-500/15 border-amber-500/30">
                                    ⚠️ สินค้าซ้ำวันนี้
                                  </Badge>
                                )}
                                {itemHookColor && (
                                  <span
                                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border text-[9px] font-mono font-bold"
                                    style={{
                                      backgroundColor: `${itemHookColor}15`,
                                      borderColor: `${itemHookColor}40`,
                                      color: itemHookColor,
                                    }}
                                    title={`Hook Color: ${itemHookColor}${itemPreset?.label ? ` (${itemPreset.label})` : ''}`}
                                  >
                                    <span className="w-1.5 h-1.5 rounded-full shadow-[0_0_5px_currentColor]" style={{ backgroundColor: itemHookColor }} />
                                    <span>{itemPreset?.label || itemHookColor}</span>
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-cyan-200 font-bold mt-1 line-clamp-2">{item.hook_title || item.project_name || item.video_path}</p>
                              <p className="text-[10px] text-slate-500 font-mono mt-1 truncate">{item.video_path}</p>
                            </div>
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
              );
            })}
          </div>
        )}
      </div>

      <Modal isOpen={singleOpen} onClose={() => setSingleOpen(false)} title="เพิ่มคลิปลงคิว" subtitle="เลือกคลิปที่ตัดต่อเสร็จแล้ว แล้วกำหนดวันและเวลาโพสต์" maxWidth="max-w-2xl">
        <div className="space-y-4"><div className="space-y-2"><label className="text-xs font-bold text-slate-300">คลิป</label><select value={singleDraft.clip ? clipKey(singleDraft.clip) : ''} onChange={(event) => setSingleDraft((prev) => ({ ...prev, clip: availableClips.find((clip) => clipKey(clip) === event.target.value) || null }))} className="w-full px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-sm text-white"><option value="">เลือกคลิปที่ตัดต่อเสร็จแล้ว</option>{availableClips.map((clip) => <option key={clipKey(clip)} value={clipKey(clip)}>{clip.parentProduct?.name || 'ไม่ระบุสินค้า'} · {clip.hook_title || clip.project_name}</option>)}</select></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-3"><label className="space-y-1 text-xs font-bold text-slate-300">วันที่<input type="date" value={singleDraft.date} onChange={(event) => setSingleDraft((prev) => ({ ...prev, date: event.target.value }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" /></label><label className="space-y-1 text-xs font-bold text-slate-300">เวลา (รอบละ 5 นาที)<select value={singleDraft.time} onChange={(event) => setSingleDraft((prev) => ({ ...prev, time: event.target.value }))} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white font-mono">{timeOptions.map((time) => <option key={time} value={time}>{time}</option>)}</select></label></div><p className="text-[11px] text-slate-500">ระบบจะกันคลิปซ้ำและกันเวลาชนกันให้ก่อนบันทึก</p><div className="flex justify-end gap-2"><button type="button" onClick={() => setSingleOpen(false)} className="px-3 py-2 rounded-xl text-xs text-slate-300">ยกเลิก</button><button type="button" disabled={!singleDraft.clip || saving} onClick={saveSingle} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black disabled:opacity-50">บันทึกเข้าคิว</button></div></div>
      </Modal>

      <Modal isOpen={bulkOpen} onClose={() => setBulkOpen(false)} title="เพิ่มคลิปเป็นชุด" subtitle="เลือกจัดเวลาเดิมทุกวัน หรือจัดในวันเดียวกัน พร้อมระบบสุ่มเลือกคลิปอัตโนมัติ" maxWidth="max-w-5xl">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 p-1.5 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-400 pl-2">รูปแบบการจัด:</span>
              <button
                type="button"
                onClick={() => setBulkDraft((prev) => ({ ...prev, mode: 'daily' }))}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                  bulkDraft.mode === 'daily'
                    ? 'bg-cyan-400 text-slate-950 font-black shadow-md'
                    : 'text-slate-300 hover:text-white hover:bg-white/[0.05]'
                }`}
              >
                <Calendar className="w-3.5 h-3.5" />
                เวลาเดิมทุกวัน (Daily Fixed Time)
              </button>
              <button
                type="button"
                onClick={() => setBulkDraft((prev) => ({ ...prev, mode: 'interval' }))}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                  bulkDraft.mode === 'interval'
                    ? 'bg-cyan-400 text-slate-950 font-black shadow-md'
                    : 'text-slate-300 hover:text-white hover:bg-white/[0.05]'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                ในวันเดียวกัน (ตามช่วงนาที)
              </button>
            </div>
            <div className="text-[11px] text-cyan-200/80 pr-2">
              {bulkDraft.mode === 'daily'
                ? `ลงเวลา ${bulkDraft.time || '19:30'} ติดต่อกันวันละ 1 คลิป`
                : `รันต่อเนื่องในวันเดียว ห่างกันทุก ${bulkDraft.interval || 5} นาที`}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label className="space-y-1 text-xs font-bold text-slate-300">
              เริ่มวันที่
              <input
                type="date"
                value={bulkDraft.date}
                onChange={(event) => setBulkDraft((prev) => ({ ...prev, date: event.target.value }))}
                className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white"
              />
            </label>
            <label className="space-y-1 text-xs font-bold text-slate-300">
              {bulkDraft.mode === 'daily' ? 'เวลาที่ต้องการลงทุกวัน' : 'เริ่มเวลา'}
              <select
                value={bulkDraft.time}
                onChange={(event) => setBulkDraft((prev) => ({ ...prev, time: event.target.value }))}
                className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white font-mono"
              >
                {timeOptions.map((time) => (
                  <option key={time} value={time}>{time}</option>
                ))}
              </select>
            </label>
            {bulkDraft.mode === 'interval' ? (
              <label className="space-y-1 text-xs font-bold text-slate-300">
                ระยะห่าง
                <select
                  value={bulkDraft.interval}
                  onChange={(event) => setBulkDraft((prev) => ({ ...prev, interval: Number(event.target.value) }))}
                  className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white"
                >
                  <option value="5">ทุก 5 นาที</option>
                  <option value="10">ทุก 10 นาที</option>
                  <option value="15">ทุก 15 นาที</option>
                  <option value="30">ทุก 30 นาที</option>
                  <option value="60">ทุก 1 ชั่วโมง</option>
                </select>
              </label>
            ) : (
              <div className="flex flex-col justify-end">
                <div className="p-2.5 rounded-xl bg-cyan-400/[0.06] border border-cyan-400/20 text-[11px] text-cyan-200">
                  📅 คลิปจะถูกจัดลงเวลา <strong className="text-white font-mono">{bulkDraft.time}</strong> ในแต่ละวันต่อเนื่องกัน
                </div>
              </div>
            )}
          </div>

          {/* Quick Auto-Pick Control Bar */}
          <div className="p-3 rounded-2xl bg-gradient-to-r from-cyan-950/30 via-slate-900/60 to-purple-950/20 border border-cyan-400/20 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Shuffle className="w-3.5 h-3.5 text-cyan-300" />
                ดึงคลิปอัตโนมัติ (ไม่ต้องเลือกทีละอัน)
              </span>
              <span className="text-[11px] text-slate-400">
                พร้อมจัดคิว <strong className="text-cyan-200">{availableClips.length}</strong> คลิป · เลือกแล้ว <strong className="text-white">{bulkSelected.length}</strong> คลิป
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5 bg-black/40 px-2 py-1 rounded-xl border border-white/[0.08]">
                <span className="text-[11px] text-slate-400">จำนวน:</span>
                <input
                  type="number"
                  min="1"
                  max={Math.max(1, availableClips.length)}
                  value={bulkDraft.autoCount ?? 5}
                  onChange={(e) => setBulkDraft((prev) => ({ ...prev, autoCount: Math.max(1, Number(e.target.value) || 1) }))}
                  className="w-14 px-2 py-1 rounded-lg bg-black/60 border border-white/[0.1] text-xs text-white text-center font-bold"
                />
                <div className="flex items-center gap-1">
                  {[3, 5, 7, 10].map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => {
                        setBulkDraft((prev) => ({ ...prev, autoCount: num }));
                        autoSelectClips(num, bulkDraft.filterProduct);
                      }}
                      className="px-2 py-1 rounded-lg border border-white/[0.1] text-[10px] text-slate-300 hover:text-white hover:bg-white/[0.08]"
                    >
                      {num}
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => {
                      setBulkDraft((prev) => ({ ...prev, autoCount: availableClips.length }));
                      autoSelectClips(availableClips.length, bulkDraft.filterProduct);
                    }}
                    className="px-2 py-1 rounded-lg border border-white/[0.1] text-[10px] text-cyan-300 hover:bg-cyan-400/10"
                  >
                    ทั้งหมด
                  </button>
                </div>
              </div>

              <select
                value={bulkDraft.filterProduct || 'all'}
                onChange={(e) => {
                  const val = e.target.value;
                  setBulkDraft((prev) => ({ ...prev, filterProduct: val }));
                  autoSelectClips(bulkDraft.autoCount, val);
                }}
                className="px-2.5 py-1.5 rounded-xl bg-black/50 border border-white/[0.1] text-xs text-slate-200"
              >
                <option value="all">สินค้าทั้งหมด</option>
                {productOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </select>

              <button
                type="button"
                onClick={() => autoSelectClips(bulkDraft.autoCount, bulkDraft.filterProduct)}
                disabled={!availableClips.length}
                className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md hover:brightness-110 disabled:opacity-50"
              >
                <Shuffle className="w-3.5 h-3.5" />
                สุ่มเลือก {bulkDraft.autoCount || 5} คลิป (หมุนเวียนสินค้า)
              </button>

              {bulkSelected.length > 0 && (
                <button
                  type="button"
                  onClick={() => setBulkSelected([])}
                  className="px-2.5 py-1.5 rounded-xl border border-white/[0.1] text-slate-400 hover:text-white text-xs"
                >
                  ล้างการเลือก
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left: Clips Pool with checkboxes */}
            <div className="rounded-2xl border border-white/[0.1] p-3 max-h-80 overflow-y-auto space-y-1">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-white">รายการคลิปที่เลือก ({bulkSelected.length})</span>
                <span className="text-[10px] text-slate-500">ติ๊กเพิ่ม/ลดได้เองตามต้องการ</span>
              </div>
              {availableClips.length === 0 ? (
                <p className="text-xs text-slate-500 py-8 text-center">ไม่มีคลิปที่ว่างสำหรับจัดคิว</p>
              ) : (
                availableClips.map((clip) => {
                  const key = clipKey(clip);
                  const selected = bulkSelected.some((item) => clipKey(item) === key);
                  return (
                    <label key={key} className={`flex items-center gap-2 p-2 rounded-xl hover:bg-white/[0.05] cursor-pointer transition-colors ${selected ? 'bg-cyan-400/[0.08] border border-cyan-400/20' : ''}`}>
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => setBulkSelected((prev) => selected ? prev.filter((item) => clipKey(item) !== key) : [...prev, clip])}
                        className="accent-cyan-400"
                      />
                      <span className="text-xs text-slate-200 truncate">
                        {clip.parentProduct?.name || 'ไม่ระบุสินค้า'} · {clip.hook_title || clip.project_name}
                      </span>
                    </label>
                  );
                })
              )}
            </div>

            {/* Right: Calculated Preview */}
            <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.03] p-3 max-h-80 overflow-y-auto">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-white">ตัวอย่างคิวที่จะบันทึก ({bulkPreview.length})</span>
                <span className="text-[10px] text-slate-500">ปรับลำดับด้วยปุ่มขึ้น/ลงได้</span>
              </div>
              {bulkPreview.length === 0 ? (
                <div className="py-12 text-center">
                  <p className="text-xs text-slate-400">ยังไม่ได้เลือกคลิป</p>
                  <p className="text-[11px] text-slate-500 mt-1">กดปุ่ม "สุ่มเลือกคลิปอัตโนมัติ" ด้านบนได้ทันที</p>
                </div>
              ) : (
                bulkPreview.map(({ clip, date, time, isOccupied, hookColor, hasProductConflict, hasColorConflict }, index) => (
                  <div
                    key={`${clipKey(clip)}-${index}`}
                    className={`flex items-center gap-2 py-2 border-b border-white/[0.06] last:border-0 ${
                      isOccupied
                        ? 'bg-red-500/[0.08] -mx-2 px-2 rounded-lg'
                        : hasProductConflict || hasColorConflict
                          ? 'bg-amber-500/[0.04] -mx-2 px-2 rounded-lg'
                          : ''
                    }`}
                  >
                    <span className="w-5 h-5 rounded-full bg-cyan-400/15 text-cyan-200 text-[10px] flex items-center justify-center font-bold">
                      {index + 1}
                    </span>
                    <span
                      className="w-2.5 h-2.5 rounded-full border border-white/30 flex-shrink-0"
                      style={{ backgroundColor: hookColor || '#FFE600' }}
                      title={`สี Hook: ${hookColor || 'ไม่ระบุ'}`}
                    />
                    <span className="text-[11px] text-white font-mono whitespace-nowrap">
                      {date} {time}
                    </span>
                    {isOccupied && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-500/20 text-red-200 border border-red-500/30 whitespace-nowrap">
                        ⚠️ เวลาซ้ำ
                      </span>
                    )}
                    {hasProductConflict && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-200 border border-amber-500/30 whitespace-nowrap" title="มีคลิปสินค้านี้ลงในวันเดียวกันแล้ว">
                        ⚠️ สินค้าซ้ำวันนี้
                      </span>
                    )}
                    {hasColorConflict && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-500/20 text-purple-200 border border-purple-500/30 whitespace-nowrap" title="มีคลิปที่ใช้สี Hook นี้ลงในวันเดียวกันแล้ว">
                        ⚠️ สีซ้ำวันนี้
                      </span>
                    )}
                    <span className="text-xs text-slate-300 truncate flex-1">
                      {clip.parentProduct?.name || 'ไม่ระบุสินค้า'} · {clip.hook_title || clip.project_name}
                    </span>
                    <button
                      type="button"
                      disabled={index === 0}
                      onClick={() => setBulkSelected((prev) => {
                        const next = [...prev];
                        [next[index - 1], next[index]] = [next[index], next[index - 1]];
                        return next;
                      })}
                      className="p-1 rounded border border-white/[0.1] text-slate-400 hover:text-white disabled:opacity-25"
                      title="เลื่อนขึ้น"
                      aria-label="เลื่อนขึ้น"
                    >
                      <ChevronUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      disabled={index === bulkPreview.length - 1}
                      onClick={() => setBulkSelected((prev) => {
                        const next = [...prev];
                        [next[index], next[index + 1]] = [next[index + 1], next[index]];
                        return next;
                      })}
                      className="p-1 rounded border border-white/[0.1] text-slate-400 hover:text-white disabled:opacity-25"
                      title="เลื่อนลง"
                      aria-label="เลื่อนลง"
                    >
                      <ChevronDown className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {hasOccupiedConflict && (
            <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-200 flex items-center gap-2">
              <span>⚠️ มีบางช่วงเวลาชนกับคิวเดิม กรุณาปรับเปลี่ยนวันที่/เวลา หรือสลับลำดับคลิปก่อนบันทึก</span>
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <span className="text-[11px] text-slate-500">
              {bulkDraft.mode === 'daily'
                ? `📅 จัดคิวเวลา ${bulkDraft.time} รวมทั้งหมด ${bulkPreview.length} วัน`
                : `⏱️ จัดคิววันที่ ${bulkDraft.date} เริ่ม ${bulkDraft.time}`}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setBulkOpen(false)}
                className="px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-white/[0.05]"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                disabled={!bulkPreview.length || saving || hasOccupiedConflict}
                onClick={saveBulk}
                className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black disabled:opacity-50 hover:brightness-110"
              >
                {saving ? 'กำลังบันทึก...' : `บันทึกทั้งชุด (${bulkPreview.length} คลิป)`}
              </button>
            </div>
          </div>
        </div>
      </Modal>

      <Modal isOpen={templateOpen} onClose={() => setTemplateOpen(false)} title="ตั้งค่าเวลารายสัปดาห์" subtitle="สัปดาห์จันทร์–อาทิตย์ · เพิ่มช่วงพิเศษแยกเป็นรายวันได้ · ใช้เฉพาะจัดคิวอัตโนมัติ" maxWidth="max-w-4xl">
        <div className="space-y-4">
          <div className="rounded-xl border border-cyan-400/15 bg-cyan-400/[0.04] px-3 py-2.5 text-[11px] text-cyan-100">
            ค่าเริ่มต้นของระบบ: 5 ช่วง/วัน — 09:00 · 12:30 · 16:00 · 19:00 · 21:30
            <span className="text-slate-400"> · สัปดาห์ที่ไม่ได้ตั้งค่าเฉพาะจะใช้ชุดนี้ต่อเนื่อง</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-end gap-3">
            <label className="flex-1 text-xs font-bold text-slate-300">สัปดาห์ที่เริ่มวันจันทร์
              <input type="date" value={templateWeek} disabled={templateBusy} onChange={async (event) => { const week = weekStartForDate(event.target.value); await loadTemplate(week); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" />
            </label>
            <div className="flex gap-2">
              <button type="button" disabled={templateBusy} onClick={copyPreviousTemplate} className="px-3 py-2 rounded-xl border border-white/[0.1] text-xs text-slate-200 flex items-center gap-1.5"><Copy className="w-3.5 h-3.5" />คัดลอกสัปดาห์ก่อน</button>
              <button type="button" disabled={templateBusy} onClick={resetTemplate} className="px-3 py-2 rounded-xl border border-white/[0.1] text-xs text-slate-200 flex items-center gap-1.5"><RotateCcw className="w-3.5 h-3.5" />คืนค่าเริ่มต้น</button>
            </div>
          </div>
          <fieldset disabled={templateBusy} className="rounded-2xl border border-white/[0.1] overflow-x-auto">
            <div className="min-w-[760px]">
              <div className="grid grid-cols-[120px_76px_minmax(0,1fr)] gap-2 px-3 py-2 text-[10px] text-slate-500 border-b border-white/[0.08]"><span>วัน</span><span>เปิดใช้</span><span>ช่วงเวลาโพสต์ · เพิ่ม/ลบแยกเป็นรายวัน</span></div>
              {Object.entries(templateDraft.days).map(([index, day]) => <div key={index} className="grid grid-cols-[120px_76px_minmax(0,1fr)] gap-2 items-center px-3 py-2.5 border-b border-white/[0.06] last:border-0"><span className="text-xs text-white font-bold">{['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์'][Number(index)]}</span><label className="flex items-center"><input type="checkbox" checked={day.enabled !== false} onChange={(event) => updateTemplateDay(index, (current) => ({ ...current, enabled: event.target.checked }))} className="accent-cyan-400" /><span className="sr-only">เปิดใช้ {['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์'][Number(index)]}</span></label><div className="flex flex-wrap items-center gap-2">{day.times.map((time, timeIndex) => <div key={`${index}-${timeIndex}`} className="flex items-center gap-1"><select value={time} onChange={(event) => updateTemplateTime(index, timeIndex, event.target.value)} className="w-[112px] px-2 py-2 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white font-mono">{primaryOptions.map((option) => <option key={option} value={option} disabled={day.times.some((current, currentIndex) => currentIndex !== timeIndex && current === option)}>{option}</option>)}</select><button type="button" onClick={() => removeTemplateTime(index, timeIndex)} disabled={day.times.length <= 1} className="p-1.5 rounded-lg border border-white/[0.08] text-slate-500 hover:text-red-300 hover:border-red-400/30 disabled:opacity-25 disabled:hover:text-slate-500" title="ลบช่วงเวลานี้" aria-label={`ลบช่วงเวลา ${time} ของวัน${['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์'][Number(index)]}`}><Trash2 className="w-3.5 h-3.5" /></button></div>)}<button type="button" onClick={() => addTemplateTime(index)} disabled={day.times.length >= primaryOptions.length} className="px-2.5 py-2 rounded-lg border border-cyan-400/25 text-cyan-200 text-[11px] font-bold flex items-center gap-1 hover:bg-cyan-400/10 disabled:opacity-40" title="เพิ่มช่วงเวลาพิเศษ"><Plus className="w-3.5 h-3.5" />เพิ่มช่วง</button></div></div>)}
            </div>
          </fieldset>
          <p className={`text-[11px] ${templateHasInvalidTimes ? 'text-amber-200' : 'text-slate-500'}`}>{templateHasInvalidTimes ? 'กรุณาเลือกเวลาไม่ซ้ำกัน และให้เหลืออย่างน้อย 1 ช่วงต่อวัน' : 'ค่าเริ่มต้นมี 5 ช่วง · เพิ่มช่วงพิเศษนอกเหนือจากค่าเริ่มต้นได้ · ทุกช่วงเป็นรอบละ 5 นาที · การแก้เทมเพลตไม่เปลี่ยนคิวที่บันทึกไว้แล้ว'}</p>
          <div className="flex justify-end gap-2"><button type="button" onClick={() => setTemplateOpen(false)} className="px-3 py-2 rounded-xl text-xs text-slate-300">ยกเลิก</button><button type="button" disabled={templateBusy || templateHasInvalidTimes} onClick={saveTemplate} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black disabled:opacity-50">บันทึกเทมเพลต</button></div>
        </div>
      </Modal>

      <Modal isOpen={autofillOpen} onClose={() => setAutofillOpen(false)} title="จัดคิวอัตโนมัติ" subtitle="ดูตัวอย่างก่อนบันทึก · จัดเฉพาะในช่วงวันที่เลือก · ระบบจะใช้คลิปที่ยังไม่อยู่ในคิวเท่านั้น" maxWidth="max-w-5xl">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2"><button type="button" onClick={() => chooseAutofillRange('today')} className={`px-3 py-2 rounded-xl text-xs font-bold ${autofillRange === 'today' ? 'bg-cyan-400 text-slate-950' : 'border border-white/[0.1] text-slate-200'}`}>วันนี้</button><button type="button" onClick={() => chooseAutofillRange('week')} className={`px-3 py-2 rounded-xl text-xs font-bold ${autofillRange === 'week' ? 'bg-cyan-400 text-slate-950' : 'border border-white/[0.1] text-slate-200'}`}>สัปดาห์นี้</button><button type="button" onClick={() => chooseAutofillRange('custom')} className={`px-3 py-2 rounded-xl text-xs font-bold ${autofillRange === 'custom' ? 'bg-cyan-400 text-slate-950' : 'border border-white/[0.1] text-slate-200'}`}>กำหนดช่วงเอง</button></div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"><label className="text-xs font-bold text-slate-300">เริ่มวันที่<input type="date" value={autofillStart} max={autofillEnd || undefined} onChange={(event) => { setAutofillStart(event.target.value); setAutofillRange('custom'); setAutofillPreview(null); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" /></label><label className="text-xs font-bold text-slate-300">ถึงวันที่<input type="date" value={autofillEnd} min={autofillStart || undefined} onChange={(event) => { setAutofillEnd(event.target.value); setAutofillRange('custom'); setAutofillPreview(null); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white" /></label><label className="text-xs font-bold text-slate-300">สินค้า<select value={autofillProduct} onChange={(event) => { setAutofillProduct(event.target.value); setAutofillPreview(null); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white"><option value="all">สินค้าทั้งหมด</option>{productOptions.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label><label className="text-xs font-bold text-slate-300"><span className="flex flex-wrap items-center justify-between gap-1"><span>จำนวนคลิป</span><span className="text-[10px] font-normal text-slate-500">ว่าง = ทั้งหมด · พร้อมจัด {availableClips.length}</span></span><input type="number" min="1" max="10000" value={autofillLimit} placeholder={availableClips.length ? `ทั้งหมด (${availableClips.length})` : 'ทั้งหมด'} aria-label="จำนวนคลิป" onChange={(event) => { setAutofillLimit(event.target.value); setAutofillPreview(null); }} className="w-full mt-1 px-3 py-2.5 rounded-xl bg-black/50 border border-white/[0.1] text-white placeholder:text-slate-500" /></label></div>
          <label className="flex items-center gap-2 text-xs text-slate-200"><input type="checkbox" checked={autofillUseStats} onChange={(event) => { setAutofillUseStats(event.target.checked); setAutofillPreview(null); }} className="accent-cyan-400" />ใช้สถิติยอดวิว/engagement/ออเดอร์ช่วยเลือกสินค้าและช่วงเวลา <span className="text-slate-500">(มีข้อมูลน้อยจะลดความมั่นใจให้อัตโนมัติ)</span></label>
          {(autofillDateError || autofillLimitError) && <p role="alert" className="text-xs text-red-200">{autofillDateError || autofillLimitError}</p>}
          <div className="flex items-center justify-between gap-3"><p className="text-[11px] text-slate-500">จัดเฉพาะช่วงวันที่เลือกเท่านั้น · ข้ามเวลาที่ผ่านไปแล้วและเวลาที่ถูกใช้ไปแล้ว · ถ้าช่องไม่พอ ระบบจะแจ้งจำนวนที่เหลือ</p><button type="button" disabled={autofillBusy || !availableClips.length || Boolean(autofillDateError || autofillLimitError)} onClick={runAutofillPreview} className="px-4 py-2 rounded-xl bg-cyan-400 text-slate-950 text-xs font-black flex items-center gap-1.5 disabled:opacity-50"><Shuffle className="w-4 h-4" />{autofillBusy ? 'กำลังคำนวณ' : 'สร้างตัวอย่างคิว'}</button></div>
          <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.03] p-3 max-h-96 overflow-y-auto">{!autofillPreview ? <p className="py-12 text-center text-xs text-slate-500">กดสร้างตัวอย่างเพื่อดูวัน เวลา ลำดับคลิป และเหตุผลการเลือกก่อนบันทึก</p> : autofillPreview.items?.length ? <div className="space-y-1"><p className="text-[11px] text-cyan-200 pb-2">จัดได้ {autofillPreview.items.length} จาก {autofillPreview.requested_count ?? autofillPreview.items.length} คลิปในช่วง {autofillPreview.range_start} ถึง {autofillPreview.range_end}</p>{autofillPreview.analytics?.available ? <p className="text-[11px] text-slate-400 pb-2">อ้างอิงสถิติ {autofillPreview.analytics.sample_size} คลิป · สินค้าเด่น {autofillPreview.analytics.top_products?.[0]?.product_name || '-'} · ช่วงเวลาเด่น {String(autofillPreview.analytics.top_hours?.[0]?.hour ?? '-').padStart(2, '0')}:00 · ความมั่นใจ {autofillPreview.analytics.confidence}</p> : <p className="text-[11px] text-slate-500 pb-2">ยังไม่มีสถิติที่วัดผลเพียงพอ ระบบจึงไม่ฝืนสรุปว่าสินค้าหรือเวลาใดชนะ</p>}{autofillPreview.items.map((item, index) => <div key={`${item.video_path}-${item.scheduled_at}`} className="flex items-center gap-2 py-2 border-b border-white/[0.06] last:border-0"><span className="w-6 h-6 rounded-full bg-cyan-400/15 text-cyan-100 text-[10px] flex items-center justify-center">{index + 1}</span><span className="w-2.5 h-2.5 rounded-full border border-white/30 flex-shrink-0" style={{ backgroundColor: item.hook_color || 'transparent' }} title={`สี Hook ${item.hook_color || 'ไม่ระบุ'}`} aria-label={`สี Hook ${item.hook_color || 'ไม่ระบุ'}`} /><span className="text-xs font-mono text-white whitespace-nowrap">{item.scheduled_at.slice(0, 16).replace('T', ' ')}</span><span className="text-xs text-cyan-100 truncate flex-1">{item.product_name || 'ไม่ระบุสินค้า'} · {item.hook_title || item.project_name || item.video_path}</span></div>)}{autofillPreview.reason && <p className="text-xs text-amber-200 mt-3">{autofillPreview.reason} · เหลืออีก {autofillPreview.skipped_items || 0} คลิปที่ยังไม่ถูกจัด</p>}</div> : <div className="py-10 text-center"><p className="text-sm text-slate-300">ยังจัดคิวไม่ได้</p><p className="text-xs text-slate-500 mt-1">{autofillPreview.reason || 'ไม่มีรายการที่พร้อม'}</p></div>}</div>
          {autofillPreview?.skipped_invalid?.length > 0 && <p className="text-xs text-red-200">ข้ามไฟล์ที่ตรวจสอบไม่ได้ {autofillPreview.skipped_invalid.length} รายการ</p>}
          {autofillPreview?.skipped_slots > 0 && <p className="text-xs text-amber-200">เว้นช่วงเวลาอีก {autofillPreview.skipped_slots} ช่อง เพราะไม่มีคลิปหรือช่วงเวลาที่ว่าง</p>}
          {autofillPreview?.skipped_repetition > 0 && <p className="text-xs text-amber-200">เว้นคลิปอีก {autofillPreview.skipped_repetition} รายการ เพราะจะทำให้สินค้าหรือสี Hook ซ้ำภายในวันเดียวกัน</p>}
          {autofillPreview?.skip_summary && <p className="text-xs text-slate-400">สรุปที่ข้าม: อยู่ในคิวแล้ว {autofillPreview.skip_summary.already_queued || 0} · โพสต์/ตรวจสอบไม่ได้ {autofillPreview.skip_summary.invalid_or_posted || 0} · ไม่ตรงตัวกรองสินค้า {autofillPreview.skip_summary.outside_product_filter || 0} · ซ้ำสินค้า/สี Hook {autofillPreview.skip_summary.duplicate_product_or_hook_color || 0} · ไม่มีช่องเวลา {autofillPreview.skip_summary.no_available_slot || 0}</p>}
          {autofillPreview?.analytics?.available && <p className="text-xs text-slate-400">ตัวชี้วัดรายได้ของสินค้าเด่น: ออเดอร์ {autofillPreview.analytics.top_products?.[0]?.orders_per_1000_views ?? 0} ต่อ 1,000 วิว · คอมมิชชัน {autofillPreview.analytics.top_products?.[0]?.commission_per_1000_views_thb ?? 0} บาทต่อ 1,000 วิว · คลิกตะกร้า {autofillPreview.analytics.top_products?.[0]?.cart_click_rate ?? 0}%</p>}
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
              {postedQueue.slice((postedPage - 1) * postedPageSize, postedPage * postedPageSize).map((item) => (
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
              <PaginationControls
                page={postedPage}
                pageSize={postedPageSize}
                totalItems={postedQueue.length}
                onPageChange={setPostedPage}
                onPageSizeChange={(size) => {
                  setPostedPageSize(size);
                  setPostedPage(1);
                }}
                itemLabel="รายการ"
              />
            </>
          )}
        </div>
      </Modal>
      {publicationReview && <PublicationReviewModal item={publicationReview} channelId={channel?.channelId || 'main'}
        onClose={() => setPublicationReview(null)} onRecorded={async () => { setPublicationReview(null); await loadQueue(); }} />}
    </div>
  );
}
