const INTERESTS = [
  'Accounting',
  'Finance',
  'HR',
  'Technology',
  'Marketing',
]

export default function InterestSelectScreen({ onSelect, onBack }) {
  return (
    <div className="screen center-content">
      <h2>What area interests you?</h2>
      <div className="q-answers">
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
      <button className="btn-secondary" onClick={onBack}>Back</button>
    </div>
  )
}
