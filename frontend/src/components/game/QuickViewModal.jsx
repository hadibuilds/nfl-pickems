import React from 'react';
import { createPortal } from 'react-dom';

export default function QuickViewModal({ 
  isOpen, 
  onClose, 
  weekNumber, 
  games = [], 
  moneyLineSelections = {}, 
  propBetSelections = {} 
}) {

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
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10001]"
      onClick={handleBackdropClick}
    >
      <div className="bg-[#1a1a1a] rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white font-bebas tracking-wider uppercase">Week {weekNumber} - Quick View</h2>
          <button
            onClick={onClose}
            className="text-[#800020] transition active:text-[#800020] md:hover:text-[#800020] focus:outline-none focus:ring-2 focus:ring-[#800020] focus:ring-offset-2 focus:ring-offset-[#1a1a1a] md:focus:ring-2 md:focus:ring-[#800020] md:focus:ring-offset-2 md:focus:ring-offset-[#1a1a1a]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-white">
            <thead>
              <tr className="border-b border-gray-600">
                <th className="text-left py-3 px-4 font-roboto uppercase font-semibold text-sm tracking-wide" style={{color: '#F59E0B'}}>Game</th>
                <th className="text-center py-3 px-4 font-roboto uppercase font-semibold text-sm tracking-wide" style={{color: '#F59E0B'}}>$</th>
                <th className="text-center py-3 px-4 font-roboto uppercase font-semibold text-sm tracking-wide" style={{color: '#F59E0B'}}>Prop</th>
              </tr>
            </thead>
            <tbody>
              {games.length > 0 ? (
                games.map((game) => (
                  <tr key={game.id} className="border-b border-gray-700 md:hover:bg-gray-800">
                    <td className="py-3 px-4 font-semibold font-roboto uppercase text-white">
                      {game.away_team} @ {game.home_team}
                    </td>
                    <td className="py-3 px-4 font-roboto uppercase font-medium text-white text-center" style={{opacity: 0.75, letterSpacing: '0.05rem'}}>
                      {moneyLineSelections[game.id] || '—'}
                    </td>
                    <td className="py-3 px-4 font-roboto uppercase font-medium text-white text-center" style={{opacity: 0.75, letterSpacing: '0.05rem'}}>
                      {getPropBetPick(game)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="text-center py-8 text-gray-400">
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