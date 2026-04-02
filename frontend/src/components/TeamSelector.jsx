const TEAM_COLORS = {
  'Chennai Super Kings':         '#d4a017',
  'Mumbai Indians':              '#0057a8',
  'Royal Challengers Bengaluru': '#c8102e',
  'Kolkata Knight Riders':       '#6b21a8',
  'Delhi Capitals':              '#0078bc',
  'Sunrisers Hyderabad':         '#e87722',
  'Rajasthan Royals':            '#e8315a',
  'Punjab Kings':                '#c41e3a',
  'Gujarat Titans':              '#1b4f72',
  'Lucknow Super Giants':        '#29a8e0',
}

export default function TeamSelector({ label, value, onChange, teams, exclude }) {
  const available = teams.filter(t => t !== exclude)
  const color = TEAM_COLORS[value]

  return (
    <div>
      <label style={{ fontSize: 12, color: '#64748b', marginBottom: 6, display: 'block' }}>{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          width: '100%',
          padding: '10px 13px',
          background: '#0a0f1e',
          border: `1px solid ${color ? color + '80' : '#1e2d45'}`,
          borderRadius: '8px',
          color: color ? '#e2e8f0' : '#64748b',
          fontSize: '14px',
          cursor: 'pointer',
          outline: 'none',
          transition: 'border-color 0.2s',
        }}
      >
        <option value="">Select team...</option>
        {available.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
    </div>
  )
}
