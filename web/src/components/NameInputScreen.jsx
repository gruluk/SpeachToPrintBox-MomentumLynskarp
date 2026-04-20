import { useState, useEffect, useRef } from 'react'

export default function NameInputScreen({ onSubmit, onCancel }) {
  const [filter, setFilter] = useState('')
  const [allUsers, setAllUsers] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [showReregister, setShowReregister] = useState(false)
  const inputRef = useRef(null)
  const screenRef = useRef(null)

  // Load all registered users on mount
  useEffect(() => {
    fetch('/users')
      .then(r => r.json())
      .then(data => setAllUsers(data))
      .catch(e => console.error('[users]', e))
  }, [])

  // Auto-focus input for keyboard
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Resize screen when virtual keyboard opens/closes (iPad)
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

  const filtered = allUsers.filter(u =>
    u.name.toLowerCase().includes(filter.toLowerCase())
  )

  const selectedUser = allUsers.find(u => u.id === selectedId)

  function handleSelect(user) {
    setSelectedId(user.id)
    setFilter(user.name)
    setShowReregister(false)
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!selectedUser) return
    if (selectedUser.has_char && !showReregister) {
      setShowReregister(true)
      return
    }
    onSubmit({ id: selectedUser.id, name: selectedUser.name })
  }

  function handleInputChange(val) {
    setFilter(val)
    setShowReregister(false)
    // Clear selection if user edits the text away from the selected name
    if (selectedUser && val !== selectedUser.name) {
      setSelectedId(null)
    }
  }

  return (
    <div ref={screenRef} className="screen center name-screen">
      <h2>Hva heter du?</h2>
      <form onSubmit={handleSubmit} className="name-form">
        <input
          ref={inputRef}
          className="name-input"
          type="text"
          placeholder="Søk etter navnet ditt..."
          value={filter}
          onChange={e => handleInputChange(e.target.value)}
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
              {filtered.map(u => (
                <li
                  key={u.id}
                  className={`name-list-item ${selectedId === u.id ? 'name-list-selected' : ''}`}
                  onClick={() => handleSelect(u)}
                >
                  {u.name}
                </li>
              ))}
            </ul>
          )}
        </div>
        {showReregister && (
          <div className="reregister-notice">
            <p>Du er allerede registrert! Vil du lage en ny avatar?</p>
            <p className="reregister-sub">Dine eksisterende demovalg beholdes.</p>
          </div>
        )}
        <p className="name-help-text">Finner du ikke navnet ditt? Ta kontakt med en av våre ansatte.</p>
        <div className="btn-row">
          <button className="btn-cancel" type="button" onClick={onCancel}>Avbryt</button>
          <button className="btn-primary" type="submit" disabled={!selectedUser}>
            {showReregister ? 'Registrer på nytt' : 'Neste'}
          </button>
        </div>
      </form>
    </div>
  )
}
