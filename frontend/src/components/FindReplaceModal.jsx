import React, { useState, useMemo } from 'react';
import { Replace, Check, X, ArrowRight, Sparkles, AlertCircle } from 'lucide-react';
import { Modal } from './ui';

export default function FindReplaceModal({
  isOpen,
  onClose,
  angles = [],
  currentAngleIndex = 0,
  onApplyReplace
}) {
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [scope, setScope] = useState('all'); // 'all' | 'current'
  const [matchCase, setMatchCase] = useState(false);

  // Quick Preset Chips for common Thai copywriting & brand corrections
  const presets = [
    { label: 'ค่ะ ➔ ครับ', find: 'ค่ะ', replace: 'ครับ' },
    { label: 'ครับ ➔ ค่ะ', find: 'ครับ', replace: 'ค่ะ' },
    { label: 'นะคะ ➔ นะครับ', find: 'นะคะ', replace: 'นะครับ' },
    { label: 'นะครับ ➔ นะคะ', find: 'นะครับ', replace: 'นะคะ' },
    { label: 'คีย์ส ➔ คีย์', find: 'คีย์ส', replace: 'คีย์' },
    { label: 'โลจิเทค ➔ Logitech', find: 'โลจิเทค', replace: 'Logitech' },
    { label: 'ยูเอสบีซี ➔ USB-C', find: 'ยูเอสบีซี', replace: 'USB-C' },
    { label: 'บลูทูธ ➔ Bluetooth', find: 'บลูทูธ', replace: 'Bluetooth' },
  ];

  const handleApplyPreset = (p) => {
    setFindText(p.find);
    setReplaceText(p.replace);
  };

  // Calculate live matches across angles
  const { totalMatches, affectedAngles, previewItems } = useMemo(() => {
    if (!findText || !findText.trim()) {
      return { totalMatches: 0, affectedAngles: [], previewItems: [] };
    }

    const query = findText;
    const isCurrentOnly = scope === 'current';
    let count = 0;
    const affected = [];
    const previews = [];

    angles.forEach((ang, aIdx) => {
      if (isCurrentOnly && aIdx !== currentAngleIndex) return;

      const lines = Array.isArray(ang.script_lines)
        ? ang.script_lines
        : (ang.script_text ? ang.script_text.split('\n') : []);

      let angleMatchCount = 0;

      lines.forEach((line, lIdx) => {
        if (!line) return;
        let occurrences = 0;

        if (matchCase) {
          occurrences = line.split(query).length - 1;
        } else {
          const regex = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
          const matches = line.match(regex);
          occurrences = matches ? matches.length : 0;
        }

        if (occurrences > 0) {
          count += occurrences;
          angleMatchCount += occurrences;

          // Generate highlighted preview line
          let replacedLine = '';
          if (matchCase) {
            replacedLine = line.replaceAll(query, replaceText);
          } else {
            const regex = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
            replacedLine = line.replace(regex, replaceText);
          }

          if (previews.length < 8) {
            previews.push({
              angleIndex: aIdx,
              angleName: ang.angle_name || `มุมที่ ${aIdx + 1}`,
              lineIndex: lIdx + 1,
              original: line,
              replaced: replacedLine,
            });
          }
        }
      });

      if (angleMatchCount > 0) {
        affected.push({
          angleIndex: aIdx,
          angleName: ang.angle_name || `มุมที่ ${aIdx + 1}`,
          matches: angleMatchCount,
        });
      }
    });

    return { totalMatches: count, affectedAngles: affected, previewItems: previews };
  }, [findText, replaceText, scope, matchCase, angles, currentAngleIndex]);

  const handleExecuteReplace = () => {
    if (!findText || totalMatches === 0) return;

    const isCurrentOnly = scope === 'current';
    const query = findText;

    const updatedAngles = angles.map((ang, aIdx) => {
      if (isCurrentOnly && aIdx !== currentAngleIndex) return ang;

      const lines = Array.isArray(ang.script_lines)
        ? ang.script_lines
        : (ang.script_text ? ang.script_text.split('\n') : []);

      const replaceStr = (str) => {
        if (!str || typeof str !== 'string') return str;
        if (matchCase) {
          return str.replaceAll(query, replaceText);
        } else {
          const regex = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
          return str.replace(regex, replaceText);
        }
      };

      const nextLines = lines.map(replaceStr);
      const nextScriptText = nextLines.join('\n');
      const nextTtsLines = Array.isArray(ang.tts_lines)
        ? ang.tts_lines.map(replaceStr)
        : nextLines;

      return {
        ...ang,
        script_lines: nextLines,
        script_text: nextScriptText,
        tts_lines: nextTtsLines,
        hook_title: replaceStr(ang.hook_title),
        tts_hook_title: replaceStr(ang.tts_hook_title),
      };
    });

    onApplyReplace({
      findText,
      replaceText,
      scope,
      updatedAngles,
      matchCount: totalMatches,
      affectedAnglesCount: affectedAngles.length,
    });

    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="ค้นหา & แทนที่คำในสคริปต์"
      subtitle={`แทนที่คำพร้อมกันในทุกสคริปต์ หรือเฉพาะมุมที่กำลังเลือก (${angles.length} สคริปต์)`}
      maxWidth="max-w-xl"
    >
      <div className="space-y-4">
        {/* Quick Presets */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-400">
            <Sparkles className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span>คำที่พบบ่อย (คลิกเพื่อแทนที่ทันที):</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplyPreset(p)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                  findText === p.find && replaceText === p.replace
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE]/50 text-[#25F4EE]'
                    : 'bg-white/[0.04] border-white/[0.08] hover:bg-white/[0.08] text-slate-300'
                }`}
              >
                <span>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Inputs */}
        <div className="space-y-3 p-3.5 rounded-xl bg-black/40 border border-white/[0.08]">
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300">คำที่ต้องการค้นหา:</label>
            <input
              type="text"
              value={findText}
              onChange={(e) => setFindText(e.target.value)}
              placeholder="เช่น ค่ะ, คีย์ส, โลจิเทค, ยูเอสบีซี..."
              className="w-full bg-[#080B11] border border-white/[0.12] focus:border-[#25F4EE] rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
              autoFocus
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300">แทนที่ด้วยคำว่า:</label>
            <input
              type="text"
              value={replaceText}
              onChange={(e) => setReplaceText(e.target.value)}
              placeholder="เช่น ครับ, คีย์, Logitech, USB-C... (เว้นว่างไว้เพื่อลบคำ)"
              className="w-full bg-[#080B11] border border-white/[0.12] focus:border-[#25F4EE] rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
            />
          </div>

          {/* Scope & Options */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-white/[0.06] text-xs">
            <div className="flex items-center gap-3 text-slate-300">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="replaceScope"
                  checked={scope === 'all'}
                  onChange={() => setScope('all')}
                  className="accent-[#25F4EE]"
                />
                <span>ทุกสคริปต์ ({angles.length} มุม)</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="replaceScope"
                  checked={scope === 'current'}
                  onChange={() => setScope('current')}
                  className="accent-[#25F4EE]"
                />
                <span>เฉพาะมุมที่ {currentAngleIndex + 1}</span>
              </label>
            </div>

            <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-300">
              <input
                type="checkbox"
                checked={matchCase}
                onChange={(e) => setMatchCase(e.target.checked)}
                className="accent-[#25F4EE]"
              />
              <span>ตรงตามพิมพ์เล็ก-ใหญ่</span>
            </label>
          </div>
        </div>

        {/* Live Match Summary & Preview */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-slate-400">ผลการตรวจหาในสคริปต์:</span>
            {findText.trim() ? (
              totalMatches > 0 ? (
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-bold font-mono">
                  พบ {totalMatches} จุด ใน {affectedAngles.length} สคริปต์
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 font-bold">
                  ไม่พบคำนี้ในสคริปต์
                </span>
              )
            ) : (
              <span className="text-slate-500 text-[11px]">พิมพ์คำเพื่อค้นหา</span>
            )}
          </div>

          {/* Preview Box */}
          {previewItems.length > 0 && (
            <div className="p-2.5 rounded-xl bg-black/50 border border-white/[0.08] max-h-44 overflow-y-auto space-y-2 font-mono text-[11px] leading-relaxed">
              {previewItems.map((item, pIdx) => (
                <div key={pIdx} className="space-y-0.5 border-b border-white/[0.04] pb-1.5 last:border-0 last:pb-0">
                  <div className="text-[10px] text-slate-500 font-bold truncate">
                    {item.angleName} • ท่อนที่ {item.lineIndex}
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <span className="line-through text-red-400/80 truncate">{item.original}</span>
                    <ArrowRight className="w-3 h-3 text-slate-600 flex-shrink-0" />
                    <span className="text-emerald-300 font-bold truncate">{item.replaced}</span>
                  </div>
                </div>
              ))}
              {totalMatches > previewItems.length && (
                <div className="text-center text-[10px] text-slate-500 pt-1">
                  และอีก {totalMatches - previewItems.length} จุดที่เหลือ...
                </div>
              )}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-semibold cursor-pointer flex items-center gap-1.5 transition-all"
          >
            <X className="w-3.5 h-3.5" />
            <span>ยกเลิก</span>
          </button>
          <button
            type="button"
            disabled={totalMatches === 0 || !findText.trim()}
            onClick={handleExecuteReplace}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-md ${
              totalMatches > 0 && findText.trim()
                ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white cursor-pointer active:scale-95'
                : 'bg-white/[0.05] text-slate-500 border border-white/[0.06] cursor-not-allowed'
            }`}
          >
            <Replace className="w-3.5 h-3.5" />
            <span>แทนที่ทั้งหมด ({totalMatches} จุด)</span>
          </button>
        </div>
      </div>
    </Modal>
  );
}
