import React, {useEffect, useState} from 'react'
import MatchList from './components/MatchList'
import MatchPage from './components/MatchPage'

export default function App(){
  const [matches, setMatches] = useState([])
  const [selected, setSelected] = useState(null)

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
        setMatches(Array.isArray(data)?data:data)
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
          {selected ? <MatchPage match={selected} /> : <div>Select a match</div>}
        </section>
      </main>
    </div>
  )
}
