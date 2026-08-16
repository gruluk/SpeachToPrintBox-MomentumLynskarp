import { useEffect, useState } from 'react'
import { api } from '../api'
import { joinStartsAt, splitStartsAt } from '../datetime'

/** Event-level settings only. Booth content (privacy, interests, lookup) is edited on the canvas. */
export default function EventSettings({ event, onSave, onReload }) {
  const initial = splitStartsAt(event.starts_at)
  const [form, setForm] = useState({
    name: event.name || '',
    slug: event.slug || '',
    startDate: initial.date,
    startTime: initial.time,
  })
  const [msg, setMsg] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const next = splitStartsAt(event.starts_at)
    setForm({
      name: event.name || '',
      slug: event.slug || '',
      startDate: next.date,
      startTime: next.time,
    })
  }, [event])

  async function submit(e) {
    e.preventDefault()
    setSaving(true)
    setMsg('')
    try {
      await onSave({
        name: form.name,
        slug: form.slug,
        starts_at: joinStartsAt(form.startDate, form.startTime),
        ends_at: '',
      })
      setMsg('Lagret')
      onReload?.()
    } catch (err) {
      setMsg(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function removeEvent() {
    if (!confirm('Slette dette arrangementet og alle deltakere/booths?')) return
    try {
      await api.deleteEvent(event.id)
      window.location.href = '/admin/'
    } catch (err) {
      setMsg(err.message)
    }
  }

  return (
    <form className="card" style={{ maxWidth: 720 }} onSubmit={submit}>
      <h2 style={{ marginBottom: '0.5rem' }}>Innstillinger</h2>
      <p className="muted" style={{ marginBottom: '1.25rem' }}>
        Arrangementets navn, URL og tidspunkt. Personvern, interesser og oppslag redigeres på canvas
        — klikk på den aktuelle siden der.
      </p>
      <label className="field">
        Navn
        <input
          className="input"
          value={form.name || ''}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
      </label>
      <label className="field">
        Slug (URL)
        <input
          className="input"
          value={form.slug || ''}
          onChange={(e) => setForm({ ...form, slug: e.target.value })}
        />
      </label>
      <div className="row">
        <label className="field" style={{ flex: 1 }}>
          Dato
          <input
            className="input"
            type="date"
            value={form.startDate || ''}
            onChange={(e) => setForm({ ...form, startDate: e.target.value })}
          />
        </label>
        <label className="field" style={{ flex: 1 }}>
          Starttid
          <input
            className="input"
            type="time"
            value={form.startTime || ''}
            onChange={(e) => setForm({ ...form, startTime: e.target.value })}
          />
        </label>
      </div>
      <div className="row">
        <button className="btn btn-primary" disabled={saving}>
          Lagre
        </button>
        <button className="btn btn-ghost" type="button" onClick={removeEvent}>
          Slett arrangement
        </button>
      </div>
      {msg && (
        <p className="muted" style={{ marginTop: '0.75rem' }}>
          {msg}
        </p>
      )}
    </form>
  )
}
