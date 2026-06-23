import { useState } from 'react'

// Collapsible panel showing the source chunks used to build an answer.
export default function SourcesPanel({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null

  return (
    <div className="sources">
      <button className="sources-toggle" onClick={() => setOpen((o) => !o)}>
        {open ? '▾' : '▸'} Fontes ({sources.length})
      </button>
      {open && (
        <ul className="sources-list">
          {sources.map((s, i) => (
            <li key={i}>
              <div className="source-head">
                <span className="source-file">{s.source}</span>
                <span className="source-score">score {s.score}</span>
              </div>
              <p className="source-chunk">{s.chunk}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
