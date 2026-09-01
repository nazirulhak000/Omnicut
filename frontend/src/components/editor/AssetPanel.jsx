import React, { useMemo, useState } from 'react';
import {
  Check, Film, Music, Palette, Plus, Search, Sticker, Type, Volume2,
  FileText, Sparkles, Loader2, Download, Copy, RefreshCw, Layers
} from 'lucide-react';
import { transcribeMedia } from '../../api';

const TABS = [
  { id: 'clips', label: 'คลิป', icon: Film },
  { id: 'srt', label: 'AI ถอดซับ', icon: FileText },
  { id: 'audio', label: 'เสียง', icon: Music },
  { id: 'text', label: 'ข้อความ', icon: Type },
  { id: 'sticker', label: 'สติกเกอร์', icon: Sticker },
  { id: 'filter', label: 'ฟิลเตอร์', icon: Palette },
];

// Drag payload type shared with Timeline's drop target.
export const CLIP_DRAG_TYPE = 'application/x-capcut-clip';

const FONTS = [
  { id: 'IBMPlex', name: 'IBM Plex Sans Thai' },
  { id: 'Kanit', name: 'Kanit' },
  { id: 'Prompt', name: 'Prompt' },
  { id: 'NotoSansThai', name: 'Noto Sans Thai' },
];

function parseSrtToCues(srtText) {
  if (!srtText) return [];
  const blocks = srtText.trim().split(/\n\s*\n/);
  const cues = [];

  const timeToSec = (timeStr) => {
    if (!timeStr) return 0;
    const [hms, ms] = timeStr.trim().replace('.', ',').split(',');
    const [h, m, s] = hms.split(':').map(Number);
    return (h || 0) * 3600 + (m || 0) * 60 + (s || 0) + (parseInt(ms || 0, 10) / 1000);
  };

  blocks.forEach((block) => {
    const lines = block.trim().split('\n');
    if (lines.length >= 2) {
      let timeLine = lines[0].includes('-->') ? lines[0] : lines[1];
      let textLines = lines[0].includes('-->') ? lines.slice(1) : lines.slice(2);

      if (timeLine && timeLine.includes('-->')) {
        const [startStr, endStr] = timeLine.split('-->');
        const start = timeToSec(startStr);
        const end = timeToSec(endStr);
        const text = textLines[0] || '';
        const translation = textLines.slice(1).join(' ') || '';

        cues.push({
          start: Number(start.toFixed(2)),
          end: Number(end.toFixed(2)),
          text: text.trim(),
          translation: translation.trim(),
          sfx: null
        });
      }
    }
  });

  return cues;
}

function Row({ active, onClick, children, title, draggable, onDragStart, onDragEnd }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      draggable={draggable}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={`group flex w-full items-center gap-2 rounded-lg border px-2 py-1.5 text-left transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE] ${
        active
          ? 'border-[#25F4EE] bg-[#25F4EE]/10 text-white'
          : 'border-white/[0.08] bg-black/40 hover:border-white/[0.2] hover:bg-white/[0.05]'
      }`}
    >
      {children}
    </button>
  );
}

export default function AssetPanel({
  videos = [],
  clipList = [],
  assets,             // { sfx, music, fonts, stickers, luts }
  style,              // { fontName, bgmName, lutName, stickerBadge }
  selectedCaption,    // cue object or null
  onAddClip,
  onStyleChange,
  onAssignSfx,
  onImportCues,       // (cues: Array<{ start, end, text, translation, sfx }>) => void
}) {
  const [tab, setTab] = useState('clips');
  const [query, setQuery] = useState('');

  // Auto-SRT Generator state inside Editor
  const [selectedMediaForSrt, setSelectedMediaForSrt] = useState(videos[0]?.path || '');
  const [srtMode, setSrtMode] = useState('bilingual'); // 'bilingual' | 'mono' | 'dual'
  const [srtLang, setSrtLang] = useState('th');
  const [srtDensity, setSrtDensity] = useState(5);
  const [transcribing, setTranscribing] = useState(false);
  const [transcribeResult, setTranscribeResult] = useState(null);
  const [transcribeError, setTranscribeError] = useState(null);
  const [copiedSrt, setCopiedSrt] = useState(false);
  const [importedSuccess, setImportedSuccess] = useState(false);

  const handleTranscribe = async () => {
    if (!selectedMediaForSrt) {
      alert('กรุณาเลือกคลิปวิดีโอหรือเสียงที่ต้องการถอดซับก่อนครับ');
      return;
    }

    setTranscribing(true);
    setTranscribeError(null);
    setTranscribeResult(null);
    setImportedSuccess(false);

    try {
      const res = await transcribeMedia({
        media_path: selectedMediaForSrt,
        mode: srtMode,
        lang: srtLang || null,
        words_per_line: srtDensity,
        fast: true
      });
      setTranscribeResult(res);
    } catch (err) {
      setTranscribeError(err.friendlyMessage || err.response?.data?.detail || err.message || 'ถอดเสียงล้มเหลว');
    } finally {
      setTranscribing(false);
    }
  };

  const handleImportToTimeline = () => {
    if (!transcribeResult?.content) return;
    const parsedCues = parseSrtToCues(transcribeResult.content);
    if (parsedCues.length === 0) {
      alert('ไม่พบข้อความซับไตเติลที่แยกเวลาได้');
      return;
    }
    onImportCues?.(parsedCues);
    setImportedSuccess(true);
    setTimeout(() => setImportedSuccess(false), 3000);
  };

  const handleCopySrt = () => {
    if (!transcribeResult?.content) return;
    navigator.clipboard.writeText(transcribeResult.content);
    setCopiedSrt(true);
    setTimeout(() => setCopiedSrt(false), 2000);
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const match = (item) => !q || `${item.label_th || ''} ${item.name || ''}`.toLowerCase().includes(q);
    return {
      videos: (videos || []).filter((v) => !q || v.name.toLowerCase().includes(q)),
      sfx: (assets?.sfx || []).filter(match),
      music: (assets?.music || []).filter(match),
      stickers: (assets?.stickers || []).filter(match),
      luts: (assets?.luts || []).filter(match),
      fonts: FONTS
        .map((f) => {
          // Match the render engine's font id to a real file on disk so the
          // row can be previewed in its own typeface instead of the UI font.
          const key = f.id.toLowerCase();
          const file = (assets?.fonts || []).find((a) => {
            const norm = (a.id || '').replace(/[^a-zA-Z]/g, '').toLowerCase();
            return norm.startsWith(key);
          });
          return { ...f, file };
        })
        .filter((f) => !q || `${f.name} ${f.id}`.toLowerCase().includes(q)),
    };
  }, [videos, assets, query]);

  return (
    <div className="flex h-full min-h-0 flex-col border-r border-white/[0.08] bg-[#0C1019]">
      {/* tab rail */}
      <div className="flex flex-shrink-0 border-b border-white/[0.08] overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            title={label}
            aria-pressed={tab === id}
            className={`flex flex-1 min-w-[50px] flex-col items-center gap-0.5 py-2 text-[10px] font-bold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#D97757] ${
              tab === id
                ? 'border-b-2 border-[#D97757] bg-[#D97757]/10 text-[#E89274]'
                : 'cursor-pointer text-[#9C968F] hover:bg-white/[0.04] hover:text-[#EDE9E3]'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Search box (hide in SRT tab) */}
      {tab !== 'srt' && (
        <div className="flex-shrink-0 p-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="ค้นหา..."
              className="w-full py-1.5 pl-8 pr-2.5 rounded-xl bg-black/50 border border-white/[0.08] text-white text-[11px] focus:outline-none focus:border-[#25F4EE]"
            />
          </div>
        </div>
      )}

      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
        {/* TAB 1: CLIPS */}
        {tab === 'clips' && (
          <>
            {filtered.videos.map((v) => (
              <Row
                key={v.path}
                onClick={() => onAddClip(v)}
                title={`คลิกเพื่อต่อท้าย หรือลากไปวางตรงจุดที่ต้องการบนไทม์ไลน์ — ${v.name}`}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.effectAllowed = 'copy';
                  e.dataTransfer.setData(CLIP_DRAG_TYPE, JSON.stringify({ path: v.path, name: v.name, duration: v.duration }));
                }}
              >
                <Film className="h-3.5 w-3.5 flex-shrink-0 text-slate-400 group-hover:text-[#25F4EE]" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-slate-200">{v.name}</span>
                <Plus className="h-3.5 w-3.5 flex-shrink-0 text-slate-500 group-hover:text-[#25F4EE]" />
              </Row>
            ))}
            {filtered.videos.length === 0 && (
              <p className="px-1 py-3 text-[10px] text-slate-500">
                ไม่มีคลิปที่ตรงกับคำค้น — อัปโหลดคลิปได้ที่แท็บ 1-Click Studio
              </p>
            )}
          </>
        )}

        {/* TAB 2: AI AUTO-SRT SUBTITLES (Consolidated) */}
        {tab === 'srt' && (
          <div className="space-y-3 text-left">
            <div className="p-2.5 rounded-xl bg-gradient-to-r from-[#25F4EE]/10 to-blue-500/10 border border-[#25F4EE]/20 space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#25F4EE] font-kanit">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Auto-SRT (ถอดซับแม่นยำ)</span>
              </div>
              <p className="text-[10px] text-slate-300 leading-tight">
                ถอดเสียงอัตโนมัติด้วย Whisper + PyThaiNLP แล้วนำเข้าเป็นท่อนคำบรรยายบนไทม์ไลน์ทันที
              </p>
            </div>

            {/* Select Media */}
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-300">เลือกคลิปหรือเสียง:</label>
              <select
                value={selectedMediaForSrt}
                onChange={(e) => setSelectedMediaForSrt(e.target.value)}
                className="w-full py-1.5 px-2 rounded-xl bg-black/60 border border-white/[0.1] text-white text-[11px] focus:outline-none focus:border-[#25F4EE]"
              >
                {videos.map((v) => (
                  <option key={v.path} value={v.path} className="bg-[#080B11]">
                    {v.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Subtitle Mode */}
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-300">รูปแบบภาษา:</label>
              <select
                value={srtMode}
                onChange={(e) => setSrtMode(e.target.value)}
                className="w-full py-1.5 px-2 rounded-xl bg-black/60 border border-white/[0.1] text-white text-[11px] focus:outline-none focus:border-[#25F4EE]"
              >
                <option value="bilingual" className="bg-[#080B11]">2 ภาษา (ไทย + แปลอังกฤษ)</option>
                <option value="mono" className="bg-[#080B11]">ภาษาไทยล้วน</option>
                <option value="dual" className="bg-[#080B11]">Dual Original</option>
              </select>
            </div>

            {/* Subtitle Density */}
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-300">ความยาวประโยค:</label>
              <div className="grid grid-cols-3 gap-1">
                {[
                  { count: 4, label: '4 คำ' },
                  { count: 5, label: '5-6 คำ' },
                  { count: 7, label: '7-8 คำ' },
                ].map((d) => (
                  <button
                    key={d.count}
                    type="button"
                    onClick={() => setSrtDensity(d.count)}
                    className={`py-1 rounded-lg text-[10px] font-bold border transition-colors ${
                      srtDensity === d.count
                        ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                        : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Transcribe Action Button */}
            <button
              type="button"
              onClick={handleTranscribe}
              disabled={transcribing}
              className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-md cursor-pointer transition-all disabled:opacity-50"
            >
              {transcribing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>กำลังถอดเสียง AI...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>เริ่มถอดซับอัตโนมัติ</span>
                </>
              )}
            </button>

            {transcribeError && (
              <p className="text-[10px] text-rose-400 bg-rose-500/10 p-2 rounded-xl border border-rose-500/20">
                {transcribeError}
              </p>
            )}

            {/* Transcribe Results & Import Button */}
            {transcribeResult && (
              <div className="p-2.5 rounded-xl bg-black/60 border border-[#25F4EE]/30 space-y-2 animate-fadeIn">
                <div className="flex items-center justify-between text-[11px] font-bold text-[#25F4EE]">
                  <span>ถอดเสียงสำเร็จ</span>
                  <button
                    type="button"
                    onClick={handleCopySrt}
                    className="text-[10px] text-slate-300 hover:text-white flex items-center gap-1 cursor-pointer"
                  >
                    {copiedSrt ? <><Check className="w-3 h-3 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3 h-3" /> คัดลอก .SRT</>}
                  </button>
                </div>

                <div className="max-h-28 overflow-y-auto p-1.5 rounded-lg bg-black/40 border border-white/[0.04] text-[10px] font-mono text-slate-300 space-y-1 select-all">
                  {transcribeResult.content || 'ไม่มีข้อความ'}
                </div>

                {/* Import to Timeline Button */}
                <button
                  type="button"
                  onClick={handleImportToTimeline}
                  className="w-full py-1.5 px-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-[11px] font-bold flex items-center justify-center gap-1.5 shadow-md cursor-pointer transition-all"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>นำเข้าสู่ไทม์ไลน์ (Import to Timeline)</span>
                </button>

                {importedSuccess && (
                  <p className="text-[10px] text-emerald-400 text-center font-bold">
                    ✓ นำเข้าคำบรรยายลงไทม์ไลน์เรียบร้อยแล้ว
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: AUDIO */}
        {tab === 'audio' && (
          <>
            <p className="px-1 pt-1 text-[9px] font-semibold uppercase tracking-wide text-slate-400">
              เพลงประกอบ (ทั้งคลิป)
            </p>

            <div className="mb-1 space-y-1.5 rounded-lg border border-white/[0.08] bg-black/40 px-2 py-2">
              <label className="block">
                <span className="mb-1 flex justify-between text-[10px] text-slate-400">
                  <span>ระดับเสียงเพลง</span>
                  <span className="font-mono text-slate-300">{Math.round((style.bgmVolume ?? 0.12) * 100)}%</span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={style.bgmVolume ?? 0.12}
                  onChange={(e) => onStyleChange({ bgmVolume: parseFloat(e.target.value) })}
                  className="w-full accent-[#D97757]"
                />
              </label>
              <button
                type="button"
                onClick={() => onStyleChange({ bgmDucking: !style.bgmDucking })}
                aria-pressed={!!style.bgmDucking}
                className={`w-full rounded-lg border py-1.5 text-[11px] font-bold transition-colors duration-150 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
                  style.bgmDucking
                    ? 'border-[#D97757] bg-[#D97757]/20 text-[#E89274]'
                    : 'border-white/[0.08] bg-black/40 text-slate-300 hover:text-white'
                }`}
              >
                {style.bgmDucking ? '✓ ลดเพลงตอนพูดอยู่' : 'ลดเพลงตอนพูด (auto-duck)'}
              </button>
              <p className="text-[9px] leading-relaxed text-slate-500">
                เปิดแล้วเพลงจะเบาลง ~9 dB ระหว่างมีเสียงพูด แล้วดังกลับตอนเว้นวรรค · เปลี่ยนค่าพวกนี้ต้องมิกซ์เสียงใหม่ Apply จะช้ากว่าปกติเล็กน้อย
              </p>
            </div>
            <Row active={!style.bgmName} onClick={() => onStyleChange({ bgmName: null })}>
              <Music className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
              <span className="min-w-0 flex-1 truncate text-[11px] text-slate-200">เสียงหลักของช่อง</span>
              {!style.bgmName && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
            </Row>
            {filtered.music.map((m) => (
              <Row
                key={m.id}
                active={style.bgmName === m.id}
                onClick={() => onStyleChange({ bgmName: m.id })}
                title={m.name}
              >
                <Music className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-slate-200">{m.label_th || m.name}</span>
                {style.bgmName === m.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
              </Row>
            ))}

            <p className="px-1 pt-3 text-[9px] font-semibold uppercase tracking-wide text-slate-400">
              เสียงเอฟเฟกต์ {selectedCaption ? '(ใส่ให้ท่อนที่เลือก)' : '(เลือกท่อนคำบรรยายก่อน)'}
            </p>
            {filtered.sfx.map((s) => (
              <Row
                key={s.id}
                active={selectedCaption?.sfx === s.id}
                onClick={() => selectedCaption && onAssignSfx(s.id)}
                title={selectedCaption ? `ใส่ ${s.name}` : 'เลือกท่อนคำบรรยายบนไทม์ไลน์ก่อน'}
              >
                <Volume2 className={`h-3.5 w-3.5 flex-shrink-0 ${selectedCaption ? 'text-slate-400' : 'text-slate-600'}`} />
                <span className={`min-w-0 flex-1 truncate text-[11px] ${selectedCaption ? 'text-slate-200' : 'text-slate-500'}`}>
                  {s.label_th || s.name}
                </span>
                {selectedCaption?.sfx === s.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
              </Row>
            ))}
          </>
        )}

        {/* TAB 4: TEXT / FONTS */}
        {tab === 'text' && (
          <>
            <style>{filtered.fonts
              .filter((f) => f.file)
              .map((f) => `@font-face{font-family:'ed-${f.id}';src:url('/api/media/${f.file.rel_path}') format('${(f.file.name || '').toLowerCase().endsWith('.otf') ? 'opentype' : 'truetype'}');font-display:swap;}`)
              .join(' ')}</style>

            <p className="px-1 pt-1 text-[9px] font-semibold uppercase tracking-wide text-[#9C968F]">
              ฟอนต์คำบรรยาย
            </p>
            {filtered.fonts.map((f) => (
              <Row key={f.id} active={style.fontName === f.id} onClick={() => onStyleChange({ fontName: f.id })}>
                <Type className="h-3.5 w-3.5 flex-shrink-0 text-[#9C968F]" />
                <span
                  className="min-w-0 flex-1 truncate text-[12px] text-[#EDE9E3]"
                  style={f.file ? { fontFamily: `'ed-${f.id}', sans-serif` } : undefined}
                >
                  {f.name} · ก ข ค
                </span>
                {style.fontName === f.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#D97757]" />}
              </Row>
            ))}
            {filtered.fonts.length === 0 && (
              <p className="px-1 py-2 text-[10px] text-[#6B6660]">ไม่พบฟอนต์ที่ค้นหา</p>
            )}
            <p className="px-1 pt-3 text-[10px] leading-relaxed text-[#6B6660]">
              แก้ข้อความแต่ละท่อนได้ที่แผงขวา — คลิกท่อนคำบรรยายบนไทม์ไลน์
            </p>
          </>
        )}

        {/* TAB 5: STICKERS */}
        {tab === 'sticker' && (
          <>
            <Row active={!style.stickerBadge} onClick={() => onStyleChange({ stickerBadge: '' })}>
              <Sticker className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
              <span className="min-w-0 flex-1 truncate text-[11px] text-slate-200">ไม่ใส่ป้าย</span>
              {!style.stickerBadge && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
            </Row>
            {filtered.stickers.map((s) => (
              <Row
                key={s.id}
                active={style.stickerBadge === s.name}
                onClick={() => onStyleChange({ stickerBadge: s.name })}
                title={s.name}
              >
                <img src={s.img_url} alt="" className="h-6 w-6 flex-shrink-0 rounded object-contain" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-slate-200">{s.name.replace(/\.(png|webp|jpg)$/i, '')}</span>
                {style.stickerBadge === s.name && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
              </Row>
            ))}
            <p className="px-1 pt-2 text-[10px] leading-relaxed text-slate-500">
              ป้ายวางมุมขวาบนตลอดคลิป — สามารถเปลี่ยนแบบป้ายได้ตามธีม
            </p>
          </>
        )}

        {/* TAB 6: LUTS / FILTERS */}
        {tab === 'filter' && (
          <>
            <Row active={!style.lutName} onClick={() => onStyleChange({ lutName: null })}>
              <Palette className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
              <span className="min-w-0 flex-1 truncate text-[11px] text-slate-200">ไม่ใช้ (เร็วกว่า)</span>
              {!style.lutName && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
            </Row>
            {filtered.luts.map((l) => (
              <Row
                key={l.id}
                active={style.lutName === l.id}
                onClick={() => onStyleChange({ lutName: l.id })}
                title={l.name}
              >
                <Palette className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-slate-200">
                  {l.name.replace(/\.cube$/i, '')}
                </span>
                {style.lutName === l.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
              </Row>
            ))}
            {style.lutName && (
              <label className="block px-1 pt-2">
                <span className="mb-1 flex justify-between text-[10px] text-slate-400">
                  <span>ความเข้มฟิลเตอร์</span>
                  <span className="font-mono text-slate-300">{Math.round((style.lutIntensity ?? 1) * 100)}%</span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={style.lutIntensity ?? 1}
                  onChange={(e) => onStyleChange({ lutIntensity: parseFloat(e.target.value) })}
                  className="w-full accent-[#D97757]"
                />
                <span className="block pt-1 text-[9px] leading-relaxed text-slate-500">
                  พรีวิวไม่แสดงฟิลเตอร์ — เห็นผลจริงหลังกด Apply
                </span>
              </label>
            )}
          </>
        )}
      </div>
    </div>
  );
}
