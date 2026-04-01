/**
 * TeamSelector — dropdown for selecting an IPL team.
 */

import React from 'react'

const TEAM_COLORS = {
  'Chennai Super Kings':       '#f5d000',
  'Mumbai Indians':            '#004ba0',
  'Royal Challengers Bengaluru': '#c8102e',
  'Kolkata Knight Riders':     '#3a225d',
  'Delhi Capitals':            '#0078bc',
  'Sunrisers Hyderabad':       '#f7a721',
  'Rajasthan Royals':          '#e8315a',
  'Punjab Kings':              '#ed1b24',
  'Gujarat Titans':            '#1b4f72',
  'Lucknow Super Giants':      '#a0e4ff',
}

const selectStyle = (team) => ({
  width: '100%',
  padding: '10px 14px',
  background: '#1e2738',
  border: `2px solid ${team ? (TEAM_COLORS[team] || '#334155') : '#334155'}`,
  borderRadius: '8px',
  color: '#e2e8f0',
  fontSize: '14px',
  cursor: 'pointer',
  outline: 'none',
})

export default function TeamSelector({ label, value, onChange, teams, exclude }) {
  const available = teams.filter(t => t !== exclude)
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: 'block', marginBottom: 6, fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </label>
      <select value={value} onChange={e => onChange(e.target.value)} style={selectStyle(value)}>
        <option value="">Select team...</option>
        {available.map(t => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
    </div>
  )
}
