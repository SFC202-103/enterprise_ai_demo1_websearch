import React, { useMemo, useEffect, useState } from 'react'
import useEventSource from '../hooks/useEventSource'

export default function DemoPage({ matchId: initialMatchId = 'm1', matchTitle = 'Demo Match' }) {
  const [matchId, setMatchId] = React.useState(initialMatchId)
  const sseUrl = `/api/stream/matches/${encodeURIComponent(matchId)}`
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsUrl = `${wsProtocol}://${window.location.host}/ws/matches/${encodeURIComponent(matchId)}`

  const { connected, messages, clear } = useEventSource(sseUrl, { websocketFallbackUrl: wsUrl })

  const [homeTeam, setHomeTeam] = useState({ name: 'Home', logo: null, color: null })
  const [awayTeam, setAwayTeam] = useState({ name: 'Away', logo: null, color: null })
  const [adminToken, setAdminToken] = useState('')
  const seederRef = React.useRef(null)

  // deterministic color from name
  const colorFromName = (name) => {
    if (!name) return '#888'
    let h = 0
    for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h)
    const c = (h & 0x00ffffff).toString(16).toUpperCase()
    return `#${'00000'.substring(0, 6 - c.length)}${c}`.slice(0, 7)
  }

  // Fetch match metadata to populate team names/logos where available
  useEffect(() => {
    let cancelled = false
    async function fetchMeta() {
      // discover tracked match first
      try {
        const t = await fetch('/api/tracked')
        if (t.ok) {
          const td = await t.json()
          if (td && td.match_id) {
            setMatchId(td.match_id)
          }
        }
      } catch (err) {
        // ignore
      }
      try {
        const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}`)
        if (!res.ok) return
        const data = await res.json()
        if (cancelled) return

        // Attempt common shapes for team info
        const teams = data.teams || data.participants || data.opponents || null
        if (Array.isArray(teams) && teams.length >= 2) {
          const h = teams[0] || {}
          const a = teams[1] || {}
          setHomeTeam({ name: h.name || h.title || String(h.id || 'Home'), logo: h.image || h.logo || h.logo_url || null })
          setAwayTeam({ name: a.name || a.title || String(a.id || 'Away'), logo: a.image || a.logo || a.logo_url || null })
          return
        }

        // Some fixtures use home_team/away_team
        if (data.home_team || data.away_team) {
          const h = data.home_team || {}
          const a = data.away_team || {}
          setHomeTeam({ name: h.name || String(h.id || 'Home'), logo: h.logo || h.image || null })
          setAwayTeam({ name: a.name || String(a.id || 'Away'), logo: a.logo || a.image || null })
          return
        }

        // Fallback: parse title like 'Team A vs Team B'
        if (data.title && typeof data.title === 'string') {
          const parts = data.title.split(/\s+v(?:s)?\.?\s+|\s+vs\.?\s+/i)
          if (parts.length >= 2) {
            setHomeTeam((t) => ({ ...t, name: parts[0].trim() }))
            setAwayTeam((t) => ({ ...t, name: parts[1].trim() }))
            return
          }
        }

        // If no useful metadata, leave defaults
      } catch (err) {
        // ignore
      }
    }
    fetchMeta()
    return () => { cancelled = true }
  }, [matchId])

  // derive scoreboard from messages — pick latest score-like update
  const latestScore = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]
      // seeder pushes { match_id, update: { home, away, ... } }
      if (m && m.update && (m.update.home !== undefined || m.update.away !== undefined)) {
        return { home: m.update.home || 0, away: m.update.away || 0 }
      }
      // direct score objects
      if (m && (m.home !== undefined || m.away !== undefined)) {
        return { home: m.home || 0, away: m.away || 0 }
      }
    }
    return { home: 0, away: 0 }
  }, [messages])

  const events = messages.filter((m) => m && ((m.update && m.update.event) || m.event || m.type === 'event' || m.type === 'score'))

  return (
    <div className="demo-page">
      <header>
        <h2>{matchTitle}</h2>
        <div className="demo-controls">
          <span className={`status ${connected ? 'online' : 'offline'}`}>{connected ? 'live' : 'disconnected'}</span>
          <button onClick={() => clear()}>Clear</button>
        </div>
      </header>

      <section className="scoreboard" style={{display:'flex',gap:20,alignItems:'center'}}>
        <div className="team home" style={{textAlign:'center'}}>
          {homeTeam.logo ? (
            <img src={homeTeam.logo} alt={homeTeam.name} className="team-logo" onError={(e)=>{e.target.onerror=null; e.target.src='data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2264%22 height=%2264%22><rect width=%2264%22 height=%2264%22 fill=%22%23eee%22/><text x=%2232%22 y=%2236%22 font-size=%2210%22 text-anchor=%22middle%22 fill=%22%23777%22>${encodeURIComponent(homeTeam.name.slice(0,2))}</text></svg>'}} />
          ) : (
            <div className="team-logo" style={{background:homeTeam.color||colorFromName(homeTeam.name),color:'#fff',display:'flex',alignItems:'center',justifyContent:'center'}}>{homeTeam.name.slice(0,2).toUpperCase()}</div>
          )}
          <div className="team-name">{homeTeam.name}</div>
          <div className="team-score" style={{fontSize:48,fontWeight:700}}>{latestScore.home}</div>
        </div>
        <div style={{fontSize:24}}>—</div>
        <div className="team away" style={{textAlign:'center'}}>
          {awayTeam.logo ? (
            <img src={awayTeam.logo} alt={awayTeam.name} className="team-logo" onError={(e)=>{e.target.onerror=null; e.target.src='data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2264%22 height=%2264%22><rect width=%2264%22 height=%2264%22 fill=%22%23eee%22/><text x=%2232%22 y=%2236%22 font-size=%2210%22 text-anchor=%22middle%22 fill=%22%23777%22>${encodeURIComponent(awayTeam.name.slice(0,2))}</text></svg>'}} />
          ) : (
            <div className="team-logo" style={{background:awayTeam.color||colorFromName(awayTeam.name),color:'#fff',display:'flex',alignItems:'center',justifyContent:'center'}}>{awayTeam.name.slice(0,2).toUpperCase()}</div>
          )}
          <div className="team-name">{awayTeam.name}</div>
          <div className="team-score" style={{fontSize:48,fontWeight:700}}>{latestScore.away}</div>
        </div>
      </section>

      <section className="timeline" style={{marginTop:12}}>
        <h3>Score timeline</h3>
        <div className="timeline-rows">
          {/* render simple bars representing score history */}
          {(() => {
            const hist = []
            for (let i = 0; i < messages.length; i++) {
              const m = messages[i]
              if (m && m.update && (m.update.home !== undefined || m.update.away !== undefined)) {
                hist.push({ t: m.update.timestamp || m.update.time || i, home: m.update.home||0, away: m.update.away||0 })
              } else if (m && (m.home !== undefined || m.away !== undefined)) {
                hist.push({ t: m.timestamp || i, home: m.home||0, away: m.away||0 })
              }
            }
            const max = Math.max(1, ...hist.flatMap(h=>[h.home,h.away]))
            return hist.slice(-10).map((h,idx)=> (
              <div key={idx} style={{display:'flex',gap:8,alignItems:'center',marginBottom:6}}>
                <div style={{width:80,fontSize:12}}>{new Date(h.t||Date.now()).toLocaleTimeString()}</div>
                <div style={{flex:1,display:'flex',gap:4}}>
                  <div style={{height:12,background:homeTeam.color||colorFromName(homeTeam.name),width:`${(h.home/max)*100}%`}} />
                  <div style={{height:12,background:awayTeam.color||colorFromName(awayTeam.name),width:`${(h.away/max)*100}%`}} />
                </div>
                <div style={{width:80,textAlign:'right',fontSize:12}}>{h.home} — {h.away}</div>
              </div>
            ))
          })()}
        </div>
      </section>

      <section className="admin-seeder" style={{marginTop:12}}>
        <h3>Admin seeder (requires admin token)</h3>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <input placeholder="X-Admin-Token" value={adminToken} onChange={(e)=>setAdminToken(e.target.value)} style={{flex:1}} />
          <button onClick={() => {
            // start auto seeder: POST a score update every 2s
            if (!adminToken) return alert('Provide admin token')
            if (seederRef.current) return
            seederRef.current = setInterval(async ()=>{
              const payload = { match_id: matchId, update: { type: 'score', timestamp: new Date().toISOString(), home: Math.floor(Math.random()*10), away: Math.floor(Math.random()*10) } }
              try{
                await fetch('/api/admin/push_update', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Admin-Token': adminToken }, body: JSON.stringify(payload) })
              }catch(err){ console.warn('seeder post failed', err) }
            }, 2000)
          }}>Start Seeder</button>
          <button onClick={() => { if (seederRef.current) { clearInterval(seederRef.current); seederRef.current=null } }}>Stop Seeder</button>
        </div>
      </section>

      <section className="admin-tracked" style={{marginTop:12}}>
        <h3>Admin: set tracked match/team</h3>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <input placeholder="match_id (e.g. m1)" value={matchId} onChange={(e)=>setMatchId(e.target.value)} style={{width:160}} />
          <input placeholder="team name (optional)" onChange={(e)=>{/* noop, optional */}} style={{flex:1}} id="tracked-team-input" />
          <input placeholder="X-Admin-Token" value={adminToken} onChange={(e)=>setAdminToken(e.target.value)} style={{width:200}} />
          <button onClick={async ()=>{
            if (!adminToken) return alert('Provide admin token')
            const teamInput = document.getElementById('tracked-team-input')
            const payload = { match_id: matchId, team: teamInput ? teamInput.value : undefined }
            try{
              const res = await fetch('/api/tracked', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Admin-Token': adminToken }, body: JSON.stringify(payload) })
              if (res.ok) {
                const jd = await res.json()
                // reflect tracked change locally
                if (jd && jd.tracked && jd.tracked.match_id) setMatchId(jd.tracked.match_id)
                alert('tracked updated')
              } else {
                const txt = await res.text()
                alert('failed: ' + txt)
              }
            }catch(err){ alert('error: '+err.message) }
          }}>Set Tracked</button>
          <button onClick={async ()=>{
            if (!adminToken) return alert('Provide admin token')
            // Track the home team
            const payload = { match_id: matchId, team: homeTeam.name }
            try{
              const res = await fetch('/api/tracked', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Admin-Token': adminToken }, body: JSON.stringify(payload) })
              if (res.ok) { alert('Now tracking home team: ' + homeTeam.name) }
              else { alert('failed to set tracked') }
            }catch(err){ alert('error: '+err.message) }
          }}>Track Home</button>
          <button onClick={async ()=>{
            if (!adminToken) return alert('Provide admin token')
            const payload = { match_id: matchId, team: awayTeam.name }
            try{
              const res = await fetch('/api/tracked', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Admin-Token': adminToken }, body: JSON.stringify(payload) })
              if (res.ok) { alert('Now tracking away team: ' + awayTeam.name) }
              else { alert('failed to set tracked') }
            }catch(err){ alert('error: '+err.message) }
          }}>Track Away</button>
        </div>
      </section>

      <section className="event-list" style={{marginTop:12}}>
        <h3>Recent events</h3>
        {events.length === 0 ? (
          <div className="no-events">No events yet</div>
        ) : (
          <ul>
            {events.slice().reverse().map((e, i) => (
              <li key={i}><pre style={{margin:0}}>{JSON.stringify(e, null, 2)}</pre></li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
