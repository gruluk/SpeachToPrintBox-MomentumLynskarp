import { useState } from 'react'
import SceneDecorations from './SceneDecorations'

export default function QuestionnaireScreen({ questions, onDone, onBack }) {
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

  function goBack() {
    if (step === 0) {
      onBack()
    } else {
      setAnswers(answers.slice(0, -1))
      setStep(step - 1)
    }
  }

  const q = questions[step]
  return (
    <div className="screen center">
      <SceneDecorations seed={4} />
      <p className="q-progress">{step + 1} / {questions.length}</p>
      <h2 className="q-text">{q.q}</h2>
      <div className="q-answers">
        {q.a.map(([label, value]) => (
          <button key={value} className="btn-answer" onClick={() => pick(value)}>
            {label}
          </button>
        ))}
      </div>
      <button className="btn-secondary q-back" onClick={goBack}>← Tilbake</button>
    </div>
  )
}
