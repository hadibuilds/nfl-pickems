import React from "react";
import { Link } from "react-router-dom";

export default function WeekSelector() {
  const totalWeeks = 18;
  const weeks = Array.from({ length: totalWeeks }, (_, i) => i + 1);
  
  // TODO: Replace these with real data from your backend/context
  // You'll need to pass these as props or get from context:
  // - games data for each week
  // - current week number
  // - completed weeks with points
  // - game results
  
  const getWeekStatus = (weekNumber) => {
    const now = new Date();
    
    // FOR TESTING: Week 1 starts today and lasts 4 weeks (28 days)
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Start of today
    
    if (weekNumber === 1) {
      // Week 1 is current for 4 weeks starting today
      const week1End = new Date(today);
      week1End.setDate(today.getDate() + 28); // 4 weeks from today
      
      if (now >= today && now < week1End) {
        return {
          status: 'current',
          points: null,
          label: 'Current Week'
        };
      } else if (now >= week1End) {
        return {
          status: 'completed',
          points: null,
          label: 'Completed'
        };
      }
    } else {
      // All other weeks are upcoming for now
      return {
        status: 'upcoming',
        points: null,
        label: 'Coming Soon'
      };
    }
    
    return {
      status: 'upcoming',
      points: null,
      label: 'Coming Soon'
    };
  };

  const getWeekDates = (weekNumber) => {
    // Calculate week dates based on Tuesday schedule
    const firstTuesday = new Date('2025-09-02T16:00:00Z'); // Sept 2, 2025 8 AM PST
    
    const weekStart = new Date(firstTuesday);
    weekStart.setDate(firstTuesday.getDate() + ((weekNumber - 1) * 7));
    
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6); // 7 days later (Tuesday to Monday)
    
    return {
      start: weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      end: weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    };
  };

  const getCardStyles = (status) => {
    switch (status) {
      case 'completed':
        return {
          backgroundColor: '#10B981', // Green
          borderColor: '#059669',
          textColor: 'white',
          hoverColor: '#047857'
        };
      case 'current':
        return {
          backgroundColor: '#8B5CF6', // Purple
          borderColor: '#7C3AED',
          textColor: 'white',
          hoverColor: '#7C3AED'
        };
      case 'upcoming':
        return {
          backgroundColor: '#374151', // Gray
          borderColor: '#4B5563',
          textColor: '#9CA3AF',
          hoverColor: '#4B5563'
        };
      default:
        return {
          backgroundColor: '#2d2d2d',
          borderColor: '#4B5563',
          textColor: 'white',
          hoverColor: '#3a3a3a'
        };
    }
  };

  return (
    <div className="min-h-screen py-12 px-6" style={{ backgroundColor: '#1E1E20', color: 'white' }}>
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl text-center mb-12 font-bold text-white">
          Select a Week
        </h1>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {weeks.map((week) => {
            const weekStatus = getWeekStatus(week);
            const weekDates = getWeekDates(week);
            const styles = getCardStyles(weekStatus.status);

            return (
              <div key={week} className="week-card-wrapper">
                <Link
                  to={`/week/${week}`}
                  className="week-card"
                  style={{ 
                    backgroundColor: styles.backgroundColor,
                    borderColor: styles.borderColor,
                    color: styles.textColor
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = styles.hoverColor;
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = styles.backgroundColor;
                  }}
                >
                  <div className="week-card-content">
                    <div className="week-header">
                      <h3 className="week-number">Week {week}</h3>
                      <span 
                        className="week-status-badge" 
                        style={{ 
                          backgroundColor: weekStatus.status === 'completed' ? '#065F46' : 
                                         weekStatus.status === 'current' ? '#5B21B6' : '#374151'
                        }}
                      >
                        {weekStatus.label}
                      </span>
                    </div>
                    
                    <div className="week-dates" style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                      {weekDates.start} - {weekDates.end}
                    </div>
                    
                    <div className="week-footer">
                      {weekStatus.status === 'completed' && weekStatus.points !== null && (
                        <div className="points-earned">
                          <span className="points-label">Points: </span>
                          <span className="points-value">{weekStatus.points}</span>
                        </div>
                      )}
                      {weekStatus.status === 'current' && (
                        <div className="current-indicator">
                          <span>▶ Play Now</span>
                        </div>
                      )}
                    </div>
                  </div>
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}