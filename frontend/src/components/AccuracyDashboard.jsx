import { useState, useEffect } from 'react'
import { api } from '../api/client.js'

const card = {
  background: '#0d1424', borderRadius: '14px',
  padding: '22px 24px', marginBottom: '16px', border: '1px solid #1a2235',
}

const inputStyle = {
  width: '100%', padding: '10px 13px',
  background: '#0a0f1e', border: '1px solid #1e2d45',
  borderRadius: '8px', color: '#e2e8f0', fontSize: '14px', outline: 'none',
}

const labelStyle = { fontSize: 12, color: '#64748b', marginBottom: 6, display: 'block' }

const sectionTitle = {
  fontSize: 11, fontWeight: 700, color: '#475569',
  textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 16,
}

const TEAMS = [
  'Chennai Super Kings','Delhi Capitals','Gujarat Titans','Kolkata Knight Riders',
  'Lucknow Super Giants','Mumbai Indians','Punjab Kings','Rajasthan Royals',
  'Royal Challengers Bengaluru','Sunrisers Hyderabad',
]

export default function AccuracyDashboard() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [logForm, setLogForm] = useState({ match_id:'', team_a:'', team_b:'', predicted_winner:'', actual_winner:'', match_date:'' })
  const [logMsg, setLogMsg]   = useState('')

  const load = async () => {
    setLoading(true)
    try { setData(await api.getAccuracy()) } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const setL = (k, v) => setLogForm(f => ({ ...f, [k]: v }))

  const logResult = async () => {
    try {
      await api.logResult(logForm)
      setLogMsg('✓ Logged successfully')
      setTimeout(() => setLogMsg(''), 3000)
      load()
    } catch (e) { setLogMsg('Error: ' + e.message) }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, color: '#f1f5f9', marginBottom: 4 }}>Accuracy Dashboard</h2>
        <p style={{ fontSize: 13, color: '#475569' }}>Track how well the model predicts real IPL 2026 matches</p>
      </div>

      {loading ? (
        <div style={{ ...card, textAlign: 'center', color: '#334155', padding: 40 }}>Loading...</div>
      ) : data && (
        <>
          {/* Stats cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 16 }}>
            {[
              ['Predictions', data.total_predictions, '#60a5fa', '🎯'],
              ['Correct',     data.correct,            '#22c55e', '✓'],
              ['Accuracy',    data.accuracy_percent || '—', '#f59e0b', '📈'],
            ].map(([lbl, val, color, icon]) => (
              <div key={lbl} style={{ ...card, textAlign: 'center', marginBottom: 0, border: `1px solid ${color}20` }}>
                <div style={{ fontSize: 18, marginBottom: 8 }}>{icon}</div>
                <div style={{ color, fontSize: 26, fontWeight: 800, lineHeight: 1, marginBottom: 6 }}>{val}</div>
                <div style={{ color: '#475569', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{lbl}</div>
              </div>
            ))}
          </div>

          {/* Per-team accuracy */}
          {Object.keys(data.by_team).length > 0 && (
            <div style={card}>
              <div style={sectionTitle}>Accuracy by Team</div>
              {Object.entries(data.by_team)
                .sort((a, b) => b[1].accuracy - a[1].accuracy)
                .map(([team, stats]) => {
                  const color = stats.accuracy >= 0.65 ? '#22c55e' : stats.accuracy >= 0.5 ? '#f59e0b' : '#ef4444'
                  return (
                    <div key={team} style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }}>
                      <span style={{ width: 180, fontSize: 13, color: '#94a3b8', flexShrink: 0 }}>{team}</span>
                      <div style={{ flex: 1, height: 6, background: '#0a0f1e', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ height: '100%', borderRadius: 4, width: `${stats.accuracy * 100}%`, background: color, transition: 'width 0.7s ease' }} />
                      </div>
                      <span style={{ width: 90, fontSize: 12, color: '#64748b', textAlign: 'right', flexShrink: 0 }}>
                        {(stats.accuracy * 100).toFixed(0)}%
                        <span style={{ color: '#334155' }}> ({stats.correct}/{stats.total})</span>
                      </span>
                    </div>
                  )
                })}
            </div>
          )}

          {/* Recent predictions table */}
          {data.recent.length > 0 && (
            <div style={card}>
              <div style={sectionTitle}>Recent Predictions</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      {['Date', 'Match', 'Predicted', 'Actual', ''].map(h => (
                        <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#334155', fontWeight: 600, borderBottom: '1px solid #1a2235' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.recent].reverse().map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #0d1424' }}>
                        <td style={{ padding: '11px 12px', color: '#475569' }}>{r.match_date}</td>
                        <td style={{ padding: '11px 12px', color: '#64748b' }}>{r.team_a} vs {r.team_b}</td>
                        <td style={{ padding: '11px 12px', color: '#60a5fa' }}>{r.predicted_winner}</td>
                        <td style={{ padding: '11px 12px', color: '#e2e8f0' }}>{r.actual_winner}</td>
                        <td style={{ padding: '11px 12px' }}>
                          <span style={{
                            padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
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
            <div style={{ ...card, textAlign: 'center', color: '#334155', padding: 40 }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🏏</div>
              No predictions logged yet.<br />
              <span style={{ fontSize: 13 }}>Make a prediction and log the result after the match to track accuracy.</span>
            </div>
          )}
        </>
      )}

      {/* Log result */}
      <div style={{ ...card, border: '1px solid #1e2d45' }}>
        <div style={sectionTitle}>Log a Match Result</div>
        <p style={{ color: '#334155', fontSize: 12, marginBottom: 16 }}>After a match ends, log the actual winner to track model accuracy.</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div>
            <label style={labelStyle}>Match ID</label>
            <input value={logForm.match_id} onChange={e => setL('match_id', e.target.value)} style={inputStyle} placeholder="e.g. MI-CSK-Apr15" />
          </div>
          <div>
            <label style={labelStyle}>Match Date</label>
            <input type="date" value={logForm.match_date} onChange={e => setL('match_date', e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Team A</label>
            <select value={logForm.team_a} onChange={e => setL('team_a', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Team B</label>
            <select value={logForm.team_b} onChange={e => setL('team_b', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Predicted Winner</label>
            <select value={logForm.predicted_winner} onChange={e => setL('predicted_winner', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {[logForm.team_a, logForm.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Actual Winner</label>
            <select value={logForm.actual_winner} onChange={e => setL('actual_winner', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {[logForm.team_a, logForm.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <button onClick={logResult} style={{
            padding: '11px 24px',
            background: 'linear-gradient(90deg, #2563eb, #7c3aed)',
            color: '#fff', border: 'none', borderRadius: '8px',
            fontSize: '14px', fontWeight: 700, cursor: 'pointer',
          }}>
            Log Result
          </button>
          {logMsg && <span style={{ fontSize: 13, color: logMsg.startsWith('Error') ? '#fca5a5' : '#86efac' }}>{logMsg}</span>}
        </div>
      </div>
    </div>
  )
}
