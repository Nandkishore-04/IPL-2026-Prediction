import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client.js'
import ProbabilityBar from './ProbabilityBar.jsx'
import ProbabilityChart from './ProbabilityChart.jsx'

const card = {
  background: '#0d1424',
  borderRadius: '14px',
  padding: '22px 24px',
  marginBottom: '16px',
  border: '1px solid #1a2235',
}

const inputStyle = {
  width: '100%', padding: '10px 13px',
  background: '#0a0f1e', border: '1px solid #1e2d45',
  borderRadius: '8px', color: '#e2e8f0',
  fontSize: '14px', outline: 'none',
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

const situationColor = {
  comfortable: '#22c55e', 'evenly poised': '#f59e0b',
  'under pressure': '#f97316', critical: '#ef4444',
}

export default function LiveTracker() {
  const [mode, setMode]         = useState('manual')
  const [liveState, setLiveState] = useState(null)
  const [manual, setManual]     = useState({
    batting_team: '', bowling_team: '', venue: '',
    current_score: '', wickets: '', balls_bowled: '', target: '',
    last6_runs: '', last6_wickets: '', dot_pct_last12: '',
    partnership_balls: '', last18_wickets: '', pp_vs_avg: '',
  })
  const [prediction, setPrediction] = useState(null)
  const [history, setHistory]       = useState([])
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState('')
  const [autoStatus, setAutoStatus] = useState('Polling...')
  const pollRef = useRef(null)

  useEffect(() => {
    if (mode !== 'auto') { if (pollRef.current) clearInterval(pollRef.current); return }
    const fetchLive = async () => {
      try {
        const state = await api.getLiveFeed()
        setLiveState(state)
        if (state.status === 'live' && state.current_score !== null) {
          setAutoStatus('Live')
          await runLivePrediction({ ...state, venue: '' })
        } else {
          setAutoStatus(state.status === 'no_live_match' ? 'No live IPL match' : 'API unavailable')
        }
      } catch { setAutoStatus('Error fetching') }
    }
    fetchLive()
    pollRef.current = setInterval(fetchLive, 15000)
    return () => clearInterval(pollRef.current)
  }, [mode])

  const set = (k, v) => setManual(f => ({ ...f, [k]: v }))

  const runLivePrediction = async (data) => {
    if (!data.batting_team || !data.current_score || !data.target) return
    setLoading(true); setError('')
    try {
      const payload = {
        batting_team: data.batting_team, bowling_team: data.bowling_team || '',
        venue: data.venue || '', current_score: Number(data.current_score),
        wickets: Number(data.wickets || 0), balls_bowled: Number(data.balls_bowled || 0),
        target: Number(data.target),
        last6_runs:       data.last6_runs       ? Number(data.last6_runs)      : null,
        last6_wickets:    data.last6_wickets     ? Number(data.last6_wickets)   : null,
        dot_pct_last12:   data.dot_pct_last12    ? Number(data.dot_pct_last12)  : null,
        partnership_balls:data.partnership_balls ? Number(data.partnership_balls): null,
        last18_wickets:   data.last18_wickets    ? Number(data.last18_wickets)  : null,
        pp_vs_avg:        data.pp_vs_avg         ? Number(data.pp_vs_avg)       : null,
      }
      const r = await api.predictLive(payload)
      setPrediction(r)
      setHistory(prev => {
        const ball = payload.balls_bowled
        const point = { ball, prob: r.batting_team_win_prob, score: payload.current_score, wickets: payload.wickets, wicket: false, six: false }
        const idx = prev.findIndex(p => p.ball === ball)
        if (idx >= 0) { const n = [...prev]; n[idx] = point; return n }
        return [...prev, point].sort((a, b) => a.ball - b.ball)
      })
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  const markEvent = (type) => setHistory(prev => {
    if (!prev.length) return prev
    return [...prev.slice(0, -1), { ...prev[prev.length - 1], [type]: true }]
  })

  const reset = () => { setPrediction(null); setHistory([]); setError('') }

  const canPredict = manual.batting_team && manual.current_score && manual.target

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: '#f1f5f9', marginBottom: 4 }}>Live Match Tracker</h2>
          <p style={{ fontSize: 13, color: '#475569' }}>Ball-by-ball win probability — updates after every delivery</p>
        </div>
        {/* Mode toggle */}
        <div style={{ display: 'flex', background: '#0a0f1e', borderRadius: 8, padding: 3, border: '1px solid #1a2235' }}>
          {['manual', 'auto'].map(m => (
            <button key={m} onClick={() => setMode(m)} style={{
              padding: '7px 16px', borderRadius: 6,
              background: mode === m ? '#1e3a5f' : 'transparent',
              color: mode === m ? '#93c5fd' : '#475569',
              border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13,
              transition: 'all 0.15s', textTransform: 'capitalize',
            }}>
              {m === 'auto' ? '📡 Auto' : '✏️ Manual'}
            </button>
          ))}
        </div>
      </div>

      {/* Auto status */}
      {mode === 'auto' && (
        <div style={{ ...card, border: '1px solid #1e3a5f' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: autoStatus === 'Live' ? '#22c55e' : '#f59e0b', boxShadow: autoStatus === 'Live' ? '0 0 8px #22c55e' : 'none' }} />
            <span style={{ color: '#94a3b8', fontSize: 13 }}>
              {autoStatus}
              {liveState?.last_updated && ` · Updated ${new Date(liveState.last_updated).toLocaleTimeString()}`}
            </span>
          </div>
          {liveState?.match_title && <p style={{ marginTop: 10, fontWeight: 700, color: '#60a5fa', fontSize: 14 }}>{liveState.match_title}</p>}
        </div>
      )}

      {/* Manual input */}
      {mode === 'manual' && (
        <div style={card}>
          <div style={sectionTitle}>2nd Innings State</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
            {[['Batting Team', 'batting_team'], ['Bowling Team', 'bowling_team']].map(([lbl, key]) => (
              <div key={key}>
                <label style={labelStyle}>{lbl}</label>
                <select value={manual[key]} onChange={e => set(key, e.target.value)} style={inputStyle}>
                  <option value="">Select...</option>
                  {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
            {[['Target', 'target'], ['Score', 'current_score'], ['Wickets', 'wickets'], ['Balls Bowled', 'balls_bowled']].map(([lbl, key]) => (
              <div key={key}>
                <label style={labelStyle}>{lbl}</label>
                <input type="number" value={manual[key]} onChange={e => set(key, e.target.value)}
                  style={inputStyle} placeholder="0" />
              </div>
            ))}
          </div>

          <details>
            <summary style={{ cursor: 'pointer', color: '#3b82f6', fontSize: 13, marginBottom: 12, userSelect: 'none' }}>
              ▸ Momentum features (optional)
            </summary>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 12 }}>
              {[['Last 6 Runs', 'last6_runs'], ['Last 6 Wickets', 'last6_wickets'],
                ['Dot % Last 12', 'dot_pct_last12'], ['Partnership Balls', 'partnership_balls'],
                ['Wkts Last 3 Overs', 'last18_wickets'], ['PP vs Avg', 'pp_vs_avg']].map(([lbl, key]) => (
                <div key={key}>
                  <label style={labelStyle}>{lbl}</label>
                  <input type="number" step="0.01" value={manual[key]} onChange={e => set(key, e.target.value)} style={inputStyle} />
                </div>
              ))}
            </div>
          </details>

          <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
            <button onClick={() => runLivePrediction(manual)} disabled={!canPredict || loading} style={{
              flex: 3, padding: '12px',
              background: !canPredict || loading ? '#1a2235' : 'linear-gradient(90deg, #2563eb, #7c3aed)',
              color: !canPredict || loading ? '#334155' : '#fff',
              border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: 700,
              cursor: canPredict && !loading ? 'pointer' : 'not-allowed',
            }}>
              {loading ? 'Predicting...' : 'Update →'}
            </button>
            <button onClick={() => markEvent('wicket')} style={{
              flex: 1, padding: '12px', background: '#1a0505',
              color: '#fca5a5', border: '1px solid #7f1d1d', borderRadius: '8px', fontWeight: 700, cursor: 'pointer', fontSize: 13,
            }}>🎯 Wicket</button>
            <button onClick={() => markEvent('six')} style={{
              flex: 1, padding: '12px', background: '#1a1005',
              color: '#fde68a', border: '1px solid #78350f', borderRadius: '8px', fontWeight: 700, cursor: 'pointer', fontSize: 13,
            }}>6️⃣ Six</button>
            <button onClick={reset} style={{
              flex: 1, padding: '12px', background: '#0a0f1e',
              color: '#475569', border: '1px solid #1a2235', borderRadius: '8px', fontWeight: 600, cursor: 'pointer', fontSize: 13,
            }}>Reset</button>
          </div>
        </div>
      )}

      {error && (
        <div style={{ padding: '12px 16px', background: '#2d0a0a', borderRadius: 8, color: '#fca5a5', fontSize: 13, border: '1px solid #450a0a', marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* Live result */}
      {prediction && (
        <>
          <div style={{ ...card, border: '1px solid #1e3a5f' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>Live Probability</div>
                <div style={{ fontSize: 13, color: '#64748b' }}>
                  {prediction.current_score}/{prediction.wickets} &nbsp;·&nbsp;
                  {Math.floor(prediction.balls_bowled / 6)}.{prediction.balls_bowled % 6} ov &nbsp;·&nbsp;
                  Target {prediction.target}
                </div>
              </div>
              <div style={{
                padding: '6px 14px', borderRadius: 20, fontWeight: 700, fontSize: 12,
                background: (situationColor[prediction.match_situation] || '#94a3b8') + '18',
                border: `1px solid ${(situationColor[prediction.match_situation] || '#94a3b8')}40`,
                color: situationColor[prediction.match_situation] || '#94a3b8',
                textTransform: 'capitalize',
              }}>
                {prediction.match_situation}
              </div>
            </div>

            <ProbabilityBar
              teamA={prediction.batting_team} teamB={prediction.bowling_team}
              probA={prediction.batting_team_win_prob} probB={prediction.bowling_team_win_prob}
            />

            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginTop: 20 }}>
              {[['Runs Needed', prediction.runs_remaining], ['Balls Left', prediction.balls_remaining],
                ['CRR', prediction.crr], ['RRR', prediction.rrr]].map(([lbl, val]) => (
                <div key={lbl} style={{ background: '#0a0f1e', borderRadius: 8, padding: '12px 10px', textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 5 }}>{lbl}</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#e2e8f0' }}>{val}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Chart */}
          <div style={card}>
            <div style={sectionTitle}>Win Probability Timeline</div>
            <ProbabilityChart data={history} battingTeam={prediction.batting_team} />
          </div>
        </>
      )}
    </div>
  )
}
