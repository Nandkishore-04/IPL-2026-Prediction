import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client.js'
import XiSelector from './XiSelector.jsx'
import ProbabilityChart from './ProbabilityChart.jsx'
import { teamColor, TEAM_COLORS } from '../utils/teamColors.js'

/* ── helpers ──────────────────────────────────────────────────────────────── */
const fmtOvers = (balls) => `${Math.floor(balls / 6)}.${balls % 6}`
const rrCalc   = (runs, balls) => balls > 0 ? ((runs / balls) * 6).toFixed(2) : '0.00'
const rrrCalc  = (need, left)  => left  > 0 ? ((need / left)  * 6).toFixed(2) : '—'

const situationColor = {
  comfortable:    '#22c55e',
  'evenly poised':'#f59e0b',
  'under pressure':'#f97316',
  critical:       '#ef4444',
}

/* ── sub-components ───────────────────────────────────────────────────────── */

function PhaseBar({ phase }) {
  const steps = ['Setup', '1st Innings', 'Live Chase']
  const idx   = { setup: 0, innings1: 1, chase: 2 }[phase]
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 28 }}>
      {steps.map((s, i) => (
        <div key={s} style={{ display: 'flex', alignItems: 'center', flex: i < steps.length - 1 ? 1 : 0 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5 }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: i < idx ? '#22c55e' : i === idx ? '#3b82f6' : 'var(--bg)',
              border: `2px solid ${i < idx ? '#22c55e' : i === idx ? '#3b82f6' : 'rgba(255,255,255,0.1)'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 800,
              color: i <= idx ? '#fff' : 'var(--text-dim)',
              transition: 'all 0.3s',
            }}>
              {i < idx ? '✓' : i + 1}
            </div>
            <span style={{ fontSize: 10, color: i === idx ? '#93c5fd' : 'var(--text-dim)', fontWeight: i === idx ? 700 : 400, whiteSpace: 'nowrap' }}>{s}</span>
          </div>
          {i < steps.length - 1 && (
            <div style={{ flex: 1, height: 2, background: i < idx ? '#22c55e' : 'rgba(255,255,255,0.06)', margin: '0 8px', marginBottom: 20, transition: 'background 0.3s' }} />
          )}
        </div>
      ))}
    </div>
  )
}

function MatchHeader({ match, onEdit, compact = false }) {
  const colorA = teamColor(match.teamA)
  const colorB = teamColor(match.teamB)
  return (
    <div style={{
      borderRadius: 14, overflow: 'hidden',
      border: '1px solid rgba(255,255,255,0.07)',
      marginBottom: 20,
    }}>
      {/* Color strip */}
      <div style={{ height: 3, background: `linear-gradient(90deg, ${colorA}, ${colorB})` }} />
      <div style={{
        background: 'var(--surface)', padding: compact ? '12px 18px' : '16px 20px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: colorA, margin: '0 auto 4px', boxShadow: `0 0 8px ${colorA}80` }} />
            <div style={{ fontSize: compact ? 12 : 14, fontWeight: 800, color: 'var(--text)' }}>{match.teamA}</div>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', fontWeight: 600 }}>VS</div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: colorB, margin: '0 auto 4px', boxShadow: `0 0 8px ${colorB}80` }} />
            <div style={{ fontSize: compact ? 12 : 14, fontWeight: 800, color: 'var(--text)' }}>{match.teamB}</div>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 3 }}>{match.venue?.split(',')[0]}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Toss: <span style={{ color: teamColor(match.tossWinner) }}>{match.tossWinner?.split(' ').pop()}</span>
            {' '}chose to <strong>{match.tossDecision}</strong>
          </div>
          {onEdit && (
            <button onClick={onEdit} style={{
              marginTop: 6, background: 'none', border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 6, color: 'var(--text-dim)', fontSize: 11, padding: '3px 10px',
              cursor: 'pointer', fontFamily: 'inherit',
            }}>Edit</button>
          )}
        </div>
      </div>
    </div>
  )
}

function SplitProb({ battingTeam, bowlingTeam, batProb }) {
  const bowlProb   = 1 - batProb
  const colorBat   = teamColor(battingTeam)
  const colorBowl  = teamColor(bowlingTeam)
  const batPct     = Math.round(batProb  * 100)
  const bowlPct    = Math.round(bowlProb * 100)
  const leader     = batProb >= 0.5 ? battingTeam : bowlingTeam
  const leaderColor= batProb >= 0.5 ? colorBat    : colorBowl

  return (
    <div>
      {/* Team labels + percentages */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 3 }}>Batting</div>
          <div style={{ fontSize: 32, fontWeight: 900, color: colorBat, letterSpacing: '-1px', lineHeight: 1 }}>{batPct}%</div>
          <div style={{ fontSize: 12, color: colorBat, fontWeight: 600 }}>{battingTeam}</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Win Probability</div>
          <div style={{
            padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700,
            background: `${leaderColor}18`, border: `1px solid ${leaderColor}40`, color: leaderColor,
          }}>{leader.split(' ').pop()} favoured</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 3 }}>Bowling</div>
          <div style={{ fontSize: 32, fontWeight: 900, color: colorBowl, letterSpacing: '-1px', lineHeight: 1 }}>{bowlPct}%</div>
          <div style={{ fontSize: 12, color: colorBowl, fontWeight: 600 }}>{bowlingTeam}</div>
        </div>
      </div>
      {/* Bar */}
      <div style={{ height: 10, borderRadius: 10, overflow: 'hidden', background: `${colorBowl}40`, display: 'flex' }}>
        <div style={{ width: `${batPct}%`, background: colorBat, transition: 'width 0.6s ease', borderRadius: '10px 0 0 10px' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
        <div style={{ height: 3, width: 3, borderRadius: '50%', background: colorBat }} />
        <div style={{ height: 3, width: 3, borderRadius: '50%', background: colorBowl }} />
      </div>
    </div>
  )
}

/* ── main component ───────────────────────────────────────────────────────── */
export default function LiveTracker() {
  const [teams,  setTeams]  = useState([])
  const [venues, setVenues] = useState([])
  const [squads, setSquads] = useState({})

  // Phase: 'setup' | 'innings1' | 'chase'
  const [phase, setPhase] = useState('setup')

  // Match context (locked after setup)
  const [match, setMatch] = useState({
    teamA: '', teamB: '', venue: '',
    tossWinner: '', tossDecision: 'bat',
    xiA: [], xiB: [],
    battingFirst: '', bowlingFirst: '',
  })

  // 1st innings
  const [inn1Score, setInn1Score]   = useState('')
  const [inn1Overs, setInn1Overs]   = useState('')

  // Chase state
  const [target,  setTarget]  = useState(null)
  const [chase,   setChase]   = useState({ score: '', wickets: '', balls: '' })

  // Prediction
  const [prediction, setPrediction] = useState(null)
  const [history,    setHistory]    = useState([])
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')

  useEffect(() => {
    api.getTeams().then(d => setTeams(d.teams)).catch(() => {})
    api.getVenues().then(d => setVenues(d.venues)).catch(() => {})
    api.getSquads().then(d => setSquads(d)).catch(() => {})
  }, [])

  // Derive batting first from toss
  const deriveBattingFirst = (m) => {
    if (!m.tossWinner || !m.teamA || !m.teamB) return { battingFirst: '', bowlingFirst: '' }
    const other = m.tossWinner === m.teamA ? m.teamB : m.teamA
    const battingFirst = m.tossDecision === 'bat' ? m.tossWinner : other
    const bowlingFirst = battingFirst === m.teamA ? m.teamB : m.teamA
    return { battingFirst, bowlingFirst }
  }

  const setM = (k, v) => setMatch(prev => {
    const next = { ...prev, [k]: v }
    if (['tossWinner','tossDecision','teamA','teamB'].includes(k)) {
      const { battingFirst, bowlingFirst } = deriveBattingFirst(next)
      return { ...next, battingFirst, bowlingFirst }
    }
    return next
  })

  const setTeamA = (v) => { setMatch(p => { const n = { ...p, teamA: v, tossWinner: '' }; return n }); }
  const setTeamB = (v) => { setMatch(p => { const n = { ...p, teamB: v, tossWinner: '' }; return n }); }

  const canStart = match.teamA && match.teamB && match.venue && match.tossWinner

  const startTracking = () => {
    const { battingFirst, bowlingFirst } = deriveBattingFirst(match)
    setMatch(p => ({ ...p, battingFirst, bowlingFirst }))
    setPhase('innings1')
    setPrediction(null)
    setHistory([])
  }

  const setTargetFromInn1 = () => {
    const t = parseInt(inn1Score) + 1
    setTarget(t)
    setChase({ score: '', wickets: '', balls: '' })
    setPrediction(null)
    setHistory([])
    setPhase('chase')
  }

  // Chase team = the team that DIDN'T bat first
  const chasingTeam  = match.bowlingFirst  // bowled in inn1 = bats in inn2
  const defendingTeam = match.battingFirst

  const updateLive = async () => {
    if (!chase.score || !target) return
    setLoading(true); setError('')
    try {
      const balls = parseInt(chase.balls || 0)
      const score = parseInt(chase.score)
      const wickets = parseInt(chase.wickets || 0)
      const r = await api.predictLive({
        batting_team: chasingTeam,
        bowling_team: defendingTeam,
        venue:        match.venue,
        current_score: score,
        wickets,
        balls_bowled: balls,
        target,
      })
      setPrediction(r)
      setHistory(prev => {
        const point = { ball: balls, prob: r.batting_team_win_prob, score, wickets, wicket: false, six: false }
        const idx = prev.findIndex(p => p.ball === balls)
        if (idx >= 0) { const n = [...prev]; n[idx] = point; return n }
        return [...prev, point].sort((a, b) => a.ball - b.ball)
      })
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  const resetMatch = () => {
    setPhase('setup')
    setPrediction(null)
    setHistory([])
    setTarget(null)
    setInn1Score(''); setInn1Overs('')
    setChase({ score: '', wickets: '', balls: '' })
    setMatch(p => ({ ...p, tossWinner: '', xiA: [], xiB: [] }))
  }

  const colorA = teamColor(match.teamA)
  const colorB = teamColor(match.teamB)

  /* ── render ─────────────────────────────────────────────────────────────── */
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 className="page-title">Live Match Tracker</h2>
        <p className="page-sub">Set up the match, track the innings, get ball-by-ball win probability</p>
      </div>

      <PhaseBar phase={phase} />

      {/* ── PHASE 1: SETUP ────────────────────────────────────────────────── */}
      {phase === 'setup' && (
        <>
          {/* Teams */}
          <div className="card">
            <div className="section-label">Teams</div>
            <div className="grid-2" style={{ gap: 12 }}>
              {/* Team A */}
              <div style={{ borderRadius: 10, border: `1px solid ${match.teamA ? colorA + '40' : 'rgba(255,255,255,0.06)'}`, padding: 14, background: match.teamA ? `${colorA}08` : 'transparent', transition: 'all 0.2s' }}>
                <label className="label">Team A</label>
                <select value={match.teamA} onChange={e => setTeamA(e.target.value)} className="input">
                  <option value="">Select team...</option>
                  {teams.filter(t => t !== match.teamB).map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                {match.teamA && <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: colorA, boxShadow: `0 0 6px ${colorA}` }} />
                  <span style={{ fontSize: 11, color: colorA, fontWeight: 600 }}>{match.teamA}</span>
                </div>}
              </div>
              {/* Team B */}
              <div style={{ borderRadius: 10, border: `1px solid ${match.teamB ? colorB + '40' : 'rgba(255,255,255,0.06)'}`, padding: 14, background: match.teamB ? `${colorB}08` : 'transparent', transition: 'all 0.2s' }}>
                <label className="label">Team B</label>
                <select value={match.teamB} onChange={e => setTeamB(e.target.value)} className="input">
                  <option value="">Select team...</option>
                  {teams.filter(t => t !== match.teamA).map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                {match.teamB && <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: colorB, boxShadow: `0 0 6px ${colorB}` }} />
                  <span style={{ fontSize: 11, color: colorB, fontWeight: 600 }}>{match.teamB}</span>
                </div>}
              </div>
            </div>
          </div>

          {/* Venue + Toss */}
          <div className="card">
            <div className="section-label">Venue & Toss</div>
            <div style={{ marginBottom: 14 }}>
              <label className="label">Venue</label>
              <select value={match.venue} onChange={e => setM('venue', e.target.value)} className="input">
                <option value="">Select venue...</option>
                {venues.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div className="grid-2">
              <div>
                <label className="label">Toss Winner</label>
                <select value={match.tossWinner} onChange={e => setM('tossWinner', e.target.value)} className="input" disabled={!match.teamA || !match.teamB}>
                  <option value="">Select...</option>
                  {[match.teamA, match.teamB].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Decision</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['bat','field'].map(d => (
                    <button key={d} onClick={() => setM('tossDecision', d)} style={{
                      flex: 1, padding: '11px 8px', borderRadius: 10, fontFamily: 'inherit',
                      border: `1px solid ${match.tossDecision === d ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.07)'}`,
                      background: match.tossDecision === d ? 'rgba(59,130,246,0.1)' : 'var(--bg)',
                      color: match.tossDecision === d ? '#93c5fd' : 'var(--text-muted)',
                      cursor: 'pointer', fontWeight: 600, fontSize: 13, transition: 'all 0.15s',
                    }}>{d === 'bat' ? '🏏 Bat' : '⚾ Field'}</button>
                  ))}
                </div>
              </div>
            </div>

            {/* Batting first derived display */}
            {match.battingFirst && (
              <div style={{ marginTop: 14, padding: '10px 14px', borderRadius: 10, background: `${teamColor(match.battingFirst)}10`, border: `1px solid ${teamColor(match.battingFirst)}30` }}>
                <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>Batting first: </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: teamColor(match.battingFirst) }}>{match.battingFirst}</span>
              </div>
            )}
          </div>

          {/* Playing XI (optional) */}
          <div className="card">
            <div className="section-label">
              Playing XI
              <span style={{ color: 'var(--text-dim)', textTransform: 'none', fontSize: 11, fontWeight: 400, marginLeft: 8 }}>— optional, improves prediction accuracy</span>
            </div>
            <div className="grid-2" style={{ alignItems: 'start' }}>
              <XiSelector team={match.teamA} squad={squads[match.teamA] || []} selected={match.xiA} onChange={v => setM('xiA', v)} />
              <XiSelector team={match.teamB} squad={squads[match.teamB] || []} selected={match.xiB} onChange={v => setM('xiB', v)} />
            </div>
          </div>

          <button className="btn-primary" onClick={startTracking} disabled={!canStart}>
            Start Live Tracking →
          </button>
        </>
      )}

      {/* ── PHASE 2: 1ST INNINGS ──────────────────────────────────────────── */}
      {phase === 'innings1' && (
        <>
          <MatchHeader match={match} onEdit={resetMatch} />

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: teamColor(match.battingFirst), boxShadow: `0 0 8px ${teamColor(match.battingFirst)}` }} />
              <div className="section-label" style={{ marginBottom: 0 }}>
                <span style={{ color: teamColor(match.battingFirst) }}>{match.battingFirst}</span>
                <span style={{ color: 'var(--text-dim)', fontWeight: 400, textTransform: 'none', fontSize: 12, marginLeft: 8 }}>batting first</span>
              </div>
            </div>

            <div className="grid-2" style={{ marginBottom: 20 }}>
              <div>
                <label className="label">Final Score</label>
                <input type="number" value={inn1Score} onChange={e => setInn1Score(e.target.value)}
                  className="input" placeholder="e.g. 185" style={{ fontSize: 22, fontWeight: 800, textAlign: 'center' }} />
              </div>
              <div>
                <label className="label">Overs Played</label>
                <input type="number" max="20" value={inn1Overs} onChange={e => setInn1Overs(e.target.value)}
                  className="input" placeholder="e.g. 20" style={{ fontSize: 22, fontWeight: 800, textAlign: 'center' }} />
              </div>
            </div>

            {inn1Score && (
              <div style={{ padding: '12px 16px', borderRadius: 10, background: `${teamColor(match.bowlingFirst)}10`, border: `1px solid ${teamColor(match.bowlingFirst)}30`, marginBottom: 16 }}>
                <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                  <span style={{ color: teamColor(match.bowlingFirst), fontWeight: 700 }}>{match.bowlingFirst}</span>
                  {' '}need <strong style={{ color: 'var(--text)', fontSize: 14 }}>{parseInt(inn1Score) + 1} runs</strong> to win
                </span>
              </div>
            )}

            <button className="btn-primary" onClick={setTargetFromInn1} disabled={!inn1Score}>
              Set Target & Start Chase →
            </button>
          </div>
        </>
      )}

      {/* ── PHASE 3: LIVE CHASE ───────────────────────────────────────────── */}
      {phase === 'chase' && (
        <>
          <MatchHeader match={match} compact />

          {/* Scoreboard */}
          <div style={{ borderRadius: 16, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.07)', marginBottom: 16 }}>
            {/* Batting team strip */}
            <div style={{ background: `linear-gradient(135deg, ${teamColor(chasingTeam)}20, ${teamColor(chasingTeam)}08)`, padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>CHASING</div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: teamColor(chasingTeam) }}>{chasingTeam}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 2 }}>TARGET</div>
                  <div style={{ fontSize: 36, fontWeight: 900, color: 'var(--text)', letterSpacing: '-1px', lineHeight: 1 }}>{target}</div>
                </div>
              </div>
            </div>

            {/* Score input row */}
            <div style={{ background: 'var(--surface)', padding: '16px 20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                {[['Score', 'score', '0'], ['Wickets', 'wickets', '0'], ['Balls Bowled', 'balls', '0']].map(([lbl, key, ph]) => (
                  <div key={key}>
                    <label className="label">{lbl}</label>
                    <input type="number" value={chase[key]} min="0"
                      onChange={e => setChase(p => ({ ...p, [key]: e.target.value }))}
                      className="input" placeholder={ph}
                      style={{ fontSize: 20, fontWeight: 800, textAlign: 'center' }} />
                  </div>
                ))}
              </div>

              {/* Quick stats derived from inputs */}
              {chase.score !== '' && chase.balls !== '' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 14 }}>
                  {[
                    ['Needed',    target - parseInt(chase.score || 0)],
                    ['Balls Left', 120 - parseInt(chase.balls  || 0)],
                    ['CRR',  rrCalc(parseInt(chase.score || 0), parseInt(chase.balls || 0))],
                    ['RRR',  rrrCalc(target - parseInt(chase.score || 0), 120 - parseInt(chase.balls || 0))],
                  ].map(([lbl, val]) => (
                    <div key={lbl} style={{ background: 'var(--bg)', borderRadius: 8, padding: '10px 8px', textAlign: 'center' }}>
                      <div style={{ fontSize: 9, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{lbl}</div>
                      <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)' }}>{val}</div>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                <button onClick={updateLive} disabled={!chase.score || loading} className="btn-primary" style={{ flex: 1 }}>
                  {loading ? 'Updating...' : 'Update Prediction →'}
                </button>
                <button onClick={() => { setPrediction(null); setHistory([]); setChase({ score: '', wickets: '', balls: '' }) }} style={{
                  padding: '12px 18px', background: 'var(--bg)', border: '1px solid rgba(255,255,255,0.07)',
                  borderRadius: 12, color: 'var(--text-muted)', cursor: 'pointer', fontWeight: 600, fontSize: 13, fontFamily: 'inherit',
                }}>Reset</button>
                <button onClick={resetMatch} style={{
                  padding: '12px 18px', background: 'var(--bg)', border: '1px solid rgba(255,255,255,0.07)',
                  borderRadius: 12, color: 'var(--text-dim)', cursor: 'pointer', fontSize: 13, fontFamily: 'inherit',
                }}>New Match</button>
              </div>
            </div>
          </div>

          {error && (
            <div style={{ padding: '12px 16px', background: 'rgba(239,68,68,0.08)', borderRadius: 10, color: '#fca5a5', fontSize: 13, border: '1px solid rgba(239,68,68,0.2)', marginBottom: 16 }}>
              {error}
            </div>
          )}

          {/* Live probability result */}
          {prediction && (
            <>
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                  <div className="section-label" style={{ marginBottom: 0 }}>Live Win Probability</div>
                  <div style={{
                    padding: '5px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                    background: (situationColor[prediction.match_situation] || '#94a3b8') + '18',
                    border: `1px solid ${(situationColor[prediction.match_situation] || '#94a3b8')}40`,
                    color: situationColor[prediction.match_situation] || '#94a3b8',
                    textTransform: 'capitalize',
                  }}>
                    {prediction.match_situation}
                  </div>
                </div>
                <SplitProb
                  battingTeam={chasingTeam}
                  bowlingTeam={defendingTeam}
                  batProb={prediction.batting_team_win_prob}
                />
              </div>

              {/* Chart */}
              {history.length > 1 && (
                <div className="card">
                  <div className="section-label">Win Probability Timeline</div>
                  <ProbabilityChart data={history} battingTeam={chasingTeam} />
                </div>
              )}
            </>
          )}

          {!prediction && (
            <div className="card" style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-dim)' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>📡</div>
              <div style={{ fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>Enter the current score and hit Update</div>
              <div style={{ fontSize: 12 }}>Win probability will appear here and update with each entry</div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
