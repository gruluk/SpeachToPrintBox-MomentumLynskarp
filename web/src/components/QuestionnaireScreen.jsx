import { useState, useCallback } from 'react'

export default function QuestionnaireScreen({ questions, onDone }) {
  const [qIndex, setQIndex] = useState(0)
  const [picked, setPicked] = useState(null)
  const [revealed, setRevealed] = useState(false)

  const question = questions[qIndex]

  const handlePick = useCallback((i) => {
    if (revealed) return
    setPicked(i)
    setRevealed(true)

    setTimeout(() => {
      const next = qIndex + 1
      if (next < questions.length) {
        setQIndex(next)
        setPicked(null)
        setRevealed(false)
      } else {
        onDone()
      }
    }, 2000)
  }, [qIndex, revealed, questions, onDone])

  return (
    <div className="screen center">
      <p className="q-progress">{qIndex + 1} / {questions.length}</p>
      <h2 className="q-text">{question.q}</h2>
      <div className="q-answers">
        {question.a.map((ans, i) => {
          let cls = 'btn-answer'
          if (revealed) {
            if (i === question.correct) cls += ' answer-correct'
            else if (i === picked) cls += ' answer-wrong'
            else cls += ' answer-dim'
          }
          return (
            <button
              key={i}
              className={cls}
              onClick={() => handlePick(i)}
              disabled={revealed}
            >
              {ans}
            </button>
          )
        })}
      </div>
      {revealed && (
        <p className="q-feedback">
          {picked === question.correct ? 'Riktig!' : `Svaret var: ${question.a[question.correct]}`}
        </p>
      )}
    </div>
  )
}
