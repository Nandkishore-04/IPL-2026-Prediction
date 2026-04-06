import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import TeamSelector from './TeamSelector.jsx'
import ProbabilityBar from './ProbabilityBar.jsx'
import XiSelector from './XiSelector.jsx'
import { teamColor } from '../utils/teamColors.js'

const confidenceColor = { High: '#22c55e', Medium: '#f59e0b', Low: '#ef4444' }

export default function PreMatchPredictor() {
  const [teams, setTeams]   = useState([])
  const [venues, setVenues] = useState([])
  const [squads, setSquads] = useState({})
  const [form, setForm]     = useState({
    team_a: '', team_b: '', venue: '',
    toss_winner: '', toss_decision: 'bat',
  })
  const [xiA, setXiA] = useState([])
  const [xiB, setXiB] = useState([])
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [saved, setSaved]     = useState(false)
  const [matchDate, setMatchDate] = useState(() => new Date().toISOString().slice(0, 10))

  useEffect(() => {
    api.getTeams().then(d => setTeams(d.teams)).catch(() => {})
    api.getVenues().then(d => setVenues(d.venues)).catch(() => {})
    api.getSquads().then(d => setSquads(d)).catch(() => {})
  }, [])

  // Clear XI when team changes
  const setTeamA = (v) => { setForm(f => ({ ...f, team_a: v, toss_winner: '' })); setXiA([]) }
  const setTeamB = (v) => { setForm(f => ({ ...f, team_b: v, toss_winner: '' })); setXiB([]) }
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const canPredict = form.team_a && form.team_b && form.venue && form.toss_winner

  const predict = async () => {
    setLoading(true); setError(''); setSaved(false)
    try {
      const r = await api.predictMatch({
        team_a: form.team_a, team_b: form.team_b, venue: form.venue,
        toss_winner: form.toss_winner, toss_decision: form.toss_decision,
        team_a_xi: xiA, team_b_xi: xiB,
        match_date: matchDate,
      })
      setResult(r)
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  const savePrediction = async () => {
    try {
      await api.predictMatch({
        team_a: form.team_a, team_b: form.team_b, venue: form.venue,
        toss_winner: form.toss_winner, toss_decision: form.toss_decision,
        team_a_xi: xiA, team_b_xi: xiB,
        match_date: matchDate,
      })
      setSaved(true)
    } catch (e) { setError(e.message) }
  }

  const winnerColor = result ? teamColor(result.predicted_winner) : '#3b82f6'

  return (
    <div>
      <h2 className="page-title">Pre-Match Predictor</h2>
      <p className="page-sub">Select teams, venue, toss — then pick your Playing XI from the squad</p>

      {/* Match Setup */}
      <div className="card">
        <div className="section-label">Match Setup</div>
        <div className="grid-2" style={{ marginBottom: 14 }}>
          <TeamSelector label="Team A" value={form.team_a} onChange={setTeamA} teams={teams} exclude={form.team_b} />
          <TeamSelector label="Team B" value={form.team_b} onChange={setTeamB} teams={teams} exclude={form.team_a} />
        </div>
        <div className="grid-2">
          <div>
            <label className="label">Venue</label>
            <select value={form.venue} onChange={e => set('venue', e.target.value)} className="input">
              <option value="">Select venue...</option>
              {venues.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Match Date</label>
            <input type="date" value={matchDate} onChange={e => { setMatchDate(e.target.value); setSaved(false) }} className="input" />
          </div>
        </div>
      </div>

      {/* Toss */}
      <div className="card">
        <div className="section-label">Toss</div>
        <div className="grid-2">
          <div>
            <label className="label">Toss Winner</label>
            <select value={form.toss_winner} onChange={e => set('toss_winner', e.target.value)} className="input">
              <option value="">Select...</option>
              {[form.team_a, form.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Decision</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {['bat', 'field'].map(d => (
                <button key={d} onClick={() => set('toss_decision', d)} style={{
                  flex: 1, padding: '11px 8px', borderRadius: 10,
                  border: `1px solid ${form.toss_decision === d ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.07)'}`,
                  background: form.toss_decision === d ? 'rgba(59,130,246,0.1)' : 'var(--bg)',
                  color: form.toss_decision === d ? '#93c5fd' : 'var(--text-muted)',
                  cursor: 'pointer', fontWeight: 600, fontSize: 13,
                  transition: 'all 0.15s', fontFamily: 'inherit',
                }}>
                  {d === 'bat' ? '🏏 Bat' : '⚾ Field'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Playing XI */}
      <div className="card">
        <div className="section-label">
          Playing XI
          <span style={{ color: 'var(--text-dim)', textTransform: 'none', fontSize: 11, fontWeight: 400, marginLeft: 8 }}>
            — optional, select up to 11 from squad
          </span>
        </div>
        <div className="grid-2" style={{ alignItems: 'start' }}>
          <XiSelector
            team={form.team_a}
            squad={squads[form.team_a] || []}
            selected={xiA}
            onChange={setXiA}
          />
          <XiSelector
            team={form.team_b}
            squad={squads[form.team_b] || []}
            selected={xiB}
            onChange={setXiB}
          />
        </div>
      </div>

      {/* Predict button */}
      <button className="btn-primary" onClick={predict} disabled={!canPredict || loading}>
        {loading ? 'Analysing...' : 'Predict Winner →'}
      </button>

      {error && (
        <div style={{ marginTop: 14, padding: '12px 16px', background: 'rgba(239,68,68,0.08)', borderRadius: 10, color: '#fca5a5', fontSize: 13, border: '1px solid rgba(239,68,68,0.2)' }}>
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ marginTop: 20 }}>
          <div style={{
            borderRadius: 16,
            background: `linear-gradient(135deg, ${winnerColor}18, ${winnerColor}08)`,
            border: `1px solid ${winnerColor}30`,
            padding: '20px 24px',
            marginBottom: 3,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontSize: 10.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 5, fontWeight: 700 }}>Predicted Winner</div>
              <div style={{ fontSize: 22, fontWeight: 900, color: winnerColor, letterSpacing: '-0.5px' }}>{result.predicted_winner}</div>
            </div>
            <div style={{
              padding: '7px 16px', borderRadius: 20,
              background: `${confidenceColor[result.confidence]}15`,
              border: `1px solid ${confidenceColor[result.confidence]}35`,
              color: confidenceColor[result.confidence],
              fontWeight: 700, fontSize: 12, letterSpacing: '0.04em',
            }}>
              {result.confidence} Confidence
            </div>
          </div>

          <div className="card">
            <ProbabilityBar
              teamA={result.team_a.team} teamB={result.team_b.team}
              probA={result.team_a.win_probability} probB={result.team_b.win_probability}
            />
            {result.key_factors.length > 0 && (
              <div style={{ marginTop: 20, paddingTop: 18, borderTop: '1px solid var(--border)' }}>
                <div className="section-label">Key Factors</div>
                {result.key_factors.map((f, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, alignItems: 'flex-start' }}>
                    <span style={{ color: winnerColor, fontSize: 12, marginTop: 2, flexShrink: 0 }}>▸</span>
                    <span style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.55 }}>{f}</span>
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 20, paddingTop: 18, borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 14 }}>
              {saved ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', borderRadius: 10, background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)' }}>
                  <span style={{ color: '#4ade80', fontWeight: 700, fontSize: 13 }}>✓ Saved to Predictions Log</span>
                </div>
              ) : (
                <button onClick={savePrediction} style={{
                  padding: '10px 22px', borderRadius: 10, border: '1px solid rgba(59,130,246,0.3)',
                  background: 'rgba(59,130,246,0.08)', color: '#93c5fd',
                  fontWeight: 600, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit',
                  transition: 'all 0.15s',
                }}>
                  Save Prediction →
                </button>
              )}
              <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>for {matchDate}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
