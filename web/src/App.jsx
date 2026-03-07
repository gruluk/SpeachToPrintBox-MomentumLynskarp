import { useState, useRef, useCallback } from 'react'
import './App.css'
import StartScreen from './components/StartScreen'
import PreviewScreen from './components/PreviewScreen'
import ValidatingScreen from './components/ValidatingScreen'
import ReviewScreen from './components/ReviewScreen'
import NameInputScreen from './components/NameInputScreen'
import QuestionnaireScreen from './components/QuestionnaireScreen'
import WaitingScreen from './components/WaitingScreen'
import ResultScreen from './components/ResultScreen'
import DinoRevealScreen from './components/DinoRevealScreen'

const QUESTIONS = [
  {
    q: "Production is on fire 🔥. You...",
    a: [
      ["Blame the intern", "1"],
      ["Open 3 incidents, close 2 immediately", "2"],
      ["Push a hotfix without testing", "3"],
      ["Already left for vacation", "4"],
    ],
  },
  {
    q: "Your README is...",
    a: [
      ["A detailed 40-page novel", "1"],
      ["A strongly-worded warning", "2"],
      ["Three emojis and a broken badge", "3"],
      ["What's a README?", "4"],
    ],
  },
  {
    q: "You at a hackathon:",
    a: [
      ["Planning the perfect architecture", "1"],
      ["Defending your tech choices loudly", "2"],
      ["Rewriting in a new framework at 2am", "3"],
      ["Pitching 5 ideas to anyone nearby", "4"],
    ],
  },
]

const DINO_NAMES = {
  "1": "Brachiosaurus",
  "2": "Triceratops",
  "3": "Stegosaurus",
  "4": "Pterodactyl",
}

function scoreDino(answers) {
  const counts = {}
  for (const a of answers) counts[a] = (counts[a] || 0) + 1
  return Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0][0]
}

export default function App() {
  const [state, setState] = useState('START')
  const [photoBlob, setPhotoBlob] = useState(null)
  const [photoUrl, setPhotoUrl] = useState(null)
  const [name, setName] = useState('')
  const [answers, setAnswers] = useState([])
  const [resultData, setResultData] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [validating, setValidating] = useState(false)

  // Gen state in refs — avoids re-renders while WaitingScreen polls
  const genReadyRef = useRef(false)
  const genResultRef = useRef(null)
  const genErrorRef = useRef(false)
  const genCharIdRef = useRef(null)

  function resetGen() {
    genReadyRef.current = false
    genResultRef.current = null
    genErrorRef.current = false
    genCharIdRef.current = null
  }

  const startGeneration = useCallback(async (blob) => {
    resetGen()
    const fd = new FormData()
    fd.append('image', blob, 'photo.jpg')
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 120_000)
    try {
      const res = await fetch('/generate', { method: 'POST', body: fd, signal: controller.signal })
      clearTimeout(timeout)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      genResultRef.current = data
      genCharIdRef.current = data.id
      genReadyRef.current = true
    } catch (e) {
      clearTimeout(timeout)
      console.error('[generate]', e)
      genErrorRef.current = true
    }
  }, [])

  const handleCapture = useCallback(async (blob) => {
    setPhotoBlob(blob)
    setPhotoUrl(URL.createObjectURL(blob))
    setValidating(true)
    setState('REVIEW')

    const fd = new FormData()
    fd.append('image', blob, 'photo.jpg')
    try {
      const res = await fetch('/validate', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.ok) {
        startGeneration(blob) // fire and forget
        setValidating(false)
      } else {
        setErrorMsg(data.message || 'Photo not valid. Try again.')
        setValidating(false)
        setState('PREVIEW')
      }
    } catch (e) {
      console.error('[validate]', e)
      startGeneration(blob) // proceed anyway on network error
      setValidating(false)
    }
  }, [startGeneration])

  const handleReviewOk = useCallback(() => setState('NAME_INPUT'), [])

  const handleNameSubmit = useCallback((n) => {
    setName(n)
    setState('QUESTIONNAIRE')
  }, [])

  const handleQuestionsDone = useCallback((ans) => {
    setAnswers(ans)
    setState('DINO_REVEAL')
  }, [])

  const handleGenReady = useCallback((result) => {
    setResultData(result)
    setState('RESULT')
  }, [])

  const handleGenError = useCallback(() => {
    setErrorMsg('Generation failed. Please try again.')
    setState('START')
  }, [])

  const handlePublish = useCallback(async (currentAnswers, currentName) => {
    const charId = genCharIdRef.current
    if (!charId) return
    const dinoKey = currentAnswers.length ? scoreDino(currentAnswers) : '1'
    const dinoType = DINO_NAMES[dinoKey] || ''
    const fd = new FormData()
    fd.append('name', currentName)
    fd.append('dino_type', dinoType)
    try {
      await fetch(`/publish/${charId}`, { method: 'POST', body: fd })
    } catch (e) {
      console.error('[publish]', e)
    }
  }, [])

  const handleDone = useCallback(() => {
    if (photoUrl) URL.revokeObjectURL(photoUrl)
    setPhotoBlob(null)
    setPhotoUrl(null)
    setName('')
    setAnswers([])
    setResultData(null)
    setErrorMsg('')
    setValidating(false)
    resetGen()
    setState('START')
  }, [photoUrl])

  const dinoKey = answers.length ? scoreDino(answers) : '1'
  const dinoName = DINO_NAMES[dinoKey] || ''

  return (
    <div className="app">
      {state === 'START' && (
        <StartScreen onStart={() => { setErrorMsg(''); setState('PREVIEW') }} errorMsg={errorMsg} />
      )}
      {state === 'PREVIEW' && (
        <PreviewScreen onCapture={handleCapture} onCancel={() => { setErrorMsg(''); setState('START') }} errorMsg={errorMsg} />
      )}
      {state === 'VALIDATING' && (
        <ValidatingScreen />
      )}
      {state === 'REVIEW' && (
        <ReviewScreen photoUrl={photoUrl} validating={validating} onOk={handleReviewOk} onRetake={() => { setValidating(false); setState('PREVIEW') }} />
      )}
      {state === 'NAME_INPUT' && (
        <NameInputScreen onSubmit={handleNameSubmit} onBack={() => setState('REVIEW')} />
      )}
      {state === 'QUESTIONNAIRE' && (
        <QuestionnaireScreen questions={QUESTIONS} onDone={handleQuestionsDone} onBack={() => setState('NAME_INPUT')} />
      )}
      {state === 'DINO_REVEAL' && (
        <DinoRevealScreen dinoKey={dinoKey} dinoName={dinoName} onContinue={() => setState('WAITING')} />
      )}
      {state === 'WAITING' && (
        <WaitingScreen
          genReadyRef={genReadyRef}
          genResultRef={genResultRef}
          genErrorRef={genErrorRef}
          onReady={handleGenReady}
          onError={handleGenError}
        />
      )}
      {state === 'RESULT' && (
        <ResultScreen
          resultData={resultData}
          name={name}
          dinoName={dinoName}
          answers={answers}
          onPublish={handlePublish}
          onDone={handleDone}
        />
      )}
    </div>
  )
}
