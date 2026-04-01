/**
 * Screen 2: Live Match Tracker
 * Ball-by-ball win probability with chart, wicket/six markers, momentum panel.
 * Auto mode polls /api/live-feed every 15s. Manual mode lets user type score.
 */

import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api/client.js'
import ProbabilityBar from './ProbabilityBar.jsx'
import ProbabilityChart from './ProbabilityChart.jsx'

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

export default function LiveTracker() {
  const [mode, setMode] = useState('manual')   // 'auto' | 'manual'
  const [liveState, setLiveState] = useState(null)
  const [manual, setManual] = useState({
    batting_team: '', bowling_team: '', venue: '',
    current_score: '', wickets: '', balls_bowled: '', target: '',
    last6_runs: '', last6_wickets: '', dot_pct_last12: '',
    partnership_balls: '', last18_wickets: '', pp_vs_avg: '',
  })
  const [prediction, setPrediction] = useState(null)
  const [history, setHistory]       = useState([])   // ball-by-ball chart data
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState('')
  const [autoStatus, setAutoStatus] = useState('Polling...')
  const pollRef = useRef(null)

  // Auto mode: poll /api/live-feed every 15s
  useEffect(() => {
    if (mode !== 'auto') {
      if (pollRef.current) clearInterval(pollRef.current)
      return
    }
    const fetchLive = async () => {
      try {
        const state = await api.getLiveFeed()
        setLiveState(state)
        if (state.status === 'live' && state.current_score !== null) {
          setAutoStatus('Live')
          await runLivePrediction({
            batting_team: state.batting_team,
            bowling_team: state.bowling_team,
            current_score: state.current_score,
            wickets: state.wickets,
            balls_bowled: state.balls_bowled,
            target: state.target,
            venue: '',
          })
        } else if (state.status === 'no_live_match') {
          setAutoStatus('No live IPL match')
        } else {
          setAutoStatus('API unavailable')
        }
      } catch {
        setAutoStatus('Error fetching live data')
      }
    }
    fetchLive()
    pollRef.current = setInterval(fetchLive, 15000)
    return () => clearInterval(pollRef.current)
  }, [mode])

  const set = (k, v) => setManual(f => ({ ...f, [k]: v }))

  const runLivePrediction = async (data) => {
    if (!data.batting_team || !data.current_score || !data.target) return
    setLoading(true)
    setError('')
    try {
      const payload = {
        batting_team: data.batting_team,
        bowling_team: data.bowling_team || '',
        venue: data.venue || '',
        current_score: Number(data.current_score),
        wickets: Number(data.wickets || 0),
        balls_bowled: Number(data.balls_bowled || 0),
        target: Number(data.target),
        last6_runs:      data.last6_runs      ? Number(data.last6_runs)      : null,
        last6_wickets:   data.last6_wickets   ? Number(data.last6_wickets)   : null,
        dot_pct_last12:  data.dot_pct_last12  ? Number(data.dot_pct_last12)  : null,
        partnership_balls: data.partnership_balls ? Number(data.partnership_balls) : null,
        last18_wickets:  data.last18_wickets  ? Number(data.last18_wickets)  : null,
        pp_vs_avg:       data.pp_vs_avg       ? Number(data.pp_vs_avg)       : null,
      }
      const r = await api.predictLive(payload)
      setPrediction(r)

      // Add to chart history
      setHistory(prev => {
        const ball = payload.balls_bowled
        const existing = prev.findIndex(p => p.ball === ball)
        const point = {
          ball,
          prob: r.batting_team_win_prob,
          score: payload.current_score,
          wickets: payload.wickets,
          wicket: false,
          six: false,
        }
        if (existing >= 0) {
          const next = [...prev]
          next[existing] = point
          return next
        }
        return [...prev, point].sort((a, b) => a.ball - b.ball)
      })
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const markEvent = (type) => {
    setHistory(prev => {
      if (!prev.length) return prev
      const last = { ...prev[prev.length - 1], [type]: true }
      return [...prev.slice(0, -1), last]
    })
  }

  const reset = () => {
    setPrediction(null)
    setHistory([])
    setError('')
  }

  const canPredict = manual.batting_team && manual.current_score && manual.target

  const situationColor = {
    comfortable:    '#22c55e',
    'evenly poised':'#f59e0b',
    'under pressure':'#f97316',
    critical:       '#ef4444',
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '0 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 800 }}>Live Match Tracker</h2>
        {/* Mode toggle */}
        <div style={{ display: 'flex', gap: 10 }}>
          {['manual', 'auto'].map(m => (
            <button key={m} onClick={() => setMode(m)} style={{
              padding: '8px 18px', borderRadius: '20px',
              border: `2px solid ${mode === m ? '#3b82f6' : '#334155'}`,
              background: mode === m ? '#1d4ed8' : '#1e2738',
              color: '#e2e8f0', cursor: 'pointer', fontWeight: 600,
              textTransform: 'capitalize', fontSize: 13,
            }}>
              {m === 'auto' ? `Auto ${mode === 'auto' ? '●' : '○'}` : 'Manual'}
            </button>
          ))}
        </div>
      </div>

      {mode === 'auto' && (
        <div style={{ ...card, border: '1px solid #334155' }}>
          <p style={{ color: '#94a3b8', fontSize: 13 }}>
            Status: <span style={{ color: autoStatus === 'Live' ? '#22c55e' : '#f59e0b', fontWeight: 700 }}>{autoStatus}</span>
            {' '} · Polls CricAPI every 90s · Last updated: {liveState?.last_updated ? new Date(liveState.last_updated).toLocaleTimeString() : '—'}
          </p>
          {liveState?.match_title && (
            <p style={{ marginTop: 8, fontWeight: 600, color: '#60a5fa' }}>{liveState.match_title}</p>
          )}
        </div>
      )}

      {mode === 'manual' && (
        <div style={card}>
          <h3 style={{ marginBottom: 16, color: '#94a3b8', fontSize: 14, textTransform: 'uppercase' }}>
            Match State (2nd Innings)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
            <div>
              <label style={label}>Batting Team</label>
              <select value={manual.batting_team} onChange={e => set('batting_team', e.target.value)} style={inputStyle}>
                <option value="">Select...</option>
                {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label style={label}>Bowling Team</label>
              <select value={manual.bowling_team} onChange={e => set('bowling_team', e.target.value)} style={inputStyle}>
                <option value="">Select...</option>
                {TEAMS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
            {[
              ['Target', 'target', 'e.g. 185'],
              ['Score', 'current_score', 'e.g. 98'],
              ['Wickets', 'wickets', '0-10'],
              ['Balls Bowled', 'balls_bowled', '0-120'],
            ].map(([lbl, key, ph]) => (
              <div key={key}>
                <label style={label}>{lbl}</label>
                <input type="number" placeholder={ph} value={manual[key]} onChange={e => set(key, e.target.value)} style={inputStyle} />
              </div>
            ))}
          </div>

          {/* Momentum features — collapsible */}
          <details style={{ marginBottom: 14 }}>
            <summary style={{ cursor: 'pointer', color: '#60a5fa', fontSize: 13, marginBottom: 10 }}>
              Momentum Features (optional — improves accuracy)
            </summary>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 12 }}>
              {[
                ['Last 6 Balls Runs', 'last6_runs'],
                ['Last 6 Balls Wickets', 'last6_wickets'],
                ['Dot Ball % (last 12)', 'dot_pct_last12'],
                ['Partnership Balls', 'partnership_balls'],
                ['Wickets in Last 3 Overs', 'last18_wickets'],
                ['PP Score vs Avg', 'pp_vs_avg'],
              ].map(([lbl, key]) => (
                <div key={key}>
                  <label style={label}>{lbl}</label>
                  <input type="number" value={manual[key]} onChange={e => set(key, e.target.value)} style={inputStyle} step="0.01" />
                </div>
              ))}
            </div>
          </details>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={() => runLivePrediction(manual)}
              disabled={!canPredict || loading}
              style={{
                flex: 2, padding: '12px',
                background: !canPredict || loading ? '#334155' : 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                color: '#fff', border: 'none', borderRadius: '8px',
                fontSize: '15px', fontWeight: 700, cursor: !canPredict ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Predicting...' : 'Update Prediction'}
            </button>
            <button onClick={() => markEvent('wicket')} style={{
              flex: 1, padding: '12px', background: '#450a0a',
              color: '#fca5a5', border: '1px solid #ef4444', borderRadius: '8px',
              fontWeight: 700, cursor: 'pointer',
            }}>+ Wicket</button>
            <button onClick={() => markEvent('six')} style={{
              flex: 1, padding: '12px', background: '#451a03',
              color: '#fde68a', border: '1px solid #fbbf24', borderRadius: '8px',
              fontWeight: 700, cursor: 'pointer',
            }}>+ Six</button>
            <button onClick={reset} style={{
              flex: 1, padding: '12px', background: '#1e2738',
              color: '#94a3b8', border: '1px solid #334155', borderRadius: '8px',
              fontWeight: 700, cursor: 'pointer',
            }}>Reset</button>
          </div>
        </div>
      )}

      {error && (
        <div style={{ padding: 14, background: '#450a0a', borderRadius: 8, color: '#fca5a5', fontSize: 14, marginBottom: 16 }}>
          Error: {error}
        </div>
      )}

      {/* Live result */}
      {prediction && (
        <>
          <div style={{ ...card, border: '1px solid #1d4ed8' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <p style={{ color: '#94a3b8', fontSize: 12, textTransform: 'uppercase' }}>Live Win Probability</p>
                <p style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>
                  {prediction.current_score}/{prediction.wickets} · {Math.floor(prediction.balls_bowled / 6)}.{prediction.balls_bowled % 6} ov · Target {prediction.target}
                </p>
              </div>
              <div style={{
                padding: '6px 14px', borderRadius: '20px',
                background: (situationColor[prediction.match_situation] || '#94a3b8') + '22',
                color: situationColor[prediction.match_situation] || '#94a3b8',
                fontWeight: 700, fontSize: 13, textTransform: 'capitalize',
              }}>
                {prediction.match_situation}
              </div>
            </div>

            <ProbabilityBar
              teamA={prediction.batting_team}
              teamB={prediction.bowling_team}
              probA={prediction.batting_team_win_prob}
              probB={prediction.bowling_team_win_prob}
            />

            {/* CRR / RRR panel */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 20 }}>
              {[
                ['Runs Needed', prediction.runs_remaining],
                ['Balls Left', prediction.balls_remaining],
                ['CRR', prediction.crr],
                ['RRR', prediction.rrr],
              ].map(([lbl, val]) => (
                <div key={lbl} style={{ background: '#1e2738', borderRadius: 8, padding: '12px', textAlign: 'center' }}>
                  <p style={{ color: '#64748b', fontSize: 11, textTransform: 'uppercase', marginBottom: 4 }}>{lbl}</p>
                  <p style={{ color: '#e2e8f0', fontSize: 20, fontWeight: 800 }}>{val}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Ball-by-ball chart */}
          <div style={card}>
            <h3 style={{ marginBottom: 16, color: '#94a3b8', fontSize: 14, textTransform: 'uppercase' }}>
              Win Probability Timeline
            </h3>
            <ProbabilityChart data={history} battingTeam={prediction.batting_team} />
          </div>
        </>
      )}
    </div>
  )
}
