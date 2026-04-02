import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'
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
const labelStyle  = { fontSize: 12, color: '#64748b', marginBottom: 6, display: 'block' }
const sectionTitle = { fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 16 }

const TEAMS = [
  'Chennai Super Kings','Delhi Capitals','Gujarat Titans','Kolkata Knight Riders',
  'Lucknow Super Giants','Mumbai Indians','Punjab Kings','Rajasthan Royals',
  'Royal Challengers Bengaluru','Sunrisers Hyderabad',
]

// ── Calibration chart tooltip ────────────────────────────────────────────────
const CalibTip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div style={{ background: '#0d1424', border: '1px solid #1a2235', padding: '10px 14px', borderRadius: 8, fontSize: 13 }}>
      <p style={{ color: '#94a3b8' }}>Predicted: {(d.predicted_prob * 100).toFixed(0)}%</p>
      <p style={{ color: '#60a5fa', fontWeight: 700 }}>Actual: {(d.actual_win_rate * 100).toFixed(0)}%</p>
      <p style={{ color: '#475569' }}>{d.count} predictions</p>
    </div>
  )
}

// ── Streak indicator ─────────────────────────────────────────────────────────
const Streak = ({ val }) => {
  if (val === 0) return <span style={{ color: '#475569' }}>—</span>
  const color = val > 0 ? '#22c55e' : '#ef4444'
  const label = val > 0 ? `W${val}` : `L${Math.abs(val)}`
  return <span style={{ color, fontWeight: 700, fontSize: 12 }}>{label}</span>
}

// ── Last 5 dots ──────────────────────────────────────────────────────────────
const Last5 = ({ results }) => (
  <div style={{ display: 'flex', gap: 3 }}>
    {results.map((r, i) => (
      <div key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: r ? '#22c55e' : '#ef4444' }} />
    ))}
    {Array(5 - results.length).fill(0).map((_, i) => (
      <div key={`e${i}`} style={{ width: 8, height: 8, borderRadius: '50%', background: '#1a2235' }} />
    ))}
  </div>
)

export default function AccuracyDashboard() {
  const [tab, setTab]         = useState('standings')   // 'standings' | 'accuracy' | 'log'
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
      setLogMsg('✓ Result logged. Model form stats updated for next prediction.')
      setTimeout(() => setLogMsg(''), 4000)
      load()
    } catch (e) { setLogMsg('Error: ' + e.message) }
  }

  // Calibration data — add perfect diagonal for reference
  const calibData = data?.calibration?.length
    ? [{ predicted_prob: 0, actual_win_rate: 0, count: 0, range: 'ideal' },
       ...data.calibration,
       { predicted_prob: 1, actual_win_rate: 1, count: 0, range: 'ideal' }]
    : []

  const tabStyle = (t) => ({
    padding: '10px 20px', background: 'none',
    border: 'none',
    borderBottom: `2px solid ${tab === t ? '#3b82f6' : 'transparent'}`,
    color: tab === t ? '#e2e8f0' : '#475569',
    cursor: 'pointer', fontWeight: tab === t ? 600 : 400, fontSize: 14,
  })

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, color: '#f1f5f9', marginBottom: 4 }}>Accuracy Dashboard</h2>
        <p style={{ fontSize: 13, color: '#475569' }}>Track predictions and live 2026 season standings</p>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid #1a2235', marginBottom: 20 }}>
        {[['standings','🏆 Standings'], ['accuracy','📊 Accuracy'], ['log','+ Log Result']].map(([t, lbl]) => (
          <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>{lbl}</button>
        ))}
      </div>

      {loading ? (
        <div style={{ ...card, textAlign: 'center', color: '#334155', padding: 40 }}>Loading...</div>
      ) : (
        <>
          {/* ── STANDINGS TAB ────────────────────────────────────────────── */}
          {tab === 'standings' && (
            <div style={card}>
              <div style={sectionTitle}>IPL 2026 Points Table</div>
              {standings?.table && standings.table.some(t => t.matches > 0) ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      {['#','Team','M','W','L','Pts','Last 5','Streak'].map(h => (
                        <th key={h} style={{ padding: '8px 10px', textAlign: h === 'Team' ? 'left' : 'center', color: '#334155', fontWeight: 600, borderBottom: '1px solid #1a2235', whiteSpace: 'nowrap' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {standings.table.map((row, i) => (
                      <tr key={row.team} style={{ borderBottom: '1px solid #0d1424', opacity: row.matches === 0 ? 0.35 : 1 }}>
                        <td style={{ padding: '11px 10px', textAlign: 'center', color: i < 4 ? '#22c55e' : '#475569', fontWeight: 700 }}>{i + 1}</td>
                        <td style={{ padding: '11px 10px', color: '#e2e8f0', fontWeight: 500 }}>{row.team}</td>
                        <td style={{ padding: '11px 10px', textAlign: 'center', color: '#94a3b8' }}>{row.matches}</td>
                        <td style={{ padding: '11px 10px', textAlign: 'center', color: '#22c55e' }}>{row.wins}</td>
                        <td style={{ padding: '11px 10px', textAlign: 'center', color: '#ef4444' }}>{row.losses}</td>
                        <td style={{ padding: '11px 10px', textAlign: 'center', color: '#f1f5f9', fontWeight: 700 }}>{row.points}</td>
                        <td style={{ padding: '11px 10px', textAlign: 'center' }}><Last5 results={row.last5} /></td>
                        <td style={{ padding: '11px 10px', textAlign: 'center' }}><Streak val={row.streak} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ textAlign: 'center', color: '#334155', padding: '40px 0' }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>🏏</div>
                  No 2026 matches logged yet.<br />
                  <span style={{ fontSize: 13 }}>Log your first result in the "Log Result" tab — standings update automatically.</span>
                </div>
              )}
            </div>
          )}

          {/* ── ACCURACY TAB ─────────────────────────────────────────────── */}
          {tab === 'accuracy' && data && (
            <>
              {/* Stats row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
                {[
                  ['Predictions', data.total_predictions, '#60a5fa'],
                  ['Correct',     data.correct,            '#22c55e'],
                  ['Accuracy',    data.accuracy_percent || '—', '#f59e0b'],
                  ['Brier Score', data.brier_score != null ? data.brier_score.toFixed(3) : '—', '#a78bfa'],
                ].map(([lbl, val, color]) => (
                  <div key={lbl} style={{ ...card, textAlign: 'center', marginBottom: 0, border: `1px solid ${color}18` }}>
                    <div style={{ color, fontSize: 22, fontWeight: 800, marginBottom: 4 }}>{val}</div>
                    <div style={{ color: '#475569', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{lbl}</div>
                    {lbl === 'Brier Score' && <div style={{ color: '#334155', fontSize: 10, marginTop: 4 }}>lower = better (0=perfect)</div>}
                  </div>
                ))}
              </div>

              {/* Calibration chart */}
              {calibData.length > 2 ? (
                <div style={card}>
                  <div style={sectionTitle}>Calibration Curve</div>
                  <p style={{ fontSize: 12, color: '#334155', marginBottom: 16 }}>
                    Blue line should follow the grey diagonal — if our model says 70%, teams should win 70% of those games.
                  </p>
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={calibData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1a2235" />
                      <XAxis dataKey="predicted_prob" tickFormatter={v => `${(v*100).toFixed(0)}%`} stroke="#334155" tick={{ fill: '#475569', fontSize: 11 }} />
                      <YAxis tickFormatter={v => `${(v*100).toFixed(0)}%`} domain={[0, 1]} stroke="#334155" tick={{ fill: '#475569', fontSize: 11 }} />
                      <Tooltip content={<CalibTip />} />
                      {/* Perfect diagonal */}
                      <Line type="linear" dataKey="predicted_prob" stroke="#1e2d45" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Perfect" />
                      {/* Actual calibration */}
                      <Line type="monotone" dataKey="actual_win_rate" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6', r: 4 }} name="Model" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div style={{ ...card, textAlign: 'center', color: '#334155', padding: 30, fontSize: 13 }}>
                  Log predictions with win % to see calibration curve (needs 5+ entries with probability stored).
                </div>
              )}

              {/* Per-team accuracy */}
              {Object.keys(data.by_team).length > 0 && (
                <div style={card}>
                  <div style={sectionTitle}>Accuracy by Team</div>
                  {Object.entries(data.by_team).sort((a, b) => b[1].accuracy - a[1].accuracy).map(([team, stats]) => {
                    const color = stats.accuracy >= 0.65 ? '#22c55e' : stats.accuracy >= 0.5 ? '#f59e0b' : '#ef4444'
                    return (
                      <div key={team} style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 10 }}>
                        <span style={{ width: 190, fontSize: 13, color: '#94a3b8', flexShrink: 0 }}>{team}</span>
                        <div style={{ flex: 1, height: 6, background: '#0a0f1e', borderRadius: 4, overflow: 'hidden' }}>
                          <div style={{ height: '100%', borderRadius: 4, width: `${stats.accuracy * 100}%`, background: color, transition: 'width 0.7s ease' }} />
                        </div>
                        <span style={{ width: 90, fontSize: 12, color: '#64748b', textAlign: 'right', flexShrink: 0 }}>
                          {(stats.accuracy * 100).toFixed(0)}% <span style={{ color: '#334155' }}>({stats.correct}/{stats.total})</span>
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Recent predictions */}
              {data.recent.length > 0 && (
                <div style={card}>
                  <div style={sectionTitle}>Recent Predictions</div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr>
                        {['Date','Match','Predicted','Prob','Actual',''].map(h => (
                          <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: '#334155', fontWeight: 600, borderBottom: '1px solid #1a2235' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[...data.recent].reverse().map((r, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #0d1424' }}>
                          <td style={{ padding: '10px', color: '#475569' }}>{r.match_date}</td>
                          <td style={{ padding: '10px', color: '#64748b' }}>{r.team_a} vs {r.team_b}</td>
                          <td style={{ padding: '10px', color: '#60a5fa' }}>{r.predicted_winner}</td>
                          <td style={{ padding: '10px', color: '#94a3b8' }}>
                            {r.predicted_probability != null ? `${(r.predicted_probability * 100).toFixed(0)}%` : '—'}
                          </td>
                          <td style={{ padding: '10px', color: '#e2e8f0' }}>{r.actual_winner}</td>
                          <td style={{ padding: '10px' }}>
                            <span style={{ padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700, background: r.correct ? '#14532d' : '#450a0a', color: r.correct ? '#86efac' : '#fca5a5' }}>
                              {r.correct ? 'Correct' : 'Wrong'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {data.total_predictions === 0 && (
                <div style={{ ...card, textAlign: 'center', color: '#334155', padding: 40 }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>🏏</div>
                  No predictions logged yet.
                </div>
              )}
            </>
          )}

          {/* ── LOG RESULT TAB ───────────────────────────────────────────── */}
          {tab === 'log' && (
            <div style={card}>
              <div style={sectionTitle}>Log a Match Result</div>
              <p style={{ color: '#334155', fontSize: 12, marginBottom: 20 }}>
                After each IPL 2026 match — log the result. The model's form stats update automatically so the next prediction uses current 2026 form.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
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
                  <label style={labelStyle}>Our Predicted Win % (for calibration)</label>
                  <input type="number" min="0" max="100" value={logForm.predicted_probability} onChange={e => setL('predicted_probability', e.target.value)} style={inputStyle} placeholder="e.g. 67" />
                </div>
                <div style={{ gridColumn: '1/-1' }}>
                  <label style={labelStyle}>Actual Winner</label>
                  <select value={logForm.actual_winner} onChange={e => setL('actual_winner', e.target.value)} style={inputStyle}>
                    <option value="">Select...</option>
                    {[logForm.team_a, logForm.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <button onClick={logResult} style={{
                  padding: '11px 28px',
                  background: 'linear-gradient(90deg, #2563eb, #7c3aed)',
                  color: '#fff', border: 'none', borderRadius: '8px',
                  fontSize: '14px', fontWeight: 700, cursor: 'pointer',
                }}>
                  Log Result →
                </button>
                {logMsg && <span style={{ fontSize: 13, color: logMsg.startsWith('Error') ? '#fca5a5' : '#86efac' }}>{logMsg}</span>}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
