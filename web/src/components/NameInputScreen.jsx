import { useState } from 'react'

export default function NameInputScreen({ onSubmit }) {
  const [value, setValue] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (value.trim()) onSubmit(value.trim())
  }

  return (
    <div className="screen center">
      <h2>What's your name?</h2>
      <form onSubmit={handleSubmit} className="name-form">
        <input
          className="name-input"
          type="text"
          placeholder="Your name"
          value={value}
          onChange={e => setValue(e.target.value)}
          autoFocus
          maxLength={40}
        />
        <button className="btn-primary" type="submit" disabled={!value.trim()}>
          Next →
        </button>
      </form>
    </div>
  )
}
