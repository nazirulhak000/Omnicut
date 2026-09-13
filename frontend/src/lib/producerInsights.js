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
      if (Array.isArray(parsed)) return parsed;
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
      tag: 'Hook'
    },
    {
      id: 'note-starter-2',
      text: 'คลิปรีวิวอุปกรณ์อิเล็กทรอนิกส์ คนดูชอบฟังเสียงคลิกปุ่ม / เสียงพัดลมจริง อย่าลืมเปิดเสียง SFX ให้ชัด',
      createdAt: '2026-09-12T14:30:00.000Z',
      tag: 'Audio'
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
  const nowMs = now.getTime();
  const monday = getMondayOfWeek(now);
  const sunday = getSundayOfWeek(now);
  const monMs = monday.getTime();
  const sunMs = sunday.getTime();

  let dailyCutsCount = 0;
  let weeklyCutsCount = 0;
  let dailyPostsCount = 0;

  // Track unique exported clips / rendered angles
  const countedCutKeys = new Set();
  const countedPostKeys = new Set();

  // 1. Process Exports
  (exports || []).forEach(exp => {
    const d = extractEntityDate(exp);
    if (!d) return;
    const t = d.getTime();

    // Check Cuts
    const expKey = exp.export_id || exp.path || exp.name;
    if (expKey && !countedCutKeys.has(expKey)) {
      if (isSameDay(d, now)) {
        dailyCutsCount++;
        countedCutKeys.add(expKey);
      }
      if (t >= monMs && t <= sunMs) {
        weeklyCutsCount++;
        countedCutKeys.add(expKey);
      }
    }

    // Check Posts
    if (exp.is_posted && expKey && !countedPostKeys.has(expKey)) {
      const postDate = exp.posted_at ? new Date(exp.posted_at) : d;
      if (isSameDay(postDate, now)) {
        dailyPostsCount++;
        countedPostKeys.add(expKey);
      }
    }
  });

  // 2. Process Products & Angles (to catch in-progress or freshly rendered angles)
  (products || []).forEach(prod => {
    (prod.angles || []).forEach(ang => {
      const d = extractEntityDate(ang);
      const angKey = ang.angle_id || (prod.id + '_' + (ang.angle_name || ang.hook_title));
      if (!d || countedCutKeys.has(angKey)) return;

      const t = d.getTime();
      const isRendered = ang.status === 'rendered' || ang.status === 'posted' || ang.is_posted;

      if (isRendered) {
        if (isSameDay(d, now)) {
          dailyCutsCount++;
          countedCutKeys.add(angKey);
        }
        if (t >= monMs && t <= sunMs) {
          weeklyCutsCount++;
          countedCutKeys.add(angKey);
        }
      }

      if ((ang.is_posted || ang.status === 'posted') && !countedPostKeys.has(angKey)) {
        const postDate = ang.posted_at ? new Date(ang.posted_at) : d;
        if (isSameDay(postDate, now)) {
          dailyPostsCount++;
          countedPostKeys.add(angKey);
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
    },
    weeklyCuts: {
      current: weeklyCutsCount,
      target: weeklyCutsTarget,
      pct: Math.min(100, Math.round((weeklyCutsCount / weeklyCutsTarget) * 100)),
      remaining: Math.max(0, weeklyCutsTarget - weeklyCutsCount),
      monday,
      sunday,
    },
    dailyPosts: {
      current: dailyPostsCount,
      target: dailyPostsTarget,
      pct: Math.min(100, Math.round((dailyPostsCount / dailyPostsTarget) * 100)),
      remaining: Math.max(0, dailyPostsTarget - dailyPostsCount),
    },
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
      const alreadyInList = readyToPost.some(item => item.exportPath && item.exportPath.includes(exp.name));
      if (!alreadyInList) {
        readyToPost.push({
          type: 'export_file',
          id: exp.export_id || exp.name,
          title: exp.name.replace(/\.mp4$/i, ''),
          productName: exp.product_name || 'คลิปตัดเสร็จ',
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

  return {
    readyToPost,
    readyToCut,
    needsFootage,
  };
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
 * Analyze content performance and generate AI retrospective insights.
 */
export function analyzeContentPerformance(tiktokStats = [], products = []) {
  const rows = Array.isArray(tiktokStats) ? tiktokStats : (tiktokStats?.rows || []);

  if (!rows || rows.length === 0) {
    return {
      hasData: false,
      topPerformer: null,
      topTakeaways: [
        'คลิปที่เปิดด้วย Hook ปัญหาหรือคำเตือน มักดึงยอดวิวช่วง 3 วินาทีแรกได้ดีกว่าการเปิดด้วยชื่อแบรนด์',
        'การใส่ J-Cut ให้เสียง Whoosh หรือประโยคถัดไปเริ่มก่อนภาพตัด 200ms ช่วยลดการปัดหนีได้จริง',
        'คลิปรีวิวที่มีการแสดงขนาดหรือการใช้งานจริง (Demo) ช่วยเพิ่มอัตราการคลิกตะกร้าสินค้าได้ชัดเจน',
      ],
      improvementAdvice: 'ยังไม่มีสถิติที่ซิงก์จาก TikTok Studio กดปุ่ม [ซิงก์สถิติ] ในหน้า Performance เพื่อดึงข้อมูลจริงมาวิเคราะห์',
    };
  }

  // Find top performer by view count
  const sorted = [...rows].sort((a, b) => (Number(b.views) || 0) - (Number(a.views) || 0));
  const top = sorted[0];

  const takeaways = [
    `คลิป "${top.video_title || 'คลิปยอดนิยม'}" ทำยอดวิวสูงสุดที่ ${(Number(top.views) || 0).toLocaleString()} วิว เพราะฮุกเข้าประเด็นทันที`,
    'คลิปที่มีการเน้นป้ายราคาโปรและจุดคุ้มค่าช่วงท้าย ช่วยดันยอดแชร์และคอมเมนต์สอบถามพิกัดได้สูง',
    'ระยะเวลาคลิปที่กำลังดีสำหรับสินค้ารีวิวแอฟฟิลิเอตอยู่ที่ 35–45 วินาที กระชับ ไม่ยืดยาว',
  ];

  const improvement = (Number(top.views) || 0) > 1000
    ? 'สังเกตเห็นว่าคลิปที่มียอดวิวนำ มักใช้แคปชันที่ชวนให้คนหยุดดูและมีแฮชแท็กตรงกลุ่มเป้าหมาย 3-5 แท็ก แนะนำให้ใช้สูตรนี้กับคลิปถัดไปครับ'
    : 'ยอดวิวเฉลี่ยยังอยู่ในช่วงเริ่มต้น แนะนำให้ทดลองใช้ Hook สไตล์ "เตือนภัย/ข้อควรระวัง" หรือ "โปรไฟลุก" เพื่อเพิ่มหยุดนิ้วช่วง 3 วินาทีแรกครับ';

  return {
    hasData: true,
    topPerformer: {
      title: top.video_title || 'คลิปท็อป',
      views: Number(top.views) || 0,
      likes: Number(top.likes) || 0,
      shares: Number(top.shares) || 0,
      comments: Number(top.comments) || 0,
      postedAt: top.posted_at || '',
    },
    topTakeaways: takeaways,
    improvementAdvice: improvement,
  };
}
