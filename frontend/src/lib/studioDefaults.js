// Everything /api/render needs beyond the product itself, and what it starts
// as. Lives here rather than in App.jsx because both the old Studio tab and
// the editor's new-clip panel build the same payload -- two copies of these
// defaults would drift and the render would quietly change behaviour
// depending on which screen started it.

export const DEFAULT_STUDIO_FORM = {
  selectedVideo: '',
  productName: 'Esseger สายชาร์จแม่เหล็ก',
  hookTitle: 'อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก',
  painPoint: 'สายชาร์จพังง่าย เสียบยากในที่มืด',
  priceDeal: 'ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง',
  keyFeatures: 'แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก',
  customScript: '',
  useCustomScript: false,
  voiceMode: 'gemini_tts',
  voiceGender: 'male',
  voiceSpeed: '+15%',
  voicePreset: 'gemini_puck_male_hype',
  adTone: 'commercial_premium',
  fontName: 'IBMPlex',
  bilingualSubtitles: true,
  stickerBadge: 'badge_flash_sale_3d.png',
  bgmName: null,
  lutName: null,
};

export const STUDIO_FORM_KEY = 'capcut_studio_form';

/** Saved form merged over the defaults; defaults alone if nothing is stored. */
export function getSavedStudioForm() {
  try {
    const raw = localStorage.getItem(STUDIO_FORM_KEY);
    if (raw) return { ...DEFAULT_STUDIO_FORM, ...JSON.parse(raw) };
  } catch (err) {
    console.error('Failed to parse saved studio form:', err);
  }
  return DEFAULT_STUDIO_FORM;
}

export default DEFAULT_STUDIO_FORM;
