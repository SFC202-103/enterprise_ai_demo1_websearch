import React, {useEffect, useState, useRef} from 'react'

export default function MatchPage({match}){
  const [updates, setUpdates] = useState([])
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)

  useEffect(()=>{
    // open websocket to backend demo endpoint
    const id = match.id || match.match_id || match.title || 'default'
    // Use relative host so Vite proxy forwards websocket upgrades to backend.
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/ws/matches/${id}`
    let ws
    try{
      ws = new WebSocket(url)
  ws.onopen = ()=>{ console.log('ws open', url); setConnected(true) }
      ws.onmessage = (ev)=>{
        try{
          const data = JSON.parse(ev.data)
          setUpdates(u => [...u, data])
        }catch(e){
          console.error('invalid ws data', e)
        }
      }
  ws.onerror = (e)=>{ console.error('ws error', e); setConnected(false) }
  ws.onclose = ()=>{ console.log('ws closed'); setConnected(false) }
    }catch(e){
      console.error('ws failed', e)
    }

    wsRef.current = ws
    return ()=>{
      try{ if(wsRef.current) wsRef.current.close() }catch(_){}
    }
  },[match])

  return (
    <div>
      <h2>{match.title || match.id || 'Match'}</h2>
      <div className="match-meta">
        <pre>{JSON.stringify(match, null, 2)}</pre>
      </div>
      <div className="updates">
        <h3>Live updates</h3>
        <div className="connection-status">WebSocket: {connected ? 'connected' : 'disconnected'}</div>
        {updates.length===0 ? <div>No live updates yet</div> : (
          <ul>
            {updates.map((u,i)=>(<li key={i}><pre>{JSON.stringify(u)}</pre></li>))}
          </ul>
        )}
      </div>
    </div>
  )
}
