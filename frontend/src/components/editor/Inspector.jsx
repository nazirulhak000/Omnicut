import React from 'react';
import { AlertTriangle, Film, MessageSquare, Settings2 } from 'lucide-react';
import { formatTimecode } from '../../lib/timelineMath';

const SPEEDS = [0.5, 1, 1.5, 2];

function Section({ icon: Icon, title, children }) {
  return (
    <div className="space-y-2">
      <h3 className="flex items-center gap-1.5 border-b border-[#363430] pb-1.5 text-[11px] font-semibold text-[#EDE9E3]">
        <Icon className="h-3.5 w-3.5 text-[#E89274]" />
        {title}
      </h3>
      {children}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] font-medium text-[#9C968F]">{label}</span>
      {children}
    </label>
  );
}

function NumberInput(props) {
  return <input type="number" {...props} className="claude-input w-full px-2 py-1 font-mono text-[11px]" />;
}

export default function Inspector({
  selection,
  selectedSeg,
  selectedCaption,
  style,
  totalDuration,
  audioDuration,
  onClipChange,
  onCaptionChange,
}) {
  const gap = (audioDuration || 0) - totalDuration;

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto border-l border-[#363430] bg-[#232220] p-3">
      {selection?.type === 'clip' && selectedSeg && (
        <Section icon={Film} title={`คลิปที่ ${selectedSeg.index + 1}`}>
          <p className="truncate text-[10px] text-[#9C968F]" title={selectedSeg.clip.source_path}>
            {(selectedSeg.clip.source_path || '').split(/[\\/]/).pop()}
          </p>

          <div className="grid grid-cols-2 gap-2">
            <Field label="เข้า (วิ)">
              <NumberInput
                step="0.1"
                min="0"
                value={selectedSeg.clip.trim_start}
                onChange={(e) => onClipChange({ trim_start: Math.max(0, parseFloat(e.target.value) || 0) })}
              />
            </Field>
            <Field label="ออก (วิ)">
              <NumberInput
                step="0.1"
                min="0"
                placeholder="สุดคลิป"
                value={selectedSeg.clip.trim_end ?? ''}
                onChange={(e) => onClipChange({
                  trim_end: e.target.value === '' ? null : parseFloat(e.target.value),
                })}
              />
            </Field>
          </div>

          <div className="rounded-lg bg-[#1C1B19] px-2 py-1.5 text-[10px] text-[#9C968F]">
            ยาวบนไทม์ไลน์ <span className="font-mono text-[#EDE9E3]">{selectedSeg.dur.toFixed(2)}s</span>
            {' · '}ต้นฉบับ <span className="font-mono">{selectedSeg.srcDur.toFixed(1)}s</span>
          </div>

          <Field label="ความเร็ว">
            <div className="flex gap-1">
              {SPEEDS.map((s) => {
                const active = (selectedSeg.clip.speed || 1) === s;
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onClipChange({ speed: s === 1 ? undefined : s })}
                    className={`flex-1 rounded-lg py-1 text-[11px] font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
                      active
                        ? 'bg-[#D97757] text-white'
                        : 'cursor-pointer bg-[#1C1B19] text-[#C9C3BB] hover:bg-[#2C2B27]'
                    }`}
                  >
                    {s}x
                  </button>
                );
              })}
            </div>
          </Field>

          <button
            type="button"
            onClick={() => onClipChange({ mirror: !selectedSeg.clip.mirror })}
            className={`w-full rounded-lg py-1.5 text-[11px] font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
              selectedSeg.clip.mirror
                ? 'bg-[#33251F] text-[#E89274] ring-1 ring-[#D97757]'
                : 'cursor-pointer bg-[#1C1B19] text-[#C9C3BB] hover:bg-[#2C2B27]'
            }`}
          >
            {selectedSeg.clip.mirror ? 'กลับซ้ายขวาอยู่ · คลิกเพื่อยกเลิก' : 'กลับซ้ายขวา'}
          </button>

          {selectedSeg.index > 0 && (
            <Field label="รอยต่อกับคลิปก่อนหน้า">
              <div className="flex gap-1">
                {['cut', 'fade'].map((mode) => {
                  const active = (selectedSeg.clip.transition_in || 'cut') === mode;
                  return (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => onClipChange({ transition_in: mode })}
                      className={`flex-1 rounded-lg py-1 text-[11px] font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
                        active
                          ? 'bg-[#D97757] text-white'
                          : 'cursor-pointer bg-[#1C1B19] text-[#C9C3BB] hover:bg-[#2C2B27]'
                      }`}
                    >
                      {mode === 'cut' ? 'ตัดตรง' : 'fade 0.4s'}
                    </button>
                  );
                })}
              </div>
            </Field>
          )}
        </Section>
      )}

      {selection?.type === 'caption' && selectedCaption && (
        <Section icon={MessageSquare} title="ท่อนคำบรรยาย">
          <Field label="ข้อความ">
            <textarea
              rows={3}
              value={selectedCaption.text}
              onChange={(e) => onCaptionChange({ text: e.target.value })}
              className="claude-input w-full resize-none px-2 py-1.5 text-[11px]"
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="เริ่ม (วิ)">
              <NumberInput
                step="0.1"
                value={selectedCaption.start}
                onChange={(e) => onCaptionChange({ start: parseFloat(e.target.value) || 0 })}
              />
            </Field>
            <Field label="จบ (วิ)">
              <NumberInput
                step="0.1"
                value={selectedCaption.end}
                onChange={(e) => onCaptionChange({ end: parseFloat(e.target.value) || 0 })}
              />
            </Field>
          </div>
          <div className="rounded-lg bg-[#1C1B19] px-2 py-1.5 text-[10px] text-[#9C968F]">
            SFX: <span className="font-mono text-[#EDE9E3]">{selectedCaption.sfx || 'ไม่มี'}</span>
            <span className="block pt-0.5 text-[9px]">เลือกเสียงใหม่ได้ที่แท็บ “เสียง” ด้านซ้าย</span>
          </div>
        </Section>
      )}

      {!selection?.type && (
        <Section icon={Settings2} title="ทั้งคลิป">
          <div className="space-y-1.5 rounded-lg bg-[#1C1B19] px-2 py-2 text-[10px] text-[#9C968F]">
            <div className="flex justify-between">
              <span>ฟอนต์</span><span className="font-mono text-[#EDE9E3]">{style.fontName}</span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="flex-shrink-0">เพลง</span>
              <span className="truncate font-mono text-[#EDE9E3]">{style.bgmName || 'ค่าเริ่มต้น'}</span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="flex-shrink-0">ฟิลเตอร์</span>
              <span className="truncate font-mono text-[#EDE9E3]">{style.lutName || 'ไม่ใช้'}</span>
            </div>
            <div className="flex justify-between">
              <span>ความยาววิดีโอ</span>
              <span className="font-mono text-[#EDE9E3]">{formatTimecode(totalDuration)}</span>
            </div>
            <div className="flex justify-between">
              <span>ความยาวเสียง</span>
              <span className="font-mono text-[#EDE9E3]">{formatTimecode(audioDuration || 0)}</span>
            </div>
          </div>
          <p className="text-[10px] leading-relaxed text-[#6B6660]">
            เลือกคลิปหรือท่อนคำบรรยายบนไทม์ไลน์เพื่อแก้รายตัว · เปลี่ยนฟอนต์/เพลง/ฟิลเตอร์ที่แผงซ้าย
          </p>
        </Section>
      )}

      {audioDuration > 0 && gap > 0.3 && (
        <div className="flex gap-2 rounded-lg border border-[#5C4326] bg-[#2E2418] p-2">
          <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-[#C08A5E]" />
          <p className="text-[10px] leading-relaxed text-[#D9BFA0]">
            วิดีโอสั้นกว่าเสียงพากย์ {gap.toFixed(1)} วิ — ช่วงท้ายจะไม่มีภาพ
            เพิ่มคลิปหรือลดความเร็วให้ยาวขึ้น
          </p>
        </div>
      )}
    </div>
  );
}
