// One angle from the product flow -> the fields a render needs.
//
// The product screen produces angles (hook, script lines, pain point, selling
// points, price line); every later screen just fills itself from one of them.
// Keeping that mapping in one place is what makes the flow a flow: if the
// editor and the old Studio tab each did their own translation, picking the
// same angle in two places would start two different renders.

import { guessBrandModel } from './overlayModel';
import { getRecommendedStyleForAngle } from './stylePresetCatalog';

/**
 * @param {object} angle    one entry of productContext.angles
 * @param {object} context  the product context it came from (for fallbacks)
 * @returns {object|null}   patch to merge into the form, or null if unusable
 */
export function angleToForm(angle, context = {}) {
  if (!angle) return null;

  const rawScriptText = Array.isArray(angle.script_lines)
    ? angle.script_lines.join('\n')
    : (angle.script_text || '');

  // Strip all stray ellipses ("...", "…") and collapse extra whitespace
  const scriptText = rawScriptText
    .replace(/\.{2,}|…/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .split('\n')
    .map(line => line.trim())
    .join('\n');

  const productName = angle.product_name || context.title || 'สินค้า';
  // The banner used to be manual-only, which in practice meant blank: the
  // three fields are collapsed on this path and nobody opened them, so every
  // first render burned the whole product name into the brand tier.
  //
  // The script AI splits it now. `angle.hook_title` is still deliberately
  // NOT used -- it is a spoken sentence, not a stacked headline, and reading
  // it here is what once put a full sentence across the banner.
  const guessed = guessBrandModel(productName);
  const patch = {
    productName,
    hookBrand: angle.hook_brand || context.hook_brand || guessed.brand,
    hookModel: angle.hook_model || context.hook_model || guessed.model,
    hookLabel: angle.hook_label || context.hook_label || '',
    customScript: scriptText,
    // A script that came from the flow is meant to be spoken as written --
    // anything else would throw away the angle the user just picked.
    useCustomScript: true,
    keyFeatures: angle.key_features || context.description || '',
    painPoint: angle.pain_point || '',
    priceDeal: angle.price_deal || context.price_note || '',
  };
  const angleId = angle.angle_id || angle.id;
  const recommendedStyle = angleId ? getRecommendedStyleForAngle(angleId) : null;
  patch.stylePreset = angle.style_preset || recommendedStyle || 'viral_punch';

  const VALID_AD_TONES = ['commercial_premium', 'commercial_hype', 'commercial_aesthetic', 'commercial_expert'];
  patch.adTone = (angle.ad_tone && VALID_AD_TONES.includes(angle.ad_tone) && angle.ad_tone !== 'commercial_premium')
    ? angle.ad_tone
    : 'commercial_hype';
  patch.voicePreset = angle.voice_preset || 'gemini_puck_male_hype';
  patch.voiceGender = 'male';
  patch.voiceMode = angle.voice_mode || 'gemini_tts';

  const angleVideos = angle.selected_videos || (angle.selected_video ? [angle.selected_video] : []);
  if (angleVideos.length > 0) {
    patch.selectedVideos = angleVideos;
    patch.selectedVideo = angleVideos[0];
  } else {
    // When no specific video is chosen for this angle, do not inject unrelated videos.
    // Keep it empty so the editor can accurately show that no specific clip is pinned,
    // or allow auto-assembly from the entire library.
    patch.selectedVideos = [];
    patch.selectedVideo = '';
  }
  return patch;
}

/** Label for an angle in a picker, with a 1-based number as the fallback. */
export function angleLabel(angle, index) {
  if (!angle) return `มุมที่ ${index + 1}`;
  return angle.angle_name || angle.hook_title || `มุมที่ ${index + 1}`;
}

export default angleToForm;
