import { useState } from 'react'
import SceneDecorations from './SceneDecorations'

export default function NameInputScreen({ onSubmit, onBack }) {
  const [value, setValue] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (value.trim()) onSubmit(value.trim())
  }

  return (
    <div className="screen center">
      <SceneDecorations seed={3} />
      <h2>Hva heter du?</h2>
      <form onSubmit={handleSubmit} className="name-form">
        <input
          className="name-input"
          type="text"
          placeholder="Ditt navn"
          value={value}
          onChange={e => setValue(e.target.value)}
          autoFocus
          maxLength={40}
        />
        <div className="btn-row">
          <button className="btn-secondary" type="button" onClick={onBack}>← Tilbake</button>
          <button className="btn-primary" type="submit" disabled={!value.trim()}>Neste →</button>
        </div>
      </form>
    </div>
  )
}
