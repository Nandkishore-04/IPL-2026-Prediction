import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../api/client.js'

const inputStyle = {
  width: '100%', padding: '11px 14px',
  background: 'var(--bg)', border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 10, color: 'var(--text)', fontSize: 14, outline: 'none',
  fontFamily: 'inherit', appearance: 'none',
}
const labelStyle = { fontSize: 12, color: 'var(--text-muted)', marginBottom: 7, display: 'block', fontWeight: 500 }

const TEAMS = [
  'Chennai Super Kings','Delhi Capitals','Gujarat Titans','Kolkata Knight Riders',
  'Lucknow Super Giants','Mumbai Indians','Punjab Kings','Rajasthan Royals',
  'Royal Challengers Bengaluru','Sunrisers Hyderabad',
]

const CalibTip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div style={{ background: '#0c1220', border: '1px solid rgba(255,255,255,0.1)', padding: '10px 14px', borderRadius: 8, fontSize: 13 }}>
      <p style={{ color: 'var(--text-muted)' }}>Predicted: {(d.predicted_prob * 100).toFixed(0)}%</p>
      <p style={{ color: '#60a5fa', fontWeight: 700 }}>Actual: {(d.actual_win_rate * 100).toFixed(0)}%</p>
      <p style={{ color: 'var(--text-dim)' }}>{d.count} predictions</p>
    </div>
  )
}

const Streak = ({ val }) => {
  if (val === 0) return <span style={{ color: 'var(--text-dim)' }}>—</span>
  const color = val > 0 ? '#22c55e' : '#ef4444'
  return (
    <span style={{
      color, fontWeight: 700, fontSize: 11,
      background: val > 0 ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
      padding: '2px 7px', borderRadius: 6,
    }}>
      {val > 0 ? `W${val}` : `L${Math.abs(val)}`}
    </span>
  )
}

const Last5 = ({ results }) => (
  <div style={{ display: 'flex', gap: 3 }}>
    {results.map((r, i) => (
      <div key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: r ? '#22c55e' : '#ef4444', boxShadow: r ? '0 0 4px rgba(34,197,94,0.5)' : 'none' }} />
    ))}
    {Array(5 - results.length).fill(0).map((_, i) => (
      <div key={`e${i}`} style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--text-dim)', opacity: 0.3 }} />
    ))}
  </div>
)

const positionColors = ['#f5a623', '#94a3b8', '#cd7f32']

export default function AccuracyDashboard() {
  const [tab, setTab]         = useState('standings')
  const [data, setData]       = useState(null)
  const [standings, setStandings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [logForm, setLogForm] = useState({
    match_id: '', team_a: '', team_b: '',
    predicted_winner: '', actual_winner: '',
    match_date: '', predicted_probability: '',
  })
  const [logMsg, setLogMsg] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [acc, st] = await Promise.all([api.getAccuracy(), fetch('/api/standings').then(r => r.json())])
      setData(acc)
      setStandings(st)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const setL = (k, v) => setLogForm(f => ({ ...f, [k]: v }))

  const logResult = async () => {
    try {
      const payload = {
        ...logForm,
        predicted_probability: logForm.predicted_probability ? parseFloat(logForm.predicted_probability) / 100 : null,
      }
      await api.logResult(payload)
      setLogMsg('Result logged — form stats updated.')
      setTimeout(() => setLogMsg(''), 4000)
      load()
    } catch (e) { setLogMsg('Error: ' + e.message) }
  }

  const calibData = data?.calibration?.length
    ? [{ predicted_prob: 0, actual_win_rate: 0, count: 0 },
       ...data.calibration,
       { predicted_prob: 1, actual_win_rate: 1, count: 0 }]
    : []

  const tabStyle = (t) => ({
    padding: '8px 18px', background: 'none',
    border: 'none',
    borderBottom: `2px solid ${tab === t ? '#3b82f6' : 'transparent'}`,
    color: tab === t ? 'var(--text)' : 'var(--text-muted)',
    cursor: 'pointer', fontWeight: tab === t ? 600 : 400, fontSize: 13,
    fontFamily: 'inherit', transition: 'color 0.15s',
  })

  return (
    <div>
      <h2 className="page-title">Season Dashboard</h2>
      <p className="page-sub">Live 2026 standings, model accuracy tracking, and result logging</p>

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
        {[['standings','🏆 Standings'], ['accuracy','📊 Accuracy'], ['log','+ Log Result']].map(([t, lbl]) => (
          <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>{lbl}</button>
        ))}
      </div>

      {loading ? (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 48 }}>Loading...</div>
      ) : (
        <>
          {/* ── STANDINGS ─────────────────────────────────────────────────── */}
          {tab === 'standings' && (
            <div className="card">
              <div className="section-label">IPL 2026 Points Table</div>
              {standings?.table && standings.table.some(t => t.matches > 0) ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      {['#','Team','M','W','L','Pts','Last 5','Streak'].map(h => (
                        <th key={h} style={{
                          padding: '8px 10px',
                          textAlign: h === 'Team' ? 'left' : 'center',
                          color: 'var(--text-dim)', fontWeight: 600, fontSize: 11,
                          borderBottom: '1px solid var(--border)',
                          textTransform: 'uppercase', letterSpacing: '0.07em',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {standings.table.map((row, i) => (
                      <tr key={row.team} style={{
                        borderBottom: '1px solid var(--border)',
                        opacity: row.matches === 0 ? 0.3 : 1,
                        background: i < 4 ? 'rgba(59,130,246,0.025)' : 'transparent',
                      }}>
                        <td style={{ padding: '12px 10px', textAlign: 'center' }}>
                          {i < 3 ? (
                            <span style={{ color: positionColors[i], fontWeight: 800, fontSize: 14 }}>
                              {i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'}
                            </span>
                          ) : (
                            <span style={{ color: i < 4 ? '#60a5fa' : 'var(--text-muted)', fontWeight: 700 }}>{i + 1}</span>
                          )}
                        </td>
                        <td style={{ padding: '12px 10px', color: 'var(--text)', fontWeight: 500 }}>
                          {row.team}
                          {i < 4 && <span style={{ marginLeft: 6, fontSize: 10, color: '#3b82f6', fontWeight: 600 }}>playoff</span>}
                        </td>
                        <td style={{ padding: '12px 10px', textAlign: 'center', color: 'var(--text-muted)' }}>{row.matches}</td>
                        <td style={{ padding: '12px 10px', textAlign: 'center', color: '#22c55e', fontWeight: 600 }}>{row.wins}</td>
                        <td style={{ padding: '12px 10px', textAlign: 'center', color: '#ef4444', fontWeight: 600 }}>{row.losses}</td>
                        <td style={{ padding: '12px 10px', textAlign: 'center', color: 'var(--text)', fontWeight: 800 }}>{row.points}</td>
                        <td style={{ padding: '12px 10px', textAlign: 'center' }}><Last5 results={row.last5} /></td>
                        <td style={{ padding: '12px 10px', textAlign: 'center' }}><Streak val={row.streak} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: 36, marginBottom: 14 }}>🏆</div>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>No matches logged yet</div>
                  <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>Log results in the "Log Result" tab — standings update automatically.</div>
                </div>
              )}
            </div>
          )}

          {/* ── ACCURACY ──────────────────────────────────────────────────── */}
          {tab === 'accuracy' && data && (
            <>
              <div className="grid-4" style={{ marginBottom: 16 }}>
                {[
                  { label: 'Total',      value: data.total_predictions,                                 color: '#60a5fa', icon: '🎯' },
                  { label: 'Correct',    value: data.correct,                                           color: '#22c55e', icon: '✓' },
                  { label: 'Accuracy',   value: data.accuracy_percent || '—',                           color: '#f59e0b', icon: '%' },
                  { label: 'Brier',      value: data.brier_score != null ? data.brier_score.toFixed(3) : '—', color: '#a78bfa', icon: '◈' },
                ].map(({ label, value, color, icon }) => (
                  <div key={label} className="card" style={{ textAlign: 'center', marginBottom: 0, padding: '18px 12px' }}>
                    <div style={{ fontSize: 11, color, marginBottom: 8, fontWeight: 700 }}>{icon}</div>
                    <div style={{ fontSize: 24, fontWeight: 900, color, letterSpacing: '-0.5px', marginBottom: 4 }}>{value}</div>
                    <div style={{ fontSize: 10.5, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>{label}</div>
                  </div>
                ))}
              </div>

              {calibData.length > 2 ? (
                <div className="card">
                  <div className="section-label">Calibration Curve</div>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 18 }}>
                    If the model says 70%, teams should win ~70% of those games. Blue = model, dashed = perfect.
                  </p>
                  <ResponsiveContainer width="100%" height={210}>
                    <LineChart data={calibData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="predicted_prob" tickFormatter={v => `${(v*100).toFixed(0)}%`} stroke="transparent" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                      <YAxis tickFormatter={v => `${(v*100).toFixed(0)}%`} domain={[0, 1]} stroke="transparent" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                      <Tooltip content={<CalibTip />} />
                      <Line type="linear" dataKey="predicted_prob" stroke="rgba(255,255,255,0.1)" strokeWidth={1} strokeDasharray="5 5" dot={false} />
                      <Line type="monotone" dataKey="actual_win_rate" stroke="#3b82f6" strokeWidth={2.5} dot={{ fill: '#3b82f6', r: 4, strokeWidth: 2, stroke: '#06090f' }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32, fontSize: 13 }}>
                  Log 5+ predictions with a win % to see the calibration curve.
                </div>
              )}

              {Object.keys(data.by_team).length > 0 && (
                <div className="card">
                  <div className="section-label">Accuracy by Team</div>
                  {Object.entries(data.by_team).sort((a, b) => b[1].accuracy - a[1].accuracy).map(([team, stats]) => {
                    const color = stats.accuracy >= 0.65 ? '#22c55e' : stats.accuracy >= 0.5 ? '#f59e0b' : '#ef4444'
                    return (
                      <div key={team} style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }}>
                        <span style={{ width: 200, fontSize: 13, color: 'var(--text-muted)', flexShrink: 0 }}>{team}</span>
                        <div style={{ flex: 1, height: 5, background: 'var(--bg)', borderRadius: 4, overflow: 'hidden' }}>
                          <div style={{ height: '100%', borderRadius: 4, width: `${stats.accuracy * 100}%`, background: color, transition: 'width 0.8s ease' }} />
                        </div>
                        <span style={{ width: 80, fontSize: 12, color: 'var(--text-muted)', textAlign: 'right', flexShrink: 0 }}>
                          {(stats.accuracy * 100).toFixed(0)}% <span style={{ color: 'var(--text-dim)' }}>({stats.correct}/{stats.total})</span>
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}

              {data.recent.length > 0 && (
                <div className="card">
                  <div className="section-label">Recent Predictions</div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr>
                        {['Date','Match','Predicted','Prob','Actual','Result',''].map(h => (
                          <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: 'var(--text-dim)', fontWeight: 600, fontSize: 11, borderBottom: '1px solid var(--border)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[...data.recent].reverse().map((r, i) => {
                        const hasPrediction = r.predicted_winner != null
                        const hasResult     = r.actual_winner != null
                        return (
                          <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                            <td style={{ padding: '11px 10px', color: 'var(--text-muted)' }}>{r.match_date}</td>
                            <td style={{ padding: '11px 10px', color: 'var(--text-muted)', fontSize: 12 }}>{r.team_a} vs {r.team_b}</td>
                            <td style={{ padding: '11px 10px', color: hasPrediction ? '#60a5fa' : 'var(--text-dim)', fontWeight: hasPrediction ? 500 : 400 }}>
                              {hasPrediction ? r.predicted_winner : '—'}
                            </td>
                            <td style={{ padding: '11px 10px', color: 'var(--text-muted)' }}>
                              {r.predicted_probability != null ? `${(r.predicted_probability * 100).toFixed(0)}%` : '—'}
                            </td>
                            <td style={{ padding: '11px 10px', color: 'var(--text)', fontWeight: 500 }}>
                              {hasResult ? r.actual_winner : '—'}
                            </td>
            <td style={{ padding: '11px 10px' }}>
              {!hasPrediction || !hasResult ? (
                <span style={{ color: 'var(--text-dim)', fontSize: 12 }}>—</span>
              ) : (r.actual_winner && (r.actual_winner.toLowerCase().includes('no result') || r.actual_winner.toLowerCase().includes('washout'))) ? (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                  background: 'rgba(255,255,255,0.05)', color: 'var(--text-dim)',
                  border: '1px solid rgba(255,255,255,0.1)', minWidth: 85, justifyContent: 'center'
                }}>
                   Washout
                </span>
              ) : (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                  background: r.correct ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                  color: r.correct ? '#4ade80' : '#f87171',
                  border: `1px solid ${r.correct ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)'}`,
                  minWidth: 85, justifyContent: 'center'
                }}>
                  {r.correct ? '✓ Correct' : '✘ Wrong'}
                </span>
              )}
            </td>
                            <td style={{ padding: '11px 10px' }}>
                              <button onClick={async () => {
                                await api.deletePrediction(r.match_id)
                                load()
                              }} style={{
                                background: 'none', border: '1px solid rgba(239,68,68,0.2)',
                                color: '#f87171', borderRadius: 6, padding: '3px 9px',
                                cursor: 'pointer', fontSize: 12, fontFamily: 'inherit',
                                transition: 'all 0.15s',
                              }} title="Delete entry">
                                ✕
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {data.total_predictions === 0 && (
                <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 48 }}>
                  <div style={{ fontSize: 36, marginBottom: 12 }}>📊</div>
                  <div style={{ fontWeight: 600 }}>No predictions logged yet</div>
                </div>
              )}
            </>
          )}

          {/* ── LOG RESULT ────────────────────────────────────────────────── */}
          {tab === 'log' && (
            <div className="card">
              <div className="section-label">Log a Match Result</div>
              <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 22, lineHeight: 1.6 }}>
                After each IPL 2026 match — log the result here. Team form stats update automatically so the next prediction uses current 2026 form.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                <div>
                  <label style={labelStyle}>Match ID</label>
                  <input value={logForm.match_id} onChange={e => setL('match_id', e.target.value)} style={inputStyle} placeholder="e.g. RCB-SRH-Match1" />
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
                  <label style={labelStyle}>Our Predicted Winner</label>
                  <select value={logForm.predicted_winner} onChange={e => setL('predicted_winner', e.target.value)} style={inputStyle}>
                    <option value="">Select...</option>
                    {[logForm.team_a, logForm.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Predicted Win % (for calibration)</label>
                  <input type="number" min="0" max="100" value={logForm.predicted_probability} onChange={e => setL('predicted_probability', e.target.value)} style={inputStyle} placeholder="e.g. 67" />
                </div>
                <div style={{ gridColumn: '1/-1' }}>
                  <label style={labelStyle}>Actual Winner</label>
                  <select value={logForm.actual_winner} onChange={e => setL('actual_winner', e.target.value)} style={inputStyle}>
                    <option value="">Select...</option>
                    {[logForm.team_a, logForm.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
                    <option value="No Result">No Result / Washout</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <button onClick={logResult} className="btn-primary" style={{ width: 'auto', padding: '11px 28px' }}>
                  Log Result →
                </button>
                {logMsg && (
                  <span style={{ fontSize: 13, color: logMsg.startsWith('Error') ? '#f87171' : '#4ade80', fontWeight: 500 }}>{logMsg}</span>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
