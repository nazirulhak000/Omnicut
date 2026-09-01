import React, { useMemo, useState } from 'react';
import {
  Check, Film, Music, Palette, Plus, Search, Sticker, Type, Volume2,
} from 'lucide-react';

const TABS = [
  { id: 'clips', label: 'คลิป', icon: Film },
  { id: 'audio', label: 'เสียง', icon: Music },
  { id: 'text', label: 'ข้อความ', icon: Type },
  { id: 'sticker', label: 'สติกเกอร์', icon: Sticker },
  { id: 'filter', label: 'ฟิลเตอร์', icon: Palette },
];

const FONTS = [
  { id: 'IBMPlex', name: 'IBM Plex Sans Thai' },
  { id: 'Kanit', name: 'Kanit' },
  { id: 'Prompt', name: 'Prompt' },
  { id: 'NotoSansThai', name: 'Noto Sans Thai' },
];

function Row({ active, onClick, children, title }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`group flex w-full items-center gap-2 rounded-lg border px-2 py-1.5 text-left transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
        active
          ? 'border-[#D97757] bg-[#33251F]'
          : 'border-[#363430] bg-[#1C1B19] hover:border-[#4A4742] hover:bg-[#232220]'
      }`}
    >
      {children}
    </button>
  );
}

export default function AssetPanel({
  videos,
  assets,             // { sfx, music, fonts, stickers, luts }
  style,              // { fontName, bgmName, lutName, stickerBadge }
  selectedCaption,    // cue object or null
  onAddClip,
  onStyleChange,
  onAssignSfx,
}) {
  const [tab, setTab] = useState('clips');
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const match = (item) => !q || `${item.label_th || ''} ${item.name || ''}`.toLowerCase().includes(q);
    return {
      videos: (videos || []).filter((v) => !q || v.name.toLowerCase().includes(q)),
      sfx: (assets?.sfx || []).filter(match),
      music: (assets?.music || []).filter(match),
      stickers: (assets?.stickers || []).filter(match),
      luts: (assets?.luts || []).filter(match),
    };
  }, [videos, assets, query]);

  return (
    <div className="flex h-full min-h-0 flex-col border-r border-[#363430] bg-[#232220]">
      {/* tab rail */}
      <div className="flex flex-shrink-0 border-b border-[#363430]">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            title={label}
            aria-pressed={tab === id}
            className={`flex flex-1 flex-col items-center gap-0.5 py-1.5 text-[9px] font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#D97757] ${
              tab === id
                ? 'bg-[#282724] text-[#E89274]'
                : 'cursor-pointer text-[#9C968F] hover:bg-[#2C2B27] hover:text-[#EDE9E3]'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      <div className="flex-shrink-0 p-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-[#6B6660]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="ค้นหา..."
            className="claude-input w-full py-1 pl-7 pr-2 text-[11px]"
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto px-2 pb-2">
        {tab === 'clips' && (
          <>
            {filtered.videos.map((v) => (
              <Row key={v.path} onClick={() => onAddClip(v)} title={`เพิ่ม ${v.name} เข้าไทม์ไลน์`}>
                <Film className="h-3.5 w-3.5 flex-shrink-0 text-[#9C968F] group-hover:text-[#E89274]" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-[#EDE9E3]">{v.name}</span>
                <Plus className="h-3.5 w-3.5 flex-shrink-0 text-[#6B6660] group-hover:text-[#E89274]" />
              </Row>
            ))}
            {filtered.videos.length === 0 && (
              <p className="px-1 py-3 text-[10px] text-[#6B6660]">
                ไม่มีคลิปที่ตรงกับคำค้น — อัปโหลดคลิปได้ที่แท็บ 1-Click Studio
              </p>
            )}
          </>
        )}

        {tab === 'audio' && (
          <>
            <p className="px-1 pt-1 text-[9px] font-semibold uppercase tracking-wide text-[#6B6660]">
              เพลงประกอบ (ทั้งคลิป)
            </p>
            <Row active={!style.bgmName} onClick={() => onStyleChange({ bgmName: null })}>
              <Music className="h-3.5 w-3.5 flex-shrink-0 text-[#9C968F]" />
              <span className="min-w-0 flex-1 truncate text-[11px] text-[#EDE9E3]">เสียงหลักของช่อง</span>
              {!style.bgmName && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
            </Row>
            {filtered.music.map((m) => (
              <Row
                key={m.id}
                active={style.bgmName === m.id}
                onClick={() => onStyleChange({ bgmName: m.id })}
                title={m.name}
              >
                <Music className="h-3.5 w-3.5 flex-shrink-0 text-[#9C968F]" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-[#EDE9E3]">{m.label_th || m.name}</span>
                {style.bgmName === m.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
              </Row>
            ))}

            <p className="px-1 pt-3 text-[9px] font-semibold uppercase tracking-wide text-[#6B6660]">
              เสียงเอฟเฟกต์ {selectedCaption ? '(ใส่ให้ท่อนที่เลือก)' : '(เลือกท่อนคำบรรยายก่อน)'}
            </p>
            {filtered.sfx.map((s) => (
              <Row
                key={s.id}
                active={selectedCaption?.sfx === s.id}
                onClick={() => selectedCaption && onAssignSfx(s.id)}
                title={selectedCaption ? `ใส่ ${s.name}` : 'เลือกท่อนคำบรรยายบนไทม์ไลน์ก่อน'}
              >
                <Volume2 className={`h-3.5 w-3.5 flex-shrink-0 ${selectedCaption ? 'text-[#9C968F]' : 'text-[#5A554F]'}`} />
                <span className={`min-w-0 flex-1 truncate text-[11px] ${selectedCaption ? 'text-[#EDE9E3]' : 'text-[#6B6660]'}`}>
                  {s.label_th || s.name}
                </span>
                {selectedCaption?.sfx === s.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
              </Row>
            ))}
          </>
        )}

        {tab === 'text' && (
          <>
            <p className="px-1 pt-1 text-[9px] font-semibold uppercase tracking-wide text-[#6B6660]">
              ฟอนต์คำบรรยาย
            </p>
            {FONTS.map((f) => (
              <Row key={f.id} active={style.fontName === f.id} onClick={() => onStyleChange({ fontName: f.id })}>
                <Type className="h-3.5 w-3.5 flex-shrink-0 text-[#9C968F]" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-[#EDE9E3]">{f.name}</span>
                {style.fontName === f.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
              </Row>
            ))}
            <p className="px-1 pt-3 text-[10px] leading-relaxed text-[#6B6660]">
              แก้ข้อความแต่ละท่อนได้ที่แผงขวา — คลิกท่อนคำบรรยายบนไทม์ไลน์
            </p>
          </>
        )}

        {tab === 'sticker' && (
          <>
            <Row active={!style.stickerBadge} onClick={() => onStyleChange({ stickerBadge: '' })}>
              <Sticker className="h-3.5 w-3.5 flex-shrink-0 text-[#9C968F]" />
              <span className="min-w-0 flex-1 truncate text-[11px] text-[#EDE9E3]">ไม่ใส่ป้าย</span>
              {!style.stickerBadge && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
            </Row>
            {filtered.stickers.map((s) => (
              <Row
                key={s.id}
                active={style.stickerBadge === s.name}
                onClick={() => onStyleChange({ stickerBadge: s.name })}
                title={s.name}
              >
                <img src={s.img_url} alt="" className="h-6 w-6 flex-shrink-0 rounded object-contain" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-[#EDE9E3]">{s.name.replace(/\.(png|webp|jpg)$/i, '')}</span>
                {style.stickerBadge === s.name && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
              </Row>
            ))}
            <p className="px-1 pt-2 text-[10px] leading-relaxed text-[#6B6660]">
              ป้ายวางมุมขวาบนตลอดคลิป — ยังเลือกตำแหน่งเองไม่ได้ในเวอร์ชันนี้
            </p>
          </>
        )}

        {tab === 'filter' && (
          <>
            <Row active={!style.lutName} onClick={() => onStyleChange({ lutName: null })}>
              <Palette className="h-3.5 w-3.5 flex-shrink-0 text-[#9C968F]" />
              <span className="min-w-0 flex-1 truncate text-[11px] text-[#EDE9E3]">ไม่ใช้ (เร็วกว่า)</span>
              {!style.lutName && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
            </Row>
            {filtered.luts.map((l) => (
              <Row
                key={l.id}
                active={style.lutName === l.id}
                onClick={() => onStyleChange({ lutName: l.id })}
                title={l.name}
              >
                <Palette className="h-3.5 w-3.5 flex-shrink-0 text-[#9C968F]" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-[#EDE9E3]">
                  {l.name.replace(/\.cube$/i, '')}
                </span>
                {style.lutName === l.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
              </Row>
            ))}
            {style.lutName && (
              <p className="px-1 pt-2 text-[10px] leading-relaxed text-[#C08A5E]">
                เครื่องนี้ไม่มีการ์ดจอ — ใส่ฟิลเตอร์แล้วเรนเดอร์ช้าลงราว 90%
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
