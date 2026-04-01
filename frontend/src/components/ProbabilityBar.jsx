/**
 * ProbabilityBar — animated dual-team probability bar.
 * Shows team A (blue) vs team B (orange) probability side by side.
 */

import React from 'react'

const styles = {
  container: {
    margin: '20px 0',
  },
  labels: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '8px',
    fontSize: '14px',
  },
  teamName: {
    fontWeight: 600,
    maxWidth: '45%',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  bar: {
    height: '36px',
    display: 'flex',
    borderRadius: '8px',
    overflow: 'hidden',
    background: '#1e2738',
  },
  segA: (pct) => ({
    width: `${pct}%`,
    background: 'linear-gradient(90deg, #3b82f6, #2563eb)',
    transition: 'width 0.8s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px',
    fontWeight: 700,
    color: '#fff',
    minWidth: pct > 8 ? '50px' : '0',
  }),
  segB: (pct) => ({
    width: `${pct}%`,
    background: 'linear-gradient(90deg, #f97316, #ea580c)',
    transition: 'width 0.8s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px',
    fontWeight: 700,
    color: '#fff',
    minWidth: pct > 8 ? '50px' : '0',
  }),
  percents: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '6px',
    fontSize: '22px',
    fontWeight: 800,
  },
  pA: { color: '#60a5fa' },
  pB: { color: '#fb923c' },
}

export default function ProbabilityBar({ teamA, teamB, probA, probB }) {
  const pctA = Math.round(probA * 100)
  const pctB = Math.round(probB * 100)

  return (
    <div style={styles.container}>
      <div style={styles.labels}>
        <span style={styles.teamName}>{teamA}</span>
        <span style={styles.teamName}>{teamB}</span>
      </div>
      <div style={styles.bar}>
        <div style={styles.segA(pctA)}>{pctA > 10 ? `${pctA}%` : ''}</div>
        <div style={styles.segB(pctB)}>{pctB > 10 ? `${pctB}%` : ''}</div>
      </div>
      <div style={styles.percents}>
        <span style={styles.pA}>{pctA}%</span>
        <span style={styles.pB}>{pctB}%</span>
      </div>
    </div>
  )
}
