import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_TARGETS,
  getMondayOfWeek,
  getSundayOfWeek,
  isSameDay,
  calculateProductionStats,
  getDailyActionQueue,
  generateBossGreeting,
  analyzeContentPerformance,
} from './producerInsights.js';

test('getMondayOfWeek and getSundayOfWeek calculate Monday to Sunday interval correctly', () => {
  // Wednesday 2026-09-09
  const wed = new Date('2026-09-09T14:30:00Z');
  const mon = getMondayOfWeek(wed);
  const sun = getSundayOfWeek(wed);

  assert.equal(mon.getDay(), 1); // Monday
  assert.equal(sun.getDay(), 0); // Sunday
  assert.equal(sun.getDate() - mon.getDate(), 6);
});

test('isSameDay matches same calendar date regardless of hours', () => {
  const d1 = new Date(2026, 8, 13, 2, 0, 0);
  const d2 = new Date(2026, 8, 13, 20, 30, 0);
  const d3 = new Date(2026, 8, 14, 2, 0, 0);

  assert.equal(isSameDay(d1, d2), true);
  assert.equal(isSameDay(d1, d3), false);
  assert.equal(isSameDay(null, d1), false);
});

test('calculateProductionStats tracks daily and weekly cuts and posts accurately', () => {
  const fixedNow = new Date('2026-09-13T12:00:00.000Z');
  const exports = [
    { export_id: 'exp1', created_at: '2026-09-13T08:00:00.000Z', is_posted: false },
    { export_id: 'exp2', created_at: '2026-09-13T10:00:00.000Z', is_posted: true, posted_at: '2026-09-13T11:00:00.000Z' },
    { export_id: 'exp3', created_at: '2026-09-10T10:00:00.000Z', is_posted: true, posted_at: '2026-09-10T11:00:00.000Z' }, // earlier this week
  ];

  const products = [
    {
      id: 'prod1',
      angles: [
        { angle_id: 'ang1', status: 'rendered', status_updated_at: '2026-09-13T09:00:00.000Z' },
      ],
    },
  ];

  const stats = calculateProductionStats(products, exports, { dailyCuts: 5, weeklyCuts: 35, dailyPosts: 3 }, fixedNow);

  // Today cuts: exp1 (cut today), exp2 (cut today), ang1 (rendered today) = 3
  assert.equal(stats.dailyCuts.current, 3);
  assert.equal(stats.dailyCuts.target, 5);
  assert.equal(stats.dailyCuts.remaining, 2);

  // Weekly cuts: exp1, exp2, exp3, ang1 = 4
  assert.equal(stats.weeklyCuts.current, 4);
  assert.equal(stats.weeklyCuts.target, 35);
  assert.equal(stats.weeklyCuts.remaining, 31);

  // Today posts: exp2 = 1
  assert.equal(stats.dailyPosts.current, 1);
  assert.equal(stats.dailyPosts.target, 3);
  assert.equal(stats.dailyPosts.remaining, 2);
});

test('getDailyActionQueue categorizes 3 priority queues properly', () => {
  const products = [
    {
      id: 'p1',
      name: 'Product 1',
      raw_videos: ['vid1.mov'],
      angles: [
        { angle_id: 'ang1', status: 'rendered', is_posted: false, hook_title: 'Hook 1' },
        { angle_id: 'ang2', status: 'in_production', is_posted: false, hook_title: 'Hook 2' },
        { angle_id: 'ang3', status: 'scripted', is_posted: false, hook_title: 'Hook 3' },
      ],
    },
    {
      id: 'p2',
      name: 'Product 2',
      raw_videos: [],
      angles: [
        { angle_id: 'ang4', status: 'scripted', is_posted: false, hook_title: 'Hook 4' },
      ],
    },
  ];

  const exports = [
    { export_id: 'exp1', name: 'unlinked_clip.mp4', is_posted: false },
  ];

  const queue = getDailyActionQueue(products, exports);

  // Ready to post: ang1, exp1
  assert.equal(queue.readyToPost.length, 2);
  assert.equal(queue.readyToPost[0].id, 'ang1');

  // Ready to cut: ang2 (in_production), ang3 (scripted with footage)
  assert.equal(queue.readyToCut.length, 2);
  assert.equal(queue.readyToCut[0].id, 'ang2');
  assert.equal(queue.readyToCut[1].id, 'ang3');

  // Needs footage: ang4 (scripted without footage)
  assert.equal(queue.needsFootage.length, 1);
  assert.equal(queue.needsFootage[0].id, 'ang4');
});

test('generateBossGreeting calls user เจ้านาย and adapts to status', () => {
  const stats = {
    dailyCuts: { current: 1, target: 5, remaining: 4 },
    weeklyCuts: { current: 10, target: 35, remaining: 25 },
    dailyPosts: { current: 0, target: 3, remaining: 3 },
  };
  const actionQueue = {
    readyToPost: [{ id: '1' }],
    readyToCut: [{ id: '2' }],
  };

  const greeting = generateBossGreeting({ stats, actionQueue, now: new Date('2026-09-13T09:00:00Z') });
  assert.ok(greeting.title.includes('เจ้านาย'));
  assert.ok(greeting.title.includes('ยังไม่ได้ลงคลิป'));
  assert.ok(greeting.message.includes('1 คลิป'));
});

test('analyzeContentPerformance identifies top video and actionable insights', () => {
  const tiktokRows = [
    { video_title: 'พัดลมมือถือไฟลุก', views: 4500, likes: 230, shares: 45 },
    { video_title: 'สายชาร์จถึกทน', views: 800, likes: 50, shares: 5 },
  ];

  const result = analyzeContentPerformance(tiktokRows);
  assert.equal(result.hasData, true);
  assert.equal(result.topPerformer.title, 'พัดลมมือถือไฟลุก');
  assert.equal(result.topPerformer.views, 4500);
  assert.ok(result.topTakeaways.length >= 2);
});
