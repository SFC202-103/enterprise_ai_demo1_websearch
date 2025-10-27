import React, {useEffect, useState} from 'react'
import MatchList from './components/MatchList'
import MatchPage from './components/MatchPage'
import DemoPage from './components/DemoPage'

export default function App(){
  const [matches, setMatches] = useState([])
  const [selected, setSelected] = useState(null)
  const [demoMode, setDemoMode] = useState(false)

  useEffect(()=>{
    async function load(){
      try{
        // Use relative URL so Vite proxy (vite.config.js) can forward requests
        const res = await fetch('/api/matches')
        if(!res.ok){
          setMatches([])
          return
        }
        const data = await res.json()
        const arr = Array.isArray(data) ? data : data
        setMatches(arr)
        // Auto-enable demo mode when URL contains ?demo=1
        try{
          const params = new URLSearchParams(window.location.search)
          if(params.get('demo') === '1'){
            setDemoMode(true)
            // Prefer a match with id 'm1' if present
            const demoMatch = arr.find(m => String(m.id) === 'm1') || arr[0] || { id: 'm1', title: 'Demo Match' }
            setSelected(demoMatch)
          }
        }catch(_){ }
      }catch(e){
        console.error(e)
        setMatches([])
      }
    }
    load()
  },[])

  return (
    <div className="app">
      <header>
        <h1>Esports Demo</h1>
      </header>
      <main>
        <section className="left">
          <MatchList matches={matches} onSelect={m=>setSelected(m)} />
        </section>
        <section className="right">
          {demoMode ? (
            <DemoPage matchId={selected?.id || 'm1'} matchTitle={selected?.title || 'Demo Match'} />
          ) : selected ? (
            <MatchPage match={selected} />
          ) : (
            <div>
              <div>Select a match</div>
              <div style={{marginTop:12}}>
                <button onClick={() => {
                  // enable demo targeting first match or m1
                  const demoMatch = matches.find(m => String(m.id) === 'm1') || matches[0] || { id: 'm1', title: 'Demo Match' }
                  setSelected(demoMatch)
                  setDemoMode(true)
                }}>Open demo</button>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
