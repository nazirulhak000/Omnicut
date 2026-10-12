export const MAIN_WATERMARK_TEXT = 'สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง';

// Preview follows the project's captured identity, never the current registry.
// Legacy manifests have no owner/snapshot and belong to main only.
export function projectWatermark(snapshot, channelId = 'main') {
  if (!snapshot) return channelId === 'main' ? MAIN_WATERMARK_TEXT : null;
  const owner = snapshot.channel_id || snapshot.id;
  if (owner !== channelId || typeof snapshot.watermark_text !== 'string') return null;
  return snapshot.watermark_text;
}
