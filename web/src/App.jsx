import { useState, useRef, useCallback, useEffect } from 'react'
import './App.css'
import FaceDebugScreen from './components/FaceDebugScreen'
import StartScreen from './components/StartScreen'
import PreviewScreen from './components/PreviewScreen'
import ValidatingScreen from './components/ValidatingScreen'
import ReviewScreen from './components/ReviewScreen'
import NameInputScreen from './components/NameInputScreen'
import InterestSelectScreen from './components/InterestSelectScreen'
import QuestionnaireScreen from './components/QuestionnaireScreen'
import WaitingScreen from './components/WaitingScreen'
import ResultScreen from './components/ResultScreen'
import InfoScreen from './components/InfoScreen'
import DemoAutoRecognize from './components/DemoAutoRecognize'
import DemoMatchedScreen from './components/DemoMatchedScreen'
import DemoNoMatchScreen from './components/DemoNoMatchScreen'
import DemoDoneScreen from './components/DemoDoneScreen'

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
  // Route to face debug screen if path matches
  if (window.location.pathname.includes('face-debug')) {
    return (
      <div className="app">
        <FaceDebugScreen />
      </div>
    )
  }

  // Extract booth number from URL (e.g., /booth/2 → 2)
  const boothNumber = (() => {
    const match = window.location.pathname.match(/\/booth\/(\d+)/)
    return match ? parseInt(match[1], 10) : 1
  })()

  const [boothMode, setBoothMode] = useState('both') // 'both' | 'register' | 'demo'

  useEffect(() => {
    fetch(`/booth-config/${boothNumber}`)
      .then(r => r.json())
      .then(data => setBoothMode(data.mode || 'both'))
      .catch(() => {})
  }, [boothNumber])

  const [state, setState] = useState('START')
  const [flow, setFlow] = useState(null) // 'register' | 'demo'
  const [photoBlob, setPhotoBlob] = useState(null)
  const [photoUrl, setPhotoUrl] = useState(null)
  const [name, setName] = useState('')
  const [interest, setInterest] = useState('')
  const [resultData, setResultData] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [validating, setValidating] = useState(false)

  // Demo flow state
  const [matchedUser, setMatchedUser] = useState(null)
  const [demoChoice, setDemoChoice] = useState('')

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

  // --- Register flow ---

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
    setState('INTEREST_SELECT')
  }, [])

  const handleInterestSelect = useCallback((i) => {
    setInterest(i)
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
    setErrorMsg('Generation failed. Try again.')
    setState('START')
  }, [])

  const handlePublish = useCallback(async (currentName, currentInterest) => {
    const charId = genCharIdRef.current
    if (!charId) return
    // Publish character (for wall + printing)
    const fd = new FormData()
    fd.append('name', currentName)
    fd.append('interest', currentInterest || '')
    try {
      await fetch(`/publish/${charId}`, { method: 'POST', body: fd })
    } catch (e) {
      console.error('[publish]', e)
    }

    // Also enroll face (fire and forget)
    if (photoBlob) {
      const enrollFd = new FormData()
      enrollFd.append('image', photoBlob, 'photo.jpg')
      enrollFd.append('name', currentName)
      enrollFd.append('interest', currentInterest || '')
      fetch('/face/enroll', { method: 'POST', body: enrollFd }).catch(e => console.error('[face enroll]', e))
    }
  }, [photoBlob])

  // --- Demo flow ---

  const handleDemoSelect = useCallback(async (demoIds) => {
    setDemoChoice(demoIds)
    if (matchedUser) {
      fetch('/demo-choice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: matchedUser.id, demo_ids: demoIds }),
      }).catch(e => console.error('[demo-choice]', e))
    }
    setState('DEMO_DONE')
  }, [matchedUser])

  // --- Reset ---

  const handleDone = useCallback(() => {
    if (photoUrl) URL.revokeObjectURL(photoUrl)
    setPhotoBlob(null)
    setPhotoUrl(null)
    setName('')
    setInterest('')
    setResultData(null)
    setErrorMsg('')
    setValidating(false)
    setFlow(null)
    setMatchedUser(null)
    setDemoChoice('')
    resetGen()
    setState('START')
  }, [photoUrl])

  return (
    <div className="app">
      {state === 'START' && (
        <StartScreen
          mode={boothMode}
          onRegister={() => { setErrorMsg(''); setFlow('register'); setState('INFO') }}
          onDemo={() => { setErrorMsg(''); setFlow('demo'); setState('DEMO_AUTO_RECOGNIZE') }}
          errorMsg={errorMsg}
        />
      )}

      {/* Register flow */}
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
      {state === 'INTEREST_SELECT' && (
        <InterestSelectScreen onSelect={handleInterestSelect} onBack={() => setState('NAME_INPUT')} />
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
          interest={interest}
          onPublish={handlePublish}
          onDone={handleDone}
        />
      )}

      {/* Demo flow */}
      {state === 'DEMO_AUTO_RECOGNIZE' && (
        <DemoAutoRecognize
          onMatched={(user) => { setMatchedUser(user); setState('DEMO_MATCHED') }}
          onNoMatch={() => setState('DEMO_NO_MATCH')}
          onCancel={handleDone}
        />
      )}
      {state === 'DEMO_MATCHED' && (
        <DemoMatchedScreen matchedUser={matchedUser} onSelectDemos={handleDemoSelect} onBack={handleDone} />
      )}
      {state === 'DEMO_NO_MATCH' && (
        <DemoNoMatchScreen
          onRetry={() => setState('DEMO_AUTO_RECOGNIZE')}
          onRegister={() => { setFlow('register'); setState('INFO') }}
          onBack={handleDone}
        />
      )}
      {state === 'DEMO_DONE' && (
        <DemoDoneScreen name={matchedUser?.name} demoCount={Array.isArray(demoChoice) ? demoChoice.length : 0} onDone={handleDone} />
      )}
    </div>
  )
}
