import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { getTeamLogo } from '../../utils/teamLogos.js';

export default function QuickViewModal({
  isOpen,
  onClose,
  weekNumber,
  games = [],
  moneyLineSelections = {},
  propBetSelections = {}
}) {

  // Lock scroll when modal is open
  useEffect(() => {
    if (!isOpen) return;

    const body = document.body;
    const html = document.documentElement;

    // Lock scroll without changing position
    const originalOverflow = body.style.overflow;
    const originalHtmlOverflow = html.style.overflow;

    body.style.overflow = 'hidden';
    html.style.overflow = 'hidden';
    html.style.overscrollBehavior = 'contain';

    // Disable pull-to-refresh while modal is open
    body.dataset.modalOpen = 'true';

    return () => {
      // Restore scroll
      body.style.overflow = originalOverflow;
      html.style.overflow = originalHtmlOverflow;
      html.style.overscrollBehavior = '';
      delete body.dataset.modalOpen;
    };
  }, [isOpen]);

  // Track which game's prop question tooltip is open and its position
  const [activeQuestionGameId, setActiveQuestionGameId] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, right: 0 });
  const modalContentRef = useRef(null);
  const cellRefs = useRef({});

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Get prop bet selection for a game
  const getPropBetPick = (game) => {
    if (!game.prop_bets || game.prop_bets.length === 0) return '—';
    
    const propBet = game.prop_bets[0]; // Assuming one prop bet per game
    const selection = propBetSelections[propBet.id];
    return selection || '—';
  };

  // Handle tooltip toggle with position calculation
  const handleTooltipToggle = (gameId, pillElement) => {
    if (activeQuestionGameId === gameId) {
      setActiveQuestionGameId(null);
    } else {
      if (pillElement && modalContentRef.current) {
        const pillRect = pillElement.getBoundingClientRect();
        const modalRect = modalContentRef.current.getBoundingClientRect();
        
        // Account for modal scroll position
        const modalScrollTop = modalContentRef.current.scrollTop;
        
        // Calculate position relative to modal content - right edge of the pill (grows leftward)
        const right = modalRect.right - pillRect.right;
        // Position at the top of the pill (grows upward) - add scroll offset
        const top = (pillRect.top - modalRect.top) + modalScrollTop;
        
        setTooltipPosition({ top, right });
        setActiveQuestionGameId(gameId);
      } else {
        // Fallback: just toggle without position calculation
        setActiveQuestionGameId(gameId);
      }
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-[10001] backdrop-blur-sm"
      onMouseDown={handleBackdropClick}
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), 50px)',
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 20px)',
      }}
    >
      <div
        ref={modalContentRef}
        className="quickview-modal-content"
        onMouseDown={(e) => e.stopPropagation()}
      >
      {/* Header */}
      <div className="flex items-center justify-between mb-1.5">
          <h2 className="text-xl font-semibold text-white font-bebas tracking-[0.18em] uppercase">
            Quick View - Week {weekNumber}
          </h2>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onClose();
            }}
            className="quickview-close-btn"
            aria-label="Close modal"
            >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        {/* Helper subheader */}
        <p className="text-[11px] font-roboto text-gray-400 mb-2">
          Tap a prop answer to see the full question.
        </p>

        {/* Content */}
        <div style={{ overflowX: 'hidden', overflowY: 'visible' }}>
          <table className="w-full text-white">
            <thead>
              <tr className="quickview-table-header">
                <th className="text-left py-2 px-3 font-roboto uppercase font-semibold text-xs tracking-[0.16em]">Game</th>
                <th className="text-center py-2 px-3 font-roboto uppercase font-semibold text-xs tracking-[0.16em]">$</th>
                <th className="text-center py-2 px-3 font-roboto uppercase font-semibold text-xs tracking-[0.16em]">Prop</th>
              </tr>
            </thead>
            <tbody>
              {games.length > 0 ? (
                games.map((game, index) => (
                  <tr
                    key={game.id}
                    className="quickview-table-row"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <td className="py-2 px-3 font-semibold font-roboto uppercase text-white text-sm">
                      {game.away_team} @ {game.home_team}
                    </td>
                    <td className="py-2 px-3 text-center" style={{borderLeft: '1px solid rgba(68, 68, 68, 0.3)'}}>
                      {moneyLineSelections[game.id] ? (
                        <img
                          src={getTeamLogo(moneyLineSelections[game.id])}
                          alt={moneyLineSelections[game.id]}
                          className="quickview-team-logo"
                        />
                      ) : (
                        <span className="text-gray-600">—</span>
                      )}
                    </td>
                    <td
                      ref={(el) => { if (el) cellRefs.current[game.id] = el; }}
                      className="py-2 px-3 font-roboto uppercase font-bold text-white text-center text-sm"
                      style={{ letterSpacing: '0.06rem', borderLeft: '1px solid rgba(68, 68, 68, 0.3)' }}
                    >
                      <div
                        className="relative inline-block w-full"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          if (game.prop_bets && game.prop_bets.length > 0) {
                            // Find the actual pill element (span) for positioning
                            const pillElement = e.currentTarget.querySelector('.quickview-prop-pill') || e.currentTarget;
                            handleTooltipToggle(game.id, pillElement);
                          }
                        }}
                      >
                        {getPropBetPick(game) === '—' ? (
                          <span className="text-gray-600">—</span>
                        ) : (
                          <span
                            className={`quickview-prop-pill ${
                              (getPropBetPick(game) || '').length > 5
                                ? 'quickview-prop-pill--long'
                                : ''
                            }`}
                          >
                            {getPropBetPick(game)}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="text-center py-12 text-gray-500 font-medium">
                    No games found for this week
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        
        {/* Tooltip rendered relative to modal content */}
        {activeQuestionGameId && games.find(g => g.id === activeQuestionGameId)?.prop_bets?.[0] && (
          <div
            className="quickview-prop-tooltip"
            style={{
              position: 'absolute',
              top: `${tooltipPosition.top}px`,
              right: `${tooltipPosition.right}px`,
              bottom: 'auto',
              left: 'auto',
              transform: 'translateY(calc(-100% - 6px))',
            }}
          >
            <div className="whitespace-normal text-left" style={{ margin: 0, padding: 0 }}>
              {games.find(g => g.id === activeQuestionGameId)?.prop_bets[0].question}
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}