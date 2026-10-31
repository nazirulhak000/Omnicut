// Caption keyword highlighting -- a port of apply_kinetic_highlighting(),
// apply_kinetic_highlighting_en() and apply_bilingual_kinetic_highlighting()
// in scripts/subtitle/translation_service.py, so the canvas preview colours
// the same word of a burst that the ASS render colours (Preview = Render,
// AGENTS.md rule 9).
//
// Order (both sides): explicit *markers* / [markers] -> per-product custom
// keywords -> spec number (value + unit) -> hype/pain dictionary. One
// highlight per burst (markers excepted: every marker is coloured).
//
// The output is a list of segments `{ text, ass }` where `ass` is the ASS
// colour tag the render would wrap that run in (`&H00FFE600&` ...) or null for
// the caption's primary colour. Mapping a tag to the canvas colour is the
// caller's job (ASS_TO_PREVIEW_COLOR keeps the preview's existing values).
//
// The dictionaries live in kineticKeywords.json, asserted equal to the
// backend's by tests/test_preview_render_parity.py; the behaviour is pinned by
// tests/fixtures/sfx_highlight_parity_cases.json, run on both sides.
import KEYWORDS from './kineticKeywords.json' with { type: 'json' };

export const KINETIC_KEYWORDS_TH = KEYWORDS.th;
export const KINETIC_KEYWORDS_EN = KEYWORDS.en;

export const ASS_YELLOW = '&H0000E6FF&';
export const ASS_CYAN = '&H00FFE600&';
export const ASS_RED = '&H00303BFF&';
export const SPEC_HIGHLIGHT_COLOR = ASS_CYAN;

// The canvas colours the preview has always painted for each ASS tag.
export const ASS_TO_PREVIEW_COLOR = {
  [ASS_YELLOW]: '#FFE600',
  [ASS_CYAN]: '#00E5FF',
  [ASS_RED]: '#FF3B30',
};

// Python's `\d` (str pattern) is any Unicode decimal digit and its `\s` is
// str.isspace(); spelled out so the JS regex matches exactly the same text.
const PY_WS = '\\t\\n\\v\\f\\r \\x1c-\\x1f\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
export const SPEC_NUMBER_PATTERN = new RegExp(
  `(?<![A-Za-z0-9.,])\\p{Nd}+(?:[.,]\\p{Nd}+)?[${PY_WS}]?`
  + '(?:mAh|ms|mm|cm|GB|TB|Hz|W|ชม\\.|ชั่วโมง|นาที|วัตต์|นิ้ว)'
  + '(?![A-Za-z])',
  'u',
);

// Python's `\b` in a str pattern: a word character is str.isalnum() or "_".
const PY_W = '[\\p{L}\\p{N}_]';
const PY_B = `(?:(?<=${PY_W})(?!${PY_W})|(?<!${PY_W})(?=${PY_W}))`;
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
const wordRe = (kw) => new RegExp(`${PY_B}${escapeRe(kw)}${PY_B}`, 'iu');

const MARKER_RE = /(\*([^*]+)\*|\[([^\]]+)\])/g;
const THAI_CHAR_RE = /[฀-๿]/;
const pyLen = (s) => [...s].length;
const byLengthDesc = (list) => [...list].sort((a, b) => pyLen(b) - pyLen(a));

export function findSpecNumber(text) {
  if (!text) return null;
  const m = SPEC_NUMBER_PATTERN.exec(text);
  return m ? m[0] : null;
}

function plain(text) {
  return text ? [{ text, ass: null }] : [];
}

// Drop empty runs and merge neighbours of the same colour.
export function normalizeSegments(segments) {
  const out = [];
  for (const seg of segments) {
    if (!seg.text) continue;
    const last = out[out.length - 1];
    if (last && last.ass === seg.ass) last.text += seg.text;
    else out.push({ text: seg.text, ass: seg.ass });
  }
  return out;
}

function wrapAt(text, start, length, ass, thaiGap) {
  // _safe_replace_kw: a highlighted word glued to a Thai letter gets a space.
  const prefix = thaiGap && start > 0 && THAI_CHAR_RE.test(text[start - 1]) ? ' ' : '';
  return normalizeSegments([
    { text: text.slice(0, start) + prefix, ass: null },
    { text: text.slice(start, start + length), ass },
    { text: text.slice(start + length), ass: null },
  ]);
}

function wrapFirst(text, kw, ass) {
  const idx = text.indexOf(kw);
  return idx === -1 ? plain(text) : wrapAt(text, idx, kw.length, ass, true);
}

function markerSegments(text, chosen) {
  MARKER_RE.lastIndex = 0;
  if (!MARKER_RE.test(text)) return null;
  MARKER_RE.lastIndex = 0;
  const segments = [];
  let last = 0;
  for (const m of text.matchAll(MARKER_RE)) {
    segments.push({ text: text.slice(last, m.index), ass: null });
    segments.push({ text: m[2] ?? m[3], ass: chosen });
    last = m.index + m[0].length;
  }
  segments.push({ text: text.slice(last), ass: null });
  return normalizeSegments(segments);
}

/** apply_kinetic_highlighting (Thai line). */
export function highlightTh(text, { colorHint = null, customKeywords = null } = {}) {
  if (!text) return plain(text);
  const markers = markerSegments(text, colorHint || ASS_YELLOW);
  if (markers) return markers;
  if (text.includes('{\\c')) return plain(text);

  if (customKeywords && customKeywords.length) {
    for (const ckw of byLengthDesc(customKeywords)) {
      if (pyLen(ckw) >= 2 && text.includes(ckw)) return wrapFirst(text, ckw, colorHint || ASS_CYAN);
    }
  }

  const spec = findSpecNumber(text);
  if (spec) return wrapFirst(text, spec, colorHint || SPEC_HIGHLIGHT_COLOR);

  const order = colorHint ? [colorHint] : Object.keys(KINETIC_KEYWORDS_TH);
  for (const tag of order) {
    for (const kw of byLengthDesc(KINETIC_KEYWORDS_TH[tag] || [])) {
      if (text.includes(kw)) return wrapFirst(text, kw, tag);
    }
  }
  return plain(text);
}

/** apply_kinetic_highlighting_en (English line). */
export function highlightEn(text, { colorHint = null, customKeywords = null } = {}) {
  if (!text) return plain(text);
  const markers = markerSegments(text, colorHint || ASS_YELLOW);
  if (markers) return markers;
  if (text.includes('{\\c')) return plain(text);

  if (customKeywords && customKeywords.length) {
    for (const ckw of byLengthDesc(customKeywords)) {
      if (pyLen(ckw) < 2) continue;
      const m = wordRe(ckw).exec(text);
      if (m) return wrapAt(text, m.index, m[0].length, colorHint || ASS_CYAN, false);
    }
  }

  const spec = SPEC_NUMBER_PATTERN.exec(text);
  if (spec) return wrapAt(text, spec.index, spec[0].length, colorHint || SPEC_HIGHLIGHT_COLOR, false);

  const order = colorHint ? [colorHint] : Object.keys(KINETIC_KEYWORDS_EN);
  for (const tag of order) {
    for (const kw of byLengthDesc(KINETIC_KEYWORDS_EN[tag] || [])) {
      const m = wordRe(kw).exec(text);
      if (m) return wrapAt(text, m.index, m[0].length, tag, false);
    }
  }
  return plain(text);
}

const firstColor = (segments) => (segments.find((s) => s.ass !== null) || {}).ass || null;

const EN_STOPWORDS = new Set([
  'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'am', 'of', 'to', 'in',
  'on', 'at', 'for', 'with', 'and', 'or', 'but', 'if', 'it', 'its', 'this', 'that',
  'these', 'those', 'as', 'by', 'from', 'up', 'out', 'so', 'than', 'then', 'too',
  'very', 'can', 'will', 'just', 'not', 'no', 'do', 'does', 'did', 'you', 'your',
  'i', 'my', 'we', 'our', 'they', 'their', 'he', 'she', 'his', 'her', 'how', 'what',
  'who', 'why', 'when', 'where', 'all', 'any', 'more', 'most', 'some', 'such', 'own',
  'about', 'into', 'over', 'also', 'have', 'has', 'had', 'would', 'could', 'should',
]);

const TH_PARTICLES = new Set([
  'ครับ', 'ค่ะ', 'คะ', 'นะ', 'น่ะ', 'จ้า', 'เลย', 'ก็', 'ที่', 'ซึ่ง', 'และ', 'หรือ',
  'แต่', 'กับ', 'ของ', 'ใน', 'จะ', 'ได้', 'ให้', 'มา', 'ไป', 'อยู่', 'คือ', 'ว่า',
  'เป็น', 'มี', 'ไม่', 'แล้ว', 'ด้วย', 'อีก', 'มัน', 'เรา', 'เขา', 'ทั้ง', 'ทุก',
]);

/** _salient_word_en: longest non-stopword token. */
export function salientWordEn(text) {
  let best = null;
  for (const raw of text.match(/[A-Za-z][A-Za-z'-]*/g) || []) {
    if (EN_STOPWORDS.has(raw.toLowerCase()) || raw.length < 3) continue;
    if (!best || raw.length > best.length) best = raw;
  }
  return best;
}

/**
 * _salient_word_th. The render tokenizes with pythainlp (newmm); the browser
 * has no newmm, so ICU's Thai word segmenter stands in -- it usually picks the
 * same word but is not guaranteed to (the only approximate step here).
 */
export function salientWordTh(text) {
  let candidates;
  if (typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function') {
    const seg = new Intl.Segmenter('th', { granularity: 'word' });
    candidates = [...seg.segment(text)].map((s) => s.segment.trim()).filter(Boolean);
  } else {
    candidates = text.match(/[฀-๿]+/g) || [];
  }
  let best = null;
  for (const w of candidates) {
    if (TH_PARTICLES.has(w) || pyLen(w) < 3 || !THAI_CHAR_RE.test(w)) continue;
    if (!best || pyLen(w) > pyLen(best)) best = w;
  }
  return best;
}

/** _force_highlight */
function forceHighlight(segments, text, word, ass) {
  if (!word || !text.includes(word)) return segments;
  return wrapFirst(text, word, ass);
}

/**
 * apply_bilingual_kinetic_highlighting: the Thai and English lines of one
 * burst always end up with the same highlight colour.
 */
export function highlightBilingual(thText, enText, { customKeywords = null } = {}) {
  let th = highlightTh(thText, { customKeywords });
  let thColor = firstColor(th);
  let en = highlightEn(enText, { colorHint: thColor, customKeywords });
  const enColor = firstColor(en);

  if (!thColor && enColor) {
    th = highlightTh(thText, { colorHint: enColor, customKeywords });
    thColor = firstColor(th) ? enColor : null;
  }

  if (thColor && !enColor) {
    en = forceHighlight(en, enText, salientWordEn(enText), thColor);
  } else if (enColor && !thColor) {
    th = forceHighlight(th, thText, salientWordTh(thText), enColor);
  } else if (thColor && enColor && thColor !== enColor) {
    // Unreachable today (the English pass is hinted with the Thai colour);
    // the render rewrites every colour tag of the line, so everything from
    // the first highlight on takes the Thai colour.
    let seen = false;
    en = normalizeSegments(en.map((s) => {
      if (s.ass !== null) seen = true;
      return seen ? { text: s.text, ass: thColor } : s;
    }));
  }
  return { th, en };
}

// The render highlights a whole burst, wrapped lines joined by ASS's literal
// "\N". Running the same joined string here (and splitting the result back
// per line) keeps "one highlight per burst" and the same line-boundary
// behaviour instead of colouring a keyword on every wrapped line.
export const ASS_LINE_BREAK = '\\N';

export function splitSegmentsByLine(segments, lineCount) {
  const lines = [[]];
  for (const seg of segments) {
    const parts = seg.text.split(ASS_LINE_BREAK);
    parts.forEach((part, i) => {
      if (i > 0) lines.push([]);
      if (part) lines[lines.length - 1].push({ text: part, ass: seg.ass });
    });
  }
  while (lines.length < lineCount) lines.push([]);
  return lines.map(normalizeSegments);
}

/**
 * Highlight one caption burst given its wrapped Thai and English lines.
 * Returns per-line segment lists `{ th: [[seg...]...], en: [[seg...]...] }`.
 */
export function highlightBurstLines(thLines, enLines = [], { customKeywords = null } = {}) {
  const thText = thLines.join(ASS_LINE_BREAK);
  if (!enLines.length) {
    return { th: splitSegmentsByLine(highlightTh(thText, { customKeywords }), thLines.length), en: [] };
  }
  const enText = enLines.join(ASS_LINE_BREAK);
  const { th, en } = highlightBilingual(thText, enText, { customKeywords });
  return {
    th: splitSegmentsByLine(th, thLines.length),
    en: splitSegmentsByLine(en, enLines.length),
  };
}
