import { useState, useCallback, useEffect } from 'react'
import './App.css'
import StartScreen from './components/StartScreen'
import NameInputScreen from './components/NameInputScreen'
import PrivacyScreen from './components/PrivacyScreen'
import InterestSelectScreen from './components/InterestSelectScreen'
import DoneScreen from './components/DoneScreen'
import QrScanScreen from './components/QrScanScreen'
import DemoMatchedScreen from './components/DemoMatchedScreen'
import DemoDoneScreen from './components/DemoDoneScreen'
import CheckoutDoneScreen from './components/CheckoutDoneScreen'

export default function App() {
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
  const [userId, setUserId] = useState('')
  const [name, setName] = useState('')
  const [interest, setInterest] = useState('')

  // Demo flow state
  const [matchedUser, setMatchedUser] = useState(null)

  // --- Register flow ---

  const handleNameSubmit = useCallback((user) => {
    setUserId(user.id)
    setName(user.name)
    setState('PRIVACY')
  }, [])

  const handleInterestSelect = useCallback(async (i) => {
    setInterest(i)
    setState('DONE')

    // Print label (fire and forget)
    const printFd = new FormData()
    printFd.append('name', name)
    printFd.append('interest', i)
    printFd.append('user_id', userId)
    fetch('/print-label', { method: 'POST', body: printFd }).catch(e => console.error('[print-label]', e))
  }, [userId, name])

  // --- Demo flow ---

  const handleWantsDemo = useCallback(async () => {
    if (matchedUser) {
      fetch('/demo-choice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: matchedUser.id, wants_demo: true }),
      }).catch(e => console.error('[demo-choice]', e))
    }
    setState('DEMO_DONE')
  }, [matchedUser])

  const handleNoDemo = useCallback(() => {
    setState('CHECKOUT_DONE')
  }, [])

  // --- Reset ---

  const handleDone = useCallback(() => {
    setUserId('')
    setName('')
    setInterest('')
    setFlow(null)
    setMatchedUser(null)
    setState('START')
  }, [])

  return (
    <div className="app">
      {state === 'START' && (
        <StartScreen
          mode={boothMode}
          onRegister={() => { setFlow('register'); setState('NAME_INPUT') }}
          onDemo={() => { setFlow('demo'); setState('QR_SCAN') }}
        />
      )}

      {/* Register flow */}
      {state === 'NAME_INPUT' && (
        <NameInputScreen onSubmit={handleNameSubmit} onCancel={handleDone} />
      )}
      {state === 'PRIVACY' && (
        <PrivacyScreen onAccept={() => setState('INTEREST_SELECT')} onCancel={handleDone} />
      )}
      {state === 'INTEREST_SELECT' && (
        <InterestSelectScreen name={name} onSelect={handleInterestSelect} onCancel={handleDone} />
      )}
      {state === 'DONE' && (
        <DoneScreen name={name} interest={interest} userId={userId} onDone={handleDone} />
      )}

      {/* Demo flow */}
      {state === 'QR_SCAN' && (
        <QrScanScreen
          onScanned={(user) => { setMatchedUser(user); setState('DEMO_MATCHED') }}
          onCancel={handleDone}
        />
      )}
      {state === 'DEMO_MATCHED' && (
        <DemoMatchedScreen matchedUser={matchedUser} onWantsDemo={handleWantsDemo} onNoDemo={handleNoDemo} />
      )}
      {state === 'DEMO_DONE' && (
        <DemoDoneScreen name={matchedUser?.name} onDone={handleDone} />
      )}
      {state === 'CHECKOUT_DONE' && (
        <CheckoutDoneScreen name={matchedUser?.name} onDone={handleDone} />
      )}
    </div>
  )
}
