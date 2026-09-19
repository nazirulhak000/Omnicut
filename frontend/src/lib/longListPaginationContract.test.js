import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const readComponent = (relativePath) => fs.readFileSync(
  path.resolve(process.cwd(), relativePath),
  'utf8',
);

test('long-list surfaces render paginated visible collections instead of raw full arrays', () => {
  const contracts = [
    {
      file: 'src/components/ExportGallery.jsx',
      visible: ['visibleSplitExports.map', 'visibleExports.map'],
      raw: ['filteredExports.map(item =>'],
    },
    {
      file: 'src/components/analytics/tabs/PerformanceAnalyticsTab.jsx',
      visible: ['visiblePendingRows.map', 'visibleIgnoredRows.map'],
      raw: ['pendingRows.map', 'ignoredRows.map'],
    },
    {
      file: 'src/components/TokenDashboard.jsx',
      visible: ['visibleDailyBreakdownRows.map'],
      raw: ['[...filteredDailyStats].reverse().map'],
    },
    {
      file: 'src/components/analytics/tabs/StorageAnalyticsTab.jsx',
      visible: ['visibleArchiveItems.map'],
      raw: ['archiveItems.map'],
    },
    {
      file: 'src/components/ActivityCenter.jsx',
      visible: ['visibleFilteredTasks.map', 'visibleViralMilestones.map'],
      raw: ['filteredTasks.map', 'viralMilestones.map'],
    },
  ];

  for (const contract of contracts) {
    const source = readComponent(contract.file);
    for (const marker of contract.visible) {
      assert.ok(source.includes(marker), `${contract.file} must render ${marker}`);
    }
    for (const marker of contract.raw) {
      assert.ok(!source.includes(marker), `${contract.file} must not render raw ${marker}`);
    }
  }
});
