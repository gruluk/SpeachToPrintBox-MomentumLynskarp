import { useState } from 'react'

const INTERESTS = [
  'Periodeavslutning',
  'Avsetninger og periodiseringer',
  'Interntransaksjoner',
  'Kostnader og varelager',
  'Budsjett og prognose',
  'Konsolidering',
  'Effektivisering av økonomifunksjonen',
  'Rapportering',
  'Lønnsomhet ved bruk av KI',
  'Praktisk bruk av KI',
]

const MAX_COUNT = 3

export default function InterestSelectScreen({ name, onSelect, onCancel }) {
  const [selected, setSelected] = useState([])

  function toggleInterest(interest) {
    setSelected(prev => {
      if (prev.includes(interest)) {
        return prev.filter(i => i !== interest)
      }
      if (prev.length >= MAX_COUNT) return prev
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
      <p className="status-sub">Velg 1–{MAX_COUNT} temaer. Valgt: {selected.length} av {MAX_COUNT}</p>
      <div className="interest-grid">
        {INTERESTS.map((interest) => (
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
        <button className="btn-cancel" onClick={onCancel}>Avbryt</button>
        <button className="btn-primary" onClick={handleContinue} disabled={selected.length < 1}>
          Neste
        </button>
      </div>
    </div>
  )
}
