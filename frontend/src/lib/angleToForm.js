// One angle from the product flow -> the fields a render needs.
//
// The product screen produces angles (hook, script lines, pain point, selling
// points, price line); every later screen just fills itself from one of them.
// Keeping that mapping in one place is what makes the flow a flow: if the
// editor and the old Studio tab each did their own translation, picking the
// same angle in two places would start two different renders.

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

  const cleanHook = (angle.hook_title || '')
    .replace(/\.{2,}|…/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .trim();

  const patch = {
    productName: angle.product_name || context.title || 'สินค้า',
    hookTitle: cleanHook,
    customScript: scriptText,
    // A script that came from the flow is meant to be spoken as written --
    // anything else would throw away the angle the user just picked.
    useCustomScript: true,
    keyFeatures: angle.key_features || context.description || '',
    painPoint: angle.pain_point || '',
    priceDeal: angle.price_deal || context.price_note || '',
  };
  if (angle.ad_tone) patch.adTone = angle.ad_tone;

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
