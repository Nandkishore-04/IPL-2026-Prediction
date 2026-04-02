import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import TeamSelector from './TeamSelector.jsx'
import ProbabilityBar from './ProbabilityBar.jsx'

const card = {
  background: '#0d1424',
  borderRadius: '14px',
  padding: '22px 24px',
  marginBottom: '16px',
  border: '1px solid #1a2235',
}

const sectionTitle = {
  fontSize: 11,
  fontWeight: 700,
  color: '#475569',
  textTransform: 'uppercase',
  letterSpacing: '0.1em',
  marginBottom: 16,
}

const inputStyle = {
  width: '100%',
  padding: '10px 13px',
  background: '#0a0f1e',
  border: '1px solid #1e2d45',
  borderRadius: '8px',
  color: '#e2e8f0',
  fontSize: '14px',
  outline: 'none',
}

const labelStyle = {
  fontSize: 12,
  color: '#64748b',
  marginBottom: 6,
  display: 'block',
}

const confidenceColor = { High: '#22c55e', Medium: '#f59e0b', Low: '#ef4444' }

export default function PreMatchPredictor() {
  const [teams, setTeams]   = useState([])
  const [venues, setVenues] = useState([])
  const [form, setForm]     = useState({
    team_a: '', team_b: '', venue: '',
    toss_winner: '', toss_decision: 'bat',
    team_a_xi: '', team_b_xi: '',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')

  useEffect(() => {
    api.getTeams().then(d => setTeams(d.teams)).catch(() => {})
    api.getVenues().then(d => setVenues(d.venues)).catch(() => {})
  }, [])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const canPredict = form.team_a && form.team_b && form.venue && form.toss_winner

  const predict = async () => {
    setLoading(true); setError('')
    try {
      const xiA = form.team_a_xi.split('\n').map(s => s.trim()).filter(Boolean)
      const xiB = form.team_b_xi.split('\n').map(s => s.trim()).filter(Boolean)
      const r = await api.predictMatch({
        team_a: form.team_a, team_b: form.team_b, venue: form.venue,
        toss_winner: form.toss_winner, toss_decision: form.toss_decision,
        team_a_xi: xiA, team_b_xi: xiB,
      })
      setResult(r)
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, color: '#f1f5f9', marginBottom: 4 }}>Pre-Match Predictor</h2>
        <p style={{ fontSize: 13, color: '#475569' }}>Enter match details and playing XI to get win probabilities</p>
      </div>

      {/* Teams */}
      <div style={card}>
        <div style={sectionTitle}>Match Setup</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
          <TeamSelector label="Team A" value={form.team_a} onChange={v => set('team_a', v)} teams={teams} exclude={form.team_b} />
          <TeamSelector label="Team B" value={form.team_b} onChange={v => set('team_b', v)} teams={teams} exclude={form.team_a} />
        </div>
        <div>
          <label style={labelStyle}>Venue</label>
          <select value={form.venue} onChange={e => set('venue', e.target.value)} style={inputStyle}>
            <option value="">Select venue...</option>
            {venues.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
      </div>

      {/* Toss */}
      <div style={card}>
        <div style={sectionTitle}>Toss</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div>
            <label style={labelStyle}>Toss Winner</label>
            <select value={form.toss_winner} onChange={e => set('toss_winner', e.target.value)} style={inputStyle}>
              <option value="">Select...</option>
              {[form.team_a, form.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Decision</label>
            <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
              {['bat', 'field'].map(d => (
                <button key={d} onClick={() => set('toss_decision', d)} style={{
                  flex: 1, padding: '10px', borderRadius: '8px',
                  border: `1px solid ${form.toss_decision === d ? '#3b82f6' : '#1e2d45'}`,
                  background: form.toss_decision === d ? '#1e3a5f' : '#0a0f1e',
                  color: form.toss_decision === d ? '#93c5fd' : '#64748b',
                  cursor: 'pointer', fontWeight: 600, fontSize: 13, textTransform: 'capitalize',
                  transition: 'all 0.15s',
                }}>
                  {d === 'bat' ? '🏏 Bat' : '🥊 Field'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Playing XI */}
      <div style={card}>
        <div style={sectionTitle}>Playing XI <span style={{ color: '#334155', textTransform: 'none', fontSize: 11, fontWeight: 400 }}>— optional, enter after toss</span></div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          {[['team_a_xi', form.team_a || 'Team A'], ['team_b_xi', form.team_b || 'Team B']].map(([key, name]) => (
            <div key={key}>
              <label style={labelStyle}>{name}</label>
              <textarea
                value={form[key]}
                onChange={e => set(key, e.target.value)}
                rows={8}
                placeholder={'Player Name\nPlayer Name\n...'}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace', fontSize: 13, lineHeight: 1.7 }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Submit */}
      <button onClick={predict} disabled={!canPredict || loading} style={{
        width: '100%', padding: '14px',
        background: !canPredict || loading
          ? '#1a2235'
          : 'linear-gradient(90deg, #2563eb, #7c3aed)',
        color: !canPredict || loading ? '#334155' : '#fff',
        border: 'none', borderRadius: '10px',
        fontSize: '15px', fontWeight: 700, cursor: canPredict && !loading ? 'pointer' : 'not-allowed',
        letterSpacing: '0.02em', transition: 'opacity 0.2s',
      }}>
        {loading ? 'Analysing...' : 'Predict Winner →'}
      </button>

      {error && (
        <div style={{ marginTop: 14, padding: '12px 16px', background: '#2d0a0a', borderRadius: 8, color: '#fca5a5', fontSize: 13, border: '1px solid #450a0a' }}>
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ marginTop: 20, background: '#0d1424', border: '1px solid #1e3a5f', borderRadius: 14, padding: '24px' }}>
          {/* Winner banner */}
          <div style={{
            background: 'linear-gradient(135deg, #1e3a5f, #1e1b4b)',
            borderRadius: 10, padding: '16px 20px', marginBottom: 20,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>Predicted Winner</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: '#93c5fd' }}>{result.predicted_winner}</div>
            </div>
            <div style={{
              padding: '6px 14px', borderRadius: 20,
              background: confidenceColor[result.confidence] + '20',
              border: `1px solid ${confidenceColor[result.confidence]}40`,
              color: confidenceColor[result.confidence],
              fontWeight: 700, fontSize: 12,
            }}>
              {result.confidence} Confidence
            </div>
          </div>

          <ProbabilityBar
            teamA={result.team_a.team} teamB={result.team_b.team}
            probA={result.team_a.win_probability} probB={result.team_b.win_probability}
          />

          {result.key_factors.length > 0 && (
            <div style={{ marginTop: 20, borderTop: '1px solid #1a2235', paddingTop: 18 }}>
              <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Key Factors</div>
              {result.key_factors.map((f, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, alignItems: 'flex-start' }}>
                  <span style={{ color: '#3b82f6', fontSize: 12, marginTop: 1, flexShrink: 0 }}>▸</span>
                  <span style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.5 }}>{f}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
