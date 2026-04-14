import { useEffect, useState } from 'react'

export default function DemoMatchedScreen({ matchedUser, onSelectDemos, onBack }) {
  const [demos, setDemos] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(new Set())

  useEffect(() => {
    fetch('/presentations')
      .then(r => r.json())
      .then(data => { setDemos(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  function toggleDemo(id) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleConfirm() {
    onSelectDemos(Array.from(selected))
  }

  return (
    <div className="screen center">
      <p className="demo-greeting">Hei {matchedUser?.name}!</p>
      <h2>Hvilke demoer vil du ha?</h2>
      {loading ? (
        <p className="status-sub">Laster alternativer...</p>
      ) : demos.length === 0 ? (
        <p className="status-sub">Ingen demoer tilgjengelig akkurat nå.</p>
      ) : (
        <div className="demo-options">
          {demos.map((demo) => (
            <button
              key={demo.id}
              className={`btn-answer ${selected.has(demo.id) ? 'demo-selected' : ''}`}
              onClick={() => toggleDemo(demo.id)}
            >
              {demo.name}
            </button>
          ))}
        </div>
      )}
      <div className="start-buttons" style={{ marginTop: '1.5rem' }}>
        <button className="btn-secondary" onClick={onBack}>Tilbake</button>
        <button
          className="btn-primary"
          onClick={handleConfirm}
          disabled={selected.size === 0}
        >
          Bekreft ({selected.size})
        </button>
      </div>
    </div>
  )
}
