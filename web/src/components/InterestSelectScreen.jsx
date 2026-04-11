const INTERESTS = [
  'Accounting',
  'Finance',
  'HR',
  'Technology',
  'Marketing',
]

export default function InterestSelectScreen({ onSelect, onBack }) {
  return (
    <div className="screen center">
      <h2>What area interests you?</h2>
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
      <button className="btn-secondary" onClick={onBack} style={{ marginTop: '1rem' }}>Back</button>
    </div>
  )
}
