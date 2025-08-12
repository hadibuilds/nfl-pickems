import { useEffect, useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

export default function Standings() {
  const { userInfo } = useAuth();
  const [standings, setStandings] = useState([]);
  const [weeks, setWeeks] = useState([]);
  const [selectedWeek, setSelectedWeek] = useState(null);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  const API_BASE = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const fetchStandings = async () => {
      try {
        const res = await fetch(`${API_BASE}/predictions/api/standings/`, {
          credentials: 'include',
        });
        const data = await res.json();
        setStandings(data.standings);
        setWeeks(data.weeks.sort((a, b) => a - b));
      } catch (err) {
        console.error('Failed to load standings:', err);
      }
    };

    fetchStandings();
  }, [API_BASE]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const sortedStandings = [...standings].sort((a, b) => {
    const aPoints = selectedWeek ? a.weekly_scores[selectedWeek] || 0 : a.total_points;
    const bPoints = selectedWeek ? b.weekly_scores[selectedWeek] || 0 : b.total_points;

    if (bPoints !== aPoints) return bPoints - aPoints;
    return a.username.localeCompare(b.username);
  });

  return (
    <div className="flex justify-start items-start pt-20 min-h-screen w-full px-4 sm:px-6" style={{ backgroundColor: '#1E1E20' }}>
      <div className="w-full max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-4 text-white">League Standings</h1>

        <div className="relative inline-block text-left mb-6" ref={dropdownRef}>
          <button
            onClick={() => setOpen(!open)}
            className="inline-flex justify-between w-48 px-4 py-2 text-sm font-medium rounded-md shadow-sm focus:outline-none text-white hover:bg-[#3a3a3a] transition"
            style={{ 
              backgroundColor: '#2d2d2d',
              border: '1px solid #4b5563'
            }}
          >
            {selectedWeek ? `Week ${selectedWeek}` : 'All Weeks (Total)'}
            <svg className="w-4 h-4 ml-2 mt-[2px]" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.293l3.71-4.06a.75.75 0 111.08 1.04l-4.25 4.65a.75.75 0 01-1.08 0l-4.25-4.65a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </button>

          {open && (
            <div className="absolute z-10 mt-2 w-48 rounded-md shadow-lg text-white ring-1" style={{ backgroundColor: '#2d2d2d', borderColor: '#4b5563' }}>
              <ul className="py-1 text-sm">
                <li>
                  <button
                    onClick={() => {
                      setSelectedWeek(null);
                      setOpen(false);
                    }}
                    className="w-full px-4 py-2 text-left text-white hover:bg-[#3a3a3a] transition"
                  >
                    All Weeks (Total)
                  </button>
                </li>
                {weeks.map((week) => (
                  <li key={week}>
                    <button
                      onClick={() => {
                        setSelectedWeek(week);
                        setOpen(false);
                      }}
                      className="w-full px-4 py-2 text-left text-white hover:bg-[#3a3a3a] transition"
                    >
                      Week {week}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="overflow-x-auto rounded-xl shadow-lg">
          <table className="min-w-full text-sm text-left text-white">
            <thead className="text-xs uppercase font-semibold tracking-wider" style={{ backgroundColor: '#2d2d2d' }}>
              <tr>
                <th className="px-5 py-3 text-white">Rank</th>
                <th className="px-5 py-3 text-white">User</th>
                <th className="px-5 py-3 text-white">
                  {selectedWeek ? `Week ${selectedWeek}` : 'Total'}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ backgroundColor: '#1f1f1f', borderColor: '#4b5563' }}>
              {sortedStandings.map((entry, index) => {
                const points = selectedWeek
                  ? entry.weekly_scores[selectedWeek] || 0
                  : entry.total_points;

                return (
                  <tr
                    key={entry.username}
                    className="hover:bg-[#2a2a2a] transition text-white"
                    style={{ backgroundColor: '#1f1f1f' }}
                  >
                    <td className="px-5 py-3 whitespace-nowrap text-white">{index + 1}</td>
                    <td className="px-5 py-3 whitespace-nowrap text-white">{entry.username}</td>
                    <td className="px-5 py-3 whitespace-nowrap text-center text-white">{points}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}