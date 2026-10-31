import React from 'react';
import { resolveTheme } from '../../lib/themeResolver.js';
import { Button } from '../ui/Button.jsx';
import { Input } from '../ui/Input.jsx';

export default function ThemePreview({ preferences }) {
  const reducedMotion = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const backdropSupported = typeof CSS !== 'undefined' && (CSS.supports('backdrop-filter', 'blur(1px)') || CSS.supports('-webkit-backdrop-filter', 'blur(1px)'));
  const resolved = resolveTheme(preferences, { reducedMotion, backdropSupported });
  if (resolved.isLegacy) return <p className="text-xs text-slate-400">ชุดธีมเดิมแสดงผลผ่านระบบเดิม กดใช้ธีมเพื่อดูหน้าจอจริง ตัวอย่างกระจกแบบใหม่จะแสดงเมื่อเลือก Balanced Glass Workspace</p>;
  return (
    <div role="region" aria-label="ตัวอย่างธีมที่ยังไม่ได้ใช้" data-ui-theme="balanced"
      data-ui-effects={resolved.effects}
      style={{ ...resolved.variables, color: 'var(--oc-ui-text-primary)', background: 'var(--oc-ui-bg-canvas)' }}
      className="relative isolate rounded-xl border overflow-hidden">
      <div aria-hidden="true" className="oc-ui-ambient oc-ui-ambient-cyan absolute -top-24 -left-20 w-80 h-80" />
      <div aria-hidden="true" className="oc-ui-ambient oc-ui-ambient-indigo absolute top-0 right-0 w-80 h-80" />
      <div data-oc-surface="shell" className="relative p-3 border-b flex items-center justify-between gap-3">
        <span className="text-xs font-bold">OmniCut Studio</span>
        <span className="text-xs" style={{ color: 'var(--oc-ui-text-secondary)' }}>ตัวอย่างธีม</span>
      </div>
      <div className="relative grid grid-cols-1 sm:grid-cols-[140px_1fr]">
        <nav data-oc-surface="shell" className="p-3 space-y-2" aria-label="ตัวอย่างเมนู">
          <button type="button" className="oc-ui-nav-item oc-ui-nav-active w-full rounded-lg p-2 text-left text-xs" aria-current="page">คลังผลงาน</button>
          <button type="button" className="oc-ui-nav-item w-full rounded-lg p-2 text-left text-xs">ตั้งค่าโปรแกรม</button>
        </nav>
        <div data-oc-surface="workspace" className="p-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            <Button size="sm">สร้างโปรเจกต์</Button>
            <Button size="sm" variant="secondary">ดูรายละเอียด</Button>
          </div>
          <Input id="theme-preview-search" aria-label="ตัวอย่างช่องค้นหา" placeholder="ค้นหาโปรเจกต์" />
          <div data-oc-surface="data" className="rounded-lg border p-3 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-bold">ตัวอย่างโปรเจกต์</span>
              <span className="rounded-full px-2 py-1 text-xs" style={{ color: 'var(--oc-ui-success)', background: 'var(--oc-ui-bg-workspace)' }}>พร้อมใช้งาน</span>
            </div>
            <table className="w-full text-xs"><caption className="sr-only">ตัวอย่างข้อมูลในตาราง</caption>
              <thead><tr><th className="text-left pb-2">ชื่อโปรเจกต์</th><th className="text-right pb-2">ประเภท</th></tr></thead>
              <tbody><tr className="border-t"><td className="pt-2">Product Review</td><td className="text-right pt-2" style={{ color: 'var(--oc-ui-text-secondary)' }}>วิดีโอ</td></tr></tbody>
            </table>
          </div>
          <div data-oc-surface="floating" className="rounded-lg border p-2" aria-label="ตัวอย่างเมนูลอย">
            <button type="button" className="oc-ui-nav-item w-full p-2 rounded-lg text-left text-xs">เปิดโปรเจกต์</button>
            <button type="button" className="oc-ui-nav-item w-full p-2 rounded-lg text-left text-xs">สร้างสำเนา</button>
          </div>
        </div>
      </div>
    </div>
  );
}
