import { teamColor } from '../utils/teamColors.js'

export default function TeamSelector({ label, value, onChange, teams, exclude }) {
  const available = teams.filter(t => t !== exclude)
  const color = value ? teamColor(value) : null

  return (
    <div>
      <label className="label">{label}</label>
      <div style={{ position: 'relative' }}>
        {color && (
          <div style={{
            position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
            width: 8, height: 8, borderRadius: '50%', background: color,
            pointerEvents: 'none', zIndex: 1,
          }} />
        )}
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          className="input"
          style={{
            paddingLeft: color ? 28 : 14,
            border: `1px solid ${color ? color + '50' : 'rgba(255,255,255,0.08)'}`,
            cursor: 'pointer',
            transition: 'border-color 0.2s',
          }}
        >
          <option value="">Select team...</option>
          {available.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
    </div>
  )
}
