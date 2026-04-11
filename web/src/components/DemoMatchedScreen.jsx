const DEMOS = [
  'AI Assistant',
  'Document Processing',
  'Data Analytics',
  'Process Automation',
  'Custom Solution',
]

export default function DemoMatchedScreen({ matchedUser, onSelectDemo, onBack }) {
  return (
    <div className="screen center-content">
      <p className="demo-greeting">Hi {matchedUser?.name}!</p>
      <h2>Which demo would you like?</h2>
      <div className="q-answers">
        {DEMOS.map((demo) => (
          <button
            key={demo}
            className="btn-answer"
            onClick={() => onSelectDemo(demo)}
          >
            {demo}
          </button>
        ))}
      </div>
      <button className="btn-secondary" onClick={onBack}>Back</button>
    </div>
  )
}
