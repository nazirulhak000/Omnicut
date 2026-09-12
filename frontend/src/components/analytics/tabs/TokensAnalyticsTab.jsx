import React, { useRef } from 'react';
import TokenDashboard from '../../TokenDashboard';

export default function TokensAnalyticsTab() {
  const tokenDashboardRef = useRef(null);

  return (
    <div className="space-y-6">
      {/* Reusing existing robust TokenDashboard with enhanced styling container */}
      <TokenDashboard ref={tokenDashboardRef} />
    </div>
  );
}
