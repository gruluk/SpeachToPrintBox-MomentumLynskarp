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
import { apiBase, hasAction, nextNodeId, nodeScreen, parseBoothLocation } from './flow'

export default function App() {
  const { eventSlug, boothNumber } = parseBoothLocation()
  const base = apiBase(eventSlug)

  const [boothMode, setBoothMode] = useState('both')
  const [eventConfig, setEventConfig] = useState(null)
  const [nodeId, setNodeId] = useState('start')
  const [userId, setUserId] = useState('')
  const [name, setName] = useState('')
  const [interest, setInterest] = useState('')
  const [matchedUser, setMatchedUser] = useState(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    fetch(`${base}/booth-config/${boothNumber}`)
      .then((r) => {
        if (!r.ok) throw new Error('config failed')
        return r.json()
      })
      .then((data) => {
        setBoothMode(data.mode || 'both')
        setEventConfig(data.event || null)
        setNodeId('start')
      })
      .catch((e) => {
        console.error(e)
        setLoadError('Kunne ikke laste arrangementet.')
      })
  }, [base, boothNumber])

  const flow = eventConfig?.flow
  const screen = nodeScreen(flow, nodeId) || (nodeId === 'start' ? 'start' : null)

  const go = useCallback(
    (action) => {
      if (!flow) return
      const next = nextNodeId(flow, nodeId, action)
      if (next) {
        const scr = nodeScreen(flow, next)
        // Skip integration nodes when navigating guest flow
        if (scr) setNodeId(next)
        else {
          // Follow through if target is integration — stay put for print side-effect
        }
      }
    },
    [flow, nodeId],
  )

  const reset = useCallback(() => {
    setUserId('')
    setName('')
    setInterest('')
    setMatchedUser(null)
    setNodeId('start')
  }, [])

  const handleNameSubmit = useCallback(
    (user) => {
      setUserId(user.id)
      setName(user.name)
      go('next')
    },
    [go],
  )

  const handleInterestSelect = useCallback(
    async (i) => {
      setInterest(i)
      const printFd = new FormData()
      printFd.append('name', name)
      printFd.append('interest', i)
      printFd.append('user_id', userId)
      fetch(`${base}/print-label`, { method: 'POST', body: printFd }).catch((e) =>
        console.error('[print-label]', e),
      )
      // Prefer done screen via flow; print edge is side-effect
      const done = nextNodeId(flow, nodeId, 'next')
      if (done) setNodeId(done)
    },
    [base, name, userId, flow, nodeId],
  )

  const handleWantsDemo = useCallback(async () => {
    if (matchedUser) {
      fetch(`${base}/demo-choice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: matchedUser.id, wants_demo: true }),
      }).catch((e) => console.error('[demo-choice]', e))
    }
    go('wants_demo')
  }, [matchedUser, base, go])

  const handleNoDemo = useCallback(() => {
    go('no_demo')
  }, [go])

  if (loadError) {
    return (
      <div className="app">
        <div className="screen center">
          <p className="error">{loadError}</p>
        </div>
      </div>
    )
  }

  if (!eventConfig) {
    return (
      <div className="app">
        <div className="screen center">
          <p className="subtitle">Laster...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {screen === 'start' && (
        <StartScreen
          mode={boothMode}
          showRegister={hasAction(flow, 'start', 'register') && boothMode !== 'demo'}
          showCheckout={hasAction(flow, 'start', 'checkout') && boothMode !== 'register'}
          onRegister={() => go('register')}
          onDemo={() => go('checkout')}
        />
      )}

      {screen === 'privacy' && (
        <PrivacyScreen
          title={eventConfig.privacy_title}
          bullets={eventConfig.privacy_bullets}
          checkboxLabel={eventConfig.privacy_checkbox_label}
          onAccept={() => go('next')}
          onCancel={reset}
        />
      )}

      {screen === 'name_input' && (
        <NameInputScreen
          apiBase={base}
          lookupMode={eventConfig.lookup_mode}
          allowWalkup={eventConfig.allow_walkup_registration}
          onSubmit={handleNameSubmit}
          onCancel={reset}
        />
      )}

      {screen === 'interest_select' && (
        <InterestSelectScreen
          name={name}
          interests={eventConfig.interests}
          maxCount={eventConfig.max_interests}
          onSelect={handleInterestSelect}
          onCancel={reset}
        />
      )}

      {screen === 'done' && (
        <DoneScreen name={name} interest={interest} userId={userId} onDone={reset} />
      )}

      {screen === 'qr_scan' && (
        <QrScanScreen
          apiBase={base}
          onScanned={(user) => {
            setMatchedUser(user)
            go('next')
          }}
          onCancel={reset}
        />
      )}

      {screen === 'demo_matched' && (
        <DemoMatchedScreen
          matchedUser={matchedUser}
          onWantsDemo={handleWantsDemo}
          onNoDemo={handleNoDemo}
        />
      )}

      {screen === 'demo_done' && (
        <DemoDoneScreen name={matchedUser?.name} onDone={reset} />
      )}

      {screen === 'checkout_done' && (
        <CheckoutDoneScreen name={matchedUser?.name} onDone={reset} />
      )}
    </div>
  )
}
