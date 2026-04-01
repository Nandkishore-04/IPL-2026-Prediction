/**
 * Screen 1: Pre-Match Predictor
 * Input: teams, venue, toss, playing XI → win probabilities
 */

import React, { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import TeamSelector from './TeamSelector.jsx'
import ProbabilityBar from './ProbabilityBar.jsx'

const card = {
  background: '#111827',
  borderRadius: '12px',
  padding: '24px',
  marginBottom: '20px',
  border: '1px solid #1e2738',
}

const input = {
  width: '100%',
  padding: '10px 14px',
  background: '#1e2738',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#e2e8f0',
  fontSize: '14px',
  outline: 'none',
  marginTop: 6,
}

const btn = (disabled) => ({
  width: '100%',
  padding: '14px',
  background: disabled ? '#334155' : 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
  color: '#fff',
  border: 'none',
  borderRadius: '10px',
  fontSize: '16px',
  fontWeight: 700,
  cursor: disabled ? 'not-allowed' : 'pointer',
  marginTop: '10px',
  transition: 'opacity 0.2s',
})

const label = {
  fontSize: 12,
  color: '#94a3b8',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: 4,
  display: 'block',
}

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
    setLoading(true)
    setError('')
    try {
      const xiA = form.team_a_xi.split('\n').map(s => s.trim()).filter(Boolean)
      const xiB = form.team_b_xi.split('\n').map(s => s.trim()).filter(Boolean)
      const r = await api.predictMatch({
        team_a: form.team_a,
        team_b: form.team_b,
        venue: form.venue,
        toss_winner: form.toss_winner,
        toss_decision: form.toss_decision,
        team_a_xi: xiA,
        team_b_xi: xiB,
      })
      setResult(r)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const confidenceColor = { High: '#22c55e', Medium: '#f59e0b', Low: '#ef4444' }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '0 16px' }}>
      <h2 style={{ marginBottom: 20, fontSize: 22, fontWeight: 800, color: '#e2e8f0' }}>
        Pre-Match Predictor
      </h2>

      {/* Team & Venue */}
      <div style={card}>
        <h3 style={{ marginBottom: 16, color: '#94a3b8', fontSize: 14, textTransform: 'uppercase' }}>Match Setup</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <TeamSelector label="Team A" value={form.team_a} onChange={v => set('team_a', v)} teams={teams} exclude={form.team_b} />
          <TeamSelector label="Team B" value={form.team_b} onChange={v => set('team_b', v)} teams={teams} exclude={form.team_a} />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={label}>Venue</label>
          <select value={form.venue} onChange={e => set('venue', e.target.value)} style={input}>
            <option value="">Select venue...</option>
            {venues.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
      </div>

      {/* Toss */}
      <div style={card}>
        <h3 style={{ marginBottom: 16, color: '#94a3b8', fontSize: 14, textTransform: 'uppercase' }}>Toss</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <label style={label}>Toss Winner</label>
            <select value={form.toss_winner} onChange={e => set('toss_winner', e.target.value)} style={input}>
              <option value="">Select...</option>
              {[form.team_a, form.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={label}>Decision</label>
            <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
              {['bat', 'field'].map(d => (
                <button
                  key={d}
                  onClick={() => set('toss_decision', d)}
                  style={{
                    flex: 1, padding: '10px', borderRadius: '8px',
                    border: `2px solid ${form.toss_decision === d ? '#3b82f6' : '#334155'}`,
                    background: form.toss_decision === d ? '#1d4ed8' : '#1e2738',
                    color: '#e2e8f0', cursor: 'pointer', fontWeight: 600,
                    textTransform: 'capitalize',
                  }}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Playing XI */}
      <div style={card}>
        <h3 style={{ marginBottom: 4, color: '#94a3b8', fontSize: 14, textTransform: 'uppercase' }}>Playing XI (optional — enter after toss)</h3>
        <p style={{ color: '#475569', fontSize: 12, marginBottom: 16 }}>One player name per line. Unknown players will use team-average stats.</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <label style={label}>{form.team_a || 'Team A'} XI</label>
            <textarea
              value={form.team_a_xi}
              onChange={e => set('team_a_xi', e.target.value)}
              rows={11}
              placeholder={'Rohit Sharma\nIshan Kishan\nSuryakumar Yadav\n...'}
              style={{ ...input, resize: 'vertical', fontFamily: 'monospace', lineHeight: 1.6 }}
            />
          </div>
          <div>
            <label style={label}>{form.team_b || 'Team B'} XI</label>
            <textarea
              value={form.team_b_xi}
              onChange={e => set('team_b_xi', e.target.value)}
              rows={11}
              placeholder={'Ruturaj Gaikwad\nMS Dhoni\nRavindra Jadeja\n...'}
              style={{ ...input, resize: 'vertical', fontFamily: 'monospace', lineHeight: 1.6 }}
            />
          </div>
        </div>
      </div>

      <button onClick={predict} disabled={!canPredict || loading} style={btn(!canPredict || loading)}>
        {loading ? 'Predicting...' : 'Predict Winner'}
      </button>

      {error && (
        <div style={{ marginTop: 16, padding: 14, background: '#450a0a', borderRadius: 8, color: '#fca5a5', fontSize: 14 }}>
          Error: {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ ...card, marginTop: 24, border: '1px solid #1d4ed8' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <p style={{ color: '#94a3b8', fontSize: 12, textTransform: 'uppercase' }}>Predicted Winner</p>
              <p style={{ fontSize: 22, fontWeight: 800, color: '#60a5fa' }}>{result.predicted_winner}</p>
            </div>
            <div style={{
              padding: '6px 14px', borderRadius: '20px',
              background: confidenceColor[result.confidence] + '22',
              color: confidenceColor[result.confidence],
              fontWeight: 700, fontSize: 13,
            }}>
              {result.confidence} Confidence
            </div>
          </div>

          <ProbabilityBar
            teamA={result.team_a.team}
            teamB={result.team_b.team}
            probA={result.team_a.win_probability}
            probB={result.team_b.win_probability}
          />

          {result.key_factors.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <p style={{ color: '#94a3b8', fontSize: 12, textTransform: 'uppercase', marginBottom: 10 }}>Key Factors</p>
              {result.key_factors.map((f, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, alignItems: 'flex-start' }}>
                  <span style={{ color: '#3b82f6', marginTop: 2 }}>→</span>
                  <span style={{ color: '#cbd5e1', fontSize: 14 }}>{f}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
