/**
 * Computes product progress and multi-segment color percentages:
 * - Native Program renders: Green (bg-emerald-400 / #34D399)
 * - Google Flow (Veo AI) renders: Amber (bg-amber-400 / #F59E0B)
 * - HyperFrames renders: Sky Blue (bg-sky-400 / #38BDF8)
 * - All within the same capsule progress bar
 */
export function getProductProgressStats(product) {
  const pAngles = product?.angles || [];
  const total = pAngles.length || 20;

  const stats = product?.export_stats || {};
  const hasStats =
    (typeof stats.native_count === 'number' || typeof stats.flow_count === 'number' || typeof stats.hyperframes_count === 'number') &&
    ((stats.native_count || 0) > 0 || (stats.flow_count || 0) > 0 || (stats.hyperframes_count || 0) > 0);

  let effectiveNative = 0;
  let effectiveFlow = 0;
  let effectiveHf = 0;

  if (hasStats) {
    effectiveNative = stats.native_count || 0;
    effectiveFlow = stats.flow_count || 0;
    effectiveHf = stats.hyperframes_count || 0;
  } else {
    // Inspect angles directly
    const productCode = String(product?.product_code || product?.code || '').toUpperCase();
    const isCoupleCatalog = ['HAT01', 'HAT02', 'ORS01', 'RED01', 'GOO01', 'HOY01'].includes(productCode);

    for (const a of pAngles) {
      if (a.status === 'posted' || a.status === 'rendered') {
        const proj = String(a.project_name || '');
        const vUrl = String(a.video_url || '').toLowerCase();
        const aid = String(a.angle_id || '');

        const isFlow =
          a.source_kind === 'flow' ||
          vUrl.includes('_ai_veo_') ||
          vUrl.includes('_veo_') ||
          proj.includes('flow_job');

        const isHf =
          a.source_kind === 'hyperframes' ||
          a.draft_type === 'hyperframes' ||
          a.format === 'couple_paper_chat' ||
          proj.startsWith('_HyperFrames_Studio/') ||
          vUrl.includes('-pov-') ||
          vUrl.includes('hyperframe') ||
          (isCoupleCatalog && aid.startsWith('ang_'));

        if (isFlow) {
          effectiveFlow += 1;
        } else if (isHf) {
          effectiveHf += 1;
        } else {
          effectiveNative += 1;
        }
      }
    }
  }

  const totalDone = effectiveNative + effectiveFlow + effectiveHf;
  const displayDone = Math.min(totalDone, total);

  let nativePct = 0;
  let flowPct = 0;
  let hfPct = 0;
  if (totalDone > 0) {
    if (totalDone >= total) {
      nativePct = Math.round((effectiveNative / totalDone) * 100);
      flowPct = Math.round((effectiveFlow / totalDone) * 100);
      hfPct = 100 - (nativePct + flowPct);
    } else {
      nativePct = Math.round((effectiveNative / total) * 100);
      flowPct = Math.round((effectiveFlow / total) * 100);
      hfPct = Math.round((effectiveHf / total) * 100);
    }
  }

  // Determine standard accent text color based on generator type
  let colorClass = 'text-slate-400';
  if (totalDone > 0) {
    if (effectiveFlow > 0 && effectiveNative === 0 && effectiveHf === 0) {
      colorClass = 'text-amber-400';
    } else if (effectiveHf > 0 && effectiveNative === 0 && effectiveFlow === 0) {
      colorClass = 'text-sky-400';
    } else if (effectiveNative > 0 && effectiveHf === 0 && effectiveFlow === 0) {
      colorClass = 'text-emerald-400';
    } else {
      colorClass = 'text-[#25F4EE]';
    }
  }

  return {
    total,
    totalDone,
    displayDone,
    effectiveNative,
    effectiveFlow,
    effectiveHf,
    nativePct,
    flowPct,
    hfPct,
    isComplete: totalDone >= total,
    colorClass,
  };
}

/**
 * Returns engine badge metadata for a rendered/posted angle:
 * - Flow (Veo AI): { type: 'flow', label: '⚡ Flow', title: '...', chipClass: '...' }
 * - HyperFrames: { type: 'hyperframes', label: 'HyperFrames', title: '...', chipClass: '...' }
 * - Native: { type: 'native', label: 'ปกติ', title: '...', chipClass: '...' }
 * - Returns null if angle is not rendered or has no video
 */
export function getAngleEngineBadge(angle, product) {
  if (!angle) return null;
  const isRendered = angle.status === 'rendered' || angle.status === 'posted' || Boolean(angle.video_url);
  if (!isRendered) return null;

  // Pattern heuristics from video_url, project_name, and source_kind
  const vUrl = String(angle.video_url || '').toLowerCase();
  const proj = String(angle.project_name || '').toLowerCase();
  const aid = String(angle.angle_id || '').toLowerCase();
  const productCode = String(product?.product_code || product?.code || '').toUpperCase();
  const isCoupleCatalog = ['HAT01', 'HAT02', 'ORS01', 'RED01', 'GOO01', 'HOY01'].includes(productCode);

  const isFlow =
    angle.source_kind === 'flow' ||
    vUrl.includes('_ai_veo_') ||
    vUrl.includes('_veo_') ||
    proj.includes('flow_job') ||
    angle.format === 'flow';

  if (isFlow) {
    return {
      type: 'flow',
      label: '⚡ Flow',
      title: 'วิดีโอสร้างด้วย Google Flow (Veo AI)',
      chipClass: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    };
  }

  const isHf =
    angle.source_kind === 'hyperframes' ||
    angle.draft_type === 'hyperframes' ||
    angle.format === 'couple_paper_chat' ||
    proj.startsWith('_hyperframes_studio/') ||
    vUrl.includes('-pov-') ||
    vUrl.includes('hyperframe') ||
    (isCoupleCatalog && aid.startsWith('ang_'));

  if (isHf) {
    return {
      type: 'hyperframes',
      label: 'HyperFrames',
      title: 'วิดีโอแอนิเมชันสร้างด้วย HyperFrames',
      chipClass: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
    };
  }

  return {
    type: 'native',
    label: 'ปกติ',
    title: 'วิดีโอตัดต่อด้วยฟุตเทจจริงผ่านโปรแกรมหลัก',
    chipClass: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  };
}
