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

  const scriptText = Array.isArray(angle.script_lines)
    ? angle.script_lines.join('\n')
    : (angle.script_text || '');

  const patch = {
    productName: angle.product_name || context.title || 'สินค้า',
    hookTitle: angle.hook_title || '',
    customScript: scriptText,
    // A script that came from the flow is meant to be spoken as written --
    // anything else would throw away the angle the user just picked.
    useCustomScript: true,
    keyFeatures: angle.key_features || context.description || '',
    painPoint: angle.pain_point || '',
    priceDeal: angle.price_deal || context.price_note || '',
  };
  if (angle.ad_tone) patch.adTone = angle.ad_tone;
  if (angle.selected_video) patch.selectedVideo = angle.selected_video;
  else if (angle.selected_videos && angle.selected_videos.length > 0) patch.selectedVideo = angle.selected_videos[0];
  else if (context.selectedVideo) patch.selectedVideo = context.selectedVideo;
  else if (context.images && context.images.length > 0) patch.selectedVideo = context.images[0].local_path || context.images[0].rel_path || context.images[0].path;
  return patch;
}

/** Label for an angle in a picker, with a 1-based number as the fallback. */
export function angleLabel(angle, index) {
  if (!angle) return `มุมที่ ${index + 1}`;
  return angle.angle_name || angle.hook_title || `มุมที่ ${index + 1}`;
}

export default angleToForm;
