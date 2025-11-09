import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

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
        className="quickview-modal-content"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-2xl font-bold text-white font-bebas tracking-wider uppercase">Week {weekNumber} - Quick View</h2>
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onClose();
            }}
            className="quickview-close-btn"
            aria-label="Close modal"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-white">
            <thead>
              <tr className="quickview-table-header">
                <th className="text-left py-3 px-3 font-roboto uppercase font-bold text-sm tracking-wide">Game</th>
                <th className="text-center py-3 px-3 font-roboto uppercase font-bold text-sm tracking-wide">$</th>
                <th className="text-center py-3 px-3 font-roboto uppercase font-bold text-sm tracking-wide">Prop</th>
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
                    <td className="py-3 px-3 font-semibold font-roboto uppercase text-white text-sm">
                      {game.away_team} @ {game.home_team}
                    </td>
                    <td className="py-3 px-3 font-roboto uppercase font-bold text-white text-center text-sm" style={{letterSpacing: '0.05rem', borderLeft: '1px solid rgba(68, 68, 68, 0.3)'}}>
                      {moneyLineSelections[game.id] || <span className="text-gray-600">—</span>}
                    </td>
                    <td className="py-3 px-3 font-roboto uppercase font-bold text-white text-center text-sm" style={{letterSpacing: '0.05rem', borderLeft: '1px solid rgba(68, 68, 68, 0.3)'}}>
                      {getPropBetPick(game) === '—' ? <span className="text-gray-600">—</span> : getPropBetPick(game)}
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
      </div>
    </div>,
    document.body
  );
}