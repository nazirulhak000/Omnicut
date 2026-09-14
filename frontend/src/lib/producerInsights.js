/**
 * AI Producer Hub & Daily Mission Insights Engine
 * Provides calculation of production quotas, daily action items,
 * dynamic boss greetings, content retrospectives, and playbook persistence.
 */

export const DEFAULT_TARGETS = {
  dailyCuts: 5,
  weeklyCuts: 35,
  dailyPosts: 3,
};

export const TARGETS_STORAGE_KEY = 'omnicut_producer_targets';
export const PLAYBOOK_STORAGE_KEY = 'omnicut_boss_playbook';
export const PRODUCER_INSIGHTS_CONTRACT = '1.1.0';

/**
 * Normalize a path or external identity so equivalent media can be compared.
 * This intentionally keeps the value local and deterministic; it never exposes
 * the full filesystem path to the UI.
 */
function normalizeIdentityToken(value) {
  if (!value || typeof value !== 'string') return '';
  return value
    .trim()
    .replace(/\\/g, '/')
    .split('/')
    .pop()
    .replace(/\.(mp4|mov|m4v|webm|avi)$/i, '')
    .toLowerCase();
}

/**
 * Return every stable identity available on an angle/export record.
 * Shared aliases let stats deduplicate an angle and its rendered export even
 * when the API gives them different primary ids.
 */
export function getClipIdentityAliases(item = {}) {
  const aliases = new Set();
  const add = (prefix, value) => {
    const normalized = normalizeIdentityToken(String(value || ''));
    if (normalized) aliases.add(`${prefix}:${normalized}`);
  };

  if (item.clip_id) add('clip', item.clip_id);
  if (item.angle_id) add('angle', item.angle_id);
  if (item.project_name) add('project', item.project_name);
  if (item.projectName) add('project', item.projectName);
  if (item.export_id) add('export', item.export_id);
  if (item.path) add('media', item.path);
  if (item.video_url) add('media', item.video_url);
  if (item.export_path) add('media', item.export_path);
  if (item.rendered_video) add('media', item.rendered_video);
  if (item.name) add('name', item.name);

  return Array.from(aliases);
}

function hasKnownClipIdentity(item, knownAliases) {
  return getClipIdentityAliases(item).some(alias => knownAliases.has(alias));
}

function addClipAliases(item, knownAliases) {
  getClipIdentityAliases(item).forEach(alias => knownAliases.add(alias));
}

function findProductForExport(exp, products = []) {
  const productId = exp?.product_id || exp?.productId;
  const productCode = exp?.product_code || exp?.productCode;
  const productName = exp?.product_name || exp?.productName;
  return (products || []).find(product => (
    (productId && product.id === productId) ||
    (productCode && product.product_code === productCode) ||
    (productName && product.name === productName)
  )) || null;
}

/**
 * Load targets from localStorage or fallback to defaults.
 */
export function loadTargets() {
  try {
    const raw = typeof window !== 'undefined' ? localStorage.getItem(TARGETS_STORAGE_KEY) : null;
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        dailyCuts: Number(parsed.dailyCuts) || DEFAULT_TARGETS.dailyCuts,
        weeklyCuts: Number(parsed.weeklyCuts) || DEFAULT_TARGETS.weeklyCuts,
        dailyPosts: Number(parsed.dailyPosts) || DEFAULT_TARGETS.dailyPosts,
      };
    }
  } catch (e) {
    // Ignore error
  }
  return { ...DEFAULT_TARGETS };
}

/**
 * Save targets to localStorage.
 */
export function saveTargets(targets) {
  try {
    if (typeof window !== 'undefined') {
      localStorage.setItem(TARGETS_STORAGE_KEY, JSON.stringify(targets));
    }
  } catch (e) {
    // Ignore error
  }
}

/**
 * Load playbook notes.
 */
export function loadPlaybookNotes() {
  try {
    const raw = typeof window !== 'undefined' ? localStorage.getItem(PLAYBOOK_STORAGE_KEY) : null;
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed.map(note => ({
          ...note,
          images: Array.isArray(note.images) ? note.images : (note.imageUrl ? [note.imageUrl] : []),
          imageUrl: note.imageUrl || (note.images && note.images[0]) || undefined,
        }));
      }
    }
  } catch (e) {
    // Ignore error
  }
  // Default starter notes if empty
  return [
    {
      id: 'note-starter-1',
      text: 'ฮุกเปิดคลิปอย่าเกริ่นเวิ่นเว้อ 0.5 วินาทีแรกต้องมีภาพสินค้าและปัญหากระแทกตาคนดูทันที',
      createdAt: '2026-09-12T10:00:00.000Z',
      tag: 'Hook',
      images: [],
    },
    {
      id: 'note-starter-2',
      text: 'คลิปรีวิวอุปกรณ์อิเล็กทรอนิกส์ คนดูชอบฟังเสียงคลิกปุ่ม / เสียงพัดลมจริง อย่าลืมเปิดเสียง SFX ให้ชัด',
      createdAt: '2026-09-12T14:30:00.000Z',
      tag: 'Audio',
      images: [],
    }
  ];
}

/**
 * Save playbook notes.
 */
export function savePlaybookNotes(notes) {
  try {
    if (typeof window !== 'undefined') {
      localStorage.setItem(PLAYBOOK_STORAGE_KEY, JSON.stringify(notes));
    }
  } catch (e) {
    // Ignore error
  }
}

/**
 * Add a new idea or ref note to the collection.
 */
export function addPlaybookNote(note, currentNotes = []) {
  const images = Array.isArray(note.images)
    ? note.images
    : (note.imageUrl ? [note.imageUrl] : []);

  const newNote = {
    id: note.id || `idea-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    text: note.text || '',
    url: note.url ? note.url.trim() : undefined,
    imageUrl: images[0] || undefined,
    images: images,
    tag: note.tag || 'Hook',
    productId: note.productId || undefined,
    productName: note.productName || undefined,
    productCode: note.productCode || undefined,
    createdAt: note.createdAt || new Date().toISOString(),
    aiAnalysis: note.aiAnalysis || undefined,
  };
  const updated = [newNote, ...currentNotes.filter(n => n.id !== newNote.id)];
  savePlaybookNotes(updated);
  return updated;
}

/**
 * Delete an idea or ref note.
 */
export function deletePlaybookNote(noteId, currentNotes = []) {
  const updated = currentNotes.filter(n => n.id !== noteId);
  savePlaybookNotes(updated);
  return updated;
}

/**
 * Format a note into a clean, professional summary text to share with team or boss.
 */
export function formatNoteForSharing(note) {
  if (!note) return '';
  const lines = [];
  const prod = note.productName ? `${note.productName} ${note.productCode ? `[${note.productCode}]` : ''}` : 'ทั่วไป (ไม่ระบุสินค้า)';
  lines.push(`📌 [ไอเดีย & เรฟวิดีโอ] สินค้า: ${prod}`);
  if (note.tag) lines.push(`🏷️ หมวดหมู่: ${note.tag}`);
  if (note.text) lines.push(`📝 ไอเดีย/จุดเด่น: ${note.text}`);
  if (note.url) lines.push(`🔗 ลิงก์เรฟ: ${note.url}`);

  const imgs = Array.isArray(note.images) && note.images.length > 0
    ? note.images
    : (note.imageUrl ? [note.imageUrl] : []);

  if (imgs.length > 0) {
    lines.push(`🖼️ ภาพประกอบ (${imgs.length} รูป):`);
    imgs.forEach((img, idx) => {
      // If relative URL from server, create full link
      const fullUrl = img.startsWith('http') || img.startsWith('data:')
        ? img
        : (typeof window !== 'undefined' ? `${window.location.origin}${img}` : img);
      lines.push(`   - ภาพที่ ${idx + 1}: ${fullUrl}`);
    });
  }
  return lines.join('\n');
}

/**
 * Update an existing idea or ref note.
 */
export function updatePlaybookNote(noteId, updates = {}, currentNotes = []) {
  const updated = currentNotes.map(n => {
    if (n.id === noteId) {
      const mergedImages = Array.isArray(updates.images)
        ? updates.images
        : (updates.imageUrl ? [updates.imageUrl] : n.images || (n.imageUrl ? [n.imageUrl] : []));
      return {
        ...n,
        ...updates,
        images: mergedImages,
        imageUrl: mergedImages[0] || updates.imageUrl || n.imageUrl,
        updatedAt: new Date().toISOString()
      };
    }
    return n;
  });
  savePlaybookNotes(updated);
  return updated;
}

/**
 * Detect social / video platform from URL.
 */
export function detectRefPlatform(url = '') {
  if (!url || typeof url !== 'string') return null;
  const lower = url.toLowerCase();
  if (lower.includes('tiktok.com') || lower.includes('vt.tiktok')) return 'tiktok';
  if (lower.includes('pinterest.com') || lower.includes('pin.it')) return 'pinterest';
  if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'youtube';
  if (lower.includes('instagram.com')) return 'instagram';
  if (lower.startsWith('http://') || lower.startsWith('https://')) return 'web';
  return null;
}

/**
 * Helper to get Monday 00:00:00 of the week for a given date.
 */
export function getMondayOfWeek(d = new Date()) {
  const date = new Date(d);
  const day = date.getDay(); // 0 is Sunday, 1 is Monday...
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  date.setDate(diff);
  date.setHours(0, 0, 0, 0);
  return date;
}

/**
 * Helper to get Sunday 23:59:59 of the week for a given date.
 */
export function getSundayOfWeek(d = new Date()) {
  const mon = getMondayOfWeek(d);
  const sun = new Date(mon);
  sun.setDate(mon.getDate() + 6);
  sun.setHours(23, 59, 59, 999);
  return sun;
}

/**
 * Check if two dates fall on the same calendar day.
 */
export function isSameDay(d1, d2) {
  if (!d1 || !d2) return false;
  const a = new Date(d1);
  const b = new Date(d2);
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/**
 * Parse an entity date (checks status_updated_at, posted_at, updated_at, created_at, mtime)
 */
function extractEntityDate(item) {
  if (!item) return null;
  const val = item.status_updated_at || item.posted_at || item.updated_at || item.created_at || item.mtime || item.timestamp;
  if (!val) return null;
  const d = new Date(val);
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Calculate production statistics for today and this week.
 */
export function calculateProductionStats(products = [], exports = [], targets = DEFAULT_TARGETS, now = new Date()) {
  const monday = getMondayOfWeek(now);
  const sunday = getSundayOfWeek(now);
  const monMs = monday.getTime();
  const sunMs = sunday.getTime();

  let dailyCutsCount = 0;
  let weeklyCutsCount = 0;
  let dailyPostsCount = 0;

  // Track unique exported clips / rendered angles
  const countedCutAliases = new Set();
  const countedPostAliases = new Set();
  const dailyCutSources = new Set();
  const weeklyCutSources = new Set();
  const dailyPostSources = new Set();

  // 1. Process Exports
  (exports || []).forEach(exp => {
    const d = extractEntityDate(exp);
    if (!d) return;
    const t = d.getTime();

    // Check Cuts. Use all known aliases so an export and its angle count once.
    const expAliases = getClipIdentityAliases(exp);
    const expSource = expAliases[0];
    if (expAliases.length > 0 && !hasKnownClipIdentity(exp, countedCutAliases)) {
      if (isSameDay(d, now)) {
        dailyCutsCount++;
        addClipAliases(exp, countedCutAliases);
        if (expSource) dailyCutSources.add(expSource);
      }
      if (t >= monMs && t <= sunMs) {
        weeklyCutsCount++;
        addClipAliases(exp, countedCutAliases);
        if (expSource) weeklyCutSources.add(expSource);
      }
    }

    // Check Posts
    if (exp.is_posted && expAliases.length > 0 && !hasKnownClipIdentity(exp, countedPostAliases)) {
      const postDate = exp.posted_at ? new Date(exp.posted_at) : d;
      if (isNaN(postDate.getTime())) return;
      if (isSameDay(postDate, now)) {
        dailyPostsCount++;
        addClipAliases(exp, countedPostAliases);
        if (expSource) dailyPostSources.add(expSource);
      }
    }
  });

  // 2. Process Products & Angles (to catch in-progress or freshly rendered angles)
  (products || []).forEach(prod => {
    (prod.angles || []).forEach(ang => {
      const d = extractEntityDate(ang);
      const normalizedAngle = {
        ...ang,
        angle_id: ang.angle_id || `${prod.id}_${ang.angle_name || ang.hook_title || 'untitled'}`,
      };
      const angleAliases = getClipIdentityAliases(normalizedAngle);
      const angleSource = angleAliases[0];
      if (!d || angleAliases.length === 0 || hasKnownClipIdentity(normalizedAngle, countedCutAliases)) return;

      const t = d.getTime();
      const isRendered = ang.status === 'rendered' || ang.status === 'posted' || ang.is_posted;

      if (isRendered) {
        if (isSameDay(d, now)) {
          dailyCutsCount++;
          addClipAliases(normalizedAngle, countedCutAliases);
          if (angleSource) dailyCutSources.add(angleSource);
        }
        if (t >= monMs && t <= sunMs) {
          weeklyCutsCount++;
          addClipAliases(normalizedAngle, countedCutAliases);
          if (angleSource) weeklyCutSources.add(angleSource);
        }
      }

      if ((ang.is_posted || ang.status === 'posted') && !hasKnownClipIdentity(normalizedAngle, countedPostAliases)) {
        const postDate = ang.posted_at ? new Date(ang.posted_at) : d;
        if (isNaN(postDate.getTime())) return;
        if (isSameDay(postDate, now)) {
          dailyPostsCount++;
          addClipAliases(normalizedAngle, countedPostAliases);
          if (angleSource) dailyPostSources.add(angleSource);
        }
      }
    });
  });

  const dailyCutsTarget = Math.max(1, targets.dailyCuts || DEFAULT_TARGETS.dailyCuts);
  const weeklyCutsTarget = Math.max(1, targets.weeklyCuts || DEFAULT_TARGETS.weeklyCuts);
  const dailyPostsTarget = Math.max(1, targets.dailyPosts || DEFAULT_TARGETS.dailyPosts);

  return {
    dailyCuts: {
      current: dailyCutsCount,
      target: dailyCutsTarget,
      pct: Math.min(100, Math.round((dailyCutsCount / dailyCutsTarget) * 100)),
      remaining: Math.max(0, dailyCutsTarget - dailyCutsCount),
      sourceIds: Array.from(dailyCutSources),
    },
    weeklyCuts: {
      current: weeklyCutsCount,
      target: weeklyCutsTarget,
      pct: Math.min(100, Math.round((weeklyCutsCount / weeklyCutsTarget) * 100)),
      remaining: Math.max(0, weeklyCutsTarget - weeklyCutsCount),
      monday,
      sunday,
      sourceIds: Array.from(weeklyCutSources),
    },
    dailyPosts: {
      current: dailyPostsCount,
      target: dailyPostsTarget,
      pct: Math.min(100, Math.round((dailyPostsCount / dailyPostsTarget) * 100)),
      remaining: Math.max(0, dailyPostsTarget - dailyPostsCount),
      sourceIds: Array.from(dailyPostSources),
    },
    contract: PRODUCER_INSIGHTS_CONTRACT,
    source: 'product_store_and_exports',
  };
}

/**
 * Filter and categorize actionable items for the daily queue.
 */
export function getDailyActionQueue(products = [], exports = []) {
  const readyToPost = [];
  const readyToCut = [];
  const needsFootage = [];

  // 1. Ready to post: rendered angles or unposted exports
  (products || []).forEach(prod => {
    (prod.angles || []).forEach(ang => {
      const isRendered = ang.status === 'rendered' && !ang.is_posted;
      if (isRendered) {
        readyToPost.push({
          type: 'angle_rendered',
          id: ang.angle_id,
          productId: prod.id,
          updatedAt: ang.status_updated_at || ang.updated_at || ang.created_at,
          title: ang.hook_title || ang.angle_name || prod.name,
          productName: prod.name,
          productCode: prod.product_code,
          parentProduct: prod,
          angle: ang,
          exportPath: ang.export_path || ang.rendered_video,
          caption: ang.tiktok_caption || '',
          hashtags: ang.tiktok_hashtags || '',
        });
      }
    });
  });

  // Also include standalone exports that are not posted
  (exports || []).forEach(exp => {
    if (!exp.is_posted) {
      const alreadyInList = readyToPost.some(item => {
        const itemIdentity = {
          ...(item.angle || {}),
          export_id: item.id,
          export_path: item.exportPath,
          name: item.title,
        };
        return hasKnownClipIdentity(exp, new Set(getClipIdentityAliases(itemIdentity)));
      });
      if (!alreadyInList) {
        const parentProduct = findProductForExport(exp, products);
        const exportName = exp.name || (exp.path ? exp.path.replace(/\\/g, '/').split('/').pop() : null) || exp.export_id || 'คลิปตัดเสร็จ';
        readyToPost.push({
          type: 'export_file',
          id: exp.export_id || exp.name,
          productId: parentProduct?.id || exp.product_id || exp.productId,
          title: exportName.toString().replace(/\.mp4$/i, ''),
          productName: parentProduct?.name || exp.product_name || 'คลิปตัดเสร็จ',
          productCode: parentProduct?.product_code || exp.product_code || exp.productCode,
          parentProduct,
          updatedAt: exp.modified_time || exp.modified || exp.created_at || exp.timestamp,
          exportPath: exp.path,
          caption: '',
          hashtags: '',
        });
      }
    }
  });

  // 2. Ready to cut: in_production angles OR scripted angles with available raw footage
  (products || []).forEach(prod => {
    const hasRawVideos = (prod.raw_videos && prod.raw_videos.length > 0) || (prod.videos && prod.videos.length > 0);
    (prod.angles || []).forEach(ang => {
      if (ang.is_posted) return;

      if (ang.status === 'in_production') {
        readyToCut.push({
          id: ang.angle_id,
          status: 'in_production',
          productId: prod.id,
          updatedAt: ang.status_updated_at || ang.updated_at || ang.created_at,
          title: ang.hook_title || ang.angle_name || prod.name,
          productName: prod.name,
          productCode: prod.product_code,
          projectName: ang.project_name,
          parentProduct: prod,
          angle: ang,
          hasFootage: true,
        });
      } else if (ang.status === 'scripted' && hasRawVideos) {
        readyToCut.push({
          id: ang.angle_id,
          status: 'scripted',
          productId: prod.id,
          updatedAt: ang.status_updated_at || ang.updated_at || ang.created_at,
          title: ang.hook_title || ang.angle_name || prod.name,
          productName: prod.name,
          productCode: prod.product_code,
          projectName: ang.project_name,
          parentProduct: prod,
          angle: ang,
          hasFootage: true,
        });
      } else if (ang.status === 'scripted' && !hasRawVideos) {
        needsFootage.push({
          id: ang.angle_id,
          status: 'scripted',
          productId: prod.id,
          updatedAt: ang.status_updated_at || ang.updated_at || ang.created_at,
          title: ang.hook_title || ang.angle_name || prod.name,
          productName: prod.name,
          productCode: prod.product_code,
          parentProduct: prod,
          angle: ang,
          hasFootage: false,
        });
      }
    });
  });

  // Apply round-robin product diversification:
  // Split readyToCut into in_production (urgent) and scripted, diversify each, then combine
  const inProd = readyToCut.filter(i => i.status === 'in_production');
  const scripted = readyToCut.filter(i => i.status !== 'in_production');
  const diversifiedCut = [
    ...diversifyByProduct(inProd),
    ...diversifyByProduct(scripted),
  ];
  const diversifiedFootage = diversifyByProduct(needsFootage);

  // Calculate unique products across the action queue for filtering
  const allActionItems = [...readyToPost, ...diversifiedCut, ...diversifiedFootage];
  const productCountMap = new Map();
  allActionItems.forEach(item => {
    const matchedProduct = item.parentProduct || findProductForExport(item, products);
    const key = matchedProduct?.id || item.productId || item.productCode || item.productName;
    if (!key) return;
    if (!productCountMap.has(key)) {
      productCountMap.set(key, {
        id: matchedProduct?.id || item.productId || key,
        code: matchedProduct?.product_code || item.productCode || '',
        name: matchedProduct?.name || item.productName || key,
        count: 0,
      });
    }
    productCountMap.get(key).count++;
  });

  return {
    readyToPost,
    readyToCut: diversifiedCut,
    needsFootage: diversifiedFootage,
    productsInQueue: Array.from(productCountMap.values()),
    summary: {
      total: allActionItems.length,
      readyToPost: readyToPost.length,
      readyToCut: diversifiedCut.length,
      needsFootage: diversifiedFootage.length,
    },
  };
}

/**
 * Convert either the canonical AI proposal fields or the legacy aliases into
 * the payload accepted by the product angle API.
 */
export function buildAnglePayload(proposal = {}) {
  const hookCategory = proposal.hook_category || 'curiosity';
  return {
    name: proposal.name || proposal.angle_name || 'มุมมองจากเรฟ',
    hook: proposal.hook || proposal.hook_title || '',
    hook_category: hookCategory,
    shoot_brief: proposal.shoot_brief || proposal.shoot_angle_brief || '',
    script: proposal.script || proposal.script_brief || '',
    tags: [hookCategory, 'ref-inspired'].filter(Boolean),
  };
}

/**
 * Select one actionable item using an explicit priority policy.
 * Posting a rendered clip outranks editing, while blocked footage remains
 * visible but never displaces work that can ship now.
 */
export function getNextAction(actionQueue = {}, now = new Date()) {
  const groups = [
    ['post', actionQueue.readyToPost || [], 300, 'เรนเดอร์เสร็จแล้วและยังไม่โพสต์'],
    ['cut', actionQueue.readyToCut || [], 200, 'วัตถุดิบพร้อมสำหรับตัดต่อ'],
    ['footage', actionQueue.needsFootage || [], 100, 'สคริปต์พร้อม แต่ยังขาดวัตถุดิบ'],
  ];

  const candidates = groups.flatMap(([type, items, baseScore, reason]) => items.map((item, index) => {
    const updatedAt = item.updatedAt || item.angle?.status_updated_at || item.angle?.created_at;
    const updatedDate = extractEntityDate({ updated_at: updatedAt });
    const ageHours = updatedDate
      ? Math.max(0, (now.getTime() - updatedDate.getTime()) / 3600000)
      : 0;
    const urgencyBonus = Math.min(72, Math.round(ageHours));
    return {
      type,
      item,
      priorityScore: baseScore + urgencyBonus,
      priorityReason: reason,
      updatedAt,
      sourceIndex: index,
    };
  }));

  candidates.sort((a, b) => (
    b.priorityScore - a.priorityScore ||
    (new Date(a.updatedAt || 0).getTime() || 0) - (new Date(b.updatedAt || 0).getTime() || 0) ||
    a.sourceIndex - b.sourceIndex
  ));

  const selected = candidates[0];
  if (!selected) return null;

  const labels = {
    post: {
      badge: '🚨 เร่งด่วนอันดับ 1',
      title: 'ปล่อยคลิปนี้ลง TikTok ด่วนเพื่อดันยอดขาย!',
      description: 'วิดีโอเรนเดอร์เสร็จแล้ว รอโพสต์ลง TikTok',
    },
    cut: {
      badge: '🎬 ภารกิจถัดไป',
      title: 'ตัดต่อคลิปนี้ทันที วัตถุดิบพร้อมแล้ว!',
      description: selected.item.projectName
        ? `ไทม์ไลน์: ${selected.item.projectName}`
        : 'วัตถุดิบและสคริปต์พร้อมตัดต่อทันที',
    },
    footage: {
      badge: '📝 ถ่ายคลิปเพิ่ม',
      title: 'เตรียมวัตถุดิบและดู Shot List สินค้านี้',
      description: 'สคริปต์พร้อมแล้ว ขาดคลิปถ่ายจริง',
    },
  };

  return {
    ...selected,
    ...labels[selected.type],
    contract: PRODUCER_INSIGHTS_CONTRACT,
  };
}

/**
 * Distributes queue items across products in a balanced round-robin fashion
 * so no single product with many angles dominates the daily feed.
 */
export function diversifyByProduct(items = []) {
  if (!items || items.length <= 1) return items || [];

  const groups = new Map();
  items.forEach(item => {
    const key = item.parentProduct?.id || item.productCode || item.productName || 'misc';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  });

  const result = [];
  let addedInRound = true;
  let round = 0;

  while (addedInRound) {
    addedInRound = false;
    for (const list of groups.values()) {
      if (round < list.length) {
        result.push(list[round]);
        addedInRound = true;
      }
    }
    round++;
  }

  return result;
}

/**
 * Generate a motivating, intelligent greeting calling the user "เจ้านาย"
 */
export function generateBossGreeting({ stats, actionQueue, now = new Date() }) {
  const hours = now.getHours();
  let timeGreeting = 'สวัสดีครับเจ้านาย!';
  if (hours >= 5 && hours < 12) timeGreeting = 'อรุณสวัสดิ์ครับเจ้านาย!';
  else if (hours >= 12 && hours < 18) timeGreeting = 'ช่วงบ่ายลุยต่อครับเจ้านาย!';
  else if (hours >= 18 && hours < 22) timeGreeting = 'ช่วงค่ำคนดูแน่นมากครับเจ้านาย!';
  else timeGreeting = 'ดึกแล้วยังฟิตอยู่เลยนะเจ้านาย!';

  const { dailyCuts, weeklyCuts, dailyPosts } = stats || {
    dailyCuts: { current: 0, target: 5, remaining: 5 },
    weeklyCuts: { current: 0, target: 35, remaining: 35 },
    dailyPosts: { current: 0, target: 3, remaining: 3 },
  };

  const pendingPostsCount = actionQueue?.readyToPost?.length || 0;
  const pendingCutsCount = actionQueue?.readyToCut?.length || 0;

  // Case 1: Has ready to post clips and haven't posted yet today
  if (dailyPosts.current === 0 && pendingPostsCount > 0) {
    return {
      title: `${timeGreeting} วันนี้ยังไม่ได้ลงคลิปเลยนะ!`,
      message: `มีคลิปตัดต่อเสร็จรอส่ง TikTok อยู่ ${pendingPostsCount} คลิป รีบปล่อยก่อนคนเข้านอน ยอดวิวจะพุ่งแรงครับ!`,
      badge: '🚨 รอลงคลิปด่วน',
      badgeColor: 'from-rose-500 to-amber-500',
      actionPrompt: 'ส่งคลิป TikTok ทันที',
      actionTab: 'post',
    };
  }

  // Case 2: Daily cuts target already completed
  if (dailyCuts.current >= dailyCuts.target) {
    return {
      title: `${timeGreeting} วันนี้ฟาดเป้าแตกแล้ว!`,
      message: `ตัดไปแล้ว ${dailyCuts.current}/${dailyCuts.target} คลิป ครบโควตาวันนี้อย่างงดงาม จะพักชิลล์หรือปั๊มยอดต่อให้สัปดาห์นี้ถึง ${weeklyCuts.target} คลิปดีครับ?`,
      badge: '🔥 ทะลุเป้าวันนี้',
      badgeColor: 'from-emerald-500 to-teal-500',
      actionPrompt: 'ดูคลิปในคลังผลงาน',
      actionTab: 'gallery',
    };
  }

  // Case 3: In progress with pending cuts
  if (pendingCutsCount > 0) {
    return {
      title: `${timeGreeting} วันนี้ตัดไปแล้ว ${dailyCuts.current} คลิป!`,
      message: `ยังเหลืออีก ${dailyCuts.remaining} คลิปจะครบเป้าหมายวันนี้ และสัปดาห์นี้ทำไปแล้ว ${weeklyCuts.current}/${weeklyCuts.target} คลิป มีวัตถุดิบพร้อมตัดรออยู่ ${pendingCutsCount} คลิป ลุยกันเลยครับ!`,
      badge: `⚡ เหลืออีก ${dailyCuts.remaining} คลิปวันนี้`,
      badgeColor: 'from-amber-500 to-orange-500',
      actionPrompt: 'เปิดตัดต่อคลิปถัดไป',
      actionTab: 'cut',
    };
  }

  // Case 4: Default welcoming
  return {
    title: `${timeGreeting} พร้อมลุยสร้างยอดขายหรือยังครับ?`,
    message: `สัปดาห์นี้ทำไปแล้ว ${weeklyCuts.current} คลิป (เหลืออีก ${weeklyCuts.remaining} คลิปจะครบเป้า 35 คลิป) เตรียมสคริปต์แล้วลุยต่อได้เลยครับ!`,
    badge: `🎯 สัปดาห์นี้: ${weeklyCuts.current}/${weeklyCuts.target}`,
    badgeColor: 'from-cyan-500 to-blue-500',
    actionPrompt: 'เปิด Script Lab',
    actionTab: 'script',
  };
}

/**
 * Analyze content performance with an evidence contract.
 * The recommendation text is heuristic, but every measured claim carries
 * the sample, period, baseline and source row used to derive it.
 */
export function analyzeContentPerformance(tiktokStats = [], _products = []) {
  const rawRows = Array.isArray(tiktokStats)
    ? tiktokStats
    : (Array.isArray(tiktokStats?.rows) ? tiktokStats.rows : (tiktokStats?.posts || []));
  const rows = rawRows
    .map((row) => {
      if (!row || typeof row !== 'object') return row;
      const nestedMetrics = row.metrics && typeof row.metrics === 'object' ? row.metrics : {};
      return {
        ...row,
        ...nestedMetrics,
        video_title: row.video_title || row.title || row.angle_title || row.clip_file,
        posted_at: row.posted_at || row.postedAt || row.created_at,
      };
    })
    .filter(row => row && typeof row === 'object');
  const metricRows = rows.map((row, index) => ({
    row,
    index,
    views: Math.max(0, Number(row.views) || 0),
    likes: Math.max(0, Number(row.likes) || 0),
    shares: Math.max(0, Number(row.shares) || 0),
    comments: Math.max(0, Number(row.comments) || 0),
    postedAt: row.posted_at || row.postedAt || row.created_at || '',
  }));

  if (metricRows.length === 0) {
    return {
      hasData: false,
      method: 'heuristic',
      source: 'tiktok_stats_unavailable',
      sampleSize: 0,
      confidence: 'none',
      period: { from: null, to: null },
      metrics: { averageViews: 0, medianViews: 0, engagementRate: 0 },
      topPerformer: null,
      topTakeaways: [
        'คลิปที่เปิดด้วย Hook ปัญหาหรือคำเตือน มักดึงยอดวิวช่วง 3 วินาทีแรกได้ดีกว่าการเปิดด้วยชื่อแบรนด์',
        'การใส่ J-Cut ให้เสียง Whoosh หรือประโยคถัดไปเริ่มก่อนภาพตัด 200ms ช่วยลดการปัดหนีได้จริง',
        'คลิปรีวิวที่มีการแสดงขนาดหรือการใช้งานจริง (Demo) ช่วยเพิ่มอัตราการคลิกตะกร้าสินค้าได้ชัดเจน',
      ],
      improvementAdvice: 'ยังไม่มีสถิติที่ซิงก์จาก TikTok Studio กดปุ่ม [ซิงก์สถิติ] ในหน้า Performance เพื่อดึงข้อมูลจริงมาวิเคราะห์',
    };
  }

  const sorted = [...metricRows].sort((a, b) => b.views - a.views);
  const top = sorted[0];
  const viewValues = metricRows.map(item => item.views).sort((a, b) => a - b);
  const totalViews = viewValues.reduce((sum, value) => sum + value, 0);
  const totalEngagement = metricRows.reduce((sum, item) => sum + item.likes + item.shares + item.comments, 0);
  const medianViews = viewValues.length % 2
    ? viewValues[Math.floor(viewValues.length / 2)]
    : (viewValues[viewValues.length / 2 - 1] + viewValues[viewValues.length / 2]) / 2;
  const averageViews = totalViews / metricRows.length;
  const engagementRate = totalViews > 0 ? (totalEngagement / totalViews) * 100 : 0;
  const datedRows = metricRows
    .map(item => ({ ...item, date: item.postedAt ? new Date(item.postedAt) : null }))
    .filter(item => item.date && !Number.isNaN(item.date.getTime()))
    .sort((a, b) => a.date - b.date);
  const period = {
    from: datedRows[0]?.date.toISOString() || null,
    to: datedRows[datedRows.length - 1]?.date.toISOString() || null,
  };
  const topVsAverage = averageViews > 0 ? Math.round((top.views / averageViews) * 100) : 0;
  const topVsMedian = medianViews > 0 ? Math.round((top.views / medianViews) * 100) : 0;
  const sourceId = top.row.id || top.row.video_id || top.row.export_id || top.row.video_title || `row-${top.index}`;
  const topPerformer = {
    id: sourceId,
    title: top.row.video_title || 'คลิปท็อป',
    views: top.views,
    likes: top.likes,
    shares: top.shares,
    comments: top.comments,
    postedAt: top.postedAt,
    sourceId,
    metricSnapshot: { views: top.views, likes: top.likes, shares: top.shares, comments: top.comments },
  };

  const takeaways = [
    topVsAverage >= 150
      ? `คลิป "${topPerformer.title}" ทำ ${top.views.toLocaleString()} วิว หรือ ${topVsAverage}% ของค่าเฉลี่ยจาก ${metricRows.length} คลิป จึงควรถอด Hook/มุมเปิดไปทดลองซ้ำ`
      : `คลิป "${topPerformer.title}" เป็นอันดับหนึ่งที่ ${top.views.toLocaleString()} วิว แต่ยังไม่เกิน 1.5 เท่าของค่าเฉลี่ย ควรทดสอบ Hook เพิ่มก่อนสรุปเป็นสูตรหลัก`,
    engagementRate >= 5
      ? `อัตรา engagement รวมอยู่ที่ ${engagementRate.toFixed(2)}% จากยอดวิวทั้งหมด สัญญาณการมีส่วนร่วมอยู่ในระดับที่ควรรักษาไว้`
      : `อัตรา engagement รวมอยู่ที่ ${engagementRate.toFixed(2)}% ยังมีพื้นที่ให้ปรับ CTA, ราคา หรือจุดชวนคอมเมนต์ให้ชัดขึ้น`,
    averageViews > medianViews * 1.25
      ? `ค่าเฉลี่ย ${Math.round(averageViews).toLocaleString()} สูงกว่าค่ากลาง ${Math.round(medianViews).toLocaleString()} แปลว่าผลลัพธ์มีคลิปเด่นดันค่าเฉลี่ย ควรดูการกระจายรายคลิปด้วย`
      : `ค่าเฉลี่ย ${Math.round(averageViews).toLocaleString()} ใกล้ค่ากลาง ${Math.round(medianViews).toLocaleString()} ผลลัพธ์ค่อนข้างสม่ำเสมอ เหมาะกับการทำซ้ำ format ที่ชนะ`,
  ];

  const improvement = topVsMedian >= 200
    ? `เริ่มจากถอดองค์ประกอบของคลิปท็อปที่ทำได้ ${topVsMedian}% ของค่ากลาง แล้วทำ A/B Hook อย่างน้อย 2 แบบ โดยวัดผลจากชุดข้อมูลรอบถัดไปครับ`
    : engagementRate < 2
      ? 'รอบถัดไปให้เพิ่ม CTA ที่ชัดเจนและคำถามปลายเปิด แล้วติดตาม likes, shares และ comments แยกจากยอดวิวครับ'
      : 'รอบถัดไปให้คง format ที่ทำผลงานสม่ำเสมอ แล้วทดสอบ Hook หรือข้อเสนอสินค้าเพิ่มทีละตัวแปรครับ';

  return {
    hasData: true,
    method: 'heuristic',
    source: 'tiktok_stats_latest',
    sampleSize: metricRows.length,
    confidence: metricRows.length >= 10 ? 'medium' : 'low',
    period,
    metrics: {
      averageViews: Math.round(averageViews),
      medianViews: Math.round(medianViews),
      engagementRate: Number(engagementRate.toFixed(2)),
      topVsAverage,
      topVsMedian,
    },
    topPerformer,
    topTakeaways: takeaways,
    improvementAdvice: improvement,
  };
}

/**
 * Calculate pacing towards weekly quota based on days remaining.
 */
export function calculateWeeklyPacing(stats, now = new Date()) {
  const day = now.getDay(); // 0 = Sun, 1 = Mon, ..., 6 = Sat
  // Days remaining in this week including today (Mon = 7, Tue = 6, ..., Sun = 1)
  const daysRemaining = 7 - ((day + 6) % 7);
  const remainingCuts = stats?.weeklyCuts?.remaining ?? 0;
  const targetDaily = stats?.dailyCuts?.target ?? 5;

  if (remainingCuts <= 0) {
    return {
      daysRemaining,
      dailyRequired: 0,
      paceStatus: 'completed',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
      paceAdvice: '🎉 เจ้านายพิชิตเป้าหมายรายสัปดาห์เรียบร้อยแล้ว!',
    };
  }

  const dailyRequired = Math.ceil(remainingCuts / daysRemaining);

  if (dailyRequired <= targetDaily) {
    return {
      daysRemaining,
      dailyRequired,
      paceStatus: 'on_track',
      badgeColor: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
      paceAdvice: `ตามแผนสบายๆ: ตัดต่อเฉลี่ยวันละ ~${dailyRequired} คลิป (เหลืออีก ${daysRemaining} วัน)`,
    };
  }

  return {
    daysRemaining,
    dailyRequired,
    paceStatus: 'behind',
    badgeColor: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    paceAdvice: `ต้องเร่งสปีด: ตัดเฉลี่ยวันละ ~${dailyRequired} คลิป (เหลืออีก ${daysRemaining} วันในสัปดาห์นี้)`,
  };
}

/**
 * Automatically extract actionable notes from retrospective insights.
 */
export function autoSuggestPlaybookNotes(retrospective, currentNotes = []) {
  if (!retrospective) return [];
  const suggestions = [];
  const existingTexts = new Set((currentNotes || []).map(n => n.text?.trim()));

  (retrospective.topTakeaways || []).forEach((text, idx) => {
    let tag = 'Hook';
    if (text.includes('เสียง') || text.includes('SFX') || text.includes('เพลง')) tag = 'Audio';
    else if (text.includes('ภาพ') || text.includes('เดโม') || text.includes('Demo')) tag = 'Visual';
    else if (text.includes('ราคา') || text.includes('โปร') || text.includes('สเปก')) tag = 'Product';

    suggestions.push({
      id: `suggest-${idx}`,
      text: text,
      tag: tag,
      alreadySaved: existingTexts.has(text?.trim()),
    });
  });

  return suggestions;
}
