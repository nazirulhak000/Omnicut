import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_TARGETS,
  getMondayOfWeek,
  getSundayOfWeek,
  isSameDay,
  calculateProductionStats,
  getDailyActionQueue,
  getNextAction,
  generateBossGreeting,
  analyzeContentPerformance,
  calculateWeeklyPacing,
  autoSuggestPlaybookNotes,
  diversifyByProduct,
  detectRefPlatform,
  getClipIdentityAliases,
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

test('calculateProductionStats deduplicates an angle and its matching export media', () => {
  const now = new Date('2026-09-13T12:00:00.000Z');
  const products = [{
    id: 'p1',
    angles: [{
      angle_id: 'ang1',
      status: 'rendered',
      status_updated_at: '2026-09-13T09:00:00.000Z',
      rendered_video: 'D:/exports/clip-one.mp4',
    }],
  }];
  const exports = [{
    export_id: 'exp1',
    path: 'D:/exports/clip-one.mp4',
    created_at: '2026-09-13T08:00:00.000Z',
    is_posted: false,
  }];

  const stats = calculateProductionStats(products, exports, DEFAULT_TARGETS, now);

  assert.equal(stats.dailyCuts.current, 1);
  assert.equal(stats.weeklyCuts.current, 1);
  assert.equal(stats.dailyCuts.sourceIds.length, 1);
  assert.equal(stats.contract, '1.1.0');
});

test('clip identity aliases normalize equivalent media paths', () => {
  assert.deepEqual(
    getClipIdentityAliases({ path: 'D:\\Exports\\CLIP-ONE.MP4' }),
    ['media:clip-one'],
  );
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

test('getNextAction returns a traceable priority reason and prefers shippable work', () => {
  const now = new Date('2026-09-13T12:00:00.000Z');
  const next = getNextAction({
    readyToPost: [{ id: 'export-1', productName: 'Product 1', updatedAt: '2026-09-12T10:00:00.000Z' }],
    readyToCut: [{ id: 'angle-1', productName: 'Product 2', updatedAt: '2026-09-01T10:00:00.000Z' }],
    needsFootage: [{ id: 'angle-2', productName: 'Product 3' }],
  }, now);

  assert.equal(next.type, 'post');
  assert.equal(next.item.id, 'export-1');
  assert.equal(next.priorityReason, 'เรนเดอร์เสร็จแล้วและยังไม่โพสต์');
  assert.equal(next.contract, '1.1.0');
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
  assert.equal(result.method, 'heuristic');
  assert.equal(result.sampleSize, 2);
});

test('analyzeContentPerformance changes evidence when metric distribution changes', () => {
  const skewed = analyzeContentPerformance([
    { id: 'clip-top', video_title: 'ตัวชนะ', views: 10000, likes: 700, shares: 200, comments: 100, posted_at: '2026-09-01T00:00:00Z' },
    { id: 'clip-low', video_title: 'คลิปทั่วไป', views: 500, likes: 5, shares: 1, comments: 1, posted_at: '2026-09-02T00:00:00Z' },
  ]);
  const consistent = analyzeContentPerformance([
    { id: 'clip-a', video_title: 'คลิป A', views: 2000, likes: 100, shares: 40, comments: 20, posted_at: '2026-09-01T00:00:00Z' },
    { id: 'clip-b', video_title: 'คลิป B', views: 2100, likes: 105, shares: 42, comments: 21, posted_at: '2026-09-02T00:00:00Z' },
  ]);

  assert.equal(skewed.topPerformer.sourceId, 'clip-top');
  assert.ok(skewed.metrics.topVsMedian > consistent.metrics.topVsMedian);
  assert.notEqual(skewed.topTakeaways[0], consistent.topTakeaways[0]);
  assert.equal(skewed.period.from, '2026-09-01T00:00:00.000Z');
  assert.equal(skewed.period.to, '2026-09-02T00:00:00.000Z');
});

test('calculateWeeklyPacing calculates remaining pace accurately', () => {
  // Wednesday (2026-09-09) -> 5 days remaining (Wed, Thu, Fri, Sat, Sun)
  const wed = new Date('2026-09-09T10:00:00Z');
  const statsOnTrack = {
    weeklyCuts: { remaining: 15, target: 35 },
    dailyCuts: { target: 5 },
  };
  const pacingOnTrack = calculateWeeklyPacing(statsOnTrack, wed);
  assert.equal(pacingOnTrack.daysRemaining, 5);
  assert.equal(pacingOnTrack.dailyRequired, 3);
  assert.equal(pacingOnTrack.paceStatus, 'on_track');

  // Behind pace: 25 cuts remaining with 3 days left (Fri, Sat, Sun)
  const fri = new Date('2026-09-11T10:00:00Z');
  const statsBehind = {
    weeklyCuts: { remaining: 25, target: 35 },
    dailyCuts: { target: 5 },
  };
  const pacingBehind = calculateWeeklyPacing(statsBehind, fri);
  assert.equal(pacingBehind.daysRemaining, 3);
  assert.equal(pacingBehind.dailyRequired, 9); // Math.ceil(25/3) = 9
  assert.equal(pacingBehind.paceStatus, 'behind');

  // Completed
  const statsDone = {
    weeklyCuts: { remaining: 0, target: 35 },
    dailyCuts: { target: 5 },
  };
  const pacingDone = calculateWeeklyPacing(statsDone, wed);
  assert.equal(pacingDone.paceStatus, 'completed');
});

test('autoSuggestPlaybookNotes suggests notes and checks duplicates', () => {
  const retrospective = {
    topTakeaways: [
      'คลิปที่เปิดด้วย Hook ปัญหาหรือคำเตือน มักดึงยอดวิวช่วง 3 วินาทีแรกได้ดี',
      'การเปิดเสียง SFX ชัดเจนช่วยเพิ่มความน่าสนใจ',
    ],
  };

  const currentNotes = [
    { id: '1', text: 'การเปิดเสียง SFX ชัดเจนช่วยเพิ่มความน่าสนใจ' },
  ];

  const suggestions = autoSuggestPlaybookNotes(retrospective, currentNotes);
  assert.equal(suggestions.length, 2);
  assert.equal(suggestions[0].tag, 'Hook');
  assert.equal(suggestions[0].alreadySaved, false);
  assert.equal(suggestions[1].tag, 'Audio');
  assert.equal(suggestions[1].alreadySaved, true);
});

test('diversifyByProduct round-robins items across products fairly', () => {
  const items = [
    { id: '1', productCode: 'PROD_A', title: 'A1' },
    { id: '2', productCode: 'PROD_A', title: 'A2' },
    { id: '3', productCode: 'PROD_A', title: 'A3' },
    { id: '4', productCode: 'PROD_B', title: 'B1' },
    { id: '5', productCode: 'PROD_B', title: 'B2' },
    { id: '6', productCode: 'PROD_C', title: 'C1' },
  ];

  const diversified = diversifyByProduct(items);
  // Round 0: A1, B1, C1
  // Round 1: A2, B2
  // Round 2: A3
  assert.equal(diversified[0].id, '1');
  assert.equal(diversified[1].id, '4');
  assert.equal(diversified[2].id, '6');
  assert.equal(diversified[3].id, '2');
  assert.equal(diversified[4].id, '5');
  assert.equal(diversified[5].id, '3');
});

test('detectRefPlatform recognizes social URLs accurately', () => {
  assert.equal(detectRefPlatform('https://www.tiktok.com/@user/video/123456789'), 'tiktok');
  assert.equal(detectRefPlatform('https://vt.tiktok.com/ZS99999/'), 'tiktok');
  assert.equal(detectRefPlatform('https://pin.it/7xK9m'), 'pinterest');
  assert.equal(detectRefPlatform('https://www.pinterest.com/pin/12345/'), 'pinterest');
  assert.equal(detectRefPlatform('https://www.youtube.com/watch?v=abc'), 'youtube');
  assert.equal(detectRefPlatform('https://example.com/blog'), 'web');
  assert.equal(detectRefPlatform('just some random note'), null);
});
