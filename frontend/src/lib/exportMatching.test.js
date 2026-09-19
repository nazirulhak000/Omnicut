import test from 'node:test';
import assert from 'node:assert/strict';
import { matchExportVideo } from './exportMatching.js';

test('matchExportVideo returns false for null/empty inputs', () => {
  assert.equal(matchExportVideo(null, 'target'), false);
  assert.equal(matchExportVideo({}, null), false);
  assert.equal(matchExportVideo({ name: 'clip.mp4' }, ''), false);
});

test('matchExportVideo matches exact export_id', () => {
  const item = { export_id: 'exp_toshino_123', name: 'toshino_v1.mp4' };
  assert.equal(matchExportVideo(item, { exportId: 'exp_toshino_123' }), true);
  assert.equal(matchExportVideo(item, 'exp_toshino_123'), true);
  assert.equal(matchExportVideo(item, { exportId: 'other_exp' }), false);
});

test('matchExportVideo matches video path or filename stem', () => {
  const item = {
    name: 'TO802-ปัญหาการใช้งาน_1_20260919_080000.mp4',
    rel_path: '04_Exports/Ready_to_post/TO802-ปัญหาการใช้งาน_1_20260919_080000.mp4',
    path: 'D:/Capcut/04_Exports/Ready_to_post/TO802-ปัญหาการใช้งาน_1_20260919_080000.mp4',
  };

  assert.equal(matchExportVideo(item, { videoPath: '04_Exports/Ready_to_post/TO802-ปัญหาการใช้งาน_1_20260919_080000.mp4' }), true);
  assert.equal(matchExportVideo(item, { projectName: 'TO802-ปัญหาการใช้งาน_1_20260919_080000' }), true);
  assert.equal(matchExportVideo(item, 'TO802-ปัญหาการใช้งาน_1_20260919_080000'), true);
  assert.equal(matchExportVideo(item, 'TO802-ปัญหาการใช้งาน_1_20260919_080000.mp4'), true);
  assert.equal(matchExportVideo(item, 'IWA01-รีวิวใช้จริง_1_20260917_234455'), false);
});

test('matchExportVideo matches product_id and angle_id with is_latest', () => {
  const itemLatest = {
    product_id: 'prod_toshino',
    angle_id: 'angle_spec',
    is_latest: true,
    name: 'toshino_v2.mp4',
  };
  const itemOld = {
    product_id: 'prod_toshino',
    angle_id: 'angle_spec',
    is_latest: false,
    name: 'toshino_v1.mp4',
  };

  assert.equal(matchExportVideo(itemLatest, { productId: 'prod_toshino', angleId: 'angle_spec' }), true);
  assert.equal(matchExportVideo(itemOld, { productId: 'prod_toshino', angleId: 'angle_spec' }), false);
});

test('matchExportVideo does not falsely match unrelated mouse clip for plug target', () => {
  const mouseItem = {
    name: 'IWA01-รีวิวใช้จริง_1_20260917_234455.mp4',
    rel_path: '04_Exports/Ready_to_post/IWA01-รีวิวใช้จริง_1_20260917_234455.mp4',
    path: 'D:/Capcut/04_Exports/Ready_to_post/IWA01-รีวิวใช้จริง_1_20260917_234455.mp4',
    project_name: 'IWA01-รีวิวใช้จริง_1_20260917_234455',
    product_name: 'เมาส์ไร้สาย IWACHI i6',
  };

  const plugTarget = {
    projectName: 'TO802-ปัญหาการใช้งาน_1_20260919_080000',
    videoPath: '04_Exports/Ready_to_post/TO802-ปัญหาการใช้งาน_1_20260919_080000.mp4',
    targetStr: 'TO802-ปัญหาการใช้งาน_1_20260919_080000',
  };

  assert.equal(matchExportVideo(mouseItem, plugTarget), false);
  assert.equal(matchExportVideo(mouseItem, 'TO802-ปัญหาการใช้งาน_1_20260919_080000'), false);
});
