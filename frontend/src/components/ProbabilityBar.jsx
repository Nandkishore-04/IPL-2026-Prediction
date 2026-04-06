import { teamColor } from '../utils/teamColors.js'

export default function ProbabilityBar({ teamA, teamB, probA, probB }) {
  const pctA = Math.round(probA * 100)
  const pctB = Math.round(probB * 100)
  const aWins = pctA >= pctB
  const colorA = teamColor(teamA)
  const colorB = teamColor(teamB)

  return (
    <div style={{ margin: '8px 0 4px' }}>
      {/* Team names + big percentages */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 4, height: 36, borderRadius: 2,
            background: colorA, opacity: aWins ? 1 : 0.3,
            flexShrink: 0,
          }} />
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 2, fontWeight: 500 }}>{teamA}</div>
            <div style={{ fontSize: 34, fontWeight: 900, lineHeight: 1, color: aWins ? colorA : 'var(--text-muted)', letterSpacing: '-1px' }}>
              {pctA}<span style={{ fontSize: 18, fontWeight: 700, marginLeft: 1 }}>%</span>
            </div>
          </div>
        </div>

        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
          padding: '6px 14px', background: 'var(--bg)', borderRadius: 8,
          border: '1px solid var(--border)',
        }}>
          <span style={{ fontSize: 10, color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.1em' }}>WIN %</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>VS</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, textAlign: 'right' }}>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 2, fontWeight: 500 }}>{teamB}</div>
            <div style={{ fontSize: 34, fontWeight: 900, lineHeight: 1, color: !aWins ? colorB : 'var(--text-muted)', letterSpacing: '-1px' }}>
              {pctB}<span style={{ fontSize: 18, fontWeight: 700, marginLeft: 1 }}>%</span>
            </div>
          </div>
          <div style={{
            width: 4, height: 36, borderRadius: 2,
            background: colorB, opacity: !aWins ? 1 : 0.3,
            flexShrink: 0,
          }} />
        </div>

      </div>

      {/* Bar */}
      <div style={{ height: 10, borderRadius: 8, overflow: 'hidden', background: 'var(--bg)', display: 'flex' }}>
        <div style={{
          width: `${pctA}%`,
          background: colorA,
          transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
          opacity: aWins ? 1 : 0.45,
        }} />
        <div style={{
          width: `${pctB}%`,
          background: colorB,
          transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
          opacity: !aWins ? 1 : 0.45,
        }} />
      </div>
    </div>
  )
}
