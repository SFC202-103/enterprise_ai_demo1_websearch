import React, { useEffect, useRef } from 'react'
import useEventSource from '../hooks/useEventSource'

export default function MatchPage({ match }) {
  const id = match.id || match.match_id || match.title || 'default'
  const sseUrl = `/api/stream/matches/${encodeURIComponent(id)}`
  // Provide WebSocket fallback URL (relative) in case SSE is not available
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsUrl = `${wsProtocol}://${window.location.host}/ws/matches/${encodeURIComponent(id)}`

  const { connected, messages, clear } = useEventSource(sseUrl, { websocketFallbackUrl: wsUrl })
  const listRef = useRef(null)

  // Auto-scroll when new messages arrive
  useEffect(() => {
    try {
      if (listRef.current) {
        listRef.current.scrollTop = listRef.current.scrollHeight
      }
    } catch (_) {}
  }, [messages])

  const formatItem = (u) => {
    if (u == null) return ''
    if (u.timestamp) return `${new Date(u.timestamp).toLocaleTimeString()} — ${u.type || ''}`
    if (u.update && u.update.timestamp) return `${new Date(u.update.timestamp).toLocaleTimeString()} — ${u.update.type || ''}`
    return JSON.stringify(u)
  }

  return (
    <div className="match-page">
      <h2>{match.title || match.id || 'Match'}</h2>
      <div className="match-meta">
        <pre>{JSON.stringify(match, null, 2)}</pre>
      </div>

      <div className="live-panel">
        <div className="live-header">
          <h3>Live updates</h3>
          <div className="controls">
            <span className={`status ${connected ? 'online' : 'offline'}`}>{connected ? 'live' : 'disconnected'}</span>
            <button onClick={() => clear()}>Clear</button>
          </div>
        </div>

        <div className="updates" ref={listRef} role="log" aria-live="polite">
          {messages.length === 0 ? (
            <div className="no-updates">No live updates yet</div>
          ) : (
            <ul>
              {messages.map((u, i) => (
                <li key={i} className="update-item">
                  <div className="update-meta">{formatItem(u)}</div>
                  <div className="update-body"><pre>{JSON.stringify(u, null, 2)}</pre></div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
