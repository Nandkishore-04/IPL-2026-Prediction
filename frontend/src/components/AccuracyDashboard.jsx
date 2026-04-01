/**
 * Screen 3: Accuracy Dashboard
 * Shows past predictions vs actual results, overall accuracy, per-team breakdown.
 */

import React, { useState, useEffect } from 'react'
import { api } from '../api/client.js'

const card = {
  background: '#111827',
  borderRadius: '12px',
  padding: '24px',
  marginBottom: '20px',
  border: '1px solid #1e2738',
}

const inputStyle = {
  width: '100%',
  padding: '10px 14px',
  background: '#1e2738',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#e2e8f0',
  fontSize: '14px',
  outline: 'none',
}

const label = {
  fontSize: 12,
  color: '#94a3b8',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: 4,
  display: 'block',
}

const TEAMS = [
  'Chennai Super Kings', 'Delhi Capitals', 'Gujarat Titans',
  'Kolkata Knight Riders', 'Lucknow Super Giants', 'Mumbai Indians',
  'Punjab Kings', 'Rajasthan Royals', 'Royal Challengers Bengaluru',
  'Sunrisers Hyderabad',
]

export default function AccuracyDashboard() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [logForm, setLogForm] = useState({
    match_id: '', team_a: '', team_b: '',
    predicted_winner: '', actual_winner: '', match_date: '',
  })
  const [logMsg, setLogMsg] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const d = await api.getAccuracy()
      setData(d)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const setL = (k, v) => setLogForm(f => ({ ...f, [k]: v }))

  const logResult = async () => {
    try {
      await api.logResult(logForm)
      setLogMsg('Logged successfully!')
      setTimeout(() => setLogMsg(''), 3000)
      load()
    } catch (e) {
      setLogMsg('Error: ' + e.message)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '0 16px' }}>
      <h2 style={{ marginBottom: 20, fontSize: 22, fontWeight: 800 }}>Accuracy Dashboard</h2>

      {loading ? (
        <p style={{ color: '#475569' }}>Loading...</p>
      ) : data && (
        <>
          {/* Overall stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
            {[
              ['Total Predictions', data.total_predictions, '#60a5fa'],
              ['Correct', data.correct, '#22c55e'],
              ['Accuracy', data.accuracy_percent || '—', '#f59e0b'],
            ].map(([lbl, val, color]) => (
              <div key={lbl} style={{ ...card, textAlign: 'center', marginBottom: 0 }}>
                <p style={{ color: '#64748b', fontSize: 12, textTransform: 'uppercase', marginBottom: 8 }}>{lbl}</p>
                <p style={{ color, fontSize: 28, fontWeight: 800 }}>{val}</p>
              </div>
            ))}
          </div>

          {/* Per-team accuracy */}
          {Object.keys(data.by_team).length > 0 && (
            <div style={card}>
              <h3 style={{ marginBottom: 16, color: '#94a3b8', fontSize: 14, textTransform: 'uppercase' }}>Accuracy by Team</h3>
              {Object.entries(data.by_team)
                .sort((a, b) => b[1].accuracy - a[1].accuracy)
                .map(([team, stats]) => (
                  <div key={team} style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }}>
                    <span style={{ width: 200, fontSize: 13, color: '#cbd5e1' }}>{team}</span>
                    <div style={{ flex: 1, height: 8, background: '#1e2738', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: 4,
                        width: `${stats.accuracy * 100}%`,
                        background: stats.accuracy >= 0.65 ? '#22c55e' : stats.accuracy >= 0.5 ? '#f59e0b' : '#ef4444',
                        transition: 'width 0.6s ease',
                      }} />
                    </div>
                    <span style={{ width: 80, fontSize: 13, color: '#94a3b8', textAlign: 'right' }}>
                      {(stats.accuracy * 100).toFixed(0)}% ({stats.correct}/{stats.total})
                    </span>
                  </div>
                ))}
            </div>
          )}

          {/* Recent predictions */}
          {data.recent.length > 0 && (
            <div style={card}>
              <h3 style={{ marginBottom: 16, color: '#94a3b8', fontSize: 14, textTransform: 'uppercase' }}>Recent Predictions</h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1e2738' }}>
                      {['Date', 'Match', 'Predicted', 'Actual', 'Result'].map(h => (
                        <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#475569' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.recent].reverse().map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #111827' }}>
                        <td style={{ padding: '10px 12px', color: '#64748b' }}>{r.match_date}</td>
                        <td style={{ padding: '10px 12px', color: '#94a3b8' }}>{r.team_a} vs {r.team_b}</td>
                        <td style={{ padding: '10px 12px', color: '#60a5fa' }}>{r.predicted_winner}</td>
                        <td style={{ padding: '10px 12px', color: '#e2e8f0' }}>{r.actual_winner}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{
                            padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 700,
                            background: r.correct ? '#14532d' : '#450a0a',
                            color: r.correct ? '#86efac' : '#fca5a5',
                          }}>
                            {r.correct ? 'Correct' : 'Wrong'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data.total_predictions === 0 && (
            <div style={{ ...card, textAlign: 'center', color: '#475569', padding: 40 }}>
              No predictions logged yet. Make a prediction and log the result after the match ends.
            </div>
          )}
        </>
      )}

      {/* Log a result */}
      <div style={{ ...card, border: '1px solid #334155' }}>
        <h3 style={{ marginBottom: 16, color: '#94a3b8', fontSize: 14, textTransform: 'uppercase' }}>
          Log Match Result
        </h3>
        <p style={{ color: '#475569', fontSize: 12, marginBottom: 16 }}>
          After a match ends, log the actual result to track model accuracy.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={label}>Match ID (any unique string)</label>
            <input value={logForm.match_id} onChange={e => setL('match_id', e.target.value)} style={inputStyle} placeholder="e.g. MI-CSK-2026-04-15" />
          </div>
          <div>
            <label style={label}>Match Date</label>
            <input type="date" value={logForm.match_date} onChange={e => setL('match_date', e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={label}>Team A</label>
            <select value={logForm.team_a} onChange={e => setL('team_a', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={label}>Team B</label>
            <select value={logForm.team_b} onChange={e => setL('team_b', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={label}>Predicted Winner</label>
            <select value={logForm.predicted_winner} onChange={e => setL('predicted_winner', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {[logForm.team_a, logForm.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={label}>Actual Winner</label>
            <select value={logForm.actual_winner} onChange={e => setL('actual_winner', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {[logForm.team_a, logForm.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={logResult}
          style={{
            marginTop: 16, padding: '12px 24px',
            background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
            color: '#fff', border: 'none', borderRadius: '8px',
            fontSize: '14px', fontWeight: 700, cursor: 'pointer',
          }}
        >
          Log Result
        </button>
        {logMsg && (
          <p style={{ marginTop: 10, color: logMsg.startsWith('Error') ? '#fca5a5' : '#86efac', fontSize: 13 }}>
            {logMsg}
          </p>
        )}
      </div>
    </div>
  )
}
