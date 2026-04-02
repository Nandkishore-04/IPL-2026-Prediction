import { useState } from 'react'
import PreMatchPredictor from './components/PreMatchPredictor.jsx'
import LiveTracker from './components/LiveTracker.jsx'
import AccuracyDashboard from './components/AccuracyDashboard.jsx'

const tabs = [
  { id: 'prematch', label: 'Pre-Match', icon: '🏏' },
  { id: 'live',     label: 'Live Tracker', icon: '📡' },
  { id: 'accuracy', label: 'Accuracy', icon: '📊' },
]

export default function App() {
  const [tab, setTab] = useState('prematch')

  return (
    <div style={{ minHeight: '100vh', background: '#070c18', color: '#e2e8f0', fontFamily: "'Segoe UI', system-ui, sans-serif" }}>

      {/* Top accent line */}
      <div style={{ height: 3, background: 'linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899)' }} />

      {/* Navigation */}
      <nav style={{
        background: 'rgba(10,14,26,0.95)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid #1a2235',
        padding: '0 32px',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ marginRight: 32, padding: '14px 0', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16,
          }}>🏏</div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.3px' }}>IPL 2026</div>
            <div style={{ fontSize: 10, color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Predictor</div>
          </div>
        </div>

        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: '20px 18px',
              background: 'none',
              border: 'none',
              borderBottom: `2px solid ${tab === t.id ? '#3b82f6' : 'transparent'}`,
              color: tab === t.id ? '#f1f5f9' : '#64748b',
              cursor: 'pointer',
              fontWeight: tab === t.id ? 600 : 400,
              fontSize: 14,
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              transition: 'color 0.2s',
              whiteSpace: 'nowrap',
            }}
          >
            <span style={{ fontSize: 15 }}>{t.icon}</span>
            {t.label}
          </button>
        ))}

        {/* Right side badge */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: '#22c55e',
            boxShadow: '0 0 6px #22c55e',
          }} />
          <span style={{ fontSize: 12, color: '#64748b' }}>Model Live</span>
        </div>
      </nav>

      {/* Content */}
      <main style={{ padding: '36px 24px', maxWidth: 820, margin: '0 auto' }}>
        {tab === 'prematch'  && <PreMatchPredictor />}
        {tab === 'live'      && <LiveTracker />}
        {tab === 'accuracy'  && <AccuracyDashboard />}
      </main>
    </div>
  )
}
