import { useState, useEffect, useRef } from 'react'

export default function NameInputScreen({
  apiBase = '',
  lookupMode = 'name',
  allowWalkup = false,
  onSubmit,
  onCancel,
}) {
  const [filter, setFilter] = useState('')
  const [allUsers, setAllUsers] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [walkupMode, setWalkupMode] = useState(false)
  const [walkupName, setWalkupName] = useState('')
  const [walkupEmail, setWalkupEmail] = useState('')
  const [walkupPhone, setWalkupPhone] = useState('')
  const [walkupError, setWalkupError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const inputRef = useRef(null)
  const screenRef = useRef(null)

  useEffect(() => {
    fetch(`${apiBase}/users`)
      .then((r) => r.json())
      .then((data) => setAllUsers(data))
      .catch((e) => console.error('[users]', e))
  }, [apiBase])

  useEffect(() => {
    inputRef.current?.focus()
  }, [walkupMode])

  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    function onResize() {
      if (screenRef.current) {
        screenRef.current.style.height = `${vv.height}px`
      }
    }
    onResize()
    vv.addEventListener('resize', onResize)
    return () => vv.removeEventListener('resize', onResize)
  }, [])

  const q = filter.toLowerCase().replace(/\s/g, '')
  const filtered = allUsers.filter((u) => {
    if (!filter.trim()) return true
    const name = (u.name || '').toLowerCase()
    const phone = (u.phone || '').toLowerCase().replace(/\s/g, '')
    if (lookupMode === 'name') return name.includes(filter.toLowerCase())
    if (lookupMode === 'phone') return phone.includes(q)
    return name.includes(filter.toLowerCase()) || phone.includes(q)
  })

  const selectedUser = allUsers.find((u) => u.id === selectedId)

  function handleSelect(user) {
    setSelectedId(user.id)
    setFilter(lookupMode === 'phone' ? user.phone || user.name : user.name)
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!selectedUser) return
    onSubmit({ id: selectedUser.id, name: selectedUser.name })
  }

  function handleInputChange(val) {
    setFilter(val)
    if (selectedUser) {
      const match =
        lookupMode === 'phone'
          ? val === (selectedUser.phone || selectedUser.name)
          : val === selectedUser.name
      if (!match) setSelectedId(null)
    }
  }

  async function handleWalkup(e) {
    e.preventDefault()
    setWalkupError('')
    if (!walkupName.trim()) {
      setWalkupError('Navn er påkrevd')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch(`${apiBase}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: walkupName.trim(),
          email: walkupEmail.trim(),
          phone: walkupPhone.trim(),
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setWalkupError(data.detail || 'Kunne ikke registrere')
        return
      }
      onSubmit({ id: data.id, name: data.name })
    } catch (err) {
      setWalkupError(String(err))
    } finally {
      setSubmitting(false)
    }
  }

  const placeholder =
    lookupMode === 'phone'
      ? 'Søk etter telefonnummer...'
      : lookupMode === 'both'
        ? 'Søk etter navn eller telefon...'
        : 'Søk etter navnet ditt...'

  const title =
    lookupMode === 'phone' ? 'Hva er telefonnummeret ditt?' : 'Hva heter du?'

  if (walkupMode) {
    return (
      <div ref={screenRef} className="screen center name-screen">
        <h2>Registrer ny deltaker</h2>
        <form onSubmit={handleWalkup} className="name-form">
          <input
            ref={inputRef}
            className="name-input"
            type="text"
            placeholder="Navn"
            value={walkupName}
            onChange={(e) => setWalkupName(e.target.value)}
            maxLength={40}
          />
          <input
            className="name-input"
            type="email"
            placeholder="E-post (valgfritt)"
            value={walkupEmail}
            onChange={(e) => setWalkupEmail(e.target.value)}
            style={{ marginTop: '0.75rem' }}
          />
          <input
            className="name-input"
            type="tel"
            placeholder="Telefon (valgfritt)"
            value={walkupPhone}
            onChange={(e) => setWalkupPhone(e.target.value)}
            style={{ marginTop: '0.75rem' }}
          />
          {walkupError && <p className="error">{walkupError}</p>}
          <div className="btn-row">
            <button className="btn-cancel" type="button" onClick={() => setWalkupMode(false)}>
              Tilbake
            </button>
            <button className="btn-primary" type="submit" disabled={submitting || !walkupName.trim()}>
              Neste
            </button>
          </div>
        </form>
      </div>
    )
  }

  return (
    <div ref={screenRef} className="screen center name-screen">
      <h2>{title}</h2>
      <form onSubmit={handleSubmit} className="name-form">
        <input
          ref={inputRef}
          className="name-input"
          type="text"
          placeholder={placeholder}
          value={filter}
          onChange={(e) => handleInputChange(e.target.value)}
          autoFocus
          maxLength={40}
        />
        <div className="name-list-wrap">
          {filtered.length === 0 ? (
            <p className="name-list-empty">
              {allUsers.length === 0 ? 'Laster...' : 'Ingen treff'}
            </p>
          ) : (
            <ul className="name-list">
              {filtered.map((u) => (
                <li
                  key={u.id}
                  className={`name-list-item ${selectedId === u.id ? 'name-list-selected' : ''}`}
                  onClick={() => handleSelect(u)}
                >
                  {u.name}
                  {lookupMode !== 'name' && u.phone ? (
                    <span style={{ opacity: 0.6 }}> · {u.phone}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
        {allowWalkup ? (
          <p className="name-help-text">
            Finner du ikke navnet ditt?{' '}
            <button type="button" className="linkish" onClick={() => setWalkupMode(true)}>
              Registrer ny
            </button>
          </p>
        ) : (
          <p className="name-help-text">
            Finner du ikke navnet ditt? Ta kontakt med en av våre ansatte.
          </p>
        )}
        <div className="btn-row">
          <button className="btn-cancel" type="button" onClick={onCancel}>
            Avbryt
          </button>
          <button className="btn-primary" type="submit" disabled={!selectedUser}>
            Neste
          </button>
        </div>
      </form>
    </div>
  )
}
