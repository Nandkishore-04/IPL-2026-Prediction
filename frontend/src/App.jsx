import { useState } from 'react'
import PreMatchPredictor from './components/PreMatchPredictor.jsx'
import LiveTracker from './components/LiveTracker.jsx'
import AccuracyDashboard from './components/AccuracyDashboard.jsx'

const tabs = [
  { id: 'prematch', label: 'Pre-Match',    icon: '🏏' },
  { id: 'live',     label: 'Live',         icon: '📡' },
  { id: 'accuracy', label: 'Season',       icon: '📊' },
]

export default function App() {
  const [tab, setTab] = useState('prematch')

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>

      {/* Top gradient bar */}
      <div style={{ height: 2, background: 'linear-gradient(90deg, #2563eb, #7c3aed, #e8102a)' }} />

      {/* Navigation */}
      <nav style={{
        background: 'rgba(6,9,15,0.92)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border)',
        padding: '0 28px',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: 60,
      }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 28 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 10,
            background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 17, flexShrink: 0,
          }}>🏏</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.3px', lineHeight: 1.2 }}>IPL 2026</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Predictor</div>
          </div>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 24, background: 'var(--border-md)', marginRight: 10 }} />

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 2 }}>
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: '7px 16px',
                background: tab === t.id ? 'rgba(59,130,246,0.12)' : 'transparent',
                border: tab === t.id ? '1px solid rgba(59,130,246,0.28)' : '1px solid transparent',
                borderRadius: 8,
                color: tab === t.id ? '#93c5fd' : 'var(--text-muted)',
                cursor: 'pointer',
                fontWeight: tab === t.id ? 600 : 400,
                fontSize: 13,
                display: 'flex', alignItems: 'center', gap: 6,
                transition: 'all 0.18s',
                fontFamily: 'inherit',
                whiteSpace: 'nowrap',
              }}
            >
              <span style={{ fontSize: 14 }}>{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        {/* Live badge */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 7, padding: '5px 12px', background: 'rgba(34,197,94,0.07)', border: '1px solid rgba(34,197,94,0.18)', borderRadius: 20 }}>
          <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 7px #22c55e' }} />
          <span style={{ fontSize: 11, color: '#4ade80', fontWeight: 600, letterSpacing: '0.04em' }}>Model Live</span>
        </div>
      </nav>

      {/* Content */}
      <main style={{ padding: '32px 20px 60px', maxWidth: 860, margin: '0 auto' }}>
        {tab === 'prematch'  && <PreMatchPredictor />}
        {tab === 'live'      && <LiveTracker />}
        {tab === 'accuracy'  && <AccuracyDashboard />}
      </main>
    </div>
  )
}
