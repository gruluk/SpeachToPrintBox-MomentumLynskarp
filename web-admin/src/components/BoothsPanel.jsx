import { useEffect, useState } from 'react'
import { api } from '../api'

export default function BoothsPanel({ event }) {
  const [booths, setBooths] = useState([])
  const [error, setError] = useState('')

  async function load() {
    try {
      setBooths(await api.listBooths(event.id))
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [event.id])

  function boothUrl(number) {
    return `${window.location.origin}/e/${event.slug}/booth/${number}`
  }

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2>Booths</h2>
        <button
          className="btn btn-primary"
          onClick={async () => {
            await api.createBooth(event.id)
            await load()
          }}
        >
          Legg til booth
        </button>
      </div>
      {error && <p style={{ color: '#ff9aa8' }}>{error}</p>}
      <div className="grid">
        {booths.map((b) => (
          <div className="card" key={b.id}>
            <h3>{b.name}</h3>
            <p className="muted">Nummer: {b.number}</p>
            <label className="field">
              Modus
              <select
                className="select"
                value={b.mode || 'both'}
                onChange={async (e) => {
                  await api.patchBooth(event.id, b.id, { mode: e.target.value })
                  await load()
                }}
              >
                <option value="both">Begge</option>
                <option value="register">Kun registrering</option>
                <option value="demo">Kun utsjekk</option>
              </select>
            </label>
            <p className="muted" style={{ wordBreak: 'break-all', fontSize: '0.8rem' }}>
              {boothUrl(b.number)}
            </p>
            <div className="row">
              <button
                className="btn btn-ghost"
                onClick={() => navigator.clipboard.writeText(boothUrl(b.number))}
              >
                Kopier URL
              </button>
              <button
                className="btn btn-ghost"
                onClick={async () => {
                  if (!confirm('Slette booth?')) return
                  await api.deleteBooth(event.id, b.id)
                  await load()
                }}
              >
                Slett
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
