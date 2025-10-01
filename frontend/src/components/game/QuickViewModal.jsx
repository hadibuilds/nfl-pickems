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
      className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-[10001] backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="bg-gradient-to-br from-[#2d2d2d] via-[#1e1e1e] to-[#2a2a2a] rounded-2xl shadow-2xl p-8 max-w-4xl w-full mx-4 max-h-[85vh] overflow-y-auto border border-white border-opacity-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-3xl font-bold text-white font-bebas tracking-wider uppercase">Week {weekNumber} - Quick View</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-all duration-200 focus:outline-none p-2 rounded-full hover:bg-white hover:bg-opacity-10 active:scale-95"
            aria-label="Close modal"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-white">
            <thead>
              <tr className="border-b-2 border-[#F59E0B] border-opacity-30">
                <th className="text-left py-4 px-4 font-roboto uppercase font-bold text-base tracking-wide text-[#F59E0B]">Game</th>
                <th className="text-center py-4 px-4 font-roboto uppercase font-bold text-base tracking-wide text-[#F59E0B]">$</th>
                <th className="text-center py-4 px-4 font-roboto uppercase font-bold text-base tracking-wide text-[#F59E0B]">Prop</th>
              </tr>
            </thead>
            <tbody>
              {games.length > 0 ? (
                games.map((game, index) => (
                  <tr
                    key={game.id}
                    className="border-b border-gray-700 border-opacity-50 transition-all duration-200 hover:bg-white hover:bg-opacity-5"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <td className="py-4 px-4 font-semibold font-roboto uppercase text-white">
                      {game.away_team} @ {game.home_team}
                    </td>
                    <td className="py-4 px-4 font-roboto uppercase font-bold text-white text-center text-lg" style={{letterSpacing: '0.05rem'}}>
                      {moneyLineSelections[game.id] || <span className="text-gray-600">—</span>}
                    </td>
                    <td className="py-4 px-4 font-roboto uppercase font-bold text-white text-center text-lg" style={{letterSpacing: '0.05rem'}}>
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