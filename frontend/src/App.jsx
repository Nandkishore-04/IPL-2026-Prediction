import React, { useState } from 'react'
import PreMatchPredictor from './components/PreMatchPredictor.jsx'
import LiveTracker from './components/LiveTracker.jsx'
import AccuracyDashboard from './components/AccuracyDashboard.jsx'

const tabs = [
  { id: 'prematch', label: 'Pre-Match' },
  { id: 'live',     label: 'Live Tracker' },
  { id: 'accuracy', label: 'Accuracy' },
]

const navStyle = {
  background: '#0d1421',
  borderBottom: '1px solid #1e2738',
  padding: '0 24px',
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  position: 'sticky',
  top: 0,
  zIndex: 100,
}

const logoStyle = {
  fontSize: 18,
  fontWeight: 900,
  color: '#60a5fa',
  marginRight: 24,
  padding: '16px 0',
  letterSpacing: '-0.5px',
}

const tabStyle = (active) => ({
  padding: '18px 20px',
  background: 'none',
  border: 'none',
  borderBottom: `3px solid ${active ? '#3b82f6' : 'transparent'}`,
  color: active ? '#e2e8f0' : '#475569',
  cursor: 'pointer',
  fontWeight: active ? 700 : 400,
  fontSize: 14,
  transition: 'color 0.2s',
})

export default function App() {
  const [tab, setTab] = useState('prematch')

  return (
    <div style={{ minHeight: '100vh', background: '#0a0e1a', color: '#e2e8f0' }}>
      {/* Navigation */}
      <nav style={navStyle}>
        <span style={logoStyle}>IPL 2026</span>
        {tabs.map(t => (
          <button key={t.id} style={tabStyle(tab === t.id)} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main style={{ padding: '32px 24px', maxWidth: 900, margin: '0 auto' }}>
        {tab === 'prematch'  && <PreMatchPredictor />}
        {tab === 'live'      && <LiveTracker />}
        {tab === 'accuracy'  && <AccuracyDashboard />}
      </main>
    </div>
  )
}
