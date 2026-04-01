/**
 * API client — all calls to the FastAPI backend go through here.
 * Base URL is /api (proxied to localhost:8000 in dev via vite.config.js).
 */

const BASE = '/api'

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.statusText}`)
  return res.json()
}

export const api = {
  predictMatch: (data) => post('/predict-match', data),
  predictLive:  (data) => post('/predict-live',  data),
  getTeams:     ()     => get('/teams'),
  getVenues:    ()     => get('/venues'),
  getTeamStats: (name) => get(`/team/${encodeURIComponent(name)}/stats`),
  getAccuracy:  ()     => get('/accuracy'),
  getLiveFeed:  ()     => get('/live-feed'),
  logResult:    (data) => post('/log-result', data),
  manualUpdate: (data) => post('/live-feed/manual', data),
}
