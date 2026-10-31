import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import react from '@vitejs/plugin-react';

let server, ThemeProvider, useThemeSettings, AppearanceSettings, Input;
before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL('../..', import.meta.url)), configFile: false,
    plugins: [react()], logLevel: 'silent',
    server: { middlewareMode: true, hmr: false, watch: null },
  });
  ({ ThemeProvider, useThemeSettings } = await server.ssrLoadModule('/src/context/ThemeContext.jsx'));
  ({ default: AppearanceSettings } = await server.ssrLoadModule('/src/components/settings/AppearanceSettings.jsx'));
  ({ Input } = await server.ssrLoadModule('/src/components/ui/Input.jsx'));
});
after(async () => { await server?.close(); delete globalThis.localStorage; });

test('the flag-off React provider never reads or writes theme storage', () => {
  globalThis.localStorage = { getItem() { assert.fail('flag-off read'); }, setItem() { assert.fail('flag-off write'); } };
  function Probe() { const settings = useThemeSettings(); return React.createElement('span', null, String(settings.enabled)); }
  assert.equal(renderToStaticMarkup(React.createElement(ThemeProvider, { enabled: false }, React.createElement(Probe))), '<span>false</span>');
});

test('opt-in React settings render a scoped draft without persisting or switching the migrated legacy theme', () => {
  const data = { omnicut_ui_theme: 'obsidian', omnicut_ambient_orbs_enabled: 'false' };
  globalThis.localStorage = { getItem: key => data[key] ?? null, setItem() { assert.fail('render must not persist'); } };
  const html = renderToStaticMarkup(React.createElement(ThemeProvider, { enabled: true }, React.createElement(AppearanceSettings)));
  assert.match(html, /Balanced Glass Workspace/);
  assert.match(html, /data-ui-theme="balanced"/);
  assert.match(html, /aria-pressed="true"[^>]*>[\s\S]*?Obsidian Pro Dark/);
  assert.match(html, /ใช้ธีม/);
  assert.equal(data.omnicut_ui_theme, 'obsidian');
  assert.equal(Object.hasOwn(data, 'omnicut_ui_preferences_v2'), false);
});

test('shared fields associate labels with both generated and caller-specified ids', () => {
  const html = renderToStaticMarkup(React.createElement('div', null,
    React.createElement(Input, { label: 'ค้นหา' }), React.createElement(Input, { label: 'ชื่อ', id: 'provided-name' }),
  ));
  const generated = html.match(/<label[^>]*for="([^"]+)"/)[1];
  assert.ok(html.includes(`id="${generated}"`));
  assert.ok(html.includes('for="provided-name"'));
  assert.ok(html.includes('id="provided-name"'));
});
