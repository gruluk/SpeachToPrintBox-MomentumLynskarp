import { useState } from 'react'

const INTERESTS = [
  'Regnskap',
  'Finans',
  'HR',
  'Teknologi',
  'Markedsføring',
  'Bærekraft',
  'Strategi',
  'Innovasjon',
  'Ledelse',
  'Data & AI',
]

const REQUIRED_COUNT = 3

export default function InterestSelectScreen({ onSelect, onBack }) {
  const [selected, setSelected] = useState([])

  function toggleInterest(interest) {
    setSelected(prev => {
      if (prev.includes(interest)) {
        return prev.filter(i => i !== interest)
      }
      if (prev.length >= REQUIRED_COUNT) return prev
      return [...prev, interest]
    })
  }

  function handleContinue() {
    if (selected.length === REQUIRED_COUNT) {
      onSelect(selected.join(', '))
    }
  }

  return (
    <div className="screen center">
      <h2>Velg {REQUIRED_COUNT} interesser</h2>
      <p className="status-sub">Velg {REQUIRED_COUNT - selected.length > 0 ? `${REQUIRED_COUNT - selected.length} til` : 'ferdig!'}</p>
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
        <button className="btn-secondary" onClick={onBack}>Tilbake</button>
        <button className="btn-primary" onClick={handleContinue} disabled={selected.length !== REQUIRED_COUNT}>
          Neste
        </button>
      </div>
    </div>
  )
}
