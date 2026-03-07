import { useState } from 'react'

export default function QuestionnaireScreen({ questions, onDone }) {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState([])

  function pick(value) {
    const newAnswers = [...answers, value]
    if (step + 1 < questions.length) {
      setAnswers(newAnswers)
      setStep(step + 1)
    } else {
      onDone(newAnswers)
    }
  }

  const q = questions[step]
  return (
    <div className="screen center">
      <p className="q-progress">{step + 1} / {questions.length}</p>
      <h2 className="q-text">{q.q}</h2>
      <div className="q-answers">
        {q.a.map(([label, value]) => (
          <button key={value} className="btn-answer" onClick={() => pick(value)}>
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
