import React, { useEffect, useState } from 'react';
import { useThemeSettings } from '../../context/ThemeContext.jsx';
import { UI_THEME_PRESETS, UI_THEME_CONTROL_RANGES, createDefaultThemePreferences } from '../../lib/themeCatalog.js';
import { getPresetDefinition, normalizeThemePreferences, updatePresetOverrides, resolveTheme, createCustomPreset, deleteCustomPreset } from '../../lib/themeResolver.js';
import ThemePreview from './ThemePreview.jsx';

const ACCENTS = ['#67d7e7', '#a5b4fc', '#86efac', '#fcd34d', '#fda4af'];
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const controlClass = ' rounded-lg border px-3 py-2 text-xs';

export default function AppearanceSettings() {
  const { preferences, readOnly, status, revision, applyPreferences } = useThemeSettings();
  const [baseline, setBaseline] = useState(preferences);
  const [draft, setDraft] = useState(preferences);
  const [baseRevision, setBaseRevision] = useState(revision);
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [conflict, setConflict] = useState(false);
  const dirty = !same(draft, baseline);

  useEffect(() => {
    if (revision === baseRevision) return;
    if (dirty) { setConflict(true); return; }
    setBaseline(preferences); setDraft(preferences); setBaseRevision(revision); setConflict(false);
  }, [preferences, revision, baseRevision, dirty]);

  const definition = getPresetDefinition(draft, draft.activePresetId);
  const custom = draft.customPresets.find(item => item.id === draft.activePresetId);
  const controls = { ...definition.defaults, ...custom?.overrides, ...draft.overridesByPreset[draft.activePresetId] };
  const resolved = resolveTheme(draft);
  const settingsSurface = resolveTheme({ ...baseline, activePresetId: 'balanced-glass' });
  const patch = (key, value) => {
    setDraft(current => {
      if (value !== undefined) return updatePresetOverrides(current, current.activePresetId, { [key]: value });
      const overrides = { ...current.overridesByPreset[current.activePresetId] }; delete overrides[key];
      return normalizeThemePreferences({ ...current, overridesByPreset: { ...current.overridesByPreset, [current.activePresetId]: overrides } });
    });
    setMessage('');
  };
  const loadApplied = () => {
    setBaseline(preferences); setDraft(preferences); setBaseRevision(revision);
    setConflict(false); setMessage('โหลดค่าที่ใช้จริงแล้ว');
  };
  const apply = () => {
    const result = applyPreferences(draft, { expectedRevision: baseRevision });
    if (result.conflict) { setConflict(true); setMessage('ค่าถูกเปลี่ยนจากอีกแท็บ กรุณาเลือกโหลดใหม่หรือยืนยันใช้ค่าร่าง'); return; }
    if (!result.ok) { setMessage(result.error || 'ใช้ธีมไม่ได้ กรุณาลองใหม่'); return; }
    setBaseline(result.preferences || draft); setDraft(result.preferences || draft);
    setConflict(false); setMessage('ใช้ค่าร่างแล้ว ตรวจสถานะการบันทึกด้านล่าง');
  };
  const resetPreset = () => {
    const next = { ...draft.overridesByPreset }; delete next[draft.activePresetId];
    setDraft(normalizeThemePreferences({ ...draft, overridesByPreset: next }));
    setMessage('คืนค่าเริ่มต้นในร่างแล้ว กดใช้ธีมเพื่อยืนยัน');
  };
  const saveCopy = () => {
    if (!name.trim()) { setMessage('ตั้งชื่อธีมส่วนตัวก่อนบันทึก'); return; }
    if (draft.customPresets.length >= 12) { setMessage('เก็บธีมส่วนตัวได้สูงสุด 12 ชุด ลบชุดที่ไม่ใช้ก่อน'); return; }
    const id = `custom-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
    setDraft(createCustomPreset(draft, { id, name: name.trim() }));
    setName(''); setMessage('เพิ่มสำเนาในร่างแล้ว กดใช้ธีมเพื่อบันทึก');
  };

  return (
    <section data-ui-theme="balanced" data-ui-effects={settingsSurface.effects} data-oc-surface="data" className="rounded-2xl p-4 sm:p-5 space-y-4" aria-label="ปรับแต่งธีม" style={{ ...settingsSurface.variables, color: 'var(--oc-ui-text-primary)' }}>
      <div>
        <h3 className="text-sm sm:text-base font-bold">ชุดธีมสีของระบบ (UI Theme Presets)</h3>
        <p data-oc-field-label className="text-xs mt-1">ปรับในตัวอย่างก่อน กดใช้ธีมเพื่อเปลี่ยนทั้งโปรแกรม</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" aria-label="เลือกชุดธีม">
        {[...UI_THEME_PRESETS, ...draft.customPresets].map(preset => (
          <button data-oc-button="secondary" key={preset.id} type="button" aria-pressed={draft.activePresetId === preset.id}
            onClick={() => { setDraft(current => normalizeThemePreferences({ ...current, activePresetId: preset.id })); setMessage(''); }}
            className={`rounded-xl border p-4 text-left text-xs ${draft.activePresetId === preset.id ? 'oc-ui-nav-active' : ''}`}>
            <span className="block font-bold">{preset.name}</span>
            <span data-oc-field-label className="block mt-2">{preset.description || 'ธีมส่วนตัวจาก Balanced Glass Workspace'}</span>
          </button>
        ))}
      </div>
      <ThemePreview preferences={draft} />
      {resolved.accentAdjusted && <p data-oc-field-label className="text-xs" role="status">สีที่เลือกมี contrast ต่ำ ใช้สีหลักสำรองในตัวอย่างและหน้าจอจริงเพื่อให้อ่านได้</p>}
      {definition.supportsGlass ? <>
        <fieldset className="space-y-3">
          <legend className="text-sm font-bold mb-2">ปรับทั่วไป</legend>
          <div className="flex flex-wrap gap-2" aria-label="เลือกสีหลัก">
            {ACCENTS.map(accent => <button data-oc-button="secondary" key={accent} type="button" className={`${controlClass} ${controls.accent === accent ? 'oc-ui-nav-active' : ''}`}
              aria-pressed={controls.accent === accent} onClick={() => patch('accent', accent)}>
              <span aria-hidden="true" className="inline-block w-3 h-3 rounded-full mr-2" style={{ background: accent }} />{accent}
            </button>)}
          </div>
          <ThemeRange name="shellTransparency" value={controls.shellTransparency} onChange={patch} />
          <label className="block text-xs">แสงพื้นหลัง
            <select data-oc-surface="control" data-oc-field="input" className={`${controlClass} block mt-2 w-full`} value={controls.ambientStrength === 0 ? '0' : controls.ambientStrength <= 14 ? '14' : '24'}
              onChange={event => patch('ambientStrength', Number(event.target.value))}>
              <option value="0">ปิด</option><option value="14">เบา</option><option value="24">ปกติ</option>
            </select>
          </label>
          <label className="block text-xs">เอฟเฟกต์
            <select data-oc-surface="control" data-oc-field="input" className={`${controlClass} block mt-2 w-full`} value={draft.effects}
              onChange={event => setDraft(current => ({ ...current, effects: event.target.value }))}>
              <option value="full">เต็ม</option><option value="light">เบา — ลด blur และปิดแสงพื้นหลัง</option><option value="off">ปิด — ใช้พื้นผิวทึบ</option>
            </select>
          </label>
          <p data-oc-field-label className="text-xs" role="status">{resolved.ambientEnabled ? 'แสดงแสงพื้นหลังตามระดับที่เลือก' : 'แสงพื้นหลังปิดอยู่'} · {draft.effects === 'off' ? 'ใช้พื้นผิวทึบ ปิดเอฟเฟกต์' : draft.effects === 'light' ? 'ลดความเบลอและปิดแสงพื้นหลัง' : 'ใช้เอฟเฟกต์เต็มเมื่อเบราว์เซอร์รองรับ'}</p>
        </fieldset>
        <details className="border-t pt-3">
          <summary className="cursor-pointer text-sm font-bold">ปรับขั้นสูง</summary>
          <div className="space-y-4 mt-4">
            <label className="block text-xs">สีหลักแบบกำหนดเอง
              <input type="color" data-oc-surface="control" className="block mt-2 h-9 w-16" value={controls.accent} onChange={event => patch('accent', event.target.value)} />
            </label>
            {['blurPx', 'backgroundStrength', 'rimStrength', 'shadowStrength', 'saturationPct'].map(key =>
              <ThemeRange key={key} name={key} value={controls[key]} onChange={patch} disabled={draft.effects === 'off' && key === 'blurPx'} />)}
            <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={draft.ambientMotion}
              disabled={draft.effects !== 'full'} onChange={event => setDraft(current => ({ ...current, ambientMotion: event.target.checked }))} />เคลื่อนไหวแสงพื้นหลัง (เคารพการลดการเคลื่อนไหวของระบบ)</label>
          </div>
        </details>
        <div className="space-y-2 border-t pt-3">
          <label className="block text-xs" htmlFor="personal-theme-name">ชื่อธีมส่วนตัว</label>
          <div className="flex flex-wrap gap-2">
            <input id="personal-theme-name" data-oc-field="input" data-oc-surface="control" className={`${controlClass} min-w-0 flex-1`} maxLength={48} value={name} onChange={event => setName(event.target.value)} />
            <button data-oc-button="secondary" type="button" className={controlClass} onClick={saveCopy}>เพิ่มสำเนาธีม</button>
            {custom && <button data-oc-button="secondary" type="button" className={controlClass} onClick={() => { setDraft(deleteCustomPreset(draft, custom.id)); setMessage('ลบออกจากร่างแล้ว กดใช้ธีมเพื่อบันทึก'); }}>ลบธีมส่วนตัว</button>}
          </div>
          <p data-oc-field-label className="text-xs">บันทึกได้สูงสุด 12 ชุด ธีมมาตรฐานจะไม่ถูกเขียนทับ</p>
        </div>
      </> : <p data-oc-field-label className="text-xs">ธีมเดิมใช้ลักษณะพื้นผิวเดิม เลือก Balanced Glass Workspace เพื่อปรับแต่งกระจกแบบใหม่</p>}
      {conflict && <div data-oc-surface="data" className="rounded-xl p-3 space-y-2" role="alert">
        <p className="text-xs">ค่าที่ใช้จริงเปลี่ยนแล้ว ร่างของคุณยังอยู่ เลือกโหลดค่าล่าสุดหรือยืนยันใช้ร่างแทน</p>
        <div className="flex flex-wrap gap-2">
          <button data-oc-button="secondary" type="button" className={controlClass} onClick={loadApplied}>โหลดค่าล่าสุด</button>
          <button data-oc-button="secondary" type="button" className={controlClass} onClick={() => { setBaseRevision(revision); setConflict(false); setMessage('ตรวจร่างแล้วกดใช้ธีมอีกครั้งเพื่อยืนยัน'); }}>เก็บร่างและยืนยันใช้แทน</button>
        </div>
      </div>}
      {readOnly && <p className="text-xs" role="alert">พบข้อมูลธีมจากเวอร์ชันใหม่กว่า ปิดการบันทึกเพื่อรักษาข้อมูลเดิม</p>}
      <div className="flex flex-wrap gap-2 border-t pt-3">
        <button data-oc-button="primary" type="button" className={controlClass} disabled={readOnly || !dirty || conflict} onClick={apply}>ใช้ธีม</button>
        <button data-oc-button="secondary" type="button" className={controlClass} disabled={!dirty && !conflict} onClick={loadApplied}>ยกเลิกการปรับ</button>
        <button data-oc-button="secondary" type="button" className={controlClass} onClick={resetPreset}>คืนค่าเริ่มต้นของชุดธีม</button>
        <button data-oc-button="secondary" type="button" className={controlClass} onClick={() => { setDraft(createDefaultThemePreferences()); setMessage('คืนค่าทั้งหมดในร่างแล้ว รวมถึงรายการธีมส่วนตัว กดใช้ธีมเพื่อยืนยัน'); }}>คืนค่าทั้งหมดในร่าง</button>
      </div>
      <p data-oc-field-label className="text-xs" aria-live="polite">{message || (dirty ? 'มีค่าร่างที่ยังไม่ได้ใช้' : status?.message || 'กำลังใช้ค่าที่บันทึกไว้')}</p>
      {message && status?.message && <p data-oc-field-label className="text-xs" role="status">{status.message}</p>}
    </section>
  );
}

function ThemeRange({ name, value, onChange, disabled = false }) {
  const range = UI_THEME_CONTROL_RANGES[name];
  return <div>
    <label className="block text-xs" htmlFor={`theme-${name}`}>{range.label} <output htmlFor={`theme-${name}`}>{value}{name === 'blurPx' ? 'px' : ''}</output></label>
    <div className="flex items-center gap-3 mt-2">
      <input id={`theme-${name}`} className="flex-1 min-w-0" type="range" min={range.min} max={range.max} step={range.step} value={value} disabled={disabled}
        onChange={event => onChange(name, Number(event.target.value))} />
      <button data-oc-button="secondary" type="button" className={controlClass} disabled={disabled} onClick={() => onChange(name, undefined)}>คืนค่า</button>
    </div>
    {disabled && <p data-oc-field-label className="text-xs mt-1">ปิดความเบลออยู่ในโหมดลดเอฟเฟกต์</p>}
  </div>;
}
