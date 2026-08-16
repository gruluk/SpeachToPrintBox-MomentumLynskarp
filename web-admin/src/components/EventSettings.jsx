import { useEffect, useState } from 'react'
import { api } from '../api'
import { joinStartsAt, splitStartsAt } from '../datetime'

export default function EventSettings({ event, onSave, onReload }) {
  const initial = splitStartsAt(event.starts_at)
  const [form, setForm] = useState({ ...event, startDate: initial.date, startTime: initial.time })
  const [msg, setMsg] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const next = splitStartsAt(event.starts_at)
    setForm({ ...event, startDate: next.date, startTime: next.time })
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
        lookup_mode: form.lookup_mode,
        allow_walkup_registration: form.allow_walkup_registration,
        interests: form.interests,
        max_interests: form.max_interests,
        privacy_title: form.privacy_title,
        privacy_bullets: form.privacy_bullets,
        privacy_checkbox_label: form.privacy_checkbox_label,
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
      <h2 style={{ marginBottom: '1rem' }}>Innstillinger</h2>
      <label className="field">
        Navn
        <input className="input" value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </label>
      <label className="field">
        Slug (URL)
        <input className="input" value={form.slug || ''} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
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
      <label className="field">
        Oppslagsmodus
        <select className="select" value={form.lookup_mode || 'name'} onChange={(e) => setForm({ ...form, lookup_mode: e.target.value })}>
          <option value="name">Kun navn</option>
          <option value="phone">Kun telefon</option>
          <option value="both">Navn og telefon</option>
        </select>
      </label>
      <label className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
        <input
          type="checkbox"
          checked={Boolean(form.allow_walkup_registration)}
          onChange={(e) => setForm({ ...form, allow_walkup_registration: e.target.checked })}
        />
        Tillat walk-up registrering
      </label>
      <label className="field">
        Interesser (én per linje)
        <textarea
          className="textarea"
          value={(form.interests || []).join('\n')}
          onChange={(e) => setForm({ ...form, interests: e.target.value.split('\n').map((l) => l.trim()).filter(Boolean) })}
        />
      </label>
      <label className="field">
        Maks interesser
        <input className="input" type="number" min={1} max={10} value={form.max_interests || 3} onChange={(e) => setForm({ ...form, max_interests: Number(e.target.value) })} />
      </label>
      <label className="field">
        Personvern-tittel
        <input className="input" value={form.privacy_title || ''} onChange={(e) => setForm({ ...form, privacy_title: e.target.value })} />
      </label>
      <label className="field">
        Personvern-punkter
        <textarea
          className="textarea"
          value={(form.privacy_bullets || []).join('\n')}
          onChange={(e) => setForm({ ...form, privacy_bullets: e.target.value.split('\n').filter((l) => l.trim()) })}
        />
      </label>
      <label className="field">
        Avkrysningstekst
        <textarea className="textarea" value={form.privacy_checkbox_label || ''} onChange={(e) => setForm({ ...form, privacy_checkbox_label: e.target.value })} />
      </label>
      <div className="row">
        <button className="btn btn-primary" disabled={saving}>Lagre</button>
        <button className="btn btn-ghost" type="button" onClick={removeEvent}>Slett arrangement</button>
      </div>
      {msg && <p className="muted" style={{ marginTop: '0.75rem' }}>{msg}</p>}
    </form>
  )
}
