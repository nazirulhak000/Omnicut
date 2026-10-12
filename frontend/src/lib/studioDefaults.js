import { channelLocalStorage } from './channelStorage.js';
// Everything /api/render needs beyond the product itself, and what it starts
// as. Lives here rather than in App.jsx because both the old Studio tab and
// the editor's new-clip panel build the same payload -- two copies of these
// defaults would drift and the render would quietly change behaviour
// depending on which screen started it.

import { DEFAULT_ONE_CLICK_STYLE_PRESET, DEFAULT_STYLE_PRESET } from './stylePresetCatalog.js';

export const STYLE_PRESET_STORAGE_VERSION = 2;

export const DEFAULT_STUDIO_FORM = {
  selectedVideo: '',
  productName: 'Esseger สายชาร์จแม่เหล็ก',
  // Left empty (not hardcoded to match the productName sample above) so
  // NewClipPanel's guessBrandModel() pre-fill actually fires the first time
  // a user blurs out of the product name field -- a fixed sample here would
  // make the fields look "already filled" and silently skip that guess,
  // which is exactly the stale-Header-text bug this pre-fill exists to fix.
  hookBrand: '',
  hookModel: '',
  hookLabel: '',
  painPoint: 'สายชาร์จพังง่าย เสียบยากในที่มืด',
  priceDeal: 'ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง',
  keyFeatures: 'แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก',
  customScript: '',
  useCustomScript: false,
  voiceMode: 'gemini_tts',
  voiceGender: 'male',
  voiceSpeed: '+15%',
  voicePreset: 'gemini_fenrir_male_strong',
  adTone: 'commercial_hype',
  stylePreset: DEFAULT_ONE_CLICK_STYLE_PRESET,
  stylePresetVersion: STYLE_PRESET_STORAGE_VERSION,
  fontName: 'IBMPlex',
  bilingualSubtitles: true,
  showWatermark: true,
  stickerBadge: null,
  stickerScale: 1,
  stickerStartTime: null,
  stickerEndTime: null,
  stickerNormX: null,
  stickerNormY: null,
  stickers: [],
  bgmName: null,
  lutName: null,
  useAiVision: true,   // matches RenderRequest's own default
};

export const STUDIO_FORM_KEY = 'capcut_studio_form';

/** Migrate a saved form without depending on browser storage. */
export function migrateSavedStudioForm(saved) {
  const form = { ...DEFAULT_STUDIO_FORM, ...saved };
  // The style picker was introduced with viral_punch as the implicit
  // default. Reset only pre-versioned saved forms to the old baseline;
  // explicit choices made after this migration remain untouched.
  if (saved?.stylePresetVersion !== STYLE_PRESET_STORAGE_VERSION) {
    form.stylePreset = DEFAULT_STYLE_PRESET;
    form.stylePresetVersion = STYLE_PRESET_STORAGE_VERSION;
  }
  return form;
}

/** Saved form merged over the defaults; defaults alone if nothing is stored. */
export function getSavedStudioForm() {
  try {
    const raw = channelLocalStorage().getItem(STUDIO_FORM_KEY);
    if (raw) {
      return migrateSavedStudioForm(JSON.parse(raw));
    }
  } catch (err) {
    console.error('Failed to parse saved studio form:', err);
  }
  return DEFAULT_STUDIO_FORM;
}

export default DEFAULT_STUDIO_FORM;
