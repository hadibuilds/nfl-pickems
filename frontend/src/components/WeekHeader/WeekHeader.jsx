/*
 * Week Header Component
 * Complete header section with controls and title for week page
 * FIXED: Pass navigate function down to controls
 */

import React from 'react';
import WeekHeaderControls from './WeekHeaderControls.jsx';

export default function WeekHeader({ weekNumber, onRefresh, isRefreshing, onBack }) {
  return (
    <>
      {/* Back button and refresh */}
      <WeekHeaderControls onRefresh={onRefresh} isRefreshing={isRefreshing} onBack={onBack} />

      {/* Page title */}
      <h1 className="text-4xl text-center mb-8 text-white">
        Week {weekNumber} Games
      </h1>
    </>
  );
}