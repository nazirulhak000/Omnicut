/**
 * UI-facing metadata for the renderer-agnostic motion contract.
 *
 * This module deliberately contains no animation implementation. It only
 * translates the existing contract/preset ids into labels and accessible
 * view-model data for a future Inspector/Gallery integration.
 */

import { MOTION_ROLES } from './motionContract.js';
import { MOTION_PRESETS } from './motionPresets.js';

export const MOTION_UI_VERSION = 1;

export const MOTION_UI_PHASE_ORDER = Object.freeze(['in', 'hold', 'out']);

const CONTRACT_PHASE_BY_UI_PHASE = Object.freeze({
  in: 'in',
  hold: 'loop',
  out: 'out',
});

const UI_PHASE_BY_CONTRACT_PHASE = Object.freeze({
  in: 'in',
  loop: 'hold',
  out: 'out',
});

export const MOTION_UI_PHASES = Object.freeze({
  in: Object.freeze({
    id: 'in',
    contractPhase: 'in',
    label: 'เข้า',
    title: 'ตอนเปิดตัว',
    description: 'ช่วงที่ข้อความหรือ Hook ปรากฏขึ้นบนจอ',
  }),
  hold: Object.freeze({
    id: 'hold',
    contractPhase: 'loop',
    label: 'ค้าง',
    title: 'ช่วงค้างบนจอ',
    description: 'ช่วงที่ข้อความอยู่บนจอและเล่นซ้ำได้',
  }),
  out: Object.freeze({
    id: 'out',
    contractPhase: 'out',
    label: 'ออก',
    title: 'ตอนปิด',
    description: 'ช่วงที่ข้อความหายหรือเคลื่อนออกจากจอ',
  }),
});

export const MOTION_UI_ROLE_LABELS = Object.freeze({
  text: 'Text Overlay',
  hook: 'Hook',
  caption: 'Caption',
});

const PRESET_COPY = Object.freeze({
  in: Object.freeze({
    bounce: ['เด้งเข้า', 'ขยายเข้าพร้อมการเด้งหลายจังหวะ'],
    bounce_soft: ['เด้งเข้านุ่มนวล', 'ขยายเข้าพร้อมการเด้งที่นุ่มลง'],
    pop: ['ป๊อปเข้า', 'ปรากฏขึ้นอย่างรวดเร็วพร้อมขยายเล็กน้อย'],
    pop_soft: ['ป๊อปเข้านุ่มนวล', 'ปรากฏขึ้นอย่างรวดเร็วแบบไม่กระแทก'],
    slam: ['กระแทกเข้า', 'พุ่งเข้าจากขนาดใหญ่แล้วล็อกเข้าตำแหน่ง'],
    elastic_bounce: ['เด้งยืดหยุ่น', 'ขยายและเด้งกลับคล้ายสปริง'],
    fade: ['ค่อยๆ ปรากฏ', 'เพิ่มความทึบอย่างต่อเนื่อง'],
    zoom: ['ซูมเข้า', 'เริ่มจากขนาดใหญ่แล้วปรับเข้าขนาดปกติ'],
    slide_up: ['เลื่อนขึ้น', 'เลื่อนจากด้านล่างขึ้นสู่ตำแหน่งปกติ'],
    typewriter: ['พิมพ์ทีละตัว', 'เผยข้อความตามลำดับเหมือนกำลังพิมพ์'],
    blur: ['คลายเบลอ', 'เริ่มจากภาพเบลอแล้วค่อยๆ ชัดขึ้น'],
    snap: ['สะบัดเข้า', 'ขยายสั้นๆ แล้วคืนสู่ขนาดปกติ'],
    pop_zoom: ['ป๊อปซูม', 'ขยายสั้นๆ พร้อมค่อยๆ ปรากฏ'],
    stamp: ['ประทับตรา', 'ปรากฏจากขนาดใหญ่แล้วหยุดอย่างชัดเจน'],
    quick_fade: ['เฟดเร็ว', 'ปรากฏอย่างรวดเร็วด้วยการเพิ่มความทึบ'],
    rise: ['เลื่อนขึ้น', 'เลื่อนขึ้นจากด้านล่างพร้อมค่อยๆ ปรากฏ'],
    none: ['ไม่มี', 'แสดงข้อความทันทีโดยไม่ใช้ Animation ตอนเข้า'],
  }),
  loop: Object.freeze({
    pulse: ['เต้นเบา', 'ปรับความทึบขึ้นลงอย่างนุ่มนวลเป็นรอบ'],
    wave: ['โบก', 'หมุนสลับซ้ายขวาอย่างต่อเนื่อง'],
    shake: ['สั่น', 'สั่นซ้ายขวาเป็นจังหวะสั้นๆ'],
    flicker: ['กะพริบ', 'เปลี่ยนความสว่างเป็นจังหวะไม่สม่ำเสมอ'],
    lightsweep: ['แสงกวาด', 'กวาดแสงผ่านตัวข้อความเป็นรอบ'],
    none: ['ไม่มี', 'ค้างนิ่งระหว่างที่ข้อความอยู่บนจอ'],
  }),
  out: Object.freeze({
    fade: ['ค่อยๆ หาย', 'ลดความทึบจนข้อความหายไป'],
    slide: ['เลื่อนออก', 'เลื่อนลงพร้อมลดความทึบจนหายไป'],
    zoom: ['ซูมออก', 'ขยายออกพร้อมลดความทึบจนหายไป'],
    glitch: ['Glitch ออก', 'สั่นรบกวนสั้นๆ ก่อนหายไป'],
    none: ['ตัดทันที', 'จบการแสดงผลทันทีโดยไม่ใช้ Animation ตอนออก'],
  }),
});

const CAPABILITY_REASON = 'ยังไม่ผูกกับ Renderer กลาง จึงยังไม่เปิดการปรับค่า';

function assertRole(role) {
  if (!MOTION_ROLES.includes(role)) {
    throw new TypeError(`Unsupported motion UI role: ${role}`);
  }
}

function normalizeUiPhase(phase) {
  if (phase === 'loop') return 'hold';
  if (MOTION_UI_PHASE_ORDER.includes(phase)) return phase;
  return null;
}

function getLegacyId(contract) {
  return contract.id.split('.').at(-1);
}

export function formatMotionDuration(durationMs, { repeat = false } = {}) {
  const duration = Number(durationMs);
  if (!Number.isFinite(duration) || duration <= 0) return 'ทันที';
  if (duration <= 1 && !repeat) return 'ตัดทันที';
  if (duration < 1000) return `${Math.round(duration)} มิลลิวินาที${repeat ? '/รอบ' : ''}`;
  const seconds = (duration / 1000).toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
  return `${seconds} วินาที${repeat ? '/รอบ' : ''}`;
}

function buildCapabilities() {
  return Object.freeze({
    intensity: Object.freeze({
      supported: false,
      label: 'ความแรง',
      reason: CAPABILITY_REASON,
    }),
    speed: Object.freeze({
      supported: false,
      label: 'ความเร็ว',
      reason: CAPABILITY_REASON,
    }),
  });
}

function buildPresetViewModel(contract, uiPhase, { selectedId = null } = {}) {
  const phase = MOTION_UI_PHASES[uiPhase];
  const legacyId = getLegacyId(contract);
  const [label, description] = PRESET_COPY[contract.phase]?.[legacyId] || [legacyId, 'Animation ที่มีอยู่ใน Motion Contract'];
  const roleLabel = MOTION_UI_ROLE_LABELS[contract.role] || contract.role;
  const durationLabel = formatMotionDuration(contract.duration_ms, { repeat: Boolean(contract.repeat) });
  const ariaLabel = `${label}, ${phase.title}, ${durationLabel}`;

  return Object.freeze({
    id: legacyId,
    legacyId,
    contractId: contract.id,
    role: contract.role,
    phase: contract.phase,
    uiPhase,
    phaseLabel: phase.label,
    label,
    description,
    durationMs: contract.duration_ms,
    durationLabel,
    repeat: Boolean(contract.repeat),
    rendererBound: Boolean(contract.metadata?.renderer_bound),
    parityLevel: contract.metadata?.parity_level || 'unknown',
    unsupportedTracks: Object.freeze([...(contract.metadata?.unsupported_tracks || [])]),
    enabled: Boolean(contract.metadata?.renderer_bound),
    disabledReason: contract.metadata?.renderer_bound
      ? null
      : 'Renderer กลางยังต้องใช้ตัวเรนเดอร์เดิมสำหรับ preset นี้',
    recommendedRole: contract.role,
    recommendedRoleLabel: roleLabel,
    capabilities: buildCapabilities(),
    preview: Object.freeze({
      phaseOrder: MOTION_UI_PHASE_ORDER,
      activePhase: uiPhase,
      repeat: Boolean(contract.repeat),
    }),
    aria: Object.freeze({
      role: 'radio',
      'aria-label': ariaLabel,
      'aria-description': `${description} แนะนำสำหรับ ${roleLabel}`,
      'aria-checked': legacyId === selectedId,
    }),
  });
}

export function getMotionUiPreset(role, phase, presetId, options = {}) {
  assertRole(role);
  const uiPhase = normalizeUiPhase(phase);
  if (!uiPhase || !presetId) return null;

  const contractPhase = CONTRACT_PHASE_BY_UI_PHASE[uiPhase];
  const contract = MOTION_PRESETS[`${role}.${contractPhase}.${presetId}`];
  return contract ? buildPresetViewModel(contract, uiPhase, options) : null;
}

export function getMotionUiPresets(role, phase, options = {}) {
  assertRole(role);
  const uiPhase = normalizeUiPhase(phase);
  if (!uiPhase) return [];

  const contractPhase = CONTRACT_PHASE_BY_UI_PHASE[uiPhase];
  return Object.values(MOTION_PRESETS)
    .filter((contract) => contract.role === role && contract.phase === contractPhase)
    .map((contract) => buildPresetViewModel(contract, uiPhase, options));
}

export function getMotionUiModel({ role = 'hook', selectedByPhase = {} } = {}) {
  assertRole(role);

  const groups = MOTION_UI_PHASE_ORDER.map((uiPhase) => {
    const phase = MOTION_UI_PHASES[uiPhase];
    const presets = getMotionUiPresets(role, uiPhase, { selectedId: selectedByPhase[uiPhase] });
    return Object.freeze({
      ...phase,
      presets,
      aria: Object.freeze({
        role: 'radiogroup',
        'aria-label': `${phase.title} — ${role === 'caption' ? 'Caption' : MOTION_UI_ROLE_LABELS[role]}`,
      }),
    });
  });

  return Object.freeze({
    version: MOTION_UI_VERSION,
    role,
    roleLabel: MOTION_UI_ROLE_LABELS[role],
    phaseOrder: MOTION_UI_PHASE_ORDER,
    contractPhaseOrder: MOTION_UI_PHASE_ORDER.map((uiPhase) => CONTRACT_PHASE_BY_UI_PHASE[uiPhase]),
    groups,
    aria: Object.freeze({
      role: 'group',
      'aria-label': `Animation สำหรับ ${MOTION_UI_ROLE_LABELS[role]}`,
    }),
  });
}

export { CONTRACT_PHASE_BY_UI_PHASE, UI_PHASE_BY_CONTRACT_PHASE };
