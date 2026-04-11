import { useState, useEffect, useRef } from 'react'

export default function NameInputScreen({ onSubmit, onBack }) {
  const [value, setValue] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const debounceRef = useRef(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!value.trim()) {
      setSuggestions([])
      return
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`/registered-users?q=${encodeURIComponent(value.trim())}`)
        const data = await res.json()
        setSuggestions(data)
        setShowSuggestions(data.length > 0)
      } catch (e) {
        console.error('[autocomplete]', e)
      }
    }, 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [value])

  function handleSubmit(e) {
    e.preventDefault()
    if (value.trim()) {
      setShowSuggestions(false)
      onSubmit(value.trim())
    }
  }

  function selectSuggestion(name) {
    setValue(name)
    setShowSuggestions(false)
  }

  return (
    <div className="screen center">
      <h2>What's your name?</h2>
      <form onSubmit={handleSubmit} className="name-form">
        <div className="autocomplete-wrap">
          <input
            className="name-input"
            type="text"
            placeholder="Your name"
            value={value}
            onChange={e => { setValue(e.target.value); setShowSuggestions(true) }}
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            autoFocus
            maxLength={40}
          />
          {showSuggestions && suggestions.length > 0 && (
            <ul className="autocomplete-list">
              {suggestions.slice(0, 8).map(s => (
                <li key={s.id} className="autocomplete-item" onClick={() => selectSuggestion(s.name)}>
                  {s.name}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="btn-row">
          <button className="btn-secondary" type="button" onClick={onBack}>Back</button>
          <button className="btn-primary" type="submit" disabled={!value.trim()}>Next</button>
        </div>
      </form>
    </div>
  )
}
