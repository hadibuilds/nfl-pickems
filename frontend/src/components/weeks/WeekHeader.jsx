import React from 'react';

export default function WeekHeader({ weekNumber, onBack }) {
  return (
    <div className="max-w-4xl mx-auto mb-8">  {/* Match game grid constraints */}
      <div className="flex items-center relative">
        {/* Back button - positioned on left */}
        <button
          onClick={onBack}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl text-white hover:bg-[#3a3a3a] transition focus:outline-none"
          style={{ backgroundColor: '#2d2d2d' }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        {/* Page title - absolutely centered within the max-w-4xl container */}
        <h1 className="absolute left-1/2 transform -translate-x-1/2 text-4xl sm:text-5xl md:text-6xl text-white font-bebas tracking-wider">
          Week {weekNumber}
        </h1>
      </div>
    </div>
  );
}