import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { formatStartsAt } from '../datetime'

export default function EventList() {
  const [events, setEvents] = useState([])
  const [error, setError] = useState('')

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

  const sorted = [...events].sort((a, b) => {
    const da = a.starts_at || ''
    const db = b.starts_at || ''
    if (da && db) return da < db ? 1 : da > db ? -1 : 0
    if (da) return -1
    if (db) return 1
    return (a.name || '').localeCompare(b.name || '', 'nb')
  })

  return (
    <>
      <header className="topbar">
        <h1>LYNSKARP / Admin</h1>
      </header>
      <main className="content">
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div>
            <h2>Arrangementer</h2>
            <p className="muted" style={{ marginTop: '0.35rem' }}>
              Hvert arrangement har egen deltakerliste, booth-flyt og innstillinger.
            </p>
          </div>
          <Link className="btn btn-primary" to="/new">
            + Nytt arrangement
          </Link>
        </div>
        {error && (
          <p className="muted" style={{ color: '#ff9aa8', marginBottom: '1rem' }}>
            {error}
          </p>
        )}
        {events.length === 0 && !error && (
          <div className="card" style={{ maxWidth: 480 }}>
            <h3 style={{ marginBottom: '0.5rem' }}>Ingen arrangementer ennå</h3>
            <p className="muted" style={{ marginBottom: '1rem' }}>
              Start med navn og velkomstsiden — deretter bygger du flyten steg for steg på canvas.
            </p>
            <Link className="btn btn-primary" to="/new">
              Kom i gang
            </Link>
          </div>
        )}
        <div className="grid">
          {sorted.map((ev) => {
            const when = formatStartsAt(ev.starts_at)
            return (
              <Link key={ev.id} className="card event-card" to={`/events/${ev.id}`}>
                <p className={`event-card-date${when ? '' : ' empty'}`}>
                  {when || 'Ingen dato satt'}
                </p>
                <h3>{ev.name}</h3>
                <p className="event-card-meta">
                  {ev.attendee_count} deltakere · {ev.booth_count} booths
                </p>
                <p className="event-card-slug">/e/{ev.slug}</p>
              </Link>
            )
          })}
        </div>
      </main>
    </>
  )
}
