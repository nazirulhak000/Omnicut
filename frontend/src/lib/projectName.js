/**
 * Project Name generation and sanitization utility.
 * Standard format: [short_product_name]_[angle_name]_[index]
 * e.g. "logitech_wave_keys_แกะกล่องว้าว_1"
 */

/**
 * Extracts a concise, clean product slug containing Brand + Model (2-3 words).
 * Strips bracketed marketing tags and excess fluff.
 * Note: Must include \p{M} so Thai vowels and tone marks (่, ้, ๊, ๋, ิ, ี, ึ, ื, etc.) are never stripped!
 * @param {string} productName
 * @param {number} maxWords
 * @param {number} maxChars
 * @returns {string}
 */
export function extractShortProductName(productName, maxWords = 3, maxChars = 28) {
  if (!productName || typeof productName !== 'string') {
    return 'สินค้า';
  }

  // Remove bracketed marketing tags like [ส่งฟรี], (แท้ 100%), etc.
  const cleaned = productName
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/\([^)]*\)/g, ' ')
    .replace(/[^\p{L}\p{M}\p{N}\s_-]/gu, ' ')
    .trim();

  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length === 0) return 'สินค้า';

  let pickedWords = [];
  let currentLen = 0;

  for (const word of words) {
    if (pickedWords.length >= maxWords) break;
    if (currentLen + word.length + (pickedWords.length > 0 ? 1 : 0) > maxChars) {
      if (pickedWords.length === 0) {
        pickedWords.push(word.slice(0, maxChars));
      }
      break;
    }
    pickedWords.push(word);
    currentLen += word.length + 1;
  }

  return pickedWords.join('_').toLowerCase();
}

export const ANGLE_SLUG_MAP = {
  spec_review: 'รีวิวสเปก',
  unboxing: 'แกะกล่องว้าว',
  pain_point: 'ปัญหาก่อนใช้',
  fomo_deal: 'โปรไฟลุก',
  comparison: 'เทียบของเดิม',
  life_hack: 'ทริกลึก',
  stop_scroll: 'เตือนภัย',
  niche_target: 'เจาะกลุ่ม',
  longterm_review: 'รีวิวใช้จริง',
  math_value: 'คำนวณคุ้มค่า',
};

/**
 * Cleans an angle or hook title into a concise slug (1-3 words, max 20 chars).
 * @param {object|string} angle
 * @param {number} fallbackIndex
 * @returns {string}
 */
export function cleanAngleSlug(angle, fallbackIndex = 0) {
  if (angle && typeof angle === 'object' && angle.angle_id && ANGLE_SLUG_MAP[angle.angle_id]) {
    return ANGLE_SLUG_MAP[angle.angle_id];
  }

  let raw = '';
  if (typeof angle === 'string') {
    raw = angle;
  } else if (angle && typeof angle === 'object') {
    raw = angle.angle_name || angle.hook_title || '';
  }

  // Strip variation selectors, ellipses, punctuation, and symbols while keeping Thai characters & marks
  const cleaned = raw
    .replace(/[\uFE00-\uFE0F]/g, '')
    .replace(/\.{2,}|…/g, ' ')
    .replace(/[^\p{L}\p{M}\p{N}\s_-]/gu, ' ')
    .trim();

  const words = cleaned
    .split(/\s+/)
    .map((w) => w.trim())
    .filter((w) => w && /[\p{L}\p{N}]/u.test(w));

  if (words.length === 0) {
    return `มุม${fallbackIndex + 1}`;
  }

  // Pick up to 2 words, max 24 chars
  let picked = [];
  let len = 0;
  for (const w of words) {
    if (picked.length >= 2) break;
    if (len + w.length + (picked.length > 0 ? 1 : 0) > 24) {
      if (picked.length === 0) picked.push(w.slice(0, 24));
      break;
    }
    picked.push(w);
    len += w.length + 1;
  }

  let result = picked.join('_');
  // Strip any trailing combining marks (vowels/tone marks) left over from slicing
  result = result.replace(/[\p{M}]+$/u, '');
  return result || `มุม${fallbackIndex + 1}`;
}

/**
 * Builds a collision-free project name according to the standard:
 * [short_product]_[angle]_[1, 2, 3...]
 * @param {object} params
 * @param {string} params.productName
 * @param {object|string} [params.angle]
 * @param {number} [params.angleIndex=0]
 * @param {Array<string|object>} [params.existingProjects=[]]
 * @returns {string}
 */
export function buildProjectName({
  productName = '',
  angle = null,
  angleIndex = 0,
  existingProjects = [],
}) {
  const shortProduct = extractShortProductName(productName);
  const angleSlug = cleanAngleSlug(angle, angleIndex);
  const base = `${shortProduct}_${angleSlug}`;

  const existingSet = new Set(
    (existingProjects || []).map((p) => {
      if (typeof p === 'string') return p.toLowerCase();
      if (p && p.project_name) return p.project_name.toLowerCase();
      return '';
    })
  );

  // Auto-increment version: _1, _2, _3...
  let version = 1;
  while (version < 100) {
    const candidate = `${base}_${version}`;
    if (!existingSet.has(candidate.toLowerCase())) {
      return candidate;
    }
    version++;
  }

  return `${base}_${Date.now().toString(36)}`;
}
