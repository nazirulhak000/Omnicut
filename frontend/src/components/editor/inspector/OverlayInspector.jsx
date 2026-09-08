import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Trash2,
  RotateCcw,
  ChevronDown,
  Volume2,
  Play,
  Type,
  AlignLeft,
  AlignCenter,
  AlignRight,
  BookmarkPlus,
  Check,
  Loader2,
} from 'lucide-react';
import {
  ACCENT_COLOR,
  DEFAULT_TEXT_LOOK,
  HOOK_FS_RATIO,
  HOOK_SHADOW,
  overriddenTierFields,
  resolveLook,
  withHookFont,
  withHookTemplate,
  withHookTemplateReset,
  withTierLook,
  withTierText,
} from '../../../lib/overlayModel';
import { TIER_KEYS } from '../../../lib/hookStyles';
import TextLookPreview from '../TextLookPreview';
import {
  pillForBgStyle,
  bgStyleOf,
  clampScale,
  clampHookDuration,
} from '../../../lib/inspectorModel';
import { toMediaUrl } from '../../../lib/mediaUrl';
import { FONT_OPTIONS, PRESET_STYLES } from './CaptionInspector';

const HOOK_TIER_LABELS = ['แบรนด์', 'รุ่น / จุดเด่น', 'หมวดหมู่ / คำโปรย'];
const HOOK_MIN_DURATION = 1.0;
const HOOK_MAX_DURATION = 8.0;
const HOOK_CARD_SAMPLE = ['BRAND', 'รุ่นเด่น', 'คำโปรย'];

export const FALLBACK_ACCENT_OPTIONS = {
  underline: { label_th: 'เส้นใต้เรืองแสง', label_en: 'Accent Bar' },
  badge: { label_th: 'แถบไฮไลต์', label_en: 'Badge' },
  none: { label_th: 'ไม่มี', label_en: 'None' },
};

function hookCardLook(tpl, tierKey) {
  const tier = (tpl.tiers || {})[tierKey] || {};
  return {
    font: tpl.font,
    size_pct: tier.size_pct,
    color: tier.color === null ? '#FFE600' : tier.color,
    outline_color: tier.outline_color,
    outline_px: tier.outline_px,
    upper: tier.upper,
    pill: tier.pill ? { fill: tier.pill, border: null, pad_x_em: 0.342, pad_y_em: 0.171 } : null,
    shadow: HOOK_SHADOW,
  };
}

function getMotionPreviewClass(motion) {
  const loop = motion?.loop;
  const animIn = motion?.in;
  if (loop === 'flicker') return 'group-hover:anim-preview-flicker';
  if (loop === 'shake' || animIn === 'pop') return 'group-hover:anim-preview-shake';
  if (loop === 'wave') return 'group-hover:anim-preview-wave';
  if (loop === 'pulse' || animIn === 'bounce') return 'group-hover:anim-preview-pulse';
  if (animIn === 'pop_zoom') return 'group-hover:anim-preview-pop_zoom';
  if (loop === 'lightsweep') return 'group-hover:anim-preview-lightsweep';
  return 'group-hover:scale-105';
}

const LEGACY_SFX_ALIASES = {
  whoosh: 'sfx_whoosh_fast',
  pop: 'sfx_pop_bubble',
  ding: 'sfx_bell_ding',
  cash: 'sfx_cash_register',
  boom: 'sfx_vine_boom',
};

export default function OverlayInspector({
  selection,
  selectedTextOverlay,
  hookOverlay,
  hookMotionCatalog,
  hookMotionDefault,
  hookTemplates,
  customHookTemplates = {},
  onSaveCustomHookTemplate = null,
  onDeleteCustomHookTemplate = null,
  assets = {},
  onToggleHookHeader,
  onUpdateOverlay,
  onReplaceOverlay,
  onDeleteOverlay,
}) {
  const [openTier, setOpenTier] = useState(0);
  const [textPattern, setTextPattern] = useState({ bold: true, italic: false, underline: false });
  const [textAlign, setTextAlign] = useState('center');
  const [newTemplateName, setNewTemplateName] = useState('');
  const [isSavingCustom, setIsSavingCustom] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const hookHeaderCardRef = useRef(null);
  const hookBrandInputRef = useRef(null);
  const textAreaRef = useRef(null);

  const sfxList = assets?.sfx || [];

  const playSfxAudio = (sfxKey) => {
    if (!sfxKey) return;
    const canonical = LEGACY_SFX_ALIASES[sfxKey] || sfxKey;
    const item = sfxList.find((s) => s.id === canonical || s.name === canonical || s.id === sfxKey || s.name === sfxKey)
      || sfxList.find((s) => s.name?.toLowerCase().includes(sfxKey.toLowerCase()));
    if (!item?.path) return;
    try {
      const audio = new Audio(toMediaUrl(item.path));
      audio.volume = 0.28;
      audio.play().catch(() => {});
    } catch (_) {}
  };

  useEffect(() => {
    let hookTimeoutId;
    let textTimeoutId;
    if (selection?.type === 'hook') {
      hookTimeoutId = setTimeout(() => {
        hookHeaderCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        hookBrandInputRef.current?.focus();
      }, 50);
    }
    if (selection?.type === 'text_overlay' && selection?.focusText) {
      textTimeoutId = setTimeout(() => {
        if (textAreaRef.current) {
          textAreaRef.current.focus();
          textAreaRef.current.select();
        }
      }, 60);
    }
    return () => {
      clearTimeout(hookTimeoutId);
      clearTimeout(textTimeoutId);
    };
  }, [selection]);

  // ═════════════════════════════════════════════════════════════════════
  // HOOK HEADER VIEW
  // ═════════════════════════════════════════════════════════════════════
  if (selection?.type === 'hook') {
    const showHookHeader = !!hookOverlay && !hookOverlay.hidden;
    const hookOverrides = hookOverlay ? overriddenTierFields(hookOverlay) : [];
    const hasHookOverrides = hookOverrides.some((fields) => fields.length > 0);
    const hookDuration = hookOverlay ? clampHookDuration(hookOverlay.end - hookOverlay.start) : 3.0;
    const hookMotion = hookOverlay?.anim || {};

    const patchHookTier = (tierIdx, patch) => {
      if (!hookOverlay) return;
      onReplaceOverlay?.(hookOverlay.id, withTierLook(hookOverlay, tierIdx, patch));
    };
    const setHookTierText = (tierIdx, text) => {
      if (!hookOverlay) return;
      onReplaceOverlay?.(hookOverlay.id, withTierText(hookOverlay, tierIdx, text));
    };
    const onHookTemplate = (template) => {
      if (!hookOverlay) return;
      onReplaceOverlay?.(hookOverlay.id, withHookTemplate(hookOverlay, template));
    };
    const onHookStyleReset = () => {
      if (!hookOverlay) return;
      onReplaceOverlay?.(hookOverlay.id, withHookTemplateReset(hookOverlay));
    };
    const handleSaveAsTemplate = async () => {
      if (!newTemplateName.trim() || !hookOverlay || !onSaveCustomHookTemplate) return;
      setIsSavingCustom(true);
      try {
        const font = hookOverlay.look?.font || (hookOverlay.tiers?.[0]?.look?.font) || 'Kanit';
        const tiers = {};
        TIER_KEYS.forEach((tierKey, idx) => {
          const tier = (hookOverlay.tiers || [])[idx] || {};
          const look = resolveLook(hookOverlay.look, tier.look);
          tiers[tierKey] = {
            size_pct: look.size_pct || 100,
            color: look.color === null || look.color === undefined ? '#FFE600' : look.color,
            outline_color: look.outline_color || '#000000',
            outline_px: look.outline_px !== undefined ? Number(look.outline_px) : 6.0,
            upper: !!look.upper,
            pill: look.pill?.fill || null,
          };
        });
        const motion = hookOverlay.anim || {};
        const res = await onSaveCustomHookTemplate({
          name: newTemplateName.trim(),
          label_th: newTemplateName.trim(),
          font,
          tiers,
          motion,
        });
        setSaveSuccess(true);
        setNewTemplateName('');
        setTimeout(() => setSaveSuccess(false), 3000);
        if (res?.id) {
          onReplaceOverlay?.(hookOverlay.id, withHookTemplate(hookOverlay, res.id));
        }
      } catch (err) {
        console.error(err);
      } finally {
        setIsSavingCustom(false);
      }
    };

    const onHookDurationChange = (seconds) => {
      if (!hookOverlay) return;
      onUpdateOverlay?.(hookOverlay.id, { end: Math.round((hookOverlay.start + seconds) * 100) / 100 });
    };
    const onHookMotionChange = (key, value) => {
      if (!hookOverlay) return;
      onUpdateOverlay?.(hookOverlay.id, { anim: { ...(hookOverlay.anim || {}), [key]: value } });
    };

    const handleSaveCustom = async () => {
      if (!newTemplateName.trim() || !onSaveCustomHookTemplate) return;
      setIsSavingCustom(true);
      try {
        const tiersObj = {};
        const masterMul = ((hookOverlay?.look?.size_pct ?? 100) / 100);
        (hookOverlay?.tiers || []).forEach((t, i) => {
          const tierKey = TIER_KEYS[i];
          if (tierKey) {
            const resolved = resolveLook(hookOverlay.look, t.look);
            tiersObj[tierKey] = {
              size_pct: Math.round((resolved.size_pct ?? 100) * masterMul),
              color: resolved.color ?? '#FFFFFF',
              outline_color: resolved.outline_color ?? '#000000',
              outline_px: resolved.outline_px ?? 8,
              upper: resolved.upper ?? false,
              bold: resolved.bold ?? false,
              italic: resolved.italic ?? false,
              underline: resolved.underline ?? false,
              pill: resolved.pill ? (typeof resolved.pill === 'string' ? resolved.pill : resolved.pill.fill) : null,
            };
          }
        });

        const payload = {
          name: newTemplateName.trim(),
          label_th: newTemplateName.trim(),
          font: (hookOverlay?.look?.font) || 'Kanit',
          motion: hookOverlay?.anim || { in: 'pop', out: 'fade', loop: 'pulse' },
          tiers: tiersObj,
        };
        await onSaveCustomHookTemplate(payload);
        setSaveSuccess(true);
        setNewTemplateName('');
        setTimeout(() => setSaveSuccess(false), 2500);
      } catch (err) {
        alert(err?.message || 'บันทึกสไตล์ไม่สำเร็จ');
      } finally {
        setIsSavingCustom(false);
      }
    };

    const combinedTemplates = { ...(customHookTemplates || {}), ...(hookTemplates || {}) };

    return (
      <div
        ref={hookHeaderCardRef}
        className="rounded-2xl border border-white/[0.08] bg-black/40 p-3 space-y-3"
      >
        <div className="flex items-center justify-between pb-1 border-b border-white/[0.08]">
          <span className="text-xs font-bold text-[#E6C24A] flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-[#E6C24A]" />
            <span>ป้ายฮุก</span>
            <span className="font-mono text-[10px] text-[#E6C24A]/60">
              {(hookOverlay?.start ?? 0).toFixed(1)}–{(hookOverlay?.end ?? 3).toFixed(1)}s
            </span>
          </span>
          <button
            type="button"
            onClick={onToggleHookHeader}
            className={`px-2 py-0.5 rounded text-[10px] font-bold border transition-colors cursor-pointer ${
              showHookHeader
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                : 'bg-white/[0.05] text-slate-500 border-white/[0.08]'
            }`}
          >
            {showHookHeader ? 'เปิดใช้งาน' : 'ปิดอยู่'}
          </button>
        </div>

        {!hookOverlay ? (
          <p className="py-4 text-center text-xs text-slate-500">
            ยังไม่มีป้ายฮุก — กด “ปิดอยู่” ด้านบนเพื่อสร้าง
          </p>
        ) : (
          <>
            {/* Template row */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium text-slate-400">สไตล์</span>
                <button
                  type="button"
                  onClick={onHookStyleReset}
                  disabled={!hasHookOverrides}
                  title="คืนทุกแถวกลับเป็นค่าของสไตล์นี้"
                  className={`flex items-center gap-1 rounded-lg px-2 py-0.5 text-[10px] font-bold transition-all ${
                    hasHookOverrides
                      ? 'text-[#E6C24A] hover:bg-[#E6C24A]/10 cursor-pointer'
                      : 'text-slate-600 cursor-not-allowed'
                  }`}
                >
                  <RotateCcw className="h-3 w-3" />
                  รีเซ็ต
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(combinedTemplates).map(([key, tpl]) => {
                  const isSelected = hookOverlay.template === key;
                  const labelParts = (tpl.label_th || tpl.name || key).split(' — ');
                  const titleName = labelParts[0] || key;
                  const motionTag = tpl.motion?.loop || tpl.motion?.in || 'pop';
                  const motionClass = getMotionPreviewClass(tpl.motion);
                  const isCustom = !!tpl.is_custom || (customHookTemplates && !!customHookTemplates[key]);

                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => onHookTemplate(key)}
                      title={tpl.label_th || tpl.name || key}
                      className={`group relative flex flex-col gap-1.5 rounded-xl border p-2 text-left transition-all hover:-translate-y-0.5 cursor-pointer overflow-hidden ${
                        isSelected
                          ? isCustom
                            ? 'border-[#25F4EE] bg-[#25F4EE]/10 shadow-[0_0_15px_rgba(37,244,238,0.2)] ring-1 ring-[#25F4EE]/50'
                            : 'border-[#E6C24A] bg-[#E6C24A]/10 shadow-[0_0_15px_rgba(230,194,74,0.2)] ring-1 ring-[#E6C24A]/50'
                          : isCustom
                            ? 'border-[#25F4EE]/30 bg-gradient-to-b from-[#18181B] to-[#0E0E10] hover:border-[#25F4EE]/60'
                            : 'border-white/[0.08] bg-gradient-to-b from-[#18181B] to-[#0E0E10] hover:border-[#E6C24A]/60'
                      }`}
                    >
                      {/* Delete button for custom template */}
                      {isCustom && onDeleteCustomHookTemplate && (
                        <span
                          role="button"
                          tabIndex={0}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm(`ต้องการลบแม่แบบ "${tpl.label_th || tpl.name || key}" ใช่หรือไม่?`)) {
                              onDeleteCustomHookTemplate(key);
                            }
                          }}
                          title="ลบแม่แบบนี้"
                          className="absolute top-1 right-1 z-20 p-1 rounded bg-black/70 hover:bg-red-500/80 text-slate-400 hover:text-white transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-2.5 h-2.5" />
                        </span>
                      )}

                      {/* Top Header: Title + Motion Badge */}
                      <div className="flex items-center justify-between gap-1 w-full">
                        <span className={`text-[11px] font-bold truncate ${
                          isSelected
                            ? (isCustom ? 'text-[#25F4EE]' : 'text-[#E6C24A]')
                            : (isCustom ? 'text-[#25F4EE]' : 'text-slate-200')
                        }`}>
                          {titleName}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-mono font-bold bg-black/60 shrink-0 border ${
                          isCustom ? 'text-[#25F4EE] border-[#25F4EE]/30' : 'text-[#E6C24A] border-[#E6C24A]/30'
                        }`}>
                          {motionTag.toUpperCase()}
                        </span>
                      </div>

                      {/* Mini Live Preview Box with Micro-Motion on Hover */}
                      <div className="relative flex h-16 w-full flex-col items-center justify-center gap-0.5 overflow-hidden rounded-lg border border-white/[0.04] bg-black/60 p-1">
                        <div className="absolute inset-x-0 top-0 h-1/2 bg-gradient-to-b from-black/70 to-transparent pointer-events-none" />
                        <div className={`w-full flex flex-col items-center justify-center gap-0.5 relative z-10 transition-transform duration-200 ${motionClass}`}>
                          {TIER_KEYS.map((tierKey, i) => (
                            <TextLookPreview
                              key={tierKey}
                              look={hookCardLook(tpl, tierKey)}
                              text={HOOK_CARD_SAMPLE[i]}
                              baseFsRatio={HOOK_FS_RATIO}
                              scale={0.16}
                            />
                          ))}
                        </div>
                      </div>

                      {/* Footer: Font & Active indicator */}
                      <div className="flex items-center justify-between text-[9.5px] text-slate-400 pt-0.5">
                        <span className="truncate">{tpl.font}</span>
                        {isSelected && (
                          <span className={`text-[9px] font-bold shrink-0 ${isCustom ? 'text-[#25F4EE]' : 'text-[#E6C24A]'}`}>
                            ใช้งานอยู่
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Save As My Style Card */}
            {onSaveCustomHookTemplate && (
              <div className="rounded-xl border border-[#25F4EE]/30 bg-[#25F4EE]/5 p-2.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-[#25F4EE] flex items-center gap-1.5">
                    <BookmarkPlus className="w-3.5 h-3.5" />
                    <span>บันทึกเป็นสไตล์ของฉัน</span>
                  </span>
                  {saveSuccess && (
                    <span className="text-[10px] font-bold text-emerald-400 flex items-center gap-0.5">
                      <Check className="w-3 h-3" />
                      <span>บันทึกเรียบร้อย!</span>
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    value={newTemplateName}
                    onChange={(e) => setNewTemplateName(e.target.value)}
                    placeholder="พิมพ์ชื่อสไตล์ (เช่น VIP Gold, สไตล์ประจำแบรนด์)..."
                    className="flex-1 min-w-0 rounded-lg border border-white/[0.12] bg-black/60 px-2 py-1 text-xs text-white placeholder-slate-500 focus:border-[#25F4EE] focus:outline-none"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveCustom();
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleSaveCustom}
                    disabled={!newTemplateName.trim() || isSavingCustom}
                    className="flex items-center gap-1 rounded-lg bg-[#25F4EE] hover:bg-[#1fe2dc] disabled:opacity-40 disabled:cursor-not-allowed px-2.5 py-1 text-xs font-bold text-black transition-all cursor-pointer shrink-0"
                  >
                    {isSavingCustom ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <BookmarkPlus className="w-3.5 h-3.5" />
                    )}
                    <span>บันทึกสไตล์</span>
                  </button>
                </div>
              </div>
            )}

            {/* Duration */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-medium text-slate-400">ระยะเวลาแสดง</span>
                <span className="font-mono font-bold text-[#E6C24A]">{hookDuration.toFixed(1)} วิ</span>
              </div>
              <input
                type="range"
                min={HOOK_MIN_DURATION}
                max={HOOK_MAX_DURATION}
                step={0.1}
                value={hookDuration}
                onChange={(e) => onHookDurationChange(parseFloat(e.target.value))}
                className="w-full accent-[#E6C24A] cursor-pointer"
              />
            </div>

            {/* Master Font Selector */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-medium text-slate-400">ฟอนต์หลักของป้ายฮุก</span>
                <span className="font-mono text-[10px] text-[#E6C24A]">{hookOverlay.look?.font || 'Kanit'}</span>
              </div>
              <select
                value={hookOverlay.look?.font || 'Kanit'}
                onChange={(e) => onReplaceOverlay?.(hookOverlay.id, withHookFont(hookOverlay, e.target.value))}
                className="w-full rounded-lg border border-white/[0.1] bg-black/60 px-2 py-1.5 text-xs font-semibold text-white shadow-inner focus:border-[#E6C24A] focus:outline-none cursor-pointer"
              >
                {FONT_OPTIONS.map((f) => {
                  const fontVal = f.id || f.value;
                  const fontLbl = f.name || f.label;
                  return (
                    <option key={fontVal} value={fontVal} className="bg-[#18181B] text-white" style={{ fontFamily: fontVal }}>
                      {fontLbl}
                    </option>
                  );
                })}
              </select>
            </div>

            {/* One row per tier */}
            <div className="space-y-1.5">
              {HOOK_TIER_LABELS.map((tierLabel, idx) => {
                const tier = (hookOverlay.tiers || [])[idx];
                if (!tier) return null;
                const look = resolveLook(hookOverlay.look, tier.look);
                const overridden = hookOverrides[idx] || [];
                const open = openTier === idx;
                const swatch = look.color === ACCENT_COLOR ? '#FFE600' : look.color;
                return (
                  <div
                    key={tierLabel}
                    className={`rounded-xl border transition-colors ${
                      open ? 'border-[#E6C24A]/40 bg-black/50' : 'border-white/[0.07] bg-black/25'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setOpenTier(open ? -1 : idx)}
                      className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left cursor-pointer"
                    >
                      <span className="w-4 flex-shrink-0 font-mono text-[10px] text-slate-500">{idx + 1}</span>
                      <span className="min-w-0 flex-1 truncate text-[11px] font-bold text-slate-300">
                        {tier.text?.trim() || tierLabel}
                      </span>
                      <span className="flex-shrink-0 font-mono text-[10px] text-slate-500">
                        {look.size_pct}%
                      </span>
                      <span
                        className="h-3 w-3 flex-shrink-0 rounded-full border border-white/20"
                        style={{ background: swatch }}
                      />
                      <span
                        title={overridden.length ? `แก้จากสไตล์แล้ว: ${overridden.length} ค่า` : 'ค่าเดิมของสไตล์'}
                        className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                          overridden.length ? 'bg-[#E6C24A]' : 'bg-transparent ring-1 ring-slate-600'
                        }`}
                      />
                      <ChevronDown
                        className={`h-3 w-3 flex-shrink-0 text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`}
                      />
                    </button>

                    {open && (
                      <div className="space-y-2 border-t border-white/[0.06] px-2.5 pb-2.5 pt-2">
                        <input
                          ref={idx === 0 ? hookBrandInputRef : undefined}
                          value={tier.text || ''}
                          onChange={(e) => setHookTierText(idx, e.target.value)}
                          placeholder={tierLabel}
                          className="w-full rounded-lg border border-white/[0.1] bg-black/60 px-2 py-1.5 text-xs font-semibold text-white shadow-inner focus:border-[#E6C24A] focus:outline-none"
                        />

                        {/* Per-Tier Font Override */}
                        <div className="flex items-center gap-2">
                          <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">ฟอนต์</span>
                          <select
                            value={tier.font || ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              const updatedTiers = [...(hookOverlay.tiers || [])];
                              updatedTiers[idx] = { ...updatedTiers[idx], font: val || undefined };
                              onReplaceOverlay?.(hookOverlay.id, { ...hookOverlay, tiers: updatedTiers });
                            }}
                            className="min-w-0 flex-1 rounded border border-white/[0.1] bg-black/60 px-2 py-1 text-[11px] text-white focus:border-[#E6C24A] focus:outline-none cursor-pointer"
                          >
                            <option value="">ตามฟอนต์หลัก ({hookOverlay.look?.font || 'Kanit'})</option>
                            {FONT_OPTIONS.map((f) => {
                              const fontVal = f.id || f.value;
                              const fontLbl = f.name || f.label;
                              return (
                                <option key={fontVal} value={fontVal} className="bg-[#18181B] text-white" style={{ fontFamily: fontVal }}>
                                  {fontLbl}
                                </option>
                              );
                            })}
                          </select>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">ขนาด</span>
                          <input
                            type="range"
                            min={40}
                            max={220}
                            step={1}
                            value={look.size_pct}
                            onChange={(e) => patchHookTier(idx, { size_pct: parseInt(e.target.value, 10) })}
                            className="min-w-0 flex-1 accent-[#E6C24A] cursor-pointer"
                          />
                          <span className="w-9 flex-shrink-0 text-right font-mono text-[10px] text-[#E6C24A]">
                            {look.size_pct}%
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">สี</span>
                          <input
                            type="color"
                            value={swatch}
                            onChange={(e) => patchHookTier(idx, { color: e.target.value })}
                            className="h-6 w-8 flex-shrink-0 cursor-pointer rounded border border-white/[0.1] bg-transparent"
                          />
                          <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">ขอบ</span>
                          <input
                            type="color"
                            value={look.outline_color}
                            onChange={(e) => patchHookTier(idx, { outline_color: e.target.value })}
                            className="h-6 w-8 flex-shrink-0 cursor-pointer rounded border border-white/[0.1] bg-transparent"
                          />
                          <div className="ml-auto flex items-center gap-1">
                            <button
                              type="button"
                              onClick={() => patchHookTier(idx, { bold: !look.bold })}
                              title="ตัวหนา"
                              className={`h-6 w-6 flex items-center justify-center rounded-lg border text-[11px] font-black transition-all cursor-pointer ${
                                look.bold
                                  ? 'border-[#E6C24A] bg-[#E6C24A]/20 text-[#E6C24A]'
                                  : 'border-white/[0.08] bg-black/30 text-slate-500 hover:text-white'
                              }`}
                            >
                              B
                            </button>
                            <button
                              type="button"
                              onClick={() => patchHookTier(idx, { italic: !look.italic })}
                              title="ตัวเอียง"
                              className={`h-6 w-6 flex items-center justify-center rounded-lg border text-[11px] font-bold italic transition-all cursor-pointer font-serif ${
                                look.italic
                                  ? 'border-[#E6C24A] bg-[#E6C24A]/20 text-[#E6C24A]'
                                  : 'border-white/[0.08] bg-black/30 text-slate-500 hover:text-white'
                              }`}
                            >
                              I
                            </button>
                            <button
                              type="button"
                              onClick={() => patchHookTier(idx, { underline: !look.underline })}
                              title="ขีดเส้นใต้"
                              className={`h-6 w-6 flex items-center justify-center rounded-lg border text-[11px] font-bold underline transition-all cursor-pointer ${
                                look.underline
                                  ? 'border-[#E6C24A] bg-[#E6C24A]/20 text-[#E6C24A]'
                                  : 'border-white/[0.08] bg-black/30 text-slate-500 hover:text-white'
                              }`}
                            >
                              U
                            </button>
                            <button
                              type="button"
                              onClick={() => patchHookTier(idx, { upper: !look.upper })}
                              title="ตัวพิมพ์ใหญ่ทั้งบรรทัด"
                              className={`h-6 w-6 flex items-center justify-center rounded-lg border text-[10px] font-black transition-all cursor-pointer ${
                                look.upper
                                  ? 'border-[#E6C24A] bg-[#E6C24A]/20 text-[#E6C24A]'
                                  : 'border-white/[0.08] bg-black/30 text-slate-500 hover:text-white'
                              }`}
                            >
                              AA
                            </button>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">ขอบหนา</span>
                          <input
                            type="range"
                            min={0}
                            max={20}
                            step={0.5}
                            value={look.outline_px}
                            onChange={(e) => patchHookTier(idx, { outline_px: parseFloat(e.target.value) })}
                            className="min-w-0 flex-1 accent-[#E6C24A] cursor-pointer"
                          />
                          <span className="w-9 flex-shrink-0 text-right font-mono text-[10px] text-[#E6C24A]">
                            {look.outline_px}px
                          </span>
                        </div>

                        {look.color === ACCENT_COLOR && (
                          <p className="text-[10px] text-slate-500">
                            แถวนี้ใช้สีเดียวกับคำบรรยายอยู่ — เลือกสีเพื่อกำหนดเอง
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Motion presets */}
            <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
              <span className="text-xs font-bold text-slate-400">แอนิเมชันพาดหัว:</span>
              {[
                { cat: 'in', label: 'เข้า' },
                { cat: 'loop', label: 'ค้าง' },
                { cat: 'out', label: 'ออก' },
                { cat: 'accent', label: 'ตกแต่ง' },
              ].map(({ cat, label }) => {
                const options = cat === 'accent'
                  ? { ...FALLBACK_ACCENT_OPTIONS, ...(hookMotionCatalog?.[cat] || {}) }
                  : hookMotionCatalog?.[cat];
                if (!options) return null;
                return (
                  <React.Fragment key={cat}>
                    <div className="flex items-center gap-2">
                      <span className="w-12 flex-shrink-0 text-xs font-bold text-slate-400">{label}</span>
                      <select
                        value={hookMotion?.[cat] ?? hookMotionDefault?.[cat] ?? 'none'}
                        onChange={(e) => onHookMotionChange(cat, e.target.value)}
                        className="flex-1 min-w-0 rounded-lg border border-white/[0.1] bg-black/60 px-2 py-1 text-xs font-semibold text-white shadow-inner focus:border-[#E6C24A] focus:outline-none cursor-pointer"
                      >
                        {Object.entries(options).map(([id, meta]) => (
                          <option key={id} value={id}>{meta.label_th}</option>
                        ))}
                      </select>
                    </div>

                    {cat === 'accent' && (hookMotion?.accent ?? hookMotionDefault?.accent ?? 'none') !== 'none' && (
                      <div className="flex items-center gap-2 pl-14 pt-0.5 pb-1">
                        <span className="text-[10px] font-medium text-slate-400">สีตกแต่ง</span>
                        <div className="flex items-center gap-1.5 flex-1">
                          <input
                            type="color"
                            value={hookMotion?.accent_color || hookOverlay?.look?.accent_color || '#FFE600'}
                            onChange={(e) => {
                              const val = e.target.value;
                              onHookMotionChange('accent_color', val);
                              if (hookOverlay && onReplaceOverlay) {
                                onReplaceOverlay(hookOverlay.id, {
                                  ...hookOverlay,
                                  look: { ...(hookOverlay.look || {}), accent_color: val },
                                });
                              }
                            }}
                            className="h-6 w-8 flex-shrink-0 cursor-pointer rounded border border-white/[0.1] bg-transparent"
                            title="เลือกสีตกแต่งเอง"
                          />
                          <div className="flex items-center gap-1">
                            {['#FFE600', '#25F4EE', '#FE2C55', '#FFFFFF', '#A855F7', '#22C55E'].map((swatch) => (
                              <button
                                key={swatch}
                                type="button"
                                style={{ backgroundColor: swatch }}
                                onClick={() => {
                                  onHookMotionChange('accent_color', swatch);
                                  if (hookOverlay && onReplaceOverlay) {
                                    onReplaceOverlay(hookOverlay.id, {
                                      ...hookOverlay,
                                      look: { ...(hookOverlay.look || {}), accent_color: swatch },
                                    });
                                  }
                                }}
                                title={swatch}
                                className="w-4 h-4 rounded-full border border-black/40 hover:scale-110 transition-transform cursor-pointer"
                              />
                            ))}
                          </div>
                          {(hookMotion?.accent_color || hookOverlay?.look?.accent_color) && (
                            <button
                              type="button"
                              onClick={() => {
                                onHookMotionChange('accent_color', null);
                                if (hookOverlay && onReplaceOverlay) {
                                  onReplaceOverlay(hookOverlay.id, {
                                    ...hookOverlay,
                                    look: { ...(hookOverlay.look || {}), accent_color: null },
                                  });
                                }
                              }}
                              className="ml-auto text-[9px] px-1.5 py-0.5 rounded bg-white/[0.06] hover:bg-white/[0.12] text-slate-400 hover:text-white transition-colors cursor-pointer"
                              title="รีเซ็ตกลับไปใช้สีตามแถวไฮไลต์อัตโนมัติ"
                            >
                              อัตโนมัติ
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </React.Fragment>
                );
              })}

              {/* Animation Speed / Dynamics */}
              <div className="flex items-center gap-2 pt-1">
                <span className="w-12 flex-shrink-0 text-xs font-bold text-slate-400">สปีด</span>
                <div className="flex-1 grid grid-cols-3 gap-1 bg-black/40 p-0.5 rounded-lg border border-white/[0.08]">
                  {[
                    { id: 'fast', label: 'เร็ว (0.15s)' },
                    { id: 'normal', label: 'ปกติ (0.25s)' },
                    { id: 'smooth', label: 'นุ่มนวล (0.4s)' },
                  ].map((spd) => {
                    const isCurrent = (hookMotion?.speed || 'normal') === spd.id;
                    return (
                      <button
                        key={spd.id}
                        type="button"
                        onClick={() => onHookMotionChange('speed', spd.id)}
                        className={`py-1 px-1 text-[10px] font-bold rounded transition-all cursor-pointer truncate text-center ${
                          isCurrent
                            ? 'bg-[#E6C24A] text-black shadow-sm'
                            : 'text-slate-400 hover:text-white hover:bg-white/[0.06]'
                        }`}
                      >
                        {spd.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Stagger Toggle */}
              <div className="flex items-center justify-between text-xs pt-1">
                <span className="font-bold text-slate-400">ทยอยเด้งทีละแถว (Stagger)</span>
                <input
                  type="checkbox"
                  checked={hookMotion?.stagger !== false}
                  onChange={(e) => onHookMotionChange('stagger', e.target.checked)}
                  className="accent-[#E6C24A] w-4 h-4 cursor-pointer rounded"
                />
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  // ═════════════════════════════════════════════════════════════════════
  // SINGLE TEXT OVERLAY VIEW
  // ═════════════════════════════════════════════════════════════════════
  if (!selectedTextOverlay) return null;

  const selectedLook = resolveLook(selectedTextOverlay.look, (selectedTextOverlay.tiers || [{}])[0].look);
  const currentText = (selectedTextOverlay.tiers || [{}])[0].text || '';
  const currentFont = selectedLook.font || 'Kanit';
  const currentScale = (selectedLook.size_pct ?? 100) / 100;
  const currentColor = selectedLook.color === ACCENT_COLOR ? '#FFE600' : selectedLook.color;
  const currentPosition = selectedTextOverlay.position || 'middle';

  const patchOverlayLook = (patch) => {
    onReplaceOverlay?.(selectedTextOverlay.id, withTierLook(selectedTextOverlay, 0, patch));
  };

  const handleResetFormat = () => {
    onUpdateOverlay?.(selectedTextOverlay.id, { x: 0.5, y: 0.5, position: 'middle' });
    patchOverlayLook({
      size_pct: DEFAULT_TEXT_LOOK.size_pct,
      font: 'Kanit',
      color: '#FFE600',
      outline_color: DEFAULT_TEXT_LOOK.outline_color,
      outline_px: DEFAULT_TEXT_LOOK.outline_px,
    });
  };

  return (
    <div className="space-y-3">
      {/* Header Context Card */}
      <div className="flex items-center justify-between pb-1 border-b border-white/[0.08]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-white flex items-center gap-1.5">
            <Type className="w-4 h-4 text-[#25F4EE]" />
            ข้อความเสริมบนจอ
          </span>
        </div>

        <button
          type="button"
          onClick={() => onDeleteOverlay?.(selectedTextOverlay.id)}
          className="text-rose-400 hover:text-rose-300 text-[11px] font-bold flex items-center gap-1 px-2 py-0.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 cursor-pointer transition-colors"
          title="ลบข้อความเสริมนี้"
        >
          <Trash2 className="w-3 h-3" />
          <span>ลบ</span>
        </button>
      </div>

      <div className="flex items-center justify-end">
        <button
          type="button"
          onClick={handleResetFormat}
          className="px-2 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-[11px] font-semibold text-slate-300 hover:text-white flex items-center gap-1 transition-all cursor-pointer"
          title="คืนค่าตำแหน่งและขนาดเริ่มต้น"
        >
          <RotateCcw className="w-3 h-3 text-slate-400" />
          <span>รีเซ็ตค่าเริ่มต้น</span>
        </button>
      </div>

      {/* Textarea Content Box */}
      <div className="space-y-1.5">
        <textarea
          ref={textAreaRef}
          rows={2}
          value={currentText}
          onChange={(e) => onReplaceOverlay?.(selectedTextOverlay.id, withTierText(selectedTextOverlay, 0, e.target.value))}
          placeholder="พิมพ์ข้อความที่นี่..."
          className="w-full px-3 py-2 rounded-xl bg-black/60 border border-white/[0.1] text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE] shadow-inner resize-none font-medium leading-relaxed"
        />
      </div>

      {/* Timing Fine-tune */}
      <div className="grid grid-cols-2 gap-2 text-xs p-2.5 rounded-xl bg-black/40 border border-white/[0.08]">
        <div className="space-y-1">
          <span className="text-slate-400">เริ่ม (วินาที):</span>
          <input
            type="number"
            step="0.1"
            min="0"
            value={selectedTextOverlay.start ?? 0}
            onChange={(e) => onUpdateOverlay?.(selectedTextOverlay.id, { start: Math.max(0, parseFloat(e.target.value) || 0) })}
            className="w-full px-2.5 py-1 rounded-lg bg-black/60 border border-white/[0.1] text-xs font-mono text-white focus:outline-none focus:border-[#25F4EE]"
          />
        </div>
        <div className="space-y-1">
          <span className="text-slate-400">สิ้นสุด (วินาที):</span>
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={selectedTextOverlay.end ?? 2.5}
            onChange={(e) => onUpdateOverlay?.(selectedTextOverlay.id, { end: Math.max((selectedTextOverlay.start || 0) + 0.1, parseFloat(e.target.value) || 0.1) })}
            className="w-full px-2.5 py-1 rounded-lg bg-black/60 border border-white/[0.1] text-xs font-mono text-white focus:outline-none focus:border-[#25F4EE]"
          />
        </div>
      </div>

      {/* Typography Controls Card */}
      <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
        {/* Font dropdown */}
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-slate-400 font-medium w-14 flex-shrink-0">ฟอนต์:</span>
          <select
            value={currentFont}
            onChange={(e) => patchOverlayLook({ font: e.target.value })}
            className="flex-1 min-w-0 py-1.5 px-2.5 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-semibold text-white focus:outline-none focus:border-[#25F4EE] cursor-pointer"
          >
            {FONT_OPTIONS.map((f) => (
              <option key={f.id} value={f.id} className="bg-[#0A0D14] text-white">
                {f.name}
              </option>
            ))}
          </select>
        </div>

        {/* Font size slider & number input */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">ขนาดตัวอักษร:</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={50}
                max={220}
                step={5}
                value={Math.round(currentScale * 100)}
                onChange={(e) => {
                  const clamped = clampScale((parseInt(e.target.value, 10) || 100) / 100);
                  patchOverlayLook({ size_pct: Math.round(clamped * 100) });
                }}
                className="w-14 px-1.5 py-0.5 rounded-lg bg-black/60 border border-white/[0.1] text-right font-mono text-xs font-bold text-[#25F4EE] focus:outline-none focus:border-[#25F4EE]"
              />
              <span className="text-xs font-bold text-slate-400">%</span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {[0.7, 0.85, 1.0, 1.25, 1.5].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => patchOverlayLook({ size_pct: Math.round(s * 100) })}
                className={`flex-1 py-1 rounded-lg text-[10px] sm:text-[11px] font-bold border transition-all cursor-pointer ${
                  Math.abs(currentScale - s) < 0.05
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE] shadow-sm'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                {Math.round(s * 100)}%
              </button>
            ))}
          </div>
          <input
            type="range"
            min="0.5"
            max="1.8"
            step="0.05"
            value={currentScale}
            onChange={(e) => patchOverlayLook({ size_pct: Math.round(parseFloat(e.target.value) * 100) })}
            className="w-full accent-[#25F4EE] cursor-pointer"
          />
        </div>

        {/* Pattern and Alignment */}
        <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/[0.06]">
          <div className="space-y-1">
            <span className="text-[11px] text-slate-400 font-medium">รูปแบบ:</span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setTextPattern((p) => ({ ...p, bold: !p.bold }))}
                className={`flex-1 py-1 rounded-lg text-xs font-bold border transition-all cursor-pointer ${
                  textPattern.bold
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
                title="ตัวหนา"
              >
                B
              </button>
              {(() => {
                const isItalic = Math.abs(selectedLook.skew || 0) > 0.01;
                return (
                  <button
                    type="button"
                    onClick={() => patchOverlayLook({ skew: isItalic ? 0.0 : -0.25 })}
                    className={`flex-1 py-1 rounded-lg text-xs font-bold italic border transition-all cursor-pointer ${
                      isItalic
                        ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                        : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                    }`}
                    title="ตัวเอียง (Skew -0.25)"
                  >
                    I
                  </button>
                );
              })()}
              <button
                type="button"
                onClick={() => setTextPattern((p) => ({ ...p, underline: !p.underline }))}
                className={`flex-1 py-1 rounded-lg text-xs font-bold underline border transition-all cursor-pointer ${
                  textPattern.underline
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
                title="ขีดเส้นใต้"
              >
                U
              </button>
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] text-slate-400 font-medium">จัดแนว:</span>
            <div className="flex items-center gap-1">
              {[
                { id: 'left', icon: AlignLeft, title: 'ชิดซ้าย' },
                { id: 'center', icon: AlignCenter, title: 'กึ่งกลาง' },
                { id: 'right', icon: AlignRight, title: 'ชิดขวา' },
              ].map(({ id, icon: Icon, title }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setTextAlign(id)}
                  className={`flex-1 py-1 rounded-lg text-xs font-bold border transition-all flex items-center justify-center cursor-pointer ${
                    textAlign === id
                      ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                      : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                  }`}
                  title={title}
                >
                  <Icon className="w-3.5 h-3.5" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Position on screen */}
        <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
          <span className="text-[11px] text-slate-400 font-medium">ตำแหน่งบนจอ:</span>
          <div className="grid grid-cols-3 gap-1.5">
            {[
              { pos: 'top', label: 'บน (20%)' },
              { pos: 'middle', label: 'กลาง (50%)' },
              { pos: 'bottom', label: 'ล่าง (72%)' },
            ].map(({ pos, label }) => (
              <button
                key={pos}
                type="button"
                onClick={() => onUpdateOverlay?.(selectedTextOverlay.id, { position: pos, x: null, y: null })}
                className={`py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer ${
                  currentPosition === pos
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Color picker */}
        <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-400 font-medium">สีตัวอักษร:</span>
            <div className="flex items-center gap-1.5">
              <input
                type="color"
                value={currentColor.startsWith('#') ? currentColor : '#FFFFFF'}
                onChange={(e) => patchOverlayLook({ color: e.target.value })}
                className="h-6 w-6 rounded border border-white/20 bg-transparent cursor-pointer p-0"
              />
              <span className="text-xs font-mono font-bold text-white uppercase">
                {currentColor}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Preset Styles */}
      <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-300">สไตล์สำเร็จรูป (Preset Styles)</span>
          <span className="text-[10px] text-slate-500">คลิกเปลี่ยนทันที</span>
        </div>
        <div className="grid grid-cols-5 gap-1.5">
          {PRESET_STYLES.map((preset) => {
            const isCurrent = currentColor.toUpperCase() === preset.color.toUpperCase();
            return (
              <button
                key={preset.id}
                type="button"
                onClick={() => patchOverlayLook({ color: preset.color })}
                className={`flex flex-col items-center justify-center p-1.5 rounded-xl border transition-all cursor-pointer group ${
                  isCurrent
                    ? 'border-[#25F4EE] bg-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40 shadow-sm'
                    : 'border-white/[0.08] bg-black/60 hover:border-white/20'
                }`}
                title={`${preset.name}: ${preset.desc}`}
              >
                <div
                  className="w-full h-8 rounded-lg flex items-center justify-center font-black text-sm border shadow-inner"
                  style={{
                    backgroundColor: '#000000',
                    color: preset.color,
                    borderColor: preset.color + '40',
                    textShadow: '0 1px 3px rgba(0,0,0,0.9)',
                  }}
                >
                  Aa
                </div>
                <span className="text-[10px] font-bold text-slate-300 mt-1 truncate w-full text-center group-hover:text-white">
                  {preset.name}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Animation, Badge Style & Linked SFX */}
      <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
        <div className="flex items-center justify-between pb-1 border-b border-white/[0.06]">
          <span className="text-xs font-bold text-slate-200">แอนิเมชัน กรอบ และเสียงป็อปอัพ</span>
        </div>

        {/* 1. In-Animation selector */}
        <div className="space-y-1.5">
          <span className="text-[11px] text-slate-400 font-medium">แอนิเมชันตอนเปิดตัว (In-Animation):</span>
          <div className="grid grid-cols-3 gap-1">
            {[
              { id: 'snap', label: 'Pop เด้งเข้า' },
              { id: 'pop_zoom', label: 'Zoom พุ่งเข้า' },
              { id: 'stamp', label: 'Stamp กระแทก' },
              { id: 'rise', label: 'Slide เลื่อนขึ้น' },
              { id: 'quick_fade', label: 'Fade ค่อยๆ โผล่' },
              { id: 'none', label: 'None นิ่ง' },
            ].map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => onUpdateOverlay?.(selectedTextOverlay.id, { anim: { ...(selectedTextOverlay.anim || {}), in: a.id } })}
                className={`py-1 px-1 rounded-lg text-xs font-bold border transition-all cursor-pointer truncate text-center ${
                  (selectedTextOverlay.anim?.in || 'snap') === a.id
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>

        {/* 1.1 Word Stagger selector */}
        <div className="space-y-1.5">
          <span className="text-[11px] text-slate-400 font-medium">ความเร็วคำทยอยเข้า (Word Stagger):</span>
          <div className="grid grid-cols-4 gap-1">
            {[
              { id: 0, label: '0ms พร้อมกัน' },
              { id: 50, label: '50ms เร็ว' },
              { id: 70, label: '70ms กลาง' },
              { id: 100, label: '100ms ช้า' },
            ].map((s) => {
              const currentStagger = Number(selectedTextOverlay.anim?.word_stagger_ms || 0);
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => onUpdateOverlay?.(selectedTextOverlay.id, { anim: { ...(selectedTextOverlay.anim || {}), word_stagger_ms: s.id } })}
                  className={`py-1 px-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer truncate text-center ${
                    currentStagger === s.id
                      ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                      : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                  }`}
                >
                  {s.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 1.2 Loop Animation selector */}
        <div className="space-y-1.5">
          <span className="text-[11px] text-slate-400 font-medium">แอนิเมชันตอนค้าง (Loop Animation):</span>
          <div className="grid grid-cols-3 gap-1">
            {[
              { id: 'none', label: 'None นิ่ง' },
              { id: 'pulse', label: 'Pulse หายใจ' },
              { id: 'wave', label: 'Wave แกว่ง' },
              { id: 'shake', label: 'Shake สั่น' },
              { id: 'flicker', label: 'Flicker กระพริบ' },
              { id: 'lightsweep', label: 'Light Sweep แสงวาบ' },
            ].map((lp) => (
              <button
                key={lp.id}
                type="button"
                onClick={() => onUpdateOverlay?.(selectedTextOverlay.id, { anim: { ...(selectedTextOverlay.anim || {}), loop: lp.id } })}
                className={`py-1 px-1 rounded-lg text-xs font-bold border transition-all cursor-pointer truncate text-center ${
                  (selectedTextOverlay.anim?.loop || 'none') === lp.id
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                {lp.label}
              </button>
            ))}
          </div>
        </div>

        {/* 1.3 Out Animation selector */}
        <div className="space-y-1.5">
          <span className="text-[11px] text-slate-400 font-medium">แอนิเมชันตอนออก (Out Animation):</span>
          <div className="grid grid-cols-3 gap-1">
            {[
              { id: 'fade', label: 'Fade ค่อยๆ จาง' },
              { id: 'slide', label: 'Slide หล่นลง' },
              { id: 'zoom', label: 'Zoom ขยายจาง' },
              { id: 'glitch', label: 'Glitch สั่นวูบ' },
              { id: 'none', label: 'Cut ตัดทันที' },
            ].map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => onUpdateOverlay?.(selectedTextOverlay.id, { anim: { ...(selectedTextOverlay.anim || {}), out: o.id } })}
                className={`py-1 px-1 rounded-lg text-xs font-bold border transition-all cursor-pointer truncate text-center ${
                  (selectedTextOverlay.anim?.out || 'fade') === o.id
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        {/* 2. Badge Background Style */}
        <div className="space-y-1.5">
          <span className="text-[11px] text-slate-400 font-medium">สไตล์กรอบ/ป้ายพื้นหลัง:</span>
          <div className="grid grid-cols-3 gap-1">
            {[
              { id: 'none', label: 'ไม่มีกรอบ' },
              { id: 'pill', label: 'Dark Glass' },
              { id: 'badge_red', label: 'Sale แดง' },
              { id: 'badge_yellow', label: 'ดีล เหลือง' },
              { id: 'badge_cyan', label: 'Cyber นีออน' },
            ].map((bg) => (
              <button
                key={bg.id}
                type="button"
                onClick={() => patchOverlayLook({ pill: pillForBgStyle(bg.id) })}
                className={`py-1 px-1 rounded-lg text-xs font-bold border transition-all cursor-pointer truncate text-center ${
                  bgStyleOf(selectedLook.pill) === bg.id
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                {bg.label}
              </button>
            ))}
          </div>
        </div>

        {/* 3. Linked Sound FX */}
        <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
              <Volume2 className="w-3.5 h-3.5 text-amber-400" />
              <span>เสียงเอฟเฟกต์ (SFX):</span>
            </span>
            {selectedTextOverlay.sfx && (
              <button
                type="button"
                onClick={() => playSfxAudio(selectedTextOverlay.sfx)}
                className="px-2 py-0.5 rounded-md bg-amber-400/20 hover:bg-amber-400/30 text-amber-300 text-[10px] font-bold flex items-center gap-1 border border-amber-400/40 cursor-pointer transition-all"
                title="ทดลองฟังเสียงสด"
              >
                <Play className="w-2.5 h-2.5 fill-current" />
                <span>ลองฟัง</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <select
              value={selectedTextOverlay.sfx || 'none'}
              onChange={(e) => {
                const val = e.target.value === 'none' ? null : e.target.value;
                onUpdateOverlay?.(selectedTextOverlay.id, { sfx: val });
                if (val) playSfxAudio(val);
              }}
              className="w-full py-1.5 px-2 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-semibold text-white focus:outline-none focus:border-[#25F4EE] cursor-pointer"
            >
              <option value="none" className="bg-[#0A0D14] text-slate-400">ปิดเสียง (None)</option>
              <option value="pop" className="bg-[#0A0D14] text-white">Pop บับเบิล</option>
              <option value="ding" className="bg-[#0A0D14] text-white">Ding กระดิ่ง</option>
              <option value="cash" className="bg-[#0A0D14] text-white">Cash เปิดกล่องเงิน</option>
              <option value="sfx_coin_drop" className="bg-[#0A0D14] text-white">Coin เหรียญทอง</option>
              <option value="sfx_whoosh_fast" className="bg-[#0A0D14] text-white">Whoosh พุ่งเร็ว</option>
              <option value="boom" className="bg-[#0A0D14] text-white">Boom กระแทก</option>
              <option value="sfx_camera_shutter" className="bg-[#0A0D14] text-white">Shutter ถ่ายรูป</option>
              <option value="sfx_sub_drop" className="bg-[#0A0D14] text-white">Sub Drop ทุ้มลึก</option>
              <option value="sfx_bell_ding" className="bg-[#0A0D14] text-white">Bell Ding แจ้งเตือน</option>
              <option value="sfx_mouse_click" className="bg-[#0A0D14] text-white">Click คลิกเบา</option>
            </select>

            <div className="flex items-center text-[10px] text-slate-400 px-1">
              {selectedTextOverlay.sfx ? (
                <span className="text-emerald-400">✓ ผูกเสียงแล้ว (ลบตาม)</span>
              ) : (
                <span className="text-slate-500">ไม่มีเสียงประกอบ</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
