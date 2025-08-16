/*
 * Week Header Controls Component
 * Back button and refresh button for week page
 * FIXED: Accept navigate as prop to avoid hook issues
 */

import React from 'react';

export default function WeekHeaderControls({ onRefresh, isRefreshing, onBack }) {
  return (
    <div className="flex justify-between items-center mb-6">
      <button
        onClick={onBack}
        className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl text-white hover:bg-[#3a3a3a] transition"
        style={{ backgroundColor: '#2d2d2d' }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      
      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl text-white hover:bg-[#1d4ed8] transition disabled:opacity-50"
        style={{ backgroundColor: '#2d2d2d' }}
      >
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span>{isRefreshing ? 'Sync' : 'Sync'}</span>
      </button>
    </div>
  );
}