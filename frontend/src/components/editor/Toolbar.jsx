import React from 'react';
import {
  ArrowLeftToLine,
  ArrowRightToLine,
  AudioLines, ClipboardCopy, ClipboardPaste, Copy, FlipHorizontal2, Gauge, Link2, Magnet, Maximize2, Music2, Redo2, RotateCcw, Scissors, ScissorsLineDashed, Shield, Sparkles, Trash2, Undo2, Unlink, ZoomIn, ZoomOut, Type,
} from 'lucide-react';
import { formatTimecode } from '../../lib/timelineMath';
import { rippleScopeHint, rippleScopeLabel } from '../../lib/rippleUi';
import { pxPerSecToSlider, sliderToPxPerSec, zoomPercentageLabel } from '../../lib/timelineZoom.js';

const SPEEDS = [0.5, 1, 1.5, 2];

function ToolButton({ icon: Icon, label, hint, shortcut, onClick, disabled, active }) {
  const tip = [hint || label, shortcut && `(${shortcut})`].filter(Boolean).join(' ');
  return (
    <button
      type="button"
      onClick={() => {
        try { navigator.vibrate?.(10); } catch {}
        if (onClick) onClick();
      }}
      disabled={disabled}
      title={tip}
      aria-label={label}
      className={`flex h-11 sm:h-9 min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-xl px-2.5 text-sm font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] active:scale-[0.96] ${
        disabled
          ? 'cursor-not-allowed text-[#5A554F]'
          : active
            ? 'cursor-pointer bg-[#33251F] text-[#E89274]'
            : 'cursor-pointer text-[#C9C3BB] hover:bg-[#2C2B27] hover:text-[#EDE9E3]'
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

export default function Toolbar({
  playhead = 0,
  totalDuration = 0,
  hasClipSelected,
  hasSelection,
  selectedClip,
  canSplit = hasClipSelected,
  splitBlockedReason,
  canTrimHead = hasClipSelected,
  trimHeadBlockedReason,
  onTrimHead = null,
  canTrimTail = hasClipSelected,
  trimTailBlockedReason,
  onTrimTail = null,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onSplit,
  onAddText,
  onDuplicate,
  onCopySettings = null,
  onPasteSettings = null,
  canPasteSettings = false,
  selectedCount = 0,
  onDelete,
  onToggleMirror,
  onCycleSpeed,
  onResetClipTransform,
  hasTransformOverride = false,
  currentHookTemplate = 'tech',
  customHookTemplates = {},
  onApplyHookTemplate,
  showSafeZone = false,
  onToggleSafeZone,
  zoomIndex,
  zoomCount,
  pxPerSec = null,
  onZoomTo = null,
  onZoom,
  onZoomToFit,
  snapEnabled,
  onToggleSnap,
  beatSnapEnabled = false,
  onToggleBeatSnap,
  beatGridAvailable = false,
  beatBpm = null,
  onScanSilences,
  canScanSilences = false,
  silenceScanning = false,
  previewQuality = 'master1080',
  onPreviewQualityChange = null,
  highResStillEnabled = true,
  onToggleHighResStill = null,
  // Ripple delete. The scope toggle only exists while the project has a
  // voiceover: without one there is nothing to cut together with the picture.
  // `rangeReady` = both In and Out are marked, so the range cut is offered.
  rippleScope = 'all',
  showRippleScope = false,
  onToggleRippleScope = null,
  rangeReady = false,
  onRippleRange = null,
}) {
  const speed = selectedClip?.speed || 1;
  const nextSpeed = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length] || 1;

  return (
    <div className="flex items-center gap-1 border-b border-[#363430] bg-[#232220] px-2 py-1 overflow-x-auto no-scrollbar min-w-0">
      <ToolButton icon={Undo2} label="ย้อน" hint="ย้อนการแก้ล่าสุด" shortcut="Ctrl+Z" onClick={onUndo} disabled={!canUndo} />
      <ToolButton icon={Redo2} label="ไปหน้า" hint="ทำสิ่งที่เพิ่งย้อนไปอีกครั้ง" shortcut="Ctrl+Shift+Z" onClick={onRedo} disabled={!canRedo} />

      <span className="mx-1 h-4 w-px bg-[#363430]" />

      <ToolButton icon={Scissors} label="แยก" hint={!canSplit && splitBlockedReason ? splitBlockedReason : 'ผ่าคลิปตรงหัวอ่าน'} shortcut="S / Ctrl+B" onClick={onSplit} disabled={!canSplit} />
      <ToolButton
        icon={ArrowRightToLine}
        label="ตัดหัว"
        hint={!canTrimHead && trimHeadBlockedReason ? trimHeadBlockedReason : 'ตัดหัวคลิปทิ้งถึงหัวอ่านแล้วดึงคลิปมาชิด'}
        shortcut="Q"
        onClick={onTrimHead}
        disabled={!onTrimHead || !canTrimHead}
      />
      <ToolButton
        icon={ArrowLeftToLine}
        label="ตัดท้าย"
        hint={!canTrimTail && trimTailBlockedReason ? trimTailBlockedReason : 'ตัดท้ายคลิปทิ้งถึงหัวอ่าน'}
        shortcut="W"
        onClick={onTrimTail}
        disabled={!onTrimTail || !canTrimTail}
      />
      <ToolButton icon={Type} label="เพิ่มข้อความ" hint="แทรกข้อความใหม่ตรงหัวอ่าน" onClick={onAddText} />
      <ToolButton icon={Copy} label="ทำสำเนา" hint="ก๊อบคลิปที่เลือกต่อท้ายตัวเอง" onClick={onDuplicate} disabled={!hasClipSelected} />
      <ToolButton
        icon={ClipboardCopy}
        label="คัดลอกค่า"
        hint="คัดลอกความเร็ว ซูม/แพน สี ทรานซิชันของคลิปหลัก"
        shortcut="Ctrl+Alt+C"
        onClick={onCopySettings}
        disabled={!hasClipSelected}
      />
      <ToolButton
        icon={ClipboardPaste}
        label={selectedCount > 1 ? `วางค่า (${selectedCount})` : 'วางค่า'}
        hint={canPasteSettings ? 'วางการตั้งค่าที่คัดลอกไว้ลงคลิปที่เลือก' : 'ยังไม่ได้คัดลอกการตั้งค่าจากคลิปไหน'}
        shortcut="Ctrl+Alt+V"
        onClick={onPasteSettings}
        disabled={!canPasteSettings || (!hasClipSelected && selectedCount === 0)}
      />
      <ToolButton icon={Trash2} label="ลบ" shortcut="Del" onClick={onDelete} disabled={!hasSelection} />
      {/* One control, one icon: it says what Delete does to the voice and the
          captions now, and a click flips it. Hidden without a voiceover. */}
      {showRippleScope && onToggleRippleScope && (
        <ToolButton
          icon={rippleScope === 'video' ? Unlink : Link2}
          label={rippleScopeLabel(rippleScope)}
          hint={rippleScopeHint(rippleScope)}
          onClick={onToggleRippleScope}
          active={rippleScope !== 'video'}
        />
      )}
      {/* Offered only once In and Out are both marked (I / O keys). */}
      {rangeReady && onRippleRange && (
        <ToolButton
          icon={ScissorsLineDashed}
          label="ตัดช่วงที่ตั้งไว้"
          hint="ตัดช่วงระหว่างจุดเข้า-จุดออกทิ้งแล้วดึงส่วนที่เหลือมาชิด (ยืนยันก่อนตัดจริง)"
          shortcut="Shift+Del"
          onClick={onRippleRange}
        />
      )}

      <span className="mx-1 h-4 w-px bg-[#363430]" />

      <ToolButton
        icon={FlipHorizontal2}
        label="กลับด้าน"
        onClick={onToggleMirror}
        disabled={!hasClipSelected}
        active={!!selectedClip?.mirror}
      />
      <ToolButton
        icon={Gauge}
        label={`${speed}x`}
        shortcut={`คลิกเป็น ${nextSpeed}x`}
        onClick={onCycleSpeed}
        disabled={!hasClipSelected}
        active={speed !== 1}
      />
      <ToolButton
        icon={RotateCcw}
        label="รีเซ็ตซูม"
        hint="คืนค่าซูมและตำแหน่งช็อตเป็น 100%"
        onClick={onResetClipTransform}
        disabled={!hasClipSelected || !hasTransformOverride}
        active={hasTransformOverride}
      />

      {/* Quick Hook Style Preset Selector */}
      <span className="mx-1 h-4 w-px bg-[#363430]" />
      <div
        className="flex items-center gap-1.5 rounded-lg bg-[#1C1B19] border border-[#3A3833] px-2 py-1 text-xs flex-shrink-0"
        title="เลือกสไตล์ป้ายฮุกพาดหัวคลิป (สร้างหรือเปลี่ยนทันที)"
      >
        <Sparkles className="h-3.5 w-3.5 text-[#FFE600] flex-shrink-0" />
        <span className="text-[#A8A29E] font-medium hidden md:inline">ฮุก:</span>
        <select
          value={currentHookTemplate || 'tech'}
          onChange={(e) => onApplyHookTemplate?.(e.target.value)}
          className="bg-transparent text-xs font-semibold text-[#EDE9E3] focus:outline-none cursor-pointer pr-1"
        >
          {Object.keys(customHookTemplates || {}).length > 0 && (
            <optgroup label="🌟 แม่แบบของฉัน">
              {Object.entries(customHookTemplates).map(([id, tpl]) => (
                <option key={id} value={id} className="bg-[#232220] text-[#25F4EE]">
                  {tpl.label_th || tpl.name || id}
                </option>
              ))}
            </optgroup>
          )}
          <optgroup label="⚡ แม่แบบมาตรฐาน T1">
            <option value="b1_viral_red" className="bg-[#232220] text-[#EDE9E3]">T1 (แดง+กระพริบ)</option>
            <option value="b2_clean_yellow" className="bg-[#232220] text-[#EDE9E3]">T1 (เหลือง+สั่น)</option>
            <option value="b2_tech_cyan" className="bg-[#232220] text-[#EDE9E3]">T1 (ฟ้า+สั่นเบา)</option>
            <option value="b1_smooth_mint" className="bg-[#232220] text-[#EDE9E3]">T1 (เขียวมิ้นต์+กวาดแสง)</option>
            <option value="b2_premium_gold" className="bg-[#232220] text-[#EDE9E3]">T1 (ทอง+สั่นเบา)</option>
            <option value="b1_deal_orange" className="bg-[#232220] text-[#EDE9E3]">T1 (ส้ม+กระพริบ)</option>
            <option value="b1_pain_pink" className="bg-[#232220] text-[#EDE9E3]">T1 (ชมพู+สั่น)</option>
            <option value="b2_compare_blue" className="bg-[#232220] text-[#EDE9E3]">T1 (น้ำเงิน+คลื่น)</option>
            <option value="b1_hack_lime" className="bg-[#232220] text-[#EDE9E3]">T1 (เขียวมะนาว+กวาดแสง)</option>
            <option value="b2_niche_purple" className="bg-[#232220] text-[#EDE9E3]">T1 (ม่วง+คลื่น)</option>
          </optgroup>
        </select>
      </div>

      <div className="ml-auto flex items-center gap-1">
        <ToolButton
          icon={Magnet}
          label="ดูดขอบ"
          onClick={onToggleSnap}
          active={snapEnabled}
        />
        {/* Dead-air trimming. Disabled without a voiceover rather than hidden,
            so the capability is discoverable and the tooltip can say what it
            needs. The label names the action, not the finding: pressing it
            only proposes a cut, which is then confirmed. */}
        {onScanSilences && (
          <ToolButton
            icon={AudioLines}
            label="ตัดช่วงเงียบ"
            hint={canScanSilences
              ? 'ตรวจหาช่วงเงียบในเสียงพากย์แล้วเสนอการตัด (ยืนยันก่อนตัดจริง)'
              : 'ต้องมีเสียงพากย์ในโปรเจกต์ก่อน'}
            onClick={onScanSilences}
            disabled={!canScanSilences || silenceScanning}
            active={silenceScanning}
          />
        )}
        {/* Only offered once a beat grid exists: a control that cannot do
            anything is worse than no control. The hint carries the measured
            tempo so the user can tell the analysis found real music. */}
        {beatGridAvailable && (
          <ToolButton
            icon={Music2}
            label="ดูดจังหวะ"
            hint={beatBpm ? `ดูดขอบคลิปเข้าจังหวะเพลง (${Math.round(beatBpm)} BPM)` : 'ดูดขอบคลิปเข้าจังหวะเพลง'}
            onClick={onToggleBeatSnap}
            active={beatSnapEnabled && snapEnabled}
            disabled={!snapEnabled}
          />
        )}
        <span className="mx-1 h-4 w-px bg-[#363430]" />
        <ToolButton icon={ZoomOut} label="" hint="ซูมออก (ปุ่ม -)" onClick={() => onZoom(-1)} disabled={zoomIndex <= 0} />
        {onZoomTo && pxPerSec ? (
          <div className="flex items-center gap-1.5 px-1" title="ลากเพื่อซูมไทม์ไลน์อิสระ (Ctrl+Scroll บนไทม์ไลน์)">
            <input
              type="range"
              min="0"
              max="1000"
              step="1"
              value={Math.round(pxPerSecToSlider(pxPerSec) * 1000)}
              onChange={(e) => onZoomTo(sliderToPxPerSec(Number(e.target.value) / 1000))}
              aria-label="แถบซูมไทม์ไลน์"
              className="h-1.5 w-16 sm:w-20 cursor-pointer appearance-none rounded-full bg-[#363430] accent-[#E89274] hover:bg-[#48453F]"
            />
            <span className="w-11 text-center font-mono text-xs font-semibold text-[#9C968F]" title={`สเกล ${Math.round(pxPerSec)} px/s`}>
              {zoomPercentageLabel(pxPerSec)}
            </span>
          </div>
        ) : (
          <span className="w-10 text-center font-mono text-sm text-[#9C968F]">
            {zoomIndex + 1}/{zoomCount}
          </span>
        )}
        <ToolButton icon={ZoomIn} label="" hint="ซูมเข้า (ปุ่ม +) · Ctrl+เลื่อนล้อเมาส์ซูมต่อเนื่อง" onClick={() => onZoom(1)} disabled={zoomIndex >= zoomCount - 1} />
        <ToolButton icon={Maximize2} label="" hint="ซูมให้เห็นทั้งคลิปพอดีจอ" onClick={onZoomToFit} disabled={!onZoomToFit} />
      </div>
    </div>
  );
}
