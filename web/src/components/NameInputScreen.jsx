import { useState, useEffect, useRef } from 'react'

export default function NameInputScreen({ onSubmit, onBack }) {
  const [filter, setFilter] = useState('')
  const [allUsers, setAllUsers] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const inputRef = useRef(null)

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

  const filtered = allUsers.filter(u =>
    u.name.toLowerCase().includes(filter.toLowerCase())
  )

  const selectedUser = allUsers.find(u => u.id === selectedId)

  function handleSelect(user) {
    setSelectedId(user.id)
    setFilter(user.name)
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (selectedUser) {
      onSubmit({ id: selectedUser.id, name: selectedUser.name })
    }
  }

  function handleInputChange(val) {
    setFilter(val)
    // Clear selection if user edits the text away from the selected name
    if (selectedUser && val !== selectedUser.name) {
      setSelectedId(null)
    }
  }

  return (
    <div className="screen center">
      <h2>What's your name?</h2>
      <form onSubmit={handleSubmit} className="name-form">
        <input
          ref={inputRef}
          className="name-input"
          type="text"
          placeholder="Search your name..."
          value={filter}
          onChange={e => handleInputChange(e.target.value)}
          autoFocus
          maxLength={40}
        />
        <div className="name-list-wrap">
          {filtered.length === 0 ? (
            <p className="name-list-empty">
              {allUsers.length === 0 ? 'Loading...' : 'No matching names found'}
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
        <div className="btn-row">
          <button className="btn-secondary" type="button" onClick={onBack}>Back</button>
          <button className="btn-primary" type="submit" disabled={!selectedUser}>Next</button>
        </div>
      </form>
    </div>
  )
}
