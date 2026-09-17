import React from 'react';
import TokenDashboard from '../../TokenDashboard';

export default function TokensAnalyticsTab() {
  return (
    <div className="space-y-6">
      {/* Reusing existing robust TokenDashboard with enhanced styling container */}
      <TokenDashboard />
    </div>
  );
}
