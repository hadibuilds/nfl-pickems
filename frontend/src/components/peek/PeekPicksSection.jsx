import React from 'react';
import UserAvatar from './UserAvatar';

export default function PeekPicksSection({ game, peekData }) {
  const propBet = game?.prop_bets?.[0];

  // Group users by their picks (backend shape you described)
  const picksByTeam = peekData?.moneyline_picks || { home_team: [], away_team: [] };
  const picksByProp = peekData?.prop_picks || { answer_a: [], answer_b: [] };

  const getQuadrantUsers = (teamKey, answerKey) => {
    const teamPickers = picksByTeam?.[teamKey] || [];
    const propPickers = picksByProp?.[answerKey] || [];
    // Intersect by username
    const propSet = new Set(propPickers.map((u) => u.username));
    return teamPickers.filter((u) => propSet.has(u.username));
  };

  // Precompute quadrants
  const quadrants = {
    awayA: getQuadrantUsers('away_team', 'answer_a'),
    homeA: getQuadrantUsers('home_team', 'answer_a'),
    awayB: getQuadrantUsers('away_team', 'answer_b'),
    homeB: getQuadrantUsers('home_team', 'answer_b'),
  };

  const getOptionLabel = (answerKey) => {
    if (!propBet) return answerKey === 'answer_a' ? 'Option A' : 'Option B';
    const a = propBet.option_a ?? propBet.options?.[0] ?? 'Option A';
    const b = propBet.option_b ?? propBet.options?.[1] ?? 'Option B';
    return answerKey === 'answer_a' ? a : b;
  };

  // Color mapping
  const TEAM_COLORS = {
    home: 'text-purple-400', // light purple
    away: 'text-sky-400',    // dodger blue
  };
  const OPTION_COLORS = {
    answer_a: 'text-amber-200', // Option A → purple
    answer_b: 'text-zinc-300',    // Option B → blue
  };

  // Fallback UI when no prop bet present (Away on left, Home on right)
  if (!propBet) {
    return (
      <div className="p-[15px]">
        <div className="grid grid-cols-2 gap-[15px]">
          <QuadrantSection
            teamTone="away"
            optionKey={null}
            titleTeam={game.away_team}
            titleOption={null}
            users={picksByTeam.away_team || []}
            TEAM_COLORS={TEAM_COLORS}
            OPTION_COLORS={OPTION_COLORS}
            compact={false}
          />
          <QuadrantSection
            teamTone="home"
            optionKey={null}
            titleTeam={game.home_team}
            titleOption={null}
            users={picksByTeam.home_team || []}
            TEAM_COLORS={TEAM_COLORS}
            OPTION_COLORS={OPTION_COLORS}
            compact={false}
          />
        </div>
        <div className="mt-2 flex justify-between text-[11px]" style={{ color: '#666' }}>
          <span>{game.away_team}: {(picksByTeam.away_team || []).length}</span>
          <span>{game.home_team}: {(picksByTeam.home_team || []).length}</span>
        </div>
      </div>
    );
  }

  // Normal 2x2: top = Option A, bottom = Option B; left = Away, right = Home
  return (
    <div className="p-[15px]">
      <div
        className="mb-[15px] text-center text-[12px] border-b border-[#444] pb-[10px]"
        style={{ color: '#888' }}
      >
        <strong>{propBet.question}</strong>
      </div>

      <div
        className="grid"
        style={{
          gridTemplateColumns: '1fr 1fr',
          gridTemplateRows: '1fr 1fr',
          gap: '1px',
          backgroundColor: '#444',
          borderRadius: '6px',
          overflow: 'hidden',
        }}
      >
        {/* Top-left: Away + Option A */}
        <QuadrantSection
          teamTone="away"
          optionKey="answer_a"
          titleTeam={game.away_team}
          titleOption={getOptionLabel('answer_a')}
          users={quadrants.awayA}
          TEAM_COLORS={TEAM_COLORS}
          OPTION_COLORS={OPTION_COLORS}
          compact
        />
        {/* Top-right: Home + Option A */}
        <QuadrantSection
          teamTone="home"
          optionKey="answer_a"
          titleTeam={game.home_team}
          titleOption={getOptionLabel('answer_a')}
          users={quadrants.homeA}
          TEAM_COLORS={TEAM_COLORS}
          OPTION_COLORS={OPTION_COLORS}
          compact
        />
        {/* Bottom-left: Away + Option B */}
        <QuadrantSection
          teamTone="away"
          optionKey="answer_b"
          titleTeam={game.away_team}
          titleOption={getOptionLabel('answer_b')}
          users={quadrants.awayB}
          TEAM_COLORS={TEAM_COLORS}
          OPTION_COLORS={OPTION_COLORS}
          compact
        />
        {/* Bottom-right: Home + Option B */}
        <QuadrantSection
          teamTone="home"
          optionKey="answer_b"
          titleTeam={game.home_team}
          titleOption={getOptionLabel('answer_b')}
          users={quadrants.homeB}
          TEAM_COLORS={TEAM_COLORS}
          OPTION_COLORS={OPTION_COLORS}
          compact
        />
      </div>

      <div className="mt-[10px] flex justify-between text-[11px]" style={{ color: '#666' }}>
        <span>{game.away_team}: {(picksByTeam.away_team || []).length}</span>
        <span>{game.home_team}: {(picksByTeam.home_team || []).length}</span>
      </div>
    </div>
  );
}

// --- Internal: One quadrant (box) ------------------------------

function HeaderTokens({ teamTone, optionKey, titleTeam, titleOption, TEAM_COLORS, OPTION_COLORS }) {
  const teamClass = TEAM_COLORS[teamTone] || '';
  const optClass = optionKey ? (OPTION_COLORS[optionKey] || '') : '';

  return (
    <div className="text-center leading-tight mb-[6px]">
      <div className="font-bold text-[clamp(0.95rem,1.2vw+0.6rem,1.1rem)]">
        <span className={teamClass}>{titleTeam}</span>
        {titleOption ? (
          <>
            <span className="mx-1" style={{ color: '#888' }}>•</span>
            <span className={optClass}>{titleOption}</span>
          </>
        ) : null}
      </div>
    </div>
  );
}

function QuadrantSection({
  teamTone,            // 'home' | 'away'
  optionKey,           // 'answer_a' | 'answer_b' | null
  titleTeam,
  titleOption,
  users,
  TEAM_COLORS,
  OPTION_COLORS,
  compact = false,
}) {
  const padding = compact ? '8px' : '12px';

  return (
    <div style={{ backgroundColor: '#2d2d2d', padding, minHeight: compact ? '60px' : '80px' }}>
      <HeaderTokens
        teamTone={teamTone}
        optionKey={optionKey}
        titleTeam={titleTeam}
        titleOption={titleOption}
        TEAM_COLORS={TEAM_COLORS}
        OPTION_COLORS={OPTION_COLORS}
      />

      <div
        className="flex flex-wrap gap-1 justify-center items-center"
        style={{ minHeight: compact ? '30px' : '40px' }}
      >
        {users.length === 0 ? (
          <span style={{ color: '#666', fontSize: '10px' }}>—</span>
        ) : (
          users.map((user) => (
            <UserAvatar key={user.username} user={user} size={compact ? 24 : 28} />
          ))
        )}
      </div>

      {!compact && (
        <div className="text-center mt-1" style={{ fontSize: '10px', color: '#666' }}>
          {users.length} pick{users.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
