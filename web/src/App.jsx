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
import InfoScreen from './components/InfoScreen'

const QUESTIONS = [
  {
    q: "Hvor mange ansatte er det i Sopra Steria i Norge?",
    a: ["1000", "3500", "7000"],
    correct: 1,
  },
  {
    q: "Hva heter husbandet til Sopra Steria?",
    a: ["Kjells Angels", "Posthusetdruse", "The Ozzy Osbournes"],
    correct: 0,
  },
  {
    q: "Hva er ikke en sosial gruppe i Sopra Steria?",
    a: ["Surfegruppe", "Poker-gruppe", "Vinsmaking", "Badminton"],
    correct: 3,
  },
]

export default function App() {
  const [state, setState] = useState('START')
  const [photoBlob, setPhotoBlob] = useState(null)
  const [photoUrl, setPhotoUrl] = useState(null)
  const [name, setName] = useState('')
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
        setErrorMsg(data.message || 'Bildet er ikke gyldig. Prøv igjen.')
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

  const handleQuizDone = useCallback(() => {
    setState('WAITING')
  }, [])

  const handleGenReady = useCallback((result) => {
    setResultData(result)
    setState('RESULT')
  }, [])

  const handleGenError = useCallback(() => {
    setErrorMsg('Generering feilet. Prøv igjen.')
    setState('START')
  }, [])

  const handlePublish = useCallback(async (currentName) => {
    const charId = genCharIdRef.current
    if (!charId) return
    const fd = new FormData()
    fd.append('name', currentName)
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
    setResultData(null)
    setErrorMsg('')
    setValidating(false)
    resetGen()
    setState('START')
  }, [photoUrl])

  return (
    <div className="app">
      {state === 'START' && (
        <StartScreen onStart={() => { setErrorMsg(''); setState('INFO') }} errorMsg={errorMsg} />
      )}
      {state === 'INFO' && (
        <InfoScreen onContinue={() => setState('PREVIEW')} onBack={() => setState('START')} />
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
        <QuestionnaireScreen questions={QUESTIONS} onDone={handleQuizDone} />
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
          onPublish={handlePublish}
          onDone={handleDone}
        />
      )}
    </div>
  )
}
