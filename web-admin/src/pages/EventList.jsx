import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function EventList() {
  const [events, setEvents] = useState([])
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')

  async function load() {
    try {
      setEvents(await api.listEvents())
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function createEvent(e) {
    e.preventDefault()
    setCreating(true)
    try {
      await api.createEvent({ name: name.trim() || 'Nytt arrangement' })
      setName('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <>
      <header className="topbar">
        <h1>LYNSKARP / Admin</h1>
      </header>
      <main className="content">
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <h2>Arrangementer</h2>
          <form className="row" onSubmit={createEvent}>
            <input
              className="input"
              style={{ width: 220 }}
              placeholder="Navn på arrangement"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <button className="btn btn-primary" disabled={creating}>
              Opprett
            </button>
          </form>
        </div>
        {error && <p className="muted" style={{ color: '#ff9aa8', marginBottom: '1rem' }}>{error}</p>}
        <div className="grid">
          {events.map((ev) => (
            <div className="card event-card" key={ev.id}>
              <h3>{ev.name}</h3>
              <p>Slug: /e/{ev.slug}</p>
              <p>
                {ev.attendee_count} deltakere · {ev.booth_count} booths
              </p>
              {(ev.starts_at || ev.ends_at) && (
                <p>
                  {ev.starts_at || '—'} → {ev.ends_at || '—'}
                </p>
              )}
              <div className="actions">
                <Link className="btn btn-primary" to={`/events/${ev.id}`}>
                  Åpne
                </Link>
              </div>
            </div>
          ))}
        </div>
      </main>
    </>
  )
}
