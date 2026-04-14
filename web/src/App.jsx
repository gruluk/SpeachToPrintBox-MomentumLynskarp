import { useState, useCallback, useEffect } from 'react'
import './App.css'
import FaceDebugScreen from './components/FaceDebugScreen'
import StartScreen from './components/StartScreen'
import PreviewScreen from './components/PreviewScreen'
import ValidatingScreen from './components/ValidatingScreen'
import ReviewScreen from './components/ReviewScreen'
import NameInputScreen from './components/NameInputScreen'
import InterestSelectScreen from './components/InterestSelectScreen'
import DoneScreen from './components/DoneScreen'
import InfoScreen from './components/InfoScreen'
import DemoAutoRecognize from './components/DemoAutoRecognize'
import DemoMatchedScreen from './components/DemoMatchedScreen'
import DemoNoMatchScreen from './components/DemoNoMatchScreen'
import DemoDoneScreen from './components/DemoDoneScreen'

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
  const [userId, setUserId] = useState('')
  const [name, setName] = useState('')
  const [interest, setInterest] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [validating, setValidating] = useState(false)

  // Demo flow state
  const [matchedUser, setMatchedUser] = useState(null)
  const [demoChoice, setDemoChoice] = useState('')

  // --- Register flow ---

  const handleCapture = useCallback(async (blob) => {
    setPhotoBlob(blob)
    setPhotoUrl(URL.createObjectURL(blob))
    setValidating(true)
    setState('VALIDATING')

    const fd = new FormData()
    fd.append('image', blob, 'photo.jpg')
    try {
      const res = await fetch('/validate', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.ok) {
        setValidating(false)
        setState('REVIEW')
      } else {
        setErrorMsg(data.message || 'Bildet er ikke gyldig. Prøv igjen.')
        setValidating(false)
        setState('PREVIEW')
      }
    } catch (e) {
      console.error('[validate]', e)
      setValidating(false)
      setState('REVIEW') // proceed anyway on network error
    }
  }, [])

  const handleReviewOk = useCallback(() => setState('NAME_INPUT'), [])

  const handleNameSubmit = useCallback((user) => {
    setUserId(user.id)
    setName(user.name)
    setState('INTEREST_SELECT')
  }, [])

  const handleInterestSelect = useCallback(async (i) => {
    setInterest(i)
    setState('DONE')

    // Enroll face (fire and forget)
    if (photoBlob && userId) {
      const enrollFd = new FormData()
      enrollFd.append('image', photoBlob, 'photo.jpg')
      enrollFd.append('user_id', userId)
      fetch('/face/enroll', { method: 'POST', body: enrollFd }).catch(e => console.error('[face enroll]', e))
    }

    // Print label (fire and forget)
    const printFd = new FormData()
    printFd.append('name', name)
    printFd.append('interest', i)
    printFd.append('user_id', userId)
    fetch('/print-label', { method: 'POST', body: printFd }).catch(e => console.error('[print-label]', e))
  }, [photoBlob, userId, name])

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
    setUserId('')
    setName('')
    setInterest('')
    setErrorMsg('')
    setValidating(false)
    setFlow(null)
    setMatchedUser(null)
    setDemoChoice('')
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
        <NameInputScreen onSubmit={handleNameSubmit} onBack={() => setState('PREVIEW')} />
      )}
      {state === 'INTEREST_SELECT' && (
        <InterestSelectScreen onSelect={handleInterestSelect} onBack={() => setState('NAME_INPUT')} />
      )}
      {state === 'DONE' && (
        <DoneScreen name={name} interest={interest} onDone={handleDone} />
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
