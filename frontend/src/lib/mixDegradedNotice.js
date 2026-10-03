/**
 * What the editor tells the user after a render whose full audio mix failed.
 *
 * render_jobs.complete_job() copies `mix_degraded` / `mix_degraded_reason` from
 * the stage result into the job result. The clip itself still exports (the
 * backend keeps the voice), so this is a warning on a finished render, not an
 * error -- but it must be seen, because nothing in the video says the music and
 * SFX are gone.
 *
 * @param {object | null | undefined} result the finished job's `result`
 * @returns {{ title: string, message: string } | null} null when the mix was fine
 */
export const MIX_DEGRADED_FALLBACK_MESSAGE =
  'มิกซ์เสียงเต็มล้มเหลว จึงใช้เสียงพากย์อย่างเดียว: คลิปนี้ไม่มีเพลงพื้นหลังและเอฟเฟกต์ SFX';

export function mixDegradedNotice(result) {
  if (!result || result.mix_degraded !== true) return null;
  const reason = typeof result.mix_degraded_reason === 'string' ? result.mix_degraded_reason.trim() : '';
  return {
    title: 'มิกซ์เสียงไม่สมบูรณ์',
    message: reason || MIX_DEGRADED_FALLBACK_MESSAGE,
  };
}
