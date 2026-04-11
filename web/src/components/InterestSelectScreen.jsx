const INTERESTS = [
  'Regnskap',
  'Finans',
  'HR',
  'Teknologi',
  'Markedsføring',
]

export default function InterestSelectScreen({ onSelect, onBack }) {
  return (
    <div className="screen center">
      <h2>Hvilket område interesserer deg?</h2>
      <div className="demo-options">
        {INTERESTS.map((interest) => (
          <button
            key={interest}
            className="btn-answer"
            onClick={() => onSelect(interest)}
          >
            {interest}
          </button>
        ))}
      </div>
      <button className="btn-secondary" onClick={onBack} style={{ marginTop: '1rem' }}>Tilbake</button>
    </div>
  )
}
