import test from 'node:test';
import assert from 'node:assert/strict';

import { buildProjectName } from './projectName.js';

test('buildProjectName prepends productCode when present', () => {
  const name = buildProjectName({
    productName: 'ESSAGER สายชาร์จแม่เหล็ก',
    angle: { angle_id: 'pain_point' },
    angleIndex: 0,
    existingProjects: [],
    productCode: 'ESG01',
  });
  assert.equal(name, 'ESG01-ปัญหาก่อนใช้_1');
});

test('buildProjectName falls back to shortProduct_angleSlug when no productCode', () => {
  const name = buildProjectName({
    productName: 'ESSAGER สายชาร์จแม่เหล็ก',
    angle: { angle_id: 'pain_point' },
    angleIndex: 0,
    existingProjects: [],
  });
  assert.equal(name, 'essager_สายชาร์จแม่เหล็ก_ปัญหาก่อนใช้_1');
});

test('buildProjectName increments version on collision with a code-based base', () => {
  const name = buildProjectName({
    productName: 'ESSAGER สายชาร์จแม่เหล็ก',
    angle: { angle_id: 'pain_point' },
    angleIndex: 0,
    existingProjects: ['ESG01-ปัญหาก่อนใช้_1', 'ESG01-ปัญหาก่อนใช้_2'],
    productCode: 'ESG01',
  });
  assert.equal(name, 'ESG01-ปัญหาก่อนใช้_3');
});
