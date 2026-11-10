import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const systemSettingsPath = path.resolve(__dirname, '../components/SystemSettings.jsx');
const channelSettingsPath = path.resolve(__dirname, '../components/ChannelSettings.jsx');
const loginScreenPath = path.resolve(__dirname, '../components/LoginScreen.jsx');
const agentDockPath = path.resolve(__dirname, '../components/agent/OmniCutAgentDock.jsx');

test('SystemSettings and ChannelSettings adhere to Obsidian Pro Dark tokens without visual slop', () => {
  const sysSource = fs.readFileSync(systemSettingsPath, 'utf8');
  const chanSource = fs.readFileSync(channelSettingsPath, 'utf8');

  // Obsidian Pro Dark tokens
  assert.match(sysSource, /border-white\/\[0\.08\]/);
  assert.match(chanSource, /border-white\/\[0\.08\]/);

  // Slop gradient removed from theme and font selector
  assert.doesNotMatch(sysSource, /bg-gradient-to-br from-cyan-500\/10 to-pink-500\/10/);
  assert.doesNotMatch(sysSource, /bg-gradient-to-tr from-\[#FE2C55\] to-\[#25F4EE\]/);

  // Functional inputs and accents
  assert.match(sysSource, /#25F4EE/);
  assert.match(chanSource, /#25F4EE/);
});

test('LoginScreen adheres to Obsidian Dark and clean typography', () => {
  const loginSource = fs.readFileSync(loginScreenPath, 'utf8');

  // Obsidian Dark tokens
  assert.match(loginSource, /border-white\/\[0\.08\]/);

  // Clean studio background
  assert.match(loginSource, /#0A0D14/);
});

test('OmniCutAgentDock adheres to Obsidian Pro Dark dock chrome', () => {
  const dockSource = fs.readFileSync(agentDockPath, 'utf8');

  // Obsidian Pro Dark tokens
  assert.match(dockSource, /border-white\/\[0\.08\]/);
  assert.match(dockSource, /#0A0D14/);
});

