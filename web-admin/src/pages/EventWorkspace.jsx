import { useEffect, useState } from 'react'
import { Link, NavLink, Route, Routes, useParams } from 'react-router-dom'
import { api } from '../api'
import FlowCanvas from '../components/FlowCanvas'
import EventSettings from '../components/EventSettings'
import AttendeesPanel from '../components/AttendeesPanel'
import BoothsPanel from '../components/BoothsPanel'

export default function EventWorkspace() {
  const { eventId } = useParams()
  const [event, setEvent] = useState(null)
  const [error, setError] = useState('')

  async function load() {
    try {
      setEvent(await api.getEvent(eventId))
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [eventId])

  async function savePatch(patch) {
    const updated = await api.patchEvent(eventId, patch)
    setEvent(updated)
    return updated
  }

  if (error) {
    return (
      <main className="content">
        <p style={{ color: '#ff9aa8' }}>{error}</p>
        <Link to="/">Tilbake</Link>
      </main>
    )
  }

  if (!event) {
    return (
      <main className="content">
        <p className="muted">Laster...</p>
      </main>
    )
  }

  return (
    <>
      <header className="topbar">
        <div className="row">
          <Link to="/" className="btn btn-ghost">
            ← Arrangementer
          </Link>
          <h1>{event.name}</h1>
        </div>
        <span className="muted">/e/{event.slug}</span>
      </header>
      <nav className="tabs">
        <NavLink to={`/events/${eventId}`} end className={({ isActive }) => `tab${isActive ? ' active' : ''}`}>
          Canvas
        </NavLink>
        <NavLink to={`/events/${eventId}/attendees`} className={({ isActive }) => `tab${isActive ? ' active' : ''}`}>
          Deltakere
        </NavLink>
        <NavLink to={`/events/${eventId}/booths`} className={({ isActive }) => `tab${isActive ? ' active' : ''}`}>
          Booths
        </NavLink>
        <NavLink to={`/events/${eventId}/settings`} className={({ isActive }) => `tab${isActive ? ' active' : ''}`}>
          Innstillinger
        </NavLink>
      </nav>
      <main className="content">
        <Routes>
          <Route
            index
            element={<FlowCanvas event={event} onSaveFlow={(flow) => savePatch({ flow })} onSaveSettings={savePatch} />}
          />
          <Route
            path="attendees"
            element={<AttendeesPanel event={event} />}
          />
          <Route path="booths" element={<BoothsPanel event={event} />} />
          <Route
            path="settings"
            element={<EventSettings event={event} onSave={savePatch} onReload={load} />}
          />
        </Routes>
      </main>
    </>
  )
}
