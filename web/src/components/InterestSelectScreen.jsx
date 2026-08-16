import { useState } from 'react'

export default function InterestSelectScreen({
  name,
  interests = [],
  maxCount = 3,
  onSelect,
  onCancel,
}) {
  const [selected, setSelected] = useState([])
  const max = maxCount || 3

  function toggleInterest(interest) {
    setSelected((prev) => {
      if (prev.includes(interest)) {
        return prev.filter((i) => i !== interest)
      }
      if (prev.length >= max) return prev
      return [...prev, interest]
    })
  }

  function handleContinue() {
    if (selected.length >= 1) {
      onSelect(selected.join(', '))
    }
  }

  return (
    <div className="screen center interest-screen">
      <p className="interest-greeting">Hyggelig å se deg, {name}!</p>
      <h2>Velg dine interesseområder</h2>
      <p className="status-sub">
        Velg 1–{max} temaer. Valgt: {selected.length} av {max}
      </p>
      <div className="interest-grid">
        {interests.map((interest) => (
          <button
            key={interest}
            className={`btn-answer ${selected.includes(interest) ? 'interest-selected' : ''}`}
            onClick={() => toggleInterest(interest)}
          >
            {interest}
          </button>
        ))}
      </div>
      <div className="btn-row">
        <button className="btn-cancel" onClick={onCancel}>
          Avbryt
        </button>
        <button className="btn-primary" onClick={handleContinue} disabled={selected.length < 1}>
          Neste
        </button>
      </div>
    </div>
  )
}
