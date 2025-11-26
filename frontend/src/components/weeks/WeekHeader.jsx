import React from 'react';

export default function WeekHeader({ weekNumber, onBack, onQuickView }) {
  return (
    <div className="max-w-4xl mx-auto mb-6 mt-2">
      <div className="flex items-center justify-between relative">
        {/* Back button - larger, better spaced */}
        <button
          onClick={onBack}
          className="week-header-button"
          title="Back"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 19l-7-7 7-7" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        
        {/* Page title - larger, better centered */}
        <h1 className="absolute left-1/2 transform -translate-x-1/2 text-4xl sm:text-5xl md:text-6xl text-white font-bebas font-bold tracking-wide">
          Week {weekNumber || '...'}
        </h1>

        {/* Quick View button - larger, better spaced */}
        {onQuickView ? (
          <button
            onClick={onQuickView}
            className="week-header-button"
            title="Quick View - See all your picks"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M8 21h12a2 2 0 0 0 2-2v-2H10v2a2 2 0 1 1-4 0V3a2 2 0 1 1 4 0v3h11v2H10v2h11v2H10v2h11v2H10z" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M10 5v2" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M10 9v2" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M10 13v2" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        ) : (
          <div className="week-header-button" style={{ visibility: 'hidden' }}></div>
        )}
      </div>
    </div>
  );
}