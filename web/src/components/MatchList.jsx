import React from 'react'

export default function MatchList({matches, onSelect}){
  if(!matches || matches.length===0){
    return <div>No matches available (check backend)</div>
  }

  return (
    <div>
      <h2>Matches</h2>
      <ul>
        {matches.map((m, idx)=> (
          <li key={m.id || idx}>
            <button onClick={()=>onSelect(m)}>
              {m.title || m.id || `Match ${idx+1}`}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
