import React from 'react';

export default function WeekHeader({ weekNumber, onBack, onQuickView }) {
  return (
    <div className="max-w-4xl mx-auto mb-8">  {/* Match game grid constraints */}
      <div className="flex items-center justify-between relative">
        {/* Back button - positioned on left */}
        <button
          onClick={onBack}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl text-white hover:bg-[#3a3a3a] transition focus:outline-none focus:ring-0 focus-visible:ring-0"
          style={{ backgroundColor: '#2d2d2d' }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        {/* Page title - absolutely centered within the max-w-4xl container */}
        <h1 className="absolute left-1/2 transform -translate-x-1/2 text-5xl sm:text-6xl md:text-7xl text-white font-bebas tracking-wider">
          Week {weekNumber}
        </h1>

        {/* Quick View button - positioned on right - only show if onQuickView is provided */}
        {onQuickView && (
          <button
            onClick={onQuickView}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl text-white hover:bg-[#3a3a3a] transition focus:outline-none focus:ring-0 focus-visible:ring-0"
            style={{ backgroundColor: '#2d2d2d' }}
            title="Quick View - See all your picks"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="white" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 21h12a2 2 0 0 0 2-2v-2H10v2a2 2 0 1 1-4 0V3a2 2 0 1 1 4 0v3h11v2H10v2h11v2H10v2h11v2H10z"/>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 5v2"/>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 9v2"/>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 13v2"/>
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}