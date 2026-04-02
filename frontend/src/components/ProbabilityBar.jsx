import React from 'react'

export default function ProbabilityBar({ teamA, teamB, probA, probB }) {
  const pctA = Math.round(probA * 100)
  const pctB = Math.round(probB * 100)
  const aWins = pctA >= pctB

  return (
    <div style={{ margin: '20px 0' }}>
      {/* Team names + percentages */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 3 }}>{teamA}</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: aWins ? '#60a5fa' : '#94a3b8', lineHeight: 1 }}>
            {pctA}%
          </div>
        </div>
        <div style={{ fontSize: 12, color: '#334155', fontWeight: 600, letterSpacing: '0.05em' }}>VS</div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 3 }}>{teamB}</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: !aWins ? '#f97316' : '#94a3b8', lineHeight: 1 }}>
            {pctB}%
          </div>
        </div>
      </div>

      {/* Bar */}
      <div style={{ height: 12, borderRadius: 8, overflow: 'hidden', background: '#0f172a', display: 'flex' }}>
        <div style={{
          width: `${pctA}%`,
          background: 'linear-gradient(90deg, #2563eb, #3b82f6)',
          transition: 'width 0.9s cubic-bezier(0.4,0,0.2,1)',
          borderRadius: '8px 0 0 8px',
        }} />
        <div style={{
          width: `${pctB}%`,
          background: 'linear-gradient(90deg, #f97316, #ea580c)',
          transition: 'width 0.9s cubic-bezier(0.4,0,0.2,1)',
          borderRadius: '0 8px 8px 0',
        }} />
      </div>
    </div>
  )
}
