/**
 * ProbabilityChart — ball-by-ball win probability timeline.
 * X-axis: ball number (1–120). Y-axis: batting team win %.
 * Red dots = wickets, Gold dots = sixes.
 * This is what Star Sports Win Predictor looks like.
 */

import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Scatter, ScatterChart,
  ComposedChart, LabelList,
} from 'recharts'

const CustomDot = (props) => {
  const { cx, cy, payload } = props
  if (payload.wicket) {
    return <circle cx={cx} cy={cy} r={5} fill="#ef4444" stroke="#fff" strokeWidth={1} />
  }
  if (payload.six) {
    return <circle cx={cx} cy={cy} r={5} fill="#fbbf24" stroke="#fff" strokeWidth={1} />
  }
  return null
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{
      background: '#1e2738', border: '1px solid #334155',
      padding: '10px 14px', borderRadius: '8px', fontSize: '13px',
    }}>
      <p style={{ color: '#94a3b8', marginBottom: 4 }}>Ball {d.ball}</p>
      <p style={{ color: '#60a5fa', fontWeight: 700 }}>
        Win Prob: {(d.prob * 100).toFixed(1)}%
      </p>
      <p style={{ color: '#e2e8f0' }}>Score: {d.score}/{d.wickets}</p>
      {d.wicket && <p style={{ color: '#ef4444' }}>WICKET</p>}
      {d.six && <p style={{ color: '#fbbf24' }}>SIX</p>}
    </div>
  )
}

export default function ProbabilityChart({ data, battingTeam }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ textAlign: 'center', color: '#475569', padding: '40px' }}>
        No data yet — predictions will appear ball by ball
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 20, marginBottom: 12, fontSize: 12, color: '#94a3b8' }}>
        <span><span style={{ color: '#ef4444' }}>●</span> Wicket</span>
        <span><span style={{ color: '#fbbf24' }}>●</span> Six</span>
        <span><span style={{ color: '#60a5fa' }}>—</span> {battingTeam} Win %</span>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2738" />
          <XAxis
            dataKey="ball"
            stroke="#475569"
            tick={{ fill: '#64748b', fontSize: 11 }}
            label={{ value: 'Ball', position: 'insideBottom', offset: -2, fill: '#64748b' }}
            ticks={[6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90, 96, 102, 108, 114, 120]}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            stroke="#475569"
            tick={{ fill: '#64748b', fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0.5} stroke="#334155" strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="prob"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={<CustomDot />}
            activeDot={{ r: 6, fill: '#60a5fa' }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
