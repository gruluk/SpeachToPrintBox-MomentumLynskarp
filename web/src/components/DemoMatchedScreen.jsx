import { useEffect, useState } from 'react'

export default function DemoMatchedScreen({ matchedUser, onSelectDemo, onBack }) {
  const [demos, setDemos] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/presentations')
      .then(r => r.json())
      .then(data => { setDemos(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="screen center-content">
      <p className="demo-greeting">Hi {matchedUser?.name}!</p>
      <h2>Which demo would you like?</h2>
      {loading ? (
        <p className="status-sub">Loading options...</p>
      ) : demos.length === 0 ? (
        <p className="status-sub">No demos available right now.</p>
      ) : (
        <div className="q-answers">
          {demos.map((demo) => (
            <button
              key={demo.id}
              className="btn-answer"
              onClick={() => onSelectDemo(demo.name)}
            >
              {demo.name}
            </button>
          ))}
        </div>
      )}
      <button className="btn-secondary" onClick={onBack}>Back</button>
    </div>
  )
}
