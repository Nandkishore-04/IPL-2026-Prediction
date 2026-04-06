export const TEAM_COLORS = {
  'Chennai Super Kings':         { primary: '#f5a623', secondary: '#1a3a5c' },
  'Mumbai Indians':              { primary: '#0078d7', secondary: '#c8a951' },
  'Royal Challengers Bengaluru': { primary: '#e8102a', secondary: '#1a1a1a' },
  'Kolkata Knight Riders':       { primary: '#6b21a8', secondary: '#d4a017' },
  'Delhi Capitals':              { primary: '#0057b8', secondary: '#ef3340' },
  'Sunrisers Hyderabad':         { primary: '#f4862a', secondary: '#1a1a1a' },
  'Rajasthan Royals':            { primary: '#e8315a', secondary: '#2563a8' },
  'Punjab Kings':                { primary: '#e73b3b', secondary: '#c0c0c0' },
  'Gujarat Titans':              { primary: '#1d7dbd', secondary: '#c9a84c' },
  'Lucknow Super Giants':        { primary: '#00b2e3', secondary: '#a72b8c' },
}

export function teamColor(name) {
  return TEAM_COLORS[name]?.primary ?? '#3b82f6'
}
