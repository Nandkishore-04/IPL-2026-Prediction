import { useState } from 'react'
import { teamColor } from '../utils/teamColors.js'

const roleIcon = { Batter: '🏏', Bowler: '⚾', 'All Rounder': '⚡', 'Wicket Keeper': '🧤' }
const roleOrder = { Batter: 0, 'Wicket Keeper': 1, 'All Rounder': 2, Bowler: 3 }

export default function XiSelector({ team, squad, selected, onChange }) {
  const [search, setSearch] = useState('')
  const color = teamColor(team)

  const count = selected.length

  const sorted = squad
    .filter(p => !search || p.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const ro = (roleOrder[a.role] ?? 9) - (roleOrder[b.role] ?? 9)
      return ro !== 0 ? ro : a.name.localeCompare(b.name)
    })


  const toggle = (name) => {
    if (selected.includes(name)) {
      onChange(selected.filter(n => n !== name))
    } else if (count < 11) {
      onChange([...selected, name])
    }
  }

  const grouped = sorted.reduce((acc, p) => {
    const r = p.role || 'Other'
    if (!acc[r]) acc[r] = []
    acc[r].push(p)
    return acc
  }, {})

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: color, flexShrink: 0 }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>{team || 'Select a team'}</span>
        </div>
        <span style={{
          fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 10,
          background: count === 11 ? 'rgba(34,197,94,0.12)' : count > 0 ? `${color}18` : 'rgba(255,255,255,0.04)',
          color: count === 11 ? '#4ade80' : count > 0 ? color : 'var(--text-dim)',
          border: `1px solid ${count === 11 ? 'rgba(34,197,94,0.25)' : count > 0 ? color + '35' : 'transparent'}`,
          transition: 'all 0.2s',
        }}>
          {count}/11 selected
        </span>
      </div>

      {/* Search */}


      <div style={{ marginBottom: 10 }}>
        <input
          type="text"
          placeholder="Search players..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            width: '100%',
            padding: '8px 12px',
            borderRadius: 8,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: 'var(--text)',
            fontSize: 13,
            outline: 'none',
          }}
        />
      </div>

      {/* Player list */}

      {!team ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: 13, background: 'var(--bg)', borderRadius: 10, border: '1px dashed rgba(255,255,255,0.06)', minHeight: 200 }}>
          Select a team first
        </div>
      ) : (
        <div style={{ background: 'var(--bg)', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden', flex: 1 }}>
          {Object.entries(grouped).map(([role, players]) => (
            <div key={role}>
              <div style={{
                padding: '6px 12px', fontSize: 10, fontWeight: 700, color: 'var(--text-dim)',
                textTransform: 'uppercase', letterSpacing: '0.1em',
                background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.04)',
              }}>
                {roleIcon[role] || '·'} {role}s
              </div>
              {players.map((p) => {
                const isSelected = selected.includes(p.name)
                const isDisabled = !isSelected && count >= 11
                return (
                  <div
                    key={p.name}
                    onClick={() => !isDisabled && toggle(p.name)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '9px 12px',
                      cursor: isDisabled ? 'not-allowed' : 'pointer',
                      opacity: isDisabled ? 0.3 : 1,
                      background: isSelected ? `${color}14` : 'transparent',
                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                      transition: 'background 0.12s',
                    }}
                  >
                    {/* Checkbox */}
                    <div style={{
                      width: 16, height: 16, borderRadius: 4, flexShrink: 0,
                      border: `1.5px solid ${isSelected ? color : 'rgba(255,255,255,0.15)'}`,
                      background: isSelected ? color : 'transparent',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.15s',
                    }}>
                      {isSelected && <span style={{ color: '#fff', fontSize: 10, lineHeight: 1, fontWeight: 800 }}>✓</span>}
                    </div>

                    {/* Name */}
                    <span style={{
                      fontSize: 13, flex: 1,
                      color: isSelected ? 'var(--text)' : 'var(--text-muted)',
                      fontWeight: isSelected ? 600 : 400,
                    }}>
                      {p.name}
                      {p.is_captain && <span style={{ marginLeft: 5, fontSize: 9, color: color, fontWeight: 700, textTransform: 'uppercase' }}>C</span>}
                      {p.is_wicketkeeper && <span style={{ marginLeft: 4, fontSize: 9, color: '#94a3b8' }}>†</span>}
                    </span>

                    {/* Overseas badge */}
                    {p.is_overseas && (
                      <span style={{ fontSize: 9, color: 'var(--text-dim)', fontWeight: 600, background: 'rgba(255,255,255,0.05)', padding: '1px 5px', borderRadius: 4 }}>OS</span>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}




      {/* Selected summary */}
      {count > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {selected.map(name => (
            <span
              key={name}
              onClick={() => toggle(name)}
              style={{
                fontSize: 11, padding: '2px 8px', borderRadius: 6,
                background: `${color}18`, border: `1px solid ${color}30`,
                color: color, cursor: 'pointer', fontWeight: 500,
              }}
              title="Click to remove"
            >
              {name} ×
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
